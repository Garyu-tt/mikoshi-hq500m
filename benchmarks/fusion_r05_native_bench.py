#!/usr/bin/env python3
"""Cold/warm end-to-end CPU comparison of exact Python vs optional native C5.

No extrapolation from microbenchmark or dense-equivalent TOPS. Original C5
connections, identical drive and no added fanout. Repeats reset the brain.
"""
import json
from pathlib import Path
import platform
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import PagedBrain
from hq500m.c5_fast import source_edges
from hq500m.native_c5 import NativeUnavailable

SIZES = (1024, 4096, 8192)
REPEATS = 4


def measure(n, kernel, cold):
    timings = []
    results = []
    stimulus = {500_000 + i * 59_771: 2.0 for i in range(n)}
    for _ in range(REPEATS):
        if cold:
            source_edges.cache_clear()
        brain = PagedBrain(max_pages=1024, ticks=2,
                           learning=False, kernel=kernel)
        t0 = time.perf_counter()
        result = brain.step({}, stimulus)
        timings.append(time.perf_counter() - t0)
        results.append(result)
    assert all(r == results[0] for r in results), "nondeterministic repeated result"
    return {
        "median_seconds": round(statistics.median(timings), 6),
        "all_seconds": [round(t, 6) for t in timings],
        "neural": results[-1],
    }


def main():
    output = {
        "project": "HQ500M x BitWeave Fusion R05",
        "host": platform.node(),
        "cpu": platform.processor(),
        "python": platform.python_version(),
        "benchmark": "full PagedBrain.step of 2 ticks, 1024 logical pages",
        "input": "first-tick forced 2.0 in N unique exact virtual C5 sources",
        "repetitions": REPEATS,
        "cold_definition": "source_edges Python LRU cleared immediately before run",
        "warm_definition": "same source IDs repeated with existing Python LRU",
        "kernels": ["python", "native"],
        "cases": [],
    }
    for n in SIZES:
        for cold in (True, False):
            a = measure(n, "python", cold)
            b = measure(n, "native", cold)
            assert {k:v for k,v in a["neural"].items() if k!="c5_kernel"} == {
                k:v for k,v in b["neural"].items() if k!="c5_kernel"
            }, "native vs Python network mismatch"
            row = {
                "forced_sources": n,
                "cold": cold,
                "real_updated": a["neural"]["unique_updated_neurons"],
                "real_spiking": a["neural"]["unique_spiking_neurons"],
                "c5_events_delivered": a["neural"]["synapses_delivered"],
                "cross_region_delivered": a["neural"]["remote_synapses_delivered"],
                "python_s": a["median_seconds"],
                "native_s": b["median_seconds"],
                "native_over_python_x": round(a["median_seconds"]/b["median_seconds"], 4),
                "python_repetitions_s": a["all_seconds"],
                "native_repetitions_s": b["all_seconds"],
            }
            output["cases"].append(row)
            print(json.dumps(row),flush=True)
    path=Path(__file__).resolve().parents[1]/"artifacts/fusion_r05_native_bench.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"complete":True,"report":str(path)}),flush=True)


if __name__ == "__main__":
    main()
