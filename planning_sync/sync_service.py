"""Sync service: bidirectional sync between Plane work items and MQ DevEngine Features."""

from __future__ import annotations

import logging
import re
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .client import PlanningApiClient, PlanningApiError
from .mapper import feature_status_to_planning_update, find_state_id_for_group, state_group_for_id, work_item_to_feature_dict
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

    # Detect hierarchy: items that appear as `parent` of other items in the cycle are
    # Feature-level containers (Epic → Feature). We import only their children
    # (User Stories) with the Feature name as context. Standalone items (no parent,
    # not a parent) are imported as-is (existing behaviour).
    cycle_item_ids = {item.id for item in work_items}
    cycle_parent_ids = {item.parent for item in work_items if item.parent and item.parent in cycle_item_ids}

    # Build Feature context map: id → {name, description} for items that ARE parents
    feature_context: dict[str, dict[str, str]] = {
        item.id: {"name": item.name, "description": item.description_stripped or item.name}
        for item in work_items
        if item.id in cycle_parent_ids
    }

    if feature_context:
        logger.info(
            "Hierarchy detected: %d Feature-level items (will import their User Stories only): %s",
            len(feature_context),
            [v["name"] for v in feature_context.values()],
        )

    # Track siblings per Plane parent for sequential dependency assignment
    parent_to_sibling_features: dict[str, list] = {}  # plane_parent_id → [Feature]

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
            # Skip Feature-level containers (items that have children in this cycle)
            if item.id in cycle_parent_ids:
                result.skipped += 1
                result.details.append(PlanningImportDetail(
                    planning_id=item.id,
                    name=item.name,
                    action="skipped",
                    reason="feature_container",
                ))
                continue

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
                # Prepend Feature context if this is a User Story (has parent Feature)
                if item.parent and item.parent in feature_context:
                    ctx = feature_context[item.parent]
                    mapped["description"] = f"[Feature: {ctx['name']}]\n\n{mapped['description']}"
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
                # Track Plane parent container UUID for aggregated outbound sync
                if item.parent and item.parent in feature_context:
                    existing.planning_parent_work_item_id = item.parent

                if item.parent and item.parent in feature_context:
                    parent_to_sibling_features.setdefault(item.parent, []).append(existing)

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
                # Prepend Feature context if this is a User Story (has parent Feature)
                if item.parent and item.parent in feature_context:
                    ctx = feature_context[item.parent]
                    mapped["description"] = f"[Feature: {ctx['name']}]\n\n{mapped['description']}"
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
                    # Track Plane parent container UUID for aggregated outbound sync
                    planning_parent_work_item_id=(
                        item.parent if item.parent and item.parent in feature_context else None
                    ),
                    cycle_id=cycle_id,
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
                if item.parent and item.parent in feature_context:
                    parent_to_sibling_features.setdefault(item.parent, []).append(new_feature)
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

        # Set sort_order on Plane work items for hierarchical display (2.1 → 2.1.1 → 2.1.2 → 2.2 …)
        def _numeric_sort_key(item) -> list[int]:
            m = re.match(r'^([\d.]+)', item.name)
            return [int(x) for x in m.group(1).split('.')] if m else [999]

        items_sorted = sorted(work_items, key=_numeric_sort_key)
        sort_updated = 0
        for i, item in enumerate(items_sorted):
            new_order = (i + 1) * 10000
            if item.sort_order == float(new_order):
                continue
            try:
                client.update_work_item(item.id, {"sort_order": new_order})
                sort_updated += 1
            except Exception:
                pass  # non-critical
        if sort_updated:
            logger.info("Updated sort_order for %d items in cycle", sort_updated)

        # Set sequential sibling dependencies: 2.4.2 depends on 2.4.1, etc.
        # Sort siblings by name (numeric prefix order) and chain them.
        # Only set if the feature has no explicit dependencies yet (don't override).
        sibling_deps_set = 0
        for siblings in parent_to_sibling_features.values():
            if len(siblings) < 2:
                continue
            siblings_sorted = sorted(siblings, key=lambda f: f.name)
            for i in range(1, len(siblings_sorted)):
                curr = siblings_sorted[i]
                if not curr.dependencies:
                    curr.dependencies = [siblings_sorted[i - 1].id]
                    sibling_deps_set += 1

        if sibling_deps_set:
            logger.info("Set sequential sibling dependencies for %d features", sibling_deps_set)

        session.commit()

    logger.info(
        "Import complete: %d imported, %d updated, %d skipped",
        result.imported, result.updated, result.skipped,
    )
    return result


def _build_client_for_project(project_name: str) -> PlanningApiClient:
    """Build a PlanningApiClient from per-project registry settings."""
    root = Path(__file__).parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from registry import get_planning_setting, get_setting
    return PlanningApiClient(
        base_url=get_setting("planning_api_url") or "",
        api_key=get_setting("planning_api_key") or "",
        workspace_slug=get_setting("planning_workspace_slug") or "",
        project_id=get_planning_setting("planning_project_id", project_name) or "",
    )


def sync_tasks_to_plane(
    feature,
    session,
    project_name: str,
) -> int:
    """Create Plane child work items for feature tasks that have no planning_work_item_id yet.

    Idempotent: skips tasks that already have a Plane ID.
    Returns count of child items created.
    """
    if not feature.planning_work_item_id:
        return 0
    tasks = feature.tasks or []
    if not any(not t.get("planning_work_item_id") for t in tasks):
        return 0  # all tasks already synced

    try:
        client = _build_client_for_project(project_name)
    except Exception as e:
        logger.warning("sync_tasks_to_plane: could not build client: %s", e)
        return 0

    try:
        states = client.list_states()
        unstarted_id = find_state_id_for_group("unstarted", states)

        created = 0
        new_ids = []
        for task in tasks:
            if task.get("planning_work_item_id"):
                continue
            try:
                resp = client.create_work_item({
                    "name": task["name"],
                    "description_html": f"<p>{task.get('description', '')}</p>",
                    "parent": feature.planning_work_item_id,
                    "state": unstarted_id,
                    "priority": "none",
                })
                if resp and resp.get("id"):
                    task["planning_work_item_id"] = resp["id"]
                    new_ids.append(resp["id"])
                    created += 1
            except Exception as e:
                logger.warning("sync_tasks_to_plane: failed to create task '%s': %s", task.get("name"), e)

        # Add child items to the active cycle so they appear in the sprint board
        if new_ids and feature.cycle_id:
            try:
                client.add_work_items_to_cycle(feature.cycle_id, new_ids)
            except Exception as e:
                logger.warning("sync_tasks_to_plane: failed to add tasks to cycle: %s", e)

        if created:
            feature.tasks = list(tasks)  # trigger JSON update
            session.commit()
            logger.info(
                "sync_tasks_to_plane: created %d child items in Plane for feature %d (%s)",
                created, feature.id, feature.name,
            )
    finally:
        client.close()

    return created


def apply_category_mapping(project_dir: Path, project_name: str) -> int:
    """Apply category-to-Plane-work-item mapping to features.

    Sets planning_parent_work_item_id on features whose category matches the mapping.
    Idempotent: skips features that already have a parent or have a direct 1:1 link.

    Returns:
        Number of features updated.
    """
    root = Path(__file__).parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from registry import get_category_mapping

    _, Feature = _get_db_classes()
    mapping = get_category_mapping(project_name)
    if not mapping:
        return 0

    updated = 0
    with _get_db_session(project_dir) as session:
        features = session.query(Feature).filter(
            Feature.planning_parent_work_item_id.is_(None),
            Feature.planning_work_item_id.is_(None),
        ).all()

        for feat in features:
            parent_id = mapping.get(feat.category)
            if parent_id:
                feat.planning_parent_work_item_id = parent_id
                updated += 1

        session.commit()

    if updated:
        logger.info(
            "Applied category mapping for %s: %d features linked to parent work items",
            project_name, updated,
        )
    return updated


def _compute_aggregated_status(features) -> tuple[bool, bool]:
    """Compute aggregated status from a group of features.

    Returns:
        (all_pass, any_started) tuple for determining Plane state group.
    """
    all_pass = all(
        (f.passes if f.passes is not None else False) for f in features
    )
    any_started = any(
        (f.in_progress if f.in_progress is not None else False)
        or (f.passes if f.passes is not None else False)
        for f in features
    )
    return all_pass, any_started


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
            review_status = feature.review_status or ""
            status_hash = f"{passes}:{in_progress}:{review_status}"

            # Skip if status hasn't changed since last push
            if feature.planning_last_status_hash == status_hash:
                result.skipped += 1
                continue

            # Build the Plane update
            update = feature_status_to_planning_update(passes, in_progress, states, review_status or None)
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

        # --- Mode 2: Aggregated sync for parent-linked features ---
        parent_features = session.query(Feature).filter(
            Feature.planning_parent_work_item_id.isnot(None),
            Feature.planning_work_item_id.is_(None),
        ).all()

        if parent_features:
            # Group by parent work item
            groups: dict[str, list] = defaultdict(list)
            for feat in parent_features:
                groups[feat.planning_parent_work_item_id].append(feat)

            root = Path(__file__).parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from registry import get_setting, set_setting

            for parent_id, group in groups.items():
                all_pass, any_started = _compute_aggregated_status(group)
                passes_count = sum(
                    1 for f in group if (f.passes if f.passes is not None else False)
                )
                in_progress_count = sum(
                    1 for f in group if (f.in_progress if f.in_progress is not None else False)
                )
                agg_hash = f"agg:{passes_count}:{in_progress_count}:{len(group)}"

                # Check if hash changed
                hash_key = f"planning_agg_hash:{parent_id}:{project_dir.name}"
                prev_hash = get_setting(hash_key)
                if prev_hash == agg_hash:
                    result.skipped += 1
                    continue

                # Determine target state group
                if all_pass:
                    target_group = "completed"
                elif any_started:
                    target_group = "started"
                else:
                    target_group = "unstarted"

                state_id = find_state_id_for_group(target_group, states)
                if not state_id:
                    result.skipped += 1
                    continue

                try:
                    client.update_work_item(parent_id, {"state": state_id})
                    set_setting(hash_key, agg_hash)
                    result.pushed += 1
                    logger.debug(
                        "Pushed aggregated status %s for parent %s (%d features)",
                        target_group, parent_id, len(group),
                    )
                except PlanningApiError as e:
                    result.errors += 1
                    logger.warning(
                        "Failed to push aggregated status for parent %s: %s",
                        parent_id, e,
                    )

        # --- Mode 3: Container sync — aggregate sub-story status onto Plane parent containers ---
        # Sub-stories have both planning_work_item_id (their own) AND
        # planning_parent_work_item_id (the Feature container they belong to in Plane).
        # We never import containers into mq-devEngine, so this is the only way to
        # keep them up-to-date in Plane.
        container_children = session.query(Feature).filter(
            Feature.planning_work_item_id.isnot(None),
            Feature.planning_parent_work_item_id.isnot(None),
        ).all()

        if container_children:
            container_groups: dict[str, list] = defaultdict(list)
            for feat in container_children:
                container_groups[feat.planning_parent_work_item_id].append(feat)

            root = Path(__file__).parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from registry import get_setting, set_setting

            for parent_uuid, children in container_groups.items():
                all_pass, any_started = _compute_aggregated_status(children)
                passes_count = sum(1 for f in children if (f.passes or False))
                in_progress_count = sum(1 for f in children if (f.in_progress or False))
                agg_hash = f"container:{passes_count}:{in_progress_count}:{len(children)}"

                hash_key = f"planning_container_hash:{parent_uuid}:{project_dir.name}"
                if get_setting(hash_key) == agg_hash:
                    result.skipped += 1
                    continue

                if all_pass:
                    target_group = "completed"
                elif any_started:
                    target_group = "started"
                else:
                    target_group = "unstarted"

                state_id = find_state_id_for_group(target_group, states)
                if not state_id:
                    result.skipped += 1
                    continue

                try:
                    client.update_work_item(parent_uuid, {"state": state_id})
                    set_setting(hash_key, agg_hash)
                    result.pushed += 1
                    logger.info(
                        "Container %s → %s (%d/%d children done)",
                        parent_uuid[:8], target_group, passes_count, len(children),
                    )
                except PlanningApiError as e:
                    result.errors += 1
                    logger.warning("Failed container sync for %s: %s", parent_uuid[:8], e)

        # --- Mode 4: sync child task states back to Plane ---
        task_features = session.query(Feature).filter(
            Feature.planning_work_item_id.isnot(None),
        ).all()
        for feature in task_features:
            tasks = feature.tasks or []
            for task in tasks:
                plane_id = task.get("planning_work_item_id")
                if not plane_id:
                    continue
                target_group = "completed" if task.get("done") else "unstarted"
                # Use a hash to avoid redundant API calls
                task_hash_key = f"task_state_hash:{plane_id}"
                from registry import get_setting as _get_setting, set_setting as _set_setting
                if _get_setting(task_hash_key) == target_group:
                    continue
                state_id = find_state_id_for_group(target_group, states)
                if not state_id:
                    continue
                try:
                    client.update_work_item(plane_id, {"state": state_id})
                    _set_setting(task_hash_key, target_group)
                    result.pushed += 1
                except PlanningApiError as e:
                    result.errors += 1
                    logger.warning("Failed task state sync for %s: %s", plane_id[:8], e)

        session.commit()

    logger.info(
        "Outbound sync: %d pushed, %d skipped, %d errors",
        result.pushed, result.skipped, result.errors,
    )
    return result


def outbound_comments_sync(
    client: PlanningApiClient,
    project_dir: Path,
) -> dict:
    """Push AC labels and escalation reasons as comments on Plane work items.

    Two triggers:
    1. Escalation: feature.review_status == "needs_human_review" and escalation_reason set
       → Comment on issue + set state to 'blocked' group
    2. AC labels: feature.ac_labels contains "human-only" entries
       → Comment listing which ACs need human verification (posted once)

    Uses registry settings to prevent duplicate comments.

    Returns:
        Dict with pushed/skipped/errors counts.
    """
    _, Feature = _get_db_classes()
    root = Path(__file__).parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from registry import get_setting, set_setting

    counts = {"pushed": 0, "skipped": 0, "errors": 0}

    states = client.list_states()

    with _get_db_session(project_dir) as session:
        features = session.query(Feature).filter(
            Feature.planning_work_item_id.isnot(None)
        ).all()

        for feature in features:
            issue_id = feature.planning_work_item_id

            # --- 1. Escalation comment ---
            if feature.review_status == "needs_human_review" and feature.escalation_reason:
                hash_key = f"planning_escalation_comment:{issue_id}"
                current_hash = f"esc:{hash(feature.escalation_reason)}"
                if get_setting(hash_key) != current_hash:
                    try:
                        reason_html = feature.escalation_reason.replace("\n", "<br>")
                        comment_html = (
                            "<p><strong>🔴 Escalatie: vereist menselijk oordeel</strong></p>"
                            f"<p>{reason_html}</p>"
                            "<p><em>De testing agent kon dit acceptatiecriterium niet automatisch verificeren. "
                            "Jouw beoordeling is vereist voordat deze story als Done kan worden gemarkeerd.</em></p>"
                        )
                        client.create_issue_comment(issue_id, comment_html)

                        # Try to move to 'blocked' state group
                        blocked_state = find_state_id_for_group("blocked", states)
                        if not blocked_state:
                            # Fall back to 'unstarted' if no blocked group
                            blocked_state = find_state_id_for_group("unstarted", states)
                        if blocked_state:
                            client.update_work_item(issue_id, {"state": blocked_state})

                        set_setting(hash_key, current_hash)
                        counts["pushed"] += 1
                        logger.info(
                            "Posted escalation comment for feature %d (%s) on Plane issue %s",
                            feature.id, feature.name, issue_id,
                        )
                    except PlanningApiError as e:
                        counts["errors"] += 1
                        logger.warning(
                            "Failed to post escalation comment for feature %d: %s",
                            feature.id, e,
                        )
                else:
                    counts["skipped"] += 1

            # --- 2. AC labels comment (human-only ACs) ---
            ac_labels = feature.ac_labels or []
            steps = feature.steps or []
            human_only_acs = [
                steps[i] for i, lbl in enumerate(ac_labels)
                if lbl == "human-only" and i < len(steps)
            ]

            if human_only_acs:
                hash_key = f"planning_ac_labels_comment:{issue_id}"
                current_hash = f"ac:{hash(str(ac_labels))}"
                if get_setting(hash_key) != current_hash:
                    try:
                        ac_items = "".join(
                            f"<li>{ac}</li>" for ac in human_only_acs
                        )
                        comment_html = (
                            "<p><strong>🔍 AC-kwaliteitsreview (architect agent)</strong></p>"
                            f"<p>De volgende {len(human_only_acs)} acceptatiecriteria vereisen "
                            "menselijk oordeel — ze kunnen niet automatisch worden geverificeerd:</p>"
                            f"<ul>{ac_items}</ul>"
                            "<p><em>Overige ACs worden automatisch getest door de testing agent.</em></p>"
                        )
                        client.create_issue_comment(issue_id, comment_html)
                        set_setting(hash_key, current_hash)
                        counts["pushed"] += 1
                        logger.info(
                            "Posted AC labels comment for feature %d (%s): %d human-only ACs",
                            feature.id, feature.name, len(human_only_acs),
                        )
                    except PlanningApiError as e:
                        counts["errors"] += 1
                        logger.warning(
                            "Failed to post AC labels comment for feature %d: %s",
                            feature.id, e,
                        )
                else:
                    counts["skipped"] += 1

    logger.info(
        "Comments sync: %d pushed, %d skipped, %d errors",
        counts["pushed"], counts["skipped"], counts["errors"],
    )
    return counts
