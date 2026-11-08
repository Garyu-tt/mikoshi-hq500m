#!/usr/bin/env python3
"""Make synthetic fibers local, curved and depth-occluded in the full cloud.
Input R20, outputs R21; HRA stencils, addresses and adjacency unchanged.
"""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
s=(P/'docs/procedural/procedural_r20.js').read_text()
def swap(a,b):
    global s
    assert s.count(a)==1,(s.count(a),a[:110])
    s=s.replace(a,b)
swap('''if(lg&&segments){gl.disable(gl.DEPTH_TEST);gl.depthMask(false);common(L);gl.bindVertexArray(lg.v);gl.drawArrays(gl.LINES,0,2*segments);gl.depthMask(true);gl.enable(gl.DEPTH_TEST);}''',
'''if(lg&&segments){
  // Ordinary local neurites obey the depth of the point cloud.
  // Isolated graphs and selected anatomical tracts remain readable on top.
  const emphasized=!!focusedGraph||tract>=0;
  if(emphasized)gl.disable(gl.DEPTH_TEST);
  else gl.enable(gl.DEPTH_TEST);
  gl.depthMask(false);common(L);gl.bindVertexArray(lg.v);
  gl.drawArrays(gl.LINES,0,2*segments);
  gl.depthMask(true);gl.enable(gl.DEPTH_TEST);
}''')
start=s.index('function syntheticEdges(data){')
stop=s.index('function tractEdges(r){',start)
assert start>=0 and stop>start
block='''// Draw a thin, region-local *schematic* neurite in short curved segments.
// This is only a visualization of an already-generated synthetic ID edge.
// It is NOT traced biological axonal morphology.
function localFiber(out,a,b,seed,col){
 const dx=b[0]-a[0],dy=b[1]-a[1],dz=b[2]-a[2];
 const len=Math.hypot(dx,dy,dz);
 if(len<=.000008)return 0;
 let tangent=[-dy,dx+.000001,0];
 let norm=Math.hypot(...tangent);
 if(norm<.00001){tangent=[0,-dz,dy+.00001];norm=Math.hypot(...tangent);}
 tangent=tangent.map(x=>x/norm);
 const rad=Math.min(.0045,len*.12)*(rnd(hash(seed+9973))-.5)*2;
 const bend=t=>4*t*(1-t)*rad;
 let prev=a;
 const div=len<.015?3:len<.040?4:6;
 for(let j=1;j<=div;j++){
  const t=j/div,w=bend(t);
  const next=[a[0]+dx*t+tangent[0]*w,a[1]+dy*t+tangent[1]*w,a[2]+dz*t+tangent[2]*w];
  addLine(out,prev,next,col);prev=next;
 }
 return div;
}
function syntheticEdges(data){
 const lines=[],roots=[];
 const active=selected>=0?[rows[selected]]:
  rows.filter(r=>quotas[r.index]>0&&r.cells_count&&r.shell_count).slice(0,130);
 for(const r of active){
  if(!quotas[r.index])continue;
  const count=selected>=0?Math.min(120,quotas[r.index]):Math.min(3,quotas[r.index]);
  for(let j=0;j<count;j++){
   const ordinal=Math.min(quotas[r.index]-1,Math.floor((j+.5)/count*quotas[r.index]));
   roots.push(regionRanges[r.index]+ordinal);
  }
 }
 const seen=new Set(),maxSpan=selected>=0?.095:.067;
 for(const id of roots){
  const src=neuronForId(id);
  if(!src.xyz)continue;
  for(const to of graphOutgoing(id)){
   if(lines.length/12>=2400)break;
   const signature=id+":"+to;
   if(seen.has(signature))continue;
   seen.add(signature);
   const dst=neuronForId(to);
   if(!dst.xyz)continue;
   // The full-scene context should NOT show long false axon chords.
   // Long synthetic projections are still available through the selected
   // ID graph and named tract mode, where their provisional nature is clear.
   if(src.region_id!==dst.region_id)continue;
   const d=Math.hypot(...src.xyz.map((x,k)=>x-dst.xyz[k]));
   if(d>maxSpan)continue;
   localFiber(lines,src.xyz,dst.xyz,hash(id)^hash(to),
     selected>=0?[.92,.34,.44]:[.44,.16,.29]);
  }
  if(lines.length/12>=2400)break;
 }
 return lines;
}
'''
s=s[:start]+block+s[stop:]
swap('''const factor=Math.max(1.08,Math.min(3.7,2.90*Math.pow(60000/Math.max(1,B),.35)));''',
'''// Slightly fuller appearance, still bounded by the same per-device GPU LOD.
 const factor=Math.max(1.28,Math.min(3.7,3.25*Math.pow(60000/Math.max(1,B),.35)));''')
swap('''gl_PointSize=clamp(aSize*uHeight/(130.*d),.75,8.);''',
'''gl_PointSize=clamp(aSize*uHeight/(130.*d),1.05,8.);''')
swap('''const lines=focusedGraph?dots.neuronEdges:
    tract>=0?tractEdges(rows[tract]):links?syntheticEdges(dots):[];''',
'''const lines=focusedGraph?dots.neuronEdges:
    tract>=0?tractEdges(rows[tract]):links?syntheticEdges(dots):[];''')
(P/'docs/procedural/procedural_r21.js').write_text(s)
html=(P/'docs/procedural/index.html').read_text()
if 'procedural_r20.js' in html:
    assert html.count('procedural_r20.js')==1
    html=html.replace('procedural_r20.js','procedural_r21.js')
else:
    assert html.count('procedural_r21.js')==1
html=html.replace('HQ500M R20 · High-Density Procedural Neural Atlas',
                  'HQ500M R21 · Local Curved Fibers + Dense Neural Atlas')
html=html.replace('R20 · 283 HRA','R21 · 283 HRA')
html=html.replace('Синтетические связи</button>',
                  'Локальные связи</button>')
html=html.replace('<span class="mini">Связи</span>',
 '''<span class="mini">Локальные схематические волокна</span>''')
html=html.replace('Трактовые линии — условные трассы',
'''В полном мозге связи ограничены пространственно близкими узлами:
длинные пересекающие весь мозг линии скрыты. Отдельный ID-путь
и режим тракта показывают выделенные проекции. Все волокна остаются
синтетическими, не реконструкцией аксонов.
Трактовые линии — условные трассы''')
(P/'docs/procedural/index.html').write_text(html)
print('R21 generated',len(s),'JS chars, anatomy and ID graph unchanged')
