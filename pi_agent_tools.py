"""
Pi Agent Tool Proxy
===================

Executes feature management tools on behalf of Pi Agent.

When Pi Agent emits a tool_use block, the bridge intercepts it and
routes it here. This module calls the same database functions that
the MCP feature server uses, ensuring identical behavior regardless
of runtime.

Supported tools (matching MCP tool names without prefix):
- feature_get_stats
- feature_get_by_id
- feature_get_summary
- feature_claim_and_get
- feature_mark_in_progress
- feature_mark_passing
- feature_mark_failing
- feature_skip
- feature_clear_in_progress
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Ensure project root is on sys.path for api imports
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from api.database import Feature, atomic_transaction, create_database
from api.dependency_resolver import compute_scheduling_scores


def _get_db_path(project_dir: Path) -> Path:
    """Get the features.db path for a project."""
    mq_dir = project_dir / ".mq-devengine"
    db_path = mq_dir / "features.db"
    if db_path.exists():
        return db_path
    # Legacy location
    legacy = project_dir / "features.db"
    if legacy.exists():
        return legacy
    return db_path


def _ensure_db(project_dir: Path) -> str:
    """Ensure database exists and return the DB URL."""
    db_path = _get_db_path(project_dir)
    db_url = f"sqlite:///{db_path}"
    create_database(db_url)
    return db_url


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _feature_get_stats(project_dir: Path) -> dict[str, Any]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        features = session.query(Feature).all()
        total = len(features)
        passing = sum(1 for f in features if f.passes)
        in_progress = sum(1 for f in features if f.in_progress)
        pending = total - passing - in_progress
    return {
        "total": total,
        "passing": passing,
        "in_progress": in_progress,
        "pending": pending,
        "percentage": round(passing / total * 100, 1) if total else 0.0,
    }


def _feature_get_by_id(project_dir: Path, feature_id: int) -> dict[str, Any]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if not feature:
            return {"error": f"Feature {feature_id} not found"}
        return {
            "id": feature.id,
            "name": feature.name,
            "category": feature.category,
            "description": feature.description,
            "steps": json.loads(feature.steps) if isinstance(feature.steps, str) else feature.steps,
            "passes": feature.passes,
            "in_progress": feature.in_progress,
            "priority": feature.priority,
            "dependencies": json.loads(feature.dependencies) if feature.dependencies else [],
        }


def _feature_get_summary(project_dir: Path) -> list[dict[str, Any]]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        features = session.query(Feature).order_by(Feature.priority).all()
        return [
            {
                "id": f.id,
                "name": f.name,
                "passes": f.passes,
                "in_progress": f.in_progress,
                "dependencies": json.loads(f.dependencies) if f.dependencies else [],
            }
            for f in features
        ]


def _feature_claim_and_get(project_dir: Path) -> dict[str, Any]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        features = session.query(Feature).all()
        # Compute scheduling scores for priority
        all_features = []
        for f in features:
            deps = json.loads(f.dependencies) if f.dependencies else []
            all_features.append({
                "id": f.id, "passes": f.passes, "in_progress": f.in_progress,
                "priority": f.priority, "dependencies": deps,
            })

        scores = compute_scheduling_scores(all_features)
        scored = [(f, scores.get(f.id, 0)) for f in features
                  if not f.passes and not f.in_progress]

        # Filter blocked features
        passing_ids = {f.id for f in features if f.passes}
        ready = []
        for f, score in scored:
            deps = json.loads(f.dependencies) if f.dependencies else []
            if all(d in passing_ids for d in deps):
                ready.append((f, score))

        if not ready:
            return {"error": "No features available to claim"}

        ready.sort(key=lambda x: (-x[1], x[0].priority))
        feature = ready[0][0]
        feature.in_progress = True

        return {
            "id": feature.id,
            "name": feature.name,
            "category": feature.category,
            "description": feature.description,
            "steps": json.loads(feature.steps) if isinstance(feature.steps, str) else feature.steps,
            "passes": feature.passes,
            "in_progress": True,
            "priority": feature.priority,
            "dependencies": json.loads(feature.dependencies) if feature.dependencies else [],
        }


def _feature_mark_in_progress(project_dir: Path, feature_id: int) -> dict[str, Any]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if not feature:
            return {"error": f"Feature {feature_id} not found"}
        feature.in_progress = True
        return {"success": True, "feature_id": feature_id}


def _feature_mark_passing(project_dir: Path, feature_id: int) -> dict[str, Any]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if not feature:
            return {"error": f"Feature {feature_id} not found"}
        feature.passes = True
        feature.in_progress = False
        return {"success": True, "feature_id": feature_id}


def _feature_mark_failing(project_dir: Path, feature_id: int) -> dict[str, Any]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if not feature:
            return {"error": f"Feature {feature_id} not found"}
        feature.passes = False
        feature.in_progress = False
        return {"success": True, "feature_id": feature_id}


def _feature_skip(project_dir: Path, feature_id: int) -> dict[str, Any]:
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if not feature:
            return {"error": f"Feature {feature_id} not found"}
        # Move to end of queue
        max_priority = session.query(Feature).count()
        feature.priority = max_priority + 1
        feature.in_progress = False
        return {"success": True, "feature_id": feature_id}


def _feature_clear_in_progress(project_dir: Path, feature_id: int) -> dict[str, Any]:
    """Checkpoint: stamp cleared_at, do NOT clear in_progress.
    Feature stays In Progress until the agent process exits."""
    from datetime import datetime, timezone
    db_url = _ensure_db(project_dir)
    with atomic_transaction(db_url) as session:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if not feature:
            return {"error": f"Feature {feature_id} not found"}
        feature.cleared_at = datetime.now(timezone.utc)
        return {"success": True, "feature_id": feature_id}


# ---------------------------------------------------------------------------
# Tool registry and dispatcher
# ---------------------------------------------------------------------------

# Map MCP tool names (without mcp__features__ prefix) to implementations
TOOL_REGISTRY: dict[str, Any] = {
    "feature_get_stats": lambda project_dir, args: _feature_get_stats(project_dir),
    "feature_get_by_id": lambda project_dir, args: _feature_get_by_id(project_dir, args["feature_id"]),
    "feature_get_summary": lambda project_dir, args: _feature_get_summary(project_dir),
    "feature_claim_and_get": lambda project_dir, args: _feature_claim_and_get(project_dir),
    "feature_mark_in_progress": lambda project_dir, args: _feature_mark_in_progress(project_dir, args["feature_id"]),
    "feature_mark_passing": lambda project_dir, args: _feature_mark_passing(project_dir, args["feature_id"]),
    "feature_mark_failing": lambda project_dir, args: _feature_mark_failing(project_dir, args["feature_id"]),
    "feature_skip": lambda project_dir, args: _feature_skip(project_dir, args["feature_id"]),
    "feature_clear_in_progress": lambda project_dir, args: _feature_clear_in_progress(project_dir, args["feature_id"]),
}

# Map full MCP tool names to short names
_MCP_PREFIX = "mcp__features__"


def _normalize_tool_name(name: str) -> str:
    """Strip MCP prefix if present."""
    if name.startswith(_MCP_PREFIX):
        return name[len(_MCP_PREFIX):]
    return name


async def execute_tool(tool_name: str, args: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    """Execute a feature tool and return the result.

    Args:
        tool_name: Tool name (with or without mcp__features__ prefix).
        args: Tool arguments from Pi Agent.
        project_dir: Project directory for database access.

    Returns:
        Dict with "content" (JSON string) and optional "is_error" flag.
    """
    short_name = _normalize_tool_name(tool_name)

    handler = TOOL_REGISTRY.get(short_name)
    if handler is None:
        logger.warning("Unknown tool: %s (normalized: %s)", tool_name, short_name)
        return {
            "content": json.dumps({"error": f"Unknown tool: {tool_name}"}),
            "is_error": True,
        }

    try:
        result = handler(project_dir, args)
        return {
            "content": json.dumps(result),
            "is_error": False,
        }
    except Exception as e:
        logger.exception("Tool execution failed: %s", tool_name)
        return {
            "content": json.dumps({"error": str(e)}),
            "is_error": True,
        }
