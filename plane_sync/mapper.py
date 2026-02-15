"""Data mapper: converts Plane WorkItems to MQ DevEngine Features and back."""

from __future__ import annotations

import html
import logging
import re
from typing import Any

from .models import PlaneState, PlaneWorkItem

logger = logging.getLogger(__name__)

# Priority mapping: Plane string -> MQ DevEngine integer
PRIORITY_TO_INT: dict[str, int] = {
    "urgent": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "none": 5,
}

# Reverse: MQ DevEngine integer -> Plane string
INT_TO_PRIORITY: dict[int, str] = {v: k for k, v in PRIORITY_TO_INT.items()}


def _strip_html(html_str: str) -> str:
    """Convert HTML description to plain text."""
    if not html_str:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "\n", html_str)
    # Decode HTML entities
    text = html.unescape(text)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_steps_from_description(description: str) -> list[str]:
    """Extract numbered/bulleted steps from a description.

    Looks for lines starting with numbers, dashes, or asterisks.
    If no structured steps found, returns the description as a single step.
    """
    if not description:
        return []

    lines = description.split("\n")
    steps: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Match numbered items (1. 2. etc) or bulleted items (- * +)
        if re.match(r"^(\d+[\.\)]\s+|[-*+]\s+)", stripped):
            # Remove the bullet/number prefix
            step_text = re.sub(r"^(\d+[\.\)]\s+|[-*+]\s+)", "", stripped)
            if step_text:
                steps.append(step_text)

    if not steps and description.strip():
        # No structured steps found — use the whole description
        steps = [description.strip()]

    return steps


# Patterns that mark the start of an acceptance criteria section
_AC_HEADER_RE = re.compile(
    r"^(?:acceptance\s+criteria|ac:|definition\s+of\s+done|dod:)",
    re.IGNORECASE,
)

# Markdown checkbox pattern: - [ ] item  or  - [x] item
_CHECKBOX_RE = re.compile(r"^-\s*\[([ xX])\]\s+(.+)")

# Given/When/Then pattern
_GWT_RE = re.compile(r"^(given|when|then|and|but)\s+", re.IGNORECASE)


def _extract_acceptance_criteria(description: str) -> list[str]:
    """Extract acceptance criteria from a description.

    Recognises:
    - Section headers: "Acceptance Criteria", "AC:", "Definition of Done"
    - Checkbox markdown: ``- [ ] item`` and ``- [x] item``
    - Given/When/Then BDD-style criteria

    Returns a list of criteria strings, or an empty list if none found.
    """
    if not description:
        return []

    lines = description.split("\n")
    criteria: list[str] = []
    in_ac_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line is an AC section header
        if _AC_HEADER_RE.match(stripped):
            in_ac_section = True
            # The header itself might have criteria after a colon
            after_colon = stripped.split(":", 1)
            if len(after_colon) > 1 and after_colon[1].strip():
                criteria.append(after_colon[1].strip())
            continue

        # If we hit another section header while in AC section, stop
        if in_ac_section and stripped.startswith("#"):
            break

        if in_ac_section:
            # Checkbox items
            m = _CHECKBOX_RE.match(stripped)
            if m:
                criteria.append(m.group(2))
                continue
            # Numbered/bulleted items
            if re.match(r"^(\d+[\.\)]\s+|[-*+]\s+)", stripped):
                step_text = re.sub(r"^(\d+[\.\)]\s+|[-*+]\s+)", "", stripped)
                if step_text:
                    criteria.append(step_text)
                continue
            # Plain text lines in section
            if stripped:
                criteria.append(stripped)
            continue

        # Outside AC section: check for checkbox items (standalone AC)
        m = _CHECKBOX_RE.match(stripped)
        if m:
            criteria.append(m.group(2))
            continue

        # Given/When/Then lines outside AC section
        if _GWT_RE.match(stripped):
            criteria.append(stripped)

    return criteria


def state_group_for_id(
    state_id: str, states: list[PlaneState]
) -> str:
    """Look up the state group (backlog/unstarted/started/completed/cancelled)
    for a given state ID."""
    for state in states:
        if state.id == state_id:
            return state.group
    return "unstarted"  # safe default


def find_state_id_for_group(
    target_group: str, states: list[PlaneState]
) -> str | None:
    """Find the first state ID that belongs to the target group."""
    for state in states:
        if state.group == target_group:
            return state.id
    return None


def work_item_to_feature_dict(
    item: PlaneWorkItem,
    states: list[PlaneState],
    modules: dict[str, str] | None = None,
    parent_feature_ids: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Convert a Plane WorkItem to a dict suitable for creating an MQ DevEngine Feature.

    Args:
        item: The Plane work item.
        states: All project states (for state group lookup).
        modules: Optional dict of module_id -> module_name (for category).
        parent_feature_ids: Optional dict of plane_work_item_id -> feature_id
            (for resolving parent -> dependency).

    Returns:
        Dict with keys matching Feature model columns.
    """
    # Priority
    priority = PRIORITY_TO_INT.get(item.priority, 5)

    # Category from module
    category = "functional"  # default
    if modules and item.module and item.module in modules:
        category = modules[item.module]

    # Description: prefer stripped text, fall back to HTML conversion
    description = item.description_stripped or _strip_html(item.description_html)

    # Steps: prefer acceptance criteria over generic description steps
    steps = _extract_acceptance_criteria(description) or _parse_steps_from_description(description)

    # State -> passes / in_progress
    group = state_group_for_id(item.state, states)
    passes = group == "completed"
    in_progress = group == "started"

    # Dependencies from parent
    dependencies = None
    if item.parent and parent_feature_ids and item.parent in parent_feature_ids:
        dependencies = [parent_feature_ids[item.parent]]

    return {
        "name": item.name,
        "description": description or item.name,
        "priority": priority,
        "category": category,
        "steps": steps or [item.name],
        "passes": passes,
        "in_progress": in_progress,
        "dependencies": dependencies,
        "plane_work_item_id": item.id,
        "plane_updated_at": item.updated_at,
    }


def feature_status_to_plane_update(
    passes: bool,
    in_progress: bool,
    states: list[PlaneState],
) -> dict | None:
    """Convert MQ DevEngine feature status to a Plane work item update dict.

    Returns None if no state change is needed.
    """
    if passes:
        target_group = "completed"
    elif in_progress:
        target_group = "started"
    else:
        target_group = "unstarted"

    state_id = find_state_id_for_group(target_group, states)
    if not state_id:
        logger.warning("No Plane state found for group '%s'", target_group)
        return None

    return {"state": state_id}
