# R22: camera-visible synthetic neuron rendering on HRA anatomy

Date: 2026-11-08. This is an interactive synthetic point-cloud viewer, NOT a measured biological connectome.

## Why R21 appeared too crowded

The former R21 generator repeatedly plotted the same sparse surface anchor points and could show far-side neuron proxies through gaps in nearer layers. Increasing GPU point count to 1.1 million made repeated anchors brighter, rather than adding genuinely distinct surface positions.

R22 separates reference geometry, surface sampling and visibility:

1. An invisible HRA/Allen 3D anatomical triangle stencil represents 283 named regions, containing 324,855 source vertices and 656,268 source triangles. It comes from the already-used HRA male human brain v1.3 reference, with original license CC BY 4.0.
2. A camera-dependent coarse depth map is built from the prior 46,543 exterior HRA shell anchors. Triangle centers are compared against the nearest depth in surrounding screen-space bins, excluding strongly occluded source triangles before LOD point generation.
3. A GPU-only HRA depth prepass uses exterior stencil splats to fill the WebGL2 depth buffer WITHOUT drawing the original anatomical mesh as colored geometry. Neuron-point proxies and short synthetic fibers behind that front shell are depth-rejected.
4. Visible synthetic point sprites are newly sampled by deterministic area-weighted barycentric interpolation over eligible HRA source triangles. Thus the 220,000-to-1.1-million GPU point budgets produce many distinct positions without storing millions of points, let alone billions.

A default screenshot of the 500-million logical-neuron model showed 124,764 colored surface pixels versus 150,551 with occlusion disabled in the same test viewport. These are screen pixels, NOT neuron counts. They demonstrate that some obstructed layers are removed while the visible front remains substantially filled.

## User behavior

- The option "Не отображать закрытые нейроны и связи" defaults to enabled.
- When viewing the whole brain, visibility uses the current camera. After rotating the camera or pausing a wheel zoom, GPU point proxies are regenerated for that viewpoint.
- Focusing one region, a chosen neuron or a named tract disables whole-brain occlusion so the selected structures can be studied.
- The GPU counter is explicitly labeled as submitted candidates, not the exact number of pixels or neurons visible after depth testing.
- Synthetic neuron ID addresses, R19 directed adjacency and the underlying 500M/86.1B model quotas remain unchanged.
- The original HRA atlas mesh is used as geometry to sample from but is not drawn as the visible brain surface.

## Binary format and provenance

R22's compressed triangle stream is split into 9 small, exact byte
chunks named docs/assets/hra_triangle_stencil_r22.part00 through part08.
The browser downloads these in parallel, checks byte lengths, concatenates
the gzip stream, then decompresses the complete HTR2 triangle template.
The list of chunk filenames, lengths and SHA256 hashes is in
docs/assets/manifest_r22_triangles.json. The combined gzip stream is
5,006,784 bytes; no giant single-file payload or billion-point array
needs to be stored in the public GitHub repository.

- Header: ASCII HTR2, little-endian uint32 fields for version=1, regionCount=283, vertexCount=324855, triangleCount=656268.
- Data: all quantized normalized uint16 XYZ vertices (three values per vertex), then three uint16 mesh-local vertex indices per triangle.
- Region ranges, source SHA256, license, counts and precise region names are in docs/assets/manifest_r22_triangles.json.
- Decompressed triangle stencil contains approximately 5.89 MB. Compressed storage is approximately 5.01 MB. It contains reference geometry, not materialized virtual neurons.
- Original HRA GLB, existing HST8, Terrie R13 point cloud and Q0.8 R11 fibers remain byte-for-byte unchanged.

Build on the authorized mirbi-linux machine:

    python3 tools/build_r22_hra_triangles.py
    python3 tools/build_r22_hidden_surface.py
    python3 tools/test_r22.py

Browser integration QA:

    python3 tools/qa_r22_browser.py

## Testing and limitations

Local Chromium WebGL2 integration checks confirmed 54,357 eligible candidate triangles in the initial camera and 69,239 after rotating; point budgets of 220,000 at 500M and 1,100,000 in manual 86.1B mode; a 120,000-point mobile cap; selected area, directed neuron ID search and tract modes; and no reported JS/WebGL console errors.

HRA surfaces are legitimate anatomical reference structures, but generated points are NOT measured human neuronal cell bodies. Fine per-region neuron quotas are model estimates. Neuron-ID connections and neurite/tract lines are SYNTHETIC, not traced biological synapses or axons.

Occlusion uses a coarse camera-space visibility estimate plus a finite-resolution depth proxy, not fully watertight exact hidden-triangle geometry. Some folds/silhouette boundaries can show minor artifacts. GPU fragment rejection also does not imply that every vertex was skipped before submission; the CPU generator does skip deeply obscured candidate triangle regions before sampling.

Source attribution:
HRA/Allen human reference brain male v1.3, CC BY 4.0
https://3d.nih.gov/entries/3DPX-020960?version=1
https://creativecommons.org/licenses/by/4.0/

Biological aggregate neuron count context:
Azevedo et al. 2009, https://pubmed.ncbi.nlm.nih.gov/19226510/
