"""ANW namespace migration tools.

These modules unify the mod's two civ-architectures (base-game-patched + anw)
into a single `ANW{Civ}` namespace where every civ is fully mod-owned. See
`tools/migration/anw_token_map.py` for the canonical 48-civ mapping.

Run order (executed by `tools/migration/run_anw_migration.py`):

  1. anw_token_map.py        — single source of truth (no I/O)
  2. build_anw_civmods.py    — emit 48-block civmods.xml
  3. migrate_strings.py      — rewrite stringmods.xml + randomnamemods.xml
  4. migrate_personalities.py — rename + rewrite all 48 .personality files
  5. build_anw_decks.py      — merge decks_standard.json + decks_legendary.json
                                into decks_anw.json
  6. (manual) update validators in tools/validation/ to drop base/rev branching

Each script supports `--dry-run` (print what would change without writing) and
`--check` (exit non-zero if rerunning would change anything — for CI drift).
"""
