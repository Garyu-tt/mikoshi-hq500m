#!/usr/bin/env python3
"""R20 high-density GPU level of detail over the source-preserving R19 generator."""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
source=(P/'docs/procedural/procedural_r19.js').read_text()
s=source
def swap(old,new):
 global s
 count=s.count(old)
 assert count==1,(count,old[:130])
 s=s.replace(old,new)

swap('''function budget(){return Math.min(total,Number($("lod").value),mobile?90000:220000,Math.max(1600,Math.round(24000*Math.pow(total/5e8,.28))));}''',
'''// Memory-safe LOD only; virtual population and region quotas never change.
function budget(){
 const slider=Number($("lod").value), mode=$("lodMode").value;
 const automatic=Math.max(12000,Math.round(220000*Math.pow(total/500000000,.22)));
 const cap=mobile?120000:1100000;
 return Math.min(total,cap,mode==="manual"?slider:Math.min(slider,automatic));
}''')
swap('''const factor=Math.max(.8,Math.min(4,2.8*Math.sqrt(24000/B)));''',
'''// Area-aware point scaling: denser point clouds remain legible, without
 // oversized opaque markers or the nearly invisible R19 0.8px glyphs.
 const factor=Math.max(1.08,Math.min(3.7,2.90*Math.pow(60000/Math.max(1,B),.35)));''')
swap('''const radius=Math.min(.0018,4.0e-4/meta.max_extent_m);''',
'''// A little less than 1mm in reference space; avoid obvious duplicate
 // points if an HRA shell stencil seed is reused at high GPU density.
 const radius=Math.min(.0020,5.0e-4/meta.max_extent_m);''')
swap(''' $("lod").oninput=later;$("background").onchange=later;$("regionSearch").oninput=search;''',
''' $("lod").oninput=later;$("lodMode").onchange=later;
 $("background").onchange=later;$("regionSearch").oninput=search;''')
swap('''$("lodValue").textContent=F.format(budget())+" активных GPU-точек (максимум "+F.format(Number($("lod").value))+")";''',
'''$("lodValue").textContent=F.format(budget())+" GPU-точек · режим: "+
   ($("lodMode").value==="auto"?"автоматический":"ручной")+
   " · ограничение "+F.format(mobile?120000:1100000);''')
swap('''  getQuota:id=>quotas[Number(id)],''',
'''  getQuota:id=>quotas[Number(id)],
  getLOD:()=>({rendered:points,target:budget(),mode:$("lodMode").value,
    requested:Number($("lod").value),platformCap:mobile?120000:1100000}),''')
# Graph isolation stays sparse regardless of density controls.
(P/'docs/procedural/procedural_r20.js').write_text(s)

h=(P/'docs/procedural/index.html').read_text()
if 'procedural_r19.js' in h:
    assert h.count('procedural_r19.js')==1
    h=h.replace('procedural_r19.js','procedural_r20.js')
else:
    assert h.count('procedural_r20.js')==1
h=h.replace('<title>HQ500M R19 · Procedural Neural Atlas + ID Graph</title>',
            '<title>HQ500M R20 · High-Density Procedural Neural Atlas</title>')
h=h.replace('R19 · 283 HRA','R20 · 283 HRA')
needle='''<span class="mini">GPU-детализация (бюджет точек)</span>
<input id="lod" type="range" min="8000" max="220000" step="4000" value="130000">
<div id="lodValue" class="note">60 000 отображаемых точек</div>'''
repl='''<span class="mini">Уплотнение нейронного облака · GPU LOD</span>
<select id="lodMode" aria-label="Режим плотности"><option value="auto" selected>Авто: адаптация к количеству нейронов</option><option value="manual">Вручную: выбранный лимит точек</option></select>
<input id="lod" type="range" min="20000" max="1100000" step="20000" value="800000" aria-label="Максимум отображаемых нейронных точек" style="margin-top:5px">
<div id="lodValue" class="note">Подготовка адаптивного уровня детализации…</div>
<p class="note">В авто-режиме ~220 тыс. видимых точек при 500 млн виртуальных нейронов и ~680 тыс. при 86,1 млрд. Ручной режим — до 1,1 млн на ПК и до 120 тыс. на мобильных. Все внутренние области скрыты до выбора.</p>'''
if 'id="lodMode"' not in h:
    assert h.count(needle)==1
    h=h.replace(needle,repl)
else:
    assert h.count('id="lodMode"')==1
(P/'docs/procedural/index.html').write_text(h)
print("R20 high-density viewer created",len(s),"JS characters")
