# HQ500M R10 voxel-surface viewer — credits & provenance

- Original geometry: **Brain Point Cloud** by **Terrie Simmons-Ehrhardt**, Creative Commons Attribution 4.0 (CC BY 4.0).
- Original model: https://sketchfab.com/3d-models/brain-point-cloud-c427ea0aee214141a78eba37bf9b76bb
- Licence: https://creativecommons.org/licenses/by/4.0/
- Voxel-shell extraction, Deep Ruby color treatment, interactive WebGL viewer: Garyu-tt / Mikoshi (2026).
- Changes to source: discretized source coordinates into voxel occupancy volumes at resolutions 96³ and 160³; filled tiny gaps, extracted 6-neighbor exterior shell, discarded hidden interior voxels, and derived optional sparse blue curvature highlights. GPU depth testing hides rear surface as the viewpoint changes.
- The exterior visualization is an artistic/procedural derivative of the point cloud, **not** a measured connectome, not a biological brain simulation, and not a display of 500 million independently visible nodes. The 500M virtual neuron addresses and 16B potential edges are separate HQ500M computational design properties.
- Files `assets/hq500m_surface_shell_96.vox.gz` and `assets/hq500m_surface_shell_160.vox.gz` encode 3-D shell occupancy and accent bitmasks, not synapse coordinates.
