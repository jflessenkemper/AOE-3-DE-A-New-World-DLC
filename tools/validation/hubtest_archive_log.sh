#!/usr/bin/env bash
# hubtest_archive_log.sh — wait for an anwHubTest match to self-terminate,
# then archive Age3Log.txt to artifacts/validation/ai_playstyle/hubtest_passN_*/
#
# Usage:
#   PASS=1 ./tools/validation/hubtest_archive_log.sh
#
# Workflow per pass:
#   1. Start this script with PASS=N (it waits for the auto-end).
#   2. In AoE3: Skirmish → map "ANW Hub Test" → fill slots 2..8 with the civs
#      listed for this pass (see artifacts/validation/hub_test_roster.md, also
#      printed below) → press Play.
#   3. The map self-terminates at T+1200s (20 min) by setting the observer
#      defeated. Walk away.
#   4. When this script wakes, it archives the log and greps probe counts.
#
# The map runs autonomously. No keystroke/mouse automation here — the game's
# own triggers fire the milestones and write [LLP v=2] lines to Age3Log.txt.

set -euo pipefail

PASS="${PASS:-}"
if [[ -z "$PASS" ]]; then
    echo "Error: PASS env var is required (1..6)" >&2
    exit 1
fi

LOGFILE="${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
ARTROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ai_playstyle"
RUNDIR="${ARTROOT}/hubtest_pass${PASS}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${RUNDIR}"

declare -A PASS_CIVS=(
  [1]="ANWCanadians ANWAztecs ANWBarbary ANWBrazil ANWGermans ANWArgentines ANWChileans"
  [2]="ANWHaitians ANWBritish ANWHausa ANWItalians ANWColumbians ANWChinese ANWIndonesians"
  [3]="ANWDutch ANWRomanians ANWMexicans ANWHaudenosaunee ANWEgyptians ANWMayans ANWPortuguese"
  [4]="ANWRussians ANWRevFrance ANWHungarians ANWEthiopians ANWSouthAfricans ANWUSA ANWJapanese"
  [5]="ANWFinnish ANWLakota ANWFrench ANWNapoleonicFrance ANWInca ANWSpanish ANWIndians"
  [6]="ANWSwedes ANWMaltese ANWTexians ANWOttomans ANWPeruvians"
)

CIVS="${PASS_CIVS[$PASS]:-}"
if [[ -z "$CIVS" ]]; then
    echo "Error: PASS=$PASS not in 1..6" >&2
    exit 1
fi

echo "==========================================================================="
echo "ANW Hub Test — Pass ${PASS}"
echo "==========================================================================="
echo "Civs for this pass (assign one per AI slot 2..8 in Skirmish setup):"
for civ in $CIVS; do
    echo "  - $civ"
done
echo ""
echo "Map: ANW Hub Test  (or anwHubTest in the map list)"
echo "Slot 1: Player (Observer) — any civ, you will be auto-defeated at T+1200s"
echo ""
echo "Archive dir: ${RUNDIR}"
echo "Log source : ${LOGFILE}"
echo ""

# Truncate the log so we only capture this pass's lines
echo "Truncating Age3Log.txt so this pass's lines are isolated..."
: > "${LOGFILE}"

echo "==> Now start the match in AoE3.  This script will sleep 1260s (21 min)"
echo "    then auto-archive the log."
echo ""

SLEEP_S=1260
START_TS=$(date +%s)
END_TS=$((START_TS + SLEEP_S))
while :; do
    NOW_TS=$(date +%s)
    if (( NOW_TS >= END_TS )); then break; fi
    REMAIN=$(( END_TS - NOW_TS ))
    printf "\r  waiting ... %5ds remaining " "$REMAIN"
    sleep 10
done
printf "\n"

cp -v "${LOGFILE}" "${RUNDIR}/Age3Log.txt"

PROBE_COUNT=$(grep -c '\[LLP v=2\]' "${RUNDIR}/Age3Log.txt" || true)
WALL_COUNT=$(grep -c 'milestone.first_wall_segment' "${RUNDIR}/Age3Log.txt" || true)
BARRACKS_COUNT=$(grep -c 'milestone.first_barracks' "${RUNDIR}/Age3Log.txt" || true)
POSTURE_COUNT=$(grep -c 'posture.snapshot' "${RUNDIR}/Age3Log.txt" || true)

echo ""
echo "==========================================================================="
echo "Pass ${PASS} probe summary"
echo "==========================================================================="
echo "  Total [LLP v=2] lines      : ${PROBE_COUNT}"
echo "  milestone.first_wall_segment: ${WALL_COUNT}"
echo "  milestone.first_barracks   : ${BARRACKS_COUNT}"
echo "  posture.snapshot           : ${POSTURE_COUNT}"
echo ""
echo "Archived to: ${RUNDIR}/Age3Log.txt"
echo "Next pass: PASS=$((PASS + 1)) $0"
