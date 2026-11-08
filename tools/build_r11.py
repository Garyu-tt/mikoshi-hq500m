#!/usr/bin/env python3
"""Build genuine source-point and deterministic Q0.8-edge render assets.
Spatial mapping is synthetic. No measured axonal paths or 500M live cells.
Source: Terrie Simmons-Ehrhardt, Brain Point Cloud, CC BY 4.0.
"""
import bisect, gzip, hashlib, json, struct, sys, time
from pathlib import Path
import numpy as np

N=500_000_000
K=0x517cc1b727220a95
MASK=(1<<64)-1
REG=(0,224999424,294999040,344999936,394999808,434999296,469999616,N)
ROUTE=(3,5,0,0,3,1,2)
SLOTS_LOCAL=(0,1,3,6,12,18,23)
SLOTS_GLOBAL=(24,27,30)

def mix(x):
    x=(x+0x9e3779b97f4a7c15)&MASK
    x=((x^(x>>30))*0xbf58476d1ce4e5b9)&MASK
    x=((x^(x>>27))*0x94d049bb133111eb)&MASK
    return x^(x>>31)

def target_of(src,slot):
    r=bisect.bisect_right(REG,src)-1
    h0=mix(src^37421);h=mix(h0^(((slot+1)*K)&MASK))
    if slot<24:
        st=(src//1024)*1024
        odd=((h0>>11)&0xffffffff)|1
        return st+(((src-st+(slot+1)*odd)&0xffffffff)%min(1024,N-st))
    rr=ROUTE[r];st=REG[rr];end=REG[rr+1]
    modules=(end-st+1023)//1024
    mb=st+(mix(h^(src//1024))%modules)*1024
    return mb+((h>>24)%min(1024,end-mb))

def morton(v):
    v=v.astype(np.uint64)
    v=(v|(v<<32))&np.uint64(0x1f00000000ffff)
    v=(v|(v<<16))&np.uint64(0x1f0000ff0000ff)
    v=(v|(v<<8))&np.uint64(0x100f00f00f00f00f)
    v=(v|(v<<4))&np.uint64(0x10c30c30c30c30c3)
    v=(v|(v<<2))&np.uint64(0x1249249249249249)
    return v

def load_glb(path):
    binary=Path(path).read_bytes()
    assert binary[:4]==b'glTF'
    n=struct.unpack_from('<I',binary,12)[0]
    spec=json.loads(binary[20:20+n])
    base=20+n
    assert binary[base+4:base+8]==b'BIN\x00'
    base+=8
    views=spec['bufferViews'];accessors=spec['accessors']
    positions=[];colors=[];sizes=[]
    for mesh in spec['meshes']:
        primitive=mesh['primitives'][0]
        assert primitive['mode']==0
        def values(name,components):
            ac=accessors[primitive['attributes'][name]]
            view=views[ac['bufferView']]
            assert ac['componentType']==5126 and view['byteStride']==components*4
            o=base+view.get('byteOffset',0)+ac.get('byteOffset',0)
            return np.frombuffer(binary,dtype='<f4',count=ac['count']*components,offset=o).reshape(-1,components)
        pos=values('POSITION',3);col=values('COLOR_0',4)
        assert len(pos)==len(col)
        positions.append(pos.copy());colors.append(col.copy());sizes.append(len(pos))
    p=np.concatenate(positions)
    c=np.concatenate(colors)
    mat=np.array(spec['nodes'][0]['matrix'],dtype=np.float32).reshape(4,4,order='F')
    world=p@mat[:3,:3].T+mat[:3,3]
    lo=world.min(0);hi=world.max(0)
    center=(lo+hi)*.5
    radius=float(np.max(hi-lo)*.5)
    norm=np.clip((world-center)/radius,-1,1).astype('f4')
    print('SOURCE',len(p),'groups',len(sizes),'bbox',lo,hi,flush=True)
    assert len(p)==1192673 and len(sizes)==19
    return norm,np.clip(c,0,1),sizes,hashlib.sha256(binary).hexdigest()

def write_asset(out,name,raw):
    target=out/name
    target.write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    print(name,len(raw),'->',target.stat().st_size,flush=True)
    return {'file':'assets/'+name,'bytes':target.stat().st_size,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

def build(src,out):
    out.mkdir(parents=True,exist_ok=True)
    p,c,sizes,source_hash=load_glb(src)
    size=len(p);q=np.rint((p+1)*32767.5).clip(0,65535).astype('<u2')
    cbytes=np.rint(c*255).clip(0,255).astype('u1')
    # Source color controls ruby contrast and sparse blue sulcal accent.
    attrib=np.zeros((size,8),dtype='u1')
    attrib[:,:6]=q.view('u1').reshape(-1,6)
    attrib[:,6]=cbytes[:,2]
    attrib[:,7]=cbytes[:,0]
    points_raw=b'HQP3'+struct.pack('<I',size)+attrib.tobytes()
    point_meta=write_asset(out,'hq500m_source_points_r11.bin.gz',points_raw)
    lite=attrib[::4].copy()
    lite_meta=write_asset(out,'hq500m_source_points_lite_r11.bin.gz',
                          b'HQP3'+struct.pack('<I',len(lite))+lite.tobytes())
    # Assign each exact virtual address to a spatially sorted original source
    # point, without changing its original ID or exact Q0.8 target.
    counts=[N*int(x)//size for x in sizes]
    for i in range(N-sum(counts)):counts[i]+=1
    gstart=np.cumsum([0]+counts).tolist()
    start_points=np.cumsum([0]+sizes).tolist()
    sorted_points=[];rank=np.empty(size,dtype=np.int32)
    for g,(first,n) in enumerate(zip(start_points,sizes)):
        xyz=np.rint((p[first:first+n]+1)*511.5).clip(0,1023).astype('u2')
        code=morton(xyz[:,0])|(morton(xyz[:,1])<<np.uint64(1))|(morton(xyz[:,2])<<np.uint64(2))
        order=np.argsort(code,kind='stable').astype(np.int32)
        rank[first+order]=np.arange(n,dtype=np.int32)
        sorted_points.append(order+first)
    def pos_id(nid):
        g=bisect.bisect_right(gstart,nid)-1
        if g>=len(sizes):g=len(sizes)-1
        ix=(nid-gstart[g])*sizes[g]//counts[g]
        return q[int(sorted_points[g][ix])]
    # Visual fibers are exact edges in a SYNTHETIC atlas, not measured paths.
    # Every seed corresponds to a point on the outer shell from R10.
    shell_path=out/'hq500m_surface_shell_160.vox.gz'
    if shell_path.exists():
        raw=gzip.decompress(shell_path.read_bytes())
        assert raw[:4]==b'HQS2'
        nn,expected=struct.unpack_from('<II',raw,4)
        assert nn==160
        bl=(nn**3+7)//8
        shell=np.unpackbits(np.frombuffer(raw[12:12+bl],dtype=np.uint8),
                            bitorder='little')[:nn**3]
        normlo=p.min(0);normhi=p.max(0)
        vox=np.rint((p-normlo)/(normhi-normlo)*(nn-1)).clip(0,nn-1).astype('i4')
        linear=(vox[:,0]*nn+vox[:,1])*nn+vox[:,2]
        surface=np.flatnonzero(shell[linear]).astype(np.int32)
        print('EXTERIOR SEEDS',len(surface),'of',len(p),flush=True)
    else:
        # conservative fallback for source geometry not yet voxelized
        r2=np.sum(p*p,axis=1)
        surface=np.flatnonzero(r2>np.quantile(r2,.94)).astype(np.int32)
    local=bytearray();long=bytearray()
    lengths=[]
    for j,pi in enumerate(surface):
        idx=int(pi)
        g=bisect.bisect_right(start_points,idx)-1
        base=gstart[g]+int(rank[idx])*counts[g]//sizes[g]
        bucket=max(1,counts[g]//sizes[g])
        srcid=min(gstart[g+1]-1,base+(mix(idx^37421)%bucket))
        a=pos_id(srcid)
        for slot in SLOTS_LOCAL+SLOTS_GLOBAL:
            dst=target_of(srcid,slot)
            b=pos_id(dst)
            # Neuron IDs and endpoints are exact; paths are straight
            # illustrative segments, without invented extra connections.
            payload=struct.pack('<6H',*(int(v) for v in a),
                                *(int(v) for v in b))
            if slot<24:
                local.extend(payload)
            else:long.extend(payload)
        if j%10000==0:print('FIBERS',j,'/',len(surface),flush=True)
    nl=len(local)//12;ng=len(long)//12
    # Header and separate byte runs make it cheap to toggle fiber families.
    edges_raw=b'HQF3'+struct.pack('<II',nl,ng)+local+long
    fiber_meta=write_asset(out,'hq500m_exact_fibers_r11.bin.gz',edges_raw)
    man={'schema':'hq500m-interactive-atlas-r11','source':'Brain Point Cloud by Terrie Simmons-Ehrhardt',
         'source_url':'https://sketchfab.com/3d-models/brain-point-cloud-c427ea0aee214141a78eba37bf9b76bb',
         'source_license':'CC BY 4.0','source_sha256':source_hash,
         'source_points':size,'source_groups':len(sizes),
         'virtual_addresses':N,'potential_connections':N*32,
         'point_geometry':point_meta,'lite_point_geometry':lite_meta,
         'edge_geometry':fiber_meta,'visible_surface_seed_count':len(surface),
         'local_edges_sampled':nl,'long_edges_sampled':ng,'total_edges_sampled':nl+ng,
         'edge_algorithm':'HQ500M Q0.8 exact deterministic 32-slot endpoints (seed 37421)',
         'spatial_atlas':'synthetic 19-group Morton sorted mapping to Terrie source positions',
         'render_convention':'True source geometry, viewport depth testing; sampled exact edge endpoints as illustrative straight segments. No reconstructed biological axon trajectories.',
         'not_a_human_connectome':True,'simultaneously_active_500m':False}
    (out/'manifest_r11.json').write_text(json.dumps(man,indent=2),encoding='utf-8')
    print('RESULT',json.dumps({'source_points':size,'edges':nl+ng,'sizes':[point_meta['bytes'],fiber_meta['bytes']]},indent=2),flush=True)

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: build_r11.py brain_point_cloud.glb docs/assets')
    build(Path(sys.argv[1]),Path(sys.argv[2]))
