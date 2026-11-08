# HQ500M R15 — reversible boundary-aware regional density (2026-11-08)

R15 improves a synthetic visualization **without moving any original
1,192,673 source points**. This is not an 86-billion-neuron simulation,
MRI-based segmentation, or human connectome reconstruction.

## Anatomical status

Terrie's Brain Point Cloud (CC BY 4.0) has no verified MRI orientation,
brain-region metadata or patient-specific atlas. Orthogonal projections of
the source do not prove a separate cerebellum. R14 labels remain schematic
candidates. R15 assigns a per-point **local boundary stability** byte
reflecting agreement of neighboring R14 heuristic labels in a 64-cubed
voxel grid over 3x3x3 cells. It is **NOT anatomical confidence**.
Even perfect geometric consistency does not validate a cerebellum label.

The approximate 69B cerebellum / 16B cortical neuron counts are literature
guidance for stylized density. Rendered points are not measured neurons
and their on-screen disc radii are not physical cell diameters.

## Density-preserving rendering

- The source pass draws the unchanged 1,192,673 vertices once.
- A separate 100,392-vertex candidate-zone VBO is used only for extra
  simulated point glyphs. R14 drew the whole source in every instance
  then discarded most vertices in the shader.
- At 4x, R15 submits ~1,493,849 vertices instead of R14 ~4,770,692.
  At 8x, ~1,895,417 instead of ~9,541,384. These are counts of
  submitted vertices, not measured FPS improvements.
- Extra shader offsets are deterministic and small. No permanent neuron
  IDs or positions are created. Unstable region-boundary replicas are
  suppressed by the user-adjustable geometric stability threshold.
- Glyph radius responds to local occupancy, regional guidance, camera
  distance and instance count, approximately conserving displayed area.

## Provenance and files

R13 XYZ/source accents, original R11 Q0.8 edge endpoints, and R14
annotations are byte-for-byte unchanged. R15 adds:

- docs/assets/hq500m_region_stability_r15.bin.gz: HQA5, little-endian
  uint32 N, followed by N one-byte stability scores in source order.
- docs/assets/hq500m_region_stability_lite_r15.bin.gz: every 4th point.
- docs/assets/manifest_r15.json: checksums, method and unregistered status.
- docs/viewer_r15.js: geometry plus efficient proxy density rendering.
- tools/build_r15_region_stability.py and tools/build_r15_viewer.py.
- tools/test_r15.py for hashes and regression checks.

Rebuild:
~~~
python3 tools/build_r15_region_stability.py docs/assets
python3 tools/build_r15_viewer.py
python3 tools/test_r14.py
python3 tools/test_r15.py
~~~

## Real atlas registration: still required

An anatomical atlas cannot be registered honestly to a shape without
landmarks and known orientation. A future atlas-aligned layer should:

1. Verify that the chosen licensed reference geometry actually contains
   distinct cerebrum, cerebellum and brainstem with documented axes.
2. Use full-brain MNI152 and SUIT cerebellar atlas as references; verify
   registration using landmarks and a documented affine/deformation.
3. Store confirmed region ID, atlas confidence, unmapped regions and
   coordinate transform *separately* from R14/R15 geometric heuristics.
4. Preserve the Terrie point coordinates, avoiding anatomy fabricated
   by silently stretching or deforming the original.
5. Compare segmentation against atlas source and preserve license credit.

References:
- Azevedo 2009: https://pubmed.ncbi.nlm.nih.gov/19226510/
- Diedrichsen SUIT: https://www.diedrichsenlab.org/imaging/atlasPackage.htm
- Terrie CC BY 4.0: https://sketchfab.com/3d-models/brain-point-cloud-c427ea0aee214141a78eba37bf9b76bb
