# R16: Smooth region candidates and Neural Path Explorer

Date: 2026-11-08. Terrie Brain Point Cloud, CC BY 4.0.
This is a **synthetic, provisional visualization**. No MRI atlas is
registered and the original point cloud has no certified anatomical
orientation or proven separate cerebellum.

## R14 waterline removed

The R14 rule y < 0.36 and z > 0.50 gave the fake cerebellum a
flat cut-off. R16 replaces it with eight smooth, overlapping spatial
membership weights (Gaussian kernels with mild continuous shape
modulation): frontal, parietal, temporal, occipital, cerebellum,
brainstem, deep-structure and insular candidates.

Every R13 point has 8 uint8 weights summing to 255. Colors are mixtures
of all weights; glyph radius depends continuously on local occupancy,
cerebellar candidate weight and GPU proxy-sample density. The
replication mask is smoothly weighted, not a planar threshold.
Every original XYZ stays byte-for-byte untouched.

The eight region names are only heuristic hypotheses about a shape
whose anatomical orientation is unverified. This is not an MRI atlas.
A real atlas should be added as a separate source-backed layer, with
reference MRI registration, a distinct unknown/unmapped class and
provenance.

## Neural Path Explorer (working synthetic prototype)

**Synthetic Neuron ID mode:** enter any HQ500M 0..499,999,999 neuron
address. The browser calculates 32 exact outgoing Q0.8 targets using
the original R11 deterministic 64-bit routing algorithm. An optional
second ID triggers bounded directed breadth-first search, up to four
hops and 4,096 visited IDs. Missing a path does not prove none exists.
The view can hide, dim, or show the base cloud, focus camera on a path,
and reset to the full brain.

Important: a reverse mapping from all 500M virtual IDs to R11
Morton-sorted original XYZ was not released with R11. Until an
explicit, verified mapping is provided, the browser uses stable
hashed point proxies to draw Q0.8 selected neurons. Q0.8 graph
neighbors are algorithmically exact; their displayed spatial
positions are illustrative and are NOT the original ID-to-XYZ
assignment. A drawn segment must not be interpreted as an axon,
tracked morphological skeleton, or biological synapse.

**Regional projection mode:** given two of the eight candidate zones,
the viewer consults a HQE6 sidecar assigning both endpoints of every
one of 520,150 original directed R11 sampled Q0.8 segments a dominant
candidate region and membership value. It calculates a shortest
route over 8 aggregated region classes and draws selected original
spatial segments. This is a regional adjacency preview, not a
guaranteed continuous path through individual neuron IDs. Up to 8,000
desktop or 2,800 mobile segments are drawn at once. No invented
intermediate synapses or axons are injected.

A true neuronal path explorer will require actual neuron ID-to-XYZ
mapping, directed indexed synaptic graph, real SWC skeletons or
equivalent morphologies, and verified tract labels. Those are not
provided by this proof of concept or our 86B high-level goal.

## Data and reproducibility

- Original R13 HQP3 geometry unchanged (1,192,673 points).
- Original R11 HQF3 synthetic fiber geometry unchanged (520,150
  displayed Q0.8 segments; 16B theoretical edges in entire graph).
- R16 HQW6 full+lite sidecar: 8 weights per point; each sums to 255.
- R16 HQE6 sidecar: 4 bytes per directed R11 segment (from region,
  to region, from weight, to weight).
- SHA256 manifests contain original source checks and output hashes.
- Q0.8 test vectors ensure JS routing agrees with authoritative R11
  target_of for three IDs across different partitions.

Rebuild commands:

    python3 tools/build_r16_soft_regions.py docs/assets
    python3 tools/build_r16_fiber_regions.py docs/assets
    python3 tools/build_r16_viewer.py
    python3 tools/test_r14.py
    python3 tools/test_r15.py
    python3 tools/test_r16.py
    python3 tools/test_r16_explorer.py

Scientific context:
Azevedo et al. 2009 https://pubmed.ncbi.nlm.nih.gov/19226510/
Terrie original https://sketchfab.com/3d-models/brain-point-cloud-c427ea0aee214141a78eba37bf9b76bb
License https://creativecommons.org/licenses/by/4.0/
