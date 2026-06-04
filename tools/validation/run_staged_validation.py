from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, repo_relative
from tools.validation.validate_civ_crossrefs import validate_civ_crossrefs
from tools.validation.validate_civ_homecities import validate_civ_homecities
from tools.validation.validate_civmods_ui import validate_civmods_ui
from tools.validation.validate_homecity_cards import validate_homecity_cards
from tools.validation.validate_homecity_visuals import validate_homecity_visuals
from tools.validation.validate_packaged_mod import validate_packaged_mod_with_options
from tools.validation.validate_live_mod_install import validate_live_mod_install
from tools.validation.validate_playercolors import validate_playercolors
from tools.validation.validate_html_reference import validate_html_reference
from tools.validation.validate_html_vs_mod import validate_html_vs_mod
from tools.validation.validate_playstyle_modal import validate_playstyle_modal
from tools.validation.validate_protomods import validate_protomods
from tools.validation.validate_runtime_logs import DEFAULT_LOG_PATH, validate_runtime_log
from tools.playtest.coverage_v2 import run_all_checks as _cov2_run_all_checks
from tools.validation.validate_stringtables import validate_stringtables
from tools.validation.validate_techtree import validate_techtree
from tools.validation.validate_terrain_heading import validate_terrain_heading
from tools.validation.validate_xml_well_formed import validate_xml_well_formed
from tools.validation.validate_xs_scripts import validate_xs_scripts
from tools.validation.validate_personality_overrides import validate_personality_overrides
from tools.validation.validate_art_coverage import validate_art_coverage
from tools.validation.validate_dev_subtrees import validate_dev_subtrees


STAGE_ORDER = ("content", "regression", "packaged", "live", "runtime")


@dataclass(frozen=True)
class ValidationCheckResult:
    name: str
    findings: list[str]

    @property
    def passed(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    summary: str
    details: list[str]

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def normalize_stage_names(requested_stages: list[str]) -> list[str]:
    if not requested_stages or "all" in requested_stages:
        return list(STAGE_ORDER)

    normalized: list[str] = []
    seen: set[str] = set()
    for stage_name in STAGE_ORDER:
        if stage_name in requested_stages and stage_name not in seen:
            normalized.append(stage_name)
            seen.add(stage_name)
    return normalized


def build_content_checks(repo_root: Path, strict_display_name_ids: bool = False) -> list[ValidationCheckResult]:
    return [
        ValidationCheckResult("Civ Crossrefs", validate_civ_crossrefs(repo_root, validate_display_name_ids=strict_display_name_ids)),
        ValidationCheckResult("Civ HomeCities", validate_civ_homecities(repo_root)),
        ValidationCheckResult("HomeCity Cards", validate_homecity_cards(repo_root)),
        ValidationCheckResult("HomeCity Visuals", validate_homecity_visuals(repo_root)),
        ValidationCheckResult("Civ UI", validate_civmods_ui(repo_root)),
        ValidationCheckResult("Proto", validate_protomods(repo_root)),
        ValidationCheckResult("StringTables", validate_stringtables(repo_root)),
        ValidationCheckResult("TechTree", validate_techtree(repo_root)),
        ValidationCheckResult("XML Well-Formedness", validate_xml_well_formed(repo_root)),
        ValidationCheckResult("XS", validate_xs_scripts(repo_root)),
        ValidationCheckResult("Terrain/Heading Wiring", validate_terrain_heading(repo_root)),
        ValidationCheckResult(
            "Playstyle Modal",
            validate_playstyle_modal(
                repo_root,
                # Auto-enable imperial-peer enforcement once the data file
                # has been authored. Until then we only require the base
                # civ-doctrine fields.
                require_imperial=(repo_root / "tools" / "playstyle" / "imperial_data.py").is_file(),
            ),
        ),
        ValidationCheckResult("Personality Overrides", validate_personality_overrides(repo_root)),
        ValidationCheckResult("Art Coverage", validate_art_coverage(repo_root)),
        ValidationCheckResult("Player Colors", validate_playercolors(repo_root)),
        ValidationCheckResult("HTML Reference Structure", validate_html_reference(repo_root)),
        ValidationCheckResult("HTML vs Mod Consistency", validate_html_vs_mod(repo_root)),
        ValidationCheckResult("Dev Subtrees", validate_dev_subtrees(repo_root)),
    ]


def summarize_check_results(results: list[ValidationCheckResult]) -> tuple[str, list[str], str]:
    passing = sum(1 for result in results if result.passed)
    failing = len(results) - passing
    status = "pass" if failing == 0 else "fail"
    summary = f"{passing}/{len(results)} checks passed"

    details: list[str] = []
    for result in results:
        if result.passed:
            details.append(f"PASS {result.name}")
            continue
        details.append(f"FAIL {result.name}")
        for finding in result.findings:
            details.append(f"  - {finding}")
    return status, details, summary


def run_content_stage(repo_root: Path, strict_display_name_ids: bool = False) -> StageResult:
    checks = build_content_checks(repo_root, strict_display_name_ids=strict_display_name_ids)
    status, details, summary = summarize_check_results(checks)
    return StageResult(name="Content Validation", status=status, summary=summary, details=details)


def run_regression_stage(repo_root: Path) -> StageResult:
    # Discover both the validator regression tests and the playtest
    # harness tests in a single pass so anything under tests/ is run.
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_*.py",
        "-t",
        ".",
    ]
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True)
    output_lines = [line.rstrip() for line in (completed.stdout + completed.stderr).splitlines() if line.strip()]

    if completed.returncode == 0:
        summary = output_lines[-1] if output_lines else "Validator regression tests passed"
        details = [summary]
        return StageResult(name="Validator Regression Tests", status="pass", summary=summary, details=details)

    details = output_lines[-20:] if output_lines else ["unittest discovery failed without output"]
    summary = details[-1]
    return StageResult(name="Validator Regression Tests", status="fail", summary=summary, details=details)


def run_packaged_stage(repo_root: Path, strict_display_name_ids: bool = False) -> StageResult:
    packaged_result = validate_packaged_mod_with_options(
        repo_root,
        validate_display_name_ids=strict_display_name_ids,
    )
    findings = packaged_result.issues
    if findings:
        details = [f"FAIL Packaged Mod"] + [f"  - {finding}" for finding in findings]
        return StageResult(
            name="Packaged Mod Validation",
            status="fail",
            summary=f"{len(findings)} packaged validation issue(s)",
            details=details,
        )

    return StageResult(
        name="Packaged Mod Validation",
        status="pass",
        summary="packaged mod validation passed",
        details=["PASS Packaged Mod"],
    )


def run_live_stage(repo_root: Path, live_root: Path | None = None) -> StageResult:
    result = validate_live_mod_install(repo_root=repo_root, live_root=live_root)
    if result.live_root.exists() is False:
        return StageResult(
            name="Live Mod Install Validation",
            status="skipped",
            summary=f"live mod install not found at {result.live_root}",
            details=[
                f"live mod install not found at {result.live_root}",
                "Next: sync or copy the current mod into the active Proton local mod folder, then rerun this stage.",
            ],
        )

    if result.issues:
        return StageResult(
            name="Live Mod Install Validation",
            status="fail",
            summary=f"{len(result.issues)} live install issue(s)",
            details=[f"FAIL Live Mod Install ({result.live_root})"] + [f"  - {issue}" for issue in result.issues],
        )

    return StageResult(
        name="Live Mod Install Validation",
        status="pass",
        summary="live mod install matches packaged payload",
        details=[f"PASS Live Mod Install ({result.live_root})"],
    )


_COV2_SUITES = {"pacing_v2", "shipment_order_v2", "escort_v2"}
_COV2_ALL = sorted(_COV2_SUITES)


def run_runtime_stage(repo_root: Path, log_path: Path, suite_names: list[str],
                      all_runtime_suites: bool = False) -> StageResult:
    if not log_path.exists():
        summary = f"runtime log not found at {repo_relative(log_path, repo_root)}"
        details = [
            summary,
            "Next: run the deterministic scenario or test map, then rerun this stage with --runtime-log-path.",
            "Scenario spec: Scenario/TEST_SCENARIO_SETUP.md",
            "Automation matrix: Scenario/CHECKLIST_AUTOMATION_MATRIX.md",
            "Scenario binary: Scenario/ANEWWORLD.age3Yscn",
        ]
        return StageResult(name="Runtime Log Validation", status="skipped", summary=summary, details=details)

    issues = validate_runtime_log(repo_root=repo_root, log_path=log_path, suite_names=suite_names)

    # Run coverage_v2 suites if requested via --all-runtime-suites or explicit
    # suite names (pacing_v2 / shipment_order_v2 / escort_v2).
    cov2_suites = [s for s in suite_names if s in _COV2_SUITES]
    if all_runtime_suites:
        cov2_suites = _COV2_ALL
    if cov2_suites:
        text = log_path.read_text(encoding="utf-8", errors="replace")
        cov2_errors, cov2_warnings = _cov2_run_all_checks(text)
        # Filter to requested suites
        wanted = set(cov2_suites)
        def _suite_tag(msg: str) -> str:
            import re as _re
            m = _re.search(r"\[(\w+_v2)\]", msg)
            return m.group(1) if m else ""
        for e in cov2_errors:
            if not wanted or _suite_tag(e) in wanted:
                issues.append(e)
        for w in cov2_warnings:
            if not wanted or _suite_tag(w) in wanted:
                issues.append(f"WARN: {w}")

    if issues:
        return StageResult(
            name="Runtime Log Validation",
            status="fail",
            summary=f"{len(issues)} runtime validation issue(s)",
            details=[f"FAIL Runtime Log Validation"] + [f"  - {issue}" for issue in issues],
        )

    suite_summary = ", ".join(suite_names) if suite_names else "all suites"
    if all_runtime_suites:
        suite_summary += " + pacing_v2,shipment_order_v2,escort_v2"
    return StageResult(
        name="Runtime Log Validation",
        status="pass",
        summary=f"runtime log validation passed for {suite_summary}",
        details=[f"PASS Runtime Log Validation ({suite_summary})"],
    )


def format_stage_report(stage_results: list[StageResult]) -> str:
    lines = ["A New World staged validation report", ""]
    for stage in stage_results:
        lines.append(f"[{stage.status.upper()}] {stage.name}: {stage.summary}")
        for detail in stage.details:
            lines.append(f"  {detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = build_repo_root_parser("Run the staged A New World validation workflow locally.")
    parser.add_argument(
        "--stage",
        action="append",
        choices=["all", *STAGE_ORDER],
        default=[],
        help="Stage to run. Repeat to run multiple stages. Defaults to all stages.",
    )
    parser.add_argument(
        "--runtime-log-path",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="Age3Log.txt path for the runtime stage. Defaults to the standard Proton log location.",
    )
    parser.add_argument(
        "--runtime-suite",
        action="append",
        default=[],
        help="Runtime suite name to validate during the runtime stage. Repeat to validate multiple suites.",
    )
    parser.add_argument(
        "--all-runtime-suites",
        action="store_true",
        default=False,
        help="Run all runtime suites including pacing_v2, shipment_order_v2, and escort_v2.",
    )
    parser.add_argument(
        "--live-root",
        type=Path,
        help="Explicit active Proton local-mod root for the live stage.",
    )
    parser.add_argument(
        "--strict-display-name-ids",
        action="store_true",
        help="Require DisplayNameID locIDs to resolve from repo StringTables in cross-reference checks.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        help="Optional path to write the staged validation report to.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    selected_stages = normalize_stage_names(args.stage)
    stage_results: list[StageResult] = []

    for stage_name in selected_stages:
        if stage_name == "content":
            stage_results.append(run_content_stage(repo_root, strict_display_name_ids=args.strict_display_name_ids))
        elif stage_name == "regression":
            stage_results.append(run_regression_stage(repo_root))
        elif stage_name == "packaged":
            stage_results.append(run_packaged_stage(repo_root, strict_display_name_ids=args.strict_display_name_ids))
        elif stage_name == "live":
            stage_results.append(run_live_stage(repo_root, live_root=args.live_root))
        elif stage_name == "runtime":
            stage_results.append(
                run_runtime_stage(
                    repo_root,
                    log_path=args.runtime_log_path.resolve(),
                    suite_names=args.runtime_suite,
                    all_runtime_suites=args.all_runtime_suites,
                )
            )
        else:
            raise ValueError(f"Unsupported stage: {stage_name}")

    report = format_stage_report(stage_results)
    print(report, end="")

    if args.report_file is not None:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(report, encoding="utf-8")

    if any(stage.status == "fail" for stage in stage_results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())