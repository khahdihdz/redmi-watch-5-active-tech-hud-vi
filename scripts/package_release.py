#!/usr/bin/env python3
"""Create preview, source archive, checksums, build info and release notes."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DIST_DIR, PREVIEW_PATH, ROOT, load_layout, sha256_file  # noqa: E402

ARTIFACT = "redmi-watch-5-active-tech-hud-vi"
SOURCE_FILES = [
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "requirements.txt",
]
SOURCE_DIRS = [
    ".github",
    "assets",
    "design",
    "docs",
    "scripts",
    "src",
    "tests",
]
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git"}


def release_channel() -> tuple[bool, dict]:
    path = ROOT / "tests" / "device_verification.json"
    if not path.is_file():
        return True, {"verified": False, "reason": "missing device verification record"}
    record = json.loads(path.read_text(encoding="utf-8"))
    return not bool(record.get("verified", False)), record


def iter_sources():
    for name in SOURCE_FILES:
        path = ROOT / name
        if path.is_file():
            yield path
    for name in SOURCE_DIRS:
        base = ROOT / name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            yield path


def build_source_zip(target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(iter_sources()):
            arcname = Path(ARTIFACT) / path.relative_to(ROOT)
            info = zipfile.ZipInfo(str(arcname), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def write_checksums(paths: list[Path], target: Path) -> None:
    lines = []
    for path in sorted(paths):
        if path.name == "SHA256SUMS.txt" or not path.is_file():
            continue
        lines.append(f"{sha256_file(path)}  {path.name}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_notes(target: Path, version: str, prerelease: bool, record: dict, checksums: list[tuple[str, str]]) -> None:
    layout = load_layout()
    meta = layout["meta"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status = "Pre-release (chưa kiểm thử thiết bị thật)" if prerelease else "Stable"
    repo = os.environ.get("GITHUB_REPOSITORY", "khahdihdz/redmi-watch-5-active-tech-hud-vi")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    preview_url = f"{server}/{repo}/releases/download/{version}/{ARTIFACT}-preview.png"
    table = "\n".join(f"| `{name}` | `{digest}` |" for name, digest in checksums)
    files = "\n".join(f"- `{name}`" for name, _ in checksums)
    files += "\n- `SHA256SUMS.txt`"
    text = f"""# Redmi Watch 5 Active Tech HUD VI: Brass {version}

- **Phiên bản:** {version}
- **Ngày phát hành:** {today}
- **Kênh:** {status}
- **Thiết bị:** {meta['device']} — DeviceType {meta['device_type']}, {meta['canvas']['w']}×{meta['canvas']['h']}
- **Định dạng:** Gen2 watch face (`.bin`, magic `5AA53412`)

## Thay đổi

- Giao diện **steampunk / brass** tiếng Việt có dấu, tối ưu màn hình 320×385.
- Đồng hồ `HH:MM` dùng **DSEG7 Classic Bold** bảy đoạn màu amber trong khung đồng có đinh tán.
- Nhãn và số liệu dùng **Lora** serif (OFL); Lora có đủ glyph tiếng Việt, DSEG7 chỉ dùng cho chữ số giờ:phút.
- Các số bảy đoạn `1`/`4` được căn đáy chung với `0`/`8`, không bị lệch dòng.
- Nền da/gunmetal, bánh răng đồng, ống dẫn, panel viền brass và vòng MỤC TIÊU kiểu mặt số.
- Bố cục tối giản: bỏ footer tên thiết bị, mã phiên bản, nhãn PIN, đơn vị BPM/KCAL, panel trạng thái và chấm trạng thái trùng.
- Tên thứ đầy đủ (CHỦ NHẬT … THỨ BẢY), ngày dạng `21/10`.
- Bốn panel dữ liệu: BƯỚC, TIM, CALO, NHIỆT ĐỘ; vùng số rộng hơn để không tràn.
- Vòng MỤC TIÊU 21 mức (5% mỗi mức) lấy từ phần trăm mục tiêu bước chân, căn giữa; nhãn không bị vạch trang trí đè.
- Toàn bộ nội dung nằm trong vùng an toàn của màn hình bo góc bán kính 82 px; không đặt chữ/số sát bốn góc.
- Build tự động, kiểm tra cấu trúc nhị phân, checksum SHA-256 và GitHub Actions.

## Ảnh xem trước

![Tech HUD VI]({preview_url})

> Ảnh xem trước dùng **số liệu minh họa**. Trên đồng hồ, các giá trị lấy từ cảm biến và ứng dụng điện thoại.

## Tệp tải xuống

{files}

## Cài đặt

Chỉ dùng phương pháp đã được cộng đồng ghi nhận cho đúng mẫu Redmi Watch 5 Active:

1. Đồng hồ đã ghép nối với Mi Fitness. **Không unpair hoặc reset** sau bước này.
2. Lưu log Mi Fitness: Hồ sơ → Giới thiệu ứng dụng → chạm logo 10 lần → xác nhận. File zip nằm trong `Download/wearablelog`.
3. Cài **Notify for Xiaomi** (Google Play), chọn nhập từ ứng dụng chính thức và trỏ tới thư mục log.
4. Tắt quyền của Mi Fitness khi Notify yêu cầu (không gỡ Mi Fitness).
5. Trong Notify: Thiết bị → Mặt đồng hồ → menu phụ → **Custom watch face (.bin)** → chọn `tech-hud-vi.bin` → Install.
6. Trên đồng hồ, nhấn giữ mặt hiện tại và vuốt tới mặt mới.

Mi Fitness chỉ cài mặt từ catalogue của Xiaomi. Gadgetbridge hiện không cài được mặt `.bin` cho mẫu này. Không có phương pháp chính thức từ iPhone.

## Phục hồi

- Nhấn giữ mặt đồng hồ → chọn một mặt có sẵn của máy.
- Hoặc xoá mặt tuỳ chỉnh đã cài; không cần flash firmware.
- Dự án không can thiệp bootloader, root hay firmware hệ thống.

## Trạng thái kiểm thử

- Build compiler thực tế: **ĐẠT** (GitHub Actions, Windows runner).
- Kiểm tra magic, phiên bản, bảng resource trong biên: **ĐẠT**.
- Kiểm thử trên thiết bị thật: **CHƯA THỰC HIỆN**.
- Vì chưa có xác nhận trên thiết bị, bản này được phát hành ở kênh **pre-release**.

Ghi chú kiểm thử thiết bị: `{record.get('reason', record.get('notes', 'chưa có bản ghi'))}`

## Giới hạn tương thích

- Chỉ dành cho **Redmi Watch 5 Active** (DeviceType 3651). Không dùng cho Redmi Watch 5, 5 Lite hay mẫu khác.
- Không có ô **KM**: định dạng của mẫu này không công bố nguồn quãng đường; dự án không bịa dữ liệu.
- Nhiệt độ lấy từ thời tiết do ứng dụng điện thoại cung cấp; có thể trống nếu chưa đồng bộ.
- Không có AOD trong phiên bản này.
- Chưa xác minh hiển thị thực tế ngoài trời hoặc hao pin.

## SHA-256

| Tệp | SHA-256 |
|---|---|
{table}

Xác minh:

```bash
sha256sum -c SHA256SUMS.txt
```

## Giấy phép

Mã nguồn và thiết kế: MIT. Font **Lora** và **DSEG7 Classic**: SIL Open Font License 1.1.
Be Vietnam Pro và Orbitron còn trong source để tham khảo nhưng không còn được dùng để render từ v1.1.0.
Compiler `compile.exe` là công cụ bên thứ ba, **không** được phân phối trong repo hay release.
"""
    target.write_text(text, encoding="utf-8")


def write_build_info(version: str, prerelease: bool, record: dict, binary: Path | None) -> None:
    layout = load_layout()
    meta = layout["meta"]
    lines = [
        "REDMI WATCH 5 ACTIVE — TECH HUD VI: BRASS",
        "==========================================",
        f"Phiên bản:             {version}",
        f"Kênh:                  {'pre-release' if prerelease else 'stable'}",
        f"Phong cách:            Steampunk / brass",
        f"Font:                  DSEG7 (giờ:phút), Lora (nhãn/số liệu)",
        f"Thiết bị:              {meta['device']} (DeviceType {meta['device_type']})",
        f"Độ phân giải:          {meta['canvas']['w']}x{meta['canvas']['h']}",
        f"Thời điểm đóng gói:    {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Git commit:            {os.environ.get('GITHUB_SHA', 'local')}",
        f"Workflow run:          {os.environ.get('GITHUB_RUN_ID', 'local')}",
        f"Kiểm thử thiết bị:     {'ĐÃ XÁC NHẬN' if record.get('verified') else 'CHƯA THỰC HIỆN'}",
        "",
        "Thành phần:",
        "- tech-hud-vi-preview.png : ảnh xem trước, số liệu minh họa",
        f"- {ARTIFACT}-source.zip : toàn bộ mã nguồn, asset, font, test và workflow",
        "- SHA256SUMS.txt : checksum của mọi tệp phát hành",
        "- BUILD-INFO.txt : thông tin build này",
    ]
    if binary and binary.is_file():
        lines.append(f"- tech-hud-vi.bin : biên dịch thật, {binary.stat().st_size} bytes, sha256 {sha256_file(binary)}")
        lines.append("")
        lines.append("Binary đã qua kiểm tra cấu trúc (magic/version/resource table/title).")
        lines.append("KHÔNG được coi là đã kiểm thử trên thiết bị thật.")
    else:
        lines.append("")
        lines.append("KHÔNG có tech-hud-vi.bin trong gói này: compiler chưa chạy hoặc chưa đạt kiểm tra.")
        lines.append("Không tải gói này như một mặt đồng hồ cài được.")
    lines.append("")
    lines.append("Compiler: ooflet/Mi-Create src/compiler/compile.exe @ 586a917dec69626447254adc965daabb97fb30dc")
    lines.append("SHA-256 compiler: bf0f7230f4fd08ed45d9a9fd1b8359a679b04b87998825a259e0ef49ba239f30")
    lines.append("")
    (DIST_DIR / "BUILD-INFO.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version")
    parser.add_argument("--require-bin", action="store_true")
    parser.add_argument("--channel", choices=["auto", "stable", "prerelease"], default="auto")
    args = parser.parse_args()

    layout = load_layout()
    version = args.version or f"v{layout['meta']['version']}"
    if not version.startswith("v"):
        version = "v" + version

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for stale in ("SHA256SUMS.txt", "BUILD-INFO.txt", "release-notes.md", f"{ARTIFACT}-source.zip", f"{ARTIFACT}-preview.png"):
        (DIST_DIR / stale).unlink(missing_ok=True)

    preview = DIST_DIR / f"{ARTIFACT}-preview.png"
    shutil.copy2(PREVIEW_PATH, preview)

    source_zip = DIST_DIR / f"{ARTIFACT}-source.zip"
    build_source_zip(source_zip)

    binary = DIST_DIR / "tech-hud-vi.bin"
    if args.require_bin and (not binary.is_file() or binary.stat().st_size == 0):
        print("FAIL: --require-bin nhưng dist/tech-hud-vi.bin không tồn tại hoặc rỗng")
        return 1

    auto_prerelease, record = release_channel()
    prerelease = auto_prerelease if args.channel == "auto" else args.channel == "prerelease"
    if args.channel == "stable" and auto_prerelease:
        print("FAIL: không thể đánh dấu stable khi tests/device_verification.json chưa xác nhận thiết bị")
        return 2

    write_build_info(version, prerelease, record, binary if binary.is_file() else None)

    # Checksums cover every release file except the checksum file itself.
    targets = [preview, source_zip, DIST_DIR / "BUILD-INFO.txt"]
    if binary.is_file():
        targets.append(binary)
    write_checksums(targets, DIST_DIR / "SHA256SUMS.txt")

    checksums = []
    for line in (DIST_DIR / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        checksums.append((name, digest))
    write_notes(DIST_DIR / "release-notes.md", version, prerelease, record, checksums)

    print(f"OK: packaged {version} ({'pre-release' if prerelease else 'stable'})")
    for path in sorted(DIST_DIR.iterdir()):
        if path.is_file():
            print(f"  {path.name:48} {path.stat().st_size:>9} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
