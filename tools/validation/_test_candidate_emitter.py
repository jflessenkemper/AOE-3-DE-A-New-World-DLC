#!/usr/bin/env python3
"""Generate candidate passthrough scenarios for engine acceptance testing.

Each candidate explores ONE hypothesis about why the engine rejects our
passthrough output. All candidates have an identical decompressed body
(byte-for-byte == LL source body); they differ only in the container
encoding.

Outputs go to ``artifacts/emitted_scenarios/_test_<descriptor>.age3Yscn``.
The user installs each and reports which (if any) the engine accepts.
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.validation import validate_scenario_binary as v  # noqa: E402

# 2026-05-11: was Scenario/legendary-leaders-ai.age3Yscn; the recovered
# binary now lives at _test_template.age3Yscn (same md5 504465a9…). The
# canonical AI-testing scenario is Scenario/ANEWWORLD.age3Yscn, but the
# byte-level emitter tests are tightly coupled to this specific template's
# zlib params, so we kept it for test stability.
LL_PATH = REPO / "Scenario" / "_test_template.age3Yscn"
OUT_DIR = REPO / "artifacts" / "emitted_scenarios"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _wrap(body: bytes, compressed: bytes, trailer: bytes) -> bytes:
    """Build l33t/zlib container from arbitrary compressed stream + trailer."""
    out = bytearray()
    out += b"l33t"
    out += struct.pack("<I", len(body))
    out += compressed
    out += trailer
    return bytes(out)


def _compress_with(body: bytes, level: int, strategy: int = zlib.Z_DEFAULT_STRATEGY,
                   memLevel: int = 8) -> bytes:
    c = zlib.compressobj(level=level, method=zlib.DEFLATED, wbits=15,
                         memLevel=memLevel, strategy=strategy)
    return c.compress(body) + c.flush()


def main() -> int:
    sf = v.parse(LL_PATH)
    body = sf.body
    original_trailer = sf.trailer  # b'\xb7\x38\x33\x81'
    written = []

    # Hypothesis A: Original LL trailer + level-9 compression.
    #   Profile-dir ANEWWORLD used 78da (level 9). Possibly the engine
    #   accepts L9 streams differently. Pair with original trailer.
    cz = _compress_with(body, level=9)
    candidate = _wrap(body, cz, original_trailer)
    p = OUT_DIR / "_test_A_l9_origtrailer.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis B: level 9 + NO trailer (mimic ANEWWORLD profile file exactly)
    candidate = _wrap(body, cz, b"")
    p = OUT_DIR / "_test_B_l9_notrailer.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis C: level 6 (matches LL header) with trailer = adler32 of body LE
    # (one of the few values the engine could synthesise from body alone)
    cz6 = _compress_with(body, level=6)
    al_le = struct.pack("<I", zlib.adler32(body) & 0xffffffff)
    candidate = _wrap(body, cz6, al_le)
    p = OUT_DIR / "_test_C_l6_adler32_le.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis D: level 6, trailer = crc32 of body LE
    crc_le = struct.pack("<I", zlib.crc32(body) & 0xffffffff)
    candidate = _wrap(body, cz6, crc_le)
    p = OUT_DIR / "_test_D_l6_crc32_le.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis E: level 6, trailer = crc32 of compressed stream LE
    crc_z_le = struct.pack("<I", zlib.crc32(cz6) & 0xffffffff)
    candidate = _wrap(body, cz6, crc_z_le)
    p = OUT_DIR / "_test_E_l6_crc32_compressed_le.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis F: level 6 with HUFFMAN_ONLY strategy (sometimes engine uses
    # this for certain blocks)
    czh = _compress_with(body, level=6, strategy=zlib.Z_HUFFMAN_ONLY)
    candidate = _wrap(body, czh, original_trailer)
    p = OUT_DIR / "_test_F_l6_huffman.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis G: Append the whole 8-byte file header (l33t + outer_size)
    # AGAIN as the "trailer" -- some engines write a duplicate header.
    duplicate_hdr = b"l33t" + struct.pack("<I", len(body))
    candidate = _wrap(body, cz6, duplicate_hdr)
    p = OUT_DIR / "_test_G_l6_dup_header_trailer.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis H: trailer = u32 LE of FILE size (some games store final size
    # at end as a sentinel)
    # Compute compressed size first to know file size.
    file_no_trailer_size = 8 + len(cz6)
    fz_le = struct.pack("<I", file_no_trailer_size + 4)
    candidate = _wrap(body, cz6, fz_le)
    p = OUT_DIR / "_test_H_l6_filesize_trailer.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis I: trailer = the FOUR LITERAL ZERO BYTES.
    # If the engine just expects "any 4 bytes are present after the stream"
    # but our previous attempts had specific values, ALL ZEROES might be a
    # valid sentinel.
    candidate = _wrap(body, cz6, b"\x00\x00\x00\x00")
    p = OUT_DIR / "_test_I_l6_zero_trailer.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis J: level 6, original trailer, but use raw deflate (no zlib
    # wrapper) -- low probability, but tests whether the engine bypasses the
    # zlib header. (We retain the file's first 2 bytes as a fake zlib hdr.)
    # SKIP: this would break the parser entirely; not worth a slot.

    # Hypothesis K: level 6 with strategy=Z_FILTERED
    czf = _compress_with(body, level=6, strategy=zlib.Z_FILTERED)
    candidate = _wrap(body, czf, original_trailer)
    p = OUT_DIR / "_test_K_l6_filtered.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis L: level 6, memLevel=9 (max). Default in zlib C is memLevel=8;
    # Python's zlib.compress also uses 8. The engine might use 9.
    czm = _compress_with(body, level=6, memLevel=9)
    candidate = _wrap(body, czm, original_trailer)
    p = OUT_DIR / "_test_L_l6_mem9.age3Yscn"
    p.write_bytes(candidate)
    written.append(p)

    # Hypothesis M: zlib raw passthrough -- copy the LL file's zlib stream
    # bytes verbatim (since body is identical, it's the same stream). This is
    # a sanity check: a literal byte-clone of LL with NO modifications.
    # The result MUST be identical to LL itself; if the engine accepts LL but
    # rejects this, something is corrupting the file system path.
    raw_clone = LL_PATH.read_bytes()
    p = OUT_DIR / "_test_M_byte_clone_of_LL.age3Yscn"
    p.write_bytes(raw_clone)
    written.append(p)

    # Validate every candidate parses.
    print(f"Generated {len(written)} candidates:\n")
    for path in written:
        sf = v.parse(path)
        bodies_identical = (sf.body == body)
        issues = v.validate(sf)
        ok = "OK" if not issues and bodies_identical else "PROBLEM"
        print(f"  {ok}  {path.name}  fsz={sf.file_size:7d} "
              f"trlr={sf.trailer.hex() or '(none)':10s} "
              f"zhdr={sf.zlib_stream[:2].hex()} body_match={bodies_identical}")
        if issues:
            for x in issues:
                print(f"      issue: {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
