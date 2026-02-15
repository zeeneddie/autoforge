"""Background sync loop for bidirectional Plane <-> MQ DevEngine sync."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependencies at module level
_registry_imported = False


def _ensure_registry():
    global _registry_imported
    if not _registry_imported:
        root = Path(__file__).parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        _registry_imported = True


class PlanningSyncLoop:
    """Asyncio-based background loop for Plane sync.

    Runs outbound (push status to Plane) and inbound (pull changes from Plane)
    sync on a configurable interval per project. Designed to be started/stopped
    via the FastAPI lifespan.
    """

    def __init__(self):
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_webhook_at: str | None = None
        self._webhook_count: int = 0
        # Per-project status tracking
        self._per_project_status: dict[str, dict] = {}
        # Per-project last sync time for respecting individual poll intervals
        self._last_sync_time: dict[str, float] = {}

    @property
    def running(self) -> bool:
        return self._running

    def _get_project_config(self, project_name: str) -> dict[str, Any]:
        """Read sync config for a specific project.

        Shared settings (url, key, workspace, webhook_secret) from global registry.
        Per-project settings (project_id, cycle_id, sync_enabled, poll_interval)
        via get_planning_setting() with project_name fallback.
        """
        _ensure_registry()
        from registry import get_planning_setting, get_setting

        return {
            "enabled": (get_planning_setting("planning_sync_enabled", project_name, "false") or "false").lower() == "true",
            "poll_interval": int(get_planning_setting("planning_poll_interval", project_name, "30") or "30"),
            "active_cycle_id": get_planning_setting("planning_active_cycle_id", project_name) or None,
            "planning_api_url": get_setting("planning_api_url") or "",
            "planning_api_key": get_setting("planning_api_key") or "",
            "planning_workspace_slug": get_setting("planning_workspace_slug") or "",
            "planning_project_id": get_planning_setting("planning_project_id", project_name) or "",
        }

    def _build_client(self, config: dict[str, Any]):
        """Build a PlanningApiClient from config. Returns None if not configured."""
        from .client import PlanningApiClient

        if not all([
            config["planning_api_url"],
            config["planning_api_key"],
            config["planning_workspace_slug"],
            config["planning_project_id"],
        ]):
            return None

        return PlanningApiClient(
            base_url=config["planning_api_url"],
            api_key=config["planning_api_key"],
            workspace_slug=config["planning_workspace_slug"],
            project_id=config["planning_project_id"],
        )

    def _get_registered_projects(self) -> dict[str, dict]:
        """Get all registered projects."""
        _ensure_registry()
        from registry import list_registered_projects
        return list_registered_projects()

    def _check_sprint_completion_for_project(self, project_name: str, project_dir: Path) -> None:
        """Check sprint completion for a single project."""
        _ensure_registry()
        total = 0
        passing = 0
        total_test_runs = 0
        passed_test_runs = 0

        try:
            root = Path(__file__).parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from api.database import Feature, TestRun, create_database
            from sqlalchemy import func

            _, SessionLocal = create_database(project_dir)
            session = SessionLocal()
            try:
                linked = session.query(Feature).filter(
                    Feature.planning_work_item_id.isnot(None)
                ).all()
                linked_ids = []
                for f in linked:
                    total += 1
                    linked_ids.append(f.id)
                    if f.passes:
                        passing += 1

                if linked_ids:
                    stats = session.query(
                        func.count(TestRun.id),
                        func.sum(func.cast(TestRun.passed, type_=None)),
                    ).filter(
                        TestRun.feature_id.in_(linked_ids)
                    ).first()
                    if stats:
                        total_test_runs += stats[0] or 0
                        passed_test_runs += int(stats[1] or 0)
            finally:
                session.close()
        except Exception as e:
            logger.debug("Sprint completion check failed for %s: %s", project_dir, e)

        status = self._per_project_status.setdefault(project_name, {})
        if total > 0:
            status["sprint_complete"] = passing == total
            pass_rate = (passed_test_runs / total_test_runs * 100) if total_test_runs > 0 else 0.0
            status["sprint_stats"] = {
                "total": total,
                "passing": passing,
                "failed": total - passing,
                "total_test_runs": total_test_runs,
                "overall_pass_rate": round(pass_rate, 1),
            }
        else:
            status["sprint_complete"] = False
            status["sprint_stats"] = None

    async def _sync_iteration(self) -> None:
        """Run one sync cycle per project: outbound then inbound.

        Respects per-project poll intervals — skips projects whose interval
        has not yet elapsed since their last sync.
        """
        import time

        projects = self._get_registered_projects()
        now = time.monotonic()

        for project_name, project_info in projects.items():
            config = self._get_project_config(project_name)

            if not config["enabled"]:
                continue

            # Respect per-project poll interval
            last_sync = self._last_sync_time.get(project_name, 0.0)
            if now - last_sync < config["poll_interval"]:
                continue

            client = self._build_client(config)
            if not client:
                continue

            project_dir = Path(project_info["path"])
            if not project_dir.exists():
                continue

            cycle_id = config["active_cycle_id"]
            total_items = 0

            try:
                from .sync_service import outbound_sync, import_cycle
                outbound_result = await asyncio.to_thread(
                    outbound_sync, client, project_dir
                )
                total_items += outbound_result.pushed

                if cycle_id:
                    inbound_result = await asyncio.to_thread(
                        import_cycle, client, project_dir, cycle_id
                    )
                    total_items += inbound_result.imported + inbound_result.updated

                self._last_sync_time[project_name] = now
                status = self._per_project_status.setdefault(project_name, {})
                status["items_synced"] = total_items
                status["last_sync_at"] = datetime.now(timezone.utc).isoformat()
                status["last_error"] = None

                # Check sprint completion for this project
                await asyncio.to_thread(
                    self._check_sprint_completion_for_project, project_name, project_dir
                )

            except Exception as e:
                self._last_sync_time[project_name] = now  # avoid retry-storm
                status = self._per_project_status.setdefault(project_name, {})
                status["last_error"] = str(e)
                logger.error("Plane sync error for %s: %s", project_name, e, exc_info=True)
            finally:
                client.close()

    async def _run_loop(self) -> None:
        """Main loop that runs sync iterations on a short tick.

        Uses a 5-second tick; _sync_iteration() respects each project's
        individual poll_interval via _last_sync_time tracking.
        """
        logger.info("Plane sync loop started")
        self._running = True
        tick_interval = 5  # seconds between loop ticks

        try:
            while not self._stop_event.is_set():
                try:
                    await self._sync_iteration()
                except Exception as e:
                    logger.error("Plane sync iteration failed: %s", e, exc_info=True)

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=tick_interval,
                    )
                    break
                except asyncio.TimeoutError:
                    pass
        finally:
            self._running = False
            logger.info("Plane sync loop stopped")

    async def start(self) -> None:
        """Start the background sync loop."""
        if self._task and not self._task.done():
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Plane sync loop task created")

    async def stop(self) -> None:
        """Stop the background sync loop gracefully."""
        if not self._task or self._task.done():
            return

        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=10)
        except asyncio.TimeoutError:
            logger.warning("Plane sync loop did not stop in time, cancelling")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    def record_webhook(self) -> None:
        """Record that a webhook was received."""
        self._webhook_count += 1
        self._last_webhook_at = datetime.now(timezone.utc).isoformat()

    def get_status(self, project_name: str | None = None) -> dict:
        """Get current sync status for the API.

        If project_name is given, return per-project status.
        Otherwise return aggregated status.
        """
        if project_name:
            config = self._get_project_config(project_name)
            ps = self._per_project_status.get(project_name, {})
            return {
                "enabled": config["enabled"],
                "running": self._running,
                "last_sync_at": ps.get("last_sync_at"),
                "last_error": ps.get("last_error"),
                "items_synced": ps.get("items_synced", 0),
                "active_cycle_name": None,
                "sprint_complete": ps.get("sprint_complete", False),
                "sprint_stats": ps.get("sprint_stats"),
                "last_webhook_at": self._last_webhook_at,
                "webhook_count": self._webhook_count,
                "project_name": project_name,
            }

        # Aggregated: any project enabled = enabled, merge stats
        projects = self._get_registered_projects()
        any_enabled = False
        total_items = 0
        latest_sync = None
        latest_error = None
        agg_sprint_complete = True
        agg_sprint_stats: dict | None = None
        has_any_stats = False

        for pn in projects:
            config = self._get_project_config(pn)
            if config["enabled"]:
                any_enabled = True
            ps = self._per_project_status.get(pn, {})
            total_items += ps.get("items_synced", 0)
            sync_at = ps.get("last_sync_at")
            if sync_at and (latest_sync is None or sync_at > latest_sync):
                latest_sync = sync_at
            err = ps.get("last_error")
            if err:
                latest_error = err

            ss = ps.get("sprint_stats")
            if ss:
                has_any_stats = True
                if agg_sprint_stats is None:
                    agg_sprint_stats = {"total": 0, "passing": 0, "failed": 0, "total_test_runs": 0, "overall_pass_rate": 0.0}
                agg_sprint_stats["total"] += ss["total"]
                agg_sprint_stats["passing"] += ss["passing"]
                agg_sprint_stats["failed"] += ss["failed"]
                agg_sprint_stats["total_test_runs"] += ss["total_test_runs"]
                if not ps.get("sprint_complete", False):
                    agg_sprint_complete = False

        if agg_sprint_stats and agg_sprint_stats["total_test_runs"] > 0:
            # Recalculate overall pass rate from aggregated data
            pass  # keep per-project rates, we'll just average
        if not has_any_stats:
            agg_sprint_complete = False

        return {
            "enabled": any_enabled,
            "running": self._running,
            "last_sync_at": latest_sync,
            "last_error": latest_error,
            "items_synced": total_items,
            "active_cycle_name": None,
            "sprint_complete": agg_sprint_complete,
            "sprint_stats": agg_sprint_stats,
            "last_webhook_at": self._last_webhook_at,
            "webhook_count": self._webhook_count,
        }


# Singleton instance
_sync_loop: PlanningSyncLoop | None = None


def get_sync_loop() -> PlanningSyncLoop:
    """Get or create the singleton PlanningSyncLoop."""
    global _sync_loop
    if _sync_loop is None:
        _sync_loop = PlanningSyncLoop()
    return _sync_loop
