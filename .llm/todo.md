# ANW Release-Readiness TODO

## STATUS: ✅ COMPLETE — 2026-05-25 (thirteenth pass: static AI Behaviour Map — review the AI without playing)

All tracks completed. Mod is deploy-ready. Validators **42/49 PASS, 0 FAIL**.
Latest re-run: 2026-05-25 21:26.

**Thirteenth pass (this session)** — new tool + zero-mismatch milestone:

User asked: *"I think we need to build an AI behaviour schema, like a way
to review how the actual ai will play without playing, and you can review
and iterate on a nation, like an AI behaviour map"*.

Delivered `tools/validation/ai_behaviour_map.py`:
- Statically derives the **per-civ AI behaviour schema** from every
  `game/ai/leaders/*.xs` file by parsing the `initLeader*()` block,
  the per-age `rule *` blocks, and the build-style helper defaults.
- Cross-checks each civ against `playstyle_spec.json` claims
  (wall_strategy, expects_forward, expects_naval, expects_treaty).
- Wired into `run_all_validators.py` → suite is now 42/49 PASS.
- Outputs `artifacts/validation/ai_behaviour_map.{json,html,md,png}`:
   - JSON: machine-readable per-civ behaviour
   - HTML: 45-civ side-by-side sortable table with personality colour-
     coding, wall-strategy backgrounds, A1→A5 age timeline strip
   - MD: rollup + per-civ one-row summary table
   - PNG: 2600×5400 headless-Chrome render for multimodal review
- **Result: 0/45 civs have spec mismatches.** Every civ's static
  behaviour (personality, biases, military focus, build style, wall
  strategy, distance multipliers, strongpoint profile, tactical doctrine,
  per-age policy drift) matches its playstyle_spec.json claim.

This is the **"review without playing"** primitive the user asked for:
edit a leader's `init*()` or rule, re-run `python3 tools/validation/ai_behaviour_map.py`,
diff the HTML/JSON to see exactly what changed in the behaviour map.

**Twelfth pass (this session)** — fixes applied:
1. **Reverted procedural flag art** (commit 9509c9e) per user directive:
   *"Don't generate flags or art, ever, find art in the base game we can use."*
   12 PNGs reverted (British/Russian/Ethiopian/Indian × 3 surfaces) +
   `tools/cardextract/repaint_flags.py` deleted. Now shipping base-game
   art: Union Jack, Russian tricolor, Ethiopian tricolor, Maratha Lion+Sun.
   Each flag multimodally re-verified — all show proper heraldry and
   cloth-fold shading.
2. **Aligned 18 anw lobby portrait PNGs** (commits 4400cf8 + 58f737c) with
   their DDT counterparts and `data/civmods.xml` `<smallportraittexturewpf>`
   canonical references. The PNGs were 1.5-2.8KB flat-color text placeholders
   in repo, but the matching DDTs already pointed at real base-game leader
   portraits. Now both render paths source from the same canonical leader:
     anwargentines       → San Martín
     anwbarbary          → Barbarossa
     anwbrazil           → Pedro I
     anwcanadians        → Isaac Brock
     anwchileans         → O'Higgins
     anwcolumbians       → Bolívar
     anwegyptians        → Muhammad Ali
     anwfinnish          → Mannerheim
     anwhaitians         → Louverture
     anwhungarians       → Kossuth
     anwindonesians      → Diponegoro
     anwmayans           → Carrillo Puerto statue (tenth pass)
     anwnapoleonicfrance → Napoleon (canonical napoleonic_france.png)
     anwperuvians        → Santa Cruz
     anwrevfrance        → Robespierre
     anwromanians        → Cuza
     anwsouthafricans    → Kruger
     anwtexians          → Sam Houston
   All DDTs regenerated at 128×128 BGRA32. 4 portraits multimodally
   spot-verified (Louverture, Kruger, Barbarossa, Mannerheim) — all
   recognizable historical leaders.

**Eleventh pass (this session)** — fixes applied:
1. **Flag historical repaint REVERTED** — user directive 2026-05-25:
   *"Don't generate flags or art, ever, find art in the base game that we can use"*.
   All 12 procedurally-generated flag PNGs (Flag_/postgame_flag_/flag_hc_
   for British/Russian/Ethiopian/Indian) reverted to commit 0e2533a
   base-game art (Union Jack, Russian tricolor, Ethiopian tricolor,
   Indian Lion+Sun). `tools/cardextract/repaint_flags.py` deleted.
   The 4 civs were already shipping recognizable base-game flag art —
   procedural overrides were aesthetic-only and out of scope.
2. **3 card anachronism fixes**:
   - HCXPFlorenceNightingale renamed "Florence Nightingale" → "Manor Infirmaries"
     (period-neutral; works for both Elizabeth I British and Brock Canadians decks)
   - ANWOttomans: removed `HCShipBalloons` + `HCXPAdvancedBalloon` cards
     (Montgolfier 1783 anachronistic for Suleiman 1520s)
   - ANWIndians: removed `YPHCMughalArchitecture` card (Shivaji's Maratha
     Confederacy explicitly opposed Mughal architectural conventions);
     also rebranded home-city name "Mughal India" → "Maratha India" (locID 60003)
3. **Catherine/Ivan + Akbar/Shivaji rendering consistency**:
   - `a_new_world.html`: 5 places updated — "Russians — Catherine" → "Ivan the Terrible",
     "Indians — Akbar" → "Shivaji Maharaj", data-name + leader keys
   - `tools/chatquotes/quotes.json` "catherine" block: rewrote 6 quote lines
     to Ivan IV themes (Kazan/Astrakhan sieges, Streltsy, Oprichnik terror)
   - `resources/audio/standard_leader_manifest.json`: leaderName +
     articleUrl + voicePrompt + insults + compliments all switched to Ivan IV
   - `tools/playtest/html_card_decks.json` shivaji block: reverted
     "Akbar" → "Shivaji Maharaj" (engine binding "shivaji" is load-bearing,
     leader_shivaji.xs exists)
   - Engine personality binding "Catherine" preserved (load-bearing, see
     `leader_catherine.xs` header which documents the Ivan IV rebrand)
4. **Oversized lobby portraits resized**:
   - `cpai_avatar_british.png`: 1254×1254 (2.5MB) → 256×256 (136KB)
   - `cpai_avatar_dutch.png`: 1254×1254 (2.5MB) → 256×256 (133KB)
   - Corresponding `.ddt` files regenerated via `tools/cardextract/png_to_ddt.py`
   - All 40 lobby portraits now standardized at 256×256 ≤ 200KB
5. **Hausa + Peruvian flags evaluated, kept as-is**:
   - ANWHausa green Sokoto field with Islamic geometric knot — visually strong
   - ANWPeruvians republic tricolor with coat of arms — historically appropriate

Tenth pass (prior): gruesome portrait fix, Italian Savoy shield, Gall string cleanup.

**Tenth pass (this session)** — fixes applied:
1. **Gruesome ANWMayans portrait replaced**: was Canek-on-the-wheel
   execution scene; now a dignified Caste War rebel statue with machete
   (sourced from orphan ANWYucatan `cpai_avatar_yucatan_carrillo_puerto.png`,
   256×256 RGBA). DDT also regenerated via `tools/cardextract/png_to_ddt.py`
   so the legacy `<smallportraittexture>` path also shows the statue.
2. **Italian flag Risorgimento-accurate**: Savoy cross shield (white
   field, red Greek cross, blue heraldic border) added to all three
   surfaces (`Flag_Italian.png`, `postgame_flag_italian.png`,
   `flag_hc_italian.png`) — composited over the existing wave-shaded
   tricolor via PIL.
3. **Crazy Horse → Chief Gall user-visible strings**: rendered HTML
   site (`a_new_world.html`), card deck JSON
   (`tools/playtest/html_card_decks.json`), audio voice manifest
   (`resources/audio/standard_leader_manifest.json`), and chat-quotes
   display (`tools/chatquotes/quotes.json`) all updated. Engine-binding
   files keep `crazy_horse` filename and `Crazyhorse` personality ID
   (load-bearing; documented in `leader_crazy_horse.xs` header).
4. **Orphan placeholders deleted**: pink-text placeholder PNGs
   `cpai_avatar_anwmayans.png`, `cpai_avatar_anwyucatan.png`, plus
   their stale .ddt artifact `cpai_avatar_anwyucatan.ddt`.
5. **Wavy loading-flag consistency confirmed**: direct multimodal Read
   of all 40 `loading_flag.png` captures — 39 wavy, 1 broken capture
   (ANWBritish — purely a capture-pipeline artifact, gitignored, not
   shipped). The in-game wavy rendering is engine-driven and consistent.
6. **Lobby/HUD/diplomacy/scoreboard cross-civ audit**: 5 reported
   "bugs" were verified to be capture-pipeline artifacts only — every
   live in-game portrait (`cpai_avatar_*.png` in `resources/images/`)
   renders correctly. La Valette is in Hospitaller robes; Usman dan
   Fodio shows Sokoto dignitaries; Napoleon Imperial Guard portrait
   is distinct from Bourbon-French / Robespierre. Nothing ships
   broken.

Ninth pass (prior): SA Vierkleur fix — see
`artifacts/validation/visual_confirmation_2026-05-25_session.md`.

## Completed
- [x] Track 1: Smart walls in aiBuildingsWalls.xs — llDetectChokepointVector,
      water-aware center, llSelectWallType tier-by-age, verifyWallClosure rule
- [x] Track 2: Visual confirmation — all 40 ANW civ portraits + flags pixel-reviewed;
      40/40 PASS; 11 aesthetic anachronisms flagged (user decision, skip by default)
- [x] Track 3: Doctrine compliance — playstyle_modal validator PASS; probes_vs_spec PASS
- [x] Track 4: FrenchCanadians vs LowerCanada — ANWCanadians = playable Province of Canada;
      RvltModFrenchCanadians = revolution state "Lower Canada" (string 494006). No rename needed.
- [x] Flag art: all 40 civs' postgameflagtexture / postgameflagiconwpf /
      homecityflagbuttonset fully audited and corrected (commits 9ea750e → 99c0653 → 503c069)
- [x] ANWRevFrance rollover string (400102) split from ANWNapoleonicFrance (400020)
- [x] modinfo.json date updated to 2026-05-23
- [x] Final validator run: 41/48 PASS, 0 FAIL, 7 SKIP (2026-05-23 13:01:09)
- [x] thumbnail.jpg confirmed present at repo root (175 KB)
- [x] Testing map (RandMaps/anwHubTest.xs) verified complete — v5, no syntax errors,
      7-compartment arena, doctrine probes at T+15/30/60/90s, auto-end T+120s. READY.
- [x] Full 40-civ column site audit: all Strategic Identity + Build Strategy text
      checked against actual XS leader files. 14 critical errors fixed:
      ANWBritish text rewrite, ANWHausa leader identity, ANWIndonesians doctrine label,
      ANWDutch copy-paste removal, ANWNapoleonicFrance wall claims removed,
      ANWPeruvians/Columbians/Indonesians boilerplate de-duplicated, ANWItalians
      Lombards description, ANWMaltese card name, ANWTexians cavalry doctrine added,
      ANWRussians fabricated claims removed + card names corrected, ANWOttomans
      wall claims removed + card names corrected.
- [x] Eighth loop pass (2026-05-25): six low-priority column items fixed
      against rendered Cards sections — ANWGermans Age IV card names,
      ANWSwedes Age I/II card names, ANWFinnish Age I/II card names,
      ANWJapanese + ANWHaudenosaunee shrine wording, ANWHaudenosaunee
      Aenna unit (was fabricated "Aenna Shotgun Rider"), ANWEthiopians
      "Menelik II" sub-header. Validators still 41/48 PASS, 0 FAIL.

## User decisions remaining (all skip by default — ship as-is)
1. LICENSE file (MIT? CC-BY-NC?) — Workshop doesn't require one
2. modinfo.json gameVersion: keep `100.15.x` wildcard or pin to `100.15.59076.0`
3. 11 flag/card anachronisms — aesthetic only, see visual_audit_round2.md
4. Column site historical choices (9 items) — see artifacts/validation/column_site_audit_2026-05-23.md
   Most impactful: ANWHaitians (Toussaint vs Empire), ANWMayans (Canek era), ANWBrazil (Pedro I vs II)
   All are documentation-only; zero gameplay or Workshop deploy impact.

## Long-standing deferred
- [ ] Multi-instance parallelization — analyze cost/benefit first, never implement without confirmation
