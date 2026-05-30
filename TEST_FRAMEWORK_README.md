# ANW Comprehensive Test Framework

Exhaustive overnight testing framework for validating all 48 ANW nations' playstyles, visual assets, and gameplay behaviors.

## Overview

This test framework provides a complete solution for:
- **Game Testing**: Run all 48 civs through 6 diverse test scenarios
- **AI Analysis**: Parse AI decision logs and extract playstyle metrics
- **Playstyle Validation**: Compare actual vs. expected civ behaviors
- **Visual Validation**: Pixel-compare screenshots for rendering issues
- **Reporting**: Generate comprehensive HTML/JSON reports

## Components

### 1. Test Scenarios (`test_scenarios.json`)

Six diverse scenarios testing different playstyle aspects:

| Scenario | Duration | Focus | Key Metrics |
|----------|----------|-------|-------------|
| **Aggressive Rush** | 5 min | Early aggression | Unit production, military decisions |
| **Economy Boom** | 10 min | Economic expansion | Settlers, resource gathering, age progression |
| **Military Composition** | 15 min | Unit diversity | Infantry/cavalry/ranged ratios |
| **Naval Playstyle** | 10 min | Naval production | Dock building, ship counts, trading posts |
| **Late Game** | 30 min | Long-game strategy | Wonder progress, fortifications, army scale |
| **Trading Post Control** | 8 min | Trade economy | Trading post capture, trade revenue |

### 2. AI Decision Analyzer (`tools/aoe3_automation/ai_decision_analyzer.py`)

Parses Age3Log.txt to extract AI behavioral signals:

```python
from tools.aoe3_automation.ai_decision_analyzer import parse_game_log

metrics = parse_game_log("path/to/match.log", "ANWBritish")
print(metrics.to_dict())
```

**Metrics extracted:**
- Unit production patterns (infantry vs cavalry vs ranged)
- Economic focus (food/gold/wood priority)
- Age progression timing
- Strategic decisions (rush, boom, naval, trade, defense)
- Military building counts
- Naval activity indicators
- Tech tree progression

### 3. Matrix Runner (`tools/aoe3_automation/matrix_runner_anw.py`)

Orchestrates game tests across all civs and scenarios:

```bash
# Full matrix (all 48 civs, all scenarios)
python3 tools/aoe3_automation/matrix_runner_anw.py --all-civs --all-scenarios

# Sample (2 civs × 2 scenarios)
python3 tools/aoe3_automation/matrix_runner_anw.py --sample

# Specific civs
python3 tools/aoe3_automation/matrix_runner_anw.py --civ ANWBritish --civ ANWFrench --all-scenarios
```

**Features:**
- Runs games via existing automation infrastructure
- Captures screenshots at: 0s, 1min, 3min, 5min, end
- Logs AI decisions per civ
- Monitors for crashes/errors
- Creates per-civ trace files
- Checkpoints progress every 5 matches
- Generates HTML/JSON reports

### 4. Playstyle Validator (`tools/validation/validate_playstyles.py`)

Validates playstyles against specifications:

```bash
python3 tools/validation/validate_playstyles.py /var/home/jflessenkemper/artifacts/anw_matrix/anw_matrix_20260507_120000_abc12345
```

**Validation rules:**
- Unit production rate (units/minute)
- Age progression timing
- Economic activity level
- Unit diversity (unique unit types)
- Military composition (dominant unit percentage)
- Conformance to `PLAYSTYLE_SPECIFICATIONS.json`

**Output:**
- `validation_report.json`: Detailed results per civ
- `validation_report.html`: Visual report with pass/fail status

### 5. Visual Validator (`tools/validation/validate_visuals.py`)

Validates screenshot rendering quality:

```bash
python3 tools/validation/validate_visuals.py /var/home/jflessenkemper/artifacts/anw_matrix/anw_matrix_20260507_120000_abc12345
```

**Checks:**
- Civ names display correctly (via heuristics)
- UI elements render (toolbar, panels)
- No massive black regions (asset corruption)
- Screenshot file integrity
- Image size and format validity

**Output:**
- `visual_validation_report.json`: Issues per screenshot
- `visual_validation_report.html`: Visual report
- `visual_mismatches/`: Detailed issue analysis

### 6. Master Test Runner (`comprehensive_test.sh`)

Orchestrates complete test workflow:

```bash
# Full overnight run (14-18 hours)
./comprehensive_test.sh --all

# Quick test (30 minutes)
./comprehensive_test.sh --sample

# Only validation (no games)
./comprehensive_test.sh --validate-only

# Resume from checkpoint
./comprehensive_test.sh --resume /path/to/artifact_dir
```

## Playstyle Specifications

Reference file: `PLAYSTYLE_SPECIFICATIONS.json`

Defines expected behaviors for each civ:
- Unit focus (expected unit types)
- Economic focus (food/gold/wood priority)
- Naval capability
- Wall building tendency
- Trading focus
- Rush viability
- Tech tree investment

Example:
```json
{
  "civ_name": "British",
  "civ_token": "ANWBritish",
  "unit_focus": ["redcoat", "musketeer", "dragoon"],
  "economic_focus": "balanced",
  "naval_capable": true,
  "trading_focused": true
}
```

## Quick Start

### Minimal Setup
```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World

# Verify prerequisites
python3 tools/aoe3_automation/matrix_runner_anw.py --help

# Run sample test
./comprehensive_test.sh --sample
```

### Full Overnight Run
```bash
# Start test (12+ hours)
./comprehensive_test.sh --all 2>&1 | tee test_run.log &

# Monitor progress
tail -f test_run.log

# Check artifacts periodically
ls -lt /var/home/jflessenkemper/artifacts/anw_matrix/ | head -5
```

### Validate Results Without Playing Games
```bash
# If games already ran
./comprehensive_test.sh --validate-only

# For specific run
python3 tools/validation/validate_playstyles.py <artifact_dir>
python3 tools/validation/validate_visuals.py <artifact_dir>
```

## Output Structure

```
/var/home/jflessenkemper/artifacts/anw_matrix/
├── anw_matrix_20260507_120000_abc12345/          # Run artifact root
│   ├── run_report.json                           # Game test metadata
│   ├── run_report.html                           # Game test HTML report
│   ├── SUMMARY.txt                               # Quick summary
│   ├── validation_report.json                    # Playstyle validation
│   ├── validation_report.html                    # Playstyle HTML report
│   ├── visual_validation_report.json             # Visual validation
│   ├── visual_validation_report.html             # Visual HTML report
│   ├── COMPREHENSIVE_SUMMARY.md                  # Full summary
│   ├── ANWBritish_aggressive_rush_test/          # Per-civ-scenario
│   │   ├── match.log                             # AI decision log
│   │   ├── screenshots/
│   │   │   ├── screenshot_00_0s.png
│   │   │   ├── screenshot_01_60s.png
│   │   │   └── ...
│   │   └── metrics.json                          # Parsed metrics
│   ├── ANWBritish_economy_boom_test/
│   └── ...
│   └── checkpoint.json                           # Progress checkpoint
```

## Performance Expectations

| Test Mode | Civs | Scenarios | Duration | Machine |
|-----------|------|-----------|----------|---------|
| Sample | 2 | 2 | ~30 min | Any |
| Fast | 48 | 2 | ~6 hours | Any |
| Medium | 48 | 4 | ~10 hours | Any |
| Full | 48 | 6 | ~14-18 hours | Any |

Times assume:
- ~7-10 minutes per game (game speed: Fast)
- ~1-2 minutes per civ for analysis
- ~2-3 minutes for validation

## Integration with Existing Tools

### aoe3_ui_automation
- Uses existing game launching and screenshot capture
- Leverages xdotool and gamescopectl
- Coordinates with log_capture.py for per-match logs

### log_capture.py
- Snaps log file offsets before matches
- Extracts per-match log content after resign
- Ensures developer mode is enabled (user.cfg)

### Migration Tools (anw_token_map.py)
- Provides authoritative list of 48 ANW civs
- Maps civ tokens to display names
- Used by matrix runner for civ iteration

## Customization

### Add New Scenario
1. Edit `test_scenarios.json`
2. Add scenario with id, name, map, timing
3. Define expected_behaviors and key_metrics
4. Matrix runner auto-picks up on next run

### Modify Playstyle Specs
1. Edit `PLAYSTYLE_SPECIFICATIONS.json`
2. Update unit_focus, economic_focus for civ
3. Validator uses specs for next validation run

### Add Validation Rule
1. Edit `tools/validation/validate_playstyles.py`
2. Add rule to `_create_validation_rules()`
3. Define metric name, expected range, threshold

## Troubleshooting

### Game Tests Won't Run
```bash
# Check prerequisites
python3 -c "from tools.migration.anw_token_map import ANW_CIVS; print(len(ANW_CIVS))"

# Verify game is running
ps aux | grep -i aoe3

# Check log capture path exists
ls /var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age\ of\ Empires\ 3\ DE/Logs/
```

### Low Confidence Scores
- Not enough log entries parsed
- Game logs not captured properly
- Developer mode not enabled in user.cfg
- Check `log_entries_parsed` in metrics

### Validation False Negatives
- Playstyle spec missing for civ
- Expected range too narrow
- Add civ to PLAYSTYLE_SPECIFICATIONS.json

### Visual Issues Not Detected
- PIL not installed (`pip install Pillow`)
- Screenshot files corrupted
- Check file sizes in visual_validation_report.json

## Advanced Usage

### Resume Interrupted Run
```bash
# If test was killed at match N/M
./comprehensive_test.sh --resume /path/to/artifact_dir

# Or manually continue from checkpoint
python3 tools/aoe3_automation/matrix_runner_anw.py --resume <run_id>
```

### Export Metrics for Analysis
```bash
# Extract all metrics to CSV
python3 << 'EOF'
import json
from pathlib import Path

artifact_dir = Path("/var/home/jflessenkemper/artifacts/anw_matrix/anw_matrix_*")
run_dir = list(artifact_dir.parent.glob(artifact_dir.name))[-1]

with open(run_dir / "run_report.json") as f:
    report = json.load(f)

for result in report['results']:
    metrics = result.get('metrics', {})
    print(f"{result['civ_token']},{metrics.get('avg_units_per_minute', 0):.2f}")
EOF
```

### Generate Custom Report
```python
from pathlib import Path
from tools.validation.validate_playstyles import PlaystyleValidator

validator = PlaystyleValidator()
report = validator.validate_matrix_run(Path("/var/home/jflessenkemper/artifacts/anw_matrix/anw_matrix_..."))

# Access report data
print(f"Overall pass rate: {report.overall_pass_rate*100:.1f}%")
for civ_report in report.civ_reports:
    if civ_report.overall_status.value == "fail":
        print(f"{civ_report.civ_name}: {civ_report.mismatches}")
```

## Notes

- All paths use absolute paths for stability
- Test framework is idempotent (safe to re-run)
- Checkpoints every 5 matches (resume-safe)
- Reports generated in JSON + HTML for accessibility
- AI analyzer extracts signals without LLM involvement (deterministic)

## See Also

- `/var/home/jflessenkemper/AOE-3-DE-A-New-World/test_scenarios.json` — Scenario definitions
- `/var/home/jflessenkemper/AOE-3-DE-A-New-World/PLAYSTYLE_SPECIFICATIONS.json` — Civ specs
- `tools/aoe3_automation/` — Game automation tools
- `tools/validation/` — Static validation suite
