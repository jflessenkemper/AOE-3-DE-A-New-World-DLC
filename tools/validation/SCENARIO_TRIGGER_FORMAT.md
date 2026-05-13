# Scenario `TR` (Trigger) sub-record format

Authoritative on-disk layout for the trigger section of an
`.age3Yscn` scenario, as observed in AoE3 Definitive Edition.

Reverse engineered from
`Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn` (`BB`, 104
triggers in 11 groups) and cross-checked against
`Scenario/_test_template.age3Yscn` (`TT`, 0 triggers, 1 empty group)
and `Scenario/ANEWWORLD.age3Yscn` (also 0/1).

The companion reader is
[`scenario_trigger_parser.py`](scenario_trigger_parser.py) and it
parses the entirety of `BB` byte-for-byte (no leftover bytes, every
sub-field decoded).

## Conventions

All multi-byte integers are little-endian. Strings come in two shapes:

| Encoding | Layout                                                                 |
| -------- | ---------------------------------------------------------------------- |
| `lpu8`   | `u32 length` (INCLUDING the trailing null) + `length` bytes UTF-8      |
| `lpu16`  | `u32 char_count` + `2*char_count` bytes UTF-16-LE (no trailing null)   |

Note the asymmetry: `lpu8` length covers the null terminator,
`lpu16` length is a char count and the wire has no terminator.

The empty `lpu8` is just `u32 0` (no string bytes, no null).
The empty `lpu16` is just `u32 0`.

## Location

The trigger section is a tagged sub-record embedded in the
zlib-decompressed scenario body:

```
body[off ..]      = 'T' 'R'                ; 2-byte tag
body[off+2 ..]    = u32 payload_size       ; little-endian
body[off+6 ..]    = payload_size bytes     ; payload (see below)
```

There is exactly **one `TR` record per scenario** (validated by
scanning both campaign maps and our two templates). Locate it with
the heuristic in `find_tr_section`: scan for `b'TR'`, verify
`payload_size` fits in the body, and verify the first `u32` of the
payload is `9` (the format version).

## Payload layout

```
TR_payload = TR_header
           + Trigger[trigger_count]
           + TriggerGroupBlock
```

### `TR_header` (20 bytes)

| Offset | Field         | Type | Notes                                          |
| ------ | ------------- | ---- | ---------------------------------------------- |
| 0      | version       | u32  | Always `9` in observed scenarios                |
| 4      | next_id       | u32  | Next trigger id the editor will hand out       |
| 8      | unknown_h2    | u32  | Often equal to a group count or `0`; role TBD  |
| 12     | group_count   | u32  | Number of `TriggerGroup` records that follow   |
| 16     | trigger_count | u32  | Number of `Trigger` records that follow        |

`unknown_h2` is `52` in `BB` and `1` in `TT`/`AW`; not yet decoded.
Re-serialising it verbatim round-trips fine.

### `Trigger` record

```
prefix         : u32[4]               ; (6, trigger_id, ?, ?)
name           : lpu8
parent_id      : i32                  ; -1 = no parent, else parent trigger_id
flags          : u8[5]                ; bitfield (see "Trigger flags")
cond_count     : u32
conditions     : Action[cond_count]
effect_count   : u32
effects        : Action[effect_count]
```

The 4-`u32` `prefix` is the trigger's on-wire header. The first slot
is always `6` (a record-type tag the engine uses to discriminate
trigger blocks from neighbouring sub-records during a forward scan).
The second slot is the trigger id. The third and fourth slots vary
per trigger but look like the editor's last-known counts of
conditions and effects respectively (in `BB`, `prefix[2] == cond_count`
and `prefix[3] == effect_count` for the trigger; this is not a
parser invariant — we trust the trailing `u32` counts).

`parent_id` lets the editor build the parent/child tree in the
trigger pane. `-1` is the root.

The 5-byte `flags` are bitflags: bit positions seen are `0x01`
(probably "enabled"), `0x02`, `0x04`, plus two slots that look like
`run_immediately` / `loop`. We round-trip them verbatim.

#### `Action` record (used for both conditions and effects)

Conditions and effects share an identical on-wire shape. Whether a
particular `Action` block is a condition or an effect is determined
purely by **its position in the trigger** (conditions come before
`effect_count`, effects come after).

```
type_tag       : u32                  ; always 2 in observed data
name           : lpu8                 ; ASCII keyword, e.g. 'Always',
                                      ;   'Move to Unit', 'Fire Event'
display        : lpu8                 ; editor-visible label
param_count    : u32
params         : Param[param_count]
eval_expr      : lpu8                 ; XS bool expression; 'true' for
                                      ;   unconditional firing
xs_count       : u32                  ; number of XS preamble blocks
xs_blocks      : XSBlock[xs_count]
```

For most conditions/effects `eval_expr` is the literal string
`"true"`. Conditions with a real test (e.g. `Army Is Dead`) use an
XS expression like `"trUnitDead()==true"`.

#### `Param` record

```
type_tag       : u32                  ; 2/3/4/8 observed (see below)
name           : lpu8                 ; ASCII, e.g. 'SrcObject', 'EventID'
display        : lpu8                 ; editor-visible label
value_type     : u32                  ; see "value_type" table below
value_count    : u32
[ if value_type == 22:
    extra      : u32                  ; observed as 0
]
values         : lpu16[value_count]
```

Each `lpu16` is one value. For numeric-typed params the engine
parses the UTF-16 text back to int / float (e.g. `'-1'`, `'1.0'`,
`'378'`). For multi-unit selectors (`value_type == 4`) `value_count`
is the number of unit ids selected and each value is the ASCII-in-
UTF-16 form of that id.

##### `Param.type_tag`

| Tag | Meaning                                              |
| --- | ---------------------------------------------------- |
| 2   | Numeric input (e.g. `Damage`, `RunSpeed`)            |
| 3   | Boolean input (e.g. `Active`, `Ignore`)              |
| 4   | Object / string input (units, points, names)         |
| 8   | Signed-integer input (e.g. `EventID`)                |

##### `Param.value_type`

This is the engine's underlying data type. It selects an editor
widget and tells the runtime how to coerce the UTF-16 string.

| value_type | Meaning                                              |
| ---------- | ---------------------------------------------------- |
| 0          | (rare) generic                                       |
| 1          | Trigger id reference                                  |
| 2          | Number (int / float)                                  |
| 3          | Boolean (`"true"` / `"false"`)                         |
| 4          | Unit selector (one or more unit ids)                  |
| 5          | Point on map                                           |
| 6          | Player id                                              |
| 7          | Sound / fade colour                                    |
| 8          | Signed integer                                          |
| 9          | Camera track name                                       |
| 10         | Tech id                                                  |
| 11         | Tech / unit status                                       |
| 13         | Proto-unit                                                |
| 15         | Operator (`==`, `>=`, …)                                  |
| 16         | Status                                                    |
| 17         | Army id                                                   |
| 18         | Camera info                                                |
| 22         | Localized string id; extra `u32 0` between count and value |
| 25         | Objective id                                                |
| 26         | Trade route id                                              |
| 27         | Unit type                                                   |

`value_type == 22` is the one schema-quirk: it inserts a single
`u32 0` between `value_count` and the first value. The value
itself is the localized-string token, e.g. `"{81108}"`.

#### `XSBlock` record

```
code       : lpu8                     ; the XS source line
has_deps   : u8                       ; 1 iff dep_count > 0 (else 0)
dep_count  : u32
deps       : lpu8[dep_count]          ; parameter names referenced
```

XS blocks contain the *expanded* engine command lines that the
editor writes out when the user drops an effect onto a trigger.
Example expansion for a `Move to Unit` effect:

```
xs[0] = "trUnitSelectClear();"
xs[1] = "trUnitSelect(\"%SrcObject%\");"      ; deps = ['SrcObject']
xs[2] = "trUnitMoveToUnit(\"%DstObject%\",%EventID%, ...);"
```

The `%ParamName%` tokens are re-substituted at runtime from the
matching `Param.values`. The `deps` list records which params each
XS line references — this is what the editor uses to highlight
related fields and to refuse to delete a referenced param.

### `TriggerGroupBlock`

Immediately after the last trigger:

```
group_count_block : u32                      ; usually equals
                                             ;   TR_header.group_count
groups            : TriggerGroup[group_count]
```

`group_count_block` is normally equal to `TR_header.group_count`,
but at least one campaign scenario (`age3challenges02.age3Yscn`)
has the in-block count one lower than the header (8 vs 9). The
block count is the authoritative one; the parser warns about the
mismatch and uses the in-block value.

#### `TriggerGroup` record

```
sentinel    : u32                            ; observed as 1
group_id    : u32
name        : lpu8                           ; e.g. 'Ungrouped'
trig_count  : u32
trig_ids    : u32[trig_count]                ; references Trigger.trigger_id
```

`_test_template.age3Yscn` has exactly one group `'Ungrouped'` with
`trig_count = 0`.

## Validated invariants

The parser (`scenario_trigger_parser.py`) enforces / observes:

* every `Action.type_tag` (cond and effect) is `2`
* every `Param.value_type == 22` has `value_count == 1` and the
  extra `u32` is `0`
* the sum of `TR_header (20) + sum(t.size for t in triggers)
  + group_block_size` equals `payload_size`
* in `BB`: 20 + 119587 + 731 = 120338 (= `payload_size`)
* in `TT`: 20 + 0 + 30 = 50 (= `payload_size`)
* trigger ids are strictly increasing in serialisation order

## Open / undecoded

* `TR_header.unknown_h2` — not decoded (round-trips verbatim)
* `Trigger.prefix[2..3]` — appear to be redundant counts; not load-
  bearing for the parser
* `Trigger.flags` — 5 bytes of bitfield; the individual bits have
  not been mapped to editor checkboxes
* `Param.value_type` exotic values (1, 9–18, 25–27): the on-wire
  shape is the same generic `[u32 vcount][lpu16 values]` so the
  parser handles them, but the *meaning* of each value (e.g. which
  registry the id is into) has not been catalogued
* The `XSBlock.has_deps` flag is redundant with `dep_count > 0`;
  the engine likely uses it as a cheap presence check

## How to add a trigger to a clean scenario

Insertion roadmap, used by the (planned) `scenario_trigger_injector.py`:

1. Locate `TR` via `find_tr_section`.
2. Decode the current section, append the new `Trigger` record to
   the list, append its id to one of the groups, bump
   `TR_header.trigger_count` and `TR_header.next_id`.
3. Re-encode `TR_payload` using the layout above (start from
   header, then each trigger, then `group_count_redundant + groups`).
4. Splice the new `TR` record back into the body and re-`zlib`
   compress to produce a fresh `.age3Yscn`.

Trigger records are self-contained — there are no offsets or
pointers from elsewhere in the body. The only cross-reference is
`TriggerGroup.trig_ids -> Trigger.trigger_id`.
