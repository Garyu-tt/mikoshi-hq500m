"""Fusion R03: fused exact C5 generator, native-network propagation, honest metrics."""
import random
import unittest

from hq500m import PagedBrain
from hq500m.c5_fast import source_edges
from hq500m.core import edge, VIRTUAL_NEURONS


class FusionR03Tests(unittest.TestCase):
    def test_fused_c5_matches_reference_all_slots_and_boundaries(self):
        boundary_ids = [0, 1023, 1024, 224999423, 224999424,
            294999039, 294999040, 344999935, 344999936,
            394999807, 394999808, 434999295, 434999296,
            469999615, 469999616, 499999744, 499999999]
        rng = random.Random(20261108)
        for gid in boundary_ids + [rng.randrange(VIRTUAL_NEURONS)
                                   for _ in range(300)]:
            actual = source_edges(gid)
            self.assertEqual(len(actual), 32)
            for slot, (dst, current) in enumerate(actual):
                expected = edge(gid, slot)
                self.assertEqual(dst, expected[0])
                self.assertEqual(current, expected[1] * .000035)
        with self.assertRaises(ValueError):
            source_edges(VIRTUAL_NEURONS)

    def test_last_virtual_page_has_only_256_valid_neurons(self):
        b = PagedBrain(max_pages=8, ticks=1, learning=False)
        last = VIRTUAL_NEURONS - 1
        initial = b.neurons
        b._touch(last)
        self.assertEqual(b.neurons, initial + (VIRTUAL_NEURONS % 1024))
        self.assertEqual(b.hot[last//1024], {})
        b.step({}, {last: 2.0})
        self.assertEqual(b.step({}, {})["nonresident_synapse_events_dropped"], 0)

    def test_intrinsic_c5_propagation_nonforced_without_broadcast(self):
        # Stimulus is applied at tick 1 only, to 512 original C5 source IDs.
        # Subsequent ticks have no external sensory drive or fanout.
        for base in (1_048_576, 1_049_600, 1_050_624, 2_011_136):
            b = PagedBrain(max_pages=128, ticks=24, learning=False)
            obs = b.step({}, {base + i: 2.0 for i in range(512)})
            self.assertFalse(obs["synthetic_fanout"])
            self.assertEqual(obs["directly_driven_neurons"], 512)
            self.assertEqual(obs["spikes_per_tick"][0], 512)
            self.assertGreater(obs["unique_undriven_spiking_neurons"], 0)
            self.assertEqual(obs["spikes"], sum(obs["spikes_per_tick"]))
            self.assertGreater(obs["spikes_per_tick"][1], 0)
            self.assertEqual(obs["spikes_per_tick"][-1], 0)
            self.assertEqual(obs["remote_synapses_delivered"] > 0, True)
            self.assertEqual(obs["nonresident_synapse_events_dropped"], 0)
            # No learning without reward or plasticity.
            self.assertEqual(obs["learned_c5_edges"], 0)

    def test_per_tick_counters_unchanged_across_resume(self):
        pulse = {1_048_576 + i: 2.0 for i in range(256)}
        b = PagedBrain(max_pages=128, ticks=6, learning=False)
        r = b.step({}, pulse)
        self.assertEqual(len(r["spikes_per_tick"]), 6)
        self.assertEqual(r["directly_driven_neurons"], 256)
        self.assertGreaterEqual(r["unique_spiking_neurons"], 256)
        self.assertGreaterEqual(r["unique_undriven_spiking_neurons"], 0)
        self.assertEqual(len(r["undriven_spikes_per_tick"]), 6)
        self.assertLessEqual(r["unique_undriven_spiking_neurons"],
                             sum(r["undriven_spikes_per_tick"]))
        s = b.snapshot()
        clone = PagedBrain(max_pages=128, ticks=6, learning=False)
        clone.restore(s)
        self.assertEqual(b.step({}, {499999999: 2}),
                         clone.step({}, {499999999: 2}))


if __name__ == "__main__":
    unittest.main()
