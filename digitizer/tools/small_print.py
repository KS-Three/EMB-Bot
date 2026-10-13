#!/usr/bin/env python
"""Small print: how the digitizer's traced lettering sews at 2.5-6 mm caps.

Kent asked about fine print (2026-10-12). `docs/small-cap-census-2026-10-12.md`
measured the JS lettering engine; this measures the DIGITIZER's lettering
path (the Column lane, `cfg.lettering_columns`, ON since #863) on traced
artwork, scaled so one line of lettering lands at a chosen cap height.

The line. A REFERENCE run at the fixture's reference width finds the
lettering-tagged regions (`columns.is_lettering`), groups them into lines by
vertical overlap and takes the `rank`-th by cap (largest / second /
smallest); the cap is the median bounding-box height of its letters. The
union of that line's region polygons is the SOURCE artwork: traced at a size
where every counter survives, then scaled (design coordinates are mm about
the design centre, so a width change is a scale about the origin) to each
small run. Measuring against the small run's own polygons would hide every
counter the trace already lost.

Per line, on a raster at `PX_PER_MM`, every needle-down segment of the plan
that lies in the line's box drawn at the thread's laid width
(`machine.thread_profile(cfg.thread_wt).width_mm`):

  dust      share of those segments under `machine.SATIN_SHORT_STITCH_AT_MM`
            (0.3 mm, the engine's own same-hole line).
  counters  each interior ring of the source (the A's triangle, the O's
            bowl): `counter_open` = the share of counter area still bare
            after sewing, area-weighted; `counters_shut` = counters under
            half open; `counters_traced` = counters the small run's own
            regions still carry (the rest were filled by the trace before
            a stitch was planned).
  spill     thread outside the source letters and outside their counters,
            over the source area: the column sewn wider than the letter.
  covered   share of the source letters under thread.

Run, from `digitizer/`:

    .venv/Scripts/python tools/small_print.py --fixture enthusiast --caps 3,4,5
    .venv/Scripts/python tools/small_print.py --fixture synthetic --caps 3 --flag small_print_floor=true
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
from shapely import affinity, wkt
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize, machine, stitches   # noqa: E402
from digitizer_core.columns import is_lettering                          # noqa: E402

PX_PER_MM = 40
TESTDATA = ROOT / "testdata"

# name -> (image, line rank, reference width mm)
FIXTURES = {
    "synthetic": (None, "largest", 100.0),
    "enthusiast": ("photo/enthusiast_logo.png", "largest", 100.0),
    "enthusiast_sub": ("photo/enthusiast_logo.png", "smallest", 200.0),
    "golden_tee": ("photo/logo_golden_tee.jpg", "second", 100.0),
    "fremont": ("photo/logo_hotel_fremont.webp", "smallest", 200.0),
    "fremont_tagline": ("photo/logo_hotel_fremont.webp", "largest", 80.0),
}

# name -> source-pixel crop (x0, y0, x1, y1), the image composited on white
# first. `fremont_tagline` is the EAT | STAY | PLAY band alone: the whole
# badge's 200 mm reference trace did not finish inside a lane's time box
# (#873), and at 3 to 5 mm caps the whole badge is 140 to 230 mm wide. The
# crop traces on its own (one gold colour and two black bars, no rope), so
# its classification is the crop's, not the badge's -- say so beside any
# number it gives.
CROPS = {
    "fremont_tagline": (850, 925, 1695, 1035),
}


def synthetic_text() -> np.ndarray:
    """A block word with counters (B, O, A, R, D, 8, 0), cv2's Hershey
    simplex at a stroke/cap of about 0.14 -- the same on every platform, so
    a test can pin it. Near-black on white, BGR."""
    img = np.full((260, 1500, 3), 255, np.uint8)
    cv2.putText(img, "BOARD 80", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 6.0,
                (20, 20, 20), 19, cv2.LINE_AA)
    return img


def load(name: str):
    path = FIXTURES[name][0]
    if path is None:
        return synthetic_text()
    if name in CROPS:
        from PIL import Image
        im = Image.open(TESTDATA / path).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        rgb = np.asarray(bg.convert("RGB").crop(CROPS[name]))
        return np.ascontiguousarray(rgb[:, :, ::-1])
    return str(TESTDATA / path)


def parse_flags(items) -> dict:
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        if v.lower() in ("true", "false"):
            out[k] = v.lower() == "true"
        else:
            try:
                out[k] = int(v)
            except ValueError:
                try:
                    out[k] = float(v)
                except ValueError:
                    out[k] = None if v == "None" else v
    return out


def _lines(regions, cfg):
    """Lettering regions grouped into lines by vertical overlap."""
    letters = [r for r in regions if is_lettering(r, cfg) and not r.polygon.is_empty]
    letters.sort(key=lambda r: r.polygon.bounds[1])
    lines: list[list] = []
    for r in letters:
        y0, y1 = r.polygon.bounds[1], r.polygon.bounds[3]
        for ln in lines:
            ly0 = min(q.polygon.bounds[1] for q in ln)
            ly1 = max(q.polygon.bounds[3] for q in ln)
            ov = min(y1, ly1) - max(y0, ly0)
            if ov > 0.5 * min(y1 - y0, ly1 - ly0):
                ln.append(r)
                break
        else:
            lines.append([r])
    return [ln for ln in lines if len(ln) >= 2] or lines


def _cap(line) -> float:
    return statistics.median(r.polygon.bounds[3] - r.polygon.bounds[1] for r in line)


def pick_line(regions, cfg, rank: str):
    lines = sorted(_lines(regions, cfg), key=_cap, reverse=True)
    if not lines:
        return []
    if rank == "largest":
        return lines[0]
    if rank == "second":
        return lines[1] if len(lines) > 1 else lines[0]
    return lines[-1]


def reference(image, cfg: PipelineConfig, rank: str) -> dict:
    """The source line, traced at the reference width, in units of design
    width (multiply by a run's `target_width_mm` to place it)."""
    result, _plan = digitize(image, cfg)
    line = pick_line(result.regions, cfg, rank)
    s = 1.0 / cfg.target_width_mm
    art = affinity.scale(unary_union([r.polygon for r in line]).buffer(0), s, s, origin=(0, 0))
    return dict(cap=_cap(line) * s, art=art.wkt, letters=len(line))


def _segments(plan):
    """Needle-down segments of the plan: consecutive points inside a run, and
    the hop into a run that is neither a jump nor a block's first."""
    segs = []
    for blk in plan.blocks:
        prev = None
        for run in blk.runs:
            pts = run.points
            if prev is not None and not run.jump and pts:
                segs.append((prev, tuple(pts[0]), run.shape_id))
            for a, b in zip(pts, pts[1:]):
                segs.append((tuple(a), tuple(b), run.shape_id))
            if pts:
                prev = tuple(pts[-1])
    return segs


def measure(image, cfg: PipelineConfig, ref: dict) -> dict:
    t0 = time.time()
    result, plan = digitize(image, cfg)
    w = cfg.target_width_mm
    art = affinity.scale(wkt.loads(ref["art"]), w, w, origin=(0, 0))
    parts = list(getattr(art, "geoms", [art]))
    counters = [Polygon(ring) for g in parts for ring in g.interiors]
    x0, y0, x1, y1 = art.bounds
    pad = 0.6
    box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    ox, oy = box[0], box[1]
    W = int(math.ceil((box[2] - box[0]) * PX_PER_MM))
    H = int(math.ceil((box[3] - box[1]) * PX_PER_MM))

    def px(p):
        return [int(round((p[0] - ox) * PX_PER_MM)), int(round((p[1] - oy) * PX_PER_MM))]

    def inside(p):
        return box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]

    art_m = np.zeros((H, W), np.uint8)
    hole_m = np.zeros((H, W), np.uint8)
    for g in parts:
        cv2.fillPoly(art_m, [np.array([px(p) for p in g.exterior.coords], np.int32)], 1)
    for c in counters:
        pts = np.array([px(p) for p in c.exterior.coords], np.int32)
        cv2.fillPoly(art_m, [pts], 0)
        cv2.fillPoly(hole_m, [pts], 1)
    tw = machine.thread_profile(cfg.thread_wt).width_mm
    t = max(1, int(round(tw * PX_PER_MM)))
    sewn = np.zeros((H, W), np.uint8)
    lens = []
    shapes = set()
    for a, b, sid in _segments(plan):
        if inside(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)):
            cv2.line(sewn, tuple(px(a)), tuple(px(b)), 1, t)
            lens.append(math.dist(a, b))
            shapes.add(sid)
    short = sum(1 for d in lens if d < machine.SATIN_SHORT_STITCH_AT_MM)
    art_a = int(art_m.sum())
    hole_a = int(hole_m.sum())
    shut = 0
    for c in counters:
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [np.array([px(p) for p in c.exterior.coords], np.int32)], 1)
        a = int(m.sum())
        if a and (m & (1 - sewn)).sum() < 0.5 * a:
            shut += 1
    # tier per letter of the small run that sits in the line
    tiers: dict[str, int] = {}
    kinds_by: dict[str, set] = {}
    for blk in plan.blocks:
        for run in blk.runs:
            kinds_by.setdefault(run.shape_id, set()).add(run.kind)
    # counters the small run's SEWN regions still carry (not filled by the
    # trace); a region nothing sews (a background-coloured counter shape) is
    # not ink and does not fill one
    here = [r.polygon for r in result.regions
            if r.shape_id in kinds_by and r.polygon.intersects(art)]
    traced = sum(1 for c in counters
                 if not any(p.covers(c.representative_point()) for p in here))
    per_counter = []
    for c in counters:
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [np.array([px(p) for p in c.exterior.coords], np.int32)], 1)
        a = int(m.sum())
        per_counter.append(dict(mm2=round(a / PX_PER_MM ** 2, 3),
                                open=round(float((m & (1 - sewn)).sum()) / a, 3) if a else None,
                                traced=not any(p.covers(c.representative_point()) for p in here)))
    for r in result.regions:
        if not r.polygon.intersects(art) or not inside(r.polygon.representative_point().coords[0]):
            continue
        k = kinds_by.get(r.shape_id, set())
        tier = ("satin" if stitches.SATIN in k else "fill" if stitches.FILL in k else
                "run" if (stitches.RUN in k or stitches.BEAN in k) else
                "none" if not k else "other")
        tiers[tier] = tiers.get(tier, 0) + 1
    letters = [r for r in result.regions if is_lettering(r, cfg) and r.polygon.intersects(art)]
    return dict(
        width_mm=w, cap_mm=ref["cap"] * w,
        cap_traced_mm=_cap(letters) if letters else float("nan"),
        tiers=tiers, stitches=len(lens),
        trims=sum(1 for _, r in plan.iter_runs() if r.trim),
        jumps=sum(1 for _, r in plan.iter_runs() if r.jump),
        dust=short / len(lens) if lens else float("nan"),
        covered=int((art_m & sewn).sum()) / art_a if art_a else float("nan"),
        spill=int((sewn & (1 - art_m) & (1 - hole_m)).sum()) / art_a if art_a else float("nan"),
        counters=len(counters), counters_traced=traced, counters_shut=shut,
        counter_open=int((hole_m & (1 - sewn)).sum()) / hole_a if hole_a else float("nan"),
        counter_mm2=hole_a / PX_PER_MM ** 2, per_counter=per_counter,
        seconds=round(time.time() - t0, 1),
    ), (result, plan, art)


def run_fixture(name: str, caps, flags: dict | None = None, ref: dict | None = None,
                thread_wt: int | None = None):
    _path, rank, ref_w = FIXTURES[name]
    image = load(name)
    flags = dict(flags or {})
    if thread_wt is not None:
        flags["thread_wt"] = thread_wt
    if ref is None:
        ref = reference(image, PipelineConfig(target_width_mm=ref_w), rank)
    out = []
    for cap in caps:
        cfg = PipelineConfig(target_width_mm=round(cap / ref["cap"], 2), **flags)
        m, _ = measure(image, cfg, ref)
        m.update(fixture=name, target_cap=cap, flags=flags)
        out.append(m)
    return ref, out


def fmt(m: dict) -> str:
    return (f"{m['fixture']} cap {m['target_cap']} (got {m['cap_mm']:.2f}, traced {m['cap_traced_mm']:.2f}) "
            f"w {m['width_mm']} {m['tiers']} st {m['stitches']} trims {m['trims']} dust {m['dust']:.3f} "
            f"covered {m['covered']:.3f} spill {m['spill']:.3f} counters {m['counters']} "
            f"traced {m['counters_traced']} shut {m['counters_shut']} open {m['counter_open']:.3f} "
            f"({m['counter_mm2']:.2f} mm2) {m['flags']} [{m['seconds']} s]")


def focus_box(art):
    """The bounds of the source letter holding the largest counter (the zoom
    panel's window), or None when the line has no counter."""
    best = None
    for g in getattr(art, "geoms", [art]):
        for ring in g.interiors:
            a = Polygon(ring).area
            if best is None or a > best[0]:
                best = (a, g.bounds)
    return best[1] if best else None


def render_line(plan, art, thread_mm: float, ppm: int = PX_PER_MM, pad: float = 0.8,
                box=None) -> np.ndarray:
    """The plan sewn (`stitchviz.render_design`, thread at `thread_mm`),
    cropped to the measured line (or to `box`), the SOURCE outline and its
    counters in red on top."""
    from digitizer_core import stitchviz
    from digitizer_core.adapter import plan_to_design

    d = plan_to_design(plan)
    img = stitchviz.render_design(d, px_per_mm=ppm, pad_mm=2.0, thread_mm=thread_mm)
    (_h, _w), to_px = stitchviz._frame(d["stitches"], ppm, 2.0)
    u = stitchviz.UNITS_PER_MM

    def P(x, y):   # plan mm (y down) -> design units (y up) -> pixel
        return to_px({"x": x * u, "y": -y * u})

    for g in getattr(art, "geoms", [art]):
        for ring in [g.exterior, *g.interiors]:
            pts = np.array([P(x, y) for x, y in ring.coords], np.int32)
            cv2.polylines(img, [pts], True, (40, 40, 220), 1, cv2.LINE_AA)
    x0, y0, x1, y1 = box or art.bounds
    a, b = P(x0 - pad, y0 - pad), P(x1 + pad, y1 + pad)
    xa, xb = sorted((a[0], b[0]))
    ya, yb = sorted((a[1], b[1]))
    return img[max(0, ya):yb, max(0, xa):xb].copy()


def _label(img: np.ndarray, text: str) -> np.ndarray:
    bar = np.full((30, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def _hstack(imgs, gap=12):
    h = max(i.shape[0] for i in imgs)
    out = []
    for k, i in enumerate(imgs):
        if i.shape[0] < h:
            i = np.vstack([i, np.full((h - i.shape[0], i.shape[1], 3), 255, np.uint8)])
        out.append(i)
        if k < len(imgs) - 1:
            out.append(np.full((h, gap, 3), 255, np.uint8))
    return np.hstack(out)


def _vstack(imgs, gap=16):
    w = max(i.shape[1] for i in imgs)
    out = []
    for i in imgs:
        if i.shape[1] < w:
            i = np.hstack([i, np.full((i.shape[0], w - i.shape[1], 3), 255, np.uint8)])
        out += [i, np.full((gap, w, 3), 255, np.uint8)]
    return np.vstack(out[:-1])


def sheet(name: str, ref: dict, caps, weights=(40,), ppm: int = PX_PER_MM) -> tuple[np.ndarray, list]:
    """OFF beside ON (`small_print_floor`) per cap and weight, every panel at
    `ppm` px/mm, the same scale throughout. -> (BGR sheet, metric rows)."""
    image = load(name)
    rows, metrics = [], []
    for wt in weights:
        tw = machine.thread_profile(wt).width_mm
        for cap in caps:
            w = round(cap / ref["cap"], 2)
            pair, zoom = [], []
            for on in (False, True):
                cfg = PipelineConfig(target_width_mm=w, thread_wt=wt, small_print_floor=on)
                m, (_res, plan, art) = measure(image, cfg, ref)
                m.update(fixture=name, target_cap=cap, flags={"thread_wt": wt, "small_print_floor": on})
                metrics.append(m)
                tag = f"{'ON ' if on else 'OFF'} {cap:g} mm cap, {wt} wt"
                pair.append(_label(render_line(plan, art, tw, ppm),
                                   f"{tag}: {m['counters_shut']}/{m['counters']} counters shut, "
                                   f"{m['counter_open']:.2f} open"))
                fb = focus_box(art)
                if fb is not None:
                    zoom.append(_label(render_line(plan, art, tw, 2 * ppm, pad=0.5, box=fb),
                                       f"{tag}, zoom {2 * ppm} px/mm"))
            rows.append(_hstack(pair))
            if zoom:
                rows.append(_hstack(zoom))
    out = _vstack(rows)
    title = np.full((40, out.shape[1], 3), 255, np.uint8)
    cv2.putText(title, f"{name}: cfg.small_print_floor OFF (left) vs ON (right), {ppm} px/mm, "
                f"red = source outline traced at the reference width",
                (6, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack([title, out]), metrics


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True, choices=sorted(FIXTURES))
    ap.add_argument("--caps", default="3,4,5")
    ap.add_argument("--flag", action="append")
    ap.add_argument("--ref", help="a reference JSON written by an earlier run (skips the reference run)")
    ap.add_argument("--save-ref", help="write the reference JSON here")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sheet", help="write an OFF/ON render sheet (PNG) here instead of measuring")
    ap.add_argument("--weights", default="40", help="thread weights for --sheet, e.g. 40,60")
    a = ap.parse_args(argv)
    _path, rank, ref_w = FIXTURES[a.fixture]
    ref = json.loads(Path(a.ref).read_text()) if a.ref else None
    if ref is None:
        t0 = time.time()
        ref = reference(load(a.fixture), PipelineConfig(target_width_mm=ref_w), rank)
        print(f"# {a.fixture} ref width {ref_w} -> cap {ref['cap'] * ref_w:.3f} mm "
              f"({ref['letters']} letters, {time.time() - t0:.0f} s)", flush=True)
        if a.save_ref:
            Path(a.save_ref).write_text(json.dumps(ref))
    if a.sheet:
        img, metrics = sheet(a.fixture, ref, [float(c) for c in a.caps.split(",")],
                             tuple(int(w) for w in a.weights.split(",")))
        cv2.imwrite(a.sheet, img)
        for m in metrics:
            print(json.dumps(m) if a.json else fmt(m), flush=True)
        return
    for cap in [float(c) for c in a.caps.split(",")]:
        _ref, (m,) = run_fixture(a.fixture, [cap], parse_flags(a.flag), ref)
        print(json.dumps(m) if a.json else fmt(m), flush=True)


if __name__ == "__main__":
    main()
