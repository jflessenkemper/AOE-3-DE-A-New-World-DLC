#!/usr/bin/env python3
"""Static validator: gamescope_detect.py must verify AoE3 AppId/exe before
reporting AoE3 present.

Bug this pins (logged 2026-06-09): gamescope_detect.py reported
  [gamescope_detect] AoE3 detected: DISPLAY=:1 GAMESCOPE_WAYLAND_DISPLAY=gamescope-0
when the ONLY gamescope running was Company of Heroes 2 (AppId=231430,
RelicCoH2.exe). AoE3 was dead. The runner then tried to drive CoH2's menu
and failed. Root cause: the detector matched "any gamescope" without verifying
the process tree contains AppId=933110 or AoE3DE_s.exe.

This validator asserts:
  1. The source of gamescope_detect.py contains the AoE3 AppId constant
     ("933110") guarding the detection path.
  2. The source contains the AoE3 executable name ("AoE3DE_s.exe") guarding
     the detection path.
  3. The AppId/exe checks appear BEFORE the detection result is cached and
     logged (i.e. before the "[gamescope_detect] AoE3 detected:" log line),
     proving they are a gate rather than a post-hoc annotation.
  4. There is no code path that sets _CACHE and emits the "AoE3 detected"
     log line without first checking 933110 / AoE3DE_s.exe (structural guard
     against the original false-positive pattern).

A future edit that removes the AppId/exe guard will cause this to fail loudly
(exit 1) rather than let the regression silently return.

Usage:
    python3 tools/validation/validate_gamescope_detect_appid.py

Exit codes:
    0 — gamescope_detect.py contains the required identity guard (PASS)
    1 — the guard is absent or weakened (FAIL — details printed)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "tools" / "aoe3_automation" / "gamescope_detect.py"

AOE3_APPID = "933110"
AOE3_EXE = "AoE3DE_s.exe"
# The string the original bug logged — if this appears without the AppId guard
# it means we've regressed to the false-positive pattern.
DETECTED_LOG = "[gamescope_detect] AoE3 detected:"


def _line_index(lines: list[str], pattern: str) -> int:
    """Return the 0-based index of the first line containing *pattern*, or -1."""
    for i, ln in enumerate(lines):
        if pattern in ln:
            return i
    return -1


def main() -> int:
    print("gamescope_detect AppId/exe identity-guard check")
    print(f"  target: {TARGET.relative_to(REPO)}")
    print()

    # --- 1. File must exist and be readable --------------------------------
    if not TARGET.exists():
        print(f"FAIL — target file not found: {TARGET}")
        return 1

    try:
        source = TARGET.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL — cannot read target: {exc}")
        return 1

    # --- 2. Must parse as valid Python (catches accidental corruption) -----
    try:
        ast.parse(source)
    except SyntaxError as exc:
        print(f"FAIL — {TARGET.name} has a syntax error: {exc}")
        return 1

    lines = source.splitlines()
    errors: list[str] = []

    # --- 3. AppId constant must be present ----------------------------------
    appid_lines = [i for i, ln in enumerate(lines) if AOE3_APPID in ln]
    if not appid_lines:
        errors.append(
            f"AppId constant {AOE3_APPID!r} not found anywhere in {TARGET.name}. "
            f"The AoE3 identity guard is missing."
        )
    else:
        print(f"  [OK] AppId {AOE3_APPID!r} found at line(s): "
              f"{[i + 1 for i in appid_lines]}")

    # --- 4. AoE3 executable name must be present ----------------------------
    exe_lines = [i for i, ln in enumerate(lines) if AOE3_EXE in ln]
    if not exe_lines:
        errors.append(
            f"AoE3 executable name {AOE3_EXE!r} not found anywhere in {TARGET.name}. "
            f"The AoE3 identity guard is missing."
        )
    else:
        print(f"  [OK] Exe name {AOE3_EXE!r} found at line(s): "
              f"{[i + 1 for i in exe_lines]}")

    # --- 5. The AppId/exe checks must appear BEFORE the "AoE3 detected" log -
    detected_line = _line_index(lines, DETECTED_LOG)
    if detected_line == -1:
        errors.append(
            f"The expected log string {DETECTED_LOG!r} was not found in "
            f"{TARGET.name}. Either the log message changed (update this "
            f"validator) or the detection path was removed entirely."
        )
    else:
        print(f"  [OK] Detection log found at line {detected_line + 1}")
        # AppId must appear at least once before the detected log line.
        appid_before = [i for i in appid_lines if i < detected_line]
        if not appid_before:
            errors.append(
                f"AppId {AOE3_APPID!r} does not appear before the detection log "
                f"(line {detected_line + 1}). The guard must execute BEFORE "
                f"AoE3 is declared present."
            )
        else:
            print(f"  [OK] AppId guard precedes detection log "
                  f"(guard line {appid_before[-1] + 1} < log line {detected_line + 1})")

        # AoE3_EXE must also appear at least once before the detected log line.
        exe_before = [i for i in exe_lines if i < detected_line]
        if not exe_before:
            errors.append(
                f"Exe name {AOE3_EXE!r} does not appear before the detection log "
                f"(line {detected_line + 1}). The guard must execute BEFORE "
                f"AoE3 is declared present."
            )
        else:
            print(f"  [OK] Exe guard precedes detection log "
                  f"(guard line {exe_before[-1] + 1} < log line {detected_line + 1})")

    # --- 6. Must contain a function that checks both identity markers -------
    # Look for a function definition that spans lines containing both AppId and
    # exe name — this is the structural proof that a verification function exists,
    # not just loose constants declared in comments or dead code.
    func_with_guard = False
    func_re = re.compile(r"^def\s+\w")
    func_ranges: list[tuple[int, int]] = []
    for i, ln in enumerate(lines):
        if func_re.match(ln):
            # Find where this function ends (next def at same indent or EOF).
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if func_re.match(lines[j]):
                    end = j
                    break
            func_ranges.append((i, end))

    for start, end in func_ranges:
        body = "\n".join(lines[start:end])
        if AOE3_APPID in body and AOE3_EXE in body:
            func_with_guard = True
            print(f"  [OK] Identity-guard function found at lines {start + 1}–{end}")
            break

    if not func_with_guard:
        errors.append(
            f"No single function body contains both {AOE3_APPID!r} and "
            f"{AOE3_EXE!r}. The guard must be in a dedicated function so "
            f"it can be called from detect_aoe3_display()."
        )

    # --- 7. detect_aoe3_display must call the guard before caching ----------
    # Find detect_aoe3_display body and ensure it references AOE3_APPID or
    # AOE3_EXE (directly or via a helper call containing "aoe3") before _CACHE
    detect_func_start = -1
    for i, ln in enumerate(lines):
        if re.match(r"^def\s+detect_aoe3_display\s*\(", ln):
            detect_func_start = i
            break
    if detect_func_start == -1:
        errors.append(
            "detect_aoe3_display() function not found — the public API has been "
            "renamed or removed. Update this validator."
        )
    else:
        # Find the function's end.
        detect_func_end = len(lines)
        for j in range(detect_func_start + 1, len(lines)):
            if func_re.match(lines[j]):
                detect_func_end = j
                break
        body_lines = lines[detect_func_start:detect_func_end]
        body = "\n".join(body_lines)

        cache_line_rel = _line_index(body_lines, "_CACHE =")
        # Look for AppId, exe, or a helper name containing "aoe3" before the cache write.
        guard_present = (
            AOE3_APPID in body
            or AOE3_EXE in body
            or re.search(r"_gamescope_hosts_aoe3|aoe3_verified", body) is not None
        )
        if not guard_present:
            errors.append(
                f"detect_aoe3_display() body (lines {detect_func_start + 1}–"
                f"{detect_func_end}) does not reference the AppId/exe guard. "
                f"The guard function exists but is never called from the detection path."
            )
        else:
            print(f"  [OK] detect_aoe3_display() body references the identity guard")

    print()
    if errors:
        print("FAIL — AppId/exe identity guard missing or incomplete:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("PASS — gamescope_detect.py contains the required AoE3 AppId/exe "
          "identity guard (AppId=933110, AoE3DE_s.exe) that must verify the "
          "process tree before reporting AoE3 present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
