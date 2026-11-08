#!/usr/bin/env python3
"""R19 repeatable artifact checks; real browser QA in qa_r19_browser.py."""
from pathlib import Path
import gzip,hashlib,json,struct
P=Path(__file__).resolve().parents[1]
A=P/'docs/assets'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 m=json.loads((A/'manifest_r18.json').read_text())
 r13=json.loads((A/'manifest_r13.json').read_text())
 r11=json.loads((A/'manifest_r11.json').read_text())
 assert len(m['regions'])==283
 assert sha(A/'hra_procedural_stencil_r18.bin.gz')==m['stencil_sha256']
 assert sha(A/'hq500m_source_points_r13.bin.gz')==r13['full']['sha256']
 assert sha(A/'hq500m_exact_fibers_r11.bin.gz')==r11['edge_geometry']['sha256']
 b=gzip.decompress((A/'hra_procedural_stencil_r18.bin.gz').read_bytes())
 assert b[:4]==b'HST8'
 assert struct.unpack_from('<III',b,4)==(1,283,188495)
 assert len(b)==16+188495*8
 assert sum(x['neuron_quota_86_1b'] for x in m['regions'])==86100000000
 assert all(x['neuron_quota_86_1b']==0 for x in m['regions'] if x['type'] in ('tract','cavity'))
 page=(P/'docs/procedural/index.html').read_text()
 assert any(v in page for v in ('procedural_r19.js','procedural_r20.js','procedural_r21.js','procedural_r22.js','procedural_r23.js'))
 assert 'procedural_r18.js' not in page
 for k in ('sourceNeuronR19','targetNeuronR19','neuronClearR19','graphDepthR19','neuronRunR19'):
  assert page.count('id="'+k+'"')==1,k
 js=(P/'docs/procedural/procedural_r19.js').read_text()
 assert 'function mortonPart' in js
 for k in ('regionSpatialOrder','rebuildRanges','neuronForId','graphOutgoing',
           'traverse','findSyntheticPath','graphFocusCamera','graphZoom',
           'window.ProceduralAtlasR18','uZoom'):
  assert k in js,k
 assert js.count('function syntheticEdges(data)')==1
 assert 'graphVersion:"R19 procedural directed synthetic ID connections' in js
 assert 'realSynapses:false' in js
 assert 'quotaFor' not in js
 assert any(x in (P/'docs/index.html').read_text() for x in ('R19 · Нейроны и связи по ID','R20 · Плотный нейронный мозг','R21 · Локальные нервные связи','R22 · Только видимые нейроны','R23 · Видимые нейроны и связи'))
 assert (P/'docs/images/r19_graph_tree_demo.png').exists()
 assert (P/'docs/images/r19_neuron_pair_demo.png').exists()
 print('PASS R19: HRA 283-region template + all original R18/R11/R13 checksums preserved; deterministic ID graph and browser UI sources ready')
if __name__=='__main__':run()
