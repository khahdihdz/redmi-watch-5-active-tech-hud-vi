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
    for word in ("THỨ", "THÁNG", "BƯỚC", "TIM", "CALO", "NHIỆT ĐỘ", "MỤC TIÊU", "TRẠNG THÁI"):
        assert word in text


def test_widgets_stay_inside_canvas():
    for widget in LAYOUT["widgets"]:
        assert widget["x"] >= 0 and widget["y"] >= 0
        assert widget["x"] + widget["w"] <= 320
        assert widget["y"] + widget["h"] <= 385


def test_no_undocumented_distance_source():
    sources = {widget["source"] for widget in LAYOUT["widgets"]}
    assert "0825" not in sources
    assert "distance" in LAYOUT["notes"]


def test_preview_is_marked_as_illustrative():
    assert "MINH HỌA" in LAYOUT["meta"]["preview_note"]


@pytest.mark.parametrize("widget_id", ["steps", "heart", "calories", "temp", "goal_ring", "status", "weekday", "battery"])
def test_core_widgets_exist(widget_id):
    assert any(widget["id"] == widget_id for widget in LAYOUT["widgets"])
