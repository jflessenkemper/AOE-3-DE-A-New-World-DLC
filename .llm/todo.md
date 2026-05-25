# ANW Release-Readiness TODO

## STATUS: ✅ COMPLETE — 2026-05-25 (tenth pass: gruesome-portrait fix, Italian Savoy shield, Crazy Horse → Gall string cleanup)

All tracks completed. Mod is deploy-ready. Validators 41/48 PASS, 0 FAIL.
Latest re-run: 2026-05-25 20:05:45.

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
