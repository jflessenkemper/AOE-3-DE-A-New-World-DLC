#!/usr/bin/env python3
"""repaint_flags.py — Historically-accurate flag overhaul for ANW civs.

Preserves the wave shading of the existing flag (extracted from the
grayscale luminance of the source) and repaints heraldry on top.

Targets:
  - ANWBritish    -> Cross of St George (Elizabeth I)
  - ANWRussians   -> Double-headed eagle on gold (Ivan IV)
  - ANWEthiopians -> Red/yellow/green tricolor + Lion of Judah (Menelik II)
  - ANWIndians    -> Bhagwa saffron field (Shivaji)

Touches all three live surfaces per civ:
  - resources/images/icons/flags/Flag_<Civ>.png         (lobby)
  - resources/images/icons/flags/postgame_flag_<civ>.png
  - resources/images/icons/flags/flag_hc_<civ>.png       (HC button)
"""
from __future__ import annotations
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageChops

FLAGS_DIR = Path("resources/images/icons/flags")


# ---------- wave-shading helpers ----------

def extract_wave_mask(src_png: Path) -> Image.Image:
    """Return a grayscale wave-fold mask that ignores the source's
    heraldic pattern and preserves only the soft cloth-fold gradient.

    Strategy:
      1. Convert to luminance.
      2. Heavily blur (radius = ~min_dim/6) so colored heraldry blurs
         out into a smooth gradient.
      3. Normalize to [200..255] — subtle, just enough to show folds
         without darkening the flat-color repaint.
    """
    base = Image.open(src_png).convert("L")
    w, h = base.size
    radius = max(20, min(w, h) // 6)
    blurred = base.filter(ImageFilter.GaussianBlur(radius=radius))
    # Re-normalize so blur output spans full [200..255]
    lo, hi = blurred.getextrema()
    if hi <= lo:
        return Image.new("L", base.size, 255)
    span = hi - lo
    pixels = bytearray(blurred.tobytes())
    for i, v in enumerate(pixels):
        norm = (v - lo) / span  # 0..1
        pixels[i] = int(200 + norm * 55)  # map to 200..255
    return Image.frombytes("L", base.size, bytes(pixels))


def apply_wave(flat: Image.Image, mask: Image.Image) -> Image.Image:
    """Multiply flat-color flag by the wave-shading mask. Preserves alpha.

    Pure-PIL implementation: per-channel multiply where the mask is
    treated as a 0..1 factor. ImageChops.multiply takes 0..255 inputs,
    so we feed the channel and mask directly — at 255 mask the channel
    is unchanged; at 140 mask the channel becomes ~55% of its value."""
    r, g, b, a = flat.split()
    # Ensure mask is mode L and same size
    if mask.size != flat.size:
        mask = mask.resize(flat.size, Image.LANCZOS)
    if mask.mode != "L":
        mask = mask.convert("L")
    r2 = ImageChops.multiply(r, mask)
    g2 = ImageChops.multiply(g, mask)
    b2 = ImageChops.multiply(b, mask)
    return Image.merge("RGBA", (r2, g2, b2, a))


# ---------- flag designs ----------

def design_st_george(size: tuple[int, int]) -> Image.Image:
    """Red Greek cross (1/5 width arms) on white field."""
    w, h = size
    img = Image.new("RGBA", size, (250, 250, 250, 255))
    d = ImageDraw.Draw(img)
    red = (200, 30, 30, 255)
    arm = max(8, h // 5)
    # Horizontal bar
    d.rectangle([0, (h - arm) // 2, w, (h + arm) // 2], fill=red)
    # Vertical bar
    d.rectangle([(w - arm) // 2, 0, (w + arm) // 2, h], fill=red)
    return img


def design_russian_eagle(size: tuple[int, int]) -> Image.Image:
    """Black double-headed eagle silhouette on gold (Tsardom of Russia,
    Ivan IV era). Stylized heraldic silhouette: outstretched diagonal
    wings, two crowned heads in profile facing outward, central torso,
    red shield with gold cross.
    """
    w, h = size
    gold = (215, 175, 35, 255)  # heraldic or
    img = Image.new("RGBA", size, gold)
    d = ImageDraw.Draw(img)

    black = (20, 20, 20, 255)
    red_shield = (180, 25, 25, 255)

    cx, cy = w // 2, int(h * 0.55)
    s = h  # scale base

    # ----- Wings: large outstretched, slightly down-curved -----
    # Each wing is a polygon: from upper-inner shoulder, out to wing-tip,
    # back to lower-inner. Drawn first so body overlaps cleanly.
    wing_span = int(s * 0.42)  # horizontal reach from center
    wing_thick = int(s * 0.18)
    sh_x = int(s * 0.08)        # inner shoulder offset from cx
    sh_y_top = cy - int(s * 0.18)
    sh_y_bot = cy + int(s * 0.06)
    tip_y_top = cy - int(s * 0.04)
    tip_y_bot = cy + int(s * 0.16)
    # Left wing
    d.polygon([
        (cx - sh_x, sh_y_top),               # inner-upper shoulder
        (cx - wing_span, tip_y_top),         # wing tip upper
        (cx - wing_span + int(s * 0.04), tip_y_bot),  # wing tip lower
        (cx - sh_x, sh_y_bot),               # inner-lower shoulder
    ], fill=black)
    # Right wing (mirror)
    d.polygon([
        (cx + sh_x, sh_y_top),
        (cx + wing_span, tip_y_top),
        (cx + wing_span - int(s * 0.04), tip_y_bot),
        (cx + sh_x, sh_y_bot),
    ], fill=black)

    # ----- Body / torso -----
    body_w = int(s * 0.10)
    body_top = cy - int(s * 0.16)
    body_bot = cy + int(s * 0.22)
    d.rectangle([cx - body_w, body_top, cx + body_w, body_bot], fill=black)
    # Bottom of body tapers to tail
    d.polygon([
        (cx - body_w, body_bot - 2),
        (cx + body_w, body_bot - 2),
        (cx + int(s * 0.04), body_bot + int(s * 0.06)),
        (cx - int(s * 0.04), body_bot + int(s * 0.06)),
    ], fill=black)

    # ----- Necks: short stalks rising from shoulders to head positions -----
    neck_w = int(s * 0.025)
    head_offset_x = int(s * 0.10)
    neck_top_y = cy - int(s * 0.26)
    # Left neck
    d.polygon([
        (cx - int(s * 0.02), body_top + 2),
        (cx - int(s * 0.08), body_top + 2),
        (cx - head_offset_x - neck_w, neck_top_y),
        (cx - head_offset_x + neck_w, neck_top_y),
    ], fill=black)
    # Right neck
    d.polygon([
        (cx + int(s * 0.02), body_top + 2),
        (cx + int(s * 0.08), body_top + 2),
        (cx + head_offset_x + neck_w, neck_top_y),
        (cx + head_offset_x - neck_w, neck_top_y),
    ], fill=black)

    # ----- Heads: profile facing outward, with beak -----
    head_r = int(s * 0.05)
    head_y = neck_top_y - head_r
    # Left head (profile facing left)
    d.ellipse([cx - head_offset_x - head_r, head_y - head_r,
               cx - head_offset_x + head_r, head_y + head_r], fill=black)
    # Left beak — triangle pointing left
    d.polygon([
        (cx - head_offset_x - head_r + 1, head_y),
        (cx - head_offset_x - head_r - int(s * 0.04), head_y - 1),
        (cx - head_offset_x - head_r - int(s * 0.025), head_y + int(s * 0.018)),
    ], fill=black)
    # Right head (profile facing right)
    d.ellipse([cx + head_offset_x - head_r, head_y - head_r,
               cx + head_offset_x + head_r, head_y + head_r], fill=black)
    # Right beak
    d.polygon([
        (cx + head_offset_x + head_r - 1, head_y),
        (cx + head_offset_x + head_r + int(s * 0.04), head_y - 1),
        (cx + head_offset_x + head_r + int(s * 0.025), head_y + int(s * 0.018)),
    ], fill=black)

    # ----- Crowns on each head: small Russian-style 5-point crown -----
    def draw_crown(center_x: int, base_y: int):
        cw = int(s * 0.07)
        ch = int(s * 0.03)
        # Crown base bar
        d.rectangle([center_x - cw // 2, base_y - ch,
                     center_x + cw // 2, base_y], fill=black)
        # 3 points
        for off in (-cw // 3, 0, cw // 3):
            d.polygon([
                (center_x + off - ch // 2, base_y - ch),
                (center_x + off + ch // 2, base_y - ch),
                (center_x + off, base_y - ch - int(s * 0.025)),
            ], fill=black)
    draw_crown(cx - head_offset_x, head_y - head_r)
    draw_crown(cx + head_offset_x, head_y - head_r)
    # Imperial crown above center
    draw_crown(cx, head_y - head_r - int(s * 0.01))

    # ----- Central shield: red with gold cross (St George of Moscow) -----
    sh_w, sh_h = int(s * 0.11), int(s * 0.15)
    sh_top = cy - int(s * 0.04)
    # Shield = rectangle with pointed bottom
    d.rectangle([cx - sh_w // 2, sh_top,
                 cx + sh_w // 2, sh_top + sh_h - int(s * 0.03)],
                fill=red_shield)
    d.polygon([
        (cx - sh_w // 2, sh_top + sh_h - int(s * 0.03)),
        (cx + sh_w // 2, sh_top + sh_h - int(s * 0.03)),
        (cx, sh_top + sh_h + int(s * 0.015)),
    ], fill=red_shield)
    # Gold cross on shield (vertical + horizontal bars)
    cross_arm = max(2, sh_w // 6)
    d.rectangle([cx - cross_arm // 2, sh_top + 3,
                 cx + cross_arm // 2, sh_top + sh_h - int(s * 0.025) - 3],
                fill=gold)
    d.rectangle([cx - sh_w // 2 + 3, cy + int(s * 0.025) - cross_arm // 2,
                 cx + sh_w // 2 - 3, cy + int(s * 0.025) + cross_arm // 2],
                fill=gold)

    # ----- Talons / claws at base of body -----
    talon_y = body_bot + int(s * 0.06)
    talon_w = int(s * 0.025)
    for off in (-int(s * 0.05), -int(s * 0.02), int(s * 0.02), int(s * 0.05)):
        d.polygon([
            (cx + off - talon_w // 2, talon_y),
            (cx + off + talon_w // 2, talon_y),
            (cx + off, talon_y + int(s * 0.03)),
        ], fill=black)

    return img


def design_ethiopian_lion_tricolor(size: tuple[int, int]) -> Image.Image:
    """Red/yellow/green horizontal tricolor — historically the
    Ethiopian Empire flag as adopted by Menelik II in 1897.

    Note: the Conquering Lion of Judah was added to the central band
    by Haile Selassie in 1914; for Menelik II's reign (1889–1913) the
    plain tricolor is canonical. We add a small Imperial seal disc
    (gold sun) on the yellow band for distinguishability and visual
    interest, but skip an amateur procedural lion.
    """
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 255))
    d = ImageDraw.Draw(img)

    band_h = h // 3
    red = (200, 30, 30, 255)
    yellow = (240, 200, 30, 255)
    green = (30, 130, 50, 255)
    d.rectangle([0, 0, w, band_h], fill=red)
    d.rectangle([0, band_h, w, 2 * band_h], fill=yellow)
    d.rectangle([0, 2 * band_h, w, h], fill=green)

    # Imperial seal: gold disc with thin dark border on the yellow band
    seal_cx, seal_cy = w // 2, h // 2
    seal_r = int(h * 0.16)
    border = (90, 50, 12, 255)   # dark brown
    inner = (235, 200, 60, 255)  # bright gold
    d.ellipse([seal_cx - seal_r - 2, seal_cy - seal_r - 2,
               seal_cx + seal_r + 2, seal_cy + seal_r + 2], fill=border)
    d.ellipse([seal_cx - seal_r, seal_cy - seal_r,
               seal_cx + seal_r, seal_cy + seal_r], fill=inner)
    # Inner Ethiopian-style cross (Lalibela cross simplified)
    cross_w = max(3, int(h * 0.025))
    arm = int(seal_r * 0.7)
    d.rectangle([seal_cx - cross_w // 2, seal_cy - arm,
                 seal_cx + cross_w // 2, seal_cy + arm], fill=border)
    d.rectangle([seal_cx - arm, seal_cy - cross_w // 2,
                 seal_cx + arm, seal_cy + cross_w // 2], fill=border)
    # Diagonal "rays" — short diagonal bars (Ethiopian cross style)
    diag_arm = int(seal_r * 0.5)
    for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        d.line([
            (seal_cx, seal_cy),
            (seal_cx + sx * diag_arm, seal_cy + sy * diag_arm)
        ], fill=border, width=cross_w)

    return img

    # ---- Lion silhouette (dark brown, almost black) ----
    lion = (60, 30, 12, 255)
    cx, cy = w // 2, int(h * 0.55)

    # Body: long horizontal ellipse, lion faces RIGHT
    body_w = int(h * 0.32)   # half-width (so full width = 0.64h)
    body_h = int(h * 0.07)   # half-height
    body_top = cy - body_h
    body_bot = cy + body_h
    d.ellipse([cx - body_w, body_top, cx + body_w, body_bot], fill=lion)

    # Hindquarter haunch — slightly bigger oval at left
    haunch_w = int(h * 0.10)
    haunch_h = int(h * 0.10)
    d.ellipse([cx - body_w - haunch_w // 2, cy - haunch_h,
               cx - body_w + haunch_w, cy + haunch_h], fill=lion)

    # ---- Legs: 4 legs, slightly staggered for a walking pose ----
    leg_h = int(h * 0.13)
    leg_w = max(3, int(h * 0.025))
    leg_top_y = body_bot - 2
    # x positions: front-far, front-near, rear-near, rear-far
    leg_xs = [
        cx + int(body_w * 0.70),   # front-far (right side, lifted)
        cx + int(body_w * 0.45),   # front-near
        cx - int(body_w * 0.45),   # rear-near
        cx - int(body_w * 0.70),   # rear-far
    ]
    leg_offsets_y = [0, -int(h * 0.02), 0, -int(h * 0.015)]  # walking pose
    for lx, lyoff in zip(leg_xs, leg_offsets_y):
        d.rectangle([lx - leg_w // 2, leg_top_y + lyoff,
                     lx + leg_w // 2, leg_top_y + leg_h], fill=lion)
        # Paw at bottom
        d.ellipse([lx - leg_w, leg_top_y + leg_h - leg_w,
                   lx + leg_w, leg_top_y + leg_h + leg_w // 2], fill=lion)

    # ---- Tail — curves up from the back-left ----
    tail_base_x = cx - body_w - int(h * 0.02)
    tail_base_y = cy - body_h // 2
    # Curving tail: a bezier-ish polygon
    d.polygon([
        (tail_base_x, tail_base_y),
        (tail_base_x - int(h * 0.06), tail_base_y - int(h * 0.04)),
        (tail_base_x - int(h * 0.10), tail_base_y - int(h * 0.12)),
        (tail_base_x - int(h * 0.06), tail_base_y - int(h * 0.16)),
        (tail_base_x - int(h * 0.02), tail_base_y - int(h * 0.10)),
        (tail_base_x - int(h * 0.04), tail_base_y - int(h * 0.06)),
        (tail_base_x, tail_base_y - int(h * 0.02)),
    ], fill=lion)
    # Tail tuft at top
    d.ellipse([tail_base_x - int(h * 0.08), tail_base_y - int(h * 0.20),
               tail_base_x - int(h * 0.02), tail_base_y - int(h * 0.14)],
              fill=lion)

    # ---- Mane: large circle covering shoulders on right side ----
    mane_cx = cx + body_w - int(h * 0.04)
    mane_cy = cy - int(h * 0.04)
    mane_r = int(h * 0.13)
    # Draw a slightly bumpy mane edge by overlapping a few circles
    for off_x, off_y, rr in [
        (0, 0, mane_r),
        (-int(h * 0.04), -int(h * 0.04), int(mane_r * 0.85)),
        (-int(h * 0.06), int(h * 0.02), int(mane_r * 0.80)),
        (int(h * 0.02), -int(h * 0.06), int(mane_r * 0.75)),
        (int(h * 0.03), int(h * 0.04), int(mane_r * 0.70)),
    ]:
        d.ellipse([mane_cx + off_x - rr, mane_cy + off_y - rr,
                   mane_cx + off_x + rr, mane_cy + off_y + rr], fill=lion)

    # ---- Head: oval emerging from right edge of mane, snout pointing right ----
    head_cx = mane_cx + int(h * 0.07)
    head_cy = mane_cy + int(h * 0.01)
    head_w = int(h * 0.06)
    head_h = int(h * 0.05)
    d.ellipse([head_cx - head_w, head_cy - head_h,
               head_cx + head_w, head_cy + head_h], fill=lion)
    # Small ear on top
    d.polygon([
        (head_cx - head_w // 2, mane_cy - mane_r // 2),
        (head_cx - head_w // 4, mane_cy - mane_r // 2 - int(h * 0.03)),
        (head_cx, mane_cy - mane_r // 2 + 2),
    ], fill=lion)

    # ---- Cross-bearing processional staff at lion's shoulder ----
    # Held diagonally, leaning back over shoulder
    staff_color = lion
    staff_w = max(2, int(h * 0.012))
    # Staff base (at shoulder)
    sb_x = cx + int(body_w * 0.30)
    sb_y = body_top + int(h * 0.01)
    # Staff top (up and to the left, leaning back)
    st_x = sb_x - int(h * 0.18)
    st_y = sb_y - int(h * 0.32)
    d.line([(sb_x, sb_y), (st_x, st_y)], fill=staff_color, width=staff_w)
    # Cross at top — Ethiopian-style: horizontal bar + small upper bar
    bar_w = int(h * 0.06)
    # Main crossbar
    d.line([(st_x - bar_w, st_y + int(h * 0.01)),
            (st_x + bar_w, st_y + int(h * 0.01))],
           fill=staff_color, width=staff_w)
    # Upper crossbar (shorter)
    d.line([(st_x - bar_w // 2, st_y - int(h * 0.025)),
            (st_x + bar_w // 2, st_y - int(h * 0.025))],
           fill=staff_color, width=staff_w)
    # Extend staff above top crossbar a little
    d.line([(st_x, st_y), (st_x, st_y - int(h * 0.05))],
           fill=staff_color, width=staff_w)

    # ---- Pennant (small banner hanging from staff) ----
    pen_top_y = st_y + int(h * 0.04)
    pen_bot_y = pen_top_y + int(h * 0.08)
    pen_left_x = st_x - int(h * 0.10)
    d.polygon([
        (st_x - 1, pen_top_y),
        (pen_left_x, pen_top_y + int(h * 0.02)),
        (pen_left_x + int(h * 0.02), (pen_top_y + pen_bot_y) // 2),
        (pen_left_x, pen_bot_y - int(h * 0.02)),
        (st_x - 1, pen_bot_y),
    ], fill=(180, 25, 25, 255))  # red pennant

    return img


def design_bhagwa(size: tuple[int, int]) -> Image.Image:
    """Saffron field (Bhagwa) for Shivaji's Maratha Empire.
    Optional small white sun emblem for distinguishability."""
    w, h = size
    saffron = (235, 130, 35, 255)
    img = Image.new("RGBA", size, saffron)
    d = ImageDraw.Draw(img)

    # Small white sun-disc (Shivaji's seal mentions the sun) in upper
    # hoist quadrant — keeps the design readable vs a plain orange field
    sun_cx = int(w * 0.30)
    sun_cy = int(h * 0.40)
    sun_r = int(h * 0.10)
    white = (250, 240, 200, 255)
    d.ellipse([sun_cx - sun_r, sun_cy - sun_r,
               sun_cx + sun_r, sun_cy + sun_r], fill=white)
    # 8 rays
    import math
    for i in range(8):
        ang = i * math.pi / 4
        x1 = sun_cx + int(sun_r * 1.2 * math.cos(ang))
        y1 = sun_cy + int(sun_r * 1.2 * math.sin(ang))
        x2 = sun_cx + int(sun_r * 1.8 * math.cos(ang))
        y2 = sun_cy + int(sun_r * 1.8 * math.sin(ang))
        d.line([(x1, y1), (x2, y2)], fill=white,
               width=max(2, int(h * 0.015)))

    return img


# ---------- orchestrator ----------

JOBS = [
    # (civ_label, primary_source_path, design_fn, list_of_output_paths)
    (
        "ANWBritish (Cross of St George)",
        FLAGS_DIR / "Flag_British.png",
        design_st_george,
        [
            FLAGS_DIR / "Flag_British.png",
            FLAGS_DIR / "postgame_flag_british.png",
            FLAGS_DIR / "flag_hc_british.png",
        ],
    ),
    (
        "ANWRussians (double-headed eagle on gold)",
        FLAGS_DIR / "Flag_Russian.png",
        design_russian_eagle,
        [
            FLAGS_DIR / "Flag_Russian.png",
            FLAGS_DIR / "postgame_flag_russian.png",
            FLAGS_DIR / "flag_hc_russian.png",
        ],
    ),
    (
        "ANWEthiopians (Lion of Judah on tricolor)",
        FLAGS_DIR / "Flag_Ethiopian.png",
        design_ethiopian_lion_tricolor,
        [
            FLAGS_DIR / "Flag_Ethiopian.png",
            FLAGS_DIR / "postgame_flag_ethiopian.png",
            FLAGS_DIR / "flag_hc_ethiopian.png",
        ],
    ),
    (
        "ANWIndians (Bhagwa saffron for Maratha Shivaji)",
        FLAGS_DIR / "Flag_Indian.png",
        design_bhagwa,
        [
            FLAGS_DIR / "Flag_Indian.png",
            FLAGS_DIR / "postgame_flag_indian.png",
            FLAGS_DIR / "flag_hc_indian.png",
        ],
    ),
]


def repaint_one(label: str, ref: Path, design_fn, outs: list[Path]) -> None:
    if not ref.exists():
        print(f"[SKIP] {label} — reference missing: {ref}")
        return
    print(f"[RUN ] {label}")
    wave = extract_wave_mask(ref)

    for out in outs:
        if not out.exists():
            print(f"  [SKIP out] {out} (not present)")
            continue
        # Use each output's own dimensions (flag_hc_*.png differ from
        # main Flag_*.png by aspect ratio in some cases)
        own_im = Image.open(out).convert("RGBA")
        size = own_im.size
        own_wave = extract_wave_mask(out)  # use own waves for own size
        flat = design_fn(size)
        result = apply_wave(flat, own_wave)
        # Copy alpha from original (preserve any transparency on edges)
        _, _, _, a = own_im.split()
        result.putalpha(a)
        result.save(out, "PNG")
        print(f"  wrote {out} ({size[0]}x{size[1]})")


def main():
    os.chdir(Path(__file__).resolve().parent.parent.parent)
    for label, ref, fn, outs in JOBS:
        repaint_one(label, ref, fn, outs)
    print("Done.")


if __name__ == "__main__":
    main()
