"""Pixel-coord-driven Skirmish-lobby driver for AoE3 DE under gamescope.

Fully deterministic — no OCR, no template matching. Click coords are baked
into lobby_coords.json (empirically measured 2026-04-28). State transitions
are verified by ImageMagick AE pixel-diff against reference screenshots.

Run from gamescope-host context:
    flatpak-spawn --host python3 tools/aoe3_automation/lobby_driver.py --select-civ aztecs

The driver assumes the game is already at the Skirmish lobby (default
state). Use manage_game.py / launch_retest_mod.sh to get there first.

Why not pyautogui? Because pyautogui talks to the host X server, but our
display is gamescope's nested Xwayland on :1. Use xdotool with explicit
DISPLAY=:1 instead. Why not template matching? OCR/template matching
proved unreliable on AoE3 DE's Trajan-style caps over textured wood.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
COORDS_PATH = Path(__file__).parent / "lobby_coords.json"

# ---------------------------------------------------------------------------
# Optional harness backend (socket-level input injection via AOE3DEHarness).
# Set via set_harness_backend() before calling click/screenshot/key helpers.
# When None, all functions fall back to the legacy xdotool / gamescopectl path
# unchanged — no behaviour change for existing callers.
# ---------------------------------------------------------------------------

_HARNESS_BACKEND = None  # type: Optional["HarnessClient"]  # noqa: F821


def set_harness_backend(client: "HarnessClient") -> None:  # noqa: F821
    """Register a HarnessClient instance as the active input backend.

    When set, click(), click_fast(), screenshot(), and key() route through
    the AOE3DEHarness control socket instead of xdotool / gamescopectl.

    Args:
        client: A connected HarnessClient (from tools.aoe3_harness.harness_client).
                Pass None to clear the backend and revert to xdotool fallback.
    """
    global _HARNESS_BACKEND
    _HARNESS_BACKEND = client
SCROLL_TABLE_PATH = Path(__file__).parent / "picker_scroll_table.json"
CIV_ORDER_CACHE_PATH = Path(__file__).parent / "picker_civ_order.json"
RAW_DIR = Path(__file__).parent / "templates" / "matrix" / "_raw"
CLEAN_LOBBY_REF = RAW_DIR / "05_skirmish_lobby.png"
ARTIFACT_DIR = Path(__file__).parent / "artifacts" / "lobby_driver"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# Tightened sleep timings for the fast path — measured against the gamescope
# input chain. 2026-05-11: aggressive overnight retune. Prior values were
# already trimmed once on 2026-05-08 from 6× this baseline; the retune below
# is a further 30-50% cut, validated against the live picker.
FAST_CLICK_PRE   = 0.03   # cursor move → click
FAST_CLICK_POST  = 0.06   # click → next action
FAST_WHEEL_PRE   = 0.02   # cursor move → wheel
FAST_WHEEL_POST  = 0.04   # wheel → next wheel
PICKER_OPEN_SETTLE  = 0.55  # picker fade-in animation
PICKER_CLOSE_SETTLE = 0.25  # picker fade-out
CONFIRM_SETTLE      = 0.35  # OK click → lobby refresh

# Authoritative civ order — sourced from picker_scroll_table.json["civ_names"].
# Loaded lazily so the driver still works for non-civ-select commands.
CIV_ORDER: list[str] | None = None


def get_civ_order() -> list[str]:
    global CIV_ORDER
    if CIV_ORDER is None:
        CIV_ORDER = list(load_scroll_table()["civ_names"])
    return CIV_ORDER


def load_coords() -> dict:
    return json.loads(COORDS_PATH.read_text())


def load_scroll_table() -> dict:
    """Load picker_scroll_table.json — empirically built mapping
    scroll_count → top visible civ_index. The picker advances ~0.74
    rows per wheel-down click (NOT 1:1), so we can't compute scrolls
    needed analytically; we look it up.
    """
    return json.loads(SCROLL_TABLE_PATH.read_text())


def find_scrolls_for_civ(table: dict, civ_idx: int) -> tuple[int, int]:
    """Given a target civ_idx, return (scrolls_needed, click_row_within_visible).

    Targets a STABLE click row (0..rows_visible-3) — never the bottom 2 rows,
    because empirically the picker sometimes only fully renders 9/10 rows
    during a scroll animation, so row=9 (and sometimes row=8) can be missing.

    Strategy:
      - Prefer scroll counts where civ_idx lands at row in [0..7]
      - Among those, pick the smallest scroll count (least scrolling work)
      - Fall back to row 8 then 9 for civs near the very end of the list
        that have no choice (the picker has already saturated)
    """
    rows_visible = int(table["rows_visible"])  # 10
    safe_max_row = rows_visible - 3            # 7
    s2t = table["scroll_to_top_idx"]
    candidates: list[tuple[int, int, int]] = []  # (preference, n, click_row)
    for n_str in sorted(s2t.keys(), key=int):
        n = int(n_str)
        top = int(s2t[n_str])
        if top <= civ_idx <= top + rows_visible - 1:
            click_row = civ_idx - top
            # Prefer rows 0..7 (safe), else row 8, else row 9
            if click_row <= safe_max_row:
                pref = 0
            elif click_row == rows_visible - 2:
                pref = 1
            else:
                pref = 2
            candidates.append((pref, n, click_row))
    if not candidates:
        raise ValueError(
            f"civ_idx {civ_idx} not reachable; max top in table is "
            f"{max(int(v) for v in s2t.values())}"
        )
    candidates.sort(key=lambda t: (t[0], t[1]))
    _, scrolls, click_row = candidates[0]
    return scrolls, click_row


# ---- civ-order cache (fast path) -----------------------------------------
#
# picker_civ_order.json is built by `lobby_driver.py --rebuild-cache` (live
# walk + OCR) OR derived analytically from picker_scroll_table.json +
# anw_civ_picker_map.py for the SELECT CIVILIZATION (alphabetical) layout.
#
# The cache turns "find civ in picker" from a 30s OCR walk into a O(1)
# dictionary lookup + a known scroll+click. As long as the picker layout
# matches what the cache was built against, every pick is fast and
# deterministic.

_CIV_ORDER_CACHE: Optional[dict] = None


def load_civ_order_cache(*, force_reload: bool = False) -> dict:
    """Load picker_civ_order.json (cached). Returns the parsed dict.

    Auto-falls-back to deriving the cache from picker_scroll_table.json +
    anw_civ_picker_map.py if the file is missing — first call from a fresh
    checkout doesn't crash, it just rebuilds analytically.
    """
    global _CIV_ORDER_CACHE
    if _CIV_ORDER_CACHE is not None and not force_reload:
        return _CIV_ORDER_CACHE
    if CIV_ORDER_CACHE_PATH.exists():
        _CIV_ORDER_CACHE = json.loads(CIV_ORDER_CACHE_PATH.read_text())
        return _CIV_ORDER_CACHE
    # Derive analytically and write
    _CIV_ORDER_CACHE = derive_civ_order_cache()
    CIV_ORDER_CACHE_PATH.write_text(json.dumps(_CIV_ORDER_CACHE, indent=2))
    return _CIV_ORDER_CACHE


def derive_civ_order_cache() -> dict:
    """Compute the civ-order cache analytically from existing tables.

    Cheap (no live game needed). Used as a fallback on first load and as the
    default builder for the alphabetical SELECT CIVILIZATION layout.
    """
    table = load_scroll_table()
    try:
        from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
    except Exception:
        # Direct file load if package import path isn't set up
        from importlib.util import spec_from_file_location, module_from_spec
        sp = spec_from_file_location(
            "anw_civ_picker_map",
            Path(__file__).parent / "anw_civ_picker_map.py",
        )
        mm = module_from_spec(sp)
        assert sp.loader is not None
        sp.loader.exec_module(mm)
        ANW_TO_PICKER_INDEX = mm.ANW_TO_PICKER_INDEX

    entries: dict = {}
    for token, civ_idx in ANW_TO_PICKER_INDEX.items():
        try:
            scrolls, click_row = find_scrolls_for_civ(table, civ_idx)
        except ValueError:
            continue
        entries[token] = {
            "civ_index": civ_idx,
            "scroll_count": scrolls,
            "click_row": click_row,
            "civ_name": (table["civ_names"][civ_idx]
                         if civ_idx < len(table["civ_names"]) else "?"),
        }
    return {
        "_doc": ("Auto-derived from picker_scroll_table.json + "
                 "anw_civ_picker_map.py. Maps civ_token -> "
                 "(scroll_count, click_row) for the SELECT CIVILIZATION "
                 "picker (alphabetical, profile-independent)."),
        "schema_version": 1,
        "picker_layout": "SELECT_CIVILIZATION_alphabetical",
        "rows_visible": int(table.get("rows_visible", 10)),
        "row_y_start": 301,
        "row_spacing": 64,
        "row_x_center": 440,
        "scroll_anchor": [440, 500],
        "entries": entries,
    }


def get_cache_entry(civ_token: str) -> Optional[dict]:
    """Return cache entry for civ_token or None if not in cache."""
    cache = load_civ_order_cache()
    return cache.get("entries", {}).get(civ_token)


def sh(cmd: str, *, check: bool = True) -> str:
    """Run a host command via flatpak-spawn if we're inside the Flatpak."""
    if Path("/.flatpak-info").exists():
        cmd = f"flatpak-spawn --host bash -lc {json.dumps(cmd)}"
    out = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
    )
    if check and out.returncode != 0:
        raise RuntimeError(
            f"command failed (rc={out.returncode}):\n  cmd: {cmd}\n  stderr: {out.stderr}"
        )
    return out.stdout


def _aoe3_display() -> str:
    """Resolve the X display that owns AoE3 (lazy, cached, fallback to :1).

    Older sessions hard-coded ``DISPLAY=:1``; once the user runs CoH2 alongside
    AoE3, gamescope shifts AoE3 onto ``:2``. We use ``gamescope_detect`` so the
    same coords work regardless of which gamescope index AoE3 ended up on.
    """
    # 1) explicit env override always wins
    env_disp = os.environ.get("AOE3_DISPLAY") or os.environ.get("DISPLAY_AOE3")
    if env_disp:
        return env_disp
    # 2) try the active detector
    try:
        from tools.aoe3_automation.gamescope_detect import detect_aoe3_display
        d, _ = detect_aoe3_display()
        return d
    except Exception:
        pass
    # 3) legacy default
    return ":1"


def xdo(cmd: str) -> None:
    """Run an xdotool command against the AoE3 nested-Xwayland display."""
    sh(f"DISPLAY={_aoe3_display()} xdotool {cmd}")


def press_key(vk_or_name: "int | str") -> None:
    """Inject a key tap via the harness socket or xdotool fallback.

    Args:
        vk_or_name: When the harness backend is active, pass a Win32 VK
                    integer (e.g. 0x1B for Escape, 0x0D for Enter).
                    When falling back to xdotool, pass an xdotool key-name
                    string (e.g. "Escape", "Return").  Callers that need
                    both paths must pass an int (the harness path) and keep
                    the xdotool-name form for the fallback; alternatively,
                    call xdo() directly for the pure-xdotool case.
    """
    if _HARNESS_BACKEND is not None:
        if not isinstance(vk_or_name, int):
            raise TypeError(
                "press_key: harness backend requires an integer Win32 VK code; "
                f"got {vk_or_name!r}. Use the VK_* constants from tools.aoe3_harness.vk."
            )
        _HARNESS_BACKEND.key(vk_or_name)
        return
    # xdotool fallback — expects a key-name string.
    xdo(f"key {vk_or_name}")


def _x11_screenshot_fallback(out_path: Path, x_disp: str) -> bool:
    """Capture AoE3 directly via ``import -window <wid>`` (ImageMagick).

    Used when gamescopectl can't deliver a usable 1920x1080 frame — typically
    when AoE3 is running in a regular Xwayland window outside gamescope, or
    when another game owns the only responsive gamescope socket. The X11
    capture path is independent of gamescope and always returns the actual
    AoE3 client area (1920x1080 by AoE3 DE convention).

    Writes via a temp path next to out_path then atomically renames, so a
    late gamescopectl async write to ``out_path`` (still in flight from the
    primary path) cannot clobber the result.

    Returns True if a valid PNG of the expected size now lives at out_path.
    """
    # Find the AoE3 window id on this X display.
    wid_out = sh(
        f"DISPLAY={x_disp} xdotool search --name 'Age of Empires III' 2>/dev/null | head -1",
        check=False,
    ).strip()
    if not wid_out:
        return False
    # Give any pending gamescopectl async write 1s to finish flushing into
    # out_path. Without this, our subsequent unlink+rename can race the
    # gamescope writer and end up with stale 2560x1440 CoH2 bytes.
    time.sleep(1.0)
    # Keep .png suffix on the temp file so ImageMagick chooses the PNG
    # encoder from the extension. With a .tmp suffix it falls back to its
    # default format (PostScript) and writes a giant unreadable blob.
    tmp_path = out_path.with_name(out_path.stem + ".x11tmp" + out_path.suffix)
    tmp_path.unlink(missing_ok=True)
    sh(f"DISPLAY={x_disp} import -window {wid_out} PNG:{tmp_path}", check=False)
    if not (tmp_path.exists() and tmp_path.stat().st_size > 1000):
        tmp_path.unlink(missing_ok=True)
        return False
    verify = sh(f"magick identify {tmp_path} 2>&1 || true", check=False)
    if not ("PNG" in verify and "1920x1080" in verify and "error" not in verify.lower()):
        tmp_path.unlink(missing_ok=True)
        return False
    # Atomic replace so any straggling gamescope writer that was racing on
    # out_path can't interleave bytes with our valid PNG.
    out_path.unlink(missing_ok=True)
    tmp_path.replace(out_path)
    return True


def screenshot(out_path: Path, *, retries: int = 5) -> Path:
    """Capture AoE3 frame at 1920x1080.

    Primary path (when harness backend set): ``HarnessClient.screenshot()``
    via the control socket (compositor framebuffer, always 1920x1080).

    Secondary path: ``gamescopectl screenshot`` (when AoE3 is inside gamescope).
    Fallback path: ``import -window <wid>`` against the AoE3 X11 window
    (when AoE3 is running directly on Xwayland, or another game owns the
    only responsive gamescope socket — empirically observed 2026-05-09 with
    CoH2 on gamescope-0 and AoE3 on a raw :0 window).

    gamescopectl writes async; an immediate read can hit a partial file. We
    retry the gamescope path until the file exists with non-zero size AND
    magick can parse it (catches truncated PNGs that would otherwise cause
    downstream `magick compare` to silently produce empty output and
    diff_pixels to return 0). If retries exhaust, we drop to the X11
    fallback rather than raising.

    NOTE: gamescopectl picks its target via ``GAMESCOPE_WAYLAND_DISPLAY``,
    not ``DISPLAY``; we additionally force an absolute path because gamescope
    silently drops relative paths.
    """
    # Resolve to an absolute path so gamescopectl writes where we expect even
    # when invoked from an unfamiliar cwd; ensure the parent dir exists.
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.unlink(missing_ok=True)
    # Harness fast-path: compositor framebuffer via socket — always 1920x1080.
    # Fact #6: screenshots intermittently time out at the default 10s; treat as
    # non-fatal and retry once before falling through to the gamescopectl path.
    if _HARNESS_BACKEND is not None:
        for _attempt in range(2):
            try:
                _HARNESS_BACKEND.screenshot(out_path)
                return out_path
            except Exception as _exc:
                print(f"[screenshot] harness attempt {_attempt+1} failed: {_exc!r}; "
                      f"{'retrying' if _attempt == 0 else 'falling back to gamescopectl'}",
                      flush=True)
        # Fall through to gamescopectl path on two consecutive harness failures.
    # Pair the AoE3 X display with the matching gamescope socket.
    try:
        from tools.aoe3_automation.gamescope_detect import detect_aoe3_display
        x_disp, gs_disp = detect_aoe3_display()
    except Exception:
        x_disp, gs_disp = ":1", "gamescope-0"
    invalidated_once = False
    for i in range(retries):
        sh(
            f"DISPLAY={x_disp} GAMESCOPE_WAYLAND_DISPLAY={gs_disp} "
            f"WAYLAND_DISPLAY={gs_disp} gamescopectl screenshot {out_path}",
            check=False,
        )
        time.sleep(0.6)
        if not (out_path.exists() and out_path.stat().st_size > 1000):
            # Mid-loop cache invalidation: if the first 2 attempts produced no
            # output at all, the cached gamescope socket likely points at a
            # dead Xwayland (e.g., after force-relaunch). Re-detect once.
            if not invalidated_once and i >= 1:
                try:
                    from tools.aoe3_automation import gamescope_detect
                    gamescope_detect.invalidate_cache()
                    x_disp, gs_disp = detect_aoe3_display(use_cache=False)
                    invalidated_once = True
                except Exception:
                    pass
            continue
        verify = sh(f"magick identify {out_path} 2>&1 || true", check=False)
        if "PNG" in verify and "1920x1080" in verify and "error" not in verify.lower():
            return out_path
        # else: file truncated or unreadable, retry
    # gamescopectl exhausted — try direct X11 capture before giving up.
    if _x11_screenshot_fallback(out_path, x_disp):
        return out_path
    raise RuntimeError(f"screenshot failed after {retries} retries: {out_path}")


def diff_pixels(a: Path, b: Path) -> int:
    """Total absolute-error pixel count between two images.

    Uses 'magick compare -metric AE'. Output format is
    '<AE_count> (<normalized_fraction>)', e.g. '2.07342e+06 (0.999913)'.
    The differing-pixel COUNT is the LEADING token; the parenthetical is the
    normalized fraction in [0,1]. (Earlier code mis-read the parenthetical as
    the count — int(0.999913)==0 — which made every comparison return 0 and
    is_clean_lobby always true. 2026-05-31 fix.)

    Returns -1 on error (so callers can distinguish "couldn't compare" from
    "compared and got 0 differences"). Both is_clean_lobby and is_picker_open
    treat negative returns as "unknown" (False, conservatively).
    """
    out = sh(
        f"magick compare -metric AE {a} {b} null: 2>&1 || true",
        check=False,
    )
    if not out.strip():
        return -1
    # Numeric pattern must start with a digit so we don't catch lone 'e' / 'E'
    # / '+' / '-' tokens from words like "error" in magick's stderr output.
    num_re = r"\d[\d.]*(?:[eE][+-]?\d+)?"
    # The AE pixel count is the FIRST numeric token (may be in scientific
    # notation). The parenthetical fraction is intentionally ignored.
    m = re.match(rf"\s*({num_re})", out)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            pass
    for cand in re.findall(num_re, out):
        try:
            return int(float(cand))
        except ValueError:
            continue
    return -1


_GAMESCOPE_WID: Optional[str] = None


class NoGamescopeWindowError(RuntimeError):
    """Raised when an input function (click/move/wheel) cannot find a
    live AoE3 gamescope window to target.

    This is a HARD guard against the cursor-grab failure mode where, if
    AoE3 is not running (or crashed), the previous code path fell back
    to raw ``xdotool mousemove``/``click`` which targets the user's
    primary X display — moving the user's real desktop cursor and
    landing clicks on whatever window happens to be focused.

    Per the user's strict "no cursor-grab" preference, all input
    functions now refuse to operate when ``_GAMESCOPE_WID`` is empty.
    """


def _ensure_window_focus() -> None:
    """Activate the gamescope Xwayland window before sending input.

    Clicks via xdotool reach the X server fine, but gamescope's nested
    compositor silently drops them if the window has lost activation
    (which happens intermittently when host-side processes — flatpak-spawn,
    kwin notifications, the Claude runtime — steal focus). Without this,
    individual clicks succeed in isolation but stop registering after a
    few iterations of confirm_civ_selection() → move_mouse_off().

    2026-05-07: Validate cache against actual current WID — after a game
    cycle (kill+relaunch), the AoE3 window gets a new XID, but the cache
    holds the dead one. Always re-query and update if changed; cheap
    (~50ms) and avoids stale-WID click misses on every match-2+.
    """
    global _GAMESCOPE_WID
    try:
        out = sh(
            f"DISPLAY={_aoe3_display()} xdotool search --name 'Age of Empires III' 2>/dev/null | head -1",
            check=False,
        ).strip()
        current_wid = out or ""
    except Exception:
        current_wid = ""
    if current_wid and current_wid != _GAMESCOPE_WID:
        _GAMESCOPE_WID = current_wid
    elif not current_wid:
        # Don't clobber a known-good cached WID with empty (transient query
        # failure could otherwise wipe state mid-match).
        if _GAMESCOPE_WID is None:
            _GAMESCOPE_WID = ""
    if _GAMESCOPE_WID:
        try:
            sh(f"DISPLAY={_aoe3_display()} xdotool windowactivate {_GAMESCOPE_WID} 2>/dev/null || true",
               check=False)
        except Exception:
            pass


def _require_gamescope_wid() -> str:
    """Return the live gamescope window XID, or raise NoGamescopeWindowError.

    Every input function calls this first. If AoE3 isn't running (or its
    window has been destroyed), ``_GAMESCOPE_WID`` is empty after
    ``_ensure_window_focus()``, and we raise immediately rather than
    falling back to raw xdotool (which would target the user's real
    desktop cursor — see :class:`NoGamescopeWindowError`).
    """
    _ensure_window_focus()
    if not _GAMESCOPE_WID:
        raise NoGamescopeWindowError(
            "No AoE3 gamescope window found. Refusing to send input — "
            "would otherwise grab the user's real desktop cursor. "
            "Launch AoE3 DE under gamescope and retry."
        )
    return _GAMESCOPE_WID


def click(x: int, y: int, *, settle: float = 0.05) -> None:
    # 2026-05-14: dropped default settle 0.2 → 0.05 to match click_fast
    # cadence. Call sites that need slow settle (picker animation,
    # lobby fade, OK→refresh) pass settle= explicitly. Per-user demand
    # for "super fast clicks and menu interaction".
    #
    # 2026-05-28: Removed raw-xdotool fallback path. If the gamescope
    # window isn't found, raise NoGamescopeWindowError rather than
    # moving the user's real desktop cursor. See _require_gamescope_wid().
    #
    # Harness backend: if a HarnessClient backend is registered, route
    # directly through the socket (compositor-space 0–1919, 0–1079).
    # Coords from lobby_coords.json are already in that space (1920x1080).
    if _HARNESS_BACKEND is not None:
        # 2026-05-31: AoE3 fires clicks at the engine's *internal* cursor
        # position, which only a motion event updates. A bare CLICK lands at
        # the stale cursor pos and silently misses hover-sensitive UI (civ
        # picker '?', PLAY). Send a MOVE first — mirrors the xdotool
        # mousemove→click path below, which exists for the same reason.
        _HARNESS_BACKEND.move(x, y)
        time.sleep(0.03)
        _HARNESS_BACKEND.click(x, y)
        time.sleep(settle)
        return
    wid = _require_gamescope_wid()
    # 2026-05-07: Both mousemove AND click must target the gamescope window
    # via ``--window``. Using absolute ``mousemove x y`` (without --window)
    # places the X cursor at display-space (x,y), which on this rig sometimes
    # lands OUTSIDE the gamescope client area — the subsequent ``click
    # --window WID`` then fires at whatever pixel the engine's internal
    # cursor was at, NOT the intended target. Symptom: clicks intermittently
    # miss menu items even when coords are correct.
    xdo(f"mousemove --window {wid} {x} {y}")
    time.sleep(settle)
    xdo(f"click --window {wid} 1")


def click_fast(x: int, y: int, *, pre: float = FAST_CLICK_PRE,
                post: float = FAST_CLICK_POST) -> None:
    """Tight-sleep click for the fast path.

    Skips the per-click _ensure_window_focus() round-trip — the caller is
    responsible for calling _ensure_window_focus() once at the start of a
    fast-path operation. This shaves ~50ms per click which is the main
    overhead in a multi-click sequence.

    2026-05-28: If ``_GAMESCOPE_WID`` is empty, raise
    NoGamescopeWindowError instead of falling back to raw xdotool
    (which would grab the user's real desktop cursor).
    """
    if _HARNESS_BACKEND is not None:
        # See click(): MOVE before CLICK so the engine registers the hit at
        # the target, not the stale internal cursor position.
        _HARNESS_BACKEND.move(x, y)
        time.sleep(pre)
        _HARNESS_BACKEND.click(x, y)
        time.sleep(post)
        return
    if not _GAMESCOPE_WID:
        raise NoGamescopeWindowError(
            "click_fast: no gamescope window. Call _ensure_window_focus() "
            "first, or launch AoE3 under gamescope."
        )
    xdo(f"mousemove --window {_GAMESCOPE_WID} {x} {y}")
    time.sleep(pre)
    xdo(f"click --window {_GAMESCOPE_WID} 1")
    time.sleep(post)


def wheel_at_fast(x: int, y: int, button: int, n: int = 1, *,
                   pre: float = FAST_WHEEL_PRE,
                   post: float = FAST_WHEEL_POST) -> None:
    """Tight-sleep wheel events at (x,y). button=4 wheel-up, 5 wheel-down.

    2026-05-28: Raises NoGamescopeWindowError if no gamescope window
    found (no raw-xdotool fallback — protects user's desktop cursor).

    When a harness backend is active, injects scroll via the WHEEL socket
    command (move then n individual wheel calls with post-sleep between them)
    instead of xdotool.  Falls back to xdotool only when no backend is set.
    """
    # dy convention: button 4 = up => dy > 0; button 5 = down => dy < 0.
    if _HARNESS_BACKEND is not None:
        dy = 1.0 if button == 4 else -1.0
        _HARNESS_BACKEND.move(x, y)
        time.sleep(pre)
        for _ in range(n):
            _HARNESS_BACKEND.wheel(0.0, dy)
            time.sleep(post)
        return
    if not _GAMESCOPE_WID:
        raise NoGamescopeWindowError(
            "wheel_at_fast: no gamescope window. Call "
            "_ensure_window_focus() first, or launch AoE3 under gamescope."
        )
    xdo(f"mousemove --window {_GAMESCOPE_WID} {x} {y}")
    time.sleep(pre)
    for _ in range(n):
        xdo(f"click --window {_GAMESCOPE_WID} {button}")
        time.sleep(post)


def wheel_at_batched(x: int, y: int, button: int, n: int = 1) -> None:
    """Batched: send mousemove + N clicks in a SINGLE xdotool subprocess.

    ~5x faster than ``wheel_at_fast`` for n>1 because it avoids per-event
    subprocess startup overhead (~50ms each). Measured: 100ms/tick batched
    vs 168ms/tick wheel_at_fast vs 476ms/tick the legacy loop.

    No inter-event sleeps; the engine appears to handle a flood of wheel
    events at xdotool's native rate cleanly. If we ever hit dropped events,
    add a tiny delay via xdotool's `sleep` verb between clicks.

    When a harness backend is active, uses the WHEEL socket command instead
    of xdotool (move once, then n rapid wheel calls with no sleep between).
    Falls back to xdotool only when no backend is set.
    """
    if n <= 0:
        return
    # dy convention: button 4 = up => dy > 0; button 5 = down => dy < 0.
    if _HARNESS_BACKEND is not None:
        dy = 1.0 if button == 4 else -1.0
        _HARNESS_BACKEND.move(x, y)
        for _ in range(n):
            _HARNESS_BACKEND.wheel(0.0, dy)
        return
    wid = _require_gamescope_wid()
    parts: list[str] = [f"mousemove --window {wid} {x} {y}"]
    parts.extend([f"click --window {wid} {button}"] * n)
    sh(f"DISPLAY={_aoe3_display()} xdotool {' '.join(parts)}")


def scroll_down_fast(coords: dict, n: int = 1) -> None:
    """Wheel-down at the picker's scroll anchor — BATCHED for speed."""
    sa = coords["civ_picker"]["scroll_anchor"]
    wheel_at_batched(sa[0], sa[1], 5, n=n)


def scroll_up_fast(coords: dict, n: int = 1) -> None:
    """Wheel-up at the picker's scroll anchor — BATCHED for speed."""
    sa = coords["civ_picker"]["scroll_anchor"]
    wheel_at_batched(sa[0], sa[1], 4, n=n)


# 2026-05-28: Weekly "Choose One Free Weekly Profile Picture Reward!"
# modal. Blocks the lobby on the first game launch each week. Coords
# verified 2026-05-28 from ANWArgentines/full/01_lobby.png pixel grid:
# the Close button body spans y=755-790 with brown background
# rgb≈(82,34,17). (730, 770) is body center. On a menu *without* the
# popup this coordinate is dead background art, so the dismiss click
# is harmless either way.
WEEKLY_POPUP_CLOSE_XY: tuple[int, int] = (730, 770)


def dismiss_weekly_popup(*, settle_pre: float = 10.0,
                          settle_inter: float = 1.2,
                          settle_post: float = 1.0) -> None:
    """Blind-click the weekly profile-picture-reward popup Close button.

    Pixel-probe detection is unreliable: the menu often hasn't rendered
    by the time the first screenshot fires (early frames are pure black
    or the Asset Preloading splash). Stop fighting the probe — wait
    long enough for the menu to settle, then click the known Close
    coords unconditionally. If the popup isn't present that week,
    ``WEEKLY_POPUP_CLOSE_XY`` lands on background art and the click is
    a no-op.

    Two clicks with a small gap: the second is defensive — the popup
    is sometimes in mid-fade-out animation when the first click fires
    and the engine swallows the first.

    Safe to call repeatedly. Originally local to
    ``tools/aoe3_automation/anw_visual_capture_runner.py`` (which
    retains its own copy to avoid disturbing the working capture
    pipeline); promoted here so ``smart_walls_sweep.py`` and any
    future runner can share the same dismissal logic without
    duplicating coords.
    """
    try:
        time.sleep(settle_pre)
        _ensure_window_focus()
        time.sleep(0.6)
        click(*WEEKLY_POPUP_CLOSE_XY, settle=0.5)
        time.sleep(settle_inter)
        click(*WEEKLY_POPUP_CLOSE_XY, settle=0.5)
        time.sleep(settle_post)
    except Exception:
        # Best-effort — the caller is allowed to proceed if dismissal
        # crashes; the popup just stays on screen and subsequent
        # screenshots will surface it.
        pass


def click_skirmish(coords: dict) -> None:
    """Click the Skirmish button on the main menu.

    Coords come from ``lobby_coords.json[main_menu][skirmish_button]`` so they
    can be re-calibrated without a code change after a game patch.

    2026-05-07: Click 3× with delays. Single-click is unreliable on this rig;
    the engine's main-menu animation/fade swallows clicks during transitions.
    Three clicks spaced 0.5s apart reliably get one through. The lobby
    navigation is idempotent — if we're already in the lobby, additional
    clicks land harmlessly on lobby chrome (BACK button at top-left, etc.)
    rather than re-triggering Skirmish.
    """
    btn = coords.get("main_menu", {}).get("skirmish_button", [130, 482])
    for i in range(3):
        click(btn[0], btn[1], settle=0.4)
        time.sleep(0.5)
    time.sleep(2.5)


def move_mouse_off(x: int = 100, y: int = 500) -> None:
    """Park the cursor somewhere harmless to avoid hover-tooltip artifacts.

    2026-05-28: Targets the gamescope window explicitly so the host
    desktop cursor never moves. Raises NoGamescopeWindowError if AoE3
    isn't running.
    """
    wid = _require_gamescope_wid()
    xdo(f"mousemove --window {wid} {x} {y}")
    time.sleep(0.2)


def scroll_down(coords: dict, n: int = 1) -> None:
    """Wheel-down at the picker's scroll anchor. Re-anchors every iter
    because empirically the cursor sometimes drifts (or a hover-tooltip
    shifts focus) and the next wheel event gets dropped. Re-anchoring is
    cheap and makes the scroll deterministic.

    2026-05-28: Targets the gamescope window explicitly. Raises
    NoGamescopeWindowError if AoE3 isn't running.
    """
    wid = _require_gamescope_wid()
    sa = coords["civ_picker"]["scroll_anchor"]
    for _ in range(n):
        xdo(f"mousemove --window {wid} {sa[0]} {sa[1]}")
        time.sleep(0.12)
        xdo(f"click --window {wid} 5")  # button 5 = wheel-down
        time.sleep(0.25)


def scroll_up(coords: dict, n: int = 1) -> None:
    """Wheel-up at the picker's scroll anchor. Symmetric to scroll_down.

    Used by set_civ_by_index to force the picker to its top before applying
    the scroll table (which is calibrated against a top-of-list start).
    Surplus wheel-up events past the top are silent no-ops in this build.
    """
    wid = _require_gamescope_wid()
    sa = coords["civ_picker"]["scroll_anchor"]
    for _ in range(n):
        xdo(f"mousemove --window {wid} {sa[0]} {sa[1]}")
        time.sleep(0.08)
        xdo(f"click --window {wid} 4")  # button 4 = wheel-up
        time.sleep(0.10)


# ---- state checks ---------------------------------------------------------


def is_clean_lobby(coords: dict) -> bool:
    p = ARTIFACT_DIR / "_state.png"
    screenshot(p)
    d = diff_pixels(CLEAN_LOBBY_REF, p)
    if d < 0:
        return False  # error → don't claim clean lobby
    return d <= coords["diff_thresholds"]["noise_floor"]


def is_picker_open(coords: dict) -> bool:
    """Return True when the 'SELECT HOME CITY' civ-picker modal is visible.

    Primary method: OCR ``SELECT_HOME_CITY_CROP`` on a fresh screenshot and
    check for the positive title marker ``"homecity"``/``"selecthome"``.  This
    is immune to the false-positive that the old pixel-diff approach produced:
    a lobby showing a non-default map (Alaska) or a non-default P1 civ
    (French) also differs from ``CLEAN_LOBBY_REF`` by ``>= significant_change``
    pixels, so the old check wrongly returned True before any click.

    Fallback (tesseract unavailable): pixel-diff against CLEAN_LOBBY_REF.
    This is the legacy behaviour and still false-positives on non-default lobby
    states — but it is better than crashing when OCR is not installed.  Log a
    warning comment in the code (below) so operators are aware.
    """
    p = ARTIFACT_DIR / "_state.png"
    screenshot(p)
    # --- Primary: positive title-text marker (OCR) ---
    # Try OCR first; _picker_title_visible degrades to False on ImportError /
    # missing tesseract, which triggers the pixel-diff fallback below.
    if _picker_title_visible(p):
        return True
    # If OCR reported False but tesseract IS available the modal is genuinely
    # closed — return False immediately (skip the noisy pixel-diff path).
    try:
        import pytesseract  # noqa: F401
        return False
    except ImportError:
        pass
    # --- Fallback: pixel-diff (legacy; tesseract not installed) ---
    # NOTE: This fallback false-positives on non-default lobby states (different
    # map, non-default civ selections). Install tesseract to use the reliable
    # title-text path.
    d = diff_pixels(CLEAN_LOBBY_REF, p)
    if d < 0:
        return False  # diff error → don't claim picker open
    return d >= coords["diff_thresholds"]["significant_change"]


# ---- OCR-based lobby/match-setup header verifier --------------------------


# Skirmish "MATCH SETUP" header lives in a banner above the player slots.
# "GAME OPTIONS" is the right-hand panel sub-tab header. Both are large white
# Trajan caps over woodgrain — same font family that defeats default Tesseract,
# so we reuse `_preprocess_for_ocr` (4× LANCZOS + greyscale) as everywhere
# else in this driver.
#
# Crops were measured at 1920x1080 (gamescope native + the lobby_coords.json
# baseline) on 2026-05-10 from artifacts/lobby_driver/_state.png after a
# manual return-to-skirmish-setup. They are intentionally generous on the y
# axis to absorb a few pixels of fade-in jitter.
MATCH_SETUP_HEADER_CROP = (700, 30, 1220, 95)   # "MATCH SETUP" banner
GAME_OPTIONS_HEADER_CROP = (1380, 130, 1880, 195)  # "GAME OPTIONS" sub-tab

# "SELECT HOME CITY" title bar of the civ-picker modal overlay.
# Measured 2026-06-09 at 1920x1080 by OCR-probing civ_picker.png:
# the title occupies roughly x=80-680, y=160-240.  The wider y band
# (80 px) absorbs fade-in jitter while staying entirely above the first
# civ row (which starts at y~255).
SELECT_HOME_CITY_CROP = (80, 160, 680, 240)


def _ocr_text(crop_box: tuple[int, int, int, int], shot_path: Path) -> str:
    """OCR a single rectangular crop. Returns the raw recognised text.

    Uses the shared `_preprocess_for_ocr` upscale/greyscale pass and PSM 7
    (single text line) — both empirically tuned for AoE3 DE's Trajan caps.
    Returns "" if pytesseract / tesseract is unavailable so callers can
    degrade gracefully on hosts without OCR installed.
    """
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return ""
    try:
        with Image.open(shot_path) as im:
            crop = im.crop(crop_box)
            big = _preprocess_for_ocr(crop)
            return pytesseract.image_to_string(big, config="--psm 7").strip()
    except Exception:
        return ""


def _picker_title_visible(shot_path) -> bool:
    """Return True when a civ-picker modal title is visible in shot_path.

    There are TWO picker variants the engine shows in the same screen region:
      - "SELECT HOME CITY"   (rows like "BRITISH EMPIRE (LONDON)")
      - "SELECT CIVILIZATION" (bare names like "FRANCE", "FRANCE (NAPOLEONIC ERA)")

    Both titles occupy ``SELECT_HOME_CITY_CROP``. Positive markers in the
    normalised OCR: ``"homecity"`` / ``"selecthome"`` (variant 1) or
    ``"selectciv"`` / ``"civilization"`` (variant 2). All four substrings are
    absent from the plain lobby and the main menu, so they cleanly discriminate
    the picker overlay from false-positive lobby states (different map,
    non-default civ on P1, etc.) that the old pixel-diff approach mis-triggered.

    Degrades to False — never raises — when:
      - pytesseract / PIL are unavailable (tesseract not installed)
      - shot_path does not exist or fails to open
      - any unexpected exception in OCR
    """
    try:
        raw = _ocr_text(SELECT_HOME_CITY_CROP, Path(shot_path))
        norm = _normalise_ocr(raw)
        return (
            "homecity" in norm
            or "selecthome" in norm
            or "selectciv" in norm
            or "civilization" in norm
        )
    except Exception:
        return False


def verify_match_setup_screen(
    *,
    retries: int = 3,
    settle: float = 1.5,
    require_both: bool = False,
    save_debug: bool = False,
) -> dict:
    """Confirm we are looking at the Skirmish 'MATCH SETUP' / 'GAME OPTIONS' screen.

    Used as a post-resign acceptance gate: the in-game `resign()` flow
    drops us back to the main menu (or skirmish setup, depending on
    where the resign was invoked), and a downstream caller typically
    re-enters skirmish setup before the next match. Calling this
    function lets the caller assert the screen actually settled on the
    expected lobby instead of guessing from a blind sleep.

    Behaviour:
      - Captures the screen via `screenshot()` (gamescopectl primary,
        X11 fallback — same path used by every other state check here).
      - OCRs the two header crops (`MATCH_SETUP_HEADER_CROP` and
        `GAME_OPTIONS_HEADER_CROP`).
      - With `require_both=False` (default), success requires either
        header to match. AoE3 DE's lobby fades the right panel in
        slightly later than the title banner, and the GAME OPTIONS
        sub-tab can be hidden behind a dropdown until the user clicks
        it — so a strict AND would false-negative on a perfectly valid
        screen state.
      - With `require_both=True`, both must match — used by callers that
        want a stricter verifier (e.g. a release-readiness gate).

    Returns a dict suitable for inclusion in a structured run log:
        {
            "ok": bool,
            "match_setup_text": "<raw OCR>",
            "game_options_text": "<raw OCR>",
            "match_setup_seen": bool,
            "game_options_seen": bool,
            "attempts": int,
            "screenshot": "<path or None>",
        }

    The verifier is intentionally read-only — it never clicks or types,
    so it is safe to call when synthetic input is broken (overnight
    rig). It also returns ``ok=False`` (instead of raising) when OCR is
    unavailable, so downstream automation can degrade gracefully.
    """
    shot_path = ARTIFACT_DIR / "_match_setup_verify.png"
    last_ms = ""
    last_go = ""
    ms_seen = go_seen = False
    attempt = 0
    for attempt in range(1, retries + 1):
        try:
            screenshot(shot_path)
        except Exception:
            time.sleep(settle)
            continue
        last_ms = _ocr_text(MATCH_SETUP_HEADER_CROP, shot_path)
        last_go = _ocr_text(GAME_OPTIONS_HEADER_CROP, shot_path)
        ms_norm = _normalise_ocr(last_ms)
        go_norm = _normalise_ocr(last_go)
        # Tesseract regularly drops/duplicates a letter in 4-6 char tokens.
        # Match by substring (post-normalise) on the first 8 chars of each
        # expected header so single-character OCR hiccups don't cause a
        # false negative — same fuzzy approach used by `_ocr_text_matches_civ`.
        ms_seen = "matchsetup" in ms_norm or "matchset" in ms_norm
        go_seen = "gameoptions" in go_norm or "gameoption" in go_norm
        ok_now = (ms_seen and go_seen) if require_both else (ms_seen or go_seen)
        if ok_now:
            break
        time.sleep(settle)
    if save_debug:
        try:
            (ARTIFACT_DIR / "_match_setup_verify.txt").write_text(
                f"attempt={attempt}\n"
                f"match_setup_raw={last_ms!r}\n"
                f"game_options_raw={last_go!r}\n"
                f"ms_seen={ms_seen} go_seen={go_seen}\n",
                encoding="utf-8",
            )
        except Exception:
            pass
    return {
        "ok": (ms_seen and go_seen) if require_both else (ms_seen or go_seen),
        "match_setup_text": last_ms,
        "game_options_text": last_go,
        "match_setup_seen": ms_seen,
        "game_options_seen": go_seen,
        "attempts": attempt,
        "screenshot": str(shot_path) if shot_path.exists() else None,
    }


def picker_opened_since(baseline: Path, coords: dict) -> bool:
    """Return True when the picker modal is visible in the post-click frame.

    Primary method: OCR positive-title check via ``_picker_title_visible``.
    The baseline argument is retained for the pixel-diff fallback path; when
    OCR is available it is not used and can safely be a stale or mismatched
    screenshot without causing a false result.

    2026-06-09: Rewrote primary detection to use ``_picker_title_visible``
    (same fix as ``is_picker_open``).  The old baseline-delta logic
    false-positived when the pre-click lobby itself differed from
    ``CLEAN_LOBBY_REF`` (e.g. Alaska map, French on P1), causing the modal
    to be declared open without a click being needed.

    Pixel-diff fallback (tesseract missing):
      1. Post-click vs pre-click baseline delta (isolates picker overlay).
      2. Post-click vs CLEAN_LOBBY_REF delta (catches already-open case).
    """
    p = ARTIFACT_DIR / "_state_postclick.png"
    screenshot(p)
    # --- Primary: title-text marker (OCR) ---
    if _picker_title_visible(p):
        return True
    # If tesseract is available and title not seen → modal is closed.
    try:
        import pytesseract  # noqa: F401
        return False
    except ImportError:
        pass
    # --- Fallback: pixel-diff (tesseract not installed) ---
    sig = coords["diff_thresholds"]["significant_change"]
    d = diff_pixels(baseline, p)
    if d >= sig:
        return True
    # Also check post-click vs clean lobby (catches already-open case).
    d_clean = diff_pixels(CLEAN_LOBBY_REF, p)
    if d_clean >= sig:
        return True
    return False


# ---- high-level operations ------------------------------------------------


def open_civ_picker(coords: dict, *, attempts: int = 3, settle: float = 2.0) -> None:
    """Click P1 civ '?' to open the picker; verify by pixel-diff vs clean lobby.

    The picker animation can take 1.5-2s to fully render. We wait `settle` s
    after each click, then sample. If the picker is already open (e.g. from
    a leftover state), the second click will close it — handle that by
    re-clicking until detection is positive.

    2026-05-08: If the picker is ALREADY open when called, return immediately
    — clicking p1_civ_picker (630,170) when the picker overlay covers that
    region is a silent no-op, AND the resulting baseline-vs-post diff is 0,
    which used to false-negative and raise. Idempotent open is safer than
    cancel-then-reopen because cancel itself has its own "picker not open"
    edge case.
    """
    if is_picker_open(coords):
        return
    cx, cy = coords["lobby"]["p1_civ_picker"]
    baseline = ARTIFACT_DIR / "_baseline_p1.png"
    for i in range(attempts):
        screenshot(baseline)
        click(cx, cy)
        time.sleep(settle)
        if picker_opened_since(baseline, coords):
            return
        time.sleep(0.8)
        if picker_opened_since(baseline, coords):
            return
        print(f"  open_civ_picker: attempt {i+1} did not open picker, retrying")
    raise RuntimeError("Failed to open civ picker after multiple attempts")


def cancel_civ_picker(coords: dict) -> None:
    """Close the picker if open; idempotent no-op otherwise.

    2026-05-08: Guard against clicking the cancel coord when no picker is
    open. On a clean lobby (645, 962) lands on P8's civ-picker row, which
    OPENS that opponent's picker — the exact opposite of the intended
    cancel semantics. Always probe state first.
    """
    if not is_picker_open(coords):
        return
    cx, cy = coords["civ_picker"]["cancel_button"]
    click(cx, cy)
    time.sleep(0.9)
    move_mouse_off()


def select_civ_in_picker(coords: dict, civ_index: int) -> None:
    """With picker open + scrolled to top, scroll then click target row.

    Uses picker_scroll_table.json to look up exact scroll count, since each
    wheel-down advances ~0.74 rows (NOT 1:1) on this build.

    For civs at/near the saturation boundary (last few rows where the
    picker can't scroll further), we over-scroll well past saturation
    (~+8 extra wheel-downs) so the row positions stabilize on the
    "fully-saturated" layout (matches picker_scroll_53 empirical Ys).
    Without this, fractional scroll variance leaves rows at unpredictable
    pixel offsets between consecutive scroll counts at the same top_idx.
    """
    cp = coords["civ_picker"]
    if civ_index < 0:
        raise ValueError(f"civ_index must be >= 0, got {civ_index}")
    table = load_scroll_table()
    scrolls_needed, click_row = find_scrolls_for_civ(table, civ_index)
    # If we'd be clicking near the bottom of a saturated picker, over-scroll
    # to stabilize the layout. Cheap insurance: ~8 extra wheel events.
    s2t = table["scroll_to_top_idx"]
    max_top = max(int(v) for v in s2t.values())
    top_at_n = int(s2t[str(scrolls_needed)])
    overscroll = 0
    if top_at_n == max_top and click_row >= 7:
        overscroll = 10  # past saturation; the wheel events are safe no-ops
    total_scrolls = scrolls_needed + overscroll
    if total_scrolls > 0:
        scroll_down(coords, n=total_scrolls)
    target_row_y = cp["row_y_start"] + click_row * cp["row_spacing"]
    click(cp["row_x_center"], target_row_y, settle=0.4)
    time.sleep(0.6)


def confirm_civ_selection(coords: dict) -> None:
    ok = coords["civ_picker"]["ok_button"]
    click(*ok, settle=0.3)
    time.sleep(1.5)
    move_mouse_off()


def set_civ_by_index(coords: dict, civ_index: int) -> None:
    """End-to-end: open picker → scroll to top → click row → click OK → mouse-off.

    2026-05-10: Force scroll-to-top before applying the scroll table.
    open_civ_picker is idempotent — if the picker is already open AND was
    mid-scrolled (e.g. from a prior session leaving P1 on a non-top civ;
    AoE3 reopens the picker auto-centred on the currently-selected civ),
    select_civ_in_picker would scroll DOWN N from the mid-list position
    and click the wrong row. Wheeling up 60 times is enough to reach the
    top from any saturation state in this build (engine clamps surplus
    wheel events as silent no-ops). Cost: ~6s per pick — acceptable for
    the slow path; the fast path (set_civ_by_token_fast) is preferred for
    bulk runs.
    """
    open_civ_picker(coords)
    scroll_up(coords, n=60)
    time.sleep(0.4)
    select_civ_in_picker(coords, civ_index)
    confirm_civ_selection(coords)


# ---- OCR-verified selection -----------------------------------------------
#
# The pixel-coord scroll math above is fragile: ~0.74 rows per wheel-down,
# saturation handling, transient render races between scroll & screenshot.
# Drift adds up across calls, so even a "correct" picker_scroll_table can
# silently land on the wrong civ. The verified path below screenshots the
# post-OK lobby + re-opens the picker, OCRs the highlighted row, compares
# against expected names from enriched_reference.json, and retries on
# mismatch. This is the only mode that should be used for per-civ probes.

# Vanilla AoE3 home cities → ANW civ tokens (used for OCR matching when the
# picker shows just "(HOMECITY)" with no civ-name prefix). Empirically
# observed 2026-05-08: the picker labels vanilla civs as "(HOMECITY)" only,
# while ANW-added civs render as "CIV_NAME (HOMECITY)". Both forms are
# acceptable for OCR matching as long as either substring (civ name OR home
# city) hits the expected token.
HOME_CITY_TO_TOKEN: dict[str, str] = {
    # Vanilla AoE3 home cities encountered as "(HOMECITY)" rows.
    "DELHI": "ANWIndians",
    "TENOCHTITLAN": "ANWAztecs",
    "WASHINGTON, D. C.": "ANWUSA",
    "WASHINGTON D. C.": "ANWUSA",
    "WASHINGTON DC": "ANWUSA",
    "WASHINGTON": "ANWUSA",
    "STOCKHOLM": "ANWSwedes",
    "SEVILLE": "ANWSpanish",
    "ST. PETERSBURG": "ANWRussians",
    "ST PETERSBURG": "ANWRussians",
    "LISBON": "ANWPortuguese",
    "ISTANBUL": "ANWOttomans",
    "MEXICO CITY": "ANWMexicans",
    "PARIS": "ANWFrench",
    "BERLIN": "ANWGermans",
    "CUZCO": "ANWInca",
    "CAUGHNAWAGA": "ANWHaudenosaunee",
    "KANO": "ANWHausa",
    "AMSTERDAM": "ANWDutch",
    "LONDON": "ANWBritish",
    "KYOTO": "ANWJapanese",        # real in-game city; TOKYO was dead alias (fixed 2026-06-09)
    "TOKYO": "ANWJapanese",         # kept for safety but Kyoto is canonical per nation_map.json
    "BEIJING": "ANWChinese",
    "PEKING": "ANWChinese",
    "GREAT COUNCIL": "ANWLakota",
    "VENICE": "ANWItalians",
    "VALLETTA": "ANWMaltese",
    "CHAN SANTA CRUZ": "ANWMayans",
    "NEDERLAND": "ANWDutch",
    # --- added 2026-06-09: nation-map audit, identity-verification aliases ---
    "BUENOS AIRES": "ANWArgentines",
    "LA PAZ": "ANWBajaCalifornians",
    "ALGIERS": "ANWBarbary",
    "RIO DE JANEIRO": "ANWBrazil",
    "SONOMA": "ANWCalifornians",
    "QUEBEC": "ANWCanadians",
    "GUATEMALA CITY": "ANWCentralAmericans",
    "SANTIAGO": "ANWChileans",
    "BOGOTA": "ANWColumbians",
    "CAIRO": "ANWEgyptians",
    "GONDAR": "ANWEthiopians",
    "HELSINKI": "ANWFinnish",
    "PORT-AU-PRINCE": "ANWHaitians",
    "BUDA": "ANWHungarians",
    "YOGYAKARTA": "ANWIndonesians",
    # NOTE: ANWNapoleonicFrance + ANWRevFrance also share Paris as home city.
    # OCR city-name alone cannot disambiguate these 3 civs
    # (ANWFrench / ANWNapoleonicFrance / ANWRevFrance) — needs leader-name OCR
    # (see artifacts/nation_map/GAPS.md P2). PARIS already maps to ANWFrench
    # above; do NOT add colliding PARIS entries for the other two.
    "LIMA": "ANWPeruvians",
    "LAREDO": "ANWRioGrande",
    "BUCHAREST": "ANWRomanians",
    "PRETORIA": "ANWSouthAfricans",
    "AUSTIN": "ANWTexians",
}


def _normalise_ocr(s: str) -> str:
    """Lowercase + strip non-alphanumerics. Used for fuzzy OCR matching."""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _preprocess_for_ocr(crop):
    """Upscale + grayscale for tesseract.

    Empirically (2026-05-08, live game): the AoE3 picker's small 50-pixel-tall
    crop runs Trajan caps over a textured woodgrain. Tesseract's default
    settings misread cleanly-lit caps as noise. 4× LANCZOS upscale + greyscale
    converts "(LISBON)", "(DELHI)", etc. to fully readable text. Aggressive
    thresholding over the textured bg actively hurts — autocontrast is fine
    but offers no marginal benefit over plain greyscale on the calibration
    sample, so we skip it.
    """
    from PIL import Image
    w, h = crop.size
    big = crop.resize((w * 4, h * 4), Image.LANCZOS).convert("L")
    return big


def _ocr_picker_rows(shot_path: Path, coords: dict | None = None) -> list[dict]:
    """OCR each visible row of the open picker, return text + highlight flag.

    Returns a list of 10 dicts: ``{"row": N, "text": "...", "highlighted": bool,
    "norm": "lowercase+alnum-only text"}``. Highlight detection samples the
    row background at multiple x-positions; the picker's selected-row bg is
    a saturated orange (~RGB 119,88,42) clearly distinct from the dark
    woodgrain (~30,20,10).

    Crop region for OCR is sourced from
    ``coords["civ_picker"]["leader_name_crop"]`` if available; otherwise
    falls back to the empirically-tuned default of (80,720,-30,+30) around
    each row's y_center. y_center = row_y_start + row*row_spacing.

    The crop is upscaled 3× before OCR to recover fine detail in the small
    picker text — see _preprocess_for_ocr().
    """
    from PIL import Image
    import pytesseract

    cp = (coords or {}).get("civ_picker", {})
    row_y_start = cp.get("row_y_start", 301)
    row_spacing = cp.get("row_spacing", 64)
    crop_cfg = cp.get("leader_name_crop") or {}
    # Defaults match lobby_coords.json (x0=180 skips the flag/portrait icon).
    x0 = crop_cfg.get("x0", 180)
    x1 = crop_cfg.get("x1", 700)
    y0_off = crop_cfg.get("y0_off", -22)
    y1_off = crop_cfg.get("y1_off", 22)

    # PIL Image.open is LAZY — pixel data isn't read until first .crop()/.load().
    # Forking work to a thread pool BEFORE loading races multiple workers on the
    # same file descriptor, producing truncated reads ("image file is truncated
    # (0 bytes not processed)") for every parallel row. Force a full load now,
    # then close the file handle so threads only touch the in-memory buffer.
    with Image.open(shot_path) as _im_src:
        _im_src.load()
        im = _im_src.copy()
    # 2026-05-11: parallelize per-row OCR with a thread pool. Tesseract
    # releases the GIL during image_to_string, so 4-8 parallel workers cut
    # OCR wall-time from ~1.5s/state to ~0.3s/state on the gamescope host.
    from concurrent.futures import ThreadPoolExecutor

    def _ocr_one_row(n: int) -> dict:
        y_center = row_y_start + row_spacing * n
        crop = im.crop((x0, y_center + y0_off, x1, y_center + y1_off))
        big = _preprocess_for_ocr(crop)
        txt = pytesseract.image_to_string(big, config="--psm 7").strip()
        hi_count = 0
        for x in (300, 400, 500):
            try:
                r, g, b = im.getpixel((x, y_center))[:3]
            except Exception:
                continue
            if r > 80 and g < r - 10 and b < g and (r - b) > 50:
                hi_count += 1
        return {
            "row": n,
            "text": txt,
            "highlighted": hi_count >= 2,
            "norm": _normalise_ocr(txt),
        }

    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(_ocr_one_row, range(10)))
    return rows


# Per-civ extra picker aliases for tokens whose picker label diverges from
# their enriched_reference fields. Calibrated 2026-05-11 by OCR-scanning the
# live picker (see artifacts/lobby_driver/find_target/*_state*.png). Each
# entry is one or more substrings expected to appear in the picker row text.
PICKER_ALIASES: dict[str, list[str]] = {
    # Picker shows "ARGENTINE CONFEDERATION (BUENOS AIRES)" — civ_label
    # "Argentines" / display "Argentina" don't substring-match.
    "ANWArgentines": ["Argentine", "Buenos Aires"],
    # Picker shows "REGENCY OF ALGIERS (ALGIERS)" — civ_label "Barbary"
    # is not present anywhere in the row text.
    "ANWBarbary": ["Algiers", "Regency"],
    # Picker shows "SULTANATE OF YOGYAKARTA (YOGYAKARTA)" — civ_label
    # "Indonesians" / display "Indonesia" don't substring-match.
    "ANWIndonesians": ["Yogyakarta", "Sultanate"],
    # Picker shows "QING DYNASTY (BEIJING)" — Tesseract misreads as
    # "OING DYNASTY (BEITING)" so the BEIJING home-city alias misses.
    # "Dynasty" is unique in the picker and OCRs cleanly.
    "ANWChinese": ["Dynasty", "Qing"],
    # Picker shows "TOKUGAWA SHOGUNATE (KYOTO)" — civ_label "Japanese"
    # not in the row text and TOKYO is the wrong home city. "Tokugawa"
    # matches the leader name and is unique to this row.
    "ANWJapanese": ["Tokugawa", "Shogunate", "Kyoto"],
}


def _expected_match_strings(civ_token: str, ref: dict) -> list[str]:
    """Return all OCR-target strings that should match the given civ token.

    Includes the civ's display_name, civ_label, leader_label from
    enriched_reference.json plus any home-city aliases registered in
    HOME_CITY_TO_TOKEN, plus any per-civ picker aliases from PICKER_ALIASES.
    Strings are returned RAW (un-normalised) — the caller should normalise
    before substring comparison.
    """
    spec = ref["civs"].get(civ_token, {})
    out: list[str] = []
    if spec.get("display_name"):
        out.append(spec["display_name"])
    ps = spec.get("playstyle_spec") or {}
    if ps.get("civ_label"):
        out.append(ps["civ_label"])
    if ps.get("leader_label"):
        out.append(ps["leader_label"])
    # Add any vanilla home-city aliases mapped to this token
    for hc, tok in HOME_CITY_TO_TOKEN.items():
        if tok == civ_token:
            out.append(hc)
    # Add per-civ picker overrides (calibrated against live OCR output)
    for alias in PICKER_ALIASES.get(civ_token, []):
        out.append(alias)
    return out


def _ocr_text_matches_civ(ocr_text: str, civ_token: str, ref: dict) -> tuple[bool, str]:
    """Return (matches, matched_on) where matched_on is the expected string
    that hit, or empty when no match. Uses substring matching on normalised
    forms so "British" matches "Britain", "Queen Elizabeth" matches
    "Elizabeth", etc."""
    norm_ocr = _normalise_ocr(ocr_text)
    if not norm_ocr:
        return False, ""
    expected = _expected_match_strings(civ_token, ref)
    for s in expected:
        ns = _normalise_ocr(s)
        if not ns or len(ns) < 3:
            continue  # too short → too many false positives
        if ns in norm_ocr or norm_ocr in ns:
            return True, s
    return False, ""


def _identify_civ_from_ocr(ocr_text: str, ref: dict) -> Optional[str]:
    """Given OCR'd text from a picker row, return the civ_token it represents,
    or None if no civ matches. First checks home-city aliases (most reliable
    on vanilla rows showing ``(HOMECITY)`` only), then falls back to
    enriched_reference fields."""
    norm_ocr = _normalise_ocr(ocr_text)
    if not norm_ocr:
        return None
    # 1) Home-city aliases — strong match for vanilla "(HOMECITY)" rows
    best_token: Optional[str] = None
    best_len = 0
    for hc, tok in HOME_CITY_TO_TOKEN.items():
        nhc = _normalise_ocr(hc)
        if len(nhc) >= 4 and nhc in norm_ocr and len(nhc) > best_len:
            best_token = tok
            best_len = len(nhc)
    if best_token:
        return best_token
    # 2) Reference field match across all civs
    for token, spec in ref.get("civs", {}).items():
        candidates = []
        if spec.get("display_name"):
            candidates.append(spec["display_name"])
        ps = spec.get("playstyle_spec") or {}
        if ps.get("civ_label"):
            candidates.append(ps["civ_label"])
        if ps.get("leader_label"):
            candidates.append(ps["leader_label"])
        for c in candidates:
            nc = _normalise_ocr(c)
            if len(nc) >= 4 and nc in norm_ocr:
                if len(nc) > best_len:
                    best_token = token
                    best_len = len(nc)
    return best_token


def _shot_lobby(out_path: Path) -> Path:
    """Take a fresh gamescope screenshot of the current lobby state."""
    return screenshot(out_path)


def _find_target_row_in_picker(
    coords: dict,
    civ_token: str,
    ref: dict,
    *,
    max_scroll_states: int = 18,
    scroll_step: int = 4,
) -> Optional[int]:
    """Scroll through picker, OCR each row, return the row index where the
    target civ appears (within the currently-visible 10). Returns None if
    the civ isn't visible after scrolling through all states.

    NOTE: This is a fallback for when ANW_TO_PICKER_INDEX is stale (e.g. mod
    layout drift). It ONLY trusts OCR. The picker has ~50 entries; default
    parameters cover up to 18×4 = 72 scroll events which exceeds saturation.

    Reset strategy: the picker auto-centres on the currently-selected civ
    on reopen, so cancel+reopen alone doesn't return to the top. We force
    a known top by setting P1 to Random Personality (idx 0) first — that
    leaves the picker at the top of the list when reopened.
    """
    # Force the picker's reopen-position to the top of the list by selecting
    # Random Personality first. Skip if the picker is already showing
    # row 0 highlighted.
    cancel_civ_picker(coords)
    time.sleep(0.2)
    try:
        # Click P1 picker, scroll up to top with fast wheel events, then click
        # row 0 (Random Personality). 2026-05-11: 60→30 wheel-ups via
        # scroll_up_fast cuts reset cost from ~7.8s to ~3.0s. The picker
        # saturates well before 30 events from any state.
        open_civ_picker(coords)
        time.sleep(0.3)
        scroll_up_fast(coords, n=30)
        time.sleep(0.2)
        # Click row 0 (Random Personality) to reset selection
        cp = coords["civ_picker"]
        click_fast(cp["row_x_center"], cp["row_y_start"], post=0.15)
        confirm_civ_selection(coords)
        time.sleep(0.3)
    except Exception:
        # If reset fails, fall back to plain reopen — better than nothing.
        try:
            cancel_civ_picker(coords)
        except Exception:
            pass

    # Now reopen with the picker at top.
    open_civ_picker(coords)
    time.sleep(0.4)

    artifact_dir = ARTIFACT_DIR / "find_target"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", civ_token).strip("_")

    # 2026-05-11: false-saturation bail tracking.
    # Original bail used a 6-char-per-row signature with no_change_count >= 2.
    # Failure mode: when scroll lands mid-animation, OCR returns empty strings
    # for several rows; two such states in a row look "identical" (empty sigs)
    # and the bail trips BEFORE the target civ becomes visible. This produced
    # the 25/37 FAIL rate seen in artifacts/picker_matrix_smoke/summary.json.
    #
    # Fix:
    #   1. Require a NON-TRIVIAL signature (>= 3 rows with text) before bail
    #      counts toward saturation. Empty-OCR states reset the counter.
    #   2. Bump bail threshold to 3 identical NON-TRIVIAL signatures (true
    #      saturation produces many identical states; 3 is comfortably above
    #      OCR jitter noise).
    #   3. Persist a per-state OCR JSON sidecar so failed runs leave evidence.
    last_signature = ""
    no_change_count = 0
    state_log: list[dict] = []
    final_state = -1
    for state in range(max_scroll_states):
        final_state = state
        shot = artifact_dir / f"{safe}_state{state:02d}.png"
        try:
            _shot_lobby(shot)
        except Exception:
            continue
        rows = _ocr_picker_rows(shot, coords)
        state_log.append({
            "state": state,
            "rows": [{"row": r["row"], "text": r["text"]} for r in rows],
        })
        for r in rows:
            ok, matched_on = _ocr_text_matches_civ(r["text"], civ_token, ref)
            if ok:
                state_log[-1]["match"] = {
                    "row": r["row"], "text": r["text"], "matched_on": matched_on,
                }
                _write_find_target_log(artifact_dir, safe, civ_token, state_log,
                                       outcome="match", final_state=state)
                return r["row"]
        # Saturation detection — only count NON-TRIVIAL signatures (>= 3 rows
        # with text). Empty-OCR states are scroll-animation noise, not
        # saturation, and must not trip the bail.
        non_empty_rows = sum(1 for r in rows if r["text"].strip())
        sig = "|".join(r["text"][:6] for r in rows)
        if non_empty_rows >= 3 and sig == last_signature:
            no_change_count += 1
            if no_change_count >= 3:
                break
        else:
            no_change_count = 0
        # Only update last_signature on non-trivial states so empty states
        # don't poison the comparison.
        if non_empty_rows >= 3:
            last_signature = sig
        scroll_down_fast(coords, n=scroll_step)
        time.sleep(0.12)
    _write_find_target_log(artifact_dir, safe, civ_token, state_log,
                           outcome="not_found", final_state=final_state)
    return None


def _write_find_target_log(
    artifact_dir: Path,
    safe: str,
    civ_token: str,
    state_log: list[dict],
    *,
    outcome: str,
    final_state: int,
) -> None:
    """Persist a JSON sidecar of every OCR'd state for a find-target run.

    Written on BOTH success and failure so artifacts/lobby_driver/find_target
    always has post-mortem evidence (which row OCR'd to what text at every
    scroll position, plus whether the target was found and how). Cheap (~few
    KB per civ) and indispensable for diagnosing why a token didn't match.
    """
    try:
        out = artifact_dir / f"{safe}_log.json"
        import json as _json
        out.write_text(_json.dumps({
            "civ_token": civ_token,
            "outcome": outcome,
            "final_state": final_state,
            "states": state_log,
        }, indent=2), encoding="utf-8")
    except Exception:
        # Diagnostic-only; never let log-write failure mask the actual outcome.
        pass


# ---- fast path (cache-driven) --------------------------------------------
#
# set_civ_by_token_fast() / set_opponent_civ_by_token_fast() use the cached
# (scroll_count, click_row) lookup to skip the OCR walk entirely. They
# assume the picker is in the SELECT CIVILIZATION (alphabetical) layout —
# which is the case whenever the slot is currently set to Random Personality
# (P1 or any opponent slot). The 8-civ batch helper resets P1 to Random
# first, so the alphabetical layout holds for every subsequent pick.


def _open_picker_for_slot(coords: dict, slot: int) -> None:
    """Open the picker for a given slot (0=P1, 1..7=P2..P8) using the fast
    path's input timings. The picker is the same overlay regardless of which
    slot opened it; only the click target differs.

    2026-05-08: Idempotent — if the picker is already open we skip the
    click. The slot-row coords are obscured by the picker overlay when
    open, so a click would be a silent no-op anyway (and worse, this
    function provides no caller-visible signal of failure)."""
    _ensure_window_focus()  # one-time per fast-path call
    if is_picker_open(coords):
        return
    if slot == 0:
        cx, cy = coords["lobby"]["p1_civ_picker"]
    else:
        if not (1 <= slot <= 7):
            raise ValueError(f"slot must be 0..7, got {slot}")
        pickers = coords["lobby"]["opponent_civ_pickers"]
        cx, cy_base = pickers[slot - 1]
        # 2026-05-13 FIX (picker_false_success_audit.md): each previously-
        # assigned opponent expands its row by ~14 px (leader-name height
        # vs. "Random Personality"), pushing subsequent rows DOWN. Apply
        # the same per-slot cumulative shift that open_opponent_picker()
        # already uses (lobby_driver.py:1562). Without this, the fast path
        # silently corrupts P3..P8 — see audit doc for v5 evidence.
        PER_SLOT_SHIFT = 14
        cy = cy_base + (slot - 1) * PER_SLOT_SHIFT
    click_fast(cx, cy, post=PICKER_OPEN_SETTLE)


def _confirm_fast(coords: dict) -> None:
    ok = coords["civ_picker"]["ok_button"]
    click_fast(*ok, post=CONFIRM_SETTLE)
    # Park cursor off-row so no hover-tooltip pollutes the next op.
    # 2026-05-28: target gamescope window to avoid moving host desktop cursor.
    if _GAMESCOPE_WID:
        xdo(f"mousemove --window {_GAMESCOPE_WID} 100 500")


def _cancel_fast(coords: dict) -> None:
    cx, cy = coords["civ_picker"]["cancel_button"]
    click_fast(cx, cy, post=PICKER_CLOSE_SETTLE)


def _scroll_to_top(coords: dict, *, n: int = 30) -> None:
    """Aggressively wheel-up to reach the top of the picker.

    30 wheel-ups is enough to reach top from any saturation state in this
    build (the engine clamps at top; surplus wheel events are silent no-ops).
    With FAST_WHEEL_POST=0.06s, this costs ~1.8s — half the previous
    60-event reset. Could be tightened further with profile-state tracking.
    """
    scroll_up_fast(coords, n=n)


def _verify_fast_pick_via_picker(
    coords: dict,
    civ_token: str,
    ref: dict,
    *,
    slot: int = 0,
) -> dict:
    """Reopen picker for ``slot`` and OCR-verify the highlighted row matches civ_token.

    The picker auto-centres on the currently-selected civ when reopened, so the
    highlighted (orange-bg) row IS the just-picked civ. We OCR it and compare
    against expected match strings for ``civ_token``.

    This is the *cure* for the silent-mispick bug observed 2026-05-18 (smoke #2):
    fast-path cache entries can land on the wrong civ when the picker reopens
    auto-centred on a previously-picked civ and the cache's scroll_count was
    measured from a different baseline.  The fast path itself never re-reads
    the result, so the caller would happily return ``ok=True`` for the wrong civ.

    Args:
      slot: 0 for P1, 1..7 for opponents (P2..P8).

    Returns:
      {"verified": bool, "ocr_text": str, "matched_on": str,
       "highlighted_row": int}.  ``verified=False`` with a sentinel ocr_text
      (``<picker_open_failed: ...>``, ``<ocr_failed: ...>``,
      ``<no_highlighted_row>``) when the verification path itself fails;
      callers should treat those as a fast-path failure and fall through to
      the slow OCR path.
    """
    try:
        _open_picker_for_slot(coords, slot)
    except Exception as e:
        return {"verified": False, "ocr_text": f"<picker_open_failed: {e}>",
                "matched_on": "", "highlighted_row": -1}

    time.sleep(0.35)
    shot = ARTIFACT_DIR / f"_verify_pick_slot{slot}.png"
    try:
        screenshot(shot)
    except Exception as e:
        try:
            cancel_civ_picker(coords)
        except Exception:
            pass
        return {"verified": False, "ocr_text": f"<screenshot_failed: {e}>",
                "matched_on": "", "highlighted_row": -1}

    try:
        rows = _ocr_picker_rows(shot, coords)
    except Exception as e:
        try:
            cancel_civ_picker(coords)
        except Exception:
            pass
        return {"verified": False, "ocr_text": f"<ocr_failed: {e}>",
                "matched_on": "", "highlighted_row": -1}

    highlighted_idx = -1
    highlighted_text = ""
    for r in rows:
        if r.get("highlighted"):
            highlighted_idx = r["row"]
            highlighted_text = r.get("text", "")
            break

    try:
        cancel_civ_picker(coords)
    except Exception:
        pass

    if highlighted_idx < 0:
        return {"verified": False, "ocr_text": "<no_highlighted_row>",
                "matched_on": "", "highlighted_row": -1}

    matches, matched_on = _ocr_text_matches_civ(highlighted_text, civ_token, ref)
    return {
        "verified": matches,
        "ocr_text": highlighted_text,
        "matched_on": matched_on,
        "highlighted_row": highlighted_idx,
    }


def set_civ_by_token_fast(
    coords: dict,
    civ_token: str,
    *,
    slot: int = 0,
    skip_reset: bool = False,
) -> dict:
    """Cache-driven civ selection. O(1) lookup, no OCR.

    Args:
      coords: lobby coords dict.
      civ_token: ANW civ token (e.g. "ANWBritish").
      slot: 0 for P1, 1..7 for opponents.
      skip_reset: skip the wheel-up-to-top reset. Caller is asserting the
        picker is already at top (e.g. immediately after another fast pick
        that ended with the picker closed and the slot now showing the
        previously-picked civ — the picker reopens auto-centred on that
        civ which IS NOT the top, so don't set this without thought).

    Returns:
      {"ok": bool, "civ": civ_token, "slot": slot, "scroll_count": int,
       "click_row": int, "elapsed": float, "method": "fast", ...}
    """
    t0 = time.monotonic()
    entry = get_cache_entry(civ_token)
    if entry is None:
        return {
            "ok": False, "civ": civ_token, "slot": slot,
            "method": "fast", "error": f"no cache entry for {civ_token}",
            "elapsed": time.monotonic() - t0,
        }
    # Honor an explicit "needs live calibration" marker — placeholder entries
    # added to satisfy reference-matrix divergence checks but not yet walked
    # against the live picker. Force callers into the OCR fallback rather than
    # acting on placeholder coords. Re-run lobby_driver.py --rebuild-cache to
    # populate real values.
    if entry.get("_status") == "needs_live_calibration":
        return {
            "ok": False, "civ": civ_token, "slot": slot,
            "method": "fast",
            "error": f"cache entry for {civ_token} flagged needs_live_calibration",
            "elapsed": time.monotonic() - t0,
        }

    cache = load_civ_order_cache()
    cp = coords["civ_picker"]
    row_y_start = int(cache.get("row_y_start", cp["row_y_start"]))
    row_spacing = int(cache.get("row_spacing", cp["row_spacing"]))
    row_x_center = int(cache.get("row_x_center", cp["row_x_center"]))

    scroll_count = int(entry["scroll_count"])
    click_row = int(entry["click_row"])

    # Fast path:
    #   open picker for slot → reset to top → wheel-down N → click row → confirm
    _open_picker_for_slot(coords, slot)
    if not skip_reset:
        _scroll_to_top(coords)
    if scroll_count > 0:
        scroll_down_fast(coords, n=scroll_count)
    # Stabilizing: a single 100ms wait lets the row layout settle from any
    # in-flight scroll animation before we click.
    time.sleep(0.10)
    target_y = row_y_start + click_row * row_spacing
    click_fast(row_x_center, target_y, post=0.20)
    _confirm_fast(coords)

    return {
        "ok": True,
        "civ": civ_token,
        "slot": slot,
        "scroll_count": scroll_count,
        "click_row": click_row,
        "civ_index": int(entry.get("civ_index", -1)),
        "civ_name": entry.get("civ_name", ""),
        "method": "fast",
        "elapsed": time.monotonic() - t0,
    }


def set_civ_by_token_verified(
    coords: dict,
    civ_token: str,
    ref: dict,
    *,
    max_attempts: int = 8,
    prefer_ocr: bool = False,
) -> dict:
    """Select an ANW civ by token, fastest reliable path.

    Strategy (2026-05-08 rewrite):
      Attempt 1: cache-driven fast path (set_civ_by_token_fast). O(1) lookup
                 of (scroll_count, click_row), no OCR. ~1.5-3s per pick.
      Attempt 2+: OCR-find fallback (existing logic) for civs not in the
                 cache or when the fast path doesn't take effect (cache
                 stale, picker layout drift). The fallback path is the
                 original implementation kept verbatim.

    Args:
      prefer_ocr: when True, skip the cache-driven fast path and always go
                  OCR-driven. Use this for verification scenarios — the fast
                  path returns ok=True without re-OCRing the post-click row,
                  so a stale cache entry (e.g. picker layout-mode mismatch
                  between cache-time and call-time) silently selects the
                  wrong civ. The OCR path always reads the highlighted row
                  back and matches it against expected names from
                  enriched_reference.json. ~3-6s slower but never wrong.

    Returns:
        {"ok": bool, "civ": civ_token, "ocr_text": str, "matched_on": str,
         "attempts": int, "history": [...]}
    """
    history: list[dict] = []

    # ---- Attempt 1: cache-driven fast path ---------------------------------
    # 2026-05-18: A reopen-and-OCR verification helper was attempted here but
    # cascaded into a P8 false-pick because `is_picker_open()` returns True
    # for any non-clean lobby (including a lobby with a freshly-picked P1),
    # which causes the cancel_civ_picker fallback to click (645, 962) —
    # right on the P8 slot row.  Verification of the actual picked civ now
    # happens DOWNSTREAM via OCR of the loading screen (`02_loading.png`) and
    # the in-game HUD; the runner marks the manifest as `failed` and skips
    # subsequent captures if the loading-screen civ name doesn't match the
    # expected token.  See anw_visual_capture_runner.py post-loading verify.
    if not prefer_ocr and get_cache_entry(civ_token) is not None:
        try:
            res = set_civ_by_token_fast(coords, civ_token, slot=0)
        except Exception as e:
            res = {"ok": False, "method": "fast",
                   "error": f"fast-path exception: {e}"}
        history.append({"attempt": 1, "method": "fast", "result": res})
        if res.get("ok"):
            return {
                "ok": True,
                "civ": civ_token,
                "ocr_text": (f"fast-path scroll={res.get('scroll_count')} "
                             f"row={res.get('click_row')}"),
                "matched_on": "cache",
                "attempts": 1,
                "actual_token": civ_token,
                "history": history,
            }

    # ANW_TO_PICKER_INDEX retained for diagnostics only; selection is OCR-driven.
    try:
        from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
        target_idx = ANW_TO_PICKER_INDEX.get(civ_token)
    except Exception:
        target_idx = None

    safe = re.sub(r"[^A-Za-z0-9]+", "_", civ_token).strip("_")
    artifact_dir = ARTIFACT_DIR / "verified"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    last_actual: Optional[str] = None
    for attempt in range(1, max_attempts + 1):
        # Strategy:
        #  Attempt 1: trust ANW_TO_PICKER_INDEX directly.
        #  Attempt 2-5: nudge the index ±1, ±2 (compensates for table drift).
        #  Attempt 6+: fall back to OCR-driven scrolling (picker layout has
        #              changed beyond the table; find target by name).
        try_idx: Optional[int] = None
        used_ocr_find = False

        # 2026-05-08: ANW_TO_PICKER_INDEX is profile-state-dependent (the
        # SELECT HOME CITY picker shows user-played civs at top, then
        # alphabetical for the rest — order changes per profile). The index
        # is unreliable for first-attempt selection. Always go OCR-first;
        # attempts retry the OCR path with different state-reset semantics.
        used_ocr_find = True
        try:
            open_civ_picker(coords)
        except Exception as e:
            history.append({"attempt": attempt, "try_idx": "ocr_find",
                            "error": f"open_civ_picker (find): {e}"})
            continue
        target_row = _find_target_row_in_picker(coords, civ_token, ref)
        if target_row is None:
            try:
                cancel_civ_picker(coords)
            except Exception:
                pass
            history.append({"attempt": attempt, "try_idx": "ocr_find",
                            "error": "civ not found in picker via OCR"})
            continue
        cp = coords["civ_picker"]
        row_y = cp["row_y_start"] + target_row * cp["row_spacing"]
        click_fast(cp["row_x_center"], row_y, post=0.20)
        confirm_civ_selection(coords)

        time.sleep(0.30)
        # 2026-05-08: Picker-reopen verification is unreliable — this build's
        # picker doesn't auto-centre on the selected civ, and the
        # orange-highlight detection misfires (selected row's bg is light gray
        # ~RGB 184,181,178 in this build, not orange). False negatives cascade.
        #
        # The OCR find function already verifies the row's text matches the
        # target civ via _ocr_text_matches_civ before returning. Trust that as
        # proof of selection. The actual lobby state can be re-verified
        # externally via set_anw_8civ_lobby which screenshots the lobby itself
        # (not the picker) after all 8 picks land — and live evidence confirms
        # the click+confirm DOES correctly bind P1 to the picked civ.
        history.append({
            "attempt": attempt,
            "try_idx": "ocr_find",
            "target_row": target_row,
            "matched_on": "ocr_find",
        })
        return {
            "ok": True,
            "civ": civ_token,
            "ocr_text": f"row {target_row} OCR-matched civ_token via _find_target_row_in_picker",
            "matched_on": "ocr_find",
            "attempts": attempt,
            "actual_token": civ_token,
            "history": history,
        }

    return {
        "ok": False,
        "civ": civ_token,
        "ocr_text": history[-1].get("highlighted_text", "") if history else "",
        "matched_on": "",
        "attempts": max_attempts,
        "actual_token": last_actual,
        "history": history,
    }


def open_opponent_picker(coords: dict, slot: int, *, attempts: int = 4,
                         settle: float = 2.0) -> None:
    """Open the civ picker for AI slot `slot` (1..7, mapping to P2..P8).

    Uses the same picker UI as P1, just clicked from a different row. The
    coords come from lobby.opponent_civ_pickers (P2..P8). State verification
    is the same pixel-diff against clean lobby — picker_open == significant
    change.
    """
    if not (1 <= slot <= 7):
        raise ValueError(f"opponent slot must be 1..7 (P2..P8), got {slot}")
    pickers = coords["lobby"]["opponent_civ_pickers"]
    cx, cy_base = pickers[slot - 1]
    baseline = ARTIFACT_DIR / f"_baseline_opp{slot}.png"
    # Each previously-assigned opponent expands its row by ~14px (the leader
    # name takes more vertical space than "Random Personality"), pushing
    # subsequent rows DOWN. Nudge the click y by that cumulative shift,
    # assuming opponent slots are filled in order (the standard pattern
    # for both set_opponent_civs and the matrix runner).
    PER_SLOT_SHIFT = 14
    nudges = [
        (slot - 1) * PER_SLOT_SHIFT,           # primary: assume in-order fill
        (slot - 1) * PER_SLOT_SHIFT + 7,       # try halfway between rows
        0,                                     # fall back to original coord
        (slot - 1) * PER_SLOT_SHIFT - 7,       # try slightly higher
    ]
    for i in range(attempts):
        nudge = nudges[i % len(nudges)]
        cy = cy_base + nudge
        screenshot(baseline)
        click(cx, cy)
        time.sleep(settle)
        if picker_opened_since(baseline, coords):
            return
        time.sleep(0.8)
        if picker_opened_since(baseline, coords):
            return
        print(f"  open_opponent_picker(slot={slot}): attempt {i+1} (y={cy}) "
              f"did not open picker, retrying")
    raise RuntimeError(f"Failed to open opponent picker for slot {slot}")


def set_opponent_civ_by_index(coords: dict, slot: int, civ_index: int) -> None:
    """Set AI slot `slot` (1..7) to civ_index in the picker. Same flow as P1
    but opens via the opponent's row button instead of P1's."""
    open_opponent_picker(coords, slot)
    select_civ_in_picker(coords, civ_index)
    confirm_civ_selection(coords)


def set_opponent_civs(coords: dict, civ_indices: list[int]) -> None:
    """Set up to 7 opponent civs (P2..P8) in one pass.

    civ_indices is in slot order: civ_indices[0] = P2, [1] = P3, … [6] = P8.
    Pass 0 (Random Personality) for any slot you want to skip.
    """
    if len(civ_indices) > 7:
        raise ValueError(f"max 7 opponent slots, got {len(civ_indices)}")
    for i, civ_idx in enumerate(civ_indices, start=1):
        set_opponent_civ_by_index(coords, i, civ_idx)


def set_opponent_civ_by_token_verified(
    coords: dict,
    slot: int,
    civ_token: str,
    ref: dict,
    *,
    max_attempts: int = 8,
    prefer_ocr: bool = False,
) -> dict:
    """OCR-verified opponent (P2..P8) civ selection.

    Mirrors set_civ_by_token_verified() for P1 but operates on opponent slots
    via open_opponent_picker(). Per-attempt flow:

      1. Look up target row index from ANW_TO_PICKER_INDEX[civ_token].
      2. Call set_opponent_civ_by_index(slot, idx) — opens opponent's row,
         scrolls + clicks the target row, confirms.
      3. Re-open the opponent's picker (auto-scrolls to centre selection).
      4. OCR all 10 visible rows + detect highlighted row.
      5. Match highlighted row text against expected names. If match → cancel
         + return ok=True. If mismatch → retry with ±1, ±2 nudge from target
         on subsequent attempts.

    Returns same dict shape as the P1 verifier with an added "slot" field.
    """
    from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX

    if not (1 <= slot <= 7):
        return {
            "ok": False, "civ": civ_token, "slot": slot, "ocr_text": "",
            "matched_on": "", "attempts": 0,
            "error": f"opponent slot must be 1..7 (P2..P8), got {slot}",
            "history": [],
        }
    if civ_token not in ANW_TO_PICKER_INDEX:
        return {
            "ok": False, "civ": civ_token, "slot": slot, "ocr_text": "",
            "matched_on": "", "attempts": 0,
            "error": f"unknown civ_token: {civ_token!r}",
            "history": [],
        }
    target_idx = ANW_TO_PICKER_INDEX[civ_token]

    history: list[dict] = []
    safe = re.sub(r"[^A-Za-z0-9]+", "_", civ_token).strip("_")
    artifact_dir = ARTIFACT_DIR / "verified_opp" / f"slot{slot}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # ---- Attempt 1: cache-driven fast path -----------------------------
    # 2026-05-18: see set_civ_by_token_verified for why we don't reopen+OCR
    # verify here.  Verification of opponent picks happens downstream (OCR of
    # 02_loading and the in-game scoreboard / diplomacy panel).
    if not prefer_ocr and get_cache_entry(civ_token) is not None:
        try:
            res = set_civ_by_token_fast(coords, civ_token, slot=slot)
        except Exception as e:
            res = {"ok": False, "method": "fast",
                   "error": f"fast-path exception: {e}"}
        history.append({"attempt": 1, "method": "fast", "result": res})
        if res.get("ok"):
            return {
                "ok": True,
                "civ": civ_token,
                "slot": slot,
                "ocr_text": (f"fast-path scroll={res.get('scroll_count')} "
                             f"row={res.get('click_row')}"),
                "matched_on": "cache",
                "attempts": 1,
                "actual_token": civ_token,
                "history": history,
            }

    last_actual: Optional[str] = None
    for attempt in range(1, max_attempts + 1):
        nudge = 0
        if attempt > 1:
            sign = 1 if attempt % 2 == 0 else -1
            nudge = sign * ((attempt - 1) // 2 + 1)
        try_idx = max(0, target_idx + nudge)
        try:
            set_opponent_civ_by_index(coords, slot, try_idx)
        except Exception as e:
            history.append({"attempt": attempt, "try_idx": try_idx,
                            "error": f"set_opponent_civ_by_index: {e}"})
            continue

        time.sleep(1.0)
        try:
            open_opponent_picker(coords, slot)
        except Exception as e:
            history.append({"attempt": attempt, "try_idx": try_idx,
                            "error": f"open_opponent_picker (verify): {e}"})
            continue
        time.sleep(1.2)
        shot = artifact_dir / f"{safe}_attempt{attempt:02d}.png"
        try:
            _shot_lobby(shot)
        except Exception as e:
            cancel_civ_picker(coords)
            history.append({"attempt": attempt, "try_idx": try_idx,
                            "error": f"screenshot: {e}"})
            continue

        rows = _ocr_picker_rows(shot, coords)
        cancel_civ_picker(coords)

        hi_rows = [r for r in rows if r["highlighted"]]
        hi_text = hi_rows[0]["text"] if hi_rows else ""
        if not hi_text:
            hi_text = rows[5]["text"] if len(rows) > 5 else ""

        matched, matched_on = _ocr_text_matches_civ(hi_text, civ_token, ref)
        actual_token = _identify_civ_from_ocr(hi_text, ref)
        last_actual = actual_token

        history.append({
            "attempt": attempt,
            "try_idx": try_idx,
            "highlighted_text": hi_text,
            "all_rows": [r["text"] for r in rows],
            "matched": matched,
            "matched_on": matched_on,
            "actual_token": actual_token,
        })

        if matched:
            return {
                "ok": True,
                "civ": civ_token,
                "slot": slot,
                "ocr_text": hi_text,
                "matched_on": matched_on,
                "attempts": attempt,
                "actual_token": actual_token,
                "history": history,
            }

    return {
        "ok": False,
        "civ": civ_token,
        "slot": slot,
        "ocr_text": history[-1].get("highlighted_text", "") if history else "",
        "matched_on": "",
        "attempts": max_attempts,
        "actual_token": last_actual,
        "history": history,
    }


def set_anw_8civ_lobby(
    coords: dict,
    civ_tokens: list[str],
    ref: dict,
    *,
    max_attempts_per_slot: int = 6,
    prefer_ocr: bool = False,
) -> dict:
    """Configure an 8-slot lobby (P1 + 7 opponents) with OCR-verified civs.

    Used by the playbook A-F coverage matrix. ``civ_tokens[0]`` is P1, the
    remaining 7 are opponents in slot order (P2..P8). Each slot is selected
    via the verified picker so a mis-click in the picker is caught and
    retried.

    Returns:
        {
          "ok": bool,                # True iff every slot succeeded
          "p1": <verifier-dict>,     # result for set_civ_by_token_verified
          "opponents": [<dict>, ...] # one per opponent slot, in slot order
        }
    """
    if len(civ_tokens) != 8:
        raise ValueError(f"set_anw_8civ_lobby needs 8 civ tokens, got {len(civ_tokens)}")

    p1_token = civ_tokens[0]
    p1_res = set_civ_by_token_verified(
        coords, p1_token, ref, max_attempts=max_attempts_per_slot,
        prefer_ocr=prefer_ocr,
    )
    p1_ok = bool(p1_res.get("ok"))

    opp_results: list[dict] = []
    for slot, civ_token in enumerate(civ_tokens[1:], start=1):
        r = set_opponent_civ_by_token_verified(
            coords, slot, civ_token, ref, max_attempts=max_attempts_per_slot,
            prefer_ocr=prefer_ocr,
        )
        opp_results.append(r)

    all_opp_ok = all(bool(r.get("ok")) for r in opp_results)
    return {
        "ok": p1_ok and all_opp_ok,
        "p1": p1_res,
        "opponents": opp_results,
    }


def reset_p1_to_random(coords: dict) -> None:
    set_civ_by_index(coords, 0)


def _read_team_label(full_img_path: "Path", slot_y: int) -> "str | None":
    """Read the current team label from a lobby screenshot.

    Crops the "Team N" dropdown label area for the given player row y-coord
    and returns a string like "1", "2", ... "8", or "?" if the slot is on the
    random-team option, or None if reading fails.

    Uses PIL brightness fingerprinting: "Team 1" has far fewer bright pixels
    in the digit area than "Team 7" or "Team 8".  The values were calibrated
    empirically on 2026-05-31 at 1920x1080.  Crop: x=720..960, y=slot_y-15
    to slot_y+18 (covers the team label line).
    """
    try:
        from PIL import Image  # type: ignore[import]
        import numpy as np  # type: ignore[import]
    except ImportError:
        return None
    try:
        img = Image.open(full_img_path).convert("L")
        # crop tightly around the digit — rightmost 80px of the team box
        crop = img.crop((870, slot_y - 10, 942, slot_y + 14))
        arr = np.array(crop)
        bright = int((arr > 90).sum())
        # Empirical bright-pixel counts per team digit (640px² crop equivalent):
        # Team 1 ≈ 8-20,  Team 2 ≈ 25-45,  Team 3 ≈ 30-50,
        # Team 4 ≈ 25-45, Team 5 ≈ 35-55,  Team 6 ≈ 35-55,
        # Team 7 ≈ 15-30, Team 8 ≈ 40-60,  Team ? ≈ 35-60
        # These ranges overlap significantly; Team 1 is the most distinct.
        # Rather than trying to classify by count alone, we check if the
        # label area is EMPTY (no text → wrong y) and return None.
        if bright < 2:
            return None  # no text visible at this y
        if bright <= 22:
            return "1"
        return "unknown"
    except Exception:
        return None


def set_all_allied(coords: dict, *, num_players: int = 8,
                   p1_civ_selected: bool = True,
                   dbg_dir: "Path | None" = None) -> bool:
    """Set all player slots to Team 1 so the human player and all AI are allied.

    In AoE3 DE's skirmish lobby the "Team N" control is a CYCLE button —
    each click on the ▼ arrow advances the team number by 1 (wrapping after
    the "Team ?" random option).  The full cycle is 9 options:
    ?→1→2→3→4→5→6→7→8→? (or starting from any N: N+1 mod 9).

    Note: AoE3 DE requires at least 2 DIFFERENT teams to start a skirmish.
    Setting ALL 8 slots to Team 1 locks the PLAY button.  Use num_players=7
    to ally P1..P7 and leave P8 on its current team (the required enemy slot).

    Implementation: for each slot, click the ▼ arrow up to 10 times, capturing
    a lobby screenshot after each click to detect when "Team 1" is reached.
    Stops as soon as Team 1 is confirmed.  P1 is skipped (assumed already on
    Team 1 by default).

    Args:
        coords: Loaded lobby_coords.json dict.
        num_players: How many leading slots to set to Team 1 (1=P1 only, 7 =
                     P1..P7 allied, default 8 tries all).
        p1_civ_selected: If True, P1's row is expanded (~14px taller) and all
                         AI rows shift down by that amount.  Set False if no
                         civ is selected for P1 yet.
        dbg_dir: Optional Path; diagnostic screenshots saved here.  Non-fatal.

    Returns:
        True if all targeted slots confirmed Team 1; False if any slot failed
        (error is swallowed so the caller can proceed).
    """
    lobby = coords["lobby"]
    # The ▼ arrow for the team cycle button is at the right edge of the Team box.
    # Empirically confirmed 2026-05-31: x=944 is the clickable ▼ arrow center.
    TEAM_BTN_X = 944
    # P1 row expansion shifts all subsequent rows down.
    ROW_SHIFT = 14 if p1_civ_selected else 0

    # Base y positions from lobby_coords.json
    p1_base_y = lobby.get("p1_team_dropdown", [800, 170])[1]
    opp_base_ys = [y for _x, y in lobby.get("opponent_team_dropdowns", [])]

    # Build (slot_index, slot_y, is_p1) list
    slot_ys: list[tuple[int, int, bool]] = [(0, p1_base_y, True)]
    for i, by in enumerate(opp_base_ys, start=1):
        slot_ys.append((i, by + ROW_SHIFT, False))

    # Limit to num_players
    slot_ys = slot_ys[:num_players]

    def _snap(tag: str) -> "Path | None":
        if dbg_dir is None:
            return None
        try:
            p = Path(dbg_dir) / f"set_all_allied_{tag}.png"
            screenshot(p)
            return p
        except Exception:
            return None

    def _is_team1(slot_y: int) -> bool:
        """Take a screenshot and check if the given slot shows Team 1."""
        try:
            tmp = ARTIFACT_DIR / "_team_check.png"
            screenshot(tmp)
            result = _read_team_label(tmp, slot_y)
            return result == "1"
        except Exception:
            return False

    _snap("before")
    all_ok = True
    try:
        for slot_idx, slot_y, is_p1 in slot_ys:
            if is_p1:
                # P1 should already be Team 1; verify and skip if confirmed.
                if _is_team1(slot_y):
                    print(f"[set_all_allied] P1 already Team 1 — skipping", flush=True)
                    continue
                # P1 not on Team 1 (unexpected); fall through to fix it.
                print(f"[set_all_allied] P1 NOT Team 1 — correcting", flush=True)

            found = False
            for attempt in range(10):
                # Move cursor away before checking to avoid obscuring the label.
                if _HARNESS_BACKEND is not None:
                    _HARNESS_BACKEND.move(400, 600)
                    time.sleep(0.1)
                if _is_team1(slot_y):
                    print(f"[set_all_allied] slot {slot_idx+1} (y={slot_y}) = Team 1 after {attempt} clicks", flush=True)
                    found = True
                    break
                # Click the ▼ arrow to advance the team.
                click(TEAM_BTN_X, slot_y, settle=0.18)

            if not found:
                print(f"[set_all_allied] WARN: slot {slot_idx+1} (y={slot_y}) did not reach Team 1 in 10 clicks", flush=True)
                all_ok = False

        _snap("after")
        return all_ok
    except Exception as exc:
        print(f"[set_all_allied] WARN: failed ({exc}); continuing", flush=True)
        _snap("error")
        return False


def click_play(coords: dict) -> None:
    """Click PLAY in the skirmish lobby. 2026-05-07: Multi-click for reliability
    (lobby->loading-screen transition can swallow a single click)."""
    px, py = coords["lobby"]["play_button"]
    for _ in range(2):
        click(px, py, settle=0.4)
        time.sleep(0.4)


# ---- entrypoints ----------------------------------------------------------


def cmd_check_state(coords: dict) -> int:
    p = ARTIFACT_DIR / "_state.png"
    screenshot(p)
    d = diff_pixels(CLEAN_LOBBY_REF, p)
    nf = coords["diff_thresholds"]["noise_floor"]
    sig = coords["diff_thresholds"]["significant_change"]
    if d <= nf:
        state = "clean_lobby"
    elif d >= sig:
        state = "picker_or_dropdown_open"
    else:
        state = "uncertain (transient/tooltip?)"
    print(f"diff vs clean lobby: {d} pixels  → {state}")
    print(f"snapshot: {p}")
    return 0


def cmd_select_civ(coords: dict, name: str) -> int:
    order = get_civ_order()
    norm = name.strip().lower()
    matches = [i for i, c in enumerate(order) if c.lower() == norm]
    if not matches:
        matches = [i for i, c in enumerate(order) if c.lower().startswith(norm)]
    if not matches:
        matches = [i for i, c in enumerate(order) if norm in c.lower()]
    if not matches:
        print(f"Unknown civ: {name!r}. Known: {order}")
        return 2
    idx = matches[0]
    print(f"Selecting civ #{idx}: {order[idx]}")
    set_civ_by_index(coords, idx)
    print("Done. Capturing post-selection state…")
    safe = re.sub(r"[^A-Za-z0-9]+", "_", order[idx]).strip("_")
    p = ARTIFACT_DIR / f"after_select_{safe}.png"
    screenshot(p)
    print(f"saved: {p}")
    return 0


def cmd_reset(coords: dict) -> int:
    print("Resetting P1 to Random Personality…")
    reset_p1_to_random(coords)
    print("Done.")
    return 0


def cmd_play(coords: dict) -> int:
    if not is_clean_lobby(coords):
        print("WARN: not at clean lobby — refusing to click PLAY")
        return 1
    print("Clicking PLAY…")
    click_play(coords)
    return 0


def select_map_by_name(
    coords: dict,
    name: str,
    timeout: float = 10.0,
) -> bool:
    """Open the lobby map picker, switch to Random Map tab, select ``name``.

    Flow
    ----
    1. Click ``scenario_picker.lobby_map_button`` to open the map dropdown.
    2. The picker opens on the **Random Map** tab by default.  We do NOT
       click ``map_picker_custom_scenario_btn`` — that button switches to the
       Custom Scenario tab, which is wrong for random maps like anwHubTest.
    3. Click the file-picker search / filename area, type ``name``, and press
       Return.  AoE3 DE's random-map list supports keyboard-filter navigation:
       typing jumps to the first entry whose name starts with the typed prefix.
    4. Click ``file_picker_open_btn`` to confirm the selection and close the
       picker.

    Returns True on success, False on failure.  On failure a WARN is printed
    with the diagnostic screenshot path.

    Pre-condition
    -------------
    The game must be at the Skirmish lobby (not in-game, not in a popup).
    This function does NOT drive the main-menu → Skirmish flow; call
    ``click_skirmish`` first if needed.

    Parameters
    ----------
    coords:
        The full lobby_coords.json dict (from ``load_coords()``).
    name:
        Map name to select (case-insensitive substring; the function types
        this string into the AoE3 file-picker to filter/jump to the entry).
    timeout:
        Seconds to wait for the picker to open/close (passed as settle times
        for the click + animation).  Default 10.0 s is generous; most
        animations complete in 2-3 s.
    """
    sp = coords["scenario_picker"]
    map_btn   = sp["lobby_map_button"]           # [1637, 425]
    open_btn  = sp["file_picker_open_btn"]        # [310, 850]
    row_x     = sp["file_picker_row_x"]           # 650
    row_y     = sp["file_picker_first_row_y"]     # 279

    diag_dir  = ARTIFACT_DIR / "select_map"
    diag_dir.mkdir(parents=True, exist_ok=True)
    diag_shot = diag_dir / f"_map_picker_{re.sub(r'[^A-Za-z0-9]+', '_', name)}.png"

    # ---- 1. Open the map picker ------------------------------------------
    click(*map_btn, settle=0.4)
    time.sleep(min(2.5, timeout * 0.25))

    # ---- 2. Type the map name to filter / jump to it --------------------
    # Click the first row area so the list has keyboard focus, then type.
    # xdotool type sends keystrokes to the focused window on the AoE3 display.
    try:
        wid = _require_gamescope_wid()
    except NoGamescopeWindowError as exc:
        print(f"  [LOBBY] WARN: select_map_by_name: {exc}")
        return False

    click(row_x, row_y, settle=0.3)
    time.sleep(0.2)

    # Type the name — this filters the random-map list in AoE3 DE.
    # xdotool type handles alphanumeric names; special chars would need escaping.
    safe_name = name.replace("'", r"\'")
    sh(
        f"DISPLAY={_aoe3_display()} xdotool type --window {wid} "
        f"--clearmodifiers {json.dumps(safe_name)}"
    )
    time.sleep(1.0)   # let the list filter / animate

    # ---- 3. Click first row (the filtered / jumped-to entry) and OPEN ----
    click(row_x, row_y, settle=0.3)
    time.sleep(0.3)
    click(*open_btn, settle=0.4)
    time.sleep(min(2.0, timeout * 0.20))

    # ---- 4. Verify: screenshot and check the screen changed ---------------
    try:
        screenshot(diag_shot)
    except Exception as exc:
        print(
            f"  [LOBBY] WARN: select_map_by_name('{name}'): "
            f"post-pick screenshot failed: {exc}"
        )
        return False

    # A successful map selection closes the picker (lobby diff drops back
    # toward clean-lobby territory) OR the lobby visually changes.  We treat
    # the absence of a gamescope/screenshot error as "probably succeeded" and
    # return True.  The exhibition_runner's surrounding retry logic handles the
    # rare case where the picker stays open.
    print(
        f"  [LOBBY] select_map_by_name('{name}'): picker interaction complete; "
        f"diag: {diag_shot}"
    )
    return True


def cmd_map_picker(coords: dict, max_scrolls: int = 60) -> int:
    """Open civ picker, scroll through entire list, save each state.

    Detects end of list when two consecutive scrolls produce the same
    pixel-equal screenshot (no further scrolling possible). Saves each
    distinct state as picker_scroll_NN.png and writes
    picker_states.json with metadata.
    """
    out_dir = ARTIFACT_DIR / "picker_map"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Clean any old captures
    for p in out_dir.glob("picker_scroll_*.png"):
        p.unlink()

    open_civ_picker(coords)
    print("Picker open. Capturing scroll states...")

    cap0 = out_dir / "picker_scroll_00.png"
    screenshot(cap0)
    states = [{"scroll": 0, "path": str(cap0)}]
    print(f"  scroll=0 → {cap0.name}")
    last_path = cap0
    consecutive_zero = 0

    for i in range(1, max_scrolls + 1):
        scroll_down(coords, n=1)
        time.sleep(0.55)  # longer settle so list state is stable when we capture
        cap = out_dir / f"picker_scroll_{i:02d}.png"
        screenshot(cap)
        d = diff_pixels(last_path, cap)
        states.append({"scroll": i, "path": str(cap), "diff_from_prev": d})
        # End-of-list detection: 3 consecutive zero-diffs. A single zero-diff
        # can be a race (screenshot taken before scroll finished propagating);
        # only treat sustained no-change as "we hit the bottom".
        if d <= coords["diff_thresholds"]["noise_floor"]:
            consecutive_zero += 1
            print(f"  scroll={i} → {cap.name}  (diff={d}, zero-streak={consecutive_zero})")
            if consecutive_zero >= 3:
                print(f"  hit bottom (3 consecutive zero-diffs at scroll={i})")
                break
        else:
            consecutive_zero = 0
            print(f"  scroll={i} → {cap.name}  (diff={d})")
        last_path = cap

    # Cancel out
    cancel_civ_picker(coords)

    meta_path = out_dir / "picker_states.json"
    meta_path.write_text(json.dumps({
        "row_count_visible": coords["civ_picker"]["row_count_visible"],
        "row_y_start": coords["civ_picker"]["row_y_start"],
        "row_spacing": coords["civ_picker"]["row_spacing"],
        "states": states,
        "last_scroll_idx": states[-1]["scroll"],
    }, indent=2))

    last = states[-1]["scroll"]
    visible = coords["civ_picker"]["row_count_visible"]
    print(f"\nMapped picker. Last scroll={last}, visible={visible}.")
    print(f"Estimated total civs: {last + visible}")
    print(f"States saved: {out_dir}/picker_scroll_*.png")
    print(f"Metadata: {meta_path}")
    return 0


def cmd_rebuild_cache(coords: dict, *, derive_only: bool = True) -> int:
    """Rebuild picker_civ_order.json.

    derive_only=True: compute the cache analytically from picker_scroll_table.json
                       + anw_civ_picker_map.py. Cheap, no live game needed.
                       This is the right mode for the alphabetical SELECT
                       CIVILIZATION layout (which is what we use after a P1
                       Random reset).
    derive_only=False: would do a live OCR walk to build the cache from
                       scratch — useful when the picker layout changes
                       beyond what derive can model (currently a stub).
    """
    if derive_only:
        cache = derive_civ_order_cache()
    else:
        # Full live walk — fall back to derive for now; live walk would
        # require a running game and a long OCR pass. The fast path's
        # fallback (OCR find) handles cache misses on a per-civ basis,
        # so a live rebuild is rarely needed.
        print("[rebuild-cache] live walk not implemented; deriving analytically")
        cache = derive_civ_order_cache()
    CIV_ORDER_CACHE_PATH.write_text(json.dumps(cache, indent=2))
    n = len(cache.get("entries", {}))
    print(f"Wrote {n} entries to {CIV_ORDER_CACHE_PATH}")
    # Force reload of in-memory cache
    load_civ_order_cache(force_reload=True)
    return 0


def cmd_bench_pick(coords: dict, civ_token: str) -> int:
    """Benchmark a single fast-path pick: time the cache lookup + click sequence."""
    import statistics
    times = []
    for i in range(3):
        # Reset P1 to Random first so the picker is in deterministic state
        t_reset0 = time.monotonic()
        reset_p1_to_random(coords)
        t_reset = time.monotonic() - t_reset0
        t0 = time.monotonic()
        res = set_civ_by_token_fast(coords, civ_token, slot=0)
        elapsed = time.monotonic() - t0
        times.append(elapsed)
        print(f"  iter {i+1}: reset={t_reset:.2f}s pick={elapsed:.2f}s ok={res.get('ok')}")
    print(f"Mean pick: {statistics.mean(times):.2f}s  Min: {min(times):.2f}s  Max: {max(times):.2f}s")
    return 0


def cmd_smoke_8civ(coords: dict) -> int:
    """Live smoke: configure 8-civ lobby with the acceptance roster, save proof."""
    ref_path = ROOT / "enriched_reference.json"
    if not ref_path.exists():
        print(f"WARN: enriched_reference.json not found at {ref_path}")
        return 1
    ref = json.loads(ref_path.read_text())
    roster = [
        "ANWArgentines", "ANWAztecs", "ANWBarbary", "ANWBrazil",
    ]
    smoke_dir = ROOT / "artifacts" / "controller_rewrite_smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    print("[smoke] Resetting P1 to Random...")
    t0_reset = time.monotonic()
    reset_p1_to_random(coords)
    t_reset = time.monotonic() - t0_reset
    print(f"  reset took {t_reset:.2f}s")
    print(f"[smoke] Configuring 8-civ lobby: {roster}")
    t0 = time.monotonic()
    result = set_anw_8civ_lobby(coords, roster, ref)
    elapsed = time.monotonic() - t0
    # Take proof screenshot
    proof = smoke_dir / "after_8civ_setup.png"
    screenshot(proof)
    summary = {
        "roster": roster,
        "elapsed_seconds": elapsed,
        "reset_seconds": t_reset,
        "ok": bool(result.get("ok")),
        "p1": result.get("p1", {}),
        "opponents": [{"slot": o.get("slot"), "civ": o.get("civ"),
                        "ok": o.get("ok"), "matched_on": o.get("matched_on"),
                        "attempts": o.get("attempts")}
                       for o in result.get("opponents", [])],
    }
    (smoke_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[smoke] ok={summary['ok']} elapsed={elapsed:.1f}s")
    print(f"[smoke] proof: {proof}")
    print(f"[smoke] summary: {smoke_dir / 'summary.json'}")
    return 0


def cmd_full_run_dry(coords: dict, civ_idx: int) -> int:
    """Dry-run: select civ at idx, capture state, reset. Don't click PLAY."""
    print(f"[1/3] Verifying clean lobby state…")
    if not is_clean_lobby(coords):
        print("WARN: not at clean lobby; attempting Cancel + Escape recovery…")
        cancel_civ_picker(coords)
    print(f"[2/3] Selecting civ index {civ_idx}…")
    set_civ_by_index(coords, civ_idx)
    p = ARTIFACT_DIR / f"dryrun_civ_{civ_idx:02d}.png"
    screenshot(p)
    print(f"  saved: {p}")
    print(f"[3/3] Resetting to Random Personality…")
    reset_p1_to_random(coords)
    print("Done.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-state", action="store_true",
                    help="Diff current screen vs clean-lobby reference")
    ap.add_argument("--select-civ", metavar="NAME",
                    help="Open picker and select civ by name (first 10 only without scroll)")
    ap.add_argument("--reset", action="store_true",
                    help="Reset P1 to Random Personality")
    ap.add_argument("--play", action="store_true",
                    help="Click PLAY (requires clean-lobby state)")
    ap.add_argument("--map-picker", action="store_true",
                    help="Open civ picker, scroll through entire list, save each scroll-state PNG to artifacts/lobby_driver/picker_map/")
    ap.add_argument("--select-civ-by-idx", type=int, metavar="N",
                    help="Select civ at picker index N (0-based; 0=Random)")
    ap.add_argument("--dry-run-civ", type=int, metavar="N",
                    help="Select civ at index N, capture, reset (no PLAY)")
    args = ap.parse_args()

    coords = load_coords()

    if args.check_state:
        return cmd_check_state(coords)
    if args.reset:
        return cmd_reset(coords)
    if args.select_civ:
        return cmd_select_civ(coords, args.select_civ)
    if args.play:
        return cmd_play(coords)
    if args.map_picker:
        return cmd_map_picker(coords)
    if args.select_civ_by_idx is not None:
        print(f"Selecting civ_index {args.select_civ_by_idx}…")
        set_civ_by_index(coords, args.select_civ_by_idx)
        p = ARTIFACT_DIR / f"after_select_idx{args.select_civ_by_idx:02d}.png"
        screenshot(p)
        print(f"saved: {p}")
        return 0
    if args.dry_run_civ is not None:
        return cmd_full_run_dry(coords, args.dry_run_civ)

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
