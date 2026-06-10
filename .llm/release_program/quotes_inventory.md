# ANW Chat Quotes Inventory

## Where Quotes Live

Three separate storage layers, all of which must be updated for a full quote rewrite:

### 1. `game/ai/core/aiLeaderQuotes.xs` — AI insult/compliment chat lines
- **Functions**: `anwGetLeaderInsult()` and `anwGetLeaderCompliment()` (lines ~252–1019)
- **Data shape**: per-civ `if/else if` branches, each returning 2 strings (quoteIndex 0 or 1)
- **Shared tactical lines** (lines 127–145): 4 generic strings used across all civs:
  - retreat: `"Fall back and close ranks. Our leader will not be lost today."`
  - rout: `"Your broken soldiers are in full retreat now."`
  - bulk_assault: `"Break their main line first. The army is the real prize."`
  - decapitation: `"Ignore the rabble. Bring down their leader."`
- **Coverage**: 33 civs in insult function, 33 in compliment function
- **Missing from XS**: ANWCalifornians (partial — insult only?), ANWCentralAmericans, ANWYucatan, ANWBajaCalifornians, ANWRioGrande have entries in aiLeaderQuotes.xs

### 2. `game/ai/chatsetsmods.xml` — In-game AI chat trigger lines
- **Data shape**: `<Chatset name="anw_<token>">` blocks, each with 6 `<Tag>` triggers:
  `ToAllyIntro`, `ToEnemyIntro`, `ToAllyWhenIWallIn`, `ToEnemyWhenHeWallsIn`,
  `ToAllyILoseExplorerEnemy`, `ToAllyBattleOverIWonAsExpected`
- Each tag has `<String>` text, a `<Sound>` file reference, and a `<StringID>`
- **Count**: 48 chatsets total (including `suleiman` for Ottomans and legacy `anw_americansrev`/`anw_mexicansrev`)
- The sound file used is the key indicator of which base-game leader's voice acts the lines

### 3. `tools/migration/anw_blurb_data.py` (BLURBS dict) + `blurb_database.json`
- **Purpose**: tooltip/lobby blurbs shown in the civilization select screen
- `anw_blurb_data.py` has `leader_history` and `nation_history` fields per civ token
- `blurb_database.json` has `history`, `playstyle`, `units`, `bonus`, `ageup` per display-name key
- These are separate from chat quotes but share the "historical authenticity" concern
- `data/anw_civ_blurbs.json` has `civ_bonus`, `unique_units`, `unique_buildings`, `playstyle`, `age_up` — no quote text

### Leader → Sound file mapping (base-game voice assets used)
| Sound prefix | Leader |
|---|---|
| `FRED` | Frederick the Great (Germans, Hungarians, Romanians) |
| `GUST` | Gustavus Adolphus (Swedes) |
| `HIAW` | Hiawatha (Haudenosaunee) |
| `IVAN` | Ivan the Terrible (Russians, Finnish) |
| `ISAB` | Isabella (Spanish, Argentines, Chileans, Peruvians, Columbians, Peruvians, CentralAmericans, BajaCalifornians, Canadians... see XML) |
| `NAPO` | Napoleon (NapoleonicFrance, RevFrance, Haitians, French, anw_revfrance) |
| `KANG` | Kangxi (Chinese) |
| `WILL` | William/Maurice of Nassau (Dutch, Indonesians, SouthAfricans) |
| `HENR` | Henry the Navigator (Portuguese, Brazil) |
| `HIDA` | Hidalgo (Mexicans, Californians, BajaCalifornians override, CentralAmericans, RioGrande, Yucatan, MexicansRev) |
| `SULE` | Suleiman (Ottomans, Barbary, Egyptians) |
| `GARI` | Garibaldi (Italians) |
| `JEAN` | Jean de Valette (Maltese) |
| `CRAZ` | Crazy Horse (Lakota) |
| `CUAU` | Cuauhtémoc (Aztecs, Mayans) |
| `WASH` | Washington (USA, Texians, AmericansRev) |
| `TOKU` | Tokugawa (Japanese) |
| `AMIN` | (Hausa — likely Usman dan Fodio or a DE asset) |
| `TEWO` | (Ethiopians — likely Tewodros II / Menelik asset) |
| `ELIZ` | Elizabeth (British, Canadians) |
| `AKBA` | (Indians — Akbar/Shivaji asset) |
| `HUAY` | (Inca — Huayna Capac / Pachacuti asset) |

---

## 44 Civ Token → Leader Table

(All tokens verified from `data/civmods.xml` `<name>` entries and `<homecitypreviewwpf>` portrait paths. Quote samples are from `aiLeaderQuotes.xs` insult quoteIndex=0 / `chatsetsmods.xml` ToEnemyIntro.)

| # | Civ Token (civmods.xml) | Leader (portrait/civmods) | Current insult quote (q0) | Current chatset ToEnemyIntro | Historical & leader-matched? | Native-language text? | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | ANWNapoleonicFrance | Napoleon Bonaparte | "Europe did not fear me for such maneuvers." | "Kings have learned my name through their retreats." | Y — Napoleon-voice, Napoleon-themed | Partial (French phrases in chatset: "Grande Armée") | Keep |
| 2 | ANWRevFrance | Robespierre (portrait: french_robespierre) | "The Republic has no patience for such timidity." | "The tyrant's head fell in Paris. Yours is not so different." | Partial — Republican rhetoric fits but no Robespierre attribution | French phrases present ("Liberté, Égalité...") | Refine (add Robespierre-attributed quotes) |
| 3 | ANWCanadians | Isaac Brock (portrait: canadians_brock) | "This frontier has broken louder men than you." | "The Americans came to Detroit and left with bowed heads." | Partial — Brock-era themes; chatset refs Detroit/Queenston Heights | No native-language | Refine (Brock-attributed lines) |
| 4 | ANWBrazil | Pedro II (portrait: brazil_pedro_i — labelled Pedro I) | "Empires are not born from such hesitation." | "Brazil is a new empire. You will discover its strength." | Partial — imperial Brazil voice; "Independência ou morte" in chatset (Pedro I cry) | Partial (Portuguese: "Independência ou morte") | Refine (clarify Pedro I vs II; add attributed quote) |
| 5 | ANWArgentines | José de San Martín | "The Andes would laugh at such a march." | "I have crossed the Andes. A single battlefield will not stop me." | Y — Andean crossing explicitly referenced; San Martín themes | No (chatset English only) | Refine (add native-language; source actual San Martín quote) |
| 6 | ANWChileans | Bernardo O'Higgins | "A wavering hand cannot found a republic." | "La cordillera nos separa. Pero no por mucho tiempo." | Y — Chilean republic founding themes; Maipú ref | Y (Spanish lines present) | Keep |
| 7 | ANWPeruvians | Andrés de Santa Cruz | "You campaign without altitude or vision." | "Peru and Bolivia are one. You do not know what you have awakened." | Partial — Confederation themes correct; no Santa Cruz attribution | Partial (Spanish phrases) | Refine (add Santa Cruz-attributed quote) |
| 8 | ANWColumbians | Simón Bolívar | "You dream of empire and cannot hold a ridge." | "I have liberated five nations. Yours will be the sixth." | Y — El Libertador voice, Carabobo/Gran Colombia refs | Y (Spanish lines) | Keep |
| 9 | ANWHaitians | Toussaint L'Ouverture | "No army stands long upon the whip." | "I overthrew an empire with enslaved hands." | Y — slave revolution themes, Crête-à-Pierrot ref | No (French Creole absent) | Refine (add Haitian Creole or French-original Toussaint quote) |
| 10 | ANWIndonesians | Prince Diponegoro | "You occupy land you do not understand." | "The VOC has been here before. They do not stay." | Y — Java War themes, VOC ref | Y (Javanese: "Seorang prajurit yang jatuh...") | Keep |
| 11 | ANWSouthAfricans | Paul Kruger | "You spend strength like a man with borrowed land." | "The Boer does not yield. Majuba reminded the Empire." | Y — Boer/Transvaal, Majuba refs; Kruger tone | Y (Afrikaans: "'n Boer gesneuwel. God sien hom.") | Keep |
| 12 | ANWFinnish | Carl Gustaf Mannerheim | "You waste terrain as if it were free." | "The forest, the snow, and the sisu. You will meet all three." | Partial — Finnish themes correct; Mannerheim Line ref; no Mannerheim attribution | Y (Finnish: "Suomi seisoo.") | Refine (add Mannerheim-attributed quote) |
| 13 | ANWHungarians | Lajos Kossuth | "A nation is not led by hesitation." | "Habsburg-ally or worse? Magyarország does not yield again." | Partial — 1848 themes; no Kossuth attribution | Y (Hungarian: "Egy hős elesett.", "Magyarország") | Refine (add Kossuth-attributed quote) |
| 14 | ANWRomanians | Alexandru Ioan Cuza | "You confuse disorder with liberty." | "Unirea Principatelor este făcută. You come too late to divide us." | Partial — Unification themes match Cuza; no direct attribution | Y (Romanian lines present) | Refine (add Cuza-attributed quote) |
| 15 | ANWBarbary | Hayreddin Barbarossa | "You sail and march with equal confusion." | "Algiers has no fear of empires. Ask Charles V." | Y — Algiers/corsair themes, Charles V ref matches Barbarossa | No native-language (Ottoman Turkish/Arabic absent) | Refine (add Ottoman Turkish original or Arabic phrase) |
| 16 | ANWEgyptians | Muhammad Ali Pasha | "You inherit strength and waste it." | "Mamluks learned fear at my table. You are not a Mamluk." | Y — Citadel massacre ref, Nizami Cedid themes, Muhammad Ali voice | No native-language (Arabic/Ottoman absent) | Refine (add Arabic original phrase) |
| 17 | ANWMayans | "Canek" spirit / Cruzob leader (portrait: mayans_canek) | "Old ground does not honor cowards." | "Tu emperador es como el sol — cae cada noche." | Y — Caste War/Chan Santa Cruz themes; Cruzob ref | Y (Spanish/Maya lines present) | Keep |
| 18 | ANWTexians | Sam Houston | "A loud charge is still a bad plan." | "San Jacinto was eighteen minutes. I have time to spare." | Y — San Jacinto explicit, Alamo ref, Houston voice | No native-language | Keep |
| 19 | ANWAztecs (XPAztec) | Montezuma II (portrait: aztecs_montezuma) | "The omens condemn such disorder." | "The smoking mirror shows me your end. Come, meet it." | Y — Aztec cosmology, flower war refs | No (Nahuatl absent) | Refine (add Nahuatl phrase) |
| 20 | ANWBritish (British base) | Wellington (portrait: cpai_avatar_british — uses ELIZ sound, but chatset says Vitoria = Wellington) | "That advance would die nameless on a ridge in Spain." | "I have seen your kind at Vitoria. Discipline will decide this." | Partial — chatset is clearly Wellington (Vitoria, Guards, Hussars); blurb_data says "Elizabeth I"; mismatched | No | Replace (reconcile leader: Wellington or Elizabeth? chatset/XS lines are Wellington; portrait unspecified) |
| 21 | ANWChinese (Chinese base) | Kangxi Emperor | "You bring disorder to a field that demands harmony." | "The Qing do not address barbarians twice. Kneel, or depart." | Y — Eight Banners, Qing Dynasty refs | No (Mandarin absent) | Refine (add Mandarin original phrase) |
| 22 | ANWDutch (Dutch base) | Maurice of Nassau | "Your volley is late and your drill worse." | "You have not studied the line. You will learn." | Y — Dutch drill/VOC themes, Maurice voice | No native-language | Refine (add Dutch phrase) |
| 23 | ANWEthiopians (DEEthiopians) | Menelik II (portrait: ethiopians_menelik) | "You climb these heights without judgment." | "Adwa is not yet finished. Come and see." | Y — Adwa explicit, highland themes | No (Amharic absent) | Refine (add Amharic phrase) |
| 24 | ANWFrench (French base) | Bourbon/Louis XVIII per blurb_data; but NAPO sound + Napoleon quotes used | "You maneuver like a clerk and expect empire to follow." | "Impossible is a word only found in the dictionary of fools." | N — chatset/XS lines are Napoleon ("Soldiers! Forty centuries look down upon us", "Impossible is a word…") but blurb leader is Louis XVIII; WRONG LEADER | Y (French: Napoleonic phrases) | Replace (chatset uses Napoleon quotes but civ token is Bourbon France — needs reconciliation or leader reassignment) |
| 25 | ANWGermans (Germans base) | Frederick the Great | "Your line offends both reason and powder." | "You are neither Austrian nor French. I shall have to improvise." | Y — Leuthen/Silesia/Oblique Order refs | No native-language (German absent) | Refine (add German phrase from Frederick) |
| 26 | ANWHaudenosaunee (XPIroquois) | Hiawatha (portrait: haudenosaunee_hiawatha) | "You break ranks as easily as broken councils." | "You have not learned the Great Law. We will teach you." | Y — Great Law, six fires, confederacy themes | No (Mohawk absent) | Refine (add Mohawk/Onondaga phrase) |
| 27 | ANWHausa (DEHausa) | Usman dan Fodio (portrait: hausa_usman_dan_fodio) | "You advance without justice or discipline." | "The Caliphate of Sokoto calls all unbelievers to account." | Y — Sokoto/Hausa jihad themes, Kano's walls ref | No (Fulfulde/Arabic absent) | Refine (add Arabic or Fulfulde phrase from dan Fodio writings) |
| 28 | ANWInca (DEInca) | Pachacuti (portrait: inca_pachacuti) | "You cannot build victory on such loose stones." | "You are far from your sea. The mountain will teach you." | Partial — Sacsayhuaman ref, Inca themes; no Pachacuti attribution; chatset uses "Pachacuti" XS file but quotes are generic | No (Quechua absent) | Refine (add Quechua phrase; attribute to Pachacuti) |
| 29 | ANWIndians (Indians base) | Shivaji Maharaj (portrait: indians_shivaji) | "You guard no flank and deserve none." | "I am the jackal of the Sahyadri. You will see only my shadow." | Y — Ganimi Kava, Maratha, Sahyadri ref; Shivaji voice | Partial (Sanskrit/Marathi: "Hindavi Swarajya!") | Keep |
| 30 | ANWItalians (DEItalians) | Giuseppe Garibaldi | "You march like ceremony, not revolution." | "I have fought kings and popes. You are no worse than either." | Y — Mille/Redshirts, Risorgimento refs; Garibaldi voice | Partial (Italian: "O Roma, o morte!") | Keep |
| 31 | ANWJapanese (Japanese base) | Tokugawa Ieyasu | "The impatient commander defeats himself first." | "Sekigahara decided the matter. You come late, and from the wrong flank." | Y — Sekigahara, Edo Castle, Sakoku refs; Tokugawa voice | Partial (Japanese patience metaphor via "patient river") | Refine (add Japanese original phrase from Tokugawa) |
| 32 | ANWLakota (XPSioux) | Crazy Horse (portrait: lakota_crazy_horse) | "You ride as if the plains forgive weakness." | "You have come to the Paha Sapa. You will not leave." | Y — Paha Sapa, Greasy Grass (Little Bighorn), "Hoka hey" refs | Partial (Lakota: "Hoka hey") | Keep |
| 33 | ANWMaltese (DEMaltese) | Jean de Valette | "You break on stone and call it valor." | "The Turk came to Malta and left his bones. You shall not do better." | Y — Great Siege, Birgu/Senglea/St.Elmo; Valette voice | Partial (Latin: "Deo gratias") | Keep |
| 34 | ANWMexicans (DEMexicans) | Miguel Hidalgo (portrait: mexicans_hidalgo) | "A people do not stay quiet forever." | "The Cry of Dolores! Spain will hear us from the pulpit itself." | Y — Grito de Dolores, Alhóndiga refs; Hidalgo voice | Partial (Spanish phrases) | Keep |
| 35 | ANWCalifornians | Mariano Guadalupe Vallejo (portrait: californians_vallejo) | "You threaten the province more than you command it." | "Las Californias has its own governors. You are not one." | Partial — Californio themes; Sonoma/Monterey refs; no Vallejo attribution | Y (Spanish: "Desde Sonoma hasta Monterey...") | Refine (add Vallejo-attributed historical quote) |
| 36 | ANWCentralAmericans | Francisco Morazán (portrait: central_americans_morazan) | "A divided command defeats itself." | "The conservatives have learned. You will learn too." | Partial — Federation/liberal themes; no Morazán attribution | Partial (Spanish: "Se esconde como el godo colonial") | Refine (add Morazán-attributed quote) |
| 37 | ANWBajaCalifornians | Juan Bautista Alvarado (portrait: baja_californians_alvarado) | "The frontier swallows slower men than you." | "The Californias do not surrender without the word of their governors." | Partial — Loreto/Baja themes; no Alvarado attribution | No native-language | Refine (add Alvarado-attributed quote) |
| 38 | ANWRioGrande | Antonio Canales Rosillo (portrait: rio_grande_canales_rosillo) | "You were too slow for this border." | "Mexico and the gringos both wanted us. Neither had us." | Partial — Republic of Rio Grande themes, Laredo/Nueces refs; no Canales attribution | Partial (Spanish phrases) | Refine (add Canales-attributed quote; source-needed for specific lines) |
| 39 | ANWOttomans (Ottomans base) | Suleiman the Magnificent (portrait: ottomans_suleiman) | "You bring neither law nor strength." | "I am Suleiman, Sultan of Sultans. Kneel, or I shall teach you." | Y — Belgrade/Rhodes/Mohács refs; Suleiman explicitly named | No (Ottoman Turkish/Arabic absent) | Refine (add Ottoman Turkish phrase from Suleiman) |
| 40 | ANWPortuguese (Portuguese base) | Henry the Navigator (portrait: portuguese_henry) | "You mistake horizon for mastery." | "I have charted stranger shores than you. Your coast, too, will be known." | Y — Sagres, caravel, horizon themes; Henry voice | No native-language (Portuguese absent) | Refine (add Portuguese phrase attributed to Henry) |
| 41 | ANWRussians (Russians base) | Ivan IV the Terrible (portrait: russians_ivan) | "You have breadth but no design." | "The Empire of the Rus does not negotiate with disorder." | Partial — empire/frontier themes; chatset says "even Frederick dared meet me on the field" (anachronism: Ivan died 1584, Frederick born 1712) | No native-language | Replace (fix anachronism in chatset; add Russian phrase from Ivan) |
| 42 | ANWSpanish (Spanish base) | Isabella I (portrait: spanish_isabella) | "You squander zeal as well as steel." | "Granada fell. Then Iberia. Then the New World. Do not be the next line." | Y — Reconquista, Granada, New World refs; Isabella voice | No native-language (Spanish absent from XS quotes) | Refine (add Spanish original phrase attributed to Isabella) |
| 43 | ANWSwedes (DESwedish) | Gustavus Adolphus (portrait: swedes_gustavus_adolphus) | "You are too slow for modern war." | "The Lion of the North is abroad. Kneel or face the Hakkapeliitta." | Y — Breitenfeld, Lion of the North, Hakkapeliitta; Gustavus voice | Y (Swedish: "För Gud och fäderneslandet.") | Keep |
| 44 | ANWUSA (DEAmericans) | George Washington (portrait: americans_washington) | "Liberty is not defended by blundering in plain sight." | "We fight for independence. You will find that an unshakable thing." | Y — Valley Forge, Yorktown, Continental Army; Washington voice | No native-language | Refine (add Washington-attributed historical quote) |

---

## Summary

| Verdict | Count | Notes |
|---|---|---|
| **Keep** | 12 | Strong leader match, thematic consistency, no major issues |
| **Refine** | 27 | Correct leader/period but missing: native-language original, direct attribution, or minor anachronism |
| **Replace** | 3 | Significant mismatches: ANWFrench (Bourbon civ uses Napoleon quotes), ANWBritish (Elizabeth blurb vs Wellington chatset), ANWRussians (Ivan/Frederick anachronism) |
| **Source-needed** | 1 | ANWRioGrande (Canales Rosillo is historically obscure; specific attributed quotes need sourcing) |

**Total: 44 nations.** 12 already in good shape; 28 need work (27 refine + 1 source-needed); 3 need replacement.

---

## Key Data Files for Implementation

- XS insult/compliment branches: `/game/ai/core/aiLeaderQuotes.xs` lines 252–1019
- Chatset XML: `/game/ai/chatsetsmods.xml` (48 `<Chatset>` blocks)
- Blurb historical text: `/tools/migration/anw_blurb_data.py` (`BLURBS` dict, `leader_history`/`nation_history` fields)
- Blurb database: `/blurb_database.json` (`history` field per display-name key)
- Extraction tool: `/tools/validation/extract_civ_quotes.py` (parses both XS and XML, public API documented)
- Generation tool: `/tools/chatquotes/generate_chat_quotes.py` (produces chatset XML)
