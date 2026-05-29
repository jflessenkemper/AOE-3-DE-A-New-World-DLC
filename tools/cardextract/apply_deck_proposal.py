#!/usr/bin/env python3
"""
apply_deck_proposal.py

Applies data/decks_anw_proposal.json to data/decks_anw.json.

Only the 16 "dumped" ANW civs are modified. The 5 already-stratified civs
(ANWFinnish, ANWArgentines, ANWCanadians, ANWBarbary, ANWTexians) are left
untouched, as are all base-game civs.

Usage:
    python3 apply_deck_proposal.py [--dry-run] [--backup]

Flags:
    --dry-run   Print what would change but do not write any files.
    --backup    Before writing, copy decks_anw.json -> decks_anw.json.bak_before_proposal
"""
import argparse
import copy
import json
import os
import shutil
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MOD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECKS_FILE = os.path.join(MOD_ROOT, "data", "decks_anw.json")
PROPOSAL_FILE = os.path.join(MOD_ROOT, "data", "decks_anw_proposal.json")
BACKUP_FILE = os.path.join(MOD_ROOT, "data", "decks_anw.json.bak_before_proposal")

TARGET_CIVS = [
    "ANWBritish", "ANWDutch", "ANWFrench", "ANWGermans",
    "ANWHaitians", "ANWHungarians", "ANWMexicans", "ANWNapoleonicFrance",
    "ANWOttomans", "ANWPeruvians", "ANWPortuguese", "ANWRevFrance",
    "ANWRussians", "ANWSpanish", "ANWUSA",
]

PROTECTED_CIVS = {
    "ANWFinnish", "ANWArgentines", "ANWCanadians", "ANWBarbary", "ANWTexians",
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def apply_proposal(decks, proposal, dry_run=False):
    """
    For each target civ in proposal, replace the civ's deck in decks with
    the proposed slot distribution (card names only, dropping the confidence/rationale).

    Returns a modified copy of decks (does not mutate the input).
    """
    new_decks = copy.deepcopy(decks)
    changed = []
    errors = []

    for civ in TARGET_CIVS:
        if civ not in proposal:
            errors.append(f"  SKIP {civ}: not found in proposal JSON")
            continue
        if civ in PROTECTED_CIVS:
            errors.append(f"  SKIP {civ}: marked as protected (should not be in target list)")
            continue

        old_slots = decks.get(civ, {})
        old_cards = sorted(sum([v for v in old_slots.values()], []))

        # Build new slot dict: {slot_str: [card_name, ...]}
        new_slots = {}
        new_cards = []
        for slot_str, entries in proposal[civ].items():
            cards = [e["card"] for e in entries]
            if cards:
                new_slots[slot_str] = cards
                new_cards.extend(cards)
        new_cards_sorted = sorted(new_cards)

        # Validation
        if len(new_cards) != 25:
            errors.append(
                f"  WARN {civ}: proposal has {len(new_cards)} cards (expected 25); skipping"
            )
            continue

        if old_cards != new_cards_sorted:
            added = set(new_cards_sorted) - set(old_cards)
            removed = set(old_cards) - set(new_cards_sorted)
            if added or removed:
                errors.append(
                    f"  WARN {civ}: card set changed! "
                    f"added={sorted(added)}, removed={sorted(removed)}"
                )
                # Still apply, since proposal is authoritative
            else:
                changed.append(civ)
        else:
            changed.append(civ)

        if not dry_run:
            new_decks[civ] = new_slots

        # Print the distribution
        dist = {}
        for slot_str, cards in new_slots.items():
            dist[int(slot_str)] = len(cards)
        dist_str = "/".join(str(dist.get(i, 0)) for i in range(5))
        prefix = "[DRY-RUN] " if dry_run else ""
        print(f"  {prefix}{civ}: {dist_str}")

    if errors:
        print("\nWarnings:")
        for e in errors:
            print(e)

    return new_decks, changed


def main():
    parser = argparse.ArgumentParser(
        description="Apply decks_anw_proposal.json to decks_anw.json"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change but do not write files",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Back up decks_anw.json before writing",
    )
    args = parser.parse_args()

    # Load files
    if not os.path.exists(DECKS_FILE):
        print(f"ERROR: {DECKS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(PROPOSAL_FILE):
        print(f"ERROR: {PROPOSAL_FILE} not found — run generate_deck_proposal.py first", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {DECKS_FILE}...")
    decks = load_json(DECKS_FILE)

    print(f"Loading {PROPOSAL_FILE}...")
    proposal = load_json(PROPOSAL_FILE)

    print(f"\nApplying proposal ({'DRY RUN' if args.dry_run else 'LIVE'}):")
    new_decks, changed = apply_proposal(decks, proposal, dry_run=args.dry_run)

    if args.dry_run:
        print(f"\n[DRY-RUN] Would modify {len(changed)} civs. No files written.")
        return

    if args.backup:
        shutil.copy2(DECKS_FILE, BACKUP_FILE)
        print(f"\nBacked up original to {BACKUP_FILE}")

    print(f"\nWriting {DECKS_FILE}...")
    save_json(DECKS_FILE, new_decks)
    print(f"Done. Modified {len(changed)} civs.")
    print(
        "\nNext step: run the mod deploy pipeline to pick up the changes "
        "and test in-game."
    )


if __name__ == "__main__":
    main()
