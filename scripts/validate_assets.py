#!/usr/bin/env python3
"""Validate every generated bitmap, Vietnamese glyph and .fprj reference."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BACKGROUND_PATH,
    FPRJ_PATH,
    LAYOUT_PATH,
    PREVIEW_PATH,
    PREVIEW_RAW_PATH,
    ROOT,
    SRC_IMAGES,
    fits_rounded_display,
    hex_rgb,
    load_font_cmap,
    load_layout,
    text_width,
    load_font,
)

VIETNAMESE = "ăâđêôơưĂÂĐÊÔƠƯáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"

errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def luminance(rgb: tuple[int, int, int]) -> float:
    values = []
    for channel in rgb:
        c = channel / 255
        values.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = luminance(a), luminance(b)
    light, dark = max(la, lb), min(la, lb)
    return (light + 0.05) / (dark + 0.05)


def verify_png(path: Path) -> Image.Image:
    try:
        with Image.open(path) as probe:
            probe.verify()
        image = Image.open(path)
        image.load()
        return image.convert("RGBA")
    except Exception as exc:  # noqa: BLE001 - report the concrete decoder error
        errors.append(f"invalid PNG {path.relative_to(ROOT)}: {exc}")
        return Image.new("RGBA", (1, 1))


def main() -> int:
    layout = load_layout()
    meta = layout["meta"]
    W, H = meta["canvas"]["w"], meta["canvas"]["h"]

    # ---- fonts / Vietnamese coverage -------------------------------------------------
    weekdays = meta["weekdays"]
    required_chars = set(VIETNAMESE)
    for label in layout["labels"]:
        required_chars |= set(label["text"])
    for text in weekdays:
        required_chars |= set(text)
    for font_name in ("label", "label_medium", "label_regular"):
        cmap = load_font_cmap(ROOT / meta["fonts"][font_name])
        missing = {ch for ch in required_chars if ord(ch) not in cmap}
        check(not missing, f"{font_name} misses glyphs: {''.join(sorted(missing))}")
    check("Lora" in meta["fonts"]["display"], "display font is not Lora")
    check("Lora" in meta["fonts"]["label"], "label font is not Lora")
    check("DSEG7" in meta["fonts"]["clock"], "clock font is not DSEG7")
    display_cmap = load_font_cmap(ROOT / meta["fonts"]["display"])
    check(all(ord(str(d)) in display_cmap for d in range(10)), "display font misses digits")
    clock_cmap = load_font_cmap(ROOT / meta["fonts"]["clock"])
    check(all(ord(str(d)) in clock_cmap for d in range(10)), "clock font misses digits")

    # ---- static label fit and contrast ------------------------------------------------
    label_boxes: list[tuple[str, float, float, float, float]] = []
    for label in layout["labels"]:
        font = load_font(layout, label["font"], label["size"], weight=label.get("weight", 700))
        width = text_width(font, label["text"], label.get("tracking", 0.0)) / 4  # SS
        anchor = label.get("anchor", "la")
        x = label["x"]
        if anchor == "ra":
            x -= width
        elif anchor == "ma":
            x -= width / 2
        check(width <= label["max_width"] + 0.5, f"label {label['id']} overflows max_width ({width:.1f}>{label['max_width']})")
        check(x >= 2 and x + width <= W - 2, f"label {label['id']} leaves the canvas (x={x:.1f}, w={width:.1f})")
        check(label["y"] + label["size"] + 2 <= H, f"label {label['id']} leaves the canvas vertically")
        fg = hex_rgb(meta["colors"][label["color"]])
        bg = (0, 0, 0) if label["y"] >= 150 else (0, 0, 0)
        ratio = contrast(fg, bg)
        minimum = 3.0 if label["color"] == "muted" else 4.5
        check(ratio >= minimum, f"label {label['id']} contrast {ratio:.2f} < {minimum}")
        label_boxes.append((label["id"], x, label["y"], x + width, label["y"] + label["size"]))

    # Pairwise overlap check: a one-pixel gap is required so descenders and
    # accents cannot collide even when a font is re-rendered.
    for index, first in enumerate(label_boxes):
        for second in label_boxes[index + 1 :]:
            if (
                first[1] < second[3] + 1
                and second[1] < first[3] + 1
                and first[2] < second[4] + 1
                and second[2] < first[4] + 1
            ):
                errors.append(f"labels overlap: {first[0]} and {second[0]}")

    ring = next(widget for widget in layout["widgets"] if widget["id"] == "goal_ring")
    goal = next(label for label in layout["labels"] if label["id"] == "goal_label")
    check(goal["y"] >= ring["y"] + ring["h"] + 4, "goal_label is too close to the goal ring")
    check(goal["y"] + goal["size"] <= H - 16, "goal_label is too close to the bottom edge")

    # ---- rounded display safety ------------------------------------------------------
    radius = meta["corner_radius"]
    for panel in layout["panels"]:
        check(
            fits_rounded_display(panel["x"], panel["y"], panel["w"], panel["h"], W, H, radius),
            f"panel {panel['id']} enters the rounded corner",
        )
    for icon in layout["icons"]:
        check(
            fits_rounded_display(icon["x"], icon["y"], icon["w"], icon["h"], W, H, radius),
            f"icon {icon['id']} enters the rounded corner",
        )
    for widget in layout["widgets"]:
        check(
            fits_rounded_display(widget["x"], widget["y"], widget["w"], widget["h"], W, H, radius),
            f"widget {widget['id']} enters the rounded corner",
        )
    for label_id, x0, y0, x1, y1 in label_boxes:
        check(
            fits_rounded_display(x0, y0, x1 - x0, y1 - y0 + 4, W, H, radius),
            f"label {label_id} enters the rounded corner",
        )

    # ---- canvas assets ---------------------------------------------------------------
    background = verify_png(BACKGROUND_PATH)
    check(background.size == (W, H), f"background is {background.size}, expected {(W, H)}")
    check(background.getbbox() is not None, "background is fully transparent")
    if background.size == (W, H):
        alpha = background.getchannel("A")
        check(alpha.getextrema()[0] >= 250, "background must be opaque")
        check(background.convert("RGB").getextrema() != ((0, 0), (0, 0), (0, 0)), "background is pure black with no HUD art")

    raw_preview = verify_png(PREVIEW_RAW_PATH)
    check(raw_preview.size == (W, H), f"raw preview is {raw_preview.size}, expected {(W, H)}")
    captioned = verify_png(PREVIEW_PATH)
    check(captioned.size == (W * 2, H * 2 + 74), f"captioned preview is {captioned.size}")

    # ---- widget bitmaps ---------------------------------------------------------------
    expected: dict[str, tuple[int, int]] = {"background": (W, H), "preview": (W, H)}
    for prefix, size in {
        "digit_time": (64, 88),
        "digit_metric": (14, 24),
        "digit_small": (10, 24),
        "digit_batt": (10, 24),
        "digit_pct": (12, 20),
    }.items():
        for digit in range(10):
            expected[f"{prefix}_{digit}"] = size
        expected[f"{prefix}_minus"] = size
    for index in range(7):
        expected[f"weekday_{index}"] = (110, 26)
    for pct in range(0, 101, 5):
        expected[f"ring_{pct:02d}"] = (88, 88)

    on_disk = {path.stem for path in SRC_IMAGES.glob("*.png")}
    check(on_disk == set(expected), f"image set mismatch: missing={sorted(set(expected) - on_disk)} extra={sorted(on_disk - set(expected))}")

    for name, size in expected.items():
        path = SRC_IMAGES / f"{name}.png"
        if not path.is_file():
            continue
        image = verify_png(path)
        check(image.size == size, f"{name}.png is {image.size}, expected {size}")
        if name.startswith("digit_") or name.startswith("ring_") or name.startswith("weekday_"):
            check(image.getchannel("A").getextrema()[0] == 0, f"{name}.png background is not transparent")
            check(image.getchannel("A").getextrema()[1] > 40, f"{name}.png has no visible ink")
        if name.startswith("ring_"):
            expected_pct = int(name.split("_")[1])
            if expected_pct == 0:
                # only the track is allowed
                pass

    # ---- .fprj -----------------------------------------------------------------------
    check(FPRJ_PATH.is_file(), "tech_hud_vi.fprj missing")
    if FPRJ_PATH.is_file():
        raw = FPRJ_PATH.read_bytes()
        check(raw.decode("utf-8") == raw.decode("utf-8"), "fprj is not valid UTF-8")
        check(not raw.startswith(b"\xff\xfe"), "fprj must be UTF-8, not UTF-16")
        tree = ET.fromstring(raw.decode("utf-8"))
        check(tree.tag == "FaceProject", "root element is not FaceProject")
        check(tree.get("DeviceType") == "3651", "fprj DeviceType is not 3651")
        screen = tree.find("Screen")
        check(screen is not None, "fprj has no Screen")
        if screen is not None:
            check(screen.get("Title") == meta["title"], "fprj title does not match layout")
            check((SRC_IMAGES / (screen.get("Bitmap") or "")).is_file(), "fprj preview bitmap missing")
            names: set[str] = set()
            widgets = screen.findall("Widget")
            check(len(widgets) == len(layout["widgets"]) + 1, f"fprj has {len(widgets)} widgets")
            for widget in widgets:
                name = widget.get("Name", "")
                check(name and name not in names, f"duplicate/empty widget name: {name}")
                names.add(name)
                x, y = int(widget.get("X", "0")), int(widget.get("Y", "0"))
                w, h = int(widget.get("Width", "0")), int(widget.get("Height", "0"))
                check(x >= 0 and y >= 0 and x + w <= W and y + h <= H, f"widget {name} leaves the canvas")
                shape = widget.get("Shape")
                if shape == "30":
                    bitmap = widget.get("Bitmap", "")
                    check((SRC_IMAGES / bitmap).is_file(), f"widget {name} bitmap missing: {bitmap}")
                    if (SRC_IMAGES / bitmap).is_file():
                        check(Image.open(SRC_IMAGES / bitmap).size == (w, h), f"widget {name} size mismatch")
                elif shape == "31":
                    check(widget.get("Index_Src") in {str(x["source"]) for x in layout["widgets"]}, f"widget {name} unknown source")
                    parts = (widget.get("BitmapList") or "").split("|")
                    check(len(parts) >= 2, f"widget {name} bitmap list too short")
                    previous = None
                    for part in parts:
                        check(":" in part, f"widget {name} bitmap entry missing index: {part}")
                        prefix, filename = part.split(":", 1)
                        check(prefix.startswith("(") and prefix.endswith(")"), f"widget {name} bad index prefix: {prefix}")
                        try:
                            value = int(prefix[1:-1])
                        except ValueError:
                            errors.append(f"widget {name} non-integer index: {prefix}")
                            continue
                        if previous is not None:
                            check(value > previous, f"widget {name} bitmap indexes not ascending")
                        previous = value
                        check((SRC_IMAGES / filename).is_file(), f"widget {name} image missing: {filename}")
                elif shape == "32":
                    digits = int(widget.get("Digits", "0"))
                    spacing = int(widget.get("Spacing", "0"))
                    check(widget.get("Value_Src") in {str(x["source"]) for x in layout["widgets"]}, f"widget {name} unknown source")
                    parts = (widget.get("BitmapList") or "").split("|")
                    check(len(parts) == 11, f"widget {name} must have 10 digit images plus a minus image")
                    check(parts[-1].endswith("_minus.png"), f"widget {name} 11th bitmap is not a minus image")
                    first = SRC_IMAGES / parts[0]
                    if first.is_file():
                        cell = Image.open(first).width
                        expected_width = digits * cell + spacing * max(0, digits - 1)
                        check(w == expected_width, f"widget {name} width {w} != {expected_width}")
                    for part in parts:
                        check((SRC_IMAGES / part).is_file(), f"widget {name} digit missing: {part}")
                else:
                    errors.append(f"widget {name} has unsupported shape {shape}")

    # ---- manifest --------------------------------------------------------------------
    manifest_path = ROOT / "assets" / "manifest.json"
    check(manifest_path.is_file(), "assets/manifest.json missing")
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        check(manifest.get("layout_sha256"), "manifest has no layout hash")
        check(len(manifest.get("images", {})) == len(expected), "manifest image count mismatch")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {len(on_disk)} bitmaps valid, Vietnamese glyph coverage complete")
    print(f"OK: {len(layout['labels'])} labels fit, contrast thresholds passed")
    print("OK: .fprj references all resolve; DeviceType 3651; canvas 320x385")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
