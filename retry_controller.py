"""
retry_controller.py — Retry loop for mq-devEngine post-checks.

Wraps PostCheckRunner with retry logic:
  1. Run post-checks after coding agent completes
  2. On failure: format error context for retry prompt
  3. Track attempts, give up after max_attempts
  4. Emit events for WebSocket (post_check_update)

Usage in orchestrator:
    controller = RetryController(project_dir="/path/to/project")
    outcome = await controller.run_with_retry(feature_id=42)

    if outcome.final_passed:
        # mark feature passing
    else:
        # mark feature failing + escalate
"""

from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

from post_checks import PostCheckReport, PostCheckRunner, load_checks_config


@dataclass
class RetryOutcome:
    """Final result after all retry attempts."""

    feature_id: int
    final_passed: bool
    attempts: list[PostCheckReport] = field(default_factory=list)
    total_duration_ms: int = 0

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def last_report(self) -> PostCheckReport | None:
        return self.attempts[-1] if self.attempts else None

    @property
    def escalation_reason(self) -> str | None:
        """Human-readable reason if all retries exhausted."""
        if self.final_passed:
            return None
        report = self.last_report
        if report is None:
            return "No post-check results available"
        failed = [c.name for c in report.failed_checks]
        return (
            f"Post-checks failed after {self.attempt_count} attempt(s). "
            f"Failing checks: {', '.join(failed)}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "final_passed": self.final_passed,
            "attempt_count": self.attempt_count,
            "total_duration_ms": self.total_duration_ms,
            "escalation_reason": self.escalation_reason,
            "attempts": [a.to_dict() for a in self.attempts],
        }


@dataclass
class PostCheckEvent:
    """Event emitted during post-check execution for WebSocket updates."""

    feature_id: int
    event_type: str  # "check_start" | "check_done" | "retry" | "complete"
    check_name: str | None = None
    passed: bool | None = None
    attempt: int = 1
    max_attempts: int = 3
    detail: str = ""

    def to_ws_message(self) -> dict[str, Any]:
        """Format as WebSocket message (type: post_check_update)."""
        return {
            "type": "post_check_update",
            "feature_id": self.feature_id,
            "event": self.event_type,
            "check_name": self.check_name,
            "passed": self.passed,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "detail": self.detail,
        }


# Type alias for the event callback
EventCallback = Callable[[PostCheckEvent], Awaitable[None]]


async def _noop_callback(event: PostCheckEvent) -> None:
    """Default no-op callback."""
    pass


class RetryController:
    """Manages post-check execution with retry logic."""

    def __init__(
        self,
        project_dir: str | Path,
        config: dict[str, Any] | None = None,
        on_event: EventCallback = _noop_callback,
    ):
        self.project_dir = Path(project_dir)
        self.config = config or load_checks_config(self.project_dir)
        self.on_event = on_event

        retry_cfg = self.config.get("retry", {})
        self.max_attempts: int = retry_cfg.get("max_attempts", 3)
        self.max_error_lines: int = retry_cfg.get("max_error_lines", 50)
        self.include_error_output: bool = retry_cfg.get("include_error_output", True)

    async def run_with_retry(self, feature_id: int) -> RetryOutcome:
        """Run post-checks with retry loop. Returns final outcome."""
        outcome = RetryOutcome(feature_id=feature_id, final_passed=False)
        t0 = time.monotonic()

        for attempt in range(1, self.max_attempts + 1):
            runner = PostCheckRunner(self.project_dir, config=self.config)

            # Emit start event
            await self.on_event(PostCheckEvent(
                feature_id=feature_id,
                event_type="check_start",
                attempt=attempt,
                max_attempts=self.max_attempts,
                detail=f"Running post-checks (attempt {attempt}/{self.max_attempts})",
            ))

            report = await runner.run_all()
            outcome.attempts.append(report)

            # Emit per-check results
            for check in report.checks:
                await self.on_event(PostCheckEvent(
                    feature_id=feature_id,
                    event_type="check_done",
                    check_name=check.name,
                    passed=check.passed,
                    attempt=attempt,
                    max_attempts=self.max_attempts,
                    detail=check.output[:200] if check.passed else (check.error or check.output)[:200],
                ))

            if report.passed:
                outcome.final_passed = True
                await self.on_event(PostCheckEvent(
                    feature_id=feature_id,
                    event_type="complete",
                    passed=True,
                    attempt=attempt,
                    max_attempts=self.max_attempts,
                    detail="All post-checks passed",
                ))
                break

            # Not the last attempt — emit retry event
            if attempt < self.max_attempts:
                await self.on_event(PostCheckEvent(
                    feature_id=feature_id,
                    event_type="retry",
                    passed=False,
                    attempt=attempt,
                    max_attempts=self.max_attempts,
                    detail=f"Retrying ({attempt}/{self.max_attempts}): {', '.join(c.name for c in report.failed_checks)}",
                ))
            else:
                # Final attempt failed
                await self.on_event(PostCheckEvent(
                    feature_id=feature_id,
                    event_type="complete",
                    passed=False,
                    attempt=attempt,
                    max_attempts=self.max_attempts,
                    detail=outcome.escalation_reason or "All retries exhausted",
                ))

        outcome.total_duration_ms = int((time.monotonic() - t0) * 1000)
        return outcome

    def format_retry_prompt(self, report: PostCheckReport) -> str:
        """Format a failed report as context for the coding agent retry prompt."""
        if not self.include_error_output:
            failed = [c.name for c in report.failed_checks]
            return f"Post-checks failed: {', '.join(failed)}. Fix and retry."

        return (
            "Your previous implementation failed the following post-checks. "
            "Fix the issues and try again.\n\n"
            + report.error_context(max_lines=self.max_error_lines)
        )
