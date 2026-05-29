"""ANW Test Harness — umu-run-based, gamescope-free probe capture pipeline.

Public API:
    from tools.aoe3_harness.launch import launch_game, kill_stale
    from tools.aoe3_harness.supervisor import run_pass
    from tools.aoe3_harness.validator import validate_pass

Gamescope-anw socket client (new path):
    from tools.aoe3_harness import GamescopeClient, GamescopeState, ScreenshotResult
    from tools.aoe3_harness import gs_launch

Legacy DLL client (kept for backwards compatibility until Phase 6 verification):
    from tools.aoe3_harness.dll_client import DllClient
"""

__version__ = "0.2.0"

# ---------------------------------------------------------------------------
# Gamescope-anw socket client (new path — Phase 5+)
# ---------------------------------------------------------------------------

from tools.aoe3_harness.gamescope_client import (  # noqa: E402, F401
    GamescopeClient,
    GamescopeCommandError,
    GamescopeConnectionError,
    GamescopeError,
    GamescopeProtocolError,
    GamescopeShuttingDownError,
    GamescopeState,
    GamescopeTimeoutError,
    ScreenshotResult,
)
from tools.aoe3_harness.gs_launch import gs_launch  # noqa: E402, F401
