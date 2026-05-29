#!/usr/bin/env bash
# setup_input.sh — bring the verified-input harness to a working state.
#
# Run this on the HOST (not inside flatpak). It walks through all four
# remediation paths in priority order, stopping when one succeeds. Each
# step is opt-in (prompts y/N) to avoid surprising changes.
#
# Usage:  bash tools/aoe3_automation/setup_input.sh
#         bash tools/aoe3_automation/setup_input.sh --auto    # no prompts

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
AUTO=0
[[ "${1:-}" == "--auto" ]] && AUTO=1

ask() {
    local prompt="$1"
    [[ "$AUTO" == "1" ]] && { echo "[auto] $prompt → yes"; return 0; }
    read -r -p "$prompt [y/N] " yn
    [[ "$yn" =~ ^[Yy]$ ]]
}

probe() {
    cd "$REPO_ROOT"
    python3 tools/aoe3_automation/verified_input.py --probe 2>&1 | tail -25
    cd - >/dev/null
}

echo "================================================================"
echo " ANW input-harness setup — priority order: A (libei) → B (ydotool seat) → C (gamescope flag)"
echo "================================================================"

echo
echo "→ Initial probe …"
if cd "$REPO_ROOT" && python3 tools/aoe3_automation/verified_input.py --probe >/dev/null 2>&1; then
    echo "✓ A backend already works. Nothing to do."
    cd - >/dev/null
    exit 0
fi
cd - >/dev/null

echo "✗ No backend reaches the game yet. Walking remediation paths."
echo

# ---------------------------------------------------------------- Option A
echo "── Option A: libei via gamescope-0-ei (preferred) ──"
EI_BIN="$REPO_ROOT/tools/aoe3_automation/ei_inject"
if [[ -x "$EI_BIN" ]]; then
    echo "  ei_inject already built at $EI_BIN"
else
    if ! pkg-config --exists libei 2>/dev/null; then
        echo "  libei-devel headers missing."
        if ask "  Install libei-devel via rpm-ostree (REQUIRES REBOOT)?"; then
            sudo rpm-ostree install libei-devel libeis-devel
            echo "  Reboot, then re-run this script."
            exit 0
        fi
        # Fallback: extract headers from the RPM without installing
        if ask "  Skip the system install and extract headers from the RPM into a local include dir?"; then
            tmp=/tmp/libei_extract
            rm -rf "$tmp" && mkdir -p "$tmp"
            ( cd "$tmp" && dnf download libei-devel >/dev/null )
            ( cd "$tmp" && rpm2cpio libei-devel-*.x86_64.rpm | cpio -idm )
            mkdir -p "$REPO_ROOT/tools/aoe3_automation/libei_local_include"
            mkdir -p "$REPO_ROOT/tools/aoe3_automation/libei_local_lib"
            cp "$tmp/usr/include/libei-1.0/libei.h" \
               "$REPO_ROOT/tools/aoe3_automation/libei_local_include/"
            ln -sf /usr/lib64/libei.so.1 \
               "$REPO_ROOT/tools/aoe3_automation/libei_local_lib/libei.so"
        fi
    fi
    if [[ -f "$REPO_ROOT/tools/aoe3_automation/libei_local_include/libei.h" ]] \
       || pkg-config --exists libei 2>/dev/null; then
        cd "$REPO_ROOT/tools/aoe3_automation"
        if pkg-config --exists libei 2>/dev/null; then
            gcc ei_inject.c $(pkg-config --cflags --libs libei) -o ei_inject
        else
            gcc -I libei_local_include -L libei_local_lib \
                -Wl,-rpath,/usr/lib64 ei_inject.c -lei -o ei_inject
        fi
        cd - >/dev/null
        echo "  ✓ ei_inject built."
    fi
fi
echo "→ Re-probing …"
probe
if cd "$REPO_ROOT" && python3 tools/aoe3_automation/verified_input.py --probe >/dev/null 2>&1; then
    echo "✓ Option A succeeded. Done."
    exit 0
fi
cd - >/dev/null
echo "  ei_inject built but events not reaching game. Checking gamescope flags …"

# ---------------------------------------------------------------- Option B
echo
echo "── Option B: wire ydotool's uinput device into the host seat ──"
if ! pgrep -x ydotoold >/dev/null; then
    echo "  ydotoold not running."
    if ask "  Start ydotoold (sudo)?"; then
        sudo ydotoold --socket-path=/tmp/.ydotool_socket --socket-own=$UID:$UID --socket-perm=0660 &
        sleep 1
    fi
fi
EVENT_DEV=$(grep -l "ydotoold virtual device" /sys/class/input/event*/device/name 2>/dev/null \
            | head -1 | sed 's|/device/name||')
if [[ -n "$EVENT_DEV" ]]; then
    EVENT_NUM=$(basename "$EVENT_DEV")
    echo "  ydotoold device: $EVENT_NUM"
    SEAT=$(loginctl seat-status seat0 2>/dev/null | grep "$EVENT_NUM" || true)
    if [[ -z "$SEAT" ]]; then
        echo "  Device not on seat0."
        if ask "  Attach ydotoold's uinput device to seat0 (requires sudo)?"; then
            sudo loginctl attach seat0 "/sys/class/input/$EVENT_NUM" || true
        fi
    fi
fi
echo "→ Re-probing …"
probe
if cd "$REPO_ROOT" && python3 tools/aoe3_automation/verified_input.py --probe >/dev/null 2>&1; then
    echo "✓ Option B succeeded. Done."
    exit 0
fi
cd - >/dev/null

# ---------------------------------------------------------------- Option C
echo
echo "── Option C: re-launch gamescope with explicit --backend=sdl ──"
echo "  Steam launch options: gamescope --backend=sdl -W 1920 -H 1080 -- %command%"
echo "  (Set this in Steam → AoE3 DE → Properties → Launch Options.)"
echo "  Then exit and restart the game; xdotool DISPLAY=:0 will reach the SDL window."

# ---------------------------------------------------------------- Option D
echo
echo "── Option D: manual control + screenshot-only harness ──"
echo "  If no automation backend works, drive the lobby by hand and use the"
echo "  validators (validate_live_picker.py, etc.) for observation only."

echo
echo "Probe still failing. See diagnostic above; pick a path and re-run."
exit 1
