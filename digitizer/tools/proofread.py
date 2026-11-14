"""Proof-read one artwork by eye and against Kent's pins.

    python -m tools.proofread run  --image ART --width MM --out DIR [--garment left_chest] [--name N] [--debug]
    python -m tools.proofread pins --kit KITDIR --item C_<slug> --out DIR --name N [--radius 3]
    python -m tools.proofread summary --out DIR

`run` digitizes ART the way the Studio does (`tools.fremont_triage.
studio_request` at MM on the garment, as `tools.photo_corpus`'s worker sends
it) with `cfg.proofread` ON, in this process, and writes, all in DIR:

  N.proofread.json  the report preflight carries under `metrics["proofread"]`
                    plus the design's render frame (for pins) and, with
                    `--debug`, the raster cross-check below
  N.design.json     the design (`adapter.plan_to_design`)
  N.overlay.png     three panels on one frame: the art the pipeline traced,
                    the colour classes the proof-read read it as, and the
                    render with every finding boxed and numbered (red error,
                    orange misfire, grey explained)

`--debug` also runs the pipeline with `debug_dir` and compares the proof-
read's thread raster with the pipeline's own `stage6_stitches.png` (a
scratch renderer once skipped every run that starts with a jump): the share
of that picture's thread pixels the raster also covers (`recall`), which
should read ~1.0.

`pins` reads one item's pins from a defect-marks kit (`marks.json`, frame:
mm from the render's top-left, pad undone, `defect_marks.mark_mm`) and says,
per pin, whether a finding lies within `--radius` mm (the harness's
pre-registered 3 mm) and which. A hit table is an instrument reading on a
handful of pins (ROADMAP gate 4: no chance correction is claimed here, and n
is small).

Nothing here is committed output: DIR is meant to be gitignored
(`eye_pairs_out/`), this repo is public.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]          # digitizer/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PXMM = 10.0
PAD_MM = 2.0
SEV_BGR = {"error": (40, 40, 230), "misfire": (0, 150, 255), "explained": (150, 150, 150)}


def _cfg(width: float, garment: str, debug_dir: Path | None, extra: dict):
    from digitizer_core import PipelineConfig
    from digitizer_service.app import _parse_config
    from tools.fremont_triage import studio_request
    req = studio_request(width)
    req["target_width_mm"] = float(width)
    req["garment_id"] = garment
    cfg = PipelineConfig(**_parse_config(json.dumps(req)))
    cfg.proofread = True
    for k, v in extra.items():
        setattr(cfg, k, v)
    if debug_dir is not None:
        cfg.debug_dir = debug_dir
    return cfg, req


def render_frame(design: dict) -> dict:
    """The design's render frame: plan mm (x, y down) -> render mm (pad undone)
    is (x - x0, y + y1) with x0 = min design x / 10, y1 = max design y / 10."""
    from digitizer_core import stitchviz
    x0, x1, y0, y1 = stitchviz._bounds(design["stitches"])
    return {"x0_mm": x0 / 10.0, "y1_mm": y1 / 10.0, "w_mm": (x1 - x0) / 10.0, "h_mm": (y1 - y0) / 10.0}


def plan_to_render_mm(x: float, y: float, fr: dict) -> tuple[float, float]:
    return x - fr["x0_mm"], y + fr["y1_mm"]


def raster_check(rep_r: dict, plan, size_mm, debug_dir: Path) -> dict | None:
    """Recall of `stage6_stitches.png`'s thread pixels under the proof-read's raster."""
    png = debug_dir / "stage6_stitches.png"
    if not png.exists():
        return None
    img = cv2.imread(str(png))
    if img is None:
        return None
    scale, margin = 12, 6      # debugviz._MM_SCALE, _MM_MARGIN
    w_mm, h_mm = size_mm
    g = rep_r["grid"]
    top = rep_r["top"]
    h, w = img.shape[:2]
    # proof-read raster -> debug canvas
    k = scale / g.px
    M = np.array([[k, 0, scale * (g.x0 + w_mm / 2 + margin)],
                  [0, k, scale * (g.y0 + h_mm / 2 + margin)]], np.float64)
    ours = cv2.warpAffine((top >= 0).astype(np.uint8), M, (w, h), flags=cv2.INTER_NEAREST) > 0
    diff = np.abs(img.astype(int) - 250).sum(-1) > 60
    b, gch, r = img[..., 0].astype(int), img[..., 1].astype(int), img[..., 2].astype(int)
    jumpish = ((np.abs(r - 255) < 60) & (gch < 120) & (np.abs(b - 255) < 60)) | \
              ((np.abs(r - 120) < 40) & (np.abs(gch - 120) < 40) & (b > 200)) | \
              ((np.abs(b - 120) < 40) & (np.abs(gch - 120) < 40) & (r > 200))
    theirs = diff & ~jumpish
    near = cv2.dilate(ours.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    n = int(theirs.sum())
    return {"stage6_thread_px": n, "recall": round(float((theirs & near).sum()) / max(1, n), 4),
            "ours_px": int(ours.sum())}


def overlay(rep: dict, rasters: dict, p, design: dict, out_png: Path, title: str) -> None:
    from digitizer_core import stitchviz
    grid = rasters["grid"]
    art = rasters["art"]
    classes = rep["classes"]
    fr = render_frame(design)
    # panel 1: the traced raster in the grid's frame
    ax0, ay0, ax1, ay1 = p.art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    kk = grid.px / float(p.px_per_mm)
    M = np.array([[kk, 0, grid.px * (-cx / p.px_per_mm - grid.x0)],
                  [0, kk, grid.px * (-cy / p.px_per_mm - grid.y0)]], np.float64)
    src = cv2.warpAffine(cv2.cvtColor(p.rgb, cv2.COLOR_RGB2BGR), M, (grid.w, grid.h),
                         flags=cv2.INTER_AREA, borderValue=(255, 255, 255))
    bgm = cv2.warpAffine(np.asarray(p.bg_mask, np.uint8), M, (grid.w, grid.h),
                         flags=cv2.INTER_NEAREST, borderValue=1) > 0
    src[bgm] = (src[bgm] * 0.35 + 255 * 0.65).astype(np.uint8)
    # panel 2: the classes
    lab = np.full((grid.h, grid.w, 3), 255, np.uint8)
    for i, c in enumerate(classes):
        lab[art == i] = (c[2], c[1], c[0])
    lab[art == -2] = (200, 225, 235)
    lab[art == -3] = (255, 0, 255)
    # panel 3: the render, warped into the grid's frame
    ren = stitchviz.render_design(design, px_per_mm=grid.px, pad_mm=PAD_MM)
    # render px = (x - x0 + pad) * px ; grid px = (x - g.x0) * px
    dx = (fr["x0_mm"] - PAD_MM - grid.x0) * grid.px
    dy = (-fr["y1_mm"] - PAD_MM - grid.y0) * grid.px
    M3 = np.array([[1, 0, dx], [0, 1, dy]], np.float64)
    ren = cv2.warpAffine(ren, M3, (grid.w, grid.h), borderValue=(223, 232, 235))
    for i, f in enumerate(rep["findings"], 1):
        colr = SEV_BGR[f["severity"]]
        x0, y0 = grid.to_px(f["box_mm"][0], f["box_mm"][1])
        x1, y1 = grid.to_px(f["box_mm"][2], f["box_mm"][3])
        cv2.rectangle(ren, (x0 - 3, y0 - 3), (x1 + 3, y1 + 3), colr, 2)
        cx_, cy_ = grid.to_px(*f["at_mm"])
        cv2.circle(ren, (cx_, cy_), 4, colr, -1)
        cv2.putText(ren, f"{i}{f['kind'][:2]}", (x0, max(10, y0 - 6)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, colr, 1, cv2.LINE_AA)
        if f["kind"] == "MOVED" and f.get("produced_at_mm"):
            ax_, ay_ = grid.to_px(*f["at_mm"])
            bx_, by_ = grid.to_px(*f["produced_at_mm"])
            cv2.arrowedLine(ren, (ax_, ay_), (bx_, by_), colr, 1, tipLength=0.3)
    clean = cv2.warpAffine(stitchviz.render_design(design, px_per_mm=grid.px, pad_mm=PAD_MM), M3,
                           (grid.w, grid.h), borderValue=(223, 232, 235))
    gap = np.full((grid.h, 8, 3), 255, np.uint8)
    row = np.full((8, 2 * grid.w + 8, 3), 255, np.uint8)
    # art | render ; what the read took the art for | render with the findings
    sheet = np.vstack([np.hstack([src, gap, clean]), row, np.hstack([lab, gap, ren])])
    head = np.full((28, sheet.shape[1], 3), 255, np.uint8)
    txt = (f"{title}  unexplained {rep['unexplained']}  misfire {rep['misfires']}  explained "
           f"{rep['explained']}  tol {rep['tol_mm']} mm  {rep['counts']}")
    cv2.putText(head, txt[:220], (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.imwrite(str(out_png), np.vstack([head, sheet]))


def cmd_run(a) -> int:
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.preflight import _prepped_view, _two_tone_view, run_preflight
    from digitizer_core.stage1_prep import prep
    from digitizer_core import proofread as pr
    from digitizer_service.app import _decode
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = a.name or Path(a.image).stem
    dbg = (out / f"{name}.debug") if a.debug else None
    if dbg:
        dbg.mkdir(exist_ok=True)
    extra = {}
    for kv in a.set or ():
        k, v = kv.split("=", 1)
        extra[k] = json.loads(v)
    cfg, req = _cfg(a.width, a.garment, dbg, extra)
    data = Path(a.image).read_bytes()
    t0 = time.time()
    pixels = _decode(data)
    gen = build_generation(pixels, cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    t_plan = time.time() - t0
    pf = run_preflight(result, plan, cfg, image=pixels)
    t_pf = time.time() - t0 - t_plan
    rep = pf["metrics"].get("proofread")
    design = plan_to_design(plan, name="Digitized design")
    # the rasters again, for the picture (the same function, the same view)
    p = prep(pixels, cfg, design_class=getattr(result, "design_class", None))
    view = _two_tone_view(p, plan, cfg)
    pv = _prepped_view(view, result, cfg)
    graded = view if pv is None else pv
    t1 = time.time()
    rep2 = pr.read(graded, result, plan, cfg, want_rasters=True)
    t_read = time.time() - t1
    rasters = rep2.pop("_rasters")
    same = json.dumps(rep2, sort_keys=True, default=str) == json.dumps(rep, sort_keys=True, default=str)
    record = {"image": str(a.image), "width_mm": a.width, "garment": a.garment, "config_extra": extra,
              "class": getattr(gen, "classification_class", None),
              "design_size_mm": list(result.design_size_mm), "frame": render_frame(design),
              "timing_s": {"plan": round(t_plan, 1), "preflight": round(t_pf, 1), "proofread": round(t_read, 2)},
              "preflight_grade": pf["grade"], "preflight_score": pf["score"],
              "rerun_identical": same, "report": rep}
    if dbg:
        record["raster_check"] = raster_check(rasters, plan, result.design_size_mm, dbg)
    if a.keep:
        import pickle
        with open(out / f"{name}.job.pkl", "wb") as fh:
            pickle.dump({"result": result, "plan": plan, "graded": graded, "cfg": cfg}, fh)
    _finish(out, name, record, rasters, graded, design, f"{name} {a.width} mm")
    print(name, "grade", pf["grade"], "counts", rep["counts"], "unexplained", rep["unexplained"],
          "misfire", rep["misfires"], "explained", rep["explained"],
          "raster", record.get("raster_check"), "t", record["timing_s"], "same", same, flush=True)
    return 0


def _finish(out: Path, name: str, record: dict, rasters: dict, graded, design: dict, title: str) -> None:
    rep = record["report"]
    (out / f"{name}.proofread.json").write_text(json.dumps(record, indent=1, default=str) + "\n", encoding="utf-8")
    (out / f"{name}.design.json").write_text(json.dumps(design) + "\n", encoding="utf-8")
    top_cls = np.array([r.cls for r in rasters["runs"]] + [-1], np.int32)[rasters["top"]]
    np.savez_compressed(out / f"{name}.rasters.npz", art=rasters["art"], top_cls=top_cls)
    overlay(rep, rasters, graded, design, out / f"{name}.overlay.png", title)


def cmd_reread(a) -> int:
    """The proof-read again on a kept job (`run --keep`): no digitize."""
    import pickle
    from digitizer_core import proofread as pr
    from digitizer_core.adapter import plan_to_design
    out = Path(a.out)
    with open(out / f"{a.name}.job.pkl", "rb") as fh:
        job = pickle.load(fh)
    record = json.loads((out / f"{a.name}.proofread.json").read_text(encoding="utf-8"))
    t1 = time.time()
    rep = pr.read(job["graded"], job["result"], job["plan"], job["cfg"], want_rasters=True)
    rasters = rep.pop("_rasters")
    record["report"] = rep
    record.setdefault("timing_s", {})["proofread"] = round(time.time() - t1, 2)
    design = plan_to_design(job["plan"], name="Digitized design")
    _finish(out, a.name, record, rasters, job["graded"], design, f"{a.name} {record['width_mm']} mm")
    print(a.name, "counts", rep["counts"], "unexplained", rep["unexplained"], "misfire", rep["misfires"],
          "explained", rep["explained"], flush=True)
    return 0


def _finding_dist(f: dict, x: float, y: float) -> float:
    x0, y0, x1, y1 = f["box_mm"]
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return math.hypot(dx, dy)


def score_pins(record: dict, pins: list[dict], radius: float) -> list[dict]:
    fr = record["frame"]
    rows = []
    for k, pin in enumerate(pins, 1):
        px_, py_ = pin["x_mm"] + fr["x0_mm"], pin["y_mm"] - fr["y1_mm"]
        near = []
        for i, f in enumerate(record["report"]["findings"], 1):
            d = _finding_dist(f, px_, py_)
            if d <= radius:
                near.append((d, i, f))
        near.sort(key=lambda t: t[0])
        rows.append({"pin": k, "what": pin.get("what"), "severity": pin.get("severity"),
                     "note": pin.get("note", ""), "plan_mm": [round(px_, 2), round(py_, 2)],
                     "hit": bool(near),
                     "hits": [{"finding": i, "kind": f["kind"], "severity": f["severity"],
                               "dist_mm": round(d, 2), "explained_by": f["explained_by"]}
                              for d, i, f in near[:4]]})
    return rows


def cmd_pins(a) -> int:
    kit = Path(a.kit)
    marks = json.loads((kit / "marks.json").read_text(encoding="utf-8"))
    items = dict(marks["items"]) if isinstance(marks["items"], list) else marks["items"]
    pins = (items.get(a.item) or {}).get("pins") or []
    record = json.loads((Path(a.out) / f"{a.name}.proofread.json").read_text(encoding="utf-8"))
    rows = score_pins(record, pins, a.radius)
    chance = chance_rate(Path(a.out), a.name, record, a.radius)
    (Path(a.out) / f"{a.name}.pins.json").write_text(
        json.dumps({"pins": rows, "chance_hit_rate": chance, "radius_mm": a.radius}, indent=1) + "\n",
        encoding="utf-8")
    for r in rows:
        print(f"pin {r['pin']:>2} {'HIT ' if r['hit'] else 'miss'} {str(r['what']):<12} "
              f"{[(h['kind'], h['severity'], h['dist_mm']) for h in r['hits']]}  {r['note'][:70]}")
    print(f"{a.item}: {sum(r['hit'] for r in rows)}/{len(rows)} pins within {a.radius} mm "
          f"(a pin dropped at random on the thread would hit {chance:.2f})")
    return 0


def chance_rate(out: Path, name: str, record: dict, radius: float) -> float | None:
    """The share of the stitched area within `radius` of a finding's box: the
    hit rate of a pin dropped at random on the thread (the harness's plain
    `chance_rate` null, ROADMAP gate 4)."""
    npz = out / f"{name}.rasters.npz"
    if not npz.exists():
        return None
    thread = np.load(npz)["top_cls"] >= 0
    gx0, gy0 = record["report"]["grid_origin_mm"]
    near = np.zeros(thread.shape, np.uint8)
    for f in record["report"]["findings"]:
        x0, y0, x1, y1 = f["box_mm"]
        cv2.rectangle(near, (int((x0 - gx0) * PXMM), int((y0 - gy0) * PXMM)),
                      (int((x1 - gx0) * PXMM), int((y1 - gy0) * PXMM)), 1, -1)
    if near.any():
        k = int(round(radius * PXMM))
        near = cv2.dilate(near, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    n = int(thread.sum())
    return round(float((near.astype(bool) & thread).sum()) / n, 3) if n else None


def cmd_summary(a) -> int:
    out = Path(a.out)
    for pj in sorted(out.glob("*.proofread.json")):
        rec = json.loads(pj.read_text(encoding="utf-8"))
        rep = rec["report"]
        name = pj.name[:-len(".proofread.json")]
        pins = out / f"{name}.pins.json"
        hit = ""
        if pins.exists():
            pj_ = json.loads(pins.read_text(encoding="utf-8"))
            rows = pj_["pins"]
            hit = f"pins {sum(r['hit'] for r in rows)}/{len(rows)} chance {pj_['chance_hit_rate']}"
        print(f"{name:<28} {rec['width_mm']:>6} mm  unexpl {rep['unexplained']:>3}  misfire {rep['misfires']:>3}  "
              f"expl {rep['explained']:>3}  {rep['counts']}  {hit}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--image", required=True)
    r.add_argument("--width", type=float, required=True)
    r.add_argument("--garment", default="left_chest")
    r.add_argument("--out", required=True)
    r.add_argument("--name")
    r.add_argument("--debug", action="store_true")
    r.add_argument("--set", action="append", help="cfg field=json value, e.g. sliver_prune=true")
    r.add_argument("--keep", action="store_true", help="pickle the job for `reread`")
    rr = sub.add_parser("reread")
    rr.add_argument("--out", required=True)
    rr.add_argument("--name", required=True)
    q = sub.add_parser("pins")
    q.add_argument("--kit", required=True)
    q.add_argument("--item", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--name", required=True)
    q.add_argument("--radius", type=float, default=3.0)
    s = sub.add_parser("summary")
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"run": cmd_run, "reread": cmd_reread, "pins": cmd_pins, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
