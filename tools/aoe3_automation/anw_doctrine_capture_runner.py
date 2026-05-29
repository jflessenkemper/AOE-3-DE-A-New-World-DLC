#!/usr/bin/env python3
"""ANW Doctrine Capture Runner — AI doctrine evidence screenshot harvester.

Drives AoE3 DE through a full skirmish per ANW civ (P1=host civ, P2=hard
AI ally same civ, P3-P8=hard AI enemies) and captures 6 doctrine evidence
screenshots at fixed game-time intervals:

  T+0:30  doctrine_wall_planning  — early base, AI deciding wall strategy
  T+5:00  doctrine_wall_chokepoint — walls under construction
  T+10:00 doctrine_wall_closure   — fortified ring visible
  T+15:00 doctrine_elite_units    — units gathered
  T+18:00 doctrine_hero_attack    — hero with army
  T+22:00 doctrine_endgame_state  — late-game state

All captures are full 1920×1080 PNGs dumped to:
  artifacts/validation/visual_art/<CIV_TOKEN>/doctrine/<surface>.png

After all captures land, the runner resigns and returns to the main menu.

CLI:
    python3 tools/aoe3_automation/anw_doctrine_capture_runner.py \\
        [--civs A,B]  \\
        [--smoke]     \\
        [--resume]

    --smoke   : only ANWBritish, ANWFrench (2 civs)
    --resume  : skip civs that already have all 6 doctrine captures on disk

Pre-condition:
    AoE3 DE is already running and on the MAIN MENU.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# structlog setup — mirrors anw_visual_capture_runner.py pattern
# ---------------------------------------------------------------------------
try:
    import structlog
    _structlog_available = True
except ImportError:
    _structlog_available = False

_JSONL_HANDLE: Optional[Any] = None


def _configure_logging(artifact_root: Path) -> None:
    global _JSONL_HANDLE
    artifact_root.mkdir(parents=True, exist_ok=True)
    if not _structlog_available:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
        return
    jsonl_path = artifact_root / "doctrine_capture_runner.log.jsonl"
    _JSONL_HANDLE = jsonl_path.open("a", buffering=1, encoding="utf-8")
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=False),
            foreign_pre_chain=[timestamper, structlog.stdlib.add_log_level],
        )
    )
    jsonl_handler = logging.StreamHandler(stream=_JSONL_HANDLE)
    jsonl_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=[timestamper, structlog.stdlib.add_log_level],
        )
    )
    root_logger = logging.getLogger()
    root_logger.handlers = [console_handler, jsonl_handler]
    root_logger.setLevel(logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class _StdlibKwLogger:
    """Thin wrapper that lets stdlib loggers accept structlog-style kwargs.

    Renders the kwargs as ``key=value`` pairs appended to the event string.
    This is the fallback path when structlog is not installed.
    """

    def __init__(self, name: str):
        self._lg = logging.getLogger(name)

    @staticmethod
    def _fmt(event: str, kwargs: dict[str, Any]) -> str:
        if not kwargs:
            return event
        bits = " ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{event}  {bits}"

    def info(self, event: str, **kw: Any) -> None:
        self._lg.info(self._fmt(event, kw))

    def warning(self, event: str, **kw: Any) -> None:
        self._lg.warning(self._fmt(event, kw))

    def error(self, event: str, **kw: Any) -> None:
        self._lg.error(self._fmt(event, kw))

    def debug(self, event: str, **kw: Any) -> None:
        self._lg.debug(self._fmt(event, kw))

    def exception(self, event: str, **kw: Any) -> None:
        self._lg.exception(self._fmt(event, kw))


def _get_logger(name: str):
    if _structlog_available:
        import structlog as sl
        return sl.get_logger(name)
    return _StdlibKwLogger(name)


log = _get_logger(__name__)

# ---------------------------------------------------------------------------
# Game driver imports
# ---------------------------------------------------------------------------
from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
from tools.aoe3_automation import lobby_driver as ldr
from tools.aoe3_automation.in_game_driver import (
    GameDriver,
    ESC_MENU_X,
    ESC_RESIGN,
    RESIGN_YES,
    _click,
    _key,
    _focus_window,
)
from tools.aoe3_automation.lobby_driver import screenshot as _gs_screenshot

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Civs that cannot be selected from the lobby picker (Revolution-only)
SKIP_CIVS: set[str] = set()

# Smoke-test civ list
SMOKE_CIVS: list[str] = ["ANWBritish", "ANWFrench"]

# Seconds to wait after click_play before starting the game-time clock.
# Must cover loading screen + engine settle after wait_for_in_game.
LOADING_SCREEN_SLEEP = 13   # sleep during loading screen before wait_for_in_game
HUD_SETTLE = 20             # settle after wait_for_in_game before T=0 mark
IN_GAME_TIMEOUT = 360       # generous: ANW Hub with 8 AIs can take ~3 min to load

# Time between civs
INTER_CIV_DWELL = 4

# Schema version this runner writes (same as visual_capture_runner)
SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Doctrine capture schedule
# Each entry: (surface_name, game_seconds_after_T0, description)
# T0 is the moment wait_for_in_game returns + HUD_SETTLE seconds.
# These are real-wall-clock seconds (game runs at default speed — we don't
# touch the speed bar so it stays at whatever the lobby default is).
# ---------------------------------------------------------------------------
DOCTRINE_SCHEDULE: list[tuple[str, int, str]] = [
    ("doctrine_wall_planning",    30,    "T+0:30 early base, AI wall strategy"),
    ("doctrine_wall_chokepoint",  300,   "T+5:00 walls under construction"),
    ("doctrine_wall_closure",     600,   "T+10:00 fortified ring"),
    ("doctrine_elite_units",      900,   "T+15:00 elite unit composition"),
    ("doctrine_hero_attack",      1080,  "T+18:00 hero leading army"),
    ("doctrine_endgame_state",    1320,  "T+22:00 late-game state"),
]

DOCTRINE_SURFACES: list[str] = [s for s, _, _ in DOCTRINE_SCHEDULE]

# ---------------------------------------------------------------------------
# Map-picker workaround (see anw_visual_capture_runner for full rationale).
# anwHubTest custom map fails to load on Proton session re-use (engine bug:
# mode 6 -> mode 0 with no mode-27 entry on the 3rd+ attempt in a single
# game session). We force every doctrine match onto a stable vanilla map
# via the lobby map picker so the doctrine schedule actually runs.
# These coords are picker-popup-relative, screen=1920x1080.
# ---------------------------------------------------------------------------
_MAP_BTN = (1645, 425)              # Lobby "Select Map" button
# 2026-05-28: Re-calibrated. Old coords (1408, 832) hit the right-side
# Filter checkbox area (no-op); (1616, 991) landed between OK and Cancel
# and selected Cancel, so map-force silently closed without saving.
# Verified Acropolis ~(965, 837); Alaska ~(1195, 837); OK ~(1530, 1010).
_ALASKA_TILE = (1195, 837)          # Alaska tile in picker (row 3 col 5)
_PICKER_OK = (1530, 1010)           # OK button in picker


def _force_map_alaska(warnings: list[str]) -> None:
    """Open lobby map picker, click Alaska, confirm. Idempotent."""
    _focus_window()
    time.sleep(0.3)
    _click(*_MAP_BTN, delay=1.6)
    time.sleep(1.6)
    _click(*_ALASKA_TILE, delay=1.0)
    time.sleep(0.8)
    _click(*_PICKER_OK, delay=1.6)
    time.sleep(2.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _civ_label(token: str) -> str:
    return token[3:] if token.startswith("ANW") else token


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _match_id(civ_token: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"doctrine_{civ_token.lower()}_{ts}"


def _safe_screenshot(label: str, out_path: Path, warnings: list[str]) -> bool:
    """Wrap gamescopectl-based screenshot; record failures into warnings list."""
    try:
        _gs_screenshot(out_path)
        ok = out_path.exists() and out_path.stat().st_size > 1000
    except Exception as exc:
        warnings.append(f"screenshot:{label}:exception:{exc!r}")
        return False
    if not ok:
        warnings.append(f"screenshot:{label}:no_png_produced")
    return ok


def _build_capture_entry(
    label: str,
    full_path_rel: str,
    captured_ms: int,
    description: str,
) -> dict:
    """Build one entry for manifest.captures[] (doctrine entries have no pre-defined crops)."""
    return {
        "label": label,
        "full_path": full_path_rel,
        "captured_ms": captured_ms,
        "ocr_text": None,
        "description": description,
        "crops": [],  # cropping done by separate pipeline; no predefined crop regions for doctrine
    }


def _all_doctrine_captures_exist(civ_dir: Path) -> bool:
    """Return True if all 6 doctrine PNGs are already on disk for this civ."""
    doctrine_dir = civ_dir / "doctrine"
    for surface in DOCTRINE_SURFACES:
        if not (doctrine_dir / f"{surface}.png").exists():
            return False
    return True


def _extend_manifest(
    civ_dir: Path,
    *,
    civ_token: str,
    new_captures: list[dict],
    status: str,
    warnings: list[str],
    match_id: str,
    captured_at: str,
) -> None:
    """Extend or create manifest.json with doctrine capture entries.

    If manifest.json already exists (written by anw_visual_capture_runner.py),
    we load it and append the new doctrine entries under captures[].
    If it doesn't exist, we write a fresh minimal manifest.
    The status field of the existing manifest is not downgraded; we only
    record the doctrine-pass status in a new 'doctrine_status' field.
    """
    mf_path = civ_dir / "manifest.json"
    if mf_path.exists():
        try:
            manifest = json.loads(mf_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    else:
        manifest = {}

    # Ensure base fields are present
    if "schema_version" not in manifest:
        manifest["schema_version"] = SCHEMA_VERSION
    if "civ_token" not in manifest:
        manifest["civ_token"] = civ_token
    if "civ_label" not in manifest:
        manifest["civ_label"] = _civ_label(civ_token)
    if "captured_at" not in manifest:
        manifest["captured_at"] = captured_at
    if "host_perspective" not in manifest:
        manifest["host_perspective"] = True
    if "host_civ_token" not in manifest:
        manifest["host_civ_token"] = None

    # Append new doctrine captures (avoid duplicates by label)
    existing_captures: list[dict] = manifest.get("captures", [])
    existing_labels = {c.get("label") for c in existing_captures}
    for cap in new_captures:
        if cap["label"] not in existing_labels:
            existing_captures.append(cap)
            existing_labels.add(cap["label"])
    manifest["captures"] = existing_captures

    # Record doctrine-specific metadata
    manifest["doctrine_match_id"] = match_id
    manifest["doctrine_captured_at"] = captured_at
    manifest["doctrine_status"] = status
    manifest.setdefault("warnings", [])
    manifest["warnings"] = list(manifest["warnings"]) + warnings

    mf_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _resolve_civs(arg: Optional[str], *, smoke: bool) -> list[str]:
    if smoke:
        civs = list(SMOKE_CIVS)
    elif arg:
        civs = [c.strip() for c in arg.split(",") if c.strip()]
    else:
        civs = sorted(ANW_TO_PICKER_INDEX.keys())
    civs = [c for c in civs if c not in SKIP_CIVS]
    for c in civs:
        if c not in ANW_TO_PICKER_INDEX:
            raise SystemExit(f"unknown civ token: {c!r} (not in ANW_TO_PICKER_INDEX)")
    return civs


# ---------------------------------------------------------------------------
# Per-civ doctrine capture
# ---------------------------------------------------------------------------

def _run_doctrine_civ(
    civ_token: str,
    out_root: Path,
    *,
    driver: GameDriver,
    coords: dict,
    enriched_ref: dict,
    resume: bool,
) -> dict:
    """Run a full doctrine capture pass for one civ.

    Lobby setup:
      P1 = host civ (civ_token)
      P2 = hard AI ally (same civ_token)
      P3..P8 = hard AI enemies (same civ_token — keeps picker work minimal;
               the AI doctrine is civ-independent from the observation POV)

    Returns a summary dict with civ_token, status, elapsed_s.
    """
    civ_dir = out_root / civ_token
    doctrine_dir = civ_dir / "doctrine"
    doctrine_dir.mkdir(parents=True, exist_ok=True)

    if resume and _all_doctrine_captures_exist(civ_dir):
        log.info("civ_skip_complete", civ=civ_token)
        return {"civ_token": civ_token, "status": "skipped_complete", "elapsed_s": 0.0}

    t0 = time.time()
    captured_at = _utc_now_iso()
    mid = _match_id(civ_token)
    warnings: list[str] = []
    captures: list[dict] = []

    log.info("doctrine_civ_start", civ=civ_token)

    # ── 0. Ensure main menu ──────────────────────────────────────────────────
    try:
        driver.wait_for_main_menu(timeout=60)
    except Exception as exc:
        warnings.append(f"wait_for_main_menu:pre:{exc!r}")

    # ── 1. Click Skirmish ────────────────────────────────────────────────────
    try:
        ldr.click_skirmish(coords)
        time.sleep(2.0)
    except Exception as exc:
        warnings.append(f"click_skirmish:{exc!r}")
        _extend_manifest(civ_dir, civ_token=civ_token, new_captures=captures,
                         status="failed", warnings=warnings,
                         match_id=mid, captured_at=captured_at)
        log.warning("doctrine_civ_failed", civ=civ_token, reason="click_skirmish",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed",
                "elapsed_s": round(time.time() - t0, 1)}

    # ── 2. Pick P1 civ (host) ────────────────────────────────────────────────
    try:
        _focus_window()
        res = ldr.set_civ_by_token_verified(coords, civ_token, enriched_ref,
                                            prefer_ocr=False)
        if not res.get("ok"):
            raise RuntimeError(f"P1 set_civ_verified not ok: {res.get('history', [])!r}")
        time.sleep(0.6)
    except Exception as exc:
        warnings.append(f"select_p1_civ:{exc!r}")
        try:
            driver.ensure_main_menu(retries=4)
        except Exception:
            pass
        _extend_manifest(civ_dir, civ_token=civ_token, new_captures=captures,
                         status="failed", warnings=warnings,
                         match_id=mid, captured_at=captured_at)
        log.warning("doctrine_civ_failed", civ=civ_token, reason="select_p1_civ",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed",
                "elapsed_s": round(time.time() - t0, 1)}

    # ── 3. Pick P2..P8 (AI opponents/ally) ──────────────────────────────────
    # slot indices 1..7 map to P2..P8. We set all 7 to the same civ so the
    # picker walk is predictable and minimises inter-slot resets.
    # Slots 1 = P2 (ally), slots 2..7 = P3..P8 (enemies).
    # The lobby ALREADY defaults to enemies; we don't change diplomacy here —
    # the goal is simply to guarantee the same civ AI is fighting/defending.
    for slot_idx in range(1, 8):  # 1..7 = P2..P8
        try:
            res = ldr.set_opponent_civ_by_token_verified(
                coords, slot_idx, civ_token, enriched_ref, prefer_ocr=False)
            if not res.get("ok"):
                warnings.append(
                    f"set_opponent_P{slot_idx + 1}:not_ok:{res.get('history', [])!r}")
            time.sleep(0.4)
        except Exception as exc:
            warnings.append(f"set_opponent_P{slot_idx + 1}:{exc!r}")
            # Non-fatal — continue with whatever civ landed there

    # ── 3b. Force map to a stable vanilla (Alaska) ────────────────────────────
    # 2026-05-18: anwHubTest custom map currently fails to load on Proton
    # session re-use; force every doctrine match onto a vanilla map so the
    # 22-min schedule actually runs.
    try:
        _force_map_alaska(warnings)
    except Exception as exc:
        warnings.append(f"force_map_alaska:{exc!r}")

    # ── 4. Click PLAY ────────────────────────────────────────────────────────
    try:
        ldr.click_play(coords)
        time.sleep(2.0)
    except Exception as exc:
        warnings.append(f"click_play:{exc!r}")
        _extend_manifest(civ_dir, civ_token=civ_token, new_captures=captures,
                         status="failed", warnings=warnings,
                         match_id=mid, captured_at=captured_at)
        log.warning("doctrine_civ_failed", civ=civ_token, reason="click_play",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed",
                "elapsed_s": round(time.time() - t0, 1)}

    # ── 5. Ride out the loading screen, then wait for in-game ────────────────
    # Sleep through the loading screen first (13s), then call wait_for_in_game.
    # We do NOT capture a loading screenshot here — the doctrine runner is
    # only interested in in-game AI behaviour.
    time.sleep(LOADING_SCREEN_SLEEP)

    try:
        in_game = driver.wait_for_in_game(timeout=IN_GAME_TIMEOUT,
                                          dismiss_errors=True)
    except Exception as exc:
        warnings.append(f"wait_for_in_game:{exc!r}")
        in_game = False

    if not in_game:
        warnings.append("wait_for_in_game:timeout_or_failure")
        try:
            driver.ensure_main_menu(retries=8)
        except Exception:
            pass
        _extend_manifest(civ_dir, civ_token=civ_token, new_captures=captures,
                         status="failed", warnings=warnings,
                         match_id=mid, captured_at=captured_at)
        log.warning("doctrine_civ_failed", civ=civ_token, reason="wait_for_in_game",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed",
                "elapsed_s": round(time.time() - t0, 1)}

    log.info("doctrine_in_game", civ=civ_token, settling_s=HUD_SETTLE)
    time.sleep(HUD_SETTLE)

    # T0 = now. All game-time intervals in DOCTRINE_SCHEDULE are measured
    # from this point. We walk through them in order, sleeping the delta
    # between consecutive capture times.
    t_game_start = time.time()
    prev_game_s = 0

    for surface, game_s, description in DOCTRINE_SCHEDULE:
        # Sleep the remaining time until this capture point
        elapsed_so_far = time.time() - t_game_start
        sleep_needed = game_s - elapsed_so_far
        if sleep_needed > 0:
            log.info("doctrine_waiting", civ=civ_token, surface=surface,
                     sleep_s=round(sleep_needed, 1), target_game_s=game_s)
            time.sleep(sleep_needed)
        else:
            log.warning("doctrine_late", civ=civ_token, surface=surface,
                        behind_s=round(-sleep_needed, 1))

        out_path = doctrine_dir / f"{surface}.png"
        ms = _utc_now_ms()
        ok = _safe_screenshot(surface, out_path, warnings)
        if ok:
            rel_path = f"doctrine/{surface}.png"
            captures.append(_build_capture_entry(surface, rel_path, ms, description))
            log.info("doctrine_captured", civ=civ_token, surface=surface,
                     game_s=game_s, path=str(out_path))
        else:
            log.warning("doctrine_capture_failed", civ=civ_token, surface=surface)

        prev_game_s = game_s

    # ── 6. Resign and return to main menu ────────────────────────────────────
    # Per user rules: only ESC + RESIGN are injected during gameplay.
    # No camera panning, no unit clicks, no F-keys during the match.
    try:
        _focus_window()
        _key("Escape")
        time.sleep(0.8)
        _click(*ESC_RESIGN, delay=0.5)
        time.sleep(0.5)
        _click(*RESIGN_YES, delay=0.4)
        _click(*RESIGN_YES, delay=0.4)   # second attempt in case dialog still fading
        time.sleep(2.5)
        driver.ensure_main_menu(retries=3)
    except Exception as exc:
        warnings.append(f"resign:{exc!r}")
        try:
            driver.ensure_main_menu(retries=6)
        except Exception:
            pass

    time.sleep(INTER_CIV_DWELL)

    # Determine status
    captured_labels = {cap["label"] for cap in captures}
    missing = [s for s in DOCTRINE_SURFACES if s not in captured_labels]
    if missing:
        status = "partial" if captures else "failed"
        warnings.append(f"missing_surfaces:{missing!r}")
    else:
        status = "complete"

    _extend_manifest(civ_dir, civ_token=civ_token, new_captures=captures,
                     status=status, warnings=warnings,
                     match_id=mid, captured_at=captured_at)

    elapsed = round(time.time() - t0, 1)
    log.info("doctrine_civ_done", civ=civ_token, status=status,
             elapsed_s=elapsed, n_captures=len(captures), n_warnings=len(warnings))
    return {"civ_token": civ_token, "status": status, "elapsed_s": elapsed}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="ANW doctrine capture runner — AI doctrine evidence screenshot harvester."
    )
    p.add_argument("--civs", default=None,
                   help="Comma-separated ANW civ tokens. Default: all minus skip set.")
    p.add_argument("--smoke", action="store_true",
                   help=f"Quick smoke test: only {SMOKE_CIVS} (2 civs).")
    p.add_argument("--resume", action="store_true",
                   help="Skip civs that already have all 6 doctrine PNGs on disk.")
    p.add_argument("--out", default="artifacts/validation/visual_art",
                   help="Output root (relative to repo root).")
    args = p.parse_args()

    out_root = Path(args.out)
    if not out_root.is_absolute():
        out_root = _REPO_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)

    _configure_logging(out_root)

    civs = _resolve_civs(args.civs, smoke=args.smoke)
    log.info("doctrine_runner_start", n_civs=len(civs),
             smoke=args.smoke, resume=args.resume)

    # Load shared resources
    enriched_ref_path = _REPO_ROOT / "enriched_reference.json"
    if not enriched_ref_path.exists():
        print(f"ERROR: enriched_reference.json not found at {enriched_ref_path}",
              file=sys.stderr)
        return 1
    enriched_ref = json.loads(enriched_ref_path.read_text(encoding="utf-8"))
    coords = ldr.load_coords()
    driver = GameDriver(art_dir=str(out_root / "_doctrine_driver_scratch"))

    results: list[dict] = []

    for civ_token in civs:
        try:
            r = _run_doctrine_civ(
                civ_token, out_root,
                driver=driver, coords=coords,
                enriched_ref=enriched_ref, resume=args.resume,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            log.error("doctrine_civ_unhandled", civ=civ_token, exc=str(exc), tb=tb)
            r = {"civ_token": civ_token, "status": "failed", "elapsed_s": 0.0}
            try:
                driver.ensure_main_menu(retries=5)
            except Exception:
                pass
        results.append(r)

    # ── Summary ──────────────────────────────────────────────────────────────
    n_complete = sum(1 for r in results if r["status"] == "complete")
    n_failed   = sum(1 for r in results if r["status"] == "failed")
    n_partial  = sum(1 for r in results if r["status"] == "partial")
    n_skipped  = sum(1 for r in results if "skipped" in r["status"])
    total_s    = sum(r["elapsed_s"] for r in results)

    print(
        f"[doctrine] done: complete={n_complete} partial={n_partial} "
        f"failed={n_failed} skipped={n_skipped} total_civs={len(results)} "
        f"elapsed={total_s:.0f}s  out={out_root}"
    )

    if _JSONL_HANDLE:
        _JSONL_HANDLE.close()

    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
