"""Exact-address demand-paged CPU HQ500M engine (experimental Fusion R02).

Packed sparse presynaptic events; a true global-ID paged scheduler.
This simulates only neurons receiving current, NOT all 500M virtual IDs.
Inactive (evicted) page state is held in host RAM. No GPU, no real anatomy.
"""
from collections import OrderedDict
import json
import math
from pathlib import Path

from .core import (
    ACTIONS, BOUNDS, BRIDGES, INPUT_PORTS, MOTOR_PORTS, REGION_NAMES,
    VIRTUAL_NEURONS, WIDTH, _normalize_observation, port_id,
)
from .bitweave import DECAY
from .c5_fast import source_edges as _edges
from .native_c5 import NativeC5, NativeUnavailable, EDGE_GAIN

PAGE_SIZE = 1024
FORMAT = "mikoshi-hq500m-page-cpu-r02"
MAX_EVENTS = 500_000
MAX_TRACKED = 2_000_000
PLASTIC_WINDOW = 15

class PagedBrain:
    """Exact C5 inter-page propagation with LRU residency, cold-state persistence.

    max_pages is the logical simultaneous page budget, not an allocation of
    max_pages*1024 dense state; pages are loaded only on delivered events.
    """
    def __init__(self, max_pages=128, ticks=6, learning=True, threshold=1.0,
                 plasticity_scope="remote", kernel="python",
                 lab_max_pulses=8192, event_kernel="python",
                 lif_kernel="python"):
        if type(max_pages) is not int or not 8 <= max_pages <= 1024:
            raise ValueError("max_pages must be 8..1024")
        if type(ticks) is not int or not 1 <= ticks <= 32:
            raise ValueError("ticks must be 1..32")
        # Explicit experimental excitability knob; default preserves R02/R03.
        if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0.25 <= threshold <= 2.0:
            raise ValueError("threshold must be finite, 0.25..2.0")
        if plasticity_scope not in ("remote", "all_exc"):
            raise ValueError("plasticity_scope must be remote or all_exc")
        if kernel not in ("python", "native", "auto"):
            raise ValueError("kernel must be python, native, or auto")
        self._native = None
        if kernel != "python":
            try:
                self._native = NativeC5()
            except NativeUnavailable:
                if kernel == "native":
                    raise
        self.c5_kernel = "native-c99" if self._native else "python"
        if event_kernel not in ("python", "native") or lif_kernel not in ("python", "native"):
            raise ValueError("event_kernel and lif_kernel must be python or native")
        self._native_math = self._native
        if (event_kernel == "native" or lif_kernel == "native") and self._native_math is None:
            self._native_math = NativeC5()
        self.event_kernel = event_kernel
        self.lif_kernel = lif_kernel
        self.plasticity_scope = plasticity_scope
        self.threshold = float(threshold)
        # The ordinary public API keeps its 8,192-pulse safety ceiling.
        # Lab-scale workloads explicitly opt into a bounded larger budget.
        if type(lab_max_pulses) is not int or lab_max_pulses not in (8192, 32768):
            raise ValueError("lab_max_pulses must be 8192 (default) or 32768")
        self.lab_max_pulses = lab_max_pulses
        self.max_events = max(MAX_EVENTS, lab_max_pulses * 33)
        self.max_tracked = max(MAX_TRACKED, lab_max_pulses * 40)
        self.max_pages = max_pages
        self.ticks = ticks
        self.learning = bool(learning)
        # Seven functional port modules are held pinned for interface stability.
        self.pinned = frozenset(b // PAGE_SIZE for b in BOUNDS[:-1])
        self.hot = OrderedDict((p, {}) for p in sorted(self.pinned))
        self.cold = {}
        self.pending = []  # (exact_dest_id, weight, source_id, C5_slot)
        self.gain = {}
        self.q = {action: 0.0 for action in ACTIONS}
        self.last_action = None
        self.last_sensors = []
        self.step_number = 0
        self.neural_ticks = 0
        self.plasticity_updates = 0
        # (global source ID, exact outgoing C5 slot) -> additive multiplier
        self.plastic = {}
        # global target -> list of (source ID, slot, arrived tick)
        self.pre_trace = {}
        self.last_post = {}
        self.input_ports = {k: tuple(range(port_id("input", k),
                    port_id("input", k) + WIDTH)) for k in INPUT_PORTS}
        self.motor_ports = {k: tuple(range(port_id("output", k),
                    port_id("output", k) + WIDTH)) for k in MOTOR_PORTS}
        self.motor_of = {gid: action for action, gids in self.motor_ports.items()
                         for gid in gids}
        self.bridges = {}
        for sensor, motor_names in BRIDGES.items():
            for motor in motor_names:
                for src, dst in zip(self.input_ports[sensor], self.motor_ports[motor]):
                    self.bridges.setdefault(src, []).append((dst, sensor, motor))
        self.load_count = len(self.hot)
        self.eviction_count = 0
        self.last_delivery_sample = []

    @property
    def neurons(self):
        """Resident neurons, not virtual neurons, not currently firing cells."""
        # The final virtual page has fewer than 1,024 valid addresses.
        return sum(min(PAGE_SIZE, VIRTUAL_NEURONS - page * PAGE_SIZE)
                   for page in self.hot)

    def _page(self, neuron_id):
        if type(neuron_id) is not int or not 0 <= neuron_id < VIRTUAL_NEURONS:
            raise ValueError("invalid global neuron ID")
        return neuron_id // PAGE_SIZE

    def _touch(self, neuron_id):
        page = self._page(neuron_id)
        if page in self.hot:
            self.hot.move_to_end(page)
            return self.hot[page]
        if len(self.hot) == self.max_pages:
            evict = next((p for p in self.hot if p not in self.pinned), None)
            if evict is None:
                raise RuntimeError("no evictable page")
            state = self.hot.pop(evict)
            if state:
                self.cold[evict] = state
            self.eviction_count += 1
        state = self.cold.pop(page, {})
        self.hot[page] = state
        self.load_count += 1
        return state

    def _validate_pulses(self, pulses):
        if pulses is None:
            return {}
        if not isinstance(pulses, dict) or len(pulses) > self.lab_max_pulses:
            raise ValueError("pulses must be a dictionary within lab_max_pulses limit")
        out = {}
        for gid, current in pulses.items():
            if type(gid) is not int or not 0 <= gid < VIRTUAL_NEURONS:
                raise ValueError("invalid pulse neuron ID")
            if type(current) not in (int, float) or not math.isfinite(current) or abs(current) > 100.:
                raise ValueError("pulse must be finite with absolute strength <= 100")
            if current:
                out[gid] = float(current)
        return out

    def _plastic_incoming(self, dest, src, slot, base, now):
        if (not self.learning or src < 0 or
                (slot < 24 and self.plasticity_scope == "remote") or base <= 0):
            return
        key = (src, slot)
        post = self.last_post.get(dest, -10**12)
        if 0 <= now - post <= PLASTIC_WINDOW:
            old = self.plastic.get(key, 0.0)
            new = max(-0.7, min(0.8, old - 0.004))
            if new != old:
                self.plastic[key] = new
                self.plasticity_updates += 1
        arr = self.pre_trace.setdefault(dest, [])
        arr[:] = [(s, k, t) for s, k, t in arr if now - t <= PLASTIC_WINDOW]
        arr.append((src, slot, now))
        if len(arr) > 1024:
            del arr[:len(arr) - 1024]

    def _plastic_post(self, dest, now):
        if not self.learning:
            return
        for src, slot, arrived in self.pre_trace.pop(dest, ()):
            lag = now - arrived
            if 0 <= lag <= PLASTIC_WINDOW:
                key = (src, slot)
                old = self.plastic.get(key, 0.0)
                new = max(-0.7, min(0.8, old + 0.008 * math.exp(-lag / 20.)))
                if new != old:
                    self.plastic[key] = new
                    self.plasticity_updates += 1
        self.last_post[dest] = now

    def _prune_expired_traces(self, now):
        cutoff = now - PLASTIC_WINDOW
        # Expired traces cannot affect learning, but keeping them forever
        # would make a long-running brain leak memory across cold pages.
        for gid, events in list(self.pre_trace.items()):
            live = [event for event in events if event[2] >= cutoff]
            if live:
                self.pre_trace[gid] = live
            else:
                del self.pre_trace[gid]
        for gid, tick in list(self.last_post.items()):
            if tick < cutoff:
                del self.last_post[gid]

    def step(self, observation, pulses=None, watch_ids=None):
        """Game observation and optional exact-ID external pulses (one tick).

        Unlike sensory game input, pulses are injected only on the first tick.
        """
        sensors, reward = _normalize_observation(observation)
        pulses = self._validate_pulses(pulses)
        if watch_ids is None:
            watched = set()
        elif isinstance(watch_ids, (set, tuple, list)) and len(watch_ids) <= 64:
            if any(type(gid) is not int or not 0 <= gid < VIRTUAL_NEURONS
                   for gid in watch_ids):
                raise ValueError("watch_ids must contain valid global neuron IDs")
            watched = set(watch_ids)
        else:
            raise ValueError("watch_ids must be a list, tuple or set with at most 64 IDs")
        watched_spikes = {str(gid): [] for gid in sorted(watched)}
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
        sensory = [(gid, v * 1.65, -1, -1)
                   for name, v in sensors.items() if v
                   for gid in self.input_ports[name]]
        counts = {a: 0 for a in ACTIONS}
        unique_updated, unique_spikes, contacted_pages = set(), set(), set()
        # "updated" historically means received input. Track ACTUAL voltage
        # integration separately, excluding the refractory short-circuit.
        integrated_neurons = set()
        refractory_skips = 0
        # These IDs receive an injected drive; spikes outside that set are
        # caused by native C5 connections, original game bridges or residual state.
        directly_driven = set(pulses)
        for name, value in sensors.items():
            if value:
                directly_driven.update(self.input_ports[name])
        spikes_by_tick = []
        undriven_spikes_by_tick = []
        all_spikes = delivery_count = remote_count = evaluated = 0
        peak_spikes = peak_updates = 0
        initial_loads, initial_evictions = self.load_count, self.eviction_count
        delivered_sample = []
        native_lif_cells = native_lif_pages = native_lif_integrations = 0
        for substep in range(self.ticks):
            now = self.neural_ticks + 1
            incoming = self.pending
            self.pending = []
            # Named sensors drive the same 12 IDs on each tick as the legacy API.
            incoming.extend(sensory)
            if substep == 0:
                incoming.extend((gid, val, -1, -1) for gid, val in pulses.items())
            if len(incoming) > self.max_events:
                raise RuntimeError("event budget exceeded; no silent dropping")
            # Both C99 and Python respect the exact stable order by
            # (target, source, slot). C only reduces already-sorted events.
            ordered = sorted(incoming, key=lambda e: (e[0], e[2], e[3]))
            if self.event_kernel == "native":
                currents = self._native_math.reduce_sorted(ordered)
            else:
                currents = {}
            for dest, amplitude, src, slot in ordered:
                contacted_pages.add(dest // PAGE_SIZE)
                if self.event_kernel == "python":
                    currents[dest] = currents.get(dest, 0.0) + amplitude
                if src >= 0 and slot >= 0:
                    delivery_count += 1
                    if slot >= 24:
                        remote_count += 1
                    # Local C5 synapses participate only under the explicit
                    # experimental all_exc flag; remote-only remains default.
                    self._plastic_incoming(dest, src, slot, amplitude, now)
                    if len(delivered_sample) < 96:
                        delivered_sample.append((src, slot, dest))
            peak_updates = max(peak_updates, len(currents))
            unique_updated.update(currents)
            firing = []
            if self.lif_kernel == "native":
                # Use C99 only on meaningfully dense 1024-ID pages.
                # Sparse one-event pages keep the faster Python branch.
                from itertools import groupby
                for pg, ids_iter in groupby(sorted(currents),
                                            key=lambda gid: gid // PAGE_SIZE):
                    ids = list(ids_iter)
                    state = self._touch(ids[0])
                    if len(ids) < 48:
                        for gid in ids:
                            voltage, last_tick, last_fire = state.get(gid, (0.0, -1, -100))
                            if now - last_fire <= 2:
                                refractory_skips += 1
                                continue
                            integrated_neurons.add(gid)
                            voltage = voltage * (DECAY ** (now - last_tick)) + currents[gid]
                            if voltage >= self.threshold:
                                state[gid] = (0.0, now, now)
                                firing.append(gid)
                                unique_spikes.add(gid)
                                if gid in watched:
                                    watched_spikes[str(gid)].append(now)
                                if gid in self.motor_of:
                                    counts[self.motor_of[gid]] += 1
                                self._plastic_post(gid, now)
                            else:
                                state[gid] = (max(-2.0, min(1.0, voltage)), now, last_fire)
                    else:
                        rows = []
                        for gid in ids:
                            v, t, fired_at = state.get(gid, (0.0, -1, -100))
                            rows.append((v, t, fired_at, currents[gid]))
                        resolved = self._native_math.lif_rows(rows, now, self.threshold)
                        native_lif_cells += len(ids)
                        native_lif_pages += 1
                        for gid, before, after in zip(ids, rows, resolved):
                            v, t, fired_at, spiked = after
                            if now - before[2] <= 2:
                                refractory_skips += 1
                                continue
                            integrated_neurons.add(gid)
                            native_lif_integrations += 1
                            state[gid] = (v, t, fired_at)
                            if spiked:
                                firing.append(gid)
                                unique_spikes.add(gid)
                                if gid in watched:
                                    watched_spikes[str(gid)].append(now)
                                if gid in self.motor_of:
                                    counts[self.motor_of[gid]] += 1
                                self._plastic_post(gid, now)
            else:
                # Original event-driven Python LIF; identical by default.
                current_page = None
                state = None
                for gid in sorted(currents):
                    pg = gid // PAGE_SIZE
                    if pg != current_page:
                        state = self._touch(gid)
                        current_page = pg
                    voltage, last_tick, last_fire = state.get(gid, (0.0, -1, -100))
                    if now - last_fire <= 2:
                        refractory_skips += 1
                        continue
                    integrated_neurons.add(gid)
                    voltage = voltage * (DECAY ** (now - last_tick)) + currents[gid]
                    if voltage >= self.threshold:
                        state[gid] = (0.0, now, now)
                        firing.append(gid)
                        unique_spikes.add(gid)
                        if gid in watched:
                            watched_spikes[str(gid)].append(now)
                        if gid in self.motor_of:
                            counts[self.motor_of[gid]] += 1
                        self._plastic_post(gid, now)
                    else:
                        state[gid] = (max(-2.0, min(1.0, voltage)), now, last_fire)
            peak_spikes = max(peak_spikes, len(firing))
            spikes_by_tick.append(len(firing))
            undriven_spikes_by_tick.append(
                sum(gid not in directly_driven for gid in firing))
            all_spikes += len(firing)
            outgoing = []
            # The native path is a bounded C99 batch; the original Python
            # LIF/learning/event routing retains ownership of all state.
            # Separate loops prevent a Python generator allocation per
            # spiking source, which would defeat native savings.
            if self._native is None:
                for gid in firing:
                    for slot, (dest, base) in enumerate(_edges(gid)):
                        evaluated += 1
                        factor = 1.0 + self.plastic.get((gid, slot), 0.0)
                        outgoing.append((dest, base * factor, gid, slot))
                    for dest, sensor, motor in self.bridges.get(gid, ()):
                        outgoing.append((dest, 1.25 * self.gain.get(
                            sensor + ":" + motor, 1.0), -1, -2))
            else:
                for start in range(0, len(firing), 8192):
                    chunk = firing[start:start + 8192]
                    targets, raw_weights = self._native.batch(chunk)
                    for index, gid in enumerate(chunk):
                        offset = index * 32
                        for slot in range(32):
                            evaluated += 1
                            base = raw_weights[offset + slot] * EDGE_GAIN
                            dest = targets[offset + slot]
                            factor = 1.0 + self.plastic.get((gid, slot), 0.0)
                            outgoing.append((dest, base * factor, gid, slot))
                        for dest, sensor, motor in self.bridges.get(gid, ()):
                            outgoing.append((dest, 1.25 * self.gain.get(
                                sensor + ":" + motor, 1.0), -1, -2))
            if len(outgoing) > self.max_events:
                raise RuntimeError("outgoing event budget exceeded")
            self.pending = outgoing
            self.neural_ticks = now
            if self.learning and now % 256 == 0:
                self._prune_expired_traces(now)
            if sum(len(s) for s in self.hot.values()) + sum(len(s) for s in self.cold.values()) > self.max_tracked:
                raise RuntimeError("tracked neuron state budget exceeded")
        self.last_delivery_sample = delivered_sample
        directly_driven_pages = {gid // PAGE_SIZE for gid in directly_driven}
        spiking_pages = {gid // PAGE_SIZE for gid in unique_spikes}
        updated_pages = {gid // PAGE_SIZE for gid in unique_updated}
        extra_spiking = {gid for gid in unique_spikes
                         if gid // PAGE_SIZE not in directly_driven_pages}
        extra_updated = {gid for gid in unique_updated
                         if gid // PAGE_SIZE not in directly_driven_pages}
        scores = {a: counts[a] / WIDTH + 0.4 * self.q[a] for a in ACTIONS}
        scores["idle"] += .05
        chosen = max(ACTIONS, key=lambda a: scores[a])
        self.last_action = chosen
        self.last_sensors = [name for name, v in sensors.items() if v > 0]
        self.step_number += 1
        return {
            "schema": "mikoshi-hq500m-game-v1",
            "engine": "bitweave-cpu-exact-paged-r04",
            "step": self.step_number,
            "action": chosen,
            "motor_scores": {a: round(scores[a], 4) for a in ACTIONS},
            "motor_spikes": counts, "spikes": all_spikes,
            "neural_ticks": self.ticks,
            "virtual_neurons": VIRTUAL_NEURONS,
            "resident_neurons": self.neurons,
            "page_capacity_neurons": self.max_pages * PAGE_SIZE,
            "lab_max_pulses": self.lab_max_pulses,
            "resident_pages": len(self.hot),
            "cold_pages": len(self.cold),
            "pages_loaded": self.load_count - initial_loads,
            "pages_evicted": self.eviction_count - initial_evictions,
            "pages_contacted": len(contacted_pages),
            "unique_updated_neurons": len(unique_updated),
            "unique_membrane_integrated_neurons": len(integrated_neurons),
            "refractory_event_skips": refractory_skips,
            "unique_spiking_neurons": len(unique_spikes),
            "directly_driven_neurons": len(directly_driven),
            "unique_undriven_spiking_neurons": len(unique_spikes - directly_driven),
            # Identify true spread, not repeated spikes in the seeded page.
            "unique_spiking_outside_driven_pages": len(extra_spiking),
            "unique_updated_outside_driven_pages": len(extra_updated),
            "spiking_pages": len(spiking_pages),
            "spiking_outside_driven_pages": len(spiking_pages - directly_driven_pages),
            "updated_pages": len(updated_pages),
            "spikes_per_tick": spikes_by_tick,
            "undriven_spikes_per_tick": undriven_spikes_by_tick,
            "peak_spiking_in_one_tick": peak_spikes,
            "peak_updated_in_one_tick": peak_updates,
            "synapses_evaluated": evaluated,
            "synapses_delivered": delivery_count,
            "remote_synapses_delivered": remote_count,
            "pending_synapse_events": len(self.pending),
            "nonresident_synapse_events_dropped": 0,
            "learned_c5_edges": len(self.plastic),
            "plasticity_updates": self.plasticity_updates,
            "synthetic_fanout": False,
            "c5_kernel": self.c5_kernel,
            "event_kernel": self.event_kernel,
            "lif_kernel": self.lif_kernel,
            "native_lif_input_cells": native_lif_cells,
            "native_lif_integrations": native_lif_integrations,
            "native_lif_page_batches": native_lif_pages,
            "lif_threshold": self.threshold,
            "plasticity_scope": self.plasticity_scope,
            "source": "synthetic_neural_ports",
            "motor_mapping": "toy-functional",
            **({"watched_spike_ticks": watched_spikes} if watched else {}),
        }

    @staticmethod
    def _encode_pages(pages):
        return [[pg, [[gid, *state] for gid, state in sorted(cells.items())]]
                for pg, cells in pages.items()]

    def snapshot(self):
        return {
            "schema": FORMAT, "max_pages": self.max_pages,
            "lab_max_pulses": self.lab_max_pulses,
            "ticks": self.ticks, "learning": self.learning,
            "threshold": self.threshold, "plasticity_scope": self.plasticity_scope,
            "virtual_neurons": VIRTUAL_NEURONS,
            "step_number": self.step_number, "neural_ticks": self.neural_ticks,
            "load_count": self.load_count,
            "eviction_count": self.eviction_count,
            "plasticity_updates": self.plasticity_updates,
            "q": self.q, "gain": self.gain, "last_action": self.last_action,
            "last_sensors": self.last_sensors,
            "hot": self._encode_pages(self.hot),
            "cold": self._encode_pages(self.cold),
            "pending": [list(event) for event in self.pending],
            "plastic": [[src, slot, delta]
                        for (src, slot), delta in sorted(self.plastic.items())],
            "pre_trace": [[dst, entries] for dst, entries in sorted(self.pre_trace.items())],
            "last_post": [[dst, t] for dst, t in sorted(self.last_post.items())],
        }

    def restore(self, s):
        if not isinstance(s, dict) or any((
            s.get("schema") != FORMAT,
            s.get("max_pages") != self.max_pages,
            s.get("lab_max_pulses", 8192) != self.lab_max_pulses,
            s.get("ticks") != self.ticks,
            s.get("learning") != self.learning,
            # Historical R02/R03 checkpoints omitted threshold: they are 1.0.
            s.get("threshold", 1.0) != self.threshold,
            s.get("plasticity_scope", "remote") != self.plasticity_scope,
            s.get("virtual_neurons") != VIRTUAL_NEURONS,
        )):
            raise ValueError("incompatible checkpoint")
        for field in ("step_number", "neural_ticks", "load_count",
                      "eviction_count", "plasticity_updates"):
            if type(s.get(field)) is not int or not 0 <= s[field] <= 10**12:
                raise ValueError("invalid checkpoint counter")
        if not isinstance(s.get("q"), dict) or set(s["q"]) != set(ACTIONS):
            raise ValueError("invalid policy")
        for x in s["q"].values():
            if type(x) not in (float, int) or not math.isfinite(x) or abs(x) > 2:
                raise ValueError("invalid policy value")
        if not isinstance(s.get("gain"), dict):
            raise ValueError("invalid bridge weights")
        for k, v in s["gain"].items():
            parts = k.split(":")
            if (len(parts) != 2 or parts[0] not in BRIDGES or
                parts[1] not in BRIDGES[parts[0]] or
                type(v) not in (int, float) or not math.isfinite(v) or
                not 0.55 <= v <= 1.5):
                raise ValueError("invalid bridge weight")
        if s.get("last_action") is not None and s["last_action"] not in ACTIONS:
            raise ValueError("invalid last action")
        if not isinstance(s.get("last_sensors"), list) or any(
            x not in INPUT_PORTS for x in s["last_sensors"]
        ):
            raise ValueError("invalid last sensors")
        def decode(pages):
            if not isinstance(pages, list):
                raise ValueError("invalid pages")
            out = OrderedDict()
            for p, rows in pages:
                if type(p) is not int or not 0 <= p <= (VIRTUAL_NEURONS-1)//PAGE_SIZE or p in out:
                    raise ValueError("invalid page ID")
                cells = {}
                for gid, v, prev, fired in rows:
                    if (type(gid) is not int or gid//PAGE_SIZE != p or gid in cells or
                        type(v) not in (float, int) or not math.isfinite(v) or
                        not -2 <= v <= 1 or type(prev) is not int or
                        not -1 <= prev <= s["neural_ticks"] or
                        type(fired) is not int or not -100 <= fired <= s["neural_ticks"]):
                        raise ValueError("invalid cell")
                    cells[gid] = (v, prev, fired)
                out[p] = cells
            return out
        hot = decode(s.get("hot"))
        cold = decode(s.get("cold"))
        if (not self.pinned.issubset(hot) or set(hot) & set(cold) or
            len(hot) > self.max_pages or
            sum(len(v) for v in hot.values()) + sum(len(v) for v in cold.values()) > MAX_TRACKED):
            raise ValueError("invalid page residency")
        pending = []
        for event in s.get("pending", []):
            if not isinstance(event, list) or len(event) != 4:
                raise ValueError("invalid event")
            dest, amp, src, slot = event
            if (type(dest) is not int or not 0 <= dest < VIRTUAL_NEURONS or
                type(amp) not in (float, int) or not math.isfinite(amp) or
                abs(amp) > 100 or type(src) is not int or
                (src != -1 and not 0 <= src < VIRTUAL_NEURONS) or
                type(slot) is not int or not -2 <= slot < 32):
                raise ValueError("invalid event")
            pending.append(tuple(event))
        if len(pending) > self.max_events:
            raise ValueError("checkpoint event overflow")
        plastic = {}
        for src, slot, delta in s.get("plastic", []):
            if (type(src) is not int or not 0 <= src < VIRTUAL_NEURONS or
                type(slot) is not int or not
                (24 <= slot < 32 if self.plasticity_scope == "remote" else 0 <= slot < 32) or
                type(delta) not in (float, int) or not math.isfinite(delta) or
                not -.7 <= delta <= .8):
                raise ValueError("invalid plastic map")
            plastic[(src, slot)] = delta
        pre_trace = {}
        for dst, entries in s.get("pre_trace", []):
            if type(dst) is not int or not 0 <= dst < VIRTUAL_NEURONS:
                raise ValueError("invalid pre-trace destination")
            validated = []
            for src, slot, t in entries:
                if (type(src) is not int or not 0 <= src < VIRTUAL_NEURONS or
                    type(slot) is not int or not
                    (24 <= slot < 32 if self.plasticity_scope == "remote" else 0 <= slot < 32) or
                    type(t) is not int or not 0 <= t <= s["neural_ticks"]):
                    raise ValueError("invalid pre-trace")
                validated.append((src, slot, t))
            pre_trace[dst] = validated
        last_post = {}
        for dst, t in s.get("last_post", []):
            if (type(dst) is not int or not 0 <= dst < VIRTUAL_NEURONS or
                type(t) is not int or not 0 <= t <= s["neural_ticks"]):
                raise ValueError("invalid post trace")
            last_post[dst] = t
        # Commit to instance only after successful full validation.
        self.hot, self.cold = hot, cold
        self.pending = pending
        self.plastic, self.pre_trace, self.last_post = plastic, pre_trace, last_post
        self.q, self.gain = dict(s["q"]), dict(s["gain"])
        self.last_action, self.last_sensors = s["last_action"], list(s["last_sensors"])
        for field in ("step_number", "neural_ticks", "load_count",
                      "eviction_count", "plasticity_updates"):
            setattr(self, field, s[field])
        self.last_delivery_sample = []

    def save(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        try:
            with temp.open("w", encoding="utf-8") as f:
                json.dump(self.snapshot(), f, separators=(",", ":"), allow_nan=False)
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)

    def load(self, path):
        target = Path(path)
        if target.stat().st_size > 128*1024*1024:
            raise ValueError("checkpoint too large")
        self.restore(json.loads(target.read_text(encoding="utf-8")))
