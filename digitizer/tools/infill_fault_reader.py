"""In-fill reader: WHERE an empty space of the art is stitched unlike its siblings.

    python -m tools.infill_fault_reader run --corpus-run DIR --photos DIR --out DIR --only C_<slug> [--tree DIGITIZER]
    python -m tools.infill_fault_reader run --pro-run DIR --out DIR --only L_<slug> [--tree DIGITIZER]
    python -m tools.fault_reader_harness score --fault infill --marks M --flags DIR --prefix C_ ...

The third reader scored by `tools.fault_reader_harness` against Kent's pins,
for the same kind of feature stitched in some places and not in others. His
largest note of that family (`C_kanji_seal`, sitting 2: "#1-#28 extra
in-fill, some empty spaces have it while others don't") was read first, at
the stitches (`docs/infill-fault-reader-2026-11-11/preregistration.md`): at
all 28 pins, and at `C_devanagari_logo` pins 1, 5 and 6, the top thread is
WHITE satin over pixels the source art leaves TRANSPARENT, where stage 1's
`bg_mask` reads foreground: `sew_enclosed_white` sews enclosed background it
takes for a body or field and leaves what it takes for a letter counter open
(`.claude/memory/enclosed-white-like-pro-2026-10-23.md`), and on seal script
that split falls on spaces Kent sees as alike.

So the candidate features are the art's EMPTY SPACES, read from the source
art itself and never from `bg_mask` (whose miss is the fault): pixels whose
alpha is under half where the art has an alpha channel, else pixels within
`BG_TOL` of the colour of the art's outer frame. Each 4-connected empty
space is one member of one group (all the empty spaces of the design), and
two treatments are read for each, on our render's own rasters (top thread
colour class and top run kind, every filament drawn in sew order):

  1. COVER: `infill` when at least `SEWN_FRAC` of its interior (pixels more
     than `INSET_MM` inside it) carries thread of a colour other than the
     thread just outside it; `bare` when under `SEWN_FRAC` carries thread.
     Not judged: `closed` (covered in the surrounding ink's own colour: a
     counter lost, the letter reader's fault) and `matched` (sewn in a thread
     within `BG_TOL` of the art's own empty colour, as a white field on a
     white page; alpha art has no empty colour, so never). The group's
     treatment is the one with more interior area (in practice the outer
     background, bare); every judged member treated otherwise is flagged,
     strength = its interior area, mm2.
  2. RIM: for BARE enclosed spaces (openings showing fabric; not touching the
     render's frame, not the largest space), `outlined` when at least `OUTLINED` of the band within
     `RIM_MM` of its edge is topped by a line run (`run`, `bean`, `border`),
     `plain` at most `PLAIN`; the group's treatment is the one with more rim
     length; the others are flagged, strength = rim length, mm.

Flags sit at each flagged space's deepest interior point, in the pins' mm
frame. The candidate set (written beside the flags for the harness's
candidate nulls) is every judged space but the largest: the places this
reader could flag. Fill direction, stitch type inside ink, thread colour and
shape are NOT read (the emoji's leg, the feet, the wheel handles).

The worker re-runs the job at `--tree` and refuses unless the stitches equal
the stored design's (`tools.fault_reader_jobs`). Output per item, all in the
gitignored out dir: `<item>.flags.json` (harness format plus `candidates`),
`<item>.mask.npz` (`mask` = thread pixels, `cand` = candidate interiors) and
`<item>.labels.npz` (empty, thread, kind rasters). No picture.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]            # digitizer/
PXMM = 12.0                                           # the review render's scale (pins' frame)
PAD_MM = 2.0
THREAD_MM = 0.4                                       # == stitchviz.THREAD_MM (asserted by the worker)
INSET_MM = 0.5 * THREAD_MM                            # interior = this far inside a space
MIN_SPACE_MM2 = 0.25                                  # a judged space's interior: a 0.5 x 0.5 mm patch
SEWN_FRAC = 0.5                                       # interior share carrying thread: sewn
SURROUND_MM = 0.6                                     # the ring read for "the thread just outside"
RIM_MM = THREAD_MM                                    # rim band half-width
OUTLINED = 0.25                                       # rim share topped by a line run: outlined
PLAIN = 0.05                                          # ... at most this: plain
BG_TOL = 32.0                                         # RGB distance to the frame colour: empty (no alpha)
ALPHA_EMPTY = 128                                     # alpha under this: empty
REG_MIN = 0.9                                         # share of bg_mask the raw art must call empty
KINDS = ("fill", "satin", "run", "bean", "border", "travel", "underlay")
LINE_KINDS = ("run", "bean", "border")
NO_KIND = 255
FOUR = ndi.generate_binary_structure(2, 1)
EIGHT = np.ones((3, 3), bool)


# ------------------------------------------------------------ pure helpers ----

def to_mm(xy_px, px_per_mm: float = PXMM, pad_mm: float = PAD_MM):
    """Render pixel (x, y) -> the pins' frame (`defect_marks.mark_mm`)."""
    return round(float(xy_px[0]) / px_per_mm - pad_mm, 2), round(float(xy_px[1]) / px_per_mm - pad_mm, 2)


def empty_from_art(rgb: np.ndarray, alpha: np.ndarray | None = None, bg_tol: float = BG_TOL) -> np.ndarray:
    """The art's empty pixels: alpha under half where the art has a real alpha
    channel (any pixel under `ALPHA_EMPTY`), else within `bg_tol` of the
    median colour of the art's outer 2-pixel frame."""
    if alpha is not None and (alpha < ALPHA_EMPTY).any():
        return alpha < ALPHA_EMPTY
    rgb = np.asarray(rgb, np.float32)
    ring = np.concatenate([rgb[:2].reshape(-1, 3), rgb[-2:].reshape(-1, 3),
                           rgb[:, :2].reshape(-1, 3), rgb[:, -2:].reshape(-1, 3)])
    bg = np.median(ring, 0)
    return np.sqrt(((rgb - bg[None, None, :]) ** 2).sum(-1)) <= bg_tol


def _mode(v: np.ndarray) -> int:
    vals, cnt = np.unique(v, return_counts=True)
    return int(vals[np.argmax(cnt)])


def read_spaces(empty: np.ndarray, thr: np.ndarray, kind: np.ndarray, px_per_mm: float = PXMM,
                pad_mm: float = PAD_MM, class_rgb=None, empty_rgb=None):
    """-> (flags, candidates, cand_mask, members). `empty` bool (art empty, in
    the render grid), `thr` int (top thread class, -1 bare), `kind` uint8
    (top run kind index into `KINDS`, `NO_KIND` bare). `class_rgb` the thread
    classes' RGB and `empty_rgb` the art's empty colour (None for alpha art):
    a space sewn in a thread within `BG_TOL` of the art's own empty colour is
    `matched` (the thread draws what the art shows there: a white field on a
    white page), not in-fill, and is not judged."""
    H, W = empty.shape
    lab, n = ndi.label(empty, FOUR)
    dt = ndi.distance_transform_edt(np.pad(empty, 1, constant_values=False))[1:-1, 1:-1]
    interior_all = dt > INSET_MM * px_per_mm
    line_idx = [KINDS.index(k) for k in LINE_KINDS]
    sur_r = max(1, int(round(SURROUND_MM * px_per_mm)))
    rim_r = max(1, int(round(RIM_MM * px_per_mm)))
    mem = []
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None:
            continue
        pad = max(sur_r, rim_r) + 1
        y0, y1 = max(0, sl[0].start - pad), min(H, sl[0].stop + pad)
        x0, x1 = max(0, sl[1].start - pad), min(W, sl[1].stop + pad)
        m = lab[y0:y1, x0:x1] == i
        inner = m & interior_all[y0:y1, x0:x1]
        area = float(inner.sum()) / px_per_mm ** 2
        if area < MIN_SPACE_MM2:
            continue
        t = thr[y0:y1, x0:x1]
        k = kind[y0:y1, x0:x1]
        sewn = float((t[inner] >= 0).mean())
        if sewn >= SEWN_FRAC:
            inside = _mode(t[inner][t[inner] >= 0])
            ring = ndi.binary_dilation(m, EIGHT, iterations=sur_r) & ~m & (t >= 0)
            around = _mode(t[ring]) if ring.any() else -1
            cover = "infill" if inside != around else "closed"
            if cover == "infill" and empty_rgb is not None and class_rgb is not None and                     float(np.linalg.norm(np.subtract(class_rgb[inside], empty_rgb))) <= BG_TOL:
                cover = "matched"
        else:
            cover = "bare"
        out_band = ndi.binary_dilation(m, EIGHT, iterations=rim_r) & ~m
        in_band = m & (dt[y0:y1, x0:x1] <= rim_r)
        band = out_band | in_band
        line = float(np.isin(k[band], line_idx).mean()) if band.any() else 0.0
        rim = "outlined" if line >= OUTLINED else "plain" if line <= PLAIN else None
        touches = sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == H or sl[1].stop == W
        ys, xs = np.nonzero(inner)
        j = int(np.argmax(dt[y0:y1, x0:x1][ys, xs]))
        mem.append({"id": i, "px": (float(xs[j] + x0), float(ys[j] + y0)), "area_mm2": round(area, 3),
                    "cover": cover, "sewn_frac": round(sewn, 3), "rim": rim, "rim_line_frac": round(line, 3),
                    "rim_mm": round(float(band.sum()) / px_per_mm ** 2 / (2 * RIM_MM), 2),
                    "touches_frame": bool(touches), "box": (y0, y1, x0, x1)})
    largest = max(mem, key=lambda r: r["area_mm2"])["id"] if mem else None
    flags = []
    judged = [r for r in mem if r["cover"] in ("infill", "bare")]
    by = {c: sum(r["area_mm2"] for r in judged if r["cover"] == c) for c in ("infill", "bare")}
    if by["infill"] and by["bare"]:
        ref = max(by, key=by.get)
        for r in judged:
            if r["cover"] != ref:
                flags.append(_flag(r, "cover", r["area_mm2"], ref, px_per_mm, pad_mm))
    rims = [r for r in mem if r["rim"] and r["cover"] == "bare" and not r["touches_frame"]
            and r["id"] != largest]
    by = {c: sum(r["rim_mm"] for r in rims if r["rim"] == c) for c in ("outlined", "plain")}
    if by["outlined"] and by["plain"]:
        ref = max(by, key=by.get)
        for r in rims:
            if r["rim"] != ref:
                flags.append(_flag(r, "rim", r["rim_mm"], ref, px_per_mm, pad_mm))
    # the places either rule could flag: judged spaces (the rim rule reads a
    # subset of the bare ones), but the largest, which sets the cover group
    cands = [r for r in mem if r["id"] != largest and r["cover"] in ("infill", "bare")]
    cand_mask = np.zeros_like(empty, bool)
    for r in cands:
        y0, y1, x0, x1 = r["box"]
        cand_mask[y0:y1, x0:x1] |= (lab[y0:y1, x0:x1] == r["id"]) & interior_all[y0:y1, x0:x1]
    candidates = []
    for r in cands:
        x, y = to_mm(r["px"], px_per_mm, pad_mm)
        candidates.append({"x_mm": x, "y_mm": y, "space": r["id"], "area_mm2": r["area_mm2"],
                           "cover": r["cover"], "rim": r["rim"]})
    flags.sort(key=lambda f: (-f["strength"], f["x_mm"], f["y_mm"]))
    for r in mem:
        r.pop("box")
    return flags, candidates, cand_mask, mem


def _flag(r: dict, kind: str, strength: float, ref: str, px_per_mm: float, pad_mm: float) -> dict:
    x, y = to_mm(r["px"], px_per_mm, pad_mm)
    return {"x_mm": x, "y_mm": y, "kind": kind, "strength": round(float(strength), 3), "space": r["id"],
            "treatment": r["cover"] if kind == "cover" else r["rim"], "group": ref,
            "area_mm2": r["area_mm2"], "sewn_frac": r["sewn_frac"], "rim_line_frac": r["rim_line_frac"]}


# ------------------------------------------------------------------ worker ----

WORKER = r'''
import hashlib, json, sys
spec = json.loads(sys.argv[1])
sys.path.insert(0, spec["tree"])
import cv2
import numpy as np
from digitizer_core import PipelineConfig, stitchviz
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.adapter import plan_to_design
from digitizer_core.stitchviz import render_design
from digitizer_service.app import _decode, _parse_config
from tools import pro_baseline as pb
assert stitchviz.THREAD_MM == spec["thread_mm"], ("THREAD_MM moved", stitchviz.THREAD_MM)
stored = json.load(open(spec["job"], encoding="utf-8"))
art = spec.get("art") or pb.resolve(pb.JOBS[spec["slug"]][2])
data = open(art, "rb").read()
cfg = PipelineConfig(**_parse_config(json.dumps(stored["_meta"]["config_sent"])))
pixels = _decode(data)
gen = build_generation(pixels, cfg, exif_source=data)
result = finish_generation(gen.fork(), cfg)
plan = plan_stitches(result, cfg)
design = plan_to_design(plan, name="Digitized design")
def h(st): return hashlib.sha256(json.dumps([[s["x"], s["y"], s["type"]] for s in st]).encode()).hexdigest()
same = h(design["stitches"]) == h(stored["design"]["stitches"])
d = stored["design"]
cfgs = stored["_meta"]["config_sent"]
fabric = tuple(reversed(cfgs.get("garment_rgb") or [235, 232, 223]))
img = render_design(d, px_per_mm=spec["pxmm"], fabric_bgr=fabric, pad_mm=spec["pad"])
mask = (np.abs(img.astype(int) - np.array(fabric)[None, None, :]).sum(-1) > 0)
classes = spec["classes"]
kinds = spec["kinds"]
# thread and run kind at the top of each pixel: every filament at
# render_design's own width and endpoints, in sew order, no anti-alias
(H, W), to_px = stitchviz._frame(d["stitches"], spec["pxmm"], spec["pad"])
tw = max(2, int(round(stitchviz.THREAD_MM * spec["pxmm"])))
cls_of = [int(np.argmin([sum((a - b) ** 2 for a, b in zip((c["r"], c["g"], c["b"]), k)) for k in classes]))
          for c in d["colors"]]
kind_of = {}
for r in d.get("runs") or []:
    v = kinds.index(r["kind"]) if r["kind"] in kinds else 254
    for i in range(int(r["i0"]), int(r["i1"]) + 1):
        kind_of[i] = v
lab = np.full((H, W), 255, np.uint8)
kl = np.full((H, W), 255, np.uint8)
ci, prev = 0, None
for i, s_ in enumerate(d["stitches"]):
    t = s_.get("type")
    if t == "color":
        ci += 1
        prev = None
        continue
    if t != "stitch":
        prev = None
        continue
    q = to_px(s_)
    if prev is not None and prev != q:
        cv2.line(lab, prev, q, cls_of[min(ci, len(cls_of) - 1)], tw, cv2.LINE_8)
        cv2.line(kl, prev, q, kind_of.get(i, 254), tw, cv2.LINE_8)
    prev = q
thr = np.where(lab == 255, -1, lab.astype(np.int16)).astype(np.int16)
# the art's EMPTY pixels from the source art itself (alpha, else the frame
# colour), resized onto the prepped raster, then into the render grid
p = gen.p
ph, pw = p.rgb.shape[:2]
src = pixels
alpha = src[:, :, 3] if src.ndim == 3 and src.shape[2] == 4 else None
rgb_raw = cv2.cvtColor(np.ascontiguousarray(src[:, :, :3]), cv2.COLOR_BGR2RGB) if src.ndim == 3 \
    else cv2.cvtColor(src, cv2.COLOR_GRAY2RGB)
sx, sy = pw / src.shape[1], ph / src.shape[0]
assert abs(sx - sy) <= 0.01 * max(sx, sy), ("prep is not a plain resize of the art", sx, sy)
ALPHA_EMPTY, BG_TOL = spec["alpha_empty"], spec["bg_tol"]
if alpha is not None and (alpha < ALPHA_EMPTY).any():
    emp = alpha < ALPHA_EMPTY
    how = "alpha"
    emp_rgb = None
else:
    f = rgb_raw.astype(np.float32)
    ring = np.concatenate([f[:2].reshape(-1, 3), f[-2:].reshape(-1, 3), f[:, :2].reshape(-1, 3), f[:, -2:].reshape(-1, 3)])
    bg = np.median(ring, 0)
    emp = np.sqrt(((f - bg[None, None, :]) ** 2).sum(-1)) <= BG_TOL
    how = "frame colour %s" % [int(v) for v in bg]
    emp_rgb = [float(v) for v in bg]
emp_p = cv2.resize(emp.astype(np.float32), (pw, ph), interpolation=cv2.INTER_LINEAR) >= 0.5
bgm = np.asarray(p.bg_mask, bool)
reg = float(emp_p[bgm].mean()) if bgm.any() else float("nan")
ax0, ay0, ax1, ay1 = p.art_bbox
cx, cy, ppm = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0, float(p.px_per_mm)
st = d["stitches"]
xs = [s["x"] for s in st if s.get("type") in ("stitch", "jump")]
ys = [s["y"] for s in st if s.get("type") in ("stitch", "jump")]
x0, y1 = min(xs) / 10.0, max(ys) / 10.0
kk = spec["pxmm"] / ppm
M = np.array([[kk, 0, spec["pxmm"] * (-cx / ppm - x0 + spec["pad"])],
              [0, kk, spec["pxmm"] * (-cy / ppm + y1 + spec["pad"])]], np.float64)
empty = cv2.warpAffine(emp_p.astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderValue=1.0) >= 0.5
np.savez_compressed(spec["labels"], empty=empty, thread=thr, kind=kl)
np.savez_compressed(spec["mask"], mask=mask)
json.dump({"same_stitches": same, "stored_sha": h(stored["design"]["stitches"]),
           "rerun_sha": h(design["stitches"]), "img_w": int(W), "img_h": int(H),
           "art_px_per_mm": ppm, "empty_from": how, "empty_rgb": emp_rgb, "bg_mask_empty_share": reg,
           "bg_frac": float(bgm.mean()), "art_scale": [sx, sy]},
          open(spec["out"], "w", encoding="utf-8"))
'''


def run(items: list[str], out: Path, tree: Path, pro_run: Path | None = None,
        corpus_run: Path | None = None, photos: Path | None = None, timeout: float = 1800.0) -> int:
    """Re-run each item at `tree`, refuse unless the stitches match or the
    art does not register (`REG_MIN`), read the spaces, write the harness
    files."""
    from tools import fault_reader_jobs as jobs
    from tools.letter_fault_reader import colour_classes
    out.mkdir(parents=True, exist_ok=True)
    sha = jobs.tree_sha(tree)
    bad = 0
    for iid in items:
        _kind, slug = jobs.split_item(iid)
        job, art = jobs.job_paths(iid, pro_run, corpus_run, photos)
        stored = json.loads(job.read_text(encoding="utf-8"))
        classes = colour_classes(stored["design"]["colors"])
        labels, maskf = out / f"{iid}.labels.npz", out / f"{iid}.mask.npz"
        spec = {"tree": str(tree), "slug": slug, "job": str(job),
                "art": str(art) if art else None, "out": str(out / f"{iid}.raw.json"),
                "mask": str(maskf), "labels": str(labels), "pxmm": PXMM, "pad": PAD_MM,
                "thread_mm": THREAD_MM, "classes": [list(c) for c in classes], "kinds": list(KINDS),
                "alpha_empty": ALPHA_EMPTY, "bg_tol": BG_TOL}
        try:
            r = jobs.run_worker(WORKER, spec, tree, timeout)
        except (jobs.WorkerFailed, jobs.Refused) as e:
            print(iid, type(e).__name__, e, flush=True)
            bad += 1
            continue
        if not r["bg_mask_empty_share"] >= REG_MIN:
            print(iid, f"REFUSED: the art does not register (bg_mask empty share {r['bg_mask_empty_share']:.3f})",
                  flush=True)
            bad += 1
            continue
        lab = np.load(labels)
        flags, cands, cand_mask, mem = read_spaces(lab["empty"], lab["thread"], lab["kind"],
                                                   class_rgb=classes, empty_rgb=r["empty_rgb"])
        mask = np.load(maskf)["mask"]
        np.savez_compressed(maskf, mask=mask, cand=cand_mask)
        by = {}
        for f in flags:
            by[f["kind"]] = by.get(f["kind"], 0) + 1
        cover = {c: sum(1 for m in mem if m["cover"] == c) for c in ("infill", "bare", "closed", "matched")}
        rec = {"item": iid, "reader": "infill_fault_reader", "tree_sha": sha,
               "stored_tree_sha": (stored.get("_meta") or {}).get("tree_sha"),
               "stitches_sha256": r["stored_sha"], "px_per_mm": PXMM, "pad_mm": PAD_MM,
               "img_w": r["img_w"], "img_h": r["img_h"], "art_px_per_mm": r["art_px_per_mm"],
               "empty_from": r["empty_from"], "empty_rgb": r["empty_rgb"], "bg_mask_empty_share": r["bg_mask_empty_share"],
               "spaces": len(mem), "cover_counts": cover, "by_kind": by, "flags": flags,
               "candidates": cands, "members": mem}
        (out / f"{iid}.flags.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        print(iid, "spaces", len(mem), cover, "candidates", len(cands), "flags", len(flags), by,
              "empty from", r["empty_from"], "reg", round(r["bg_mask_empty_share"], 3), flush=True)
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--pro-run", type=Path, help="defect_marks capture-pro output (L_ items)")
    r.add_argument("--corpus-run", type=Path, help="corpus capture with <slug>.json designs (C_ items)")
    r.add_argument("--photos", type=Path, help="corpus artwork folder (C_ items)")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--tree", type=Path, default=ROOT, help="digitizer/ of the checkout the kit was built on")
    r.add_argument("--only", action="append", required=True, help="item id, L_<slug> or C_<slug>")
    a = ap.parse_args(argv)
    return run(a.only, a.out, a.tree.resolve(), a.pro_run, a.corpus_run, a.photos)


if __name__ == "__main__":
    sys.exit(main())
