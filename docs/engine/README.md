# AoE3 DE — Embedded XS API Reference

Extracted verbatim from `AoE3DE_s.exe` (build dated 2026-03-18) via
`strings` on the engine's embedded function docstrings. This is the
authoritative 'proxydump' the modding community references — 787 functions
with engine-authored descriptions.

Category counts: kb*=308 (knowledge base), ai*=307 (AI plans/control),
hc*=63 (home city / unit cmds), xs*=49 (language/runtime), +tr* trigger effects.

Source of truth for the smart-walls area API (kbAreaGetType, kbAreaGetBorderAreaID,
kbAreaGroupGetCenter, kbAreAreaGroupsPassableByLand, kbAreaGetNumberTiles, ...)
and for the simulation farm (aiRandSetSeed, kbIsGameOver, aiResign, xsGetTime).

Raw dump: see xs_api_reference.txt (same dir).
