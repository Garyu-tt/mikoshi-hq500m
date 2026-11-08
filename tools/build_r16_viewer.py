#!/usr/bin/env python3
"""Build R16 viewer; source positions and existing JS R15 remain untouched."""
from pathlib import Path
import json
P=Path(__file__).resolve().parents[1]
s=(P/'docs/viewer_r15.js').read_text()

def between(before, after, replacement):
    global s
    i=s.find(before); j=s.find(after, i+len(before))
    assert i>=0 and j>i,(before,after)
    assert s.count(before)==1 and s.count(after)==1,(before,after)
    s=s[:i]+replacement+s[j:]

def swap(before,after):
    global s
    assert s.count(before)==1, f"match {s.count(before)} {before[:100]!r}"
    s=s.replace(before,after)

ctrl='''const regionNames=["Лобная","Теменная","Височная","Затылочная","Мозжечковая","Стволовая","Глубинные структуры","Островковая"];
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
'''
between('ctl.innerHTML=', 'document.querySelector("#kicker")', ctrl)
swap('DEEP RUBY / BOUNDARY-STABLE DENSITY · R15','DEEP RUBY / SMOOTH REGIONS · R16')
swap('Те же 1 192 673 исходные координаты + предполагаемые области, устойчивость границ и динамические размеры. Синтетические связи HQ500M Q0.8 сохранены.',
     '1 192 673 неизменных точек, восемь плавно смешиваемых условных зон и непрерывная плотность. Без подтверждённого анатомического атласа.')
swap('const regionCtl=document.getElementById("regionView"),sizeCtl=document.getElementById("pointScale"),replicaCtl=document.getElementById("replicas"),boundaryCtl=document.getElementById("boundary");',
     'const regionCtl=document.getElementById("regionView"),sizeCtl=document.getElementById("pointScale"),replicaCtl=document.getElementById("replicas"),focusCtl=document.getElementById("focusZone");')
geo='''function pointGeometry(bytes,regionBytes,softBytes){
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
'''
between('function pointGeometry(', 'function lineGeometry(',geo)
start='const certainty=await ungzip(selected==="lite"?"hq500m_region_stability_lite_r15.bin.gz":"hq500m_region_stability_r15.bin.gz");'
end='document.getElementById("rendered").textContent=n.toLocaleString("ru-RU");'
load='''const soft=await ungzip(selected==="lite"?"hq500m_soft_regions_lite_r16.bin.gz":"hq500m_soft_regions_r16.bin.gz");
if(token!==generation)return;
const q=new DataView(soft);
if(q.getUint32(0,true)!==0x36575148||q.getUint32(4,true)!==n||soft.byteLength!==8+8*n)throw Error("Ошибка слоя восьми мягких регионов R16");
const source=new Uint8Array(data,8), regions=new Uint8Array(ann,8), weights=new Uint8Array(soft,8);
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
'''
between(start,end,load)
glsl="""#version 300 es
precision highp float;
layout(location=0) in vec3 aPosition;
layout(location=1) in vec2 aSource; // sulcal depth and stable seed, from unchanged R13
layout(location=2) in vec2 aRegion; // local occupancy proxy from R14; region id ignored
layout(location=3) in vec4 aW0; // frontal, parietal, temporal, occipital [0,1]
layout(location=4) in vec4 aW1; // cerebellum, brainstem, deep, insula [0,1]
uniform float uYaw,uPitch,uCamera,uAspect,uHeight,uSize,uJitter,uRegionView,uScale;
uniform float uReplicaPass,uRegionInstances,uFocusZone;
out vec3 vColor;
vec3 turn(vec3 p){
 float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);
 p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);
 return vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);
}
vec3 stableHash(vec3 p){
 p=fract(p*vec3(.1031,.1030,.0973));
 p+=dot(p,p.yxz+33.33);
 return fract((p.xxy+p.yxx)*p.zyx);
}
float areaWeight(float index) {
 if(index<.5)return aW0.x;
 if(index<1.5)return aW0.y;
 if(index<2.5)return aW0.z;
 if(index<3.5)return aW0.w;
 if(index<4.5)return aW1.x;
 if(index<5.5)return aW1.y;
 if(index<6.5)return aW1.z;
 return aW1.w;
}
void main(){
 vec3 original=aPosition*2.0-1.0;
 vec3 key=vec3(aSource.y*313.1+11.0,
          aPosition.x*73.0+aPosition.y*39.0,
          aPosition.z*101.0+aSource.y*31.0);
 float cereb=clamp(aW1.x,0.,1.);
 float inst=float(gl_InstanceID)+uReplicaPass;
 if(uReplicaPass>.5){
   // Gradual, deterministic local coverage. Never cut off at a horizontal plane.
   float keep=smoothstep(.035,.58,cereb);
   float toss=stableHash(key+vec3(inst*17.31,inst*5.63,inst*3.61)).x;
   if(toss>keep){
     gl_Position=vec4(2.,2.,2.,1.);gl_PointSize=0.;vColor=vec3(0.);return;
   }
 }
 vec3 jitter=(stableHash(key)-.5)*2.0*uJitter;
 vec3 p=original+jitter+normalize(original+vec3(.00001))*uJitter*.09;
 if(uReplicaPass>.5){
   vec3 offset=(stableHash(key+vec3(inst*.131,inst*.771,inst*.334))-.5)*.0032;
   p+=offset-normalize(original+vec3(.00001))*.0014;
 }
 vec3 r=turn(p);
 float depth=max(.1,uCamera-r.z),f=2.10;
 gl_Position=vec4(r.x*f/uAspect,r.y*f,depth*1.003-.34,depth);
 float cellPressure=1.0+aRegion.y/70.0;
 // This is a continuous glyph-size *visual* proxy, NOT physical neuron diameter.
 float biologicalRatio=mix(1.0,34.7,smoothstep(.02,.80,cereb));
 float dynamicRadius=pow(cellPressure,-.17)*pow(biologicalRatio,-.18)*uScale;
 float coverage=mix(1.0,inversesqrt(max(1.,uRegionInstances)),
                    .88*smoothstep(.02,.65,cereb));
 gl_PointSize=clamp(uSize*uHeight/(120.0*depth)*dynamicRadius*coverage,.72,5.6);
 float wave=.58+.17*sin(original.y*17.+original.x*8.)+.13*sin(original.z*23.-original.y*5.);
 float light=clamp(wave,.12,1.0);
 vec3 red=mix(vec3(.12,.002,.022),vec3(.93,.026,.077),light)
           *(.83+.17*clamp(r.z,-1.0,1.0));
 float blue=smoothstep(.045,.63,aSource.x)*smoothstep(-.43,-.02,original.y);
 vColor=mix(red,vec3(.035,.11,.93),blue*.98);
 // Palette weights add up to 1.0. Every region blend is continuous.
 vec3 painted =
   aW0.x*vec3(.94,.14,.24)+aW0.y*vec3(.82,.34,.66)+
   aW0.z*vec3(.94,.56,.31)+aW0.w*vec3(.54,.31,.90)+
   aW1.x*vec3(.31,.50,.93)+aW1.y*vec3(.91,.74,.40)+
   aW1.z*vec3(.73,.44,.82)+aW1.w*vec3(.30,.69,.69);
 if(uRegionView>.5) {
   vColor=mix(vColor,painted,.87);
   if(uRegionView>1.5 && uRegionView<2.5){
      float focus=areaWeight(uFocusZone);
      vColor*=.15+.85*smoothstep(.03,.62,focus);
   }
   if(uRegionView>2.5) {
      // Cerebellar candidate weight heat map, not verified biological density.
      vColor=mix(vec3(.08,.02,.06),vec3(.39,.58,.98),
                 smoothstep(.005,.53,cereb));
   }
 }
}
"""
between('const PVS=', 'const PFS=', "const PVS="+json.dumps(glsl,ensure_ascii=False)+";\n")
swap('uniform("uRegionView",Number(regionCtl.value),pp);uniform("uScale",Number(sizeCtl.value)/100,pp);',
     'uniform("uRegionView",Number(regionCtl.value),pp);uniform("uFocusZone",Number(focusCtl.value),pp);uniform("uScale",Number(sizeCtl.value)/100,pp);')
swap('uniform("uRegionInstances",repl,pp);uniform("uStabilityMin",Number(boundaryCtl.value)/100,pp);',
     'uniform("uRegionInstances",repl,pp);')
swap('showEdges.onchange=showLong.onchange=regionCtl.onchange=replicaCtl.onchange=boundaryCtl.oninput=strength.oninput=jitterCtl.oninput=sizeCtl.oninput=()=>dirty=true;',
     '''showEdges.onchange=showLong.onchange=regionCtl.onchange=replicaCtl.onchange=strength.oninput=jitterCtl.oninput=sizeCtl.oninput=()=>dirty=true;
focusCtl.onchange=()=>{regionCtl.value="2";dirty=true;};''')
swap('HQ500M-R15-Boundary-Stable.png','HQ500M-R16-Smooth-Regions.png')
(P/'docs/viewer_r16.js').write_text(s)
index=(P/'docs/index.html').read_text()
if 'viewer_r16.js' not in index:
    assert index.count('viewer_r15.js')==1
    index=index.replace('viewer_r15.js','viewer_r16.js')
else:
    assert index.count('viewer_r16.js')==1
index=index.replace('Boundary-Stable Density R15','Smooth Anatomical Zones R16')
index=index.replace('BOUNDARY-STABLE DENSITY · R15','SMOOTH REGIONS · R16')
index=index.replace('1,19 млн исходных точек. Предполагаемые области, геометрическая устойчивость их границ и GPU-детализация без перемещения исходных точек. Атласная регистрация пока отсутствует.',
 '''1,19 млн исходных точек, восемь плавно размеченных условных областей и GPU-детализация без жёсткой границы. Атласная регистрация пока отсутствует.''')
(P/'docs/index.html').write_text(index)
import runpy
runpy.run_path(str(P/'tools/patch_r16_explorer_bridge.py'),run_name='__main__')
print('Wrote R16 viewer',len(s),'chars; R15 intact')
