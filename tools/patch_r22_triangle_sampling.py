#!/usr/bin/env python3
"""R22: sample actual HRA triangles on the view-visible surface, not sparse anchors."""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
f=P/'docs/procedural/procedural_r22.js'
s=f.read_text()
def swap(a,b):
 global s
 n=s.count(a)
 assert n==1,(n,a[:120])
 s=s.replace(a,b)
swap('let shellMaskXYZ=null,shellRegionIds=null,shellLocalIds=null,visibleShell=null,visibleStencil=0,viewStamp="";',
'''let shellMaskXYZ=null,shellRegionIds=null,shellLocalIds=null,visibleShell=null,visibleStencil=0,viewStamp="";
let frontDepthGrid=null,triMeta=null,triVerts=null,triIndices=null,triRaw=null,triFull=new Map(),triVisible=null,triStamp="",frontTriangleCount=0;''')
swap(''' const grouped=new Map();
 for(let i=0;i<maskCount;i++){''',
''' frontDepthGrid={nearest,tilesX,tilesY,tile,width,height};
 const grouped=new Map();
 for(let i=0;i<maskCount;i++){''')

insert='''// HTR2 is a compact exact HRA triangle template, NOT a rendered atlas mesh.
// At each camera pose we retain areas facing the image; draw-time barycentric
// sampling generates unique display points without materializing billions.
function triangleVertices(r,j){
 const meta=triMeta.regions[r.index],start=3*(meta.triangle_start+j);
 const offset=3*meta.vertex_start,verts=[];
 for(let v=0;v<3;v++){
  const ind=triIndices[start+v],base=offset+ind*3;
  verts.push([triVerts[base]/32767.5-1,
              triVerts[base+1]/32767.5-1,
              triVerts[base+2]/32767.5-1]);
 }
 return verts;
}
function triangleArea(a,b,c){
 const x=b[0]-a[0],y=b[1]-a[1],z=b[2]-a[2];
 const xx=c[0]-a[0],yy=c[1]-a[1],zz=c[2]-a[2];
 return .5*Math.hypot(y*zz-z*yy,z*xx-x*zz,x*yy-y*xx);
}
function buildAreaList(r,allow){
 const mr=triMeta.regions[r.index],ids=[],cum=[];
 let totalArea=0;
 for(let i=0;i<mr.triangle_count;i++){
  const [a,b,c]=triangleVertices(r,i);
  const area=triangleArea(a,b,c);
  if(area<=1e-12)continue;
  if(allow&&!allow(a,b,c))continue;
  totalArea+=area;ids.push(i);cum.push(totalArea);
 }
 return {ids:Uint32Array.from(ids),cdf:Float64Array.from(cum),
         totalArea,triangle_count:ids.length};
}
function fullTriangles(r){
 let v=triFull.get(r.index);
 if(v)return v;
 v=buildAreaList(r,null);
 triFull.set(r.index,v);
 return v;
}
function ensureVisibleTriangles(){
 if(!triMeta)return null;
 ensureFrontShell();
 if(triVisible&&triStamp===viewStamp)return triVisible;
 const grid=frontDepthGrid;
 if(!grid)return null;
 const c=Math.cos(yaw),s=Math.sin(yaw),u=Math.cos(pitch),v=Math.sin(pitch);
 const byRegion=new Map();
 let kept=0;
 // Avoid the old problem where 220K points collapsed onto 1.6K anchors:
 // sample actual source triangles after coarse HRA depth classification.
 const isNear=(a,b,d)=>{
  const x=(a[0]+b[0]+d[0])/3-center[0],
    y=(a[1]+b[1]+d[1])/3-center[1],
    z=(a[2]+b[2]+d[2])/3-center[2];
  const xx=c*x*graphZoom+s*z*graphZoom,
    zz=-s*x*graphZoom+c*z*graphZoom;
  const yy=u*y*graphZoom-v*zz,rz=v*y*graphZoom+u*zz;
  const depth=Math.max(.12,distance-rz);
  const px=grid.width*.5+1.025*xx/depth*grid.height;
  const py=grid.height*.5-1.025*yy/depth*grid.height;
  if(px<0||py<0||px>=grid.width||py>=grid.height)return false;
  const ix=Math.floor(px/grid.tile),iy=Math.floor(py/grid.tile);
  let near=Infinity;
  for(let dy=-1;dy<=1;dy++){
   const row=iy+dy;if(row<0||row>=grid.tilesY)continue;
   for(let dx=-1;dx<=1;dx++){
    const col=ix+dx;if(col<0||col>=grid.tilesX)continue;
    near=Math.min(near,grid.nearest[row*grid.tilesX+col]);
   }
  }
  return depth<=near+.18;
 };
 for(const r of rows){
  if(!outer(r)||!r.shell_count)continue;
  const list=buildAreaList(r,isNear);
  if(list.triangle_count){
   byRegion.set(r.index,list);kept+=list.triangle_count;
  }
 }
 triVisible=byRegion;triStamp=viewStamp;frontTriangleCount=kept;
 return triVisible;
}
function sampleTrianglePosition(r,j,count){
 if(!triMeta)return null;
 const narrow=selected<0&&tract<0&&!focusedGraph&&$("occludeBack").checked;
 const info=narrow?triVisible?.get(r.index):fullTriangles(r);
 if(!info||!info.ids.length||info.totalArea<=0)return null;
 const h=hash(r.index*47519+j*12073);
 const target=(j+rnd(h+8123))/count*info.totalArea;
 let lo=0,hi=info.ids.length-1;
 while(lo<hi){
  const mid=(lo+hi)>>>1;
  if(info.cdf[mid]<target)lo=mid+1;else hi=mid;
 }
 const [a,b,c]=triangleVertices(r,info.ids[lo]);
 const t=Math.sqrt(rnd(h+173)),v=rnd(h+7919);
 const ca=1-t,cb=t*(1-v),cc=t*v;
 return [0,1,2].map(k=>ca*a[k]+cb*b[k]+cc*c[k]);
}
'''
ix=s.index('function shellPosition(r,j,k){')
s=s[:ix]+insert+s[ix:]
swap('''function shellPosition(r,j,k){
 const front=''', '''function shellPosition(r,j,k){
 const sampled=sampleTrianglePosition(r,j,k);
 if(sampled)return sampled;
 const front=''')

swap('''const front=selected<0&&tract<0&&!focusedGraph&&$("occludeBack").checked
   ?ensureFrontShell():null;''',
'''const front=selected<0&&tract<0&&!focusedGraph&&$("occludeBack").checked
   ?ensureVisibleTriangles():null;''')
swap('''(!front||((front.get(r.index)?.length||0)>0)));''',
'''(!front||((front.get(r.index)?.triangle_count||0)>0)));''')

swap('''const [a,b]=await Promise.all([fetch("../assets/manifest_r18.json"),fetch("../assets/hra_procedural_stencil_r18.bin.gz")]);''',
'''const [a,b,tMeta]=await Promise.all([
 fetch("../assets/manifest_r18.json"),
 fetch("../assets/hra_procedural_stencil_r18.bin.gz"),
 fetch("../assets/manifest_r22_triangles.json")
]);''')
swap('''if(!a.ok||!b.ok)throw Error("HRA трафарет недоступен");''',
'''if(!a.ok||!b.ok||!tMeta.ok)throw Error("Неполный HRA трафарет R22");''')
swap(''' rows=meta.regions;
 let cursor=0;''',
''' triMeta=await tMeta.json();
 if(triMeta.HRA_reference_sha256!==meta.reference_HRA_sha256||
    triMeta.region_count!==283||triMeta.regions.length!==283)
   throw Error("Треугольный трафарет не совпадает с HRA v1.3");
 if(!Array.isArray(triMeta.parts)||!triMeta.parts.length||
    triMeta.parts.some(p=>typeof p.file!=="string"||p.bytes<=0))
   throw Error("Нет списка частей треугольного трафарета R22");
 // GitHub transfers each compressed HRA chunk independently; the browser
 // concatenates them byte-for-byte before gzip decoding.
 const partResponses=await Promise.all(triMeta.parts.map(p=>fetch("../"+p.file,{cache:"force-cache"})));
 if(partResponses.some(r=>!r.ok))throw Error("Не загружена часть HRA трафарета R22");
 const payloads=await Promise.all(partResponses.map(r=>r.arrayBuffer()));
 const compressed=new Uint8Array(triMeta.gzip_bytes);
 let offset=0;
 for(let i=0;i<payloads.length;i++){
  const chunk=new Uint8Array(payloads[i]);
  if(chunk.length!==triMeta.parts[i].bytes||
     offset+chunk.length>compressed.length)throw Error("Повреждена часть HRA трафарета");
  compressed.set(chunk,offset);offset+=chunk.length;
 }
 if(offset!==compressed.length)throw Error("Неполный поток HRA");
 triRaw=await new Response(new Blob([compressed]).stream()
   .pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
 const header=new DataView(triRaw);
 if(String.fromCharCode(...new Uint8Array(triRaw,0,4))!=="HTR2"||
    header.getUint32(4,true)!==1||header.getUint32(8,true)!==283)
   throw Error("Повреждён HTR2");
 const nv=header.getUint32(12,true),nt=header.getUint32(16,true);
 if(nv!==triMeta.vertex_count||nt!==triMeta.triangle_count||
    triRaw.byteLength!==20+(nv+nt)*6)throw Error("Неполная HTR2 геометрия");
 triVerts=new Uint16Array(triRaw,20,nv*3);
 triIndices=new Uint16Array(triRaw,20+nv*6,nt*3);
 rows=meta.regions;
 let cursor=0;''')
swap('''sourceSurfaceStencil:maskCount,frontSurfaceStencil:visibleStencil,''',
'''sourceSurfaceStencil:maskCount,frontSurfaceStencil:visibleStencil,
     eligibleHraTriangles:frontTriangleCount,sourceHraTriangles:triMeta?.triangle_count||0,''')
f.write_text(s)
print("R22 triangle sampling integrated; script bytes",len(s))
