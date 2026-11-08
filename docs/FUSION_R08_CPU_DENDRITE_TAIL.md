# Fusion R08 — sparse CPU dendritic temporal tails

Date: 2026-11-08. CPU-only experimental extension for the
R07 synthetic four-branch paged neuron engine. No GPU required.

## Fixed R07 limitation

The paged scheduler integrates a neuron only when it receives an
event. R07 therefore stored branch potential but skipped all
silent ticks, even when a slowly decaying branch would have
triggered a delayed somatic spike.

R08 optionally tracks recently charged dendritic cells in a
bounded sparse CPU wake map, keyed by original exact global ID.
Those cells are integrated on silent ticks for up to 1..8 further
ticks without artificially injecting any new synaptic event.

- No dense 500M array. A hard limit of 131,072 simultaneously
  pending wake IDs raises an explicit error if exceeded, never
  silently dropping state.
- Four branch voltages, signed inhibition and original 32 C5
  connections remain unchanged.
- Quiet wakes expire when branch voltage decays below 0.025,
  a cell fires, or their configured tail tick budget is exhausted.
- Checkpoints retain global wake IDs and their expiry ticks.
  Restore validates wake geometry and the existence of each
  saved neuron before mutating engine state.
- Telemetry differentiates real arrivals (unique_updated_neurons)
  from awake neurons without arrivals (dendritic_wake_integrations)
  and their spikes (dendritic_silent_spikes).
- Default tail remains 0 for R07 checkpoint compatibility.
  Native C99 LIF remains unsupported with compartments enabled.
  CPU C5/native event reducer can still be used independently.

## Run

    python3 -m hq500m demo --engine paged --dendrites --dendrite-tail 4
    python3 -m unittest discover -s tests -v

This is a four-branch synthetic model, **not** measured human
dendritic biophysics, verified NMDA plateaus, or a human connectome.
Tail ticks are deliberately arbitrary software timesteps; no
biological millisecond scale has been calibrated.

CPU cost depends on the number and duration of recently active
branches. The explicit 131,072-wake safety ceiling can be hit in
large-scale lab workloads; reduce tail duration or intensity.

## Measured CPU cost on mirbi-linux (32-vCPU host)

Reproducible opt-in probe with 2 trials per configuration, three
simulation ticks per external step, exactly 32 C5 outputs per driven
source, and an additional three-tick silent step:

| Driven IDs | Tail ticks | Median drive-step seconds | Median silent-step seconds |
|---:|---:|---:|---:|
| 256 | 0 | 0.0874 | 0.00053 |
| 256 | 4 | 0.1733 | 0.13962 |
| 1,024 | 0 | 0.3625 | 0.00154 |
| 1,024 | 4 | 0.6754 | 0.54645 |

The 1,024-ID / tail-4 silent follow-up performed 67,833 additional
branch-tail integrations without new external inputs (three ticks in
one step), and ultimately cleared its bounded wake map. Thus the
feature provides additional neural dynamics at **substantial CPU cost**,
not an acceleration. All times are preliminary, machine-specific and
use only two trials; do not extrapolate them to 500M active cells.

Reproduce each workload:

    python3 benchmarks/fusion_r08_dendrite_cpu_bench.py --sources 1024 --tail 0 --trials 2
    python3 benchmarks/fusion_r08_dendrite_cpu_bench.py --sources 1024 --tail 4 --trials 2

Raw runs: artifacts/fusion_r08_bench_{256,1024}_tail{0,4}.json.
