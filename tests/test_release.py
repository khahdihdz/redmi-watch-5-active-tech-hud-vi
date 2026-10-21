import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_channel_is_prerelease_without_device_evidence():
    record = json.loads((ROOT / "tests" / "device_verification.json").read_text(encoding="utf-8"))
    assert record["verified"] is False


def test_package_contains_source_and_preview():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "package_release.py"), "--version", "v0.0.0-test"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    dist = ROOT / "dist"
    preview = dist / "redmi-watch-5-active-tech-hud-vi-preview.png"
    archive = dist / "redmi-watch-5-active-tech-hud-vi-source.zip"
    checksums = dist / "SHA256SUMS.txt"
    assert preview.is_file()
    assert archive.is_file()
    assert checksums.is_file()
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    assert any(name.endswith("design/layout.json") for name in names)
    assert any(name.endswith("src/watchface/tech_hud_vi.fprj") for name in names)
    assert any(name.endswith("assets/fonts/BeVietnamPro-Bold.ttf") for name in names)
    assert not any("__pycache__" in name for name in names)
    assert "redmi-watch-5-active-tech-hud-vi-preview.png" in checksums.read_text(encoding="utf-8")


def test_stable_is_refused_without_device_verification():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "package_release.py"), "--version", "v0.0.1-test", "--channel", "stable"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "stable" in result.stdout
