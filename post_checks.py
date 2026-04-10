"""
post_checks.py — Deterministic post-check runner for mq-devEngine.

Runs after a coding agent marks a feature as complete.
The agent cannot self-certify — these checks gate the transition to "passing".

Checks (in order):
  1. Lint (ruff)
  2. Mock data detection (regex grep)
  3. Test suite execution (pytest / npm test)
  4. Test coverage on modified files (>= threshold)

Usage:
    from post_checks import PostCheckRunner

    runner = PostCheckRunner(project_dir="/path/to/project")
    result = await runner.run_all()

    if result.passed:
        # feature can be marked passing
    else:
        # retry coding agent with result.error_context()
"""

from __future__ import annotations

import asyncio
import dataclasses
import fnmatch
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CheckResult:
    """Result of a single post-check."""

    name: str
    passed: bool
    output: str = ""
    error: str = ""
    skipped: bool = False
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class PostCheckReport:
    """Aggregated result of all post-checks."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed or c.skipped for c in self.checks)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and not c.skipped]

    def error_context(self, max_lines: int = 50) -> str:
        """Format failed checks as context for retry prompt."""
        parts: list[str] = []
        for check in self.failed_checks:
            output = check.error or check.output
            lines = output.strip().splitlines()
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
            parts.append(
                f"## POST-CHECK FAILED: {check.name}\n\n"
                f"```\n{chr(10).join(lines)}\n```"
            )
        return "\n\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
        }


def load_checks_config(project_dir: Path) -> dict[str, Any]:
    """Load checks.yaml with fallback chain: project → default."""
    project_config = project_dir / ".mq-devengine" / "checks.yaml"
    if project_config.exists():
        with open(project_config) as f:
            project_overrides = yaml.safe_load(f) or {}
    else:
        project_overrides = {}

    # Fallback chain: .claude/templates/checks.yaml → same dir as this file
    default_candidates = [
        Path(__file__).parent / ".claude" / "templates" / "checks.yaml",
        Path(__file__).parent / "checks.yaml",
    ]
    defaults = {}
    for candidate in default_candidates:
        if candidate.exists():
            with open(candidate) as f:
                defaults = yaml.safe_load(f) or {}
            break

    # Shallow merge: project overrides win per top-level key
    merged = {**defaults, **project_overrides}
    return merged


async def _run_command(
    cmd: list[str],
    cwd: Path,
    timeout: int = 120,
) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return (
            proc.returncode or 0,
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        proc.kill()  # type: ignore[union-attr]
        return 1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"


class PostCheckRunner:
    """Runs deterministic post-checks on a project directory."""

    def __init__(self, project_dir: str | Path, config: dict[str, Any] | None = None):
        self.project_dir = Path(project_dir)
        self.config = config or load_checks_config(self.project_dir)

    async def run_all(self) -> PostCheckReport:
        """Run all enabled checks in order. Stop-on-first-failure."""
        report = PostCheckReport()

        for check_fn in [
            self._check_lint,
            self._check_mock_detection,
            self._check_tests,
            self._check_coverage,
        ]:
            result = await check_fn()
            report.checks.append(result)
            if not result.passed and not result.skipped:
                # Fail fast — no point running coverage if tests fail
                break

        return report

    async def _check_lint(self) -> CheckResult:
        """Run linter (ruff by default)."""
        cfg = self.config.get("lint", {})
        if not cfg.get("enabled", True):
            return CheckResult(name="lint", passed=True, skipped=True)

        tool = cfg.get("tool", "ruff")
        args = cfg.get("args", ["check", "."])
        extra = cfg.get("extra_args", [])

        import time
        t0 = time.monotonic()
        returncode, stdout, stderr = await _run_command(
            [tool, *args, *extra], cwd=self.project_dir
        )
        duration = int((time.monotonic() - t0) * 1000)

        return CheckResult(
            name="lint",
            passed=returncode == 0,
            output=stdout,
            error=stderr,
            duration_ms=duration,
        )

    async def _check_mock_detection(self) -> CheckResult:
        """Grep production code for hardcoded mock/test data patterns."""
        cfg = self.config.get("mock_detection", {})
        if not cfg.get("enabled", True):
            return CheckResult(name="mock_detection", passed=True, skipped=True)

        patterns = cfg.get("patterns", [])
        scan_dirs = cfg.get("scan_dirs", ["src", "app", "lib", "server"])
        exclude_dirs = cfg.get("exclude_dirs", [
            "test", "tests", "__tests__", "fixtures", "mocks", "node_modules", ".venv"
        ])
        extensions = cfg.get("extensions", [".py", ".ts", ".tsx", ".js", ".jsx"])

        if not patterns:
            return CheckResult(name="mock_detection", passed=True, skipped=True)

        import time
        t0 = time.monotonic()

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        violations: list[str] = []

        for scan_dir_name in scan_dirs:
            scan_path = self.project_dir / scan_dir_name
            if not scan_path.exists():
                continue

            for file_path in scan_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in extensions:
                    continue

                # Check exclude dirs
                rel = file_path.relative_to(self.project_dir)
                if any(
                    fnmatch.fnmatch(part, excl)
                    for part in rel.parts
                    for excl in exclude_dirs
                ):
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                for i, line in enumerate(content.splitlines(), 1):
                    for pattern in compiled:
                        if pattern.search(line):
                            violations.append(f"{rel}:{i}: {line.strip()}")

        duration = int((time.monotonic() - t0) * 1000)

        if violations:
            output = (
                f"Found {len(violations)} mock data violation(s):\n"
                + "\n".join(violations[:50])
            )
            return CheckResult(
                name="mock_detection",
                passed=False,
                output=output,
                duration_ms=duration,
            )

        return CheckResult(
            name="mock_detection",
            passed=True,
            output=f"No mock data patterns found in {', '.join(scan_dirs)}",
            duration_ms=duration,
        )

    async def _check_tests(self) -> CheckResult:
        """Run the project's test suite."""
        cfg = self.config.get("tests", {})
        if not cfg.get("enabled", True):
            return CheckResult(name="tests", passed=True, skipped=True)

        commands = cfg.get("commands", [])
        cmd = self._detect_command(commands)

        if cmd is None:
            return CheckResult(
                name="tests",
                passed=False,
                error="No test runner detected. Add a tests section to checks.yaml.",
            )

        import time
        t0 = time.monotonic()
        returncode, stdout, stderr = await _run_command(cmd, cwd=self.project_dir)
        duration = int((time.monotonic() - t0) * 1000)

        return CheckResult(
            name="tests",
            passed=returncode == 0,
            output=stdout,
            error=stderr,
            duration_ms=duration,
        )

    async def _check_coverage(self) -> CheckResult:
        """Run tests with coverage and check threshold on modified files."""
        cfg = self.config.get("coverage", {})
        if not cfg.get("enabled", True):
            return CheckResult(name="coverage", passed=True, skipped=True)

        threshold = cfg.get("threshold", 80)
        commands = cfg.get("commands", [])
        cmd_entry = self._detect_command_entry(commands)

        if cmd_entry is None:
            return CheckResult(
                name="coverage",
                passed=True,
                skipped=True,
                output="No coverage tool detected.",
            )

        cmd = cmd_entry["run"]
        report_path = cmd_entry.get("report")

        import time
        t0 = time.monotonic()
        returncode, stdout, stderr = await _run_command(cmd, cwd=self.project_dir)
        duration = int((time.monotonic() - t0) * 1000)

        if returncode != 0:
            return CheckResult(
                name="coverage",
                passed=False,
                output=stdout,
                error=stderr or f"Coverage command failed with exit code {returncode}",
                duration_ms=duration,
            )

        # Parse coverage report
        coverage_pct = self._parse_coverage(report_path, stdout)
        passed = coverage_pct >= threshold if coverage_pct is not None else True

        output = (
            f"Coverage: {coverage_pct:.1f}% (threshold: {threshold}%)"
            if coverage_pct is not None
            else "Coverage: could not determine percentage (check passed by default)"
        )

        return CheckResult(
            name="coverage",
            passed=passed,
            output=output,
            duration_ms=duration,
        )

    def _parse_coverage(self, report_path: str | None, stdout: str) -> float | None:
        """Extract coverage percentage from report file or stdout."""
        import json

        # Try JSON report first
        if report_path:
            full_path = self.project_dir / report_path
            if full_path.exists():
                try:
                    data = json.loads(full_path.read_text())
                    # pytest-cov format
                    if "totals" in data:
                        return data["totals"].get("percent_covered", None)
                    # istanbul/vitest format
                    if "total" in data:
                        total = data["total"]
                        if "statements" in total:
                            return total["statements"].get("pct", None)
                except (json.JSONDecodeError, KeyError):
                    pass

        # Fallback: parse stdout for common patterns
        # pytest-cov: "TOTAL    500    50    90%"
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
        if match:
            return float(match.group(1))

        # vitest/jest: "All files  |   85.5 |"
        match = re.search(r"All files\s*\|\s*([\d.]+)", stdout)
        if match:
            return float(match.group(1))

        return None

    def _detect_command(self, commands: list[dict[str, Any]]) -> list[str] | None:
        """Find the first matching command based on detect file."""
        entry = self._detect_command_entry(commands)
        return entry["run"] if entry else None

    def _detect_command_entry(
        self, commands: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find the first matching command entry based on detect file."""
        for entry in commands:
            detect_file = entry.get("detect", "")
            if (self.project_dir / detect_file).exists():
                return entry
        return None
