#!/usr/bin/env python3
"""
audit_civ_correctness.py — Per-civ heuristic correctness auditor for the ANW mod.

Checks every civ returned by get_civ_order() against a keyword table, art-path
existence, and string/display-name sanity.

Outputs:
  artifacts/validation/civ_correctness/findings.json
  artifacts/validation/civ_correctness/report.md
  Console summary

Exit 0 if no FAIL; exit 1 if any FAIL.
"""

import os, sys, re, json, datetime, xml.etree.ElementTree as ET

# ── Path setup ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR  = os.path.dirname(SCRIPT_DIR)
MOD_ROOT   = os.path.dirname(TOOLS_DIR)

sys.path.insert(0, TOOLS_DIR)
from build_civ_columns import (
    load_strings, load_strings_by_civ, load_civmods, get_civ_order, blurb_key,
    DATA_DIR, RESOURCES,
)

OUTPUT_DIR = os.path.join(MOD_ROOT, "artifacts", "validation", "civ_correctness")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VANILLA_BAR_PATH = "/tmp/vanilla_bar_inventory.txt"

# ── Known-safe paths (shared revolution/UI assets that should never FAIL) ──────
# These patterns in a path make Check 2 treat the asset as shared/generic.
SHARED_PATTERNS = re.compile(
    r"(shared|generic|default|placeholder|revolution_hall|bunting_white"
    r"|pregame_bg|lobby_bg|ui_overlay|common_flag|common_btn"
    r"|homecity[/\\]revolution[/\\](?!.*[a-z]{3,}))",  # revolution/ without a country suffix
    re.IGNORECASE,
)

# Vanilla homecity scene directory names — any path starting with one of these
# is a vanilla .bar asset and should never appear on mod disk.
VANILLA_HC_DIRS = frozenset([
    "french", "british", "spanish", "portuguese", "dutch", "russian",
    "german", "ottoman", "mexico", "aztec", "inca", "iroquois", "sioux",
    "china", "japan", "india", "italy", "malta", "swedish", "american",
    "ethiopia", "hausa",
])

# Explicit path substrings that are known-safe cross-civ (e.g. base flag textures
# that many revolution civs share with their parent civ).
KNOWN_SAFE_PATHS: set[str] = {
    # Parent-civ flag textures borrowed by revolution civs (vanilla .bar assets)
    "objects/flags/spanish",
    "objects/flags/french",
    "objects/flags/british",
    "objects/flags/portuguese",
    "objects/flags/dutch",
    "objects/flags/russian",
    "objects/flags/ottoman",
    "objects/flags/german",
    "objects/flags/french_revolution_ne",  # shared between NapoleonicFrance and RevFrance
    # Postgame flag textures (vanilla .bar)
    "ui/ingame/ingame_ui_postgame_flag_french",
    "ui/ingame/ingame_ui_postgame_flag_british",
    "ui/ingame/ingame_ui_postgame_flag_spanish",
    "ui/ingame/ingame_ui_postgame_flag_portuguese",
    "ui/ingame/ingame_ui_postgame_flag_dutch",
    "ui/ingame/ingame_ui_postgame_flag_russian",
    "ui/ingame/ingame_ui_postgame_flag_german",
    "ui/ingame/ingame_ui_postgame_flag_ottoman",
    "ui/ingame/ingame_ui_postgame_flag_chinese",
    "ui/ingame/ingame_ui_postgame_flag_japanese",
    "ui/ingame/ingame_ui_postgame_flag_mexican",  # mesoamerican civs share this
    "ui/ingame/ingame_ui_postgame_flag_aztec",    # DEInca / ANWMayans share aztec post-game
    "ui/ingame/ingame_ui_postgame_flag_usa",
    "ui/ingame/ingame_ui_postgame_flag_iroquois",
    "ui/ingame/ingame_ui_postgame_flag_sioux",
    "ui/ingame/ingame_ui_postgame_flag_indian",
    "ui/ingame/ingame_ui_postgame_flag_aztec",
    # Homecity scene files — revolution civs intentionally inherit parent HC
    # These are ALL vanilla .bar assets, never in the mod's disk tree.
    "french/french_homecity",
    "french/french_background",
    "british/british_homecity",
    "british/british_background",
    "spanish/spanish_homecity",
    "spanish/spanish_background",
    "portuguese/portuguese_homecity",
    "portuguese/portuguese_background",
    "dutch/dutch_homecity",
    "dutch/dutch_background",
    "russian/russian_homecity",
    "russian/russian_background",
    "german/german_homecity",
    "german/german_background",
    "ottoman/ottoman_homecity",
    "ottoman/ottoman_background",
    "mexico/mexico_homecity",
    "mexico/mexico_background",
    "mexico/pathable_area",
    "aztec/aztec_homecity",
    "aztec/aztec_background",
    "inca/inca_homecity",
    "inca/inca_background",
    "iroquois/iroquois_homecity",
    "iroquois/iroquois_background",
    "sioux/sioux_homecity",
    "sioux/sioux_background",
    "china/china_homecity",
    "china/china_background",
    "japan/japan_homecity",
    "japan/japan_background",
    "india/india_homecity",
    "india/india_background",
    "italy/italy_homecity",
    "italy/italy_background",
    "malta/malta_homecity",
    "malta/malta_background",
    "swedish/swedish_homecity",
    "swedish/swedish_background",
    "american/american_homecity",
    "american/american_background",
    "ethiopia/ethiopia_homecity",
    "ethiopia/ethiopia_background",
    "hausa/hausa_homecity",
    "hausa/hausa_background",
    # Misc vanilla assets
    "hc_revolution",
    "revolutionambientsounds",
    "generic_city",
    "homecitygatherflag",
    "pathable_area_object",
    "pathable_area",
}

# ── Per-civ keyword table ───────────────────────────────────────────────────────
# Revolution civs — explicit keywords
CIV_KEYWORDS: dict[str, list[str]] = {
    "ANWArgentines":       ["argent", "san_martin", "granadero", "pampas", "patagonia"],
    "ANWBarbary":          ["barbary", "moroccan", "moros", "omani", "barbarossa", "saharan", "magrib"],
    "ANWBrazil":           ["brazil", "amazon", "pedro", "orinoco", "rio_de_janeiro",
                            "rio_grande"],  # Rio Grande river is in southern Brazil
    # Canadians historically shared the Saint Lawrence with the Iroquois
    # Confederacy, but the Iroquois branded art (flag_iroquois.png et al.)
    # belongs to ANWHaudenosaunee — the standalone Haudenosaunee civ owns
    # that namespace, not ANWCanadians. Do not put "iroquois" here or the
    # ownership audit will mis-attribute the Haudenosaunee flag set.
    "ANWCanadians":        ["canad", "brock", "papineau", "metis", "voyageur", "ranger",
                            "congreve", "lower_canada", "patriote", "ottawa", "quebec",
                            "montreal", "saguenay", "yukon", "great_lakes"],
    "ANWHaudenosaunee":    ["haudenosaunee", "iroquois", "mohawk", "onondaga", "seneca",
                            "oneida", "cayuga", "tuscarora", "longhouse", "tomahawk",
                            "kanienkehaka"],
    "ANWInca":             ["inca", "pachacuti", "huascar", "quechua", "cusco",
                            "chasqui", "macuahuitl", "huayna", "qhapaq"],
    "ANWChileans":         ["chile", "ohiggins", "araucan", "andean"],
    "ANWColumbians":       ["colombi", "columbia", "coumbia", "bolivar", "orinoco"],
    "ANWEgyptians":        ["egypt", "muhammad_ali", "nile", "alexandria", "mamluk", "cairo"],
    "ANWFinnish":          ["finn", "karelian", "mannerheim", "sami", "siberia"],
    "ANWHaitians":         ["haiti", "louverture", "padre_revolution", "hispaniola", "voodoo"],
    "ANWHungarians":       ["hungar", "hajduk", "kossuth", "magyar", "eurasian_steppe"],
    "ANWIndonesians":      ["indones", "cetbang", "java", "diponegoro", "indochina", "batavia", "ceylon"],
    "ANWMayans":           ["mayan", "cruzob", "canek", "yucatan", "everglades", "jaguar"],
    "ANWNapoleonicFrance": ["french_revolution_ne", "revolution_ne", "noble_class_french",
                            "napoleon", "imperial_guard", "grenadier", "napoleonic",
                            "france", "french"],  # display name "France (Napoleonic Era)" is correct
    # Peruvians is the post-Inca revolutionary state led by Andrés de
    # Santa Cruz — Pachacuti (the Inca emperor) and Cusco (Inca capital)
    # are historically Inca, not Peruvian-revolutionary. Don't claim those
    # keywords here or the ownership audit will mis-attribute Inca art.
    "ANWPeruvians":        ["peru", "llama", "andean", "santa_cruz"],
    "ANWRevFrance":        ["french_revolution", "noble_class_french", "robespierre",
                            "sansculotte", "marseillaise", "revolutionary_france", "revfrance",
                            "france", "french"],  # display name "France" is correct
    "ANWRioGrande":        ["rio_grande", "riograndense", "riogrande", "canales", "rosillo",
                            "tamaulipas", "northern_mexico", "norteno", "frontier_republic"],
    "ANWRomanians":        ["romanian", "dorobant", "rosior", "cuza", "wallach",
                            "death_hussar", "eurasian_steppe"],
    "ANWSouthAfricans":    ["south_afric", "kruger", "boer", "zulu", "transvaal", "voortrekker", "southafrican"],
    "ANWTexians":          ["texan", "texas", "sam_houston", "great_plains", "alamo", "carolina", "texian"],
}

# Base-game civs — generate from token name, plus curated extras
_BASE_CIV_EXTRA: dict[str, list[str]] = {
    "French":      ["french", "france", "bourbon"],
    "British":     ["british", "england", "britain", "redcoat"],
    "Germans":     ["german", "prussian", "frederick", "bismarck", "hessian"],
    "Russians":    ["russian", "russia", "cossack", "strelet"],
    "Spanish":     ["spanish", "spain", "conquistador", "rodelero"],
    "Ottomans":    ["ottoman", "janissary", "abus", "sipahi"],
    "Portuguese":  ["portugu", "cassador", "dragoon"],
    "Dutch":       ["dutch", "holland", "fluyt", "ruyter"],
    "DEItalians":  ["italian", "italy", "papal", "bersaglier"],
    "DEMaltese":   ["maltes", "malta", "hospitaller", "cavalier"],
    "DESwedish":   ["swedish", "sweden", "carolus", "carolean", "hakkapelit"],
    "Chinese":     ["chinese", "china", "porcelain", "banner"],
    "Japanese":    ["japan", "samurai", "shogun", "daimyo", "ashigaru"],
    "Indians":     ["indian", "india", "gurkha", "rajput", "zamburak"],
    "XPAztec":     ["aztec", "jaguar", "eagle_warrior"],
    "XPIroquois":  ["iroquois", "haudenosaunee", "mohawk", "onondaga", "seneca"],
    "DEInca":      ["inca", "peru", "chasqui", "huascar"],
    "XPSioux":     ["sioux", "lakota", "tashunke", "dog_soldier"],
    "DEAmericans": ["american", "usa", "united_states", "minuteman", "jefferson", "washington"],
    "DEMexicans":  ["mexican", "mexico", "insurgent", "soldado", "rurales"],
    "DEEthiopians":["ethiopian", "ethiopia", "shotel", "neftenya"],
    "DEHausa":     ["hausa", "fulani", "makama", "maigadi"],
}

def _make_base_keywords(token: str) -> list[str]:
    """Generate keyword list for a base-game civ token."""
    extra = _BASE_CIV_EXTRA.get(token, [])
    # Derive a stem from the token (strip DE/XP prefix)
    stem = token.lower()
    for pf in ("de", "xp"):
        if stem.startswith(pf):
            stem = stem[len(pf):]
            break
    result = [stem] + [k for k in extra if k != stem]
    return result

def build_full_keyword_table(civ_order: list[str]) -> dict[str, list[str]]:
    table: dict[str, list[str]] = {}
    for tok in civ_order:
        anw_tok = blurb_key(tok)  # normalise to ANWXxx
        if anw_tok in CIV_KEYWORDS:
            table[tok] = CIV_KEYWORDS[anw_tok]
        elif tok in CIV_KEYWORDS:
            table[tok] = CIV_KEYWORDS[tok]
        else:
            table[tok] = _make_base_keywords(tok)
    return table

# ── Civ-label substrings used for string cross-civ detection ───────────────────
CIV_LABELS: dict[str, list[str]] = {
    "British":     ["british", "england"],
    "French":      ["french", "france"],
    "Germans":     ["german", "prussian"],
    "Russians":    ["russian"],
    "Spanish":     ["spanish", "spain"],
    "Ottomans":    ["ottoman"],
    "Portuguese":  ["portuguese"],
    "Dutch":       ["dutch"],
    "DEItalians":  ["italian"],
    "DEMaltese":   ["maltese"],
    "DESwedish":   ["swedish"],
    "Chinese":     ["chinese"],
    "Japanese":    ["japanese"],
    "Indians":     ["indian"],
    "XPAztec":     ["aztec"],
    "XPIroquois":  ["iroquois", "haudenosaunee"],
    "DEInca":      ["inca"],
    "XPSioux":     ["sioux", "lakota"],
    "DEAmericans": ["american"],
    "DEMexicans":  ["mexican"],
    "DEEthiopians":["ethiopian"],
    "DEHausa":     ["hausa"],
    "ANWArgentines":    ["argentin"],
    "ANWBarbary":       ["barbary"],
    "ANWBrazil":        ["brazil"],
    "ANWCanadians":     ["canadian"],
    "ANWChileans":      ["chilean"],
    "ANWColumbians":    ["colombian", "columbian"],
    "ANWEgyptians":     ["egyptian"],
    "ANWFinnish":       ["finnish", "finn"],
    "ANWHaitians":      ["haitian"],
    "ANWHungarians":    ["hungarian"],
    "ANWIndonesians":   ["indonesian"],
    "ANWMayans":        ["mayan"],
    "ANWNapoleonicFrance": ["napoleonic"],
    "ANWPeruvians":     ["peruvian"],
    "ANWRevFrance":     ["revolutionary france", "revolution france"],
    "ANWRomanians":     ["romanian"],
    "ANWSouthAfricans": ["south african"],
    "ANWTexians":       ["texian", "texan"],
}

# Shared vanilla diplomacy string IDs — all civs point to these, they live in
# the base game string archives, not in stringmods.xml, so we silently skip them.
VANILLA_SHARED_LOC_IDS: frozenset[str] = frozenset(["26444", "26445", "26446"])

# Words indicating diplomatic/historical context (allow foreign civ name mentions)
DIPLOMATIC_WORDS = re.compile(
    r"\b(ally|allies|allied|war with|trade|history|historical|enemy|enemies"
    r"|treaty|diplomacy|fought|battled|campaign|against|defeated|victory over)\b",
    re.IGNORECASE,
)

# ── Art path extraction helpers ─────────────────────────────────────────────────
# Mirror the _is_art / _is_art_tag predicates used in Section K of build_civ_columns.py
# so that the audit covers the exact same surface shown to the user.
_ART_SUFFIXES = ('.png', '.ddt', '.gr2', '.tga', '.xml', '.wpf', '.xaml',
                 '.jpg', '.jpeg', '.webp', '.cam', '.xmb')

def _is_art_value(val: str) -> bool:
    """True if the value looks like an art/asset path (ends with a known extension)."""
    v = (val or "").strip().lower()
    return any(v.endswith(s) for s in _ART_SUFFIXES)

def _is_art_tag(tag: str) -> bool:
    """True if the XML tag name suggests an art field (matches Section K heuristic)."""
    t = tag.lower()
    return (t.endswith("filename") or t.endswith("texture") or
            t.endswith("icon")    or t.endswith("portrait") or
            t.endswith("wpf")     or t.endswith("visual")   or
            t.endswith("scene")   or t.endswith("music"))

def norm_path(p: str) -> str:
    """Normalise a path: backslash → slash, lowercase, strip leading slash."""
    return p.replace("\\", "/").lower().strip("/")

def extract_art_paths_from_civ(civ_elem) -> list[str]:
    """Extract all art-related path values from a civmods <civ> element.

    Uses the same heuristic as Section K in build_civ_columns.py:
    iterate every element; emit the text if the tag name is art-like OR the
    text value ends with a known art extension; also emit attribute values that
    end with a known art extension.
    """
    seen: set[str] = set()
    paths: list[str] = []

    for elem in civ_elem.iter():
        tag = elem.tag
        text = (elem.text or "").strip()
        # Emit if tag looks like art OR text looks like an art path
        if (_is_art_tag(tag) or _is_art_value(text)) and text:
            p = norm_path(text)
            if p and p not in seen:
                seen.add(p)
                paths.append(p)
        # Emit attribute values that look like art paths
        for _attr, val in elem.attrib.items():
            if _is_art_value(val):
                p = norm_path(val)
                if p and p not in seen:
                    seen.add(p)
                    paths.append(p)

    return paths

def extract_art_paths_from_homecity(hc_path: str) -> list[str]:
    """Extract all art/asset paths from a homecity XML file.

    Mirrors Section K exactly: walk every element in the tree, emit text that
    looks like an art path OR whose tag name is art-like, plus attribute values
    that look like art paths.  Returns a de-duplicated list.
    """
    if not os.path.exists(hc_path):
        return []
    try:
        tree = ET.parse(hc_path)
    except ET.ParseError:
        return []
    root = tree.getroot()
    seen: set[str] = set()
    paths: list[str] = []

    for elem in root.iter():
        tag = elem.tag
        text = (elem.text or "").strip()
        if (_is_art_tag(tag) or _is_art_value(text)) and text:
            p = norm_path(text)
            if p and p not in seen:
                seen.add(p)
                paths.append(p)
        for _attr, val in elem.attrib.items():
            if _is_art_value(val):
                p = norm_path(val)
                if p and p not in seen:
                    seen.add(p)
                    paths.append(p)

    return paths

def path_exists_on_disk(p: str) -> bool:
    """Check if a normalised path exists under the mod root or resources."""
    candidates = [
        os.path.join(MOD_ROOT, p),
        os.path.join(RESOURCES, p),
        os.path.join(DATA_DIR, p),
    ]
    return any(os.path.exists(c) for c in candidates)

# ── Load vanilla bar inventory ──────────────────────────────────────────────────
def load_bar_inventory() -> set[str] | None:
    if not os.path.exists(VANILLA_BAR_PATH):
        return None
    inv: set[str] = set()
    with open(VANILLA_BAR_PATH, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            raw = parts[1] if len(parts) >= 2 else (parts[0].strip() if parts[0].strip() else "")
            if not raw:
                continue
            p = norm_path(raw)
            inv.add(p)
            # Also add the path with .xmb / .precomp suffixes stripped so that
            # a reference to "foo.xml" matches the bar entry "foo.xml.XMB".
            for suffix in (".xmb", ".precomp"):
                if p.endswith(suffix):
                    inv.add(p[: -len(suffix)])
    return inv

# ── Build "exclusive keyword" index (keywords only in one civ) ─────────────────
def build_exclusive_keywords(kw_table: dict[str, list[str]]) -> dict[str, str]:
    """
    Returns a dict: keyword -> civ_token for keywords that appear in exactly
    one civ's keyword list.  Short keywords (< 5 chars) are excluded to avoid
    false-positives.
    """
    count: dict[str, list[str]] = {}
    for tok, kws in kw_table.items():
        for kw in kws:
            if len(kw) >= 5:
                count.setdefault(kw, []).append(tok)
    return {kw: civs[0] for kw, civs in count.items() if len(civs) == 1}

# ── Check helpers ───────────────────────────────────────────────────────────────
def is_shared_path(p: str) -> bool:
    """True if the path looks like a shared/generic revolution asset."""
    if SHARED_PATTERNS.search(p):
        return True
    for safe in KNOWN_SAFE_PATHS:
        # Match if path starts with the safe prefix, equals it, or contains it
        if p == safe or p.startswith(safe + "/") or p.startswith(safe + ".") or safe in p:
            return True
    return False

def check_art_path_existence(civ_token: str, path: str, bar_inv: set[str] | None) -> dict | None:
    """Return a FAIL finding if the path is missing on disk and not in bar inventory."""
    # Skip abstract names (button set identifiers, light set names, etc.)
    if "/" not in path and "." not in path:
        return None
    # Skip known vanilla/shared assets (these live in .bar archives, never on mod disk)
    if is_shared_path(path):
        return None
    # Skip vanilla engine texture paths (objects/flags/*, ui/ingame/*, ui/singleplayer/*)
    # These are all .bar assets; we only check mod-specific resources here
    if path.startswith("objects/") or path.startswith("ui/"):
        return None  # vanilla .bar asset
    # Skip vanilla HC scene directories (e.g. french/, british/, italian/, american/)
    # and the homecity/ subtree (building models, icon DDTs, sound XMLs — all .bar assets)
    top_dir = path.split("/")[0] if "/" in path else ""
    if top_dir in VANILLA_HC_DIRS or top_dir == "homecity":
        return None
    # Skip vanilla homecity building XML refs (e.g. buildings_west/academy.xml) —
    # they live under ArtHomecity.bar as homecity/buildings_west/academy.xml.XMB
    if top_dir == "buildings_west":
        return None

    # Only check wpf/png/jpg/xml extensions (mod-owned paths)
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext not in ("png", "jpg", "jpeg", "xml", "ddt", "gr2", "material", "cam", "xmb"):
        # Could be a texture path without extension — still check disk
        if "/" not in path:
            return None

    if path_exists_on_disk(path):
        return None

    # Not on disk — check vanilla bar inventory
    if bar_inv is not None:
        # Check if any inventory entry ends with the basename of this path
        basename = path.rsplit("/", 1)[-1]
        if path in bar_inv or any(e.endswith(basename) for e in bar_inv):
            return None
        return {"civ": civ_token, "path": path, "kind": "missing_file"}
    else:
        # Can't verify — skip with no finding
        return None

def check_art_path_identity(civ_token: str, path: str,
                             kw_table: dict[str, list[str]],
                             exclusive_kws: dict[str, str]) -> dict | None:
    """Return a FAIL if the path contains an exclusive keyword of another civ."""
    # Skip abstract names (button set names, texture names without path separators)
    if "/" not in path and "." not in path:
        return None
    # Skip vanilla engine paths (flag textures, postgame overlays, HC scenes)
    if path.startswith("objects/") or path.startswith("ui/"):
        return None
    top_dir = path.split("/")[0] if "/" in path else ""
    if top_dir in VANILLA_HC_DIRS or top_dir in ("homecity", "buildings_west"):
        return None
    if is_shared_path(path):
        return None
    own_kws = kw_table.get(civ_token, [])
    # If path matches any own keyword → fine
    if any(kw in path for kw in own_kws):
        return None
    # Check exclusive keywords of other civs
    for kw, owner in exclusive_kws.items():
        if owner == civ_token:
            continue
        if kw in path:
            # Double-check: is this kw also in own keywords?
            if kw in own_kws:
                continue
            return {
                "civ": civ_token,
                "path": path,
                "kind": "wrong_civ_art",
                "detected_civ": owner,
                "keyword": kw,
            }
    return None

def check_string_identity(civ_token: str, loc_id: str, text: str,
                           kw_table: dict[str, list[str]]) -> dict | None:
    """Return a WARN if the string clearly names another civ (not historical context)."""
    if not text:
        return {"civ": civ_token, "locID": loc_id, "kind": "empty_string"}

    # Skip if text looks like it has a diplomatic context
    if DIPLOMATIC_WORDS.search(text):
        return None

    text_lower = text.lower()
    for other_tok, labels in CIV_LABELS.items():
        if other_tok == civ_token:
            continue
        # Also skip if this civ's keywords overlap with the other's labels
        own_kws = kw_table.get(civ_token, [])
        for label in labels:
            if len(label) < 7:  # short labels (≤6 chars) generate too many false positives
                continue
            # Use word-boundary matching to avoid "Mexicana" → "mexican", "Frances" → "france"
            if not re.search(r'\b' + re.escape(label) + r'\b', text_lower):
                continue
            # Check if any own keyword also matches (shared identity)
            # Normalise underscores/spaces for comparison
            label_norm = label.replace(" ", "_").replace("-", "_")
            if any(kw.replace(" ", "_") in label_norm or label_norm in kw.replace(" ", "_")
                   for kw in own_kws):
                continue
            return {
                "civ": civ_token,
                "locID": loc_id,
                "text": text[:120],
                "kind": "foreign_civ_name",
                "detected": other_tok,
            }
    return None

def check_displayname(civ_token: str, loc_id: str, field: str,
                       strings: dict[str, str],
                       kw_table: dict[str, list[str]]) -> dict | None:
    """Check displaynameid / rollovernameid resolution."""
    # Skip known shared vanilla diplomacy strings (live in base game archives)
    if loc_id in VANILLA_SHARED_LOC_IDS:
        return None
    resolved = strings.get(loc_id)
    if resolved is None:
        try:
            n = int(loc_id)
        except ValueError:
            n = 0
        if n < 100000:
            return {"civ": civ_token, "locID": loc_id, "field": field,
                    "kind": "displayname_unresolved"}
        return None  # base-game range — pass silently

    # Rollover/bio fields are leader biographical texts — they naturally mention
    # other nations (e.g. "Barbary corsair turned Ottoman admiral"). Skip them.
    if field in ("rollovernameid", "alliedid", "alliedotherid", "unalliedid"):
        return None
    # Check if resolved text strongly names another civ
    result = check_string_identity(civ_token, loc_id, resolved, kw_table)
    if result:
        result["kind"] = "displayname_wrong_civ"
        result["field"] = field
        result["severity"] = "WARN"
    return result

# ── Main audit ─────────────────────────────────────────────────────────────────
def run_audit():
    print("Loading data sources...")
    strings      = load_strings()
    strings_by_civ = load_strings_by_civ()
    civmods      = load_civmods()
    civ_order    = get_civ_order()
    bar_inv      = load_bar_inventory()

    if bar_inv is None:
        print(f"WARNING: {VANILLA_BAR_PATH} not found — Check 1 (file existence) skipped.")

    kw_table      = build_full_keyword_table(civ_order)
    exclusive_kws = build_exclusive_keywords(kw_table)

    # All findings accumulated here
    findings: list[dict] = []

    # Per-civ stats
    per_civ: dict[str, dict] = {}

    for civ_token in civ_order:
        anw_token = blurb_key(civ_token)   # ANWXxx normalised form
        civ_elem  = civmods.get(civ_token)
        if civ_elem is None:
            civ_elem = civmods.get(anw_token)

        stats = {"art_refs": 0, "strings": 0, "fail": 0, "warn": 0}
        per_civ[civ_token] = stats

        # ── Gather art paths ────────────────────────────────────────────────
        art_paths: list[str] = []
        if civ_elem is not None:
            art_paths = extract_art_paths_from_civ(civ_elem)
            # Also load homecity file paths (full Section K iteration)
            hc_fname = civ_elem.findtext("homecityfilename")
            if hc_fname:
                hc_full = os.path.join(DATA_DIR, hc_fname.strip())
                if os.path.exists(hc_full):
                    hc_paths = extract_art_paths_from_homecity(hc_full)
                    # Merge, deduplicating across civmods + homecity sources
                    existing = set(art_paths)
                    for p in hc_paths:
                        if p not in existing:
                            existing.add(p)
                            art_paths.append(p)
                else:
                    findings.append({
                        "civ": civ_token, "kind": "missing_homecity_xml",
                        "path": hc_fname.strip(), "severity": "WARN",
                    })
                    stats["warn"] += 1
        else:
            findings.append({
                "civ": civ_token, "kind": "missing_civmods_entry",
                "severity": "WARN",
            })
            stats["warn"] += 1

        stats["art_refs"] = len(art_paths)

        # ── Check 1 — Art path existence ───────────────────────────────────
        for path in art_paths:
            f = check_art_path_existence(civ_token, path, bar_inv)
            if f:
                f["severity"] = "FAIL"
                findings.append(f)
                stats["fail"] += 1

        # ── Check 2 — Civ identity in art paths ────────────────────────────
        for path in art_paths:
            f = check_art_path_identity(civ_token, path, kw_table, exclusive_kws)
            if f:
                f["severity"] = "FAIL"
                findings.append(f)
                stats["fail"] += 1

        # ── Check 3 — Civ identity in strings ──────────────────────────────
        # Try both civ_token and anw_token for string lookup
        str_entries = strings_by_civ.get(civ_token, [])
        if not str_entries and anw_token != civ_token:
            str_entries = strings_by_civ.get(anw_token, [])
        # Also try bare token (no ANW/DE/XP prefix)
        if not str_entries:
            bare = civ_token.lower()
            for pf in ("anw", "de", "xp"):
                if bare.startswith(pf):
                    bare = bare[len(pf):]
                    break
            str_entries = strings_by_civ.get(bare, [])

        stats["strings"] = len(str_entries)

        for loc_id, text in str_entries:
            if not text.strip():
                findings.append({
                    "civ": civ_token, "locID": loc_id,
                    "kind": "empty_string", "severity": "WARN",
                })
                stats["warn"] += 1
            else:
                f = check_string_identity(civ_token, loc_id, text, kw_table)
                if f:
                    f["severity"] = "WARN"
                    findings.append(f)
                    stats["warn"] += 1

        # ── Check 4 — Display names resolve ────────────────────────────────
        if civ_elem is not None:
            for field in ["displaynameid", "rollovernameid", "alliedid",
                          "alliedotherid", "unalliedid"]:
                loc_id = civ_elem.findtext(field)
                if not loc_id or not loc_id.strip():
                    continue
                f = check_displayname(civ_token, loc_id.strip(), field,
                                      strings, kw_table)
                if f:
                    sev = f.get("severity", "WARN")
                    if sev == "FAIL":
                        stats["fail"] += 1
                    else:
                        stats["warn"] += 1
                    findings.append(f)

    return findings, per_civ, kw_table

# ── Classify per-civ overall result ────────────────────────────────────────────
def civ_result(stats: dict) -> str:
    if stats["fail"] > 0:
        return "FAIL"
    if stats["warn"] > 0:
        return "WARN"
    return "PASS"

# ── Report generation ──────────────────────────────────────────────────────────
def write_report(findings: list[dict], per_civ: dict, civ_order: list[str]):
    date_str = datetime.date.today().isoformat()

    total   = len(civ_order)
    n_fail  = sum(1 for tok in civ_order if civ_result(per_civ[tok]) == "FAIL")
    n_warn  = sum(1 for tok in civ_order if civ_result(per_civ[tok]) == "WARN")
    n_pass  = total - n_fail - n_warn

    fail_findings = [f for f in findings if f.get("severity") == "FAIL"]
    warn_findings = [f for f in findings if f.get("severity") == "WARN"]

    lines = [
        f"# ANW Per-Civ Correctness Audit — {date_str}",
        "",
        f"Total civs: {total}",
        f"PASS: {n_pass} | WARN: {n_warn} | FAIL: {n_fail}",
        "",
    ]

    if fail_findings:
        lines.append("## Failures")
        lines.append("")
        fail_by_civ: dict[str, list[dict]] = {}
        for f in fail_findings:
            fail_by_civ.setdefault(f["civ"], []).append(f)
        for civ_tok in civ_order:
            if civ_tok not in fail_by_civ:
                continue
            lines.append(f"### {civ_tok}")
            for f in fail_by_civ[civ_tok]:
                kind = f.get("kind", "?")
                if kind == "missing_file":
                    lines.append(f"- **missing_file**: `{f['path']}`")
                elif kind == "wrong_civ_art":
                    lines.append(
                        f"- **wrong_civ_art**: `{f['path']}` "
                        f"matches {f['detected_civ']} keyword `{f['keyword']}`"
                    )
                elif kind == "displayname_unresolved":
                    lines.append(
                        f"- **displayname_unresolved**: field `{f.get('field','')}` "
                        f"locID {f['locID']} not found in stringmods"
                    )
                else:
                    lines.append(f"- **{kind}**: {json.dumps({k:v for k,v in f.items() if k not in ('civ','kind','severity')})}")
            lines.append("")
    else:
        lines += ["## Failures", "", "*(none)*", ""]

    if warn_findings:
        lines.append("## Warnings")
        lines.append("")
        warn_by_civ: dict[str, list[dict]] = {}
        for f in warn_findings:
            warn_by_civ.setdefault(f["civ"], []).append(f)
        for civ_tok in civ_order:
            if civ_tok not in warn_by_civ:
                continue
            lines.append(f"### {civ_tok}")
            for f in warn_by_civ[civ_tok]:
                kind = f.get("kind", "?")
                if kind == "empty_string":
                    lines.append(f"- **empty_string**: locID {f['locID']}")
                elif kind == "foreign_civ_name":
                    lines.append(
                        f"- **foreign_civ_name**: locID {f['locID']} "
                        f"mentions `{f['detected']}` — text: _{f.get('text','')[:80]}_"
                    )
                elif kind == "displayname_wrong_civ":
                    lines.append(
                        f"- **displayname_wrong_civ**: field `{f.get('field','')}` "
                        f"locID {f['locID']} mentions `{f.get('detected','?')}` — "
                        f"text: _{f.get('text','')[:80]}_"
                    )
                elif kind == "missing_homecity_xml":
                    lines.append(f"- **missing_homecity_xml**: `{f.get('path','?')}`")
                elif kind == "missing_civmods_entry":
                    lines.append("- **missing_civmods_entry**: civ not found in civmods.xml")
                else:
                    lines.append(f"- **{kind}**: {json.dumps({k:v for k,v in f.items() if k not in ('civ','kind','severity')})}")
            lines.append("")
    else:
        lines += ["## Warnings", "", "*(none)*", ""]

    # Per-civ summary table
    lines += ["## Per-civ summary", ""]
    lines.append("| Civ | Result | Art refs | Strings | FAIL | WARN |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for tok in civ_order:
        s = per_civ[tok]
        r = civ_result(s)
        lines.append(
            f"| {tok} | {r} | {s['art_refs']} | {s['strings']} "
            f"| {s['fail']} | {s['warn']} |"
        )

    report_path = os.path.join(OUTPUT_DIR, "report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Report written: {report_path}")
    return report_path

def write_findings_json(findings: list[dict]):
    out_path = os.path.join(OUTPUT_DIR, "findings.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    print(f"Findings JSON written: {out_path}")

# ── Console summary ────────────────────────────────────────────────────────────
def print_summary(findings: list[dict], per_civ: dict, civ_order: list[str]):
    from collections import Counter

    fail_findings = [f for f in findings if f.get("severity") == "FAIL"]
    warn_findings = [f for f in findings if f.get("severity") == "WARN"]

    n_fail = sum(1 for tok in civ_order if civ_result(per_civ[tok]) == "FAIL")
    n_warn = sum(1 for tok in civ_order if civ_result(per_civ[tok]) == "WARN")
    n_pass = len(civ_order) - n_fail - n_warn

    print("\n" + "=" * 60)
    print(f"AUDIT SUMMARY — {len(civ_order)} civs")
    print(f"  PASS: {n_pass}  WARN: {n_warn}  FAIL: {n_fail}")
    print("=" * 60)

    if fail_findings:
        print(f"\nFAIL findings ({len(fail_findings)} total):")
        kind_count = Counter(f["kind"] for f in fail_findings)
        for kind, cnt in kind_count.most_common(5):
            print(f"  {cnt:3d}  {kind}")
        print("\nAll FAIL rows:")
        for f in fail_findings:
            civ = f["civ"]
            kind = f["kind"]
            path = f.get("path", "")
            det  = f.get("detected_civ", f.get("detected", ""))
            kw   = f.get("keyword", "")
            if kind == "missing_file":
                print(f"  [{civ}] MISSING FILE: {path}")
            elif kind == "wrong_civ_art":
                print(f"  [{civ}] WRONG CIV ART: {path}  (kw={kw}, owner={det})")
            else:
                print(f"  [{civ}] {kind}: {path or f.get('locID','')}")
    else:
        print("\nNo FAIL findings.")

    if warn_findings:
        print(f"\nWARN findings ({len(warn_findings)} total):")
        kind_count = Counter(f["kind"] for f in warn_findings)
        for kind, cnt in kind_count.most_common(10):
            print(f"  {cnt:3d}  {kind}")

    print()

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    findings, per_civ, kw_table = run_audit()
    write_findings_json(findings)
    report_path = write_report(findings, per_civ, get_civ_order())
    print_summary(findings, per_civ, get_civ_order())

    any_fail = any(f.get("severity") == "FAIL" for f in findings)
    sys.exit(1 if any_fail else 0)
