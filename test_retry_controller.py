"""Tests for retry_controller.py — retry loop + WebSocket events."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from retry_controller import (
    PostCheckEvent,
    RetryController,
    RetryOutcome,
)
from post_checks import CheckResult, PostCheckReport


# ---------------------------------------------------------------------------
# RetryOutcome tests
# ---------------------------------------------------------------------------

class TestRetryOutcome:
    def test_passed(self):
        outcome = RetryOutcome(
            feature_id=42,
            final_passed=True,
            attempts=[PostCheckReport(checks=[
                CheckResult(name="lint", passed=True),
            ])],
        )
        assert outcome.final_passed is True
        assert outcome.attempt_count == 1
        assert outcome.escalation_reason is None

    def test_failed_with_reason(self):
        outcome = RetryOutcome(
            feature_id=42,
            final_passed=False,
            attempts=[
                PostCheckReport(checks=[
                    CheckResult(name="lint", passed=True),
                    CheckResult(name="tests", passed=False),
                ]),
                PostCheckReport(checks=[
                    CheckResult(name="lint", passed=True),
                    CheckResult(name="tests", passed=False),
                ]),
            ],
        )
        assert outcome.attempt_count == 2
        assert "tests" in outcome.escalation_reason
        assert "2 attempt(s)" in outcome.escalation_reason

    def test_to_dict_serializable(self):
        outcome = RetryOutcome(
            feature_id=1,
            final_passed=True,
            attempts=[PostCheckReport(checks=[
                CheckResult(name="lint", passed=True),
            ])],
            total_duration_ms=100,
        )
        d = outcome.to_dict()
        serialized = json.dumps(d)
        assert '"feature_id": 1' in serialized
        assert '"final_passed": true' in serialized


# ---------------------------------------------------------------------------
# PostCheckEvent tests
# ---------------------------------------------------------------------------

class TestPostCheckEvent:
    def test_ws_message_format(self):
        event = PostCheckEvent(
            feature_id=42,
            event_type="check_done",
            check_name="lint",
            passed=True,
            attempt=1,
            max_attempts=3,
            detail="ok",
        )
        msg = event.to_ws_message()
        assert msg["type"] == "post_check_update"
        assert msg["feature_id"] == 42
        assert msg["event"] == "check_done"
        assert msg["check_name"] == "lint"
        assert msg["passed"] is True

    def test_ws_message_serializable(self):
        event = PostCheckEvent(
            feature_id=1,
            event_type="retry",
            attempt=2,
            max_attempts=3,
        )
        msg = event.to_ws_message()
        json.dumps(msg)  # should not raise


# ---------------------------------------------------------------------------
# RetryController tests
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_project(tmp_path: Path) -> Path:
    """Minimal project that passes all checks."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello() -> str:\n    return 'hi'\n")
    return tmp_path


@pytest.fixture
def failing_project(tmp_path: Path) -> Path:
    """Project with lint errors."""
    (tmp_path / "bad.py").write_text("import os\nimport sys\nx=1\n")
    return tmp_path


class TestRetryController:
    def test_passes_first_try(self, clean_project: Path):
        events: list[PostCheckEvent] = []

        async def collect(e: PostCheckEvent) -> None:
            events.append(e)

        controller = RetryController(
            clean_project,
            config={
                "lint": {"enabled": True, "tool": "ruff", "args": ["check", "."], "extra_args": []},
                "mock_detection": {"enabled": False},
                "tests": {"enabled": False},
                "coverage": {"enabled": False},
                "retry": {"max_attempts": 3},
            },
            on_event=collect,
        )
        outcome = asyncio.run(controller.run_with_retry(feature_id=1))

        assert outcome.final_passed is True
        assert outcome.attempt_count == 1
        assert outcome.total_duration_ms >= 0

        # Should have: check_start, check_done(lint), complete
        event_types = [e.event_type for e in events]
        assert "check_start" in event_types
        assert "check_done" in event_types
        assert "complete" in event_types
        assert "retry" not in event_types

    def test_fails_all_retries(self, failing_project: Path):
        events: list[PostCheckEvent] = []

        async def collect(e: PostCheckEvent) -> None:
            events.append(e)

        controller = RetryController(
            failing_project,
            config={
                "lint": {"enabled": True, "tool": "ruff", "args": ["check", "."], "extra_args": []},
                "mock_detection": {"enabled": False},
                "tests": {"enabled": False},
                "coverage": {"enabled": False},
                "retry": {"max_attempts": 2},
            },
            on_event=collect,
        )
        outcome = asyncio.run(controller.run_with_retry(feature_id=99))

        assert outcome.final_passed is False
        assert outcome.attempt_count == 2
        assert outcome.escalation_reason is not None
        assert "lint" in outcome.escalation_reason

        # Should have retry events
        event_types = [e.event_type for e in events]
        assert event_types.count("check_start") == 2
        assert "retry" in event_types

    def test_max_attempts_respected(self, failing_project: Path):
        controller = RetryController(
            failing_project,
            config={
                "lint": {"enabled": True, "tool": "ruff", "args": ["check", "."], "extra_args": []},
                "mock_detection": {"enabled": False},
                "tests": {"enabled": False},
                "coverage": {"enabled": False},
                "retry": {"max_attempts": 1},
            },
        )
        outcome = asyncio.run(controller.run_with_retry(feature_id=5))
        assert outcome.attempt_count == 1
        assert outcome.final_passed is False

    def test_event_callback_receives_all_events(self, clean_project: Path):
        callback = AsyncMock()
        controller = RetryController(
            clean_project,
            config={
                "lint": {"enabled": True, "tool": "ruff", "args": ["check", "."], "extra_args": []},
                "mock_detection": {"enabled": False},
                "tests": {"enabled": False},
                "coverage": {"enabled": False},
                "retry": {"max_attempts": 3},
            },
            on_event=callback,
        )
        asyncio.run(controller.run_with_retry(feature_id=1))
        assert callback.call_count >= 3  # start + check_done + complete

    def test_format_retry_prompt_with_errors(self):
        report = PostCheckReport(checks=[
            CheckResult(name="lint", passed=False, error="E501 line too long"),
        ])
        controller = RetryController(
            "/tmp/fake",
            config={"retry": {"include_error_output": True, "max_error_lines": 50}},
        )
        prompt = controller.format_retry_prompt(report)
        assert "POST-CHECK FAILED: lint" in prompt
        assert "E501 line too long" in prompt
        assert "Fix the issues" in prompt

    def test_format_retry_prompt_without_errors(self):
        report = PostCheckReport(checks=[
            CheckResult(name="lint", passed=False, error="some error"),
        ])
        controller = RetryController(
            "/tmp/fake",
            config={"retry": {"include_error_output": False}},
        )
        prompt = controller.format_retry_prompt(report)
        assert "Post-checks failed: lint" in prompt
        assert "some error" not in prompt

    def test_default_config_from_project(self, clean_project: Path):
        """Controller loads checks.yaml defaults when no config passed."""
        controller = RetryController(clean_project)
        assert controller.max_attempts == 3


# ---------------------------------------------------------------------------
# YOLO removal spec (no code to test — this is the design contract)
# ---------------------------------------------------------------------------

class TestYoloRemovalSpec:
    """
    YOLO mode removal specification (task 0.8).

    These tests document what needs to change in mq-devEngine.
    They are markers, not functional tests.
    """

    def test_spec_cli_flag_removed(self):
        """autonomous_agent_demo.py: remove --yolo argument."""
        # After removal:
        # - argparse no longer accepts --yolo
        # - client.create_client() no longer has yolo_mode param
        # - Playwright MCP always loaded (testing agents always available)
        pass

    def test_spec_settings_toggle_removed(self):
        """SettingsModal.tsx: remove YOLO mode toggle from UI."""
        # After removal:
        # - No yolo_mode in project settings API
        # - No toggle in SettingsModal
        # - Registry DB: yolo column can be dropped or ignored
        pass

    def test_spec_post_checks_replace_yolo(self):
        """Post-checks are the new quality gate — YOLO is redundant."""
        # The post-check system (checks.yaml) allows per-project
        # configuration. Projects that want lighter checks can:
        # - Disable coverage: coverage.enabled = false
        # - Disable mock detection: mock_detection.enabled = false
        # This replaces YOLO's purpose without removing all gates.
        pass
