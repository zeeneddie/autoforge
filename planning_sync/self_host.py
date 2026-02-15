"""Self-hosting setup: register MQ DevEngine as a project in its own registry."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Marker files that identify the MQ DevEngine project root
_MARKER_FILES = [
    "server/main.py",
    "parallel_orchestrator.py",
    "planning_sync/__init__.py",
]


def detect_devengine_root(start: Path | None = None) -> Path | None:
    """Detect the MQ DevEngine project root by checking for marker files.

    Walks up from *start* (default: this file's grandparent) looking for a
    directory that contains all marker files.

    Returns the root Path, or None if not found.
    """
    if start is None:
        start = Path(__file__).resolve().parent.parent

    candidate = start.resolve()
    for _ in range(10):  # limit traversal depth
        if all((candidate / m).exists() for m in _MARKER_FILES):
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent

    return None


def setup_self_host(project_name: str = "mq-devengine") -> dict:
    """Register MQ DevEngine in its own project registry (idempotent).

    Returns a dict with keys:
        - project_name: str
        - project_path: str
        - already_registered: bool
    """
    root = detect_devengine_root()
    if root is None:
        raise RuntimeError("Cannot detect MQ DevEngine project root")

    # Ensure registry module is importable
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from registry import register_project, get_project_path, RegistryError

    existing = get_project_path(project_name)
    if existing is not None:
        logger.info("MQ DevEngine already registered as '%s' at %s", project_name, existing)
        return {
            "project_name": project_name,
            "project_path": str(existing),
            "already_registered": True,
        }

    try:
        register_project(project_name, root)
    except RegistryError:
        # Race condition: another call registered between check and register
        existing = get_project_path(project_name)
        return {
            "project_name": project_name,
            "project_path": str(existing) if existing else str(root),
            "already_registered": True,
        }

    logger.info("Registered MQ DevEngine as '%s' at %s", project_name, root)
    return {
        "project_name": project_name,
        "project_path": str(root),
        "already_registered": False,
    }
