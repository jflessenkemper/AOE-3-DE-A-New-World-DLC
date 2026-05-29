"""Mock GameState — what kb*/ai* builtins read from.

Real XS reads ~280 game APIs. About 40 of those carry the doctrine signal
(age, resources, unit counts, map class, threat level). Everything else is
either action (`aiTask*`) which we log as a side effect, or rare query
which we return a sensible default for.

A Scenario configures a GameState that captures the situation we want to
test: "Age II on coastal map, balanced resources, no threat." Run a
leader's rules against it and assert the doctrine variables they set.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GameState:
    # Time
    sim_time_s: float = 0.0          # simulated game time (seconds)

    # Player
    player_id: int = 1
    civ_name: str = "French"
    age: int = 1                      # 1=Discovery 2=Colonial 3=Fortress 4=Industrial 5=Imperial
    difficulty: int = 2               # 0..4, AoE3 difficulty index

    # Resources (current stockpile)
    food: float = 200.0
    wood: float = 200.0
    gold: float = 100.0
    xp: float = 0.0

    # Population
    pop: int = 5
    pop_cap: int = 10
    villager_count: int = 5
    army_pop: int = 0

    # Unit counts by category
    counts: dict = field(default_factory=lambda: {
        "infantry": 0, "cavalry": 0, "artillery": 0,
        "naval": 0, "settler": 5, "town_center": 1,
        "house": 0, "barracks": 0, "stable": 0, "artillery_depot": 0,
        "wall_segment": 0, "outpost": 0, "fort": 0,
    })

    # Revolution flag — set True when simulating a revolution civ so that
    # civIsRevolution() returns True and the aggregator dispatch fires.
    is_revolution: bool = False

    # Map / posture
    map_class: str = "land"           # "land", "coastal", "island", "naval"
    has_water: bool = False
    threat_level: float = 0.0         # 0..1
    enemy_distance: float = 200.0     # tiles to nearest enemy

    # Action log (side effects of aiTask* / aiCommand* calls)
    actions: list = field(default_factory=list)

    # Echo / chat log (llVerboseEcho, aiEcho, aiChat)
    echo: list = field(default_factory=list)

    def log_action(self, name: str, args: tuple) -> None:
        self.actions.append((self.sim_time_s, name, args))

    def log_echo(self, msg: str) -> None:
        self.echo.append((self.sim_time_s, msg))


# ---- Pre-baked scenarios -----------------------------------------------

def scenario_open_age2() -> GameState:
    """Open land map, mid-Colonial, balanced resources, no threat."""
    gs = GameState()
    gs.age = 2
    gs.sim_time_s = 600.0
    gs.food = 800; gs.wood = 600; gs.gold = 400; gs.xp = 200
    gs.pop = 25; gs.pop_cap = 40; gs.villager_count = 22
    gs.counts.update({"settler": 22, "barracks": 1, "house": 4})
    gs.map_class = "land"
    return gs

def scenario_coastal_age2() -> GameState:
    gs = scenario_open_age2()
    gs.map_class = "coastal"
    gs.has_water = True
    return gs

def scenario_under_threat_age2() -> GameState:
    gs = scenario_open_age2()
    gs.threat_level = 0.7
    gs.enemy_distance = 60.0
    return gs

def scenario_industrial() -> GameState:
    gs = scenario_open_age2()
    gs.age = 4
    gs.sim_time_s = 1800.0
    gs.food = 2000; gs.wood = 1200; gs.gold = 1500
    gs.pop = 80; gs.pop_cap = 120; gs.villager_count = 50
    gs.counts.update({"settler": 50, "barracks": 2, "stable": 1, "artillery_depot": 1})
    return gs


SCENARIOS = {
    "open_age2": scenario_open_age2,
    "coastal_age2": scenario_coastal_age2,
    "under_threat_age2": scenario_under_threat_age2,
    "industrial": scenario_industrial,
}
