#!/bin/bash
# Verification script for ANW comprehensive test framework

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON3="${PYTHON3:-python3}"

echo "ANW Test Framework Verification"
echo "=============================="
echo ""

# Check required files exist
echo "Checking required files..."
required_files=(
    "test_scenarios.json"
    "PLAYSTYLE_SPECIFICATIONS.json"
    "comprehensive_test.sh"
    "TEST_FRAMEWORK_README.md"
    "QUICKSTART_TEST.md"
    "tools/aoe3_automation/matrix_runner_anw.py"
    "tools/aoe3_automation/ai_decision_analyzer.py"
    "tools/validation/validate_playstyles.py"
    "tools/validation/validate_visuals.py"
)

for file in "${required_files[@]}"; do
    path="$REPO_ROOT/$file"
    if [[ -f "$path" ]]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (MISSING)"
        exit 1
    fi
done

echo ""
echo "Checking Python syntax..."
"$PYTHON3" -m py_compile \
    "$REPO_ROOT/tools/aoe3_automation/matrix_runner_anw.py" \
    "$REPO_ROOT/tools/aoe3_automation/ai_decision_analyzer.py" \
    "$REPO_ROOT/tools/validation/validate_playstyles.py" \
    "$REPO_ROOT/tools/validation/validate_visuals.py" && \
    echo "  ✓ All Python files compile"

echo ""
echo "Checking Python imports..."
"$PYTHON3" << 'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

try:
    from tools.migration.anw_token_map import ANW_CIVS
    print(f"  ✓ ANW civs: {len(ANW_CIVS)} civs loaded")
except Exception as e:
    print(f"  ✗ Failed to import ANW civs: {e}")
    sys.exit(1)

try:
    from tools.aoe3_automation.ai_decision_analyzer import AIDecisionAnalyzer
    print("  ✓ AI Decision Analyzer")
except Exception as e:
    print(f"  ✗ Failed to import AI Decision Analyzer: {e}")
    sys.exit(1)

try:
    from tools.aoe3_automation.matrix_runner_anw import ANWMatrixRunner
    print("  ✓ Matrix Runner")
except Exception as e:
    print(f"  ✗ Failed to import Matrix Runner: {e}")
    sys.exit(1)

try:
    from tools.validation.validate_playstyles import PlaystyleValidator
    print("  ✓ Playstyle Validator")
except Exception as e:
    print(f"  ✗ Failed to import Playstyle Validator: {e}")
    sys.exit(1)

try:
    from tools.validation.validate_visuals import VisualValidator
    print("  ✓ Visual Validator")
except Exception as e:
    print(f"  ✗ Failed to import Visual Validator: {e}")
    sys.exit(1)

print("  ✓ All imports OK")
PYEOF

echo ""
echo "Checking artifact directory..."
mkdir -p "/var/home/jflessenkemper/artifacts/anw_matrix" && \
    echo "  ✓ Artifact directory writable"

echo ""
echo "Checking JSON files..."
"$PYTHON3" << 'PYEOF'
import json

try:
    with open("test_scenarios.json") as f:
        data = json.load(f)
    print(f"  ✓ test_scenarios.json: {len(data['scenarios'])} scenarios")
except Exception as e:
    print(f"  ✗ test_scenarios.json: {e}")
    exit(1)

try:
    with open("PLAYSTYLE_SPECIFICATIONS.json") as f:
        data = json.load(f)
    print(f"  ✓ PLAYSTYLE_SPECIFICATIONS.json: {len(data['playstyles'])} specs")
except Exception as e:
    print(f"  ✗ PLAYSTYLE_SPECIFICATIONS.json: {e}")
    exit(1)
PYEOF

echo ""
echo "=============================="
echo "✓ Framework verification complete!"
echo ""
echo "Quick start:"
echo "  ./comprehensive_test.sh --sample"
echo ""
