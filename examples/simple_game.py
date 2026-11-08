"""Tiny fake arena; replace these observations with your own game's sensors.

Run from the repository root: python3 examples/simple_game.py
No external dependencies.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import Brain

brain = Brain(cells=128, ticks=6)
arena = [
    {"eye_left": 0.9, "obstacle_left": 0.8},
    {"obstacle_right": 0.8, "reward": 0.5},
    {"food": 0.9, "reward": 0.3},
    {"threat": 0.95, "reward": 1.0},
    {"spinal_sensory": 0.7, "reward": -0.2},
]
for frame, observation in enumerate(arena, 1):
    decision = brain.step(observation)
    # Only your game adapter should apply movement/collisions/physics:
    print("frame", frame, "observed", observation,
          "->", decision["action"], "spikes", decision["spikes"])
