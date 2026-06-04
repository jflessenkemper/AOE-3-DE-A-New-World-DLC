#!/usr/bin/env python3
"""Poll the harness, screenshot, and emit a single line when the main menu has
rendered (bright frame, not the dark Asset-Preloading splash). Emits on terminal
states only so a Monitor watching this stays silent until something actionable."""
from __future__ import annotations
import sys, time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))
from tools.aoe3_harness.harness_client import HarnessClient  # noqa: E402

SOCK = "/tmp/AOE3DEHarness.sock"
SHOT = REPO / "artifacts" / "harness_probe" / "menu_wait.png"
SHOT.parent.mkdir(parents=True, exist_ok=True)


def mean_lum(png: Path) -> float:
    # Tiny PNG mean-luminance without PIL: use struct via zlib decode is heavy;
    # instead shell out to a minimal approach using the harness PNG + simple parse.
    try:
        from PIL import Image  # type: ignore
        im = Image.open(png).convert("L")
        # downsample for speed
        im = im.resize((64, 36))
        px = list(im.getdata())
        return sum(px) / len(px)
    except Exception:
        return -1.0


def main() -> int:
    deadline = time.time() + 280
    stable = 0
    last = -1.0
    while time.time() < deadline:
        try:
            c = HarnessClient(SOCK)
            c.connect(timeout=10)
            st = c.state()
            c.screenshot(str(SHOT.resolve()))
            c.close()
        except Exception as e:
            print(f"HARNESS_ERR {type(e).__name__}: {e}", flush=True)
            time.sleep(5)
            continue
        lum = mean_lum(SHOT)
        if lum > 28:
            stable += 1
            if stable >= 2:
                print(f"MENU_READY lum={lum:.1f} ready={st.ready}", flush=True)
                return 0
        else:
            stable = 0
        last = lum
        time.sleep(6)
    print(f"TIMEOUT last_lum={last:.1f}", flush=True)
    return 2


if __name__ == "__main__":
    sys.exit(main())
