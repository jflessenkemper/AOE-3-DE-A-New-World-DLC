# Exhibition Match Report

**Generated:** 2026-05-13T13:17:06.584585
**Total time:** 296s (4.9m)
**Result:** 0/1 civs passed ✅

## Summary

| Civ | Leader | Engine Token | Leader Found | Deck | Escort | Ransom | Rout | Suites | Status |
|-----|--------|--------------|--------------|------|--------|--------|------|--------|--------|
| British | Elizabeth | ANWBritish | ❌ | ❌ | ❌ | ❌ | ❌ | 0/0 | ❌ ERROR: never reached in-game state |

## Civs Needing Review

- **British** (British Elizabeth / ANWBritish): leader name not found, deck not loaded, escort plan never fired, rout plan never fired, ERROR: never reached in-game state

## Configuration

- Match length: 120s per civ
- Launch method: Automated (steam:// or proton)
- Test opponent: ANWNapoleonicFrance
- Difficulty: Hard
- Scenario: ANEWWORLD

## How to Reproduce

```bash
python3 tools/validation/exhibition_runner.py --dry-run
python3 tools/validation/exhibition_runner.py --match-seconds 120
```

See `tools/validation/EXHIBITION_RUNNER.md` for detailed instructions.