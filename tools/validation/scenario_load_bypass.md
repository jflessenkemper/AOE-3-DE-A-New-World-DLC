# Scenario Load Bypass — Investigation

**Status:** static-RE blocked by binary protection; pivoting to runtime bypass.
**Target:** `/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe`
**Symptom:** all custom & original scenario loads end with `INVALID FILE` dialog. Age3Log: `PreGame XXX: Unlock Error - Inventory Extended:-1`. Random skirmish works (mod loads OK).

## TL;DR — Executive summary

1. **`AoE3DE_s.exe` ships with its `.text` sections encrypted/obfuscated on
   disk** (Shannon entropy 7.99/8.0; entry point + every `.pdata`-listed
   function start disassembles to garbage). Both `.text` sections show this
   pattern. Code is decrypted at process start by an unpacker stub.
2. As a direct consequence: **no string in the binary, including the
   `Unlock Error - Inventory %s%d` format string, has any statically
   discoverable RIP-relative or absolute reference**. Even `BugSplat` and
   `STEAMUSERSTATS_INTERFACE_VERSION011` show zero static refs. The
   references exist only after runtime decryption.
3. Therefore **a static binary patch is not a viable plan** without
   first dumping the unpacked process from memory, then locating the gate,
   then patching, then evading the protector's integrity-check guards. That
   work is well beyond the time budget here.
4. **No config-flag bypass is visible on disk either.** None of:
   `noinventory`, `bypassinventory`, `skipinventory`, `nodrm`, `skipsignature`,
   `nointegritycheck`, `disableinventory`, `forceunlock`, `unlockall`,
   `freeplay`, `nochecksum`, etc. exist in the binary. A few related-looking
   tokens DO exist (`forcePatchDataVersion`, `disableDataPatch`,
   `disableDataPatchUpdate`, `SKIPVIDEO`, `forceGameMode`) but none look like
   inventory bypasses, and even if they did, they could be wired up only
   from the encrypted code region.
5. The user's empirical pattern (`Unlock Error - Inventory Extended:-1`
   appearing in `Age3Log.txt` on every failed scenario load) **may or may
   not** be the real gate — the format string is also emitted from the
   benign "no extended inventory items to merge" path in `unlocksboston.cpp`.
   Cross-checking whether the SAME log line appears on a successful random-map
   launch is the cheapest next step. If it does, we're chasing the wrong line.

The realistic remaining options are:

- **Replacement `steam_api64.dll`** that fakes ownership of every DLC
  entitlement (Goldberg Steam Emu is the standard implementation; drop-in,
  reversible, costs ~5 minutes to test). Disables online matchmaking but
  fine for offline scenario testing.
- **Wine DLL override + custom shim** for fine-grained interception
  (more work, less collateral).
- **Process-memory patch via Wine debugger / VEH hook injected post-unpack**
  — the proper static-RE workflow. Significant effort.

See "Recommended next step" at the bottom for a concrete user-facing plan.

## Already ruled out (do not retest)

- File-format integrity (CRC32/Adler32/file-size/zero/dup-header trailers)
- zlib encoder variants (level/memLevel/strategy)
- `remotecache.vdf` SHA1 manifest (chmod 444 — still rejects)
- `validatechecksum` user.cfg flag (no effect)
- Filename pattern (any case/prefix rejected)

## Plan

A. config-flag bypass via strings cross-ref
B. `steam_appid.txt` / Steam API
C. Locate "Inventory" gate function via string xref
D. Identify a binary patch (file-offset + before/after bytes)

## Findings

### PE layout

Image base `0x140000000`, 9 sections; two `.text` sections (the engine appears
to use a split-text layout, with a second `.text` at rva `0x03662000`). Strings
are in `.rdata` at rva `0x02347000`.

### Located strings

| string                                               | file off    | va                |
| ---------------------------------------------------- | ----------- | ----------------- |
| `Unlock Error - Inventory %s%d`                      | `0x0236a020`| `0x14236b420`     |
| `Unlock Error - Unable to process inventory for %lld`| `0x02369fd8`| `0x14236b3d8`     |
| `Unlock Error - Detach %s%d`                         | `0x0236a040`| `0x14236b440`     |
| `Extended:` (the `%s` arg)                           | `0x0236a010`| `0x14236b410`     |
| `d:\projects\age3\source\age3\unlocksboston.cpp`     | `0x02369fa8`| `0x14236b3a8`     |
| `InvalidFileDialog-prompt`                           | `0x0243ce70`| `0x14243e270`     |
| `loadScenario` (cmd)                                 | `0x023b0fb8`| `0x1423b23b8`     |
| `uiScenarioLoad`                                     | `0x023e2758`| `0x1423e3b58`     |

So the gate function lives in `unlocksboston.cpp` — interesting name: an Age3
"Inventory" subsystem that processes the player's home-city / DLC unlock data.

### Config tokens — none of the obvious bypass names exist

`noinventory`, `noscenariosig`, `nodrm`, `bypassinventory`, `skipsignature`,
`skipinventory`, `fakeinventory`, `nointegritycheck`, `developermode`,
`nounlock`, `unlockall`, `allunlocked`, `unlockedall`, `skipunlock`,
`bypassunlock`, `freeplay`, `debugmode`, `nochecksum`, `skipchecksum`,
`disableinventory`, `disabledrm`, `disablecheck`, `allcontent`, `forceunlock`,
`skipdrm`, `nounlockcheck` — **no occurrences** in `AoE3DE_s.exe`.

`developer` appears (and is in user.cfg already); `unlocked` only appears in
HC-tooltip / xs-script identifier strings.

The `validatechecksum` / `noPregameScenario` / `noPregameRecording` tokens that
appear in `Startup/game.cfg` **are not present in the binary at all** — they
may be dead-letters from an older codebase, which would explain why
`validatechecksum` had no effect when added to user.cfg.

### Steam appid

`/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/` contains
`steam_api64.dll` but **no `steam_appid.txt`**. The game launches via Steam so
this is normally fine, but worth noting.

### *** Major finding: `.text` is encrypted/packed ***

Both `.text` sections have Shannon entropy ~7.99 (max 8.0 = pure random).
First bytes of `.text` are `e3 e3 53 9f dc 1b 1f 4d ...` — random.

Disassembling the entry point gives garbage:

```
0x141306a8c  eb2f                 jmp 0x141306abd
0x141306a8e  cc                   int3
0x141306a8f  ba5b1b8d00           mov edx, 0x8d1b5b
0x141306a96  4ea05feab50e22619048 movabs al, byte ptr [...]    # nonsensical
```

A direct byte-level scan of *both* `.text` sections shows **zero RIP-relative
references and zero absolute QWORD references** to *any* of the located
strings, including ones that are unquestionably used (like `BugSplat`,
`InvalidFileDialog-prompt`). The relocation table contains 213,180 entries.

This means **the binary is packed/obfuscated** — almost certainly Arxan
GuardIT (which AoE: DE titles are known to ship with) — and the real
references are reconstructed at runtime.

PE imports include `WINTRUST.dll`, `bcrypt.dll`, `CRYPT32.dll`, and the
duplicate-cased `KERNEL32.dll` / `KERNEL32.DLL` import directory — classic
packer artefact.

### Implication for our investigation

Static binary patching of the gate is **not feasible** with the time/tools we
have:

- We cannot find the gate function statically — its body is not in the disk
  image in plaintext form. It only exists after Arxan's stub decrypts it.
- Even if we located it in a memory dump, Arxan inserts integrity checks
  ("guards") all over the place that re-checksum critical code regions and
  crash/corrupt if any byte is patched. AoE3 DE has previously been observed
  to call `BugSplat` and self-terminate on integrity failure.
- A `0F 84` → `0F 85` flip would be visible to the protector and trigger a
  guard.

So plan **D (binary patch)** is effectively dead.

### Re-prioritising

- Plan A (config flag): the obvious bypass tokens are not in the binary at
  all, but that's also expected — the *ASCII names* of console commands may
  be in the encrypted region too. We can't enumerate the command table by
  scanning the disk image. The only way is to dump them from the running
  process.
- Plan B (Steam API): `steam_api64.dll` is the standard Valve shim and IS
  unencrypted. The Inventory check almost certainly funnels through
  `ISteamInventory`. If the inventory query returns -1, it's coming back
  through the Steam API layer. **This is the most promising attack surface.**
- New plan **E**: hijack `steam_api64.dll`'s `ISteamInventory::*` calls so
  the gate sees a "successful" inventory result, regardless of what Steam
  actually returned.

### Steam-API import surface

`AoE3DE_s.exe` imports only 12 functions from `steam_api64.dll`:

```
SteamAPI_Shutdown                            iat=0x143661c28
SteamAPI_RunCallbacks                        iat=0x143661c30
SteamAPI_RegisterCallResult                  iat=0x143661c38
SteamAPI_UnregisterCallResult                iat=0x143661c40
SteamAPI_GetHSteamUser                       iat=0x143661c48
SteamInternal_FindOrCreateUserInterface      iat=0x143661c50
SteamInternal_CreateInterface                iat=0x143661c58
SteamAPI_Init                                iat=0x143661c60
SteamAPI_RestartAppIfNecessary               iat=0x143661c68
SteamAPI_RegisterCallback                    iat=0x143661c70
SteamAPI_UnregisterCallback                  iat=0x143661c78
SteamInternal_ContextInit                    iat=0x143661c80
```

The game gets the `ISteamInventory` interface pointer via
`SteamInternal_FindOrCreateUserInterface(hsteamuser, "STEAMINVENTORY_INTERFACE_V003")`
(version string is in encrypted `.text` so we can't see it on disk, but the
flat-API export naming in `steam_api64.dll` confirms ISteamInventory is
present in the Steam SDK). The returned pointer is a C++ vtable — methods
are dispatched via `vtable[N]`. After the call, AoE calls
`SteamAPI_RegisterCallResult` for `SteamInventoryResultReady_t` and waits for
its `RunCallbacks` to fire. Failure path comes from `GetResultStatus !=
k_EResultOK` (== `-1`-ish via the engine's adapter, which then logs `Inventory
Extended:-1`).

### Concrete bypass — replace `steam_api64.dll` with an asynchronous-friendly
mock

The game calls a small set of Steam-API functions. A *replacement*
`steam_api64.dll` that is wire-compatible (matching ordinals + same flat-API
exports for the inventory C functions used internally) and that returns
"yes you own everything" can satisfy the gate without touching the encrypted
binary.

But the game uses the **vtable interface**, not the flat C API, for
inventory calls. So the replacement must:

1. Implement an `ISteamInventory` vtable whose
   `RequestPrices`, `GetAllItems`, `GetResultStatus`, `GetResultItems`,
   `CheckResultSteamID` etc. all behave as if the user owns every DLC item
   and every call returns `k_EResultOK` (= 1).
2. Forward the rest of the API (`SteamAPI_Init`, `RunCallbacks`, etc.) to
   the real `steam_api64.dll` so multiplayer/auth/etc still work.

This is non-trivial but **achievable**. There is also a much simpler
existing tool that does exactly this: **`Goldberg Steam Emu`**. It's a
drop-in `steam_api64.dll` that emulates Steam offline and grants ownership
of every DLC. Several AoE-modding communities already use it for offline
play and it satisfies the inventory check for OWNERSHIP-related gates.

However, Goldberg disables online multiplayer. For our purposes (offline
scenario loading on Linux/Proton) that's fine.

### Recommended next step (handed to user)

Two options, in order of effort:

1. **Cheapest, untested:** drop-in Goldberg Steam Emu. The user replaces
   `steam_api64.dll` with the Goldberg build, sets a `steam_appid.txt`,
   relaunches via Proton, and tries to load the scenario. If the
   "Unlock Error - Inventory Extended:-1" message disappears, this
   confirms the gate is the Steam Inventory interface and the bypass
   is "fake every DLC as owned". Cost to user: 5 minutes; reversible.
2. **More work, more controlled:** write a small `LD_PRELOAD` (well, in
   Proton-land, a Wine `WINEDLLOVERRIDES=steam_api64=n,b` plus a tiny
   custom DLL) that intercepts ONLY the inventory-related vtable calls
   and forwards everything else. Still ~half a day's work; would need
   building under MinGW.

We do NOT have a static binary patch and cannot get one without
unpacking/dumping the live process — which is out of scope here.

### Cross-check: is the `Inventory Extended:-1` line *actually* the gate, or
###  is it a benign startup log entry that always fires?

The format string at `0x14236b420` is literally `"Unlock Error - Inventory %s%d"`.
The runtime substitution gives `Inventory Extended:-1`, where `Extended:` is
the literal `%s` arg from `0x14236b410` and `-1` is the `%d`. This is
emitted from `unlocksboston.cpp`. The same source file emits another log line:
`Unlock Error - Detach %s%d` (twin format string at `0x14236b440`).

Possibility we should not rule out: the "Unlock Error - Inventory Extended:-1"
line is **emitted every startup** as a normal "no Extended-inventory items
to merge" status. If the user has no DLC-extended inventory entitlement, the
function reports `-1` (== "no items to enumerate") and logs the line — but
that logging might be unrelated to the failure to open a scenario file.

The empirical pattern that incriminates this line is:
- random skirmish (no scenario file) succeeds and the log line still appears
- scenario load fails and the log line still appears

If both succeed and fail paths show the same line, **the line is not the
gate**. We should ask the user to check whether the `Unlock Error - Inventory
Extended:-1` message appears in `Age3Log.txt` from a *successful* random-map
launch as well. If yes, we have been chasing a red herring — the actual
gate is something else.

This is now the FIRST thing to verify before further engine RE work.

### What is in `tools/aoe3_automation/manage_game.py`?

`manage_game.py` already deploys `~/.../Startup/user.cfg` containing the
tokens `developer +ixsLog +cxsLog`. The infrastructure to add another token
(or another `.cfg` line) is trivial — it's done in `log_capture.py`'s
`_REQUIRED_TOKENS` tuple and `_DEV_CFG_CONTENT` literal. If we ever find a
working bypass token, adding it is a one-line change.

### Status: blocked on hard data

The path forward depends on the answer to the cross-check question above.

If `Inventory Extended:-1` appears on **successful** random-map launches:
- We've been chasing the wrong log line.
- We need a fresh diff: capture full `Age3Log.txt` from a successful skirmish
  and a failing scenario load, diff them, and find the line that ONLY appears
  in the failing run. That's the real gate.
- Specific suspects: anything mentioning "checksum", "signature", "trust",
  "wintrust", "cert", "validate", "verify", "scenario integrity".

If it appears ONLY on failing scenario loads:
- The gate IS the inventory subsystem.
- The bypass is to replace `steam_api64.dll` with one that fakes ownership
  of every entitlement (Goldberg Steam Emu is the standard tool for this).
- Caveats: this disables Steam Workshop / online matchmaking; for offline
  scenario testing, that's acceptable.

Either way, no static binary patch is achievable here because `.text` is
encrypted on disk (Arxan or equivalent).

## Recommended next step (concrete, actionable)

**Step 1 — 30-second cross-check the user must run before anything else:**

Reproduce a *successful* random-map skirmish, then `grep "Unlock Error" Age3Log.txt`.

```bash
grep -c "Unlock Error - Inventory" \
    "/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Logs/Age3Log.txt"
```

- If it prints `0` after a successful skirmish but a positive number after a
  failed scenario load → the line IS the gate. Proceed to step 2.
- If it prints a positive number on **both** successful and failed runs →
  the line is benign, we have been chasing a red herring; we need a
  log-diff between successful and failed runs to find the real gate.
  Recommended: capture both logs, run `diff -u success.log failure.log |
  head -200`, look for any `Error`, `Failed`, `Reject`, `Sig`, `Verify`,
  `Trust`, `Crypto`, or `WinTrust` line that only appears in the failure
  log.

**Step 2 (if the line IS the gate) — drop in Goldberg Steam Emu:**

Goldberg Steam Emu is a community-maintained, MIT-licensed `steam_api64.dll`
replacement that emulates the Steam API offline. It implements all
`ISteamInventory` and `ISteamApps` calls and reports ownership of every
DLC, which is exactly what we need.

Direct download URL (latest stable):
- https://gitlab.com/Mr_Goldberg/goldberg_emulator/-/releases

Apply it as follows (do NOT delete the original DLL, archive it):

```bash
GAME=/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE
cp "$GAME/steam_api64.dll" "$GAME/steam_api64.dll.original"
# unzip the goldberg release, then:
cp /path/to/goldberg/steam_api64.dll "$GAME/steam_api64.dll"
echo 933110 > "$GAME/steam_appid.txt"
mkdir -p "$GAME/steam_settings"
echo 933110 > "$GAME/steam_settings/steam_appid.txt"
# Goldberg also needs DLC list — give it the AoE3 DE DLC IDs:
cat > "$GAME/steam_settings/DLC.txt" << 'EOF'
# Format: <appid>=<name> (one per line). Listing all known AoE3 DE DLC.
1167070=Age of Empires III: DE - The African Royals
1442590=Age of Empires III: DE - Knights of the Mediterranean
1937550=Age of Empires III: DE - The Asian Dynasties
2138310=Age of Empires III: DE - Mexico Civilization
2208600=Age of Empires III: DE - United States Civilization
EOF
```

Then launch via Steam normally. If the inventory check was the gate, the
scenario will load. If not, the `INVALID FILE` dialog will still appear and
we'll need step 1's log-diff to find the real gate.

**Reversal:** `cp steam_api64.dll.original steam_api64.dll` and delete
`steam_appid.txt`/`steam_settings/`.

**Caveats:**
- Steam Workshop subscribed mods will not auto-sync (Goldberg's stub of
  `RemoteStorage` is best-effort).
- Multiplayer matchmaking will not work while Goldberg is in place.
- Steam may flag the install as "modified" and re-validate it on next
  Steam restart, replacing `steam_api64.dll`. Workaround: set the install
  to "do not auto-update" in Steam properties.

**Step 3 (only if step 2 also fails) — Wine debugger memory patch:**

If the gate isn't `ISteamInventory` after all, the next play is:

1. Run the game under `winedbg` with a breakpoint at any printf-class call
   that emits format strings (e.g. wcstomb, vsnprintf).
2. Trigger the failed scenario load and let the breakpoint fire.
3. Walk back the call stack to find the gate function in the now-decrypted
   in-memory `.text`.
4. Identify the conditional branch and write a one-shot VEH-based patch
   (loadable as a Wine plugin) that flips the branch in memory after the
   protector finishes its self-decrypt but before the gate is hit.

This is a multi-day effort and not in scope for this session.

## Files produced by this investigation

- `tools/validation/scenario_load_bypass.md` — this document.
- `tools/validation/inspect_engine_binary.py` — re-runnable static analysis.
  Usage: `python3 tools/validation/inspect_engine_binary.py [--xref] [--brute-xref]`.
  - default: list sections + entropies, locate target/candidate strings,
    disasm probe at entry point and a couple of `.pdata` function starts
    (proves `.text` is encrypted).
  - `--xref`: fast x86-64 RIP-relative scan against the chosen targets
    (will find zero refs in this binary; included for completeness and
    future use on un-packed builds).
  - `--brute-xref`: exhaustive scan; very slow but tries every plausible
    instruction length. Will also find zero refs here.

No `tools/aoe3_automation/apply_engine_patch.py` was produced because no
patch was identified.




