"""Reproducible CPU-only R08 four-branch temporal-tail cost probe.

No GPU used; benchmark measures full Python engine steps, not a kernel
throughput extrapolation. Repeat runs as separate OS processes.
"""
import argparse
import json
import resource
import statistics
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import PagedBrain


def run(sources=512, tail=0, trials=2, ticks=3):
    if not 1 <= sources <= 2048 or tail not in range(9):
        raise ValueError("sources must be 1..2048, tail 0..8")
    results = []
    for i in range(trials):
        b = PagedBrain(max_pages=128, ticks=ticks, learning=False,
                       dendrites=True, dendrite_tail_ticks=tail)
        pulses = {500_000 + j * 12_941: 2.0 for j in range(sources)}
        t0 = time.perf_counter()
        drive = b.step({}, pulses)
        t1 = time.perf_counter()
        silence = b.step({})
        t2 = time.perf_counter()
        results.append({
            "driven_seconds": t1 - t0, "silent_seconds": t2 - t1,
            "driven_spikes": drive["spikes"],
            "driven_integrated_unique": drive["unique_membrane_integrated_neurons"],
            "driven_events": drive["synapses_delivered"],
            "silent_spikes": silence["spikes"],
            "silent_no_input_integrations": silence.get("dendritic_wake_integrations", 0),
            "wake_after_silence": silence.get("dendritic_active_tails", 0),
        })
    return {
        "schema": "HQ500M-CPU-FUSION-R08-DENDRITE-BENCH",
        "sources": sources, "ticks_per_step": ticks, "tail_ticks": tail,
        "trials": trials, "median_driven_seconds": round(statistics.median(
            r["driven_seconds"] for r in results), 6),
        "median_silent_seconds": round(statistics.median(
            r["silent_seconds"] for r in results), 6),
        "maxrss_kib_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "results": results,
        "no_gpu_used": True, "virtual_neurons_not_fully_active": True,
        "real_human_dendrites": False
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sources", type=int, default=512)
    p.add_argument("--tail", type=int, default=0)
    p.add_argument("--trials", type=int, default=2)
    p.add_argument("--ticks", type=int, default=3)
    args = p.parse_args()
    print(json.dumps(run(args.sources, args.tail, args.trials, args.ticks), indent=2))
