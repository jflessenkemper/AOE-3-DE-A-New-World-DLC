#!/usr/bin/env bash
# recover_kwin_input.sh — recover synthetic-input authorisation on Plasma 6 Wayland.
#
# Symptom this script fixes:
#   xdotool / ydotool / KWin MCP all return success but nothing actually moves
#   on screen. The cursor is frozen at its last position. Diagnosis: KDE Plasma
#   6 grants org.kde.KWin.fakeinput as a per-app permission via a popup dialog;
#   if you Deny once or the popup is eaten by gamescope, the permission stays
#   revoked until the compositor restarts.
#
# What this script does:
#   Restarts kwin_wayland in place (--replace). Plasma + your open apps survive.
#   The next time anything attempts synthetic input, KWin re-prompts the dialog;
#   click "Allow" once and synthetic input works again.
#
# How to run:
#   1. Switch to a TTY: Ctrl+Alt+F3 (F2 is sometimes the SDDM greeter).
#   2. Log in with your normal user.
#   3. bash /var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/aoe3_automation/recover_kwin_input.sh
#   4. Ctrl+Alt+F1 (or F7) to return to the graphical session.
#   5. The next synthetic-input attempt will pop the permission dialog.
#
# Safety guards:
#   - Refuses to run as root (kwin_wayland must run as the user owning the session).
#   - Verifies kwin_wayland is on PATH before doing anything.
#   - Logs to /tmp/kwin-replace-<timestamp>.log so you can read what happened.

set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERROR: do not run as root. Run as the user who owns the Plasma session." >&2
  exit 1
fi

if ! command -v kwin_wayland >/dev/null 2>&1; then
  echo "ERROR: kwin_wayland not on PATH. On Bazzite you may need to enter the kde-plasma flatpak runtime first." >&2
  exit 1
fi

# Plasma session normally exports these in the user environment, but a fresh
# TTY login starts with an empty environment. Set the conventional values; if
# you have a non-default WAYLAND_DISPLAY (e.g. wayland-1) override it inline:
#   WAYLAND_DISPLAY=wayland-1 bash recover_kwin_input.sh
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

LOG="/tmp/kwin-replace-$(date +%Y%m%d-%H%M%S).log"

echo "Replacing running kwin_wayland. Log: $LOG"
echo "DISPLAY=$DISPLAY  WAYLAND_DISPLAY=$WAYLAND_DISPLAY  XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"
echo

# nohup + disown detaches from this TTY so the new compositor survives logout.
nohup kwin_wayland --replace >"$LOG" 2>&1 &
NEW_PID=$!
disown "$NEW_PID" 2>/dev/null || true

# Give the replace 3s to take effect; if kwin failed to start it'll have exited
# by then and we should surface the log.
sleep 3
if ! kill -0 "$NEW_PID" 2>/dev/null; then
  echo "ERROR: kwin_wayland replace exited within 3s. Tail of log:" >&2
  tail -20 "$LOG" >&2 || true
  exit 1
fi

echo "kwin_wayland --replace running as PID $NEW_PID."
echo "Switch back to your graphical session (Ctrl+Alt+F1 or F7) and trigger any"
echo "synthetic-input action. KWin should now re-prompt the permission dialog."
exit 0
