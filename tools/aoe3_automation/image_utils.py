"""Shared image utilities for AoE3 DE capture pipeline.

Provides:
  - avg_hash / hamming  — perceptual duplicate-detection helpers
  - is_splash_frame     — detects EITHER of the two distinct AoE3 loading
                          screens that fire after wait_for_in_game returns
                          True (see below).  Used by the capture runner's
                          wait_for_splash_clear() poll so screenshots only
                          fire once BOTH loading screens have cleared.

There are two visually-distinct loading screens, and a capture that fires
during either one is a wrong/contaminated surface (the 2026-06-09 regression:
the HUD_SETTLE_CONFIRMED=3 speed path captured 03_hud and 04_homecity_panel
during the Asset-Preloading screen because only screen (1) was detected).

(1) "Globe splash"  — bright central globe blob on an otherwise dark frame.
    Calibration (2026-05-30): centre-to-border brightness ratio on a 256×144
    grayscale thumbnail. Centre crop = middle fifth of each axis; border =
    top+bottom 15% of rows.
      Splash positives (n=12): ratio 9.10 – 12.94
      Real-screen negatives (n=16): ratio 0.58 – 1.39
      Threshold: ratio > 4.0 (2.28× margin above, 2.88× below).

(2) "Asset Preloading (Beta)" — a DARK, blurry frame with a teal/cyan
    horizontal progress bar in the bottom strip.  Has NO bright central blob,
    so the globe-splash ratio test misses it entirely.  Detected instead by
    the fraction of teal pixels (G & B clearly above R) in the bottom strip.
    Calibration (2026-06-09, ANWBritish/full):
      Asset-preload positives (n=2): teal_frac 0.0444 – 0.0525
      Real-screen negatives (n=7, incl. equally-dark endgame/diplomacy at
        mean_lum ~34-37): teal_frac 0.0000 – 0.0065
      Threshold: teal_frac > 0.020 (2.2× margin above, 3.1× below).
    Note mean luminance alone does NOT separate these — the endgame and
    diplomacy screens are as dark as the loading screen; the teal bar is the
    discriminator.

is_splash_frame() returns True if EITHER screen is detected, so the runner
waits through both before capturing.
"""
from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image as _PILImage  # type: ignore
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# ---------------------------------------------------------------------------
# avg_hash / hamming (mirrors logic formerly inline in
# tools/validation/build_release_readiness_site.py)
# ---------------------------------------------------------------------------

def avg_hash(path: "str | Path") -> "int | None":
    """16×16 grayscale average-hash of *path* as a 256-bit integer.

    Returns None on any failure (missing file, PIL unavailable, decode error).
    """
    if not _PIL_AVAILABLE:
        return None
    path = Path(path)
    try:
        with _PILImage.open(path) as img:
            img = img.convert("L").resize((16, 16), _PILImage.LANCZOS)
            try:
                pixels = list(img.getdata())  # type: ignore[attr-defined]
            except AttributeError:
                # Pillow ≥ 14 removes getdata(); use tobytes() instead
                pixels = list(img.tobytes())
            mean = sum(pixels) / len(pixels)
            bits = 0
            for p in pixels:
                bits = (bits << 1) | (1 if p > mean else 0)
            return bits
    except Exception:
        return None


def hamming(a: "int | None", b: "int | None") -> int:
    """Hamming distance between two 256-bit avg-hashes.

    Returns 999 if either argument is None (treat as maximally different).
    """
    if a is None or b is None:
        return 999
    return bin(a ^ b).count("1")


# ---------------------------------------------------------------------------
# Splash-frame detection
# ---------------------------------------------------------------------------

# Calibration constants — see module docstring for derivation.
_SPLASH_THUMB_W = 256
_SPLASH_THUMB_H = 144
_SPLASH_CENTRE_FRACTION = 0.20   # half-width of centre crop as fraction of axis
_SPLASH_BORDER_FRACTION = 0.15   # top+bottom border height fraction
# Ratio threshold: splash ≥ 9.1, real ≤ 1.4 — use 4.0 for a 2.28× margin
_SPLASH_CENTRE_BORDER_RATIO_THRESHOLD = 4.0

# Asset-Preloading-screen teal-bar detection — see module docstring (screen 2).
# Bottom strip = rows 82%..97%, cols 15%..85% (where the progress bar sits).
# A pixel is 'teal' if green and blue are clearly above red and reasonably
# bright.
#
# IMPORTANT (2026-06-10): the old "overall teal fraction > 0.020" test
# false-positived on the real home-city panel, whose harbour WATER fills the
# whole bottom strip with teal (overall_teal≈0.43, 10x the splash's ≈0.05) and
# was wrongly flagged as a loading screen by validate_no_loading_screen_
# contamination. The distinguishing signal is SHAPE, not amount: the real
# Asset-Preloading progress bar is a THIN bright horizontal band confined to the
# bottom few rows of the strip (≈5 of 40 resized rows; all rows above it are
# teal-free), whereas scene water spreads teal across most rows of the strip.
# We therefore require a bright teal peak row AND that teal occupies only a
# small fraction of the strip's rows (a band, not a fill).
_PRELOAD_PEAK_ROW_TEAL_MIN = 0.20    # peak row must be clearly teal (bar present)
_PRELOAD_TEAL_ROW_FRACTION_MAX = 0.30  # <=30% of strip rows teal → thin band, not water fill
_PRELOAD_ROW_TEAL_MIN = 0.10         # a row counts as "teal" above this fraction


def is_globe_splash_frame(path: "str | Path") -> bool:
    """Return True if *path* is the bright-globe loading splash (screen 1).

    The splash has a bright central "globe" blob on an otherwise dark frame;
    real in-game/UI screens have no strong centre-vs-border brightness
    contrast.  Computes centre-to-border mean-brightness ratio on a small
    grayscale thumbnail; ratio > 4.0 → splash.

    Returns False (not-a-splash) on any error so callers degrade safely.
    """
    if not _PIL_AVAILABLE:
        return False
    try:
        import numpy as _np  # type: ignore
        with _PILImage.open(path) as img:
            thumb = img.convert("L").resize(
                (_SPLASH_THUMB_W, _SPLASH_THUMB_H), _PILImage.LANCZOS
            )
            arr = _np.array(thumb, dtype=_np.float32)

        h, w = arr.shape
        # Centre crop
        cx, cy = w // 2, h // 2
        rw = int(w * _SPLASH_CENTRE_FRACTION)
        rh = int(h * _SPLASH_CENTRE_FRACTION)
        centre = arr[cy - rh: cy + rh, cx - rw: cx + rw]

        # Top + bottom border rows
        bh = max(1, int(h * _SPLASH_BORDER_FRACTION))
        border = _np.concatenate([arr[:bh, :].ravel(), arr[-bh:, :].ravel()])

        border_mean = float(border.mean()) if border.size > 0 else 1.0
        if border_mean < 1.0:
            border_mean = 1.0
        centre_mean = float(centre.mean()) if centre.size > 0 else 0.0
        ratio = centre_mean / border_mean

        return ratio > _SPLASH_CENTRE_BORDER_RATIO_THRESHOLD
    except Exception:
        return False


def is_asset_preloading_frame(path: "str | Path") -> bool:
    """Return True if *path* is the "Asset Preloading (Beta)" screen (screen 2).

    This loading screen is dark and blurry with NO bright central blob, so the
    globe-splash ratio test misses it.  Its distinctive feature is a teal/cyan
    horizontal progress *bar* in the bottom strip — a THIN bright band confined
    to the bottom few rows.  We must not confuse it with the real home-city
    panel, whose harbour water also reads teal but FILLS the whole strip.  So we
    require both: (1) a clearly-teal peak row (the bar exists) and (2) teal
    confined to a small fraction of the strip's rows (a band, not a water fill).

    Returns False on any error so callers degrade safely.
    """
    if not _PIL_AVAILABLE:
        return False
    try:
        import numpy as _np  # type: ignore
        with _PILImage.open(path) as img:
            small = img.convert("RGB").resize((480, 270), _PILImage.LANCZOS)
            arr = _np.asarray(small, dtype=_np.float32)
        h, w, _c = arr.shape
        strip = arr[int(h * 0.82): int(h * 0.97), int(w * 0.15): int(w * 0.85)]
        r, g, b = strip[..., 0], strip[..., 1], strip[..., 2]
        teal = (g > r + 25) & (b > r + 25) & (g > 90) & (b > 90)
        row_frac = teal.mean(axis=1)                       # teal fraction per strip row
        if row_frac.size == 0:
            return False
        peak = float(row_frac.max())                       # brightest teal row
        n_teal_rows = int((row_frac > _PRELOAD_ROW_TEAL_MIN).sum())
        teal_row_fraction = n_teal_rows / float(row_frac.size)
        # Real progress bar: bright peak AND thin band. Home-city water: bright
        # peak BUT band spans most rows → teal_row_fraction high → rejected.
        return (peak > _PRELOAD_PEAK_ROW_TEAL_MIN
                and teal_row_fraction <= _PRELOAD_TEAL_ROW_FRACTION_MAX)
    except Exception:
        return False


def is_splash_frame(path: "str | Path") -> bool:
    """Return True if *path* is EITHER AoE3 loading screen (see module docstring).

    True if the bright-globe splash (screen 1) OR the Asset-Preloading screen
    (screen 2) is detected.  Used by the capture runner's wait_for_splash_clear
    so screenshots only fire once both loading screens have cleared.

    Returns False (not-a-loading-screen) on any error so callers degrade safely.
    """
    return is_globe_splash_frame(path) or is_asset_preloading_frame(path)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path

    _REPO = Path(__file__).resolve().parents[2]  # repo root

    SPLASH_POSITIVES = [
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/02_hud_default.png",
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/03_scoreboard.png",
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/04_diplomacy.png",
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/05_homecity_panel.png",
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/06_esc_menu.png",
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/07_endgame_screen.png",
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/07a_abandon_screen.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/01_diplomacy.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/02_scoreboard.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/03_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/04_ally_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/05_postgame.png",
    ]

    # Asset-Preloading screen (screen 2) positives — the 2026-06-09 regression
    # frames that the globe-splash test missed. is_splash_frame must catch them.
    SPLASH_POSITIVES += [
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/_assetpreload_03_hud.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/_assetpreload_04_homecity_panel.png",
    ]

    # Real-screen negatives.  The live wait_for_splash_clear poll only ever
    # probes full-screen 1920×1080 gamescope frames, so the negative set must
    # be FULL-RESOLUTION real frames — NOT the 256px portrait thumbnails that
    # used to live at the civ-dir root (those are out-of-domain: e.g. the
    # Argentine portrait's light-blue flag trips the teal-bar test even though
    # such a thumbnail is never fed to the live detector).  These are the
    # confirmed-real ANWBritish/full frames, spanning bright in-game HUD,
    # menus, and equally-dark endgame/diplomacy screens.
    REAL_NEGATIVES = [
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/01_lobby.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/05_tech_tree.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/07_scoreboard.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/08_esc_menu.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/10_ai_homecity.png",
        # Equally-dark real screens that must NOT trip the teal-bar test.
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/09_endgame.png",
        _REPO / "artifacts/validation/visual_art/ANWBritish/full/06_diplomacy.png",
    ]

    failures = 0
    total = 0

    print("=== Splash positives (expect: all True) ===")
    for p in SPLASH_POSITIVES:
        if not p.exists():
            print(f"  SKIP (missing) {p.name}")
            continue
        result = is_splash_frame(p)
        status = "PASS" if result else "FAIL"
        if not result:
            failures += 1
        total += 1
        print(f"  {status}  {p.parent.name}/{p.name}  (splash={result})")

    print("\n=== Real negatives (expect: all False) ===")
    for p in REAL_NEGATIVES:
        if not p.exists():
            print(f"  SKIP (missing) {p.name}")
            continue
        result = is_splash_frame(p)
        status = "PASS" if not result else "FAIL"
        if result:
            failures += 1
        total += 1
        print(f"  {status}  {p.parent.name}/{p.name}  (splash={result})")

    print()
    if failures == 0:
        print(f"PASS — {total}/{total} classifications correct.")
    else:
        print(f"FAIL — {failures} misclassification(s) out of {total}.")
        sys.exit(1)
