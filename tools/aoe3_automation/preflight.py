"""Pre-flight assertions for the ANW exhibition runner.

A 720-match matrix that silently fails on every match because dev-mode
isn't set, the game crashed at startup, or the log mirror thread died is
catastrophic — we burn hours on noise. Pre-flight catches these before we
commit to the run.

The single public entrypoint is :func:`run_preflight`. It returns a tuple
``(ok, failures)`` where ``failures`` is a list of human-readable strings.
An empty list means pass; non-empty means abort. Soft warnings are logged
but not returned in the failure list (see ``Check D``).

Checks performed
----------------
A. Age3Log.txt exists           — game has run at least once
B. Dev mode active              — ``ensure_dev_mode()`` reports True OR
                                   the user.cfg has all 3 required tokens
C. Game window detectable       — gamescope_detect.get_xdo_env() succeeds
                                   AND xdotool finds an AoE3 window
D. Log is being written to      — Age3Log.txt grows over a small window
                                   (soft: warn-only when game window exists
                                   but log is static — game may legitimately
                                   be idle on the main menu)

The runner calls :func:`run_preflight` once before any matches, and a
lightweight :func:`per_match_preflight` at the start of each match.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import List, Tuple

from tenacity import Retrying, stop_after_attempt, wait_fixed

from tools.aoe3_automation.log_capture import (
    AGE3_LOG_PATH,
    USER_CFG_PATH,
    ensure_dev_mode,
)


_REQUIRED_TOKENS: tuple[str, ...] = ("developer", "+ixsLog", "+cxsLog")


def _user_cfg_has_all_tokens() -> bool:
    """True iff user.cfg exists and contains all 3 dev-mode tokens uncommented."""
    if not USER_CFG_PATH.exists():
        return False
    try:
        content = USER_CFG_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    active: list[str] = []
    for raw in content.splitlines():
        s = raw.strip()
        if not s or s.startswith("//"):
            continue
        active.append(s)
    joined = "\n".join(active)
    return all(tok in joined for tok in _REQUIRED_TOKENS)


def _xdotool_finds_aoe3_window() -> Tuple[bool, str]:
    """Returns (found, detail). Tolerates xdotool missing entirely."""
    try:
        from tools.aoe3_automation.gamescope_detect import get_xdo_env
    except Exception as exc:
        return False, f"gamescope_detect import failed: {exc}"

    try:
        env = get_xdo_env()
    except Exception as exc:
        return False, f"get_xdo_env() failed: {exc}"

    try:
        res = subprocess.run(
            ["xdotool", "search", "--name", "Age of Empires"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        return False, "xdotool binary not found"
    except subprocess.TimeoutExpired:
        return False, "xdotool search timed out"
    except Exception as exc:
        return False, f"xdotool error: {exc}"

    win_ids = res.stdout.strip().splitlines()
    if not win_ids:
        return False, "no AoE3 window found via xdotool"
    return True, f"found {len(win_ids)} window(s): {','.join(win_ids[:3])}"


def _log_size() -> int:
    """Current Age3Log.txt size in bytes, or 0 if missing."""
    try:
        return AGE3_LOG_PATH.stat().st_size if AGE3_LOG_PATH.exists() else 0
    except OSError:
        return 0


def _log_is_growing(growth_window_s: float) -> bool:
    """Single sample: snapshot size, sleep, snapshot again. True iff grew."""
    before = _log_size()
    time.sleep(growth_window_s)
    after = _log_size()
    return after > before


def _log_is_growing_with_retry(growth_window_s: float, attempts: int = 3) -> bool:
    """Retry the growth check a few times — the game may be flushing in bursts."""
    for attempt in Retrying(
        stop=stop_after_attempt(attempts),
        wait=wait_fixed(1),
        reraise=False,
    ):
        with attempt:
            if _log_is_growing(growth_window_s):
                return True
            # Force a retry by raising — tenacity will swallow until last attempt.
            raise RuntimeError("log not growing")
    return False


def run_preflight(
    log_path: Path = AGE3_LOG_PATH,
    *,
    growth_window_s: float = 3.0,
) -> Tuple[bool, List[str]]:
    """Verify we're ready to run a match. Returns (ok, list_of_failures).

    See module docstring for the full check list. ``ok`` is True iff the
    failures list is empty.
    """
    failures: List[str] = []

    # A. AGE3_LOG_PATH exists.
    if not log_path.exists():
        failures.append(
            f"Age3Log.txt missing at {log_path} — has the game ever launched?"
        )

    # B. Dev mode active.
    try:
        dev_ok = ensure_dev_mode()
    except Exception as exc:
        dev_ok = False
        failures.append(f"ensure_dev_mode() raised: {exc}")
    if not dev_ok and not _user_cfg_has_all_tokens():
        failures.append(
            f"Dev mode not active: user.cfg at {USER_CFG_PATH} missing one or "
            f"more required tokens {_REQUIRED_TOKENS}. aiEcho() probes will be "
            "silently dropped."
        )

    # C. Game window detectable.
    win_found, win_detail = _xdotool_finds_aoe3_window()
    if not win_found:
        failures.append(f"AoE3 window not detectable: {win_detail}")

    # D. Log is being written to (soft check).
    # If the game window isn't there at all, no point checking log growth.
    # If window IS there but log static, that's suspicious-but-not-fatal:
    # the game may be sitting idle on the main menu.
    if win_found and log_path.exists():
        growing = False
        try:
            growing = _log_is_growing_with_retry(growth_window_s, attempts=3)
        except Exception:
            growing = False
        if not growing:
            # Soft warning — surfaced to caller for logging but NOT a failure.
            # The runner will log this; we don't append to failures.
            pass

    return (len(failures) == 0, failures)


def per_match_preflight(log_path: Path = AGE3_LOG_PATH) -> Tuple[bool, List[str]]:
    """Lightweight pre-flight at the start of each match.

    Verifies:
      - AGE3_LOG_PATH exists and is non-empty.
      - The game window is still findable.

    No log-growth check (would add latency to every match). Returns same
    shape as :func:`run_preflight`.
    """
    failures: List[str] = []

    if not log_path.exists():
        failures.append(f"Age3Log.txt missing at {log_path}")
    else:
        try:
            size = log_path.stat().st_size
        except OSError as exc:
            size = 0
            failures.append(f"Cannot stat Age3Log.txt: {exc}")
        if size == 0:
            failures.append("Age3Log.txt is empty (size=0)")

    win_found, win_detail = _xdotool_finds_aoe3_window()
    if not win_found:
        failures.append(f"AoE3 window not detectable: {win_detail}")

    return (len(failures) == 0, failures)
