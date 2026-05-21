#!/usr/bin/env python3
"""Build a focused review page for the British civ (most complete in-game
captures, used as the reference for what every civ should look like)."""
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts' / 'validation' / 'visual_art' / 'ANWBritish' / 'full'
OUT = ROOT / 'artifacts' / 'validation' / 'visual_art' / 'british_review.html'

LABELS = {
    '01_lobby.png': 'Lobby — civ picker / flag',
    '02_loading.png': 'Loading screen',
    '03_hud.png': 'In-game HUD (Age 1)',
    '04_homecity_panel.png': 'Home City panel',
    '05_tech_tree.png': 'Tech tree (early game)',
    '06_diplomacy.png': 'Diplomacy screen',
    '06b_ai_homecity_via_diplo.png': 'AI Home City (via Diplomacy)',
    '07_scoreboard_with_banter.png': 'Scoreboard + AI banter',
    '08_esc_menu.png': 'ESC pause menu',
    '09_postgame_results.png': 'Post-game results',
    '10_british_ai_base.png': 'British AI base (overhead)',
    '15_age_up_colonial.png': 'Age 2 — Colonial politician select',
    '16_age_up_fortress.png': 'Age 3 — Fortress politician select',
    '17_age_up_industrial.png': 'Age 4 — Industrial politician select',
    '18_age_up_imperial.png': 'Age 5 — Imperial politician select',
    '19_tech_tree.png': 'Tech tree (late game, all ages unlocked)',
    '20_postgame_awards.png': 'Post-game awards (final tab)',
}

ORDER = list(LABELS.keys())


def main():
    files = sorted([p.name for p in ART.iterdir() if p.is_file()])
    sections = []
    for fname in ORDER:
        if fname not in files:
            continue
        label = LABELS[fname]
        path = f'ANWBritish/full/{fname}'
        size_kb = (ART / fname).stat().st_size // 1024
        sections.append(
            f'<figure class="surface">'
            f'<a href="{path}" target="_blank">'
            f'<img loading="lazy" src="{path}" alt="{html.escape(label)}"></a>'
            f'<figcaption><strong>{html.escape(label)}</strong>'
            f'<br><code>{html.escape(fname)}</code> · {size_kb}KB</figcaption>'
            f'</figure>'
        )

    # Any surfaces in dir but not in our LABELS dict?
    extras = [f for f in files if f not in LABELS]
    for fname in extras:
        path = f'ANWBritish/full/{fname}'
        sections.append(
            f'<figure class="surface">'
            f'<a href="{path}" target="_blank"><img loading="lazy" src="{path}"></a>'
            f'<figcaption><code>{html.escape(fname)}</code> (unlabeled)</figcaption>'
            f'</figure>'
        )

    html_out = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>ANW British — Reference Capture Review</title>
<style>
body {{ background:#1c1410; color:#e6d4ad; font-family:'Georgia',serif;
  margin:0; padding:24px 32px; }}
h1 {{ color:#f0d896; border-bottom:2px solid #8b6a3a; padding-bottom:10px; }}
.subtitle {{ color:#b89a64; font-size:13px; margin-top:-6px; margin-bottom:24px;
  letter-spacing:.1em; text-transform:uppercase; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(560px, 1fr));
  gap:18px; }}
.surface {{ margin:0; background:#2a1d11; border:1px solid #5b4525;
  border-radius:6px; padding:10px; }}
.surface img {{ width:100%; height:auto; display:block; border-radius:3px;
  background:#000; }}
.surface figcaption {{ padding-top:8px; font-size:13px; color:#ddc8a0;
  line-height:1.5; }}
code {{ background:#1c1410; color:#c2a060; padding:1px 5px; border-radius:2px;
  font-size:11px; }}
.meta {{ background:#2e2014; padding:10px 16px; border-radius:4px;
  margin-bottom:18px; font-size:13px; line-height:1.6; }}
.meta strong {{ color:#f0d896; }}
</style></head><body>
<h1>British Empire — Reference Capture Review</h1>
<div class="subtitle">A New World · ANWBritish · {len(sections)} surfaces</div>
<div class="meta">
  This is the <strong>reference civ</strong> — used to verify that the
  orchestrator's pipeline produces correct screenshots before fanning out
  to the other 39 civs.<br>
  Surfaces 15-18 are the politician age-up dialogs.
  Surface 05 / 19 are the tech tree (early vs late game).
  Surfaces 01-10 / 20 are the full pre-/in-/post-game flow.
</div>
<div class="grid">
{''.join(sections)}
</div>
</body></html>
"""
    OUT.write_text(html_out, encoding='utf-8')
    print(f'wrote {OUT}')
    print(f'  surfaces: {len(sections)}')


if __name__ == '__main__':
    main()
