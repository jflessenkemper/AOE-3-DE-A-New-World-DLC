# Picker doubles

> The same civ appears twice (or twice with subtle variants) in the
> SELECT CIVILIZATION or SELECT HOME CITY picker after enabling a mod
> that touches a base civ. No first-party documentation; community
> diagnoses are partial.

## Symptoms

Two known variants:

1. **SELECT CIVILIZATION picker** shows two tiles for the same civ —
   one base entry, one mod override — when the additive overlay does
   not match the base entry's `<name>` exactly.
2. **SELECT HOME CITY picker** shows two saved profiles for the same
   civ — typically one created from base saved data and one from the
   mod default — when the mod adds a new civ but also touches the
   base civ entry.

## Suspected causes (community)

- **Wrong `mergeMode`.** If the engine cannot find a matching base
  entry, `mergeMode` falls back to `add` and produces a duplicate.
  See [additive data mods](../additive-data-mods.md).
- **Distinct `<civ>` IDs needed.** A rename of base British via a new
  ANW British without suppressing the original.
- **Duplicate `<civsmenu>` or `<civilizationsdef>` entries** in the
  merged tree.
- **Saved profiles persist across mod uninstall**: if the player has
  played base British before installing the mod, the base saved
  profile lingers alongside the new ANW British saved profile.

**No authoritative tutorial documents this specific symptom or a
canonical fix.**

## Mitigations used in this repo

For SELECT HOME CITY doubles, ANW writes suppression entries that
override `<homecityfilename>` to empty for hidden base civs:

```xml
<civ>
  <name>British</name>
  <main>0</main>
  <homecityfilename></homecityfilename>
</civ>
```

Validator: [`tools/validation/validate_no_homecity_doubles.py`](../../../tools/validation/validate_no_homecity_doubles.py).

For SELECT CIVILIZATION doubles, ensure that the overlay's `<name>`
exactly matches the base civ's `<name>` (so the merge resolves to
`modify`, not `add`) and that `<main>` is set explicitly.

## Diagnosing

1. Enable `DebugOutputGameData` (see
   [engine merge dump](../validation/engine-merge-dump.md)).
2. Inspect the merged `civs.xml` in the Temp dump.
3. Look for two `<civ>` entries with the same `<name>` (these will
   surface as picker doubles) or for unexpected entries that should
   have been overridden.

## Cross-references

- [SELECT CIVILIZATION picker](../ui-layer/select-civilization.md).
- [SELECT HOME CITY picker](../ui-layer/select-home-city.md).
- [civmods.xml](../data-layer/civmods.md) — `<main>0</main>` +
  empty `<homecityfilename>` pattern.
- [Case sensitivity](case-sensitivity.md) — separate root cause that
  also produces missing-or-doubled entries depending on direction.

## Open questions

- Authoritative diagnosis from Microsoft.
- The exact rule for "saved profile" creation and cleanup.
- Whether DE prunes saved profiles on mod uninstall.

## Sources

- This repo: empirical observations,
  `civ_binding_verifications/`, `picker_calibration*`.
- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods) — does not document this.
