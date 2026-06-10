#!/usr/bin/env python3
"""Validate readiness site gallery images: eager loading, compact thumbs, no broken refs.

The unified release_readiness_site.html must show ALL per-civ surface gallery
images on page load (no lazy loading for visual_art/ gallery images). This
validator prevents regression to the 2026-05-12 bug where full-res PNGs (3-5 MB
each, ~1.8 GB total) were referenced as src with lazy loading — images stayed
blank until scroll.

The fix: gallery images use compact full/thumbs/*.webp as src with eager loading,
and full-res PNGs appear only in data-full attributes or <a href>.

Assertions:
  1. No visual_art/ gallery <img> has src ending in /full/<name>.png
  2. No visual_art/ gallery <img> carries loading="lazy"
  3. Every visual_art/ src referenced exists on disk
  4. Total byte size of all eagerly-referenced visual_art/ thumb files < 60 MB

(card_icons/ and unit_icons/ images MAY be lazy-loaded.)

Exit codes:
  0 — all checks pass (or site not built yet)
  1 — validation failures (broken refs, bad loading, wrong file types)
  2 — script error (bad HTML, missing dir, etc.)

Usage:
    python3 tools/validation/validate_readiness_site_images.py
"""
from __future__ import annotations

import argparse
import html.parser
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_FILE = _REPO_ROOT / "artifacts" / "validation" / "release_readiness_site.html"


class ImageExtractor(html.parser.HTMLParser):
    """Extract all <img> tags from HTML."""

    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            attr_dict = {k: v for k, v in attrs}
            self.images.append(attr_dict)


def parse_images(html_content: str) -> list[dict[str, str | None]]:
    """Extract all <img> tags from HTML string."""
    parser = ImageExtractor()
    parser.feed(html_content)
    return parser.images


def validate_readiness_site() -> int:
    """Validate the readiness site HTML.

    Returns 0 on pass, 1 on validation failure, 2 on script error.
    """
    # Check if site exists
    if not SITE_FILE.exists():
        print(f"Site not built yet: {SITE_FILE.relative_to(_REPO_ROOT)}")
        print("Skipping validation (exit 0).")
        return 0

    try:
        html_content = SITE_FILE.read_text(encoding="utf-8")
    except Exception as e:
        print(f"ERROR: Failed to read {SITE_FILE}: {e}", file=sys.stderr)
        return 2

    # Extract all images
    try:
        images = parse_images(html_content)
    except Exception as e:
        print(f"ERROR: Failed to parse HTML: {e}", file=sys.stderr)
        return 2

    # Filter to visual_art gallery images
    gallery_images = [
        img for img in images
        if img.get("src", "").startswith("visual_art/")
    ]

    if not gallery_images:
        print("No visual_art/ gallery images found in site.")
        return 2

    # Track results
    failures = []
    broken_refs = []
    total_bytes = 0

    # Check each gallery image
    for img_idx, img in enumerate(gallery_images):
        src = img.get("src", "")
        loading = img.get("loading", "")

        # Assertion 1: no full-res PNG as src
        if src.endswith("/full.png") or (
            "/full/" in src and src.endswith(".png")
        ):
            failures.append(
                f"Image {img_idx}: src references full-res PNG: {src}"
            )

        # Assertion 2: no lazy loading on visual_art gallery
        if loading == "lazy":
            failures.append(
                f"Image {idx}: visual_art/ gallery img has loading='lazy': {src}"
            )

        # Assertion 3: file exists
        file_path = _REPO_ROOT / "artifacts" / "validation" / src
        if not file_path.exists():
            broken_refs.append(src)
            failures.append(f"Image {img_idx}: broken ref (file not found): {src}")
        else:
            # Assertion 4: accumulate byte size for eager-loaded images
            if loading != "lazy":  # eager-loaded
                try:
                    total_bytes += file_path.stat().st_size
                except Exception as e:
                    failures.append(f"Image {img_idx}: failed to stat {src}: {e}")

    # Check total byte size
    total_mb = total_bytes / (1024 * 1024)
    if total_mb >= 60:
        failures.append(
            f"Total eager-loaded visual_art/ thumb size {total_mb:.1f} MB >= 60 MB limit"
        )

    # Print summary
    print(f"Gallery images checked: {len(gallery_images)}")
    print(f"Broken refs found: {len(broken_refs)}")
    print(f"Total eager-loaded byte size: {total_bytes:,} bytes ({total_mb:.1f} MB)")

    if failures:
        print(f"\nFAIL: {len(failures)} validation error(s):")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nPASS: all gallery images pass readiness checks.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    args = p.parse_args()
    return validate_readiness_site()


if __name__ == "__main__":
    raise SystemExit(main())
