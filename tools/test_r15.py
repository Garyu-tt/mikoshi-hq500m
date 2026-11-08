#!/usr/bin/env python3
"""R15 regression/provenance checks; no dependencies."""
import gzip,hashlib,json,struct
from pathlib import Path
P=Path(__file__).resolve().parents[1]
A=P/'docs/assets'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def layer(name,magic,stride):
    raw=gzip.decompress((A/name).read_bytes())
    assert raw[:4]==magic,name
    n,=struct.unpack_from('<I',raw,4)
    assert len(raw)==8+n*stride,(name,n,len(raw))
    return n,raw[8:]
def run():
    r13=json.loads((A/'manifest_r13.json').read_text())
    r11=json.loads((A/'manifest_r11.json').read_text())
    r14=json.loads((A/'manifest_r14.json').read_text())
    r15=json.loads((A/'manifest_r15.json').read_text())
    assert digest(A/'hq500m_source_points_r13.bin.gz') == r13['full']['sha256'] == r14['source_r13_sha256']==r15['source_r13_sha256']
    assert digest(A/'hq500m_exact_fibers_r11.bin.gz')==r11['edge_geometry']['sha256']
    n,pts=layer('hq500m_source_points_r13.bin.gz',b'HQP3',8)
    m,rg=layer('hq500m_region_density_r14.bin.gz',b'HQR4',2)
    q,stab=layer('hq500m_region_stability_r15.bin.gz',b'HQA5',1)
    l,small=layer('hq500m_region_stability_lite_r15.bin.gz',b'HQA5',1)
    assert n==m==q==1192673 and l==(n+3)//4
    assert len(set(stab))>50
    assert small == stab[::4]
    for i in range(4):
        vals=[stab[j] for j in range(n) if rg[2*j]==i]
        assert len(vals)==r15['regions'][str(i)]['points']
        assert sum(v>=192 for v in vals)==r15['regions'][str(i)]['stable_ge_192']
    assert all(digest(A/name)==r15[key]['sha256'] for key,name in [
        ('full','hq500m_region_stability_r15.bin.gz'),
        ('lite','hq500m_region_stability_lite_r15.bin.gz')])
    assert r15['atlas_registration']['status']=='not_registered'
    assert r15['original_r13_xyz_modified'] is False and r15['original_r11_fibers_modified'] is False
    js=(P/'docs/viewer_r15.js').read_text()
    for token in ['uStabilityMin','aStability','uReplicaPass','uRegionInstances',
                  'gl.drawArraysInstanced(gl.POINTS,0,cerebCount,repl-1)',
                  'hq500m_region_stability_r15.bin.gz','gl.drawArrays(gl.POINTS,0,numPoints)',
                  'const cp=new Uint8Array(count*8)']:
        assert token in js, token
    assert (P/'docs/index.html').read_text().count('viewer_r15.js')==1
    assert (P/'docs/viewer_r14.js').exists()
    print('PASS R15',n,'original points;',r15['full']['bytes'],'compressed annotation bytes; Q0.8 fibers preserved')
if __name__=='__main__':run()
