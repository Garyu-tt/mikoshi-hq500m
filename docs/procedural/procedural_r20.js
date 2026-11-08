"use strict";
(()=>{
const $=id=>document.getElementById(id);
const C=$("scene"),S=$("status"),F=new Intl.NumberFormat("ru-RU");
const gl=C.getContext("webgl2",{alpha:false,antialias:true,depth:true});
const mobile=matchMedia("(max-width:760px), (pointer:coarse)").matches;
const REF=86100000000;
const palette={cerebellum:[.48,.31,.98],cortex:[.98,.12,.29],other:[.91,.53,.23],tract:[.22,.81,.95],cavity:[.25,.25,.3]};
let meta=null,rows=[],bytes=null,view=null,quotas=[],total=500000000;
let selected=-1,tract=-1,links=false,points=0,segments=0,dirty=true;
let yaw=.6,pitch=.18,distance=3.5,center=[0,0,0],graphZoom=1,touches=new Map(),pinch=0;
let P=null,L=null,pg=null,lg=null,loading=false;
const pointVS=[
"#version 300 es","precision highp float;",
"layout(location=0) in vec3 aPos;layout(location=1) in float aSize;layout(location=2) in vec3 aColor;",
"uniform float uYaw,uPitch,uDistance,uAspect,uHeight,uZoom;uniform vec3 uCenter;out vec3 vColor;",
"void main(){vec3 p=(aPos-uCenter)*uZoom;float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);",
"p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);p=vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);",
"float d=max(.12,uDistance-p.z);gl_Position=vec4(2.05*p.x/uAspect,2.05*p.y,d*1.003-.35,d);",
"gl_PointSize=clamp(aSize*uHeight/(130.*d),.75,8.);vColor=aColor*(.84+.22*clamp(p.z+.55,0.,1.));}"
].join("\n");
const pointFS=["#version 300 es","precision highp float;in vec3 vColor;out vec4 f;",
"void main(){float r=length(gl_PointCoord-vec2(.5))*2.;if(r>1.)discard;f=vec4(vColor*(1.15-.36*smoothstep(.1,1.,r)),1.);}"].join("\n");
const lineVS=["#version 300 es","precision highp float;layout(location=0) in vec3 aPos;layout(location=1) in vec3 aColor;",
"uniform float uYaw,uPitch,uDistance,uAspect,uZoom;uniform vec3 uCenter;out vec3 vColor;",
"void main(){vec3 p=(aPos-uCenter)*uZoom;float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);",
"p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);p=vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);",
"float d=max(.12,uDistance-p.z);gl_Position=vec4(2.05*p.x/uAspect,2.05*p.y,d*1.003-.36,d);vColor=aColor;}"].join("\n");
const lineFS=["#version 300 es","precision highp float;in vec3 vColor;out vec4 f;void main(){f=vec4(vColor,1.);}"].join("\n");
function shader(t,src){const s=gl.createShader(t);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
function prog(v,f){const p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,v));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));return p;}
function make(buffer,stride,layout){
 const g={v:gl.createVertexArray(),b:gl.createBuffer()};gl.bindVertexArray(g.v);gl.bindBuffer(gl.ARRAY_BUFFER,g.b);
 gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(buffer),gl.STATIC_DRAW);
 for(const [id,n,off] of layout){gl.enableVertexAttribArray(id);gl.vertexAttribPointer(id,n,gl.FLOAT,false,stride*4,off*4);}
 gl.bindVertexArray(null);return g;
}
function free(g){if(g){gl.deleteBuffer(g.b);gl.deleteVertexArray(g.v);}}
function uf(p,n,v){const a=gl.getUniformLocation(p,n);if(a===null)return;if(Array.isArray(v))gl.uniform3f(a,...v);else gl.uniform1f(a,v);}
function draw(){
 if(!gl||!P)return;dirty=false;
 const ratio=Math.min(devicePixelRatio||1,mobile?1.25:1.7);
 const w=Math.max(1,Math.round(C.clientWidth*ratio)),h=Math.max(1,Math.round(C.clientHeight*ratio));
 if(C.width!==w||C.height!==h){C.width=w;C.height=h;}
 gl.viewport(0,0,w,h);gl.clearColor(.015,.012,.018,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.depthMask(true);gl.disable(gl.BLEND);
 const common=p=>{gl.useProgram(p);uf(p,"uYaw",yaw);uf(p,"uPitch",pitch);uf(p,"uDistance",distance);uf(p,"uAspect",w/h);uf(p,"uCenter",center);uf(p,"uZoom",graphZoom);};
 if(pg&&points){common(P);uf(P,"uHeight",h);gl.bindVertexArray(pg.v);gl.drawArrays(gl.POINTS,0,points);}
 if(lg&&segments){gl.disable(gl.DEPTH_TEST);gl.depthMask(false);common(L);gl.bindVertexArray(lg.v);gl.drawArrays(gl.LINES,0,2*segments);gl.depthMask(true);gl.enable(gl.DEPTH_TEST);}
 gl.bindVertexArray(null);
}
function frame(){const r=Math.min(devicePixelRatio||1,mobile?1.25:1.7);if(dirty||C.width!==Math.round(C.clientWidth*r))draw();requestAnimationFrame(frame);}
if(gl){try{P=prog(pointVS,pointFS);L=prog(lineVS,lineFS);requestAnimationFrame(frame);}catch(e){S.textContent="Ошибка WebGL2: "+e.message;console.error(e);}}else S.textContent="Нужен WebGL2";
const hash=(x)=>{x=x>>>0;x^=x>>>16;x=Math.imul(x,0x7feb352d);x^=x>>>15;x=Math.imul(x,0x846ca68b);x^=x>>>16;return x>>>0;};
const rnd=x=>hash(x)/4294967296;
function cell(i){const off=16+i*8;return [0,2,4].map(j=>view.getUint16(off+j,true)/32767.5-1);}
function allocation(n){
 if(!Number.isSafeInteger(n)||n<1000||n>1e12)throw Error("Диапазон: от 1000 до 1 трлн");
 const fractions=rows.map(r=>n*r.neuron_quota_86_1b/REF);
 const q=fractions.map(Math.floor);
 let left=n-q.reduce((a,b)=>a+b,0);
 const order=fractions.map((v,i)=>({i,f:v-q[i]})).sort((a,b)=>b.f-a.f||a.i-b.i);
 if(left<0||left>order.length+1)throw Error("Ошибка квот");
 for(let j=0;j<left;j++)q[order[j%order.length].i]++;
 if(q.reduce((a,b)=>a+b,0)!==n)throw Error("Ошибка суммы");
 return q;
}
// Memory-safe LOD only; virtual population and region quotas never change.
function budget(){
 const slider=Number($("lod").value), mode=$("lodMode").value;
 const automatic=Math.max(12000,Math.round(220000*Math.pow(total/500000000,.22)));
 const cap=mobile?120000:1100000;
 return Math.min(total,cap,mode==="manual"?slider:Math.min(slider,automatic));
}
function color(r,chosen=false){
 if(chosen)return [1,.83,.64];
 const p=palette[r.type]||palette.other,tone=.90+.15*rnd(r.index*59363+17);
 return p.map(x=>Math.min(1,x*tone));
}
function outer(r){return r.type==="cortex"||r.type==="cerebellum"||r.group==="brainstem";}
const spatialOrders=new Map();
const regionCenters=new Map();
let regionRanges=[];
function mortonPart(n){
 n&=1023;n=(n|n<<16)&0x030000ff;
 n=(n|n<<8)&0x0300f00f;
 n=(n|n<<4)&0x030c30c3;
 n=(n|n<<2)&0x09249249;
 return n;
}
function regionSpatialOrder(r){
 if(spatialOrders.has(r.index))return spatialOrders.get(r.index);
 const values=[];
 let sum=[0,0,0];
 for(let i=0;i<r.cells_count;i++){
  const offset=16+(r.cells_start+i)*8;
  const x=view.getUint16(offset,true),y=view.getUint16(offset+2,true),z=view.getUint16(offset+4,true);
  const key=mortonPart(x>>>6)|(mortonPart(y>>>6)<<1)|(mortonPart(z>>>6)<<2);
  values.push([key,i]);sum[0]+=x/32767.5-1;sum[1]+=y/32767.5-1;sum[2]+=z/32767.5-1;
 }
 values.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
 const order=Uint32Array.from(values,v=>v[1]);
 spatialOrders.set(r.index,order);
 if(order.length)regionCenters.set(r.index,sum.map(v=>v/order.length));
 return order;
}
function volumePosition(r,ordinal){
 if(r.cells_count===0 || quotas[r.index]<=0)return null;
 const count=quotas[r.index], low=ordinal>>>0,hi=Math.floor(ordinal/4294967296)>>>0;
 const rank=Math.min(r.cells_count-1,Math.floor(ordinal/count*r.cells_count));
 const order=regionSpatialOrder(r);
 const p=cell(r.cells_start+order[rank]);
 const h=hash(low^hi^Math.imul(r.index+23,0x9e3779b1));
 const jitter=Math.min(.006,1.8e-3/meta.max_extent_m);
 return p.map((v,k)=>v+(rnd(h+Math.imul(k+1,0x51ed270b))-.5)*jitter);
}
function rebuildRanges(){
 regionRanges=[];let start=0;
 for(const r of rows){regionRanges.push(start);start+=quotas[r.index];}
 if(start!==total)throw Error("Neuron ID prefix sum mismatch");
}
function neuronForId(value){
 const id=Number(value);
 if(!Number.isSafeInteger(id)||id<0||id>=total)throw Error("Neuron ID outside current model range");
 let low=0,high=rows.length;
 while(low<high){
  const mid=(low+high)>>>1;
  if(regionRanges[mid]+quotas[mid]<=id)low=mid+1;
  else high=mid;
 }
 const r=rows[low];if(!r||quotas[low]<1)throw Error("Neuron ID maps to empty region");
 const ordinal=id-regionRanges[low];
 return {namespace:"R19-HRA-procedural",id,region_id:low,region_name:r.name,
         local_ordinal:ordinal,xyz:volumePosition(r,ordinal),
         target_total:total,synthetic:true};
}
const adjacencyCache=new Map();
function nearSomaRegions(r){
 if(adjacencyCache.has(r.index))return adjacencyCache.get(r.index);
 regionSpatialOrder(r);
 const a=regionCenters.get(r.index);
 if(!a){adjacencyCache.set(r.index,[]);return [];}
 const candidates=[];
 for(const t of rows){
  if(t.index===r.index||!quotas[t.index]||!t.cells_count)continue;
  regionSpatialOrder(t);
  const b=regionCenters.get(t.index);
  if(!b)continue;
  const dist=a.reduce((sum,v,k)=>sum+(v-b[k])**2,0);
  candidates.push([dist,t.index]);
 }
 candidates.sort((u,v)=>u[0]-v[0]||u[1]-v[1]);
 const ids=candidates.slice(0,4).map(a=>a[1]);
 adjacencyCache.set(r.index,ids);
 return ids;
}
function graphOutgoing(id){
 const cellInfo=neuronForId(id),rid=cellInfo.region_id,from=rows[rid];
 const count=quotas[rid],ord=cellInfo.local_ordinal;
 const stride=Math.max(1,Math.floor(count/Math.max(1,from.cells_count)));
 const out=[],seen=new Set([id]);
 for(const offset of [1,stride,stride*2,stride*7,stride*17]){
  const n=regionRanges[rid]+((ord+offset)%count);
  if(!seen.has(n)){seen.add(n);out.push(n);}
 }
 // Sparse projection proxies: nearest HRA tissue *centroids*, not known synapses.
 // No fabricated connections are assigned to white matter or ventricular soma.
 if(hash(id^0x5f3759df)%8===0){
  const nearby=nearSomaRegions(from);
  for(let k=0;k<Math.min(2,nearby.length);k++){
   const targetId=nearby[(k+(hash(id+17)%nearby.length))%nearby.length];
   const destCount=quotas[targetId];
   const fraction=ord/count;
   const destOrdinal=Math.min(destCount-1,Math.floor(fraction*destCount));
   const n=regionRanges[targetId]+destOrdinal;
   if(!seen.has(n)){seen.add(n);out.push(n);}
  }
 }
 return out;
}
function traverse(root,depth,maxNodes=192){
 const queue=[[root,0]],visited=new Set([root]),directed=[],seenEdges=new Set();
 let head=0,truncated=false;
 while(head<queue.length){
  const [id,d]=queue[head++];
  if(d>=depth)continue;
  for(const nxt of graphOutgoing(id)){
   if(!visited.has(nxt)&&visited.size>=maxNodes){truncated=true;continue;}
   const signature=id+":"+nxt;
   if(!seenEdges.has(signature)){seenEdges.add(signature);directed.push([id,nxt]);}
   if(!visited.has(nxt)){visited.add(nxt);queue.push([nxt,d+1]);}
  }
 }
 return {ids:[...visited],edges:directed,truncated,depth};
}
function findSyntheticPath(source,target,maxDepth=4,maxVisited=1800){
 if(source===target)return {ids:[source],visited:1,truncated:false,found:true};
 const queue=[[source,0]],seen=new Set([source]),from=new Map();
 let head=0,found=false,truncated=false;
 while(head<queue.length&&!found){
  const [id,d]=queue[head++];
  if(d>=maxDepth)continue;
  for(const neighbor of graphOutgoing(id)){
   if(seen.has(neighbor))continue;
   if(seen.size>=maxVisited){truncated=true;break;}
   seen.add(neighbor);from.set(neighbor,id);
   if(neighbor===target){found=true;break;}
   queue.push([neighbor,d+1]);
  }
  if(truncated)break;
 }
 if(!found)return {ids:[],visited:seen.size,found:false,truncated};
 let p=target,path=[target];
 while(p!==source){p=from.get(p);if(p===undefined)throw Error("Graph predecessor lost");path.push(p);}
 path.reverse();
 return {ids:path,visited:seen.size,found:true,truncated:false};
}
let focusedGraph=null;
function clearGraph(){
 focusedGraph=null;center=[0,0,0];distance=3.5;graphZoom=1;
 $("neuronResultR19").textContent="Выделение снято. Отображается наружная поверхность; внутренние нейроны снова скрыты.";
 later();
}
function graphGeometry(g){
 const vertices=[],segments=[],pointById=new Map();
 for(const id of g.ids){
  const v=neuronForId(id);
  if(!v.xyz)continue;
  pointById.set(id,v.xyz);
  addPoint(vertices,v.xyz,id===g.root?7.5:5.8,
      id===g.root?[1,1,.95]:v.region_id===g.root_region?[1,.64,.25]:[.30,.88,.98]);
 }
 for(const [a,b] of g.edges){
  const p=pointById.get(a),q=pointById.get(b);
  if(p&&q)addLine(segments,p,q,[1,.65,.22]);
 }
 return {points:vertices,lines:segments};
}
function graphFocusCamera(geometry){
 if(!geometry.points.length)return;
 const xyz=geometry.points;
 const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
 for(let i=0;i<xyz.length;i+=7)for(let k=0;k<3;k++){
  lo[k]=Math.min(lo[k],xyz[i+k]);hi[k]=Math.max(hi[k],xyz[i+k]);
 }
 center=lo.map((v,k)=>(v+hi[k])*.5);
 const span=Math.max(...lo.map((v,k)=>hi[k]-v));
 distance=3.0;graphZoom=Math.max(1,Math.min(1200,1.3/Math.max(span,.0007)));
}
function selectNeuronGraph(){
 try{
  const input=$("sourceNeuronR19").value.trim();
  if(!/^[0-9]+$/.test(input))throw Error("Neuron ID должен быть целым");
  const source=Number(input);
  const root=neuronForId(source);
  const targetText=$("targetNeuronR19").value.trim();
  let graph;
  if(targetText){
    if(!/^[0-9]+$/.test(targetText))throw Error("Целевой ID должен быть целым");
    const target=Number(targetText);
    neuronForId(target);
    const found=findSyntheticPath(source,target,Number($("graphDepthR19").value),1800);
    if(!found.found){
      $("neuronResultR19").textContent="Путь в ограниченном синтетическом обходе не найден. Посещено "+found.visited+" ID"+(found.truncated?" (лимит 1800)":"")+". Отсутствие полного пути не доказано.";
      return;
    }
    const edges=found.ids.slice(1).map((id,i)=>[found.ids[i],id]);
    graph={root:source,root_region:root.region_id,ids:found.ids,edges,truncated:false,
           note:"Путь по модельному графу: "+found.ids.join(" → ")};
  }else{
    const walk=traverse(source,Number($("graphDepthR19").value),mobile?88:192);
    graph={...walk,root:source,root_region:root.region_id,
           note:"Синтетическое дерево исходящих связей: "+walk.ids.length+" ID и "+walk.edges.length+" ребёр"+(walk.truncated?" (ограничение LOD)":"")};
  }
  const g=graphGeometry(graph);
  focusedGraph=graph;
  selected=-1;tract=-1;$("region").value="-1";$("tract").value="-1";
  $("neuronResultR19").textContent=graph.note+" · старт: "+root.region_name+
   " · пространство HRA/V5, не настоящие аксоны/синапсы.";
  graphFocusCamera(g);later();
 }catch(e){$("neuronResultR19").textContent="Ошибка: "+e.message;console.error(e);}
}

function shellPosition(r,j,k){
 const index=Math.min(r.shell_count-1,Math.floor((j+.5)/k*r.shell_count));
 const p=cell(r.shell_start+index);
 // Sub-voxel deterministic LOD jitter, never persisted as anatomy.
 const seed=hash(r.index*810103+j*1459);
 // A little less than 1mm in reference space; avoid obvious duplicate
 // points if an HRA shell stencil seed is reused at high GPU density.
 const radius=Math.min(.0020,5.0e-4/meta.max_extent_m);
 return p.map((x,a)=>x+(rnd(seed+a*61843)-.5)*radius);
}
function addPoint(buf,p,size,col){buf.push(...p,size,...col);}
function addLine(buf,p,q,col){buf.push(...p,...col,...q,...col);}
function shares(b,active,weightFn){
 const map=new Map(),sum=active.reduce((a,r)=>a+weightFn(r),0);
 if(!sum||!b)return map;
 let left=b;
 const remainders=[];
 for(const r of active){const x=b*weightFn(r)/sum,q=Math.floor(x);map.set(r.index,q);left-=q;remainders.push([r.index,x-q]);}
 remainders.sort((a,b)=>b[1]-a[1]||a[0]-b[0]);
 for(let j=0;j<left;j++)map.set(remainders[j%remainders.length][0],map.get(remainders[j%remainders.length][0])+1);
 return map;
}
function makeDots(){
 const B=budget(),choice=rows[selected],back=$("background").value;
 const active=rows.filter(r=>r.shell_count>0&&(selected<0?outer(r):r.index===selected||(back!=="hide"&&outer(r))));
 const inner=choice&&quotas[selected]&&choice.cells_count&&choice.type!=="tract"&&choice.type!=="cavity"?
  Math.min(quotas[selected],Math.floor(B*.68)):0;
 const allot=shares(B-inner,active,r=>Math.pow(Math.max(1,quotas[r.index]),.87)*Math.pow(Math.max(1,r.shell_count),.13));
 // Area-aware point scaling: denser point clouds remain legible, without
 // oversized opaque markers or the nearly invisible R19 0.8px glyphs.
 const factor=Math.max(1.08,Math.min(3.7,2.90*Math.pow(60000/Math.max(1,B),.35)));
 const raw=[], samples=new Map(), inside=[];
 for(const r of active){
  const count=allot.get(r.index)||0,chosen=r.index===selected;
  if(!count)continue;
  let c=color(r,chosen);
  if(selected>=0&&!chosen&&back==="dim")c=c.map(v=>v*.13);
  for(let j=0;j<count;j++){
   const p=shellPosition(r,j,count);
   addPoint(raw,p,factor*(chosen?1.08:1)*(r.type==="cerebellum"?.68:1),c);
   if(j%Math.max(1,Math.floor(count/50))===0){
    if(!samples.has(r.index))samples.set(r.index,[]);
    samples.get(r.index).push(p);
   }
  }
 }
 if(inner){
  for(let j=0;j<inner;j++){
   const ordinal=Math.min(quotas[selected]-1,Math.floor((j+.5)*quotas[selected]/inner));
   const p=volumePosition(choice,ordinal);
   if(!p)continue;inside.push(p);
   addPoint(raw,p,factor*(choice.type==="cerebellum"?.53:.75),[1,.70,.42]);
  }
 }
 return {buffer:raw,inside,samples};
}
function syntheticEdges(data){
 const lines=[],roots=[];
 const active=selected>=0 ? [rows[selected]] :
   rows.filter(r=>quotas[r.index]>0&&r.cells_count&&r.shell_count).slice(0,120);
 for(const r of active){
  if(!quotas[r.index])continue;
  const count=selected>=0?Math.min(85,quotas[r.index]):Math.min(2,quotas[r.index]);
  for(let j=0;j<count;j++){
   const ordinal=Math.min(quotas[r.index]-1,Math.floor((j+.5)/count*quotas[r.index]));
   roots.push(regionRanges[r.index]+ordinal);
  }
 }
 const edgeSet=new Set();
 for(const id of roots){
  const source=neuronForId(id);
  for(const destId of graphOutgoing(id)){
   if(lines.length>=12*1800)break;
   const key=id+":"+destId;
   if(edgeSet.has(key))continue;edgeSet.add(key);
   const dest=neuronForId(destId);
   if(source.xyz&&dest.xyz)addLine(lines,source.xyz,dest.xyz,[.78,.31,.46]);
  }
  if(lines.length>=12*1800)break;
 }
 return lines;
}
function tractEdges(r){
 const out=[];
 if(!r||r.cells_count<2)return out;
 const ps=Array.from({length:r.cells_count},(_,i)=>cell(r.cells_start+i));
 const variances=[0,1,2].map(k=>{
  const mean=ps.reduce((a,p)=>a+p[k],0)/ps.length;
  return ps.reduce((a,p)=>a+(p[k]-mean)**2,0);
 });
 const ax=variances.indexOf(Math.max(...variances));
 ps.sort((a,b)=>a[ax]-b[ax]);
 const num=Math.max(3,Math.min(48,Math.floor(ps.length/2)));
 const centers=[];
 for(let j=0;j<num;j++){
  const start=Math.floor(j*ps.length/num),end=Math.max(start+1,Math.floor((j+1)*ps.length/num));
  const chunk=ps.slice(start,end);
  centers.push([0,1,2].map(k=>chunk.reduce((s,p)=>s+p[k],0)/chunk.length));
 }
 const lanes=mobile?4:12,ax2=(ax+1)%3,ax3=(ax+2)%3,offset=Math.min(.008,1.8e-3/meta.max_extent_m)*.28;
 for(let lane=0;lane<lanes;lane++){
  const angle=lane*2.399963,rad=offset*Math.sqrt((lane+.5)/lanes);
  for(let j=1;j<centers.length;j++){
   const a=centers[j-1].slice(),b=centers[j].slice();
   for(const p of [a,b]){p[ax2]+=rad*Math.cos(angle);p[ax3]+=rad*Math.sin(angle);}
   addLine(out,a,b,[.26,.82,.99]);
  }
 }
 return out;
}
function readout(){
 $("virtualCount").textContent=F.format(total);$("gpuCount").textContent=F.format(points);
 const group={cerebellum:0,cortex:0,other:0};
 for(const r of rows)if(group[r.type]!==undefined)group[r.type]+=quotas[r.index];
 $("split").innerHTML="Мозжечок <span>"+F.format(group.cerebellum)+"</span><br>Кора <span>"+F.format(group.cortex)+"</span><br>Остальные <span>"+F.format(group.other)+"</span>";
 const r=rows[selected];
 $("areaInfo").textContent=r?
  r.label+" · "+r.name+" · "+F.format(quotas[selected])+" модельных нейронов · "+F.format(r.cells_count)+" опорных ячеек. "+
  (r.type==="tract"?"Проводящие волокна, не тела нейронов":r.type==="cavity"?"Полость": "Внутренний объём раскрыт"):
  "Внутренние точки скрыты. Выберите область, чтобы раскрыть нейроны в ней.";
 $("lodValue").textContent=F.format(budget())+" GPU-точек · режим: "+
   ($("lodMode").value==="auto"?"автоматический":"ручной")+
   " · ограничение "+F.format(mobile?120000:1100000);
}
function rebuild(){
 if(!meta||!gl||!P)return;
 try{
  quotas=allocation(total);rebuildRanges();
  const dots=focusedGraph&&$("background").value==="hide"?
    {buffer:[],inside:[],samples:new Map()}:makeDots();
  if(focusedGraph){
    if($("background").value==="dim"){
      for(let i=4;i<dots.buffer.length;i+=7){
        dots.buffer[i]*=.10;dots.buffer[i+1]*=.10;dots.buffer[i+2]*=.10;
      }
    }
    const graph=graphGeometry(focusedGraph);
    dots.buffer.push(...graph.points);
    dots.neuronEdges=graph.lines;
  }
  free(pg);pg=make(dots.buffer,7,[[0,3,0],[1,1,3],[2,3,4]]);
  points=dots.buffer.length/7;
  const lines=focusedGraph?dots.neuronEdges:
    tract>=0?tractEdges(rows[tract]):links?syntheticEdges(dots):[];
  free(lg);lg=lines.length?make(lines,6,[[0,3,0],[1,3,3]]):null;
  segments=lines.length/12;
  readout();dirty=true;
  S.textContent=F.format(total)+" виртуальных нейронов · "+F.format(points)+" GPU-точек · "+F.format(segments)+" модельных направленных сегментов"+(focusedGraph?" · Neural Explorer":"");
 }catch(e){S.textContent="Ошибка генератора: "+e.message;console.error(e);}
}
function later(){if(loading)return;loading=true;requestAnimationFrame(()=>{loading=false;rebuild();});}
function setTotal(n){
 n=Number(n);
 if(!Number.isSafeInteger(n)||n<1000||n>1e12){S.textContent="Задайте целое число от 1000 до 1 трлн";return;}
 total=n;$("target").value=String(n);quotas=allocation(n);rebuildRanges();
 if(focusedGraph){focusedGraph=null;graphZoom=1;$("neuronResultR19").textContent="Общий размер изменён, диапазоны ID перенумерованы; выделение снято.";}
 spatialOrders.clear();regionCenters.clear();adjacencyCache.clear();
 for(const [id,preset] of [["preset500",5e8],["preset86",8.6e9],["preset861",86.1e9]])
  $(id).setAttribute("aria-pressed",String(n===preset));
 later();
}
function dropdown(){
 const sel=$("region"),tr=$("tract");
 sel.replaceChildren(new Option("Весь мозг · только наружные области","-1"));
 tr.replaceChildren(new Option("Не показывать тракт","-1"));
 for(const r of rows){
  const label=r.label+" · "+r.name.replace("Allen_","");
  sel.add(new Option(label,String(r.index)));
  if(r.type==="tract"&&r.cells_count>1)tr.add(new Option(label,String(r.index)));
 }
}
function search(){
 const sel=$("region"),q=$("regionSearch").value.trim().toLowerCase(),old=selected;
 sel.replaceChildren(new Option("Весь мозг · только наружные области","-1"));
 for(const r of rows)if((r.label+" "+r.name+" "+r.type).toLowerCase().includes(q))sel.add(new Option(r.label+" · "+r.name.replace("Allen_"),String(r.index)));
 if(old>=0&&[...sel.options].some(o=>o.value===String(old)))sel.value=String(old);
 else {sel.value="-1";selected=-1;}
 later();
}
function inputs(){
 for(const [id,n] of [["preset500",500000000],["preset86",8600000000],["preset861",86100000000]])$(id).onclick=()=>setTotal(n);
 $("target").onchange=()=>setTotal($("target").value);
 $("lod").oninput=later;$("lodMode").onchange=later;
 $("background").onchange=later;$("regionSearch").oninput=search;
 $("region").onchange=()=>{focusedGraph=null;graphZoom=1;selected=Number($("region").value);tract=-1;$("tract").value="-1";later();};
 $("tract").onchange=()=>{focusedGraph=null;graphZoom=1;tract=Number($("tract").value);if(tract>=0){selected=-1;$("region").value="-1";}later();};
 $("linkOff").onclick=()=>{links=false;$("linkOff").setAttribute("aria-pressed","true");$("linkOn").setAttribute("aria-pressed","false");later();};
 $("linkOn").onclick=()=>{focusedGraph=null;links=true;$("linkOn").setAttribute("aria-pressed","true");$("linkOff").setAttribute("aria-pressed","false");later();};
 $("neuronRunR19").onclick=selectNeuronGraph;
 $("neuronClearR19").onclick=clearGraph;
 $("reset").onclick=()=>{yaw=.6;pitch=.18;distance=3.5;center=[0,0,0];graphZoom=1;dirty=true;};
 $("export").onclick=()=>{
  const lines=["region_id,source_name,tissue_type,estimated_virtual_neurons,template_volume_cells,template_surface_points,region_count_measured"];
  for(const r of rows)lines.push([r.index,r.name,r.type,quotas[r.index],r.cells_count,r.shell_count,false].join(","));
  const u=URL.createObjectURL(new Blob(["\ufeff"+lines.join("\n")+"\n"],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a");a.href=u;a.download="R18_"+total+"_model_quota.csv";a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);
 };
 if(mobile){$("panel").classList.add("collapsed");$("togglePanel").onclick=()=>{
  const hidden=$("panel").classList.toggle("collapsed");$("togglePanel").textContent=hidden?"Управление мозгом":"Закрыть панель";};}
 window.addEventListener("resize",()=>dirty=true);
 C.addEventListener("pointerdown",e=>{C.setPointerCapture(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);});
 C.addEventListener("pointermove",e=>{
  if(!touches.has(e.pointerId))return;const a=touches.get(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);
  if(touches.size>=2){const p=[...touches.values()],d=Math.hypot(p[0][0]-p[1][0],p[0][1]-p[1][1]);
   if(pinch>0)distance=Math.max(1.2,Math.min(10,distance*pinch/d));pinch=d;
  }else{yaw+=(e.clientX-a[0])*.008;pitch=Math.max(-1.45,Math.min(1.45,pitch+(e.clientY-a[1])*.008));}dirty=true;
 });
 const release=e=>{touches.delete(e.pointerId);pinch=0;};
 C.addEventListener("pointerup",release);C.addEventListener("pointercancel",release);
 C.addEventListener("wheel",e=>{e.preventDefault();distance=Math.max(1.2,Math.min(10,distance*Math.exp(e.deltaY*.001)));dirty=true;},{passive:false});
}
async function start(){
 inputs();
 const [a,b]=await Promise.all([fetch("../assets/manifest_r18.json"),fetch("../assets/hra_procedural_stencil_r18.bin.gz")]);
 if(!a.ok||!b.ok)throw Error("HRA трафарет недоступен");
 meta=await a.json();
 const raw=await new Response(b.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
 view=new DataView(raw);
 if(String.fromCharCode(...new Uint8Array(raw,0,4))!=="HST8")throw Error("HST8 magic mismatch");
 if(view.getUint32(4,true)!==1||view.getUint32(8,true)!==283||
    view.getUint32(12,true)*8+16!==raw.byteLength)throw Error("Трафарет повреждён");
 if(meta.regions.length!==283||meta.reference_HRA_sha256!=="c97d7d0b9ff0baebbdec5566fa7b08d789195ef965e0bd04cf743a8d683882db")
  throw Error("Неверная версия HRA");
 rows=meta.regions;
 let cursor=0;for(const r of rows){
  if(r.cells_start!==cursor)throw Error("Ошибка области "+r.index);
  cursor+=r.cells_count;
  if(r.shell_start!==cursor)throw Error("Ошибка внешней поверхности "+r.index);
  cursor+=r.shell_count;
 }
 if(cursor!==view.getUint32(12,true))throw Error("Ошибка полноты трафарета");
 dropdown();quotas=allocation(total);rebuild();
 window.ProceduralAtlasR18={
  setTotal,
  setRegion:id=>{selected=Number(id);tract=-1;$("region").value=String(id);later();},
  setTract:id=>{tract=Number(id);selected=-1;$("tract").value=String(id);later();},
  getQuota:id=>quotas[Number(id)],
  getLOD:()=>({rendered:points,target:budget(),mode:$("lodMode").value,
    requested:Number($("lod").value),platformCap:mobile?120000:1100000}),
  resolveNeuronId:neuronForId,
  outgoingNeuronIds:graphOutgoing,
  walkNeuronIds:traverse,
  findPath:findSyntheticPath,
  focusNeuron:id=>{
   $("sourceNeuronR19").value=String(id);
   $("targetNeuronR19").value="";
   selectNeuronGraph();
  },
  clearNeuronFocus:clearGraph,
  getGraph:()=>focusedGraph?{zoom:graphZoom,root:focusedGraph.root,ids:focusedGraph.ids.length,
     edges:focusedGraph.edges.length,truncated:!!focusedGraph.truncated}:null,
  getStats:()=>({total,shown:points,segments,selected,tract,regions:rows.length,templateRecords:cursor,
    allocated:quotas.reduce((s,v)=>s+v,0)}),
  metadata:()=>meta,
  graphVersion:"R19 procedural directed synthetic ID connections, stable within fixed population",
  anatomySource:"HRA/Allen CC BY 4.0",
  confidence:"regional quota estimates, not measured 283-region counts",
  realSynapses:false
 };
}
start().catch(e=>{S.textContent="Ошибка R18: "+e.message;console.error(e);});
})();