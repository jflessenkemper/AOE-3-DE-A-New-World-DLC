"""AoE3 DE l33t/L33t-zip codec — used by .age3Yrec replays and .age3Yscn scenarios.

Format
======

::

    offset 0:  4 bytes — ASCII 'l33t' (or 'L33t') magic
    offset 4:  uint32 little-endian — decompressed size
    offset 8:  zlib-deflate stream

That's it. The inner stream is plain zlib.

Both replay (.age3Yrec) and scenario (.age3Yscn) files share this
wrapper.  Reverse-engineered from samples on 2026-05-09.
"""
from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path


_MAGIC_LOWER = b"l33t"
_MAGIC_UPPER = b"L33t"


def is_l33t(data: bytes) -> bool:
    return len(data) >= 8 and data[:4] in (_MAGIC_LOWER, _MAGIC_UPPER)


def decompress(data: bytes) -> bytes:
    """Decompress an l33t blob. Returns the inner bytes."""
    if not is_l33t(data):
        raise ValueError(f"not an l33t blob (magic={data[:4]!r})")
    expected_size = struct.unpack("<I", data[4:8])[0]
    decompressed = zlib.decompress(data[8:])
    if len(decompressed) != expected_size:
        raise ValueError(
            f"size mismatch: got {len(decompressed)} expected {expected_size}"
        )
    return decompressed


def compress(data: bytes, *, magic: bytes = _MAGIC_LOWER) -> bytes:
    """Compress to an l33t blob. Returns wrapped bytes."""
    z = zlib.compress(data)
    return magic + struct.pack("<I", len(data)) + z


def decompress_file(path: Path) -> bytes:
    return decompress(Path(path).read_bytes())


def compress_to_file(path: Path, data: bytes, *,
                     magic: bytes = _MAGIC_LOWER) -> None:
    Path(path).write_bytes(compress(data, magic=magic))
