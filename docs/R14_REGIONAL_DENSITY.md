# HQ500M R14 — regional density display (2026-11-08)

R14 is a **reversible visual layer** over Terrie's source point cloud (CC BY 4.0). The existing R13 .bin.gz source with its 1,192,673 positions, colors, sulcal marks and stable seeds is unchanged. The R11 sampled Q0.8 neural-address fiber file is unchanged.

## Why

Humans have ~86.1B neurons, of which ~69B are cerebellar, ~16.3B are cerebral cortical, and ~0.8B are in other brain structures (Azevedo et al., 2009; Herculano-Houzel, *Front Hum Neurosci*, 2009: https://pmc.ncbi.nlm.nih.gov/articles/PMC2776484/). The cerebellum accounts for ~10% of brain mass yet ~80% of neurons. An equal-radius grid cannot illustrate this contrast.

## What is implemented

- Sidecar `docs/assets/hq500m_region_density_r14.bin.gz` and lite equivalent, byte 0 = tentative region id and byte 1 = local 96-grid occupancy proxy. It overlays the **original** R13 positions rather than moving or resampling them.
- Region IDs: 0 cortex candidate, 1 cerebellum candidate, 2 brainstem candidate, 3 deep structure candidate.
- WebGL2 per-vertex glyph radius scales inversely with local crowding and a region-specific biological density guidance. UI slider adjusts presentation; region palette and cerebellar emphasis are selectable.
- Optional illustrative GPU instances add subvoxel visual samples **inside** the existing cloud near the provisional cerebellum; the original anchor remains untouched. These instances are neither real neurons nor persistent virtual IDs.
- Existing 500M synthetic address space, edge ID pairing, original R11 fibers and simulator are unchanged. No new 86B simulator has been created by this visualization.

## Anatomical qualification

**Caution:** The original point cloud is not accompanied by medically validated region labels, subject MRI, orientation metadata, or a verified presence/extent of the separate cerebellum. Current assignments assume Y up and positive Z posterior, use crude geometric envelopes, and are marked `candidate`. The point-cloud shape is not proof of actual cerebellum. Counts in this R14 sidecar are **renderable proxy points**; the 69B/16.3B literature values guide on-screen glyph size rather than imply the counts are instantiated.

A scientifically accurate revision requires a registered volumetric atlas (e.g. FreeSurfer, MNI or comparable), a verified cerebellum surface, consistent affine orientation, and segmentation confidence per point. If the Terrie geometry excludes a cerebellar mesh, preserving source geometry strictly means we **must not fabricate that missing organ**; use an independently sourced anatomically registered brain geometry as a separate optional LOD.

## Rebuild and QA

```sh
python3 tools/build_r14_anatomical_density.py docs/assets
python3 tools/test_r14.py
```

Inputs: existing R13 compressed positions; `build_r14_anatomical_density.py` uses only the Python stdlib. Nothing overwrites R13 source. License: original Terrie point cloud CC BY 4.0. 

