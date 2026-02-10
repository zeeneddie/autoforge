"""Background sync loop for bidirectional Plane <-> AutoForge sync."""

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


class PlaneSyncLoop:
    """Asyncio-based background loop for Plane sync.

    Runs outbound (push status to Plane) and inbound (pull changes from Plane)
    sync on a configurable interval. Designed to be started/stopped via the
    FastAPI lifespan.
    """

    def __init__(self):
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_sync_at: str | None = None
        self._last_error: str | None = None
        self._items_synced: int = 0

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_sync_at(self) -> str | None:
        return self._last_sync_at

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def items_synced(self) -> int:
        return self._items_synced

    def _get_config(self) -> dict[str, Any]:
        """Read sync config from registry settings."""
        _ensure_registry()
        from registry import get_all_settings
        settings = get_all_settings()
        return {
            "enabled": settings.get("plane_sync_enabled", "false").lower() == "true",
            "poll_interval": int(settings.get("plane_poll_interval", "30")),
            "active_cycle_id": settings.get("plane_active_cycle_id") or None,
            "plane_api_url": settings.get("plane_api_url") or "",
            "plane_api_key": settings.get("plane_api_key") or "",
            "plane_workspace_slug": settings.get("plane_workspace_slug") or "",
            "plane_project_id": settings.get("plane_project_id") or "",
        }

    def _build_client(self, config: dict[str, Any]):
        """Build a PlaneApiClient from config. Returns None if not configured."""
        from .client import PlaneApiClient

        if not all([
            config["plane_api_url"],
            config["plane_api_key"],
            config["plane_workspace_slug"],
            config["plane_project_id"],
        ]):
            return None

        return PlaneApiClient(
            base_url=config["plane_api_url"],
            api_key=config["plane_api_key"],
            workspace_slug=config["plane_workspace_slug"],
            project_id=config["plane_project_id"],
        )

    def _get_project_dirs(self) -> list[Path]:
        """Get all registered project directories that have Plane-linked features."""
        _ensure_registry()
        from registry import get_all_projects
        projects = get_all_projects()
        dirs = []
        for name, path_str in projects.items():
            p = Path(path_str)
            if p.exists():
                dirs.append(p)
        return dirs

    async def _sync_iteration(self) -> None:
        """Run one sync cycle: outbound then inbound."""
        config = self._get_config()

        if not config["enabled"]:
            return

        client = self._build_client(config)
        if not client:
            return

        cycle_id = config["active_cycle_id"]
        total_items = 0

        try:
            project_dirs = self._get_project_dirs()

            for project_dir in project_dirs:
                # Outbound: push status changes to Plane
                from .sync_service import outbound_sync
                outbound_result = await asyncio.to_thread(
                    outbound_sync, client, project_dir
                )
                total_items += outbound_result.pushed

                # Inbound: re-import cycle to pick up changes
                if cycle_id:
                    from .sync_service import import_cycle
                    inbound_result = await asyncio.to_thread(
                        import_cycle, client, project_dir, cycle_id
                    )
                    total_items += inbound_result.imported + inbound_result.updated

            self._items_synced = total_items
            self._last_sync_at = datetime.now(timezone.utc).isoformat()
            self._last_error = None

        except Exception as e:
            self._last_error = str(e)
            logger.error("Plane sync error: %s", e, exc_info=True)
        finally:
            client.close()

    async def _run_loop(self) -> None:
        """Main loop that runs sync iterations on an interval."""
        logger.info("Plane sync loop started")
        self._running = True

        try:
            while not self._stop_event.is_set():
                config = self._get_config()

                if config["enabled"]:
                    try:
                        await self._sync_iteration()
                    except Exception as e:
                        self._last_error = str(e)
                        logger.error("Plane sync iteration failed: %s", e, exc_info=True)

                # Wait for the poll interval or until stopped
                interval = config.get("poll_interval", 30)
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=interval,
                    )
                    # If we get here, stop was requested
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    pass
        finally:
            self._running = False
            logger.info("Plane sync loop stopped")

    async def start(self) -> None:
        """Start the background sync loop."""
        if self._task and not self._task.done():
            return  # Already running

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

    def get_status(self) -> dict:
        """Get current sync status for the API."""
        config = self._get_config()
        return {
            "enabled": config["enabled"],
            "running": self._running,
            "last_sync_at": self._last_sync_at,
            "last_error": self._last_error,
            "items_synced": self._items_synced,
            "active_cycle_name": None,  # Filled by the API endpoint if needed
        }


# Singleton instance
_sync_loop: PlaneSyncLoop | None = None


def get_sync_loop() -> PlaneSyncLoop:
    """Get or create the singleton PlaneSyncLoop."""
    global _sync_loop
    if _sync_loop is None:
        _sync_loop = PlaneSyncLoop()
    return _sync_loop
