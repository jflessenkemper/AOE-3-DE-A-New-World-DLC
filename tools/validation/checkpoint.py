#!/usr/bin/env python3
"""Checkpoint system for resumable validation runs."""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """Progress state for a validation run."""
    run_id: str
    mode: str  # "quick-test", "sample", "full", "resume"
    civs_total: int
    civs_done: List[str] = field(default_factory=list)
    civs_failed: Dict[str, str] = field(default_factory=dict)  # civ -> reason
    phase_results: Dict[str, Dict[str, str]] = field(default_factory=dict)  # civ -> {phase: status}
    started_at: str = ""
    last_updated: str = ""
    checkpoint_path: Optional[Path] = None

    def __post_init__(self):
        """Initialize timestamps if not set."""
        if not self.started_at:
            self.started_at = datetime.utcnow().isoformat()
        if not self.last_updated:
            self.last_updated = self.started_at

    def save(self) -> None:
        """Save checkpoint to JSON file."""
        if not self.checkpoint_path:
            return

        self.last_updated = datetime.utcnow().isoformat()

        data = {
            "run_id": self.run_id,
            "mode": self.mode,
            "civs_total": self.civs_total,
            "civs_done": self.civs_done,
            "civs_failed": self.civs_failed,
            "phase_results": self.phase_results,
            "started_at": self.started_at,
            "last_updated": self.last_updated
        }

        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Checkpoint saved: {len(self.civs_done)} civs done, "
                   f"{len(self.civs_failed)} failed")

    def mark_civ_phase(self, civ_token: str, phase: int, status: str) -> None:
        """Mark a civ's phase as complete with status.

        Args:
            civ_token: Civilization identifier
            phase: Phase number (1-5)
            status: "pass", "fail", "skip", etc.
        """
        if civ_token not in self.phase_results:
            self.phase_results[civ_token] = {}

        self.phase_results[civ_token][str(phase)] = status
        logger.debug(f"{civ_token} phase {phase}: {status}")

    def mark_civ_done(self, civ_token: str) -> None:
        """Mark a civ as fully processed.

        Args:
            civ_token: Civilization identifier
        """
        if civ_token not in self.civs_done:
            self.civs_done.append(civ_token)
        if civ_token in self.civs_failed:
            del self.civs_failed[civ_token]

    def mark_civ_failed(self, civ_token: str, phase: int, reason: str) -> None:
        """Mark a civ as failed at a specific phase.

        Args:
            civ_token: Civilization identifier
            phase: Phase number where failure occurred
            reason: Failure reason
        """
        self.civs_failed[civ_token] = f"phase_{phase}: {reason}"
        self.mark_civ_phase(civ_token, phase, "fail")

    def next_pending(self, all_civs: List[str]) -> List[str]:
        """Get list of civs still needing processing.

        Args:
            all_civs: Full list of civs to process

        Returns:
            List of pending civ tokens
        """
        pending = [c for c in all_civs if c not in self.civs_done and c not in self.civs_failed]
        logger.info(f"Pending civs: {len(pending)}/{len(all_civs)}")
        return pending

    def summary(self) -> str:
        """Get human-readable summary.

        Returns:
            Summary string
        """
        total_phases = 5
        avg_progress = (len(self.civs_done) / self.civs_total * 100) if self.civs_total > 0 else 0

        return (
            f"Run {self.run_id} ({self.mode}): "
            f"{len(self.civs_done)}/{self.civs_total} civs done, "
            f"{len(self.civs_failed)} failed ({avg_progress:.1f}% complete)"
        )


def load_checkpoint(run_id: str, checkpoint_dir: Path) -> Optional[Checkpoint]:
    """Load checkpoint from file.

    Args:
        run_id: Run identifier
        checkpoint_dir: Base checkpoint directory

    Returns:
        Checkpoint object or None if not found
    """
    checkpoint_path = checkpoint_dir / run_id / "checkpoint.json"

    if not checkpoint_path.exists():
        logger.warning(f"Checkpoint not found: {checkpoint_path}")
        return None

    try:
        with open(checkpoint_path) as f:
            data = json.load(f)

        ckpt = Checkpoint(
            run_id=data["run_id"],
            mode=data["mode"],
            civs_total=data["civs_total"],
            civs_done=data.get("civs_done", []),
            civs_failed=data.get("civs_failed", {}),
            phase_results=data.get("phase_results", {}),
            started_at=data.get("started_at", ""),
            last_updated=data.get("last_updated", "")
        )
        ckpt.checkpoint_path = checkpoint_path
        logger.info(f"Loaded checkpoint: {ckpt.summary()}")
        return ckpt

    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return None


def create_checkpoint(run_id: str, mode: str, civs_total: int,
                     checkpoint_dir: Path) -> Checkpoint:
    """Create a new checkpoint.

    Args:
        run_id: Run identifier
        mode: Run mode
        civs_total: Total number of civs
        checkpoint_dir: Base checkpoint directory

    Returns:
        New Checkpoint object
    """
    checkpoint_path = checkpoint_dir / run_id / "checkpoint.json"

    ckpt = Checkpoint(
        run_id=run_id,
        mode=mode,
        civs_total=civs_total,
        checkpoint_path=checkpoint_path
    )
    ckpt.save()
    logger.info(f"Created checkpoint: {ckpt.summary()}")
    return ckpt


def main():
    """Test checkpoint functionality."""
    logging.basicConfig(level=logging.INFO)

    # Create test checkpoint
    ckpt = create_checkpoint("test_20260507", "sample", 5, Path("artifacts/checkpoints"))

    # Mark some progress
    ckpt.mark_civ_phase("british", 1, "pass")
    ckpt.mark_civ_phase("british", 2, "pass")
    ckpt.mark_civ_done("british")
    ckpt.mark_civ_failed("aztecs", 2, "screenshot_timeout")
    ckpt.save()

    print(f"\n{ckpt.summary()}")
    print(f"Phase results: {ckpt.phase_results}")
    print(f"Failed civs: {ckpt.civs_failed}")


if __name__ == "__main__":
    main()
