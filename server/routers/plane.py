"""Plane integration API router."""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

# Add project root to path for imports
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from plane_sync.client import PlaneApiClient, PlaneApiError
from plane_sync.background import get_sync_loop
from marqed_import.models import (
    MarQedImportRequest,
    MarQedImportResult,
)
from plane_sync.models import (
    PlaneConfig,
    PlaneConfigUpdate,
    PlaneConnectionResult,
    PlaneCycleSummary,
    PlaneImportRequest,
    PlaneImportResult,
    PlaneSyncStatus,
    ReleaseNotesContent,
    ReleaseNotesItem,
    ReleaseNotesList,
    SelfHostSetupResult,
    SprintCompletionResult,
    SprintStats,
    TestHistoryResponse,
    TestReport,
    TestRunDetail,
    TestRunSummary,
)
from plane_sync.sync_service import import_cycle
from plane_sync.webhook_handler import verify_signature, parse_webhook_event
from registry import get_all_settings, get_setting, set_setting, get_plane_setting, set_plane_setting, list_registered_projects

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


def _get_plane_config(project_name: str | None = None) -> dict[str, str]:
    """Get Plane config from env vars, with registry settings as overrides.

    Shared settings (url, key, workspace, webhook_secret) are always global.
    Per-project settings (project_id, cycle_id, sync_enabled, poll_interval)
    use get_plane_setting() which falls back to global when no per-project key.
    """
    env = _get_plane_env()
    settings = get_all_settings()

    return {
        "plane_api_url": settings.get("plane_api_url") or env["plane_api_url"],
        "plane_api_key": settings.get("plane_api_key") or env["plane_api_key"],
        "plane_workspace_slug": settings.get("plane_workspace_slug") or env["plane_workspace_slug"],
        "plane_project_id": get_plane_setting("plane_project_id", project_name) or env["plane_project_id"],
        "plane_sync_enabled": get_plane_setting("plane_sync_enabled", project_name, "false") or "false",
        "plane_poll_interval": get_plane_setting("plane_poll_interval", project_name, "30") or "30",
        "plane_active_cycle_id": get_plane_setting("plane_active_cycle_id", project_name) or None,
        "plane_webhook_secret": settings.get("plane_webhook_secret") or None,
    }


def _build_client(project_name: str | None = None) -> PlaneApiClient:
    """Build a PlaneApiClient from current config. Raises HTTPException if not configured."""
    config = _get_plane_config(project_name)

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
async def get_config(project_name: Optional[str] = Query(None)):
    """Get current Plane configuration (API key masked)."""
    config = _get_plane_config(project_name)
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
        plane_webhook_secret_set=bool(config.get("plane_webhook_secret")),
        project_name=project_name,
    )


@router.post("/config", response_model=PlaneConfig)
async def update_config(update: PlaneConfigUpdate):
    """Update Plane configuration."""
    pn = update.project_name

    # Shared (global) settings
    if update.plane_api_url is not None:
        set_setting("plane_api_url", update.plane_api_url)
    if update.plane_api_key is not None:
        set_setting("plane_api_key", update.plane_api_key)
    if update.plane_workspace_slug is not None:
        set_setting("plane_workspace_slug", update.plane_workspace_slug)
    if update.plane_webhook_secret is not None:
        set_setting("plane_webhook_secret", update.plane_webhook_secret)

    # Per-project settings (uses set_plane_setting for scoped storage)
    if update.plane_project_id is not None:
        set_plane_setting("plane_project_id", update.plane_project_id, pn)
    if update.plane_sync_enabled is not None:
        set_plane_setting("plane_sync_enabled", "true" if update.plane_sync_enabled else "false", pn)
    if update.plane_poll_interval is not None:
        set_plane_setting("plane_poll_interval", str(update.plane_poll_interval), pn)
    if update.plane_active_cycle_id is not None:
        set_plane_setting("plane_active_cycle_id", update.plane_active_cycle_id, pn)

    return await get_config(project_name=pn)


# --- Connection test ---


@router.post("/test-connection", response_model=PlaneConnectionResult)
async def test_connection(project_name: Optional[str] = Query(None)):
    """Test the connection to Plane API."""
    try:
        client = _build_client(project_name)
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
async def list_cycles(project_name: Optional[str] = Query(None)):
    """List available cycles from Plane."""
    client = _build_client(project_name)
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
    project_dir = get_project_path(request.project_name)
    if not project_dir:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{request.project_name}' not found in registry",
        )
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    client = _build_client(request.project_name)
    try:
        result = import_cycle(client, project_dir, request.cycle_id)

        # Save active cycle ID per-project
        set_plane_setting("plane_active_cycle_id", request.cycle_id, request.project_name)

        return result
    except PlaneApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    finally:
        client.close()


# --- Sync status ---


@router.get("/sync-status", response_model=PlaneSyncStatus)
async def get_sync_status(project_name: Optional[str] = Query(None)):
    """Get current Plane sync loop status."""
    sync_loop = get_sync_loop()
    status = sync_loop.get_status(project_name)

    # Try to get active cycle name
    active_cycle_name = None
    cycle_id = _get_plane_config(project_name).get("plane_active_cycle_id")
    if cycle_id:
        try:
            client = _build_client(project_name)
            try:
                cycle = client.get_cycle(cycle_id)
                active_cycle_name = cycle.name
            finally:
                client.close()
        except Exception:
            pass

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
        last_webhook_at=status.get("last_webhook_at"),
        webhook_count=status.get("webhook_count", 0),
        project_name=project_name,
    )


@router.post("/sync/toggle", response_model=PlaneSyncStatus)
async def toggle_sync(project_name: Optional[str] = Query(None)):
    """Toggle the Plane sync loop on/off."""
    config = _get_plane_config(project_name)
    currently_enabled = config["plane_sync_enabled"].lower() == "true"

    new_state = not currently_enabled
    set_plane_setting("plane_sync_enabled", "true" if new_state else "false", project_name)

    return await get_sync_status(project_name)


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

    config = _get_plane_config(request.project_name)
    cycle_id = config.get("plane_active_cycle_id")
    if not cycle_id:
        return SprintCompletionResult(
            success=False,
            error="No active cycle configured. Import a cycle first.",
        )

    client = _build_client(request.project_name)
    try:
        from plane_sync.completion import complete_sprint
        result = complete_sprint(client, project_dir, cycle_id, request.project_name)
        return result
    except PlaneApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    finally:
        client.close()


# --- Test Report ---


@router.get("/test-report", response_model=TestReport)
async def get_test_report(project_name: str, all_features: bool = False):
    """Get regression test report for a project."""
    project_dir = get_project_path(project_name)
    if not project_dir:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found in registry",
        )
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    from api.database import Feature, TestRun, create_database
    from sqlalchemy import Integer, func

    _, SessionLocal = create_database(project_dir)
    session = SessionLocal()
    try:
        if all_features:
            linked = session.query(Feature).all()
        else:
            linked = session.query(Feature).filter(
                Feature.plane_work_item_id.isnot(None)
            ).all()

        if not linked:
            return TestReport(generated_at=datetime.now(timezone.utc).isoformat())

        linked_ids = [f.id for f in linked]
        feature_names = {f.id: f.name for f in linked}

        stats = session.query(
            TestRun.feature_id,
            func.count(TestRun.id).label("total"),
            func.sum(func.cast(TestRun.passed, Integer)).label("passes"),
            func.max(TestRun.completed_at).label("last_at"),
        ).filter(
            TestRun.feature_id.in_(linked_ids)
        ).group_by(TestRun.feature_id).all()

        summaries = []
        total_runs = 0
        total_passed = 0
        tested_ids = set()

        for row in stats:
            fid = row[0]
            runs = row[1] or 0
            passes = int(row[2] or 0)
            fails = runs - passes
            total_runs += runs
            total_passed += passes
            tested_ids.add(fid)

            last_run = session.query(TestRun).filter(
                TestRun.feature_id == fid
            ).order_by(TestRun.completed_at.desc()).first()

            summaries.append(TestRunSummary(
                feature_id=fid,
                feature_name=feature_names.get(fid, ""),
                total_runs=runs,
                pass_count=passes,
                fail_count=fails,
                last_tested_at=row[3].isoformat() if row[3] else None,
                last_result=last_run.passed if last_run else None,
            ))

        pass_rate = (total_passed / total_runs * 100) if total_runs > 0 else 0.0

        return TestReport(
            total_features=len(linked_ids),
            features_tested=len(tested_ids),
            features_never_tested=len(linked_ids) - len(tested_ids),
            total_test_runs=total_runs,
            overall_pass_rate=round(pass_rate, 1),
            feature_summaries=summaries,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        session.close()


# --- Test History ---


@router.get("/test-history", response_model=TestHistoryResponse)
async def get_test_history(
    project_name: str,
    feature_id: int | None = None,
    limit: int = 50,
):
    """Get individual test run records for timeline/heatmap display."""
    project_dir = get_project_path(project_name)
    if not project_dir:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found in registry",
        )
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    from api.database import Feature, TestRun, create_database

    _, SessionLocal = create_database(project_dir)
    session = SessionLocal()
    try:
        query = session.query(TestRun)
        if feature_id is not None:
            query = query.filter(TestRun.feature_id == feature_id)
        total_count = query.count()

        runs = query.order_by(TestRun.completed_at.desc()).limit(min(limit, 200)).all()

        fids = {r.feature_id for r in runs}
        features = session.query(Feature).filter(Feature.id.in_(fids)).all() if fids else []
        fname_map = {f.id: f.name for f in features}

        details = [
            TestRunDetail(
                id=r.id,
                feature_id=r.feature_id,
                feature_name=fname_map.get(r.feature_id, ""),
                passed=r.passed,
                agent_type=r.agent_type,
                completed_at=r.completed_at.isoformat() if r.completed_at else "",
                return_code=r.return_code,
            )
            for r in runs
        ]

        return TestHistoryResponse(runs=details, total_count=total_count)
    finally:
        session.close()


# --- Release Notes ---


@router.get("/release-notes", response_model=ReleaseNotesList)
async def list_release_notes(project_name: str):
    """List available release notes files for a project."""
    project_dir = get_project_path(project_name)
    if not project_dir:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found in registry",
        )
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    releases_dir = project_dir / "releases"
    if not releases_dir.is_dir():
        return ReleaseNotesList()

    items = []
    for f in sorted(releases_dir.glob("*.md"), reverse=True):
        stat = f.stat()
        cycle_name = f.stem
        if cycle_name.startswith("sprint-"):
            cycle_name = cycle_name[7:]
        cycle_name = cycle_name.replace("-", " ").title()

        items.append(ReleaseNotesItem(
            filename=f.name,
            cycle_name=cycle_name,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            size_bytes=stat.st_size,
        ))

    return ReleaseNotesList(items=items)


@router.get("/release-notes/content", response_model=ReleaseNotesContent)
async def get_release_notes_content(project_name: str, filename: str):
    """Get the content of a specific release notes file."""
    project_dir = get_project_path(project_name)
    if not project_dir:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found in registry",
        )
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = project_dir / "releases" / filename
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Release notes file not found: {filename}")

    content = filepath.read_text(encoding="utf-8", errors="replace")
    return ReleaseNotesContent(filename=filename, content=content)


# --- Webhook ---

_webhook_dedup: dict[str, float] = {}
_WEBHOOK_DEDUP_COOLDOWN = 5.0


@router.post("/webhooks")
async def receive_webhook(request: Request):
    """Receive a webhook from Plane. Verifies HMAC if secret is configured."""
    body = await request.body()

    config = _get_plane_config()
    secret = config.get("plane_webhook_secret")
    if secret:
        signature = request.headers.get("x-plane-signature", "") or request.headers.get("x-signature", "")
        if not signature or not verify_signature(body, signature, secret):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        import json
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type, action, data = parse_webhook_event(payload)

    event_key = f"{event_type}:{action}:{data.get('id', '')}"
    now = time.time()
    if event_key in _webhook_dedup and (now - _webhook_dedup[event_key]) < _WEBHOOK_DEDUP_COOLDOWN:
        return {"status": "ok", "action": "deduped"}

    _webhook_dedup[event_key] = now

    cutoff = now - _WEBHOOK_DEDUP_COOLDOWN * 2
    for k in list(_webhook_dedup.keys()):
        if _webhook_dedup[k] < cutoff:
            del _webhook_dedup[k]

    sync_loop = get_sync_loop()
    sync_loop.record_webhook()

    # Route events: iterate projects, re-import each project's own cycle
    try:
        projects = list_registered_projects()
        for pn, pinfo in projects.items():
            cycle_id = get_plane_setting("plane_active_cycle_id", pn)
            if not cycle_id:
                continue

            project_dir = Path(pinfo["path"])
            if not project_dir.exists():
                continue

            # Filter by source Plane project — skip if event is for a different project
            project_plane_id = get_plane_setting("plane_project_id", pn)
            event_project_id = data.get("project") or data.get("project_id")

            should_import = False
            if event_type in ("issue", "work_item") and action == "update":
                # Only import if the event belongs to this project's Plane project
                if event_project_id and project_plane_id and event_project_id != project_plane_id:
                    continue
                should_import = True
            elif event_type == "cycle" and action == "update" and data.get("id") == cycle_id:
                should_import = True

            if should_import:
                try:
                    client = _build_client(pn)
                    try:
                        import_cycle(client, project_dir, cycle_id)
                    finally:
                        client.close()
                except Exception as e:
                    logger.warning("Webhook import failed for %s: %s", pn, e)

    except Exception as e:
        logger.warning("Webhook processing error: %s", e)
        return {"status": "ok", "action": "error", "message": str(e)}

    return {"status": "ok", "action": "processed"}


# --- Self-hosting ---


@router.post("/self-host-setup", response_model=SelfHostSetupResult)
async def self_host_setup():
    """Register AutoForge as a project in its own registry (idempotent)."""
    try:
        from plane_sync.self_host import setup_self_host
        result = setup_self_host()
        return SelfHostSetupResult(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- MarQed Import ---


@router.post("/marqed-import", response_model=MarQedImportResult)
async def marqed_import_endpoint(request: MarQedImportRequest):
    """Import a MarQed directory tree into Plane as modules and work items."""
    from pathlib import Path as _Path

    marqed_dir = _Path(request.marqed_dir)
    if not marqed_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"MarQed directory not found: {request.marqed_dir}",
        )

    client = _build_client(request.project_name)
    try:
        from marqed_import.importer import import_to_plane
        result = import_to_plane(client, marqed_dir, request.cycle_id)
        return result
    except PlaneApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    finally:
        client.close()
