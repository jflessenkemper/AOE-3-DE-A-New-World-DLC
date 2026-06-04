"""telemetry.py — ANW probe-event log parser and HTML report generator.

Parses ``[ANWP v=2]`` lines from AoE3 log files (Age3Log.txt,
Age3DEAIOutputPlayer*.txt, archived hubtest logs) into per-civ event
trajectories and renders a self-contained SVG-based HTML report.

Protocol format (one line per probe event)::

    [ANWP v=2] tick=<ms> player=<N> <probe_name> [key=value ...]

Example::

    [ANWP v=2] tick=12345 player=2 wall.closure pct=0.6 radius=80.0

Design goals:
    - Zero external dependencies: SVG charts are inlined, no CDN.
    - Pure Python: works with stdlib only.
    - Clean API: parse first, render second.

Usage::

    from pathlib import Path
    from tools.aoe3_harness.telemetry import parse_log_to_trajectories, emit_html_report

    trajectories = parse_log_to_trajectories(Path("logs/Age3Log.txt"))
    emit_html_report(trajectories, Path("artifacts/validation/telemetry_report.html"))

CLI (via cli.py)::

    python3 -m tools.aoe3_harness.cli telemetry parse logs/Age3Log.txt
    python3 -m tools.aoe3_harness.cli telemetry parse logs/Age3Log.txt --output report.html
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = [
    "ProbeEvent",
    "parse_log_to_trajectories",
    "emit_html_report",
]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ProbeEvent:
    """One ``[ANWP v=2]`` probe line from the game log.

    Attributes:
        tick_ms:    Game tick in milliseconds (integer; 0 if not parsed).
        probe_name: Dot-separated probe identifier, e.g. ``wall.closure``.
        params:     Key/value pairs extracted from the line (all string values).
                    E.g. ``{"pct": "0.6", "radius": "80.0"}``.
        player:     Player slot index (1-based), or 0 if not present.
        raw:        The original log line (stripped), for debugging.
    """

    tick_ms: int
    probe_name: str
    params: dict[str, str] = field(default_factory=dict)
    player: int = 0
    raw: str = ""

    def numeric_value(self, key: str | None = None) -> float | None:
        """Return the first (or named) numeric param, or None.

        If *key* is given, look that key up.  Otherwise iterate params in
        insertion order and return the first one whose value parses as float.
        """
        keys = [key] if key else list(self.params.keys())
        for k in keys:
            v = self.params.get(k)
            if v is not None:
                try:
                    return float(v)
                except (ValueError, TypeError):
                    continue
        return None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Matches the canonical ``[ANWP v=2]`` prefix followed by mandatory tick and
# optional player field, then the probe name, then zero-or-more key=value
# pairs.  We allow spaces in unexpected places and tolerate extra tokens.
_LLP_RE = re.compile(
    r"\[ANWP v=2\]\s+"
    r"tick=(\d+)\s+"
    r"(?:player=(\d+)\s+)?"
    r"([\w.:-]+)"           # probe name
    r"((?:\s+\w+=\S+)*)"   # optional key=value pairs (space-separated)
)
_KV_RE = re.compile(r"(\w+)=(\S+)")

# CLAUDE-NOTE: The player-first variant ``player=N tick=M`` is also accepted
# via a second regex for resilience.
_LLP_RE_ALT = re.compile(
    r"\[ANWP v=2\]\s+"
    r"player=(\d+)\s+"
    r"tick=(\d+)\s+"
    r"([\w.:-]+)"
    r"((?:\s+\w+=\S+)*)"
)

# Player-slot → civ mapping is not available in the log lines; callers who
# want to map player index → civ token should supply an external mapping.
# By default we key trajectories by f"player_{N}".
_DEFAULT_CIV_MAP: dict[int, str] = {}


def parse_log_to_trajectories(
    log_path: Path,
    civ_map: dict[int, str] | None = None,
) -> dict[str, list[ProbeEvent]]:
    """Parse ``[ANWP v=2]`` lines from *log_path* into per-civ trajectories.

    Args:
        log_path: Path to an AoE3 log file (Age3Log.txt or similar).
        civ_map:  Optional mapping of player-slot (int) to civ token string.
                  If supplied, trajectory keys are civ tokens.  Otherwise the
                  key is ``"player_<N>"``.  Player 0 (no player field) maps to
                  ``"unknown"``.

    Returns:
        Dict mapping civ-key → sorted list of ProbeEvent (by tick_ms).

    Raises:
        OSError: If *log_path* cannot be read.
    """
    mapping: dict[int, str] = civ_map if civ_map is not None else _DEFAULT_CIV_MAP
    trajectories: dict[str, list[ProbeEvent]] = {}

    text = log_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        event = _parse_line(line)
        if event is None:
            continue
        civ_key = mapping.get(event.player, f"player_{event.player}" if event.player else "unknown")
        trajectories.setdefault(civ_key, []).append(event)

    # Sort each trajectory by tick_ms for consistent rendering.
    for key in trajectories:
        trajectories[key].sort(key=lambda e: e.tick_ms)

    return trajectories


def _parse_line(line: str) -> Optional[ProbeEvent]:
    """Parse one log line.  Returns None if it is not a valid LLP line."""
    stripped = line.strip()
    if "[ANWP v=2]" not in stripped:
        return None

    # Try canonical order first (tick before player).
    m = _LLP_RE.search(stripped)
    if m:
        tick_ms = int(m.group(1))
        player = int(m.group(2)) if m.group(2) else 0
        probe_name = m.group(3)
        kv_blob = m.group(4)
    else:
        # Try alt order (player before tick).
        m2 = _LLP_RE_ALT.search(stripped)
        if not m2:
            return None
        player = int(m2.group(1))
        tick_ms = int(m2.group(2))
        probe_name = m2.group(3)
        kv_blob = m2.group(4)

    params: dict[str, str] = {k: v for k, v in _KV_RE.findall(kv_blob)}
    return ProbeEvent(
        tick_ms=tick_ms,
        probe_name=probe_name,
        params=params,
        player=player,
        raw=stripped,
    )


# ---------------------------------------------------------------------------
# HTML renderer (SVG inline charts, no CDN)
# ---------------------------------------------------------------------------

_HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ANW Telemetry Report</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #e0e0f0;
         margin: 0; padding: 16px; }}
  h1   {{ color: #a8c8ff; font-size: 22px; margin-bottom: 4px; }}
  .meta {{ font-size: 12px; color: #888; margin-bottom: 20px; }}
  .civ-section {{ border: 1px solid #334; border-radius: 8px; margin: 14px 0;
                  padding: 12px; background: #16213e; }}
  .civ-section h2 {{ color: #7db8ff; font-size: 17px; margin: 0 0 10px 0; }}
  .probe-grid {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .probe-chart {{ background: #0f3460; border: 1px solid #556; border-radius: 6px;
                  padding: 8px; }}
  .probe-chart h3 {{ margin: 0 0 6px 0; font-size: 12px; color: #9ac; }}
  svg {{ display: block; }}
  .no-numeric {{ font-size: 11px; color: #779; font-style: italic; padding: 20px 10px; }}
  .summary {{ border: 2px solid #3a6; border-radius: 6px; padding: 10px 14px;
              background: #0d2a18; margin-bottom: 16px; font-size: 14px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 6px; }}
  th {{ background: #223; color: #aac; text-align: left; padding: 4px 8px; }}
  td {{ padding: 3px 8px; border-bottom: 1px solid #334; }}
</style>
</head>
<body>
"""

_HTML_TAIL = "</body>\n</html>\n"

_CHART_W = 220
_CHART_H = 100
_PAD_L = 30
_PAD_R = 8
_PAD_T = 8
_PAD_B = 18
_PLOT_W = _CHART_W - _PAD_L - _PAD_R
_PLOT_H = _CHART_H - _PAD_T - _PAD_B


def _svg_chart(events: list[ProbeEvent], probe: str, value_key: str | None = None) -> str:
    """Render a small SVG line chart for the given probe events.

    Args:
        events:    ProbeEvent list for ONE probe (already filtered).
        probe:     Probe name (for aria-label).
        value_key: The param key to plot (auto-detected if None).

    Returns:
        HTML string containing the SVG element, or a ``<p class="no-numeric">``
        placeholder if no numeric values exist.
    """
    # Collect (tick_ms, float_value) pairs
    points: list[tuple[int, float]] = []
    for ev in events:
        val = ev.numeric_value(value_key)
        if val is not None:
            points.append((ev.tick_ms, val))

    if not points:
        return (
            f'<p class="no-numeric">no numeric param found<br>'
            f'({len(events)} event(s))</p>'
        )

    min_t = min(p[0] for p in points)
    max_t = max(p[0] for p in points)
    min_v = min(p[1] for p in points)
    max_v = max(p[1] for p in points)

    # Avoid division by zero
    t_range = max(max_t - min_t, 1)
    v_range = max(max_v - min_v, 1e-9)

    def _x(t: int) -> float:
        return _PAD_L + (t - min_t) / t_range * _PLOT_W

    def _y(v: float) -> float:
        return _PAD_T + (1.0 - (v - min_v) / v_range) * _PLOT_H

    polyline_pts = " ".join(f"{_x(t):.1f},{_y(v):.1f}" for t, v in points)

    # Y-axis tick labels
    y_labels = ""
    for frac in (0.0, 0.5, 1.0):
        val_label = min_v + frac * v_range
        y_pos = _PAD_T + (1.0 - frac) * _PLOT_H
        y_labels += (
            f'<text x="{_PAD_L - 3}" y="{y_pos + 3:.1f}" '
            f'text-anchor="end" font-size="9" fill="#779">'
            f"{val_label:.2g}</text>"
        )

    # X-axis tick labels (start and end)
    x_labels = (
        f'<text x="{_PAD_L}" y="{_CHART_H - 4}" font-size="9" fill="#779">{min_t}</text>'
        f'<text x="{_CHART_W - _PAD_R}" y="{_CHART_H - 4}" '
        f'text-anchor="end" font-size="9" fill="#779">{max_t}</text>'
    )

    # Axes
    axes = (
        f'<line x1="{_PAD_L}" y1="{_PAD_T}" x2="{_PAD_L}" y2="{_PAD_T + _PLOT_H}" '
        f'stroke="#446" stroke-width="1"/>'
        f'<line x1="{_PAD_L}" y1="{_PAD_T + _PLOT_H}" '
        f'x2="{_PAD_L + _PLOT_W}" y2="{_PAD_T + _PLOT_H}" '
        f'stroke="#446" stroke-width="1"/>'
    )

    # Dots for sparse data (fewer than 20 points)
    dots = ""
    if len(points) < 20:
        for t, v in points:
            dots += (
                f'<circle cx="{_x(t):.1f}" cy="{_y(v):.1f}" r="2.5" '
                f'fill="#4a9eff" opacity="0.85"/>'
            )

    return (
        f'<svg width="{_CHART_W}" height="{_CHART_H}" '
        f'aria-label="probe:{html.escape(probe)}">'
        f'<rect width="{_CHART_W}" height="{_CHART_H}" fill="#0a1628" rx="4"/>'
        f"{axes}{y_labels}{x_labels}"
        f'<polyline points="{html.escape(polyline_pts)}" '
        f'fill="none" stroke="#4a9eff" stroke-width="1.5" opacity="0.9"/>'
        f"{dots}"
        f"</svg>"
    )


def _render_civ_section(civ_key: str, events: list[ProbeEvent]) -> str:
    """Render the HTML block for one civ's probe events."""
    # Group events by probe name
    by_probe: dict[str, list[ProbeEvent]] = {}
    for ev in events:
        by_probe.setdefault(ev.probe_name, []).append(ev)

    probe_charts = []
    for probe_name in sorted(by_probe.keys()):
        probe_events = by_probe[probe_name]
        chart_svg = _svg_chart(probe_events, probe_name)
        probe_charts.append(
            f'<div class="probe-chart">'
            f'<h3>{html.escape(probe_name)} '
            f'<span style="font-weight:normal;color:#668;">({len(probe_events)} events)</span>'
            f"</h3>"
            f"{chart_svg}"
            f"</div>"
        )

    grid_html = (
        '<div class="probe-grid">' + "".join(probe_charts) + "</div>"
    ) if probe_charts else '<p style="color:#779;font-size:12px;">no probes</p>'

    return (
        f'<section class="civ-section">'
        f'<h2>{html.escape(civ_key)}</h2>'
        f"<details><summary style=\"font-size:12px;color:#779;cursor:pointer;\">"
        f"Event table ({len(events)} total)</summary>"
        f"{_event_table(events[:50])}"
        f"{'<p style=\"font-size:11px;color:#667;\">(truncated to 50 rows)</p>' if len(events) > 50 else ''}"
        f"</details>"
        f"{grid_html}"
        f"</section>"
    )


def _event_table(events: list[ProbeEvent]) -> str:
    """Render a compact HTML table of probe events."""
    rows = []
    for ev in events:
        param_str = " ".join(f"{k}={v}" for k, v in ev.params.items())
        rows.append(
            f"<tr>"
            f"<td>{ev.tick_ms}</td>"
            f"<td>{html.escape(ev.probe_name)}</td>"
            f"<td>{ev.player}</td>"
            f"<td style='font-family:monospace;font-size:10px;'>{html.escape(param_str)}</td>"
            f"</tr>"
        )
    return (
        "<table>"
        "<tr><th>tick_ms</th><th>probe</th><th>player</th><th>params</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _summary_block(trajectories: dict[str, list[ProbeEvent]]) -> str:
    """Render a top-level summary block."""
    total_events = sum(len(evs) for evs in trajectories.values())
    all_probes: set[str] = set()
    for evs in trajectories.values():
        for ev in evs:
            all_probes.add(ev.probe_name)
    probe_list = html.escape(", ".join(sorted(all_probes)) or "(none)")

    return (
        '<div class="summary">'
        f"<b>{len(trajectories)}</b> player(s) / civ(s) found &nbsp;|&nbsp; "
        f"<b>{total_events}</b> total probe events &nbsp;|&nbsp; "
        f"<b>{len(all_probes)}</b> distinct probe name(s)<br>"
        f'<span style="font-size:12px;color:#9ac;">Probes: {probe_list}</span>'
        "</div>"
    )


def emit_html_report(
    trajectories: dict[str, list[ProbeEvent]],
    output_path: Path,
    source_path: str | Path | None = None,
) -> None:
    """Render per-civ probe time-series charts to a self-contained HTML file.

    Args:
        trajectories: Output of :func:`parse_log_to_trajectories`.
        output_path:  Destination HTML file path (created or overwritten).
        source_path:  Optional source log path for display in the header.

    Returns:
        None.  Writes *output_path* as a side-effect.
    """
    src_label = str(source_path) if source_path else "(inline/synthetic)"
    body_parts: list[str] = [
        _HTML_HEAD.format(),
        f"<h1>ANW Telemetry Report</h1>\n"
        f'<div class="meta">Source: {html.escape(src_label)}</div>\n',
        _summary_block(trajectories),
    ]

    if not trajectories:
        body_parts.append(
            '<p style="color:#779;">No [ANWP v=2] probe events found in the log.</p>'
        )
    else:
        for civ_key in sorted(trajectories.keys()):
            body_parts.append(_render_civ_section(civ_key, trajectories[civ_key]))

    body_parts.append(_HTML_TAIL)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(body_parts), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entry point (called from cli.py ``telemetry`` subcommand)
# ---------------------------------------------------------------------------

def main_cli(argv: list[str] | None = None) -> int:
    """CLI handler for ``python3 -m tools.aoe3_harness.cli telemetry ...``.

    Subcommands:
        parse <log_path> [--output <report.html>]
            Parse the log and emit an HTML report.

    Returns:
        0 on success, non-zero on error.
    """
    import argparse
    import sys

    ap = argparse.ArgumentParser(
        prog="cli.py telemetry",
        description="Parse ANW probe logs and render telemetry HTML report.",
    )
    sub = ap.add_subparsers(dest="sub", required=True)

    p_parse = sub.add_parser("parse", help="parse log and emit HTML report")
    p_parse.add_argument("log_path", type=Path, help="path to Age3Log.txt or similar")
    p_parse.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/validation/telemetry_report.html"),
        help="output HTML path (default: artifacts/validation/telemetry_report.html)",
    )

    args = ap.parse_args(argv)

    if args.sub == "parse":
        log_path: Path = args.log_path
        if not log_path.exists():
            print(f"ERROR: log file not found: {log_path}", file=sys.stderr)
            return 1
        print(f"[telemetry] Parsing: {log_path}")
        trajectories = parse_log_to_trajectories(log_path)
        n_events = sum(len(evs) for evs in trajectories.values())
        print(f"[telemetry] Found {n_events} probe event(s) across {len(trajectories)} player(s)")
        output_path: Path = args.output
        emit_html_report(trajectories, output_path, source_path=log_path)
        size = output_path.stat().st_size
        print(f"[telemetry] Report written: {output_path} ({size:,} B)")
        return 0

    print(f"[telemetry] Unknown subcommand: {args.sub}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main_cli())
