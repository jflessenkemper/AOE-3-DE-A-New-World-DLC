#!/usr/bin/env python3
# ============================================================================
# DEPRECATED / OBSOLETE — DO NOT GATE. This validator parses the same
# <!-- DEV-START name="..." --> / <!-- DEV-END --> HTML blocks as
# validate_dev_tree.py, which were intentionally removed from a_new_world.html
# in commit 6db1026 ("Remove dev-tree subsections + Dev Trees Only button from
# reference site"). With zero DEV-START blocks it raises SystemExit before doing
# any work, so it can never pass. Kept only for git history. The HTML-vs-civmods
# art-wiring it once checked is now covered by the GATED civmods_art_consistency,
# civ_asset_existence, art_coverage, and civ_crossrefs validators.
# ============================================================================
r"""Cross-check HTML Development art references against data/civmods.xml wiring.

The dev-tree validator (``validate_dev_tree.py``) proves every flag/portrait
referenced in ``a_new_world.html`` resolves to a file on disk. This validator
takes the next step: it confirms the *wiring* between the HTML reference and
the engine-side civ definitions is consistent.

Per civ, three pairs are checked:

  1. HTML "Scoreboard flag" ``<img src>`` (Flag_*.png basename)
       vs ``civmods.xml/civ[name=token]/homecityflagiconwpf`` basename.
  2. HTML "Player Summary flag" ``<img src>``
       vs ``civmods.xml/civ[name=token]/postgameflagiconwpf`` basename.
  3. HTML Portrait (Lobby/Diplomacy/Chat) basename
       vs ``civmods.xml/civ[name=token]/portrait`` slug. Engine paths look like
       ``objects\flags\<slug>``; the slug is fuzzy-matched against the civ
       token / data-name. Reported as a NOTE (no hard fail) since the engine
       path is intentionally not a PNG. ANW Revolution civs intentionally
       reuse the parent culture's 3D flag prop while wiring their per-civ AI
       avatar through a separate ``cpai_avatar_*.png`` asset; the NOTE is
       suppressed when a matching avatar PNG is found on disk.

Revolution-only civs (reached only through revolution dispatch) intentionally
have no ``<Civ><Name>`` entry in
civmods.xml — those are demoted from BLOCKER to NOTE when the home-city
XML + ``.personality`` file both exist.

#1 and #2 mismatches are BLOCKER. #3 mismatches and revolution-only civs
are NOTE.

Inputs (auto-discovered from repo root, override with --html / --civmods /
--dev-tree-findings):

  * ``a_new_world.html``
  * ``data/civmods.xml``
  * ``artifacts/validation/dev_tree/dev_tree_findings.json``

Outputs (to ``artifacts/validation/civmods_art/``):

  * ``findings.json``
  * ``findings.md``

Exit 0 iff zero BLOCKER findings; otherwise 1.

Usage::

    python3 tools/validation/validate_civmods_art.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from bs4 import BeautifulSoup, Tag
except ImportError as exc:  # pragma: no cover - dep is required
    raise SystemExit(
        "beautifulsoup4 is required. Install with: "
        ".venv/bin/python -m pip install beautifulsoup4"
    ) from exc


# ---------------------------------------------------------------------------
# Severity buckets
# ---------------------------------------------------------------------------

BLOCKER = "BLOCKER"
NOTE = "NOTE"

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Finding:
    severity: str
    category: str
    message: str


@dataclass
class CivResult:
    civ_token: str
    civ_display: str
    data_name: str
    html_scoreboard_flag: str = ""
    html_player_summary_flag: str = ""
    html_portrait: str = ""
    xml_homecity_flag: str = ""
    xml_postgame_flag: str = ""
    xml_portrait: str = ""
    ok: bool = True
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, category: str, message: str) -> None:
        self.findings.append(Finding(severity, category, message))
        if severity == BLOCKER:
            self.ok = False


# ---------------------------------------------------------------------------
# HTML parsing - reuses the same DEV-START/END convention as validate_dev_tree
# ---------------------------------------------------------------------------

_DEV_START_RE = re.compile(
    r'<!--\s*DEV-START\s+name="([^"]+)"\s*-->(.*?)<!--\s*DEV-END\s+name="\1"\s*-->',
    re.DOTALL,
)


def _row_label(row: Tag) -> str:
    label_cell = row.find("td", class_="dev-cell-label")
    if not label_cell:
        return ""
    parts: list[str] = []
    for child in label_cell.children:
        if getattr(child, "name", None) == "span" and "dev-ctx" in (child.get("class") or []):
            break
        if isinstance(child, str):
            parts.append(child)
        else:
            parts.append(child.get_text(" ", strip=True))
    return "".join(parts).strip()


def _row_value_cell(row: Tag) -> Tag | None:
    cells = row.find_all("td", recursive=False)
    if len(cells) >= 2:
        return cells[1]
    return None


def _value_img_src(cell: Tag | None) -> str:
    if cell is None:
        return ""
    img = cell.find("img")
    return (img.get("src", "") if img is not None else "").strip()


def _section_of_row(row: Tag) -> str:
    prev = row.find_previous("th", class_="dev-section")
    return prev.get_text(" ", strip=True).lower() if prev else ""


@dataclass
class DevArt:
    """Subset of dev-table fields needed for the art cross-check."""
    name: str
    data_name: str
    civ_picker_name: str = ""
    portrait_lobby: str = ""
    scoreboard_flag: str = ""
    player_summary_flag: str = ""
    portrait_diplomacy: str = ""
    portrait_chat: str = ""


def parse_dev_art(html_path: Path) -> tuple[list[DevArt], list[str]]:
    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    warnings: list[str] = []

    dev_tables_in_doc = soup.find_all("table", class_="dev-table")
    block_iter = list(_DEV_START_RE.finditer(raw))

    if len(block_iter) != len(dev_tables_in_doc):
        warnings.append(
            f"DEV-START/END count ({len(block_iter)}) != "
            f"<table class='dev-table'> count ({len(dev_tables_in_doc)})"
        )

    table_to_node: dict[int, Tag] = {}
    for tbl in dev_tables_in_doc:
        node = tbl.find_parent("details", class_="nation-node")
        if node is not None:
            table_to_node[id(tbl)] = node

    out: list[DevArt] = []
    for idx, match in enumerate(block_iter):
        if idx >= len(dev_tables_in_doc):
            break
        name = match.group(1).strip()
        tbl = dev_tables_in_doc[idx]
        node = table_to_node.get(id(tbl))
        data_name = node.get("data-name", "").strip() if node is not None else ""
        dev = DevArt(name=name, data_name=data_name or name)

        for row in tbl.find_all("tr"):
            if row.find("th", class_="dev-section"):
                continue
            label = _row_label(row).rstrip(": ").strip().lower()
            if not label:
                continue
            section = _section_of_row(row)
            cell = _row_value_cell(row)
            if cell is None:
                continue

            if section.startswith("lobby"):
                if label == "civ-picker name":
                    strong = cell.find("strong", class_="dev-str")
                    dev.civ_picker_name = (
                        strong.get_text(" ", strip=True) if strong else cell.get_text(" ", strip=True)
                    )
                elif label == "portrait":
                    dev.portrait_lobby = _value_img_src(cell)
            elif section.startswith("in-match hud"):
                if label == "scoreboard flag":
                    dev.scoreboard_flag = _value_img_src(cell)
                elif label == "player summary flag":
                    dev.player_summary_flag = _value_img_src(cell)
            elif section.startswith("diplomacy"):
                if label == "portrait":
                    dev.portrait_diplomacy = _value_img_src(cell)
            elif section.startswith("chat"):
                if label == "portrait":
                    dev.portrait_chat = _value_img_src(cell)

        out.append(dev)
    return out, warnings


# ---------------------------------------------------------------------------
# civmods.xml parsing
# ---------------------------------------------------------------------------

def _xml_text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


@dataclass
class CivmodsEntry:
    name: str
    homecity_flag: str = ""
    postgame_flag: str = ""
    portrait: str = ""


def load_civmods(path: Path) -> dict[str, CivmodsEntry]:
    out: dict[str, CivmodsEntry] = {}
    if not path.exists():
        return out
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return out

    # The XML uses mixed-case element names (<Civ>, <Name>, <Portrait>,
    # <HomeCityFlagIconWPF>, <PostgameFlagIconWPF>). ElementTree's findall
    # is case-sensitive, so iterate over all direct children of the root and
    # match by lower-cased local name.
    def _local(elem) -> str:
        tag = elem.tag
        if "}" in tag:
            tag = tag.rsplit("}", 1)[-1]
        return tag.lower()

    def _find_child(parent, name_lower: str):
        for child in parent:
            if _local(child) == name_lower:
                return child
        return None

    root = tree.getroot()
    for civ in root:
        if _local(civ) != "civ":
            continue
        name_elem = _find_child(civ, "name")
        name = _xml_text(name_elem)
        if not name:
            continue
        out[name] = CivmodsEntry(
            name=name,
            homecity_flag=_xml_text(_find_child(civ, "homecityflagiconwpf")),
            postgame_flag=_xml_text(_find_child(civ, "postgameflagiconwpf")),
            portrait=_xml_text(_find_child(civ, "portrait")),
        )
    return out


# ---------------------------------------------------------------------------
# dev_tree_findings.json -> data_name -> civ_token mapping
# ---------------------------------------------------------------------------

def load_data_name_to_token(path: Path) -> dict[str, tuple[str, str]]:
    """Returns mapping: data_name -> (civ_token, civ_display)."""
    if not path.exists():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out: dict[str, tuple[str, str]] = {}
    for r in rows:
        dn = (r.get("data_name") or "").strip()
        token = (r.get("civ_token") or "").strip()
        display = (r.get("civ_display") or "").strip()
        if dn:
            out[dn] = (token, display)
    return out


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

_FLAG_BASENAME_RE = re.compile(r"([Ff]lag_[A-Za-z0-9_]+\.png)$")


def _basename(path_like: str) -> str:
    if not path_like:
        return ""
    norm = path_like.replace("\\", "/").strip()
    return norm.rsplit("/", 1)[-1].lower()


def _flag_basename(path_like: str) -> str:
    """Return the lowercase ``flag_<slug>.png`` basename if recognisable."""
    if not path_like:
        return ""
    m = _FLAG_BASENAME_RE.search(path_like.replace("\\", "/"))
    if m:
        return m.group(1).lower()
    return _basename(path_like)


def _portrait_slug(engine_path: str) -> str:
    """Extract the trailing slug from ``objects\\flags\\<slug>``."""
    if not engine_path:
        return ""
    norm = engine_path.replace("\\", "/").strip().lower()
    return norm.rsplit("/", 1)[-1]


def _civ_token_slug(token: str) -> str:
    """Strip common prefixes (XP, DE, ANW) and lowercase, e.g. XPAztec -> aztec."""
    t = token or ""
    for pfx in ("ANW", "XP", "DE"):
        if t.startswith(pfx):
            t = t[len(pfx):]
            break
    return t.lower()


def _slug_related(xml_slug: str, token: str, data_name: str) -> bool:
    """Heuristic: is the engine portrait slug plausibly related to this civ?"""
    if not xml_slug:
        return False
    candidates: set[str] = set()
    if token:
        candidates.add(_civ_token_slug(token))
        candidates.add(token.lower())
    if data_name:
        first_word = data_name.split(" ", 1)[0].lower()
        candidates.add(first_word)
        candidates.add(first_word.rstrip("s"))  # plural -> singular
        candidates.add(first_word + "s")
    candidates.discard("")
    for c in candidates:
        if c and (c == xml_slug or c in xml_slug or xml_slug in c):
            return True
    return False


def _avatar_png_exists(token: str, html_portrait: str = "") -> bool:
    """Return True if a per-civ AI avatar PNG exists on disk.

    The engine's per-civ AI avatar PNG lives in
    ``resources/images/icons/singleplayer/``. Its presence proves the civ has
    its own UI portrait asset, independent of the 3D flag prop referenced by
    ``<Portrait>objects\\flags\\<culture>`` in civmods.xml.

    Two signals are checked:
      1. The HTML-referenced portrait PNG path resolves on disk (strongest
         signal — proves the HTML reference is wired to a real file).
      2. Heuristic ``cpai_avatar_*.png`` filenames derived from the civ token
         (fallback when HTML reference is missing).
    """
    base = REPO_ROOT / "resources" / "images" / "icons" / "singleplayer"
    # 1. HTML-referenced PNG path (strongest signal)
    if html_portrait:
        norm = html_portrait.replace("\\", "/").strip()
        png_basename = norm.rsplit("/", 1)[-1]
        if png_basename and (base / png_basename).exists():
            return True
        # also try resolving the full relative path from REPO_ROOT
        if (REPO_ROOT / norm).exists():
            return True
    # 2. Token-derived filename heuristics
    if token:
        slug = _civ_token_slug(token)
        candidates = [
            f"cpai_avatar_{token.lower()}.png",
            f"cpai_avatar_anw{slug}.png",
            f"cpai_avatar_{slug}.png",
        ]
        for name in candidates:
            if (base / name).exists():
                return True
    return False


def _is_revolution_only_civ(token: str) -> bool:
    """Return True if the civ is dispatched ONLY via revolution (no civmod
    entry expected).

    Signal: a home-city XML and a ``.personality`` file exist, but the civ
    intentionally lacks a ``<Civ><Name>`` entry in civmods.xml because it is
    reached exclusively through a revolution dispatch (see
    ``leader_revolution_commanders.xs``).
    """
    if not token:
        return False
    civtok = token.lower()
    hc_file = REPO_ROOT / "data" / f"anwhomecity{civtok.removeprefix('anw')}.xml"
    pers_file = REPO_ROOT / "game" / "ai" / f"{civtok}.personality"
    return hc_file.exists() and pers_file.exists()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_one(
    dev: DevArt,
    civ_token: str,
    civ_display: str,
    civ_entry: CivmodsEntry | None,
) -> CivResult:
    res = CivResult(
        civ_token=civ_token,
        civ_display=civ_display or dev.civ_picker_name or dev.data_name,
        data_name=dev.data_name,
        html_scoreboard_flag=dev.scoreboard_flag,
        html_player_summary_flag=dev.player_summary_flag,
        html_portrait=dev.portrait_lobby or dev.portrait_diplomacy or dev.portrait_chat,
    )
    if civ_entry is None:
        # Revolution-only civs are dispatched via revolution scripts and
        # intentionally have no <Civ><Name> entry in civmods.xml.
        # Demote to NOTE — it is not a wiring bug.
        if _is_revolution_only_civ(civ_token):
            res.add(
                NOTE, "civmods_lookup",
                f"civ token `{civ_token}` is a revolution-only civ (home city "
                f"+ .personality present, no civmod entry expected); "
                f"art cross-check skipped.",
            )
        else:
            res.add(
                BLOCKER, "civmods_lookup",
                f"civ token `{civ_token}` not found in data/civmods.xml; "
                f"cannot cross-check art.",
            )
        return res

    res.xml_homecity_flag = civ_entry.homecity_flag
    res.xml_postgame_flag = civ_entry.postgame_flag
    res.xml_portrait = civ_entry.portrait

    # ---- 1. Scoreboard flag vs homecityflagiconwpf -----------------------
    html_sb = _flag_basename(dev.scoreboard_flag)
    xml_hc = _flag_basename(civ_entry.homecity_flag)
    if html_sb and html_sb.startswith("flag_") and xml_hc and xml_hc.startswith("flag_"):
        if html_sb != xml_hc:
            res.add(
                BLOCKER, "scoreboard_flag",
                f"HTML Scoreboard flag basename `{html_sb}` does not match "
                f"civmods.xml <homecityflagiconwpf> basename `{xml_hc}` "
                f"(civ `{civ_token}`).",
            )
    elif html_sb and not xml_hc:
        res.add(
            BLOCKER, "scoreboard_flag",
            f"civmods.xml <homecityflagiconwpf> empty for civ `{civ_token}` "
            f"but HTML references `{dev.scoreboard_flag}`.",
        )

    # ---- 2. Player Summary flag vs postgameflagiconwpf ------------------
    html_ps = _flag_basename(dev.player_summary_flag)
    xml_pg = _flag_basename(civ_entry.postgame_flag)
    if html_ps and html_ps.startswith("flag_") and xml_pg and xml_pg.startswith("flag_"):
        if html_ps != xml_pg:
            res.add(
                BLOCKER, "player_summary_flag",
                f"HTML Player Summary flag basename `{html_ps}` does not match "
                f"civmods.xml <postgameflagiconwpf> basename `{xml_pg}` "
                f"(civ `{civ_token}`).",
            )
    elif html_ps and not xml_pg:
        res.add(
            BLOCKER, "player_summary_flag",
            f"civmods.xml <postgameflagiconwpf> empty for civ `{civ_token}` "
            f"but HTML references `{dev.player_summary_flag}`.",
        )

    # ---- 3. Portrait slug vs <portrait>objects\flags\<slug> --------------
    # NOTE: civmods.xml ``<Portrait>`` is the 3D in-game flag prop slug
    # (``objects\flags\<culture>``), not the AI avatar PNG. ANW Revolution
    # civs intentionally reuse the parent culture's flag prop (e.g.
    # ANWBrazil → ``portuguese``), while the per-civ AI avatar PNG lives in
    # ``resources/images/icons/singleplayer/cpai_avatar_*.png``. The
    # slug-vs-token heuristic produces false positives in that pattern, so
    # we suppress the NOTE when a corresponding avatar PNG exists on disk
    # (proves the per-civ avatar is wired separately).
    xml_slug = _portrait_slug(civ_entry.portrait)
    html_portrait = res.html_portrait
    if xml_slug and html_portrait:
        if not _slug_related(xml_slug, civ_token, dev.data_name):
            if not _avatar_png_exists(civ_token, html_portrait):
                res.add(
                    NOTE, "portrait",
                    f"civmods.xml <portrait> slug `{xml_slug}` looks unrelated "
                    f"to civ token `{civ_token}` / data-name `{dev.data_name}` "
                    f"and no `cpai_avatar_*.png` was found on disk for this "
                    f"civ. HTML references portrait `{html_portrait}`.",
                )
    elif html_portrait and not xml_slug:
        if not _avatar_png_exists(civ_token, html_portrait):
            res.add(
                NOTE, "portrait",
                f"civmods.xml <portrait> is empty for civ `{civ_token}` and "
                f"no `cpai_avatar_*.png` was found on disk. HTML references "
                f"portrait `{html_portrait}`.",
            )

    return res


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_json_report(out_path: Path, results: list[CivResult]) -> None:
    payload = []
    for r in results:
        payload.append({
            "civ_token": r.civ_token,
            "civ_display": r.civ_display,
            "data_name": r.data_name,
            "html_scoreboard_flag": r.html_scoreboard_flag,
            "html_player_summary_flag": r.html_player_summary_flag,
            "html_portrait": r.html_portrait,
            "xml_homecity_flag": r.xml_homecity_flag,
            "xml_postgame_flag": r.xml_postgame_flag,
            "xml_portrait": r.xml_portrait,
            "ok": r.ok,
            "findings": [asdict(f) for f in r.findings],
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_markdown_report(
    out_path: Path,
    results: list[CivResult],
    parser_warnings: list[str],
) -> None:
    total = len(results)
    pass_count = sum(1 for r in results if r.ok and not r.findings)
    blocker_count = sum(1 for r in results for f in r.findings if f.severity == BLOCKER)
    note_count = sum(1 for r in results for f in r.findings if f.severity == NOTE)

    lines: list[str] = []
    lines.append("# A New World - civmods.xml Art Cross-Check")
    lines.append("")
    lines.append(
        f"**{pass_count}/{total} civs PASS, {blocker_count} BLOCKER, {note_count} NOTE**"
    )
    lines.append("")

    if parser_warnings:
        lines.append("## Parser warnings")
        lines.append("")
        for w in parser_warnings:
            lines.append(f"- {w}")
        lines.append("")

    for severity in (BLOCKER, NOTE):
        bucket: list[tuple[CivResult, list[Finding]]] = []
        for r in results:
            findings = [f for f in r.findings if f.severity == severity]
            if findings:
                bucket.append((r, findings))
        if not bucket:
            continue
        total_in_bucket = sum(len(fs) for _, fs in bucket)
        lines.append(f"## {severity} ({total_in_bucket})")
        lines.append("")
        for r, findings in bucket:
            label = r.civ_token or r.data_name or "(unknown civ)"
            lines.append(f"### {label} - {r.civ_display}")
            lines.append("")
            for f in findings:
                lines.append(f"- *{f.category}*: {f.message}")
            lines.append("")

    lines.append("## Per-civ status")
    lines.append("")
    for r in sorted(results, key=lambda x: (x.civ_token or "").lower()):
        label = r.civ_token or r.data_name or "(?)"
        status = "PASS" if r.ok and not r.findings else "FAIL"
        n_block = sum(1 for f in r.findings if f.severity == BLOCKER)
        n_note = sum(1 for f in r.findings if f.severity == NOTE)
        lines.append(
            f"- `{label}` ({r.civ_display}): **{status}** -- "
            f"BLOCKER={n_block} NOTE={n_note}"
        )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cross-check HTML art references vs data/civmods.xml wiring.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=REPO_ROOT / "a_new_world.html",
        help="Path to the reference HTML document (default: %(default)s).",
    )
    parser.add_argument(
        "--civmods",
        type=Path,
        default=REPO_ROOT / "data" / "civmods.xml",
        help="Path to civmods.xml (default: %(default)s).",
    )
    parser.add_argument(
        "--dev-tree-findings",
        type=Path,
        default=REPO_ROOT / "artifacts" / "validation" / "dev_tree" / "dev_tree_findings.json",
        help="Path to dev_tree findings JSON (default: %(default)s).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts" / "validation" / "civmods_art",
        help="Directory to write findings.json + findings.md (default: %(default)s).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info logging; only emit summary line at the end.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    html_path = args.html.resolve() if args.html.is_absolute() else (Path.cwd() / args.html).resolve()
    civmods_path = args.civmods.resolve() if args.civmods.is_absolute() else (Path.cwd() / args.civmods).resolve()
    devtree_path = args.dev_tree_findings.resolve() if args.dev_tree_findings.is_absolute() else (Path.cwd() / args.dev_tree_findings).resolve()
    out_dir = args.out.resolve() if args.out.is_absolute() else (Path.cwd() / args.out).resolve()

    if not html_path.exists():
        print(f"error: HTML reference not found: {html_path}", file=sys.stderr)
        return 1
    if not civmods_path.exists():
        print(f"error: civmods.xml not found: {civmods_path}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"[*] Parsing {html_path}")
    dev_arts, warnings = parse_dev_art(html_path)
    if not dev_arts:
        print("error: no DEV-START blocks parsed from HTML.", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"[+] Parsed {len(dev_arts)} dev-tables")

    civmods = load_civmods(civmods_path)
    if not civmods:
        warnings.append(f"civmods.xml empty or unparseable: {civmods_path}")

    data_name_to_token = load_data_name_to_token(devtree_path)
    if not data_name_to_token:
        warnings.append(
            f"dev_tree findings JSON missing/empty ({devtree_path}); "
            "civ_token will be inferred via fallback heuristic."
        )

    results: list[CivResult] = []
    for dev in dev_arts:
        token, display = data_name_to_token.get(dev.data_name, ("", ""))
        if not token:
            # Fallback: try matching dev.name against civmods directly (e.g. "British" -> "British").
            if dev.name in civmods:
                token = dev.name
                display = dev.civ_picker_name
        entry = civmods.get(token) if token else None
        results.append(validate_one(dev, token, display, entry))

    json_path = out_dir / "findings.json"
    md_path = out_dir / "findings.md"
    write_json_report(json_path, results)
    write_markdown_report(md_path, results, warnings)

    if not args.quiet:
        print(f"[+] Wrote JSON: {json_path}")
        print(f"[+] Wrote MD:   {md_path}")

    blocker = sum(1 for r in results for f in r.findings if f.severity == BLOCKER)
    note = sum(1 for r in results for f in r.findings if f.severity == NOTE)
    pass_count = sum(1 for r in results if r.ok and not r.findings)
    print(
        f"civs={len(results)} pass={pass_count} blocker={blocker} note={note}"
    )
    return 0 if blocker == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
