#!/usr/bin/env python3
"""R16 anatomical *hypothesis* fields, continuous everywhere; never deform geometry.

Eight soft schematic regions. This is NOT MRI atlas segmentation:
Terrie's CC BY 4.0 point cloud has no anatomical orientation or landmarks.
"""
from __future__ import annotations
import gzip, hashlib, json, math, struct, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REGION_NAMES = (
    "frontal_lobe_candidate", "parietal_lobe_candidate",
    "temporal_lobe_candidate", "occipital_lobe_candidate",
    "cerebellum_candidate", "brainstem_candidate",
    "deep_structures_candidate", "insula_candidate"
)
NAMES_RU = (
    "Лобная зона", "Теменная зона", "Височная зона", "Затылочная зона",
    "Мозжечковая зона", "Стволовая зона", "Глубинные структуры", "Островковая зона"
)
LICENSE = "Terrie Brain Point Cloud CC BY 4.0"

def gauss(x:float, y:float, z:float, cx:float, cy:float, cz:float,
          sx:float, sy:float, sz:float) -> float:
    return math.exp(-0.5 * (((x-cx)/sx)**2+((y-cy)/sy)**2+((z-cz)/sz)**2))

def field(x:float, y:float, z:float) -> tuple[float,...]:
    """Smooth analytic membership weights; NONE are anatomical evidence."""
    # Gradual envelope deformation produces curvature; no y<0.36 threshold
    # and no hard categorical region boundary.
    fold = 0.018 * math.sin(13.2*x+7.0*z)*math.sin(6.6*z-4.0*x)
    yy = y + fold
    s = [
        .055+2.60*gauss(x,yy,z,.50,.63,.25,.56,.24,.29), # frontal
        .055+2.80*gauss(x,yy,z,.50,.70,.55,.56,.21,.24), # parietal
        .055+2.35*gauss(x,yy,z,.50,.43,.50,.56,.20,.26), # temporal
        .055+2.80*gauss(x,yy,z,.50,.60,.78,.54,.23,.20), # occipital
        .012+5.80*gauss(x,yy,z,.50,.265,.70,.39,.11,.21), # cerebellum
        .012+4.20*gauss(x,yy,z,.50,.23,.46,.145,.145,.165), # stem
        .012+2.45*gauss(x,yy,z,.50,.47,.50,.225,.175,.20), # deep
        .012+1.70*(gauss(x,yy,z,.265,.45,.48,.12,.155,.17)+
                    gauss(x,yy,z,.735,.45,.48,.12,.155,.17)), # insula
    ]
    total=sum(s)
    return tuple(a/total for a in s)

def quantize(ws:tuple[float,...]) -> bytes:
    assert len(ws)==8 and all(math.isfinite(w) and 0<=w<=1 for w in ws)
    floors=[int(w*255) for w in ws]
    # Largest-remainder method: preserve exactly 255 per point.
    gap=255-sum(floors)
    residues=sorted(range(8),key=lambda i:(-(ws[i]*255-floors[i]),i))
    for i in residues[:gap]: floors[i]+=1
    assert sum(floors)==255
    return bytes(floors)

def sha(path:Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pack(path:Path, data:bytes) -> dict:
    n=len(data)//8
    raw=b'HQW6'+struct.pack('<I',n)+data
    blob=gzip.compress(raw,compresslevel=7,mtime=0)
    path.write_bytes(blob)
    return {'file':'assets/'+path.name, 'bytes':len(blob),
            'raw_bytes':len(raw),'sha256':sha(path), 'points':n}

def build(root:Path) -> dict:
    r13=json.loads((root/'manifest_r13.json').read_text())
    r11=json.loads((root/'manifest_r11.json').read_text())
    src=root/'hq500m_source_points_r13.bin.gz'
    fib=root/'hq500m_exact_fibers_r11.bin.gz'
    before_src=sha(src)
    before_fib=sha(fib)
    assert before_src==r13['full']['sha256']
    assert before_fib==r11['edge_geometry']['sha256']
    raw=gzip.decompress(src.read_bytes())
    assert raw[:4]==b'HQP3'
    n,=struct.unpack_from('<I',raw,4)
    assert len(raw)==8+n*8
    weights=bytearray(n*8)
    sums=[0]*8
    dominant=Counter()
    for i,(x,y,z,_accent,_seed) in enumerate(struct.iter_unpack('<HHHBB',raw[8:])):
        w=quantize(field(x/65535.,y/65535.,z/65535.))
        weights[8*i:8*i+8]=w
        for k,val in enumerate(w):sums[k]+=val
        dominant[max(range(8),key=lambda k:w[k])]+=1
    full=pack(root/'hq500m_soft_regions_r16.bin.gz',bytes(weights))
    # R13 lite samples exactly every fourth original source point.
    liteweights=bytearray(((n+3)//4)*8)
    for j,i in enumerate(range(0,n,4)):
        liteweights[j*8:j*8+8]=weights[i*8:i*8+8]
    lite=pack(root/'hq500m_soft_regions_lite_r16.bin.gz',bytes(liteweights))
    manifest={
        'version':'R16','generated_at':datetime.now(timezone.utc).isoformat(),
        'geometry':LICENSE, 'source_points':n,
        'original_R13_sha256':before_src,'original_R11_Q08_sha256':before_fib,
        'original_geometry_modified':False,'fiber_geometry_modified':False,
        'atlas_registration':'NOT_REGISTERED',
        'annotation_kind':'continuous schematic spatial candidate weights, not validated anatomical labels',
        'assumed_axes':'x midline, y vertical, z posterior; all unverified',
        'format':'HQW6 little-endian u32 N + 8 uint8 weights per point; bytes sum to 255',
        'regions':[{'id':i,'key':REGION_NAMES[i],'ru':NAMES_RU[i],
                    'dominant_points':dominant[i],
                    'mean_weight':round(sums[i]/(n*255),5),
                    'anatomical_verified':False} for i in range(8)],
        'source_neurons_simulated':False,
        'cerebellar_density':'approx 69B/86B as literature guidance ONLY; neither instances nor glyphs are true neurons',
        'full':full,'lite':lite,
        'notes':'Smoothly varying spatial kernels remove the fixed R14 y=0.36 plane; no source points moved. Source may lack separately identifiable cerebellum. Do not infer from high weights that an anatomical region exists.',
        'references':['https://pubmed.ncbi.nlm.nih.gov/19226510/',
                      'https://sketchfab.com/3d-models/brain-point-cloud-c427ea0aee214141a78eba37bf9b76bb']
    }
    (root/'manifest_r16.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    assert sha(src)==before_src and sha(fib)==before_fib
    for f in (full,lite):
        b=gzip.decompress((root/Path(f['file']).name).read_bytes())
        assert b[:4]==b'HQW6' and struct.unpack_from('<I',b,4)[0]==f['points']
        assert len(b)==8+8*f['points']
    print(json.dumps({'original_points':n,'candidate_classes':len(REGION_NAMES),
                      'dominant':dict(dominant),
                      'mean_weights':{REGION_NAMES[i]:round(sums[i]/(n*255),4) for i in range(8)},
                      'full_compressed_bytes':full['bytes'],
                      'lite_compressed_bytes':lite['bytes'],
                      'source_unchanged':True},indent=2))
    return manifest

if __name__=='__main__':build(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'docs/assets')
