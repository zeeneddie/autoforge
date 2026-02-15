"""Import parsed MarQed entities into Plane as modules and work items."""

from __future__ import annotations

import logging
from pathlib import Path

from planning_sync.client import PlanningApiClient, PlanningApiError
from planning_sync.models import PlanningState

from .models import MarQedImportEntityResult, MarQedImportResult
from .parser import MarQedEntity, parse_marqed_tree

logger = logging.getLogger(__name__)

# Map MarQed priority strings to Plane priority values
_PRIORITY_TO_PLANE = {
    "urgent": "urgent",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "none": "none",
}

# Map MarQed status strings to Plane state groups
_STATUS_TO_GROUP = {
    "backlog": "backlog",
    "unstarted": "unstarted",
    "started": "started",
    "completed": "completed",
    "cancelled": "cancelled",
}


def _find_state_id(states: list[PlanningState], group: str) -> str | None:
    """Find a state ID matching the given group."""
    for s in states:
        if s.group == group:
            return s.id
    return None


def _build_description_html(entity: MarQedEntity) -> str:
    """Build HTML description from entity, including AC and dependencies."""
    parts = []

    if entity.description:
        # Use the raw markdown as plain text in the description
        parts.append(f"<p>{entity.description[:2000]}</p>")

    if entity.acceptance_criteria:
        parts.append("<h3>Acceptance Criteria</h3><ul>")
        for ac in entity.acceptance_criteria:
            parts.append(f"<li>{ac}</li>")
        parts.append("</ul>")

    if entity.depends_on:
        parts.append(
            f"<p><strong>Depends on:</strong> {', '.join(entity.depends_on)}</p>"
        )

    return "\n".join(parts) if parts else f"<p>{entity.name}</p>"


def import_to_planning(
    client: PlanningApiClient,
    marqed_dir: str | Path,
    cycle_id: str | None = None,
) -> MarQedImportResult:
    """Parse a MarQed directory and import entities into Plane.

    Import algorithm:
    1. Parse the MarQed tree
    2. Fetch Plane states for status mapping
    3. Per epic: create a Module
    4. Per feature: create a Work Item (linked to module)
    5. Per story: create a Sub-Work Item (parent=feature work item)
    6. Per task: create a Sub-Work Item (parent=story work item)
    7. Add work items to module
    8. Add all work items to cycle if cycle_id provided

    Args:
        client: Configured PlanningApiClient.
        marqed_dir: Path to the MarQed project root.
        cycle_id: Optional cycle ID to add all work items to.

    Returns:
        MarQedImportResult with details of all created entities.
    """
    result = MarQedImportResult()

    # 1. Parse
    tree = parse_marqed_tree(Path(marqed_dir))
    if tree is None:
        result.errors = 1
        result.entities.append(MarQedImportEntityResult(
            identifier="",
            name=str(marqed_dir),
            entity_type="project",
            planning_type="",
            action="error",
            error="Failed to parse MarQed directory tree",
        ))
        return result

    # 2. Fetch states
    try:
        states = client.list_states()
    except PlanningApiError as e:
        result.errors = 1
        result.entities.append(MarQedImportEntityResult(
            identifier="",
            name="states",
            entity_type="",
            planning_type="",
            action="error",
            error=f"Failed to fetch Plane states: {e}",
        ))
        return result

    # Collect all work item IDs for cycle assignment
    all_work_item_ids: list[str] = []

    # 3. Process epics
    for epic in tree.children:
        if epic.entity_type != "epic":
            continue

        result.total_entities += 1

        # Create module for epic
        module_id = None
        try:
            module = client.create_module({
                "name": f"{epic.identifier} | {epic.name}",
                "description": epic.description[:2000] if epic.description else "",
            })
            module_id = module.id
            result.modules_created += 1
            result.created += 1
            result.entities.append(MarQedImportEntityResult(
                identifier=epic.identifier,
                name=epic.name,
                entity_type="epic",
                planning_type="module",
                planning_id=module.id,
                action="created",
            ))
        except PlanningApiError as e:
            logger.warning("Failed to create module for %s: %s", epic.identifier, e)
            result.errors += 1
            result.entities.append(MarQedImportEntityResult(
                identifier=epic.identifier,
                name=epic.name,
                entity_type="epic",
                planning_type="module",
                action="error",
                error=str(e),
            ))
            continue

        # Items to link to this module
        module_work_item_ids: list[str] = []

        # 4. Process features within epic
        for feature in epic.children:
            if feature.entity_type != "feature":
                continue

            result.total_entities += 1

            state_id = _find_state_id(states, _STATUS_TO_GROUP.get(feature.status, "backlog"))
            wi_data = {
                "name": f"{feature.identifier} | {feature.name}",
                "description_html": _build_description_html(feature),
                "priority": _PRIORITY_TO_PLANE.get(feature.priority, "none"),
            }
            if state_id:
                wi_data["state"] = state_id

            try:
                wi = client.create_work_item(wi_data)
                feature_wi_id = wi.id
                module_work_item_ids.append(feature_wi_id)
                all_work_item_ids.append(feature_wi_id)
                result.work_items_created += 1
                result.created += 1
                result.entities.append(MarQedImportEntityResult(
                    identifier=feature.identifier,
                    name=feature.name,
                    entity_type="feature",
                    planning_type="work_item",
                    planning_id=wi.id,
                    action="created",
                ))
            except PlanningApiError as e:
                logger.warning("Failed to create work item for %s: %s", feature.identifier, e)
                result.errors += 1
                result.entities.append(MarQedImportEntityResult(
                    identifier=feature.identifier,
                    name=feature.name,
                    entity_type="feature",
                    planning_type="work_item",
                    action="error",
                    error=str(e),
                ))
                continue

            # 5. Process stories within feature
            for story in feature.children:
                if story.entity_type != "story":
                    continue

                result.total_entities += 1

                state_id = _find_state_id(states, _STATUS_TO_GROUP.get(story.status, "backlog"))
                story_data = {
                    "name": f"{story.identifier} | {story.name}",
                    "description_html": _build_description_html(story),
                    "priority": _PRIORITY_TO_PLANE.get(story.priority, "none"),
                    "parent": feature_wi_id,
                }
                if state_id:
                    story_data["state"] = state_id

                try:
                    story_wi = client.create_work_item(story_data)
                    story_wi_id = story_wi.id
                    module_work_item_ids.append(story_wi_id)
                    all_work_item_ids.append(story_wi_id)
                    result.work_items_created += 1
                    result.created += 1
                    result.entities.append(MarQedImportEntityResult(
                        identifier=story.identifier,
                        name=story.name,
                        entity_type="story",
                        planning_type="sub_work_item",
                        planning_id=story_wi.id,
                        action="created",
                    ))
                except PlanningApiError as e:
                    logger.warning("Failed to create sub-item for %s: %s", story.identifier, e)
                    result.errors += 1
                    result.entities.append(MarQedImportEntityResult(
                        identifier=story.identifier,
                        name=story.name,
                        entity_type="story",
                        planning_type="sub_work_item",
                        action="error",
                        error=str(e),
                    ))
                    continue

                # 6. Process tasks within story
                for task in story.children:
                    if task.entity_type != "task":
                        continue

                    result.total_entities += 1

                    state_id = _find_state_id(states, _STATUS_TO_GROUP.get(task.status, "backlog"))
                    task_data = {
                        "name": f"{task.identifier} | {task.name}",
                        "description_html": _build_description_html(task),
                        "priority": _PRIORITY_TO_PLANE.get(task.priority, "none"),
                        "parent": story_wi_id,
                    }
                    if state_id:
                        task_data["state"] = state_id

                    try:
                        task_wi = client.create_work_item(task_data)
                        module_work_item_ids.append(task_wi.id)
                        all_work_item_ids.append(task_wi.id)
                        result.work_items_created += 1
                        result.created += 1
                        result.entities.append(MarQedImportEntityResult(
                            identifier=task.identifier,
                            name=task.name,
                            entity_type="task",
                            planning_type="sub_work_item",
                            planning_id=task_wi.id,
                            action="created",
                        ))
                    except PlanningApiError as e:
                        logger.warning("Failed to create sub-item for %s: %s", task.identifier, e)
                        result.errors += 1
                        result.entities.append(MarQedImportEntityResult(
                            identifier=task.identifier,
                            name=task.name,
                            entity_type="task",
                            planning_type="sub_work_item",
                            action="error",
                            error=str(e),
                        ))

        # 7. Link work items to module
        if module_id and module_work_item_ids:
            try:
                client.add_work_items_to_module(module_id, module_work_item_ids)
            except PlanningApiError as e:
                logger.warning("Failed to add items to module %s: %s", module_id, e)

    # 8. Add all work items to cycle
    if cycle_id and all_work_item_ids:
        try:
            client.add_work_items_to_cycle(cycle_id, all_work_item_ids)
        except PlanningApiError as e:
            logger.warning("Failed to add items to cycle %s: %s", cycle_id, e)

    return result
