"""R07 opt-in dendritic model: locality, replay, boundaries, compatibility."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from hq500m import PagedBrain
from hq500m.dendrites import INITIAL, branch_for_slot, integrate
from hq500m.__main__ import main
from hq500m.page_engine import MAX_TRACKED


class DendritesTests(unittest.TestCase):
    def test_mapping_and_supralinear_local_coincidence(self):
        self.assertEqual([branch_for_slot(x) for x in (0, 7, 8, 15, 16, 23, 24, 31)],
                         [0, 0, 1, 1, 2, 2, 3, 3])
        with self.assertRaises(ValueError):
            branch_for_slot(-1)
        with self.assertRaises(ValueError):
            branch_for_slot(True)
        close, close_fire = integrate(INITIAL, 1, 0.55, 0.0, [1.2, 0, 0, 0])
        separated, separate_fire = integrate(INITIAL, 1, 0.55, 0.0, [0.6, 0.6, 0, 0])
        self.assertTrue(close_fire)
        self.assertFalse(separate_fire)
        self.assertLess(separated[0], 0.55)
        self.assertEqual(close[3:], (0., 0., 0., 0.))

    def test_real_paged_input_uses_branch_not_total_only(self):
        target, source = 2_000_000, 1_000_000
        same = PagedBrain(max_pages=8, ticks=1, learning=False,
                          dendrites=True, threshold=0.55)
        split = PagedBrain(max_pages=8, ticks=1, learning=False,
                           dendrites=True, threshold=0.55)
        same.pending = [(target, 0.6, source, 0), (target, 0.6, source, 1)]
        split.pending = [(target, 0.6, source, 0), (target, 0.6, source, 8)]
        rs = same.step({}, watch_ids=[target])
        rd = split.step({}, watch_ids=[target])
        self.assertEqual(rs["watched_spike_ticks"][str(target)], [1])
        self.assertEqual(rd["watched_spike_ticks"][str(target)], [])
        self.assertEqual(rs["synapses_delivered"], rd["synapses_delivered"])
        self.assertEqual(rs["unique_updated_neurons"], 1)
        self.assertEqual(rd["unique_updated_neurons"], 1)

    def test_signed_inhibition_and_temporal_decay(self):
        a, spiked = integrate(INITIAL, 1, 1.4, 0, [1.0, 0, 0, 0])
        self.assertFalse(spiked)
        b, spiked = integrate(a, 3, 1.4, 0, [0, 0, 0, 0])
        self.assertFalse(spiked)
        self.assertLess(b[3], a[3])
        c, spiked = integrate(INITIAL, 1, 1.4, 0, [1., -1., 0, 0])
        self.assertFalse(spiked)
        self.assertLess(c[0], a[0])

    def test_paged_routing_and_checkpoint_replay(self):
        src = 1_048_577
        a = PagedBrain(max_pages=8, ticks=2, learning=False, dendrites=True)
        first = a.step({}, {src: 2}, watch_ids=[src])
        self.assertEqual(first["dendrite_branches"], 4)
        self.assertEqual(first["synapses_delivered"], 32)
        self.assertEqual(first["remote_synapses_delivered"], 8)
        self.assertEqual(first["nonresident_synapse_events_dropped"], 0)
        self.assertGreaterEqual(first["unique_membrane_integrated_neurons"], 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dendritic.json"
            a.save(path)
            self.assertTrue(json.loads(path.read_text())["dendrites"])
            b = PagedBrain(max_pages=8, ticks=2, learning=False, dendrites=True)
            b.load(path)
            self.assertEqual(a.snapshot(), b.snapshot())
            for obs, pulses in (({}, {src: 2}), ({"food": 0.7}, {}), ({}, {})):
                self.assertEqual(a.step(obs, pulses), b.step(obs, pulses))
            self.assertEqual(a.snapshot(), b.snapshot())
            with self.assertRaises(ValueError):
                PagedBrain(max_pages=8, ticks=2, learning=False).load(path)

    def test_legacy_checkpoint_unchanged(self):
        a = PagedBrain(max_pages=8, ticks=1, learning=False)
        a.step({"food": 0.6})
        snap = a.snapshot()
        self.assertNotIn("dendrites", snap)
        b = PagedBrain(max_pages=8, ticks=1, learning=False)
        b.restore(snap)
        self.assertEqual(a.snapshot(), b.snapshot())
        with self.assertRaises(ValueError):
            PagedBrain(max_pages=8, ticks=1, learning=False, dendrites=True).restore(snap)

    def test_corrupted_branch_state_rejected_atomically(self):
        a = PagedBrain(max_pages=8, ticks=1, learning=False, dendrites=True)
        a.step({}, {1_048_577: 2})
        saved = a.snapshot()
        mutated = json.loads(json.dumps(saved))
        for page, rows in mutated["hot"] + mutated["cold"]:
            if rows:
                rows[0][4] = float("nan")
                break
        with self.assertRaises(ValueError):
            a.restore(mutated)
        self.assertEqual(saved, a.snapshot())

    def test_backend_guardrails_and_cli(self):
        with self.assertRaises(ValueError):
            PagedBrain(dendrites=True, lif_kernel="native")
        with self.assertRaises(ValueError):
            PagedBrain(dendrites=1)
        with self.assertRaises(ValueError):
            main(["demo", "--engine", "legacy", "--dendrites"])
        a = PagedBrain(max_pages=8, ticks=3, learning=False, dendrites=True)
        response = a.step({"food": 0.9})
        self.assertEqual(response["action"], "interact")
        self.assertEqual(response["dendrite_model"], "four-branch-proxy-r07")


if __name__ == "__main__":
    unittest.main()
