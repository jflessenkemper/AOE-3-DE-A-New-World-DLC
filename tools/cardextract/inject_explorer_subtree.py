"""Inject per-civ "Explorer" sub-section into a_new_world.html.

Shows, for each nation, the conceptual hero (leader portrait + name + brief
note) that defines the civ's AI explorer identity. Does not alter in-engine
explorer visuals — that's a separate runtime cosmetics pass — but documents
the intended hero mapping so players know which legendary leader backs each AI
personality.

Respects the design rule: base-game French (Bourbon Restoration / Louis XVIII)
never gets Napoleonic cosmetic or cards. Napoleon is tied to
ANWNapoleonicFrance only.

Idempotent via <!-- EXPLORER-START civ -->...<!-- EXPLORER-END --> markers.
Re-running replaces prior injection.
"""
from __future__ import annotations

import html as html_esc
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HTML_PATH = REPO / "a_new_world.html"

# (section-data-name-substring, portrait-file, leader-name, blurb, explorer-note)
# - portrait-file is relative to art/ui/leaders/ (mod's own leader portraits)
# - leader-name is the display name (also used by the AI for chat/rename)
# - blurb is the one-line historical identity
# - explorer-note describes the AI's visible hero theme (and cosmetic intent)
CIVS = [
    # ------- 26 mod revolution civs -------
    ("Napoleonic France", "napoleon.jpg", "Napoleon Bonaparte",
     "Emperor of the French, Grande Armée architect.",
     "Napoleonic cosmetic (Imperial French explorer skin)."),
    ("Revolutionary France", "robespierre.png", "Maximilien Robespierre",
     "Jacobin tribune of the Committee of Public Safety.",
     "Generic French revolutionary explorer; NOT the Napoleon skin."),
    ("Americans Jefferson", "jefferson.jpg", "Thomas Jefferson",
     "Virginian statesman of the early republic.",
     "Early-republic American explorer; Washington-style skin."),
    ("Mexicans Hidalgo", "hidalgo.jpg", "Miguel Hidalgo",
     "Parish priest who sparked Mexican Independence with the Grito de Dolores.",
     "Mexican Independence-era clergyman explorer skin."),
    ("Canadians", "brock.png", "Isaac Brock",
     "Anglo-Canadian general of the War of 1812, \"Saviour of Upper Canada\".",
     "Redcoat Canadian officer (deSPCBrock proto theme)."),
    ("French Canadians", "papineau.png", "Louis-Joseph Papineau",
     "Patriote leader of the 1837 Lower Canada Rebellion.",
     "Patriote militia officer cosmetic."),
    ("Brazil", "pedro_i.png", "Pedro I",
     "First Emperor of Brazil, declared independence from Portugal (1822).",
     "Imperial Brazilian monarch in military regalia."),
    ("Argentines", "san_martin.png", "José de San Martín",
     "Liberator of Argentina, Chile, and Peru.",
     "Granadero officer (deREVSanMartin proto theme)."),
    ("Chileans", "ohiggins.png", "Bernardo O'Higgins",
     "Supreme Director of Chile, revolutionary general.",
     "Chilean Libertador cosmetic (SanMartin-lineage proto)."),
    ("Peruvians", "santa_cruz.png", "Andrés de Santa Cruz",
     "Marshal of Ayacucho, architect of the Peru–Bolivia Confederation.",
     "Andean Libertador cosmetic."),
    ("Columbians", "bolivar.png", "Simón Bolívar",
     "El Libertador, founder of Gran Colombia.",
     "Bolivar cosmetic (deREVBolivar proto theme)."),
    ("Haitians", "louverture.png", "Toussaint L'Ouverture",
     "Leader of the Haitian Revolution, the only successful slave revolt in history.",
     "Haitian revolutionary general cosmetic."),
    ("Indonesians", "diponegoro.png", "Prince Diponegoro",
     "Javanese prince who led the Java War against the Dutch East Indies.",
     "Javanese noble-warrior cosmetic (dePrince proto theme)."),
    ("South Africans", "kruger.png", "Paul Kruger",
     "President of the South African Republic, Boer War leader.",
     "Boer commando cosmetic."),
    ("Finnish", "mannerheim.png", "Carl Gustaf Emil Mannerheim",
     "Finnish field marshal and later president, architect of Finnish defense.",
     "Finnish officer cosmetic (deGeneral proto base)."),
    ("Hungarians", "kossuth.png", "Lajos Kossuth",
     "Revolutionary governor-president of Hungary during the 1848 uprising.",
     "Hungarian hussar-officer cosmetic."),
    ("Romanians", "cuza.png", "Alexandru Ioan Cuza",
     "First Domnitor of the United Principalities (Moldavia + Wallachia).",
     "Danubian prince cosmetic (dePrince proto theme)."),
    ("Barbary", "barbarossa.png", "Hayreddin Barbarossa",
     "Ottoman admiral and Barbary corsair, Pasha of Algiers.",
     "Barbary corsair captain (deREVCorsairCaptain / deSPCHayreddin proto theme)."),
    ("Egyptians", "muhammad_ali.png", "Muhammad Ali Pasha",
     "Wali of Egypt, modernizer of Egyptian military and economy.",
     "Egyptian pasha cosmetic (deEmir proto base)."),
    ("Central Americans", "morazan.png", "Francisco Morazán",
     "President of the Federal Republic of Central America, liberal reformer.",
     "Federalist officer cosmetic."),
    ("Baja Californians", "alvarado.jpg", "Juan Bautista Alvarado",
     "Californio governor of Alta California during the Mexican period.",
     "Californio ranchero officer cosmetic."),
    ("Yucatan", "carrillo_puerto.png", "Felipe Carrillo Puerto",
     "Socialist governor of Yucatán, \"Red Apostle\" of the Maya.",
     "Yucateco reformer cosmetic."),
    ("Rio Grande", "canales_rosillo.png", "Antonio Canales Rosillo",
     "Founder of the short-lived Republic of the Rio Grande (1840).",
     "Norteño cavalry officer cosmetic."),
    ("Mayans", "canek.png", "Jacinto Canek",
     "Maya rebel leader of the 1761 uprising in Yucatán.",
     "Maya insurrectionist cosmetic."),
    ("Californians", "vallejo.png", "Mariano Guadalupe Vallejo",
     "Californio military commander and later California state senator.",
     "Californio senior officer cosmetic."),
    ("Texians", "sam_houston.png", "Sam Houston",
     "Commander of the Texian army at San Jacinto, first President of Texas.",
     "Texian Republic general cosmetic (deSPCJackson proto theme)."),

    # ------- Bourbon France (base French with Louis XVIII profile) -------
    # NO Napoleonic cosmetic.
    ("French Louis XVIII Bourbon", "louis_xviii.jpg", "Louis XVIII",
     "Bourbon Restoration king, the deliberate counterpoint to Napoleon.",
     "Base-game French explorer (Voyageur line). NO Napoleonic cosmetic, "
     "NO Napoleonic cards — Bourbon restoration is anti-Napoleonic by design."),
]

EXPLORER_BLOCK_CSS = """\
.explorer-block{margin:8px 0;padding:8px 10px;background:rgba(120,85,50,.08);\
border-left:3px solid var(--accent,#c9a77a);border-radius:4px}
.explorer-block summary{cursor:pointer;font-weight:600;color:var(--accent,#c9a77a)}
.explorer-block .explorer-body{display:flex;gap:12px;align-items:center;margin-top:6px}
.explorer-block .explorer-portrait{width:72px;height:72px;object-fit:cover;\
border-radius:50%;border:2px solid var(--accent,#c9a77a);flex-shrink:0}
.explorer-block .explorer-meta{font-size:.9rem;line-height:1.3}
.explorer-block .explorer-name{font-weight:700;display:block;margin-bottom:2px}
.explorer-block .explorer-cosmetic{font-style:italic;opacity:.85;\
font-size:.85rem;display:block;margin-top:4px}
"""


def render_explorer_block(portrait: str, name: str, blurb: str, note: str) -> str:
    portrait_path = f"art/ui/leaders/{portrait}"
    return (
        "<details class=\"explorer-block\"><summary>Explorer &mdash; "
        + html_esc.escape(name)
        + "</summary>\n"
        + "<div class=\"explorer-body\">"
        + f"<img class=\"explorer-portrait\" src=\"{html_esc.escape(portrait_path)}\" alt=\"{html_esc.escape(name)} portrait\">"
        + "<div class=\"explorer-meta\">"
        + f"<span class=\"explorer-name\">{html_esc.escape(name)}</span>"
        + html_esc.escape(blurb)
        + f"<span class=\"explorer-cosmetic\">{html_esc.escape(note)}</span>"
        + "</div></div>\n"
        + "</details>"
    )


def inject() -> int:
    if not HTML_PATH.exists():
        print(f"HTML not found: {HTML_PATH}")
        return 1

    html = HTML_PATH.read_text(encoding="utf-8")

    # Ensure CSS is present exactly once.
    if ".explorer-block{" not in html:
        # Insert before </style> of the main style block, or end of <head>
        if "</style>" in html:
            html = html.replace("</style>", EXPLORER_BLOCK_CSS + "\n</style>", 1)
        else:
            html = html.replace("</head>", f"<style>{EXPLORER_BLOCK_CSS}</style>\n</head>", 1)

    injected = 0
    skipped = []
    for data_name_substr, portrait, name, blurb, note in CIVS:
        # Locate the <details class="nation-node" ...data-name="<substr>...">
        pattern = re.compile(
            r'(<details class="nation-node"[^>]*data-name="[^"]*'
            + re.escape(data_name_substr)
            + r'[^"]*"[^>]*>\s*<summary[^>]*>.*?</summary>)',
            re.DOTALL,
        )
        m = pattern.search(html)
        if not m:
            skipped.append(data_name_substr)
            continue

        start_marker = f"<!-- EXPLORER-START {data_name_substr} -->"
        end_marker = "<!-- EXPLORER-END -->"
        block = render_explorer_block(portrait, name, blurb, note)
        full = f"\n{start_marker}\n{block}\n{end_marker}\n"

        # Remove any prior EXPLORER block for this civ
        old = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker) + r"\n?",
            re.DOTALL,
        )
        html = old.sub("", html)

        # Re-find after removal since positions shifted
        m = pattern.search(html)
        if not m:
            skipped.append(data_name_substr)
            continue

        insert_at = m.end()
        html = html[:insert_at] + full + html[insert_at:]
        injected += 1

    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"injected explorer blocks for {injected} civs")
    if skipped:
        print(f"skipped (no matching section): {skipped}")
    return 0 if not skipped else 2


if __name__ == "__main__":
    import sys
    sys.exit(inject())
