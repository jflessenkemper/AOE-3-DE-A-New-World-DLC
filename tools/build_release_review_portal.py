#!/usr/bin/env python3
"""
build_release_review_portal.py — Pre-release sign-off portal.

Takes the existing `a_new_world_columns.html` (one column per civ, ~635 KB)
and post-processes it into `a_new_world_review.html` — a self-contained
HTML file the user opens in a browser to walk through every civ, visually
confirm every art surface, and tick off sign-off checkboxes before
pushing the Workshop update.

Adds three layers on top of the existing column site:

  1. A sticky top bar with:
       - the dashboard verdict pill (SHIP WITH KNOWN GAPS, etc.)
       - a progress meter: "N/40 approved"
       - a filter dropdown (All / Pending / Flagged / Approved)
       - a jump-to-civ select (alphabetical)
       - keyboard shortcut hints
       - Export sign-off JSON
       - Reset all

  2. A sign-off panel injected into each <section class="civ-col">:
       - Civ status row (Static / Art / Spec / Runtime pills from
         release_readiness.json)
       - 4 confirmation checkboxes (visual / doctrine / blurb / ship)
       - Notes textarea
       - APPROVE & NEXT button (sets all 4, status=approved, jumps to
         next pending civ)
       - FLAG ISSUE button (asks for a required note, status=flagged)

  3. JavaScript layer:
       - localStorage persistence (key: anw_release_review)
       - Filter logic (hides/shows civ-col sections)
       - Keyboard shortcuts (A = approve, F = flag, → ← = nav,
         / = focus jump-to)
       - Export = downloads <date>_release_signoff.json
       - On full sign-off (40/40 approved) shows a "READY TO PUBLISH"
         banner and reveals a "copy deploy command" snippet.

This file is 100% additive — it does not change any existing column
semantics. The original `a_new_world_columns.html` remains untouched.

Run: python3 tools/build_release_review_portal.py
Open: a_new_world_review.html in a browser.
"""

from __future__ import annotations

import json
import os
import re
import sys
from html import escape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(MOD_ROOT, "a_new_world_columns.html")
DST = os.path.join(MOD_ROOT, "a_new_world_review.html")
DASH = os.path.join(MOD_ROOT, "artifacts", "validation", "release_readiness.json")
BLURBS = os.path.join(MOD_ROOT, "data", "anw_civ_blurbs.json")


def load_dashboard() -> dict:
    """Map civ-token-ish → row from release_readiness.json.

    The dashboard rows are keyed by spec_key ("Argentines San Martin Revolution")
    not by civ token ("ANWArgentines"), so we build both lookups.
    """
    if not os.path.exists(DASH):
        return {"verdict": "UNKNOWN", "counts": {}, "by_civlabel": {}, "by_spec": {}}
    data = json.loads(open(DASH, encoding="utf-8").read())
    by_civlabel = {}
    by_spec = {}
    for row in data.get("civs", []):
        spec_key = row.get("spec_key", "")
        civ_label = row.get("civ_label", "")
        by_spec[spec_key] = row
        # The civ_label is "Argentines", "British", ... — derive the
        # ANW<Label> token (best-effort; some civs need overrides).
        token_label = civ_label.replace(" ", "").replace("'", "")
        by_civlabel[token_label] = row
    return {
        "verdict": data.get("verdict", "UNKNOWN"),
        "counts": data.get("counts", {}),
        "by_civlabel": by_civlabel,
        "by_spec": by_spec,
    }


# ── Civ-token → dashboard civ_label override map. Built by hand from the
# release_readiness.json civ_label values. Only non-trivial cases are
# listed; ANW<Civ> with Civ stripped == civ_label by default.
#
# Values match the *stripped* civ_label that `load_dashboard()` uses as
# its by_civlabel key (i.e. spaces and apostrophes removed). So "United
# States" → "UnitedStates", "French Louis" → "FrenchLouis", etc.
_TOKEN_TO_CIVLABEL = {
    "ANWUSA": "UnitedStates",
    "ANWRevFrance": "RevolutionaryFrance",
    "ANWNapoleonicFrance": "NapoleonicFrance",
    "ANWFrench": "FrenchLouis",  # Louis XVIII Bourbon
    "ANWSouthAfricans": "SouthAfricans",
    "ANWHaudenosaunee": "Haudenosaunee",
    "ANWCanadians": "Canadians",
    "ANWBrazil": "Brazil",
    "ANWArgentines": "Argentines",
    "ANWChileans": "Chileans",
    "ANWPeruvians": "Peruvians",
    "ANWColumbians": "Columbians",
    "ANWMexicans": "Mexicans",
    "ANWTexians": "Texians",
    "ANWHaitians": "Haitians",
    "ANWIndonesians": "Indonesians",
    "ANWFinnish": "Finnish",
    "ANWHungarians": "Hungarians",
    "ANWRomanians": "Romanians",
    "ANWBarbary": "Barbary",
    "ANWEgyptians": "Egyptians",
    "ANWEthiopians": "Ethiopians",
    "ANWHausa": "Hausa",
    "ANWMaltese": "Maltese",
    "ANWMayans": "Mayans",
    "ANWIndians": "Indians",
    "ANWAztecs": "Aztecs",
    "ANWInca": "Inca",
    "ANWLakota": "Lakota",
    "ANWChinese": "Chinese",
    "ANWJapanese": "Japanese",
    "ANWBritish": "British",
    "ANWFrench_dup": "French",  # not used; placeholder
    "ANWGermans": "Germans",
    "ANWRussians": "Russians",
    "ANWSpanish": "Spanish",
    "ANWOttomans": "Ottomans",
    "ANWPortuguese": "Portuguese",
    "ANWDutch": "Dutch",
    "ANWItalians": "Italians",
    "ANWSwedes": "Swedes",
}


def dashboard_row_for(token: str, dash: dict) -> dict:
    label = _TOKEN_TO_CIVLABEL.get(token, token.replace("ANW", ""))
    return dash["by_civlabel"].get(label, {})


def pill(text: str, ok: bool | None) -> str:
    """Static/Art/Spec/Runtime status pill. ok=True → green, False → red,
    None → grey."""
    cls = "pill-ok" if ok is True else ("pill-fail" if ok is False else "pill-warn")
    return f'<span class="rr-pill {cls}">{escape(text)}</span>'


def status_pills(row: dict) -> str:
    if not row:
        return '<span class="rr-pill pill-warn">no dashboard row</span>'
    parts = [
        pill("Static " + ("✓" if row.get("static_pass") else "✗"), row.get("static_pass")),
        pill("Art " + ("✓" if row.get("art_pass") else "✗"), row.get("art_pass")),
        pill("Spec " + ("✓" if row.get("spec_pass") else "✗"), row.get("spec_pass")),
    ]
    # Runtime is allowed to be WARN; surface that distinctly.
    runtime_ok = row.get("runtime_pass")
    if runtime_ok is True:
        parts.append(pill("Runtime ✓", True))
    else:
        parts.append(pill("Runtime ⚠", None))
    overall = row.get("overall", "?")
    parts.append(f'<span class="rr-pill pill-overall pill-{overall.lower()}">{escape(overall)}</span>')
    return " ".join(parts)


"""Civs where a historical-canon / design choice is still open and
the user is the only one who can make the call. Surfaced as a blue
"❓ Decision" banner so the reviewer can resolve in-flow rather than
flipping back to the audit doc.
Source: artifacts/validation/column_site_audit_2026-05-23.md
🟡 medium-priority table."""
DECISION_NOTES = {
    "ANWHaitians": (
        "Toussaint died 1803 before Haiti declared independence (1804, "
        "Dessalines's First Empire). Options: (A) rename civ to "
        "\"Republic of Saint-Domingue\" (Toussaint's title); "
        "(B) switch leader to Dessalines; (C) keep as artistic licence."
    ),
    "ANWMayans": (
        "Jacinto Canek (executed 1761) predates the Cruzob movement "
        "(Caste War 1847) by ~86 years. Real founders: Cecilio Chi + "
        "Jacinto Pat. Options: (A) switch to Chi/Pat; (B) keep Canek "
        "as symbolic of Maya resistance."
    ),
    "ANWMexicans": (
        "Hidalgo (executed 1811) cannot be paired with the First Mexican "
        "Empire (Iturbide, 1821). Options: (A) rename to \"Insurgent "
        "Mexico\" / \"Grito de Dolores\"; (B) keep as-is."
    ),
    "ANWRevFrance": (
        "Robespierre was a politician (Committee of Public Safety, "
        "executed 1794), not a military commander. Options: (A) replace "
        "with Lazare Carnot (\"organizer of victory\"); (B) drop the "
        "named commander — sub-header \"The Terror · Revolutionary "
        "France\" alone."
    ),
    "ANWBrazil": (
        "XS log says \"Pedro II\"; HTML sub-header says \"Pedro I.\" "
        "Options: (A) align HTML to Pedro II (long reign 1841–1889, "
        "more AoE3-era); (B) change XS to Pedro I and keep HTML. "
        "Gameplay identical."
    ),
    "ANWLakota": (
        "Sub-header now says \"Chief Gall\" but the avatar DDT is "
        "`cpai_avatar_lakota_crazy_horse.png`. Options: (A) rename "
        "the portrait file; (B) revert sub-header to Crazy Horse; "
        "(C) keep as-is (reused art)."
    ),
    "ANWCanadians": (
        "Strategic-identity text mentions \"Lower-Canada Patriote "
        "doctrine\" but the AI personality is Isaac Brock (War of 1812, "
        "died 1812). Papineau's Patriote rebellion was 1837 — 25 years "
        "later. Suggestion: replace phrase with \"War of 1812 defensive "
        "posture.\""
    ),
}

"""Civs with known-intentional leader/doctrine substitutions that
look like bugs at first glance but are deliberate per the
MORNING_DEPLOY_BRIEF design notes. These get a yellow "intentional"
banner in the sign-off panel so the reviewer doesn't flag them.
Source: artifacts/validation/polish_pass_3.md + commit 3e0d00b."""
INTENTIONAL_NOTES = {
    "ANWIndians": (
        "Leader renamed Akbar → Shivaji Maharaj (Maratha Ganimi-Kava raid "
        "doctrine, not Mughal elephant citadel). Intentional per 3e0d00b."
    ),
    "ANWRussians": (
        "Leader renamed Catherine → Ivan the Terrible (Streltsy/Oprichnik "
        "siege, not Cossack cavalry stream). Intentional per 3e0d00b."
    ),
    "ANWLakota": (
        "Leader renamed Crazy Horse → Chief Gall (Little Bighorn "
        "envelopment, not pure speed-raid). Intentional per 3e0d00b."
    ),
    "ANWTexians": (
        "ai_behaviour_map.py previously read the vanilla ANWTexians "
        "block instead of the ANWTexians block (mapper artefact, fixed). "
        "Actual dispatch is cavalry-aggressive with forward base."
    ),
    "ANWRomanians": (
        "Forward base intentionally disabled — Cuza's 1859 was internal "
        "consolidation, not external expansion. Per 9c0c39c."
    ),
}


def signoff_panel_html(token: str, row: dict) -> str:
    """Sign-off panel injected at the top of each civ-col section."""
    leader = escape(row.get("leader_label", ""))
    pills = status_pills(row)
    note = INTENTIONAL_NOTES.get(token, "")
    note_html = (
        f'<div class="rr-signoff-note rr-signoff-note-intentional">'
        f'<strong>ⓘ Intentional design:</strong> {escape(note)}'
        f'</div>'
    ) if note else ""
    decision = DECISION_NOTES.get(token, "")
    decision_html = (
        f'<div class="rr-signoff-note rr-signoff-note-decision">'
        f'<strong>❓ Needs decision:</strong> {escape(decision)}'
        f'</div>'
    ) if decision else ""
    return f"""
<div class="rr-signoff" data-civ="{escape(token)}">
  <div class="rr-signoff-head">
    <span class="rr-signoff-leader">{leader}</span>
    <span class="rr-signoff-pills">{pills}</span>
    <span class="rr-signoff-state" data-role="state">pending</span>
  </div>
  {note_html}
  {decision_html}
  <div class="rr-signoff-checks">
    <label><input type="checkbox" data-check="visual">  Visual art correct (portrait, home city, flag)</label>
    <label><input type="checkbox" data-check="doctrine"> AI doctrine matches lore</label>
    <label><input type="checkbox" data-check="blurb">    Player-facing blurb reads well</label>
    <label><input type="checkbox" data-check="ship">     Ready to ship</label>
  </div>
  <div class="rr-signoff-notes">
    <textarea data-role="notes" rows="2" placeholder="Issue notes (required if flagged) — written here are preserved in browser localStorage and exported in the final JSON."></textarea>
  </div>
  <div class="rr-signoff-buttons">
    <button type="button" data-action="approve" class="rr-btn rr-btn-approve">APPROVE &amp; NEXT &nbsp;<span class="rr-key">A</span></button>
    <button type="button" data-action="flag" class="rr-btn rr-btn-flag">FLAG ISSUE &nbsp;<span class="rr-key">F</span></button>
    <button type="button" data-action="reset" class="rr-btn rr-btn-reset">RESET</button>
  </div>
</div>
""".strip()


def nav_strip_html(tokens: list[str], token_to_label: dict) -> str:
    """A sticky row of 40 color-coded tiles, one per civ. Status colour
    (grey = pending, green = approved, orange = flagged) is hydrated by
    JS from localStorage on load and on every state change. Click → scroll
    to that civ."""
    tiles = []
    for tok in tokens:
        leader = token_to_label.get(tok, "")
        short = tok.replace("ANW", "")
        title = f"{tok}" + (f" — {leader}" if leader else "")
        tiles.append(
            f'<a class="rr-tile" data-rr-tile="{escape(tok)}" '
            f'href="#{escape(tok)}" title="{escape(title)}">'
            f'<span class="rr-tile-label">{escape(short)}</span></a>'
        )
    return (
        '<div class="rr-navstrip" id="rr-navstrip">'
        + "".join(tiles)
        + "</div>"
    )


def flagged_panel_html() -> str:
    """Right-side collapsible drawer showing every civ the user flagged,
    with their notes. Rebuilt by JS whenever state changes."""
    return (
        '<button type="button" class="rr-flag-toggle" id="rr-flag-toggle" '
        'title="Toggle flagged-civs panel">⚐ <span data-role="flag-count">0</span></button>'
        '<aside class="rr-flag-panel" id="rr-flag-panel" hidden>'
        '<div class="rr-flag-panel-head">'
        '<h3>Flagged civs</h3>'
        '<button type="button" class="rr-btn rr-btn-reset" id="rr-flag-close">close</button>'
        '</div>'
        '<div class="rr-flag-list" data-role="flag-list">'
        '<p class="rr-flag-empty">No civs flagged. Press <kbd>F</kbd> on a civ to flag it.</p>'
        '</div>'
        '<div class="rr-flag-panel-foot">'
        '<button type="button" class="rr-btn rr-btn-approve" id="rr-flag-copy">'
        'Copy flagged summary to clipboard</button>'
        '</div>'
        '</aside>'
    )


def lightbox_html() -> str:
    """Image lightbox modal. Hidden by default. JS opens it on click of
    any <img> inside a civ-col."""
    return (
        '<div class="rr-lightbox" id="rr-lightbox" hidden>'
        '<button type="button" class="rr-lightbox-close" title="Close (Esc)">×</button>'
        '<img class="rr-lightbox-img" alt="">'
        '<div class="rr-lightbox-caption" data-role="lightbox-caption"></div>'
        '</div>'
    )


def top_bar_html(dash: dict) -> str:
    """Sticky top bar. Verdict, progress, filter, jump-to, export, reset."""
    verdict = dash["verdict"]
    counts = dash["counts"]
    verdict_cls = {
        "READY TO SHIP": "verdict-ok",
        "SHIP WITH KNOWN GAPS": "verdict-warn",
        "BLOCKED": "verdict-fail",
    }.get(verdict, "verdict-warn")
    pass_n = counts.get("pass", counts.get("PASS", 0))
    warn_n = counts.get("warn", counts.get("WARN", 0))
    fail_n = counts.get("fail", counts.get("FAIL", 0))
    total_n = counts.get("total", counts.get("Total", 0))
    return f"""
<div class="rr-topbar" id="rr-topbar">
  <span class="rr-verdict {verdict_cls}" title="dashboard verdict from release_readiness.json">{escape(verdict)}</span>
  <span class="rr-counts">PASS {pass_n} · WARN {warn_n} · FAIL {fail_n} / {total_n}</span>
  <span class="rr-progress-wrap">
    <span class="rr-progress-label">Reviewed: <span data-role="reviewed-count">0</span>/<span data-role="total-count">40</span></span>
    <span class="rr-progress-bar"><span class="rr-progress-fill" data-role="progress-fill" style="width:0%"></span></span>
  </span>
  <label>Filter:
    <select id="rr-filter">
      <option value="all">All civs</option>
      <option value="pending" selected>Pending only</option>
      <option value="flagged">Flagged only</option>
      <option value="approved">Approved only</option>
      <option value="runtime-warn">Runtime WARN only (need in-game probe)</option>
    </select>
  </label>
  <label>Jump:
    <select id="rr-jump">
      <option value="">— select civ —</option>
    </select>
  </label>
  <button type="button" id="rr-export" class="rr-btn rr-btn-approve">Export sign-off JSON</button>
  <button type="button" id="rr-reset-all" class="rr-btn rr-btn-reset">Reset all</button>
  <span class="rr-help">[A]pprove · [F]lag · ← → nav · / = jump · ? = help</span>
</div>
<div class="rr-shipbanner" id="rr-shipbanner" hidden>
  <span class="rr-ship-text">🚢 All 40 civs approved.</span>
  <code class="rr-ship-cmd">python3 tools/deploy_to_mod.py</code>
  <span class="rr-ship-hint">Run that command, then in Steam: Workshop → A New World → Update.</span>
</div>
""".strip()


PORTAL_CSS = r"""
:root {
  --rr-bg: #0f1116; --rr-fg: #e8eaee; --rr-muted:#9aa0a8;
  --rr-ok:#2fb84f; --rr-warn:#d8a020; --rr-fail:#d94646; --rr-flag:#e26a3a;
  --rr-card:#181c24; --rr-border:#2a2f3a;
}
.rr-topbar {
  position: sticky; top:0; left:0; right:0; z-index:9999;
  background:#0b0d12; color:var(--rr-fg);
  display:flex; flex-wrap:wrap; align-items:center; gap:12px;
  padding:8px 14px; border-bottom:2px solid #2a2f3a;
  font:13px/1.4 system-ui,-apple-system,sans-serif;
}
.rr-topbar .rr-btn {
  font:600 12px/1 system-ui,sans-serif; padding:6px 10px; border-radius:4px;
  cursor:pointer; border:1px solid #444; background:#1a1f2a; color:#e8eaee;
}
.rr-topbar .rr-btn-approve { background:#1f6f3a; border-color:#2fb84f; }
.rr-topbar .rr-btn-reset   { background:#3a1f1f; border-color:#d94646; }
.rr-topbar select { background:#1a1f2a; color:var(--rr-fg); border:1px solid #444;
  padding:4px 6px; font:13px/1.4 system-ui,sans-serif; }
.rr-verdict { padding:4px 10px; border-radius:4px; font-weight:700; letter-spacing:.5px; }
.rr-verdict.verdict-ok   { background:var(--rr-ok);   color:#fff; }
.rr-verdict.verdict-warn { background:var(--rr-warn); color:#111; }
.rr-verdict.verdict-fail { background:var(--rr-fail); color:#fff; }
.rr-counts { color:var(--rr-muted); }
.rr-progress-wrap { display:flex; align-items:center; gap:8px; }
.rr-progress-bar { display:inline-block; width:160px; height:10px; background:#222;
  border-radius:6px; overflow:hidden; border:1px solid #333; }
.rr-progress-fill { display:block; height:100%; background:var(--rr-ok); transition:width .2s; }
.rr-help { color:var(--rr-muted); margin-left:auto; font-size:11px; }

.rr-shipbanner {
  background:var(--rr-ok); color:#fff; padding:14px 16px; text-align:center;
  font:600 16px/1.4 system-ui,sans-serif; position:sticky; top:42px; z-index:9998;
}
.rr-shipbanner .rr-ship-cmd { background:#001; padding:4px 10px; margin:0 8px;
  border-radius:4px; font:13px/1 monospace; }

/* Per-civ sign-off panel — slides in at the top of every <section class="civ-col">.
   The column site uses 100vh columns; the panel is absolute-positioned to overlay
   the top 220 px of the column so it never displaces the existing layout. */
.civ-col { position: relative; }
.rr-signoff {
  position:absolute; top:0; left:0; right:0;
  background:rgba(15,17,22,0.92); color:var(--rr-fg);
  padding:8px 12px 10px; z-index:5;
  font:12px/1.3 system-ui,-apple-system,sans-serif;
  border-bottom:2px solid rgba(255,255,255,0.15);
  box-shadow:0 2px 8px rgba(0,0,0,0.4);
}
.rr-signoff[data-status="approved"] { border-bottom-color:var(--rr-ok); background:rgba(31,111,58,0.92); }
.rr-signoff[data-status="flagged"]  { border-bottom-color:var(--rr-flag); background:rgba(58,30,15,0.92); }
.rr-signoff-head { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-bottom:6px; }
.rr-signoff-leader { font-weight:700; font-size:13px; }
.rr-pill { display:inline-block; padding:1px 7px; border-radius:3px; font-size:11px;
  border:1px solid rgba(255,255,255,0.2); }
.rr-pill.pill-ok   { background:var(--rr-ok);   color:#fff; }
.rr-pill.pill-fail { background:var(--rr-fail); color:#fff; }
.rr-pill.pill-warn { background:var(--rr-warn); color:#111; }
.rr-pill.pill-overall { font-weight:700; margin-left:4px; }
.rr-pill.pill-pass { background:var(--rr-ok); color:#fff; }
.rr-pill.pill-warn { background:var(--rr-warn); color:#111; }
.rr-pill.pill-fail { background:var(--rr-fail); color:#fff; }
.rr-signoff-state { margin-left:auto; padding:1px 8px; border-radius:3px;
  background:#444; color:#fff; font-size:11px; text-transform:uppercase; }
.rr-signoff[data-status="approved"] .rr-signoff-state { background:var(--rr-ok); }
.rr-signoff[data-status="flagged"]  .rr-signoff-state { background:var(--rr-flag); }
.rr-signoff-note {
  margin: 4px 0 6px; padding: 5px 8px; border-radius: 3px;
  font-size: 11px; line-height: 1.35; background: rgba(216,160,32,0.18);
  border-left: 3px solid var(--rr-warn); color: #f3e1b8;
}
.rr-signoff-note strong { color: var(--rr-warn); margin-right: 4px; }
.rr-signoff-note-decision {
  background: rgba(80,120,200,0.18);
  border-left-color: #6688cc;
  color: #d2dcee;
}
.rr-signoff-note-decision strong { color: #aac1ff; }
.rr-signoff-checks { display:grid; grid-template-columns:repeat(2,1fr); gap:2px 14px; margin-bottom:6px; }
.rr-signoff-checks label { display:flex; align-items:center; gap:6px; cursor:pointer; }
.rr-signoff-notes textarea {
  width:100%; box-sizing:border-box; resize:vertical; font:12px/1.3 system-ui,sans-serif;
  background:rgba(0,0,0,0.4); color:var(--rr-fg); border:1px solid #444; border-radius:3px; padding:4px 6px;
}
.rr-signoff-buttons { display:flex; gap:8px; margin-top:6px; }
.rr-signoff-buttons .rr-btn {
  font:700 12px/1 system-ui,sans-serif; padding:7px 12px; border-radius:4px;
  cursor:pointer; border:1px solid #555; background:#1a1f2a; color:#e8eaee;
}
.rr-signoff-buttons .rr-btn-approve { background:#1f6f3a; border-color:#2fb84f; }
.rr-signoff-buttons .rr-btn-flag    { background:#aa3a14; border-color:#e26a3a; }
.rr-signoff-buttons .rr-btn-reset   { background:#3a1f1f; border-color:#d94646; }
.rr-key { background:#000; color:#0f0; padding:1px 4px; border-radius:2px; font:11px monospace; }

/* Filter hiding: civ-col with data-rr-hide=1 collapses to 0 width
   in the horizontal scroller so the user only sees what they're
   filtering for. */
.civ-col[data-rr-hide="1"] { display:none !important; }

/* Help overlay (toggled by ?) */
.rr-help-overlay {
  position:fixed; inset:0; background:rgba(0,0,0,0.85); color:#fff;
  display:flex; align-items:center; justify-content:center; z-index:10000;
  font:14px/1.6 system-ui,sans-serif;
}
.rr-help-overlay > div { background:#0f1116; padding:24px 32px; border-radius:8px;
  max-width:560px; border:1px solid #2a2f3a; }
.rr-help-overlay h3 { margin:0 0 12px; }
.rr-help-overlay kbd { background:#000; color:#0f0; padding:2px 6px; border-radius:3px;
  font:13px monospace; margin-right:6px; }
.rr-help-overlay button { margin-top:12px; }

/* Push the existing column content down to give room for the panel.
   The first direct child inside each civ-col is .col-header for normal
   civs and .stub-content for base/DLC stub civs. Padding both keeps
   the leader portrait + body from being hidden behind the sign-off.
   Note: we add ~28 extra px to account for the nav strip stickying
   below the topbar (the panel is absolute inside the col, but the
   col itself isn't scrolled past the sticky chrome). */
.civ-col > .col-header,
.civ-col > .stub-content {
  margin-top: 240px;
}

/* ── Civ-nav strip ────────────────────────────────────────────────────
   Sticky row of 40 color-coded tiles below the topbar. Each tile gets
   its colour from the data-rr-status attribute (set by JS from
   localStorage). */
.rr-navstrip {
  position:sticky; top:42px; left:0; right:0; z-index:9998;
  background:#0b0d12; border-bottom:1px solid #2a2f3a;
  display:flex; flex-wrap:wrap; gap:2px; padding:4px 8px;
}
.rr-tile {
  display:inline-block; padding:3px 6px; font:600 10px/1.2 system-ui,sans-serif;
  background:#2a2f3a; color:#bbb; border-radius:3px; text-decoration:none;
  border:1px solid #1a1f2a; cursor:pointer; user-select:none;
  transition:background .15s, color .15s;
}
.rr-tile:hover { background:#444; color:#fff; }
.rr-tile[data-rr-status="approved"] { background:var(--rr-ok);   color:#fff; }
.rr-tile[data-rr-status="flagged"]  { background:var(--rr-flag); color:#fff; }
.rr-tile[data-rr-status="warn"]     { background:var(--rr-warn); color:#111; }
.rr-tile-label { letter-spacing:.3px; }

/* ── Image lightbox ───────────────────────────────────────────────────
   Click any <img> inside a civ-col to open the source image at its
   natural size in an overlay. Esc or click anywhere to close. */
.rr-lightbox {
  position:fixed; inset:0; background:rgba(0,0,0,0.92); z-index:10001;
  display:flex; align-items:center; justify-content:center; flex-direction:column;
  cursor:zoom-out;
}
.rr-lightbox[hidden] { display:none; }
.rr-lightbox-img {
  max-width:96vw; max-height:90vh; box-shadow:0 0 60px rgba(0,0,0,0.8);
  background:#fff;
}
.rr-lightbox-caption {
  position:absolute; bottom:14px; left:14px; right:14px; text-align:center;
  color:#ddd; font:13px/1.4 system-ui,sans-serif; pointer-events:none;
}
.rr-lightbox-close {
  position:absolute; top:14px; right:18px; background:rgba(0,0,0,0.7);
  color:#fff; border:1px solid #444; border-radius:4px;
  font:700 22px/1 system-ui,sans-serif; padding:4px 12px; cursor:pointer;
}
/* Show pointer cursor on every visible image inside a civ-col so it's
   obvious you can click to zoom. */
.civ-col img { cursor:zoom-in; }

/* ── Flagged-civs panel + toggle ──────────────────────────────────────
   Floating ⚐ button (bottom-right) opens a side drawer with every
   flagged civ + its note. */
.rr-flag-toggle {
  position:fixed; bottom:14px; right:14px; z-index:9997;
  background:var(--rr-flag); color:#fff; border:none; border-radius:24px;
  padding:8px 16px; font:700 14px/1 system-ui,sans-serif; cursor:pointer;
  box-shadow:0 4px 14px rgba(0,0,0,0.4);
}
.rr-flag-toggle:hover { background:#d8551e; }
.rr-flag-panel {
  position:fixed; top:88px; right:0; bottom:0; width:360px; z-index:9996;
  background:#0f1116; color:var(--rr-fg); border-left:2px solid var(--rr-flag);
  box-shadow:-4px 0 16px rgba(0,0,0,0.5);
  display:flex; flex-direction:column;
  font:13px/1.4 system-ui,sans-serif;
}
.rr-flag-panel[hidden] { display:none; }
.rr-flag-panel-head {
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 14px; border-bottom:1px solid #2a2f3a;
}
.rr-flag-panel-head h3 { margin:0; font-size:14px; }
.rr-flag-list { flex:1; overflow-y:auto; padding:10px 14px; }
.rr-flag-list .rr-flag-empty { color:var(--rr-muted); font-style:italic; }
.rr-flag-list .rr-flag-entry {
  margin-bottom:12px; padding:8px 10px; background:#1a1f2a; border-radius:4px;
  border-left:3px solid var(--rr-flag); cursor:pointer;
}
.rr-flag-list .rr-flag-entry:hover { background:#262c3a; }
.rr-flag-list .rr-flag-entry-civ {
  font-weight:700; color:#fff; margin-bottom:4px;
}
.rr-flag-list .rr-flag-entry-note {
  color:#ccc; font-size:12px; white-space:pre-wrap; word-break:break-word;
}
.rr-flag-panel-foot {
  padding:10px 14px; border-top:1px solid #2a2f3a;
}
.rr-flag-panel-foot .rr-btn { width:100%; }
"""


def portal_js(token_to_label: dict) -> str:
    """JavaScript layer. Renders sign-off state, persists to localStorage,
    applies filter, exports JSON. Embedded inline so the file is self-
    contained when opened by file://."""
    token_to_label_json = json.dumps(token_to_label)
    return r"""
<script>
(function(){
  'use strict';
  const STORAGE_KEY = 'anw_release_review';
  const TOKEN_LABELS = """ + token_to_label_json + r""";

  function loadState(){
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch(e){ return {}; }
  }
  function saveState(s){
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch(e){}
  }

  function statusOf(civState){
    if (!civState) return 'pending';
    return civState.status || 'pending';
  }

  function allChecked(civState){
    if (!civState || !civState.checks) return false;
    const c = civState.checks;
    return c.visual && c.doctrine && c.blurb && c.ship;
  }

  function applyToPanel(panel, civState){
    const status = statusOf(civState);
    panel.dataset.status = status;
    panel.querySelector('[data-role="state"]').textContent = status;
    const checks = (civState && civState.checks) || {};
    ['visual','doctrine','blurb','ship'].forEach(k=>{
      const cb = panel.querySelector(`input[data-check="${k}"]`);
      if (cb) cb.checked = !!checks[k];
    });
    const ta = panel.querySelector('textarea[data-role="notes"]');
    if (ta) ta.value = (civState && civState.notes) || '';
  }

  function hydrateNavStrip(state){
    // Paint each tile in the nav strip with its current sign-off status.
    document.querySelectorAll('.rr-tile').forEach(tile=>{
      const civ = tile.dataset.rrTile;
      const status = statusOf(state[civ]);
      if (status === 'pending') tile.removeAttribute('data-rr-status');
      else tile.setAttribute('data-rr-status', status);
    });
  }

  function rebuildFlagPanel(state){
    const list = document.querySelector('[data-role="flag-list"]');
    const countEl = document.querySelector('[data-role="flag-count"]');
    if (!list || !countEl) return;
    const flagged = Object.entries(state)
      .filter(([_, v]) => v && v.status === 'flagged');
    countEl.textContent = flagged.length;
    if (!flagged.length){
      list.innerHTML = '<p class="rr-flag-empty">No civs flagged. Press <kbd>F</kbd> on a civ to flag it.</p>';
      return;
    }
    list.innerHTML = '';
    flagged.sort((a,b) => a[0].localeCompare(b[0]));
    flagged.forEach(([civ, v])=>{
      const e = document.createElement('div');
      e.className = 'rr-flag-entry';
      e.dataset.civ = civ;
      const leader = TOKEN_LABELS[civ] || '';
      const head = civ.replace(/^ANW/,'') + (leader ? ' — ' + leader : '');
      e.innerHTML = '<div class="rr-flag-entry-civ"></div><div class="rr-flag-entry-note"></div>';
      e.querySelector('.rr-flag-entry-civ').textContent = head;
      e.querySelector('.rr-flag-entry-note').textContent = (v.notes || '(no note)');
      e.addEventListener('click', ()=>{
        const col = document.getElementById(civ);
        if (col) scrollToCol(col);
      });
      list.appendChild(e);
    });
  }

  function updateProgress(){
    const state = loadState();
    const panels = document.querySelectorAll('.rr-signoff');
    let approved = 0;
    panels.forEach(p=>{
      const civ = p.dataset.civ;
      if (statusOf(state[civ]) === 'approved') approved++;
    });
    document.querySelector('[data-role="reviewed-count"]').textContent = approved;
    document.querySelector('[data-role="total-count"]').textContent = panels.length;
    const pct = panels.length ? (approved / panels.length * 100) : 0;
    document.querySelector('[data-role="progress-fill"]').style.width = pct + '%';
    const banner = document.getElementById('rr-shipbanner');
    if (banner) banner.hidden = (approved < panels.length);
    hydrateNavStrip(state);
    rebuildFlagPanel(state);
  }

  // ── Lightbox ─────────────────────────────────────────────────────────
  function openLightbox(src, caption){
    const lb = document.getElementById('rr-lightbox');
    if (!lb) return;
    const img = lb.querySelector('.rr-lightbox-img');
    const cap = lb.querySelector('[data-role="lightbox-caption"]');
    img.src = src;
    img.alt = caption || '';
    if (cap) cap.textContent = caption || '';
    lb.hidden = false;
  }
  function closeLightbox(){
    const lb = document.getElementById('rr-lightbox');
    if (!lb) return;
    lb.hidden = true;
    const img = lb.querySelector('.rr-lightbox-img');
    if (img) img.src = '';
  }

  // ── Flagged-panel toggle + copy ─────────────────────────────────────
  function toggleFlagPanel(force){
    const p = document.getElementById('rr-flag-panel');
    if (!p) return;
    if (force === true)  p.hidden = false;
    else if (force === false) p.hidden = true;
    else p.hidden = !p.hidden;
  }
  function copyFlaggedSummary(){
    const state = loadState();
    const flagged = Object.entries(state)
      .filter(([_, v]) => v && v.status === 'flagged')
      .sort((a,b) => a[0].localeCompare(b[0]));
    if (!flagged.length){
      alert('No civs flagged.');
      return;
    }
    const lines = ['ANW v1.0 — flagged civs (' + flagged.length + ')', ''];
    flagged.forEach(([civ, v])=>{
      const leader = TOKEN_LABELS[civ] || '';
      lines.push('• ' + civ.replace(/^ANW/,'') + (leader ? ' (' + leader + ')' : ''));
      lines.push('  ' + (v.notes || '(no note)').replace(/\n/g, '\n  '));
      lines.push('');
    });
    const text = lines.join('\n');
    if (navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(
        ()=> alert('Copied ' + flagged.length + ' flagged civs to clipboard.'),
        ()=> alert('Clipboard copy failed. Text:\n\n' + text)
      );
    } else {
      alert(text);
    }
  }

  function applyFilter(){
    const mode = document.getElementById('rr-filter').value;
    const state = loadState();
    document.querySelectorAll('section.civ-col').forEach(col=>{
      const civ = col.id;
      const civState = state[civ];
      const status = statusOf(civState);
      let show = true;
      if (mode === 'pending')   show = (status === 'pending');
      else if (mode === 'flagged')  show = (status === 'flagged');
      else if (mode === 'approved') show = (status === 'approved');
      else if (mode === 'runtime-warn') {
        const panel = col.querySelector('.rr-signoff');
        const pillsHtml = panel ? panel.querySelector('.rr-signoff-pills').innerHTML : '';
        show = /Runtime\s+⚠/.test(pillsHtml);
      }
      col.dataset.rrHide = show ? '0' : '1';
    });
  }

  function nextCiv(currentId, direction){
    const cols = Array.from(document.querySelectorAll('section.civ-col[data-rr-hide="0"], section.civ-col:not([data-rr-hide])'));
    if (!cols.length) return null;
    const idx = cols.findIndex(c => c.id === currentId);
    if (idx === -1) return cols[0];
    const next = (idx + direction + cols.length) % cols.length;
    return cols[next];
  }

  function scrollToCol(col){
    if (!col) return;
    col.scrollIntoView({behavior:'smooth', inline:'start', block:'start'});
    // Move keyboard focus to the column so subsequent shortcuts target it
    col.setAttribute('tabindex', '-1');
    col.focus({preventScroll:true});
  }

  function currentColInView(){
    const cols = document.querySelectorAll('section.civ-col');
    let best = null, bestDist = Infinity;
    cols.forEach(c=>{
      const r = c.getBoundingClientRect();
      if (r.right < 0 || r.left > window.innerWidth) return;
      const dist = Math.abs(r.left);
      if (dist < bestDist){ bestDist = dist; best = c; }
    });
    return best;
  }

  function approveCurrent(){
    const col = currentColInView(); if (!col) return;
    const panel = col.querySelector('.rr-signoff'); if (!panel) return;
    panel.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
    const state = loadState();
    state[col.id] = {
      checks:{visual:true,doctrine:true,blurb:true,ship:true},
      notes: (state[col.id] && state[col.id].notes) || '',
      status: 'approved',
      timestamp: Date.now()
    };
    saveState(state);
    applyToPanel(panel, state[col.id]);
    updateProgress();
    // jump to next non-approved in filter view
    const cols = Array.from(document.querySelectorAll('section.civ-col[data-rr-hide="0"], section.civ-col:not([data-rr-hide])'));
    const remaining = cols.filter(c => statusOf((loadState())[c.id]) !== 'approved');
    if (remaining.length) scrollToCol(remaining[0]);
  }

  function flagCurrent(){
    const col = currentColInView(); if (!col) return;
    const panel = col.querySelector('.rr-signoff'); if (!panel) return;
    const ta = panel.querySelector('textarea[data-role="notes"]');
    const existing = ta ? ta.value.trim() : '';
    const note = prompt('Why are you flagging ' + col.id + '? (required)', existing);
    if (note === null) return;
    if (!note.trim()){ alert('Flag note is required.'); return; }
    if (ta) ta.value = note;
    const state = loadState();
    state[col.id] = {
      checks: (state[col.id] && state[col.id].checks) || {visual:false,doctrine:false,blurb:false,ship:false},
      notes: note,
      status: 'flagged',
      timestamp: Date.now()
    };
    saveState(state);
    applyToPanel(panel, state[col.id]);
    updateProgress();
  }

  function exportSignoff(){
    const state = loadState();
    const out = {
      generated: new Date().toISOString(),
      total_civs: document.querySelectorAll('.rr-signoff').length,
      approved: Object.values(state).filter(v => v.status === 'approved').length,
      flagged:  Object.values(state).filter(v => v.status === 'flagged').length,
      civs: {}
    };
    document.querySelectorAll('.rr-signoff').forEach(p=>{
      const civ = p.dataset.civ;
      out.civs[civ] = state[civ] || {status:'pending'};
      out.civs[civ].leader = TOKEN_LABELS[civ] || '';
    });
    const blob = new Blob([JSON.stringify(out, null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const stamp = new Date().toISOString().replace(/[:.]/g,'-').slice(0,19);
    a.href = url; a.download = `anw_release_signoff_${stamp}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url), 1000);
  }

  function resetAll(){
    if (!confirm('Reset ALL sign-off state? This clears every checkbox and note for every civ.')) return;
    localStorage.removeItem(STORAGE_KEY);
    document.querySelectorAll('.rr-signoff').forEach(p=> applyToPanel(p, null));
    updateProgress();
    applyFilter();
  }

  function showHelp(){
    let ov = document.querySelector('.rr-help-overlay');
    if (ov){ ov.remove(); return; }
    ov = document.createElement('div');
    ov.className = 'rr-help-overlay';
    ov.innerHTML = `<div>
      <h3>ANW Release Review — keyboard shortcuts</h3>
      <p><kbd>A</kbd> Approve current civ &amp; jump to next pending</p>
      <p><kbd>F</kbd> Flag current civ (requires a note)</p>
      <p><kbd>→</kbd> Next civ &nbsp; <kbd>←</kbd> Previous civ</p>
      <p><kbd>/</kbd> Focus the Jump dropdown</p>
      <p><kbd>?</kbd> Toggle this help</p>
      <p style="color:#9aa0a8;margin-top:14px;">State is saved in your browser. Use <em>Export sign-off JSON</em> to download a final report.</p>
      <button type="button">Close</button>
    </div>`;
    document.body.appendChild(ov);
    ov.addEventListener('click', e => { if (e.target === ov || e.target.tagName === 'BUTTON') ov.remove(); });
  }

  // ── Wire-up ────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', ()=>{
    // Populate jump-to select
    const jump = document.getElementById('rr-jump');
    const cols = Array.from(document.querySelectorAll('section.civ-col'))
      .sort((a,b)=> a.id.localeCompare(b.id));
    cols.forEach(c=>{
      const o = document.createElement('option');
      o.value = c.id;
      o.textContent = c.id.replace(/^ANW/,'') + (TOKEN_LABELS[c.id] ? ` — ${TOKEN_LABELS[c.id]}` : '');
      jump.appendChild(o);
    });
    jump.addEventListener('change', e => {
      const v = e.target.value;
      if (v) scrollToCol(document.getElementById(v));
    });

    // Hydrate panels from localStorage
    const state = loadState();
    document.querySelectorAll('.rr-signoff').forEach(p => applyToPanel(p, state[p.dataset.civ]));

    // Bind panel interactions
    document.querySelectorAll('.rr-signoff').forEach(p=>{
      const civ = p.dataset.civ;
      p.querySelectorAll('input[type="checkbox"]').forEach(cb=>{
        cb.addEventListener('change', ()=>{
          const s = loadState();
          const cur = s[civ] || {checks:{},notes:'',status:'pending'};
          cur.checks = cur.checks || {};
          cur.checks[cb.dataset.check] = cb.checked;
          if (allChecked(cur)) cur.status = 'approved';
          else if (cur.status === 'approved') cur.status = 'pending';
          cur.timestamp = Date.now();
          s[civ] = cur; saveState(s); applyToPanel(p, cur); updateProgress();
        });
      });
      const ta = p.querySelector('textarea[data-role="notes"]');
      if (ta){
        let t=null;
        ta.addEventListener('input', ()=>{
          clearTimeout(t);
          t = setTimeout(()=>{
            const s = loadState();
            const cur = s[civ] || {checks:{},notes:'',status:'pending'};
            cur.notes = ta.value;
            cur.timestamp = Date.now();
            s[civ] = cur; saveState(s);
          }, 250);
        });
      }
      p.querySelector('[data-action="approve"]').addEventListener('click', ()=>{
        // simulate "approve current" against THIS specific panel
        const col = p.closest('section.civ-col');
        scrollToCol(col); approveCurrent();
      });
      p.querySelector('[data-action="flag"]').addEventListener('click', ()=>{
        const col = p.closest('section.civ-col');
        scrollToCol(col); flagCurrent();
      });
      p.querySelector('[data-action="reset"]').addEventListener('click', ()=>{
        if (!confirm('Reset sign-off for ' + civ + '?')) return;
        const s = loadState(); delete s[civ]; saveState(s);
        applyToPanel(p, null); updateProgress();
      });
    });

    // Filter
    const filter = document.getElementById('rr-filter');
    filter.addEventListener('change', applyFilter);
    applyFilter();

    // Top-bar buttons
    document.getElementById('rr-export').addEventListener('click', exportSignoff);
    document.getElementById('rr-reset-all').addEventListener('click', resetAll);

    // Lightbox: clicking any image inside a civ-col opens it fullscreen.
    document.body.addEventListener('click', e=>{
      const img = e.target.closest('section.civ-col img');
      if (img){
        e.preventDefault();
        // Caption = nearest figcaption or img alt, or parent label text.
        let cap = img.alt || '';
        const fig = img.closest('figure');
        if (fig){
          const fc = fig.querySelector('figcaption');
          if (fc) cap = fc.textContent.trim();
        }
        openLightbox(img.src, cap);
      }
    });
    const lb = document.getElementById('rr-lightbox');
    if (lb){
      lb.addEventListener('click', e=>{
        // Click background or × button — close. Click on the image itself — keep open.
        if (e.target === lb || e.target.classList.contains('rr-lightbox-close')){
          closeLightbox();
        }
      });
    }

    // Flagged-panel: floating ⚐ toggles drawer, close button hides it,
    // copy button copies a markdown-ish summary to the clipboard.
    const ft = document.getElementById('rr-flag-toggle');
    if (ft) ft.addEventListener('click', ()=> toggleFlagPanel());
    const fc = document.getElementById('rr-flag-close');
    if (fc) fc.addEventListener('click', ()=> toggleFlagPanel(false));
    const fcp = document.getElementById('rr-flag-copy');
    if (fcp) fcp.addEventListener('click', copyFlaggedSummary);

    // Nav-strip tile click → scroll to col (anchors handle this naturally
    // but we also want to ensure the col gets keyboard focus).
    document.querySelectorAll('.rr-tile').forEach(t=>{
      t.addEventListener('click', e=>{
        const civ = t.dataset.rrTile;
        const col = document.getElementById(civ);
        if (col){
          e.preventDefault();
          scrollToCol(col);
        }
      });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', e=>{
      // Esc closes lightbox / flag panel / help overlay even from inputs.
      if (e.key === 'Escape'){
        const lb = document.getElementById('rr-lightbox');
        if (lb && !lb.hidden){ closeLightbox(); return; }
        const fp = document.getElementById('rr-flag-panel');
        if (fp && !fp.hidden){ toggleFlagPanel(false); return; }
        const ov = document.querySelector('.rr-help-overlay');
        if (ov){ ov.remove(); return; }
      }
      if (e.target.matches('input,textarea,select')) return;
      if (e.key === 'a' || e.key === 'A'){ e.preventDefault(); approveCurrent(); }
      else if (e.key === 'f' || e.key === 'F'){ e.preventDefault(); flagCurrent(); }
      else if (e.key === 'ArrowRight'){ const c = currentColInView(); scrollToCol(nextCiv(c && c.id, +1)); }
      else if (e.key === 'ArrowLeft' ){ const c = currentColInView(); scrollToCol(nextCiv(c && c.id, -1)); }
      else if (e.key === '/'){ e.preventDefault(); document.getElementById('rr-jump').focus(); }
      else if (e.key === '?'){ showHelp(); }
    });

    updateProgress();
  });
})();
</script>
""".strip()


CIV_COL_RE = re.compile(
    r'(<section class="civ-col"[^>]*id="(ANW[A-Za-z]+)"[^>]*>)',
    re.MULTILINE,
)


def main() -> int:
    if not os.path.exists(SRC):
        print(f"ERROR: source HTML missing: {SRC}", file=sys.stderr)
        print("Run `python3 tools/build_civ_columns.py` first.", file=sys.stderr)
        return 1
    html = open(SRC, encoding="utf-8").read()
    dash = load_dashboard()

    # Collect token labels for the jump select.
    token_to_label = {}
    for m in CIV_COL_RE.finditer(html):
        token = m.group(2)
        row = dashboard_row_for(token, dash)
        token_to_label[token] = row.get("leader_label", "")

    # Inject sign-off panel right after each civ-col opening tag.
    def _inject(m):
        opener = m.group(1)
        token = m.group(2)
        row = dashboard_row_for(token, dash)
        return opener + "\n" + signoff_panel_html(token, row)

    new_html, n_replaced = CIV_COL_RE.subn(_inject, html)

    # Inject CSS at end of <head>.
    css_block = f"<style>\n{PORTAL_CSS}\n</style>"
    new_html = new_html.replace("</head>", css_block + "\n</head>", 1)

    # Inject top bar + nav strip right after <body>.
    # Nav strip appears below the topbar (sticky) so tile colours
    # mirror live sign-off state.
    tokens_in_order = [m.group(2) for m in CIV_COL_RE.finditer(html)]
    top_chrome = (
        top_bar_html(dash)
        + "\n"
        + nav_strip_html(tokens_in_order, token_to_label)
    )
    new_html = new_html.replace("<body>", "<body>\n" + top_chrome, 1)

    # Inject lightbox + flagged-civs side panel + JS before </body>.
    tail = (
        lightbox_html()
        + "\n"
        + flagged_panel_html()
        + "\n"
        + portal_js(token_to_label)
    )
    new_html = new_html.replace("</body>", tail + "\n</body>", 1)

    with open(DST, "w", encoding="utf-8") as f:
        f.write(new_html)

    sz_in = len(html)
    sz_out = len(new_html)
    print(f"Sign-off panels injected: {n_replaced}")
    print(f"Source : {SRC}  ({sz_in:,} bytes)")
    print(f"Output : {DST}  ({sz_out:,} bytes, +{sz_out - sz_in:,})")
    print(f"Verdict: {dash['verdict']}")
    print(f"Open the output HTML in a browser to begin sign-off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
