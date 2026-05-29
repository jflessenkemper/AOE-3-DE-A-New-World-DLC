#!/usr/bin/env bash
# install_goldberg_for_scenarios.sh
#
# Drop-in installer for Goldberg Steam Emu, the community-maintained
# replacement steam_api64.dll that lets AoE3 DE load custom scenarios on
# Linux/Proton without the engine's Inventory ownership check rejecting
# them as INVALID FILE.
#
# Why this is needed:
#   `tools/validation/scenario_load_bypass.md` documents that the AoE3 DE
#   engine binary is Arxan-encrypted and rejects custom scenarios via an
#   `Unlock Error - Inventory Extended:-1` gate that funnels through
#   `ISteamInventory`. The standard fix is a steam_api64.dll replacement
#   that fakes ownership of every DLC entitlement.
#
# What this script does:
#   1. Backs up the current steam_api64.dll (if not already backed up).
#   2. Downloads the latest Goldberg release from gitlab.com.
#   3. Drops the Windows-x64 build into the AoE3 DE folder.
#   4. Writes steam_appid.txt and steam_settings/DLC.txt with every
#      known AoE3 DE DLC ID so Goldberg reports them all as owned.
#   5. Prints reversal instructions.
#
# WHAT IT DOES NOT DO:
#   - Verify Goldberg release signatures. (Future improvement.)
#   - Auto-launch the game.
#   - Disable Steam's auto-verify; the user MUST set
#     Steam → AoE3 DE Properties → Updates → "Only update when I launch it"
#     manually, or Steam will restore the original steam_api64.dll.
#
# USAGE:
#   tools/aoe3_automation/install_goldberg_for_scenarios.sh           # dry-run (default)
#   tools/aoe3_automation/install_goldberg_for_scenarios.sh --apply   # actually deploy
#   tools/aoe3_automation/install_goldberg_for_scenarios.sh --revert  # restore .original
#
# CAVEATS (read before --apply):
#   * Steam Workshop / online matchmaking will NOT work while Goldberg
#     is active. For offline scenario testing this is fine.
#   * Goldberg is MIT-licensed and widely used in the AoE community.
#     The source is at https://gitlab.com/Mr_Goldberg/goldberg_emulator.
#     Review before deploying.
#   * Reversible at any time via --revert.

set -euo pipefail

GAME_DIR="${HOME}/.local/share/Steam/steamapps/common/AoE3DE"
DLL="${GAME_DIR}/steam_api64.dll"
DLL_BACKUP="${GAME_DIR}/steam_api64.dll.original"
APPID_FILE="${GAME_DIR}/steam_appid.txt"
SETTINGS_DIR="${GAME_DIR}/steam_settings"
DLC_FILE="${SETTINGS_DIR}/DLC.txt"

# 2026-05-11: the original CI-artifacts URL (master/download?job=build) now
# returns HTTP 404 (Goldberg's gitlab CI was disabled some time after this
# script was originally written). Switched to the last stable release v0.2.5
# (Aug 2019), which is the final tagged build by the original author. The
# v0.2.5 zip root contains steam_api64.dll directly (no "release/" subdir),
# so the unzip-target path below was updated to match. v0.2.5 includes
# Inventory support per its release notes, which is the API that AoE3 DE's
# scenario-load gate checks against.
GOLDBERG_URL="https://gitlab.com/Mr_Goldberg/goldberg_emulator/uploads/2524331e488ec6399c396cf48bbe9903/Goldberg_Lan_Steam_Emu_v0.2.5.zip"
WORK_DIR="$(mktemp -d -t anw-goldberg-XXXXXX)"
trap 'rm -rf "${WORK_DIR}"' EXIT

MODE="${1:-dry-run}"

usage() {
  sed -n '2,40p' "$0"
}

require_game_dir() {
  if [[ ! -d "${GAME_DIR}" ]]; then
    echo "ERROR: AoE3 DE not found at ${GAME_DIR}." >&2
    echo "Is the game installed via Steam?" >&2
    exit 2
  fi
}

action_revert() {
  require_game_dir
  if [[ ! -f "${DLL_BACKUP}" ]]; then
    echo "ERROR: no backup at ${DLL_BACKUP}. Cannot revert." >&2
    exit 3
  fi
  echo "[+] Restoring ${DLL} from ${DLL_BACKUP}"
  cp -p "${DLL_BACKUP}" "${DLL}"
  echo "[+] Removing ${APPID_FILE} (if present)"
  rm -f "${APPID_FILE}"
  echo "[+] Removing ${SETTINGS_DIR} (if present)"
  rm -rf "${SETTINGS_DIR}"
  echo "Done. Original Steam DLL restored."
}

show_plan() {
  echo "=== Goldberg install plan ==="
  echo
  echo "Game dir         : ${GAME_DIR}"
  echo "DLL backup       : ${DLL_BACKUP}"
  if [[ -f "${DLL_BACKUP}" ]]; then
    echo "                   (already exists, will not overwrite)"
  else
    echo "                   (will be created on --apply)"
  fi
  echo "DLC list (5)     : ${DLC_FILE}"
  echo "Steam app ID file: ${APPID_FILE}  (will contain 933110)"
  echo "Goldberg source  : ${GOLDBERG_URL}"
  echo
  echo "Cross-check first: run a successful skirmish match, then check"
  echo "    grep -c 'Unlock Error - Inventory' \\"
  echo "        \"\${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt\""
  echo "If that returns 0 (zero unlock errors on a SUCCESSFUL skirmish)"
  echo "then the Inventory check is the gate and Goldberg will help."
  echo "If it returns positive, the line is benign and we need a different"
  echo "log-diff approach — DO NOT install Goldberg in that case."
  echo
  echo "Re-run with --apply to deploy, --revert to restore the original DLL."
}

action_apply() {
  require_game_dir

  # Cross-check question: warn if the user hasn't done it yet.
  echo
  echo "===================================================================="
  echo "Have you done the cross-check?"
  echo "  - Launch a successful random-map skirmish."
  echo "  - grep 'Unlock Error - Inventory' Age3Log.txt."
  echo "  - If the count is POSITIVE on success → the line is benign;"
  echo "    Goldberg may not help. Read scenario_load_bypass.md first."
  echo "===================================================================="
  read -rp "Proceed anyway? [y/N] " ans
  case "${ans}" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 1 ;;
  esac

  # Step 1: backup
  if [[ ! -f "${DLL_BACKUP}" ]]; then
    echo "[+] Backing up ${DLL} -> ${DLL_BACKUP}"
    cp -p "${DLL}" "${DLL_BACKUP}"
  else
    echo "[=] Backup already exists: ${DLL_BACKUP}"
  fi

  # Step 2: download Goldberg
  echo "[+] Downloading Goldberg latest…"
  if ! command -v curl >/dev/null; then
    echo "ERROR: curl is required." >&2; exit 4
  fi
  cd "${WORK_DIR}"
  if ! curl -fSL -o goldberg.zip "${GOLDBERG_URL}"; then
    echo "ERROR: download failed. Visit ${GOLDBERG_URL} in a browser" >&2
    echo "       and place the .zip at ${WORK_DIR}/goldberg.zip then re-run." >&2
    exit 5
  fi
  if ! command -v unzip >/dev/null; then
    echo "ERROR: unzip is required." >&2; exit 6
  fi
  unzip -q goldberg.zip
  # v0.2.5 zip root contains steam_api64.dll directly. (Older script versions
  # expected release/steam_api64.dll — that layout was from the CI-artifacts
  # zip which no longer exists.)
  if [[ ! -f steam_api64.dll ]]; then
    echo "ERROR: Goldberg layout changed — steam_api64.dll not found at zip root." >&2
    echo "       Check the unzipped contents:" >&2
    ls -la "${WORK_DIR}" >&2
    exit 7
  fi

  # Step 3: drop into AoE3 DE folder
  echo "[+] Copying Goldberg steam_api64.dll -> ${DLL}"
  cp -p steam_api64.dll "${DLL}"

  # Step 4: write steam_appid.txt
  echo "[+] Writing ${APPID_FILE}"
  echo 933110 > "${APPID_FILE}"

  mkdir -p "${SETTINGS_DIR}"
  echo "[+] Writing ${DLC_FILE}"
  cat > "${DLC_FILE}" << 'EOF'
# AoE3 DE DLC IDs for Goldberg ownership emulation.
# Format: <appid>=<name>
1167070=Age of Empires III: DE - The African Royals
1442590=Age of Empires III: DE - Knights of the Mediterranean
1937550=Age of Empires III: DE - The Asian Dynasties
2138310=Age of Empires III: DE - Mexico Civilization
2208600=Age of Empires III: DE - United States Civilization
EOF

  echo
  echo "===================================================================="
  echo "Goldberg installed. Before launching:"
  echo "  1. Open Steam → Library → AoE3 DE → Properties → Updates"
  echo "     Set 'Auto-update' to 'Only update this game when I launch it'."
  echo "     Otherwise Steam will overwrite the new steam_api64.dll on"
  echo "     restart, reverting the bypass."
  echo "  2. Launch AoE3 DE via Steam normally."
  echo "  3. Try to load the ANEWWORLD scenario (Steam Cloud path:"
  echo "     ~/.local/share/Steam/userdata/209941315/933110/remote/scenario@ANEWWORLD.age3Yscn)."
  echo "  4. If it loads, the gate was the Inventory check and we're done."
  echo "  5. If it still fails, check Age3Log.txt for new error lines and"
  echo "     consult tools/validation/scenario_load_bypass.md step 3."
  echo
  echo "Revert at any time with:"
  echo "  $(basename "$0") --revert"
  echo "===================================================================="
}

case "${MODE}" in
  --apply)  action_apply  ;;
  --revert) action_revert ;;
  --help|-h) usage ;;
  dry-run)  show_plan ;;
  *) usage; exit 1 ;;
esac
