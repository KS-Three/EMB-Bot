"""pro_pair: our digitizing of a customer logo beside the professional's file.

WHAT IT IS FOR. The one way every session puts "what we sew" next to "what
the pro sewed" for the same artwork, so two workers looking at one defect
are looking at the same pictures and the same numbers. It digitizes the art
exactly as the Studio asks for it (`tools.fremont_triage.studio_request`
through the service's own `_parse_config` / `_decode`, then
build_generation -> finish_generation(gen.fork()) -> plan_stitches), reads
the pro's machine file through `tools.pro_parity.pairframe.design_for`, and
renders both through `digitizer_core.stitchviz.render_design` (the Studio's
previewer). Outputs in --out: sheet_whole.png (art | ours | pro, 20 px/mm),
sheet_band.png or sheet_crop.png (40 px/mm), stats.json (ours: stitches,
trims, colours, regions, warnings, preflight; the pro's stitches, trims and
colour changes as pystitch reads them), band_meta.jsonl (one row per region
in the band/crop), and per --shapes id spines_<id>.png + runs_<id>.txt.

WHAT IT DOES NOT DO. No registration (each side is drawn in its own frame;
a band is a fraction of each render's own height, a crop is mm from the
top-left of each design's own stitch extents), no scoring, no IoU, no
verdict. `tools/pro_parity/` (pairframe, scorecard, overlay) does that.

  python -m tools.pro_pair --art A --pro P --width MM [--garment hat_front]
      [--out DIR] [--band Y0 Y1 | --crop X0 Y0 X1 Y1] [--shapes id,id]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

PPM = 20.0          # whole-design renders
PPM_CROP = 40.0     # band / crop renders
PAD_MM = 2.0        # stitchviz.render_design's default pad
DEFAULT_BAND = (0.80, 1.0)

#: Meta keys a lettering investigation reads (the probe's filter, verbatim).
META_TERMS = ("text", "letter", "word", "cluster", "rescued", "stray", "tier", "guard", "ink",
              "stitched", "technique", "small", "counter", "hold", "column", "run", "satin",
              "tag", "group", "detail", "skip", "declin")
LETTERING_KEYS = ("text_cluster_id", "lettering_group", "word_id", "bean_letter",
                  "small_text_stray", "rescued_small_shape", "detail_spokes")


# ------------------------------------------------------------------ pieces
def request(width_mm: float, garment_id: str = "hat_front", extra: dict | None = None) -> dict:
    """The Studio's /digitize config at `width_mm`, `garment_id` swapped in,
    and `extra` (a customer option the Studio would send, e.g.
    `{"sew_enclosed_white": true}`) merged over it."""
    from tools.fremont_triage import studio_request
    req = studio_request(width_mm)
    req["garment_id"] = garment_id
    req.update(extra or {})
    return req


def select_regions(regions, band=None, crop=None) -> list:
    """Regions in a window, in input order. `band` = (y0frac, y1frac) of the
    regions' own y extent (mm, y-down): a region is IN when its top is at or
    below y0 and its bottom at or above y1 -- it lies inside the band (with
    y1frac 1.0 this is the probe's `top >= cut`). `crop` = (x0, y0, x1, y1)
    plan mm: a region is IN when its box meets the window. Neither: all."""
    regions = list(regions)
    if band is not None and crop is not None:
        raise ValueError("band and crop are exclusive")
    if band is not None and regions:
        ys = [r.polygon.bounds[1] for r in regions] + [r.polygon.bounds[3] for r in regions]
        lo, hi = min(ys), max(ys)
        c0, c1 = lo + band[0] * (hi - lo), lo + band[1] * (hi - lo)
        eps = 1e-9
        return [r for r in regions
                if r.polygon.bounds[1] >= c0 - eps and r.polygon.bounds[3] <= c1 + eps]
    if crop is not None:
        x0, y0, x1, y1 = crop
        return [r for r in regions
                if not (r.polygon.bounds[2] < x0 or r.polygon.bounds[0] > x1
                        or r.polygon.bounds[3] < y0 or r.polygon.bounds[1] > y1)]
    return regions


def pro_counts(path) -> dict:
    """The pro's file as pystitch reads it: STITCH / TRIM / COLOR_CHANGE
    records and the stitch extents' width and height in mm."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    cmds = [c & m for *_xy, c in pat.stitches]
    x0, y0, x1, y1 = pat.extents()
    return {"file": Path(path).name,
            "stitches": sum(1 for c in cmds if c == pystitch.STITCH),
            "trims": sum(1 for c in cmds if c == pystitch.TRIM),
            "colour_changes": sum(1 for c in cmds if c == pystitch.COLOR_CHANGE),
            "thread_colours": len(pat.threadlist),
            "width_mm": round((x1 - x0) / 10.0, 2), "height_mm": round((y1 - y0) / 10.0, 2)}


@dataclass
class Digitized:
    art: Path
    width_mm: float
    garment_id: str
    data: bytes
    cfg: object
    gen: object
    result: object
    plan: object
    design: dict
    secs: float


def digitize(art, width_mm: float, garment_id: str = "hat_front",
             extra: dict | None = None) -> Digitized:
    """The Studio's request, through the service's parser, then the pipeline
    the product runs. Identical to the director's proseal_run.py."""
    from digitizer_service.app import _decode as svc_decode, _parse_config
    from digitizer_core import PipelineConfig
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    art = Path(art)
    data = art.read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps(request(width_mm, garment_id, extra))))
    pixels = svc_decode(data)
    t = time.time()
    gen = build_generation(pixels, cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    secs = time.time() - t
    design = plan_to_design(plan, name=art.stem)
    return Digitized(art, float(width_mm), garment_id, data, cfg, gen, result, plan, design, secs)


def _stats(d: Digitized, pro: Path) -> dict:
    from digitizer_core.preflight import run_preflight
    plan, result = d.plan, d.result
    stats = {
        "art": d.art.name, "width_mm": d.width_mm, "garment_id": d.garment_id,
        "secs": round(d.secs, 1),
        "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
        "colours": len(d.design.get("colors", [])),
        "regions": len(result.regions),
        "warnings": [w.get("code") for w in getattr(plan, "warnings", [])],
        "lettering": {}, "tiers": {},
    }
    for r in result.regions:
        m = getattr(r, "meta", {}) or {}
        key = str(m.get("tier") or m.get("technique") or getattr(r, "technique", None) or "?")
        stats["tiers"][key] = stats["tiers"].get(key, 0) + 1
        for k in LETTERING_KEYS:
            if k in m:
                stats["lettering"][k] = stats["lettering"].get(k, 0) + 1
    try:
        pf = run_preflight(result, plan, d.cfg)
        stats["preflight"] = {k: pf.get(k) for k in ("grade", "findings", "metrics")}
    except Exception as e:  # noqa: BLE001 -- a broken preflight is a finding, not a crash
        stats["preflight"] = {"grade": None, "findings": [],
                              "error": f"{type(e).__name__}: {e}"[:300]}
    stats["pro"] = pro_counts(pro)
    return stats


# ------------------------------------------------------------------ images
def _art_ink(path: Path):
    """The art on white (alpha composited), cut to its ink box (grey < 200)."""
    import cv2
    import numpy as np
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im is None:
        raise SystemExit(f"unreadable art: {path}")
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    elif im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        im = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(g < 200)
    if not len(xs):
        return im
    return im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _scaled(img, width_mm: float, ppm: float, interp):
    import cv2
    s = (width_mm * ppm) / img.shape[1]
    return cv2.resize(img, None, fx=s, fy=s, interpolation=interp)


def _label(img, text):
    import cv2
    im = img.copy()
    cv2.rectangle(im, (0, 0), (im.shape[1], 34), (255, 255, 255), -1)
    cv2.putText(im, text, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
    return im


def _hstack(imgs, gap=24):
    import numpy as np
    h = max(i.shape[0] for i in imgs)
    cols = []
    for i in imgs:
        pad = np.full((h, i.shape[1], 3), 255, np.uint8)
        pad[: i.shape[0], : i.shape[1]] = i
        cols += [pad, np.full((h, gap, 3), 255, np.uint8)]
    return np.hstack(cols[:-1])


def _vstack(imgs, gap=16):
    import numpy as np
    w = max(i.shape[1] for i in imgs)
    rows = []
    for i in imgs:
        p = np.full((i.shape[0], w, 3), 255, np.uint8)
        p[:, : i.shape[1]] = i
        rows += [p, np.full((gap, w, 3), 255, np.uint8)]
    return np.vstack(rows[:-1])


def _crop_px(img, crop_mm, pad_mm, ppm):
    """`crop_mm` (x0, y0, x1, y1) from the top-left of the drawn extents."""
    x0, y0, x1, y1 = (int(round((v + pad_mm) * ppm)) for v in crop_mm)
    h, w = img.shape[:2]
    return img[max(0, y0):max(1, min(h, y1)), max(0, x0):max(1, min(w, x1))]


def _design_top_left_mm(design: dict):
    """Plan-frame mm (x, y-down) of the render's top-left, before the pad:
    the same box `stitchviz._frame` draws from (stitches and jumps)."""
    from digitizer_core import stitchviz
    x0, _x1, _y0, y1 = stitchviz._bounds(design.get("stitches") or [])
    return x0 / 10.0, -y1 / 10.0


# ------------------------------------------------------------------ meta
def _run_kinds(plan) -> dict:
    kinds: dict[str, dict] = {}
    for _blk, run in plan.iter_runs():
        d = kinds.setdefault(str(run.shape_id), {})
        k = str(run.kind)
        d[k] = d.get(k, 0) + len(run.points or [])
    return kinds


def _meta_row(r, kinds: dict) -> dict:
    from shapely.geometry import Polygon
    b = r.polygon.bounds
    m = dict(getattr(r, "meta", {}) or {})
    spines = m.pop("bean_letter_spines", None)
    return {
        "id": r.shape_id, "thread": r.thread_number,
        "bbox": [round(v, 2) for v in b],
        "area": round(r.polygon.area, 3), "holes": len(r.polygon.interiors),
        "hole_areas": [round(Polygon(i).area, 3) for i in r.polygon.interiors],
        "bean_spines": len(spines) if spines else None,
        "meta": {k: v for k, v in m.items() if any(t in k for t in META_TERMS)},
        "runs": kinds.get(str(r.shape_id)),
    }


def _shape_outputs(d: Digitized, sid: str, out: Path) -> None:
    """spines_<id>.png: the source at 40 px/mm with the shape's outline
    (green) and its bean spines (red, points blue). runs_<id>.txt: every
    plan run of the shape, plus any other run lying (>50% of points) in its
    box padded 0.3 mm, with block, thread, shape, kind, role and points."""
    import cv2
    import numpy as np
    from digitizer_core.legibility import _plan_frame
    regs = {r.shape_id: r for r in d.result.regions}
    if sid not in regs:
        (out / f"runs_{sid}.txt").write_text(f"{sid}: no such region\n", encoding="utf-8")
        return
    r = regs[sid]
    p = d.gen.p
    cx, cy, ppm = _plan_frame(p)
    sp = r.meta.get("bean_letter_spines") or []
    x0, y0, x1, y1 = r.polygon.bounds
    pad = 0.6
    X0, Y0 = int((x0 - pad) * ppm + cx), int((y0 - pad) * ppm + cy)
    X1, Y1 = int(np.ceil((x1 + pad) * ppm + cx)), int(np.ceil((y1 + pad) * ppm + cy))
    X0, Y0 = max(0, X0), max(0, Y0)
    crop = p.rgb[Y0:Y1, X0:X1]
    scale = PPM_CROP / ppm
    im = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), None, fx=scale, fy=scale,
                    interpolation=cv2.INTER_NEAREST)

    def to_px(pt):
        return (int(round((pt[0] * ppm + cx - X0) * scale)), int(round((pt[1] * ppm + cy - Y0) * scale)))
    ring = np.array([to_px(q) for q in r.polygon.exterior.coords], np.int32)
    cv2.polylines(im, [ring], True, (0, 200, 0), 1)
    for s in sp:
        pts = np.array([to_px(q) for q in s], np.int32)
        cv2.polylines(im, [pts], False, (0, 0, 255), 2)
        for q in pts:
            cv2.circle(im, (int(q[0]), int(q[1])), 3, (255, 0, 0), -1)
    cv2.imwrite(str(out / f"spines_{sid}.png"), im)

    lines = [f"{sid} thread {r.thread_number} bbox {tuple(round(v, 2) for v in r.polygon.bounds)} "
             f"holes {len(r.polygon.interiors)} cluster {r.meta.get('text_cluster_id')} "
             f"ink_stroke {r.meta.get('ink_stroke_mm')} spines {len(sp)}"]
    for i, s in enumerate(sp):
        a = np.asarray(s, np.float64)
        ln = float(np.hypot(*np.diff(a, axis=0).T).sum()) if len(a) > 1 else 0.0
        lines.append(f"  spine {i}: {len(a)} pts, {ln:.2f} mm")
    for bi, blk in enumerate(d.plan.blocks):
        for run in blk.runs:
            pts = np.asarray(run.points, np.float64)
            if not len(pts):
                continue
            inside = ((pts[:, 0] >= x0 - 0.3) & (pts[:, 0] <= x1 + 0.3)
                      & (pts[:, 1] >= y0 - 0.3) & (pts[:, 1] <= y1 + 0.3))
            if run.shape_id == sid or inside.mean() > 0.5:
                lines.append(
                    f"  blk{bi} {blk.thread_number} {run.shape_id} {run.kind!s:8s} "
                    f"role={run.role!r:14s} pts={len(pts):3d} jump={run.jump} trim={run.trim} "
                    f"x {pts[:, 0].min():.2f}-{pts[:, 0].max():.2f} "
                    f"y {pts[:, 1].min():.2f}-{pts[:, 1].max():.2f}")
    (out / f"runs_{sid}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ driver
def run(args, d: Digitized) -> int:
    import cv2
    from digitizer_core import stitchviz
    from digitizer_core.export import write_dst
    from tools.pro_parity import pairframe
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pro = Path(args.pro)
    write_dst(d.plan, out / "ours.dst")

    stats = _stats(d, pro)
    (out / "stats.json").write_text(json.dumps(stats, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "preflight"}, default=str))

    # pairframe.design_for falls back to prep_all.GREYS when the file carries
    # no thread colours (a DST never does), so a colourless pro file still draws
    pro_design = pairframe.design_for(pro, None, None, pro.stem)
    ours_img = stitchviz.render_design(d.design, px_per_mm=PPM)
    pro_img = stitchviz.render_design(pro_design, px_per_mm=PPM)
    ink = _art_ink(d.art)
    W = d.width_mm
    art_img = _scaled(ink, W, PPM, cv2.INTER_AREA)
    pc = stats["pro"]
    cv2.imwrite(str(out / "sheet_whole.png"), _hstack([
        _label(art_img, f"art, {W} mm wide"),
        _label(ours_img, f"ours: {stats['stitches']} st, {stats['trims']} trims"),
        _label(pro_img, f"pro: {pc['stitches']} st, {pc['trims']} trims")]))

    ours_hi = stitchviz.render_design(d.design, px_per_mm=PPM_CROP)
    pro_hi = stitchviz.render_design(pro_design, px_per_mm=PPM_CROP)
    art_hi = _scaled(ink, W, PPM_CROP, cv2.INTER_CUBIC)
    if args.crop is not None:
        cm = tuple(args.crop)
        tiles = [_crop_px(art_hi, cm, 0.0, PPM_CROP), _crop_px(ours_hi, cm, PAD_MM, PPM_CROP),
                 _crop_px(pro_hi, cm, PAD_MM, PPM_CROP)]
        name = "sheet_crop.png"
        ox, oy = _design_top_left_mm(d.design)
        sel = select_regions(d.result.regions,
                             crop=(cm[0] + ox, cm[1] + oy, cm[2] + ox, cm[3] + oy))
    else:
        b0, b1 = args.band
        def band(im):
            h = im.shape[0]
            return im[int(h * b0):max(int(h * b0) + 1, int(h * b1)), :]
        tiles = [band(art_hi), band(ours_hi), band(pro_hi)]
        name = "sheet_band.png"
        sel = select_regions(d.result.regions, band=(b0, b1))
    cv2.imwrite(str(out / name), _vstack([_label(t, s) for t, s in zip(tiles, ("art", "ours", "pro"))]))

    kinds = _run_kinds(d.plan)
    rows = sorted((_meta_row(r, kinds) for r in sel), key=lambda row: row["bbox"][0])
    (out / "band_meta.jsonl").write_text("".join(json.dumps(r, default=str) + "\n" for r in rows),
                                         encoding="utf-8")
    for sid in [s for s in (args.shapes or "").split(",") if s]:
        _shape_outputs(d, sid, out)
    print("wrote", sorted(p.name for p in out.iterdir()))
    return 0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.pro_pair",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--art", required=True, type=Path, help="customer artwork")
    ap.add_argument("--pro", required=True, type=Path, help="the pro's machine file (DST/PES/...)")
    ap.add_argument("--width", required=True, type=float, help="target width, mm")
    ap.add_argument("--garment", default="hat_front", help="Studio garment_id (hat_front, left_chest, ...)")
    ap.add_argument("--out", type=Path, default=Path("../scratch_pro_pair"))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--band", nargs=2, type=float, default=DEFAULT_BAND, metavar=("Y0FRAC", "Y1FRAC"))
    g.add_argument("--crop", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"),
                   help="mm from the top-left of each design's stitch extents")
    ap.add_argument("--shapes", default="", help="comma-separated region ids for spines/runs dumps")
    ap.add_argument("--config", default="", help="JSON merged over the Studio request, "
                    "e.g. '{\"sew_enclosed_white\": true}'")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    extra = json.loads(args.config) if args.config else None
    return run(args, digitize(args.art, args.width, args.garment, extra))


if __name__ == "__main__":
    raise SystemExit(main())
