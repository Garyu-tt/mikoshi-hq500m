#!/usr/bin/env python3
"""R20 dense point-cloud: test desktop/mobile WebGL, counts, manual cap & synthetic ID invariants."""
from playwright.sync_api import sync_playwright
import json, time
CHROME='/home/mirbi/.cache/ai3d-lab/playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64'
URL='http://127.0.0.1:48999/procedural/'
errs=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=CHROME+'/chrome-headless-shell',
   headless=True,args=['--no-sandbox','--disable-dev-shm-usage',
    '--disable-gpu-sandbox','--enable-unsafe-swiftshader',
    '--use-gl=angle','--use-angle=swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
 page.on('pageerror',lambda e:errs.append("PAGE: "+str(e)))
 page.on('console',lambda m:errs.append("CONSOLE: "+m.text) if m.type=='error' else None)
 t0=time.monotonic()
 page.goto(URL,wait_until='domcontentloaded',timeout=30000)
 page.wait_for_function("window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown>0",timeout=80000)
 base=page.evaluate("({s:window.ProceduralAtlasR18.getStats(),lod:window.ProceduralAtlasR18.getLOD(),id:window.ProceduralAtlasR18.resolveNeuronId(42),neighbors:window.ProceduralAtlasR18.outgoingNeuronIds(42)})")
 assert base['s']['total']==500000000 and base['s']['shown']==220000,base
 assert base['lod']['mode']=='auto' and base['s']['allocated']==500000000
 print("500M AUTO",json.dumps(base['s']),"seconds",round(time.monotonic()-t0,2),flush=True)
 page.locator('#preset861').click()
 page.wait_for_function("window.ProceduralAtlasR18.getStats().allocated===86100000000 && window.ProceduralAtlasR18.getStats().shown>600000",timeout=90000)
 big=page.evaluate("({s:window.ProceduralAtlasR18.getStats(),lod:window.ProceduralAtlasR18.getLOD()})")
 assert 600000<=big['s']['shown']<=800000,big
 assert big['lod']['mode']=='auto'
 page.wait_for_timeout(500)
 page.screenshot(path='/home/mirbi/projects/hq500m-procedural-r19/docs/images/r20_dense_861b.png',timeout=90000)
 print("86.1B AUTO",json.dumps(big),flush=True)
 # Manual mode must be able to increase detail ABOVE automatic target.
 page.locator('#lodMode').select_option('manual')
 page.locator('#lod').fill('1100000')
 page.wait_for_function("window.ProceduralAtlasR18.getStats().shown===1100000",timeout=90000)
 cap=page.evaluate("({s:window.ProceduralAtlasR18.getStats(),lod:window.ProceduralAtlasR18.getLOD()})")
 assert cap['s']['allocated']==86100000000 and cap['lod']['mode']=='manual',cap
 print("MANUAL MAX",json.dumps(cap),flush=True)
 # Focused path must render only its chosen nodes even at 1.1m slider.
 page.locator('#sourceNeuronR19').fill('42')
 page.locator('#background').select_option('hide')
 page.locator('#neuronRunR19').click()
 page.wait_for_function("window.ProceduralAtlasR18.getGraph() && window.ProceduralAtlasR18.getStats().shown<200",timeout=25000)
 graph=page.evaluate("({graph:window.ProceduralAtlasR18.getGraph(),s:window.ProceduralAtlasR18.getStats()})")
 assert graph['graph']['edges']>0 and graph['s']['shown']==graph['graph']['ids'],graph
 print("FOCUSED GRAPH AT 1.1M LOD",json.dumps(graph),flush=True)
 page.locator('#neuronClearR19').click()
 page.wait_for_function("window.ProceduralAtlasR18.getGraph()===null",timeout=18000)
 # Changing LOD must not change virtual ID position or graph, at a fixed N.
 page.locator('#preset500').click()
 page.wait_for_function("window.ProceduralAtlasR18.getStats().allocated===500000000",timeout=65000)
 x=page.evaluate("({id:window.ProceduralAtlasR18.resolveNeuronId(42),neighbors:window.ProceduralAtlasR18.outgoingNeuronIds(42)})")
 assert x=={'id':base['id'],'neighbors':base['neighbors']}
 print("ID LOD INVARIANCE PASS",flush=True)
 mob=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
 mob.on('pageerror',lambda e:errs.append("MOBILE: "+str(e)))
 mob.goto(URL,wait_until='domcontentloaded',timeout=30000)
 mob.wait_for_function("window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown>0",timeout=65000)
 m1=mob.evaluate("({s:window.ProceduralAtlasR18.getStats(),lod:window.ProceduralAtlasR18.getLOD()})")
 assert m1['s']['shown']==120000 and m1['lod']['platformCap']==120000,m1
 mob.locator('#togglePanel').click()
 mob.locator('#lodMode').select_option('manual')
 mob.locator('#lod').fill('1100000')
 mob.wait_for_timeout(500)
 m2=mob.evaluate("({s:window.ProceduralAtlasR18.getStats(),lod:window.ProceduralAtlasR18.getLOD()})")
 assert m2['s']['shown']==120000,m2
 print("MOBILE CAP",json.dumps(m2),flush=True)
 print("ERRORS",json.dumps(errs[:10],ensure_ascii=False),flush=True)
 assert not errs,errs
 b.close()
