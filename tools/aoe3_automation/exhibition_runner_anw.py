#!/usr/bin/env python3
"""Comprehensive exhibition runner for ANW — validates all 48 civs.

Runs the full 48-civ matrix with property validation:
  1. Load reference_matrix.json as source of truth
  2. For each ANW civ:
     - Launch match
     - Capture log + screenshots
     - Extract [ANWP v=2] probes
     - Run PropertyValidatorSuite
     - Compare against reference specs
  3. Generate behavioral_compliance_report.json

Usage:
    python3 exhibition_runner_anw.py --all
    python3 exhibition_runner_anw.py --civs ANWBritish ANWFrench ANWChinese
    python3 exhibition_runner_anw.py --sample  # 5 civs for quick validation
    python3 exhibition_runner_anw.py --resume <artifact_dir>

Reliability features (added 2026-05):
  * Pre-flight assertions before the matrix runs (preflight.py).
  * Per-match preflight skips dead matches without burning the 60s timeout.
  * match.log persisted on every code path (success / timeout / exception).
  * Failure screenshots dropped on every failure path.
  * Log-mirror sanity check after start_log_tail.
  * Event-driven observation window with --min-probe-count early exit.
  * Single-match smoke test runs first by default (skip with --skip-smoke).
  * structlog JSON sink at <artifact_root>/runner.log.jsonl for jq post-mortem.
  * tenacity retries around lobby.set_civ_by_index / lobby.click_play.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional, List, Dict, Tuple

import structlog
from tenacity import (
    RetryError,
    Retrying,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Repo setup (match matrix_runner.py pattern)
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from tools.migration.anw_token_map import ANW_CIVS
from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX

# structlog is configured in main(); use a module-level logger as a placeholder
# so import-time `logger.warning` calls work even before main() runs.
logger = structlog.get_logger(__name__)

# Try to import game drivers
try:
    import lobby_driver as lobby
    from tools.aoe3_automation.in_game_driver import GameDriver
    from tools.aoe3_automation.log_capture import (
        AGE3_LOG_PATH,
        start_log_tail,
        stop_log_tail,
    )
    from tools.aoe3_automation.preflight import per_match_preflight, run_preflight
    GAME_HARNESS_AVAILABLE = True
except ImportError as e:
    logger.warning("game_harness_unavailable", error=str(e))
    GAME_HARNESS_AVAILABLE = False

# Import validators
try:
    from tools.validation.property_validators_v1 import PropertyValidatorSuite
    VALIDATORS_AVAILABLE = True
except ImportError as e:
    logger.warning("validators_unavailable", error=str(e))
    VALIDATORS_AVAILABLE = False

# Import visual validators (Phase 3)
try:
    from tools.validation.team_color_detector import TeamColorDetector
    from tools.validation.layout_analyzer import LayoutAnalyzer
    VISUAL_VALIDATORS_AVAILABLE = True
except ImportError as e:
    logger.warning("visual_validators_unavailable", error=str(e))
    VISUAL_VALIDATORS_AVAILABLE = False


# ---------------------------------------------------------------------------
# structlog configuration
# ---------------------------------------------------------------------------
_JSONL_FILE_HANDLE: Optional[Any] = None  # closed in main()'s finally


def _configure_structlog(artifact_root: Path) -> Path:
    """Configure structlog with a console renderer + JSONL file sink.

    Stdout: human-readable lines (preserves the user's tail-watching habit).
    File:   one JSON object per line at <artifact_root>/runner.log.jsonl, for
            post-mortem analysis with jq.

    Returns the path to the JSONL file.
    """
    global _JSONL_FILE_HANDLE

    artifact_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = artifact_root / "runner.log.jsonl"

    # Open in append mode so resumed runs accumulate.
    _JSONL_FILE_HANDLE = jsonl_path.open("a", buffering=1, encoding="utf-8")

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Stdout console renderer (plain text, ANSI off — easy to tail).
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=False),
            foreign_pre_chain=[timestamper, structlog.stdlib.add_log_level],
        )
    )

    # JSONL file handler.
    jsonl_handler = logging.StreamHandler(stream=_JSONL_FILE_HANDLE)
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

    return jsonl_path


@dataclass
class CivMatch:
    """Result of a single civ match."""
    civ_token: str
    civ_name: str
    start_time: float
    end_time: float
    duration_s: float
    status: str  # "completed", "crashed", "timeout", "error", "preflight-error"
    artifact_dir: str
    log_lines: int = 0
    error_message: Optional[str] = None
    validation_results: Dict = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    # Reliability-refactor additions:
    preflight_failures: List[str] = field(default_factory=list)
    match_started: bool = False  # True iff wait_for_in_game returned True
    probe_count: int = 0          # final log_mirror.current_probe_count()
    mirror_bytes: int = 0         # final len(log_mirror.current_content())


class _LobbyOpsError(RuntimeError):
    """Raised when a lobby driver call fails repeatedly. Triggers tenacity retry."""


class ExhibitionRunnerANW:
    """Orchestrates all-civ exhibition matches with property validation."""

    def __init__(self, artifact_root: Optional[Path] = None):
        """Initialize runner."""
        if artifact_root is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            artifact_root = Path(f"artifacts/anw_exhibition_{timestamp}")

        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)

        # Load reference matrix
        try:
            ref_path = Path("reference_matrix.json")
            self.reference = json.loads(ref_path.read_text())
            logger.info(
                "reference_matrix_loaded",
                total_civs=self.reference['total_civs'],
            )
        except FileNotFoundError:
            logger.error("reference_matrix_missing")
            self.reference = None

        # Initialize validators
        self.validators = PropertyValidatorSuite() if VALIDATORS_AVAILABLE else None

        self.results: List[CivMatch] = []
        self.checkpoint_path = self.artifact_root / "checkpoint.json"

        # Tunables (set by main() from CLI flags).
        self.min_probe_count: int = 20
        self.full_observe: bool = False
        # ANW with 8 AIs: mode-27 marker fires ~150s after PLAY click. The
        # original 60s default was the root cause of every match in
        # artifacts/anw_exhibition_20260507_154740 timing out blind. 240s
        # gives ~90s of margin while still failing fast on a truly dead match.
        self.wait_for_in_game_timeout: int = 240

    # ---- preflight -------------------------------------------------------

    def _run_matrix_preflight(self) -> bool:
        """Run the full preflight; abort the matrix on hard failure.

        Returns True if it's safe to proceed, False if the matrix should abort.
        """
        if not GAME_HARNESS_AVAILABLE:
            logger.error("preflight_skipped_no_harness")
            return False

        logger.info("preflight_starting")
        ok, failures = run_preflight(AGE3_LOG_PATH, growth_window_s=3.0)
        if ok:
            logger.info("preflight_passed")
            return True
        logger.error("preflight_failed", failures=failures)
        return False

    def smoke_test(self, observe_seconds: int = 60) -> Tuple[bool, str]:
        """Run a single match against the first civ in ANW_TO_PICKER_INDEX.

        Returns (ok, reason). Used as a guardrail before the full matrix:
        if even one match can't complete, running 720 is pointless.
        """
        if not ANW_TO_PICKER_INDEX:
            return False, "ANW_TO_PICKER_INDEX is empty"

        # Pick the first civ deterministically (sorted by token).
        civ_token = sorted(ANW_TO_PICKER_INDEX.keys())[0]
        picker_index = ANW_TO_PICKER_INDEX[civ_token]
        civ_data = ANW_CIVS.get(civ_token, {})
        civ_name = civ_data.get("display", civ_token)

        log = logger.bind(civ=civ_token, picker_index=picker_index, smoke=True)
        log.info("smoke_test_start")

        result = self._run_single_match(
            civ_token, civ_name, picker_index, observe_seconds
        )
        # Don't pollute the main results list with the smoke run.
        if result.status == "completed":
            log.info(
                "smoke_test_passed",
                duration_s=result.duration_s,
                probe_count=result.probe_count,
                log_lines=result.log_lines,
            )
            return True, "smoke passed"
        log.error(
            "smoke_test_failed",
            status=result.status,
            error=result.error_message,
            preflight_failures=result.preflight_failures,
        )
        return False, f"smoke failed: status={result.status} err={result.error_message}"

    # ---- main run loops --------------------------------------------------

    def _ensure_ready(self, *, skip_smoke: bool, observe_seconds: int) -> bool:
        """Run preflight + (optional) smoke before any matrix run."""
        if not self._run_matrix_preflight():
            return False
        if skip_smoke:
            logger.warning("smoke_test_skipped_by_flag")
            return True
        ok, reason = self.smoke_test(observe_seconds=observe_seconds)
        if not ok:
            logger.error("smoke_failed_aborting", reason=reason)
            return False
        return True

    def run_all_civs(
        self,
        observe_seconds: int = 60,
        *,
        skip_smoke: bool = False,
    ) -> List[CivMatch]:
        """Run all 48 civs through matches."""
        if not self._ensure_ready(skip_smoke=skip_smoke, observe_seconds=observe_seconds):
            logger.error("run_all_civs_aborted_preflight")
            return self.results

        civs = sorted(ANW_CIVS.items())
        total = len(civs)

        logger.info(
            "run_all_civs_start",
            total=total,
            observe_seconds=observe_seconds,
            artifact_root=str(self.artifact_root),
        )

        for idx, (civ_token, civ_data) in enumerate(civs, 1):
            progress = (idx / total) * 100
            logger.info("civ_match_starting", civ=civ_token, idx=idx, total=total,
                        progress_pct=round(progress, 1))

            civ_name = civ_data.get("display", civ_token)
            picker_index = ANW_TO_PICKER_INDEX.get(civ_token)

            if picker_index is None:
                logger.warning("civ_no_picker_index", civ=civ_token)
                continue

            result = self._run_single_match(
                civ_token, civ_name, picker_index, observe_seconds
            )
            self.results.append(result)
            self._save_checkpoint()
            time.sleep(2)

        return self.results

    def run_sample(
        self,
        sample_size: int = 5,
        observe_seconds: int = 60,
        *,
        skip_smoke: bool = False,
    ) -> List[CivMatch]:
        """Run a small sample for quick validation."""
        if not self._ensure_ready(skip_smoke=skip_smoke, observe_seconds=observe_seconds):
            logger.error("run_sample_aborted_preflight")
            return self.results

        civs = list(ANW_CIVS.items())[:sample_size]
        logger.info("run_sample_start", count=len(civs), sample_size=sample_size)

        for idx, (civ_token, civ_data) in enumerate(civs, 1):
            progress = (idx / len(civs)) * 100
            logger.info("civ_match_starting", civ=civ_token, idx=idx,
                        total=len(civs), progress_pct=round(progress, 1))

            civ_name = civ_data.get("display", civ_token)
            picker_index = ANW_TO_PICKER_INDEX.get(civ_token)

            if picker_index is None:
                logger.warning("civ_no_picker_index", civ=civ_token)
                continue

            result = self._run_single_match(
                civ_token, civ_name, picker_index, observe_seconds
            )
            self.results.append(result)
            self._save_checkpoint()
            time.sleep(2)

        return self.results

    def run_specific_civs(
        self,
        tokens: List[str],
        observe_seconds: int = 60,
        *,
        skip_smoke: bool = False,
    ) -> List[CivMatch]:
        """Run specific civs."""
        if not self._ensure_ready(skip_smoke=skip_smoke, observe_seconds=observe_seconds):
            logger.error("run_specific_civs_aborted_preflight")
            return self.results

        civs = [(t, ANW_CIVS[t]) for t in tokens if t in ANW_CIVS]
        logger.info("run_specific_civs_start", count=len(civs), tokens=tokens)

        for idx, (civ_token, civ_data) in enumerate(civs, 1):
            progress = (idx / len(civs)) * 100
            logger.info("civ_match_starting", civ=civ_token, idx=idx,
                        total=len(civs), progress_pct=round(progress, 1))

            civ_name = civ_data.get("display", civ_token)
            picker_index = ANW_TO_PICKER_INDEX.get(civ_token)

            if picker_index is None:
                logger.warning("civ_no_picker_index", civ=civ_token)
                continue

            result = self._run_single_match(
                civ_token, civ_name, picker_index, observe_seconds
            )
            self.results.append(result)
            self._save_checkpoint()
            time.sleep(2)

        return self.results

    # ---- single match (the meat) -----------------------------------------

    def _safe_screenshot(self, log: Any, path: Path, label: str,
                         result: CivMatch) -> None:
        """Take a screenshot; on failure log + append to error_message.

        Never raises. Used on every screenshot path so a screenshot failure
        is visible in the report instead of silently swallowed.
        """
        try:
            lobby.screenshot(path)
        except Exception as exc:
            log.warning("screenshot_failed", step=label, error=str(exc))
            result.error_message = (result.error_message or "") + \
                f" | screenshot[{label}]: {exc}"

    def _set_civ_with_retry(self, log: Any, coords: dict, picker_index: int,
                            match_dir: Path) -> None:
        """Wrap lobby.set_civ_by_index in tenacity retry. Raises on final fail."""
        attempt_no = {"n": 0}

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
            reraise=True,
        )
        def _go() -> None:
            attempt_no["n"] += 1
            n = attempt_no["n"]
            if n > 1:
                # Re-screenshot pre-retry so we can see what state the lobby
                # was in when we retried.
                try:
                    lobby.screenshot(match_dir / f"01a_civ_retry{n}.png")
                except Exception as exc:
                    log.warning("retry_screenshot_failed", step="set_civ",
                                attempt=n, error=str(exc))
            try:
                lobby.set_civ_by_index(coords, picker_index)
            except Exception as exc:
                log.warning("set_civ_attempt_failed", attempt=n, error=str(exc))
                raise

        _go()

    def _click_play_with_retry(self, log: Any, coords: dict,
                               match_dir: Path) -> None:
        """Wrap lobby.click_play in tenacity retry. Raises on final fail."""
        attempt_no = {"n": 0}

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
            reraise=True,
        )
        def _go() -> None:
            attempt_no["n"] += 1
            n = attempt_no["n"]
            if n > 1:
                try:
                    lobby.screenshot(match_dir / f"01b_play_retry{n}.png")
                except Exception as exc:
                    log.warning("retry_screenshot_failed", step="click_play",
                                attempt=n, error=str(exc))
            try:
                lobby.click_play(coords)
            except Exception as exc:
                log.warning("click_play_attempt_failed", attempt=n, error=str(exc))
                raise

        _go()

    def _observe_with_early_exit(
        self,
        log: Any,
        log_mirror: Any,
        observe_seconds: int,
    ) -> None:
        """Sleep observe_seconds, but exit early when probe count crosses
        ``self.min_probe_count`` AND we've used at least half the window.

        With ``self.full_observe`` set, behaves like ``time.sleep(observe_seconds)``.
        """
        if self.full_observe:
            log.info("observe_full", observe_seconds=observe_seconds)
            time.sleep(observe_seconds)
            log.info("observe_complete", probe_count=log_mirror.current_probe_count())
            return

        threshold = self.min_probe_count
        half = observe_seconds * 0.5
        deadline = time.time() + observe_seconds
        next_tick = time.time()
        last_count = -1
        log.info("observe_start", observe_seconds=observe_seconds,
                 min_probe_count=threshold)

        while time.time() < deadline:
            now = time.time()
            if now >= next_tick:
                count = log_mirror.current_probe_count()
                if count != last_count:
                    log.info("observe_tick", probe_count=count,
                             elapsed_s=round(now - (deadline - observe_seconds), 1))
                    last_count = count
                elapsed = now - (deadline - observe_seconds)
                if count >= threshold and elapsed >= half:
                    log.info("observe_early_exit", probe_count=count,
                             elapsed_s=round(elapsed, 1))
                    return
                next_tick = now + 5.0
            # Short sleep so we stay responsive.
            time.sleep(0.5)

        log.info("observe_complete", probe_count=log_mirror.current_probe_count())

    def _run_single_match(
        self,
        civ_token: str,
        civ_name: str,
        picker_index: int,
        observe_seconds: int,
    ) -> CivMatch:
        """Run one match for a civ.

        Reliability invariants:
          * If ``log_mirror`` is started, ``match.log`` IS persisted (in finally).
          * Every failure path drops ``99_failure.png`` if at all possible.
          * Per-match preflight skips matches when game/log are missing —
            cheaper than burning the 60s wait_for_in_game timeout.
        """
        log = logger.bind(civ=civ_token, picker_index=picker_index)

        match_dir = self.artifact_root / civ_token
        match_dir.mkdir(parents=True, exist_ok=True)
        log_path = match_dir / "match.log"

        result = CivMatch(
            civ_token=civ_token,
            civ_name=civ_name,
            start_time=time.time(),
            end_time=time.time(),
            duration_s=0.0,
            status="error",
            artifact_dir=str(match_dir),
        )

        if not GAME_HARNESS_AVAILABLE:
            result.error_message = "Game harness not available"
            result.end_time = time.time()
            result.duration_s = result.end_time - result.start_time
            return result

        # ---- per-match preflight ----------------------------------------
        ok, pf_failures = per_match_preflight(AGE3_LOG_PATH)
        result.preflight_failures = pf_failures
        if not ok:
            result.status = "preflight-error"
            result.error_message = "preflight: " + " | ".join(pf_failures)
            result.end_time = time.time()
            result.duration_s = result.end_time - result.start_time
            log.error("per_match_preflight_failed", failures=pf_failures)
            return result

        log_mirror = None
        try:
            # Load lobby coordinates
            log.info("loading_lobby_coords")
            coords = lobby.load_coords()

            # 1. Ensure clean lobby
            log.info("lobby_initial_screenshot")
            self._safe_screenshot(log, match_dir / "00_lobby_start.png",
                                  "00_lobby_start", result)

            # 2. Select civ (with retry)
            log.info("selecting_civ")
            try:
                self._set_civ_with_retry(log, coords, picker_index, match_dir)
            except Exception as exc:
                # Hard failure: fall through to except handler below.
                raise
            time.sleep(1)
            self._safe_screenshot(log, match_dir / "01_civ_selected.png",
                                  "01_civ_selected", result)

            # 3. Start log capture
            log.info("starting_log_tail")
            log_mirror = start_log_tail(log_path)

            # Sanity check the mirror.
            time.sleep(0.5)
            mirror_initial = len(log_mirror.current_content())
            age3_initial = AGE3_LOG_PATH.stat().st_size if AGE3_LOG_PATH.exists() else 0
            time.sleep(2.0)
            mirror_after = len(log_mirror.current_content())
            age3_after = AGE3_LOG_PATH.stat().st_size if AGE3_LOG_PATH.exists() else 0

            if mirror_initial == 0 and mirror_after == 0:
                if age3_after == age3_initial:
                    # Both static. Likely game idle on menu — soft warn.
                    log.warning(
                        "log_mirror_static_but_age3_also_static",
                        note="game may be idle on main menu, or mirror thread dead",
                        mirror_bytes=mirror_after,
                        age3_bytes=age3_after,
                    )
                else:
                    # Age3 is growing but mirror is not — mirror thread dead.
                    log.error(
                        "log_mirror_thread_dead",
                        age3_growth=age3_after - age3_initial,
                    )
                    result.status = "preflight-error"
                    result.error_message = (
                        f"log mirror not capturing ({mirror_after} bytes) "
                        f"but Age3Log.txt grew by {age3_after - age3_initial} bytes"
                    )
                    raise RuntimeError(result.error_message)
            else:
                log.info(
                    "log_mirror_sanity_ok",
                    mirror_initial=mirror_initial,
                    mirror_after=mirror_after,
                )

            # 4. Click PLAY (with retry)
            log.info("clicking_play")
            try:
                self._click_play_with_retry(log, coords, match_dir)
            except Exception:
                raise

            # 5. Wait for in-game
            log.info("waiting_for_in_game", timeout_s=self.wait_for_in_game_timeout)
            driver = GameDriver(art_dir=match_dir)
            in_game = driver.wait_for_in_game(
                timeout=self.wait_for_in_game_timeout, log_mirror=log_mirror,
            )
            result.match_started = bool(in_game)

            if not in_game:
                # Drop a failure screenshot BEFORE raising so we have forensics.
                self._safe_screenshot(
                    log, match_dir / "99_failure.png",
                    "99_failure_wait_for_in_game", result,
                )
                raise RuntimeError("Timeout waiting for match to start")

            log.info("match_started_observing", observe_seconds=observe_seconds)
            self._observe_with_early_exit(log, log_mirror, observe_seconds)

            # 6. Capture in-game state
            #    _screenshot_raw is a module-level helper, not a GameDriver
            #    method. Call it directly. (2026-05-10: prior code called
            #    driver._screenshot_raw and silently ate the AttributeError.)
            log.info("capturing_in_game_screenshot")
            try:
                from tools.aoe3_automation.in_game_driver import _screenshot_raw
                _screenshot_raw(match_dir / "02_in_game.png")
            except Exception as exc:
                log.warning("in_game_screenshot_failed", error=str(exc))
                result.error_message = (result.error_message or "") + \
                    f" | screenshot[02_in_game]: {exc}"

            # 7. Resign
            log.info("resigning")
            try:
                driver.resign()
                time.sleep(2)
            except Exception as exc:
                log.warning("resign_failed", error=str(exc))
                result.error_message = (result.error_message or "") + \
                    f" | resign: {exc}"

            # 8. Capture end state
            self._safe_screenshot(log, match_dir / "03_end_state.png",
                                  "03_end_state", result)

            result.status = "completed"

        except Exception as e:
            result.status = "error" if result.status == "error" else result.status
            if result.status == "error":
                # Don't overwrite preflight-error.
                result.status = "error"
            # Append to error_message rather than overwrite (chains screenshot
            # failures + the primary fault).
            primary = str(e)
            if result.error_message:
                result.error_message = primary + " | " + result.error_message
            else:
                result.error_message = primary

            # Drop a failure screenshot if we haven't already.
            failure_shot = match_dir / "99_failure.png"
            if not failure_shot.exists():
                self._safe_screenshot(log, failure_shot,
                                      "99_failure_exception", result)

            log.error("match_failed", error=primary, status=result.status)

        finally:
            # Always persist match.log + close out the mirror.
            if log_mirror is not None:
                try:
                    final_text = stop_log_tail(log_mirror)
                except Exception as exc:
                    log.warning("stop_log_tail_failed", error=str(exc))
                    final_text = log_mirror.current_content()
                # Ensure match.log is written even if stop_log_tail returned ""
                # (e.g. mirror dest was truncated mid-way).
                try:
                    if final_text:
                        # log_mirror.dest IS log_path; stop_log_tail already
                        # wrote it. Only re-write if file is missing/empty.
                        if not log_path.exists() or log_path.stat().st_size == 0:
                            log_path.write_text(final_text, encoding="utf-8",
                                                errors="replace")
                except Exception as exc:
                    log.warning("match_log_write_failed", error=str(exc))

                try:
                    result.probe_count = log_mirror.current_probe_count()
                    result.mirror_bytes = len(log_mirror.current_content())
                except Exception:
                    pass

            # Compute log_lines from the file we (hopefully) just persisted.
            try:
                log_content = log_path.read_text() if log_path.exists() else ""
                result.log_lines = len(log_content.splitlines())
            except Exception as exc:
                log.warning("log_read_failed", error=str(exc))
                log_content = ""

            # Run validators on the success path only — on failure, content
            # is unreliable.
            if result.status == "completed" and self.validators:
                try:
                    log.info("running_validators")
                    validation_results = self.validators.validate(log_content, {})
                    passed, summary = self.validators.summarize(validation_results)
                    log.info("validation_done", passed=passed)
                    for name, (ok_v, msg) in validation_results.items():
                        log.info("validator_result", name=name, ok=ok_v, msg=msg)
                    result.validation_results = validation_results
                except Exception as exc:
                    log.warning("validators_failed", error=str(exc))
                    result.error_message = (result.error_message or "") + \
                        f" | validators: {exc}"

            # Collect screenshots.
            try:
                result.screenshots = sorted([str(f) for f in match_dir.glob("*.png")])
            except Exception:
                pass

            result.end_time = time.time()
            result.duration_s = result.end_time - result.start_time

            log.info(
                "match_complete",
                status=result.status,
                duration_s=round(result.duration_s, 1),
                log_lines=result.log_lines,
                probe_count=result.probe_count,
                mirror_bytes=result.mirror_bytes,
                match_started=result.match_started,
            )

        return result

    # ---- reporting -------------------------------------------------------

    def _save_checkpoint(self):
        """Save intermediate results."""
        checkpoint_data = {
            "timestamp": time.time(),
            "completed": len(self.results),
            "results": [asdict(r) for r in self.results],
        }
        with open(self.checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

    def generate_report(self) -> Dict:
        """Generate final compliance report."""
        total = len(self.results)
        completed = sum(1 for r in self.results if r.status == "completed")
        errors = sum(1 for r in self.results if r.status != "completed")

        # Reliability counters — surface patterns at a glance.
        match_started_count = sum(1 for r in self.results if r.match_started)
        zero_probe_count = sum(1 for r in self.results if r.probe_count == 0)
        preflight_errors = sum(
            1 for r in self.results if r.status == "preflight-error"
        )

        # Count validator pass/fail
        validator_pass = 0
        validator_warn = 0
        for result in self.results:
            for name, (passed, msg) in result.validation_results.items():
                if passed:
                    validator_pass += 1
                else:
                    validator_warn += 1

        report = {
            "timestamp": time.time(),
            "summary": {
                "total_matches": total,
                "completed": completed,
                "errors": errors,
                "preflight_errors": preflight_errors,
                "match_started_count": match_started_count,
                "zero_probe_count": zero_probe_count,
                "success_rate_pct": (completed / total * 100) if total > 0 else 0,
            },
            "validation_summary": {
                "validators_passed": validator_pass,
                "validators_warned": validator_warn,
                "pass_rate_pct": (validator_pass / (validator_pass + validator_warn) * 100) if (validator_pass + validator_warn) > 0 else 0,
            },
            "results": [asdict(r) for r in self.results],
            "artifact_root": str(self.artifact_root),
        }

        return report

    def save_report(self, report: Dict):
        """Save report to file."""
        report_path = self.artifact_root / "compliance_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(
            "report_saved",
            path=str(report_path),
            completed=report['summary']['completed'],
            total=report['summary']['total_matches'],
            success_rate_pct=round(report['summary']['success_rate_pct'], 1),
            validator_pass_rate_pct=round(
                report['validation_summary']['pass_rate_pct'], 1
            ),
            preflight_errors=report['summary']['preflight_errors'],
            match_started_count=report['summary']['match_started_count'],
            zero_probe_count=report['summary']['zero_probe_count'],
        )

        return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Exhibition runner for ANW — validates all civs"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all 48 civs (default)"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run first 5 civs for quick validation"
    )
    parser.add_argument(
        "--civs",
        nargs="*",
        default=None,
        help="Run specific civs (e.g., --civs ANWBritish ANWFrench)"
    )
    parser.add_argument(
        "--observe-seconds",
        type=int,
        default=60,
        help="Observation duration per match (default: 60)"
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Custom artifact directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without launching games"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run only the single-match smoke test and exit"
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip the smoke test before the matrix (NOT recommended)"
    )
    parser.add_argument(
        "--min-probe-count",
        type=int,
        default=20,
        help="Early-exit threshold for observation window (default: 20)"
    )
    parser.add_argument(
        "--full-observe",
        action="store_true",
        help="Disable early exit; always sleep --observe-seconds (baseline runs)"
    )
    parser.add_argument(
        "--wait-for-in-game-timeout",
        type=int,
        default=240,
        help=(
            "Seconds to wait for the loading screen to clear before declaring"
            " the match dead. ANW with 8 AIs reliably emits the mode-27 marker"
            " ~150s after PLAY click; 60s is too tight (default: 240)."
        ),
    )

    args = parser.parse_args()

    # Resolve artifact root early so structlog can drop the JSONL sink there.
    if args.artifact_dir is not None:
        artifact_root = Path(args.artifact_dir)
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        artifact_root = Path(f"artifacts/anw_exhibition_{timestamp}")
    artifact_root.mkdir(parents=True, exist_ok=True)

    jsonl_path = _configure_structlog(artifact_root)

    logger.info("=" * 70)
    logger.info("anw_exhibition_runner_start")
    logger.info("=" * 70)
    logger.info(
        "harness_status",
        game_harness_available=GAME_HARNESS_AVAILABLE,
        validators_available=VALIDATORS_AVAILABLE,
        jsonl_log=str(jsonl_path),
    )

    runner = ExhibitionRunnerANW(artifact_root=artifact_root)
    runner.min_probe_count = args.min_probe_count
    runner.full_observe = args.full_observe
    runner.wait_for_in_game_timeout = args.wait_for_in_game_timeout

    try:
        if args.dry_run:
            logger.info("dry_run_no_matches")
            return 0

        if args.smoke:
            ok = runner._run_matrix_preflight()
            if not ok:
                logger.error("smoke_aborted_preflight")
                return 2
            ok, reason = runner.smoke_test(observe_seconds=args.observe_seconds)
            logger.info("smoke_done", ok=ok, reason=reason)
            return 0 if ok else 1

        # Determine which civs to run
        if args.civs is not None and len(args.civs) > 0:
            logger.info("running_specific_civs", count=len(args.civs), civs=args.civs)
            results = runner.run_specific_civs(
                args.civs, args.observe_seconds, skip_smoke=args.skip_smoke,
            )
        elif args.sample:
            logger.info("running_sample", count=5)
            results = runner.run_sample(
                observe_seconds=args.observe_seconds, skip_smoke=args.skip_smoke,
            )
        else:
            logger.info("running_all_civs", count=48)
            results = runner.run_all_civs(
                args.observe_seconds, skip_smoke=args.skip_smoke,
            )

        # If preflight aborted, results will be empty.
        if not results:
            logger.error("matrix_aborted_no_results")
            return 2

        # Generate and save report
        report = runner.generate_report()
        runner.save_report(report)

        return 0 if report['summary']['errors'] == 0 else 1
    finally:
        # Flush + close the JSONL sink so the file is complete on exit.
        global _JSONL_FILE_HANDLE
        if _JSONL_FILE_HANDLE is not None:
            try:
                _JSONL_FILE_HANDLE.flush()
                _JSONL_FILE_HANDLE.close()
            except Exception:
                pass
            _JSONL_FILE_HANDLE = None


if __name__ == "__main__":
    sys.exit(main())
