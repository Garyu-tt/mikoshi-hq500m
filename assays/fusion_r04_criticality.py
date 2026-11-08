#!/usr/bin/env python3
"""Bounded HQ500M Fusion R04 excitability / recurrent-C5 propagation study.

External drive only in first tick; learning off; all connections are original
C5 (no synthetic fanout). Saves reproducible per-module observations.
This is a toy synthetic dynamical-system experiment, not a cognition score.
"""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import PagedBrain

BASES = (1_048_576, 1_049_600, 1_050_624, 2_011_136, 469_999_616)
THRESHOLDS = (1.0, .4, .35, .30, .25)

def sample(base, threshold, windows=1):
    brain = PagedBrain(max_pages=128, ticks=24, learning=False,
                       threshold=threshold)
    results = []
    start = time.perf_counter()
    try:
        for k in range(windows):
            source = {base+i: 2.0 for i in range(512)} if k == 0 else {}
            result = brain.step({}, source)
            results.append({
                "window": k, "input_source_neurons": len(source),
                "spikes_total": result["spikes"],
                "unique_spiking": result["unique_spiking_neurons"],
                "unforced_spiking": result["unique_undriven_spiking_neurons"],
                "spiking_outside_driven_pages":
                    result["unique_spiking_outside_driven_pages"] if k == 0 else None,
                "spiking_pages": result["spiking_pages"],
                "spiking_outside_driven_pages":
                    result["spiking_outside_driven_pages"] if k == 0 else None,
                "updated": result["unique_updated_neurons"],
                "remote_c5_events": result["remote_synapses_delivered"],
                "last_tick_spikes": result["spikes_per_tick"][-1],
                "firing_ticks": sum(x > 0 for x in result["spikes_per_tick"]),
                "spikes_per_tick": result["spikes_per_tick"],
                "pending": result["pending_synapse_events"],
                "dropped": result["nonresident_synapse_events_dropped"],
                "pages_resident_end": result["resident_pages"],
            })
        return {"base": base, "threshold": threshold,
                "windows": results, "status": "complete",
                "seconds_total": round(time.perf_counter()-start, 5)}
    except RuntimeError as exc:
        return {"base": base, "threshold": threshold,
                "windows": results, "status": "guard-triggered",
                "error": str(exc),
                "seconds_total": round(time.perf_counter()-start, 5)}


def main():
    rows = []
    for threshold in THRESHOLDS:
        for base in BASES:
            windows = (3 if threshold in (.30, .25)
                       and base in (BASES[0], BASES[-1]) else 1)
            # Avoid hard-to-read compound conditional across lines.
            row = sample(base, threshold, windows=windows)
            rows.append(row)
            print(json.dumps({
                "base": base, "threshold": threshold,
                "result": row["status"],
                "spikes": row["windows"][0]["spikes_total"]
                           if row["windows"] else None,
                "last_spikes": row["windows"][-1]["last_tick_spikes"]
                               if row["windows"] else None,
                "windows": len(row["windows"]),
            }), flush=True)
    out = {
        "experiment": "Fusion R04 exact-C5 criticality response",
        "fixed_source_modules": list(BASES),
        "thresholds": list(THRESHOLDS),
        "source_pulse": "512 neurons at amplitude 2.0, initial tick only",
        "no_new_wiring": True,
        "learning": False,
        "artificial_fanout": False,
        "caveat": ("Sustained periodic spikes are repeated threshold crossings "
                   "within a synthetic recurrent circuit, not proof of cognition"),
        "results": rows,
    }
    target = Path(__file__).resolve().parents[1]/"artifacts/fusion_r04_criticality.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2)+"\n", encoding="utf8")
    print(json.dumps({"done": True, "cases": len(rows), "report": str(target)}))
if __name__ == "__main__":
    main()
