#!/usr/bin/env python3
"""Derive R19 3D dynamic directed ID graph from R18 without touching R18 files."""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
src=(P/'docs/procedural/procedural_r18.js').read_text()
s=src
def swap(a,b):
    global s
    found=s.count(a)
    assert found==1, (found,a[:120])
    s=s.replace(a,b)

# Region-local Morton ordering improves spatial locality of per-neuron ordinal neighbors.
old='''function volumePosition(r,ordinal){
 if(r.cells_count===0)return null;
 const low=ordinal>>>0,hi=Math.floor(ordinal/4294967296)>>>0;
 const h=hash(low^hi^Math.imul(r.index+23,0x9e3779b1));
 const p=cell(r.cells_start+h%r.cells_count);
 const j=Math.min(.006,1.8e-3/meta.max_extent_m);
 return p.map((v,k)=>v+(rnd(h+Math.imul(k+1,0x51ed270b))-.5)*j);
}'''
new='''const spatialOrders=new Map();
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
 focusedGraph=null;center=[0,0,0];distance=3.5;
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
 distance=Math.max(1.5,Math.min(4,1.7+2*span));
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
'''
swap(old,new)
# Our ordinary "show links" button uses the very same LOD-independent directed synthetic graph.
a=s.index('function syntheticEdges(data){')
b=s.index('function tractEdges(r){',a)
assert a>=0 and b>a
s=s[:a]+'''function syntheticEdges(data){
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
''' + s[b:]

swap('''function rebuild(){
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
}''',
'''function rebuild(){
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
}''')
swap(''' total=n;$("target").value=String(n);
 for(const [id,preset]''',''' total=n;$("target").value=String(n);
 if(focusedGraph){focusedGraph=null;$("neuronResultR19").textContent="Общий размер изменён, диапазоны ID перенумерованы; выделение снято.";}
 spatialOrders.clear();regionCenters.clear();adjacencyCache.clear();
 for(const [id,preset]''')
swap(''' $("region").onchange=()=>{selected=Number($("region").value);tract=-1;$("tract").value="-1";later();};''',
''' $("region").onchange=()=>{focusedGraph=null;selected=Number($("region").value);tract=-1;$("tract").value="-1";later();};''')
swap(''' $("tract").onchange=()=>{tract=Number($("tract").value);if(tract>=0){selected=-1;$("region").value="-1";}later();};''',
''' $("tract").onchange=()=>{focusedGraph=null;tract=Number($("tract").value);if(tract>=0){selected=-1;$("region").value="-1";}later();};''')
swap(''' $("linkOn").onclick=()=>{links=true;$("linkOn").setAttribute("aria-pressed","true");$("linkOff").setAttribute("aria-pressed","false");later();};''',
''' $("linkOn").onclick=()=>{focusedGraph=null;links=true;$("linkOn").setAttribute("aria-pressed","true");$("linkOff").setAttribute("aria-pressed","false");later();};
 $("neuronRunR19").onclick=selectNeuronGraph;
 $("neuronClearR19").onclick=clearGraph;''')
swap(''' dropdown();quotas=allocation(total);rebuild();
 window.ProceduralAtlasR18={''',
''' dropdown();quotas=allocation(total);rebuild();
 window.ProceduralAtlasR18={''')
swap('''  resolveNeuronId:id=>{
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
  },''',
'''  resolveNeuronId:neuronForId,
  outgoingNeuronIds:graphOutgoing,
  walkNeuronIds:traverse,
  findPath:findSyntheticPath,
  focusNeuron:id=>{
   $("sourceNeuronR19").value=String(id);
   $("targetNeuronR19").value="";
   selectNeuronGraph();
  },
  clearNeuronFocus:clearGraph,
  getGraph:()=>focusedGraph?{root:focusedGraph.root,ids:focusedGraph.ids.length,
     edges:focusedGraph.edges.length,truncated:!!focusedGraph.truncated}:null,''')
swap('''  metadata:()=>meta,
  anatomySource:"HRA/Allen CC BY 4.0",''',
'''  metadata:()=>meta,
  graphVersion:"R19 procedural directed synthetic ID connections, stable within fixed population",
  anatomySource:"HRA/Allen CC BY 4.0",''')

# R19 microscopic camera magnification, never an edit to anatomical XYZ.
swap('let yaw=.6,pitch=.18,distance=3.5,center=[0,0,0],touches=',
     'let yaw=.6,pitch=.18,distance=3.5,center=[0,0,0],graphZoom=1,touches=')
swap('uniform float uYaw,uPitch,uDistance,uAspect,uHeight;uniform vec3 uCenter;',
     'uniform float uYaw,uPitch,uDistance,uAspect,uHeight,uZoom;uniform vec3 uCenter;')
swap('uniform float uYaw,uPitch,uDistance,uAspect;uniform vec3 uCenter;',
     'uniform float uYaw,uPitch,uDistance,uAspect,uZoom;uniform vec3 uCenter;')
assert s.count('vec3 p=aPos-uCenter;float c=')==2
s=s.replace('vec3 p=aPos-uCenter;float c=', 'vec3 p=(aPos-uCenter)*uZoom;float c=')
swap('uf(p,"uAspect",w/h);uf(p,"uCenter",center);',
     'uf(p,"uAspect",w/h);uf(p,"uCenter",center);uf(p,"uZoom",graphZoom);')
swap('focusedGraph=null;center=[0,0,0];distance=3.5;',
     'focusedGraph=null;center=[0,0,0];distance=3.5;graphZoom=1;')
swap('distance=Math.max(1.5,Math.min(4,1.7+2*span));',
     'distance=3.0;graphZoom=Math.max(1,Math.min(1200,1.3/Math.max(span,.0007)));')
swap('if(focusedGraph){focusedGraph=null;$("neuronResultR19")',
     'if(focusedGraph){focusedGraph=null;graphZoom=1;$("neuronResultR19")')
swap('$("region").onchange=()=>{focusedGraph=null;',
     '$("region").onchange=()=>{focusedGraph=null;graphZoom=1;')
swap('$("tract").onchange=()=>{focusedGraph=null;',
     '$("tract").onchange=()=>{focusedGraph=null;graphZoom=1;')
swap('$("reset").onclick=()=>{yaw=.6;pitch=.18;distance=3.5;center=[0,0,0];dirty=true;};',
     '$("reset").onclick=()=>{yaw=.6;pitch=.18;distance=3.5;center=[0,0,0];graphZoom=1;dirty=true;};')
swap('  getGraph:()=>focusedGraph?{root:focusedGraph.root,ids:focusedGraph.ids.length,',
     '  getGraph:()=>focusedGraph?{zoom:graphZoom,root:focusedGraph.root,ids:focusedGraph.ids.length,')

# Keep externally exposed ID-addressing correct immediately after changing N.
swap('total=n;$("target").value=String(n);\n if(focusedGraph)',
     'total=n;$("target").value=String(n);quotas=allocation(n);rebuildRanges();\n if(focusedGraph)')

dest=P/'docs/procedural/procedural_r19.js'
dest.write_text(s)
h=(P/'docs/procedural/index.html').read_text()
if 'procedural_r18.js' in h:
    h=h.replace('procedural_r18.js','procedural_r19.js')
else:
    assert 'procedural_r19.js' in h
h=h.replace('<title>HQ500M R18 · Procedural Neural Atlas</title>','<title>HQ500M R19 · Procedural Neural Atlas + ID Graph</title>')
h=h.replace('R18 · 283 HRA','R19 · 283 HRA')
h=h.replace('id="neuralPathExplorer"', 'id="neuralPathExplorer"')
needle='<span class="mini">Режим проводящих трактов</span>'
assert h.count(needle)==1
panel='''<h3>Neural Path Explorer · ID граф</h3>
<label class="mini" for="sourceNeuronR19">Neuron ID от 0 до N−1</label>
<input id="sourceNeuronR19" type="number" value="42" min="0" step="1" placeholder="Например, 42">
<label class="mini" for="targetNeuronR19">Целевой ID (необязательно)</label>
<input id="targetNeuronR19" type="number" min="0" step="1" placeholder="Пусто = исходящие связи">
<label class="mini" for="graphDepthR19">Глубина направленного обхода</label>
<select id="graphDepthR19"><option value="1">1</option><option value="2" selected>2</option><option value="3">3</option><option value="4">4</option></select>
<div class="row" style="margin-top:8px"><button id="neuronRunR19" class="main">Показать нейрон и связи</button><button id="neuronClearR19">Очистить</button></div>
<div id="neuronResultR19" role="status" style="margin:8px 0;font-size:10px;color:#ffb9cb;line-height:1.45;overflow-wrap:anywhere">ID адресуются процедурно. Вершины и направленные связи не хранятся заранее.</div>
<p class="note">Структурный граф строго <strong>синтетический</strong>: локальные связи и редкие пространственные проекции между соседними HRA-областями, без биологических синаптических данных. Смена общего количества перенумеровывает глобальные ID.</p>
'''
if 'id="neuronRunR19"' not in h:
    h=h.replace(needle,panel+needle)
h=h.replace('синтетическая визуализация, не измеренный коннектом',
'''синтетический процедурный граф, не измеренный коннектом''')
(P/'docs/procedural/index.html').write_text(h)
print('R19 built',len(s),'JS bytes')
