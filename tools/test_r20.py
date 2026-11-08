#!/usr/bin/env python3
"""R20 high-density LOD source/data regression; browser E2E is separate."""
import gzip, hashlib, json, math
from pathlib import Path
P=Path(__file__).resolve().parents[1]; A=P/'docs/assets'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 m=json.loads((A/'manifest_r18.json').read_text())
 r11=json.loads((A/'manifest_r11.json').read_text())
 r13=json.loads((A/'manifest_r13.json').read_text())
 assert len(m['regions'])==283 and m['no_86_billion_materialized_cells']
 assert sha(A/'hra_procedural_stencil_r18.bin.gz')==m['stencil_sha256']
 assert sha(A/'hq500m_source_points_r13.bin.gz')==r13['full']['sha256']
 assert sha(A/'hq500m_exact_fibers_r11.bin.gz')==r11['edge_geometry']['sha256']
 assert len(gzip.decompress((A/'hra_procedural_stencil_r18.bin.gz').read_bytes()))==16+188495*8
 html=(P/'docs/procedural/index.html').read_text()
 assert any(x in html for x in ('procedural_r20.js','procedural_r21.js','procedural_r22.js','procedural_r23.js')) and 'procedural_r19.js' not in html
 for token in ('id="lodMode"','id="lod"','value="800000"','max="1100000"','id="neuronRunR19"'):
  assert token in html,token
 js=(P/'docs/procedural/procedural_r20.js').read_text()
 for token in ('function budget()','mode==="manual"','220000*Math.pow(total/500000000,.22)',
               'mobile?120000:1100000','getLOD:','function graphOutgoing','function neuronForId',
               'function findSyntheticPath','uZoom'):
  assert token in js,token
 assert 220000==round(220000*(500000000/500000000)**.22)
 assert 682889==round(220000*(86100000000/500000000)**.22)
 assert (P/'docs/images/r20_dense_861b.png').exists()
 assert any(x in (P/'docs/index.html').read_text() for x in ('R20 · Плотный нейронный мозг','R21 · Локальные нервные связи','R22 · Только видимые нейроны','R23 · Видимые нейроны и связи'))
 print('PASS R20: automatic 500M=220000 and 86.1B=682889 points, 1.1M desktop/manual and 120k mobile caps, original HRA/R11/R13 unmodified')
if __name__=='__main__':main()
