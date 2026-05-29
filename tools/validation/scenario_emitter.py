#!/usr/bin/env python3
"""ANW Scenario Emitter.

Bake player->civ bindings into a known-good .age3Yscn template and emit one
scenario per row of a 6-row playbook matrix (A..F), each with 8 player slots
preset to a specific ANW civ + AI loader. The lobby civ-picker is bypassed
entirely; the engine reads the binding from the scenario binary.

Container layout (post-decompression body):

    file[0:4]   = b'l33t'                      (magic)
    file[4:8]   = uint32_LE outer_size         (== len(body))
    file[8:]    = zlib-compressed body

    body[0:2]   = b'BG'
    body[2:6]   = uint32_LE inner_size         (== len(body) - 7)
    body[6:10]  = uint32_LE version
    body[10:12] = b'FH'
    ...

Player table = 9 BP records contiguous near offset ~0x279ee0 in the LL
template (1 Gaia + 8 player slots). Per record:

    01            - flag (slot exists)
    'BP'          - magic
    u32 size      - record body size (excluding 7-byte header)
    u32 version   - 0xFC (252) in v105 templates
    [sub-records] - tagged P1, P2, P3, P4, P5, P6, ... each: tag(2) + u32 size + payload

P5 sub-record (the civ binding) payload layout:

    LP-UTF16  hcname        e.g. b'homecityspanish.xml'    <- CIV BINDING
    20 bytes  fixed flags   01 00 00 00 00 00 00 00 01 01 01 01 00 00 00 00 00 00 00 00
    LP-UTF16  ai_loader     '' (human) or 'aiLoaderStandard' (AI)
    18 bytes  tail          00 00 00 00 00 00 [u32 player_id] ff ff ff ff 00 00 00 00

Patching the hcname/ai_loader changes the size of the P5 sub-record, the
enclosing BP record, and ultimately the body. inner_size and outer_size MUST
both be patched (the v2 builder failed because it didn't).

CLI:

    python3 scenario_emitter.py emit --template <path> \
        --matrix matrix.json --out-dir out/ [--ai aiLoaderStandard]

    python3 scenario_emitter.py emit-playbook --template <path> --out-dir out/

The "playbook" command generates ANW_Coverage_A..F per the documented matrix.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path
from typing import List, Optional, Tuple


# --- Container -------------------------------------------------------------


L33T_MAGIC = b"l33t"
BG_MAGIC = b"BG"
FH_MAGIC = b"FH"


def load_scenario(path: Path) -> Tuple[bytes, bytes]:
    """Load an .age3Yscn file. Returns (raw_file_bytes, decompressed_body).

    Note: stock scenarios also carry a 4-byte trailing signature AFTER the
    zlib stream — see `load_scenario_with_trailer` if you need to preserve
    it for engine acceptance. The engine's load-gate rejects files that
    drop the trailer.
    """
    raw, body, _trailer = load_scenario_with_trailer(path)
    return raw, body


def load_scenario_with_trailer(path: Path) -> Tuple[bytes, bytes, bytes]:
    """Load an .age3Yscn file. Returns (raw_bytes, decompressed_body, trailer).

    `trailer` is the bytes that appear after the zlib stream's adler32 end —
    typically 4 bytes on stock scenarios (a per-scenario signature whose
    semantics are not yet decoded). Empty `bytes()` if there is no trailer.
    Preserving the trailer across a re-pack is required for the engine's
    scenario load-gate to accept the file (empirically validated 2026-05-13).
    """
    raw = path.read_bytes()
    if raw[:4] != L33T_MAGIC:
        raise ValueError(f"{path}: bad magic {raw[:4]!r}, expected b'l33t'")
    declared_size = struct.unpack_from("<I", raw, 4)[0]
    do = zlib.decompressobj()
    body = do.decompress(raw[8:])
    trailer = bytes(do.unused_data)
    if len(body) != declared_size:
        # Not fatal for parse, but warn -- this is the v2-builder bug.
        print(
            f"WARN: {path}: outer decompressed_size={declared_size} but actual "
            f"body length={len(body)} (delta={len(body)-declared_size})",
            file=sys.stderr,
        )
    if body[:2] != BG_MAGIC:
        raise ValueError(f"{path}: body missing 'BG' magic")
    inner = struct.unpack_from("<I", body, 2)[0]
    if inner != len(body) - 7:
        print(
            f"WARN: {path}: inner_size={inner} but body_len-7={len(body)-7} "
            f"(delta={len(body)-7-inner})",
            file=sys.stderr,
        )
    if body[10:12] != FH_MAGIC:
        raise ValueError(f"{path}: body missing 'FH' submagic at +10")
    return raw, body, trailer


def compute_crc32_trailer(raw_file_without_trailer: bytes) -> bytes:
    """Compute the 4-byte engine-validated trailer for an .age3Yscn file.

    Reverse-engineered 2026-05-13 (see tools/validation/SCENARIO_TRAILER_ANALYSIS.md).
    Verified 4/4 against Bombard_Brawl, _test_template, QuickSavegame,
    QuickSavegame.bak.

    Algorithm:
      trailer_bytes = LE u32 of zlib.crc32(file_with_trailer_region_zeroed)

    The engine's Custom Scenario load-gate verifies this checksum; a stale or
    inherited trailer (e.g. carrying the template's trailer into a modified
    body) is rejected with "INVALID FILE".
    """
    data = raw_file_without_trailer + b"\x00\x00\x00\x00"
    crc = zlib.crc32(data) & 0xFFFFFFFF
    return struct.pack("<I", crc)


def verify_trailer(path: Path) -> bool:
    """Return True iff the file's last 4 bytes equal compute_crc32_trailer(file[:-4])."""
    raw = path.read_bytes()
    if len(raw) < 12:
        return False
    expected = compute_crc32_trailer(raw[:-4])
    return raw[-4:] == expected


def pack_scenario(
    body: bytes,
    trailer: bytes = b"",
    recompute_trailer: bool = True,
) -> bytes:
    """Pack a body back into the l33t/zlib container.

    Args:
        body: decompressed body bytes (will be CRC32-trailer-computed over
              the full re-packed file).
        trailer: legacy parameter — explicit trailer bytes to append. ONLY
              used when ``recompute_trailer`` is False. Passing a non-empty
              trailer with ``recompute_trailer=True`` is a no-op and logs a
              warning, because the engine will reject the inherited trailer
              for any modified body.
        recompute_trailer: when True (default, recommended), the trailer is
              recomputed as ``CRC32(file_with_trailer_zeroed)`` stored
              little-endian. Set to False ONLY for diagnostic round-trips
              where you want byte-exact reproduction of an existing file.

    Returns:
        Complete .age3Yscn bytes ready to write to disk.
    """
    body = bytearray(body)
    # Patch inner_size (= len(body) - 7).
    struct.pack_into("<I", body, 2, len(body) - 7)
    body = bytes(body)
    compressed = zlib.compress(body, level=6)
    out = bytearray()
    out += L33T_MAGIC
    out += struct.pack("<I", len(body))  # outer decompressed_size
    out += compressed
    if recompute_trailer:
        if trailer:
            print(
                "WARN: pack_scenario(): ignoring explicit `trailer` because "
                "recompute_trailer=True (engine validates CRC32; an inherited "
                "trailer would be rejected).",
                file=sys.stderr,
            )
        out += compute_crc32_trailer(bytes(out))
    elif trailer:
        out += trailer
    return bytes(out)


# --- Player table parser ---------------------------------------------------


class SubRecord:
    """A 6-byte-header tagged sub-record inside a BP block."""

    __slots__ = ("tag", "off", "size", "payload")

    def __init__(self, tag: bytes, off: int, size: int, payload: bytes) -> None:
        self.tag = tag
        self.off = off  # absolute body offset of the tag (start of record)
        self.size = size  # payload length
        self.payload = payload  # bytes(size)

    def __repr__(self) -> str:
        return f"SubRecord({self.tag!r}, off={self.off:#x}, size={self.size})"


class BPRecord:
    """One Bang-Player record: 1-byte flag + 'BP' + u32 size + u32 version + payload."""

    __slots__ = ("off", "size", "version", "subs")

    def __init__(self, off: int, size: int, version: int, subs: List[SubRecord]) -> None:
        self.off = off  # absolute body offset of the leading 0x01 flag
        self.size = size  # u32 size field (covers the version+sub-records)
        self.version = version
        self.subs = subs

    def __repr__(self) -> str:
        return f"BPRecord(off={self.off:#x}, size={self.size}, subs={len(self.subs)})"

    def get_sub(self, tag: bytes) -> Optional[SubRecord]:
        for s in self.subs:
            if s.tag == tag:
                return s
        return None


def _parse_subs(body: bytes, start: int, end: int) -> List[SubRecord]:
    out: List[SubRecord] = []
    cur = start
    while cur + 6 <= end:
        tag = bytes(body[cur:cur + 2])
        # Tag must be ASCII-alphanumeric (P1..P9, then later A0..Z9 etc.)
        if not (32 < tag[0] < 127 and 32 < tag[1] < 127):
            break
        sz = struct.unpack_from("<I", body, cur + 2)[0]
        if sz < 0 or cur + 6 + sz > end:
            break
        payload = bytes(body[cur + 6:cur + 6 + sz])
        out.append(SubRecord(tag, cur, sz, payload))
        cur = cur + 6 + sz
    return out


def find_bp_records(body: bytes) -> List[BPRecord]:
    """Locate all BP records in the body. Heuristic: 0x01 prefix + 'BP' + a
    sane size + first sub-record tagged 'P1'.
    Returns them in file order.
    """
    out: List[BPRecord] = []
    needle = b"\x01BP"
    cur = 0
    while True:
        i = body.find(needle, cur)
        if i < 0:
            break
        cur = i + 1
        # i is the offset of the 0x01 flag; 'BP' at i+1.
        if i + 11 > len(body):
            continue
        sz = struct.unpack_from("<I", body, i + 3)[0]
        version = struct.unpack_from("<I", body, i + 7)[0]
        if sz < 30 or sz > 1_000_000:
            continue
        if i + 7 + sz > len(body):
            continue
        # First sub-record at i+11 must be tagged 'P1'.
        if body[i + 11:i + 13] != b"P1":
            continue
        subs = _parse_subs(body, i + 11, i + 7 + sz)
        # Sanity: must have at least P1, P2, P3.
        tags = {s.tag for s in subs}
        if not {b"P1", b"P2", b"P3"}.issubset(tags):
            continue
        out.append(BPRecord(off=i, size=sz, version=version, subs=subs))
    return out


# --- P5 (civ binding) ------------------------------------------------------


# 20 bytes of per-player flags between the hcname and the AI loader name.
#
# Original assumption (refuted 2026-05-13): these were "fixed" at
#   01 00 00 00 00 00 00 00 01 01 01 01 00 00 00 00 00 00 00 00.
# That pattern is what _test_template.age3Yscn carries — and the engine
# REJECTS the file with an "INVALID FILE" modal when you try to load it
# from Single Player → Custom Scenario.
#
# Stock Bombard_Brawl.age3Yscn (which loads cleanly) actually has
# per-player variation, e.g.:
#   slot 1: ff ff ff ff 03 00 00 00 01 01 01 01 00 00 00 00 63 00 00 00
#   slot 2: ff ff ff ff 00 00 00 00 01 01 01 01 00 00 00 00 01 00 00 00
# i.e. bytes 0..3 are int32 -1, bytes 4..7 carry per-slot state (team id?
# observer flag? we don't know yet — they round-trip fine when preserved),
# bytes 8..11 are the only true constant 01 01 01 01, bytes 12..15 are
# always 00, and bytes 16..19 are per-slot again (color? civ-bias index?).
#
# We now treat this region as opaque per-record state and preserve it
# byte-for-byte through parse/serialize, identical to how the trailing
# `tail` bytes are handled. The legacy length is kept as a sanity bound.
_P5_MID_FLAGS_LEN = 20
# Tail length is NOT fixed across all scenarios:
#   _test_template.age3Yscn (broken):  18 bytes
#   Bombard_Brawl.age3Yscn (loads):    18/26/66 bytes depending on slot
# Bytes 0-17 are the same shape everywhere
#   (00 00 00 00 00 00  [u32 pid]  ff ff ff ff  00 00 00 00)
# but Bombard_Brawl appends an additional structure on most slots that
# the engine validates. We preserve the raw tail bytes verbatim instead
# of asserting a fixed length.
_P5_TAIL_MIN_LEN = 18


def _read_lp_utf16(buf: bytes, off: int) -> Tuple[str, int]:
    """Read a length-prefixed UTF-16-LE string. Returns (str, bytes_consumed)."""
    n = struct.unpack_from("<I", buf, off)[0]
    end = off + 4 + 2 * n
    return buf[off + 4:end].decode("utf-16-le"), 4 + 2 * n


def _write_lp_utf16(s: str) -> bytes:
    enc = s.encode("utf-16-le")
    if len(enc) % 2 != 0:
        raise ValueError("utf-16 encoding produced odd byte count")
    return struct.pack("<I", len(enc) // 2) + enc


class P5:
    """Parsed P5 sub-record (civ + AI binding)."""

    __slots__ = ("hcname", "mid_flags", "ai_loader", "tail")

    def __init__(self, hcname: str, mid_flags: bytes, ai_loader: str, tail: bytes) -> None:
        self.hcname = hcname
        self.mid_flags = mid_flags  # 20 raw bytes (opaque per-slot state)
        self.ai_loader = ai_loader
        self.tail = tail  # 18 raw tail bytes (preserve them)

    def __repr__(self) -> str:
        return f"P5(hcname={self.hcname!r}, ai_loader={self.ai_loader!r}, mid={self.mid_flags.hex()})"

    @classmethod
    def parse(cls, payload: bytes) -> "P5":
        cur = 0
        hcname, n = _read_lp_utf16(payload, cur)
        cur += n
        if cur + _P5_MID_FLAGS_LEN > len(payload):
            raise ValueError(
                f"P5 truncated before mid_flags at offset {cur}, "
                f"payload len {len(payload)}"
            )
        mid_flags = bytes(payload[cur:cur + _P5_MID_FLAGS_LEN])
        cur += _P5_MID_FLAGS_LEN
        ai_loader, n2 = _read_lp_utf16(payload, cur)
        cur += n2
        tail = bytes(payload[cur:])
        if len(tail) < _P5_TAIL_MIN_LEN:
            raise ValueError(
                f"P5 tail expected >={_P5_TAIL_MIN_LEN} bytes, got {len(tail)}"
            )
        return cls(hcname, mid_flags, ai_loader, tail)

    def serialize(self) -> bytes:
        if len(self.mid_flags) != _P5_MID_FLAGS_LEN:
            raise ValueError(
                f"mid_flags must be {_P5_MID_FLAGS_LEN} bytes, "
                f"got {len(self.mid_flags)}"
            )
        return (
            _write_lp_utf16(self.hcname)
            + self.mid_flags
            + _write_lp_utf16(self.ai_loader)
            + self.tail
        )


# --- BP / body rewriter ----------------------------------------------------


# Parent 'PL' (Player List) record wraps ALL the BP records.
# Layout:
#     'PL'          (2 bytes)            -- magic
#     u32 size                            -- covers ALL bytes after this field
#                                            up to and including the last BP
#     u32 player_count_a                  -- = number of BPs (9)
#     u32 player_count_b                  -- = number of BPs (9, identical?)
#     [9 BP records]
#
# Verified empirically against Bombard_Brawl 2026-05-14: PL.size = 31224,
# BP region length = 31216, delta = +8 (the two u32 count fields).
#
# CRITICAL: if you shrink/grow ANY BP record without updating PL.size, the
# engine's load-gate reads past the end of the BP region into the next
# section, mis-aligns, and rejects the scenario with "INVALID FILE".
# This was the silent root cause of every set_player_bindings failure
# until 2026-05-14 — fix landed in this commit.

_PL_MAGIC = b"PL"


def find_pl_header_offset(body: bytes, bps: List[BPRecord]) -> Optional[int]:
    """Locate the 'PL' magic that precedes the first BP record.

    Returns the byte offset of the 'P' in 'PL', or None if not found within
    32 bytes before the first BP. (We scan backwards to avoid false matches
    against 'PL' patterns elsewhere in the body — empirically the PL header
    is always immediately before the first BP, with 14 bytes between the 'P'
    and the BP[0] flag.)
    """
    if not bps:
        return None
    first_bp = bps[0].off
    search_start = max(0, first_bp - 32)
    idx = body.find(_PL_MAGIC, search_start, first_bp)
    if idx < 0:
        return None
    # Sanity: header layout is 'PL' + u32 size + u32 count + u32 count + BP[0].
    # That's idx + 2 + 4 + 4 + 4 = idx + 14 == first_bp.
    if idx + 14 != first_bp:
        return None
    return idx


def patch_pl_size(body: bytes, delta: int) -> bytes:
    """Adjust the parent PL.size field by `delta` bytes.

    `delta` is the net change to the BP region length. Called by
    replace_sub_payload after it rewrites a BP record's size.
    """
    if delta == 0:
        return body
    bps = find_bp_records(body)
    pl_off = find_pl_header_offset(body, bps)
    if pl_off is None:
        raise RuntimeError(
            "PL parent header not found before first BP — body structure "
            "is unexpected; refusing to silently corrupt PL.size"
        )
    out = bytearray(body)
    old_pl_size = struct.unpack_from("<I", out, pl_off + 2)[0]
    new_pl_size = old_pl_size + delta
    struct.pack_into("<I", out, pl_off + 2, new_pl_size)
    return bytes(out)


def replace_sub_payload(
    body: bytes, bp: BPRecord, sub: SubRecord, new_payload: bytes
) -> bytes:
    """Replace a sub-record's payload, patching the local size, the enclosing
    BP record's size, AND the parent PL.size field. Returns the new body
    (does NOT update outer length fields — call pack_scenario for that).

    Caller must NOT continue using the old `bp`/`sub` offsets after this
    returns; offsets shift by `delta = len(new_payload) - sub.size`.
    """
    delta = len(new_payload) - sub.size
    if delta == 0 and new_payload == sub.payload:
        return body
    # Rewrite sub-record payload + its size field.
    out = bytearray(body)
    # Sub-record header: tag(2) + u32 size + payload
    sub_payload_off = sub.off + 6
    # Splice
    out[sub_payload_off:sub_payload_off + sub.size] = new_payload
    # Patch sub-record size field
    struct.pack_into("<I", out, sub.off + 2, len(new_payload))
    # Patch enclosing BP record size field (at bp.off + 3, u32)
    new_bp_size = bp.size + delta
    struct.pack_into("<I", out, bp.off + 3, new_bp_size)
    body = bytes(out)
    # CRITICAL: also propagate the size delta up to the parent PL record.
    # See module-level comment block above for layout + failure mode.
    if delta != 0:
        body = patch_pl_size(body, delta)
    return body


# --- High-level emitter ----------------------------------------------------


def civ_to_hcname(civ: str) -> str:
    """Map a civ token (ANW or vanilla) -> homecity XML filename."""
    civ = civ.strip()
    if civ.startswith("ANW"):
        short = civ[3:].lower()
        return f"anwhomecity{short}.xml"
    # Vanilla civ tokens (e.g. "British", "French").
    return f"homecity{civ.lower()}.xml"


def hcname_to_civ(hcname: str) -> str:
    """Inverse of civ_to_hcname (best-effort, used for diagnostics)."""
    name = hcname.lower()
    if name.endswith(".xml"):
        name = name[:-4]
    if name.startswith("anwhomecity"):
        short = name[len("anwhomecity"):]
        return "ANW" + short.capitalize()
    if name.startswith("homecity"):
        short = name[len("homecity"):]
        return short.capitalize()
    return hcname


def get_player_bindings(body: bytes) -> List[Tuple[str, str, int]]:
    """Return list of (hcname, ai_loader, player_id) for each BP slot in body
    order (Gaia first, then Player 1..8)."""
    out = []
    for bp in find_bp_records(body):
        p5 = bp.get_sub(b"P5")
        p1 = bp.get_sub(b"P1")
        if p5 is None or p1 is None:
            continue
        try:
            parsed = P5.parse(p5.payload)
        except ValueError:
            out.append(("?", "?", -1))
            continue
        # P1 payload: u32 pid, u8 flag, u32 namelen, utf-16 name, ...
        pid = struct.unpack_from("<I", p1.payload, 0)[0]
        out.append((parsed.hcname, parsed.ai_loader, pid))
    return out


def set_player_bindings(
    body: bytes,
    civs: List[str],
    ai_loader: str = "aiLoaderStandard",
    ai_loaders: Optional[List[str]] = None,
) -> bytes:
    """Bind 8 player slots to the given list of civ tokens.

    civs: list of 8 ANW (or vanilla) civ tokens, mapped to player slots 1..8.
    ai_loader: default AI loader name when ai_loaders is not supplied.
        Empty string = human player.
    ai_loaders: optional per-slot AI loader list (8 entries). Each entry
        is the XS loader name for that slot, or '' for human. Overrides
        ai_loader when supplied. This is what you want for any scenario
        where one slot is a human observer and the rest are AI.

    The Gaia slot (BP[0]) is left untouched.

    Length invariants are enforced:
      - Each P5 sub-record's u32 size field
      - Each BP record's u32 size field
      - The outer body's inner_size (handled via pack_scenario)
      - The outer container's decompressed_size (also via pack_scenario)
    """
    if len(civs) != 8:
        raise ValueError(f"need 8 civ tokens, got {len(civs)}")
    if ai_loaders is not None and len(ai_loaders) != 8:
        raise ValueError(f"ai_loaders must be 8 entries, got {len(ai_loaders)}")
    hcnames = [civ_to_hcname(c) for c in civs]
    loaders = ai_loaders if ai_loaders is not None else [ai_loader] * 8
    # Re-locate BP records each iteration because offsets shift after every edit.
    for slot_idx in range(8):
        bps = find_bp_records(body)
        if len(bps) < 9:
            raise RuntimeError(
                f"expected >=9 BP records (1 Gaia + 8 players), found {len(bps)}"
            )
        bp = bps[slot_idx + 1]  # skip Gaia
        p5 = bp.get_sub(b"P5")
        if p5 is None:
            raise RuntimeError(f"BP[{slot_idx+1}] has no P5 sub-record")
        parsed = P5.parse(p5.payload)
        parsed.hcname = hcnames[slot_idx]
        parsed.ai_loader = loaders[slot_idx]
        new_payload = parsed.serialize()
        body = replace_sub_payload(body, bp, p5, new_payload)
    return body


# --- CLI -------------------------------------------------------------------


# Default per-playbook matrix (docs/SCENARIO_AUTHORING_PLAYBOOK.md).
# 2026-05-18: Updated to 44-civ roster (ANWAmericans, ANWBajaCalifornians
# removed).
# 2026-05-19: Removed 4 dormant civs — now 40 primaries in A-E (8 each); F holds
# 8 filler slots for scenario-binding validation only (all already in A-E).
#
# 2026-05-19 (frozen): The 6 ANW_Coverage_*.age3Yscn carriers are now treated
# as a FROZEN manual-fallback artifact (per user directive). They are kept
# on disk for crash-survival manual play (when exhibition_runner can't
# launch a particular civ), but `emit-playbook` is NOT part of any
# matrix-change reflex. Regenerate ONLY when explicitly asked; otherwise
# leave the on-disk files alone. Runner uses Scenario/ANEWWORLD.age3Yscn
# exclusively and re-emits it per-match with fresh civ bindings.
PLAYBOOK_MATRIX = {
    "A": [
        "ANWArgentines", "ANWAztecs", "ANWBarbary", "ANWBrazil",
        "ANWBritish", "ANWCanadians", "ANWChileans", "ANWChinese",
    ],
    "B": [
        "ANWColumbians", "ANWDutch", "ANWEgyptians", "ANWEthiopians",
        "ANWFinnish", "ANWFrench", "ANWGermans", "ANWHaitians",
    ],
    "C": [
        "ANWHaudenosaunee", "ANWHausa", "ANWHungarians", "ANWInca",
        "ANWIndians", "ANWIndonesians", "ANWItalians", "ANWJapanese",
    ],
    "D": [
        "ANWLakota", "ANWMaltese", "ANWMayans", "ANWMexicans",
        "ANWNapoleonicFrance", "ANWOttomans", "ANWPeruvians", "ANWPortuguese",
    ],
    "E": [
        "ANWRevFrance", "ANWRomanians", "ANWRussians", "ANWSouthAfricans",
        "ANWSpanish", "ANWSwedes", "ANWTexians", "ANWUSA",
    ],
    "F": [
        # Filler-only scenario (all 8 are already covered in A-E).
        # Kept so the 6-scenario binding test can still exercise a 6th slot.
        "ANWArgentines", "ANWBrazil", "ANWBritish", "ANWFrench",
        "ANWGermans", "ANWMexicans", "ANWNapoleonicFrance", "ANWSpanish",
    ],
}


def cmd_inspect(args: argparse.Namespace) -> int:
    raw, body = load_scenario(Path(args.template))
    print(f"file_size={len(raw)}  body_size={len(body)}  outer_size={struct.unpack_from('<I', raw, 4)[0]}  inner_size={struct.unpack_from('<I', body, 2)[0]}")
    bps = find_bp_records(body)
    print(f"BP records: {len(bps)}")
    for i, bp in enumerate(bps):
        p5 = bp.get_sub(b"P5")
        p1 = bp.get_sub(b"P1")
        if p1:
            pid = struct.unpack_from("<I", p1.payload, 0)[0]
            nlen = struct.unpack_from("<I", p1.payload, 5)[0]
            name = p1.payload[9:9 + 2 * nlen].decode("utf-16-le", errors="replace")
        else:
            pid, name = -1, "?"
        if p5:
            try:
                parsed = P5.parse(p5.payload)
                civ = hcname_to_civ(parsed.hcname)
                hc, ai = parsed.hcname, parsed.ai_loader
            except ValueError as e:
                hc, ai, civ = "?", "?", f"<P5 parse error: {e}>"
        else:
            hc, ai, civ = "<no P5>", "", ""
        print(
            f"  BP[{i}] @ {bp.off:#08x} size={bp.size:6d} "
            f"pid={pid} name={name!r:18s} hc={hc:30s} ai={ai!r:18s} civ={civ}"
        )
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    template = Path(args.template)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix = json.loads(Path(args.matrix).read_text())
    raw, body = load_scenario(template)
    for label, civs in sorted(matrix.items()):
        new_body = set_player_bindings(body, civs, ai_loader=args.ai)
        out = pack_scenario(new_body)
        out_path = out_dir / f"ANW_Coverage_{label}.age3Yscn"
        out_path.write_bytes(out)
        # Verify round-trip
        verify_raw = out
        verify_body = zlib.decompress(verify_raw[8:])
        bindings = get_player_bindings(verify_body)
        print(f"  wrote {out_path.name}  size={len(out)}  body={len(verify_body)}")
        for i, (hc, ai, pid) in enumerate(bindings):
            print(f"    slot {i}: pid={pid} hc={hc!r} ai={ai!r}")
    return 0


def cmd_emit_playbook(args: argparse.Namespace) -> int:
    """Emit ANW_Coverage_A..F per the 46-civ playbook matrix.

    Carrier resolution:
      - If --template is supplied, use it as-is.
      - Else, fall back to the stock AoE3DE Bombard_Brawl.age3Yscn (known to
        pass the engine load-gate); see ``find_default_carrier()``.

    Every emitted file gets a fresh CRC32 trailer via pack_scenario
    (recompute_trailer=True). Each file is then re-verified before we
    declare success — a wrong trailer aborts the whole batch with rc=1.

    Per-slot AI loader policy: Player 1 is a human observer (loader=''),
    Players 2..8 are AI under aiLoaderStandard. Mirrors cmd_emit_anewworld.
    """
    args.matrix = None
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.template:
        template = Path(args.template)
    else:
        template = find_default_carrier()
        print(f"using default carrier: {template}", file=sys.stderr)
    _ver, ok, msg = check_carrier_version(template)
    if not ok:
        print(msg, file=sys.stderr)
    raw, body, original_trailer = load_scenario_with_trailer(template)
    # Per-slot loaders: P1 human, P2..P8 AI.
    per_slot_loaders = [""] + [args.ai] * 7
    failures: List[str] = []
    for label, civs in sorted(PLAYBOOK_MATRIX.items()):
        new_body = set_player_bindings(
            body, civs, ai_loaders=per_slot_loaders
        )
        out = pack_scenario(new_body, recompute_trailer=True)
        out_path = out_dir / f"ANW_Coverage_{label}.age3Yscn"
        out_path.write_bytes(out)
        # Re-decode body for verification (strip outer header + trailer).
        verify_body = zlib.decompress(out[8 : len(out) - 4])
        bindings = get_player_bindings(verify_body)
        slot_civs = [hcname_to_civ(b[0]) for b in bindings[1:9]]
        slot_loaders = [b[1] for b in bindings[1:9]]
        trailer_ok = verify_trailer(out_path)
        status = "OK" if trailer_ok else "BAD-TRAILER"
        print(
            f"  [{status}] {out_path.name}  size={len(out)}  "
            f"trailer={out[-4:].hex()}\n"
            f"    civs={slot_civs}\n"
            f"    loaders={slot_loaders}"
        )
        if not trailer_ok:
            failures.append(out_path.name)
    if failures:
        print(
            f"ERROR: {len(failures)} file(s) failed CRC32 verification: {failures}",
            file=sys.stderr,
        )
        return 1
    return 0


# --- Carrier scenario paths -----------------------------------------------
#
# The canonical carrier is `Bombard_Brawl.age3Yscn` from the stock AoE3 DE
# install. Bombard_Brawl is a 9-BP single-map scenario that empirically passes
# the engine's Custom Scenario load-gate (verified in-game 2026-05-13). Our
# previous carrier (`Scenario/_test_template.age3Yscn`) was REJECTED with an
# "INVALID FILE" modal — even after the trailer-CRC32 fix — because its body
# has a structural defect we have not yet identified. Using BB as the carrier
# sidesteps that issue while we investigate.
#
# Resolution order for the default carrier:
#   1. Caller-supplied --template path (highest priority)
#   2. AoE3DE stock install:
#         ~/.local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/
#             ScoreChallenges/Bombard_Brawl.age3Yscn
#   3. Repo-local fallback (if user has copied BB into the repo):
#         tools/validation/_carrier_bb.age3Yscn
#
# The matrix runner (exhibition_runner.py) consumes the same carrier — every
# match re-emits the scenario with different ANW civ bindings.

_STOCK_BB_PATHS = [
    Path.home() / ".local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn",
    Path.home() / "Steam/steamapps/common/AoE3DE/Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn",
    Path(__file__).resolve().parent / "_carrier_bb.age3Yscn",
]


def find_default_carrier() -> Path:
    """Locate a known-good carrier scenario. Returns the first path that exists."""
    for p in _STOCK_BB_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError(
        "No carrier scenario found. Searched:\n  "
        + "\n  ".join(str(p) for p in _STOCK_BB_PATHS)
        + "\nCopy Bombard_Brawl.age3Yscn from the AoE3 DE install into one of these locations."
    )


# Engine's Custom Scenario load-gate accepts BG body version up to 103
# inclusive (empirical max across all 79 stock scenarios in the
# 2026-05-13 AoE3DE install). Higher versions are quick-save / replay
# formats and gate-reject with "INVALID FILE". See
# tools/validation/TEMPLATE_BODY_REJECTION_FORENSICS.md for details.
SUPPORTED_BG_VERSION_MAX = 103


def check_carrier_version(carrier_path: Path) -> Tuple[int, bool, str]:
    """Validate a carrier's BG body version against the engine-supported range.

    Returns (body_version, ok, message). ``ok`` is False when the carrier
    body version exceeds SUPPORTED_BG_VERSION_MAX — typical for quick-save
    files mis-used as scenario carriers (e.g. the deprecated
    Scenario/_test_template.age3Yscn). The emitter prints the message to
    stderr but DOES proceed so that callers who know what they're doing
    can still override.
    """
    _raw, body = load_scenario(carrier_path)
    version = struct.unpack_from("<I", body, 6)[0]
    ok = version <= SUPPORTED_BG_VERSION_MAX
    if ok:
        msg = f"carrier BG version {version} (<= {SUPPORTED_BG_VERSION_MAX}, OK)"
    else:
        msg = (
            f"WARN: carrier {carrier_path} has BG body version {version} > "
            f"{SUPPORTED_BG_VERSION_MAX}. This is a QUICK-SAVE / REPLAY format; "
            f"the engine's Custom Scenario load-gate will reject the emitted "
            f"file with 'INVALID FILE'. Use Bombard_Brawl.age3Yscn or any "
            f"stock-install scenario as the carrier. See "
            f"tools/validation/TEMPLATE_BODY_REJECTION_FORENSICS.md."
        )
    return version, ok, msg


# 8-civ diverse roster for the canonical ANEWWORLD AI test scenario.
# Each civ exercises a different wall doctrine so a single match exposes
# all 6 smart-wall strategies + diverse personalities.
#
#   Slot 1: human observer (P1)
#   Slots 2..8: AI under aiLoaderStandard
#
# Wall-doctrine coverage:
#   ANWBritish      -> FortressRing      (vanilla baseline)
#   ANWAztecs       -> ChokepointSegments (Montezuma)
#   ANWMaltese      -> CoastalBatteries  (La Valette)
#   ANWRussians     -> FrontierPalisades (Catherine)
#   ANWUSA          -> UrbanBarricade    (Washington)
#   ANWLakota       -> MobileNoWalls     (Crazy Horse)
#   ANWFrench       -> FortressRing      (Bourbon — base French)
#   ANWJapanese     -> MobileNoWalls     (Tokugawa)
ANEWWORLD_CIVS = [
    "ANWBritish",       # P1 human observer
    "ANWAztecs",        # P2 AI - ChokepointSegments
    "ANWMaltese",       # P3 AI - CoastalBatteries
    "ANWRussians",      # P4 AI - FrontierPalisades
    "ANWUSA",           # P5 AI - UrbanBarricade
    "ANWLakota",        # P6 AI - MobileNoWalls
    "ANWFrench",        # P7 AI - FortressRing
    "ANWJapanese",      # P8 AI - MobileNoWalls
]
ANEWWORLD_LOADERS = [
    "",                 # P1 human
    "aiLoaderStandard", # P2 AI
    "aiLoaderStandard", # P3 AI
    "aiLoaderStandard", # P4 AI
    "aiLoaderStandard", # P5 AI
    "aiLoaderStandard", # P6 AI
    "aiLoaderStandard", # P7 AI
    "aiLoaderStandard", # P8 AI
]


def cmd_emit_anewworld(args: argparse.Namespace) -> int:
    """Generate the canonical ANEWWORLD.age3Yscn from a known-good carrier.

    8 ANW civs spanning all 6 wall doctrines + Player 1 as a human observer
    seat. Used by tools/validation/exhibition_runner.py and by the user when
    manually loading the scenario for live AI observation.

    Carrier resolution:
      - If --template is supplied, use it as-is.
      - Else, fall back to the stock AoE3DE Bombard_Brawl.age3Yscn (known to
        pass the engine load-gate); see ``find_default_carrier()``.

    The trailer is ALWAYS recomputed as CRC32(file_with_trailer_zeroed) so
    that any body modification is reflected in a fresh, engine-valid trailer.
    """
    if args.template:
        template = Path(args.template)
    else:
        template = find_default_carrier()
        print(f"using default carrier: {template}", file=sys.stderr)
    _ver, ok, msg = check_carrier_version(template)
    if not ok:
        print(msg, file=sys.stderr)
    out_path = Path(args.out)
    raw, body, original_trailer = load_scenario_with_trailer(template)
    new_body = set_player_bindings(
        body, ANEWWORLD_CIVS, ai_loaders=ANEWWORLD_LOADERS
    )
    # Trailer recomputed inside pack_scenario via CRC32 of full file.
    out = pack_scenario(new_body, recompute_trailer=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(out)
    verify_body = zlib.decompress(out[8 : len(out) - 4])
    bindings = get_player_bindings(verify_body)
    new_trailer = out[-4:]
    trailer_ok = verify_trailer(out_path)
    print(
        f"wrote {out_path}  size={len(out)}  body={len(verify_body)}\n"
        f"  carrier={template}\n"
        f"  carrier_trailer={original_trailer.hex() or '<none>'}\n"
        f"  emitted_trailer={new_trailer.hex()}  trailer_crc32_ok={trailer_ok}"
    )
    for i, (hc, ai_l, pid) in enumerate(bindings):
        role = "Gaia" if i == 0 else ("HUMAN" if not ai_l else "AI")
        print(f"  slot {i}: pid={pid} role={role:5s} hc={hc!r} ai={ai_l!r}")
    if not trailer_ok:
        print("ERROR: emitted file fails CRC32 trailer verification!", file=sys.stderr)
        return 1
    return 0


def cmd_validate_trailer(args: argparse.Namespace) -> int:
    """Verify the CRC32 trailer of one or more .age3Yscn files.

    Files with a wrong trailer are rejected by the engine's load-gate
    ("INVALID FILE" modal). This subcommand is the cheapest pre-flight check
    before launching the game.
    """
    rc = 0
    for arg in args.paths:
        p = Path(arg)
        raw = p.read_bytes()
        if len(raw) < 12:
            print(f"BAD: {p}: file too short ({len(raw)} bytes)")
            rc = 1
            continue
        expected = compute_crc32_trailer(raw[:-4])
        actual = raw[-4:]
        ok = expected == actual
        status = "OK" if ok else "BAD"
        print(
            f"{status}: {p}\n"
            f"  expected_trailer={expected.hex()} actual_trailer={actual.hex()}"
        )
        if not ok:
            rc = 1
    return rc


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ins = sub.add_parser("inspect", help="dump player table from a scenario")
    p_ins.add_argument("template")
    p_ins.set_defaults(func=cmd_inspect)

    p_emit = sub.add_parser("emit", help="emit scenarios from a JSON matrix")
    p_emit.add_argument("--template", required=True)
    p_emit.add_argument("--matrix", required=True, help="JSON: {label: [8 civs]}")
    p_emit.add_argument("--out-dir", required=True)
    p_emit.add_argument("--ai", default="aiLoaderStandard",
                        help="AI loader name (empty for human)")
    p_emit.set_defaults(func=cmd_emit)

    p_pb = sub.add_parser("emit-playbook",
                          help="emit ANW_Coverage_A..F per the documented matrix")
    p_pb.add_argument(
        "--template",
        default=None,
        help="path to known-good carrier scenario (default: stock Bombard_Brawl.age3Yscn)",
    )
    p_pb.add_argument("--out-dir", required=True)
    p_pb.add_argument("--ai", default="aiLoaderStandard",
                      help="AI loader name for slots 2..8 (P1 is always human)")
    p_pb.set_defaults(func=cmd_emit_playbook)

    p_aw = sub.add_parser(
        "emit-anewworld",
        help="generate the canonical 8-civ ANEWWORLD.age3Yscn with P1 human + 7 AI",
    )
    p_aw.add_argument(
        "--template",
        default=None,
        help="path to known-good carrier scenario (default: stock Bombard_Brawl.age3Yscn)",
    )
    p_aw.add_argument(
        "--out",
        required=True,
        help="output path, typically Scenario/ANEWWORLD.age3Yscn",
    )
    p_aw.set_defaults(func=cmd_emit_anewworld)

    p_vt = sub.add_parser(
        "validate-trailer",
        help="verify CRC32 trailer (engine load-gate uses this checksum)",
    )
    p_vt.add_argument("paths", nargs="+", help="one or more .age3Yscn files to check")
    p_vt.set_defaults(func=cmd_validate_trailer)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
