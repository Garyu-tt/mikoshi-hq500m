"""CPU-first, dependency-free synthetic HQ500M brain and labeled game ports.

Only seven small windows are resident. 500M is a fixed VIRTUAL address range.
Functional port-to-motor bridges are an explicit toy engineering addition, NOT
measured human anatomy or biological brain simulation.
"""
import json
import math
from pathlib import Path

VIRTUAL_NEURONS = 500_000_000
MODULE = 1024
SEED = 37421
MASK = (1 << 64) - 1
K = 0x517cc1b727220a95
REGION_NAMES = ("cortex", "cerebellum", "hippocampus", "thalamus",
                "basal_ganglia", "brainstem", "limbic")
BOUNDS = (0, 224999424, 294999040, 344999936,
          394999808, 434999296, 469999616, VIRTUAL_NEURONS)
ROUTES = (3, 5, 0, 0, 3, 1, 2)

# Port offsets are within the FIRST 128 addresses of one 1024-address module.
# These are engineering IO labels, not inferred biological cell classes.
INPUT_PORTS = {
    "eye_left": ("thalamus", 0, "left retinal signal -> toy thalamic relay"),
    "eye_right": ("thalamus", 12, "right retinal signal -> toy thalamic relay"),
    "ear_left": ("thalamus", 24, "left acoustic signal -> toy auditory relay"),
    "ear_right": ("thalamus", 36, "right acoustic signal -> toy auditory relay"),
    "touch": ("thalamus", 48, "body touch -> ascending sensory relay"),
    "obstacle_left": ("thalamus", 60, "left obstacle perception"),
    "obstacle_right": ("thalamus", 72, "right obstacle perception"),
    "food": ("thalamus", 84, "environmental food cue"),
    "spinal_sensory": ("brainstem", 0, "spinal cord ascending / proprioception input"),
    "fatigue": ("brainstem", 12, "synthetic fatigue/homeostatic input"),
    "balance": ("cerebellum", 0, "vestibular/balance input"),
    "novelty": ("hippocampus", 0, "new context / episodic cue"),
    "smell": ("limbic", 0, "olfactory-like input"),
    "hunger": ("limbic", 12, "hunger/homeostasis input"),
    "threat": ("limbic", 24, "salience / danger cue"),
}
MOTOR_PORTS = {
    "forward": ("brainstem", 48, "descending locomotor / spinal efferent proxy"),
    "left": ("brainstem", 60, "descending turn-left output"),
    "right": ("brainstem", 72, "descending turn-right output"),
    "interact": ("cortex", 0, "voluntary interaction / tool command"),
    "retreat": ("brainstem", 84, "descending defensive movement"),
    "idle": ("basal_ganglia", 0, "action suppression / no-op"),
}
ACTIONS = tuple(MOTOR_PORTS)
# Explicit, inspectable artificial pathways. These are not the 32 genome edges.
BRIDGES = {
    "eye_left": ("left",), "eye_right": ("right",),
    "ear_left": ("left",), "ear_right": ("right",),
    "touch": ("retreat",), "obstacle_left": ("right",),
    "obstacle_right": ("left",), "food": ("interact",),
    "spinal_sensory": ("retreat",), "fatigue": ("idle",),
    "balance": ("forward",), "novelty": ("interact",),
    "smell": ("forward",), "hunger": ("forward",),
    "threat": ("retreat",),
}
# Familiar compatibility aliases with the BrainFryGameAgent observation protocol.
GAME_ALIASES = {
    "obstacle": ("obstacle_left", "obstacle_right"),
}
WIDTH = 12


def mix(x):
    x = (x + 0x9e3779b97f4a7c15) & MASK
    x = ((x ^ (x >> 30)) * 0xbf58476d1ce4e5b9) & MASK
    x = ((x ^ (x >> 27)) * 0x94d049bb133111eb) & MASK
    return x ^ (x >> 31)


def region(global_id):
    if isinstance(global_id, bool) or not isinstance(global_id, int) or not 0 <= global_id < VIRTUAL_NEURONS:
        raise ValueError("global_id must be an integer in 0..499999999")
    for r in range(7):
        if global_id < BOUNDS[r + 1]:
            return r
    raise AssertionError("unreachable")


def edge(global_id, slot):
    """Exact deterministic 32-edge potential connectivity of original HQ500M."""
    r = region(global_id)
    if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < 32:
        raise ValueError("slot must be in 0..31")
    h0 = mix(global_id ^ SEED)
    h = mix(h0 ^ (((slot + 1) * K) & MASK))
    inhibitory = int(h0 % 100 < 20)
    if slot < 24:
        start = global_id // MODULE * MODULE
        count = min(MODULE, VIRTUAL_NEURONS - start)
        odd = ((h0 >> 11) & 0xFFFFFFFF) | 1
        dst = start + (((global_id - start + (slot + 1) * odd) & 0xFFFFFFFF) % count)
        gene = 0
    else:
        target_region = ROUTES[r]
        start = BOUNDS[target_region]
        end = BOUNDS[target_region + 1]
        modules = (end - start + MODULE - 1) // MODULE
        start_of_module = start + (mix(h ^ (global_id // MODULE)) % modules) * MODULE
        count = min(MODULE, end - start_of_module)
        dst = start_of_module + ((h >> 24) % count)
        gene = r + 1
    weight = 300 + ((h >> 33) % 4800)
    return (dst, -weight if inhibitory else weight, gene, inhibitory)


def port_id(direction, name):
    source = INPUT_PORTS if direction == "input" else MOTOR_PORTS
    region_name, offset, _ = source[name]
    return BOUNDS[REGION_NAMES.index(region_name)] + offset


def describe_ports():
    out = {"schema": "mikoshi-hq500m-ports-v1", "virtual_neurons": VIRTUAL_NEURONS,
           "resident_default": 7 * 128, "port_width": WIDTH,
           "port_kind": "synthetic-functional-not-biological", "regions": [],
           "inputs": {}, "outputs": {}, "pathways": {}}
    for i, name in enumerate(REGION_NAMES):
        out["regions"].append({"name": name, "virtual_start": BOUNDS[i],
                               "virtual_end_inclusive": BOUNDS[i + 1] - 1,
                               "resident_module_start": BOUNDS[i]})
    for direction, table, key in (("input", INPUT_PORTS, "inputs"),
                                  ("output", MOTOR_PORTS, "outputs")):
        for name, (reg, offset, purpose) in table.items():
            first = port_id(direction, name)
            out[key][name] = {"region": reg, "neuron_ids": [first, first + WIDTH - 1],
                              "direction": direction, "meaning": purpose}
    for sensor, motors in BRIDGES.items():
        out["pathways"][sensor] = list(motors)
    out["spinal_cord_note"] = ("The spinal cord itself is NOT simulated. "
                               "'spinal_sensory' receives ascending body-state values; "
                               "brainstem motor ports emit abstract descending game commands.")
    return out


def _normalize_observation(observation):
    if not isinstance(observation, dict) or len(observation) > 24:
        raise ValueError("observation must be a small JSON object")
    allowed = set(INPUT_PORTS) | set(GAME_ALIASES) | {"reward"}
    unknown = set(observation) - allowed
    if unknown:
        raise ValueError("unknown input port(s): " + ", ".join(sorted(unknown)))
    values = {x: 0.0 for x in INPUT_PORTS}
    reward = 0.0
    for name, value in observation.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(name + " must be a finite number")
        if not -1.0 <= value <= 1.0:
            raise ValueError(name + " must be between -1 and 1")
        value = float(value)
        if name == "reward":
            reward = value
        elif name in GAME_ALIASES:
            for target in GAME_ALIASES[name]:
                values[target] = max(-1.0, min(1.0, values[target] + value))
        else:
            values[name] = max(-1.0, min(1.0, values[name] + value))
    return values, reward


class Brain:
    """Seven bounded active windows, with deterministic wiring and game IO.

    One step consists of 1..32 synchronous neural ticks. No full 500M allocation.
    Sensor->motor plastic bridge weights and action-value policy are toy additions.
    """

    def __init__(self, cells=128, ticks=6, learning=True):
        if type(cells) is not int or cells not in (128, 256, 512, 1024):
            raise ValueError("cells must be 128, 256, 512 or 1024 per region")
        if type(ticks) is not int or not 1 <= ticks <= 32:
            raise ValueError("ticks must be 1..32")
        self.cells = cells
        self.ticks = ticks
        self.learning = bool(learning)
        self.ids = []
        for start in BOUNDS[:-1]:
            self.ids.extend(range(start, start + cells))
        self.index = {node: i for i, node in enumerate(self.ids)}
        self.neurons = len(self.ids)
        self.local_edges = 0
        self.links = [[] for _ in self.ids]
        # No full graph is constructed. Ignore dormant or nonresident targets.
        for i, source in enumerate(self.ids):
            for slot in range(32):
                target, weight, _, _ = edge(source, slot)
                dst = self.index.get(target)
                if dst is not None:
                    self.links[i].append((dst, weight * 0.000035))
                    self.local_edges += 1
        self.sensor_indices = {name: tuple(self.index[port_id("input", name) + n]
                                     for n in range(WIDTH)) for name in INPUT_PORTS}
        self.motor_indices = {name: tuple(self.index[port_id("output", name) + n]
                                    for n in range(WIDTH)) for name in MOTOR_PORTS}
        self.bridge_links = [[] for _ in self.ids]
        for sensor, motors in BRIDGES.items():
            for action in motors:
                for src, dst in zip(self.sensor_indices[sensor], self.motor_indices[action]):
                    self.bridge_links[src].append((dst, sensor, action))
        self.voltage = [0.0] * self.neurons
        self.current = [0.0] * self.neurons
        self.refractory = [0] * self.neurons
        self.q = {action: 0.0 for action in ACTIONS}
        self.gain = {}
        self.last_action = None
        self.last_sensors = []
        self.step_number = 0
        self.neural_ticks = 0
        self.plasticity_updates = 0

    def step(self, observation):
        sensors, reward = _normalize_observation(observation)
        if self.learning and self.last_action is not None and reward:
            action = self.last_action
            self.q[action] = max(-2.0, min(2.0, self.q[action] + 0.18 * (reward - self.q[action])))
            for sensor in self.last_sensors:
                key = sensor + ":" + action
                if action in BRIDGES[sensor]:
                    self.gain[key] = max(0.55, min(1.5, self.gain.get(key, 1.0) + 0.09 * reward))
                    self.plasticity_updates += 1
        injected = []
        for name, strength in sensors.items():
            if strength != 0:
                injected.append((self.sensor_indices[name], strength * 1.65))
        counts = {action: 0 for action in ACTIONS}
        total_spikes = 0
        for _ in range(self.ticks):
            for group, impulse in injected:
                for i in group:
                    self.current[i] += impulse
            spiked = []
            for i in range(self.neurons):
                impulse = self.current[i]
                self.current[i] = 0.0
                if self.refractory[i]:
                    self.refractory[i] -= 1
                    self.voltage[i] = 0.0
                    continue
                v = self.voltage[i] * 0.68 + impulse
                if v >= 1.0:
                    self.voltage[i] = 0.0
                    self.refractory[i] = 2
                    spiked.append(i)
                else:
                    self.voltage[i] = max(-2.0, min(1.0, v))
            total_spikes += len(spiked)
            for i in spiked:
                for dst, weight in self.links[i]:
                    self.current[dst] += weight
                for dst, sensor, action in self.bridge_links[i]:
                    self.current[dst] += 1.25 * self.gain.get(sensor + ":" + action, 1.0)
            hit = set(spiked)
            for action, group in self.motor_indices.items():
                counts[action] += sum(i in hit for i in group)
            self.neural_ticks += 1
        scores = {action: counts[action] / WIDTH + 0.4 * self.q[action]
                  for action in ACTIONS}
        scores["idle"] += 0.05
        chosen = max(ACTIONS, key=lambda action: scores[action])
        self.last_action = chosen
        self.last_sensors = [name for name, val in sensors.items() if val > 0.0]
        self.step_number += 1
        return {"schema": "mikoshi-hq500m-game-v1", "step": self.step_number,
                "action": chosen, "motor_scores": {a: round(scores[a], 4) for a in ACTIONS},
                "motor_spikes": counts, "spikes": total_spikes,
                "neural_ticks": self.ticks, "resident_neurons": self.neurons,
                "virtual_neurons": VIRTUAL_NEURONS,
                "plasticity_updates": self.plasticity_updates,
                "source": "synthetic_neural_ports", "motor_mapping": "toy-functional"}

    def snapshot(self):
        return {"schema": "mikoshi-hq500m-state-v1", "virtual_neurons": VIRTUAL_NEURONS,
                "cells": self.cells, "ticks": self.ticks, "learning": self.learning,
                "q": self.q, "gain": self.gain, "last_action": self.last_action,
                "last_sensors": self.last_sensors, "step_number": self.step_number,
                "neural_ticks": self.neural_ticks,
                "plasticity_updates": self.plasticity_updates,
                "voltage": self.voltage, "current": self.current,
                "refractory": self.refractory}

    def restore(self, state):
        if not isinstance(state, dict) or state.get("schema") != "mikoshi-hq500m-state-v1":
            raise ValueError("unsupported checkpoint")
        if state.get("virtual_neurons") != VIRTUAL_NEURONS or state.get("cells") != self.cells or state.get("ticks") != self.ticks:
            raise ValueError("checkpoint geometry mismatch")
        if type(state.get("learning")) is not bool or state["learning"] != self.learning:
            raise ValueError("checkpoint learning mode mismatch")
        q, gain = state.get("q"), state.get("gain")
        if not isinstance(q, dict) or set(q) != set(ACTIONS):
            raise ValueError("invalid action values")
        if not isinstance(gain, dict) or len(gain) > len(INPUT_PORTS) * len(ACTIONS):
            raise ValueError("invalid plasticity map")
        for action, val in q.items():
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not -2 <= val <= 2:
                raise ValueError("invalid q-value")
        for key, val in gain.items():
            parts = key.split(":")
            if len(parts) != 2 or parts[0] not in BRIDGES or parts[1] not in BRIDGES[parts[0]]:
                raise ValueError("invalid plastic synapse key")
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not .55 <= val <= 1.5:
                raise ValueError("invalid plastic synapse weight")
        last = state.get("last_action")
        prev_sensors = state.get("last_sensors")
        if last is not None and last not in ACTIONS:
            raise ValueError("invalid last action")
        if not isinstance(prev_sensors, list) or len(prev_sensors) > len(INPUT_PORTS) or any(x not in INPUT_PORTS for x in prev_sensors):
            raise ValueError("invalid last sensor set")
        arrays = []
        for field in ("voltage", "current", "refractory"):
            values = state.get(field)
            if not isinstance(values, list) or len(values) != self.neurons:
                raise ValueError("invalid state length: " + field)
            if field == "refractory":
                if any(type(v) is not int or not 0 <= v <= 2 for v in values):
                    raise ValueError("invalid refractory values")
            elif any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 10 for v in values):
                raise ValueError("invalid voltage/current values")
            arrays.append(values[:])
        for field in ("step_number", "neural_ticks", "plasticity_updates"):
            val = state.get(field)
            if type(val) is not int or not 0 <= val <= 10**12:
                raise ValueError("invalid counter")
        self.q = dict(q)
        self.gain = dict(gain)
        self.last_action = last
        self.last_sensors = prev_sensors[:]
        self.step_number = state["step_number"]
        self.neural_ticks = state["neural_ticks"]
        self.plasticity_updates = state["plasticity_updates"]
        self.voltage, self.current, self.refractory = arrays

    def save(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        temp.write_text(json.dumps(self.snapshot(), separators=(",", ":")), encoding="utf8")
        temp.replace(target)

    def load(self, path):
        source = Path(path)
        if source.stat().st_size > 2_000_000:
            raise ValueError("checkpoint too large")
        self.restore(json.loads(source.read_text(encoding="utf8")))
