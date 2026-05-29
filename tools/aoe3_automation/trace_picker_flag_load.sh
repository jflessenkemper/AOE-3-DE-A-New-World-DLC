#!/usr/bin/env bash
# trace_picker_flag_load.sh — capture every flag/portrait file the engine
# tries to open while the user navigates the picker.
#
# Usage:
#   1. Launch game (with WINEDEBUG=+file in launch options if available).
#   2. Navigate to SELECT HOME CITY picker.
#   3. Run this script — it attaches strace to the AoE3 process.
#   4. In game: hover over each civ entry you want to trace (especially
#      French Republic + Lower Canada + Napoleonic France for comparison).
#   5. Stop the script (Ctrl-C). It writes a filtered log of file opens
#      to artifacts/picker_flag_trace.log.
#
# Output: which Flag_*.png, cpai_avatar_*.png, *.ddt files the engine
# attempted to open, and which succeeded vs failed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$REPO_ROOT/artifacts/picker_flag_trace.log"
mkdir -p "$(dirname "$OUT")"

# Find the running game (Wine truncates the Linux comm to 'Age3DE')
PID=$(pgrep -f 'AoE3DE_s\.exe$' 2>/dev/null | head -1)
if [[ -z "$PID" ]]; then
    PID=$(pgrep -x Age3DE 2>/dev/null | head -1)
fi
if [[ -z "$PID" ]]; then
    echo "ERROR: AoE3 isn't running. Start it via Steam first." >&2
    exit 1
fi

echo "Attached to AoE3 PID=$PID"
echo "Capturing file opens. Hover over picker entries in-game."
echo "Stop with Ctrl-C when done."
echo "Output: $OUT"
echo

# strace settings:
#   -f         — follow forked threads (Wine spawns many)
#   -p $PID    — attach to running process
#   -e openat  — only the openat syscall (file opens)
#   -y         — print resolved file paths next to fds
#   -s 512     — show longer path strings
#   2>&1       — strace writes to stderr by default
#
# We pipe through grep to filter for flag/portrait/avatar/picker assets.
{
    sudo strace -f -p "$PID" -e openat -y -s 512 2>&1 \
        | grep --line-buffered -iE 'Flag_|flag_hc_|cpai_avatar_|civ_flags|portrait|picker|.ddt|.png' \
        | tee "$OUT"
} || true

echo
echo "Trace saved to: $OUT"
echo "Lines captured: $(wc -l < "$OUT")"
