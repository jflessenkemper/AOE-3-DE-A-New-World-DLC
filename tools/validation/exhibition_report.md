# Exhibition Match Report

**Generated:** 2026-05-30T20:42:47.933858
**Total time:** 289s (4.8m)
**Result:** 0/1 civs passed ✅

## Summary

| Civ | Leader | Engine Token | Leader | Deck | AIs | Wall | Escort | Rout | Suites | Status |
|-----|--------|--------------|--------|------|-----|------|--------|------|--------|--------|
| Inca | Pachacuti | ANWInca | ❌ | ❌ | 0 | — | — | — | — | ❌ FAIL |

## Civs Needing Review

- **Inca** (Inca Pachacuti / ANWInca): leader name not found, deck not loaded, escort plan never fired, rout plan never fired

## Configuration

- Match length: 150s per civ
- Launch method: Automated (steam:// or proton)
- Test opponents (P2..P8 ANW slate): ANWNapoleonicFrance, ANWBritish, ANWGermans, ANWAztecs, ANWUSA, ANWChinese, ANWLakota
- Difficulty: Hard
- Map: anwHubTest (random map)

## How to Reproduce

```bash
python3 tools/validation/exhibition_runner.py --dry-run
python3 tools/validation/exhibition_runner.py --match-seconds 150
```

See `tools/validation/EXHIBITION_RUNNER.md` for detailed instructions.