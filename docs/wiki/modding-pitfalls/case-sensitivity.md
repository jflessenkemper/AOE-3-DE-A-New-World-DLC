# Case sensitivity in additive merge

> Tag and attribute names ARE case-sensitive at the additive merge
> layer. `<Civ>` and `<civ>` are NOT treated as the same element. The
> base game uses **lowercase** tags. Mods that use Capital tags have
> their entries silently dropped.

## Symptom

The picker shows base civs only; ANW civs are missing. No error
logged. `DebugOutputGameData` reveals that the post-merge tree
contains the base civs unchanged — the mod's overlay simply did not
match.

## Root cause

The additive-merge match key is element-name + child element. Names
are matched byte-exactly. A mod that ships:

```xml
<Civmods>
  <Civ>
    <Name>British</Name>
    <Main>1</Main>
  </Civ>
</Civmods>
```

does not match the base, which uses lowercase:

```xml
<civmods>
  <civ>
    <name>British</name>
    <main>1</main>
  </civ>
</civmods>
```

The engine treats `<Civ>` and `<civ>` as different element types, so
the overlay is added (default merge mode `add`) under the wrong key
and never collides with the base data — but it also never surfaces in
the picker, which queries by lowercase tag name.

## Fix

Lowercase every tag and attribute name in mod XML to match the base
game:

```xml
<civmods>
  <civ>
    <name>British</name>
    <main>1</main>
    <statsid>BR</statsid>
    ...
  </civ>
</civmods>
```

## Verification

In this repo, switching from Capital to lowercase tags restored the
full set of ANW civs (44 active today) to the picker (verified
empirically, 2026-05-09 session). No intermediate state existed — the
engine either saw all ANW civs (after lowercasing) or none of them.

## Status

- **Microsoft documentation**: not stated.
- **Community forum mentions**: scattered references but no canonical
  doc.
- **Empirically verified in this repo.**

## Cross-references

- [Additive data mods](../additive-data-mods.md) — overall merge
  semantics.
- [civmods.xml](../data-layer/civmods.md) — primary place this bites.
- [stringmods.xml](../data-layer/stringmods.md) — `<String>` and
  `_locID` casing also community-suspected to matter.
- [XMB binary XML](../file-formats/xmb.md) — XMB tag names from the
  base game are lowercase by convention.

## Sources

- This repo: empirical verification (2026-05-09 session).
- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods) — does not document this.
