#!/usr/bin/env python3
"""Fusion R04 small controlled associative learning assay.

Pre-specified source pages and deterministic cue->readout candidate selection
based ONLY on pretraining C5 weights. Paired vs four controls, equal schedules.
Toy local excitatory STDP, not validated cognition or generalization.
"""
from collections import defaultdict
import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hq500m import PagedBrain
from hq500m.c5_fast import source_edges

BASES = (
    1_048_576, 1_049_600, 1_050_624, 2_011_136, 16_777_216,
    134_217_728, 250_000_384, 300_000_256, 370_000_896,
    420_000_768, 450_000_896, 480_000_000,
)
REPETITIONS = 25
GAP = 16
CONDITIONS = ("paired", "plasticity_off", "cue_only", "teacher_only", "remote_only")


def select_readout(base):
    if base % 1024:
        raise ValueError("source module must be 1024-aligned")
    cue_ids = set(range(base, base + 128))
    totals = defaultdict(float)
    excitatory_counts = defaultdict(int)
    excitatory_magnitude = defaultdict(float)
    for src in sorted(cue_ids):
        for target, gain in source_edges(src)[:24]:
            if target in cue_ids:
                continue
            totals[target] += gain
            if gain > 0:
                excitatory_counts[target] += 1
                excitatory_magnitude[target] += gain
    choices = [(abs(total - .875), target, total, excitatory_counts[target],
                excitatory_magnitude[target])
               for target, total in totals.items()
               if .75 <= total <= .95 and excitatory_counts[target] >= 5]
    if not choices:
        return None
    _, target, total, npos, positive = min(choices)
    return {"target": target, "expected_cue_current": round(total, 7),
            "excitatory_incoming_edges": npos,
            "positive_current": round(positive, 7)}


def run_condition(base, target, condition):
    learned = condition != "plasticity_off"
    scope = "remote" if condition == "remote_only" else "all_exc"
    brain = PagedBrain(max_pages=128, ticks=1, threshold=1.0,
                       plasticity_scope=scope, learning=learned)
    cue = {base + i: 2.0 for i in range(128)}
    def probe():
        brain.step({}, cue)
        response = brain.step({}, watch_ids=(target,))
        return bool(response["watched_spike_ticks"][str(target)])
    baseline = probe()
    for _ in range(GAP):
        brain.step({})
    start = time.perf_counter()
    for _ in range(REPETITIONS):
        brain.step({}, cue if condition not in ("teacher_only",) else None)
        brain.step({}, {target: 2.0} if condition in
                   ("paired", "plasticity_off", "teacher_only", "remote_only") else None)
        for _ in range(GAP):
            brain.step({})
    # Independent checkpoint clones: probes never train the same object twice.
    frozen = json.loads(json.dumps(brain.snapshot()))
    immediate = PagedBrain(max_pages=128, ticks=1, threshold=1.0,
                           plasticity_scope=scope, learning=learned)
    immediate.restore(frozen)
    delayed = PagedBrain(max_pages=128, ticks=1, threshold=1.0,
                         plasticity_scope=scope, learning=learned)
    delayed.restore(frozen)
    distractor = PagedBrain(max_pages=128, ticks=1, threshold=1.0,
                            plasticity_scope=scope, learning=learned)
    distractor.restore(frozen)

    def readout(test):
        test.step({}, cue)
        return bool(test.step({}, watch_ids=(target,))
                    ["watched_spike_ticks"][str(target)])
    output = readout(immediate)
    for _ in range(256):
        delayed.step({})
    after_delay = readout(delayed)
    # Unrelated neighbouring module stimulus, followed by 16 silent ticks.
    distractor.step({}, {base + 1024 + i: 2.0 for i in range(128)})
    for _ in range(GAP):
        distractor.step({})
    after_distractor = readout(distractor)
    deltas = []
    for src in cue:
        for slot, (dst, gain) in enumerate(source_edges(src)):
            if dst == target and gain > 0:
                deltas.append(brain.plastic.get((src, slot), 0.0))
    return {
        "baseline_readout_spike": baseline,
        "after_training_readout_spike": output,
        "after_256_silent_ticks": after_delay,
        "after_unrelated_distractor": after_distractor,
        "positive_target_synapses": len(deltas),
        "target_synapse_multiplier_delta_sum": round(sum(deltas), 6),
        "changed_c5_synapses_all": len(brain.plastic),
        "plastic_updates_all": brain.plasticity_updates,
        "elapsed_s": round(time.perf_counter() - start, 4),
    }


def main():
    all_trials = []
    for base in BASES:
        readout = select_readout(base)
        if readout is None:
            all_trials.append({"base": base, "selection": "no eligible target"})
            print(json.dumps(all_trials[-1]), flush=True)
            continue
        scores = {c: run_condition(base, readout["target"], c)
                  for c in CONDITIONS}
        summary = {"base": base, "readout": readout, "conditions": scores}
        all_trials.append(summary)
        print(json.dumps({"base": base, "readout": readout["target"],
            "post_spike": {k: v["after_training_readout_spike"]
                           for k, v in scores.items()},
            "paired_delta": scores["paired"]["target_synapse_multiplier_delta_sum"]}),
            flush=True)
    evaluated = [x for x in all_trials if "conditions" in x]
    report = {
        "experiment": "fusion-r04-local-association",
        "label": "controlled toy associative plasticity, topology-conditioned selection",
        "date": "2026-11-08",
        "source_pages_prespecified": list(BASES),
        "selected_by": "absolute predicted cue C5 current nearest .875 within [.75,.95], >=5 positive local inputs",
        "pulse_sources_per_trial": 128,
        "training_repetitions": REPETITIONS,
        "inter_trial_silent_ticks": GAP,
        "lif_threshold": 1.0,
        "plasticity_policy": "positive all-C5 only in paired/cueonly/teacheronly",
        "conditions": list(CONDITIONS),
        "total_eligible": len(evaluated),
        "success_counts": {c: sum(x["conditions"][c]["after_training_readout_spike"]
                                 for x in evaluated) for c in CONDITIONS},
        "retention_256_ticks": {c: sum(x["conditions"][c]["after_256_silent_ticks"]
                                    for x in evaluated) for c in CONDITIONS},
        "distractor_retention": {c: sum(x["conditions"][c]["after_unrelated_distractor"]
                                     for x in evaluated) for c in CONDITIONS},
        "baseline_spiking": sum(x["conditions"]["paired"]["baseline_readout_spike"]
                               for x in evaluated),
        "trials": all_trials,
        "limitations": ["not randomized target selection or biological model",
                        "selection based on known target C5 current, not held-out unseen tasks",
                        "single-cue local circuit, not broad autonomously learned behavior",
                        "teacher pulse explicitly forces desired post spike during training"],
    }
    out = Path(__file__).resolve().parents[1] / "artifacts/fusion_r04_assay.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"complete": True, "eligible": len(evaluated),
                      "success_counts": report["success_counts"],
                      "retention": report["retention_256_ticks"],
                      "distractor_retention": report["distractor_retention"],
                      "output": str(out)}))


if __name__ == "__main__":
    main()
