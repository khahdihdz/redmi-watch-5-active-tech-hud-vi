"""Shared helpers for the Tech HUD VI watch-face pipeline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "design" / "layout.json"
SRC_DIR = ROOT / "src" / "watchface"
SRC_IMAGES = SRC_DIR / "images"
FPRJ_PATH = SRC_DIR / "tech_hud_vi.fprj"
BACKGROUND_PATH = ROOT / "assets" / "backgrounds" / "background.png"
PREVIEW_PATH = ROOT / "design" / "preview.png"
PREVIEW_RAW_PATH = SRC_DIR / "preview.png"
DIST_DIR = ROOT / "dist"

SS = 4  # supersampling factor for every generated bitmap


def load_layout() -> dict:
    with LAYOUT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid colour: {value}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgba(layout: dict, name: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = hex_rgb(layout["meta"]["colors"][name])
    return (r, g, b, alpha)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def fits_rounded_display(
    x: float,
    y: float,
    width: float,
    height: float,
    canvas_width: int,
    canvas_height: int,
    radius: float,
) -> bool:
    """Return True when every corner of a box is inside a rounded rectangle.

    The watch display is a 320×385 rectangle with an 82 px corner radius.
    Checking only a rectangular safe inset is not enough: a label near a
    corner can be inside the canvas but still hidden by the bezel.  The
    rounded rectangle is convex, so testing all four box corners is enough
    for an axis-aligned box.
    """
    if x < 0 or y < 0 or x + width > canvas_width or y + height > canvas_height:
        return False
    corners = ((x, y), (x + width, y), (x, y + height), (x + width, y + height))
    left = radius
    right = canvas_width - radius
    top = radius
    bottom = canvas_height - radius
    for px, py in corners:
        if px < left and py < top:
            if (px - left) ** 2 + (py - top) ** 2 > radius**2:
                return False
        elif px > right and py < top:
            if (px - right) ** 2 + (py - top) ** 2 > radius**2:
                return False
        elif px < left and py > bottom:
            if (px - left) ** 2 + (py - bottom) ** 2 > radius**2:
                return False
        elif px > right and py > bottom:
            if (px - right) ** 2 + (py - bottom) ** 2 > radius**2:
                return False
    return True


def font_path(layout: dict, name: str) -> Path:
    return ROOT / layout["meta"]["fonts"][name]


def load_font(layout: dict, name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    path = font_path(layout, name)
    font = ImageFont.truetype(str(path), size * SS)
    if weight is not None:
        try:
            font.set_variation_by_axes([weight])
        except (OSError, AttributeError):
            pass
    return font


def text_width(font: ImageFont.FreeTypeFont, text: str, tracking: float = 0.0) -> float:
    if not text:
        return 0.0
    width = sum(font.getlength(ch) for ch in text)
    return width + tracking * SS * (len(text) - 1)


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    tracking: float = 0.0,
    anchor: str = "la",
):
    """Draw text with optional letter-spacing on one shared baseline.

    Coordinates are 1x design pixels.  ``y`` is the top of capital letters,
    not the top of each individual glyph: drawing every character with
    ``anchor="lt"`` made accented Vietnamese letters sit lower than plain
    letters on the same line.  The baseline is derived from the font's "H"
    cap height and every glyph is anchored with ``ls`` so its body shares
    exactly that baseline.  Diacritics extend above ``y`` naturally.
    """
    x, y = xy[0] * SS, xy[1] * SS
    step = tracking * SS
    total = text_width(font, text, tracking)
    if anchor in ("ra", "ma"):
        x -= total if anchor == "ra" else total / 2
    cap_height = -font.getbbox("H", anchor="ls")[1]
    baseline = y + cap_height
    for index, char in enumerate(text):
        draw.text((x, baseline), char, font=font, fill=fill, anchor="ls")
        x += font.getlength(char) + step


def text_bbox(font: ImageFont.FreeTypeFont, text: str, tracking: float = 0.0) -> tuple[int, int, int, int]:
    return (0, 0, round(text_width(font, text, tracking) / SS), round(font.size / SS))


MIN_PADDED_PIXELS = 256  # compile.exe small-input path needs >= 256 indexed bytes
MAX_PALETTE_COLORS = 256


def fit_compiler_limits(image: Image.Image) -> Image.Image:
    """Make a bitmap acceptable to the Gen2 compiler.

    compile.exe indexes every bitmap to at most 256 colours and deflates each
    image with an output buffer the size of its zero-padded indexed data, so
    images shorter than 256 padded bytes crash the compressor. Both limits are
    invisible: extra rows are fully transparent and palette reduction keeps
    antialiasing.
    """
    width, height = image.size
    padded_height = height
    while (width + 1) * padded_height < MIN_PADDED_PIXELS:
        padded_height += 1
    if padded_height != height:
        padded = Image.new("RGBA", (width, padded_height), (0, 0, 0, 0))
        padded.paste(image.convert("RGBA"), (0, 0))
        image = padded
    if image.convert("RGBA").getcolors(maxcolors=MAX_PALETTE_COLORS) is None:
        image = image.quantize(
            colors=MAX_PALETTE_COLORS,
            method=Image.Quantize.FASTOCTREE,
            dither=Image.Dither.NONE,
        ).convert("RGBA")
    return image


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_compiled = SRC_IMAGES in path.parents or path == PREVIEW_RAW_PATH
    if is_compiled:
        image = fit_compiler_limits(image)
    image.save(path, format="PNG", optimize=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_font_cmap(path: Path) -> set[int]:
    from fontTools.ttLib import TTFont

    font = TTFont(str(path))
    result: set[int] = set()
    for table in font["cmap"].tables:
        result |= set(table.cmap)
    return result


def parse_number(
    value: int,
    digits: int,
    blanking: bool = True,
    signed: bool = False,
) -> list[str | None]:
    value = int(value)
    if signed and value < 0:
        # Temperature can legitimately fall below zero. Keep the minus sign
        # in its own cell so the existing `_minus` bitmap can render it.
        magnitude = str(-value)
        allowed = max(0, digits - 1)
        if len(magnitude) > allowed:
            magnitude = magnitude[-allowed:] if allowed else ""
        if not blanking:
            return ["-"] + list(magnitude.rjust(allowed, "0"))
        chars = ["-"] + list(magnitude)
        return [None] * (digits - len(chars)) + chars
    raw = str(max(0, value)).rjust(digits, "0")
    if len(raw) > digits:
        raw = raw[-digits:]
    if not blanking:
        return list(raw)
    first = next((index for index, ch in enumerate(raw) if ch != "0"), None)
    if first is None:
        # A real zero reading must still render one digit; hiding the whole
        # field made a valid 0 steps/calories reading look like missing data.
        return [None] * (digits - 1) + ["0"]
    return [None] * first + list(raw[first:])
