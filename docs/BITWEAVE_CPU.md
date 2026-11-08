# HQ500M x BitWeave-inspired CPU sparse event engine (experimental R01)

This engine is optional. The original CPU playground remains unchanged by default.

## Run

Python 3.11+, standard library only, no CUDA or compiler:

~~~sh
python3 -m hq500m demo --engine bitweave --pages 16 --fanout 16 --ticks 3
python3 -m hq500m jsonl --engine bitweave --pages 32 --fanout 16
python3 -m hq500m server --engine bitweave --pages 16 --fanout 16 --port 8766
python3 -m unittest discover -s tests -v
~~~

Direct Python API:

~~~python
from hq500m import BitWeaveBrain
brain = BitWeaveBrain(pages=16, fanout=16, ticks=3)
result = brain.step({"food": 0.9})
print(result["action"], result["unique_spiking_neurons"],
      result["peak_spiking_in_one_tick"])
~~~

- --pages is the number of resident 1,024-neuron modules per each of seven
  regions; range 1..128.
- --fanout is the number of synthetic sensory broadcast lanes per resident
  module and active input; range 0..64. --fanout 0 disables broadcast, retaining
  only original genome C5 synapses plus existing small game-port bridges.
- The old --cells option affects only the legacy engine.
- Saved state is tied to engine, pages, fanout, ticks and learning mode.
  The BitWeave CPU state format differs from legacy CPU checkpoints.

## What is packed?

- Spikes are packed into 1,024-bit page masks (Python arbitrary-precision
  integers), enumerated by bit scan, summarized with int.bit_count (popcount).
- Only firing neurons generate their original 32 C5 edges, on demand by
  exact global source and slot, retaining the original signed weights.
  Destinations outside the seven resident windows are counted but not
  delivered or remapped.
- Membranes are advanced lazily with the input-free exponential decay;
  idle neurons need not be scanned on each tick.
- The original GPU BitWeave R04 XOR+POPCOUNT **matrix multiplication**
  kernel has NOT been ported directly. This engine is a CPU
  bitset/sparse-event adaptation, not a 100 TOPS CPU claim.

## Crucial distinction: resident != updated != spiking

All 500,000,000 addresses are virtual; 16 billion potential C5 edges are
never stored. Pages designate resident neurons. Only neurons receiving
current are dynamically updated. Only threshold crossings count as spikes.

When --fanout is positive, an explicitly SYNTHETIC distributed sensory
broadcast injects input into each resident page, making more cells fire.
It is NOT an original C5 connection or anatomical circuit. Without fanout,
activity remains limited and is suitable for legacy behavior comparison.
This does not establish meaningful learning, intelligence or biology.

## Reproducible CPU benchmark (2026-11-08)

Host: virtual 32-vCPU Xeon E5-2660 v4 system, single Python process.
One step with {"food": 0.9}, three neural ticks, fanout=16. Seconds
include Python computation; exclude process initialization.

| Pages per region | Resident | Unique spiking | Peak spiking/tick | Unique updated | Seconds |
|---:|---:|---:|---:|---:|---:|
| 16 | 114,688 | 1,819 | 1,804 | 37,877 | 0.322 |
| 32 | 229,376 | 3,610 | 3,596 | 75,326 | 0.618 |
| 64 | 458,752 | 7,196 | 7,180 | 150,112 | 1.286 |

14 original/new tests passed including zero-fanout legacy parity and
checkpoint replay.

## Work remaining

- Most remote C5 edges target nonresident addresses. A demand-paged CPU
  scheduler with cold event queues is needed to route those exact events
  without losing them or inventing shortcut connectivity.
- Validate meaningful associative task performance, learning controls,
  generalization and memory retention, not just spike totals.
- A real CPU BitWeave GEMM port needs a separate bitplane / popcount
  matrix kernel, numeric comparison against a reference, quantization
  controls and end-to-end latency profiling.
