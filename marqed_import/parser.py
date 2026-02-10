"""Parse MarQed directory tree into in-memory entity tree.

MarQed directory layout:
    project/
      project.md
      epics/EPIC-001-name/
        epic.md
        features/FEATURE-001-name/
          feature.md
          stories/STORY-001-name/
            story.md
            tasks/TASK-001.md
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Priority mapping from MarQed keywords to Plane priorities
_PRIORITY_MAP = {
    "urgent": "urgent",
    "critical": "urgent",
    "high": "high",
    "medium": "medium",
    "normal": "medium",
    "low": "low",
    "none": "none",
}

# Status mapping from MarQed keywords to Plane state groups
_STATUS_MAP = {
    "backlog": "backlog",
    "todo": "unstarted",
    "planned": "unstarted",
    "in progress": "started",
    "in-progress": "started",
    "active": "started",
    "done": "completed",
    "completed": "completed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}

# Regex for H1 title: # IDENTIFIER | Name
_H1_RE = re.compile(r"^#\s+([A-Z]+-\d+)\s*\|\s*(.+)$")
# Regex for frontmatter-style field: **Key:** Value
_FRONTMATTER_RE = re.compile(r"^\*\*(\w[\w\s]*):\*\*\s*(.+)$")
# AC section headers
_AC_HEADER_RE = re.compile(
    r"^#{1,3}\s*(acceptance\s+criteria|ac:|definition\s+of\s+done)",
    re.IGNORECASE,
)
# Checkbox line
_CHECKBOX_RE = re.compile(r"^-\s*\[[ x]\]\s*(.+)$", re.IGNORECASE)
# GWT (Given/When/Then)
_GWT_RE = re.compile(r"^(given|when|then|and)\b", re.IGNORECASE)
# Dependency line: Depends on: FEATURE-001, STORY-002
_DEPENDS_RE = re.compile(r"^\*\*depends\s+on:\*\*\s*(.+)$", re.IGNORECASE)


@dataclass
class MarQedEntity:
    """A parsed MarQed entity from a markdown file."""

    entity_type: str  # "project", "epic", "feature", "story", "task"
    identifier: str  # "EPIC-001", "FEATURE-001", etc.
    name: str
    priority: str = "none"
    status: str = "backlog"
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    children: list[MarQedEntity] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract **Key:** Value pairs from markdown text."""
    result: dict[str, str] = {}
    for line in text.split("\n"):
        m = _FRONTMATTER_RE.match(line.strip())
        if m:
            key = m.group(1).strip().lower()
            value = m.group(2).strip()
            result[key] = value
    return result


def _extract_acceptance_criteria(text: str) -> list[str]:
    """Extract acceptance criteria from markdown text.

    Recognises AC section headers, checkbox items, and Given/When/Then.
    """
    if not text:
        return []

    lines = text.split("\n")
    criteria: list[str] = []
    in_ac_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _AC_HEADER_RE.match(stripped):
            in_ac_section = True
            continue

        if in_ac_section:
            # New section header ends AC section
            if stripped.startswith("#") and not _AC_HEADER_RE.match(stripped):
                in_ac_section = False
                continue

            cb = _CHECKBOX_RE.match(stripped)
            if cb:
                criteria.append(cb.group(1).strip())
                continue

            if _GWT_RE.match(stripped):
                criteria.append(stripped)
                continue

            # Plain list item
            if stripped.startswith("- ") or stripped.startswith("* "):
                criteria.append(stripped[2:].strip())
                continue

    return criteria


def parse_markdown_file(path: Path, entity_type: str) -> MarQedEntity | None:
    """Parse a single MarQed markdown file into a MarQedEntity.

    Returns None if the file cannot be parsed.
    """
    if not path.exists():
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Cannot read %s: %s", path, e)
        return None

    # Parse H1 title
    identifier = ""
    name = ""
    for line in text.split("\n"):
        m = _H1_RE.match(line.strip())
        if m:
            identifier = m.group(1)
            name = m.group(2).strip()
            break
        # Fallback: plain H1 without identifier
        if line.strip().startswith("# ") and not identifier:
            name = line.strip()[2:].strip()

    # Derive identifier from directory name if not in H1
    if not identifier:
        # Directory name like EPIC-001-authentication -> EPIC-001
        dir_name = path.parent.name
        m = re.match(r"([A-Z]+-\d+)", dir_name)
        if m:
            identifier = m.group(1)
        else:
            # For files like TASK-001.md
            m = re.match(r"([A-Z]+-\d+)", path.stem)
            if m:
                identifier = m.group(1)

    if not name:
        name = identifier or path.stem

    # Parse frontmatter fields
    fm = parse_frontmatter(text)
    priority_raw = fm.get("priority", "none").lower()
    priority = _PRIORITY_MAP.get(priority_raw, "none")

    status_raw = fm.get("status", "backlog").lower()
    status = _STATUS_MAP.get(status_raw, "backlog")

    # Extract AC
    acceptance_criteria = _extract_acceptance_criteria(text)

    # Extract dependencies
    depends_on: list[str] = []
    for line in text.split("\n"):
        m = _DEPENDS_RE.match(line.strip())
        if m:
            deps = [d.strip() for d in m.group(1).split(",")]
            depends_on.extend(d for d in deps if d)

    # Description: everything except the frontmatter fields
    description = text.strip()

    return MarQedEntity(
        entity_type=entity_type,
        identifier=identifier,
        name=name,
        priority=priority,
        status=status,
        description=description,
        acceptance_criteria=acceptance_criteria,
        children=[],
        depends_on=depends_on,
    )


def parse_marqed_tree(root_dir: Path) -> MarQedEntity | None:
    """Parse an entire MarQed directory tree into a nested entity tree.

    Args:
        root_dir: Path to the MarQed project root directory.

    Returns:
        The root MarQedEntity (type="project") with nested children,
        or None if the directory is invalid.
    """
    root_dir = Path(root_dir)
    if not root_dir.is_dir():
        logger.error("MarQed root is not a directory: %s", root_dir)
        return None

    # Parse project.md
    project_md = root_dir / "project.md"
    if project_md.exists():
        project = parse_markdown_file(project_md, "project")
        if project is None:
            project = MarQedEntity(
                entity_type="project",
                identifier="PROJECT",
                name=root_dir.name,
            )
    else:
        project = MarQedEntity(
            entity_type="project",
            identifier="PROJECT",
            name=root_dir.name,
        )

    # Parse epics
    epics_dir = root_dir / "epics"
    if epics_dir.is_dir():
        for epic_dir in sorted(epics_dir.iterdir()):
            if not epic_dir.is_dir():
                continue
            epic_md = epic_dir / "epic.md"
            epic = parse_markdown_file(epic_md, "epic") if epic_md.exists() else None
            if epic is None:
                # Create from directory name
                m = re.match(r"([A-Z]+-\d+)-?(.*)", epic_dir.name)
                ident = m.group(1) if m else epic_dir.name
                ename = (m.group(2).replace("-", " ").strip() if m else epic_dir.name) or ident
                epic = MarQedEntity(
                    entity_type="epic", identifier=ident, name=ename
                )

            # Parse features within epic
            features_dir = epic_dir / "features"
            if features_dir.is_dir():
                for feat_dir in sorted(features_dir.iterdir()):
                    if not feat_dir.is_dir():
                        continue
                    feat_md = feat_dir / "feature.md"
                    feat = parse_markdown_file(feat_md, "feature") if feat_md.exists() else None
                    if feat is None:
                        m = re.match(r"([A-Z]+-\d+)-?(.*)", feat_dir.name)
                        ident = m.group(1) if m else feat_dir.name
                        fname = (m.group(2).replace("-", " ").strip() if m else feat_dir.name) or ident
                        feat = MarQedEntity(
                            entity_type="feature", identifier=ident, name=fname
                        )

                    # Parse stories within feature
                    stories_dir = feat_dir / "stories"
                    if stories_dir.is_dir():
                        for story_dir in sorted(stories_dir.iterdir()):
                            if not story_dir.is_dir():
                                continue
                            story_md = story_dir / "story.md"
                            story = parse_markdown_file(story_md, "story") if story_md.exists() else None
                            if story is None:
                                m = re.match(r"([A-Z]+-\d+)-?(.*)", story_dir.name)
                                ident = m.group(1) if m else story_dir.name
                                sname = (m.group(2).replace("-", " ").strip() if m else story_dir.name) or ident
                                story = MarQedEntity(
                                    entity_type="story", identifier=ident, name=sname
                                )

                            # Parse tasks within story
                            tasks_dir = story_dir / "tasks"
                            if tasks_dir.is_dir():
                                for task_file in sorted(tasks_dir.glob("*.md")):
                                    task = parse_markdown_file(task_file, "task")
                                    if task:
                                        story.children.append(task)

                            feat.children.append(story)

                    epic.children.append(feat)

            project.children.append(epic)

    return project
