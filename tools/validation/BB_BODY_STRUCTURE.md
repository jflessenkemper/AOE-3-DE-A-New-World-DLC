# Bombard_Brawl Player-Slot Binding Region

Reverse-engineered from
`Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn`
(369 942 bytes on disk, 8 275 691 bytes decompressed body).

All offsets are **decompressed-body coordinates** (call
`body = zlib.decompress(raw[8:])` after stripping the 8-byte l33t header).

The companion patcher that reads/writes these fields is
`tools/validation/scenario_emitter.py` (`find_bp_records`, `P5.parse`,
`set_player_bindings`).

---

## Container layout

```
raw[0:4]   b'l33t'                      magic
raw[4:8]   u32 LE  outer_size           == len(body)  MUST be patched on edit
raw[8:]    zlib-compressed body         (last 4 raw bytes are a trailer signature)
           (trailer must be preserved   engine rejects files without it)

body[0:2]  b'BG'                        top-level tag
body[2:6]  u32 LE  inner_size           == len(body)-7  MUST be patched on edit
body[6:10] u32 LE  version              0x00000036 (54) in BB
body[10:12] b'FH'                       build-info sub-record (editor version string)
body[12:16] u32    FH size = 265
... FH payload (UTF-16 build string) ...
body[0x119:0x11b] b'GT'                player-count sub-record
body[0x11f:0x123] u32  = 7             active non-Gaia player count (BB has 7)
...
body[0x128:0x12a] b'SF'                slot-count sub-record
body[0x12e:0x132] u32  = 8             total non-Gaia slot count (BP[1]..BP[8])
...
body[0x147:0x149] b'SH'                pre-baked homecity states (NOT player binding)
... SH payload ...
body[0x6a3f28...] BP records           player binding region (see below)
```

`pack_scenario()` in `scenario_emitter.py` patches `inner_size` and
`outer_size` automatically.  Callers must also preserve the 4-byte trailer.

---

## Player-count fields

| Field | Body offset | Type | BB value | Meaning |
|-------|-------------|------|----------|---------|
| GT payload[0] | `0x0000011f` | u32 LE | 7 | Active non-Gaia AI slots |
| SF payload[0] | `0x0000012e` | u32 LE | 8 | Total non-Gaia slot count |

These fields are informational and are NOT validated by the engine's load-gate
(empirically: the template with different counts still loads). They should be
kept consistent when adding or removing player slots.

---

## SH block (pre-baked homecity states) — NOT the binding

`body[0x0147]` holds a `SH` sub-record (size 129 240) containing 9 inner SH
slots with pre-saved homecity card state.  These are the civs whose home-city
decks were saved when the scenario was last edited, **not** the runtime civ
assignments.  BB's SH slots:

```
SH[0] Spanish    SH[3] Portuguese  SH[6] Germans
SH[1] British    SH[4] Dutch       SH[7] Ottomans
SH[2] French     SH[5] Russians    SH[8] XPIroquois
```

These do **not** need to be patched when changing player-slot civs.

---

## BP record structure (player-slot binding)

There are exactly **9 BP records** (`\x01BP` sentinel) in BB, one per slot
including Gaia (slot 0).

### Record wire layout

```
body[off+0]      u8   = 0x01                  flag (slot present)
body[off+1:+3]   b'BP'                        tag
body[off+3:+7]   u32  bp_size                 payload size (covers version + sub-records)
                                              MUST be updated when P5 changes size
body[off+7:+11]  u32  version = 0xac (172)    record version
body[off+11 ..]  sub-records                  P1 P2 P3 P4 P5 P6 P7 P8 P9

Each sub-record:
  tag[2] + u32 size + payload(size bytes)
```

### Sub-records of interest

| Tag | Size in BB | Contents |
|-----|-----------|----------|
| P1  | 38–48 B   | `u32 pid` + `u8 flag` + `u32 namelen` + UTF-16 name |
| P5  | 82–174 B  | **civ binding** — see below |
| P8  | 30–603 B  | `u32[0]` + `u32[0]` + `u8 active` + `CM` sub-rec + `u32 pid` |

---

## P5 sub-record — the civ binding

```
P5 payload layout:

  [+0x00]  u32 LE  hcname_charcount        character count (not byte count)
  [+0x04]  UTF-16-LE[hcname_charcount]     homecity XML path  ← CIV BINDING
  [+0x04 + hcname_charcount*2 + 0x00]
           u8[20]  mid_flags               opaque per-slot state (see notes)
  [after mid_flags]
           u32 LE  ai_charcount            character count of AI loader name
  [+4]     UTF-16-LE[ai_charcount]         AI loader name     ← AI BINDING
  [after ai_loader]
           tail bytes (18–66 B)            opaque; contains u32 pid at [+6]
```

**hcname examples** (vanilla civs):
```
'homecityottomans.xml'   'homecityrussians.xml'  'homecityxpaztec.xml'
'homecityjapanese.xml'   'homecitybritish.xml'   'homecityfrench.xml'
'homecitygerman.xml'     'homecityportuguese.xml'
```

**ai_loader**: empty string `''` = human / lobby-assigned; `'aiLoaderStandard'` = AI.

### mid_flags (20 bytes) field map

```
Byte offset  Size  Meaning
[0:4]        i32   slot-active flag: -1 (0xffffffff) for all player slots; +1 for Gaia
[4:8]        u32   team id (BB slot 1 = 3, all others = 0); 0 = solo/unassigned
[8:12]       u32   always 0x01010101 (constant)
[12:16]      u32   always 0x00000000 (constant)
[16:20]      u32   color/lobby-index hint (slot 1 = 99, all others = 1 for BB AI slots)
```

The fields at [8:16] are constant — treat as padding when writing new slots.
The [16:20] field may affect civ-picker UI color assignment; safe to copy from
a known-good slot when creating new bindings.

---

## Annotated slot table (BB, all 9 BP records)

```
Slot  pid  Name           Civ (hcname)                             ai_loader
----  ---  --------       ---------------------------------------- ---------------
0     0    Mother Nature  homecityfrench.xml                       '' (do not edit)
1     1    Player 1       ScoreChallenges\homecitybombardbrawl.xml '' (human)
2     2    Player 2       homecityrussians.xml                     '' (AI - no loader)
3     3    Player 3       homecityxpaztec.xml                      '' (AI - no loader)
4     4    Player 4       homecityjapanese.xml                     '' (AI - no loader)
5     5    Player 5       homecitybritish.xml                      '' (AI - no loader)
6     6    Player 6       homecityfrench.xml                       '' (AI - no loader)
7     7    Player 7       homecityottomans.xml                     '' (AI - no loader)
8     8    Player 8       homecityottomans.xml                     '' (AI - no loader)
```

Note: BB uses blank ai_loader for all slots — the scenario drives combat via
triggers, not the general AI loader.  For the ANW mod, AI-controlled slots
should use `'aiLoaderStandard'`.

---

## Precise body offsets (compact table)

Key offsets for each BP slot in the decompressed body.  All values are
for the ORIGINAL unmodified BB file; offsets shift after any edit that
changes P5 payload size — use `find_bp_records()` to re-locate dynamically.

```
Slot  BP_header    BP_size_fld  P5_sub_hdr   P5_payload   hcname_cnt   ai_cnt       ai_data
  0  0x006a3f28   0x006a3f2b   0x006a43a7   0x006a43ad   0x006a43ad   0x006a43e9   0x006a43ed  (Gaia - DO NOT MODIFY)
  1  0x006a47ed   0x006a47f0   0x006a4dc3   0x006a4dc9   0x006a4dc9   0x006a4e31   0x006a4e35
  2  0x006a5521   0x006a5524   0x006a5d3a   0x006a5d40   0x006a5d40   0x006a5d80   0x006a5d84
  3  0x006a6408   0x006a640b   0x006a6a90   0x006a6a96   0x006a6a96   0x006a6ad4   0x006a6ad8
  4  0x006a7321   0x006a7324   0x006a7a44   0x006a7a4a   0x006a7a4a   0x006a7a8a   0x006a7a8e
  5  0x006a8373   0x006a8376   0x006a8b1c   0x006a8b22   0x006a8b22   0x006a8b60   0x006a8b64
  6  0x006a91e8   0x006a91eb   0x006a9933   0x006a9939   0x006a9939   0x006a9975   0x006a9979
  7  0x006a9ff5   0x006a9ff8   0x006aa6f7   0x006aa6fd   0x006aa6fd   0x006aa73d   0x006aa741
  8  0x006aaddd   0x006aade0   0x006ab252   0x006ab258   0x006ab258   0x006ab298   0x006ab29c
```

`hcname_cnt` = body address of the u32 LP-UTF16 char count for the homecity path.
`hcname_data` = `hcname_cnt + 4`.
`ai_cnt` = body address of the u32 LP-UTF16 char count for the AI loader name.
`ai_data` = `ai_cnt + 4`.

Slot 1 (Player 1) mid_flags note: `mid[4:8]=3` (team 3), `mid[16:20]=99` (color 99).
All other player slots: `mid[4:8]=0`, `mid[16:20]=1`.
Gaia: `mid[0:4]=1` (not -1), all others `mid[0:4]=-1` (0xffffffff).

---

## Hcname → civ mapping (vanilla civs in BB)

| hcname (UTF-16-LE) | In-game civ | Chars |
|---------------------|-------------|-------|
| `homecityottomans.xml` | Ottomans | 20 |
| `homecityrussians.xml` | Russians | 20 |
| `homecityxpaztec.xml`  | Aztecs   | 19 |
| `homecityjapanese.xml` | Japanese | 20 |
| `homecitybritish.xml`  | British  | 19 |
| `homecityfrench.xml`   | French   | 18 |
| `homecitygerman.xml`   | Germans  | 18 |
| `homecityportuguese.xml` | Portuguese | 22 |

ANW civ pattern: `anwhomecity<civlower>.xml`
e.g. `anwhomecitybritish.xml` (22 chars), `anwhomecityrussians.xml` (23 chars).

---

## How to swap Player 2: Russians → ANWBritish + aiLoaderStandard

All fields are LP-UTF16 (u32 char_count + UTF-16-LE data, no null terminator).
When the char_count changes, the P5 sub-record size AND the enclosing BP size
MUST be patched.  `scenario_emitter.replace_sub_payload()` handles this.

### Old P5 payload at `body+0x006a5d40` (94 bytes total):

```
hcname    = 'homecityrussians.xml'    charcount=20   40 UTF-16 bytes
mid_flags = ffffffff 00000000 01010101 00000000 01000000   (20 bytes, preserve verbatim)
ai_loader = ''                        charcount=0    0 bytes
tail      = 00000000 0000 08000000 ffffffff 01000000 24010000 33030000  (26 bytes, preserve verbatim)
```

### New P5 payload (130 bytes):

```
hcname    = 'anwhomecitybritish.xml'  charcount=22   44 UTF-16 bytes
mid_flags = (same 20 bytes as old, copied verbatim)
ai_loader = 'aiLoaderStandard'        charcount=16   32 UTF-16 bytes
tail      = (same 26 bytes as old, copied verbatim)
```

**Size changes:**
```
P5 payload:  94  → 130  (delta = +36)
P5 sub u32:  94  → 130  at body+0x006a5d3c (sub_off+2)
BP size u32: 3808 → 3844 at body+0x006a5524
```

**New hcname field bytes (48 bytes):**
```
16 00 00 00  61 00 6e 00 77 00 68 00 6f 00 6d 00 65 00 63 00
69 00 74 00 79 00 62 00 72 00 69 00 74 00 69 00 73 00 68 00
2e 00 78 00 6d 00 6c 00
```

**New ai_loader field bytes (36 bytes):**
```
10 00 00 00  61 00 69 00 4c 00 6f 00 61 00 64 00 65 00 72 00
53 00 74 00 61 00 6e 00 64 00 61 00 72 00 64 00
```

Use `scenario_emitter.set_player_bindings()` which handles all size patching
automatically — do NOT splice bytes manually.

---

## No personality/aiLoader strings in vanilla BB

A grep for `pPersonality*`, `aiLoader*` in the decompressed body finds
**zero occurrences** (both ASCII and UTF-16-LE).  BB runs all AI via XS
triggers, not the personality system.  All BP P5 `ai_loader` fields are
empty strings.

For ANW scenarios that need the personality system, set `ai_loader` to
`'aiLoaderStandard'` in P5 and ensure the civ's personality file is present
under `AI/Personalities/`.

---

## Invariants that MUST hold after any edit

1. `body[2:6]` inner_size = `len(body) - 7`  — patched by `pack_scenario()`
2. `raw[4:8]` outer_size = `len(body)` — patched by `pack_scenario()`
3. Each BP record's u32 size field at `bp.off+3` must equal the sum of all its
   sub-record sizes (6 header + payload each).  `replace_sub_payload()` patches
   this automatically.
4. Each P5 sub-record's u32 size at `sub.off+2` must equal `len(new_payload)`.
5. The 4-byte trailer from the original file must be appended after the zlib
   stream (pass it as `trailer=` to `pack_scenario()`).

---

## Relationship between BP slot index and in-game player number

BP[0] = Gaia (pid=0)
BP[1] = Player 1 in lobby (pid=1) — first human/AI seat
BP[2] = Player 2 (pid=2)
…
BP[8] = Player 8 (pid=8)

The `pid` is also stored in P1.payload[0:4] and in P8's embedded CM
sub-record at CM.payload[6:10].  When `set_player_bindings()` patches P5,
it skips BP[0] (Gaia) and patches BP[1]..BP[8] in order.

---

*Generated 2026-05-13 by binary analysis of Bombard_Brawl.age3Yscn.*
