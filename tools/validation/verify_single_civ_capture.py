"""Post-flight verification for a single-civ visual capture.

Runs checks A–K from the smoke-test plan and emits a PASS/FAIL table.
Exit code 0 iff every check passes.

Usage:
    python3 tools/validation/verify_single_civ_capture.py ANWCanadians
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

REQUIRED_LABELS = [
    "01_lobby", "02_loading", "03_hud", "04_homecity_panel",
    "05_tech_tree", "06_diplomacy", "07_scoreboard",
    "08_esc_menu", "09_endgame",
]

# (label -> [crop_name, ...]) from anw_visual_capture_runner.LABEL_TO_CROPS
LABEL_TO_CROPS = {
    "01_lobby":           ["lobby_portrait"],
    "02_loading":         ["loading_flag"],
    "03_hud":             ["home_city_button", "hud_flag_corner"],
    "04_homecity_panel":  ["home_city_scene"],
    "05_tech_tree":       ["tech_tree_overview"],
    "06_diplomacy":       ["diplomacy_panel"],
    "07_scoreboard":      ["scoreboard_player_row"],
    "08_esc_menu":        ["esc_menu_player_summary"],
    "09_endgame":         ["endgame_flag"],
}


def _ok(name, condition, detail=""):
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}{' — ' + detail if detail else ''}")
    return bool(condition)


def main():
    if len(sys.argv) < 2:
        print("usage: verify_single_civ_capture.py <civ_token>", file=sys.stderr)
        return 2
    civ = sys.argv[1]
    civ_dir = REPO / "artifacts/validation/visual_art" / civ
    print(f"Verifying capture: {civ}")
    print(f"  dir: {civ_dir}")

    all_pass = True

    # A: manifest exists + status=complete
    manifest_path = civ_dir / "manifest.json"
    manifest = None
    a_pass = manifest_path.exists()
    if a_pass:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            a_pass = manifest.get("status") == "complete"
        except Exception as e:
            a_pass = False
    all_pass &= _ok("A: manifest.json exists + status=complete",
                    a_pass,
                    f"status={manifest.get('status') if manifest else 'N/A'}")

    # B: all required labels present
    labels_in = {c.get("label") for c in (manifest.get("captures", []) if manifest else [])}
    missing = sorted(set(REQUIRED_LABELS) - labels_in)
    all_pass &= _ok("B: all 9 required labels present",
                    not missing,
                    f"missing={missing}" if missing else f"have {len(labels_in)}/9")

    # C: full PNGs exist, > 50KB
    full_dir = civ_dir / "full"
    c_pass = True
    c_detail = []
    for label in REQUIRED_LABELS:
        p = full_dir / f"{label}.png"
        if not p.exists():
            c_pass = False
            c_detail.append(f"{label}=MISSING")
        elif p.stat().st_size < 50 * 1024:
            c_pass = False
            c_detail.append(f"{label}={p.stat().st_size}B<50KB")
    all_pass &= _ok("C: all 9 full/*.png exist, >50KB",
                    c_pass,
                    ", ".join(c_detail) if c_detail else "all 9 present, sized OK")

    # D + E: crops + thumbs per label. Validate via header magic + dims (not size).
    crops_dir = civ_dir / "crops"
    thumbs_dir = civ_dir / "thumbs"
    d_pass = True
    e_pass = True
    d_detail = []
    e_detail = []
    expected_crops = []
    for label, crop_names in LABEL_TO_CROPS.items():
        for cn in crop_names:
            expected_crops.append(cn)
            cp = crops_dir / f"{cn}.png"
            tp = thumbs_dir / f"{cn}.webp"
            if not cp.exists():
                d_pass = False
                d_detail.append(f"{cn}=missing")
            else:
                try:
                    head = cp.read_bytes()[:24]
                    if head[:8] != b"\x89PNG\r\n\x1a\n":
                        d_pass = False
                        d_detail.append(f"{cn}=bad_png_magic")
                    else:
                        w = int.from_bytes(head[16:20], "big")
                        h = int.from_bytes(head[20:24], "big")
                        if w < 50 or h < 30:
                            d_pass = False
                            d_detail.append(f"{cn}=tiny_dims_{w}x{h}")
                except Exception as ex:
                    d_pass = False
                    d_detail.append(f"{cn}=read_err:{ex}")
            if not tp.exists():
                e_pass = False
                e_detail.append(f"{cn}=missing")
            else:
                # WebP starts with "RIFF....WEBP"
                try:
                    head = tp.read_bytes()[:12]
                    if head[:4] != b"RIFF" or head[8:12] != b"WEBP":
                        e_pass = False
                        e_detail.append(f"{cn}=bad_webp_magic")
                except Exception as ex:
                    e_pass = False
                    e_detail.append(f"{cn}=read_err:{ex}")
    all_pass &= _ok(f"D: all {len(expected_crops)} crops/*.png valid PNG (magic + dims >= 50x30)",
                    d_pass,
                    ", ".join(d_detail) if d_detail else f"all {len(expected_crops)} valid")
    all_pass &= _ok(f"E: all {len(expected_crops)} thumbs/*.webp valid WebP (RIFF...WEBP)",
                    e_pass,
                    ", ".join(e_detail) if e_detail else f"all {len(expected_crops)} valid")

    # F: PNG headers
    f_pass = True
    f_detail = []
    for label in REQUIRED_LABELS:
        p = full_dir / f"{label}.png"
        if p.exists():
            try:
                head = p.read_bytes()[:8]
                if head[:4] != b"\x89PNG":
                    f_pass = False
                    f_detail.append(f"{label}=bad_header")
            except Exception as e:
                f_pass = False
                f_detail.append(f"{label}={e}")
    all_pass &= _ok("F: all 9 full PNGs have \\x89PNG header",
                    f_pass,
                    ", ".join(f_detail) if f_detail else "all valid")

    # G: column site rebuild succeeds
    g_proc = subprocess.run(
        [sys.executable, "tools/build_civ_columns.py"],
        cwd=str(REPO), capture_output=True, text=True, timeout=120,
    )
    g_pass = g_proc.returncode == 0
    all_pass &= _ok("G: build_civ_columns.py exit 0",
                    g_pass,
                    f"rc={g_proc.returncode}" +
                    (f", stderr={g_proc.stderr[:200]}" if not g_pass else ""))

    # H + I: column HTML has refs for this civ, all files exist
    html_path = REPO / "a_new_world_columns.html"
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    refs = sorted(set(re.findall(
        rf'visual_art/{re.escape(civ)}/(?:crops|thumbs)/[\w_]+\.(?:png|webp)',
        html,
    )))
    h_pass = len(refs) >= 2 * len(expected_crops)
    all_pass &= _ok(f"H: column HTML contains {2*len(expected_crops)}+ refs for {civ}",
                    h_pass,
                    f"found {len(refs)} unique refs")

    missing_on_disk = []
    for ref in refs:
        p = REPO / "artifacts/validation/visual_art" / civ
        # ref looks like "visual_art/ANWCanadians/crops/foo.png"
        # find the part after the civ token
        rel = ref.split(civ + "/", 1)[1] if civ + "/" in ref else None
        if rel is None:
            missing_on_disk.append(f"weird_ref:{ref}")
            continue
        full = p / rel
        if not full.exists():
            missing_on_disk.append(rel)
    i_pass = not missing_on_disk
    all_pass &= _ok("I: every column-site ref resolves on disk",
                    i_pass,
                    f"missing={missing_on_disk}" if missing_on_disk else "all resolved")

    # J: doctrine text columns populated
    # Look for the civ's column block and check that text cells aren't all "n/a"
    # The build script renders an info-table with rows for civ-data.
    # We do a soft check: confirm the civ's section contains > 200 chars of non-trivial text
    civ_block_match = re.search(
        rf'(?:data-civ-id|data-civ-token|id)="[^"]*{re.escape(civ)}[^"]*"(.{{0,8000}}?)(?:</section>|</div>\s*<!--\s*end\s*civ)',
        html, flags=re.DOTALL,
    )
    if civ_block_match:
        block = civ_block_match.group(1)
        # strip tags + whitespace, look for non-trivial text
        block_text = re.sub(r"<[^>]+>", " ", block)
        block_text = re.sub(r"\s+", " ", block_text).strip()
        # heuristic: must have > 200 chars, must NOT have ">5 n/a" tokens
        na_count = len(re.findall(r"\bn/a\b", block_text, flags=re.IGNORECASE))
        j_pass = len(block_text) > 200 and na_count < 5
        j_detail = f"text_len={len(block_text)}, n/a_count={na_count}"
    else:
        # Fallback: just count civ mentions
        mentions = len(re.findall(re.escape(civ), html))
        j_pass = mentions >= 10  # arbitrary floor for "has its own column"
        j_detail = f"civ_block not matched; total mentions={mentions}"
    all_pass &= _ok("J: doctrine text columns populated (not all n/a)",
                    j_pass, j_detail)

    # K: scoreboard OCR sanity — scoreboard_player_row should contain SOME readable
    # English text (player name, civ name, score numbers). loading_flag is graphical
    # and unreliable; the scoreboard always renders text. Skip if no tesseract.
    k_pass = True
    k_detail = "skipped"
    try:
        which = subprocess.run(["which", "tesseract"], capture_output=True, text=True)
        magick = subprocess.run(["which", "magick"], capture_output=True, text=True)
        if which.returncode == 0:
            crop = crops_dir / "scoreboard_player_row.png"
            if crop.exists():
                ocr_input = str(crop)
                if magick.returncode == 0:
                    pre = Path("/tmp") / f"_verify_{civ}_sc.png"
                    subprocess.run(
                        ["magick", str(crop), "-colorspace", "Gray",
                         "-threshold", "50%", str(pre)],
                        capture_output=True, timeout=15,
                    )
                    if pre.exists():
                        ocr_input = str(pre)
                proc = subprocess.run(
                    ["tesseract", ocr_input, "-", "-l", "eng"],
                    capture_output=True, text=True, timeout=30,
                )
                text = (proc.stdout or "").strip()
                tokens = re.findall(r"[A-Za-z0-9]{3,}", text)
                # Soft pass: any tokens at all means OCR can read it.
                k_pass = len(tokens) >= 1
                k_detail = f"OCR_tokens={tokens[:6]}"
            else:
                k_pass = False
                k_detail = "scoreboard_player_row.png missing"
        else:
            k_detail = "tesseract not installed; soft pass"
    except Exception as e:
        k_pass = False
        k_detail = f"OCR exception: {e}"
    all_pass &= _ok("K: scoreboard OCR yields >=1 readable token (soft sanity)",
                    k_pass, k_detail)

    print()
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print(f"Column site: {html_path}")
    print(f"Capture dir: {civ_dir}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
