# HQ500M R12 — Geometric crest highlights and stable point jitter

**Goal:** Replace arbitrary blue speckling with spatially clustered highlights
on convex folds of the original point-cloud geometry, preserving the deep ruby
palette and the exact Q0.8 edge endpoint sample from R11.

## Pipeline

- Source: Terrie Simmons-Ehrhardt, [Brain Point Cloud](https://sketchfab.com/3d-models/brain-point-cloud-c427ea0aee214141a78eba37bf9b76bb), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Input: all 1,192,673 source point positions in the original 19 groups. The R12
  packed XYZ byte fields (3 × uint16) are **bit-identical** to R11. The 520,150
  straight fiber segments (computed from deterministic neural address pairs)
  are **unchanged** from R11.
- Use the previously published 160³ exterior occupancy grid (74,932 exterior
  voxels) to estimate a surface.
- For each surface voxel: a 28-neighbor PCA estimates a tangent plane.
  Estimate convexity from the displacement relative to the local tangent,
  orient it approximately outwards, smooth over the neighborhood graph.
- Combine this signal with exterior exposure (a Gaussian local-surface-density
  estimate). Propagate scores to source points near that surface. Threshold
  conservatively to leave very few bright blue highlights.
- Final mask: 17,683 points with any blue score, **4,179** with strong blue,
  representing **0.35%** of all source points. The mask is a *geometric proxy*
  for convex crests, not anatomical gyrification labels or measured gyri.
- Assign each point a reproducible per-point seed; use it solely in the vertex
  shader to displace the screen-space display position by a small, static jitter
  (default maximum ±0.002535 normalized scene units per axis at slider 39).
  The original 3D coordinates remain unchanged in all data assets.

## Verification

\`python tools/test_r12.py\` — verifies the exact XYZ bytes, R12/lite
subsampling, counts, stable seeds, and spatial clustering of strong-blue
highlights. A sample of 8-nearest-neighbor strong-blue points produced ~24.3%
blue neighbors against a ~0.35% unconditional baseline, demonstrating
non-random spatial clustering (not claiming biological accuracy).

Desktop browser: 1,192,673 points + 520,150 computed edge endpoints.
Touch-screen/mobile defaults to 298,169 source points (every fourth) and
offers a hidden settings drawer plus a camera distance suited to mobile.

## Rebuilding the new geometry

Use Python with NumPy and SciPy in a separate environment:

\`\`\`bash
python -m pip install numpy scipy
python tools/build_r12.py /path/to/brain_point_cloud.glb docs/assets
python tools/test_r12.py
\`\`\`

The public CPU toy release itself **does not require** NumPy or SciPy.
The GLB source is not bundled in this GitHub repository; it remains
separately licensed and attributed as above.

## Accuracy caveats

All 500 million virtual HQ500M neuron addresses and 16 billion potential Q0.8
edges remain virtual mathematical quantities. The scene does **not** show all
16 billion edges or reconstruct actual biological synapses, brain-region
assignment, axons, or gyral tissue. The R11 edge endpoints preserve exact
deterministic address pairs but their 3D placement is synthetic.
