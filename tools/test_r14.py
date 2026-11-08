#!/usr/bin/env python3
"""Checks for reversible R14 density annotations; no third-party dependencies."""
import gzip,hashlib,json,struct
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parents[1]
A=P/'docs/assets'

def unpack(name,magic,stride):
    raw=gzip.decompress((A/name).read_bytes())
    assert raw[:4]==magic
    count=struct.unpack_from('<I',raw,4)[0]
    assert len(raw)==8+stride*count
    return count,memoryview(raw)[8:]

def run():
    old=json.loads((A/'manifest_r13.json').read_text())
    cur=json.loads((A/'manifest_r14.json').read_text())
    assert hashlib.sha256((A/'hq500m_source_points_r13.bin.gz').read_bytes()).hexdigest()==old['full']['sha256']==cur['source_r13_sha256']
    assert hashlib.sha256((A/'hq500m_exact_fibers_r11.bin.gz').read_bytes()).hexdigest()==json.loads((A/'manifest_r11.json').read_text())['edge_geometry']['sha256']
    n,base=unpack('hq500m_source_points_r13.bin.gz',b'HQP3',8)
    m,meta=unpack('hq500m_region_density_r14.bin.gz',b'HQR4',2)
    l,small=unpack('hq500m_region_density_lite_r14.bin.gz',b'HQR4',2)
    assert n==m==1192673 and l==(n+3)//4
    count=Counter(meta[::2]);assert all(0<=x<=3 for x in count)
    assert sum(count.values())==n and count[1]>30000 and count[1]<n//4
    for i in (0,1,2,333,55000,l-1):
        assert bytes(small[i*2:i*2+2])==bytes(meta[i*8:i*8+2])
    assert all(x<=255 for x in meta[1::2])
    assert cur['region_annotation_status'].startswith('unverified')
    assert cur['original_xyz_modified'] is False and cur['original_fibers_modified'] is False
    js=(P/'docs/viewer_r14.js').read_text()
    assert 'gl.drawArraysInstanced' in js and 'biologicalRatio' in js
    assert 'regionCtl.onchange' in js and 'hq500m_region_density_r14.bin.gz' in js
    assert any(x in (P/'docs/index.html').read_text() for x in ('viewer_r14.js','viewer_r15.js'))
    assert 'gl_PointSize=clamp' in js and 'pow(cellPressure' in js
    assert sum(x['illustrative_human_neurons'] for x in cur['regions'])==86100000000
    print('PASS R14:',dict(count),'source point XYZ/seed and Q0.8 fibers unchanged; annotations match lite stride')

if __name__=='__main__':run()

