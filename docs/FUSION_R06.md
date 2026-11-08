# HQ500M × BitWeave Fusion R06 — first million membrane-integrated CPU neurons

Date: 2026-11-08. Experimental **CPU-only** exact-C5 synthetic neural
circuit on mirbi-linux. The 500M IDs are virtual addressable slots,
NOT 500M simultaneously firing cells, a trained LLM or measured human brain.
No GPU CUDA BitWeave kernels have been integrated.

## Milestone: 1,080,623 distinct membrane integrations

With 32,768 one-time externally stimulated **distinct source IDs**
in a 500-million-ID address space, the original 32 C5 connections/source
(24 local + 8 remote) delivered 1,048,576 synaptic events, including
262,144 remote events, during two simulation ticks. This processed
1,080,623 distinct neuron IDs through membrane integration.

The new integrated-neuron metric specifically excludes any
refractory short-circuit. In the million-cell experiment there were
**17 refractory skip occurrences**, but every ID skipped was also
integrated on the previous tick. Therefore the unique number of
actual membrane-integrated neurons remains 1,080,623.

IMPORTANT: Only **32,768 neuron IDs fired** (the deliberately driven
sources). The rest received and integrated synaptic input but did NOT
cross firing threshold. This is an engineering throughput and memory
test, **not** evidence of a million autonomous, firing, learning,
biologically faithful or behaviorally meaningful neurons.

All original C5 global IDs and 32 synapse slots were retained.
No artificial broadcasting or remapped nonresident C5 edges.
Cold per-neuron state lives in CPU RAM with LRU logical resident pages.
The maximum simultaneously mapped logical page addresses is 1,048,576,
but the 1,080,623 distinct processed IDs include pages paged in and out
DURING the two-tick step: do NOT call all of them resident simultaneously.

Standalone first observed 32,768-source experiment (native C5 generation,
Python event/LIF): **6.265 s**, process peak **520.84 MiB** on mirbi-linux
under a separate baseline run. The measured times are not per-tick
real-time latency claims.

## New compiled CPU mathematical operations

The optional native C99 library now includes two more operations:
- event_lif.c: stable-order binary64 event current aggregation of
  exact source-target ordered events;
- event_lif.c: batched lazy leaky-integrate-and-fire voltage integration
  with original LIF decay 0.68, threshold and two-tick refractory semantics.

Both operations preserve exact input and membrane semantics in tests.
They use the existing R05 native C5 generator. Python still owns the
event list, source ordering, state paging, plasticity, learning traces,
source-event generation policy, and checkpoint persistence.

The optional LIF kernel activates for relatively dense active
1024-neuron pages (at least **48** destination IDs in one tick),
and falls back to the original Python path for highly sparse pages.
Hence in the 1M test, with broadly distributed events, **zero**
cells took the native LIF route even if requested. This is not a
failure to count cells: the million-cell milestone is real but
currently runs predominantly through Python state integration.

### Modes

Standard commands (native library OPTIONAL, defaults unchanged):

~~~sh
python3 -m hq500m demo --engine paged --kernel python
python3 -m unittest discover -s tests -v
~~~

Install native on other Linux systems with a working C99 compiler,
without downloading any Python dependency:

~~~sh
sh hq500m/native/build.sh
python3 -m hq500m demo --engine paged --kernel native \
  --event-kernel native --lif-kernel native --max-pages 128
~~~

These native knobs are independent. For CPU source generator:
--kernel python/native/auto; for ordered event reducer:
--event-kernel python/native; for dense-page LIF:
--lif-kernel python/native.

The default for ALL kernels is Python. Selecting --kernel auto
only checks whether the compiled native shared library exists;
it is NOT a performance-sensitive adaptive runtime.

An external workload with 32,768 forced source IDs must explicitly
opt into lab_max_pulses=32768 in Python (or --lab-max-pulses 32768
for paged CLI constructors). The ordinary public step API still
limits injected laboratory source pulses to 8,192.
No arbitrary lab-pulse HTTP endpoint was added.

~~~sh
python3 benchmarks/fusion_r06_bench.py --large --repeats 2
~~~

The large test is memory/time bounded, not recommended on tiny hosts.
It stores many cold states in RAM and never silently drops target IDs.
No package installs, live service restarts or modifications to the
original HQ500M/GPU BitWeave models were required on mirbi-linux.

## Reproducible native vs Python test (full neural step)

Same machine, two LIF ticks, learning OFF, original 32 C5 edges,
no artificial fanout, 1024 logical page capacity, original
native C5 edge generator on both sides. Source pattern:
500000+i*12941, amplitude 2.0, only first tick.
Each mode is the median of **two** full-step wall-clock timings.
Both cases passed EXACT equality on ALL non-backend telemetry.
Measurements exclude construction and are host-specific.

| Directly driven spikers | Unique membrane-integrated IDs | C5 events delivered | Event/LIF Python, s | Event/LIF native requested, s |
|---:|---:|---:|---:|---:|
| 8,192 | 270,285 | 262,144 | 1.313 | 1.472 |
| 32,768 | **1,080,623** | **1,048,576** | **7.253** | **7.482** |

The native event reducer currently spends extra time converting
Python event tuples into C arrays. At this low density native
batched LIF does not activate at all. Hence the complete C99
event/LIF path did NOT show acceleration for this workload.
Do not advertise a speedup that has not been demonstrated.

The benchmark process peak RSS was 608.7 MiB across both backends
and repeated runs. This is not the isolated model memory; resident
CPU pages and cold states occupy a smaller subset.

Raw data: artifacts/fusion_r06_bench.json
Source: benchmarks/fusion_r06_bench.py

## Correctness and guardrails

- All existing R05 checkpoint states remain readable in default lab
  mode, with the new lab_max_pulses field defaulted to 8192.
  A checkpoint created at 32768 capacity must be restored with
  the same explicit lab limit.
- The C99 reducer expects already sorted events; exact Python
  accumulation ordering for repeated targets is reproduced.
  The C function rejects invalid target bounds, unsorted targets
  and oversized buffers.
- The batched native LIF uses numeric binary64 state and returns
  the same voltages, refractory clock, spike flags and last-update
  values as Python in random tests at thresholds 0.25, 0.35, 1.0, 1.7.
- Cross-backend whole-state parity is verified for independent
  sparse/dense recurrent circuits, with learning ON/OFF,
  local plasticity ON/OFF, and state checkpoint restoration.
- The 32768-pulse large mode is opt-in, capacity guarded by
  max_events and max_tracked; the original safe default remains.
- Newly differentiated telemetry: unique_updated_neurons means
  distinct IDs RECEIVING input; unique_membrane_integrated_neurons
  means distinct IDs actually integrated after refractory skips;
  refractory_event_skips is number of skipped events (not unique IDs).
- Native LIF input counts and integration counts are separate;
  no GPU acceleration or training has been claimed.

## Next major speedup: C-owned state, not more FFI loops

Move active 1024-ID page voltage / refractory state to a compact
native arena, reduce and integrate event batches WITHOUT repeatedly
materializing Python tuples. Preserve page eviction, exact global
ID routing, synaptic plastic deltas and checkpoint interchange.
Then benchmark native event queue and sparse vs packed kernel crossover
against this R06 baseline. Only if proven faster should any native
mode replace the default.
