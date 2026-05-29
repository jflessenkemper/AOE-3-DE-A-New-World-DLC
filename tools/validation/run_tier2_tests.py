#!/usr/bin/env python3
"""
TIER 2: SCENARIO EXECUTION ORCHESTRATOR

Helper script to organize and validate TIER 2 gameplay test execution.
Expects: scenario log files in logs/tier2/ directory (one per civ)
Output: Organized logs with metadata, ready for TIER 3 validation

Usage:
  python3 run_tier2_tests.py --init              # Create log directory structure
  python3 run_tier2_tests.py --check             # Verify log files are present
  python3 run_tier2_tests.py --validate          # Validate all logs with TIER 3
  python3 run_tier2_tests.py --summary           # Generate execution summary
"""

import sys
import json
from pathlib import Path
from datetime import datetime

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from tools.migration.anw_token_map import ANW_CIVS
from tools.migration.anw_mapping import ANW_CIVS_BY_SLUG

LOGS_DIR = repo_root / "logs" / "tier2"
RESULTS_DIR = repo_root / "logs" / "tier2_results"

def init_directories():
    """Create log directory structure."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Create placeholder for each civ. ANW_CIVS is a dict keyed by ANW token.
    for anw_token in ANW_CIVS:
        civ_log = LOGS_DIR / f"{anw_token}_scenario.log"
        if not civ_log.exists():
            civ_log.write_text(f"# Awaiting TIER 2 test execution for {anw_token}\n")

    print(f"✓ Initialized {len(ANW_CIVS)} log placeholders in {LOGS_DIR}")

def check_log_files():
    """Verify scenario log files are present and complete."""
    print("\n[CHECK] TIER 2 Log Files")
    print("="*80)

    missing = []
    present = []

    for civ in ANW_CIVS:
        log_file = LOGS_DIR / f"{civ.anw_token}_scenario.log"

        if not log_file.exists():
            missing.append(civ.anw_token)
        else:
            content = log_file.read_text()
            if "Awaiting TIER 2" in content or len(content) < 100:
                missing.append(f"{civ.anw_token} (incomplete)")
            else:
                present.append(civ.anw_token)

    print(f"\n✓ Complete logs: {len(present)}/{len(ANW_CIVS)}")
    if present:
        for token in present[:5]:
            print(f"  - {token}")
        if len(present) > 5:
            print(f"  ... and {len(present)-5} more")

    if missing:
        print(f"\n✗ Missing/incomplete logs: {len(missing)}/{len(ANW_CIVS)}")
        for token in missing[:10]:
            print(f"  - {token}")
        if len(missing) > 10:
            print(f"  ... and {len(missing)-10} more")

        print("\nTo complete TIER 2:")
        print("  1. Load ANW_Doctrine_Validator.scn in AOE3 Scenario Editor")
        print("  2. For each civ:")
        print("     a. Set Computer player to that civ")
        print("     b. Run game 10 minutes")
        print("     c. Export trigger log to: logs/tier2/{CivName}_scenario.log")
        return False

    return True

def validate_with_tier3():
    """Run TIER 3 validator on all TIER 2 logs."""
    print("\n[VALIDATE] TIER 3 Comparison Matrix")
    print("="*80)

    if not LOGS_DIR.exists() or not list(LOGS_DIR.glob("*_scenario.log")):
        print("✗ No TIER 2 logs found in", LOGS_DIR)
        return

    import subprocess

    results = {}
    for civ in ANW_CIVS:
        log_file = LOGS_DIR / f"{civ.anw_token}_scenario.log"

        if not log_file.exists():
            results[civ.anw_token] = {"status": "MISSING"}
            continue

        # Run TIER 3 validator
        try:
            result = subprocess.run(
                [sys.executable, "tools/validation/validate_tier3_gameplay.py", str(log_file), civ.anw_token],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                results[civ.anw_token] = {"status": "PASS"}
            else:
                results[civ.anw_token] = {"status": "FAIL", "stderr": result.stderr[:200]}
        except subprocess.TimeoutExpired:
            results[civ.anw_token] = {"status": "TIMEOUT"}
        except Exception as e:
            results[civ.anw_token] = {"status": "ERROR", "error": str(e)[:200]}

    # Summary
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] in ["FAIL", "ERROR"])

    print(f"\n✓ PASS: {passed}/{len(ANW_CIVS)}")
    print(f"✗ FAIL: {failed}/{len(ANW_CIVS)}")

    if failed > 0:
        print("\nFailed civs:")
        for token, result in results.items():
            if result["status"] != "PASS":
                print(f"  - {token}: {result['status']}")

    # Save results
    result_file = RESULTS_DIR / f"tier3_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_file.write_text(json.dumps(results, indent=2))
    print(f"\n✓ Results saved to {result_file}")

def generate_summary():
    """Generate TIER 2 execution summary."""
    print("\n[SUMMARY] TIER 2 Execution Status")
    print("="*80)

    if not LOGS_DIR.exists():
        print("✗ No TIER 2 logs directory yet. Run --init first.")
        return

    logs = list(LOGS_DIR.glob("*_scenario.log"))
    complete = sum(1 for f in logs if len(f.read_text()) > 100)

    print(f"\nLogs directory: {LOGS_DIR}")
    print(f"Log files created: {len(logs)}")
    print(f"Log files complete: {complete}/{len(ANW_CIVS)}")

    if complete == len(ANW_CIVS):
        print("\n✓ TIER 2 EXECUTION COMPLETE")
        print("  Ready to run: python3 tools/validation/run_tier2_tests.py --validate")
    elif complete > 0:
        print(f"\n⚠ TIER 2 IN PROGRESS ({complete}/{len(ANW_CIVS)} civs tested)")
        print(f"  Remaining: {len(ANW_CIVS) - complete} civs")
    else:
        print("\n⚠ TIER 2 NOT STARTED")
        print("  Follow TIER2_SCENARIO_DESIGN.md to build scenario and run tests")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "--init":
        init_directories()
    elif command == "--check":
        complete = check_log_files()
        sys.exit(0 if complete else 1)
    elif command == "--validate":
        validate_with_tier3()
    elif command == "--summary":
        generate_summary()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
