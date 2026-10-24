#!/usr/bin/env python
"""silhouette_underfill_proof: OFF | ON | pro for `cfg.silhouette_underfill`.

One digitization per job through the Studio's request
(`tools.pro_pair.digitize`, `sew_enclosed_white` and `enclosed_white_keyline`
ON -- the two flags the under-fill is judged beside), then `plan_stitches`
twice on that one result: under-fill OFF and ON. Both plans are written to
DST and read back, so ours and the pro's file go through one reader:

  economy   stitches / trims / colour changes as pystitch reads each DST;
            travel mm, and the part no later colour sews over (ours only:
            the plan carries run kinds, a DST does not)
  blocks    per colour block, the share of the ring, of its holes and of the
            silhouette (the ring's outline, holes closed) that block covers
            (`tier_census.read_tier`'s 0.1 mm thread raster). The pro's
            construction reads as ONE block covering ring and holes; ours
            OFF covers the ring and the holes with different blocks.

Shapes are OURS (the ring `silhouette_underfill.plan` reads on the ON plan's
regions), mapped into the pro's frame by `pairframe.register_pair`. The sheet
(art | OFF | ON | pro, 10 px/mm, each in its own frame) goes to --out.

  python tools/silhouette_underfill_proof.py --art A --pro P --width MM --garment G --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
for p in (str(DIGITIZER), str(DIGITIZER / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

PPM = 10.0
FLAGS = {"sew_enclosed_white": True, "enclosed_white_keyline": True}


def _block_cover(dst: Path, polys: dict, reg=None) -> list[dict]:
    """Per colour block of `dst`: cover of each named polygon (mapped by `reg`)."""
    from shapely.affinity import affine_transform
    from tools import tier_census as tc
    from tools.study_pro import load_runs
    runs, _t, _j = load_runs(dst)
    mapped = {k: (affine_transform(v, reg.matrix()) if reg is not None else v) for k, v in polys.items()}
    out = []
    for b in range(max(r["block"] for r in runs) + 1):
        segs = tc._segments([r for r in runs if r["block"] == b])
        if not len(segs):
            continue
        ix = tc.Index(segs)
        row = {"block": b, "stitches": int(len(segs))}
        for k, poly in mapped.items():
            row[k] = round(tc._cover(poly, ix.near(poly.bounds)), 2) if poly.area > 1 else None
        out.append(row)
    return out


def _art_on_white(path: Path):
    """The artwork as BGR, an alpha channel composited onto white (a plain
    imread drops alpha and draws a transparent PNG black)."""
    import cv2
    import numpy as np
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im is None or im.ndim == 2 or im.shape[2] == 3:
        return cv2.imread(str(path), cv2.IMREAD_COLOR)
    a = im[:, :, 3:4].astype(np.float32) / 255.0
    return (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)


def exposed_travel_mm(plan, res: float = 10.0) -> dict:
    """Needle-down travel (`StitchRun.kind == "travel"`) in mm, all of it and
    the part no LATER block sews over (a 0.4 mm thread raster at `res` px/mm,
    sampled every 0.25 mm along each travel stitch). Sewing white over black
    leaves the white's travel on top -- this is what that costs."""
    import math
    import cv2
    import numpy as np
    blocks = plan.blocks
    pts = [p for b in blocks for r in b.runs for p in (r.points or [])]
    if not pts:
        return {"travel_mm": 0.0, "exposed_mm": 0.0}
    x0 = min(p[0] for p in pts) - 2
    y0 = min(p[1] for p in pts) - 2
    w = int((max(p[0] for p in pts) - x0 + 2) * res) + 1
    h = int((max(p[1] for p in pts) - y0 + 2) * res) + 1
    cover = np.zeros((h, w), np.uint8)
    thick = max(1, int(round(0.4 * res)))
    total = exposed = 0.0
    runs = [r for b in blocks for r in b.runs]
    for r in reversed(runs):                    # everything sewn later is drawn first
        if r.jump or not r.points:
            continue
        if str(r.kind) == "travel":
            for a, c in zip(r.points, r.points[1:]):
                L = math.dist(a, c)
                n = max(1, int(L / 0.25))
                hit = 0
                for k in range(n + 1):
                    x = a[0] + (c[0] - a[0]) * k / n
                    y = a[1] + (c[1] - a[1]) * k / n
                    hit += cover[int((y - y0) * res), int((x - x0) * res)] > 0
                total += L
                exposed += L * (1 - hit / (n + 1))
        q = np.array([((x - x0) * res, (y - y0) * res) for x, y in r.points], np.int32)
        cv2.polylines(cover, [q], False, 1, thick)
    return {"travel_mm": round(total, 1), "exposed_mm": round(exposed, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--art", required=True, type=Path)
    ap.add_argument("--pro", required=True, type=Path)
    ap.add_argument("--width", required=True, type=float)
    ap.add_argument("--garment", default="hat_front")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--pickle", type=Path, default=None,
                    help="cache the digitization here (read it if present): re-plans cost seconds")
    a = ap.parse_args(argv)

    import cv2
    from digitizer_core import silhouette_underfill as su
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.export import write_dst
    from digitizer_core.pipeline import plan_stitches
    from digitizer_core.stitchviz import render_design
    from tools import pro_pair as pp
    from tools.pro_parity.pairframe import design_for, register_pair

    a.out.mkdir(parents=True, exist_ok=True)
    if a.pickle is not None and a.pickle.exists():
        import pickle
        saved = pickle.loads(a.pickle.read_bytes())       # our own scratch file
        result, cfg = saved["result"], saved["cfg"]
    else:
        d = pp.digitize(a.art, a.width, a.garment, dict(FLAGS))
        result, cfg = d.result, d.cfg
        if a.pickle is not None:
            import pickle
            a.pickle.write_bytes(pickle.dumps({"result": result, "cfg": cfg}))
    plans = {"off": plan_stitches(result, cfg),
             "on": plan_stitches(result, replace(cfg, silhouette_underfill=True))}
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    rings = su.plan(stitched, [r for r in result.regions if not r.meta.get("stitched", True)])
    stats = {"pro": pp.pro_counts(a.pro), "rings": []}
    polys = {}
    for ring, host, outline, merged, inner in rings:
        stats["rings"].append({"ring": ring.shape_id, "host": host.shape_id,
                               "ring_mm2": round(ring.polygon.area, 1),
                               "outline_mm2": round(outline.area, 1), "merged": len(merged),
                               "inner": len(inner), "host_is_ring": host is ring})
    if rings:
        ring, _h, outline, _m, _i = rings[0]
        polys = {"ring": ring.polygon, "holes": outline.difference(ring.polygon), "silhouette": outline}
    imgs = []
    art = _art_on_white(a.art)
    if art is not None:
        s = a.width * PPM / art.shape[1]
        imgs.append(pp._label(cv2.resize(art, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), "art"))
    for arm, plan in plans.items():
        dst = a.out / f"ours_{arm}.dst"
        write_dst(plan, dst)
        stats[arm] = {k: v for k, v in pp.pro_counts(dst).items() if k != "file"}
        stats[arm].update(exposed_travel_mm(plan))
        if polys:
            stats[arm]["blocks"] = _block_cover(dst, polys)
        img = render_design(plan_to_design(plan, name=arm), px_per_mm=PPM)
        imgs.append(pp._label(img, f"ours {arm.upper()}: {stats[arm]['stitches']} st, "
                                   f"{stats[arm]['trims']} trims"))
    if polys:
        reg = register_pair(a.pro, a.out / "ours_on.dst")
        stats["pro"]["blocks"] = _block_cover(a.pro, polys, reg)
        stats["pro"]["registration_iou"] = round(reg.iou, 3)
    pro_img = render_design(design_for(a.pro, None, None, "pro"), px_per_mm=PPM)
    imgs.append(pp._label(pro_img, f"pro: {stats['pro']['stitches']} st, {stats['pro']['trims']} trims"))
    cv2.imwrite(str(a.out / "sheet.png"), pp._hstack(imgs), [cv2.IMWRITE_PNG_COMPRESSION, 9])
    (a.out / "stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
