"""Sync service: bidirectional sync between Plane work items and MQ DevEngine Features."""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .client import PlanningApiClient, PlanningApiError
from .mapper import feature_status_to_planning_update, state_group_for_id, work_item_to_feature_dict
from .models import PlanningImportDetail, PlanningImportResult, PlanningOutboundResult

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependencies
_create_database = None
_Feature = None


def _get_db_classes():
    """Lazy import of database classes."""
    global _create_database, _Feature
    if _create_database is None:
        root = Path(__file__).parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from api.database import Feature, create_database
        _create_database = create_database
        _Feature = Feature
    return _create_database, _Feature


@contextmanager
def _get_db_session(project_dir: Path):
    """Context manager for database sessions."""
    create_database, _ = _get_db_classes()
    _, SessionLocal = create_database(project_dir)
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def import_cycle(
    client: PlanningApiClient,
    project_dir: Path,
    cycle_id: str,
) -> PlanningImportResult:
    """Import work items from a Plane cycle into the MQ DevEngine Feature DB.

    - New work items are created as Features.
    - Existing Features (matched by planning_work_item_id) are updated if Plane
      has a newer updated_at timestamp.
    - Cancelled work items are skipped.

    Args:
        client: Authenticated PlanningApiClient.
        project_dir: Path to the MQ DevEngine project directory.
        cycle_id: Plane cycle UUID to import from.

    Returns:
        PlanningImportResult with counts and details.
    """
    _, Feature = _get_db_classes()

    # Fetch Plane data
    states = client.list_states()
    modules_raw = client.list_modules()
    modules = {m.id: m.name for m in modules_raw}
    work_items = client.list_cycle_work_items(cycle_id)

    logger.info(
        "Importing cycle %s: %d work items, %d states, %d modules",
        cycle_id, len(work_items), len(states), len(modules),
    )

    result = PlanningImportResult()

    with _get_db_session(project_dir) as session:
        # Build lookup: planning_work_item_id -> feature_id for dependency resolution
        existing_features = session.query(Feature).filter(
            Feature.planning_work_item_id.isnot(None)
        ).all()
        planning_to_feature: dict[str, int] = {
            f.planning_work_item_id: f.id for f in existing_features
        }

        # Determine next available priority
        max_prio_feature = (
            session.query(Feature)
            .order_by(Feature.priority.desc())
            .first()
        )
        next_priority = (max_prio_feature.priority + 1) if max_prio_feature else 1

        for item in work_items:
            # Skip cancelled items
            group = state_group_for_id(item.state, states)
            if group == "cancelled":
                result.skipped += 1
                result.details.append(PlanningImportDetail(
                    planning_id=item.id,
                    name=item.name,
                    action="skipped",
                    reason="cancelled",
                ))
                continue

            # Check if already imported
            existing = session.query(Feature).filter(
                Feature.planning_work_item_id == item.id
            ).first()

            if existing:
                # Update if Plane has a newer version
                if (
                    item.updated_at
                    and existing.planning_updated_at
                    and item.updated_at == existing.planning_updated_at.isoformat()
                ):
                    # Same timestamp = our own update echoing back, skip
                    result.skipped += 1
                    result.details.append(PlanningImportDetail(
                        planning_id=item.id,
                        name=item.name,
                        action="skipped",
                        reason="already_imported",
                        feature_id=existing.id,
                    ))
                    continue

                # Plane has a newer version — update the feature
                mapped = work_item_to_feature_dict(
                    item, states, modules, planning_to_feature,
                )
                existing.name = mapped["name"]
                existing.description = mapped["description"]
                existing.priority = mapped["priority"]
                existing.category = mapped["category"]
                existing.steps = mapped["steps"]
                if mapped["dependencies"] is not None:
                    existing.dependencies = mapped["dependencies"]
                existing.planning_synced_at = datetime.now(timezone.utc)
                existing.planning_updated_at = (
                    datetime.fromisoformat(item.updated_at)
                    if item.updated_at else None
                )

                result.updated += 1
                result.details.append(PlanningImportDetail(
                    planning_id=item.id,
                    name=item.name,
                    action="updated",
                    feature_id=existing.id,
                ))
            else:
                # Create new Feature
                mapped = work_item_to_feature_dict(
                    item, states, modules, planning_to_feature,
                )
                new_feature = Feature(
                    name=mapped["name"],
                    description=mapped["description"],
                    priority=next_priority,
                    category=mapped["category"],
                    steps=mapped["steps"],
                    passes=mapped["passes"],
                    in_progress=mapped["in_progress"],
                    dependencies=mapped["dependencies"],
                    planning_work_item_id=mapped["planning_work_item_id"],
                    planning_synced_at=datetime.now(timezone.utc),
                    planning_updated_at=(
                        datetime.fromisoformat(item.updated_at)
                        if item.updated_at else None
                    ),
                )
                session.add(new_feature)
                session.flush()  # Get the ID

                # Track for dependency resolution of later items
                planning_to_feature[item.id] = new_feature.id
                next_priority += 1

                result.imported += 1
                result.details.append(PlanningImportDetail(
                    planning_id=item.id,
                    name=item.name,
                    action="created",
                    feature_id=new_feature.id,
                ))

        # Detect items removed from the cycle (mid-sprint removals)
        cycle_item_ids = {item.id for item in work_items}
        for feature in existing_features:
            if feature.planning_work_item_id not in cycle_item_ids:
                # Item was removed from the cycle — mark as skipped (not deleted)
                if not feature.passes and feature.in_progress:
                    feature.in_progress = False
                    result.skipped += 1
                    result.details.append(PlanningImportDetail(
                        planning_id=feature.planning_work_item_id,
                        name=feature.name,
                        action="skipped",
                        reason="removed_from_cycle",
                        feature_id=feature.id,
                    ))

        session.commit()

    logger.info(
        "Import complete: %d imported, %d updated, %d skipped",
        result.imported, result.updated, result.skipped,
    )
    return result


def outbound_sync(
    client: PlanningApiClient,
    project_dir: Path,
) -> PlanningOutboundResult:
    """Push MQ DevEngine feature status changes to Plane work items.

    For each feature linked to a Plane work item:
    1. Compute a status hash from passes/in_progress
    2. Skip if hash matches planning_last_status_hash (no change)
    3. Map status to Plane state group and push via API
    4. Store Plane's response updated_at as planning_updated_at (echo prevention)

    Args:
        client: Authenticated PlanningApiClient.
        project_dir: Path to the MQ DevEngine project directory.

    Returns:
        PlanningOutboundResult with counts.
    """
    _, Feature = _get_db_classes()

    # Fetch Plane states once
    states = client.list_states()

    result = PlanningOutboundResult()

    with _get_db_session(project_dir) as session:
        features = session.query(Feature).filter(
            Feature.planning_work_item_id.isnot(None)
        ).all()

        for feature in features:
            # Compute current status hash
            passes = feature.passes if feature.passes is not None else False
            in_progress = feature.in_progress if feature.in_progress is not None else False
            status_hash = f"{passes}:{in_progress}"

            # Skip if status hasn't changed since last push
            if feature.planning_last_status_hash == status_hash:
                result.skipped += 1
                continue

            # Build the Plane update
            update = feature_status_to_planning_update(passes, in_progress, states)
            if not update:
                result.skipped += 1
                continue

            try:
                updated_item = client.update_work_item(
                    feature.planning_work_item_id, update
                )

                # Store Plane's response timestamp for echo prevention
                if updated_item.updated_at:
                    feature.planning_updated_at = datetime.fromisoformat(
                        updated_item.updated_at
                    )

                # Mark this status as synced
                feature.planning_last_status_hash = status_hash
                feature.planning_synced_at = datetime.now(timezone.utc)

                result.pushed += 1
                logger.debug(
                    "Pushed status %s for feature %d (%s) to Plane",
                    status_hash, feature.id, feature.name,
                )
            except PlanningApiError as e:
                result.errors += 1
                logger.warning(
                    "Failed to push feature %d to Plane: %s",
                    feature.id, e,
                )

        session.commit()

    logger.info(
        "Outbound sync: %d pushed, %d skipped, %d errors",
        result.pushed, result.skipped, result.errors,
    )
    return result
