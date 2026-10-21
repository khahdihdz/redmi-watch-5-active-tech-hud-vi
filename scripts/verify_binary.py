#!/usr/bin/env python3
"""Structural verification of a compiled Gen2 watch-face binary.

This is not a format reimplementation. It checks the invariants that the
Redmi Watch 5 Active firmware format exposes publicly in research:
  * magic 5A A5 34 12
  * version 0x00010000
  * a monotonic 16-byte resource table whose offsets stay inside the file
  * the compiled face title is present
Any failure makes the build/release fail.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path

MAGIC = b"\x5a\xa5\x34\x12"
VERSION = 0x00010000
TABLE_CANDIDATES = (0x100, 0x1C0)
MIN_SIZE = 40 * 1024
MAX_SIZE = 8 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_table(data: bytes, start: int) -> list[tuple[int, int, int, int]]:
    entries: list[tuple[int, int, int, int]] = []
    offset = start
    expected_type = 0
    last_offset = 0
    while offset + 16 <= len(data):
        rtype, flags, roff, rsize = struct.unpack_from("<IIII", data, offset)
        if rtype == 0 and flags == 0 and roff == 0 and rsize == 0:
            break
        if rtype != expected_type:
            break
        if roff < 0x200 or roff < last_offset or rsize <= 0 or roff + rsize > len(data):
            break
        entries.append((rtype, flags, roff, rsize))
        last_offset = roff
        expected_type += 1
        offset += 16
    return entries


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def verify(path: Path, expect_title: str) -> dict:
    data = path.read_bytes()
    problems: list[str] = []
    if len(data) < MIN_SIZE:
        problems.append(f"file too small: {len(data)} bytes")
    if len(data) > MAX_SIZE:
        problems.append(f"file too large: {len(data)} bytes")
    if data[:4] != MAGIC:
        problems.append(f"bad magic: {data[:4].hex()}")
    version = struct.unpack_from("<I", data, 4)[0] if len(data) >= 8 else 0
    if version != VERSION:
        problems.append(f"unexpected version: 0x{version:08x}")

    best_start, best_entries = 0, []
    for start in TABLE_CANDIDATES:
        entries = parse_table(data, start)
        if len(entries) > len(best_entries):
            best_start, best_entries = start, entries
    if len(best_entries) < 8:
        problems.append(f"resource table not found (best={len(best_entries)} entries)")
    if len(best_entries) > 512:
        problems.append(f"resource table implausible: {len(best_entries)} entries")

    body = data[best_start:] if best_start else data
    if entropy(body) < 3.0:
        problems.append(f"payload entropy too low: {entropy(body):.2f}")
    if len(body.strip(b"\x00")) < MIN_SIZE // 2:
        problems.append("payload is mostly zero padding")

    title_bytes = expect_title.encode("utf-8")
    title_found = title_bytes in data
    if not title_found:
        problems.append(f"watch-face title {expect_title!r} not present")

    if problems:
        return {"ok": False, "problems": problems, "sha256": sha256(path), "size": len(data)}

    return {
        "ok": True,
        "problems": [],
        "sha256": sha256(path),
        "size": len(data),
        "magic": data[:4].hex(),
        "version": f"0x{version:08x}",
        "resource_table_offset": f"0x{best_start:04x}",
        "resource_entries": len(best_entries),
        "table_first_data": f"0x{best_entries[0][2]:06x}",
        "table_last_end": f"0x{best_entries[-1][2] + best_entries[-1][3]:06x}",
        "title_found": title_found,
        "entropy": round(entropy(body), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--expect-title", default="Tech HUD VI")
    parser.add_argument("--json-out")
    args = parser.parse_args()
    path = Path(args.binary)
    if not path.is_file():
        print(f"FAIL: missing {path}")
        return 1
    result = verify(path, args.expect_title)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not result["ok"]:
        for problem in result["problems"]:
            print(f"FAIL: {problem}")
        return 1
    print("OK: binary structure verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
