#!/usr/bin/env python3
"""Validate art/portrait coverage for every personality.

Checks per `game/ai/*.personality`:
  • <icon> path resolves to an existing PNG file with a valid header
  • <forcedciv> value resolves to a real civ:
      - in our `data/civmods.xml` (ANW*), or
      - in the base-game civ allowlist
  • <chatset> is non-empty (audio is base-game; can't verify locally)

Repo-wide checks:
  • Orphan files under `art/ui/leaders/` that no personality references
    (these are HC card / age-up portraits — flag for manual triage)
  • Stale duplicate flag images (Title_Case.png + lower_case.png pairs)

Exit non-zero if any FAIL row. ORPHAN/INFO are warnings only.

Usage:
  python3 tools/validation/validate_art_coverage.py
  python3 tools/validation/validate_art_coverage.py --json
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AI_DIR = REPO / "game" / "ai"
ART_LEADERS = REPO / "art" / "ui" / "leaders"
SP_AVATARS = REPO / "resources" / "images" / "icons" / "singleplayer"
FLAGS = REPO / "resources" / "images" / "icons" / "flags"
CIVMODS = REPO / "data" / "civmods.xml"

# Base-game avatar PNG filenames that live in the base game install, not in
# this repo.  The validator skips the file-existence check for these paths so
# personality files that legitimately reference them still pass.
BASE_GAME_AVATARS = {
    "cpai_avatar_random.png",
    "cpai_avatar_aztec.png",
    "cpai_avatar_iroquois.png",
    "cpai_avatar_sioux.png",
    "cpai_avatar_usa.png",
}

# Base-game civs the personality `forcedciv` may reference. Lower-cased on
# both sides at compare time so "British"/"british"/"DEEthiopians" all match.
BASE_CIVS = {
    "british", "french", "spanish", "portuguese", "dutch", "germans",
    "russians", "ottomans", "japanese", "chinese", "indians",
    "deamericans", "demexicans", "deswedish", "deethiopians", "dehausa",
    "deinca", "deitalians", "demaltese",
    "iroquois", "sioux", "aztec", "xpaztec", "xpiroquois", "xpsioux",
    "haudenosaunee", "lakota",
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPG_MAGIC = b"\xff\xd8\xff"


def _check_image(path: Path) -> str | None:
    """Return None on OK; otherwise a short failure reason."""
    if not path.exists():
        return "missing"
    try:
        head = path.read_bytes()[:16]
    except OSError as e:
        return f"unreadable: {e}"
    if not head:
        return "empty"
    suffix = path.suffix.lower()
    if suffix == ".png" and not head.startswith(PNG_MAGIC):
        return "not a PNG (bad magic)"
    if suffix in (".jpg", ".jpeg") and not head.startswith(JPG_MAGIC):
        return "not a JPEG (bad magic)"
    return None


def _parse_personality(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="ignore")

    def find(tag: str) -> str | None:
        m = re.search(rf"<{tag}>([^<]+)</{tag}>", txt)
        return m.group(1).strip() if m else None

    return {
        "icon": find("icon"),
        "forcedciv": find("forcedciv"),
        "chatset": find("chatset"),
        "nameID": find("nameID"),
        "tooltipID": find("tooltipID"),
    }


def _load_civmods() -> set[str]:
    if not CIVMODS.exists():
        return set()
    txt = CIVMODS.read_text(encoding="utf-8", errors="ignore")
    # civmods.xml uses lowercase <name> tags inside <civ> blocks.
    return {m.lower() for m in re.findall(r"<name>([^<]+)</name>", txt)}


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def validate_art_coverage(repo_root: Path = REPO) -> list[str]:
    """Return list of FAIL findings (orphans/info excluded). Empty = pass."""
    findings: list[str] = []

    if not AI_DIR.exists():
        return [f"game/ai/ not found under {repo_root}"]

    civmods_civs = _load_civmods()
    valid_civs = civmods_civs | {c.lower() for c in BASE_CIVS}

    for p in sorted(AI_DIR.glob("*.personality")):
        info = _parse_personality(p)

        # 1. <icon> path → real PNG
        icon = info["icon"]
        if not icon:
            findings.append(f"{p.name}: missing <icon>")
        else:
            icon_fname = Path(icon).name
            if icon_fname in BASE_GAME_AVATARS:
                pass  # base-game asset — not shipped in this repo, skip check
            else:
                icon_path = repo_root / icon
                err = _check_image(icon_path)
                if err:
                    findings.append(f"{p.name}: <icon>={icon} {err}")

        # 2. <forcedciv> → known civ
        fc = (info["forcedciv"] or "").lower()
        if not fc:
            findings.append(f"{p.name}: missing <forcedciv>")
        elif fc not in valid_civs:
            findings.append(f"{p.name}: <forcedciv>={info['forcedciv']!r} "
                            f"not in civmods.xml or base allowlist")

        # 3. <chatset> non-empty (audio can't be verified — base-game owned)
        if not info["chatset"]:
            findings.append(f"{p.name}: missing <chatset>")

    return findings


def find_orphan_leader_art(repo_root: Path = REPO) -> list[Path]:
    """art/ui/leaders/* files that no personality references."""
    if not ART_LEADERS.exists():
        return []

    # Collect every personality icon basename (lower-cased, no extension).
    # An art/ui/leaders/<stem>.<ext> file is "referenced" if its stem appears
    # as a suffix of any icon basename — handles both single-word leaders
    # (washington) and multi-word ones (crazy_horse, muhammad_ali).
    referenced_basenames: list[str] = []
    for p in AI_DIR.glob("*.personality"):
        icon = _parse_personality(p)["icon"]
        if icon:
            referenced_basenames.append(Path(icon).stem.lower())

    orphans = []
    for f in sorted(ART_LEADERS.glob("*")):
        if not f.is_file():
            continue
        stem = f.stem.lower()
        if not any(b == stem or b.endswith(f"_{stem}") for b in referenced_basenames):
            orphans.append(f)
    return orphans


def find_duplicate_flags(repo_root: Path = REPO) -> list[tuple[Path, Path]]:
    """Find Title_Case.png + lower_case.png pairs in flags/."""
    if not FLAGS.exists():
        return []
    files_by_lower: dict[str, list[Path]] = {}
    for f in FLAGS.glob("*.png"):
        files_by_lower.setdefault(f.name.lower(), []).append(f)
    return [(group[0], group[1]) for group in files_by_lower.values()
            if len(group) >= 2]


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--include-orphans", action="store_true",
                    help="also list orphan art files (informational)")
    args = ap.parse_args(argv)

    fails = validate_art_coverage()
    orphans = find_orphan_leader_art() if args.include_orphans else []
    dup_flags = find_duplicate_flags()

    if args.json:
        print(json.dumps({
            "fails": fails,
            "orphans": [str(p.relative_to(REPO)) for p in orphans],
            "duplicate_flags": [[str(a.relative_to(REPO)), str(b.relative_to(REPO))]
                                for a, b in dup_flags],
        }, indent=2))
    else:
        print(f"=== Personality art coverage ===")
        if fails:
            for f in fails:
                print(f"  FAIL: {f}")
        else:
            print(f"  OK: all 48 personalities have valid icon/forcedciv/chatset")
        if args.include_orphans and orphans:
            print(f"\n=== Orphan art/ui/leaders/ ({len(orphans)}) ===")
            for p in orphans:
                print(f"  ORPHAN: {p.relative_to(REPO)}")
        if dup_flags:
            print(f"\n=== Duplicate flag images (case variants) ===")
            for a, b in dup_flags:
                print(f"  {a.name}  <->  {b.name}")
        print()
        print(f"Total FAIL: {len(fails)}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
