# HQ500M × BitWeave Fusion R04 — CPU recurrent activity and controlled plasticity

Date: 2026-11-08. Experimental synthetic neural circuit. This is not
a measured human connectome, LLM, GPU BitWeave port, or proof of cognition.
All 500,000,000 neuron IDs remain VIRTUAL. No original C5 topology was changed.

## What changed from Fusion R03

- The exact-ID demand-paged CPU simulator now accepts an OPTIONAL
  excitability parameter (LIF spike threshold 0.25..2.0). The original
  threshold 1.0 remains the DEFAULT, preserving R02/R03 behavior.
- Experimental positive local C5 plasticity is supported with the
  --plasticity-scope all_exc flag. Default remains remote-only plasticity.
  Original C5 edges are unchanged; learned multipliers are keyed by
  exact (source global neuron ID, original outgoing slot).
- Fixed the actual local-plasticity event-delivery path, which previously
  registered learning events only for remote C5 slots.
- Readout probes can monitor up to 64 explicit global IDs using the
  PagedBrain.step(..., watch_ids=[...]) Python interface.
- Metrics distinguish all event-integrated cells, those that actually
  spike, spikes outside externally driven pages, all resident addresses,
  distinct active pages, and peak per-tick activity.
- Expired causal pre/post traces are purged every 256 simulated ticks.
- Checkpoint stores experimental threshold and plasticity scope and
  refuses incompatible parameters on restore. Older R02/R03 checkpoints
  missing these keys are supported in default 1.0/remote mode.

No old learned checkpoints or active services were overwritten.
A CUDA version and native C++ kernel have NOT been built on the CPU-only
controller (no system C/C++ compiler installed).

## Reproduce (Python 3.11+, standard library only)

Default behavior remains unchanged:

~~~sh
python3 -m hq500m demo --engine paged --max-pages 128 --ticks 4
python3 -m unittest discover -s tests -v
~~~

Experimental excitability:

~~~sh
python3 -m hq500m demo --engine paged --max-pages 128 --ticks 4 --threshold 0.35
python3 assays/fusion_r04_criticality.py
~~~

Experimental local C5 associative plasticity:

~~~sh
python3 -m hq500m demo --engine paged --max-pages 128 --ticks 4 --plasticity-scope all_exc
python3 assays/fusion_r04_assay.py
~~~

These scripts use externally injected lab pulses via the Python API,
which is not exposed by the unauthenticated localhost JSONL/HTTP adapter.

## 25-cell parameter sweep — genuine C5 recurrent activity

25 cases: 5 fixed source page IDs and 5 threshold values. Each case
starts with 512 one-tick driven cells (amplitude 2.0), then no external
stimulus for the rest of 24 simulated ticks. Original 24 local plus 8
long-range C5 connections only; NO artificial broadcast; plasticity OFF.

| Threshold | Source modules still firing on tick 24 |
|---:|---:|
| 1.00 | 0 / 5 |
| 0.40 | 0 / 5 |
| 0.35 | 3 / 5 |
| 0.30 | 4 / 5 |
| 0.25 | 5 / 5 |

Four specific trials at thresholds 0.30 or 0.25 (two fixed modules)
were extended to 72 ticks without new external input. All four were
still firing at tick 72.

At threshold 0.25 and source module 469999616, first 24 ticks produced
18,183 TOTAL spikes from 3,680 DISTINCT neurons; 3,168 had not
been directly stimulated, including 2,658 outside the driven source
page. 622 pages contained one or more spike events. This means
neither 622 fully firing pages nor millions of active neurons.

NOTE: Reducing threshold changes the simulated neuron's excitability.
It can create persistent repetitive feedback loops, including
pathologically strong oscillations. It does NOT imply meaningful
information processing, memory, stable balance, learning or cognition.
Use the default threshold for regular users. The experimental
0.25 setting can consume more events/CPU and is bounded by guards.

Raw results: artifacts/fusion_r04_criticality.json
Source: assays/fusion_r04_criticality.py

## Controlled toy local associative learning

A deliberately small falsifiable plasticity experiment:

- Twelve source pages pre-specified. On each page, 128 adjacent cue cells
  are stimulated. Readout targets are deterministically selected from
  original PRE-TRAINING C5 net input closest to 0.875 within [0.75,0.95],
  requiring five or more positive local incoming C5 edges.
- Eleven of twelve pages had an eligible readout. No selection based on
  actual learning outcome.
- Each trial uses 25 train pairings, each cue followed one tick later by
  a forced teacher pulse to the target. Sixteen silent ticks separate
  train trials. Evaluation does NOT include the teacher.
- Every selected target failed to fire during its pretraining cue-only
  baseline probe.
- All conditions use the same initially selected source/target structure.
  Controls include plasticity disabled, cue-only, teacher-only, and
  plasticity limited to remote C5 slots.

| Training condition | Cue-alone readout success |
|:--|--:|
| Paired cue+teacher, positive local C5 plasticity enabled | 5 / 11 |
| Same stimuli, plasticity disabled | 0 / 11 |
| Cue only, learning enabled | 0 / 11 |
| Teacher only, learning enabled | 0 / 11 |
| Cue+teacher, remote-only plasticity | 0 / 11 |

All five successful associations retained cue-only readout firing
after 256 quiet ticks in a separate checkpoint-resumed clone and
after a nearby distinct-page distractor and 16 silent ticks in another
clone. They failed in the equivalent control branches.

CAVEATS: The targets were CONDITIONED ON known pretraining wiring
and the task uses a forced teacher spike. This is not a randomized
unseen-task benchmark, general intelligence, long-term continual
learning, or a trained naturalistic brain. Success was 5/11, not 11/11.

Raw results: artifacts/fusion_r04_assay.json
Source: assays/fusion_r04_assay.py

## Validation and next engineering block

28/28 unit/integration tests passed locally on mirbi-linux,
including the original 24 tests plus 4 R04 tests: threshold and
old-checkpoint fallback, recurrent C5 propagation with silent control,
paired plasticity vs controls, trace expiration, watch-ID validation.

For end-user scale, native page-batched event scatter and true
C++/CUDA profiling still matter. The 75.7x historical lazy-LIF
microbenchmark and up to 2.16x R03 CPU improvement must not be
converted into promised inference throughput. The full GPU BitWeave
R04 binary GEMM is not yet merged; it requires a quality-preserving
and measurable crossover with sparse C5 event handling.

Working CPU-only R04 sources are isolated from earlier R01-R03 versions.
