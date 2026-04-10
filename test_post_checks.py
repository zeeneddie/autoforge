"""Tests for post_checks.py — Sprint 0 post-check runner."""

from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import pytest

from post_checks import (
    CheckResult,
    PostCheckReport,
    PostCheckRunner,
    load_checks_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal Python project for testing."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello() -> str:\n    return 'hi'\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text(
        "from src.main import hello\n\ndef test_hello():\n    assert hello() == 'hi'\n"
    )
    return tmp_path


@pytest.fixture
def tmp_project_with_mocks(tmp_project: Path) -> Path:
    """Project with mock data violations in production code."""
    (tmp_project / "src" / "api.py").write_text(
        textwrap.dedent("""\
        fake_data = {"user": "test"}
        mock_response = [1, 2, 3]

        def get_users():
            return fake_data
        """)
    )
    return tmp_project


@pytest.fixture
def tmp_project_clean(tmp_project: Path) -> Path:
    """Project with no mock violations."""
    (tmp_project / "src" / "clean.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n"
    )
    return tmp_project


# ---------------------------------------------------------------------------
# CheckResult tests
# ---------------------------------------------------------------------------

class TestCheckResult:
    def test_to_dict(self):
        r = CheckResult(name="lint", passed=True, output="ok", duration_ms=42)
        d = r.to_dict()
        assert d["name"] == "lint"
        assert d["passed"] is True
        assert d["duration_ms"] == 42

    def test_skipped(self):
        r = CheckResult(name="lint", passed=True, skipped=True)
        assert r.skipped


# ---------------------------------------------------------------------------
# PostCheckReport tests
# ---------------------------------------------------------------------------

class TestPostCheckReport:
    def test_all_passed(self):
        report = PostCheckReport(checks=[
            CheckResult(name="lint", passed=True),
            CheckResult(name="tests", passed=True),
        ])
        assert report.passed is True
        assert report.failed_checks == []

    def test_one_failed(self):
        report = PostCheckReport(checks=[
            CheckResult(name="lint", passed=True),
            CheckResult(name="tests", passed=False, error="1 failed"),
        ])
        assert report.passed is False
        assert len(report.failed_checks) == 1
        assert report.failed_checks[0].name == "tests"

    def test_skipped_counts_as_passed(self):
        report = PostCheckReport(checks=[
            CheckResult(name="lint", passed=True, skipped=True),
            CheckResult(name="tests", passed=True),
        ])
        assert report.passed is True

    def test_error_context_formatting(self):
        report = PostCheckReport(checks=[
            CheckResult(name="lint", passed=False, error="E501 line too long"),
            CheckResult(name="tests", passed=False, output="FAILED test_x"),
        ])
        ctx = report.error_context()
        assert "POST-CHECK FAILED: lint" in ctx
        assert "E501 line too long" in ctx
        assert "POST-CHECK FAILED: tests" in ctx
        assert "FAILED test_x" in ctx

    def test_error_context_truncates(self):
        long_output = "\n".join(f"line {i}" for i in range(200))
        report = PostCheckReport(checks=[
            CheckResult(name="tests", passed=False, output=long_output),
        ])
        ctx = report.error_context(max_lines=10)
        # Should contain last 10 lines, not all 200
        assert "line 199" in ctx
        assert "line 0" not in ctx

    def test_to_dict(self):
        report = PostCheckReport(checks=[
            CheckResult(name="lint", passed=True),
        ])
        d = report.to_dict()
        assert d["passed"] is True
        assert len(d["checks"]) == 1


# ---------------------------------------------------------------------------
# Config loading tests
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_default(self, tmp_path: Path):
        cfg = load_checks_config(tmp_path)
        assert "lint" in cfg
        assert cfg["lint"]["tool"] == "ruff"

    def test_project_overrides(self, tmp_path: Path):
        devengine_dir = tmp_path / ".mq-devengine"
        devengine_dir.mkdir()
        (devengine_dir / "checks.yaml").write_text(
            "lint:\n  enabled: false\n  tool: flake8\n"
        )
        cfg = load_checks_config(tmp_path)
        assert cfg["lint"]["enabled"] is False
        assert cfg["lint"]["tool"] == "flake8"
        # Other sections should still have defaults
        assert "mock_detection" in cfg

    def test_missing_project_config(self, tmp_path: Path):
        cfg = load_checks_config(tmp_path)
        assert cfg["lint"]["enabled"] is True


# ---------------------------------------------------------------------------
# Lint check tests
# ---------------------------------------------------------------------------

class TestLintCheck:
    def test_lint_passes_clean_code(self, tmp_project: Path):
        runner = PostCheckRunner(tmp_project)
        result = asyncio.run(runner._check_lint())
        assert result.name == "lint"
        assert result.passed is True

    def test_lint_fails_bad_code(self, tmp_path: Path):
        (tmp_path / "bad.py").write_text("import os\nimport sys\nx=1\n")
        runner = PostCheckRunner(tmp_path)
        result = asyncio.run(runner._check_lint())
        assert result.name == "lint"
        assert result.passed is False

    def test_lint_disabled(self, tmp_project: Path):
        runner = PostCheckRunner(
            tmp_project, config={"lint": {"enabled": False}}
        )
        result = asyncio.run(runner._check_lint())
        assert result.skipped is True

    def test_lint_measures_duration(self, tmp_project: Path):
        runner = PostCheckRunner(tmp_project)
        result = asyncio.run(runner._check_lint())
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Mock detection tests
# ---------------------------------------------------------------------------

class TestMockDetection:
    def test_detects_mock_data(self, tmp_project_with_mocks: Path):
        runner = PostCheckRunner(tmp_project_with_mocks)
        result = asyncio.run(runner._check_mock_detection())
        assert result.passed is False
        assert "fake_data" in result.output
        assert "mock_response" in result.output

    def test_clean_code_passes(self, tmp_project_clean: Path):
        runner = PostCheckRunner(tmp_project_clean)
        result = asyncio.run(runner._check_mock_detection())
        assert result.passed is True

    def test_excludes_test_dirs(self, tmp_project: Path):
        # Mock patterns in test files should NOT trigger violations
        (tmp_project / "tests" / "test_api.py").write_text(
            "mock_response = {'status': 200}\n"
        )
        runner = PostCheckRunner(tmp_project)
        result = asyncio.run(runner._check_mock_detection())
        assert result.passed is True

    def test_disabled(self, tmp_project_with_mocks: Path):
        runner = PostCheckRunner(
            tmp_project_with_mocks,
            config={"mock_detection": {"enabled": False}},
        )
        result = asyncio.run(runner._check_mock_detection())
        assert result.skipped is True

    def test_no_scan_dirs_exist(self, tmp_path: Path):
        runner = PostCheckRunner(tmp_path)
        result = asyncio.run(runner._check_mock_detection())
        # No src/app/lib/server dirs → passes (nothing to scan)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Test suite execution tests
# ---------------------------------------------------------------------------

class TestTestSuite:
    def test_detects_pytest(self, tmp_project: Path):
        runner = PostCheckRunner(tmp_project)
        result = asyncio.run(runner._check_tests())
        assert result.name == "tests"
        # May pass or fail depending on imports — we care it runs
        assert not result.skipped

    def test_no_test_runner_detected(self, tmp_path: Path):
        runner = PostCheckRunner(tmp_path)
        result = asyncio.run(runner._check_tests())
        assert result.passed is False
        assert "No test runner detected" in result.error

    def test_disabled(self, tmp_project: Path):
        runner = PostCheckRunner(
            tmp_project, config={"tests": {"enabled": False}}
        )
        result = asyncio.run(runner._check_tests())
        assert result.skipped is True


# ---------------------------------------------------------------------------
# Coverage check tests
# ---------------------------------------------------------------------------

class TestCoverage:
    def test_no_coverage_tool(self, tmp_path: Path):
        runner = PostCheckRunner(tmp_path)
        result = asyncio.run(runner._check_coverage())
        assert result.skipped is True

    def test_disabled(self, tmp_project: Path):
        runner = PostCheckRunner(
            tmp_project, config={"coverage": {"enabled": False}}
        )
        result = asyncio.run(runner._check_coverage())
        assert result.skipped is True

    def test_parse_pytest_cov_stdout(self, tmp_project: Path):
        runner = PostCheckRunner(tmp_project)
        pct = runner._parse_coverage(None, "TOTAL    500    50    90%")
        assert pct == 90.0

    def test_parse_vitest_stdout(self, tmp_project: Path):
        runner = PostCheckRunner(tmp_project)
        pct = runner._parse_coverage(None, "All files  |   85.5 |   70.2 |")
        assert pct == 85.5

    def test_parse_json_report_pytest(self, tmp_project: Path):
        report = tmp_project / "coverage.json"
        report.write_text(json.dumps({"totals": {"percent_covered": 92.3}}))
        runner = PostCheckRunner(tmp_project)
        pct = runner._parse_coverage("coverage.json", "")
        assert pct == 92.3

    def test_parse_json_report_istanbul(self, tmp_project: Path):
        cov_dir = tmp_project / "coverage"
        cov_dir.mkdir()
        (cov_dir / "coverage-final.json").write_text(
            json.dumps({"total": {"statements": {"pct": 88.1}}})
        )
        runner = PostCheckRunner(tmp_project)
        pct = runner._parse_coverage("coverage/coverage-final.json", "")
        assert pct == 88.1

    def test_threshold_pass(self, tmp_project: Path):
        """Coverage above threshold passes."""
        runner = PostCheckRunner(
            tmp_project,
            config={
                "coverage": {
                    "enabled": True,
                    "threshold": 80,
                    "commands": [{
                        "detect": "pyproject.toml",
                        "run": ["echo", "TOTAL    100    10    90%"],
                        "report": None,
                    }],
                }
            },
        )
        result = asyncio.run(runner._check_coverage())
        # echo returns 0 and outputs the TOTAL line
        assert result.passed is True

    def test_threshold_fail(self, tmp_project: Path):
        """Coverage below threshold fails."""
        runner = PostCheckRunner(
            tmp_project,
            config={
                "coverage": {
                    "enabled": True,
                    "threshold": 95,
                    "commands": [{
                        "detect": "pyproject.toml",
                        "run": ["echo", "TOTAL    100    30    70%"],
                        "report": None,
                    }],
                }
            },
        )
        result = asyncio.run(runner._check_coverage())
        assert result.passed is False


# ---------------------------------------------------------------------------
# Full run_all integration tests
# ---------------------------------------------------------------------------

class TestRunAll:
    def test_stops_on_first_failure(self, tmp_path: Path):
        """If lint fails, tests and coverage should NOT run."""
        (tmp_path / "bad.py").write_text("import os\nimport sys\nx=1\n")
        runner = PostCheckRunner(tmp_path)
        report = asyncio.run(runner.run_all())
        assert report.passed is False
        # Should have run lint (failed) and stopped
        names = [c.name for c in report.checks]
        assert "lint" in names
        # tests and coverage should NOT be in the list
        assert "coverage" not in names

    def test_all_disabled_passes(self, tmp_path: Path):
        runner = PostCheckRunner(tmp_path, config={
            "lint": {"enabled": False},
            "mock_detection": {"enabled": False},
            "tests": {"enabled": False},
            "coverage": {"enabled": False},
        })
        report = asyncio.run(runner.run_all())
        assert report.passed is True
        assert all(c.skipped for c in report.checks)

    def test_report_serializable(self, tmp_project: Path):
        runner = PostCheckRunner(tmp_project, config={
            "lint": {"enabled": True, "tool": "ruff", "args": ["check", "."], "extra_args": []},
            "mock_detection": {"enabled": False},
            "tests": {"enabled": False},
            "coverage": {"enabled": False},
        })
        report = asyncio.run(runner.run_all())
        d = report.to_dict()
        # Must be JSON-serializable
        serialized = json.dumps(d)
        assert '"passed"' in serialized
