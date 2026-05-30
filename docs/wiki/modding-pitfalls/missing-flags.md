# Missing flags / forward slashes in WPF paths

> Some WPF flag/portrait fields fail to resolve when the path uses
> forward slashes (`/`) instead of backslashes (`\`). Other fields
> appear to accept both. **No authoritative rule documented**; treat as
> engine-behaviour-to-be-probed.

## Symptom

A flag, banner, portrait, or icon does not appear in the picker even
though the file exists at the declared path. Switching `/` to `\` (or
vice versa) makes it appear.

## What we know

- The base game stores Windows-style paths with backslashes inside
  XMB. Filename-override resolution uses `\` separators.
- DE WPF PNG fields (`<homecityflagiconwpf>`, `<smallportraittexturewpf>`,
  `<homecitypreviewwpf>`, `<homecityflagbuttonwpf>`,
  `<postgameflagiconwpf>`) are paths into `resources/images/icons/...`
  and are **community-observed** to behave inconsistently between `/`
  and `\`.
- `.personality` `<icon>` paths in this repo use forward slashes
  (`resources/images/icons/singleplayer/cpai_avatar_*.png`) and work.
- Some civmods WPF fields appear to require backslashes; others accept
  forward slashes.

## Mitigation

When in doubt:

- Use backslashes (`\`) for civmods WPF paths to match base game
  convention.
- Use forward slashes (`/`) for `.personality` `<icon>` paths (matches
  base game).
- If a field fails, try the other slash style before assuming the file
  is missing.

## Status

- **Microsoft documentation**: silent.
- **Community guidance**: anecdotal forum reports.
- **Empirical observation in this repo**: confirmed inconsistent.
- **Authoritative rule per field**: open.

## Cross-references

- [Flag rendering](../ui-layer/flag-rendering.md).
- [Portrait rendering](../ui-layer/portrait-rendering.md).
- [Personality files](../data-layer/personalities.md).
- [Mod folder structure](../mod-folder-structure.md) — path
  conventions.

## Open questions

- Per-field rule for slash direction.
- Whether the engine normalises slashes internally for some fields but
  not others.
- Whether case sensitivity interacts with slash direction (e.g.
  Linux/Proton differences).

## Sources

- This repo: empirical observations.
