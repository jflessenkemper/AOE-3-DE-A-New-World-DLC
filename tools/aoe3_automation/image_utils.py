"""Shared image utilities for AoE3 DE capture pipeline.

Provides:
  - avg_hash / hamming  — perceptual duplicate-detection helpers
  - is_splash_frame     — detects the "Asset Preloading" splash that fires
                          ~14-25 s after wait_for_in_game returns True

Calibration (2026-05-30):
  Feature used: centre-to-border brightness ratio on a 256×144 grayscale
  thumbnail.  Centre crop = middle fifth of each axis; border = top+bottom
  15% of rows.

  Splash positives (n=12, ANWBritish batch_01 + ANWBritish root):
    ratio range  9.10 – 12.94

  Real-screen negatives (n=16, lobby + Argentines/Aztecs/Inca in-game):
    ratio range  0.58 –  1.39

  Threshold chosen: ratio > 4.0
  Margin: lowest splash (9.10) is 2.28× above threshold;
          highest negative (1.39) is 2.88× below threshold.
  No false-positives, no false-negatives across the full calibration set.
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


def is_splash_frame(path: "str | Path") -> bool:
    """Return True if *path* looks like the "Asset Preloading" splash screen.

    Detection strategy: the splash has a bright central "globe" blob on an
    otherwise dark frame; real in-game/UI screens have no strong
    centre-vs-border brightness contrast.

    Computes centre-to-border mean-brightness ratio on a small grayscale
    thumbnail; ratio > 4.0 → splash.

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

    REAL_NEGATIVES = [
        _REPO / "artifacts/validation/visual_art/batch_01_ANWBritish/01_lobby.png",
        _REPO / "artifacts/validation/visual_art/ANWArgentines/01_diplomacy.png",
        _REPO / "artifacts/validation/visual_art/ANWArgentines/02_scoreboard.png",
        _REPO / "artifacts/validation/visual_art/ANWArgentines/03_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWArgentines/04_ally_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWArgentines/05_postgame.png",
        _REPO / "artifacts/validation/visual_art/ANWAztecs/01_diplomacy.png",
        _REPO / "artifacts/validation/visual_art/ANWAztecs/02_scoreboard.png",
        _REPO / "artifacts/validation/visual_art/ANWAztecs/03_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWAztecs/04_ally_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWAztecs/05_postgame.png",
        _REPO / "artifacts/validation/visual_art/ANWInca/01_diplomacy.png",
        _REPO / "artifacts/validation/visual_art/ANWInca/02_scoreboard.png",
        _REPO / "artifacts/validation/visual_art/ANWInca/03_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWInca/04_ally_homecity.png",
        _REPO / "artifacts/validation/visual_art/ANWInca/05_postgame.png",
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
