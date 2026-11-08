# R18 Procedural Neural Atlas, 2026-11-08

The HRA/Allen brain atlas is used only as an anatomical stencil.
The new procedural 3D scene renders no atlas mesh directly. Instead it
creates point sprites deterministically on demand from source-backed
region surfaces and approximate volumetric cells.

The source has 283 named HRA meshes (CC BY 4.0), 110,404
NeutralLab R04 estimated V5 volumetric slots, and 78,091 newly sampled
HRA triangle-surface points. These are stored as a compact gzipped
HST8 binary: magic, u32 version, u32 region count, u32 record count,
8-byte source records (three u16 xyz + one u16 region). They are
spatial templates, not measured individual neurons.

The browser calculates virtual regional counts at runtime using
an 86.1B reference: cerebellar ~69.03B, cerebral cortical ~16.34B,
remaining brain regions ~0.73B. For each broad tissue category,
R18 distributes quota to individual HRA meshes in proportion to
the number of registered V5 volume cells. These individual mesh
quotas are estimated allocation priors; they are NOT measured
region-specific neuron counts or source biological neuron densities.
Axonal white matter pathways and cavities receive no soma quota.

Select total (500M, 8.6B, 86.1B, custom) to recompute all 283
region quotas using largest-remainder integer apportionment.
The sum always matches the requested total, with no 500M/86B array.
Visible samples are limited by a target-dependent GPU LOD and
user-adjustable cap. Inactive region interiors are never drawn;
a selected region reveals its sampled interior and surface while
other surface regions can be hidden, dimmed or shown.

Connections mode draws deterministic illustrative links between
sampled points only; these are synthetic, not reconstructed axons
or actual synapses. Tract mode uses named HRA white matter regions
and draws shape-guided schematic longitudinal traces through
their estimated V5 volume cells. This is NOT a reconstructed
corticospinal or any other verified biological neuronal pathway.
The existing Q0.8 graph and Neural Path Explorer stay unchanged
and accessible from the original viewer.

HST8 source and generated assets:
- docs/assets/hra_procedural_stencil_r18.bin.gz
- docs/assets/manifest_r18.json
- docs/procedural/index.html
- docs/procedural/procedural_r18.js

Rebuild and validate on mirbi-linux:
    python3 tools/build_r18_procedural_stencil.py
    python3 tools/test_r18.py

HRA geometry provenance:
https://3d.nih.gov/entries/3DPX-020960?version=1
CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
Reference aggregate neuron counts:
https://pubmed.ncbi.nlm.nih.gov/19226510/

Original HRA GLB, V5 registration, Terrie HQ500M point cloud, and
R11 Q0.8 fiber geometry remain byte-for-byte unmodified.

Any logical neuron ID within the configured total can be resolved on
demand to a deterministic region ID and a generated spatial proxy
using ProceduralAtlasR18.resolveNeuronId(id). The ID namespace is
R18-specific and its global ranges change with the configured
total, so it must NOT be confused with original Q0.8 IDs.
