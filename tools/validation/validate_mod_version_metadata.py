#!/usr/bin/env python3
"""Catch version-metadata inconsistencies before Workshop submission.

Checks that ``modinfo.json``, ``mod.xml``, and ``RELEASE_NOTES.md`` (when they
exist) all agree on the same version string.  At least one of ``modinfo.json``
or ``mod.xml`` must be present for a Workshop-ready mod.

Rank #5 in test coverage plan (impact 4/5, effort 1/5).

Usage::

    python3 tools/validation/validate_mod_version_metadata.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_modinfo_version(path: Path) -> str | None:
    """Return version string from modinfo.json, or None on failure."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data["version"]) if "version" in data else None


def parse_modxml_version(path: Path) -> str | None:
    """Return version string from mod.xml <version> element, or None."""
    tree = ET.parse(path)
    elem = tree.getroot().find("version")
    return elem.text.strip() if elem is not None and elem.text else None


def parse_release_notes_version(path: Path) -> str | None:
    """Return the first version heading found in RELEASE_NOTES.md.

    Recognises headings like:  ## v1.0.0  /  ## 1.0.0  /  # v2.3
    Returns the raw version token (e.g. ``v1.0.0`` or ``1.0.0``).
    """
    text = path.read_text(encoding="utf-8")
    # Look at any heading line (# or ## or ###) and pull the first
    # version token (v?MAJOR.MINOR[.PATCH][...] ) from it. Handles both
    # "## v1.0.0" and "# A New World — Release Notes v1.0".
    for line in text.splitlines():
        if re.match(r"^#{1,3}\s+", line):
            m = re.search(r"\b(v?\d+\.\d+(?:\.[\w.]+)?)", line)
            if m:
                return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Normalisation — strip leading "v" so "v1.0.0" == "1.0.0"
# ---------------------------------------------------------------------------

def normalise(version: str) -> str:
    """Drop leading 'v' and zero-pad to three parts so 1.0 == 1.0.0."""
    v = version.lstrip("v").strip()
    parts = v.split(".")
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modinfo", type=Path,
                    default=REPO_ROOT / "modinfo.json")
    ap.add_argument("--mod-xml", type=Path,
                    default=REPO_ROOT / "mod.xml")
    # Default release-notes file: resolve at runtime so versioned filenames
    # (RELEASE_NOTES_v1.0.md) are picked up automatically.
    ap.add_argument("--release-notes", type=Path, default=None)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("MOD VERSION METADATA")
    print("=" * 60)

    failures: list[str] = []
    report: dict = {}

    # --- modinfo.json -------------------------------------------------------
    modinfo_version: str | None = None
    if not args.modinfo.exists():
        print(f"  WARN: modinfo.json not found at {args.modinfo} — skipping")
        report["modinfo"] = {"status": "missing"}
    else:
        try:
            modinfo_version = parse_modinfo_version(args.modinfo)
        except Exception as exc:
            failures.append(f"modinfo.json parse error: {exc}")
            report["modinfo"] = {"status": "parse_error", "error": str(exc)}
        else:
            if modinfo_version is None:
                failures.append("modinfo.json: no 'version' key")
                report["modinfo"] = {"status": "missing_key"}
            else:
                print(f"  ✓ modinfo.json version = {modinfo_version}")
                report["modinfo"] = {"status": "ok", "version": modinfo_version}

    # --- mod.xml ------------------------------------------------------------
    modxml_version: str | None = None
    if not args.mod_xml.exists():
        print(f"  WARN: mod.xml not found at {args.mod_xml} — skipping")
        report["mod_xml"] = {"status": "missing"}
    else:
        try:
            modxml_version = parse_modxml_version(args.mod_xml)
        except Exception as exc:
            failures.append(f"mod.xml parse error: {exc}")
            report["mod_xml"] = {"status": "parse_error", "error": str(exc)}
        else:
            if modxml_version is None:
                failures.append("mod.xml: no <version> element")
                report["mod_xml"] = {"status": "missing_element"}
            elif modinfo_version is not None:
                if normalise(modxml_version) == normalise(modinfo_version):
                    print(f"  ✓ mod.xml version = {modxml_version}"
                          f" (matches modinfo.json)")
                else:
                    msg = (f"mod.xml version '{modxml_version}' does not match"
                           f" modinfo.json version '{modinfo_version}'")
                    failures.append(msg)
                    print(f"  ✗ {msg}")
                report["mod_xml"] = {"status": "ok", "version": modxml_version}
            else:
                print(f"  ✓ mod.xml version = {modxml_version}")
                report["mod_xml"] = {"status": "ok", "version": modxml_version}

    # --- At-least-one check -------------------------------------------------
    if modinfo_version is None and modxml_version is None:
        if not args.modinfo.exists() and not args.mod_xml.exists():
            msg = "Neither modinfo.json nor mod.xml found — mod is not Workshop-ready"
            failures.append(msg)
            print(f"  ✗ {msg}")

    # --- RELEASE_NOTES.md ---------------------------------------------------
    canonical = normalise(modinfo_version or modxml_version or "")
    # Auto-discover release notes if not explicitly provided.  Try plain
    # RELEASE_NOTES.md first, then versioned variants (RELEASE_NOTES_v*.md
    # / RELEASE_NOTES-*.md) sorted lexically so the highest-numbered one
    # wins.
    if args.release_notes is None:
        candidates = sorted(REPO_ROOT.glob("RELEASE_NOTES*.md"))
        plain = REPO_ROOT / "RELEASE_NOTES.md"
        if plain.exists():
            args.release_notes = plain
        elif candidates:
            args.release_notes = candidates[-1]
        else:
            args.release_notes = plain  # for the "missing" message below
    if not args.release_notes.exists():
        print(f"  WARN: RELEASE_NOTES*.md not found in {REPO_ROOT} — skipping")
        report["release_notes"] = {"status": "missing"}
    else:
        try:
            rn_version = parse_release_notes_version(args.release_notes)
        except Exception as exc:
            failures.append(f"RELEASE_NOTES.md parse error: {exc}")
            report["release_notes"] = {"status": "parse_error", "error": str(exc)}
        else:
            if rn_version is None:
                failures.append("RELEASE_NOTES.md: no version heading found")
                print("  ✗ RELEASE_NOTES.md: no version heading found")
                report["release_notes"] = {"status": "no_heading"}
            elif canonical and normalise(rn_version) != canonical:
                msg = (f"RELEASE_NOTES.md most-recent = {rn_version}"
                       f" — does not match mod version '{canonical}'")
                failures.append(msg)
                print(f"  ✗ {msg}")
                report["release_notes"] = {"status": "mismatch", "version": rn_version}
            else:
                print(f"  ✓ RELEASE_NOTES.md most-recent = {rn_version} (matches)")
                report["release_notes"] = {"status": "ok", "version": rn_version}

    # --- Summary ------------------------------------------------------------
    print()
    if failures:
        print(f"FAIL — {len(failures)} version inconsistency(ies):")
        for f in failures:
            print(f"  • {f}")
    else:
        print("PASS — all version metadata consistent")

    report["failures"] = failures
    report["passed"] = not failures

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
