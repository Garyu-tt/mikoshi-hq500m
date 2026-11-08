# HQ500M x BitWeave Fusion R02 — exact-address CPU page scheduler

Status: **experimental CPU-only prototype; no trained model, no CUDA port**.
Date: 2026-11-08.

This is additive to the existing public HQ500M Python CPU demo and the optional
BitWeave-inspired fixed-window R01 engine. The old modes remain unchanged.

## Run

Python 3.11+, standard library only:

~~~sh
python3 -m hq500m demo --engine paged --max-pages 128 --ticks 4
python3 -m hq500m demo --engine paged --max-pages 1024 --ticks 4
python3 -m hq500m jsonl --engine paged --max-pages 128
python3 -m unittest discover -s tests -v
~~~

Exact-address external pulses, only in the Python API:

~~~python
from hq500m import PagedBrain
b = PagedBrain(max_pages=128, ticks=2, learning=True)
out = b.step({}, {1_048_577: 2.0})
print(out["synapses_evaluated"], out["synapses_delivered"],
      out["remote_synapses_delivered"], out["unique_updated_neurons"])
b.save("checkpoint.json")
b2 = PagedBrain(max_pages=128, ticks=2, learning=True)
b2.load("checkpoint.json")
~~~

Existing named game sensors and motor output schema are preserved. External
pulses are an explicit laboratory stimulus; the HTTP/JSONL API accepts only
the original named sensory observations, not arbitrary pulses.

## Implemented

- Globally addressable neuron IDs 0..499999999. The exact 32 original C5
  procedural outgoing edges (24 local + 8 projected) are evaluated only when
  a neuron spikes, with original signed weights; fixed-window mod/remap is
  NOT used.
- Ordered LRU manager for exact global pages of 1,024 addresses, with 7
  fixed functional interface pages and a capacity of 8..1,024 pages.
- Real delivery of remote C5 events to the exact target ID. An absent page
  is logically loaded, and evicted page state is preserved in an in-RAM cold
  dictionary. No remote event is silently discarded at page boundaries.
- Lazy, event-driven toy LIF updates preserve inactive membrane voltage by
  applying analytic decay on next touch. No dense scan of 500M addresses.
- Signed floating-point C5 gains stay intact; learned changes are separate
  per-(source global ID, original C5 slot) bounded multipliers. Toy causal
  pre/post plasticity is implemented **only** for positive remote C5 edges;
  a no-learning control remains supported.
- Deterministic sort of delivered events, pending queue carried across steps,
  versioned save/restore including hot/cold pages, pending exact-ID events,
  plastic weights, traces, named game policy, and clock.
- No artificial high-fanout sensory broadcast in the paged engine.

The earlier BitWeave fixed-window engine is separate: fixed windows with
packed 1024-bit spike masks and optional explicitly artificial broadcast.
Paged mode uses event-scatter and lazy LIF; it has not incorporated the CUDA
BitWeave R04 binary/ternary GEMM kernel, nor a device-measured automatic GEMM
crossover. These algorithms are NOT proof of human-like cognition.

## Real measurements (2026-11-08)

A single CPU-only Python process on a host reporting 32 vCPUs,
Xeon E5-2660 v4. One step of 2 LIF ticks, manually injected pulse 2.0
into each of N *distinct global IDs* distributed throughout the 500M
address space. All links are generated from C5; NO synthetic fanout.
Times are a short single-run microbenchmark, not repeat-trial medians.
Resident neurons reports logically loaded 1,024-ID pages; it does
NOT mean every resident address was updated or had a membrane allocated.

| Page budget | External source pulses | Logical resident IDs | Unique updated neurons | Unique spiking neurons | C5 delivered (8 remote each) | Step seconds |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 128 | 8,192 | 4,224 | 128 | 4,096 (1,024 remote) | 0.0339 |
| 128 | 128 | 131,072 | 4,224 | 128 | 4,096 (1,024 remote) | 0.0159 |
| 1,024 | 128 | 1,048,576 | 4,224 | 128 | 4,096 (1,024 remote) | 0.0145 |
| 1,024 | 512 | 1,048,576 | 16,895 | 512 | 16,384 (4,096 remote) | 0.1172 |

A reported million **resident addresses** is *NOT* a million active or
processed neurons! In the largest measured row only 16,895 distinct neurons
were integrated, and only 512 fired (externally driven). This is a correct
baseline for moving toward a million genuinely processed neurons.

Additional single-run **forced-pulse stress** on the same host (two ticks,
1,024-page logical capacity, learning disabled, 32 original C5 outputs
per triggered source):

| Forced source spikes | Unique neurons integrated | C5 events delivered | Remote C5 events | Wall sec | Process peak RSS |
|---:|---:|---:|---:|---:|---:|
| 1,024 | 33,792 | 32,768 | 8,192 | 0.264 | 32.4 MiB |
| 2,048 | 67,583 | 65,536 | 16,384 | 0.410 | 52.0 MiB |
| 4,096 | 135,162 | 131,072 | 32,768 | 0.963 | 92.1 MiB |

All 4,096 spikes above were externally driven. No spontaneous emergence
of 4,096-neuron activity or learning capability has been established.
RSS is for the whole Python process, not a model-only peak.

Original 14 tests + 6 new page routing/plasticity/cold storage tests = **20
PASS** on the host. No unmodified HQ500M, CUDA, BitWeave GPU code or
prior learned checkpoints were overwritten.

## Constraints and follow-up

1. Cold states live in CPU RAM, not on SSD; page residency is a logical
   scheduler, not a fixed-memory GPU cache. Sparse state growth is bounded
   by guardrails, but they raise errors rather than silently discard events.
2. Synthetic C5 wiring (24 local + only 8 projected edges) causes
   weak spontaneous large-scale propagation at low activity. Artificial
   external stimulation is not validated cognition, learning, or life-like
   dynamics. The model is not an anatomical human connectome.
3. CPU PagedBrain event routing currently scans/sorts Python event lists.
   Large brain-wide loads need a native C/C++/CUDA event queue, indexed
   per-page batching, exact-ID cold-state management and a verified
   adaptive switch to packed BitWeave kernels on genuinely dense motifs.
4. Measure meaningful behavior and interference: real sensor-driven
   responses, learning vs off control, cross-region cue-to-readout
   performance, checkpoint continuation, hot/cold fairness, end-to-end
   latency, resident/updated/spiking counts, RSS and power.
5. A true million *processed* neurons per desired wall-clock budget remains
   an open milestone. Do not infer it from 1,024 loaded page slots alone.
