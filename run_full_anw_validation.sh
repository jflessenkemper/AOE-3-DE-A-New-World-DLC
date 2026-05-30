#!/bin/bash
# Complete ANW Deterministic Validation Pipeline (Phases 1-5)
# Runs all phases sequentially for comprehensive civ validation
#
# Usage:
#   bash run_full_anw_validation.sh [mode]
#
# Modes:
#   full   - All 48 civs, all phases (8+ hours)
#   sample - 5 civs, all phases (30-45 min)
#   quick  - Phase 1-2 only (15 min)
#   phase1 - HTML extraction only (1 min, no game needed)

set -e

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACTS="${REPO_ROOT}/artifacts/anw_full_validation_${TIMESTAMP}"
MODE="${1:-sample}"

echo "========================================================================"
echo "ANW COMPLETE DETERMINISTIC VALIDATION FRAMEWORK"
echo "========================================================================"
echo "Mode: ${MODE}"
echo "Timestamp: ${TIMESTAMP}"
echo "Artifacts: ${ARTIFACTS}"
echo ""

mkdir -p "${ARTIFACTS}"
cd "${REPO_ROOT}"

# Function to run validation
run_validation() {
  local phases="${1}"
  local civs_arg="${2}"
  local observe="${3:-60}"

  echo "[*] Running: phases=${phases}, civs=${civs_arg}, observe=${observe}s"
  echo ""

  python3 tools/aoe3_automation/master_validator_anw.py \
    --phase ${phases} \
    ${civs_arg} \
    --observe-seconds ${observe} \
    2>&1 | tee "${ARTIFACTS}/validation_${TIMESTAMP}.log"
}

# Display mode information
case "${MODE}" in
  full)
    echo "📊 FULL MODE: All 48 civs, Phases 1-5"
    echo "   Phases: HTML extraction + Behavioral + Visual + State + Determinism"
    echo "   Duration: ~8-10 hours"
    echo "   Coverage: 100% exhaustive validation"
    echo ""
    run_validation "1 2 3 4 5" "--all" "120"
    ;;

  sample)
    echo "🔍 SAMPLE MODE: 5 civs, Phases 1-5"
    echo "   Phases: HTML extraction + Behavioral + Visual + State + Determinism"
    echo "   Duration: ~45-60 minutes"
    echo "   Coverage: Quick validation of all phases"
    echo ""
    run_validation "1 2 3 4 5" "" "90"
    ;;

  quick)
    echo "⚡ QUICK MODE: 5 civs, Phases 1-2"
    echo "   Phases: HTML extraction + Behavioral validation"
    echo "   Duration: ~15-20 minutes"
    echo "   Coverage: Core validation without visual/state checks"
    echo ""
    run_validation "1 2" "" "60"
    ;;

  phase1)
    echo "📋 PHASE 1 ONLY: HTML reference extraction"
    echo "   Duration: ~1 minute"
    echo "   Coverage: Extracts ground truth from a_new_world.html"
    echo "   Note: No game required"
    echo ""
    run_validation "1" "" "60"
    ;;

  *)
    echo "❌ Unknown mode: ${MODE}"
    echo ""
    echo "Usage: bash run_full_anw_validation.sh [mode]"
    echo ""
    echo "Modes:"
    echo "  full   - All 48 civs, all phases (8+ hours)"
    echo "  sample - 5 civs, all phases (45-60 min)  [default]"
    echo "  quick  - 5 civs, phases 1-2 only (15 min)"
    echo "  phase1 - Phase 1 only (1 min, no game)"
    exit 1
    ;;
esac

# Post-validation summary
echo ""
echo "========================================================================"
echo "VALIDATION COMPLETE"
echo "========================================================================"
echo "Artifacts: ${ARTIFACTS}"
echo ""

# Check for report
if [ -f "artifacts/master_validation_report.json" ]; then
  echo "📊 Main Report: artifacts/master_validation_report.json"
  echo ""
  echo "Phase Results:"
  python3 << 'PYTHON_EOF'
import json
from pathlib import Path
report_path = Path("artifacts/master_validation_report.json")
if report_path.exists():
  with open(report_path) as f:
    report = json.load(f)
    if 'phases' in report:
      for phase, data in sorted(report['phases'].items()):
        status = data.get('status', 'UNKNOWN').upper()
        icon = "✓" if status == "COMPLETED" else "⏳" if status == "PENDING" else "✗"
        print(f"  {icon} {phase}: {status}")

        if status == "COMPLETED":
          if 'success_rate_pct' in data:
            print(f"     Success: {data['success_rate_pct']:.1f}%")
          if 'validator_pass_rate_pct' in data:
            print(f"     Compliance: {data['validator_pass_rate_pct']:.1f}%")
PYTHON_EOF
fi

echo ""
echo "Log file: ${ARTIFACTS}/validation_${TIMESTAMP}.log"
echo ""
echo "Next steps:"
echo "  1. Review the reports in ${ARTIFACTS}/"
echo "  2. Check artifacts/master_validation_report.json for detailed results"
echo "  3. For failed civs, review match logs and screenshots"
echo "  4. Fix any issues and re-run validation"
echo ""
echo "✨ Full validation framework complete!"
