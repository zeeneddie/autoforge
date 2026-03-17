"""
Stuck State Router
==================

Endpoints for reading stuck state info and submitting human decisions
for stuck state recovery.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..schemas import StuckDecisionRequest, StuckStateResponse
from ..utils.project_helpers import get_project_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["stuck-state"])


def _get_stuck_state_path(project_path: Path) -> Path:
    """Get the stuck_state.json path for a project."""
    return project_path / ".mq-devengine" / "stuck_state.json"


@router.get("/{project_name}/stuck-state", response_model=StuckStateResponse)
async def get_stuck_state(project_name: str):
    """Get the current stuck state for a project.

    Returns 404 if the project is not stuck.
    """
    project_path = get_project_path(project_name)
    stuck_path = _get_stuck_state_path(project_path)

    if not stuck_path.exists():
        raise HTTPException(status_code=404, detail="Project is not stuck")

    try:
        data = json.loads(stuck_path.read_text(encoding="utf-8"))
        return StuckStateResponse(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.error("Failed to parse stuck_state.json: %s", e)
        raise HTTPException(status_code=500, detail="Invalid stuck state data")


@router.post("/{project_name}/stuck-state/decision")
async def submit_stuck_decision(project_name: str, request: StuckDecisionRequest):
    """Submit a human decision for a stuck state.

    The orchestrator polls stuck_state.json for the decision field.
    """
    project_path = get_project_path(project_name)
    stuck_path = _get_stuck_state_path(project_path)

    if not stuck_path.exists():
        raise HTTPException(status_code=404, detail="Project is not stuck")

    try:
        data = json.loads(stuck_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(status_code=500, detail=f"Invalid stuck state data: {e}")

    if data.get("decision") is not None:
        raise HTTPException(status_code=409, detail="Decision already submitted")

    # Write the decision
    data["decision"] = request.decision
    data["decision_details"] = {
        "modifications": [m.model_dump() for m in request.modifications]
    } if request.modifications else None

    stuck_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info("Stuck state decision submitted: %s for project %s", request.decision, project_name)

    return {"status": "ok", "decision": request.decision}
