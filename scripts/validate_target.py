#!/usr/bin/env python3
"""Validate the target device contract and the build toolchain pins."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LAYOUT_PATH, ROOT, load_layout  # noqa: E402

DEVICE = {
    "name": "Redmi Watch 5 Active",
    "device_type": "3651",
    "width": 320,
    "height": 385,
    "corner_radius": 82,
    # Evidence: ooflet/Mi-Create src/data/devices.json (redmi_watch_5_active)
    # and m0tral/MiWatchLuaWatchfaces/_NonLuaModels/RedmiWatch5_Active/*.fprj
}

PALETTE = {
    "bg": "#0B0806",
    "bg2": "#1B120B",
    "panel": "#17100B",
    "brass": "#C99A4B",
    "brass_dark": "#6B4A23",
    "copper": "#B4633B",
    "amber": "#FFB24A",
    "cream": "#F2E2C2",
    "text": "#F2E2C2",
    "muted": "#A88A5E",
    "patina": "#4F8B78",
    "red": "#C45A45",
}

# Sources documented for redmi_watch_5_active by Mi Create's sources.json.
ALLOWED_SOURCES = {
    "0811": "Hour",
    "0911": "Hour low digit",
    "1000911": "Hour high digit",
    "1011": "Minute",
    "1111": "Minute low digit",
    "1211": "Minute high digit",
    "1811": "Second",
    "1911": "Second low digit",
    "1001911": "Second high digit",
    "1812": "Day",
    "1912": "Day low digit",
    "1001912": "Day high digit",
    "2012": "Weekday index",
    "1012": "Month",
    "0812": "Year",
    "0813": "AM/PM",
    "3031": "Weather type",
    "2031": "Weather temperature (C)",
    "40009031": "Weather temperature (F)",
    "0841": "Battery percent",
    "1841": "Sleep status",
    "2041": "Bluetooth connection status",
    "3041": "Screen lock status",
    "0822": "Heart rate",
    "1022": "Interval HRM",
    "0821": "Step count",
    "1021": "Step goal percentage",
    "0823": "Active calories",
    "1023": "Calorie goal percentage",
    "0824": "Stand value",
    "0826": "Stress",
    "0828": "Sleep score",
    "5031": "Sleep score (alias)",
}

COMPILER_PIN = {
    "project": "ooflet/Mi-Create",
    "commit": "586a917dec69626447254adc965daabb97fb30dc",
    "path": "src/compiler/compile.exe",
    "sha256": "bf0f7230f4fd08ed45d9a9fd1b8359a679b04b87998825a259e0ef49ba239f30",
    "size": 12999680,
    "license": "Third-party closed-source compiler, not redistributed by this repository",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    layout = load_layout()
    meta = layout["meta"]
    errors: list[str] = []

    if meta["device"] != DEVICE["name"]:
        errors.append(f"device is {meta['device']!r}")
    if str(meta["device_type"]) != DEVICE["device_type"]:
        errors.append(f"device_type is {meta['device_type']!r}, expected 3651")
    if meta["canvas"] != {"w": DEVICE["width"], "h": DEVICE["height"]}:
        errors.append(f"canvas is {meta['canvas']}, expected 320x385")
    if meta.get("corner_radius") != DEVICE["corner_radius"]:
        errors.append(f"corner_radius is {meta.get('corner_radius')!r}, expected {DEVICE['corner_radius']}")
    if meta["colors"] != PALETTE:
        errors.append("palette does not match the locked Tech HUD palette")

    for name, path in meta["fonts"].items():
        full = ROOT / path
        if not full.is_file():
            errors.append(f"font {name} missing: {path}")

    used_sources = {str(widget["source"]) for widget in layout["widgets"]}
    unknown = used_sources - set(ALLOWED_SOURCES)
    if unknown:
        errors.append(f"undocumented data sources: {sorted(unknown)}")

    # The format has no distance source for this model. Never invent one.
    if "0825" in used_sources or any("distance" in ALLOWED_SOURCES[s].lower() for s in used_sources):
        errors.append("a distance source was used although none is documented for DeviceType 3651")

    if "distance" not in layout.get("notes", {}):
        errors.append("layout.notes must document the missing distance source")

    if not re.fullmatch(r"\d+\.\d+\.\d+", meta["version"]):
        errors.append("version is not semantic")

    pin_path = ROOT / "docs" / "compiler-pin.json"
    if not pin_path.is_file():
        errors.append("docs/compiler-pin.json missing")
    else:
        pin = json.loads(pin_path.read_text(encoding="utf-8"))
        for key, value in COMPILER_PIN.items():
            if pin.get(key) != value:
                errors.append(f"compiler pin mismatch for {key}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("OK: target contract valid (Redmi Watch 5 Active, DeviceType 3651, 320x385)")
    print(f"OK: {len(used_sources)} documented data sources, palette locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
