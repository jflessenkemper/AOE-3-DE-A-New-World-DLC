"""Age3Log.txt per-match slice capture helper.

AoE3 DE appends all output — including aiEcho() lines from the XS AI scripts —
to a single Age3Log.txt file.  To attribute probes to a specific match we:

  1. Snapshot the file's byte offset BEFORE starting the match.
  2. After resigning, read from that offset to end-of-file.
  3. Save the delta as ``match.log`` next to the other match artefacts.

The validator (tools/playtest/replay_probes.py) then parses match.log directly
for ``[ANWP v=2 ...]`` lines — no decompression or replay parsing needed.

Dev-mode requirement
--------------------
aiEcho() only writes to Age3Log.txt when the game runs with developer mode
enabled.  On this rig that is achieved by placing a ``user.cfg`` file containing
the bare token ``developer`` in:

    ~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/
    Games/Age of Empires 3 DE/76561198170207043/Startup/user.cfg

manage_game.py open() ensures this file exists before launching the game.
Without it, aiEcho() calls are silently dropped and match.log will contain
zero probe lines.

Usage::

    from tools.aoe3_automation.log_capture import snapshot_offset, read_since, AGE3_LOG_PATH

    offset = snapshot_offset()          # call BEFORE starting match
    # ... run match ...
    content = read_since(offset)        # call AFTER resigning
    Path("pack_1/match.log").write_text(content, encoding="utf-8", errors="replace")
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Absolute path to the game's live log file (Proton prefix).
AGE3_LOG_PATH: Path = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)

# Absolute path to the user's developer-mode cfg file.
# Its presence (with the bare token "developer") enables aiEcho() output.
USER_CFG_PATH: Path = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE"
    / "76561198170207043/Startup/user.cfg"
)

# The three tokens required for aiEcho() probe capture:
#   developer  -- enables developer mode (console, dev keybinds, dev allowances)
#   +ixsLog    -- enables XS info-level logging (engine routes XS output to log)
#   +cxsLog    -- enables XS console XS log (aiEcho lines)
#
# The bare "developer" token alone is INSUFFICIENT.  Even with developer mode
# active, aiEcho() output is gated by the XS-log flags.  game.cfg line 84
# documents the convention: "to turn off +XYZ add -XYZ to your user.cfg" --
# meaning the engine reads user.cfg for +/- overrides on the same flags it
# parses from game.cfg/production.cfg.
_REQUIRED_TOKENS: tuple[str, ...] = ("developer", "+ixsLog", "+cxsLog", "generateAIEchoesOutput")

_DEV_CFG_CONTENT = """\
// user.cfg -- personal developer overrides for A New World AI probe capture
//
// These four tokens together enable aiEcho() probe output to Age3Log.txt
// and per-AI demuxed output to Age3DEAIOutputPlayer<N>.txt:
//   developer              -- engine developer mode
//   +ixsLog                -- XS info-level logging (overrides "//+ixsLog" in game.cfg:85)
//   +cxsLog                -- XS console-XS logging (overrides "//+cxsLog" in game.cfg:87)
//   generateAIEchoesOutput -- demux aiEcho() per AI player to Age3DEAIOutputPlayer<N>.txt
//
// Without developer+ixsLog+cxsLog, aiEcho() calls are silently dropped.
// generateAIEchoesOutput is a bare token (NOT key=value); it was added in
// Update 61213 and fixed (empty-file bug) in a subsequent 2022 patch.
//
// Remove this file to revert to production mode.

developer
+ixsLog
+cxsLog
generateAIEchoesOutput
"""


def _has_all_tokens(content: str) -> bool:
    """Check that every required dev-mode token is present uncommented."""
    # Strip line comments before checking.
    active_lines: list[str] = []
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("//"):
            continue
        active_lines.append(stripped)
    active = "\n".join(active_lines)
    return all(tok in active for tok in _REQUIRED_TOKENS)


def ensure_dev_mode() -> bool:
    """Write the developer-mode user.cfg if it is missing or incomplete.

    Returns True if the file was already correct, False if it was created
    or repaired (missing tokens appended).
    """
    if USER_CFG_PATH.exists():
        content = USER_CFG_PATH.read_text(encoding="utf-8", errors="replace")
        if _has_all_tokens(content):
            return True
        # File exists but missing one or more tokens -- append the missing ones.
        existing_active = "\n".join(
            ln for ln in content.splitlines()
            if ln.strip() and not ln.strip().startswith("//")
        )
        missing = [tok for tok in _REQUIRED_TOKENS if tok not in existing_active]
        appended = "\n// appended by ensure_dev_mode():\n" + "\n".join(missing) + "\n"
        USER_CFG_PATH.write_text(content.rstrip() + "\n" + appended,
                                 encoding="utf-8", errors="replace")
        return False

    USER_CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_CFG_PATH.write_text(_DEV_CFG_CONTENT, encoding="utf-8", errors="replace")
    return False


def remove_dev_mode() -> bool:
    """Remove the developer-mode user.cfg (production launch).

    Returns True if the file was removed, False if it did not exist.
    """
    if USER_CFG_PATH.exists():
        USER_CFG_PATH.unlink()
        return True
    return False


def snapshot_offset() -> int:
    """Return the current byte size of Age3Log.txt.

    Call this BEFORE starting a match.  The returned value is the ``offset``
    argument to pass to :func:`read_since` after the match ends.

    Returns 0 if the file does not exist yet (first launch).
    """
    if not AGE3_LOG_PATH.exists():
        return 0
    return AGE3_LOG_PATH.stat().st_size


def read_since(offset: int) -> str:
    """Return the Age3Log.txt content from ``offset`` to end-of-file.

    This is the per-match slice: all lines appended by the game engine
    (including aiEcho probe lines) during the match that just ended.

    Args:
        offset: Byte offset returned by :func:`snapshot_offset` before the match.

    Returns:
        UTF-8 decoded string (invalid bytes replaced).  Empty string if the
        log has not grown since ``offset`` or the file does not exist.
    """
    if not AGE3_LOG_PATH.exists():
        return ""
    current_size = AGE3_LOG_PATH.stat().st_size
    if current_size <= offset:
        return ""
    with AGE3_LOG_PATH.open("rb") as fh:
        fh.seek(offset)
        raw = fh.read()
    return raw.decode("utf-8", errors="replace")


def probe_count_in_slice(content: str) -> int:
    """Quick count of [ANWP v=2 ...] lines in a log slice."""
    return content.count("[ANWP v=2 ")


# ---------------------------------------------------------------------------
# Live log mirroring
# ---------------------------------------------------------------------------
#
# AoE3 DE buffers Age3Log.txt writes (especially XS aiEcho output) in process
# memory and only flushes on certain events (mode transitions, clean exit).
# A D3D11 crash mid-match dumps the unflushed buffer — we lose all probes
# emitted since the last flush.
#
# We can't force the engine to flush, but we CAN persistently mirror whatever
# IS on disk to a per-match file in real time.  That gives us:
#   1. Crash-resilience: bytes that reached the disk never get lost.
#   2. A single per-match file we can poll for early-exit-on-coverage.
#   3. No data race with the game (we only ever read).
#
# The mirror runs as a daemon thread that polls Age3Log.txt size every
# `poll_interval` seconds and appends new bytes to the destination file.

@dataclass
class LogMirror:
    """Background mirror of Age3Log.txt to a per-match destination file.

    Use as::

        mirror = start_log_tail(Path("pack_dir/match.log"))
        # ... run match ...
        text = stop_log_tail(mirror)   # final flush + return content

    The mirror starts from the current end of Age3Log.txt and only forwards
    bytes appended after start.  Reads happen via normal file I/O and are
    safe even while the engine is writing (POSIX append-write semantics).
    """
    dest: Path
    start_offset: int
    poll_interval: float = 0.5
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: Optional[threading.Thread] = None
    _last_offset: int = 0

    def _run(self) -> None:
        self._last_offset = self.start_offset
        with self.dest.open("ab") as out:
            while not self._stop.is_set():
                try:
                    if AGE3_LOG_PATH.exists():
                        size = AGE3_LOG_PATH.stat().st_size
                        if size < self._last_offset:
                            # Log was truncated (game relaunched).  Reset.
                            self._last_offset = 0
                        if size > self._last_offset:
                            with AGE3_LOG_PATH.open("rb") as src:
                                src.seek(self._last_offset)
                                chunk = src.read(size - self._last_offset)
                            if chunk:
                                out.write(chunk)
                                out.flush()
                                self._last_offset = size
                except OSError:
                    pass
                self._stop.wait(self.poll_interval)
            # Final drain: catch any bytes appended between last poll and stop.
            try:
                if AGE3_LOG_PATH.exists():
                    size = AGE3_LOG_PATH.stat().st_size
                    if size > self._last_offset:
                        with AGE3_LOG_PATH.open("rb") as src:
                            src.seek(self._last_offset)
                            chunk = src.read(size - self._last_offset)
                        if chunk:
                            out.write(chunk)
                            self._last_offset = size
            except OSError:
                pass

    def start(self) -> "LogMirror":
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        # Truncate dest at start so each match has a clean file.
        self.dest.write_bytes(b"")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self, *, final_flush_wait: float = 1.5) -> str:
        """Stop the mirror, do one final read, return the full mirrored content."""
        # Give the engine a moment to flush its userspace buffers (resign
        # triggers a flush, but the write may not have hit disk yet).
        time.sleep(final_flush_wait)
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        if self.dest.exists():
            return self.dest.read_text(encoding="utf-8", errors="replace")
        return ""

    def current_content(self) -> str:
        """Read whatever has been mirrored so far (non-blocking, safe to poll)."""
        if not self.dest.exists():
            return ""
        try:
            return self.dest.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def current_probe_count(self) -> int:
        """Count of [ANWP v=2 ...] lines mirrored so far."""
        return probe_count_in_slice(self.current_content())


def start_log_tail(dest: Path, *, poll_interval: float = 0.5) -> LogMirror:
    """Begin mirroring Age3Log.txt -> dest in a background thread.

    Call BEFORE starting the match.  Mirroring begins from the current end
    of Age3Log.txt; only bytes appended afterward reach `dest`.

    Returns a LogMirror handle.  Pass it to :func:`stop_log_tail` after the
    match (or any time, e.g. for early-exit polling via
    ``handle.current_probe_count()``).
    """
    mirror = LogMirror(dest=Path(dest),
                       start_offset=snapshot_offset(),
                       poll_interval=poll_interval)
    return mirror.start()


def stop_log_tail(mirror: LogMirror, *, final_flush_wait: float = 1.5) -> str:
    """Stop the mirror and return the full per-match log content as a string.

    `final_flush_wait` is a small grace period (default 1.5 s) before stopping
    so the engine's last flush after resign() reaches disk.
    """
    return mirror.stop(final_flush_wait=final_flush_wait)
