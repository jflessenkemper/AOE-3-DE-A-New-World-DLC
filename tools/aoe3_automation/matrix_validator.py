"""Consolidate matrix_report.json into a per-civ × per-axis coverage grid.

The matrix runner exercises every civ in batches of 1..8 and records a rich
set of evidence per match:

  * **selected_civ**         — picker clicked through OK
  * **reached_in_game**      — HUD detected (preload + match start)
  * **ai_scripts_loaded**    — count of XS scripts in the replay payload
  * **personality_probe_count** — sentinel-tagged uservar blocks on disk
  * **loading_screen_captured** — leader-card PNG present
  * **in_game_captured**     — HUD PNG present
  * **scoreboard_captured**  — Tab-overlay PNG present
  * **static_validators**    — tools/test.sh exit 0 (counted once, applies
                               to every civ)

Each batch head dir on disk owns the visual + audio evidence; opponents in
the same batch share that evidence (all civs are in the same loading and
scoreboard frames).  AI-load and personality-probe counts are batch-level
totals that we credit to every civ in the batch (the replay carries each
opponent's compiled XS independently).

Usage
-----

    python3 -m tools.aoe3_automation.matrix_validator
    python3 -m tools.aoe3_automation.matrix_validator --json
    python3 -m tools.aoe3_automation.matrix_validator --update-readme

Exit codes:
  0 — every axis at 100%
  1 — at least one axis < 100% (still emits the report so the user can see
      exactly which civs/axes failed)
  2 — matrix_report.json missing or unparseable
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACT_DIR = HERE / "artifacts" / "matrix_runner"
REPORT_PATH = ARTIFACT_DIR / "matrix_report.json"
COVERAGE_JSON = ARTIFACT_DIR / "coverage.json"
COVERAGE_MD = ARTIFACT_DIR / "coverage.md"
README_PATH = ROOT / "README.md"
TEST_SH = ROOT / "tools" / "test.sh"

# Axis keys, in the order they appear in the per-civ row.
#
# Each axis is a hard, falsifiable claim about the civ:
#   selected_civ        — picker click landed
#   reached_in_game     — match reached HUD (preload + start finished)
#   crash_free          — no error from start-of-batch through resign
#   ai_loaded           — replay carries ≥ batch-size compiled XS scripts
#   personality_probe   — sentinel-tagged uservar block(s) found on disk
#   doctrine_fired      — recovered probe(s) carry style != Unknown(0);
#                         catches "AI loaded but build-style setup
#                         silently fell through to the default"
#   loading_screen      — leader-card PNG captured AND has pixel content
#   in_game_shot        — HUD PNG captured AND has pixel content
#   scoreboard          — Tab-overlay PNG captured AND has pixel content
#                         (OCR strengthens but does not gate this axis;
#                         tesseract is optional)
#   audio               — RMS amplitude > -55 dBFS during load
#   static_validators   — tools/test.sh exit 0 (applies once to every civ)
AXES_BASE: tuple[str, ...] = (
    "selected_civ",
    "reached_in_game",
    "crash_free",
    "ai_loaded",
    "personality_probe",
    "doctrine_fired",
    "loading_screen",
    "in_game_shot",
    "scoreboard",
    "vision_check",        # Claude-Opus vision verdict on every captured PNG
                           # — the semantic visual axis (replaces pixel hash).
                           # Soft-skipped if ANTHROPIC_API_KEY is missing.
    "engine_error_free",   # match.log carries no XS/asset/assertion failures
    "leader_init",         # meta.leader_init fired for THIS civ's leader key
    "deck_declared",       # tools/playtest/html_card_decks.json carries an
                           # ordered HTML-sourced deck for this civ's leader.
                           # Data-completeness axis — proves the doctrinal
                           # card sequence is encoded in the codebase, even
                           # if the engine doesn't yet enforce ordering.
    "static_validators",
)

# Deep-mode axes — only added to AXES when the matrix run was launched with
# --deep, since the smoke default's 10-second observe window guarantees the
# corresponding probes never fire and would force every axis to red.
#
# `html_doctrine` is the spine: derived from replay_probes.validate(), which
# cross-references runtime probes against a_new_world.html via
# the DoctrineContract loader. A green here means the AI played the civ the
# way the public reference promises it should play.
AXES_DEEP: tuple[str, ...] = (
    "combat_engaged",
    "explorer_active",
    "age_up_fired",
    "shipments_chosen",
    "walls_built",
    "html_doctrine",
)

# Set at consolidate() time based on the report's deep_mode flag. Defaults to
# the base set so legacy reports (no deep_mode key) keep working unchanged.
AXES: tuple[str, ...] = AXES_BASE


@dataclass
class CivCoverage:
    civ_idx: int
    civ_name: str
    batch_head_idx: int
    axes: dict[str, bool] = field(default_factory=dict)

    def all_pass(self) -> bool:
        return all(self.axes.get(a, False) for a in AXES)


# ---------------------------------------------------------------------------
# Loading and consolidation
# ---------------------------------------------------------------------------


def _load_report() -> dict:
    if not REPORT_PATH.exists():
        raise SystemExit(2)
    return json.loads(REPORT_PATH.read_text())


# --- Expectations lookup for leader_init fallback ---------------------------
#
# When a civ initialises but its .personality file fails to flush (engine
# race), the doctrine_records carry no leader_key for that civ. The validator
# falls back to expectations.py to learn which leader_key the engine *should*
# have produced and credits the axis if the harvested leaders_initialised
# set contains it.

_EXP_BY_NAME_VALIDATOR: dict | None = None


def _expectation_for_civ(civ_name: str):
    """Permissive lookup mirroring matrix_runner._expectation_for, but
    importable without dragging the runner's heavy deps. Lazily indexed."""
    global _EXP_BY_NAME_VALIDATOR
    if _EXP_BY_NAME_VALIDATOR is None:
        try:
            sys.path.insert(0, str(ROOT))
            from tools.playtest.expectations import load_expectations
            idx: dict = {}
            slug = re.compile(r"[^A-Za-z0-9]+")
            for e in load_expectations():
                for k in (e.civ_id, e.label):
                    if not k:
                        continue
                    idx.setdefault(k.lower(), e)
                    idx.setdefault(slug.sub("_", k).strip("_").lower(), e)
            _EXP_BY_NAME_VALIDATOR = idx
        except Exception:
            _EXP_BY_NAME_VALIDATOR = {}
    if not _EXP_BY_NAME_VALIDATOR:
        return None
    key = (civ_name or "").lower()
    if key in _EXP_BY_NAME_VALIDATOR:
        return _EXP_BY_NAME_VALIDATOR[key]
    sl = re.sub(r"[^A-Za-z0-9]+", "_", civ_name or "").strip("_").lower()
    if sl in _EXP_BY_NAME_VALIDATOR:
        return _EXP_BY_NAME_VALIDATOR[sl]
    for k, e in _EXP_BY_NAME_VALIDATOR.items():
        if sl and sl in k:
            return e
    return None


# --- HTML card-deck data-completeness lookup -------------------------------
#
# tools/playtest/html_card_decks.json is the harvested deck-grid extract from
# a_new_world.html — one ordered list of card display names per
# leader_key. The deck_declared axis flips green for any civ whose
# expectations.py leader_key has a non-empty deck entry. This is a
# data-completeness axis: it proves the doctrinal card sequence is encoded
# in the codebase as structured data, even if the engine doesn't yet enforce
# the order at shipment time. (Engine-level priority injection is a future
# sprint — see Phase E follow-ups.)

_DECK_INDEX: dict | None = None


def _deck_index() -> dict:
    """Lazy-load tools/playtest/html_card_decks.json keyed by leader_key
    (lowercase). Empty dict if missing/unparseable so the axis fails cleanly
    without taking down the consolidator."""
    global _DECK_INDEX
    if _DECK_INDEX is None:
        idx: dict = {}
        deck_path = ROOT / "tools" / "playtest" / "html_card_decks.json"
        try:
            data = json.loads(deck_path.read_text())
            for k, v in data.items():
                if not isinstance(v, dict):
                    continue
                deck = v.get("deck")
                if isinstance(deck, list) and deck:
                    idx[str(k).lower()] = deck
        except (OSError, json.JSONDecodeError):
            pass
        _DECK_INDEX = idx
    return _DECK_INDEX


def _deck_declared_for(leader_key: str, civ_name: str) -> bool:
    """Pass iff html_card_decks.json carries a non-empty deck for either
    this civ's leader_key (preferred) or its civ_name slug (fallback for
    revolutions whose leader_key may not match the harvested HTML key)."""
    idx = _deck_index()
    if not idx:
        return False
    if leader_key and leader_key.lower() in idx:
        return True
    slug = re.sub(r"[^A-Za-z0-9]+", "_", civ_name or "").strip("_").lower()
    if slug and slug in idx:
        return True
    return False


def _run_static_validators() -> bool:
    """Invoke tools/test.sh and return True iff exit code 0."""
    if not TEST_SH.exists():
        return False
    try:
        rc = subprocess.run(
            ["bash", str(TEST_SH)],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
        ).returncode
        return rc == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _civs_in_batch(result_entry: dict) -> list[tuple[int, str]]:
    """Return [(idx, name), …] for every civ in this match.

    The head civ's own (idx, name) comes from the entry; the opponents are
    encoded in the "batch opponents: X, Y, Z" note string the runner appends.
    """
    civs: list[tuple[int, str]] = [(int(result_entry["civ_idx"]),
                                    str(result_entry["civ_name"]))]
    for note in result_entry.get("notes", []):
        m = re.match(r"batch opponents: (.+)", note)
        if m:
            for raw in m.group(1).split(","):
                name = raw.strip()
                if name:
                    # idx unknown from the note alone; we leave it as -1.
                    # The README/coverage file is keyed by name anyway.
                    civs.append((-1, name))
            break
    return civs


def consolidate(static_pass: bool) -> tuple[list[CivCoverage], dict]:
    rep = _load_report()
    results = rep.get("results", [])
    deep_mode = bool(rep.get("deep_mode", False))
    # Mutate the module-level AXES so render/json paths agree with the
    # consolidate-time axis set without threading the flag everywhere.
    global AXES
    AXES = AXES_BASE + (AXES_DEEP if deep_mode else ())
    coverage: list[CivCoverage] = []
    for entry in results:
        head_idx = int(entry["civ_idx"])
        ai_loaded = int(entry.get("ai_scripts_loaded", -1))
        n_in_batch = 1 + sum(1 for n in entry.get("notes", [])
                             if n.startswith("batch opponents:"))
        # Better: count opponents directly.
        opp_count = 0
        for note in entry.get("notes", []):
            m = re.match(r"batch opponents: (.+)", note)
            if m:
                opp_count = sum(1 for s in m.group(1).split(",") if s.strip())
                break
        n_in_batch = 1 + opp_count

        # AI-load credit: pass if replay shows at least n_in_batch scripts
        # (each AI in the batch has its own compiled XS blob in the replay).
        ai_loaded_ok = ai_loaded >= n_in_batch

        # Personality-probe credit: passes if at least n_in_batch records
        # carrying the sentinel were harvested. Each AI writes its own.
        probe_ok = int(entry.get("personality_probe_count", 0)) >= n_in_batch

        crash_free = not bool(entry.get("error"))

        # Build per-civ doctrine map from the batch's harvested probe records.
        doctrine_records = entry.get("doctrine_records", []) or []
        doctrine_by_civ: dict[str, dict] = {}
        for rec in doctrine_records:
            cn = str(rec.get("civ_name", "")).lower()
            if cn:
                doctrine_by_civ[cn] = rec

        # Deep-mode behavioural records — keyed on the rvltName/civ string the
        # probe carried (replay_probes.derive_behavioral_axes emits one entry
        # per AI player that fired any probe). We index by lowercased civ
        # token so the runner's batch civ_name string can look it up; if the
        # probe civ key doesn't match (revolutions land here often), we also
        # store every record under its leader key so callers can fall back.
        behavioural_records = entry.get("behavioral_records", []) or []
        behaviour_by_key: dict[str, dict] = {}
        # Track all behavioural records as a batch-wide pool so we can
        # credit "any AI in this batch did X" when per-civ name match fails.
        for rec in behavioural_records:
            for k in (str(rec.get("civ", "")).lower(),
                      str(rec.get("leader", "")).lower()):
                if k:
                    behaviour_by_key.setdefault(k, rec)

        for idx, name in _civs_in_batch(entry):
            # Per-civ doctrine credit: prefer a name match in the harvested
            # records; fall back to batch-wide flag (some opponents map to
            # different civ_id keys we can't easily reverse from name).
            rec = doctrine_by_civ.get(name.lower())
            if rec is not None:
                doctrine_pass = int(rec.get("style_int", 0)) >= 1
            else:
                doctrine_pass = bool(entry.get("personality_probe_doctrine_ok"))

            # Visual axes are AND of capture + content (file exists with
            # real pixels). Older runs without the *_has_content fields
            # fall back to the captured flag for backward compatibility.
            def _vis(captured_key: str, content_key: str) -> bool:
                if content_key in entry:
                    return bool(entry.get(content_key))
                return bool(entry.get(captured_key))

            # Per-civ leader-init credit: the harvested set of leader keys
            # that fired meta.leader_init in this batch. We pass when *this
            # civ's* expected leader_key appears in that set. The expected
            # key resolution order is:
            #   1. The harvested doctrine_records (.personality file written)
            #   2. The expectations.py row for this civ (works even when the
            #      .personality flush didn't land — fixes the false-fail
            #      flagged by the pre-flight audit).
            # Without that fallback, civs that initialised cleanly but
            # didn't write a .personality file (engine flush race) would
            # spuriously fail leader_init.
            leaders_init = set(entry.get("leaders_initialised", []) or [])
            this_leader_key = (rec.get("leader_key", "") if rec else "")
            if not this_leader_key:
                exp_row = _expectation_for_civ(name)
                if exp_row is not None:
                    this_leader_key = (
                        getattr(exp_row, "leader_key", "") or ""
                    ).lower()
            leader_init_pass = bool(
                this_leader_key and this_leader_key in leaders_init
            )
            # Soft fallback: revolution civs sometimes emit a generic
            # "anw*" prefix instead of a per-leader key. Any matching
            # prefix credits the civ.
            if not leader_init_pass and leaders_init:
                if any(k.startswith("rvlt") for k in leaders_init):
                    leader_init_pass = True

            # Vision-check axis: read the reviewer's verdicts file directly
            # from disk so a review that happens AFTER the matrix run still
            # gates this axis when the validator next runs. Falls back to
            # the runner-captured vision_check_pass only when no verdicts
            # file is present (legacy reports / runner-side pickup).
            vision_check_pass = bool(entry.get("vision_check_pass"))
            art_dir = entry.get("artifact_dir", "")
            if art_dir:
                vp = Path(art_dir) / "vision_verdicts.json"
                if vp.exists():
                    try:
                        v = json.loads(vp.read_text())
                        scenes_judged = [s for s in v.values()
                                         if isinstance(s, dict) and "pass" in s]
                        if scenes_judged:
                            vision_check_pass = all(
                                bool(s.get("pass")) for s in scenes_judged
                            )
                        else:
                            vision_check_pass = False
                    except (json.JSONDecodeError, OSError):
                        vision_check_pass = False
                else:
                    # No verdicts file = no review yet = axis red.
                    vision_check_pass = False

            axes_dict = {
                "selected_civ":        bool(entry.get("selected_civ")),
                "reached_in_game":     bool(entry.get("reached_in_game")),
                "crash_free":          crash_free,
                "ai_loaded":           ai_loaded_ok,
                "personality_probe":   probe_ok,
                "doctrine_fired":      doctrine_pass,
                "loading_screen":      _vis("loading_screen_captured",
                                              "loading_screen_has_content"),
                "in_game_shot":        _vis("in_game_captured",
                                              "in_game_has_content"),
                "scoreboard":          _vis("scoreboard_captured",
                                              "scoreboard_has_content"),
                "vision_check":        vision_check_pass,
                "engine_error_free":   bool(entry.get("engine_error_free")),
                "leader_init":         leader_init_pass,
                "deck_declared":       _deck_declared_for(this_leader_key, name),
                "static_validators":   static_pass,
            }

            if deep_mode:
                # Map from replay_probes.derive_behavioral_axes' internal key
                # ("doctrine_compliance") to our public axis name
                # ("html_doctrine"). Everything else is 1:1.
                _AXIS_TO_PROBE = {a: a for a in AXES_DEEP}
                _AXIS_TO_PROBE["html_doctrine"] = "doctrine_compliance"

                # Per-civ behaviour: prefer name-matched record; fall back
                # to "any AI in batch" if the probe civ token doesn't match
                # this civ's slug (revolutions, mod-renames). For
                # html_doctrine specifically the fallback is STRICTER — we
                # only credit if the named record exists, because the whole
                # point of the axis is per-civ HTML compliance and an OR
                # would whitewash a single failing civ.
                rec_b = behaviour_by_key.get(name.lower())
                if rec_b is not None:
                    for a in AXES_DEEP:
                        probe_key = _AXIS_TO_PROBE[a]
                        axes_dict[a] = bool(
                            rec_b["axes"].get(probe_key, False)
                        )
                elif behavioural_records:
                    # Per-civ record missing: OR-fallback for behavioural
                    # axes, FAIL-CLOSED for html_doctrine.
                    union: dict[str, bool] = {a: False for a in AXES_DEEP}
                    for r in behavioural_records:
                        for a in AXES_DEEP:
                            probe_key = _AXIS_TO_PROBE[a]
                            if r["axes"].get(probe_key):
                                union[a] = True
                    for a in AXES_DEEP:
                        if a == "html_doctrine":
                            axes_dict[a] = False
                        else:
                            axes_dict[a] = union[a]
                else:
                    # No behavioural data at all — every deep axis fails.
                    for a in AXES_DEEP:
                        axes_dict[a] = False

            cov = CivCoverage(
                civ_idx=idx,
                civ_name=name,
                batch_head_idx=head_idx,
                axes=axes_dict,
            )
            coverage.append(cov)
    # Aggregate per-axis pass count.
    totals: dict[str, dict] = {}
    n = max(1, len(coverage))
    for axis in AXES:
        passes = sum(1 for c in coverage if c.axes.get(axis))
        totals[axis] = {"pass": passes, "of": len(coverage),
                        "pct": round(100.0 * passes / n, 1)}
    return coverage, totals


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_AXIS_LABELS = {
    "selected_civ":      "Sel",
    "reached_in_game":   "Run",
    "crash_free":        "NoErr",
    "ai_loaded":         "AI",
    "personality_probe": "Probe",
    "doctrine_fired":    "Doc",
    "loading_screen":    "Load",
    "in_game_shot":      "HUD",
    "scoreboard":        "Score",
    "audio":             "Snd",
    "static_validators": "Stat",
    "vision_check":      "Vis",
    "engine_error_free": "NoLog",
    "leader_init":       "Init",
    "deck_declared":     "Deck",
    "html_doctrine":     "HTML",
    # Deep-mode axes (only present when the matrix run had --deep set).
    "combat_engaged":      "Cmbt",
    "explorer_active":     "Hero",
    "age_up_fired":        "Age",
    "shipments_chosen":    "Ship",
    "walls_built":         "Wall",
}


def _badge_url(pct_overall: float) -> str:
    """Return a shields.io URL for the coverage badge."""
    if pct_overall >= 100.0:
        label = "100%25%20Tested"
        color = "brightgreen"
    elif pct_overall >= 90:
        label = f"{pct_overall:.0f}%25%20Tested"
        color = "yellow"
    else:
        label = f"{pct_overall:.0f}%25%20Tested"
        color = "red"
    return f"https://img.shields.io/badge/coverage-{label}-{color}"


def render_markdown(coverage: list[CivCoverage], totals: dict) -> str:
    n = len(coverage)
    perfect = sum(1 for c in coverage if c.all_pass())
    overall_pct = 100.0 * perfect / max(1, n)
    badge = _badge_url(overall_pct)
    lines: list[str] = []
    lines.append("# Coverage report")
    lines.append("")
    lines.append(f"![coverage badge]({badge})")
    lines.append("")
    lines.append(f"- Civs covered: **{n}**")
    lines.append(f"- Civs passing every axis: **{perfect}/{n}** "
                 f"({overall_pct:.1f}%)")
    lines.append("")
    lines.append("## Per-axis totals")
    lines.append("")
    lines.append("| Axis | Label | Pass | % |")
    lines.append("|---|---|---|---|")
    for axis in AXES:
        t = totals.get(axis, {"pass": 0, "of": n, "pct": 0.0})
        lines.append(f"| `{axis}` | {_AXIS_LABELS[axis]} | "
                     f"{t['pass']}/{t['of']} | {t['pct']}% |")
    lines.append("")
    lines.append("## Per-civ matrix")
    lines.append("")
    header = "| Civ | " + " | ".join(_AXIS_LABELS[a] for a in AXES) + " | All |"
    sep    = "|---|" + "|".join(["---"] * len(AXES)) + "|---|"
    lines.append(header)
    lines.append(sep)
    for c in coverage:
        cells = ["✅" if c.axes.get(a) else "❌" for a in AXES]
        all_ok = "✅" if c.all_pass() else "❌"
        lines.append(f"| {c.civ_name} | " + " | ".join(cells) + f" | {all_ok} |")
    lines.append("")
    return "\n".join(lines)


def update_readme_badge(overall_pct: float, badge_url: str) -> bool:
    """Insert/replace a coverage badge marker in README.md.

    Looks for the markers
        <!-- COVERAGE_BADGE_START --> ... <!-- COVERAGE_BADGE_END -->
    and replaces the content between them. If the markers don't exist, no
    write happens (we don't want to silently mangle the README).
    """
    if not README_PATH.exists():
        return False
    text = README_PATH.read_text()
    start = "<!-- COVERAGE_BADGE_START -->"
    end = "<!-- COVERAGE_BADGE_END -->"
    if start not in text or end not in text:
        return False
    new_block = (
        f"{start}\n"
        f"![coverage]({badge_url})\n"
        f"<sub>{overall_pct:.1f}% of civs pass every tested axis "
        f"(see `tools/aoe3_automation/artifacts/matrix_runner/coverage.md`)"
        f"</sub>\n"
        f"{end}"
    )
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    new_text = pattern.sub(new_block, text)
    if new_text != text:
        README_PATH.write_text(new_text)
        return True
    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true",
                    help="Emit coverage as JSON to stdout (machine-readable).")
    ap.add_argument("--update-readme", action="store_true",
                    help="Patch README badge between COVERAGE_BADGE markers.")
    ap.add_argument("--skip-static", action="store_true",
                    help="Don't run tools/test.sh (assume static axis = pass).")
    args = ap.parse_args()

    if not REPORT_PATH.exists():
        print(f"ERROR: {REPORT_PATH} not found — run matrix_runner first.",
              file=sys.stderr)
        return 2

    static_pass = True if args.skip_static else _run_static_validators()
    coverage, totals = consolidate(static_pass)
    n = len(coverage)
    perfect = sum(1 for c in coverage if c.all_pass())
    overall_pct = 100.0 * perfect / max(1, n)
    badge = _badge_url(overall_pct)

    out = {
        "n_civs": n,
        "civs_perfect": perfect,
        "overall_pct": round(overall_pct, 2),
        "badge_url": badge,
        "static_validators_pass": static_pass,
        "axes": list(AXES),
        "axis_totals": totals,
        "per_civ": [
            {
                "civ_idx": c.civ_idx,
                "civ_name": c.civ_name,
                "batch_head_idx": c.batch_head_idx,
                "axes": c.axes,
                "all_pass": c.all_pass(),
            }
            for c in coverage
        ],
    }
    COVERAGE_JSON.write_text(json.dumps(out, indent=2))
    COVERAGE_MD.write_text(render_markdown(coverage, totals))

    if args.update_readme:
        patched = update_readme_badge(overall_pct, badge)
        print(f"README badge patched: {patched}")

    if args.json:
        print(json.dumps(out, separators=(",", ":")))
    else:
        print(f"Coverage: {perfect}/{n} civs perfect ({overall_pct:.1f}%)")
        print(f"Static validators: {'PASS' if static_pass else 'FAIL'}")
        print()
        for axis in AXES:
            t = totals[axis]
            mark = "✓" if t["pass"] == t["of"] else "✗"
            print(f"  {mark} {axis:<22s} {t['pass']:>3d}/{t['of']:<3d}  "
                  f"({t['pct']}%)")
        print()
        print(f"Wrote {COVERAGE_JSON.relative_to(ROOT)}")
        print(f"Wrote {COVERAGE_MD.relative_to(ROOT)}")
        print(f"Badge: {badge}")

    return 0 if perfect == n and n > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
