#!/usr/bin/env python3
"""Real Playwright/SwiftShader R23 integration + screenshot verification.
Requires Chromium with WebGL2 support. Libraries can be supplied through LD_LIBRARY_PATH."""
import json, time
from PIL import Image, ImageChops, ImageStat
from pathlib import Path
from playwright.sync_api import sync_playwright
CHROME='/home/mirbi/.cache/ai3d-lab/playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'
BASE='http://127.0.0.1:48999/procedural/'
ROOT=Path(__file__).resolve().parents[1]
ERRORS=[]
def wait(page, predicate, timeout=30):
    deadline=time.monotonic()+timeout
    last=None
    while time.monotonic()<deadline:
        try:
            last=page.evaluate(predicate)
            if last:return last
        except Exception as exc:
            last=str(exc)
        page.wait_for_timeout(350)
    status=page.evaluate("document.getElementById('status')?.textContent")
    raise AssertionError(f"Timeout: {predicate}; last={last}; status={status}; errors={ERRORS[:4]}")
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,headless=True,args=[
        '--no-sandbox','--disable-dev-shm-usage','--disable-gpu-sandbox',
        '--enable-unsafe-swiftshader','--enable-webgl','--use-gl=angle','--use-angle=swiftshader'])
    page=b.new_page(viewport={'width':1460,'height':890},device_scale_factor=1)
    page.add_init_script("""window.__fiberDraws=0;const orig=WebGL2RenderingContext.prototype.drawArraysInstanced;
        WebGL2RenderingContext.prototype.drawArraysInstanced=function(mode,start,vertices,count){
        if(mode===this.LINE_STRIP&&vertices===3)window.__fiberDraws++;
        return orig.apply(this,arguments);};""")
    page.on('pageerror',lambda e:ERRORS.append('js:'+str(e)))
    page.on('console',lambda m:ERRORS.append('console:'+m.text) if m.type=='error' else None)
    page.goto(BASE,wait_until='domcontentloaded',timeout=20000)
    wait(page,"window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown===220000",60)
    wait(page,"window.__fiberDraws>0",20)
    initial=page.evaluate("""({stats:window.ProceduralAtlasR18.getStats(),
      visibility:window.ProceduralAtlasR18.getVisibility(),draws:window.__fiberDraws,
      gpuError:document.getElementById('scene').getContext('webgl2').getError()})""")
    assert initial['stats']['surfaceFiberEdges']>200000,initial
    assert initial['visibility']['active'] and initial['gpuError']==0,initial
    assert initial['stats']['segments']==0,initial
    print('R23 DESKTOP',json.dumps(initial),flush=True)
    page.screenshot(path=str(ROOT/'docs/images/r23_dense_front.png'),timeout=30000)
    page.locator('#linkOff').click()
    wait(page,"window.ProceduralAtlasR18.getStats().surfaceFiberEdges===0",35)
    page.screenshot(path=str(ROOT/'docs/images/r23_front_no_fibers.png'),timeout=30000)
    with_fibers=Image.open(ROOT/'docs/images/r23_dense_front.png').convert('RGB')
    without_fibers=Image.open(ROOT/'docs/images/r23_front_no_fibers.png').convert('RGB')
    red_change=ImageStat.Stat(ImageChops.difference(with_fibers,without_fibers)).mean[0]
    assert red_change>2.0,f"Fibers are not visibly modifying the rendered framebuffer: {red_change}"
    print('SCREENSHOT PIXEL DELTA RED',round(red_change,2),flush=True)
    page.locator('#linkOn').click()
    wait(page,"window.ProceduralAtlasR18.getStats().surfaceFiberEdges>200000",35)
    start=page.evaluate("window.ProceduralAtlasR18.getVisibility().eligibleHraTriangles")
    page.mouse.move(660,350);page.mouse.down();page.mouse.move(820,390,steps=5);page.mouse.up()
    wait(page,f"window.ProceduralAtlasR18.getVisibility().eligibleHraTriangles!=={start}",40)
    rotated=page.evaluate("window.ProceduralAtlasR18.getVisibility()")
    assert rotated['active'] and rotated['eligibleHraTriangles']>10000
    print('ROTATED',rotated['eligibleHraTriangles'],flush=True)
    page.locator('#occludeBack').uncheck()
    wait(page,"window.ProceduralAtlasR18.getVisibility().active===false",20)
    page.locator('#occludeBack').check()
    wait(page,"window.ProceduralAtlasR18.getVisibility().active===true",30)
    page.locator('#preset861').click()
    wait(page,"window.ProceduralAtlasR18.getStats().shown===682889",55)
    huge=page.evaluate("window.ProceduralAtlasR18.getStats()")
    assert huge['total']==86100000000 and huge['surfaceFiberEdges']>600000
    print('86.1B AUTO',json.dumps(huge),flush=True)
    page.locator('#lodMode').select_option('manual')
    page.locator('#lod').fill('1100000')
    wait(page,"window.ProceduralAtlasR18.getStats().shown===1100000",60)
    dense=page.evaluate("window.ProceduralAtlasR18.getStats()")
    assert dense['surfaceFiberEdges']>1000000
    print('86.1B MAX',json.dumps(dense),flush=True)
    page.locator('#region').select_option('111')
    wait(page,"window.ProceduralAtlasR18.getStats().selected===111 && window.ProceduralAtlasR18.getStats().surfaceFiberEdges===0",30)
    focused=page.evaluate("window.ProceduralAtlasR18.getStats()")
    assert focused['surfaceFiberEdges']==0
    print('FOCUS REGION',focused['selected'],flush=True)
    page.evaluate('''() => {
      document.getElementById('region').value='-1';
      document.getElementById('region').dispatchEvent(new Event('change'));
      document.getElementById('sourceNeuronR19').value='42';
      document.getElementById('targetNeuronR19').value='';
      document.getElementById('background').value='hide';
      document.getElementById('neuronRunR19').click();
    }''')
    wait(page,"window.ProceduralAtlasR18.getGraph()!==null && window.ProceduralAtlasR18.getStats().surfaceFiberEdges===0 && window.ProceduralAtlasR18.getStats().shown<300",35)
    graph=page.evaluate("window.ProceduralAtlasR18.getStats()")
    assert graph['surfaceFiberEdges']==0 and 0<graph['segments']<1000 and graph['shown']<300
    print('NEURON GRAPH',json.dumps(graph),flush=True)
    page.close()  # release the 1.1M-edge software GPU context before mobile QA
    m=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
    m.on('pageerror',lambda e:ERRORS.append('mobile:'+str(e)))
    m.goto(BASE,wait_until='domcontentloaded',timeout=45000)
    wait(m,"window.ProceduralAtlasR18 && window.ProceduralAtlasR18.getStats().shown===120000",55)
    mobile=m.evaluate("window.ProceduralAtlasR18.getStats()")
    assert mobile['surfaceFiberEdges']>100000
    print('MOBILE',json.dumps(mobile),flush=True)
    print('ERRORS',json.dumps(ERRORS[:8]),flush=True)
    assert not ERRORS,ERRORS
    b.close()
    print('PASS R23 actual Chromium WebGL2 browser integration',flush=True)
