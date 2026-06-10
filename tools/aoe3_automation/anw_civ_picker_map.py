"""Mapping from ANW mod tokens to lobby picker indices.

INTEGER INDICES: 0-based positions in the full (base-game + ANW mod) SELECT
CIVILIZATION picker list, in the order the game engine renders it.

AUTHORITATIVE SOURCE AT RUNTIME:
    picker_civ_order.json — built from a live OCR walk of the picker.
    lobby_driver.set_civ_by_token_fast() reads scroll_count + click_row from
    that file directly.  The integer indices here are a SECONDARY source used
    only when the live cache file is absent (analytical fallback rebuild via
    lobby_driver --rebuild-cache --derive-only) or by code that drives the
    picker via keyboard Up/Down navigation (anw_master_orchestrator.py →
    in_game_driver._select_civ_for_slot).

WARNING — STALE SCROLL TABLE:
    picker_scroll_table.json was built 2026-04-28 against the 46-civ picker.
    It does NOT include Baja Californians, Californians, Central Americans, or
    Rio Grande.  The analytical fallback that derives scroll_count from these
    integer indices is therefore unreliable for civs beyond index 7 (British).
    Prefer picker_civ_order.json (built via live OCR walk) for correct
    scroll_count + click_row values.

INDEX ORDERING NOTE (audited 2026-06-08 against picker_walk_raw.json):
    The picker sorts by DISPLAY NAME (city name field), not by civ token.
    Lakota's home city is shown as "(Great Council)" which alphabetises
    before "A" entries, so it appears near the top of the list even though
    its token starts with 'L'.  Most other civs appear in token-alphabetical
    order.  Indices below are APPROXIMATE for the live picker; the
    picker_civ_order.json scroll_count/click_row values are the ground truth.

DUPLICATE INDEX NOTICE:
    ANWNapoleonicFrance and ANWFrench both map to the same scroll position in
    the live picker (both display as "France (Paris)" / "French Empire (Paris)"
    depending on exact picker build).  The picker_civ_order.json entries for
    these two use the same scroll_count=39/click_row=9 value from the OCR
    walk; only one is in-picker at a given slot.
"""

# Approximate 0-based position in the live (2026-05-17) SELECT CIVILIZATION
# picker.  See module docstring for limitations.  Primary key for validation
# only; runtime selection uses picker_civ_order.json.
ANW_TO_PICKER_INDEX = {
    "ANWArgentines": 2,             # Argentina (Buenos Aires)
    "ANWAztecs": 3,                 # Aztec Empire (Tenochtitlan)
    # Baja California sorts after Argentina/Aztec:
    "ANWBajaCalifornians": 4,       # Baja California (La Paz)
    "ANWBarbary": 5,                # Barbary States (Algiers)
    "ANWBrazil": 6,                 # Brazilians (Rio de Janeiro)
    "ANWBritish": 7,                # Britain (London)
    # Californians, Canadians, and Central Americans were added after the stale
    # picker_scroll_table.json was frozen (2026-04-28, 46 entries).
    # Correct live indices (verified against picker_civ_order.json, 2026-06-08):
    "ANWCalifornians": 8,           # Californians (Sonoma)           [was 10 — fixed]
    "ANWCanadians": 9,              # Canadians (Quebec)
    "ANWCentralAmericans": 10,      # Central Americans (Guatemala City) [was 11 — fixed]
    "ANWChileans": 11,              # Chileans (Santiago)
    "ANWChinese": 12,               # China (Beijing)
    "ANWColumbians": 13,            # Gran Colombia (Bogota)
    "ANWEgyptians": 14,             # Egyptians (Cairo)
    "ANWEthiopians": 15,            # Ethiopia (Gondar)
    "ANWFinnish": 16,               # Finnish (Helsinki)
    "ANWFrench": 17,                # France (Paris)
    "ANWGermans": 18,               # Germany (Berlin)
    "ANWHaitians": 19,              # Haitians (Port-au-Prince)
    "ANWHungarians": 20,            # Hungarians (Buda)
    "ANWInca": 21,                  # Inca Empire (Cuzco)
    "ANWIndonesians": 22,           # Indonesians (Yogyakarta)
    "ANWHaudenosaunee": 23,         # Iroquois Confederacy (Caughnawaga)
    "ANWItalians": 24,              # Italy (Venice)
    "ANWJapanese": 25,              # Japan (Kyoto)
    # Lakota sorts near top of live picker (display: "(Great Council)") but
    # we keep its approximate mid-list index here for consistency with the
    # stale scroll_table. picker_civ_order.json scroll_count=4 is authoritative.
    "ANWLakota": 26,                # Lakota (Great Council)
    "ANWMaltese": 27,               # Malta (Valletta)
    "ANWMayans": 28,                # Maya (Chan Santa Cruz)
    "ANWMexicans": 29,              # Mexico (Mexico City)
    "ANWIndians": 30,               # Mughal India (Delhi)
    "ANWNapoleonicFrance": 31,      # French Empire (Paris)
    "ANWDutch": 32,                 # Netherlands (Amsterdam)
    "ANWOttomans": 33,              # Ottoman Empire (Istanbul)
    "ANWPeruvians": 34,             # Peruvians (Lima)
    "ANWPortuguese": 35,            # Portugal (Lisbon)
    "ANWRevFrance": 36,             # Revolutionary French (Paris)
    "ANWRioGrande": 37,             # Rio Grande (Laredo)
    "ANWRomanians": 38,             # Romanians (Bucharest)
    "ANWRussians": 39,              # Russia (St. Petersburg)
    "ANWHausa": 40,                 # Sokoto (Kano)
    "ANWSouthAfricans": 41,         # South Africans (Pretoria)
    "ANWSpanish": 42,               # Spain (Seville)
    "ANWSwedes": 43,                # Sweden (Stockholm)
    "ANWTexians": 44,               # Texas (Austin)
    "ANWUSA": 45,                   # United States (Washington D.C.)
}
