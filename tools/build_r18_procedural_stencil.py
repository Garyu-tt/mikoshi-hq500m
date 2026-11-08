#!/usr/bin/env python3
"""R18 compact HRA anatomical template, not a stored neuron cloud.
Uses original HRA meshes for surface templates and NeutralLab R04 registered
V5 synthetic voxel positions for coarse interior templates; both are distinct
from real, measured neurons. Only Python standard library required.
"""
from __future__ import annotations
import array, bisect, gzip, hashlib, json, math, random, re, struct
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HRA=Path('/home/mirbi/projects/neutrallab-web-r04/assets/hra-brain-male-v1.3.glb')
V5=Path('/home/mirbi/projects/neutrallab-web-r04/assets/registered/v5-hra-registered-110404.bin')
CAT=Path('/home/mirbi/projects/neutrallab-web-r04/assets/registered/v5-hra-registered-manifest.json')
ASSETS=ROOT/'docs/assets'
REFERENCE=86_100_000_000
BUDGETS={'cerebellum':69_030_000_000,'cortex':16_340_000_000,'other':730_000_000}
EXCLUDED=('white_matter','optic_tract','optic_radiation','olfactory_tract',
 'corpus_callosum','commissure','fornix','mammillothalamic_tract','peduncle',
 'stria_terminalis','cerebral_aqueduct','ventricle','central_canal',
 'pineal_body','optic_chiasm')
CORTEX=('cortex','gyrus','gyri','lobule','cuneus','precuneus','operculum',
  'insula','planum','piriform_region','parahippocampal','paracingulate',
  'cingulate','perirhinal','poles','_pole_','_pole','limen_')
CEREB=('cerebellar_vermis','paravermis_of_cerebellum','lateral_hemisphere_of_cerebellum')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def classify(name,rec):
 n=name.lower()
 if rec['cavity_excluded'] or any(s in n for s in ('ventricle','central_canal','cerebral_aqueduct')):
  return 'cavity'
 if any(s in n for s in EXCLUDED): return 'tract'
 if any(s in n for s in CEREB): return 'cerebellum'
 if any(s in n for s in CORTEX):return 'cortex'
 return 'other'
def quota(weights,total):
 """Stable integer Hamilton apportionment; no fictional per-region measurements."""
 if total==0:return [0]*len(weights)
 assert sum(weights)>0
 q=sum(weights)
 floor=[(total*v)//q for v in weights]
 missing=total-sum(floor)
 ranked=sorted(range(len(weights)),key=lambda i: (-(total*weights[i])%q,i))
 # Avoid modulo negative confusion: sort exactly by fractional remainder descending
 ranked=sorted(range(len(weights)),key=lambda i:(-(total*weights[i]%q),i))
 for i in ranked[:missing]:floor[i]+=1
 assert sum(floor)==total
 return floor
def unpack_accessor(spec,accessor_id,chunk,components):
 acc=spec['accessors'][accessor_id]
 view=spec['bufferViews'][acc['bufferView']]
 fmt={5123:'H',5125:'I',5126:'f'}[acc['componentType']]
 stride=view.get('byteStride',struct.calcsize(fmt)*components)
 begin=view.get('byteOffset',0)+acc.get('byteOffset',0)
 assert stride==struct.calcsize(fmt)*components,('unsupported strided HRA',accessor_id)
 tupfmt='<'+fmt*components
 return [x for x in struct.iter_unpack(tupfmt,chunk[begin:begin+acc['count']*stride])]
def load_meshes():
 raw=HRA.read_bytes()
 assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,4)[0]==2
 slen=struct.unpack_from('<I',raw,12)[0]
 spec=json.loads(raw[20:20+slen])
 start=20+slen
 assert raw[start+4:start+8]==b'BIN\x00'
 blen=struct.unpack_from('<I',raw,start)[0]
 binary=raw[start+8:start+8+blen]
 assert len(spec['meshes'])==283
 return spec,binary
def build():
 ASSETS.mkdir(exist_ok=True)
 reg=json.loads(CAT.read_text())
 assert sha(HRA)==reg['atlas_sha256']
 assert sha(V5)==reg['out_sha256']
 catalog=reg['region_catalog']
 spec,binary=load_meshes()
 assert len(catalog)==len(spec['meshes'])==283
 mins=[1e9]*3;maxs=[-1e9]*3
 for mesh in spec['meshes']:
  pos=spec['accessors'][mesh['primitives'][0]['attributes']['POSITION']]
  for k in range(3):
   mins[k]=min(mins[k],pos['min'][k]);maxs[k]=max(maxs[k],pos['max'][k])
 center=[(mins[k]+maxs[k])/2 for k in range(3)]
 extent=max(maxs[i]-mins[i] for i in range(3))
 assert .1<extent<1
 def packed_xyz(p):
  return [max(0,min(65535,round(((p[k]-center[k])/extent+.5)*65535))) for k in range(3)]
 rr=V5.read_bytes()
 assert rr[:4]==b'NLRC' and struct.unpack_from('<III',rr,4)==(2,110404,20)
 volume=[[] for _ in catalog]
 for slot,x,y,z,rid,group,quality in struct.iter_unpack('<IfffHBB',rr[16:]):
  assert 0<=rid<283
  volume[rid].append((x,y,z))
 assert all(len(volume[i])==r['count'] for i,r in enumerate(catalog))
 types=[classify(rec['name'],rec) for rec in catalog]
 # Use V5 occupancy counts as *relative volume proxies* within each broad
 # tissue class; they are not measured region-specific neuronal counts.
 allocated=[0]*283
 for kind,budget in BUDGETS.items():
  ix=[i for i,t in enumerate(types) if t==kind and volume[i]]
  q=quota([len(volume[i]) for i in ix],budget)
  for i,v in zip(ix,q):allocated[i]=v
 assert sum(allocated)==REFERENCE
 # Decode real anatomical boundary surfaces once, but never display meshes.
 # Store a compact surface-only point stencil plus the V5 interior cell stencil.
 SURFACE_BUDGET=78_000
 meshes=[]
 surface_areas=[]
 for rid,mesh in enumerate(spec['meshes']):
  primitive=mesh['primitives'][0]
  assert primitive.get('mode',4)==4
  pos=unpack_accessor(spec,primitive['attributes']['POSITION'],binary,3)
  inds=unpack_accessor(spec,primitive['indices'],binary,1)
  tris=[]
  area_sum=0.
  for n in range(0,len(inds),3):
   a,b,c=(pos[inds[n+j][0]] for j in range(3))
   ux,uy,uz=(b[j]-a[j] for j in range(3))
   vx,vy,vz=(c[j]-a[j] for j in range(3))
   area=.5*math.sqrt((uy*vz-uz*vy)**2+(uz*vx-ux*vz)**2+(ux*vy-uy*vx)**2)
   if area<1e-16:continue
   area_sum+=area
   tris.append((area_sum,a,b,c))
  meshes.append(tris);surface_areas.append(area_sum)
 # Surface quota: area-weighted with a floor so small structures are accessible.
 floors=[max(12,round(SURFACE_BUDGET*area/sum(surface_areas))) if area>0 else 0 for area in surface_areas]
 total_surface=sum(floors)
 # capped memory, area weighting; no neuron IDs stored
 assert total_surface<90_000,total_surface
 shell=[[] for _ in catalog]
 for rid,(tris,count,area) in enumerate(zip(meshes,floors,surface_areas)):
  if not tris or count<=0:continue
  cdf=[t[0] for t in tris];rnd=random.Random(71017+rid*7919)
  for j in range(count):
   v=(j+rnd.random())/count*area
   ix=bisect.bisect_left(cdf,v)
   _,a,b,c=tris[min(ix,len(tris)-1)]
   u=rnd.random();v=rnd.random()
   su=math.sqrt(u)
   alpha,beta,gamma=1-su,su*(1-v),su*v
   p=tuple(alpha*a[k]+beta*b[k]+gamma*c[k] for k in range(3))
   shell[rid].append(p)
 # Order cells by atlas region to support O(1) region indexing from JS.
 records=bytearray()
 rows=[]
 for rid,rec in enumerate(catalog):
  vstart=len(records)//8
  for p in volume[rid]:
   records+=struct.pack('<4H',*packed_xyz(p),rid)
  vcount=len(volume[rid])
  sstart=len(records)//8
  for p in shell[rid]:
   records+=struct.pack('<4H',*packed_xyz(p),rid)
  rows.append({'index':rid,'name':rec['name'],'label':rec['label'],
    'group':rec['group'],'type':types[rid],
    'cells_start':vstart,'cells_count':vcount,
    'shell_start':sstart,'shell_count':len(shell[rid]),
    'neuron_quota_86_1b':allocated[rid],
    'surface_area_proxy_m2':round(surface_areas[rid],10),
    'is_anatomical_reference':True,
    'quota_is_measured':False,
    'excluded_cavity':rec['cavity_excluded'],
    'registration_quality': 'HRA reference surface; interior cells are estimated V5 geometric fit'})
 assert len(records)//8 == 110404+total_surface
 payload=b'HST8'+struct.pack('<III',1,len(rows),len(records)//8)+records
 target=ASSETS/'hra_procedural_stencil_r18.bin.gz'
 target.write_bytes(gzip.compress(payload,compresslevel=6,mtime=0))
 manifest={
 'version':'R18','generated_at':datetime.now(timezone.utc).isoformat(),
 'source':'HRA/Allen brain male v1.3, CC BY 4.0',
 'source_url':'https://3d.nih.gov/entries/3DPX-020960?version=1',
 'reference_HRA_sha256':sha(HRA),
 'reference_NeutralLab_registration_sha256':sha(V5),
 'source_registered_V5_voxel_slots':110404,
 'original_mesh_count':283,
 'anatomical_surface_samples':total_surface,
 'raw_stencil_bytes':len(payload),
 'stencil_sha256':sha(target),
 'stencil_asset':'assets/'+target.name,
 'format':'HST8 + u32 version, region count, records count + 8-byte records (u16 XYZ in normalized HRA frame + u16 region index); region offsets in manifest',
 'coordinates':'HRA source mesh frame, isotropically normalized: (p-center)/global_max_extent + 0.5, u16',
 'center_m':center,'max_extent_m':extent,
 'reference_86_1b_neuron_budget':BUDGETS,
 'allocation_method':'Azevedo 2009 broad cerebellum/cerebral cortex/other biological neuron estimates; within each class allocate using relative NeutralLab V5 voxel occupancy as a heuristic, NOT measured region counts',
 'white_matter_and_cavities_have_soma_quota_zero':True,
 'biological_neuron_count_at_each_HRA_region_measured':False,
 'dynamic_total_neurons':'Quotas are recomputed at runtime by largest-remainder scaling; only bounded LOD sample points are instantiated in the browser',
 'never_infer_real_synapses':True,
 'no_86_billion_materialized_cells':True,
 'surface_stencil':'Original HRA triangle surfaces uniformly sampled by triangle area; points are not original biological neuron coordinates',
 'interior_stencil':'NeutralLab R04 estimated V5 mapped voxel centers; each is a procedural seed not a neuron',
 'no_existing_HQ500M_Terrie_geometry_changed':True,
 'no_existing_Q08_connectome_changed':True,
 'regions':rows
 }
 dest=ASSETS/'manifest_r18.json'
 dest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'regions':len(rows),'active_soma_regions':sum(r['neuron_quota_86_1b']>0 for r in rows),
 'volume_cells':110404,'surface_stencil_points':total_surface,
 'compressed_bytes':target.stat().st_size,'neurons_per_class':BUDGETS,
 'soma_zero_regions':Counter(types)},indent=2))
 return manifest
if __name__=='__main__':build()
