"""Parse a_new_world.html into structured per-civ doctrine
contracts so the replay validator can cross-check that runtime probes match
what the public reference tree advertises.

The HTML stores each civ as:

    <details class="nation-node" data-name="British Elizabeth"
        data-search="... long blob ...
                     · Builds the docks first. ... wall ring ...">
      <summary>... <img class="portrait-img" src="resources/.../foo.png">

The trailing prose after the last "·" separator in `data-search` is the
playstyle/walling doctrine narrative. We map well-known keywords in that
prose to runtime probe expectations:

    "no walls"/"never wall"/"refuses to wall"  → wallStrategy MobileNoWalls
    "choke"/"chokepoint"                       → wallStrategy ChokepointSegments
    "ring wall"/"wall ring"/"perimeter wall"   → wallStrategy FortressRing
    "palisade"                                 → wallStrategy FrontierPalisades
    "barricade"                                → wallStrategy UrbanBarricade
    "coastal"/"harbour"/"harbor"               → wallStrategy CoastalBatteries
    "docks first"/"fleet"/"naval"              → expect ships+fleetSnap > 0
    "forward"/"frontier"/"raid"/"mobile"       → expect outward heading_axis
    "treaty"/"trading post"/"native ally"      → expect compliance.diplomacy.tposts ≥ 1
    "cavalry-heavy"/"horse"                    → expect btBiasCav > 0 (proxy via personality)
    "infantry"/"musketeer-heavy"               → expect btBiasInf > 0

Numeric mapping must match cLLWallStrategy* constants in aiHeader.xs
(verified against game/ai/aiHeader.xs:202-207):
    0=FortressRing 1=ChokepointSegments 2=CoastalBatteries
    3=FrontierPalisades 4=UrbanBarricade 5=MobileNoWalls

Usage:
    from tools.playtest.html_reference import load_doctrine_contracts
    contracts = load_doctrine_contracts(Path("a_new_world.html"))
    contracts["British"]  # → DoctrineContract(...)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Wall-strategy ints from aiHeader.xs cLLWallStrategy* (NOT aiGlobals.xs).
# Verified against game/ai/aiHeader.xs:202-207. Earlier versions of this
# file had these off-by-one (1..6); that silently broke every wall-strategy
# assertion in tools/playtest/replay_probes.py because the runtime emits
# 0..5 from gLLWallStrategy.
WALL_FORTRESS_RING       = 0
WALL_CHOKEPOINT_SEGMENTS = 1
WALL_COASTAL_BATTERIES   = 2
WALL_FRONTIER_PALISADES  = 3
WALL_URBAN_BARRICADE     = 4
WALL_MOBILE_NO_WALLS     = 5

# Phrase → expected wall strategy. Order matters: more specific first.
WALL_PHRASES = [
    # Mobile / no-wall doctrines.
    (re.compile(r"\b(?:no walls?|never wall|refuses? to wall|substitutes? .*? for walls|causeways for walls|War Huts and causeways)\b", re.I),
     WALL_MOBILE_NO_WALLS),
    (re.compile(r"\b(?:scout.{0,8}intercept|raid mobility|mobile camps?)\b", re.I),
     WALL_MOBILE_NO_WALLS),
    # Chokepoint.
    (re.compile(r"\b(?:choke ?points?|chokes? — cliffs|cliff edges? and valley|valley chokepoints?)\b", re.I),
     WALL_CHOKEPOINT_SEGMENTS),
    # Coastal batteries.
    (re.compile(r"\b(?:coastal batter|harbou?r batteries?|coastal defen[cs]e)\b", re.I),
     WALL_COASTAL_BATTERIES),
    # Urban barricade.
    (re.compile(r"\b(?:urban barricade|Paris barricades?|city barricade)\b", re.I),
     WALL_URBAN_BARRICADE),
    # Fortress ring.
    (re.compile(r"\b(?:wall ring|ring[- ]wall|perimeter wall|fortress ring|star[- ]fort|Vauban|triple fortress|multi[- ]ring)\b", re.I),
     WALL_FORTRESS_RING),
    # Frontier palisades (catch-all wall strategy when prose says "palisade").
    (re.compile(r"\b(?:frontier palisades?|colonial palisade|palisade)\b", re.I),
     WALL_FRONTIER_PALISADES),
]

NAVAL_RX     = re.compile(r"\b(?:docks? first|fishing fleet|naval shipment|harbou?r|warships?|fleet|coastal)\b", re.I)
FORWARD_RX   = re.compile(r"\b(?:forward (?:base|warband)|frontier|raid|mobile|outward|push enemy[- ]ward|Frontier ?Push)\b", re.I)
TREATY_RX    = re.compile(r"\b(?:trading post|treaty|native (?:ally|warriors?)|Native Embassy|Travois)\b", re.I)
CAVALRY_RX   = re.compile(r"\b(?:cavalry[- ]heavy|over[- ]builds? Stables?|hussar|cossack|Lipizzaner|raiding cavalry)\b", re.I)
INFANTRY_RX  = re.compile(r"\b(?:musketeer[- ]heavy|levée|levee|line[- ]infantry|grenadier mass|pike[- ]heavy)\b", re.I)
ARTILLERY_RX = re.compile(r"\b(?:siege train|grand battery|cannon doctrine|bombard|Vauban[- ]style bastion)\b", re.I)


@dataclass
class DoctrineContract:
    """What the HTML reference promises about a civ. Each field is None
    when the prose doesn't make a claim — the validator only asserts on
    fields with a value, so partial coverage is fine."""

    civ_label: str
    leader_label: str
    portrait_path: Optional[str]
    doctrine_prose: str  # the trailing paragraph itself, for diagnostic display
    expected_wall_strategy: Optional[int] = None
    expects_naval: bool = False
    expects_forward: bool = False
    expects_treaty: bool = False
    expects_cavalry: bool = False
    expects_infantry: bool = False
    expects_artillery: bool = False
    keyword_hits: list[str] = field(default_factory=list)


# `data-name="Civ Leader Words"` — capture the whole first token block.
NATION_BLOCK_RX = re.compile(
    r'<details class="nation-node"[^>]*?data-name="([^"]+)"[^>]*?data-search="([^"]+)">'
    r'\s*<summary>.*?<img class="portrait-img" src="([^"]+)"',
    re.DOTALL,
)


def _extract_doctrine_prose(data_search: str) -> str:
    """The doctrine narrative is the trailing prose paragraph in data-search,
    after the last "·" card-list separator. Sometimes the doctrine itself
    contains "·" (rare); we take everything after the final separator and
    strip leading whitespace. Falls back to the entire blob if no separator."""
    parts = data_search.split(" · ")
    return parts[-1].strip() if parts else data_search.strip()


def _classify(prose: str) -> tuple[Optional[int], dict[str, bool], list[str]]:
    """Return (wall_strategy, flags_dict, keyword_hits) from doctrine prose."""
    hits: list[str] = []
    wall_strategy: Optional[int] = None
    for rx, strat in WALL_PHRASES:
        m = rx.search(prose)
        if m:
            wall_strategy = strat
            hits.append(f"wall:{m.group(0)}")
            break  # first wall match wins (most specific patterns are first)

    flags = {
        "expects_naval":     bool(NAVAL_RX.search(prose)),
        "expects_forward":   bool(FORWARD_RX.search(prose)),
        "expects_treaty":    bool(TREATY_RX.search(prose)),
        "expects_cavalry":   bool(CAVALRY_RX.search(prose)),
        "expects_infantry":  bool(INFANTRY_RX.search(prose)),
        "expects_artillery": bool(ARTILLERY_RX.search(prose)),
    }
    for label, hit in flags.items():
        if hit:
            hits.append(label.removeprefix("expects_"))
    return wall_strategy, flags, hits


# Civs whose first whitespace-separated token in `data-name` collides with
# another nation node (revolutions vs. base civs of the same root). For
# these we widen the civ_label to the first TWO tokens so the key remains
# unique. Anything not in this set keeps the legacy single-token key for
# backwards compatibility with existing callers (matrix runner, replay
# validator).
MULTI_TOKEN_CIVS = frozenset({
    "French Canadians", "French Louis",
    "Baja Californians",
    "Napoleonic France",
    "Revolutionary France",
    "Rio Grande",
    "South Africans",
    "United States",
})


def _civ_label_for(full_name: str) -> tuple[str, str]:
    """Return (civ_label, leader_label).

    Multi-word civs (revolutions whose root collides with a base civ —
    French Canadians vs. French; Napoleonic France vs. French Louis) get a
    two-token civ_label so they don't overwrite each other in the
    contracts dict. Single-token civs keep their first-token key
    (e.g. 'British', 'Aztecs', 'Haudenosaunee')."""
    bits = full_name.split()
    if len(bits) >= 2:
        two = f"{bits[0]} {bits[1]}"
        if two in MULTI_TOKEN_CIVS:
            return two, " ".join(bits[2:])
    return bits[0], " ".join(bits[1:]) if len(bits) > 1 else ""


def load_doctrine_contracts(html_path: Path) -> dict[str, DoctrineContract]:
    """Read a_new_world.html and return contracts keyed by civ
    label. Single-token for unique civs ('British', 'Aztecs'), two-token
    for revolutions whose root collides with a base civ ('French Louis',
    'Napoleonic France', 'South Africans')."""
    text = html_path.read_text(encoding="utf-8", errors="replace")
    contracts: dict[str, DoctrineContract] = {}

    for m in NATION_BLOCK_RX.finditer(text):
        full_name = m.group(1)
        data_search = m.group(2)
        portrait = m.group(3)

        civ_label, leader_label = _civ_label_for(full_name)

        prose = _extract_doctrine_prose(data_search)
        wall_strat, flags, hits = _classify(prose)

        contracts[civ_label] = DoctrineContract(
            civ_label=civ_label,
            leader_label=leader_label,
            portrait_path=portrait,
            doctrine_prose=prose,
            expected_wall_strategy=wall_strat,
            keyword_hits=hits,
            **flags,
        )
    return contracts


# ─── self-test when run directly ───────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from pathlib import Path as _P

    repo_root = _P(__file__).resolve().parents[2]
    html = repo_root / "a_new_world.html"
    if not html.exists():
        print(f"missing {html}", file=sys.stderr)
        raise SystemExit(2)

    contracts = load_doctrine_contracts(html)
    print(f"parsed {len(contracts)} civ contracts")
    for c in sorted(contracts.values(), key=lambda x: x.civ_label):
        ws = c.expected_wall_strategy
        ws_name = {
            0: "FortressRing", 1: "ChokepointSegments", 2: "CoastalBatteries",
            3: "FrontierPalisades", 4: "UrbanBarricade", 5: "MobileNoWalls",
        }.get(ws, "—")
        print(f"  {c.civ_label:<22s}  wall={ws_name:<18s}  hits={','.join(c.keyword_hits) or '∅'}")
