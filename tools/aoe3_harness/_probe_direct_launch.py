"""Throwaway probe: launch AoE3 via the DIRECT harness path and screenshot.

Verifies that harness_launch() (direct AOE3DEHarness binary -> umu-run game)
yields a usable control socket AND boots the game far enough to screenshot.
This is the fix-validation for the Steam-launch-options socket bug.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
OUT = REPO / "artifacts" / "harness_probe"
OUT.mkdir(parents=True, exist_ok=True)

from tools.aoe3_harness.harness_launch import harness_launch


def brightness(png: Path) -> float:
    try:
        from PIL import Image
        im = Image.open(png).convert("L").resize((64, 36))
        px = list(im.getdata())
        return sum(px) / len(px)
    except Exception as e:  # noqa: BLE001
        return -1.0


def main() -> int:
    print("[probe] launching game via DIRECT harness path ...", flush=True)
    proc, client = harness_launch(socket_timeout=180.0, connect_timeout=30.0)
    print(f"[probe] harness proc pid={proc.pid}; socket connected", flush=True)
    try:
        st = client.state()
        print(f"[probe] initial STATE: ready={getattr(st,'ready',None)} "
              f"w={getattr(st,'internal_w',None)} h={getattr(st,'internal_h',None)}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[probe] state() err: {e!r}", flush=True)

    # Poll-screenshot as the game boots.
    deadline = time.time() + 260
    shot_i = 0
    last_report = ""
    while time.time() < deadline:
        time.sleep(20)
        shot_i += 1
        p = OUT / f"probe_{shot_i:02d}.png"
        try:
            client.screenshot(str(p))
            b = brightness(p)
            last_report = f"shot {shot_i}: {p.name} brightness={b:.1f}"
            print(f"[probe] {last_report}", flush=True)
            # Non-trivial frame (menu rendered) typically brightness > 25
            if b > 25:
                print(f"[probe] RENDERED FRAME detected (brightness {b:.1f}) — pipeline WORKS", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[probe] screenshot {shot_i} err: {e!r}", flush=True)

    print("[probe] done; leaving harness RUNNING for follow-up driving.", flush=True)
    print(f"[probe] harness pid={proc.pid}", flush=True)
    # Do NOT kill — leave it up so we can drive the lobby next.
    return 0


if __name__ == "__main__":
    sys.exit(main())
