#!/usr/bin/env python3
"""Game control orchestration wrapper for AoE3 DE validation.

Consolidates gamescope_detect + lobby_driver + in_game_driver + manage_game
into a single stateful controller for running full match cycles.
"""
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from tools.aoe3_automation.gamescope_detect import detect_aoe3_display, get_gs_env
    from tools.aoe3_automation.in_game_driver import GameDriver
    from tools.aoe3_automation import lobby_driver as lobby
    from tools.aoe3_automation import manage_game
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    logging.error(f"Import error: {e}")

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a single match."""
    civ_token: str
    civ_name: str
    success: bool
    duration_s: float
    log_path: Optional[Path] = None
    screenshot_dir: Optional[Path] = None
    error: Optional[str] = None
    log_lines: int = 0


class GameController:
    """Orchestrates game control for validation runs."""

    def __init__(self, artifact_root: Path):
        """Initialize controller.

        Args:
            artifact_root: Base directory for storing artifacts
        """
        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)

        self.gs_env = get_gs_env()
        self.display, self.gs_socket = detect_aoe3_display()
        self.game_driver = None
        self.coords = None

        logger.info(f"GameController initialized: display={self.display}, socket={self.gs_socket}")

    def take_screenshot(self, path: str) -> bool:
        """Take screenshot using gamescopectl.

        Args:
            path: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # gamescopectl silently drops relative paths; force absolute and
            # ensure the parent directory exists before invoking it.
            abs_path = str(Path(path).resolve())
            Path(abs_path).parent.mkdir(parents=True, exist_ok=True)

            proc = subprocess.run(
                ["gamescopectl", "screenshot", abs_path],
                env=self.gs_env,
                capture_output=True,
                text=True,
                timeout=10
            )

            # Poll for async write completion (up to 5s)
            deadline = time.time() + 5.0
            while time.time() < deadline:
                try:
                    stat = Path(abs_path).stat()
                    if stat.st_size > 1024:  # At least 1KB of data
                        logger.debug(f"Screenshot saved: {abs_path} ({stat.st_size} bytes)")
                        return True
                except FileNotFoundError:
                    pass
                time.sleep(0.2)

            logger.warning(
                f"Screenshot timeout or undersized: {abs_path} "
                f"(rc={proc.returncode}, stderr={proc.stderr[:120]!r})"
            )
            return False

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False

    def ensure_ready(self) -> bool:
        """Ensure game is running and at clean lobby.

        Returns:
            True if ready, False if unrecoverable
        """
        try:
            # Check if game is running
            if not manage_game.game_pids():
                logger.info("Game not running, cycling...")
                manage_game.cmd_cycle()
                time.sleep(10)

            # Load lobby coordinates
            self.coords = lobby.load_coords()

            # Navigate to lobby
            if not self._ensure_lobby():
                logger.error("Failed to reach lobby")
                return False

            logger.info("Game ready at lobby")
            return True

        except Exception as e:
            logger.error(f"ensure_ready failed: {e}")
            return False

    def _ensure_lobby(self, retries: int = 3) -> bool:
        """Navigate to clean lobby state.

        Args:
            retries: Number of retry attempts

        Returns:
            True if at lobby, False otherwise
        """
        for attempt in range(retries):
            try:
                logger.info(f"Lobby navigation attempt {attempt + 1}/{retries}")

                # Check if game is running
                pids = manage_game.game_pids()
                if not pids:
                    logger.warning("Game not running, skipping lobby navigation")
                    return False

                # Take screenshot to verify window is responsive
                test_path = self.artifact_root / f"state_probe_{attempt}.png"
                if not self.take_screenshot(str(test_path)):
                    logger.warning(f"Screenshot failed, retrying...")
                    time.sleep(2)
                    continue

                # 2026-05-07: Menu-ready pixel probe. After cycle/relaunch the
                # AoE3 main menu chrome can take 30-60s to render in addition
                # to the splash and intro movies. Without this wait, click
                # at (130, 482) for Skirmish lands on a backdrop with no
                # active button and Phase 2 burns the full 360s timeout.
                # The Skirmish-row pixel sum is ~131 when menu is ready,
                # ~0 on a backdrop or black frame.
                from PIL import Image
                menu_ready = False
                for menu_wait in range(60):  # up to 120s
                    try:
                        with Image.open(test_path) as im:
                            sk_pixel = sum(im.getpixel((130, 482))[:3])
                        if sk_pixel > 50:
                            if menu_wait > 0:
                                logger.info(f"Menu ready after {menu_wait*2}s")
                            menu_ready = True
                            break
                    except Exception:
                        pass
                    time.sleep(2)
                    self.take_screenshot(str(test_path))
                if not menu_ready:
                    logger.warning("Menu chrome did not render after 120s")

                # Try to navigate to skirmish
                if self.coords:
                    try:
                        lobby.click_skirmish(self.coords)
                        time.sleep(3)
                    except Exception as e:
                        logger.warning(f"Skirmish click failed: {e}")

                return True

            except Exception as e:
                logger.warning(f"Lobby check attempt {attempt + 1} failed: {e}")
                time.sleep(2)

        return False

    def run_match(self, civ_idx: int, observe_secs: int = 60) -> MatchResult:
        """Run a single match for one civ.

        Args:
            civ_idx: Civ picker index
            observe_secs: Seconds to observe match

        Returns:
            MatchResult with artifacts
        """
        start_time = time.time()
        civ_artifact_dir = self.artifact_root / f"civ_{civ_idx}"
        civ_artifact_dir.mkdir(parents=True, exist_ok=True)

        screenshot_dir = civ_artifact_dir / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Starting match for civ index {civ_idx}")

            # Ensure at lobby
            if not self.ensure_ready():
                raise RuntimeError("Failed to reach lobby state")

            # Select civ
            if self.coords:
                logger.info(f"Selecting civ {civ_idx}")
                lobby.set_civ_by_index(self.coords, civ_idx)
                time.sleep(1)

            # Screenshot before play
            self.take_screenshot(str(civ_artifact_dir / "00_civ_selected.png"))

            # Click play
            if self.coords:
                logger.info("Clicking PLAY")
                lobby.click_play(self.coords)

            # Wait for in-game
            logger.info("Waiting for in-game...")
            self.game_driver = GameDriver(art_dir=civ_artifact_dir)
            # 2026-05-07: First match after a fresh game launch needs ~250s
            # (cold mod cache, full asset preload). Subsequent matches in same
            # session are ~120s. Set to 360s = enough for cold start with slack.
            in_game = self.game_driver.wait_for_in_game(timeout=360)

            if not in_game:
                raise RuntimeError("Timeout waiting for match to start")

            logger.info(f"In-game, observing for {observe_secs}s")

            # Observe and take screenshots every 30s
            for i in range(0, observe_secs, 30):
                screenshot_name = f"t{i:04d}.png"
                self.take_screenshot(str(screenshot_dir / screenshot_name))
                if i < observe_secs - 30:
                    time.sleep(30)

            # Screenshot at end
            self.take_screenshot(str(civ_artifact_dir / "02_in_game_final.png"))

            # End match via game cycle. 2026-05-07: cycle() is the bullet-proof
            # path — the resign+abandon-screen flow has variant UIs that drift
            # between builds. cycle ≈25s overhead per match; for 720 matches
            # that's ~5h of cycle time, acceptable for a one-time exhaustive
            # run. Resign-based fast cycling can be re-enabled later once the
            # abandon-screen pixel coords are properly calibrated.
            logger.info("Ending match via cycle (skip resign)")
            self.take_screenshot(str(civ_artifact_dir / "02_in_game_final.png"))
            try:
                # Subprocess call so manage_game's argparse defaults populate.
                cycle_proc = subprocess.run(
                    [sys.executable,
                     str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                     "cycle", "--timeout", "180", "--post-menu-wait", "6"],
                    capture_output=True, text=True, timeout=300
                )
                if cycle_proc.returncode != 0:
                    logger.warning(
                        f"cycle rc={cycle_proc.returncode} "
                        f"stderr={cycle_proc.stderr[-300:]!r}"
                    )
            except Exception as cycle_e:
                logger.warning(f"cycle failed: {cycle_e}")

            # Skip the intro splash + studio movies that play on every launch.
            # Uses xdotool Esc on the gamescope nested display only — the host
            # cursor/keyboard on :0 is untouched.
            try:
                from tools.aoe3_automation.gamescope_detect import detect_aoe3_display
                disp, _ = detect_aoe3_display(use_cache=False)
                xenv = {**os.environ, "DISPLAY": disp}
                wid_proc = subprocess.run(
                    ["xdotool", "search", "--name", "Age of Empires"],
                    env=xenv, capture_output=True, text=True, timeout=5
                )
                if wid_proc.stdout.strip():
                    wid = wid_proc.stdout.strip().splitlines()[0]
                    for _ in range(3):
                        subprocess.run(
                            ["xdotool", "key", "--window", wid, "Escape"],
                            env=xenv, timeout=5
                        )
                        time.sleep(2.0)
            except Exception as skip_e:
                logger.warning(f"intro-skip failed: {skip_e}")

            # Screenshot end state
            self.take_screenshot(str(civ_artifact_dir / "03_end_state.png"))

            duration = time.time() - start_time

            return MatchResult(
                civ_token=f"civ_{civ_idx}",
                civ_name=f"Civ {civ_idx}",
                success=True,
                duration_s=duration,
                screenshot_dir=screenshot_dir,
                log_path=civ_artifact_dir / "match.log"
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Match failed: {e}")

            # 2026-05-07: On match failure, recover via cycle so the NEXT civ
            # starts from a known main-menu state. Without this the engine
            # could be stuck mid-load or in-match, and the next civ's lobby
            # nav would click into the wrong screen.
            try:
                logger.info("Recovering via cycle after failure...")
                subprocess.run(
                    [sys.executable,
                     str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                     "cycle", "--timeout", "180", "--post-menu-wait", "6"],
                    capture_output=True, text=True, timeout=300
                )
                # Skip intro on relaunch
                from tools.aoe3_automation.gamescope_detect import detect_aoe3_display
                disp, _ = detect_aoe3_display(use_cache=False)
                xenv = {**os.environ, "DISPLAY": disp}
                wid_proc = subprocess.run(
                    ["xdotool", "search", "--name", "Age of Empires"],
                    env=xenv, capture_output=True, text=True, timeout=5
                )
                if wid_proc.stdout.strip():
                    wid = wid_proc.stdout.strip().splitlines()[0]
                    for _ in range(3):
                        subprocess.run(
                            ["xdotool", "key", "--window", wid, "Escape"],
                            env=xenv, timeout=5
                        )
                        time.sleep(2.0)
                # Wait for menu chrome to render
                time.sleep(8)
            except Exception as recover_e:
                logger.warning(f"recovery cycle failed: {recover_e}")

            return MatchResult(
                civ_token=f"civ_{civ_idx}",
                civ_name=f"Civ {civ_idx}",
                success=False,
                duration_s=duration,
                error=str(e),
                screenshot_dir=screenshot_dir
            )

    def recover(self) -> bool:
        """Attempt to recover from error state.

        Returns:
            True if recovered, False otherwise
        """
        try:
            logger.info("Attempting recovery...")
            manage_game.cycle()
            time.sleep(15)
            return self.ensure_ready()
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False


def main():
    """Test the game controller."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    artifact_dir = Path("artifacts/game_ctl_test")
    controller = GameController(artifact_dir)

    if controller.ensure_ready():
        logger.info("Game ready, taking screenshot test")
        controller.take_screenshot(str(artifact_dir / "test.png"))
    else:
        logger.error("Failed to ensure game ready")


if __name__ == "__main__":
    main()
