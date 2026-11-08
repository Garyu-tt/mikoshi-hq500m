"""Game-neutral JSONL and localhost HTTP adapters for HQ500M."""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .core import Brain, VIRTUAL_NEURONS, describe_ports, edge, region
from .bitweave import BitWeaveBrain


def create_brain(args):
    brain = (BitWeaveBrain(pages=args.pages, ticks=args.ticks,
                          learning=not args.no_learning, fanout=args.fanout)
             if args.engine == "bitweave" else
             Brain(cells=args.cells, ticks=args.ticks, learning=not args.no_learning))
    if args.state_file and Path(args.state_file).exists():
        brain.load(args.state_file)
    return brain


def run_step(brain, payload, state_file=None):
    if not isinstance(payload, dict) or set(payload) != {"observation"}:
        raise ValueError("request must contain only {'observation': {...}}")
    output = brain.step(payload["observation"])
    if state_file:
        brain.save(state_file)
    return output


def jsonl(args):
    brain = create_brain(args)
    for line in sys.stdin:
        if len(line) > 16_384:
            print(json.dumps({"error": "request too large"}), flush=True)
            continue
        try:
            data = json.loads(line)
            result = run_step(brain, data, args.state_file)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            result = {"error": str(e)}
        print(json.dumps(result, separators=(",", ":")), flush=True)


def server(args):
    brain = create_brain(args)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, data):
            content = json.dumps(data, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok", "engine": type(brain).__name__, "virtual_neurons": VIRTUAL_NEURONS,
                                 "resident_neurons": brain.neurons, "steps": brain.step_number})
            elif self.path == "/v1/ports":
                self._send(200, describe_ports())
            else:
                self._send(404, {"error": "unknown endpoint"})

        def do_POST(self):
            if self.path != "/v1/step":
                self._send(404, {"error": "unknown endpoint"})
                return
            raw = self.headers.get("Content-Length")
            try:
                length = int(raw)
                if not 0 < length <= 16_384:
                    raise ValueError("payload must be 1..16384 bytes")
                data = json.loads(self.rfile.read(length))
                self._send(200, run_step(brain, data, args.state_file))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})

        def log_message(self, *_):
            return

    # Intentionally fixed loopback: do not expose an unauthenticated agent on LAN.
    httpd = HTTPServer(("127.0.0.1", args.port), Handler)
    print("HQ500M CPU game API: http://127.0.0.1:%d" % httpd.server_port, file=sys.stderr)
    print("GET /v1/ports | GET /health | POST /v1/step", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def demo(args):
    brain = create_brain(args)
    print("HQ500M CPU toy; %d resident of %d virtual neurons" % (brain.neurons, VIRTUAL_NEURONS))
    for obs in ({"food": 0.9}, {"threat": 0.9, "reward": 0.5},
                {"obstacle_left": 0.8, "reward": -0.5},
                {"eye_right": 1.0}, {"novelty": 0.9}, {}):
        result = run_step(brain, {"observation": obs}, args.state_file)
        print("input=%s -> action=%s spikes=%d motor=%s unique_spiking=%s" %
              (obs, result["action"], result["spikes"], result["motor_spikes"],
               result.get("unique_spiking_neurons", "legacy")))


def query(args):
    ident = args.neuron
    info = [{"slot": slot, "target": edge(ident, slot)[0],
             "raw_weight": edge(ident, slot)[1],
             "gene": edge(ident, slot)[2],
             "inhibitory": bool(edge(ident, slot)[3]),
             "kind": "local" if slot < 24 else "projected"}
            for slot in range(32)]
    print(json.dumps({"virtual_neurons": VIRTUAL_NEURONS, "neuron": ident,
                      "region": region(ident), "edges": info,
                      "full_graph_simulated": False}, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description="Mikoshi HQ500M: portable CPU synthetic brain + game ports")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("demo", "server", "jsonl"):
        sp = sub.add_parser(name)
        sp.add_argument("--cells", type=int, default=128, choices=(128, 256, 512, 1024),
                        help="resident neurons per region; default 128")
        sp.add_argument("--ticks", type=int, default=6, help="neural ticks per game step (1..32)")
        sp.add_argument("--no-learning", action="store_true")
        sp.add_argument("--engine", choices=("legacy", "bitweave"), default="legacy",
                        help="bitweave: packed sparse event CPU simulator")
        sp.add_argument("--pages", type=int, default=16,
                        help="bitweave: resident pages of 1024 neurons per region (1..128)")
        sp.add_argument("--fanout", type=int, default=16,
                        help="bitweave: synthetic sensory broadcast lanes per resident page (0..64)")
        sp.add_argument("--state-file", help="optional persistent toy neural state")
        if name == "server":
            sp.add_argument("--port", type=int, default=8766)
    sub.add_parser("ports", help="list anatomical-style input and output ports")
    q = sub.add_parser("query", help="look up 32 deterministic edges of one virtual neuron")
    q.add_argument("neuron", type=int)
    a = p.parse_args(argv)
    if a.cmd == "demo":
        demo(a)
    elif a.cmd == "server":
        server(a)
    elif a.cmd == "jsonl":
        jsonl(a)
    elif a.cmd == "ports":
        print(json.dumps(describe_ports(), indent=2))
    elif a.cmd == "query":
        query(a)


if __name__ == "__main__":
    main()
