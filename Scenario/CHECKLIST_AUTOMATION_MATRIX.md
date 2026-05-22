# Checklist Automation Matrix

This file maps the 15-item match checklist in `dutch_napoleon_vs_russia_egypt_checklist.txt` into two groups:

- `Automatable`: can be checked by in-game triggers plus runtime log validation.
- `Manual`: still requires visual judgment from a live observer.

## Short Answer

You cannot reliably test every box with one code command after loading into a match.

What you *can* automate today is the objective rule-path behavior:

- AI non-elite rout bootstrap
- AI rout start, move, and arrival
- elite-support blocked rout
- elite retreat after explorer death

Run this after the scenario or skirmish test finishes:

```bash
tools/validation/run_objective_runtime_checks.sh
```

## Automatable Now

These are already represented by runtime suites in `tools/validation/runtime_specs/legendary_runtime_suites.json`.

### 13. Elite units pull back after explorer death

- Status: `Automatable`
- Runtime suite: `elite_retreat_lane`
- Best setup: Lane B from `Scenario/TEST_SCENARIO_SETUP.md`
- Fast trigger idea: one-button AI explorer kill trigger

### 14. Unsupported AI non-elite units rout while elite-supported units keep fighting

- Status: `Automatable`
- Runtime suites: `ai_rout_lane`, `elite_support_blocks_rout`
- Covered today:
  - AI rout start recorded
  - AI rout move recorded
  - AI rout arrival recorded
  - explicit support-block case logged with `elite_support_blocks_rout`

### 15. AI rout and elite retreat create visible tactical consequences

- Status: `Automatable`
- Runtime suites: `ai_rout_lane`, `elite_retreat_lane`
- Best setup: Lane A and Lane B from `Scenario/TEST_SCENARIO_SETUP.md`

## Manual Today

These boxes are mostly style, timing, composition, or formation-judgment checks. They need either human observation or new instrumentation before they can be machine-validated.

### 1. Dutch feel safer and more positional than Napoleon

- Status: `Manual`

### 2. Napoleon is the side most often starting the main fights

- Status: `Manual`

### 3. Napoleonic France fields meaningful artillery as a core part of assaults

- Status: `Manual`

### 4. Napoleon uses protected elite second-wave pressure rather than throwing elites in first

- Status: `Manual`

### 5. Napoleon keeps his explorer screened during assaults

- Status: `Manual`

### 6. Napoleon sometimes shifts onto an exposed enemy explorer when that explorer is actually near the battle

- Status: `Manual`

### 7. Russia brings the broadest army mass and widest battle line

- Status: `Manual`

### 8. Russia becomes more infantry-heavy and more oppressive from Age III onward

- Status: `Manual`

### 9. Egyptians play more methodically and feel more structured than Russia

- Status: `Manual`

### 10. Egyptians use forts, anchored positions, or artillery-backed structure more than Russia

- Status: `Manual`

### 11. Russia and Egyptians feel different from each other rather than tactically identical

- Status: `Manual`

### 12. All four armies keep their explorers screened instead of leaving them isolated

- Status: `Manual`

## Best Practical Workflow

1. Use `Scenario/ANEWWORLD.age3Yscn` or a stock random map to force the mechanical cases.
2. Add Scenario Editor triggers for reset, respawn, explorer teleport, and AI explorer kill.
3. Run the match long enough to generate `[LLP v=2]` probe markers in `Age3Log.txt`.
4. Run `tools/validation/run_objective_runtime_checks.sh`.
5. Use the checklist text file for the still-manual style and formation boxes.

## If You Want More Boxes Automated

The next step is to add explicit logging for the currently subjective categories, for example:

- log when the AI forms a regular-first / elite-second assault stack
- log when the explorer is assigned behind the escort line
- log when artillery share in an assault exceeds a threshold
- log when an exposed enemy explorer becomes the preferred focus target

Once those markers exist, we can add more suites to `legendary_runtime_suites.json` and extend `run_objective_runtime_checks.sh`.
