#!/usr/bin/env python3
"""Build a unified art-asset inventory for the ANW mod.

Walks four sources and joins them per-civ:

  1. ``a_new_world.html``  → every ``<img src="resources/images/...">``
  2. ``resources/images/`` → on-disk static reference images (PNG/JPG/SVG)
  3. ``art/``              → mod-internal art (PNG/JPG/DDT/XML)
  4. ``data/civmods.xml`` → per-civ ``HomeCityPreviewWPF`` /
     ``HomeCityFlagIconWPF`` / ``HomeCityFlagTexture`` references
     (canonical engine-readable filename; ``modinfo.json`` ships ``data/``)
  5. Deployed mod dir (Proton): same layout under
     ``…/Age of Empires 3 DE/.../mods/local/A New World``

For every ANW civ it produces a record like::

    {
      "civ": "ANWArgentines",
      "html_flag":            "resources/images/icons/flags/Flag_Argentinian.png",
      "html_portrait":        "resources/images/icons/singleplayer/cpai_avatar_argentines_san_martin.png",
      "civmods_flag_wpf":     "resources/images/icons/flags/Flag_Argentinian.png",
      "civmods_portrait_wpf": "resources/images/icons/singleplayer/cpai_avatar_argentines_san_martin.png",
      "civmods_flag_texture": "objects/flags/...",
      "art_portrait_hires":   "art/ui/leaders/san_martin.png",
      "deployed_html_flag":   "<deployed-path>/resources/images/icons/flags/Flag_Argentinian.png",
      ...
    }

It also catalogs every standalone art asset under
``art/`` (buildings, units, ui, etc.) and every loose
file under ``resources/images/`` that no civ section claimed (ui_elements bucket).

**Track 2 extension** (visual-confirmation pipeline): every ANW civ record
also gets an ``art_surfaces`` block enumerating each in-game art surface
exposed by civmods.xml (``diplomacy_portrait_wpf``,
``scoreboard_portrait_wpf``, ``postgame_flag_wpf``, ``homecity_preview_wpf``,
``homecity_flag_icon_wpf``, ``homecity_flag_button_wpf``,
``homecity_filename``, ``custom_leader_portrait_hires``) — each with
``path`` (repo-relative POSIX) and ``_on_disk`` (bool). A top-level
``art_surface_summary`` block reports ``custom_portraits_total``,
``custom_portraits_missing``, and ``civmods_art_missing``.

Outputs ``tools/validation/art_inventory.json`` (pretty-printed) so other
verifiers can ingest it without re-walking the trees.

Usage::

    python3 tools/validation/art_inventory.py            # writes JSON
    python3 tools/validation/art_inventory.py --stdout   # JSON to stdout
    python3 tools/validation/art_inventory.py --summary  # one-line stats
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[2]
HTML_FILE = REPO / "a_new_world.html"
RESOURCES = REPO / "resources" / "images"
ART = REPO / "art"
CIVMODS = REPO / "data" / "civmods.xml"
INVENTORY_OUT = Path(__file__).resolve().parent / "art_inventory.json"

DEFAULT_DEPLOYED = Path(
    "/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/"
    "drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/"
    "mods/local/A New World"
)

# ---------------------------------------------------------------------------
# Regex / parsing helpers
# ---------------------------------------------------------------------------

# An <img …> tag — captures the full attribute blob so we can later pluck
# src and alt / class.
_IMG_TAG_RE = re.compile(r"<img\b([^>]+)>", re.IGNORECASE)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

# HTML civ-section delimiter, e.g. <!-- ── Argentines ── -->
_SECTION_RE = re.compile(r"<!--\s*[─\-]+\s*([^─\-][^<]*?)\s*[─\-]+\s*-->")

# Civmods.xml fields we care about (one per civ block, treat as text-search per
# civ subblock). Tags in civmods.xml are lowercase; use IGNORECASE for safety.
_RE_FLAGS = re.DOTALL | re.IGNORECASE
_CIV_BLOCK_RE = re.compile(r"<Civ>(.*?)</Civ>", _RE_FLAGS)
_NAME_RE = re.compile(r"<Name>([^<]+)</Name>", re.IGNORECASE)
_PREVIEW_WPF_RE = re.compile(r"<HomeCityPreviewWPF>([^<]+)</HomeCityPreviewWPF>", re.IGNORECASE)
_FLAG_WPF_RE = re.compile(r"<HomeCityFlagIconWPF>([^<]+)</HomeCityFlagIconWPF>", re.IGNORECASE)
_POSTGAME_WPF_RE = re.compile(r"<PostgameFlagIconWPF>([^<]+)</PostgameFlagIconWPF>", re.IGNORECASE)
_FLAG_TEX_RE = re.compile(r"<HomeCityFlagTexture>([^<]+)</HomeCityFlagTexture>", re.IGNORECASE)
_PORTRAIT_RE = re.compile(r"<Portrait>([^<]+)</Portrait>", re.IGNORECASE)
# New surfaces (Track 2 visual confirmation pipeline)
_SMALL_PORTRAIT_WPF_RE = re.compile(
    r"<SmallPortraitTextureWPF>([^<]+)</SmallPortraitTextureWPF>", re.IGNORECASE
)
_HC_FLAG_BUTTON_WPF_RE = re.compile(
    r"<HomeCityFlagButtonWPF>([^<]+)</HomeCityFlagButtonWPF>", re.IGNORECASE
)
_HC_FILENAME_RE = re.compile(
    r"<HomeCityFileName>([^<]+)</HomeCityFileName>", re.IGNORECASE
)
# Home-city XML top-level <visual> — the scene/animation file (e.g.
# "french\french_homecity.xml" or "british\british_homecity.xml").
_HC_VISUAL_RE = re.compile(
    r"^\s*<visual>([^<\r\n]+)</visual>", re.MULTILINE | re.IGNORECASE
)
# Art-directory walkers for surfaces that may exist as separate tree dirs.
# These dirs are not in the repo yet — we record the resolved path from
# civmods.xml and also attempt the conventional art/ui/<surface>/ location.
_ART_UI_DIPLOMACY = Path("art/ui/diplomacy")
_ART_UI_SCOREBOARD = Path("art/ui/scoreboard")
_ART_UI_POSTGAME   = Path("art/ui/postgame")

# ---------------------------------------------------------------------------
# Home-city XML helpers for idle animation files + primary deck name
# ---------------------------------------------------------------------------

# Representative building slugs used to select up to 5 <file> entries from
# the homecity XML building/unit <file>...</file> blocks.  We rank matches
# by this priority list; any remaining <file> refs fill the list to 5.
_HC_FILE_PRIORITY = [
    "towncenter", "homecity", "manufacturing", "church", "cathedral", "estate",
]

# Matches any <file>path</file> element in the homecity XML (buildings/units).
_HC_FILE_RE = re.compile(r"<file>([^<\r\n]+)</file>", re.IGNORECASE)
# Matches the <name> inside the first <deck> block.
_HC_FIRST_DECK_NAME_RE = re.compile(
    r"<deck>.*?<name>([^<]+)</name>",
    re.DOTALL | re.IGNORECASE,
)


def _read_hc_xml(civ_name: str, hc_path: str, repo: Path) -> str:
    """Read the homecity XML text for *civ_name*, trying multiple fallback
    paths.  Returns empty string if not found."""
    # 1. Path from civmods (already resolved to data/<filename>)
    if hc_path and (repo / hc_path).exists():
        try:
            return (repo / hc_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    # 2. Convention: data/anwhomecity<lower>.xml
    stem = civ_name.replace("ANW", "").lower()
    cand = repo / "data" / f"anwhomecity{stem}.xml"
    if cand.exists():
        try:
            return cand.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return ""


def _homecity_idle_files(hc_xml: str, *, max_files: int = 5) -> list[str]:
    """Return up to *max_files* representative <file> paths from the homecity XML.

    Priority slots are filled by the _HC_FILE_PRIORITY keyword list first;
    remaining slots are back-filled from any other <file> references so we
    always return at least something when the XML is present.
    """
    all_files = [_normalise_path(m.strip()) for m in _HC_FILE_RE.findall(hc_xml)]
    if not all_files:
        return []
    prioritised: list[str] = []
    # Greedily fill by priority keywords (first match per keyword).
    seen: set[str] = set()
    for kw in _HC_FILE_PRIORITY:
        for f in all_files:
            if kw in f.lower() and f not in seen:
                prioritised.append(f)
                seen.add(f)
                break
    # Back-fill with remaining files until we reach max_files.
    for f in all_files:
        if len(prioritised) >= max_files:
            break
        if f not in seen:
            prioritised.append(f)
            seen.add(f)
    return prioritised[:max_files]


def _primary_deck_name(hc_xml: str) -> str:
    """Return the <name> of the first <deck> block in the homecity XML."""
    m = _HC_FIRST_DECK_NAME_RE.search(hc_xml)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------------------
# 1. HTML extraction
# ---------------------------------------------------------------------------

def _normalise_path(p: str) -> str:
    """Backslash → slash, strip leading ./, collapse double slashes."""
    p = p.replace("\\", "/").lstrip("./")
    while "//" in p:
        p = p.replace("//", "/")
    return p


def parse_html_imgs(text: str) -> list[dict]:
    """Return one dict per <img> tag with src, alt, classes, civ_section."""
    sections = list(_SECTION_RE.finditer(text))

    def section_for(pos: int) -> str | None:
        # Walk backwards to find the most recent section comment.
        prev = None
        for s in sections:
            if s.start() > pos:
                break
            prev = s
        return prev.group(1).strip() if prev else None

    out: list[dict] = []
    for m in _IMG_TAG_RE.finditer(text):
        attrs = dict(_ATTR_RE.findall(m.group(1)))
        src = _normalise_path(attrs.get("src", ""))
        if not src:
            continue
        out.append({
            "src": src,
            "alt": html.unescape(attrs.get("alt", "")),
            "class": attrs.get("class", ""),
            "civ_section": section_for(m.start()),
        })
    return out


# ---------------------------------------------------------------------------
# 2. civmods.xml extraction
# ---------------------------------------------------------------------------

def parse_civmods(xml_text: str) -> dict[str, dict[str, str]]:
    """Return {civ_name: {portrait_wpf, flag_wpf, postgame_wpf, flag_tex,
    portrait_obj, small_portrait_wpf, flag_button_wpf, homecity_filename}}.

    All fields normalised to POSIX-slash form. Missing fields are empty
    strings (not None) so consumers can treat them uniformly.
    """
    def _first(rx: re.Pattern, blk: str) -> str:
        m = rx.search(blk)
        return m.group(1).strip() if m else ""

    out: dict[str, dict[str, str]] = {}
    for block in _CIV_BLOCK_RE.findall(xml_text):
        nm = _NAME_RE.search(block)
        if not nm:
            continue
        name = nm.group(1).strip()
        out[name] = {
            "portrait_wpf":        _first(_PREVIEW_WPF_RE, block),
            "flag_wpf":            _first(_FLAG_WPF_RE, block),
            "postgame_wpf":        _first(_POSTGAME_WPF_RE, block),
            "flag_texture":        _first(_FLAG_TEX_RE, block),
            "portrait_obj":        _first(_PORTRAIT_RE, block),
            "small_portrait_wpf":  _first(_SMALL_PORTRAIT_WPF_RE, block),
            "flag_button_wpf":     _first(_HC_FLAG_BUTTON_WPF_RE, block),
            "homecity_filename":   _first(_HC_FILENAME_RE, block),
        }
        # Normalise paths
        for k, v in out[name].items():
            out[name][k] = _normalise_path(v) if v else ""
    return out


class _Empty:
    @staticmethod
    def group(_):
        return ""


def _empty():
    return _Empty


# ---------------------------------------------------------------------------
# 3. Filesystem walk
# ---------------------------------------------------------------------------

_IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ddt", ".dds", ".tga", ".webp"}


def walk_files(root: Path) -> list[str]:
    """Return repo-relative POSIX paths for every image-ish file under root."""
    if not root.exists():
        return []
    out: list[str] = []
    base = root
    for dirpath, _, files in os.walk(base):
        for name in files:
            if Path(name).suffix.lower() in _IMG_EXTS:
                fp = Path(dirpath) / name
                try:
                    rel = fp.relative_to(REPO)
                    out.append(rel.as_posix())
                except ValueError:
                    out.append(fp.as_posix())
    out.sort()
    return out


# ---------------------------------------------------------------------------
# 4. Civ ↔ asset linking
# ---------------------------------------------------------------------------

# A short heuristic stem table for HTML-section-name → ANW civ-name.
# We try multiple fallbacks before giving up.
_SECTION_OVERRIDES = {
    "Argentina": "ANWArgentines",
    "Argentines": "ANWArgentines",
    "Aztec": "ANWAztecs",
    "Aztecs": "ANWAztecs",
    "Barbary": "ANWBarbary",
    "Barbary States": "ANWBarbary",
    "Brazil": "ANWBrazil",
    "Brazilian": "ANWBrazil",
    "British": "ANWBritish",
    "Canadian": "ANWCanadians",
    "Canadians": "ANWCanadians",
    "Chilean": "ANWChileans",
    "Chileans": "ANWChileans",
    "Chinese": "ANWChinese",
    "Columbian": "ANWColumbians",
    "Columbians": "ANWColumbians",
    "Colombians": "ANWColumbians",
    "Dutch": "ANWDutch",
    "Egyptian": "ANWEgyptians",
    "Egyptians": "ANWEgyptians",
    "Ethiopian": "ANWEthiopians",
    "Ethiopians": "ANWEthiopians",
    "Finnish": "ANWFinnish",
    "French": "ANWFrench",
    "Germans": "ANWGermans",
    "German": "ANWGermans",
    "Haitian": "ANWHaitians",
    "Haitians": "ANWHaitians",
    "Haudenosaunee": "ANWHaudenosaunee",
    "Hausa": "ANWHausa",
    "Hungarian": "ANWHungarians",
    "Hungarians": "ANWHungarians",
    "Inca": "ANWInca",
    "Indian": "ANWIndians",
    "Indians": "ANWIndians",
    "Indonesian": "ANWIndonesians",
    "Indonesians": "ANWIndonesians",
    "Italian": "ANWItalians",
    "Italians": "ANWItalians",
    "Japanese": "ANWJapanese",
    "Lakota": "ANWLakota",
    "Maltese": "ANWMaltese",
    "Mayan": "ANWMayans",
    "Mayans": "ANWMayans",
    "Mexican": "ANWMexicans",
    "Mexicans": "ANWMexicans",
    "Napoleonic France": "ANWNapoleonicFrance",
    "Ottoman": "ANWOttomans",
    "Ottomans": "ANWOttomans",
    "Peruvian": "ANWPeruvians",
    "Peruvians": "ANWPeruvians",
    "Portuguese": "ANWPortuguese",
    "Revolutionary France": "ANWRevFrance",
    "Rev France": "ANWRevFrance",
    "Romanian": "ANWRomanians",
    "Romanians": "ANWRomanians",
    "Russian": "ANWRussians",
    "Russians": "ANWRussians",
    "South African": "ANWSouthAfricans",
    "South Africans": "ANWSouthAfricans",
    "Spanish": "ANWSpanish",
    "Swedes": "ANWSwedes",
    "Swedish": "ANWSwedes",
    "Texian": "ANWTexians",
    "Texians": "ANWTexians",
    "USA": "ANWUSA",
    "United States": "ANWUSA",
}


def section_to_civ(section: str | None) -> str | None:
    if not section:
        return None
    s = section.strip()
    if s in _SECTION_OVERRIDES:
        return _SECTION_OVERRIDES[s]
    # Last-resort: collapse whitespace and try again.
    s2 = re.sub(r"\s+", " ", s).strip()
    if s2 in _SECTION_OVERRIDES:
        return _SECTION_OVERRIDES[s2]
    return None


# ---------------------------------------------------------------------------
# 5. Build inventory
# ---------------------------------------------------------------------------

def build_inventory(
    repo: Path = REPO,
    deployed: Path | None = DEFAULT_DEPLOYED,
) -> dict:
    html_text = (repo / "a_new_world.html").read_text(encoding="utf-8")
    civmods_text = (repo / "data" / "civmods.xml").read_text(encoding="utf-8")

    imgs = parse_html_imgs(html_text)
    civmods = parse_civmods(civmods_text)
    art_files = walk_files(repo / "art")
    res_files = walk_files(repo / "resources" / "images")

    # Civ-keyed accumulation
    civs: dict[str, dict] = {}
    # Track which HTML img URLs we've claimed, to compute "ui_elements" bucket
    claimed_html: set[str] = set()

    # Seed with civmods entries (they're authoritative for what the engine reads).
    for civ_name, fields in civmods.items():
        civs[civ_name] = {
            "civ": civ_name,
            "html_flag": "",
            "html_portrait": "",
            "html_extra_imgs": [],
            "civmods_portrait_wpf": fields["portrait_wpf"],
            "civmods_flag_wpf": fields["flag_wpf"],
            "civmods_postgame_wpf": fields["postgame_wpf"],
            "civmods_flag_texture": fields["flag_texture"],
            "civmods_portrait_obj": fields["portrait_obj"],
            "art_portrait_hires": "",
            "html_section": None,
            # Track 2 art-surface enumeration (populated after leaders_index built)
            "art_surfaces": {},
        }

    # Link HTML images to civ sections.
    for entry in imgs:
        civ = section_to_civ(entry["civ_section"])
        if not civ:
            continue
        rec = civs.setdefault(civ, {
            "civ": civ,
            "html_flag": "",
            "html_portrait": "",
            "html_extra_imgs": [],
            "civmods_portrait_wpf": "",
            "civmods_flag_wpf": "",
            "civmods_postgame_wpf": "",
            "civmods_flag_texture": "",
            "civmods_portrait_obj": "",
            "art_portrait_hires": "",
            "html_section": entry["civ_section"],
        })
        rec["html_section"] = entry["civ_section"]
        cls = entry.get("class", "")
        src = entry["src"]
        if "flag-img" in cls and not rec["html_flag"]:
            rec["html_flag"] = src
        elif "portrait-img" in cls and not rec["html_portrait"]:
            rec["html_portrait"] = src
        else:
            rec["html_extra_imgs"].append(src)
        claimed_html.add(src)

    # Find the hi-res mod portrait by scanning art/ui/leaders/.
    leaders_dir = repo / "art" / "ui" / "leaders"
    leaders_index: dict[str, str] = {}
    if leaders_dir.exists():
        for f in leaders_dir.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
                leaders_index[f.stem.lower()] = (f.relative_to(repo)).as_posix()

    def _stem_from_civmods_portrait(wpf: str) -> str | None:
        """`resources/images/icons/singleplayer/cpai_avatar_argentines_san_martin.png`
        → `san_martin` if that exists in art/ui/leaders, else None."""
        if not wpf:
            return None
        bn = Path(wpf).stem  # cpai_avatar_argentines_san_martin
        bn = bn.replace("cpai_avatar_", "")
        # Try progressively shorter trailing tokens until we hit a known file.
        parts = bn.split("_")
        for i in range(len(parts)):
            cand = "_".join(parts[i:])
            if cand in leaders_index:
                return cand
        return None

    for civ_name, rec in civs.items():
        stem = _stem_from_civmods_portrait(rec.get("civmods_portrait_wpf", ""))
        if stem:
            rec["art_portrait_hires"] = leaders_index[stem]

    # ------------------------------------------------------------------
    # Track 2: enumerate every art-surface field per civ + on-disk check.
    # ------------------------------------------------------------------
    def _disk_check(rel: str) -> tuple[bool, str]:
        if not rel:
            return False, ""
        # Strip leading ./ and treat as repo-relative POSIX path.
        rp = _normalise_path(rel)
        fp = repo / rp
        return (fp.exists() and fp.is_file()), rp

    def _leader_hires_for(civmods_fields: dict[str, str]) -> tuple[str, bool]:
        """Resolve art/ui/leaders/<leader>.{png,jpg} from the civmods
        portrait-wpf filename. Returns (relpath_or_empty, on_disk)."""
        wpf = civmods_fields.get("portrait_wpf", "") or civmods_fields.get(
            "small_portrait_wpf", ""
        )
        if not wpf:
            return "", False
        bn = Path(wpf).stem.replace("cpai_avatar_", "")
        parts = bn.split("_")
        for i in range(len(parts)):
            cand = "_".join(parts[i:])
            if cand in leaders_index:
                rel = leaders_index[cand]
                return rel, (repo / rel).exists()
        return "", False

    custom_portraits_missing: list[str] = []
    civmods_art_missing: list[tuple[str, str, str]] = []

    # Mapping: art_surface_key -> (civmods_field_key, label for missing list)
    _surface_keys = [
        ("diplomacy_portrait_wpf",  "small_portrait_wpf"),
        ("scoreboard_portrait_wpf", "small_portrait_wpf"),
        ("postgame_flag_wpf",       "postgame_wpf"),
        ("homecity_preview_wpf",    "portrait_wpf"),
        ("homecity_flag_icon_wpf",  "flag_wpf"),
        ("homecity_flag_button_wpf", "flag_button_wpf"),
    ]

    for civ_name, rec in civs.items():
        # art_surfaces section is only meaningful for ANW civs; skip stock
        # civilizations and campaign (SPC*) blocks that civmods.xml inherits.
        if not civ_name.startswith("ANW"):
            rec["art_surfaces"] = {}
            continue
        fields = civmods.get(civ_name, {})
        surfaces: dict[str, dict] = {}
        for surface_key, cm_key in _surface_keys:
            raw = fields.get(cm_key, "")
            on_disk, path = _disk_check(raw)
            surfaces[surface_key] = {"path": path, "_on_disk": bool(on_disk)}
            if raw and not on_disk:
                civmods_art_missing.append((civ_name, surface_key, path))

        # homecity_filename — XML path under data/
        hc_fname = fields.get("homecity_filename", "")
        hc_path = ""
        hc_on_disk = False
        if hc_fname:
            hc_path = f"data/{Path(hc_fname).name}"
            hc_on_disk = (repo / hc_path).exists()
            if not hc_on_disk:
                civmods_art_missing.append((civ_name, "homecity_filename", hc_path))
        surfaces["homecity_filename"] = {"path": hc_path, "_on_disk": hc_on_disk}

        # ---- NEW: homecity_visual_scene ---------------------------------
        # Parse the homecity XML to extract the top-level <visual> element
        # (e.g. "french\french_homecity.xml") which is the scene file
        # referenced for the home-city walking animation.  This file lives
        # in the engine's base data tree, not the mod repo, so _on_disk will
        # usually be False — we record the raw reference for human review.
        hc_visual_raw = ""
        hc_xml_text = ""
        if hc_path and hc_on_disk:
            try:
                hc_xml_text = (repo / hc_path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
        if not hc_xml_text and hc_fname:
            # Convention fallback: stem of filename → data/anwhomecity<stem>.xml
            stem = Path(hc_fname).stem.lower()
            cand = repo / "data" / f"{stem}.xml"
            if cand.exists():
                try:
                    hc_xml_text = cand.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
        if not hc_xml_text:
            # Last fallback: conventional name from civ token
            civ_stem = civ_name.replace("ANW", "").lower()
            cand2 = repo / "data" / f"anwhomecity{civ_stem}.xml"
            if cand2.exists():
                try:
                    hc_xml_text = cand2.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
        if hc_xml_text:
            vm = _HC_VISUAL_RE.search(hc_xml_text)
            if vm:
                hc_visual_raw = vm.group(1).strip().replace("\\", "/")
        # The scene file lives in the engine art tree (not the mod repo), so
        # resolve it as "art/<visual_raw>" or just store as a slug.
        hc_visual_mod_path = ""
        hc_visual_on_disk = False
        if hc_visual_raw:
            # Try art/<scene> in the mod repo
            cand_art = repo / "art" / hc_visual_raw
            if cand_art.exists():
                hc_visual_mod_path = f"art/{hc_visual_raw}"
                hc_visual_on_disk = True
            else:
                # Store the raw slug for reference even if not in mod repo
                hc_visual_mod_path = hc_visual_raw
        surfaces["homecity_visual_scene"] = {
            "path": hc_visual_mod_path,
            "_on_disk": hc_visual_on_disk,
            "_raw_engine_ref": hc_visual_raw,
        }

        # ---- NEW: art/ui/{diplomacy,scoreboard,postgame} directory walk ----
        # Walk the conventional art/ui/<surface>/ subdirectories for any
        # per-civ override assets.  These dirs may not exist in the current
        # repo; the result is null when absent (not a failure — engine falls
        # back to base civs).
        def _art_ui_walk(subdir: Path, token: str) -> str | None:
            """Return first file whose stem contains the civ name fragment."""
            if not (repo / subdir).exists():
                return None
            frag = token.replace("ANW", "").lower()
            for f in sorted((repo / subdir).iterdir()):
                if f.suffix.lower() in _IMG_EXTS and frag in f.stem.lower():
                    return (f.relative_to(repo)).as_posix()
            return None

        for surf_key, art_subdir in [
            ("diplomacy_panel_art", _ART_UI_DIPLOMACY),
            ("scoreboard_portrait_art", _ART_UI_SCOREBOARD),
            ("postgame_flag_art", _ART_UI_POSTGAME),
        ]:
            found = _art_ui_walk(art_subdir, civ_name)
            surfaces[surf_key] = {
                "path": found or "",
                "_on_disk": found is not None,
                "_art_dir": str(art_subdir),
            }

        # ---- NEW: captured_screenshots ------------------------------------
        # Per-civ screenshots written by anw_visual_capture.py live at
        # artifacts/validation/visual_art/<civ>/0N_*.png.  We record their
        # repo-relative paths and _on_disk status so the contact sheet can
        # link directly to them.
        _CAPTURE_MAP = [
            ("diplomacy_panel",                    "01_diplomacy.png"),
            ("scoreboard_portrait",                "02_scoreboard.png"),
            ("home_city_walking_animation_thumbnail", "03_homecity.png"),
            ("ally_homecity",                      "04_ally_homecity.png"),
            ("postgame_flag",                      "05_postgame.png"),
        ]
        visual_art_dir = repo / "artifacts" / "validation" / "visual_art"
        captures: dict[str, dict] = {}
        for cap_key, cap_fname in _CAPTURE_MAP:
            cap_path = visual_art_dir / civ_name / cap_fname
            cap_rel = (cap_path.relative_to(repo)).as_posix()
            captures[cap_key] = {
                "path": cap_rel,
                "_on_disk": cap_path.exists() and cap_path.stat().st_size > 0,
            }
        rec["captured_screenshots"] = captures

        # custom_leader_portrait_hires — art/ui/leaders/<leader>.{png,jpg}
        hires_rel, hires_on_disk = _leader_hires_for(fields)
        surfaces["custom_leader_portrait_hires"] = {
            "path": hires_rel,
            "_on_disk": bool(hires_on_disk),
        }
        if not hires_rel or not hires_on_disk:
            custom_portraits_missing.append(civ_name)

        # Also keep the legacy single-string flat fields for back-compat,
        # and expose the same hi-res path on the top-level record.
        if hires_rel and not rec.get("art_portrait_hires"):
            rec["art_portrait_hires"] = hires_rel

        rec["art_surfaces"] = surfaces

        # ---- NEW v1.0 top-level flat fields ---------------------------------
        # diplomacy_portrait / scoreboard_portrait / postgame_portrait:
        # The engine uses <SmallPortraitTextureWPF> for both the diplomacy
        # panel and the scoreboard in-game portrait.  The post-game results
        # screen uses the same texture.  All three fields therefore point to
        # the same source asset; they are documented separately so callers
        # (contact-sheet, ally-deck verifier) can reference each surface by
        # its logical name without looking up the art_surfaces sub-block.
        small_wpf = _normalise_path(fields.get("small_portrait_wpf", ""))
        rec["diplomacy_portrait"] = small_wpf      # diplomacy panel portrait
        rec["scoreboard_portrait"] = small_wpf     # scoreboard portrait (same source)
        rec["postgame_portrait"] = small_wpf       # post-game results portrait (same source)

        # homecity_idle_animation_files: up to 5 representative visual-XML
        # paths from <file>…</file> blocks in the homecity XML.  These paths
        # reference engine art/animation XMLs; the actual GR2/anim data lives
        # in the engine's data.bar archive and is not in the mod repo.
        hc_xml_text_for_files = _read_hc_xml(
            civ_name,
            (surfaces.get("homecity_filename") or {}).get("path", ""),
            repo,
        )
        rec["homecity_idle_animation_files"] = _homecity_idle_files(hc_xml_text_for_files)

        # primary_deck_name: the <name> of the first <deck> block in the
        # homecity XML — this is the default/starting deck for the civ.
        rec["primary_deck_name"] = _primary_deck_name(hc_xml_text_for_files)

    # Building & unit inventory: every file under art/ that we did NOT pin to a civ.
    pinned_art_paths: set[str] = set()
    for rec in civs.values():
        if rec.get("art_portrait_hires"):
            pinned_art_paths.add(rec["art_portrait_hires"])

    buildings: list[str] = []
    units: list[str] = []
    other_art: list[str] = []
    for ap in art_files:
        if ap in pinned_art_paths:
            continue
        if ap.startswith("art/buildings/"):
            buildings.append(ap)
        elif ap.startswith("art/units/"):
            units.append(ap)
        else:
            other_art.append(ap)

    # ui_elements: HTML images not claimed by any civ (banners, generic icons,
    # color-swatch demos, etc).
    ui_elements: list[str] = sorted({e["src"] for e in imgs if e["src"] not in claimed_html})

    # Deployed mod files (just count + path for sanity)
    deployed_info: dict = {"present": False, "art_files": [], "resources_files": []}
    if deployed and deployed.exists():
        deployed_info["present"] = True
        deployed_info["art_files"] = walk_files(deployed / "art") if (deployed / "art").exists() else []
        deployed_info["resources_files"] = walk_files(deployed / "resources" / "images") if (deployed / "resources" / "images").exists() else []
        # Strip the deployed prefix so paths look uniform — we keep the full
        # absolute path under "deployed_root" instead.
        deployed_info["deployed_root"] = str(deployed)

    return {
        "_meta": {
            "repo": str(repo),
            "deployed_root": str(deployed) if deployed else None,
            "html_img_total": len(imgs),
            "html_img_with_civ": sum(1 for e in imgs if section_to_civ(e["civ_section"])),
            "art_files_total": len(art_files),
            "resources_files_total": len(res_files),
            "civs_seen": sorted(civs.keys()),
        },
        "art_surface_summary": {
            "custom_portraits_total": sum(1 for c in civs if c.startswith("ANW")),
            "custom_portraits_missing": sorted(
                {c for c in custom_portraits_missing if c.startswith("ANW")}
            ),
            "civmods_art_missing": [
                {"civ": c, "field": f, "path": p}
                for c, f, p in civmods_art_missing
                if c.startswith("ANW")
            ],
        },
        "civs": dict(sorted(civs.items())),
        "buildings": buildings,
        "units": units,
        "ui_elements": ui_elements,
        "other_art": other_art,
        "all_resources": res_files,
        "all_art": art_files,
        "deployed": deployed_info,
    }


# ---------------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------------

def _cli(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build ANW art inventory.")
    p.add_argument("--stdout", action="store_true", help="JSON to stdout instead of writing file")
    p.add_argument("--summary", action="store_true", help="One-line stats, no JSON write")
    p.add_argument("--deployed", default=str(DEFAULT_DEPLOYED), help="Deployed mod dir")
    args = p.parse_args(list(argv) if argv is not None else None)

    deployed = Path(args.deployed) if args.deployed else None
    inv = build_inventory(REPO, deployed)
    meta = inv["_meta"]

    if args.summary:
        print(
            f"civs={len(inv['civs'])}  buildings={len(inv['buildings'])}  "
            f"units={len(inv['units'])}  ui_elements={len(inv['ui_elements'])}  "
            f"other_art={len(inv['other_art'])}  "
            f"html_imgs={meta['html_img_total']} (linked={meta['html_img_with_civ']})  "
            f"art_files={meta['art_files_total']}  resources_files={meta['resources_files_total']}"
        )
        return 0

    if args.stdout:
        json.dump(inv, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        INVENTORY_OUT.write_text(json.dumps(inv, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {INVENTORY_OUT.relative_to(REPO)}  ({INVENTORY_OUT.stat().st_size} bytes)")
        print(
            f"  civs={len(inv['civs'])}  html_imgs={meta['html_img_total']} "
            f"(linked={meta['html_img_with_civ']})  art={meta['art_files_total']}  "
            f"resources={meta['resources_files_total']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
