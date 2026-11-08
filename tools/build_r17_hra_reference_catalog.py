#!/usr/bin/env python3
"""Build an external-source anatomical reference catalog, without remapping HQ500M.
Input: NeutralLab HRA/V5 registration manifest (not a biological neuronal atlas).
The source is not bundled because it belongs to another project/dataset.
"""
from __future__ import annotations
import json, hashlib, sys
from datetime import datetime, timezone
from pathlib import Path

def build(source: Path, target: Path) -> dict:
    manifest=json.loads(source.read_text())
    assert manifest['atlas_meshes']==283
    assert manifest['point_count']==110404
    regions=manifest['region_catalog']
    assert len(regions)==283
    assert sum(int(r['count']) for r in regions)==110404
    out={
      'schema':'HQ500M/HRA-reference-catalog/R17',
      'generated_at':datetime.now(timezone.utc).isoformat(),
      'reference':'HRA/Allen human reference organ brain male v1.3',
      'reference_source':'https://3d.nih.gov/entries/3DPX-020960?version=1',
      'reference_license':'CC BY 4.0',
      'reference_glb_sha256':manifest['atlas_sha256'],
      'neutral_lab_registration_manifest_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'external_viewer':'https://neutrallab.infracare-it.com/viewer/',
      'region_count':len(regions),
      'registered_V5_slot_count':manifest['point_count'],
      'tissue_regions_with_V5_slots':manifest['atlas_fine_regions_with_at_least_one_slot'],
      'source_voxel_model':'Silico Animus Brain V5 (110,404 synthetic voxel slots)',
      'atlas_to_hq500m_transform':None,
      'hq500m_source_point_positions_modified':False,
      'hq500m_ids_mapped_to_regions':False,
      'not_synaptic_connectome':True,
      'accuracy_limitations':[
        'Atlas has named reference anatomical meshes, not measured neuron identities',
        '110404 synthetic V5 voxel slots are geometrically fitted, not biological neurons',
        'HRA spatial frame cannot be silently applied to Terrie HQ500M point cloud',
        'HRA names in this catalog do not classify any HQ500M source point',
        'Anatomical correspondence to HQ500M requires a separately validated coordinate registration'
      ],
      'broad_groups':manifest['broad_group_source_counts'],
      'regions':[
         {
          'mesh_name':r['name'],
          'label':r['label'],
          'group':r['group'],
          'source':r.get('source','HRA brain male v1.3'),
          'ontology':r.get('ontology'),
          'synthetic_V5_slots':int(r['count']),
          'excluded_cavity':bool(r.get('cavity_excluded')),
          'watertight':bool(r.get('watertight')),
         }
         for r in regions
      ]
    }
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'regions':len(regions),
        'mapped_V5_regions':sum(r['synthetic_V5_slots']>0 for r in out['regions']),
        'synthetic_V5_slots':sum(r['synthetic_V5_slots'] for r in out['regions']),
        'json_bytes':target.stat().st_size,
        'HQ500M_coordinates_changed':False},indent=2))
    return out
if __name__=='__main__':
    if len(sys.argv)!=3:
        raise SystemExit('Usage: python tools/build_r17_hra_reference_catalog.py PATH_TO_V5_REGISTRATION_MANIFEST.json OUTPUT.json')
    build(Path(sys.argv[1]),Path(sys.argv[2]))
