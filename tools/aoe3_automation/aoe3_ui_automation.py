#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def ensure_runtime_support(needs_input: bool = False) -> None:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    display = os.environ.get("DISPLAY", "")
    if session_type == "wayland" and needs_input:
        fail(
            "Raw input recording is not supported on pure Wayland from this harness. Use run-flow with grim + "
            "ydotool/wtype, or run recording under X11/XWayland. You can use the 'probe-environment' command to "
            "see what is missing."
        )
    if not display and session_type != "wayland":
        fail("No desktop display detected.")


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def can_spawn_host() -> bool:
    return command_exists("flatpak-spawn")


def run_host_command(args: list[str], capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    if not can_spawn_host():
        fail("flatpak-spawn is not available")

    kwargs: dict[str, Any] = {"check": False, "text": True}
    if capture_output:
        kwargs["capture_output"] = True

    return subprocess.run(["flatpak-spawn", "--host", *args], **kwargs)


def host_command_exists(name: str) -> bool:
    result = run_host_command(["which", name], capture_output=True)
    return result.returncode == 0


def host_xdotool_available() -> bool:
    if not host_command_exists("xdotool"):
        return False
    result = run_host_command(["xdotool", "getmouselocation"], capture_output=True)
    return result.returncode == 0


def find_host_game_window() -> str | None:
    if host_xdotool_available() is False:
        return None

    result = run_host_command(
        ["sh", "-lc", "xdotool search --name 'Age of Empires|AoE3|age of empires' | head -n1"],
        capture_output=True,
    )
    if result.returncode != 0:
        return None

    lines = (result.stdout or "").strip().splitlines()
    if not lines:
        return None
    return lines[0].strip()


def focus_host_game_window() -> str | None:
    window_id = find_host_game_window()
    if not window_id:
        return None
    # Guard: only windowactivate if this window isn't already the active one,
    # to avoid stealing focus from CoH2 or other foreground apps.
    active_res = run_host_command(["xdotool", "getactivewindow"], capture_output=True)
    if active_res.returncode == 0 and active_res.stdout.strip() == window_id:
        return window_id  # already focused — no-op
    run_host_command(["xdotool", "windowactivate", window_id])
    return window_id


def focus_game_window(backend: str | None = None) -> bool:
    # Under gamescope the nested compositor always has focus on its window.
    if backend == "gamescope_xdotool" or (backend is None and gamescope_available()):
        return True
    if backend == "host_xdotool" or backend is None:
        window_id = focus_host_game_window()
        return window_id is not None
    return False


def wait_for_game_window_focus(
    backend: str | None = None,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 1.0,
) -> bool:
    deadline = time.time() + max(timeout_seconds, 0.0)
    while True:
        if focus_game_window(backend):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(max(poll_interval_seconds, 0.1))


def run_host_xdotool_window_command(command: list[str], supports_window: bool = True) -> None:
    window_id = focus_host_game_window()
    if window_id is not None and supports_window:
        run_host_command(["xdotool", command[0], "--window", window_id, *command[1:]])
        return
    run_host_command(["xdotool", *command])


def host_wayland_tool_available(name: str) -> bool:
    return can_spawn_host() and host_command_exists(name)


def host_ydotool_daemon_running() -> bool:
    if host_wayland_tool_available("ydotoold") is False:
        return False
    result = run_host_command(["sh", "-lc", "pgrep -x ydotoold >/dev/null"], capture_output=True)
    return result.returncode == 0


def host_wayland_input_available() -> bool:
    return host_wayland_tool_available("ydotool") and host_wayland_tool_available("wtype")


def local_wayland_input_available() -> bool:
    return command_exists("ydotool") and command_exists("wtype")


def run_checked_command(args: list[str]) -> None:
    result = subprocess.run(args, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "unknown error").strip()
        fail(message)


def run_wayland_command(backend: str, args: list[str]) -> None:
    if backend == "local_wayland":
        run_checked_command(args)
        return
    if backend == "host_wayland":
        result = run_host_command(args, capture_output=True)
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "unknown error").strip()
            fail(message)
        return
    fail(f"unknown Wayland backend: {backend}")


def default_aoe3_log_dir() -> Path:
    return Path.home() / ".steam/steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs"


def import_pillow_image():
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        fail(f"Pillow import failed: {exc}")
    return Image


def import_cv2():
    try:
        import cv2  # type: ignore
    except Exception as exc:
        fail(f"opencv-python import failed: {exc}")
    return cv2


def import_pytesseract():
    try:
        import pytesseract  # type: ignore
    except Exception as exc:
        fail(f"pytesseract import failed: {exc}")
    return pytesseract


def resolve_tesseract_command() -> str:
    if command_exists("tesseract"):
        return shutil.which("tesseract") or "tesseract"

    if can_spawn_host() and host_command_exists("tesseract"):
        wrapper_path = Path(__file__).resolve().parent / "artifacts" / ".tmp" / "host_tesseract.sh"
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        if wrapper_path.exists() is False:
            wrapper_path.write_text(
                "#!/usr/bin/env sh\nexec flatpak-spawn --host tesseract \"$@\"\n",
                encoding="utf-8",
            )
            wrapper_path.chmod(0o755)
        return str(wrapper_path)

    fail("No tesseract binary found locally or on the host.")


def gamescope_available() -> bool:
    """True when AoE3 is running in a gamescope-nested session we can drive."""
    gamescope_display = os.environ.get("GAMESCOPE_WAYLAND_DISPLAY", "gamescope-0")
    socket = Path("/run/user/1000") / gamescope_display
    if not socket.exists():
        return False
    if not command_exists("gamescopectl"):
        return False
    # Verify DISPLAY=:1 xdotool can reach the nested Xwayland
    try:
        env = {**os.environ, "DISPLAY": ":1"}
        result = subprocess.run(
            ["xdotool", "getmouselocation"],
            env=env, capture_output=True, text=True, timeout=2,
        )
        return result.returncode == 0
    except Exception:
        return False


def detect_input_backend(needs_vision: bool = False) -> str:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    display = os.environ.get("DISPLAY", "")

    # Prefer gamescope when AoE3 is nested there — the host desktop input
    # backends (pyautogui, host_xdotool) address :0 which is the wrong
    # display in that topology.
    if gamescope_available():
        return "gamescope_xdotool"

    if maybe_import_pyautogui() is not None:
        return "pyautogui"

    if can_spawn_host() and host_xdotool_available():
        return "host_xdotool"

    if session_type == "wayland":
        if local_wayland_input_available():
            return "local_wayland"
        if host_wayland_input_available():
            return "host_wayland"

    if needs_vision:
        fail(
            "No usable input/vision backend found. Install Python requirements for local control, or provide host Wayland tools "
            "(ydotool/wtype/grim) or host X11 tools (xdotool/import) reachable via flatpak-spawn."
        )

    if session_type == "wayland":
        fail(
            "Wayland input automation needs ydotool plus wtype locally or on the host, or an X11/XWayland-compatible backend."
        )
    if not display:
        fail("No desktop display detected.")
    fail("No usable input backend found.")


def detect_capture_backend() -> str:
    preferred_backends: list[str] = []
    if gamescope_available():
        preferred_backends.append("gamescopectl")
    if command_exists("gnome-screenshot"):
        preferred_backends.append("gnome-screenshot")
    if maybe_import_pyautogui() is not None:
        preferred_backends.append("pyautogui")
    if command_exists("spectacle"):
        preferred_backends.append("spectacle")
    if command_exists("import"):
        preferred_backends.append("import")
    if can_spawn_host() and host_command_exists("spectacle"):
        preferred_backends.append("host-spectacle")
    if can_spawn_host() and host_command_exists("import"):
        preferred_backends.append("host-import")
    if command_exists("grim"):
        preferred_backends.append("grim")
    if host_wayland_tool_available("grim"):
        preferred_backends.append("host-grim")
    if preferred_backends:
        return preferred_backends[0]
    fail("No screenshot backend found. Install grim or pyautogui locally, or provide a host capture tool such as grim, spectacle, or import.")


def capture_screen(output_path: Path, region: list[int] | None = None) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_region = normalize_region(region)
    backend_candidates: list[str] = []
    if gamescope_available():
        backend_candidates.append("gamescopectl")
    if command_exists("gnome-screenshot"):
        backend_candidates.append("gnome-screenshot")
    if maybe_import_pyautogui() is not None:
        backend_candidates.append("pyautogui")
    if command_exists("spectacle"):
        backend_candidates.append("spectacle")
    if command_exists("import"):
        backend_candidates.append("import")
    if can_spawn_host() and host_command_exists("spectacle"):
        backend_candidates.append("host-spectacle")
    if can_spawn_host() and host_command_exists("import"):
        backend_candidates.append("host-import")
    if command_exists("grim"):
        backend_candidates.append("grim")
    if host_wayland_tool_available("grim"):
        backend_candidates.append("host-grim")

    if not backend_candidates:
        detect_capture_backend()

    backend = ""
    capture_errors: list[str] = []
    for candidate in backend_candidates:
        try:
            if candidate == "gamescopectl":
                # gamescopectl writes the file ASYNC after returning rc=0.
                # Need explicit GAMESCOPE_WAYLAND_DISPLAY env + post-call wait.
                gs_env = {
                    **os.environ,
                    "GAMESCOPE_WAYLAND_DISPLAY": os.environ.get("GAMESCOPE_WAYLAND_DISPLAY", "gamescope-0"),
                    "WAYLAND_DISPLAY": "gamescope-0",
                    "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000"),
                }
                last_exc: Exception | None = None
                for _ in range(5):
                    try: output_path.unlink()
                    except FileNotFoundError: pass
                    proc = subprocess.run(
                        ["gamescopectl", "screenshot", str(output_path)],
                        env=gs_env, capture_output=True, text=True, timeout=20,
                    )
                    # Poll up to 5s for the async file write to complete.
                    deadline = time.time() + 5.0
                    while time.time() < deadline:
                        if output_path.exists() and output_path.stat().st_size > 50_000:
                            last_exc = None
                            break
                        time.sleep(0.25)
                    if last_exc is None and output_path.exists() and output_path.stat().st_size > 50_000:
                        break
                    last_exc = RuntimeError((proc.stderr or proc.stdout or "empty screenshot after async wait").strip())
                    time.sleep(0.5)
                if last_exc is not None:
                    raise last_exc
            elif candidate == "grim":
                args = ["grim"]
                if normalized_region is not None:
                    left, top, width, height = normalized_region
                    args.extend(["-g", f"{left},{top} {width}x{height}"])
                args.append(str(output_path))
                run_checked_command(args)
            elif candidate == "gnome-screenshot":
                subprocess.run(["gnome-screenshot", "-f", str(output_path)], check=True)
            elif candidate == "pyautogui":
                pyautogui = import_pyautogui()
                pyautogui.screenshot(str(output_path))
            elif candidate == "spectacle":
                result = subprocess.run(["spectacle", "-b", "-n", "-o", str(output_path)], check=False, text=True, capture_output=True)
                if result.returncode != 0:
                    message = (result.stderr or result.stdout or "unknown error").strip()
                    raise RuntimeError(message)
            elif candidate == "import":
                result = subprocess.run(["import", "-window", "root", str(output_path)], check=False, text=True, capture_output=True)
                if result.returncode != 0:
                    message = (result.stderr or result.stdout or "unknown error").strip()
                    raise RuntimeError(message)
            elif candidate == "host-grim":
                args = ["grim"]
                if normalized_region is not None:
                    left, top, width, height = normalized_region
                    args.extend(["-g", f"{left},{top} {width}x{height}"])
                args.append(str(output_path))
                result = run_host_command(args, capture_output=True)
                if result.returncode != 0:
                    message = (result.stderr or result.stdout or "unknown error").strip()
                    raise RuntimeError(message)
            elif candidate == "host-spectacle":
                result = run_host_command(["spectacle", "-b", "-n", "-o", str(output_path)], capture_output=True)
                if result.returncode != 0:
                    message = (result.stderr or result.stdout or "unknown error").strip()
                    raise RuntimeError(message)
            elif candidate == "host-import":
                result = run_host_command(["import", "-window", "root", str(output_path)], capture_output=True)
                if result.returncode != 0:
                    message = (result.stderr or result.stdout or "unknown error").strip()
                    raise RuntimeError(message)
            else:
                raise RuntimeError(f"unknown screenshot backend: {candidate}")
            backend = candidate
            break
        except Exception as exc:
            capture_errors.append(f"{candidate}: {exc}")

    if not backend:
        fail("host screenshot failed: " + " | ".join(capture_errors))

    Image = import_pillow_image()
    deadline = time.time() + 5.0
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with Image.open(output_path) as image:
                image.load()
            break
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    else:
        message = str(last_error) if last_error is not None else "unknown error"
        fail(f"captured screenshot is not readable yet: {message}")

    if (region is not None) and (backend not in {"grim", "host-grim"}):
        left, top, width, height = normalize_region(region)
        with Image.open(output_path) as image:
            cropped = image.crop((left, top, left + width, top + height))
            cropped.save(output_path)

    return backend


def locate_image_with_capture(image_path: Path, timeout: float, confidence: float, grayscale: bool,
                              region: list[int] | None) -> tuple[int, int] | None:
    cv2 = import_cv2()
    offset_x = 0
    offset_y = 0
    temp_dir = Path(__file__).resolve().parent / "artifacts" / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    if region is not None:
        offset_x, offset_y, _, _ = normalize_region(region)

    deadline = time.time() + timeout
    while time.time() < deadline:
        with tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".png", delete=False) as handle:
            screenshot_path = Path(handle.name)
        screenshot_path.unlink(missing_ok=True)

        try:
            capture_screen(screenshot_path, region)
            mode = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
            haystack = cv2.imread(str(screenshot_path), mode)
            needle = cv2.imread(str(image_path), mode)
            if haystack is None:
                fail(f"failed to read screenshot: {screenshot_path}")
            if needle is None:
                fail(f"failed to read template image: {image_path}")

            result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
            _, max_value, _, max_location = cv2.minMaxLoc(result)
            if max_value >= confidence:
                height, width = needle.shape[:2]
                return offset_x + max_location[0] + width // 2, offset_y + max_location[1] + height // 2
        finally:
            screenshot_path.unlink(missing_ok=True)

        time.sleep(0.2)

    return None


def ensure_image_visible(
    *,
    image_path: Path,
    overall_timeout: float,
    confidence: float,
    grayscale: bool,
    region: list[int] | None,
    recovery_key: str | None,
    recovery_presses: int,
    recovery_interval: float,
    recovery_sleep: float,
    attempt_timeout: float,
    dry_run: bool,
) -> tuple[int, int] | None:
    deadline = time.time() + overall_timeout
    backend: str | None = None
    if not dry_run:
        backend = detect_input_backend()

    while time.time() < deadline:
        remaining = max(0.5, deadline - time.time())
        point = locate_image(
            None,
            image_path,
            timeout=min(attempt_timeout, remaining),
            confidence=confidence,
            grayscale=grayscale,
            region=region,
        )
        if point is not None:
            return point
        if dry_run or not recovery_key:
            continue
        focus_game_window(backend)
        press_key(
            backend,
            recovery_key,
            presses=max(1, recovery_presses),
            interval=recovery_interval,
        )
        if recovery_sleep > 0:
            time.sleep(recovery_sleep)

    return None


def normalize_ocr_string(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def normalize_ocr_token(value: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", value.lower())


def preprocess_ocr_image(image, grayscale: bool, threshold: int | None):
    if grayscale:
        image = image.convert("L")
    if threshold is not None:
        threshold_value = max(0, min(255, int(threshold)))
        image = image.point(lambda pixel: 255 if pixel >= threshold_value else 0)
    return image


def extract_ocr_entries(region: list[int] | None, grayscale: bool, threshold: int | None,
                        psm: int) -> tuple[list[dict[str, Any]], str]:
    pytesseract = import_pytesseract()
    pytesseract.pytesseract.tesseract_cmd = resolve_tesseract_command()
    Image = import_pillow_image()
    temp_dir = Path(__file__).resolve().parent / "artifacts" / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # When the caller passes a region, capture_screen() crops to it and
    # tesseract returns box coords relative to the crop's top-left. Without
    # adding the region origin back, downstream click_text/wait_text would
    # land off-target by (region_left, region_top) — which is exactly the
    # 2026-05-10 lobby-flow bug. Mirror locate_image_with_capture's behavior
    # and apply the offset here so OCR-driven flows can finally use `region`
    # for speed without click misalignment.
    offset_x = 0
    offset_y = 0
    if region is not None:
        normalized = normalize_region(region)
        if normalized is not None:
            offset_x, offset_y, _, _ = normalized

    with tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".png", delete=False) as handle:
        screenshot_path = Path(handle.name)
    screenshot_path.unlink(missing_ok=True)

    try:
        capture_screen(screenshot_path, region)
        with Image.open(screenshot_path) as image:
            processed = preprocess_ocr_image(image, grayscale=grayscale, threshold=threshold)
            data = pytesseract.image_to_data(
                processed,
                config=f"--psm {int(psm)}",
                output_type=pytesseract.Output.DICT,
            )
    finally:
        screenshot_path.unlink(missing_ok=True)

    entries: list[dict[str, Any]] = []
    total_items = len(data.get("text", []))
    for index in range(total_items):
        raw_text = str(data["text"][index]).strip()
        if raw_text == "":
            continue

        try:
            confidence = float(data.get("conf", ["-1"])[index])
        except Exception:
            confidence = -1.0
        if confidence < 0:
            continue

        entry = {
            "text": raw_text,
            "normalized": normalize_ocr_string(raw_text),
            "token": normalize_ocr_token(raw_text),
            "left": int(data["left"][index]) + offset_x,
            "top": int(data["top"][index]) + offset_y,
            "width": int(data["width"][index]),
            "height": int(data["height"][index]),
            "block": int(data["block_num"][index]),
            "paragraph": int(data["par_num"][index]),
            "line": int(data["line_num"][index]),
            "word": int(data["word_num"][index]),
            "confidence": confidence,
        }
        entries.append(entry)

    full_text = normalize_ocr_string(" ".join(entry["text"] for entry in entries))
    return entries, full_text


def target_texts_from_step(step: dict[str, Any], field_name: str = "text") -> list[str]:
    single_value = step.get(field_name)
    if isinstance(single_value, str) and single_value.strip() != "":
        return [single_value]

    plural_value = step.get("texts")
    if isinstance(plural_value, list):
        targets = [str(value) for value in plural_value if str(value).strip() != ""]
        if targets:
            return targets

    fail(f"{field_name} action requires 'text' or a non-empty 'texts' array")


def build_ocr_line_groups(entries: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for entry in entries:
        key = (entry["block"], entry["paragraph"], entry["line"])
        grouped.setdefault(key, []).append(entry)

    lines: list[list[dict[str, Any]]] = []
    for key in sorted(grouped.keys()):
        lines.append(sorted(grouped[key], key=lambda item: item["word"]))
    return lines


def collect_text_box_matches(entries: list[dict[str, Any]], targets: list[str], partial: bool) -> list[tuple[int, int, str]]:
    normalized_targets = [normalize_ocr_string(target) for target in targets]
    token_targets = [
        [token for token in (normalize_ocr_token(part) for part in target.split()) if token != ""]
        for target in targets
    ]

    matches: list[tuple[int, int, str]] = []

    for line_entries in build_ocr_line_groups(entries):
        line_text = normalize_ocr_string(" ".join(entry["text"] for entry in line_entries))
        line_tokens = [entry["token"] for entry in line_entries]

        for target, normalized_target, target_tokens in zip(targets, normalized_targets, token_targets):
            if normalized_target == "":
                continue

            if partial and normalized_target in line_text and target_tokens:
                if len(target_tokens) == 1:
                    for entry in line_entries:
                        if target_tokens[0] in entry["token"]:
                            center_x = entry["left"] + entry["width"] // 2
                            center_y = entry["top"] + entry["height"] // 2
                            matches.append((center_x, center_y, target))
                    continue
                else:
                    joined_tokens = " ".join(token for token in line_tokens if token != "")
                    joined_target = " ".join(target_tokens)
                    if joined_target not in joined_tokens:
                        continue

            if not target_tokens:
                continue

            window = len(target_tokens)
            for start_index in range(0, len(line_entries) - window + 1):
                candidate_entries = line_entries[start_index:start_index + window]
                candidate_tokens = [entry["token"] for entry in candidate_entries]
                if partial:
                    if len(target_tokens) == 1:
                        if target_tokens[0] not in candidate_tokens[0]:
                            continue
                    else:
                        if candidate_tokens != target_tokens:
                            continue
                else:
                    if candidate_tokens != target_tokens:
                        continue

                left = min(entry["left"] for entry in candidate_entries)
                top = min(entry["top"] for entry in candidate_entries)
                right = max(entry["left"] + entry["width"] for entry in candidate_entries)
                bottom = max(entry["top"] + entry["height"] for entry in candidate_entries)
                matches.append((left + (right - left) // 2, top + (bottom - top) // 2, target))

    return matches


def locate_text_box(entries: list[dict[str, Any]], targets: list[str], partial: bool,
                    match_index: int = 0) -> tuple[int, int, str] | None:
    if match_index < 0:
        fail("matchIndex must be greater than or equal to 0")

    matches = collect_text_box_matches(entries, targets=targets, partial=partial)
    if match_index >= len(matches):
        return None
    return matches[match_index]


def locate_text_with_capture(targets: list[str], timeout: float, region: list[int] | None, partial: bool,
                             grayscale: bool, threshold: int | None, psm: int,
                             match_index: int = 0) -> tuple[int | None, int | None, str] | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        entries, full_text = extract_ocr_entries(region=region, grayscale=grayscale, threshold=threshold, psm=psm)
        box = locate_text_box(entries, targets=targets, partial=partial, match_index=match_index)
        if box is not None:
            return box

        for target in targets:
            normalized_target = normalize_ocr_string(target)
            if normalized_target == "":
                continue
            if partial:
                if normalized_target in full_text:
                    return None, None, target
            else:
                full_text_tokens = full_text.split()
                target_tokens = normalized_target.split()
                if target_tokens and target_tokens == full_text_tokens[:len(target_tokens)]:
                    return None, None, target
                if f" {normalized_target} " in f" {full_text} ":
                    return None, None, target

        time.sleep(0.5)

    return None


def normalize_key_name(key: str) -> str:
    if key.startswith("Key."):
        key = key[4:]

    mapping = {
        "alt": "Alt_L",
        "backspace": "BackSpace",
        "ctrl": "Control_L",
        "control": "Control_L",
        "delete": "Delete",
        "down": "Down",
        "enter": "Return",
        "esc": "Escape",
        "escape": "Escape",
        "left": "Left",
        "pagedown": "Next",
        "pageup": "Prior",
        "pgdn": "Next",
        "pgup": "Prior",
        "return": "Return",
        "right": "Right",
        "shift": "Shift_L",
        "space": "space",
        "tab": "Tab",
        "up": "Up",
    }
    return mapping.get(key.lower(), key)


def run_gamescope_xdotool(args: list[str]) -> None:
    env = {
        **os.environ,
        "DISPLAY": ":1",
        "XAUTHORITY": os.environ.get("XAUTHORITY", ""),
    }
    result = subprocess.run(["xdotool", *args], env=env, capture_output=True, text=True)
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "unknown error").strip()
        fail(f"gamescope xdotool failed: {msg}")


def move_pointer(backend: str, x: int, y: int, duration: float = 0.0) -> None:
    if backend == "gamescope_xdotool":
        run_gamescope_xdotool(["mousemove", str(x), str(y)])
        return
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        pyautogui.moveTo(x, y, duration=duration)
        return
    if backend in {"local_wayland", "host_wayland"}:
        run_wayland_command(backend, ["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)])
        return
    if backend == "host_xdotool":
        focus_host_game_window()
        run_host_command(["xdotool", "mousemove", str(x), str(y)])
        return
    fail(f"unknown input backend: {backend}")


def click_pointer(backend: str, button: str = "left", presses: int = 1) -> None:
    if backend == "gamescope_xdotool":
        button_map = {"left": "1", "middle": "2", "right": "3"}
        run_gamescope_xdotool(["click", "--repeat", str(max(1, presses)), button_map.get(button, "1")])
        return
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        if presses == 2:
            pyautogui.doubleClick(button=button)
        else:
            pyautogui.click(button=button, clicks=presses)
        return
    if backend in {"local_wayland", "host_wayland"}:
        button_map = {"left": "0xC0", "right": "0xC1", "middle": "0xC2"}
        args = ["ydotool", "click"]
        if presses > 1:
            args.extend(["--repeat", str(max(1, presses)), "--next-delay", "50"])
        args.append(button_map.get(button, "0xC0"))
        run_wayland_command(backend, args)
        return
    if backend == "host_xdotool":
        button_map = {"left": "1", "middle": "2", "right": "3"}
        x_button = button_map.get(button, "1")
        focus_host_game_window()
        run_host_command(["xdotool", "click", "--repeat", str(max(1, presses)), x_button])
        return
    fail(f"unknown input backend: {backend}")


def mouse_button(backend: str, button: str, pressed: bool) -> None:
    if backend == "gamescope_xdotool":
        button_map = {"left": "1", "middle": "2", "right": "3"}
        action = "mousedown" if pressed else "mouseup"
        run_gamescope_xdotool([action, button_map.get(button, "1")])
        return
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        if pressed:
            pyautogui.mouseDown(button=button)
        else:
            pyautogui.mouseUp(button=button)
        return
    if backend in {"local_wayland", "host_wayland"}:
        fail("Wayland ydotool backend does not support replaying separate mouse down/up events. Use run-flow instead of replay-input.")
    if backend == "host_xdotool":
        button_map = {"left": "1", "middle": "2", "right": "3"}
        x_button = button_map.get(button, "1")
        action = "mousedown" if pressed else "mouseup"
        focus_host_game_window()
        run_host_command(["xdotool", action, x_button])
        return
    fail(f"unknown input backend: {backend}")


def press_key(backend: str, key: str, presses: int = 1, interval: float = 0.05) -> None:
    if backend == "gamescope_xdotool":
        normalized = normalize_key_name(key)
        for index in range(max(1, presses)):
            run_gamescope_xdotool(["key", normalized])
            if index + 1 < presses:
                time.sleep(interval)
        return
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        pyautogui.press(key, presses=presses, interval=interval)
        return
    if backend in {"local_wayland", "host_wayland"}:
        normalized = normalize_wayland_key_name(key)
        try:
            for index in range(max(1, presses)):
                run_wayland_command(backend, ["wtype", "-P", normalized, "-p", normalized])
                if index + 1 < presses:
                    time.sleep(interval)
            return
        except SystemExit:
            if backend != "host_wayland" or not host_xdotool_available():
                raise
            backend = "host_xdotool"
            normalized = normalize_key_name(key)
            for index in range(max(1, presses)):
                run_host_xdotool_window_command(["key", normalized])
                if index + 1 < presses:
                    time.sleep(interval)
        return
    if backend == "host_xdotool":
        normalized = normalize_key_name(key)
        for index in range(max(1, presses)):
            run_host_xdotool_window_command(["key", normalized])
            if index + 1 < presses:
                time.sleep(interval)
        return
    fail(f"unknown input backend: {backend}")


def key_state(backend: str, key: str, pressed: bool) -> None:
    if backend == "gamescope_xdotool":
        action = "keydown" if pressed else "keyup"
        run_gamescope_xdotool([action, normalize_key_name(key)])
        return
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        if pressed:
            pyautogui.keyDown(key)
        else:
            pyautogui.keyUp(key)
        return
    if backend in {"local_wayland", "host_wayland"}:
        action = "-P" if pressed else "-p"
        run_wayland_command(backend, ["wtype", action, normalize_wayland_key_name(key)])
        return
    if backend == "host_xdotool":
        action = "keydown" if pressed else "keyup"
        run_host_xdotool_window_command([action, normalize_key_name(key)])
        return
    fail(f"unknown input backend: {backend}")


def press_hotkey(backend: str, keys: list[str]) -> None:
    if backend == "gamescope_xdotool":
        chord = "+".join(normalize_key_name(key) for key in keys)
        run_gamescope_xdotool(["key", chord])
        return
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        pyautogui.hotkey(*keys)
        return
    if backend in {"local_wayland", "host_wayland"}:
        modifier_map = {
            "alt": "alt",
            "alt_l": "alt",
            "control": "ctrl",
            "control_l": "ctrl",
            "ctrl": "ctrl",
            "shift": "shift",
            "shift_l": "shift",
            "super": "super",
            "super_l": "super",
        }
        normalized_keys = [normalize_wayland_key_name(key) for key in keys]
        args = ["wtype"]
        non_modifiers: list[str] = []
        modifiers_to_release: list[str] = []
        for normalized in normalized_keys:
            modifier = modifier_map.get(normalized.lower())
            if modifier is not None:
                args.extend(["-M", modifier])
                modifiers_to_release.append(modifier)
            else:
                non_modifiers.append(normalized)

        if len(non_modifiers) == 0:
            fail("hotkey action requires at least one non-modifier key")

        final_key = non_modifiers[-1]
        args.extend(["-P", final_key, "-p", final_key])
        for modifier in reversed(modifiers_to_release):
            args.extend(["-m", modifier])
        run_wayland_command(backend, args)
        return
    if backend == "host_xdotool":
        chord = "+".join(normalize_key_name(key) for key in keys)
        run_host_xdotool_window_command(["key", chord])
        return
    fail(f"unknown input backend: {backend}")


def type_text(backend: str, text: str, interval: float = 0.02) -> None:
    if backend == "gamescope_xdotool":
        delay_ms = max(1, int(interval * 1000))
        run_gamescope_xdotool(["type", "--delay", str(delay_ms), text])
        return
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        pyautogui.write(text, interval=interval)
        return
    if backend in {"local_wayland", "host_wayland"}:
        delay_ms = max(0, int(interval * 1000))
        run_wayland_command(backend, ["wtype", "-d", str(delay_ms), text])
        return
    if backend == "host_xdotool":
        delay_ms = max(1, int(interval * 1000))
        run_host_xdotool_window_command(["type", "--delay", str(delay_ms), text])
        return
    fail(f"unknown input backend: {backend}")


def scroll_pointer(backend: str, clicks: int) -> None:
    if backend == "pyautogui":
        pyautogui = import_pyautogui()
        pyautogui.scroll(clicks)
        return
    if backend in {"local_wayland", "host_wayland"}:
        fail("Wayland backend does not currently support scroll emulation. Prefer click_image flows that avoid wheel input.")
    if backend == "host_xdotool":
        button = "4" if clicks > 0 else "5"
        for _ in range(abs(clicks)):
            run_host_command(["xdotool", "click", button])
        return
    fail(f"unknown input backend: {backend}")


def try_capture_screenshot(output_path: Path) -> str | None:
    try:
        return capture_screen(output_path)
    except SystemExit:
        return None
    except Exception:
        return None


def collect_artifacts(output_dir: Path, log_dir: Path, include_screenshot: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied_any = False

    for log_name in ["Age3Log.txt", "Age3SessionData.txt"]:
        source = log_dir / log_name
        if not source.exists():
            continue
        shutil.copy2(source, output_dir / log_name)
        copied_any = True

    if include_screenshot:
        screenshot_path = output_dir / "desktop.png"
        backend = try_capture_screenshot(screenshot_path)
        if backend is not None:
            copied_any = True
            print(f"Captured screenshot via {backend}: {screenshot_path}")
        else:
            print("warning: screenshot capture backend unavailable", file=sys.stderr)

    if not copied_any:
        fail(f"No artifacts were collected from {log_dir}")

    print(f"Artifacts written to {output_dir}")


def probe_environment() -> None:
    print(f"session_type: {os.environ.get('XDG_SESSION_TYPE', 'unknown')}")
    print(f"display: {os.environ.get('DISPLAY', '') or '<unset>'}")
    print(f"wayland_display: {os.environ.get('WAYLAND_DISPLAY', '') or '<unset>'}")
    for command in ["ydotool", "wtype", "grim", "slurp", "gnome-screenshot", "xdotool", "tesseract"]:
        print(f"{command}: {'yes' if command_exists(command) else 'no'}")

    print(f"local_wayland_input_ready: {'yes' if local_wayland_input_available() else 'no'}")

    print(f"flatpak_spawn: {'yes' if can_spawn_host() else 'no'}")
    if can_spawn_host():
        for command in ["xdotool", "spectacle", "import", "grim", "wtype", "ydotool", "ydotoold", "tesseract"]:
            print(f"host_{command}: {'yes' if host_command_exists(command) else 'no'}")
        print(f"host_xdotool_ready: {'yes' if host_xdotool_available() else 'no'}")
        print(f"host_wayland_input_ready: {'yes' if host_wayland_input_available() else 'no'}")
        print(f"host_ydotoold_running: {'yes' if host_ydotool_daemon_running() else 'no'}")

    for module in ["pyautogui", "PIL", "mss", "pynput", "pytesseract"]:
        try:
            __import__(module)
            print(f"{module}: yes")
        except Exception:
            print(f"{module}: no")


def import_pyautogui():
    try:
        import pyautogui  # type: ignore
    except Exception as exc:
        fail(f"pyautogui import failed: {exc}")
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    return pyautogui


def maybe_import_pyautogui():
    try:
        import pyautogui  # type: ignore
    except Exception:
        return None
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    return pyautogui


def import_pynput():
    try:
        from pynput import keyboard, mouse  # type: ignore
    except Exception as exc:
        fail(f"pynput import failed: {exc}")
    return keyboard, mouse


def resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def normalize_region(region: list[int] | None) -> tuple[int, int, int, int] | None:
    if region is None:
        return None
    if len(region) != 4:
        fail("region must contain exactly 4 integers: [left, top, width, height]")
    return tuple(int(value) for value in region)


def normalize_wayland_key_name(key: str) -> str:
    if key.startswith("Key."):
        key = key[4:]

    mapping = {
        "alt": "alt",
        "backspace": "BackSpace",
        "ctrl": "ctrl",
        "control": "ctrl",
        "delete": "Delete",
        "down": "Down",
        "enter": "Return",
        "esc": "Escape",
        "escape": "Escape",
        "left": "Left",
        "pagedown": "Next",
        "pageup": "Prior",
        "pgdn": "Next",
        "pgup": "Prior",
        "return": "Return",
        "right": "Right",
        "shift": "shift",
        "space": "space",
        "super": "super",
        "tab": "Tab",
        "up": "Up",
    }
    return mapping.get(key.lower(), key)


def locate_image(pyautogui, image_path: Path, timeout: float, confidence: float, grayscale: bool,
                 region: list[int] | None) -> tuple[int, int] | None:
    if pyautogui is None:
        return locate_image_with_capture(image_path, timeout, confidence, grayscale, region)

    deadline = time.time() + timeout
    search_region = normalize_region(region)
    while time.time() < deadline:
        try:
            point = pyautogui.locateCenterOnScreen(
                str(image_path),
                confidence=confidence,
                grayscale=grayscale,
                region=search_region,
            )
        except TypeError:
            point = pyautogui.locateCenterOnScreen(str(image_path), grayscale=grayscale, region=search_region)
        if point is not None:
            return int(point.x), int(point.y)
        time.sleep(0.2)
    return None


def _interpolate_step(step: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of *step* with ``${VAR}`` placeholders in all
    string values replaced with the matching environment variable.

    Only string values are interpolated; nested lists of strings (e.g.
    the ``texts`` list) are interpolated element-by-element.  If a
    referenced variable is not set in the environment the placeholder is
    left as-is so downstream validators can surface the issue clearly.
    """
    def _sub(s: str) -> str:
        return re.sub(
            r"\$\{([^}]+)\}",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            s,
        )

    out: dict[str, Any] = {}
    for key, value in step.items():
        if isinstance(value, str):
            out[key] = _sub(value)
        elif isinstance(value, list):
            out[key] = [_sub(v) if isinstance(v, str) else v for v in value]
        else:
            out[key] = value
    return out


def run_flow(flow_path: Path, dry_run: bool) -> None:
    if not dry_run:
        detect_input_backend()
    payload = load_json(flow_path)
    if not isinstance(payload, dict):
        fail("flow file must contain an object")
    steps = payload.get("steps")
    if not isinstance(steps, list):
        fail("flow file must contain a 'steps' array")

    base_dir = flow_path.parent
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            fail(f"flow step {index} is not an object")
        # Apply ${VAR} substitution from environment before processing.
        step = _interpolate_step(step)
        action = step.get("action")
        if not isinstance(action, str):
            fail(f"flow step {index} is missing an action")
        optional = bool(step.get("optional", False))

        print(f"[{index}/{len(steps)}] {action}")

        try:
            if action == "launch":
                command = step.get("command")
                if not command:
                    fail("launch action requires 'command'")
                if dry_run:
                    continue
                if isinstance(command, str):
                    subprocess.Popen(command, shell=True)
                elif isinstance(command, list):
                    subprocess.Popen(command)
                else:
                    fail("launch command must be a string or array")
            elif action == "sleep":
                seconds = float(step.get("seconds", 1.0))
                time.sleep(seconds)
            elif action == "focus_window":
                if dry_run:
                    continue
                backend = detect_input_backend()
                timeout_seconds = float(step.get("timeout", 30.0))
                poll_interval_seconds = float(step.get("pollInterval", 1.0))
                if not wait_for_game_window_focus(backend, timeout_seconds, poll_interval_seconds):
                    fail("could not find or focus the Age of Empires III window")
            elif action in {"wait_image", "click_image"}:
                image = step.get("image")
                if not isinstance(image, str):
                    fail(f"{action} requires 'image'")
                image_path = resolve_path(base_dir, image)
                if not image_path.exists():
                    fail(f"image not found: {image_path}")
                point = locate_image(
                    None,
                    image_path,
                    timeout=float(step.get("timeout", 20.0)),
                    confidence=float(step.get("confidence", 0.92)),
                    grayscale=bool(step.get("grayscale", False)),
                    region=step.get("region"),
                )
                if point is None:
                    fail(f"timed out waiting for image: {image_path}")
                if action == "click_image" and not dry_run:
                    backend = detect_input_backend()
                    offset = step.get("offset", [0, 0])
                    x = int(point[0] + int(offset[0]))
                    y = int(point[1] + int(offset[1]))
                    move_pointer(backend, x, y, duration=float(step.get("moveDuration", 0.15)))
                    click_pointer(backend, presses=2 if step.get("double", False) else 1)
            elif action == "ensure_image":
                image = step.get("image")
                if not isinstance(image, str):
                    fail("ensure_image requires 'image'")
                image_path = resolve_path(base_dir, image)
                if not image_path.exists():
                    fail(f"image not found: {image_path}")
                point = ensure_image_visible(
                    image_path=image_path,
                    overall_timeout=float(step.get("timeout", 20.0)),
                    confidence=float(step.get("confidence", 0.92)),
                    grayscale=bool(step.get("grayscale", False)),
                    region=step.get("region"),
                    recovery_key=str(step.get("recoveryKey")) if step.get("recoveryKey") is not None else None,
                    recovery_presses=int(step.get("recoveryPresses", 1)),
                    recovery_interval=float(step.get("recoveryInterval", 0.1)),
                    recovery_sleep=float(step.get("recoverySleep", 0.5)),
                    attempt_timeout=float(step.get("attemptTimeout", 2.0)),
                    dry_run=dry_run,
                )
                if point is None:
                    fail(f"timed out ensuring image: {image_path}")
            elif action in {"wait_text", "click_text"}:
                targets = target_texts_from_step(step)
                match = locate_text_with_capture(
                    targets=targets,
                    timeout=float(step.get("timeout", 20.0)),
                    region=step.get("region"),
                    partial=bool(step.get("partial", True)),
                    grayscale=bool(step.get("grayscale", True)),
                    threshold=int(step["threshold"]) if "threshold" in step else None,
                    psm=int(step.get("psm", 6)),
                    match_index=int(step.get("matchIndex", 0)),
                )
                if match is None:
                    fail(f"timed out waiting for text: {targets}")
                if action == "click_text" and not dry_run:
                    x, y, matched_text = match
                    if x is None or y is None:
                        fail(f"matched text without clickable OCR box: {matched_text}")
                    backend = detect_input_backend()
                    offset = step.get("offset", [0, 0])
                    move_pointer(
                        backend,
                        int(x + int(offset[0])),
                        int(y + int(offset[1])),
                        duration=float(step.get("moveDuration", 0.15)),
                    )
                    click_pointer(backend, presses=2 if step.get("double", False) else 1)
            elif action == "click":
                if dry_run:
                    continue
                backend = detect_input_backend()
                move_pointer(backend, int(step["x"]), int(step["y"]), duration=float(step.get("moveDuration", 0.15)))
                click_pointer(backend)
            elif action == "press":
                if dry_run:
                    continue
                backend = detect_input_backend()
                key = step.get("key")
                if not isinstance(key, str):
                    fail("press action requires 'key'")
                press_key(backend, key, presses=int(step.get("presses", 1)), interval=float(step.get("interval", 0.05)))
            elif action == "hotkey":
                if dry_run:
                    continue
                backend = detect_input_backend()
                keys = step.get("keys")
                if not isinstance(keys, list) or not keys:
                    fail("hotkey action requires a non-empty 'keys' array")
                press_hotkey(backend, [str(key) for key in keys])
            elif action == "type_text":
                if dry_run:
                    continue
                backend = detect_input_backend()
                text = step.get("text")
                if not isinstance(text, str):
                    fail("type_text action requires 'text'")
                type_text(backend, text, interval=float(step.get("interval", 0.02)))
            elif action == "scroll":
                if dry_run:
                    continue
                backend = detect_input_backend()
                scroll_pointer(backend, int(step.get("clicks", 0)))
            elif action == "screenshot":
                output = step.get("path")
                if not isinstance(output, str):
                    fail("screenshot action requires 'path'")
                output_path = resolve_path(base_dir, output)
                if not dry_run:
                    capture_screen(output_path)
            else:
                fail(f"unknown action: {action}")
        except SystemExit as exc:
            if optional:
                message = str(exc) if str(exc) else f"optional step failed: {action}"
                print(f"warning: optional step skipped: {message}", file=sys.stderr)
                continue
            raise


def record_input(output_path: Path) -> None:
    ensure_runtime_support(needs_input=True)
    keyboard, mouse = import_pynput()
    events: list[dict[str, Any]] = []
    start = time.perf_counter()
    last_move_time = 0.0
    last_position: tuple[int, int] | None = None
    stop_state = {"active": False}

    def now() -> float:
        return round(time.perf_counter() - start, 4)

    def record(payload: dict[str, Any]) -> None:
        payload["t"] = now()
        events.append(payload)

    def on_move(x: int, y: int) -> None:
        nonlocal last_move_time, last_position
        current_time = time.perf_counter()
        if last_position is not None:
            dx = x - last_position[0]
            dy = y - last_position[1]
            if current_time - last_move_time < 0.02 and math.hypot(dx, dy) < 4.0:
                return
        last_move_time = current_time
        last_position = (x, y)
        record({"type": "move", "x": x, "y": y})

    def on_click(x: int, y: int, button, pressed: bool) -> None:
        record({"type": "click", "x": x, "y": y, "button": str(button), "pressed": pressed})

    def on_scroll(x: int, y: int, dx: int, dy: int) -> None:
        record({"type": "scroll", "x": x, "y": y, "dx": dx, "dy": dy})

    def normalize_key(key) -> str:
        if hasattr(key, "char") and key.char is not None:
            return key.char
        return str(key)

    def on_press(key) -> None:
        key_name = normalize_key(key)
        record({"type": "key_press", "key": key_name})
        if key_name == "Key.esc":
            stop_state["active"] = True
            return False
        return None

    def on_release(key) -> None:
        record({"type": "key_release", "key": normalize_key(key)})
        return None

    print("Recording started. Press Esc to stop.")
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    mouse_listener.start()
    keyboard_listener.start()
    keyboard_listener.join()
    mouse_listener.stop()
    mouse_listener.join()

    payload = {
        "version": 1,
        "recordedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "events": events,
    }
    dump_json(output_path, payload)
    print(f"Recorded {len(events)} events to {output_path}")


def replay_input(input_path: Path, speed: float) -> None:
    backend = detect_input_backend()
    payload = load_json(input_path)
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        fail("recording must contain an 'events' array")

    previous_time = 0.0
    button_map = {
        "Button.left": "left",
        "Button.middle": "middle",
        "Button.right": "right",
    }

    for event in events:
        if not isinstance(event, dict):
            continue
        event_time = float(event.get("t", 0.0))
        delay = max(0.0, (event_time - previous_time) / max(speed, 0.01))
        time.sleep(delay)
        previous_time = event_time

        event_type = event.get("type")
        if event_type == "move":
            move_pointer(backend, int(event["x"]), int(event["y"]))
        elif event_type == "click":
            button = button_map.get(str(event.get("button")), "left")
            x = int(event["x"])
            y = int(event["y"])
            move_pointer(backend, x, y)
            if bool(event.get("pressed", False)):
                mouse_button(backend, button, True)
            else:
                mouse_button(backend, button, False)
        elif event_type == "scroll":
            scroll_pointer(backend, int(event.get("dy", 0)))
        elif event_type == "key_press":
            key_name = str(event.get("key"))
            key_state(backend, key_name, True)
        elif event_type == "key_release":
            key_name = str(event.get("key"))
            key_state(backend, key_name, False)


def capture_reference(output_path: Path, region: list[int] | None) -> None:
    ensure_runtime_support(needs_input=False)
    capture_screen(output_path, region)
    print(f"Saved reference image to {output_path}")


def capture_loop(output_dir: Path, interval: float, count: int, region: list[int] | None) -> None:
    ensure_runtime_support(needs_input=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    latest_path = output_dir / "latest.png"
    iteration = 0

    while count <= 0 or iteration < count:
        iteration += 1
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"screen_{timestamp}_{iteration:04d}.png"
        backend = capture_screen(output_path, region)
        shutil.copy2(output_path, latest_path)
        print(f"[{iteration}] Captured via {backend}: {output_path}")
        if count > 0 and iteration >= count:
            break
        time.sleep(max(0.1, interval))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AoE3 DE desktop automation helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-flow", help="Run an image-driven UI flow")
    run_parser.add_argument("flow", type=Path)
    run_parser.add_argument("--dry-run", action="store_true")

    record_parser = subparsers.add_parser("record-input", help="Record mouse and keyboard input until Esc")
    record_parser.add_argument("output", type=Path)

    replay_parser = subparsers.add_parser("replay-input", help="Replay a previously recorded input timeline")
    replay_parser.add_argument("input", type=Path)
    replay_parser.add_argument("--speed", type=float, default=1.0)

    capture_parser = subparsers.add_parser("capture-reference", help="Capture a screenshot for image matching")
    capture_parser.add_argument("output", type=Path)
    capture_parser.add_argument("--region", nargs=4, type=int)

    watch_parser = subparsers.add_parser("capture-loop", help="Capture repeated screenshots at a fixed interval")
    watch_parser.add_argument("output", type=Path)
    watch_parser.add_argument("--interval", type=float, default=1.0)
    watch_parser.add_argument("--count", type=int, default=0, help="Number of screenshots to capture. Use 0 to run until stopped.")
    watch_parser.add_argument("--region", nargs=4, type=int)

    probe_parser = subparsers.add_parser("probe-environment", help="Report available desktop automation backends")

    artifacts_parser = subparsers.add_parser("collect-artifacts", help="Copy AoE3 logs and an optional screenshot")
    artifacts_parser.add_argument("output", type=Path)
    artifacts_parser.add_argument("--log-dir", type=Path, default=default_aoe3_log_dir())
    artifacts_parser.add_argument("--screenshot", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run-flow":
        run_flow(args.flow.resolve(), args.dry_run)
    elif args.command == "record-input":
        record_input(args.output.resolve())
    elif args.command == "replay-input":
        replay_input(args.input.resolve(), args.speed)
    elif args.command == "capture-reference":
        capture_reference(args.output.resolve(), args.region)
    elif args.command == "capture-loop":
        capture_loop(args.output.resolve(), args.interval, args.count, args.region)
    elif args.command == "probe-environment":
        probe_environment()
    elif args.command == "collect-artifacts":
        collect_artifacts(args.output.resolve(), args.log_dir.resolve(), args.screenshot)
    else:
        parser.error("unknown command")


if __name__ == "__main__":
    main()