#!/usr/bin/env python3
"""Pixel-perfect static art verifier for the ANW mod.

Layered checks (each one builds on the previous):

  1. **Existence**       — every HTML <img src> resolves to a file on disk
  2. **Header**          — file's magic bytes match its extension
  3. **Decode**          — Pillow can open it; we capture (W, H)
  4. **HTML ↔ civmods**  — for each civ, the HTML's flag-img / portrait-img
                            equal the engine's HomeCityFlagIconWPF /
                            HomeCityPreviewWPF (post path-normalisation)
  5. **Source ↔ deployed** — for every HTML img, the source file's bytes
                              match the deployed mod copy (sha256)
  6. **Hi-res linkage**   — every civ has an art/ui/leaders/<stem>.png that
                            looks like a higher-res version of its HTML
                            portrait (perceptual hash distance)
  7. **Orphans**          — files in art/ui/leaders/ that no civ claims
  8. **Duplicates**       — flag images shipped under both Title_Case and
                            lower_case names (legacy issue)

Each check produces a row::

    {"check": "html_exists", "asset": "...", "status": "PASS|WARN|FAIL", "detail": "..."}

CLI::

    python3 tools/validation/validate_art_pixel_perfect.py            # human report
    python3 tools/validation/validate_art_pixel_perfect.py --json     # machine
    python3 tools/validation/validate_art_pixel_perfect.py --strict   # WARN→FAIL
    python3 tools/validation/validate_art_pixel_perfect.py --civ ANWBritish

Designed to be importable: ``run_all(repo, deployed)`` returns the same dict
the CLI prints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[2]

# Lazy imports so the module loads even if Pillow is missing
try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:
    import imagehash  # type: ignore
except Exception:  # pragma: no cover
    imagehash = None  # type: ignore

# Reuse the inventory builder so we don't re-walk twice.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from art_inventory import build_inventory, DEFAULT_DEPLOYED  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPG_MAGIC = b"\xff\xd8\xff"
GIF_MAGIC = b"GIF8"
SVG_MAGIC = b"<?xml"
SVG_MAGIC2 = b"<svg"

PHASH_THRESHOLD_GOOD = 8     # ≤ this: same source asset
PHASH_THRESHOLD_WARN = 16    # > GOOD, ≤ WARN: probably same; warn
                             # > WARN: probably different — fail


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def _row(check: str, asset: str, status: str, detail: str = "", **extra) -> dict:
    r = {"check": check, "asset": asset, "status": status, "detail": detail}
    r.update(extra)
    return r


def _check_header(path: Path) -> str | None:
    """Return None if header looks right; otherwise a short reason."""
    if not path.exists():
        return "missing"
    try:
        head = path.read_bytes()[:16]
    except OSError as e:
        return f"unreadable: {e}"
    if not head:
        return "empty"
    suf = path.suffix.lower()
    if suf == ".png" and not head.startswith(PNG_MAGIC):
        return "bad PNG magic"
    if suf in (".jpg", ".jpeg") and not head.startswith(JPG_MAGIC):
        return "bad JPEG magic"
    if suf == ".gif" and not head.startswith(GIF_MAGIC):
        return "bad GIF magic"
    if suf == ".svg" and not (head.startswith(SVG_MAGIC) or head.startswith(SVG_MAGIC2)):
        return "bad SVG magic"
    return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _decode_size(path: Path) -> tuple[int, int] | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            return im.size  # (w, h)
    except Exception:
        return None


def _phash(path: Path):
    if Image is None or imagehash is None:
        return None
    try:
        with Image.open(path) as im:
            return imagehash.phash(im.convert("RGB"))
    except Exception:
        return None


def _normalise(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


# ---------------------------------------------------------------------------
# Per-check implementations
# ---------------------------------------------------------------------------

def check_html_files(inv: dict, repo: Path, civ_filter: str | None) -> list[dict]:
    """For every HTML <img src="resources/..."> asset claimed by a civ,
    confirm existence + header + decode."""
    rows: list[dict] = []
    seen: set[str] = set()
    for civ_name, rec in inv["civs"].items():
        if civ_filter and civ_name != civ_filter:
            continue
        targets = []
        if rec.get("html_flag"):
            targets.append(("flag", rec["html_flag"]))
        if rec.get("html_portrait"):
            targets.append(("portrait", rec["html_portrait"]))
        for src in rec.get("html_extra_imgs", []):
            targets.append(("extra", src))
        for kind, src in targets:
            if src in seen:
                continue
            seen.add(src)
            if src.startswith("http"):
                continue  # remote badge or external img
            p = repo / src
            err = _check_header(p)
            if err:
                rows.append(_row("html_exists", src, "FAIL", err, civ=civ_name, kind=kind))
                continue
            sz = _decode_size(p)
            if sz is None:
                rows.append(_row("html_decode", src, "WARN",
                                  "Pillow could not decode (could be SVG)",
                                  civ=civ_name, kind=kind))
            else:
                rows.append(_row("html_exists", src, "PASS",
                                  f"{sz[0]}x{sz[1]}", civ=civ_name, kind=kind,
                                  width=sz[0], height=sz[1]))
    return rows


def check_civmods_files_exist(inv: dict, repo: Path, civ_filter: str | None) -> list[dict]:
    """The paths civmods.xml references must exist on disk. This is the
    most important check — if civmods points at a nonexistent file the
    engine renders nothing for that civ at runtime."""
    rows: list[dict] = []
    for civ_name, rec in inv["civs"].items():
        if civ_filter and civ_name != civ_filter:
            continue
        for kind, key in (
            ("portrait", "civmods_portrait_wpf"),
            ("flag", "civmods_flag_wpf"),
            ("postgame_flag", "civmods_postgame_wpf"),
        ):
            wpf = rec.get(key, "")
            if not wpf:
                continue
            p = repo / wpf
            if p.exists():
                rows.append(_row(f"civmods_file_exists.{kind}", civ_name, "PASS",
                                  wpf, civ=civ_name))
            else:
                rows.append(_row(f"civmods_file_exists.{kind}", civ_name, "FAIL",
                                  f"missing on disk: {wpf}", civ=civ_name))
    return rows


def check_html_vs_civmods(inv: dict, civ_filter: str | None) -> list[dict]:
    """The HTML's flag/portrait should equal civmods.xml's WPF paths."""
    rows: list[dict] = []
    for civ_name, rec in inv["civs"].items():
        if civ_filter and civ_name != civ_filter:
            continue
        # Portrait (HomeCityPreviewWPF)
        h_p = _normalise(rec.get("html_portrait", ""))
        c_p = _normalise(rec.get("civmods_portrait_wpf", ""))
        if not h_p and not c_p:
            rows.append(_row("html_vs_civmods.portrait", civ_name, "WARN",
                              "no portrait in HTML or civmods", civ=civ_name))
        elif h_p == c_p:
            rows.append(_row("html_vs_civmods.portrait", civ_name, "PASS",
                              h_p, civ=civ_name))
        else:
            rows.append(_row("html_vs_civmods.portrait", civ_name, "FAIL",
                              f"HTML={h_p!r} civmods={c_p!r}", civ=civ_name))
        # Flag (HomeCityFlagIconWPF or PostgameFlagIconWPF — pick the first match)
        h_f = _normalise(rec.get("html_flag", ""))
        c_f = _normalise(rec.get("civmods_flag_wpf", ""))
        c_pg = _normalise(rec.get("civmods_postgame_wpf", ""))
        if not h_f and not c_f:
            rows.append(_row("html_vs_civmods.flag", civ_name, "WARN",
                              "no flag in HTML or civmods", civ=civ_name))
        elif h_f == c_f or h_f == c_pg:
            rows.append(_row("html_vs_civmods.flag", civ_name, "PASS",
                              h_f, civ=civ_name))
        else:
            rows.append(_row("html_vs_civmods.flag", civ_name, "FAIL",
                              f"HTML={h_f!r} civmods.flag={c_f!r} civmods.postgame={c_pg!r}",
                              civ=civ_name))
    return rows


def check_source_vs_deployed(inv: dict, repo: Path, deployed: Path | None,
                              civ_filter: str | None) -> list[dict]:
    """For each HTML img claimed by a civ, hash source vs deployed copy."""
    rows: list[dict] = []
    if not deployed or not deployed.exists():
        rows.append(_row("source_vs_deployed", "<root>", "WARN",
                          f"deployed dir not present: {deployed}"))
        return rows
    seen: set[str] = set()
    for civ_name, rec in inv["civs"].items():
        if civ_filter and civ_name != civ_filter:
            continue
        candidates = [rec.get("html_flag", ""), rec.get("html_portrait", "")]
        candidates.extend(rec.get("html_extra_imgs", []))
        for src in candidates:
            if not src or src in seen or src.startswith("http"):
                continue
            seen.add(src)
            sp = repo / src
            dp = deployed / src
            if not sp.exists():
                rows.append(_row("source_vs_deployed", src, "FAIL",
                                  "missing in source", civ=civ_name))
                continue
            if not dp.exists():
                rows.append(_row("source_vs_deployed", src, "FAIL",
                                  "missing in deployed mod", civ=civ_name))
                continue
            try:
                h1 = _sha256(sp)
                h2 = _sha256(dp)
            except OSError as e:
                rows.append(_row("source_vs_deployed", src, "WARN",
                                  f"hash failed: {e}", civ=civ_name))
                continue
            if h1 == h2:
                rows.append(_row("source_vs_deployed", src, "PASS",
                                  f"sha256={h1[:12]}", civ=civ_name))
            else:
                rows.append(_row("source_vs_deployed", src, "FAIL",
                                  f"hash mismatch src={h1[:12]} deployed={h2[:12]}",
                                  civ=civ_name))
    return rows


def check_hires_portraits(inv: dict, repo: Path, civ_filter: str | None) -> list[dict]:
    """Each civ should have a hi-res `art/ui/leaders/<stem>.png`, and that
    image's perceptual hash should be close to the HTML portrait's pHash."""
    rows: list[dict] = []
    for civ_name, rec in inv["civs"].items():
        if civ_filter and civ_name != civ_filter:
            continue
        hires = rec.get("art_portrait_hires", "")
        html_p = rec.get("html_portrait", "")
        if not hires:
            rows.append(_row("hires_portrait", civ_name, "WARN",
                              "no art/ui/leaders/* file resolved",
                              civ=civ_name))
            continue
        if not html_p:
            rows.append(_row("hires_portrait", civ_name, "WARN",
                              f"hires={hires} but no HTML portrait", civ=civ_name))
            continue
        if Image is None or imagehash is None:
            rows.append(_row("hires_portrait", civ_name, "WARN",
                              "Pillow/imagehash unavailable", civ=civ_name))
            continue
        a = _phash(repo / hires)
        b = _phash(repo / html_p)
        if a is None or b is None:
            rows.append(_row("hires_portrait", civ_name, "WARN",
                              "phash failed", civ=civ_name))
            continue
        d = a - b  # imagehash subtraction = hamming distance
        if d <= PHASH_THRESHOLD_GOOD:
            status, label = "PASS", f"phash dist={d}"
        elif d <= PHASH_THRESHOLD_WARN:
            status, label = "WARN", f"phash dist={d} (probably same source)"
        else:
            status, label = "FAIL", f"phash dist={d} — looks like different art"
        rows.append(_row("hires_portrait", civ_name, status, label,
                          civ=civ_name, hires=hires, html_portrait=html_p))
    return rows


def check_orphans(inv: dict, repo: Path) -> list[dict]:
    """Files in art/ui/leaders/ that no civ links to."""
    rows: list[dict] = []
    pinned: set[str] = set()
    for rec in inv["civs"].values():
        if rec.get("art_portrait_hires"):
            pinned.add(rec["art_portrait_hires"])
    leaders_dir = repo / "art" / "ui" / "leaders"
    if not leaders_dir.exists():
        return rows
    for f in sorted(leaders_dir.iterdir()):
        if f.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        rel = f.relative_to(repo).as_posix()
        if rel in pinned:
            continue
        rows.append(_row("orphan_leader", rel, "WARN",
                          "unreferenced art/ui/leaders/* file"))
    return rows


def check_flag_duplicates(inv: dict, repo: Path) -> list[dict]:
    """`Flag_British.png` next to `flag_british.png` — legacy collision."""
    rows: list[dict] = []
    flags_dir = repo / "resources" / "images" / "icons" / "flags"
    if not flags_dir.exists():
        return rows
    by_lower: dict[str, list[str]] = defaultdict(list)
    for f in flags_dir.iterdir():
        by_lower[f.name.lower()].append(f.name)
    for low, variants in by_lower.items():
        if len(variants) > 1:
            rows.append(_row("flag_duplicates", low, "WARN",
                              f"variants: {sorted(variants)}"))
    return rows


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def run_all(repo: Path = REPO,
            deployed: Path | None = DEFAULT_DEPLOYED,
            civ_filter: str | None = None) -> dict:
    inv = build_inventory(repo, deployed)
    rows: list[dict] = []
    rows.extend(check_html_files(inv, repo, civ_filter))
    rows.extend(check_civmods_files_exist(inv, repo, civ_filter))
    rows.extend(check_html_vs_civmods(inv, civ_filter))
    rows.extend(check_source_vs_deployed(inv, repo, deployed, civ_filter))
    rows.extend(check_hires_portraits(inv, repo, civ_filter))
    if civ_filter is None:
        rows.extend(check_orphans(inv, repo))
        rows.extend(check_flag_duplicates(inv, repo))

    summary = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in rows:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {"summary": summary, "rows": rows, "civ_count": len(inv["civs"])}


def _render_human(report: dict, max_per_status: int = 30) -> str:
    out: list[str] = []
    s = report["summary"]
    out.append(f"=== Pixel-perfect static verifier ===")
    out.append(f"civs={report['civ_count']}  "
               f"PASS={s.get('PASS', 0)}  "
               f"WARN={s.get('WARN', 0)}  "
               f"FAIL={s.get('FAIL', 0)}")
    by_check: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in report["rows"]:
        by_check[r["check"]][r["status"]] += 1
    out.append("\nBy-check:")
    for check, statuses in sorted(by_check.items()):
        out.append(f"  {check:30s} "
                   f"P={statuses.get('PASS', 0):4d}  "
                   f"W={statuses.get('WARN', 0):4d}  "
                   f"F={statuses.get('FAIL', 0):4d}")
    fails = [r for r in report["rows"] if r["status"] == "FAIL"]
    warns = [r for r in report["rows"] if r["status"] == "WARN"]
    if fails:
        out.append(f"\nFAIL ({len(fails)}; showing first {min(max_per_status, len(fails))}):")
        for r in fails[:max_per_status]:
            out.append(f"  [{r['check']}] {r['asset']}: {r['detail']}")
    if warns:
        out.append(f"\nWARN ({len(warns)}; showing first {min(max_per_status, len(warns))}):")
        for r in warns[:max_per_status]:
            out.append(f"  [{r['check']}] {r['asset']}: {r['detail']}")
    return "\n".join(out)


def _cli(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true",
                    help="WARN counts as FAIL for exit code")
    p.add_argument("--civ", default=None,
                    help="Run for a single civ name (e.g. ANWBritish)")
    p.add_argument("--deployed", default=str(DEFAULT_DEPLOYED))
    p.add_argument("--max-rows", type=int, default=30)
    args = p.parse_args(list(argv) if argv is not None else None)

    deployed = Path(args.deployed) if args.deployed else None
    report = run_all(REPO, deployed, args.civ)

    if args.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(_render_human(report, args.max_rows))

    s = report["summary"]
    if s.get("FAIL", 0):
        return 1
    if args.strict and s.get("WARN", 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
