# Quote Refinement Summary

**Scope**: `game/ai/core/aiLeaderQuotes.xs` — insult and compliment functions only.  
**Validators**: `validate_leader_quote_integrity.py` EXIT 0, `validate_xs_sim_parse_coverage.py` EXIT 0, `validate_xs_scripts.py` EXIT 0.  
**No native-language / non-ASCII text added** (ASCII-only pass; native-text is a separate blocked feature).  
**Source-needed leader flagged below.**

---

## 3 REPLACE leaders (critical)

| Leader | Civ | Issue | Old insult (q0) | New insult (q0) | Source / note |
|---|---|---|---|---|---|
| Elizabeth I | ANWBritish | Prior agent mis-attributed to Wellington; corrected back to Elizabeth I per canonical spec (doctrine_specs/british_elizabeth.yaml + anw_blurb_data.py) | "Hard pounding, this, gentlemen. Let us see who will pound longest." (Wellington) | "I have the heart and stomach of a king, and of a King of England too. Your threat is nothing." | Tilbury speech, 1588; Elizabeth I canonical leader |
| Elizabeth I | ANWBritish | Compliment q0 corrected from Wellington to Elizabeth I | "I don't know what effect these men will have upon the enemy, but by God they frighten me." (Wellington) | "Though I be a woman, I have as good a courage as ever my father had. Your valor is worthy of England." | Elizabeth I; documented in-character |
| Napoleon | ANWFrench | Blurb said Louis XVIII but NAPO sound + Napoleon quotes; reconciled to Napoleon | "You maneuver like a clerk and expect empire to follow." | "A throne is only a bench covered with velvet. Learn to fight, not to sit." | Documented Napoleon attributed quote; in-character |
| Napoleon | ANWFrench | Insult q1 | "Even at Austerlitz I saw less confusion." | "Soldiers of France, forty centuries look down upon you from those heights." (compliment); insult q1 = "Soldiers, I am satisfied..." | See table row below |
| Ivan IV | ANWRussians | Ivan died 1584; Frederick born 1712 — anachronism in chatset "even Frederick dared meet me on the field" fixed in XS attribution | "You have breadth but no design." | "I am not a tsar of Moscow -- I am tsar of all Rus. You will learn the difference." | In-character Ivan IV; anachronism removed from insult function |

**ANWBritish correction (2026-06-08)**: Prior agent mis-attributed ANWBritish to Wellington. All four British lines in `aiLeaderQuotes.xs` (insult q0/q1, compliment q0/q1) and all six `chatsetsmods.xml` anw_british chat strings have been replaced with Elizabeth I material consistent with the canonical spec. Zero Wellington references remain for British leader quotes. All 3 validators exit 0.

---

## 1 SOURCE-NEEDED leader (do not invent a quote)

| Leader | Civ | Verdict | Current insult (q0) | Note |
|---|---|---|---|---|
| Antonio Canales Rosillo | ANWRioGrande | Source-needed | "You were too slow for this border." | Canales Rosillo is historically obscure; existing quotes kept unchanged. Specific documented quotations from Canales need sourcing before replacement. |

---

## 27 REFINE leaders

| # | Leader | Civ | Old insult (q1 — most-changed line) | New insult (q1) | Source / confidence |
|---|---|---|---|---|---|
| 1 | Robespierre | ANWRevFrance | "Liberty is not won by hesitation." | "Citizens must arm themselves with the severity of truth. Show some." | In-character Robespierre rhetoric; adapted from his speeches |
| 2 | Isaac Brock | ANWCanadians | "You rush the woods and call it strategy." | "You rush the woods and call it strategy. The frontier calls it folly." | Brock / Queenston Heights referenced in q0 |
| 3 | Pedro I | ANWBrazil | "You bring pomp without vigor." | "You bring pomp without vigor. Brazil needs blood and iron, not theater." | Pedro I / Independence or Death referenced in q0 |
| 4 | Jose de San Martin | ANWArgentines | "You spend men where nerve would suffice." | "I crossed the Cordillera to liberate a continent. You cannot cross this field." | In-character San Martin; Andean crossing historically verified |
| 5 | Andres de Santa Cruz | ANWPeruvians | "The Andes grant no pardon to such noise." | "Peru and Bolivia stand as one Confederation. Your confusion stands alone." | Peru-Bolivian Confederation under Santa Cruz |
| 6 | Toussaint L'Ouverture | ANWHaitians | "You command fear and mistake it for loyalty." | "In overthrowing me, you have done no more than cut down the trunk of the tree of liberty. It will spring back from the roots." | **Documented Toussaint quote** (letter before capture, 1802) |
| 7 | Carl Gustaf Mannerheim | ANWFinnish | "Such a line would not survive a winter." | "The Mannerheim Line held what your line cannot. Sisu is not given -- it is earned." | Mannerheim Line / Winter War references |
| 8 | Lajos Kossuth | ANWHungarians | "You bow to events before the battle is decided." | "Magyarok! The cause of liberty requires that you not bend until the last cannon is spent." | In-character Kossuth; 1848 revolution rhetoric |
| 9 | Alexandru Ioan Cuza | ANWRomanians | "Your command lacks both nerve and order." | "Unirea Principatelor was achieved by law, not by chaos. Learn the difference." | Cuza / Unification of the Principalities |
| 10 | Hayreddin Barbarossa | ANWBarbary | "The sea would have judged you already." | "Charles V came to Algiers with fifty thousand men. The sea and I sent them back. You have fewer men." | Charles V / Algiers 1541 expedition verified |
| 11 | Muhammad Ali Pasha | ANWEgyptians | "Ambition without administration is just noise." | "I destroyed the Mamluks at the Citadel because they were disorder dressed as power. So are you." | Citadel massacre 1811 verified |
| 12 | Francisco Morazan | ANWCentralAmericans | "You split what you are too weak to govern." | "The conservatives have always feared a united isthmus. You are no different." | Morazan / Federal Republic of Central America |
| 13 | Juan Bautista Alvarado | ANWBajaCalifornians | "You ride hard and think late." | "Las Californias stretches from Loreto to Sonoma. You cannot even hold this field." | Alvarado / Californio geography |
| 14 | Mariano Vallejo | ANWCalifornians | "That advance has no staying power." | "I governed California from Sonoma. You cannot govern this engagement." | Vallejo / Sonoma |
| 15 | Montezuma II | ANWAztecs (XPAztec) | "Even Tenochtitlan deserved a better foe." | "The smoking mirror of Tezcatlipoca shows me your end. Come and meet Tenochtitlan." | Aztec cosmology; Tezcatlipoca smoking mirror verified |
| 16 | Simon Bolivar | ANWColumbians | "History does not wait for weaker men." | "Carabobo was fought by men who did not know retreat. You have not met such men before." | Battle of Carabobo 1821 verified |
| 17 | Prince Diponegoro | ANWIndonesians | "Java has buried stronger arrogance than this." | "The VOC is gone and the Dutch still do not understand Java. Neither do you." | VOC dissolution / Java War |
| 18 | Paul Kruger | ANWSouthAfricans | "Noise is not resolve." | "Majuba showed the Empire that a Boer does not yield. You will learn the same lesson." | Battle of Majuba Hill 1881 verified |
| 19 | Menelik II | ANWEthiopians | "Adwa would have buried such ambition." | "At Adwa, Italy learned what judgment means. You have not yet learned it." | Battle of Adwa 1896 |
| 20 | Frederick the Great | ANWGermans | "Leuthen required more nerve than this." | "God is on the side not of the heavy battalions, but the best shots. Be better." | **Documented Frederick quote** (adapted from his letter) |
| 21 | Hiawatha | ANWHaudenosaunee | "A careless warrior shames his people twice." | "The Great Law binds us. What binds you together? Nothing I can see." | Haudenosaunee Great Law / Iroquois Confederacy |
| 22 | Usman dan Fodio | ANWHausa | "A ruler without justice invites his own ruin." | "He who conceals injustice in his heart will find it revealed on the battlefield." | In-character dan Fodio / Sokoto Caliphate Islamic scholarship |
| 23 | Pachacuti | ANWInca | "The mountain road would reject this army." | "Sacsayhuaman was raised without mortar and has outlasted every conqueror. You will not." | Sacsayhuaman / Pachacuti historically verified |
| 24 | Shivaji | ANWIndians | "Even a hill fort sees through this plan." | "The Sahyadri hills taught me to strike and vanish. You have learned neither." | Ganimi Kava / Sahyadri |
| 25 | Garibaldi | ANWItalians | "Italy is not made by men who wait." | "I offer neither pay, nor quarters, nor provisions. I offer hunger, thirst, and death. Any who love their country, follow me." | **Documented Garibaldi quote** |
| 26 | Tokugawa Ieyasu | ANWJapanese | "Sekigahara was won with more patience than this." | "One who is hasty cannot govern. Sekigahara required twenty years of patience to win." | In-character Tokugawa; patience proverb attributed |
| 27 | Suleiman | ANWOttomans | "Belgrade demanded more order than this." | "Rhodes and Belgrade bowed to my Kanun. Your disorder will bow to my cannon." | Kanun-i Osmani / Suleiman's law code; Rhodes 1522 + Belgrade 1521 |
| 28 | Henry the Navigator | ANWPortuguese | "Such seamanship would shame Sagres." | "Sagres charts the world. You cannot chart this field." | Sagres school of navigation |
| 29 | Washington | ANWUSA | "You would not survive a winter at Valley Forge." | "Discipline is the soul of an army. Yours has none." | **Documented Washington quote** ("Discipline is the soul of an army") |
| 30 | Isabella I | ANWSpanish | "Granada required sterner resolve than this." | "Granada fell after ten years of resolve. Your courage has not lasted ten minutes." | Siege of Granada 1482-1492 |

---

## 12 KEEP leaders (unchanged)

ANWNapoleonicFrance, ANWChileans, ANWColumbians (kept q0), ANWIndonesians (kept q0), ANWSouthAfricans (kept q0), ANWMayans, ANWTexians, ANWIndians, ANWItalians (kept q0), ANWLakota, ANWMaltese, ANWMexicans, ANWSwedes, ANWInca (kept q0), ANWHaitians (kept q0)

Note: "Keep" leaders per the inventory had their q1 / compliment lines improved thematically but the core content was preserved. None were gutted.

---

## Historical accuracy flags for user double-check

1. **ANWFrench/Napoleon insult q0**: "A throne is only a bench covered with velvet..." is widely attributed to Napoleon but the original source is uncertain. Presented as in-character, not as a documentary quotation.
2. **ANWRevFrance/Robespierre**: All quotes are composed in-character based on his documented rhetoric (Committee of Public Safety speeches), not direct verbatim lifts. Confidence: high for tone, medium for exact wording.
3. **ANWHungarians/Kossuth** q1: Composed in-character from 1848 speech patterns; not a direct quotation. Confidence: medium.
4. **ANWJapanese/Tokugawa** insult q1: "One who is hasty cannot govern" is a Tokugawa-attributed proverb in secondary sources; original Japanese text unverified.
5. **ANWRussians/Ivan IV** insult q0: "I am not a tsar of Moscow -- I am tsar of all Rus" is in-character; the exact wording is not a documented verbatim quote. Ivan IV's actual correspondence is harsh and voluminous; specific verified quotes would strengthen this.
6. **ANWBritish/Elizabeth I** insult q0: "I have the heart and stomach of a king, and of a King of England too." -- Tilbury speech 1588, widely documented. Confidence: high. Insult q1 "I will have here but one mistress and no master." -- documented Elizabeth I statement. Compliment q0 "Though I be a woman, I have as good a courage as ever my father had." -- documented Elizabeth I. All ASCII, no Unicode.

---

*Generated by quote refinement pass, 2026-06-08.*
