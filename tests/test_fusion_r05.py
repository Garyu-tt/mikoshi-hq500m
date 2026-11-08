"""Fusion R05: native C5 optional kernel must match original CPU C5 exactly."""
import random
import unittest

from hq500m import PagedBrain
from hq500m.c5_fast import source_edges
from hq500m.native_c5 import NativeC5, NativeUnavailable, LIB_PATH


class NativeC5Tests(unittest.TestCase):
    def test_native_backend_initialization_and_validation(self):
        self.assertEqual(PagedBrain(max_pages=8).c5_kernel, "python")
        with self.assertRaises(ValueError):
            PagedBrain(kernel="invented")
        if LIB_PATH.exists():
            self.assertEqual(PagedBrain(kernel="native").c5_kernel, "native-c99")
            self.assertEqual(PagedBrain(kernel="auto").c5_kernel, "native-c99")
        else:
            self.assertEqual(PagedBrain(kernel="auto").c5_kernel, "python")
            with self.assertRaises(NativeUnavailable):
                PagedBrain(kernel="native")

    def test_optional_native_edges_match_raw_32_links_exact(self):
        if not LIB_PATH.exists():
            self.skipTest("native shared library absent (run sh hq500m/native/build.sh)")
        c = NativeC5()
        rng = random.Random(20261108)
        boundary = [0, 1023, 1024, 224999423, 224999424, 294999039,
                    294999040, 344999935, 344999936, 394999807,
                    394999808, 434999295, 434999296, 469999615,
                    469999616, 499999999]
        ids = boundary + [rng.randrange(500_000_000) for _ in range(2048)]
        targets, weights = c.batch(ids)
        self.assertEqual(len(targets), len(ids)*32)
        for i, src in enumerate(ids):
            for slot, (dst, weight) in enumerate(source_edges(src)):
                self.assertEqual(dst, targets[i*32+slot])
                self.assertEqual(weight, weights[i*32+slot]*.000035)
        with self.assertRaises(ValueError):
            c.batch([-1])
        with self.assertRaises(ValueError):
            c.batch([500_000_000])
        with self.assertRaises(ValueError):
            c.batch([True])
        with self.assertRaises(ValueError):
            c.batch([0]*8193)
        self.assertEqual(c.batch([]), ((), ()))

    def test_native_python_end_to_end_parity_with_plasticity(self):
        if not LIB_PATH.exists():
            self.skipTest("native shared library absent")
        inputs = [
            ({}, {1_048_576 + i: 2.0 for i in range(256)}),
            ({}, {}),
            ({"food": .9}, {469_999_616 + i: 2.0 for i in range(128)}),
            ({"threat": .6, "reward": .25}, {}),
            ({}, {499_999_999: 2.0}),
            ({}, {}),
        ]
        for learning in (False, True):
            for threshold, scope in ((1., "remote"), (.35, "all_exc")):
                with self.subTest(learning=learning, threshold=threshold):
                    brains = [
                        PagedBrain(max_pages=8, ticks=4, learning=learning,
                                   threshold=threshold, plasticity_scope=scope,
                                   kernel=k)
                        for k in ("python", "native")
                    ]
                    for observation, pulses in inputs:
                        a = brains[0].step(observation, pulses, watch_ids=[1_048_577])
                        b = brains[1].step(observation, pulses, watch_ids=[1_048_577])
                        a.pop("c5_kernel"); b.pop("c5_kernel")
                        self.assertEqual(a, b)
                    self.assertEqual(brains[0].snapshot(), brains[1].snapshot())
                    # Cross-kernel checkpoint loading is okay: the stored
                    # network state is backend independent.
                    recovered = PagedBrain(max_pages=8, ticks=4,
                        learning=learning, threshold=threshold,
                        plasticity_scope=scope, kernel="native")
                    recovered.restore(brains[0].snapshot())
                    self.assertEqual(recovered.snapshot(), brains[1].snapshot())


if __name__ == "__main__":
    unittest.main()
