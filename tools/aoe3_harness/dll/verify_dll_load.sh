#!/usr/bin/env bash
# verify_dll_load.sh — Load-verification script for hello_anw.dll
#
# Usage: bash tools/aoe3_harness/dll/verify_dll_load.sh
#
# This script:
#   1. Checks AoE3 is not already running
#   2. Launches AoE3 via umu-run with WINEDLLOVERRIDES=hello_anw=n,b
#   3. Waits 45s for the game to boot
#   4. Checks /tmp/anw_dll.log for the DLL load message
#   5. Kills the game
#   6. Reports pass/fail

set -euo pipefail

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
DLL_LOG="/tmp/anw_dll.log"
UMU_RUN="/usr/bin/umu-run"
AOE3_EXE="$HOME/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe"
WINEPREFIX="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx"
PROTONPATH="$HOME/.local/share/Steam/steamapps/common/Proton - Experimental"
STEAM_ROOT="$HOME/.local/share/Steam"
APPID="933110"

echo "[verify] Phase 2 DLL load verification — $(date)"
echo "[verify] DLL: hello_anw.dll"

# 1. Check not already running
if pgrep -f "AoE3DE_s.exe" > /dev/null 2>&1; then
    echo "[verify] ABORT: AoE3DE_s.exe is already running. Wait for it to exit first."
    exit 1
fi

# 2. Clear any previous log
rm -f "$DLL_LOG"
echo "[verify] Cleared $DLL_LOG"

# 3. Launch with override
echo "[verify] Launching AoE3 with WINEDLLOVERRIDES=hello_anw=n,b"
WINEPREFIX="$WINEPREFIX" \
PROTONPATH="$PROTONPATH" \
GAMEID="$APPID" \
STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT" \
WINEDLLOVERRIDES="hello_anw=n,b" \
"$UMU_RUN" "$AOE3_EXE" &

GAME_PID=$!
echo "[verify] umu-run PID: $GAME_PID"

# 4. Wait for boot (45s to reach main menu)
echo "[verify] Waiting 45s for game to boot..."
sleep 45

# 5. Check log
if [ -f "$DLL_LOG" ]; then
    echo "[verify] SUCCESS: DLL log exists:"
    cat "$DLL_LOG"
    RESULT="VERIFIED"
else
    echo "[verify] FAIL: $DLL_LOG not found. DLL was not loaded."
    # Check if game is even running
    if pgrep -f "AoE3DE_s.exe" > /dev/null 2>&1; then
        echo "[verify] Game IS running but DLL did not write log."
        echo "[verify] Possible causes:"
        echo "[verify]   - WINEDLLOVERRIDES not picked up by umu-run (check Proton passthrough)"
        echo "[verify]   - hello_anw.dll not found in search path"
        echo "[verify]   - Z: drive not mapped to / in this Proton version"
        echo "[verify]   - /tmp not writable from inside the Wine sandbox"
    else
        echo "[verify] Game is NOT running — it may have crashed at boot."
    fi
    RESULT="FAILED"
fi

# 6. Kill game
echo "[verify] Killing game..."
pkill -f "AoE3DE_s.exe" 2>/dev/null || true
sleep 3
pkill -9 -f "AoE3DE_s.exe" 2>/dev/null || true

echo "[verify] Result: $RESULT"
echo "[verify] Done."
