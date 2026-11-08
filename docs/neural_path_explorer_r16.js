"use strict";
// Neural Path Explorer R16. All sampled fibers and Q0.8 targets are SYNTHETIC.
// Full-Morton neuronal ID-to-coordinate registration and SWC skeletons are NOT supplied.
(()=>{
const V=window.HQ500MViewer, ctl=document.getElementById("control");
if(!V||!ctl){console.error("Neural Path Explorer: missing R16 viewer bridge");return;}
const REG=["Лобная","Теменная","Височная","Затылочная","Мозжечковая","Стволовая","Глубинные структуры","Островковая"];
const card=document.createElement("section");
card.id="neuralPathExplorer";
card.style.cssText="border-top:1px solid #513240;padding-top:13px;margin-top:15px;font-size:11px;line-height:1.45";
const opts=REG.map((name,i)=>'<option value="'+i+'">'+name+'</option>').join("");
card.innerHTML=
'<div style="font-size:13px;font-weight:800;color:#ff4161;margin-bottom:7px">Neural Path Explorer · R16</div>'+
'<div class="mini">Режим исследования</div><select id="npeMode"><option value="id">По ID нейронов Q0.8</option><option value="regions">По двум пространственным зонам</option></select>'+
'<div id="npeIdControls"><div class="mini">Исходный Neuron ID (0–499 999 999)</div><input id="npeSourceId" type="number" min="0" max="499999999" step="1" value="42" style="width:100%;background:#231a20;color:#fff;border:1px solid #5c3441;padding:7px;border-radius:7px;margin:6px 0">'+
'<div class="mini">Целевой Neuron ID · необязательно</div><input id="npeTargetId" type="number" min="0" max="499999999" step="1" placeholder="Пусто = показать 32 исходящих" style="width:100%;background:#231a20;color:#fff;border:1px solid #5c3441;padding:7px;border-radius:7px;margin:6px 0">'+
'<div class="mini">Глубина · направленные исходящие связи</div><select id="npeDepth"><option value="1">1 переход</option><option value="2">2 перехода</option><option value="3" selected>3 перехода</option><option value="4">4 перехода</option></select></div>'+
'<div id="npeRegionControls" hidden><div class="mini">Исходная условная зона</div><select id="npeRegionFrom">'+opts+'</select>'+
'<div class="mini">Целевая условная зона</div><select id="npeRegionTo">'+opts+'</select>'+
'<div style="font-size:10px;color:#bda9b3;margin:5px 0">Показываются сегменты R11. Переходы между зонами не доказывают непрерывный нейронный тракт.</div></div>'+
'<div class="mini">Остальная модель</div><select id="npeContext"><option value="hide" selected>Скрыть</option><option value="dim">Затемнить контекст</option><option value="all">Показать полностью</option></select>'+
'<div class="gap"><button class="primary" id="npeRun">Найти / выделить</button><button id="npeClear">Очистить</button></div>'+
'<div id="npeResult" role="status" aria-live="polite" style="font-size:10px;line-height:1.5;color:#f3b9c2;margin:7px 0;overflow-wrap:anywhere">Поиск пока не запущен.</div>'+
'<div style="font-size:9px;color:#a594a0">Важно: ID-граф действительно вычисляется по алгоритму Q0.8, но отображаемые координаты ID пока только стабильные пространственные прокси. Реконструированных аксонов, отдельных синапсов, карты 86 млрд и подтверждённых анатомических трактов здесь нет.</div>';
ctl.appendChild(card);
const $=id=>document.getElementById(id), result=$("npeResult");
const mod=$("npeMode"),from=$("npeRegionFrom"),to=$("npeRegionTo");
from.value="0";to.value="4";
mod.onchange=()=>{$("npeIdControls").hidden=mod.value!=="id";$("npeRegionControls").hidden=mod.value!=="regions";};
const N=500000000n,MASK=(1n<<64n)-1n,K=0x517cc1b727220a95n;
const REGIONS=[0n,224999424n,294999040n,344999936n,394999808n,434999296n,469999616n,N];
const ROUTES=[3,5,0,0,3,1,2];
function mix(n){
 let x=(n+0x9e3779b97f4a7c15n)&MASK;
 x=((x^(x>>30n))*0xbf58476d1ce4e5b9n)&MASK;
 x=((x^(x>>27n))*0x94d049bb133111ebn)&MASK;
 return (x^(x>>31n))&MASK;
}
function targetOf(src,slot){
 if(src<0n||src>=N||slot<0||slot>=32||!Number.isInteger(slot))throw Error("ID/slot out of range");
 let region=0;for(let r=0;r<7;r++)if(src>=REGIONS[r])region=r;
 const h0=mix(src^37421n),h=mix(h0^((BigInt(slot+1)*K)&MASK));
 if(slot<24){
   const st=(src/1024n)*1024n;
   const odd=((h0>>11n)&0xffffffffn)|1n;
   const count=st+1024n>N?N-st:1024n;
   return st+((src-st+(BigInt(slot+1)*odd)&0xffffffffn)%count);
 }
 const rr=ROUTES[region],st=REGIONS[rr],end=REGIONS[rr+1];
 const modules=(end-st+1023n)/1024n;
 const mb=st+(mix(h^(src/1024n))%modules)*1024n;
 const available=mb+1024n>end?end-mb:1024n;
 return mb+((h>>24n)%available);
}
function outgoing(id){const a=[];for(let slot=0;slot<32;slot++)a.push(targetOf(id,slot));return a;}
function parseId(v,optional=false){
 if(!v.trim()&&optional)return null;
 if(!/^\d+$/.test(v.trim()))throw Error("Neuron ID должен быть целым числом");
 const id=BigInt(v.trim());if(id<0n||id>=N)throw Error("Neuron ID вне диапазона Q0.8");
 return id;
}
function pathfind(a,b,depth=3,limit=4096){
 if(a===b)return {ids:[a],visited:1,truncated:false};
 const visited=new Set([a]),parent=new Map();
 const queue=[[a,0]],maxD=Math.min(4,Math.max(1,depth));
 let head=0,found=false;
 while(head<queue.length&&!found){
   const [v,d]=queue[head++];
   if(d>=maxD)continue;
   for(let slot=0;slot<32;slot++){
     const w=targetOf(v,slot);
     if(visited.has(w))continue;
     visited.add(w);parent.set(w,v);
     if(w===b){found=true;break;}
     if(visited.size>=limit)break;
     queue.push([w,d+1]);
   }
   if(visited.size>=limit)break;
 }
 if(!found)return {ids:[],visited:visited.size,truncated:visited.size>=limit};
 let cursor=b,ids=[b];
 while(cursor!==a){cursor=parent.get(cursor);if(cursor===undefined)throw Error("Broken BFS predecessor");ids.push(cursor);}
 ids.reverse();
 return {ids,visited:visited.size,truncated:false};
}
function renderIds(chain,neighborhood=false){
 const pairs=[];
 if(neighborhood){for(const to of outgoing(chain[0]))pairs.push([chain[0],to]);}
 else for(let i=1;i<chain.length;i++)pairs.push([chain[i-1],chain[i]]);
 if(!pairs.length)return 0;
 const bytes=new Uint8Array(pairs.length*12),out=new DataView(bytes.buffer);
 for(let i=0;i<pairs.length;i++){
   const a=V.proxyPosition(pairs[i][0]),b=V.proxyPosition(pairs[i][1]);
   if(!a||!b)throw Error("Позиции ещё не загружены");
   for(let j=0;j<3;j++){out.setUint16(i*12+j*2,a[j],true);out.setUint16(i*12+6+j*2,b[j],true);}
 }
 return V.setExplorer(bytes,$("npeContext").value,true);
}
function showIds(){
 if(!V.ready())throw Error("Сначала дождись загрузки геометрии и волокон");
 const a=parseId($("npeSourceId").value),b=parseId($("npeTargetId").value,true);
 if(b===null){
   const count=renderIds([a],true);
   result.textContent="Neuron "+a+" → "+count+" направленных Q0.8 соседей. Координаты являются прокси, а не точным отображением R11.";
   return;
 }
 const res=pathfind(a,b,Number($("npeDepth").value),4096);
 if(!res.ids.length){
   V.clearExplorer();
   result.textContent="Путь не найден в ограниченном обходе: "+res.visited+" посещённых ID"+(res.truncated?", достигнут лимит 4096":", в заданной глубине")+". Отсутствие пути не доказано.";
   return;
 }
 const edges=renderIds(res.ids);
 result.textContent=edges+" переход(ов), "+res.visited+" посещённых ID: "+res.ids.map(x=>x.toString()).join(" → ")+". Координаты схематические; путь Q0.8 синтетический.";
}
let endpointRegions=null;
async function getRegions(){
 if(endpointRegions)return endpointRegions;
 const response=await fetch("./assets/hq500m_fiber_regions_r16.bin.gz",{cache:"force-cache"});
 if(!response.ok)throw Error("Не загружен индекс зон R11: HTTP "+response.status);
 const raw=await new Response(response.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
 const view=new DataView(raw);
 if(view.getUint32(0,true)!==0x36455148)throw Error("Неверный формат HQE6");
 const c=view.getUint32(4,true)+view.getUint32(8,true);
 if(raw.byteLength!==12+4*c)throw Error("Повреждён индекс HQE6");
 const fibers=V.getEdges();
 if(!fibers||fibers.byteLength!==c*12)throw Error("Индекс и реальные волокна имеют разный размер");
 endpointRegions=new Uint8Array(raw,12);
 return endpointRegions;
}
function regionalRoute(src,dst,meta){
 const counts=new Uint32Array(64);
 for(let i=0;i<meta.byteLength;i+=4)counts[meta[i]*8+meta[i+1]]++;
 const queue=[[src]],used=new Set([src]);
 while(queue.length){
   const path=queue.shift(),a=path[path.length-1];
   if(a===dst)return {path,counts};
   for(let b=0;b<8;b++){
     if(!used.has(b)&&counts[a*8+b]>0){
       used.add(b);queue.push([...path,b]);
     }
   }
 }
 return {path:[],counts};
}
async function showRegional(){
 if(!V.ready())throw Error("Сначала дождись загрузки облака и R11 волокон");
 const source=Number(from.value),target=Number(to.value);
 const regions=await getRegions(),fibers=V.getEdges();
 const {path,counts}=regionalRoute(source,target,regions);
 if(!path.length)throw Error("Нет даже условного межрегионального маршрута по доступным сегментам");
 const desired=new Set();
 if(path.length===1)desired.add(source*8+source);
 for(let i=1;i<path.length;i++)desired.add(path[i-1]*8+path[i]);
 let matched=0;
 for(let i=0;i<regions.length;i+=4)if(desired.has(regions[i]*8+regions[i+1]))matched++;
 if(!matched)throw Error("Региональные сегменты не найдены");
 const mobile=matchMedia("(max-width:760px), (pointer:coarse)").matches;
 const cap=mobile?2800:8000;
 const step=Math.max(1,Math.ceil(matched/cap));
 const out=new Uint8Array(Math.ceil(matched/step)*12);
 let kept=0,seen=0;
 for(let i=0;i<regions.length;i+=4){
   if(!desired.has(regions[i]*8+regions[i+1]))continue;
   if(seen%step===0){out.set(fibers.subarray((i/4)*12,(i/4)*12+12),kept*12);kept++;}
   seen++;
 }
 V.setExplorer(out.subarray(0,kept*12),$("npeContext").value,true);
 const labels=path.map(i=>REG[i]).join(" → ");
 result.textContent=labels+": показано "+kept+" из "+matched+" вычисленных сегментов Q0.8. Это маршрут по агрегированным кандидатным зонам, НЕ доказанная последовательность нейронов или аксонный тракт.";
}
$("npeRun").onclick=async()=>{
 $("npeRun").disabled=true;result.textContent="Вычисление…";
 try{if(mod.value==="id")showIds();else await showRegional();}
 catch(e){result.textContent="Ошибка: "+e.message;console.error(e);}
 finally{$("npeRun").disabled=false;}
};
$("npeClear").onclick=()=>{
 V.clearExplorer();result.textContent="Выделение снято, полный мозг снова виден.";
};
window.HQ500MNeuralPath={
  targetOf,pathfind,regionalRoute,
  graph_kind:"synthetic_Q08_outgoing_only",
  coordinates:"visual_proxies_for_ID_search",
  atlas_verified:false
};
})();
