"""Negative-space reader: WHERE thread fills the spaces of lettering.

    python -m tools.space_fault_reader run --labels DIR --out DIR [--only ITEM ...]
    python -m tools.fault_reader_harness score --fault space --marks M --flags DIR [--prefix C_ ...]

The fourth reader scored by `tools.fault_reader_harness` against Kent's
defect-marks pins, on the SAME pins as the letter reader (his closed, merged
and unreadable letters: `select_letter_pins`). The letter reader compares
topology, so it cannot see a bay filled solid: an S whose curves meet its
spine with thread changes no hole count (both of Kent's "the S doesn't have
spacing between the curves" pins were misses). This reader reads the SPACES
instead, the way `digitizer_core.glyph_read`'s `space` reading does for one
glyph, generalised to the whole design and to the gaps between shapes. What
is fixed before any result is `docs/space-fault-reader-2026-11-12.md`.

Per thread colour class `c`, with `S` the art's `c` shapes (8-connected, at
least `MIN_SHAPE_MM2`) and `T` the thread's `c` pixels (the top thread):

  * the SPACE RIDGE is the midline of `c`'s negative space, two parts:
      bay  the medial axis of each judged shape's own negative space, its
           convex hull less `S` (glyph_read's rule verbatim: the mouth of an
           E, the waist of an S, a counter);
      gap  the boundary between two judged shapes' nearest-pixel zones
           (their Voronoi line) where it lies inside the convex hull of the
           pair: the space between two letters, between a stroke and a
           border, not the field around them.
    Kept where the art leaves a clear circle of `SPACE_MIN_HALF_MM` (the
    ridge point is that far from any `S` pixel), and only BETWEEN inks: the
    point's clear circle fits inside the hull (the pair's, for a gap) with
    `SPACE_KEEP_HALF_MM` to spare (`enclosed`). Without that, glyph_read's
    hull ridge, applied to a whole field, runs along every shallow dent of an
    outline, midway between the ink and the hull's edge, where thread spill
    always reaches (found on the dev items, before any pinned item was read).
  * a ridge point is CLOSED when `c` thread lies within `SPACE_KEEP_HALF_MM`
    of it (glyph_read: the space survives only with a clear circle that big).
  * a FAULT is a connected run of closed ridge points longer than
    `BRIDGE_MIN_MM` (the letter reader's 1.5 filaments: one running stitch
    across a gap is travel, not a filled space).

A shape is judged where its thread sews it (`SEWN_FRAC` of its art carries
`c`, the letter reader's guard). Flags are spread along each fault, no two
within `SPACING_MM` (the edge reader's merge distance), first at the
fault's widest art space; strength = the fault's length, mm. The CANDIDATE
set, for the harness's `chance_pick` null, is every ridge run longer than
`BRIDGE_MIN_MM`, spread the same way: the places this reader could flag.

The reader runs no pipeline. It reads the letter reader's stored rasters
(`<item>.labels.npz`: `art` and `thread` class images at 12 px/mm, written by
`tools.letter_fault_reader run`, which refused any item whose re-run
stitches differed from the stored design) and its `<item>.mask.npz`, and
refuses an item whose letter-reader record is missing. Output, all in the
out dir: `<item>.flags.json` (harness format plus `candidates`) and
`<item>.mask.npz` (`mask` = thread pixels, `cand` = candidate ridge pixels).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

PXMM = 12.0                                           # the review render's scale (pins' frame)
PAD_MM = 2.0
THREAD_MM = 0.4                                       # == stitchviz.THREAD_MM
SPACE_MIN_HALF_MM = 0.15                              # == glyph_read.SPACE_MIN_HALF_MM
SPACE_KEEP_HALF_MM = 0.10                             # == glyph_read.SPACE_KEEP_HALF_MM
MIN_SHAPE_MM2 = 0.12                                  # == glyph_read.MIN_GLYPH_MM2 (letter reader's)
SEWN_FRAC = 0.5                                       # == letter_fault_reader.SEWN_FRAC
BRIDGE_MIN_MM = 1.5 * THREAD_MM                       # == letter_fault_reader.BRIDGE_MIN_MM
SPACING_MM = 2.0                                      # == edge_fault_reader.MERGE_MM
UNSEWN = -1
EIGHT = np.ones((3, 3), bool)


# ------------------------------------------------------------ pure helpers ----

def to_mm(x: float, y: float, px_per_mm: float = PXMM, pad_mm: float = PAD_MM):
    """Render pixel -> the pins' frame (`defect_marks.mark_mm`)."""
    return round(float(x) / px_per_mm - pad_mm, 2), round(float(y) / px_per_mm - pad_mm, 2)


def shapes(art_c: np.ndarray, thr_c: np.ndarray, px_per_mm: float = PXMM):
    """-> (labels 1..n of the class's shapes of at least MIN_SHAPE_MM2, judged
    bool per label index 0..n)."""
    lab, n = ndi.label(art_c, EIGHT)
    if n:
        sizes = np.bincount(lab.ravel(), minlength=n + 1)
        keep = sizes >= MIN_SHAPE_MM2 * px_per_mm ** 2
        keep[0] = False
        lab, n = ndi.label(keep[lab], EIGHT)
    judged = np.zeros(n + 1, bool)
    if n:
        area = np.bincount(lab.ravel(), minlength=n + 1).astype(float)
        sewn = np.bincount(lab.ravel(), weights=thr_c.ravel().astype(float), minlength=n + 1)
        judged[1:] = sewn[1:] >= SEWN_FRAC * area[1:]
    return lab, n, judged


def _hull_pts(ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    pts = np.stack([xs, ys], 1).astype(np.int32).reshape(-1, 1, 2)
    return cv2.convexHull(pts).reshape(-1, 2)


def hull_depth(px: np.ndarray, py: np.ndarray, hull: np.ndarray) -> np.ndarray:
    """Per point (px, py): its distance to the edge of a convex polygon (cv2
    hull order, either orientation) when inside or on it, -1 outside. A hull
    of 1-2 points holds nothing."""
    px, py = np.asarray(px, float), np.asarray(py, float)
    if len(hull) < 3:
        return np.full(len(px), -1.0)
    x0, y0 = hull[:, 0].astype(float), hull[:, 1].astype(float)
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    ln = np.hypot(x1 - x0, y1 - y0)
    keep = ln > 0
    x0, y0, x1, y1, ln = x0[keep], y0[keep], x1[keep], y1[keep], ln[keep]
    out = np.full(len(px), -1.0)
    step = max(1, 2_000_000 // max(1, len(x0)))         # bound the (points x edges) array
    for s in range(0, len(px), step):
        qx, qy = px[s:s + step, None], py[s:s + step, None]
        d = ((x1 - x0)[None, :] * (qy - y0[None, :]) - (y1 - y0)[None, :] * (qx - x0[None, :])) / ln[None, :]
        pos, neg = (d >= -1e-9).all(1), (d <= 1e-9).all(1)
        out[s:s + step] = np.where(pos, d.min(1), np.where(neg, (-d).min(1), -1.0))
    return out


def enclosed(px, py, s_dist_px, hull: np.ndarray, px_per_mm: float = PXMM) -> np.ndarray:
    """A ridge point lies BETWEEN inks, not between an ink and the hull's
    edge: its clear circle (radius = its distance to the ink) fits inside the
    hull with `SPACE_KEEP_HALF_MM` to spare. A medial line between the ink
    and the hull's edge (a shallow dent of an outline, which thread spill
    always "closes") is equidistant from both and fails."""
    return hull_depth(px, py, hull) >= np.asarray(s_dist_px, float) + SPACE_KEEP_HALF_MM * px_per_mm


def space_ridge(lab: np.ndarray, n: int, judged: np.ndarray, px_per_mm: float = PXMM):
    """-> (ridge bool, kind uint8: 1 bay, 2 gap, 0 none, s_dist px). The
    class's negative-space midline (module docstring), before the closed test."""
    H, W = lab.shape
    S = lab > 0
    ridge = np.zeros((H, W), bool)
    kind = np.zeros((H, W), np.uint8)
    if not n:
        return ridge, kind, np.full((H, W), np.inf)
    s_dist, (iy, ix) = ndi.distance_transform_edt(~S, return_indices=True)
    near = lab[iy, ix]
    min_px = SPACE_MIN_HALF_MM * px_per_mm
    hulls: dict[int, np.ndarray] = {}
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None or not judged[i]:
            continue
        y0, y1 = max(0, sl[0].start - 1), min(H, sl[0].stop + 1)
        x0, x1 = max(0, sl[1].start - 1), min(W, sl[1].stop + 1)
        m = lab[y0:y1, x0:x1] == i
        ys, xs = np.nonzero(m)
        hull = _hull_pts(ys, xs)
        hulls[i] = hull + np.array([x0, y0])
        if len(hull) < 3:
            continue
        hm = np.zeros(m.shape, np.uint8)
        cv2.fillConvexPoly(hm, hull.reshape(-1, 1, 2).astype(np.int32), 1)
        neg = (hm > 0) & ~S[y0:y1, x0:x1]
        if not neg.any():
            continue
        r = skeletonize(neg) & (s_dist[y0:y1, x0:x1] >= min_px)
        ys, xs = np.nonzero(r)
        ok = enclosed(xs, ys, s_dist[y0:y1, x0:x1][ys, xs], hull, px_per_mm)
        ys, xs = ys[ok] + y0, xs[ok] + x0
        ridge[ys, xs] = True
        kind[ys, xs] = 1
    # gap: the Voronoi line between two judged shapes, inside the pair's hull
    gy, gx, ga, gb = [], [], [], []
    for dy, dx in ((0, 1), (1, 0)):
        a = near[: H - dy, : W - dx]
        b = near[dy:, dx:]
        ok = (a != b) & ~S[: H - dy, : W - dx] & ~S[dy:, dx:] & judged[a] & judged[b] \
            & (s_dist[: H - dy, : W - dx] >= min_px)
        ys, xs = np.nonzero(ok)
        gy.append(ys)
        gx.append(xs)
        ga.append(np.minimum(a[ys, xs], b[ys, xs]))
        gb.append(np.maximum(a[ys, xs], b[ys, xs]))
    gy, gx, ga, gb = (np.concatenate(v) for v in (gy, gx, ga, gb))
    if len(gy):
        key = ga.astype(np.int64) * (n + 1) + gb
        order = np.argsort(key, kind="stable")
        gy, gx, ga, gb, key = gy[order], gx[order], ga[order], gb[order], key[order]
        cuts = np.flatnonzero(np.diff(key)) + 1
        for s, e in zip(np.r_[0, cuts], np.r_[cuts, len(key)]):
            a_, b_ = int(ga[s]), int(gb[s])
            pair = _hull_pts(np.r_[hulls[a_][:, 1], hulls[b_][:, 1]], np.r_[hulls[a_][:, 0], hulls[b_][:, 0]])
            inside = enclosed(gx[s:e], gy[s:e], s_dist[gy[s:e], gx[s:e]], pair, px_per_mm)
            ys, xs = gy[s:e][inside], gx[s:e][inside]
            ridge[ys, xs] = True
            kind[ys, xs] = 2
    return ridge, kind, s_dist


def spread(ys: np.ndarray, xs: np.ndarray, order: np.ndarray, spacing_px: float) -> list[int]:
    """Indices of a greedy subset of the points, taken in `order`, no two
    within `spacing_px`. Deterministic for a given order."""
    cell = max(1.0, spacing_px)
    grid: dict[tuple[int, int], list[int]] = {}
    out = []
    s2 = spacing_px ** 2
    for i in order:
        y, x = float(ys[i]), float(xs[i])
        cy, cx = int(y // cell), int(x // cell)
        clash = False
        for gy in (cy - 1, cy, cy + 1):
            for gx in (cx - 1, cx, cx + 1):
                for j in grid.get((gy, gx), ()):
                    if (ys[j] - y) ** 2 + (xs[j] - x) ** 2 < s2:
                        clash = True
                        break
                if clash:
                    break
            if clash:
                break
        if not clash:
            grid.setdefault((cy, cx), []).append(int(i))
            out.append(int(i))
    return out


def read_class(art_c: np.ndarray, thr_c: np.ndarray, px_per_mm: float = PXMM):
    """One class: -> (faults [{"ys", "xs", "sd", "kind", "len_mm"}], candidate
    runs [same]), pixel arrays per connected run."""
    lab, n, judged = shapes(art_c, thr_c, px_per_mm)
    ridge, kind, s_dist = space_ridge(lab, n, judged, px_per_mm)
    if not ridge.any():
        return [], []
    t_dist = ndi.distance_transform_edt(~thr_c) if thr_c.any() else np.full(thr_c.shape, np.inf)
    closed = ridge & (t_dist < SPACE_KEEP_HALF_MM * px_per_mm)
    min_len = BRIDGE_MIN_MM * px_per_mm

    def runs(mask):
        rl, k = ndi.label(mask, EIGHT)
        out = []
        for j, sl in enumerate(ndi.find_objects(rl), start=1):
            if sl is None:
                continue
            ys, xs = np.nonzero(rl[sl] == j)
            if len(ys) <= min_len:            # pixel count as length: 1 px ~ 1/px_per_mm
                continue
            ys, xs = ys + sl[0].start, xs + sl[1].start
            out.append({"ys": ys, "xs": xs, "sd": s_dist[ys, xs], "kind": kind[ys, xs],
                        "len_mm": len(ys) / px_per_mm})
        return out
    return runs(closed), runs(ridge)


def _points(rs: list[dict], px_per_mm: float, pad_mm: float, cls: int, flag: bool) -> list[dict]:
    out = []
    for r in rs:
        # widest art space first, then position: deterministic
        order = np.lexsort((r["xs"], r["ys"], -r["sd"]))
        for i in spread(r["ys"], r["xs"], order, SPACING_MM * px_per_mm):
            x, y = to_mm(r["xs"][i], r["ys"][i], px_per_mm, pad_mm)
            p = {"x_mm": x, "y_mm": y, "class": cls, "kind": "bay" if r["kind"][i] == 1 else "gap",
                 "space_mm": round(2.0 * float(r["sd"][i]) / px_per_mm, 3)}
            if flag:
                p["strength"] = round(float(r["len_mm"]), 3)
            out.append(p)
    return out


def read_spaces(art_lab: np.ndarray, thr_lab: np.ndarray, px_per_mm: float = PXMM,
                pad_mm: float = PAD_MM):
    """Every class: -> (flags strongest first, candidates, cand_mask)."""
    flags, cands = [], []
    cand_mask = np.zeros(thr_lab.shape, bool)
    for c in sorted(int(v) for v in np.unique(thr_lab) if v != UNSEWN):
        faults, ridge_runs = read_class(art_lab == c, thr_lab == c, px_per_mm)
        flags += _points(faults, px_per_mm, pad_mm, c, True)
        cands += _points(ridge_runs, px_per_mm, pad_mm, c, False)
        for r in ridge_runs:
            cand_mask[r["ys"], r["xs"]] = True
    flags.sort(key=lambda f: (-f["strength"], f["x_mm"], f["y_mm"]))
    return flags, cands, cand_mask


# --------------------------------------------------------------------- run ----

def run(items: list[str], labels_dir: Path, out: Path) -> int:
    """Read each item's letter-reader rasters, write the harness files."""
    out.mkdir(parents=True, exist_ok=True)
    bad = 0
    for iid in items:
        src = labels_dir / f"{iid}.flags.json"
        if not (src.exists() and (labels_dir / f"{iid}.labels.npz").exists()):
            print(iid, "REFUSED: no letter-reader record and rasters in", labels_dir, flush=True)
            bad += 1
            continue
        prov = json.loads(src.read_text(encoding="utf-8"))
        if prov.get("px_per_mm") != PXMM or prov.get("pad_mm") != PAD_MM:
            print(iid, "REFUSED: rasters not at", PXMM, "px/mm, pad", PAD_MM, flush=True)
            bad += 1
            continue
        lab = np.load(labels_dir / f"{iid}.labels.npz")
        flags, cands, cand_mask = read_spaces(lab["art"], lab["thread"])
        mask = np.load(labels_dir / f"{iid}.mask.npz")["mask"].astype(bool)
        np.savez_compressed(out / f"{iid}.mask.npz", mask=mask, cand=cand_mask)
        by = {}
        for f in flags:
            by[f["kind"]] = by.get(f["kind"], 0) + 1
        rec = {"item": iid, "reader": "space_fault_reader", "rasters_from": "letter_fault_reader",
               "tree_sha": prov.get("tree_sha"), "stitches_sha256": prov.get("stitches_sha256"),
               "px_per_mm": PXMM, "pad_mm": PAD_MM, "by_kind": by,
               "candidates_n": len(cands), "flags": flags, "candidates": cands}
        (out / f"{iid}.flags.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        print(iid, "flags", len(flags), by, "candidates", len(cands), flush=True)
    return 1 if bad else 0


PREDICTED = (("L_gaulke_roofing_hat", 6), ("L_proseal_hat", 2), ("L_gaulke_roofing_hat", 2))


def leave_one_out(rows: dict, radius: float, null: str = "chance_pick") -> dict:
    """Per target item left out: the per-note and per-pin pools without it."""
    from tools import fault_reader_harness as h
    out = {}
    for iid in [k for k, r in rows.items() if r["pins"]]:
        rest = {k: v for k, v in rows.items() if k != iid}
        out[iid] = {"notes": h.pool_notes(rest, radius, null), "pins": h.pool(rest, radius, null)}
    return out


def overlap(pins: list[dict], space_flags: dict, letter_flags: dict, radius: float) -> dict:
    """Per pin and per note: hit by this reader, by the letter reader, both,
    neither. `*_flags` = item -> flag list."""
    from tools import fault_reader_harness as h
    per_pin = []
    for p in pins:
        s = bool(h.hits([p], space_flags.get(p["item"], []), radius)[0])
        lt = bool(h.hits([p], letter_flags.get(p["item"], []), radius)[0])
        per_pin.append({"item": p["item"], "pin": p["pin"], "note_pin": p["note_pin"], "space": s, "letter": lt})
    notes: dict = {}
    for r in per_pin:
        k = (r["item"], r["note_pin"])
        n = notes.setdefault(k, {"pins": 0, "space": 0, "letter": 0})
        n["pins"] += 1
        n["space"] += r["space"]
        n["letter"] += r["letter"]

    def table(rs, sk="space", lk="letter"):
        t = {"both": 0, "space_only": 0, "letter_only": 0, "neither": 0}
        for r in rs:
            s, lt = bool(r[sk]), bool(r[lk])
            t["both" if s and lt else "space_only" if s else "letter_only" if lt else "neither"] += 1
        return t
    note_rows = [{"item": k[0], "note_pin": k[1], **v} for k, v in notes.items()]
    return {"per_pin": per_pin, "pins": table(per_pin), "notes_any_hit": table(note_rows),
            "per_note": note_rows}


def report(sources, letter_dirs: list[Path], radius: float = 3.0) -> dict:
    """The harness's score plus leave-one-out, the overlap table and the
    predicted pins (`docs/space-fault-reader-2026-11-12.md`)."""
    from tools import fault_reader_harness as h
    res = h.score_many(sources, "space")
    pins = [p for marks, _d, px in sources for p in h.select_space_pins(marks, px)]
    space_flags, letter_flags = {}, {}
    for _m, d, _p in sources:
        for f in Path(d).glob("*.flags.json"):
            rec = json.loads(f.read_text(encoding="utf-8"))
            space_flags[rec.get("item") or f.name[: -len(".flags.json")]] = rec["flags"]
    for d in letter_dirs:
        for f in Path(d).glob("*.flags.json"):
            rec = json.loads(f.read_text(encoding="utf-8"))
            letter_flags[rec.get("item") or f.name[: -len(".flags.json")]] = rec["flags"]
    res["leave_one_out"] = {str(r): leave_one_out(res["items"], r) for r in (radius,)}
    res["overlap"] = overlap(pins, space_flags, letter_flags, radius)
    near = {(p["item"], p["pin"]): p for p in pins}
    res["predicted"] = [{"item": i, "pin": k,
                         "nearest_flag_mm": (lambda d: None if not np.isfinite(d) else round(float(d), 2))(
                             h.nearest_mm([near[(i, k)]], space_flags.get(i, []))[0])}
                        for i, k in PREDICTED if (i, k) in near]
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("report", help="--marks/--flags/--prefix repeat together, one per sitting")
    rp.add_argument("--marks", type=Path, action="append", required=True)
    rp.add_argument("--flags", type=Path, action="append", required=True)
    rp.add_argument("--prefix", action="append", required=True)
    rp.add_argument("--letter-flags", type=Path, action="append", default=[],
                    help="a dir of the letter reader's <item>.flags.json, for the overlap table")
    rp.add_argument("--json", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--labels", type=Path, required=True,
                   help="a letter_fault_reader out dir (<item>.labels.npz, .mask.npz, .flags.json)")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--only", action="append", default=[], help="item id; default every item in --labels")
    a = ap.parse_args(argv)
    if a.cmd == "report":
        if not len(a.marks) == len(a.flags) == len(a.prefix):
            ap.error("--marks, --flags and --prefix must repeat together")
        res = report([(json.loads(m.read_text(encoding="utf-8")), f, px)
                      for m, f, px in zip(a.marks, a.flags, a.prefix)], a.letter_flags)
        a.json.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        for key in ("pooled", "pooled_notes", "precision"):
            for rad, by in res[key].items():
                print(f"{key} r={rad}: {by}")
        print("overlap", res["overlap"]["pins"], res["overlap"]["notes_any_hit"])
        print("predicted", res["predicted"])
        return 0
    items = a.only or sorted(p.name[: -len(".labels.npz")] for p in a.labels.glob("*.labels.npz"))
    return run(items, a.labels, a.out)


if __name__ == "__main__":
    sys.exit(main())
