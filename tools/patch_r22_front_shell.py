#!/usr/bin/env python3
"""Refine R22: allocate GPU LOD on camera-visible HRA shell anchors only."""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
f=P/'docs/procedural/procedural_r22.js'
s=f.read_text()
def swap(a,b):
 global s
 count=s.count(a)
 assert count==1,(count,a[:100])
 s=s.replace(a,b)
swap('let P=null,L=null,Mask=null,pg=null,lg=null,mg=null,maskCount=0,maskActual=false,maskBias=.0022,maskFootprint=7.0,loading=false;',
'''let P=null,L=null,Mask=null,pg=null,lg=null,mg=null,maskCount=0,maskActual=false,maskBias=.0022,maskFootprint=6.0,loading=false;
let shellMaskXYZ=null,shellRegionIds=null,shellLocalIds=null,visibleShell=null,visibleStencil=0,viewStamp="";''')
start=s.index('function buildDepthStencil(){')
end=s.index('function allocation(n){',start)
s=s[:start]+'''function buildDepthStencil(){
 const verts=[],regionIds=[],localIds=[];
 for(const r of rows){
  if(!outer(r)||r.shell_count<1)continue;
  for(let j=0;j<r.shell_count;j++){
   verts.push(...cell(r.shell_start+j));
   regionIds.push(r.index);localIds.push(j);
  }
 }
 shellMaskXYZ=new Float32Array(verts);
 shellRegionIds=new Uint16Array(regionIds);
 shellLocalIds=new Uint32Array(localIds);
 visibleShell=null;viewStamp="";
 free(mg);
 mg=verts.length?make(verts,3,[[0,3,0]]):null;
 maskCount=verts.length/3;
 if(maskCount<15000||maskCount>80000)throw Error("Некорректный шаблон видимости HRA");
 return maskCount;
}
// Camera-dependent coarse occlusion, using ONLY 46.5K existing HRA
// geometric shell samples. No hidden synthetic neuron XYZ array is built.
function ensureFrontShell(){
 const stamp=[yaw.toFixed(4),pitch.toFixed(4),distance.toFixed(3),
   graphZoom.toFixed(3),center.join(","),C.clientWidth,C.clientHeight].join("|");
 if(visibleShell&&viewStamp===stamp)return visibleShell;
 if(!shellMaskXYZ||!maskCount)return null;
 const width=Math.max(1,C.clientWidth),height=Math.max(1,C.clientHeight),tile=7;
 const tilesX=Math.ceil(width/tile),tilesY=Math.ceil(height/tile);
 const nearest=new Float32Array(tilesX*tilesY).fill(Infinity);
 const positions=new Int32Array(maskCount).fill(-1);
 const depth=new Float32Array(maskCount);
 const c=Math.cos(yaw),s=Math.sin(yaw),u=Math.cos(pitch),v=Math.sin(pitch);
 for(let i=0;i<maskCount;i++){
  const off=i*3,x=(shellMaskXYZ[off]-center[0])*graphZoom,
    y=(shellMaskXYZ[off+1]-center[1])*graphZoom,
    z=(shellMaskXYZ[off+2]-center[2])*graphZoom;
  const xx=c*x+s*z,zz=-s*x+c*z;
  const yy=u*y-v*zz,rz=v*y+u*zz;
  const d=Math.max(.12,distance-rz);
  const px=width*.5+1.025*xx/d*height;
  const py=height*.5-1.025*yy/d*height;
  if(px<0||py<0||px>=width||py>=height)continue;
  const tx=Math.floor(px/tile),ty=Math.floor(py/tile);
  const at=ty*tilesX+tx;
  positions[i]=at;depth[i]=d;
  if(d<nearest[at])nearest[at]=d;
 }
 const grouped=new Map();
 for(let i=0;i<maskCount;i++){
  const at=positions[i];if(at<0)continue;
  const tx=at%tilesX,ty=Math.floor(at/tilesX);
  let closest=Infinity;
  for(let v=-1;v<=1;v++){
   const y=ty+v;if(y<0||y>=tilesY)continue;
   for(let u=-1;u<=1;u++){
    const x=tx+u;if(x<0||x>=tilesX)continue;
    closest=Math.min(closest,nearest[y*tilesX+x]);
   }
  }
  // Preserve near-surface gyrus folds, discard deeper/superposed regions.
  if(depth[i]>closest+.18)continue;
  const rid=shellRegionIds[i];
  if(!grouped.has(rid))grouped.set(rid,[]);
  grouped.get(rid).push(shellLocalIds[i]);
 }
 visibleShell=new Map([...grouped.entries()].map(([k,v])=>[k,Uint32Array.from(v)]));
 visibleStencil=0;
 for(const v of visibleShell.values())visibleStencil+=v.length;
 viewStamp=stamp;
 return visibleShell;
}
''' + s[end:]
swap('''function shellPosition(r,j,k){
 const index=Math.min(r.shell_count-1,Math.floor((j+.5)/k*r.shell_count));''',
'''function shellPosition(r,j,k){
 const front=selected<0&&tract<0&&!focusedGraph&&$("occludeBack").checked
   ?visibleShell?.get(r.index):null;
 const index=front&&front.length?
   front[Math.min(front.length-1,Math.floor((j+.5)/k*front.length))]:
   Math.min(r.shell_count-1,Math.floor((j+.5)/k*r.shell_count));''')
swap(''' const B=budget(),choice=rows[selected],back=$("background").value;
 const active=rows.filter(r=>r.shell_count>0&&(selected<0?outer(r):r.index===selected||(back!=="hide"&&outer(r))));''',
''' const B=budget(),choice=rows[selected],back=$("background").value;
 const front=selected<0&&tract<0&&!focusedGraph&&$("occludeBack").checked
   ?ensureFrontShell():null;
 const active=rows.filter(r=>r.shell_count>0&&
   (selected<0?outer(r):r.index===selected||(back!=="hide"&&outer(r)))&&
   (!front||((front.get(r.index)?.length||0)>0)));''')
swap(''' $("occludeBack").onchange=()=>{dirty=true;readout();};''',
''' $("occludeBack").onchange=()=>{visibleShell=null;viewStamp="";later();};''')
swap('''const release=e=>{touches.delete(e.pointerId);pinch=0;};''',
'''const release=e=>{
  touches.delete(e.pointerId);pinch=0;
  if(!touches.size&&$("occludeBack").checked&&selected<0&&!focusedGraph)later();
};''')
swap(''' C.addEventListener("wheel",e=>{e.preventDefault();distance=Math.max(1.2,Math.min(10,distance*Math.exp(e.deltaY*.001)));dirty=true;},{passive:false});''',
''' let wheelSync=null;
 C.addEventListener("wheel",e=>{
  e.preventDefault();
  distance=Math.max(1.2,Math.min(10,distance*Math.exp(e.deltaY*.001)));dirty=true;
  if(wheelSync!==null)clearTimeout(wheelSync);
  wheelSync=setTimeout(()=>{wheelSync=null;
    if($("occludeBack").checked&&selected<0&&!focusedGraph)later();
  },160);
 },{passive:false});''')
swap('''sourceSurfaceStencil:maskCount,bias:maskBias,splatPx:maskFootprint,registeredToHRA:true,''',
'''sourceSurfaceStencil:maskCount,frontSurfaceStencil:visibleStencil,
     frontFraction:maskCount?visibleStencil/maskCount:0,
     bias:maskBias,splatPx:maskFootprint,registeredToHRA:true,''')
swap('''$("occludeBack").checked=!!value;dirty=true;readout();''',
'''$("occludeBack").checked=!!value;visibleShell=null;viewStamp="";later();''')
f.write_text(s)
print("R22 view-dependent front-LOD sampling",len(s),"bytes")
