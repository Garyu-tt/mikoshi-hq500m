# R20 — High-density dynamic neuron GPU level of detail

Date: 2026-11-08.

R20 makes the **R18 anatomical-stencil-based synthetic neural point
visualization substantially denser**, without increasing the logical neuron
population or storing new anatomy. It retains the R19 directed virtual
ID/connection explorer, region interior isolation and schematic HRA tracts.

## What changed

* The automatic visible-point budget is `round(220000 * (N / 500000000)^0.22)`,
  limited by the user-controlled GPU maximum, the logical population and a
  device-class cap. Default user maximum is 800,000.
* At N = 500,000,000 the browser displays **220,000 points**; the former
  R18 scene displayed 24,000. At N = 86,100,000,000 the browser displays
  **682,889 points**, vs 101,461 in R18.
* "Manual" switches the slider to a real override, rather than an upper
  bound on a much smaller hidden automatic point budget. Verified manual
  rendering reaches **1,100,000** GPU point sprites on a desktop browser.
* Coarse-pointer/mobile devices are capped at **120,000**, including
  manual mode. There is no guarantee every device meets a target frame rate.
* Point radius scales down moderately with increasing displayed density,
  with minimum size guarding visibility. This produces a more continuous
  cortical visual surface at higher resolution.
* R19's neuron ID positions and directed graph neighbors remain invariant
  under LOD changes for a fixed total N. When isolating a neuron path,
  only the requested small subgraph remains drawn (when background is
  hidden); even the million-point manual setting cannot force unwanted
  background points into that view.
* Existing R18/19 files and the HRA/Allen 283-structure source stencil,
  188,495 HST8 records, 110,404 NeutralLab interior cells and original
  HQ500M R11/R13 geometry are unchanged. No biological soma, synapses
  or neurons have been measured or reconstructed by increasing visual LOD.

## Reproducibility

    python3 tools/build_r19_graph.py   # regenerate R19 on a clean R18 page
    python3 tools/build_r20_dense_lod.py
    python3 tools/test_r18.py
    python3 tools/test_r19.py
    python3 tools/test_r20.py

A R20 tree checkout already has R19 JavaScript; rebuilding R20 alone is
idempotent. For a clean rebuild of all UI revisions, regenerate R19 over
the original R18 HTML before running the R20 builder.

Browser E2E via the locally available playwright/SwiftShader browser:

    python3 tools/qa_r20_browser.py

R20 browser checks:
* 500M automatic budget exactly 220,000;
* 86.1B automatic budget exactly 682,889;
* manual maximum 1,100,000;
* mobile cap 120,000;
* full synthetic graph isolation at maximum LOD;
* same ID 42 coordinate and neighbors across LOD changes;
* zero page JavaScript and WebGL console errors.

## Important interpretation

Virtual N is a **logical allocation**, not a fully instantiated neuron
simulation. Increasing the number of displayed point sprites does
not alter the number of virtual IDs or reconstruct real neurons or
measured synaptic connections. Fine regional quotas remain model-based
estimates using HRA geometry and approximate NeutralLab V5 volume
references; there are no biological cell-by-cell positions here.

HRA source: https://3d.nih.gov/entries/3DPX-020960?version=1
HRA/Allen license: CC BY 4.0.
