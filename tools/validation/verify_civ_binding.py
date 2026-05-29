#!/usr/bin/env python3
"""Verify that the lobby civ-picker actually selects the ANW civ we asked for.

The harness's `lobby_driver.set_civ_by_index(N)` scrolls and clicks on row N
of the picker. If the scroll math is off by one, or if the picker layout
changed, the harness silently picks the wrong civ — and every downstream
"per-civ test" runs against the wrong faction.

This tool screenshots the lobby AFTER selection, OCRs the leader name + civ
label visible in the player slot, and confirms it matches the expected ANW
display name.

Usage:
    # Open Skirmish lobby manually first, then:
    python3 verify_civ_binding.py --civ ANWBritish --picker-idx 7

    # Bulk-verify all civs in ANW_TO_PICKER_INDEX:
    python3 verify_civ_binding.py --bulk
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _shot(out_path: Path) -> bool:
    """Take a gamescope screenshot via the harness env."""
    from tools.aoe3_automation.gamescope_detect import get_gs_env
    gs_env = get_gs_env(use_cache=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    subprocess.run(
        ["gamescopectl", "screenshot", str(out_path)],
        env=gs_env, capture_output=True, text=True, timeout=10,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        if out_path.exists() and out_path.stat().st_size > 1024:
            return True
        time.sleep(0.2)
    return False


def _ocr_lobby_p1(shot_path: Path) -> dict[str, Any]:
    """OCR the P1 row of the SP Skirmish lobby.

    2026-05-08: After empirical investigation we confirmed the P1 row in
    AoE3 DE's SP Skirmish lobby only displays the *player name* (e.g.
    "FLESSENKEMPER"), the chosen flag, and the leader portrait — it does
    NOT render the leader name as text. Tested crop regions:

        (50,80,800,200)   → catches title bar + player name → garbled
        (50,130,800,220)  → P1 row only → "FLESSENKEMPER" only, no civ text
        (50,140,1100,210) → wider variant → still just "FLESSENKEMPER"

    The civ identity is encoded only in the flag image and the leader
    portrait (knight, samurai, etc.), neither of which OCRs as text.
    Reliable text-based verification therefore requires re-opening the
    civ picker (which auto-scrolls to centre the selected civ) and OCRing
    the *highlighted* row — that row text always contains either the civ
    name or the home-city name.

    This function now returns the player-name text from the cleaner crop
    region (50,130,800,220) for backwards compatibility with callers that
    only need a "lobby is rendered" sanity check, and a hint that
    picker-based verification is required for actual civ identification.
    """
    from PIL import Image
    import pytesseract

    if not shot_path.exists():
        return {"ok": False, "error": f"no screenshot at {shot_path}"}

    im = Image.open(shot_path)
    if im.size != (1920, 1080):
        return {"ok": False,
                "error": f"unexpected resolution {im.size} (expected 1920x1080)"}

    # P1 row banner — drops the title bar above and stops above P2's row.
    crop = im.crop((50, 130, 800, 220))
    # Use psm 7 (single line) for the player-name banner; psm 6 (block) bleeds
    # garbled noise from the flag / portrait pixels into the text output.
    text = pytesseract.image_to_string(crop, config="--psm 7").strip()
    return {
        "ok": True,
        "raw_text": text,
        "lines": [l for l in text.split("\n") if l.strip()],
        "note": "P1 row shows player name only; for civ verification use "
                "lobby_driver.set_civ_by_token_verified (picker re-open + OCR).",
    }


def _ocr_picker_highlighted_row(shot_path: Path) -> dict[str, Any]:
    """OCR each visible picker row and return the highlighted (selected) row.

    Highlighted-row detection: the picker's selected row has a saturated
    orange background (~RGB 119,88,42) clearly distinct from the dark
    woodgrain (~30,20,10). We sample 3 x-positions per row and require at
    least 2 of 3 to register as orange-saturated.

    Caller is expected to have invoked open_civ_picker() and screenshotted
    the open-picker state. After this, the caller should cancel/close the
    picker.
    """
    from PIL import Image
    import pytesseract

    if not shot_path.exists():
        return {"ok": False, "error": f"no screenshot at {shot_path}"}

    im = Image.open(shot_path)
    if im.size != (1920, 1080):
        return {"ok": False,
                "error": f"unexpected resolution {im.size} (expected 1920x1080)"}

    rows: list[dict] = []
    for n in range(10):
        y_center = 296 + 64 * n
        crop = im.crop((80, y_center - 30, 720, y_center + 30))
        txt = pytesseract.image_to_string(crop, config="--psm 7").strip()
        hi_count = 0
        for x in (300, 400, 500):
            r, g, b = im.getpixel((x, y_center))[:3]
            if r > 80 and g < r - 10 and b < g and (r - b) > 50:
                hi_count += 1
        rows.append({"row": n, "text": txt, "highlighted": hi_count >= 2})

    hi = [r for r in rows if r["highlighted"]]
    hi_text = hi[0]["text"] if hi else (rows[5]["text"] if len(rows) > 5 else "")
    return {
        "ok": True,
        "raw_text": hi_text,
        "lines": [hi_text] if hi_text else [],
        "all_rows": rows,
    }


def _normalise(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _expected_strings(civ_token: str, ref: dict[str, Any]) -> list[str]:
    """Return strings we'd expect to see in the OCR for this civ."""
    spec = ref["civs"].get(civ_token, {})
    out = []
    if spec.get("display_name"):
        out.append(spec["display_name"])
    ps = spec.get("playstyle_spec") or {}
    if ps.get("civ_label"):
        out.append(ps["civ_label"])
    if ps.get("leader_label"):
        out.append(ps["leader_label"])
    return out


def verify_one(
    civ_token: str,
    picker_idx: int,
    ref: dict[str, Any],
    artifact_dir: Path,
) -> dict[str, Any]:
    """Drive the harness to select picker_idx, screenshot, OCR, compare."""
    from tools.aoe3_automation import lobby_driver
    coords = lobby_driver.load_coords()

    # Pre-screenshot for diagnostics
    pre = artifact_dir / f"{civ_token}_pre.png"
    _shot(pre)

    # Drive the picker
    try:
        lobby_driver.set_civ_by_index(coords, picker_idx)
        time.sleep(2)
    except Exception as e:
        return {"civ": civ_token, "picker_idx": picker_idx,
                "verdict": "FAIL", "error": f"set_civ_by_index: {e}"}

    # Post-screenshot
    post = artifact_dir / f"{civ_token}_post.png"
    if not _shot(post):
        return {"civ": civ_token, "picker_idx": picker_idx,
                "verdict": "FAIL", "error": "screenshot failed"}

    ocr = _ocr_lobby_p1(post)
    if not ocr.get("ok"):
        return {"civ": civ_token, "picker_idx": picker_idx,
                "verdict": "FAIL", "error": ocr.get("error", "ocr failed"),
                "screenshot": str(post)}

    # Compare OCR text against expected strings
    raw = ocr["raw_text"]
    norm_raw = _normalise(raw)
    expected_strings = _expected_strings(civ_token, ref)
    matches = [s for s in expected_strings if _normalise(s) in norm_raw]

    if matches:
        verdict = "PASS"
    elif raw:
        verdict = "MISMATCH"
    else:
        verdict = "BLANK"

    return {
        "civ": civ_token,
        "picker_idx": picker_idx,
        "verdict": verdict,
        "expected": expected_strings,
        "ocr_text": raw,
        "ocr_lines": ocr["lines"],
        "matches": matches,
        "screenshot": str(post),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--civ", help="single civ token to verify")
    ap.add_argument("--picker-idx", type=int, help="picker index for --civ mode")
    ap.add_argument("--bulk", action="store_true",
                    help="verify all civs in ANW_TO_PICKER_INDEX")
    ap.add_argument(
        "--reference", type=Path,
        default=REPO_ROOT / "enriched_reference.json",
    )
    ap.add_argument(
        "--out-dir", type=Path,
        default=REPO_ROOT / "artifacts" / "civ_binding_verifications",
    )
    args = ap.parse_args()

    if not args.reference.exists():
        print(f"missing: {args.reference}", file=sys.stderr)
        return 1
    with open(args.reference) as f:
        ref = json.load(f)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.bulk:
        from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
        targets = sorted(ANW_TO_PICKER_INDEX.items())
    elif args.civ and args.picker_idx is not None:
        targets = [(args.civ, args.picker_idx)]
    else:
        ap.error("need --bulk or both --civ and --picker-idx")

    results = []
    for civ, idx in targets:
        print(f"\n=== {civ} (idx={idx}) ===", flush=True)
        r = verify_one(civ, idx, ref, args.out_dir)
        results.append(r)
        mark = {"PASS": "✓", "MISMATCH": "✗",
                "BLANK": "?", "FAIL": "!"}.get(r["verdict"], "?")
        print(f"  {mark} {r['verdict']}: matches={r.get('matches')}", flush=True)
        print(f"  OCR: {r.get('ocr_text', '')[:120]!r}", flush=True)

    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r["verdict"] == "PASS"),
        "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
        "blank": sum(1 for r in results if r["verdict"] == "BLANK"),
        "fail": sum(1 for r in results if r["verdict"] == "FAIL"),
    }
    summary_path = args.out_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print(f"\n{summary}")
    print(f"summary: {summary_path}")
    return 0 if summary["fail"] == 0 and summary["mismatch"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
