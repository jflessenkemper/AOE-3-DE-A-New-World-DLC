#!/usr/bin/env python3
"""build_unit_index.py — master unit index for the ANW local wiki.

Cross-references three existing data sources into a single index of every
*createable* unit in the mod:

  1. artifacts/roster_audit/base_data/proto.xml   — per-unit stats
       (maxhitpoints, armor type/value, cost, populationcount, los,
        trainpoints, allowedage, protoaction attacks, icon).
  2. artifacts/roster_audit/resolved_rosters.json — which civ can create
       which unit (military_units + mercenaries + hero), with per-civ
       age / source / tier. Produced by resolve_civ_rosters.py.
  3. resources/images/icons/units/*.png           — extracted in-game
       menu/selection icons, resolved by name via the same helper the
       release-readiness site uses (_resolve_unit_icon).

Outputs (all under artifacts/unit_index/ except the wiki page):
  • unit_index.json            — master index: proto -> stats + civ list + icon
  • civ_rosters_detailed.json  — civ -> [ {proto,label,age,source,tier,stats,icon} ]
                                 consumed by build_release_readiness_site.py to
                                 render the per-civ "ALL UNITS" roster section.
  • docs/wiki/data-layer/unit-index.md — human-readable wiki index table.

The "createable unit" universe is the UNION of every unit referenced by any
civ roster — i.e. exactly the set the player can build/train/ship, which is
what "which nation can create them" means. Pure animals / projectiles /
buildings that no civ trains are excluded.

Run:  python3 tools/validation/build_unit_index.py
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]

PROTO_XML = REPO / "artifacts" / "roster_audit" / "base_data" / "proto.xml"
ROSTERS   = REPO / "artifacts" / "roster_audit" / "resolved_rosters.json"
UNIT_ICON_DIR = REPO / "resources" / "images" / "icons" / "units"
# Authoritative proto -> extracted-icon basename map, produced by
# extract_unit_icons.py straight from the game's proto.xml <icon> paths +
# UIResources1.bar payloads. This is the unambiguous primary resolver (404/408
# roster units); the slug/path heuristics below are fallbacks for the handful
# of protos with inherited/abstract icons not in the map.
PROTO_ICON_MAP_PATH = REPO / "artifacts" / "unit_index" / "proto_icon_map.json"

OUT_DIR   = REPO / "artifacts" / "unit_index"
OUT_INDEX = OUT_DIR / "unit_index.json"
OUT_CIV   = OUT_DIR / "civ_rosters_detailed.json"
OUT_WIKI  = REPO / "docs" / "wiki" / "data-layer" / "unit-index.md"

# Relative path from the wiki page (docs/wiki/data-layer/) to the icon dir.
WIKI_ICON_REL = "../../../resources/images/icons/units"

# --------------------------------------------------------------------------
# Icon resolution — reuse the site's resolver so icons match 1:1. Fall back to
# a local slug resolver if the heavy site module can't be imported.
# --------------------------------------------------------------------------

def _make_icon_resolver():
    sys.path.insert(0, str(HERE.parent))
    try:
        import build_release_readiness_site as site  # type: ignore
        return site._resolve_unit_icon
    except Exception as exc:  # pragma: no cover - defensive
        print(f"  [warn] site import failed ({exc}); using local slug resolver",
              file=sys.stderr)

        def _local(display_name: str):
            slug = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")
            cand = f"{slug}_icon.png"
            return cand if (UNIT_ICON_DIR / cand).is_file() else None

        return _local


_resolve_icon = _make_icon_resolver()


def _load_proto_icon_map() -> dict[str, str]:
    """Load the authoritative {proto: basename} map. Empty dict if absent
    (run extract_unit_icons.py first to populate it)."""
    try:
        m = json.loads(PROTO_ICON_MAP_PATH.read_text(encoding="utf-8"))
        # Keep only entries whose PNG actually landed on disk.
        return {k: v for k, v in m.items() if (UNIT_ICON_DIR / v).is_file()}
    except Exception as exc:  # pragma: no cover - defensive
        print(f"  [warn] proto_icon_map missing ({exc}); falling back to "
              "slug/path heuristics", file=sys.stderr)
        return {}


_PROTO_ICON_MAP = _load_proto_icon_map()


def icon_from_proto_path(proto_icon_path: str):
    """Derive the extracted-PNG filename from a proto <icon> path.

    proto.xml stores a Windows art path like
        resources\\art\\units\\infantry_ranged\\musketeer\\musketeer_icon_64x64.png
    The extracted icons in resources/images/icons/units/ drop the size suffix,
    e.g. musketeer_icon.png. This is the most reliable key — it works for
    proto-named units (MercBarbaryCorsair -> barbary_corsair_icon.png) where a
    name slug fails. Returns the basename if it exists, else None.
    """
    if not proto_icon_path:
        return None
    base = proto_icon_path.replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"_\d+x\d+(?=\.png$)", "", base)  # drop _64x64 etc.
    if not base.endswith(".png"):
        return None
    if (UNIT_ICON_DIR / base).is_file():
        return base
    # Safe fallback: the home-city card variant (hc_<base>) is the SAME unit's
    # icon — extracted under an hc_ prefix for several units (cacadore,
    # barbary_corsair, saxon_cuirassier, …). Only the exact-stem hc_ form is
    # accepted; no fuzzy substring matching (which would mis-assign, e.g.
    # bowman -> crossbowman).
    hc = f"hc_{base}"
    if (UNIT_ICON_DIR / hc).is_file():
        return hc
    return None


# A handful of Consulate-spawned protos inherit their parent unit's icon and so
# declare no <icon> in proto.xml (extract_unit_icons.py can't reach them). They
# are functionally the base unit — alias them to the base unit's extracted icon.
_ICON_ALIAS = {
    "ypConsulateNassauHalberdier": "halberdier_icon.png",
    "ypConsulatePetard": "petard_icon.png",
    "ypConsulateSpy": "spy_icon.png",
}


def resolve_icon(proto: str, proto_icon_path: str, *names: str):
    """Resolve a unit icon. Priority: authoritative proto->icon map (exact,
    extracted from the game), then the proto <icon> path heuristic, then name
    slugs as a last resort."""
    hit = _PROTO_ICON_MAP.get(proto)
    if hit:
        return hit
    alias = _ICON_ALIAS.get(proto)
    if alias and (UNIT_ICON_DIR / alias).is_file():
        return alias
    hit = icon_from_proto_path(proto_icon_path)
    if hit:
        return hit
    for n in names:
        if not n:
            continue
        hit = _resolve_icon(n)
        if hit:
            return hit
    return None


# --------------------------------------------------------------------------
# proto.xml parsing
# --------------------------------------------------------------------------

def _f(text, default=0.0):
    try:
        return float((text or "").strip())
    except (TypeError, ValueError):
        return default


def parse_proto_stats(path: Path) -> dict[str, dict]:
    """Return {proto_name: stat_dict} for every <unit> in proto.xml."""
    root = ET.parse(path).getroot()
    out: dict[str, dict] = {}
    for u in root.findall("unit"):
        name = u.get("name")
        if not name:
            continue

        hp = _f(u.findtext("maxhitpoints"))

        armor = []
        for a in u.findall("armor"):
            atype = a.get("type") or "?"
            pct = round(_f(a.get("value")) * 100)
            armor.append({"type": atype, "pct": pct})

        cost = {}
        for c in u.findall("cost"):
            res = c.get("resourcetype") or "?"
            amt = round(_f(c.text))
            if amt:
                cost[res] = cost.get(res, 0) + amt

        # Attacks: keep the highest-damage entry per damagetype (compact).
        best_by_type: dict[str, dict] = {}
        for pa in u.findall("protoaction"):
            dmg = _f(pa.findtext("damage"))
            if dmg <= 0:
                continue
            dtype = (pa.findtext("damagetype") or "?").strip()
            entry = {
                "type": dtype,
                "damage": round(dmg, 1),
                "rof": round(_f(pa.findtext("rof")), 2),
                "range": round(_f(pa.findtext("maxrange")), 1),
            }
            prev = best_by_type.get(dtype)
            if prev is None or entry["damage"] > prev["damage"]:
                best_by_type[dtype] = entry
        attacks = sorted(best_by_type.values(), key=lambda e: -e["damage"])

        out[name] = {
            "hp": round(hp),
            "armor": armor,
            "cost": cost,
            "pop": round(_f(u.findtext("populationcount"))),
            "los": round(_f(u.findtext("los")), 1),
            "train": round(_f(u.findtext("trainpoints")), 1),
            "age": int(_f(u.findtext("allowedage"))),
            "attacks": attacks,
            "proto_icon": (u.findtext("icon") or "").strip(),
        }
    return out


# --------------------------------------------------------------------------
# roster -> unit/civ cross-reference
# --------------------------------------------------------------------------

def iter_roster_units(civ_data: dict):
    """Yield (proto, label, age, source, tier) for every createable unit."""
    for entry in civ_data.get("military_units", []) or []:
        yield (entry.get("proto"), entry.get("label") or entry.get("proto"),
               entry.get("age"), entry.get("source"), entry.get("tier"))
    for entry in civ_data.get("mercenaries", []) or []:
        yield (entry.get("proto"), entry.get("label") or entry.get("proto"),
               entry.get("age"), entry.get("source"), entry.get("tier"))
    for hero in civ_data.get("hero", []) or []:
        # hero entries are bare proto strings
        if isinstance(hero, str):
            yield (hero, hero, 1, "hero", "hero")
        elif isinstance(hero, dict):
            yield (hero.get("proto"), hero.get("label") or hero.get("proto"),
                   hero.get("age"), hero.get("source") or "hero",
                   hero.get("tier") or "hero")


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def build():
    stats = parse_proto_stats(PROTO_XML)
    rosters = json.loads(ROSTERS.read_text(encoding="utf-8"))

    units: dict[str, dict] = {}
    civ_detail: dict[str, list] = {}

    for civ, civ_data in sorted(rosters.items()):
        detail_list = []
        seen_protos = set()
        for proto, label, age, source, tier in iter_roster_units(civ_data):
            if not proto:
                continue
            st = stats.get(proto, {})
            icon = resolve_icon(proto, st.get("proto_icon", ""), label, proto)

            # --- master index entry ---
            u = units.setdefault(proto, {
                "proto": proto,
                "label": label,
                "hp": st.get("hp", 0),
                "armor": st.get("armor", []),
                "attacks": st.get("attacks", []),
                "cost": st.get("cost", {}),
                "pop": st.get("pop", 0),
                "los": st.get("los", 0.0),
                "train": st.get("train", 0.0),
                "age": st.get("age", 0),
                "icon": icon,
                "has_stats": proto in stats,
                "civs": [],
                "tiers": {},
            })
            if civ not in u["civs"]:
                u["civs"].append(civ)
            u["tiers"][civ] = tier

            # --- per-civ detail (dedup per proto, keep lowest age) ---
            if proto not in seen_protos:
                seen_protos.add(proto)
                detail_list.append({
                    "proto": proto,
                    "label": label,
                    "age": age,
                    "source": source,
                    "tier": tier,
                    "hp": st.get("hp", 0),
                    "armor": st.get("armor", []),
                    "attacks": st.get("attacks", []),
                    "cost": st.get("cost", {}),
                    "pop": st.get("pop", 0),
                    "icon": icon,
                    "has_stats": proto in stats,
                })
        # Sort: tier (core first), then age, then name.
        tier_rank = {"hero": 0, "core_standard": 1, "core_unique": 2,
                     "situational": 3}
        detail_list.sort(key=lambda d: (tier_rank.get(d["tier"], 9),
                                        d["age"] or 0, d["label"].lower()))
        civ_detail[civ] = detail_list

    # finalize civ lists
    for u in units.values():
        u["civs"].sort()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = _dt.datetime.now().isoformat(timespec="seconds")

    OUT_INDEX.write_text(json.dumps({
        "generated": now,
        "unit_count": len(units),
        "civ_count": len(rosters),
        "units": dict(sorted(units.items())),
    }, indent=2), encoding="utf-8")

    OUT_CIV.write_text(json.dumps({
        "generated": now,
        "civs": civ_detail,
    }, indent=2), encoding="utf-8")

    write_wiki(units, rosters, now)

    icons_resolved = sum(1 for u in units.values() if u["icon"])
    no_stats = sum(1 for u in units.values() if not u["has_stats"])
    print(f"Unit index built: {len(units)} createable units across "
          f"{len(rosters)} civs.")
    print(f"  icons resolved : {icons_resolved}/{len(units)}")
    print(f"  missing stats  : {no_stats} (proto not found in proto.xml)")
    print(f"  -> {OUT_INDEX.relative_to(REPO)}")
    print(f"  -> {OUT_CIV.relative_to(REPO)}")
    print(f"  -> {OUT_WIKI.relative_to(REPO)}")

    # Re-derive the per-(civ,unit) role classification and merge it back into
    # civ_rosters_detailed.json, so a bare `build_unit_index.py` run never
    # leaves the site reading stale/absent roles. Best-effort: if the classifier
    # is unavailable the site falls back to the legacy tier mapping.
    try:
        sys.path.insert(0, str(HERE.parent))
        import classify_unit_roles  # type: ignore
        print("Re-deriving unit role classification ...")
        classify_unit_roles.main()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"  [warn] role classification skipped ({exc}); run "
              f"classify_unit_roles.py manually", file=sys.stderr)


# --------------------------------------------------------------------------
# Wiki markdown
# --------------------------------------------------------------------------

def _fmt_armor(armor):
    if not armor:
        return "—"
    return ", ".join(f"{a['pct']}% {a['type']}" for a in armor)


def _fmt_attacks(attacks):
    if not attacks:
        return "—"
    parts = []
    for a in attacks[:2]:
        seg = f"{a['damage']:g} {a['type']}"
        if a["range"]:
            seg += f" (rng {a['range']:g})"
        parts.append(seg)
    return "; ".join(parts)


def _fmt_cost(cost):
    if not cost:
        return "—"
    order = ["Food", "Wood", "Gold", "Coin"]
    keys = sorted(cost, key=lambda k: (order.index(k) if k in order else 99, k))
    return ", ".join(f"{cost[k]} {k}" for k in keys)


# Short civ labels for the "nations" column (strip ANW prefix).
def _civ_short(tok: str) -> str:
    return tok[3:] if tok.startswith("ANW") else tok


def write_wiki(units: dict[str, dict], rosters: dict, now: str):
    OUT_WIKI.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Unit Index")
    lines.append("")
    lines.append(f"*Auto-generated by `tools/validation/build_unit_index.py` "
                 f"on {now}. Do not edit by hand.*")
    lines.append("")
    lines.append(f"Every createable unit in the mod ({len(units)} units across "
                 f"{len(rosters)} civilizations), cross-referenced from "
                 "`proto.xml` (stats), `resolved_rosters.json` (which nation "
                 "can create each unit) and the extracted in-game icons.")
    lines.append("")
    lines.append("Columns: **Icon** · **Unit** · **Age** · **HP** · "
                 "**Armor** · **Attack** · **Cost** · **Pop** · "
                 "**Nations that can create it**.")
    lines.append("")
    lines.append("| Icon | Unit | Age | HP | Armor | Attack | Cost | Pop | Nations |")
    lines.append("|------|------|----:|---:|-------|--------|------|----:|---------|")

    for proto, u in sorted(units.items(),
                           key=lambda kv: kv[1]["label"].lower()):
        if u["icon"]:
            icon_md = f"![{u['label']}]({WIKI_ICON_REL}/{u['icon']})"
        else:
            icon_md = "—"
        civs = ", ".join(_civ_short(c) for c in u["civs"])
        name = u["label"]
        if name != proto:
            name = f"{name}<br><sub>`{proto}`</sub>"
        else:
            name = f"`{proto}`"
        hp = u["hp"] or "—"
        age = u["age"] if u["has_stats"] else "—"
        lines.append(
            f"| {icon_md} | {name} | {age} | {hp} | {_fmt_armor(u['armor'])} "
            f"| {_fmt_attacks(u['attacks'])} | {_fmt_cost(u['cost'])} "
            f"| {u['pop'] or '—'} | {civs} |"
        )

    lines.append("")
    lines.append("## Per-civ rosters")
    lines.append("")
    lines.append("The full list of units each nation can create is rendered "
                 "on that nation's page in the release-readiness site, in the "
                 "**ALL UNITS** section beneath *Unique Units* and *Retreat "
                 "Units*. The machine-readable source is "
                 "`artifacts/unit_index/civ_rosters_detailed.json`.")
    lines.append("")

    OUT_WIKI.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
