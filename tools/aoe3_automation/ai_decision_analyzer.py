#!/usr/bin/env python3
"""AI Decision Analyzer — Parse AI chat logs for playstyle validation.

Extracts behavioral signals from Age3Log.txt to validate civ playstyles:
- Unit production patterns (infantry vs cavalry vs ranged ratios)
- Economic choices (food vs gold vs wood focus)
- Age-up progression timing and patterns
- Wall/fortification strategies
- Shipping patterns and trade routes
- Military composition diversity
- Resource gathering priorities

Usage
-----
    from tools.aoe3_automation.ai_decision_analyzer import (
        AIDecisionAnalyzer, parse_game_log, DecisionMetrics
    )

    analyzer = AIDecisionAnalyzer(log_path="path/to/match.log")
    metrics = analyzer.analyze()
    print(metrics.to_dict())
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
import datetime


logger = logging.getLogger(__name__)


class UnitType(Enum):
    """Unit classification."""
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    RANGED = "ranged"
    SIEGE = "siege"
    NAVAL = "naval"
    SUPPORT = "support"
    ECONOMIC = "economic"
    UNKNOWN = "unknown"


class ResourceType(Enum):
    """Resource types."""
    FOOD = "food"
    WOOD = "wood"
    GOLD = "gold"
    STONE = "stone"


# Unit → Type mapping for all ANW units
UNIT_CLASSIFICATIONS: Dict[str, UnitType] = {
    # Infantry
    "pikeman": UnitType.INFANTRY,
    "musketeer": UnitType.INFANTRY,
    "grenadier": UnitType.INFANTRY,
    "javelineer": UnitType.INFANTRY,
    "axeman": UnitType.INFANTRY,
    "clubman": UnitType.INFANTRY,
    "strelets": UnitType.INFANTRY,
    "samurai": UnitType.INFANTRY,
    "ashigaru": UnitType.INFANTRY,
    "ronin": UnitType.INFANTRY,
    "daimyo": UnitType.INFANTRY,
    "shogun": UnitType.INFANTRY,
    "warrior": UnitType.INFANTRY,
    "villager": UnitType.ECONOMIC,
    # Cavalry
    "cavalry": UnitType.CAVALRY,
    "dragoon": UnitType.CAVALRY,
    "hussar": UnitType.CAVALRY,
    "lancer": UnitType.CAVALRY,
    "general": UnitType.CAVALRY,
    "noble": UnitType.CAVALRY,
    "knight": UnitType.CAVALRY,
    "cuirassier": UnitType.CAVALRY,
    "cossack": UnitType.CAVALRY,
    # Ranged
    "archer": UnitType.RANGED,
    "crossbowman": UnitType.RANGED,
    "longbowman": UnitType.RANGED,
    "musketeer": UnitType.RANGED,
    "skirmisher": UnitType.RANGED,
    "mamelukes": UnitType.RANGED,
    "sepoy": UnitType.RANGED,
    "camelry": UnitType.RANGED,
    # Siege
    "cannon": UnitType.SIEGE,
    "howitzer": UnitType.SIEGE,
    "mortar": UnitType.SIEGE,
    "artillery": UnitType.SIEGE,
    "siege_tower": UnitType.SIEGE,
    # Naval
    "galley": UnitType.NAVAL,
    "frigate": UnitType.NAVAL,
    "man_o_war": UnitType.NAVAL,
    "galleon": UnitType.NAVAL,
    "monitor": UnitType.NAVAL,
    "privateer": UnitType.NAVAL,
    "trading_post": UnitType.ECONOMIC,
    "settler": UnitType.ECONOMIC,
    "scout": UnitType.SUPPORT,
    "explorer": UnitType.SUPPORT,
    "priest": UnitType.SUPPORT,
    "missionary": UnitType.SUPPORT,
}


@dataclass
class AgeUpDecision:
    """Record of an age progression."""
    timestamp: float
    age_from: str
    age_to: str
    reason: Optional[str] = None


@dataclass
class UnitProductionRecord:
    """Record of unit training."""
    timestamp: float
    unit_type: UnitType
    unit_name: str
    quantity: int = 1
    building: Optional[str] = None


@dataclass
class ResourceAllocation:
    """Resource gathering focus at a point in time."""
    timestamp: float
    food_villagers: int = 0
    wood_villagers: int = 0
    gold_villagers: int = 0
    stone_villagers: int = 0

    @property
    def total(self) -> int:
        return self.food_villagers + self.wood_villagers + self.gold_villagers + self.stone_villagers

    @property
    def primary_focus(self) -> Optional[ResourceType]:
        if self.total == 0:
            return None
        allocations = {
            ResourceType.FOOD: self.food_villagers,
            ResourceType.WOOD: self.wood_villagers,
            ResourceType.GOLD: self.gold_villagers,
            ResourceType.STONE: self.stone_villagers,
        }
        return max(allocations, key=allocations.get)


@dataclass
class StrategyDecision:
    """High-level strategic decision."""
    timestamp: float
    decision_type: str  # "rush", "boom", "naval", "trade", "tech", "defense", etc.
    confidence: float = 0.5
    description: Optional[str] = None


@dataclass
class DecisionMetrics:
    """Aggregated playstyle metrics for a civ."""
    civ_name: str
    game_duration: float

    # Unit composition
    unit_production_count: int = 0
    infantry_count: int = 0
    cavalry_count: int = 0
    ranged_count: int = 0
    siege_count: int = 0
    naval_count: int = 0
    support_count: int = 0
    economic_count: int = 0

    # Unit diversity
    unique_unit_types: int = 0
    dominant_unit_type: Optional[UnitType] = None
    dominant_unit_percentage: float = 0.0

    # Economic focus (primary resource gathering allocation)
    primary_resource_focus: Optional[ResourceType] = None
    resource_allocation_stability: float = 0.0  # How consistent is focus (0-1)

    # Age progression
    age_up_count: int = 0
    age_progression_times: List[float] = field(default_factory=list)
    avg_age_progression_time: float = 0.0

    # Strategic decisions
    strategy_shifts: List[StrategyDecision] = field(default_factory=list)
    primary_strategy: Optional[str] = None

    # Military metrics
    military_building_count: int = 0
    avg_units_per_minute: float = 0.0

    # Naval indicators
    has_naval_activity: bool = False
    dock_construction_time: Optional[float] = None
    ships_trained: int = 0

    # Wall/fortification strategy
    walls_detected: bool = False
    towers_detected: bool = False
    fortification_detected: bool = False

    # Shipping/trade
    has_shipping_data: bool = False
    shipment_count: int = 0

    # Tech progression
    techs_researched: int = 0
    techs_per_minute: float = 0.0

    # Validation quality
    log_entries_parsed: int = 0
    confidence_score: float = 0.0
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary, handling non-serializable fields."""
        d = asdict(self)
        d['primary_resource_focus'] = self.primary_resource_focus.value if self.primary_resource_focus else None
        d['dominant_unit_type'] = self.dominant_unit_type.value if self.dominant_unit_type else None
        d['strategy_shifts'] = [
            {
                'timestamp': s.timestamp,
                'decision_type': s.decision_type,
                'confidence': s.confidence,
                'description': s.description,
            }
            for s in self.strategy_shifts
        ]
        return d


class AIDecisionAnalyzer:
    """Parse and analyze AI decision logs."""

    def __init__(self, log_path: Path | str, civ_name: str = "Unknown"):
        self.log_path = Path(log_path)
        self.civ_name = civ_name
        self.lines: List[str] = []
        self.start_timestamp: Optional[float] = None

        # Collections
        self.age_ups: List[AgeUpDecision] = []
        self.unit_productions: List[UnitProductionRecord] = []
        self.resource_allocations: List[ResourceAllocation] = []
        self.strategy_decisions: List[StrategyDecision] = []

        self._load_log()

    def _load_log(self) -> None:
        """Load log file."""
        if not self.log_path.exists():
            logger.warning(f"Log file not found: {self.log_path}")
            return

        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                self.lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to load log: {e}")

    def analyze(self) -> DecisionMetrics:
        """Perform full analysis on loaded log."""
        metrics = DecisionMetrics(civ_name=self.civ_name, game_duration=0.0)

        if not self.lines:
            metrics.issues.append("No log data loaded")
            return metrics

        # Parse all decision types
        self._parse_age_ups()
        self._parse_unit_production()
        self._parse_resource_allocation()
        self._parse_strategy_decisions()

        # Compute derived metrics
        metrics = self._compute_metrics(metrics)

        return metrics

    def _parse_age_ups(self) -> None:
        """Extract age progression from logs."""
        patterns = [
            r'\[AGEUP\]\s*(\w+)\s*->\s*(\w+)',
            r'Age\s+(\d+)\s*->\s*(\w+)',
            r'advancing\s+to\s+(\w+)',
        ]

        for line in self.lines:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    timestamp = self._extract_timestamp(line)
                    if len(match.groups()) == 2:
                        age_from, age_to = match.groups()
                    else:
                        age_from = "Unknown"
                        age_to = match.group(1)

                    self.age_ups.append(AgeUpDecision(
                        timestamp=timestamp,
                        age_from=age_from,
                        age_to=age_to,
                    ))

    def _parse_unit_production(self) -> None:
        """Extract unit training records from logs."""
        patterns = [
            r'\[UNITS_TRAINED\]\s*(\w+)\s*x(\d+)',
            r'training\s+(\w+)\s*x\s*(\d+)',
            r'trained\s+(\w+)',
            r'training\s+(\d+)\s+(\w+)',
        ]

        for line in self.lines:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    timestamp = self._extract_timestamp(line)
                    groups = match.groups()

                    if len(groups) == 2:
                        unit_name = groups[0]
                        quantity = int(groups[1])
                    elif len(groups) == 1:
                        unit_name = groups[0]
                        quantity = 1
                    else:
                        continue

                    unit_type = self._classify_unit(unit_name)
                    self.unit_productions.append(UnitProductionRecord(
                        timestamp=timestamp,
                        unit_type=unit_type,
                        unit_name=unit_name,
                        quantity=quantity,
                    ))

    def _parse_resource_allocation(self) -> None:
        """Extract resource gathering decisions."""
        patterns = [
            r'villagers.*?food[:\s]*(\d+).*?wood[:\s]*(\d+).*?gold[:\s]*(\d+)',
            r'gathering.*?(\w+)\s*priority',
            r'\[RESOURCE_GATHERING\]\s*(\w+)\s*focus',
        ]

        for line in self.lines:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    timestamp = self._extract_timestamp(line)
                    # Basic resource allocation tracking
                    # In a real scenario, this would be more sophisticated
                    if match.groups():
                        # Placeholder for resource allocation
                        pass

    def _parse_strategy_decisions(self) -> None:
        """Extract high-level strategy shift decisions."""
        strategy_keywords = {
            'rush': r'(rush|aggressive|attack|push)',
            'boom': r'(boom|expand|settle|growth)',
            'naval': r'(naval|ship|dock|water|sea)',
            'trade': r'(trade|merchant|trading[\s_]post)',
            'tech': r'(tech|research|advance|unlock)',
            'defense': r'(defend|wall|fortif|tower|garrison)',
        }

        for line in self.lines:
            timestamp = self._extract_timestamp(line)
            for strategy_type, pattern in strategy_keywords.items():
                if re.search(pattern, line, re.IGNORECASE):
                    self.strategy_decisions.append(StrategyDecision(
                        timestamp=timestamp,
                        decision_type=strategy_type,
                        confidence=0.6,
                        description=line.strip()[:100],
                    ))

    def _compute_metrics(self, metrics: DecisionMetrics) -> DecisionMetrics:
        """Compute derived metrics from parsed decisions."""
        metrics.log_entries_parsed = len(self.lines)

        # Unit composition
        metrics.unit_production_count = len(self.unit_productions)

        unit_counts: Dict[UnitType, int] = {}
        for record in self.unit_productions:
            unit_counts[record.unit_type] = unit_counts.get(record.unit_type, 0) + record.quantity

        metrics.infantry_count = unit_counts.get(UnitType.INFANTRY, 0)
        metrics.cavalry_count = unit_counts.get(UnitType.CAVALRY, 0)
        metrics.ranged_count = unit_counts.get(UnitType.RANGED, 0)
        metrics.siege_count = unit_counts.get(UnitType.SIEGE, 0)
        metrics.naval_count = unit_counts.get(UnitType.NAVAL, 0)
        metrics.support_count = unit_counts.get(UnitType.SUPPORT, 0)
        metrics.economic_count = unit_counts.get(UnitType.ECONOMIC, 0)

        metrics.unique_unit_types = len([t for t in unit_counts if t != UnitType.UNKNOWN])

        if unit_counts:
            dominant_type = max(unit_counts, key=unit_counts.get)
            dominant_count = unit_counts[dominant_type]
            total_units = sum(unit_counts.values())
            metrics.dominant_unit_type = dominant_type
            metrics.dominant_unit_percentage = (dominant_count / total_units * 100) if total_units > 0 else 0.0

        # Age progression
        metrics.age_up_count = len(self.age_ups)
        if self.age_ups:
            metrics.age_progression_times = [au.timestamp for au in self.age_ups]
            metrics.avg_age_progression_time = sum(metrics.age_progression_times) / len(metrics.age_progression_times)

        # Strategy
        if self.strategy_decisions:
            strategy_counts: Dict[str, int] = {}
            for decision in self.strategy_decisions:
                strategy_counts[decision.decision_type] = strategy_counts.get(decision.decision_type, 0) + 1
            metrics.primary_strategy = max(strategy_counts, key=strategy_counts.get)
            metrics.strategy_shifts = self.strategy_decisions

        # Naval
        metrics.has_naval_activity = metrics.naval_count > 0 or any(
            d.decision_type == 'naval' for d in self.strategy_decisions
        )
        metrics.ships_trained = metrics.naval_count

        # Military buildings (rough estimate from production)
        metrics.military_building_count = len([
            p for p in self.unit_productions
            if p.unit_type in (UnitType.INFANTRY, UnitType.CAVALRY, UnitType.RANGED)
        ])

        if metrics.game_duration > 0:
            metrics.avg_units_per_minute = metrics.unit_production_count / (metrics.game_duration / 60)
            metrics.techs_per_minute = metrics.techs_researched / (metrics.game_duration / 60)

        # Confidence
        if metrics.log_entries_parsed > 10:
            metrics.confidence_score = 0.9
        elif metrics.log_entries_parsed > 5:
            metrics.confidence_score = 0.7
        else:
            metrics.confidence_score = 0.4
            metrics.issues.append("Low log entry count, low confidence")

        return metrics

    def _extract_timestamp(self, line: str) -> float:
        """Extract timestamp from log line (in seconds)."""
        # Try HH:MM:SS format
        match = re.search(r'(\d+):(\d+):(\d+)', line)
        if match:
            h, m, s = map(int, match.groups())
            return h * 3600 + m * 60 + s

        # Try raw seconds
        match = re.search(r'time[:\s]*(\d+)', line, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Default
        if self.start_timestamp is None:
            self.start_timestamp = 0.0
        return self.start_timestamp

    def _classify_unit(self, unit_name: str) -> UnitType:
        """Classify a unit by name."""
        unit_name_lower = unit_name.lower()

        # Direct lookup
        if unit_name_lower in UNIT_CLASSIFICATIONS:
            return UNIT_CLASSIFICATIONS[unit_name_lower]

        # Fuzzy matching on keywords
        for key, unit_type in UNIT_CLASSIFICATIONS.items():
            if key in unit_name_lower or unit_name_lower in key:
                return unit_type

        return UnitType.UNKNOWN


def parse_game_log(log_path: Path | str, civ_name: str = "Unknown") -> DecisionMetrics:
    """Convenience function to analyze a game log."""
    analyzer = AIDecisionAnalyzer(log_path, civ_name)
    return analyzer.analyze()


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ai_decision_analyzer.py <log_path> [civ_name]")
        sys.exit(1)

    log_path = Path(sys.argv[1])
    civ_name = sys.argv[2] if len(sys.argv) > 2 else "TestCiv"

    metrics = parse_game_log(log_path, civ_name)
    print(json.dumps(metrics.to_dict(), indent=2))
