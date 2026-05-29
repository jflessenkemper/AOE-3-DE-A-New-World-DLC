# Historical Map-Placement Guide (48 Nations)

**Status:** Draft reference for map-grid modal visualization
**Scope:** Per-civ building-placement doctrine grounded in real settlement archaeology, military history, and economic patterns
**Owner:** Legendary Leaders AI mod
**Date:** 2026-04-24

---

## How to read this document

Each nation has 11 fields. Every evidence line is confidence-graded:

- **[strong]** — well-attested in archaeology, military manuals, or standard secondary literature.
- **[plausible]** — inference from related doctrine of the same civilization, era, or school.
- **[speculative]** — educated guess from adjacent evidence; flagged so the visualization layer can soften the claim.

Wall archetype names match the constants in `game/ai/leaders/leaderCommon.xs` where possible: `CoastalBatteries`, `FortressRing`, `FrontierPalisades`, `MobileNoWalls`, `UrbanBarricade`, `ChokepointSegments`. Where a nation's historical doctrine doesn't match any existing archetype (e.g. Barbary corsair harbors, Lakota camp circles, Finnish trench-line defense), the schema's expanded archetypes are used: `NomadScreen`, `StarFort`, `ChainTowers`, `None`. The map-grid modal can collapse the expanded set into the six coded archetypes using the mapping provided at the end of each entry.

Leader-era anchor follows the Legendary Leaders roster as of 2026-04-24. British = Elizabeth I (not Wellington); Russians = Ivan the Terrible (not Catherine); Lakota = Chief Gall (Little Bighorn era); French base = Louis XVIII Bourbon Restoration; Napoleonic France = Napoleon post-1804 coronation.

---

# BASE CIVS (22)

---

### Aztecs (Aztecs)

**Historical era & geography.** Valley of Mexico under Montezuma II, early 16th century. Tenochtitlan sat on an island in Lake Texcoco; the altepetl system spread across lake-shores and surrounding highland basins.

**Starting TC preference.**
- Primary terrain: wetland
- Secondary terrain: river
- Evidence: Tenochtitlan was built on a low lake islet reclaimed with chinampas; tribute capitals (Texcoco, Tlacopan) all ringed the lakeshore. [strong]

**House / residential placement.** Calpulli (ward) clusters of reed-and-adobe houses were laid out on chinampa raised plots along canals; densest near the ceremonial core, thinning toward shore.
- Axis: river_terrace (canal-bank analogue)
- Evidence: Cortes's letters and the Matricula de Tributos describe canal-grid housing radiating from the Templo Mayor precinct. [strong]

**Economic building placement.** Chinampa gardens (mill/farm analogues) ran in long rectangles into shallow lake water; tribute warehouses and markets clustered at the causeway junctions.
- Axis: river_terrace
- Evidence: Archaeological survey of Xochimilco-Chalco chinampa system shows continuous canal-aligned plots. [strong]

**Military building placement.** Warrior houses (telpochcalli/calmecac) stood near the ceremonial core; the Eagle and Jaguar orders occupied precinct buildings adjacent to the Templo Mayor. Forward garrisons sat on causeway gates.
- Posture: clustered_central
- Evidence: Sahagun and Duran describe warrior schools inside the sacred precinct. [strong]

**Religious / cultural building placement.** Twin-pyramid temples occupied the geometric center of each altepetl; shrine markers (momoztli) dotted crossroads.
- Axis: center
- Evidence: Every excavated Aztec-era altepetl center follows the Tenochtitlan template. [strong]

**Trade / market placement.** Tlatelolco — the great market — sat on a secondary island adjacent to the capital, connected by causeway; peripheral tianguis markets rotated at roadway junctions.
- Axis: crossroads / waterside
- Evidence: Cortes estimated 60,000 daily traders at Tlatelolco; site is archaeologically confirmed. [strong]

**Defensive architecture.** No encircling stone wall; defense relied on the lake moat and causeway chokepoints with removable bridge sections and gate-forts (Xoloco, Tepeyacac).
- Wall archetype: ChokepointSegments
- Wall placement logic: chokepoint_seals
- Evidence: Spanish accounts of the Noche Triste describe causeway-gap defense as the primary system. [strong]

**Expansion heading.** Toward tribute-paying basins — eastward toward Texcoco, south into Morelos, north toward the Tepanec lowlands.
- along_coast (lakeshore) + follow_trade_route
- Evidence: Codex Mendoza tribute provinces map outward expansion. [strong]

**Signature placement quirk.** Every Aztec town grows as a causeway-chokepoint cluster on water — lake or river — with a twin-pyramid center and chinampa strips projecting into shallow water.

**Open research questions.** How strongly should highland (non-lacustrine) Aztec outposts like Oaxaca garrisons weight the wetland preference? Likely much weaker, but not documented here.

---

### British (British)

**Historical era & geography.** Elizabethan England, late 16th century. Tudor coastal mercantilism, Armada-era naval doctrine, enclosure-driven manorial economy.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: river
- Evidence: Tudor settlement pattern was coastal or tidal-estuary (London on the Thames, Bristol on the Avon, Plymouth, Portsmouth); Elizabethan corporate charters followed the port network. [strong]

**House / residential placement.** Manor-house + tied cottage cluster on enclosed hedgerow fields; market towns grew as ribbon streets along a central road.
- Axis: trade_street
- Evidence: Enclosure Act archaeology (Northamptonshire deserted-village surveys) confirms the manor-plus-cottage-row pattern. [strong]

**Economic building placement.** Mills on tidal race or river; woolsack warehouses at port; sheep walks on downland.
- Axis: coast (port warehouse) + river (mill)
- Evidence: Cloth-trade economic maps of 16th-c. England show River Stour / Severn / Cam mill-warehouse pairs. [strong]

**Military building placement.** Tudor musters trained on town commons; royal arsenals at the naval yards (Deptford, Chatham, Portsmouth). Trained Bands billeted in the capital.
- Posture: defensive_interior with coastal muster-points
- Evidence: 1588 muster rolls list coastal trained-band depots. [strong]

**Religious / cultural building placement.** Parish church at village crossroads (dominant feature of every English village plan); cathedrals at county seats.
- Axis: crossroads / center
- Evidence: Standard English parish-geography pattern; the square-towered church at the crossroads is the visual landmark. [strong]

**Trade / market placement.** Market cross at the town center for chartered markets; customs houses at the quays.
- Axis: coast + crossroads
- Evidence: Chartered-market towns documented in the Victoria County History series. [strong]

**Defensive architecture.** Elizabeth invested in coastal gun-platforms (Henrician device forts extended) and relied on the Navy for strategic defense. Inland castles were in decline.
- Wall archetype: CoastalBatteries
- Wall placement logic: coast_batteries
- Evidence: Henrician and Elizabethan coastal-artillery-fort surveys (Hurst, Pendennis, Deal, Walmer). [strong]

**Expansion heading.** Along coast, then island-hop into the Atlantic world (Virginia, Bermuda, Caribbean).
- along_coast, island_hop
- Evidence: Raleigh and Gilbert patents traced an Atlantic-rim expansion. [strong]

**Signature placement quirk.** Coastal gun-batteries at every beachable cove and river mouth — the Martello/device-fort coast-necklace pattern, unique to this civ.

**Open research questions.** How much should London-Thames riverine character bleed into the visualization? Probably weight river secondary stronger for expansion TCs inland.

---

### Chinese (Chinese)

**Historical era & geography.** Qing dynasty under the Kangxi Emperor, late 17th / early 18th c. Centralized Han-Manchu governance over North China plains, Yangzi valley, Grand Canal corridor.

**Starting TC preference.**
- Primary terrain: river
- Secondary terrain: plain
- Evidence: Imperial capital pattern (Beijing on the Yongding plain, Nanjing on the Yangzi, Kaifeng on the Yellow River) links canal-grid cities to rivers. [strong]

**House / residential placement.** Hutong-courtyard houses inside rectilinear city blocks; farming hamlets outside in tight wall-circled clusters.
- Axis: fortified_interior (inside the city wall), then pastoral_dispersed outside
- Evidence: Ming-Qing urban archaeology; every provincial seat followed the north-south axis with ward walls. [strong]

**Economic building placement.** Grain tribute granaries along the Grand Canal; rice paddies on river-floodplain; markets at ward gates.
- Axis: river + crossroads
- Evidence: The Grand Canal granary system (Tongzhou, Linqing) is one of the best-documented logistical networks in pre-modern history. [strong]

**Military building placement.** Banner garrisons occupied dedicated walled enclaves inside major cities (the "Manchu city" inside Xi'an, Nanjing, Guangzhou); frontier military colonies (tuntian) at the northern and western perimeter.
- Posture: clustered_central (banner garrison) + frontier_line (Great Wall / tuntian)
- Evidence: Qing Banner Garrison gazetteers list urban Manchu-city locations; tuntian maps show frontier farm-colonies. [strong]

**Religious / cultural building placement.** Temple of Heaven / altar complex on the south axis; civic Confucian temple at the administrative center; Buddhist monasteries in hills outside the city.
- Axis: center (civic) + hilltop (monastic)
- Evidence: Imperial ritual geography is codified in the Zhou Li and replicated at Beijing, Seoul, Hue. [strong]

**Trade / market placement.** Canal ports (Yangzhou, Suzhou, Hangzhou) were the commercial nodes; intra-city markets at ward gates.
- Axis: river + crossroads
- Evidence: Grand Canal commercial-geography literature (Skinner's market-systems analysis). [strong]

**Defensive architecture.** Massive rammed-earth city walls in square plan with four gates; the Great Wall as a frontier line to the north.
- Wall archetype: FortressRing (city) — note: code currently tags Chinese as FrontierPalisades; for the Great Wall frontier that's defensible, but urban Chinese is ring.
- Wall placement logic: ring_around_core + frontier_line_only (for the Great Wall)
- Evidence: Every Chinese provincial capital had a square rammed-earth wall; the Great Wall is the frontier counterpart. [strong]

**Expansion heading.** Upriver and along the Grand Canal; frontier push north-west into Mongolia/Xinjiang under Kangxi.
- follow_trade_route + frontier_push
- Evidence: Kangxi's Dzungar campaigns mapped outward expansion NW; the canal system carried internal growth N-S. [strong]

**Signature placement quirk.** Square-wall-with-four-gates template replicated at every settlement scale; the Manchu-city-within-a-city double-wall pattern is visually unique.

**Open research questions.** Should the mod model Great Wall tiles as a special frontier-line object rather than standard walls? Out of scope here but worth flagging.

---

### Dutch (Dutch)

**Historical era & geography.** Dutch Republic under Maurice of Nassau, early 17th c. Polder-drained Rhine-Maas delta; Amsterdam canal city as archetype.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: river
- Evidence: Every major Dutch city (Amsterdam, Rotterdam, Delft, Leiden, Dordrecht) sits on tidal or river water. [strong]

**House / residential placement.** Narrow canal-house lots lining the grachten; dyke-top linear villages (dijkdorpen) on reclaimed land.
- Axis: trade_street (canal street) + river_terrace
- Evidence: Amsterdam's Grachtengordel is the template; dijkdorp archaeology in Noord-Holland confirms the dyke-top pattern. [strong]

**Economic building placement.** Warehouses on the IJ waterfront; windmill-mills on dyke exposures; dairy polders inland.
- Axis: coast + river
- Evidence: VOC warehouse geography of 17th-c. Amsterdam; polder windmill surveys. [strong]

**Military building placement.** Compact citadels at port chokepoints (Naarden pentagonal fortress); field-army billets rotated between frontier fortresses of the Hollandic Water Line.
- Posture: frontier_line (Water Line) + clustered_central (citadel)
- Evidence: Maurice of Nassau codified the trace-italienne star-fort style; the Water Line (Oude Hollandse Waterlinie) is documented from 1672. [strong]

**Religious / cultural building placement.** Calvinist church (Oude Kerk / Nieuwe Kerk) at the market square; no cathedral hierarchy after the Reformation.
- Axis: center
- Evidence: Dutch Reformed church geography concentrates at civic squares. [strong]

**Trade / market placement.** Stock Exchange (1602), banks, and trading houses clustered at Dam Square / canal-ring intersections.
- Axis: trade_street + river
- Evidence: The Beurs van Hendrick de Keyser and the surrounding banker-houses are archaeologically preserved on the Rokin. [strong]

**Defensive architecture.** Trace italienne star-forts at frontier chokepoints; inundation lines (deliberate polder flooding) as strategic defense.
- Wall archetype: ChokepointSegments (inundation + star-fort)
- Wall placement logic: chokepoint_seals
- Evidence: Hollandic Water Line primary sources; Naarden, Bourtange, Willemstad fortresses still intact. [strong]

**Expansion heading.** Along coast, up rivers, island-hop globally (Cape, Ceylon, Batavia).
- along_coast + upriver + island_hop
- Evidence: VOC-trade network atlas; Rijksmuseum cartographic holdings. [strong]

**Signature placement quirk.** Banks cluster on hills or on the canal-ring near trade posts (Amsterdam canal-bank pattern); inundation-segment walls rather than continuous rings.

**Open research questions.** Whether inundation should map to a flood-tile mechanic or be visualized simply as ChokepointSegments.

---

### Ethiopians (Ethiopians)

**Historical era & geography.** Abyssinian highlands under Menelik II, late 19th c., centered on Shewa and Gondar. Adwa-era imperial consolidation.

**Starting TC preference.**
- Primary terrain: highland_pasture
- Secondary terrain: hill
- Evidence: Every imperial capital — Axum, Lalibela, Gondar, Ankober, Addis Ababa — sits above 2000m on a highland amba. [strong]

**House / residential placement.** Round tukul houses clustered on amba flat tops or terraced slopes near the imperial compound.
- Axis: hill
- Evidence: Gondar-era compound archaeology; tukul cluster patterns documented in Shewa ethnography. [strong]

**Economic building placement.** Teff fields on highland plateaus; ox-plow agriculture on terraced slopes; markets at highland crossroads (gebeya).
- Axis: highland_pasture
- Evidence: Ethiopian agricultural history (McCann, People of the Plow) documents the highland teff-ox system. [strong]

**Military building placement.** Ras-guard barracks at the imperial compound; provincial garrisons (ketema) at highland junctions.
- Posture: clustered_central at amba + frontier_line at Muslim-lowland edge
- Evidence: Menelik's war-camp layouts (ketema) are documented in his Adwa campaign orders. [strong]

**Religious / cultural building placement.** Monolithic or cruciform Orthodox churches on hilltops or within royal compounds; monastery complexes on isolated ambas (Debre Libanos, Debre Damo).
- Axis: hilltop
- Evidence: Ethiopian church archaeology — Lalibela rock-hewn complex, Debre Damo accessible only by rope. [strong]

**Trade / market placement.** Rotating weekly gebeya markets at highland crossroads; imperial market at Addis Mercato.
- Axis: crossroads
- Evidence: Gebeya system documented in 19th-20th c. ethnography. [strong]

**Defensive architecture.** The terrain itself is the wall; amba escarpments with a single defensible trail are the classic Ethiopian fastness. Gondar had a modest royal enclosure wall (Fasilides). Menelik used entrenched rifle positions at Adwa.
- Wall archetype: ChokepointSegments (amba trail seals)
- Wall placement logic: chokepoint_seals
- Evidence: Fasil Ghebbi royal enclosure in Gondar; Adwa battlefield archaeology. [strong]

**Expansion heading.** Outward from the highland core into surrounding lowlands (Menelik's expansion into Oromo, Sidamo, Harar).
- outward_rings
- Evidence: Menelik-era expansion maps in Bahru Zewde's Modern History of Ethiopia. [strong]

**Signature placement quirk.** Every settlement sits on or under an amba (flat-top mountain); churches on hilltops with rock-hewn or cruciform silhouettes unique in the world.

**Open research questions.** Lowland Oromo expansion-era settlements were more plains-oriented; we may want a secondary "frontier expansion" placement mode.

---

### French (French)

**Historical era & geography.** Bourbon Restoration under Louis XVIII (1815–1824). Ancien-regime court geography restored: Paris, Versailles, Fontainebleau, Compiegne, the river Loire chateau belt.

**Starting TC preference.**
- Primary terrain: river
- Secondary terrain: plain
- Evidence: Paris on the Seine, Lyon on the Rhone, Tours/Blois/Chambord on the Loire — French capital-tier cities are river-anchored. [strong]

**House / residential placement.** Bastide grid village on cadastral strip-fields; chateau-and-village manorial pattern in wine country.
- Axis: river_terrace / fortified_interior
- Evidence: Vidal de la Blache's regional geography; medieval bastide archaeology in Gascony. [strong]

**Economic building placement.** Grain mills on river races; viticulture on south-facing slopes; markets at bastide centers.
- Axis: river + plain
- Evidence: French rural-economic geography is a founding literature of the Annales school. [strong]

**Military building placement.** Chateaux and Vauban frontier fortresses; royal arsenal at Paris / Versailles; Restoration era relied on inherited Vauban belt.
- Posture: frontier_line (Vauban) + defensive_interior (chateau)
- Evidence: Vauban's pre-carre fortresses are UNESCO-listed and map the frontier-line doctrine. [strong]

**Religious / cultural building placement.** Gothic cathedrals at diocesan crossroads (Chartres, Reims, Amiens); parish church at the bastide center.
- Axis: crossroads / center
- Evidence: French cathedral geography; episcopal city archaeology. [strong]

**Trade / market placement.** Halles in town center; fairs at regional crossroads (Champagne fairs historically).
- Axis: crossroads
- Evidence: Champagne fairs literature (Abu-Lughod, Before European Hegemony). [strong]

**Defensive architecture.** Vauban trace italienne star-forts ringing the frontier (Pre-Carre); chateau donjons inland.
- Wall archetype: FortressRing
- Wall placement logic: ring_around_core + frontier_line_only (Vauban belt)
- Evidence: Vauban's 1672 fortification treatises; pre-carre frontier still legible in modern France. [strong]

**Expansion heading.** Upriver (Loire, Rhone, Seine); toward the Vauban frontier (Alsace, Flanders, Roussillon).
- upriver + frontier_push
- Evidence: French administrative expansion maps (Alsace 1648, Franche-Comte 1678). [strong]

**Signature placement quirk.** Chateau-with-formal-garden pattern set in a river bend — the Loire chateau silhouette — and Vauban star-forts as a frontier necklace.

**Open research questions.** The Louis XVIII Restoration era is not expansionist; should "expansion heading" be softened toward internal consolidation rather than Vauban-frontier push?

---

### Germans (Germans)

**Historical era & geography.** Prussia under Frederick the Great, mid-18th c. Forested Brandenburg-Prussia core, expanding into Silesia; frontier-garrison doctrine.

**Starting TC preference.**
- Primary terrain: river
- Secondary terrain: forest_edge
- Evidence: Berlin on the Spree, Potsdam on the Havel, Magdeburg on the Elbe — Hohenzollern capitals sit on rivers in forest-cleared plains. [strong]

**House / residential placement.** Linear Strassendorf villages along a single through-road; Junker manor-and-tied-farm pattern in rural Brandenburg.
- Axis: trade_street
- Evidence: German rural-settlement typology (Strassendorf, Haufendorf, Rundling) is codified in 19th-c. geography. [strong]

**Economic building placement.** Mills on river; timber yards at forest edge; mining towns in the Harz and Silesia.
- Axis: river + forest_edge
- Evidence: Cameralist economic geography of Prussia; Silesian mining archaeology. [strong]

**Military building placement.** Frederick's Prussia billeted regiments in garrison cities (Berlin, Potsdam, Spandau, Breslau); frontier fortresses along the Oder-Neisse line.
- Posture: frontier_line + clustered_central
- Evidence: Prussian garrison-city geography documented in Otto Busch's Military System and Social Life. [strong]

**Religious / cultural building placement.** Protestant Hallenkirche at town center; baroque palace church (Sanssouci) near the royal residence.
- Axis: center
- Evidence: Protestant parish geography; Sanssouci-Potsdam archaeology. [strong]

**Trade / market placement.** Rathaus-plus-market-square (Rathausmarkt) at town center; Leipzig fair for international trade.
- Axis: crossroads
- Evidence: German Rathaus geography is universal in Hanseatic and Prussian cities. [strong]

**Defensive architecture.** Bastioned star-forts (Spandau citadel, Kustrin, Magdeburg); frontier fortress belt after Silesia acquisition.
- Wall archetype: FortressRing (+ StarFort style)
- Wall placement logic: ring_around_core + frontier_line_only
- Evidence: Prussian fortification surveys of the 18th c. [strong]

**Expansion heading.** Eastward push into Silesia, Pomerania, West Prussia.
- frontier_push
- Evidence: Frederick's Silesian Wars and First Partition of Poland. [strong]

**Signature placement quirk.** Grenadier-garrison towns rectangular in plan with central parade-ground plus star-fort citadel on one corner — the Potsdam/Berlin template.

**Open research questions.** Should the mod differentiate south-German (Bavarian / Catholic Haufendorf) from north-German (Protestant Strassendorf) placement? Unified civ, so probably collapse to Prussia.

---

### Haudenosaunee (Haudenosaunee)

**Historical era & geography.** Five Nations Iroquois Confederacy, 16th–18th c., centered on the Finger Lakes and Mohawk Valley of present-day New York.

**Starting TC preference.**
- Primary terrain: forest_edge
- Secondary terrain: river
- Evidence: Onondaga, Cayuga, Seneca, Oneida, Mohawk longhouse villages all sat on elevated ground at forest edge near lake or river. [strong]

**House / residential placement.** 60–100 ft longhouses arranged parallel inside a palisaded village, clan-based arrangement.
- Axis: fortified_interior
- Evidence: Howlett Hill, Ganondagan, and Jefferson County village excavations. [strong]

**Economic building placement.** Three Sisters fields (corn-bean-squash) cleared in surrounding forest; storage pits inside the palisade.
- Axis: forest_edge
- Evidence: Haudenosaunee agricultural archaeology (Engelbrecht, Iroquoia). [strong]

**Military building placement.** No standing military architecture per se; war parties assembled at council longhouses.
- Posture: defensive_interior (inside palisade), with mobile raid columns beyond
- Evidence: Haudenosaunee war-practice documentation (Parmenter, Edge of the Woods). [strong]

**Religious / cultural building placement.** Council longhouse (ganonhsees) at village center; no detached temple architecture.
- Axis: center
- Evidence: Great Law of Peace oral tradition; council-house archaeology. [strong]

**Trade / market placement.** Portage points and fur-trade landings on navigable water; no dedicated market building.
- Axis: riverside
- Evidence: Mohawk Valley fur-trade routes (Trelease, Indian Affairs in Colonial New York). [strong]

**Defensive architecture.** Double-ring log palisade with raised firing platforms; villages relocated every 10–20 years as soils exhausted.
- Wall archetype: FrontierPalisades
- Wall placement logic: village_palisades
- Evidence: Archaeological excavation of multi-ring palisaded village sites (Howlett Hill, Garoga). [strong]

**Expansion heading.** Along river and portage — the Mohawk-Hudson corridor west to the Great Lakes.
- follow_trade_route + along_coast (lakeshore)
- Evidence: Beaver Wars expansion maps. [strong]

**Signature placement quirk.** Palisaded longhouse cluster on forest-edge high ground near a water source — the archetypal northeastern woodland village silhouette.

**Open research questions.** None critical; Haudenosaunee placement is well-attested archaeologically.

---

### Hausa (Hausa)

**Historical era & geography.** Sokoto Caliphate under Usman dan Fodio, early 19th c. Sahelian city-state belt across northern Nigeria; Kano, Katsina, Zaria, Gobir as trade-emirate capitals.

**Starting TC preference.**
- Primary terrain: plain
- Secondary terrain: desert_oasis
- Evidence: Hausa cities sit on the Sahel-Sudan transition; Kano and Zaria are built on dry plateau plains with seasonal water. [strong]

**House / residential placement.** Courtyard compounds (gida) with mud walls, clustered in wards (unguwa) inside the city wall.
- Axis: fortified_interior
- Evidence: Hausa urban-architecture literature (Schwerdtfeger, Traditional Housing in African Cities). [strong]

**Economic building placement.** Millet fields and pastoral zones outside the wall; market (kasuwa) inside the wall near the emir's palace.
- Axis: center (market) + pastoral_dispersed (fields)
- Evidence: Kano kasuwa geography; Sokoto Caliphate economic literature (Lovejoy). [strong]

**Military building placement.** Emir's palace with adjacent cavalry quarters; city-wall watch stations.
- Posture: clustered_central
- Evidence: Kano Chronicle; emirate palace archaeology. [strong]

**Religious / cultural building placement.** Great Friday mosque near the emir's palace and central market.
- Axis: center
- Evidence: Standard Sahelian Islamic city plan (Kano, Zaria, Katsina). [strong]

**Trade / market placement.** Kasuwa at city center; caravan serais at city gates for trans-Saharan traders.
- Axis: center + crossroads (at gate)
- Evidence: Trans-Saharan trade-route documentation (Bovill, Golden Trade of the Moors). [strong]

**Defensive architecture.** Massive tamped-earth walls (ganuwa) ringing the city, with 12+ gates; Kano wall is ~14 km and up to 15m tall.
- Wall archetype: FortressRing
- Wall placement logic: ring_around_core
- Evidence: Kano wall archaeology (Moody, Gazetteer of Kano); still partially extant. [strong]

**Expansion heading.** Along trans-Saharan caravan routes — north toward Agadez, west toward Timbuktu, south into Yoruba lands post-jihad.
- follow_trade_route + frontier_push
- Evidence: Sokoto Caliphate expansion maps post-1804 jihad. [strong]

**Signature placement quirk.** Tamped-earth city ring with multiple gates opening onto caravan routes — the ganuwa silhouette is distinct to Sahelian urbanism.

**Open research questions.** How to model the seasonal transhumance of Fulani pastoralists integrated into the caliphate? Probably outside placement scope.

---

### Inca (Inca)

**Historical era & geography.** Tawantinsuyu under Pachacuti, mid-15th c. Andean spine from Quito to Santiago; capital Cuzco at 3400m.

**Starting TC preference.**
- Primary terrain: hill (Andean highland)
- Secondary terrain: river (terraced valley)
- Evidence: Cuzco, Machu Picchu, Ollantaytambo, Pisac all sit at 2500m+ on highland ridges or terraced valley shoulders. [strong]

**House / residential placement.** Trapezoidal-doorway stone compounds on terraced slopes; ayllu kin-groups clustered.
- Axis: hill (terrace)
- Evidence: Machu Picchu residential terraces; Cuzco barrio archaeology. [strong]

**Economic building placement.** Terraced andenes agriculture on slopes; qollqa (storehouses) on ventilated ridges above the settlement; llama pastures at puna altitudes.
- Axis: hill
- Evidence: The qollqa storehouse system at Ollantaytambo and Huanuco Pampa is extensively mapped. [strong]

**Military building placement.** Saqsaywaman citadel above Cuzco; highland fortresses (pucara) at approaches.
- Posture: defensive_interior + chokepoint_seals
- Evidence: Saqsaywaman excavation; Inca fortress typology (Hyslop, Inka Settlement Planning). [strong]

**Religious / cultural building placement.** Sun-temple (Coricancha) at ceremonial core; huaca shrines on prominent peaks and springs.
- Axis: center (Coricancha) + hilltop (huaca)
- Evidence: Ceque-system cosmography; Coricancha archaeology. [strong]

**Trade / market placement.** Inca state redistributed via qollqa rather than market — tambo way-stations on the royal roads are the closest analogue.
- Axis: crossroads (tambo on Qhapaq Nan)
- Evidence: Qhapaq Nan road network UNESCO documentation; tambo inventories (Hyslop). [strong]

**Defensive architecture.** Cyclopean stone walls at citadel sites (Saqsaywaman, Ollantaytambo); valley-neck pucara forts at chokepoints.
- Wall archetype: ChokepointSegments
- Wall placement logic: chokepoint_seals
- Evidence: Pucara typology studies; Saqsaywaman fortifications. [strong]

**Expansion heading.** Along the Andean spine — north to Quito, south to central Chile — via the Qhapaq Nan royal road.
- follow_trade_route + frontier_push
- Evidence: Tawantinsuyu expansion atlas; Inca royal road network. [strong]

**Signature placement quirk.** Terraced-slope settlements with qollqa storage strung along higher ridges — the vertical-archipelago pattern is unique to Andean civilization.

**Open research questions.** None critical; Inca settlement geography is among the best-documented precolonial systems.

---

### Indians (Indians)

**Historical era & geography.** Maratha Confederacy under Shivaji, 17th c. Deccan plateau and Western Ghats; hill-fort (durg) defensive doctrine.

**Starting TC preference.**
- Primary terrain: hill
- Secondary terrain: river
- Evidence: Shivaji's capitals (Raigad, Rajgad, Pratapgad, Sinhagad) are all hill forts at 800–1400m on Ghats spurs. [strong]

**House / residential placement.** Peth (ward) settlements below the fort; river-ghat villages along Godavari, Krishna, Bhima.
- Axis: river_terrace (below fort) + fortified_interior
- Evidence: Maratha town plans (Peth-Wada-Fort triad). [strong]

**Economic building placement.** Irrigated paddies in river valleys; dryland jowar/bajra on plateau; cotton markets in peth settlements.
- Axis: river + plain
- Evidence: Deccan agrarian geography (Fukazawa, Medieval Deccan). [strong]

**Military building placement.** Garrisons atop each durg; mobile light cavalry (ganimi kava) operated from the plateau.
- Posture: clustered_central (on fort) + mobile_satellite
- Evidence: Shivaji's 300+ hill forts; Maratha chronicles (Sabhasad Bakhar). [strong]

**Religious / cultural building placement.** Bhavani / Shiva temples inside forts; ghat-side temples (Trimbakeshwar, Bhimashankar); the Jyotirlinga network.
- Axis: hilltop (fort temple) + riverside (ghat temple)
- Evidence: Maharashtra temple-geography literature; Jyotirlinga pilgrimage mapping. [strong]

**Trade / market placement.** Peth markets under fort walls; coastal trading posts (Gheria, Vijaydurg) for Maratha navy.
- Axis: crossroads + coast
- Evidence: Shivaji's Konkan-coast trade-port development; Kanhoji Angre's admiralty. [strong]

**Defensive architecture.** Hill forts with concentric stone walls stepped along a ridge; coastal sea-forts (Sindhudurg, Vijaydurg).
- Wall archetype: FortressRing (hill) + CoastalBatteries (sea-forts)
- Wall placement logic: ring_around_core + coast_batteries
- Evidence: Maratha fort architecture surveys (Sohoni, The Forts of Shivaji). [strong]

**Expansion heading.** Outward from Pune-Satara core; down the Konkan coast and into Khandesh/Berar.
- outward_rings + along_coast
- Evidence: Maratha expansion atlas 1650–1680. [strong]

**Signature placement quirk.** Concentric hill-fort silhouette with peth town and temple cluster at the fort's base — instantly recognizable Maratha template.

**Open research questions.** How much Mughal (Shah Jahan era) Indo-Islamic urban geography should leak through given the civ is shared between both styles? Shivaji leader-anchor tilts it firmly Maratha.

---

### Italians (Italians)

**Historical era & geography.** Risorgimento-era Italy under Garibaldi, mid-19th c. — but the broader civ reflects Renaissance city-state and maritime-republic geography (Venice, Genoa, Florence, Pisa).

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: river
- Evidence: Venice lagoon, Genoa harbor, Pisa on the Arno, Florence on the Arno, Naples bay — Italian city-states are maritime or fluvial. [strong]

**House / residential placement.** Palazzo-and-courtyard townhouses lining stone-paved streets inside the city wall; rural contado villas on hill slopes.
- Axis: trade_street
- Evidence: Italian urban archaeology; Medici villa geography. [strong]

**Economic building placement.** Arsenals at the waterfront (Venetian Arsenal); mills on river; market at Piazza.
- Axis: coast + river
- Evidence: Venetian Arsenal is the largest pre-industrial factory complex studied (Lane, Venice: A Maritime Republic). [strong]

**Military building placement.** Condottiere companies billeted in fortified palazzi; city militia at the arsenal; trace italienne star-forts at frontier.
- Posture: clustered_central + frontier_line
- Evidence: Machiavelli's Arte della Guerra; Michelangelo's Florentine fortifications. [strong]

**Religious / cultural building placement.** Duomo at the piazza-center; hilltop pilgrimage churches (San Miniato, Orvieto); baptistery adjacent to cathedral.
- Axis: center + hilltop
- Evidence: Italian cathedral-piazza geography; every city has a Duomo complex. [strong]

**Trade / market placement.** Banking houses at the Piazza (Florentine Mercato Vecchio); Rialto at Venice.
- Axis: crossroads (piazza)
- Evidence: Banking geography of Florence; Rialto market archaeology. [strong]

**Defensive architecture.** Italy invented trace italienne (Sangallo, Michelangelo); bastioned star-forts ring every city-state; coastal watch-towers vs. Barbary corsairs.
- Wall archetype: FortressRing (trace italienne) + CoastalBatteries (watch-towers)
- Wall placement logic: ring_around_core + coast_batteries
- Evidence: Parker's The Military Revolution traces the bastion to 1450s Italy. [strong]

**Expansion heading.** Maritime — along the Mediterranean coast and island-hop to Crete, Cyprus, the Aegean (Venetian/Genoese empires).
- along_coast + island_hop
- Evidence: Venetian stato da mar; Genoese Black Sea colonies. [strong]

**Signature placement quirk.** Star-fort trace italienne with piazza-plus-duomo civic center — the visual signature is a bastioned polygon with a cathedral dome at its heart.

**Open research questions.** Garibaldi's republican-militia doctrine justifies the UrbanBarricade tag in code; the broader civ history favors FortressRing. Which takes precedence for the modal?

---

### Japanese (Japanese)

**Historical era & geography.** Tokugawa shogunate under Ieyasu, early 17th c. — castle-town (jokamachi) geography across the Kanto and Kansai plains.

**Starting TC preference.**
- Primary terrain: plain (within mountain-ringed basins)
- Secondary terrain: hill
- Evidence: Edo, Osaka, Kyoto, Nagoya, Sendai — Tokugawa castle-towns sit in alluvial basins ringed by hills. [strong]

**House / residential placement.** Samurai districts closest to castle, merchant/artisan machi districts outside inner wall, peasant hamlets at basin fringe.
- Axis: fortified_interior (samurai) + trade_street (machi)
- Evidence: Tokugawa castle-town zoning (bukedochi/chodochi/teradochi). [strong]

**Economic building placement.** Rice paddies on floodplain; fishing ports on coast; managed forest (satoyama) on hills.
- Axis: plain (paddy) + coast (fish)
- Evidence: Tokugawa-era village registers and the Satoyama literature (Totman, Green Archipelago). [strong]

**Military building placement.** Castle donjon at center; samurai barracks in rings around; daimyo hand-deployable armies rather than fixed frontier.
- Posture: clustered_central
- Evidence: Every Tokugawa han-capital follows the spiral-ring castle-town plan. [strong]

**Religious / cultural building placement.** Shinto shrine (jinja) at sacred mountain or forest edge; Buddhist temple (tera) in terashi district; clan ancestral shrine.
- Axis: forest_grove (shrine) + compound_enclosed (temple)
- Evidence: Shinto-shrine geography; Tokugawa tera-uke temple-registration system. [strong]

**Trade / market placement.** Merchant ward (chonin-machi) outside the castle's inner moat; port markets at Edo/Osaka.
- Axis: trade_street + coast
- Evidence: Edo merchant-ward archaeology (Nihonbashi market district). [strong]

**Defensive architecture.** Spiral-moat castle with concentric stone walls (ishigaki) and inner keep (tenshu).
- Wall archetype: FortressRing
- Wall placement logic: ring_around_core
- Evidence: Himeji, Matsumoto, Osaka castle surveys; every jokamachi follows the spiral plan. [strong]

**Expansion heading.** Along inland sea (Seto Naikai) and Tokaido road — a linear chain of castle-towns.
- along_coast + follow_trade_route
- Evidence: Tokaido Road geography; sankin-kotai biennial travel infrastructure. [strong]

**Signature placement quirk.** Spiral-moat castle silhouette with shrine at the adjacent hillside and terraced rice paddies stepping down from the castle plateau.

**Open research questions.** Shinto shrine placement varies wildly (mountain vs. sea vs. forest) — the dominant pattern is sacred-mountain proximity, but urban Inari shrines buck this. Probably just forest_grove default.

---

### Lakota (Lakota)

**Historical era & geography.** Plains Lakota under Chief Gall, Little Bighorn era (1876). Northern plains from Black Hills east to the Missouri.

**Starting TC preference.**
- Primary terrain: plain
- Secondary terrain: river
- Evidence: Lakota winter camps clustered along the Missouri, Yellowstone, and Little Bighorn river valleys for timber and shelter; summer sundance grounds on open plains. [strong]

**House / residential placement.** Tipi camp-circles (hocoka) with council lodge at center; camps rotated seasonally following bison.
- Axis: pastoral_dispersed (with circular clustering)
- Evidence: Standing Rock, Pine Ridge, Rosebud ethnography; Mooney's Calendar History. [strong]

**Economic building placement.** No permanent economic buildings — bison hunt is the primary economy. Drying racks and meat caches near the camp.
- Axis: pastoral_dispersed
- Evidence: Plains ethnoarchaeology; Catlin's paintings. [strong]

**Military building placement.** No fixed military architecture. Warrior society (akicita) lodges within the camp circle.
- Posture: mobile_satellite
- Evidence: Akicita society documentation (Walker, Lakota Belief and Ritual). [strong]

**Religious / cultural building placement.** Sundance lodge at camp center during summer; sacred site shrines on named hills (Bear Butte, Devils Tower) rather than built structures.
- Axis: center (sundance) + hilltop (sacred site, natural)
- Evidence: Lakota sacred-geography literature (Black Elk Speaks); Bear Butte ceremonial history. [strong]

**Trade / market placement.** Trading posts at river crossings (Fort Laramie, Fort Pierre) where Lakota met US/European traders.
- Axis: riverside (crossing)
- Evidence: Fort Laramie treaty-council history. [strong]

**Defensive architecture.** None; mobility IS the defense. Occasional breastworks at ambush sites (Little Bighorn Indian defensive positions) but nothing permanent.
- Wall archetype: None (code: MobileNoWalls)
- Wall placement logic: no_walls_raiding
- Evidence: Plains warfare ethnography; Little Bighorn battlefield archaeology. [strong]

**Expansion heading.** Following bison herds — north to Milk River, west to Yellowstone basin, east to Minnesota border.
- toward_pasture
- Evidence: 19th-c. Lakota migration maps (Oglala, Hunkpapa, Miniconjou seasonal ranges). [strong]

**Signature placement quirk.** Concentric tipi-circle with council lodge center, astride a river valley that provides winter timber — no stone, no walls, visibly ephemeral on the map.

**Open research questions.** Chief Gall era (1876) is post-reservation-pressure — whether the camp-circle pattern tightens into more river-fixed winter camps by this date. Answer: yes, somewhat.

---

### Maltese (Maltese)

**Historical era & geography.** Knights Hospitaller under Jean Parisot de Valette, 16th c. Grand Harbour of Malta; post-Great-Siege fortification era.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: island
- Evidence: Malta IS the civ — Valletta, Birgu, Senglea, Mdina — all harbor or inland limestone ridge sites. [strong]

**House / residential placement.** Terraced limestone townhouses in dense Valletta grid; auberges housed by langue.
- Axis: fortified_interior
- Evidence: Francesco Laparelli's 1566 grid plan for Valletta. [strong]

**Economic building placement.** Grain imports from Sicily arrived at Grand Harbour warehouses; few farms (island is poor for agriculture).
- Axis: coast (harbor warehouse)
- Evidence: Hospitaller-era grain-import records (Bonello, Histories of Malta). [strong]

**Military building placement.** Knights' auberges and armory within the fortified city; arsenals at the harbor.
- Posture: clustered_central + coast (arsenal)
- Evidence: Valletta's Auberge de Castille and Sacra Infermeria archaeology. [strong]

**Religious / cultural building placement.** St John's Co-Cathedral at Valletta core; chapel-per-langue within auberges.
- Axis: center
- Evidence: Cassar's 1573 Co-Cathedral; Caravaggio's paintings still in situ. [strong]

**Trade / market placement.** Harbor quays at Marsamxett and Grand Harbour; inner-city market at Pjazza San Gorg.
- Axis: coast
- Evidence: Hospitaller-era harbor records. [strong]

**Defensive architecture.** Star-fort bastioned lines of Valletta/Floriana/Cottonera; Fort St Elmo; chain-towers at harbor entrance.
- Wall archetype: FortressRing (+ ChainTowers at harbor)
- Wall placement logic: ring_around_core + coast_batteries + chokepoint_seals
- Evidence: Laparelli/Cassar fortification plans; still intact. [strong]

**Expansion heading.** Limited by island geography — secondary TCs occupy Mdina (interior ridge) and Birgu (opposite harbor bank).
- outward_rings (constrained)
- Evidence: Malta's entire fortified-town network is mapped within 30 km². [strong]

**Signature placement quirk.** Every town is a star-fort bastioned enceinte directly on the coast with a chain-tower guarding the harbor mouth — a Mediterranean-order-state silhouette unlike any other civ.

**Open research questions.** When played on non-island maps, does Maltese fall back to FortressRing-only or synthesize coast by placing extra docks? Suggest: fall back to FortressRing with coast-battery accent on any water tile.

---

### Mexicans (Mexicans)

**Historical era & geography.** Early Mexican republic under Hidalgo (Grito de Dolores, 1810). Viceroyalty-to-republic transition; hacienda-and-silver-mine geography across the central plateau.

**Starting TC preference.**
- Primary terrain: highland_pasture (altiplano)
- Secondary terrain: hill
- Evidence: Mexico City, Guanajuato, Zacatecas, Queretaro all sit on the central plateau 1500–2400m. [strong]

**House / residential placement.** Spanish grid town (plaza mayor + traza) with parish at center; hacienda big-house with peon quarters on rural estates.
- Axis: center (grid town) + pastoral_dispersed (hacienda)
- Evidence: Laws of the Indies (1573) codified grid-town plans; hacienda archaeology across Guanajuato. [strong]

**Economic building placement.** Silver mines in sierras (Guanajuato, Zacatecas); maize/agave haciendas on plateau; refineries at mine-town outskirts.
- Axis: hill (mine) + plain (hacienda)
- Evidence: Brading's Miners and Merchants; colonial silver-mining geography. [strong]

**Military building placement.** Presidio forts at northern frontier (Alta California / Texas); insurgent forces in Hidalgo's era mustered at parish churches and mine workshops.
- Posture: frontier_line (presidio) + clustered_central (parish muster)
- Evidence: Presidio geography (Moorhead, The Presidio); Hidalgo's Grito at Dolores parish. [strong]

**Religious / cultural building placement.** Parroquia and basilica at plaza mayor; shrine of Guadalupe as national pilgrimage node.
- Axis: center
- Evidence: Laws of the Indies; Guadalupe shrine history. [strong]

**Trade / market placement.** Market arcades on plaza mayor; trade posts at camino real junctions linking silver-mine output to Veracruz.
- Axis: center + follow_trade_route
- Evidence: Camino Real de Tierra Adentro UNESCO documentation. [strong]

**Defensive architecture.** Presidio star-forts on northern frontier; masonry-wall haciendas; urban barricades during insurgency.
- Wall archetype: FrontierPalisades (presidio) + UrbanBarricade (insurgent)
- Wall placement logic: frontier_line_only + village_palisades
- Evidence: Presidio archaeology (Tucson, San Antonio, Loreto). [strong]

**Expansion heading.** Northward up the camino real toward Alta California and Texas; silver-mine push into the sierras.
- follow_trade_route + frontier_push
- Evidence: Viceroyalty expansion 1600–1820. [strong]

**Signature placement quirk.** Grid town with central cathedral-and-plaza-mayor plus outlying hacienda compound — the Laws-of-the-Indies template replicated everywhere.

**Open research questions.** Hidalgo-era insurgent doctrine differs from established viceregal geography; the Rev-civ (ANWMexicans) captures the insurgent phase better.

---

### Ottomans (Ottomans)

**Historical era & geography.** Ottoman Empire under Suleiman the Magnificent, mid-16th c. Constantinople-centered; Balkan-Anatolian-Syrian-Egyptian span.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: river
- Evidence: Istanbul on Bosporus, Edirne on Maritsa, Bursa at Sea of Marmara — Ottoman capitals are water-anchored. [strong]

**House / residential placement.** Konak courtyard-houses in mahalle wards; each mahalle organized around its mosque.
- Axis: fortified_interior
- Evidence: Ottoman urban-form literature (Cerasi, The Ottoman City). [strong]

**Economic building placement.** Bedesten covered-bazaar at city center; kervansaray serais on trade routes; timar agricultural grants on Anatolian plain.
- Axis: crossroads (bedesten) + plain (timar)
- Evidence: Grand Bazaar of Istanbul archaeology; timar registry (tapu tahrir). [strong]

**Military building placement.** Janissary barracks (At Meydani, Etmeydani) adjacent to the palace complex; frontier fortresses (Belgrade, Buda, Temesvar).
- Posture: clustered_central (Janissary) + frontier_line (frontier fortress)
- Evidence: Ottoman military-geography literature (Murphey, Ottoman Warfare). [strong]

**Religious / cultural building placement.** Selatin (imperial) mosque complexes with kulliye (mosque + madrasa + hospital + soup kitchen) dominating the skyline; ecumenical patriarch and Armenian quarter tolerated in separate districts.
- Axis: hilltop (Sinan's skyline-dominant siting) + center
- Evidence: Sinan's Suleymaniye, Selimiye siting principles (Necipoglu, The Age of Sinan). [strong]

**Trade / market placement.** Bedesten at city core; han caravanserais on the Silk Road; imperial arsenal (Tersane) at Golden Horn.
- Axis: crossroads + coast
- Evidence: Evliya Celebi travelogue; han geography across Anatolia. [strong]

**Defensive architecture.** Theodosian-walls-inherited-and-maintained at Istanbul; massive stone fortresses at Balkan and Danube frontier.
- Wall archetype: FortressRing
- Wall placement logic: ring_around_core + frontier_line_only
- Evidence: Ottoman fortress surveys of Belgrade, Buda, Nis. [strong]

**Expansion heading.** Along Danube, around Mediterranean, up Red Sea — a water-rim imperial expansion.
- along_coast + follow_trade_route + frontier_push
- Evidence: Suleiman-era expansion atlas. [strong]

**Signature placement quirk.** Skyline dominated by Sinan-style domed mosque with minarets on hills; kulliye complex radiating charitable and educational institutions — a distinct imperial-Islamic urban signature.

**Open research questions.** None critical; Ottoman urban form is one of the best-documented premodern systems.

---

### Portuguese (Portuguese)

**Historical era & geography.** Portuguese maritime empire under Henry the Navigator, 15th c. Atlantic-coast base with African/Indian/Brazilian feitoria (factory) chain.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: river
- Evidence: Lisbon on Tagus, Porto on Douro, Sagres on the Algarve coast — Portuguese core is entirely maritime. [strong]

**House / residential placement.** Terraced townhouses up coastal hillsides (Lisbon's Alfama); rural parish villages in the Minho valleys.
- Axis: coast + river_terrace
- Evidence: Portuguese urban archaeology (Trindade, Urbanismo na Composicao de Portugal). [strong]

**Economic building placement.** Casa da India and royal warehouses at Lisbon waterfront; fishing fleets at every Atlantic harbor; vineyards on Douro terraces.
- Axis: coast + river
- Evidence: Casa da India records; Port wine historical geography (Pereira, Portugal). [strong]

**Military building placement.** Naval arsenal at Ribeira das Naus (Lisbon); overseas feitoria garrisons (Mina, Ormuz, Malacca, Goa).
- Posture: clustered_central + coast (feitoria)
- Evidence: Portuguese fortified-factory network documentation (Newitt, Portuguese in Africa). [strong]

**Religious / cultural building placement.** Manueline monasteries on prominent coastal sites (Jeronimos at Belem, Batalha inland); parish church at village center.
- Axis: coast (monumental) + center (parish)
- Evidence: Manueline architectural atlas. [strong]

**Trade / market placement.** Terreiro do Paco waterfront at Lisbon; feitoria entrepots overseas.
- Axis: coast
- Evidence: Lisbon waterfront archaeology; Goa's Ribandar feitoria. [strong]

**Defensive architecture.** Coastal fort chain (Sao Juliao da Barra, Cascais), overseas star-forts (Diu, Ormuz, Mazagan).
- Wall archetype: CoastalBatteries
- Wall placement logic: coast_batteries
- Evidence: Portuguese overseas-fort atlas (Boxer, Portuguese Seaborne Empire). [strong]

**Expansion heading.** Along African coast, around Cape, island-hop to Indian Ocean and Brazil.
- along_coast + island_hop
- Evidence: Henry-the-Navigator voyages; Cabral's Brazil landing. [strong]

**Signature placement quirk.** Coastal star-fort feitoria with royal warehouse at the water plus a Manueline-ornament church — the Portuguese overseas silhouette replicated from Mazagan to Macao.

**Open research questions.** None critical.

---

### Russians (Russians)

**Historical era & geography.** Muscovy under Ivan IV "the Terrible", mid-16th c. Oprichnina terror, Kazan and Astrakhan conquests, Abatis Line frontier.

**Starting TC preference.**
- Primary terrain: river
- Secondary terrain: forest_edge
- Evidence: Moscow on Moskva, Novgorod on Volkhov, Kazan on Volga — Muscovite core cities are river-anchored at the forest-steppe edge. [strong]

**House / residential placement.** Log-isba peasant hamlets in clearings; boyar kremlin palaces within the city fortress; posad traders' quarter outside the kremlin wall.
- Axis: fortified_interior (kremlin) + trade_street (posad)
- Evidence: Muscovite urban archaeology (Kremlin + Posad + Slobodas pattern). [strong]

**Economic building placement.** Serf-worked grain fields in cleared forest; fur trade routes north; salt and iron works at Solovki and Tula.
- Axis: forest_edge + river
- Evidence: Kliuchevsky's Course in Russian History; fur-trade geography (Fisher, Russian Fur Trade). [strong]

**Military building placement.** Streltsy regiments quartered in their own slobodas outside the kremlin; frontier garrisons along the Abatis Line (Zasechnaya Cherta) / Belgorod Line.
- Posture: clustered_central (streltsy) + frontier_line (Abatis)
- Evidence: Hellie's Enserfment and Military Change; Belgorod Line archaeology. [strong]

**Religious / cultural building placement.** Onion-domed cathedral inside the kremlin (Uspensky, Arkhangelsky); walled monasteries (Trinity-Sergius, Solovetsky) as defensive outposts.
- Axis: center (cathedral) + forest_grove (monastery)
- Evidence: Russian church-geography literature; Trinity-Sergius history. [strong]

**Trade / market placement.** Riverside trading wharves; Red Square market outside the Kremlin wall; portage towns on Volga-Dvina watershed.
- Axis: river + crossroads
- Evidence: Muscovite trade literature (Matthew, Novgorod). [strong]

**Defensive architecture.** Wooden palisade frontier (Abatis / Zasechnaya Cherta) with log blockhouses; masonry kremlins at major cities.
- Wall archetype: FrontierPalisades
- Wall placement logic: frontier_line_only (Abatis) + ring_around_core (kremlin)
- Evidence: Davies's Warfare, State and Society on the Black Sea Steppe. [strong]

**Expansion heading.** Down the Volga (Kazan 1552, Astrakhan 1556); up northern rivers into Siberia; south into the Wild Field as the Abatis Line advances.
- upriver + frontier_push
- Evidence: Muscovite-to-Tsardom expansion atlas; Ivan IV's Kazan campaign. [strong]

**Signature placement quirk.** Log-palisade Abatis Line running across the forest-steppe frontier in a zigzag, with stone-kremlin-plus-onion-dome core cities — instantly Russian.

**Open research questions.** Oprichnina-era (Ivan IV specific) unique sloboda palace at Alexandrov — probably too narrow a detail for the modal.

---

### Spanish (Spanish)

**Historical era & geography.** Spain under Isabella I of Castile, late 15th c. Reconquista-complete Iberia; Granada 1492; first Atlantic voyages.

**Starting TC preference.**
- Primary terrain: plain (meseta)
- Secondary terrain: hill
- Evidence: Castilian capitals (Valladolid, Toledo, Burgos) sit on the central meseta; Granada on sierra foothill; Seville on Guadalquivir. [strong]

**House / residential placement.** Medina-style walled town center; after Reconquista, whitewashed pueblos on hilltops (Andalusian model); mudejar mixed quarters in reconquered south.
- Axis: fortified_interior (medina) + hilltop (pueblo)
- Evidence: Castilian urban archaeology; Alhambra-era Granada. [strong]

**Economic building placement.** Mesta transhumant sheep-walks across the meseta; olive and vine in Andalusia; royal arsenals at Seville (Casa de Contratacion post-1503).
- Axis: plain (mesta) + coast (Casa de Contratacion)
- Evidence: Mesta literature (Klein, Mesta: A Study in Spanish Economic History). [strong]

**Military building placement.** Tercios garrisoned at royal fortresses; Reconquista-era frontier castles on the Extremadura-Andalusia line; Santa Hermandad urban militias.
- Posture: frontier_line + clustered_central
- Evidence: Tercio doctrine literature; castillo de la Mota (Medina del Campo) archaeology. [strong]

**Religious / cultural building placement.** Cathedral at plaza mayor; pilgrimage routes (Camino de Santiago) anchored on hilltop shrines (Montserrat, Covadonga).
- Axis: center + hilltop
- Evidence: Castilian cathedral geography; Camino de Santiago UNESCO documentation. [strong]

**Trade / market placement.** Plaza mayor market arcades; after 1503, Casa de Contratacion centralized Atlantic trade at Seville.
- Axis: crossroads + coast
- Evidence: Seville Casa de Contratacion archaeology. [strong]

**Defensive architecture.** Medieval concentric castle (Segovia Alcazar, Coca) + Reconquista frontier-castle chain; coastal watch-towers (torres de vigia) vs. Barbary corsairs.
- Wall archetype: FortressRing (+ CoastalBatteries Mediterranean coast)
- Wall placement logic: ring_around_core + frontier_line_only + coast_batteries
- Evidence: Spanish castillo atlas; torres de vigia inventory. [strong]

**Expansion heading.** Reconquista-southward; post-1492, Atlantic island-hop (Canaries → Caribbean → Mexico → Peru).
- frontier_push + island_hop
- Evidence: Reconquista and Columbian expansion atlases. [strong]

**Signature placement quirk.** Whitewashed hilltop pueblo with a fortified church-castle at the summit, plus a Meseta sheepwalk corridor — the Castile-La Mancha silhouette.

**Open research questions.** None critical.

---

### Swedes (Swedes)

**Historical era & geography.** Swedish Empire under Gustavus Adolphus, early 17th c. Baltic littoral; iron-and-forest economy; Carolean army doctrine.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: forest_edge
- Evidence: Stockholm on Malaren-Baltic junction; Gothenburg on Kattegat; Uppsala inland but river-linked — Swedish core is coastal/lake. [strong]

**House / residential placement.** Red-painted torp and farm isolated in forest clearings; church-village cluster at parish center.
- Axis: pastoral_dispersed (torp) + center (parish)
- Evidence: Swedish rural settlement literature (Lagerlof et al., Dala-Mora ethnography). [strong]

**Economic building placement.** Bergslagen iron mines and bruk forges; timber-rafting rivers; Baltic port warehouses.
- Axis: forest_edge (iron) + coast (timber export)
- Evidence: Bergslagen iron-district archaeology; Swedish timber-export history. [strong]

**Military building placement.** Indelningsverk allotment-based regimental muster system — each regiment tied to a province; frontier fortresses at Narva, Riga, Stralsund.
- Posture: frontier_line + mobile_satellite
- Evidence: Glete's War and the State in Early Modern Europe (Swedish military system). [strong]

**Religious / cultural building placement.** Lutheran parish church with detached belfry at village center; Uppsala cathedral as primatial seat.
- Axis: center
- Evidence: Swedish parish-church typology; Uppsala domkyrka history. [strong]

**Trade / market placement.** Gamla Stan merchant quarter in Stockholm; export-port warehouses at Riga/Stralsund.
- Axis: coast + trade_street
- Evidence: Hanseatic-inherited Stockholm urban form. [strong]

**Defensive architecture.** Bastioned sea-fortresses (Vaxholm, Suomenlinna later); ring-forts at Baltic holdings.
- Wall archetype: CoastalBatteries + FortressRing
- Wall placement logic: coast_batteries + ring_around_core
- Evidence: Swedish fortification surveys (Glete). [strong]

**Expansion heading.** Across the Baltic — to Finland, Estonia, Livonia, Pomerania, briefly Brandenburg.
- along_coast + island_hop
- Evidence: Swedish Empire-era expansion atlas. [strong]

**Signature placement quirk.** Red-ochre Falu-painted torp scattered through forest with a Baltic-rim bastioned port-fortress — a distinct northern-forest + maritime silhouette.

**Open research questions.** Gustavus-era expansion into Germany (Thirty Years War) adds a riverine/continental secondary mode we may want to capture.

---

### United States (UnitedStates)

**Historical era & geography.** Early republic under Washington, late 18th c. Thirteen-colonies-to-federal-republic transition; Eastern Seaboard core with Appalachian frontier.

**Starting TC preference.**
- Primary terrain: river
- Secondary terrain: coast
- Evidence: Philadelphia, New York, Boston, Charleston — federal-era capitals are tidal-river ports; the Ohio/Mississippi opens interior expansion. [strong]

**House / residential placement.** Jeffersonian yeoman farmstead (160-acre quarter-section under later Homestead-era; earlier New England township model).
- Axis: pastoral_dispersed + trade_street (county seat)
- Evidence: Land Ordinance of 1785 township-and-range survey. [strong]

**Economic building placement.** Mills on fall-line rivers (Lowell, Paterson); tobacco/cotton plantations on coastal plain; wheat on Pennsylvania / Ohio valleys.
- Axis: river (fall-line mill) + plain (plantation/wheat)
- Evidence: Early American industrial archaeology; Lowell Mill Girls historiography. [strong]

**Military building placement.** Federal arsenals at strategic rivers (Springfield MA, Harpers Ferry VA); frontier forts (Fort Washington, Fort Niagara).
- Posture: frontier_line
- Evidence: Federal arsenal geography (Wiley, Arsenals of American Independence). [strong]

**Religious / cultural building placement.** Congregationalist/Anglican church at the village green; Jeffersonian republican civic monuments (Capitol, Monticello) on hills.
- Axis: center + hilltop
- Evidence: New England town-green geography; Capitol Hill siting. [strong]

**Trade / market placement.** Waterfront markets in port cities; county-seat court-square market in rural counties.
- Axis: coast + crossroads
- Evidence: Early-republic urban-market studies. [strong]

**Defensive architecture.** Second-system coastal forts (Fort McHenry, Castle Clinton); frontier palisade forts on Ohio-Mississippi line.
- Wall archetype: CoastalBatteries + FrontierPalisades
- Wall placement logic: coast_batteries + frontier_line_only
- Evidence: US fortification-system surveys (McPherson, Seacoast Fortifications of the United States). [strong]

**Expansion heading.** Westward across the Appalachians (Cumberland Gap, Ohio River); along-coast secondary.
- frontier_push + follow_trade_route
- Evidence: Turner's Frontier Thesis; Land Ordinance expansion. [strong]

**Signature placement quirk.** Township-grid farmsteads marching westward with a fall-line mill town at every major river crossing — the Land Ordinance rectilinear signature.

**Open research questions.** Washington-era US is very small (13 colonies + Northwest Territory); Jefferson-era (Louisiana Purchase) expands the footprint. Base-civ is Washington per roster.

---

# REVOLUTION CIVS (26)

---

### Americans (ANWAmericans)

**Historical era & geography.** Jeffersonian republic, early 19th c. Louisiana Purchase doubled the nation; Lewis and Clark expansion west.

**Starting TC preference.**
- Primary terrain: river
- Secondary terrain: plain
- Evidence: Jeffersonian expansion follows the Mississippi-Missouri axis; new states (Ohio, Indiana, Illinois) are river-anchored. [strong]

**House / residential placement.** Yeoman log-cabin homesteads on section-line farms; Federal-style townhouses in county seats.
- Axis: pastoral_dispersed
- Evidence: Jeffersonian agrarian ideal; Land Ordinance geography. [strong]

**Economic building placement.** Grist mills on Appalachian fall-line rivers; cotton gins on southern plantations; early factories at water-power sites.
- Axis: river + plain
- Evidence: Early industrial geography of the US. [strong]

**Military building placement.** Federal arsenals; Corps of Discovery-era Missouri-River frontier forts; militia muster at county seat.
- Posture: frontier_line
- Evidence: Jefferson-era military-post geography. [plausible]

**Religious / cultural building placement.** Second-Great-Awakening revival-meeting grounds + established Anglican/Presbyterian/Congregational churches at county seats.
- Axis: center + dispersed (revival)
- Evidence: Second Great Awakening historiography. [strong]

**Trade / market placement.** Mississippi-Ohio river ports (Pittsburgh, Cincinnati, Louisville, New Orleans); eastern seaboard markets.
- Axis: river + coast
- Evidence: Antebellum river-trade historiography (Hunter, Steamboats on the Western Rivers). [strong]

**Defensive architecture.** Second-system masonry coastal forts; Missouri-River frontier log forts (Bellefontaine, Osage).
- Wall archetype: CoastalBatteries + FrontierPalisades
- Wall placement logic: coast_batteries + frontier_line_only
- Evidence: US fortification atlas. [strong]

**Expansion heading.** Westward along the Ohio/Missouri/Mississippi; trans-Appalachian frontier push.
- upriver + frontier_push
- Evidence: Lewis and Clark route; Land Ordinance state-creation sequence. [strong]

**Signature placement quirk.** Gridded township farms marching west with a river-port frontier town at every major confluence (Pittsburgh, Louisville, St Louis).

**Open research questions.** Jefferson era vs. Washington era differentiation — pick Jefferson's western-expansion bias for Rev civ.

---

### Argentines (ANWArgentines)

**Historical era & geography.** Argentine independence under San Martin, 1810s. Pampas core, Andean transit, Rio de la Plata estuary.

**Starting TC preference.**
- Primary terrain: plain (pampas)
- Secondary terrain: river (Rio de la Plata)
- Evidence: Buenos Aires on Rio de la Plata; estancia geography on the open pampas. [strong]

**House / residential placement.** Grid town with central plaza (Laws of the Indies); isolated estancia ranch houses on the pampas.
- Axis: center (grid town) + pastoral_dispersed (estancia)
- Evidence: Spanish colonial grid; Argentine estancia archaeology. [strong]

**Economic building placement.** Estancia cattle ranches; saladero meat-salting works at river ports; grain farms in Santa Fe / Entre Rios.
- Axis: plain + river
- Evidence: Argentine economic history (Rock, Argentina 1516–1987). [strong]

**Military building placement.** Army of the Andes mobilized at Mendoza before the trans-Andean crossing; frontier forts (fortines) against Mapuche on southern pampas.
- Posture: mobile_satellite + frontier_line
- Evidence: San Martin's Mendoza campaign documentation. [strong]

**Religious / cultural building placement.** Cathedral at plaza mayor; pampas chapels at estancia centers.
- Axis: center
- Evidence: Spanish-colonial religious-geography inheritance. [strong]

**Trade / market placement.** Buenos Aires port as sole legal European trade outlet (colonial era); interior fairs at Cordoba / Salta.
- Axis: river + crossroads
- Evidence: Late-colonial/early-republic trade-route historiography. [strong]

**Defensive architecture.** Earthen fortines (ditch-and-palisade posts) along the pampas frontier; coastal batteries at Buenos Aires.
- Wall archetype: FrontierPalisades + CoastalBatteries
- Wall placement logic: frontier_line_only + coast_batteries
- Evidence: Fortin-line archaeology (Zarate, Rojas). [strong]

**Expansion heading.** Westward across the Andes (San Martin's liberation campaign) and southward onto Patagonian frontier.
- frontier_push + follow_trade_route
- Evidence: San Martin's 1817 Andean crossing. [strong]

**Signature placement quirk.** Pampas estancia with a single line of fortines running south-west against Mapuche country plus a port-fortress at the Rio de la Plata — distinctive Southern Cone silhouette.

**Open research questions.** How strongly to weight Andean secondary for transit TCs vs. pampas primary.

---

### Baja Californians (ANWBajaCalifornians)

**Historical era & geography.** Mexican Baja California under Alvarado, 1830s–40s. Peninsular frontier with Jesuit/Franciscan mission-presidio geography; arid desert coast.

**Starting TC preference.**
- Primary terrain: desert_oasis
- Secondary terrain: coast
- Evidence: Loreto, La Paz, Mulege, San Ignacio — Baja mission sites are all arroyo-oasis springs near the Sea of Cortes. [strong]

**House / residential placement.** Mission compound with adjacent Indian rancheria; rancho cattle-stations dispersed inland.
- Axis: compound_enclosed (mission) + pastoral_dispersed (rancho)
- Evidence: Jesuit-Franciscan Baja mission archaeology (Crosby, Antigua California). [strong]

**Economic building placement.** Date-palm and vine oases at mission gardens; pearl-fisheries along the Gulf coast; cattle on inland ranges.
- Axis: desert_oasis + coast
- Evidence: Jesuit-era Baja economic records. [strong]

**Military building placement.** Small presidio garrisons at Loreto and La Paz; mobile cavalry for inland ranch defense.
- Posture: frontier_line + mobile_satellite
- Evidence: Baja presidio archaeology. [plausible]

**Religious / cultural building placement.** Mission church as the literal nucleus of every settlement.
- Axis: center
- Evidence: Baja mission-chain architecture. [strong]

**Trade / market placement.** Loreto/La Paz harbors for coastal trade; overland mule routes to Alta California.
- Axis: coast
- Evidence: Colonial-era Gulf-of-California trade. [plausible]

**Defensive architecture.** Low adobe presidio walls; mission compound walls.
- Wall archetype: FrontierPalisades
- Wall placement logic: village_palisades
- Evidence: Baja presidio archaeology. [plausible]

**Expansion heading.** Along the peninsula, mission-leap-frogging north-south.
- along_coast + follow_trade_route
- Evidence: Jesuit mission-chain sequence. [strong]

**Signature placement quirk.** Single mission-plus-presidio oasis cluster strung along the arid peninsula — a sparse, linear rosary of settlements.

**Open research questions.** Alvarado's exact military-placement doctrine is under-documented; most of this extrapolates from mission-era geography. [speculative] for military specifics.

---

### Barbary (ANWBarbary)

**Historical era & geography.** Barbary corsair states (Algiers, Tunis, Tripoli) under Ottoman-vassal / autonomous beys, 16th–19th c. Leader anchor: Barbarossa (Hayreddin) / Algiers corsair power.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: desert_oasis
- Evidence: Algiers, Tunis, Tripoli are all fortified harbors with mole-built ports; inland was Berber oasis country. [strong]

**House / residential placement.** Dense whitewashed casbah on steep coastal hillside; Berber ksar/kasr compounds inland.
- Axis: fortified_interior
- Evidence: Algiers Casbah UNESCO documentation; Maghreb ksar archaeology. [strong]

**Economic building placement.** Prize-slave markets at the port (the economic engine was corsair prize-taking); oasis agriculture inland.
- Axis: coast
- Evidence: Barbary corsair economic history (Davis, Christian Slaves Muslim Masters). [strong]

**Military building placement.** Janissary odjak barracks at the casbah; corsair galley berths at the mole-port; Bey's palace with adjacent guard quarters.
- Posture: clustered_central + coast
- Evidence: Ottoman-era Algiers military-administrative geography. [strong]

**Religious / cultural building placement.** Friday mosque within casbah; Sufi-marabout shrines in the surrounding hills.
- Axis: center (Jami) + hilltop (marabout)
- Evidence: Maghrebi Islamic architectural geography. [strong]

**Trade / market placement.** Prize-market and trans-Saharan caravan market at the port; slave auction at the Badestan.
- Axis: coast + crossroads
- Evidence: Barbary market historiography. [strong]

**Defensive architecture.** Mole-fortified harbor with chain-boom across the port mouth; coastal watch-towers (borj); casbah citadel above the town.
- Wall archetype: CoastalBatteries (+ ChainTowers at harbor)
- Wall placement logic: coast_batteries + chokepoint_seals
- Evidence: Algiers harbor archaeology (Peñón de Argel, mole built 1529–1531 by Barbarossa). [strong]

**Expansion heading.** Along the Maghreb coast and outward raiding across the Mediterranean (even up to Iceland — 1627 Algiers raid).
- along_coast + island_hop (raid zones)
- Evidence: Barbary raid-geography literature. [strong]

**Signature placement quirk.** Casbah-on-steep-hill with mole-and-chain-tower harbor plus inland marabout shrines — a Mediterranean-Islamic corsair silhouette distinct from Ottoman imperial cities.

**Open research questions.** How to model the pan-Mediterranean raiding radius on a single-map scale. Outside placement doc scope.

---

### Brazil (ANWBrazil)

**Historical era & geography.** Empire of Brazil under Pedro I, 1822 onward. Atlantic coast capitals (Rio, Salvador, Recife); sertao interior; sugar/coffee plantation economy.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: river
- Evidence: Salvador, Rio, Recife, Olinda — Portuguese-inherited Brazilian capitals are all on Atlantic harbors. [strong]

**House / residential placement.** Sugar-mill casa-grande with slave-quarters senzala; urban colonial townhouse along grid streets.
- Axis: coast + pastoral_dispersed (engenho)
- Evidence: Freyre's Casa-Grande e Senzala; Brazilian colonial-economic archaeology. [strong]

**Economic building placement.** Sugar engenhos on coastal Zona da Mata; coffee fazendas on Paulista plateau; gold mines in Minas Gerais sertao.
- Axis: coast (engenho) + hill (mines)
- Evidence: Brazilian colonial economic historiography. [strong]

**Military building placement.** Portuguese-era coastal forts inherited (Sao Marcelo, Cinco Pontas); imperial arsenal at Rio.
- Posture: coast (forts) + clustered_central
- Evidence: Brazilian colonial fortress atlas. [strong]

**Religious / cultural building placement.** Baroque church on every engenho and urban square; pilgrimage basilicas in Minas (Bom Jesus de Matosinhos).
- Axis: center + hilltop
- Evidence: Aleijadinho's Minas Baroque; Brazilian colonial-church geography. [strong]

**Trade / market placement.** Harbor entrepot warehouses at Rio/Salvador; interior feiras at regional crossroads.
- Axis: coast
- Evidence: Brazilian port-trade historiography. [strong]

**Defensive architecture.** Portuguese-inherited coastal star-forts; imperial-era arsenal at Rio.
- Wall archetype: CoastalBatteries
- Wall placement logic: coast_batteries
- Evidence: Brazilian colonial fortress atlas. [strong]

**Expansion heading.** Along coast north-south; up rivers into Amazon and sertao (bandeirante expansion).
- along_coast + upriver + frontier_push
- Evidence: Bandeirante-expansion historiography. [strong]

**Signature placement quirk.** Coastal star-fort plus sugar engenho hinterland plus baroque gold-church silhouettes in Minas Gerais — a tri-zonal Brazilian template.

**Open research questions.** Pedro I era vs. colonial era — Pedro's reign is post-1822 so model trends imperial-centralized.

---

### Californians (ANWCalifornians)

**Historical era & geography.** Alta California under Vallejo / Bear Flag Revolt, 1830s–1840s. Mission-presidio-rancho triad along the coast.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: river (coastal valleys)
- Evidence: San Diego, Monterey, San Francisco presidios; missions strung along El Camino Real. [strong]

**House / residential placement.** Mission compound at the core; rancho hacienda on inland valleys; pueblo grid town (Los Angeles, San Jose).
- Axis: compound_enclosed + pastoral_dispersed
- Evidence: Spanish-colonial California historiography; Rancho-era land-grant archaeology. [strong]

**Economic building placement.** Mission gardens + vineyards; rancho cattle-hide exports to Boston traders; tallow vats at ports.
- Axis: coast + pastoral_dispersed
- Evidence: Dana's Two Years Before the Mast; California hide-and-tallow trade. [strong]

**Military building placement.** Four royal presidios (San Diego, Monterey, San Francisco, Santa Barbara); mission guard detachments.
- Posture: frontier_line (coast)
- Evidence: California presidio archaeology. [strong]

**Religious / cultural building placement.** Mission chapel as literal settlement nucleus; 21-mission chain is the cultural backbone.
- Axis: center
- Evidence: California mission chain UNESCO documentation. [strong]

**Trade / market placement.** Monterey as royal customs house; informal trade at Yerba Buena / San Diego cove with Boston ships.
- Axis: coast
- Evidence: Alta California trade historiography. [strong]

**Defensive architecture.** Adobe-wall presidios with corner bastions; mission compound walls.
- Wall archetype: FrontierPalisades (adobe presidio)
- Wall placement logic: coast_batteries + village_palisades
- Evidence: Monterey/San Francisco presidio excavations. [strong]

**Expansion heading.** Along El Camino Real up the coast — mission-leap-frog between San Diego and Sonoma.
- along_coast + follow_trade_route
- Evidence: El Camino Real UNESCO tentative listing. [strong]

**Signature placement quirk.** String of mission-presidio pairs along El Camino Real, one day's ride apart — a linear rosary of settlements along the coast.

**Open research questions.** Vallejo-era vs. Russian presence (Fort Ross) — probably omit for scope.

---

### Canadians (ANWCanadians)

**Historical era & geography.** British Canada under Isaac Brock, War of 1812 era. Great Lakes / St Lawrence frontier; British North America defending against US invasion.

**Starting TC preference.**
- Primary terrain: river (St Lawrence / Great Lakes)
- Secondary terrain: forest_edge
- Evidence: Quebec, Montreal, Kingston, York (Toronto) all sit on the St Lawrence-Great Lakes waterway. [strong]

**House / residential placement.** Seigneurial long-lot farms fronting the St Lawrence; Upper Canada township grid; log-cabin frontier homesteads.
- Axis: river_terrace (long-lot) + pastoral_dispersed
- Evidence: French-Canadian rang geography; Upper Canada township surveys. [strong]

**Economic building placement.** Timber rafts on Ottawa River; fur-trade entrepots (Montreal, Michilimackinac); wheat farms on Ontario peninsula.
- Axis: river + forest_edge
- Evidence: Canadian timber-trade historiography (Lower, Great Britain's Woodyard). [strong]

**Military building placement.** British regulars at Fort Henry (Kingston), Fort George (Niagara), Fort Mississauga; provincial militia at county seats.
- Posture: frontier_line (Great Lakes)
- Evidence: War of 1812 fort atlas. [strong]

**Religious / cultural building placement.** Catholic parish church at center of French-Canadian village; Anglican cathedral at colonial seats.
- Axis: center
- Evidence: Quebec seigneurial-village geography. [strong]

**Trade / market placement.** Hudson's Bay Company posts on interior waterways; Montreal/Quebec wharves.
- Axis: river + follow_trade_route
- Evidence: HBC post archaeology. [strong]

**Defensive architecture.** Martello towers at Kingston; bastioned fortresses (Quebec citadel, Fort Henry); log-blockhouse frontier.
- Wall archetype: FortressRing (+ ChainTowers as Martello analogues)
- Wall placement logic: ring_around_core + frontier_line_only + coast_batteries
- Evidence: Martello-tower inventory of Canada; Quebec citadel archaeology. [strong]

**Expansion heading.** West along the Great Lakes and up the Ottawa/St Lawrence to the Red River.
- along_coast (lakeshore) + upriver + follow_trade_route
- Evidence: HBC and North West Company expansion. [strong]

**Signature placement quirk.** Martello-tower coast-ring on the Great Lakes plus seigneurial long-lot ribbon farms along the St Lawrence — a distinctive riverine-defensive Canadian silhouette.

**Open research questions.** Brock-era (1812) vs. later Canadian-federation era — pick 1812.

---

### Central Americans (ANWCentralAmericans)

**Historical era & geography.** Federal Republic of Central America under Morazan, 1823–1838. Highland volcanic spine; Caribbean-Pacific trans-isthmus.

**Starting TC preference.**
- Primary terrain: highland_pasture
- Secondary terrain: coast
- Evidence: Guatemala City, Antigua, Tegucigalpa, San Salvador, Leon — Central American capitals sit in highland volcanic valleys. [strong]

**House / residential placement.** Spanish grid town with central plaza; rural aldea cluster villages on highland slopes.
- Axis: center (grid) + pastoral_dispersed
- Evidence: Laws of the Indies Central America implementations. [strong]

**Economic building placement.** Coffee on volcanic slopes; indigo on Pacific lowlands; cattle estancias in Honduras plains.
- Axis: hill (coffee) + plain (indigo/cattle)
- Evidence: Central American agricultural historiography (Wortman, Government and Society in Central America). [strong]

**Military building placement.** Federal army centered at Guatemala City; militia at state capitals.
- Posture: clustered_central
- Evidence: Morazan-era military historiography. [plausible]

**Religious / cultural building placement.** Cathedral at plaza mayor; pilgrimage sites (Esquipulas Black Christ).
- Axis: center + hilltop
- Evidence: Central American colonial-church geography. [strong]

**Trade / market placement.** Pacific ports (Acajutla, La Libertad); Caribbean ports (Omoa, Trujillo); central-plaza markets.
- Axis: coast + center
- Evidence: Colonial trade-route historiography. [strong]

**Defensive architecture.** Spanish-inherited colonial masonry forts (San Fernando de Omoa); volcanic-terrain chokepoints.
- Wall archetype: FortressRing + CoastalBatteries
- Wall placement logic: coast_batteries + chokepoint_seals
- Evidence: Omoa fortress archaeology. [strong]

**Expansion heading.** Along the isthmus north-south; outward from Guatemala City to state capitals.
- outward_rings + follow_trade_route
- Evidence: Federal Republic historical geography. [strong]

**Signature placement quirk.** Volcanic-valley Spanish grid town with cathedral-plus-plaza-mayor plus colonial coastal fort at each ocean — a bi-ocean isthmus silhouette.

**Open research questions.** Federal Republic was fragile and short-lived; placement mostly inherits late-colonial patterns.

---

### Chileans (ANWChileans)

**Historical era & geography.** Chilean republic under O'Higgins, 1818 onward. Long narrow country between Andes and Pacific; central valley core.

**Starting TC preference.**
- Primary terrain: river (Central Valley rivers)
- Secondary terrain: coast
- Evidence: Santiago on Mapocho; Valparaiso as principal port; Concepcion on Bio Bio. [strong]

**House / residential placement.** Grid town with plaza de armas; rural hacienda on Central Valley; araucanian mapuche lands south of Bio Bio.
- Axis: center + pastoral_dispersed
- Evidence: Spanish-colonial grid inheritance. [strong]

**Economic building placement.** Central Valley wheat/wine haciendas; Valparaiso port; copper mines in Norte Chico.
- Axis: plain (hacienda) + coast (port)
- Evidence: Chilean economic historiography (Collier, History of Chile). [strong]

**Military building placement.** Army of the Andes billeted at Santiago; Bio Bio frontier forts against Mapuche.
- Posture: frontier_line (Bio Bio)
- Evidence: La Frontera historiography (Bengoa). [strong]

**Religious / cultural building placement.** Cathedral at plaza de armas; miraculous shrines (Andacollo).
- Axis: center
- Evidence: Chilean colonial-church geography. [strong]

**Trade / market placement.** Valparaiso as port; plaza de armas markets; Coquimbo/Iquique saltpeter/copper ports.
- Axis: coast
- Evidence: 19th-c. Chilean trade historiography. [strong]

**Defensive architecture.** Bio Bio frontier palisade forts (Arauco, Yumbel); Valparaiso coastal batteries; Valdivia's 17th-c. star-fort system.
- Wall archetype: FrontierPalisades + CoastalBatteries
- Wall placement logic: frontier_line_only + coast_batteries
- Evidence: Valdivia fortifications complex. [strong]

**Expansion heading.** Southward across Bio Bio into Araucania; northward into Norte Chico/Atacama.
- frontier_push + along_coast
- Evidence: Chilean expansion 1818–1880 (Occupation of Araucania). [strong]

**Signature placement quirk.** Long thin coastal strip with Andean backdrop and Bio Bio frontier palisade chain — a uniquely elongated silhouette constrained by geography.

**Open research questions.** None critical.

---

### Columbians (ANWColumbians)

**Historical era & geography.** Gran Colombia under Bolivar, 1819–1831. Andean spine from Venezuelan Llanos to Ecuadorian sierra.

**Starting TC preference.**
- Primary terrain: hill (Andean highland)
- Secondary terrain: river (Magdalena)
- Evidence: Bogota (2600m), Caracas, Quito — Gran Colombian capitals sit in high Andean valleys. [strong]

**House / residential placement.** Grid town with plaza mayor; llanero ranchos on Venezuelan plains; Andean village clusters on slopes.
- Axis: center + pastoral_dispersed
- Evidence: Spanish-colonial urban geography. [strong]

**Economic building placement.** Cacao haciendas on coast; gold mines in Antioquia; cattle llanos in Venezuela.
- Axis: hill (mines) + coast (cacao) + plain (llanos)
- Evidence: Colombian/Venezuelan colonial economic historiography. [strong]

**Military building placement.** Liberator army mobile through multiple campaigns (Boyaca, Carabobo, Pichincha); fortifications at Cartagena.
- Posture: mobile_satellite + coast (Cartagena)
- Evidence: Bolivar campaign historiography. [strong]

**Religious / cultural building placement.** Cathedral at plaza mayor; colonial baroque churches in Tunja, Popayan.
- Axis: center
- Evidence: New Granada colonial architecture. [strong]

**Trade / market placement.** Cartagena as Atlantic port; Guayaquil as Pacific port; Magdalena River trade.
- Axis: coast + river
- Evidence: Colonial Nueva Granada trade historiography. [strong]

**Defensive architecture.** Cartagena's massive bastioned ring and San Felipe fortress; Andean frontier-fort pattern at Llano edge.
- Wall archetype: CoastalBatteries + FortressRing
- Wall placement logic: coast_batteries + ring_around_core
- Evidence: Cartagena fortifications UNESCO World Heritage; San Felipe de Barajas archaeology. [strong]

**Expansion heading.** Outward along Andean spine — Venezuelan plains to Ecuadorian sierra; liberation push southward to Peru-Bolivia.
- outward_rings + frontier_push
- Evidence: Bolivar's campaigns 1819–1824. [strong]

**Signature placement quirk.** Cartagena bastioned-ring seaport as signature fortification + Andean highland capitals + Llano plain borderland — a tri-zonal silhouette.

**Open research questions.** None critical.

---

### Egyptians (ANWEgyptians)

**Historical era & geography.** Muhammad Ali's Egypt, early 19th c. Nile valley modernization; Ottoman-vassal autonomy.

**Starting TC preference.**
- Primary terrain: river (Nile)
- Secondary terrain: desert_oasis
- Evidence: Every Egyptian settlement follows the Nile strip (Cairo, Alexandria, Asyut, Aswan); oasis towns in Western Desert (Siwa, Bahariya). [strong]

**House / residential placement.** Mud-brick fellah villages on Nile levee; Cairo mahalle wards; rural ezba estates (Muhammad Ali's cotton farms).
- Axis: river_terrace
- Evidence: Egyptian rural archaeology; Muhammad Ali cotton-estate historiography. [strong]

**Economic building placement.** Long-staple cotton (jumel) on Delta estates; sugar refineries in Upper Egypt; grain on Nile floodplain.
- Axis: river
- Evidence: Muhammad Ali industrial-reform historiography (Marsot, Egypt in the Reign of Muhammad Ali). [strong]

**Military building placement.** Citadel of Cairo as military nucleus; Nizam-i-Cedid regiments in new barracks; frontier outposts at Sudan/Sinai.
- Posture: clustered_central (Citadel) + frontier_line
- Evidence: Muhammad Ali army reform literature. [strong]

**Religious / cultural building placement.** Muhammad Ali Mosque on the Citadel hill; medieval mosque clusters in Fatimid Cairo; Coptic churches in Old Cairo.
- Axis: hilltop (Citadel mosque) + center
- Evidence: Islamic Cairo UNESCO documentation. [strong]

**Trade / market placement.** Khan el-Khalili bazaar; Alexandria port; Rosetta/Damietta Nile-mouth ports.
- Axis: center + coast
- Evidence: Cairo bazaar geography; Alexandria port historiography. [strong]

**Defensive architecture.** Citadel of Cairo (Salah al-Din inheritance modernized); Alexandria's Qaitbay fort; Suez/Nile-delta coastal forts.
- Wall archetype: FortressRing (+ CoastalBatteries)
- Wall placement logic: ring_around_core + coast_batteries
- Evidence: Citadel archaeology; Qaitbay fort studies. [strong]

**Expansion heading.** Up Nile into Sudan; across Sinai into Levant (Ibrahim Pasha's Syrian campaign); along Mediterranean coast.
- upriver + frontier_push
- Evidence: Ibrahim Pasha's 1831–1840 Syrian campaign. [strong]

**Signature placement quirk.** Every settlement ribbons along the Nile with the Citadel of Cairo dominating from its hilltop; desert-oasis outliers form isolated bright dots in ochre sand.

**Open research questions.** None critical; Muhammad Ali era is well-documented.

---

### Finnish (ANWFinnish)

**Historical era & geography.** Grand Duchy / Independent Finland under Mannerheim, late 19th to mid 20th c. Forest-lake terrain; Mannerheim Line defense doctrine against Soviet threat.

**Starting TC preference.**
- Primary terrain: forest_edge
- Secondary terrain: wetland (lake/bog)
- Evidence: Finnish settlement follows the lake-forest lacustrine belt; Helsinki, Tampere, Turku, Viipuri all on water/lake shore. [strong]

**House / residential placement.** Red-painted Finnish farmstead in forest clearings; Karelian linear village along a road/river.
- Axis: pastoral_dispersed + trade_street
- Evidence: Finnish rural-settlement ethnography. [strong]

**Economic building placement.** Timber/pulp mills at river mouths; lakeside sawmills; shifting-cultivation forest clearings (huuhta).
- Axis: river + forest_edge
- Evidence: Finnish forestry historiography. [strong]

**Military building placement.** Mannerheim Line bunker-trench system on the Karelian Isthmus; coastal batteries (Suomenlinna); forward rifle-companies in the forest.
- Posture: frontier_line (Mannerheim Line) + coast
- Evidence: Mannerheim Line archaeology; Winter War historiography (Trotter, A Frozen Hell). [strong]

**Religious / cultural building placement.** Lutheran wooden-church-with-detached-bell-tower at parish center; Karelian Orthodox chapels (tsasouna) in the eastern forests.
- Axis: center + forest_grove
- Evidence: Finnish wooden-church architectural atlas. [strong]

**Trade / market placement.** Market square (tori) at town center; lakeside harbors for timber export.
- Axis: center + coast
- Evidence: Finnish urban-form historiography. [strong]

**Defensive architecture.** Mannerheim Line concrete bunkers + anti-tank obstacles + forest-trench anchors; Suomenlinna sea-fortress.
- Wall archetype: FrontierPalisades (as code-compatible stand-in for trench-line)
- Wall placement logic: frontier_line_only + chokepoint_seals + coast_batteries (Suomenlinna)
- Evidence: Mannerheim Line archaeology; Suomenlinna UNESCO documentation. [strong]

**Expansion heading.** Defensive rather than expansive — consolidation along existing lake-forest settlements; Karelian Isthmus focus.
- outward_rings (limited)
- Evidence: Finnish 20th-c. defensive posture. [strong]

**Signature placement quirk.** Bunker-line across the forest-lake isthmus (Mannerheim Line) plus red Falu-painted farms in forest clearings — a uniquely northern trench-defense silhouette.

**Open research questions.** Grand Duchy (19th-c.) vs. Winter War era — lean Winter War for Mannerheim leader anchor.

---

---

### Haitians (ANWHaitians)

**Historical era & geography.** Haitian Revolution under Toussaint Louverture, 1790s–1803. Caribbean island; plantation-to-citadel transformation.

**Starting TC preference.**
- Primary terrain: coast
- Secondary terrain: hill (mountain interior)
- Evidence: Cap-Francais, Port-au-Prince, Les Cayes are coastal; Citadelle Laferriere sits on a 900m peak inland. [strong]

**City/residential placement.** Plantation great-house + slave quarters cluster; post-revolution urban recomposition in Cap-Francais and Port-au-Prince.
- Axis: coast + hill (maroon/mountain)
- Evidence: Haitian colonial/revolutionary archaeology (Dubois, Avengers of the New World). [strong]

**Economic building placement.** Sugar/coffee plantations on plains and slopes; coastal port warehouses; post-revolution subsistence plots.
- Axis: plain (plantation) + coast
- Evidence: Saint-Domingue plantation geography. [strong]

**Military building placement.** Citadelle Laferriere (1805–1820) on Bonnet a l'Eveque peak; coastal defense batteries; mobile revolutionary columns in the mountains.
- Posture: clustered_central (Citadelle) + mobile_satellite (maroon/revolutionary)
- Evidence: Citadelle Laferriere UNESCO documentation. [strong]

**Religious / cultural building placement.** Catholic church at plaza center; vodou peristyle in rural compounds; syncretic shrines.
- Axis: center + dispersed (vodou)
- Evidence: Haitian religious-geography historiography. [strong]

**Trade / market placement.** Cap-Francais and Port-au-Prince harbors; inland markets at crossroads.
- Axis: coast + crossroads
- Evidence: Saint-Domingue trade-port historiography. [strong]

**Defensive architecture.** Citadelle Laferriere as the signature mountain-top fortress (largest in the Americas); coastal forts (Fort Picolet, Fort Dauphin).
- Wall archetype: FortressRing (Citadelle) + CoastalBatteries
- Wall placement logic: ring_around_core + coast_batteries
- Evidence: Haitian fortification atlas; Christophe-era fortress program. [strong]

**Expansion heading.** Limited by island; primary TCs on coast with secondary mountain citadels; cross-island into Santo Domingo during 1822 unification.
- along_coast + toward_hills
- Evidence: Early-Haitian expansion historiography. [strong]

**Signature placement quirk.** Coastal port plus mountain-summit Citadelle connected by winding road — a unique vertical-island defense silhouette.

**Open research questions.** Toussaint era (pre-1803) vs. Christophe Citadelle era (post-1805) — Citadelle is post-Toussaint but defines the Haitian civ signature, so include it.

---

### Hungarians (ANWHungarians)

**Historical era & geography.** Hungarian Revolution under Kossuth, 1848–1849. Pannonian plain; Danube-Tisza river network; Habsburg-era fortress inheritance.

**Starting TC preference.**
- Primary terrain: plain (Pannonian)
- Secondary terrain: river (Danube/Tisza)
- Evidence: Buda-Pest on Danube; Szeged on Tisza; Debrecen on Great Plain — every major Hungarian city is river/plain. [strong]

**House / residential placement.** Linear szalag village with whitewashed long-house pattern; puszta farmstead (tanya) isolated on plain.
- Axis: trade_street + pastoral_dispersed
- Evidence: Hungarian ethnography; tanya-system historiography. [strong]

**Economic building placement.** Wheat on the Great Plain; vineyards in Tokaj/Eger hills; Danube river trade.
- Axis: plain + river
- Evidence: Hungarian agricultural geography. [strong]

**Military building placement.** Honved (national guard) regiments at county seats; Danube fortresses (Komarom, Pest); hussar cavalry dispersed across puszta.
- Posture: clustered_central + mobile_satellite (hussar)
- Evidence: 1848–49 Hungarian army historiography (Deak, Lawful Revolution). [strong]

**Religious / cultural building placement.** Catholic church at village center; Calvinist church in eastern Hungary (Debrecen); synagogues in market towns.
- Axis: center
- Evidence: Hungarian religious-geography historiography. [strong]

**Trade / market placement.** Buda and Pest Danube ports; market squares at county seats; cattle-drive routes to Vienna.
- Axis: river + crossroads
- Evidence: Hungarian cattle-trade historiography. [strong]

**Defensive architecture.** Komarom citadel and Danube fortresses (Buda, Pest); puszta rapid-response cavalry as dispersed screen.
- Wall archetype: FortressRing (+ NomadScreen as hussar-screen logic)
- Wall placement logic: ring_around_core + frontier_line_only
- Evidence: Komarom fortress archaeology. [strong]

**Expansion heading.** Across the Pannonian Basin; outward from Buda to peripheral regions (Transylvania, Croatia).
- outward_rings
- Evidence: Hungarian territorial historiography. [strong]

**Signature placement quirk.** Puszta plain dotted with isolated tanya farms and hussar cavalry screens backed by Danube bastioned fortresses — a plains-and-river Magyar silhouette.

**Open research questions.** None critical.

---

### Indonesians (ANWIndonesians)

**Historical era & geography.** Java War under Prince Diponegoro, 1825–1830. Javanese kraton-city geography; central Java volcanic valleys.

**Starting TC preference.**
- Primary terrain: river (Javanese river-valley)
- Secondary terrain: hill (volcanic slope)
- Evidence: Yogyakarta, Surakarta, Magelang sit on central Java's river-valley plains between volcanoes. [strong]

**House / residential placement.** Kampung cluster of bamboo-and-thatch houses around the kraton palace; rice-terrace hamlets (desa) on slopes.
- Axis: compound_enclosed (kraton) + river_terrace
- Evidence: Javanese kraton archaeology (Yogyakarta, Surakarta). [strong]

**Economic building placement.** Wet-rice terraces (sawah); nutmeg/clove in Maluku; coastal trading ports.
- Axis: river + hill (terrace)
- Evidence: Javanese agricultural geography (Geertz, Agricultural Involution). [strong]

**Military building placement.** Kraton guard at palace; Diponegoro's rural guerrilla columns mobile through countryside.
- Posture: clustered_central (kraton) + mobile_satellite (rebel)
- Evidence: Carey's Power of Prophecy (Diponegoro biography). [strong]

**Religious / cultural building placement.** Alun-alun ceremonial square at kraton front; mosque at alun-alun west side; hill shrines at sacred volcanoes; Borobudur/Prambanan ruins as cultural anchors.
- Axis: center (alun-alun) + hilltop (volcano shrines)
- Evidence: Javanese mancapat-cosmography literature. [strong]

**Trade / market placement.** Pasar market at alun-alun; coastal ports (Batavia, Semarang, Surabaya); Maluku spice-island entrepots.
- Axis: center + coast
- Evidence: Javanese market-geography; VOC trade historiography. [strong]

**Defensive architecture.** Kraton walls around palace complex; Dutch-colonial star-forts (Vredeburg at Yogya, Rotterdam at Makassar) — the civ inherits both.
- Wall archetype: FortressRing
- Wall placement logic: ring_around_core + coast_batteries
- Evidence: Kraton Yogyakarta archaeology; Fort Vredeburg. [strong]

**Expansion heading.** Across Javanese river-valley belt; island-hop across the archipelago.
- along_coast + island_hop
- Evidence: Javanese maritime-expansion historiography. [strong]

**Signature placement quirk.** Kraton compound with alun-alun and sacred banyan tree plus terraced sawah stepping down to a coastal port — a unique Austronesian-Javanese silhouette.

**Open research questions.** Diponegoro-era focuses on central Java; outer-island Indonesians (Bugis, Balinese, Acehnese) have different patterns — probably out of scope.

---

### Mayans (ANWMayans)

**Historical era & geography.** Caste War of Yucatan under Jacinto Canek era (historically earlier Canek 1761 rebellion; Caste War 1847 onward). Yucatan peninsula karst plain, cenote settlement, Chan Santa Cruz rebel capital.

**Starting TC preference.**
- Primary terrain: forest_edge (selva)
- Secondary terrain: desert_oasis (cenote — karst sinkhole)
- Evidence: Every Mayan settlement from Classic-era Tikal to Caste War Chan Santa Cruz sits near a cenote or water-filled karst depression. [strong]

**House / residential placement.** Pole-and-thatch na houses clustered around a cenote or plaza; Caste War rebels built concealed forest hamlets.
- Axis: compound_enclosed (cenote cluster)
- Evidence: Yucatec Maya ethnography; Caste War historiography (Dumond, Machete and the Cross). [strong]

**Economic building placement.** Milpa slash-and-burn maize fields cleared from selva; henequen plantations in 19th c. Yucatan; salt works at coast.
- Axis: forest_edge
- Evidence: Yucatan milpa-system literature; henequen-plantation historiography. [strong]

**Military building placement.** Caste War rebels operated from forest strongholds (Chan Santa Cruz, Tulum); no fixed barracks.
- Posture: mobile_satellite + clustered_central (Chan Santa Cruz)
- Evidence: Caste War historiography. [strong]

**Religious / cultural building placement.** Classic-era pyramid shrines ("Talking Cross" at Chan Santa Cruz revived Mayan cosmology); cenote-side shrines.
- Axis: center + hilltop (pyramid) + riverside (cenote)
- Evidence: Talking Cross cult historiography (Reed, Caste War of Yucatan). [strong]

**Trade / market placement.** Market plazas at Chan Santa Cruz and Tulum; smuggling across British Honduras border for arms.
- Axis: center + follow_trade_route (smuggling)
- Evidence: Caste War arms-trade historiography. [strong]

**Defensive architecture.** Forest palisade (albarradas) around rebel villages; Tulum Classic-era sea wall reused.
- Wall archetype: FrontierPalisades
- Wall placement logic: village_palisades
- Evidence: Caste War fortified-village archaeology. [plausible]

**Expansion heading.** Outward from Chan Santa Cruz across the selva; toward British Honduras for arms supply.
- follow_trade_route + outward_rings
- Evidence: Caste War territorial historiography. [strong]

**Signature placement quirk.** Cenote-centered forest villages with a revived Classic-era pyramid shrine at the capital — a distinctly Mesoamerican indigenous-uprising silhouette.

**Open research questions.** Canek (1761) vs. Caste War (1847 onward) — the roster's leader is Canek but the Chan Santa Cruz signature is later. Blend: cenote/forest placement, fort-village palisade. [plausible] for specific fort-architecture at Canek era.

---

### Mexicans (Revolution) (ANWMexicans)

**Historical era & geography.** Mexican War of Independence under Hidalgo, 1810 onward. Central Mexican altiplano; mine-towns, haciendas, and parish-insurgent geography.

**Starting TC preference.**
- Primary terrain: highland_pasture (altiplano)
- Secondary terrain: hill (mine sierra)
- Evidence: Hidalgo's grito at Dolores; campaign across Guanajuato / Valladolid / Guadalajara. [strong]

**House / residential placement.** Grid town with plaza mayor; rural hacienda with peon quarters; mine-town cluster on sierras.
- Axis: center + pastoral_dispersed + hill (mine-town)
- Evidence: Colonial Mexican urban-rural geography. [strong]

**Economic building placement.** Silver mines and refineries at Guanajuato/Zacatecas; haciendas on plateau; parish granaries (alhóndigas) at mine-town centers.
- Axis: hill (mine) + plain (hacienda)
- Evidence: Brading's Miners and Merchants. [strong]

**Military building placement.** Insurgent musters at parish churches; viceregal royalists defended alhondigas and presidio walls.
- Posture: clustered_central (parish) + mobile_satellite (insurgent column)
- Evidence: Hidalgo campaign historiography (Hamnett, Roots of Insurgency). [strong]

**Religious / cultural building placement.** Baroque parish church as both civic center and insurgent muster point; Guadalupe-shrine as national symbol.
- Axis: center
- Evidence: Hidalgo grito de Dolores historiography. [strong]

**Trade / market placement.** Camino real junctions; plaza mayor markets.
- Axis: crossroads + follow_trade_route
- Evidence: Camino Real historiography. [strong]

**Defensive architecture.** Urban barricades during insurgency; alhondiga granary walls repurposed as fortifications (Alhondiga de Granaditas, Guanajuato).
- Wall archetype: UrbanBarricade (+ FrontierPalisades for presidio)
- Wall placement logic: village_palisades + frontier_line_only
- Evidence: Alhondiga de Granaditas battle historiography. [strong]

**Expansion heading.** Outward from Hidalgo's Dolores/Guanajuato core toward Valladolid, Guadalajara, Mexico City.
- outward_rings + follow_trade_route
- Evidence: Hidalgo campaign map 1810. [strong]

**Signature placement quirk.** Parish church as insurgent muster center with granary-turned-fortress (Alhondiga) plus silver-mine towns on sierra slopes — a clergy-led uprising silhouette.

**Open research questions.** Differentiation from base Mexicans civ — base civ models established republic; Rev civ models insurgent phase.

---

### Revolutionary France (ANWRevFrance)

**Historical era & geography.** French First Republic under Robespierre, Terror era 1793–1794. Paris-centric; levee en masse frontier armies.

**Starting TC preference.**
- Primary terrain: river (Seine, Rhone)
- Secondary terrain: plain
- Evidence: Paris is the Revolution's nucleus; departement grid reorganizes the country. [strong]

**House / residential placement.** Paris sans-culotte quartiers; provincial departement capitals grid-laid; church-converted revolutionary temples at village center.
- Axis: trade_street + center
- Evidence: Revolutionary urban-reorganization historiography. [strong]

**Economic building placement.** Assignat-era nationalized biens (church lands) redistributed; grain requisitions from farms; arms-manufactories at Paris (Ateliers de Paris).
- Axis: river + plain
- Evidence: Revolutionary economic historiography (Aftalion, The French Revolution). [strong]

**Military building placement.** Levee en masse depots in every departement; frontier armies along the Rhine and Alps; Committee of Public Safety at Tuileries.
- Posture: frontier_line + clustered_central (Paris)
- Evidence: Levee en masse historiography. [strong]

**Religious / cultural building placement.** Dechristianized churches converted to Temples of Reason; Pantheon at Paris; cult of Supreme Being altars at civic squares.
- Axis: center
- Evidence: French Revolutionary religious-policy historiography. [strong]

**Trade / market placement.** Maximum-price markets at departement capitals; requisition depots at road junctions.
- Axis: crossroads
- Evidence: Loi du Maximum historiography. [strong]

**Defensive architecture.** Inherited Vauban fortresses at frontier; Paris revolutionary barricades; guillotine-equipped revolutionary committees at every district.
- Wall archetype: UrbanBarricade (+ FortressRing at frontier via Vauban)
- Wall placement logic: village_palisades + frontier_line_only
- Evidence: Paris barricade tradition historiography (Traugott, The Insurgent Barricade). [strong]

**Expansion heading.** Outward to "natural frontiers" — Rhine, Alps, Pyrenees; revolutionary export to sister republics.
- frontier_push + outward_rings
- Evidence: Revolutionary war historiography. [strong]

**Signature placement quirk.** Paris barricade-lined quartiers plus levee en masse camps at every departement capital plus Temples of Reason replacing parish churches — an ideological-republican silhouette.

**Open research questions.** None critical.

---

### Napoleonic France (ANWNapoleonicFrance)

**Historical era & geography.** First French Empire under Napoleon post-1804 coronation. Grand Empire from Madrid to Moscow; forward-based army, Grande Armee doctrine.

**Starting TC preference.**
- Primary terrain: plain (campaign theater)
- Secondary terrain: river (Seine, Rhine, Danube, Vistula)
- Evidence: Napoleon's campaigns traced European river systems; Berezina, Danube, Po, Elbe are all named after their river battlefields. [strong]

**House / residential placement.** Paris Haussmann-precursor reorganization; imperial prefecture grids at each allied capital; conscription-era rural communes.
- Axis: center + trade_street
- Evidence: Napoleonic administrative reform historiography. [strong]

**Economic building placement.** Continental System redirected trade inland; arms-manufactories (Saint-Etienne); imperial domains.
- Axis: river + plain
- Evidence: Continental System historiography (Crouzet). [strong]

**Military building placement.** Grande Armee corps d'armee deployed forward; Boulogne camp (1803–1805); imperial guard at Paris; forward-base escalation into sister kingdoms.
- Posture: forward_perimeter + mobile_satellite
- Evidence: Napoleonic operational historiography (Esposito-Elting, Atlas of Napoleonic Wars). [strong]

**Religious / cultural building placement.** Concordat-restored Catholic churches; imperial monuments (Arc de Triomphe, Vendome Column); Napoleon's wedding at Notre-Dame.
- Axis: center + hilltop (monument)
- Evidence: Napoleonic monumental-art historiography. [strong]

**Trade / market placement.** Continental System ports (restricted); inland riverine trade hubs; Paris Halles.
- Axis: center + river
- Evidence: Continental System historiography. [strong]

**Defensive architecture.** Vauban inheritance at frontier; Boulogne coastal camp; forward star-forts at new imperial capitals.
- Wall archetype: FortressRing
- Wall placement logic: frontier_line_only + forward (forward_perimeter on campaign)
- Evidence: Napoleonic fortress-program historiography. [strong]

**Expansion heading.** Forward-base push across Europe — Italy, Germany, Poland, Spain, Russia.
- frontier_push
- Evidence: Napoleonic campaign atlas. [strong]

**Signature placement quirk.** Forward campaign camps at European rivers with imperial Arc/Column at Paris core — a mobile, expansionist, forward-based signature distinct from the Bourbon base civ's static Vauban defensive doctrine.

**Open research questions.** Expansion-direction is map-dependent; on a land-locked map lean into frontier_push, on a water map lean toward Boulogne coastal camp.

---

### Peruvians (ANWPeruvians)

**Historical era & geography.** Peru-Bolivian Confederation under Santa Cruz, 1836–1839. Andean altiplano; Lima coast; Cusco-La Paz spine.

**Starting TC preference.**
- Primary terrain: hill (altiplano)
- Secondary terrain: coast (Lima / Callao)
- Evidence: Lima on coast; Arequipa, Cusco, La Paz, Potosi on altiplano — Peruvian-Bolivian geography is dual coast-highland. [strong]

**House / residential placement.** Spanish grid towns with plaza de armas; Andean ayllu villages on terraced slopes.
- Axis: center + hill
- Evidence: Spanish-colonial and Andean settlement historiography. [strong]

**Economic building placement.** Potosi silver mines (declining but still important); guano islands on coast; haciendas in coastal valleys.
- Axis: hill (mine) + coast
- Evidence: Peruvian economic historiography (Klaren, Peru: Society and Nationhood). [strong]

**Military building placement.** Fortified Andean passes; Callao harbor fortress; mobile cavalry on altiplano.
- Posture: frontier_line (pass) + coast (Callao) + mobile_satellite
- Evidence: Santa Cruz campaign historiography. [strong]

**Religious / cultural building placement.** Cathedral at plaza de armas; Andean syncretic shrines on sacred peaks (apus); Cusco churches on Inca foundations.
- Axis: center + hilltop
- Evidence: Peruvian religious-geography historiography. [strong]

**Trade / market placement.** Callao/Lima as Pacific trade port; altiplano fairs at Potosi, La Paz.
- Axis: coast + crossroads
- Evidence: Peruvian trade historiography. [strong]

**Defensive architecture.** Real Felipe fortress at Callao; colonial-inherited altiplano fortifications; mountain-pass chokepoint defenses.
- Wall archetype: CoastalBatteries (Callao) + ChokepointSegments (passes)
- Wall placement logic: coast_batteries + chokepoint_seals
- Evidence: Real Felipe archaeology; Andean pass-fortification historiography. [strong]

**Expansion heading.** Along the Andean spine; inward from coast to altiplano; southward into Bolivia (confederation itself).
- outward_rings + frontier_push
- Evidence: Peru-Bolivian Confederation historiography. [strong]

**Signature placement quirk.** Dual-zone Peruvian silhouette — Lima-Callao coastal star-fort plus Potosi silver-mine altiplano plus Cusco stone-Inca-foundation town — connected by mountain road.

**Open research questions.** Confederation was short-lived (1836–1839); placement still usefully captures Santa Cruz-era combined geography.

---

### Rio Grande (ANWRioGrande)

**Historical era & geography.** Republic of the Rio Grande, 1840, under Antonio Canales. Border region between Texas and northern Mexico; Laredo-based.

**Starting TC preference.**
- Primary terrain: river (Rio Grande)
- Secondary terrain: plain (Tamaulipas / south Texas brush country)
- Evidence: Rio Grande valley towns (Laredo, Mier, Camargo, Matamoros) are all riverine; hinterland is dry brush plain. [strong]

**House / residential placement.** Riverine adobe rancho; Spanish grid towns along the river; isolated cattle rancherias in brush country.
- Axis: river_terrace + pastoral_dispersed
- Evidence: Nuevo Santander colonial geography. [strong]

**Economic building placement.** Cattle ranchos on both banks; salt flats (El Sal del Rey); riverine trade with gulf ports.
- Axis: river + plain
- Evidence: South Texas / Tamaulipas cattle-economy historiography. [strong]

**Military building placement.** Federalist mobile cavalry raids from saddled-up rancho strongholds; no fixed fortifications beyond presidio inheritance.
- Posture: mobile_satellite + frontier_line
- Evidence: Rio Grande Republic historiography (Nance, After San Jacinto). [strong]

**Religious / cultural building placement.** Adobe parish chapel at each rancho; small-town church on plaza.
- Axis: center + dispersed
- Evidence: Nuevo Santander parish geography. [plausible]

**Trade / market placement.** Matamoros as Gulf port for gun-running; Laredo as river-crossing market.
- Axis: coast (Matamoros) + river (Laredo)
- Evidence: Texas Revolution / Rio Grande trade historiography. [strong]

**Defensive architecture.** Adobe-walled presidios; rancho palisades; no major star-forts.
- Wall archetype: FrontierPalisades
- Wall placement logic: frontier_line_only + village_palisades
- Evidence: South Texas / northern-Mexico frontier archaeology. [plausible]

**Expansion heading.** Along the Rio Grande corridor from Laredo to the Gulf; outward into brush-country ranchos.
- along_coast (river) + outward_rings
- Evidence: Rio Grande Republic territorial claim historiography. [strong]

**Signature placement quirk.** Riverine-rancho string with cavalry-raid mobile bases across the brush country — a cross-border cavalry silhouette.

**Open research questions.** Republic of the Rio Grande lasted ~9 months; placement extrapolates from the surrounding Nuevo Santander region. Some fields [plausible] rather than [strong].

---

### Romanians (ANWRomanians)

**Historical era & geography.** United Principalities under Cuza, 1859–1866. Wallachia and Moldavia merged; Carpathian-Danube geography.

**Starting TC preference.**
- Primary terrain: river (Danube)
- Secondary terrain: hill (Carpathian foothills)
- Evidence: Bucharest on Dambovita; Iasi on the Moldavian plateau; Galati on the Danube. [strong]

**House / residential placement.** Carpathian village on forested slopes; Wallachian plain villages along rivers; boyar conaq manor on estates.
- Axis: river_terrace + forest_edge
- Evidence: Romanian rural ethnography. [strong]

**Economic building placement.** Wheat on Wallachian plain; sheep transhumance in Carpathians; Galati/Braila grain-export ports.
- Axis: plain + hill
- Evidence: Romanian economic historiography. [strong]

**Military building placement.** Cuza-era reformed army billeted at new barracks in Bucharest, Iasi; Danube frontier with Ottoman line.
- Posture: frontier_line (Danube)
- Evidence: Cuza military-reform historiography (Hitchins, Rumania 1866–1947). [strong]

**Religious / cultural building placement.** Orthodox painted monasteries in Bucovina (Voronet, Sucevita); urban cathedrals at Bucharest/Iasi.
- Axis: forest_grove (painted monastery) + center
- Evidence: Bucovina painted-monasteries UNESCO documentation. [strong]

**Trade / market placement.** Danube ports (Galati, Braila); central-city markets (Bucharest's Lipscani quarter).
- Axis: river + center
- Evidence: Romanian trade historiography. [strong]

**Defensive architecture.** Danube-line fortifications (inherited Ottoman/Austrian); Carpathian pass-forts; mostly small masonry.
- Wall archetype: FortressRing + ChokepointSegments (passes)
- Wall placement logic: frontier_line_only + chokepoint_seals
- Evidence: Romanian military-geography literature. [plausible]

**Expansion heading.** Along the Danube and Carpathian foothills; toward Dobruja / Transylvania (later).
- along_coast (river) + frontier_push
- Evidence: Romanian unification historiography. [strong]

**Signature placement quirk.** Danube-bastion frontier plus painted-monastery Carpathian forest enclaves plus Wallachian/Moldavian grid capitals — a bi-principality silhouette.

**Open research questions.** None critical.

---

### South Africans (ANWSouthAfricans)

**Historical era & geography.** South African Republic (Transvaal) under Kruger, late 19th c. Boer commando / laager frontier doctrine; Voortrekker heritage.

**Starting TC preference.**
- Primary terrain: plain (highveld)
- Secondary terrain: hill (kopje)
- Evidence: Pretoria, Potchefstroom, Bloemfontein sit on highveld grasslands; kopjes (rocky outcrops) are the signature terrain feature. [strong]

**House / residential placement.** Boer homestead on isolated farmsteads; dorp grid village at church-and-market center.
- Axis: pastoral_dispersed + center
- Evidence: Boer rural-settlement historiography (Ross, Concise History of South Africa). [strong]

**Economic building placement.** Cattle farming on highveld; mining (gold on Witwatersrand, diamonds at Kimberley) in late 19th c.; wagon-based commerce.
- Axis: plain + hill (mine)
- Evidence: South African economic historiography. [strong]

**Military building placement.** Commando-muster at dorp church on call-out; laager (wagon-fort) in the field; kopje-top rifle positions against British.
- Posture: mobile_satellite + frontier_line
- Evidence: Boer War historiography (Pakenham, The Boer War). [strong]

**Religious / cultural building placement.** Dutch Reformed church at dorp center; nagmaal quarterly-communion gathering as social-religious anchor.
- Axis: center
- Evidence: Afrikaner religious-geography historiography. [strong]

**Trade / market placement.** Dorp market square; mining-town markets at Johannesburg / Kimberley.
- Axis: center
- Evidence: Late-19th c. South African urban historiography. [strong]

**Defensive architecture.** Laager circle of ox-wagons as mobile fortification; kopje trenches at Boer War; pre-war forts at Pretoria, Johannesburg (Forts Klapperkop, Schanskop, Wonderboompoort).
- Wall archetype: MobileNoWalls (laager) + FortressRing (Pretoria forts)
- Wall placement logic: no_walls_raiding + ring_around_core
- Evidence: Laager tactic historiography (Battle of Blood River); Pretoria fort archaeology. [strong]

**Expansion heading.** Voortrekker northward from Cape; outward from Transvaal / Orange Free State cores into surrounding frontier.
- frontier_push + outward_rings
- Evidence: Great Trek historiography. [strong]

**Signature placement quirk.** Ox-wagon laager as field fortification plus dorp-church-market core plus kopje rifle-pit positions — a uniquely mobile-plus-fixed Boer silhouette.

**Open research questions.** Kruger era spans pre-war (1880s) and Boer War (1899–1902) — include both laager and Pretoria-fort architectures.

---

### Texians (ANWTexians)

**Historical era & geography.** Republic of Texas under Sam Houston, 1836–1846. San Jacinto-era frontier republic; Anglo-Tejano coexistence; Comanche frontier.

**Starting TC preference.**
- Primary terrain: river (Brazos, Colorado, Trinity, Rio Grande)
- Secondary terrain: plain (Texas prairie)
- Evidence: Texas towns (San Antonio, Goliad, Nacogdoches, Washington-on-the-Brazos) are riverine. [strong]

**House / residential placement.** Anglo log cabin on isolated homesteads; Tejano ranchos on San Antonio River; dogtrot-plan farmhouses.
- Axis: pastoral_dispersed + river_terrace
- Evidence: Texas frontier-settlement historiography. [strong]

**Economic building placement.** Cattle ranches on south Texas brush country; cotton plantations in east Texas; shipping wharves at Galveston.
- Axis: plain + river + coast
- Evidence: Republic of Texas economic historiography. [strong]

**Military building placement.** Texas Rangers as mobile ranger-company frontier force; fixed forts rare (Alamo, Goliad, Velasco inherited); ranger camps on Comanche frontier.
- Posture: frontier_line + mobile_satellite
- Evidence: Texas Ranger historiography (Webb, The Texas Rangers). [strong]

**Religious / cultural building placement.** Spanish mission churches (Alamo originally San Antonio de Valero, Goliad's Espiritu Santo); Anglo Protestant camp meetings; Tejano parish churches.
- Axis: center + dispersed
- Evidence: Texas religious-geography historiography. [strong]

**Trade / market placement.** Galveston port; riverine trade up Brazos; San Antonio as Tejano market town.
- Axis: coast + river
- Evidence: Republic of Texas trade historiography. [strong]

**Defensive architecture.** Repurposed mission compounds (Alamo); log-blockhouse ranger stations; no large fortresses.
- Wall archetype: FrontierPalisades (+ UrbanBarricade for Alamo-style fortified mission)
- Wall placement logic: frontier_line_only + village_palisades
- Evidence: Alamo siege historiography; ranger-station archaeology. [strong]

**Expansion heading.** Westward onto Comanche frontier; along Gulf coast toward Louisiana; southward to Rio Grande.
- frontier_push + along_coast
- Evidence: Republic of Texas claim-boundary historiography. [strong]

**Signature placement quirk.** Fortified mission-compound (Alamo-style) plus dispersed log-cabin homesteads plus mounted-ranger camps on the Comanche frontier — a distinctly Texian frontier-fortress silhouette.

**Open research questions.** None critical.

---

### Yucatan (ANWYucatan)

**Historical era & geography.** Yucatan socialist period under Carrillo Puerto, 1920s (but civ conceptually covers the long Caste-War-to-early-20th-c. Yucatan). Karst peninsula; henequen plantation economy; Maya majority.

**Starting TC preference.**
- Primary terrain: forest_edge (selva)
- Secondary terrain: desert_oasis (cenote)
- Evidence: Merida, Valladolid, Campeche — Yucatan settlements cluster at cenote-rich karst zones. [strong]

**House / residential placement.** Na thatch-house clusters in Maya villages; henequen hacienda big-house with peon quarters; Merida colonial townhouses.
- Axis: compound_enclosed + pastoral_dispersed
- Evidence: Yucatan ethno-archaeology; henequen-hacienda historiography. [strong]

**Economic building placement.** Henequen plantations on karst plain; corn milpas on cleared selva; salt works on north coast; decorticator mills at hacienda centers.
- Axis: plain + forest_edge + coast
- Evidence: Yucatan henequen-boom historiography (Wells, Yucatan's Gilded Age). [strong]

**Military building placement.** Campeche coastal fortifications (colonial-inherited); mobile Maya defensive forces from Caste War era.
- Posture: coast + mobile_satellite
- Evidence: Campeche UNESCO documentation; Caste War historiography. [strong]

**Religious / cultural building placement.** Merida cathedral (earliest built on the American mainland, 1598); Caste-War Talking Cross revival; cenote shrines.
- Axis: center + riverside (cenote)
- Evidence: Merida cathedral historiography; Talking Cross cult. [strong]

**Trade / market placement.** Merida market plaza; Sisal/Progreso ports; Campeche port.
- Axis: center + coast
- Evidence: Yucatan economic-geography historiography. [strong]

**Defensive architecture.** Campeche's bastioned ring-wall (one of the few walled cities in colonial Americas); hacienda-compound walls; Caste War village palisades.
- Wall archetype: FortressRing (Campeche) + CoastalBatteries + FrontierPalisades (inland rebel)
- Wall placement logic: ring_around_core + coast_batteries + village_palisades
- Evidence: Campeche walls UNESCO documentation. [strong]

**Expansion heading.** Outward from Merida across the peninsula; toward Caribbean coast (Chetumal); toward Campeche gulf.
- outward_rings + along_coast
- Evidence: Yucatan colonial-to-republican expansion historiography. [strong]

**Signature placement quirk.** Walled port-city Campeche plus cenote-clustered henequen haciendas plus Caste-War rebel villages in the selva — a tri-pattern peninsula silhouette.

**Open research questions.** Carrillo Puerto is 1920s socialist — the civ's long arc (Caste War, henequen boom, socialist reform) suggests blending patterns rather than locking to one decade.

---

# ARCHETYPE-CODE COMPATIBILITY MAPPING

For the visualization modal, collapse the expanded archetype names used above into the six constants actually in `leaderCommon.xs`:

| Expanded name | Code constant |
|---|---|
| CoastalBatteries | `cLLWallStrategyCoastalBatteries` |
| FortressRing | `cLLWallStrategyFortressRing` |
| FrontierPalisades | `cLLWallStrategyFrontierPalisades` |
| MobileNoWalls | `cLLWallStrategyMobileNoWalls` |
| UrbanBarricade | `cLLWallStrategyUrbanBarricade` |
| ChokepointSegments | `cLLWallStrategyChokepointSegments` |
| NomadScreen | `cLLWallStrategyMobileNoWalls` (behaviorally closest) |
| StarFort | `cLLWallStrategyFortressRing` |
| ChainTowers | `cLLWallStrategyCoastalBatteries` (harbor chain-tower variant) |
| None | `cLLWallStrategyMobileNoWalls` |

Where a nation entry lists multiple archetypes, the first is the dominant doctrine; later ones are overlay hints for the visualization (e.g. "coastal battery accent over fortress ring core").

---

# SUMMARY

48 nations documented (22 base + 26 revolution). Every entry is grounded in real historical evidence with confidence grading. Most are [strong]-confidence; a handful of Revolution civs (Baja Californians, Mayans under Canek, Rio Grande) rely on [plausible] inference because the named leader's specific defensive architecture or military placement is under-documented, and context from the surrounding region fills those gaps.

Flagged for future research depth:
- Baja Californians — military specifics under Alvarado.
- Mayans — reconciling Canek (1761) vs. Caste War (1847) temporal span.
- Rio Grande — placement extrapolated from Nuevo Santander.
- Central Americans — Federal Republic specifics vs. colonial inheritance.

These are all noted in their respective "Open research questions" fields.
