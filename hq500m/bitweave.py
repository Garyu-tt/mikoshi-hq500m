"""CPU BitWeave-inspired sparse-event HQ500M engine.

This is NOT the CUDA R04 binary GEMM kernel. It uses packed 1024-bit spike
masks, popcount, lazy LIF updates and exact on-demand C5 edges, with an
explicitly artificial, optional sensory broadcast to activate more cells.
The 500M address space stays virtual. This is a synthetic toy network.
"""
from functools import lru_cache
import json
import math
from pathlib import Path

from .core import (
    ACTIONS, BOUNDS, BRIDGES, INPUT_PORTS, MOTOR_PORTS, REGION_NAMES,
    SEED, VIRTUAL_NEURONS, WIDTH, _normalize_observation, edge, mix, region,
)

PAGE = 1024
GAIN = 0.000035
DECAY = 0.68
STATE_SCHEMA = "mikoshi-hq500m-bitweave-cpu-state-v1"


@lru_cache(maxsize=4096)
def _edges(global_id):
    # Full signed deterministic C5 weights, not quantized surrogate synapses.
    return tuple((target, weight * GAIN)
                 for slot in range(32)
                 for target, weight, _gene, _inhibitory in (edge(global_id, slot),))


class BitWeaveBrain:
    """Demand-computed, sparse LIF with packed spike masks and 7 region windows.

    pages=16 => 114,688 resident addresses; memory is proportional mainly to
    actually touched neuron states, not the 500M virtual address range.
    """

    def __init__(self, pages=16, ticks=6, learning=True, fanout=16):
        if type(pages) is not int or not 1 <= pages <= 128:
            raise ValueError("pages must be 1..128 per region")
        if type(ticks) is not int or not 1 <= ticks <= 32:
            raise ValueError("ticks must be 1..32")
        if type(fanout) is not int or not 0 <= fanout <= 64:
            raise ValueError("fanout must be 0..64 per page, per active input")
        self.pages, self.ticks, self.fanout = pages, ticks, fanout
        self.learning = bool(learning)
        self.cells = pages * PAGE
        self.neurons = len(REGION_NAMES) * self.cells
        self.sensor_indices = {
            name: tuple(REGION_NAMES.index(r) * self.cells + offset + k
                        for k in range(WIDTH))
            for name, (r, offset, _desc) in INPUT_PORTS.items()
        }
        self.motor_indices = {
            name: tuple(REGION_NAMES.index(r) * self.cells + offset + k
                        for k in range(WIDTH))
            for name, (r, offset, _desc) in MOTOR_PORTS.items()
        }
        self.bridge_map = {}
        for sensor, motors in BRIDGES.items():
            for action in motors:
                for src, dst in zip(self.sensor_indices[sensor],
                                    self.motor_indices[action]):
                    self.bridge_map.setdefault(src, []).append((dst, sensor, action))
        self.q = {action: 0.0 for action in ACTIONS}
        self.gain = {}
        self.last_action = None
        self.last_sensors = []
        self.step_number = 0
        self.neural_ticks = 0
        self.plasticity_updates = 0
        # local-index -> (voltage, last-integrated-global-tick, last-fire-tick)
        self.membrane = {}
        # input current arriving at the NEXT tick, including across game steps.
        self.pending = {}

    def _local(self, global_id):
        reg = region(global_id)
        offset = global_id - BOUNDS[reg]
        if offset >= self.cells:
            return None
        return reg * self.cells + offset

    def _global(self, local_id):
        reg, offset = divmod(local_id, self.cells)
        return BOUNDS[reg] + offset

    def _input_currents(self, sensors):
        currents = {}
        active = [(i, name, val) for i, (name, val) in
                  enumerate(sensors.items()) if val != 0.0]
        # Bound CPU and memory, including hostile all-sensors requests.
        requested = len(active) * 7 * self.pages * self.fanout
        if requested > 50000:
            raise ValueError("too many simultaneous fanout injections; reduce pages/fanout")
        for input_idx, name, strength in active:
            impulse = strength * 1.65
            for pos in self.sensor_indices[name]:
                currents[pos] = currents.get(pos, 0.0) + impulse
            # Explicitly SYNTHETIC distributed sensory fanout; it does not
            # masquerade as original HQ500M C5 connectivity.
            if self.fanout:
                for pg in range(7 * self.pages):
                    # Multiplication by odd stride visits distinct lanes.
                    h = mix(SEED ^ ((input_idx + 1) << 44) ^ (pg * 0x9E3779B97F4A7C15))
                    start = h & 1023
                    stride = ((h >> 11) | 1) & 1023
                    base = pg * PAGE
                    for lane in range(self.fanout):
                        idx = base + ((start + lane * stride) & 1023)
                        currents[idx] = currents.get(idx, 0.0) + impulse
        return currents

    def step(self, observation):
        sensors, reward = _normalize_observation(observation)
        if self.learning and self.last_action is not None and reward:
            action = self.last_action
            self.q[action] = max(-2.0, min(2.0,
                self.q[action] + 0.18 * (reward - self.q[action])))
            for sensor in self.last_sensors:
                key = sensor + ":" + action
                if action in BRIDGES[sensor]:
                    self.gain[key] = max(0.55, min(1.5,
                        self.gain.get(key, 1.0) + 0.09 * reward))
                    self.plasticity_updates += 1
        injected = self._input_currents(sensors)
        counts = {action: 0 for action in ACTIONS}
        updated = set()
        fired = set()
        total_spikes = 0
        delivered = dropped_outside_window = evaluated = 0
        peak_spikes = peak_updated = 0
        for _ in range(self.ticks):
            now = self.neural_ticks + 1
            currents = self.pending
            self.pending = {}
            for pos, impulse in injected.items():
                currents[pos] = currents.get(pos, 0.0) + impulse
            peak_updated = max(peak_updated, len(currents))
            updated.update(currents)
            masks = {}
            for pos in sorted(currents):
                impulse = currents[pos]
                voltage, previous_tick, last_fired = self.membrane.get(pos, (0.0, -1, -100))
                if now - last_fired <= 2:
                    # Refractory: current is discarded, exactly as base Brain.
                    continue
                voltage = voltage * (DECAY ** (now - previous_tick)) + impulse
                if voltage >= 1.0:
                    self.membrane[pos] = (0.0, now, now)
                    page, lane = divmod(pos, PAGE)
                    masks[page] = masks.get(page, 0) | (1 << lane)
                else:
                    self.membrane[pos] = (max(-2.0, min(1.0, voltage)), now, last_fired)
            tick_spikes = sum(mask.bit_count() for mask in masks.values())
            total_spikes += tick_spikes
            peak_spikes = max(peak_spikes, tick_spikes)
            for action, pos_group in self.motor_indices.items():
                first = pos_group[0]
                page, lane = divmod(first, PAGE)
                counts[action] += (masks.get(page, 0) & (((1 << WIDTH) - 1) << lane)).bit_count()
            # Popcount and bit scan operate on packed 1024-neuron spike pages.
            # Only fired sources have outgoing C5 edges computed.
            for page in sorted(masks):
                bits = masks[page]
                while bits:
                    low_bit = bits & -bits
                    lane = low_bit.bit_length() - 1
                    bits ^= low_bit
                    src = page * PAGE + lane
                    fired.add(src)
                    gid = self._global(src)
                    for dst_gid, weight in _edges(gid):
                        evaluated += 1
                        dst = self._local(dst_gid)
                        if dst is None:
                            dropped_outside_window += 1
                            continue
                        self.pending[dst] = self.pending.get(dst, 0.0) + weight
                        delivered += 1
                    for dst, sensor, action in self.bridge_map.get(src, ()):
                        gain = 1.25 * self.gain.get(sensor + ":" + action, 1.0)
                        self.pending[dst] = self.pending.get(dst, 0.0) + gain
            self.neural_ticks = now
        scores = {action: counts[action] / WIDTH + 0.4 * self.q[action]
                  for action in ACTIONS}
        scores["idle"] += 0.05
        chosen = max(ACTIONS, key=lambda action: scores[action])
        self.last_action = chosen
        self.last_sensors = [name for name, value in sensors.items() if value > 0]
        self.step_number += 1
        return {
            "schema": "mikoshi-hq500m-game-v1",
            "engine": "bitweave-cpu-packed-sparse",
            "step": self.step_number, "action": chosen,
            "motor_scores": {a: round(scores[a], 4) for a in ACTIONS},
            "motor_spikes": counts, "spikes": total_spikes,
            "neural_ticks": self.ticks, "resident_neurons": self.neurons,
            "virtual_neurons": VIRTUAL_NEURONS,
            "plasticity_updates": self.plasticity_updates,
            "source": "synthetic_neural_ports", "motor_mapping": "toy-functional",
            "unique_updated_neurons": len(updated),
            "unique_spiking_neurons": len(fired),
            "peak_spiking_in_one_tick": peak_spikes,
            "peak_updated_in_one_tick": peak_updated,
            "synapses_evaluated": evaluated,
            "synapses_delivered": delivered,
            "nonresident_synapse_events": dropped_outside_window,
            "fanout_per_page": self.fanout,
            "resident_pages": self.pages * 7,
            "synthetic_fanout": bool(self.fanout),
        }

    def snapshot(self):
        return {
            "schema": STATE_SCHEMA, "virtual_neurons": VIRTUAL_NEURONS,
            "pages": self.pages, "ticks": self.ticks, "fanout": self.fanout,
            "learning": self.learning, "q": self.q, "gain": self.gain,
            "last_action": self.last_action, "last_sensors": self.last_sensors,
            "step_number": self.step_number, "neural_ticks": self.neural_ticks,
            "plasticity_updates": self.plasticity_updates,
            "membrane": {str(k): list(v) for k, v in self.membrane.items()},
            "pending": {str(k): v for k, v in self.pending.items()},
        }

    def restore(self, state):
        if state.get("schema") != STATE_SCHEMA or any((
            state.get("virtual_neurons") != VIRTUAL_NEURONS,
            state.get("pages") != self.pages, state.get("ticks") != self.ticks,
            state.get("fanout") != self.fanout,
            state.get("learning") != self.learning,
        )):
            raise ValueError("incompatible BitWeave CPU checkpoint")
        for field in ("step_number", "neural_ticks", "plasticity_updates"):
            if type(state.get(field)) is not int or not 0 <= state[field] <= 10**12:
                raise ValueError("invalid counter")
        q, gain = state.get("q"), state.get("gain")
        if not isinstance(q, dict) or set(q) != set(ACTIONS):
            raise ValueError("invalid action policy")
        if not isinstance(gain, dict) or len(gain) > len(BRIDGES)*len(ACTIONS):
            raise ValueError("invalid bridge map")
        for a, v in q.items():
            if type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 2:
                raise ValueError("invalid Q value")
        for key, v in gain.items():
            parts = key.split(":")
            if (len(parts) != 2 or parts[0] not in BRIDGES
                    or parts[1] not in BRIDGES[parts[0]]
                    or type(v) not in (int, float) or not math.isfinite(v)
                    or not .55 <= v <= 1.5):
                raise ValueError("invalid bridge gain")
        if state.get("last_action") is not None and state["last_action"] not in ACTIONS:
            raise ValueError("invalid last action")
        previous = state.get("last_sensors")
        if not isinstance(previous, list) or any(x not in INPUT_PORTS for x in previous):
            raise ValueError("invalid last sensors")
        membrane = state.get("membrane")
        pending = state.get("pending")
        if not isinstance(membrane, dict) or not isinstance(pending, dict):
            raise ValueError("invalid neuron state")
        if len(membrane) > self.neurons or len(pending) > self.neurons:
            raise ValueError("oversized neuron state")
        clean_membrane = {}
        for key, values in membrane.items():
            pos = int(key)
            if not (0 <= pos < self.neurons and isinstance(values, list)
                    and len(values) == 3 and type(values[0]) in (float, int)
                    and math.isfinite(values[0]) and abs(values[0]) <= 2
                    and type(values[1]) is int and -1 <= values[1] <= state["neural_ticks"]
                    and type(values[2]) is int and -100 <= values[2] <= state["neural_ticks"]):
                raise ValueError("invalid voltage or clock")
            clean_membrane[pos] = tuple(values)
        clean_pending = {}
        for key, current in pending.items():
            pos = int(key)
            if (not 0 <= pos < self.neurons or type(current) not in (int, float)
                    or not math.isfinite(current) or abs(current) > 1e5):
                raise ValueError("invalid pending current")
            clean_pending[pos] = current
        self.q = dict(q)
        self.gain = dict(gain)
        self.last_action = state["last_action"]
        self.last_sensors = list(previous)
        for field in ("step_number", "neural_ticks", "plasticity_updates"):
            setattr(self, field, state[field])
        self.membrane = clean_membrane
        self.pending = clean_pending

    def save(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        try:
            temp.write_text(json.dumps(self.snapshot(), separators=(",", ":")),
                            encoding="utf8")
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)

    def load(self, path):
        source = Path(path)
        if source.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("checkpoint too large")
        self.restore(json.loads(source.read_text(encoding="utf8")))
