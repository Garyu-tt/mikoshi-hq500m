#!/usr/bin/env python3
"""Apply R15 reversible view-layer upgrades to the frozen R14 viewer.
No original R11/R13 geometry or Q0.8 topology modified.
"""
from pathlib import Path
P = Path(__file__).resolve().parents[1]
s = (P/"docs/viewer_r14.js").read_text()

def swap(a, b):
    global s
    count = s.count(a)
    assert count == 1, f"expected 1 hit, found {count}: {a[:95]!r}"
    s = s.replace(a, b)

swap("const canvas=document.getElementById", "// R15: geometric boundary stability, NOT atlas verification.\nconst canvas=document.getElementById")
swap("Дополнительные отображаемые точки", "LOD мозжечковой зоны · условные точки")
swap("Масштаб нейронов (адаптивный)", "Размер нейронных маркеров · адаптивный")
swap('<option value="1" selected>Показать области</option>',
     '<option value="1" selected>Предположительные области</option>')
swap('<option value="2" selected>2× · мозжечок</option><option value="4">4× · мозжечок</option>',
     '<option value="2">2× · мозжечковая зона</option><option value="4" selected>4× · мозжечковая зона</option><option value="8">8× · мозжечковая зона</option>')
swap("'<div style=\"font-size:10px;line-height:1.35;color:#a8a1a4\">Области определены эвристически:",
     "'<div class=\"mini\" style=\"margin-top:7px\">Устойчивость границ зоны</div><input id=\"boundary\" type=\"range\" min=\"0\" max=\"95\" value=\"75\" style=\"width:100%\">'+\n'<div id=\"cerebCount\" style=\"font-size:10px;color:#e5b8c3;margin-top:5px\">Загрузка зоны…</div>'+\n'<div style=\"font-size:10px;line-height:1.35;color:#a8a1a4\">Области определены эвристически:")
swap("без регистрации МРТ нельзя подтвердить, что модель содержит отдельный мозжечок.",
     "Границы показывают геометрическую стабильность R14, не вероятность правильной анатомической разметки. Отдельный мозжечок не подтверждён.")
swap('<option value="2">Выделить мозжечок</option>',
     '<option value="2">Выделить предполагаемый мозжечок</option><option value="3">Показать сомнительные границы</option>')
swap('document.querySelector("#kicker").textContent="DEEP RUBY / DENSITY ATLAS · R14";',
     'document.querySelector("#kicker").textContent="DEEP RUBY / BOUNDARY-STABLE DENSITY · R15";')
swap("предполагаемые области мозга и адаптивные размеры точек.",
     "предполагаемые области, устойчивость границ и динамические размеры.")
swap('const regionCtl=document.getElementById("regionView"),sizeCtl=document.getElementById("pointScale"),replicaCtl=document.getElementById("replicas");',
     'const regionCtl=document.getElementById("regionView"),sizeCtl=document.getElementById("pointScale"),replicaCtl=document.getElementById("replicas"),boundaryCtl=document.getElementById("boundary");')
swap('function pointGeometry(bytes,regionBytes){', 'function pointGeometry(bytes,regionBytes,stabilityBytes){')
swap('gl.enableVertexAttribArray(2);gl.vertexAttribPointer(2,2,gl.UNSIGNED_BYTE,false,2,0);\ngl.bindVertexArray(null);return {buffer,metaBuffer,vao};}',
     'gl.enableVertexAttribArray(2);gl.vertexAttribPointer(2,2,gl.UNSIGNED_BYTE,false,2,0);\nconst stabilityBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,stabilityBuffer);gl.bufferData(gl.ARRAY_BUFFER,stabilityBytes,gl.STATIC_DRAW);\ngl.enableVertexAttribArray(3);gl.vertexAttribPointer(3,1,gl.UNSIGNED_BYTE,true,1,0);\ngl.bindVertexArray(null);return {buffer,metaBuffer,stabilityBuffer,vao};}')
swap('let numPoints=0,localEdges=0,globalEdges=0,pointData=null,lineData=null,pp,lp,loaded=false;',
     'let numPoints=0,cerebCount=0,localEdges=0,globalEdges=0,pointData=null,cerebData=null,lineData=null,pp,lp,loaded=false;')
swap('if(pointData){gl.deleteBuffer(pointData.buffer);gl.deleteBuffer(pointData.metaBuffer);gl.deleteVertexArray(pointData.vao);}\npointData=pointGeometry(new Uint8Array(data,8),new Uint8Array(ann,8));numPoints=n;',
     '''const certainty=await ungzip(selected==="lite"?"hq500m_region_stability_lite_r15.bin.gz":"hq500m_region_stability_r15.bin.gz");
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
document.getElementById("cerebCount").textContent=count.toLocaleString("ru-RU")+" точек в предполагаемой зоне (не подтверждённый мозжечок)";''')
swap(r'layout(location=1) in vec2 aSource; // x=geometry-derived concave sulcus depth; y=stable point seed',
     r'layout(location=3) in float aStability; // nearby R14 label agreement, NOT atlas certainty\nlayout(location=1) in vec2 aSource; // x=geometry-derived concave sulcus depth; y=stable point seed')
swap(r'uniform float uYaw,uPitch,uCamera,uAspect,uHeight,uSize,uJitter,uRegionView,uScale;',
     r'uniform float uYaw,uPitch,uCamera,uAspect,uHeight,uSize,uJitter,uRegionView,uScale,uReplicaPass,uRegionInstances,uStabilityMin;')
swap(r' if(gl_InstanceID>0 && region!=1.0){gl_Position=vec4(2.,2.,2.,1.);gl_PointSize=0.;vColor=vec3(0.);return;}\n',
     r' if(uReplicaPass>.5 && (region!=1.0 || aStability<uStabilityMin)){gl_Position=vec4(2.,2.,2.,1.);gl_PointSize=0.;vColor=vec3(0.);return;}\n')
swap(r' if(gl_InstanceID>0){\n float inst=float(gl_InstanceID);',
     r' if(float(gl_InstanceID)+uReplicaPass>0.5){\n float inst=float(gl_InstanceID)+uReplicaPass;')
swap(r' float dynamicRadius=pow(cellPressure,-.17)*pow(biologicalRatio,-.18)*uScale;\n gl_PointSize=clamp(uSize*uHeight/(120.0*depth)*dynamicRadius,.78,5.6);',
     r' float dynamicRadius=pow(cellPressure,-.17)*pow(biologicalRatio,-.18)*uScale;\n // Approximate projected-area conservation: more proxy instances, smaller glyphs.\n // 0.85 factor softens gaps while staying much closer to stable coverage than R14.\n float coverage=region==1.0?mix(1.0,inversesqrt(max(1.,uRegionInstances)),.85):1.0;\n gl_PointSize=clamp(uSize*uHeight/(120.0*depth)*dynamicRadius*coverage,.72,5.6);')
swap(r'  vColor=mix(vColor,regionColor,.68);\n  if(uRegionView>1.5 && region!=1.0)vColor*=.17;',
     r'  float boundaryAgreement=smoothstep(uStabilityMin-.08,uStabilityMin+.08,aStability);\n  vColor=mix(vColor,regionColor,.68*boundaryAgreement);\n  if(uRegionView>1.5 && uRegionView<2.5 && region!=1.0)vColor*=.17;\n  if(uRegionView>1.5 && uRegionView<2.5 && region==1.0)vColor*=mix(.22,1.0,boundaryAgreement);\n  if(uRegionView>2.5){vColor=mix(vColor,vec3(.97,.42,.095),1.0-boundaryAgreement);}')
swap('uniform("uRegionView",Number(regionCtl.value),pp);uniform("uScale",Number(sizeCtl.value)/100,pp);\ngl.bindVertexArray(pointData.vao);\ngl.drawArraysInstanced(gl.POINTS,0,numPoints,mobile?Math.min(2,Number(replicaCtl.value)):Number(replicaCtl.value));',
     '''uniform("uRegionView",Number(regionCtl.value),pp);uniform("uScale",Number(sizeCtl.value)/100,pp);
const repl=mobile?Math.min(4,Number(replicaCtl.value)):Number(replicaCtl.value);
uniform("uRegionInstances",repl,pp);uniform("uStabilityMin",Number(boundaryCtl.value)/100,pp);
uniform("uReplicaPass",0,pp);gl.bindVertexArray(pointData.vao);gl.drawArrays(gl.POINTS,0,numPoints);
// Only candidate-zone vertices are redrawn. R14 instead submitted the entire cloud 2-4x.
if(cerebData&&repl>1){uniform("uReplicaPass",1,pp);gl.bindVertexArray(cerebData.vao);
gl.drawArraysInstanced(gl.POINTS,0,cerebCount,repl-1);}''')
swap('showEdges.onchange=showLong.onchange=regionCtl.onchange=replicaCtl.onchange=strength.oninput=jitterCtl.oninput=sizeCtl.oninput=()=>dirty=true;',
     'showEdges.onchange=showLong.onchange=regionCtl.onchange=replicaCtl.onchange=boundaryCtl.oninput=strength.oninput=jitterCtl.oninput=sizeCtl.oninput=()=>dirty=true;')
swap('a.download="HQ500M-R14-Anatomical-Density.png";','a.download="HQ500M-R15-Boundary-Stable.png";')

(P/"docs/viewer_r15.js").write_text(s)
index=(P/"docs/index.html").read_text()
if 'viewer_r15.js' in index and 'viewer_r14.js' not in index:
    assert index.count('viewer_r15.js') == 1
else:
    assert index.count('viewer_r14.js')==1
    index=index.replace('viewer_r14.js','viewer_r15.js')
index=index.replace('Anatomical Density R14','Boundary-Stable Density R15')
index=index.replace('REGIONAL DENSITY · R14','BOUNDARY-STABLE DENSITY · R15')
index=index.replace('1,19 млн исходных точек с предварительным разделением на области и адаптивными размерами. Разметка является эвристикой, а не подтверждённым человеческим атласом.',
'''1,19 млн исходных точек. Предполагаемые области, геометрическая устойчивость их границ и GPU-детализация без перемещения исходных точек. Атласная регистрация пока отсутствует.''')
(P/"docs/index.html").write_text(index)
print("R15 viewer upgraded",len(s),"bytes; R14 untouched")
