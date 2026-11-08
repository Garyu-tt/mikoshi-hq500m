#!/usr/bin/env python3
"""HRA catalog integration does not confuse anatomical source with HQ500M."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1]
data=json.loads((P/'docs/assets/hra_reference_catalog_r17.json').read_text())
assert data['region_count']==len(data['regions'])==283
assert data['registered_V5_slot_count']==110404
assert data['tissue_regions_with_V5_slots']==265
assert len({r['mesh_name'] for r in data['regions']})==283
assert sum(r['synthetic_V5_slots'] for r in data['regions'])==110404
assert data['atlas_to_hq500m_transform'] is None
assert data['hq500m_ids_mapped_to_regions'] is False
assert data['not_synaptic_connectome'] is True
assert sum('cerebell' in r['mesh_name'].lower() for r in data['regions'])>=12
assert all(isinstance(r['mesh_name'],str) and r['mesh_name'] for r in data['regions'])
assert data['reference_license']=='CC BY 4.0'
r13=json.loads((P/'docs/assets/manifest_r13.json').read_text())
r11=json.loads((P/'docs/assets/manifest_r11.json').read_text())
sha=lambda name:hashlib.sha256((P/'docs/assets'/name).read_bytes()).hexdigest()
assert sha('hq500m_source_points_r13.bin.gz')==r13['full']['sha256']
assert sha('hq500m_exact_fibers_r11.bin.gz')==r11['edge_geometry']['sha256']
html=(P/'docs/index.html').read_text()
js=(P/'docs/hra_reference_bridge_r17.js').read_text()
assert 'hra_reference_bridge_r17.js' in html
for part in ('hra_reference_catalog_r17.json','neutrallab.infracare-it.com/viewer/','searchParams.set("region",r.mesh_name)','hq500m_ids_mapped_to_regions'):
 assert part in js,part
print('PASS R17: 283 human anatomical reference meshes, 110404 synthetic V5 slots; original HQ500M and Q0.8 unchanged')
