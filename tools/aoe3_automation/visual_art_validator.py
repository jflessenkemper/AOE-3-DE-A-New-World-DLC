#!/usr/bin/env python3
"""Visual art validator: capture labeled screenshots of every UI surface
where civilization art appears for the A New World mod.

Non-interactive overnight driver. Produces one PNG per UI screen per
civilization batch, plus a JSON manifest per batch and a top-level
findings.json + contact_sheet.html for visual review.

Usage:
    python3 tools/aoe3_automation/visual_art_validator.py \\
        --civs ANWBritish,ANWAztecs,ANWFrench,ANWJapanese \\
        --out artifacts/validation/visual_art \\
        --observe-seconds 20

Pre-condition:
    AoE3 DE is already running and on the MAIN MENU. The script does NOT
    cold-launch the game and does NOT recover from in-match state.

Per batch (4 civs/match) flow — 7 capture points:
    01_lobby.png            (lobby with 4 civs picked, BEFORE clicking PLAY)
    02_hud_default.png      (in-match HUD, no menu, after observe-seconds)
    03_scoreboard.png       (Tab toggled — scoreboard overlay)
    04_diplomacy.png        (F4 — diplomacy panel; falls back to ESC menu)
    05_homecity_panel.png   (Home City button top-right)
    06_esc_menu.png         (Escape menu — Player Summary)
    07_endgame_screen.png   (after Resign — endgame screen)

via in-match Revolution age-up, never selectable from the lobby picker).

This script DELIBERATELY does not modify in_game_driver.py — it inlines the
needed start-skirmish sequence so we can insert the lobby screenshot
between civ-select and PLAY-click. All low-level primitives are imported
from in_game_driver / lobby_driver.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Make the project root importable so we can use the
# `tools.aoe3_automation.*` package paths that in_game_driver itself uses.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
from tools.aoe3_automation import in_game_driver as igd
from tools.aoe3_automation import lobby_driver as ldr
from tools.aoe3_automation.in_game_driver import (
    GameDriver,
    P1_CIV_FLAG,
    P2_CIV_FLAG,
    P3_CIV_FLAG,
    P4_CIV_FLAG,
    PLAY_BTN,
    SKIRMISH_BTN,
    ESC_RESIGN,
    RESIGN_YES,
    POSTGAME_QUIT,
    _click,
    _key,
    _focus_window,
)
# IMPORTANT: in_game_driver._screenshot_raw uses AoE3's PrintScreen binding
# which requires dev mode + an unbound PrintScreen key. On this rig that
# path silently produces "no_png_produced" errors. lobby_driver.screenshot()
# uses gamescopectl + an X11 fallback and is the proven capture path
# (verified producing 5.5MB 1920x1080 PNGs against the running game).
from tools.aoe3_automation.lobby_driver import screenshot as _gs_screenshot

# ---------------------------------------------------------------------------
# Constants — added here (NOT in in_game_driver.py) so we don't pollute the
# shared driver module. These are visual-validator-specific.
# ---------------------------------------------------------------------------

# Revolution-only civ — Lower Canada is only reachable via French → French
# Canadians age-up Revolution and is NOT in the lobby civ picker. Document
# in findings.json and skip from the default civ list.

# Home City button: top-right corner of the in-match HUD. Approximate from
# 1920x1080 HUD layout — the icon sits inside the right info panel, above
# the resource bar's right edge. Refine on first batch by reviewing
# 05_homecity_panel.png; if the panel didn't open, the click missed.
HOMECITY_BTN = (1850, 80)

# Default observation time after match start — gives the engine time to
# fully render the HUD (player names, flags, scoreboard data).
DEFAULT_OBSERVE_SECONDS = 20

# How many seconds to wait after click_play before polling for in-game.
# wait_for_in_game itself polls Age3Log.txt, so we just give it a generous
# timeout.
IN_GAME_TIMEOUT = 240

# Endgame screen settle time — gives the resign animation + endgame screen
# enough time to fully draw before we capture.
ENDGAME_SETTLE = 10

# Per-batch dwell after returning to main menu before starting next batch.
# Prevents the next click_skirmish from racing the menu animation.
INTER_BATCH_DWELL = 4

# 2026-05-11: dropped from 4 to 1. ANW civs CANNOT be selected via blind
# `Up*60, Down*idx, OK` keyboard navigation in slots P2-P4 — that path
# lands on vanilla AoE3:DE civs (verified empirically: asking for
# British/Aztecs/French/Japanese landed on Louis XVIII, Frederick the
# Great, Mehmed II — picker_idx values that are valid in the OCR-verified
# table do NOT match the keyboard-navigated picker offsets for opponent
# slots). The proven OCR path (`lobby_driver.set_civ_by_token_verified`)
# only handles slot=0 by default. Rather than build a multi-slot OCR
# picker tonight, we accept 1 civ per match. P2-P4 stay at Random
# Personality, which still gives us the in-game HUD/diplomacy/endgame
# captures for our chosen P1 civ. 45 matches × ~5 min ≈ 4h overnight.
BATCH_SIZE = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Stderr logger with [viz] prefix for human tail-f visibility.
    Stdout is reserved for the final summary line so the parent driver
    can scrape it cleanly."""
    print(f"[viz] {msg}", file=sys.stderr, flush=True)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _select_civ_for_slot(flag_coord: tuple[int, int], picker_idx: int) -> None:
    """Replicates GameDriver._select_civ_for_slot inline so this module can
    be self-contained. Intentionally NOT calling the bound method to avoid
    extra screenshots / focus churn between picks."""
    _click(*flag_coord, delay=2.0)
    _key("Up", n=60, delay=0.03)
    time.sleep(0.4)
    _key("Down", n=picker_idx, delay=0.04)
    time.sleep(0.4)
    # PICKER_OK is at (240, 976) — same value used inside the driver.
    _click(240, 976, delay=2.5)


def _batch_id_str(idx: int) -> str:
    return f"{idx:02d}"


def _make_batch_dir(out: Path, batch_idx: int, civs: list[str]) -> Path:
    name = f"batch_{_batch_id_str(batch_idx)}_" + "__".join(civs)
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _existing_ok_manifest(batch_dir: Path) -> Optional[dict]:
    mf = batch_dir / "manifest.json"
    if not mf.exists():
        return None
    try:
        data = json.loads(mf.read_text())
    except Exception:
        return None
    if data.get("ok") is True:
        return data
    return None


def _safe_screenshot(label: str, out_path: Path, errors: list[str]) -> bool:
    """Wrap lobby_driver.screenshot (gamescopectl-based capture) and record
    errors to the per-batch list rather than raising. Returns True on success.
    """
    try:
        _gs_screenshot(out_path)
        ok = out_path.exists() and out_path.stat().st_size > 1000
    except Exception as exc:
        errors.append(f"screenshot:{label}:exception:{exc!r}")
        return False
    if not ok:
        errors.append(f"screenshot:{label}:no_png_produced")
    return ok


def _run_one_batch(
    batch_idx: int,
    civs: list[str],
    out: Path,
    *,
    observe_seconds: int,
    force: bool,
    coords: dict,
    driver: GameDriver,
) -> dict:
    """Drive a single 4-civ skirmish and capture all 7 art surfaces.

    Returns a per-batch summary dict (also written as manifest.json).
    Never raises — all failures are logged into ``errors``.
    """
    batch_dir = _make_batch_dir(out, batch_idx, civs)
    if not force:
        existing = _existing_ok_manifest(batch_dir)
        if existing is not None:
            _log(f"batch {batch_idx:02d} already ok; skipping (use --force to redo)")
            return existing

    started_at = _utc_now_iso()
    errors: list[str] = []
    screenshots: dict[str, str] = {}

    def _shot(label: str, filename: str) -> None:
        path = batch_dir / filename
        ok = _safe_screenshot(label, path, errors)
        if ok:
            screenshots[label] = filename

    _log(f"batch {batch_idx:02d} starting: civs={civs}")

    # ------- 1. Click Skirmish from main menu ----------------------------
    try:
        ldr.click_skirmish(coords)
        time.sleep(2.0)
    except Exception as exc:
        errors.append(f"click_skirmish:{exc!r}")
        return _finalise_batch(batch_dir, batch_idx, civs, started_at,
                               screenshots, errors, observe_seconds, ok=False)

    # ------- 2. Pick civ for P1 via OCR-verified path --------------------
    # P2-P4 stay at Random Personality (see BATCH_SIZE=1 comment for why).
    # set_civ_by_token_verified loads the civ-name OCR reference from
    # enriched_reference.json and reads back the highlighted row to confirm
    # the right civ landed — slow (~3-6s per pick) but never wrong.
    try:
        _focus_window()
        civ_token = civs[0]
        ref_path = _REPO_ROOT / "enriched_reference.json"
        if not ref_path.exists():
            raise RuntimeError(f"enriched_reference.json missing at {ref_path}")
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        _log(f"  picking {civ_token} via OCR-verified path (slot=P1)")
        res = ldr.set_civ_by_token_verified(coords, civ_token, ref,
                                            prefer_ocr=True)
        if not res.get("ok"):
            errors.append(f"set_civ_verified:{civ_token}:not_ok:"
                          f"{res.get('history', [])!r}")
            try:
                driver.ensure_main_menu(retries=3)
            except Exception:
                pass
            return _finalise_batch(batch_dir, batch_idx, civs, started_at,
                                   screenshots, errors, observe_seconds, ok=False)
        time.sleep(0.6)
    except Exception as exc:
        errors.append(f"select_civs:{exc!r}\n{traceback.format_exc()}")
        try:
            driver.ensure_main_menu(retries=3)
        except Exception:
            pass
        return _finalise_batch(batch_dir, batch_idx, civs, started_at,
                               screenshots, errors, observe_seconds, ok=False)

    # ------- 3. Capture lobby BEFORE clicking PLAY (01) ------------------
    time.sleep(1.5)  # let the last picker close & lobby chrome settle
    _shot("01_lobby", "01_lobby.png")

    # ------- 4. Click PLAY ----------------------------------------------
    # Use lobby_driver.click_play (double-click for reliability) instead
    # of a raw _click on PLAY_BTN — the lobby-to-loading transition can
    # swallow a single click and leave us stuck in the lobby.
    try:
        ldr.click_play(coords)
        time.sleep(2.0)
    except Exception as exc:
        errors.append(f"click_play:{exc!r}")
        return _finalise_batch(batch_dir, batch_idx, civs, started_at,
                               screenshots, errors, observe_seconds, ok=False)

    # ------- 5. Wait for in-game ----------------------------------------
    try:
        in_game = driver.wait_for_in_game(timeout=IN_GAME_TIMEOUT,
                                          dismiss_errors=True)
    except Exception as exc:
        errors.append(f"wait_for_in_game:{exc!r}")
        in_game = False
    if not in_game:
        errors.append("wait_for_in_game:timeout_or_failure")
        # Try to recover to main menu so next batch can run.
        try:
            driver.ensure_main_menu(retries=8)
        except Exception:
            pass
        return _finalise_batch(batch_dir, batch_idx, civs, started_at,
                               screenshots, errors, observe_seconds, ok=False)

    # ------- 6. Settle, then 02 hud_default -----------------------------
    _log(f"  in-match; sleeping {observe_seconds}s for HUD to settle")
    time.sleep(observe_seconds)
    _focus_window()
    _shot("02_hud_default", "02_hud_default.png")

    # ------- 7. Tab → scoreboard (03) → Tab to close --------------------
    try:
        _key("Tab")
        time.sleep(1.0)
        _shot("03_scoreboard", "03_scoreboard.png")
        _key("Tab")
        time.sleep(0.7)
    except Exception as exc:
        errors.append(f"scoreboard:{exc!r}")

    # ------- 8. F4 → diplomacy (04) → Esc to close ----------------------
    # F4 is the AoE3:DE diplomacy hotkey; if it does not open the panel
    # (e.g. rebound or eaten by gamescope), the screenshot will simply
    # show the HUD rather than diplomacy — visually obvious to the
    # reviewer. We do NOT fall back to ESC menu automatically because
    # the ESC menu is captured separately at step 06; opening it here
    # would conflate the two surfaces and break the dismiss-with-Escape
    # contract. If F4 is confirmed broken after the first batch, change
    # this block to a click on the ESC-menu Diplomacy submenu.
    try:
        _focus_window()
        _key("F4")
        time.sleep(1.5)
        _shot("04_diplomacy", "04_diplomacy.png")
        _key("Escape")
        time.sleep(0.8)
    except Exception as exc:
        errors.append(f"diplomacy:{exc!r}")

    # ------- 9. Home City button (05) -----------------------------------
    try:
        _focus_window()
        _click(*HOMECITY_BTN, delay=1.5)
        time.sleep(1.5)
        _shot("05_homecity_panel", "05_homecity_panel.png")
        _key("Escape")
        time.sleep(0.8)
    except Exception as exc:
        errors.append(f"homecity:{exc!r}")

    # ------- 10. ESC menu (06) ------------------------------------------
    try:
        _focus_window()
        _key("Escape")
        time.sleep(1.2)
        _shot("06_esc_menu", "06_esc_menu.png")
    except Exception as exc:
        errors.append(f"esc_menu:{exc!r}")

    # ------- 11. Resign → "You Abandon" → View Postgame → endgame (07) --
    # Empirically (verified 2026-05-11): after Resign+Yes the game lands
    # on a "You Abandon Your Town" intermediate screen with VIEW_MAP and
    # VIEW_POSTGAME buttons. We must click VIEW_POSTGAME to reach the
    # actual end-of-match summary (which is where civ flags/names show).
    try:
        _click(*ESC_RESIGN, delay=0.5)
        for _ in range(2):
            _click(*RESIGN_YES, delay=0.4)
        # Wait for "You Abandon" intermediate screen to draw.
        time.sleep(4.0)
        # Capture the "You Abandon" surface as 07a (it does show the
        # civ-vs-civ summary card briefly).
        _shot("07a_abandon_screen", "07a_abandon_screen.png")
        # Click VIEW_POSTGAME to reach the per-player flag+name table.
        _click(*igd.VIEW_POSTGAME, delay=2.0)
        time.sleep(ENDGAME_SETTLE)
        _shot("07_endgame_screen", "07_endgame_screen.png")
    except Exception as exc:
        errors.append(f"resign:{exc!r}")

    # ------- 12. Quit endgame back to main menu -------------------------
    try:
        _click(*POSTGAME_QUIT, delay=1.0)
        time.sleep(3.0)
        # ensure_main_menu is blind but cheap; helps if endgame had a
        # different layout (e.g. multi-tab postgame).
        driver.ensure_main_menu(retries=5)
    except Exception as exc:
        errors.append(f"return_to_main_menu:{exc!r}")

    time.sleep(INTER_BATCH_DWELL)

    ok = not errors or all(
        # Don't fail the whole batch on a single missing screenshot —
        # the reviewer can still see what was captured. Only hard-fail
        # if we never reached in-game (already returned above).
        not e.startswith(("click_skirmish:", "select_civs:",
                          "click_play:", "wait_for_in_game:"))
        for e in errors
    )
    return _finalise_batch(batch_dir, batch_idx, civs, started_at,
                           screenshots, errors, observe_seconds, ok=ok)


def _finalise_batch(
    batch_dir: Path,
    batch_idx: int,
    civs: list[str],
    started_at: str,
    screenshots: dict[str, str],
    errors: list[str],
    observe_seconds: int,
    *,
    ok: bool,
) -> dict:
    manifest = {
        "batch_id": _batch_id_str(batch_idx),
        "civs": civs,
        "ok": ok,
        "started_at": started_at,
        "completed_at": _utc_now_iso(),
        "observed_seconds": observe_seconds,
        "screenshots": screenshots,
        "errors": errors,
    }
    (batch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    _log(f"batch {batch_idx:02d} {'OK' if ok else 'FAIL'}; "
         f"{len(screenshots)} shots, {len(errors)} errors")
    return manifest


# ---------------------------------------------------------------------------
# Aggregate output
# ---------------------------------------------------------------------------

def _write_findings(
    out: Path,
    started_at: str,
    completed_at: str,
    civs_requested: list[str],
    civs_skipped: list[str],
    batches: list[dict],
    errors: list[str],
) -> None:
    findings = {
        "started_at": started_at,
        "completed_at": completed_at,
        "civs_requested": len(civs_requested),
        "civs_skipped": civs_skipped,
        "batches": [
            {
                "batch_id": b["batch_id"],
                "civs": b["civs"],
                "ok": b["ok"],
                "screenshots": b["screenshots"],
            }
            for b in batches
        ],
        "errors": errors,
    }
    (out / "findings.json").write_text(json.dumps(findings, indent=2))


def _write_contact_sheet(out: Path, batches: list[dict]) -> None:
    """Static HTML contact sheet — one row per batch, one image per
    capture surface, civ name as caption. No JS, image paths relative."""
    parts: list[str] = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        "<title>ANW Visual Art Contact Sheet</title>",
        "<style>",
        "body{font-family:sans-serif;background:#111;color:#eee;margin:1em;}",
        "h2{border-bottom:1px solid #444;padding-bottom:.2em;}",
        ".batch{margin-bottom:2em;}",
        ".row{display:flex;flex-wrap:wrap;gap:.5em;}",
        ".cell{flex:0 0 auto;text-align:center;}",
        ".cell img{max-width:280px;max-height:160px;border:1px solid #333;}",
        ".cap{font-size:.8em;color:#aaa;}",
        ".fail{color:#f55;}",
        "</style></head><body>",
        "<h1>ANW Visual Art Contact Sheet</h1>",
    ]
    for b in batches:
        status = "" if b["ok"] else " <span class='fail'>(FAIL)</span>"
        civ_list = ", ".join(b["civs"])
        batch_dir_name = (
            f"batch_{b['batch_id']}_" + "__".join(b["civs"])
        )
        parts.append(f"<div class='batch'>")
        parts.append(
            f"<h2>Batch {b['batch_id']}: {civ_list}{status}</h2>"
        )
        parts.append("<div class='row'>")
        for label, fname in sorted(b["screenshots"].items()):
            rel = f"{batch_dir_name}/{fname}"
            parts.append(
                f"<div class='cell'><img src='{rel}' alt='{label}'>"
                f"<div class='cap'>{label}</div></div>"
            )
        parts.append("</div></div>")
    parts.append("</body></html>")
    (out / "contact_sheet.html").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _resolve_civs(arg: Optional[str]) -> list[str]:
    if arg:
        civs = [c.strip() for c in arg.split(",") if c.strip()]
    else:
        civs = sorted(ANW_TO_PICKER_INDEX.keys())
    # Always honour the SKIP set.
    civs = [c for c in civs if c not in SKIP_CIVS]
    # Validate.
    for c in civs:
        if c not in ANW_TO_PICKER_INDEX:
            raise SystemExit(
                f"unknown civ token: {c!r} "
                f"(not in ANW_TO_PICKER_INDEX)"
            )
    return civs


def _batch(civs: list[str]) -> list[list[str]]:
    """Group civs into BATCH_SIZE-sized chunks. The final batch may be
    short (1-3 civs); GameDriver allows None slots, so we pad with None
    placeholders by simply running fewer slot picks for that batch."""
    return [civs[i:i + BATCH_SIZE] for i in range(0, len(civs), BATCH_SIZE)]


def main() -> int:
    p = argparse.ArgumentParser(
        description="Capture labeled screenshots of every ANW civ's "
                    "in-game UI surfaces.")
    p.add_argument("--civs", default=None,
                   help="Comma-separated ANW civ tokens. Default: all 46 "
                        "minus SKIP_CIVS.")
    p.add_argument("--out", default="artifacts/validation/visual_art",
                   help="Output directory (relative to repo root).")
    p.add_argument("--observe-seconds", type=int,
                   default=DEFAULT_OBSERVE_SECONDS,
                   help="Seconds to wait after match start before HUD "
                        "captures begin.")
    p.add_argument("--force", action="store_true",
                   help="Re-run batches whose manifest.json already says "
                        "ok=true.")
    args = p.parse_args()

    civs = _resolve_civs(args.civs)
    batches = _batch(civs)
    out = Path(args.out)
    if not out.is_absolute():
        out = _REPO_ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    _log(f"civs={len(civs)} batches={len(batches)} "
         f"out={out} skip={sorted(SKIP_CIVS)}")

    coords = ldr.load_coords()
    driver = GameDriver(art_dir=str(out / "_driver_scratch"))

    started_at = _utc_now_iso()
    batch_summaries: list[dict] = []
    top_errors: list[str] = []

    for i, batch_civs in enumerate(batches, start=1):
        try:
            summary = _run_one_batch(
                batch_idx=i,
                civs=batch_civs,
                out=out,
                observe_seconds=args.observe_seconds,
                force=args.force,
                coords=coords,
                driver=driver,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            _log(f"batch {i:02d} unhandled exception: {exc!r}\n{tb}")
            top_errors.append(f"batch_{i:02d}_unhandled:{exc!r}")
            summary = {
                "batch_id": _batch_id_str(i),
                "civs": batch_civs,
                "ok": False,
                "screenshots": {},
                "errors": [f"unhandled:{exc!r}", tb],
            }
            # Try to recover.
            try:
                driver.ensure_main_menu(retries=5)
            except Exception:
                pass
        batch_summaries.append(summary)

    completed_at = _utc_now_iso()
    _write_findings(
        out=out,
        started_at=started_at,
        completed_at=completed_at,
        civs_requested=civs,
        civs_skipped=sorted(SKIP_CIVS),
        batches=batch_summaries,
        errors=top_errors,
    )
    _write_contact_sheet(out, batch_summaries)

    n_ok = sum(1 for b in batch_summaries if b["ok"])
    n_total = len(batch_summaries)
    print(
        f"[viz] {n_ok}/{n_total} batches completed; "
        f"see {out / 'contact_sheet.html'}"
    )
    return 0 if n_ok == n_total else 1


if __name__ == "__main__":
    sys.exit(main())
