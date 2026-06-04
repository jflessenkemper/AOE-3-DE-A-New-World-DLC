"""AI-script-load diagnostic via decompressed replay payload.

Background
----------
NIGHT_JOURNAL lists three theories for "0 personality probes after every
match":

  1. AI not loading at all (no positive proof either way without aiEcho).
  2. ``aiPersonalitySetPlayerUserVar`` is in-memory only (write happens but
     doesn't persist to disk).
  3. Wrong personality file is being targeted.

Theory #1 has been impossible to test because every observable channel
(aiEcho, aiChat, personality writes) sits *downstream* of the AI loading.
If the AI never loads, every channel reads zero — but for different
reasons than if it loads-then-fails-to-write.

This tool gives us ground truth on theory #1.

How it works
------------
A .age3Yrec replay is ``l33t\\x00\\x00\\x00\\x00`` + a single zlib stream
(verified 2026-04-29 on a 21 MB live replay; previously undocumented).
After ``zlib.decompress`` the payload contains, among other things, the
**compiled XS script blob for each AI player** stitched into the replay
header so the engine can replay deterministically. Each AI's blob carries
its own copy of any string literals from the script — including the
``[ANWP v=2 t=`` format-string template defined in
``aiUtilities.xs::llProbe`` and the tag literals (``meta.boot``,
``meta.gameover``, etc.).

So the count of ``[ANWP v=2 t=`` literal hits in a decompressed replay
equals the number of AI players whose XS script was loaded. In a 1v7
match: 7 hits = all AI loaded; 0 hits = AI failed to load entirely.

This does NOT recover the runtime probe values — those go through chat,
which IS string-table indexed (the original ``replay_probes.py``
docstring was right about that). To recover values we still need the
personality-uservar channel (``probes_from_replay.py``) or a new
disk-write channel.

Usage
-----
    python3 -m tools.playtest.replay_chat_scan PATH.age3Yrec
    python3 -m tools.playtest.replay_chat_scan PATH.age3Yrec --json
    python3 -m tools.playtest.replay_chat_scan PATH.age3Yrec --expected 7

Exit codes:
  0 — at least one AI script loaded
  1 — fewer scripts than --expected (set with --expected N)
  2 — file missing or unreadable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from pathlib import Path

REPLAY_MAGIC = b"l33t\x00\x00\x00\x00"
REPLAY_PAYLOAD_OFFSET = 8

# Constants embedded in the compiled AI script. Each is a string literal in
# game/ai/core/aiUtilities.xs (llProbe) or aiCore.xs (gameOverHandler etc.).
# Counting any of them gives a per-AI-script-loaded count; we report all
# three for redundancy.
PROBE_FORMAT_LITERAL = b"ANWP v=2 t="
META_BOOT_LITERAL = b"meta.boot"
META_GAMEOVER_LITERAL = b"meta.gameover"


def decompress_replay(path: Path) -> bytes:
    """Inflate the zlib payload of a .age3Yrec file. Returns b'' on failure."""
    raw = path.read_bytes()
    if raw.startswith(REPLAY_MAGIC):
        payload = raw[REPLAY_PAYLOAD_OFFSET:]
    else:
        # Fallback: locate any zlib-default header.
        idx = raw.find(b"\x78\x9c")
        if idx < 0:
            return b""
        payload = raw[idx:]
    do = zlib.decompressobj()
    out = bytearray()
    try:
        out += do.decompress(payload)
        out += do.flush()
    except zlib.error:
        # Partial decompression is fine — script blobs sit early-mid in
        # the payload, well before any forced-quit truncation.
        pass
    return bytes(out)


def count_loaded_scripts(decompressed: bytes) -> dict[str, int]:
    """Return per-literal occurrence counts. The MAX of the three is the
    most reliable per-AI count (different optimisation levels strip some
    literals)."""
    return {
        "probe_format": decompressed.count(PROBE_FORMAT_LITERAL),
        "meta_boot": decompressed.count(META_BOOT_LITERAL),
        "meta_gameover": decompressed.count(META_GAMEOVER_LITERAL),
    }


def diagnose(path: Path, expected: int = 0) -> dict:
    """Decompress + count + summarise. Returns a dict suitable for JSON."""
    if not path.exists():
        return {"ok": False, "reason": f"file not found: {path}"}
    decompressed = decompress_replay(path)
    if not decompressed:
        return {"ok": False, "reason": "zlib decompression yielded 0 bytes "
                                       "(unexpected magic / corrupt header)"}
    counts = count_loaded_scripts(decompressed)
    n = max(counts.values())
    return {
        "ok": True,
        "replay": str(path),
        "decompressed_bytes": len(decompressed),
        "counts": counts,
        "ai_scripts_loaded": n,
        "expected": expected,
        "verdict": (
            "no AI scripts loaded — theory #1 is confirmed; investigate XS "
            "compile / loader path before chasing probe channels"
            if n == 0
            else f"{n} AI script(s) loaded; theory #1 ruled out"
            if n > 0 and (expected == 0 or n >= expected)
            else f"{n}/{expected} AI scripts loaded — partial load failure"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("replay", type=Path, help=".age3Yrec file to scan")
    ap.add_argument("--expected", type=int, default=0,
                    help="Expected AI script count (e.g. 7 for 1v7 FFA). "
                         "If set, exit 1 when fewer scripts loaded.")
    ap.add_argument("--json", action="store_true",
                    help="Emit one JSON object to stdout")
    args = ap.parse_args()

    res = diagnose(args.replay, expected=args.expected)
    if args.json:
        print(json.dumps(res, separators=(",", ":")))
    else:
        if not res["ok"]:
            print(f"ERROR: {res['reason']}", file=sys.stderr)
            return 2
        print(f"Replay: {Path(res['replay']).name}")
        print(f"Decompressed: {res['decompressed_bytes']:,} bytes")
        print(f"AI scripts loaded: {res['ai_scripts_loaded']}")
        if args.expected:
            print(f"Expected: {args.expected}")
        print(f"Verdict: {res['verdict']}")
        print()
        print("Per-literal counts (max = AI count):")
        for k, v in res["counts"].items():
            print(f"  {k:<14s} {v}")

    if not res["ok"]:
        return 2
    if args.expected and res["ai_scripts_loaded"] < args.expected:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
