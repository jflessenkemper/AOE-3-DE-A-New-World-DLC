#!/usr/bin/env python3
"""Rebuild leader avatar PNGs from the high-resolution colour source images
in `art/ui/leaders/`, with NO duotone overlay.

Background
──────────
A previous batch run (the now-deprecated `tools/colorize_bw_portraits.py`)
ran `PIL.ImageOps.colorize()` over EVERY portrait that fell below a chroma
threshold. That threshold caught not just true B&W photographs but also
slightly-desaturated period oil paintings and sepia photographs that *did*
contain colour information. The duotone overlay produced uniformly orange
images for ~14 leaders.

This script does the right thing:

  1. Read the high-res source from art/ui/leaders/<source>
  2. Crop to a centred square (preserving the face)
  3. Resize to 256×256 with LANCZOS
  4. Optional: apply a light unsharp mask to compensate for resize blur
  5. Save as RGB (or RGBA if a roundel mask is requested) PNG to
     resources/images/icons/singleplayer/<target>.png

NO COLOR ALTERATION. Source colour is preserved verbatim. If the source is
genuinely B&W, the output is clean greyscale — never orange duotone.

Usage:
    python3 tools/rebuild_portraits.py            # rebuild all 14 leaders
    python3 tools/rebuild_portraits.py --dry-run  # show plan without writing
    python3 tools/rebuild_portraits.py --check    # chroma-audit current PNGs
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "art/ui/leaders"
DST_DIR = REPO / "resources/images/icons/singleplayer"
DDT_DIR = REPO / "art/ui/singleplayer"
TARGET = 256
DDT_SIZE = 128  # engine DDT size (128x128 BGRA32 = 65,560B)


@dataclass(frozen=True)
class PortraitJob:
    leader: str               # human-readable label
    source: str               # filename in art/ui/leaders/
    targets: tuple[str, ...]  # one or more target filenames in DST_DIR
    crop_y_pct: float = 0.0   # vertical bias for face crop: 0.0 = top half,
                              # 0.5 = exact centre, -0.2 = lift face higher.
                              # Most portrait paintings centre the face above
                              # the geometric centre, so we shave a bit from
                              # the bottom by default.
    crop_x_pct: float = 0.0   # horizontal bias for face crop. 0.0 = centred
                              # (default). +0.3 = shift the crop window right
                              # by 30% of the slack — use this for paintings
                              # where the subject stands to one side (e.g.
                              # multi-figure compositions like Hiawatha,
                              # where the central leader is on the right).
    zoom: float = 1.0         # post-square-crop zoom factor. 1.0 = full
                              # square (default). 1.2 = trim 1/1.2≈83% sub-
                              # rect from centre then rescale to 256×256
                              # (tighter face shot). 1.4 = significantly
                              # tighter — use when the source has lots of
                              # uniform/torso below the face.


# Mapping: art/ui/leaders/ source → resources/images/icons/singleplayer/ target.
# Built from the audit output (14 problem files) + their colour-rich sources.
JOBS: tuple[PortraitJob, ...] = (
    # 2026-05-26: Hiawatha source is a multi-figure council illustration —
    # central leader (with staff + headdress) stands on the right side of
    # the canvas. Centred crop captured the seated council; we now shift
    # the crop window right (+0.35) and lift it up (-0.25) to frame his
    # upper body, then zoom 1.15 for a tighter face shot.
    PortraitJob("Hiawatha (Haudenosaunee)", "hiawatha.png",
                ("cpai_avatar_haudenosaunee.png",
                 "cpai_avatar_haudenosaunee_hiawatha.png"),
                crop_y_pct=-0.25,
                crop_x_pct=0.35,
                zoom=1.15),
    # 2026-05-27: source is a 253×316 grainy historical photo with
    # a tall Finnish field cap dominating the top third. The previous
    # `crop_y_pct=-0.20, zoom=1.35` lifted the crop window UP which
    # kept the entire cap in frame and left the face cramped at the
    # vertical centre with collar+decorations below. User reported
    # the portrait looked "zoomed-out with blur around his face".
    # Tightening: shift crop window slightly DOWN past the upper cap
    # band and zoom in on the face. The source's variance peak is at
    # 51.5% vertical (slightly below centre), so a positive y bias
    # matches the actual subject placement.
    PortraitJob("Mannerheim (Finnish)", "mannerheim.png",
                ("cpai_avatar_finnish_mannerheim.png",
                 "cpai_avatar_anwfinnish.png"),
                crop_y_pct=0.05,
                zoom=1.55),
    # 2026-05-26: Papineau (French Canadians) job removed — that civ was
    # consolidated into Canadians Brock Revolution. The avatar files and
    # source remain on disk as orphan assets but aren't actively rebuilt.
    # 2026-05-26: Usman dan Fodio source is an Arabic manuscript page,
    # NOT a portrait. No facial portrait of Usman dan Fodio exists in
    # the historical record — Sokoto Caliphate tradition discouraged
    # figural portraiture of religious leaders, and the only widely-
    # available "Usman" images are manuscript-of-Bayan-Wujub-al-Hijra
    # pages. We render the manuscript as a placeholder so the avatar
    # slot isn't blank. If a verified historical portrait surfaces,
    # swap `usman_dan_fodio.png` in art/ui/leaders/ for it and re-run
    # this script.
    PortraitJob("Usman dan Fodio (Hausa)", "usman_dan_fodio.png",
                ("cpai_avatar_hausa.png",
                 "cpai_avatar_hausa_usman.png"),
                crop_y_pct=-0.05),
    PortraitJob("Diponegoro (Indonesians)", "diponegoro.png",
                ("cpai_avatar_indonesians_diponegoro.png",),
                crop_y_pct=-0.25,
                zoom=1.35),
    PortraitJob("Canales Rosillo (Rio Grande)", "canales_rosillo.png",
                ("cpai_avatar_rio_grande_canales_rosillo.png",),
                crop_y_pct=-0.05),
    PortraitJob("Cuza (Romanians)", "cuza.png",
                ("cpai_avatar_romanians_cuza.png",),
                crop_y_pct=-0.30,
                zoom=1.40),
    PortraitJob("Kruger (South Africans)", "kruger.png",
                ("cpai_avatar_south_africans_kruger.png",),
                crop_y_pct=-0.05),
    PortraitJob("Sam Houston (Texians)", "sam_houston.png",
                ("cpai_avatar_texians_sam_houston.png",),
                crop_y_pct=-0.20),
    PortraitJob("Menelik II (Ethiopians)", "menelik.png",
                ("cpai_avatar_ethiopians.png",
                 "cpai_avatar_ethiopians_menelik.png"),
                crop_y_pct=-0.05),
    # 2026-05-27: user feedback — Dutch Maurice and Napoleonic France
    # were displaying generic base-game stock art rather than proper
    # historical portraits. Both have high-quality classical paintings
    # available in art/ui/leaders/. Maurice (Frans Hals / Mierevelt
    # tradition) is portrait orientation with the face in the upper
    # third (a typical pose for a portrait of nobility — face above
    # the chest decoration, hand-on-hip / sword-at-hip composition).
    PortraitJob("Maurice of Nassau (Dutch)", "maurice.jpg",
                ("cpai_avatar_dutch_maurice.png",
                 "cpai_avatar_dutch.png",
                 "cpai_avatar_anwdutch.png"),
                crop_y_pct=-0.35,
                zoom=1.45),
    # David's "Napoleon in His Study" (1812) — full-body composition
    # ~370×600 portrait orientation. Face occupies roughly y=60-150 of
    # the 600-tall source (i.e. the top 10-25% band). The square crop
    # would naturally centre on the breeches/desk; we need an extreme
    # negative y_bias to lift the window into the face band AND a high
    # zoom factor to crop tight on the face once lifted.
    PortraitJob("Napoleon (Napoleonic France)", "napoleon.jpg",
                ("cpai_avatar_napoleonic_france_napoleon.png",
                 "cpai_avatar_napoleonic_france.png",
                 "cpai_avatar_anwnapoleonicfrance.png",
                 "cpai_avatar_french_napoleon.png"),
                crop_y_pct=-0.45,
                zoom=1.85),
)


def chroma_score(img: Image.Image) -> float:
    """Average chroma over the centre 50% of the image. >12 ≈ has colour."""
    arr = np.asarray(img.convert("RGB"))
    h, w = arr.shape[:2]
    centre = arr[h // 4:3 * h // 4, w // 4:3 * w // 4]
    return float(centre.max(2).astype(int).mean() - centre.min(2).astype(int).mean())


def square_crop(img: Image.Image, y_bias: float = 0.0,
                x_bias: float = 0.0) -> Image.Image:
    """Centre-crop to a square. y_bias shifts the crop window vertically:
    -0.5 = top of image, 0.0 = centre (default), +0.5 = bottom.
    x_bias shifts the crop window horizontally:
    -0.5 = left of image, 0.0 = centre (default), +0.5 = right.
    For most portraits a slight negative y_bias keeps the face in frame;
    x_bias is for multi-figure compositions where the subject stands
    asymmetrically (e.g. Hiawatha on the right of a council scene).
    """
    w, h = img.size
    side = min(w, h)
    centre_x = w // 2
    biased_x = int(centre_x + x_bias * (w - side))
    x = max(0, min(w - side, biased_x - side // 2))
    centre_y = h // 2
    biased_y = int(centre_y + y_bias * (h - side))
    y = max(0, min(h - side, biased_y - side // 2))
    return img.crop((x, y, x + side, y + side))


def process_one(job: PortraitJob, dry_run: bool = False) -> dict:
    src_path = SRC_DIR / job.source
    if not src_path.exists():
        return {"leader": job.leader, "status": "missing_source", "src": str(src_path)}

    src = Image.open(src_path).convert("RGB")
    src_chroma = chroma_score(src)

    cropped = square_crop(src, job.crop_y_pct, job.crop_x_pct)
    # Optional secondary tight-zoom: crop a centred sub-square of the square
    # crop, then scale to TARGET. The zoom value is the ratio of the OUTER
    # square edge to the INNER one — zoom=1.4 means the inner sub-rect is
    # 1/1.4 ≈ 71% of the outer edge, so the face gets ≈40% larger after
    # rescaling.
    if job.zoom > 1.0:
        cs = cropped.size[0]
        inner = max(1, int(round(cs / job.zoom)))
        offset = (cs - inner) // 2
        cropped = cropped.crop((offset, offset, offset + inner, offset + inner))
    resized = cropped.resize((TARGET, TARGET), Image.LANCZOS)

    # Light unsharp mask to recover detail lost in the LANCZOS downsample.
    final = resized.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=2))
    out_chroma = chroma_score(final)

    written: list[str] = []
    if not dry_run:
        DST_DIR.mkdir(parents=True, exist_ok=True)
        DDT_DIR.mkdir(parents=True, exist_ok=True)
        # Lazy-import the DDT writer so this script still runs (with
        # PNG-only output) if the cardextract module is missing.
        png_to_ddt = None
        try:
            sys.path.insert(0, str(REPO / "tools" / "cardextract"))
            from png_to_ddt import png_to_ddt as _png_to_ddt  # type: ignore
            png_to_ddt = _png_to_ddt
        except Exception:
            pass
        for target in job.targets:
            out = DST_DIR / target
            final.save(out, "PNG", optimize=True)
            written.append(str(out.name))
            # Also emit the matching art/ui/singleplayer/<target>.ddt so the
            # engine + WPF UI stay in sync. Without this, the deployed mod
            # serves stale portraits in the lobby + chat-bubble surfaces.
            if png_to_ddt is not None:
                ddt_out = DDT_DIR / (Path(target).stem + ".ddt")
                try:
                    png_to_ddt(out, ddt_out, size=DDT_SIZE)
                    written.append(str(ddt_out.name))
                except Exception as e:  # noqa: BLE001
                    print(f"  [warn] DDT write failed for {target}: {e}",
                          file=sys.stderr)

    return {
        "leader": job.leader,
        "status": "ok",
        "src_chroma": round(src_chroma, 1),
        "out_chroma": round(out_chroma, 1),
        "src_size": f"{src.size[0]}x{src.size[1]}",
        "wrote": written,
        "would_write": list(job.targets) if dry_run else [],
    }


def chroma_audit() -> int:
    """Print chroma scores for every cpai_avatar_*.png currently in DST_DIR.
    >12 = has colour, ≤12 = greyscale or duotone-overlay."""
    print(f"{'file':<55s} {'size':<11s} {'chroma':>7s}  status")
    print("-" * 90)
    bad = 0
    for p in sorted(DST_DIR.glob("cpai_avatar_*.png")):
        img = Image.open(p)
        c = chroma_score(img)
        flag = "OK     " if c > 12 else "BW/DUO"
        if c <= 12:
            bad += 1
        print(f"{p.name:<55s} {img.size[0]:>4d}x{img.size[1]:<5d} {c:7.2f}  {flag}")
    print(f"\n{bad} portraits below chroma threshold (12).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true",
                   help="Process and report without writing PNG output")
    p.add_argument("--check", action="store_true",
                   help="Audit chroma of all current cpai_avatar_*.png files")
    args = p.parse_args(argv)

    if args.check:
        return chroma_audit()

    print(f"{'leader':<32s} {'src→out chroma':<22s}  files")
    print("-" * 90)
    rows = []
    fail = 0
    for job in JOBS:
        r = process_one(job, dry_run=args.dry_run)
        rows.append(r)
        if r["status"] != "ok":
            fail += 1
            print(f"{r['leader']:<32s}  {r['status']:<20s}  {r.get('src','?')}")
            continue
        chroma_str = f"{r['src_chroma']:5.1f} → {r['out_chroma']:5.1f}"
        files = ", ".join(r["wrote"] or r["would_write"])
        marker = "  (dry)" if args.dry_run else ""
        print(f"{r['leader']:<32s}  {chroma_str:<22s}  {files}{marker}")

    print()
    if fail:
        print(f"FAILED {fail}/{len(JOBS)}")
        return 1
    print(f"OK {len(JOBS)}/{len(JOBS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
