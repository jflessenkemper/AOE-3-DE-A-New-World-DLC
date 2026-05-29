# AoE3 UI Automation

This is a small desktop automation harness for repeatedly launching and driving Age of Empires III: DE menu flows.

It supports two automation styles:

- `record-input`: raw mouse and keyboard event recording, then `replay-input`.
- `run-flow`: image-driven, step-by-step UI automation using screenshots as anchors.

It also includes two support commands:

- `probe-environment`: report which Linux desktop automation backends are available.
- `capture-loop`: capture screenshots on a fixed interval so you can observe the current game state continuously.
- `collect-artifacts`: copy AoE3 log files and optionally grab a screenshot after a failure.

The image-driven flow is the safer mode for game menus because it is less sensitive to timing drift than pure replay.

## Dependencies

Install into a virtual environment if you want to keep it isolated:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/aoe3_automation/requirements.txt
```

## Linux Note

The harness supports two Linux automation paths:

- X11/XWayland via `pyautogui` or host `xdotool`
- native Wayland via `ydotool` + `wtype` for input and `grim` for screenshots

If you run VS Code inside Flatpak, the script can use host-side tools through `flatpak-spawn --host`.

For this machine, prefer host `xdotool` first when the game window is exposed through XWayland. Some compositors reject the virtual-keyboard path used by `wtype`, which can stall flows even when `ydotoold` is running.

Fallback host paths:

- host `xdotool` for pointer movement, clicks, and key presses when the game window is reachable
- host `ydotool` plus `wtype` for native Wayland input when XWayland control is not available
- host `grim` or `spectacle` for screenshots

Use the helper below to inspect the host machine and print the exact install command:

```bash
tools/aoe3_automation/setup_linux_host.sh
```

On an immutable Fedora/Bazzite-style host this will recommend `rpm-ostree install` and a reboot before the new tools become available.

Check your current environment with:

```bash
python3 tools/aoe3_automation/aoe3_ui_automation.py probe-environment
```

`probe-environment` reports whether local or host Wayland input is ready and whether `ydotoold` is already running.

## Host Setup

After the host packages are installed:

1. Ensure `ydotoold` is running on the host.
2. Re-run `probe-environment` from the repo.
3. Run a flow with `run-flow` or `launch_retest_mod.sh`.

## Commands

Record raw input until `Esc`:

```bash
python3 tools/aoe3_automation/aoe3_ui_automation.py record-input tools/aoe3_automation/recordings/start_match.json
```

Replay the captured input:

```bash
python3 tools/aoe3_automation/aoe3_ui_automation.py replay-input tools/aoe3_automation/recordings/start_match.json --speed 1.0
```

Capture a reference image for button matching:

```bash
python3 tools/aoe3_automation/aoe3_ui_automation.py capture-reference tools/aoe3_automation/templates/single_player_button.png
```

Capture one screenshot every second into a folder while the game is open:

```bash
python3 tools/aoe3_automation/aoe3_ui_automation.py capture-loop tools/aoe3_automation/artifacts/live_watch --interval 1.0
```

`capture-loop` writes timestamped frames and also refreshes `latest.png` on each capture. That gives you a simple observe-act workflow: keep grabbing the current screen, inspect `latest.png`, then issue a `run-flow`, `press`, `click`, or other targeted action based on what is visible.

Run an image-driven flow:

```bash
python3 tools/aoe3_automation/aoe3_ui_automation.py run-flow tools/aoe3_automation/flows/example_skirmish_flow.json
```

Collect failure artifacts:

```bash
python3 tools/aoe3_automation/aoe3_ui_automation.py collect-artifacts tools/aoe3_automation/artifacts/latest --screenshot
```

Validate the resulting AoE3 runtime log against a named Legendary Leaders suite:

```bash
python tools/validation/validate_runtime_logs.py \
	--log-path "$HOME/.steam/steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt" \
	--suite elite_retreat_lane
```

Orchestrate the whole sequence with one command:

```bash
./.venv/bin/python tools/aoe3_automation/run_runtime_validation.py \
	tools/aoe3_automation/flows/dutch_napoleon_vs_russia_egypt_skirmish.json \
	--suite ai_rout_bootstrap \
	--artifacts-dir tools/aoe3_automation/artifacts/dutch_napoleon_vs_russia_egypt \
	--screenshot
```

This is the preferred way to promote runtime systems from "structurally wired" to "behaviorally verified": drive the menu flow, run a deterministic scenario or skirmish, collect `Age3Log.txt`, and assert on `Legendary Leaders:` log markers.

Retest the current mod install with one shell command:

```bash
tools/aoe3_automation/launch_retest_mod.sh
```

For a reproducible sandbox run that first syncs the repo into the live Proton mod install, republishes the active test random map into the profile `RandMaps` folder, and then delegates to `launch_retest_mod.sh`, use:

```bash
python3 tools/aoe3_automation/run_sandbox.py \
	--runtime-suite ai_rout_bootstrap
```

Useful variants:

```bash
python3 tools/aoe3_automation/run_sandbox.py --dry-run
python3 tools/aoe3_automation/run_sandbox.py --skip-launch --skip-flow
python3 tools/aoe3_automation/run_sandbox.py --scenario ANEWWORLD --skip-flow
```

`run_sandbox.py` is the preferred entrypoint for this repo when debugging custom RMS, scenario payloads, or live-install drift because it closes the gap between repo state and what AoE3 actually loads.

Before launching, `launch_retest_mod.sh` now checks whether AoE3 or its Proton children are still alive on the host. It first asks Steam to stop app `933110`, then escalates to terminating matching `compatdata/933110`, `RelicCardinal`, `AoE3`, `wine64`, or Proton child processes if Steam is stuck showing the game as still open.

If Steam still shows AoE3 as running after you already closed the window manually, the reliable fix is the same sequence the script now uses:

```bash
flatpak-spawn --host sh -lc 'steam steam://stop/933110 >/dev/null 2>&1 || true'
flatpak-spawn --host sh -lc 'pkill -f -i "compatdata/933110|age3y\\.exe|AoE3|RelicCardinal|steamgameid=933110" >/dev/null 2>&1 || true'
```

Useful variants:

```bash
tools/aoe3_automation/launch_retest_mod.sh --skip-launch --flow tools/aoe3_automation/flows/capture_open_menu.json
tools/aoe3_automation/launch_retest_mod.sh --skip-launch --skip-flow
tools/aoe3_automation/launch_retest_mod.sh --runtime-suite ai_rout_bootstrap
```

The script snapshots the previous `Age3Log.txt`, runs the static validation profiles, optionally launches AoE3, optionally runs a UI flow, collects artifacts, and writes a grep-based runtime error scan into the run artifact directory.

## Flow Format

`run-flow` expects a JSON object with a `steps` array. Supported actions:

- `launch`
- `sleep`
- `wait_image`
- `click_image`
- `wait_text`
- `click_text`
- `click`
- `press`
- `hotkey`
- `type_text`
- `scroll`
- `screenshot`

See [tools/aoe3_automation/flows/example_skirmish_flow.json](tools/aoe3_automation/flows/example_skirmish_flow.json) for a starting template.

## Recommended Workflow

1. Capture reference images for the exact buttons and civ/map slots you want.
2. Build a `run-flow` JSON that waits for those images before clicking.
3. Run `python3 tools/aoe3_automation/run_sandbox.py --dry-run` to confirm the live mod root, profile root, and published assets.
4. Keep the game resolution and UI scale fixed.
5. Use `record-input` only for short stable segments, not as the primary whole-run approach.
6. Run `probe-environment` first if you are inside Flatpak or Wayland, so you know which host backends are actually usable.
7. Prefer `run_sandbox.py` over manual file copies so the active local mod, profile `RandMaps`, and artifacts folder all stay in sync.
8. After the match or scenario run, validate `Age3Log.txt` with `tools/validation/validate_runtime_logs.py` and the appropriate suite name.

## Current Limits

- It does not inspect game memory or internal UI objects.
- It relies on the game window being visible.
- It will be brittle if the UI layout, resolution, or language changes.
- `Esc` is the stop key for recording.
- `record-input` still depends on local Python packages such as `pynput`; host passthrough helps with playback and flow execution, not raw event capture.
- `replay-input` is still a poor fit on Wayland because low-level mouse down/up replay is not supported by the `ydotool` path. Prefer `run-flow` for real tests.
- Wheel scrolling is not implemented for the Wayland backend yet, so flows should prefer direct image clicks over scroll-dependent menu traversal.
- Image matching still depends on Python dependencies from [tools/aoe3_automation/requirements.txt](tools/aoe3_automation/requirements.txt).
- OCR-driven `wait_text` and `click_text` steps require `pytesseract` plus a `tesseract` binary available either locally or on the host through `flatpak-spawn`.

## Unattended Runs

For a hands-off test run, build one flow that both starts the match and waits for post-game UI before collecting artifacts. The OCR actions are intended for the long-running part because they are easier to generalize across end-of-match screens than fixed templates.

Example:

```bash
python3 tools/aoe3_automation/run_runtime_validation.py \
	tools/aoe3_automation/flows/dutch_napoleon_vs_russia_egypt_unattended.json \
	--suite ai_rout_bootstrap \
	--artifacts-dir tools/aoe3_automation/artifacts/dutch_napoleon_vs_russia_egypt_unattended \
	--screenshot
```

Useful flow fields for unattended runs:

- `optional: true` lets the run continue if a non-essential cleanup click is absent.
- `matchIndex` selects the zero-based OCR match to use when the same text appears more than once in the search region.
- `wait_text` waits for OCR text such as `Victory`, `Defeat`, `Continue`, `Home City`, or `Main Menu`.
- `click_text` clicks the center of OCR-detected text when a stable template image is not practical.