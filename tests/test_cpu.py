"""End-to-end CPU-only checks: procedural addressing, game IO, learning, persistence."""
import io
import json
import math
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import Brain, VIRTUAL_NEURONS, describe_ports, edge
from hq500m.core import BOUNDS, REGION_NAMES, _normalize_observation, region
from hq500m.__main__ import main, run_step


class CPUPlaygroundTests(unittest.TestCase):
    def test_scope_and_port_ranges(self):
        self.assertEqual(VIRTUAL_NEURONS, 500_000_000)
        self.assertEqual(len(REGION_NAMES), 7)
        mapping = describe_ports()
        self.assertEqual(mapping["virtual_neurons"], VIRTUAL_NEURONS)
        for io in ("inputs", "outputs"):
            for item in mapping[io].values():
                lo, hi = item["neuron_ids"]
                self.assertEqual(hi - lo + 1, 12)
                self.assertLess(hi, VIRTUAL_NEURONS)
                self.assertEqual(region(lo), region(hi))
        self.assertIn("spinal cord itself is NOT simulated", mapping["spinal_cord_note"])

    def test_32_virtual_connections_and_boundaries(self):
        for neuron in (0, 1023, 1048577, BOUNDS[1], BOUNDS[2], BOUNDS[3],
                       BOUNDS[4], BOUNDS[5], BOUNDS[6], VIRTUAL_NEURONS - 1):
            connections = [edge(neuron, i) for i in range(32)]
            self.assertEqual(connections, [edge(neuron, i) for i in range(32)])
            self.assertTrue(all(0 <= x[0] < VIRTUAL_NEURONS for x in connections))
            for x in connections[:24]:
                self.assertEqual(x[0] // 1024, neuron // 1024)
        for invalid in (-1, 500_000_000):
            with self.assertRaises(ValueError):
                edge(invalid, 0)

    def test_neural_io_genuinely_routes_inputs_to_motor(self):
        for sensor, command in (("food", "interact"), ("threat", "retreat"),
                                ("obstacle_left", "right"), ("obstacle_right", "left"),
                                ("eye_left", "left"), ("eye_right", "right"),
                                ("balance", "forward"), ("fatigue", "idle"),
                                ("spinal_sensory", "retreat")):
            brain = Brain()
            response = brain.step({sensor: 1.0})
            self.assertEqual(response["action"], command, sensor)
            self.assertGreater(response["motor_spikes"][command], 0)
            self.assertEqual(response["resident_neurons"], 896)
        idle = Brain().step({})
        self.assertEqual(idle["action"], "idle")
        self.assertEqual(idle["spikes"], 0)

    def test_learning_and_replay(self):
        brain = Brain()
        first = brain.step({"threat": 1.0})
        self.assertEqual(first["action"], "retreat")
        second = brain.step({"reward": 1.0})
        self.assertGreater(second["plasticity_updates"], 0)
        self.assertGreater(brain.q["retreat"], 0.0)
        self.assertGreater(brain.gain["threat:retreat"], 1.0)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"
            brain.save(path)
            other = Brain()
            other.load(path)
            self.assertEqual(other.snapshot(), brain.snapshot())
            self.assertEqual(brain.step({"food": 0.9}), other.step({"food": 0.9}))
            bad = brain.snapshot()
            bad["virtual_neurons"] = 1_000_000_000
            with self.assertRaises(ValueError):
                other.restore(bad)

    def test_reproducibility_and_scale(self):
        a, b = Brain(cells=256), Brain(cells=256)
        for stimulus in ({"food": 1.0}, {"reward": -0.7, "eye_left": 0.8},
                         {"obstacle": 1.0}, {"touch": 0.2}):
            self.assertEqual(a.step(stimulus), b.step(stimulus))
        self.assertEqual(a.neurons, 1792)
        self.assertLess(a.local_edges, 1792 * 33)

    def test_protocol_rejects_bad_input(self):
        brain = Brain()
        for payload in ({"bad": 1}, {"food": 2}, {"food": math.nan},
                        {"food": True}, [], {f"s{i}": 0 for i in range(25)}):
            with self.assertRaises(ValueError):
                brain.step(payload)
        with self.assertRaises(ValueError):
            run_step(brain, {"observation": {}, "command": "shutdown"})
        with self.assertRaises(ValueError):
            Brain(cells=42)

    def test_loopback_http_adapter(self):
        import subprocess
        import urllib.request
        from urllib.error import HTTPError
        cmd = [sys.executable, "-m", "hq500m", "server", "--port", "0"]
        proc = subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parents[1]),
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            status = proc.stderr.readline().strip()
            self.assertIn("http://127.0.0.1:", status)
            base = status.split("http://", 1)[1]
            with urllib.request.urlopen("http://" + base + "/v1/ports", timeout=3) as reply:
                ports = json.load(reply)
            self.assertIn("eye_left", ports["inputs"])
            self.assertIn("spinal_sensory", ports["inputs"])
            payload = json.dumps({"observation": {"food": 0.9}}).encode()
            request = urllib.request.Request("http://" + base + "/v1/step", data=payload,
                                             headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=3) as reply:
                self.assertEqual(json.load(reply)["action"], "interact")
            bad = urllib.request.Request("http://" + base + "/v1/step", data=b'{"observation":{"oops":1}}')
            with self.assertRaises(HTTPError) as caught:
                urllib.request.urlopen(bad, timeout=3)
            self.assertEqual(caught.exception.code, 400)
        finally:
            proc.terminate()
            proc.wait(timeout=3)
            proc.stderr.close()

    def test_cli_port_map_and_query(self):
        for args in (["ports"], ["query", "499999999"]):
            with io.StringIO() as buf, redirect_stdout(buf):
                main(args)
                result = json.loads(buf.getvalue())
                self.assertEqual(result["virtual_neurons"], VIRTUAL_NEURONS)
        with self.assertRaises(ValueError):
            main(["query", "500000000"])


if __name__ == "__main__":
    unittest.main()
