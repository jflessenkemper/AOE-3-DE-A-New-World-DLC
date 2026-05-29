# Exhibition Match Report

**Generated:** 2026-05-13T17:33:28.348706
**Total time:** 503s (8.4m)
**Result:** 1/1 civs passed ✅

## Summary

| Civ | Leader | Engine Token | Leader | Deck | AIs | Wall | Escort | Rout | Suites | Status |
|-----|--------|--------------|--------|------|-----|------|--------|------|--------|--------|
| Inca | Pachacuti | ANWInca | ✅ | ✅ | 7 | — | — | — | — | ✅ PASS |

## Civs Needing Review

All civs passed!

## Configuration

- Match length: 240s per civ
- Launch method: Automated (steam:// or proton)
- Test opponents (P2..P8 ANW slate): ANWNapoleonicFrance, ANWBritish, ANWGermans, ANWAztecs, ANWUSA, ANWChinese, ANWLakota
- Difficulty: Hard
- Scenario: ANEWWORLD

## How to Reproduce

```bash
python3 tools/validation/exhibition_runner.py --dry-run
python3 tools/validation/exhibition_runner.py --match-seconds 240
```

See `tools/validation/EXHIBITION_RUNNER.md` for detailed instructions.