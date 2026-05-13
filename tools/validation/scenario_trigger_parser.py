#!/usr/bin/env python3
"""AoE3 DE .age3Yscn TRIGGER section parser.

Reverse-engineered from
  Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn (104 triggers,
  11 trigger groups) and cross-checked against
  Scenario/_test_template.age3Yscn (0 triggers, 1 empty group) and
  Scenario/ANEWWORLD.age3Yscn (0 triggers, 1 empty group).

The trigger section lives in the decompressed body as a tagged sub-record
with the 2-byte tag b'TR' followed by a uint32 little-endian payload size.

    body[off..off+2]   = b'TR'
    body[off+2..off+6] = u32 size
    body[off+6..off+6+size] = payload

There is **exactly one TR record per scenario** (validated by scanning
multiple templates). The TR payload starts with a 5-u32 section header
(version=9, next_id, unknown, group_count, trigger_count), followed by all
triggers in serialisation order, followed by the trigger-groups block.

This file is a parser (no writer / generator yet). Run as:

    python3 scenario_trigger_parser.py dump /path/to/scenario.age3Yscn
    python3 scenario_trigger_parser.py list /path/to/scenario.age3Yscn

The full format spec is in SCENARIO_TRIGGER_FORMAT.md (this directory).
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Container helpers (delegates to scenario_emitter for round-trip safety).
# ---------------------------------------------------------------------------

# We import lazily so that this file can be used as a stand-alone reader even
# when scenario_emitter.py is missing.
def _load_body(path: Path) -> bytes:
    try:
        from scenario_emitter import load_scenario  # type: ignore
        _raw, body = load_scenario(path)
        return body
    except Exception:
        raw = path.read_bytes()
        if raw[:4] != b"l33t":
            raise ValueError(f"{path}: bad magic, not an .age3Yscn")
        return zlib.decompress(raw[8:])


# ---------------------------------------------------------------------------
# Low-level reader.
# ---------------------------------------------------------------------------


class Reader:
    """Stateful little-endian byte reader. Tracks an offset into a buffer."""

    __slots__ = ("buf", "pos")

    def __init__(self, buf: bytes, pos: int = 0) -> None:
        self.buf = buf
        self.pos = pos

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.buf, self.pos)[0]
        self.pos += 4
        return v

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.buf, self.pos)[0]
        self.pos += 4
        return v

    def u8(self) -> int:
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def take(self, n: int) -> bytes:
        v = bytes(self.buf[self.pos:self.pos + n])
        self.pos += n
        return v

    def lp_utf8(self) -> str:
        """Read a length-prefixed UTF-8 string. Length is u32 INCLUDING the
        trailing null byte. Returns the string without the null."""
        n = self.u32()
        if n == 0:
            return ""
        raw = self.take(n)
        if raw[-1] != 0:
            # Some short strings (e.g. trigger-group sentinel) may have no
            # trailing null. Treat as raw.
            return raw.decode("utf-8", errors="replace")
        return raw[:-1].decode("utf-8", errors="replace")

    def lp_utf8_raw(self) -> Tuple[str, int]:
        """Like lp_utf8 but also returns the raw u32 length prefix value.

        This is needed to round-trip the non-canonical empty-string encoding
        used in some campaign scenarios: ``01 00 00 00 00`` (length=1 with just
        a null byte) encodes the empty string but differs on-wire from the
        canonical ``00 00 00 00`` (length=0).  Callers that need byte-perfect
        re-serialisation must use this method and store the returned raw_len.
        """
        n = self.u32()
        if n == 0:
            return "", 0
        raw = self.take(n)
        if raw[-1] != 0:
            return raw.decode("utf-8", errors="replace"), n
        return raw[:-1].decode("utf-8", errors="replace"), n

    def lp_utf16(self) -> str:
        """Read a length-prefixed UTF-16-LE string. Length is u32 = CHAR
        count. No trailing null in the wire format."""
        n = self.u32()
        if n == 0:
            return ""
        raw = self.take(2 * n)
        return raw.decode("utf-16-le", errors="replace")


# ---------------------------------------------------------------------------
# Data classes.
# ---------------------------------------------------------------------------


class Param:
    """One named parameter of a condition or effect."""

    __slots__ = ("type_tag", "name", "display", "value_type", "values", "extra",
                 "_name_raw_len", "_disp_raw_len")

    def __init__(
        self,
        type_tag: int,
        name: str,
        display: str,
        value_type: int,
        values: List[str],
        extra: bytes = b"",
        _name_raw_len: int = -1,
        _disp_raw_len: int = -1,
    ) -> None:
        self.type_tag = type_tag
        self.name = name
        self.display = display
        self.value_type = value_type
        self.values = values  # UTF-16 strings (engine parses to int/float/etc)
        # `extra` holds the type-specific bonus field. For value_type=22 it is
        # the u32 "0" that follows vcount=1. For other types it is empty.
        self.extra = extra
        # Raw length-prefix values preserved for byte-perfect re-serialisation.
        # -1 means "not recorded" (use canonical encoding).  For empty strings,
        # some campaign files use 1 (null-only byte) instead of 0.
        self._name_raw_len = _name_raw_len
        self._disp_raw_len = _disp_raw_len

    def __repr__(self) -> str:
        v = repr(self.values) if len(self.values) <= 4 else f"[{len(self.values)} vals]"
        e = f" extra={self.extra.hex()}" if self.extra else ""
        return (
            f"Param(name={self.name!r}, disp={self.display!r}, "
            f"vtype={self.value_type}, vals={v}{e})"
        )


class XSBlock:
    """An XS script string embedded after a cond/effect's eval_expr.

    BB scenarios serialise the *expanded* XS code that the editor emits when
    you drop an effect on a trigger (e.g. `trUnitSelectClear();`,
    `trUnitMoveToUnit("%DstObject%", ...)`). The engine re-expands these at
    runtime by substituting %ParamName% with the matching Param.values.

    Each XS block is followed by a small trailer:
        [u8 has_deps]
        [u32 dep_count]
        [lp_utf8 dep_name] * dep_count
    `deps` enumerates the parameter names this XS expression substitutes."""

    __slots__ = ("text", "has_deps", "deps")

    def __init__(self, text: str, has_deps: int, deps: List[str]) -> None:
        self.text = text
        self.has_deps = has_deps
        self.deps = deps  # parameter names this script references

    def __repr__(self) -> str:
        snippet = self.text if len(self.text) <= 60 else self.text[:57] + "..."
        return f"XSBlock(deps={self.deps!r}, text={snippet!r})"


class Condition:
    """One condition inside a Trigger.

    A condition is a typed action with name/display, a list of parameters,
    an XS eval expression returning bool, and a list of XS preamble blocks
    that prepare the runtime state. The trigger fires when eval_expr
    evaluates true."""

    __slots__ = ("type_tag", "name", "display", "params", "eval_expr", "xs_blocks",
                 "_name_raw_len", "_disp_raw_len")

    def __init__(
        self,
        type_tag: int,
        name: str,
        display: str,
        params: List[Param],
        eval_expr: str,
        xs_blocks: List[XSBlock],
        _name_raw_len: int = -1,
        _disp_raw_len: int = -1,
    ) -> None:
        self.type_tag = type_tag
        self.name = name
        self.display = display
        self.params = params
        self.eval_expr = eval_expr
        self.xs_blocks = xs_blocks
        self._name_raw_len = _name_raw_len
        self._disp_raw_len = _disp_raw_len

    def __repr__(self) -> str:
        return (
            f"Condition(name={self.name!r}, disp={self.display!r}, "
            f"params={len(self.params)}, xs={len(self.xs_blocks)})"
        )


class Effect:
    """One effect inside a Trigger.

    Effects share the on-wire layout with Conditions: name/display, params,
    an eval_expr (usually "true"), and a list of XS blocks that run when
    the trigger fires."""

    __slots__ = ("type_tag", "name", "display", "params", "eval_expr", "xs_blocks",
                 "_name_raw_len", "_disp_raw_len")

    def __init__(
        self,
        type_tag: int,
        name: str,
        display: str,
        params: List[Param],
        eval_expr: str,
        xs_blocks: List[XSBlock],
        _name_raw_len: int = -1,
        _disp_raw_len: int = -1,
    ) -> None:
        self.type_tag = type_tag
        self.name = name
        self.display = display
        self.params = params
        self.eval_expr = eval_expr
        self.xs_blocks = xs_blocks
        self._name_raw_len = _name_raw_len
        self._disp_raw_len = _disp_raw_len

    def __repr__(self) -> str:
        return (
            f"Effect(name={self.name!r}, disp={self.display!r}, "
            f"params={len(self.params)}, xs={len(self.xs_blocks)})"
        )


class Trigger:
    """One Trigger record."""

    __slots__ = (
        "abs_off", "size", "prefix", "trigger_id", "name", "parent_id",
        "flags", "cond_count", "conditions",
        "effect_count", "effects", "raw",
    )

    def __init__(self) -> None:
        self.abs_off: int = 0      # absolute offset within the body
        self.size: int = 0         # bytes consumed
        self.prefix: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self.trigger_id: int = 0
        self.name: str = ""
        self.parent_id: int = -1
        self.flags: bytes = b""
        self.cond_count: int = 0
        self.conditions: List[Condition] = []
        self.effect_count: int = 0
        self.effects: List[Effect] = []
        self.raw: bytes = b""

    def __repr__(self) -> str:
        return (
            f"Trigger(id={self.trigger_id}, name={self.name!r}, "
            f"parent={self.parent_id}, conds={self.cond_count}, "
            f"effects={self.effect_count}, size={self.size})"
        )


class TriggerGroup:
    __slots__ = ("group_id", "name", "trigger_ids")

    def __init__(self, group_id: int, name: str, trigger_ids: List[int]) -> None:
        self.group_id = group_id
        self.name = name
        self.trigger_ids = trigger_ids

    def __repr__(self) -> str:
        return (
            f"TriggerGroup(id={self.group_id}, name={self.name!r}, "
            f"triggers={len(self.trigger_ids)})"
        )


class TriggerSection:
    """Parsed contents of the TR sub-record."""

    __slots__ = (
        "off", "size", "version", "next_id", "unknown_h2",
        "group_count", "trigger_count", "triggers", "groups", "raw",
    )

    def __init__(self) -> None:
        self.off: int = 0
        self.size: int = 0
        self.version: int = 0
        self.next_id: int = 0
        self.unknown_h2: int = 0
        self.group_count: int = 0
        self.trigger_count: int = 0
        self.triggers: List[Trigger] = []
        self.groups: List[TriggerGroup] = []
        self.raw: bytes = b""


# ---------------------------------------------------------------------------
# Locating the TR section in the body.
# ---------------------------------------------------------------------------


def find_tr_section(body: bytes) -> Tuple[int, int]:
    """Locate the unique TR sub-record in the body.

    Returns (absolute_offset_of_tag, payload_size).
    """
    cur = 0
    candidates: List[Tuple[int, int, int]] = []
    while True:
        i = body.find(b"TR", cur)
        if i < 0:
            break
        cur = i + 1
        if i + 6 > len(body):
            continue
        size = struct.unpack_from("<I", body, i + 2)[0]
        if size < 24 or i + 6 + size > len(body):
            continue
        # First 4 bytes of payload must be u32 version (always 9 in observed scenarios).
        v = struct.unpack_from("<I", body, i + 6)[0]
        if v not in (9,):
            continue
        # The next two u32s are next_id and "unknown_h2"; the 4th is
        # group_count (1..1000) and the 5th is trigger_count (0..10000).
        gc = struct.unpack_from("<I", body, i + 6 + 12)[0]
        tc = struct.unpack_from("<I", body, i + 6 + 16)[0]
        if not (0 < gc < 1000):
            continue
        if not (0 <= tc < 10000):
            continue
        candidates.append((i, size, gc + tc))
    if not candidates:
        raise ValueError("no TR section found in body")
    if len(candidates) > 1:
        # Prefer the largest plausible one (real scenarios only have one).
        candidates.sort(key=lambda t: -t[1])
    return candidates[0][0], candidates[0][1]


# ---------------------------------------------------------------------------
# Trigger walking.
# ---------------------------------------------------------------------------


def _parse_param(r: Reader) -> Param:
    """Parse one [type_tag, name, display, value_type, vcount, values...] block.

    Most value_types use [u32 vcount][lp_utf16 * vcount]. Value-type 22
    (LocalizedStringID, used by Msg/Subtitle/StringID/Text) inserts an
    extra u32=0 between vcount and the values."""
    type_tag = r.u32()
    name, name_raw_len = r.lp_utf8_raw()
    display, disp_raw_len = r.lp_utf8_raw()
    value_type = r.u32()
    vcount = r.u32()
    extra = b""
    if value_type == 22:
        # Extra u32 (always observed as 0) between vcount and values.
        extra = r.take(4)
    values: List[str] = []
    for _ in range(vcount):
        values.append(r.lp_utf16())
    return Param(type_tag, name, display, value_type, values, extra,
                 _name_raw_len=name_raw_len, _disp_raw_len=disp_raw_len)


def _parse_xs_block(r: Reader) -> XSBlock:
    """Parse one XS script block:
        [lp_utf8 code]
        [u8 has_deps]
        [u32 dep_count]
        [lp_utf8 dep_name] * dep_count
    """
    code = r.lp_utf8()
    has_deps = r.u8()
    dep_count = r.u32()
    deps: List[str] = []
    for _ in range(dep_count):
        deps.append(r.lp_utf8())
    return XSBlock(code, has_deps, deps)


def _parse_cond_or_effect(r: Reader, is_effect: bool):
    """Parse a single condition or effect. The on-wire layout is identical.
    Returns Condition or Effect (depending on `is_effect`)."""
    type_tag = r.u32()  # observed: always 2
    name, name_raw_len = r.lp_utf8_raw()
    display, disp_raw_len = r.lp_utf8_raw()
    param_count = r.u32()
    params = [_parse_param(r) for _ in range(param_count)]
    eval_expr = r.lp_utf8()
    xs_count = r.u32()
    xs_blocks = [_parse_xs_block(r) for _ in range(xs_count)]
    if is_effect:
        return Effect(type_tag, name, display, params, eval_expr, xs_blocks,
                      _name_raw_len=name_raw_len, _disp_raw_len=disp_raw_len)
    return Condition(type_tag, name, display, params, eval_expr, xs_blocks,
                     _name_raw_len=name_raw_len, _disp_raw_len=disp_raw_len)


def parse_trigger(buf: bytes, off: int, payload_end: int) -> Tuple[Trigger, int]:
    """Parse one trigger starting at absolute body offset `off`.

    Returns (trigger, next_off) where next_off is the offset immediately
    after the parsed trigger.
    """
    r = Reader(buf, off)
    t = Trigger()
    t.abs_off = off
    t.prefix = (r.u32(), r.u32(), r.u32(), r.u32())
    t.trigger_id = t.prefix[1]
    t.name = r.lp_utf8()
    t.parent_id = r.i32()
    t.flags = r.take(5)
    t.cond_count = r.u32()
    for _ in range(t.cond_count):
        t.conditions.append(_parse_cond_or_effect(r, is_effect=False))
    t.effect_count = r.u32()
    for _ in range(t.effect_count):
        t.effects.append(_parse_cond_or_effect(r, is_effect=True))
    t.size = r.pos - off
    t.raw = bytes(buf[off:r.pos])
    return t, r.pos


def parse_groups(buf: bytes, start: int, end: int, group_count: int) -> Tuple[List[TriggerGroup], int]:
    """Parse the trigger-groups block.

    Layout:
        [u32 group_count_block]    ; usually equals header.group_count, but
                                   ;   some campaign maps (age3challenges02)
                                   ;   record one fewer. The block count
                                   ;   wins.
        per group:
            [u32 = 1 (sentinel)]
            [u32 group_id]
            [u32 name_len] [name + null]
            [u32 trig_count]
            [u32 trig_id] * trig_count
    """
    r = Reader(buf, start)
    actual_count = r.u32()
    # Trust the count in the block over the header (verified across multiple
    # campaign scenarios -- some have a 1-off mismatch with the header).
    if actual_count != group_count and 0 < actual_count <= group_count + 4:
        group_count = actual_count
    groups: List[TriggerGroup] = []
    for _ in range(group_count):
        sent = r.u32()
        gid = r.u32()
        name = r.lp_utf8()
        tc = r.u32()
        ids = [r.u32() for _ in range(tc)]
        groups.append(TriggerGroup(group_id=gid, name=name, trigger_ids=ids))
        _ = sent  # sentinel observed as 1
    return groups, r.pos


def parse_trigger_section(body: bytes) -> TriggerSection:
    """Top-level entry point: locate and parse the TR sub-record."""
    tag_off, size = find_tr_section(body)
    payload_off = tag_off + 6
    payload_end = payload_off + size
    sec = TriggerSection()
    sec.off = tag_off
    sec.size = size
    sec.raw = bytes(body[payload_off:payload_end])

    r = Reader(body, payload_off)
    sec.version = r.u32()
    sec.next_id = r.u32()
    sec.unknown_h2 = r.u32()
    sec.group_count = r.u32()
    sec.trigger_count = r.u32()

    cur = r.pos
    triggers: List[Trigger] = []
    while cur < payload_end and len(triggers) < sec.trigger_count:
        # Sanity check: prefix u32 must be 6.
        if struct.unpack_from("<I", body, cur)[0] != 6:
            break
        t, cur = parse_trigger(body, cur, payload_end)
        triggers.append(t)
    sec.triggers = triggers

    # Groups follow.
    if sec.group_count > 0:
        sec.groups, _ = parse_groups(body, cur, payload_end, sec.group_count)
    return sec


# ---------------------------------------------------------------------------
# CLI / pretty-printing.
# ---------------------------------------------------------------------------


def _hexdump(data: bytes, base: int = 0, max_lines: int = 16) -> str:
    out = []
    for i in range(0, min(len(data), max_lines * 16), 16):
        chunk = data[i:i + 16]
        hex_ = " ".join(f"{b:02x}" for b in chunk)
        ascii_ = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{base + i:08x}  {hex_:<48s}  {ascii_}")
    if len(data) > max_lines * 16:
        out.append(f"... ({len(data) - max_lines * 16} more bytes)")
    return "\n".join(out)


def dump(sec: TriggerSection, max_triggers: int = 3) -> str:
    out = []
    out.append("=" * 72)
    out.append(
        f"TR section @ 0x{sec.off:x}  payload_size={sec.size}  "
        f"version={sec.version}"
    )
    out.append(
        f"next_id={sec.next_id}  unknown_h2={sec.unknown_h2}  "
        f"group_count={sec.group_count}  trigger_count={sec.trigger_count}"
    )
    out.append(f"parsed: {len(sec.triggers)} triggers, {len(sec.groups)} groups")
    out.append("=" * 72)
    for i, t in enumerate(sec.triggers[:max_triggers]):
        out.append("")
        out.append(f"--- Trigger {i+1}/{len(sec.triggers)} {t!r} ---")
        out.append(
            f"  prefix={t.prefix}  parent_id={t.parent_id}  "
            f"flags={t.flags.hex()}"
        )
        for ci, c in enumerate(t.conditions):
            out.append(f"  cond[{ci}] {c!r}")
            for p in c.params:
                out.append(f"      {p!r}")
            out.append(f"      eval_expr={c.eval_expr!r}")
            for xi, xb in enumerate(c.xs_blocks):
                out.append(f"      xs[{xi}] {xb!r}")
        for ei, e in enumerate(t.effects):
            out.append(f"  effect[{ei}] {e!r}")
            for p in e.params:
                out.append(f"      {p!r}")
            out.append(f"      eval_expr={e.eval_expr!r}")
            for xi, xb in enumerate(e.xs_blocks):
                out.append(f"      xs[{xi}] {xb!r}")
        out.append("  raw[0:128]:")
        out.append(_hexdump(t.raw[:128], base=t.abs_off, max_lines=8))
    if len(sec.triggers) > max_triggers:
        # Always also list remaining triggers as 1-line summaries
        out.append("")
        out.append(f"... remaining {len(sec.triggers) - max_triggers} triggers (summary):")
        for t in sec.triggers[max_triggers:]:
            out.append(f"  id={t.trigger_id:4d}  name={t.name!r}")
    if sec.groups:
        out.append("")
        out.append("Trigger groups:")
        for g in sec.groups:
            ids = g.trigger_ids[:8]
            tail = "..." if len(g.trigger_ids) > 8 else ""
            out.append(
                f"  id={g.group_id:3d} name={g.name!r:24s} "
                f"({len(g.trigger_ids)} triggers) {ids}{tail}"
            )
    return "\n".join(out)


def cmd_dump(path: Path, max_triggers: int) -> int:
    body = _load_body(path)
    sec = parse_trigger_section(body)
    print(dump(sec, max_triggers=max_triggers))
    return 0


def cmd_list(path: Path) -> int:
    body = _load_body(path)
    sec = parse_trigger_section(body)
    print(f"# {path.name}: {sec.trigger_count} triggers in {sec.group_count} groups")
    for t in sec.triggers:
        print(f"  id={t.trigger_id:4d}  parent={t.parent_id:4d}  "
              f"conds={t.cond_count} effects={t.effect_count}  name={t.name!r}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Parse the TR (trigger) sub-record of an .age3Yscn scenario."
    )
    sub = ap.add_subparsers(dest="cmd", required=False)

    p_dump = sub.add_parser("dump", help="parse + pretty-print (default)")
    p_dump.add_argument("path", type=Path)
    p_dump.add_argument(
        "--max", type=int, default=3, dest="max_triggers",
        help="number of triggers to print fully (default 3)",
    )

    p_list = sub.add_parser("list", help="list trigger IDs and names only")
    p_list.add_argument("path", type=Path)

    # Allow `scenario_trigger_parser.py /path/to/file` shorthand.
    args = ap.parse_args(argv)
    if args.cmd is None:
        # Backwards-compatible default: treat first positional as path
        if argv and len(argv) >= 1 and not argv[0].startswith("-"):
            return cmd_dump(Path(argv[0]), max_triggers=3)
        ap.error("subcommand required (use 'dump' or 'list')")
    if args.cmd == "dump":
        return cmd_dump(args.path, args.max_triggers)
    if args.cmd == "list":
        return cmd_list(args.path)
    ap.error(f"unknown command {args.cmd!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
