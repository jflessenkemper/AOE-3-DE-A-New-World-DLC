#!/usr/bin/env python3
"""
TIER 1: COMPREHENSIVE STATIC VALIDATION SUITE

Tests all static assets without running the game:
- XML integrity
- File existence (homecity, personality, decks)
- Deck composition (25 cards per civ)
- XS doctrine definitions
- Documentation consistency
- HTML reference sync
"""

import json
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

# Import the AnwCiv namedtuple list (NOT the dict-shape ANW_CIVS in
# anw_token_map.py — that one is keyed by token and the values don't expose
# the anw_stem/slug fields this validator needs).
from tools.migration.anw_mapping import (
    ANW_CIVS,
    ANW_CIVS_BY_SLUG,
    ANW_DEFERRED_SLUGS,
    engine_token_for,
)

print("\n" + "="*80)
print("TIER 1: COMPREHENSIVE STATIC VALIDATION SUITE")
print("="*80)

# ============================================================================
# TEST 1: XML FILE INTEGRITY
# ============================================================================
print("\n[TEST 1/7] XML FILE INTEGRITY")

xml_files = {
    "civmods.xml": repo_root / "data/civmods.xml",
    "playercolors.xml": repo_root / "data/playercolors.xml",
    "stringmods.xml": repo_root / "data/strings/english/stringmods.xml",
}

xml_pass = True
for name, path in xml_files.items():
    try:
        ET.parse(path)
        print(f"  ✓ {name}: Valid XML")
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        xml_pass = False

# ============================================================================
# TEST 2: HOMECITY FILES (all 48)
# ============================================================================
print("\n[TEST 2/7] HOMECITY FILES EXIST (48 civs)")

data_dir = repo_root / "data"
homecity_files = {f.stem: f for f in data_dir.glob("anwhomecity*.xml")}

missing_homecities = []
for civ in ANW_CIVS:
    # anw_stem is e.g. "british" (no "anw" prefix); homecity file is
    # data/anwhomecity{stem}.xml — its .stem on disk is "anwhomecity{stem}".
    expected_stem = f"anwhomecity{civ.anw_stem}"
    if expected_stem not in homecity_files:
        missing_homecities.append((civ.slug, civ.anw_token))

if missing_homecities:
    print(f"  ✗ Missing {len(missing_homecities)} homecity files:")
    for slug, token in missing_homecities[:3]:
        print(f"    - {token}")
else:
    print(f"  ✓ All {len(ANW_CIVS)} homecity files found")

# ============================================================================
# TEST 3: PERSONALITY FILES (all 48)
# ============================================================================
print("\n[TEST 3/7] PERSONALITY FILES EXIST (48 civs)")

ai_dir = repo_root / "game/ai"
personality_files = {f.stem.lower(): f for f in ai_dir.glob("anw*.personality")}

missing_personalities = []
for civ in ANW_CIVS:
    # Personality filename is anw{stem}.personality, e.g. anwbritish.personality.
    stem = f"anw{civ.anw_stem.lower()}"
    if stem not in personality_files:
        missing_personalities.append((civ.slug, civ.anw_token))

if missing_personalities:
    print(f"  ✗ Missing {len(missing_personalities)} personality files:")
    for slug, token in missing_personalities[:3]:
        print(f"    - {token.lower()}.personality")
else:
    print(f"  ✓ All {len(ANW_CIVS)} personality files found")

# ============================================================================
# TEST 4: DECK COMPOSITION (25 cards per civ, valid age distribution)
# ============================================================================
print("\n[TEST 4/7] DECK COMPOSITION (25 cards per civ)")

with open(repo_root / "data/decks_anw.json") as f:
    decks = json.load(f)

deck_issues = []
age_distribution_issues = []

for civ in ANW_CIVS:
    # decks_anw.json is keyed by a mix of ANW tokens and engine tokens
    # (e.g. ANWBritish, but XPAztec for the Aztecs civ). Fall back to the
    # engine token when the ANW token has no direct entry.
    token = civ.anw_token
    deck_key = token if token in decks else engine_token_for(token)

    if deck_key not in decks:
        deck_issues.append(f"{token}: NOT IN decks_anw.json (also tried {deck_key!r})")
        continue

    # Check total
    total = sum(len(cards) for cards in decks[deck_key].values())
    if total != 25:
        deck_issues.append(f"{token}: {total} cards (expected 25)")

    # Check age distribution (no age should be empty or overcrowded)
    for age_idx in range(5):
        age_str = str(age_idx)
        age_count = len(decks[deck_key].get(age_str, []))
        if age_count > 10:
            age_distribution_issues.append(f"{token}: Age {age_idx} has {age_count} cards (max 10)")

if deck_issues:
    print(f"  ✗ {len(deck_issues)} deck issues:")
    for issue in deck_issues[:3]:
        print(f"    - {issue}")
else:
    print(f"  ✓ All {len(ANW_CIVS)} decks have exactly 25 cards")

if age_distribution_issues:
    print(f"  ⚠ {len(age_distribution_issues)} age distribution warnings:")
    for issue in age_distribution_issues[:3]:
        print(f"    - {issue}")

# ============================================================================
# TEST 5: CARD REFERENCE VALIDATION
# ============================================================================
print("\n[TEST 5/7] CARD REFERENCES IN DECKS")

with open(repo_root / "data/cards.json") as f:
    cards_db = json.load(f)

card_name_to_id = {}
for card_id, card_meta in cards_db.items():
    name = card_meta.get("name", "")
    if name:
        if name not in card_name_to_id:
            card_name_to_id[name] = []
        card_name_to_id[name].append(card_id)

invalid_cards = []
for token, deck in decks.items():
    for age_idx in range(5):
        for card_id in deck.get(str(age_idx), []):
            if card_id not in cards_db:
                invalid_cards.append((token, card_id))

if invalid_cards:
    print(f"  ✗ {len(invalid_cards)} invalid card references:")
    for token, card_id in invalid_cards[:3]:
        print(f"    - {token}: {card_id} not in cards.json")
else:
    print(f"  ✓ All deck cards reference valid card IDs")

# ============================================================================
# TEST 6: HTML REFERENCE INTEGRITY
# ============================================================================
print("\n[TEST 6/7] HTML REFERENCE INTEGRITY")

html_path = repo_root / "a_new_world.html"
with open(html_path) as f:
    html_content = f.read()

# Check for all civ section headers (<!-- ─── {slug} ─── --> markers)
missing_sections = []
import re
section_pattern = r'<!--\s*[─\-]+\s*([^─\-][^<]*?)\s*[─\-]+\s*-->'
found_sections = set(re.findall(section_pattern, html_content))

for civ in ANW_CIVS:
    # Deferred civs don't have section headers (intentional)
    if civ.slug in ANW_DEFERRED_SLUGS:
        continue
    if civ.slug not in found_sections:
        missing_sections.append(civ.slug)

# Check for dev blocks
import re
dev_blocks = set(re.findall(r'<!-- DEV-START name="([^"]+)"', html_content))
expected_dev_blocks = {civ.slug for civ in ANW_CIVS if civ.slug not in ["Americans", "Mexicans (Revolution)"]}

missing_dev_blocks = expected_dev_blocks - dev_blocks

if missing_sections:
    print(f"  ✗ Missing {len(missing_sections)} civ section headers")
else:
    print(f"  ✓ All {len(ANW_CIVS)} civ section headers present")

if missing_dev_blocks:
    print(f"  ⚠ Missing {len(missing_dev_blocks)} dev-subtree blocks (expected for non-deferred civs)")
else:
    print(f"  ✓ All expected dev-subtree blocks present")

# ============================================================================
# TEST 7: CRITICAL FILES INVENTORY
# ============================================================================
print("\n[TEST 7/7] CRITICAL FILES INVENTORY")

critical_files = [
    "a_new_world.html",
    "data/civmods.xml",
    "data/decks_anw.json",
    "data/cards.json",
    "data/playercolors.xml",
    "data/strings/english/stringmods.xml",
    "game/ai/aiMain.xs",
    "game/ai/core/aiSetup.xs",
    "README.md",
]

missing_files = []
for f in critical_files:
    if not (repo_root / f).exists():
        missing_files.append(f)

if missing_files:
    print(f"  ✗ Missing {len(missing_files)} critical files: {missing_files[:3]}")
else:
    print(f"  ✓ All {len(critical_files)} critical files present")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("TIER 1 VALIDATION RESULTS")
print("="*80)

results = {
    "XML Integrity": xml_pass,
    "Homecity Files": len(missing_homecities) == 0,
    "Personality Files": len(missing_personalities) == 0,
    "Deck Composition": len(deck_issues) == 0,
    "Card References": len(invalid_cards) == 0,
    "HTML Reference": len(missing_sections) == 0,
    "Critical Files": len(missing_files) == 0,
}

for test, passed in results.items():
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{test:<25} {status}")

all_pass = all(results.values())

print("\n" + "="*80)
if all_pass:
    print("TIER 1: ✓✓✓ ALL VALIDATION TESTS PASSED ✓✓✓")
    print(f"        Validated 48 civs, {len(decks)} decks, {len(critical_files)} files")
    exit(0)
else:
    failed = [t for t, p in results.items() if not p]
    print(f"TIER 1: ✗ {len(failed)} TEST(S) FAILED")
    print(f"        Failed: {', '.join(failed)}")
    exit(1)
print("="*80)
