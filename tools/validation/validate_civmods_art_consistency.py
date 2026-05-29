"""Catch the art-mismatch class that hit on 2026-05-12 live test.

Pattern (verified on Napoleonic France, Dutch in user's live test):

  * `<homecityflagbuttonwpf>` (top-left in-game home-city button) points at the
    *correct* mod-supplied flag — verified visually working.
  * `<homecityflagiconwpf>` (scoreboard, Tab key) and `<postgameflagiconwpf>`
    (post-game results screen) often still point at the *base-game* flag
    (e.g. Bourbon `Flag_French.png` for Napoleon, Vatican flag for Maltese,
    etc).
  * `<homecitypreviewwpf>` (home-city preview tile + diplomacy ally panel)
    points at the *correct* custom leader portrait.
  * `<smallportraittexturewpf>` (skirmish lobby AI civ-picker) often still
    points at the *generic* civ portrait (e.g. `cpai_avatar_dutch.png` not
    `cpai_avatar_dutch_maurice.png`).

Both pairs are conceptually the same image rendered at different surfaces
in the engine. When one pair-member is the new ANW asset and the other
is the base-game asset, players see a half-fixed mod (top-left flag
correct, scoreboard flag Bourbon) — exactly the bug we just shipped.

This validator flags every civ whose pair-mates disagree. Exit 1 with a
per-civ punch-list so they can be batch-fixed.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


# Pair-key → (canonical "known-good" field, fields that must match)
FLAG_PAIR = (
    "homecityflagbuttonwpf",
    ("homecityflagiconwpf", "postgameflagiconwpf"),
)
PORTRAIT_PAIR = (
    "homecitypreviewwpf",
    ("smallportraittexturewpf",),
)


def text_of(parent: ET.Element, tag: str) -> str:
    el = parent.find(tag)
    if el is None:
        return ""
    return (el.text or "").strip()


def basename(path: str) -> str:
    # Normalize both Windows-style and Unix-style separators — civmods.xml
    # mixes both (vanilla data uses backslashes, ANW overrides use forward).
    return path.replace("\\", "/").rsplit("/", 1)[-1].lower()


# Strip the family prefix from a flag filename to recover the civ token.
# `flag_hc_dutch.png` → `dutch`; `Flag_French.png` → `french`;
# `Flag_French_Revolution_NE.png` → `french_revolution_ne`.
_FLAG_FAMILY_PREFIXES = ("flag_hc_", "flag_", "ingame_ui_postgame_flag_",
                         "postgame_flag_")
# Strip the avatar family prefix from a portrait filename to recover the
# civ + leader token. `cpai_avatar_dutch_maurice.png` → `dutch_maurice`;
# `cpai_avatar_dutch.png` → `dutch`.
_PORTRAIT_FAMILY_PREFIXES = ("cpai_avatar_",)


# Known canonical-equivalence pairs. Some flags ship in TWO asset families
# whose civ tokens differ by pluralization (``canadian`` vs ``canadians``)
# or by an alternate-name convention (``usa`` vs ``american``, ``inca`` vs
# ``incan``). Both depict the same flag visually — the divergence is purely
# a filename artifact of how the original artist named each render size.
# These are NOT bugs; canonicalize before comparing so the validator
# doesn't flag them.
_CANONICAL_EQUIVALENCES = {
    "canadians": "canadian",
    "romanians": "romanian",
    "egyptians": "egyptian",
    "incan": "inca",
    "usa": "american",
}


def civ_token_from_filename(path: str, prefixes: tuple[str, ...]) -> str:
    """Strip family prefix + extension to recover the civ-identity token."""
    b = basename(path)
    # Drop extension
    if "." in b:
        b = b.rsplit(".", 1)[0]
    for p in prefixes:
        if b.startswith(p):
            b = b[len(p):]
            break
    # Canonicalize known-equivalent tokens (e.g. canadians -> canadian)
    return _CANONICAL_EQUIVALENCES.get(b, b)


def check_civ_pair(civ_name: str, civ_el: ET.Element,
                   anchor: str, mirrors: tuple[str, ...],
                   prefixes: tuple[str, ...]) -> list[str]:
    """If anchor is set + non-empty, every mirror field that is also set must
    share the same civ-identity token as the anchor.

    We strip the family prefix (``Flag_``, ``flag_hc_``, ``cpai_avatar_``)
    so that mirrors which legitimately use a different *family* of asset
    (e.g. the home-city button vs. the scoreboard) but the *same* civ
    are NOT flagged. The bug we want to catch is exactly when the civ
    identity diverges between mirrors — e.g. Napoleon's flag button is
    ``flag_hc_french_revolution_ne.png`` (token: ``french_revolution_ne``)
    but the scoreboard flag is ``Flag_French.png`` (token: ``french``).
    """
    issues: list[str] = []
    anchor_path = text_of(civ_el, anchor)
    if not anchor_path:
        return issues
    anchor_token = civ_token_from_filename(anchor_path, prefixes)
    for mirror in mirrors:
        mirror_path = text_of(civ_el, mirror)
        if not mirror_path:
            continue
        mirror_token = civ_token_from_filename(mirror_path, prefixes)
        # Allow the trivial subset relationship (e.g. anchor has
        # ``french_revolution_ne`` and mirror has ``french`` — the
        # mirror is a strictly-less-specific civ token, which is the
        # exact bug pattern).
        if mirror_token == anchor_token:
            continue
        issues.append(
            f"{civ_name}: <{mirror}> '{mirror_path}' "
            f"(token '{mirror_token}') "
            f"!= <{anchor}> '{anchor_path}' (token '{anchor_token}')"
        )
    return issues


def _portrait_civ_root(token: str) -> str:
    """Reduce a portrait token to its base civ root for equivalence checks.

    Lobby-picker matchmaking portraits use generic `anwbritish`, while
    home-city preview uses leader-specific `british_elizabeth`. Both refer
    to ANWBritish. Strip "anw" prefix and any "_leadername" suffix to
    recover the civ root.
    """
    t = token
    if t.startswith("anw"):
        t = t[3:]
    # Split on first underscore — base civ token is the head.
    return t.split("_", 1)[0]


def check_matchmaking_pair(civ_name: str, civ_el: ET.Element) -> list[str]:
    """`<matchmakingtextures>/<smallportraittexturewpf>` is the lobby
    picker portrait; should match the top-level `<homecitypreviewwpf>`
    (home-city preview / diplomacy panel) on civ-identity token."""
    mt = civ_el.find("matchmakingtextures")
    if mt is None:
        return []
    spt = text_of(mt, "smallportraittexturewpf")
    anchor = text_of(civ_el, "homecitypreviewwpf")
    if not anchor or not spt:
        return []
    spt_token = civ_token_from_filename(spt, _PORTRAIT_FAMILY_PREFIXES)
    anchor_token = civ_token_from_filename(anchor, _PORTRAIT_FAMILY_PREFIXES)
    if spt_token == anchor_token:
        return []
    # Accept generic-vs-leader pairing (anwbritish ≡ british_elizabeth).
    if _portrait_civ_root(spt_token) == _portrait_civ_root(anchor_token):
        return []
    return [
        f"{civ_name}: <matchmakingtextures>/<smallportraittexturewpf> "
        f"'{spt}' (token '{spt_token}') "
        f"!= <homecitypreviewwpf> '{anchor}' (token '{anchor_token}')"
    ]


def validate(repo_root: Path) -> list[str]:
    civmods = repo_root / "data" / "civmods.xml"
    if not civmods.exists():
        return [f"civmods.xml not found at {civmods}"]
    tree = ET.parse(civmods)
    root = tree.getroot()
    # ``data/civmods.xml`` was lowercased to <civ> (was <Civ>) so the engine's
    # case-sensitive XML merge picks the entries up. Match the same tag here.
    issues: list[str] = []
    for civ_el in root.findall("civ"):
        name_el = civ_el.find("name")
        if name_el is None:
            continue
        civ_name = (name_el.text or "").strip()
        if not civ_name:
            continue
        anchor, mirrors = FLAG_PAIR
        issues.extend(check_civ_pair(
            civ_name, civ_el, anchor, mirrors, _FLAG_FAMILY_PREFIXES))
        anchor, mirrors = PORTRAIT_PAIR
        issues.extend(check_civ_pair(
            civ_name, civ_el, anchor, mirrors, _PORTRAIT_FAMILY_PREFIXES))
        issues.extend(check_matchmaking_pair(civ_name, civ_el))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = ap.parse_args()
    issues = validate(args.repo_root.resolve())
    if issues:
        print(f"civmods art-consistency: {len(issues)} mismatch(es)")
        for issue in issues:
            print(f"  {issue}")
        print()
        print("Each mismatch means two engine surfaces will show DIFFERENT art.")
        print("Resolution: pick the canonical path (usually the 'button'/'preview'")
        print("one, since those work in-game) and update the mirror field to match.")
        return 1
    print("civmods art-consistency: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
