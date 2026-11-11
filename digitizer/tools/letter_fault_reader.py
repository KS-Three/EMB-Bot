"""Letter-fault reader: WHERE the thread closes a counter or joins two shapes.

    python -m tools.letter_fault_reader run --pro-run DIR --out DIR [--tree DIGITIZER] [--only SLUG]
    python -m tools.letter_fault_reader run --corpus-run DIR --photos DIR --out DIR --only C_<slug>
    python -m tools.fault_reader_harness score --fault letters --marks MARKS.json --flags DIR

The second reader scored by `tools.fault_reader_harness` against Kent's
2026-11-10 pins, for letters that close up, merge or cannot be read (14 pins
on 6 logos: the B's lost holes, B+R and N+T merged, the S and E with no
spacing, the T into the border). What is fixed before any result is
`docs/defect-marks-2026-11-10/letter-reader-preregistration.md`.

It compares TOPOLOGY, one thread colour at a time, between the artwork the
design was traced from and our own render of the design (the render Kent
marked):

  * art: the prepped raster (`gen.p`, the stage-1 picture the trace came
    from), each pixel given the nearest of the design's thread colours, or
    "unsewn" where stage 1's `bg_mask` says background (not by colour: the
    art's background is often a thread colour too, Becker's dark cutout and
    TOAT's white field); warped into the render grid through the plan's frame.
  * thread: every filament of the stored design at `render_design`'s own
    width and endpoints (`stitchviz._frame`), drawn in sew order as its
    colour class with no anti-alias, so the top thread at each pixel is known
    exactly (an anti-aliased edge between black and white reads as grey).

Per colour class `c`, with `S` the art's `c` pixels and `T` the thread's:

  1. COUNTER LOST: a hole of `S` (enclosed non-`c` area) wide enough to
     hold a circle of half a thread (`MIN_CLEAR_MM`) whose matching hole in
     `T` (overlap rule of `glyph_read`, one to one) is missing or narrower
     than `KEEP_FRAC` of the art's. At the art hole's deepest point;
     strength = art width - sewn width, mm.
  2. JOIN: two shapes of `S` (components of at least `MIN_SHAPE_MM2`)
     whose thread runs continuously across the line midway between them
     (their Voronoi boundary), where the art's gap is at least
     `MIN_CLEAR_MM` and the thread there is wider than `BRIDGE_MIN_MM` (one
     running-stitch filament across fabric is travel, a stray, not a join).
     At the crossing's widest art gap; strength = that gap, mm.
  3. BAY CLOSED: a hole of `T` at least `MIN_CLEAR_MM` wide, overlapping no
     enclosed area of the art, lying mostly on the art's non-`c` pixels:
     the thread closed a bay's mouth (the S whose curve meets its spine).
     At its deepest point; strength = its width, mm.

A shape is judged only where its thread sews it (`SEWN_FRAC` of its art
pixels carry `c` in the render), so an anti-alias fringe or a piece the
pipeline dropped is not read as a lost counter. No pull compensation is
taken back: Kent marked the render, so the render is what is read.

`digitizer_core` already reads counters per glyph (`glyph_read`, behind
`cfg.preflight_glyph_metric`) and dropped elements (`ARTWORK_ELEMENT_DROPPED`);
neither says WHERE, the first covers only text-tagged words, and neither sees
two shapes joined. This reader keeps the counter rule's numbers (half a
thread, the 25% overlap, `MIN_GLYPH_MM2`) and reads the whole design.

The worker re-runs each job as `edge_fault_reader` does and REFUSES an item
unless the re-run's stitches equal the stored design's. Output: `<item>.
flags.json` and `<item>.mask.npz` (the harness format; the mask is the same
thread-pixel mask the edge reader wrote) plus `<item>.labels.npz` (both class
images). No picture leaves `eye_pairs_out/`.
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
MIN_CLEAR_MM = 0.5 * THREAD_MM                        # glyph_read.MIN_HOLE_DIAM_THREADS x thread
KEEP_FRAC = 0.5                                       # a sewn counter under half the art's width is lost
MIN_SHAPE_MM2 = 0.12                                  # == glyph_read.MIN_GLYPH_MM2
OVERLAP = 0.25                                        # glyph_read's counter-matching overlap
SEWN_FRAC = 0.5                                       # a shape is judged when half its art carries its thread
BRIDGE_MIN_MM = 1.5 * THREAD_MM                       # thread width at a join: wider than one filament
TOUCH_MM2 = 0.05                                      # a thread piece "holds" a shape over this much of it
COLOUR_MERGE = 12.0                                   # RGB distance: two spools this close are one class
UNSEWN = -1

EIGHT = np.ones((3, 3), bool)


# ------------------------------------------------------------ pure helpers ----

def colour_classes(colors: list[dict], merge: float = COLOUR_MERGE) -> list[tuple[int, int, int]]:
    """The design's spools as distinct RGB classes, first-seen order; a spool
    within `merge` of a kept class joins it (black twice is one class)."""
    out: list[tuple[int, int, int]] = []
    for c in colors:
        rgb = (int(c["r"]), int(c["g"]), int(c["b"]))
        if not any(np.linalg.norm(np.subtract(rgb, k)) <= merge for k in out):
            out.append(rgb)
    return out


def to_mm(xy_px: tuple[float, float], px_per_mm: float = PXMM, pad_mm: float = PAD_MM):
    """Render pixel (x, y) -> the pins' frame (`defect_marks.mark_mm`)."""
    return round(xy_px[0] / px_per_mm - pad_mm, 2), round(xy_px[1] / px_per_mm - pad_mm, 2)


def _holes(mask: np.ndarray):
    filled = ndi.binary_fill_holes(mask)
    return ndi.label(filled & ~mask)


def _deepest(dt: np.ndarray, region: np.ndarray):
    ys, xs = np.nonzero(region)
    i = int(np.argmax(dt[ys, xs]))
    return float(xs[i]), float(ys[i]), float(dt[ys, xs][i])


def counter_events(S: np.ndarray, T: np.ndarray, judged: np.ndarray, px_per_mm: float = PXMM) -> list[dict]:
    """Rule 1. `S`, `T` bool (art, thread) of one class; `judged` bool, the
    art pixels of shapes that are judged (sewn guard)."""
    min_px = MIN_CLEAR_MM * px_per_mm
    lab_s, n_s = _holes(S)
    if not n_s:
        return []
    dt_s = ndi.distance_transform_edt(~S)
    filled_j = ndi.binary_fill_holes(judged)
    art = []
    for i, sl in enumerate(ndi.find_objects(lab_s), start=1):
        h = lab_s == i
        x, y, r = _deepest(dt_s, h)
        if 2 * r < min_px or not filled_j[int(y), int(x)]:
            continue
        art.append((h, x, y, 2 * r / px_per_mm))
    if not art:
        return []
    lab_t, n_t = _holes(T)
    dt_t = ndi.distance_transform_edt(~T)
    sewn = []
    for j in range(1, n_t + 1):
        h = lab_t == j
        _, _, r = _deepest(dt_t, h)
        sewn.append((h, 2 * r / px_per_mm))
    pairs = []
    for i, (h, *_rest) in enumerate(art):
        for j, (th, _d) in enumerate(sewn):
            ov = float((h & th).sum())
            if ov and ov >= OVERLAP * min(h.sum(), th.sum()):
                pairs.append((ov, i, j))
    pairs.sort(reverse=True)
    match: dict[int, int] = {}
    used = set()
    for _ov, i, j in pairs:
        if i not in match and j not in used:
            match[i] = j
            used.add(j)
    out = []
    for i, (_h, x, y, d_a) in enumerate(art):
        d_t = sewn[match[i]][1] if i in match else 0.0
        if d_t < MIN_CLEAR_MM or d_t < KEEP_FRAC * d_a:
            out.append({"kind": "counter_lost", "px": (x, y), "strength": round(d_a - d_t, 3),
                        "art_mm": round(d_a, 3), "sewn_mm": round(d_t, 3)})
    return out


def join_events(S_lab: np.ndarray, judged_ids: set, T: np.ndarray, px_per_mm: float = PXMM) -> list[dict]:
    """Rule 2. `S_lab` int, art shapes of one class labelled 1..n (specks
    already removed); `judged_ids` the labels the sewn guard passed."""
    if S_lab.max() < 2 or not T.any():
        return []
    S = S_lab > 0
    dt_s, (iy, ix) = ndi.distance_transform_edt(~S, return_indices=True)
    near = S_lab[iy, ix]
    dt_t = ndi.distance_transform_edt(T)
    tlab, _ = ndi.label(T, EIGHT)
    # which thread pieces hold which shapes
    both = (tlab > 0) & S
    key = tlab[both].astype(np.int64) * (int(S_lab.max()) + 1) + S_lab[both]
    ks, cnt = np.unique(key, return_counts=True)
    touch = TOUCH_MM2 * px_per_mm ** 2
    held = {(int(k) // (int(S_lab.max()) + 1), int(k) % (int(S_lab.max()) + 1))
            for k, c in zip(ks, cnt) if c >= touch}
    cross = np.zeros(T.shape, bool)
    pair_at = {}
    for dy, dx in ((0, 1), (1, 0)):
        a = near[: near.shape[0] - dy, : near.shape[1] - dx]
        b = near[dy:, dx:]
        t0 = T[: T.shape[0] - dy, : T.shape[1] - dx] & T[dy:, dx:]
        ys, xs = np.nonzero(t0 & (a != b))
        for y, x in zip(ys, xs):
            p = (min(int(a[y, x]), int(b[y, x])), max(int(a[y, x]), int(b[y, x])))
            for (yy, xx) in ((y, x), (y + dy, x + dx)):
                cross[yy, xx] = True
                pair_at.setdefault((yy, xx), set()).add(p)
    if not cross.any():
        return []
    glab, ng = ndi.label(cross, EIGHT)
    out = []
    for g in range(1, ng + 1):
        ys, xs = np.nonzero(glab == g)
        pairs = set().union(*(pair_at[(int(y), int(x))] for y, x in zip(ys, xs)))
        t = int(tlab[ys[0], xs[0]])
        for a, b in sorted(pairs):
            if a not in judged_ids or b not in judged_ids:
                continue
            if (t, a) not in held or (t, b) not in held:
                continue
            gap = 2 * dt_s[ys, xs]
            wid = 2 * dt_t[ys, xs]
            if wid.max() < BRIDGE_MIN_MM * px_per_mm or gap.max() < MIN_CLEAR_MM * px_per_mm:
                continue
            k = int(np.argmax(gap))
            out.append({"kind": "join", "px": (float(xs[k]), float(ys[k])),
                        "strength": round(float(gap[k]) / px_per_mm, 3), "shapes": [a, b],
                        "bridge_mm": round(float(wid.max()) / px_per_mm, 3)})
    return out


def bay_events(S: np.ndarray, T: np.ndarray, judged: np.ndarray, px_per_mm: float = PXMM) -> list[dict]:
    """Rule 3: holes of the thread where the art has no enclosed area and
    mostly no ink of this class, closed by thread that sews a judged art
    shape (`judged`, bool): a field of thread sewn where the art has none of
    its colour (Becker's white interiors) closes nothing."""
    lab_t, n_t = _holes(T)
    if not n_t or not judged.any():
        return []
    src_any = ndi.binary_fill_holes(S) & ~S
    dt_t = ndi.distance_transform_edt(~T)
    tlab, _ = ndi.label(T, EIGHT)
    touch = TOUCH_MM2 * px_per_mm ** 2
    out = []
    for j in range(1, n_t + 1):
        h = lab_t == j
        x, y, r = _deepest(dt_t, h)
        if 2 * r < MIN_CLEAR_MM * px_per_mm or (h & src_any).any():
            continue
        if float((h & S).sum()) > 0.5 * float(h.sum()):
            continue                     # thread missing over ink: a gap, not a closure
        rim = tlab[ndi.binary_dilation(h, EIGHT) & T]
        rim = rim[rim > 0]
        if not len(rim):
            continue
        t = int(np.bincount(rim).argmax())
        if float(((tlab == t) & judged).sum()) < touch:
            continue                     # the closing thread sews no shape of this colour
        out.append({"kind": "bay_closed", "px": (x, y), "strength": round(2 * r / px_per_mm, 3)})
    return out


def read_class(art_c: np.ndarray, thr_c: np.ndarray, px_per_mm: float = PXMM) -> list[dict]:
    """All three rules on one class's two masks."""
    lab, n = ndi.label(art_c, EIGHT)
    min_px = MIN_SHAPE_MM2 * px_per_mm ** 2
    if n:
        sizes = ndi.sum(np.ones(lab.shape), lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        keep[1:] = sizes >= min_px
        lab = np.where(keep[lab], lab, 0)
        lab, n = ndi.label(lab > 0, EIGHT)
    if not n:
        return []
    S = lab > 0
    cover = ndi.sum(thr_c, lab, range(1, n + 1)) / ndi.sum(np.ones(lab.shape), lab, range(1, n + 1))
    judged_ids = {i + 1 for i, f in enumerate(cover) if f >= SEWN_FRAC}
    jm = np.zeros(n + 1, bool)
    jm[list(judged_ids)] = True
    judged = jm[lab]
    return (counter_events(S, thr_c, judged, px_per_mm) + join_events(lab, judged_ids, thr_c, px_per_mm)
            + bay_events(S, thr_c, judged, px_per_mm))


def read_faults(art_lab: np.ndarray, thr_lab: np.ndarray, px_per_mm: float = PXMM,
                pad_mm: float = PAD_MM) -> list[dict]:
    """Every event of every thread class, as flags in the pins' frame,
    strongest first."""
    flags = []
    for c in sorted(int(v) for v in np.unique(thr_lab) if v != UNSEWN):
        for e in read_class(art_lab == c, thr_lab == c, px_per_mm):
            x, y = to_mm(e.pop("px"), px_per_mm, pad_mm)
            flags.append({"x_mm": x, "y_mm": y, "class": c, **e})
    return sorted(flags, key=lambda f: (-f["strength"], f["x_mm"], f["y_mm"]))


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
np.savez_compressed(spec["mask"], mask=mask)
classes = spec["classes"]                       # RGB
K = len(classes)
def argnear(pix, protos):
    best = np.full(pix.shape[:2], np.inf, np.float32)
    arg = np.zeros(pix.shape[:2], np.int32)
    for i, q in enumerate(protos):
        dq = ((pix - q[None, None, :]) ** 2).sum(-1)
        sel = dq < best
        best[sel] = dq[sel]
        arg[sel] = i
    return arg
# thread: each filament drawn at render_design's own width and endpoints, in
# sew order, as its class index with no anti-alias (an AA edge between black
# and white would read as grey thread)
(H, W), to_px = stitchviz._frame(d["stitches"], spec["pxmm"], spec["pad"])
tw = max(2, int(round(stitchviz.THREAD_MM * spec["pxmm"])))
cls_of = [int(np.argmin([sum((a - b) ** 2 for a, b in zip((c["r"], c["g"], c["b"]), k)) for k in classes]))
          for c in d["colors"]]
lab = np.full((H, W), 255, np.uint8)
ci, prev = 0, None
for s_ in d["stitches"]:
    kind = s_.get("type")
    if kind == "color":
        ci += 1
        prev = None
        continue
    if kind in ("jump", "trim", "end"):
        prev = None
        continue
    if kind != "stitch":
        continue
    q = to_px(s_)
    if prev is not None and prev != q:
        cv2.line(lab, prev, q, cls_of[min(ci, len(cls_of) - 1)], tw, cv2.LINE_8)
    prev = q
thr = np.where(lab == 255, -1, lab.astype(np.int16)).astype(np.int16)
# art: prepped raster, nearest spool or unsewn, into the render grid
p = gen.p
rgb = p.rgb.astype(np.float32)
bgm = np.asarray(p.bg_mask, bool)
# unsewn = the pipeline's own background mask, nothing else: the art's
# background colour is often a thread colour too (white field, dark cutout)
P = np.stack([np.array(c, np.float32) for c in classes])
ka = argnear(rgb, P)
ka[bgm] = K
hot = np.zeros(rgb.shape[:2] + (K + 1,), np.float32)
idx = np.clip(ka, 0, K)
np.put_along_axis(hot, idx[:, :, None], 1.0, axis=2)
ax0, ay0, ax1, ay1 = p.art_bbox
cx, cy, ppm = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0, float(p.px_per_mm)
st = d["stitches"]
xs = [s["x"] for s in st if s.get("type") in ("stitch", "jump")]
ys = [s["y"] for s in st if s.get("type") in ("stitch", "jump")]
x0, y1 = min(xs) / 10.0, max(ys) / 10.0
kk = spec["pxmm"] / ppm
M = np.array([[kk, 0, spec["pxmm"] * (-cx / ppm - x0 + spec["pad"])],
              [0, kk, spec["pxmm"] * (-cy / ppm + y1 + spec["pad"])]], np.float64)
chans = []
for c in range(K + 1):
    chans.append(cv2.warpAffine(hot[:, :, c], M, (W, H), flags=cv2.INTER_LINEAR,
                                borderValue=1.0 if c == K else 0.0))
hw = np.stack(chans, -1)
ka2 = hw.argmax(-1)
artl = np.where(ka2 >= K, -1, ka2).astype(np.int16)
np.savez_compressed(spec["labels"], art=artl, thread=thr)
json.dump({"same_stitches": same, "stored_sha": h(stored["design"]["stitches"]),
           "rerun_sha": h(design["stitches"]), "img_w": int(W), "img_h": int(H),
           "art_px_per_mm": ppm, "bg_frac": float(bgm.mean())},
          open(spec["out"], "w", encoding="utf-8"))
'''


def run(items: list[str], out: Path, tree: Path, pro_run: Path | None = None,
        corpus_run: Path | None = None, photos: Path | None = None, timeout: float = 1800.0) -> int:
    """Re-run each item's job at `tree` (`tools.fault_reader_jobs`: pro jobs
    `L_<slug>` and corpus rows `C_<slug>`), refuse unless the stitches match,
    read the faults, write `<item>.flags.json`."""
    from tools import fault_reader_jobs as jobs
    out.mkdir(parents=True, exist_ok=True)
    sha = jobs.tree_sha(tree)
    bad = 0
    for iid in items:
        _kind, slug = jobs.split_item(iid)
        job, art = jobs.job_paths(iid, pro_run, corpus_run, photos)
        stored = json.loads(job.read_text(encoding="utf-8"))
        classes = colour_classes(stored["design"]["colors"])
        labels = out / f"{iid}.labels.npz"
        spec = {"tree": str(tree), "slug": slug, "job": str(job), "out": str(out / f"{iid}.raw.json"),
                "art": str(art) if art else None,
                "mask": str(out / f"{iid}.mask.npz"), "labels": str(labels), "pxmm": PXMM,
                "pad": PAD_MM, "thread_mm": THREAD_MM, "classes": [list(c) for c in classes]}
        try:
            r = jobs.run_worker(WORKER, spec, tree, timeout)
        except (jobs.WorkerFailed, jobs.Refused) as e:
            print(iid, type(e).__name__, e, flush=True)
            bad += 1
            continue
        lab = np.load(labels)
        flags = read_faults(lab["art"], lab["thread"])
        kinds = {}
        for f in flags:
            kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
        rec = {"item": iid, "reader": "letter_fault_reader", "tree_sha": sha,
               "stored_tree_sha": (stored.get("_meta") or {}).get("tree_sha"),
               "stitches_sha256": r["stored_sha"], "px_per_mm": PXMM, "pad_mm": PAD_MM,
               "img_w": r["img_w"], "img_h": r["img_h"], "art_px_per_mm": r["art_px_per_mm"],
               "classes": [list(c) for c in classes], "by_kind": kinds, "flags": flags}
        (out / f"{iid}.flags.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        print(iid, "flags", len(flags), kinds, flush=True)
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
    r.add_argument("--only", action="append", default=[], help="item id (L_<slug> / C_<slug>) or pro slug")
    a = ap.parse_args(argv)
    from tools.defect_marks import PRO_SLUGS
    items = [o if o[:2] in ("L_", "C_") else f"L_{o}" for o in a.only] or [f"L_{s}" for s in PRO_SLUGS]
    return run(items, a.out, a.tree.resolve(), a.pro_run, a.corpus_run, a.photos)


if __name__ == "__main__":
    sys.exit(main())
