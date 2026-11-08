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
let yaw=.6,pitch=.18,distance=3.5,center=[0,0,0],touches=new Map(),pinch=0;
let P=null,L=null,pg=null,lg=null,loading=false;
const pointVS=[
"#version 300 es","precision highp float;",
"layout(location=0) in vec3 aPos;layout(location=1) in float aSize;layout(location=2) in vec3 aColor;",
"uniform float uYaw,uPitch,uDistance,uAspect,uHeight;uniform vec3 uCenter;out vec3 vColor;",
"void main(){vec3 p=aPos-uCenter;float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);",
"p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);p=vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);",
"float d=max(.12,uDistance-p.z);gl_Position=vec4(2.05*p.x/uAspect,2.05*p.y,d*1.003-.35,d);",
"gl_PointSize=clamp(aSize*uHeight/(130.*d),.75,8.);vColor=aColor*(.84+.22*clamp(p.z+.55,0.,1.));}"
].join("\n");
const pointFS=["#version 300 es","precision highp float;in vec3 vColor;out vec4 f;",
"void main(){float r=length(gl_PointCoord-vec2(.5))*2.;if(r>1.)discard;f=vec4(vColor*(1.15-.36*smoothstep(.1,1.,r)),1.);}"].join("\n");
const lineVS=["#version 300 es","precision highp float;layout(location=0) in vec3 aPos;layout(location=1) in vec3 aColor;",
"uniform float uYaw,uPitch,uDistance,uAspect;uniform vec3 uCenter;out vec3 vColor;",
"void main(){vec3 p=aPos-uCenter;float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);",
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
 const common=p=>{gl.useProgram(p);uf(p,"uYaw",yaw);uf(p,"uPitch",pitch);uf(p,"uDistance",distance);uf(p,"uAspect",w/h);uf(p,"uCenter",center);};
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
function budget(){return Math.min(total,Number($("lod").value),mobile?90000:220000,Math.max(1600,Math.round(24000*Math.pow(total/5e8,.28))));}
function color(r,chosen=false){
 if(chosen)return [1,.83,.64];
 const p=palette[r.type]||palette.other,tone=.90+.15*rnd(r.index*59363+17);
 return p.map(x=>Math.min(1,x*tone));
}
function outer(r){return r.type==="cortex"||r.type==="cerebellum"||r.group==="brainstem";}
function volumePosition(r,ordinal){
 if(r.cells_count===0)return null;
 const low=ordinal>>>0,hi=Math.floor(ordinal/4294967296)>>>0;
 const h=hash(low^hi^Math.imul(r.index+23,0x9e3779b1));
 const p=cell(r.cells_start+h%r.cells_count);
 const j=Math.min(.006,1.8e-3/meta.max_extent_m);
 return p.map((v,k)=>v+(rnd(h+Math.imul(k+1,0x51ed270b))-.5)*j);
}
function shellPosition(r,j,k){
 const index=Math.min(r.shell_count-1,Math.floor((j+.5)/k*r.shell_count));
 const p=cell(r.shell_start+index);
 // Sub-voxel deterministic LOD jitter, never persisted as anatomy.
 const seed=hash(r.index*810103+j*1459);
 const radius=Math.min(.0018,4.0e-4/meta.max_extent_m);
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
 const factor=Math.max(.8,Math.min(4,2.8*Math.sqrt(24000/B)));
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
 const lines=[];
 if(data.inside.length>1){
  const n=data.inside.length,m=Math.min(1500,Math.floor(n/6));
  for(let j=0;j<m;j++){
   const a=hash(7919+j*43)%n,b=hash(1741+j*29)%n;
   if(a!==b)addLine(lines,data.inside[a],data.inside[b],[.8,.23,.39]);
  }
 }else{
  const ids=[...data.samples.keys()],mid=p=>p.reduce((s,v)=>s.map((x,k)=>x+v[k]/p.length),[0,0,0]);
  const mids=new Map(ids.map(id=>[id,mid(data.samples.get(id))]));
  for(const r of ids.slice(0,115)){
   const p=data.samples.get(r);let best=-1,bd=Infinity;
   for(const o of ids){
    if(o===r)continue;
    const a=mids.get(r),b=mids.get(o);
    const d=a.reduce((s,x,k)=>s+(x-b[k])**2,0);
    if(d<bd){bd=d;best=o;}
   }
   if(best<0)continue;
   const q=data.samples.get(best);
   for(let j=0;j<12;j++)addLine(lines,p[hash(r*17+j)%p.length],q[hash(r*71+j)%q.length],[.59,.20,.34]);
  }
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
 $("lodValue").textContent=F.format(budget())+" активных GPU-точек (максимум "+F.format(Number($("lod").value))+")";
}
function rebuild(){
 if(!meta||!gl||!P)return;
 try{
  quotas=allocation(total);
  const dots=makeDots();
  free(pg);pg=make(dots.buffer,7,[[0,3,0],[1,1,3],[2,3,4]]);
  points=dots.buffer.length/7;
  const lines=tract>=0?tractEdges(rows[tract]):links?syntheticEdges(dots):[];
  free(lg);lg=lines.length?make(lines,6,[[0,3,0],[1,3,3]]):null;
  segments=lines.length/12;
  readout();dirty=true;
  S.textContent=F.format(total)+" виртуальных нейронов · "+F.format(points)+" точек GPU · "+F.format(segments)+" синтетических сегментов";
 }catch(e){S.textContent="Ошибка генератора: "+e.message;console.error(e);}
}
function later(){if(loading)return;loading=true;requestAnimationFrame(()=>{loading=false;rebuild();});}
function setTotal(n){
 n=Number(n);
 if(!Number.isSafeInteger(n)||n<1000||n>1e12){S.textContent="Задайте целое число от 1000 до 1 трлн";return;}
 total=n;$("target").value=String(n);
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
 $("lod").oninput=later;$("background").onchange=later;$("regionSearch").oninput=search;
 $("region").onchange=()=>{selected=Number($("region").value);tract=-1;$("tract").value="-1";later();};
 $("tract").onchange=()=>{tract=Number($("tract").value);if(tract>=0){selected=-1;$("region").value="-1";}later();};
 $("linkOff").onclick=()=>{links=false;$("linkOff").setAttribute("aria-pressed","true");$("linkOn").setAttribute("aria-pressed","false");later();};
 $("linkOn").onclick=()=>{links=true;$("linkOn").setAttribute("aria-pressed","true");$("linkOff").setAttribute("aria-pressed","false");later();};
 $("reset").onclick=()=>{yaw=.6;pitch=.18;distance=3.5;center=[0,0,0];dirty=true;};
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
  resolveNeuronId:id=>{
    const n=Number(id);
    if(!Number.isSafeInteger(n)||n<0||n>=total)throw Error("Virtual ID out of range");
    let start=0;
    for(const r of rows){
      const end=start+quotas[r.index];
      if(n<end){
        return {namespace:"R18-HRA-procedural-v1",id:n,
          region_id:r.index,region_name:r.name,local_ordinal:n-start,
          xyz:volumePosition(r,n-start),measured_biological_neuron:false};
      }
      start=end;
    }
    throw Error("Virtual ID not resolved");
  },
  getStats:()=>({total,shown:points,segments,selected,tract,regions:rows.length,templateRecords:cursor,
    allocated:quotas.reduce((s,v)=>s+v,0)}),
  metadata:()=>meta,
  anatomySource:"HRA/Allen CC BY 4.0",
  confidence:"regional quota estimates, not measured 283-region counts",
  realSynapses:false
 };
}
start().catch(e=>{S.textContent="Ошибка R18: "+e.message;console.error(e);});
})();