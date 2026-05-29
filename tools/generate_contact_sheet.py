#!/usr/bin/env python3
"""
Generate static_contact_sheet.html for ANW v1.0 release-readiness visual review.
Shows lobby_portrait, loading_flag, home_city preview, leader_portrait, and deck_card_back
for all 40 ANW civs side-by-side in one page.
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import date

BASE = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
CIVMODS = BASE / "data" / "civmods.xml"
OUT_HTML = BASE / "artifacts" / "validation" / "visual_art" / "static_contact_sheet.html"
OUT_JSON = BASE / "artifacts" / "validation" / "visual_art" / "art_inventory.json"
GENERATED_DATE = "2026-05-20"

# Leader name -> civ token mapping (derived from homecitypreviewwpf references in civmods.xml)
LEADER_TO_CIV = {
    "san_martin": "ANWArgentines",
    "montezuma": "ANWAztecs",
    "barbarossa": "ANWBarbary",
    "pedro_i": "ANWBrazil",
    "wellington": "ANWBritish",
    "brock": "ANWCanadians",
    "ohiggins": "ANWChileans",
    "kangxi": "ANWChinese",
    "bolivar": "ANWColumbians",
    "maurice": "ANWDutch",
    "muhammad_ali": "ANWEgyptians",
    "menelik": "ANWEthiopians",
    "mannerheim": "ANWFinnish",
    "napoleon": "ANWFrench",
    "frederick": "ANWGermans",
    "louverture": "ANWHaitians",
    "hiawatha": "ANWHaudenosaunee",
    "usman_dan_fodio": "ANWHausa",
    "kossuth": "ANWHungarians",
    "pachacuti": "ANWInca",
    "shivaji": "ANWIndians",
    "diponegoro": "ANWIndonesians",
    "garibaldi": "ANWItalians",
    "tokugawa": "ANWJapanese",
    "crazy_horse": "ANWLakota",
    "valette": "ANWMaltese",
    "canek": "ANWMayans",
    "hidalgo": "ANWMexicans",
    "napoleon_imperial": "ANWNapoleonicFrance",
    "suleiman": "ANWOttomans",
    "santa_cruz": "ANWPeruvians",
    "henry": "ANWPortuguese",
    "robespierre": "ANWRevFrance",
    "cuza": "ANWRomanians",
    "catherine": "ANWRussians",
    "kruger": "ANWSouthAfricans",
    "isabella": "ANWSpanish",
    "gustavus_adolphus": "ANWSwedes",
    "sam_houston": "ANWTexians",
    "washington": "ANWUSA",
}

# Build reverse mapping: civ -> list of leader files (prefer the named one from civmods)
CIV_TO_LEADER = {}
for leader_stem, civ in LEADER_TO_CIV.items():
    CIV_TO_LEADER.setdefault(civ, []).append(leader_stem)

def resolve_path(relative_path: str) -> Path | None:
    """Resolve a relative path from civmods.xml to an absolute Path, checking existence."""
    if not relative_path:
        return None
    # Normalize separators
    p = relative_path.replace("\\", "/")
    candidate = BASE / p
    if candidate.exists():
        return candidate
    # Try case-insensitive match in parent dir
    parent = candidate.parent
    if parent.exists():
        name_lower = candidate.name.lower()
        for f in parent.iterdir():
            if f.name.lower() == name_lower:
                return f
    return None

def ext_badge(path: Path) -> str:
    if path is None:
        return ""
    ext = path.suffix.lower()
    badges = {".ddt": "DDT", ".btx": "BTX", ".tga": "TGA", ".bak": "BAK"}
    return badges.get(ext, "")

def is_displayable(path: Path) -> bool:
    if path is None:
        return False
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}

def img_or_path(path: Path, label: str = "") -> str:
    """Return HTML snippet for a given asset path."""
    if path is None:
        return '<span class="missing">MISSING</span>'
    badge = ext_badge(path)
    rel = str(path).replace(str(BASE) + "/", "")
    abs_url = f"file://{path}"
    if is_displayable(path):
        return (
            f'<a href="{abs_url}" title="{rel}">'
            f'<img src="{abs_url}" loading="lazy" alt="{label}">'
            f'</a>'
        )
    else:
        return (
            f'<span class="badge">{badge}</span> '
            f'<a href="{abs_url}" title="{rel}" class="path-link">{path.name}</a>'
        )

def find_leader_portrait(civ_token: str, preview_wpf: str) -> Path | None:
    """Find the best leader portrait for a civ."""
    leaders_dir = BASE / "art" / "ui" / "leaders"

    # Try the named leaders for this civ
    candidates = CIV_TO_LEADER.get(civ_token, [])
    for stem in candidates:
        for ext in [".png", ".jpg", ".jpeg"]:
            p = leaders_dir / (stem + ext)
            if p.exists():
                return p

    # Fall back: use the cpai_avatar preview from civmods (that image shows the leader)
    if preview_wpf:
        p = resolve_path(preview_wpf)
        if p and p.exists():
            return p

    # Last resort: look for any leader file containing a known keyword
    token_lower = civ_token.lower().replace("anw", "")
    for f in leaders_dir.iterdir():
        if token_lower in f.stem.lower():
            return f
    return None

def parse_civmods():
    """Parse civmods.xml and return list of civ dicts."""
    tree = ET.parse(CIVMODS)
    root = tree.getroot()
    civs = []
    for civ_el in root.findall("civ"):
        name_el = civ_el.find("name")
        if name_el is None or not (name_el.text or "").startswith("ANW"):
            continue
        token = name_el.text.strip()

        # Display name: derive from token (pretty-print)
        display = token.replace("ANW", "").replace("NapoleonicFrance", "Napoleonic France").replace("RevFrance", "Rev. France")
        # Insert space before uppercase letters run
        import re
        display = re.sub(r'([a-z])([A-Z])', r'\1 \2', display)

        hcfile = civ_el.findtext("homecityfilename", "")
        flag_icon = civ_el.findtext("homecityflagiconwpf", "") or civ_el.findtext("postgameflagiconwpf", "")
        postgame_flag = civ_el.findtext("postgameflagiconwpf", "")
        preview_wpf = civ_el.findtext("homecitypreviewwpf", "")

        civs.append({
            "token": token,
            "display": display,
            "homecityfilename": hcfile,
            "flag_icon_wpf": flag_icon,
            "postgame_flag_wpf": postgame_flag,
            "homecitypreview_wpf": preview_wpf,
        })
    return civs

def find_hc_flag(token: str) -> Path | None:
    """Find home-city flag icon (flag_hc_* files in resources/images/icons/flags/)."""
    flags_dir = BASE / "resources" / "images" / "icons" / "flags"
    token_lower = token.lower().replace("anw", "")
    # Try common patterns
    patterns = [
        f"flag_hc_{token_lower}.png",
    ]
    # Also try known abbreviations
    abbrevs = {
        "haudenosaunee": "iroquois",
        "revfrance": "french_revolution",
        "napoleonicfrance": "french_revolution_ne",
        "indians": "indian",
        "southafricans": "south_african",
        "ethiopians": "ethiopian",
        "italians": "italian",
        "maltese": "maltese_cross",
        "canadians": "canadian",
        "mexicans": "mexican",
        "ottomans": "ottoman",
        "russians": "russian",
        "portuguese": "portuguese",
        "brazilians": "brazilian",
        "brazil": "brazilian",
        "argentines": "argentinian",
        "columbians": "colombian",
        "peruvians": "peruvian",
        "chileans": "chilean",
        "haitians": "haitian",
        "egyptians": "egyptian",
        "barbary": "barbary",
        "hausa": "hausa",
        "indonesians": "indonesian",
        "hungarians": "hungarian",
        "romanians": "romanian",
        "finnish": "finnish",
        "swedes": "swedish",
        "lakota": "sioux",
        "texians": "texan",
        "usa": "american",
        "mayans": "mayan",
    }
    if token_lower in abbrevs:
        patterns.insert(0, f"flag_hc_{abbrevs[token_lower]}.png")

    for p in patterns:
        candidate = flags_dir / p
        if candidate.exists():
            return candidate

    # Fuzzy: look for any flag_hc_ file containing the token
    for f in flags_dir.iterdir():
        if f.name.startswith("flag_hc_") and token_lower in f.name.lower():
            return f
    return None

def find_deck_card_back(token: str) -> Path | None:
    """Look for civ-specific deck card back icon."""
    cards_dir = BASE / "resources" / "images" / "icons" / "cards"
    token_lower = token.lower().replace("anw", "")
    for f in cards_dir.iterdir():
        if ("deck" in f.name.lower() or "card_back" in f.name.lower()) and token_lower in f.name.lower():
            return f
    return None

def check_synth_manifest(token: str) -> dict:
    """Check if there's a synthesised manifest for this civ."""
    civ_dir = BASE / "artifacts" / "validation" / "visual_art" / token
    manifest_path = civ_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        with open(manifest_path) as f:
            return json.load(f)
    except Exception:
        return {}

def get_synth_crop(manifest: dict, crop_name: str) -> Path | None:
    """Extract a specific crop path from a synthesised manifest."""
    civ_dir = BASE / "artifacts" / "validation" / "visual_art" / manifest.get("civ_token", "")
    for capture in manifest.get("captures", []):
        for crop in capture.get("crops", []):
            if crop.get("name") == crop_name:
                # Prefer thumb (webp), fall back to png
                thumb = crop.get("thumb_path")
                if thumb:
                    p = civ_dir / thumb
                    if p.exists():
                        return p
                crop_p = crop.get("crop_path")
                if crop_p:
                    p = civ_dir / crop_p
                    if p.exists():
                        return p
    return None

def main():
    civs = parse_civmods()
    print(f"Parsed {len(civs)} civs from civmods.xml")

    inventory = []
    stats = {
        "lobby_portrait": 0,
        "loading_flag": 0,
        "home_city_preview": 0,
        "leader_portrait": 0,
        "hc_flag": 0,
        "deck_card_back": 0,
    }

    rows = []
    for civ in civs:
        token = civ["token"]
        manifest = check_synth_manifest(token)

        # --- lobby_portrait ---
        lobby_portrait = None
        # 1. Try synth manifest crop
        if manifest:
            lobby_portrait = get_synth_crop(manifest, "lobby_portrait")
        # 2. Fall back to cpai_avatar preview image from civmods
        if lobby_portrait is None and civ["homecitypreview_wpf"]:
            lobby_portrait = resolve_path(civ["homecitypreview_wpf"])
        # 3. Try anw-prefixed cpai_avatar file
        if lobby_portrait is None:
            token_lower = token.lower()
            p = BASE / "resources" / "images" / "icons" / "singleplayer" / f"cpai_avatar_{token_lower}.png"
            if p.exists():
                lobby_portrait = p

        # --- loading_flag ---
        loading_flag = None
        if manifest:
            loading_flag = get_synth_crop(manifest, "loading_flag")
        if loading_flag is None and civ["flag_icon_wpf"]:
            loading_flag = resolve_path(civ["flag_icon_wpf"])

        # --- home_city_preview (the lobby avatar that corresponds to home city) ---
        home_city = None
        if manifest:
            home_city = get_synth_crop(manifest, "home_city_scene")
        if home_city is None and civ["homecitypreview_wpf"]:
            home_city = resolve_path(civ["homecitypreview_wpf"])

        # --- leader_portrait ---
        leader_portrait = find_leader_portrait(token, civ["homecitypreview_wpf"])

        # --- hc_flag (home city button flag) ---
        hc_flag = None
        if manifest:
            hc_flag = get_synth_crop(manifest, "home_city_button")
        if hc_flag is None:
            hc_flag = find_hc_flag(token)

        # --- deck_card_back ---
        deck_card_back = find_deck_card_back(token)

        # --- postgame / endgame flag ---
        postgame_flag = None
        if manifest:
            postgame_flag = get_synth_crop(manifest, "endgame_flag")
        if postgame_flag is None and civ["postgame_flag_wpf"]:
            postgame_flag = resolve_path(civ["postgame_flag_wpf"])

        # Stats
        if lobby_portrait: stats["lobby_portrait"] += 1
        if loading_flag: stats["loading_flag"] += 1
        if home_city: stats["home_city_preview"] += 1
        if leader_portrait: stats["leader_portrait"] += 1
        if hc_flag: stats["hc_flag"] += 1
        if deck_card_back: stats["deck_card_back"] += 1

        # Notes
        notes = []
        if manifest.get("synthesised"):
            notes.append("synth")
        if manifest.get("status") == "complete":
            notes.append("runtime-ok")

        rows.append({
            "token": token,
            "display": civ["display"],
            "lobby_portrait": lobby_portrait,
            "loading_flag": loading_flag,
            "home_city": home_city,
            "leader_portrait": leader_portrait,
            "hc_flag": hc_flag,
            "deck_card_back": deck_card_back,
            "postgame_flag": postgame_flag,
            "notes": ", ".join(notes) if notes else "—",
        })

        inventory.append({
            "civ_token": token,
            "display_name": civ["display"],
            "lobby_portrait": str(lobby_portrait) if lobby_portrait else None,
            "loading_flag": str(loading_flag) if loading_flag else None,
            "home_city_preview": str(home_city) if home_city else None,
            "leader_portrait": str(leader_portrait) if leader_portrait else None,
            "hc_flag": str(hc_flag) if hc_flag else None,
            "deck_card_back": str(deck_card_back) if deck_card_back else None,
            "postgame_flag": str(postgame_flag) if postgame_flag else None,
            "has_manifest": bool(manifest),
            "manifest_status": manifest.get("status", "none"),
        })

    total = len(civs)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ANW Art Contact Sheet — v1.0 Release Readiness</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 12px; background: #1a1a2e; color: #e0e0e0; }}
  h1 {{ margin: 0 0 4px 0; color: #f0c040; font-size: 1.4em; }}
  .meta {{ color: #aaa; font-size: 0.85em; margin-bottom: 10px; }}
  .summary-bar {{ background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 10px 16px; margin-bottom: 14px; display: flex; flex-wrap: wrap; gap: 16px; }}
  .summary-item {{ font-size: 0.85em; }}
  .summary-item span.count {{ font-weight: bold; color: #4fc3f7; }}
  .summary-item span.total {{ color: #888; }}
  .summary-item.warn span.count {{ color: #ff8a65; }}

  table {{ border-collapse: collapse; width: 100%; font-size: 0.8em; }}
  thead tr {{ background: #0f3460; position: sticky; top: 0; z-index: 10; }}
  thead th {{ padding: 8px 6px; text-align: left; color: #4fc3f7; font-size: 0.85em; border-bottom: 2px solid #4fc3f7; white-space: nowrap; }}
  tbody tr:nth-child(even) {{ background: #16213e; }}
  tbody tr:nth-child(odd) {{ background: #1a1a2e; }}
  tbody tr:hover {{ background: #0f3460; }}
  td {{ padding: 6px 6px; vertical-align: middle; border-bottom: 1px solid #2a2a4e; }}
  td.token {{ font-family: monospace; font-size: 0.78em; color: #90caf9; white-space: nowrap; }}
  td.display {{ font-weight: 600; white-space: nowrap; }}
  td.notes {{ font-family: monospace; font-size: 0.75em; color: #b0bec5; }}

  img {{ max-width: 160px; max-height: 100px; object-fit: contain; display: block; background: #0a0a1a; border: 1px solid #2a2a4e; border-radius: 3px; }}
  img:hover {{ border-color: #4fc3f7; }}

  .missing {{ background: #7f0000; color: #ffcdd2; padding: 3px 7px; border-radius: 3px; font-size: 0.8em; font-weight: bold; display: inline-block; }}
  .badge {{ background: #4a148c; color: #e1bee7; padding: 2px 5px; border-radius: 3px; font-size: 0.75em; font-weight: bold; margin-right: 3px; }}
  .path-link {{ color: #b39ddb; font-family: monospace; font-size: 0.8em; word-break: break-all; }}
  a {{ color: inherit; text-decoration: none; }}
  a:hover img {{ opacity: 0.85; }}

  footer {{ margin-top: 20px; color: #666; font-size: 0.78em; font-family: monospace; border-top: 1px solid #2a2a4e; padding-top: 8px; }}
</style>
</head>
<body>
<h1>ANW Art Contact Sheet — v1.0 Release Readiness</h1>
<div class="meta">Generated: {GENERATED_DATE} &nbsp;|&nbsp; Source: {str(CIVMODS)} &nbsp;|&nbsp; Civs: {total}</div>

<div class="summary-bar">
"""

    for key, label in [
        ("lobby_portrait", "Lobby Portrait"),
        ("loading_flag", "Loading Flag"),
        ("home_city_preview", "Home City Preview"),
        ("leader_portrait", "Leader Portrait"),
        ("hc_flag", "HC Flag"),
        ("deck_card_back", "Deck Card Back"),
    ]:
        count = stats[key]
        warn_class = " warn" if count < total else ""
        html += f'  <div class="summary-item{warn_class}"><span class="count">{count}</span><span class="total">/{total}</span> {label}</div>\n'

    html += """</div>

<table>
<thead>
<tr>
  <th>#</th>
  <th>Token</th>
  <th>Display Name</th>
  <th>Lobby Portrait<br><small>(cpai_avatar)</small></th>
  <th>Loading Flag<br><small>(flag icon)</small></th>
  <th>Home City<br><small>(preview)</small></th>
  <th>Leader Portrait<br><small>(art/ui/leaders)</small></th>
  <th>HC Flag<br><small>(flag_hc_*)</small></th>
  <th>Deck Card Back</th>
  <th>Notes</th>
</tr>
</thead>
<tbody>
"""

    for i, row in enumerate(rows, 1):
        html += f"""<tr>
  <td>{i}</td>
  <td class="token">{row['token']}</td>
  <td class="display">{row['display']}</td>
  <td>{img_or_path(row['lobby_portrait'], 'lobby_portrait')}</td>
  <td>{img_or_path(row['loading_flag'], 'loading_flag')}</td>
  <td>{img_or_path(row['home_city'], 'home_city')}</td>
  <td>{img_or_path(row['leader_portrait'], 'leader_portrait')}</td>
  <td>{img_or_path(row['hc_flag'], 'hc_flag')}</td>
  <td>{img_or_path(row['deck_card_back'], 'deck_card_back')}</td>
  <td class="notes">{row['notes']}</td>
</tr>
"""

    html += f"""</tbody>
</table>

<footer>
ANW mod path: {BASE}<br>
Columns: lobby_portrait={stats['lobby_portrait']}/{total} | loading_flag={stats['loading_flag']}/{total} | home_city_preview={stats['home_city_preview']}/{total} | leader_portrait={stats['leader_portrait']}/{total} | hc_flag={stats['hc_flag']}/{total} | deck_card_back={stats['deck_card_back']}/{total}<br>
DDT/BTX assets cannot be previewed in browser — they appear as path links with format badges. Verify in-engine.<br>
Generated by tools/generate_contact_sheet.py on {GENERATED_DATE}
</footer>
</body>
</html>
"""

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML written: {OUT_HTML}")

    OUT_JSON.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON written: {OUT_JSON}")

    print("\n=== SUMMARY ===")
    for key, label in [
        ("lobby_portrait", "Lobby Portrait"),
        ("loading_flag", "Loading Flag"),
        ("home_city_preview", "Home City Preview"),
        ("leader_portrait", "Leader Portrait"),
        ("hc_flag", "HC Flag"),
        ("deck_card_back", "Deck Card Back"),
    ]:
        print(f"  {label}: {stats[key]}/{total}")

    # Report missing
    print("\n=== MISSING SURFACES ===")
    for row in rows:
        missing = []
        if not row['lobby_portrait']: missing.append("lobby_portrait")
        if not row['loading_flag']: missing.append("loading_flag")
        if not row['home_city']: missing.append("home_city")
        if not row['leader_portrait']: missing.append("leader_portrait")
        if not row['hc_flag']: missing.append("hc_flag")
        if missing:
            print(f"  {row['token']}: {', '.join(missing)}")

if __name__ == "__main__":
    main()
