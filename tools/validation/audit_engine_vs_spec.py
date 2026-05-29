#!/usr/bin/env python3
"""Cross-check engine wall_strategy assignments vs playstyle_spec.json claims.

Reads:
  game/ai/aiHeader.xs               — wall strategy enum (cLLWallStrategy*)
  game/ai/leaders/leaderCommon.xs   — llUse*Style functions + per-civ dispatch
  game/ai/leaders/leader_*.xs       — per-leader init style call
  game/ai/leaders/leader_revolution_commanders.xs — per-ANW commander dispatch
  playstyle_spec.json               — authoritative claims per data_name

Reports any data_name whose engine-resolved wall_strategy differs from the
spec claim. Comments are stripped before scanning so commented-out style
references inside docstrings don't produce false positives.

Usage:
  python3 tools/validation/audit_engine_vs_spec.py
"""
from __future__ import annotations
import json
import re
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

ENUM = {
    'FortressRing': 0, 'ChokepointSegments': 1, 'CoastalBatteries': 2,
    'FrontierPalisades': 3, 'UrbanBarricade': 4, 'MobileNoWalls': 5,
}
WS_NAME = {v: k for k, v in ENUM.items()}


def strip_comments(src: str) -> str:
    """Strip C++-style // line comments. Preserves line numbers (replaces with empty)."""
    return re.sub(r'//[^\n]*', '', src)


def load_style_to_ws(common_path: pathlib.Path) -> dict[str, int]:
    """For each `void llUse<X>Style(...)` body, find the gLLWallStrategy assignment."""
    src = strip_comments(common_path.read_text())
    out: dict[str, int] = {}
    pat = re.compile(
        r'void (llUse\w+Style)\(.*?\)\s*\{[^}]*?gLLWallStrategy\s*=\s*cLLWallStrategy(\w+)',
        re.DOTALL,
    )
    for m in pat.finditer(src):
        out[m.group(1)] = ENUM.get(m.group(2), -1)
    return out


WALL_OVERRIDE_RX = re.compile(r'gLLWallStrategy\s*=\s*cLLWallStrategy(\w+)\s*;')


def load_leader_file_style(leaders_dir: pathlib.Path) -> dict[str, tuple[str, int | None]]:
    """leader_<token>.xs -> (llUse*Style call, effective_wall_strategy_int or None).

    If a gLLWallStrategy = cLLWallStrategy<X>; assignment appears AFTER the
    last style-helper call in the file, that override value is used as the
    effective wall_strategy instead of the helper's default.  The caller still
    looks up the helper default from style_ws; we store the override (if any)
    so infer_engine_ws can apply it.
    """
    out: dict[str, tuple[str, int | None]] = {}
    for p in leaders_dir.glob('leader_*.xs'):
        if 'revolution' in p.stem:
            continue
        txt = strip_comments(p.read_text())
        call_matches = list(re.finditer(r'(llUse\w+Style)\s*\(', txt))
        if not call_matches:
            continue
        style = call_matches[-1].group(1)
        # Check for a post-helper gLLWallStrategy override.
        post_text = txt[call_matches[-1].end():]
        wall_overrides = WALL_OVERRIDE_RX.findall(post_text)
        ws_override: int | None = None
        if wall_overrides:
            ws_override = ENUM.get(wall_overrides[-1])
        out[p.stem] = (style, ws_override)
    return out


def _extract_block(src: str, open_pos: int) -> str:
    """Return the text of the brace-delimited block starting at open_pos (the '{').

    Walks forward counting braces to find the matching closing '}', then
    returns the text between them (exclusive of the outer braces).
    """
    depth = 0
    i = open_pos
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[open_pos + 1:i]
        i += 1
    # Unclosed block — return what we have.
    return src[open_pos + 1:]


def load_revolution_dispatch(rev_path: pathlib.Path) -> dict[str, tuple[str, int | None]]:
    """ANW<civ> or ANW<civ> -> (llUse*Style call, wall_override_int or None).

    For each `if (rvltName == "ANWXxx")` block, extracts the exact
    brace-delimited block text (no bleed into sibling blocks), finds the
    llUse*Style call, then checks for a gLLWallStrategy override AFTER that
    call within the same block.
    """
    src = strip_comments(rev_path.read_text())
    out: dict[str, tuple[str, int | None]] = {}
    # ANW renamed revolution dispatch keys; accept both legacy and current prefixes.
    for m in re.finditer(r'rvltName\s*==\s*"((?:ANW|ANW)\w+)"[^{]*(\{)', src):
        brace_pos = m.start(2)
        block = _extract_block(src, brace_pos)
        s = re.search(r'(llUse\w+Style)\s*\(', block)
        if not s:
            continue
        style = s.group(1)
        # Scan the text AFTER the helper call within this block for an override.
        post_block = block[s.end():]
        wall_overrides = WALL_OVERRIDE_RX.findall(post_block)
        ws_override: int | None = None
        if wall_overrides:
            ws_override = ENUM.get(wall_overrides[-1])
        out[m.group(1)] = (style, ws_override)
    return out


def load_civ_dispatch(common_path: pathlib.Path) -> dict[str, tuple[str, int | None]]:
    """leaderCommon.xs `cMyCiv == cCiv<X>` branch -> (first llUse*Style call, override_ws or None).

    Mirrors load_leader_file_style / load_revolution_dispatch: scans for a
    gLLWallStrategy override that appears AFTER the helper call inside the
    same `cMyCiv == cCiv<X>` block. This is required because civs like
    cCivRussians intentionally call `llUseCossackVoiskoStyle(1)` (helper
    default = FortressRing) then immediately override to FrontierPalisades.
    Without honouring this, the audit produces spurious mismatches.
    """
    src = strip_comments(common_path.read_text())
    out: dict[str, tuple[str, int | None]] = {}
    # Find each `cMyCiv == cCiv<X>` block start, then walk the brace block.
    for m in re.finditer(r'cMyCiv\s*==\s*cCiv(\w+)[^{]*?(\{)', src):
        token = m.group(1)
        block = _extract_block(src, m.start(2))
        s = re.search(r'(llUse\w+Style)\s*\(', block)
        if not s:
            continue
        style = s.group(1)
        post_block = block[s.end():]
        wall_overrides = WALL_OVERRIDE_RX.findall(post_block)
        ws_override: int | None = None
        if wall_overrides:
            ws_override = ENUM.get(wall_overrides[-1])
        out[token] = (style, ws_override)
    return out


# civ_label -> cCiv* token used in leaderCommon.xs dispatch (when not
# already a substring match). Engine uses legacy/expansion prefixes that
# don't follow the human civ name.
CIV_TOKEN_ALIAS = {
    'Lakota': 'XPSioux',
    'Haudenosaunee': 'XPIroquois',
    'Aztecs': 'XPAztec',
    'Revolutionary France': 'RevFrance',
    # Spec uses "French Republic" as the civ_label for Robespierre, but the
    # engine dispatch key is `ANW*/ANW*RevFrance`. Bind the human label
    # to the engine token so the audit resolves the correct dispatch block.
    'French Republic': 'RevFrance',
}


def infer_engine_ws(data_name: str, civ_label: str, leader_to_style, rvlt_style,
                    civ_dispatch, style_ws):
    """Return (engine_ws_int, style_name, source_tag) or (None, None, None).

    For leader files and revolution dispatch blocks, if a post-helper
    gLLWallStrategy override was recorded the override value supersedes the
    style helper's default (same logic as validate_leader_vs_spec.py).
    """
    norm = data_name.lower().replace(' ', '_')
    for stem, (style, ws_override) in leader_to_style.items():
        token = stem.replace('leader_', '')
        if token in norm:
            effective_ws = ws_override if ws_override is not None else style_ws.get(style)
            label = style if ws_override is None else f'{style}+wall_override'
            return effective_ws, label, f'leader_file:{stem}'
    cl_compact = civ_label.replace(' ', '').replace('-', '')
    # ANW renamed revolution dispatch keys from `ANW*` to `ANW*`. Try both.
    # Also consult CIV_TOKEN_ALIAS so e.g. "Revolutionary France" -> "RevFrance".
    compact_candidates = [cl_compact]
    if civ_label in CIV_TOKEN_ALIAS:
        compact_candidates.append(CIV_TOKEN_ALIAS[civ_label])
    for prefix in ('ANW', 'ANW'):
        for cand in compact_candidates:
            rvlt_key = prefix + cand
            if rvlt_key in rvlt_style:
                st, ws_override = rvlt_style[rvlt_key]
                effective_ws = ws_override if ws_override is not None else style_ws.get(st)
                label = st if ws_override is None else f'{st}+wall_override'
                return effective_ws, label, f'rev:{rvlt_key}'
    # Base civ dispatch with alias fallback for civ_label -> engine token mismatch.
    candidates = [cl_compact]
    if civ_label in CIV_TOKEN_ALIAS:
        candidates.append(CIV_TOKEN_ALIAS[civ_label])
    for cand in candidates:
        for ck, entry in civ_dispatch.items():
            st, ws_override = entry
            if cand.lower() in ck.lower():
                effective_ws = ws_override if ws_override is not None else style_ws.get(st)
                label = st if ws_override is None else f'{st}+wall_override'
                return effective_ws, label, f'common:cCiv{ck}'
    return None, None, None


def main() -> int:
    common = ROOT / 'game/ai/leaders/leaderCommon.xs'
    rev = ROOT / 'game/ai/leaders/leader_revolution_commanders.xs'
    leaders_dir = ROOT / 'game/ai/leaders'
    spec_path = ROOT / 'playstyle_spec.json'

    style_ws = load_style_to_ws(common)
    leader_to_style = load_leader_file_style(leaders_dir)
    rvlt_style = load_revolution_dispatch(rev)
    civ_dispatch = load_civ_dispatch(common)
    spec = json.loads(spec_path.read_text())

    mismatches = []
    unknowns = []
    for data_name, entry in spec['civs'].items():
        spec_ws = entry.get('claims', {}).get('wall_strategy')
        eng_ws, style, src = infer_engine_ws(
            data_name, entry.get('civ_label', ''),
            leader_to_style, rvlt_style, civ_dispatch, style_ws,
        )
        if eng_ws is None:
            unknowns.append(data_name)
            continue
        if eng_ws != spec_ws:
            mismatches.append({
                'data_name': data_name,
                'engine_ws': eng_ws,
                'engine_ws_name': WS_NAME.get(eng_ws, '?'),
                'spec_ws': spec_ws,
                'spec_ws_name': WS_NAME.get(spec_ws, str(spec_ws)),
                'style': style,
                'source': src,
            })

    print(f'== {len(mismatches)} engine-vs-spec wall_strategy mismatches ==')
    for r in mismatches:
        print(f"  {r['data_name']}")
        print(f"    engine={r['engine_ws']}({r['engine_ws_name']}) "
              f"spec={r['spec_ws']}({r['spec_ws_name']}) "
              f"via {r['style']} [{r['source']}]")
    print(f'== {len(unknowns)} civs with no engine path matched ==')
    for u in unknowns:
        print(f'  {u}')

    out_dir = ROOT / 'artifacts/validation/engine_vs_spec'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'findings.json').write_text(json.dumps({
        'mismatches': mismatches,
        'unknowns': unknowns,
        'total_civs': len(spec['civs']),
    }, indent=2))
    print(f'\nwrote {out_dir / "findings.json"}')
    return 1 if mismatches else 0


if __name__ == '__main__':
    sys.exit(main())
