"""Inject a per-civ "Walling Doctrine" block into a_new_world.html.

Maps each civ to one of six historical archetypes plus a short historical
citation. Appears between <!-- WALLING-START <civ> --> / <!-- WALLING-END
<civ> --> markers. If markers don't exist, inserts after the nation-header
summary line of each civ.

Idempotent.

.. note::
   This file's CIV_TO_DOCTRINE table is historical reference text only —
   the *runtime* wall doctrine for each civ is defined in
   ``tools/ai_design/wall_knob_calibration.CALIBRATION`` which emits
   ``game/ai/core/aiWallKnobsByCiv.xs``. The validator
   ``validate_spec_internal_consistency`` (invariant I-6) locks
   ``playstyle_spec.json:claims.wall_strategy`` against CALIBRATION;
   this file is not in that loop. Entries here may drift from
   CALIBRATION over time; CALIBRATION wins.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HTML_PATH = REPO / "a_new_world.html"

# (civ_display_name, strategy_short, historical_citation)
# 48 civs
DOCTRINES = {
    # Base civs — 22
    "Aztecs":               ("Mobile — No Walls", "Chinampa canal network replaced perimeter walls; Tenochtitlan relied on causeways and flood-plain terrain for defense."),
    "British":              ("Coastal Batteries", "Lines of Torres Vedras (1810): land-side ring-wall + naval gun batteries facing the sea. Wellington built 152 redoubts guarding Lisbon."),
    "Chinese":              ("Chokepoint Segments", "Great Wall sections at mountain passes only — Qing policy of fortifying the strategic chokepoints (Shanhaiguan, Jiayuguan), not the entire frontier."),
    "Dutch":                ("Coastal Batteries", "Hollandic Water Line (1672): inundated polders as the wall, forts at bridges and dry passes. Maurice of Nassau pioneered geometric fortification schools."),
    "Ethiopians":           ("Chokepoint Segments", "Amba fortress tradition — natural cliff amba (flat-topped mountain) as the wall itself; masonry only at ascending passes. Menelik's Entoto/Addis Ababa."),
    "French":               ("Fortress Ring", "Vauban's étoile pré carré (1678+): double bastion rings surrounding every frontier town. Bourbon France built the world's most geometrically perfect fortresses."),
    "Germans":              ("Fortress Ring", "Prussian Festungsanlage school: Frederick the Great's bastioned fortresses (Glatz, Silberberg, Neisse). Geometrical star walls with sally ports and redans."),
    "Haudenosaunee":        ("Mobile — No Walls", "Haudenosaunee longhouse villages had stockades against other nations but fought outside them — the raid-response doctrine, not siege endurance."),
    "Hausa":                ("Fortress Ring", "Kano Ancient City Wall (built c.1095, reinforced to the 19th century): 14 km of concentric mud-brick ramparts — one of Africa's longest wall circuits."),
    "Inca":                 ("Chokepoint Segments", "Sacsayhuamán's cyclopean zigzag walls defended Cusco only at the northern approach — the other sides sat on natural escarpments. Pachacuti's terrace-fort doctrine."),
    "Indians":              ("Chokepoint Segments", "Maratha hill-fort system: Shivaji's 300+ durgs (Raigad, Pratapgad, Sinhagad) each crowned a single strategic peak, wall only the narrow ridge to the gate."),
    "Italians":             ("Urban Barricade", "Renaissance trace italienne — compact star-fort city walls (Palmanova, Lucca, Siena). Tight ring around the urban core. Garibaldi's Risorgimento fought inside the old walls."),
    "Japanese":             ("Mobile — No Walls", "Sakoku-era Tokugawa Japan relied on castle-town (jōkamachi) redoubts, not perimeter walls. Mountain castles (yamashiro) used cliff terrain as the outer defense."),
    "Lakota":               ("Mobile — No Walls", "Lakota / Sioux plains doctrine: winter camps were moved, not walled. Crazy Horse explicitly refused static defense — mobility was the wall."),
    "Maltese":              ("Fortress Ring", "Great Siege of Malta (1565): the Hospitaller three-ring defense — Fort St. Elmo, Senglea, Birgu. Valette's triple fortress ring endured 4 months of Ottoman siege."),
    "Mexicans (Standard)":  ("Urban Barricade", "Mexican independence-era church strongpoints and hacienda walls (Alhóndiga de Granaditas, Guanajuato 1810). Tight urban cores walled, open country left exposed."),
    "Mexicans (Revolution)":("Urban Barricade", "Hidalgo's Grito de Dolores clergy-led revolt — parish churches and hacienda walls as strongpoints (Alhóndiga de Granaditas). Tight urban insurrection, open country left exposed."),
    "Ottomans":             ("Fortress Ring", "Theodosian walls of Constantinople + Suleiman's adaptation to cannon age. Triple-ring fortress walls with moat — the Byzantine gift Suleiman expanded after 1453."),
    "Portuguese":           ("Coastal Batteries", "Portuguese Discovery-era coastal fortresses (Elmina, Mombasa, Ormuz, Goa): sea-facing gun platforms with a single land-side ring. Prince Henry's colonial school."),
    "Russians":             ("Frontier Palisades", "Ivan the Terrible's steppe-frontier kremlin system (Kazan 1552, Astrakhan 1556): timber-then-stone palisade ring with sentinel watchtowers and Oprichnik flank screen."),
    "Spanish":              ("Coastal Batteries", "Spanish presidio system (Havana, Cartagena, San Juan, St. Augustine). Isabella's conquistador-era walled harbor compounds. Sea-facing artillery + land-side ring."),
    "Swedes":               ("Urban Barricade", "Gustavus Adolphus' fortified core cities (Stockholm, Göteborg). Carolean redoubts added outer field positions but the urban perimeter stayed Renaissance-trace tight."),
    "United States":        ("Frontier Palisades", "American frontier blockhouse doctrine: Fort Detroit, Fort Pitt, Fort Niagara. Wood palisades with corner blockhouses — Washington's Continental Army built them in days, not months."),

    # Revolution civs — 26
    "Americans":            ("Frontier Palisades", "Continental Army field fortifications (Valley Forge, Saratoga, Yorktown): quick timber redans + abatis. Jefferson's frontier thesis, not masonry citadels."),
    "Argentines":           ("Mobile — No Walls", "Argentine Fortín system — small cavalry outposts on the Pampa frontier against indigenous raids. San Martín's Army of the Andes crossed, it didn't wall."),
    "Baja Californians":    ("Frontier Palisades", "Adobe mission-presidio ring (Loreto, Santo Domingo): low walls, corner watchtowers, inner chapel as keep. Alvarado's pronunciamiento-era defenses."),
    "Barbary":              ("Coastal Batteries", "Algiers, Tunis, Tripoli corsair harbors: massive sea-facing gun batteries (Penon, Kasbah). Barbarossa-era naval fortress doctrine."),
    "Brazil":               ("Frontier Palisades", "Pedro I's distributed plantation economy: light palisade frontier protecting Mills, Plantations, and Markets across multiple resource patches; Atlantic coast fortaleza chain (Forte de São João, Santa Cruz, Lage) as fallback."),
    "Californians":         ("Frontier Palisades", "El Presidio de Sonoma, Presidio de Monterey: adobe wall + corner bastions + interior barracks. Vallejo's Californio ranchero defense network."),
    "Canadians":            ("Frontier Palisades", "War of 1812 blockhouse system (Fort Wellington, Fort Henry, Fort Malden). Brock's militia-based wood-wall + blockhouse frontier defense."),
    "Central Americans":    ("Frontier Palisades", "Federal Republic of Central America presidios — Spanish-colonial compact walled compounds kept during Morazán's unification wars. Wood + adobe, not stone."),
    "Chileans":             ("Chokepoint Segments", "Cordillera pass fortifications — Valparaíso harbor + Andean mountain gates. O'Higgins' Army of the Andes held the chokepoints; open pampa was scouted not walled."),
    "Columbians":           ("Chokepoint Segments", "Bolívar's Andean campaign walled only the passes (Boyacá, Pantano de Vargas). Urban Cartagena kept its colonial coastal fortress; interior cities used natural terrain."),
    "Egyptians":            ("Frontier Palisades", "Muhammad Ali's Nile delta fortifications: village walls + canal redoubts. Citadel of Cairo was the jewel but provincial defense was palisade-and-redoubt."),
    "Finnish":              ("Mobile — No Walls", "Mannerheim Line analog (projected back): forest redoubts + trench lines, not a continuous wall. Finnish forest doctrine is camouflage, not masonry."),
    "French Canadians":     ("Frontier Palisades", "New France seigneurial palisades (Fort Chambly, Fort St-Jean). Papineau-era Patriotes used village palisades + Iroquois-style stockades."),
    "Haitians":             ("Urban Barricade", "Fort de Joux, Citadelle Laferrière: mountain fortresses after the Revolution. Cap-Français pre-revolution: tight urban French colonial walls. Toussaint's hybrid."),
    "Hungarians":           ("Frontier Palisades", "Hungarian Military Frontier (Militärgrenze): Habsburg-era forward-settler palisade chain vs the Ottoman frontier. Kossuth-era Honvéd used the same forward line."),
    "Indonesians":          ("Frontier Palisades", "Javanese kraton (royal walled village) + Diponegoro's Java War (1825-30) bamboo-palisade system. Guerrilla walls moved with the army, not static forts."),
    "Mayans":               ("Urban Barricade", "Caste War of Yucatán (1847+): walled cenote villages (Chan Santa Cruz, Tixcacal). Canek's earlier 1761 rising used hidden jungle walls around sacred cenotes."),
    "Napoleonic France":    ("Mobile — No Walls", "Napoleon's doctrine — move, don't wall. Continental fortresses (Metz, Strasbourg, Lyon) were inherited; the field army carried only field-gun redans, never city walls."),
    "Peruvians":            ("Chokepoint Segments", "Inca fortress inheritance (Ollantaytambo, Pisac) + Spanish presidio walls at the Pacific ports. Santa Cruz's Peru-Bolivian Confederation fortified passes not perimeters."),
    "Revolutionary France": ("Urban Barricade", "Paris Revolutionary barricades (1789, 1830, 1848): urban street walls of overturned carts + paving stones. Robespierre's CSP relied on the city core, not ramparts."),
    "Rio Grande":           ("Frontier Palisades", "Republic of the Rio Grande (1840) presidios — Laredo, Guerrero, Mier. Canales Rosillo's rebel presidios were adobe-and-palisade, frontier-style."),
    "Romanians":            ("Frontier Palisades", "Carpathian mountain-pass palisades + Wallachian princely courts (Târgoviște, Bucharest). Cuza's 1859 unification inherited the Danube frontier palisade chain."),
    "South Africans":       ("Frontier Palisades", "Boer laager doctrine: wagon-circle ring + earthwork schanz + thorn-bush fence. Not masonry — Kruger's Transvaal fought inside-out from laagers, not walls."),
    "Texians":              ("Urban Barricade", "Alamo, Goliad, Gonzales: mission-fortress compact urban walls. Houston's Texas kept the compact mission core as the defensive doctrine through independence."),
    "Yucatan":              ("Urban Barricade", "Mérida cathedral + convent walls, cenote villages. Carrillo Puerto's Yucatecan socialism inherited the urban core + walled hacienda pattern."),
}


def build_block(civ: str, strategy: str, citation: str) -> str:
    strat = html.escape(strategy, quote=True)
    cit = html.escape(citation, quote=True)
    return (
        f'<details class="walling-block"><summary>Walling Doctrine &mdash; {strat}</summary>\n'
        f'<div class="walling-body">{cit}</div>\n'
        f'</details>'
    )


def main():
    txt = HTML_PATH.read_text(encoding="utf-8")
    injected = skipped = 0

    for civ, (strategy, citation) in DOCTRINES.items():
        block = build_block(civ, strategy, citation)
        start_marker = f"<!-- WALLING-START {civ} -->"
        end_marker = f"<!-- WALLING-END {civ} -->"
        wrapped = f"{start_marker}\n{block}\n{end_marker}"

        # Replace existing block if present
        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL,
        )
        if pattern.search(txt):
            txt = pattern.sub(wrapped, txt)
            injected += 1
            continue

        # Otherwise insert after the civ's EXPLORER-END marker (next line),
        # which every civ has. Fall back to summary line if not found.
        # Each civ has "<!-- EXPLORER-END -->" immediately after its explorer block.
        # We prepend our walling block after the first EXPLORER-END found for this civ.
        # To scope to the civ, anchor on the civ's nation-header alt="...flag" pattern.
        civ_anchor = re.compile(
            r'(<!-- ──────────── ' + re.escape(civ) + r' ──────────── -->.*?<!-- EXPLORER-END -->)',
            re.DOTALL,
        )
        m = civ_anchor.search(txt)
        if not m:
            print(f"  SKIP {civ}: anchor not found")
            skipped += 1
            continue
        insertion = m.group(1) + "\n" + wrapped
        txt = txt[:m.start()] + insertion + txt[m.end():]
        injected += 1
        print(f"  ok   {civ}: {strategy}")

    HTML_PATH.write_text(txt, encoding="utf-8")
    print(f"\ninjected: {injected}  skipped: {skipped}")


if __name__ == "__main__":
    main()
