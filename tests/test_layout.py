import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
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
    for word in ("BƯỚC", "TIM", "CALO", "NHIỆT ĐỘ", "MỤC TIÊU", "TRẠNG THÁI"):
        assert word in text
    assert "ĐÃ KẾT NỐI" in LAYOUT["meta"]["connection_labels"]
    assert "MẤT KẾT NỐI" in LAYOUT["meta"]["connection_labels"]


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
    assert not label_ids & {"pin_label", "thang", "date_dot", "heart_unit", "calo_unit", "core", "footer", "goal_unit"}
    widget_ids = {widget["id"] for widget in LAYOUT["widgets"]}
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


def test_no_undocumented_distance_source():
    sources = {widget["source"] for widget in LAYOUT["widgets"]}
    assert "0825" not in sources
    assert "distance" in LAYOUT["notes"]


def test_preview_is_marked_as_illustrative():
    assert "MINH HỌA" in LAYOUT["meta"]["preview_note"]


@pytest.mark.parametrize("widget_id", ["steps", "heart", "calories", "temp", "goal_ring", "goal_value", "status", "weekday", "battery"])
def test_core_widgets_exist(widget_id):
    assert any(widget["id"] == widget_id for widget in LAYOUT["widgets"])
