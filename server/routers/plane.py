"""Plane integration API router."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add project root to path for imports
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from plane_sync.client import PlaneApiClient, PlaneApiError
from plane_sync.background import get_sync_loop
from plane_sync.models import (
    PlaneConfig,
    PlaneConfigUpdate,
    PlaneConnectionResult,
    PlaneCycleSummary,
    PlaneImportRequest,
    PlaneImportResult,
    PlaneSyncStatus,
    SprintCompletionResult,
    SprintStats,
)
from plane_sync.sync_service import import_cycle
from registry import get_all_settings, get_setting, set_setting

from ..utils.project_helpers import get_project_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plane", tags=["plane"])


def _mask_api_key(key: str) -> str:
    """Mask an API key for display, showing only last 4 chars."""
    if not key or len(key) < 8:
        return "****"
    return key[:8] + "****" + key[-4:]


def _get_plane_env() -> dict[str, str]:
    """Read Plane config from environment variables."""
    return {
        "plane_api_url": os.environ.get("PLANE_API_URL", ""),
        "plane_api_key": os.environ.get("PLANE_API_KEY", ""),
        "plane_workspace_slug": os.environ.get("PLANE_WORKSPACE_SLUG", ""),
        "plane_project_id": os.environ.get("PLANE_PROJECT_ID", ""),
    }


def _get_plane_config() -> dict[str, str]:
    """Get Plane config from env vars, with registry settings as overrides."""
    env = _get_plane_env()
    settings = get_all_settings()

    return {
        "plane_api_url": settings.get("plane_api_url") or env["plane_api_url"],
        "plane_api_key": settings.get("plane_api_key") or env["plane_api_key"],
        "plane_workspace_slug": settings.get("plane_workspace_slug") or env["plane_workspace_slug"],
        "plane_project_id": settings.get("plane_project_id") or env["plane_project_id"],
        "plane_sync_enabled": settings.get("plane_sync_enabled", "false"),
        "plane_poll_interval": settings.get("plane_poll_interval", "30"),
        "plane_active_cycle_id": settings.get("plane_active_cycle_id") or None,
    }


def _build_client() -> PlaneApiClient:
    """Build a PlaneApiClient from current config. Raises HTTPException if not configured."""
    config = _get_plane_config()

    if not config["plane_api_url"]:
        raise HTTPException(status_code=400, detail="Plane API URL not configured")
    if not config["plane_api_key"]:
        raise HTTPException(status_code=400, detail="Plane API key not configured")
    if not config["plane_workspace_slug"]:
        raise HTTPException(status_code=400, detail="Plane workspace slug not configured")
    if not config["plane_project_id"]:
        raise HTTPException(status_code=400, detail="Plane project ID not configured")

    return PlaneApiClient(
        base_url=config["plane_api_url"],
        api_key=config["plane_api_key"],
        workspace_slug=config["plane_workspace_slug"],
        project_id=config["plane_project_id"],
    )


# --- Config endpoints ---


@router.get("/config", response_model=PlaneConfig)
async def get_config():
    """Get current Plane configuration (API key masked)."""
    config = _get_plane_config()
    api_key = config["plane_api_key"]

    return PlaneConfig(
        plane_api_url=config["plane_api_url"],
        plane_api_key_set=bool(api_key),
        plane_api_key_masked=_mask_api_key(api_key) if api_key else "",
        plane_workspace_slug=config["plane_workspace_slug"],
        plane_project_id=config["plane_project_id"],
        plane_sync_enabled=config["plane_sync_enabled"].lower() == "true",
        plane_poll_interval=int(config["plane_poll_interval"]),
        plane_active_cycle_id=config["plane_active_cycle_id"],
    )


@router.post("/config", response_model=PlaneConfig)
async def update_config(update: PlaneConfigUpdate):
    """Update Plane configuration."""
    if update.plane_api_url is not None:
        set_setting("plane_api_url", update.plane_api_url)
    if update.plane_api_key is not None:
        set_setting("plane_api_key", update.plane_api_key)
    if update.plane_workspace_slug is not None:
        set_setting("plane_workspace_slug", update.plane_workspace_slug)
    if update.plane_project_id is not None:
        set_setting("plane_project_id", update.plane_project_id)
    if update.plane_sync_enabled is not None:
        set_setting("plane_sync_enabled", "true" if update.plane_sync_enabled else "false")
    if update.plane_poll_interval is not None:
        set_setting("plane_poll_interval", str(update.plane_poll_interval))
    if update.plane_active_cycle_id is not None:
        set_setting("plane_active_cycle_id", update.plane_active_cycle_id)

    return await get_config()


# --- Connection test ---


@router.post("/test-connection", response_model=PlaneConnectionResult)
async def test_connection():
    """Test the connection to Plane API."""
    try:
        client = _build_client()
    except HTTPException as e:
        return PlaneConnectionResult(status="error", message=e.detail)

    try:
        project_info = client.test_connection()
        return PlaneConnectionResult(
            status="ok",
            workspace=client.workspace_slug,
            project_name=project_info.get("name", ""),
        )
    except PlaneApiError as e:
        return PlaneConnectionResult(
            status="error",
            message=f"HTTP {e.status_code}: {e.message}",
        )
    except Exception as e:
        return PlaneConnectionResult(
            status="error",
            message=str(e),
        )
    finally:
        client.close()


# --- Cycles ---


@router.get("/cycles", response_model=list[PlaneCycleSummary])
async def list_cycles():
    """List available cycles from Plane."""
    client = _build_client()
    try:
        cycles = client.list_cycles()
        return [
            PlaneCycleSummary(
                id=c.id,
                name=c.name,
                start_date=c.start_date,
                end_date=c.end_date,
                status=c.status,
                total_issues=c.total_issues,
                completed_issues=c.completed_issues,
            )
            for c in cycles
        ]
    except PlaneApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    finally:
        client.close()


# --- Import ---


@router.post("/import-cycle", response_model=PlaneImportResult)
async def import_cycle_endpoint(request: PlaneImportRequest):
    """Import work items from a Plane cycle as AutoForge Features."""
    # Resolve project directory
    project_dir = get_project_path(request.project_name)
    if not project_dir:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{request.project_name}' not found in registry",
        )
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    client = _build_client()
    try:
        result = import_cycle(client, project_dir, request.cycle_id)

        # Save active cycle ID
        set_setting("plane_active_cycle_id", request.cycle_id)

        return result
    except PlaneApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    finally:
        client.close()


# --- Sync status ---


@router.get("/sync-status", response_model=PlaneSyncStatus)
async def get_sync_status():
    """Get current Plane sync loop status."""
    sync_loop = get_sync_loop()
    status = sync_loop.get_status()

    # Try to get active cycle name
    active_cycle_name = None
    cycle_id = status.get("active_cycle_id") or _get_plane_config().get("plane_active_cycle_id")
    if cycle_id:
        try:
            client = _build_client()
            try:
                cycle = client.get_cycle(cycle_id)
                active_cycle_name = cycle.name
            finally:
                client.close()
        except Exception:
            pass  # Don't fail status endpoint for this

    sprint_stats_raw = status.get("sprint_stats")
    sprint_stats = SprintStats(**sprint_stats_raw) if sprint_stats_raw else None

    return PlaneSyncStatus(
        enabled=status["enabled"],
        running=status["running"],
        last_sync_at=status["last_sync_at"],
        last_error=status["last_error"],
        items_synced=status["items_synced"],
        active_cycle_name=active_cycle_name,
        sprint_complete=status.get("sprint_complete", False),
        sprint_stats=sprint_stats,
    )


@router.post("/sync/toggle", response_model=PlaneSyncStatus)
async def toggle_sync():
    """Toggle the Plane sync loop on/off."""
    config = _get_plane_config()
    currently_enabled = config["plane_sync_enabled"].lower() == "true"

    # Toggle
    new_state = not currently_enabled
    set_setting("plane_sync_enabled", "true" if new_state else "false")

    return await get_sync_status()


# --- Sprint Completion ---


class CompleteSprintRequest(BaseModel):
    """Request to complete a sprint."""

    project_name: str


@router.post("/complete-sprint", response_model=SprintCompletionResult)
async def complete_sprint_endpoint(request: CompleteSprintRequest):
    """Complete the current sprint: verify DoD, post retrospective, create git tag."""
    project_dir = get_project_path(request.project_name)
    if not project_dir:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{request.project_name}' not found in registry",
        )
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    config = _get_plane_config()
    cycle_id = config.get("plane_active_cycle_id")
    if not cycle_id:
        return SprintCompletionResult(
            success=False,
            error="No active cycle configured. Import a cycle first.",
        )

    client = _build_client()
    try:
        from plane_sync.completion import complete_sprint
        result = complete_sprint(client, project_dir, cycle_id)
        return result
    except PlaneApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    finally:
        client.close()
