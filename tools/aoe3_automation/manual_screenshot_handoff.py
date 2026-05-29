#!/usr/bin/env python3
"""manual_screenshot_handoff.py — poll ~/Pictures/anw_handoff/ for user-supplied screenshots.

Usage
-----
1. Run this script (it creates the handoff dir if needed and starts polling).
2. In-game, press F12 (Steam screenshot) or use any other method to capture
   the AoE3 window and drop the PNG/JPG into ~/Pictures/anw_handoff/.
3. The script picks up each new file, copies it to artifacts/visual_confirmation/
   with a timestamp + sequence name, and prints a confirmation line.

Constraints
-----------
- No cursor grab, no Wayland/gamescope protocol, no X11 connection.
- Purely filesystem polling — completely safe under the "no mouse-grab" rule.

Steam F12 screenshots land in:
  ~/.local/share/Steam/userdata/209941315/760/remote/<appid>/screenshots/
For AoE3 DE (app 933110) that directory may not exist yet — Steam auto-creates it
on first screenshot. After pressing F12 you can also copy from there manually.
"""

import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

HANDOFF_DIR = Path.home() / "Pictures" / "anw_handoff"
OUTPUT_DIR = (
    Path(__file__).resolve().parents[2]
    / "artifacts"
    / "visual_confirmation"
)
POLL_INTERVAL_S = 2
SUFFIX_WHITELIST = {".png", ".jpg", ".jpeg"}


def setup_dirs() -> None:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def already_seen(seen: set, path: Path) -> bool:
    return str(path) in seen


def collect(seen: set) -> list[Path]:
    return [
        p
        for p in HANDOFF_DIR.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUFFIX_WHITELIST
        and str(p) not in seen
    ]


def process(path: Path, idx: int) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = OUTPUT_DIR / f"anw_manual_{ts}_{idx:03d}{path.suffix.lower()}"
    shutil.copy2(path, dest)
    return dest


def main() -> None:
    setup_dirs()
    seen: set[str] = set()

    # Seed seen with files already present so we don't re-process old ones.
    for p in HANDOFF_DIR.iterdir():
        if p.is_file() and p.suffix.lower() in SUFFIX_WHITELIST:
            seen.add(str(p))

    print(f"[handoff] Watching {HANDOFF_DIR}")
    print(f"[handoff] Saving captures to {OUTPUT_DIR}")
    print(
        "[handoff] Drop PNG/JPG screenshots into the watch dir, or copy from "
        "~/.local/share/Steam/userdata/209941315/760/remote/933110/screenshots/"
    )
    print("[handoff] Press Ctrl+C to stop.\n")

    idx = 0
    try:
        while True:
            new_files = collect(seen)
            for p in sorted(new_files):
                dest = process(p, idx)
                print(f"[handoff] captured #{idx:03d}  {p.name}  →  {dest}")
                seen.add(str(p))
                idx += 1
            time.sleep(POLL_INTERVAL_S)
    except KeyboardInterrupt:
        print(f"\n[handoff] Stopped. {idx} screenshot(s) saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
