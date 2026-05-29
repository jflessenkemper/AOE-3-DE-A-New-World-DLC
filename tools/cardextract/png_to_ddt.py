"""PNG → DDT converter (uncompressed BGRA32 format).

AoE3 DDT format (verified from extracted samples + eBaeza/Resource-Manager source):

    Offset  Size  Field
    0       4     'RTS3' magic
    4       1     usage (0 = standard texture)
    5       1     alpha (1 = has alpha)
    6       1     format (1 = uncompressed BGRA32, 4 = DXT1, 8 = DXT3)
    7       1     mip levels (1 = single image, no mipmap chain)
    8       4     width (uint32 LE)
    12      4     height (uint32 LE)
    16+     8 per mip:
                  4: data offset
                  4: data size
    after:  pixel data (BGRA, row-major, top-down)

Uses format=1 (uncompressed BGRA32) — simplest and works for small UI textures
like leader avatars. Engine accepts. No DXT compression library needed.

Usage::

    from tools.cardextract.png_to_ddt import png_to_ddt
    png_to_ddt(Path("avatar.png"), Path("avatar.ddt"))
"""
from __future__ import annotations

import struct
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


def png_to_ddt(src: Path, dst: Path, *,
               size: int | None = None) -> None:
    """Convert a PNG (or any PIL-supported image) to a DDT file.

    Args:
        src: source image path
        dst: target DDT path
        size: if set, resize to (size, size). If None, keep original.
              Engine prefers power-of-two; default 128 if not power-of-two.
    """
    if Image is None:
        raise RuntimeError("PIL not installed")
    img = Image.open(src).convert("RGBA")
    w, h = img.size

    # Engine requires power-of-two and multiple-of-4 sizes. Resize if needed.
    if size is not None:
        target = size
    else:
        # Find nearest power-of-2 ≥ max(w, h), clamped to [64, 256]
        m = max(w, h)
        target = 1
        while target < m:
            target *= 2
        target = max(64, min(256, target))
    if (w, h) != (target, target):
        img = img.resize((target, target), Image.Resampling.LANCZOS)
        w = h = target

    # PIL gives RGBA; engine expects BGRA. Swap channels.
    pixels = bytearray(img.tobytes())
    for i in range(0, len(pixels), 4):
        pixels[i], pixels[i + 2] = pixels[i + 2], pixels[i]  # R↔B

    # Build header
    HEADER_SIZE = 16  # magic+flags+w+h
    MIP_ENTRY_SIZE = 8  # offset+size
    n_mips = 1
    pixel_offset = HEADER_SIZE + (MIP_ENTRY_SIZE * n_mips)
    pixel_size = len(pixels)

    header = b"RTS3"
    header += struct.pack("<BBBB",
                          0,   # usage
                          1,   # alpha
                          1,   # format=1 (uncompressed BGRA32)
                          n_mips,
                          )
    header += struct.pack("<II", w, h)
    # Mip table (just one entry)
    header += struct.pack("<II", pixel_offset, pixel_size)

    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "wb") as f:
        f.write(header)
        f.write(pixels)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--size", type=int, default=None)
    args = ap.parse_args()
    png_to_ddt(args.src, args.dst, size=args.size)
    print(f"Wrote {args.dst} ({args.dst.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
