#!/usr/bin/env python3
"""Generate every bitmap, the .fprj project and the preview from design/layout.json.

The script is deliberately deterministic: no timestamps, no randomness.
Vietnamese labels are rasterised with Lora (OFL) and the clock uses DSEG7
Classic Bold (OFL), so the watch never depends on a system font being able to
render Vietnamese diacritics or seven-segment digits.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BACKGROUND_PATH,
    FPRJ_PATH,
    LAYOUT_PATH,
    PREVIEW_PATH,
    PREVIEW_RAW_PATH,
    ROOT,
    SRC_DIR,
    SRC_IMAGES,
    SS,
    draw_text,
    font_path,
    hex_rgb,
    load_font,
    load_layout,
    mix,
    parse_number,
    rgba,
    save_png,
    sha256_file,
)

LAYOUT = load_layout()
META = LAYOUT["meta"]
W, H = META["canvas"]["w"], META["canvas"]["h"]
CANVAS = (W, H)
COLORS = META["colors"]


def sc(value: float) -> int:
    return int(round(value * SS))


def new_layer(w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (sc(w), sc(h)), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image, "RGBA")


def downsample(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.resize(size, Image.LANCZOS)


def add_glow(image: Image.Image, mask: Image.Image, colour, radius: float, strength: int = 180) -> None:
    glow = Image.new("RGBA", image.size, colour[:3] + (0,))
    alpha = mask.filter(ImageFilter.GaussianBlur(sc(radius))).point(lambda v: int(v * strength / 255))
    glow.putalpha(alpha)
    image.alpha_composite(glow)


def chamfer_polygon(x: int, y: int, w: int, h: int, cut: int = 6) -> list[tuple[int, int]]:
    return [
        (sc(x + cut), sc(y)),
        (sc(x + w), sc(y)),
        (sc(x + w), sc(y + h - cut)),
        (sc(x + w - cut), sc(y + h)),
        (sc(x), sc(y + h)),
        (sc(x), sc(y + cut)),
    ]


def draw_panel(draw: ImageDraw.ImageDraw, panel: dict) -> None:
    accent = hex_rgb(COLORS[panel["accent"]])
    border = hex_rgb(COLORS["brass_dark"])
    inner = hex_rgb(COLORS["brass"])
    fill = hex_rgb(COLORS["panel"]) + (238,)
    x, y, w, h = panel["x"], panel["y"], panel["w"], panel["h"]
    points = chamfer_polygon(x, y, w, h)
    draw.polygon(points, fill=fill, outline=border + (255,))
    inset = chamfer_polygon(x + 3, y + 3, w - 6, h - 6, cut=4)
    draw.line(inset + [inset[0]], fill=inner + (65,), width=sc(1))
    # brass rail at the top and a short accent at the bottom-right
    draw.line([(sc(x + 8), sc(y + 0.7)), (sc(x + 28), sc(y + 0.7))], fill=accent + (220,), width=sc(1.2))
    draw.line([(sc(x + w - 18), sc(y + h - 0.7)), (sc(x + w - 1), sc(y + h - 0.7))], fill=accent + (135,), width=sc(1))
    # corner screws
    for px, py in ((x + 5, y + 5), (x + w - 5, y + 5), (x + 5, y + h - 5), (x + w - 5, y + h - 5)):
        draw.ellipse(
            [sc(px - 1.3), sc(py - 1.3), sc(px + 1.3), sc(py + 1.3)],
            fill=inner + (215,),
            outline=border + (255,),
            width=1,
        )
    # three gauge ticks at the upper right
    for i in range(3):
        tx = x + w - 14 + i * 4
        draw.line([(sc(tx), sc(y + 5)), (sc(tx), sc(y + 8))], fill=accent + (95,), width=sc(0.6))


def draw_icon(draw: ImageDraw.ImageDraw, icon: dict) -> None:
    colour = hex_rgb(COLORS[icon["color"]]) + (255,)
    x, y, w, h = icon["x"], icon["y"], icon["w"], icon["h"]
    width = max(1, sc(1.2))
    if icon["kind"] == "battery":
        draw.rounded_rectangle([sc(x), sc(y), sc(x + w - 3), sc(y + h)], radius=sc(2), outline=colour, width=width)
        draw.rectangle([sc(x + w - 2), sc(y + h * 0.3), sc(x + w), sc(y + h * 0.7)], fill=colour)
        for i in range(3):
            bx = x + 2 + i * 5
            draw.line([(sc(bx), sc(y + 4)), (sc(bx), sc(y + h - 3))], fill=colour[:3] + (140,), width=sc(1))
    elif icon["kind"] == "heart":
        cx, cy = x + w / 2, y + h / 2
        pts = []
        for deg in range(0, 360, 6):
            t = math.radians(deg)
            hx = 16 * math.sin(t) ** 3
            hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((sc(cx + hx * w / 34), sc(cy + hy * h / 34)))
        draw.line(pts + [pts[0]], fill=colour, width=width, joint="curve")
    elif icon["kind"] == "steps":
        draw.arc([sc(x), sc(y + 1), sc(x + w), sc(y + h + 4)], 200, 340, fill=colour, width=width)
        draw.line([(sc(x + 1), sc(y + h - 1)), (sc(x + w - 1), sc(y + h - 1))], fill=colour, width=width)
        draw.ellipse([sc(x + w * 0.15), sc(y + h * 0.15), sc(x + w * 0.4), sc(y + h * 0.45)], fill=colour)
    elif icon["kind"] == "flame":
        pts = [
            (x + w * 0.5, y + h * 0.05),
            (x + w * 0.78, y + h * 0.38),
            (x + w * 0.72, y + h * 0.62),
            (x + w * 0.95, y + h * 0.75),
            (x + w * 0.78, y + h * 0.95),
            (x + w * 0.45, y + h),
            (x + w * 0.16, y + h * 0.8),
            (x + w * 0.08, y + h * 0.55),
            (x + w * 0.35, y + h * 0.3),
        ]
        draw.line([(sc(px), sc(py)) for px, py in pts] + [(sc(pts[0][0]), sc(pts[0][1]))], fill=colour, width=width, joint="curve")
    elif icon["kind"] == "thermo":
        draw.rounded_rectangle([sc(x + w * 0.35), sc(y), sc(x + w * 0.65), sc(y + h * 0.68)], radius=sc(2), outline=colour, width=width)
        draw.ellipse([sc(x + w * 0.18), sc(y + h * 0.6), sc(x + w * 0.82), sc(y + h)], outline=colour, width=width)
        draw.line([(sc(x + w * 0.5), sc(y + h * 0.25)), (sc(x + w * 0.5), sc(y + h * 0.66))], fill=colour, width=width)


def gear_points(cx: float, cy: float, outer: float, inner: float, teeth: int) -> list[tuple[int, int]]:
    points = []
    for i in range(teeth):
        base = 2 * math.pi * i / teeth
        for frac, radius in ((0.0, inner), (0.12, outer), (0.38, outer), (0.5, inner)):
            angle = base + frac * 2 * math.pi / teeth
            points.append((sc(cx + math.cos(angle) * radius), sc(cy + math.sin(angle) * radius)))
    return points


def draw_gear(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    outer: float,
    inner: float,
    teeth: int,
    colour: tuple[int, int, int],
    fill_alpha: int = 10,
    outline_alpha: int = 55,
) -> None:
    points = gear_points(cx, cy, outer, inner, teeth)
    draw.polygon(points, fill=colour + (fill_alpha,))
    draw.line(points + [points[0]], fill=colour + (outline_alpha,), width=sc(1))
    draw.ellipse(
        [sc(cx - inner * 0.58), sc(cy - inner * 0.58), sc(cx + inner * 0.58), sc(cy + inner * 0.58)],
        outline=colour + (outline_alpha,),
        width=sc(1),
    )
    for i in range(6):
        angle = 2 * math.pi * i / 6
        draw.line(
            [
                (sc(cx + math.cos(angle) * inner * 0.6), sc(cy + math.sin(angle) * inner * 0.6)),
                (sc(cx + math.cos(angle) * inner * 0.92), sc(cy + math.sin(angle) * inner * 0.92)),
            ],
            fill=colour + (max(20, outline_alpha // 3),),
            width=sc(0.7),
        )


def draw_rivet(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float = 1.3) -> None:
    brass = hex_rgb(COLORS["brass"])
    dark = hex_rgb(COLORS["brass_dark"])
    draw.ellipse(
        [sc(cx - radius), sc(cy - radius), sc(cx + radius), sc(cy + radius)],
        fill=brass + (220,),
        outline=dark + (255,),
        width=1,
    )


def draw_pipe(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], colour: tuple[int, int, int], width: float) -> None:
    coords = [(sc(px), sc(py)) for px, py in points]
    draw.line(coords, fill=colour + (95,), width=sc(width + 1.4), joint="curve")
    draw.line(coords, fill=colour + (45,), width=sc(width), joint="curve")


def draw_clock_frame(draw: ImageDraw.ImageDraw) -> None:
    x, y, w, h = 10, 52, 300, 96
    panel = hex_rgb(COLORS["panel"])
    border = hex_rgb(COLORS["brass_dark"])
    brass = hex_rgb(COLORS["brass"])
    # dark leather clock window with a brass bezel
    draw.rounded_rectangle(
        [sc(x - 1), sc(y - 1), sc(x + w + 1), sc(y + h + 1)],
        radius=sc(9),
        fill=(0, 0, 0, 120),
    )
    draw.rounded_rectangle(
        [sc(x), sc(y), sc(x + w), sc(y + h)],
        radius=sc(8),
        fill=panel + (240,),
        outline=border + (255,),
        width=sc(2),
    )
    draw.rounded_rectangle(
        [sc(x + 4), sc(y + 4), sc(x + w - 4), sc(y + h - 4)],
        radius=sc(5),
        outline=brass + (65,),
        width=sc(1),
    )
    for px, py in ((x + 9, y + 9), (x + w - 9, y + 9), (x + 9, y + h - 9), (x + w - 9, y + h - 9)):
        draw_rivet(draw, px, py)
    draw.line([(sc(x + 20), sc(y)), (sc(x + w - 20), sc(y))], fill=brass + (110,), width=sc(1))
    draw.line([(sc(x + 20), sc(y + h)), (sc(x + w - 20), sc(y + h))], fill=brass + (110,), width=sc(1))


def build_background() -> Image.Image:
    image = Image.new("RGBA", (sc(W), sc(H)), hex_rgb(COLORS["bg"]) + (255,))
    draw = ImageDraw.Draw(image, "RGBA")
    bg = hex_rgb(COLORS["bg"])
    bg2 = hex_rgb(COLORS["bg2"])
    brass = hex_rgb(COLORS["brass"])
    copper = hex_rgb(COLORS["copper"])
    amber = hex_rgb(COLORS["amber"])
    muted = hex_rgb(COLORS["muted"])

    # warm gunmetal/leather gradient
    for yy in range(sc(H)):
        t = yy / max(1, sc(H) - 1)
        colour = mix(bg, bg2, min(1.0, abs(t - 0.5) * 1.45))
        draw.line([(0, yy), (sc(W), yy)], fill=colour + (255,))

    # very faint leather grain and dust
    for gx in range(0, W, 6):
        offset = round(3 * math.sin(gx * 0.27))
        draw.line([(sc(gx), 0), (sc(gx + offset), sc(H))], fill=brass + (6,), width=sc(0.5))
    for gy in range(5, H, 11):
        draw.line([(0, sc(gy)), (sc(W), sc(gy))], fill=brass + (3,), width=sc(0.4))
    for gy in range(7, H, 17):
        for gx in range(5, W, 19):
            if (gx * 17 + gy * 31) % 53 < 10:
                draw.point((sc(gx), sc(gy)), fill=brass + (12,))

    # large, low-contrast brass gears behind the interface
    draw_gear(draw, 4, 16, 104, 78, 18, brass, fill_alpha=10, outline_alpha=55)
    draw_gear(draw, 318, 374, 92, 68, 15, copper, fill_alpha=8, outline_alpha=45)

    # copper steam pipes at the sides
    draw_pipe(draw, [(2, 98), (16, 98), (24, 106), (24, 146)], copper, 1.3)
    draw_pipe(draw, [(318, 248), (304, 248), (296, 256), (296, 318)], brass, 1.2)

    # brass top rail with rivets
    draw.line([(sc(10), sc(48)), (sc(W - 10), sc(48))], fill=hex_rgb(COLORS["brass_dark"]) + (210,), width=sc(1.6))
    draw.line([(sc(10), sc(48)), (sc(66), sc(48))], fill=copper + (230,), width=sc(1.6))
    draw_rivet(draw, 16, 48, 1.1)
    draw_rivet(draw, W - 16, 48, 1.1)

    # side gauge ticks, kept outside the clock bezel and inside the 82 px corners
    for ty in range(58, 300, 24):
        draw.line([(sc(6), sc(ty)), (sc(9), sc(ty))], fill=brass + (85,), width=sc(1))
        draw.line([(sc(W - 9), sc(ty + 12)), (sc(W - 6), sc(ty + 12))], fill=brass + (85,), width=sc(1))

    draw_clock_frame(draw)

    # amber lamp glow inside the clock window
    glow, gdraw = new_layer(W, 150)
    gdraw.ellipse([sc(24), sc(58), sc(W - 24), sc(142)], fill=amber + (40,))
    glow = glow.filter(ImageFilter.GaussianBlur(sc(20)))
    image.alpha_composite(glow)

    # brass-rimmed amber colon lenses
    for cy in (78, 112):
        draw.ellipse(
            [sc(154), sc(cy - 1), sc(166), sc(cy + 13)],
            fill=hex_rgb(COLORS["brass_dark"]) + (255,),
            outline=brass + (255,),
            width=sc(1),
        )
        draw.ellipse([sc(157), sc(cy + 2), sc(163), sc(cy + 10)], fill=amber + (255,))

    # brass rails under the clock
    draw.line([(sc(34), sc(148)), (sc(148), sc(148))], fill=brass + (120,), width=sc(1))
    draw.line([(sc(172), sc(148)), (sc(286), sc(148))], fill=brass + (120,), width=sc(1))

    # gear surround for the centred goal ring
    draw_gear(draw, 160, 302, 48, 40, 14, brass, fill_alpha=8, outline_alpha=65)
    draw.ellipse(
        [sc(160 - 45), sc(302 - 45), sc(160 + 45), sc(302 + 45)],
        outline=brass + (45,),
        width=sc(1),
    )

    # base rail beneath the goal label
    draw.line([(sc(128), sc(370)), (sc(192), sc(370))], fill=hex_rgb(COLORS["brass_dark"]) + (160,), width=sc(1))
    draw_rivet(draw, 122, 370, 1.1)
    draw_rivet(draw, 198, 370, 1.1)

    # panels
    for panel in LAYOUT["panels"]:
        draw_panel(draw, panel)

    # icons
    for icon in LAYOUT["icons"]:
        draw_icon(draw, icon)

    # labels
    for label in LAYOUT["labels"]:
        font = load_font(LAYOUT, label["font"], label["size"], weight=label.get("weight", 700))
        colour = rgba(LAYOUT, label["color"])
        draw_text(draw, (label["x"], label["y"]), label["text"], font, colour, label.get("tracking", 0.0), label.get("anchor", "la"))

    final = Image.new("RGBA", CANVAS, hex_rgb(COLORS["bg"]) + (255,))
    final.alpha_composite(downsample(image, CANVAS))
    return final


def render_glyph(
    char: str,
    size: tuple[int, int],
    font_family: str,
    font_size: int,
    fill: tuple[int, int, int, int],
    glow_colour: tuple[int, int, int] | None = None,
    weight: int | None = None,
    padding: float = 1.5,
    vertical: str = "center",
) -> Image.Image:
    w, h = size
    layer, draw = new_layer(w, h)
    font = load_font(LAYOUT, font_family, font_size, weight=weight)
    bbox = draw.textbbox((0, 0), char, font=font, anchor="lt")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # Fit the glyph inside the cell instead of clipping it.
    usable_w, usable_h = sc(w) - sc(padding * 2), sc(h) - sc(padding * 2)
    factor = min(usable_w / max(tw, 1), usable_h / max(th, 1), 1.0)
    if factor < 1.0:
        font = load_font(LAYOUT, font_family, max(4, int(font_size * factor)), weight=weight)
        bbox = draw.textbbox((0, 0), char, font=font, anchor="lt")
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (sc(w) - tw) / 2 - bbox[0]
    if vertical == "baseline":
        # Seven-segment digits such as 1/4 have shorter ink than 0/8.  Align
        # their bottoms instead of centring each glyph so the clock sits on
        # one baseline like a real segmented display.
        y = sc(h - padding) - bbox[3]
    else:
        y = (sc(h) - th) / 2 - bbox[1]
    if glow_colour:
        mask = Image.new("L", layer.size, 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.text((x, y), char, font=font, fill=255, anchor="lt")
        add_glow(layer, mask, glow_colour + (255,), 3.4, strength=200)
    draw.text((x, y), char, font=font, fill=fill, anchor="lt")
    return downsample(layer, size)


def common_font_size(
    size: tuple[int, int],
    family: str,
    font_size: int,
    weight: int | None,
    padding: float,
    chars: str = "0123456789-",
) -> int:
    """Choose one font size for every glyph in a digit set.

    Lora is proportional: "1" is much narrower than "0". Fitting each glyph
    independently made "1" fill the cell height while "0" and "8" were scaled
    down by width, so the numbers looked uneven. A shared size keeps cap
    heights and baselines identical. DSEG7 also shares one size; its shorter
    1/4 glyphs are bottom-aligned later by ``render_glyph``.
    """
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    font = load_font(LAYOUT, family, font_size, weight=weight)
    usable_w = sc(size[0]) - sc(padding * 2)
    usable_h = sc(size[1]) - sc(padding * 2)
    factor = 1.0
    for char in chars:
        bbox = draw.textbbox((0, 0), char, font=font, anchor="lt")
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        factor = min(factor, usable_w / max(width, 1), usable_h / max(height, 1))
    return max(4, int(font_size * factor * 0.98))


def build_digits() -> dict[str, list[Path]]:
    created: dict[str, list[Path]] = {}
    specs = {
        "digit_time": ((64, 88), "clock", 96, 400, rgba(LAYOUT, "amber"), hex_rgb(COLORS["copper"]), 2.0),
        "digit_metric": ((14, 24), "display", 24, 700, rgba(LAYOUT, "cream"), None, 1.0),
        "digit_small": ((10, 20), "label", 17, 600, rgba(LAYOUT, "cream"), None, 0.5),
        "digit_batt": ((10, 18), "label", 14, 600, rgba(LAYOUT, "brass"), None, 0.5),
        "digit_pct": ((12, 18), "label", 14, 600, rgba(LAYOUT, "amber"), None, 0.5),
    }
    for prefix, (size, family, font_size, weight, fill, glow, padding) in specs.items():
        shared_size = common_font_size(size, family, font_size, weight, padding)
        paths = []
        for digit in range(10):
            image = render_glyph(
                str(digit),
                size,
                family,
                shared_size,
                fill,
                glow_colour=glow,
                weight=weight,
                padding=padding,
                vertical="baseline" if prefix == "digit_time" else "center",
            )
            path = SRC_IMAGES / f"{prefix}_{digit}.png"
            save_png(image, path)
            paths.append(path)
        # Index 10 is the minus sign: compile.exe/Mi Create numbers widgets index
        # the 11th bitmap when the formatted value is negative (e.g. temperature).
        minus = render_glyph("-", size, family, shared_size, fill, glow_colour=glow, weight=weight, padding=padding)
        path = SRC_IMAGES / f"{prefix}_minus.png"
        save_png(minus, path)
        paths.append(path)
        created[prefix] = paths
    return created


def fit_font(
    family: str,
    text: str,
    size: int,
    max_width: float,
    tracking: float = 0.0,
    weight: int | None = None,
):
    while size > 5:
        font = load_font(LAYOUT, family, size, weight=weight)
        width = sum(font.getlength(ch) for ch in text) + tracking * SS * (len(text) - 1)
        if width <= max_width * SS:
            return font
        size -= 1
    return load_font(LAYOUT, family, 5, weight=weight)


def build_weekdays() -> list[Path]:
    """Render the full Vietnamese weekday name, not a truncated abbreviation."""
    paths = []
    for index, name in enumerate(META["weekdays"]):
        layer, draw = new_layer(110, 26)
        font = fit_font("label", name, 18, 106, 0.2, weight=700)
        # Leave room above the capital-line for Vietnamese diacritics.  The
        # old y=1 top-aligned each glyph and made accented letters sink.
        draw_text(draw, (2, 6), name, font, rgba(LAYOUT, "text"), 0.2, "la")
        path = SRC_IMAGES / f"weekday_{index}.png"
        save_png(downsample(layer, (110, 26)), path)
        paths.append(path)
    return paths


def build_rings() -> list[Path]:
    paths = []
    size = (88, 88)
    for pct in range(0, 101, 5):
        layer, draw = new_layer(*size)
        box = [sc(6), sc(6), sc(82), sc(82)]
        track = mix(hex_rgb(COLORS["brass"]), hex_rgb(COLORS["bg"]), 0.82)
        draw.arc(box, 0, 359, fill=track + (255,), width=sc(5))
        inner = mix(hex_rgb(COLORS["brass"]), hex_rgb(COLORS["bg"]), 0.72)
        draw.arc([sc(15), sc(15), sc(73), sc(73)], 0, 359, fill=inner + (110,), width=sc(1))
        draw.arc([sc(2), sc(2), sc(86), sc(86)], 0, 359, fill=hex_rgb(COLORS["brass"]) + (75,), width=sc(1))
        if pct > 0:
            amber = hex_rgb(COLORS["amber"])
            end = -90 + 360 * pct / 100
            draw.arc(box, -90, end if pct < 100 else 269.9, fill=amber + (255,), width=sc(5))
            # rounded caps
            for angle in (-90, end if pct < 100 else 269.9):
                t = math.radians(angle)
                px, py = 44 + math.cos(t) * 38, 44 + math.sin(t) * 38
                draw.ellipse([sc(px - 2.6), sc(py - 2.6), sc(px + 2.6), sc(py + 2.6)], fill=amber + (255,))
            mask = Image.new("L", layer.size, 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.arc(box, -90, end if pct < 100 else 269.9, fill=255, width=sc(5))
            add_glow(layer, mask, hex_rgb(COLORS["amber"]) + (255,), 2.8, strength=150)
        path = SRC_IMAGES / f"ring_{pct:02d}.png"
        save_png(downsample(layer, size), path)
        paths.append(path)
    return paths


def widget_images(widget: dict) -> list[str]:
    if widget["kind"] == "imagelist":
        return widget["images"]
    prefix = widget["image"]
    return [f"{prefix}_{i}" for i in range(10)] + [f"{prefix}_minus"]


def compose_widget(canvas: Image.Image, widget: dict, sample: dict, assets: dict[str, Image.Image]) -> None:
    if widget["kind"] == "imagelist":
        index = widget.get("preview", widget.get("default", 0))
        img = assets[widget["images"][index]]
        canvas.alpha_composite(img, (widget["x"], widget["y"]))
        return
    value = widget.get("preview", "0")
    digits = widget["digits"]
    chars = parse_number(int(value), digits, bool(widget.get("blanking", 1)))
    cell_w = assets[f"{widget['image']}_0"].width
    spacing = widget.get("spacing", 0)
    for index, char in enumerate(chars):
        if char is None:
            continue
        img = assets[f"{widget['image']}_{int(char)}"]
        canvas.alpha_composite(img, (widget["x"] + index * (cell_w + spacing), widget["y"]))


def build_preview(background: Image.Image, assets: dict[str, Image.Image]) -> Image.Image:
    sample = META["sample"]
    canvas = background.copy()
    for widget in LAYOUT["widgets"]:
        compose_widget(canvas, widget, sample, assets)
    return canvas


def build_captioned_preview(raw: Image.Image) -> Image.Image:
    scale = 2
    margin_top = 12
    caption_h = 62
    width = W * scale
    height = H * scale + caption_h + margin_top
    out = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(out, "RGBA")

    # The real display is a rounded rectangle (radius 82 at 1x).  Mask the
    # preview so clipped content is visible before installing and the image
    # matches what the watch can actually show.
    radius = int(META.get("corner_radius", 82)) * scale
    watch = raw.resize((W * scale, H * scale), Image.LANCZOS)
    mask = Image.new("L", watch.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, watch.width - 1, watch.height - 1], radius=radius, fill=255)
    out.paste(watch, (0, margin_top), mask)

    # thin HUD frame follows the rounded display edge
    frame = hex_rgb(COLORS["brass"]) + (110,)
    draw.rounded_rectangle(
        [0, margin_top, width - 1, margin_top + H * scale - 1],
        radius=radius,
        outline=frame,
        width=1,
    )

    # Caption is drawn at 2x directly: draw_text() works in 1x design pixels
    # multiplied by SS, which would put it outside this 2x canvas.
    font = ImageFont.truetype(str(font_path(LAYOUT, "label")), 20)
    small = ImageFont.truetype(str(font_path(LAYOUT, "label_medium")), 16)
    note = META["preview_note"]
    draw.text(
        (width / 2, margin_top + H * scale + 8),
        note,
        font=font,
        fill=hex_rgb(COLORS["muted"]) + (255,),
        anchor="ma",
    )
    draw.text(
        (width / 2, margin_top + H * scale + 32),
        "Redmi Watch 5 Active · 320×385 · Tech HUD VI",
        font=small,
        fill=hex_rgb(COLORS["brass"]) + (220,),
        anchor="ma",
    )
    return out


def build_fprj() -> str:
    lines = [
        '<?xml version="1.0" encoding="utf-8" ?>',
        f'<FaceProject DeviceType="{META["device_type"]}">',
        f'  <Screen Title={quoteattr(META["title"])} Bitmap="preview.png">',
        '    <Widget Shape="30" Name="background" X="0" Y="0" Width="320" Height="385" Alpha="255" Visible_Src="0" Bitmap="background.png" />',
    ]
    for widget in LAYOUT["widgets"]:
        attrs = [
            f'Name="{widget["id"]}"',
            f'X="{widget["x"]}"',
            f'Y="{widget["y"]}"',
            f'Width="{widget["w"]}"',
            f'Height="{widget["h"]}"',
            'Alpha="255"',
            'Visible_Src="0"',
        ]
        if widget["kind"] == "imagelist":
            attrs.append('Shape="31"')
            attrs.append(f'Index_Src="{widget["source"]}"')
            attrs.append(f'DefaultIndex="{widget.get("default", 0)}"')
            names = [f'{name}.png' for name in widget["images"]]
            thresholds = widget.get("thresholds") or list(range(len(names)))
            parts = [f"({threshold}):{name}" for threshold, name in zip(thresholds, names)]
            attrs.append(f'BitmapList="{"|".join(parts)}"')
        else:
            attrs.append('Shape="32"')
            attrs.append(f'Digits="{widget["digits"]}"')
            attrs.append(f'Alignment="{widget.get("align", 0)}"')
            attrs.append(f'Spacing="{widget.get("spacing", 0)}"')
            attrs.append(f'Blanking="{widget.get("blanking", 1)}"')
            attrs.append(f'Value_Src="{widget["source"]}"')
            names = [f'{widget["image"]}_{i}.png' for i in range(10)]
            names.append(f'{widget["image"]}_minus.png')
            attrs.append(f'BitmapList="{"|".join(names)}"')
        lines.append("    <Widget " + " ".join(attrs) + " />")
    lines += ["  </Screen>", "</FaceProject>", ""]
    return "\n".join(lines)


def main() -> int:
    SRC_IMAGES.mkdir(parents=True, exist_ok=True)
    (ROOT / "assets" / "backgrounds").mkdir(parents=True, exist_ok=True)
    # Remove obsolete bitmaps (for example the retired status dot) so the
    # directory always matches the current layout.
    for stale in SRC_IMAGES.glob("*.png"):
        stale.unlink()

    background = build_background()
    save_png(background, BACKGROUND_PATH)
    save_png(background, SRC_IMAGES / "background.png")

    build_digits()
    build_weekdays()
    build_rings()

    assets: dict[str, Image.Image] = {}
    for path in sorted(SRC_IMAGES.glob("*.png")):
        assets[path.stem] = Image.open(path).convert("RGBA")

    raw_preview = build_preview(background, assets)
    save_png(raw_preview, PREVIEW_RAW_PATH)
    save_png(raw_preview, SRC_IMAGES / "preview.png")
    save_png(build_captioned_preview(raw_preview), PREVIEW_PATH)

    fprj = build_fprj()
    FPRJ_PATH.write_text(fprj, encoding="utf-8", newline="\n")

    manifest = {
        "layout_sha256": sha256_file(LAYOUT_PATH),
        "fprj_sha256": sha256_file(FPRJ_PATH),
        "background_sha256": sha256_file(BACKGROUND_PATH),
        "preview_sha256": sha256_file(PREVIEW_PATH),
        "images": {
            path.name: sha256_file(path) for path in sorted(SRC_IMAGES.glob("*.png"))
        },
    }
    manifest_path = ROOT / "assets" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest['images'])} bitmaps, preview and {FPRJ_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
