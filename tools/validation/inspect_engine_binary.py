#!/usr/bin/env python3
"""
inspect_engine_binary.py
Static analysis of AoE3DE_s.exe to find the "Inventory" scenario-load gate
and any config-flag bypass.

Re-runnable. Reads the binary, writes findings as markdown fragments to stdout
and (optionally) appends to scenario_load_bypass.md when --update is passed.

Usage:
    python3 inspect_engine_binary.py [--update]
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM, CS_OP_MEM

BINARY = Path("/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe")
DOC = Path(__file__).resolve().parent / "scenario_load_bypass.md"

# Strings of interest — exact substrings (bytes) to locate in the file.
TARGET_STRINGS: list[bytes] = [
    b"Unlock Error - Inventory %s%d",
    b"Unlock Error - Unable to process inventory for %lld",
    b"Inventory Extended",
    b"InvalidFileDialog-prompt",
    b"loadScenario",
    b"uiScenarioLoad",
    b"validatechecksum",
    b"noPregameScenario",
    b"noPregameRecording",
]

# Candidate config-flag tokens we *hope* exist as bypass switches.
CANDIDATE_BYPASS_FLAGS: list[bytes] = [
    b"noinventory",
    b"noscenariosig",
    b"nodrm",
    b"bypassinventory",
    b"skipsignature",
    b"skipinventory",
    b"fakeinventory",
    b"nointegritycheck",
    b"developermode",
    b"developer",
    b"nounlock",
    b"unlockall",
    b"allunlocked",
    b"unlockedall",
    b"skipunlock",
    b"nounlockcheck",
    b"bypassunlock",
    b"freeplay",
    b"debugmode",
    b"nochecksum",
    b"skipchecksum",
    b"disableinventory",
    b"disabledrm",
    b"disablecheck",
    b"unlocked",
    b"allcontent",
    b"forceunlock",
    b"skipdrm",
]


def load_pe() -> pefile.PE:
    return pefile.PE(str(BINARY), fast_load=False)


def section_at_rva(pe: pefile.PE, rva: int):
    return pe.get_section_by_rva(rva)


def rva_to_offset(pe: pefile.PE, rva: int) -> int:
    return pe.get_offset_from_rva(rva)


def offset_to_rva(pe: pefile.PE, off: int) -> int:
    return pe.get_rva_from_offset(off)


def find_all(haystack: bytes, needle: bytes) -> list[int]:
    """Return file-offsets of every occurrence of needle (allow embedded NULs)."""
    out: list[int] = []
    start = 0
    while True:
        i = haystack.find(needle, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def is_string_terminated(data: bytes, off: int, length: int) -> bool:
    """Heuristic: ensure offset+length is at a C-string boundary."""
    if off + length >= len(data):
        return False
    return data[off + length] in (0, 0x20)


def cstr_at(data: bytes, off: int, max_len: int = 256) -> str:
    end = data.find(b"\x00", off, off + max_len)
    if end < 0:
        end = off + max_len
    try:
        return data[off:end].decode("utf-8", errors="replace")
    except Exception:
        return ""


def find_riprel_xrefs(raw: bytes, sections: list, image_base: int, target_va: int,
                      max_results: int = 64) -> list[tuple[int, int, int, bytes, str]]:
    """Fast scan over .text* sections for RIP-relative refs to `target_va`.
    Recognises common patterns:
      48/4C 8D ?? d32     LEA r64, [rip+d32]      (7 bytes)  REX.W or REX.WR
      48/4C 8B ?? d32     MOV r64, [rip+d32]      (7 bytes)
      48/4C 89 ?? d32     MOV [rip+d32], r64      (7 bytes)
      4? 39 / 3B ?? d32   CMP variants            (7 bytes)
      8D ?? d32           LEA r32, [rip+d32]      (6 bytes)
      8B ?? d32           MOV r32, [rip+d32]      (6 bytes)
      0F B6 ?? d32        MOVZX r32, byte ptr...  (7 bytes)
      0F B7 ?? d32        MOVZX r32, word ptr...  (7 bytes)
      FF 15 d32           CALL qword ptr [rip+d32](6 bytes)
      FF 25 d32           JMP  qword ptr [rip+d32](6 bytes)
      E8 d32              CALL rel32              (5 bytes) — only if target is code
      E9 d32              JMP  rel32              (5 bytes)
    Returns list of (file_off, instr_va, instr_len, bytes, mnemonic).
    """
    out: list[tuple[int, int, int, bytes, str]] = []

    def emit(foff: int, va: int, ln: int, bs: bytes, kind: str):
        out.append((foff, va, ln, bs, kind))

    for s in sections:
        name = s.Name.rstrip(b"\x00")
        if not name.startswith(b".text"):
            continue
        sec_foff = s.PointerToRawData
        sec_vsize = min(s.Misc_VirtualSize, s.SizeOfRawData)
        sec_rva = s.VirtualAddress
        end = sec_foff + sec_vsize

        i = sec_foff
        while i < end - 7:
            b0 = raw[i]
            b1 = raw[i + 1]
            # 7-byte REX-prefixed LEA / MOV / etc with rip-relative modrm
            if b0 in (0x48, 0x49, 0x4C, 0x4D, 0x4A, 0x4E):
                # length 7: REX + opcode + modrm + disp32
                if b1 in (0x8D, 0x8B, 0x89, 0x39, 0x3B, 0x85):
                    modrm = raw[i + 2]
                    if (modrm & 0xC7) == 0x05:
                        disp = int.from_bytes(raw[i + 3:i + 7], "little", signed=True)
                        instr_va = image_base + sec_rva + (i - sec_foff)
                        if instr_va + 7 + disp == target_va:
                            mnem = {0x8D: "lea", 0x8B: "mov-load", 0x89: "mov-store",
                                    0x39: "cmp", 0x3B: "cmp", 0x85: "test"}[b1]
                            emit(i, instr_va, 7, raw[i:i + 7], mnem)
                            if len(out) >= max_results:
                                return out
                # length 8: 0F B6/B7 movzx
                if b1 == 0x0F and i + 8 <= end:
                    b2 = raw[i + 2]
                    if b2 in (0xB6, 0xB7, 0xBE, 0xBF):
                        modrm = raw[i + 3]
                        if (modrm & 0xC7) == 0x05:
                            disp = int.from_bytes(raw[i + 4:i + 8], "little", signed=True)
                            instr_va = image_base + sec_rva + (i - sec_foff)
                            if instr_va + 8 + disp == target_va:
                                emit(i, instr_va, 8, raw[i:i + 8], "movzx/movsx")
                                if len(out) >= max_results:
                                    return out
            # 6-byte (no REX) LEA r32 / MOV r32 with rip-relative
            if b0 in (0x8D, 0x8B):
                modrm = raw[i + 1]
                if (modrm & 0xC7) == 0x05:
                    disp = int.from_bytes(raw[i + 2:i + 6], "little", signed=True)
                    instr_va = image_base + sec_rva + (i - sec_foff)
                    if instr_va + 6 + disp == target_va:
                        mnem = "lea32" if b0 == 0x8D else "mov32"
                        emit(i, instr_va, 6, raw[i:i + 6], mnem)
                        if len(out) >= max_results:
                            return out
            # FF 15 / FF 25 — call/jmp [rip+d32]
            if b0 == 0xFF and b1 in (0x15, 0x25):
                disp = int.from_bytes(raw[i + 2:i + 6], "little", signed=True)
                instr_va = image_base + sec_rva + (i - sec_foff)
                if instr_va + 6 + disp == target_va:
                    emit(i, instr_va, 6, raw[i:i + 6], "call/jmp[rip]")
                    if len(out) >= max_results:
                        return out
            # E8/E9 rel32 — only emit if target is in code section
            if b0 in (0xE8, 0xE9):
                disp = int.from_bytes(raw[i + 1:i + 5], "little", signed=True)
                instr_va = image_base + sec_rva + (i - sec_foff)
                if instr_va + 5 + disp == target_va:
                    emit(i, instr_va, 5, raw[i:i + 5], "call/jmp rel32")
                    if len(out) >= max_results:
                        return out
            i += 1
    return out


def find_xrefs_to_va(pe: pefile.PE, code: bytes, code_rva: int, image_base: int, target_va: int,
                     md: Cs, max_results: int = 32) -> list[tuple[int, str]]:
    """Disassemble .text and find instructions whose absolute operand resolves to target_va."""
    hits: list[tuple[int, str]] = []
    for ins in md.disasm(code, image_base + code_rva):
        # Check immediate operands and rip-relative memory operands.
        try:
            for op in ins.operands:
                if op.type == CS_OP_IMM and op.imm == target_va:
                    hits.append((ins.address, f"{ins.mnemonic} {ins.op_str}"))
                    break
                if op.type == CS_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                    # Capstone resolves rip-relative as displacement = absolute target
                    # for x86_64 only when base == X86_REG_RIP; check if address matches.
                    pass
            # Also catch rip-relative LEA whose target is target_va.
            if "rip" in ins.op_str:
                # Parse displacement: e.g. "rax, [rip + 0x1234]" or "rip - 0x1234"
                m = re.search(r"\[rip\s*([+-])\s*0x([0-9a-fA-F]+)\]", ins.op_str)
                if m:
                    sign = 1 if m.group(1) == "+" else -1
                    disp = sign * int(m.group(2), 16)
                    eff = ins.address + ins.size + disp
                    if eff == target_va:
                        hits.append((ins.address, f"{ins.mnemonic} {ins.op_str}"))
        except Exception:
            pass
        if len(hits) >= max_results:
            break
    return hits


def section_entropy(data: bytes) -> float:
    """Shannon entropy of `data` in bits-per-byte (0..8)."""
    if not data:
        return 0.0
    import math
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    e = 0.0
    for c in counts:
        if c:
            p = c / n
            e -= p * math.log2(p)
    return e


def disasm_probe(raw: bytes, pe: pefile.PE, image_base: int, n_lines: int = 8) -> None:
    """Disassemble the entry point and the first .pdata-listed function start
    to confirm whether `.text` is plaintext code or encrypted/packed."""
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = False

    ep_rva = pe.OPTIONAL_HEADER.AddressOfEntryPoint
    ep_foff = pe.get_offset_from_rva(ep_rva)
    ep_va = image_base + ep_rva
    print(f"\n[probe] entry point  rva=0x{ep_rva:x}  va=0x{ep_va:x}  foff=0x{ep_foff:x}")
    for n, ins in enumerate(md.disasm(raw[ep_foff:ep_foff + 64], ep_va)):
        print(f"    0x{ins.address:x}  {ins.bytes.hex():<22} {ins.mnemonic} {ins.op_str}")
        if n + 1 >= n_lines:
            break

    # First .pdata RUNTIME_FUNCTION
    pdata = next((s for s in pe.sections if s.Name.rstrip(b"\x00") == b".pdata"), None)
    if pdata:
        d = pdata.get_data()
        import struct
        for idx in (1, 100):
            begin, end, _ = struct.unpack_from("<III", d, idx * 12)
            if not begin:
                continue
            foff = pe.get_offset_from_rva(begin)
            va = image_base + begin
            print(f"\n[probe] pdata fn[{idx}]  rva=0x{begin:x}  va=0x{va:x}  "
                  f"foff=0x{foff:x}  bytes={raw[foff:foff + 16].hex()}")
            for n, ins in enumerate(md.disasm(raw[foff:foff + 48], va)):
                print(f"    0x{ins.address:x}  {ins.bytes.hex():<22} {ins.mnemonic} {ins.op_str}")
                if n + 1 >= n_lines:
                    break


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true",
                    help="append findings to scenario_load_bypass.md")
    ap.add_argument("--xref", action="store_true",
                    help="run expensive disasm xref pass for inventory format string")
    ap.add_argument("--xref-limit", type=int, default=0,
                    help="byte limit on .text scan (0 = full)")
    ap.add_argument("--brute-xref", action="store_true",
                    help="brute-force scan: try every plausible instruction "
                         "length and look for any disp32 that resolves to the "
                         "target VA. Slow but catches every encoding variant.")
    args = ap.parse_args()

    pe = load_pe()
    image_base = pe.OPTIONAL_HEADER.ImageBase
    print(f"[i] image base: 0x{image_base:x}")
    print(f"[i] sections: {len(pe.sections)}")
    raw = BINARY.read_bytes()
    for s in pe.sections:
        name = s.Name.rstrip(b"\x00").decode("ascii", errors="replace")
        seg = raw[s.PointerToRawData:s.PointerToRawData
                                    + min(s.SizeOfRawData, 0x40000)]
        ent = section_entropy(seg)
        print(f"    {name:<10} rva=0x{s.VirtualAddress:08x} "
              f"vsize=0x{s.Misc_VirtualSize:08x} rsize=0x{s.SizeOfRawData:08x} "
              f"foff=0x{s.PointerToRawData:08x}  entropy={ent:.3f}")

    print(f"[i] file size: {len(raw):,} bytes")
    disasm_probe(raw, pe, image_base)

    # --- locate target strings ---
    print("\n[A] target string locations:")
    string_locs: dict[bytes, list[int]] = {}
    for needle in TARGET_STRINGS:
        offs = find_all(raw, needle)
        string_locs[needle] = offs
        for off in offs[:8]:
            ctx = cstr_at(raw, off, 200)
            try:
                rva = offset_to_rva(pe, off)
                va = image_base + rva
            except Exception:
                rva, va = -1, -1
            print(f"    {needle!r}")
            print(f"      foff=0x{off:08x} rva=0x{rva:08x} va=0x{va:x}")
            print(f"      ctx: {ctx[:160]!r}")

    # --- candidate flags ---
    print("\n[B] candidate config-flag tokens:")
    flag_hits: dict[bytes, list[int]] = {}
    for tok in CANDIDATE_BYPASS_FLAGS:
        offs = find_all(raw, tok)
        if not offs:
            continue
        flag_hits[tok] = offs
        for off in offs[:5]:
            ctx = cstr_at(raw, off, 80)
            try:
                rva = offset_to_rva(pe, off)
                va = image_base + rva
            except Exception:
                rva, va = -1, -1
            print(f"    {tok!r:>30}  foff=0x{off:08x}  va=0x{va:x}  ctx={ctx[:80]!r}")

    # --- xref pass for the Inventory format string ---
    if args.xref:
        # We do a fast LEA-rip-relative scan against several relevant strings.
        targets = [
            b"Unlock Error - Inventory %s%d",
            b"Unlock Error - Unable to process inventory for %lld",
            b"Unlock Error - Detach %s%d",
            b"InvalidFileDialog-prompt",
            b"Extended:",
            b"loadScenario",
            b"uiScenarioLoad",
        ]
        for needle in targets:
            offs = string_locs.get(needle, [])
            if not offs:
                continue
            for s_off in offs:
                try:
                    target_va = image_base + offset_to_rva(pe, s_off)
                except Exception:
                    continue
                hits = find_riprel_xrefs(raw, pe.sections, image_base, target_va)
                if not hits and not args.brute_xref:
                    print(f"\n[C] {needle!r} @ va=0x{target_va:x}  (0 xrefs)")
                    continue
                if hits:
                    print(f"\n[C] {needle!r} @ va=0x{target_va:x}  ({len(hits)} xrefs)")
                    for foff, va, length, bs, mnem in hits:
                        print(f"    {mnem:<14} foff=0x{foff:08x} va=0x{va:x} bytes={bs.hex()}")
                if args.brute_xref:
                    bcnt = 0
                    for s in pe.sections:
                        if not s.Name.rstrip(b"\x00").startswith(b".text"):
                            continue
                        sf = s.PointerToRawData
                        sz = min(s.Misc_VirtualSize, s.SizeOfRawData)
                        for ilen in (5, 6, 7, 8):
                            for i in range(sf, sf + sz - 4):
                                disp = int.from_bytes(raw[i:i + 4],
                                                      "little", signed=True)
                                istart = i - (ilen - 4)
                                if istart < sf:
                                    continue
                                instr_va = (image_base + s.VirtualAddress +
                                            (istart - sf))
                                if instr_va + ilen + disp == target_va:
                                    bcnt += 1
                                    if bcnt <= 5:
                                        print(f"    BRUTE ilen={ilen} "
                                              f"foff=0x{istart:08x} "
                                              f"va=0x{instr_va:x} "
                                              f"bytes="
                                              f"{raw[istart:istart + ilen].hex()}")
                    print(f"    BRUTE total: {bcnt}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
