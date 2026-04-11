"""
Codex Review — Sprint 1 Blok C (taken 1.9-1.11)
================================================

Onafhankelijke code review met OpenAI Codex CLI als alternatief voor de
interne Claude-based review agent. Codex is een ander AI-model/-systeem
en geeft daarmee een second opinion die onafhankelijk is van de Claude
keten die de code heeft gebouwd.

## Waarom Codex als reviewer

De bestaande review agent draait op Claude (via `autonomous_agent_demo.py
--agent-type reviewer`). Dat betekent: Claude reviewt Claude. Als Claude
een systematische bias heeft in code-generatie, mist die bias in de
review eveneens. Codex (gpt-5-codex/gpt-5) is een onafhankelijk systeem
en kan die bias-laag doorbreken.

## Task mapping

- **1.9 Codex review integratie**: deze module (`codex_review.py`) —
  invoker + prompt assembly + output parser
- **1.10 Codex input**: `build_review_prompt()` — bouwt prompt met AC's,
  tech stack en Definition of Done checklist
- **1.11 Reject → retry flow**: `review_with_retry()` — max 3x retry met
  voortgangsrapportage, daarna escalatie naar handmatig

## Feature flag

`CODEX_REVIEW_ENABLED` env var (default `false`). Als `true` wordt
`codex_review_feature()` aangeroepen i.p.v. de Claude-based reviewer.
De feature flag wordt in parallel_orchestrator._maintain_review_agents
gecheckt.

## Gebruik

```python
from api.codex_review import review_with_retry, ReviewVerdict

verdict = review_with_retry(
    story_id=42,
    diff="... git diff output ...",
    acceptance_criteria=["AC1: ...", "AC2: ..."],
    tech_stack="FastAPI + React + PostgreSQL",
    dod_checklist=["Tests green", "No mocks in production", ...],
    max_retries=3,
)

if verdict.status == "approved":
    mark_story_approved(story_id, notes=verdict.notes)
elif verdict.status == "rejected":
    mark_story_rejected(story_id, notes=verdict.notes)
else:  # escalate
    escalate_to_human(story_id, notes=verdict.notes)
```
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# ============================================================================
# Configuration
# ============================================================================

CODEX_REVIEW_ENABLED_ENV = "CODEX_REVIEW_ENABLED"
CODEX_MODEL_ENV = "CODEX_REVIEW_MODEL"
CODEX_REASONING_ENV = "CODEX_REVIEW_REASONING"

DEFAULT_CODEX_MODEL = "gpt-5-codex"  # alternative: "gpt-5"
DEFAULT_REASONING_EFFORT = "medium"  # high / medium / low
DEFAULT_MAX_RETRIES = 3

# Sandbox mode: read-only means Codex cannot edit files, only analyze.
# For reviews we always want read-only — the reviewer should not touch the code.
SANDBOX_MODE = "read-only"

CODEX_TIMEOUT_SECONDS = 300  # 5 minutes per review


def is_codex_review_enabled() -> bool:
    """Check if Codex review is enabled via env var feature flag."""
    val = os.environ.get(CODEX_REVIEW_ENABLED_ENV, "false").lower()
    return val in ("true", "1", "yes", "on")


# ============================================================================
# Data types
# ============================================================================

ReviewStatus = Literal["approved", "rejected", "error", "escalate"]


@dataclass
class ReviewVerdict:
    """Result of a Codex review call."""
    story_id: int
    status: ReviewStatus
    notes: str
    attempt: int = 1
    model: str = DEFAULT_CODEX_MODEL
    reasoning: str = DEFAULT_REASONING_EFFORT
    duration_seconds: float = 0.0
    raw_output: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def is_final(self) -> bool:
        """True if no more retries should be attempted."""
        return self.status in ("approved", "escalate")


# ============================================================================
# Task 1.10 — Prompt assembly: AC's + tech stack + DoD
# ============================================================================

DEFAULT_DOD_CHECKLIST = [
    "All acceptance criteria demonstrably met",
    "No mock/stub/placeholder data in production code",
    "All tests pass (lint + type-check + unit + integration)",
    "Test coverage >= 80% on changed files",
    "No TODO/FIXME/XXX comments left in committed code",
    "No secrets, API keys or credentials hardcoded",
    "Error handling appropriate for system boundaries (no try/except everywhere)",
    "Code follows existing project patterns and conventions",
    "No over-engineering: only build what the AC's require",
]


def build_review_prompt(
    story_id: int,
    story_name: str,
    story_description: str,
    acceptance_criteria: list[str],
    diff: str,
    tech_stack: str = "",
    dod_checklist: list[str] | None = None,
) -> str:
    """Build the review prompt for Codex.

    Task 1.10 implementation: the review input is (AC + tech stack + DoD).

    Args:
        story_id: Numeric ID of the story under review.
        story_name: Short title.
        story_description: Full description text.
        acceptance_criteria: List of AC strings. Each is something the code must prove.
        diff: Git diff of the implementation (or full file contents for first pass).
        tech_stack: Short description like "FastAPI + React + PostgreSQL".
        dod_checklist: Definition of Done items. If None, uses DEFAULT_DOD_CHECKLIST.

    Returns:
        A complete prompt string ready to send to Codex via stdin or -m argument.
    """
    dod = dod_checklist if dod_checklist else DEFAULT_DOD_CHECKLIST

    ac_block = "\n".join(f"- {ac}" for ac in acceptance_criteria) if acceptance_criteria else "(none provided)"
    dod_block = "\n".join(f"- [ ] {item}" for item in dod)

    tech_section = f"\n## Tech stack context\n{tech_stack}\n" if tech_stack else ""

    return f"""You are an independent code reviewer for story #{story_id}.

Your job: decide whether the implementation below meets the acceptance criteria
and Definition of Done, OR whether it must be rejected for rework.

## Story
**#{story_id} — {story_name}**

{story_description}

## Acceptance criteria (must all be demonstrably met)
{ac_block}
{tech_section}
## Definition of Done checklist
{dod_block}

## Implementation diff
```diff
{diff}
```

## Your output format (MUST follow exactly)

Respond with EXACTLY one of these verdict lines as your final line:
- `VERDICT: APPROVED`   (all AC met, DoD satisfied, quality acceptable)
- `VERDICT: REJECTED`   (one or more AC not met, or DoD issue, or quality problem)

Before the verdict line, provide:
1. Per-AC analysis: for each acceptance criterion, state met/not-met and why (1-2 sentences)
2. DoD checklist: mark each item [x] met or [ ] not met, with brief note
3. Summary: 2-3 sentences on overall code quality

Be direct. If something is ambiguous, err on the side of REJECTED and explain
what needs clarification. Do not propose changes yourself — that is the
coding agent's job. Your job is to judge.
"""


# ============================================================================
# Task 1.9 — Codex CLI invocation
# ============================================================================


def _run_codex(
    prompt: str,
    project_dir: Path,
    model: str = DEFAULT_CODEX_MODEL,
    reasoning: str = DEFAULT_REASONING_EFFORT,
) -> tuple[int, str, str]:
    """Run `codex exec` with the given prompt.

    Args:
        prompt: The review prompt string.
        project_dir: Working directory for Codex (should be the project root).
        model: Codex model name (gpt-5-codex or gpt-5).
        reasoning: Reasoning effort (high/medium/low).

    Returns:
        Tuple of (return_code, stdout, stderr).
    """
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "-m", model,
        "--config", f'model_reasoning_effort="{reasoning}"',
        "--sandbox", SANDBOX_MODE,
        "-C", str(project_dir),
    ]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=CODEX_TIMEOUT_SECONDS,
            cwd=str(project_dir),
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"Codex review timed out after {CODEX_TIMEOUT_SECONDS}s"
    except FileNotFoundError:
        return 127, "", "codex CLI not found in PATH"
    except Exception as e:
        return 1, "", f"Unexpected error invoking codex: {e}"


def _parse_verdict(output: str) -> tuple[ReviewStatus, str]:
    """Parse Codex output to extract the verdict line.

    The prompt asks Codex to end its response with exactly:
        VERDICT: APPROVED
    or
        VERDICT: REJECTED

    We scan the last ~20 lines for this marker (it should be the final line).

    Args:
        output: Full stdout from codex exec.

    Returns:
        Tuple of (status, notes). Status is one of: approved, rejected, error.
        Notes is the full output minus the verdict line (for logging/display).
    """
    if not output.strip():
        return "error", "Empty output from Codex"

    lines = output.strip().splitlines()
    tail = lines[-20:] if len(lines) > 20 else lines

    verdict_line = None
    for line in reversed(tail):
        stripped = line.strip()
        if stripped.startswith("VERDICT:"):
            verdict_line = stripped
            break

    if verdict_line is None:
        return "error", (
            "No VERDICT line found in Codex output. "
            f"Last 20 lines:\n{chr(10).join(tail)}"
        )

    if "APPROVED" in verdict_line:
        return "approved", output.strip()
    if "REJECTED" in verdict_line:
        return "rejected", output.strip()

    return "error", f"Unknown verdict: {verdict_line}"


def codex_review_story(
    story_id: int,
    story_name: str,
    story_description: str,
    acceptance_criteria: list[str],
    diff: str,
    project_dir: Path,
    tech_stack: str = "",
    dod_checklist: list[str] | None = None,
    attempt: int = 1,
    model: str | None = None,
    reasoning: str | None = None,
) -> ReviewVerdict:
    """Run a single Codex review on a story.

    This is the base call. For retry-on-error semantics use review_with_retry().

    Args:
        story_id: Numeric story ID.
        story_name: Short title.
        story_description: Full description.
        acceptance_criteria: List of AC strings.
        diff: Implementation diff (git diff output or file contents).
        project_dir: Project root directory where Codex should run.
        tech_stack: Tech stack description (optional).
        dod_checklist: Custom DoD list (optional, uses default if None).
        attempt: Current attempt number (for retry tracking).
        model: Override model (default from env or DEFAULT_CODEX_MODEL).
        reasoning: Override reasoning effort.

    Returns:
        ReviewVerdict with status, notes, timing.
    """
    model = model or os.environ.get(CODEX_MODEL_ENV, DEFAULT_CODEX_MODEL)
    reasoning = reasoning or os.environ.get(CODEX_REASONING_ENV, DEFAULT_REASONING_EFFORT)

    prompt = build_review_prompt(
        story_id=story_id,
        story_name=story_name,
        story_description=story_description,
        acceptance_criteria=acceptance_criteria,
        diff=diff,
        tech_stack=tech_stack,
        dod_checklist=dod_checklist,
    )

    start = datetime.now(timezone.utc)
    return_code, stdout, stderr = _run_codex(
        prompt=prompt,
        project_dir=project_dir,
        model=model,
        reasoning=reasoning,
    )
    duration = (datetime.now(timezone.utc) - start).total_seconds()

    if return_code != 0:
        return ReviewVerdict(
            story_id=story_id,
            status="error",
            notes=f"Codex exec failed (rc={return_code}): {stderr[:500]}",
            attempt=attempt,
            model=model,
            reasoning=reasoning,
            duration_seconds=duration,
            raw_output=stdout,
            errors=[stderr],
        )

    status, notes = _parse_verdict(stdout)
    return ReviewVerdict(
        story_id=story_id,
        status=status,
        notes=notes,
        attempt=attempt,
        model=model,
        reasoning=reasoning,
        duration_seconds=duration,
        raw_output=stdout,
    )


# ============================================================================
# Task 1.11 — Retry flow: reject → retry max 3x → escalatie
# ============================================================================


def review_with_retry(
    story_id: int,
    story_name: str,
    story_description: str,
    acceptance_criteria: list[str],
    diff_fn,
    project_dir: Path,
    tech_stack: str = "",
    dod_checklist: list[str] | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    on_retry=None,
) -> ReviewVerdict:
    """Run Codex review with retry-on-reject logic.

    Task 1.11 implementation:
    - Attempt 1: run review. If APPROVED → return. If REJECTED → retry.
    - Attempts 2, 3: coding agent gets reject notes and tries to fix, then we
      re-review. This function doesn't call the coding agent itself — the
      caller (orchestrator) is responsible for that round-trip. This function
      only runs the *review* side of the loop, but tracks attempt count so the
      caller can enforce the max and escalate.
    - After max_retries consecutive REJECTED verdicts → escalate.
    - Any "error" status is NOT counted as a retry — transient errors are
      retried in-place with exponential backoff (future: now just 1 extra try).

    Args:
        story_id, story_name, story_description, acceptance_criteria: as codex_review_story
        diff_fn: Callable[[], str] that returns the current diff. Called on each
            attempt so retries see fresh code (after coding agent fixed things).
        project_dir: Project root
        tech_stack, dod_checklist: optional
        max_retries: Max REJECTED verdicts before escalation (default 3).
        on_retry: Optional callable[[ReviewVerdict], None] called after each
            rejected verdict, before the next attempt. Orchestrator uses this
            to trigger the coding agent retry with reject notes as context.

    Returns:
        Final ReviewVerdict. Status is one of:
        - approved: AC met, done
        - escalate: max retries exhausted, human needed
        - error: Codex or system error that couldn't be recovered
    """
    if max_retries < 1:
        max_retries = 1

    last_verdict: ReviewVerdict | None = None

    for attempt in range(1, max_retries + 1):
        # Fetch fresh diff on each attempt — coding agent may have fixed things
        current_diff = diff_fn()

        verdict = codex_review_story(
            story_id=story_id,
            story_name=story_name,
            story_description=story_description,
            acceptance_criteria=acceptance_criteria,
            diff=current_diff,
            project_dir=project_dir,
            tech_stack=tech_stack,
            dod_checklist=dod_checklist,
            attempt=attempt,
        )
        last_verdict = verdict

        if verdict.status == "approved":
            return verdict

        if verdict.status == "error":
            # Single transient retry on error, then give up and escalate
            if attempt < max_retries:
                continue
            verdict.status = "escalate"
            verdict.notes = (
                f"Codex review errored at attempt {attempt}/{max_retries}. "
                f"Last error: {verdict.notes[:200]}. Escalating to human."
            )
            return verdict

        # status == "rejected"
        if attempt >= max_retries:
            verdict.status = "escalate"
            verdict.notes = (
                f"Rejected after {attempt} attempts. Escalating to human.\n\n"
                f"Last reject notes:\n{verdict.notes}"
            )
            return verdict

        # Not the last attempt: call on_retry hook so the coding agent can fix
        if on_retry is not None:
            try:
                on_retry(verdict)
            except Exception as e:
                # If the hook fails, we still continue — but note the error
                verdict.errors.append(f"on_retry hook failed: {e}")

    # Fallthrough (shouldn't hit with correct max_retries >= 1)
    if last_verdict is None:
        return ReviewVerdict(
            story_id=story_id,
            status="error",
            notes="No review attempts were made (max_retries < 1?)",
        )
    return last_verdict
