#!/usr/bin/env python3
"""Compare HTML playstyle prose vs structured playstyle_spec.json claims.

For each civ:

  * Extract the playstyle summary from the LAST sentence of the
    ``data-search="..."`` attribute on the per-civ
    ``<details class="nation-node">`` element in ``a_new_world.html``.
  * Look up the same civ in ``playstyle_spec.json`` (keyed by data-name) and
    pull its ``doctrine_prose`` (and any ``prose_overrides``) plus ``claims``.
  * Run a fixed keyword taxonomy over both sources and emit per-civ
    "HTML keywords" / "Spec keywords" / "Mismatches" sets.

This validator is informational - the real fix path is running games and
iterating ``.personality`` files. Always exits 0.

Inputs (auto-discovered from repo root):

  * ``a_new_world.html``
  * ``playstyle_spec.json`` (or ``data/playstyle_spec.json`` as a fallback)

Outputs (to ``artifacts/validation/ai_playstyle/``):

  * ``findings.json``
  * ``findings.md``

Usage::

    python3 tools/validation/validate_ai_playstyle.py
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover - dep is required
    raise SystemExit(
        "beautifulsoup4 is required. Install with: "
        ".venv/bin/python -m pip install beautifulsoup4"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Keyword taxonomy
# ---------------------------------------------------------------------------

TAXONOMY: dict[str, set[str]] = {
    "WALL_STRATEGY": {
        "wall", "walls", "walled", "stockade", "palisade",
        "fortress", "fortresses", "ring", "rings",
        "no walls", "without walls", "skips walls",
    },
    "MILITARY_FOCUS": {
        "infantry", "cavalry", "musketeer", "musketeers",
        "longbow", "longbows", "longbowman", "longbowmen",
        "skirmisher", "skirmishers",
        "artillery", "naval", "harbor", "harbour", "fishing",
    },
    "TEMPO": {
        "boom", "rush", "raid", "raids", "raiding",
        "turtle", "turtling",
        "fast age", "early aggression", "defensive",
    },
    "ECON": {
        "hacienda", "haciendas", "estate", "estates",
        "rice paddy", "rice paddies", "field", "fields",
        "mine", "mines", "trade post", "trading post", "trading posts",
        "mercenary", "mercenaries", "shipment", "shipments",
    },
}

# Pre-compute regex patterns for keyword detection (whole-word, lowercase).
_KEYWORD_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
for cat, words in TAXONOMY.items():
    pats: list[tuple[str, re.Pattern[str]]] = []
    # Sort longest-first so multi-word phrases match before sub-words.
    for w in sorted(words, key=len, reverse=True):
        pat = re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
        pats.append((w, pat))
    _KEYWORD_PATTERNS[cat] = pats


def detect_keywords(text: str) -> dict[str, list[str]]:
    """Return {category: sorted unique matched keywords} from ``text``."""
    if not text:
        return {cat: [] for cat in TAXONOMY}
    norm = text.lower()
    out: dict[str, list[str]] = {}
    for cat, patterns in _KEYWORD_PATTERNS.items():
        hits: set[str] = set()
        for word, pat in patterns:
            if pat.search(norm):
                hits.add(word.lower())
        out[cat] = sorted(hits)
    return out


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

@dataclass
class HtmlPlaystyle:
    data_name: str
    full_data_search: str
    playstyle_sentence: str


def _last_sentence(text: str) -> str:
    """Return the playstyle-prose tail of ``data-search``.

    The HTML reference encodes a civ's ``data-search`` attribute as:

        "<civ name> · <leader> · <units> · ... · <last card name> · <playstyle prose>"

    where every chunk is separated by ` · ` (U+00B7 with surrounding
    spaces) EXCEPT the playstyle prose at the tail, which is one or two
    full sentences ending in ``.``.

    The earlier heuristic (split on ``[.!?]\\s+`` and glue the last two
    sentences) failed for civs whose card list is ``.``-free — the
    "previous" sentence ended up being the entire bullet list.

    The robust rule: split on ` · `, take the LAST chunk. That always
    yields the playstyle paragraph cleanly (verified across all 46 civs).
    Fall back to the prior heuristic only if the data-search has no
    bullet separator at all.
    """
    if not text:
        return ""
    decoded = html_lib.unescape(text).strip().rstrip('"').strip()

    # Primary path: take the chunk after the last middle-dot bullet.
    # ` · ` is the canonical separator (space-MIDDLE_DOT-space). Some
    # entries use a stray `·` without surrounding spaces inside prose,
    # so we require the spaces to avoid false splits.
    if " · " in decoded:
        tail = decoded.rsplit(" · ", 1)[1].strip()
        if tail:
            return tail

    # Fallback: legacy sentence-splitting (rare; only data-search entries
    # without bullets).
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", decoded) if p.strip()]
    if not parts:
        return ""
    parts = [re.sub(r"^[•\-*·]\s*", "", p) for p in parts]
    last = parts[-1]
    if len(parts) >= 2:
        prev = parts[-2]
        if len(prev) >= 40 and " " in prev and "·" not in prev[-30:]:
            return (prev + " " + last).strip()
    return last


def parse_html_playstyles(html_path: Path) -> list[HtmlPlaystyle]:
    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    out: list[HtmlPlaystyle] = []
    for node in soup.find_all("details", class_="nation-node"):
        data_name = (node.get("data-name") or "").strip()
        data_search = (node.get("data-search") or "").strip()
        if not data_name:
            continue
        sentence = _last_sentence(data_search)
        out.append(HtmlPlaystyle(
            data_name=data_name,
            full_data_search=data_search,
            playstyle_sentence=sentence,
        ))
    return out


# ---------------------------------------------------------------------------
# playstyle_spec.json loader
# ---------------------------------------------------------------------------

@dataclass
class SpecEntry:
    data_name: str
    doctrine_prose: str
    prose_overrides: list[str]
    claims: dict


def load_playstyle_spec(path: Path) -> dict[str, SpecEntry]:
    out: dict[str, SpecEntry] = {}
    if not path.exists():
        return out
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return out
    civs = raw.get("civs") if isinstance(raw, dict) else None
    if not isinstance(civs, dict):
        return out
    for _key, entry in civs.items():
        if not isinstance(entry, dict):
            continue
        dn = (entry.get("data_name") or "").strip()
        if not dn:
            continue
        prose = entry.get("doctrine_prose") or ""
        overrides = entry.get("prose_overrides") or []
        if not isinstance(overrides, list):
            overrides = []
        claims = entry.get("claims") or {}
        if not isinstance(claims, dict):
            claims = {}
        out[dn] = SpecEntry(
            data_name=dn,
            doctrine_prose=html_lib.unescape(prose) if isinstance(prose, str) else "",
            prose_overrides=[html_lib.unescape(o) for o in overrides if isinstance(o, str)],
            claims=claims,
        )
    return out


def _spec_text_for_keywords(entry: SpecEntry) -> str:
    """Concatenate prose + overrides for keyword scanning.

    Note: we deliberately do NOT synthesize the structured ``claims`` block
    (``wall_strategy`` numeric, ``first_military_building``, ``expects_forward``)
    into keyword text. That synth was generating false-positive
    ``WALL_STRATEGY: ['no walls', 'walls']`` mismatches whenever the HTML
    prose said semantic equivalents like "lightly fortified" or "loosely
    walled" without using the literal words ``walls`` / ``no walls``.

    Direct claim-vs-prose contradictions are checked separately by
    ``contradiction_check`` so they're surfaced cleanly rather than as
    spurious keyword-set differences.
    """
    chunks: list[str] = [entry.doctrine_prose]
    chunks.extend(entry.prose_overrides)
    return " | ".join(c for c in chunks if c)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

@dataclass
class CivPlaystyleResult:
    data_name: str
    html_sentence: str
    spec_prose: str
    html_keywords: dict[str, list[str]] = field(default_factory=dict)
    spec_keywords: dict[str, list[str]] = field(default_factory=dict)
    only_in_html: dict[str, list[str]] = field(default_factory=dict)
    only_in_spec: dict[str, list[str]] = field(default_factory=dict)
    contradictions: list[str] = field(default_factory=list)
    has_spec_entry: bool = True
    has_html_entry: bool = True

    @property
    def total_mismatches(self) -> int:
        return (
            sum(len(v) for v in self.only_in_html.values())
            + sum(len(v) for v in self.only_in_spec.values())
        )


def compare_civ(
    data_name: str,
    html_entry: HtmlPlaystyle | None,
    spec_entry: SpecEntry | None,
) -> CivPlaystyleResult:
    res = CivPlaystyleResult(
        data_name=data_name,
        html_sentence=html_entry.playstyle_sentence if html_entry else "",
        spec_prose=(spec_entry.doctrine_prose if spec_entry else ""),
        has_html_entry=html_entry is not None,
        has_spec_entry=spec_entry is not None,
    )
    res.html_keywords = detect_keywords(
        html_entry.playstyle_sentence if html_entry else ""
    )
    res.spec_keywords = detect_keywords(
        _spec_text_for_keywords(spec_entry) if spec_entry else ""
    )
    for cat in TAXONOMY:
        h = set(res.html_keywords.get(cat, []))
        s = set(res.spec_keywords.get(cat, []))
        res.only_in_html[cat] = sorted(h - s)
        res.only_in_spec[cat] = sorted(s - h)
    res.contradictions = detect_contradictions(data_name, html_entry, spec_entry)
    return res


# ---------------------------------------------------------------------------
# Cross-civ contradiction checks
# ---------------------------------------------------------------------------

# Wall-strategy semantics, reverse-engineered from the prose-cohort layout
# in playstyle_spec.json (see commit history / docstring of this file). The
# numeric knob in <claims><wall_strategy> is NOT monotonic in "more walls" —
# instead it tags doctrine modes:
#
#   0 = heavy / palisade-or-stone-ring (turtle, "walls early with stone")
#   1 = natural-choke / terrain or war-hut substitute
#   2 = naval / dock-first (no land-base wall focus)
#   3 = (unused in current spec)
#   4 = civic-tight / settler-callable (close to TC but no wall ring)
#   5 = forward / unwalled-base / push-the-edges
#   None = economic / scattered (no fixed defense doctrine)
WALL_STRATEGY_LABEL = {
    0: "heavy-wall ring",
    1: "natural choke / terrain substitute",
    2: "naval / dock-first",
    3: "(reserved)",
    4: "civic-tight",
    5: "forward / unwalled base",
    None: "economic / scattered",
}

# Prose phrases that semantically REQUIRE / FORBID a wall-strategy class.
# These are conservative — only flag contradictions when the prose explicitly
# uses one of these tells.
_PROSE_WALL_HEAVY = (
    "walls early with stone", "stone walls", "wall ring", "palisade ring",
    "concentric rings", "fortifies a single high-ground", "tier-walls",
    "layered towers", "siege belt", "siege",
)
_PROSE_WALL_LIGHT = (
    "lightly fortified", "lightly defended", "loosely walled", "loosely defended",
    "no walls", "without walls", "skips walls", "unwalled",
    "leaves the home base", "leaving the home base",
)
_PROSE_FORWARD = (
    "forward base", "forward operational", "contested edge",
    "pushes barracks", "pushes outposts",
    "push toward the map", "push out", "constant pressure",
)


# Phrases that NEGATE a wall-heavy mention if they appear in the same
# sentence right before it. Matches things like
#   "leans on Blockhouses rather than full stone walls"
#   "skips stone walls in favor of forward outposts"
_NEGATION_LEADERS = (
    "rather than ", "instead of ", "in place of ", "no full ", "no full-",
    "without ", "skips ", "skip ", "doesn't build ", "does not build ",
    "no stone ",
)


def _prose_has(prose: str, needles: tuple[str, ...],
               *, allow_negation: bool = False) -> list[str]:
    """Substring-match each needle in lowercase prose.

    If ``allow_negation`` is True, a needle is *not* counted as a hit when
    one of ``_NEGATION_LEADERS`` appears in the 40 chars immediately
    preceding the match — that catches phrases like
    ``"rather than full stone walls"`` where ``"stone walls"`` appears
    only to be negated.
    """
    p = (prose or "").lower()
    out: list[str] = []
    for n in needles:
        idx = p.find(n)
        if idx < 0:
            continue
        if allow_negation:
            window = p[max(0, idx - 40):idx]
            if any(neg in window for neg in _NEGATION_LEADERS):
                continue
        out.append(n)
    return out


def detect_contradictions(
    data_name: str,
    html_entry: HtmlPlaystyle | None,
    spec_entry: SpecEntry | None,
) -> list[str]:
    """Return a list of human-readable contradiction messages, possibly empty.

    Each message describes a clash between the structured ``claims`` block
    in playstyle_spec.json and the doctrine prose (HTML or spec — they
    should agree). These are higher-signal than keyword-overlap diffs.
    """
    out: list[str] = []
    if not spec_entry:
        return out
    claims = spec_entry.claims or {}
    ws = claims.get("wall_strategy")
    fwd = bool(claims.get("expects_forward"))
    fmb = claims.get("first_military_building")

    # Use whichever prose source we have; prefer HTML (authoritative).
    prose_sources: list[tuple[str, str]] = []
    if html_entry and html_entry.playstyle_sentence:
        prose_sources.append(("HTML", html_entry.playstyle_sentence))
    if spec_entry.doctrine_prose:
        prose_sources.append(("SPEC", spec_entry.doctrine_prose))

    if not prose_sources:
        return out

    # Aggregate prose for hit-finding.
    combined = " | ".join(s for _, s in prose_sources)

    # Wall-heavy phrases are negation-sensitive — "rather than full stone
    # walls" must not count as a wall-heavy mention.
    heavy_hits = _prose_has(combined, _PROSE_WALL_HEAVY, allow_negation=True)
    light_hits = _prose_has(combined, _PROSE_WALL_LIGHT)
    fwd_hits = _prose_has(combined, _PROSE_FORWARD)

    # If the prose explicitly negates walls (e.g. "rather than full stone walls",
    # "leans on Blockhouses"), treat it as a wall-LIGHT signal even if it
    # didn't trip a literal _PROSE_WALL_LIGHT phrase.
    combined_low = combined.lower()
    if not light_hits:
        for neg in _NEGATION_LEADERS:
            if neg in combined_low and "wall" in combined_low:
                # Look for "<neg> <something with 'wall'>"
                idx = combined_low.find(neg)
                tail = combined_low[idx:idx + 80]
                if "wall" in tail:
                    light_hits.append(f"negation: {neg.strip()}…wall")
                    break

    # 1. wall_strategy=0 (heavy wall ring) but prose says "lightly defended"
    #    or "lightly fortified" → contradiction.
    if ws == 0 and light_hits and not heavy_hits:
        out.append(
            f"wall_strategy=0 ({WALL_STRATEGY_LABEL[0]}) contradicts prose "
            f"phrases {light_hits!r} — consider wall_strategy=5 "
            f"(forward/unwalled) or 4 (civic-tight)"
        )

    # 2. wall_strategy=5 (forward/unwalled) but prose says "stone walls" /
    #    "wall ring" / "concentric rings" → contradiction.
    if ws == 5 and heavy_hits and not light_hits and not fwd_hits:
        out.append(
            f"wall_strategy=5 ({WALL_STRATEGY_LABEL[5]}) contradicts prose "
            f"phrases {heavy_hits!r} — consider wall_strategy=0 (heavy-wall ring)"
        )

    # 3. expects_forward=True but no forward / contested-edge phrasing
    #    AND prose explicitly mentions home-base wall focus.
    if fwd and not fwd_hits and heavy_hits:
        out.append(
            f"expects_forward=True contradicts wall-heavy prose phrases "
            f"{heavy_hits!r}; no forward-push phrasing detected"
        )

    # 4. first_military_building=dock but no naval/water phrasing.
    if fmb == "dock":
        naval_hits = _prose_has(combined, (
            "dock", "harbor", "harbour", "fishing", "naval", "water",
            "fleet", "ship",
        ))
        if not naval_hits:
            out.append(
                "first_military_building=dock but prose has no naval/water "
                "phrasing — claim may be miscategorised"
            )

    # 5. first_military_building=trading_post_or_market but prose has no
    #    economic/trade phrasing.
    if fmb == "trading_post_or_market":
        econ_hits = _prose_has(combined, (
            "trading post", "trading posts", "market", "markets",
            "shrine", "shrines", "plantation", "plantations", "mill", "mills",
            "scatters", "scattered", "trickle",
        ))
        if not econ_hits:
            out.append(
                "first_military_building=trading_post_or_market but prose "
                "has no economic/trade phrasing"
            )

    return out


def detect_prose_cohort_inconsistencies(
    spec_map: dict[str, SpecEntry],
) -> dict[str, list[str]]:
    """Group civs by doctrine_prose; flag any group with inconsistent claims.

    The playstyle_spec.json is template-based: each unique doctrine_prose
    string represents a cohort, and every civ in the cohort SHOULD share
    the same wall_strategy / expects_forward / first_military_building.
    Any divergence is a likely data-entry error or a half-finished refactor.

    Returns ``{data_name: [issue, ...]}``.
    """
    from collections import defaultdict

    # Normalize prose for cohort key — decode entities, collapse whitespace.
    def _norm_prose(p: str) -> str:
        return re.sub(r"\s+", " ", html_lib.unescape(p or "").strip()).lower()

    by_cohort: dict[str, list[SpecEntry]] = defaultdict(list)
    for entry in spec_map.values():
        key = _norm_prose(entry.doctrine_prose)
        if not key:
            continue
        by_cohort[key].append(entry)

    issues: dict[str, list[str]] = defaultdict(list)
    for key, members in by_cohort.items():
        if len(members) < 2:
            continue
        ws_set = {m.claims.get("wall_strategy") for m in members}
        fwd_set = {bool(m.claims.get("expects_forward")) for m in members}
        fmb_set = {m.claims.get("first_military_building") for m in members}
        if len(ws_set) > 1:
            for m in members:
                issues[m.data_name].append(
                    f"prose-cohort wall_strategy disagreement — cohort has "
                    f"{sorted(str(x) for x in ws_set)}, this civ has "
                    f"{m.claims.get('wall_strategy')!r}"
                )
        if len(fwd_set) > 1:
            for m in members:
                issues[m.data_name].append(
                    f"prose-cohort expects_forward disagreement — cohort has "
                    f"{sorted(str(x) for x in fwd_set)}, this civ has "
                    f"{bool(m.claims.get('expects_forward'))!r}"
                )
        if len(fmb_set) > 1:
            for m in members:
                issues[m.data_name].append(
                    f"prose-cohort first_military_building disagreement — "
                    f"cohort has {sorted(str(x) for x in fmb_set)}, this "
                    f"civ has {m.claims.get('first_military_building')!r}"
                )

    return dict(issues)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_json_report(out_path: Path, results: list[CivPlaystyleResult]) -> None:
    payload = []
    for r in results:
        payload.append({
            "data_name": r.data_name,
            "has_html_entry": r.has_html_entry,
            "has_spec_entry": r.has_spec_entry,
            "html_sentence": r.html_sentence,
            "spec_prose": r.spec_prose,
            "html_keywords": r.html_keywords,
            "spec_keywords": r.spec_keywords,
            "only_in_html": r.only_in_html,
            "only_in_spec": r.only_in_spec,
            "contradictions": r.contradictions,
            "total_mismatches": r.total_mismatches,
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_markdown_report(
    out_path: Path,
    results: list[CivPlaystyleResult],
    warnings: list[str],
) -> None:
    total = len(results)
    matched = sum(1 for r in results if r.total_mismatches == 0 and r.has_spec_entry and r.has_html_entry)
    mismatched = sum(1 for r in results if r.total_mismatches > 0)
    missing_spec = sum(1 for r in results if not r.has_spec_entry)
    missing_html = sum(1 for r in results if not r.has_html_entry)

    lines: list[str] = []
    lines.append("# A New World - AI Playstyle Keyword Cross-Check")
    lines.append("")
    lines.append(
        f"**{total} civs - matched={matched}, "
        f"mismatched={mismatched}, missing_spec={missing_spec}, "
        f"missing_html={missing_html}**"
    )
    lines.append("")
    lines.append("This validator is *informational only*. Mismatches indicate")
    lines.append("the prose in `a_new_world.html` and `playstyle_spec.json`")
    lines.append("emphasise different concepts; the actual remediation requires")
    lines.append("running games and iterating .personality files.")
    lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Per-civ findings")
    lines.append("")
    for r in sorted(results, key=lambda x: x.data_name.lower()):
        lines.append(f"### {r.data_name}")
        lines.append("")
        if not r.has_html_entry:
            lines.append("- **HTML**: (no nation-node entry found)")
        else:
            lines.append(f"- **HTML sentence**: {r.html_sentence}")
        if not r.has_spec_entry:
            lines.append("- **Spec**: (no playstyle_spec.json entry)")
        else:
            lines.append(f"- **Spec prose**: {r.spec_prose}")
        lines.append("")
        lines.append("- **HTML keywords**:")
        for cat in TAXONOMY:
            kws = r.html_keywords.get(cat, [])
            lines.append(f"    - {cat}: {', '.join(kws) if kws else '(none)'}")
        lines.append("- **Spec keywords**:")
        for cat in TAXONOMY:
            kws = r.spec_keywords.get(cat, [])
            lines.append(f"    - {cat}: {', '.join(kws) if kws else '(none)'}")
        lines.append("- **Mismatches**:")
        any_diff = False
        for cat in TAXONOMY:
            only_h = r.only_in_html.get(cat, [])
            only_s = r.only_in_spec.get(cat, [])
            if only_h or only_s:
                any_diff = True
                lines.append(
                    f"    - {cat}: only_in_html=[{', '.join(only_h)}] "
                    f"only_in_spec=[{', '.join(only_s)}]"
                )
        if not any_diff:
            lines.append("    - (none)")
        if r.contradictions:
            lines.append("- **Contradictions** (claims vs prose):")
            for c in r.contradictions:
                lines.append(f"    - {c}")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare HTML playstyle prose vs playstyle_spec.json keywords "
            "(informational, exit 0 always)."
        ),
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=REPO_ROOT / "a_new_world.html",
        help="Path to the reference HTML document (default: %(default)s).",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help=(
            "Path to playstyle_spec.json. If omitted, falls back to "
            "<repo>/playstyle_spec.json then <repo>/data/playstyle_spec.json."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts" / "validation" / "ai_playstyle",
        help="Output directory (default: %(default)s).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info logging; only emit summary line.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _resolve_spec_path(arg_path: Path | None) -> tuple[Path | None, list[str]]:
    warnings: list[str] = []
    candidates: list[Path] = []
    if arg_path is not None:
        candidates.append(arg_path)
    else:
        candidates.append(REPO_ROOT / "playstyle_spec.json")
        candidates.append(REPO_ROOT / "data" / "playstyle_spec.json")
    for c in candidates:
        resolved = c.resolve() if c.is_absolute() else (Path.cwd() / c).resolve()
        if resolved.exists():
            return resolved, warnings
    warnings.append(
        "playstyle_spec.json not found at any of: "
        + ", ".join(str(c) for c in candidates)
    )
    return None, warnings


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    html_path = args.html.resolve() if args.html.is_absolute() else (Path.cwd() / args.html).resolve()
    out_dir = args.out.resolve() if args.out.is_absolute() else (Path.cwd() / args.out).resolve()
    spec_path, spec_warnings = _resolve_spec_path(args.spec)

    if not html_path.exists():
        print(f"error: HTML reference not found: {html_path}", file=sys.stderr)
        # Still always exit 0 per spec (informational), but write a stub.
        write_json_report(out_dir / "findings.json", [])
        write_markdown_report(out_dir / "findings.md", [], [f"HTML missing: {html_path}"])
        return 0

    if not args.quiet:
        print(f"[*] Parsing {html_path}")
    html_entries = parse_html_playstyles(html_path)
    by_data_name: dict[str, HtmlPlaystyle] = {h.data_name: h for h in html_entries}
    if not args.quiet:
        print(f"[+] Parsed {len(html_entries)} nation-node entries")

    spec_map: dict[str, SpecEntry] = {}
    if spec_path is not None:
        spec_map = load_playstyle_spec(spec_path)
        if not args.quiet:
            print(f"[+] Loaded {len(spec_map)} playstyle spec entries from {spec_path}")
    else:
        if not args.quiet:
            print("[!] playstyle_spec.json not found - all civs will report has_spec_entry=False")

    # Merge data_names from both sources so we don't drop any civ.
    all_names = sorted(set(by_data_name) | set(spec_map))

    results: list[CivPlaystyleResult] = []
    for dn in all_names:
        results.append(compare_civ(
            data_name=dn,
            html_entry=by_data_name.get(dn),
            spec_entry=spec_map.get(dn),
        ))

    # Cross-civ cohort check: if 2+ civs share the same doctrine_prose but
    # have differing structured claims, flag every member of that cohort.
    cohort_issues = detect_prose_cohort_inconsistencies(spec_map)
    for r in results:
        if r.data_name in cohort_issues:
            r.contradictions = list(r.contradictions) + cohort_issues[r.data_name]

    json_path = out_dir / "findings.json"
    md_path = out_dir / "findings.md"
    write_json_report(json_path, results)
    write_markdown_report(md_path, results, spec_warnings)

    if not args.quiet:
        print(f"[+] Wrote JSON: {json_path}")
        print(f"[+] Wrote MD:   {md_path}")

    matched = sum(1 for r in results if r.total_mismatches == 0 and r.has_spec_entry and r.has_html_entry)
    mismatched = sum(1 for r in results if r.total_mismatches > 0)
    missing_spec = sum(1 for r in results if not r.has_spec_entry)
    missing_html = sum(1 for r in results if not r.has_html_entry)
    contradicting = sum(1 for r in results if r.contradictions)
    total_contra = sum(len(r.contradictions) for r in results)
    print(
        f"civs={len(results)} matched={matched} mismatched={mismatched} "
        f"missing_spec={missing_spec} missing_html={missing_html} "
        f"contradicting_civs={contradicting} contradiction_msgs={total_contra}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
