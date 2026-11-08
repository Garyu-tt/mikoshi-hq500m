"use strict";
// R17: HRA named regions are from NeutralLab. They do NOT label HQ500M points.
(()=>{
const ctl=document.getElementById("control");
if(!ctl)return;
const panel=document.createElement("section");
panel.id="hraReferenceR17";
panel.style.cssText="border-top:1px solid #4d3038;padding-top:12px;margin-top:13px;font-size:11px;line-height:1.5";
panel.innerHTML=
'<div style="font-size:13px;color:#ff3453;font-weight:800;margin-bottom:4px">HRA / NeutralLab · 283 структуры</div>'+
'<div style="font-size:10px;color:#b8afb6;margin-bottom:8px">Реальный анатомический атлас человеческого мозга. Это отдельная геометрия, пока не совмещённая с точками HQ500M.</div>'+
'<label class="mini" for="hraSearchR17">Поиск анатомической области</label>'+
'<input id="hraSearchR17" type="search" autocomplete="off" placeholder="cerebellar, thalamus, cortex..." style="width:100%;box-sizing:border-box;margin:6px 0;background:#1c1c1c;border:1px solid #5d3844;color:#f4e6eb;border-radius:7px;padding:8px;font:12px system-ui,sans-serif">'+
'<div id="hraCountR17" style="font-size:10px;color:#c0b2b8;margin-bottom:6px">Загружается каталог…</div>'+
'<select id="hraSelectR17" aria-label="Анатомическая структура NeutralLab" style="width:100%;margin:5px 0" disabled><option>Каталог загружается</option></select>'+
'<div id="hraDetailsR17" style="font-size:10px;line-height:1.5;color:#ccb8c0;margin:5px 0 8px"></div>'+
'<a id="hraOpenR17" href="https://neutrallab.infracare-it.com/viewer/" target="_blank" rel="noopener noreferrer" style="display:block;text-align:center;background:#aa0d29;border:1px solid #e42042;border-radius:8px;color:#fff;text-decoration:none;font-weight:700;padding:10px 6px;margin:6px 0">Открыть область в NeutralLab ↗</a>'+
'<a href="https://neutrallab.infracare-it.com/viewer/" target="_blank" rel="noopener noreferrer" style="display:block;text-align:center;color:#f5b7c4;font-size:10px;margin:8px 0">Весь анатомический атлас</a>'+
'<div style="font-size:9px;color:#a99ca6">HRA/Allen male v1.3, CC BY 4.0. 110 404 зарегистрированных V5-позиций — синтетические воксели. МРТ-привязки HQ500M к этому атласу ещё нет. Восемь цветных зон R16 — только условная схема.</div>';
ctl.appendChild(panel);
const input=document.getElementById("hraSearchR17"),select=document.getElementById("hraSelectR17");
const count=document.getElementById("hraCountR17"),details=document.getElementById("hraDetailsR17");
const open=document.getElementById("hraOpenR17");
let all=[],shown=[];
function selectRegion(){
 const r=shown[Number(select.value)];
 if(!r){details.textContent="Выберите анатомическую область";open.href="https://neutrallab.infracare-it.com/viewer/";return;}
 const side=r.group.endsWith("_left")?"левое полушарие":r.group.endsWith("_right")?"правое полушарие":r.group;
 details.textContent=r.label+" · "+side+" · V5 воксельных слотов: "+r.synthetic_V5_slots.toLocaleString("ru-RU")
   +(r.excluded_cavity?" · полость, не заполнять нейронами":"");
 const u=new URL("https://neutrallab.infracare-it.com/viewer/");
 u.searchParams.set("region",r.mesh_name);
 open.href=u.toString();
}
function update(){
 const q=input.value.trim().toLowerCase();
 const matching=all.filter(r=>(r.mesh_name+" "+r.label+" "+r.group+" "+(r.ontology||"")).toLowerCase().includes(q));
 shown=matching.slice(0,75);
 count.textContent=matching.length+" из "+all.length+" структур"+(matching.length>75?" · показаны первые 75":"");
 select.replaceChildren();
 for(let i=0;i<shown.length;i++){
   const r=shown[i],o=document.createElement("option");o.value=String(i);
   o.textContent=r.label+(r.group.endsWith("_left")?" · L":r.group.endsWith("_right")?" · R":"");
   select.appendChild(o);
 }
 select.disabled=shown.length===0;
 selectRegion();
}
input.addEventListener("input",update);
select.addEventListener("change",selectRegion);
fetch("./assets/hra_reference_catalog_r17.json",{cache:"force-cache"})
 .then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json();})
 .then(data=>{
   if(data.schema!=="HQ500M/HRA-reference-catalog/R17"||data.region_count!==283||data.hq500m_ids_mapped_to_regions!==false)
      throw Error("Неверная версия каталога");
   all=data.regions;
   input.value="cerebell";
   update();
 })
 .catch(e=>{
   count.textContent="Каталог недоступен: "+e.message;
   select.disabled=true;details.textContent="Атлас можно открыть по прямой ссылке.";
 });
})();
