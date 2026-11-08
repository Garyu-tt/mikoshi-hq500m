"""Fusion R02: exact global IDs, page churn, learning and checkpoint regression."""
import json
from pathlib import Path
import tempfile
import unittest

from hq500m import PagedBrain
from hq500m.core import edge, VIRTUAL_NEURONS


def positive_projection(source):
    for slot in range(24, 32):
        dst, strength, _, _ = edge(source, slot)
        if strength > 0:
            return slot, dst
    raise AssertionError("no positive remote projection")


class PagedBrainTests(unittest.TestCase):
    def test_lazy_capacity_is_not_fake_activity(self):
        b = PagedBrain(max_pages=1024, ticks=2, learning=False)
        self.assertEqual(b.neurons, 7168)
        r = b.step({})
        self.assertEqual(r["page_capacity_neurons"], 1_048_576)
        self.assertEqual(r["resident_neurons"], 7168)
        self.assertEqual(r["unique_updated_neurons"], 0)
        self.assertEqual(r["unique_spiking_neurons"], 0)
        self.assertEqual(r["synthetic_fanout"], False)
        self.assertEqual(r["nonresident_synapse_events_dropped"], 0)

    def test_global_projection_delivered_unaliased(self):
        src = 1_048_577
        slot, dst = positive_projection(src)
        self.assertNotEqual(src // 1024, dst // 1024)
        b = PagedBrain(max_pages=8, ticks=2, learning=False)
        r = b.step({}, {src: 2.0})
        self.assertEqual(r["synapses_evaluated"], 32)
        self.assertEqual(r["synapses_delivered"], 32)
        self.assertEqual(r["remote_synapses_delivered"], 8)
        self.assertIn((src, slot, dst), b.last_delivery_sample)
        self.assertGreater(r["pages_loaded"], 0)
        self.assertIn(dst, b.hot.get(dst // 1024, b.cold.get(dst // 1024, {})))
        self.assertGreaterEqual(r["pages_evicted"], 1)
        self.assertEqual(r["nonresident_synapse_events_dropped"], 0)
        self.assertEqual(r["pending_synapse_events"], 0)

    def test_exact_state_persists_across_evict_and_reload(self):
        b = PagedBrain(max_pages=8, ticks=1, learning=False)
        source = 1_048_577
        b.step({}, {source: 2})
        b.step({})  # C5 output delivered and many pages churn
        page = source // 1024
        self.assertIn(page, b.cold)  # all 7 port pages pinned
        self.assertIn(source, b.cold[page])
        value = b.cold[page][source]
        b._touch(source)
        self.assertIn(source, b.hot[page])
        self.assertEqual(b.hot[page][source], value)

    def test_true_projected_plasticity_control(self):
        src = 1_048_577
        slot, dst = positive_projection(src)
        train = PagedBrain(max_pages=16, ticks=1, learning=True)
        sham = PagedBrain(max_pages=16, ticks=1, learning=False)
        for brain in (train, sham):
            brain.step({}, {src: 2.0})
            brain.step({}, {dst: 2.0})
        self.assertGreater(train.plastic.get((src, slot), 0.0), 0.0)
        self.assertGreater(train.plasticity_updates, 0)
        self.assertEqual(sham.plastic, {})
        self.assertEqual(sham.plasticity_updates, 0)

    def test_checkpoint_replays_cross_region_queues(self):
        seq = [
            ({"food": 0.8}, {1_048_577: 2.0}),
            ({"threat": 0.6, "reward": 0.2}, {2_011_457: 2.0}),
            ({"novelty": 0.7}, {}),
            ({"obstacle_left": 0.8, "reward": -0.4}, {}),
            ({}, {1_048_577: 2.0}),
        ]
        a = PagedBrain(max_pages=8, ticks=2)
        for obs, pulses in seq[:2]:
            a.step(obs, pulses)
        with tempfile.TemporaryDirectory() as td:
            fn = Path(td)/"ckpt.json"
            a.save(fn)
            b = PagedBrain(max_pages=8, ticks=2)
            b.load(fn)
            for obs, pulses in seq[2:]:
                ra, rb = a.step(obs, pulses), b.step(obs, pulses)
                self.assertEqual(ra, rb)
            self.assertEqual(a.snapshot(), b.snapshot())
            with self.assertRaises(ValueError):
                PagedBrain(max_pages=16, ticks=2).load(fn)
            tampered = json.loads(fn.read_text())
            tampered["hot"][0][1].append([500_000_000, 0, 0, 0])
            with self.assertRaises(ValueError):
                b.restore(tampered)

    def test_validation_and_extreme_ids(self):
        b = PagedBrain(max_pages=8, ticks=2)
        for invalid in (True, -1, 500_000_000, 3.3):
            with self.assertRaises(ValueError):
                b.step({}, {invalid: 3})
        with self.assertRaises(ValueError):
            b.step({}, {1_048_577: float("nan")})
        with self.assertRaises(ValueError):
            b.step({}, {1_048_577: 101})
        result = b.step({}, {499_999_999: 2})
        self.assertEqual(result["virtual_neurons"], VIRTUAL_NEURONS)
        self.assertGreater(result["synapses_evaluated"], 0)


if __name__ == "__main__":
    unittest.main()
