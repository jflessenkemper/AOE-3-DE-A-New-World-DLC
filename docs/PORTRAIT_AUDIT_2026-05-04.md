# Portrait visual-consistency audit — 2026-05-04

In-session visual review of all 48 leader portraits referenced from
`game/ai/*.personality <icon>` paths. Audited against the criteria:
*"Do these belong to one art set, comparable framing/resolution, no
obvious AI artifacts or wrong-source mismatches?"*

## Style buckets (informational)

| Bucket | Count | Notes |
|---|---|---|
| Color oil / painted historical | ~30 | Baseline; matches AoE3 DE base-game leader art |
| Sepia / period photograph | ~10 | 19th-century leaders (Garibaldi, Menelik, Mannerheim, Kossuth, Kruger, Vallejo, Sam Houston, Cuza, Carrillo Puerto, Papineau). Acceptable — these post-date the oil-portrait era |
| Engraving / sketch | ~5 | Hiawatha, Crazy Horse, Usman, Diponegoro, Alvarado. Acceptable — no European-style portraits exist for these leaders |

## ⚠ Real outliers (recommend replacement before v1.0)

| Personality | File | Issue |
|---|---|---|
| `mayans.personality` | `cpai_avatar_mayans_canek.png` | Not a portrait — multi-figure sacrifice scene, heavy painterly style. Reads as fan-art / AI-generated. |
| `anwriogrande.personality` | `cpai_avatar_rio_grande_canales_rosillo.png` | Severely pixelated low-res newsprint scan. Visibly half the effective resolution of every other image. |
| `montezuma.personality` | `cpai_avatar_aztecs_montezuma.png` | Codex folio fragment — tiny stylised figure with bleeding manuscript text ("moteccoma"). Won't read as a leader at thumbnail size. |

## Action items

1. Source replacement portraits for the 3 outliers above (any commons-licensed
   historical reproduction at ~256×256+ would be a strict upgrade).
2. After replacing, re-run:
   ```
   python3 tools/validation/validate_art_coverage.py
   ```
3. (Optional) Re-run live consistency audit with API key:
   ```
   ANTHROPIC_API_KEY=... AOE3_RUN_VISION=1 \
     python3 tools/validation/validate_art_consistency.py
   ```

## Method

Audit performed by reading each PNG directly via Claude vision in-session;
no external API calls or token budget for `validate_art_consistency.py`.
The `validate_art_consistency.py` script remains available for repeatable
batch audits via Haiku 4.5 when an API key is set.
