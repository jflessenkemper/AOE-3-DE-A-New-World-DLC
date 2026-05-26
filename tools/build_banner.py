"""Build the README banner for AOE 3 DE - A New World.

Tiles all 48 nation flags into a darkened mosaic background and stamps
"A NEW WORLD" in serif black across the center, with a thin subtitle.

Run from repo root:
    python3 tools/build_banner.py

Outputs:
    resources/images/a_new_world_banner.png   (1600x400, sRGB)
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[1]
FLAG_DIR = REPO / "resources" / "images" / "icons" / "flags"
OUT = REPO / "resources" / "images" / "a_new_world_banner.png"

# Pick 48 distinct nation flags. Where multiple casings exist on disk
# we choose one per nation (canonical capitalization where possible).
FLAGS = [
    # 22 base civs
    "Flag_British.png",
    "Flag_French.png",
    "Flag_German.png",
    "Flag_Russian.png",
    "Flag_Spanish.png",
    "Flag_Ottoman.png",
    "Flag_Portuguese.png",
    "Flag_Dutch.png",
    "Flag_USA.png",
    "Flag_Mexican.png",
    "Flag_Italian.png",
    "Flag_Maltese.png",
    "Flag_Aztec.png",
    "Flag_Chinese.png",
    "Flag_Ethiopian.png",
    "Flag_Iroquois.png",
    "Flag_Hausa.png",
    "Flag_Incan.png",
    "Flag_Indian.png",
    "Flag_Japanese.png",
    "Flag_Sioux.png",
    "Flag_Swedish.png",
    # 26 revolution civs
    "Flag_American.png",
    "Flag_Argentinian.png",
    "Flag_Baja_Californian.png",
    "Flag_Barbary.png",
    "Flag_Brazilian.png",
    "Flag_Californian.png",
    "Flag_Canadians.png",
    "Flag_Central_American.png",
    "Flag_Chilean.png",
    "Flag_Colombian.png",
    "Flag_Egyptians.png",
    "Flag_Finnish.png",
    "Flag_SPC_Canadian.png",  # Lower Canada (Patriote — engine spec_key "French Canadians Papineau Revolution")
    "Flag_Haitian.png",
    "Flag_Hungarian.png",
    "Flag_Indonesian.png",
    "Flag_Mayan.png",
    "Flag_Mexican_Rev.png",
    "Flag_Tokugawa.png",  # placeholder for Napoleonic France: use the most ornate available
    "Flag_Peruvian.png",
    "Flag_Revolutionary_France.png",
    "Flag_Rio_Grande.png",
    "Flag_Romanians.png",
    "Flag_South_African.png",
    "Flag_Texan.png",
    "Flag_Yucatan.png",
    "Flag_French_Revolution.png",  # extra for Napoleonic France slot
    "Flag_Moroccan.png",          # filler to reach 48 unique-looking tiles
]


W, H = 1600, 400
COLS, ROWS = 12, 4
TILE_W, TILE_H = W // COLS, H // ROWS  # 133 x 100


def load_flag(name: str) -> Image.Image:
    path = FLAG_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return Image.open(path).convert("RGBA")


def fit_tile(im: Image.Image, w: int, h: int) -> Image.Image:
    """Center-crop the flag to the tile aspect, then resize to w×h."""
    src_w, src_h = im.size
    target_aspect = w / h
    src_aspect = src_w / src_h
    if src_aspect > target_aspect:
        # too wide — crop sides
        new_w = int(src_h * target_aspect)
        left = (src_w - new_w) // 2
        im = im.crop((left, 0, left + new_w, src_h))
    else:
        # too tall — crop top/bottom
        new_h = int(src_w / target_aspect)
        top = (src_h - new_h) // 2
        im = im.crop((0, top, src_w, top + new_h))
    return im.resize((w, h), Image.LANCZOS)


def build_mosaic() -> Image.Image:
    canvas = Image.new("RGBA", (W, H), (12, 14, 18, 255))
    flags = FLAGS[: COLS * ROWS]
    for idx, name in enumerate(flags):
        try:
            tile = load_flag(name)
        except FileNotFoundError:
            print(f"  WARN: missing {name}, leaving slot blank")
            continue
        tile = fit_tile(tile, TILE_W, TILE_H)
        col = idx % COLS
        row = idx // COLS
        canvas.paste(tile, (col * TILE_W, row * TILE_H), tile)
    return canvas


def darken_and_dim(mosaic: Image.Image) -> Image.Image:
    # Slight blur, desaturate, and overlay a dark wash so text reads.
    blurred = mosaic.filter(ImageFilter.GaussianBlur(radius=1.2))
    desat = ImageEnhance.Color(blurred).enhance(0.45)
    dimmed = ImageEnhance.Brightness(desat).enhance(0.55)

    # Vignette + horizontal dark band behind text.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Center band — strong dark in middle, transparent at edges.
    band_h = int(H * 0.55)
    band_top = (H - band_h) // 2
    for y in range(band_h):
        # ease-in-out alpha curve, peak in middle
        t = y / band_h
        eased = (1 - abs(2 * t - 1)) ** 1.2
        a = int(170 * eased)
        draw.line([(0, band_top + y), (W, band_top + y)], fill=(0, 0, 0, a))
    return Image.alpha_composite(dimmed, overlay)


def find_font(family_paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in family_paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def stamp_text(canvas: Image.Image) -> Image.Image:
    title_font = find_font(
        [
            "/usr/share/fonts/google-noto/NotoSerif-Black.ttf",
            "/usr/share/fonts/google-noto/NotoSans-Black.ttf",
        ],
        size=140,
    )
    subtitle_font = find_font(
        [
            "/usr/share/fonts/google-noto/NotoSans-CondensedBlack.ttf",
            "/usr/share/fonts/google-noto/NotoSans-Bold.ttf",
        ],
        size=28,
    )

    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    title = "A NEW WORLD"
    subtitle = "AGE OF EMPIRES III · DEFINITIVE EDITION · 48 NATIONS"

    # Title — measure, center.
    bbox = draw.textbbox((0, 0), title, font=title_font, stroke_width=2)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (W - tw) // 2 - bbox[0]
    ty = (H - th) // 2 - bbox[1] - 22
    # Soft shadow
    draw.text((tx + 4, ty + 6), title, font=title_font, fill=(0, 0, 0, 180))
    # Main fill — warm ivory
    draw.text(
        (tx, ty),
        title,
        font=title_font,
        fill=(245, 230, 200, 255),
        stroke_width=2,
        stroke_fill=(20, 16, 10, 255),
    )

    # Subtitle
    sbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    sw, sh = sbox[2] - sbox[0], sbox[3] - sbox[1]
    sx = (W - sw) // 2 - sbox[0]
    sy = ty + th + 24
    # subtle shadow for the subtitle so it lifts off the dark band
    draw.text((sx + 1, sy + 2), subtitle, font=subtitle_font, fill=(0, 0, 0, 220))
    draw.text((sx, sy), subtitle, font=subtitle_font, fill=(245, 222, 170, 255))

    # Thin gold rule above subtitle for definition
    rule_y = sy - 12
    rule_w = int(sw * 0.92)
    rule_x = (W - rule_w) // 2
    draw.line(
        [(rule_x, rule_y), (rule_x + rule_w, rule_y)],
        fill=(212, 170, 95, 255),
        width=3,
    )

    return Image.alpha_composite(canvas, layer)


def main() -> None:
    print(f"building banner → {OUT}")
    mosaic = build_mosaic()
    dimmed = darken_and_dim(mosaic)
    final = stamp_text(dimmed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    final.convert("RGB").save(OUT, "PNG", optimize=True)
    print(f"  wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
