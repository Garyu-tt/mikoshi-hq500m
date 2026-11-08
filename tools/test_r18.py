#!/usr/bin/env python3
"""R18 source provenance, full 283-region coverage, and exact dynamic quota invariants."""
from pathlib import Path
import gzip,hashlib,json,struct
P=Path(__file__).resolve().parents[1]; AS=P/'docs/assets'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def apport(target,weights):
 total=sum(weights)
 a=[target*x//total for x in weights]
 left=target-sum(a)
 order=sorted(range(len(weights)),key=lambda i:(-(target*weights[i]%total),i))
 for i in order[:left]:a[i]+=1
 assert sum(a)==target
 return a
def run():
 m=json.loads((AS/'manifest_r18.json').read_text());R=m['regions']
 assert len(R)==283
 assert m['original_mesh_count']==283 and m['source_registered_V5_voxel_slots']==110404
 assert m['anatomical_surface_samples']==78091
 assert sum(x['cells_count'] for x in R)==110404
 assert sum(x['shell_count'] for x in R)==78091
 assert sum(x['neuron_quota_86_1b'] for x in R)==86100000000
 assert m['reference_86_1b_neuron_budget']=={'cerebellum':69030000000,'cortex':16340000000,'other':730000000}
 assert not m['biological_neuron_count_at_each_HRA_region_measured']
 assert m['no_86_billion_materialized_cells'] and m['no_existing_Q08_connectome_changed']
 assert sha(AS/'hra_procedural_stencil_r18.bin.gz')==m['stencil_sha256']
 raw=gzip.decompress((AS/'hra_procedural_stencil_r18.bin.gz').read_bytes())
 assert raw[:4]==b'HST8'
 version,regs,n=struct.unpack_from('<III',raw,4)
 assert version==1 and regs==283 and n==110404+78091 and len(raw)==16+8*n
 cur=0
 names=set()
 for r in R:
  assert r['index']==len(names) and r['name'] not in names
  names.add(r['name'])
  assert r['cells_start']==cur
  cur+=r['cells_count']
  assert r['shell_start']==cur
  cur+=r['shell_count']
  for i in range(r['cells_start'],r['cells_start']+r['cells_count']):
   assert struct.unpack_from('<H',raw,16+8*i+6)[0]==r['index']
  for i in range(r['shell_start'],r['shell_start']+r['shell_count']):
   assert struct.unpack_from('<H',raw,16+8*i+6)[0]==r['index']
  if r['type'] in ('tract','cavity'):assert r['neuron_quota_86_1b']==0
 assert cur==n
 assert sum(x['type']=='cavity' for x in R)==18
 assert sum(x['type']=='tract' for x in R)==31
 assert sum(x['type']=='cerebellum' for x in R)==6
 for target in (1000,1_000_000,500_000_000,8_600_000_000,86_100_000_000,1_000_000_000_000):
  q=apport(target,[r['neuron_quota_86_1b'] for r in R])
  assert sum(q)==target
  assert all((z==0)==(r['neuron_quota_86_1b']==0) for z,r in zip(q,R)) if target>1000000 else True
  print('TARGET',target,'cerebellum',sum(q[i] for i,r in enumerate(R) if r['type']=='cerebellum'))
 r13=json.loads((AS/'manifest_r13.json').read_text())
 r11=json.loads((AS/'manifest_r11.json').read_text())
 assert sha(AS/'hq500m_source_points_r13.bin.gz')==r13['full']['sha256']
 assert sha(AS/'hq500m_exact_fibers_r11.bin.gz')==r11['edge_geometry']['sha256']
 html=(P/'docs/procedural/index.html').read_text()
 js=(P/'docs/procedural/procedural_r18.js').read_text()
 assert any(x in html for x in ('procedural_r18.js','procedural_r19.js','procedural_r20.js','procedural_r21.js'))
 for token in ('new DataView','getQuota','setTotal','setRegion','setTract','getStats','links','tractEdges','volumePosition'):
  assert token in js,token
 assert './procedural/' in (P/'docs/index.html').read_text()
 print('PASS R18',len(R),'source HRA structures,',n,'stored stencil records, none of the billion logical points stored')
if __name__=='__main__':run()
