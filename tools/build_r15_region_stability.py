#!/usr/bin/env python3
"""R15 boundary-stability metadata for unregistered R14 candidate regions.
Labels and source geometry are unchanged. Stability is geometric, NOT anatomical confidence.
"""
from __future__ import annotations
from array import array
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import gzip, hashlib, json, struct, sys

GRID = 64
REGION_N = 4

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def unpack(src: Path, magic: bytes, stride: int) -> tuple[int, bytes]:
    raw = gzip.decompress(src.read_bytes())
    assert raw[:4] == magic, src
    count, = struct.unpack_from("<I", raw, 4)
    assert len(raw) == 8 + stride * count, src
    return count, raw[8:]

def write_layer(path: Path, vals: bytes) -> dict:
    raw = b"HQA5" + struct.pack("<I", len(vals)) + vals
    zipped = gzip.compress(raw, compresslevel=7, mtime=0)
    path.write_bytes(zipped)
    return {"file": "assets/" + path.name, "bytes": len(zipped), "sha256": sha(zipped)}

def build(root: Path) -> dict:
    old = json.loads((root / "manifest_r14.json").read_text())
    pts_file = root / "hq500m_source_points_r13.bin.gz"
    r14_file = root / "hq500m_region_density_r14.bin.gz"
    assert sha(pts_file.read_bytes()) == old["source_r13_sha256"]
    assert sha(r14_file.read_bytes()) == old["full"]["sha256"]
    n, pts = unpack(pts_file, b"HQP3", 8)
    m, r14 = unpack(r14_file, b"HQR4", 2)
    assert n == m
    cells = array("I", [0]) * (GRID * GRID * GRID * REGION_N)
    ids = array("I", [0]) * n
    for i, (x,y,z,a,s) in enumerate(struct.iter_unpack("<HHHBB", pts)):
        gx,gy,gz = x * GRID // 65536, y * GRID // 65536, z * GRID // 65536
        voxel = (gx * GRID + gy) * GRID + gz
        rid = r14[2*i]
        assert 0 <= rid < REGION_N
        cells[voxel*REGION_N+rid] += 1
        ids[i] = voxel
    # One stability value per occupied voxel. This is based on the 3x3x3
    # neighboring occupancy, NOT on external MRI landmarks.
    stability = bytearray(GRID*GRID*GRID)
    mixed = 0
    for voxel in set(ids):
        z = voxel % GRID
        t = voxel // GRID
        y = t % GRID
        x = t // GRID
        acc = [0,0,0,0]
        for a in range(max(0,x-1), min(GRID,x+2)):
            for b in range(max(0,y-1), min(GRID,y+2)):
                start = (a*GRID+b)*GRID
                for c in range(max(0,z-1), min(GRID,z+2)):
                    idx = (start+c)*REGION_N
                    for r in range(REGION_N):
                        acc[r] += cells[idx+r]
        total = sum(acc)
        primary = max(range(REGION_N), key=lambda k: cells[voxel*REGION_N+k])
        purity = acc[primary]/total if total else 0
        stability[voxel] = round(purity*255)
        if purity < .6:
            mixed += 1
    out = bytearray(n)
    stats = {}
    for i in range(n):
        rid = r14[2*i]
        # Use source-point class, not majority class, near mixed cells
        voxel = ids[i]
        v = stability[voxel]
        out[i] = v if cells[voxel*REGION_N+rid] == max(cells[voxel*REGION_N:voxel*REGION_N+REGION_N]) else min(128,v)
    for r in range(REGION_N):
        vals = [out[i] for i in range(n) if r14[2*i] == r]
        stats[str(r)] = {"points":len(vals),"stable_ge_192":sum(v>=192 for v in vals),
                        "stable_ge_224":sum(v>=224 for v in vals)}
    full_file = root/"hq500m_region_stability_r15.bin.gz"
    lite_file = root/"hq500m_region_stability_lite_r15.bin.gz"
    full = write_layer(full_file, bytes(out))
    lite = write_layer(lite_file, bytes(out[::4]))
    manifest = {
        "version":"R15", "generated_at":datetime.now(timezone.utc).isoformat(),
        "atlas_registration":{"status":"not_registered",
          "atlases_to_consider":["MNI152 (full brain)","SUIT (cerebellum)"],
          "why":"Terrie point cloud has no known spatial orientation, MRI reference or registration landmarks",
          "mapping":"R14 heuristic region IDs; no verified anatomical region labels"},
        "original_r13_xyz_modified":False,"original_r11_fibers_modified":False,
        "point_count":n, "source_r13_sha256":sha(pts_file.read_bytes()),
        "source_r14_sha256":sha(r14_file.read_bytes()),
        "stability_definition":"0..255 fraction of nearby R14 candidate labels agreeing with most common label at each occupied voxel; boundary continuity only, NOT medical certainty",
        "grid":GRID, "regions":stats,"mixed_cells_lt_0_6":mixed,
        "full":full, "lite":lite,
        "original_geometry_sha256":old["source_r13_sha256"],
        "license_source":"Terrie Brain Point Cloud CC BY 4.0",
        "references":["https://pmc.ncbi.nlm.nih.gov/articles/PMC2776484/",
                      "https://www.diedrichsenlab.org/imaging/atlasPackage.htm"]
    }
    (root/"manifest_r15.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    for p, expected in [(full_file,n),(lite_file,(n+3)//4)]:
        cnt, buf=unpack(p,b"HQA5",1)
        assert cnt == expected
    assert sha(pts_file.read_bytes()) == old["source_r13_sha256"]
    print(json.dumps({"regions":stats,"mixed_cells":mixed,"full_bytes":full["bytes"],
                       "lite_bytes":lite["bytes"],"source_untouched":True},indent=2))
    return manifest

if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/"docs/assets")
