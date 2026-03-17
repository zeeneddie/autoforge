"""
Stuck State Analyzer
====================

Analyzes stuck orchestrator states using an LLM to determine root cause and
suggest recovery options (retry, modify features, remove dependencies, skip).

Returns structured JSON with confidence scores per suggestion. The orchestrator
uses these scores to decide between auto-recovery (>= 0.8) and human-in-the-loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def analyze_stuck_state(
    project_dir: Path,
    stuck_info: dict[str, Any],
    feature_dicts: list[dict],
    model: str | None = None,
) -> dict[str, Any]:
    """Analyze a stuck orchestrator state with an LLM.

    Args:
        project_dir: Path to the project directory.
        stuck_info: Dict with failed_features, blocked_features, passing_count, total_count.
        feature_dicts: Full list of feature dicts from the database.
        model: Model to use (defaults to coding model from provider config).

    Returns:
        Dict with root_cause_analysis, human_summary, recommended_option,
        confidence, and suggestions list.
    """
    # Resolve model
    if model is None:
        model = _get_analysis_model()

    # Build the analysis prompt
    prompt = _build_prompt(project_dir, stuck_info, feature_dicts)

    # Call LLM via claude CLI subprocess
    try:
        result = await _call_claude(prompt, model)
        analysis = _parse_response(result)
        return analysis
    except Exception as e:
        logger.error("Stuck state analysis failed: %s", e)
        raise


def _get_analysis_model() -> str:
    """Get the model to use for stuck state analysis.

    Uses the analyst tier (highest capability) for maximum analysis quality.
    """
    try:
        from provider_config import get_provider_model_tiers
        from task_router import resolve_model_tier
        tiers = get_provider_model_tiers()
        return resolve_model_tier("analyst", tiers)
    except Exception:
        return "claude-sonnet-4-5"  # Safe fallback


def _build_prompt(
    project_dir: Path,
    stuck_info: dict[str, Any],
    feature_dicts: list[dict],
) -> str:
    """Build the analysis prompt with full context."""
    # Load app spec (first 3000 chars)
    app_spec = ""
    spec_path = project_dir / ".mq-devengine" / "prompts" / "app_spec.txt"
    if not spec_path.exists():
        spec_path = project_dir / "app_spec.txt"
    if spec_path.exists():
        try:
            app_spec = spec_path.read_text(encoding="utf-8")[:3000]
        except Exception:
            pass

    # Build feature status list
    feature_lines = []
    for fd in feature_dicts:
        status = "PASSING" if fd.get("passes") else "PENDING"
        fid = fd["id"]
        # Check if permanently failed
        for ff in stuck_info.get("failed_features", []):
            if ff["id"] == fid:
                status = f"FAILED (x{ff['failure_count']})"
                break
        for bf in stuck_info.get("blocked_features", []):
            if bf["id"] == fid:
                status = f"BLOCKED by {bf['blocked_by']}"
                break

        deps = fd.get("dependencies") or fd.get("depends_on") or []
        if isinstance(deps, str):
            try:
                deps = json.loads(deps)
            except (json.JSONDecodeError, TypeError):
                deps = []
        dep_str = f" [depends on: {deps}]" if deps else ""

        feature_lines.append(
            f"  #{fid} {fd.get('name', '?')} — {status}{dep_str}"
        )

    # Load agent logs for failed features (last 50 lines each)
    log_sections = []
    try:
        from api.database import AgentLog, create_database
        _, session_maker = create_database(project_dir)
        session = session_maker()
        try:
            for ff in stuck_info.get("failed_features", []):
                logs = (
                    session.query(AgentLog)
                    .filter(AgentLog.feature_id == ff["id"])
                    .order_by(AgentLog.id.desc())
                    .limit(50)
                    .all()
                )
                if logs:
                    lines = [log.line for log in reversed(logs)]
                    log_sections.append(
                        f"--- Agent logs for feature #{ff['id']} ({ff.get('name', '?')}) ---\n"
                        + "\n".join(lines[-50:])
                    )
        finally:
            session.close()
    except Exception as e:
        log_sections.append(f"(Could not load agent logs: {e})")

    prompt = f"""Je bent een expert software engineer die een vastgelopen build-systeem analyseert.

## Context

Een parallel orchestrator bouwt een applicatie door features toe te wijzen aan coding agents.
Sommige features zijn permanent gefaald (3 pogingen) waardoor afhankelijke features geblokkeerd zijn.

## App Specificatie (eerste 3000 chars)
{app_spec if app_spec else "(niet beschikbaar)"}

## Feature Status ({stuck_info['passing_count']}/{stuck_info['total_count']} passing)
{chr(10).join(feature_lines)}

## Agent Logs van Gefaalde Features
{chr(10).join(log_sections) if log_sections else "(geen logs beschikbaar)"}

## Opdracht

Analyseer waarom de gefaalde features faalden en wat de beste recovery-strategie is.

Antwoord ALLEEN met valid JSON in dit exacte formaat (geen markdown, geen uitleg buiten de JSON):
{{
  "root_cause_analysis": "Gedetailleerde uitleg van de root cause...",
  "human_summary": "Korte samenvatting (1-2 zinnen) voor de gebruiker",
  "recommended_option": "retry | modify | stop",
  "confidence": 0.85,
  "suggestions": [
    {{
      "type": "retry_feature | modify_feature | remove_dependency | skip_feature",
      "feature_id": 1,
      "confidence": 0.9,
      "reason": "Waarom deze actie helpt..."
    }}
  ]
}}

Regels voor confidence:
- >= 0.8: je bent redelijk zeker dat deze actie het probleem oplost
- 0.5-0.8: mogelijk, maar niet zeker — menselijke review nodig
- < 0.5: lage kans, beter om te stoppen en handmatig te kijken

Bij "modify_feature" suggesties, voeg ook een "changes" object toe:
{{"description": "Nieuwe feature beschrijving", "steps": ["stap 1", "stap 2"]}}

Bij "remove_dependency" suggesties, voeg ook "dependency_id" toe.
"""

    return prompt


async def _call_claude(prompt: str, model: str) -> str:
    """Call claude CLI as subprocess and return the text response."""
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError("claude CLI not found in PATH")

    cmd = [
        claude_path,
        "--print",
        "--output-format", "text",
        "--model", model,
        "--max-turns", "1",
        "-p", prompt,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"claude CLI failed (exit {proc.returncode}): {error_msg}")

    return stdout.decode("utf-8", errors="replace").strip()


def _parse_response(response: str) -> dict[str, Any]:
    """Parse the LLM response, extracting JSON from potentially wrapped output."""
    # Try direct JSON parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    import re
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find first { ... } block
    brace_start = response.find("{")
    brace_end = response.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        try:
            return json.loads(response[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            pass

    # Give up — return a stop fallback
    logger.warning("Could not parse LLM response as JSON: %s", response[:200])
    return {
        "root_cause_analysis": f"LLM response kon niet als JSON geparsed worden: {response[:500]}",
        "human_summary": "LLM analyse onleesbaar — handmatige review nodig",
        "recommended_option": "stop",
        "confidence": 0.0,
        "suggestions": [],
    }
