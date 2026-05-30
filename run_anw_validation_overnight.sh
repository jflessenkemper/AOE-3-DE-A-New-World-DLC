#!/bin/bash
# ANW Overnight Validation Framework
# Comprehensive deterministic testing of all 48 ANW civilizations
#
# Usage:
#   bash run_anw_validation_overnight.sh           # Full run (all 48 civs, all phases)
#   bash run_anw_validation_overnight.sh sample    # Sample run (5 civs, phase 1-2 only)
#   bash run_anw_validation_overnight.sh quick     # Quick run (5 civs, 30s observation)

set -e

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
ARTIFACTS="${REPO_ROOT}/artifacts/anw_validation_$(date +%Y%m%d_%H%M%S)"
MODE="${1:-full}"

echo "========================================================================"
echo "ANW Overnight Validation Framework"
echo "========================================================================"
echo "Repository: ${REPO_ROOT}"
echo "Mode: ${MODE}"
echo "Artifacts: ${ARTIFACTS}"
echo ""

mkdir -p "${ARTIFACTS}"

# Function to run validation
run_validation() {
  local phase_arg="${1}"
  local all_arg="${2}"
  local observe_arg="${3:-60}"

  cd "${REPO_ROOT}"

  echo "[*] Starting validation: phase=${phase_arg}, all=${all_arg}, observe=${observe_arg}s"
  python3 tools/aoe3_automation/master_validator_anw.py \
    --phase ${phase_arg} \
    ${all_arg} \
    --observe-seconds ${observe_arg} \
    2>&1 | tee "${ARTIFACTS}/validation.log"
}

# Dispatch based on mode
case "${MODE}" in
  full)
    echo "[*] FULL MODE: All 48 civs, phases 1-2, 60s observation each"
    echo "[*] Estimated duration: ~4-5 hours"
    echo ""
    run_validation "1 2" "--all" "60"
    ;;

  sample)
    echo "[*] SAMPLE MODE: First 5 civs, phases 1-2, 60s observation each"
    echo "[*] Estimated duration: ~10-15 minutes"
    echo ""
    run_validation "1 2" "" "60"
    ;;

  quick)
    echo "[*] QUICK MODE: First 5 civs, phase 2 only, 30s observation each"
    echo "[*] Estimated duration: ~5 minutes"
    echo ""
    run_validation "2" "" "30"
    ;;

  phase1only)
    echo "[*] PHASE 1 ONLY: HTML reference extraction (no game required)"
    echo ""
    run_validation "1" "" "60"
    ;;

  *)
    echo "[!] Unknown mode: ${MODE}"
    echo ""
    echo "Usage:"
    echo "  bash run_anw_validation_overnight.sh           # Full mode (all 48 civs)"
    echo "  bash run_anw_validation_overnight.sh sample    # Sample mode (5 civs)"
    echo "  bash run_anw_validation_overnight.sh quick     # Quick mode (5 civs, 30s)"
    echo "  bash run_anw_validation_overnight.sh phase1only # Phase 1 only (HTML extraction)"
    exit 1
    ;;
esac

# Post-run summary
echo ""
echo "========================================================================"
echo "Validation Complete"
echo "========================================================================"
echo "Artifacts: ${ARTIFACTS}"
echo "Log file: ${ARTIFACTS}/validation.log"
echo ""

if [ -f "${ARTIFACTS}/../master_validation_report.json" ]; then
  echo "Report: ${ARTIFACTS}/../master_validation_report.json"
  echo ""
  python3 << 'PYTHON_EOF'
import json
report_path = "artifacts/master_validation_report.json"
try:
  with open(report_path) as f:
    report = json.load(f)
    if 'phases' in report:
      for phase, data in report['phases'].items():
        if data.get('status') == 'completed':
          print(f"✓ {phase}: PASSED")
          if 'success_rate_pct' in data:
            print(f"  Success rate: {data['success_rate_pct']:.1f}%")
          if 'validator_pass_rate_pct' in data:
            print(f"  Validator pass: {data['validator_pass_rate_pct']:.1f}%")
        else:
          print(f"✗ {phase}: {data.get('status', 'UNKNOWN').upper()}")
except Exception as e:
  print(f"Could not read report: {e}")
PYTHON_EOF
fi

echo ""
echo "Done!"
