# Static gate — offline validators

> ANW ships ~80 offline Python validators in [`tools/validation/`](../../../tools/validation/)
> that run without launching the engine. They cover XML well-formedness,
> cross-reference resolution, asset existence, picker prediction, AI
> personality wiring, and more. The community has no comparable
> open-source validator suite — `DebugOutputGameData` is the only
> Microsoft-blessed validator (see [engine merge dump](engine-merge-dump.md)).

## Validator categories

### XML / data-layer

| Validator | Checks |
|---|---|
| [`validate_xml_well_formed.py`](../../../tools/validation/validate_xml_well_formed.py) | XML well-formedness across mod files |
| [`validate_civmods_ui.py`](../../../tools/validation/validate_civmods_ui.py) | Civmods structure + required UI fields |
| [`validate_civ_loadability.py`](../../../tools/validation/validate_civ_loadability.py) | StatsID / loadability rules |
| [`validate_civ_distinguishability.py`](../../../tools/validation/validate_civ_distinguishability.py) | DisplayName resolution, no name collisions |
| [`validate_civ_tech_resolution.py`](../../../tools/validation/validate_civ_tech_resolution.py) | All tech refs resolve in mod or base |
| [`validate_civ_crossrefs.py`](../../../tools/validation/validate_civ_crossrefs.py) | Cross-references between civmods/homecity/personality |
| [`validate_techtree.py`](../../../tools/validation/validate_techtree.py) | Techtree structure |
| [`validate_protomods.py`](../../../tools/validation/validate_protomods.py) | Protomods structure |
| [`validate_string_resolution.py`](../../../tools/validation/validate_string_resolution.py) | All `_locID` refs resolve |
| [`validate_stringtables.py`](../../../tools/validation/validate_stringtables.py) | Stringtable structure |
| [`validate_no_locid_duplicates.py`](../../../tools/validation/validate_no_locid_duplicates.py) | No duplicate `_locID`s |
| [`validate_no_orphan_xml.py`](../../../tools/validation/validate_no_orphan_xml.py) | No unreferenced XML files |

### Homecity / picker

| Validator | Checks |
|---|---|
| [`validate_civ_homecities.py`](../../../tools/validation/validate_civ_homecities.py) | Per-civ homecity presence and structure |
| [`validate_homecity_assets_exist.py`](../../../tools/validation/validate_homecity_assets_exist.py) | Visual/scene asset paths resolve |
| [`validate_homecity_cards.py`](../../../tools/validation/validate_homecity_cards.py) | Card refs resolve into techtree |
| [`validate_homecity_leader_match.py`](../../../tools/validation/validate_homecity_leader_match.py) | Hero name matches expected leader |
| [`validate_homecity_visuals.py`](../../../tools/validation/validate_homecity_visuals.py) | Visual references valid |
| [`validate_no_homecity_doubles.py`](../../../tools/validation/validate_no_homecity_doubles.py) | Suppression entries override `<homecityfilename>` to empty |
| [`validate_offline_picker.py`](../../../tools/validation/validate_offline_picker.py) | Predicts picker contents from merged civ table |
| [`validate_live_picker.py`](../../../tools/validation/validate_live_picker.py) | Validates against in-engine picker observation |

### AI / personality

| Validator | Checks |
|---|---|
| [`validate_personality_active.py`](../../../tools/validation/validate_personality_active.py) | Personality file structure / fields |
| [`validate_personality_overrides.py`](../../../tools/validation/validate_personality_overrides.py) | Per-civ personality overrides resolve |
| [`validate_xs_scripts.py`](../../../tools/validation/validate_xs_scripts.py) | XS script structure / referenced symbols |

### Assets

| Validator | Checks |
|---|---|
| [`validate_civ_asset_existence.py`](../../../tools/validation/validate_civ_asset_existence.py) | Asset paths in civmods resolve to files |
| [`validate_art_consistency.py`](../../../tools/validation/validate_art_consistency.py), [`validate_art_coverage.py`](../../../tools/validation/validate_art_coverage.py), [`validate_art_pixel_perfect.py`](../../../tools/validation/validate_art_pixel_perfect.py), [`validate_art_visual.py`](../../../tools/validation/validate_art_visual.py) | Art consistency, coverage, pixel comparisons |
| [`validate_playercolors.py`](../../../tools/validation/validate_playercolors.py) | Player color XML |

### Behaviour / playstyle / leader

| Validator | Checks |
|---|---|
| [`validate_civ_behavior.py`](../../../tools/validation/validate_civ_behavior.py) | Civ behaviour expectations |
| [`validate_doctrine_compliance.py`](../../../tools/validation/validate_doctrine_compliance.py) | Doctrine / leader-doctrine compliance |
| [`validate_leader_vs_spec.py`](../../../tools/validation/validate_leader_vs_spec.py) | Leader spec match |
| [`validate_playstyle_modal.py`](../../../tools/validation/validate_playstyle_modal.py), [`validate_playstyles.py`](../../../tools/validation/validate_playstyles.py) | Playstyle modal validation |

### Runtime / engine

| Validator | Checks |
|---|---|
| [`validate_engine_merged_xml.py`](../../../tools/validation/validate_engine_merged_xml.py) | Engine-dumped post-merge XML |
| [`validate_runtime_logs.py`](../../../tools/validation/validate_runtime_logs.py) | Runtime log analysis |
| [`validate_live_mod_install.py`](../../../tools/validation/validate_live_mod_install.py) | Verifies the mod is installed correctly |
| [`validate_packaged_mod.py`](../../../tools/validation/validate_packaged_mod.py) | Packaged mod validation |
| [`validate_scenario_binary.py`](../../../tools/validation/validate_scenario_binary.py) | `.age3Yscn` binary checks |
| [`replay_determinism_validator.py`](../../../tools/validation/replay_determinism_validator.py) | Replay determinism |

### Tier runners

| Runner | Purpose |
|---|---|
| [`validate_tier1_static.py`](../../../tools/validation/validate_tier1_static.py) | Tier 1 static checks |
| [`validate_tier2_scenario.py`](../../../tools/validation/validate_tier2_scenario.py) | Tier 2 scenario checks |
| [`validate_tier3_comparison.py`](../../../tools/validation/validate_tier3_comparison.py), [`validate_tier3_gameplay.py`](../../../tools/validation/validate_tier3_gameplay.py) | Tier 3 comparison / gameplay |
| [`run_all_validators.py`](../../../tools/validation/run_all_validators.py) | Run all and emit a JSON/MD report |

## Cross-references

- [Engine merge dump](engine-merge-dump.md) — runtime complement to
  the static gate.
- [civmods.xml](../data-layer/civmods.md), [stringmods.xml](../data-layer/stringmods.md),
  [techtreemods.xml](../data-layer/techtreemods.md),
  [homecity XML](../data-layer/homecity.md),
  [personalities](../data-layer/personalities.md) — what each
  validator targets.
- [Multi-civ architecture](../multi-civ-architecture.md) — most
  validators were written because no community equivalent exists
  (see "What does NOT exist" in [community tools](../community-tools.md)).

## Open questions

- Whether any private mod-team has equivalent or better validators that
  have not been published.
- Whether Microsoft will ship a first-party mod-validation tool for DE.
