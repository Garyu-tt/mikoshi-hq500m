#!/usr/bin/env python3
"""R16 Neural Path Explorer: Q0.8 vector and derived regional edge validation."""
import gzip,hashlib,json,struct
from collections import Counter
from pathlib import Path
import ast,bisect
# Extract the authoritative Q0.8 routing function from R11 without importing
# the GLB-building numpy dependency; mirbi-linux is intentionally stdlib-only.
r11_ast=ast.parse((Path(__file__).resolve().parent/'build_r11.py').read_text())
constants={'N','K','MASK','REG','ROUTE'}
defs={'mix','target_of'}
selected=[node for node in r11_ast.body
 if (isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in node.targets))
 or (isinstance(node,ast.FunctionDef) and node.name in defs)]
exec(compile(ast.Module(body=selected,type_ignores=[]),'<R11 Q0.8>', 'exec'),globals())
P=Path(__file__).resolve().parents[1]; A=P/'docs/assets'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 m=json.loads((A/'manifest_r16_fiber_regions.json').read_text())
 r11=json.loads((A/'manifest_r11.json').read_text())
 assert m['anatomical_verified'] is False
 assert sha(A/'hq500m_exact_fibers_r11.bin.gz')==r11['edge_geometry']['sha256']
 assert sha(A/'hq500m_fiber_regions_r16.bin.gz')==m['sha256']
 raw=gzip.decompress((A/'hq500m_exact_fibers_r11.bin.gz').read_bytes())
 meta=gzip.decompress((A/'hq500m_fiber_regions_r16.bin.gz').read_bytes())
 assert raw[:4]==b'HQF3' and meta[:4]==b'HQE6'
 lo,hi=struct.unpack_from('<II',raw,4)
 assert (lo,hi)==struct.unpack_from('<II',meta,4)
 n=lo+hi
 assert n==520150 and len(raw)==12+n*12 and len(meta)==12+n*4
 counts=Counter()
 for a,b,wa,wb in struct.iter_unpack('<BBBB',meta[12:]):
  assert 0<=a<8 and 0<=b<8 and wa>0 and wb>0
  counts[(a,b)]+=1
 assert counts[(0,1)]>0 and counts[(4,1)]>0
 sample={str(i):[target_of(i,k) for k in range(32)] for i in (42,5000010,400000000)}
 (A/'q08_explorer_test_vectors_r16.json').write_text(json.dumps({'kind':'synthetic_Q0.8','samples':sample},indent=2)+'\n')
 js=(P/'docs/neural_path_explorer_r16.js').read_text()
 for name in ('function targetOf','function pathfind','regionalRoute','npeSourceId','npeTargetId','visual_proxies_for_ID_search'):
  assert name in js,name
 view=(P/'docs/viewer_r16.js').read_text()
 assert 'window.HQ500MViewer' in view and 'setExplorerGeometry' in view
 html=(P/'docs/index.html').read_text()
 assert 'neural_path_explorer_r16.js' in html and 'viewer_r16.js' in html
 print('PASS R16 Explorer',n,'sampled original Q0.8 segments,',len(counts),'candidate-region transitions')
if __name__=='__main__':run()
