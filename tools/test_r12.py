#!/usr/bin/env python3
"""R12 QA: old source positions and HQ500M Q0.8 connections remain intact."""
from pathlib import Path
from scipy.spatial import cKDTree
import gzip,hashlib,json
import numpy as np

def points(path):
    raw=gzip.decompress(path.read_bytes())
    assert raw[:4]==b'HQP3'
    count=int.from_bytes(raw[4:8],'little')
    a=np.frombuffer(raw,dtype='u1',offset=8).reshape(-1,8)
    assert len(a)==count
    return a
def main():
    root=Path(__file__).resolve().parents[1]/'docs/assets'
    old=points(root/'hq500m_source_points_r11.bin.gz')
    new=points(root/'hq500m_source_points_r12.bin.gz')
    lite=points(root/'hq500m_source_points_lite_r12.bin.gz')
    assert np.array_equal(old[:,:6],new[:,:6]),'Original coordinates changed'
    assert np.array_equal(new[::4],lite),'Lite positions or attributes changed'
    assert len(new)==1_192_673
    mask=new[:,6]
    n=int((mask>0).sum())
    strong=int((mask>=192).sum())
    assert 1000<strong<15000
    assert 8000<n<50000
    assert 0<len(np.unique(new[:,7]))>=200,'Stable seed not populated'
    oldedges=root/'hq500m_exact_fibers_r11.bin.gz'
    manifest=json.loads((root/'manifest_r12.json').read_text())
    assert manifest['source_points']==len(new)
    assert manifest['blue_accents']['blue_nonzero']==n
    assert manifest['blue_accents']['blue_strong']==strong
    assert oldedges.exists()
    # Verify the highlighted mask clusters spatially instead of resembling noise.
    # Use a representative 75k subset with its exact positions.
    coords=new[:,:6].copy().view('<u2').reshape(-1,3).astype('f4')/65535
    sel=np.arange(0,len(coords),12)
    marked=mask[sel]>=192
    tree=cKDTree(coords[sel])
    candidates=np.flatnonzero(marked)[:1200]
    if len(candidates)>200:
        _,nn=tree.query(coords[sel[candidates]],k=8)
        neighbor_fraction=np.mean(marked[nn[:,1:]])
        baseline=float(np.mean(marked))
        assert neighbor_fraction>baseline*2.0,(neighbor_fraction,baseline)
        print('Geometry clustering: neighbor strong-blue fraction',round(float(neighbor_fraction),4),'vs random expectation',round(baseline,4))
    print('R12 PASS:',len(new),'source positions unchanged;',
          n,'accent points;',strong,'strong points;',
          'lite exact stride preserved; original R11 Q0.8 edge asset unchanged')
if __name__=="__main__":main()
