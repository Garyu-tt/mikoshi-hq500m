#!/usr/bin/env python3
"""R22 HRA triangle-culling artifact and original-source regression checks."""
from pathlib import Path
import gzip, hashlib, json, struct, sys
P=Path(__file__).resolve().parents[1]
A=P/'docs/assets'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 m=json.loads((A/'manifest_r22_triangles.json').read_text())
 r18=json.loads((A/'manifest_r18.json').read_text())
 r13=json.loads((A/'manifest_r13.json').read_text())
 r11=json.loads((A/'manifest_r11.json').read_text())
 assert m['region_count']==283 and len(m['regions'])==283
 assert m['vertex_count']==324855 and m['triangle_count']==656268
 assert m['HRA_reference_sha256']==r18['reference_HRA_sha256']
 assert m['HST8_existing_sha256']==r18['stencil_sha256']
 assert not m['asset_stored_as_single_file']
 assert len(m['parts'])>=2
 compressed=b''
 for part in m['parts']:
  f=A/Path(part['file']).name
  data=f.read_bytes()
  assert len(data)==part['bytes']
  assert hashlib.sha256(data).hexdigest()==part['sha256']
  compressed+=data
 assert len(compressed)==m['gzip_bytes']
 assert hashlib.sha256(compressed).hexdigest()==m['asset_sha256']
 raw=gzip.decompress(compressed)
 assert raw[:4]==b'HTR2'
 assert struct.unpack_from('<IIII',raw,4)==(1,283,324855,656268)
 assert len(raw)==20+6*(324855+656268)
 assert sha(A/'hra_procedural_stencil_r18.bin.gz')==r18['stencil_sha256']
 assert sha(A/'hq500m_source_points_r13.bin.gz')==r13['full']['sha256']
 assert sha(A/'hq500m_exact_fibers_r11.bin.gz')==r11['edge_geometry']['sha256']
 vertices_total=0;triangles_total=0
 idx_off=20+324855*6
 for i,r in enumerate(m['regions']):
  assert r['index']==i and r['name']==r18['regions'][i]['name']
  assert r['vertex_start']==vertices_total
  assert r['triangle_start']==triangles_total
  assert r['vertex_count']>0 and 0<=r['triangle_count']
  assert r['vertex_count']<65536
  beg=idx_off+r['triangle_start']*6
  end=beg+r['triangle_count']*6
  for (idx,) in struct.iter_unpack('<H',raw[beg:end]):
   assert idx<r['vertex_count'],(i,idx)
  vertices_total+=r['vertex_count'];triangles_total+=r['triangle_count']
 assert (vertices_total,triangles_total)==(324855,656268)
 js=(P/'docs/procedural/procedural_r22.js').read_text()
 html=(P/'docs/procedural/index.html').read_text()
 assert html.count('procedural_r22.js')==1
 assert html.count('id="occludeBack"')==1
 for token in (
  'function ensureFrontShell','function ensureVisibleTriangles',
  'function sampleTrianglePosition','function triangleVertices',
  'gl.colorMask(false,false,false,false)','gl_FragDepth=',
  'eligibleHraTriangles','sourceHraTriangles','buildDepthStencil',
  'new Uint16Array(triRaw','function findSyntheticPath'):
  assert token in js,token
 # The HRA triangles act as a sampling source, not a rendered polygon mesh.
 assert 'gl.drawElements(' not in js
 assert 'gl.drawArrays(gl.TRIANGLES' not in js
 assert (P/'docs/images/r22_occluded_dense.png').is_file()
 assert (P/'docs/images/r22_occluded_default.png').is_file()
 assert (P/'docs/images/r22_unoccluded_comparison.png').is_file()
 assert 'R22 · Только видимые нейроны' in (P/'docs/index.html').read_text()
 print('PASS R22:',len(m['regions']),'HRA region meshes,',
       m['triangle_count'],'source triangles and',
       m['vertex_count'],'vertices; HST8/R13/Q0.8 untouched')
if __name__=='__main__':run()
