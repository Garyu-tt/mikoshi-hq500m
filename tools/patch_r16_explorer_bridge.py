#!/usr/bin/env python3
"""Inject private viewer bridge for static-page Neural Path Explorer."""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
p=P/'docs/viewer_r16.js'
s=p.read_text()
def one(a,b):
    global s
    assert s.count(a)==1, (s.count(a),a[:95])
    s=s.replace(a,b)
one('let numPoints=0,cerebCount=0,localEdges=0,globalEdges=0,pointData=null,cerebData=null,lineData=null,pp,lp,loaded=false;',
'''let numPoints=0,cerebCount=0,localEdges=0,globalEdges=0,pointData=null,cerebData=null,lineData=null,pp,lp,loaded=false;
let originalPointBytes=null,originalLineBytes=null,explorerData=null,explorerEdges=0;
let explorerBackground="all",camCenter=[0,0,0];''')
one('uniform("uTime",t/1000,p);}',
'''uniform("uTime",t/1000,p);
uniform("uCenterX",camCenter[0],p);uniform("uCenterY",camCenter[1],p);uniform("uCenterZ",camCenter[2],p);}''')
one('const source=new Uint8Array(data,8), regions=new Uint8Array(ann,8), weights=new Uint8Array(soft,8);',
'''const source=new Uint8Array(data,8), regions=new Uint8Array(ann,8), weights=new Uint8Array(soft,8);
originalPointBytes=source;''')
one('lineData=lineGeometry(new Uint8Array(data,12));loaded=true;',
'''originalLineBytes=new Uint8Array(data,12);
lineData=lineGeometry(originalLineBytes);loaded=true;''')
one('uniform("uSize",mobile?1.18:1.31,pp);',
    'uniform("uContextFade",explorerBackground==="dim"?.16:1.0,pp);uniform("uSize",mobile?1.18:1.31,pp);')
one('scene(pp,time);uniform("uContextFade",',
    'scene(pp,time);uniform("uContextFade",') # asserts existence
one('gl.bindVertexArray(pointData.vao);gl.drawArrays(gl.POINTS,0,numPoints);',
    'if(explorerBackground!=="hide"){gl.bindVertexArray(pointData.vao);gl.drawArrays(gl.POINTS,0,numPoints);}')
one('if(cerebData&&repl>1){',
    'if(explorerBackground==="all"&&cerebData&&repl>1){')
one('if(loaded&&showEdges.checked){',
    'if(loaded&&showEdges.checked&&explorerBackground==="all"){')
one('gl.disable(gl.BLEND);gl.depthMask(true);}\ngl.bindVertexArray(null);',
'''gl.disable(gl.BLEND);gl.depthMask(true);}
if(explorerData && explorerEdges>0){
gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);gl.depthMask(false);
scene(lp,time);uniform("uLong",2,lp);uniform("uOpacity",1,lp);
gl.bindVertexArray(explorerData.vao);
gl.drawArrays(gl.LINES,0,2*explorerEdges);
gl.depthMask(true);gl.enable(gl.DEPTH_TEST);
}
gl.bindVertexArray(null);''')
one('document.getElementById("reset").onclick=()=>{yaw=.62;pitch=.12;distance=mobile?4.7:3.00;dirty=true;};',
'''document.getElementById("reset").onclick=()=>{yaw=.62;pitch=.12;distance=mobile?4.7:3.00;camCenter=[0,0,0];dirty=true;};''')
one('uniform float uYaw,uPitch,uCamera,uAspect,uHeight,uSize,uJitter,uRegionView,uScale;',
    'uniform float uYaw,uPitch,uCamera,uAspect,uHeight,uSize,uJitter,uRegionView,uScale,uCenterX,uCenterY,uCenterZ,uContextFade;')
one(' vec3 r=turn(p);',
    ' vec3 r=turn(p-vec3(uCenterX,uCenterY,uCenterZ));')
one(' if(uRegionView>.5) {',
    ' if(uRegionView>.5) {') 
one(' }\n}\n";\nconst PFS=', ' }\n vColor*=uContextFade;\n}\n";\nconst PFS=') if False else None
# R16 PVS is a JSON serialised one-line JS string; replace within quoted JS escape.
one('vColor=mix(vec3(.08,.02,.06),vec3(.39,.58,.98),', 'vColor=mix(vec3(.08,.02,.06),vec3(.39,.58,.98),')
# Shader source string is JSON escaped; append the fade before the main's last brace.
anchor=''' }
}
";
const PFS='''
if anchor in s:
    s=s.replace(anchor, ''' }
 vColor*=uContextFade;
}
";
const PFS=''',1)
else:
    # In JSON string \\n are two characters; replace just before PFS marker.
    marker='''}\\n";\nconst PFS='''
    assert marker in s, 'Cannot find shader end'
    s=s.replace(marker,''' vColor*=uContextFade;\\n}\\n";\nconst PFS=''',1)
one('uniform float uYaw,uPitch,uCamera,uAspect,uTime,uLong;',
    'uniform float uYaw,uPitch,uCamera,uAspect,uTime,uLong,uCenterX,uCenterY,uCenterZ;')
one('vec3 p=aPosition*2.0-1.0,r=turn(p);',
    'vec3 p=aPosition*2.0-1.0,r=turn(p-vec3(uCenterX,uCenterY,uCenterZ));')
one('vColor=mix(vColor,vec3(.96,.1,.25),uLong*.23);',
    'vColor=uLong>1.5?vec3(1.0,.71,.24):mix(vColor,vec3(.96,.1,.25),uLong*.23);')
bridge='''
function setExplorerGeometry(segments,background="hide",focus=true){
 if(explorerData){gl.deleteBuffer(explorerData.buffer);gl.deleteVertexArray(explorerData.vao);}
 explorerData=null;explorerEdges=0;
 if(segments){
   if(!(segments instanceof Uint8Array) || segments.byteLength%12!==0)
     throw Error("Expected Uint8Array of 6xu16 exact spatial pairs");
   if(segments.byteLength>0){explorerData=lineGeometry(segments);explorerEdges=segments.byteLength/12;}
 }
 explorerBackground=explorerEdges>0?(["dim","hide","all"].includes(background)?background:"hide"):"all";
 if(focus&&explorerEdges>0){
   const a=new DataView(segments.buffer,segments.byteOffset,segments.byteLength);
   const lo=[65535,65535,65535],hi=[0,0,0];
   for(let i=0;i<segments.byteLength;i+=6)for(let k=0;k<3;k++){
     const val=a.getUint16(i+k*2,true);
     lo[k]=Math.min(lo[k],val);hi[k]=Math.max(hi[k],val);
   }
   camCenter=lo.map((v,k)=>(v+hi[k])/65535-1);
   const span=Math.max(...lo.map((v,k)=>2*(hi[k]-v)/65535));
   distance=Math.max(1.7,Math.min(5,2+span*1.35));
 }
 if(!segments){camCenter=[0,0,0];distance=mobile?4.7:3.00;}
 dirty=true;
 return explorerEdges;
}
function viewerProxyPosition(id){
 if(!originalPointBytes||!numPoints)return null;
 // Stable DISPLAY-ONLY proxy: not HQ500M R11 true ID-to-Morton point map.
 const mask=(1n<<64n)-1n;
 let v=(BigInt(id)^0x9e3779b97f4a7c15n)&mask;
 v=((v^(v>>30n))*0xbf58476d1ce4e5b9n)&mask;
 v=((v^(v>>27n))*0x94d049bb133111ebn)&mask;
 v=(v^(v>>31n))&mask;
 const i=Number(v%BigInt(numPoints)), offset=i*8;
 const b=originalPointBytes;
 return [b[offset]|(b[offset+1]<<8),b[offset+2]|(b[offset+3]<<8),b[offset+4]|(b[offset+5]<<8)];
}
window.HQ500MViewer={
  ready:()=>!!originalPointBytes&&!!originalLineBytes,
  getEdges:()=>originalLineBytes,
  getEdgeCounts:()=>({local:localEdges,long:globalEdges}),
  proxyPosition:viewerProxyPosition,
  setExplorer:setExplorerGeometry,
  clearExplorer:()=>setExplorerGeometry(null),
  hasAtlasRegistration:false
};
'''
# insert before 'const showError...' after render() defined but before app users
assert s.count('const showError=e=>')==1
s=s.replace('const showError=e=>',bridge+'\nconst showError=e=>')
p.write_text(s)
print('Injected NPE viewer bridge',len(s))
