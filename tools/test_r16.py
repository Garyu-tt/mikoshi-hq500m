#!/usr/bin/env python3
"""R16 reversible soft-region regression, provenance, and plane-boundary tests."""
import gzip,hashlib,json,struct
from pathlib import Path
from build_r16_soft_regions import field,quantize,REGION_NAMES
P=Path(__file__).resolve().parents[1]; A=P/'docs/assets'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unpack(path,magic,stride):
    data=gzip.decompress((A/path).read_bytes())
    assert data[:4]==magic
    n,=struct.unpack_from('<I',data,4)
    assert len(data)==8+n*stride
    return n,data[8:]
def run():
    m=json.loads((A/'manifest_r16.json').read_text())
    r13=json.loads((A/'manifest_r13.json').read_text())
    r11=json.loads((A/'manifest_r11.json').read_text())
    assert m['atlas_registration']=='NOT_REGISTERED'
    assert m['original_geometry_modified'] is False and m['fiber_geometry_modified'] is False
    assert m['original_R13_sha256']==r13['full']['sha256']==sha(A/'hq500m_source_points_r13.bin.gz')
    assert m['original_R11_Q08_sha256']==r11['edge_geometry']['sha256']==sha(A/'hq500m_exact_fibers_r11.bin.gz')
    n,source=unpack('hq500m_source_points_r13.bin.gz',b'HQP3',8)
    mcount,soft=unpack('hq500m_soft_regions_r16.bin.gz',b'HQW6',8)
    l,slim=unpack('hq500m_soft_regions_lite_r16.bin.gz',b'HQW6',8)
    assert n==mcount==1192673 and l==(n+3)//4
    assert len(m['regions'])==len(REGION_NAMES)==8
    assert all(r['anatomical_verified'] is False for r in m['regions'])
    for i in range(n):
        q=soft[8*i:8*i+8]
        assert sum(q)==255,(i,q)
    for j in range(l):
        assert slim[j*8:j*8+8]==soft[j*32:j*32+8],j
    for record in ('full','lite'):
        assert sha(A/Path(m[record]['file']).name)==m[record]['sha256']
    # The original R14 waterline was a hard horizontal y < 0.36 split.
    # Each region probability must stay smooth crossing that plane; check
    # many x,z samples at multiple y boundary positions.
    worst=0
    for x in (.12,.25,.38,.5,.62,.75,.88):
        for z in (.22,.42,.55,.68,.78):
            for y in (.27,.34,.36,.38,.47,.58,.69):
                a=field(x,y-.001,z); b=field(x,y+.001,z)
                worst=max(worst,max(abs(u-v) for u,v in zip(a,b)))
    assert worst < .015, worst
    # Compare continuous candidate weight to prior categorical plane: there
    # must be substantial non-zero cerebellum probability on both sides.
    left=field(.60,.359,.70)[4];right=field(.60,.361,.70)[4]
    assert left>.2 and right>.2 and abs(left-right)<.015,(left,right)
    assert all(len(quantize(field(x,y,z)))==8 for x,y,z in (
        (.12,.40,.25),(.3,.65,.55),(.55,.30,.70)))
    # Source geometry cannot be moved by loading the new layer
    js=(P/'docs/viewer_r16.js').read_text()
    assert js.count('hq500m_soft_regions_r16.bin.gz')==1
    assert 'aW0' in js and 'aW1' in js and 'gl.drawArraysInstanced' in js
    assert 'uFocusZone' in js and 'cereb=clamp(aW1.x' in js
    assert 'uStabilityMin' not in js and 'region==1.0' not in js
    assert 'const PVS="#version 300 es' in js
    assert (P/'docs/index.html').read_text().count('viewer_r16.js')==1
    print('PASS R16:',n,'coordinates and Q0.8 fibers unchanged; 8 smooth zones; plane continuity max=',round(worst,6))
if __name__=='__main__':run()
