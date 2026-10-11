#!/usr/bin/env python
"""Held holes with a later colour in them: the seam stage 5 leaves bare.

Stage 5 holds a hole open at its original size when the shell's pull growth
would shrink it under `min_detail_mm²` -- right for a counter, and wrong for
a hole a LATER stitched colour sews in: the hold strips the ground's pull
growth and its `overlap_mm` tongue from the whole seam round that piece, a
butt joint with nothing under it. `cfg.held_hole_bare_only` holds only the
part of the hole no later stitched shape covers (and only the bare pieces at
or over the same floor). This reads both, OFF against ON, per fixture:

  * `held`           -- holes stage 5 held open (its HOLE_NEARLY_CLOSED count);
  * `pieces`         -- later stitched shapes whose artwork sits in a hole the
                        OFF engine held (the seams this is about);
  * `zero_mm`        -- PLAN: length of those pieces' seams carrying NO
                        underlap (`seam_underlap.measure`'s depth-0 pairs);
  * `tongue_sewn`    -- STITCHES: of points just inside each piece's edge
                        (pull + overlap/2 in, halved in turn for a piece too
                        thin for that), the share the GROUND's own thread
                        passes within one fill row of, over `sampled` of the
                        pieces. DOCTRINE: prove a seam on the stitches, never
                        on the plan;
  * `ring_bare_mm2`  -- STITCHES: area of the 0.2 mm band either side of each
                        piece's edge, inside its hole, that NO thread of any
                        colour comes within one fill row of -- the line of
                        fabric Kent saw at the seams on the first sew-out;
  * stitches, trims, and whether the plan is byte-identical.

    .venv/bin/python tools/held_hole_tongue.py photo/drone_render.png
    .venv/bin/python tools/held_hole_tongue.py --all [--width 80] [--garment left_chest]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import replace
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, machine, run_stages  # noqa: E402
from digitizer_core.pipeline import fabric_for, plan_stitches  # noqa: E402
from digitizer_core.stage5_overlap import _shrink, resolve_overlaps  # noqa: E402
from seam_underlap import measure as seam_measure  # noqa: E402

TESTDATA = ROOT / "testdata"
FIXTURES = [
    "art/logo_hotel_fremont_patch.png", "photo/logo_hotel_fremont.webp",
    "photo/drone_render.png", "photo/logo_bridge_bar.jpg", "art/logo_golke_roofing.png",
    "photo/enthusiast_logo.png", "becker_marine_logo.png", "logo_whitebg.png",
]
RING_MM = 0.2


def held_pieces(regions, pull: float, floor: float) -> list[tuple]:
    """(ground, piece) for each later stitched piece whose artwork sits in a
    hole of an earlier stitched shape that the OFF engine holds open."""
    out = []
    for g in regions:
        L = g.meta["layer"]
        for ring in g.polygon.interiors:
            hole = Polygon(ring)
            if hole.area < floor or _shrink(hole, pull, None).area >= floor:
                continue
            for p in regions:
                if (p.meta["layer"] > L
                        and p.polygon.representative_point().within(hole)):
                    out.append((g, p, hole))
    return out


def _owner(run_shape_id: str) -> str:
    """The region a run belongs to: shape ids are `S<hex>`, and every run
    suffix (`-blend…`, underlay, …) follows a dash."""
    return run_shape_id.split("-")[0]


def _thread(plan, shape_ids=None):
    row = machine.FILL_ROW_MM
    lines = [LineString(r.points).buffer(row)
             for _b, r in plan.iter_runs()
             if len(r.points) > 1
             and (shape_ids is None or _owner(r.shape_id) in shape_ids)]
    return unary_union(lines) if lines else None


def _inside(poly, inset: float):
    """`poly` shrunk by `inset` -- or, for a piece thinner than twice that,
    by half its own reach in turn until something is left, so the thinnest
    pieces (the ones a full tongue runs right under) are sampled too."""
    d = inset
    while d > 0.01:
        inner = poly.buffer(-d)
        if not inner.is_empty:
            return inner
        d /= 2.0
    return None


def sewn(plan, pieces, inset: float) -> dict:
    """Tongue and bare ring, read off the stitches."""
    everything = _thread(plan)
    hits = total = 0
    sampled = 0
    bare = 0.0
    for g, p, hole in pieces:
        ground = _thread(plan, {g.shape_id})
        inner = _inside(p.polygon, inset)
        sampled += inner is not None
        for part in getattr(inner, "geoms", [inner]) if inner is not None else []:
            if part.is_empty:
                continue
            edge = part.exterior
            n = max(4, int(edge.length / 0.1))
            for i in range(n):
                pt = edge.interpolate(i / n, normalized=True)
                total += 1
                hits += bool(ground is not None and ground.contains(pt))
        ring = (p.polygon.buffer(RING_MM).difference(p.polygon.buffer(-RING_MM))
                .intersection(hole))
        if everything is not None:
            ring = ring.difference(everything)
        bare += ring.area
    return {"tongue_sewn": (hits / total) if total else None,
            "sampled": sampled,
            "ring_bare_mm2": round(bare, 3)}


def plan_md5(plan) -> str:
    h = hashlib.md5()
    for b, r in plan.iter_runs():
        h.update(f"{b.thread_number}|{r.shape_id}|{r.kind}|{r.trim}".encode())
        for x, y in r.points:
            h.update(f"{x:.6f},{y:.6f};".encode())
    return h.hexdigest()


def measure_image(image: Path, width_mm: float, garment: str | None) -> dict:
    base = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result = run_stages(image, base)
    fabric = fabric_for(base)
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    pieces = held_pieces(stitched, fabric.pull_comp_mm, base.min_detail_mm ** 2)
    piece_ids = {p.shape_id for _g, p, _h in pieces}
    inset = fabric.pull_comp_mm + base.overlap_mm / 2.0
    out = {"pieces": len(pieces), "_pieces": pieces, "_plans": {}}
    for name, flag in (("off", False), ("on", True)):
        cfg = replace(base, held_hole_bare_only=flag)
        planned, warns = resolve_overlaps(stitched, fabric, cfg, result.design_class)
        held = sum(w.get("count", 0) for w in warns if w.get("code") == "HOLE_NEARLY_CLOSED")
        seams = seam_measure(stitched, planned)
        zero = sum(s["shared_mm"] for s in seams["pairs"]
                   if s["later"] in piece_ids and s["depth_mm"] == 0.0)
        plan = plan_stitches(result, cfg)
        st = plan.stats
        out["_plans"][name] = plan
        out[name] = {"held": held, "zero_mm": round(zero, 1),
                     "under_025_mm": seams["under"][0.25],
                     "stitches": st.stitch_count, "trims": st.trims,
                     "md5": plan_md5(plan), **sewn(plan, pieces, inset)}
    return out


def _draw(plan, piece, hole, bounds, px: float):
    """One close-up: fabric, every run in its thread's colour at about a
    40-weight thread's width -- the piece's own runs at 35% so the ground's
    thread under it shows -- and the piece's artwork edge as a red line."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = bounds
    w, h = int((x1 - x0) * px), int((y1 - y0) * px)
    img = np.full((h, w, 3), (205, 214, 222), np.uint8)       # pale fabric (BGR)

    def to_px(pts):
        return np.array([[(x - x0) * px, (y - y0) * px] for x, y in pts],
                        np.int32).reshape(-1, 1, 2)
    thick = max(1, int(round(0.35 * px)))
    top = img.copy()
    mask = np.zeros((h, w), np.uint8)
    for b, r in plan.iter_runs():
        if len(r.points) < 2:
            continue
        bgr = tuple(int(c) for c in reversed(b.rgb))
        if _owner(r.shape_id) == piece.shape_id:
            cv2.polylines(top, [to_px(r.points)], False, bgr, thick, cv2.LINE_AA)
            cv2.polylines(mask, [to_px(r.points)], False, 255, thick, cv2.LINE_AA)
        else:
            cv2.polylines(img, [to_px(r.points)], False, bgr, thick, cv2.LINE_AA)
            cv2.polylines(top, [to_px(r.points)], False, bgr, thick, cv2.LINE_AA)
    a = (mask[..., None].astype(np.float32) / 255.0) * 0.35
    img = (img * (1 - a) + top * a).astype(np.uint8)
    cv2.polylines(img, [to_px(piece.polygon.exterior.coords)], True, (30, 30, 235), 1,
                  cv2.LINE_AA)
    return img


def render(m: dict, out_png: Path, px: float = 60.0, limit: int = 4) -> None:
    """OFF | ON for up to `limit` pieces, stacked: thread as sewn, the piece's
    own thread see-through, its artwork edge red."""
    import cv2
    import numpy as np
    rows = []
    for _g, p, hole in m["_pieces"][:limit]:
        bx0, by0, bx1, by1 = hole.bounds
        pad = 1.2
        bounds = (bx0 - pad, by0 - pad, bx1 + pad, by1 + pad)
        pair = [_draw(m["_plans"][k], p, hole, bounds, px) for k in ("off", "on")]
        gap = np.full((pair[0].shape[0], 12, 3), 255, np.uint8)
        rows.append(np.hstack([pair[0], gap, pair[1]]))
    if not rows:
        return
    wmax = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 12), (0, wmax - r.shape[1]), (0, 0)), constant_values=255)
            for r in rows]
    head = np.full((40, wmax, 3), 255, np.uint8)
    half = rows[0].shape[1] // 2
    cv2.putText(head, "OFF (hole held)", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(head, "ON (bare part only)", (half + 8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 0), 2)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_png), np.vstack([head] + rows))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("images", nargs="*", help="paths under testdata/, or absolute")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--render", type=Path, default=None,
                    help="directory: write an OFF|ON close-up per fixture")
    args = ap.parse_args(argv)
    names = FIXTURES if args.all else args.images
    if not names:
        ap.error("name an image or pass --all")
    print(f"{'fixture':34} {'pcs':>3}  {'held':>9} {'zero mm':>11} {'<0.25 mm':>13} "
          f"{'tongue (n)':>17} {'ring bare mm2':>15} {'stitches':>13} {'trims':>9}  same")
    for name in names:
        path = Path(name) if Path(name).is_absolute() else TESTDATA / name
        m = measure_image(path, args.width, args.garment)
        a, b = m["off"], m["on"]
        if args.render is not None:
            render(m, args.render / (Path(name).stem + ".png"))

        def pair(k, fmt="{}"):
            return f"{fmt.format(a[k])}>{fmt.format(b[k])}"

        def pct(v):
            return "-" if v is None else f"{v:.0%}"
        tongue = f"{pct(a['tongue_sewn'])}>{pct(b['tongue_sewn'])} ({b['sampled']}/{m['pieces']})"
        print(f"{name:34} {m['pieces']:>3}  {pair('held'):>9} {pair('zero_mm'):>11} "
              f"{pair('under_025_mm'):>13} {tongue:>17} "
              f"{pair('ring_bare_mm2'):>15} {pair('stitches'):>13} {pair('trims'):>9}  "
              f"{'md5' if a['md5'] == b['md5'] else 'moved'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
