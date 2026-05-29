# Visual Capture Manifest Schema

Single source of truth shared by:
- `anw_visual_capture_runner.py` (writes captures + manifest)
- `crop_visual_captures.py` (reads manifest, writes crops + thumbs)
- `tools/build_civ_columns.py` (reads manifest, emits column thumbnails)

## Output layout

```
artifacts/validation/visual_art/
  <CIV_TOKEN>/                              # e.g. ANWBritish
    full/
      01_lobby.png                          # full 1920x1080
      02_loading.png
      03_hud.png
      04_homecity_panel.png
      05_tech_tree.png
      06_diplomacy.png
      07_scoreboard.png
      08_esc_menu.png
      09_endgame.png
    crops/
      lobby_portrait.png                    # cropped at native res
      loading_flag.png
      home_city_button.png
      hud_flag_corner.png
      home_city_scene.png
      tech_tree_overview.png
      diplomacy_panel.png
      scoreboard_player_row.png
      esc_menu_player_summary.png
      endgame_flag.png
    thumbs/
      <same names as crops>.webp            # max 256px wide, q=80
    manifest.json
```

```
artifacts/validation/visual_art/allies/
  <ALLY_CIV_TOKEN>/                         # captures FROM host's perspective
    full/
      06_diplomacy.png                      # P1=host, P2=ALLY_CIV_TOKEN
    crops/
      diplomacy_ally_portrait.png           # crop of P2 slot in diplomacy
    thumbs/
      diplomacy_ally_portrait.webp
    manifest.json
```

## `manifest.json` schema

```json
{
  "schema_version": 1,
  "civ_token": "ANWBritish",
  "civ_label": "British",
  "captured_at": "2026-05-18T01:23:45Z",
  "host_perspective": true,             // false for allies/<civ>/ entries
  "host_civ_token": null,                // populated for ally captures: e.g. "ANWBritish"
  "match_id": "anwbritish_2026-05-18_012345",
  "captures": [
    {
      "label": "01_lobby",
      "full_path": "full/01_lobby.png",
      "captured_ms": 1747531200000,
      "ocr_text": null,                 // optional OCR fingerprint for state-verification
      "crops": [
        {
          "name": "lobby_portrait",
          "crop_region": [620, 320, 1300, 920],   // [x0,y0,x1,y1] in source 1920x1080
          "crop_path": "crops/lobby_portrait.png",
          "thumb_path": "thumbs/lobby_portrait.webp"
        }
      ]
    },
    // … one entry per capture
  ],
  "status": "complete"                   // "complete" | "partial" | "failed"
}
```

## Surface inventory (host perspective)

| Label | Trigger | Crop name(s) | Purpose |
|---|---|---|---|
| `01_lobby` | Picker confirms civ at slot P1 | `lobby_portrait` | Civ portrait + civ-name text shown in lobby slot |
| `02_loading` | ~12s after click_play | `loading_flag` | Civ flag + civ-name on loading screen |
| `03_hud` | First clean HUD frame in-game | `home_city_button`, `hud_flag_corner` | HC icon + player flag in top-right HUD |
| `04_homecity_panel` | Click HC icon (~1850, 80) | `home_city_scene` | Full home-city 3D scene with civ flag waving |
| `05_tech_tree` | ESC menu → Tech Tree | `tech_tree_overview` | Tech tree opens, civ-specific units visible |
| `06_diplomacy` | F4 (or Alt+D) | `diplomacy_panel` | Full diplomacy panel (own portrait at top) |
| `07_scoreboard` | Tab | `scoreboard_player_row` | Player row with civ flag + civ name |
| `08_esc_menu` | ESC | `esc_menu_player_summary` | ESC menu showing player list with civ labels |
| `09_endgame` | Resign → View Postgame | `endgame_flag` | Post-game banner with civ flag + leader |

## Surface inventory (ally perspective)

| Label | Trigger | Crop name | Purpose |
|---|---|---|---|
| `06_diplomacy` | F4 with P2=<ally_civ>, allied | `diplomacy_ally_portrait` | P2's civ portrait/flag in the ally row |

## Crop regions (1920x1080 source)

These are the canonical regions. The crop pipeline MUST honour them.
Coordinates are pixel [x0, y0, x1, y1].

```python
CROP_REGIONS = {
    "lobby_portrait":            (620, 320, 1300, 920),
    "loading_flag":              (760, 380, 1160, 780),
    "home_city_button":          (1790, 50, 1910, 130),
    "hud_flag_corner":           (1660, 8, 1910, 60),
    "home_city_scene":           (0, 0, 1920, 1000),       # near-full frame; flag waving visible
    "tech_tree_overview":        (80, 100, 1840, 980),
    "diplomacy_panel":           (400, 140, 1520, 940),
    "scoreboard_player_row":     (200, 280, 1720, 360),     # row 0 = self
    "esc_menu_player_summary":   (550, 250, 1370, 830),
    "endgame_flag":              (200, 60, 1720, 540),
    "diplomacy_ally_portrait":   (400, 220, 1520, 320),     # row 1 = P2 ally
}
```

Any agent regenerating thumbs must read this table from the manifest's
embedded crop_region, NOT from a hardcoded copy. The capture runner is
the writer of record.

## Resume semantics

A civ is "complete" iff:
- `manifest.json` exists with `status == "complete"`
- Every `crops[].crop_path` exists on disk
- Every `crops[].thumb_path` exists on disk

A `--resume` run skips any civ with status complete.

## Failure modes

- Steam crash mid-match → `status: "failed"`, partial captures kept, runner exits non-zero.
- Picker drift (OCR mismatch) → status: "failed" for that civ, runner moves on to next civ.
- Loading-screen too short to capture → `02_loading` omitted from captures[], status remains "complete" if other captures landed (note in manifest's `warnings: []` list).
