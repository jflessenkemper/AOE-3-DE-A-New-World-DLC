#!/usr/bin/env python3
"""Verify each ANW civ has an *active* ``.personality`` file (not just .proposed).

Bug class this catches (hit on 2026-05-08): we wrote
``anwfoo.personality.proposed`` while iterating, never renamed to
``anwfoo.personality``, and the engine silently used base-game leader
behavior for that civ. Symptom: ANWFoo plays "British colonial" instead
of its documented doctrine, but no error is logged.

For every ANW civ token in ``anw_token_map.ANW_CIVS``, this validator
confirms there is an *active* ``game/ai/anw{stem}.personality`` file
(stem = lowercase-suffix-after-ANW). It also flags the case where ONLY
a ``.proposed`` shadow exists — that's a release blocker.

Usage::

    python3 tools/validation/validate_personality_active.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402


def stem_from_token(token: str) -> str:
    info = ANW_CIVS.get(token, {})
    return info.get("file_stem") or (
        token[3:].lower() if token.startswith("ANW") else token.lower()
    )


def find_proposed_shadow(ai_dir: Path, stem: str) -> Path | None:
    """Return path to a .proposed shadow if it exists anywhere under ai_dir."""
    for p in ai_dir.rglob(f"anw{stem}.personality.proposed"):
        return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ai-dir", type=Path,
                    default=REPO_ROOT / "game" / "ai")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not args.ai_dir.exists():
        print(f"ERROR: {args.ai_dir} not found", file=sys.stderr)
        return 2

    print("=" * 60)
    print("ANW PERSONALITY ACTIVE FILE CHECK")
    print("=" * 60)

    missing: list[tuple[str, str, Path | None]] = []  # token, stem, proposed_path
    proposed_only: list[tuple[str, str, Path]] = []
    ok: list[str] = []

    for token, info in ANW_CIVS.items():
        stem = stem_from_token(token)
        active = args.ai_dir / f"anw{stem}.personality"
        if active.exists():
            ok.append(token)
            continue
        proposed = find_proposed_shadow(args.ai_dir, stem)
        if proposed is not None:
            proposed_only.append((token, stem, proposed))
        else:
            missing.append((token, stem, None))

    print(f"  ✓ Active .personality:           {len(ok):>3}/{len(ANW_CIVS)}")
    print(f"  ✗ Missing entirely:              {len(missing):>3}")
    print(f"  ✗ Only .proposed shadow exists:  {len(proposed_only):>3}")
    print()

    if missing:
        print("FAIL — civs with NO personality file:")
        for token, stem, _ in missing[:20]:
            print(f"    {token}  (expected anw{stem}.personality)")
        if len(missing) > 20:
            print(f"    … +{len(missing) - 20} more")

    if proposed_only:
        print()
        print("FAIL — civs with .proposed shadow but no active file "
              "(engine ignores .proposed):")
        for token, stem, p in proposed_only[:20]:
            print(f"    {token}  → {p.relative_to(REPO_ROOT)}  "
                  f"(rename to anw{stem}.personality)")
        if len(proposed_only) > 20:
            print(f"    … +{len(proposed_only) - 20} more")

    fail_count = len(missing) + len(proposed_only)

    if args.json:
        import json
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({
                "total": len(ANW_CIVS),
                "active_ok": len(ok),
                "missing": [(t, s) for t, s, _ in missing],
                "proposed_only": [(t, s, str(p.relative_to(REPO_ROOT)))
                                  for t, s, p in proposed_only],
                "fail_count": fail_count,
            }, f, indent=2)
        print(f"Report: {args.json}")

    print()
    print(f"OVERALL: {'FAIL' if fail_count else 'PASS'} "
          f"({len(ok)}/{len(ANW_CIVS)} active)")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
