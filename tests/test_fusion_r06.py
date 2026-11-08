"""Fusion R06: exact native event reduction and dense-page lazy LIF.

Prove parity against the unchanged Python engine (incl. learning, pages,
network spike timing and checkpoint resume), not only microbench kernels.
"""
import math
import random
import unittest

from hq500m import PagedBrain
from hq500m.native_c5 import NativeC5, LIB_PATH


class FusionR06Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not LIB_PATH.is_file():
            raise unittest.SkipTest("optional native C99 library not built")
        cls.native = NativeC5()

    def test_exact_sorted_event_reduction_floating_point_order(self):
        rng = random.Random(20261108)
        ev = [(rng.randrange(0, 100), rng.choice([1e-14, 0.12, -0.12, 0.9]),
               rng.randrange(20), rng.randrange(32)) for _ in range(20000)]
        ev.extend([
            (250, 1e20, 1, 1),
            (250, 1.0, 1, 2),
            (250, -1e20, 1, 3),
            (251, 0.0, 1, 1),
            (251, -0.0, 1, 2),
        ])
        ev.sort(key=lambda e: (e[0], e[2], e[3]))
        reference = {}
        for dst, current, src, slot in ev:
            reference[dst] = reference.get(dst, 0.0) + current
        self.assertEqual(self.native.reduce_sorted(ev), reference)
        self.assertEqual(self.native.reduce_sorted([]), {})
        with self.assertRaises(ValueError):
            self.native.reduce_sorted([(2, 1., 1, 0), (1, 1., 1, 0)])
        with self.assertRaises(ValueError):
            self.native.reduce_sorted([(500000000, 1., 1, 0)])

    def test_native_lif_exact_state_refractory_decay_and_threshold(self):
        rng = random.Random(1118)
        for threshold in (.25, .35, 1.0, 1.7):
            rows = []
            for _ in range(1200):
                fired_at = rng.choice([-100, -1, 10, 98, 99, 100])
                previous = rng.choice([-1, 10, 40, 99])
                rows.append((rng.uniform(-2, 1), previous, fired_at,
                             rng.uniform(-1, 2)))
            out = self.native.lif_rows(rows, 100, threshold)
            self.assertEqual(len(out), len(rows))
            for (voltage, prev, last_fire, current), result in zip(rows, out):
                if 100 - last_fire <= 2:
                    expected = (voltage, prev, last_fire, False)
                else:
                    voltage = voltage * (0.68 ** (100 - prev)) + current
                    if voltage >= threshold:
                        expected = (0., 100, 100, True)
                    else:
                        expected = (max(-2., min(1., voltage)), 100,
                                    last_fire, False)
                self.assertEqual(expected, result)
        with self.assertRaises(ValueError):
            self.native.lif_rows([(0., 101, -100, .1)], 100, 1.0)
        with self.assertRaises(ValueError):
            self.native.lif_rows([(0., 0, -100, .1)], 100, float("nan"))

    def test_dense_and_sparse_network_exact_parity_with_checkpoint(self):
        series = [
            ({}, {1_048_576 + i: 2. for i in range(512)}),
            ({}, {}),
            ({"food": .9}, {}),
            ({"threat": .6, "reward": .25}, {469_999_616 + i: 2. for i in range(256)}),
            ({}, {}),
            ({"novelty": .8}, {499_999_999: 2.}),
        ]
        strip = {"event_kernel", "lif_kernel",
                 "native_lif_input_cells", "native_lif_integrations", "native_lif_page_batches"}
        for learning, threshold, scope in ((False, 1., "remote"),
                                           (True, 1., "all_exc"),
                                           (True, .35, "all_exc")):
            for event, lif in (("native", "python"), ("python", "native"),
                               ("native", "native")):
                with self.subTest(learning=learning, threshold=threshold,
                                  event=event, lif=lif):
                    a = PagedBrain(max_pages=8, ticks=5, learning=learning,
                                  threshold=threshold, plasticity_scope=scope,
                                  kernel="native")
                    b = PagedBrain(max_pages=8, ticks=5, learning=learning,
                                  threshold=threshold, plasticity_scope=scope,
                                  kernel="native", event_kernel=event,
                                  lif_kernel=lif)
                    total_native = 0
                    for obs, pulses in series:
                        ra = a.step(obs, pulses, watch_ids=[1048576, 1049200])
                        rb = b.step(obs, pulses, watch_ids=[1048576, 1049200])
                        total_native += rb["native_lif_input_cells"]
                        self.assertEqual({k:v for k,v in ra.items() if k not in strip},
                                         {k:v for k,v in rb.items() if k not in strip})
                    self.assertEqual(a.snapshot(), b.snapshot())
                    if lif == "native":
                        self.assertGreater(total_native, 0)
                    c = PagedBrain(max_pages=8, ticks=5, learning=learning,
                                  threshold=threshold, plasticity_scope=scope,
                                  kernel="native", event_kernel=event,
                                  lif_kernel=lif)
                    c.restore(a.snapshot())
                    self.assertEqual(c.snapshot(), b.snapshot())

    def test_explicit_large_lab_budget_and_accounting(self):
        with self.assertRaises(ValueError):
            PagedBrain(lab_max_pulses=12345)
        b = PagedBrain(max_pages=8, ticks=1, learning=False)
        extra = {1_000_000 + i: 2. for i in range(8193)}
        with self.assertRaises(ValueError):
            b._validate_pulses(extra)
        large = PagedBrain(max_pages=8, ticks=1, learning=False,
                           lab_max_pulses=32768)
        self.assertEqual(len(large._validate_pulses(extra)), 8193)
        self.assertEqual(large.snapshot()["lab_max_pulses"], 32768)
        with self.assertRaises(ValueError):
            b.restore(large.snapshot())
        # "received current" is distinct from actually integrating a
        # refractory neuron, a distinction that older reports lack.
        single = PagedBrain(ticks=1, learning=False)
        first = single.step({}, {1_048_576:2.})
        second = single.step({}, {1_048_576:2.})
        self.assertEqual(first["refractory_event_skips"], 0)
        self.assertGreater(second["refractory_event_skips"], 0)
        self.assertLess(second["unique_membrane_integrated_neurons"],
                        second["unique_updated_neurons"])
        self.assertLessEqual(second["unique_membrane_integrated_neurons"],
                             second["unique_updated_neurons"])

if __name__ == "__main__":
    unittest.main()
