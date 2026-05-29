#!/usr/bin/env python3
"""Crop and thumbnail post-processor for ANW visual captures.

Reads every manifest.json under the visual_art output tree, crops each
full/<label>.png to the regions declared in manifest.captures[].crops[],
and generates WebP thumbnails.

CLI:
    python3 -m tools.validation.crop_visual_captures \\
        [--civs ANWBritish,ANWFrench] \\
        [--rebuild-all]              \\
        [--input-root artifacts/validation/visual_art]

Idempotent: safe to run any number of times. Skips outputs whose mtime is
already >= the source PNG mtime, unless --rebuild-all is given.

Requires: Pillow (pip install Pillow)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow",
          file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
THUMB_MAX_WIDTH = 256
THUMB_QUALITY = 80


# ---------------------------------------------------------------------------
# Core crop/thumb logic
# ---------------------------------------------------------------------------

def _clamp_region(
    region: list[int],
    img_width: int,
    img_height: int,
    warnings: list[str],
    label: str,
    crop_name: str,
) -> tuple[int, int, int, int]:
    """Clamp [x0, y0, x1, y1] to image bounds; emit warning if clamping occurs."""
    x0, y0, x1, y1 = region
    cx0 = max(0, min(x0, img_width))
    cy0 = max(0, min(y0, img_height))
    cx1 = max(0, min(x1, img_width))
    cy1 = max(0, min(y1, img_height))
    if (cx0, cy0, cx1, cy1) != (x0, y0, x1, y1):
        warnings.append(
            f"{label}/{crop_name}: region {region} clamped to "
            f"({cx0},{cy0},{cx1},{cy1}) for {img_width}x{img_height} image"
        )
    return cx0, cy0, cx1, cy1


def _is_up_to_date(out_path: Path, src_path: Path) -> bool:
    """Return True if out_path exists with mtime >= src_path mtime."""
    if not out_path.exists():
        return False
    return out_path.stat().st_mtime >= src_path.stat().st_mtime


def _process_manifest(
    civ_dir: Path,
    *,
    rebuild_all: bool,
    warnings_out: list[str],
) -> tuple[int, int, int]:
    """Process one civ_dir/manifest.json.

    Returns (cropped, thumbed, skipped) counts for this manifest.
    """
    mf = civ_dir / "manifest.json"
    if not mf.exists():
        return 0, 0, 0

    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings_out.append(f"{civ_dir.name}: bad manifest JSON: {exc!r}")
        return 0, 0, 0

    captures = data.get("captures", [])
    crops_dir = civ_dir / "crops"
    thumbs_dir = civ_dir / "thumbs"
    crops_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    cropped = thumbed = skipped = 0

    for cap in captures:
        label = cap.get("label", "?")
        full_rel = cap.get("full_path", "")
        src_path = civ_dir / full_rel

        if not src_path.exists():
            warnings_out.append(
                f"{civ_dir.name}/{label}: source PNG missing: {src_path}"
            )
            continue

        # Load the source image once for all crops in this capture
        try:
            src_img = Image.open(src_path).convert("RGBA")
            img_w, img_h = src_img.size
        except Exception as exc:
            warnings_out.append(
                f"{civ_dir.name}/{label}: cannot open PNG: {exc!r}"
            )
            continue

        for crop_entry in cap.get("crops", []):
            crop_name = crop_entry.get("name", "?")
            crop_region = crop_entry.get("crop_region")
            crop_rel = crop_entry.get("crop_path", f"crops/{crop_name}.png")
            thumb_rel = crop_entry.get("thumb_path", f"thumbs/{crop_name}.webp")

            crop_out = civ_dir / crop_rel
            thumb_out = civ_dir / thumb_rel

            crop_done = _is_up_to_date(crop_out, src_path) and not rebuild_all
            thumb_done = _is_up_to_date(thumb_out, src_path) and not rebuild_all

            if crop_done and thumb_done:
                skipped += 2
                continue

            # Determine crop box
            if not crop_region or len(crop_region) != 4:
                warnings_out.append(
                    f"{civ_dir.name}/{label}/{crop_name}: missing/invalid crop_region"
                )
                continue

            box = _clamp_region(
                crop_region, img_w, img_h, warnings_out, label, crop_name
            )
            x0, y0, x1, y1 = box
            if x1 <= x0 or y1 <= y0:
                warnings_out.append(
                    f"{civ_dir.name}/{label}/{crop_name}: degenerate box after clamp"
                )
                continue

            try:
                cropped_img = src_img.crop(box)
            except Exception as exc:
                warnings_out.append(
                    f"{civ_dir.name}/{label}/{crop_name}: crop error: {exc!r}"
                )
                continue

            # Write crop PNG at native density (RGB, no alpha needed)
            if not crop_done:
                try:
                    crop_out.parent.mkdir(parents=True, exist_ok=True)
                    # Convert to RGB for PNG output (avoids palette issues)
                    cropped_img.convert("RGB").save(str(crop_out), format="PNG")
                    cropped += 1
                except Exception as exc:
                    warnings_out.append(
                        f"{civ_dir.name}/{label}/{crop_name}: save crop error: {exc!r}"
                    )
                    continue
            else:
                skipped += 1

            # Generate WebP thumbnail (max width 256px, preserve aspect ratio)
            if not thumb_done:
                try:
                    thumb_out.parent.mkdir(parents=True, exist_ok=True)
                    cw, ch = cropped_img.size
                    if cw > THUMB_MAX_WIDTH:
                        ratio = THUMB_MAX_WIDTH / cw
                        new_size = (THUMB_MAX_WIDTH, max(1, int(ch * ratio)))
                        thumb_img = cropped_img.resize(new_size, Image.LANCZOS)
                    else:
                        thumb_img = cropped_img.copy()
                    thumb_img.convert("RGB").save(
                        str(thumb_out), format="WEBP", quality=THUMB_QUALITY
                    )
                    thumbed += 1
                except Exception as exc:
                    warnings_out.append(
                        f"{civ_dir.name}/{label}/{crop_name}: thumb error: {exc!r}"
                    )
            else:
                skipped += 1

        # Close the source image to free memory
        src_img.close()

    return cropped, thumbed, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crop and thumbnail ANW visual captures from manifest.json files."
    )
    ap.add_argument("--civs", default=None,
                    help="Comma-separated civ tokens to process. Default: all.")
    ap.add_argument("--rebuild-all", action="store_true",
                    help="Rewrite all crops/thumbs even if outputs are current.")
    ap.add_argument("--input-root", default="artifacts/validation/visual_art",
                    help="Root directory containing per-civ subdirs (default: "
                         "artifacts/validation/visual_art).")
    args = ap.parse_args()

    input_root = Path(args.input_root)
    if not input_root.is_absolute():
        input_root = _REPO_ROOT / input_root

    if not input_root.exists():
        print(f"ERROR: input-root does not exist: {input_root}", file=sys.stderr)
        return 1

    # Enumerate civ dirs to process
    if args.civs:
        tokens = [c.strip() for c in args.civs.split(",") if c.strip()]
        # Host-perspective dirs
        civ_dirs: list[Path] = []
        for t in tokens:
            d = input_root / t
            if d.exists():
                civ_dirs.append(d)
            else:
                print(f"WARNING: dir not found for civ {t!r}: {d}", file=sys.stderr)
            # Also check allies dir
            ally_d = input_root / "allies" / t
            if ally_d.exists():
                civ_dirs.append(ally_d)
    else:
        # All subdirs with a manifest.json, including allies/<civ>/
        civ_dirs = [
            d for d in sorted(input_root.rglob("manifest.json"))
            if (d.parent / "full").exists()
        ]
        # rglob returns manifest.json files, we want their parent dirs
        civ_dirs = [mf.parent for mf in sorted(input_root.rglob("manifest.json"))
                    if (mf.parent / "full").exists()]

    if not civ_dirs:
        print("No manifest.json found under input-root. Nothing to process.",
              file=sys.stderr)
        return 0

    total_cropped = total_thumbed = total_skipped = 0
    all_warnings: list[str] = []

    for civ_dir in civ_dirs:
        cropped, thumbed, skipped = _process_manifest(
            civ_dir,
            rebuild_all=args.rebuild_all,
            warnings_out=all_warnings,
        )
        total_cropped += cropped
        total_thumbed += thumbed
        total_skipped += skipped

    for w in all_warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    print(
        f"cropped={total_cropped} thumbed={total_thumbed} "
        f"skipped={total_skipped} warnings={len(all_warnings)}"
    )
    return 0 if not all_warnings else 0  # warnings don't fail the tool


if __name__ == "__main__":
    sys.exit(main())
