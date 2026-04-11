"""Narrative frame renderer: creates branded PNG slides for non-visual features.

Used to create evidence for features that can't be shown with a screenshot
(SSE events, WebSocket connections, background jobs, security logic, etc.).

Output is a 1280×720 PNG that looks like a professional slide:
  - Dark themed (dev-platform style)
  - Evidence tier badge (T1–T5 with colour coding)
  - Title + subtitle
  - Body text (multi-line, auto-wrapped)
  - AC reference tags
  - Step table (numbered list)

Falls back gracefully if DejaVu fonts are not available (uses PIL default font).
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Pillow is listed in requirements.txt — fail loudly if missing.
from PIL import Image, ImageDraw, ImageFont

# --- Constants ---

_FRAME_WIDTH = 1280
_FRAME_HEIGHT = 720

# Dark theme colours
_BG_DARK = (18, 18, 24)       # near-black blue-grey
_BG_CARD = (30, 32, 42)       # card background
_BORDER = (52, 56, 72)        # subtle card border
_TEXT_PRIMARY = (230, 232, 240)
_TEXT_SECONDARY = (140, 148, 172)
_ACCENT_BLUE = (79, 142, 247)  # mq brand blue

# Evidence tier colours (badge background)
_TIER_COLOURS: dict[str, tuple[int, int, int]] = {
    "T1": (34, 197, 94),    # green  — screenshot
    "T2": (59, 130, 246),   # blue   — API response
    "T3": (168, 85, 247),   # purple — test output
    "T4": (234, 179, 8),    # yellow — code reference
    "T5": (107, 114, 128),  # grey   — narrative
}

_TIER_LABELS = {
    "T1": "T1 • Screenshot",
    "T2": "T2 • API Response",
    "T3": "T3 • Test Output",
    "T4": "T4 • Code Reference",
    "T5": "T5 • Narrative",
}

# Font paths — fall back to None → PIL bitmap font
_FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
_FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
_FONT_MONO = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")


# --- Data classes ---

@dataclass
class NarrativeFrameOpts:
    """Options for a narrative frame."""

    title: str
    body: str                        # multi-line text, markdown-lite (no rendering, just plain)
    output_path: Path
    subtitle: str = ""
    evidence_tier: str = "T5"        # T1–T5
    ac_refs: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)  # numbered step list shown below body
    story_id: str = ""


@dataclass
class NarrativeFrameResult:
    success: bool
    path: Path | None = None
    error: str | None = None


# --- Font loading ---

def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    return ImageFont.load_default()


# --- Drawing helpers ---

def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
    outline_width: int = 1,
) -> None:
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=outline_width)


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    bg: tuple[int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    """Draw a pill badge, return right edge x."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x, pad_y = 12, 6
    rect = (x, y, x + text_w + pad_x * 2, y + text_h + pad_y * 2)
    _draw_rounded_rect(draw, rect, radius=8, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, fill=(255, 255, 255), font=font)
    return rect[2]


def _wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)

    for word in words:
        candidate = " ".join(current + [word])
        bbox = d.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


# --- Main render function ---

def render_narrative_frame(opts: NarrativeFrameOpts) -> NarrativeFrameResult:
    """Render a narrative frame PNG.

    Args:
        opts: NarrativeFrameOpts describing what to render.

    Returns:
        NarrativeFrameResult with path on success.
    """
    try:
        img = Image.new("RGB", (_FRAME_WIDTH, _FRAME_HEIGHT), _BG_DARK)
        draw = ImageDraw.Draw(img)

        # --- Fonts ---
        font_title = _load_font(_FONT_BOLD, 32)
        font_sub = _load_font(_FONT_REGULAR, 18)
        font_body = _load_font(_FONT_REGULAR, 16)
        font_badge = _load_font(_FONT_BOLD, 13)
        font_step = _load_font(_FONT_REGULAR, 15)
        font_ac = _load_font(_FONT_MONO, 13)
        font_story = _load_font(_FONT_MONO, 14)

        # --- Layout constants ---
        margin = 60
        content_w = _FRAME_WIDTH - margin * 2
        y = margin

        # --- Story ID (top-left, small) ---
        if opts.story_id:
            draw.text((margin, y), f"Story {opts.story_id}", fill=_TEXT_SECONDARY, font=font_story)
            y += 28

        # --- Evidence tier badge (top-right) ---
        tier = opts.evidence_tier.upper() if opts.evidence_tier else "T5"
        tier_label = _TIER_LABELS.get(tier, tier)
        tier_colour = _TIER_COLOURS.get(tier, _TIER_COLOURS["T5"])
        badge_text_bbox = draw.textbbox((0, 0), tier_label, font=font_badge)
        badge_w = badge_text_bbox[2] + 24 + 8
        _draw_badge(draw, tier_label, _FRAME_WIDTH - margin - badge_w, margin, tier_colour, font_badge)

        # --- Title ---
        y = max(y, margin + 20)
        title_lines = _wrap_text(opts.title, font_title, content_w - badge_w - 20)
        for line in title_lines:
            draw.text((margin, y), line, fill=_TEXT_PRIMARY, font=font_title)
            bbox = draw.textbbox((margin, y), line, font=font_title)
            y += (bbox[3] - bbox[1]) + 6
        y += 8

        # --- Subtitle ---
        if opts.subtitle:
            draw.text((margin, y), opts.subtitle, fill=_ACCENT_BLUE, font=font_sub)
            bbox = draw.textbbox((margin, y), opts.subtitle, font=font_sub)
            y += (bbox[3] - bbox[1]) + 16
        else:
            y += 8

        # --- Divider line ---
        draw.line([(margin, y), (_FRAME_WIDTH - margin, y)], fill=_BORDER, width=1)
        y += 20

        # --- Body text ---
        if opts.body:
            for para in opts.body.strip().split("\n\n"):
                para_lines = _wrap_text(para.strip(), font_body, content_w)
                for line in para_lines:
                    draw.text((margin, y), line, fill=_TEXT_PRIMARY, font=font_body)
                    bbox = draw.textbbox((margin, y), line, font=font_body)
                    y += (bbox[3] - bbox[1]) + 4
                y += 10

        # --- Steps ---
        if opts.steps:
            y += 6
            for i, step in enumerate(opts.steps, start=1):
                step_text = f"{i}. {step}"
                step_lines = _wrap_text(step_text, font_step, content_w - 20)
                for j, line in enumerate(step_lines):
                    indent = 0 if j == 0 else 22
                    draw.text((margin + indent, y), line, fill=_TEXT_PRIMARY, font=font_step)
                    bbox = draw.textbbox((margin + indent, y), line, font=font_step)
                    y += (bbox[3] - bbox[1]) + 4
                y += 4

        # --- AC references (bottom band) ---
        if opts.ac_refs:
            ac_y = _FRAME_HEIGHT - 60
            draw.line([(margin, ac_y - 12), (_FRAME_WIDTH - margin, ac_y - 12)], fill=_BORDER, width=1)
            draw.text((margin, ac_y - 8), "AC refs: ", fill=_TEXT_SECONDARY, font=font_ac)
            x_ac = margin + 70
            for ref in opts.ac_refs:
                x_ac = _draw_badge(draw, ref, x_ac, ac_y - 10, _BG_CARD, font_ac) + 8
                if x_ac > _FRAME_WIDTH - margin - 80:
                    break  # overflow guard

        # --- Bottom bar ---
        bar_y = _FRAME_HEIGHT - 28
        draw.rectangle([(0, bar_y), (_FRAME_WIDTH, _FRAME_HEIGHT)], fill=_BG_CARD)
        draw.text(
            (margin, bar_y + 6),
            "mq-devEngine  •  Narrative Evidence Frame",
            fill=_TEXT_SECONDARY,
            font=font_badge,
        )

        # --- Save ---
        opts.output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(opts.output_path), "PNG", optimize=True)

        return NarrativeFrameResult(success=True, path=opts.output_path)

    except Exception as e:
        return NarrativeFrameResult(success=False, error=str(e))
