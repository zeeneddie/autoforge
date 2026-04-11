"""Demo capture: runs the project's demo-capture script after sprint completion.

Convention: if a project has a `releases/demo-capture.mjs` (Node.js/Playwright)
or `releases/demo-capture.py` (Python/Playwright) file, it is run automatically
when a sprint is closed via POST /complete-sprint.

The script receives APP_URL via environment variable so mq-devEngine can pass
the URL of the already-running dev server.

Output:
    releases/screenshots/       — screenshot PNG files
    releases/screenshots/manifest.json  — step metadata
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DemoCaptureResult:
    """Result of running demo capture."""

    success: bool
    screenshots_dir: Path | None = None
    manifest_path: Path | None = None
    screenshot_count: int = 0
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


def run_demo_capture(
    project_dir: Path,
    app_url: str | None = None,
) -> DemoCaptureResult:
    """Run the project's demo capture script if one exists.

    Looks for (in order):
      1. releases/demo-capture.mjs  — Node.js Playwright script
      2. releases/demo-capture.py   — Python Playwright script

    The script is run with APP_URL and SUPABASE_URL injected as env vars
    so projects don't need to hardcode the server URL.

    Args:
        project_dir: Root of the project being reviewed.
        app_url: URL of the running dev server. If None, the script's own
                 defaults are used (usually http://localhost:3000).

    Returns:
        DemoCaptureResult with paths to output files.
    """
    releases_dir = project_dir / "releases"

    # Find capture script
    mjs_script = releases_dir / "demo-capture.mjs"
    py_script = releases_dir / "demo-capture.py"

    if mjs_script.exists():
        script_path = mjs_script
        runner = _find_node()
        if not runner:
            return DemoCaptureResult(
                success=False,
                skipped=True,
                skip_reason="node not found in PATH — install Node.js to run demo capture",
            )
        cmd = [runner, str(script_path)]
    elif py_script.exists():
        script_path = py_script
        cmd = ["python", str(script_path)]
    else:
        return DemoCaptureResult(
            success=False,
            skipped=True,
            skip_reason="No demo capture script found (releases/demo-capture.mjs or .py)",
        )

    # Build environment
    env = os.environ.copy()
    if app_url:
        env["APP_URL"] = app_url
        logger.info("Demo capture: using app URL %s", app_url)

    logger.info("Running demo capture: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes max
        )
    except subprocess.TimeoutExpired:
        return DemoCaptureResult(
            success=False,
            error="Demo capture timed out after 180 seconds",
        )
    except FileNotFoundError as e:
        return DemoCaptureResult(
            success=False,
            error=f"Script runner not found: {e}",
        )

    if result.returncode != 0:
        logger.warning(
            "Demo capture failed (exit %d):\n%s",
            result.returncode,
            result.stderr[-1000:] if result.stderr else "(no stderr)",
        )
        return DemoCaptureResult(
            success=False,
            error=f"Demo capture exited {result.returncode}: {result.stderr[-500:]}",
        )

    # Collect results
    screenshots_dir = releases_dir / "screenshots"
    manifest_path = screenshots_dir / "manifest.json"

    screenshot_count = 0
    if screenshots_dir.exists():
        screenshot_count = len(list(screenshots_dir.glob("*.png")))

    if manifest_path.exists():
        logger.info(
            "Demo capture complete: %d screenshots in %s",
            screenshot_count,
            screenshots_dir,
        )
        return DemoCaptureResult(
            success=True,
            screenshots_dir=screenshots_dir,
            manifest_path=manifest_path,
            screenshot_count=screenshot_count,
        )

    # Script ran but no manifest — partial success
    logger.warning("Demo capture ran but manifest.json not found in %s", screenshots_dir)
    return DemoCaptureResult(
        success=True,
        screenshots_dir=screenshots_dir if screenshots_dir.exists() else None,
        screenshot_count=screenshot_count,
        error="manifest.json not written — capture may have partially failed",
    )


def get_manifest_summary(manifest_path: Path) -> dict:
    """Read manifest.json and return a compact summary for release notes."""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        journeys = data.get("journeys", [])
        total_steps = sum(len(j.get("steps", [])) for j in journeys)
        return {
            "journey_count": len(journeys),
            "total_steps": total_steps,
            "journeys": [
                {"id": j["id"], "title": j["title"], "steps": len(j.get("steps", []))}
                for j in journeys
            ],
        }
    except Exception as e:
        logger.warning("Could not parse manifest: %s", e)
        return {}


def _find_node() -> str | None:
    """Return path to node executable, or None if not available."""
    return shutil.which("node")
