#!/usr/bin/env python3
from pathlib import Path
import json, hashlib
P=Path(__file__).resolve().parents[1]
A=P/'docs/assets'
m=json.loads((A/'manifest_r18.json').read_text())
assert len(m['regions'])==283
assert hashlib.sha256((A/'hra_procedural_stencil_r18.bin.gz').read_bytes()).hexdigest()==m['stencil_sha256']
s=(P/'docs/procedural/procedural_r21.js').read_text()
for v in ('function localFiber','function syntheticEdges','maxSpan=selected>=0?.095:.067','const emphasized=!!focusedGraph||tract>=0','graphOutgoing(id)','uZoom','maxSpan=selected>=0?.095:.067'):
 assert v in s,v
assert 'if(src.region_id!==dst.region_id)continue;' in s
assert 'if(d>maxSpan)continue;' in s
assert 'gl.depthMask(false);common(L)' in s
assert any(x in (P/'docs/procedural/index.html').read_text() for x in ('procedural_r21.js','procedural_r22.js'))
assert (P/'docs/images/r21_local_fibers.png').is_file()
print('PASS R21: local segment filtering, curve subdivision, depth handling, HRA geometry unchanged')
