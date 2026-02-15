"""Pydantic models for Planning API entities."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# --- Planning API Response Models ---


class PlanningState(BaseModel):
    """A project state in the planning tool."""

    id: str
    name: str
    color: str = ""
    group: str  # backlog, unstarted, started, completed, cancelled
    sequence: float = 0

    class Config:
        extra = "allow"


class PlanningCycle(BaseModel):
    """A cycle (sprint) in the planning tool."""

    id: str
    name: str
    description: str = ""
    start_date: str | None = None
    end_date: str | None = None
    owned_by: str | None = None
    status: str | None = None  # current, upcoming, completed, draft
    progress: float = 0
    total_issues: int = 0
    completed_issues: int = 0
    cancelled_issues: int = 0
    started_issues: int = 0
    unstarted_issues: int = 0
    backlog_issues: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        extra = "allow"


class PlanningWorkItem(BaseModel):
    """A work item (issue) in the planning tool."""

    id: str
    name: str
    description_html: str = ""
    description_stripped: str = ""
    priority: str = "none"  # none, urgent, high, medium, low
    state: str = ""  # state ID
    parent: str | None = None  # parent work item ID
    estimate_point: int | None = None
    start_date: str | None = None
    target_date: str | None = None
    sequence_id: int | None = None
    sort_order: float = 0
    completed_at: str | None = None
    archived_at: str | None = None
    is_draft: bool = False
    created_at: str | None = None
    updated_at: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    project: str = ""
    workspace: str = ""
    assignees: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    module: str | None = None  # module ID if assigned

    class Config:
        extra = "allow"


class PlanningModule(BaseModel):
    """A module in the planning tool."""

    id: str
    name: str
    description: str = ""
    status: str = ""
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        extra = "allow"


# --- Planning API List Response Wrappers ---


class PlanningPaginatedResponse(BaseModel):
    """Paginated response from Planning API."""

    results: list[dict] = Field(default_factory=list)
    total_count: int = 0
    next_page_number: int | None = None
    prev_page_number: int | None = None
    total_pages: int = 1

    class Config:
        extra = "allow"


# --- MQ DevEngine API Models (for the /api/planning/ router) ---


class PlanningConfig(BaseModel):
    """Planning configuration for display (API key masked)."""

    planning_api_url: str = ""
    planning_api_key_set: bool = False
    planning_api_key_masked: str = ""
    planning_workspace_slug: str = ""
    planning_project_id: str = ""
    planning_sync_enabled: bool = False
    planning_poll_interval: int = 30
    planning_active_cycle_id: str | None = None
    planning_webhook_secret_set: bool = False
    project_name: str | None = None


class PlanningConfigUpdate(BaseModel):
    """Request to update planning configuration."""

    planning_api_url: str | None = None
    planning_api_key: str | None = None
    planning_workspace_slug: str | None = None
    planning_project_id: str | None = None
    planning_sync_enabled: bool | None = None
    planning_poll_interval: int | None = None
    planning_active_cycle_id: str | None = None
    planning_webhook_secret: str | None = None
    project_name: str | None = None


class PlanningConnectionResult(BaseModel):
    """Result of a planning tool connection test."""

    status: str  # "ok" or "error"
    message: str = ""
    workspace: str = ""
    project_name: str = ""


class PlanningCycleSummary(BaseModel):
    """Summary of a planning cycle for the UI."""

    id: str
    name: str
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    total_issues: int = 0
    completed_issues: int = 0


class PlanningImportResult(BaseModel):
    """Result of importing a cycle's work items."""

    imported: int = 0
    skipped: int = 0
    updated: int = 0
    details: list[PlanningImportDetail] = Field(default_factory=list)


class PlanningImportDetail(BaseModel):
    """Detail of a single imported/skipped work item."""

    planning_id: str
    name: str
    action: str  # "created", "updated", "skipped"
    reason: str = ""
    feature_id: int | None = None


class PlanningOutboundResult(BaseModel):
    """Result of outbound sync (pushing feature status to planning tool)."""

    pushed: int = 0
    skipped: int = 0
    errors: int = 0


class TestRunSummary(BaseModel):
    """Test run summary for a single feature."""

    feature_id: int
    feature_name: str = ""
    total_runs: int = 0
    pass_count: int = 0
    fail_count: int = 0
    last_tested_at: str | None = None
    last_result: bool | None = None


class TestReport(BaseModel):
    """Aggregate test report across all features."""

    total_features: int = 0
    features_tested: int = 0
    features_never_tested: int = 0
    total_test_runs: int = 0
    overall_pass_rate: float = 0.0
    feature_summaries: list[TestRunSummary] = Field(default_factory=list)
    generated_at: str = ""


class SprintStats(BaseModel):
    """Sprint completion statistics."""

    total: int = 0
    passing: int = 0
    failed: int = 0
    total_test_runs: int = 0
    overall_pass_rate: float = 0.0


class PlanningSyncStatus(BaseModel):
    """Current state of the background sync loop."""

    enabled: bool = False
    running: bool = False
    last_sync_at: str | None = None
    last_error: str | None = None
    items_synced: int = 0
    active_cycle_name: str | None = None
    sprint_complete: bool = False
    sprint_stats: SprintStats | None = None
    last_webhook_at: str | None = None
    webhook_count: int = 0
    project_name: str | None = None


class SprintCompletionResult(BaseModel):
    """Result of completing a sprint."""

    success: bool
    features_completed: int = 0
    features_failed: int = 0
    git_tag: str | None = None
    change_log: str = ""
    release_notes_path: str | None = None
    error: str | None = None


class SelfHostSetupResult(BaseModel):
    """Result of self-hosting setup."""

    project_name: str
    project_path: str
    already_registered: bool = False


class PlanningImportRequest(BaseModel):
    """Request to import a cycle."""

    cycle_id: str
    project_name: str


# --- Analytics Dashboard Models ---


class TestRunDetail(BaseModel):
    """Individual test run record for timeline/heatmap display."""

    id: int
    feature_id: int
    feature_name: str = ""
    passed: bool
    agent_type: str  # "testing" or "coding"
    completed_at: str
    return_code: int | None = None


class TestHistoryResponse(BaseModel):
    """List of individual test run records."""

    runs: list[TestRunDetail] = Field(default_factory=list)
    total_count: int = 0


class ReleaseNotesItem(BaseModel):
    """Metadata for a single release notes file."""

    filename: str
    cycle_name: str = ""
    created_at: str = ""
    size_bytes: int = 0


class ReleaseNotesList(BaseModel):
    """List of release notes files."""

    items: list[ReleaseNotesItem] = Field(default_factory=list)


class ReleaseNotesContent(BaseModel):
    """Content of a single release notes file."""

    filename: str
    content: str = ""
