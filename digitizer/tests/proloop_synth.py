"""Synthetic stitch geometry for the pro-overlay loop's tests.

Everything is built by hand — no engine call — so a test can say exactly
what each side sewed. Coordinates are mm in the FILE frame (y-down), the
frame `satin_columns.passes_from_file` and `prep_all.decode` read.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pystitch
from PIL import Image
import shapely.wkt


def satin_pass(x0, y0, length, width, pitch=0.4, angle_deg=0.0):
    """A zigzag column: rails `width` apart, crosses every `pitch` along
    `length`, the column's axis at `angle_deg`. Points alternate rails."""
    ca, sa = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    nx, ny = -sa, ca                       # rail normal
    pts = []
    n = max(3, int(length / pitch))
    for i in range(n + 1):
        t = i * pitch
        side = 1 if i % 2 == 0 else -1
        px = x0 + t * ca + side * (width / 2) * nx
        py = y0 + t * sa + side * (width / 2) * ny
        pts.append((round(px, 3), round(py, 3)))
    return pts


def fill_passes(x0, y0, w, h, row=0.4, stitch=3.0):
    """Tatami rows across a w x h box, serpentine, one pass per row."""
    passes = []
    rows = max(3, int(h / row))
    for r in range(rows + 1):
        y = y0 + r * row
        xs = np.arange(x0, x0 + w + 1e-9, stitch).tolist()
        if xs[-1] < x0 + w:
            xs.append(x0 + w)
        if r % 2:
            xs = xs[::-1]
        passes.append([(round(x, 3), round(y, 3)) for x in xs])
    return passes


def transform_passes(passes, scale=1.0, flip_y=False, dx=0.0, dy=0.0):
    fy = -1.0 if flip_y else 1.0
    return [[(x * scale + dx, y * fy * scale + dy) for x, y in p] for p in passes]


def write_pattern(path, blocks):
    """`blocks`: [((r,g,b), [pass, pass, ...]), ...]. A TRIM before every pass
    after the first of a block; a COLOR_CHANGE between blocks. Units 0.1 mm."""
    pat = pystitch.EmbPattern()
    for rgb, _ in blocks:
        t = pystitch.EmbThread()
        t.set_color(*rgb)
        pat.add_thread(t)
    for bi, (_rgb, passes) in enumerate(blocks):
        if bi:
            x, y = passes[0][0] if passes and passes[0] else (0, 0)
            pat.add_stitch_absolute(pystitch.COLOR_CHANGE, int(round(x * 10)), int(round(y * 10)))
        for pi, pts in enumerate(passes):
            if pi:
                lx, ly = passes[pi - 1][-1]
                pat.add_stitch_absolute(pystitch.TRIM, int(round(lx * 10)), int(round(ly * 10)))
                pat.add_stitch_absolute(pystitch.JUMP, int(round(pts[0][0] * 10)), int(round(pts[0][1] * 10)))
            for x, y in pts:
                pat.add_stitch_absolute(pystitch.STITCH, int(round(x * 10)), int(round(y * 10)))
    pat.end()
    path = Path(path)
    if path.suffix.lower() == ".pes":
        pystitch.write_pes(pat, str(path))
    else:
        pystitch.write_dst(pat, str(path))
    return path


def make_prep_dir(root, slug, pro_blocks, ours_blocks, regions, art_ink_boxes_mm,
                  width_mm, garment_id="left_chest", art_px_per_mm=10.0):
    """A `<root>/real/<slug>/` directory shaped like `prep_both`'s output.

    `regions`: [(shape_id, tier, shapely polygon in OURS frame)].
    `art_ink_boxes_mm`: [(x0, y0, x1, y1)] in OURS frame; the art is drawn
    black-on-transparent at `art_px_per_mm` over the ours stitch extents.
    """
    d = Path(root) / "real" / slug
    d.mkdir(parents=True, exist_ok=True)
    pro = write_pattern(d / "pro.pes", pro_blocks)
    write_pattern(d / "ours.dst", ours_blocks)
    (d / "ours_regions.json").write_text(json.dumps([
        {"shape_id": sid, "area_mm2": round(poly.area, 1), "thread": "0010", "tier": tier,
         "bounds": [round(v, 1) for v in poly.bounds],
         "wkt": shapely.wkt.dumps(poly, rounding_precision=3)}
        for sid, tier, poly in regions], indent=1))
    (d / "ours_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(rgb)} for i, (rgb, _) in enumerate(ours_blocks)]))
    (d / "pro_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(rgb)} for i, (rgb, _) in enumerate(pro_blocks)]))
    # art: the ink boxes over ours' stitch extents, alpha where ink is
    pts = [p for _rgb, passes in ours_blocks for ps in passes for p in ps]
    if not pts:
        raise ValueError("ours_blocks carry no stitches; make_prep_dir needs at least one pass to size the art")
    ox0, oy0 = min(p[0] for p in pts), min(p[1] for p in pts)
    ox1, oy1 = max(p[0] for p in pts), max(p[1] for p in pts)
    W = max(8, int(round((ox1 - ox0) * art_px_per_mm)) + 1)
    H = max(8, int(round((oy1 - oy0) * art_px_per_mm)) + 1)
    a = np.zeros((H, W, 4), np.uint8)
    for bx0, by0, bx1, by1 in art_ink_boxes_mm:
        c0, r0 = int((bx0 - ox0) * art_px_per_mm), int((by0 - oy0) * art_px_per_mm)
        c1, r1 = int((bx1 - ox0) * art_px_per_mm), int((by1 - oy0) * art_px_per_mm)
        c0, c1 = max(0, c0), min(W, c1)
        r0, r1 = max(0, r0), min(H, r1)
        if c1 <= c0 or r1 <= r0:
            continue
        a[r0:r1, c0:c1] = (0, 0, 0, 255)
    Image.fromarray(a, "RGBA").save(d / "art.png")
    (d / "art_meta.json").write_text(json.dumps({"px_per_mm": art_px_per_mm, "origin_mm": [ox0, oy0]}))
    man = Path(root) / "real" / "manifest.json"
    entries = json.loads(man.read_text()) if man.exists() else []
    entries = [e for e in entries if e.get("slug") != slug]
    entries.append({"slug": slug, "file": str(pro), "garment_id": garment_id,
                    "pro": {"width_mm": width_mm}, "ok": True})
    man.write_text(json.dumps(entries, indent=1))
    return d
