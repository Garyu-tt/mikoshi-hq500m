# R23 experimental: anatomical-surface-adjacent synthetic fibers

2026-11-08. Source: docs/procedural/procedural_r23.js.
R22 remains the verified public release until live WebGL2 browser QA passes.

## Problem addressed

R22 draws 220,000–1,100,000 synthetic point glyph candidates but its
whole-scene ID-directed syntheticEdges function generates at most 2,400 line
segments. That does not show visually dense local connections.

R23 draws short GPU-instanced synthetic display fibers:

1. Sample points on the same 283 licensed HRA/Allen anatomical triangle surfaces
   as R22, with deterministic area-weighted barycentric placement.
2. For each new point, find a previously sampled point attached to one of its
   three HRA mesh vertex IDs within the same region.
3. Connect only when the distance is under 0.035 normalized atlas units.
   No nearest-neighbor links across disconnected mesh folds. Samples lacking a
   local predecessor remain unconnected.
4. Upload 9 floats per edge (start XYZ, end XYZ, color RGB).
   WebGL2 instanced LINE_STRIP with 3 vertices draws a bent midpoint per edge,
   two line segments, without CPU expansion into separate line vertices.
5. Retain R22 coarse camera-space triangle culling and depth-only HRA shell
   pass. Synthetic lines stay depth-tested, hidden backfaces are rejected.
6. Isolated Neuron ID graph and named tract modes retain the R19/R22 behavior.
   Dense display fibers are not Neuron-ID graph adjacency.

This requires no per-neuron disk storage and does not alter HRA source
vertices, Q0.8 fibers, R19 neuron graph, neuron quotas or manifests.

## Validation

- Node 22 JS syntax check passed.
- Node test with actual HRA geometry/manifest and mocked WebGL2 passed.
  This is CPU logic, NOT real GPU shader compilation.
- Default 500M total: 220,000 GPU candidates, 207,097 local synthetic edges,
  12,903 candidates without a preceding local neighbor (94.1% connected).
- On/off control and isolated region 111 passed in Node.
- R18–R22 historic source invariants and triangle/checksum tests can run.
- Real Chromium QA not validated: headless Chromium lacks required system
  graphics libraries in this environment. The optional Playwright script
  tools/qa_r23_browser.py is prepared for the WebGL2-enabled runner.

## Scientific limitations

These are local schematic edges between generated display proxies, not
actual synapses or axons. The 94.1% measures sampled-proxy graph coverage,
not biological connectivity. The viewer does not materialize 500M/86B neurons.

HRA/Allen male human brain v1.3: CC BY 4.0.
See docs/R22_VISIBLE_SURFACE_CULLING.md for source provenance.
