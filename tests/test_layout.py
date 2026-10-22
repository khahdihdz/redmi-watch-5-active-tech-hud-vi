import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import fits_rounded_display  # noqa: E402

LAYOUT = json.loads((ROOT / "design" / "layout.json").read_text(encoding="utf-8"))


def test_target_and_canvas():
    meta = LAYOUT["meta"]
    assert meta["device"] == "Redmi Watch 5 Active"
    assert meta["device_type"] == "3651"
    assert meta["canvas"] == {"w": 320, "h": 385}


def test_all_rendering_uses_be_vietnam_pro():
    fonts = LAYOUT["meta"]["fonts"]
    assert fonts["display"].endswith("BeVietnamPro-Bold.ttf")
    for label in LAYOUT["labels"]:
        assert "BeVietnamPro" in fonts[label["font"]]
    assert "Orbitron" not in json.dumps(LAYOUT, ensure_ascii=False)


def test_palette_is_locked():
    assert LAYOUT["meta"]["colors"] == {
        "bg": "#000000",
        "cyan": "#00D9FF",
        "blue": "#087EFF",
        "orange": "#FF6B00",
        "red": "#FF3158",
        "green": "#32E69B",
        "text": "#F5FAFF",
        "muted": "#7FA7CC",
    }


def test_vietnamese_labels_are_present():
    text = " ".join(label["text"] for label in LAYOUT["labels"])
    for word in ("BƯỚC", "TIM", "CALO", "NHIỆT ĐỘ", "MỤC TIÊU"):
        assert word in text
    assert "TRẠNG THÁI" not in text
    assert "connection_labels" not in LAYOUT["meta"]


def test_weekdays_use_full_vietnamese_names():
    assert LAYOUT["meta"]["weekdays"] == [
        "CHỦ NHẬT",
        "THỨ HAI",
        "THỨ BA",
        "THỨ TƯ",
        "THỨ NĂM",
        "THỨ SÁU",
        "THỨ BẢY",
    ]
    weekday = next(widget for widget in LAYOUT["widgets"] if widget["id"] == "weekday")
    assert len(weekday["images"]) == 7
    assert weekday["w"] >= 100


def test_widgets_stay_inside_canvas():
    for widget in LAYOUT["widgets"]:
        assert widget["x"] >= 0 and widget["y"] >= 0
        assert widget["x"] + widget["w"] <= 320
        assert widget["y"] + widget["h"] <= 385


def test_no_redundant_display_items():
    label_ids = {label["id"] for label in LAYOUT["labels"]}
    assert not label_ids & {
        "pin_label",
        "thang",
        "date_dot",
        "heart_unit",
        "calo_unit",
        "core",
        "footer",
        "goal_unit",
        "status_label",
    }
    panel_ids = {panel["id"] for panel in LAYOUT["panels"]}
    widget_ids = {widget["id"] for widget in LAYOUT["widgets"]}
    assert "status" not in panel_ids
    assert "status" not in widget_ids
    assert "status_dot" not in widget_ids


def test_metric_fields_have_room_for_large_values():
    widgets = {widget["id"]: widget for widget in LAYOUT["widgets"] if widget["kind"] == "dignum"}
    assert widgets["steps"]["digits"] >= 6
    assert widgets["calories"]["digits"] >= 5
    assert widgets["temp"]["digits"] >= 3
    assert widgets["battery"]["digits"] >= 3


def test_goal_label_clears_the_ring():
    ring = next(widget for widget in LAYOUT["widgets"] if widget["id"] == "goal_ring")
    label = next(label for label in LAYOUT["labels"] if label["id"] == "goal_label")
    assert label["y"] >= ring["y"] + ring["h"] + 4


def test_goal_section_is_centered():
    ring = next(widget for widget in LAYOUT["widgets"] if widget["id"] == "goal_ring")
    label = next(label for label in LAYOUT["labels"] if label["id"] == "goal_label")
    canvas_w = LAYOUT["meta"]["canvas"]["w"]
    assert ring["x"] == (canvas_w - ring["w"]) // 2
    assert label["x"] == canvas_w // 2


def test_content_fits_rounded_display():
    meta = LAYOUT["meta"]
    width, height = meta["canvas"]["w"], meta["canvas"]["h"]
    radius = meta["corner_radius"]
    for panel in LAYOUT["panels"]:
        assert fits_rounded_display(panel["x"], panel["y"], panel["w"], panel["h"], width, height, radius), panel["id"]
    for icon in LAYOUT["icons"]:
        assert fits_rounded_display(icon["x"], icon["y"], icon["w"], icon["h"], width, height, radius), icon["id"]
    for widget in LAYOUT["widgets"]:
        assert fits_rounded_display(widget["x"], widget["y"], widget["w"], widget["h"], width, height, radius), widget["id"]
    for label in LAYOUT["labels"]:
        box_w = label["max_width"]
        anchor = label.get("anchor", "la")
        if anchor == "ra":
            x0 = label["x"] - box_w
        elif anchor == "ma":
            x0 = label["x"] - box_w / 2
        else:
            x0 = label["x"]
        assert fits_rounded_display(
            x0,
            label["y"],
            box_w,
            label["size"] + 4,
            width,
            height,
            radius,
        ), label["id"]


def test_no_undocumented_distance_source():
    sources = {widget["source"] for widget in LAYOUT["widgets"]}
    assert "0825" not in sources
    assert "distance" in LAYOUT["notes"]


def test_preview_is_marked_as_illustrative():
    assert "MINH HỌA" in LAYOUT["meta"]["preview_note"]


@pytest.mark.parametrize("widget_id", ["steps", "heart", "calories", "temp", "goal_ring", "goal_value", "weekday", "battery"])
def test_core_widgets_exist(widget_id):
    assert any(widget["id"] == widget_id for widget in LAYOUT["widgets"])
