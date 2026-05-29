"""Per-civ thematic config used by build_themed_decks.py.

For each civ we keep:
  keywords      - substrings (case-insensitive, matched against the card NAME)
                  that earn a big scoring bonus. Drives "give Napoleon his
                  Napoleonic cards" behaviour.
  must_include  - card names that MUST land in the 25-card deck (use sparingly,
                  reserved for absolute icons of the civ/leader). Each entry
                  is verified against the civ's pool at run time — missing
                  entries are skipped silently.
  must_exclude  - card names that MUST NOT land in the deck (overrides scoring).
  buildstyle    - the archetype name for this civ (matches prose_buildstyle.py
                  AND the in-HTML Buildstyle label exactly). Maps to extra
                  keywords via BUILDSTYLE_KEYWORDS so the deck reinforces the
                  build doctrine.

Per-civ entries are authored against the leader's actual history — Wellington
gets Rangers + Rule Britannia + line-infantry combat cards; Garibaldi gets the
Risorgimento volunteer columns; Bolívar gets Llanero liberation cards;
Pachacuti gets Andean fortifications + Tawantinsuyu mass infantry; etc.
"""
from __future__ import annotations

# Buildstyle archetype → extra keyword hints that score cards reinforcing how
# the AI is wired to build/fight under this archetype.
BUILDSTYLE_KEYWORDS: dict[str, list[str]] = {
    "Compact Fortified Core":     ["fort", "wall", "tower", "outpost", "garrison", "fortif", "bastion", "castle"],
    "Forward Operational Line":   ["fort", "outpost", "barrack", "stable", "frontier", "assault", "rally"],
    "Mobile Frontier Scatter":    ["townceneter", "trading", "scout", "settler", "wagon", "explorer", "mobile"],
    "Distributed Economic Network": ["mill", "plantation", "market", "bank", "factory", "trade", "exotic", "refrig", "hardwood"],
    "Civic Militia Center":       ["militia", "minute", "outpost", "townceneter", "townwatch", "patriote", "levy"],
    "Shrine or Trade Node Spread": ["shrine", "trading", "sacred", "wonder", "monastery", "consulate", "temple"],
    "Jungle Guerrilla Network":   ["guerr", "warhut", "warchief", "ambush", "forest", "jungle", "raid", "blowgun", "tomahawk"],
    "Naval Mercantile Compound":  ["dock", "fish", "caravel", "frigate", "galleon", "ironclad", "monitor", "fleet", "merchant", "battleship"],
    "Highland Citadel":           ["fort", "wall", "citadel", "stone", "highland", "bastion", "fortif", "extensive"],
    "Siege Train Concentration":  ["cannon", "mortar", "falconet", "culverin", "artillery", "foundry", "siege", "battery", "bombard", "abus"],
    "Steppe Cavalry Wedge":       ["hussar", "dragoon", "cuirass", "cossack", "cavalry", "rider", "lancer", "horse", "stable", "uhlan"],
    "Cossack Voisko":             ["cossack", "ataman", "raider", "horseman", "townceneter", "blockhouse", "kalmuck", "bashkir"],
    "Republican Levee":           ["musketeer", "skirmisher", "regular", "infantry", "general", "barrack", "officer", "minute", "conscript"],
    "Andean Terrace Fortress":    ["fort", "wall", "kallanka", "tambo", "stone", "andean", "highland", "huam", "huayna"],
}


# ── Standard 22 civs ──────────────────────────────────────────────────────
# Buildstyles below match the in-HTML Buildstyle label exactly.

STANDARD: dict[str, dict] = {
    # British — Duke of Wellington — Iron Duke line-and-logistics
    "homecitybritish": {
        "keywords": ["british", "manor", "longbow", "musketeer", "redcoat", "rogers",
                     "ranger", "highlander", "rule", "wellington", "tea", "anglican",
                     "naval", "frigate", "galleon", "loyalist", "marion"],
        "must_include": ["DEHCRuleBritannia", "DEHCRangers", "DEHCShipRangers2", "HCExplorerBritish", "HCMusketeerGrenadierCombatBritish", "DEHCSiegeArchery", "DEHCWhaleOilTeam", "DEHCGreenwichTime", "DEHCFedMarionsDiversions"],
        "must_exclude": [],
        "buildstyle": "Naval Mercantile Compound",
    },

    # French — Louis XVIII — Bourbon Restoration court army
    # (Standard French = post-Restoration. Napoleonic / Republican flavour
    # belongs to the revolution civs Napoleon and RevolutionaryFrance.)
    "homecityfrench": {
        "keywords": ["french", "coureur", "voyageur", "cuirass", "skirmisher",
                     "tirail", "bourbon", "royal", "fencing", "salon", "court",
                     "musketeer", "hussar"],
        "must_include": ["DEHCBourbonAllies1", "DEHCFrenchRoyalArmy", "DEHCFencingSchoolFrench", "HCExplorerFrench", "HCRoyalDecreeFrench", "HCCavalryCombatFrench", "HCRangedInfantryDamageFrenchTeam"],
        "must_exclude": [],
        "buildstyle": "Compact Fortified Core",
    },

    # Dutch — Maurice of Nassau — Stadtholder drill-and-bank
    "homecitydutch": {
        "keywords": ["dutch", "ruyter", "fluyt", "bank", "stadtholder", "settler",
                     "envoy", "halberdier", "fishing", "painting", "merchant",
                     "battleship", "mercenary"],
        "must_include": ["HCXPBankWagon", "HCBetterBanks", "HCInfantryCombatDutch", "HCShipRuyters3", "HCShipHalberdiers3", "HCShipFluyts2", "DEHCMercenaryArmyDutch", "DEHCDutchPaintings", "DEHCDutchBattleshipCard"],
        "must_exclude": [],
        "buildstyle": "Naval Mercantile Compound",
    },

    # Germans — Frederick the Great — Hohenzollern oblique-order shock
    "homecitygerman": {
        "keywords": ["german", "uhlan", "doppelsold", "warwagon", "settler",
                     "landsknecht", "habsburg", "hesse", "needle", "frederick",
                     "prussian", "hohenzollern", "hessian"],
        "must_include": ["HCExplorerGerman", "HCShipUhlans3", "HCShipWarWagons1", "HCShipSettlerWagons1", "HCRoyalDecreeGerman"],
        "must_exclude": [],
        "buildstyle": "Siege Train Concentration",
    },

    # Ottomans — Suleiman the Magnificent — Sublime Porte gunpowder empire
    "homecityottomans": {
        "keywords": ["ottoman", "janissary", "abus", "spahi", "bombard", "topkapi",
                     "imam", "vizier", "harem", "mosque", "sublime", "kanun",
                     "great", "tower", "minaret"],
        "must_include": ["HCShipJanissaries3", "HCShipSpahis3", "HCShipGreatBombards2", "HCExplorerOttoman", "HCRoyalDecreeOttoman"],
        "must_exclude": [],
        "buildstyle": "Siege Train Concentration",
    },

    # Portuguese — Prince Henry the Navigator — Sagres carrack-and-padrão empire
    "homecityportuguese": {
        "keywords": ["portuguese", "cassador", "dragoon", "carrack", "feitoria",
                     "henriquan", "organ", "naval", "spy", "padrao", "lateen",
                     "sagres", "explorer"],
        "must_include": ["DEHCFeitorias", "HCShipCacadores3", "HCShipDragoons3", "HCExplorerPortuguese", "HCRoyalDecreePortuguese"],
        "must_exclude": [],
        "buildstyle": "Naval Mercantile Compound",
    },

    # Russians — Ivan the Terrible — Streltsy mass + Oprichnik shock + siege train
    "homecityrussians": {
        "keywords": ["russian", "strelet", "cossack", "oprichnik", "kalmuck",
                     "bashkir", "ataman", "blockhouse", "siberian", "romanov",
                     "catherine", "ivan", "kremlin", "petrine", "boyar"],
        "must_include": ["HCShipStrelets3", "HCShipCossacks3", "HCExplorerRussian", "HCRoyalDecreeRussian"],
        "must_exclude": [],
        "buildstyle": "Cossack Voisko",
    },

    # Spanish — Isabella I of Castile — Reconquista Tercio precursor
    "homecityspanish": {
        "keywords": ["spanish", "rodelero", "missionary", "lancer", "tercio",
                     "habsburg", "peninsular", "inquisition", "conquistador",
                     "isabella", "castile", "reconquista", "treasure", "alpaca",
                     "galleon", "guerrilla"],
        "must_include": ["DEHCHabsburgAllies1", "HCInquisition", "HCShipRodeleros3", "HCShipLancers3", "HCShipSpanishSquare", "HCSpanishTreasureFleet", "DEHCPeninsularGuerrillas", "HCExplorerSpanish", "HCRoyalDecreeSpanish"],
        "must_exclude": [],
        "buildstyle": "Forward Operational Line",
    },

    # Swedes — Gustavus Adolphus — Lion of the North combined arms
    "homecityswedish": {
        "keywords": ["swed", "carolean", "leather", "torp", "blakulla",
                     "hakkapeliitta", "leatherstocking", "nordic", "gustavus",
                     "lutheran", "tercentenary", "northstar"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Siege Train Concentration",
    },

    # Ethiopians — Menelik II — Solomonic highland modernization
    "homecityethiopians": {
        "keywords": ["ethiop", "abuna", "lalibela", "axum", "neftenya", "shotelai",
                     "gascenya", "monastery", "shrine", "monk", "menelik",
                     "solomon", "rastafar", "adwa", "imperial"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Highland Citadel",
    },

    # Hausa — Usman dan Fodio — Sokoto jihad cavalry
    "homecityhausa": {
        "keywords": ["hausa", "lifidi", "fulani", "raider", "palace", "sokoto",
                     "kano", "tribute", "marabout", "jihad", "usman", "kingdom",
                     "katsina", "horse"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Distributed Economic Network",
    },

    # Chinese — Kangxi Emperor — Eight-Banner pacification macro
    "homecitychinese": {
        "keywords": ["chinese", "ming", "manchu", "qing", "porcelain", "silk",
                     "kowtow", "rattan", "arquebus", "flaming", "monk", "village",
                     "wonder", "kangxi", "banner", "shaolin", "mandarin"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Compact Fortified Core",
    },

    # Japanese — Tokugawa Ieyasu — Bakufu shrine-and-musket order
    "homecityjapanese": {
        "keywords": ["japan", "samurai", "ashigaru", "yumi", "naginata", "shogun",
                     "rice", "tokugawa", "shrine", "daimyo", "consulate", "bakufu",
                     "bushido", "katana", "sengoku"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Shrine or Trade Node Spread",
    },

    # Indians — Shivaji Maharaj — Maratha Ganimi Kava raid
    "homecityindians": {
        "keywords": ["india", "sepoy", "mahout", "urumi", "rajput", "gurkha",
                     "wonder", "monk", "consulate", "agra", "shivaji", "maratha",
                     "ganimi", "swarajya", "konkan", "fort"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Shrine or Trade Node Spread",
    },

    # Italians — Giuseppe Garibaldi — Risorgimento volunteer columns
    "homecityitalians": {
        "keywords": ["italian", "bersagl", "elmetto", "papal", "schiavoni",
                     "lombard", "cavour", "garibald", "cathedral", "lampara",
                     "condotta", "pavisier", "risorgimento", "redshirt",
                     "thousand", "venetian"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Republican Levee",
    },

    # Maltese — Jean Parisot de Valette — Great Siege bastion defense
    "homecitymaltese": {
        "keywords": ["maltese", "malta", "knight", "hospital", "auberge",
                     "commander", "valette", "fortif", "bastion", "cathedral",
                     "balista", "siege", "tongue", "hospitaller", "fort", "bodrum",
                     "rhodes"],
        "must_include": ["DEHCKnightsMalta", "DEHCKnightsRhodes", "DEHCKnightsBodrum", "DEHCAuberges", "DEHCBritishTongue", "DEHCFrenchTongue", "DEHCSpanishTongue", "DEHCGermanTongue", "DEHCWallGuns", "DEHCExplorerMaltese", "HCHeavyFortifications"],
        "must_exclude": [],
        "buildstyle": "Highland Citadel",
    },

    # Mexicans (Standard) — Miguel Hidalgo y Costilla — Grito de Dolores levée
    "homecitymexicans": {
        "keywords": ["mexican", "soldado", "salinero", "insurgent", "cazador",
                     "agave", "hidalgo", "puebla", "guerrero", "criollo",
                     "fortifiedhacienda", "alhondiga", "dolores", "grito"],
        "must_include": ["DEHCAlhondigaDeGranaditas", "DEHCFedMXFortifiedHaciendas", "DEHCCharreada", "DEHCChipotles", "DEHCBarbacoa", "DEHCCriollos", "DEHCGeneralMexicans", "DEHCCavalryCombatMexican", "DEHCCathedralConstruction"],
        "must_exclude": [],
        "buildstyle": "Republican Levee",
    },

    # United States — George Washington — Continental Army Fabian-to-Yorktown
    "homecityamericans": {
        "keywords": ["united", "american", "pioneer", "owlhoot", "lawman",
                     "carbine", "gatling", "regular", "minute", "frontier",
                     "stagecoach", "washington", "continental", "ranger", "yorktown"],
        "must_include": ["DEHCMinutemenCompanies", "DEHCContinentalRangers", "DEHCShipRegulars3", "DEHCShipCarbineCav3", "DEHCRegularCombat", "DEHCKosciuszkoFortifications", "DEHCGeneralAmericans", "DEHCArkansasPost"],
        "must_exclude": [],
        "buildstyle": "Republican Levee",
    },

    # Inca — Pachacuti — Tawantinsuyu mass infantry
    "homecitydeinca": {
        "keywords": ["inca", "macehua", "runa", "huaminca", "chimu", "bolas",
                     "kancha", "tambo", "kallanka", "andean", "huaca", "huayna",
                     "pachacuti", "tawantinsuyu", "quipu"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Andean Terrace Fortress",
    },

    # Aztecs — Montezuma II — Flower War tribute aggression
    "homecityxpaztec": {
        "keywords": ["aztec", "jaguar", "eagle", "macehualtin", "puma", "skull",
                     "ritual", "calmec", "calendar", "tlaxcal", "zapotec", "chichi",
                     "montezuma", "flower", "tribute", "warchief"],
        "must_include": ["DEHCCalendarCeremony", "DEHCCalmecac", "DEHCSkullWall", "DEHCRitualGladiators", "DEHCShipJaguarKnights6", "DEHCMacehualtinCombat", "DEHCAztecFort", "HCXPShipEagleKnights3", "DEHCChichimecaRebellion", "DEHCZapotecAlliesTeam"],
        "must_exclude": [],
        "buildstyle": "Jungle Guerrilla Network",
    },

    # Haudenosaunee — Hiawatha — Confederacy forest warfare
    "homecityxpiroquois": {
        "keywords": ["iroquois", "haud", "tomahawk", "musketrider", "mantlet",
                     "warchief", "kanya", "longhouse", "wampum", "hiawatha",
                     "confederacy", "fivenations", "forest"],
        "must_include": ["HCXPShipTomahawk3", "HCXPWarChiefIroquois1"],
        "must_exclude": [],
        "buildstyle": "Shrine or Trade Node Spread",
    },

    # Lakota — Crazy Horse — Bighorn all-cavalry war
    "homecityxpsioux": {
        "keywords": ["sioux", "lakota", "dog", "rifle", "axe", "wakina", "pte",
                     "tipi", "tashunke", "tokala", "warchief", "crazyhorse",
                     "bighorn", "buffalo"],
        "must_include": ["HCXPShipDogSoldiers3", "HCXPShipRifleRiders3", "HCXPShipAxeRiders3", "HCXPWarChiefSioux1"],
        "must_exclude": [],
        "buildstyle": "Steppe Cavalry Wedge",
    },
}


# ── Revolution 26 civs ────────────────────────────────────────────────────

REVOLUTION: dict[str, dict] = {
    # Napoleon Bonaparte — Grande Armée Grand Battery empire
    "anwhomecitynapoleon": {
        "keywords": ["napoleon", "imperial", "oldguard", "grandbattery", "flyingbattery",
                     "hundreddays", "continental", "sister", "client", "horsehunter",
                     "rustam", "tirail", "cuirass", "balloon", "genie", "bosniak",
                     "mountedrifle", "navalgunner", "centsuisses", "wittelsbach",
                     "frenchroyal", "fencing", "theater", "grande", "armee"],
        "must_include": ["DEHCREVImperialOldGuard", "DEHCREVNapoleonicWarfare", "DEHCREVHundredDays", "DEHCREVGrandBattery", "DEHCREVFlyingBattery", "DEHCREVHorseHunters", "DEHCREVContinentalBlockade", "DEHCREVRustamsRegiment", "DEHCREVClientStates", "DEHCREVSisterRepublics", "DEHCShipBalloonsFrench"],
        "must_exclude": [],
        "buildstyle": "Forward Operational Line",
    },

    # Robespierre — Levée-en-masse Republic
    "anwhomecityrevolutionaryfrance": {
        "keywords": ["bastille", "guillotine", "robespierre", "cantinier",
                     "supremebeing", "horsehunter", "client", "revolutionar",
                     "frenchroyal", "tirail", "skirmisher", "musketeer", "general",
                     "officer", "leveeenmasse", "jacobin", "republic"],
        "must_include": ["DEHCREVBastilleStorming", "DEHCREVGuillotine", "DEHCREVRobespierre", "DEHCREVCultSupremeBeing", "DEHCREVCantinieres", "DEHCREVShipmentRevolutionaries", "DEHCREVHorseHunters", "DEHCREVClientStates"],
        "must_exclude": [],
        "buildstyle": "Republican Levee",
    },

    # Toussaint Louverture — Mass infantry insurrection
    "anwhomecityhaiti": {
        "keywords": ["haiti", "vodou", "sevites", "amazon", "akan", "marque",
                     "picket", "citizenship", "pirate", "privateer", "african",
                     "letter", "louverture", "saintdomingue"],
        "must_include": ["DEHCREVVodouCeremonies", "DEHCREVDahomeyAmazonsHaiti", "DEHCREVSevites", "DEHCREVAfricanAllies", "DEHCAkanAllies", "DEHCREVLetterOfMarque", "DEHCREVPickets", "DEHCREVCitizenshipHaiti", "DEHCREVHaitianBattleshipCard"],
        "must_exclude": [],
        "buildstyle": "Jungle Guerrilla Network",
    },

    # Jose de San Martin — Granadero shock-cavalry liberation
    "anwhomecityargentina": {
        "keywords": ["argentina", "argentine", "blandengue", "criollo", "sanmartin",
                     "trattoria", "cattle", "mortar", "pampa", "gaucho",
                     "liberation", "lombardy", "marvelous", "granadero", "andes"],
        "must_include": ["DEHCREVSanMartin", "DEHCREVBlandengues", "DEHCREVCriollos", "DEHCREVCattleDeliveryArgentina", "DEHCREVArgentineMortars", "DEHCREVTrattoria", "DEHCLiberationMarch", "DEHCMarvelousYear"],
        "must_exclude": [],
        "buildstyle": "Forward Operational Line",
    },

    # Pedro I of Brazil — Imperial line and Hessian reserve
    "anwhomecitybrazil": {
        "keywords": ["brazil", "carioca", "ordenanca", "samba", "bandeirante",
                     "candomble", "ironclad", "amazon", "rainforest", "pedro",
                     "imperial", "hessian", "lusobrazilian"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Distributed Economic Network",
    },

    # Bernardo O'Higgins — Balanced Republican infantry
    "anwhomecitychile": {
        "keywords": ["chile", "chilean", "huaso", "pacific", "andes", "ohiggins",
                     "valparaiso", "fronda", "carrera", "patria"],
        "must_include": ["DEHCExtensiveFortificationsEuropean"],
        "must_exclude": [],
        "buildstyle": "Andean Terrace Fortress",
    },

    # Simon Bolivar — Llanero liberation sweeps
    "anwhomecitycolumbia": {
        "keywords": ["columbia", "colombia", "bolivar", "llanero", "panama",
                     "magdalena", "andean", "granadine", "venezuela"],
        "must_include": ["DEHCLiberationMarch"],
        "must_exclude": [],
        "buildstyle": "Forward Operational Line",
    },

    # Mexicans (Revolution) — Hidalgo — Grito de Dolores levée
    "anwhomecitymexicans": {
        "keywords": ["mexican", "soldado", "salinero", "insurgent", "cazador",
                     "agave", "puebla", "hidalgo", "guerrero", "criollo",
                     "alhondiga", "dolores", "grito", "morelos"],
        "must_include": ["DEHCCharreada"],
        "must_exclude": [],
        "buildstyle": "Republican Levee",
    },

    # Sam Houston — Republic of Texas militia
    "anwhomecitytexas": {
        "keywords": ["texas", "ranger", "lancer", "burnet", "alamo", "sanjacinto",
                     "frontier", "ironclad", "fortwagon", "robberbaron",
                     "empresario", "gonzales", "sharpshooter", "haciendawagon",
                     "houston", "texian"],
        "must_include": ["DEHCREVMXTexasArmy", "DEHCREVMXTexasLancers", "DEHCREVMXTexasNavy", "DEHCREVMXEmpresarioContracts", "DEHCREVMXGonzalesGuns", "DEHCREVMXBurnetLand", "DEHCREVMXShipSharpshooters", "DEHCREVMXHeavyFortifications"],
        "must_exclude": [],
        "buildstyle": "Forward Operational Line",
    },

    # Juan Bautista Alvarado — Californio frontier horse raids
    "anwhomecitybajacalifornians": {
        "keywords": ["baja", "california", "ranchero", "californio", "gold",
                     "vaquero", "padre", "frontier", "alvarado", "mision"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Mobile Frontier Scatter",
    },

    # Jacinto Canek — Indigenous insurrection mass
    "anwhomecitymaya": {
        "keywords": ["maya", "yucatan", "jaguar", "calendar", "stelae", "ritual",
                     "milpa", "mayapan", "chichen", "canek", "uprising"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Jungle Guerrilla Network",
    },

    # Antonio Canales Rosillo — Rio Grande Republic horse
    "anwhomecityriogrande": {
        "keywords": ["riogrande", "rio", "ranchero", "frontier", "lancer",
                     "cattle", "vaquero", "norteno", "juarez", "canales"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Mobile Frontier Scatter",
    },

    # Andres de Santa Cruz — Andean fort line and native levy
    "anwhomecityperu": {
        "keywords": ["peru", "andean", "inca", "huaylas", "tupac", "potosi",
                     "cuzco", "ayacucho", "santacruz", "confederation"],
        "must_include": ["DEHCExtensiveFortificationsEuropean"],
        "must_exclude": [],
        "buildstyle": "Andean Terrace Fortress",
    },

    # Isaac Brock — Blockhouse infantry frontier
    "anwhomecitycanada": {
        "keywords": ["canad", "mountie", "voyageur", "metis", "habitant", "lumber",
                     "fur", "redcoat", "loyalist", "doublestack", "brock",
                     "fencible", "blockhouse"],
        "must_include": ["DEHCREVFencibles", "DEHCREVCanadianOfficer", "DEHCREVConscriptionCanada", "DEHCREVNativeAlliesCanada", "DEHCCanadianLoyalists"],
        "must_exclude": [],
        "buildstyle": "Compact Fortified Core",
    },

    # Thomas Jefferson — Continental Army Fabian-to-Yorktown (Revolution US)
    "anwhomecityamericans": {
        "keywords": ["american", "united", "pioneer", "minute", "ranger",
                     "carbine", "frontier", "regular", "musketeer", "continental",
                     "washington", "franklin", "gatling", "jefferson", "yorktown",
                     "powderalarm", "longrifle"],
        "must_include": ["DEHCREVPowderAlarm", "DEHCREVLongRifles"],
        "must_exclude": [],
        "buildstyle": "Republican Levee",
    },

    # Carl Gustaf Emil Mannerheim — Mannerheim-line ski infantry
    "anwhomecityfinland": {
        "keywords": ["finland", "finnish", "jaeger", "torp", "sissi", "lake",
                     "sami", "saimaa", "karelian", "mannerheim", "ski"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Compact Fortified Core",
    },

    # Lajos Kossuth — Honved hussar uprising
    "anwhomecityhungary": {
        "keywords": ["hungar", "magyar", "hussar", "pandour", "honved", "hajduk",
                     "kossuth", "frontier"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Steppe Cavalry Wedge",
    },

    # Alexandru Ioan Cuza — Danubian Principalities consolidation
    "anwhomecityromania": {
        "keywords": ["romania", "carpathian", "calarasi", "vlach", "boyar",
                     "wallachia", "moldavia", "transylvania", "cuza", "danubian"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Civic Militia Center",
    },

    # Paul Kruger — Boer commando trader-cavalry
    "anwhomecitysouthafricans": {
        "keywords": ["south", "africa", "boer", "afrikaner", "kommando",
                     "voortrekker", "trek", "zulu", "kimberley", "kruger",
                     "diamond"],
        "must_include": ["DEHCREVDiamondRush"],
        "must_exclude": [],
        "buildstyle": "Naval Mercantile Compound",
    },

    # Muhammad Ali Pasha — Nizam-i Cedid modernization
    "anwhomecityegypt": {
        "keywords": ["egypt", "muhammadali", "mameluke", "fellah", "nizami",
                     "pasha", "nile", "alexandria", "cairo", "bedouin", "nizam",
                     "modernization"],
        "must_include": [],
        "must_exclude": [],
        "buildstyle": "Highland Citadel",
    },

    # Hayreddin Barbarossa — Corsair raider economy
    "anwhomecitybarbary": {
        "keywords": ["barbary", "berber", "corsair", "salerover", "sale", "crabat",
                     "dey", "janissary", "algiers", "tunis", "tripoli", "barbarossa",
                     "letter", "marque", "raider", "naval"],
        "must_include": ["DEHCREVCorsairCaptain", "DEHCREVSaleRovers", "DEHCREVBerberNomads", "DEHCREVShipBarbaryWarrior", "DEHCREVShipBerberAllies", "DEHCREVBarbaryCombat"],
        "must_exclude": [],
        "buildstyle": "Naval Mercantile Compound",
    },

    # Prince Diponegoro — Java War guerrilla and kraton
    "anwhomecityindonesians": {
        "keywords": ["indon", "java", "sumatra", "aceh", "jong", "kraton",
                     "lantaka", "wokou", "majapahit", "spice", "bali",
                     "diponegoro", "javawar"],
        "must_include": ["DEHCREVKratonGuards", "DEHCREVAcehExports", "DEHCREVLantakas", "DEHCREVShipJavaSpearman", "DEHCREVShipCetbang", "DEHCREVShipWokouJunk"],
        "must_exclude": [],
        "buildstyle": "Shrine or Trade Node Spread",
    },
}


def get(civ_id: str) -> dict:
    if civ_id in STANDARD:
        return {"is_revolution": False, **STANDARD[civ_id]}
    if civ_id in REVOLUTION:
        return {"is_revolution": True, **REVOLUTION[civ_id]}
    raise KeyError(f"no themes registered for {civ_id}")


def all_civs() -> list[str]:
    return list(STANDARD.keys()) + list(REVOLUTION.keys())
