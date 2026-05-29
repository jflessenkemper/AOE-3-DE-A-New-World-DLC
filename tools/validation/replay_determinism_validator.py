#!/usr/bin/env python3
"""Replay-based determinism validation for ANW.

Parses .age3Yrec replay files to validate bit-perfect determinism.
Compares game state snapshots extracted from replays.

AoE3 replays record: player commands + RNG seed → full game state deterministic
This validator checks if the same initial RNG seed produces identical outcomes.

Format note (verified 2026-05-09):
  .age3Yrec files are l33t-wrapped (ASCII 'l33t'/'L33t' + uint32 LE size + zlib).
  The same wrapper is used by .age3Yscn scenarios. See
  ``tools/cardextract/l33t_codec.py`` for the canonical codec; we share it
  rather than re-implementing the unwrap here.

  The *inner* (decompressed) byte stream is still proprietary — no public
  format spec exists, so the per-frame snapshot extraction below is
  hash-only ("did identical inputs yield identical bytes?"), not
  field-decoded. That's enough for bit-perfect determinism checks; full
  field decode lands in a later phase if/when the format is reversed.
"""
import hashlib
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Optional

# l33t codec lives under tools/cardextract; add the parent so we can import
# it without restructuring the package tree. (Both modules sit under the
# same `tools/` root, just in sibling subdirs.)
_REPO_TOOLS = Path(__file__).resolve().parents[1]
if str(_REPO_TOOLS) not in sys.path:
    sys.path.insert(0, str(_REPO_TOOLS))
from cardextract import l33t_codec  # noqa: E402


class ReplayParser:
    """Parses .age3Yrec replay files.

    Wrapper layout (shared with .age3Yscn — see ``l33t_codec``):

    ::

        offset 0:  4 bytes — ASCII 'l33t' (or 'L33t') magic
        offset 4:  uint32 little-endian — decompressed size
        offset 8:  zlib-deflate stream

    The deflated payload's structure (RNG seed, snapshots, command stream)
    is undocumented; we expose what we can verify (hashes, sizes, magic
    flavour) without guessing field offsets.
    """

    def __init__(self):
        """Initialize parser."""
        pass

    def parse_replay(self, replay_path: Path) -> Dict:
        """Parse .age3Yrec replay file.

        Returns a dict with:
          - magic               : "l33t" / "L33t" / None
          - file_hash           : SHA256 of the raw on-disk bytes
          - inner_hash          : SHA256 of the decompressed payload
          - declared_size       : size from the l33t header (uint32 LE)
          - decompressed_size   : actual bytes after zlib.decompress
          - compressed_size     : payload size (file size minus 8-byte header)
          - status              : "PARSED" / "ERROR"
          - error               : present iff something failed

        Inner-format fields (rng_seed, snapshots, command_count) are not
        populated yet — the deflated payload schema is proprietary. Adding
        them is gated on reverse-engineering work tracked in
        docs/wiki/replays-scenarios.md.
        """
        if not replay_path.exists():
            return {"error": f"Replay not found: {replay_path}", "status": "ERROR"}

        try:
            raw_data = Path(replay_path).read_bytes()
        except Exception as e:
            return {"error": str(e), "replay_path": str(replay_path), "status": "ERROR"}

        file_hash = hashlib.sha256(raw_data).hexdigest()

        if not l33t_codec.is_l33t(raw_data):
            return {
                "error": f"Not an l33t blob (magic={raw_data[:4]!r})",
                "file_hash": file_hash,
                "replay_path": str(replay_path),
                "status": "ERROR",
            }

        magic = raw_data[:4].decode("ascii", errors="replace")
        try:
            decompressed = l33t_codec.decompress(raw_data)
        except (ValueError, zlib.error) as e:
            return {
                "magic": magic,
                "file_hash": file_hash,
                "compressed_size": len(raw_data) - 8,
                "error": f"l33t decompress failed: {e}",
                "replay_path": str(replay_path),
                "status": "ERROR",
            }

        # Header's declared size — the codec already verified it matches
        # the actual decompressed length, but surface it for completeness.
        declared_size = int.from_bytes(raw_data[4:8], "little")

        return {
            "magic": magic,
            "file_hash": file_hash,
            "inner_hash": hashlib.sha256(decompressed).hexdigest(),
            "declared_size": declared_size,
            "compressed_size": len(raw_data) - 8,
            "decompressed_size": len(decompressed),
            "replay_path": str(replay_path),
            "status": "PARSED",
        }

    def extract_rng_seed(self, replay_path: Path) -> Optional[int]:
        """Extract RNG seed from replay.

        The RNG seed determines all random events (unit production, AI
        decisions, etc). Same seed should produce identical gameplay
        (deterministic).

        Currently unimplemented: the inner byte stream's schema is not yet
        reverse-engineered, so we can't locate the seed field reliably.
        See docs/wiki/replays-scenarios.md for the open work.
        """
        return None


class DeterminismValidator:
    """Validates determinism by comparing replay executions."""

    def __init__(self):
        """Initialize validator."""
        self.parser = ReplayParser()

    def compare_replays(
        self,
        original_replay: Path,
        rerun_replay: Path,
    ) -> Dict:
        """Compare original replay vs. re-run with same RNG seed.

        Compares the *decompressed* payload hash, not the on-disk file
        hash — zlib's compressed output isn't guaranteed identical across
        runs (compressor state, dictionary, length-encoding choices), and
        the wrapper itself can carry timestamps/user-id that vary even
        when the simulation is byte-identical. ``inner_hash`` from
        ReplayParser is the right comparison.

        Returns: {
            "deterministic": bool,
            "original_inner_hash": SHA256,
            "rerun_inner_hash": SHA256,
            "original_file_hash": SHA256,
            "rerun_file_hash": SHA256,
            "hashes_match": bool,
            "analysis": description
        }
        """
        # Parse both replays
        original = self.parser.parse_replay(original_replay)
        rerun = self.parser.parse_replay(rerun_replay)

        if original.get("status") == "ERROR" or rerun.get("status") == "ERROR":
            return {
                "error": original.get("error") or rerun.get("error"),
                "status": "ERROR"
            }

        orig_inner = original.get("inner_hash", "")
        rerun_inner = rerun.get("inner_hash", "")
        hashes_match = bool(orig_inner) and orig_inner == rerun_inner

        result = {
            "deterministic": hashes_match,
            "original_replay": str(original_replay),
            "rerun_replay": str(rerun_replay),
            "original_inner_hash": orig_inner,
            "rerun_inner_hash": rerun_inner,
            "original_file_hash": original.get("file_hash", ""),
            "rerun_file_hash": rerun.get("file_hash", ""),
            "hashes_match": hashes_match,
        }

        if hashes_match:
            result["status"] = "PASS"
            result["analysis"] = "✓ Replay payloads are bit-perfect identical (deterministic)"
        else:
            result["status"] = "FAIL"
            result["analysis"] = (
                "✗ Replay payloads differ — non-deterministic simulation, "
                "or replays were recorded with different inputs/seed/version"
            )

        return result

    def validate_replay_integrity(self, replay_path: Path) -> Dict:
        """Check replay file integrity (l33t magic + zlib payload).

        Returns: {
            "valid": bool,
            "file_size": bytes,
            "magic": "l33t" / "L33t" / None,
            "is_l33t": bool,
            "is_compressed": bool,
            "decompressed_size": int (if decompressed ok),
            "errors": [list of issues]
        }
        """
        if not replay_path.exists():
            return {"error": f"Replay not found: {replay_path}", "valid": False}

        try:
            file_size = replay_path.stat().st_size
            errors: List[str] = []

            if file_size < 8:
                errors.append(f"File too small: {file_size} bytes (min 8)")
                return {
                    "valid": False,
                    "file_size": file_size,
                    "errors": errors,
                    "replay_path": str(replay_path),
                }

            raw = Path(replay_path).read_bytes()
            is_l33t = l33t_codec.is_l33t(raw)
            magic = raw[:4].decode("ascii", errors="replace") if is_l33t else None
            decompressed_size: Optional[int] = None
            is_compressed = False

            if not is_l33t:
                errors.append(f"Missing l33t/L33t magic (got {raw[:4]!r})")
            else:
                try:
                    decompressed = l33t_codec.decompress(raw)
                    decompressed_size = len(decompressed)
                    is_compressed = True
                except (ValueError, zlib.error) as e:
                    errors.append(f"l33t decompress failed: {e}")

            return {
                "valid": len(errors) == 0,
                "file_size": file_size,
                "magic": magic,
                "is_l33t": is_l33t,
                "is_compressed": is_compressed,
                "decompressed_size": decompressed_size,
                "errors": errors,
                "replay_path": str(replay_path),
            }

        except Exception as e:
            return {
                "error": str(e),
                "replay_path": str(replay_path),
                "valid": False
            }

    def batch_validate_replays(
        self,
        replay_dir: Path,
    ) -> List[Dict]:
        """Validate all replays in directory.

        Returns: List of validation results
        """
        results = []

        if not replay_dir.exists():
            return [{"error": f"Directory not found: {replay_dir}"}]

        # Find all .age3Yrec files
        replays = list(replay_dir.glob("*.age3Yrec")) + list(replay_dir.glob("*.yrec"))
        replays.sort()

        for replay_path in replays:
            result = self.validate_replay_integrity(replay_path)
            results.append(result)

        return results


def main():
    """Command-line interface."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Replay-based determinism validation"
    )
    parser.add_argument("replay", help="Replay file or directory")
    parser.add_argument("--compare", help="Compare with another replay for determinism")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    validator = DeterminismValidator()
    path = Path(args.replay)

    if args.compare:
        # Compare two replays
        result = validator.compare_replays(path, Path(args.compare))

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Determinism Check")
            print(f"  Original: {path.name}")
            print(f"  Re-run:   {Path(args.compare).name}")
            print(f"  Status:   {result.get('status', 'UNKNOWN')}")
            if "analysis" in result:
                print(f"  {result['analysis']}")

    elif path.is_file():
        # Validate single replay
        result = validator.validate_replay_integrity(path)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Replay: {path.name}")
            print(f"  Size: {result['file_size']} bytes")
            print(f"  Valid: {result['valid']}")
            if result['errors']:
                print("  Errors:")
                for error in result['errors']:
                    print(f"    - {error}")

    elif path.is_dir():
        # Batch validate directory
        results = validator.batch_validate_replays(path)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Validating {len(results)} replays...")
            for result in results:
                filename = Path(result.get("replay_path", "")).name
                status = "✓" if result.get("valid") else "✗"
                size = result.get("file_size", 0)
                print(f"  [{status}] {filename} ({size} bytes)")


if __name__ == "__main__":
    main()
