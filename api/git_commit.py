"""
Git commit per story — Sprint 1 Blok D task 1.12
==================================================

Deterministic git commit after a story transitions to 'passing'. Provides
traceability from git history back to stories, features, epics, and
ultimately to the original acceptance criteria.

## Why deterministic commits

Coding agents historically commit ad-hoc with free-form messages. That
breaks git history as an audit trail: you can't scan `git log` and find
which stories were completed when. A deterministic format enables:

1. **Traceability**: every commit has exactly one story ID in the first line
2. **Audit trail**: `git log --grep "story #42"` finds every commit for that story
3. **ISO bewijs**: every code change is linked to an acceptance criterion
4. **Automated release notes**: parse commit messages to generate changelog

## Commit message format

```
story #{id}: {story_name}

{story_description}

Acceptance criteria:
- AC1: ...
- AC2: ...

[devEngine v2 Sprint 1 task 1.12 — deterministic commit]
```

The first line starts with `story #<id>: ` so tools can parse it with regex.
The last line identifies the commit source for traceability.

## Feature flag

`DEVENGINE_GIT_COMMIT_ENABLED` env var (default `false`). When off, the
hook is a no-op so existing behavior is unchanged. When on, commits are
created automatically after successful coding agent completion.

## Gebruik (vanuit orchestrator)

```python
from api.git_commit import commit_story_if_enabled

# In _on_agent_complete after feature transitions to passes=True:
result = commit_story_if_enabled(
    project_dir=self.project_dir,
    story_id=feature.id,
    story_name=feature.name,
    story_description=feature.description,
    acceptance_criteria=feature.acceptance_criteria or [],
)
if result.committed:
    logger.info(f"Committed story #{feature.id}: {result.commit_hash[:8]}")
elif result.error:
    logger.warning(f"Git commit failed for story #{feature.id}: {result.error}")
```
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

GIT_COMMIT_ENABLED_ENV = "DEVENGINE_GIT_COMMIT_ENABLED"
GIT_COMMIT_AUTHOR_ENV = "DEVENGINE_GIT_AUTHOR"

DEFAULT_AUTHOR = "mq-devEngine <devengine@marqed.ai>"
GIT_TIMEOUT_SECONDS = 30

COMMIT_SOURCE_MARKER = "[devEngine v2 Sprint 1 task 1.12 — deterministic commit]"


def is_git_commit_enabled() -> bool:
    """Check if auto-commit is enabled via env var feature flag."""
    val = os.environ.get(GIT_COMMIT_ENABLED_ENV, "false").lower()
    return val in ("true", "1", "yes", "on")


def get_commit_author() -> str:
    """Get the configured commit author (name <email> format)."""
    return os.environ.get(GIT_COMMIT_AUTHOR_ENV, DEFAULT_AUTHOR)


# ============================================================================
# Data types
# ============================================================================


@dataclass
class CommitResult:
    """Result of a git commit attempt."""
    committed: bool
    commit_hash: str = ""
    error: str = ""
    skipped_reason: str = ""
    files_changed: int = 0
    stdout: str = ""
    stderr: str = ""


# ============================================================================
# Commit message builder
# ============================================================================


def build_commit_message(
    story_id: int,
    story_name: str,
    story_description: str = "",
    acceptance_criteria: list[str] | None = None,
) -> str:
    """Build the deterministic commit message for a story.

    Format:
        story #<id>: <name>

        <description>

        Acceptance criteria:
        - AC1: ...
        - AC2: ...

        [devEngine v2 Sprint 1 task 1.12 — deterministic commit]

    Args:
        story_id: Numeric story ID (goes in subject line).
        story_name: Short title.
        story_description: Long description (optional, goes in body).
        acceptance_criteria: List of AC strings (optional).

    Returns:
        Complete multi-line commit message.
    """
    subject = f"story #{story_id}: {story_name.strip()}"

    # Git commit subject line convention: <= 72 chars
    if len(subject) > 72:
        # Truncate the name but keep the story ID prefix intact
        max_name = 72 - len(f"story #{story_id}: ") - 1  # -1 for ellipsis
        truncated_name = story_name.strip()[:max_name]
        subject = f"story #{story_id}: {truncated_name}…"

    lines: list[str] = [subject, ""]

    if story_description.strip():
        lines.append(story_description.strip())
        lines.append("")

    if acceptance_criteria:
        lines.append("Acceptance criteria:")
        for ac in acceptance_criteria:
            lines.append(f"- {ac.strip()}")
        lines.append("")

    lines.append(COMMIT_SOURCE_MARKER)

    return "\n".join(lines)


# ============================================================================
# Git operations
# ============================================================================


def _run_git(args: list[str], cwd: Path, timeout: int = GIT_TIMEOUT_SECONDS) -> tuple[int, str, str]:
    """Run a git command and return (return_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"git {args[0]} timed out after {timeout}s"
    except FileNotFoundError:
        return 127, "", "git not found in PATH"
    except Exception as e:
        return 1, "", f"Unexpected error running git: {e}"


def _is_git_repo(cwd: Path) -> bool:
    """Check if cwd is inside a git repository."""
    rc, _, _ = _run_git(["rev-parse", "--git-dir"], cwd)
    return rc == 0


def _has_changes(cwd: Path) -> bool:
    """Check if there are uncommitted changes in the working tree."""
    rc, stdout, _ = _run_git(["status", "--porcelain"], cwd)
    if rc != 0:
        return False
    return bool(stdout.strip())


def _count_changed_files(cwd: Path) -> int:
    """Count files with uncommitted changes."""
    rc, stdout, _ = _run_git(["status", "--porcelain"], cwd)
    if rc != 0:
        return 0
    return len([line for line in stdout.splitlines() if line.strip()])


def _get_head_hash(cwd: Path) -> str:
    """Get the current HEAD commit hash."""
    rc, stdout, _ = _run_git(["rev-parse", "HEAD"], cwd)
    return stdout.strip() if rc == 0 else ""


# ============================================================================
# Main entry points
# ============================================================================


def commit_story(
    project_dir: Path,
    story_id: int,
    story_name: str,
    story_description: str = "",
    acceptance_criteria: list[str] | None = None,
    author: str | None = None,
) -> CommitResult:
    """Create a deterministic commit for a completed story.

    This is the raw commit function — it always runs regardless of the
    feature flag. For flag-gated use from the orchestrator, call
    `commit_story_if_enabled()` instead.

    Steps:
    1. Verify project_dir is a git repo. If not → skip.
    2. Check if there are uncommitted changes. If not → skip (no-op).
    3. Run `git add -A` to stage everything.
    4. Run `git commit -m "<deterministic message>"` with explicit author.
    5. Return the new HEAD hash and status.

    Args:
        project_dir: Project root directory (where git operations run).
        story_id: Numeric story ID.
        story_name: Short title.
        story_description: Long description (optional).
        acceptance_criteria: List of AC strings (optional).
        author: Override author (defaults to DEFAULT_AUTHOR via env).

    Returns:
        CommitResult with committed=True/False and commit_hash if successful.
    """
    author = author or get_commit_author()

    # Step 1: is it a git repo?
    if not _is_git_repo(project_dir):
        return CommitResult(
            committed=False,
            skipped_reason=f"{project_dir} is not a git repository",
        )

    # Step 2: are there changes to commit?
    if not _has_changes(project_dir):
        return CommitResult(
            committed=False,
            skipped_reason="no uncommitted changes (working tree clean)",
        )

    files_changed = _count_changed_files(project_dir)

    # Step 3: stage all changes
    rc, stdout_add, stderr_add = _run_git(["add", "-A"], project_dir)
    if rc != 0:
        return CommitResult(
            committed=False,
            error=f"git add failed: {stderr_add.strip()}",
            files_changed=files_changed,
        )

    # Step 4: commit with deterministic message
    message = build_commit_message(
        story_id=story_id,
        story_name=story_name,
        story_description=story_description,
        acceptance_criteria=acceptance_criteria,
    )

    commit_args = [
        "commit",
        "-m", message,
        "--author", author,
    ]
    rc, stdout_commit, stderr_commit = _run_git(commit_args, project_dir)

    if rc != 0:
        # 'nothing to commit' is sometimes returned when only staged + ignored files
        # Treat it as no-op rather than error.
        if "nothing to commit" in (stdout_commit + stderr_commit).lower():
            return CommitResult(
                committed=False,
                skipped_reason="git reported nothing to commit after add -A",
                files_changed=files_changed,
                stdout=stdout_commit,
                stderr=stderr_commit,
            )
        return CommitResult(
            committed=False,
            error=f"git commit failed: {stderr_commit.strip() or stdout_commit.strip()}",
            files_changed=files_changed,
            stdout=stdout_commit,
            stderr=stderr_commit,
        )

    # Step 5: capture the new HEAD
    head_hash = _get_head_hash(project_dir)

    return CommitResult(
        committed=True,
        commit_hash=head_hash,
        files_changed=files_changed,
        stdout=stdout_commit,
        stderr=stderr_commit,
    )


def commit_story_if_enabled(
    project_dir: Path,
    story_id: int,
    story_name: str,
    story_description: str = "",
    acceptance_criteria: list[str] | None = None,
) -> CommitResult:
    """Feature-flagged wrapper around commit_story().

    If DEVENGINE_GIT_COMMIT_ENABLED is not set to true, this is a no-op
    and returns a CommitResult with skipped_reason set.

    Call this from the orchestrator's _on_agent_complete() after verifying
    the story has transitioned to passing=True.
    """
    if not is_git_commit_enabled():
        return CommitResult(
            committed=False,
            skipped_reason=f"{GIT_COMMIT_ENABLED_ENV} not set to true (auto-commit disabled)",
        )

    return commit_story(
        project_dir=project_dir,
        story_id=story_id,
        story_name=story_name,
        story_description=story_description,
        acceptance_criteria=acceptance_criteria,
    )
