"""
Git Worktree Manager
====================

Manages git worktrees for parallel agent isolation.

Each agent in parallel mode can optionally work in its own git worktree,
preventing file conflicts when multiple agents edit the same codebase.

Lifecycle:
1. create_worktree() -- creates a new worktree + branch from HEAD
2. Agent works in the worktree directory
3. merge_worktree() -- merges changes back to the main branch
4. cleanup_worktree() -- removes the worktree and branch

Worktrees are stored in .mq-devengine/worktrees/<agent-id>/ within the
project directory.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

WORKTREE_DIR_NAME = "worktrees"


def _worktrees_root(project_dir: Path) -> Path:
    """Get the root directory for worktrees."""
    return project_dir / ".mq-devengine" / WORKTREE_DIR_NAME


async def _run_git(
    *args: str,
    cwd: Path,
    check: bool = True,
) -> tuple[int, str, str]:
    """Run a git command asynchronously.

    Returns (returncode, stdout, stderr).
    """
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stdout_str = stdout.decode().strip() if stdout else ""
    stderr_str = stderr.decode().strip() if stderr else ""

    if check and proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (rc={proc.returncode}): {stderr_str}"
        )

    return proc.returncode, stdout_str, stderr_str


async def create_feature_checkpoint(project_dir: Path, feature_id: int, phase: str) -> str:
    """Create lightweight git tag as checkpoint anchor.

    phase: 'pre' (before feature start) or 'post' (after successful build).
    Returns the tag name. Idempotent via -f flag.
    """
    tag = f"mq-cp-{feature_id}-{phase}"
    await _run_git("tag", "-f", tag, cwd=project_dir, check=False)
    return tag


def create_feature_checkpoint_sync(project_dir: Path, feature_id: int, phase: str) -> str:
    """Create lightweight git tag as checkpoint anchor (sync version).

    Use this in synchronous orchestrator context where await is not available.
    phase: 'pre' (before feature start) or 'post' (after successful build).
    """
    import subprocess  # noqa: PLC0415
    tag = f"mq-cp-{feature_id}-{phase}"
    subprocess.run(["git", "tag", "-f", tag], cwd=str(project_dir), capture_output=True)  # noqa: S603, S607
    return tag


async def list_feature_checkpoints(project_dir: Path) -> list[dict]:
    """List all mq-cp-* tags with timestamps.

    Returns list of dicts with keys: feature_id, phase, tag, timestamp.
    Sorted by creation date (newest first).
    """
    rc, stdout, _ = await _run_git(
        "tag", "-l", "mq-cp-*", "--sort=-creatordate",
        "--format=%(refname:short)|%(creatordate:iso)",
        cwd=project_dir, check=False,
    )
    result = []
    if rc != 0 or not stdout:
        return result
    for line in stdout.splitlines():
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        tag, timestamp = parts
        # Parse tag: mq-cp-{feature_id}-{phase}
        segments = tag.split("-")
        if len(segments) >= 4 and segments[0] == "mq" and segments[1] == "cp":
            try:
                feature_id = int(segments[2])
                phase = segments[3]
                result.append({
                    "feature_id": feature_id,
                    "phase": phase,
                    "tag": tag,
                    "timestamp": timestamp,
                })
            except ValueError:
                continue
    return result


async def rollback_to_checkpoint(project_dir: Path, feature_id: int) -> bool:
    """Hard reset to mq-cp-{feature_id}-pre tag.

    Returns False if the pre-tag does not exist.
    WARNING: This is a destructive operation — all uncommitted changes will be lost.
    """
    tag = f"mq-cp-{feature_id}-pre"
    rc, _, _ = await _run_git("reset", "--hard", tag, cwd=project_dir, check=False)
    return rc == 0


async def is_git_repo(project_dir: Path) -> bool:
    """Check if the project directory is a git repository."""
    rc, _, _ = await _run_git("rev-parse", "--git-dir", cwd=project_dir, check=False)
    return rc == 0


async def create_worktree(
    project_dir: Path,
    agent_id: str,
    base_ref: str = "HEAD",
) -> Path:
    """Create a git worktree for an agent.

    Args:
        project_dir: The main project directory.
        agent_id: Unique identifier for the agent (used for branch name).
        base_ref: Git ref to base the worktree on (default: HEAD).

    Returns:
        Path to the new worktree directory.

    Raises:
        RuntimeError: If git operations fail or not a git repo.
    """
    if not await is_git_repo(project_dir):
        raise RuntimeError(f"{project_dir} is not a git repository")

    worktree_path = _worktrees_root(project_dir) / agent_id
    branch_name = f"mq-agent/{agent_id}"

    # Clean up any stale worktree at this path
    if worktree_path.exists():
        logger.warning("Stale worktree found at %s, cleaning up", worktree_path)
        await cleanup_worktree(project_dir, agent_id)

    # Create worktree with a new branch
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    await _run_git(
        "worktree", "add", "-b", branch_name,
        str(worktree_path), base_ref,
        cwd=project_dir,
    )

    logger.info(
        "Created worktree for agent '%s' at %s (branch: %s)",
        agent_id, worktree_path, branch_name,
    )
    return worktree_path


async def merge_worktree(
    project_dir: Path,
    agent_id: str,
    target_branch: str | None = None,
) -> bool:
    """Merge worktree changes back to the main branch.

    Args:
        project_dir: The main project directory.
        agent_id: Agent identifier (matches create_worktree call).
        target_branch: Branch to merge into (default: current branch).

    Returns:
        True if merge succeeded, False if there were conflicts.
    """
    branch_name = f"mq-agent/{agent_id}"

    if target_branch is None:
        _, target_branch, _ = await _run_git(
            "branch", "--show-current", cwd=project_dir,
        )

    # Check if there are any commits on the agent branch
    rc, diff_output, _ = await _run_git(
        "log", f"{target_branch}..{branch_name}", "--oneline",
        cwd=project_dir, check=False,
    )
    if rc != 0 or not diff_output:
        logger.info("No changes to merge from agent '%s'", agent_id)
        return True

    # Attempt merge
    rc, stdout, stderr = await _run_git(
        "merge", "--no-ff", branch_name,
        "-m", f"Merge agent {agent_id} changes",
        cwd=project_dir, check=False,
    )

    if rc != 0:
        logger.error("Merge conflict for agent '%s': %s", agent_id, stderr)
        # Abort the failed merge
        await _run_git("merge", "--abort", cwd=project_dir, check=False)
        return False

    logger.info("Merged agent '%s' changes into %s", agent_id, target_branch)
    return True


async def cleanup_worktree(project_dir: Path, agent_id: str) -> None:
    """Remove a worktree and its branch.

    Safe to call even if the worktree doesn't exist.
    """
    worktree_path = _worktrees_root(project_dir) / agent_id
    branch_name = f"mq-agent/{agent_id}"

    # Remove worktree
    if worktree_path.exists():
        await _run_git(
            "worktree", "remove", "--force", str(worktree_path),
            cwd=project_dir, check=False,
        )
        # Fallback: remove directory if git worktree remove failed
        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)

    # Prune stale worktrees
    await _run_git("worktree", "prune", cwd=project_dir, check=False)

    # Delete the branch
    await _run_git(
        "branch", "-D", branch_name,
        cwd=project_dir, check=False,
    )

    logger.info("Cleaned up worktree for agent '%s'", agent_id)


async def list_worktrees(project_dir: Path) -> list[dict[str, str]]:
    """List all active worktrees for a project.

    Returns list of dicts with 'path', 'branch', and 'head' keys.
    """
    rc, stdout, _ = await _run_git(
        "worktree", "list", "--porcelain",
        cwd=project_dir, check=False,
    )
    if rc != 0 or not stdout:
        return []

    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:]

    if current:
        worktrees.append(current)

    # Filter to only mq-agent worktrees
    return [w for w in worktrees if w.get("branch", "").startswith("refs/heads/mq-agent/")]
