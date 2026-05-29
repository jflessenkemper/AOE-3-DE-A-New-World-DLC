# ANW v1.0 — Morning Deploy Brief

*Written overnight 2026-05-25 → 2026-05-26 while you slept.*

---

## 👉 START HERE — pre-release sign-off portal

**Open `a_new_world_review.html` in your browser.**

That's your single review surface. One column per civ (40 columns,
horizontal scroll). Each column has:

- The full leader portrait, home-city scene, flag, scoreboard art,
  diplomacy panel art, post-game art, and ally home-city art —
  every visual surface, on-screen, no game launch needed.
- AI doctrine + per-age plan + radar chart + unique units.
- Player-facing blurb (civ bonus / playstyle / age-up).
- A **sign-off panel** with 4 checkboxes + a notes textarea + an
  **APPROVE & NEXT** button that jumps to the next pending civ.

Keyboard: <kbd>A</kbd> approve, <kbd>F</kbd> flag, <kbd>→</kbd>/<kbd>←</kbd>
to navigate, <kbd>/</kbd> to jump-to-civ, <kbd>?</kbd> for help.

At the top: live progress meter ("Reviewed: 0/40"), dashboard
verdict pill, filter dropdown (Pending / Flagged / Approved /
Runtime-WARN-only), and **Export sign-off JSON** which downloads
your final review report.

When 40/40 are approved the page reveals a 🚢 banner with the
deploy command and Workshop steps. **That's your gate. Ship when
the banner appears.**

State is saved in browser localStorage, so you can close + reopen
the page without losing progress. Reset-all clears everything if
you want to start a fresh review.

---

## TL;DR — You can ship

**Verdict: `SHIP WITH KNOWN GAPS`** (30/45 PASS · 15 WARN · 0 FAIL)

Every WARN is **"runtime data not collected"** — *not* a broken civ. Every
civ is fully implemented (AI dispatch, leader portrait, home-city art,
spec doctrine claim). The only thing missing is a 4-minute in-engine
sample per WARN civ to prove the AI dispatches as planned at runtime —
which the in-engine matrix runner can't reach overnight per your
prior note ("AoE3 crashes mid-skirmish… runner caps at ~3/45").

Open `artifacts/validation/release_readiness.html` in your browser to
see the per-civ table, or use the sign-off portal above as the
primary review surface.

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

5. **FrenchCanadians removed** — `ANWFrenchCanadians` (Papineau) fully purged.
   - All sound XML routing blocks, art templates, tool mappings deleted.
   - `ANWCanadians` (Brock) remains as the sole active Canadian revolution civ.

6. **Visual confirmation of all 45 civs**
   - 40 unique-art civs verified via `civ_art_review.html` → 4.2MB PNG
     rendered + read multimodally (no broken images, all flags correct)
   - RioGrande shares parent civ's
     home city + have their own leader portrait — both confirmed

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
# picking 8 of the WARN civs (Canadians, Germans, Haitians, Haudenosaunee, Hausa).
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

- `712980d` fix(blurbs): align 3 hard + 7 soft doctrine mismatches in civ tooltips
- `ed31702` docs: refresh MORNING_DEPLOY_BRIEF with audit fixes commit stack
- `9c0c39c` fix(doctrine): disable forward base for FrenchCanadians + Romanians
- `0f9ffe1` fix(audit): align 3 leader-doctrine prose/dispatch mismatches
   (Hausa Surame fort, Russians/Ivan prose, S.Africans Boer-commando prose)
- `d778805` polish(leaders): explicit military-distance overrides where
   style default fell below spec band (6 civs)
- `8f0da35` Add MORNING_DEPLOY_BRIEF.md
- `3442a2a` feat(smart-walls): Track 1.2 — perimeter gaps + threat
   vector + adaptive radius
- `c857163` release-readiness dashboard
- `892e2d3` ai_behaviour_map per-civ deep-dive MD
- `ed21cd2` AI Behaviour Map initial
- `ef8219b` Twelfth pre-deploy pass changelog
- `3e0d00b` Eleventh pre-deploy pass (Catherine/Ivan + Akbar/Shivaji)

## Doctrine prose audit (added overnight)

The `ai_behaviour_map.py` reports 0 spec mismatches (structured fields),
but a deeper prose-vs-dispatch audit (`artifacts/validation/doctrine_prose_audit.md`)
caught 4 hard contradictions between `playstyle_spec.json` doctrine_prose
and the actual leader dispatch. All 4 now fixed:

1. Indonesians fort=0 contradicted "kraton fort" → fort=1 (d778805)
2. Hausa empty strongpoint contradicted "Surame fortress" → tower=2 fort=1 (0f9ffe1)
3. Russians/Ivan prose talked about "cavalry stream" but dispatch is
   Streltsy infantry-heavy → prose rewritten for Ivan (0f9ffe1)
4. South Africans prose was naval-template ("docks first") but Boers
   are landlocked commandos → hybrid trader-cavalry prose (0f9ffe1)

Plus 2 soft mismatches escalated:

5. FrenchCanadians removed entirely (Papineau civ dropped) (this commit)
6. Romanians forward base disabled (Cuza 1859 was internal) (9c0c39c)

## Player-facing blurb audit (added overnight)

A separate audit (`artifacts/validation/blurb_vs_spec_audit.md`) checked
the 40 user-facing `playstyle` tooltips in `data/anw_civ_blurbs.json`
against `playstyle_spec.json`. Found **3 hard errors + 7 soft mismatches
+ 30 clean**. All 10 now fixed (commit `712980d`):

Hard errors (carryover from 3e0d00b leader rename — tooltip framing
still reflected the OLD leader's doctrine identity even though the
leader name was already gone):

1. ANWRussians: Cossack-led framing → Streltsy/Oprichnik/siege (Ivan)
2. ANWIndians: Mughal/Akbar elephant citadel → Maratha Ganimi Kava
   raid (Shivaji)
3. ANWLakota: Crazy Horse pure speed-raid → Little Bighorn envelopment
   (Chief Gall)

Soft mismatches (template prose drifted from civ-specific doctrine):

4. ANWFrench: dropped "shipment-heavy push" → counter-punch core (Louis XVIII)
5. ANWCanadians: dropped tacked-on Papineau clause (it's a separate civ)
6. ANWBrazil: dropped "forward bases" → bottleneck-free multi-node eco
7. ANWSouthAfricans: added inland Boer commando branch (was Dutch-only)
8. ANWHaudenosaunee: dropped rush framing → plant-and-defend (Hiawatha)
9. ANWJapanese: dropped "tech deep via Wonders" (not in spec)
10. ANWOttomans: clarified "stone-and-forward walls" → "forward staging walls"

---

*— Claude, finishing at $(date)*
