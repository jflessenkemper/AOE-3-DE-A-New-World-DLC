#!/usr/bin/env python3
"""Comprehensive ``.age3Yscn`` binary validator.

This is the long-term gate the team runs on every emitted scenario before
installing it. Catches structural breakage that the engine reports as
"INVALID FILE" before we ever launch the game.

Container layout (post-decompression body):

    file[0:4]   = b'l33t'                      (magic)
    file[4:8]   = uint32_LE outer_size         (== len(body))
    file[8:N]   = zlib stream                  (where N = 8 + zlib_consumed)
    file[N:N+4] = optional 4-byte trailer      (present in every shipped scenario;
                                                value is per-file unique, purpose
                                                not yet reverse-engineered)

    body[0:2]   = b'BG'
    body[2:6]   = uint32_LE inner_size         (== len(body) - 7)
    body[6:10]  = uint32_LE version
    body[10:12] = b'FH'
    ...

Public API
----------

* ``parse(path)`` -> ``ScenarioFile`` — full parse with structural fields.
* ``validate(path, strict=False)`` -> ``list[str]`` — returns issues; empty
  list means valid.
* ``diff(reference_path, candidate_path)`` -> ``DiffReport`` — structural diff.
* ``validate_round_trip(path)`` -> ``RoundTripReport`` — load, repack via
  ``scenario_emitter.pack_scenario``, compare bytes.

CLI
---

::

    python3 validate_scenario_binary.py inspect <file>
    python3 validate_scenario_binary.py validate <file> [--strict]
    python3 validate_scenario_binary.py diff <reference> <candidate>
    python3 validate_scenario_binary.py round-trip <file>

Exits with non-zero status if validation fails.
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


L33T_MAGIC = b"l33t"
BG_MAGIC = b"BG"
FH_MAGIC = b"FH"
DIFF_BLOCK = 16  # diff regions are reported on 16-byte boundaries


# --- Data classes ---------------------------------------------------------


@dataclass
class ScenarioFile:
    """Fully parsed ``.age3Yscn`` container."""

    path: Optional[Path]
    raw: bytes
    outer_size: int             # u32 at file[4:8]
    zlib_stream: bytes          # raw zlib bytes (begin..adler32 inclusive)
    zlib_consumed: int          # len(zlib_stream)
    trailer: bytes              # bytes after zlib stream (0 or 4 bytes typical)
    body: bytes                 # decompressed body
    inner_size: int             # u32 at body[2:6]
    version: int                # u32 at body[6:10]

    @property
    def file_size(self) -> int:
        return len(self.raw)

    @property
    def body_size(self) -> int:
        return len(self.body)

    @property
    def has_trailer(self) -> bool:
        return len(self.trailer) > 0

    @property
    def outer_size_ok(self) -> bool:
        return self.outer_size == len(self.body)

    @property
    def inner_size_ok(self) -> bool:
        return self.inner_size == len(self.body) - 7


@dataclass
class DiffReport:
    """Structural diff between two scenario files."""

    reference: ScenarioFile
    candidate: ScenarioFile
    bodies_identical: bool
    file_size_delta: int             # candidate - reference
    body_size_delta: int             # candidate - reference (bodies)
    differing_regions: List[Tuple[int, int]] = field(default_factory=list)
    # ^ list of (offset, length) on 16-byte aligned blocks where bodies differ
    summary: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        out = []
        out.append("=== Scenario Diff ===")
        out.append(f"  reference : {self.reference.path} ({self.reference.file_size} B)")
        out.append(f"  candidate : {self.candidate.path} ({self.candidate.file_size} B)")
        out.append(f"  file delta: {self.file_size_delta:+d}")
        out.append(f"  body delta: {self.body_size_delta:+d}")
        out.append(f"  bodies byte-identical: {self.bodies_identical}")
        out.append(f"  reference trailer: {self.reference.trailer.hex() or '(none)'}")
        out.append(f"  candidate trailer: {self.candidate.trailer.hex() or '(none)'}")
        if self.differing_regions:
            out.append(f"  body differs in {len(self.differing_regions)} region(s):")
            for off, length in self.differing_regions[:10]:
                out.append(f"    @ 0x{off:08x} len={length}")
            if len(self.differing_regions) > 10:
                out.append(f"    ... ({len(self.differing_regions) - 10} more)")
        for msg in self.summary:
            out.append(f"  {msg}")
        return "\n".join(out)


@dataclass
class RoundTripReport:
    """Pack-roundtrip verification."""

    path: Path
    bodies_identical: bool
    bytes_identical: bool
    diverge_offset: Optional[int]   # first byte index where re-pack differs
    file_size_delta: int            # repacked - source
    summary: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        out = [
            "=== Round-trip Report ===",
            f"  path: {self.path}",
            f"  bodies byte-identical: {self.bodies_identical}",
            f"  files byte-identical:  {self.bytes_identical}",
            f"  file size delta: {self.file_size_delta:+d}",
        ]
        if self.diverge_offset is not None:
            out.append(f"  first divergence @ file byte 0x{self.diverge_offset:x}")
        for s in self.summary:
            out.append(f"  {s}")
        return "\n".join(out)


# --- Parse / validate -----------------------------------------------------


def parse(path: Path | str) -> ScenarioFile:
    """Parse an ``.age3Yscn`` file. Raises ``ValueError`` on structural
    invariants that prevent further parsing (bad magic, malformed zlib)."""
    p = Path(path) if not isinstance(path, Path) else path
    raw = p.read_bytes()
    return parse_bytes(raw, source=p)


def parse_bytes(raw: bytes, source: Optional[Path] = None) -> ScenarioFile:
    if len(raw) < 12:
        raise ValueError(f"file too small ({len(raw)} bytes)")
    if raw[:4] != L33T_MAGIC:
        raise ValueError(f"bad magic {raw[:4]!r}, expected {L33T_MAGIC!r}")
    outer_size = struct.unpack_from("<I", raw, 4)[0]
    decomp = zlib.decompressobj()
    body = decomp.decompress(raw[8:])
    body += decomp.flush()
    if decomp.eof is False:
        raise ValueError("zlib stream did not terminate cleanly")
    consumed = len(raw[8:]) - len(decomp.unused_data)
    zlib_stream = raw[8:8 + consumed]
    trailer = raw[8 + consumed:]
    if len(body) < 12:
        raise ValueError(f"body too small after decompression ({len(body)} bytes)")
    if body[:2] != BG_MAGIC:
        raise ValueError(f"body missing BG magic at offset 0 (got {body[:2]!r})")
    inner_size = struct.unpack_from("<I", body, 2)[0]
    version = struct.unpack_from("<I", body, 6)[0]
    if body[10:12] != FH_MAGIC:
        raise ValueError(f"body missing FH submagic at offset 10 (got {body[10:12]!r})")
    return ScenarioFile(
        path=source,
        raw=raw,
        outer_size=outer_size,
        zlib_stream=zlib_stream,
        zlib_consumed=consumed,
        trailer=trailer,
        body=body,
        inner_size=inner_size,
        version=version,
    )


def validate(path_or_obj, strict: bool = False) -> List[str]:
    """Validate a scenario file's structural invariants.

    Returns a list of issue strings. Empty list = valid.

    With ``strict=True``: also requires a 4-byte trailer to be present
    (every shipped scenario has one) and warns on level / encoder mismatch.
    """
    if isinstance(path_or_obj, ScenarioFile):
        sf = path_or_obj
    else:
        try:
            sf = parse(path_or_obj)
        except ValueError as e:
            return [f"PARSE FAIL: {e}"]

    issues: List[str] = []

    if not sf.outer_size_ok:
        issues.append(
            f"outer_size mismatch: field={sf.outer_size} != actual body len={len(sf.body)} "
            f"(delta={len(sf.body) - sf.outer_size:+d})"
        )
    if not sf.inner_size_ok:
        issues.append(
            f"inner_size mismatch: field={sf.inner_size} != body_len-7={len(sf.body) - 7} "
            f"(delta={len(sf.body) - 7 - sf.inner_size:+d})"
        )
    if len(sf.trailer) not in (0, 4):
        issues.append(
            f"unusual trailer length: {len(sf.trailer)} bytes (expected 0 or 4)"
        )
    if strict:
        if not sf.has_trailer:
            issues.append("strict: no 4-byte trailer present (all shipped scenarios have one)")
        # zlib header / level sanity
        if len(sf.zlib_stream) >= 2:
            cmf, flg = sf.zlib_stream[0], sf.zlib_stream[1]
            if cmf != 0x78:
                issues.append(f"strict: unexpected zlib CMF byte {cmf:#04x} (expected 0x78)")
            # FLG byte tells compression level (bits 6-7): 0=fastest, 1=fast, 2=default, 3=max
            level_bits = (flg >> 6) & 0x3
            if level_bits != 2:
                issues.append(
                    f"strict: zlib level bits = {level_bits} (expected 2 = default/level 6); "
                    f"shipped scenarios use 0x789c"
                )
    return issues


# --- Diff -----------------------------------------------------------------


def diff(reference: Path | str, candidate: Path | str) -> DiffReport:
    """Diff a candidate scenario against a reference scenario."""
    ref = parse(reference) if not isinstance(reference, ScenarioFile) else reference
    cand = parse(candidate) if not isinstance(candidate, ScenarioFile) else candidate
    bodies_identical = (ref.body == cand.body)
    regions: List[Tuple[int, int]] = []
    if not bodies_identical:
        regions = _compute_diff_regions(ref.body, cand.body, DIFF_BLOCK)
    summary = []
    if ref.trailer != cand.trailer:
        summary.append(
            f"trailer differs: ref={ref.trailer.hex() or '(none)'} "
            f"cand={cand.trailer.hex() or '(none)'}"
        )
    if ref.outer_size != cand.outer_size:
        summary.append(
            f"outer_size differs: ref={ref.outer_size} cand={cand.outer_size}"
        )
    if ref.inner_size != cand.inner_size:
        summary.append(
            f"inner_size differs: ref={ref.inner_size} cand={cand.inner_size}"
        )
    if ref.version != cand.version:
        summary.append(f"version differs: ref={ref.version} cand={cand.version}")
    if ref.zlib_stream[:2] != cand.zlib_stream[:2]:
        summary.append(
            f"zlib header differs: ref={ref.zlib_stream[:2].hex()} "
            f"cand={cand.zlib_stream[:2].hex()}"
        )
    if ref.zlib_consumed != cand.zlib_consumed:
        summary.append(
            f"zlib stream length: ref={ref.zlib_consumed} cand={cand.zlib_consumed} "
            f"(delta={cand.zlib_consumed - ref.zlib_consumed:+d}); bodies still "
            f"{'identical' if bodies_identical else 'differ'}"
        )
    return DiffReport(
        reference=ref,
        candidate=cand,
        bodies_identical=bodies_identical,
        file_size_delta=cand.file_size - ref.file_size,
        body_size_delta=cand.body_size - ref.body_size,
        differing_regions=regions,
        summary=summary,
    )


def _compute_diff_regions(a: bytes, b: bytes, block: int) -> List[Tuple[int, int]]:
    """Return list of (offset, length) on `block`-aligned boundaries where
    a and b differ. Coalesces adjacent blocks. Lengths handle a != b in size."""
    regions: List[Tuple[int, int]] = []
    n = max(len(a), len(b))
    cur_start: Optional[int] = None
    i = 0
    while i < n:
        end = min(i + block, n)
        sa = a[i:end] if i < len(a) else b""
        sb = b[i:end] if i < len(b) else b""
        if sa != sb:
            if cur_start is None:
                cur_start = i
        else:
            if cur_start is not None:
                regions.append((cur_start, i - cur_start))
                cur_start = None
        i = end
    if cur_start is not None:
        regions.append((cur_start, n - cur_start))
    return regions


# --- Round-trip ------------------------------------------------------------


def validate_round_trip(path: Path | str) -> RoundTripReport:
    """Load a scenario, re-pack via ``scenario_emitter.pack_scenario`` and
    verify the result is byte-identical to the source."""
    # Lazy import — keeps validator usable even if emitter import fails.
    from tools.validation import scenario_emitter  # noqa: F401

    p = Path(path) if not isinstance(path, Path) else path
    sf = parse(p)
    repacked = scenario_emitter.pack_scenario(sf.body)
    summary: List[str] = []
    bytes_identical = (repacked == sf.raw)
    diverge_offset: Optional[int] = None
    if not bytes_identical:
        for i in range(min(len(repacked), len(sf.raw))):
            if repacked[i] != sf.raw[i]:
                diverge_offset = i
                break
        if diverge_offset is None:
            diverge_offset = min(len(repacked), len(sf.raw))
    bodies_identical = True
    try:
        sf2 = parse_bytes(repacked, source=None)
        bodies_identical = (sf2.body == sf.body)
        if not bodies_identical:
            summary.append("re-pack body decompresses to different bytes (CRITICAL)")
        else:
            if not bytes_identical:
                summary.append(
                    "re-packed bytes differ from source but bodies are byte-identical "
                    "(zlib re-encoder difference)"
                )
            if sf.trailer != sf2.trailer:
                summary.append(
                    f"trailer differs: source={sf.trailer.hex() or '(none)'} "
                    f"repack={sf2.trailer.hex() or '(none)'}"
                )
    except ValueError as e:
        summary.append(f"re-packed file fails to parse: {e}")
    return RoundTripReport(
        path=p,
        bodies_identical=bodies_identical,
        bytes_identical=bytes_identical,
        diverge_offset=diverge_offset,
        file_size_delta=len(repacked) - len(sf.raw),
        summary=summary,
    )


# --- CLI ------------------------------------------------------------------


def cmd_inspect(args: argparse.Namespace) -> int:
    sf = parse(Path(args.file))
    print(f"file: {sf.path}")
    print(f"  size: {sf.file_size} bytes")
    print(f"  outer_size field: {sf.outer_size}")
    print(f"  body size: {sf.body_size}")
    print(f"  outer_size invariant ({sf.outer_size}=={len(sf.body)}): {sf.outer_size_ok}")
    print(f"  inner_size field: {sf.inner_size}")
    print(f"  inner_size invariant ({sf.inner_size}=={len(sf.body)-7}): {sf.inner_size_ok}")
    print(f"  version: {sf.version}")
    print(f"  body magic: {sf.body[:2]!r}  submagic: {sf.body[10:12]!r}")
    print(f"  zlib stream: {sf.zlib_consumed} bytes, header={sf.zlib_stream[:2].hex()}")
    print(f"  trailer: {sf.trailer.hex() or '(none)'} ({len(sf.trailer)} bytes)")
    issues = validate(sf, strict=args.strict)
    if issues:
        print("  ISSUES:")
        for x in issues:
            print(f"    - {x}")
        return 2
    print("  OK")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    issues = validate(Path(args.file), strict=args.strict)
    if not issues:
        print(f"OK: {args.file}")
        return 0
    print(f"FAIL: {args.file}")
    for x in issues:
        print(f"  - {x}")
    return 2


def cmd_diff(args: argparse.Namespace) -> int:
    report = diff(Path(args.reference), Path(args.candidate))
    print(report)
    return 0 if report.bodies_identical else 1


def cmd_round_trip(args: argparse.Namespace) -> int:
    report = validate_round_trip(Path(args.file))
    print(report)
    if not report.bodies_identical:
        return 2
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ins = sub.add_parser("inspect", help="parse and display a scenario's structure")
    p_ins.add_argument("file")
    p_ins.add_argument("--strict", action="store_true",
                       help="fail on missing trailer / non-default zlib level")
    p_ins.set_defaults(func=cmd_inspect)

    p_val = sub.add_parser("validate", help="validate a single scenario")
    p_val.add_argument("file")
    p_val.add_argument("--strict", action="store_true")
    p_val.set_defaults(func=cmd_validate)

    p_diff = sub.add_parser("diff", help="diff a candidate against a reference")
    p_diff.add_argument("reference")
    p_diff.add_argument("candidate")
    p_diff.set_defaults(func=cmd_diff)

    p_rt = sub.add_parser("round-trip", help="verify scenario_emitter.pack_scenario "
                          "round-trips byte-identical")
    p_rt.add_argument("file")
    p_rt.set_defaults(func=cmd_round_trip)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
