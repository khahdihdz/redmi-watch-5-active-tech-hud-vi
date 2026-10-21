#!/usr/bin/env python3
"""Build the real watch-face binary with the pinned Mi Create compiler.

The script never fabricates output: if the compiler is missing or fails, the
build fails. The output must pass scripts/verify_binary.py before it is copied
to dist/tech-hud-vi.bin.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DIST_DIR, FPRJ_PATH, ROOT, SRC_DIR, SRC_IMAGES, load_layout, sha256_file  # noqa: E402

import verify_binary  # noqa: E402


def run(command: list[str], what: str) -> subprocess.CompletedProcess:
    print(f"+ {what}: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result


def find_compiler(explicit: str | None) -> Path | None:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("WATCHFACE_COMPILER")
    if env:
        candidates.append(Path(env))
    candidates += [
        ROOT / "compiler" / "compile.exe",
        ROOT / "dist" / "compiler" / "compile.exe",
    ]
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 1_000_000:
            return candidate.resolve()
    return None


def compiler_command(compiler: Path) -> list[str]:
    if compiler.suffix.lower() == ".exe" and platform.system() != "Windows":
        wine = shutil.which("wine")
        if not wine:
            raise SystemExit("FAIL: compile.exe requires Windows or Wine; neither is available")
        return [wine, str(compiler)]
    return [str(compiler)]


def stage_project(stage: Path) -> tuple[Path, Path]:
    """Stage the project and create the `output` folder next to the .fprj.

    compile.exe resolves its internal paths (notably `output/<name>.info`)
    relative to the directory containing the .fprj, not to the process CWD,
    so that folder must exist before the compiler starts.
    """
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    shutil.copy2(FPRJ_PATH, stage / FPRJ_PATH.name)
    shutil.copytree(SRC_IMAGES, stage / "images")
    # Some compiler builds look for the preview next to the project as well.
    shutil.copy2(SRC_DIR / "preview.png", stage / "preview.png")
    shutil.copy2(SRC_DIR / "preview.png", stage / "images" / "preview.png")
    output_dir = stage / "output"
    output_dir.mkdir()
    return stage / FPRJ_PATH.name, output_dir


def is_face_binary(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < 40 * 1024:
            return False
        with path.open("rb") as fh:
            return fh.read(4) == b"\x5a\xa5\x34\x12"
    except OSError:
        return False


def find_compiled_binaries(*directories: Path) -> list[Path]:
    found: dict[Path, Path] = {}
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if is_face_binary(path):
                found[path.resolve()] = path
    return [found[key] for key in sorted(found)]


def write_build_info(info: dict) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIST_DIR / "BUILD-INFO.txt"
    lines = [
        "REDMI WATCH 5 ACTIVE — TECH HUD VI",
        "==================================",
        f"Phiên bản:            {info['version']}",
        f"Thiết bị:             {info['device']} (DeviceType {info['device_type']})",
        f"Độ phân giải:         {info['canvas']}",
        f"Định dạng:            Gen2 .bin (magic 5AA53412)",
        f"Thời điểm build (UTC):{info['built_at']}",
        f"Git commit:           {info['git_commit']}",
        f"Compiler:             {info['compiler_project']} @ {info['compiler_commit'][:12]}",
        f"Compiler SHA-256:     {info['compiler_sha256']}",
        f"Output SHA-256:       {info['output_sha256']}",
        f"Output size:          {info['output_size']} bytes",
        f"Kiểm tra cấu trúc:    {'ĐẠT' if info['verification']['ok'] else 'KHÔNG ĐẠT'}",
        f"Số resource:          {info['verification'].get('resource_entries', 'n/a')}",
        "",
        "Trạng thái kiểm thử:",
        "- Build và kiểm tra cấu trúc: tự động trong GitHub Actions.",
        "- Kiểm thử trên Redmi Watch 5 Active thật: CHƯA THỰC HIỆN tại thời điểm phát hành.",
        "- Vì vậy bản phát hành được đánh dấu pre-release cho tới khi có xác nhận trên thiết bị.",
        "",
        "Ghi chú:",
        "- Không có dữ liệu KM vì DeviceType 3651 không công bố source quãng đường.",
        "- Ảnh preview là số liệu minh họa, không phải dữ liệu cảm biến.",
        "- Compiler là công cụ bên thứ ba, không được phân phối lại trong repo này.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", help="path to compile.exe")
    parser.add_argument("--no-generate", action="store_true")
    parser.add_argument("--keep-stage", action="store_true")
    args = parser.parse_args()

    layout = load_layout()
    meta = layout["meta"]

    if not args.no_generate:
        for script in ("generate_assets.py", "validate_target.py", "validate_assets.py"):
            result = run([sys.executable, str(ROOT / "scripts" / script)], script)
            if result.returncode != 0:
                return result.returncode

    compiler = find_compiler(args.compiler)
    if compiler is None:
        print("FAIL: không tìm thấy compiler thực (compile.exe).")
        print("      Đặt compiler tại compiler/compile.exe hoặc đặt WATCHFACE_COMPILER.")
        print("      Không tạo file .bin giả khi thiếu compiler.")
        return 2

    expected_sha = json.loads((ROOT / "docs" / "compiler-pin.json").read_text(encoding="utf-8"))["sha256"]
    actual_sha = sha256_file(compiler)
    if actual_sha != expected_sha:
        print(f"FAIL: compiler SHA-256 không khớp pin.\n  expected {expected_sha}\n  actual   {actual_sha}")
        return 3
    print(f"OK: compiler pinned SHA-256 {actual_sha}")

    stage_root = Path(os.environ.get("WATCHFACE_BUILD_DIR", Path(tempfile.gettempdir()) / "tech-hud-build"))
    stage = stage_root / "project"
    fprj, output_dir = stage_project(stage)

    command = compiler_command(compiler) + [
        "-b",
        str(fprj),
        str(output_dir),
        "tech-hud-vi.bin",
        "1461256429",
    ]
    result = run(command, "compile watch face")
    if result.returncode != 0:
        print(f"FAIL: compiler exit code {result.returncode}")
        return 4

    produced = find_compiled_binaries(output_dir, stage)
    if not produced:
        print("FAIL: compiler exit 0 nhưng không tạo file output")
        for path in sorted(output_dir.rglob("*")):
            print(f"  output/: {path.relative_to(output_dir)}")
        for path in sorted(stage.rglob("*")):
            print(f"  project/: {path.relative_to(stage)}")
        return 5
    artifact = produced[0]
    print(f"OK: compiler tạo {artifact} ({artifact.stat().st_size} bytes)")
    if artifact.suffix.lower() != ".bin":
        renamed = output_dir / "tech-hud-vi.bin"
        artifact.replace(renamed)
        artifact = renamed
    if artifact.stat().st_size == 0:
        print("FAIL: compiler tạo file rỗng")
        return 6

    verification = verify_binary.verify(artifact, meta["title"])
    print(json.dumps(verification, indent=2, ensure_ascii=False))
    if not verification["ok"]:
        for problem in verification["problems"]:
            print(f"FAIL: {problem}")
        return 7

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    target = DIST_DIR / "tech-hud-vi.bin"
    shutil.copy2(artifact, target)

    pin = json.loads((ROOT / "docs" / "compiler-pin.json").read_text(encoding="utf-8"))
    info = {
        "version": meta["version"],
        "device": meta["device"],
        "device_type": meta["device_type"],
        "canvas": f"{meta['canvas']['w']}x{meta['canvas']['h']}",
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": os.environ.get("GITHUB_SHA", "local"),
        "compiler_project": pin["project"],
        "compiler_commit": pin["commit"],
        "compiler_sha256": actual_sha,
        "output_sha256": sha256_file(target),
        "output_size": target.stat().st_size,
        "verification": verification,
    }
    write_build_info(info)
    print(f"OK: wrote {target} ({target.stat().st_size} bytes, sha256 {info['output_sha256']})")

    if not args.keep_stage:
        shutil.rmtree(stage_root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
