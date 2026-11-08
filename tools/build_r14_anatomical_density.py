#!/usr/bin/env python3
"""R14 reversible *candidate* region annotations + local density proxy.
No edits to R13 point or fiber data. Labels are visual priors, NOT atlas verified.
"""
from __future__ import annotations
import gzip,hashlib,json,math,struct,sys
from array import array
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

GRID=96
REGIONS=('cortex_candidate','cerebellum_candidate','brainstem_candidate','deep_structures_candidate')
MASS_FRACTIONS=(.82,.10,.03,.05)
# Mean human numbers: cortex 16.3B, cerebellum 69.03B, rest approx 0.8B.
NEURONS_FULL=(16_300_000_000,69_030_000_000,300_000_000,470_000_000)
# Supplementary scale, not a biological cell diameter measurement.
RELATIVE_DENSITY=(1.,(69.03/.10)/(16.3/.82),1.0,1.0)

def classify(x,y,z):
    # Everything is tagged a geometric PROXY until registration to an MRI atlas.
    # Scene axes determined from R13 model: y up, lower posterior assumed z-high.
    # Brainstem candidate takes priority around midline in the low part.
    if y<.30 and abs(x-.50)<.115 and .35<z<.63:
        return 2
    if y<.36 and z>.50:
        return 1
    if .30<=y<.58 and abs(x-.50)<.19 and .31<z<.67:
        return 3
    return 0

def build(root):
    src=root/'hq500m_source_points_r13.bin.gz'
    before=hashlib.sha256(src.read_bytes()).hexdigest()
    raw=gzip.decompress(src.read_bytes())
    assert raw[:4]==b'HQP3'
    count=struct.unpack_from('<I',raw,4)[0]
    assert len(raw)==8+count*8
    bins=array('I',[0])*(GRID**3)
    # Use geometry occupancy to size rendering glyphs, never reposition inputs.
    for x,y,z,accent,seed in struct.iter_unpack('<HHHBB',raw[8:]):
        i=x*GRID//65536;j=y*GRID//65536;k=z*GRID//65536
        bins[(i*GRID+j)*GRID+k]+=1
    out=bytearray(count*2)
    stats=Counter()
    region_occ=Counter()
    for n,(x,y,z,accent,seed) in enumerate(struct.iter_unpack('<HHHBB',raw[8:])):
        xx=x/65535.;yy=y/65535.;zz=z/65535.
        rg=classify(xx,yy,zz)
        i=x*GRID//65536;j=y*GRID//65536;k=z*GRID//65536
        # Local 3x3x3-neighborhood occupancy with a geometry-derived density proxy.
        occ=0
        for a in range(max(i-1,0),min(i+2,GRID)):
            for b in range(max(j-1,0),min(j+2,GRID)):
                offset=(a*GRID+b)*GRID
                for c in range(max(k-1,0),min(k+2,GRID)):
                    occ+=bins[offset+c]
        out[2*n]=rg
        out[2*n+1]=min(255,round(30*math.log1p(occ)))
        stats[REGIONS[rg]]+=1
        region_occ[rg]+=occ
    header=b'HQR4'+struct.pack('<I',count)
    rawmeta=header+out
    full=root/'hq500m_region_density_r14.bin.gz'
    lite=root/'hq500m_region_density_lite_r14.bin.gz'
    full.write_bytes(gzip.compress(rawmeta,compresslevel=7,mtime=0))
    litebytes=bytearray(((count+3)//4)*2)
    for i in range((count+3)//4):
        litebytes[2*i:2*i+2]=out[8*i:8*i+2]
    lite.write_bytes(gzip.compress(b'HQR4'+struct.pack('<I',len(litebytes)//2)+litebytes,compresslevel=7,mtime=0))
    manifest={
      'version':'R14','generated_at':datetime.now(timezone.utc).isoformat(),
      'geometry_source':'HQ500M R13, original Terrie Point Cloud CC BY 4.0',
      'source_r13_sha256':before,
      'points':count,'original_xyz_modified':False,
      'original_fibers_modified':False,
      'regions':[{ 'id':i,'name':name,'candidate_points':stats[name],
                   'mass_fraction_guidance':MASS_FRACTIONS[i],
                   'illustrative_human_neurons':NEURONS_FULL[i],
                   'relative_density_to_cortex':round(RELATIVE_DENSITY[i],3)}
                 for i,name in enumerate(REGIONS)],
      'region_annotation_status':'unverified heuristic proxy (no atlas registration; cerebellar tissue may be absent from point cloud)',
      'assumed_anatomical_axes':'Y up, z-high posterior: provisional, requires verification from oriented source',
      'voxel_occupancy_grid':GRID,
      'size_logic':'point radius decreases with local occupancy and regional density; extra shader instances are illustrative samples only',
      'density_byte':'min(255, round(30*ln(1+number of source points in neighboring 3x3x3 grid cells)))',
      'full':{'file':'assets/'+full.name,'sha256':hashlib.sha256(full.read_bytes()).hexdigest()},
      'lite':{'file':'assets/'+lite.name,'sha256':hashlib.sha256(lite.read_bytes()).hexdigest()},
      'original_q08_unchanged':True,
      'point_cloud_license':'Terrie CC BY 4.0'}
    (root/'manifest_r14.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    assert hashlib.sha256(src.read_bytes()).hexdigest()==before
    for name,n in [(full,count),(lite,(count+3)//4)]:
        rr=gzip.decompress(name.read_bytes())
        assert rr[:4]==b'HQR4' and struct.unpack_from('<I',rr,4)[0]==n
        assert len(rr)==8+2*n
    print(json.dumps({'points':count,'segmentation':dict(stats),'full_bytes':full.stat().st_size,'lite_bytes':lite.stat().st_size,'sha256_R13_preserved':before},indent=2))

if __name__=='__main__':
    build(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'docs/assets')

