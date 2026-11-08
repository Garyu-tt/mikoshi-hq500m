#!/usr/bin/env python3
"""R16 sidecar: schematic region memberships for 520,150 R11 visible fibers.
Each record has FROM region, TO region, FROM strength and TO strength (4 uint8).
These are direct Q0.8 *sampled* segments, not reconstructed axons.
"""
import gzip, hashlib, json, struct, sys
from collections import Counter
from pathlib import Path
from build_r16_soft_regions import field
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root):
    raw=gzip.decompress((root/'hq500m_exact_fibers_r11.bin.gz').read_bytes())
    assert raw[:4]==b'HQF3'
    lo,hi=struct.unpack_from('<II',raw,4)
    count=lo+hi
    assert len(raw)==12+12*count
    table=bytearray(count*4)
    counts=Counter()
    for i,(ax,ay,az,bx,by,bz) in enumerate(struct.iter_unpack('<6H',raw[12:])):
        aw=field(ax/65535,ay/65535,az/65535)
        bw=field(bx/65535,by/65535,bz/65535)
        a=max(range(8),key=lambda k:aw[k])
        b=max(range(8),key=lambda k:bw[k])
        table[i*4:i*4+4]=bytes((a,b,min(255,round(aw[a]*255)),min(255,round(bw[b]*255))))
        counts[(a,b)]+=1
    target=root/'hq500m_fiber_regions_r16.bin.gz'
    rawmeta=b'HQE6'+struct.pack('<II',lo,hi)+table
    target.write_bytes(gzip.compress(rawmeta,compresslevel=7,mtime=0))
    assert sha(root/'hq500m_exact_fibers_r11.bin.gz')==json.loads((root/'manifest_r11.json').read_text())['edge_geometry']['sha256']
    info={'format':'HQE6, u32 local count, u32 long count, 4 u8 per sampled directed segment: from_region,to_region,from_weight,to_weight',
       'total_edges':count,'local_edges':lo,'long_edges':hi,'sha256':sha(target),'compressed_bytes':target.stat().st_size,
       'derived_from_R11_sampled_geometry_only':True,
       'anatomical_verified':False,
       'note':'Direct sampled segments projected to R16 schematic regions; no assertions of continuous synaptic paths'}
    (root/'manifest_r16_fiber_regions.json').write_text(json.dumps(info,indent=2)+'\n')
    print('R16 sampled fibers',count,'transitions',len(counts),'sidecar bytes',target.stat().st_size)
    print('sample directional transition counts',counts.most_common(12))
if __name__=='__main__': build(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'docs/assets')
