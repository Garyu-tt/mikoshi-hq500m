#!/usr/bin/env python3
"""Build HQ500M R13 -- sulcal recess highlight, not gyri crest highlight.
Geometry-derived visual proxy. Original point XYZ and original Q0.8 edges unchanged.
"""
from pathlib import Path
import gzip,hashlib,json,struct,sys
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
from build_r11 import load_glb,write_asset

def sulcal_mask(points, shell_path):
    n=160
    raw=gzip.decompress(shell_path.read_bytes())
    assert raw[:4]==b'HQS2'
    width,count=struct.unpack_from('<II',raw,4)
    assert width==n and count==74932
    nb=(n**3+7)//8
    occ=np.unpackbits(np.frombuffer(raw,dtype='u1',count=nb,offset=12),bitorder='little')[:n**3].reshape(n,n,n).astype(bool)
    shell_indices=np.argwhere(occ).astype('i4')
    low,high=points.min(axis=0),points.max(axis=0)
    shell=shell_indices.astype('f4')/(n-1)*(high-low)+low
    print("SHELL",len(shell),"computing outward depth and local concavity",flush=True)
    tree=cKDTree(shell)
    dist,near=tree.query(shell,k=80,workers=-1)
    near=near.astype('i4')
    # PCA normal, oriented approximately from the global point cloud center.
    close=near[:,:28]
    centroid=np.mean(shell[close],axis=1)
    dx=shell[close]-centroid[:,None,:]
    cov=np.einsum('nki,nkj->nij',dx,dx,optimize=True)/28
    _,eigenvectors=np.linalg.eigh(cov)
    nrm=eigenvectors[:,:,0]
    toward=shell-np.median(shell,axis=0)
    nrm*=np.where(np.einsum('ij,ij->i',nrm,toward)>=0,1.,-1.)[:,None]
    signed=np.einsum('ij,ij->i',shell-centroid,nrm)/np.maximum(0.00002,np.mean(dist[:,2:28],axis=1))
    concave=np.clip(-signed,0,1.5)
    # Sulcal recess: neighboring crests sit farther away from the cloud center.
    radial=np.linalg.norm(toward,axis=1)
    neighbor_rad=radial[near]
    outer_envelope=np.quantile(neighbor_rad,.90,axis=1)
    recess=np.clip((outer_envelope-radial)/np.maximum(.0001,np.mean(dist[:,10:60],axis=1)),0,2)
    # Deep narrow folds have more neighboring occupied shell voxels
    # than exposed crests. Smooth over multiple scales.
    dense=gaussian_filter(occ.astype('f4'),sigma=3.3,mode='constant')
    dense_at=dense[shell_indices[:,0],shell_indices[:,1],shell_indices[:,2]]
    dense_scale=np.quantile(dense_at,.93)
    crowding=np.clip((dense_at-np.quantile(dense_at,.18))/max(1e-6,dense_scale-np.quantile(dense_at,.18)),0,1)
    # Balanced recess + signed concavity, softened to paint continuous troughs.
    recess=recess/(.7+recess)
    concave=concave/(.5+concave)
    signed_score=(.64*recess+.28*concave+.08*crowding)
    for _ in range(4):
        signed_score=.32*signed_score+.68*np.mean(signed_score[close],axis=1)
    # Exclude isolated exterior peaks that are radially exposed / convex.
    scores=np.clip(signed_score,0,1)
    dnear,idx=tree.query(points,workers=-1)
    pt_scores=scores[idx]
    # Non-exterior source layers should stay deep ruby.
    gate=np.clip((.045-dnear)/.027,0,1)
    pt_scores*=gate
    valid=pt_scores[pt_scores>0.000001]
    print("SCORES",np.round(np.quantile(valid,[.05,.25,.5,.65,.78,.90,.97,.99]),6).tolist(),
          "valid",len(valid),"dist",np.round(np.quantile(dnear,[.1,.5,.9,.98]),4).tolist(),flush=True)
    # Wider, smooth blue troughs (not disconnected blue freckle points).
    lo=float(np.quantile(valid,.68))
    hi=float(np.quantile(valid,.94))
    t=np.clip((pt_scores-lo)/max(1e-7,hi-lo),0,1)
    t=t*t*(3-2*t)
    # Gentle intermediate blue and saturated deep-sulcus cores.
    accent=np.rint(t*255).astype('u1')
    stats={'method':'80-neighbor radial recess + signed local PCA concavity + multi-scale occupancy, 4 neighbor-smooth passes',
           'groove_selection':'depressions (not convex crests)',
           'point_count':len(points),'shell_count':len(shell),
           'mask_any':int(np.count_nonzero(accent)),
           'mask_strong':int(np.count_nonzero(accent>=192)),
           'mask_any_percent':round(100*float(np.mean(accent>0)),3),
           'mask_strong_percent':round(100*float(np.mean(accent>=192)),3),
           'local_quantiles':[lo,hi],
           'not_anatomical_sulcal_annotation':True}
    print("SULCI_STATS",json.dumps(stats),flush=True)
    return accent,stats

def build(src,out):
    out.mkdir(parents=True,exist_ok=True)
    pos,col,groups,source_hash=load_glb(src)
    mask,stats=sulcal_mask(pos,out/'hq500m_surface_shell_160.vox.gz')
    original=gzip.decompress((out/'hq500m_source_points_r12.bin.gz').read_bytes())
    assert original[:4]==b'HQP3'
    count=struct.unpack_from('<I',original,4)[0]
    assert count==len(pos)
    raw=np.frombuffer(original[8:],dtype='u1').reshape(-1,8).copy()
    raw[:,6]=mask  # ONLY mask changes; XYZ and stable jitter seed stay unchanged
    full=write_asset(out,'hq500m_source_points_r13.bin.gz',
                     b'HQP3'+struct.pack('<I',count)+raw.tobytes())
    lite=write_asset(out,'hq500m_source_points_lite_r13.bin.gz',
                     b'HQP3'+struct.pack('<I',len(raw[::4]))+raw[::4].tobytes())
    manifest={'version':'R13','source_sha256':source_hash,
      'points':len(pos),'groups':len(groups),
      'accents':'geometry-derived sulcal recess and concavity; source is unlabelled point cloud',
      'mask_stats':stats,'source_xyz':'bit-identical to R12','jitter_seed':'identical to R12',
      'edges':'R11 Q0.8 exact-address-pair edge data retained without modification',
      'full':full,'lite':lite,
      'license_source':'Terrie Brain Point Cloud CC BY 4.0',
      'note':'Synthetic 3D proxy, NOT confirmed anatomical sulcal labels or reconstructed axons'}
    (out/'manifest_r13.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit("Usage: build_r13.py brain_point_cloud.glb docs/assets")
    print(json.dumps(build(Path(sys.argv[1]),Path(sys.argv[2])),indent=2),flush=True)
