# AoE3 DE `.age3Yscn` Trailer Reverse-Engineering

## Result: SOLVED — 4/4 perfect match

### Formula

```python
import zlib, struct

def compute_trailer(raw_file_bytes: bytes) -> bytes:
    """
    Compute the correct 4-byte trailer for an AoE3 DE .age3Yscn file.
    The file must already be complete (header + zlib stream), without its trailer.
    """
    data = raw_file_bytes + b'\x00\x00\x00\x00'   # pad where trailer will go
    crc = zlib.crc32(data) & 0xFFFFFFFF            # standard zlib CRC32 (poly 0xEDB88320)
    return struct.pack('<I', crc)                   # stored as little-endian uint32

def patch_trailer(file_path: str):
    """Recompute and write the correct trailer into an existing file."""
    raw = open(file_path, 'rb').read()
    trailer = compute_trailer(raw[:-4])             # drop existing trailer first
    with open(file_path, 'wb') as f:
        f.write(raw[:-4] + trailer)
```

In plain English: the last 4 bytes of the file = **CRC32 of the entire file with those last 4 bytes zeroed**, stored little-endian.  This is equivalent to the standard "CRC32 embedded in its own field" pattern (compute over the file with the checksum region = 0x00000000).

---

## Verification Table (all 4 data points)

| File | outer bytes | expected trailer | computed trailer | match |
|------|------------|-----------------|-----------------|-------|
| Bombard_Brawl.age3Yscn | 369942 | `45069598` | `45069598` | PASS |
| _test_template.age3Yscn | 160246 | `b7383381` | `b7383381` | PASS |
| QuickSavegame.age3Yscn | 150423 | `16558739` | `16558739` | PASS |
| QuickSavegame.bak | 150425 | `b3a30be2` | `b3a30be2` | PASS |

---

## Important Implication: `_test_template` rejection is NOT the trailer

The `_test_template.age3Yscn` file has a **correct trailer** (`b7383381` matches the formula). Its engine rejection ("INVALID FILE") must be caused by something else in the file body — not the 4-byte checksum. Investigate the body XML/binary content for version mismatches, missing mandatory fields, or unsupported section tags.

---

## Candidates Tested (all failed except winner)

Prior session already ruled out: xxh32, xxh64, murmur3, djb2, sdbm, fnv1, fnv1a, jenkins oaat, ELF hash, CRC32 with multiple polynomials, MD5/SHA1/SHA256 lo/hi 32 bits.

This session tested (0/4 match unless noted):

| Candidate | Result |
|-----------|--------|
| CRC32(file[:-4]) — bytes 0..N-4 | 0/4 |
| CRC32(zlib stream only, bytes 8..N-4) | 0/4 |
| CRC32(bytes 4..N-4) | 0/4 |
| CRC32(decompressed body) | 0/4 |
| CRC32(body[:N]) for N=4,8,…,100000 | 0/4 all |
| CRC32(body[-N:]) for N=4,8,…,1024 | 0/4 all |
| Adler32(decompressed body) | 0/4 |
| zlib native Adler32 (last 4 of compressed stream) | 0/4 |
| zlib Adler32 byteswap / XOR / add with stored size | 0/4 |
| Stored body size u32 alone | 0/4 |
| XOR-fold 32-bit of body / compressed / file-minus-trailer | 0/4 |
| Sum of body bytes mod 2^32 | 0/4 |
| ESH hash (Ensemble Studios polynomial, init 0 and 1) | 0/4 |
| Bernstein hash of body | 0/4 |
| Body internal u32 at offsets 0,4,8…36,6 | 0/4 all |
| **CRC32(file with trailer zeroed) stored LE** | **4/4 WINNER** |
| CRC32(file with trailer zeroed) stored BE | 0/4 |
| Trailer bytes found literally in body | not found in any file |

---

## File Structure Reference

```
Offset   Size  Description
0x00       4   Magic/version u32 LE  (0x4247xxxx observed)
0x04       4   Decompressed body size u32 LE
0x08    N-12   zlib compressed body stream (header + deflate + Adler32)
N-4        4   Trailer = CRC32(file[0..N-4] + 0x00000000) as LE u32
```

The zlib stream itself ends with a 4-byte big-endian Adler32 (standard zlib framing), which is distinct from the file trailer.

---

## Quick Sanity Check Script

```python
import zlib, struct, sys

def verify_trailer(path):
    raw = open(path,'rb').read()
    data = bytearray(raw)
    data[-4:] = b'\x00\x00\x00\x00'
    expected = struct.pack('<I', zlib.crc32(bytes(data)) & 0xFFFFFFFF)
    actual = raw[-4:]
    ok = expected == actual
    print(f"{'OK' if ok else 'BAD'}: {path}")
    if not ok:
        print(f"  expected {expected.hex()}, got {actual.hex()}")
    return ok

if __name__ == '__main__':
    for p in sys.argv[1:]:
        verify_trailer(p)
```
