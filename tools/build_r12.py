#!/usr/bin/env python3
"""R12: source-geometry-derived convex-crest accents + stable point jitter IDs.
The source point coordinates, order and 19 groups are preserved. Blue selection
is based on the geometry, not per-vertex pseudo-random speckling.
A synthetic geometric proxy, NOT anatomically labelled gyral tissue.
"""
from pathlib import Path
import gzip,hashlib,json,struct,sys
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from build_r11 import load_glb,write_asset

def ridge_scores(p, shell_path):
    n=160
    raw=gzip.decompress(shell_path.read_bytes())
    assert raw[:4]==b'HQS2'
    grid_n,_=struct.unpack_from('<II',raw,4)
    assert grid_n==n
    bl=(n**3+7)//8
    shell=np.unpackbits(np.frombuffer(raw, dtype='u1',count=bl,offset=12),bitorder='little')[:n**3].reshape(n,n,n).astype(bool)
    coords=np.argwhere(shell).astype('i4')
    lo,hi=p.min(0),p.max(0)
    vox_pos=coords.astype('f4')/(n-1)*(hi-lo)+lo
    print("SHELL",len(vox_pos),"building local curvature",flush=True)
    tree=cKDTree(vox_pos)
    distances,idx=tree.query(vox_pos,k=28,workers=-1)
    idx=idx.astype('i4')
    # Smooth signed convexity: each point's deviation from the neighborhood
    # tangent plane, normal estimated from a local PCA. A proxy for gyri crests.
    center=np.mean(vox_pos[idx],axis=1)
    delta=vox_pos[idx]-center[:,None,:]
    cov=np.einsum("nki,nkj->nij",delta,delta,optimize=True)/28
    eig,axes=np.linalg.eigh(cov)
    normal=axes[:,:,0]
    # Prefer outward-facing convex crests; sign is approximate for folded cortex.
    outward=vox_pos-np.array([0.,0.,0.],dtype='f4')
    normal*=np.where(np.einsum("ni,ni->n",normal,outward)>0,1.,-1.)[:,None]
    convex=np.einsum("ni,ni->n",vox_pos-center,normal)/np.maximum(1e-5,np.mean(distances[:,2:],axis=1))
    convex=np.clip(convex,0,1)
    print("CONVEX",np.percentile(convex,[0,50,85,95,99]).round(5).tolist(),flush=True)
    # Remove single-point noise; preserve coherent surface sections.
    for _ in range(2):
        convex=.36*convex+.64*np.mean(convex[idx],axis=1)
    # Exposure: crowns have fewer close opposing surfaces than deep sulci.
    density=gaussian_filter(shell.astype('f4'),sigma=2.8,mode='constant')
    density_at=density[coords[:,0],coords[:,1],coords[:,2]]
    exposure=np.maximum(0,1.0-density_at/(np.percentile(density_at,95)+1e-6))
    exposure=np.clip(exposure,0,1)
    # Convexity is primary; exposure rejects tight inward creases.
    score=np.maximum(convex,0)**.72 * (.35+.65*exposure)
    for _ in range(2):
        score=.45*score+.55*np.mean(score[idx],axis=1)
    # Assign nearest shell geometry score to original points, not to random IDs.
    _,nearest=tree.query(p,workers=-1)
    pts_score=score[nearest]
    # Closest shell if a point has no nearby shell: don't dye deep interior.
    # Small gate only; source cloud is slice-based and often separated by gaps.
    _,near_dist= None,None
    distances_pts=np.linalg.norm(p-vox_pos[nearest],axis=1)
    gate=np.clip((.040-distances_pts)/.025,0,1)
    pts_score*=gate
    # Threshold from *actual* point population. Target ~2% visibly cyan peaks.
    nonzero=pts_score[pts_score>1e-7]
    thr=float(np.quantile(nonzero,.935))
    hi_score=float(np.quantile(nonzero,.991))
    mapped=np.clip((pts_score-thr)/max(hi_score-thr,1e-7),0,1)
    # 3% transition, about 1-2% strong blue; no independent randomized selector.
    accent=np.rint(mapped*255).astype('u1')
    print("ACCENTS",(accent>0).sum(),">191",(accent>191).sum(),"scores",thr,hi_score,flush=True)
    return accent,{"shell_voxels":int(len(vox_pos)),"k_neighbors":28,
       "method":"local PCA convexity smoothed over neighbors, modulated by surface exposure",
       "blue_nonzero":int(np.sum(accent>0)),"blue_strong":int(np.sum(accent>=192)),
       "strong_percent_of_source":float(np.mean(accent>=192)*100),
       "coordinate_atlas":"source point-cloud synthetic, not annotated gyri"}

def main(source,output):
    output.mkdir(parents=True,exist_ok=True)
    p,c,sizes,source_hash=load_glb(source)
    accent,meta=ridge_scores(p,output/'hq500m_surface_shell_160.vox.gz')
    q=np.rint((p+1)*32767.5).clip(0,65535).astype('<u2')
    rng=np.random.default_rng(0x5a12b31)
    jitterSeed=rng.integers(0,256,size=len(p),dtype=np.uint8)
    attrib=np.empty((len(p),8),dtype='u1')
    attrib[:,:6]=q.view('u1').reshape(-1,6)
    attrib[:,6]=accent
    attrib[:,7]=jitterSeed
    full=write_asset(output,'hq500m_source_points_r12.bin.gz',b'HQP3'+struct.pack('<I',len(p))+attrib.tobytes())
    lite=attrib[::4]
    low=write_asset(output,'hq500m_source_points_lite_r12.bin.gz',b'HQP3'+struct.pack('<I',len(lite))+lite.tobytes())
    manifest={"version":"R12","source_sha256":source_hash,"source_points":len(p),
       "groups":len(sizes),"source_coordinates_preserved_at_16bit_quantization":True,
       "coordinate_displacement_stored":False,
       "shader_displacement":"deterministic adjustable jitter (no model data changes)",
       "model_edges":"unchanged R11 exact Q0.8 endpoint sample",
       "blue_accents":meta,"source_colors":"replaced with procedural ruby + geometry-selected azure highlights",
       "full_points":full,"lite_points":low,
       "author":"Garyu-tt","source_point_cloud_attribution":"Terrie / Brain Point Cloud / CC BY 4.0",
       "note":"Ridge score is geometry-derived curvature/exposure proxy; not ground-truth gyral anatomical labels."}
    (output/'manifest_r12.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print("MANIFEST",json.dumps(meta,indent=2),flush=True)

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit("Usage: build_r12.py brain_point_cloud.glb docs/assets")
    main(Path(sys.argv[1]),Path(sys.argv[2]))
