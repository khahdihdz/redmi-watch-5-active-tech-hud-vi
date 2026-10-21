#!/usr/bin/env python3
"""Generate every bitmap, the .fprj project and the preview from design/layout.json.

The script is deliberately deterministic: no timestamps, no randomness.
All Vietnamese labels are rasterised with Be Vietnam Pro, so the watch never
depends on a system font being able to render Vietnamese diacritics.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

from PIL import Image, ImageChops, ImageDraw, ImageFilter

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
    border = mix(hex_rgb(COLORS["cyan"]), hex_rgb(COLORS["bg"]), 0.78)
    fill = (2, 8, 13, 235)
    points = chamfer_polygon(panel["x"], panel["y"], panel["w"], panel["h"])
    draw.polygon(points, fill=fill, outline=border + (255,))
    x, y, w = panel["x"], panel["y"], panel["w"]
    draw.line([(sc(x + 8), sc(y)), (sc(x + 28), sc(y))], fill=accent + (210,), width=sc(1))
    draw.line([(sc(x + w - 18), sc(y + panel["h"])), (sc(x + w), sc(y + panel["h"]))], fill=accent + (110,), width=sc(1))
    # corner ticks
    tick = 4
    draw.line([(sc(x), sc(y + 7)), (sc(x), sc(y + 7 + tick))], fill=accent + (255,), width=sc(1))
    draw.line([(sc(x + w - 7 - tick), sc(y + panel["h"])), (sc(x + w - 7), sc(y + panel["h"]))], fill=accent + (255,), width=sc(1))


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


def build_background() -> Image.Image:
    image = Image.new("RGBA", (sc(W), sc(H)), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    cyan = hex_rgb(COLORS["cyan"])
    blue = hex_rgb(COLORS["blue"])
    muted = hex_rgb(COLORS["muted"])
    orange = hex_rgb(COLORS["orange"])

    # faint dot grid
    for gy in range(14, H - 8, 16):
        for gx in range(12, W - 8, 16):
            draw.point((sc(gx), sc(gy)), fill=blue + (26,))

    # circuit traces (deliberately low contrast so readings stay dominant)
    traces = [
        [(0, 74), (22, 74), (34, 86), (34, 120)],
        [(0, 300), (20, 300), (30, 290), (30, 258)],
        [(320, 96), (304, 96), (292, 84), (292, 58)],
        [(320, 286), (302, 286), (290, 298), (290, 350)],
        [(0, 180), (10, 180), (18, 188)],
        [(320, 210), (310, 210), (302, 202)],
    ]
    for trace in traces:
        draw.line([(sc(px), sc(py)) for px, py in trace], fill=blue + (55,), width=sc(1))
        ex, ey = trace[-1]
        draw.ellipse([sc(ex - 1.5), sc(ey - 1.5), sc(ex + 1.5), sc(ey + 1.5)], outline=cyan + (65,), width=sc(1))

    # top / bottom rules
    draw.line([(sc(10), sc(48)), (sc(W - 10), sc(48))], fill=blue + (85,), width=sc(1))
    draw.line([(sc(10), sc(48)), (sc(64), sc(48))], fill=orange + (200,), width=sc(1))
    draw.line([(sc(10), sc(358)), (sc(W - 10), sc(358))], fill=blue + (55,), width=sc(1))

    # corner brackets
    inset, arm = META["safe_inset"], 22
    bracket = cyan + (190,)
    corners = [
        [(inset, inset + arm), (inset, inset), (inset + arm, inset)],
        [(W - inset - arm, inset), (W - inset, inset), (W - inset, inset + arm)],
        [(inset, H - inset - arm), (inset, H - inset), (inset + arm, H - inset)],
        [(W - inset - arm, H - inset), (W - inset, H - inset), (W - inset, H - inset - arm)],
    ]
    for pts in corners:
        draw.line([(sc(px), sc(py)) for px, py in pts], fill=bracket, width=sc(1.4))

    # segmented tick ruler at the very edges
    for ty in range(58, H - 28, 24):
        draw.line([(sc(4), sc(ty)), (sc(7), sc(ty))], fill=muted + (70,), width=sc(1))
        draw.line([(sc(W - 7), sc(ty + 12)), (sc(W - 4), sc(ty + 12))], fill=muted + (70,), width=sc(1))

    # soft cyan glow behind the clock
    glow, gdraw = new_layer(W, 150)
    gdraw.ellipse([sc(18), sc(58), sc(W - 18), sc(142)], fill=cyan + (46,))
    glow = glow.filter(ImageFilter.GaussianBlur(sc(22)))
    image.alpha_composite(glow)

    # clock colon (two chamfered blocks)
    for cy in (78, 112):
        gdraw = ImageDraw.Draw(image, "RGBA")
        gdraw.polygon(
            [(sc(154), sc(cy)), (sc(162), sc(cy)), (sc(164), sc(cy + 4)), (sc(164), sc(cy + 10)), (sc(162), sc(cy + 14)), (sc(154), sc(cy + 14)), (sc(152), sc(cy + 10)), (sc(152), sc(cy + 4))],
            fill=cyan + (235,),
        )

    # underline under the clock
    draw.line([(sc(58), sc(148)), (sc(146), sc(148))], fill=cyan + (110,), width=sc(1))
    draw.line([(sc(174), sc(148)), (sc(262), sc(148))], fill=cyan + (110,), width=sc(1))

    # panels
    for panel in LAYOUT["panels"]:
        draw_panel(draw, panel)

    # icons
    for icon in LAYOUT["icons"]:
        draw_icon(draw, icon)

    # labels
    for label in LAYOUT["labels"]:
        font = load_font(LAYOUT, label["font"], label["size"], weight=700 if label["font"] == "display" else None)
        colour = rgba(LAYOUT, label["color"])
        draw_text(draw, (label["x"], label["y"]), label["text"], font, colour, label.get("tracking", 0.0), label.get("anchor", "la"))

    # ring ticks around the progress dial
    cx, cy, radius = 62, 306, 47
    for deg in range(0, 360, 6):
        t = math.radians(deg)
        length = 2.5 if deg % 30 else 3.5
        x1, y1 = cx + math.cos(t) * radius, cy + math.sin(t) * radius
        x2, y2 = cx + math.cos(t) * (radius + length), cy + math.sin(t) * (radius + length)
        col = cyan + (110,) if deg % 30 else orange + (170,)
        draw.line([(sc(x1), sc(y1)), (sc(x2), sc(y2))], fill=col, width=sc(1))

    final = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
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
    y = (sc(h) - th) / 2 - bbox[1]
    if glow_colour:
        mask = Image.new("L", layer.size, 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.text((x, y), char, font=font, fill=255, anchor="lt")
        add_glow(layer, mask, glow_colour + (255,), 3.4, strength=200)
    draw.text((x, y), char, font=font, fill=fill, anchor="lt")
    return downsample(layer, size)


def build_digits() -> dict[str, list[Path]]:
    created: dict[str, list[Path]] = {}
    specs = {
        "digit_time": ((48, 88), "display", 92, 700, rgba(LAYOUT, "text"), hex_rgb(COLORS["cyan"]), 3.0),
        "digit_metric": ((14, 24), "display", 24, 700, rgba(LAYOUT, "text"), None, 1.0),
        "digit_small": ((10, 20), "label", 17, 600, rgba(LAYOUT, "text"), None, 0.5),
        "digit_batt": ((10, 18), "label", 14, 600, rgba(LAYOUT, "cyan"), None, 0.5),
        "digit_pct": ((12, 18), "label", 14, 600, rgba(LAYOUT, "cyan"), None, 0.5),
    }
    for prefix, (size, family, font_size, weight, fill, glow, padding) in specs.items():
        paths = []
        for digit in range(10):
            image = render_glyph(str(digit), size, family, font_size, fill, glow_colour=glow, weight=weight, padding=padding)
            path = SRC_IMAGES / f"{prefix}_{digit}.png"
            save_png(image, path)
            paths.append(path)
        created[prefix] = paths
    return created


def fit_font(family: str, text: str, size: int, max_width: float, tracking: float = 0.0):
    while size > 5:
        font = load_font(LAYOUT, family, size)
        width = sum(font.getlength(ch) for ch in text) + tracking * SS * (len(text) - 1)
        if width <= max_width * SS:
            return font
        size -= 1
    return load_font(LAYOUT, family, 5)


def build_weekdays() -> list[Path]:
    names = ["CN", "HAI", "BA", "TƯ", "NĂM", "SÁU", "BẢY"]
    paths = []
    for index, name in enumerate(names):
        layer, draw = new_layer(34, 20)
        font = fit_font("label", name, 13, 31, 0.2)
        draw_text(draw, (17, 2), name, font, rgba(LAYOUT, "text"), 0.2, "ma")
        path = SRC_IMAGES / f"weekday_{index}.png"
        save_png(downsample(layer, (34, 20)), path)
        paths.append(path)
    return paths


def build_connection() -> list[Path]:
    variants = [
        ("NGOẠI TUYẾN", "red"),
        ("SẴN SÀNG", "green"),
    ]
    paths = []
    for index, (text, colour) in enumerate(variants):
        layer, draw = new_layer(168, 26)
        rgb = hex_rgb(COLORS[colour])
        draw.rectangle([sc(0), sc(2), sc(3), sc(24)], fill=rgb + (220,))
        font = fit_font("label", text, 19, 150, 1.2)
        draw_text(draw, (12, 3), text, font, rgb + (255,), 1.2)
        path = SRC_IMAGES / f"conn_{index}.png"
        save_png(downsample(layer, (168, 26)), path)
        paths.append(path)
    return paths


def build_dots() -> list[Path]:
    paths = []
    for index, colour in enumerate(("red", "green")):
        layer, draw = new_layer(8, 8)
        rgb = hex_rgb(COLORS[colour])
        draw.ellipse([sc(1.5), sc(1.5), sc(6.5), sc(6.5)], fill=rgb + (255,))
        path = SRC_IMAGES / f"dot_{index}.png"
        save_png(downsample(layer, (8, 8)), path)
        paths.append(path)
    return paths


def build_rings() -> list[Path]:
    paths = []
    size = (88, 88)
    for pct in range(0, 101, 5):
        layer, draw = new_layer(*size)
        box = [sc(6), sc(6), sc(82), sc(82)]
        track = mix(hex_rgb(COLORS["cyan"]), hex_rgb(COLORS["bg"]), 0.82)
        draw.arc(box, 0, 359, fill=track + (255,), width=sc(6))
        inner = mix(hex_rgb(COLORS["cyan"]), hex_rgb(COLORS["bg"]), 0.72)
        draw.arc([sc(15), sc(15), sc(73), sc(73)], 0, 359, fill=inner + (110,), width=sc(1))
        if pct > 0:
            cyan = hex_rgb(COLORS["cyan"])
            end = -90 + 360 * pct / 100
            draw.arc(box, -90, end if pct < 100 else 269.9, fill=cyan + (255,), width=sc(6))
            # rounded caps
            for angle in (-90, end if pct < 100 else 269.9):
                t = math.radians(angle)
                px, py = 44 + math.cos(t) * 38, 44 + math.sin(t) * 38
                draw.ellipse([sc(px - 3), sc(py - 3), sc(px + 3), sc(py + 3)], fill=cyan + (255,))
            mask = Image.new("L", layer.size, 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.arc(box, -90, end if pct < 100 else 269.9, fill=255, width=sc(6))
            add_glow(layer, mask, hex_rgb(COLORS["cyan"]) + (255,), 2.8, strength=150)
        path = SRC_IMAGES / f"ring_{pct:02d}.png"
        save_png(downsample(layer, size), path)
        paths.append(path)
    return paths


def widget_images(widget: dict) -> list[str]:
    if widget["kind"] == "imagelist":
        return widget["images"]
    prefix = widget["image"]
    return [f"{prefix}_{i}" for i in range(10)]


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
    # thin HUD frame around the watch render
    frame = hex_rgb(COLORS["cyan"]) + (90,)
    draw.rectangle([0, margin_top, width - 1, margin_top + H * scale - 1], outline=frame, width=1)
    out.alpha_composite(raw.resize((W * scale, H * scale), Image.LANCZOS), (0, margin_top))
    font = load_font(LAYOUT, "label", 10)
    small = load_font(LAYOUT, "label_medium", 8)
    note = META["preview_note"]
    draw_text(draw, (width / 2, margin_top + H * scale + 14), note, font, hex_rgb(COLORS["muted"]) + (255,), 1.0, "ma")
    draw_text(
        draw,
        (width / 2, margin_top + H * scale + 36),
        "Redmi Watch 5 Active · 320×385 · Tech HUD VI",
        small,
        hex_rgb(COLORS["cyan"]) + (210,),
        0.4,
        "ma",
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
            if "thresholds" in widget:
                parts = [f"({threshold}):{name}" for threshold, name in zip(widget["thresholds"], names)]
                attrs.append(f'BitmapList="{"|".join(parts)}"')
            else:
                attrs.append(f'BitmapList="{"|".join(names)}"')
        else:
            attrs.append('Shape="32"')
            attrs.append(f'Digits="{widget["digits"]}"')
            attrs.append(f'Alignment="{widget.get("align", 0)}"')
            attrs.append(f'Spacing="{widget.get("spacing", 0)}"')
            attrs.append(f'Blanking="{widget.get("blanking", 1)}"')
            attrs.append(f'Value_Src="{widget["source"]}"')
            names = [f'{widget["image"]}_{i}.png' for i in range(10)]
            attrs.append(f'BitmapList="{"|".join(names)}"')
        lines.append("    <Widget " + " ".join(attrs) + " />")
    lines += ["  </Screen>", "</FaceProject>", ""]
    return "\n".join(lines)


def main() -> int:
    SRC_IMAGES.mkdir(parents=True, exist_ok=True)
    (ROOT / "assets" / "backgrounds").mkdir(parents=True, exist_ok=True)

    background = build_background()
    save_png(background, BACKGROUND_PATH)
    save_png(background, SRC_IMAGES / "background.png")

    build_digits()
    build_weekdays()
    build_connection()
    build_dots()
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
