# Scenario Emitter - Player Table Layout

Reverse-engineered from `Scenario/_test_template.age3Yscn` (160 246 B,
md5 `504465a97dff85107f2647fa26937c50`, v105 engine build — recovered
from the retired `legendary-leaders-ai.age3Yscn` binary; the canonical
runtime scenario is now `Scenario/ANEWWORLD.age3Yscn`) and
cross-checked against
`Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn` (8.27 MB, v54).

This document is intended as the authoritative reference for the player /
civ binding region inside an `.age3Yscn` body. For the outer container
(`l33t` magic, zlib stream, BG/FH header, footer) see `/tmp/age3yscn_structure.md`
or the inline docstring at the top of `scenario_emitter.py`.

## TL;DR

The civilization for each AI / human player slot is encoded as the
HomeCity XML filename (e.g. `homecityspanish.xml`, `anwhomecitybritish.xml`)
inside a length-prefixed UTF-16-LE string in a `P5` sub-record of the
slot's `BP` (Bang-Player) record. Patching civ = rewrite that string.
There are 9 BP records: BP[0] = Mother Nature (Gaia), BP[1..8] = the eight
player slots in order.

## BP record layout

A BP (Bang-Player) record has the byte structure:

| Off | Size | Field        | Notes                                                  |
| --- | ---- | ------------ | ------------------------------------------------------ |
| 0   | 1    | flag         | Always `0x01` (slot is populated). Use `\x01BP` as scan needle. |
| 1   | 2    | magic        | `b'BP'`                                                |
| 3   | 4    | size_u32     | u32-LE. Size of `(version + sub-records)`. Patch this whenever a sub-record changes size. |
| 7   | 4    | version      | `0xFC` (252) in v105 LL templates; `0xAC` (172) in v54 BB. |
| 11  | ...  | sub-records  | Concatenated tagged sub-records, each: `tag(2) + u32 size + payload`. |

Total bytes consumed by a BP record = `7 + size_u32`.

The 9 BP records appear contiguously near the end of the player block. In
the LL template they live at body offsets `0x2794e5..0x282a3d`; in BB they
are around `0x6a3f28..0x6ab8b0`. They are NOT at fixed offsets — find them
by scanning for `b'\x01BP'` followed by a sane size and a leading `P1`
sub-tag. (Random `BP` byte sequences appear inside the terrain blob, so
both filters are needed to avoid false positives.)

## Sub-records inside a BP

Observed in order in every BP[1..8] (Gaia uses the same tags but slightly
different payloads):

| Tag | Purpose (best guess)                        | Notes |
| --- | ------------------------------------------- | ----- |
| P1  | Player meta (name, id)                      | LP-UTF16 name + 4-byte civ-stub of `ff ff ff ff`. Civ is **not** here. |
| P2  | Diplomacy / team relations                  | 16 bytes of `0xff` (per-player relation matrix). |
| P3  | Knowledge / starting tech graph             | Repeats of `KB...`, `K8...`, `K%...`, `Q!...`, `T%...`, etc. |
| P4  | Single byte (probably "has tech tree" flag) | Always `00` in LL/BB templates. |
| **P5** | **HomeCity binding (the civ pointer)**   | **See below — this is what the emitter rewrites.** |
| P6  | Resource start values?                      | `10 00 00 00 02 00 00 00 ...` — looks like initial economy. |
| P7  | 5 zero bytes                                | Unknown. |
| P8  | 34-byte block + `CM` sub-tag                | Possibly camera / minimap defaults. |
| P9  | ~3 KB binary blob                           | Likely starting unit table for the slot. |

We only edit P5. All other sub-records carry their original bytes through
unchanged.

## P5 sub-record layout (the civ binding)

The P5 payload (after the 6-byte `P5 + u32 size` header) is:

```
[ LP-UTF16  hcname        ]   # u32 char_count + UTF-16-LE bytes
  20 fixed bytes:
    01 00 00 00  00 00 00 00
    01 01 01 01  00 00 00 00
    00 00 00 00
[ LP-UTF16  ai_loader     ]   # "" (=u32:0) for human, "aiLoaderStandard" for AI
  18 tail bytes:
    00 00 00 00 00 00         # 6 zeros
    XX XX XX XX               # u32 player_id (1..8 for player slots, 0 for Gaia)
    ff ff ff ff               # i32 = -1 (legacy civ-id field, ignored by engine)
    00 00 00 00               # 4 zero pad bytes
```

The total payload size is therefore:

```
4 + 2*len(hcname) + 20 + 4 + 2*len(ai_loader) + 18
= 46 + 2*len(hcname) + 2*len(ai_loader)
```

For `homecityspanish.xml` + `aiLoaderStandard` (the LL Player 2 case):
`46 + 2*19 + 2*16 = 46 + 38 + 32 = 116` bytes — matches observed.

For `homecityspanish.xml` + `""` (Player 1 = human-controlled):
`46 + 38 + 0 = 84` bytes — matches.

The mid-block 20 bytes and tail 18 bytes are **byte-identical across all
players in both LL and BB templates** (modulo the player_id u32 that lives
inside the tail). They are preserved verbatim by the emitter.

## Civ token -> HC XML mapping

For the 46 ANW civs the rule is exact:

```
ANWBritish           -> anwhomecitybritish.xml
ANWBajaCalifornians  -> anwhomecitybajacalifornians.xml
ANWNapoleonicFrance  -> anwhomecitynapoleonicfrance.xml
ANWUSA               -> anwhomecityusa.xml
...
```

Pattern: `f"anwhomecity{civ_token[3:].lower()}.xml"`. All 46 ANW civs in
`tools/migration/anw_token_map.py` match an XML at
`data/anwhomecity<civ>.xml` (verified).

For vanilla civs the rule is `f"homecity{civ.lower()}.xml"` — note the
LL template uses `homecitygerman.xml` (singular, not `homecitygermans.xml`).

`<HomeCityFilename>` in `data/civmods.xml` is the canonical source for the
exact filename per civ if a mismatch ever arises.

## Length fields to patch on insert / resize

When a P5 hcname or ai_loader changes length by `Δ` bytes, the emitter
patches three length fields:

1. `body[ p5_offset + 2 .. +6 ]`  -- the P5 sub-record's u32 size field
   (size now = `original_size + Δ`).
2. `body[ bp_offset + 3 .. +7 ]`  -- the enclosing BP record's u32 size
   field (size now = `original_size + Δ`).
3. `body[ 2 .. 6 ]`               -- the body's u32 `inner_size`
   (`= len(body) - 7`). Recomputed in `pack_scenario` from the post-edit
   body length, so multiple BP edits accumulate cleanly.
4. `file[ 4 .. 8 ]`               -- the outer `decompressed_size`
   (`= len(body)`). Also recomputed in `pack_scenario`.

The "FH chunk" mentioned in `/tmp/age3yscn_structure.md` lives at body
offset `0x40e00` in BB. It is **before** the player table (which is at
~0x2794e5 in LL, ~0x6a3f28 in BB) so changes to BP records do not
invalidate it. We deliberately do NOT touch its size field.

There is no detected CRC / hash field. The engine relies on `inner_size`
as its only structural integrity check, which is precisely what killed
the v2 builder (`scenario_trigger_builder_v2.py`).

## Failure modes / known unknowns

* **AI personality vs AI loader.** The P5 `ai_loader` string holds an XS
  loader file basename (`aiLoaderStandard`), NOT a civ-specific personality
  file. The mod's per-civ personalities (`game/ai/anwbritish.personality`
  etc.) are picked up by `aiLoaderStandard` at runtime based on the loaded
  HC, *if* `<AINames>` in `data/civmods.xml` and the `.personality` files
  are in sync. The emitter does NOT touch personalities; it only sets
  the HC binding and the loader.

* **Lobby-bound scenarios.** The LL template has every player's "civ_id"
  4-byte field set to `ff ff ff ff` (-1) inside P1; binding flows
  exclusively through P5's HC name. We have NOT verified that vanilla
  campaign scenarios (BB, age3zhb*) use the same convention -- BB does,
  age3zhb1 (HB) appears to use a different / older sub-tag layout (no
  P1/P2/P3 sub-records on its BP hits). For our 46-civ validation use
  case the LL template is the only template we need; reusability with
  other base game templates is unverified.

* **Player count != 8.** We assume 8 player slots + 1 Gaia. The emitter
  raises if it finds fewer than 9 BP records. We have not tested adding /
  removing slots.

* **Other sub-records that reference civ.** P3 (knowledge) starts with
  bytes that look the same across all 9 BP records in LL, suggesting
  starting tech is filled by the engine post-load from the HC binding.
  If a future engine update starts caching civ-specific tech state in P3,
  the emitter will produce mismatched scenarios. The `inspect` subcommand
  in `scenario_emitter.py` can be used to diff P3 across templates if
  needed.

* **In-game load test.** Round-trip via the parser is verified; loading
  the emitted scenarios in the actual game has NOT been verified by this
  agent (the parent task explicitly defers that test).

## Engine "INVALID FILE" investigation log (2026-05-08)

The engine rejects both passthrough variants:
- `_passthrough_LL.age3Yscn` (no trailer, level-6 zlib)
- `_passthrough_LL_with_trailer.age3Yscn` (original 4-byte trailer, level-6 zlib)

Both have decompressed bodies byte-identical to the LL source. Only the
**compressed zlib bytes** differ.

### Survey of all shipped scenarios (78 files in install + profile dirs)

Cross-checked container metadata across all `.age3Yscn` files in the install
ScoreChallenges/Campaigns directories and the user profile dir:

- **Every shipped scenario has a 4-byte trailer.** Trailers are per-file
  unique with no obvious pattern (high bit usually set, e.g. `b7383381`,
  `45069598`, `4e9d6cc5`).
- **All shipped scenarios use `0x789c` zlib header** (CMF=0x78 / FLG=0x9c
  = level-6 default). NONE use 0x789c+raw, 0x78da (level 9), or 0x7801.
- The single exception is `Scenario/ANEWWORLD.age3Yscn` in the profile dir
  (zlib `78da`, no trailer). This is almost certainly the broken
  v2-builder output the user copied — body length matches BB exactly
  (8275691), suggesting it's a corrupted BB rewrite, not an engine-emitted
  file. Treat as untrustworthy.

### Hypotheses ruled OUT

| # | Hypothesis | Result |
| - | ---------- | ------ |
| 1 | Trailer = CRC32(body) LE/BE | No match for LL or BB |
| 2 | Trailer = Adler32(body) LE/BE | No match (and adler32 already lives inside zlib stream) |
| 3 | Trailer = CRC32(compressed) | No match |
| 4 | Trailer = CRC32(file[:start]+body) variants | None match |
| 5 | Trailer = MD5/SHA1 prefix | No match |
| 6 | Trailer = filesize / compressed-len | No match |
| 7 | Trailer = XOR-fold of body u32s | No match |
| 8 | Python zlib could produce identical compressed bytes | No combo of (level 1-9, memLevel 1-9, strategy DEFAULT/FILTERED/HUFFMAN_ONLY/RLE/FIXED) matches LL's compressed output. Engine must use a different zlib build / compressor. |
| 9 | Compressed length stored elsewhere | No length field exists in the 64 bytes preceding the body that matches `compressed_len=160234`. Container has only `outer_size = decompressed_size`. |

### Hypotheses NOT YET ruled in/out (pending engine acceptance test)

The user is testing the candidates in `artifacts/emitted_scenarios/_test_*.age3Yscn`.
Each tests one variable while keeping the body byte-identical to LL.

| Candidate | Variable changed | Tests... |
| --------- | ---------------- | -------- |
| `_test_A_l9_origtrailer.age3Yscn` | level-9 zlib + original trailer | Does the engine accept higher compression with the source trailer? |
| `_test_B_l9_notrailer.age3Yscn` | level-9 zlib, no trailer | Mimics `ANEWWORLD.age3Yscn` exactly (engine emit?) |
| `_test_C_l6_adler32_le.age3Yscn` | trailer = adler32(body) LE | Most plausible "checksum" choice |
| `_test_D_l6_crc32_le.age3Yscn` | trailer = crc32(body) LE | Second most plausible |
| `_test_E_l6_crc32_compressed_le.age3Yscn` | trailer = crc32(compressed) LE | Tests compressed-stream checksum |
| `_test_F_l6_huffman.age3Yscn` | strategy=HUFFMAN_ONLY | Different deflate strategy |
| `_test_G_l6_dup_header_trailer.age3Yscn` | trailer = duplicate l33t header | Some games store sentinel at end |
| `_test_H_l6_filesize_trailer.age3Yscn` | trailer = u32 file size | Sentinel-as-self-size pattern |
| `_test_I_l6_zero_trailer.age3Yscn` | trailer = 4 zero bytes | Tests "any 4 bytes valid" |
| `_test_K_l6_filtered.age3Yscn` | strategy=FILTERED | Different deflate strategy |
| `_test_L_l6_mem9.age3Yscn` | memLevel=9 | Higher memLevel changes block boundaries |
| `_test_M_byte_clone_of_LL.age3Yscn` | byte-for-byte copy of LL.age3Yscn | **CRITICAL SANITY CHECK** — if engine rejects this, the issue is environmental (Steam Cloud, file path, file watching) not file format. |

### Strongest current hypothesis

The trailer values are non-deterministic and per-file unique, so they are
**likely a hash of compressed-stream-plus-something or just uninitialized
buffer bytes that the engine ignores**. The fact that level-6 with
original-trailer was rejected suggests the engine cares about something
ELSE — possibly:

1. **Zlib encoder fingerprint mismatch.** The engine may parse the
   compressed stream, then validate that re-compressing yields identical
   bytes. (Unlikely — extreme.)
2. **Steam Cloud / file-watching desync.** The user's `_passthrough` files
   may have been picked up before Steam Cloud finished syncing, or the
   file's mtime is stale. Test M will rule this in/out.
3. **Mod / Workshop manifest dependency.** ANW scenarios may need to be
   listed in a separate manifest the engine consults before allowing load.
   Out of scope for binary-only investigation.

### Recommended next step after engine test

If candidate **M** (byte-clone) is also rejected, the engine's "INVALID
FILE" error is not about the binary contents at all — investigate
filesystem / mod manifest issues. If only some non-M candidates load,
the differing variable identifies the integrity check.

---

## 2026-05-08 Engine Acceptance Investigation Log

After the emitter was producing valid binaries (16/16 round-trip + length-invariant tests), engine STILL rejected output as "INVALID FILE". Hours of black-box hypothesis testing produced no working candidate.

### Hypotheses TESTED and DISPROVEN

1. **Trailer bytes are required.** Working scenarios have a 4-byte trailer after the zlib stream end-marker (LL: `b7 38 33 81`, BB: `45 06 95 98`). Hypothesis: emitter strips them. Test: re-pack LL with trailer preserved verbatim → still rejected. **DISPROVEN.**

2. **Trailer is body-content-dependent (CRC/checksum).** Tested CRC32(body), CRC32(compressed), Adler32(body), file-size encoded as trailer, all-zero trailer, duplicated header trailer, file-size LE trailer. **DISPROVEN — no algorithm matches.**

3. **Engine requires specific zlib encoder parameters.** Tested level 1-9 × memLevel 1-9 × strategies (DEFAULT/FILTERED/HUFFMAN_ONLY/RLE/FIXED) — Python zlib cannot produce identical bytes to LL's stream under ANY combination. **DISPROVEN — engine uses a different deflate encoder, but accepts python-zlib output IF the file is "registered" somehow.**

4. **Steam Cloud `remotecache.vdf` SHA1 manifest gates load.** `remotecache.vdf` lists each scenario with `size`, `sha`, etc. The two scenarios that loaded (legendary-leaders-ai, ANEWWORLD) are registered there; our test files are not. Test: with Steam Cloud disabled (Steam UI), edit vdf to add an entry for `_test_M_byte_clone_of_LL` (byte-identical to LL, same SHA1), `chmod 444` to prevent Steam overwriting, launch game, verify entry survived. **Entry survived. Engine STILL rejected. DISPROVEN.**

### Hypotheses NOT yet tested

A. There's a **second integrity manifest** elsewhere (Steam Workshop file? engine-internal hash registry? Wine prefix sandbox metadata?) we haven't found.

B. The engine performs a **runtime hash check via Steam API** (not just local files) — would explain why `_test_M_byte_clone_of_LL` is rejected even though byte-identical to a working file.

C. Mod-state-dependent rejection: the **active mod's `civmods.xml`** may overlay base civs in a way that makes scenarios referencing `homecityspanish.xml` invalid even though the XML is in the base game `.bar`. Test: load LL itself by clicking it in the picker — if THAT also fails with INVALID FILE, the engine genuinely can't resolve the player table's HC bindings under the active mod, and the emitter is fine. (Test was run but result was ambiguous: no INVALID FILE dialog appeared but the scenario also didn't apply player slots — possibly the click missed the row.)

D. **Filename pattern** validation (e.g. underscore-prefix rejection, length cap). All our test files have `_` or `ANW_` prefix; LL doesn't. Test: rename a candidate to `MyScenario.age3Yscn` (no underscore) and try.

### What was built (net-positive deliverables)

- `tools/validation/scenario_emitter.py` + `scenario_emitter_tests.py` (16/16 unit tests pass, round-trip, length invariants, all 6 ANW_Coverage scenarios emit cleanly per file-format spec)
- `tools/validation/validate_scenario_binary.py` + `validate_scenario_binary_tests.py` (12/12 tests pass; CLI + library API; can be run on every emitted scenario before install to catch regressions)
- `tools/validation/SCENARIO_EMITTER_NOTES.md` (this file — full BP/P5 layout reverse-engineering)
- `artifacts/emitted_scenarios/_test_*.age3Yscn` (12 candidate variants for engine acceptance testing)
- `artifacts/emitted_scenarios/_test_results.md` (test runner template, audit trail)
- `tools/validation/_test_candidate_emitter.py` (deterministic re-runnable candidate generator)

### Recommended next steps (ordered by tractability)

1. Test hypothesis C: confirm the original LL scenario itself can fully load to in-game in the current ANW-mod-active environment. Either click-and-watch-log, or temporarily disable the ANW mod (toggle off in mod manager), re-cycle, and try LL → if LL loads with mod off but not on, mod-conflict is the real issue and the emitter is fine.
2. Test hypothesis D: emit `Foo.age3Yscn` (no underscore prefix) byte-clone of LL, install, attempt load.
3. If C and D both fail: reverse-engineer the engine's load-time integrity check function in `AoE3DE_s.exe` via Ghidra/IDA. This is research-shaped, ~days, not hours.
4. Pivot to lobby-picker path: `set_civ_by_token_verified` already 80% built in `lobby_driver.py`; OCR-verify civ selection and run real-game per-civ matches. Bypasses the emitter entirely.
