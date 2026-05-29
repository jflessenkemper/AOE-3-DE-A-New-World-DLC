"""ANW Test Harness — umu-run-based, AOE3DEHarness-based probe capture pipeline.

Public API:
    from tools.aoe3_harness.launch import launch_game, kill_stale
    from tools.aoe3_harness.supervisor import run_pass
    from tools.aoe3_harness.validator import validate_pass

AOE3DEHarness socket client (new path):
    from tools.aoe3_harness import HarnessClient, HarnessState, ScreenshotResult
    from tools.aoe3_harness import harness_launch

Legacy DLL client (kept for backwards compatibility until Phase 6 verification):
    from tools.aoe3_harness.dll_client import DllClient
"""

__version__ = "0.2.0"

# ---------------------------------------------------------------------------
# AOE3DEHarness socket client (new path — Phase 5+)
# ---------------------------------------------------------------------------

from tools.aoe3_harness.harness_client import (  # noqa: E402, F401
    HarnessClient,
    HarnessCommandError,
    HarnessConnectionError,
    HarnessError,
    HarnessProtocolError,
    HarnessShuttingDownError,
    HarnessState,
    HarnessTimeoutError,
    ScreenshotResult,
)
from tools.aoe3_harness.harness_launch import harness_launch  # noqa: E402, F401
