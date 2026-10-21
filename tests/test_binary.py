import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
import verify_binary  # noqa: E402


def test_rejects_empty_file(tmp_path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    result = verify_binary.verify(path, "Tech HUD VI")
    assert result["ok"] is False
    assert any("too small" in problem for problem in result["problems"])


def test_rejects_renamed_png(tmp_path):
    path = tmp_path / "fake.bin"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 60000)
    result = verify_binary.verify(path, "Tech HUD VI")
    assert result["ok"] is False
    assert any("magic" in problem for problem in result["problems"])


def test_accepts_well_formed_fixture(tmp_path):
    """The fixture only exercises the parser; it is never shipped as a watch face."""
    size = 60000
    data = bytearray(size)
    data[0:4] = verify_binary.MAGIC
    struct.pack_into("<I", data, 4, verify_binary.VERSION)
    data[0x68:0x68 + len(b"Tech HUD VI")] = b"Tech HUD VI"
    table = 0x100
    for index in range(64):
        struct.pack_into("<IIII", data, table + index * 16, index, 0, 0xC20 + index * 16, 16)
    for offset in range(0xC20, size):
        data[offset] = (offset * 37 + 11) & 0xFF
    path = tmp_path / "fixture.bin"
    path.write_bytes(bytes(data))
    result = verify_binary.verify(path, "Tech HUD VI")
    assert result["ok"] is True, result
    assert result["resource_entries"] == 64


def test_checksum_matches_sha256sum(tmp_path):
    import hashlib

    path = tmp_path / "x.bin"
    path.write_bytes(b"abc")
    assert verify_binary.sha256(path) == hashlib.sha256(b"abc").hexdigest()
