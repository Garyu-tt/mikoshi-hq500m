"use strict";
// R15: geometric boundary stability, NOT atlas verification.
const canvas=document.getElementById("brain"),status=document.getElementById("status"),progress=document.getElementById("progress");
const ctl=document.getElementById("control");
const regionNames=["Лобная","Теменная","Височная","Затылочная","Мозжечковая","Стволовая","Глубинные структуры","Островковая"];
const regionColors=["#ef344b","#d161a7","#ee9351","#9062df","#4f80ec","#e8bc68","#ba73d0","#4bafaf"];
const regionOptions=regionNames.map((name,i)=>'<option value="'+i+'">'+name+'</option>').join("");
const legendItems=regionNames.map((name,i)=>'<span style="display:inline-flex;gap:4px;align-items:center"><i style="background:'+regionColors[i]+';width:7px;height:7px;border-radius:50%"></i>'+name+'</span>').join("");
ctl.innerHTML=
'<div class="mini">Виртуальные адреса</div><div class="stat">500 000 000</div>'+
'<div class="mini">Исходные точки · неизменная геометрия</div><div class="stat" id="rendered">—</div>'+
'<div class="mini">Вычисленные связи Q0.8</div><div class="stat" id="edges">—</div>'+
'<div class="mini">Качество</div><select id="quality"><option value="auto">Полная · автоматически</option><option value="full">Полная · 1,19 млн</option><option value="lite">Облегчённая · 298 тыс.</option></select>'+
'<label class="mini"><input id="showEdges" type="checkbox" checked> Волокна</label>'+
'<label class="mini" style="display:block;margin:8px 0 0"><input id="showLong" type="checkbox" checked> Длинные волокна</label>'+
'<div class="mini" style="margin-top:10px">Сглаживание сетки</div><input id="jitter" type="range" min="0" max="100" value="39" style="width:100%">'+
'<div class="mini" style="margin-top:9px">Яркость волокон</div><input id="strength" type="range" min="10" max="100" value="72" style="width:100%">'+
'<div class="mini" style="margin-top:9px">Режим анатомической схемы</div><select id="regionView">'+
'<option value="0">Deep Ruby · исходные цвета</option><option value="1" selected>Все 8 зон · плавные границы</option>'+
'<option value="2">Фокус на области</option><option value="3">Плотность мозжечковой зоны</option></select>'+
'<div class="mini" style="margin-top:8px">Выделенная зона (предположительная)</div>'+
'<select id="focusZone">'+regionOptions+'</select>'+
'<div id="regionLegend" style="display:flex;flex-wrap:wrap;gap:4px 10px;font-size:9px;line-height:1.3;color:#bfb3c0;margin:7px 0">'+legendItems+'</div>'+
'<div class="mini" style="margin-top:7px">Размер маркеров · динамический</div><input id="pointScale" type="range" min="40" max="190" value="120" style="width:100%">'+
'<div class="mini" style="margin-top:7px">LOD плотности · условные точки</div><select id="replicas"><option value="1">1× · только исходные точки</option><option value="2">2× · мягкая плотность</option><option value="4" selected>4× · мягкая плотность</option><option value="8">8× · мягкая плотность</option></select>'+
'<div id="cerebCount" style="font-size:10px;color:#e5b8c3;margin:5px 0">Подготовка зон…</div>'+
'<div style="font-size:10px;line-height:1.35;color:#aea3ab">8 зон — пространственные гипотезы, а не результаты МРТ. Нет подтверждённых атласных координат и отдельного мозжечка. Дополнительные точки лишь для визуализации, не настоящие нейроны.</div>'+
'<div class="gap"><button id="orbit" class="primary">Автовращение</button><button id="reset">Сбросить</button></div>'+
'<button id="snap" style="width:100%">Сохранить кадр PNG</button><hr>'+
'<div class="mini">Топология · 16 млрд потенциальных связей</div>'+
'<div style="font-size:10px;line-height:1.5;color:#ad949a;margin-top:8px">Связи — ограниченная вычисленная выборка пар виртуальных ID, не биологический коннектом человека.</div>';
document.querySelector("#kicker").textContent="DEEP RUBY / SMOOTH REGIONS · R16";
document.querySelector("#desc").textContent="1 192 673 неизменных точек, восемь плавно смешиваемых условных зон и непрерывная плотность. Без подтверждённого анатомического атласа.";
document.querySelector("#bottom").textContent="ORIGINAL POINT CLOUD · EXACT Q0.8 EDGE ENDPOINTS · DEPTH OCCLUSION";
const quality=document.getElementById("quality"),showEdges=document.getElementById("showEdges"),
      showLong=document.getElementById("showLong"),strength=document.getElementById("strength"),jitterCtl=document.getElementById("jitter");
const regionCtl=document.getElementById("regionView"),sizeCtl=document.getElementById("pointScale"),replicaCtl=document.getElementById("replicas"),focusCtl=document.getElementById("focusZone");
const gl=canvas.getContext("webgl2",{depth:true,antialias:true,alpha:false,preserveDrawingBuffer:true,powerPreference:"high-performance"});
const mobile=matchMedia("(max-width:760px), (pointer:coarse)").matches;
if(!gl)status.textContent="Нужен WebGL2: открой страницу в современном браузере.";
function shader(type,source){let s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
function makeProgram(v,f){let p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,v));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));return p;}
async function ungzip(file){let r=await fetch("./assets/"+file,{cache:"force-cache"});if(!r.ok)throw Error("HTTP "+r.status+" "+file);if(!("DecompressionStream" in window))throw Error("Нужен браузер с поддержкой DecompressionStream");
let bytes=await r.arrayBuffer();return await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();}
function pointGeometry(bytes,regionBytes,softBytes){
const buffer=gl.createBuffer(),vao=gl.createVertexArray();
gl.bindVertexArray(vao);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,bytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.UNSIGNED_SHORT,true,8,0);
gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,2,gl.UNSIGNED_BYTE,true,8,6);
const metaBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,metaBuffer);gl.bufferData(gl.ARRAY_BUFFER,regionBytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(2);gl.vertexAttribPointer(2,2,gl.UNSIGNED_BYTE,false,2,0);
const softBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,softBuffer);gl.bufferData(gl.ARRAY_BUFFER,softBytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(3);gl.vertexAttribPointer(3,4,gl.UNSIGNED_BYTE,true,8,0);
gl.enableVertexAttribArray(4);gl.vertexAttribPointer(4,4,gl.UNSIGNED_BYTE,true,8,4);
gl.bindVertexArray(null);return {buffer,metaBuffer,softBuffer,vao};
}
function lineGeometry(bytes){const buffer=gl.createBuffer(),vao=gl.createVertexArray();gl.bindVertexArray(vao);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,bytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.UNSIGNED_SHORT,true,6,0);
gl.bindVertexArray(null);return {buffer,vao};}
let yaw=.62,pitch=.12,distance=mobile?4.7:3.00,spin=false,dirty=true,lastTime=0,generation=0;
let numPoints=0,cerebCount=0,localEdges=0,globalEdges=0,pointData=null,cerebData=null,lineData=null,pp,lp,loaded=false;
let originalPointBytes=null,originalLineBytes=null,explorerData=null,explorerEdges=0;
let explorerBackground="all",camCenter=[0,0,0];
function uniform(name,value,p){const l=gl.getUniformLocation(p,name);if(l!==null)gl.uniform1f(l,value);}
function scene(p,t){gl.useProgram(p);
uniform("uYaw",yaw,p);uniform("uPitch",pitch,p);uniform("uCamera",distance,p);
uniform("uAspect",canvas.width/canvas.height,p);uniform("uHeight",canvas.height,p);
uniform("uTime",t/1000,p);
uniform("uCenterX",camCenter[0],p);uniform("uCenterY",camCenter[1],p);uniform("uCenterZ",camCenter[2],p);}
async function loadPoints(mode){
const selected=mode==="auto"?"full":mode,token=++generation;
status.textContent="Загрузка исходной геометрии "+selected+"…";progress.style.width="18%";
const name=selected==="lite"?"hq500m_source_points_lite_r13.bin.gz":"hq500m_source_points_r13.bin.gz";
const data=await ungzip(name);if(token!==generation)return;
const view=new DataView(data);if(view.getUint32(0,true)!==0x33505148)throw Error("Повреждён заголовок геометрии");
const n=view.getUint32(4,true);if(data.byteLength!==8+8*n)throw Error("Неполный массив точек");
const ann=await ungzip(selected==="lite"?"hq500m_region_density_lite_r14.bin.gz":"hq500m_region_density_r14.bin.gz");
if(token!==generation)return;
const meta=new DataView(ann);
if(meta.getUint32(0,true)!==0x34525148||meta.getUint32(4,true)!==n||ann.byteLength!==8+n*2)throw Error("Ошибка слоя анатомических областей R14");
const soft=await ungzip(selected==="lite"?"hq500m_soft_regions_lite_r16.bin.gz":"hq500m_soft_regions_r16.bin.gz");
if(token!==generation)return;
const q=new DataView(soft);
if(q.getUint32(0,true)!==0x36575148||q.getUint32(4,true)!==n||soft.byteLength!==8+8*n)throw Error("Ошибка слоя восьми мягких регионов R16");
const source=new Uint8Array(data,8), regions=new Uint8Array(ann,8), weights=new Uint8Array(soft,8);
originalPointBytes=source;
let count=0;for(let i=0;i<n;i++)if(weights[i*8+4]>=20)count++; // only non-negligible cerebellum candidates
const cp=new Uint8Array(count*8), cm=new Uint8Array(count*2), cw=new Uint8Array(count*8);
for(let i=0,j=0;i<n;i++)if(weights[i*8+4]>=20){
  cp.set(source.subarray(i*8,i*8+8),j*8);
  cm.set(regions.subarray(i*2,i*2+2),j*2);
  cw.set(weights.subarray(i*8,i*8+8),j*8);j++;
}
for(const old of [pointData,cerebData])if(old){
 gl.deleteBuffer(old.buffer);gl.deleteBuffer(old.metaBuffer);
 gl.deleteBuffer(old.softBuffer);gl.deleteVertexArray(old.vao);
}
pointData=pointGeometry(source,regions,weights);
cerebData=count?pointGeometry(cp,cm,cw):null;cerebCount=count;numPoints=n;
document.getElementById("cerebCount").textContent=count.toLocaleString("ru-RU")+" кандидатов на плотный LOD · плавная граница";
document.getElementById("rendered").textContent=n.toLocaleString("ru-RU");
status.textContent="Исходное облако: "+n.toLocaleString("ru-RU")+" точек";progress.style.width="72%";dirty=true;
}
async function loadLines(){
const data=await ungzip("hq500m_exact_fibers_r11.bin.gz"),view=new DataView(data);
if(view.getUint32(0,true)!==0x33465148)throw Error("Неверный заголовок связей");
localEdges=view.getUint32(4,true);globalEdges=view.getUint32(8,true);
if(data.byteLength!==12+12*(localEdges+globalEdges))throw Error("Неполный массив связей");
originalLineBytes=new Uint8Array(data,12);
lineData=lineGeometry(originalLineBytes);loaded=true;
document.getElementById("edges").textContent=(localEdges+globalEdges).toLocaleString("ru-RU");
progress.style.width="100%";dirty=true;
status.textContent="Готово: "+numPoints.toLocaleString("ru-RU")+" точек; "+(localEdges+globalEdges).toLocaleString("ru-RU")+" вычисленных связей";
}

const PVS="#version 300 es\nprecision highp float;\nlayout(location=0) in vec3 aPosition;\nlayout(location=1) in vec2 aSource; // sulcal depth and stable seed, from unchanged R13\nlayout(location=2) in vec2 aRegion; // local occupancy proxy from R14; region id ignored\nlayout(location=3) in vec4 aW0; // frontal, parietal, temporal, occipital [0,1]\nlayout(location=4) in vec4 aW1; // cerebellum, brainstem, deep, insula [0,1]\nuniform float uYaw,uPitch,uCamera,uAspect,uHeight,uSize,uJitter,uRegionView,uScale,uCenterX,uCenterY,uCenterZ,uContextFade;\nuniform float uReplicaPass,uRegionInstances,uFocusZone;\nout vec3 vColor;\nvec3 turn(vec3 p){\n float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);\n p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);\n return vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);\n}\nvec3 stableHash(vec3 p){\n p=fract(p*vec3(.1031,.1030,.0973));\n p+=dot(p,p.yxz+33.33);\n return fract((p.xxy+p.yxx)*p.zyx);\n}\nfloat areaWeight(float index) {\n if(index<.5)return aW0.x;\n if(index<1.5)return aW0.y;\n if(index<2.5)return aW0.z;\n if(index<3.5)return aW0.w;\n if(index<4.5)return aW1.x;\n if(index<5.5)return aW1.y;\n if(index<6.5)return aW1.z;\n return aW1.w;\n}\nvoid main(){\n vec3 original=aPosition*2.0-1.0;\n vec3 key=vec3(aSource.y*313.1+11.0,\n          aPosition.x*73.0+aPosition.y*39.0,\n          aPosition.z*101.0+aSource.y*31.0);\n float cereb=clamp(aW1.x,0.,1.);\n float inst=float(gl_InstanceID)+uReplicaPass;\n if(uReplicaPass>.5){\n   // Gradual, deterministic local coverage. Never cut off at a horizontal plane.\n   float keep=smoothstep(.035,.58,cereb);\n   float toss=stableHash(key+vec3(inst*17.31,inst*5.63,inst*3.61)).x;\n   if(toss>keep){\n     gl_Position=vec4(2.,2.,2.,1.);gl_PointSize=0.;vColor=vec3(0.);return;\n   }\n }\n vec3 jitter=(stableHash(key)-.5)*2.0*uJitter;\n vec3 p=original+jitter+normalize(original+vec3(.00001))*uJitter*.09;\n if(uReplicaPass>.5){\n   vec3 offset=(stableHash(key+vec3(inst*.131,inst*.771,inst*.334))-.5)*.0032;\n   p+=offset-normalize(original+vec3(.00001))*.0014;\n }\n vec3 r=turn(p-vec3(uCenterX,uCenterY,uCenterZ));\n float depth=max(.1,uCamera-r.z),f=2.10;\n gl_Position=vec4(r.x*f/uAspect,r.y*f,depth*1.003-.34,depth);\n float cellPressure=1.0+aRegion.y/70.0;\n // This is a continuous glyph-size *visual* proxy, NOT physical neuron diameter.\n float biologicalRatio=mix(1.0,34.7,smoothstep(.02,.80,cereb));\n float dynamicRadius=pow(cellPressure,-.17)*pow(biologicalRatio,-.18)*uScale;\n float coverage=mix(1.0,inversesqrt(max(1.,uRegionInstances)),\n                    .88*smoothstep(.02,.65,cereb));\n gl_PointSize=clamp(uSize*uHeight/(120.0*depth)*dynamicRadius*coverage,.72,5.6);\n float wave=.58+.17*sin(original.y*17.+original.x*8.)+.13*sin(original.z*23.-original.y*5.);\n float light=clamp(wave,.12,1.0);\n vec3 red=mix(vec3(.12,.002,.022),vec3(.93,.026,.077),light)\n           *(.83+.17*clamp(r.z,-1.0,1.0));\n float blue=smoothstep(.045,.63,aSource.x)*smoothstep(-.43,-.02,original.y);\n vColor=mix(red,vec3(.035,.11,.93),blue*.98);\n // Palette weights add up to 1.0. Every region blend is continuous.\n vec3 painted =\n   aW0.x*vec3(.94,.14,.24)+aW0.y*vec3(.82,.34,.66)+\n   aW0.z*vec3(.94,.56,.31)+aW0.w*vec3(.54,.31,.90)+\n   aW1.x*vec3(.31,.50,.93)+aW1.y*vec3(.91,.74,.40)+\n   aW1.z*vec3(.73,.44,.82)+aW1.w*vec3(.30,.69,.69);\n if(uRegionView>.5) {\n   vColor=mix(vColor,painted,.87);\n   if(uRegionView>1.5 && uRegionView<2.5){\n      float focus=areaWeight(uFocusZone);\n      vColor*=.15+.85*smoothstep(.03,.62,focus);\n   }\n   if(uRegionView>2.5) {\n      // Cerebellar candidate weight heat map, not verified biological density.\n      vColor=mix(vec3(.08,.02,.06),vec3(.39,.58,.98),\n                 smoothstep(.005,.53,cereb));\n   }\n }\n vColor*=uContextFade;\n}\n";
const PFS="#version 300 es\nprecision highp float;\nin vec3 vColor;out vec4 frag;\nvoid main(){float r=length(gl_PointCoord-vec2(.5))*2.0;if(r>1.0)discard;\nfloat core=1.0-smoothstep(.50,1.0,r);\nfrag=vec4(vColor*(.78+.34*core),1.0);}";
const LVS="#version 300 es\nprecision highp float;\nlayout(location=0) in vec3 aPosition;\nuniform float uYaw,uPitch,uCamera,uAspect,uTime,uLong,uCenterX,uCenterY,uCenterZ;\nout vec3 vColor;\nvec3 turn(vec3 p){\n float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);\n p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);\n return vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);\n}\nvoid main(){\n vec3 p=aPosition*2.0-1.0,r=turn(p-vec3(uCenterX,uCenterY,uCenterZ));\n float depth=max(.1,uCamera-r.z),f=2.10;\n gl_Position=vec4(r.x*f/uAspect,r.y*f,depth*1.003-.34-.0009*depth,depth);\n float pulse=sin(uTime*1.45+34.*p.x+27.*p.y+17.*p.z);\n vColor=mix(vec3(.48,.005,.04),vec3(1.,.085,.18),.48+.5*pulse);\n vColor=uLong>1.5?vec3(1.0,.71,.24):mix(vColor,vec3(.96,.1,.25),uLong*.23);\n}";
const LFS="#version 300 es\nprecision highp float;\nin vec3 vColor;uniform float uOpacity;out vec4 frag;\nvoid main(){frag=vec4(vColor,uOpacity);}";

async function start(){
pp=makeProgram(PVS,PFS);lp=makeProgram(LVS,LFS);requestAnimationFrame(render);
await loadPoints("auto");await loadLines();
}
function render(time){
const dpr=Math.min(devicePixelRatio||1,mobile?1.35:1.8);
const w=Math.max(1,Math.round(canvas.clientWidth*dpr)),h=Math.max(1,Math.round(canvas.clientHeight*dpr));
if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;dirty=true;}
if(spin){yaw+=(lastTime?Math.min(.03,(time-lastTime)*.00016):0);dirty=true;}lastTime=time;
if(dirty&&pointData){dirty=false;gl.viewport(0,0,w,h);
gl.clearColor(.019,.011,.017,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.depthMask(true);gl.disable(gl.BLEND);
scene(pp,time);uniform("uContextFade",explorerBackground==="dim"?.16:1.0,pp);uniform("uSize",mobile?1.18:1.31,pp);uniform("uJitter",Number(jitterCtl.value)*.000065,pp);
uniform("uRegionView",Number(regionCtl.value),pp);uniform("uFocusZone",Number(focusCtl.value),pp);uniform("uScale",Number(sizeCtl.value)/100,pp);
const repl=mobile?Math.min(4,Number(replicaCtl.value)):Number(replicaCtl.value);
uniform("uRegionInstances",repl,pp);
uniform("uReplicaPass",0,pp);if(explorerBackground!=="hide"){gl.bindVertexArray(pointData.vao);gl.drawArrays(gl.POINTS,0,numPoints);}
// Only candidate-zone vertices are redrawn. R14 instead submitted the entire cloud 2-4x.
if(explorerBackground==="all"&&cerebData&&repl>1){uniform("uReplicaPass",1,pp);gl.bindVertexArray(cerebData.vao);
gl.drawArraysInstanced(gl.POINTS,0,cerebCount,repl-1);}
if(loaded&&showEdges.checked&&explorerBackground==="all"){
gl.depthMask(false);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
scene(lp,time);gl.bindVertexArray(lineData.vao);const a=Number(strength.value)/100;
uniform("uLong",0,lp);uniform("uOpacity",.33*a,lp);
const shortCount=mobile?Math.min(localEdges,120000):localEdges;
gl.drawArrays(gl.LINES,0,2*shortCount);
if(showLong.checked){uniform("uLong",1,lp);uniform("uOpacity",.14*a,lp);
gl.drawArrays(gl.LINES,2*localEdges,2*(mobile?Math.min(globalEdges,52000):globalEdges));}
gl.disable(gl.BLEND);gl.depthMask(true);}
if(explorerData && explorerEdges>0){
gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);gl.depthMask(false);
scene(lp,time);uniform("uLong",2,lp);uniform("uOpacity",1,lp);
gl.bindVertexArray(explorerData.vao);
gl.drawArrays(gl.LINES,0,2*explorerEdges);
gl.depthMask(true);gl.enable(gl.DEPTH_TEST);
}
gl.bindVertexArray(null);
}
requestAnimationFrame(render);
}

function setExplorerGeometry(segments,background="hide",focus=true){
 if(explorerData){gl.deleteBuffer(explorerData.buffer);gl.deleteVertexArray(explorerData.vao);}
 explorerData=null;explorerEdges=0;
 if(segments){
   if(!(segments instanceof Uint8Array) || segments.byteLength%12!==0)
     throw Error("Expected Uint8Array of 6xu16 exact spatial pairs");
   if(segments.byteLength>0){explorerData=lineGeometry(segments);explorerEdges=segments.byteLength/12;}
 }
 explorerBackground=explorerEdges>0?(["dim","hide","all"].includes(background)?background:"hide"):"all";
 if(focus&&explorerEdges>0){
   const a=new DataView(segments.buffer,segments.byteOffset,segments.byteLength);
   const lo=[65535,65535,65535],hi=[0,0,0];
   for(let i=0;i<segments.byteLength;i+=6)for(let k=0;k<3;k++){
     const val=a.getUint16(i+k*2,true);
     lo[k]=Math.min(lo[k],val);hi[k]=Math.max(hi[k],val);
   }
   camCenter=lo.map((v,k)=>(v+hi[k])/65535-1);
   const span=Math.max(...lo.map((v,k)=>2*(hi[k]-v)/65535));
   distance=Math.max(1.7,Math.min(5,2+span*1.35));
 }
 if(!segments){camCenter=[0,0,0];distance=mobile?4.7:3.00;}
 dirty=true;
 return explorerEdges;
}
function viewerProxyPosition(id){
 if(!originalPointBytes||!numPoints)return null;
 // Stable DISPLAY-ONLY proxy: not HQ500M R11 true ID-to-Morton point map.
 const mask=(1n<<64n)-1n;
 let v=(BigInt(id)^0x9e3779b97f4a7c15n)&mask;
 v=((v^(v>>30n))*0xbf58476d1ce4e5b9n)&mask;
 v=((v^(v>>27n))*0x94d049bb133111ebn)&mask;
 v=(v^(v>>31n))&mask;
 const i=Number(v%BigInt(numPoints)), offset=i*8;
 const b=originalPointBytes;
 return [b[offset]|(b[offset+1]<<8),b[offset+2]|(b[offset+3]<<8),b[offset+4]|(b[offset+5]<<8)];
}
window.HQ500MViewer={
  ready:()=>!!originalPointBytes&&!!originalLineBytes,
  getEdges:()=>originalLineBytes,
  getEdgeCounts:()=>({local:localEdges,long:globalEdges}),
  proxyPosition:viewerProxyPosition,
  setExplorer:setExplorerGeometry,
  clearExplorer:()=>setExplorerGeometry(null),
  hasAtlasRegistration:false
};

const showError=e=>{console.error(e);status.textContent="Ошибка рендера: "+e.message;progress.style.width="0";};
if(gl)start().catch(showError);
const mobileToggle=document.getElementById("mobileToggle");
if(mobile&&mobileToggle){
  ctl.classList.add("collapsed");
  mobileToggle.onclick=()=>{
    const expanded=ctl.classList.toggle("collapsed")===false;
    mobileToggle.setAttribute("aria-expanded",String(expanded));
    mobileToggle.textContent=expanded?"Скрыть панель":"Параметры 3D";
  };
}
quality.addEventListener("change",()=>loadPoints(quality.value).catch(showError));
showEdges.onchange=showLong.onchange=regionCtl.onchange=replicaCtl.onchange=strength.oninput=jitterCtl.oninput=sizeCtl.oninput=()=>dirty=true;
focusCtl.onchange=()=>{regionCtl.value="2";dirty=true;};
document.getElementById("orbit").onclick=e=>{spin=!spin;e.target.textContent=spin?"Остановить":"Автовращение";dirty=true;};
document.getElementById("reset").onclick=()=>{yaw=.62;pitch=.12;distance=mobile?4.7:3.00;camCenter=[0,0,0];dirty=true;};
document.getElementById("snap").onclick=()=>{dirty=true;requestAnimationFrame(()=>canvas.toBlob(b=>{if(!b)return;let a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="HQ500M-R16-Smooth-Regions.png";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000);},"image/png"));};
let touches=new Map(),pinch=0;
canvas.addEventListener("pointerdown",e=>{canvas.setPointerCapture(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);});
canvas.addEventListener("pointermove",e=>{if(!touches.has(e.pointerId))return;const before=touches.get(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);
if(touches.size>=2){let list=Array.from(touches.values());let d=Math.hypot(list[0][0]-list[1][0],list[0][1]-list[1][1]);if(pinch>0)distance=Math.max(1.55,Math.min(9,distance*pinch/d));pinch=d;}
else{yaw+=(e.clientX-before[0])*.008;pitch=Math.max(-1.45,Math.min(1.45,pitch+(e.clientY-before[1])*.008));}dirty=true;});
function release(e){touches.delete(e.pointerId);pinch=0;}canvas.addEventListener("pointerup",release);canvas.addEventListener("pointercancel",release);
canvas.addEventListener("wheel",e=>{e.preventDefault();distance=Math.max(1.55,Math.min(9,distance*Math.exp(e.deltaY*.001)));dirty=true;},{passive:false});
window.addEventListener("resize",()=>dirty=true);
