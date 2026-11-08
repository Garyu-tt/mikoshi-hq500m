# Fusion R07: opt-in 4-branch dendritic proxy

Date: 2026-11-08. This experimental R07 patch adds a lightweight
four-branch dendritic state to the exact-ID event-driven PagedBrain CPU
mode only. It is not a reconstructed human pyramidal cell, a measured
connectome, a biophysical NMDA model, or a demonstration of cognition.

## Design

- Each touched neuron keeps soma membrane voltage, last-integrated tick,
  last-firing tick, and four bounded signed branch potentials.
- 32 original C5 outgoing synapse slots map deterministically to four
  proxy destination branches (slots 0..7, 8..15, 16..23, 24..31).
  This mapping is a software hypothesis: there are no reconstructed
  target dendritic locations or neurotransmitter kinetics in the C5 graph.
- Branch potentials decay independently (0.60 / 0.60 / 0.68 / 0.78
  per tick), contribute with fixed couplings to soma, and add a bounded
  supralinear coincidence response for locally high excitation.
  Inhibitory synaptic currents are signed and subtract from local
  branch potentials. Direct synthetic game sensors and reward bridges
  inject soma current, to preserve functional game IO.
- Refractory input is discarded as before. Spikes hard-reset all four
  branch potentials. Sparse event scheduler only integrates targeted IDs,
  so 500 million addresses remain VIRTUAL, not materialized.
- Existing C5 targets, weights, delays, remote routes and plasticity
  remain unchanged. Four branches increase CPU and checkpoint costs
  per touched cell, not the nominal size of the virtual address space.

## Run

    python3 -m hq500m demo --engine paged --dendrites
    python3 -m unittest discover -s tests -v

Python is required for the LIF compartment integration path: native C99
LIF is rejected while --dendrites is enabled (no silent fallback).
Native C5 edge generation is still an independent optional backend,
and native ordered event reduction can still run, but routing to
branches occurs in Python. No claim of speedup.

Legacy non-dendritic checkpoints load normally in legacy mode. A new
checkpoint with dendrites=True must load in a dendrite-enabled engine;
cross-mode restores raise a geometry error. The original checkpoint
schema name remains unchanged and gains the explicit optional
dendrites flag plus four branch potentials in each occupied neuron row.

## Future research

Replace synthetic slot partitions by target-specific morphology and
synapse coordinates, empirically fit coupling/branch decay, and add
separate receptor/channel state only where justified by observations.
Bench realistic workloads before contemplating a default-mode change.
