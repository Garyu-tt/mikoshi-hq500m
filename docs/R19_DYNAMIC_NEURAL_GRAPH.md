# R19 — Deterministic procedural ID graph for the HRA brain stencil

2026-11-08. This release builds on R18 without replacing or modifying its
source anatomy, original 283 HRA meshes, V5 approximate interior anchors,
or any of the older HQ500M R11/R13 Q0.8 assets.

## Main result

A virtual neuron address can be resolved to one of 283 anatomical reference
regions and a deterministic spatial proxy without storing one record per
neuron. The address is relative to the configured total population.

The page supports exact total populations between 1,000 and 1 trillion
synthetic neurons. It generates allocations using the R18 model
that fixes biological broad-category guidance to about 69.03B
cerebellar, 16.34B cortical and 0.73B other neurons at 86.1B.
Fine anatomical region counts are derived from an approximate
HRA/V5 volume-cell distribution, NOT measured counts per structure.

Quotas are recomputed on changing the total; existing global neuron
addresses are invalidated and selections cleared. The R19 namespace
is distinct from old R11 Q0.8 IDs. At fixed total N, an address and
its outgoing edges remain unchanged across any GPU LOD setting.

## Spatial locality

1. Each of the region's volumetric HST8 reference cells is ordered by
   10-bit xyz Morton spatial key, generated lazily and cached.
2. Virtual neuron local ordinals map to those reference cells in
   monotonic spatial order, with deterministic sub-cell variation.
3. No billions of neuron XYZ positions are allocated or stored. Each
   queried neuron XYZ is a purely procedural display proxy based on
   HRA/NeutralLab anatomical stencil coordinates. Not a measured soma.
4. Selecting an address displays only its bounded reachable subgraph.
   With no selected neuron, outer region shells are visible, while
   all interiors remain hidden. Selected inner regions can be revealed
   independently with the existing R18 region selector.
5. For a very close pair of neurons, focus camera provides a *local
   magnification lens* without modifying anatomical source positions.

## Connection generator

Each neuron has directed synthetic outgoing edges generated on demand:

- Up to five region-local targets, using ordinal strides of 1,
  1x, 2x, 7x, 17x of estimated neurons per anatomical stencil cell.
- A sparse conditional (about one in eight ID hashes) adds up to two
  projection edges to a nearby, soma-bearing HRA region. Nearby means
  Euclidean **atlas tissue centroid** distance, NOT measured synaptic
  likelihood, neural connectivity or a validated axonal route.
- Duplicate/self edges are removed. All target IDs are kept inside
  the selected virtual population.
- Bounded directed breadth-first search computes an ID-to-ID path up
  to four hops and 1,800 visited IDs, or a selected source's entire
  bounded exploration tree (192 nodes desktop, 88 mobile).
- No full graph adjacency is materialized, downloaded or persisted.
  Showing links from the main "Synthetic links" control now uses the
  same stable ID-based directed graph, rather than joining random
  pairs of already visible GPU points.

HRA reference tissue, region-center proximity and synthetic graph
parameters do NOT determine actual synaptic anatomy. Tract mode remains
a separate HRA white-matter centerline **illustration** using a subset of
V5 scaffold cells; it is not reconstruction of an axon's morphology.

## Interface

- Logical total neuron count (500M, 8.6B, 86.1B or custom).
- GPU point budget independent of synthetic total neuron addresses.
- Search 283 named anatomical regions; reveal region interiors;
  hide, dim or show exterior context.
- Choose synthetic links or trace named white-matter structures.
- Input a neuron ID and bounded BFS depth 1-4.
- Optional target neuron ID for directed path search. A no-result
  within a bounded search does NOT prove a global path is absent.
- View/clear isolated subgraph and automatic center/magnification.
- Inspect exact ID and outgoing edges through the browser API:
  window.ProceduralAtlasR18.resolveNeuronId(id)
  window.ProceduralAtlasR18.outgoingNeuronIds(id)
  window.ProceduralAtlasR18.walkNeuronIds(id, depth)
  window.ProceduralAtlasR18.findPath(source, target, maxDepth)
  window.ProceduralAtlasR18.getGraph()

## Verified tests

- Full desktop WebGL2/SwiftShader browser QA with no page/console errors.
- Total 500,000,000: ID 42 depth-2 yields 32 selected virtual neurons
  and 42 directed synthetic edges; depth-3 yields 93 vertices and 168 edges.
- An optional direct target ID 43 yields a two-node/one-edge chain
  from ID 42, and camera magnification renders both distinguishably.
- XYZ and outgoing adjacency unchanged when reducing point LOD.
- Total 86,100,000,000: logical allocation exact, final ID
  86,099,999,999 resolves correctly, and bounded graph search works.
- Total 1,000,000,000,000: final ID resolves with in-range target IDs.
- Corpus callosum sample track shows 564 illustrative segments.
- Mobile panel, source/target inputs and R19 controls tested.
- R18 original stencil SHA256, HRA/Allen provenance and older
  HQ500M point/fiber checks remain unchanged.

## Reconstruction required for genuine connectomics

An actual 86-billion-neuron biological connectome with neurons,
axons and synapses needs morphological reconstructions, source
biology, synaptic evidence, cell-type-dependent density and
substantial external indexed adjacency storage. R19 is deliberately
*synthetic* and does not assert this evidence exists.

References and attribution:
- HRA/Allen human brain v1.3, CC BY 4.0:
  https://3d.nih.gov/entries/3DPX-020960?version=1
- Azevedo et al. 2009:
  https://pubmed.ncbi.nlm.nih.gov/19226510/
- Stencil implementation and provenance:
  docs/R18_PROCEDURAL_NEURAL_ATLAS.md
