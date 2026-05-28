"""Per-pass scenario setup helpers.

Manages the scenario file selection, pass-civ printing, and match lifecycle.

Scenario file location:
  /var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/
  pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/ANEWWORLD.age3Yscn

The harness does NOT automate the lobby (no xdotool; Wine ignores X11 synthetic events).
The user manually sets up the 7-AI lobby after the game launches. The supervisor
prints the civ list and waits.
"""

from __future__ import annotations

from pathlib import Path

from tools.aoe3_harness.paths import SCENARIO_DIR


def print_pass_setup_instructions(pass_number: int, civs: list[str]) -> None:
    """Print the civ list and lobby setup instructions for the user.

    Called after game launch, before the sleep timer starts.  Outputs to
    stdout so the human operator knows what to configure in the game lobby.

    Args:
        pass_number: The current pass number (1–6).
        civs: Ordered list of civ tokens for this pass.
    """
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  PASS {pass_number} LOBBY SETUP INSTRUCTIONS")
    print(separator)
    print(
        "  The game is launching. Navigate to:"
        "\n  Single Player -> Skirmish -> Load Scenario -> ANEWWORLD.age3Yscn"
    )
    print(f"\n  Assign these civs to AI slots 1-{len(civs)}:\n")
    for i, civ in enumerate(civs, 1):
        print(f"    Slot {i:2d}:  {civ}")
    if len(civs) < 7:
        for i in range(len(civs) + 1, 8):
            print(f"    Slot {i:2d}:  (any AI or leave empty)")
    print(
        f"\n  Start the match. The harness timer is already running."
        f"\n  DO NOT resign early — let the match run for the full 21 minutes."
        f"\n{separator}\n"
    )


def verify_scenario_exists(filename: str = "ANEWWORLD.age3Yscn") -> bool:
    """Verify the target scenario file is present in the Scenario directory.

    Args:
        filename: The scenario filename to check (default: ``ANEWWORLD.age3Yscn``).

    Returns:
        True if the scenario file exists.

    Raises:
        FileNotFoundError: if the scenario file is missing (supervisor should abort).
    """
    scenario_path = SCENARIO_DIR / filename
    if not scenario_path.exists():
        raise FileNotFoundError(
            f"Scenario file not found: {scenario_path}\n"
            "Verify the game is installed and the scenario has been created in the "
            "Scenario Editor.  Expected path:\n"
            f"  {scenario_path}"
        )
    return True
