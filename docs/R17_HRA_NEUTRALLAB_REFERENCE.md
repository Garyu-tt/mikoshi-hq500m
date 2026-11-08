# R17 - NeutralLab HRA anatomical reference alongside HQ500M

Verified 2026-11-08. NeutralLab R04 has the HRA/Allen human
reference male brain atlas v1.3, CC BY 4.0, with 283 individually
named anatomical meshes.

Silico Animus Brain V5 is a separate synthetic model. Its 110404
voxel slots were geometrically mapped into 265 of the HRA tissue
meshes (18 cavities excluded). This estimate is NOT measured neuron
segmentation. Five coarse source groups were retained.

The HQ500M R17 viewer adds a searchable list of HRA mesh names,
ontology fields where available and V5 synthetic-slot counts.
Clicking a mesh opens that exact region in the original
NeutralLab three-dimensional reference viewer:
https://neutrallab.infracare-it.com/viewer/

All HQ500M source XYZ and Q0.8 edges are byte-identical. No HRA
transform has been inferred for Terrie's HQ500M point cloud. The
synthetic eight-area render layer R16 remains a distinct option
and MUST NOT be called verified atlas registration.

Build:
python3 tools/build_r17_hra_reference_catalog.py PATH_TO_LOCAL_V5_REGISTRATION_MANIFEST.json docs/assets/hra_reference_catalog_r17.json

Test:
python3 tools/test_r17_hra_bridge.py

Source HRA https://3d.nih.gov/entries/3DPX-020960?version=1
License https://creativecommons.org/licenses/by/4.0/
