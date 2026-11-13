"""Inconsistency reader: WHERE like features are sewn unlike their siblings.

    python -m tools.inconsistency_fault_reader run --labels DIR --design-run DIR --out DIR [--infill DIR] --only ITEM ...
    python -m tools.inconsistency_fault_reader analyse --out DIR --json OUT [--letter DIR ...] [--space DIR]
    python -m tools.fault_reader_harness score --fault inconsistency --marks M --flags DIR --prefix C_ ...

The fifth reader scored by `tools.fault_reader_harness` against Kent's
defect-marks pins, for his notes that compare a feature with its siblings:
"the only letter that is thinly stitched", "some have bean stitching around
the openings, while the other doesn't", "right leg infill doesn't match left
leg", "#2-#3 feet are differnt colors, they should be the same"
(`select_inconsistency_pins`). What is fixed before any result is
`docs/inconsistency-fault-reader-2026-11-12.md`.

Two families of feature, each grouped by GEOMETRY only (never by a pin):

  F1 SEWN SHAPES (this reader). Per thread colour class, every 8-connected
     component of the top thread at least two filaments across (its deepest
     point `MIN_HALF_MM` from its edge). Two shapes are ALIKE when their
     areas are within `AREA_RATIO`, their elongations (sqrt of the ratio of
     their second moments) within `ELONG_RATIO` and their solidities
     (area / convex hull) within `SOLIDITY_DIFF`: rotation-, mirror- and
     colour-blind on purpose, so the two feet in different threads and the
     wheel's rotated handles can be compared. Groups are the connected
     components of the "alike" graph. Four treatments are read per shape:
       colour  its thread class;
       kind    the commonest top run kind on it (fill, satin, run, bean, border);
       angle   the length-weighted axial mean of its fill and satin
               penetration segments (from the stored stitches), judged when
               at least `ANGLE_MIN_SEGS` segments agree to `ANGLE_MIN_R`
               (resultant of the doubled angles); for two shapes both at
               least `ROUND_ELONG` elongated it is taken relative to each
               shape's own axis and folded to [0, 90] (a rotated or mirrored
               copy sewn the same way agrees), else absolute, mod 180;
               two angles disagree past `ANGLE_TOL_DEG` (halfway from
               parallel to perpendicular);
       rim     `outlined` when at least `OUTLINED` of the band within
               `RIM_MM` of its edge (both sides) is topped by a line run,
               `plain` at most `PLAIN`, else not judged (the in-fill reader's
               rim rule, applied to ink).
     A shape is ODD on a treatment when it disagrees with MORE THAN HALF of
     the judged members of its group (a pair that disagrees: both odd; a
     3-group A, A, B: only B). Each odd shape is flagged; strength = the
     number of treatments it is odd on (1-4).
  F2 EMPTY SPACES (the in-fill reader, frozen). The art's empty spaces,
     covered or not, outlined or not, unlike their siblings: read verbatim
     from `tools.infill_fault_reader`'s stored `<item>.flags.json` and
     `cand` (its rule, constants and tree). Not re-derived here.

Flags are spread over each flagged F1 shape on a `SPACING_MM` grid (at its
deepest point when no grid node falls on it), so a pin anywhere on a large
odd shape is in reach, and the CANDIDATE set (the harness's `chance_pick`
anchors) is spread the same way over every F1 shape in a group of two or
more, plus F2's candidates. Picking the right members, not finding the
region, is what the candidate null asks.

The reader runs no pipeline. It reads the in-fill reader's rasters
(`<item>.labels.npz`: `thread` top colour class and `kind` top run kind at
12 px/mm, written at tree 950855bf by a worker that refused any item whose
re-run stitches differed from the stored design) and the stored design
(`<design-run>/<slug>.json`, its stitches hashed against the in-fill
record's `stitches_sha256`, or the letter reader's for an item the in-fill
reader refused). Output, in the out dir: `<item>.flags.json` (harness format
plus `candidates` and `members`) and `<item>.mask.npz` (`mask`, `cand`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi

PXMM = 12.0                                           # the review render's scale (pins' frame)
PAD_MM = 2.0
UNITS_PER_MM = 10.0                                   # == stitchviz.UNITS_PER_MM
THREAD_MM = 0.4                                       # == stitchviz.THREAD_MM
MIN_HALF_MM = THREAD_MM                               # a shape: two filaments across
AREA_RATIO = 1.5                                      # alike: areas within x1.5
ELONG_RATIO = 1.25                                    # ... elongations within x1.25
SOLIDITY_DIFF = 0.10                                  # ... solidities within 0.10
ROUND_ELONG = 1.5                                     # under this a shape has no axis of its own
ANGLE_MIN_SEGS = 3
ANGLE_MIN_R = 0.5                                     # doubled-angle resultant: a direction exists
ANGLE_TOL_DEG = 45.0                                  # halfway from parallel to perpendicular
RIM_MM = THREAD_MM                                    # == infill_fault_reader.RIM_MM
OUTLINED = 0.25                                       # == infill_fault_reader.OUTLINED
PLAIN = 0.05                                          # == infill_fault_reader.PLAIN
SPACING_MM = 2.0                                      # == edge_fault_reader.MERGE_MM
KINDS = ("fill", "satin", "run", "bean", "border", "travel", "underlay")   # == infill_fault_reader.KINDS
LINE_KINDS = ("run", "bean", "border")
JUDGED_KINDS = ("fill", "satin", "run", "bean", "border")
ANGLE_KINDS = ("fill", "satin")
TREATMENTS = ("colour", "kind", "angle", "rim")
EIGHT = np.ones((3, 3), bool)


# ------------------------------------------------------------ pure helpers ----

def to_mm(x_px: float, y_px: float, px_per_mm: float = PXMM, pad_mm: float = PAD_MM):
    """Render pixel -> the pins' frame (`defect_marks.mark_mm`)."""
    return round(x_px / px_per_mm - pad_mm, 2), round(y_px / px_per_mm - pad_mm, 2)


def shape_geometry(member: np.ndarray) -> dict:
    """Area (px), elongation, orientation (deg, image frame, y down, mod 180),
    solidity and deepest point of one boolean component."""
    ys, xs = np.nonzero(member)
    area = len(xs)
    cx, cy = xs.mean(), ys.mean()
    cov = np.cov(np.stack([xs - cx, ys - cy])) if area > 1 else np.eye(2)
    ev, evec = np.linalg.eigh(cov + 1e-9 * np.eye(2))
    elong = float(math.sqrt(max(ev[1], 1e-9) / max(ev[0], 1e-9)))
    vx, vy = evec[:, 1]
    orient = float(math.degrees(math.atan2(vy, vx)) % 180.0)
    x0, y0 = xs.min(), ys.min()
    hull = cv2.convexHull(np.stack([xs - x0, ys - y0], 1).astype(np.int32))
    canvas = np.zeros((ys.max() - y0 + 1, xs.max() - x0 + 1), np.uint8)
    cv2.fillConvexPoly(canvas, hull, 1)                # hull PIXELS, so area / hull is like for like
    solidity = float(min(1.0, area / max(1, int(canvas.sum()))))
    return {"area_px": int(area), "elong": round(elong, 4), "orient": round(orient, 2),
            "solidity": round(solidity, 4)}


def alike_matrix(geo: list[dict], area_ratio: float = AREA_RATIO, elong_ratio: float = ELONG_RATIO,
                 solidity_diff: float = SOLIDITY_DIFF) -> np.ndarray:
    """Bool n x n: shapes i and j are alike (diagonal False)."""
    a = np.log([g["area_px"] for g in geo]) if geo else np.zeros(0)
    e = np.log([g["elong"] for g in geo]) if geo else np.zeros(0)
    s = np.array([g["solidity"] for g in geo], float)
    m = ((np.abs(a[:, None] - a[None, :]) <= math.log(area_ratio) + 1e-9)
         & (np.abs(e[:, None] - e[None, :]) <= math.log(elong_ratio) + 1e-9)
         & (np.abs(s[:, None] - s[None, :]) <= solidity_diff + 1e-9))
    np.fill_diagonal(m, False)
    return m


def groups_of(alike: np.ndarray) -> list[int]:
    """Group id per shape: connected components of the alike graph."""
    n = len(alike)
    if not n:
        return []
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    _, lab = connected_components(csr_matrix(alike), directed=False)
    return [int(v) for v in lab]


def axial_mean(angles_deg: np.ndarray, weights: np.ndarray) -> tuple[float | None, float]:
    """Length-weighted mean of undirected angles (mod 180) and its resultant R."""
    if not len(angles_deg) or weights.sum() <= 0:
        return None, 0.0
    t = np.radians(np.asarray(angles_deg, float)) * 2.0
    c, s = (weights * np.cos(t)).sum(), (weights * np.sin(t)).sum()
    r = float(math.hypot(c, s) / weights.sum())
    return float(math.degrees(math.atan2(s, c)) / 2.0 % 180.0), r


def angle_disagree(a: dict, b: dict, tol: float = ANGLE_TOL_DEG, round_elong: float = ROUND_ELONG):
    """Two judged shapes' stitch angles disagree. Relative to each shape's own
    axis (folded to [0, 90]) when both have an axis, else absolute mod 180.
    None (not comparable) between two run kinds: a fill row and a satin
    swing are a `kind` difference already (dev fix, `L_becker_hat_large`)."""
    if a["kind"] != b["kind"]:
        return None
    if a["elong"] >= round_elong and b["elong"] >= round_elong:
        def rel(m):
            d = (m["angle"] - m["orient"]) % 180.0
            return min(d, 180.0 - d)
        return abs(rel(a) - rel(b)) > tol
    d = abs(a["angle"] - b["angle"]) % 180.0
    return min(d, 180.0 - d) > tol


def odd_members(values: list, disagree=None) -> list[bool]:
    """Per member: does it disagree with MORE THAN HALF of the other judged
    members (value not None) it is comparable with (`disagree` not None)?
    An unjudged member is never odd."""
    disagree = disagree or (lambda a, b: a != b)
    out = []
    for i, v in enumerate(values):
        if v is None:
            out.append(False)
            continue
        votes = [disagree(v, w) for j, w in enumerate(values) if j != i and w is not None]
        votes = [bool(x) for x in votes if x is not None]
        out.append(bool(votes) and sum(votes) * 2 > len(votes))
    return out


def rim_treatment(member: np.ndarray, kind: np.ndarray, px_per_mm: float = PXMM) -> str | None:
    """`outlined` / `plain` / None from the line-run share of the band within
    `RIM_MM` of the member's edge, inside and outside."""
    k = max(1, int(round(RIM_MM * px_per_mm)))
    band = ndi.binary_dilation(member, EIGHT, k) & ~ndi.binary_erosion(member, EIGHT, k)
    if not band.any():
        return None
    line = np.isin(kind[band], [KINDS.index(x) for x in LINE_KINDS]).mean()
    return "outlined" if line >= OUTLINED else "plain" if line <= PLAIN else None


def top_kind(member: np.ndarray, kind: np.ndarray) -> str | None:
    """Commonest judged run kind on the member's pixels (ties: KINDS order)."""
    v = kind[member]
    counts = [(int((v == KINDS.index(k)).sum()), -i, k) for i, k in enumerate(KINDS) if k in JUDGED_KINDS]
    best = max(counts)
    return best[2] if best[0] > 0 else None


def spread_points(member: np.ndarray, px_per_mm: float = PXMM, spacing_mm: float = SPACING_MM):
    """Grid nodes (every `spacing_mm`, render frame) on the member; its
    deepest point when none lands on it. -> list of (x_px, y_px)."""
    step = max(1, int(round(spacing_mm * px_per_mm)))
    ys, xs = np.nonzero(member)
    on = (xs % step == 0) & (ys % step == 0)
    if on.any():
        return [(float(x), float(y)) for x, y in zip(xs[on], ys[on])]
    dt = ndi.distance_transform_edt(np.pad(member, 1))[1:-1, 1:-1]
    i = int(np.argmax(dt[ys, xs]))
    return [(float(xs[i]), float(ys[i]))]


def segments(design: dict, shape_hw: tuple[int, int], px_per_mm: float = PXMM, pad_mm: float = PAD_MM,
             class_of_colour: list[int] | None = None):
    """Every needle segment of an `ANGLE_KINDS` run at least `THREAD_MM`
    long, in the render frame (`stitchviz._frame`'s mapping, re-derived and
    checked against `shape_hw`). -> dict of arrays: mx, my (midpoint px),
    angle (deg mod 180, y down), length (mm), cls (colour class)."""
    st = design["stitches"]
    xs = [s["x"] for s in st if s.get("type") in ("stitch", "jump")]
    ys = [s["y"] for s in st if s.get("type") in ("stitch", "jump")]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w = max(8, int(((x1 - x0) / UNITS_PER_MM + 2 * pad_mm) * px_per_mm))
    h = max(8, int(((y1 - y0) / UNITS_PER_MM + 2 * pad_mm) * px_per_mm))
    if (h, w) != tuple(shape_hw):
        raise ValueError(f"render frame {(h, w)} != labels {tuple(shape_hw)}")
    kind_of = {}
    for r in design.get("runs") or []:
        for i in range(int(r["i0"]), int(r["i1"]) + 1):
            kind_of[i] = r["kind"]
    out = {"mx": [], "my": [], "angle": [], "length": [], "cls": []}
    ci, prev = 0, None
    for i, s in enumerate(st):
        t = s.get("type")
        if t == "color":
            ci += 1
            prev = None
            continue
        if t != "stitch":
            prev = None
            continue
        p = (((s["x"] - x0) / UNITS_PER_MM + pad_mm) * px_per_mm, ((y1 - s["y"]) / UNITS_PER_MM + pad_mm) * px_per_mm)
        if prev is not None and kind_of.get(i) in ANGLE_KINDS:
            dx, dy = p[0] - prev[0], p[1] - prev[1]
            ln = math.hypot(dx, dy) / px_per_mm
            if ln >= THREAD_MM:
                out["mx"].append((p[0] + prev[0]) / 2)
                out["my"].append((p[1] + prev[1]) / 2)
                out["angle"].append(math.degrees(math.atan2(dy, dx)) % 180.0)
                out["length"].append(ln)
                cc = class_of_colour[min(ci, len(class_of_colour) - 1)] if class_of_colour else ci
                out["cls"].append(cc)
        prev = p
    return {k: np.asarray(v, float) for k, v in out.items()}


def read_shapes(thread: np.ndarray, kind: np.ndarray, segs: dict | None = None,
                px_per_mm: float = PXMM, pad_mm: float = PAD_MM):
    """F1. -> (flags, candidates, cand_mask, members). `thread` int16 (top
    colour class, -1 bare), `kind` uint8 (index into KINDS, 255 bare),
    `segs` from `segments` (None: angle not read)."""
    min_px = MIN_HALF_MM * px_per_mm
    members, masks = [], []
    lab_all = np.zeros(thread.shape, np.int32)
    for c in sorted(int(v) for v in np.unique(thread) if v >= 0):
        lab, n = ndi.label(thread == c, EIGHT)
        for i, sl in enumerate(ndi.find_objects(lab), start=1):
            m = lab[sl] == i
            dt = ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1]
            if dt.max() < min_px:
                continue
            full = np.zeros(thread.shape, bool)
            full[sl] = m
            g = shape_geometry(full)
            g.update({"id": len(members), "cls": c, "kind": top_kind(full, kind),
                      "rim": rim_treatment(full, kind, px_per_mm), "angle": None, "angle_r": None})
            lab_all[full] = g["id"] + 1
            members.append(g)
            masks.append(full)
    if segs is not None and len(segs["mx"]):
        H, W = thread.shape
        ix = np.clip(np.round(segs["mx"]).astype(int), 0, W - 1)
        iy = np.clip(np.round(segs["my"]).astype(int), 0, H - 1)
        owner = lab_all[iy, ix] - 1
        for g in members:
            sel = (owner == g["id"]) & (segs["cls"] == g["cls"])
            if sel.sum() >= ANGLE_MIN_SEGS:
                a, r = axial_mean(segs["angle"][sel], segs["length"][sel])
                if a is not None and r >= ANGLE_MIN_R:
                    g["angle"], g["angle_r"] = round(a, 2), round(r, 3)
    grp = groups_of(alike_matrix(members))
    for g, k in zip(members, grp):
        g["group"] = k
    flags, cands = [], []
    cand_mask = np.zeros(thread.shape, bool)
    by_group: dict = {}
    for g in members:
        by_group.setdefault(g["group"], []).append(g)
    for k, mem in by_group.items():
        if len(mem) < 2:
            for g in mem:
                g["odd"] = []
            continue
        odd = {t: [False] * len(mem) for t in TREATMENTS}
        odd["colour"] = odd_members([g["cls"] for g in mem])
        odd["kind"] = odd_members([g["kind"] for g in mem])
        odd["rim"] = odd_members([g["rim"] for g in mem])
        odd["angle"] = odd_members([g if g["angle"] is not None else None for g in mem], angle_disagree)
        for j, g in enumerate(mem):
            g["odd"] = [t for t in TREATMENTS if odd[t][j]]
            m = masks[g["id"]]
            pts = spread_points(m, px_per_mm)
            cand_mask |= m
            cands += [list(to_mm(x, y, px_per_mm, pad_mm)) for x, y in pts]
            if g["odd"]:
                for x, y in pts:
                    xm, ym = to_mm(x, y, px_per_mm, pad_mm)
                    flags.append({"x_mm": xm, "y_mm": ym, "family": "shape", "strength": float(len(g["odd"])),
                                  "shape": g["id"], "group": k, "odd": g["odd"], "cls": g["cls"],
                                  "kind": g["kind"], "rim": g["rim"], "angle": g["angle"],
                                  "area_mm2": round(g["area_px"] / px_per_mm ** 2, 2)})
    for g in members:
        g["area_mm2"] = round(g["area_px"] / px_per_mm ** 2, 3)
        g["group_size"] = len(by_group[g["group"]])
    return flags, cands, cand_mask, members


def stitches_sha(design: dict) -> str:
    """The fault-reader workers' hash of a design's stitches."""
    return hashlib.sha256(json.dumps([[s["x"], s["y"], s["type"]] for s in design["stitches"]]).encode()).hexdigest()


def class_of_colours(colors: list[dict], classes: list) -> list[int]:
    """Each spool's nearest colour class (the in-fill worker's `cls_of`)."""
    return [int(np.argmin([sum((a - b) ** 2 for a, b in zip((c["r"], c["g"], c["b"]), k)) for k in classes]))
            for c in colors]


# --------------------------------------------------------------------- run ----

def design_path(iid: str, runs: list[Path]) -> Path:
    slug = iid.split("_", 1)[1]
    for r in runs:
        p = Path(r) / f"{slug}.json"
        if p.exists():
            return p
    raise FileNotFoundError(f"{iid}: no stored design {slug}.json under {runs}")


def run(items: list[str], labels: Path, design_runs: list[Path], out: Path, letter: list[Path] | None = None) -> int:
    """Read each item's in-fill rasters and stored design, write the harness
    files. F2 is the in-fill record in `labels` itself when it exists."""
    from tools.letter_fault_reader import colour_classes
    out.mkdir(parents=True, exist_ok=True)
    bad = 0
    for iid in items:
        lab = np.load(labels / f"{iid}.labels.npz")
        thread, kind = lab["thread"], lab["kind"]
        dpath = design_path(iid, design_runs)
        stored = json.loads(dpath.read_text(encoding="utf-8"))
        design = stored["design"]
        sha = stitches_sha(design)
        rec_path = labels / f"{iid}.flags.json"
        infill = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else None
        want = infill.get("stitches_sha256") if infill else None
        if want is None:
            for d in letter or []:
                q = Path(d) / f"{iid}.flags.json"
                if q.exists():
                    want = json.loads(q.read_text(encoding="utf-8")).get("stitches_sha256")
                    break
        if want != sha:
            print(iid, f"REFUSED: stored design stitches {sha[:12]} != rasters' {str(want)[:12]}", flush=True)
            bad += 1
            continue
        classes = colour_classes(design["colors"])
        segs = segments(design, thread.shape, class_of_colour=class_of_colours(design["colors"], classes))
        flags, cands, cand_mask, mem = read_shapes(thread, kind, segs)
        f2_flags, f2_cands = [], []
        mz = np.load(labels / f"{iid}.mask.npz")
        if infill is not None:
            f2_flags = [{**f, "family": "space"} for f in infill.get("flags") or []]
            f2_cands = list(infill.get("candidates") or [])
            if "cand" in mz.files:
                cand_mask = cand_mask | mz["cand"].astype(bool)
        np.savez_compressed(out / f"{iid}.mask.npz", mask=mz["mask"].astype(bool), cand=cand_mask)
        odd_counts = {t: sum(1 for g in mem if t in (g.get("odd") or [])) for t in TREATMENTS}
        rec = {"item": iid, "reader": "inconsistency_fault_reader", "stitches_sha256": sha,
               "px_per_mm": PXMM, "pad_mm": PAD_MM, "f2_from": str(rec_path) if infill else None,
               "shapes": len(mem), "grouped": sum(1 for g in mem if g["group_size"] >= 2),
               "odd_shapes": sum(1 for g in mem if g.get("odd")), "odd_by_treatment": odd_counts,
               "f1_flags": len(flags), "f2_flags": len(f2_flags),
               "flags": flags + f2_flags, "candidates": cands + f2_cands,
               "members": [{k: g[k] for k in ("id", "cls", "group", "group_size", "area_mm2", "elong", "orient",
                                              "solidity", "kind", "rim", "angle", "angle_r", "odd")} for g in mem]}
        (out / f"{iid}.flags.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        print(iid, "shapes", len(mem), "grouped", rec["grouped"], "odd", rec["odd_shapes"], odd_counts,
              "flags F1", len(flags), "F2", len(f2_flags), "cands", len(cands) + len(f2_cands), flush=True)
    return 1 if bad else 0


# ----------------------------------------------------------------- analyse ----

def f1_only(rec: dict) -> dict:
    """The record with F2 (the in-fill reader's spaces) removed."""
    return {**rec, "flags": [f for f in rec["flags"] if f.get("family") == "shape"],
            "candidates": rec["candidates"][: _n_f1_cands(rec)]}


def _n_f1_cands(rec: dict) -> int:
    n_f2 = 0
    if rec.get("f2_from"):
        n_f2 = len(json.loads(Path(rec["f2_from"]).read_text(encoding="utf-8")).get("candidates") or [])
    return len(rec["candidates"]) - n_f2


def leave_one_out(rows: dict, radius: float, null: str = "chance_pick") -> dict:
    """Per-note pool with each pinned item dropped in turn."""
    from tools import fault_reader_harness as h
    pinned = [k for k, r in rows.items() if r["pins"]]
    return {k: h.pool_notes({j: r for j, r in rows.items() if j != k}, radius, null) for k in pinned}


def overlap(pins: list[dict], dirs: dict, radius: float) -> list[dict]:
    """Per target pin: which reader (name -> list of flag dirs) has a flag
    within `radius`; None where that reader has no record for the item."""
    from tools import fault_reader_harness as h
    out = []
    for p in pins:
        row = {"item": p["item"], "pin": p["pin"], "note_pin": p.get("note_pin")}
        for name, ds in dirs.items():
            rec = next((Path(d) / f"{p['item']}.flags.json" for d in ds
                        if (Path(d) / f"{p['item']}.flags.json").exists()), None)
            if rec is None:
                row[name] = None
                continue
            fl = json.loads(rec.read_text(encoding="utf-8")).get("flags") or []
            row[name] = bool(h.hits([p], fl, radius)[0]) if fl else False
        out.append(row)
    return out


def analyse(sittings: list[tuple[Path, str]], out: Path, others: dict, radius: float = 3.0) -> dict:
    """The pre-registered score: the harness on the reader (F1 + F2), the same
    on F1 alone, leave-one-item-out, and per-pin overlap with `others`
    (reader name -> list of flag dirs). `sittings` = [(marks.json, prefix)]."""
    import shutil
    import tempfile
    from tools import fault_reader_harness as h
    marks = [(json.loads(Path(m).read_text(encoding="utf-8")), px) for m, px in sittings]
    union = h.score_many([(mk, out, px) for mk, px in marks], "inconsistency")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        for f in out.glob("*.flags.json"):
            rec = json.loads(f.read_text(encoding="utf-8"))
            (t / f.name).write_text(json.dumps(f1_only(rec)), encoding="utf-8")
            z = np.load(out / f.name.replace(".flags.json", ".mask.npz"))
            lab = np.load(Path(rec["f2_from"]).with_name(f.name.replace(".flags.json", ".mask.npz"))) \
                if rec.get("f2_from") else None
            cand = z["cand"].astype(bool)
            if lab is not None and "cand" in lab.files:
                cand = cand & ~lab["cand"].astype(bool)
            np.savez_compressed(t / f.name.replace(".flags.json", ".mask.npz"), mask=z["mask"], cand=cand)
        f1 = h.score_many([(mk, t, px) for mk, px in marks], "inconsistency")
        shutil.rmtree(t, ignore_errors=True)
    pins = [p for mk, px in marks for p in h.select_inconsistency_pins(mk, px)]
    r = str(radius)
    res = {"radius_mm": radius,
           "verdict_line": union["pooled_notes"][r]["chance_pick"],
           "union": union, "f1_only": {k: f1[k] for k in ("pooled", "pooled_notes", "precision")},
           "f1_only_items": {k: {"hit": v["by_radius"][r]["hit"], "pins": v["pins"], "flags": v["flags"],
                                 "chance_pick": v["by_radius"][r].get("chance_pick")}
                             for k, v in f1["items"].items() if v["pins"]},
           "loo": leave_one_out(union["items"], radius),
           "overlap": overlap(pins, {"inconsistency": [out], **others}, radius)}
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("analyse")
    s.add_argument("--marks", type=Path, action="append", required=True)
    s.add_argument("--prefix", action="append", required=True)
    s.add_argument("--out", type=Path, required=True, help="this reader's out dir")
    s.add_argument("--reader", action="append", default=[], help="NAME=DIR, repeat (overlap)")
    s.add_argument("--json", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--labels", type=Path, required=True, help="the in-fill reader's out dir")
    r.add_argument("--design-run", type=Path, action="append", required=True,
                   help="stored designs <slug>.json (pro_run, logo_run); repeat")
    r.add_argument("--letter", type=Path, action="append", help="letter-reader dirs: stitch hash for refused items")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--only", action="append", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "analyse":
        others: dict = {}
        for kv in a.reader:
            name, _, d = kv.partition("=")
            others.setdefault(name, []).append(Path(d))
        res = analyse(list(zip(a.marks, a.prefix)), a.out, others)
        a.json.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("verdict line (per note, chance_pick, 3 mm):", res["verdict_line"])
        print("F1 only:", res["f1_only"]["pooled_notes"]["3.0"]["chance_pick"])
        for k, v in res["loo"].items():
            print("  without", k, v)
        return 0
    return run(a.only, a.labels, a.design_run, a.out, a.letter)


if __name__ == "__main__":
    sys.exit(main())
