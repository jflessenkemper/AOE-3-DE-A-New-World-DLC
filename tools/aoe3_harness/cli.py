"""ANW Test Harness — single-command CLI entry point.

Usage:
  python3 -m tools.aoe3_harness.cli deploy [--check] [--dry-run]
  python3 -m tools.aoe3_harness.cli run --pass N [--dry-run]
  python3 -m tools.aoe3_harness.cli run --all-passes [--dry-run]
  python3 -m tools.aoe3_harness.cli validate [--civ TOKEN] [--allow-fail]
  python3 -m tools.aoe3_harness.cli report
  python3 -m tools.aoe3_harness.cli gate
  python3 -m tools.aoe3_harness.cli status
  python3 -m tools.aoe3_harness.cli capture --civ <name> --surface <name> [--out <path>]
  python3 -m tools.aoe3_harness.cli input key <vk_hex>
  python3 -m tools.aoe3_harness.cli input keydown <vk_hex>
  python3 -m tools.aoe3_harness.cli input keyup <vk_hex>
  python3 -m tools.aoe3_harness.cli input click <x> <y>
  python3 -m tools.aoe3_harness.cli input move <x> <y>
  python3 -m tools.aoe3_harness.cli input state
  python3 -m tools.aoe3_harness.cli dll verify
  python3 -m tools.aoe3_harness.cli dll status
  python3 -m tools.aoe3_harness.cli hotreload start
  python3 -m tools.aoe3_harness.cli diff <before.png> <after.png> [--output heatmap.png]
  python3 -m tools.aoe3_harness.cli bisect --probe <name> --civ <token> --target <float> --good <sha> --bad <sha>

Subcommands:
  deploy    Run deploy_to_mod.py (and optionally validate_xs_scripts.py with --check)
  run       Truncate log, launch game, wait MATCH_DURATION_S, archive, validate
  validate  Re-run doctrine compliance on existing archived logs (no game launch)
  report    Rebuild release_readiness_site.html from current artifacts
  gate      Run run_all_validators.py (full static gate, no game)
  status    Print state.json summary: which passes complete, civ coverage
  capture   Screenshot the AoE3 window for a specific civ/surface combination
  input     Inject keyboard/mouse input into the running game via anw_hook.dll pipe
  dll       Inspect anw_hook.dll files (static, no game launch)
  hotreload Watch XS/XML source files and auto-deploy on save (game need not be running)
  diff      Compare two screenshots pixel-by-pixel; optionally write a heatmap PNG
  bisect    Set up git-bisect to find the commit that broke a doctrine probe

All subcommands accept --dry-run (passed through to deploy/launch).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tools.aoe3_harness.paths import (
    ARTIFACT_ROOT,
    MOD_DEPLOY_SCRIPT,
    REPO_ROOT,
    STATE_PATH,
    VISUAL_ART_ROOT,
    XS_VALIDATOR_SCRIPT,
)


def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy mod; optionally run XS static checks first.

    Args:
        args: Parsed namespace with ``check`` and ``dry_run`` attributes.

    Returns:
        0 on success, non-zero on failure.
    """
    if args.check:
        cmd = [sys.executable, str(XS_VALIDATOR_SCRIPT)]
        print(f"[cli/deploy] Running XS check: {' '.join(cmd)}")
        if not args.dry_run:
            result = subprocess.run(cmd, cwd=str(REPO_ROOT))
            if result.returncode != 0:
                print("[cli/deploy] XS validation FAILED — aborting deploy.", file=sys.stderr)
                return result.returncode
        else:
            print("[cli/deploy] dry-run: would run XS check")

    cmd = [sys.executable, str(MOD_DEPLOY_SCRIPT)]
    print(f"[cli/deploy] Running deploy: {' '.join(cmd)}")
    if not args.dry_run:
        result = subprocess.run(cmd, cwd=str(REPO_ROOT))
        return result.returncode
    else:
        print("[cli/deploy] dry-run: would run deploy")
        return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run one or all passes via supervisor.run_pass().

    Args:
        args: Parsed namespace with ``pass_number``, ``all_passes``, and
              ``dry_run`` attributes.

    Returns:
        0 on success, non-zero on failure.
    """
    from tools.aoe3_harness.supervisor import PASS_CIVS, run_pass

    if args.all_passes:
        passes = sorted(PASS_CIVS.keys())
    else:
        passes = [args.pass_number]

    for p in passes:
        try:
            run_pass(p, dry_run=args.dry_run)
        except Exception as exc:  # noqa: BLE001
            print(f"[cli/run] Pass {p} FAILED: {exc}", file=sys.stderr)
            return 1
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Re-validate existing archived logs (no game launch).

    Args:
        args: Parsed namespace with ``civ``, ``allow_fail``, and ``dry_run``
              attributes.

    Returns:
        subprocess exit code from the validator.
    """
    from tools.aoe3_harness.validator import validate_pass

    rc = validate_pass(
        allow_empty=True,
        allow_fail=args.allow_fail,
    )
    return rc


def cmd_report(args: argparse.Namespace) -> int:
    """Rebuild release_readiness_site.html.

    Args:
        args: Parsed namespace (unused beyond dry_run).

    Returns:
        subprocess exit code from the report builder.
    """
    from tools.aoe3_harness.validator import build_release_site

    return build_release_site()


def cmd_gate(args: argparse.Namespace) -> int:
    """Run full static validation gate.

    Equivalent to running ``python3 tools/validation/run_all_validators.py``
    directly.

    Args:
        args: Parsed namespace (unused beyond dry_run).

    Returns:
        subprocess exit code.
    """
    gate_script = REPO_ROOT / "tools" / "validation" / "run_all_validators.py"
    if not gate_script.exists():
        print(
            f"[cli/gate] ERROR: {gate_script} not found.",
            file=sys.stderr,
        )
        return 2
    result = subprocess.run([sys.executable, str(gate_script)], cwd=str(REPO_ROOT))
    return result.returncode


def cmd_status(args: argparse.Namespace) -> int:
    """Print state.json summary: which passes complete, civ coverage.

    Args:
        args: Parsed namespace (unused).

    Returns:
        Always 0.
    """
    if not STATE_PATH.exists():
        print("[status] No state.json found. No passes have been run yet.")
        return 0

    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[status] ERROR reading state.json: {exc}", file=sys.stderr)
        return 2

    passes_complete: list = state.get("passes_complete", [])
    passes_archive: dict = state.get("passes_archive", {})
    civ_coverage: dict = state.get("civ_coverage", {})
    last_run: str = state.get("last_run_ts") or "(never)"

    print(f"\n{'='*60}")
    print("  ANW Test Harness — Status")
    print(f"{'='*60}")
    print(f"  Last run:        {last_run}")
    print(f"  Passes complete: {passes_complete if passes_complete else '(none)'}")
    print()

    if passes_archive:
        print("  Archives:")
        for p, path in sorted(passes_archive.items(), key=lambda x: int(x[0])):
            print(f"    Pass {p}: {path}")
        print()

    total_civs = sum(
        len(civs)
        for civs in [
            ["ANWCanadians", "ANWAztecs", "ANWBarbary", "ANWBrazil", "ANWGermans", "ANWArgentines", "ANWChileans"],
            ["ANWHaitians", "ANWBritish", "ANWHausa", "ANWItalians", "ANWColumbians", "ANWChinese", "ANWIndonesians"],
            ["ANWDutch", "ANWRomanians", "ANWMexicans", "ANWHaudenosaunee", "ANWEgyptians", "ANWMayans", "ANWPortuguese"],
            ["ANWRussians", "ANWRevFrance", "ANWHungarians", "ANWEthiopians", "ANWSouthAfricans", "ANWUSA", "ANWJapanese"],
            ["ANWFinnish", "ANWLakota", "ANWFrench", "ANWNapoleonicFrance", "ANWInca", "ANWSpanish", "ANWIndians"],
            ["ANWSwedes", "ANWMaltese", "ANWTexians", "ANWOttomans", "ANWPeruvians"],
        ]
    )

    if civ_coverage:
        n_pass = sum(1 for v in civ_coverage.values() if v.get("status") == "PASS")
        n_fail = sum(1 for v in civ_coverage.values() if v.get("status") == "FAIL")
        n_unknown = len(civ_coverage) - n_pass - n_fail
        print(f"  Civ coverage: {len(civ_coverage)}/{total_civs} civs seen")
        print(f"    PASS:    {n_pass}")
        print(f"    FAIL:    {n_fail}")
        print(f"    UNKNOWN: {n_unknown}")
        print()
        for civ, info in sorted(civ_coverage.items()):
            probes = info.get("probes", "?")
            status = info.get("status", "?")
            print(f"    {civ:<30} probes={probes:>4}  status={status}")
    else:
        print(f"  Civ coverage: 0/{total_civs} civs seen (no passes run yet)")

    print(f"{'='*60}\n")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    """Screenshot the AoE3 window for a specific civ/surface combination.

    Prompts the user to navigate to the correct UI state, then captures the
    game window pixels via ImageMagick ``import -window`` (no cursor grab).

    Args:
        args: Parsed namespace with ``civ``, ``surface``, ``out``, and
              ``dry_run`` attributes.

    Returns:
        0 on success, 1 on failure.
    """
    from tools.aoe3_harness.capture import capture_window, find_aoe3_window

    civ: str = args.civ
    surface: str = args.surface

    # Resolve output path
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = VISUAL_ART_ROOT / civ / f"{surface}.png"

    print(f"\n[cli/capture] Civ:     {civ}")
    print(f"[cli/capture] Surface: {surface}")
    print(f"[cli/capture] Output:  {out_path}")
    print()
    print("[cli/capture] Navigate AoE3 to the target UI state.")
    input("[cli/capture] Press Enter when ready to capture... ")

    wid = find_aoe3_window()
    if wid is None:
        print(
            "[cli/capture] ERROR: AoE3 window not found. "
            "Is the game running in borderless windowed mode?",
            file=sys.stderr,
        )
        return 1

    print(f"[cli/capture] Found AoE3 window: 0x{wid:x}")

    if args.dry_run:
        print(f"[cli/capture] dry-run: would capture 0x{wid:x} -> {out_path}")
        return 0

    ok = capture_window(wid, out_path)
    if ok:
        size = out_path.stat().st_size
        print(f"[cli/capture] OK — {out_path} ({size} bytes)")
        return 0
    else:
        print("[cli/capture] FAILED", file=sys.stderr)
        return 1


def cmd_input(args: argparse.Namespace) -> int:
    """Inject keyboard/mouse input into the game via the anw_hook.dll named pipe.

    Requires the game to be running with anw_hook.dll loaded
    (WINEDLLOVERRIDES="anw_hook=n,b").  Connects to the Wine Unix socket,
    sends the command, and prints the response.

    Args:
        args: Parsed namespace with ``input_cmd`` and optional ``vk``, ``x``,
              ``y`` attributes.

    Returns:
        0 on success, 1 on error.
    """
    from tools.aoe3_harness.dll_client import DllClient, DllClientError

    try:
        with DllClient() as client:
            if args.input_cmd == "state":
                print(client.state())

            elif args.input_cmd == "key":
                vk = int(args.vk, 16) if args.vk.startswith("0x") else int(args.vk, 16)
                client.press_key(vk)
                print(f"OK (pressed vk={args.vk})")

            elif args.input_cmd == "keydown":
                vk = int(args.vk, 16) if args.vk.startswith("0x") else int(args.vk, 16)
                client.key_down(vk)
                print(f"OK (key_down vk={args.vk})")

            elif args.input_cmd == "keyup":
                vk = int(args.vk, 16) if args.vk.startswith("0x") else int(args.vk, 16)
                client.key_up(vk)
                print(f"OK (key_up vk={args.vk})")

            elif args.input_cmd == "click":
                client.click(args.x, args.y)
                print(f"OK (click {args.x},{args.y})")

            elif args.input_cmd == "move":
                client.move(args.x, args.y)
                print(f"OK (move {args.x},{args.y})")

            else:
                print(f"[cli/input] Unknown input subcommand: {args.input_cmd}", file=sys.stderr)
                return 1

    except ConnectionError as exc:
        print(
            f"[cli/input] Could not connect to anw_hook pipe: {exc}\n"
            "  Is the game running with WINEDLLOVERRIDES=\"anw_hook=n,b\"?",
            file=sys.stderr,
        )
        return 1
    except DllClientError as exc:
        print(f"[cli/input] DLL error: {exc}", file=sys.stderr)
        return 1

    return 0


def cmd_dll(args: argparse.Namespace) -> int:
    """Inspect anw_hook.dll files on disk (static, no game launch).

    dll verify  — run ``file`` on each DLL and print results
    dll status  — check which DLL files exist in system32 + game data dir

    Args:
        args: Parsed namespace with ``dll_cmd`` attribute.

    Returns:
        0 on success, 1 if any expected files are missing (status only).
    """
    import subprocess

    from tools.aoe3_harness.dll_client import DLL_GAME_DATA_PATH, DLL_NAMES, DLL_SYSTEM32_PATH

    dll_src = REPO_ROOT / "tools" / "aoe3_harness" / "dll"

    if args.dll_cmd == "verify":
        print("\n[dll verify] Source DLL artifacts:")
        all_ok = True
        for name in DLL_NAMES:
            path = dll_src / name
            if path.exists():
                result = subprocess.run(
                    ["file", str(path)], capture_output=True, text=True
                )
                print(f"  {result.stdout.strip()}")
                if "PE32+" not in result.stdout:
                    print(f"  WARNING: {name} does not appear to be PE32+")
                    all_ok = False
            else:
                print(f"  {path}: NOT FOUND")
                all_ok = False

        print("\n[dll verify] Wine paths:")
        for drop_dir in (DLL_SYSTEM32_PATH, DLL_GAME_DATA_PATH):
            for name in DLL_NAMES:
                path = drop_dir / name
                status = "OK" if path.exists() else "MISSING"
                print(f"  [{status}] {path}")

        return 0 if all_ok else 1

    elif args.dll_cmd == "status":
        print("\n[dll status] Wine prefix DLL locations:")
        missing: list[Path] = []
        for drop_dir in (DLL_SYSTEM32_PATH, DLL_GAME_DATA_PATH):
            for name in DLL_NAMES:
                path = drop_dir / name
                if path.exists():
                    size = path.stat().st_size
                    print(f"  [OK     ] {path} ({size} bytes)")
                else:
                    print(f"  [MISSING] {path}")
                    missing.append(path)

        if missing:
            print(
                f"\n  {len(missing)} file(s) missing. "
                "Run: cd tools/aoe3_harness/dll && ./build.sh all",
            )
            return 1
        else:
            print("\n  All DLL files present.")
            return 0

    else:
        print(f"[cli/dll] Unknown dll subcommand: {args.dll_cmd}", file=sys.stderr)
        return 1


def cmd_hotreload(args: argparse.Namespace) -> int:
    """Start the XS hot-reload watcher (foreground; Ctrl-C to stop).

    Watches ``game/ai/**/*.xs``, ``data/*.xml``, ``RandMaps/*.xs`` and
    re-deploys via ``deploy_to_mod.py`` whenever a file changes.  The game
    does not need to be running — when the user next launches AoE3 it picks
    up the updated mod files automatically.

    Args:
        args: Parsed namespace with ``hotreload_cmd`` attribute.

    Returns:
        0 on success / clean exit (Ctrl-C).
    """
    if args.hotreload_cmd == "start":
        from tools.aoe3_harness.hotreload import run as hotreload_run
        hotreload_run()
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare two screenshots pixel-by-pixel and report the difference.

    Loads both PNGs, computes per-pixel RGB deltas, and reports the fraction
    of changed pixels, the maximum colour delta, and the bounding box of the
    changed region.  If ``--output`` is supplied, also writes a heatmap PNG
    (red = changed, black = unchanged).

    Args:
        args: Parsed namespace with ``before``, ``after``, and optional
              ``output`` attributes.

    Returns:
        0 on success, 1 on error (missing file, import failure, etc.).
    """
    from tools.aoe3_harness.diff import compare_screenshots

    before = Path(args.before)
    after  = Path(args.after)
    out    = Path(args.output) if args.output else None

    try:
        result = compare_screenshots(before, after, output_path=out)
    except FileNotFoundError as exc:
        print(f"[cli/diff] ERROR: {exc}", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"[cli/diff] ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"[cli/diff] Changed pixels: {result.pct_pixels_changed:.2%}")
    print(f"[cli/diff] Max colour delta: {result.max_color_delta}")
    if result.bbox:
        print(f"[cli/diff] Changed region (l,t,r,b): {result.bbox}")
    else:
        print("[cli/diff] No changed pixels detected.")
    if result.output_path:
        print(f"[cli/diff] Heatmap written: {result.output_path}")
    return 0


def cmd_bisect(args: argparse.Namespace) -> int:
    """Start a git-bisect session to find which XS commit broke a probe.

    Runs ``git bisect start <bad> <good>``, writes a test script that
    deploys and prompts for manual game testing, and prints the operator
    workflow.  Live game testing is required at each bisect step until
    ``exhibition_runner`` supports autonomous mode.

    Args:
        args: Parsed namespace with ``probe``, ``civ``, ``target``, ``good``,
              and ``bad`` attributes.

    Returns:
        0 on success, 1 on git error.
    """
    from tools.aoe3_harness.bisect import run_bisect

    return run_bisect(
        repo_root=REPO_ROOT,
        probe=args.probe,
        civ=args.civ,
        target=args.target,
        good_sha=args.good,
        bad_sha=args.bad,
    )


def main() -> int:
    """Entry point for the ANW test harness CLI.

    Returns:
        Exit code (0=success, non-zero=failure).
    """
    ap = argparse.ArgumentParser(
        prog="python3 -m tools.aoe3_harness.cli",
        description="ANW Test Harness — gamescope-free probe capture pipeline",
    )
    ap.add_argument("--dry-run", action="store_true", help="print actions without executing")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_deploy = sub.add_parser("deploy", help="deploy mod + optional XS check")
    p_deploy.add_argument("--check", action="store_true", help="run validate_xs_scripts.py first")

    p_run = sub.add_parser("run", help="run one or all passes")
    run_grp = p_run.add_mutually_exclusive_group(required=True)
    run_grp.add_argument("--pass", dest="pass_number", type=int, choices=range(1, 7))
    run_grp.add_argument("--all-passes", action="store_true")

    p_val = sub.add_parser("validate", help="re-validate archived logs")
    p_val.add_argument("--civ", action="append", default=[], help="filter to civ token")
    p_val.add_argument("--allow-fail", action="store_true")

    sub.add_parser("report", help="rebuild release readiness site")
    sub.add_parser("gate", help="run full static validator gate")
    sub.add_parser("status", help="show pass completion status")

    p_capture = sub.add_parser("capture", help="screenshot a civ UI surface (no cursor grab)")
    p_capture.add_argument("--civ", required=True, help="civ token (e.g. ANWBritish)")
    p_capture.add_argument(
        "--surface",
        required=True,
        help="UI surface name (e.g. homecity_picker, ai_picker, diplomacy)",
    )
    p_capture.add_argument(
        "--out",
        default=None,
        help="output PNG path (default: artifacts/validation/visual_art/<civ>/<surface>.png)",
    )

    # Phase 2: input injection via anw_hook.dll named pipe
    p_input = sub.add_parser(
        "input",
        help="inject keyboard/mouse input via anw_hook.dll pipe (game must be running)",
    )
    input_sub = p_input.add_subparsers(dest="input_cmd", required=True)

    p_key = input_sub.add_parser("key", help="inject key press (down+up) for vk_hex")
    p_key.add_argument("vk", help="virtual key code in hex, e.g. 0x57")

    p_kd = input_sub.add_parser("keydown", help="inject WM_KEYDOWN for vk_hex")
    p_kd.add_argument("vk", help="virtual key code in hex, e.g. 0x57")

    p_ku = input_sub.add_parser("keyup", help="inject WM_KEYUP for vk_hex")
    p_ku.add_argument("vk", help="virtual key code in hex, e.g. 0x57")

    p_click = input_sub.add_parser("click", help="inject left-click at (x, y)")
    p_click.add_argument("x", type=int, help="client-area x coordinate")
    p_click.add_argument("y", type=int, help="client-area y coordinate")

    p_move = input_sub.add_parser("move", help="inject mouse-move to (x, y)")
    p_move.add_argument("x", type=int, help="client-area x coordinate")
    p_move.add_argument("y", type=int, help="client-area y coordinate")

    input_sub.add_parser("state", help="print DLL STATE response (heartbeat)")

    # Phase 2: DLL file inspection (static, no game launch)
    p_dll = sub.add_parser(
        "dll",
        help="inspect anw_hook.dll files (static, no game launch)",
    )
    dll_sub = p_dll.add_subparsers(dest="dll_cmd", required=True)
    dll_sub.add_parser(
        "verify",
        help="run 'file' on each DLL and show PE32+ confirmation",
    )
    dll_sub.add_parser(
        "status",
        help="check which DLL files exist in system32 + game data dir",
    )

    # Phase 3: Hot-reload watcher
    p_hotreload = sub.add_parser(
        "hotreload",
        help="watch XS/XML source files and auto-deploy on save (game need not be running)",
    )
    hotreload_sub = p_hotreload.add_subparsers(dest="hotreload_cmd", required=True)
    hotreload_sub.add_parser(
        "start",
        help="start the watcher in the foreground (Ctrl-C to stop)",
    )

    # Phase 3: Screenshot diff
    p_diff = sub.add_parser(
        "diff",
        help="compare two screenshots pixel-by-pixel and report the difference",
    )
    p_diff.add_argument("before", help="baseline screenshot PNG path")
    p_diff.add_argument("after",  help="new screenshot PNG path to compare")
    p_diff.add_argument(
        "--output",
        default=None,
        help="write heatmap PNG to this path (red=changed, black=unchanged)",
    )

    # Phase 3: Git bisect wrapper
    p_bisect = sub.add_parser(
        "bisect",
        help="set up git-bisect to find the commit that broke a doctrine probe",
    )
    p_bisect.add_argument("--probe",  required=True, help="probe name, e.g. wall.closure")
    p_bisect.add_argument("--civ",    required=True, help="civ token, e.g. ANWFrench")
    p_bisect.add_argument(
        "--target", required=True, type=float,
        help="minimum acceptable probe value, e.g. 0.6",
    )
    p_bisect.add_argument("--good", required=True, help="known-good commit SHA")
    p_bisect.add_argument("--bad",  required=True, help="known-bad commit SHA")

    args = ap.parse_args()

    # Propagate --dry-run to subcommands that don't define it themselves
    if not hasattr(args, "dry_run"):
        args.dry_run = False

    dispatch = {
        "deploy":     cmd_deploy,
        "run":        cmd_run,
        "validate":   cmd_validate,
        "report":     cmd_report,
        "gate":       cmd_gate,
        "status":     cmd_status,
        "capture":    cmd_capture,
        "input":      cmd_input,
        "dll":        cmd_dll,
        "hotreload":  cmd_hotreload,
        "diff":       cmd_diff,
        "bisect":     cmd_bisect,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
