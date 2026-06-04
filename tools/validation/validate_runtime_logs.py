from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, repo_relative


DEFAULT_LOG_PATH = Path.home() / ".steam/steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
DEFAULT_SPEC_PATH = REPO_ROOT / "tools" / "validation" / "runtime_specs" / "anw_runtime_suites.json"
DEFAULT_XS_GLOB = "game/ai/core/*.xs"


@dataclass(frozen=True)
class RuntimeExpectation:
    kind: str
    value: str
    description: str


def load_runtime_spec(spec_path: Path) -> dict:
    with spec_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Runtime spec must be a JSON object: {spec_path}")
    suites = payload.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError(f"Runtime spec must contain a non-empty 'suites' array: {spec_path}")
    return payload


def normalize_expectations(raw_items: list[dict], field: str, default_kind: str) -> list[RuntimeExpectation]:
    expectations: list[RuntimeExpectation] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError(f"Each '{field}' entry must be an object")
        value = item.get("value")
        if not isinstance(value, str) or not value:
            raise ValueError(f"Each '{field}' entry requires a non-empty string 'value'")
        kind = item.get("kind", default_kind)
        if kind not in {"substring", "regex"}:
            raise ValueError(f"Unsupported expectation kind '{kind}' in '{field}'")
        description = item.get("description", value)
        if not isinstance(description, str) or not description:
            raise ValueError(f"Each '{field}' entry requires a non-empty string 'description'")
        expectations.append(RuntimeExpectation(kind=kind, value=value, description=description))
    return expectations


_REGEX_METACHARS = r"\^$.|?*+()[]{}"


def _regex_literal_prefix(pattern: str) -> str:
    """Return the longest literal-substring prefix of a regex pattern.

    For e.g. ``\\[UNIT\\] ai-rout-blocked unit=\\d+ reason=elite-support`` the
    result is ``[UNIT] ai-rout-blocked unit=`` — the longest run of
    characters with no unescaped metachar. Uses ``\\X`` → ``X`` to handle
    standard regex escapes for literal punctuation (``\\[`` → ``[``).
    Returns ``""`` if the pattern starts with an unescaped metachar.
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\" and i + 1 < len(pattern):
            nxt = pattern[i + 1]
            if nxt in _REGEX_METACHARS or nxt == "\\":
                # Escaped metachar → literal punctuation.
                out.append(nxt)
                i += 2
                continue
            # ``\d``, ``\w``, ``\s`` etc. → variable; stop here.
            break
        if ch in _REGEX_METACHARS:
            break
        out.append(ch)
        i += 1
    return "".join(out)


def expectation_matches(expectation: RuntimeExpectation, text: str) -> bool:
    if expectation.kind == "substring":
        return expectation.value in text
    return re.search(expectation.value, text, re.MULTILINE) is not None


def expectation_position(expectation: RuntimeExpectation, text: str) -> int:
    if expectation.kind == "substring":
        return text.find(expectation.value)
    match = re.search(expectation.value, text, re.MULTILINE)
    if match is None:
        return -1
    return match.start()


def validate_static_emitters(repo_root: Path, spec_path: Path,
                              suite_names: list[str] | None = None) -> tuple[list[str], int]:
    """Static-mode: scan XS source for emitter sites of every required marker.

    Returns (issues, total_checked).
    """
    if not spec_path.exists():
        return [f"Runtime spec not found: {repo_relative(spec_path, repo_root)}"], 0

    try:
        spec = load_runtime_spec(spec_path)
    except ValueError as exc:
        return [str(exc)], 0

    # Collect all XS source text once.
    xs_dir = repo_root / "game" / "ai" / "core"
    xs_files = sorted(xs_dir.glob("*.xs")) if xs_dir.is_dir() else []
    combined_xs = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in xs_files)

    available_suites = {suite.get("name"): suite for suite in spec["suites"] if isinstance(suite, dict)}
    selected = list(available_suites.keys()) if not suite_names else suite_names

    issues: list[str] = []
    total_checked = 0

    for suite_name in selected:
        suite = available_suites.get(suite_name)
        if suite is None:
            issues.append(f"Unknown runtime suite '{suite_name}'")
            continue

        required = normalize_expectations(suite.get("required", []), "required", "substring")
        ordered = normalize_expectations(suite.get("ordered", []), "ordered", "substring")
        # In static mode we check that the *values* (substrings) appear in XS source.
        #
        # Subtlety: the production helper ``debugLegendaryLeaders(msg)`` in
        # game/ai/core/aiUtilities.xs prepends the literal "A New World: "
        # at runtime — call sites pass only the suffix. So when the spec
        # wants e.g. "A New World: [UNIT] ai-rout-start unit=", an XS
        # source check for that exact string will fail even when the
        # emitter exists. We therefore *also* try the value with the
        # "A New World: " prefix stripped — that's the form callers
        # actually use in source code.
        _ANW_PREFIX = "A New World: "
        _ANW_REGEX_PREFIX = "A New World: "  # same string, in regex form
        for expectation in list(required) + list(ordered):
            total_checked += 1
            if expectation.kind == "substring":
                found = expectation.value in combined_xs
                if not found and expectation.value.startswith(_ANW_PREFIX):
                    found = expectation.value[len(_ANW_PREFIX):] in combined_xs
            else:
                found = re.search(expectation.value, combined_xs, re.MULTILINE) is not None
                if not found and expectation.value.startswith(_ANW_REGEX_PREFIX):
                    stripped = expectation.value[len(_ANW_REGEX_PREFIX):]
                    found = re.search(stripped, combined_xs, re.MULTILINE) is not None
                # Regex patterns with variable parts (e.g. ``unit=\d+``) won't
                # match XS source where the runtime value is filled by string
                # concatenation (``unit=" + unitID + "``). Fall back to the
                # literal-prefix substring up to the first regex metachar so
                # we can still confirm the emitter call site exists.
                if not found:
                    literal_prefix = _regex_literal_prefix(expectation.value)
                    if literal_prefix:
                        found = literal_prefix in combined_xs
                        if not found and literal_prefix.startswith(_ANW_PREFIX):
                            found = literal_prefix[len(_ANW_PREFIX):] in combined_xs
            if not found:
                issues.append(
                    f"[{suite_name}] no emitter found in game/ai/core/*.xs "
                    f"for marker: {expectation.description!r} "
                    f"(value: {expectation.value!r})"
                )

    return issues, total_checked


def validate_runtime_log(repo_root: Path = REPO_ROOT, log_path: Path = DEFAULT_LOG_PATH,
                         spec_path: Path = DEFAULT_SPEC_PATH, suite_names: list[str] | None = None) -> list[str]:
    if not log_path.exists():
        return [f"Runtime log not found: {repo_relative(log_path, repo_root)}"]
    if not spec_path.exists():
        return [f"Runtime spec not found: {repo_relative(spec_path, repo_root)}"]

    try:
        spec = load_runtime_spec(spec_path)
    except ValueError as exc:
        return [str(exc)]

    text = log_path.read_text(encoding="utf-8", errors="replace")
    available_suites = {suite.get("name"): suite for suite in spec["suites"] if isinstance(suite, dict)}

    if suite_names is None or len(suite_names) == 0:
        selected_suite_names = list(available_suites.keys())
    else:
        selected_suite_names = suite_names

    issues: list[str] = []

    for suite_name in selected_suite_names:
        suite = available_suites.get(suite_name)
        if suite is None:
            issues.append(f"Unknown runtime suite '{suite_name}' in {repo_relative(spec_path, repo_root)}")
            continue

        required = normalize_expectations(suite.get("required", []), "required", "substring")
        forbidden = normalize_expectations(suite.get("forbidden", []), "forbidden", "substring")
        ordered = normalize_expectations(suite.get("ordered", []), "ordered", "substring")

        for expectation in required:
            if expectation_matches(expectation, text) is False:
                issues.append(f"[{suite_name}] missing required log marker: {expectation.description}")

        for expectation in forbidden:
            if expectation_matches(expectation, text) is True:
                issues.append(f"[{suite_name}] found forbidden log marker: {expectation.description}")

        if ordered:
            last_position = -1
            for expectation in ordered:
                position = expectation_position(expectation, text)
                if position < 0:
                    issues.append(f"[{suite_name}] missing ordered log marker: {expectation.description}")
                    break
                if position < last_position:
                    issues.append(f"[{suite_name}] ordered marker out of sequence: {expectation.description}")
                    break
                last_position = position

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate Age of Empires III runtime logs against suite-based A New World expectations.")
    parser.add_argument(
        "--log-path",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="Age3Log.txt path to validate.",
    )
    parser.add_argument(
        "--spec-path",
        type=Path,
        default=DEFAULT_SPEC_PATH,
        help="JSON spec file containing one or more runtime validation suites.",
    )
    parser.add_argument(
        "--suite",
        action="append",
        default=[],
        help="Runtime suite name to validate. Repeat to validate multiple suites. Defaults to all suites in the spec.",
    )
    parser.add_argument(
        "--static-mode",
        action="store_true",
        default=False,
        help=(
            "Offline fallback: instead of parsing a runtime log, scan "
            "game/ai/core/*.xs for emitter sites of every required marker. "
            "PASS if every marker has at least one emitter in XS source. "
            "Catches the failure mode where an emitter is removed from XS "
            "but the validator config still requires the marker."
        ),
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    spec_path = args.spec_path.resolve()
    log_path = args.log_path.resolve()

    # Static mode: explicit opt-in via --static-mode. Validates that every
    # required runtime marker has at least one emitter site in XS source.
    # Used by the 68-validator gate (run_all_validators.py) so the gate can
    # PASS without depending on a live game session. Previously this fell
    # back to live-log mode whenever ``Age3Log.txt`` existed, which made
    # the gate effectively rely on a stale log; now ``--static-mode`` is
    # unconditional.
    if args.static_mode:
        issues, total_checked = validate_static_emitters(
            repo_root=repo_root,
            spec_path=spec_path,
            suite_names=args.suite,
        )
        if issues:
            print("static-mode: runtime log emitter coverage check FAILED:")
            for issue in issues:
                print(f" - {issue}")
            return 1
        suite_summary = ", ".join(args.suite) if args.suite else "all suites"
        print(
            f"static-mode: all {total_checked} markers have emitters in "
            f"game/ai/core/*.xs for {suite_summary}. "
            "(Live log validation requires the game running.)"
        )
        return 0

    issues = validate_runtime_log(
        repo_root=repo_root,
        log_path=log_path,
        spec_path=spec_path,
        suite_names=args.suite,
    )
    if issues:
        print("Runtime log validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    suite_summary = ", ".join(args.suite) if args.suite else "all suites"
    print(f"Runtime log validation passed for {suite_summary}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())