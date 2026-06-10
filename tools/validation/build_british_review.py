#!/usr/bin/env python3
"""Thin shim — the standalone British review page has been folded into the
unified release-readiness site.  Run this script to rebuild that site instead.

The building-coverage callout (expected_building_filenames vs. captured set)
that used to live here is now rendered inline on each civ's card by
build_release_readiness_site.py :: _render_buildings_strip().
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

print("NOTE: build_british_review.py is a shim.  "
      "The British review is now part of the unified release-readiness site.")
print("Rebuilding unified site…")

result = subprocess.run(
    [sys.executable, str(HERE / "build_release_readiness_site.py")],
    check=False,
)
print(f"Unified site builder exited with code {result.returncode}.")
print("Open: http://127.0.0.1:8765/release_readiness_site.html#card-ANWBritish")
sys.exit(result.returncode)
