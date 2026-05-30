# Multi-civ mod architecture

> Survey of the largest publicly-documented multi-civ AoE3 mods, their
> structural patterns, and the lessons applicable to ANW. No public mod
> operates at >24 civs.

## Mod-by-mod snapshot

### Wars of Liberty (WoL) — 24 civs

- **Source state**: closed-source. Distributed via aoe3wol.com and
  ModDB. Status: v1.0 ("final") after ~10 years.
- **Engine target**: AoE3 / AoE3:DE (mixed; community discussion
  suggests legacy-AoE3 codebase with DE-compatibility patches).
- **AI ownership**: explicitly partial. Community admission:
  > "Many AI do not work due to all different ways civilizations can
  > age up, and AI scripting is incredibly time consuming and difficult
  > ... Aoe3 had poorly optimized AI code, and the script in which it
  > is written isn't flexible." — WoL ModDB / Wiki.
- **Asset shipping**: full installer that lays out the data tree.
- **Documentation**: Fandom wiki + ModDB news posts.
- Sources: [aoe3wol.com](http://aoe3wol.com/),
  [ModDB](https://www.moddb.com/mods/aoe3wol),
  [Fandom](https://ageofempires.fandom.com/wiki/Wars_of_Liberty).

### Improvement Mod — all base + new

- **Source state**: partial. [`mandosrex/AoE3ImpMod_Base`](https://github.com/mandosrex/AoE3ImpMod_Base)
  GitHub mirror exists but is **archived 2025-02-16** (read-only).
  100% XS by GitHub language stats.
- **Engine target**: legacy AoE3 (TAD-era), not DE-additive.
- **AI ownership**: heavy XS modification across the codebase.
- **Asset shipping**: full data overrides (legacy non-additive).
- **Documentation**: [Blogspot](http://impmod.blogspot.com/p/downloads.html) + Steam group.

### Hundred Days — 11 nations

- **Source state**: open-source, [`aoenw/Hundred-Days`](https://github.com/aoenw/Hundred-Days)
  on GitHub. v0.1.0-beta (Jan 2015), 22 commits, 47 open issues at
  time of survey.
- **Engine target**: AoE3:TAD, not DE.
- **AI ownership**: built on the Napoleonic Era mod codebase.
- **Asset shipping**: traditional `src/`, `test/`, `docs/img/` layout.
- **Documentation**: GitHub wiki + README + issues.

### WoL Maori AI (companion)

- **Source state**: open-source [`thinotmandresy/wol-maori-ai`](https://github.com/thinotmandresy/wol-maori-ai).
- **Scope**: single-civ AI script.
- **Significance**: rare example of an open-source AoE3 AI mod and the
  only documented "future-civ AI scaffold" reference.

## Patterns observed

| Pattern | WoL | ImpMod | Hundred Days |
|---|---|---|---|
| Per-civ data files | yes | yes | yes |
| Per-civ AI script | partial | yes (XS-heavy) | partial |
| Additive `mergeMode` use | unclear (binary distribution) | no (legacy) | no (TAD-era) |
| Public source | no | partial (archived) | yes |
| Issue tracker | Discord/forums | Blog/forums | GitHub issues |
| Versioning | informal v1.0.x | v5.4 series | SemVer-ish v0.1.0-beta |

## Lessons

- **Per-civ AI is the dominant cost.** WoL frames it as "incredibly
  time consuming and difficult."
- **Balance is iterated indefinitely**, not "released":
  > "the mod never stops growing and balancing itself." (WoL paraphrase.)
- **Deck-building / homecity / techtree scope grows superlinearly with
  civs.**
- **No public deck-balancing tooling** documented for any mod.
- **Asset coverage scales linearly with civ count**: each new civ
  needs a flag (DDT + WPF), portrait (DDT + WPF), home-city scene
  (often reused from base), AI personality, civmods entry,
  techtreemods entries (per-age + post-industrial + post-imperial +
  treaty + DM + EmpireWars).

## State of practice for testing / QA

- **Workshop comments + Discord threads are the de-facto bug tracker**
  for most mods. WoL and Improvement Mod use Discord + their own
  forums.
- **GitHub issues** used by `aoenw/Hundred-Days`.
- **Versioning convention is informal**.
- **Beta-test programs**: WoL ran public closed/open beta tracks (per
  ModDB news posts); no formal program documented elsewhere.

> "No authoritative source found for a community-standard release
> checklist or mod-team '100% coverage' doctrine." — `aoe3_mod_full_research.md` §6.

### Testing primitives that DO exist

| Primitive | Authoritative? | Notes |
|---|---|---|
| In-engine Skirmish vs Hard AI | community-standard | AOE3 MC AI guide describes scenario-launch fast iteration |
| Alt+Q AI debugger overlay | community-canonical | AOE3 MC guide |
| `DebugOutputGameData` merged-XML diff | engine-blessed | Microsoft Additive Data Mods doc |
| Replay-based regression | **no authoritative pattern** | Replays exist and can be parsed; no published case as a CI/regression harness |
| External XML/lint validator | **none surfaced** publicly; ANW ships ~80 (see [static gate](validation/static-gate.md)) |
| Engine-blessed scenario validator | **none surfaced** |
| Multiplayer playtesting | community-standard | Discord-driven |

## Cross-references

- [Additive data mods](additive-data-mods.md) — DE's preferred merge
  style; not used by legacy mods.
- [XS scripts](ai-layer/xs-scripts.md) — AI ownership cost.
- [civmods.xml](data-layer/civmods.md) — per-civ data fan-out.
- [Flag rendering](ui-layer/flag-rendering.md) and
  [portrait rendering](ui-layer/portrait-rendering.md) — per-civ
  asset cost.
- [Static gate](validation/static-gate.md) and
  [community tools](community-tools.md) — what does and doesn't
  exist publicly.

## Open questions

- Whether any private mod team operates at >24 civ scale.
- Whether WoL's source will be released post-v1.0.
- Documented contributor onboarding patterns for any of these mods.
- Workshop subscriber counts (unretrievable in our search).

## Sources

- All linked above.
- [AOE3 MC AI guide](https://aoe3mc.github.io/ai-guide/getting-started/).
- [WoL ModDB news](https://www.moddb.com/mods/aoe3wol/news).
- This repo: `aoe3_mod_full_research.md` §1, §3, §6, §8.
