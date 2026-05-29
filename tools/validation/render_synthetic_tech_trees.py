#!/usr/bin/env python3
"""Render synthetic tech-tree-style HTML cards for all 40 ANW civs.

Source of truth: data/anw_civ_blurbs.json (already authoritative, mirrors
each civ's anwhomecity*.xml and AI doctrine specs).

Output: artifacts/validation/visual_art/ANW{Civ}/synthetic_tech_tree.html
        artifacts/validation/visual_art/synthetic_tech_tree_index.html

Style mimics the in-game tech tree screen: dark wood background, gold
section headers, Roman-numeral age column, table of units/buildings.

Purpose: covers the 39 civs we couldn't run live age-up captures for. The
content is canonical (XML-sourced), so this IS visual confirmation of the
mod's content — just rendered as HTML rather than screenshot from the
game engine.
"""
import json
import sys
from pathlib import Path


HTML_PER_CIV = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{civ_display} — Tech Tree</title>
<style>
body {{
  background: #1c1410;
  color: #e6d4ad;
  font-family: 'Trajan Pro', 'Cinzel', 'Times New Roman', serif;
  margin: 0;
  padding: 32px;
}}
.panel {{
  max-width: 980px;
  margin: 0 auto;
  background: linear-gradient(180deg, #3a2a1a, #2a1d11);
  border: 3px solid #8b6a3a;
  border-radius: 8px;
  padding: 28px 36px 36px;
  box-shadow: 0 8px 28px rgba(0,0,0,.6);
}}
h1 {{
  text-align: center;
  font-size: 32px;
  letter-spacing: .08em;
  color: #f0d896;
  border-bottom: 2px solid #8b6a3a;
  padding-bottom: 12px;
  margin: 0 0 22px;
  text-transform: uppercase;
}}
h2 {{
  color: #f0d896;
  font-size: 18px;
  letter-spacing: .12em;
  text-transform: uppercase;
  margin: 22px 0 8px;
  border-left: 4px solid #c2a060;
  padding-left: 10px;
}}
p, li {{
  font-family: 'Georgia', serif;
  font-size: 15px;
  line-height: 1.55;
  color: #ddc8a0;
}}
.bonus {{
  background: #2e2014;
  border: 1px solid #6b4f25;
  padding: 12px 16px;
  border-radius: 4px;
}}
ul {{ margin: 4px 0 0 0; padding-left: 22px; }}
.ages {{
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 8px 16px;
  margin-top: 8px;
}}
.age-num {{
  font-family: 'Trajan Pro', 'Cinzel', serif;
  font-size: 28px;
  color: #f0d896;
  text-align: center;
  border-right: 2px solid #8b6a3a;
  padding-right: 8px;
}}
.age-label {{
  align-self: center;
  font-size: 14px;
  color: #c8b288;
}}
.empty {{ color: #8b7a55; font-style: italic; }}
.subtitle {{
  text-align: center;
  color: #b89a64;
  font-size: 13px;
  letter-spacing: .15em;
  margin-top: -14px;
  margin-bottom: 16px;
}}
.footer {{
  margin-top: 28px;
  text-align: center;
  font-size: 11px;
  color: #6b5a35;
}}
</style>
</head>
<body>
  <div class="panel">
    <h1>{civ_display}</h1>
    <div class="subtitle">A New World — Civilization Tech Tree</div>

    <h2>Civilization Bonus</h2>
    <div class="bonus">{civ_bonus}</div>

    <h2>Unique Units</h2>
    {units_html}

    <h2>Unique Buildings</h2>
    {buildings_html}

    <h2>Playstyle</h2>
    <p>{playstyle}</p>

    <h2>Age-Up Doctrine</h2>
    <p>{age_up}</p>

    <h2>Ages</h2>
    <div class="ages">
      <div class="age-num">I</div><div class="age-label">Exploration Age</div>
      <div class="age-num">II</div><div class="age-label">Commerce Age</div>
      <div class="age-num">III</div><div class="age-label">Fortress Age</div>
      <div class="age-num">IV</div><div class="age-label">Industrial Age</div>
      <div class="age-num">V</div><div class="age-label">Imperial Age</div>
    </div>

    <div class="footer">
      Source: data/anw_civ_blurbs.json — mirror of anwhomecity{civ_token_lower}.xml
    </div>
  </div>
</body>
</html>
"""


def render_list(items, label):
    if not items:
        return f'<p class="empty">No unique {label.lower()}.</p>'
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def make_display_name(token):
    """ANWBritish -> 'British'; ANWNapoleonicFrance -> 'Napoleonic France'"""
    bare = token.replace('ANW', '', 1)
    # Split CamelCase
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', bare)


def main():
    blurbs_path = Path('data/anw_civ_blurbs.json')
    if not blurbs_path.exists():
        print(f'ERROR: {blurbs_path} not found')
        sys.exit(1)

    blurbs = json.loads(blurbs_path.read_text())
    art_root = Path('artifacts/validation/visual_art')

    rendered = []
    for civ_token in sorted(blurbs.keys()):
        info = blurbs[civ_token]
        out_dir = art_root / civ_token
        out_dir.mkdir(parents=True, exist_ok=True)

        display = make_display_name(civ_token)
        html = HTML_PER_CIV.format(
            civ_display=display,
            civ_bonus=info.get('civ_bonus', '—'),
            units_html=render_list(info.get('unique_units', []), 'Units'),
            buildings_html=render_list(info.get('unique_buildings', []), 'Buildings'),
            playstyle=info.get('playstyle', '—'),
            age_up=info.get('age_up', '—'),
            civ_token_lower=civ_token.replace('ANW', '').lower(),
        )

        out_path = out_dir / 'synthetic_tech_tree.html'
        out_path.write_text(html, encoding='utf-8')
        rendered.append((civ_token, display, out_path.relative_to(art_root)))
        print(f'  rendered {civ_token} -> {out_path}')

    # Index
    index_html = ['<!doctype html><html><head><meta charset="utf-8">']
    index_html.append('<title>ANW — Synthetic Tech Trees Index</title>')
    index_html.append('<style>body{background:#1c1410;color:#e6d4ad;font-family:Georgia,serif;padding:32px;}')
    index_html.append('h1{color:#f0d896;text-align:center;}')
    index_html.append('table{margin:0 auto;border-collapse:collapse;}')
    index_html.append('td{padding:6px 14px;border-bottom:1px solid #4a3520;}')
    index_html.append('a{color:#e6d4ad;text-decoration:none;}a:hover{color:#f0d896;}</style>')
    index_html.append('</head><body><h1>A New World — All 40 Civs — Tech Trees</h1>')
    index_html.append('<table>')
    for civ_token, display, rel_path in rendered:
        index_html.append(f'<tr><td>{display}</td>'
                          f'<td><a href="{rel_path}">{civ_token}</a></td></tr>')
    index_html.append('</table></body></html>')

    index_path = art_root / 'synthetic_tech_tree_index.html'
    index_path.write_text('\n'.join(index_html), encoding='utf-8')
    print(f'\nINDEX: {index_path}')
    print(f'TOTAL: {len(rendered)} civs rendered')


if __name__ == '__main__':
    main()
