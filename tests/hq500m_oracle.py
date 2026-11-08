#!/usr/bin/env python3
"""Independent Python oracle against the eight-GPU GENESIS HQ500M edge generator.
Reads ONLY the small JSON probe; checks every output edge (not the 16B virtual edges).
"""
import json,sys,pathlib
MASK=(1<<64)-1
N=500_000_000
MODULE=1024
K=0x517cc1b727220a95
REGIONS=[0]+[(n//1024)*1024 for n in (225_000_000,295_000_000,345_000_000,395_000_000,435_000_000,470_000_000)]+[N]
ROUTES=[3,5,0,0,3,1,2]
def mix(z):
 z=(z+0x9e3779b97f4a7c15)&MASK
 z=((z^(z>>30))*0xbf58476d1ce4e5b9)&MASK
 z=((z^(z>>27))*0x94d049bb133111eb)&MASK
 return z^(z>>31)
def region(n):
 for i in range(7):
  if REGIONS[i]<=n<REGIONS[i+1]:return i
 raise ValueError(n)
def expected(n,s):
 h0=mix(n^37421)
 r=region(n)
 t=1 if h0%100<20 else 0
 h=mix(h0^((s+1)*K&MASK))
 if s<24:
  beg=(n//MODULE)*MODULE
  sz=min(MODULE,N-beg)
  odd=((h0>>11)&0xffffffff)|1
  target=beg+((n-beg+(s+1)*odd)&0xffffffff)%sz
  gene=0
 else:
  d=ROUTES[r];start=REGIONS[d];end=REGIONS[d+1]
  nm=(end-start+MODULE-1)//MODULE
  picked=mix(h^(n//MODULE))%nm
  mb=start+picked*MODULE
  sz=min(MODULE,end-mb)
  target=mb+((h>>24)%sz)
  gene=r+1
 weight=300+((h>>33)%4800)
 if t:weight=-weight
 return [target,weight,gene,t]
def test(filename):
 x=json.loads(pathlib.Path(filename).read_text())
 assert x["addressable_neurons"]==N and x["addressable_synapses"]==16_000_000_000
 assert x["errors"]==0 and x["region_limits"]==REGIONS[1:]
 checked=0
 for sample in x["samples"]:
  src=sample["source"]
  assert 0<=src<N
  assert len(sample["edges"])==32
  for j,got in enumerate(sample["edges"]):
   want=expected(src,j)
   if got!=want:
    raise AssertionError(f"CPU-GPU mismatch source={src} slot={j} got={got} expected={want}")
   checked+=1
 print(json.dumps({"status":"PASS","cpu_oracle_verified_edges":checked,
                   "samples":len(x["samples"]),"entire_graph_materialized":False,
                   "boundary_probes":True,"genome_neurons":N,"potential_edges":N*32},indent=2))
if __name__=="__main__":test(sys.argv[1])
