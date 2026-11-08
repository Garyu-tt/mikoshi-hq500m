"""Fusion R04 controls: persistent C5 reverberation and associative plasticity.

Deterministic micro-assays on synthetic neurons only. No claim of general
intelligence, biological learning, or all 500M neurons being resident.
"""
import json
import unittest

from hq500m import PagedBrain
from hq500m.core import VIRTUAL_NEURONS
from hq500m.c5_fast import source_edges


class FusionR04Tests(unittest.TestCase):
    def test_excitability_validation_and_backward_compatible_checkpoint(self):
        for bad in (float("nan"), float("inf"), 0.0, 0.2, 2.5, True, "1.0"):
            with self.subTest(threshold=bad):
                with self.assertRaises(ValueError):
                    PagedBrain(threshold=bad)
        with self.assertRaises(ValueError):
            PagedBrain(plasticity_scope="all")
        b = PagedBrain(ticks=2, learning=True)
        b.step({}, {1_048_577: 2})
        older = json.loads(json.dumps(b.snapshot()))
        older.pop("threshold")
        older.pop("plasticity_scope")
        restored = PagedBrain(ticks=2, learning=True)
        restored.restore(older)
        self.assertEqual(b.step({}, {}), restored.step({}, {}))
        with self.assertRaises(ValueError):
            PagedBrain(ticks=2, threshold=0.35).restore(older)
        with self.assertRaises(ValueError):
            PagedBrain(ticks=2, plasticity_scope="all_exc").restore(older)

    def test_native_reverberation_vs_silent_and_normal_threshold(self):
        base = 469_999_616
        pulse = {base+i: 2.0 for i in range(512)}
        normal = PagedBrain(max_pages=128, ticks=24, learning=False)
        enhanced = PagedBrain(max_pages=128, ticks=24, learning=False,
                              threshold=0.25)
        normal_trace = normal.step({}, pulse)
        enhanced_trace = enhanced.step({}, pulse)
        self.assertEqual(normal_trace["spikes_per_tick"][-1], 0)
        self.assertGreater(enhanced_trace["spikes_per_tick"][-1], 0)
        self.assertGreater(enhanced_trace["unique_spiking_outside_driven_pages"], 1000)
        self.assertGreater(enhanced_trace["spiking_outside_driven_pages"], 100)
        self.assertEqual(enhanced_trace["nonresident_synapse_events_dropped"], 0)
        # No external signal means no spontaneous firing from rest.
        silence = PagedBrain(max_pages=128, ticks=24, learning=False,
                             threshold=0.25).step({})
        self.assertEqual(silence["spikes"], 0)
        self.assertEqual(silence["spiking_pages"], 0)
        # Later steps are truly without new pulses.
        later = enhanced.step({})
        self.assertGreater(later["spikes_per_tick"][-1], 0)
        self.assertEqual(later["directly_driven_neurons"], 0)
        self.assertEqual(later["nonresident_synapse_events_dropped"], 0)

    def test_local_c5_association_requires_pairing_and_plasticity(self):
        base, target = 1_048_576, 1_049_306
        cue = {base+i:2.0 for i in range(128)}
        observations = {}
        for name in ("paired", "learning_disabled", "remote_only", "cue_only"):
            b = PagedBrain(max_pages=128, ticks=1,
                           learning=name != "learning_disabled",
                           threshold=1.0,
                           plasticity_scope="remote" if name == "remote_only"
                                                     else "all_exc")
            b.step({}, cue)
            before = b.step({}, watch_ids=[target])
            self.assertEqual(before["watched_spike_ticks"][str(target)], [])
            for _ in range(16):
                b.step({})
            for _ in range(25):
                b.step({}, cue)
                b.step({}, {target:2.0} if name not in ("cue_only",) else {})
                for _ in range(16):
                    b.step({})
            checkpoint = json.loads(json.dumps(b.snapshot()))
            clone = PagedBrain(max_pages=128, ticks=1,
                               learning=b.learning, threshold=b.threshold,
                               plasticity_scope=b.plasticity_scope)
            clone.restore(checkpoint)
            clone.step({}, cue)
            after = clone.step({}, watch_ids=[target])
            observations[name] = bool(after["watched_spike_ticks"][str(target)])
            self.assertEqual(clone.plastic, b.plastic if name == "learning_disabled"
                             else clone.plastic)
            if name == "paired":
                self.assertTrue(any(slot < 24 and delta > 0
                                    for (gid, slot), delta in b.plastic.items()))
                for _ in range(256):
                    b.step({})
                b.step({}, cue)
                retention = b.step({}, watch_ids=[target])
                self.assertTrue(retention["watched_spike_ticks"][str(target)])
        self.assertEqual(observations, {
            "paired": True,
            "learning_disabled": False,
            "remote_only": False,
            "cue_only": False,
        })

    def test_traces_expire_and_watch_ids_validate(self):
        b = PagedBrain(max_pages=8, ticks=1, learning=True,
                       plasticity_scope="all_exc")
        b.neural_ticks = 255
        b.pre_trace[1049306] = [(1048576, 0, 1)]
        b.last_post[1049306] = 1
        b.step({})
        self.assertNotIn(1049306, b.pre_trace)
        self.assertNotIn(1049306, b.last_post)
        for bad in ([-1], [VIRTUAL_NEURONS], [True], [2.0], list(range(65))):
            with self.assertRaises(ValueError):
                b.step({}, watch_ids=bad)
        valid = b.step({}, {1048576:2.0}, watch_ids=[1048576])
        self.assertEqual(valid["watched_spike_ticks"]["1048576"], [257])


if __name__ == "__main__":
    unittest.main()
