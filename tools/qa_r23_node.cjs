"use strict";
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),queued=[];
const defaults={lod:"800000",lodMode:"auto",target:"500000000",region:"-1",tract:"-1",background:"dim",
                 graphDepthR19:"2",sourceNeuronR19:"42",targetNeuronR19:""};
const elements={};
let instanceDraws=0;
const gl=new Proxy({}, {get:(obj,k)=>{
 if (typeof k==='string'&&k.toUpperCase()===k) return k;
 if(k==='createShader'||k==='createProgram'||k==='createVertexArray'||k==='createBuffer')return ()=>({});
 if(k==='getShaderParameter'||k==='getProgramParameter')return ()=>true;
 if(k==='getUniformLocation')return ()=>0;
 if(k==='drawArraysInstanced')return (mode,first,vert,count)=>{instanceDraws++;if(vert!==3||count<1)throw Error('Bad instanced fiber');};
 return ()=>{};
}});
function elem(id){
 if(elements[id])return elements[id];
 const e={value:defaults[id]??'',checked:id==='occludeBack',
       textContent:'',innerHTML:'',style:{},options:[],clientWidth:1460,clientHeight:890,
       width:1460,height:890,
       getContext:()=>gl,
       setAttribute(){},addEventListener(){},setPointerCapture(){},classList:{add(){},toggle(){return false}},
       replaceChildren(...items){this.options=items;},
       add(item){this.options.push(item);}};
 return elements[id]=e;
}
const sandbox={
 document:{getElementById:elem},window:{addEventListener(){}},
 Option:function(label,value){return {label,value};},
 devicePixelRatio:1,matchMedia:()=>({matches:false}),
 requestAnimationFrame(fn){queued.push(fn);return queued.length;},
 console,URL,Blob,Response,DecompressionStream,DataView,Uint8Array,Float32Array,Uint16Array,Uint32Array,Float64Array,
 setTimeout,clearTimeout,
 fetch:async uri=>{
   const file=path.resolve(root,'docs/procedural',uri);
   const payload=fs.readFileSync(file);
   return new Response(payload,{status:200});
 }
};
async function main(){
 vm.createContext(sandbox);
 const js=fs.readFileSync(path.resolve(root,'docs/procedural/procedural_r23.js'),'utf8');
 vm.runInContext(js,sandbox,{filename:'procedural_r23.js',timeout:60000});
 for(let i=0;i<100;i++){if(sandbox.window.ProceduralAtlasR18)break;await new Promise(r=>setTimeout(r,100));}
 const A=sandbox.window.ProceduralAtlasR18;
 if(!A)throw Error('Atlas did not initialize: '+elem('status').textContent);
 const s0=A.getStats();
 if(s0.shown!==220000||s0.surfaceFiberEdges<50000)throw Error('Initial dense mode mismatch '+JSON.stringify(s0));
 console.log('INITIAL',JSON.stringify(s0));
 const click=(id)=>{elem(id).onclick();const jobs=queued.splice(0);for(const job of jobs){if(job.name==='frame')queued.push(job);else job();}};
 click('linkOff');
 if(A.getStats().surfaceFiberEdges!==0)throw Error('Connections did not disable');
 click('linkOn');
 const s1=A.getStats();
 console.log('LINKS ON',JSON.stringify(s1));
 if(s1.surfaceFiberEdges<50000||s1.segments!==0)throw Error('Dense mode error '+JSON.stringify(s1));
 // Simulate a render pass to confirm instanced pipeline selection.
 const frames=queued.splice(0).filter(fn=>fn.name==='frame');
 if(frames.length)frames[0]();
 if(instanceDraws<1)throw Error('Instanced draw path did not execute');
 click('linkOff');
 if(A.getStats().surfaceFiberEdges!==0)throw Error('Connections did not disable');
 A.setRegion(111);
 for(const j of queued.splice(0).filter(fn=>fn.name!=='frame'))j();
 if(A.getStats().selected!==111||A.getStats().surfaceFiberEdges!==0)throw Error('Region isolation regressed');
 console.log('REGION',JSON.stringify(A.getStats()));
 A.setRegion(-1);
 for(const j of queued.splice(0).filter(fn=>fn.name!=='frame'))j();
 click('linkOn');
 A.setTotal(86100000000);
 for(const j of queued.splice(0).filter(fn=>fn.name!=='frame'))j();
 const huge=A.getStats();
 console.log('86.1B AUTO',JSON.stringify(huge));
 if(huge.shown!==682889||huge.surfaceFiberEdges<500000)throw Error('High-scale failure '+JSON.stringify(huge));
 elem('lodMode').value='manual';elem('lod').value='1100000';elem('lodMode').onchange();
 for(const j of queued.splice(0).filter(fn=>fn.name!=='frame'))j();
 const max=A.getStats();
 console.log('86.1B MAX',JSON.stringify(max));
 if(max.shown!==1100000||max.surfaceFiberEdges<800000)throw Error('Manual high-density failure '+JSON.stringify(max));
 console.log('PASS R23 Node CPU/mock WebGL logic (not real GPU shader compilation)');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
