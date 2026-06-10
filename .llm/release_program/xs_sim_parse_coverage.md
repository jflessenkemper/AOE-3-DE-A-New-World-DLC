# XS Sim Parse Coverage Report
_Generated: 2026-06-08 — measurement-only pass, no code changes_

---

## (a) Where xs_sim lives + how to parse a file

**Package root:** `tools/xs_sim/`

| File | Purpose |
|------|---------|
| `tools/xs_sim/lexer.py` | Tokenizer — `tokenize(src, filename)` |
| `tools/xs_sim/parser.py` | Recursive-descent parser — `parse(src, filename)` |
| `tools/xs_sim/ast_nodes.py` | AST dataclasses |
| `tools/xs_sim/interpreter.py` | Interpreter (do NOT run for this task) |
| `tools/xs_sim/__init__.py` | Package init (no CLI defined) |
| `tools/xs_sim/tests/test_smoke.py` | Unit smoke tests |

**Entry point for parse-only work** (`tools/xs_sim/parser.py` line 564–566):
```python
def parse(src: str, filename: str = "<src>") -> A.Program:
    from .lexer import tokenize
    return Parser(tokenize(src, filename), filename).parse_program()
```

**How to call it from outside the repo (throwaway script pattern):**
```python
import sys
sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools")
from xs_sim.parser import parse
ast = parse(open("game/ai/core/aiGlobals.xs").read(), filename="aiGlobals.xs")
```

There is no existing CLI or batch-parse harness — the throwaway script `/tmp/xs_batch_parse.py` was used for this run.

---

## (b) Corpus size + coverage

**Corpus root:** `game/ai/` (three sub-directories)

| Directory | File count |
|-----------|-----------|
| `game/ai/` (top-level) | 6 |
| `game/ai/core/` | 37 |
| `game/ai/leaders/` | 23 |
| **Total** | **66** |

**Parse results:**

| Status | Count |
|--------|-------|
| PARSED-OK | 51 |
| PARSE-FAILED | 15 |
| **Coverage** | **77.3% (51/66)** |

---

## (c) Ranked table of failing constructs

| Rank | Files blocked | Root cause | Example file:line | Error excerpt |
|------|--------------|-----------|-------------------|---------------|
| 1 | **5** | **Lambda / fn-pointer literal** `[](...) -> T { }` — parser has no grammar rule for lambda expressions; `[` in expression context is not handled | `game/ai/core/aiBuildingsWalls.xs:1643` | `unexpected token op='[' in expression` |
| 2 | **3** | **Bare `include` without `#` prefix** — lexer only handles `#include "..."` (lexer.py:87); bare `include "..."` is tokenized as `id='include'` and the parser fails with "expected declaration" | `game/ai/aiLoaderStandard.xs:11` | `expected declaration, got id='include'` |
| 3 | **2** | **`mutable` storage-class on function/variable declarations** — `mutable` is in KEYWORDS (lexer.py:17) but `_parse_top()` (parser.py:93) only eats `const`, `static`, `extern`; `mutable` falls through to the type check | `game/ai/aiHumanAssists.xs:9` | `expected declaration, got kw='mutable'` |
| 4 | **1** | **Bitshift operators `<<` / `>>`** — `<<` and `>>` are in lexer OPS list (lexer.py:22) and tokenized correctly, but the expression hierarchy in the parser has no `_parse_shift()` level between `_parse_add` and `_parse_cmp` | `game/ai/core/aiBuildings.xs:4302` | `expected op=')', got op='<<'` |
| 5 | **1** | **`class` declarations** — `class` is not a keyword in the lexer (not in KEYWORDS), so it tokenizes as `id='class'`; parser.py has no grammar rule for class bodies | `game/ai/core/aiEconomy.xs:284` | `expected declaration, got id='class'` |
| 6 | **1** | **Empty return-value parens `return ()`** — parser.py:253 calls `_parse_expr()` when next token is not `;`; `_parse_primary()` hits `)` without a preceding expression and raises | `game/ai/core/aiExploration.xs:695` | `unexpected token op=')' in expression` |
| 7 | **1** | **Bare debug macro statement** `debugTechs "string" + ...` — XS game-engine macro that takes a string operand directly (no parentheses); parser sees `debugTechs` as an expression-statement identifier, then expects `;`, but finds a string literal | `game/ai/core/aiTechs.xs:1079` | `expected op=';', got str='WARNING...'` |
| 8 | **1** | **Function-pointer parameter type** `bool(int, int) comp = expr` in param list — `_parse_param()` (parser.py:157) reads a type kw then immediately expects an `id`, but the next token is `(` for the fn-pointer signature | `game/ai/core/aiUtilities.xs:645` | `expected id, got op='('` |

> Note: ranks 1 and 8 are related — both involve function-pointer / lambda syntax. Fixing lambda literals (rank 1) will also require resolving how fn-pointer types appear in param lists (rank 8).

---

## (d) Recommended fix order

Fixes ordered by files-unblocked and implementation coupling:

1. **Lambda / fn-pointer literals** (unblocks 5 files, rank 1)
   Add a `_parse_lambda()` branch in `_parse_primary()` triggered on `op='['`. Grammar: `'[' ']' '(' params ')' ['->' type] block`. This also covers the `bool(int,int) name = [](...) {...}` form (rank 1 + rank 8 together).
   - Key files to unblock: `aiBuildingsWalls.xs`, `aiHCCards.xs`, `aiMilitary.xs`, `aiMiscNew.xs`, `aihcccards_orig.xs`

2. **Bare `include` without `#`** (unblocks 3 files, rank 2)
   Either add `include` to KEYWORDS in `lexer.py:10` and handle `kw='include'` in `_parse_top()`, or add a bare-`include` path in `_parse_top()` before the `if not (t.kind == "kw" and ...)` guard (parser.py:99).
   - Key files to unblock: `aiLoaderInactive.xs`, `aiLoaderStandard.xs`, `aiMain.xs`

3. **`mutable` storage-class** (unblocks 2 files, rank 3)
   Add `"mutable"` to the while-loop at parser.py:93 that eats `const`/`static`/`extern` prefixes.
   - Key files to unblock: `aiHumanAssists.xs`, `aiCore.xs`

4. **Bitshift operators `<<` / `>>`** (unblocks 1 file, rank 4)
   Insert a `_parse_shift()` level in the expression hierarchy between `_parse_add()` and `_parse_cmp()`, handling `<<` and `>>`.
   - Key file to unblock: `aiBuildings.xs`

5. **`class` declarations** (unblocks 1 file, rank 5)
   Add `"class"` as a keyword in lexer.py, then implement `_parse_class_def()` in parser.py to handle `class Name { field_decls* }; `. Field access (`obj.field`) is already handled by postfix `.` (not yet wired, but the op is in OPS).
   - Key file to unblock: `aiEconomy.xs`

6. **Empty `return ()`** (unblocks 1 file, rank 6)
   In `_parse_stmt()` (parser.py:252–257), when handling `return`, check for the `return ();` pattern: if next token is `(` and the token after that is `)`, consume both and emit a `Return(value=None)`.
   - Key file to unblock: `aiExploration.xs`

7. **Bare debug macro statement** (unblocks 1 file, rank 7)
   `debugTechs` is used as an XS built-in statement that takes a string expression argument with no parentheses. Easiest fix: recognize it as a special statement keyword (add to KEYWORDS, handle in `_parse_stmt()` as `ExprStmt` eating the trailing expression). Alternatively, skip lines where statement-start is an identifier followed by a string token (fragile). Recommend the keyword approach.
   - Key file to unblock: `aiTechs.xs`

8. **Function-pointer param type** (unblocks 1 file, rank 8 — likely resolved with fix #1)
   `_parse_param()` (parser.py:153–169) needs to handle `type '(' type_list ')' name ['=' expr]` for fn-pointer params. This is already partially handled at the top-level (`_parse_top()` lines 110–123) but not in param lists.
   - Key file to unblock: `aiUtilities.xs`

---

## Summary

| Metric | Value |
|--------|-------|
| Total .xs files | 66 |
| Parsed OK | 51 |
| Parse failures | 15 |
| Coverage | **77.3%** |
| Distinct root causes | 8 |
| Files unblocked by top-3 fixes alone | 10/15 (66.7% of failures) |

Fixing items 1–3 (lambda literals, bare include, mutable) would raise coverage from 77.3% to approximately **92.4% (61/66)** without touching any expression or statement complexity.
