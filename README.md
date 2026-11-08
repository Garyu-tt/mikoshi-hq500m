# Mikoshi HQ500M — GENESIS Human Quantum

**Experimental fixed-scale neural graph with 500,000,000 virtual neuron addresses.**

HQ500M is a CUDA-based research prototype of a **synthetic, cortical-inspired** network. It generates deterministic graph connections on demand, keeps a small set of 1,024-neuron modules active across eight GPUs, routes events to exact global addresses and experiments with sparse synaptic plasticity.

> **Scope:** 500,000,000 is the *virtual address space*, **not** 500 million simultaneously simulated neurons. This is not a reconstructed human connectome, human brain simulation, general AI or evidence of human-like cognition.

## What is implemented

- Fixed neuron IDs **0 … 499,999,999** (compile-time constant; no billion-neuron option here).
- 32 deterministic potential outgoing edges per neuron: 24 module-local and 8 projected, for 16 billion **potential**, not materialized, edges.
- A bounded, resident CUDA working set across **8 CUDA-capable GPUs**; demand paging retains exact global event destinations.
- Sparse, per-connection long-range excitatory plasticity and checkpoint restore.
- Q0.8: a selected-synapse cue/teaching/readout experiment with three negative controls and a saved-state continuation test (see [technical Q0.8 notes](docs/Q08.md)).
- Q0.9: **experimental** cohort methodology for testing multiple preselected synapses. The full cohort is **not independently confirmed** in this repository.

## Run CPU-only graph inspection

Python 3, no GPU required:

```bash
python3 tools/query_edges.py 0
python3 tools/query_edges.py 499999999
python3 tests/test_fixed_scope.py
```

This inspects **virtual deterministic connectivity**, not network dynamics.

## CUDA requirements and build

The CUDA simulation currently requires **8 available NVIDIA CUDA GPUs**. It is not configured to run the full simulation on one GPU.

```bash
nvcc -O2 -std=c++17 -o hq500m_q08_assay src/hq500m_q08_assay.cu
nvcc -O2 -std=c++17 -o hq500m_q09_batch src/hq500m_q09_batch.cu
```

CUDA builds and GPU-run reproduction have **not been repeated in this GitHub export environment**. The original experiments used eight NVIDIA P106-100 devices; consult the documentation for their limited scope.

## Reproduce the Q0.8 controlled assay

```bash
./hq500m_q08_assay on 240 q08_on.json
./hq500m_q08_assay off 240 q08_off.json
./hq500m_q08_assay unpaired 240 q08_unpaired.json
./hq500m_q08_assay cueonly 240 q08_cueonly.json

# Generate an intermediate checkpoint and resume without altering it.
./hq500m_q08_assay on 190 q08_partial.json q08_at_190.chk
./hq500m_q08_assay on 240 q08_restored.json q08_at_190.chk --resume-no-save

python3 tests/hq500m_q08_audit.py q08_on.json q08_off.json q08_unpaired.json q08_cueonly.json q08_restored.json
```

The output is a small, hand-defined associative learning assay. A passing test does not establish generalizable learning.

## Investigate Q0.9 (experimental)

```bash
mkdir -p q09_cohort
./hq500m_q09_batch 0 3
python3 tests/hq500m_q09_cohort_audit.py q09_cohort 4
```

The cohort script evaluates four conditions per trial. **Do not describe a cohort as passing until the raw JSON outputs have been generated and the audit has completed on your hardware.**

## Source layout

- `src/genesis_hq500m_q08.cu`: fixed 500M procedural graph, paging and CUDA LIF substrate.
- `src/hq500m_q08_assay.cu`: Q0.8 associative probe and ablations.
- `src/hq500m_q09_trial_impl.cu`, `src/hq500m_q09_batch.cu`: experimental cohort driver.
- `tests/hq500m_oracle.py`: independent CPU edge generation reference.
- `tests/hq500m_q08_audit.py`, `tests/hq500m_q09_cohort_audit.py`: experiment result audits.
- `data/hq500m_genome.json`: original synthetic genome values (not a general executable genome interpreter).
- `docs/Q08.md`: experimental observations and limitations.

No GPU binaries, trained checkpoints, private operational paths, server logs or third-party datasets are shipped in this initial source release.

## Scientific limitations

- The full 500M graph has **never** been simultaneously activated, materialized or trained.
- The Q0.8 learning result comes from one deterministically selected synthetic synapse, **not** from a randomized population.
- Local and inhibitory edges are not covered by the Q0.8 plasticity mechanism.
- Routing latency and paging fairness may influence outcomes; Q0.9 is intended to explore reliability.
- Labels such as "Human Quantum" are project names; the implementation does **not** use quantum computing or recreate human consciousness.

Original source code in this release is **GNU GPLv3 or later** (`GPL-3.0-or-later`). Copyright (C) 2026 [Garyu-tt](https://github.com/Garyu-tt). See [LICENSE](LICENSE) and [AUTHORS.md](AUTHORS.md). Previously published MIT revisions retain their original permissions.
