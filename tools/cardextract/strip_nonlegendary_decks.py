"""Remove every <deck> block from data/*homecity*.xml except the
"Legendary Leaders" deck.

Rationale: when both base-game decks (Land / Naval / etc.) and our
"Legendary Leaders" deck coexist, the in-game Deck Builder defaults to
the base-game deck and the mod's curated deck isn't surfaced. We want
players to see ONLY our custom deck.

Idempotent: files that already have exactly one <deck> are skipped.
Warns if a file has no "Legendary Leaders" deck (leaves it untouched).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"

DECK_RE = re.compile(r"(\s*)<deck>(.*?)</deck>", re.DOTALL)
DECKS_WRAPPER_RE = re.compile(r"(<decks>)(.*?)(</decks>)", re.DOTALL)


def process(path: Path) -> str:
    txt = path.read_text(encoding="utf-8")
    decks = DECK_RE.findall(txt)
    if not decks:
        return "no_decks_section"
    if len(decks) == 1:
        return "already_ll_only"

    ll = None
    for indent, body in decks:
        if re.search(r"<name>\s*Legendary Leaders\s*</name>", body):
            ll = (indent, body)
            break
    if ll is None:
        return "no_ll_found"

    wrapper = DECKS_WRAPPER_RE.search(txt)
    if not wrapper:
        return "no_wrapper"
    indent, body = ll
    new_inner = "\n" + f"{indent}<deck>{body}</deck>" + "\n  "
    new_txt = txt[:wrapper.start(2)] + new_inner + txt[wrapper.end(2):]
    path.write_text(new_txt, encoding="utf-8")
    return "stripped"


def main():
    targets = sorted(list(DATA.glob("homecity*.xml")) + list(DATA.glob("anwhomecity*.xml")))
    counts = {"stripped": 0, "already_ll_only": 0, "no_ll_found": 0,
              "no_decks_section": 0, "no_wrapper": 0}
    for f in targets:
        result = process(f)
        counts[result] = counts.get(result, 0) + 1
        if result in ("no_ll_found", "no_wrapper"):
            print(f"  WARN {f.name}: {result}")
    print()
    print(f"Scanned: {len(targets)} homecity files")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
