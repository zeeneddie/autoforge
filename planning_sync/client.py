"""HTTP client for the Planning API with authentication and rate limiting."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .models import (
    PlanningCycle,
    PlanningModule,
    PlanningPaginatedResponse,
    PlanningState,
    PlanningWorkItem,
)

logger = logging.getLogger(__name__)

# Rate limit: 60 req/min. We budget ~40 req/min to leave headroom.
_MIN_REQUEST_INTERVAL = 1.5  # seconds between requests


class PlanningApiError(Exception):
    """Raised when the Planning API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Planning API error {status_code}: {message}")


class PlanningApiClient:
    """HTTP client for the Planning REST API.

    Handles authentication via X-API-Key header and basic rate limiting.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workspace_slug: str,
        project_id: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.workspace_slug = workspace_slug
        self.project_id = project_id
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self._last_request_time: float = 0

    def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)

    def _url(self, path: str) -> str:
        """Build full API URL for a project-scoped path."""
        return (
            f"{self.base_url}/api/v1/workspaces/{self.workspace_slug}"
            f"/projects/{self.project_id}{path}"
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        """Make an authenticated, rate-limited request to the Plane API."""
        self._rate_limit()
        url = self._url(path)

        logger.debug("Plane API %s %s", method, url)
        try:
            resp = self._session.request(
                method, url, json=json, params=params, timeout=30
            )
            self._last_request_time = time.monotonic()
        except requests.RequestException as e:
            raise PlanningApiError(0, f"Connection error: {e}") from e

        if resp.status_code == 429:
            # Rate limited — wait and retry once
            retry_after = int(resp.headers.get("Retry-After", "10"))
            logger.warning("Plane rate limit hit, waiting %ds", retry_after)
            time.sleep(retry_after)
            resp = self._session.request(
                method, url, json=json, params=params, timeout=30
            )
            self._last_request_time = time.monotonic()

        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise PlanningApiError(resp.status_code, str(detail))

        if resp.status_code == 204:
            return None

        return resp.json()

    # --- Project ---

    def test_connection(self) -> dict:
        """Test connection by fetching the project details.

        Returns project info dict on success, raises PlanningApiError on failure.
        """
        return self._request("GET", "/")

    # --- States ---

    def list_states(self) -> list[PlanningState]:
        """List all states for the project."""
        data = self._request("GET", "/states/")
        results = data if isinstance(data, list) else data.get("results", data)
        return [PlanningState(**s) for s in results]

    # --- Cycles ---

    def list_cycles(self) -> list[PlanningCycle]:
        """List all cycles for the project."""
        data = self._request("GET", "/cycles/")
        results = data if isinstance(data, list) else data.get("results", data)
        return [PlanningCycle(**c) for c in results]

    def get_cycle(self, cycle_id: str) -> PlanningCycle:
        """Get a single cycle by ID."""
        data = self._request("GET", f"/cycles/{cycle_id}/")
        return PlanningCycle(**data)

    def list_cycle_work_items(self, cycle_id: str) -> list[PlanningWorkItem]:
        """List all work items in a cycle."""
        data = self._request("GET", f"/cycles/{cycle_id}/cycle-issues/")
        # The response may be a list or paginated
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = data.get("results", [])
        else:
            results = []
        return [PlanningWorkItem(**item) for item in results]

    # --- Work Items ---

    def get_work_item(self, work_item_id: str) -> PlanningWorkItem:
        """Get a single work item by ID."""
        data = self._request("GET", f"/issues/{work_item_id}/")
        return PlanningWorkItem(**data)

    def update_work_item(
        self, work_item_id: str, updates: dict
    ) -> PlanningWorkItem:
        """Update a work item. Returns the updated work item."""
        data = self._request("PATCH", f"/issues/{work_item_id}/", json=updates)
        return PlanningWorkItem(**data)

    # --- Comments ---

    def create_issue_comment(
        self, issue_id: str, comment_html: str
    ) -> dict:
        """Create a comment on a work item.

        Args:
            issue_id: The work item UUID.
            comment_html: HTML content for the comment body.

        Returns:
            The created comment dict from the API.
        """
        return self._request(
            "POST",
            f"/issues/{issue_id}/comments/",
            json={"comment_html": comment_html},
        )

    # --- Cycles (write) ---

    def update_cycle(self, cycle_id: str, updates: dict) -> PlanningCycle:
        """Update a cycle (e.g. append to description).

        Args:
            cycle_id: The cycle UUID.
            updates: Dict of fields to update.

        Returns:
            The updated PlanningCycle.
        """
        data = self._request("PATCH", f"/cycles/{cycle_id}/", json=updates)
        return PlanningCycle(**data)

    # --- Modules ---

    def list_modules(self) -> list[PlanningModule]:
        """List all modules for the project."""
        data = self._request("GET", "/modules/")
        results = data if isinstance(data, list) else data.get("results", data)
        return [PlanningModule(**m) for m in results]

    # --- Work Items (write) ---

    def create_work_item(self, data: dict) -> PlanningWorkItem:
        """Create a new work item (issue).

        Args:
            data: Dict with fields like name, description_html, priority,
                  state, parent, etc.

        Returns:
            The created PlanningWorkItem.
        """
        result = self._request("POST", "/issues/", json=data)
        return PlanningWorkItem(**result)

    # --- Modules (write) ---

    def create_module(self, data: dict) -> PlanningModule:
        """Create a new module.

        Args:
            data: Dict with fields like name, description, status.

        Returns:
            The created PlanningModule.
        """
        result = self._request("POST", "/modules/", json=data)
        return PlanningModule(**result)

    def add_work_items_to_module(
        self, module_id: str, issue_ids: list[str]
    ) -> Any:
        """Add work items to a module.

        Args:
            module_id: The module UUID.
            issue_ids: List of work item UUIDs to add.

        Returns:
            API response.
        """
        return self._request(
            "POST",
            f"/modules/{module_id}/module-issues/",
            json={"issues": issue_ids},
        )

    # --- Cycles (add items) ---

    def add_work_items_to_cycle(
        self, cycle_id: str, issue_ids: list[str]
    ) -> Any:
        """Add work items to a cycle.

        Args:
            cycle_id: The cycle UUID.
            issue_ids: List of work item UUIDs to add.

        Returns:
            API response.
        """
        return self._request(
            "POST",
            f"/cycles/{cycle_id}/cycle-issues/",
            json={"issues": issue_ids},
        )

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
