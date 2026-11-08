#!/usr/bin/env python3
"""R22 depth-only exterior point-stencil occlusion, no saved mesh or neuron arrays."""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
src=(P/'docs/procedural/procedural_r21.js').read_text()
s=src
def replace(a,b):
    global s
    n=s.count(a)
    assert n==1,(n,a[:125])
    s=s.replace(a,b)

replace('let P=null,L=null,pg=null,lg=null,loading=false;',
'''let P=null,L=null,Mask=null,pg=null,lg=null,mg=null,maskCount=0,maskActual=false,maskBias=.0022,maskFootprint=7.0,loading=false;''')

# Invisible occluder uses 46.5K R18 HRA anatomical shell stencil
# points (not the original 283 meshes) for the scene Z buffer.
marker='function shader(t,src){'
assert s.count(marker)==1
new="""const maskVS=[
"#version 300 es","precision highp float;",
"layout(location=0) in vec3 aPos;",
"uniform float uYaw,uPitch,uDistance,uAspect,uZoom,uHeight,uSplatPx;uniform vec3 uCenter;",
"void main(){",
"vec3 p=(aPos-uCenter)*uZoom;",
"float c=cos(uYaw),s=sin(uYaw),u=cos(uPitch),v=sin(uPitch);",
"p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);",
"p=vec3(p.x,u*p.y-v*p.z,v*p.y+u*p.z);",
"float d=max(.12,uDistance-p.z);",
"gl_Position=vec4(2.05*p.x/uAspect,2.05*p.y,d*1.003-.35,d);",
"// Area coverage for the 46.5K shell stencil anchors.",
"// Mask only affects depth, never visible color or neuron identity.",
"gl_PointSize=clamp(uSplatPx*uHeight/(850.*d)*3.5,4.2,13.);",
"}"].join("\\n");
const maskFS=[
"#version 300 es","precision highp float;",
"uniform float uBias;",
"void main(){",
"vec2 q=gl_PointCoord*2.-1.;if(dot(q,q)>1.0)discard;",
"// Behind the actual HRA shell anchor by a small depth epsilon:",
"// retains foreground glyph jitter while rejecting neurons behind cortex.",
"gl_FragDepth=min(gl_FragCoord.z+uBias,1.0);",
"}"].join("\\n");
"""
s=s.replace(marker,new+marker)

replace('''if(pg&&points){common(P);uf(P,"uHeight",h);gl.bindVertexArray(pg.v);gl.drawArrays(gl.POINTS,0,points);}''',
'''maskActual=false;
 if($("occludeBack").checked&&selected<0&&tract<0&&!focusedGraph&&mg&&maskCount){
  // Depth-only, zero color writes. The anatomical shell is not displayed.
  gl.colorMask(false,false,false,false);
  common(Mask);uf(Mask,"uHeight",h);uf(Mask,"uBias",maskBias);uf(Mask,"uSplatPx",maskFootprint);
  gl.bindVertexArray(mg.v);gl.drawArrays(gl.POINTS,0,maskCount);
  gl.colorMask(true,true,true,true);
  maskActual=true;
 }
 if(pg&&points){common(P);uf(P,"uHeight",h);gl.bindVertexArray(pg.v);gl.drawArrays(gl.POINTS,0,points);}''')

replace('''if(gl){try{P=prog(pointVS,pointFS);L=prog(lineVS,lineFS);requestAnimationFrame(frame);}catch(e){S.textContent="Ошибка WebGL2: "+e.message;console.error(e);}}else S.textContent="Нужен WebGL2";''',
'''if(gl){try{
 P=prog(pointVS,pointFS);L=prog(lineVS,lineFS);Mask=prog(maskVS,maskFS);
 requestAnimationFrame(frame);
}catch(e){S.textContent="Ошибка WebGL2: "+e.message;console.error(e);}}else S.textContent="Нужен WebGL2";''')

needle='function allocation(n){'
assert s.count(needle)==1
func='''function buildDepthStencil(){
 // The existing HST8 geometry already has 78K source HRA shell anchors.
 // Only outer tissue classes participate; tracts/cavities are excluded.
 // Nothing is fetched or stored for the occlusion buffer beyond R18 HST8.
 const verts=[];
 for(const r of rows){
  if(!outer(r)||r.shell_count<1)continue;
  for(let j=0;j<r.shell_count;j++)verts.push(...cell(r.shell_start+j));
 }
 free(mg);
 mg=verts.length?make(verts,3,[[0,3,0]]):null;
 maskCount=verts.length/3;
 if(maskCount<15000||maskCount>80000)throw Error("Некорректный шаблон видимости HRA");
 return maskCount;
}
'''
s=s.replace(needle,func+needle)

replace(''' dropdown();quotas=allocation(total);rebuild();''',
''' dropdown();quotas=allocation(total);
 buildDepthStencil();
 rebuild();''')

replace(''' $("lod").oninput=later;$("lodMode").onchange=later;''',
''' $("occludeBack").onchange=()=>{dirty=true;readout();};
 $("lod").oninput=later;$("lodMode").onchange=later;''')

replace(''' $("lodValue").textContent=F.format(budget())+" GPU-точек · режим: "+''',
''' $("occlusionStatus").textContent=$("occludeBack").checked?
   "Маска HRA: "+F.format(maskCount)+" опорных точек · скрытые слои отсекаются глубиной":
   "Отсечение выключено: задние поверхности и глубинные связи видны";
 $("lodValue").textContent=F.format(budget())+" кандидатов GPU · режим: "+''')

replace('''  getQuota:id=>quotas[Number(id)],''',
'''  getQuota:id=>quotas[Number(id)],
  getVisibility:()=>({enabled:$("occludeBack").checked,active:maskActual,
     sourceSurfaceStencil:maskCount,bias:maskBias,splatPx:maskFootprint,registeredToHRA:true,
     hidesFragmentsNotVertices:true,
     mode:(selected>=0||tract>=0||!!focusedGraph)?"focused_no_mask":"whole_brain_mask"}),
  setVisibilityConfig:({bias,pixelSize})=>{
    if(Number.isFinite(bias))maskBias=Math.max(.0003,Math.min(.012,bias));
    if(Number.isFinite(pixelSize))maskFootprint=Math.max(3,Math.min(16,pixelSize));
    dirty=true;return {bias:maskBias,splatPx:maskFootprint};
  },
  setBackfaceOcclusion:value=>{
    $("occludeBack").checked=!!value;dirty=true;readout();
  },''')

# Important: "all visible neurons" counter is an issued GPU-point count,
# not an occlusion-passed fragment count. Rename label to avoid false claim.
(P/'docs/procedural/procedural_r22.js').write_text(s)

h=(P/'docs/procedural/index.html').read_text()
if 'procedural_r21.js' in h:
    assert h.count('procedural_r21.js')==1
    h=h.replace('procedural_r21.js','procedural_r22.js')
else:
    assert h.count('procedural_r22.js')==1
h=h.replace('<title>HQ500M R21 · Local Curved Fibers + Dense Neural Atlas</title>',
  '<title>HQ500M R22 · Depth-culled Neural Atlas</title>')
h=h.replace('R21 · 283 HRA','R22 · 283 HRA')
h=h.replace('GPU-точек','GPU-кандидатов')
needle='<span class="mini">Локальные схематические волокна</span>'
assert h.count(needle)==1
block='''<label class="mini" style="margin-top:10px">
<input id="occludeBack" type="checkbox" checked style="width:auto;min-height:0;accent-color:#e00018;margin-right:7px">
Не отображать закрытые нейроны и связи
</label>
<div id="occlusionStatus" style="font-size:10px;line-height:1.4;color:#c9b0bb;margin-top:4px">Глубина анатомического шаблона HRA</div>
<p class="note">Невидимая геометрия служит только маской глубины: задние точки и пересекающие мозг связи отсекаются на GPU. В режиме выбранного нейрона, области или тракта маска автоматически снимается.</p>
'''
if 'id="occludeBack"' not in h:h=h.replace(needle,block+needle)
h=h.replace('Показано точек<strong id="gpuCount">', 'GPU-кандидаты<strong id="gpuCount">')
(P/'docs/procedural/index.html').write_text(h)
import runpy
runpy.run_path(str(P/'tools/patch_r22_front_shell.py'),run_name='__main__')
runpy.run_path(str(P/'tools/patch_r22_triangle_sampling.py'),run_name='__main__')
print('R22: depth mask from R18 stencil;',len(s),'JS bytes')
