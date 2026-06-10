#!/usr/bin/env python3
"""classify_unit_roles.py — decide, for every (civ, unit) pair, whether the
unit is a **nation-unique elite anchor** (never routs early), a **retreat
unit** (standard shared unit that routs at the 25% HP threshold), a
**situational** unit (mercenary / native-alliance / shipment / outlaw /
politician / church / consulate — not part of the core standing army), or a
**hero** (explorer / commander, never routs).

Why this exists
---------------
The old tier heuristic in resolve_civ_rosters.py labelled a unit "core_unique"
purely from a name prefix (de/yp/xp). That is wrong in both directions:
  * `xpHorseArtillery` is trained by 29 nations but got tagged core_unique
    just because of the `xp` prefix — it is plainly a *shared* unit.
  * `Longbowman` (trained by exactly ONE nation) is genuinely unique but the
    prefix rule never saw it.

The authoritative, objective signal is **how many nations can train the unit**
(from the unit index's per-proto `civs` list). Combined with the hand-curated
signature list in `data/anw_civ_blurbs.json` (`unique_units`, the units a civ's
identity is built around — these are the ones the design intends to "never
rout"), we get a defensible per-civ classification:

  role = hero        if the unit is the civ's hero/explorer
       = situational if its roster source is merc/native/shipment/outlaw/
                       politician/church/consulate/revolution
       = unique      if (it is in the civ's curated unique_units list)
                       OR (it is a core military unit trained by exactly ONE
                           nation)
       = retreat     otherwise (a core military unit shared by 2+ nations)

`unique` units are the elite anchors `llIsEliteUnit()` should hold (rout at a
lower HP / never rout); `retreat` units rout normally at
`cLLAiRoutHpThreshold` (0.25).

Outputs
-------
  artifacts/unit_index/unit_roles.json
      { civ: { proto: {role, reason, nations, label, source, tier, icon} } }
      — the single source of truth the release-readiness site consumes for its
        Unique-Units row, Retreat-Units row, and full-roster section.
  artifacts/unit_index/classification_review.md
      human-readable per-civ review so the changes are auditable at a glance.

Run:  python3 tools/validation/classify_unit_roles.py
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from resolve_display_names import load_display_names as _load_display_names
except Exception:  # pragma: no cover — defensive
    def _load_display_names() -> dict:
        return {}

# proto -> real in-game display name (e.g. deIncaRunner -> "Chimu Runner").
# Used both as an extra curated-match key and to relabel roster units so the
# release-readiness site shows the real unit name instead of the raw proto.
_DISPLAY_NAMES: dict[str, str] = _load_display_names()

UNIT_INDEX = REPO / "artifacts" / "unit_index" / "unit_index.json"
CIV_DETAIL = REPO / "artifacts" / "unit_index" / "civ_rosters_detailed.json"
BLURBS     = REPO / "data" / "anw_civ_blurbs.json"

OUT_ROLES  = REPO / "artifacts" / "unit_index" / "unit_roles.json"
OUT_REVIEW = REPO / "artifacts" / "unit_index" / "classification_review.md"

# Roster sources that are NOT part of the core standing army. Units that reach a
# civ through these channels are "situational" regardless of how rare they are.
SITUATIONAL_SOURCES = {
    "native_alliance", "homecity_shipment", "outlaw", "politician",
    "church", "consulate", "revolution",
}
CORE_SOURCES = {"enable", "train"}

# Hand-verified curated-name -> roster-proto aliases. With real in-game display
# names now resolved (resolve_display_names.py) and used as match keys, the vast
# majority of curated signature names match their roster proto automatically.
# This map only holds the *residual* cases where the curated blurb spelling
# still differs from the engine's display string by more than punctuation —
# a regional/abbreviated spelling (Pirate vs "Wokou Pirate", Hospitaller Knight
# vs "Hospitaller", Cassador vs "Veteran Cassador", Hakkapelit vs "Hackapell",
# Wakina Rifle vs "Wakina Rifleman", Yucateco Insurgente vs "Insurgente").
# Every entry was confirmed by (a) the proto existing in that civ's roster and
# (b) its resolved display name being the same real unit as the curated name.
#
# This is *data*, not a fuzzy heuristic: only exact, audited pairs go here so we
# never mislabel a unit unique by accident (e.g. a 0.50-ratio "War Dog"->Petard
# false positive). Curated names with no real roster unit stay unmatched and are
# surfaced in the review markdown as genuine content gaps.
_CURATED_ALIAS: dict[str, dict[str, str]] = {
    "ANWHaitians": {"pirate": "ypWokouPirate"},          # display "Wokou Pirate"
    "ANWLakota": {"wakinarifle": "xpWarRifle"},          # display "Wakina Rifleman"
    "ANWMaltese": {"hospitallerknight": "deHospitaller"},  # display "Hospitaller"
    "ANWMayans": {"yucatecoinsurgente": "deInsurgente"},   # display "Insurgente"
    "ANWPortuguese": {"cassador": "Cacadore"},           # display "Veteran Cassador"
    "ANWFinnish": {"hakkapelit": "MercHackapell"},       # display "Hackapell"
    "ANWSwedes": {"hakkapelit": "MercHackapell"},        # display "Hackapell"
    # Redundant blurb forms of an already-matched unit (kept so they aren't
    # falsely reported as gaps): short form / plural / regional spelling.
    "ANWAztecs": {"eaglerunner": "xpEagleKnight"},       # short form of Eagle Runner Knight
    "ANWRussians": {"streltsy": "Strelet"},              # plural of Strelet
    # "Granadero a Caballo" is literally Spanish for "Mounted Granadero" —
    # San Martín's Regiment of Mounted Grenadiers; the Argentine signature.
    "ANWArgentines": {"granaderoacaballo": "deREVGranadero"},  # display "Mounted Granadero"
}


def _norm(name: str) -> str:
    """Normalise a display name for fuzzy curated-list matching."""
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


# Engine proto prefixes that are NOT part of the human-facing unit name. Many
# roster labels are still raw protos (e.g. `xpGatlingGun`), while the curated
# blurb uses the display name (`Gatling Gun`); strip the prefix before matching.
_PROTO_PREFIX_RE = re.compile(r"^(xp|yp|de|ee|np|az)(?=[A-Z])")


def _match_keys(label: str, proto: str) -> set[str]:
    """All normalised keys a curated name may legitimately match for a unit:
    its roster label, its real in-game display name, and its proto with any
    engine prefix stripped. The display name is the key that lets a civ's
    curated signature spelling (e.g. "Chimu Runner", "Samurai", "Sentinel")
    reach a roster proto the engine names differently from its proto id."""
    keys = {_norm(label)}
    display = _DISPLAY_NAMES.get(proto)
    if display:
        keys.add(_norm(display))
    deprefixed = _PROTO_PREFIX_RE.sub("", proto or "")
    keys.add(_norm(deprefixed))
    keys.add(_norm(proto))
    return {k for k in keys if k}


def main() -> int:
    idx = json.loads(UNIT_INDEX.read_text(encoding="utf-8"))["units"]
    detail = json.loads(CIV_DETAIL.read_text(encoding="utf-8"))["civs"]
    blurbs = json.loads(BLURBS.read_text(encoding="utf-8"))

    roles: dict[str, dict] = {}
    review_rows: list[str] = []
    unmatched_curated: dict[str, list[str]] = {}

    civ_unique_counts = {}

    for civ in sorted(detail):
        units = detail[civ]
        # Curated signature names for this civ (display names), normalised.
        curated = blurbs.get(civ, {}).get("unique_units", []) or []
        curated_norm = {_norm(c): c for c in curated if _norm(c)}

        # Resolve curated names -> the protos they designate in this roster.
        # A curated name marks its unit unique regardless of roster source
        # (design intent: signature units are elite anchors even if they arrive
        # via shipment / native alliance).
        curated_protos: dict[str, str] = {}   # proto -> curated display name
        matched_curated: set[str] = set()
        for u in units:
            keys = _match_keys(u["label"], u["proto"])
            # Mark ALL curated forms this unit satisfies, not just the first.
            # Blurbs often list both a long and short / old and new spelling of
            # the same unit (e.g. "Urumi Swordsman" + "Urumi", "Strelet" +
            # "Streltsy", "Eagle Runner Knight" + "Eagle Runner"); they all
            # designate one proto, so all of them count as matched — otherwise
            # the redundant form is falsely reported as a missing-content gap.
            hits = [curated_norm[k] for k in keys if k in curated_norm]
            if hits:
                curated_protos[u["proto"]] = hits[0]
                for h in hits:
                    matched_curated.add(_norm(h))

        # Second pass: hand-verified curated-name -> proto aliases for units the
        # normalised-key matcher can't reach (renamed-in-DE units, regional
        # spellings, REV/Nat/Merc-only protos). Only audited pairs live in
        # _CURATED_ALIAS, so this never produces a fuzzy false positive.
        roster_protos = {u["proto"] for u in units}
        for cnorm, proto in _CURATED_ALIAS.get(civ, {}).items():
            if cnorm in matched_curated:
                continue
            orig = curated_norm.get(cnorm)
            if orig and proto in roster_protos:
                curated_protos[proto] = orig
                matched_curated.add(cnorm)

        civ_roles: dict[str, dict] = {}
        for u in units:
            proto = u["proto"]
            label = u["label"]
            tier = u["tier"]
            source = u["source"]
            nations = len(idx.get(proto, {}).get("civs", []) or [civ])
            in_curated = proto in curated_protos

            if tier == "hero" or source == "hero":
                role, reason = "hero", "hero / explorer (never routs)"
            elif in_curated:
                role = "unique"
                reason = (f"curated signature unit "
                          f"(anw_civ_blurbs.json: \"{curated_protos[proto]}\")")
            elif source in SITUATIONAL_SOURCES:
                role = "situational"
                reason = f"reaches civ via {source} (not core army)"
            elif source in CORE_SOURCES and nations == 1:
                role = "unique"
                reason = "core unit trained by exactly one nation"
            else:
                role = "retreat"
                reason = f"core unit shared by {nations} nations"

            civ_roles[proto] = {
                "role": role,
                "reason": reason,
                "nations": nations,
                "label": label,
                "source": source,
                "tier": tier,
                "icon": u.get("icon"),
                "age": u.get("age"),
            }

        roles[civ] = civ_roles
        civ_unique_counts[civ] = sum(
            1 for r in civ_roles.values() if r["role"] == "unique")

        # Curated names that matched no roster unit → flag for human review.
        missing = [orig for n, orig in curated_norm.items()
                   if n not in matched_curated]
        if missing:
            unmatched_curated[civ] = missing

    OUT_ROLES.parent.mkdir(parents=True, exist_ok=True)
    now = _dt.datetime.now().isoformat(timespec="seconds")
    OUT_ROLES.write_text(json.dumps({
        "generated": now,
        "civ_count": len(roles),
        "roles": roles,
    }, indent=2), encoding="utf-8")

    # Augment civ_rosters_detailed.json in place so the release-readiness site
    # has a single consumable file carrying the corrected role per unit.
    _augment_civ_detail(roles)

    write_review(roles, unmatched_curated, now)

    total = sum(len(v) for v in roles.values())
    by_role = {}
    for cr in roles.values():
        for r in cr.values():
            by_role[r["role"]] = by_role.get(r["role"], 0) + 1
    print(f"Classified {total} (civ,unit) pairs across {len(roles)} civs.")
    for k in ("hero", "unique", "retreat", "situational"):
        print(f"  {k:<11}: {by_role.get(k, 0)}")
    if unmatched_curated:
        n = sum(len(v) for v in unmatched_curated.values())
        print(f"  [review] {n} curated unique-unit names matched no roster "
              f"unit across {len(unmatched_curated)} civs (see review md)")
    print(f"  -> {OUT_ROLES.relative_to(REPO)}")
    print(f"  -> {OUT_REVIEW.relative_to(REPO)}")
    return 0


def _augment_civ_detail(roles: dict):
    """Write the computed role/reason back onto each unit in
    civ_rosters_detailed.json so the site reads one file."""
    blob = json.loads(CIV_DETAIL.read_text(encoding="utf-8"))
    for civ, units in blob.get("civs", {}).items():
        cr = roles.get(civ, {})
        for u in units:
            r = cr.get(u["proto"])
            if r:
                u["role"] = r["role"]
                u["role_reason"] = r["reason"]
            # Relabel with the real in-game display name when the current label
            # is just the raw proto (so the site shows "Chimu Runner", not
            # "deIncaRunner"). Preserve the proto for reference.
            display = _DISPLAY_NAMES.get(u["proto"])
            if display and (not u.get("label") or u["label"] == u["proto"]):
                u["label"] = display
    blob["roles_merged"] = True
    blob["display_names_resolved"] = True
    CIV_DETAIL.write_text(json.dumps(blob, indent=2), encoding="utf-8")


def write_review(roles: dict, unmatched: dict, now: str):
    lines: list[str] = []
    lines.append("# Unit Role Classification Review")
    lines.append("")
    lines.append(f"*Auto-generated by `tools/validation/classify_unit_roles.py` "
                 f"on {now}.*")
    lines.append("")
    lines.append("For every nation, each unit it can field is classified as "
                 "**unique** (elite anchor — `llIsEliteUnit()` should hold it / "
                 "never rout early), **retreat** (standard shared unit — routs "
                 "at the 25% HP threshold `cLLAiRoutHpThreshold`), "
                 "**situational** (mercenary / native / shipment / outlaw / "
                 "politician / church / consulate — not core army), or "
                 "**hero** (never routs).")
    lines.append("")
    lines.append("Decision rule (see script header): a core military unit "
                 "trained by **exactly one nation**, or one named in that "
                 "civ's curated `unique_units`, is **unique**; a core unit "
                 "**shared by 2+ nations** is **retreat**. This replaces the "
                 "old name-prefix heuristic that mislabelled shared units like "
                 "`xpHorseArtillery` (29 nations) as unique.")
    lines.append("")

    if unmatched:
        lines.append("## ⚠ Curated names needing review")
        lines.append("")
        lines.append("These names appear in a civ's `unique_units` blurb but "
                     "matched no unit in that civ's resolved roster — verify "
                     "the display name or whether the civ actually fields it.")
        lines.append("")
        for civ in sorted(unmatched):
            lines.append(f"- **{_short(civ)}**: {', '.join(unmatched[civ])}")
        lines.append("")

    for civ in sorted(roles):
        cr = roles[civ]
        uniques = [r for r in cr.values() if r["role"] == "unique"]
        retreats = [r for r in cr.values() if r["role"] == "retreat"]
        situ = [r for r in cr.values() if r["role"] == "situational"]
        heroes = [r for r in cr.values() if r["role"] == "hero"]
        lines.append(f"## {_short(civ)}")
        lines.append("")
        lines.append(f"unique **{len(uniques)}** · retreat **{len(retreats)}** "
                     f"· situational {len(situ)} · hero {len(heroes)}")
        lines.append("")
        if uniques:
            lines.append("**Unique (elite anchors):**")
            for r in sorted(uniques, key=lambda r: r["label"].lower()):
                lines.append(f"- {r['label']} — _{r['reason']}_")
            lines.append("")
        if retreats:
            lines.append("**Retreat (standard, routs at 25%):**")
            names = ", ".join(sorted(r["label"] for r in retreats))
            lines.append(names)
            lines.append("")

    OUT_REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _short(tok: str) -> str:
    return tok[3:] if tok.startswith("ANW") else tok


if __name__ == "__main__":
    raise SystemExit(main())
