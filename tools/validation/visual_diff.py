#!/usr/bin/env python3
"""visual_diff.py — Pixel-level and perceptual diff between two sets of screenshots.

Compares a "before" directory of PNGs against an "after" directory (or a single
pair of images) and produces:

1. A JSON report with per-image metrics:
   - pixel_diff_pct     : fraction of pixels that differ by more than `threshold`
   - mse                : mean squared error across all channels
   - psnr               : peak signal-to-noise ratio (dB); inf = identical
   - phash_distance     : perceptual hash Hamming distance (0–64)
   - phash_similar      : True if phash_distance <= phash_cutoff (default 10)
   - verdict            : IDENTICAL | SIMILAR | CHANGED | UNMATCHED

2. A side-by-side HTML report with highlighted diff overlays for changed images.

Usage examples:
    # Compare two single images
    python3 tools/validation/visual_diff.py before.png after.png

    # Compare two directories (matched by filename)
    python3 tools/validation/visual_diff.py --before dir_a/ --after dir_b/

    # Full options
    python3 tools/validation/visual_diff.py \\
        --before artifacts/visual_art/ANWBritish/full/ \\
        --after  artifacts/visual_art/ANWBritish/full/ \\
        --out    artifacts/validation/visual_diff_report.html \\
        --json   artifacts/validation/visual_diff_report.json \\
        --threshold 5 --phash-cutoff 10

Dependencies:
    pip install Pillow imagehash numpy  (all present on this host)
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageChops, ImageFilter

try:
    import imagehash
    _HAS_IMAGEHASH = True
except ImportError:
    _HAS_IMAGEHASH = False


REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Core comparison functions
# ---------------------------------------------------------------------------


def load_image_rgb(path: Path) -> Optional[np.ndarray]:
    """Load a PNG/JPG and return a float32 [0,1] H×W×3 numpy array, or None on error."""
    try:
        img = Image.open(path).convert("RGB")
        return np.asarray(img, dtype=np.float32) / 255.0
    except Exception as exc:
        print(f"[visual_diff] WARNING: could not load {path}: {exc}", file=sys.stderr)
        return None


def compute_pixel_diff(
    a: np.ndarray, b: np.ndarray, threshold: float = 0.02
) -> tuple[float, float, float]:
    """Compare two float32 H×W×3 arrays.

    Returns:
        (pixel_diff_pct, mse, psnr)
        - pixel_diff_pct: fraction of pixels where any channel differs by > threshold
        - mse: mean squared error across all pixels and channels
        - psnr: peak signal-to-noise ratio (dB); math.inf if mse==0
    """
    if a.shape != b.shape:
        # Resize b to match a
        img_b = Image.fromarray((b * 255).astype(np.uint8))
        img_b = img_b.resize((a.shape[1], a.shape[0]), Image.LANCZOS)
        b = np.asarray(img_b, dtype=np.float32) / 255.0

    diff = np.abs(a - b)  # H×W×3
    # Pixels where ANY channel exceeds threshold
    exceeded = np.any(diff > threshold, axis=-1)
    pixel_diff_pct = float(exceeded.mean())

    mse = float(np.mean(diff ** 2))
    if mse == 0:
        psnr = math.inf
    else:
        psnr = 10.0 * math.log10(1.0 / mse)

    return pixel_diff_pct, mse, psnr


def compute_phash(path: Path) -> Optional[object]:
    """Compute perceptual hash (pHash) for an image file."""
    if not _HAS_IMAGEHASH:
        return None
    try:
        return imagehash.phash(Image.open(path))
    except Exception:
        return None


def phash_distance(h1: object, h2: object) -> Optional[int]:
    if h1 is None or h2 is None:
        return None
    try:
        return int(h1 - h2)
    except Exception:
        return None


def make_diff_overlay(a: np.ndarray, b: np.ndarray, amplify: float = 5.0) -> np.ndarray:
    """Create an amplified diff image (red channel = differences)."""
    if a.shape != b.shape:
        img_b = Image.fromarray((b * 255).astype(np.uint8))
        img_b = img_b.resize((a.shape[1], a.shape[0]), Image.LANCZOS)
        b = np.asarray(img_b, dtype=np.float32) / 255.0

    diff = np.abs(a - b)
    # Amplify differences; map to red channel
    overlay = np.zeros_like(a)
    diff_mag = np.clip(diff.max(axis=-1, keepdims=True) * amplify, 0, 1)
    overlay[..., 0] = diff_mag[..., 0]  # red
    # blend with dark version of original
    blended = a * 0.3 + overlay * 0.7
    return np.clip(blended, 0, 1)


def image_to_data_uri(arr: np.ndarray, max_dim: int = 600) -> str:
    """Convert a float32 H×W×3 array to a base64 PNG data URI (resized if needed)."""
    h, w = arr.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        img = Image.fromarray((arr * 255).astype(np.uint8))
        img = img.resize((new_w, new_h), Image.LANCZOS)
    else:
        img = Image.fromarray((arr * 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# Comparison result dataclass (plain dict for JSON serialisability)
# ---------------------------------------------------------------------------


def compare_pair(
    before_path: Path,
    after_path: Path,
    threshold: float = 0.02,
    phash_cutoff: int = 10,
) -> dict:
    """Compare a before/after pair. Returns a result dict."""
    result: dict = {
        "name": before_path.name,
        "before_path": str(before_path),
        "after_path": str(after_path),
        "pixel_diff_pct": None,
        "mse": None,
        "psnr": None,
        "phash_distance": None,
        "phash_similar": None,
        "verdict": "ERROR",
        "error": None,
        "_overlay_data_uri": None,
        "_before_data_uri": None,
        "_after_data_uri": None,
    }

    a = load_image_rgb(before_path)
    b = load_image_rgb(after_path)

    if a is None:
        result["error"] = f"could not load before: {before_path}"
        return result
    if b is None:
        result["error"] = f"could not load after: {after_path}"
        return result

    pixel_diff_pct, mse, psnr = compute_pixel_diff(a, b, threshold=threshold)
    result["pixel_diff_pct"] = round(pixel_diff_pct, 6)
    result["mse"] = round(mse, 8)
    result["psnr"] = round(psnr, 2) if not math.isinf(psnr) else None  # None = identical

    h_before = compute_phash(before_path)
    h_after = compute_phash(after_path)
    d = phash_distance(h_before, h_after)
    result["phash_distance"] = d
    result["phash_similar"] = (d is not None and d <= phash_cutoff)

    # Verdict
    if pixel_diff_pct == 0.0 and (d is None or d == 0):
        verdict = "IDENTICAL"
    elif pixel_diff_pct < threshold and result["phash_similar"] is not False:
        verdict = "SIMILAR"
    else:
        verdict = "CHANGED"
    result["verdict"] = verdict

    # Thumbnails and overlay for HTML (only for non-identical)
    if verdict in ("CHANGED", "SIMILAR"):
        result["_before_data_uri"] = image_to_data_uri(a)
        result["_after_data_uri"] = image_to_data_uri(b)
        if verdict == "CHANGED":
            overlay = make_diff_overlay(a, b)
            result["_overlay_data_uri"] = image_to_data_uri(overlay)

    return result


# ---------------------------------------------------------------------------
# HTML report builder
# ---------------------------------------------------------------------------


def build_html_report(results: list[dict]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    n_total = len(results)
    n_identical = sum(1 for r in results if r["verdict"] == "IDENTICAL")
    n_similar = sum(1 for r in results if r["verdict"] == "SIMILAR")
    n_changed = sum(1 for r in results if r["verdict"] == "CHANGED")
    n_unmatched = sum(1 for r in results if r["verdict"] == "UNMATCHED")
    n_error = sum(1 for r in results if r["verdict"] == "ERROR")

    rows_html_parts: list[str] = []
    for r in results:
        v = r["verdict"]
        v_css = {
            "IDENTICAL": "v-identical",
            "SIMILAR": "v-similar",
            "CHANGED": "v-changed",
            "UNMATCHED": "v-unmatched",
            "ERROR": "v-error",
        }.get(v, "")

        phash_str = str(r["phash_distance"]) if r["phash_distance"] is not None else "n/a"
        psnr_str = str(r["psnr"]) if r["psnr"] is not None else "∞"
        diff_pct_str = f"{r['pixel_diff_pct'] * 100:.3f}%" if r["pixel_diff_pct"] is not None else "–"

        imgs_html = ""
        if r.get("_before_data_uri"):
            imgs_html += f'<img class="thumb" src="{r["_before_data_uri"]}" title="Before">'
        if r.get("_after_data_uri"):
            imgs_html += f'<img class="thumb" src="{r["_after_data_uri"]}" title="After">'
        if r.get("_overlay_data_uri"):
            imgs_html += f'<img class="thumb overlay" src="{r["_overlay_data_uri"]}" title="Diff overlay (amplified)">'

        error_html = f'<div class="err">{html.escape(r["error"] or "")}</div>' if r.get("error") else ""

        rows_html_parts.append(f"""
<div class="result-card {v_css}">
  <div class="card-header">
    <span class="fname">{html.escape(r['name'])}</span>
    <span class="verdict-badge">{v}</span>
  </div>
  <div class="metrics">
    <span>Δpx: {diff_pct_str}</span>
    <span>PSNR: {psnr_str} dB</span>
    <span>pHash dist: {phash_str}</span>
  </div>
  {error_html}
  <div class="thumbs">{imgs_html}</div>
</div>""")

    rows_html = "\n".join(rows_html_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ANW Visual Diff Report</title>
<style>
  :root {{ --bg: #111; --surface: #1c1c1c; --border: #333; --text: #ddd; --muted: #888; }}
  body {{ font: 13px/1.5 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
  h1 {{ font-size: 1.3rem; margin-bottom: 4px; }}
  .meta {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 16px; }}
  .summary {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .s-chip {{ padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }}
  .s-identical {{ background: #1a2e1a; color: #4ade80; }}
  .s-similar {{ background: #1a2520; color: #34d399; }}
  .s-changed {{ background: #3a0f0f; color: #f87171; }}
  .s-unmatched {{ background: #2a1f00; color: #fbbf24; }}
  .s-error {{ background: #300; color: #f00; }}
  .results {{ display: grid; gap: 16px; }}
  .result-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }}
  .v-changed {{ border-color: #7f1d1d; }}
  .v-similar {{ border-color: #065f46; }}
  .v-unmatched {{ border-color: #78350f; }}
  .v-error {{ border-color: #7f1d1d; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .fname {{ font-weight: 600; font-size: 0.9rem; }}
  .verdict-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
  .v-identical .verdict-badge {{ background: #052e16; color: #4ade80; }}
  .v-similar .verdict-badge {{ background: #052e16; color: #34d399; }}
  .v-changed .verdict-badge {{ background: #450a0a; color: #f87171; }}
  .v-unmatched .verdict-badge {{ background: #292000; color: #fbbf24; }}
  .v-error .verdict-badge {{ background: #300; color: #f00; }}
  .metrics {{ font-size: 0.75rem; color: var(--muted); display: flex; gap: 16px; margin-bottom: 8px; }}
  .err {{ color: #f87171; font-size: 0.8rem; margin-bottom: 8px; }}
  .thumbs {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .thumb {{ max-height: 180px; max-width: 320px; border: 1px solid var(--border); border-radius: 4px; cursor: zoom-in; }}
  .thumb.overlay {{ border-color: #7f1d1d; }}
</style>
</head>
<body>
<h1>ANW Visual Diff Report</h1>
<div class="meta">Generated {ts}</div>
<div class="summary">
  <span class="s-chip s-identical">Identical: {n_identical}</span>
  <span class="s-chip s-similar">Similar: {n_similar}</span>
  <span class="s-chip s-changed">Changed: {n_changed}</span>
  <span class="s-chip s-unmatched">Unmatched: {n_unmatched}</span>
  {'<span class="s-chip s-error">Error: ' + str(n_error) + '</span>' if n_error else ''}
  <span style="color:var(--muted); font-size:0.8rem; align-self:center">Total: {n_total}</span>
</div>
<div class="results">
{rows_html}
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def collect_pairs(
    before: Path, after: Path
) -> list[tuple[Path, Path, str]]:
    """Return list of (before_path, after_path, name) pairs."""
    pairs = []
    if before.is_file() and after.is_file():
        pairs.append((before, after, before.name))
    elif before.is_dir() and after.is_dir():
        before_files = {p.name: p for p in sorted(before.glob("*.png"))}
        after_files = {p.name: p for p in sorted(after.glob("*.png"))}
        all_names = sorted(set(before_files) | set(after_files))
        for name in all_names:
            if name in before_files and name in after_files:
                pairs.append((before_files[name], after_files[name], name))
            elif name in before_files:
                pairs.append((before_files[name], before_files[name], name))
                # unmatched — same path
            else:
                pairs.append((after_files[name], after_files[name], name))
    else:
        print(f"ERROR: before and after must both be files or both be directories", file=sys.stderr)
        raise SystemExit(1)
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Visual diff two images or directories.")
    parser.add_argument("positional_before", nargs="?", type=Path, help="Before image/dir (positional)")
    parser.add_argument("positional_after", nargs="?", type=Path, help="After image/dir (positional)")
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "artifacts" / "validation" / "visual_diff_report.html")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--threshold", type=float, default=0.02, help="Per-pixel diff threshold [0,1]")
    parser.add_argument("--phash-cutoff", type=int, default=10, help="pHash distance cutoff for SIMILAR")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    before = args.before or args.positional_before
    after = args.after or args.positional_after

    if before is None or after is None:
        parser.print_help()
        raise SystemExit(1)

    pairs = collect_pairs(before, after)
    if not pairs:
        print("ERROR: no image pairs found", file=sys.stderr)
        raise SystemExit(1)

    results = []
    for before_path, after_path, name in pairs:
        if before_path == after_path:
            # Unmatched
            results.append({
                "name": name,
                "before_path": str(before_path) if before_path == before else "–",
                "after_path": str(after_path) if after_path == after else "–",
                "verdict": "UNMATCHED",
                "pixel_diff_pct": None, "mse": None, "psnr": None,
                "phash_distance": None, "phash_similar": None,
                "error": None,
                "_overlay_data_uri": None,
                "_before_data_uri": None,
                "_after_data_uri": None,
            })
        else:
            r = compare_pair(
                before_path, after_path,
                threshold=args.threshold,
                phash_cutoff=args.phash_cutoff,
            )
            results.append(r)
        if not args.quiet:
            v = results[-1]["verdict"]
            print(f"  [{v:10s}] {name}")

    # Write HTML
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_html_report(results))
    print(f"[visual_diff] HTML report: {args.out}")

    # Write JSON (strip data URIs)
    if args.json:
        json_results = [
            {k: v for k, v in r.items() if not k.startswith("_")}
            for r in results
        ]
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({"generated": datetime.now().isoformat(), "results": json_results}, f, indent=2)
        print(f"[visual_diff] JSON report:  {args.json}")

    n_changed = sum(1 for r in results if r["verdict"] == "CHANGED")
    raise SystemExit(0 if n_changed == 0 else 1)


if __name__ == "__main__":
    main()
