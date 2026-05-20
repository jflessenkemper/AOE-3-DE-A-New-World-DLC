#!/usr/bin/env python3
"""Build a self-contained HTML contact sheet of every civ's art assets.

Why: in-game capture proved unreliable across batches (picker state drift
after the first OCR-verified pick), so an offline static path is needed
for the user to eyeball every civ's flags + portrait against the HTML
reference.

Inputs:
  - artifacts/validation/civmods_art/findings.json  (per-civ HTML and
    civmods.xml asset paths, plus PASS/NOTE/BLOCKER status)
  - artifacts/validation/dev_tree/dev_tree_findings.json  (per-civ
    development-tree validator status)
  - tools/validation/art_inventory.json  (per-ANW-civ extras incl.
    hi-res leader portrait under art/ui/leaders/)
  - artifacts/validation/visual_art/batch_01_ANWBritish/  (in-game
    sample captures, linked at top of the page)

Output:
  artifacts/validation/visual_art/static_contact_sheet.html

Each civ row shows side-by-side:
  HTML scoreboard flag | civmods homecity flag | civmods postgame flag |
  HTML portrait        | civmods portrait obj  | art/ leader hi-res

Status badges (from findings.json) and missing-on-disk warnings
appear next to each civ. Image src= attributes use repo-relative
paths so the HTML loads correctly when opened from the repo root.

Usage:
    python3 tools/validation/build_art_contact_sheet.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "artifacts" / "validation" / "visual_art"
OUT_HTML = OUT_DIR / "static_contact_sheet.html"

CIVMODS_ART = REPO / "artifacts" / "validation" / "civmods_art" / "findings.json"
DEV_TREE = REPO / "artifacts" / "validation" / "dev_tree" / "dev_tree_findings.json"
ART_INV = REPO / "tools" / "validation" / "art_inventory.json"

# Engine token (used in findings.json) → ANW token (used in art_inventory.json).
# Without this mapping base civs never resolve their `anw_extra` block, so
# they show only the 5 generic flag/portrait cells instead of the full
# 10-cell art-surface row. Source of truth: tools/migration/anw_mapping.py
# `_TOKEN_TO_SLUG` mirrors this for base civs.
ENGINE_TO_ANW_TOKEN: dict[str, str] = {
    "XPAztec":      "ANWAztecs",
    "British":      "ANWBritish",
    "Chinese":      "ANWChinese",
    "Dutch":        "ANWDutch",
    "DEEthiopians": "ANWEthiopians",
    "French":       "ANWFrench",
    "Germans":      "ANWGermans",
    "XPIroquois":   "ANWHaudenosaunee",
    "DEHausa":      "ANWHausa",
    "DEInca":       "ANWInca",
    "Indians":      "ANWIndians",
    "DEItalians":   "ANWItalians",
    "Japanese":     "ANWJapanese",
    "XPSioux":      "ANWLakota",
    "DEMaltese":    "ANWMaltese",
    "DEMexicans":   "ANWMexicans",
    "Ottomans":     "ANWOttomans",
    "Portuguese":   "ANWPortuguese",
    "Russians":     "ANWRussians",
    "Spanish":      "ANWSpanish",
    "DESwedish":    "ANWSwedes",
    "DEAmericans":  "ANWUSA",
}

# Base-civ display-name → engine token, used when findings.json has an empty
# civ_token (the findings BLOCKER row for Sokoto/Maratha/Lakota/Russian).
# Matching by display name lets the contact sheet recover the row by rejoining
# it with art_inventory.json instead of rendering a 2-cell stub.
DISPLAY_TO_ENGINE_TOKEN: dict[str, str] = {
    "Sokoto Caliphate": "DEHausa",
    "Maratha Empire":   "Indians",
    "Lakota Sioux":     "XPSioux",
    "Russian Empire":   "Russians",
}

# In-game samples (the one civ that survived the 4-civ test).
INGAME_SAMPLE_DIR = OUT_DIR / "batch_01_ANWBritish"
INGAME_SAMPLE_LABELS = [
    ("01_lobby.png", "Lobby"),
    ("02_hud_default.png", "HUD"),
    ("03_scoreboard.png", "Scoreboard"),
    ("04_diplomacy.png", "Diplomacy"),
    ("05_homecity_panel.png", "Home City"),
    ("06_esc_menu.png", "ESC menu"),
    ("07_endgame_screen.png", "End game"),
]


def _norm(p: str) -> str:
    """Normalise a path for use in src=. Keeps it repo-relative POSIX."""
    if not p:
        return ""
    return p.replace("\\", "/").lstrip("./")


def _file_status(rel: str) -> tuple[bool, int]:
    """Return (exists, size_bytes) for a repo-relative path."""
    if not rel:
        return False, 0
    fp = REPO / rel
    if fp.exists() and fp.is_file():
        return True, fp.stat().st_size
    return False, 0


def _badge(text: str, kind: str) -> str:
    """Colour-coded inline span. kind in {ok, warn, fail, info}."""
    colours = {
        "ok": "#1f7a1f",
        "warn": "#a06a00",
        "fail": "#a01010",
        "info": "#404a8a",
    }
    bg = {
        "ok": "#e6f5e6",
        "warn": "#fff3d6",
        "fail": "#fde0e0",
        "info": "#e3e8fb",
    }
    return (
        f'<span style="display:inline-block;padding:2px 6px;margin:0 4px 2px 0;'
        f'border-radius:3px;font-size:11px;color:{colours[kind]};'
        f'background:{bg[kind]};border:1px solid {colours[kind]};">'
        f"{html.escape(text)}</span>"
    )


def _img_cell(rel_path: str, label: str, *, is_engine_slug: bool = False) -> str:
    """One image tile. Falls back to a placeholder if missing.

    If ``is_engine_slug`` is True, the value is a folder/object slug the
    engine resolves at runtime (e.g. ``objects/flags/argentinian``) — it is
    NOT expected to exist as a file on disk, so we skip the MISSING flag.
    """
    rel = _norm(rel_path)
    exists, size = _file_status(rel)
    if is_engine_slug:
        # Render as a text label only — no image, no MISSING badge.
        return (
            '<div style="display:inline-block;margin:4px;vertical-align:top;'
            'width:148px;">'
            '<div style="width:140px;height:90px;background:#3a3a4f;color:#cfd3e8;'
            'display:flex;align-items:center;justify-content:center;'
            'font-size:11px;text-align:center;padding:4px;border:1px solid #555;">'
            "engine slug<br>(runtime-resolved)</div>"
            f'<div style="font-size:11px;line-height:1.3;margin-top:3px;">'
            f"{html.escape(label)}<br>"
            f'<code style="font-size:10px;color:#444;">{html.escape(rel) if rel else "—"}</code>'
            "</div></div>"
        )
    # Compute relative href from OUT_HTML's parent (artifacts/validation/visual_art/)
    # back to repo root so file:// loads work.
    if rel:
        # OUT_HTML lives 3 levels deep from REPO; go up 3.
        href = "../../../" + rel
    else:
        href = ""
    cap_lines = [html.escape(label)]
    if rel:
        cap_lines.append(f'<span style="font-size:10px;color:#666;">{html.escape(rel)}</span>')
    if exists:
        cap_lines.append(f'<span style="font-size:10px;color:#1f7a1f;">{size:,} B</span>')
    elif rel:
        cap_lines.append(
            '<span style="font-size:10px;color:#a01010;">MISSING ON DISK</span>'
        )
    else:
        cap_lines.append('<span style="font-size:10px;color:#888;">— not set —</span>')

    img_html = ""
    if exists and rel.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
        img_html = (
            f'<img src="{html.escape(href)}" loading="lazy" '
            f'style="max-width:140px;max-height:140px;background:#222;'
            f'border:1px solid #555;display:block;">'
        )
    elif rel:
        img_html = (
            f'<div style="width:140px;height:90px;background:#444;color:#bbb;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:10px;text-align:center;padding:4px;">'
            f"{html.escape(Path(rel).suffix or 'no-ext')}<br>(non-image)</div>"
        )
    else:
        img_html = (
            '<div style="width:140px;height:90px;background:#333;color:#888;'
            'display:flex;align-items:center;justify-content:center;'
            'font-size:11px;">(no asset)</div>'
        )

    return (
        '<div style="display:inline-block;margin:4px;vertical-align:top;'
        'width:148px;">'
        f"{img_html}"
        f'<div style="font-size:11px;line-height:1.3;margin-top:3px;">'
        + "<br>".join(cap_lines)
        + "</div></div>"
    )


def _art_surface_cell(surface: dict | None, label: str) -> str:
    """Track 2 cell with PASS / MISSING / TOO-SMALL badge.

    Surface dict shape: {"path": "<repo-rel>", "_on_disk": bool}.
    None surface (civ has no override for this slot) renders a neutral
    "no override" placeholder — not a failure.
    """
    SMALL_BYTES = 1024  # 1 KB threshold for "suspicious"
    if not surface:
        rel = ""
        on_disk = False
        size = 0
    else:
        rel = _norm(surface.get("path", "") or "")
        on_disk = bool(surface.get("_on_disk"))
        size = 0
        if rel:
            fp = REPO / rel
            if fp.exists() and fp.is_file():
                size = fp.stat().st_size

    # Choose badge
    if not rel:
        badge_html = _badge("no override", "info")
    elif not on_disk:
        badge_html = '<span style="color:#a01010;font-weight:600;">' \
                     '\u274c MISSING</span>'
    elif size and size < SMALL_BYTES:
        badge_html = '<span style="color:#a06a00;font-weight:600;">' \
                     f'\u26a0 SMALL ({size} B)</span>'
    else:
        badge_html = '<span style="color:#1f7a1f;font-weight:600;">' \
                     f'\u2713 OK ({size:,} B)</span>'

    href = ("../../../" + rel) if rel else ""
    img_html = ""
    if rel and on_disk and rel.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
        img_html = (
            f'<img src="{html.escape(href)}" loading="lazy" '
            f'style="max-width:160px;max-height:160px;background:#222;'
            f'border:1px solid #555;display:block;">'
        )
    elif rel:
        img_html = (
            '<div style="width:160px;height:100px;background:#3a2020;'
            'color:#fbb;display:flex;align-items:center;justify-content:center;'
            'font-size:11px;text-align:center;padding:4px;">'
            "asset missing on disk</div>"
        )
    else:
        img_html = (
            '<div style="width:160px;height:100px;background:#2a2a3a;'
            'color:#aab;display:flex;align-items:center;justify-content:center;'
            'font-size:11px;">(no override — uses base civ)</div>'
        )

    return (
        '<div style="display:inline-block;margin:4px;vertical-align:top;'
        'width:168px;border:1px dashed #99a;padding:2px;background:#fcfcff;">'
        f"{img_html}"
        f'<div style="font-size:11px;line-height:1.3;margin-top:3px;">'
        f'<b>{html.escape(label)}</b><br>'
        f'{badge_html}<br>'
        f'<code style="font-size:10px;color:#555;">{html.escape(rel) if rel else "—"}</code>'
        "</div></div>"
    )


def _capture_cell(capture: dict | None, label: str) -> str:
    """Cell for an in-game screenshot captured by anw_visual_capture.py.

    Capture dict shape: {"path": "<repo-rel>", "_on_disk": bool}.
    Shows the screenshot thumbnail if the file exists, otherwise a
    "MISSING — run anw_visual_capture.py" placeholder (not a blocker).
    """
    if not capture:
        rel = ""
        on_disk = False
    else:
        rel = _norm(capture.get("path", "") or "")
        on_disk = bool(capture.get("_on_disk"))

    href = ("../../../" + rel) if rel else ""

    if on_disk:
        fp = REPO / rel
        size = fp.stat().st_size if fp.exists() else 0
        badge_html = (
            f'<span style="color:#1f7a1f;font-weight:600;">'
            f"\u2713 captured ({size:,} B)</span>"
        )
        img_html = (
            f'<img src="{html.escape(href)}" loading="lazy" '
            f'style="max-width:160px;max-height:160px;background:#111;'
            f'border:1px solid #555;display:block;">'
        )
    elif rel:
        badge_html = (
            '<span style="color:#888;font-weight:600;">'
            "MISSING — run anw_visual_capture.py</span>"
        )
        img_html = (
            '<div style="width:160px;height:100px;background:#2a2a2a;'
            'color:#888;display:flex;align-items:center;justify-content:center;'
            'font-size:10px;text-align:center;padding:4px;">'
            "not yet captured</div>"
        )
    else:
        badge_html = (
            '<span style="color:#888;">— no path —</span>'
        )
        img_html = (
            '<div style="width:160px;height:100px;background:#2a2a2a;'
            'color:#888;display:flex;align-items:center;justify-content:center;'
            'font-size:11px;">(no capture path)</div>'
        )

    return (
        '<div style="display:inline-block;margin:4px;vertical-align:top;'
        'width:168px;border:1px dashed #7a9a7a;padding:2px;background:#f6faf6;">'
        f"{img_html}"
        f'<div style="font-size:11px;line-height:1.3;margin-top:3px;">'
        f'<b>{html.escape(label)}</b><br>'
        f'{badge_html}<br>'
        f'<code style="font-size:10px;color:#555;">{html.escape(rel) if rel else "—"}</code>'
        "</div></div>"
    )


def _readiness_banner(records: list[dict], inv_civs: dict[str, dict]) -> str:
    """Top banner summarizing custom-portrait and flag readiness across ANW civs.

    Surfaces classified as "engine-internal" (resolved from the game's own
    data.bar archives rather than mod-relative paths) are excluded from the
    PASS check — they never appear on the mod filesystem by design.
    """
    # Surfaces the engine resolves internally (data.bar / vanilla assets) —
    # not expected to be on the mod filesystem even when the ANW civ
    # references them. Skip these from the PASS criteria.
    ENGINE_INTERNAL_SURFACES = {
        "homecity_visual_scene",  # engine-shipped HC scene (e.g. british/british_homecity.xml)
    }
    anw_civs = [c for c in inv_civs if c.startswith("ANW")]
    total = len(anw_civs)
    portrait_missing: list[str] = []
    flag_missing: list[str] = []
    pass_civs: list[str] = []
    for civ in anw_civs:
        rec = inv_civs[civ]
        surfaces = rec.get("art_surfaces") or {}
        # "missing portrait" = custom_leader_portrait_hires referenced but not on disk.
        # An empty path means the civ doesn't define a hi-res variant — that's fine,
        # the diplomacy/scoreboard DDTs in art/ui/singleplayer/ already serve as the
        # primary portrait surface for that civ.
        cph = surfaces.get("custom_leader_portrait_hires") or {}
        if cph.get("path") and not cph.get("_on_disk"):
            portrait_missing.append(civ)
        # "missing flag" = postgame_flag_wpf referenced but not on disk
        # (a civ with no override doesn't count as missing — base civ provides it)
        pg = surfaces.get("postgame_flag_wpf") or {}
        if pg.get("path") and not pg.get("_on_disk"):
            flag_missing.append(civ)
        hcf = surfaces.get("homecity_flag_icon_wpf") or {}
        if hcf.get("path") and not hcf.get("_on_disk"):
            if civ not in flag_missing:
                flag_missing.append(civ)
        # PASS if every mod-resolved surface that defines a path is on disk.
        # Engine-internal surfaces (homecity_visual_scene etc.) are excluded —
        # the engine provides them from its own data.bar, not the mod.
        all_ok = True
        for sname, s in surfaces.items():
            if sname in ENGINE_INTERNAL_SURFACES:
                continue
            if s.get("path") and not s.get("_on_disk"):
                all_ok = False
                break
        if all_ok:
            pass_civs.append(civ)

    return (
        '<section style="border:2px solid #2a6;border-radius:8px;'
        'margin:8px 0 14px 0;padding:12px;background:#eafbef;">'
        '<h2 style="margin:0 0 6px 0;color:#194;font-size:18px;">'
        "Release Readiness — Custom Art Surface Status</h2>"
        f'<div style="font-size:14px;color:#234;">'
        f'<b>{len(pass_civs)} / {total}</b> ANW civs PASS '
        f'(all referenced art surfaces present on disk &amp; have a custom leader). &nbsp;'
        f'<b>{len(portrait_missing)}</b> civs have no matching '
        f'<code>art/ui/leaders/&lt;leader&gt;.{{png,jpg}}</code> file. &nbsp;'
        f'<b>{len(flag_missing)}</b> civs reference a flag asset that is missing on disk.'
        "</div>"
        '<details style="margin-top:8px;font-size:12px;"><summary style="cursor:pointer;color:#345;">'
        "Show per-civ lists</summary>"
        f'<div style="margin-top:6px;"><b>Custom-portrait missing ({len(portrait_missing)}):</b> '
        f"<code>{html.escape(', '.join(portrait_missing) or '—')}</code></div>"
        f'<div style="margin-top:4px;"><b>Flag missing ({len(flag_missing)}):</b> '
        f"<code>{html.escape(', '.join(flag_missing) or '—')}</code></div>"
        f'<div style="margin-top:4px;"><b>PASS ({len(pass_civs)}):</b> '
        f"<code>{html.escape(', '.join(pass_civs) or '—')}</code></div>"
        "</details></section>"
    )


def _civ_row(rec: dict, anw_extra: dict | None) -> str:
    """Render one civ block."""
    token = rec["civ_token"]
    display = rec.get("civ_display", token)
    data_name = rec.get("data_name", "")
    ok = rec.get("ok", True)
    findings = rec.get("findings", []) or []

    # Status badges
    badges_html = ""
    if ok:
        badges_html = _badge("PASS", "ok")
    else:
        sev_counts: dict[str, int] = {}
        for f in findings:
            sev_counts[f.get("severity", "?")] = sev_counts.get(f.get("severity", "?"), 0) + 1
        for sev, count in sev_counts.items():
            kind = "fail" if sev in ("BLOCKER", "MAJOR") else "warn"
            badges_html += _badge(f"{sev}×{count}", kind)

    # Findings detail
    findings_html = ""
    if findings:
        items = []
        for f in findings:
            sev = html.escape(f.get("severity", "?"))
            cat = html.escape(f.get("category", ""))
            msg = html.escape(f.get("message", ""))
            items.append(f"<li><b>{sev}</b> [{cat}] — {msg}</li>")
        findings_html = (
            '<ul style="margin:6px 0 0 24px;padding:0;font-size:12px;color:#600;">'
            + "".join(items)
            + "</ul>"
        )

    # Image cells
    cells = []
    cells.append(_img_cell(rec.get("html_scoreboard_flag", ""), "HTML scoreboard flag"))
    cells.append(_img_cell(rec.get("xml_homecity_flag", ""), "civmods homecity flag"))
    cells.append(_img_cell(rec.get("xml_postgame_flag", ""), "civmods postgame flag"))
    cells.append(_img_cell(rec.get("html_portrait", ""), "HTML portrait (avatar)"))

    # civmods <portrait> entries are folder slugs (objects/flags/<slug>) — non-image.
    cells.append(_img_cell(rec.get("xml_portrait", ""), "civmods portrait slug",
                           is_engine_slug=True))

    # ANW-only: hi-res leader if present
    if anw_extra:
        cells.append(_img_cell(anw_extra.get("art_portrait_hires", ""), "art/ hi-res leader"))
        cells.append(_img_cell(anw_extra.get("html_flag", ""), "inv html_flag"))

        # ---- Track 2: four new art-surface columns ----
        surfaces = anw_extra.get("art_surfaces") or {}
        cells.append(_art_surface_cell(
            surfaces.get("diplomacy_portrait_wpf"), "Diplomacy Portrait"))
        cells.append(_art_surface_cell(
            surfaces.get("scoreboard_portrait_wpf"), "Scoreboard Portrait"))
        cells.append(_art_surface_cell(
            surfaces.get("postgame_flag_wpf"), "Post-game Flag"))
        cells.append(_art_surface_cell(
            surfaces.get("custom_leader_portrait_hires"),
            "Custom Leader (hi-res)"))

        # ---- Track 2 capture columns: in-game screenshots ----
        # These are written by anw_visual_capture.py into
        # artifacts/validation/visual_art/<civ>/0N_*.png.
        # They show "MISSING" until the user has run the capture for this civ.
        captures = anw_extra.get("captured_screenshots") or {}
        cells.append(_capture_cell(
            captures.get("diplomacy_panel"), "diplomacy_panel"))
        cells.append(_capture_cell(
            captures.get("scoreboard_portrait"), "scoreboard_portrait"))
        cells.append(_capture_cell(
            captures.get("postgame_flag"), "postgame_flag"))
        cells.append(_capture_cell(
            captures.get("home_city_walking_animation_thumbnail"),
            "home_city_walking_animation_thumbnail"))

    # Quick consistency check: HTML flag vs civmods homecity flag
    consistency = []
    h_flag = _norm(rec.get("html_scoreboard_flag", ""))
    c_flag = _norm(rec.get("xml_homecity_flag", ""))
    if h_flag and c_flag:
        if h_flag == c_flag:
            consistency.append(_badge("flag: HTML==civmods", "ok"))
        else:
            consistency.append(_badge("flag: HTML≠civmods", "warn"))
    h_pg = _norm(rec.get("html_player_summary_flag", ""))
    c_pg = _norm(rec.get("xml_postgame_flag", ""))
    if h_pg and c_pg:
        if h_pg == c_pg:
            consistency.append(_badge("postgame: HTML==civmods", "ok"))
        else:
            consistency.append(_badge("postgame: HTML≠civmods", "warn"))

    return (
        f'<section style="border:1px solid #aaa;border-radius:6px;'
        f"margin:12px 0;padding:10px;background:#fafafa;\">"
        f'<header style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
        f'<h2 style="margin:0;font-size:18px;">{html.escape(display)}</h2>'
        f'<code style="font-size:13px;color:#444;">{html.escape(token)}</code>'
        f'<span style="font-size:12px;color:#666;">{html.escape(data_name)}</span>'
        f'<span style="margin-left:auto;">{badges_html}</span>'
        f"</header>"
        f'<div style="margin-top:6px;">{"".join(consistency)}</div>'
        f'<div style="margin-top:8px;white-space:nowrap;overflow-x:auto;">'
        + "".join(cells)
        + "</div>"
        + findings_html
        + "</section>"
    )


def _ingame_panel() -> str:
    """Top panel: in-game captures from the surviving British batch."""
    if not INGAME_SAMPLE_DIR.exists():
        return ""
    cells = []
    for fname, label in INGAME_SAMPLE_LABELS:
        p = INGAME_SAMPLE_DIR / fname
        if not p.exists():
            continue
        # OUT_HTML is in same dir as INGAME_SAMPLE_DIR, so href is relative.
        href = f"batch_01_ANWBritish/{fname}"
        size = p.stat().st_size
        cells.append(
            '<div style="display:inline-block;margin:4px;vertical-align:top;width:200px;">'
            f'<a href="{html.escape(href)}" target="_blank">'
            f'<img src="{html.escape(href)}" loading="lazy" '
            f'style="max-width:200px;max-height:140px;background:#222;'
            f'border:1px solid #555;display:block;"></a>'
            f'<div style="font-size:11px;margin-top:3px;">{html.escape(label)}<br>'
            f'<span style="color:#666;font-size:10px;">{size:,} B</span></div>'
            "</div>"
        )
    if not cells:
        return ""
    return (
        '<section style="border:1px solid #4a6fa5;border-radius:6px;'
        'margin:12px 0;padding:10px;background:#eef3fb;">'
        '<h2 style="margin:0 0 6px 0;font-size:16px;color:#26467a;">'
        "In-game capture sample — ANWBritish (only civ that survived the 4-civ batch test)"
        "</h2>"
        '<p style="font-size:12px;margin:0 0 8px 0;color:#345;">'
        "Click any tile to view full-size. The remaining civs use the static "
        "asset comparison below — in-game capture proved unreliable past "
        "the first picker selection (state drift after first OCR-verified pick)."
        "</p>"
        '<div style="white-space:nowrap;overflow-x:auto;">'
        + "".join(cells)
        + "</div></section>"
    )


def _summary_table(records: list[dict]) -> str:
    """Top summary stats."""
    total = len(records)
    pass_count = sum(1 for r in records if r.get("ok"))
    fail_count = total - pass_count
    blocker_count = sum(
        1 for r in records
        for f in (r.get("findings") or [])
        if f.get("severity") == "BLOCKER"
    )
    major_count = sum(
        1 for r in records
        for f in (r.get("findings") or [])
        if f.get("severity") == "MAJOR"
    )
    note_count = sum(
        1 for r in records
        for f in (r.get("findings") or [])
        if f.get("severity") == "NOTE"
    )
    # File presence
    missing_files: list[tuple[str, str, str]] = []
    for r in records:
        for key in ("html_scoreboard_flag", "html_portrait", "xml_homecity_flag",
                    "xml_postgame_flag"):
            rel = _norm(r.get(key, ""))
            if rel:
                exists, _ = _file_status(rel)
                if not exists:
                    missing_files.append((r["civ_token"], key, rel))

    parts = [
        f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:14px;">',
        f"<div><b>Total civs:</b> {total}</div>",
        f"<div>{_badge(f'PASS {pass_count}', 'ok')}</div>",
        f"<div>{_badge(f'FAIL {fail_count}', 'fail' if fail_count else 'ok')}</div>",
        f"<div>{_badge(f'BLOCKER ×{blocker_count}', 'fail' if blocker_count else 'ok')}</div>",
        f"<div>{_badge(f'MAJOR ×{major_count}', 'warn' if major_count else 'ok')}</div>",
        f"<div>{_badge(f'NOTE ×{note_count}', 'info')}</div>",
        f"<div>{_badge(f'Missing files: {len(missing_files)}', 'fail' if missing_files else 'ok')}</div>",
        "</div>",
    ]
    if missing_files:
        rows = "".join(
            f"<tr><td><code>{html.escape(t)}</code></td>"
            f"<td>{html.escape(k)}</td>"
            f"<td><code>{html.escape(p)}</code></td></tr>"
            for t, k, p in missing_files
        )
        parts.append(
            '<details style="margin-top:8px;"><summary style="cursor:pointer;'
            'color:#a01010;">Show missing file paths</summary>'
            '<table style="border-collapse:collapse;font-size:12px;margin-top:6px;">'
            "<thead><tr style=\"background:#eee;\"><th style=\"padding:4px 8px;text-align:left;\">civ</th>"
            "<th style=\"padding:4px 8px;text-align:left;\">field</th>"
            "<th style=\"padding:4px 8px;text-align:left;\">path</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></details>"
        )
    return "".join(parts)


def main() -> int:
    civmods_records = json.loads(CIVMODS_ART.read_text(encoding="utf-8"))
    dev_tree_records = json.loads(DEV_TREE.read_text(encoding="utf-8"))
    inv = json.loads(ART_INV.read_text(encoding="utf-8")) if ART_INV.exists() else {"civs": {}}
    inv_civs: dict[str, dict] = inv.get("civs", {})

    # Index dev_tree by token for quick lookup; merge findings into the main list
    # by appending dev-tree findings to each record's findings[].
    dev_by_token = {r["civ_token"]: r for r in dev_tree_records}
    for rec in civmods_records:
        dev_rec = dev_by_token.get(rec["civ_token"])
        if dev_rec and dev_rec.get("findings"):
            tagged = [{**f, "category": f"devtree:{f.get('category', '')}"}
                      for f in dev_rec["findings"]]
            rec["findings"] = (rec.get("findings") or []) + tagged
            if not dev_rec.get("ok"):
                rec["ok"] = False

    # Synthesise stub records for any ANW civ present in the inventory but
    # missing from civmods_records (e.g. when validate_civmods_art.py
    # couldn't parse the HTML and shipped a stale findings.json). This
    # guarantees the contact sheet renders one section per ANW civ.
    rendered_anw_tokens: set[str] = set()
    for r in civmods_records:
        t = r.get("civ_token", "") or DISPLAY_TO_ENGINE_TOKEN.get(
            r.get("civ_display", ""), "")
        anw = ENGINE_TO_ANW_TOKEN.get(t, t)
        if anw.startswith("ANW"):
            rendered_anw_tokens.add(anw)
    for anw_civ, inv_rec in inv_civs.items():
        if not anw_civ.startswith("ANW"):
            continue
        if anw_civ in rendered_anw_tokens:
            continue
        # Synthesise a minimal record so the civ appears in the sheet.
        civmods_records.append({
            "civ_token": anw_civ,
            "civ_display": inv_rec.get("display_name", anw_civ),
            "data_name": anw_civ,
            "ok": True,
            "findings": [],
        })

    # Sort: failures first (BLOCKER > MAJOR > NOTE > PASS), then alphabetical.
    def _sort_key(r: dict):
        sevs = {f.get("severity") for f in (r.get("findings") or [])}
        rank = 0
        if "BLOCKER" in sevs:
            rank = 0
        elif "MAJOR" in sevs:
            rank = 1
        elif r.get("findings"):
            rank = 2
        else:
            rank = 3
        return (rank, r["civ_token"])

    civmods_records.sort(key=_sort_key)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    parts = [
        "<!doctype html>",
        '<html><head><meta charset="utf-8">',
        "<title>ANW art contact sheet</title>",
        '<style>body{font-family:system-ui,-apple-system,sans-serif;'
        "margin:20px;color:#222;background:#fff;max-width:1600px;}"
        "h1{margin:0 0 8px 0;}h2{font-weight:600;}"
        "code{font-family:Menlo,Consolas,monospace;}"
        "section img{transition:transform .15s;}"
        "section img:hover{transform:scale(1.4);position:relative;z-index:5;}"
        "</style></head><body>",
        '<h1>A New World — art contact sheet</h1>',
        '<p style="color:#555;font-size:13px;">'
        "Static cross-check of every civ's flag and portrait paths "
        "from <code>a_new_world.html</code> vs <code>data/civmods.xml</code>, "
        "with on-disk file presence and dev-tree validator status. "
        "Hover an image to magnify."
        "</p>",
        _readiness_banner(civmods_records, inv_civs),
        _summary_table(civmods_records),
        _ingame_panel(),
    ]

    for rec in civmods_records:
        token = rec.get("civ_token", "")
        # Recover empty-token findings rows by display-name → engine-token.
        if not token:
            token = DISPLAY_TO_ENGINE_TOKEN.get(rec.get("civ_display", ""), "")
            if token:
                rec["civ_token"] = token
        # Resolve to ANW token for inv lookup; engine tokens are mapped here,
        # ANW tokens (e.g. ANWArgentines) fall through unchanged.
        anw_token = ENGINE_TO_ANW_TOKEN.get(token, token)
        anw_extra = inv_civs.get(anw_token)
        parts.append(_civ_row(rec, anw_extra))

    parts.append("</body></html>")

    OUT_HTML.write_text("\n".join(parts), encoding="utf-8")
    size = OUT_HTML.stat().st_size
    print(f"wrote {OUT_HTML.relative_to(REPO)}  ({size:,} bytes, {len(civmods_records)} civs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
