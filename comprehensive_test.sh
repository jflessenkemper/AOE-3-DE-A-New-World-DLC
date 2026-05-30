#!/bin/bash
################################################################################
# Comprehensive ANW Playstyle Validator — Master Test Runner
#
# Orchestrates exhaustive overnight testing of all 48 ANW nations:
# - Runs each civ through configurable scenarios
# - Logs AI decisions and captures screenshots
# - Analyzes playstyles and validates against specifications
# - Generates detailed HTML/JSON reports
#
# Usage:
#   ./comprehensive_test.sh [options]
#
# Options:
#   --all              Run full matrix (all 48 civs, all scenarios) [default]
#   --sample           Run fast sample (2 civs × 2 scenarios, ~30 min)
#   --fast             Skip slow scenarios (observance_seconds > 600)
#   --civs-only        Run only civ tests, skip visual/playstyle validation
#   --validate-only    Only validate collected results (no game runs)
#   --resume DIR       Resume from checkpoint
#   --artifact-dir DIR Override artifact directory
#   --dry-run          Print what would run without executing
#
# Workflow:
#   1. Validate prerequisites (game running, log capture ready)
#   2. Load test scenarios from test_scenarios.json
#   3. Run matrix: all civs × scenarios
#      - Capture logs and screenshots per match
#      - Parse AI decisions with ai_decision_analyzer.py
#   4. Validate playstyles against specifications
#   5. Validate visual assets in screenshots
#   6. Generate comprehensive reports (HTML, JSON, markdown)
#   7. Summary with any critical failures
#
# Estimated times:
#   - Full matrix (48 civs × 6 scenarios):   ~14-18 hours
#   - Medium matrix (48 civs × 2 scenarios): ~6-8 hours
#   - Sample (2 civs × 2 scenarios):         ~30 minutes
################################################################################

set -euo pipefail

# ─── Configuration ─────────────────────────────────────────────────────────────

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON3="${PYTHON3:-python3}"
ARTIFACT_ROOT="${ARTIFACT_ROOT:-/var/home/jflessenkemper/artifacts/anw_matrix}"

# Test modes
TEST_MODE="all"           # all, sample, fast, civs-only, validate-only
RESUME_DIR=""
DRY_RUN=0

# ─── Functions ─────────────────────────────────────────────────────────────────

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[ERROR] $*" >&2
    exit 1
}

warn() {
    echo "[WARN] $*" >&2
}

run_cmd() {
    if [[ $DRY_RUN -eq 1 ]]; then
        echo "[DRY-RUN] $*"
    else
        "$@"
    fi
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check Python
    if ! command -v "$PYTHON3" &> /dev/null; then
        error "Python3 not found: $PYTHON3"
    fi

    # Check required modules exist
    local required_modules=(
        "tools/aoe3_automation/matrix_runner_anw.py"
        "tools/aoe3_automation/ai_decision_analyzer.py"
        "tools/validation/validate_playstyles.py"
        "tools/validation/validate_visuals.py"
        "test_scenarios.json"
    )

    for module in "${required_modules[@]}"; do
        local path="$REPO_ROOT/$module"
        if [[ ! -f "$path" ]]; then
            error "Required module not found: $path"
        fi
    done

    # Check artifact directory writable
    if ! mkdir -p "$ARTIFACT_ROOT" 2>/dev/null; then
        error "Cannot create artifact directory: $ARTIFACT_ROOT"
    fi

    log "Prerequisites OK"
}

load_scenarios() {
    log "Loading test scenarios..."

    if [[ ! -f "$REPO_ROOT/test_scenarios.json" ]]; then
        error "Scenario config not found: $REPO_ROOT/test_scenarios.json"
    fi

    # Count scenarios
    local scenario_count=$($PYTHON3 -c "
import json
with open('$REPO_ROOT/test_scenarios.json') as f:
    data = json.load(f)
print(len(data.get('scenarios', [])))
" 2>/dev/null || echo "0")

    log "Loaded $scenario_count scenarios"
}

run_matrix_tests() {
    log "Starting matrix test run..."
    log "Mode: $TEST_MODE"

    local matrix_cmd=(
        "$PYTHON3"
        "$REPO_ROOT/tools/aoe3_automation/matrix_runner_anw.py"
    )

    case "$TEST_MODE" in
        all)
            matrix_cmd+=(--all-civs --all-scenarios)
            ;;
        sample)
            matrix_cmd+=(--sample)
            ;;
        fast)
            matrix_cmd+=(--all-civs --all-scenarios)
            # TODO: filter scenarios by observe_seconds
            ;;
        validate-only)
            log "Skipping game runs (validate-only mode)"
            return 0
            ;;
        *)
            error "Unknown test mode: $TEST_MODE"
            ;;
    esac

    [[ -n "$ARTIFACT_ROOT" ]] && matrix_cmd+=(--artifact-dir "$ARTIFACT_ROOT")

    run_cmd "${matrix_cmd[@]}"
}

validate_playstyles() {
    log "Validating playstyles..."

    local latest_run=$(ls -dt "$ARTIFACT_ROOT"/anw_matrix_* 2>/dev/null | head -1)

    if [[ -z "$latest_run" ]]; then
        warn "No test artifacts found (expected if game tests skipped)"
        return 0
    fi

    log "Validating: $latest_run"

    run_cmd "$PYTHON3" "$REPO_ROOT/tools/validation/validate_playstyles.py" "$latest_run"
}

validate_visuals() {
    log "Validating visual assets..."

    local latest_run=$(ls -dt "$ARTIFACT_ROOT"/anw_matrix_* 2>/dev/null | head -1)

    if [[ -z "$latest_run" ]]; then
        warn "No test artifacts found"
        return 0
    fi

    log "Validating: $latest_run"

    run_cmd "$PYTHON3" "$REPO_ROOT/tools/validation/validate_visuals.py" "$latest_run"
}

generate_summary_report() {
    log "Generating summary report..."

    local latest_run=$(ls -dt "$ARTIFACT_ROOT"/anw_matrix_* 2>/dev/null | head -1)

    if [[ -z "$latest_run" ]]; then
        warn "No test artifacts found"
        return 0
    fi

    local summary_file="$latest_run/COMPREHENSIVE_SUMMARY.md"

    cat > "$summary_file" << 'EOF'
# ANW Comprehensive Test Run Report

## Overview
- **Run Date**: $(date)
- **Duration**: See run_report.json
- **Total Civs**: 48
- **Test Modes**: Rush, Boom, Military, Naval, Late-game, Trading Post

## Key Findings

### Playstyle Validation
- See `validation_report.json` and `validation_report.html`

### Visual Asset Validation
- See `visual_validation_report.json` and `visual_validation_report.html`

### Critical Issues
- Review CRITICAL_FAILURES section in validation_report.json

## Artifacts
```
EOF

    echo "- Run metadata: run_report.json" >> "$summary_file"
    echo "- Playstyle validation: validation_report.json" >> "$summary_file"
    echo "- Visual validation: visual_validation_report.json" >> "$summary_file"
    echo "- Per-civ logs: each <civ>_<scenario>/ directory" >> "$summary_file"

    log "Summary report: $summary_file"
}

print_usage() {
    cat << 'EOF'
Usage: ./comprehensive_test.sh [OPTIONS]

Options:
  --all              Run full matrix (all 48 civs, all scenarios) [default]
  --sample           Run fast sample (2 civs × 2 scenarios, ~30 min)
  --fast             Skip slow scenarios
  --civs-only        Run only civ tests
  --validate-only    Only validate results
  --resume DIR       Resume from checkpoint
  --artifact-dir DIR Override artifact directory
  --dry-run          Print commands without executing
  --help             Show this message

Examples:
  # Full overnight run
  ./comprehensive_test.sh --all

  # Quick validation test
  ./comprehensive_test.sh --sample

  # Continue interrupted run
  ./comprehensive_test.sh --validate-only --artifact-dir /path/to/run

EOF
}

# ─── Main ──────────────────────────────────────────────────────────────────────

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all)
                TEST_MODE="all"
                shift
                ;;
            --sample)
                TEST_MODE="sample"
                shift
                ;;
            --fast)
                TEST_MODE="fast"
                shift
                ;;
            --civs-only)
                TEST_MODE="civs-only"
                shift
                ;;
            --validate-only)
                TEST_MODE="validate-only"
                shift
                ;;
            --resume)
                RESUME_DIR="$2"
                shift 2
                ;;
            --artifact-dir)
                ARTIFACT_ROOT="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                warn "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done

    log "=========================================="
    log "ANW Comprehensive Test Runner"
    log "=========================================="
    log "Repository: $REPO_ROOT"
    log "Artifact root: $ARTIFACT_ROOT"
    log "Test mode: $TEST_MODE"
    [[ $DRY_RUN -eq 1 ]] && log "DRY-RUN MODE"
    log "=========================================="

    # Run workflow
    check_prerequisites
    load_scenarios

    case "$TEST_MODE" in
        validate-only)
            log "Validation-only mode: skipping game tests"
            ;;
        civs-only)
            log "Civs-only mode: running tests but not validation"
            run_matrix_tests
            return 0
            ;;
        *)
            run_matrix_tests
            ;;
    esac

    if [[ "$TEST_MODE" != "civs-only" ]]; then
        validate_playstyles
        validate_visuals
        generate_summary_report
    fi

    log "=========================================="
    log "Test run complete!"
    log "Artifacts: $ARTIFACT_ROOT"
    log "=========================================="
}

main "$@"
