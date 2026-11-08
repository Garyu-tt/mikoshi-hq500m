# Fusion R05 — compiled exact-C5 CPU generator (NOT full GPU BitWeave)

Date: 2026-11-08. Host: mirbi-linux, 32 vCPUs Xeon E5-2660 v4,
Linux x86-64, Python 3.13.5. Status: native C99 module compiled
and physically loaded on the project host, CPU and C99 library parity
verified. This is a synthetic 500M-VIRTUAL-ID neural circuit, not
a 500M-resident or trained human connectome.

## What was implemented

An optional native kernel calculates all 32 procedural original
HQ500M C5 outgoing synapses per spiking source in one C99 batch.
It preserves the exact integer global target ID and signed integer
synapse weight (and then uses the original 0.000035 gain factor).
The 24 local and 8 long-range C5 edges and all region bounds are
unchanged. There is no extra synthetic sensory fanout.

- Source: hq500m/native/c5_batch.c (pure C99, no Python C API)
- Build: sh hq500m/native/build.sh
- Host loader / validation: hq500m/native_c5.py using Python ctypes
- Consumer: hq500m/page_engine.py
- Reproducible benchmarks: benchmarks/fusion_r05_native_bench.py
- Raw host results: artifacts/fusion_r05_native_bench.json
- Regression: tests/test_fusion_r05.py

The native code only produces exact C5 outgoing links. It DOES NOT
replace Python LIF integration, event sorting, state paging,
plasticity, checkpoint, GPU execution, or neural model inference.
It is not the binary/ternary GEMM GPU BitWeave R04 kernel.

## How to run

Ordinary Python works without a compiler or binary:

~~~sh
python3 -m hq500m demo --engine paged --kernel python --max-pages 128
~~~

Linux x86-64 native optional mode (on a system with a C99 compiler):

~~~sh
sh hq500m/native/build.sh
python3 -m hq500m demo --engine paged --kernel native --max-pages 128
python3 benchmarks/fusion_r05_native_bench.py
python3 -m unittest discover -s tests -v
~~~

The native shared object is intentionally GIT-IGNORED to avoid
shipping an opaque binary for an incompatible machine. GitHub
CI builds it from reviewed C99 source on Ubuntu and tests Python
3.11 and 3.13. If the library cannot be loaded, select --kernel python.
Kernel auto loads native if it exists, otherwise Python; it is
not a workload-sensitive dispatch policy yet. Default is Python.

On mirbi-linux the root filesystem holding apt package caches was
read-only, so apt installation of gcc did not proceed. The identical
C source was instead built in an isolated Linux x86-64 environment,
SHA256-verified and locally loaded on mirbi-linux as an optional
project-only shared object. The binary was not published or copied
into system directories.

## Correctness evidence

- 4,112 sources x 32 = 131,584 C5 edges matched the independent
  Python reference (exact target ID and signed raw integer weight).
- The actual mirbi-linux loading step additionally verified 144
  source IDs (including region boundaries) x 32 = 4,608 edges.
- Native/Python end-to-end comparisons under several inputs,
  learning enabled and disabled, optional local C5 plasticity,
  threshold 1.0 or 0.35, and checked checkpoint continuation
  showed identical neural fields, weights, and state snapshots.
  The only expected telemetry difference is the kernel label.
- 31/31 unit/integration tests passed as user mirbi locally.

## Reproducible end-to-end timing

Experiment: one PagedBrain.step, 2 LIF ticks, 1024 logical
resident-page capacity (NOT 1M fired neurons), learning disabled,
N source IDs injected at amplitude 2.0 on the first tick, exact
32 C5 outputs per firing source (including 8 long-range).
Four repeated measurements, medians of full Python-step wall time
excluding construction, printed individually in raw JSON.
All reported engine neural fields matched between Python and C99.

In C5-cold tests, the Python source_edges LRU cache was cleared
before every repetition; for hot tests identical source IDs were
reused without clearing the source cache.

| Externally driven firing sources | Actually updated | Python cold, s | Native, s | Speedup |
|---:|---:|---:|---:|---:|
| 1,024 | 33,791 | 0.178419 | 0.114541 | 1.558x |
| 4,096 | 135,162 | 0.806543 | 0.558480 | 1.444x |
| 8,192 | 270,294 | 1.797335 | 1.345554 | 1.336x |

Warm-cache comparison on same CPU:

| Externally driven sources | Cached Python, s | Native, s | Native/Python performance |
|---:|---:|---:|---:|
| 1,024 | 0.113051 | 0.122431 | 0.923x |
| 4,096 | 0.533583 | 0.575633 | 0.927x |
| 8,192 | 1.392524 | 1.468691 | 0.948x |

**Important:** Native C99 is faster when new C5 edges must
be generated, but Python's already-cached tuples can be faster
when EXACT sources recur. This is why the CPU-only binary is OPT-IN.
An adaptive kernel selector must account for hot/cold reuse and
materialization/transfer costs. Never claim native acceleration
for every case.

## Future work

- Real adaptive source-edge backend selection based on measured
  cache hit rate and working-set churn (rather than simplistic
  assumptions about GPU TOPS).
- Native CPU page-batched event accumulation and lazy LIF
  with checkpoint-compatible state, maintaining exact C5 addresses,
  learning deltas, reproducibility and silent guardrails.
- Optional actual GPU/CUDA adaptation of the sparse event queue,
  then only dispatch structured motifs to original BitWeave GEMM
  if measured efficiency wins and numerical semantics hold.
- New meaningful no-teacher generalization/retention benchmarks;
  prior R04 5/11 associations remain a controlled toy result.
