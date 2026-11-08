#!/usr/bin/env python3
"""Reproducible, bounded Fusion R03 CPU profiles (standard library only)."""
import argparse
import json
import os
import resource
import statistics
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import PagedBrain

def trial(sources, pages, ticks, learning=False):
    # Spread exact global source IDs across synthetic virtual C5 address space,
    # deliberately as LAB DRIVE: not autonomous behavior.
    pulses = {500_000 + i * 59_771: 2.0 for i in range(sources)}
    brain = PagedBrain(max_pages=pages, ticks=ticks, learning=learning)
    start = time.perf_counter()
    result = brain.step({}, pulses)
    elapsed = time.perf_counter() - start
    return elapsed, result

def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--sources", type=int, nargs="+", default=[1024, 4096, 8192])
    cli.add_argument("--trials", type=int, default=3)
    cli.add_argument("--pages", type=int, default=1024)
    cli.add_argument("--ticks", type=int, default=2)
    args = cli.parse_args()
    if not 1 <= args.trials <= 6:
        cli.error("trials must be 1..6")
    if any(n < 1 or n > 8192 for n in args.sources):
        cli.error("each source count must be 1..8192")
    out = {"engine": "HQ500M Fusion R03 exact-C5 CPU", "python_pid": os.getpid(),
           "trials": args.trials, "page_budget": args.pages, "ticks": args.ticks,
           "synthetic_broadcast": False, "source_input": "forced_2.0_first_tick",
           "results": []}
    for n in args.sources:
        measures = [trial(n, args.pages, args.ticks)
                    for _ in range(args.trials)]
        seconds = [duration for duration, _ in measures]
        metrics = measures[-1][1]
        assert all(r["synapses_delivered"] +
                   r["pending_synapse_events"] >= r["remote_synapses_delivered"]
                   for _, r in measures)
        out["results"].append({
            "forced_sources": n, "median_step_seconds": round(statistics.median(seconds), 6),
            "all_step_seconds": [round(s, 6) for s in seconds],
            "unique_updated": metrics["unique_updated_neurons"],
            "unique_spiking": metrics["unique_spiking_neurons"],
            "undriven_spiking": metrics["unique_undriven_spiking_neurons"],
            "delivered_c5_events": metrics["synapses_delivered"],
            "remote_delivered": metrics["remote_synapses_delivered"],
            "resident_address_count": metrics["resident_neurons"],
            "page_loads": metrics["pages_loaded"],
            "evictions": metrics["pages_evicted"],
        })
        print(json.dumps(out["results"][-1]), flush=True)
    out["process_peak_rss_mb"] = round(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    print(json.dumps({"complete": True, "process_peak_rss_mb": out["process_peak_rss_mb"]}))
if __name__ == "__main__":
    main()
