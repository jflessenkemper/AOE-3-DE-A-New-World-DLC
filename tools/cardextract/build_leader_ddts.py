"""Build leader-specific .ddt portraits from source PNGs.

DEPRECATED — DO NOT USE. See ``png_to_ddt.py`` instead.

Bug: this script writes 64x64 DXT1 pixel data into a header that claims
``format=1``. Per the canonical AoE3 DE DDT spec (see ``png_to_ddt.py``),
``format=1`` means *uncompressed BGRA32*, NOT DXT1 (which would be format=4).
The engine reads the format byte, tries to decode 2048 bytes as BGRA32,
gets garbage, and silently renders an empty portrait slot. The 2026-05-12
live test confirmed the failure mode: lobby AI rows had no portrait at all
when ``<smallportraittexture>`` pointed at a leader-specific DDT built here.

Use this instead:

    from png_to_ddt import png_to_ddt
    png_to_ddt(src_png, dst_ddt, size=128)

which produces a 128x128 BGRA32 DDT with the correct 24-byte header
(matching the format the engine actually accepts, and matching the
working ANW custom-civ DDTs at 65,560 bytes).

Reads <icon> from every game/ai/*.personality and writes a 64x64 DXT1 .ddt
to art/ui/singleplayer/ using the same base name. The mod loader picks these
up to override base-game civ-level portraits in chat bubbles, scoreboards,
and lobby slots.

DDT format (AoE3 DE RTS3 variant):
  0-3:  magic b"RTS3"
  4:    usage byte (0 = AlbedoMap)
  5:    alpha byte (0 = none)
  6:    format byte (1 = DXT1)
  7:    mip count (1)
  8-11: width (u32 LE)
  12-15: height (u32 LE)
  16-19: first-mip size (u32 LE)
  20-...: DXT1 blocks (8 bytes each, 4x4 pixels)

DXT1 block (8 bytes):
  0-1: color0 (u16 LE, RGB565)
  2-3: color1 (u16 LE, RGB565)
  4-7: indices (u32 LE; 16 x 2-bit, 0..3 selecting between 4 interpolated colors)

When color0 > color1: 4-color mode (c0, c1, 2/3*c0+1/3*c1, 1/3*c0+2/3*c1).
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
ART_DIR = REPO / "art" / "ui" / "singleplayer"
ART_DIR.mkdir(parents=True, exist_ok=True)


def rgb_to_565(r: int, g: int, b: int) -> int:
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def c565_to_rgb(c: int) -> tuple[int, int, int]:
    r = ((c >> 11) & 0x1F) << 3
    g = ((c >> 5) & 0x3F) << 2
    b = (c & 0x1F) << 3
    return (r | (r >> 5), g | (g >> 6), b | (b >> 5))


def encode_block(block: np.ndarray) -> bytes:
    """Encode a 4x4x3 RGB block to 8-byte DXT1.

    Strategy: pick endpoints from min/max channel-corner pixels; fall back to
    per-channel min/max. Use 4-color interpolation (color0 > color1 mode).
    """
    pixels = block.reshape(-1, 3).astype(np.int32)  # (16, 3)

    # Endpoint selection: use the two pixels furthest apart (PCA-lite via L2
    # range across each channel). For speed, take per-channel min/max.
    cmin = pixels.min(axis=0)
    cmax = pixels.max(axis=0)

    # If degenerate (all pixels same), single color block.
    if np.array_equal(cmin, cmax):
        c = rgb_to_565(int(cmin[0]), int(cmin[1]), int(cmin[2]))
        # Force 4-color mode by making color0 != color1; or use 3-color
        # transparent mode by setting both equal — but we want opaque.
        # Set color0 = c, color1 = c-1 to force c0 > c1 if possible.
        c0 = c
        c1 = c if c == 0 else c - 1
        if c0 < c1:
            c0, c1 = c1, c0
        return struct.pack("<HHI", c0, c1, 0)

    c0_565 = rgb_to_565(int(cmax[0]), int(cmax[1]), int(cmax[2]))
    c1_565 = rgb_to_565(int(cmin[0]), int(cmin[1]), int(cmin[2]))
    # Ensure 4-color mode (c0 > c1)
    if c0_565 <= c1_565:
        c0_565, c1_565 = (c1_565, c0_565) if c0_565 != c1_565 else (c0_565 + 1, c1_565)

    # Build the 4-color palette (in 8-bit RGB)
    p0 = np.array(c565_to_rgb(c0_565), dtype=np.int32)
    p1 = np.array(c565_to_rgb(c1_565), dtype=np.int32)
    p2 = (2 * p0 + p1) // 3
    p3 = (p0 + 2 * p1) // 3
    palette = np.stack([p0, p1, p2, p3])  # (4, 3)

    # For each pixel pick nearest palette entry (squared-distance)
    diffs = pixels[:, None, :] - palette[None, :, :]  # (16, 4, 3)
    dists = np.sum(diffs * diffs, axis=2)  # (16, 4)
    indices = np.argmin(dists, axis=1)  # (16,)

    # Pack 16 2-bit indices into u32 (LSB = pixel 0)
    packed = 0
    for i, idx in enumerate(indices):
        packed |= (int(idx) & 3) << (2 * i)

    return struct.pack("<HHI", c0_565, c1_565, packed)


def png_to_ddt(png_path: Path, size: int = 64) -> bytes:
    img = Image.open(png_path).convert("RGB").resize((size, size), Image.LANCZOS)
    arr = np.array(img, dtype=np.uint8)  # (H, W, 3)

    blocks: list[bytes] = []
    for by in range(0, size, 4):
        for bx in range(0, size, 4):
            blocks.append(encode_block(arr[by:by + 4, bx:bx + 4]))
    pixel_data = b"".join(blocks)

    header = bytearray(16)
    header[0:4] = b"RTS3"
    header[4] = 0  # usage = AlbedoMap
    header[5] = 0  # alpha = none
    header[6] = 1  # format = DXT1
    header[7] = 1  # mip count
    struct.pack_into("<I", header, 8, size)
    struct.pack_into("<I", header, 12, size)

    return bytes(header) + struct.pack("<I", len(pixel_data)) + pixel_data


# Map personality forcedciv -> base-game civ-level .ddt name (lowercase token
# the base game uses in art/ui/singleplayer/cpai_avatar_<civ>.ddt).
FORCEDCIV_TO_CIV_DDT = {
    "British": "british", "French": "french", "Spanish": "spanish",
    "Portuguese": "portuguese", "Dutch": "dutch", "Germans": "germans",
    "Russians": "russians", "Ottomans": "ottomans", "DESwedish": "swedes",
    "DEItalians": "italians", "DEMaltese": "maltese", "DEMexicans": "mexicans",
    "Chinese": "chinese", "Japanese": "japanese", "Indians": "indians",
    "XPAztec": "aztecs", "DEInca": "inca", "XPIroquois": "haudenosaunee",
    "XPSioux": "lakota", "DEHausa": "hausa", "DEEthiopians": "ethiopians",
    "DEAmericans": "united_states",
}


def collect_icon_refs() -> dict[str, tuple[Path, str | None]]:
    """Map basename -> (source PNG path, civ-level ddt token or None)."""
    icons: dict[str, tuple[Path, str | None]] = {}
    for pf in sorted((REPO / "game" / "ai").glob("*.personality")):
        text = pf.read_text()
        m = re.search(r"<icon>([^<]+)</icon>", text)
        fc = re.search(r"<forcedciv>([^<]+)</forcedciv>", text)
        if not m:
            continue
        rel = m.group(1).strip()
        png = REPO / rel
        if not png.exists():
            print(f"  MISS {pf.name}: {rel} not on disk", file=sys.stderr)
            continue
        base = png.stem
        civ_token = FORCEDCIV_TO_CIV_DDT.get(fc.group(1)) if fc else None
        icons[base] = (png, civ_token)
    return icons


def main():
    icons = collect_icon_refs()
    print(f"Building leader .ddt portraits (64x64 DXT1)…")
    n_leader = 0
    civ_overrides: dict[str, Path] = {}  # civ_token -> source png (one per civ)
    for base, (png, civ_token) in sorted(icons.items()):
        try:
            blob = png_to_ddt(png)
        except Exception as exc:
            print(f"  FAIL {base}: {exc}", file=sys.stderr)
            continue
        dst = ART_DIR / f"{base}.ddt"
        dst.write_bytes(blob)
        n_leader += 1
        if civ_token and civ_token not in civ_overrides:
            civ_overrides[civ_token] = png
    print(f"  Leader-level: {n_leader} written")

    # Also write civ-level overrides (cpai_avatar_<civ>.ddt) so chat bubbles
    # / lobby portraits show real leader imagery instead of base-game default.
    print(f"Building civ-level overrides ({len(civ_overrides)})…")
    for civ_token, png in sorted(civ_overrides.items()):
        blob = png_to_ddt(png)
        dst = ART_DIR / f"cpai_avatar_{civ_token}.ddt"
        dst.write_bytes(blob)
    print(f"  Civ-level: {len(civ_overrides)} written from flagship personalities.")


if __name__ == "__main__":
    main()
