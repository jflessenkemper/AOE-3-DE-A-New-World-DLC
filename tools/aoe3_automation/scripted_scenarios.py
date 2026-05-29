#!/usr/bin/env python3
"""Pre-baked scripted scenarios — one CLI invocation, region-cropped output.

Why this exists
---------------
When Claude (or any caller) drives the harness step-by-step, every click /
scroll / screenshot is a separate tool call that burns context. The full
sequences are already calibrated in ``lobby_driver.py`` and ``in_game_driver.py``;
this module exposes them as named scenarios that run end-to-end in one bash
invocation and write ONLY the region crops listed in ``canonical_regions.json``.
The caller never sees the per-step screenshots — only the final small PNGs
that need pixel-perfect verification.

Available scenarios::

    scripted_scenarios.py picker_pixel  --civ ANWBritish [--out artifacts/pixel/]
    scripted_scenarios.py homecity_pixel --civ ANWBritish [--out artifacts/pixel/]
    scripted_scenarios.py lobby_state                     [--out artifacts/pixel/]
    scripted_scenarios.py match_observe --civ ANWBritish --observe-seconds 30

Each scenario:
  1. Drives the calibrated click/scroll sequence via the existing drivers.
  2. Captures a single full-screen ``_state.png`` at each verification point.
  3. Crops to the canonical regions and writes them to ``--out``.
  4. Prints a one-line JSON manifest of what was written, so a caller can
     parse the result without reading every PNG.

The full-screen capture is also retained in ``--out/_state.png`` so a caller
that wants to perceptual-hash the whole frame still can; the canonical crops
are sized for fast targeted verification (portrait, leader name, HUD).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))

REGIONS_PATH = HERE / "canonical_regions.json"


def _load_regions() -> dict:
    return json.loads(REGIONS_PATH.read_text(encoding="utf-8"))


def _import_pil():
    try:
        from PIL import Image  # noqa: F401
        return __import__("PIL.Image", fromlist=["Image"])
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit(
            "Pillow is required for region cropping. "
            "pip install pillow OR use the project's .venv."
        ) from exc


def _crop_named(image_path: Path, regions: dict, out_dir: Path,
                prefix: str) -> dict:
    """Crop ``image_path`` to every region in ``regions`` and write PNGs.

    ``regions`` is a mapping ``name → [l, t, r, b]``. Keys starting with ``_``
    are skipped (so the JSON can carry inline doc comments). Returns a manifest
    ``{name: {path, box}}`` describing what was written.
    """
    Image = _import_pil()
    img = Image.open(image_path).convert("RGB")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    for name, box in regions.items():
        if name.startswith("_") or not isinstance(box, list) or len(box) != 4:
            continue
        crop = img.crop(tuple(box))
        out = out_dir / f"{prefix}__{name}.png"
        crop.save(out, format="PNG")
        manifest[name] = {"path": str(out.relative_to(REPO_ROOT)), "box": box}
    return manifest


# ---- scenarios ------------------------------------------------------------


def scenario_lobby_state(out_dir: Path) -> dict:
    """Capture the current lobby screen and crop to lobby canonical regions.

    Pre-condition: AoE3 is running and you're already on the Skirmish lobby.
    No clicking is performed — this is a pure observation pass.
    """
    from tools.aoe3_automation import lobby_driver

    state = out_dir / "_state.png"
    out_dir.mkdir(parents=True, exist_ok=True)
    lobby_driver.screenshot(state)
    regions = _load_regions()["lobby"]
    return {
        "scenario": "lobby_state",
        "state_path": str(state.relative_to(REPO_ROOT)),
        "crops": _crop_named(state, regions, out_dir, "lobby"),
    }


def scenario_picker_pixel(civ_token: str, out_dir: Path) -> dict:
    """Select ``civ_token`` via the OCR-verified path, capture lobby state.

    Pre-condition: AoE3 is on the Skirmish lobby. Player 1's civ slot may be
    in any state (Random Personality, or pre-set to a previous civ — both
    are handled).

    Why ``set_civ_by_token_verified`` instead of index-based selection:
      The lobby actually opens TWO different pickers depending on P1's
      current state. SELECT CIVILIZATION (alphabetical by civ name) when
      P1 = Random Personality; SELECT HOME CITY (recently-played first,
      then alphabetical-by-home-city) when P1 = some assigned civ. The
      static ``ANW_TO_PICKER_INDEX`` table only matches the CIVILIZATION
      layout — using it directly silently selects the wrong civ when the
      lobby happens to be in HOME CITY mode (the 2026-05-10 picker_pixel
      bug: asked for British(7), got Argentine because the home-city
      picker has Argentine at row 7 and the table looked up the wrong
      list). The verified path does layout-agnostic OCR scrolling and
      maps both layouts back to civ tokens via ``HOME_CITY_TO_TOKEN``.

    Captures:
      _state.png  — full lobby AFTER the selection is committed. The
                    canonical lobby crops (player_slot_*, match_setup_header,
                    game_options_*, map_preview, play_button) provide the
                    visual evidence of which civ was selected.
    """
    from tools.aoe3_automation import lobby_driver

    out_dir.mkdir(parents=True, exist_ok=True)
    coords = lobby_driver.load_coords()
    ref_path = REPO_ROOT / "enriched_reference.json"
    if not ref_path.exists():
        raise SystemExit(
            f"enriched_reference.json missing at {ref_path}. "
            "set_civ_by_token_verified needs it for the OCR civ-name lookup."
        )
    ref = json.loads(ref_path.read_text(encoding="utf-8"))

    # prefer_ocr=True: the fast cache-driven path returns ok=True without
    # re-OCRing the highlighted row, so a stale cache silently lands on the
    # wrong civ (2026-05-10: cache calibrated for HOME CITY layout returned
    # ok=True for British but the click landed on Ottoman). Verification
    # scenarios must always confirm by OCR — speed is not the priority.
    #
    # max_attempts=2: when OCR scan-and-find fails, the failure mode is
    # "civ name not in enriched_reference's expected_names list" — retrying
    # 8 times scrolls the entire picker top-to-bottom 8 times, ~800s wasted
    # per civ (the 2026-05-11 matrix-runner observation). Cap at 2 so a
    # genuine flaky-OCR retry still works but unrecoverable name-mismatch
    # fails fast (~200s) and the matrix finishes in reasonable time.
    res = lobby_driver.set_civ_by_token_verified(
        coords, civ_token, ref, prefer_ocr=True, max_attempts=2,
    )
    if not res.get("ok"):
        raise SystemExit(
            f"set_civ_by_token_verified({civ_token}) failed after "
            f"{res.get('attempts', '?')} attempts. "
            f"matched_on={res.get('matched_on')!r}, "
            f"actual_token={res.get('actual_token')!r}. "
            f"history={res.get('history', [])!r}"
        )
    time.sleep(0.6)

    state = out_dir / "_state.png"
    lobby_driver.screenshot(state)
    lobby_regions = _load_regions()["lobby"]
    return {
        "scenario": "picker_pixel",
        "civ": civ_token,
        "selection_method": res.get("matched_on"),
        "selection_attempts": res.get("attempts"),
        "actual_token": res.get("actual_token", civ_token),
        "state_path": str(state.relative_to(REPO_ROOT)),
        "crops": _crop_named(state, lobby_regions, out_dir,
                             f"picker__{civ_token}"),
    }


def scenario_homecity_pixel(civ_token: str, out_dir: Path) -> dict:
    """Toggle picker to HOME CITY mode, scroll to civ, capture homecity panel.

    Pre-condition: AoE3 lobby is open. The picker scroll table is calibrated
    for CIVILIZATION mode; switching to HOME CITY mode resets scroll, so
    callers must re-derive the index from the homecity-mode order. This
    scenario delegates to ``lobby_driver.set_homecity_by_index`` which
    handles the layout-mode-aware lookup.
    """
    from tools.aoe3_automation import lobby_driver

    out_dir.mkdir(parents=True, exist_ok=True)
    coords = lobby_driver.load_coords()
    if not hasattr(lobby_driver, "set_homecity_by_index"):
        raise SystemExit(
            "lobby_driver.set_homecity_by_index not implemented. "
            "Calibrate the HOME CITY scroll table before running this scenario."
        )
    civ_index = lobby_driver.civ_token_to_homecity_index(civ_token)
    lobby_driver.open_homecity_picker(coords)
    lobby_driver.set_homecity_by_index(coords, civ_index)
    time.sleep(0.6)

    state = out_dir / "_state.png"
    lobby_driver.screenshot(state)
    regions = _load_regions()["picker_homecity_mode"]
    manifest = {
        "scenario": "homecity_pixel",
        "civ": civ_token,
        "homecity_index": civ_index,
        "state_path": str(state.relative_to(REPO_ROOT)),
        "crops": _crop_named(state, regions, out_dir, f"homecity__{civ_token}"),
    }
    lobby_driver.close_picker(coords)
    return manifest


def scenario_match_observe(civ_token: str, out_dir: Path,
                           observe_seconds: int = 30) -> dict:
    """Pick civ, start match, observe for N seconds, capture in-game regions, resign.

    Pre-condition: AoE3 lobby is open with default settings. Uses the
    OCR-verified civ-selection path (layout-agnostic — see
    ``scenario_picker_pixel`` for why ``ANW_TO_PICKER_INDEX`` alone isn't
    safe across both picker layouts). Captures one full ``_state.png``
    after the observation window and crops to the in-game canonical
    regions only — no per-second sampling.
    """
    from tools.aoe3_automation import in_game_driver, lobby_driver

    out_dir.mkdir(parents=True, exist_ok=True)
    coords = lobby_driver.load_coords()
    ref_path = REPO_ROOT / "enriched_reference.json"
    if not ref_path.exists():
        raise SystemExit(
            f"enriched_reference.json missing at {ref_path}. "
            "set_civ_by_token_verified needs it for the OCR civ-name lookup."
        )
    ref = json.loads(ref_path.read_text(encoding="utf-8"))

    res = lobby_driver.set_civ_by_token_verified(
        coords, civ_token, ref, prefer_ocr=True,
    )
    if not res.get("ok"):
        raise SystemExit(
            f"set_civ_by_token_verified({civ_token}) failed: "
            f"{res.get('history', [])!r}"
        )
    time.sleep(0.6)
    lobby_driver.click_play(coords)

    driver = in_game_driver.GameDriver()
    # 2026-05-11: pass diagnostic_dir so a timeout leaves a screenshot +
    # Age3Log tail in the per-civ out_dir. The 2026-05-11 ANWBritish smoke
    # run hit this path with no visible state — diagnostic dump now lets the
    # next inspection see whether the loading bar was stuck, a dialog
    # appeared, or the lobby never even transitioned.
    if not driver.wait_for_in_game(timeout=240, diagnostic_dir=out_dir):
        raise SystemExit("Timed out waiting for in-game state.")

    time.sleep(observe_seconds)

    state = out_dir / "_state.png"
    in_game_driver._screenshot_raw(state)  # type: ignore[attr-defined]
    regions = _load_regions()["ingame"]
    manifest = {
        "scenario": "match_observe",
        "civ": civ_token,
        "observe_seconds": observe_seconds,
        "state_path": str(state.relative_to(REPO_ROOT)),
        "crops": _crop_named(state, regions, out_dir, f"ingame__{civ_token}"),
    }

    driver.resign(verify_lobby=True)
    return manifest


# ---- CLI ------------------------------------------------------------------


_SCENARIOS = {
    "lobby_state": (scenario_lobby_state, False),
    "picker_pixel": (scenario_picker_pixel, True),
    "homecity_pixel": (scenario_homecity_pixel, True),
    "match_observe": (scenario_match_observe, True),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", choices=sorted(_SCENARIOS),
                    help="Which canned scenario to run.")
    ap.add_argument("--civ",
                    help="ANW civ token (required for civ-specific scenarios).")
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "artifacts" / "scripted_scenarios",
                    help="Output directory for region crops + state PNG.")
    ap.add_argument("--observe-seconds", type=int, default=30,
                    help="Observation window for match_observe (default: 30).")
    args = ap.parse_args(argv)

    fn, needs_civ = _SCENARIOS[args.scenario]
    if needs_civ and not args.civ:
        ap.error(f"--civ is required for scenario '{args.scenario}'")

    out_dir = args.out / f"{args.scenario}__{args.civ or 'none'}"

    if args.scenario == "match_observe":
        manifest = fn(args.civ, out_dir, observe_seconds=args.observe_seconds)
    elif needs_civ:
        manifest = fn(args.civ, out_dir)
    else:
        manifest = fn(out_dir)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest_path.relative_to(REPO_ROOT))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
