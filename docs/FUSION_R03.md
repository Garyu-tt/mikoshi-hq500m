# HQ500M x BitWeave Fusion R03 — measured CPU improvements and intrinsic activity

Status: experimental CPU implementation, 2026-11-08. No CUDA build,
native C/C++ compilation, trained LLM or verified human connectome.

This extends R02 exact-ID page routing, without changing the
500,000,000-neuron virtual address generator, original 32 potential C5 edges
per neuron or their signed strengths.

## Implementation

1. New hq500m/c5_fast.py generates all 32 exact signed C5 outgoing links
   in one pass when a source neuron fires. Source hash, region and polarity
   are calculated once instead of once per slot. Results are memoized
   with a bounded per-source LRU cache of 8,192 entries. All 32,512
   sampled source/slot pairs (including region transitions and last ID)
   reproduced the unchanged HQ500M C5 oracle exactly.
2. page_engine.py no longer loads each target module merely to collect
   incoming event currents, only to integrate its state. Sorted neurons
   belonging to the same 1,024-address page reuse the loaded page state.
   This avoids redundant LRU operations, saving CPU and page churn.
3. Runtime returns directly_driven_neurons, unique_undriven_spiking_neurons,
   spikes_per_tick and undriven_spikes_per_tick. These are actual LIF
   threshold crossings, not synthetic fanout and not mere resident addresses.
   No synthetic network was silently added to HQ500M.
4. Correctly reports 256 valid addresses for the last incomplete virtual
   1,024-address page (rather than counting the nonexistent 768).
5. Old game-port API, per-ID C5 address semantics, in-RAM cold pages,
   checkpoint/restart and bounded remote plastic synapse multipliers are
   preserved. No old checkpoints are overwritten.

## Reproduce

Requires only Python 3.11+, standard library:

~~~sh
python3 -m hq500m demo --engine paged --max-pages 1024 --ticks 4
python3 -m unittest discover -s tests -v
python3 benchmarks/fusion_r03_bench.py --sources 1024 4096 8192 --trials 3
~~~

Direct API to observe intrinsic C5 signal propagation:

~~~python
from hq500m import PagedBrain
brain = PagedBrain(max_pages=128, ticks=24, learning=False)
result = brain.step({}, {1_048_576+i: 2.0 for i in range(512)})
print(result["spikes_per_tick"])                # [512, 79, 4, 0, ...]
print(result["unique_undriven_spiking_neurons"])  # 83
~~~

In this test 512 adjacent source cells receive a single external pulse.
No sensory broadcast is used; subsequent spikes in unforced IDs arise from
original C5 synapses. The cascade extinguishes after a few ticks; this
is not ongoing autonomous neural dynamics or learned behavior.

## CPU profile, same test R02 versus R03

Host: mirbi-linux (32 vCPU virtual Xeon E5-2660 v4).
Single Python process per code version, three repetitions per source count;
median of step wall-clock measurements after construction. The source
ID set is deterministic: 500000+i*59771, amplitude 2.0 on tick one,
two LIF ticks, 1,024-page capacity, plasticity disabled. Any spiking
here is externally forced. R02 results use the original R02 local
code path; R03 uses fused source-edge generation plus lazy page load.

| Forced source spikes | Actually updated distinct cells | R02 median seconds | R03 median seconds | Speedup |
|---:|---:|---:|---:|---:|
| 1,024 | 33,791 | 0.1376 | 0.0959 | 1.43x |
| 4,096 | 135,162 | 0.6817 | 0.4532 | 1.50x |
| 8,192 | 270,294 | 2.4382 | 1.1267 | 2.16x |

All 32 original signed C5 synaptic impulses per spike are delivered,
including 8 long-range connections, with zero silently dropped remote
events. The reported times include Python LIF stepping, exact C5
generation, event routing and CPU page scheduler; exclude process
startup and Python memory initialization. Warm cache and CPU contention
can change ratios. These are microbenchmarks, not guaranteed on other
computers; not GPU, not tokens/s, not a trained model.

Page loads for 8,192 inputs fell from 137,730 to 68,865; exact ID and
neural event counts matched.

## Intrinsic C5 propagation diagnosis

With each of five distinct source modules, a single pulse to 512
adjacent source neurons (24 ticks, learning disabled, 128-page capacity)
caused unforced neurons to fire:

| Source module first ID | Additional unique firing cells | First ticks total spike counts |
|---:|---:|:---|
| 1048576 | 83 | 512 / 79 / 4 |
| 1049600 | 84 | 512 / 78 / 6 |
| 1050624 | 125 | 512 / 108 / 17 |
| 2011136 | 119 | 512 / 105 / 14 |
| 469999616 | 115 | 512 / 112 / 3 |

These are real C5 local propagation, not synthetic broadcast, but
all tested spontaneous cascades died out after tick 3. Sparse
long-range paths rarely receive enough coincident input for downstream
targets to reach threshold. Sustained large-scale useful dynamics and
generalization remain unproven.

## Validated scope

24/24 baseline + R02 + R03 unit/integration tests pass, including
memory checkpoint replay, actual target identity, learning disabled
control, page eviction/restoration, C5 oracle equivalence, last virtual
page geometry, per-tick counts and native C5 signal propagation.

Distinct counting: Virtual = addressable (500M); logically resident
= currently mapped page addresses; updated = received input and
integrated voltage within the current game step; firing = crossed
threshold; unforced firing = fired without direct sensory pulse in this
step (can include legitimate bridge or residual prior activity).

## Remaining architecture gaps

- Currently the high-sparsity C5 ensemble benefits from event scatter;
  CUDA BitWeave's structured binary GEMM is not a drop-in replacement.
  A true adaptive kernel must benchmark dispatch crossover including
  page assembly and transfers before choosing packed matrix operations.
- Python routing, exact-ID cold state serialization and sort are still
  major bottlenecks. This host has no C/C++ compiler installed; no
  native kernel was built or claimed.
- Current network does not sustain widespread self-driven spikes under
  small cues. Next research must test wiring/density, controlled
  excitability and learned pathway recruitment, without substituting
  artificial high-fanout stimulation for useful cognition.
- A million simultaneously updated and behaviorally useful neurons
  with demonstrated learning remains a future goal. The largest R03
  test updated 270,294 cells under external input, and only 8,192 fired.
