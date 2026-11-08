from playwright.sync_api import sync_playwright
from pathlib import Path
import json
CHROME='/home/mirbi/.cache/ai3d-lab/playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'
URL='http://127.0.0.1:48999/procedural/'
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=CHROME,args=[
   '--no-sandbox','--disable-dev-shm-usage','--disable-gpu-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
 page=b.new_page(viewport={'width':1450,'height':850},device_scale_factor=1)
 page.on('pageerror',lambda err:errors.append('pageerror: '+str(err)))
 page.on('console',lambda msg:errors.append('console: '+msg.text) if msg.type=='error' else None)
 page.goto(URL,wait_until='domcontentloaded',timeout=20000)
 page.wait_for_function('window.ProceduralAtlasR18&&window.ProceduralAtlasR18.getStats().shown>=220000',timeout=30000)
 page.locator('#linkOn').click()
 page.wait_for_function('window.ProceduralAtlasR18.getStats().segments>0',timeout=35000)
 a=page.evaluate('window.ProceduralAtlasR18.getStats()')
 print('500M LOCAL FIBERS',json.dumps(a),flush=True)
 assert a['allocated']==500000000 and a['shown']==220000 and a['segments']>0 and a['segments']<5000
 page.screenshot(path='/home/mirbi/projects/hq500m-procedural-r21/docs/images/r21_local_fibers.png',timeout=30000)
 page.locator('#preset861').click()
 page.wait_for_function('window.ProceduralAtlasR18.getStats().allocated===86100000000',timeout=40000)
 page.wait_for_function('window.ProceduralAtlasR18.getStats().shown>=680000',timeout=40000)
 x=page.evaluate('window.ProceduralAtlasR18.getStats()')
 print('86B LOCAL FIBERS',json.dumps(x),flush=True)
 assert 0<x['segments']<5000 and x['shown']==682889
 page.locator('#background').select_option('hide')
 page.locator('#sourceNeuronR19').fill('42')
 page.locator('#neuronRunR19').click()
 page.wait_for_function('window.ProceduralAtlasR18.getGraph()&&window.ProceduralAtlasR18.getStats().shown<200',timeout=30000)
 y=page.evaluate('({g:window.ProceduralAtlasR18.getGraph(),s:window.ProceduralAtlasR18.getStats()})')
 print('ISOLATED GRAPH',json.dumps(y),flush=True)
 assert y['s']['segments']==y['g']['edges'] and y['s']['shown']==y['g']['ids']
 page.locator('#neuronClearR19').click()
 page.locator('#tract').select_option('49')
 page.wait_for_function('window.ProceduralAtlasR18.getStats().segments>0',timeout=18000)
 z=page.evaluate('window.ProceduralAtlasR18.getStats()')
 print('TRACT',json.dumps(z),flush=True)
 assert z['segments']>0
 print('ERRORS',json.dumps(errors[:8],ensure_ascii=False),flush=True)
 assert not errors
 b.close()
