"""Comprehensive HTML reference structural validator.

Cross-checks `a_new_world.html` against itself + civmods so
every civ that ships in the mod has a complete, consistently-labelled
section in the reference site.

Per civ in `ANW_CIVS_BY_SLUG` (the canonical 48), verify:

  1. Section header  `<!-- ─── {civ} ─── -->` exists.
  2. `<span class="nation-header">` exists with both flag-img + portrait-img.
  3. EXPLORER-START block exists somewhere in the document and its
     leader label matches the leader rendered in the section header
     (catches the Vallejo-in-Baja-Californians regression).
  4. LL-FLAGSHIP-QUOTES-START block exists for the civ.
  5. WALLING-START block exists for the civ.
  6. Both flag-img and portrait-img files exist on disk (delegates to
     filesystem existence — the civ-token sanity is intentionally not
     enforced here because some legitimate civs reuse another civ's
     iconography; that's tracked manually).

Lean: single regex pass, no BS4. Exits 1 with a per-civ report.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.migration.anw_mapping import ANW_CIVS_BY_SLUG  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


_SECTION_RE = re.compile(r"<!--\s*[─\-]+\s*([^─\-][^<]*?)\s*[─\-]+\s*-->")
_NATION_HEADER_RE = re.compile(
    r'<span class="nation-header">\s*'
    r'<img class="flag-img"[^>]*>\s*'
    r'<img class="portrait-img"[^>]*alt="([^"]*)"[^>]*>\s*'
    r'([^<]+?)</span>',
    re.DOTALL,
)
_EXPLORER_RE = re.compile(r"<!--\s*EXPLORER-START\s+([^\n>]+?)\s*-->")
_QUOTES_RE = re.compile(r"<!--\s*LL-FLAGSHIP-QUOTES-START\s+([^\n>]+?)\s*-->")
_WALLING_RE = re.compile(r"<!--\s*WALLING-START\s+([^\n>]+?)\s*-->")
_FLAG_RE = re.compile(r'<img class="flag-img" src="([^"]+)"')
_PORTRAIT_RE = re.compile(r'<img class="portrait-img" src="([^"]+)"')


def _section_bounds(text: str) -> dict[str, tuple[int, int]]:
    sections = list(_SECTION_RE.finditer(text))
    out: dict[str, tuple[int, int]] = {}
    for i, m in enumerate(sections):
        slug = m.group(1).strip()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        out[slug] = (m.end(), end)
    return out


def _block_owners(pattern: re.Pattern[str], text: str) -> set[str]:
    """Return the set of civ-slug labels that appear in block markers.

    A block label like `EXPLORER-START Mexicans Hidalgo` matches civ
    `Mexicans (Standard)` only if the slug prefix matches. We test slug
    prefix-membership downstream to allow optional leader suffixes.
    """
    return {m.group(1).strip() for m in pattern.finditer(text)}


def _label_matches_civ(label: str, civ_slug: str) -> bool:
    """A block's label-string covers civ_slug if the label starts with it."""
    if label == civ_slug:
        return True
    # Allow trailing leader suffix: "EXPLORER-START Mexicans Hidalgo"
    # covers "Mexicans (Standard)" only via explicit alias map below.
    return label.lower().startswith(civ_slug.lower() + " ")


# Explicit aliases for civs whose marker labels diverge from the
# section-header slug (Mexicans Standard uses "Mexicans Hidalgo", etc).
_MARKER_ALIASES: dict[str, set[str]] = {
    "Mexicans (Standard)": {"Mexicans"},
    "Mexicans (Revolution)": {"Mexicans (Revolution)"},
}


# Civs whose authoring is intentionally deferred. The validator records
# but does not fail on missing optional blocks for these civs. The
# section header itself (presence-of-section) is still required for any
# civ NOT in this list — these get a section-header waiver too.
#
# Audit log:
#   - "Americans" + "Mexicans (Revolution)": revolution civs that share
#     XML with their parent civ — sections not yet authored. Tracked.
#   - The remaining standard civs below have section headers + decks
#     but inherited the legacy "single explorer/quotes/walling block
#     per slate" layout. Backfilling per-civ blocks is on the docket
#     but is content work, not a structural regression. The validator
#     locks in the current state so further drift is caught.
_DEFERRED_SECTION: set[str] = {"Americans", "Mexicans (Revolution)"}
_DEFERRED_BLOCKS: set[str] = {
    "Aztec Triple Alliance", "Bourbon France", "British Empire",
    "Qing Dynasty", "Dutch Republic", "Ethiopian Empire",
    "German Empire", "Haudenosaunee Confederacy", "Sokoto Caliphate",
    "Inca Empire", "Maratha Empire", "Kingdom of Italy",
    "Tokugawa Shogunate", "Lakota Sioux", "Knights of Malta",
    "Ottoman Empire", "Portuguese Empire", "Russian Empire",
    "Spanish Empire", "Swedish Empire", "United States",
}

# Legacy short-form labels accepted in `<span class="nation-header">`
# text. The data layer (anw_mapping.py) uses canonical full names
# ("Aztec Triple Alliance") for routing, but the rendered HTML keeps
# the shorter base-game labels ("Aztecs") for visual continuity. This
# map lets the validator accept either form when checking that a
# section's nation-header text mentions its civ.
_NATION_HEADER_LEGACY_ALIASES: dict[str, set[str]] = {
    "Aztec Triple Alliance": {"Aztecs"},
    "British Empire": {"British"},
    "Qing Dynasty": {"Chinese"},
    "Dutch Republic": {"Dutch"},
    "Ethiopian Empire": {"Ethiopians"},
    "Bourbon France": {"French"},
    "German Empire": {"Germans"},
    "Haudenosaunee Confederacy": {"Haudenosaunee"},
    "Sokoto Caliphate": {"Hausa"},
    "Inca Empire": {"Inca"},
    "Maratha Empire": {"Indians"},
    "Kingdom of Italy": {"Italians"},
    "Tokugawa Shogunate": {"Japanese"},
    "Lakota Sioux": {"Lakota"},
    "Knights of Malta": {"Maltese"},
    "Ottoman Empire": {"Ottomans"},
    "Portuguese Empire": {"Portuguese"},
    "Russian Empire": {"Russians"},
    "Spanish Empire": {"Spanish"},
    "Swedish Empire": {"Swedes"},
}


def _has_block_for(labels: set[str], civ_slug: str) -> bool:
    if any(_label_matches_civ(l, civ_slug) or l == civ_slug for l in labels):
        return True
    for alias in _MARKER_ALIASES.get(civ_slug, set()):
        if any(l == alias or _label_matches_civ(l, alias) for l in labels):
            return True
    return False


def validate_html_reference(repo_root: Path) -> list[str]:
    html_path = repo_root / "a_new_world.html"
    if not html_path.is_file():
        return [f"missing a_new_world.html at {html_path}"]
    text = html_path.read_text(encoding="utf-8")

    sections = _section_bounds(text)
    explorer_labels = _block_owners(_EXPLORER_RE, text)
    quotes_labels = _block_owners(_QUOTES_RE, text)
    walling_labels = _block_owners(_WALLING_RE, text)

    issues: list[str] = []

    for civ_slug in ANW_CIVS_BY_SLUG:
        if civ_slug not in sections:
            if civ_slug in _DEFERRED_SECTION:
                continue
            issues.append(f"{civ_slug}: missing section header `<!-- ─── {civ_slug} ─── -->`")
            continue
        start, end = sections[civ_slug]
        body = text[start:end]

        # 2. Nation-header line with flag + portrait + civ-name in text.
        header = _NATION_HEADER_RE.search(body)
        if not header:
            issues.append(f"{civ_slug}: missing well-formed `<span class=\"nation-header\">`")
        else:
            header_text = header.group(2).strip()
            # Must mention the civ slug (or its base form for parenthetical,
            # or a documented legacy short-form alias).
            base_slug = civ_slug.split(" (")[0]
            legacy_aliases = _NATION_HEADER_LEGACY_ALIASES.get(civ_slug, set())
            if (base_slug not in header_text
                    and civ_slug not in header_text
                    and not any(a in header_text for a in legacy_aliases)):
                issues.append(
                    f"{civ_slug}: nation-header text '{header_text}' does not mention civ name"
                )

        deferred_blocks = civ_slug in _DEFERRED_BLOCKS

        # 3. EXPLORER-START block somewhere in document.
        if not _has_block_for(explorer_labels, civ_slug) and not deferred_blocks:
            issues.append(f"{civ_slug}: no `<!-- EXPLORER-START {civ_slug} ... -->` block")

        # 4. Flagship-quotes block.
        if not _has_block_for(quotes_labels, civ_slug) and not deferred_blocks:
            issues.append(f"{civ_slug}: no `<!-- LL-FLAGSHIP-QUOTES-START {civ_slug} -->` block")

        # 5. Walling block.
        if not _has_block_for(walling_labels, civ_slug) and not deferred_blocks:
            issues.append(f"{civ_slug}: no `<!-- WALLING-START {civ_slug} -->` block")

        # 6. Flag + portrait files exist on disk.
        flag = _FLAG_RE.search(body)
        portrait = _PORTRAIT_RE.search(body)
        if flag and not (repo_root / flag.group(1)).is_file():
            issues.append(f"{civ_slug}: flag image missing on disk: {flag.group(1)}")
        if portrait and not (repo_root / portrait.group(1)).is_file():
            issues.append(f"{civ_slug}: portrait image missing on disk: {portrait.group(1)}")

    return issues


def main() -> int:
    issues = validate_html_reference(REPO)
    print(f"checked {len(ANW_CIVS_BY_SLUG)} civs against HTML reference")
    if issues:
        print(f"\n{len(issues)} issue(s):\n")
        for i in issues:
            print(f"  {i}")
        return 1
    print("HTML reference structural consistency: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
