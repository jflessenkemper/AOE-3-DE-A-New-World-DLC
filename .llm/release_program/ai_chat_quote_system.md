# AI Chat & Quote System — Architecture Findings

## A. PROBE SYSTEM — Emission & Validator Source

### Emission path
`anwProbe()` is defined at `game/ai/core/aiUtilities.xs:261`.  
It always emits two channels:
1. `aiEcho(line)` — engine debug stream → `Age3Log.txt` (dev builds only; silent on retail)
2. `aiChat(cMyID, line)` — self-addressed; **stored in the replay binary chat stream but does NOT appear on-screen** (engine does not display self-chat to human players)
3. `aiChat(1, line)` — **only when `cANWProbeToHostChat == true`** (`aiGlobals.xs:586`, default `false`)

`anwMirrorEventToChat()` (`aiUtilities.xs:162`) is a separate second path: it fires `aiChat(playerID, "[LL <category>] <message>")` only when `cANWDebugVisible == true` (`aiGlobals.xs:612`, default `false`) and respects a 12-second cooldown.

### Why the user sees probes in chat
**Both flags are `false` in the committed code.** The probe leak the user observes must therefore come from a local test build where either `cANWProbeToHostChat` or `cANWDebugVisible` was set `true` and has not been reset, **or** from a side-channel `aiChat` call not gated by these flags. Confirm by searching for any hardcoded `aiChat(1, ...)` or `aiChat(playerID, ...)` that bypasses `anwProbe`/`anwMirrorEventToChat` and carries `[ANWP` or `[LL ` prefix text.

### Where validators read probe text
Validators read `Age3Log.txt` (the `aiEcho` channel), **not** the binary `.age3Yrec` replay chat stream (which stores string-table indices, not plain text). This is documented verbatim at `tools/playtest/replay_probes.py:3-16`. The probe parsing regex at `replay_probes.py:74-78` matches `[ANWP v=2 ...]` in plain-text log bytes. Suppressing `aiChat(1, ...)` (probe-to-host) has **zero effect on validators** — they read `Age3Log.txt` exclusively.

### Safe fix for probe chat leakage
Two confirmed `false` flags already exist. The leak is an accidental `true` somewhere locally. Fix: verify both flags remain `false` in any released build.

**Suggested validator** (`tools/validation/validate_no_probe_chat_leak.py`):  
Parse `game/ai/core/aiGlobals.xs`, assert `cANWProbeToHostChat = false` and `cANWDebugVisible = false`. Exit non-zero if either is `true`. Run as part of pre-release CI.

---

## B. AI Chat API

Two distinct mechanisms exist:

| Function | File:Line | Sends what | Recipients |
|---|---|---|---|
| `aiChat(playerID, string)` | native XS builtin, used at `aiUtilities.xs:182,294,297`; `aiChats.xs:142,178` | Free-form text string | Single player by ID |
| `aiCommsSendStatement(playerID, commPromptID)` | native XS builtin, used at `aiChats.xs:44,109` | Chatset `<Tag>` trigger (triggers XML-configured audio + string) | Single player by ID |
| `aiCommsSendStatementWithVector(playerID, commPromptID, vec)` | native XS builtin, `aiChats.xs:48,114` | Same + map flare | Single player by ID |

Mod wrapper: `sendChatLine(playerIDorRelation, message)` at `aiChats.xs:124` calls `aiChat` per-player, supporting both explicit player IDs and relation constants (`cPlayerRelationEnemy`, etc.).  
Mod wrapper: `sendStatement(playerIDorRelation, commPromptID)` at `aiChats.xs:19` calls `aiCommsSendStatement` plus automatically invokes `anwMaybeFollowStatementWithQuote()` afterward.

**Constraints:**
- No confirmed newline character support inside a single `aiChat` string — XS string type is treated as plain text; `\n` has not been observed in any existing chat call.
- No Unicode/non-Latin character rendering is used or tested anywhere in the mod.
- Max length: undocumented; no truncation guard found in any wrapper.

---

## C. Quotes — Storage and Existing Speak-Quote Code

### Quote data locations

| Source | Path | Contents |
|---|---|---|
| XS insult/compliment tables | `game/ai/core/aiLeaderQuotes.xs:252-1019` | Two quotes per civ per polarity (enemy/ally), English only |
| Chatset XML triggers | `game/ai/chatsetsmods.anw.xml` | Full chatset entries with `<String>`, `<Sound>`, `<StringID>` per trigger |
| Chat quotes JSON | `tools/chatquotes/quotes.json` | 47 leaders, 6-8 triggers each, English only; used by `generate_chat_quotes.py` to produce the XML |
| Civ blurbs JSON | `data/anw_civ_blurbs.json` | Playstyle/unit/building descriptions — not chat quotes |
| String table | `data/strings/english/stringmods.xml` | Localized display strings (leader bios etc.) — no native-language quote text |

**No native-language (non-English) text exists anywhere in the quote pipeline.** `tools/chatquotes/quotes.json` contains only English strings; no `native_text` or `original_language` field is defined.

### Existing speak-quote code
Yes, the AI already speaks quotes in chat via two routes:

1. **Opening quotes rule** (`aiLeaderQuotes.xs:195-218`): fires at ~25 s game time, sends compliment to allies and insult to enemies via `sendChatLine` → `aiChat`.
2. **Post-statement follow-up** (`aiLeaderQuotes.xs:167-193`, `aiChats.xs:50,117`): every `sendStatement()` call checks `anwMaybeFollowStatementWithQuote()` which throttle-checks and fires an insult or compliment via `sendChatLine`.
3. **Tactical lines** (`aiLeaderQuotes.xs:147-165`): called by military code for retreat/rout/assault/decapitation events.

---

## D. Bilingual Feasibility Verdict

**Honest assessment: native-line-1 / English-line-2 in a single chat call is not feasible with the current engine path.**

- The XS `string` type is plain ASCII. No `\n` or Unicode escape has been observed in any XS chat call in this codebase.
- `aiChat(playerID, text)` routes through the engine's chatset/string-table system; the chatset `<String>` fields in `chatsetsmods.anw.xml` are XML-encoded ASCII. Non-Latin scripts (Arabic, Chinese, Japanese) are untested and almost certainly will not render in AoE3 DE's in-game chat box.
- The `data/strings/english/stringmods.xml` string table uses `utf-8` encoding (line 1) but these strings are used for UI tooltips/info panels, not in-game AI chat.
- **Two-message approach is feasible**: call `sendChatLine` twice in quick succession — native-language line first, English line second. Both arrive in chat as separate lines from the same AI player. This avoids the `\n` unknown entirely.
- **Native-language text would need to be added** to `tools/chatquotes/quotes.json` as a new `native_text` field per trigger, and `generate_chat_quotes.py` regenerated.
- **Rendering risk is high for non-Latin scripts** (Chinese, Japanese, Arabic, Cyrillic): the game engine's chat box font support is unknown and likely Latin-only. Recommend testing one civ (e.g. Russian/Cyrillic) before investing in all civs.

---

## Recommended Implementation Plan

### Change 1 — Stop probe chat leakage

**Root cause to confirm first**: add `validate_no_probe_chat_leak.py` (new file, ~20 lines) that parses `aiGlobals.xs` and asserts both `cANWProbeToHostChat = false` and `cANWDebugVisible = false`. Wire into pre-release CI.

No XS change is needed: both flags are already `false` at `aiGlobals.xs:586,612`. If the user is still seeing `[ANWP` lines in chat during a live game, the game was built with a locally modified `aiGlobals.xs` — reset it.

**Files to edit**: `tools/validation/validate_no_probe_chat_leak.py` (new), CI script to invoke it.

---

### Change 2 — Make the AI speak chatset quotes (trigger-based, with portrait/audio)

The chatset XML system (`chatsetsmods.anw.xml`) is already wired: `aiCommsSendStatement(playerID, commPromptID)` fires the chatset tag by trigger name, showing the leader portrait + playing audio. The `anwMaybeFollowStatementWithQuote()` and `anwLeaderOpeningQuote` rules already do this for opening lines and post-statement follow-ups.

To expand: add additional trigger tags to `tools/chatquotes/quotes.json` → regenerate `chatsetsmods.anw.xml` via `tools/chatquotes/generate_chat_quotes.py` → map new commPromptID constants to the new tag names in `aiChats.xs` trigger dispatch.

**Files to edit**: `tools/chatquotes/quotes.json` (add quotes), `game/ai/chatsetsmods.anw.xml` (regenerated), optionally `game/ai/core/aiChats.xs` for new trigger wiring.

---

### Change 3 — Bilingual (native line 1 + English line 2)

**Recommended approach: two consecutive `sendChatLine` calls**, separated by a 200–500 ms delay (using a timer or second rule tick).

Steps:
1. Add `native_text` field to each leader entry in `tools/chatquotes/quotes.json`.
2. Update `generate_chat_quotes.py` to emit a parallel chatset entry with the native string (or handle it as a free-form `sendChatLine` from XS).
3. In `aiLeaderQuotes.xs`, modify `anwSendLeaderInsultLine` / `anwSendLeaderComplimentLine` to fire native text first via `sendChatLine`, then the English quote.
4. **Before investing**: test Cyrillic/Chinese rendering in a live game first (one `sendChatLine` with a UTF-8 Cyrillic string) — if the engine chat box garbles it, use romanized transliteration or omit native text for non-Latin civs.

**Files to edit**: `tools/chatquotes/quotes.json`, `tools/chatquotes/generate_chat_quotes.py`, `game/ai/core/aiLeaderQuotes.xs`.

---

*All file:line citations verified against the repository as of this investigation. No code was modified.*
