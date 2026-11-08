#!/usr/bin/env python3
"""QA for R13 sulcal blue masks, source coordinates, jitter and unchanged fibers."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
from scipy.spatial import cKDTree

def open_points(path):
    raw=gzip.decompress(path.read_bytes())
    assert raw[:4]==b'HQP3'
    count=int.from_bytes(raw[4:8],'little')
    vals=np.frombuffer(raw,dtype='u1',offset=8).reshape(-1,8)
    assert len(vals)==count
    return vals

def test():
    assets=Path(__file__).resolve().parents[1]/'docs/assets'
    base=open_points(assets/'hq500m_source_points_r12.bin.gz')
    r13=open_points(assets/'hq500m_source_points_r13.bin.gz')
    lite=open_points(assets/'hq500m_source_points_lite_r13.bin.gz')
    assert len(base)==1_192_673
    assert np.array_equal(base[:,:6],r13[:,:6]),'SOURCE 3D COORDINATES CHANGED'
    assert np.array_equal(base[:,7],r13[:,7]),'STABLE JITTER SEED CHANGED'
    assert np.array_equal(lite,r13[::4]),'LITE SUBSAMPLING CHANGED'
    assert not np.array_equal(base[:,6],r13[:,6]),'OLD CREST BLUE MASK REUSED'
    assert (assets/'hq500m_exact_fibers_r11.bin.gz').is_file(),'ORIGINAL EDGES MISSING'
    fiber=gzip.decompress((assets/'hq500m_exact_fibers_r11.bin.gz').read_bytes())
    assert fiber[:4]==b'HQF3'
    local=int.from_bytes(fiber[4:8],'little')
    distant=int.from_bytes(fiber[8:12],'little')
    assert local+distant==520_150,'SAMPLED HQ500M Q0.8 EDGES CHANGED'
    blue=r13[:,6]
    n=int((blue>0).sum())
    bright=int((blue>=192).sum())
    assert 70_000<n<140_000,('SULCI MASK COVERAGE',n)
    assert 15_000<bright<60_000,('BRIGHT SULCI COVERAGE',bright)
    assert np.mean(blue>0)<.15,'TOO MUCH BLUE, RED NOT DOMINANT'
    manifest=json.loads((assets/'manifest_r13.json').read_text(encoding='utf-8'))
    assert manifest['mask_stats']['mask_any']==n
    assert manifest['mask_stats']['mask_strong']==bright
    assert manifest['points']==len(r13)
    xyz=r13[:,:6].copy().view('<u2').reshape(-1,3).astype('f4')/65535.
    # Select evenly spaced points, then compare blue neighbor rates.
    chosen=np.arange(0,len(xyz),8)
    xyz_subset=xyz[chosen]
    marked=blue[chosen]>=192
    tree=cKDTree(xyz_subset)
    sel=np.flatnonzero(marked)[::4][:1800]
    assert len(sel)>100
    _,nn=tree.query(xyz_subset[sel],k=10,workers=-1)
    neighbor_fraction=float(np.mean(marked[nn[:,1:]]))
    baseline=float(np.mean(marked))
    assert neighbor_fraction>baseline*3,(neighbor_fraction,baseline)
    print('PASS: full source XYZ byte-identical, jitter seeds preserved, edges unchanged')
    print('PASS:',n,'blue in recessed folds,',bright,'strong;',f'{n/len(r13)*100:.3f}% blue total')
    print('PASS: blue spatial neighbor fraction',f'{neighbor_fraction:.3f}',
          'vs random population baseline',f'{baseline:.3f}')
if __name__=='__main__':
    test()
