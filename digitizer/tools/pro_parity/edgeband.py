"""Edge coverage — how much of the band just inside a boundary carries no thread.

THE QUESTION. Along a shape's boundary, how much of the band just inside it has
no thread on it, and how does that compare to what a professional digitiser
leaves on the same artwork? Two numbers: the bare FRACTION of the band, and the
longest contiguous bare ARC along the boundary.

WHY THE ARC IS THE HEADLINE. Five percent of a band left bare as scattered
pinpricks is invisible; five percent as one 8 mm strip down the side of a letter
is the defect. `barecircle.py` makes exactly this argument for shape interiors
(:14-16) and then declines to make it for edges — its `clearance` is
`min(dist_out, dist_thread - w/2)` (:133-137), which caps any point's score at
its own distance from the boundary, so a continuous uncovered perimeter band is
indistinguishable from flawless work. This module answers the case that one
discounts. Nothing here supersedes it; they measure different failures.

WHY BOTH SIDES GO THROUGH ONE READER. `side_mask` delegates to
`artfidelity.pro_mask` for pro and ours alike. `prep_both.py` once hand-rolled a
second copy of a shared block and silently dropped three keys from it for weeks
(fixed 2026-08-18, 5328257); one rasteriser is how that does not happen here.

WHAT THIS DOES NOT DO. It sets no threshold. "How much bare edge is too much" is
a cloth question and ROADMAP gate 1 says cloth settles it, so the probe reports
millimetres at three band widths and lets the professional's own files be the
tolerance. It adds no key to the scorecard's WEIGHTS and changes no engine
behaviour.
"""
from pathlib import Path
import csv
import json
import sys

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artfidelity import RES, SHIFT_MM, art_mask, best_iou, pro_mask  # noqa: E402
from enginefidelity import MASK_PAD_PX, _place  # noqa: E402

# Reported at all three, never one. Picking one would invent a physical
# constant; gate 1 says cloth settles those. Three widths also separate a thin
# uniform shortfall (visible at 0.2, washed out at 0.8) from a genuinely wide
# gap. At RES = 10 px/mm these are 2, 4 and 8 pixels.
BAND_WIDTHS_MM = (0.2, 0.4, 0.8)


def band_mask(shape: np.ndarray, w_px: float) -> np.ndarray:
    """Every pixel of `shape` within `w_px` of being outside it.

    Exact Euclidean, not a morphological erosion: a square structuring element
    measures Chebyshev distance, so a 4 px band would reach 5.7 px into a
    corner. `barecircle.py` uses the same EDT convention for the same reason.
    """
    if not shape.any():
        return np.zeros(shape.shape, bool)
    return shape & (distance_transform_edt(shape) <= w_px)


def bare_frac(band: np.ndarray, thread: np.ndarray) -> float | None:
    """Share of `band` with no thread on it, or None for an empty band.

    None rather than 0.0 deliberately: an empty band is a shape too small to
    measure, and 0.0 would read as "perfectly covered" in every table it
    reaches.
    """
    n = int(np.count_nonzero(band))
    if not n:
        return None
    return float(np.count_nonzero(band & ~thread) / n)


def _rings(shape: np.ndarray) -> list[np.ndarray]:
    """Every boundary ring of `shape` as an (N, 2) array of (row, col).

    `CHAIN_APPROX_NONE` because an arc length is a walk along real pixels — the
    simplified chain would drop the very pixels being measured. `RETR_CCOMP`
    returns holes as their own rings, and a hole's boundary is an edge like any
    other.
    """
    cs, _h = cv2.findContours(shape.astype(np.uint8), cv2.RETR_CCOMP,
                              cv2.CHAIN_APPROX_NONE)
    return [c.reshape(-1, 2)[:, ::-1] for c in cs if len(c) >= 2]


def _runs(flags: np.ndarray) -> list[list[int]]:
    """Maximal runs of True in a CLOSED sequence, as index lists.

    Rings close, so a run straddling index 0 is one run. Rotating the sequence
    to start at a False is what makes that fall out for free; an all-True ring
    has no False to rotate to and is returned whole.
    """
    n = len(flags)
    if not flags.any():
        return []
    if flags.all():
        return [list(range(n))]
    start = int(np.argmax(~flags))
    out, cur = [], []
    for k in range(n):
        i = (start + k) % n
        if flags[i]:
            cur.append(i)
        elif cur:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def bare_arcs(shape: np.ndarray, thread: np.ndarray, w_px: float,
              res: float = RES) -> list[float]:
    """Lengths in mm of every maximal boundary run further than `w_px` from thread.

    A boundary pixel is bare when the nearest thread pixel is more than `w_px`
    away. Distance rather than an inward-normal probe: a normal is ambiguous at
    a corner and wherever a ring doubles back, and two implementations would
    disagree there. An exact EDT has no such freedom.

    A run's length is the distance walked BETWEEN its pixels, so a lone bare
    pixel measures 0.0 and a 30 px strip measures 29 steps of 0.1 mm. That is
    the span a strip of that length actually occupies; counting the step off its
    final pixel would add a pixel of length that is not there.
    """
    if not shape.any():
        return []
    dist = (distance_transform_edt(~thread) if thread.any()
            else np.full(shape.shape, np.inf))
    out: list[float] = []
    for ring in _rings(shape):
        bare = dist[ring[:, 0], ring[:, 1]] > w_px
        if not bare.any():
            continue
        step = np.hypot(*(np.roll(ring, -1, axis=0) - ring).T) / res
        for run in _runs(bare):
            out.append(float(step[run[:-1]].sum()) if len(run) > 1 else 0.0)
    return out


def side_mask(csv_path) -> np.ndarray:
    """The thread raster for EITHER side. One reader, deliberately.

    `enginefidelity.engine_mask` is already `artfidelity.pro_mask` — the
    trim/jump semantics are identical on both sides — so naming it once here
    keeps a second copy from appearing. Sibling probes (bare.py, holecrop.py,
    forkprobe.py) all paint at THREAD_W_MM = 0.40; changing that constant
    anywhere means changing it in step or the directory stops agreeing about
    what "covered" means (artfidelity.py:55-57).
    """
    return pro_mask(csv_path)


def _summarise(shape, thread, w_mm, res=RES) -> dict:
    """The four numbers, for one band at one width."""
    w_px = w_mm * res
    band = band_mask(shape, w_px)
    arcs = bare_arcs(shape, thread, w_px, res)
    return {
        "width_mm": w_mm,
        "bare_frac": bare_frac(band, thread),
        "bare_arc_max_mm": round(max(arcs), 3) if arcs else 0.0,
        "bare_arc_p90_mm": round(float(np.percentile(arcs, 90)), 3) if arcs else 0.0,
        "band_mm2": round(int(np.count_nonzero(band)) / (res * res), 2),
    }


def art_band_rows(dirpath, widths_mm=BAND_WIDTHS_MM) -> list[dict]:
    """Edge coverage against the ARTWORK's own boundary, for both sides.

    The artwork is the only boundary neither side authored, which is the whole
    reason it is the headline: measuring against our own polygons would let our
    segmentation decide where "the edge" is — the same circularity that bars the
    recon lane, whose art.png is reconstructed from the pro's own stitches.

    Each side is aligned to the artwork by the shipped `best_iou` shift and
    measured on its own canvas. The art geometry is identical between the two;
    only its placement differs, and placement cannot change an arc length.

    `width_mm` subtracts MASK_PAD_PX because `pro_mask`'s canvas is the stitch
    span PLUS a fixed 8 px margin. Scaling the artwork to the canvas instead
    stretched it 0.8 mm wider than the engine on every design and gave a
    flawless reproduction art_missed 0.042 (enginefidelity.py:50-58).
    """
    d = Path(dirpath)
    art = d / "art.png"
    if not art.exists():
        return []
    rows = []
    for side, name in (("pro", "pro_stitches.csv"), ("ours", "ours_stitches.csv")):
        csv_path = d / name
        if not csv_path.exists():
            continue
        M = side_mask(csv_path)
        A = art_mask(art, (M.shape[1] - MASK_PAD_PX) / RES)
        _iou, _extra, _missed, dx_mm, dy_mm = best_iou(M, A)
        H = max(M.shape[0], A.shape[0]) + int(2 * SHIFT_MM * RES) + 4
        W = max(M.shape[1], A.shape[1]) + int(2 * SHIFT_MM * RES) + 4
        Mp = _place(M, H, W)
        Ap = _place(A, H, W, int(round(dx_mm * RES)), int(round(dy_mm * RES)))
        for w_mm in widths_mm:
            rows.append({"slug": d.name, "band": "art", "side": side,
                         **_summarise(Ap, Mp, w_mm)})
    return rows


def _poly_mask(poly, H, W, oy, ox, res=RES) -> np.ndarray:
    """Rasterise a shapely polygon into a canvas at a known pixel offset.

    `oy`/`ox` are where the side's own raster was placed, so the polygon lands
    in the same frame its own stitches did.
    """
    m = np.zeros((H, W), np.uint8)

    def px(coords):
        a = np.asarray(coords, np.float64)
        return np.column_stack([a[:, 0] * res + ox, a[:, 1] * res + oy]).astype(np.int32)

    parts = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    for p in parts:
        if p.geom_type != "Polygon":
            continue
        cv2.fillPoly(m, [px(p.exterior.coords)], 255)
        for ring in p.interiors:
            cv2.fillPoly(m, [px(ring.coords)], 0)
    return m.astype(bool)


def shape_band_rows(dirpath, widths_mm=BAND_WIDTHS_MM) -> list[dict]:
    """Edge coverage per OUR shape — the attribution number.

    Which shapes are short, and in which tier. The polygon is ours on BOTH
    sides, so this asks whether the pro laid thread where our shape claims its
    edge is. Where this and `art_band_rows` disagree IS the segmentation-shrink
    signal: our polygon landing inside the artwork's ink is invisible to any
    measure that uses our polygon as ground truth.

    Only our own side is measured here. Placing our polygons on the PRO's canvas
    needs a second registration path, and mixing `best_iou`'s whole-pixel shift
    with `scorecard.register`'s hill-climb is how two probes start disagreeing
    about where a shape is. The pro's side of the comparison is `art_band_rows`.

    KNOWN CLIP, carried forward. The canvas is the stitch raster plus 8 px, and
    `pro_mask` already padded 4 px a side, so a polygon reaching more than
    0.8 mm beyond the DESIGN-WIDE stitch bbox is silently cut off by `fillPoly`
    and its bare edge under-reported. Seen on a synthetic dir 2026-08-19: a
    polygon 2.4 mm past the last row read arcs of 17.4 / 17.0 / 0.00 mm at
    W = 0.2 / 0.4 / 0.8 — the 0.8 column collapsing because the clipped edge
    sits 0.6 mm from thread, not 2.4. The bbox is the union over every shape,
    so an interior shape cannot hit this; only a shape that both defines an
    extreme of the design and starves by more than 0.8 mm can. Treat a shape
    whose three widths disagree in that pattern as suspect, not as measured.
    """
    import shapely.wkt

    d = Path(dirpath)
    regions_path = d / "ours_regions.json"
    csv_path = d / "ours_stitches.csv"
    if not (regions_path.exists() and csv_path.exists()):
        return []
    regions = json.loads(regions_path.read_text())
    if not regions or "wkt" not in regions[0]:
        return []

    M = side_mask(csv_path)
    x0, y0 = _origin_mm(csv_path)
    H = M.shape[0] + 8
    W = M.shape[1] + 8
    Mp = _place(M, H, W)
    # `_place` centres; `pro_mask` itself pads 4 px inside its own raster.
    oy = (H - M.shape[0]) // 2 + 4 - y0 * RES
    ox = (W - M.shape[1]) // 2 + 4 - x0 * RES

    rows = []
    for r in regions:
        poly = shapely.wkt.loads(r["wkt"])
        if poly.is_empty:
            continue
        P = _poly_mask(poly, H, W, oy, ox)
        if not P.any():
            continue
        for w_mm in widths_mm:
            rows.append({"slug": d.name, "band": "shape", "side": "ours",
                         "shape_id": r.get("shape_id"), "tier": r.get("tier"),
                         "area_mm2": r.get("area_mm2"),
                         **_summarise(P, Mp, w_mm)})
    return rows


def _origin_mm(csv_path) -> tuple[float, float]:
    """The mm corner `pro_mask` measures its raster from.

    Two mins, duplicated from `pro_mask` because it returns only the mask —
    its docstring says "plus its mm origin" and the code does not. Guarded by
    `test_origin_agrees_with_the_rasteriser`, which pins a known stitch to a
    known pixel, so a change to the rasteriser's framing cannot drift this
    silently.
    """
    xs, ys = [], []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            xs.append(float(r["x_mm"])); ys.append(float(r["y_mm"]))
    return min(xs), min(ys)


def main():
    out_rows = []
    for arg in sys.argv[1:]:
        d = Path(arg)
        rows = art_band_rows(d) + shape_band_rows(d)
        if not rows:
            print(f"{d.name:22s} (no artifacts)", flush=True)
            continue
        out_rows += rows
        art = {(r["side"], r["width_mm"]): r for r in rows if r["band"] == "art"}
        for w in BAND_WIDTHS_MM:
            p = art.get(("pro", w)); o = art.get(("ours", w))
            if p and o:
                print(f"{d.name:22s} W={w:.1f}  pro arc {p['bare_arc_max_mm']:6.2f} mm"
                      f" · ours arc {o['bare_arc_max_mm']:6.2f} mm"
                      f" · pro frac {p['bare_frac']:.3f} · ours frac {o['bare_frac']:.3f}",
                      flush=True)
        with open(d / f"edgeband_{d.name}.csv", "w", newline="") as f:
            keys = sorted({k for r in rows for k in r})
            w_ = csv.DictWriter(f, fieldnames=keys); w_.writeheader(); w_.writerows(rows)
    if out_rows:
        print(f"\n{len(out_rows)} rows over "
              f"{len({r['slug'] for r in out_rows})} designs")


if __name__ == "__main__":
    main()
