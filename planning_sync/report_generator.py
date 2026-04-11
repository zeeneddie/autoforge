"""Sprint demo report generator.

Reads manifest.json (screenshots) and generates a self-contained HTML report
at `releases/sprint-N-demo-report.html`.

The report is portable (inline base64 screenshots) and contains:
  - Header: project, sprint, date, evaluator badge (if available)
  - Per journey: title + numbered steps with screenshots / narrative frames
  - Evidence summary table
  - Evaluator result block (if evaluator_result.json is present)

Usage:
    from planning_sync.report_generator import generate_report

    report_path = generate_report(
        project_dir=Path("/opt/projecten/eddie/tipparena"),
        sprint=3,
    )
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_TIER_COLOURS = {
    "T1": "#22c55e",
    "T2": "#3b82f6",
    "T3": "#a855f7",
    "T4": "#eab308",
    "T5": "#6b7280",
}

_TIER_LABELS = {
    "T1": "T1 Screenshot",
    "T2": "T2 API Response",
    "T3": "T3 Test Output",
    "T4": "T4 Code Reference",
    "T5": "T5 Narrative",
}


def generate_report(
    project_dir: Path,
    sprint: int,
    manifest_path: Path | None = None,
    evaluator_result_path: Path | None = None,
) -> Path:
    """Generate an HTML sprint demo report.

    Args:
        project_dir: Root of the project.
        sprint: Sprint number.
        manifest_path: Path to manifest.json. Defaults to
                       releases/screenshots/manifest.json.
        evaluator_result_path: Optional path to evaluator-result.json.

    Returns:
        Path to the generated HTML report.
    """
    releases_dir = project_dir / "releases"
    screenshots_dir = releases_dir / "screenshots"

    if manifest_path is None:
        manifest_path = screenshots_dir / "manifest.json"

    if evaluator_result_path is None:
        evaluator_result_path = releases_dir / "evaluator-result.json"

    manifest = _load_json(manifest_path) or {}
    evaluator = _load_json(evaluator_result_path) if evaluator_result_path.exists() else None

    project_name = project_dir.name
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = _render_report(
        project_name=project_name,
        sprint=sprint,
        generated_at=generated_at,
        manifest=manifest,
        screenshots_dir=screenshots_dir,
        evaluator=evaluator,
    )

    out_path = releases_dir / f"sprint-{sprint}-demo-report.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("Demo report written to %s (%d bytes)", out_path, len(html))
    return out_path


# --- JSON helpers ---

def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Could not read %s: %s", path, e)
        return None


def _img_to_base64(path: Path) -> str | None:
    try:
        data = path.read_bytes()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except Exception:
        return None


# --- HTML rendering ---

def _render_report(
    project_name: str,
    sprint: int,
    generated_at: str,
    manifest: dict,
    screenshots_dir: Path,
    evaluator: dict | None,
) -> str:
    journeys = manifest.get("journeys", [])
    total_steps = sum(len(j.get("steps", [])) for j in journeys)
    screenshot_count = sum(
        1 for j in journeys for s in j.get("steps", [])
        if s.get("type", "screenshot") == "screenshot"
    )

    # Evaluator badge
    if evaluator:
        passed = evaluator.get("passed", False)
        score = evaluator.get("sprint_score", 0)
        badge_cls = "badge-pass" if passed else "badge-fail"
        badge_text = f"Evaluator: {'PASSED' if passed else 'FAILED'} ({score:.1f}/10)"
    else:
        badge_cls = "badge-unknown"
        badge_text = "Evaluator: niet uitgevoerd"

    journeys_html = "\n".join(
        _render_journey(j, screenshots_dir) for j in journeys
    )
    evaluator_html = _render_evaluator(evaluator) if evaluator else ""

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sprint {sprint} Demo Report — {project_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f1117; color: #e2e8f0; line-height: 1.6; }}
  .header {{ background: #1a1d2e; border-bottom: 1px solid #2d3148; padding: 24px 40px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }}
  .header h1 {{ font-size: 1.4rem; font-weight: 700; color: #fff; }}
  .header .meta {{ font-size: 0.85rem; color: #94a3b8; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; margin-left: auto; }}
  .badge-pass {{ background: #14532d; color: #4ade80; }}
  .badge-fail {{ background: #450a0a; color: #f87171; }}
  .badge-unknown {{ background: #1e293b; color: #94a3b8; }}
  .stats {{ background: #1a1d2e; border-bottom: 1px solid #2d3148; padding: 12px 40px; display: flex; gap: 32px; font-size: 0.85rem; color: #94a3b8; }}
  .stats strong {{ color: #e2e8f0; }}
  .content {{ max-width: 1200px; margin: 0 auto; padding: 32px 40px; }}
  .journey {{ background: #1a1d2e; border: 1px solid #2d3148; border-radius: 12px; margin-bottom: 32px; overflow: hidden; }}
  .journey-header {{ padding: 20px 24px; border-bottom: 1px solid #2d3148; display: flex; align-items: center; gap: 12px; }}
  .journey-header h2 {{ font-size: 1.1rem; font-weight: 600; color: #fff; }}
  .journey-id {{ background: #2d3148; color: #94a3b8; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-family: monospace; }}
  .step {{ display: grid; grid-template-columns: 48px 1fr; border-bottom: 1px solid #1e2235; }}
  .step:last-child {{ border-bottom: none; }}
  .step-num {{ background: #13152a; display: flex; align-items: flex-start; justify-content: center; padding: 16px 0; font-size: 0.8rem; font-weight: 700; color: #4f8ef7; }}
  .step-content {{ padding: 16px 20px; }}
  .step-title {{ font-weight: 600; color: #e2e8f0; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }}
  .tier-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
  .ac-tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }}
  .ac-tag {{ background: #0f172a; border: 1px solid #2d3148; color: #94a3b8; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-family: monospace; }}
  .screenshot {{ max-width: 100%; border-radius: 8px; border: 1px solid #2d3148; margin-top: 8px; }}
  .narrative-frame {{ max-width: 100%; border-radius: 8px; border: 2px solid #2d3148; margin-top: 8px; }}
  .no-screenshot {{ background: #0f172a; border: 1px dashed #2d3148; border-radius: 8px; padding: 24px; color: #475569; font-size: 0.85rem; text-align: center; margin-top: 8px; }}
  .evaluator {{ background: #1a1d2e; border: 1px solid #2d3148; border-radius: 12px; margin-top: 32px; overflow: hidden; }}
  .evaluator-header {{ padding: 16px 24px; border-bottom: 1px solid #2d3148; display: flex; align-items: center; gap: 12px; }}
  .evaluator-header h2 {{ font-size: 1rem; font-weight: 600; }}
  .story-card {{ padding: 16px 20px; border-bottom: 1px solid #1e2235; display: flex; align-items: center; gap: 16px; }}
  .story-card:last-child {{ border-bottom: none; }}
  .story-score {{ font-size: 1.5rem; font-weight: 700; min-width: 48px; text-align: center; }}
  .score-pass {{ color: #4ade80; }}
  .score-warn {{ color: #facc15; }}
  .score-fail {{ color: #f87171; }}
  .story-name {{ font-weight: 600; color: #e2e8f0; }}
  .story-issues {{ font-size: 0.8rem; color: #94a3b8; margin-top: 4px; }}
  .overall {{ background: #0f172a; border: 1px solid #2d3148; border-radius: 8px; padding: 16px 20px; margin: 16px 24px; font-size: 0.9rem; color: #94a3b8; line-height: 1.7; }}
  .footer {{ text-align: center; padding: 24px; color: #475569; font-size: 0.8rem; border-top: 1px solid #1e2235; margin-top: 40px; }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Sprint {sprint} — Demo Report</h1>
    <div class="meta">{project_name} &nbsp;·&nbsp; {generated_at}</div>
  </div>
  <span class="badge {badge_cls}">{badge_text}</span>
</div>

<div class="stats">
  <span>Journeys: <strong>{len(journeys)}</strong></span>
  <span>Stappen: <strong>{total_steps}</strong></span>
  <span>Screenshots: <strong>{screenshot_count}</strong></span>
  {f'<span>Sprint score: <strong>{evaluator.get("sprint_score", 0):.1f}/10</strong></span>' if evaluator else ''}
  {f'<span>Stories passed: <strong>{evaluator.get("stories_passed", 0)}/{evaluator.get("stories_total", 0)}</strong></span>' if evaluator else ''}
</div>

<div class="content">
{journeys_html}
{evaluator_html}
</div>

<div class="footer">
  Gegenereerd door mq-devEngine &nbsp;·&nbsp; {generated_at}
</div>

</body>
</html>"""


def _render_journey(journey: dict, screenshots_dir: Path) -> str:
    j_id = journey.get("id", "")
    j_title = journey.get("title", "Onbekend")
    steps = journey.get("steps", [])

    steps_html = "\n".join(_render_step(s, screenshots_dir) for s in steps)

    return f"""<div class="journey">
  <div class="journey-header">
    <span class="journey-id">{j_id}</span>
    <h2>{_esc(j_title)}</h2>
  </div>
  {steps_html}
</div>"""


def _render_step(step: dict, screenshots_dir: Path) -> str:
    step_num = step.get("step", "?")
    title = step.get("title", "")
    step_type = step.get("type", "screenshot")
    ac_refs = step.get("ac_ref", [])
    evidence_tier = step.get("evidence_tier", "T1" if step_type == "screenshot" else "T5")
    file_name = step.get("file", "")

    tier_colour = _TIER_COLOURS.get(evidence_tier, "#6b7280")
    tier_label = _TIER_LABELS.get(evidence_tier, evidence_tier)

    ac_html = ""
    if ac_refs:
        tags = "".join(f'<span class="ac-tag">{_esc(r)}</span>' for r in ac_refs)
        ac_html = f'<div class="ac-tags">{tags}</div>'

    img_html = ""
    if file_name:
        img_path = screenshots_dir / file_name
        b64 = _img_to_base64(img_path)
        if b64:
            img_class = "narrative-frame" if step_type == "narrative" else "screenshot"
            img_html = f'<img src="{b64}" class="{img_class}" alt="{_esc(title)}" loading="lazy">'
        else:
            img_html = f'<div class="no-screenshot">Screenshot niet gevonden: {_esc(file_name)}</div>'

    return f"""<div class="step">
  <div class="step-num">{step_num}</div>
  <div class="step-content">
    <div class="step-title">
      {_esc(title)}
      <span class="tier-badge" style="background:{tier_colour}20; color:{tier_colour}; border:1px solid {tier_colour}40">{tier_label}</span>
    </div>
    {ac_html}
    {img_html}
  </div>
</div>"""


def _render_evaluator(evaluator: dict) -> str:
    passed = evaluator.get("passed", False)
    score = evaluator.get("sprint_score", 0)
    stories = evaluator.get("stories", [])
    overall = evaluator.get("overall", "")
    dod_met = evaluator.get("dod_met", False)
    demo_data_warning = evaluator.get("demo_data_warning", False)

    badge_cls = "badge-pass" if passed else "badge-fail"
    dod_colour = "#4ade80" if dod_met else "#f87171"

    stories_html = "\n".join(_render_story_eval(s) for s in stories)
    overall_html = f'<div class="overall">{_esc(overall)}</div>' if overall else ""
    warning_html = ""
    if demo_data_warning:
        warning_html = '<div style="background:#422006; border:1px solid #92400e; border-radius:8px; padding:12px 20px; margin:12px 24px; font-size:0.85rem; color:#fbbf24;">⚠ Demo data warning: meerdere stories hebben alleen sparse bewijs. Voeg meer demo-data toe.</div>'

    return f"""<div class="evaluator">
  <div class="evaluator-header">
    <h2>AI Evaluator Resultaat</h2>
    <span class="badge {badge_cls}">Sprint score: {score:.1f}/10</span>
    <span style="color:{dod_colour}; font-size:0.85rem;">DoD: {'voldaan' if dod_met else 'NIET voldaan'}</span>
  </div>
  {warning_html}
  {overall_html}
  {stories_html}
</div>"""


def _render_story_eval(story: dict) -> str:
    story_id = story.get("story_id", "")
    title = story.get("title", "")
    score = story.get("score", 0)
    passed = story.get("passed", False)
    issues = story.get("issues", [])

    if score >= 8:
        score_cls = "score-pass"
    elif score >= 6:
        score_cls = "score-warn"
    else:
        score_cls = "score-fail"

    status = "PASS" if passed else "FAIL"
    issues_html = ""
    if issues:
        items = "".join(f"<li>{_esc(i)}</li>" for i in issues)
        issues_html = f'<div class="story-issues"><ul>{items}</ul></div>'

    return f"""<div class="story-card">
  <div class="story-score {score_cls}">{score}</div>
  <div>
    <div class="story-name">[{status}] {_esc(story_id)} — {_esc(title)}</div>
    {issues_html}
  </div>
</div>"""


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
