#!/usr/bin/env python3
"""Browser E2E for R19 deterministic ID graph, fixed-count LOD, and tract isolation."""
from playwright.sync_api import sync_playwright
import json
CHROME='/home/mirbi/.cache/ai3d-lab/playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'
URL='http://127.0.0.1:48999/procedural/'
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=CHROME,headless=True,args=[
   '--no-sandbox','--disable-dev-shm-usage','--disable-gpu-sandbox',
   '--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
 page.goto(URL,wait_until='domcontentloaded',timeout=20000)
 page.wait_for_function('window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown>0',timeout=30000)
 api='window.ProceduralAtlasR18'
 before=page.evaluate('''() => {
   const a=window.ProceduralAtlasR18;
   return {stats:a.getStats(),neuron:a.resolveNeuronId(42),neighbors:a.outgoingNeuronIds(42)};
 }''')
 assert before['stats']['total']==500000000 and before['stats']['allocated']==500000000
 assert before['neuron']['region_id']>=0
 assert len(before['neighbors'])>=2
 print('BASE',json.dumps(before,ensure_ascii=False)[:500],flush=True)
 page.locator('#background').select_option('hide')
 page.locator('#sourceNeuronR19').fill('42')
 page.locator('#graphDepthR19').select_option('2')
 page.locator('#neuronRunR19').click()
 page.wait_for_function('window.ProceduralAtlasR18.getGraph() && window.ProceduralAtlasR18.getStats().segments>0',timeout=20000)
 graph=page.evaluate('window.ProceduralAtlasR18.getGraph()')
 stats=page.evaluate('window.ProceduralAtlasR18.getStats()')
 assert graph['root']==42 and graph['ids']<=192 and graph['edges']>0
 assert stats['shown']==graph['ids'] and stats['segments']==graph['edges'],(graph,stats)
 print('GRAPH_DEPTH2',json.dumps(graph),json.dumps(stats),flush=True)
 p2=page.evaluate('''() => {
   const a=window.ProceduralAtlasR18;return {neuron:a.resolveNeuronId(42),neighbors:a.outgoingNeuronIds(42)};
 }''')
 assert p2=={'neuron':before['neuron'],'neighbors':before['neighbors']}
 page.locator('#lod').fill('8000')
 page.wait_for_timeout(650)
 p3=page.evaluate('''() => {
   const a=window.ProceduralAtlasR18;return {neuron:a.resolveNeuronId(42),neighbors:a.outgoingNeuronIds(42)};
 }''')
 assert p3==p2
 print('GRAPH_DETERMINISM_LOD_CHANGE PASS',flush=True)
 page.locator('#graphDepthR19').select_option('3')
 page.locator('#neuronRunR19').click()
 page.wait_for_timeout(600)
 larger=page.evaluate('window.ProceduralAtlasR18.getGraph()')
 assert larger['ids']>=graph['ids']
 print('GRAPH_DEPTH3',json.dumps(larger),flush=True)
 page.screenshot(path='/home/mirbi/projects/hq500m-procedural-r19/docs/images/r19_graph_tree_demo.png')
 path_neighbor=before['neighbors'][0]
 page.locator('#targetNeuronR19').fill(str(path_neighbor))
 page.locator('#neuronRunR19').click()
 page.wait_for_timeout(500)
 direct=page.evaluate('window.ProceduralAtlasR18.getGraph()')
 assert direct['ids']==2 and direct['edges']==1,direct
 print('DIRECTED_TARGET_PATH',json.dumps(direct),flush=True)
 page.screenshot(path='/home/mirbi/projects/hq500m-procedural-r19/docs/images/r19_neuron_pair_demo.png')
 page.locator('#targetNeuronR19').fill('')
 page.locator('#preset861').click()
 page.wait_for_function('window.ProceduralAtlasR18.getStats().allocated===86100000000',timeout=11000)
 assert page.evaluate('window.ProceduralAtlasR18.getGraph()') is None
 a=page.evaluate('window.ProceduralAtlasR18.getStats()')
 assert a['allocated']==86100000000 and a['shown']>0
 print('86.1B_RESET',json.dumps(a),flush=True)
 last_id=86100000000-1
 end=page.evaluate('(id) => { const a=window.ProceduralAtlasR18; return {target:a.resolveNeuronId(id),next:a.outgoingNeuronIds(id)}; }',last_id)
 assert end['target']['id']==last_id and len(end['next'])>=1 and all(0<=x<86100000000 for x in end['next']),end
 print('86B_LAST_ID',json.dumps(end,ensure_ascii=False)[:350],flush=True)
 page.locator('#sourceNeuronR19').fill(str(last_id))
 page.locator('#targetNeuronR19').fill('')
 page.locator('#graphDepthR19').select_option('1')
 page.locator('#neuronRunR19').click()
 page.wait_for_function('window.ProceduralAtlasR18.getGraph() && window.ProceduralAtlasR18.getGraph().root===86099999999',timeout=15000)
 print('86B_EDGE_SEARCH',json.dumps(page.evaluate('window.ProceduralAtlasR18.getGraph()')),flush=True)
 page.locator('#neuronClearR19').click()
 page.wait_for_function('window.ProceduralAtlasR18.getGraph()===null',timeout=10000)
 page.locator('#tract').select_option('49')
 page.wait_for_function('window.ProceduralAtlasR18.getStats().segments>0',timeout=10000)
 t=page.evaluate('window.ProceduralAtlasR18.getStats()')
 assert t['tract']==49 and t['segments']>0
 print('TRACT',json.dumps(t),flush=True)
 page.evaluate('window.ProceduralAtlasR18.setTotal(1000000000000)')
 page.wait_for_function('window.ProceduralAtlasR18.getStats().allocated===1000000000000',timeout=13000)
 trillion=page.evaluate('''() => {const a=window.ProceduralAtlasR18, id=999999999999;return {stats:a.getStats(),neuron:a.resolveNeuronId(id),out:a.outgoingNeuronIds(id)};}''')
 assert trillion['neuron']['id']==999999999999 and len(trillion['out'])>=1
 assert all(0<=x<1000000000000 for x in trillion['out'])
 print('ONE_TRILLION',json.dumps(trillion,ensure_ascii=False)[:350],flush=True)
 mobile=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
 mobile.on('pageerror',lambda e:errors.append('mobile '+str(e)))
 mobile.goto(URL,wait_until='domcontentloaded',timeout=20000)
 mobile.wait_for_function('window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown>0',timeout=30000)
 mobile.locator('#togglePanel').click()
 assert mobile.locator('#panel').is_visible()
 assert mobile.locator('#neuronRunR19').count()==1
 print('MOBILE_R19',json.dumps(mobile.evaluate('window.ProceduralAtlasR18.getStats()')),flush=True)
 print('ERRORS',json.dumps(errors[:8],ensure_ascii=False),flush=True)
 assert not errors,errors
 b.close()
