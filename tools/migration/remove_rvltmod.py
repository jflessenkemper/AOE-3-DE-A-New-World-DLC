#!/usr/bin/env python3
"""
remove_anw.py — Remove all ANW*/anw/ANW mentions from the ANW repo.

Usage:
  python3 tools/migration/remove_anw.py            # dry-run (default)
  python3 tools/migration/remove_anw.py --apply    # apply changes

Substitutions applied IN ORDER (case-sensitive):
  1. ANWRevFrance  -> ANWRevFrance   (special override, FIRST)
  2. anwrevfrance  -> anwrevfrance   (lowercase variant)
  3. ANW                     -> ANW
  4. anw                     -> anw
  5. ANW                     -> ANW

For .xs files: collapse duplicate OR arms produced by substitution,
e.g. `if (x == "ANWFoo" || x == "ANWFoo")` -> `if (x == "ANWFoo")`.
"""

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")

SKIP_DIRS = {".git", "artifacts", "replays"}

BINARY_EXTENSIONS = {
    ".age3yrec", ".age3yscn", ".png", ".webp", ".jpg", ".jpeg",
    ".bar", ".tga", ".wav", ".ogg", ".dds", ".mp3", ".mp4",
    ".pdf", ".exe", ".dll", ".so", ".pyc", ".pyd",
}

# Substitutions in order (case-sensitive)
SUBSTITUTIONS = [
    ("ANWRevFrance", "ANWRevFrance"),
    ("anwrevfrance", "anwrevfrance"),
    ("ANW",  "ANW"),
    ("anw",  "anw"),
    ("ANW",  "ANW"),
]

# Regex to detect and collapse duplicate OR arms in XS if-conditions after substitution.
# Matches patterns like:
#   if (VAR == "TOKX" || VAR == "TOKX")
#   } else if (VAR == "TOKX" || VAR == "TOKX") {
# The key invariant: after substitution both sides of || are now identical.
# We support up to 3 chained || terms (the dead code was always a 2-arm pattern).
_DUP_OR_RE = re.compile(
    r'\b(if\s*\(\s*)'                        # group 1: if (
    r'(\w+\s*(?:==|!=)\s*"[^"]*")'          # group 2: lhs comparison
    r'(\s*\|\|\s*)'                          # group 3: first ||
    r'(\w+\s*(?:==|!=)\s*"[^"]*")'          # group 4: rhs comparison (may equal lhs)
    r'(\s*(?:\|\|\s*\w+\s*(?:==|!=)\s*"[^"]*"\s*)*)'  # group 5: optional additional arms
    r'(\s*\))'                               # group 6: closing )
)

def _collapse_duplicate_or(line: str) -> str:
    """If a line has `if (x == "A" || x == "A")` pattern, collapse duplicates."""
    def _replace(m: re.Match) -> str:
        open_paren  = m.group(1)
        lhs         = m.group(2).strip()
        rhs         = m.group(4).strip()
        extra       = m.group(5)
        close_paren = m.group(6)

        # Collect all arms
        arms = [lhs, rhs]
        if extra:
            for tok in re.findall(r'\w+\s*(?:==|!=)\s*"[^"]*"', extra):
                arms.append(tok.strip())

        # Deduplicate while preserving order
        seen = []
        for arm in arms:
            if arm not in seen:
                seen.append(arm)

        if len(seen) == len(arms):
            return m.group(0)  # nothing to collapse

        collapsed = " || ".join(seen)
        return f"{open_paren}{collapsed}{close_paren}"

    return _DUP_OR_RE.sub(_replace, line)


def apply_substitutions(content: str, is_xs: bool) -> tuple[str, int]:
    """Return (new_content, substitution_count)."""
    count = 0
    for old, new in SUBSTITUTIONS:
        occurrences = content.count(old)
        if occurrences:
            content = content.replace(old, new)
            count += occurrences

    if is_xs and count > 0:
        # Collapse duplicate OR arms line by line
        lines = content.splitlines(keepends=True)
        new_lines = [_collapse_duplicate_or(l) for l in lines]
        content = "".join(new_lines)

    return content, count


def should_skip_dir(dir_name: str) -> bool:
    return dir_name in SKIP_DIRS


def should_skip_file(path: Path) -> bool:
    ext = path.suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return True
    return False


def process_repo(apply: bool) -> dict:
    stats = {
        "files_changed": 0,
        "total_substitutions": 0,
        "skipped_binary": 0,
        "skipped_warn": 0,
        "changed_files": [],
    }

    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

        for filename in filenames:
            filepath = Path(dirpath) / filename

            if should_skip_file(filepath):
                stats["skipped_binary"] += 1
                continue

            # Safety: must stay within repo root
            try:
                filepath.relative_to(REPO_ROOT)
            except ValueError:
                print(f"WARN: {filepath} is outside repo root, skipping", file=sys.stderr)
                stats["skipped_warn"] += 1
                continue

            try:
                raw = filepath.read_bytes()
            except (PermissionError, OSError) as e:
                print(f"WARN: cannot read {filepath}: {e}", file=sys.stderr)
                stats["skipped_warn"] += 1
                continue

            # Skip binary files (null bytes)
            if b"\x00" in raw[:8192]:
                stats["skipped_binary"] += 1
                continue

            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content = raw.decode("latin-1")
                except UnicodeDecodeError:
                    print(f"WARN: cannot decode {filepath}, skipping", file=sys.stderr)
                    stats["skipped_warn"] += 1
                    continue

            is_xs = filepath.suffix.lower() == ".xs"
            new_content, count = apply_substitutions(content, is_xs)

            if count > 0:
                rel = filepath.relative_to(REPO_ROOT)
                stats["files_changed"] += 1
                stats["total_substitutions"] += count
                stats["changed_files"].append((str(rel), count))
                print(f"  [{count:4d} subs] {rel}")

                if apply:
                    # Re-encode with original encoding heuristic
                    try:
                        out_bytes = new_content.encode("utf-8")
                    except UnicodeEncodeError:
                        out_bytes = new_content.encode("latin-1")
                    filepath.write_bytes(out_bytes)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Remove ANW references from ANW repo")
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== remove_anw.py  [{mode}] ===")
    print(f"Repo: {REPO_ROOT}\n")

    stats = process_repo(apply=args.apply)

    print(f"\n{'='*50}")
    print(f"Files changed:       {stats['files_changed']}")
    print(f"Total substitutions: {stats['total_substitutions']}")
    print(f"Binary files skipped:{stats['skipped_binary']}")
    print(f"Warned/skipped:      {stats['skipped_warn']}")
    if not args.apply:
        print("\n[DRY-RUN] No files were modified. Re-run with --apply to apply.")


if __name__ == "__main__":
    main()
