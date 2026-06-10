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
class AreaInfo:
    """Minimal area descriptor for kbArea* mock builtins."""
    area_id: int
    area_type: int           # 0=land, 1=water, 2=impassable, 3=cliff
    center: tuple            # (x, y, z)
    num_tiles: int
    border_area_ids: list    # list[int]


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

    # Area graph: dict[area_id -> AreaInfo] for kbArea* mock builtins
    areas: dict = field(default_factory=dict)

    # Base info: dict[base_id -> dict] for kbBase* mock builtins
    # Each entry: {"player_id": int, "location": (x,y,z), "front_vector": (x,y,z), "main": bool}
    bases: dict = field(default_factory=dict)

    # Map dimensions
    map_x_size: int = 256
    map_z_size: int = 256

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


def scenario_chokepoint_area_graph() -> "GameState":
    """Land map with a real chokepoint — area 3 is a narrow corridor (80 tiles)
    between base area 1 and enemy area 4 with impassable flanks (areas 5, 6).
    Designed so anwDetectChokepointVector returns a real vector, not the fallback.
    """
    gs = scenario_open_age2()
    gs.map_class = "land"
    gs.has_water = False
    # Area 1: main land base (player 1)
    gs.areas[1] = AreaInfo(1, 0, (100.0, 0.0, 100.0), 500, [3, 5])
    # Area 3: narrow corridor — the chokepoint (borderless narrow gap)
    gs.areas[3] = AreaInfo(3, 0, (160.0, 0.0, 100.0), 80, [1, 4, 5, 6])
    # Area 4: enemy side
    gs.areas[4] = AreaInfo(4, 0, (220.0, 0.0, 100.0), 400, [3])
    # Areas 5, 6: impassable flanks
    gs.areas[5] = AreaInfo(5, 2, (130.0, 0.0, 60.0),  10, [1, 3, 6])
    gs.areas[6] = AreaInfo(6, 2, (130.0, 0.0, 140.0), 10, [3, 4])
    # Base 1: player base at area 1 center
    gs.bases[1] = {
        "player_id": 1,
        "location": (100.0, 0.0, 100.0),
        "front_vector": (1.0, 0.0, 0.0),
        "main": True,
    }
    return gs


def scenario_coastal_area_graph() -> "GameState":
    """Coastal map with water border on the north side.
    Area 2 is water, bordered by the main land base area 1.
    Designed so anwDetectCoastVector returns a real (non-fallback) vector.
    """
    gs = scenario_coastal_age2()
    # Area 1: main land base
    gs.areas[1] = AreaInfo(1, 0, (100.0, 0.0, 100.0), 500, [2, 3])
    # Area 2: water to the north
    gs.areas[2] = AreaInfo(2, 1, (100.0, 0.0, 170.0), 200, [1])
    # Area 3: open land to the east
    gs.areas[3] = AreaInfo(3, 0, (170.0, 0.0, 100.0), 300, [1])
    # Base 1: player base at area 1 center
    gs.bases[1] = {
        "player_id": 1,
        "location": (100.0, 0.0, 100.0),
        "front_vector": (1.0, 0.0, 0.0),
        "main": True,
    }
    return gs


SCENARIOS = {
    "open_age2": scenario_open_age2,
    "coastal_age2": scenario_coastal_age2,
    "under_threat_age2": scenario_under_threat_age2,
    "industrial": scenario_industrial,
    "chokepoint_area_graph": scenario_chokepoint_area_graph,
    "coastal_area_graph": scenario_coastal_area_graph,
}
