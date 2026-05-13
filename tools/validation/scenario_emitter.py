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
    """Load an .age3Yscn file. Returns (raw_file_bytes, decompressed_body)."""
    raw = path.read_bytes()
    if raw[:4] != L33T_MAGIC:
        raise ValueError(f"{path}: bad magic {raw[:4]!r}, expected b'l33t'")
    declared_size = struct.unpack_from("<I", raw, 4)[0]
    body = zlib.decompress(raw[8:])
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
    return raw, body


def pack_scenario(body: bytes) -> bytes:
    """Pack a body back into the l33t/zlib container, recomputing all length
    invariants."""
    body = bytearray(body)
    # Patch inner_size (= len(body) - 7).
    struct.pack_into("<I", body, 2, len(body) - 7)
    body = bytes(body)
    compressed = zlib.compress(body, level=6)
    out = bytearray()
    out += L33T_MAGIC
    out += struct.pack("<I", len(body))  # outer decompressed_size
    out += compressed
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


# 20 bytes of fixed flags between the hcname and the AI loader name.
_P5_MID_FLAGS = bytes.fromhex("01000000 00000000 01010101 00000000 00000000".replace(" ", ""))
_P5_TAIL_LEN = 18  # 00 00 00 00 00 00 [u32 pid] ff ff ff ff 00 00 00 00


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

    __slots__ = ("hcname", "ai_loader", "tail")

    def __init__(self, hcname: str, ai_loader: str, tail: bytes) -> None:
        self.hcname = hcname
        self.ai_loader = ai_loader
        self.tail = tail  # 18 raw tail bytes (preserve them)

    def __repr__(self) -> str:
        return f"P5(hcname={self.hcname!r}, ai_loader={self.ai_loader!r})"

    @classmethod
    def parse(cls, payload: bytes) -> "P5":
        cur = 0
        hcname, n = _read_lp_utf16(payload, cur)
        cur += n
        if payload[cur:cur + len(_P5_MID_FLAGS)] != _P5_MID_FLAGS:
            raise ValueError(
                f"P5 mid flags mismatch at offset {cur} (got "
                f"{payload[cur:cur + 20].hex()}, expected {_P5_MID_FLAGS.hex()})"
            )
        cur += len(_P5_MID_FLAGS)
        ai_loader, n2 = _read_lp_utf16(payload, cur)
        cur += n2
        tail = payload[cur:]
        if len(tail) != _P5_TAIL_LEN:
            raise ValueError(
                f"P5 tail expected {_P5_TAIL_LEN} bytes, got {len(tail)}"
            )
        return cls(hcname, ai_loader, tail)

    def serialize(self) -> bytes:
        return (
            _write_lp_utf16(self.hcname)
            + _P5_MID_FLAGS
            + _write_lp_utf16(self.ai_loader)
            + self.tail
        )


# --- BP / body rewriter ----------------------------------------------------


def replace_sub_payload(
    body: bytes, bp: BPRecord, sub: SubRecord, new_payload: bytes
) -> bytes:
    """Replace a sub-record's payload, patching the local size and the
    enclosing BP record's size. Returns the new body (does NOT update outer
    length fields - call pack_scenario for that).

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
    return bytes(out)


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
PLAYBOOK_MATRIX = {
    "A": [
        "ANWArgentines", "ANWAztecs", "ANWBajaCalifornians", "ANWBarbary",
        "ANWBrazil", "ANWBritish", "ANWCalifornians", "ANWCanadians",
    ],
    "B": [
        "ANWCentralAmericans", "ANWChileans", "ANWChinese", "ANWColumbians",
        "ANWDutch", "ANWEgyptians", "ANWEthiopians", "ANWFinnish",
    ],
    "C": [
        "ANWFrench", "ANWFrenchCanadians", "ANWGermans", "ANWHaitians",
        "ANWHaudenosaunee", "ANWHausa", "ANWHungarians", "ANWInca",
    ],
    "D": [
        "ANWIndians", "ANWIndonesians", "ANWItalians", "ANWJapanese",
        "ANWLakota", "ANWMaltese", "ANWMayans", "ANWMexicans",
    ],
    "E": [
        "ANWNapoleonicFrance", "ANWOttomans", "ANWPeruvians", "ANWPortuguese",
        "ANWRevFrance", "ANWRioGrande", "ANWRomanians", "ANWRussians",
    ],
    "F": [
        # Last 6 ANW civs + 2 ANW filler civs (so all 8 slots have a valid binding).
        # We pick ANWBritish + ANWFrench as fillers since they are core European
        # civs guaranteed to exist; the validator only consumes probes for the
        # primary 6 here.
        "ANWSouthAfricans", "ANWSpanish", "ANWSwedes", "ANWTexians",
        "ANWUSA", "ANWYucatan", "ANWBritish", "ANWFrench",
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
    args.matrix = None
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    template = Path(args.template)
    raw, body = load_scenario(template)
    for label, civs in sorted(PLAYBOOK_MATRIX.items()):
        new_body = set_player_bindings(body, civs, ai_loader=args.ai)
        out = pack_scenario(new_body)
        out_path = out_dir / f"ANW_Coverage_{label}.age3Yscn"
        out_path.write_bytes(out)
        verify_body = zlib.decompress(out[8:])
        # Quick sanity print
        bindings = get_player_bindings(verify_body)
        slot_civs = [hcname_to_civ(b[0]) for b in bindings[1:9]]
        print(f"  {out_path.name}: civs={slot_civs}")
    return 0


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
    """Generate the canonical ANEWWORLD.age3Yscn from the test template.

    8 ANW civs spanning all 6 wall doctrines + Player 1 as a human observer
    seat. Used by tools/validation/exhibition_runner.py and by the user when
    manually loading the scenario for live AI observation.
    """
    template = Path(args.template)
    out_path = Path(args.out)
    raw, body = load_scenario(template)
    new_body = set_player_bindings(
        body, ANEWWORLD_CIVS, ai_loaders=ANEWWORLD_LOADERS
    )
    out = pack_scenario(new_body)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(out)
    verify_body = zlib.decompress(out[8:])
    bindings = get_player_bindings(verify_body)
    print(f"wrote {out_path}  size={len(out)}  body={len(verify_body)}")
    for i, (hc, ai_l, pid) in enumerate(bindings):
        role = "Gaia" if i == 0 else ("HUMAN" if not ai_l else "AI")
        print(f"  slot {i}: pid={pid} role={role:5s} hc={hc!r} ai={ai_l!r}")
    return 0


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
    p_pb.add_argument("--template", required=True)
    p_pb.add_argument("--out-dir", required=True)
    p_pb.add_argument("--ai", default="aiLoaderStandard")
    p_pb.set_defaults(func=cmd_emit_playbook)

    p_aw = sub.add_parser(
        "emit-anewworld",
        help="generate the canonical 8-civ ANEWWORLD.age3Yscn with P1 human + 7 AI",
    )
    p_aw.add_argument("--template", required=True,
                      help="path to _test_template.age3Yscn or a known-good template")
    p_aw.add_argument("--out", required=True,
                      help="output path, typically Scenario/ANEWWORLD.age3Yscn")
    p_aw.set_defaults(func=cmd_emit_anewworld)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
