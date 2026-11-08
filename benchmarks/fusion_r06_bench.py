#!/usr/bin/env python3
"""R06 reproducible CPU end-to-end stress; exact C5, no synthetic fanout.

Captures neural outputs, wall clock, max RSS. The >1M integrated-neuron
test requires explicit --large and only forces 32,768 source neurons.
The other ~1M are synaptically updated, not independently firing.
"""
import argparse
import json
from pathlib import Path
import platform
import resource
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import PagedBrain

IGNORED = {"event_kernel", "lif_kernel", "native_lif_input_cells",
           "native_lif_integrations", "native_lif_page_batches"}

def benchmark(n, mode, repeats, lab_cap):
    times = []
    observed = []
    for _ in range(repeats):
        opts = {"event_kernel": "python", "lif_kernel": "python"} if mode == "python" else {
            "event_kernel": "native", "lif_kernel": "native"}
        brain = PagedBrain(max_pages=1024, ticks=2, learning=False,
                           kernel="native", lab_max_pulses=lab_cap, **opts)
        pulse = {500_000+i*12_941: 2.0 for i in range(n)}
        start = time.perf_counter()
        result = brain.step({}, pulse)
        times.append(time.perf_counter()-start)
        observed.append(result)
    assert all(a == observed[0] for a in observed)
    return {"median_seconds": round(statistics.median(times),6),
            "samples_seconds": [round(t,6) for t in times],
            "neural": observed[0]}

def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--large", action="store_true",
                     help="allow 32,768 forced sources (~1M integrated IDs)")
    cli.add_argument("--repeats", type=int, default=2)
    args = cli.parse_args()
    if not 1 <= args.repeats <= 4:
        cli.error("repeats must be 1..4")
    sizes = [8192, 32768] if args.large else [4096, 8192]
    rows = []
    for n in sizes:
        cap = 32768 if args.large else 8192
        reference = benchmark(n, "python", args.repeats, cap)
        native = benchmark(n, "native", args.repeats, cap)
        ra = {k:v for k,v in reference["neural"].items() if k not in IGNORED}
        rb = {k:v for k,v in native["neural"].items() if k not in IGNORED}
        assert ra == rb, "native event/LIF results diverged from Python"
        result = reference["neural"]
        row = {
            "forced_sources": n,
            "unique_membrane_integrated_neurons":
                result["unique_membrane_integrated_neurons"],
            "received_synaptic_current_neurons": result["unique_updated_neurons"],
            "refractory_event_skips": result["refractory_event_skips"],
            "unique_firing_neurons": result["unique_spiking_neurons"],
            "original_C5_delivered": result["synapses_delivered"],
            "original_remote_delivered": result["remote_synapses_delivered"],
            "python_s": reference["median_seconds"],
            "native_event_lif_s": native["median_seconds"],
            "native_vs_python_x": round(reference["median_seconds"] /
                                        native["median_seconds"],3),
            "python_samples_s": reference["samples_seconds"],
            "native_samples_s": native["samples_seconds"],
            "native_lif_input_cells": native["neural"]["native_lif_input_cells"],
            "native_lif_integrations": native["neural"]["native_lif_integrations"],
            "checks": "all nonbackend fields exactly equal",
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
    report = {
        "project": "Fusion R06 exact CPU event reduction + LIF",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "repeats": args.repeats,
        "large_lab_mode": args.large,
        "neural_ticks": 2,
        "input": "2.0 pulse on first tick, globally distinct source IDs: 500000 + i*12941",
        "max_resident_pages": 1024,
        "python_C5_kernel": False,
        "native_C5_kernel": True,
        "learning": False,
        "artificial_fanout": False,
        "limitations": [
            "forcing neurons artificially is not cognition or learning",
            "native bulk LIF only on dense pages >= 48 events; sparse pages remain Python",
            "C-native state storage and GPU BitWeave not implemented",
            "single host and few short samples, no general speed guarantee"
        ],
        "cases": rows,
        "process_peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1),
    }
    output = Path(__file__).resolve().parents[1]/"artifacts/fusion_r06_bench.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"complete": True, "report": str(output),
                      "process_peak_rss_mib": report["process_peak_rss_mib"]}))

if __name__=="__main__":
    main()
