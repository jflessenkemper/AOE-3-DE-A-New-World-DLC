"""Centralized path constants for the ANW test harness.

All production-code paths that touch the Steam/Proton installation or the
Wine prefix go through this module.  If Steam moves or the prefix changes,
fix it here — not in a dozen scattered files.

All paths are resolved at import time.  If the host environment is wrong
(e.g. running in CI without a Steam install), importers catch FileNotFoundError
at the point of first use, not at import time — the constants themselves are
always valid Path objects, just potentially pointing at non-existent locations.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Host tool paths
# ---------------------------------------------------------------------------

UMU_RUN: Path = Path("/usr/bin/umu-run")

# ---------------------------------------------------------------------------
# Steam root and Proton
# ---------------------------------------------------------------------------

STEAM_ROOT: Path = Path.home() / ".local/share/Steam"
STEAMAPPS: Path = STEAM_ROOT / "steamapps"
PROTONPATH: Path = STEAMAPPS / "common" / "Proton - Experimental"
SLR_ENTRY: Path = STEAMAPPS / "common" / "SteamLinuxRuntime_4" / "_v2-entry-point"

# ---------------------------------------------------------------------------
# AoE3 DE game installation
# ---------------------------------------------------------------------------

AOE3_EXE: Path = STEAMAPPS / "common" / "AoE3DE" / "AoE3DE_s.exe"

# ---------------------------------------------------------------------------
# Wine prefix (Proton compatdata)
# ---------------------------------------------------------------------------

APPID: str = "933110"
WINEPREFIX: Path = STEAMAPPS / "compatdata" / APPID / "pfx"

# Convenience: path inside the prefix to the "steamuser" home
_STEAM_USER_HOME: Path = (
    WINEPREFIX / "drive_c" / "users" / "steamuser"
)

# ---------------------------------------------------------------------------
# User game data (inside prefix)
# ---------------------------------------------------------------------------

_GAME_PROFILE_ID: str = "76561198170207043"
_AOE3_GAME_DATA: Path = (
    _STEAM_USER_HOME
    / "Games"
    / "Age of Empires 3 DE"
    / _GAME_PROFILE_ID
)

USER_CFG_PATH: Path = _AOE3_GAME_DATA / "Startup" / "user.cfg"
USER_PROFILE_XML: Path = _AOE3_GAME_DATA / "Player" / "UserProfile.xml"
SCENARIO_DIR: Path = _AOE3_GAME_DATA / "Scenario"

# ---------------------------------------------------------------------------
# Log paths (flat Logs/ directory — NOT under the profile ID subdirectory)
# ---------------------------------------------------------------------------

_AOE3_LOGS: Path = (
    _STEAM_USER_HOME
    / "Games"
    / "Age of Empires 3 DE"
    / "Logs"
)

AGE3_LOG_PATH: Path = _AOE3_LOGS / "Age3Log.txt"
AI_OUTPUT_DIR: Path = _AOE3_LOGS   # Age3DEAIOutputPlayer<N>.txt live here
AI_OUTPUT_GLOB: str = "Age3DEAIOutputPlayer*.txt"

# ---------------------------------------------------------------------------
# Alternate search locations for per-AI output (Risk 1 mitigation)
# The engine may write to any of these; auto-discovery searches all three.
# ---------------------------------------------------------------------------

AI_OUTPUT_SEARCH_DIRS: list[Path] = [
    _AOE3_LOGS,                                        # most likely (Logs/)
    _AOE3_GAME_DATA / "Startup",                       # Startup/
    _AOE3_GAME_DATA / "Game" / "AI",                   # Game/AI/
]

# ---------------------------------------------------------------------------
# Repo-relative paths
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
HARNESS_DIR: Path = Path(__file__).resolve().parent
ARTIFACT_ROOT: Path = REPO_ROOT / "artifacts" / "validation" / "ai_playstyle"
VISUAL_ART_ROOT: Path = REPO_ROOT / "artifacts" / "validation" / "visual_art"
MOD_DEPLOY_SCRIPT: Path = REPO_ROOT / "tools" / "deploy_to_mod.py"
VALIDATOR_SCRIPT: Path = REPO_ROOT / "tools" / "validation" / "validate_doctrine_compliance.py"
XS_VALIDATOR_SCRIPT: Path = REPO_ROOT / "tools" / "validation" / "validate_xs_scripts.py"
RELEASE_SITE_SCRIPT: Path = (
    REPO_ROOT / "tools" / "validation" / "build_release_readiness_site.py"
)
STATE_PATH: Path = HARNESS_DIR / "state.json"
