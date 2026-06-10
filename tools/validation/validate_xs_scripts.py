"""Lint ANW XS script files for undeclared variables, duplicate rule/function names, and unresolved function calls."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, repo_relative

LOCAL_DECLARATION_RE = re.compile(r"^\s*(int|bool|float|string|vector)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;)")
FUNCTION_RE = re.compile(r"^\s*(?:void|bool|int|float|string|vector)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
RULE_RE = re.compile(r"^\s*rule\s+([A-Za-z_][A-Za-z0-9_]*)\b")
FUNCTION_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
INCLUDE_RE = re.compile(r'^\s*include\s+"([^"]+)"\s*;?')
# Classic form: ``int foo(...)`` / ``bool llBar(...)``. Accepts a custom return
# type (any identifier), which covers base-game struct returns like
# ``ValidResourceInfo getValidResourceInfo(...)``.
CALLABLE_DECL_RE = re.compile(
    r"^\s*(?:mutable\s+|extern\s+)?[A-Za-z_][A-Za-z0-9_]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
# Function-pointer form: ``int() createFoo = [](...)`` / ``bool(int) gFoo = impl``
# / function-pointer parameters ``bool(int, int) comp = defaultComp``.
FUNCTION_PTR_DECL_RE = re.compile(
    r"(?:^|,|\()\s*(?:mutable\s+|extern\s+)?[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)\s+([A-Za-z_][A-Za-z0-9_]*)\s*="
)
KNOWN_ENGINE_PREFIXES = ("xs", "ai", "kb", "cv", "bt")
# Type keywords also match FUNCTION_CALL_RE when used in function-pointer type
# declarations like ``extern int(int, int) cvFoo``.
KNOWN_LANGUAGE_CALLS = {
    "if", "for", "switch", "while", "return",
    "int", "bool", "float", "string", "vector", "void",
}
# Engine-provided helpers that don't follow the KNOWN_ENGINE_PREFIXES convention.
KNOWN_ENGINE_CALLS = {
    "createSimpleUnitQuery",
    "createUnitQuery",
    # Math builtins exposed by the XS VM.
    "abs", "sin", "cos", "tan", "sqrt", "pow", "min", "max", "round", "ceil", "floor",
}
# AoE3 DE installs on Linux under Proton keep the game tree under
# ``steamapps/common/AoE3DE/Game/AI`` (case-sensitive on Linux). Historically
# native installs used lowercase paths.
BASE_GAME_AI_PATHS = (
    Path.home() / ".local/share/Steam/steamapps/common/AoE3DE/Game/AI",
    Path.home() / ".local/share/Steam/steamapps/common/AoE3DE/game/ai",
    Path.home() / ".steam/steam/steamapps/common/AoE3DE/Game/AI",
    Path.home() / ".steam/steam/steamapps/common/AoE3DE/game/ai",
)
STOCK_XS_CALLS = {
    "xsArrayCreateBool",
    "xsArrayCreateFloat",
    "xsArrayCreateInt",
    "xsArrayCreateString",
    "xsArrayCreateVector",
    "xsArrayGetBool",
    "xsArrayGetFloat",
    "xsArrayGetInt",
    "xsArrayGetSize",
    "xsArrayGetString",
    "xsArrayGetVector",
    "xsArrayResizeInt",
    "xsArrayResizeVector",
    "xsArraySetBool",
    "xsArraySetFloat",
    "xsArraySetInt",
    "xsArraySetString",
    "xsArraySetVector",
    "xsDisableRule",
    "xsDisableSelf",
    "xsEnableRule",
    "xsEnableRuleGroup",
    "xsGetTime",
    "xsIsRuleEnabled",
    "xsSetContextPlayer",
    "xsSetRuleMaxIntervalSelf",
    "xsSetRuleMinInterval",
    "xsSetRuleMinIntervalSelf",
    "xsVectorGetX",
    "xsVectorGetY",
    "xsVectorGetZ",
    "xsVectorLength",
    "xsVectorNormalize",
    "xsVectorSet",
    "xsVectorSetX",
    "xsVectorSetZ",
}
UNSUPPORTED_BUILTINS = {
    "xsCeil",
    "xsFloor",
    "xsRound",
}


@dataclass
class Block:
    kind: str
    name: str
    start_line: int
    body_start_line: int
    brace_depth: int = 0
    declarations: dict[str, int] | None = None
    recent_nonempty_lines: list[str] | None = None

    def __post_init__(self) -> None:
        if self.declarations is None:
            self.declarations = {}
        if self.recent_nonempty_lines is None:
            self.recent_nonempty_lines = []


def iter_xs_files(root: Path):
    yield from sorted(root.rglob("*.xs"))


def strip_inline_block_comments(line: str, in_block_comment: bool) -> tuple[str, bool]:
    result = []
    cursor = 0

    while cursor < len(line):
        if in_block_comment:
            end = line.find("*/", cursor)
            if end == -1:
                return ("".join(result), True)
            cursor = end + 2
            in_block_comment = False
            continue

        start = line.find("/*", cursor)
        if start == -1:
            result.append(line[cursor:])
            break

        result.append(line[cursor:start])
        cursor = start + 2
        in_block_comment = True

    return ("".join(result), in_block_comment)


def strip_string_literals(code: str) -> str:
    """Remove content inside double-quoted strings so regex scans don't match
    words like ``ENABLED (`` that appear inside log messages."""
    out: list[str] = []
    i = 0
    in_string = False
    while i < len(code):
        ch = code[i]
        if in_string:
            if ch == "\\" and i + 1 < len(code):
                i += 2
                continue
            if ch == '"':
                out.append('"')
                in_string = False
            i += 1
            continue
        if ch == '"':
            out.append('"')
            in_string = True
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def collect_declared_callables(ai_root: Path) -> set[str]:
    """Collect everything that can be invoked like a function: classic
    function declarations, rule names, and function-pointer declarations
    (including function-pointer parameters and lambda-assigned globals)."""
    declared: set[str] = set()
    for file_path in iter_xs_files(ai_root):
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_block_comment = False
        for line in lines:
            code, in_block_comment = strip_inline_block_comments(line, in_block_comment)
            code = strip_string_literals(code)
            if match := CALLABLE_DECL_RE.match(code):
                declared.add(match.group(1))
            if match := RULE_RE.match(code):
                declared.add(match.group(1))
            for match in FUNCTION_PTR_DECL_RE.finditer(code):
                declared.add(match.group(1))
    return declared


def check_duplicate_names(file_path: Path, lines: list[str], repo_root: Path) -> list[str]:
    issues: list[str] = []

    function_names = [match.group(1) for line in lines if (match := FUNCTION_RE.match(line))]
    rule_names = [match.group(1) for line in lines if (match := RULE_RE.match(line))]

    duplicate_functions = sorted(name for name, count in Counter(function_names).items() if count > 1)
    duplicate_rules = sorted(name for name, count in Counter(rule_names).items() if count > 1)

    rel_path = repo_relative(file_path, repo_root)
    for name in duplicate_functions:
        issues.append(f"{rel_path}: duplicate function name '{name}'")
    for name in duplicate_rules:
        issues.append(f"{rel_path}: duplicate rule name '{name}'")

    return issues


def check_duplicate_locals(file_path: Path, lines: list[str], repo_root: Path) -> list[str]:
    """Flag duplicate variable declarations inside the same ``function``.

    The AoE3 DE XS VM hoists local declarations to function scope and rejects
    redeclarations with ``XS Error 0014: '<name>' is already defined``,
    even when the two declarations sit in disjoint ``{ }`` blocks
    (verified empirically: ``vector fallback`` collision in
    aiBuildingsWalls.xs:218 and :275 inside sibling if-blocks at function
    top level).

    Scope quirks observed in the live engine:
    - ``rule`` bodies appear to tolerate the same pattern (base-game
      ``aiCore.xs`` and ``aiEconomy.xs`` ship with sibling-if-block
      redeclarations and load cleanly), so we do NOT flag duplicates
      inside rules.
    - Lambda bodies (``[](...) -> type { ... }``) are their own function,
      so we skip declarations inside them.
    - Loop-control declarations like ``for (int i = 0; ...)`` are also
      loop-scoped — but the regex matches `int|bool|float|string|vector`
      at start-of-line, so loop headers don't match anyway.

    Net effect: this catches the exact bug class that just crashed the live
    engine (sibling-if redeclare in a function body) without false-flagging
    base-game rules or lambda-local rebindings.
    """
    issues: list[str] = []
    pending: Block | None = None
    active: Block | None = None
    # Lambda nesting depth — when > 0 we're inside one or more lambda
    # bodies and should not track declarations against the outer function.
    lambda_depth = 0
    lambda_brace_at_open: list[int] = []  # brace_depth at the `{` of each open lambda
    rel_path = repo_relative(file_path, repo_root)

    for index, line in enumerate(lines, start=1):
        scan_line = line.split("//", 1)[0]

        if active is None:
            if pending is None:
                if match := FUNCTION_RE.match(scan_line):
                    pending = Block("function", match.group(1), index, index)
                elif match := RULE_RE.match(scan_line):
                    pending = Block("rule", match.group(1), index, index)

            if pending is not None and "{" in scan_line:
                active = pending
                active.body_start_line = index
                active.brace_depth = scan_line.count("{") - scan_line.count("}")
                pending = None
                lambda_depth = 0
                lambda_brace_at_open = []
                continue

        if active is not None:
            stripped = scan_line.strip()

            # Lambda open: `[](...) -> ... {` or `[]() -> ... {`. Count each
            # `[]` as opening a new lambda whose `{` is on the same or next
            # line. We approximate by toggling on the `[](` literal; the
            # accompanying `{` (which may be on this line or the next) gets
            # counted by the generic brace tracker below. Track the brace
            # depth at which the lambda's `{` sits so we know when it closes.
            if "[](" in scan_line or "[]()" in scan_line:
                # The brace pairing with this lambda is the next `{` we see.
                # Mark the depth-at-open as the current depth + 1 (post-`{`).
                lambda_brace_at_open.append(active.brace_depth + 1)
                lambda_depth += 1

            if match := LOCAL_DECLARATION_RE.match(scan_line):
                name = match.group(2)
                in_for_control = stripped.startswith("for (")
                # Only flag inside `function`, outside any lambda.
                if (
                    not in_for_control
                    and active.kind == "function"
                    and lambda_depth == 0
                ):
                    if name in active.declarations:
                        first_line = active.declarations[name]
                        issues.append(
                            f"{rel_path}:{index}: duplicate local '{name}' "
                            f"in {active.kind} '{active.name}' "
                            f"(first declared on line {first_line}) — "
                            f"XS hoists locals to function scope; rename one"
                        )
                    else:
                        active.declarations[name] = index

            # Brace tracking — both for the active function/rule scope and
            # for collapsing lambda nesting back down.
            open_count = scan_line.count("{")
            close_count = scan_line.count("}")
            active.brace_depth += open_count
            active.brace_depth -= close_count

            # Pop any lambdas whose closing `}` we just crossed. A lambda
            # opened at depth D is closed when active.brace_depth drops
            # below D.
            while lambda_brace_at_open and active.brace_depth < lambda_brace_at_open[-1]:
                lambda_brace_at_open.pop()
                lambda_depth = max(0, lambda_depth - 1)

            if stripped:
                active.recent_nonempty_lines.append(stripped)
                if len(active.recent_nonempty_lines) > 4:
                    active.recent_nonempty_lines.pop(0)
            if active.brace_depth <= 0 and index > active.body_start_line:
                active = None
                pending = None
                lambda_depth = 0
                lambda_brace_at_open = []

    return issues


def check_unsupported_builtins(file_path: Path, lines: list[str], repo_root: Path) -> list[str]:
    issues: list[str] = []
    rel_path = repo_relative(file_path, repo_root)

    for index, line in enumerate(lines, start=1):
        code = line.split("//", 1)[0]
        stripped = code.strip()
        if not stripped or stripped.startswith("//"):
            continue

        for match in FUNCTION_CALL_RE.finditer(code):
            function_name = match.group(1)
            if function_name in UNSUPPORTED_BUILTINS:
                issues.append(f"{rel_path}:{index}: unsupported XS builtin '{function_name}'")

    return issues


def check_non_ascii_in_strings(file_path: Path, lines: list[str], repo_root: Path) -> list[str]:
    """The AoE3 DE XS tokenizer bails on non-ASCII bytes inside double-quoted
    string literals — it raises ``Token Error 0008: STRING NOT TERMINATED`` and
    the whole script fails to compile (see issues with em-dashes inside
    log messages). We allow non-ASCII in comments, but reject it inside
    string literals so this never reaches the runtime again."""

    issues: list[str] = []
    rel_path = repo_relative(file_path, repo_root)
    in_block_comment = False

    for index, line in enumerate(lines, start=1):
        code, in_block_comment = strip_inline_block_comments(line, in_block_comment)
        if "//" in code:
            code = code.split("//", 1)[0]
        # Walk only the parts inside double-quoted strings.
        i = 0
        in_string = False
        while i < len(code):
            ch = code[i]
            if in_string:
                if ch == "\\" and i + 1 < len(code):
                    i += 2
                    continue
                if ch == '"':
                    in_string = False
                elif ord(ch) > 0x7E or ord(ch) < 0x20:
                    issues.append(
                        f"{rel_path}:{index}: non-ASCII character {ch!r} (U+{ord(ch):04X}) "
                        f"inside string literal — XS tokenizer rejects multi-byte chars"
                    )
                    break  # one issue per line is enough
                i += 1
                continue
            if ch == '"':
                in_string = True
            i += 1

    return issues


def check_unknown_xs_calls(file_path: Path, lines: list[str], repo_root: Path) -> list[str]:
    issues: list[str] = []
    rel_path = repo_relative(file_path, repo_root)

    for index, line in enumerate(lines, start=1):
        code = line.split("//", 1)[0]
        stripped = code.strip()
        if not stripped:
            continue

        for match in FUNCTION_CALL_RE.finditer(code):
            function_name = match.group(1)
            if function_name.startswith("xs") and function_name not in STOCK_XS_CALLS and function_name not in UNSUPPORTED_BUILTINS:
                issues.append(
                    f"{rel_path}:{index}: unknown xs-prefixed call '{function_name}' is outside the stock AoE3 XS surface"
                )

    return issues


def flatten_loader_includes(entry_file: Path, ai_root: Path) -> list[tuple[Path, int, str]]:
    ordered_lines: list[tuple[Path, int, str]] = []
    visited: set[Path] = set()

    def visit(file_path: Path) -> None:
        resolved = file_path.resolve()
        if resolved in visited or not file_path.exists():
            return
        visited.add(resolved)

        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines, start=1):
            if match := INCLUDE_RE.match(line):
                include_path = ai_root / match.group(1).replace("\\", "/")
                visit(include_path)
                continue
            ordered_lines.append((file_path, index, line))

    visit(entry_file)
    return ordered_lines


def should_track_loader_call(function_name: str) -> bool:
    if function_name in KNOWN_LANGUAGE_CALLS:
        return False
    if function_name.startswith(KNOWN_ENGINE_PREFIXES):
        return False
    return True


def resolve_base_game_ai_root() -> Path | None:
    for candidate in BASE_GAME_AI_PATHS:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    return None


CV_DECL_RE = re.compile(
    r"^\s*(?:mutable\s+|extern\s+|const\s+|extern\s+const\s+)*"
    r"(?:int|bool|float|string|vector)\s+"
    r"(cv[A-Z][A-Za-z0-9_]*)\s*(?:=|;)"
)
CV_USE_RE = re.compile(r"\b(cv[A-Z][A-Za-z0-9_]*)\b")

G_DECL_RE = re.compile(
    r"^\s*(?:mutable\s+|extern\s+|const\s+|extern\s+const\s+|static\s+)*"
    r"(?:int|bool|float|string|vector)\s+"
    r"(g[A-Z][A-Za-z0-9_]*)\s*(?:=|;|\[)"
)
G_USE_RE = re.compile(r"\bg[A-Z][A-Za-z0-9_]*\b")


def collect_declared_cv_vars(ai_root: Path) -> set[str]:
    """Collect cv-prefixed civ-variable declarations including function-pointer
    variants like ``extern int(int, int) cvCreateBaseAttackRoute = ...``. These
    are settable AI knobs the engine looks up by exact name — an assignment to
    an undeclared cv-symbol produces XS ERROR 0310 at runtime."""
    declared: set[str] = set()
    for file_path in iter_xs_files(ai_root):
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_block_comment = False
        for line in lines:
            code, in_block_comment = strip_inline_block_comments(line, in_block_comment)
            code = strip_string_literals(code)
            if match := CV_DECL_RE.match(code):
                declared.add(match.group(1))
            # Function-pointer cv declarations.
            for match in FUNCTION_PTR_DECL_RE.finditer(code):
                name = match.group(1)
                if name.startswith("cv") and len(name) >= 3 and name[2].isupper():
                    declared.add(name)
    return declared


def check_undefined_cv_vars(repo_root: Path) -> list[str]:
    """Flag cv-prefixed symbol uses that have no extern declaration in the
    mod or base-game AI. Catches ``cvMinNumVills = 18`` patterns where the
    variable was never declared, which the XS VM rejects with
    ``XS ERROR 0310: INVALID SYMBOL LOOKUP FOR ...``."""
    ai_root = repo_root / "game" / "ai"
    if not ai_root.exists():
        return []

    declared = collect_declared_cv_vars(ai_root)
    base_root = resolve_base_game_ai_root()
    if base_root is not None:
        try:
            declared |= collect_declared_cv_vars(base_root)
        except OSError:
            pass

    issues: list[str] = []
    for file_path in iter_xs_files(ai_root):
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_block_comment = False
        rel_path = repo_relative(file_path, repo_root)

        for index, line in enumerate(lines, start=1):
            uncommented, in_block_comment = strip_inline_block_comments(line, in_block_comment)
            code = uncommented.split("//", 1)[0]
            # Skip the declaration line itself.
            if CV_DECL_RE.match(code):
                continue
            scan_target = strip_string_literals(code)
            if not scan_target.strip():
                continue
            for match in CV_USE_RE.finditer(scan_target):
                name = match.group(1)
                if name not in declared:
                    issues.append(
                        f"{rel_path}:{index}: undefined cv-variable '{name}' — not declared as extern int/bool/float/string/vector in the mod or base game"
                    )

    return issues


def collect_declared_g_vars(ai_root: Path) -> set[str]:
    """Collect g-prefixed module-global declarations. Convention: g[A-Z]\\w+
    in this codebase always names a module global (never a local), so a use
    of an undeclared g-symbol is a typo that the engine rejects with
    ``XS Error 0172: '<name>' IS NOT A VALID OPERATOR``."""
    declared: set[str] = set()
    for file_path in iter_xs_files(ai_root):
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_block_comment = False
        for line in lines:
            code, in_block_comment = strip_inline_block_comments(line, in_block_comment)
            code = strip_string_literals(code)
            if match := G_DECL_RE.match(code):
                declared.add(match.group(1))
            for match in FUNCTION_PTR_DECL_RE.finditer(code):
                name = match.group(1)
                if (
                    len(name) >= 2
                    and name[0] == "g"
                    and name[1].isupper()
                ):
                    declared.add(name)
    return declared


def check_undefined_g_vars(repo_root: Path) -> list[str]:
    """Flag g-prefixed symbol uses that have no declaration in the mod or
    base-game AI. Catches typos like ``gTownCenterUnit`` (real symbol is
    ``cUnitTypeTownCenter``) or ``gFishingBoatUnit`` (real symbol is
    ``gFishingUnit``) before they crash the AI at runtime."""
    ai_root = repo_root / "game" / "ai"
    if not ai_root.exists():
        return []

    declared = collect_declared_g_vars(ai_root)
    base_root = resolve_base_game_ai_root()
    if base_root is not None:
        try:
            declared |= collect_declared_g_vars(base_root)
        except OSError:
            pass

    issues: list[str] = []
    for file_path in iter_xs_files(ai_root):
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_block_comment = False
        rel_path = repo_relative(file_path, repo_root)

        for index, line in enumerate(lines, start=1):
            uncommented, in_block_comment = strip_inline_block_comments(line, in_block_comment)
            code = uncommented.split("//", 1)[0]
            # Skip the declaration line itself.
            if G_DECL_RE.match(code):
                continue
            scan_target = strip_string_literals(code)
            if not scan_target.strip():
                continue
            for match in G_USE_RE.finditer(scan_target):
                name = match.group(0)
                if name not in declared:
                    issues.append(
                        f"{rel_path}:{index}: undefined g-variable '{name}' "
                        f"— not declared as extern int/bool/float/string/vector "
                        f"in the mod or base game"
                    )

    return issues


def check_undefined_helper_calls(repo_root: Path) -> list[str]:
    """Flag calls to non-engine, non-language functions that have no definition
    anywhere in the mod's AI or the installed base-game AI. Catches e.g. a
    typo'd helper name that the engine's XS VM will reject at runtime with
    ``ERROR 0172: '...' IS NOT A VALID OPERATOR``.
    """
    ai_root = repo_root / "game" / "ai"
    if not ai_root.exists():
        return []

    declared = collect_declared_callables(ai_root)
    base_root = resolve_base_game_ai_root()
    if base_root is not None:
        try:
            declared |= collect_declared_callables(base_root)
        except OSError:
            # Base game path exists but we can't read it — fall back to mod-only.
            pass

    issues: list[str] = []
    for file_path in iter_xs_files(ai_root):
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_block_comment = False
        rel_path = repo_relative(file_path, repo_root)

        for index, line in enumerate(lines, start=1):
            uncommented, in_block_comment = strip_inline_block_comments(line, in_block_comment)
            code = uncommented.split("//", 1)[0]
            declaration_match = CALLABLE_DECL_RE.match(code)
            declared_here = declaration_match.group(1) if declaration_match else None
            scan_target = strip_string_literals(code)
            stripped = scan_target.strip()
            if not stripped:
                continue

            for match in FUNCTION_CALL_RE.finditer(scan_target):
                function_name = match.group(1)
                if function_name in KNOWN_LANGUAGE_CALLS:
                    continue
                if function_name.startswith(KNOWN_ENGINE_PREFIXES):
                    continue
                if function_name in STOCK_XS_CALLS or function_name in KNOWN_ENGINE_CALLS:
                    continue
                if function_name.startswith("debug"):
                    continue
                if declared_here is not None and function_name == declared_here:
                    continue
                if function_name in declared:
                    continue
                issues.append(
                    f"{rel_path}:{index}: undefined helper call '{function_name}' — not declared in the mod or base game"
                )

    return issues


def check_unresolved_loader_calls(repo_root: Path) -> list[str]:
    ai_root = repo_root / "game" / "ai"
    loader_path = ai_root / "aiLoaderStandard.xs"
    if not loader_path.exists():
        return []

    issues: list[str] = []
    known_helpers: set[str] = set()
    declared_callables = collect_declared_callables(ai_root)
    in_block_comment = False

    for file_path, index, line in flatten_loader_includes(loader_path, ai_root):
        uncommented, in_block_comment = strip_inline_block_comments(line, in_block_comment)
        code = uncommented.split("//", 1)[0]
        stripped = code.strip()
        if not stripped:
            continue

        declaration_match = CALLABLE_DECL_RE.match(code)
        if declaration_match is not None:
            known_helpers.add(declaration_match.group(1))
        if rule_match := RULE_RE.match(code):
            known_helpers.add(rule_match.group(1))
        for ptr_match in FUNCTION_PTR_DECL_RE.finditer(code):
            known_helpers.add(ptr_match.group(1))

        scan_target = strip_string_literals(code)
        for match in FUNCTION_CALL_RE.finditer(scan_target):
            function_name = match.group(1)
            if should_track_loader_call(function_name) is False:
                continue
            if function_name not in declared_callables:
                continue
            if declaration_match is not None and function_name == declaration_match.group(1):
                continue
            if function_name not in known_helpers:
                rel_path = repo_relative(file_path, repo_root)
                issues.append(
                    f"{rel_path}:{index}: helper call '{function_name}' appears before any declaration in aiLoaderStandard include order"
                )

    return issues


def validate_xs_scripts(repo_root: Path = REPO_ROOT) -> list[str]:
    ai_root = repo_root / "game" / "ai"
    if not ai_root.exists():
        return [f"AI folder not found: {repo_relative(ai_root, repo_root)}"]

    issues: list[str] = []
    for file_path in iter_xs_files(ai_root):
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        issues.extend(check_duplicate_names(file_path, lines, repo_root))
        issues.extend(check_duplicate_locals(file_path, lines, repo_root))
        issues.extend(check_unsupported_builtins(file_path, lines, repo_root))
        issues.extend(check_unknown_xs_calls(file_path, lines, repo_root))
        issues.extend(check_non_ascii_in_strings(file_path, lines, repo_root))

    issues.extend(check_undefined_helper_calls(repo_root))
    issues.extend(check_undefined_cv_vars(repo_root))
    issues.extend(check_undefined_g_vars(repo_root))
    issues.extend(check_unresolved_loader_calls(repo_root))

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate XS duplicate symbols and duplicate rule locals.")
    args = parser.parse_args()
    issues = validate_xs_scripts(args.repo_root.resolve())

    if issues:
        print("XS validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("XS validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
