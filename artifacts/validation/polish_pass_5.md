# Polish Pass 5 — Independent Third Audit
Generated 2026-05-26. Audited 10 civs: Russians, Ottomans, Germans, Indians, Lakota, Texians, Brazil, Italians, Egyptians, Haudenosaunee.

---

## Executive Summary

**4 new issues found**, not flagged in polish_pass_3, polish_pass_4, blurb_vs_spec_audit, doctrine_prose_audit, or column_site_audit_2026-05-23.

1. Haudenosaunee `data/anw_civ_blurbs.json` — "Aenna Shotgun Rider" phantom unit persists (HTML fix was never backported to the JSON source).
2. Texians `data/anw_civ_blurbs.json` — blurb is infantry-only framing; XS btBiasCav runs 0.65 → 0.90 across all ages, making it one of the highest cavalry-bias civs in the mod.
3. Egyptians `data/anw_civ_blurbs.json` — blurb leads with "Mameluke cavalry per shipment"; XS btBiasInf dominates (0.85 → 1.0) and btBiasCav is secondary (0.35 → 0.65).
4. Indians `playstyle_spec.json` — `doctrine_prose` is the generic Highland Citadel template ("Fortifies a single high-ground position…"); the blurb was correctly updated to Ganimi Kava framing after blurb_vs_spec_audit, but the spec's own prose field was never updated to match.

---

## Per-Civ Findings

### 1. Haudenosaunee — "Aenna Shotgun Rider" not backported to blurbs.json

**Prior fix scope:** `column_site_audit_2026-05-23.md` line 66 records the fix applied to `a_new_world_columns.html` only. The JSON source was not updated.

**Blurb JSON (`data/anw_civ_blurbs.json` line 213):** `"Aenna Shotgun Rider"` — phantom unit. No proto entry in techtreemods.xml or stringmods.xml.

**XS dispatch (`leader_hiawatha.xs` comment line 11):** "Tomahawk + Aenna pressure on enemy villagers" — Aenna is foot infantry. No shotgun-rider sub-type assigned anywhere in the file.

**Fix:** `data/anw_civ_blurbs.json` line 213 — `"Aenna Shotgun Rider"` → `"Aenna"`.

---

### 2. Texians — blurb omits cavalry; XS btBiasCav is 0.65 → 0.90

**Blurb (`data/anw_civ_blurbs.json` line 511):**
> "Push barracks and Outposts forward; Minuteman swarms defend while Regulars train; Republic militia mass into Sharpshooter FF timing."

No cavalry mention.

**XS dispatch (`leader_revolution_commanders.xs`):** `llSetMilitaryFocus(0.6, 0.65, 0.25)` — cavalry already leads infantry at init. Per-age: Colonial btBiasCav=0.80 (line 1018); Fortress 0.85 (line 1082); Industrial 0.90 (line 1146); Imperial 0.90 (line 1210). btBiasInf does not match btBiasCav until Imperial. `llEnableForwardBaseStyle()` fires at Colonial, Fortress, and Industrial.

**Spec (`playstyle_spec.json`):** `doctrine_prose` = "Pushes barracks, **stables**, and outposts up toward the map's contested edge" — stables confirms cavalry intent; blurb omits it.

**Prior audit status:** `blurb_vs_spec_audit.md` line 127 listed Texians **clean**. `column_site_audit_2026-05-23.md` line 37 flagged the HTML column (🔴 High) but not the blurb JSON.

**Fix:** `data/anw_civ_blurbs.json` line 511. Suggested replacement:
> "Push Stables and barracks forward; Chinaco cavalry and Minuteman infantry form a combined-arms advance; Sharpshooters screen the flanks as the Republic line reaches the enemy base."

---

### 3. Egyptians — blurb leads with cavalry; XS is infantry-and-artillery dominant

**Blurb (`data/anw_civ_blurbs.json` line 146):**
> "Fortify high ground then snowball; **Mameluke cavalry per shipment grows a dangerous force**; hard to dislodge once entrenched."

Cavalry presented as the primary snowball identity.

**XS dispatch (`leader_revolution_commanders.xs` init line 666):** `llSetMilitaryFocus(0.7, 0.3, 0.55)` — infantry (0.7) and artillery (0.55) both outrank cavalry (0.3). Per-age: Colonial btBiasInf=0.85 / btBiasCav=0.35 / btBiasArt=0.10 (line 1006); Fortress 0.95/0.50/0.70 (line 1070); Industrial 1.00/0.55/0.85 (line 1134); Imperial 1.00/0.65/1.00 (line 1198). btBiasCav never exceeds 0.65 and is the weakest arm through Colonial.

**Spec (`playstyle_spec.json`):** `doctrine_summary` = "Nizam-i Cedid modernization" — infantry modernization, not cavalry. `doctrine_prose` = "Fortifies a single high-ground position… Builds wide only after the citadel is unbreakable." No cavalry primacy mentioned.

**Prior audit status:** `blurb_vs_spec_audit.md` line 107 listed Egyptians **clean**; `doctrine_prose_audit.md` found no issues.

**Fix:** `data/anw_civ_blurbs.json` line 146. Suggested replacement:
> "Fortify high ground behind Nizam-i Cedid infantry lines and a growing cannon park; Mameluke cavalry screens the flanks while the citadel becomes unbreakable; hard to dislodge once entrenched."

---

### 4. Indians — spec `doctrine_prose` is stale Highland Citadel template after blurb rewrite

**What happened:** `blurb_vs_spec_audit.md` (line 17–28) flagged the Indians blurb as a **Hard Error** (Mughal/fortress framing conflicting with Shivaji Ganimi Kava doctrine). The blurb was subsequently rewritten to Ganimi Kava framing. The spec's `doctrine_prose` field was not updated.

**Blurb (current, `data/anw_civ_blurbs.json`):**
> "Ganimi Kava raid doctrine: swift Urumi and Sepoy strikes from high-ground cover deny open engagements; bleed the enemy economy with hit-and-run pressure; Howdah elephants commit only after the foe is softened, with Consulate allies sustaining the column."

**Spec `doctrine_prose` (`playstyle_spec.json` under "Indians Akbar", line ~464):**
> "Fortifies a single high-ground position with stone walls, layered towers, and a fort. Slow to expand and slow to push, but extremely hard to dislodge once entrenched. Builds wide only after the citadel is unbreakable."

This is the verbatim Highland Citadel template shared by Egyptians, Ethiopians, and Maltese. It directly contradicts both the blurb and the XS (`leader_shivaji.xs` Colonial rule: `btBiasCav=0.75`, `llEnableForwardBaseStyle()` — an aggressive forward-cavalry doctrine, not a fortress turtle).

The spec's `doctrine_summary` field (`"Maratha Ganimi Kava raid"`) correctly names the doctrine, but `doctrine_prose` is copy-paste from the wrong template and was never overridden.

**Fix:** `playstyle_spec.json` under `"Indians Akbar"`, `doctrine_prose` field — replace the Highland Citadel template with Shivaji-specific prose. Suggested replacement:
> "Opens with Sowar cavalry raids and Sepoy screens from Colonial on (llEnableForwardBaseStyle at age 2). Hill-fort line anchors ground already taken rather than anchoring a home base. Howdah Elephants and Mansabdar units commit once the raid has bled the opponent's eco; the Maratha Confederacy expands outward, not inward."

---

## Verified Clean (no new issues)

| Civ | XS file / block | Notes |
|-----|-----------------|-------|
| Russians (Ivan) | `leader_catherine.xs` | Blurb matches Streltsy+Oprichnik doctrine; XS btBiasInf=0.90-1.0, btBiasCav=0.40-0.70 consistent with "backbone+shock" framing |
| Ottomans (Suleiman) | `leader_suleiman.xs` | Blurb matches siege-column+Janissary doctrine; XS btBiasArt escalates to 1.0 Imperial; "forward staging walls" consistent with `gLLWallStrategy` |
| Germans (Frederick) | `leader_frederick.xs` | Spec prose (after pass_3 rewrite) aligns with XS; blurb "Settler Wagon eco" is mechanically accurate (home city has HCShipSettlerWagons series); cavalry escalation acknowledged in spec prose |
| Lakota (Chief Gall) | `leader_crazy_horse.xs` | Blurb envelopment framing consistent with XS btBiasCav=0.95-1.0; "Axe Rider and Tokala flanking columns" accurate to XS unit comments |
| Brazil (Pedro) | `leader_revolution_commanders.xs` (gRvltCivId=26) | Blurb eco framing consistent with spec Distributed Economic Network; btBiasInf dominates as expected; no forward-base language in blurb |
| Italians (Garibaldi) | `leader_garibaldi.xs` | Blurb "Papal Guard + Bersagliere" consistent with XS infantry bias (0.85-1.0); "Lombard coin boom" consistent with btBiasTrade ramp; `llSetBuildStrongpointProfile(2,2,3,true)` aligns with forward strongpoint |
| Haudenosaunee (playstyle text) | `leader_hiawatha.xs` | Playstyle prose ("Trading Posts and shrines", "isolated towers and fast cavalry") accurate; issue is only the `unique_units` array entry |

---

## Skipped

No civs skipped. All 10 sampled civs were audited at full depth (XS + spec + blurb). Remaining 30 of 40 civs were not read in this pass per the stated time budget; no new issues were found in the 10 sampled that suggest systematic failures across the unread civs.
