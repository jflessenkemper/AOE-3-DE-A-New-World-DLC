#!/usr/bin/env bash
# Unified local testing harness for AOE 3 DE - A New World DLC.
#
# Runs every static / data-side check the mod has and prints a single
# pass/fail summary with counts. The same checks run in CI; this script
# is the "before you push" smoke test.
#
# Stages (skip with flags):
#   --no-content        Skip content validators (XML, XS, civ refs, decks, …)
#   --no-regression     Skip Python unittest suite
#   --no-packaged       Skip packaged-mod validator (slowest)
#   --strict-locids     Treat unresolved DisplayNameID locIDs as fatal
#   --report PATH       Write the staged report to PATH
#
# Standalone helpers (return early, don't run staged checks):
#   --preflight         Print the per-civ runtime ground-truth table
#                       (leader, deck, terrain, heading, derived bias).
#                       Use this as a checklist while playing.
#   --layout-spot-check DIR
#                       Run tools/playtest/spot_check.py over DIR.
#                       Verifies in-game building layout per civ from
#                       screenshots. Add --team COLOR if not blue.
#   --team COLOR        Player team color for --layout-spot-check
#                       (blue/red/yellow/green/cyan/purple/orange/pink).
#
# Returns 0 if everything passes, 1 otherwise.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

run_content=1
run_regression=1
run_packaged=1
strict_locids=0
report_path=""
preflight=0
layout_dir=""
team="blue"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-content)    run_content=0 ;;
    --no-regression) run_regression=0 ;;
    --no-packaged)   run_packaged=0 ;;
    --strict-locids) strict_locids=1 ;;
    --report)        shift; report_path="$1" ;;
    --preflight)     preflight=1 ;;
    --layout-spot-check)
                     shift; layout_dir="$1" ;;
    --team)          shift; team="$1" ;;
    -h|--help)
      sed -n '2,28p' "$0" | sed 's/^# //; s/^#//'
      exit 0
      ;;
    *)
      echo "unknown flag: $1" >&2
      exit 2
      ;;
  esac
  shift
done

# Standalone helpers run and exit before the staged sweep.
if [[ $preflight -eq 1 ]]; then
  exec python3 -m tools.playtest.preflight
fi

if [[ -n "$layout_dir" ]]; then
  layout_args=("$layout_dir" --team "$team")
  [[ -n "$report_path" ]] && layout_args+=(--report "$report_path")
  exec python3 -m tools.playtest.spot_check "${layout_args[@]}"
fi

echo "━━━ AOE3 DE A New World DLC — local test harness ━━━"
echo "repo: $REPO_ROOT"
echo

stages=()
[[ $run_content -eq 1 ]]    && stages+=(--stage content)
[[ $run_regression -eq 1 ]] && stages+=(--stage regression)
[[ $run_packaged -eq 1 ]]   && stages+=(--stage packaged)

if [[ ${#stages[@]} -eq 0 ]]; then
  echo "no stages selected — exiting."
  exit 0
fi

extra=()
[[ $strict_locids -eq 1 ]]   && extra+=(--strict-display-name-ids)
[[ -n "$report_path" ]]      && extra+=(--report-file "$report_path")

python3 -m tools.validation.run_staged_validation "${stages[@]}" "${extra[@]}"
status=$?

echo
if [[ $status -eq 0 ]]; then
  echo "✅ All selected stages passed."
  echo
  echo "Mod inventory:"
  printf "  base civs:        %s homecity files\n" "$(ls data/homecity*.xml 2>/dev/null | wc -l)"
  printf "  revolution civs:  %s homecity files\n" "$(ls data/anwhomecity*.xml 2>/dev/null | wc -l)"
  printf "  leader XS files:  %s\n" "$(find game/ai/leaders -name 'leader_*.xs' 2>/dev/null | wc -l)"
  printf "  workflows:        %s GitHub Actions checks\n" "$(ls .github/workflows/*.yml 2>/dev/null | wc -l)"
  printf "  validators:       %s static checks\n" "$(ls tools/validation/validate_*.py 2>/dev/null | wc -l)"
else
  echo "❌ One or more stages failed (exit status $status). Scroll up for details."
fi

exit $status
