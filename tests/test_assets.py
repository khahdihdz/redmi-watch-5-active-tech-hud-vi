import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import parse_number  # noqa: E402


def test_zero_value_keeps_one_digit():
    assert parse_number(0, 6) == [None, None, None, None, None, "0"]
    assert parse_number(0, 1) == ["0"]
    assert parse_number(8642, 6) == [None, None, "8", "6", "4", "2"]


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
