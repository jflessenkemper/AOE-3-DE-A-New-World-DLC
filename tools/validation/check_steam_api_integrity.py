#!/usr/bin/env python3
"""Check that AoE3 DE's steam_api64.dll is the legitimate Valve SDK.

The 2026-05-11 0x5 incident was caused by a Goldberg/CreamAPI-style
Steam emulator DLL sitting where the real Valve SDK should be:

    steam_api64.dll          1,452,032 bytes, Aug 12 2019  ← emulator
    steam_api64.dll.original   288,032 bytes, May  8 2026  ← real SDK

AoE3 DE hash-checks steam_api64.dll very early in PreGame (after the
memory-report block but before mod-load). When the hash doesn't match
it pops "Fatal Error: one or more game files is invalid. Error code:
0x5" and the Age3Log freezes at exactly 16 lines — and crucially the
mod system never engages, so disabling the mod does not help.

This validator flags `steam_api64.dll` if any of these red flags hit:

    * file size outside [200 KB, 600 KB]
      (legit SDK is ~288 KB; emulators tend to be 1+ MB)
    * mtime older than 2020-09-01 (AoE3 DE release)
    * missing the `Software\\Valve\\Steam` registry string
    * presence of GoldbergSteam / cream_api / SteamEmu / SmartSteamEmu
      marker strings

Exit code is 0 on PASS, 1 on FAIL. Designed to be cheap to call from
the release-readiness pipeline.

Usage:
    python3 tools/validation/check_steam_api_integrity.py
    python3 tools/validation/check_steam_api_integrity.py --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

DEFAULT_DLL = Path(
    "/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/steam_api64.dll"
)
MIN_SIZE = 200 * 1024
MAX_SIZE = 600 * 1024
GAME_RELEASE = dt.date(2020, 9, 1)
EXPECTED_STR = b"Software\\Valve\\Steam"
EMULATOR_MARKERS = (
    b"GoldbergSteam",
    b"goldberg_emu",
    b"cream_api",
    b"CreamAPI",
    b"SteamEmu",
    b"SmartSteamEmu",
    b"SmartSteamLoader",
    b"RLD!",
)


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except Exception as e:  # noqa: BLE001
        return f"__read_error__:{e}".encode()


def check(dll: Path) -> dict:
    result = {
        "path": str(dll),
        "exists": dll.exists(),
        "checks": [],
        "pass": True,
    }
    if not dll.exists():
        result["pass"] = False
        result["checks"].append({"name": "exists", "ok": False, "detail": "missing"})
        return result

    st = dll.stat()
    size = st.st_size
    mtime = dt.date.fromtimestamp(st.st_mtime)
    blob = _read_bytes(dll)

    # 1) size
    size_ok = MIN_SIZE <= size <= MAX_SIZE
    result["checks"].append(
        {
            "name": "size",
            "ok": size_ok,
            "detail": f"{size} bytes (expected {MIN_SIZE}-{MAX_SIZE})",
        }
    )

    # 2) mtime
    mtime_ok = mtime >= GAME_RELEASE
    result["checks"].append(
        {
            "name": "mtime",
            "ok": mtime_ok,
            "detail": f"{mtime.isoformat()} (expected ≥ {GAME_RELEASE.isoformat()})",
        }
    )

    # 3) Valve signature string
    valve_ok = EXPECTED_STR in blob
    result["checks"].append(
        {
            "name": "valve_signature",
            "ok": valve_ok,
            "detail": "Software\\Valve\\Steam present"
            if valve_ok
            else "Software\\Valve\\Steam MISSING",
        }
    )

    # 4) emulator markers
    hits = [m.decode("latin1") for m in EMULATOR_MARKERS if m in blob]
    emu_ok = not hits
    result["checks"].append(
        {
            "name": "no_emulator_markers",
            "ok": emu_ok,
            "detail": "none" if emu_ok else f"FOUND: {hits}",
        }
    )

    result["pass"] = all(c["ok"] for c in result["checks"])
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dll",
        type=Path,
        default=DEFAULT_DLL,
        help=f"path to steam_api64.dll (default: {DEFAULT_DLL})",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    r = check(args.dll)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        verdict = "PASS" if r["pass"] else "FAIL"
        print(f"[{verdict}] {r['path']}")
        for c in r["checks"]:
            tag = "ok" if c["ok"] else "FAIL"
            print(f"  [{tag}] {c['name']}: {c['detail']}")
        if not r["pass"]:
            print()
            print(
                "FIX: a backup of the legit DLL is usually parked next to "
                "the active one as 'steam_api64.dll.original'. Restore with:"
            )
            print(
                "  cd /home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE"
            )
            print("  cp steam_api64.dll steam_api64.dll.emulator-backup")
            print("  cp steam_api64.dll.original steam_api64.dll")
            print(
                "If no '.original' exists, ask Steam to re-verify game files "
                "(Library → AoE3 DE → Properties → Installed Files → "
                "Verify integrity of game files)."
            )
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
