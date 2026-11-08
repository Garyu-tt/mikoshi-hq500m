"use strict";
// R15: geometric boundary stability, NOT atlas verification.
const canvas=document.getElementById("brain"),status=document.getElementById("status"),progress=document.getElementById("progress");
const ctl=document.getElementById("control");
ctl.innerHTML='<div class="mini">Виртуальные нейронные адреса</div><div class="stat">500 000 000</div>'+
'<div class="mini">Исходные пространственные точки</div><div class="stat" id="rendered">—</div>'+
'<div class="mini">Вычисленные связи Q0.8</div><div class="stat" id="edges">—</div>'+
'<div class="mini">Качество рендера</div><select id="quality"><option value="auto">Автоматически</option><option value="full">Все 1,19 млн точек</option><option value="lite">298 тыс. (возможны просветы)</option></select>'+
'<label class="mini"><input id="showEdges" type="checkbox" checked> Показать связи</label>'+
'<label class="mini" style="display:block;margin:8px 0 0"><input id="showLong" type="checkbox" checked> Длинные связи</label>'+
'<div class="mini" style="margin-top:10px">Шим / смещение точек</div><input id="jitter" type="range" min="0" max="100" value="39" style="width:100%">'+
'<div class="mini" style="margin-top:9px">Яркость волокон</div><input id="strength" type="range" min="10" max="100" value="72" style="width:100%">'+
'<div class="mini" style="margin-top:9px">Анатомическая разметка (предположительная)</div><select id="regionView"><option value="0">Deep Ruby · исходный цвет</option><option value="1" selected>Предположительные области</option><option value="2">Выделить предполагаемый мозжечок</option><option value="3">Показать сомнительные границы</option></select>'+
'<div class="mini" style="margin-top:7px">Размер нейронных маркеров · адаптивный</div><input id="pointScale" type="range" min="40" max="190" value="120" style="width:100%">'+
'<div class="mini" style="margin-top:7px">LOD мозжечковой зоны · условные точки</div><select id="replicas"><option value="1">Без дополнительных</option><option value="2">2× · мозжечковая зона</option><option value="4" selected>4× · мозжечковая зона</option><option value="8">8× · мозжечковая зона</option></select>'+
'<div class="mini" style="margin-top:7px">Устойчивость границ зоны</div><input id="boundary" type="range" min="0" max="95" value="75" style="width:100%">'+
'<div id="cerebCount" style="font-size:10px;color:#e5b8c3;margin-top:5px">Загрузка зоны…</div>'+
'<div style="font-size:10px;line-height:1.35;color:#a8a1a4">Области определены эвристически: Границы показывают геометрическую стабильность R14, не вероятность правильной анатомической разметки. Отдельный мозжечок не подтверждён. Дублирующие точки - только визуальный LOD.</div>'+
'<div class="gap"><button id="orbit" class="primary">Автовращение</button><button id="reset">Сбросить</button></div>'+
'<button id="snap" style="width:100%">Сохранить кадр PNG</button><hr>'+
'<div class="mini">Топология · 16 млрд потенциальных связей</div>'+
'<div style="font-size:10px;line-height:1.55;color:#ad949a;margin-top:8px">Визуализирована вычисленная выборка точных пар нейронных ID, а не все 16 млрд связей. Геометрические координаты и формы волокон синтетические, не реконструкция человеческого коннектома.</div>';
document.querySelector("#kicker").textContent="DEEP RUBY / BOUNDARY-STABLE DENSITY · R15";
document.querySelector("#desc").textContent="Те же 1 192 673 исходные координаты + предполагаемые области, устойчивость границ и динамические размеры. Синтетические связи HQ500M Q0.8 сохранены.";
document.querySelector("#bottom").textContent="ORIGINAL POINT CLOUD · EXACT Q0.8 EDGE ENDPOINTS · DEPTH OCCLUSION";
const quality=document.getElementById("quality"),showEdges=document.getElementById("showEdges"),
      showLong=document.getElementById("showLong"),strength=document.getElementById("strength"),jitterCtl=document.getElementById("jitter");
const regionCtl=document.getElementById("regionView"),sizeCtl=document.getElementById("pointScale"),replicaCtl=document.getElementById("replicas"),boundaryCtl=document.getElementById("boundary");
const gl=canvas.getContext("webgl2",{depth:true,antialias:true,alpha:false,preserveDrawingBuffer:true,powerPreference:"high-performance"});
const mobile=matchMedia("(max-width:760px), (pointer:coarse)").matches;
if(!gl)status.textContent="Нужен WebGL2: открой страницу в современном браузере.";
function shader(type,source){let s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
function makeProgram(v,f){let p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,v));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));return p;}
async function ungzip(file){let r=await fetch("./assets/"+file,{cache:"force-cache"});if(!r.ok)throw Error("HTTP "+r.status+" "+file);if(!("DecompressionStream" in window))throw Error("Нужен браузер с поддержкой DecompressionStream");
let bytes=await r.arrayBuffer();return await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();}
function pointGeometry(bytes,regionBytes,stabilityBytes){const buffer=gl.createBuffer(),vao=gl.createVertexArray();gl.bindVertexArray(vao);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,bytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.UNSIGNED_SHORT,true,8,0);
gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,2,gl.UNSIGNED_BYTE,true,8,6);
const metaBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,metaBuffer);gl.bufferData(gl.ARRAY_BUFFER,regionBytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(2);gl.vertexAttribPointer(2,2,gl.UNSIGNED_BYTE,false,2,0);
const stabilityBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,stabilityBuffer);gl.bufferData(gl.ARRAY_BUFFER,stabilityBytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(3);gl.vertexAttribPointer(3,1,gl.UNSIGNED_BYTE,true,1,0);
gl.bindVertexArray(null);return {buffer,metaBuffer,stabilityBuffer,vao};}
function lineGeometry(bytes){const buffer=gl.createBuffer(),vao=gl.createVertexArray();gl.bindVertexArray(vao);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,bytes,gl.STATIC_DRAW);
gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.UNSIGNED_SHORT,true,6,0);
gl.bindVertexArray(null);return {buffer,vao};}
let yaw=.62,pitch=.12,distance=mobile?4.7:3.00,spin=false,dirty=true,lastTime=0,generation=0;
let numPoints=0,cerebCount=0,localEdges=0,globalEdges=0,pointData=null,cerebData=null,lineData=null,pp,lp,loaded=false;
function uniform(name,value,p){const l=gl.getUniformLocation(p,name);if(l!==null)gl.uniform1f(l,value);}
function scene(p,t){gl.useProgram(p);
uniform("uYaw",yaw,p);uniform("uPitch",pitch,p);uniform("uCamera",distance,p);
uniform("uAspect",canvas.width/canvas.height,p);uniform("uHeight",canvas.height,p);
uniform("uTime",t/1000,p);}
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
const certainty=await ungzip(selected==="lite"?"hq500m_region_stability_lite_r15.bin.gz":"hq500m_region_stability_r15.bin.gz");
if(token!==generation)return;
const cView=new DataView(certainty);
if(cView.getUint32(0,true)!==0x35415148||cView.getUint32(4,true)!==n||certainty.byteLength!==8+n)throw Error("Ошибка слоя геометрической стабильности R15");
const source=new Uint8Array(data,8), regions=new Uint8Array(ann,8), stability=new Uint8Array(certainty,8);
let count=0;for(let i=0;i<n;i++)if(regions[i*2]===1)count++;
const cp=new Uint8Array(count*8), cm=new Uint8Array(count*2), cs=new Uint8Array(count);
for(let i=0,j=0;i<n;i++)if(regions[i*2]===1){cp.set(source.subarray(i*8,i*8+8),j*8);cm.set(regions.subarray(i*2,i*2+2),j*2);cs[j]=stability[i];j++;}
for(const old of [pointData,cerebData])if(old){gl.deleteBuffer(old.buffer);gl.deleteBuffer(old.metaBuffer);gl.deleteBuffer(old.stabilityBuffer);gl.deleteVertexArray(old.vao);}
pointData=pointGeometry(source,regions,stability);
cerebData=count?pointGeometry(cp,cm,cs):null;cerebCount=count;numPoints=n;
document.getElementById("cerebCount").textContent=count.toLocaleString("ru-RU")+" точек в предполагаемой зоне (не подтверждённый мозжечок)";
document.getElementById("rendered").textContent=n.toLocaleString("ru-RU");
status.textContent="Исходное облако: "+n.toLocaleString("ru-RU")+" точек";progress.style.width="72%";dirty=true;
}
async function loadLines(){
const data=await ungzip("hq500m_exact_fibers_r11.bin.gz"),view=new DataView(data);
if(view.getUint32(0,true)!==0x33465148)throw Error("Неверный заголовок связей");
localEdges=view.getUint32(4,true);globalEdges=view.getUint32(8,true);
if(data.byteLength!==12+12*(localEdges+globalEdges))throw Error("Неполный массив связей");
lineData=lineGeometry(new Uint8Array(data,12));loaded=true;
document.getElementById("edges").textContent=(localEdges+globalEdges).toLocaleString("ru-RU");
progress.style.width="100%";dirty=true;
status.textContent="Готово: "+numPoints.toLocaleString("ru-RU")+" точек; "+(localEdges+globalEdges).toLocaleString("ru-RU")+" вычисленных связей";
}

const PVS="#version 300 es\nprecision highp float;\nlayout(location=0) in vec3 aPosition;\nlayout(location=2) in vec2 aRegion; // 0 cortex, 1 cerebellum, 2 brainstem, 3 deep proxy\nlayout(location=3) in float aStability; // nearby R14 label agreement, NOT atlas certainty\nlayout(location=1) in vec2 aSource; // x=geometry-derived concave sulcus depth; y=stable point seed\nuniform float uYaw,uPitch,uCamera,uAspect,uHeight,uSize,uJitter,uRegionView,uScale,uReplicaPass,uRegionInstances,uStabilityMin;\nout vec3 vColor;\n\nvec3 turn(vec3 p){\n float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);\n p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);\n return vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);\n}\nvec3 stableHash(vec3 p){\n p=fract(p*vec3(.1031,.1030,.0973));\n p+=dot(p,p.yxz+33.33);\n return fract((p.xxy+p.yxx)*p.zyx);\n}\nvoid main(){\n float region=floor(aRegion.x+.5);\n if(uReplicaPass>.5 && (region!=1.0 || aStability<uStabilityMin)){gl_Position=vec4(2.,2.,2.,1.);gl_PointSize=0.;vColor=vec3(0.);return;}\n vec3 original=aPosition*2.0-1.0;\n // Subpixel-scale static perturbation. Never animated, never stored in the model.\n // Seed differs per source point; the red surface loses the quantized grid.\n vec3 key=vec3(aSource.y*313.1+11.0,\n                aPosition.x*73.0+aPosition.y*39.0,\n                aPosition.z*101.0+aSource.y*31.0);\n vec3 jitter=(stableHash(key)-.5)*2.0*uJitter;\n vec3 p=original+jitter+normalize(original+vec3(.00001))*uJitter*.09;\n if(float(gl_InstanceID)+uReplicaPass>0.5){\n float inst=float(gl_InstanceID)+uReplicaPass;\n vec3 offset=(stableHash(key+vec3(inst*.131,inst*.771,inst*.334))-.5)*.0032;\n p+=offset-normalize(original+vec3(.00001))*.0014;\n }\n vec3 r=turn(p);\n float depth=max(.1,uCamera-r.z),f=2.10;\n gl_Position=vec4(r.x*f/uAspect,r.y*f,depth*1.003-.34,depth);\n float cellPressure=1.0+aRegion.y/70.0;\n float biologicalRatio=region==1.0?34.7:1.0; // 69B/10% vs 16.3B/82% mass\n float dynamicRadius=pow(cellPressure,-.17)*pow(biologicalRatio,-.18)*uScale;\n // Approximate projected-area conservation: more proxy instances, smaller glyphs.\n // 0.85 factor softens gaps while staying much closer to stable coverage than R14.\n float coverage=region==1.0?mix(1.0,inversesqrt(max(1.,uRegionInstances)),.85):1.0;\n gl_PointSize=clamp(uSize*uHeight/(120.0*depth)*dynamicRadius*coverage,.72,5.6);\n float wave=.58+.17*sin(original.y*17.+original.x*8.)\n                 +.13*sin(original.z*23.-original.y*5.);\n float light=clamp(wave,.12,1.0);\n vec3 red=mix(vec3(.12,.002,.022),vec3(.93,.026,.077),light)\n           *(.83+.17*clamp(r.z,-1.0,1.0));\n // EXACTLY no random blue selector. This byte was measured offline\n // from local 3D convexity plus exterior exposure of the actual point cloud.\n float corticalGate=smoothstep(-.43,-.02,original.y);\n float blue=smoothstep(.045,.63,aSource.x)*corticalGate;\n vColor=mix(red,vec3(.035,.11,.93),blue*.98);\n if(uRegionView>.5){\n  vec3 regionColor=region<.5?vec3(.88,.035,.085):\n      region<1.5?vec3(.62,.14,.95):\n      region<2.5?vec3(.98,.49,.17):vec3(.92,.38,.54);\n  float boundaryAgreement=smoothstep(uStabilityMin-.08,uStabilityMin+.08,aStability);\n  vColor=mix(vColor,regionColor,.68*boundaryAgreement);\n  if(uRegionView>1.5 && uRegionView<2.5 && region!=1.0)vColor*=.17;\n  if(uRegionView>1.5 && uRegionView<2.5 && region==1.0)vColor*=mix(.22,1.0,boundaryAgreement);\n  if(uRegionView>2.5){vColor=mix(vColor,vec3(.97,.42,.095),1.0-boundaryAgreement);}\n }\n}\n";
const PFS="#version 300 es\nprecision highp float;\nin vec3 vColor;out vec4 frag;\nvoid main(){float r=length(gl_PointCoord-vec2(.5))*2.0;if(r>1.0)discard;\nfloat core=1.0-smoothstep(.50,1.0,r);\nfrag=vec4(vColor*(.78+.34*core),1.0);}";
const LVS="#version 300 es\nprecision highp float;\nlayout(location=0) in vec3 aPosition;\nuniform float uYaw,uPitch,uCamera,uAspect,uTime,uLong;\nout vec3 vColor;\nvec3 turn(vec3 p){\n float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);\n p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);\n return vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);\n}\nvoid main(){\n vec3 p=aPosition*2.0-1.0,r=turn(p);\n float depth=max(.1,uCamera-r.z),f=2.10;\n gl_Position=vec4(r.x*f/uAspect,r.y*f,depth*1.003-.34-.0009*depth,depth);\n float pulse=sin(uTime*1.45+34.*p.x+27.*p.y+17.*p.z);\n vColor=mix(vec3(.48,.005,.04),vec3(1.,.085,.18),.48+.5*pulse);\n vColor=mix(vColor,vec3(.96,.1,.25),uLong*.23);\n}";
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
scene(pp,time);uniform("uSize",mobile?1.18:1.31,pp);uniform("uJitter",Number(jitterCtl.value)*.000065,pp);
uniform("uRegionView",Number(regionCtl.value),pp);uniform("uScale",Number(sizeCtl.value)/100,pp);
const repl=mobile?Math.min(4,Number(replicaCtl.value)):Number(replicaCtl.value);
uniform("uRegionInstances",repl,pp);uniform("uStabilityMin",Number(boundaryCtl.value)/100,pp);
uniform("uReplicaPass",0,pp);gl.bindVertexArray(pointData.vao);gl.drawArrays(gl.POINTS,0,numPoints);
// Only candidate-zone vertices are redrawn. R14 instead submitted the entire cloud 2-4x.
if(cerebData&&repl>1){uniform("uReplicaPass",1,pp);gl.bindVertexArray(cerebData.vao);
gl.drawArraysInstanced(gl.POINTS,0,cerebCount,repl-1);}
if(loaded&&showEdges.checked){
gl.depthMask(false);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
scene(lp,time);gl.bindVertexArray(lineData.vao);const a=Number(strength.value)/100;
uniform("uLong",0,lp);uniform("uOpacity",.33*a,lp);
const shortCount=mobile?Math.min(localEdges,120000):localEdges;
gl.drawArrays(gl.LINES,0,2*shortCount);
if(showLong.checked){uniform("uLong",1,lp);uniform("uOpacity",.14*a,lp);
gl.drawArrays(gl.LINES,2*localEdges,2*(mobile?Math.min(globalEdges,52000):globalEdges));}
gl.disable(gl.BLEND);gl.depthMask(true);}
gl.bindVertexArray(null);
}
requestAnimationFrame(render);
}
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
showEdges.onchange=showLong.onchange=regionCtl.onchange=replicaCtl.onchange=boundaryCtl.oninput=strength.oninput=jitterCtl.oninput=sizeCtl.oninput=()=>dirty=true;
document.getElementById("orbit").onclick=e=>{spin=!spin;e.target.textContent=spin?"Остановить":"Автовращение";dirty=true;};
document.getElementById("reset").onclick=()=>{yaw=.62;pitch=.12;distance=mobile?4.7:3.00;dirty=true;};
document.getElementById("snap").onclick=()=>{dirty=true;requestAnimationFrame(()=>canvas.toBlob(b=>{if(!b)return;let a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="HQ500M-R15-Boundary-Stable.png";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000);},"image/png"));};
let touches=new Map(),pinch=0;
canvas.addEventListener("pointerdown",e=>{canvas.setPointerCapture(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);});
canvas.addEventListener("pointermove",e=>{if(!touches.has(e.pointerId))return;const before=touches.get(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);
if(touches.size>=2){let list=Array.from(touches.values());let d=Math.hypot(list[0][0]-list[1][0],list[0][1]-list[1][1]);if(pinch>0)distance=Math.max(1.55,Math.min(9,distance*pinch/d));pinch=d;}
else{yaw+=(e.clientX-before[0])*.008;pitch=Math.max(-1.45,Math.min(1.45,pitch+(e.clientY-before[1])*.008));}dirty=true;});
function release(e){touches.delete(e.pointerId);pinch=0;}canvas.addEventListener("pointerup",release);canvas.addEventListener("pointercancel",release);
canvas.addEventListener("wheel",e=>{e.preventDefault();distance=Math.max(1.55,Math.min(9,distance*Math.exp(e.deltaY*.001)));dirty=true;},{passive:false});
window.addEventListener("resize",()=>dirty=true);
