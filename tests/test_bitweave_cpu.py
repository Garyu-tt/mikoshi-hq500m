"""Cross-engine parity and expanded-activity tests for optional CPU BitWeave."""
import json
from pathlib import Path
import tempfile
import unittest

from hq500m import Brain, BitWeaveBrain
from hq500m.core import edge, VIRTUAL_NEURONS


class BitWeaveTests(unittest.TestCase):
    def test_virtual_address_and_exact_edges(self):
        self.assertEqual(VIRTUAL_NEURONS, 500_000_000)
        b = BitWeaveBrain(pages=16, ticks=2, fanout=0)
        self.assertEqual(b.neurons, 114_688)
        for r in range(7):
            node = b._global(r * b.cells + 1234)
            self.assertEqual(b._local(node), r * b.cells + 1234)
        self.assertEqual(edge(499_999_999, 31)[0] < VIRTUAL_NEURONS, True)

    def test_match_legacy_without_synthetic_broadcast(self):
        old = Brain(cells=1024, ticks=6, learning=True)
        new = BitWeaveBrain(pages=1, ticks=6, fanout=0, learning=True)
        probes = (
            {"food": .9}, {"threat": .9, "reward": .3},
            {"obstacle_left": .8, "reward": -.4},
            {"eye_right": 1.}, {}, {"food": .9}, {}, {"novelty": .9},
        )
        for obs in probes:
            expected = old.step(obs)
            actual = new.step(obs)
            for key in ("action", "motor_spikes", "motor_scores", "spikes",
                        "plasticity_updates", "neural_ticks", "resident_neurons"):
                self.assertEqual(actual[key], expected[key], (key, obs, actual, expected))

    def test_expanded_dynamic_activity(self):
        b = BitWeaveBrain(pages=16, ticks=3, fanout=16)
        result = b.step({"food": .9})
        self.assertEqual(result["resident_neurons"], 114688)
        self.assertGreater(result["unique_spiking_neurons"], 1000)
        self.assertGreater(result["peak_spiking_in_one_tick"], 1000)
        self.assertGreater(result["synapses_evaluated"], 30000)
        self.assertEqual(result["action"], "interact")
        self.assertEqual(result["synapses_evaluated"], 32 * result["spikes"])
        self.assertEqual(result["synapses_delivered"] +
                         result["nonresident_synapse_events"],
                         result["synapses_evaluated"])
        self.assertEqual(result["synthetic_fanout"], True)
        self.assertLess(result["unique_spiking_neurons"], result["resident_neurons"])

    def test_checkpoint_replay(self):
        seq = ({"food": .9}, {"threat": .9, "reward": -.3},
               {"obstacle_left": .9}, {"novelty": .9, "reward": .4}, {})
        a = BitWeaveBrain(pages=4, ticks=4, fanout=8)
        for obs in seq[:2]:
            a.step(obs)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "state.json"
            a.save(f)
            b = BitWeaveBrain(pages=4, ticks=4, fanout=8)
            b.load(f)
            for obs in seq[2:]:
                self.assertEqual(a.step(obs), b.step(obs))
            self.assertEqual(a.snapshot(), b.snapshot())
            with self.assertRaises(ValueError):
                BitWeaveBrain(pages=2, ticks=4, fanout=8).load(f)

    def test_reject_large_all_sensor_fanout(self):
        b = BitWeaveBrain(pages=128, ticks=2, fanout=64)
        from hq500m.core import INPUT_PORTS
        with self.assertRaises(ValueError):
            b.step({key: 1. for key in INPUT_PORTS})

    def test_validation(self):
        for invalid in (0, 129, 1.0, True):
            with self.assertRaises(ValueError):
                BitWeaveBrain(pages=invalid)
        for invalid in (-1, 65, 1.0, True):
            with self.assertRaises(ValueError):
                BitWeaveBrain(fanout=invalid)


if __name__ == "__main__":
    unittest.main()
