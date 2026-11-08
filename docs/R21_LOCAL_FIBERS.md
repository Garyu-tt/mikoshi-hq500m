# R21 — Depth-aware local fibers and denser cortical point coverage

Date: 2026-11-08.

This change corrects two visual artifacts of the R20 procedural
HRA-stencil model: long straight chord-like lines crossing the whole brain,
and a visibly loose point shell when rendering at normal camera distance.

## What changed

1. In the ordinary whole-brain "Local connections" mode, draw only
   within-region synthetic directed neuron-ID edges whose endpoints
   are at most 0.067 normalized HRA-frame units apart. When one region
   is selected, the local cutoff is 0.095 units. Distances are between
   the actual generated R19 display proxies, not inferred axonal distances.
2. The edges are drawn as 3–6 short gently curved segments with
   deterministic transverse perturbation. They are visualization curves,
   *not reconstructed neuronal processes*.
3. Normal scene connection lines now obey the point-cloud depth buffer,
   so hidden/background portions do not show through foreground tissue.
   Isolated ID paths and individually requested tract previews remain
   highlighted in front, so the user can inspect them.
4. The ordinary whole-brain link mode explicitly excludes
   cross-region projection edges, because long unverified edges
   otherwise dominate the anatomy. These existing directed *synthetic*
   projection links remain addressable through the R19 selected-neuron
   explorer. Named schematic tract mode is also preserved.
5. Main scene local fiber complexity is bounded to roughly 2,400
   short line segments (or fewer when the source graph lacks nearby
   neighbors). This is a GPU draw budget, not a biological synapse count.
6. Point-glyph minimum size increases slightly and adapts to LOD, to
   make dense surface regions read as continuous tissue without adding
   or saving 86 billion physically located neurons.

## Preserved from R18–R20

- Every one of the 283 HRA source region definitions, registered V5
  interior stencil cells and source-derived geometric shell points.
- The R18 compressed ~823 KiB anatomical HST8 stencil and source checksums.
- 500M / 8.6B / 86.1B virtual populations and per-region estimated quotas.
- The R19 exact procedural ID resolver and synthetic directed adjacency.
  **Neuron IDs and their neighbors are not changed by R21.**
- The separate selected-neuron bounded graph viewer and its camera zoom.
- Adaptive GPU point LOD: 220,000 auto for 500M, 682,889 auto for 86.1B;
  1.1M desktop manual maximum and 120,000 mobile maximum.

## Validation

The local browser WebGL2/SwiftShader QA verified:

- 500M: 220,000 GPU points, 2,402 local line segments.
- 86.1B: 682,889 GPU points, 2,400 local line segments.
- Isolated 86.1B neuron graph: 31 vertices and 42 directed synthetic
  connections, unaffected by the whole-brain local fiber filter.
- Named tract mode: 564 schematic sample segments.
- No page JavaScript or WebGL console errors.
- Screenshot: docs/images/r21_local_fibers.png

**Scientific caution:** Neither the original synthetic R19 graph nor
this visual smoothing reconstructs biological axons, dendrites, synaptic
strengths or true neural path topology. HRA/Allen coordinates supply
reference gross anatomy, not a measured connectome. Per-region neuron
quotas remain estimates derived from broad-category literature and
a coarse registered V5 volume proxy.
