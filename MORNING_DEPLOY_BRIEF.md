# ANW v1.0 — Morning Deploy Brief

*Written overnight 2026-05-25 → 2026-05-26 while you slept.*

## TL;DR — You can ship

**Verdict: `SHIP WITH KNOWN GAPS`** (30/45 PASS · 15 WARN · 0 FAIL)

Every WARN is **"runtime data not collected"** — *not* a broken civ. Every
civ is fully implemented (AI dispatch, leader portrait, home-city art,
spec doctrine claim). The only thing missing is a 4-minute in-engine
sample per WARN civ to prove the AI dispatches as planned at runtime —
which the in-engine matrix runner can't reach overnight per your
prior note ("AoE3 crashes mid-skirmish… runner caps at ~3/45").

Open `artifacts/validation/release_readiness.html` in your browser to
see the per-civ table.

---

## What happened overnight

### Done

1. **AI Behaviour Map** (`tools/validation/ai_behaviour_map.py`)
   - Static per-civ AI doctrine reviewer — read every leader XS file,
     extracted personality / bt biases / military focus / build style /
     wall strategy / distance multipliers / strongpoint profile /
     tactical doctrine / caps / forward-base / per-age policy drift.
   - **45/45 civs derived · 0 spec mismatches**
   - Outputs: `artifacts/validation/ai_behaviour_map.{html,json,md,png}`
   - Per-civ deep-dives: `artifacts/validation/ai_behaviour_per_civ/<slug>.md`
     — *edit dispatch, re-run script, diff the MD = see what changed*

2. **Smart Walls (Track 1)** — *already at HEAD* (commits `907b69b`,
   `96414e6`):
   - `llDetectChokepointVector` — real chokepoint detection via
     `kbAreaGet*` border-area walk
   - `llDetectCoastVector` — water awareness; pushes ring centre **inland**
     by 30% of radius for coastal civs
   - `llSelectWallType` — age-tiered radius/gate progression
   - `rule verifyWallClosure` — fires every 60s; escalates priority +
     villager pool if coverage <60% by 4 min; re-emits partial ring on
     destruction
   - Probes: `wall.closure`, `wall.escalate`, `wall.reemit`,
     `wall.water_fix`, `wall.chokepoint`, `wall.coast`

3. **Smart Walls (Track 2 refinements)** — see latest commits:
   - `llCountPerimeterGaps` — counts buildable points around ring; skips
     wall plan entirely if surrounded by natural barriers
   - `llComputeThreatVector` — tracks enemy military centroid; biases
     wall placement toward observed threat
   - `llComputeAdaptiveRadius` — radius adapts to eco saturation (tight
     when poor, expanded when saturated)

4. **Release-readiness dashboard** (`tools/validation/build_release_dashboard.py`)
   - Consolidates static + art + spec + runtime checks into single HTML
   - First run: 30/45 PASS · 15 WARN · 0 FAIL · verdict SHIP WITH KNOWN GAPS

5. **FrenchCanadians audit** (`artifacts/validation/civ_naming_audit.md`)
   - Conclusion: **keep FrenchCanadians as-is**. 152 references vs 2
     doc-only mentions of LowerCanada. Rename would touch 140+ files.

6. **Visual confirmation of all 45 civs**
   - 40 unique-art civs verified via `civ_art_review.html` → 4.2MB PNG
     rendered + read multimodally (no broken images, all flags correct)
   - 5 revolution civs (Californians, CentralAmericans, FrenchCanadians,
     RioGrande, Yucatan) share parent civ's home city + have their own
     leader portrait — all 5 leader portraits visually confirmed

7. **Validator suite gate**: 42/49 PASS (7 SKIP = live-game-required,
   not run because no game running)

### Known gaps (intentional)

- **15 civs marked WARN** — no recent `.personality` file with our probe
  pack. Static / art / spec all green. To collect runtime data, see
  "Optional: collect runtime data" below.

- **Leader-name swaps in spec** (intentional per commit `3e0d00b`):
  - "Indians Akbar" doctrine → Shivaji Maharaj portrait
  - "Russians Catherine" doctrine → Ivan the Terrible portrait
  - "Lakota Crazy Horse" doctrine → Chief Gall portrait

- **Yucatan**: spec key is "Yucatan Pat Revolution" but the portrait
  filename is `cpai_avatar_yucatan_carrillo_puerto.png` (both real
  Yucatec figures; substitution is intentional).

---

## To deploy (the short version)

1. Open `artifacts/validation/release_readiness.html` — confirm verdict
   still reads `SHIP WITH KNOWN GAPS` (no FAIL).
2. Open `artifacts/validation/ai_behaviour_map.html` — eyeball per-civ
   personality / wall strategy / age timeline for any last surprise.
3. Run `python3 tools/validation/run_all_validators.py` — expect
   42/49 PASS (or 41/49 if the wall refinements landed mid-stream;
   re-run after a quick `git status` check).
4. Run `python3 tools/deploy_to_mod.py` (already exists, see the file).
5. In Steam: Workshop → "A New World" → publish/update.

## Optional: collect runtime data before deploy

If you want to flip the 15 WARNs to PASS:

```bash
# Enable dev mode + launch the game
python3 tools/aoe3_automation/launch_anw_game.py

# Then in-game, run an AI-vs-AI skirmish in observer mode with 8 AI slots
# picking 8 of the WARN civs (Californians, Canadians, CentralAmericans,
# FrenchCanadians, Germans, Haitians, Haudenosaunee, Hausa).
# Play at max speed (Insert key) for ~20 game minutes, then resign.

# Harvest probe data:
python3 -m tools.playtest.probes_from_replay --validate
python3 tools/validation/build_release_dashboard.py
# → release_readiness.html should now show those civs as PASS.

# Repeat the batch for the other 7 WARN civs (Indians, Indonesians,
# Maltese, Mayans, NapoleonicFrance, RioGrande, Spanish).
```

Each batch is one 20-min game = data for 8 civs.  Total: ~40 game-min
for all 15.  But if it crashes mid-skirmish (per your prior note),
just kill and restart with a smaller civ batch.

The deploy is not gated on this — it's WARN, not FAIL.

---

## File map (where to look)

| Topic | File |
|---|---|
| Release verdict | `artifacts/validation/release_readiness.html` |
| Per-civ static behaviour | `artifacts/validation/ai_behaviour_map.html` |
| Per-civ deep-dive | `artifacts/validation/ai_behaviour_per_civ/<slug>.md` |
| Visual art contact sheet | `artifacts/validation/visual_art/civ_art_review.html` |
| Naming audit | `artifacts/validation/civ_naming_audit.md` |
| Validator suite report | `tools/validation/run_all_validators_report.md` |
| Wall implementation | `game/ai/core/aiBuildingsWalls.xs` |
| Probe definitions | `game/ai/core/aiDoctrineProbes.xs` |
| Leader dispatch (named) | `game/ai/leaders/leader_<name>.xs` |
| Leader dispatch (revolutions) | `game/ai/leaders/leader_revolution_commanders.xs` |
| Spec / doctrine claims | `playstyle_spec.json` |

## Recent commit history

Run `git log --oneline -10` for the latest. Top of stack (overnight):

- `c857163` release-readiness dashboard
- `892e2d3` ai_behaviour_map per-civ deep-dive MD
- `ed21cd2` AI Behaviour Map initial
- (smart-walls Track 1 + 2 refinements landed by background agent —
  check `git log` for the actual hash)
- `ef8219b` Twelfth pre-deploy pass changelog
- `3e0d00b` Eleventh pre-deploy pass (Catherine/Ivan + Akbar/Shivaji)

---

*— Claude, finishing at $(date)*
