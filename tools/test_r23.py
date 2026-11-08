#!/usr/bin/env python3
from pathlib import Path
import json
p=Path(__file__).resolve().parents[1]
js=(p/'docs/procedural/procedural_r23.js').read_text()
html=(p/'docs/procedural/index.html').read_text()
m=json.loads((p/'docs/assets/manifest_r22_triangles.json').read_text())
assert m['region_count']==283 and m['triangle_count']==656268
assert 'procedural_r23.js' in html
assert 'id="occludeBack"' in html
assert 'id="linkOn" aria-pressed="true"' in html
assert 'links=true' in js
for term in ("function makeFibers", "gl.drawArraysInstanced(gl.LINE_STRIP,0,3,surfaceFiberEdges)",
             "gl.vertexAttribDivisor(i,1)", "previous=denseFibers?new Float32Array",
             "const vid of hint.vertices", "surfaceFiberOrphans","function ensureVisibleTriangles",
             "gl.depthMask(false);common(Fiber)", "function findSyntheticPath"):
 assert term in js,term
assert "gl.drawElements(gl.TRIANGLES" not in js
assert "realSynapses:false" in js
assert (p/'docs/procedural/procedural_r22.js').is_file()
readme=(p/'README.md').read_text()
assert readme.startswith('# Mikoshi HQ500M — CPU Playground')
assert readme.index('<!-- HQ500M_README_HERO_END -->')<readme.index('## R23:')
print('PASS R23 static contract')
