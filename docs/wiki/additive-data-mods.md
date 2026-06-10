# Additive data mods

> DE's mod-XML merge system. A mod ships a small overlay (e.g.
> `civmods.xml`) that is merged into the base game's data tree at engine
> load time, instead of replacing whole files. This is the foundation of
> every `*mods.xml` discussed elsewhere in this wiki.

## Why it exists

Pre-DE, mods replaced whole base files (`civs.xml`, `proto.xml`, etc.).
Microsoft's official guidance:

> "Data mods from before the additive data mod implementation have to be
> replaced after every official update."

DE switched to overlay merging so a mod can ship a 50-line `civmods.xml`
instead of a 200-civ replacement and survive most patches unchanged.

## `mergeMode` attribute

Each overlay element can carry a `mergeMode` attribute. From the
[Microsoft Additive Data Mods support article](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods):

> "valid values being: modify, add, remove and replace. If the
> mergeMode attribute is not present then it will default to modify if a
> matching node can be found in the base data, otherwise add."

| Value | Behaviour |
|---|---|
| `modify` | Merge fields of overlay onto matching base element. Default when match exists. |
| `add` | Append a new element. Default when no match exists. |
| `remove` | Delete the matching base element. |
| `replace` | Replace the matching base element wholesale (drop base fields). |

## Match keys (per element type)

The match key is element-specific and is **not officially published**.
Empirically:

| Element | Match key |
|---|---|
| `<civ>` | child `<name>` |
| `<Tech>` | `name=` attribute |
| `<String>` | `_locID` attribute |
| `<unit>` (proto) | `name=` attribute |

## Overlay file conventions

Most additive XMLs live directly under `<mod>/data/`. What **ANW actually
ships** (verified — `ls data/*mods*.xml`):

```
data/civmods.xml
data/protomods.xml
data/techtreemods.xml
data/randomnamemods.xml
```

The stringtable overlay is the exception: it lives **per-locale** at
`data/strings/<lang>/stringmods.xml` (ANW: `data/strings/english/stringmods.xml`)
— there is **no** top-level `data/stringmods.xml`. See
[stringmods.xml](data-layer/stringmods.md).

The general DE naming pattern is `<basename>mods.xml`, with an optional
`<basename>ymods.xml` sibling that would target the DE patch-y branch
variant. **ANW ships none of those `y` siblings** (no `civmodsy.xml`,
`techtreeymods.xml`, or `protoymods.xml` in `data/`) — they are a DE
convention, not files this mod carries.

## Case sensitivity

**Tag and attribute names ARE case-sensitive at the merge layer.** The
base game uses lowercase tags (`<civ>`, `<name>`, `<main>`); a mod that
uses Capital tags (`<Civ>`, `<Name>`) has its entries silently dropped.
Empirically verified in this repo (the lowercase rewrite restored the
full set of ANW civs — 44 active today — to the picker). See
[case-sensitivity pitfall](modding-pitfalls/case-sensitivity.md).

## Verifying a merge

The engine ships `DebugOutputGameData` (see
[engine merge dump](validation/engine-merge-dump.md)) which writes the
post-merge XML tree to a Temp dir. This is the only Microsoft-blessed
way to confirm what the engine actually parsed.

## Cross-references

- [civmods.xml](data-layer/civmods.md), [stringmods](data-layer/stringmods.md),
  [techtreemods](data-layer/techtreemods.md),
  [protomods](data-layer/protomods.md),
  [homecity](data-layer/homecity.md) — all use this system.
- [XMB binary XML](file-formats/xmb.md) — base files arrive as XMB; the
  merge happens after decode.
- [Engine merge dump](validation/engine-merge-dump.md) —
  `DebugOutputGameData`.

## Known issues

- **Default merge can clobber unintended fields.** When the engine cannot
  find a match it falls back to `add`, which can produce duplicate
  entries (community-suspected mechanism for picker doubling — see
  [picker doubles](modding-pitfalls/picker-doubles.md)).
- **`mergeMode='remove'` does not check dangling references.** If a
  removed civ is still referenced by a homecity or techtree entry, the
  engine does not warn.
- **Multi-mod load-order is undocumented.** Behaviour with two simultaneously-active mods
  that both touch the same element is not specified by Microsoft.

## Open questions

- Whether `mergeMode` cascades to children (does `replace` on a parent
  imply replacement of all child fields, or only declared ones?).
- Whether `mergeMode` is supported on attribute-only diffs.
- Authoritative match-key per element type — Microsoft does not publish
  a per-element rule table.

## Sources

- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods) — canonical.
- [forums.ageofempires.com — DebugOutputGameData stringmods thread](https://forums.ageofempires.com/t/debugoutputgamedata-not-showing-stringmods/225246).
- This repo: case-sensitivity bug verified empirically (2026-05-09 session).
