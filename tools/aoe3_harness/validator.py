"""Wrapper around validate_doctrine_compliance.py for harness integration.

Thin subprocess wrapper so the harness CLI can call validation without
importing the (large) validator module directly.

Key paths:
  VALIDATOR_SCRIPT = tools/validation/validate_doctrine_compliance.py
  DEFAULT_ARTIFACT_ROOT = artifacts/validation/ai_playstyle/
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from tools.aoe3_harness.paths import (
    ARTIFACT_ROOT,
    RELEASE_SITE_SCRIPT,
    VALIDATOR_SCRIPT,
)


def validate_pass(
    pass_number: Optional[int] = None,
    archive_dir: Optional[Path] = None,
    ai_log_paths: Optional[list[Path]] = None,
    allow_empty: bool = True,
    allow_fail: bool = False,
    json_out: Optional[Path] = None,
    html_out: Optional[Path] = None,
) -> int:
    """Run validate_doctrine_compliance.py on a pass archive or auto-discovery.

    Builds a subprocess command against the validator script and runs it.
    If neither ``pass_number`` nor ``archive_dir`` is given, the validator
    uses its own auto-discovery against ``artifacts/validation/ai_playstyle/``.

    Args:
        pass_number: If provided, discovers logs under hubtest_passN_*/match.log
            under ``ARTIFACT_ROOT``.
        archive_dir: Explicit archive dir (overrides pass_number discovery).
            If provided, passes ``<dir>/match.log`` and any
            ``<dir>/Age3DEAIOutputPlayer*.txt`` as ``--logs``.
        ai_log_paths: Per-AI files to include via ``--ai-logs``.
        allow_empty: Pass ``--allow-empty`` (default True for harness use).
        allow_fail: Pass ``--allow-fail``.
        json_out: Path for ``--json`` output.
        html_out: Path for ``--html`` output (None = no HTML report).

    Returns:
        subprocess exit code (0=pass, 1=fail, 2=error).
    """
    cmd: list[str] = [sys.executable, str(VALIDATOR_SCRIPT)]

    # Determine log sources
    explicit_logs: list[Path] = []

    if archive_dir is not None:
        match_log = archive_dir / "match.log"
        if match_log.exists():
            explicit_logs.append(match_log)
        # Also include any per-AI files in the archive dir
        explicit_logs.extend(sorted(archive_dir.glob("Age3DEAIOutputPlayer*.txt")))
    elif pass_number is not None:
        # Find all hubtest_passN_* dirs for this pass number
        if ARTIFACT_ROOT.exists():
            for d in sorted(ARTIFACT_ROOT.iterdir()):
                if d.is_dir() and d.name.startswith(f"hubtest_pass{pass_number}_"):
                    ml = d / "match.log"
                    if ml.exists():
                        explicit_logs.append(ml)
                    explicit_logs.extend(sorted(d.glob("Age3DEAIOutputPlayer*.txt")))

    if explicit_logs:
        cmd += ["--logs"] + [str(p) for p in explicit_logs]

    if ai_log_paths:
        cmd += ["--ai-logs"] + [str(p) for p in ai_log_paths]

    if allow_empty:
        cmd.append("--allow-empty")
    if allow_fail:
        cmd.append("--allow-fail")
    if json_out:
        cmd += ["--json", str(json_out)]
    if html_out:
        cmd += ["--html", str(html_out)]

    result = subprocess.run(cmd, cwd=str(VALIDATOR_SCRIPT.parents[2]))
    return result.returncode


def build_release_site() -> int:
    """Invoke build_release_readiness_site.py and return exit code.

    Returns:
        subprocess exit code (0=success).
    """
    if not RELEASE_SITE_SCRIPT.exists():
        print(
            f"[harness/validator] WARNING: {RELEASE_SITE_SCRIPT} not found; skipping.",
            file=sys.stderr,
        )
        return 2
    result = subprocess.run(
        [sys.executable, str(RELEASE_SITE_SCRIPT)],
        cwd=str(RELEASE_SITE_SCRIPT.parents[2]),
    )
    return result.returncode
