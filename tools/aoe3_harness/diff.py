"""Screenshot diffing module — pixel-level visual regression for AoE3 UI captures.

Compares two PNG screenshots and produces a :class:`DiffResult` containing:
- percentage of changed pixels
- maximum colour delta across all channels
- bounding box of the changed region
- optional heatmap PNG highlighting changed areas in red

Usage::

    from tools.aoe3_harness.diff import compare_screenshots
    from pathlib import Path

    result = compare_screenshots(
        Path("before.png"),
        Path("after.png"),
        output_path=Path("heatmap.png"),   # optional
    )
    print(f"{result.pct_pixels_changed:.1%} pixels changed")
    if result.bbox:
        print(f"Changed region: {result.bbox}")   # (left, top, right, bottom)

CLI::

    python3 -m tools.aoe3_harness.cli diff before.png after.png [--output heatmap.png]

Requirements:
    Pillow (PIL) and numpy — both available in the repo Python environment.
    Install with: pip install Pillow numpy
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

# Named constants — changing these changes comparison sensitivity
CHANNEL_DELTA_THRESHOLD: int = 5
"""Per-channel absolute delta required to consider a pixel changed.

A pixel is "changed" if max(|R_before - R_after|, |G|, |B|) > this value.
Set to 5 to tolerate JPEG/PNG re-encoding artefacts without false positives.
"""

HEATMAP_CHANGED_COLOR: tuple[int, int, int] = (255, 0, 0)
"""RGB colour used for changed pixels in the heatmap output (red)."""

HEATMAP_UNCHANGED_COLOR: tuple[int, int, int] = (0, 0, 0)
"""RGB colour used for unchanged pixels in the heatmap output (black)."""


@dataclass
class DiffResult:
    """Result of a pixel-level screenshot comparison.

    Attributes:
        pct_pixels_changed: Fraction of pixels whose per-channel delta exceeds
            :data:`CHANNEL_DELTA_THRESHOLD` (0.0 = no change, 1.0 = 100% changed).
        max_color_delta: Maximum single-channel absolute delta found across all
            pixels (0–255).
        bbox: ``(left, top, right, bottom)`` pixel bounding box of the region
            containing all changed pixels, or ``None`` if no pixels changed.
            Follows PIL convention: right and bottom are exclusive (past-the-end).
        output_path: Path to the written heatmap PNG, or ``None`` if not requested.
    """

    pct_pixels_changed: float
    max_color_delta: int
    bbox: Optional[Tuple[int, int, int, int]]
    output_path: Optional[Path]


def compare_screenshots(
    before_path: Path,
    after_path: Path,
    output_path: Optional[Path] = None,
) -> DiffResult:
    """Compare two PNG screenshots pixel-by-pixel and return a :class:`DiffResult`.

    Loads both images as RGB, resizes ``after`` to match ``before`` if sizes
    differ (with a warning printed to stderr), then computes per-pixel RGB
    deltas.  A pixel is considered "changed" if any channel's absolute delta
    exceeds :data:`CHANNEL_DELTA_THRESHOLD`.

    If ``output_path`` is provided, writes a heatmap PNG: red where changed,
    black where unchanged.  Parent directories are created automatically.

    Args:
        before_path: Path to the baseline screenshot PNG (the reference).
        after_path:  Path to the new screenshot PNG to compare against the
                     baseline.
        output_path: Optional path for the heatmap PNG output.  If ``None``,
                     no heatmap is written and :attr:`DiffResult.output_path`
                     will be ``None``.

    Returns:
        A :class:`DiffResult` with comparison statistics.

    Raises:
        FileNotFoundError: if either input file does not exist.
        ImportError: if Pillow or numpy is not installed.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Pillow and numpy are required for screenshot diffing. "
            "Install with: pip install Pillow numpy"
        ) from exc

    if not before_path.exists():
        raise FileNotFoundError(f"before_path not found: {before_path}")
    if not after_path.exists():
        raise FileNotFoundError(f"after_path not found: {after_path}")

    img_before = Image.open(before_path).convert("RGB")
    img_after  = Image.open(after_path).convert("RGB")

    if img_before.size != img_after.size:
        print(
            f"[diff] WARNING: image size mismatch "
            f"(before={img_before.size}, after={img_after.size}) — "
            "resizing 'after' to match 'before'.",
            file=sys.stderr,
        )
        img_after = img_after.resize(img_before.size, Image.LANCZOS)

    # Convert to int32 arrays to avoid uint8 wrap-around in subtraction
    arr_before = np.asarray(img_before, dtype=np.int32)   # shape: (H, W, 3)
    arr_after  = np.asarray(img_after,  dtype=np.int32)

    delta          = np.abs(arr_before - arr_after)        # (H, W, 3)
    max_delta_map  = delta.max(axis=2)                     # (H, W) per-pixel max channel delta
    changed_mask   = max_delta_map > CHANNEL_DELTA_THRESHOLD  # (H, W) bool

    total_pixels  = arr_before.shape[0] * arr_before.shape[1]
    changed_count = int(changed_mask.sum())
    pct_changed   = changed_count / total_pixels if total_pixels > 0 else 0.0
    max_delta     = int(max_delta_map.max()) if total_pixels > 0 else 0

    # Compute bounding box of changed region
    bbox: Optional[Tuple[int, int, int, int]] = None
    if changed_count > 0:
        rows_with_changes = np.where(changed_mask.any(axis=1))[0]
        cols_with_changes = np.where(changed_mask.any(axis=0))[0]
        top    = int(rows_with_changes[0])
        bottom = int(rows_with_changes[-1]) + 1   # exclusive (PIL convention)
        left   = int(cols_with_changes[0])
        right  = int(cols_with_changes[-1]) + 1   # exclusive
        bbox   = (left, top, right, bottom)

    # Write heatmap if requested
    written_output: Optional[Path] = None
    if output_path is not None:
        h, w = changed_mask.shape
        heatmap_arr = np.zeros((h, w, 3), dtype=np.uint8)
        heatmap_arr[changed_mask]  = HEATMAP_CHANGED_COLOR
        heatmap_arr[~changed_mask] = HEATMAP_UNCHANGED_COLOR
        heatmap_img = Image.fromarray(heatmap_arr, mode="RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        heatmap_img.save(str(output_path))
        written_output = output_path

    return DiffResult(
        pct_pixels_changed=pct_changed,
        max_color_delta=max_delta,
        bbox=bbox,
        output_path=written_output,
    )
