#!/usr/bin/env python3
"""R22 WebGL2 depth-only surface mask, toggled on/off + graph/region preservation."""
from playwright.sync_api import sync_playwright
import json,time
from PIL import Image
CHROME='/home/mirbi/.cache/ai3d-lab/playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'
BASE='http://127.0.0.1:48999/procedural/'
errors=[]
with sync_playwright() as playwright:
 b=playwright.chromium.launch(executable_path=CHROME,headless=True,args=[
 '--no-sandbox','--disable-dev-shm-usage','--disable-gpu-sandbox',
 '--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
 page=b.new_page(viewport={'width':1460,'height':890},device_scale_factor=1)
 page.on('pageerror',lambda exc:errors.append('pageerror:'+str(exc)))
 page.on('console',lambda msg:errors.append('console:'+msg.text) if msg.type=='error' else None)
 page.goto(BASE,wait_until='domcontentloaded',timeout=20000)
 page.wait_for_function('window.ProceduralAtlasR18&&window.ProceduralAtlasR18.getStats().shown>=220000',timeout=50000)
 page.wait_for_function('window.ProceduralAtlasR18.getVisibility().active===true',timeout=18000)
 initial=page.evaluate('({stat:window.ProceduralAtlasR18.getStats(),mask:window.ProceduralAtlasR18.getVisibility()})')
 assert initial['stat']['total']==500000000 and initial['mask']['sourceSurfaceStencil']>=40000
 assert initial['mask']['registeredToHRA'] and initial['mask']['hidesFragmentsNotVertices']
 assert initial['mask']['sourceHraTriangles']==656268
 assert initial['mask']['eligibleHraTriangles']>10000
 print('500M DEPTH MASK',json.dumps(initial),flush=True)
 page.locator('#linkOn').click()
 page.wait_for_function('window.ProceduralAtlasR18.getStats().segments>0',timeout=18000)
 page.screenshot(path='/home/mirbi/projects/hq500m-procedural-r22/docs/images/r22_occluded_default.png')
 page.locator('#occludeBack').uncheck()
 page.wait_for_function('window.ProceduralAtlasR18.getVisibility().active===false',timeout=18000)
 page.screenshot(path='/home/mirbi/projects/hq500m-procedural-r22/docs/images/r22_unoccluded_comparison.png')
 page.locator('#occludeBack').check()
 page.wait_for_function('window.ProceduralAtlasR18.getVisibility().active===true',timeout=18000)
 startTriangles=page.evaluate('window.ProceduralAtlasR18.getVisibility().eligibleHraTriangles')
 page.mouse.move(710,420)
 page.mouse.down()
 page.mouse.move(915,484,steps=8)
 page.mouse.up()
 page.wait_for_function('(n)=>window.ProceduralAtlasR18.getVisibility().eligibleHraTriangles!==n',arg=startTriangles,timeout=35000)
 rotated=page.evaluate('window.ProceduralAtlasR18.getVisibility()')
 print('ROTATED',startTriangles,'->',rotated['eligibleHraTriangles'],flush=True)
 assert rotated['active'] and rotated['eligibleHraTriangles']>10000
 page.locator('#preset861').click()
 page.wait_for_function('window.ProceduralAtlasR18.getStats().allocated===86100000000',timeout=30000)
 page.wait_for_function('window.ProceduralAtlasR18.getStats().shown===682889',timeout=30000)
 print('86B MASK',json.dumps(page.evaluate('window.ProceduralAtlasR18.getVisibility()')),flush=True)
 page.locator('#lodMode').select_option('manual')
 page.locator('#lod').fill('1100000')
 page.wait_for_function('window.ProceduralAtlasR18.getStats().shown===1100000',timeout=45000)
 page.screenshot(path='/home/mirbi/projects/hq500m-procedural-r22/docs/images/r22_occluded_dense.png',timeout=45000)
 assert page.evaluate('window.ProceduralAtlasR18.getVisibility().active')
 page.locator('#regionSearch').fill('lateral_hemisphere_of_cerebellum_L')
 page.locator('#region').select_option('111')
 page.wait_for_function('window.ProceduralAtlasR18.getStats().selected===111',timeout=15000)
 page.wait_for_function('window.ProceduralAtlasR18.getVisibility().active===false',timeout=8000)
 print('SELECTED REGION NO MASK',page.evaluate('window.ProceduralAtlasR18.getVisibility()'),flush=True)
 page.locator('#regionSearch').fill('')
 page.locator('#region').select_option('-1')
 page.locator('#sourceNeuronR19').fill('42')
 page.locator('#background').select_option('hide')
 page.locator('#neuronRunR19').click()
 page.wait_for_function('window.ProceduralAtlasR18.getGraph()&&window.ProceduralAtlasR18.getStats().shown<200',timeout=20000)
 page.wait_for_function('window.ProceduralAtlasR18.getVisibility().active===false',timeout=18000)
 graph=page.evaluate('({s:window.ProceduralAtlasR18.getStats(),g:window.ProceduralAtlasR18.getGraph()})')
 assert graph['s']['segments']==graph['g']['edges']
 print('ID GRAPH NO MASK',json.dumps(graph),flush=True)
 page.locator('#neuronClearR19').click()
 page.locator('#tract').select_option('49')
 page.wait_for_function('window.ProceduralAtlasR18.getStats().segments>0',timeout=20000)
 page.wait_for_function('window.ProceduralAtlasR18.getVisibility().active===false',timeout=18000)
 print('TRACT NO MASK',json.dumps(page.evaluate('window.ProceduralAtlasR18.getStats()')),flush=True)
 mobile=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
 mobile.on('pageerror',lambda e:errors.append('mobile:'+str(e)))
 mobile.goto(BASE,wait_until='domcontentloaded',timeout=18000)
 mobile.wait_for_function('window.ProceduralAtlasR18&&window.ProceduralAtlasR18.getVisibility().active',timeout=25000)
 m=mobile.evaluate('({s:window.ProceduralAtlasR18.getStats(),m:window.ProceduralAtlasR18.getVisibility()})')
 assert m['s']['shown']==120000
 print('MOBILE MASK',json.dumps(m),flush=True)
 def count_red(path):
  im=Image.open(path).convert("RGB")
  pix=im.load()
  return sum(1 for y in range(180,700) for x in range(450,1070)
    if (lambda r,g,b:r>85 and r>g*1.42 and r>b*.94)(*pix[x,y]))
 d='/home/mirbi/projects/hq500m-procedural-r22/docs/images/'
 on=count_red(d+'r22_occluded_default.png')
 off=count_red(d+'r22_unoccluded_comparison.png')
 assert 60000<on<off,(on,off)
 print('FRONT_VISIBLE_RED_PIXELS',on,'vs all-surface',off,flush=True)
 print('ERRORS',json.dumps(errors[:12],ensure_ascii=False),flush=True)
 assert not errors
 b.close()
