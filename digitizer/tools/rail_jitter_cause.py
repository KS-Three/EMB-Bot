"""rail_jitter_cause: what a high `letter_band.rail_jitter` reading on a letter IS
(2026-10-25, `.claude/memory/marine-stem-rails-2026-10-25.md`).

WHY IT EXISTS. #1052 (`docs/lettering-10mm-up-2026-10-23.md`) read Becker
MARINE's M at a rail-jitter p90 of 0.19-0.25 mm against the pro's 0.03-0.05,
and the obvious reading was "our stem rails wobble". They do not. Measured on
the four MARINE files at the pro's widths, every station over 0.15 mm on our
side falls into one of three bins, and the bin a stem wobble would land in --
a rail off its line on a STRAIGHT outline edge -- is empty:

  corner    an outline vertex turning more than CORNER_TURN_DEG sits within
            CORNER_MM of a point of the 9-station window: the rail turns a
            corner inside one column (the slab's reflex notch, the M's V
            crotch, an A's counter and feet). The pro cuts a new piece at
            every notch (`big-letter-construction-2026-10-24`), so each of his
            pieces is straight and his letter reads ~0.03 -- construction,
            not a smoother edge;
  stray     a window point lies more than STRAY_MM from the outline: a split
            leg or a short stitch that is not on a rail at all was read as
            one (`rail_jitter` takes every other penetration as a rail);
  straight  neither -- a rail off its line on a straight (or smoothly
            curved) edge. This is the only bin that is wobble.

`stem_window` is the reading to quote for "are the stems straight", on any
machine file, ours or the pro's: per straight piece (letter_pieces' upright
pieces), the rail ends whose y lies in the stem window -- below the sheared
slab (MARINE's top ~25% of the cap), above the baseline ends -- through a
total-least-squares line, residual RMS in mm. Ours 0.013-0.04 (the DST's
0.1 mm rounding), the pro's 0.000 on the same four files.

ONE READER. The station read is `letter_band.rail_jitter`'s, imported, not
copied (`column_segments`, `WIN`): the stations classified are the stations
#1052 counted. `fused` reads them after `letter_pieces.fuse` (split legs
merged, so a split cross is one cross); raw is what #1052 read.

  python -m tools.rail_jitter_cause --art ART --width MM [--garment G]
      [--pro FILE.dst] [--rows Y0 Y1] [--min-height MM] [--set KEY=JSON ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools import letter_pieces as LP  # noqa: E402
from tools.letter_band import WIN, column_segments  # noqa: E402

OVER_MM = 0.15          # what #1052's table and edge_wobble ring as visible
CORNER_TURN_DEG = 20.0  # an outline vertex turning more than this is a corner
CORNER_MM = 0.6         # ... and a window point this close to one reads it
STRAY_MM = 0.6          # a rail sits at the pull (~0.3) from its outline
STEM_TOP = 0.35         # stem window, fractions of the letter's height (y down)
STEM_BOTTOM = 0.08
STEM_MIN_N = 10         # rail ends a piece side needs in the window to be read
END_TRIM_MM = 1.0       # a piece's first and last mm of spine are its ends
CAUSES = ("corner", "stray", "straight")


# ------------------------------------------------------------------ stations
def stations(seqs, fused: bool = True) -> list[tuple[float, np.ndarray]]:
    """`rail_jitter`'s stations with their windows: [(|residual| mm, window (WIN, 2))]."""
    out = []
    for s in seqs:
        pts = np.asarray(s, float)
        if fused and len(pts) > 2:
            pts = LP.fuse(pts)
        for i, j in column_segments(pts):
            seg = pts[i:j]
            for rail in (seg[0::2], seg[1::2]):
                for k in range(0, len(rail) - WIN + 1):
                    w = rail[k:k + WIN]
                    c = w.mean(0)
                    _, _, vt = np.linalg.svd(w - c)
                    out.append((float(abs((w[WIN // 2] - c) @ vt[1])), w))
    return out


def corners(poly, turn_deg: float = CORNER_TURN_DEG) -> np.ndarray:
    """Every ring vertex of `poly` turning more than `turn_deg`, (n, 2)."""
    out = []
    for g in getattr(poly, "geoms", [poly]):
        for ring in (g.exterior, *g.interiors):
            C = np.asarray(ring.coords, float)[:-1]
            n = len(C)
            for i in range(n):
                u, v = C[i] - C[i - 1], C[(i + 1) % n] - C[i]
                if np.hypot(*u) < 1e-9 or np.hypot(*v) < 1e-9:
                    continue
                t = math.degrees(abs(math.atan2(u[0] * v[1] - u[1] * v[0], float(u @ v))))
                if t > turn_deg:
                    out.append(C[i])
    return np.array(out, float).reshape(-1, 2)


def cause(window: np.ndarray, corner_pts: np.ndarray, poly) -> str:
    """`corner` | `stray` | `straight` for one station's window (see the module doc)."""
    from shapely.geometry import Point
    if len(corner_pts):
        d = np.hypot(*(corner_pts[None, :, :] - window[:, None, :]).transpose(2, 0, 1))
        if float(d.min()) < CORNER_MM:
            return "corner"
    bd = poly.boundary
    if max(bd.distance(Point(*p)) for p in window) > STRAY_MM:
        return "stray"
    return "straight"


def classify(poly, seqs, fused: bool = True, over: float = OVER_MM) -> dict:
    """One letter: its outline and its satin runs -> the #1052 reading and its causes."""
    st = stations(seqs, fused)
    C = corners(poly)
    counts = dict.fromkeys(CAUSES, 0)
    straight = []
    for r, w in st:
        if r <= over:
            continue
        k = cause(w, C, poly)
        counts[k] += 1
        if k == "straight":
            straight.append(round(r, 3))
    res = np.array([r for r, _w in st])
    return {"stations": len(st), "p90": float(np.percentile(res, 90)) if len(res) else None,
            "over": int((res > over).sum()) if len(res) else 0, **counts, "straight_mm": straight}


# ------------------------------------------------------------- stem window
def _tls_rms(P: np.ndarray) -> float:
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    return float(np.sqrt((((P - c) @ vt[1]) ** 2).mean()))


def stem_window(letter: dict, top: float = STEM_TOP, bottom: float = STEM_BOTTOM,
                min_n: int = STEM_MIN_N) -> list[float]:
    """A `letter_pieces.read` letter -> each upright piece side's rail RMS (mm) about
    its own line, over the rail ends inside the stem window."""
    y0, y1 = letter["bbox"][1], letter["bbox"][3]
    lo, hi = y0 + top * (y1 - y0), y1 - bottom * (y1 - y0)
    out = []
    for pi, p in enumerate(letter["pieces"]):
        if p["role"] != "upright":
            continue
        cr = [c for c, k in zip(letter["crosses"], letter["piece_of_cross"]) if k == pi]
        mids = np.array([(np.array(a) + np.array(b)) / 2 for a, b in cr])
        cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(mids, axis=0).T))])
        keep = (cum >= END_TRIM_MM) & (cum <= cum[-1] - END_TRIM_MM)
        ax = math.radians(p["axis_deg"])
        n = np.array([-math.sin(ax), math.cos(ax)])
        sides = ([], [])
        for (a, b), k in zip(cr, keep):
            a, b = np.array(a), np.array(b)
            if not k:
                continue
            if (a - b) @ n < 0:
                a, b = b, a
            for side, q in zip(sides, (a, b)):
                if lo <= q[1] <= hi:
                    side.append(q)
        out += [_tls_rms(np.array(s)) for s in sides if len(s) >= min_n]
    return out


def file_letters(path, rows=(0.6, 1.0), min_height: float = 8.0) -> list[dict]:
    """A machine file's letters (letter_pieces' own), left to right."""
    res = LP.read(Path(path), rows=rows)
    Ls = [L for L in res["letters"] if L["bbox"][3] - L["bbox"][1] >= min_height]
    return sorted(Ls, key=lambda L: L["bbox"][0])


def _clip(runs, bb, pad: float = 0.3) -> list[np.ndarray]:
    out = []
    for r in runs:
        P = r["pts"]
        m = ((P[:, 0] >= bb[0] - pad) & (P[:, 0] <= bb[2] + pad)
             & (P[:, 1] >= bb[1] - pad) & (P[:, 1] <= bb[3] + pad))
        cur: list = []
        for p, k in zip(P, m):
            if k:
                cur.append(p)
                continue
            if len(cur) > 2:
                out.append(np.array(cur))
            cur = []
        if len(cur) > 2:
            out.append(np.array(cur))
    return out


def file_jitter(path, rows=(0.6, 1.0), min_height: float = 8.0, fused: bool = True) -> list[dict]:
    """Per letter of a machine file (no outline to classify against): the
    reading and the stem window, each letter's stitches clipped to its own box."""
    runs = LP.runs_of(Path(path))
    out = []
    for L in file_letters(path, rows, min_height):
        res = np.array([r for r, _w in stations(_clip(runs, L["bbox"]), fused)])
        sw = stem_window(L)
        out.append({"bbox": L["bbox"], "p90": float(np.percentile(res, 90)) if len(res) else None,
                    "stem_rms": float(np.median(sw)) if sw else None, "stem_sides": len(sw)})
    return out


# ------------------------------------------------------------------- driver
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--art", type=Path, required=True)
    ap.add_argument("--width", type=float, required=True)
    ap.add_argument("--garment", default="hat_front")
    ap.add_argument("--pro", type=Path, help="the pro's machine file of the same art")
    ap.add_argument("--rows", nargs=2, type=float, default=(0.6, 1.0), metavar=("Y0", "Y1"),
                    help="letters whose centre lies in these fractions of the design's height")
    ap.add_argument("--min-height", type=float, default=8.0)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    from tools import pro_pair as pp
    import tempfile
    from digitizer_core.export import write_dst
    d = pp.digitize(a.art, a.width, a.garment, pp.parse_sets(a.set))
    runs_by: dict = {}
    for _b, run in d.plan.iter_runs():
        if run.kind == "satin" and len(run.points) > 2:
            runs_by.setdefault(run.shape_id, []).append(np.asarray(run.points, float))
    regs = [r for r in d.result.regions if r.shape_id in runs_by]
    ys = [v for r in regs for v in (r.polygon.bounds[1], r.polygon.bounds[3])]
    ylo, yhi = min(ys), max(ys)
    row = []
    for r in regs:
        x0, y0, x1, y1 = r.polygon.bounds
        f = ((y0 + y1) / 2 - ylo) / max(yhi - ylo, 1e-9)
        if y1 - y0 >= a.min_height and a.rows[0] <= f <= a.rows[1]:
            row.append(r)
    row.sort(key=lambda r: r.polygon.bounds[0])
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "ours.dst"
        write_dst(d.plan, dst)
        ours_file = file_jitter(dst, tuple(a.rows), a.min_height)
    pro = file_jitter(a.pro, tuple(a.rows), a.min_height) if a.pro else []
    # files are matched to our regions by left-to-right order: only when the counts agree
    ours_file = ours_file if len(ours_file) == len(row) else []
    pro = pro if len(pro) == len(row) else []
    out = {"art": a.art.name, "width_mm": a.width, "garment": a.garment,
           "stitches": d.plan.stats.stitch_count, "trims": d.plan.stats.trims, "letters": []}
    for i, r in enumerate(row):
        poly = r.polygon
        out["letters"].append({
            "shape_id": r.shape_id, "letterform_prior": r.meta.get("letterform_prior"),
            "raw": classify(poly, runs_by[r.shape_id], fused=False),
            "fused": classify(poly, runs_by[r.shape_id], fused=True),
            "ours_stem_rms": ours_file[i]["stem_rms"] if i < len(ours_file) else None,
            "pro_p90": pro[i]["p90"] if i < len(pro) else None,
            "pro_stem_rms": pro[i]["stem_rms"] if i < len(pro) else None})
    if a.json:
        print(json.dumps(out, indent=1))
        return 0
    f3 = lambda v: "  -  " if v is None else f"{v:.3f}"  # noqa: E731
    print(f"{out['art']} at {a.width} mm ({a.garment}): {out['stitches']} stitches, {out['trims']} trims")
    print("  letter      prior   | rail_jitter p90 raw / fused / pro | fused >0.15: corner stray straight"
          " | stem RMS ours / pro")
    for L in out["letters"]:
        fz = L["fused"]
        print(f"  {L['shape_id']:10s} {str(L['letterform_prior']):7s} | {f3(L['raw']['p90'])} / "
              f"{f3(fz['p90'])} / {f3(L['pro_p90'])} | {fz['corner']:4d} {fz['stray']:4d} {fz['straight']:4d}"
              f" {fz['straight_mm'] or ''} | {f3(L['ours_stem_rms'])} / {f3(L['pro_stem_rms'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
