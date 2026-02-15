"""Pydantic models for MarQed import API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MarQedImportRequest(BaseModel):
    """Request to import a MarQed directory tree to MQ Planning."""

    marqed_dir: str  # Path to the MarQed project root
    cycle_id: str | None = None  # Optional: add all items to this cycle
    project_name: str | None = None  # MQ DevEngine project for per-project Planning config


class MarQedImportEntityResult(BaseModel):
    """Result of importing a single MarQed entity to MQ Planning."""

    identifier: str
    name: str
    entity_type: str  # epic, feature, story, task
    planning_type: str  # module, work_item, sub_work_item
    planning_id: str = ""
    action: str  # created, error
    error: str = ""


class MarQedImportResult(BaseModel):
    """Overall result of a MarQed import."""

    total_entities: int = 0
    created: int = 0
    errors: int = 0
    modules_created: int = 0
    work_items_created: int = 0
    entities: list[MarQedImportEntityResult] = Field(default_factory=list)
