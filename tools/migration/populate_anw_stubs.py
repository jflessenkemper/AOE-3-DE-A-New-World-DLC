"""Populate the 22 ANW base-civ stubs in data/civmods.xml with vanilla
civ data, preserving the existing ANW-specific portrait/homecity overrides
already present in each stub.

Output is all-lowercase tag names (engine merge requires this).

Uses line-walk parsing (not regex) to avoid catastrophic backtracking on
this 5500-line file.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.cardextract.xmb import parse_xmb  # noqa: E402
from tools.bar_extract import parse_header, read_entries, maybe_decompress  # noqa: E402

CIVMODS = REPO / "data" / "civmods.xml"
DATA_BAR = Path("/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game/Data/Data.bar")

ANW_TO_VANILLA = {
    "ANWAztecs": "XPAztec",
    "ANWBritish": "British",
    "ANWChinese": "Chinese",
    "ANWDutch": "Dutch",
    "ANWEthiopians": "DEEthiopians",
    "ANWFrench": "French",
    "ANWGermans": "Germans",
    "ANWHaudenosaunee": "XPIroquois",
    "ANWHausa": "DEHausa",
    "ANWInca": "DEInca",
    "ANWIndians": "Indians",
    "ANWItalians": "DEItalians",
    "ANWJapanese": "Japanese",
    "ANWLakota": "XPSioux",
    "ANWMaltese": "DEMaltese",
    "ANWMexicans": "DEMexicans",
    "ANWOttomans": "Ottomans",
    "ANWPortuguese": "Portuguese",
    "ANWRussians": "Russians",
    "ANWSpanish": "Spanish",
    "ANWSwedes": "DESwedish",
    "ANWUSA": "DEAmericans",
}

# Fields we KEEP from the existing stub (ANW overrides).
STUB_OVERRIDE_FIELDS = {
    "name",
    "displaynameid",
    "rollovernameid",
    "homecityfilename",
    "homecitypreviewwpf",
    "matchmakingtextures",
}


def load_vanilla() -> dict[str, ET.Element]:
    with DATA_BAR.open("rb") as f:
        version, _n, offs = parse_header(f)
        _r, entries = read_entries(f, version, offs)
        e = next((x for x in entries if x["name"].lower().endswith("civs.xml.xmb")), None)
        if e is None:
            raise SystemExit("civs.xml.XMB not found")
        f.seek(e["offset"])
        raw = f.read(e["size2"])
    return {(c.findtext("name") or ""): c for c in parse_xmb(maybe_decompress(raw)) if c.tag == "civ"}


def render_lowercase(el: ET.Element, depth: int) -> str:
    tag = el.tag.lower()
    ind = "\t" * depth
    children = list(el)
    text = (el.text or "").strip()
    attribs = "".join(f' {k}="{v}"' for k, v in el.attrib.items())
    if not children:
        if text:
            return f"{ind}<{tag}{attribs}>{text}</{tag}>\n"
        return f"{ind}<{tag}{attribs}></{tag}>\n"
    body = "".join(render_lowercase(c, depth + 1) for c in children)
    return f"{ind}<{tag}{attribs}>\n{body}{ind}</{tag}>\n"


def render_block(anw_token: str, vanilla: ET.Element, stub_overrides: dict[str, ET.Element]) -> str:
    lines = ["\t<civ>"]
    emitted = set()
    lines.append(f"\t\t<name>{anw_token}</name>")
    emitted.add("name")
    for child in vanilla:
        t = child.tag.lower()
        if t == "name":
            continue
        if t in STUB_OVERRIDE_FIELDS and t in stub_overrides:
            lines.append(render_lowercase(stub_overrides[t], 2).rstrip())
            emitted.add(t)
            continue
        lines.append(render_lowercase(child, 2).rstrip())
        emitted.add(t)
    for t, stub_el in stub_overrides.items():
        if t in emitted:
            continue
        lines.append(render_lowercase(stub_el, 2).rstrip())
    lines.append("\t</civ>")
    return "\n".join(lines) + "\n"


def find_civ_blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    """Return list of (start_idx, end_idx_exclusive, name) for each <civ>...</civ>
    block at the top-level (single tab indent) in civmods.xml."""
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.rstrip() == "\t<civ>":
            start = i
            # Find matching </civ>
            j = i + 1
            name = None
            while j < n:
                stripped = lines[j].strip()
                if name is None and stripped.startswith("<name>"):
                    e = stripped.find("</name>")
                    if e > 0:
                        name = stripped[len("<name>"):e]
                if lines[j].rstrip() == "\t</civ>":
                    blocks.append((start, j + 1, name or ""))
                    i = j + 1
                    break
                j += 1
            else:
                i = n
        else:
            i += 1
    return blocks


def main() -> int:
    print(f"Reading vanilla civs.xml from {DATA_BAR}", file=sys.stderr)
    vanilla = load_vanilla()
    print(f"  loaded {len(vanilla)} vanilla civs", file=sys.stderr)

    text = CIVMODS.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    blocks = find_civ_blocks(lines)
    print(f"  found {len(blocks)} <civ> blocks in civmods.xml", file=sys.stderr)

    # Build new file content: iterate blocks; replace target stubs, keep others.
    name_to_block = {name: (s, e) for s, e, name in blocks}
    target_names = set(ANW_TO_VANILLA.keys())

    replaced = 0
    missing = []
    out_parts: list[str] = []
    cursor = 0

    # Sort blocks by position for deterministic merge
    sorted_blocks = sorted(blocks, key=lambda b: b[0])
    for start, end, name in sorted_blocks:
        # Copy lines from cursor up to start
        out_parts.extend(lines[cursor:start])

        if name in target_names:
            van_token = ANW_TO_VANILLA[name]
            van = vanilla.get(van_token)
            if van is None:
                missing.append(f"vanilla:{van_token}")
                out_parts.extend(lines[start:end])
            else:
                stub_text = "".join(lines[start:end])
                try:
                    stub_el = ET.fromstring(stub_text)
                    stub_overrides = {c.tag.lower(): c for c in stub_el}
                    new_block = render_block(name, van, stub_overrides)
                    out_parts.append(new_block)
                    replaced += 1
                except ET.ParseError as e:
                    missing.append(f"parse:{name}: {e}")
                    out_parts.extend(lines[start:end])
        else:
            # Keep verbatim
            out_parts.extend(lines[start:end])
        cursor = end

    # Trailing lines after last block
    out_parts.extend(lines[cursor:])

    new_text = "".join(out_parts)
    print(f"  replaced {replaced}/{len(ANW_TO_VANILLA)} stubs", file=sys.stderr)
    if missing:
        print(f"  MISSING: {missing}", file=sys.stderr)

    if new_text != text:
        CIVMODS.write_text(new_text, encoding="utf-8")
        print(f"wrote {CIVMODS} ({len(new_text)} bytes, was {len(text)})", file=sys.stderr)
    else:
        print("no changes", file=sys.stderr)
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
