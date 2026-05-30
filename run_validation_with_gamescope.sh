#!/bin/bash
# Launch AoE3 DE in gamescope and run comprehensive validation (Phases 1-5)
# Runs entirely in background with logging

set -e

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACTS="${REPO_ROOT}/artifacts/anw_full_validation_${TIMESTAMP}"
LOG_FILE="${ARTIFACTS}/validation_${TIMESTAMP}.log"
MODE="${1:-sample}"
DISPLAY="${DISPLAY:--1}"  # Use existing display or create new gamescope

mkdir -p "${ARTIFACTS}"
cd "${REPO_ROOT}"

echo "[$(date)] Starting ANW Comprehensive Validation Framework with Gamescope" | tee "${LOG_FILE}"
echo "Mode: ${MODE}" | tee -a "${LOG_FILE}"
echo "Artifacts: ${ARTIFACTS}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

# Function to launch game in gamescope
launch_game_gamescope() {
    local log="${1}"

    echo "[$(date)] Launching AoE3 DE in gamescope..." | tee -a "${log}"

    # Launch gamescope with AoE3 DE
    gamescope -h 1080 -w 1920 --steam \
        -- steam steam://run/933110 \
        > "${log}.gamescope.log" 2>&1 &

    GAME_PID=$!
    echo "[$(date)] Gamescope PID: ${GAME_PID}" | tee -a "${log}"

    # Wait for game to start (up to 120 seconds)
    echo "[$(date)] Waiting for game to launch (max 120s)..." | tee -a "${log}"
    for i in {1..120}; do
        if pgrep -P ${GAME_PID} -f "AoE3" > /dev/null 2>&1; then
            echo "[$(date)] Game process detected" | tee -a "${log}"
            sleep 5  # Let game fully load
            return 0
        fi
        sleep 1
    done

    echo "[$(date)] WARNING: Game process not detected within 120s" | tee -a "${log}"
    return 1
}

# Function to run validation
run_validation() {
    local phases="${1}"
    local civs_arg="${2}"
    local observe="${3:-60}"
    local log="${4}"

    echo "[$(date)] Running validation: phases=${phases}, civs=${civs_arg}, observe=${observe}s" | tee -a "${log}"

    python3 tools/aoe3_automation/master_validator_anw.py \
        --phase ${phases} \
        ${civs_arg} \
        --observe-seconds ${observe} \
        2>&1 | tee -a "${log}"
}

# Main execution
echo "[$(date)] ========================================" | tee -a "${LOG_FILE}"
echo "[$(date)] PHASE 1: HTML Reference Extraction" | tee -a "${LOG_FILE}"
echo "[$(date)] ========================================" | tee -a "${LOG_FILE}"

python3 tools/validation/extract_html_reference.py 2>&1 | tee -a "${LOG_FILE}"

echo "" | tee -a "${LOG_FILE}"
echo "[$(date)] ========================================" | tee -a "${LOG_FILE}"
echo "[$(date)] Launching Game in Gamescope" | tee -a "${LOG_FILE}"
echo "[$(date)] ========================================" | tee -a "${LOG_FILE}"

# Launch game
launch_game_gamescope "${LOG_FILE}"

echo "" | tee -a "${LOG_FILE}"

# Determine validation parameters based on mode
case "${MODE}" in
    full)
        echo "[$(date)] 📊 FULL MODE: All 48 civs, Phases 1-5" | tee -a "${LOG_FILE}"
        run_validation "1 2 3 4 5" "--all" "120" "${LOG_FILE}"
        ;;
    sample)
        echo "[$(date)] 🔍 SAMPLE MODE: 5 civs, Phases 1-5" | tee -a "${LOG_FILE}"
        run_validation "1 2 3 4 5" "" "90" "${LOG_FILE}"
        ;;
    quick)
        echo "[$(date)] ⚡ QUICK MODE: 5 civs, Phases 1-2" | tee -a "${LOG_FILE}"
        run_validation "1 2" "" "60" "${LOG_FILE}"
        ;;
    *)
        echo "[$(date)] ❌ Unknown mode: ${MODE}" | tee -a "${LOG_FILE}"
        echo "[$(date)] Usage: bash run_validation_with_gamescope.sh [full|sample|quick]" | tee -a "${LOG_FILE}"
        exit 1
        ;;
esac

# Post-validation summary
echo "" | tee -a "${LOG_FILE}"
echo "[$(date)] ========================================" | tee -a "${LOG_FILE}"
echo "[$(date)] VALIDATION COMPLETE" | tee -a "${LOG_FILE}"
echo "[$(date)] ========================================" | tee -a "${LOG_FILE}"
echo "[$(date)] Artifacts: ${ARTIFACTS}" | tee -a "${LOG_FILE}"
echo "[$(date)] Log file: ${LOG_FILE}" | tee -a "${LOG_FILE}"

# Check for report
if [ -f "${ARTIFACTS}/artifacts/master_validation_report.json" ]; then
    echo "[$(date)] 📊 Master Report: ${ARTIFACTS}/artifacts/master_validation_report.json" | tee -a "${LOG_FILE}"
fi

echo "[$(date)] ✨ Full validation framework execution complete!" | tee -a "${LOG_FILE}"
