#!/usr/bin/env python3
"""
AoE3 DE .age3Yscn trailer reverse-engineering script.
Tests all novel candidates (prior session already ruled out xxh32/64, mmh3, djb2,
sdbm, fnv1/a, jenkins, ELF, CRC32 std polys, MD5/SHA1/SHA256 lo/hi 32 bits).
"""

import zlib
import hashlib
import struct
import binascii
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# File metadata
# ---------------------------------------------------------------------------
FILES = [
    {
        "label": "Bombard_Brawl",
        "path": "/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn",
        "outer": 369942,
        "body_size": 8275691,
        "trailer_hex": "45069598",
        "status": "LOADS",
    },
    {
        "label": "_test_template",
        "path": "/var/home/jflessenkemper/AOE-3-DE-A-New-World/Scenario/_test_template.age3Yscn",
        "outer": 160246,
        "body_size": 2636786,
        "trailer_hex": "b7383381",
        "status": "REJECTED",
    },
    {
        "label": "QuickSavegame",
        "path": "/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/QuickSavegame.age3Yscn",
        "outer": 150423,
        "body_size": 2749022,
        "trailer_hex": "16558739",
        "status": "LOADS",
    },
    {
        "label": "QuickSavegame.bak",
        "path": "/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/QuickSavegame.bak",
        "outer": 150425,
        "body_size": 2749022,
        "trailer_hex": "b3a30be2",
        "status": "UNKNOWN",
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    return Path(path).read_bytes()

def trailer_expected(f):
    return bytes.fromhex(f["trailer_hex"])

def u32_le(b):
    return struct.unpack_from("<I", b)[0]

def u32_be(b):
    return struct.unpack_from(">I", b)[0]

def fmt_hex(val_int):
    return f"{val_int:08x}"

def crc32_zlib(data):
    return zlib.crc32(data) & 0xFFFFFFFF

# CRC32/BZIP2 (polynomial 0x04C11DB7, same as ISO 3309 but reflected = 0xEDB88320)
# Actually zlib CRC32 IS 0xEDB88320. BZIP2 uses same polynomial.
# The true "BZIP2" CRC32 is the same table but with different init/finalisation.
# We implement it as CRC32 with no pre/post inversion (init=0, no final XOR).
_CRC32_TABLE = None
def _build_crc32_table():
    global _CRC32_TABLE
    poly = 0xEDB88320
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            if c & 1:
                c = (c >> 1) ^ poly
            else:
                c >>= 1
        table.append(c)
    _CRC32_TABLE = table

def crc32_bzip2_variant(data, init=0xFFFFFFFF, final_xor=0xFFFFFFFF):
    """CRC32 with configurable init and final XOR (same poly as zlib but different init)."""
    if _CRC32_TABLE is None:
        _build_crc32_table()
    crc = init
    for b in data:
        crc = (crc >> 8) ^ _CRC32_TABLE[(crc ^ b) & 0xFF]
    return (crc ^ final_xor) & 0xFFFFFFFF

def adler32(data):
    return zlib.adler32(data) & 0xFFFFFFFF

def xor_fold_32(data):
    """XOR all bytes in 4-byte chunks."""
    val = 0
    for i in range(0, len(data) - (len(data) % 4), 4):
        val ^= struct.unpack_from("<I", data, i)[0]
    # handle remainder
    rem = len(data) % 4
    if rem:
        tail = data[len(data)-rem:] + b'\x00' * (4 - rem)
        val ^= struct.unpack_from("<I", tail)[0]
    return val & 0xFFFFFFFF

def sum32(data):
    """Sum all bytes mod 2^32."""
    s = 0
    for b in data:
        s += b
    return s & 0xFFFFFFFF

# ---------------------------------------------------------------------------
# ESH hash (Ensemble Studios Hash) - commonly found in AoE series
# This is a variant of the DJB2 / polynomial hash
# ---------------------------------------------------------------------------
def esh_hash(data):
    """Ensemble Studios hash as seen in AoE/AoE2/AoE3 source leaks."""
    h = 0
    for b in data:
        h = ((h << 5) + h + b) & 0xFFFFFFFF  # h*33 + b
    return h

def esh_hash_init1(data):
    """ESH variant with init=1."""
    h = 1
    for b in data:
        h = ((h << 5) + h + b) & 0xFFFFFFFF
    return h

def bernstein_hash(data):
    """Bernstein hash (DJB2 variant)."""
    h = 5381
    for b in data:
        h = (((h << 5) + h) ^ b) & 0xFFFFFFFF
    return h

# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyse():
    print("Loading files and decompressing bodies...")
    loaded = []
    for f in FILES:
        raw = read_file(f["path"])
        assert len(raw) == f["outer"], f"Size mismatch for {f['label']}: got {len(raw)}"

        # File structure:
        # bytes 0..3  : magic / version header (u32 LE)
        # bytes 4..7  : decompressed body size (u32 LE)
        # bytes 8..N-4: zlib compressed stream
        # bytes N-4..N: 4-byte trailer

        trailer_raw = raw[-4:]
        trailer_int = u32_le(trailer_raw)

        # The compressed stream is everything between the 8-byte header and the 4-byte trailer
        compressed = raw[8:-4]
        body = zlib.decompress(compressed)
        assert len(body) == f["body_size"], f"Decomp size mismatch for {f['label']}: got {len(body)}"

        # Also capture zlib stream's embedded adler32 (last 4 bytes of zlib stream)
        # In zlib format, the stream ends with a 4-byte Adler-32 checksum (big-endian)
        zlib_adler = u32_be(compressed[-4:])

        # bytes 4..7 of file = stored decompressed size (little-endian)
        stored_size = u32_le(raw[4:8])

        loaded.append({
            **f,
            "raw": raw,
            "body": body,
            "compressed": compressed,
            "trailer_int": trailer_int,
            "expected_int": int(f["trailer_hex"], 16),
            "zlib_adler": zlib_adler,
            "stored_size": stored_size,
        })
        print(f"  {f['label']}: body={len(body)} bytes, trailer={f['trailer_hex']}, zlib_adler={zlib_adler:08x}")

    print()

    # -----------------------------------------------------------------------
    # Define all candidates
    # -----------------------------------------------------------------------
    results = {}

    def test(name, fn):
        row = []
        for d in loaded:
            computed = fn(d)
            match = (computed == d["expected_int"])
            row.append((computed, match))
        results[name] = row
        matches = sum(1 for _, m in row if m)
        stars = "*" * matches
        print(f"  [{stars:<4}] {name}: " + "  ".join(f"{c:08x}{'✓' if m else '✗'}" for c, m in row))
        return matches

    print("=== TESTING CANDIDATES ===")
    print(f"{'':6} Labels: " + "  ".join(d["label"] for d in loaded))
    print(f"{'':6} Expect: " + "  ".join(d["trailer_hex"] for d in loaded))
    print()

    # --- Candidate 1: CRC32 of entire file minus trailer (bytes 0..N-4) ---
    test("crc32_file_minus_trailer_zlib",
         lambda d: crc32_zlib(d["raw"][:-4]))
    test("crc32_file_minus_trailer_bzip2",
         lambda d: crc32_bzip2_variant(d["raw"][:-4]))
    test("crc32_file_minus_trailer_init0",
         lambda d: crc32_bzip2_variant(d["raw"][:-4], init=0, final_xor=0))

    # --- Candidate 2: CRC32 of zlib stream only (bytes 8..N-4) ---
    test("crc32_zlib_stream_only_zlib",
         lambda d: crc32_zlib(d["compressed"]))
    test("crc32_zlib_stream_only_bzip2",
         lambda d: crc32_bzip2_variant(d["compressed"]))

    # --- Candidate 3: CRC32 of compressed body incl. outer u32 (bytes 4..N-4) ---
    test("crc32_bytes4_to_N4_zlib",
         lambda d: crc32_zlib(d["raw"][4:-4]))
    test("crc32_bytes4_to_N4_bzip2",
         lambda d: crc32_bzip2_variant(d["raw"][4:-4]))

    # --- Candidate 4: CRC32 of decompressed body ---
    test("crc32_body_zlib",
         lambda d: crc32_zlib(d["body"]))
    test("crc32_body_bzip2",
         lambda d: crc32_bzip2_variant(d["body"]))
    test("crc32_body_init0_nofinal",
         lambda d: crc32_bzip2_variant(d["body"], init=0, final_xor=0))
    test("crc32_body_init0_final0",
         lambda d: crc32_bzip2_variant(d["body"], init=0, final_xor=0xFFFFFFFF))

    # --- Candidate 5: CRC32 of first N bytes of body ---
    for n in [4, 8, 16, 32, 64, 128, 256, 512, 1024]:
        test(f"crc32_body_first{n}",
             lambda d, n=n: crc32_zlib(d["body"][:n]))

    # --- Candidate 6: CRC32 of last N bytes of body ---
    for n in [4, 8, 16, 32, 64, 128, 256, 512, 1024]:
        test(f"crc32_body_last{n}",
             lambda d, n=n: crc32_zlib(d["body"][-n:]))

    # --- Candidate 7: Adler32 of decompressed body ---
    test("adler32_body",
         lambda d: adler32(d["body"]))

    # --- Candidate 8: zlib stream's native adler32 and variants ---
    test("zlib_native_adler32",
         lambda d: d["zlib_adler"])
    test("zlib_native_adler32_byteswap",
         lambda d: u32_le(struct.pack(">I", d["zlib_adler"])))
    test("zlib_adler_xor_stored_size",
         lambda d: (d["zlib_adler"] ^ d["stored_size"]) & 0xFFFFFFFF)
    test("zlib_adler_plus_stored_size",
         lambda d: (d["zlib_adler"] + d["stored_size"]) & 0xFFFFFFFF)
    test("stored_size_only",
         lambda d: d["stored_size"])

    # --- Candidate 9: XOR-fold of body ---
    test("xor_fold_32_body",
         lambda d: xor_fold_32(d["body"]))
    test("xor_fold_32_compressed",
         lambda d: xor_fold_32(d["compressed"]))
    test("xor_fold_32_file_minus_trailer",
         lambda d: xor_fold_32(d["raw"][:-4]))

    # --- Candidate 10: Sum of body bytes mod 2^32 ---
    test("sum32_body",
         lambda d: sum32(d["body"]))
    test("sum32_compressed",
         lambda d: sum32(d["compressed"]))

    # --- Candidate 11: ESH / Ensemble Studios hash variants ---
    test("esh_hash_body",
         lambda d: esh_hash(d["body"]))
    test("esh_hash_compressed",
         lambda d: esh_hash(d["compressed"]))
    test("esh_hash_file_minus_trailer",
         lambda d: esh_hash(d["raw"][:-4]))
    test("bernstein_hash_body",
         lambda d: bernstein_hash(d["body"]))

    # --- Candidate 12: Trailer from body internal field (body bytes near offset 10) ---
    # The build-info string / version is near body[0:16]; check if trailer == some u32 there
    for off in range(0, 40, 4):
        test(f"body_u32le_offset{off}",
             lambda d, o=off: u32_le(d["body"][o:o+4]) if len(d["body"]) > o+4 else 0)

    # --- Candidate 13: Version field body[6:10] ---
    test("body_u32le_offset6",
         lambda d: u32_le(d["body"][6:10]))

    # --- Candidate 14: CRC32 with trailer region zeroed (compute over file with last-4 = 0x00000000) ---
    def crc32_trailer_zeroed(d):
        data = bytearray(d["raw"])
        data[-4:] = b'\x00\x00\x00\x00'
        return crc32_zlib(bytes(data))
    test("crc32_file_trailer_zeroed", crc32_trailer_zeroed)

    # --- Candidate 15/16: CRC32(body[:N]) for various breakpoints ---
    body_breakpoints = [100, 500, 1000, 5000, 10000, 50000, 100000]
    for n in body_breakpoints:
        test(f"crc32_body_first{n}_zlib",
             lambda d, n=n: crc32_zlib(d["body"][:n]) if len(d["body"]) >= n else 0)

    # --- Search for trailer bytes in body ---
    print()
    print("=== SEARCHING FOR TRAILER BYTES WITHIN BODY ===")
    for d in loaded:
        trailer_bytes = bytes.fromhex(d["trailer_hex"])
        # Search for exact 4-byte sequence in body
        idx = d["body"].find(trailer_bytes)
        if idx >= 0:
            print(f"  {d['label']}: FOUND trailer at body offset {idx} (0x{idx:08x})")
            # Show context
            ctx_start = max(0, idx-8)
            ctx_end = min(len(d["body"]), idx+12)
            print(f"    Context: {d['body'][ctx_start:ctx_end].hex()}")
        else:
            print(f"  {d['label']}: NOT found in body")

        # Also search as big-endian u32
        trailer_be = struct.pack(">I", d["expected_int"])
        idx2 = d["body"].find(trailer_be)
        if idx2 >= 0 and trailer_be != trailer_bytes:
            print(f"  {d['label']}: FOUND trailer (BE) at body offset {idx2} (0x{idx2:08x})")

    # --- Body first 64 bytes hex dump for context ---
    print()
    print("=== BODY FIRST 64 BYTES (HEX) ===")
    for d in loaded:
        print(f"  {d['label']}: {d['body'][:64].hex()}")

    # --- Zlib stream last 8 bytes (contains Adler32) ---
    print()
    print("=== ZLIB STREAM LAST 8 BYTES + ADLER32 ===")
    for d in loaded:
        last8 = d["compressed"][-8:]
        print(f"  {d['label']}: last8={last8.hex()}, adler32(BE)={d['zlib_adler']:08x}, trailer={d['trailer_hex']}")

    # --- Compute relationship: trailer vs adler32 ---
    print()
    print("=== ARITHMETIC RELATIONSHIP: trailer vs zlib_adler ===")
    for d in loaded:
        t = d["expected_int"]
        a = d["zlib_adler"]
        print(f"  {d['label']}: T={t:08x} A={a:08x} T^A={t^a:08x} T-A={((t-a)&0xFFFFFFFF):08x} A-T={((a-t)&0xFFFFFFFF):08x} T+A={((t+a)&0xFFFFFFFF):08x}")

    # --- Summarise results ---
    print()
    print("=== SUMMARY: Candidates matching >= 2 files ===")
    for name, row in results.items():
        matches = sum(1 for _, m in row if m)
        if matches >= 2:
            details = "  ".join(f"{c:08x}{'✓' if m else '✗'}" for c, m in row)
            print(f"  [{matches}/4] {name}: {details}")

    print()
    print("=== SUMMARY: Perfect matches (4/4) ===")
    perfect = [name for name, row in results.items() if all(m for _, m in row)]
    if perfect:
        for name in perfect:
            print(f"  PERFECT MATCH: {name}")
    else:
        print("  None found.")

if __name__ == "__main__":
    analyse()
