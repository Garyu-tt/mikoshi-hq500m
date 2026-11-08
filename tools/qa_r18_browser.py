#!/usr/bin/env python3
"""R18 procedural viewer end-to-end (headless SwiftShader)."""
from playwright.sync_api import sync_playwright
import json
URL='http://127.0.0.1:48998/procedural/'
CHROME='/home/mirbi/.cache/ai3d-lab/playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'
errs=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=CHROME,
   args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu-sandbox',
         '--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
 page.on('pageerror',lambda e:errs.append('PAGE: '+str(e)))
 page.on('console',lambda m:errs.append('CONSOLE: '+m.text) if m.type=='error' else None)
 page.goto(URL,wait_until='domcontentloaded',timeout=25000)
 page.wait_for_function("window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown>0",timeout=35000)
 a=page.evaluate("window.ProceduralAtlasR18.getStats()")
 assert a['total']==500000000 and a['allocated']==500000000 and a['regions']==283 and a['templateRecords']==188495,a
 print('DEFAULT',json.dumps(a),flush=True)
 page.locator('#preset861').click()
 page.wait_for_function("window.ProceduralAtlasR18.getStats().total===86100000000",timeout=18000)
 full=page.evaluate("window.ProceduralAtlasR18.getStats()")
 assert full['shown']>a['shown'] and full['allocated']==86100000000,(a,full)
 print('86B',json.dumps(full),flush=True)
 page.screenshot(path='/home/mirbi/projects/hq500m-scaling-r18/docs/images/r18_procedural_smoke.png')
 page.locator('#regionSearch').fill('lateral_hemisphere_of_cerebellum_L')
 page.locator('#region').select_option('111')
 page.wait_for_function("window.ProceduralAtlasR18.getStats().selected===111",timeout=10000)
 selected=page.evaluate("window.ProceduralAtlasR18.getStats()")
 q=page.evaluate("window.ProceduralAtlasR18.getQuota(111)")
 assert q>0 and selected['shown']>0
 print('SELECT_REGION',q,json.dumps(selected),flush=True)
 page.locator('#regionSearch').fill('')
 page.locator('#tract').select_option('49')
 page.wait_for_function("window.ProceduralAtlasR18.getStats().tract===49",timeout=11000)
 traced=page.evaluate("window.ProceduralAtlasR18.getStats()")
 assert traced['segments']>0 and page.evaluate("window.ProceduralAtlasR18.getQuota(49)") == 0,traced
 print('TRACT',json.dumps(traced),flush=True)
 page.screenshot(path='/home/mirbi/projects/hq500m-scaling-r18/docs/images/r18_tract_smoke.png')
 page.locator('#preset500').click()
 page.wait_for_function("window.ProceduralAtlasR18.getStats().total===500000000",timeout=11000)
 mobile=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
 mobile.on('pageerror',lambda e:errs.append('MOBILE: '+str(e)))
 mobile.goto(URL,wait_until='domcontentloaded',timeout=25000)
 mobile.wait_for_function("window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown>0",timeout=30000)
 mobile.locator('#togglePanel').click()
 assert mobile.locator('#panel').is_visible()
 print('MOBILE',json.dumps(mobile.evaluate("window.ProceduralAtlasR18.getStats()")),flush=True)
 print('ERRORS',json.dumps(errs[:12],ensure_ascii=False),flush=True)
 assert not errs,errs
 b.close()
