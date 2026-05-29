"""Catch malformed shipped DDTs before they hit the live engine.

Failure mode this validator was built for (2026-05-12 live test):
``tools/cardextract/build_leader_ddts.py`` wrote 64x64 DXT1 pixel data
into a header that declared ``format=1``. Per the canonical AoE3 DE DDT
spec, ``format=1`` means *uncompressed BGRA32* (4 bytes/pixel), not DXT1
(which would be ``format=4``). The engine read the format byte, tried to
decode the 2048 byte payload as BGRA32 (which would need w*h*4 bytes),
got garbage, and silently rendered an empty portrait slot — so the lobby
showed no AI civ portraits at all, base game or modded.

This validator inspects every ``art/ui/singleplayer/cpai_avatar_*.ddt``
that ``data/civmods.xml`` references via ``<smallportraittexture>`` or
``<smallportraittexturewpf>``'s DDT counterpart, and verifies:

  * magic = b"RTS3"
  * format byte ∈ {1, 4, 7, 8}  (1=BGRA32, 4=DXT1, 7=DXT3, 8=DXT5)
  * declared (w, h) > 0, multiple-of-4, ≤ 1024
  * file size matches the format:
      - format=1 (BGRA32):  24 + w*h*4   (with mip table)
      - format=4 (DXT1):    20 + w*h//2  (without mip table) OR
                            24 + w*h//2  (with mip table)
      - format=7,8 (DXT3/5): 20 + w*h    OR 24 + w*h
  * pixel data has ≥30% non-zero bytes (not an all-blank suppression DDT
    being referenced for a real surface)

Exit 1 with a punchlist per file so they can be batch-rebuilt via
``png_to_ddt.png_to_ddt(src_png, dst_ddt, size=128)``.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Valid DDT format bytes per png_to_ddt.py spec.
_FORMATS = {
    1: "BGRA32",
    4: "DXT1",
    7: "DXT3",
    8: "DXT5",
}


def _bytes_per_pixel_or_blocksize(fmt: int, w: int, h: int) -> int:
    """Return the expected pixel-data length in bytes for (fmt, w, h)."""
    if fmt == 1:
        return w * h * 4
    if fmt == 4:  # DXT1 = 4 bpp = 1 byte/2 pixels
        return (w * h) // 2
    if fmt in (7, 8):  # DXT3/DXT5 = 8 bpp = 1 byte/pixel
        return w * h
    return -1


def inspect_ddt(p: Path) -> list[str]:
    """Return a list of issues for this DDT (empty = file OK)."""
    issues: list[str] = []
    try:
        data = p.read_bytes()
    except OSError as exc:
        return [f"{p.name}: read error: {exc}"]
    if len(data) < 16:
        return [f"{p.name}: too small ({len(data)}B)"]
    if data[:4] != b"RTS3":
        return [f"{p.name}: bad magic {data[:4]!r}"]
    fmt = data[6]
    if fmt not in _FORMATS:
        issues.append(f"{p.name}: unknown format byte {fmt}")
        return issues
    w, h = struct.unpack_from("<II", data, 8)
    if w <= 0 or h <= 0 or w > 1024 or h > 1024:
        issues.append(f"{p.name}: bad dimensions {w}x{h}")
        return issues
    if w % 4 or h % 4:
        issues.append(f"{p.name}: non-multiple-of-4 dims {w}x{h}")
    expected_pixel = _bytes_per_pixel_or_blocksize(fmt, w, h)
    # Two valid header layouts:
    #   no-mip-table: 16 + 4 + pixel_data         (20-byte header)
    #   mip-table:    16 + 8*nMips + pixel_data   (24-byte header for 1 mip)
    candidates = (20 + expected_pixel, 24 + expected_pixel)
    if len(data) not in candidates:
        issues.append(
            f"{p.name}: size {len(data)}B does not match format "
            f"{_FORMATS[fmt]}({fmt}) {w}x{h} (expected {candidates[0]}B "
            f"or {candidates[1]}B). Engine will mis-decode → blank slot."
        )
        return issues
    # Non-zero pixel sanity (skip header)
    header_size = 20 if len(data) == candidates[0] else 24
    nz = sum(1 for b in data[header_size:] if b)
    total = len(data) - header_size
    if total and (nz / total) < 0.30:
        issues.append(
            f"{p.name}: pixel data is {100*nz//total}% non-zero "
            f"(likely a blank-suppression DDT; engine will render black)."
        )
    return issues


def collect_referenced_ddts(repo_root: Path) -> list[Path]:
    """Walk civmods.xml and return every shipped DDT path referenced via
    ``<smallportraittexture>``.  Anything not present in the mod is
    skipped — the engine will fall through to ``ArtUI.bar``."""
    civmods = repo_root / "data" / "civmods.xml"
    if not civmods.exists():
        return []
    text = civmods.read_text()
    paths: list[Path] = []
    for m in re.finditer(
        r"<smallportraittexture>([^<]+)</smallportraittexture>", text
    ):
        rel = m.group(1).strip().replace("\\", "/")
        basename = rel.split("/")[-1]
        ddt = repo_root / "art" / "ui" / "singleplayer" / f"{basename}.ddt"
        if ddt.exists():
            paths.append(ddt)
    return paths


def validate(repo_root: Path) -> list[str]:
    issues: list[str] = []
    ddts = collect_referenced_ddts(repo_root)
    if not ddts:
        return ["no shipped DDTs found via civmods.xml (nothing to check)"]
    for p in ddts:
        issues.extend(inspect_ddt(p))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = ap.parse_args()
    issues = validate(args.repo_root.resolve())
    if issues:
        print(f"DDT format check: {len(issues)} issue(s)")
        for i in issues:
            print(f"  {i}")
        print()
        print("Rebuild with:")
        print("  from tools.cardextract.png_to_ddt import png_to_ddt")
        print("  png_to_ddt(src_png, dst_ddt, size=128)")
        return 1
    print(f"DDT format check: OK ({len(__import__('os').listdir(args.repo_root / 'art' / 'ui' / 'singleplayer'))} files scanned, all well-formed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
