"""sim_farm — autonomous AI-vs-AI doctrine sweep for ANW.

Runs entirely as plain Python (NO LLM / Opus tokens): launches the game under
the memory/runtime safety guard, sets a deterministic seed, drives one
Skirmish match per matrix cell, harvests per-player [ANWP v=2] telemetry, and
grades each civ's per-age + walling doctrine with validate_per_age_v2.

Quality is invariant (it's the real engine); speed comes from short
observation windows + game-speed "Fast" + (later) parallel instances.
"""
