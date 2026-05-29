# ART_VERIFIER_NOTES

Running notes for the comprehensive ANW pixel-perfect art verifier.
Update incrementally as discoveries are made.

## Sources of truth

| Source                                    | Purpose                                       | Count (first run) |
|-------------------------------------------|-----------------------------------------------|-------------------|
| `a_new_world.html`                        | Reference website (low-res)                   | 3048 `<img>` tags |
| `resources/images/icons/`                 | Static reference icons (PNG)                  | 1441 image files  |
| `art/ui/leaders/`                         | Hi-res mod portraits (PNG/JPG)                | 49 files          |
| `art/buildings/`, `art/units/`            | Mod 3D-asset folders (XML + DDT + JPG)        | (mostly XML)      |
| `data/civmods.anw.xml`                    | Authoritative civ ↔ portrait/flag wiring      | 46 `<Civ>` blocks |
| Deployed mod (`...mods/local/A New World`) | What the engine actually loads                | mirrors source    |

## Civ-count clarifications

`tools/migration/anw_token_map.py` defines **46** ANW civs (one dict, 45 lines
of entries — sort order matches `civmods.anw.xml`'s 46 `<Civ>` blocks).
The richer `tools/migration/anw_mapping.py` is **broken** (references
`AnwCiv` dataclass that doesn't exist anymore) — do not rely on it. Use the
46-entry dict from `anw_token_map`, plus parse `civmods.anw.xml` directly.

## DDS / DDT decoding

In-engine portraits ship as `.ddt` (Ensemble Studios' wrapper around DDS).
Pillow can't open DDT directly. Strategy:

1. **Don't decode DDT for v1.** The high-res *source* PNGs at `art/ui/leaders/`
   are what the engine compiles into DDT, so pixel-perfect verification of
   the *source set* against the *deployed source set* is sufficient for the
   static phase.  We treat `.ddt` as opaque: we hash the bytes and match
   source-file ↔ deployed-file hashes for tamper detection only.
2. For visual rendering verification we don't need to decode DDT either —
   we screenshot the running game and pHash the live framebuffer, then
   compare to a pHash of the **source PNG** (rendered at the same square
   crop). That avoids the DDT decode chain entirely.

If we ever do need DDT pixels: install `imageio[freeimage]` and write a
DDT→DDS shim (DDT has a small header before the standard DDS payload), or
shell out to ImageMagick (Bazzite has it). Deferred.

## HTML → mod image-pair mapping logic

`a_new_world.html` puts each civ in a `<!-- ── CivName ── -->` section.
We parse those section headers and use a hand-curated
`_SECTION_OVERRIDES` map (`art_inventory.py`) to translate the human-readable
section name to the canonical `ANW…` token (e.g. "Argentina" →
`ANWArgentines`).

The HTML uses `class="flag-img"` / `class="portrait-img"` for the canonical
flag and portrait imgs; everything else (deck cards, unit-icons, blurb
ornaments) ends up in `html_extra_imgs[]`.

`civmods.anw.xml` carries the engine's view: `<HomeCityFlagIconWPF>` and
`<HomeCityPreviewWPF>` give the *exact* flag and portrait files the in-game
WPF UI loads. We compare those two paths (post-normalisation) against the
HTML's flag-img/portrait-img to detect drift.

## Inventory first-cut numbers (run 1)

```
civs=46  buildings=0  units=0  ui_elements=12  other_art=98
html_imgs=3048 (linked=2978)  art_files=121  resources_files=1441
```

70 unlinked HTML imgs are mostly:
- shields.io GitHub badges in the README banner
- One stray `art/ui/leaders/hidalgo.jpg` reference outside any civ section
- A handful of generic `Flag_*.png` / `cpai_avatar_*.png` references in
  generic UI explainer rows (not civ-pinned).

That 97.7% link rate is fine for first cut — the missing ones are not civ
art.

## First-run findings (real bugs uncovered)

After implementing the static verifier we ran against the live repo. Real
issues caught (not test artifacts):

1. **JPEG-disguised-as-PNG (10 files in `art/ui/leaders/`).** Examples:
   `san_martin.png`, `barbarossa.png`, `pedro_i.png`, `brock.png`,
   `morazan.png`, `ohiggins.png`, `muhammad_ali.png`, `louverture.png`,
   `kossuth.png`, `canek.png`. They start with the JPEG magic but have
   `.png` extensions. Engine may render them OK on Windows but Pillow and
   strict PNG decoders will fail. **Fix:** rename to `.jpg` or re-encode.
2. **22 civmods `<HomeCityPreviewWPF>` paths point at nonexistent files.**
   Pattern: `resources/images/icons/history/histories/h_pc_<civ>.png` —
   the `histories/` folder doesn't exist anywhere under `resources/`. So
   22/46 ANW civs are pointing the engine at a dead portrait at the
   lobby/HC preview. Affected: ANWBritish, ANWChinese, ANWDutch,
   ANWEthiopians, ANWFrench, ANWGermans, ANWHaudenosaunee, ANWHausa,
   ANWInca, ANWIndians, ANWItalians, ANWJapanese, ANWLakota, ANWMaltese,
   ANWMexicans (rev), ANWOttomans, ANWPortuguese, ANWRussians, ANWSpanish,
   ANWSwedes, ANWUSA, ANWAztecs.
3. **Same 22 civs have the same dead path on `<PostgameFlagIconWPF>`.**
4. **70 HTML images are missing on disk** — most are dev-section portrait
   thumbnails like `cpai_avatar_argentines.png` (no leader suffix). The
   HTML's `dev-thumb` row references a stripped-name avatar that was
   never produced; only the `_<leader>` versions exist.
5. **26 source-vs-deployed mismatches.** When the user re-deployed, some
   files were updated in source but the deployed copy is stale. The
   verifier flags exact byte-mismatches — the user should run their
   deploy script.
6. **HTML ↔ civmods.flag mismatch on 4 civs.** HTML uses one flag PNG
   while civmods uses a different one (e.g. older "_NE" suffix variant
   left in civmods after the HTML migrated to a cleaner name).
7. **23 HTML ↔ civmods.portrait mismatches.** Mostly: HTML uses
   `cpai_avatar_<civ>_<leader>.png` while civmods still points at the
   broken `h_pc_<civ>.png`. Fixing #2 fixes most of these.

Total first run: PASS=1344 WARN=53 FAIL=150.

## Open questions / TODO

- [ ] Are HTML flag images intentionally smaller than the deployed flags? The
  spec says HTML flags are 512×341 — confirm during pHash sweep.
- [ ] Some HTML extra imgs reference paths that may not exist on disk
  (`art/ui/leaders/hidalgo.jpg` etc). Static verifier should flag those.
- [ ] Personality icon path is unused for several civs (`personality_icon_path`
  in spec) — need to walk `game/ai/*.personality` to wire that.
- [ ] `art/buildings/` and `art/units/` are catalog-only (mostly XML); we
  don't pixel-verify them in v1. Future work.
- [ ] Deployed-mod diff: art is identical (same file count); HTML differs by
  bytes (probably trailing whitespace / re-deployment). Static verifier
  should hash-compare HTML imgs deployed vs source.

## UI coordinates (visual phase)

`tools/aoe3_automation/lobby_coords.json` already has skirmish-lobby
coordinates measured 2026-04-28 at 1920×1080.  See `ui_art_coords.json`
in this directory for the per-asset expansion.

### HIGH-confidence coords measured this session (1920×1080)

From `/tmp/aoe3_after_cancel.png` (Single Player Skirmish, 8-player FFA,
default ANW state — P1 = self, P2..P8 = Random Personality):

| Asset                       | x   | y   | w   | h   | What it is                        |
|-----------------------------|-----|-----|-----|-----|-----------------------------------|
| `p1_user_avatar`            | 20  | 160 | 110 |  90 | Steam avatar (NOT mod art)        |
| `p1_civ_flag`               | 575 | 168 | 105 |  82 | P1 chosen-civ flag                |
| `p1_color_swatch`           | 945 | 168 |  70 |  64 | P1 player-color box               |
| `p2_civ_portrait_btn`       | 480 | 274 |  90 |  80 | P2 leader-portrait button         |
| `civ_picker.modal_bg`       |  70 |  30 | 670 | 940 | Civ-select modal extent           |
| `civ_picker.ok_button`      | 215 | 962 |     |     | Confirm picker                    |
| `civ_picker.cancel_button`  | 645 | 962 |     |     | Dismiss picker                    |
| `main_menu.skirmish_button` | 130 | 482 |     |     | (matches lobby_coords.json)       |

### MEDIUM / LOW confidence (not directly measured this session)

* `p2_civ_flag` / `p2_color_swatch` — inferred from row spacing (106px Y delta).
* `p3..p8_*` — extrapolated using the same row spacing.
* `civ_picker.row_flag_icon` — measured-pixels say each picker row is 64px tall
  with the small flag at row_x≈90, but the flag's exact bounding box wasn't
  pHash-validated against a known PNG yet.
* `in_match_hud.*` — LOW confidence; not screenshotted this session because
  doing so would require driving into a match. Refine when we wire up
  `validate_art_visual.py --hud-only`.
* `home_city.civ_flag_banner` — LOW; not screenshotted.

### Visual harness sanity check

Ran `validate_art_visual.py --screenshot /tmp/aoe3_after_cancel.png --civ
ANWRussians --civ ANWBritish --lobby-only`. Output validated the harness:

* `[PASS] p1_user_avatar` — correctly skipped (kind=user_avatar_skip).
* `[FAIL] p1_civ_flag` — correctly flags pHash dist 30-40 between live
  Russian flag pixels and the static ANWBritish/ANWRussians PNG. (For
  ANWRussians, the failure is real: the engine's rendered flag has a
  beveled gold border + drop shadow that the static PNG lacks.)
* `[FAIL] p2_civ_portrait_btn ... expected source missing: h_pc_<civ>.png` —
  caught the same bug as the static verifier (broken civmods path).
* `[PASS] p1_color_swatch` — correctly skipped.

Conclusion: the harness wires up end-to-end. To do a full sweep we'd need
to drive the picker for each ANW civ, but that's deferred. The infrastructure
works.

## Caveats for full 46-civ visual sweep

* The pHash threshold of 8 (PASS) / 16 (WARN) is calibrated for full-image
  comparisons. Live-rendered flags in-engine include gold borders, drop
  shadows, and slight color shifts vs the static PNG. We may need a
  per-asset-type threshold (flags 16/24, portraits 8/16). Tune when the
  full sweep happens.
* Crop boxes need tightening if we want to crop *just* the flag bitmap and
  exclude the gold border / shadow — otherwise pHash will permanently
  rate live-rendering as "different art".
* For portraits, the engine renders portraits at varying sizes depending
  on UI panel; pHash is size-invariant (8x8 DCT) so this is fine.

