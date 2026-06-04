# Exhibition Match Report

**Generated:** 2026-05-30T21:28:39.749818
**Total time:** 1791s (29.9m)
**Result:** 0/3 civs passed ✅

## Summary

| Civ | Leader | Engine Token | Leader | Deck | AIs | Wall | Escort | Rout | Suites | Status |
|-----|--------|--------------|--------|------|-----|------|--------|------|--------|--------|
| Hungarians | Lajos Kossuth | ANWHungarians | ❌ | ❌ | 0 | — | — | — | — | ❌ FAIL |
| Indians | Shivaji Maharaj | ANWIndians | ❌ | ❌ | 0 | — | — | — | — | ❌ FAIL |
| Napoleonic France | Napoleon Bonaparte | ANWNapoleonicFrance | ❌ | ❌ | 0 | — | — | — | — | ❌ FAIL |

## Civs Needing Review

- **Hungarians** (Hungarians Kossuth Revolution / ANWHungarians): leader name not found, deck not loaded, escort plan never fired, rout plan never fired
- **Indians** (Indians Akbar / ANWIndians): leader name not found, deck not loaded, escort plan never fired, rout plan never fired
- **Napoleonic France** (Napoleonic France Napoleon Bonaparte Revolution / ANWNapoleonicFrance): leader name not found, deck not loaded, escort plan never fired, rout plan never fired

## Configuration

- Match length: 420s per civ
- Launch method: Automated (steam:// or proton)
- Test opponents (P2..P8 ANW slate): ANWNapoleonicFrance, ANWBritish, ANWGermans, ANWAztecs, ANWUSA, ANWChinese, ANWLakota
- Difficulty: Hard
- Map: anwHubTest (random map)

## How to Reproduce

```bash
python3 tools/validation/exhibition_runner.py --dry-run
python3 tools/validation/exhibition_runner.py --match-seconds 420
```

See `tools/validation/EXHIBITION_RUNNER.md` for detailed instructions.