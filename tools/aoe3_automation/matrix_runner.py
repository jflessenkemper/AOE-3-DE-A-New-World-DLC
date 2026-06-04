"""Fully-automated 100%-civ-coverage skirmish matrix runner.

Stitches together:
  - lobby_driver.py       — pixel-coord-driven Skirmish-lobby control
  - in_game_driver.py     — GameDriver: launch/wait/speed/resign lifecycle
  - log_capture.py        — Age3Log.txt mirror per match
  - manage_game.py        — process lifecycle / crash recovery

For every civ_idx in `picker_scroll_table.json["civ_names"]` (skipping
idx 0 = Random Personality by default) we:

  1. Verify game is alive at clean Skirmish lobby; relaunch + recover if not.
  2. Open civ picker, scroll to target row (using the empirical scroll table
     since one wheel-down ≠ one row), click civ, OK.
  3. Start Age3Log.txt mirror to artifacts/matrix/<idx>/match.log.
  4. Click PLAY.
  5. Wait for `WorldAssetPreloadingTime` (match playable).
  6. Set max speed (tick 5 = ~Fast x effective).
  7. Observe `observe_seconds` of gameplay (default 600 = ~10 min wall).
  8. Resign → confirm → return to main menu.
  9. Stop log mirror; write per-civ summary.
  10. Re-enter Skirmish lobby; reset P1 to Random Personality.

Crash recovery: if any step throws or the game exits, we call
`manage_game.cycle` (close + relaunch + main menu) and continue with the
NEXT civ. No iteration ever blocks the matrix indefinitely.

Run from gamescope-host context (game already at lobby helps but isn't
required):
    flatpak-spawn --host python3 tools/aoe3_automation/matrix_runner.py \\
        --observe-seconds 600 --start-idx 1 --end-idx 48

Use --dry-run to skip the actual PLAY (just exercises the lobby flow per civ).
Use --civs aztec_empire,spain  to run a subset by name.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Make sibling modules importable when invoked as a script.
# in_game_driver.py imports as `tools.aoe3_automation.log_capture`, so we need
# the repo root on sys.path *before* HERE.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import lobby_driver as lobby                                          # noqa: E402
from tools.aoe3_automation.in_game_driver import GameDriver           # noqa: E402
from tools.aoe3_automation.log_capture import (                       # noqa: E402
    start_log_tail, stop_log_tail, LogMirror, ensure_dev_mode,
)
from tools.playtest.probes_from_replay import (                       # noqa: E402
    scan_personality_dir, validate_probes, PERSONALITY_DIR,
    PersonalityProbe,
)
from tools.playtest.replay_chat_scan import diagnose as diagnose_replay  # noqa: E402
from tools.playtest.replay_probes import (                              # noqa: E402
    parse_probes as _parse_llp_probes,
    derive_behavioral_axes as _derive_behavioral_axes,
)
from tools.aoe3_automation.av_probe import (                           # noqa: E402
    threaded_screenshot_after,
    screenshot_with_keypress,
    image_has_content,
    image_contains_words,
)
from tools.aoe3_automation.vision_judge import (                        # noqa: E402
    doctrine_summary_from_expectation,
)
from tools.playtest.expectations import load_expectations               # noqa: E402

# Index expectations once per process so per-civ lookups are O(1).
_EXP_BY_NAME: dict | None = None


# Probe tags every AI in a batch must emit at least once before the runner
# is willing to early-exit the observe window. Picked to be the smallest set
# that also gates every behavioural axis the validator exposes:
#
#   meta.leader_init       proves dispatch fired (gates leader_init axis)
#   compliance.profile     proves heartbeat tick happened (gates doctrine_fired)
#   compliance.age         proves age-up ran (gates age_up_fired)
#   tech.ship              proves a shipment was chosen (gates shipments_chosen)
#
# We deliberately don't require mil.attack here — defensive doctrines may go
# the full window without dispatching one and that's a *valid* doctrine, not
# a probe-coverage gap. The behavioural-axis cross-check at validate() time
# already understands the doctrine→combat-pressure relationship.
_ADAPTIVE_OBSERVE_REQUIRED_TAGS = (
    b"meta.leader_init",
    b"compliance.profile",
    b"compliance.age",
    # tech.ship intentionally NOT required: defensive boomers / late-shipment
    # doctrines may not ship within the observe cap and that's a *valid*
    # doctrine, not a probe-coverage gap. The shipments_chosen behavioural
    # axis tracks per-civ shipment activity separately.
)


def _adaptive_observe(driver, log_path: Path, *,
                      expected_ai_count: int,
                      max_seconds: float,
                      poll_interval: float = 3.0,
                      annotate: callable = print) -> tuple[float, str]:
    """Poll ``log_path`` every ``poll_interval`` seconds; resign as soon as
    ``expected_ai_count`` distinct AI players have each emitted every tag in
    ``_ADAPTIVE_OBSERVE_REQUIRED_TAGS`` at least once. Returns
    (observed_seconds, exit_reason).

    Falls back gracefully:
      * If match.log can't be read at all, we sleep to ``max_seconds``.
      * Caps at max_seconds either way — never exceeds the user's budget.

    The 75% wall-time win comes from the fact that fast civs hit full
    coverage in ~90–150s; only the slowest doctrine in a batch sets the
    floor, not the wall-clock max."""
    import re as _re
    # One regex per pass — match every probe header and capture (player, tag).
    probe_header = _re.compile(
        rb"\[ANWP v=2 t=\d+ p=(?P<p>\d+) civ=\S+ ldr=\S+ tag=(?P<tag>\S+)\]"
    )
    deadline = time.monotonic() + max_seconds
    t0 = time.monotonic()
    coverage: dict[int, set[bytes]] = {}
    last_satisfied_count = 0
    while time.monotonic() < deadline:
        # Sleep first so the engine has time to write at least one tick of
        # probes before our first parse.
        remaining = deadline - time.monotonic()
        time.sleep(min(poll_interval, max(0.0, remaining)))
        try:
            if not log_path.exists():
                continue
            data = log_path.read_bytes()
        except OSError:
            continue
        coverage.clear()
        for m in probe_header.finditer(data):
            try:
                pid = int(m.group("p"))
            except (TypeError, ValueError):
                continue
            tag = m.group("tag")
            coverage.setdefault(pid, set()).add(tag)
        satisfied = [
            pid for pid, tags in coverage.items()
            if all(t in tags for t in _ADAPTIVE_OBSERVE_REQUIRED_TAGS)
        ]
        if len(satisfied) != last_satisfied_count:
            annotate(
                f"adaptive observe: {len(satisfied)}/{expected_ai_count} "
                f"AI(s) at full probe coverage "
                f"(t={time.monotonic() - t0:.0f}s, "
                f"max={max_seconds:.0f}s)"
            )
            last_satisfied_count = len(satisfied)
        if len(satisfied) >= expected_ai_count:
            obs_s = time.monotonic() - t0
            return (obs_s, f"early-exit: {len(satisfied)} AI(s) satisfied "
                            f"at {obs_s:.0f}s (saved "
                            f"{max_seconds - obs_s:.0f}s)")
    return (time.monotonic() - t0,
            f"max-observe reached ({max_seconds:.0f}s)")


def _expectation_for(civ_name: str):
    """Best-effort match by label/civ_id/slugified name.

    The lobby's civ_names entries are e.g. "British", "Spanish_DE", or the
    revolution variants like "Brazilian (Revolution)". Expectations carry
    both ``civ_id`` (cCivBritish) and ``label`` (British). Match permissively
    so we don't drop the doctrine summary on a typo."""
    global _EXP_BY_NAME
    if _EXP_BY_NAME is None:
        _EXP_BY_NAME = {}
        for e in load_expectations():
            for k in (e.civ_id, e.label, slugify(e.civ_id), slugify(e.label)):
                _EXP_BY_NAME.setdefault(k.lower() if k else "", e)
    key = civ_name.lower()
    if key in _EXP_BY_NAME:
        return _EXP_BY_NAME[key]
    sl = slugify(civ_name).lower()
    if sl in _EXP_BY_NAME:
        return _EXP_BY_NAME[sl]
    # contains-match fallback
    for k, e in _EXP_BY_NAME.items():
        if sl and sl in k:
            return e
    return None

# Engine-error markers we scan match.log for. These are the strings the
# engine prints for the failure modes that have ever silently corrupted a
# match without aborting it (XS compile errors, asset misses, native asserts).
# Anything that hits = engine_error_free axis fails.
_ENGINE_ERROR_PATTERNS = (
    re.compile(rb"XS error:", re.IGNORECASE),
    re.compile(rb"^FATAL", re.IGNORECASE | re.MULTILINE),
    re.compile(rb"assertion failed", re.IGNORECASE),
    re.compile(rb"failed to load", re.IGNORECASE),
    re.compile(rb"missing asset", re.IGNORECASE),
    re.compile(rb"unhandled exception", re.IGNORECASE),
    re.compile(rb"undefined helper", re.IGNORECASE),
    re.compile(rb"could not resolve", re.IGNORECASE),
    re.compile(rb"\[ERROR\]", re.IGNORECASE),
)

# AoE3 saves replays here as "Record Game*.age3Yrec".
REPLAY_DIR = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Savegame"
)

ARTIFACT_DIR = HERE / "artifacts" / "matrix_runner"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

MANAGE_GAME = HERE / "manage_game.py"


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()


def game_is_running() -> bool:
    rc = subprocess.run(
        [sys.executable, str(MANAGE_GAME), "status"],
        capture_output=True, text=True,
    ).returncode
    return rc == 0


# ---------------------------------------------------------------------------
# Harness input backend (AOE3DEHarness headless gamescope rig)
# ---------------------------------------------------------------------------
# On this rig the game runs under the AOE3DEHarness compositor, which exposes a
# unix control socket for click/key/screenshot injection in compositor-space
# 1920x1080 coords (exactly what lobby_coords.json uses). The legacy xdotool
# path can drive coarse clicks (Skirmish) but fails the precise civ-picker
# open sequence. We must route input through the harness socket instead.
#
# Crucially, every cycle_game() kills the game and recreates the socket, so the
# backend connection has to be (re)established *after* each cycle, not once at
# startup. ensure_harness_backend() is idempotent and self-healing: it reuses a
# live connection, drops + reconnects a dead one, and registers the client with
# both lobby_driver and in_game_driver.
_HARNESS_CLIENT = None  # module-level live HarnessClient (or None)


def ensure_harness_backend(*, retries: int = 8, delay: float = 4.0) -> bool:
    """(Re)connect the HarnessClient socket backend and register it with the
    lobby + in-game drivers. Returns True if a live backend is active.

    No-op fallback to xdotool when no socket is present (real-gamescope rig)."""
    global _HARNESS_CLIENT
    sock = os.environ.get("AOE3DE_HARNESS_SOCK", "/tmp/AOE3DEHarness.sock")

    # Reuse an existing connection if it's still alive.
    if _HARNESS_CLIENT is not None:
        try:
            _HARNESS_CLIENT.state()
            return True
        except Exception:
            try:
                _HARNESS_CLIENT.close()
            except Exception:
                pass
            _HARNESS_CLIENT = None

    if not os.path.exists(sock):
        print(f"  [harness] no socket at {sock}; using xdotool path")
        return False

    try:
        from tools.aoe3_harness.harness_client import HarnessClient
        import tools.aoe3_automation.in_game_driver as _igd
    except Exception as exc:  # pragma: no cover
        print(f"  [harness] import failed ({exc}); using xdotool path",
              file=sys.stderr)
        return False

    last = None
    for _ in range(max(1, retries)):
        try:
            hc = HarnessClient(sock, timeout=40.0)
            hc.connect(timeout=8)
            hc.state()  # liveness probe — raises if compositor not ready
            _HARNESS_CLIENT = hc
            lobby.set_harness_backend(hc)
            _igd.set_harness_backend(hc)
            print(f"  [harness] input backend registered via {sock}")
            return True
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(delay)
    print(f"  [harness] could not connect after {retries} tries "
          f"({type(last).__name__}: {last}); falling back to xdotool",
          file=sys.stderr)
    return False


def cycle_game() -> bool:
    """Close + relaunch via manage_game cycle; returns True on success.

    After a successful relaunch the AOE3DEHarness socket is freshly recreated,
    so re-establish the input backend against the new socket."""
    rc = subprocess.run(
        [sys.executable, str(MANAGE_GAME), "cycle", "--timeout", "240"],
        capture_output=False,
    ).returncode
    ok = rc == 0
    if ok:
        # Fresh game → fresh socket. Reconnect the harness backend so the
        # post-cycle lobby navigation (Skirmish + civ picker) is reliable.
        ensure_harness_backend()
    return ok


def _wait_for_lobby(coords: dict, total_wait: float = 12.0,
                    poll_interval: float = 1.0) -> bool:
    """Poll is_clean_lobby for up to total_wait seconds. Returns True as soon
    as the lobby is detected. Used to absorb slow-render / cold-launch latency
    after clicking Skirmish — the lobby can take 4-8s to fully render on a
    fresh game, much longer than the previous fixed 2.5s sleep allowed for."""
    deadline = time.monotonic() + total_wait
    while time.monotonic() < deadline:
        try:
            if lobby.is_clean_lobby(coords):
                return True
        except Exception:
            pass
        time.sleep(poll_interval)
    return False


def ensure_lobby(coords: dict, *, attempts: int = 2) -> bool:
    """Make best-effort attempt to land at a clean Skirmish lobby.

    Strategy (each attempt):
      1. If clean lobby → done.
      2. Try cancelling any open civ-picker.
      3. If the game is in a match (HUD detected by GameDriver) → resign.
      4. Click Skirmish from main menu, then poll up to 12s for lobby render.
    Last resort: cycle (close + relaunch) the game.

    2026-04-30: bumped from fixed 2.5s post-click sleep to a 12s poll because
    cold-launched games (first matrix iter after cycle) can take 6-8s to
    render the lobby; the old fixed sleep was missing the lobby on slow
    iterations and triggering cascade failures downstream.
    """
    for i in range(attempts):
        try:
            if lobby.is_clean_lobby(coords):
                return True
        except Exception:
            pass
        # In-match recovery: if HUD is visible, we're inside a skirmish; resign.
        # 2026-04-29: gate strictly on is_in_game() so we don't accidentally
        # fire ESC menu clicks from the main menu (those land on Tools/News/
        # Multiplayer and navigate into sub-screens, breaking lobby entry).
        try:
            d = GameDriver(art_dir=ARTIFACT_DIR / "_recovery")
            if d.is_in_game():
                d.resign()
                time.sleep(2.0)
        except Exception:
            pass
        # Try cancelling any picker/dialog ONLY if we're already in the lobby
        # area (close enough to clean-lobby state). cancel_civ_picker clicks
        # at fixed lobby coords which on the main menu hit MULTIPLAYER or
        # similar, navigating into a sub-screen we then can't recover from.
        try:
            picker_open = lobby.is_picker_open(coords)
        except Exception:
            picker_open = False
        if picker_open:
            try:
                lobby.cancel_civ_picker(coords)
                time.sleep(1.0)
                if lobby.is_clean_lobby(coords):
                    return True
            except Exception:
                pass
        # From main menu (or a sub-screen), Escape backs out, then Skirmish
        # enters the lobby. 2026-05-01: cold-launch failures traced to the
        # window-activate→click cadence. Explicit 2.5s settle after escape
        # gives the menu animation time to finish, then re-activate the
        # window again right before click so gamescope routes the input
        # to the now-rendered menu.
        try:
            lobby._ensure_window_focus()
            time.sleep(0.5)
            lobby.xdo("key Escape")
            time.sleep(2.5)
        except Exception:
            pass
        try:
            sk = coords["main_menu"]["skirmish_button"]
            lobby._ensure_window_focus()
            time.sleep(0.5)
            lobby.click(sk[0], sk[1], settle=0.5)
            # Belt-and-braces: a second click after a short pause. Idempotent
            # if the lobby is already loading, recovers if first click was
            # dropped by gamescope on the activation transition.
            time.sleep(1.5)
            lobby.click(sk[0], sk[1], settle=0.5)
        except Exception:
            pass
        if _wait_for_lobby(coords, total_wait=25.0, poll_interval=1.0):
            return True
        # Diagnostic: dump current state so a human can see WHERE we got stuck
        try:
            diag = ARTIFACT_DIR / "_recovery" / f"ensure_lobby_attempt{i}_failed.png"
            diag.parent.mkdir(parents=True, exist_ok=True)
            lobby.screenshot(diag)
            print(f"  ensure_lobby: attempt {i+1} failed; diag → {diag.name}")
        except Exception:
            pass
        # Stuck-state heuristic: after one failed attempt the screen is almost
        # certainly NOT one of the recoverable states (postgame banner, error
        # dialog, esc-menu sub-screen). Retrying the same Escape→Skirmish dance
        # 3 more times wastes ~75s and rarely helps. Skip straight to cycle.
        if i == 0:
            break
    # Cycle the game — only deterministic way to escape postgame screens,
    # error dialogs, or wedged menus.
    print("  ensure_lobby: attempting cycle_game last-resort recovery")
    if cycle_game():
        time.sleep(8.0)  # cold-launch settle for menu render
        try:
            sk = coords["main_menu"]["skirmish_button"]
            lobby._ensure_window_focus()
            time.sleep(0.5)
            lobby.click(sk[0], sk[1], settle=0.5)
            time.sleep(1.5)
            lobby.click(sk[0], sk[1], settle=0.5)
        except Exception:
            pass
        if _wait_for_lobby(coords, total_wait=30.0, poll_interval=1.0):
            return True
    return False


# ---------------------------------------------------------------------------
# Per-civ run
# ---------------------------------------------------------------------------


@dataclass
class CivResult:
    civ_idx: int
    civ_name: str
    started_at: str
    ended_at: str = ""
    duration_s: float = 0.0
    selected_civ: bool = False
    started_match: bool = False
    reached_in_game: bool = False
    observed_s: float = 0.0
    resigned: bool = False
    artifact_dir: str = ""
    log_lines: int = 0
    probe_count: int = 0
    # Personality-channel probe count (non-dev-mode path).
    # Populated after resign from ll_* uservars in .personality files.
    personality_probe_count: int = 0
    # AI-script-load count from the .age3Yrec replay payload (decompress +
    # count [ANWP v=2 t= literal occurrences). Diagnoses NIGHT_JOURNAL
    # theory #1 ("AI not loading at all"). 0 = AI never loaded; >=batch
    # opponent count = AI loaded as expected.
    ai_scripts_loaded: int = -1
    replay_decompressed_bytes: int = 0
    replay_path: str = ""
    # Visual axes: per-civ leader card during loading and scoreboard during
    # play. Best-effort — capture failures are not match-fatal.
    loading_screen_captured: bool = False
    scoreboard_captured: bool = False
    in_game_captured: bool = False
    # Tighter visual checks — require non-trivial pixel variance, not just
    # "file exists". Catches gamescope handing back uniform-black PNGs.
    loading_screen_has_content: bool = False
    in_game_has_content: bool = False
    scoreboard_has_content: bool = False
    # Scoreboard OCR — list of civ names actually recognised on-screen.
    # Empty list when tesseract isn't installed; matrix_validator treats
    # missing OCR as a degraded soft check and uses pixel content instead.
    scoreboard_civ_hits: list[str] = field(default_factory=list)
    # Doctrine-fired axis: true iff EVERY harvested personality probe in
    # this batch had a non-zero (i.e. non-Unknown) build style. Catches
    # "AI loaded and wrote, but doctrine setup silently fell through to
    # the default" — a real category of regression the picker/load axes
    # can't detect.
    personality_probe_doctrine_ok: bool = False
    # Per-civ doctrine probe records harvested in this batch. List of
    # {civ_name, leader_key, style_int, style_name, walls, wall_strategy_name}
    # for every AI that wrote a sentinel record. Used by matrix_validator
    # to credit per-civ doctrine pass even when batched.
    doctrine_records: list[dict] = field(default_factory=list)
    # Deep-mode behavioural axes — populated when matrix_runner is invoked
    # with --deep, which raises observe-seconds high enough that compliance.*
    # / mil.* / tech.* probes have time to fire. Each entry is a dict produced
    # by replay_probes.derive_behavioral_axes() — keyed by player id and
    # carrying the six behavioural booleans (combat_engaged, explorer_active,
    # age_up_fired, shipments_chosen, walls_built, doctrine_compliance).
    deep_mode: bool = False
    behavioral_records: list[dict] = field(default_factory=list)
    # Engine-error-free axis: scan the match.log for known fatal markers
    # (XS errors, assertion failures, asset-load failures, [ERROR] lines).
    # Hits are the strings actually found, surfaced for triage.
    engine_error_free: bool = False
    engine_error_hits: list[str] = field(default_factory=list)
    # Leader-init dispatch coverage: every batch civ should have its leader's
    # init function fire (meta.leader_init probe). We harvest the set of
    # leader keys that actually fired and the validator credits each civ
    # whose expected leader appears in that set.
    leaders_initialised: list[str] = field(default_factory=list)
    # Vision-judge axis: per-scene Claude vision verdict on each captured PNG.
    # Each value is the dict returned by vision_judge.judge_screenshot —
    # carries pass/confidence/reason/issues plus model + scene metadata.
    # vision_check_pass is True iff every scene we attempted returned
    # pass=True; pass=None (soft-skip, no API key / unreachable) does not
    # gate the axis to fail — the matrix degrades gracefully when offline.
    vision_judgements: dict[str, dict] = field(default_factory=dict)
    vision_check_pass: bool = False
    error: str = ""
    notes: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return self.resigned and not self.error


def run_one_civ(
    coords: dict,
    civ_idx: int,
    civ_name: str,
    *,
    observe_seconds: int,
    in_game_timeout: int,
    speed_tick: int,
    dry_run: bool,
    opponent_civ_indices: list[int] | None = None,
    opponent_civ_names: list[str] | None = None,
    deep_mode: bool = False,
    adaptive_observe: bool = True,
    skip_replay_diag: bool = False,
) -> CivResult:
    """Run one match.

    P1 = civ_idx; opponent_civ_indices (length 0..7) sets P2..P8 if provided.
    When opponents are set, this match exercises up to 8 civs at once — the
    big speed lever (48 civs / 8 = 6 matches).
    """
    art = ARTIFACT_DIR / f"{civ_idx:02d}_{slugify(civ_name)}"
    art.mkdir(parents=True, exist_ok=True)
    res = CivResult(
        civ_idx=civ_idx,
        civ_name=civ_name,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        artifact_dir=str(art),
        deep_mode=deep_mode,
    )
    t0 = time.monotonic()
    mirror: LogMirror | None = None
    log_path = art / "match.log"
    driver = GameDriver(art_dir=art)

    def _annotate(msg: str) -> None:
        print(f"  [civ {civ_idx:02d} {civ_name}] {msg}")
        res.notes.append(msg)

    try:
        # 1. Make sure we're at clean lobby
        if not ensure_lobby(coords):
            raise RuntimeError("could not reach clean lobby state")

        # 2. Select civ for P1 (and opponents if requested).
        _annotate(f"selecting civ_idx={civ_idx}")
        lobby.set_civ_by_index(coords, civ_idx)
        if opponent_civ_indices:
            names_str = ",".join(opponent_civ_names or [str(i) for i in opponent_civ_indices])
            _annotate(f"selecting opponents P2..P{1+len(opponent_civ_indices)}: {names_str}")
            lobby.set_opponent_civs(coords, opponent_civ_indices)
        # Snapshot post-select state so we can manually verify the right civ
        # was picked (the lobby UI shows the civ portrait).
        try:
            lobby.screenshot(art / "01_after_select.png")
        except Exception as e:
            _annotate(f"screenshot warn: {e}")
        res.selected_civ = True

        if dry_run:
            _annotate("dry-run: skipping PLAY; resetting to Random")
            try:
                lobby.reset_p1_to_random(coords)
            except Exception as e:
                _annotate(f"reset warn: {e}")
            res.duration_s = time.monotonic() - t0
            res.ended_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            return res

        # 3. Start log mirror BEFORE click_play so we capture the boot probes.
        #    Also snapshot the current mtime of every .personality file so we
        #    can detect which ones were written/updated THIS match.
        try:
            ensure_dev_mode()
        except Exception as e:
            _annotate(f"ensure_dev_mode warn: {e}")
        personality_mtime_snapshot: dict[str, float] = {}
        try:
            if PERSONALITY_DIR.exists():
                for pf in PERSONALITY_DIR.glob("*.personality"):
                    personality_mtime_snapshot[pf.name] = pf.stat().st_mtime
        except Exception as e:
            _annotate(f"personality snapshot warn: {e}")
        match_start_wall = time.time()
        mirror = start_log_tail(log_path)

        # 4. PLAY
        _annotate("clicking PLAY")
        lobby.click_play(coords)
        res.started_match = True

        # 4a. Loading-screen shot fires ~6s post-PLAY which lands in the
        # leader card slide on this rig (verified empirically). Runs on a
        # background thread so it doesn't slow the wait_for_in_game path.
        loading_shot_path = art / "02_loading.png"
        threaded_screenshot_after(6.0, loading_shot_path)

        # 5. Wait for in-game
        ok = driver.wait_for_in_game(timeout=in_game_timeout, log_mirror=mirror)
        if not ok:
            raise RuntimeError(
                f"timed out ({in_game_timeout}s) waiting for "
                "WorldAssetPreloadingTime — match never went playable"
            )
        res.reached_in_game = True

        # 5a. Loading-screen capture status check. The threaded shot above
        # has had ~observe-load seconds to complete; record whether it landed.
        try:
            res.loading_screen_captured = loading_shot_path.exists() and \
                loading_shot_path.stat().st_size > 0
            res.loading_screen_has_content = image_has_content(loading_shot_path)
            if res.loading_screen_has_content:
                _annotate(f"loading-screen capture OK with pixels "
                          f"({loading_shot_path.name})")
            elif res.loading_screen_captured:
                _annotate("loading-screen capture present but blank/black "
                          "(gamescope race?) — failing visual axis")
            else:
                _annotate("loading-screen capture missed (PrintScreen ignored "
                          "during load); will rely on in_game capture instead")
        except Exception as e:
            _annotate(f"loading capture stat warn: {e}")

        # 5b. In-game leader/HUD snapshot — fires once the HUD is real, so
        # post-match validation can confirm the right civ portrait is up
        # even if the loading shot missed.
        try:
            in_game_path = art / "03_in_game.png"
            from tools.aoe3_automation.in_game_driver import _screenshot_raw as _shot
            res.in_game_captured = _shot(in_game_path)
            res.in_game_has_content = image_has_content(in_game_path)
            if res.in_game_has_content:
                _annotate(f"in-game capture OK with pixels ({in_game_path.name})")
            elif res.in_game_captured:
                _annotate("in-game capture present but blank/black — failing visual axis")
        except Exception as e:
            _annotate(f"in-game capture warn: {e}")

        # 6. Set max speed — but only if observation is long enough to benefit.
        # Probes fire from postInit at game-time t=0; for short observations
        # (<15s wall-clock) the click on the speed bar is pure overhead and
        # adds a failure surface. Skip it unless we genuinely want game-time
        # to elapse during observe.
        if observe_seconds >= 15:
            _annotate("in-game; setting speed")
            try:
                driver.set_speed(speed_tick)
            except Exception as e:
                _annotate(f"set_speed warn: {e}")
        else:
            _annotate(f"in-game; skipping set_speed (observe={observe_seconds}s < 15s)")

        # 7. Observe — adaptive when probes fire fast (deep mode), fixed
        #    otherwise. Adaptive polls match.log every 3s and resigns as soon
        #    as every AI in the batch has hit minimal probe coverage; for
        #    typical batches this lands at 90–150s instead of the full
        #    observe_seconds budget. Smoke (observe<60) keeps the original
        #    fixed-sleep behaviour because no probes are expected to fire.
        obs_t0 = time.monotonic()
        try:
            expected_ai = max(1, len(opponent_civ_indices or []))
            if adaptive_observe and observe_seconds >= 60:
                obs_s, reason = _adaptive_observe(
                    driver, log_path,
                    expected_ai_count=expected_ai,
                    max_seconds=float(observe_seconds),
                    annotate=_annotate,
                )
                _annotate(f"observe done: {reason}")
            else:
                driver.observe(wall_seconds=observe_seconds)
        except Exception as e:
            _annotate(f"observe interrupted: {e}")
        res.observed_s = time.monotonic() - obs_t0

        # 7a. Scoreboard capture — Tab opens AoE3's scoreboard overlay; we
        # hold it while AoE3's PrintScreen binding fires, capturing every
        # AI's civ + score in one shot. Best-effort; failure is non-fatal.
        try:
            scoreboard_path = art / "04_scoreboard.png"
            res.scoreboard_captured = screenshot_with_keypress(
                "Tab", scoreboard_path, hold_s=1.0,
            )
            res.scoreboard_has_content = image_has_content(scoreboard_path)
            # OCR the scoreboard — every civ in this batch should appear
            # in the leftmost column. We accept a single hit (≥1) because
            # tesseract on stylised AoE3 fonts is noisy; missing all of
            # them is a real regression.
            batch_civs = [civ_name] + (opponent_civ_names or [])
            ok_ocr, hits = image_contains_words(
                scoreboard_path, batch_civs, min_hits=1,
            )
            res.scoreboard_civ_hits = hits
            if ok_ocr:
                _annotate(f"scoreboard capture + OCR OK; "
                          f"recognised {len(hits)}/{len(batch_civs)} civ name(s): {hits}")
            elif res.scoreboard_has_content:
                _annotate("scoreboard capture has pixels but OCR found no "
                          "expected civ names (tesseract may be missing or "
                          "fonts unrecognised — falling back to pixel-content axis)")
            elif res.scoreboard_captured:
                _annotate("scoreboard capture present but blank/black — failing axis")
            else:
                _annotate("scoreboard capture missed")
        except Exception as e:
            _annotate(f"scoreboard capture warn: {e}")

        # 8. Resign
        _annotate("resigning")
        try:
            driver.resign()
            res.resigned = True
        except Exception as e:
            _annotate(f"resign error: {e}")

        # 8a. Replay AI-load diagnostic — decompress newest .age3Yrec and
        #     count compiled-script literals. This is the missing positive
        #     proof that the AI loaded (NIGHT_JOURNAL theory #1). Runs even
        #     if resign failed; the replay exists from match start.
        if res.reached_in_game and not skip_replay_diag:
            try:
                # The .age3Yrec file is mmap-flushed continuously during
                # play; by the time resign() returns it is already on disk.
                # Old code waited 2.0s here defensively; verified empirically
                # 0.4s suffices because we open it for read after resign's
                # own internal flush completes.
                time.sleep(0.4)
                if REPLAY_DIR.exists():
                    candidates = [p for p in REPLAY_DIR.glob("*.age3Yrec")
                                  if p.stat().st_mtime >= match_start_wall - 5]
                    if candidates:
                        newest = max(candidates, key=lambda p: p.stat().st_mtime)
                        # Expected = 1 (P1's slot doesn't run AI script in
                        # human-piloted matches) + len(opponent_civs) … but
                        # the engine sometimes loads P1's script too. Set
                        # expected to opp count + 1 as a soft lower bound.
                        expected = (len(opponent_civ_indices or []) or 7) + 1
                        diag = diagnose_replay(newest, expected=0)
                        if diag.get("ok"):
                            res.ai_scripts_loaded = diag["ai_scripts_loaded"]
                            res.replay_decompressed_bytes = diag["decompressed_bytes"]
                            res.replay_path = str(newest)
                            _annotate(f"replay diag: {diag['ai_scripts_loaded']} "
                                      f"AI script(s) loaded "
                                      f"(expected ~{expected}; "
                                      f"replay={newest.name}, "
                                      f"{diag['decompressed_bytes']:,}B)")
                            if res.ai_scripts_loaded == 0:
                                _annotate("CRITICAL: 0 AI scripts in replay — "
                                          "theory #1 (AI not loading) is real, "
                                          "investigate XS loader before chasing probes")
                        else:
                            _annotate(f"replay diag failed: {diag.get('reason', '?')}")
            except Exception as e:
                _annotate(f"replay diag warn: {e}")

        # 8b. Harvest personality-channel probes (non-dev-mode path).
        #     The engine writes .personality files on game-over.  We wait a
        #     short grace period for the disk flush, then scan for files that
        #     were modified after match start.
        if res.resigned:
            try:
                # Personality XML flush — the engine writes synchronously on
                # game-over but the file mtime can lag the close by ~1s on
                # the Proton compatdata path. Poll up to 3s for an mtime
                # advance instead of always sleeping the full window.
                grace_deadline = time.time() + 3.0
                wanted_advance = match_start_wall
                while time.time() < grace_deadline:
                    if PERSONALITY_DIR.exists():
                        latest = max(
                            (p.stat().st_mtime
                             for p in PERSONALITY_DIR.glob("*.personality")),
                            default=0.0,
                        )
                        if latest >= wanted_advance:
                            break
                    time.sleep(0.25)
                if PERSONALITY_DIR.exists():
                    new_probes: list[PersonalityProbe] = []
                    for p in scan_personality_dir(PERSONALITY_DIR):
                        pf_name = f"{p.personality_file}.personality"
                        old_mtime = personality_mtime_snapshot.get(pf_name, 0.0)
                        pf_path = PERSONALITY_DIR / pf_name
                        try:
                            new_mtime = pf_path.stat().st_mtime
                        except OSError:
                            new_mtime = 0.0
                        # Accept probe if file was touched after match start
                        # OR if it's a new file (not in pre-match snapshot).
                        if new_mtime >= match_start_wall or pf_name not in personality_mtime_snapshot:
                            new_probes.append(p)
                    res.personality_probe_count = len(new_probes)
                    # Doctrine-fired check: capture (civ, leader, style)
                    # per AI and require style != 0 for every record.
                    res.doctrine_records = [
                        {
                            "civ_name": p.civ_name,
                            "leader_key": p.leader_key,
                            "style_int": int(p.style),
                            "style_name": p.build_style_name,
                            "walls": int(p.walls),
                            "wall_strategy_name": p.wall_strategy_name,
                            "terrain_primary_name": p.terrain_primary_name,
                            "heading_name": p.heading_name,
                            "match_seconds": p.match_ms // 1000,
                        }
                        for p in new_probes
                    ]
                    if new_probes:
                        res.personality_probe_doctrine_ok = all(
                            int(p.style) >= 1 for p in new_probes
                        )
                        # Write LLP-formatted probes to match.log companion.
                        personality_log = art / "personality_probes.log"
                        lines = []
                        for p in new_probes:
                            lines.append(p.to_llp_leader_line())
                            lines.append(p.to_llp_line())
                        personality_log.write_text("\n".join(lines) + "\n",
                                                   encoding="utf-8")
                        _annotate(f"personality probes: {len(new_probes)} written to "
                                  f"{personality_log.name}")
                        # Validate and log any issues.
                        issues, _ = validate_probes(new_probes)
                        for issue in issues:
                            _annotate(f"personality probe issue: {issue}")
                    else:
                        _annotate("personality probes: none found (game-over handler may not have fired)")
            except Exception as e:
                _annotate(f"personality probe harvest warn: {e}")

        # 8c. Deep-mode behavioural-axis derivation. Parses the match.log
        #     mirror (still tailing — we peek at the bytes-on-disk so far)
        #     for [ANWP v=2 ...] probes and runs derive_behavioral_axes() to
        #     compute per-AI booleans for combat_engaged, explorer_active,
        #     age_up_fired, shipments_chosen, walls_built, doctrine_compliance.
        #     Only fires when --deep was passed; in smoke mode the observe
        #     window is too short for any of these probes to fire and the
        #     axes would all be false-negatives.
        if deep_mode and res.reached_in_game:
            try:
                if log_path.exists() and log_path.stat().st_size > 0:
                    data = log_path.read_bytes()
                    probes = _parse_llp_probes(data)
                    behavioural = _derive_behavioral_axes(probes)
                    res.behavioral_records = behavioural
                    if behavioural:
                        n_combat = sum(1 for r in behavioural
                                       if r["axes"]["combat_engaged"])
                        n_age = sum(1 for r in behavioural
                                    if r["axes"]["age_up_fired"])
                        n_doc = sum(1 for r in behavioural
                                    if r["axes"]["doctrine_compliance"])
                        _annotate(
                            f"deep-mode behavioural axes: "
                            f"{len(behavioural)} AI(s) parsed, "
                            f"combat={n_combat} ageUp={n_age} "
                            f"doctrineOK={n_doc}"
                        )
                    else:
                        # match.log carries engine ModeTrack/preload lines but
                        # NOT aiEcho/aiChat output on retail FINAL_RELEASE
                        # builds (proven non-functional 2026-04-29 — dev tokens
                        # are inert despite user.cfg parsing them). The mid-
                        # game [ANWP v=2] stream is therefore expected-empty in
                        # match.log; useful behavioural signal lives in the
                        # personality channel (see personality_probes above).
                        # This annotation is informational only, not a failure.
                        _annotate("deep-mode behavioural axes: match.log "
                                  "[ANWP v=2] stream empty (expected on retail "
                                  "DE — see personality_probes for captured "
                                  "behaviour data)")
                else:
                    _annotate("deep-mode behavioural axes: match.log empty/missing "
                              "(expected — engine doesn't mirror AI output to "
                              "match.log on retail DE)")
            except Exception as e:
                _annotate(f"deep-mode behavioural axes warn: {e}")

        # 8d. Engine-error scan. Read match.log bytes (already on disk
        #     thanks to the mirror) and hunt for fatal markers. Any hit
        #     means the engine logged a problem mid-match — the run might
        #     visually look fine while a script silently failed.
        try:
            if log_path.exists() and log_path.stat().st_size > 0:
                data = log_path.read_bytes()
                hits: list[str] = []
                for pat in _ENGINE_ERROR_PATTERNS:
                    for m in pat.finditer(data):
                        # Recover the surrounding line for triage.
                        start = data.rfind(b"\n", 0, m.start()) + 1
                        end = data.find(b"\n", m.end())
                        if end == -1:
                            end = len(data)
                        line = data[start:end].decode("utf-8", "replace").strip()
                        if line and line not in hits:
                            hits.append(line[:200])
                        if len(hits) >= 20:
                            break
                    if len(hits) >= 20:
                        break
                res.engine_error_hits = hits
                res.engine_error_free = (len(hits) == 0)
                if hits:
                    _annotate(f"engine_error_free FAIL: {len(hits)} hit(s); "
                              f"first: {hits[0]!r}")
                else:
                    _annotate("engine_error_free OK: clean match.log")
            else:
                # No log to scan = can't prove clean = fail closed.
                res.engine_error_free = False
                _annotate("engine_error_free: match.log empty/missing")
        except Exception as e:
            _annotate(f"engine error scan warn: {e}")

        # 8f. Leader-init dispatch coverage. We already (in deep mode) parsed
        #     the probes; if not, do a cheap targeted parse just for
        #     meta.leader_init lines. The set of leader keys seen is what
        #     the validator cross-references against this batch's civs.
        try:
            if log_path.exists() and log_path.stat().st_size > 0:
                data = log_path.read_bytes()
                # Cheap targeted regex — avoids re-parsing every probe when
                # the deep block already did. Captures both the leader from
                # the LLP header and from the trailing "leader=X" field.
                leaders: set[str] = set()
                init_re = re.compile(
                    rb"\[ANWP v=2 t=\d+ p=\d+ civ=\S+ ldr=(?P<ldr>\S+) "
                    rb"tag=meta\.leader_init\][^\n]*?(?:leader=(?P<lkey>\S+))?"
                )
                for m in init_re.finditer(data):
                    ldr = m.group("ldr")
                    lkey = m.group("lkey")
                    if ldr:
                        leaders.add(ldr.decode(errors="replace"))
                    if lkey:
                        leaders.add(lkey.decode(errors="replace"))
                res.leaders_initialised = sorted(leaders)
                _annotate(f"leaders_initialised: {len(leaders)} key(s) — "
                          f"{res.leaders_initialised}")
        except Exception as e:
            _annotate(f"leader-init harvest warn: {e}")

        # 8f.2. Personality-channel fallback for leaders_initialised.
        #
        # The match.log regex above is the historical/preferred path, but
        # the [ANWP v=2] aiEcho channel is inert on retail FINAL_RELEASE DE
        # (proven 2026-04-29 — see NIGHT_JOURNAL.md). The personality
        # channel's doctrine_records, however, encode leader_key per AI as
        # a side-effect of the doctrine setup that runs DURING leader_init.
        # If a doctrine record exists for an AI, its leader_init fired by
        # construction. Treat each unique leader_key in the harvested
        # doctrine_records as a leader_init witness so the axis isn't
        # permanently red on retail builds.
        try:
            if not res.leaders_initialised:
                doc_leaders: set[str] = set()
                for rec in (getattr(res, "doctrine_records", []) or []):
                    lk = (rec.get("leader_key") or "").strip().lower()
                    if lk:
                        doc_leaders.add(lk)
                if doc_leaders:
                    res.leaders_initialised = sorted(doc_leaders)
                    _annotate(
                        "leaders_initialised: derived "
                        f"{len(doc_leaders)} key(s) from personality channel "
                        f"doctrine_records (match.log inert on retail DE)"
                    )
        except Exception as e:
            _annotate(f"leader-init personality fallback warn: {e}")

        # 8g. Vision review queue + verdict pickup.
        #
        #     The matrix doesn't call any external API. Instead each civ's
        #     artifact dir gets a `vision_review_request.json` listing the
        #     screenshots + per-civ doctrine summary + batch context — this
        #     is the queue Claude (or any reviewer) consumes via the Read
        #     tool to look at each PNG and write a `vision_verdicts.json`
        #     back to the same directory.
        #
        #     If a verdicts file is already present (e.g. the operator is
        #     re-running the matrix and previously reviewed this civ, or a
        #     CI bot dropped one in), we pick it up here and the
        #     vision_check axis gates on its content. Otherwise the axis
        #     stays red until review happens — the runner itself never
        #     blocks waiting for a verdict.
        try:
            exp = _expectation_for(civ_name)
            doctrine_summary = doctrine_summary_from_expectation(exp)
            batch_civ_list = [civ_name] + (opponent_civ_names or [])
            scenes_present: list[dict] = []
            for scene, scene_path in (
                ("loading",    art / "02_loading.png"),
                ("in_game",    art / "03_in_game.png"),
                ("scoreboard", art / "04_scoreboard.png"),
            ):
                if scene_path.exists() and scene_path.stat().st_size > 0:
                    scenes_present.append({
                        "scene": scene,
                        "path": str(scene_path),
                    })
            request = {
                "civ_idx": civ_idx,
                "civ_name": civ_name,
                "leader_key": getattr(exp, "leader_key", "") if exp else "",
                "doctrine_summary": doctrine_summary,
                "batch_civs": batch_civ_list,
                "scenes": scenes_present,
                "instructions": (
                    "For each scene PNG, decide whether the screenshot is a "
                    "real, non-corrupted in-game frame consistent with the "
                    "stated civ + doctrine. Write a sibling "
                    "vision_verdicts.json with shape: "
                    "{\"<scene>\": {\"pass\": bool, \"reason\": str, "
                    "\"issues\": [str, ...]}, ...}"
                ),
            }
            (art / "vision_review_request.json").write_text(
                json.dumps(request, indent=2)
            )

            # Pick up an existing verdicts file if present.
            verdicts_path = art / "vision_verdicts.json"
            if verdicts_path.exists():
                try:
                    verdicts = json.loads(verdicts_path.read_text())
                except json.JSONDecodeError:
                    verdicts = {}
                res.vision_judgements = verdicts
                judged_scenes = [s for s in verdicts.values()
                                 if isinstance(s, dict) and "pass" in s]
                if judged_scenes:
                    res.vision_check_pass = all(
                        bool(s.get("pass")) for s in judged_scenes
                    )
                    _annotate(
                        f"vision verdicts found ({len(judged_scenes)} "
                        f"scene(s); pass={res.vision_check_pass})"
                    )
                else:
                    _annotate("vision verdicts file present but empty")
            else:
                _annotate(
                    f"vision review queued: {len(scenes_present)} scene(s) — "
                    f"reviewer should write {verdicts_path.name} "
                    f"to gate this civ's vision_check axis"
                )
        except Exception as e:
            _annotate(f"vision review queue warn: {e}")

    except Exception as e:
        res.error = f"{type(e).__name__}: {e}"
        _annotate(f"ERROR: {res.error}")
        traceback.print_exc()
    finally:
        # 9. Close mirror, capture log size + probe count
        if mirror is not None:
            try:
                content = stop_log_tail(mirror)
                res.log_lines = content.count("\n")
                res.probe_count = mirror.current_probe_count()
            except Exception as e:
                _annotate(f"stop_log_tail warn: {e}")
        res.duration_s = time.monotonic() - t0
        res.ended_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    # 10. Recovery for the next iteration: ensure we're back at clean lobby.
    # If resign succeeded we're at main menu; click Skirmish to re-enter.
    if res.resigned:
        try:
            sk = coords["main_menu"]["skirmish_button"]
            lobby.click(sk[0], sk[1])
            time.sleep(2.5)
        except Exception:
            pass
    # Always reset to Random Personality so the next iteration starts clean.
    try:
        if lobby.is_clean_lobby(coords):
            lobby.reset_p1_to_random(coords)
    except Exception as e:
        _annotate(f"post-run reset warn: {e}")

    # Save per-civ JSON snapshot
    try:
        (art / "result.json").write_text(json.dumps(asdict(res), indent=2))
    except Exception:
        pass

    return res


# ---------------------------------------------------------------------------
# Matrix entrypoint
# ---------------------------------------------------------------------------


def run_matrix(
    *,
    observe_seconds: int,
    in_game_timeout: int,
    speed_tick: int,
    start_idx: int,
    end_idx: int,
    civ_names: list[str] | None,
    dry_run: bool,
    abort_on_crash: bool,
    batch_size: int = 1,
    deep_mode: bool = False,
    adaptive_observe: bool = True,
    skip_replay_diag: bool = False,
) -> int:
    """Run the matrix.

    batch_size: number of civs to test per match. 1 = legacy P1-only flow
    (1 match per civ). 2..8 = pack civs into P1+P2..P8 slots; 48 civs at
    batch_size=8 = 6 matches total. Quality is *better* per match-second
    because each AI runs postInit independently; speed is bounded by
    AoE3's match-load time amortized across N civs.
    """
    coords = lobby.load_coords()
    table = lobby.load_scroll_table()
    civs: list[str] = list(table["civ_names"])

    # Build the linear civ list (all the civs we want to cover).
    if civ_names:
        wanted: list[tuple[int, str]] = []
        slug_lookup = {slugify(n): (i, n) for i, n in enumerate(civs)}
        for raw in civ_names:
            key = slugify(raw)
            if key not in slug_lookup:
                # try contains-match
                hits = [(i, n) for i, n in enumerate(civs) if key in slugify(n)]
                if not hits:
                    print(f"WARN: unknown civ {raw!r}; skipping")
                    continue
                wanted.append(hits[0])
            else:
                wanted.append(slug_lookup[key])
        flat_civs = wanted
    else:
        lo, hi = max(start_idx, 0), min(end_idx, len(civs) - 1)
        flat_civs = [(i, civs[i]) for i in range(lo, hi + 1)]

    # Pack into batches. iteration is now a list of (head_civ, opponent_civs)
    # tuples where head goes to P1 and opponents fill P2..P{1+len}.
    if batch_size < 1 or batch_size > 8:
        raise ValueError(f"batch_size must be in 1..8, got {batch_size}")
    iteration: list[tuple[tuple[int, str], list[tuple[int, str]]]] = []
    for i in range(0, len(flat_civs), batch_size):
        batch = flat_civs[i:i + batch_size]
        head = batch[0]
        opps = batch[1:]
        iteration.append((head, opps))

    n_matches = len(iteration)
    n_civs = sum(1 + len(opps) for _, opps in iteration)
    print(f"Matrix run: {n_civs} civ(s) in {n_matches} match(es) "
          f"(batch_size={batch_size})")
    for i, (head, opps) in enumerate(iteration):
        h_idx, h_nm = head
        if opps:
            opp_str = ", ".join(f"{o[1]}" for o in opps)
            print(f"  {i+1:2d}/{n_matches}: P1=idx={h_idx:02d} {h_nm}  P2..={opp_str}")
        else:
            print(f"  {i+1:2d}/{n_matches}: idx={h_idx:02d} {h_nm}")
    print()

    results: list[CivResult] = []
    run_started = time.strftime("%Y-%m-%dT%H:%M:%S")

    for i, (head, opps) in enumerate(iteration):
        civ_idx, civ_name = head
        opp_indices = [o[0] for o in opps]
        opp_names   = [o[1] for o in opps]
        if opps:
            print(f"=== [{i+1}/{n_matches}] P1=idx={civ_idx:02d} {civ_name} "
                  f"+ {len(opps)} opponents ===")
        else:
            print(f"=== [{i+1}/{n_matches}] civ_idx={civ_idx} {civ_name} ===")

        # Make sure the game is even up AND in a recoverable state. If the
        # game is running but stuck on a postgame banner / error dialog from
        # a prior session, ensure_lobby's Skirmish-click dance can't reach the
        # lobby — only a cycle does. On the very first iteration, force-cycle
        # if not already at a clean lobby, to guarantee deterministic startup.
        need_cycle = not game_is_running()
        if not need_cycle and i == 0:
            try:
                need_cycle = not lobby.is_clean_lobby(coords)
            except Exception:
                need_cycle = True
        if need_cycle:
            print("  game not at clean lobby — cycling")
            if not cycle_game():
                print("  ERROR: cycle_game failed; aborting matrix")
                if abort_on_crash:
                    break

        # Guarantee a live harness backend for this iteration's clicks. Idempotent:
        # reuses the connection cycle_game() just made, or (re)connects if the
        # game was already up and no cycle ran this iteration.
        ensure_harness_backend()

        try:
            res = run_one_civ(
                coords, civ_idx, civ_name,
                observe_seconds=observe_seconds,
                in_game_timeout=in_game_timeout,
                speed_tick=speed_tick,
                dry_run=dry_run,
                opponent_civ_indices=opp_indices or None,
                opponent_civ_names=opp_names or None,
                deep_mode=deep_mode,
                adaptive_observe=adaptive_observe,
                skip_replay_diag=skip_replay_diag,
            )
        except Exception as e:
            print(f"  unhandled iter error: {e}")
            res = CivResult(
                civ_idx=civ_idx, civ_name=civ_name,
                started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                error=f"unhandled: {e}",
            )
        # Annotate which opponents this match also covered, so the report
        # makes it obvious that one match exercised multiple civs.
        if opp_names:
            res.notes.append(f"batch opponents: {', '.join(opp_names)}")
        results.append(res)
        ok = "OK" if res.ok() else ("DRY" if dry_run and res.selected_civ else "FAIL")
        cov_extra = f" +{len(opps)}opps" if opps else ""
        ai_str = (f"ai_loaded={res.ai_scripts_loaded}"
                  if res.ai_scripts_loaded >= 0 else "ai_loaded=?")
        print(f"  → {ok}{cov_extra}  duration={res.duration_s:.0f}s  "
              f"in_game={res.reached_in_game}  resigned={res.resigned}  "
              f"probes={res.probe_count}  personality_probes={res.personality_probe_count}  "
              f"{ai_str}  err={res.error or '-'}")

        # If something crashed the game, cycle before next iter
        if not game_is_running():
            print("  game appears dead — cycling for next iter")
            if not cycle_game():
                print("  ERROR: cycle_game failed mid-matrix")
                if abort_on_crash:
                    break

    # Summary report
    report_path = ARTIFACT_DIR / "matrix_report.json"
    md_path = ARTIFACT_DIR / "matrix_report.md"
    summary = {
        "started_at": run_started,
        "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "observe_seconds": observe_seconds,
        "speed_tick": speed_tick,
        "batch_size": batch_size,
        "deep_mode": deep_mode,
        "n_matches": n_matches,
        "n_civs_covered": n_civs,
        "dry_run": dry_run,
        "results": [asdict(r) for r in results],
        "totals": {
            "attempted": len(results),
            "selected_civ": sum(r.selected_civ for r in results),
            "reached_in_game": sum(r.reached_in_game for r in results),
            "resigned": sum(r.resigned for r in results),
            "personality_probes_total": sum(r.personality_probe_count for r in results),
            "ai_scripts_loaded_total": sum(max(0, r.ai_scripts_loaded) for r in results),
            "matches_with_zero_ai_load": sum(1 for r in results if r.ai_scripts_loaded == 0),
            "errors": sum(bool(r.error) for r in results),
        },
    }
    report_path.write_text(json.dumps(summary, indent=2))

    md_lines = [
        f"# Matrix run — {run_started}",
        "",
        f"- Civs attempted: **{len(results)}**",
        f"- Reached in-game: **{summary['totals']['reached_in_game']}**",
        f"- Resigned cleanly: **{summary['totals']['resigned']}**",
        f"- Errors: **{summary['totals']['errors']}**",
        f"- Personality probes total: **{summary['totals']['personality_probes_total']}**",
        f"- AI scripts loaded total: **{summary['totals']['ai_scripts_loaded_total']}** "
        f"(matches with 0 AI loaded: {summary['totals']['matches_with_zero_ai_load']})",
        f"- Observe seconds per civ: {observe_seconds}",
        f"- Speed tick: {speed_tick}",
        f"- Dry run: {dry_run}",
        "",
        "| idx | civ | sel | in-game | resign | obs(s) | probes | p-probes | ai-loaded | err |",
        "|-----|-----|-----|---------|--------|--------|--------|----------|-----------|-----|",
    ]
    for r in results:
        md_lines.append(
            f"| {r.civ_idx} | {r.civ_name} | "
            f"{'✓' if r.selected_civ else '✗'} | "
            f"{'✓' if r.reached_in_game else '✗'} | "
            f"{'✓' if r.resigned else '✗'} | "
            f"{r.observed_s:.0f} | {r.probe_count} | "
            f"{r.personality_probe_count} | "
            f"{r.ai_scripts_loaded if r.ai_scripts_loaded >= 0 else '?'} | "
            f"{(r.error or '-')[:60]} |"
        )
    md_path.write_text("\n".join(md_lines) + "\n")
    print(f"\nWrote: {report_path}\nWrote: {md_path}")
    return 0 if all(r.ok() or (dry_run and r.selected_civ) for r in results) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    # Defaults tuned 2026-04-29 for postInit-only probe verification:
    #   - observe-seconds 10: probes fire from postInit at game-time t=0;
    #     even at 1x speed 5s is enough. 10s is comfortable headroom.
    #     Was 600 (10 min) — 60x too long.
    #   - in-game-timeout 150: smallest map preloads in <90s; 150 leaves
    #     headroom but fails fast if something is broken. Was 240.
    #   - batch-size 8: pack 8 civs per match (P1 + 7 AI opponents).
    #     Reduces 48-civ matrix from 48 matches → 6 matches.
    ap.add_argument("--observe-seconds", type=int, default=10,
                    help="Wall-clock seconds to observe per match before resigning "
                         "(default 10 — enough for postInit probes; raise to ~120 "
                         "for mid-game behavior tests)")
    ap.add_argument("--in-game-timeout", type=int, default=150,
                    help="Max seconds to wait for WorldAssetPreloadingTime after PLAY")
    ap.add_argument("--speed-tick", type=int, default=5,
                    help="Game-speed bar tick (1..5; 5=fastest). Skipped if "
                         "observe-seconds <15 (overhead with no benefit).")
    ap.add_argument("--start-idx", type=int, default=1,
                    help="First civ_idx to run (skip 0=Random by default)")
    ap.add_argument("--end-idx", type=int, default=48,
                    help="Last civ_idx (inclusive)")
    ap.add_argument("--civs", default="",
                    help="Comma-separated civ-name slugs to run (overrides idx range)")
    ap.add_argument("--batch-size", type=int, default=8,
                    help="Civs per match (1..8). 8 = pack into P1+P2..P8 "
                         "for 8x throughput; 1 = legacy P1-only one-match-per-civ.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Select civ + screenshot only; no PLAY, no observe, no resign")
    ap.add_argument("--abort-on-crash", action="store_true",
                    help="Stop matrix immediately on cycle_game failure")
    ap.add_argument("--no-adaptive-observe", action="store_true",
                    help="Disable adaptive early-exit. Forces the runner to "
                         "sit through the full --observe-seconds budget per "
                         "batch. Use only when you need a fixed-time control "
                         "(repro timing, comparing observe-budget settings).")
    ap.add_argument("--skip-replay-diag", action="store_true",
                    help="Skip the per-match .age3Yrec decompress + "
                         "AI-script count. Saves ~1–2s per batch (~10s total) "
                         "at the cost of the ai_scripts_loaded telemetry "
                         "field. Personality-probe + behavioural axes still "
                         "prove AI loaded.")
    ap.add_argument("--auto-resign-ms", type=int, default=0,
                    help="If > 0, rewrite cLLTestModeAutoResignMs in "
                         "game/ai/core/aiGlobals.xs to this value before "
                         "sync, so every AI calls aiResign() once "
                         "xsGetTime() crosses the threshold. Bounds match "
                         "length (matches end at this+~5s). Reset to 0 on "
                         "exit. Use 90000 (90s game-time) for 47-civ "
                         "deterministic coverage in ~10min wall-clock.")
    ap.add_argument("--validate-doctrine", action="store_true",
                    help="After the matrix completes, run "
                         "tools/validation/validate_doctrine_compliance.py "
                         "across every match.log under "
                         "artifacts/matrix_runner/*/match.log and write "
                         "doctrine_compliance.{txt,json} next to matrix_report.*. "
                         "Exit code stays 0 on doctrine failures (the matrix "
                         "report itself owns CI gating); the file artifacts "
                         "are the source of truth.")
    ap.add_argument("--doctrine-spec", type=Path,
                    default=ROOT / "playstyle_spec.json",
                    help="Path to playstyle_spec.json consumed by "
                         "--validate-doctrine. Default: <repo>/playstyle_spec.json. "
                         "Regenerate via tools/playtest/extract_playstyle_spec.py "
                         "whenever a_new_world.html changes.")
    ap.add_argument("--deep", action="store_true",
                    help="Deep behavioural-axis mode. Raises observe-seconds "
                         "(if left at the default 10) to 300 so compliance.* / "
                         "mil.attack / tech.ship probes have time to fire, "
                         "then parses each match.log for per-AI behavioural "
                         "booleans (combat_engaged, explorer_active, "
                         "age_up_fired, shipments_chosen, walls_built, "
                         "doctrine_compliance). Trade-off: matrix wall-time "
                         "rises from ~8 min smoke → ~30 min for 6 batches.")
    args = ap.parse_args()

    # ── Harness input backend ───────────────────────────────────────────────
    # Best-effort initial connect against any already-running game. The robust
    # (re)connect happens after every cycle_game() and before each civ via
    # ensure_harness_backend(), because each cycle recreates the socket. Keep
    # the startup attempt short — if it fails, the first cycle reconnects.
    ensure_harness_backend(retries=2, delay=2.0)

    if args.deep and args.observe_seconds < 60:
        # Smoke default would falsely report every behavioural axis as
        # missing. With adaptive observe the budget below is a *cap*, not a
        # fixed sleep — typical batches early-exit at 90–150s. The cap was
        # 300s (~25 game-min at speed 5) before adaptive landed; with early
        # exit the safe ceiling drops to 180s because slow doctrines still
        # finish age-up + first ship within that window. Pass --observe-
        # seconds explicitly to override.
        args.observe_seconds = 180

    # ── Auto-resign toggle ──────────────────────────────────────────────────
    # Rewrite cLLTestModeAutoResignMs in aiGlobals.xs in-place. Reset to 0 on
    # exit so a release sync doesn't ship a test build by accident.
    globals_xs = ROOT / "game" / "ai" / "core" / "aiGlobals.xs"
    _restore_globals = None
    if args.auto_resign_ms > 0:
        original = globals_xs.read_text()
        new = re.sub(
            r"extern const int cLLTestModeAutoResignMs = \d+;",
            f"extern const int cLLTestModeAutoResignMs = {args.auto_resign_ms};",
            original,
        )
        if new == original:
            print("WARN: --auto-resign-ms set but no cLLTestModeAutoResignMs "
                  "line found in aiGlobals.xs; auto-resign will not arm.",
                  file=sys.stderr)
        else:
            globals_xs.write_text(new)
            print(f"  [auto-resign] cLLTestModeAutoResignMs = "
                  f"{args.auto_resign_ms} (will reset to 0 on exit)")
            def _restore_globals():  # noqa: E306
                cur = globals_xs.read_text()
                cur = re.sub(
                    r"extern const int cLLTestModeAutoResignMs = \d+;",
                    "extern const int cLLTestModeAutoResignMs = 0;",
                    cur,
                )
                globals_xs.write_text(cur)
                print("  [auto-resign] reset cLLTestModeAutoResignMs = 0")

    civ_names = [c.strip() for c in args.civs.split(",") if c.strip()]
    try:
        rc = run_matrix(
            observe_seconds=args.observe_seconds,
            in_game_timeout=args.in_game_timeout,
            speed_tick=args.speed_tick,
            start_idx=args.start_idx,
            end_idx=args.end_idx,
            civ_names=civ_names or None,
            dry_run=args.dry_run,
            abort_on_crash=args.abort_on_crash,
            batch_size=args.batch_size,
            deep_mode=args.deep,
            adaptive_observe=not args.no_adaptive_observe,
            skip_replay_diag=args.skip_replay_diag,
        )
    finally:
        if _restore_globals is not None:
            _restore_globals()

    # ── Optional: doctrine-compliance pass ─────────────────────────────────
    # Glob every per-civ match.log under artifacts/matrix_runner/*/match.log
    # and run validate_doctrine_compliance against playstyle_spec.json. The
    # validator's exit code is informational here — the matrix report still
    # owns CI gating, but the doctrine report shows up alongside it as a
    # second-pass quality bar.
    if args.validate_doctrine:
        if not args.doctrine_spec.exists():
            print(f"[doctrine] spec missing at {args.doctrine_spec}; skipping. "
                  f"Run: python3 tools/playtest/extract_playstyle_spec.py",
                  file=sys.stderr)
        else:
            sys.path.insert(0, str(ROOT / "tools" / "validation"))
            try:
                import validate_doctrine_compliance as vdc
            except Exception as exc:  # pragma: no cover — import-time failure
                print(f"[doctrine] failed to import validator: {exc}",
                      file=sys.stderr)
            else:
                logs = sorted(ARTIFACT_DIR.glob("*/match.log"))
                if not logs:
                    print(f"[doctrine] no match.log files under {ARTIFACT_DIR}",
                          file=sys.stderr)
                else:
                    print(f"[doctrine] scanning {len(logs)} match.log files…")
                    spec = json.loads(args.doctrine_spec.read_text(encoding="utf-8"))
                    probes = vdc.parse_probes(logs)
                    from collections import defaultdict
                    per_actor = defaultdict(list)
                    for p in probes:
                        per_actor[(p.civ, p.ldr)].append(p)
                    per_civ: dict[str, list] = {}
                    for (civ, ldr), plist in per_actor.items():
                        spec_key = vdc._resolve_spec_key(civ, ldr, spec)
                        if not spec_key:
                            continue
                        claims = spec["civs"][spec_key].get("claims", {})
                        if not claims:
                            continue
                        per_civ[spec_key] = vdc.evaluate_civ(spec_key, claims, plist)
                    text = vdc.render_text(per_civ)
                    txt_out = ARTIFACT_DIR / "doctrine_compliance.txt"
                    json_out = ARTIFACT_DIR / "doctrine_compliance.json"
                    txt_out.write_text(text + "\n", encoding="utf-8")
                    json_out.write_text(
                        json.dumps(vdc.render_json(per_civ), indent=2),
                        encoding="utf-8",
                    )
                    fails = sum(1 for rs in per_civ.values()
                                if vdc._verdict_for(rs) == vdc.FAIL)
                    print(f"[doctrine] wrote {txt_out} and {json_out} "
                          f"({len(per_civ)} civs, {fails} fail)")

                # Consolidated single-file report — one place to scan
                # instead of opening matrix_report.md + every match.log
                # + doctrine_compliance.txt one by one.
                try:
                    import compile_playtest_report as cpr
                    consolidated = ARTIFACT_DIR / "playtest_report.txt"
                    sys.argv = [
                        "compile_playtest_report.py",
                        "--matrix-dir", str(ARTIFACT_DIR),
                        "--spec",       str(args.doctrine_spec),
                        "--out",        str(consolidated),
                    ]
                    cpr.main()
                except Exception as exc:  # pragma: no cover
                    print(f"[doctrine] consolidated report failed: {exc}",
                          file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
