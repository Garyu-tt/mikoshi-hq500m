#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json
CHROME="/home/mirbi/.cache/ai3d-lab/playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell"
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=CHROME,headless=True,args=["--no-sandbox","--disable-dev-shm-usage","--enable-unsafe-swiftshader","--use-gl=angle","--use-angle=swiftshader"])
 page=b.new_page(viewport={"width":1460,"height":890},device_scale_factor=1)
 page.on("pageerror",lambda exc:errors.append(str(exc)))
 page.on("console",lambda msg:errors.append(msg.text) if msg.type=="error" else None)
 page.goto("http://127.0.0.1:48999/procedural/",wait_until="domcontentloaded",timeout=20000)
 page.wait_for_function("window.ProceduralAtlasR18&&window.ProceduralAtlasR18.getStats().shown>=220000",timeout=90000)
 initial=page.evaluate("window.ProceduralAtlasR18.getStats()")
 assert initial["shown"]==220000,initial
 assert initial["surfaceFiberEdges"]==0
 page.locator("#linkOn").click()
 page.wait_for_function("window.ProceduralAtlasR18.getStats().surfaceFiberEdges>50000",timeout=110000)
 dense=page.evaluate("window.ProceduralAtlasR18.getStats()")
 print("DENSE",json.dumps(dense),flush=True)
 assert dense["surfaceFiberEdges"]>50000,dense
 assert dense["segments"]==0,dense
 page.mouse.move(720,410);page.mouse.down();page.mouse.move(850,450,steps=4);page.mouse.up()
 page.wait_for_timeout(2200)
 rotate=page.evaluate("window.ProceduralAtlasR18.getStats()")
 print("ROTATE",json.dumps(rotate),flush=True)
 assert rotate["surfaceFiberEdges"]>50000
 page.locator("#occludeBack").uncheck()
 page.wait_for_function("window.ProceduralAtlasR18.getVisibility().active===false",timeout=45000)
 off=page.evaluate("window.ProceduralAtlasR18.getStats()")
 print("UNMASKED",json.dumps(off),flush=True)
 page.locator("#linkOff").click()
 page.wait_for_function("window.ProceduralAtlasR18.getStats().surfaceFiberEdges===0",timeout=25000)
 page.locator("#occludeBack").check()
 page.wait_for_function("window.ProceduralAtlasR18.getVisibility().active===true",timeout=25000)
 page.locator("#region").select_option("111")
 page.locator("#linkOn").click()
 page.wait_for_function("window.ProceduralAtlasR18.getStats().selected===111",timeout=35000)
 selected=page.evaluate("window.ProceduralAtlasR18.getStats()")
 print("REGION",json.dumps(selected),flush=True)
 assert selected["surfaceFiberEdges"]==0,selected
 page.locator("#region").select_option("-1")
 page.locator("#sourceNeuronR19").fill("42")
 page.locator("#background").select_option("hide")
 page.locator("#neuronRunR19").click()
 page.wait_for_function("window.ProceduralAtlasR18.getGraph()!=null",timeout=25000)
 graph=page.evaluate("window.ProceduralAtlasR18.getStats()")
 print("ID",json.dumps(graph),flush=True)
 assert graph["surfaceFiberEdges"]==0
 page.locator("#neuronClearR19").click()
 print("ERRORS",errors[:15],flush=True)
 assert not errors,errors
 b.close()
