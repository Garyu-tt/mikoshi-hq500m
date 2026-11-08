#!/usr/bin/env python3
"""Compact exact-source HRA triangle sampling stencil, no rendered HRA mesh."""
from pathlib import Path
import gzip,hashlib,json,struct,sys
from build_r18_procedural_stencil import load_meshes,unpack_accessor,HRA,ASSETS
P=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 assert sys.byteorder=='little'
 src=json.loads((ASSETS/'manifest_r18.json').read_text())
 assert sha(HRA)==src['reference_HRA_sha256']
 shapes,binary=load_meshes()
 assert len(shapes['meshes'])==len(src['regions'])==283
 center=src['center_m'];extent=src['max_extent_m']
 vb=bytearray();ib=bytearray();regions=[]
 nverts=0;ntris=0
 for i,mesh in enumerate(shapes['meshes']):
  primitive=mesh['primitives'][0]
  pos=unpack_accessor(shapes,primitive['attributes']['POSITION'],binary,3)
  indices=unpack_accessor(shapes,primitive['indices'],binary,1)
  assert primitive.get('mode',4)==4
  assert len(indices)%3==0 and len(pos)<65536
  for xyz in pos:
   vals=tuple(max(0,min(65535,round(((xyz[k]-center[k])/extent+.5)*65535)))
    for k in range(3))
   vb.extend(struct.pack('<3H',*vals))
  for (idx,) in indices:
   assert idx<len(pos)
   ib.extend(struct.pack('<H',idx))
  regions.append({'index':i,'name':src['regions'][i]['name'],
   'vertex_start':nverts,'vertex_count':len(pos),
   'triangle_start':ntris,'triangle_count':len(indices)//3,
   'region_type':src['regions'][i]['type']})
  nverts+=len(pos);ntris+=len(indices)//3
 header=b'HTR2'+struct.pack('<IIII',1,283,nverts,ntris)
 raw=header+vb+ib
 target=ASSETS/'hra_triangle_stencil_r22.bin.gz'
 target.write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 compressed=target.read_bytes()
 parts=[]
 for off in range(0,len(compressed),600000):
  i=off//600000
  piece=ASSETS/('hra_triangle_stencil_r22.part%02d'%i)
  piece.write_bytes(compressed[off:off+600000])
  parts.append({'file':'assets/'+piece.name,'bytes':piece.stat().st_size,
                'sha256':sha(piece)})
 manifest={
 'version':'R22','kind':'source-derived HRA anatomical triangle stencil',
 'HRA_reference_sha256':sha(HRA),'HST8_existing_sha256':src['stencil_sha256'],
 'source':'HRA/Allen male human brain v1.3, CC BY 4.0',
 'source_url':src['source_url'],
 'region_count':283,'vertex_count':nverts,'triangle_count':ntris,
 'asset':'concatenate the parts listed in parts (one gzip stream)','asset_sha256':sha(target),
 'gzip_bytes':target.stat().st_size,'uncompressed_bytes':len(raw),
 'parts':parts,'asset_stored_as_single_file':False,
 'format':'HTR2, four little-endian u32 fields version=1, region_count,vertex_count,triangle_count; all quantized u16 XYZ then all per-region local-index u16 triples; starts/counts in manifest; coordinates match HST8 normalization',
 'is_displayed_as_original_mesh':False,'requires_materialized_86b_points':False,
 'per_region_neuron_counts_measured':False,'face_visibility':'derived from 3D triangles and current camera at runtime; synthetic point sampling only',
 'regions':regions}
 (ASSETS/'manifest_r22_triangles.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 target.unlink()  # Only the independently downloadable GitHub-sized chunks are retained.
 print('R22 source triangles',ntris,'vertices',nverts,'raw',len(raw),
       'compressed',len(compressed),'parts',len(parts),'checksum',manifest['asset_sha256'])
run()
