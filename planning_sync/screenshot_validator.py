"""Screenshot validator: analyses demo captures for quality before reporting.

Detects broken or low-quality screenshots before they enter the sprint report:
- Empty / blank images (file size < 5 KB)
- Mostly-white pages (loading spinner, blank canvas, browser error page)
- Error-red dominant pages (HTTP 500 / application error screen)
- Undersized captures (viewport sanity check)

Each screenshot receives an evidence_quality rating:
  "high"   — looks like a real, populated UI page
  "medium" — small file or slightly suspicious colours but not obviously broken
  "low"    — clearly broken: blank, error screen, or near-empty

The validator can also annotate an existing manifest.json in-place so that
the report generator and sprint evaluator know which steps lack hard evidence.

Usage::

    from planning_sync.screenshot_validator import validate_screenshots
    result = validate_screenshots(Path("releases/screenshots"))
    print(result.gap_count, "gaps detected")

    # Optionally update manifest with quality annotations
    from planning_sync.screenshot_validator import annotate_manifest
    annotate_manifest(Path("releases/screenshots/manifest.json"), result)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
_MIN_SIZE_BYTES = 5_000          # below this → almost certainly blank
_MEDIUM_SIZE_BYTES = 30_000      # below this → possibly low-content (warn only)
_MIN_WIDTH = 400                 # sanity: anything narrower is suspicious
_MIN_HEIGHT = 300
_WHITE_THRESHOLD = 240           # R,G,B all above this → "white-ish"
_RED_R_MIN = 180                 # R above this
_RED_GB_MAX = 100                # G and B both below this → "red-ish"
_WHITE_RATIO_BAD = 0.85          # >85 % white → almost certainly blank/error
_WHITE_RATIO_WARN = 0.70         # >70 % white → possibly sparse content
_RED_RATIO_BAD = 0.20            # >20 % red → error screen

# ── Data classes ──────────────────────────────────────────────────────────────

EvidenceQuality = Literal["high", "medium", "low"]


@dataclass
class ScreenshotValidation:
    """Validation result for a single screenshot file."""

    path: Path
    valid: bool
    reason: str
    evidence_quality: EvidenceQuality
    issues: list[str] = field(default_factory=list)
    file_size: int = 0
    width: int = 0
    height: int = 0


@dataclass
class ValidationResult:
    """Aggregate result for an entire screenshots directory."""

    total_count: int = 0
    valid_count: int = 0
    gap_count: int = 0
    validations: dict[str, ScreenshotValidation] = field(default_factory=dict)
    gaps: list[dict] = field(default_factory=list)


# ── Public API ────────────────────────────────────────────────────────────────


def validate_screenshots(screenshots_dir: Path) -> ValidationResult:
    """Validate all PNG files in *screenshots_dir*.

    Args:
        screenshots_dir: Directory containing screenshot PNG files and
                         optionally a manifest.json.

    Returns:
        ValidationResult with per-file quality ratings and a gap list.
    """
    result = ValidationResult()

    if not screenshots_dir.exists() or not screenshots_dir.is_dir():
        logger.warning("Screenshots directory not found: %s", screenshots_dir)
        return result

    png_files = sorted(screenshots_dir.glob("*.png"))
    if not png_files:
        logger.info("No PNG files found in %s", screenshots_dir)
        return result

    result.total_count = len(png_files)

    for png_path in png_files:
        validation = _validate_single(png_path)
        result.validations[png_path.name] = validation

        if validation.valid:
            result.valid_count += 1
        else:
            result.gap_count += 1
            result.gaps.append(
                {
                    "filename": png_path.name,
                    "reason": validation.reason,
                    "evidence_quality": validation.evidence_quality,
                    "issues": validation.issues,
                }
            )

    logger.info(
        "Screenshot validation: %d/%d valid, %d gaps",
        result.valid_count,
        result.total_count,
        result.gap_count,
    )
    return result


def annotate_manifest(manifest_path: Path, result: ValidationResult) -> bool:
    """Enrich manifest.json steps with screenshot validation results.

    For each step with ``type == "screenshot"``, adds a ``validation`` key::

        {
          "valid": true,
          "evidence_quality": "high",
          "issues": []
        }

    Args:
        manifest_path: Path to manifest.json (modified in-place).
        result: ValidationResult from validate_screenshots().

    Returns:
        True if the manifest was updated, False if it could not be read/written.
    """
    if not manifest_path.exists():
        logger.warning("Manifest not found: %s", manifest_path)
        return False

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read manifest %s: %s", manifest_path, e)
        return False

    changed = False
    for journey in data.get("journeys", []):
        for step in journey.get("steps", []):
            filename = step.get("file") or step.get("filename") or step.get("screenshot")
            if not filename:
                continue
            # Normalise: keep only the basename
            filename = Path(filename).name
            if filename not in result.validations:
                continue
            v = result.validations[filename]
            step["validation"] = {
                "valid": v.valid,
                "evidence_quality": v.evidence_quality,
                "issues": v.issues,
            }
            changed = True

    if changed:
        try:
            manifest_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("Manifest annotated: %s", manifest_path)
        except OSError as e:
            logger.warning("Could not write manifest %s: %s", manifest_path, e)
            return False

    return changed


# ── Internal helpers ──────────────────────────────────────────────────────────


def _validate_single(path: Path) -> ScreenshotValidation:
    """Validate one screenshot file.  Never raises — returns "low" on errors."""
    issues: list[str] = []
    file_size = 0

    try:
        file_size = path.stat().st_size
    except OSError as e:
        return ScreenshotValidation(
            path=path,
            valid=False,
            reason=f"Cannot stat file: {e}",
            evidence_quality="low",
            issues=["file_unreadable"],
            file_size=0,
        )

    # ── Size check ──────────────────────────────────────────────────────────
    if file_size < _MIN_SIZE_BYTES:
        return ScreenshotValidation(
            path=path,
            valid=False,
            reason=f"File too small ({file_size} bytes) — likely blank or empty page",
            evidence_quality="low",
            issues=["too_small"],
            file_size=file_size,
        )

    if file_size < _MEDIUM_SIZE_BYTES:
        issues.append("small_file")

    # ── PIL colour analysis ─────────────────────────────────────────────────
    width, height = 0, 0
    try:
        from PIL import Image  # optional heavy dep — skip gracefully

        with Image.open(path) as img:
            width, height = img.size

            if width < _MIN_WIDTH or height < _MIN_HEIGHT:
                issues.append("undersized")

            white_ratio, red_ratio = _colour_ratios(img)

            if white_ratio > _WHITE_RATIO_BAD:
                issues.append("mostly_white")
            elif white_ratio > _WHITE_RATIO_WARN:
                issues.append("sparse_content")

            if red_ratio > _RED_RATIO_BAD:
                issues.append("red_dominant")

    except ImportError:
        logger.debug("Pillow not available — skipping colour analysis for %s", path.name)
    except Exception as e:  # noqa: BLE001 — never crash validation
        logger.debug("PIL error analysing %s: %s", path.name, e)
        issues.append("analysis_failed")

    # ── Determine quality ────────────────────────────────────────────────────
    hard_fail_issues = {"mostly_white", "red_dominant", "too_small", "file_unreadable"}
    has_hard_fail = bool(hard_fail_issues & set(issues))

    soft_issues = {"small_file", "sparse_content", "undersized", "analysis_failed"}
    has_soft = bool(soft_issues & set(issues))

    if has_hard_fail:
        evidence_quality: EvidenceQuality = "low"
        valid = False
        reason = _build_reason(issues)
    elif has_soft:
        evidence_quality = "medium"
        valid = True  # warn but do not block
        reason = _build_reason(issues)
    else:
        evidence_quality = "high"
        valid = True
        reason = "Screenshot looks valid"

    return ScreenshotValidation(
        path=path,
        valid=valid,
        reason=reason,
        evidence_quality=evidence_quality,
        issues=issues,
        file_size=file_size,
        width=width,
        height=height,
    )


def _colour_ratios(img) -> tuple[float, float]:
    """Return (white_ratio, red_ratio) for a PIL Image.

    Samples at most 10 000 pixels on a regular grid for performance.
    """
    from PIL import Image

    # Ensure RGB (no alpha channel arithmetic)
    if img.mode != "RGB":
        img = img.convert("RGB")

    pixels = img.load()
    w, h = img.size

    # Sample step: target ~10k pixels
    total = w * h
    step = max(1, int((total / 10_000) ** 0.5))

    white_count = 0
    red_count = 0
    sampled = 0

    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = pixels[x, y]
            sampled += 1
            if r > _WHITE_THRESHOLD and g > _WHITE_THRESHOLD and b > _WHITE_THRESHOLD:
                white_count += 1
            elif r > _RED_R_MIN and g < _RED_GB_MAX and b < _RED_GB_MAX:
                red_count += 1

    if sampled == 0:
        return 0.0, 0.0

    return white_count / sampled, red_count / sampled


def _build_reason(issues: list[str]) -> str:
    messages = {
        "too_small": "file size below 5 KB (blank or empty page)",
        "mostly_white": "image is >85 % white (blank/loading/error page)",
        "red_dominant": "image has >20 % red pixels (possible error screen)",
        "sparse_content": "image is >70 % white (possibly low-content page)",
        "small_file": "file size below 30 KB (possibly sparse content)",
        "undersized": "image dimensions below expected viewport",
        "analysis_failed": "colour analysis failed (Pillow error)",
        "file_unreadable": "file cannot be read",
    }
    parts = [messages.get(i, i) for i in issues]
    return "; ".join(parts) if parts else "unknown issue"
