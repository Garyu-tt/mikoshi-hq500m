"""Fusion R08 CPU-only dendritic temporal tail and checkpoint tests."""
import copy
import tempfile
import unittest
from pathlib import Path

from hq500m import PagedBrain


class DendriteTailTests(unittest.TestCase):
    TARGET, SOURCE = 2_000_000, 1_000_000

    def brain(self, tail=4, ticks=1):
        return PagedBrain(max_pages=8, ticks=ticks, learning=False,
                          dendrites=True, dendrite_tail_ticks=tail)

    def test_delayed_spike_without_new_input(self):
        b = self.brain()
        b.pending = [(self.TARGET, 1.48, self.SOURCE, 0)]
        first = b.step({}, watch_ids=[self.TARGET])
        self.assertEqual(first["watched_spike_ticks"][str(self.TARGET)], [])
        self.assertEqual(first["dendritic_active_tails"], 1)
        self.assertEqual(first["unique_updated_neurons"], 1)
        second = b.step({}, watch_ids=[self.TARGET])
        self.assertEqual(second["watched_spike_ticks"][str(self.TARGET)], [2])
        self.assertEqual(second["unique_updated_neurons"], 0)
        self.assertEqual(second["dendritic_wake_integrations"], 1)
        self.assertEqual(second["dendritic_silent_spikes"], 1)
        self.assertEqual(second["synapses_delivered"], 0)
        self.assertEqual(second["dendritic_active_tails"], 0)
        legacy = self.brain(tail=0)
        legacy.pending = [(self.TARGET, 1.48, self.SOURCE, 0)]
        legacy.step({})
        self.assertEqual(legacy.step({})["spikes"], 0)

    def test_wake_expires_without_new_event(self):
        b = self.brain(tail=2)
        b.pending = [(self.TARGET, -0.4, self.SOURCE, 8)]
        b.step({})
        self.assertEqual(len(b.dendritic_wake), 1)
        b.step({})
        self.assertEqual(len(b.dendritic_wake), 1)
        b.step({})
        self.assertEqual(len(b.dendritic_wake), 0)
        self.assertEqual(b.step({})["dendritic_wake_integrations"], 0)

    def test_checkpoint_replay_and_mode_guard(self):
        b = self.brain()
        b.pending = [(self.TARGET, 1.48, self.SOURCE, 0)]
        b.step({})
        snap = b.snapshot()
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / "wake.json"
            b.save(file)
            other = self.brain()
            other.load(file)
            self.assertEqual(other.snapshot(), snap)
            for _ in range(4):
                self.assertEqual(b.step({}), other.step({}))
                self.assertEqual(b.snapshot(), other.snapshot())
            with self.assertRaises(ValueError):
                self.brain(tail=0).load(file)
        with self.assertRaises(ValueError):
            self.brain(tail=0).restore(snap)

    def test_tampering_fails_atomically(self):
        b = self.brain()
        b.pending = [(self.TARGET, 1.48, self.SOURCE, 0)]
        b.step({})
        old = b.snapshot()
        for bad in (
            [[self.TARGET, -3]],
            [[self.TARGET, b.neural_ticks + 50]],
            [[self.TARGET, b.neural_ticks + 3], [self.TARGET, b.neural_ticks + 4]],
            [[123456789, b.neural_ticks + 3]],
            ["oops"]
        ):
            changed = copy.deepcopy(old)
            changed["dendritic_wake"] = bad
            with self.assertRaises(ValueError):
                b.restore(changed)
            self.assertEqual(b.snapshot(), old)

    def test_guardrails_and_empty_step(self):
        for kwargs in ({"dendrites": False, "dendrite_tail_ticks": 2},
                       {"dendrites": True, "dendrite_tail_ticks": -1},
                       {"dendrites": True, "dendrite_tail_ticks": 9},
                       {"dendrites": True, "dendrite_tail_ticks": True},
                       {"dendrites": True, "dendrite_tail_ticks": 1,
                        "lif_kernel": "native"}):
            with self.assertRaises(ValueError):
                PagedBrain(**kwargs)
        b = self.brain()
        idle = b.step({})
        self.assertEqual(idle["dendritic_active_tails"], 0)
        self.assertEqual(idle["unique_membrane_integrated_neurons"], 0)
        self.assertEqual(len(b.dendritic_wake), 0)
        self.assertEqual(b.neurons, 7168)

    def test_exact_global_c5_propagation(self):
        b = self.brain(ticks=3)
        pulse = b.step({}, {1048577: 2.0})
        self.assertEqual(pulse["synapses_delivered"], 32)
        self.assertEqual(pulse["remote_synapses_delivered"], 8)
        self.assertEqual(pulse["nonresident_synapse_events_dropped"], 0)
        self.assertGreater(pulse["dendritic_wake_integrations"], 0)


if __name__ == "__main__":
    unittest.main()
