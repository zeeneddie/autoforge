"""Demo seed runner: seeds demo data before demo capture.

Convention: if a project has a `releases/demo-seed.mjs` (Node.js)
or `releases/demo-seed.py` (Python), it is run before demo-capture.mjs
to inject a deterministic set of demo data into the app's database.

The seed script:
  - Is idempotent: running it multiple times produces the same result
  - Writes `releases/demo-state.json` describing what was seeded
    (IDs, slugs, counts — used by demo-capture.mjs for navigation)
  - Receives APP_URL via environment variable

Output:
    releases/demo-state.json   — seeded entities (IDs, names, counts)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_SEED_TIMEOUT_SECONDS = 60


@dataclass
class DemoSeedResult:
    """Result of running the demo seed script."""

    success: bool
    state_path: Path | None = None
    entities: dict = field(default_factory=dict)
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


def run_demo_seed(
    project_dir: Path,
    app_url: str | None = None,
) -> DemoSeedResult:
    """Run the project's demo seed script if one exists.

    Looks for (in order):
      1. releases/demo-seed.mjs  — Node.js seed script
      2. releases/demo-seed.py   — Python seed script

    The script receives APP_URL as an env var and must write
    releases/demo-state.json on success.

    Args:
        project_dir: Root of the project.
        app_url: URL of the running app. Passed as APP_URL env var.

    Returns:
        DemoSeedResult with parsed demo-state.json as `entities`.
    """
    releases_dir = project_dir / "releases"
    mjs_script = releases_dir / "demo-seed.mjs"
    py_script = releases_dir / "demo-seed.py"

    if mjs_script.exists():
        runner = _find_node()
        if not runner:
            return DemoSeedResult(
                success=False,
                skipped=True,
                skip_reason="node not found in PATH — install Node.js to run demo seed",
            )
        cmd = [runner, str(mjs_script)]
    elif py_script.exists():
        cmd = ["python", str(py_script)]
    else:
        return DemoSeedResult(
            success=False,
            skipped=True,
            skip_reason="No demo seed script found (releases/demo-seed.mjs or .py)",
        )

    env = os.environ.copy()
    if app_url:
        env["APP_URL"] = app_url
        logger.info("Demo seed: using app URL %s", app_url)

    state_path = releases_dir / "demo-state.json"
    env["DEMO_STATE_PATH"] = str(state_path)

    logger.info("Running demo seed: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=_SEED_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return DemoSeedResult(
            success=False,
            error=f"Demo seed timed out after {_SEED_TIMEOUT_SECONDS} seconds",
        )
    except FileNotFoundError as e:
        return DemoSeedResult(
            success=False,
            error=f"Script runner not found: {e}",
        )

    if result.returncode != 0:
        logger.warning(
            "Demo seed failed (exit %d):\n%s",
            result.returncode,
            result.stderr[-1000:] if result.stderr else "(no stderr)",
        )
        return DemoSeedResult(
            success=False,
            error=f"Demo seed exited {result.returncode}: {result.stderr[-500:]}",
        )

    entities = _read_demo_state(state_path)

    logger.info(
        "Demo seed complete — state written to %s (%d entity types)",
        state_path,
        len(entities),
    )
    return DemoSeedResult(
        success=True,
        state_path=state_path if state_path.exists() else None,
        entities=entities,
    )


def _read_demo_state(state_path: Path) -> dict:
    """Read demo-state.json written by the seed script."""
    if not state_path.exists():
        logger.warning("demo-state.json not found at %s after seed", state_path)
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not parse demo-state.json: %s", e)
        return {}


def _find_node() -> str | None:
    return shutil.which("node")
