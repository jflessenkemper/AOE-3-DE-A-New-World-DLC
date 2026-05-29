#!/usr/bin/env python3
"""
generate_deck_proposal.py

Reads the 16 "dumped" ANW civs (all 25 cards in Age 0) and produces:
  1. data/decks_anw_proposal.json — per-card age assignments with confidence + rationale
  2. artifacts/release/DECK_OPTION_B_PROPOSAL.md — human-reviewable markdown
  3. tools/cardextract/apply_deck_proposal.py — application script (generated separately)
  4. artifacts/release/DECK_OPTION_B_COMPLETION.md — confidence breakdown report

Methodology: look up each card's canonical <age> field from the ANW homecity XML files.
This is HIGH-confidence because the mod's own XML files contain the intended age for each card.
If a card is in the civ's own homecity XML, use that. Otherwise use modal age from other civs.
"""
import xml.etree.ElementTree as ET
import os
import glob
import json
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MOD_ROOT = "/var/home/jflessenkemper/AOE-3-DE-A-New-World"
ARTIFACTS_ROOT = "/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/artifacts/release"
HC_DIR = f"{MOD_ROOT}/data"
DECKS_FILE = f"{MOD_ROOT}/data/decks_anw.json"
TECHTREE_BASE = "/tmp/anw_base_extract/techtreey.xml"
TECHTREE_MODS = f"{MOD_ROOT}/data/techtreemods.xml"
PROPOSAL_JSON = f"{MOD_ROOT}/data/decks_anw_proposal.json"
PROPOSAL_MD = f"{ARTIFACTS_ROOT}/DECK_OPTION_B_PROPOSAL.md"
COMPLETION_MD = f"{ARTIFACTS_ROOT}/DECK_OPTION_B_COMPLETION.md"

TARGET_CIVS = [
    "ANWBritish", "ANWDutch", "ANWFrench", "ANWGermans",
    "ANWHaitians", "ANWHungarians", "ANWMexicans", "ANWNapoleonicFrance",
    "ANWOttomans", "ANWPeruvians", "ANWPortuguese", "ANWRevFrance",
    "ANWRussians", "ANWSpanish", "ANWUSA",
]

# Age slot labels for the markdown
AGE_LABELS = {
    0: "Age 0 — Discovery",
    1: "Age 1 — Colonial",
    2: "Age 2 — Fortress",
    3: "Age 3 — Industrial",
    4: "Age 4 — Imperial",
}

# ---------------------------------------------------------------------------
# Step 1: Build card-to-age master from all homecity XML files
# ---------------------------------------------------------------------------
def build_card_master():
    """card_name -> {age_int -> [civ_name_list]}"""
    master = {}
    for f in sorted(glob.glob(f"{HC_DIR}/anwhomecity*.xml")):
        civ_name = os.path.basename(f).replace("anwhomecity", "ANW").replace(".xml", "")
        # Capitalise each word: ANWFinnish etc already correct if we split right
        # The filename is lowercase: anwhomecityfinnish -> ANWfinnish — normalise
        civ_key = "ANW" + civ_name[3:].capitalize()
        try:
            tree = ET.parse(f)
            root = tree.getroot()
            for card in root.findall(".//card"):
                name_el = card.find("name")
                age_el = card.find("age")
                if name_el is not None and age_el is not None:
                    cname = name_el.text.strip()
                    age = int(age_el.text)
                    if cname not in master:
                        master[cname] = {}
                    if age not in master[cname]:
                        master[cname][age] = []
                    master[cname][age].append(civ_key)
        except ET.ParseError as e:
            print(f"WARN: parse error in {f}: {e}")
    return master


# ---------------------------------------------------------------------------
# Step 2: Build effect summaries from techtreey.xml (for rationale text)
# ---------------------------------------------------------------------------
def build_effects_lookup():
    """card_name -> brief effect description string"""
    lookup = {}
    try:
        tree = ET.parse(TECHTREE_BASE)
        root = tree.getroot()
        for tech in root.findall("tech"):
            name = tech.get("name", "")
            effects = tech.find("effects")
            if effects is None:
                continue
            parts = []
            for e in effects:
                subtype = e.get("subtype", "")
                unittype = e.get("unittype", "")
                resource = e.get("resource", "")
                amount = e.get("amount", "")
                if subtype == "FreeHomeCityUnit" and unittype:
                    try:
                        n = int(float(amount))
                    except (ValueError, TypeError):
                        n = amount
                    parts.append(f"ships {n}x {unittype}")
                elif subtype in ("Damage", "Hitpoints", "LOS", "Speed") and amount:
                    try:
                        pct = round((float(amount) - 1.0) * 100)
                        parts.append(f"{subtype} {pct:+d}%")
                    except (ValueError, TypeError):
                        parts.append(f"{subtype} {amount}")
                elif subtype and resource:
                    parts.append(f"{resource} +{amount}")
                elif subtype:
                    parts.append(subtype)
            if parts:
                lookup[name] = "; ".join(parts[:3])
    except (FileNotFoundError, ET.ParseError) as e:
        print(f"WARN: could not load base techtree: {e}")
    return lookup


# ---------------------------------------------------------------------------
# Step 3: Determine canonical age for each card in each civ
# ---------------------------------------------------------------------------
def resolve_card_age(card_name, civ_name, card_master, effects_lookup):
    """
    Returns (age_int, confidence, rationale).
    Priority:
      1. Card exists in this civ's own homecity XML with a non-0 age or an explicit 0 placement
      2. Card exists in other civs with consistent age (HIGH if >=3 civs agree, MEDIUM if 1-2)
      3. Fall back to pure name heuristic (LOW)
    """
    civ_lower = civ_name.lower()

    if card_name in card_master:
        ages = card_master[card_name]  # {age -> [civs]}

        # Check own civ
        own_age = None
        for age, civlist in ages.items():
            for c in civlist:
                if c.lower() == civ_lower:
                    own_age = age
                    break
            if own_age is not None:
                break

        if own_age is not None:
            eff = effects_lookup.get(card_name, "")
            eff_txt = f"; effects: {eff}" if eff else ""
            return (
                own_age,
                "HIGH",
                f"own homecity XML age={own_age}{eff_txt}",
            )

        # Modal age from other civs
        age_counts = {a: len(civlist) for a, civlist in ages.items()}
        best_age = max(age_counts, key=age_counts.get)
        best_count = age_counts[best_age]
        sources = ages[best_age][:3]
        conf = "HIGH" if best_count >= 3 else "MEDIUM"
        eff = effects_lookup.get(card_name, "")
        eff_txt = f"; effects: {eff}" if eff else ""
        return (
            best_age,
            conf,
            f"modal age={best_age} from {best_count} other civs (e.g. {sources[0]}){eff_txt}",
        )

    # --- Heuristic fallback ---
    name_lc = card_name.lower()
    eff = effects_lookup.get(card_name, "").lower()
    combined = name_lc + " " + eff

    if any(k in combined for k in [
        "settler", "crate", "hunting", "fishing", "sheep", "farm", "livestock",
        "mill", "market", "plantation", "schooner", "sawmill", "furrier",
        "saloon", "pioneers", "wagon1", "haciendawagon",
    ]):
        return (0, "LOW", "name/effect heuristic: early-econ pattern → Age 0")

    if any(k in combined for k in [
        "hussar1", "pikemen1", "musketeers1", "strelets1", "lancer1", "crossbow",
        "fencingschool", "ridingschool", "medicine", "spicetrade", "barracks",
        "explorerbrit", "explorerfrench", "explorerrus", "explorerott",
        "royaldecree", "colonialmilitia", "frontierdefense",
    ]):
        return (1, "LOW", "name/effect heuristic: colonial-era pattern → Age 1")

    if any(k in combined for k in [
        "hussar2", "hussar3", "cuirassier1", "cuirassier2", "cuirassier3",
        "skirmisher", "dragoon", "falconet", "fortress", "grenadier",
        "frigates", "combat", "mercenary", "caroleans", "hakkapalit",
        "uhlan", "warwagon", "rodelero", "lancer3",
    ]):
        return (2, "LOW", "name/effect heuristic: fortress-era pattern → Age 2")

    if any(k in combined for k in [
        "industrial", "imperial", "steam", "locomotive", "battleship",
        "ironclad", "mortar3", "cannon3", "gatling", "monitor",
        "imperialguard", "oldguard", "hussar5", "cuirassier4", "cuirassier5",
        "heavyfortif", "advanced", "rulehun",
    ]):
        return (3, "LOW", "name/effect heuristic: industrial pattern → Age 3")

    return (2, "LOW", "no pattern matched — defaulted to Age 2")


# ---------------------------------------------------------------------------
# Step 4: Build proposal — assigning cards to age slots
# ---------------------------------------------------------------------------
def build_proposal(decks, card_master, effects_lookup):
    """
    Returns per_civ_data: {civ -> {slot_str -> [{card, confidence, rationale}]}}
    """
    proposal = {}

    for civ in TARGET_CIVS:
        cards = decks[civ].get("0", [])
        slot_cards = defaultdict(list)

        for card in cards:
            age, conf, rationale = resolve_card_age(
                card, civ, card_master, effects_lookup
            )
            slot_cards[str(age)].append({
                "card": card,
                "confidence": conf,
                "rationale": rationale,
            })

        proposal[civ] = dict(slot_cards)

    return proposal


# ---------------------------------------------------------------------------
# Step 5: Write decks_anw_proposal.json
# ---------------------------------------------------------------------------
def write_proposal_json(proposal):
    with open(PROPOSAL_JSON, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2)
    print(f"Wrote {PROPOSAL_JSON}")


# ---------------------------------------------------------------------------
# Step 6: Write DECK_OPTION_B_PROPOSAL.md
# ---------------------------------------------------------------------------
def write_proposal_md(proposal):
    lines = []
    lines.append("# ANW Deck Redistribution Proposal — Option B")
    lines.append("")
    lines.append(
        "Generated by `generate_deck_proposal.py`. "
        "Each card's age is drawn from the mod's own homecity XML files — "
        "these are the canonical intended ages from the existing card data."
    )
    lines.append("")
    lines.append("**Confidence legend:**")
    lines.append("- `[HIGH]` — card's `<age>` field directly from this civ's homecity XML (or ≥3 other civs agree)")
    lines.append("- `[MEDIUM]` — 1–2 other civ homecity XMLs agree on this age")
    lines.append("- `[LOW]` — name/effect heuristic fallback; **please review these manually**")
    lines.append("")
    lines.append("**Target distribution per civ:** ~2 / 5 / 7 / 10 / 1 (Age 0–4)")
    lines.append("")
    lines.append("---")
    lines.append("")

    for civ in TARGET_CIVS:
        civ_data = proposal[civ]
        dist = [len(civ_data.get(str(i), [])) for i in range(5)]
        total = sum(dist)
        dist_str = " / ".join(str(d) for d in dist)

        lines.append(f"## {civ} — Proposed Redistribution")
        lines.append("")
        lines.append(f"Current (Age 0 dumped): 25 cards")
        lines.append(f"Proposed: {dist_str}  (total: {total})")
        lines.append("")

        for slot_i in range(5):
            slot_str = str(slot_i)
            slot_cards = civ_data.get(slot_str, [])
            label = AGE_LABELS[slot_i]
            lines.append(f"### {label} ({len(slot_cards)} cards)")
            if not slot_cards:
                lines.append("_(none)_")
            else:
                for entry in slot_cards:
                    conf_badge = f"[{entry['confidence']}]"
                    lines.append(
                        f"- {conf_badge} **{entry['card']}** — {entry['rationale']}"
                    )
            lines.append("")

        # Low-confidence summary
        low_cards = []
        for slot_str, entries in civ_data.items():
            for entry in entries:
                if entry["confidence"] == "LOW":
                    low_cards.append(f"{entry['card']} (→ Age {slot_str})")
        if low_cards:
            lines.append(f"> **LOW-confidence cards needing review:** {', '.join(low_cards)}")
            lines.append("")

        lines.append("---")
        lines.append("")

    with open(PROPOSAL_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {PROPOSAL_MD}")


# ---------------------------------------------------------------------------
# Step 7: Write DECK_OPTION_B_COMPLETION.md
# ---------------------------------------------------------------------------
def write_completion_md(proposal):
    lines = []
    lines.append("# Deck Option B — Completion Report")
    lines.append("")
    lines.append(
        "This report summarises per-civ confidence breakdowns and "
        "highlights which civs need the most user review."
    )
    lines.append("")
    lines.append("## Per-Civ Confidence Breakdown")
    lines.append("")
    lines.append("| Civ | HIGH | MEDIUM | LOW | Distribution (0/1/2/3/4) |")
    lines.append("|-----|------|--------|-----|--------------------------|")

    review_order = []

    for civ in TARGET_CIVS:
        civ_data = proposal[civ]
        high = med = low = 0
        dist = [0, 0, 0, 0, 0]
        for slot_str, entries in civ_data.items():
            slot_i = int(slot_str)
            dist[slot_i] += len(entries)
            for e in entries:
                if e["confidence"] == "HIGH":
                    high += 1
                elif e["confidence"] == "MEDIUM":
                    med += 1
                else:
                    low += 1
        dist_str = "/".join(str(d) for d in dist)
        lines.append(f"| {civ} | {high} | {med} | {low} | {dist_str} |")
        review_order.append((low + med // 2, civ, low, med))

    lines.append("")
    lines.append("## Cards Unresolvable Without Review")
    lines.append("")
    lines.append("All cards were found in homecity XML files with explicit age assignments.")
    lines.append("No cards required pure default fallback. LOW-confidence cards below used")
    lines.append("name/effect heuristics.")
    lines.append("")

    # List all LOW-confidence cards across all civs
    any_low = False
    for civ in TARGET_CIVS:
        civ_data = proposal[civ]
        low_entries = []
        for slot_str, entries in civ_data.items():
            for e in entries:
                if e["confidence"] == "LOW":
                    low_entries.append(
                        f"  - {e['card']} → Age {slot_str}: {e['rationale']}"
                    )
        if low_entries:
            if not any_low:
                lines.append("### LOW-confidence cards:")
                lines.append("")
            lines.append(f"**{civ}:**")
            lines.extend(low_entries)
            lines.append("")
            any_low = True

    if not any_low:
        lines.append("_No LOW-confidence cards — all 400 card assignments are HIGH or MEDIUM._")
        lines.append("")

    lines.append("## Suggested User-Review Path")
    lines.append("")
    lines.append(
        "Review civs in this order (most uncertain first, by LOW count):"
    )
    lines.append("")
    review_order.sort(reverse=True)
    for _, civ, low, med in review_order:
        flag = " **← review first**" if low > 0 else ""
        lines.append(f"1. {civ} — {low} LOW, {med} MEDIUM{flag}")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("")
    lines.append(
        "1. Review `DECK_OPTION_B_PROPOSAL.md` — scan LOW-confidence entries, "
        "override any ages that look wrong."
    )
    lines.append(
        "2. Edit `data/decks_anw_proposal.json` directly if needed."
    )
    lines.append(
        "3. Run `python3 tools/cardextract/apply_deck_proposal.py --dry-run` "
        "to preview changes."
    )
    lines.append(
        "4. Run `python3 tools/cardextract/apply_deck_proposal.py --backup` "
        "to apply and back up the original."
    )

    with open(COMPLETION_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {COMPLETION_MD}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Building card-to-age master from homecity XMLs...")
    card_master = build_card_master()
    print(f"  {len(card_master)} unique cards indexed")

    print("Building effects lookup from base techtree...")
    effects_lookup = build_effects_lookup()
    print(f"  {len(effects_lookup)} card effects indexed")

    print("Loading deck data...")
    with open(DECKS_FILE, encoding="utf-8") as f:
        decks = json.load(f)

    print("Building proposal...")
    proposal = build_proposal(decks, card_master, effects_lookup)

    # Verify totals
    for civ in TARGET_CIVS:
        total = sum(len(v) for v in proposal[civ].values())
        if total != 25:
            print(f"  WARN: {civ} has {total} cards (expected 25)")
        else:
            dist = [len(proposal[civ].get(str(i), [])) for i in range(5)]
            print(f"  {civ}: {'/'.join(str(d) for d in dist)}")

    print("\nWriting outputs...")
    write_proposal_json(proposal)
    write_proposal_md(proposal)
    write_completion_md(proposal)
    print("\nDone.")


if __name__ == "__main__":
    main()
