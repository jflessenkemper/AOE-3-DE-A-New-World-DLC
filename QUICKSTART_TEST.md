# ANW Test Framework — Quick Start

## 30-Second Setup

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World

# Run sample test (2 civs, 2 scenarios, ~30 min)
./comprehensive_test.sh --sample
```

## Full Overnight Test

```bash
# Run all 48 civs through all 6 scenarios (14-18 hours)
./comprehensive_test.sh --all 2>&1 | tee test_run.log &

# Monitor in background
tail -f test_run.log
```

## What Happens

1. **Load scenarios** from `test_scenarios.json`
2. **Run games**: Each civ × scenario combination
   - Capture logs and screenshots
   - Parse AI decisions
3. **Validate playstyles**: Compare actual vs. expected behaviors
4. **Validate visuals**: Check screenshots for rendering issues
5. **Generate reports**: HTML + JSON in artifact directory

## Output

```
/var/home/jflessenkemper/artifacts/anw_matrix/anw_matrix_<timestamp>/
├── run_report.html              ← Game test results
├── validation_report.html       ← Playstyle validation
├── visual_validation_report.html ← Visual asset check
├── <civ>_<scenario>/            ← Per-match artifacts
│   ├── match.log                ← AI decision log
│   └── screenshots/
```

Open `run_report.html` in a browser to see results.

## Options

```bash
./comprehensive_test.sh --sample        # 2 civs × 2 scenarios (~30 min)
./comprehensive_test.sh --all           # All 48 civs × all scenarios (~18 hours)
./comprehensive_test.sh --fast          # Skip long scenarios
./comprehensive_test.sh --validate-only # Only analyze (no games)
./comprehensive_test.sh --dry-run       # Print what would run
```

## Troubleshooting

**"Python3 not found"**
```bash
which python3
export PYTHON3=/path/to/python3
./comprehensive_test.sh --sample
```

**"Test scenarios not found"**
Verify `test_scenarios.json` exists in repo root:
```bash
ls /var/home/jflessenkemper/AOE-3-DE-A-New-World/test_scenarios.json
```

**Low confidence scores in metrics**
- Ensure game is running with developer mode enabled
- Check log file at: `~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt`

## Manual Commands

```bash
# Just run game tests
python3 tools/aoe3_automation/matrix_runner_anw.py --sample

# Just validate results (after games ran)
python3 tools/validation/validate_playstyles.py <artifact_dir>
python3 tools/validation/validate_visuals.py <artifact_dir>

# Analyze single game log
python3 tools/aoe3_automation/ai_decision_analyzer.py path/to/match.log <civ_name>
```

## Key Files

| File | Purpose |
|------|---------|
| `test_scenarios.json` | Test scenario definitions |
| `PLAYSTYLE_SPECIFICATIONS.json` | Expected civ behaviors |
| `comprehensive_test.sh` | Master test runner |
| `tools/aoe3_automation/matrix_runner_anw.py` | Game orchestration |
| `tools/aoe3_automation/ai_decision_analyzer.py` | AI behavior extraction |
| `tools/validation/validate_playstyles.py` | Playstyle validation |
| `tools/validation/validate_visuals.py` | Visual asset validation |

## Full Documentation

See `TEST_FRAMEWORK_README.md` for detailed documentation, customization, and advanced usage.

---

**Ready to test?** Run:
```bash
./comprehensive_test.sh --sample
```
