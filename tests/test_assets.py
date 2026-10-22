import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import draw_text, load_font, load_layout, parse_number  # noqa: E402

LAYOUT = load_layout()


def test_text_digit_sets_share_one_height():
    for prefix in ("digit_metric", "digit_small", "digit_batt"):
        heights = []
        for digit in range(10):
            image = Image.open(ROOT / "src" / "watchface" / "images" / f"{prefix}_{digit}.png").convert("RGBA")
            bbox = image.getchannel("A").getbbox()
            assert bbox is not None, f"{prefix}_{digit} has no ink"
            heights.append(bbox[3] - bbox[1])
        assert max(heights) - min(heights) <= 2, f"{prefix} digit heights differ: {heights}"


def test_seven_segment_digits_share_one_baseline():
    bottoms = []
    for digit in range(10):
        image = Image.open(ROOT / "src" / "watchface" / "images" / f"digit_time_{digit}.png").convert("RGBA")
        bbox = image.getchannel("A").getbbox()
        assert bbox is not None, f"digit_time_{digit} has no ink"
        bottoms.append(bbox[3])
    assert max(bottoms) - min(bottoms) <= 2, f"digit_time bottoms differ: {bottoms}"


def test_zero_value_keeps_one_digit():
    assert parse_number(0, 6) == [None, None, None, None, None, "0"]
    assert parse_number(0, 1) == ["0"]
    assert parse_number(8642, 6) == [None, None, "8", "6", "4", "2"]


def test_signed_temperature_uses_minus_cell():
    assert parse_number(28, 3, signed=True) == [None, "2", "8"]
    assert parse_number(-5, 3, signed=True) == [None, "-", "5"]
    assert parse_number(-10, 3, signed=True) == ["-", "1", "0"]
    assert parse_number(-123, 3, signed=True) == ["-", "2", "3"]


def test_text_keeps_one_baseline():
    font = load_font(LAYOUT, "label", 12)
    layer = Image.new("RGBA", (200 * 4, 40 * 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    text = "THỨ"
    draw_text(draw, (2, 10), text, font, (255, 255, 255, 255), 0.0, "la")

    x = 2 * 4
    bottoms = []
    for char in text:
        advance = font.getlength(char)
        cell = layer.crop((round(x), 0, round(x + advance), layer.height)).getchannel("A")
        bbox = cell.getbbox()
        if bbox:
            bottoms.append(bbox[3])
        x += advance

    assert len(bottoms) >= 2
    # The old per-glyph "lt" anchor produced a ~10 px difference between
    # plain and accented letters at this size.  A shared baseline is within
    # antialiasing tolerance.
    assert max(bottoms) - min(bottoms) <= 2


def run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script)], capture_output=True, text=True)


def test_target_contract():
    result = run("validate_target.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DeviceType 3651" in result.stdout


def test_assets_and_vietnamese_glyphs():
    result = run("validate_assets.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Vietnamese glyph coverage complete" in result.stdout


def test_generation_is_deterministic():
    before = (ROOT / "src" / "watchface" / "tech_hud_vi.fprj").read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_assets.py")], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    after = (ROOT / "src" / "watchface" / "tech_hud_vi.fprj").read_bytes()
    assert before == after
