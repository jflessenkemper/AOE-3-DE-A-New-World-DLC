"""ANW civilization mapping and iterator."""

# All 45 ANW civilizations
# 2026-05-11: Corrected 22 stale vanilla/DE/XP token keys to their ANW-prefixed
# equivalents so this dict matches the PLAYBOOK_MATRIX token namespace.
# Removed ANWAmericans (revolution variant of ANWUSA — reuses anwhomecityusa.xml,
# not a distinct playbook slot; ANWUSA already covers it in the matrix).
# 2026-05-17: Removed ANWBajaCalifornians (abandoned prototype — never shipped).
#             Updated ANWRevFrance display "French Republic" → "France" and
#             ANWNapoleonicFrance display "French Empire" → "France (Napoleonic Era)"
#             to match post-France-merge stringmods.
ANW_CIVS = {
    "ANWAztecs": {"display": "Aztec Triple Alliance", "leader": "Montezuma II", "file_stem": "aztecs"},
    "ANWBritish": {"display": "British Empire", "leader": "Queen Elizabeth I", "file_stem": "british"},
    "ANWChinese": {"display": "Qing Dynasty", "leader": "Kangxi", "file_stem": "chinese"},
    "ANWDutch": {"display": "Dutch Republic", "leader": "Maurice of Nassau", "file_stem": "dutch"},
    "ANWEthiopians": {"display": "Ethiopian Empire", "leader": "Menelik II", "file_stem": "ethiopians"},
    "ANWFrench": {"display": "Bourbon France", "leader": "Louis XVIII", "file_stem": "french"},
    "ANWGermans": {"display": "German Empire", "leader": "Frederick the Great", "file_stem": "germans"},
    "ANWHaudenosaunee": {"display": "Haudenosaunee Confederacy", "leader": "Hiawatha", "file_stem": "haudenosaunee"},
    "ANWHausa": {"display": "Sokoto Caliphate", "leader": "Muhammadu Rumfa", "file_stem": "hausa"},
    "ANWInca": {"display": "Inca Empire", "leader": "Pachacuti", "file_stem": "inca"},
    "ANWIndians": {"display": "Maratha Empire", "leader": "Shivaji Maharaj", "file_stem": "indians"},
    "ANWItalians": {"display": "Kingdom of Italy", "leader": "Giuseppe Garibaldi", "file_stem": "italians"},
    "ANWJapanese": {"display": "Tokugawa Shogunate", "leader": "Tokugawa", "file_stem": "japanese"},
    "ANWLakota": {"display": "Lakota Sioux", "leader": "Chief Gall", "file_stem": "lakota"},
    "ANWMaltese": {"display": "Knights of Malta", "leader": "Jean de Valette", "file_stem": "maltese"},
    "ANWMexicans": {"display": "First Mexican Empire", "leader": "Miguel Hidalgo y Costilla", "file_stem": "mexicans"},
    "ANWOttomans": {"display": "Ottoman Empire", "leader": "Suleiman the Magnificent", "file_stem": "ottomans"},
    "ANWPortuguese": {"display": "Portuguese Empire", "leader": "Prince Henry", "file_stem": "portuguese"},
    "ANWRussians": {"display": "Russian Empire", "leader": "Ivan the Terrible", "file_stem": "russians"},
    "ANWSpanish": {"display": "Spanish Empire", "leader": "Isabella", "file_stem": "spanish"},
    "ANWSwedes": {"display": "Swedish Empire", "leader": "Gustavus Adolphus", "file_stem": "swedes"},
    "ANWUSA": {"display": "United States", "leader": "George Washington", "file_stem": "usa"},
    "ANWRevFrance": {"display": "France", "leader": "Robespierre"},
    "ANWNapoleonicFrance": {"display": "France (Napoleonic Era)", "leader": "Napoleon"},
    "ANWCanadians": {"display": "Province of Canada", "leader": "Isaac Brock"},
    "ANWBrazil": {"display": "Empire of Brazil", "leader": "Pedro I of Brazil"},
    "ANWArgentines": {"display": "Argentine Confederation", "leader": "José de San Martín"},
    "ANWChileans": {"display": "Republic of Chile", "leader": "Bernardo O'Higgins"},
    "ANWPeruvians": {"display": "Republic of Peru", "leader": "Andrés de Santa Cruz"},
    "ANWColumbians": {"display": "Gran Colombia", "leader": "Simón Bolívar"},
    "ANWHaitians": {"display": "First Empire of Haiti", "leader": "Toussaint Louverture"},
    "ANWIndonesians": {"display": "Sultanate of Yogyakarta", "leader": "Prince Diponegoro"},
    "ANWSouthAfricans": {"display": "South African Republic", "leader": "Paul Kruger"},
    "ANWFinnish": {"display": "Grand Duchy of Finland", "leader": "Mannerheim"},
    "ANWHungarians": {"display": "Kingdom of Hungary", "leader": "Kossuth"},
    "ANWRomanians": {"display": "United Romanian Principalities", "leader": "Alexandru Ioan Cuza"},
    "ANWBarbary": {"display": "Regency of Algiers", "leader": "Barbarossa"},
    "ANWEgyptians": {"display": "Khedivate of Egypt", "leader": "Muhammad Ali"},
    "ANWMayans": {"display": "Cruzob Maya", "leader": "Canek"},
    "ANWTexians": {"display": "Republic of Texas", "leader": "Sam Houston"},
    # 2026-05-18: ANWFrenchCanadians removed. Papineau doctrine variant
    # is no longer active. Brock (loyalist) leads ANWCanadians.
    # ANWAmericans and the legacy revolution ANWMexicans entry were
    # removed earlier in the migration.
}

def iter_anw_civs():
    """Iterate over all ANW civilizations."""
    for civ_name in sorted(ANW_CIVS.keys()):
        yield civ_name, ANW_CIVS[civ_name]

