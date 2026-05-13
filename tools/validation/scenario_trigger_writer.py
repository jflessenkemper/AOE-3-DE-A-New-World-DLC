#!/usr/bin/env python3
"""AoE3 DE .age3Yscn TR (trigger) section writer / injector.

This module encodes a parsed TriggerSection (from scenario_trigger_parser) back
to bytes, splices the result into the decompressed scenario body, and drives the
existing scenario_emitter.pack_scenario for the outer l33t/zlib container.

Public API
----------

serialize_tr_payload(sec)           -> bytes
    Re-encodes a TriggerSection to the raw TR payload bytes.  Must round-trip
    byte-for-byte against scenario_trigger_parser.parse_trigger_section input.

replace_tr_section(body, new_tr)    -> bytes
    Splice a fresh TR payload back into the decompressed body, updating the 'TR'
    tag + u32 length prefix.  Returns a new body (uncompressed).  Call
    pack_scenario(new_body) to produce a valid .age3Yscn.

inject_triggers(scn_path, triggers, out_path)
    High-level wrapper: load -> parse -> append triggers -> update header ->
    serialize -> pack -> write.

Constructor helpers
-------------------

make_param(...)        -> Param
make_xs_block(...)     -> XSBlock
make_action(...)       -> Condition | Effect
make_trigger(...)      -> Trigger
make_group(...)        -> TriggerGroup

CLI
---

    python3 scenario_trigger_writer.py noop-roundtrip <in.age3Yscn> <out.age3Yscn>

Parses the TR section, re-encodes it verbatim, and writes a new scenario.  The
decompressed body's TR bytes MUST be bit-identical to the input; the outer file
may differ only due to zlib compression non-determinism.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path
from typing import List, Optional, Union

# ---------------------------------------------------------------------------
# Import from sibling modules.  We deliberately import the parser's dataclasses
# rather than forking them — the writer and parser share the same model.
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.validation.scenario_trigger_parser import (  # noqa: E402
    Condition,
    Effect,
    Param,
    Trigger,
    TriggerGroup,
    TriggerSection,
    XSBlock,
    find_tr_section,
    parse_trigger_section,
)
from tools.validation.scenario_emitter import (  # noqa: E402
    load_scenario,
    pack_scenario,
)


# ---------------------------------------------------------------------------
# Low-level writer.
# ---------------------------------------------------------------------------


class Writer:
    """Stateful little-endian byte accumulator."""

    __slots__ = ("_buf",)

    def __init__(self) -> None:
        self._buf: bytearray = bytearray()

    def u8(self, v: int) -> None:
        self._buf.append(v & 0xFF)

    def u32(self, v: int) -> None:
        self._buf += struct.pack("<I", v)

    def i32(self, v: int) -> None:
        self._buf += struct.pack("<i", v)

    def raw(self, data: bytes) -> None:
        self._buf += data

    def lp_utf8(self, s: str, raw_len: int = -1) -> None:
        """Write a length-prefixed UTF-8 string.

        Layout: u32 length (INCLUDING trailing null) + UTF-8 bytes + null.
        Empty string -> u32 0 only (no null byte, per canonical spec).

        ``raw_len`` is the original u32 length field value as read from disk.
        If ``raw_len == 1`` and ``s == ''``, the non-canonical empty encoding
        ``01 00 00 00 00`` is emitted to preserve byte-for-byte round-trips
        against campaign scenarios that use this form.
        """
        if not s:
            if raw_len == 1:
                # Non-canonical empty: length=1 + single null byte.
                self.u32(1)
                self._buf.append(0)
            else:
                self.u32(0)
            return
        enc = s.encode("utf-8")
        self.u32(len(enc) + 1)   # length includes the null terminator
        self._buf += enc
        self._buf.append(0)      # null terminator

    def lp_utf16(self, s: str) -> None:
        """Write a length-prefixed UTF-16-LE string.

        Layout: u32 char_count + 2*char_count bytes (no terminator).
        Empty string -> u32 0 only.
        """
        if not s:
            self.u32(0)
            return
        enc = s.encode("utf-16-le")
        char_count = len(enc) // 2
        self.u32(char_count)
        self._buf += enc

    def bytes(self) -> bytes:
        return bytes(self._buf)


# ---------------------------------------------------------------------------
# Serialisation helpers (per-record).
# ---------------------------------------------------------------------------


def _write_param(w: Writer, p: Param) -> None:
    w.u32(p.type_tag)
    w.lp_utf8(p.name, raw_len=getattr(p, "_name_raw_len", -1))
    w.lp_utf8(p.display, raw_len=getattr(p, "_disp_raw_len", -1))
    w.u32(p.value_type)
    w.u32(len(p.values))
    if p.value_type == 22:
        # Extra u32 (always 0) between vcount and values — the spec quirk.
        if p.extra:
            w.raw(p.extra)
        else:
            w.u32(0)
    for v in p.values:
        w.lp_utf16(v)


def _write_xs_block(w: Writer, xb: XSBlock) -> None:
    w.lp_utf8(xb.text)
    w.u8(xb.has_deps)
    w.u32(len(xb.deps))
    for dep in xb.deps:
        w.lp_utf8(dep)


def _write_action(w: Writer, action: Union[Condition, Effect]) -> None:
    """Write a Condition or Effect (identical on-wire shape)."""
    w.u32(action.type_tag)
    w.lp_utf8(action.name, raw_len=getattr(action, "_name_raw_len", -1))
    w.lp_utf8(action.display, raw_len=getattr(action, "_disp_raw_len", -1))
    w.u32(len(action.params))
    for p in action.params:
        _write_param(w, p)
    w.lp_utf8(action.eval_expr)
    w.u32(len(action.xs_blocks))
    for xb in action.xs_blocks:
        _write_xs_block(w, xb)


def _write_trigger(w: Writer, t: Trigger) -> None:
    # 4-u32 prefix: (6, trigger_id, prefix[2], prefix[3])
    for v in t.prefix:
        w.u32(v)
    w.lp_utf8(t.name)
    w.i32(t.parent_id)
    w.raw(t.flags)              # 5 raw bytes
    w.u32(len(t.conditions))
    for c in t.conditions:
        _write_action(w, c)
    w.u32(len(t.effects))
    for e in t.effects:
        _write_action(w, e)


def _write_group(w: Writer, g: TriggerGroup) -> None:
    w.u32(1)                    # sentinel — always 1
    w.u32(g.group_id)
    w.lp_utf8(g.name)
    w.u32(len(g.trigger_ids))
    for tid in g.trigger_ids:
        w.u32(tid)


# ---------------------------------------------------------------------------
# Public serialisation API.
# ---------------------------------------------------------------------------


def serialize_tr_payload(sec: TriggerSection) -> bytes:
    """Re-encode a TriggerSection to the raw TR payload bytes.

    Must round-trip byte-for-byte against the input of
    ``scenario_trigger_parser.parse_trigger_section`` when the section was
    parsed from a well-formed file.
    """
    w = Writer()
    # TR_header (20 bytes)
    w.u32(sec.version)
    w.u32(sec.next_id)
    w.u32(sec.unknown_h2)
    w.u32(sec.group_count)
    w.u32(sec.trigger_count)
    # Triggers
    for t in sec.triggers:
        _write_trigger(w, t)
    # TriggerGroupBlock: u32 group_count_block + groups
    # The in-block count is authoritative (the parser warns on mismatch but
    # trusts the block count).  We re-emit len(sec.groups) — the actual parsed
    # group list — so that a section that had a header/block count mismatch
    # still serialises the groups the parser actually kept.
    w.u32(len(sec.groups))
    for g in sec.groups:
        _write_group(w, g)
    return w.bytes()


def replace_tr_section(body: bytes, new_tr_bytes: bytes) -> bytes:
    """Splice a new TR payload into the decompressed body.

    Finds the unique TR sub-record tag, replaces its payload with
    ``new_tr_bytes``, and patches the u32 payload-size field.

    Returns the new body (still uncompressed).  Caller must pass through
    ``pack_scenario`` to produce a valid .age3Yscn.
    """
    tag_off, old_size = find_tr_section(body)
    # body[tag_off..tag_off+2]   = b'TR'
    # body[tag_off+2..tag_off+6] = u32 old_size
    # body[tag_off+6..tag_off+6+old_size] = old payload
    payload_off = tag_off + 6
    before = body[:tag_off]
    after = body[payload_off + old_size:]
    # Build new TR record: tag + u32 new_size + new_payload
    new_size = len(new_tr_bytes)
    new_tr_record = b"TR" + struct.pack("<I", new_size) + new_tr_bytes
    return before + new_tr_record + after


def inject_triggers(
    scn_path: Path,
    triggers: List[Trigger],
    out_path: Path,
    *,
    group_index: int = 0,
) -> None:
    """Load a scenario, append triggers to it, and write the result.

    Each trigger in ``triggers`` is appended to ``sec.triggers``; its id is
    added to ``sec.groups[group_index].trigger_ids``; ``TR_header.trigger_count``
    and ``TR_header.next_id`` are bumped accordingly.

    ``group_index`` selects which TriggerGroup receives the new trigger ids
    (default 0 = 'Ungrouped' in vanilla templates).
    """
    _raw, body = load_scenario(scn_path)
    sec = parse_trigger_section(body)

    for t in triggers:
        # Assign a fresh id if the caller left trigger_id at 0 (the Trigger()
        # default) or if the id would collide with an existing one.
        existing_ids = {x.trigger_id for x in sec.triggers}
        if t.trigger_id == 0 or t.trigger_id in existing_ids:
            t.trigger_id = sec.next_id
            # Keep the prefix in sync: prefix[1] == trigger_id
            t.prefix = (t.prefix[0], t.trigger_id, t.prefix[2], t.prefix[3])

        sec.triggers.append(t)
        sec.next_id = max(sec.next_id, t.trigger_id + 1)
        sec.trigger_count = len(sec.triggers)

        if sec.groups and 0 <= group_index < len(sec.groups):
            sec.groups[group_index].trigger_ids.append(t.trigger_id)

    new_tr_bytes = serialize_tr_payload(sec)
    new_body = replace_tr_section(body, new_tr_bytes)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pack_scenario(new_body))


# ---------------------------------------------------------------------------
# Constructor helpers.
# ---------------------------------------------------------------------------


def make_param(
    name: str,
    display: str,
    *,
    type_tag: int = 2,
    value_type: int = 2,
    values: Optional[List[str]] = None,
) -> Param:
    """Construct a Param dataclass.

    ``values`` defaults to ``['0']`` when not supplied (matches common
    numeric params in BB).  For value_type==22 the caller should supply
    exactly one value and the extra u32 0 is handled automatically by
    the writer.
    """
    if values is None:
        values = ["0"]
    extra = b"\x00\x00\x00\x00" if value_type == 22 else b""
    return Param(type_tag=type_tag, name=name, display=display,
                 value_type=value_type, values=values, extra=extra)


def make_xs_block(
    code: str,
    *,
    deps: Optional[List[str]] = None,
) -> XSBlock:
    """Construct an XSBlock dataclass."""
    if deps is None:
        deps = []
    has_deps = 1 if deps else 0
    return XSBlock(text=code, has_deps=has_deps, deps=deps)


def make_action(
    name: str,
    display: str = "",
    *,
    is_effect: bool = True,
    type_tag: int = 2,
    params: Optional[List[Param]] = None,
    eval_expr: str = "true",
    xs_blocks: Optional[List[XSBlock]] = None,
) -> Union[Condition, Effect]:
    """Construct a Condition or Effect dataclass.

    Use ``is_effect=False`` for conditions.  ``type_tag`` is always 2 in
    observed data; only override if you know what you're doing.
    """
    if params is None:
        params = []
    if xs_blocks is None:
        xs_blocks = []
    cls = Effect if is_effect else Condition
    return cls(
        type_tag=type_tag,
        name=name,
        display=display,
        params=params,
        eval_expr=eval_expr,
        xs_blocks=xs_blocks,
    )


def make_trigger(
    name: str,
    *,
    trigger_id: int = 0,
    parent_id: int = -1,
    flags: Optional[bytes] = None,
    conditions: Optional[List[Condition]] = None,
    effects: Optional[List[Effect]] = None,
) -> Trigger:
    """Construct a Trigger dataclass.

    ``trigger_id=0`` is the sentinel that ``inject_triggers`` replaces with
    ``sec.next_id``.  ``flags`` defaults to the 5-byte value `\\x01\\x00\\x00\\x00\\x00`
    (enabled, no loop, no run-immediately) which matches newly-created triggers
    seen in BB.
    """
    if flags is None:
        flags = b"\x01\x00\x00\x00\x00"
    if conditions is None:
        conditions = []
    if effects is None:
        effects = []
    t = Trigger()
    t.trigger_id = trigger_id
    t.name = name
    t.parent_id = parent_id
    t.flags = flags
    t.conditions = list(conditions)
    t.effects = list(effects)
    t.cond_count = len(conditions)
    t.effect_count = len(effects)
    # prefix[0] must be 6; prefix[1] == trigger_id (may be 0 until inject assigns one)
    nc = len(conditions)
    ne = len(effects)
    t.prefix = (6, trigger_id, nc, ne)
    return t


def make_group(
    name: str,
    *,
    group_id: int = 0,
    trigger_ids: Optional[List[int]] = None,
) -> TriggerGroup:
    """Construct a TriggerGroup dataclass."""
    if trigger_ids is None:
        trigger_ids = []
    return TriggerGroup(group_id=group_id, name=name,
                        trigger_ids=list(trigger_ids))


# ---------------------------------------------------------------------------
# String encoding helpers (also tested directly).
# ---------------------------------------------------------------------------


def encode_lpu8(s: str) -> bytes:
    """Encode a string using lpu8 (length INCLUDING null terminator).

    Empty string -> b'\\x00\\x00\\x00\\x00' (u32 0).
    """
    w = Writer()
    w.lp_utf8(s)
    return w.bytes()


def encode_lpu16(s: str) -> bytes:
    """Encode a string using lpu16 (char count, no terminator).

    Empty string -> b'\\x00\\x00\\x00\\x00' (u32 0).
    """
    w = Writer()
    w.lp_utf16(s)
    return w.bytes()


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def cmd_noop_roundtrip(in_path: Path, out_path: Path) -> int:
    """Decode TR section, re-encode verbatim, and write back."""
    _raw, body = load_scenario(in_path)
    sec = parse_trigger_section(body)
    new_tr_bytes = serialize_tr_payload(sec)

    # Verify round-trip before writing.
    if new_tr_bytes != sec.raw:
        # Report divergence offset for debugging.
        a, b = sec.raw, new_tr_bytes
        diff_pos = next(
            (i for i in range(min(len(a), len(b))) if a[i] != b[i]),
            min(len(a), len(b)),
        )
        print(
            f"WARNING: TR re-encode differs from original at byte {diff_pos} "
            f"(original={len(a)}B new={len(b)}B); writing anyway.",
            file=sys.stderr,
        )

    new_body = replace_tr_section(body, new_tr_bytes)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pack_scenario(new_body))
    print(f"wrote {out_path}  ({len(new_tr_bytes)} TR payload bytes)")
    return 0 if new_tr_bytes == sec.raw else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="AoE3 DE .age3Yscn TR section writer / injector."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_rt = sub.add_parser(
        "noop-roundtrip",
        help="decode TR, re-encode, write (should be byte-identical to input TR bytes)",
    )
    p_rt.add_argument("in_path", type=Path, metavar="in.age3Yscn")
    p_rt.add_argument("out_path", type=Path, metavar="out.age3Yscn")

    args = ap.parse_args(argv)
    if args.cmd == "noop-roundtrip":
        return cmd_noop_roundtrip(args.in_path, args.out_path)
    ap.error(f"unknown command {args.cmd!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
