"""Async tail of Age3Log.txt and per-AI output files.

Used by supervisor.py to provide live probe feedback during a match,
and to detect a match-complete marker if one is added in the future.

NOTE: Phase 0 does not require a completion marker — the match runs for
MATCH_DURATION_S and supervisor waits that fixed duration. This module
is a quality-of-life enhancement and preparation for Phase 1 event-driven
completion detection.

Key paths:
  AGE3_LOG_PATH — from log_capture module
  AI_OUTPUT_DIR — same Logs/ directory, glob Age3DEAIOutputPlayer*.txt
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from tools.aoe3_automation.log_capture import AGE3_LOG_PATH
from tools.aoe3_harness.paths import AI_OUTPUT_DIR, AI_OUTPUT_GLOB


def tail_file(
    path: Path,
    callback: Callable[[str], None],
    poll_interval: float = 0.5,
    stop_event: Optional[threading.Event] = None,
) -> threading.Thread:
    """Tail a file and call callback for each new line.

    Polls the file for new content at ``poll_interval`` seconds.  Each new
    line (stripped of the trailing newline) is passed to ``callback``.  The
    thread is a daemon thread and will stop when ``stop_event`` is set or when
    the main thread exits.

    Args:
        path: Path to the file to tail.
        callback: Called with each new line (str, without trailing newline).
        poll_interval: Seconds between polls.
        stop_event: Optional event; set it to stop the tail thread.

    Returns:
        A started daemon Thread.
    """
    if stop_event is None:
        stop_event = threading.Event()

    def _run() -> None:
        offset = 0
        if path.exists():
            offset = path.stat().st_size

        while not stop_event.is_set():
            try:
                if path.exists():
                    size = path.stat().st_size
                    if size < offset:
                        # File was truncated (game relaunched); reset.
                        offset = 0
                    if size > offset:
                        with path.open("rb") as fh:
                            fh.seek(offset)
                            chunk = fh.read(size - offset)
                        offset = size
                        text = chunk.decode("utf-8", errors="replace")
                        for line in text.splitlines():
                            callback(line)
            except OSError:
                pass
            stop_event.wait(poll_interval)

    t = threading.Thread(target=_run, daemon=True, name=f"tail:{path.name}")
    t.start()
    return t


def tail_all(
    callback: Callable[[str, str], None],
    poll_interval: float = 0.5,
    stop_event: Optional[threading.Event] = None,
) -> list[threading.Thread]:
    """Tail Age3Log.txt and all Age3DEAIOutputPlayer*.txt in parallel.

    All log sources are tailed simultaneously.  Each new line from any
    source triggers ``callback(filename, line)`` where ``filename`` is
    the base filename (e.g. ``"Age3Log.txt"`` or
    ``"Age3DEAIOutputPlayer2.txt"``).

    Args:
        callback: Called with (filename: str, line: str) for each new line.
        poll_interval: Seconds between polls.
        stop_event: Optional shared event; set it to stop all tail threads.

    Returns:
        A list of started daemon Threads (one per file being tailed).
    """
    if stop_event is None:
        stop_event = threading.Event()

    threads: list[threading.Thread] = []

    # Tail main log
    def _main_cb(line: str) -> None:
        callback(AGE3_LOG_PATH.name, line)

    threads.append(
        tail_file(AGE3_LOG_PATH, _main_cb, poll_interval, stop_event)
    )

    # Tail per-AI files (both existing and those appearing during the match)
    ai_files = sorted(AI_OUTPUT_DIR.glob(AI_OUTPUT_GLOB)) if AI_OUTPUT_DIR.exists() else []
    for ai_path in ai_files:
        ai_name = ai_path.name  # closure capture

        def _ai_cb(line: str, name: str = ai_name) -> None:
            callback(name, line)

        threads.append(
            tail_file(ai_path, _ai_cb, poll_interval, stop_event)
        )

    return threads
