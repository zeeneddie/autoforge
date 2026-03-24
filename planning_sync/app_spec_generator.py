"""Generate app_spec.txt from BMAD artifacts (prd.md, architecture.md, epics.md).

Called automatically after import_cycle when no app_spec.txt exists yet.
Reads standard BMAD output files from {project_dir}/docs/ and writes
{project_dir}/prompts/app_spec.txt in the <project_specification> format
that mq-devEngine expects.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# BMAD artifact locations relative to project root
_BMAD_DOCS = {
    "prd": ["docs/prd.md"],
    "architecture": ["docs/architecture.md"],
    "epics": ["docs/epics.md"],
    "context": ["docs/project_context.md"],
}


def _find_doc(project_dir: Path, candidates: list[str]) -> Path | None:
    """Search for a doc in project_dir first, then case-variant siblings."""
    search_roots = [project_dir]

    # Also check sibling directories with different capitalisation.
    # Handles the case where BMAD docs live in e.g. TippArena/ while the
    # code project is registered as tipparena/.
    parent = project_dir.parent
    name_lower = project_dir.name.lower()
    for sibling in parent.iterdir():
        if sibling != project_dir and sibling.is_dir() and sibling.name.lower() == name_lower:
            search_roots.append(sibling)

    for root in search_roots:
        for rel in candidates:
            p = root / rel
            if p.exists():
                return p
    return None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _extract_section(text: str, heading: str, stop_headings: list[str] | None = None) -> str:
    """Extract content between *heading* and the next heading of equal/higher level."""
    pattern = rf"(?m)^(#{{{1,3}}}) {re.escape(heading)}\s*\n(.*?)(?=\n\1 |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return ""
    content = m.group(2).strip()
    if stop_headings:
        for stop in stop_headings:
            idx = content.find(f"\n## {stop}")
            if idx != -1:
                content = content[:idx].strip()
    return content


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip()
    return text


def _extract_overview(prd_text: str) -> str:
    """Pull executive summary or first meaningful paragraph from PRD."""
    text = _strip_frontmatter(prd_text)
    section = _extract_section(text, "Executive Summary")
    if section:
        # Take first 800 chars to keep it concise
        return section[:800].strip()
    # Fallback: first non-heading paragraph
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 40:
            return line[:800]
    return ""


def _extract_tech_stack(arch_text: str) -> str:
    """Extract selected stack table and key decisions from architecture.md."""
    text = _strip_frontmatter(arch_text)
    for heading in ("Geselecteerde Stack", "Technology Stack", "Stack", "Starter Template Evaluatie"):
        section = _extract_section(text, heading)
        if section:
            return section[:1200].strip()
    # Fallback: grep for table rows with known stack keywords
    lines = []
    for line in text.splitlines():
        if "|" in line and any(kw in line for kw in ("NestJS", "Next.js", "Prisma", "Supabase", "Turborepo", "TypeScript", "Frontend", "Backend", "ORM", "Monorepo")):
            lines.append(line)
    return "\n".join(lines[:20]) if lines else ""


def _extract_epics_summary(epics_text: str) -> str:
    """Extract the epic list overview (short descriptions per epic)."""
    text = _strip_frontmatter(epics_text)
    # Try to find an overview/list section
    section = _extract_section(text, "Epic List")
    if not section:
        section = _extract_section(text, "Epics")
    if section:
        return section[:2000].strip()
    # Fallback: collect all ## Epic N lines + their first paragraph
    lines = []
    capture = False
    for line in text.splitlines():
        if re.match(r"^## Epic \d+", line):
            lines.append(line)
            capture = True
            continue
        if capture:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
                capture = False
            elif re.match(r"^## Epic \d+", stripped):
                capture = True
    return "\n".join(lines[:60])


def _extract_stories_for_spec(epics_text: str) -> str:
    """Extract story names and acceptance criteria summaries."""
    text = _strip_frontmatter(epics_text)
    stories = []
    current_epic = ""
    for line in text.splitlines():
        if re.match(r"^## Epic \d+", line):
            current_epic = line.lstrip("#").strip()
        elif re.match(r"^### Story \d+\.\d+", line):
            story_name = line.lstrip("#").strip()
            stories.append(f"[{current_epic}] {story_name}")
    return "\n".join(f"- {s}" for s in stories)


def _extract_project_name(prd_text: str, fallback: str) -> str:
    text = _strip_frontmatter(prd_text)
    # Look for "# Product Requirements Document - ProjectName" or frontmatter project_name
    m = re.search(r"project_name:\s*['\"]?([^'\"\n]+)['\"]?", prd_text)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#\s+.*?[-—]\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return fallback


def generate_app_spec(project_dir: Path) -> Path:
    """Generate prompts/app_spec.txt from BMAD artifacts.

    Reads docs/prd.md, docs/architecture.md, docs/epics.md from project_dir.
    Writes {project_dir}/prompts/app_spec.txt.

    Returns the path to the written file.
    Raises FileNotFoundError if no BMAD artifacts found.
    """
    prd_path = _find_doc(project_dir, _BMAD_DOCS["prd"])
    arch_path = _find_doc(project_dir, _BMAD_DOCS["architecture"])
    epics_path = _find_doc(project_dir, _BMAD_DOCS["epics"])

    if not any([prd_path, arch_path, epics_path]):
        raise FileNotFoundError(
            f"No BMAD artifacts found in {project_dir}/docs/ "
            "(expected prd.md, architecture.md or epics.md)"
        )

    prd_text = _read(prd_path) if prd_path else ""
    arch_text = _read(arch_path) if arch_path else ""
    epics_text = _read(epics_path) if epics_path else ""

    project_name = _extract_project_name(prd_text, project_dir.name)
    overview = _extract_overview(prd_text)
    tech_stack = _extract_tech_stack(arch_text)
    epics_summary = _extract_epics_summary(epics_text)
    stories = _extract_stories_for_spec(epics_text)

    spec = f"""<!-- Auto-generated from BMAD artifacts by mq-devEngine planning_sync.
     Source: {project_dir}/docs/
     Do not edit manually — regenerate by deleting this file and re-importing a sprint.
-->

<project_specification>
  <project_name>{project_name}</project_name>

  <overview>
{overview}
  </overview>

  <technology_stack>
{tech_stack if tech_stack else "    See docs/architecture.md for full stack details."}
  </technology_stack>

  <source_type>brownfield</source_type>

  <project_root>{project_dir}</project_root>

  <bmad_artifacts>
    <prd>{prd_path or "not found"}</prd>
    <architecture>{arch_path or "not found"}</architecture>
    <epics>{epics_path or "not found"}</epics>
  </bmad_artifacts>

  <epics_overview>
{epics_summary}
  </epics_overview>

  <all_stories>
{stories}
  </all_stories>

</project_specification>
"""

    prompts_dir = project_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    spec_path = prompts_dir / "app_spec.txt"
    spec_path.write_text(spec, encoding="utf-8")

    logger.info("Generated app_spec.txt for %s at %s", project_name, spec_path)
    return spec_path
