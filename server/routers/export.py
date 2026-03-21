"""
Export Router
=============

Export project features and test reports as DOCX / PDF / PPTX via mq-office.

Usage:
    GET /api/export/{project_name}?format=docx        → feature list as Word document
    GET /api/export/{project_name}?format=pdf         → feature list as PDF
    GET /api/export/{project_name}?format=pptx        → feature list as PowerPoint
    GET /api/export/{project_name}/test-report?format=docx|pdf   → test report document
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..utils.project_helpers import get_project_path as _get_project_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])

MQ_OFFICE_URL = os.environ.get("MQ_OFFICE_URL", "http://localhost:8091")

# Output format → file extension mapping
_EXT = {"docx": "docx", "pdf": "pdf", "pptx": "pptx"}
_MIMETYPE = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _get_project_or_404(project_name: str) -> Path:
    project_dir = _get_project_path(project_name)
    if not project_dir:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")
    return project_dir


def _build_features_markdown(project_name: str, project_dir: Path) -> str:
    """Generate Markdown document from features in the database."""
    from api.database import Feature, create_database

    _, SessionLocal = create_database(project_dir)
    session = SessionLocal()
    try:
        features = (
            session.query(Feature)
            .order_by(Feature.priority, Feature.id)
            .all()
        )
    finally:
        session.close()

    lines = [
        f"# Feature Deliverable — {project_name}",
        "",
        f"**Totaal:** {len(features)} features  ",
        f"**Afgerond:** {sum(1 for f in features if f.passes)}  ",
        f"**In uitvoering:** {sum(1 for f in features if f.in_progress)}  ",
        "",
        "---",
        "",
    ]

    categories: dict[str, list] = {}
    for f in features:
        categories.setdefault(f.category, []).append(f)

    for cat, cat_features in categories.items():
        lines.append(f"## {cat}")
        lines.append("")
        for f in cat_features:
            status = "✓" if f.passes else ("⟳" if f.in_progress else "○")
            lines.append(f"### {status} {f.name}")
            lines.append("")
            lines.append(f.description)
            lines.append("")
            if f.steps:
                lines.append("**Stappen:**")
                for step in f.steps:
                    lines.append(f"- {step}")
                lines.append("")
            if f.acceptance_criteria:
                lines.append("**Acceptatiecriteria:**")
                for ac in f.acceptance_criteria:
                    lines.append(f"- {ac}")
                lines.append("")

    return "\n".join(lines)


def _build_test_report_markdown(project_name: str, project_dir: Path) -> str:
    """Generate Markdown test report from feature + test_run data."""
    from api.database import Feature, TestRun, create_database
    from sqlalchemy import Integer, func

    _, SessionLocal = create_database(project_dir)
    session = SessionLocal()
    try:
        features = session.query(Feature).all()
        feature_map = {f.id: f for f in features}

        stats = session.query(
            TestRun.feature_id,
            func.count(TestRun.id).label("total"),
            func.sum(func.cast(TestRun.passed, Integer)).label("passes"),
        ).group_by(TestRun.feature_id).all()
    finally:
        session.close()

    total_features = len(features)
    passing = sum(1 for f in features if f.passes)

    lines = [
        f"# Test Rapport — {project_name}",
        "",
        f"**Features totaal:** {total_features}  ",
        f"**Geslaagd:** {passing}  ",
        f"**Slagingspercentage:** {round(passing / total_features * 100) if total_features else 0}%  ",
        "",
        "---",
        "",
        "## Resultaten per Feature",
        "",
        "| Feature | Categorie | Status | Test runs | Geslaagd |",
        "|---------|-----------|--------|-----------|----------|",
    ]

    run_map = {s.feature_id: s for s in stats}
    for f in sorted(features, key=lambda x: (x.category, x.priority)):
        status = "✓ Geslaagd" if f.passes else ("⟳ Bezig" if f.in_progress else "○ Open")
        s = run_map.get(f.id)
        total_runs = s.total if s else 0
        passing_runs = int(s.passes or 0) if s else 0
        lines.append(f"| {f.name} | {f.category} | {status} | {total_runs} | {passing_runs} |")

    lines.append("")
    return "\n".join(lines)


async def _convert_via_mq_office(md_content: str, fmt: str, filename: str) -> FileResponse:
    """Send markdown to mq-office and stream back the converted file."""
    ext = _EXT[fmt]

    # Write markdown to a named temp file so we can multipart-upload it
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp_in:
        tmp_in.write(md_content)
        tmp_in_path = Path(tmp_in.name)

    tmp_out_path = tmp_in_path.with_suffix(f".{ext}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(tmp_in_path, "rb") as f:
                resp = await client.post(
                    f"{MQ_OFFICE_URL}/api/v1/convert",
                    data={"source_format": "md", "target_format": fmt},
                    files={"file": (f"{filename}.md", f, "text/markdown")},
                )

        if resp.status_code != 200:
            detail = resp.text[:300] if resp.text else "mq-office error"
            raise HTTPException(status_code=502, detail=f"mq-office: {detail}")

        tmp_out_path.write_bytes(resp.content)
        return FileResponse(
            path=str(tmp_out_path),
            media_type=_MIMETYPE[fmt],
            filename=f"{filename}.{ext}",
            background=None,
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"mq-office niet bereikbaar op {MQ_OFFICE_URL}. "
                   "Start de service met: uvicorn app.main:app --port 8091",
        )
    finally:
        tmp_in_path.unlink(missing_ok=True)
        # tmp_out_path is cleaned up by FastAPI after FileResponse is sent


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{project_name}", summary="Export features als document")
async def export_features(
    project_name: str,
    format: Literal["docx", "pdf", "pptx"] = "docx",
):
    """Exporteer alle features van een project als DOCX, PDF of PPTX via mq-office."""
    project_dir = _get_project_or_404(project_name)
    md = _build_features_markdown(project_name, project_dir)
    return await _convert_via_mq_office(md, format, f"{project_name}-features")


@router.get("/{project_name}/test-report", summary="Export test rapport als document")
async def export_test_report(
    project_name: str,
    format: Literal["docx", "pdf"] = "pdf",
):
    """Exporteer het test rapport van een project als DOCX of PDF via mq-office."""
    project_dir = _get_project_or_404(project_name)
    md = _build_test_report_markdown(project_name, project_dir)
    return await _convert_via_mq_office(md, format, f"{project_name}-test-report")
