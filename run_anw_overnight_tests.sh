#!/bin/bash
# Master test runner for ANW overnight validation
# Run this once before sleep to start full automation

set -e

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
TOOLS="${REPO_ROOT}/tools/aoe3_automation"
ARTIFACT_DIR="${REPO_ROOT}/artifacts/anw_overnight"

mkdir -p "${ARTIFACT_DIR}"

echo "=========================================="
echo "ANW Overnight Testing Framework"
echo "=========================================="
echo "Repo: ${REPO_ROOT}"
echo "Artifacts: ${ARTIFACT_DIR}"
echo ""

# Step 1: Enable developer mode and launch game
echo "[1/3] Launching game with developer mode enabled..."
python3 "${TOOLS}/launch_anw_game.py"

# Wait for Steam/game to stabilize
sleep 10

# Step 2: Run matrix tests with real games
echo ""
echo "[2/3] Running comprehensive ANW matrix tests..."
echo "      (this will take 8-12 hours for all 48 civs)"
echo ""

cd "${REPO_ROOT}"
PYTHONPATH="${REPO_ROOT}:$PYTHONPATH" python3 "${TOOLS}/matrix_runner_anw_live.py" \
  --observe-seconds 120 \
  --skip-launch \
  2>&1 | tee "${ARTIFACT_DIR}/test_run.log"

TEST_EXIT=$?

if [ $TEST_EXIT -eq 0 ]; then
  echo "[3/3] Tests completed successfully"
  echo ""
  echo "Report: ${ARTIFACT_DIR}/final_report.json"
else
  echo "[ERROR] Tests failed with exit code $TEST_EXIT"
fi

exit $TEST_EXIT
