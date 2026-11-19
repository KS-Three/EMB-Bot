"""satin_census: segment a stitch file into satin PIECES and describe a junction.

    python -m tools.satin_census --pro mfab_hat --at 35,6 --at 45,12.5
    python -m tools.satin_census --ours mfab_hat --width 104.9 --at 35,6 [--json OUT]
    python -m tools.satin_census --ours mfab_hat --width 104.9 --validate

Numbers only: nothing here draws a picture, and a professional's file read
from the committed zip stays in the session's scratch (tests/test_no_new_pro_renders).

Built 2026-11-19 for the MFab top line (docs/mfab-top-line-faults-2026-11-19.md):
five grader faults share one construction, the satin ladder's junction, and a
build needs to know how the professional sews the same junction. A chain
heuristic could not read his F arm (groups of 5-6 stitches interleaved in one
long run), so this reader works on THROWS, not on runs:

1. A needle-down run is a polyline; consecutive collinear segments (a split
   stitch) are merged into one throw (`throws`).
2. Two consecutive throws are one satin step when both are at least
   `MIN_THROW_MM` long, they are anti-parallel within `PAIR_DEG` (the cross
   angle varies slowly), the midpoint moves at most `MAX_STEP_MM` (a
   continuous centreline), their lengths are comparable, and the centreline
   does not turn back on itself (`_steps_ok`). A PIECE is a maximal chain of
   such steps of at least `MIN_THROWS` throws. A direction change, a reversal
   (a stem's second pass), a width jump or an interleaved other piece each
   end a piece; the census is over pieces, so a piece interleaved with
   another in one run is still read whole when each stretch is long enough.
3. A piece's cross angle (axial mean of its throws), length (its centreline),
   width (median throw), same-side pitch and covered polygon (its triangles,
   a half thread wider) describe it; `relate` says, for two pieces at a
   junction, which runs through and how far the other butts into or stops
   short of it.

`--validate` digitizes OUR file and compares the pieces with the ladder's
own bars (every `stage6_satin.satin_stroke` result, recorded while the
pipeline runs): the ground truth the reader must reproduce before its reading
of a professional's file means anything.

Layers: every needle-down segment of the chosen thread drawn 0.4 mm wide at
20 px/mm and summed (the convention of the MFab fault table); mean over the
covered pixels in a disk, max, share 3 or more deep, covered mm2. Junction
points are mm from the top-left of the file's stitch extents.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MIN_THROW_MM = 0.3        # a throw shorter than this is a needle-hole jitter, not a satin cross
PAIR_DEG = 35.0           # consecutive throws anti-parallel within this
MAX_STEP_MM = 1.2         # midpoint step of a satin (a zigzag underlay steps ~1 mm)
WIDTH_RATIO = 2.2         # consecutive throw lengths within this ratio ...
WIDTH_ABS_MM = 0.9        # ... or this difference
COLLINEAR_DEG = 12.0      # a split stitch: consecutive segments within this
MIN_THROWS = 4            # shortest piece reported
TOP_PITCH_MM = 0.7        # same-side pitch at or under this is top satin; over it, underlay
LINE_MM = 0.4             # layer raster: thread width
PPM = 20                  # layer raster: px per mm


# ------------------------------------------------------------------ reading
@dataclass
class Run:
    pts: list            # [(x, y)] mm, y down
    thread: str          # thread label (pro: block index + colour; ours: thread number)
    rgb: tuple           # (r, g, b)
    kind: str = ""       # ours: the plan's run kind; pro: ""
    order: int = 0       # global index of pts[0] in sew order


def pro_runs(path) -> list[Run]:
    """Needle-down runs of a machine file, in sew order, with their thread colour."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    cols = [tuple(int(t.hex_color()[i:i + 2], 16) for i in (1, 3, 5)) for t in pat.threadlist]
    out, cur, block, n = [], [], 0, 0
    m = pystitch.COMMAND_MASK

    def flush():
        if len(cur) >= 2:
            rgb = cols[block] if block < len(cols) else (0, 0, 0)
            out.append(Run(list(cur), f"block{block}", rgb, "", n - len(cur)))
    for x, y, c in pat.stitches:
        cmd = c & m
        if cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
            n += 1
            continue
        flush()
        cur = []
        if cmd == pystitch.COLOR_CHANGE:
            block += 1
    flush()
    return out


def plan_runs(plan) -> list[Run]:
    """Our plan's runs as needle-down runs (a jump starts a new one)."""
    out, n = [], 0
    for b in plan.blocks:
        for r in b.runs:
            pts = [tuple(map(float, p)) for p in (r.points or [])]
            if len(pts) >= 2:
                out.append(Run(pts, str(b.thread_number), tuple(b.rgb), str(r.kind), n))
            n += len(pts)
    return out


def extents_top_left(runs: list[Run]) -> tuple[float, float]:
    xs = [p[0] for r in runs for p in r.pts]
    ys = [p[1] for r in runs for p in r.pts]
    return min(xs), min(ys)


def is_white(rgb) -> bool:
    return min(rgb) >= 200


# ------------------------------------------------------------------ throws
def throws(pts) -> list[tuple[int, int]]:
    """Index pairs (i, j): each throw runs pts[i] -> pts[j]; collinear
    consecutive segments (a split stitch) merge into one."""
    out = []
    i = 0
    n = len(pts)
    while i < n - 1:
        j = i + 1
        while j < n - 1:
            a = np.subtract(pts[j], pts[i])
            b = np.subtract(pts[j + 1], pts[j])
            la, lb = np.hypot(*a), np.hypot(*b)
            if la < 1e-9 or lb < 1e-9:
                j += 1
                continue
            cos = float(np.dot(a, b) / (la * lb))
            if cos < math.cos(math.radians(COLLINEAR_DEG)):
                break
            j += 1
        out.append((i, j))
        i = j
    return out


def _axial(deg_list, weights=None) -> float:
    """Axial (mod 180) mean in degrees, [0, 180)."""
    a = np.radians(np.asarray(deg_list, float) * 2.0)
    w = np.ones_like(a) if weights is None else np.asarray(weights, float)
    return float(np.degrees(math.atan2((w * np.sin(a)).sum(), (w * np.cos(a)).sum())) / 2.0) % 180.0


@dataclass
class Piece:
    run: int                      # index into the runs list
    thread: str
    t0: int                       # first throw index in the run
    t1: int                       # last throw index (inclusive)
    i0: int                       # first point index in the run
    i1: int                       # last point index (inclusive)
    order: int                    # global sew-order index of the first point
    ends: list = field(default_factory=list)   # throw segments [(a, b)]
    mids: list = field(default_factory=list)   # throw midpoints
    width_mm: float = 0.0
    width_max_mm: float = 0.0
    cross_deg: float = 0.0
    cross_span_deg: float = 0.0   # max deviation of a throw from cross_deg
    length_mm: float = 0.0
    pitch_mm: float = 0.0         # same-side pitch
    top: bool = True
    _poly: object = None

    @property
    def n(self) -> int:
        return self.t1 - self.t0 + 1

    def polygon(self):
        """Covered area: the triangles of consecutive throws, a half thread wider."""
        if self._poly is None:
            from shapely.geometry import LineString, Polygon
            from shapely.ops import unary_union
            parts = []
            for (a, b), (c, d) in zip(self.ends, self.ends[1:]):
                q = Polygon([a, b, d, c])
                if not q.is_valid:
                    q = q.buffer(0)
                parts.append(q)
            parts += [LineString(s) for s in self.ends]
            self._poly = unary_union(parts).buffer(LINE_MM / 2)
        return self._poly

    def centreline(self):
        from shapely.geometry import LineString
        m = np.asarray(self.mids)
        k = max(1, min(4, len(m) // 3))
        sm = np.array([m[max(0, i - k):i + k + 1].mean(0) for i in range(len(m))])
        return LineString(sm) if len(sm) >= 2 else None

    def row(self, tl=(0.0, 0.0)) -> dict:
        c = self.centreline()
        a = (c.coords[0] if c else self.mids[0])
        b = (c.coords[-1] if c else self.mids[-1])
        return {"run": self.run, "thread": self.thread, "order": self.order, "throws": self.n,
                "top": self.top, "cross_deg": round(self.cross_deg, 1),
                "cross_span_deg": round(self.cross_span_deg, 1),
                "length_mm": round(self.length_mm, 2), "width_mm": round(self.width_mm, 2),
                "width_max_mm": round(self.width_max_mm, 2), "pitch_mm": round(self.pitch_mm, 2),
                "from": [round(a[0] - tl[0], 2), round(a[1] - tl[1], 2)],
                "to": [round(b[0] - tl[0], 2), round(b[1] - tl[1], 2)]}


def _steps_ok(pts, ta, tb) -> bool:
    a0, a1 = np.asarray(pts[ta[0]]), np.asarray(pts[ta[1]])
    b0, b1 = np.asarray(pts[tb[0]]), np.asarray(pts[tb[1]])
    da, db = a1 - a0, b1 - b0
    la, lb = float(np.hypot(*da)), float(np.hypot(*db))
    if la < MIN_THROW_MM or lb < MIN_THROW_MM:
        return False
    if float(np.dot(da, -db) / (la * lb)) < math.cos(math.radians(PAIR_DEG)):
        return False
    if np.hypot(*((a0 + a1) / 2 - (b0 + b1) / 2)) > MAX_STEP_MM:
        return False
    if max(la, lb) / min(la, lb) > WIDTH_RATIO and abs(la - lb) > WIDTH_ABS_MM:
        return False
    return True


def _same_side(pts, ta, tc) -> bool:
    """Throws two apart run the same way across the same column: parallel
    within `PAIR_DEG` and of comparable length."""
    da = np.subtract(pts[ta[1]], pts[ta[0]])
    dc = np.subtract(pts[tc[1]], pts[tc[0]])
    la, lc = float(np.hypot(*da)), float(np.hypot(*dc))
    if la < 1e-9 or lc < 1e-9:
        return False
    if float(np.dot(da, dc) / (la * lc)) < math.cos(math.radians(PAIR_DEG)):
        return False
    return max(la, lc) / min(la, lc) <= WIDTH_RATIO or abs(la - lc) <= WIDTH_ABS_MM


def _turns_back(mids, k: int) -> bool:
    """The centreline reverses at throw k: the step over the next two throws
    points against the step over the previous two (a second pass)."""
    if k < 2 or k + 2 >= len(mids):
        return False
    before = np.subtract(mids[k], mids[k - 2])
    after = np.subtract(mids[k + 2], mids[k])
    nb, na = np.hypot(*before), np.hypot(*after)
    if nb < 0.05 or na < 0.05:
        return False
    return float(np.dot(before, after) / (nb * na)) < math.cos(math.radians(100))


def pieces(runs: list[Run], select=None) -> list[Piece]:
    out = []
    for ri, r in enumerate(runs):
        if select is not None and not select(r):
            continue
        pts = r.pts
        th = throws(pts)
        if len(th) < MIN_THROWS:
            continue
        mids = [tuple((np.asarray(pts[i]) + np.asarray(pts[j])) / 2) for i, j in th]
        start = 0
        for k in range(1, len(th) + 1):
            brk = (k == len(th) or not _steps_ok(pts, th[k - 1], th[k])
                   or _turns_back(mids[start:k + 1], k - start))
            if not brk and k - 2 >= start and not _same_side(pts, th[k - 2], th[k]):
                # throw k does not repeat throw k-2 (one rail to the other):
                # an odd first throw (the underlay's last stitch) is dropped,
                # anywhere else the piece ends
                if k - 2 == start:
                    start += 1
                else:
                    brk = True
            if not brk:
                continue
            if k - start >= MIN_THROWS:
                out.append(_piece(ri, r, th, mids, start, k - 1))
            start = k
    return out


def _piece(ri, r: Run, th, mids, t0, t1) -> Piece:
    pts = r.pts
    ends = [(tuple(pts[i]), tuple(pts[j])) for i, j in th[t0:t1 + 1]]
    lens = [math.dist(a, b) for a, b in ends]
    angs = [math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0 for a, b in ends]
    p = Piece(ri, r.thread, t0, t1, th[t0][0], th[t1][1], r.order + th[t0][0], ends,
              list(mids[t0:t1 + 1]))
    p.width_mm = float(np.median(lens))
    p.width_max_mm = float(max(lens))
    p.cross_deg = _axial(angs, lens)
    p.cross_span_deg = float(max(abs((x - p.cross_deg + 90) % 180 - 90) for x in angs))
    # length along the midpoints taken every fourth throw (the zigzag of
    # consecutive midpoints is not length) and always the last one, so the
    # ends are kept where a smoothed centreline would pull them in
    m = list(p.mids[::4]) + ([p.mids[-1]] if (len(p.mids) - 1) % 4 else [])
    p.length_mm = float(sum(math.dist(a, b) for a, b in zip(m, m[1:])))
    p.pitch_mm = 2.0 * p.length_mm / max(1, p.n - 1)
    p.top = p.pitch_mm <= TOP_PITCH_MM
    return p


# ------------------------------------------------------------------ junctions
def relate(a: Piece, b: Piece) -> dict:
    """How piece b meets piece a: the length of b's centreline inside a's
    covered area at each of b's ends (mm; > 0 overlaps, the end inside a),
    or, when an end is outside, its distance to a (reported negative)."""
    from shapely.geometry import Point
    pa = a.polygon()
    cb = b.centreline()
    if cb is None:
        return {}
    out = {}
    coords = list(cb.coords)
    for tag, end, seq in (("start", coords[0], coords), ("end", coords[-1], coords[::-1])):
        pe = Point(end)
        if pa.contains(pe):
            run = 0.0
            for p, q in zip(seq, seq[1:]):
                if not pa.contains(Point(q)):
                    from shapely.geometry import LineString
                    run += LineString([p, q]).intersection(pa).length
                    break
                run += math.dist(p, q)
            out[tag] = round(run, 2)
        else:
            out[tag] = round(-pe.distance(pa), 2)
    inter = pa.intersection(b.polygon()).area
    out["shared_mm2"] = round(inter, 2)
    d = abs((a.cross_deg - b.cross_deg + 90) % 180 - 90)
    out["cross_diff_deg"] = round(d, 1)
    return out


def through(p: Piece, c, r: float) -> str:
    """'through' when the centreline enters and leaves the disk (both ends
    farther than r + 0.5 mm), 'ends' when an end lies inside r + 0.5 mm."""
    from shapely.geometry import Point
    cl = p.centreline()
    if cl is None:
        return "?"
    q = Point(c)
    e0, e1 = Point(cl.coords[0]).distance(q), Point(cl.coords[-1]).distance(q)
    if min(e0, e1) <= r + 0.5:
        return "ends" if max(e0, e1) > r + 0.5 else "inside"
    return "through" if cl.distance(q) <= r else "passes"


def layers(runs: list[Run], c, r: float, select=None) -> dict:
    """Thread layers in the disk (c, r): 0.4 mm lines at 20 px/mm, summed."""
    import cv2
    size = int(math.ceil(2 * (r + 1) * PPM))
    ox, oy = c[0] - (r + 1), c[1] - (r + 1)
    acc = np.zeros((size, size), np.uint16)
    tmp = np.zeros((size, size), np.uint8)
    w = max(1, int(round(LINE_MM * PPM)))
    lo = np.array([ox, oy]) - 5
    hi = np.array([ox, oy]) + size / PPM + 5
    for run in runs:
        if select is not None and not select(run):
            continue
        P = np.asarray(run.pts)
        if not ((P >= lo) & (P <= hi)).all(1).any():
            continue
        for p, q in zip(P, P[1:]):
            if not (((p >= lo) & (p <= hi)).all() or ((q >= lo) & (q <= hi)).all()):
                continue
            tmp[:] = 0
            a = (int(round((p[0] - ox) * PPM)), int(round((p[1] - oy) * PPM)))
            b = (int(round((q[0] - ox) * PPM)), int(round((q[1] - oy) * PPM)))
            cv2.line(tmp, a, b, 1, w)
            acc += tmp
    yy, xx = np.mgrid[0:size, 0:size]
    disk = (np.hypot(xx / PPM + ox - c[0], yy / PPM + oy - c[1]) <= r)
    v = acc[disk]
    cov = v[v > 0]
    if not len(cov):
        return {"mean": 0.0, "max": 0, "deep3": 0.0, "covered_mm2": 0.0}
    return {"mean": round(float(cov.mean()), 2), "max": int(cov.max()),
            "deep3": round(float((cov >= 3).mean()), 2),
            "covered_mm2": round(len(cov) / PPM ** 2, 2)}


def junction(runs: list[Run], ps: list[Piece], at_mm, r: float, tl, select=None,
             top_only=True) -> dict:
    """Every piece reaching the disk at `at_mm` (mm from the top-left `tl`),
    in sew order, how each pair meets, and the thread layers there."""
    from shapely.geometry import Point
    c = (at_mm[0] + tl[0], at_mm[1] + tl[1])
    disk = Point(c).buffer(r)
    here = [p for p in ps if (p.top or not top_only) and p.polygon().intersects(disk)]
    here.sort(key=lambda p: p.order)
    rows = []
    for k, p in enumerate(here):
        row = p.row(tl)
        row["id"] = k
        row["at_junction"] = through(p, c, r)
        row["in_disk_mm2"] = round(p.polygon().intersection(disk).area, 2)
        rows.append(row)
    pairs = []
    for i, a in enumerate(here):
        for j, b in enumerate(here):
            if i == j:
                continue
            rel = relate(a, b)
            if rel.get("shared_mm2", 0) <= 0.05 and max(rel.get("start", -9), rel.get("end", -9)) < -0.5:
                continue
            pairs.append({"a": i, "b": j, **rel})
    return {"at": list(at_mm), "r": r, "pieces": rows, "pairs": pairs,
            "layers": layers(runs, c, r, select)}


# ------------------------------------------------------------------ validation
def machine_runs(plan) -> tuple[list[Run], list[list[int]]]:
    """Our plan as a machine file reads it: consecutive plan runs joined
    until the needle lifts (a jump or trim) or the thread changes, so run
    boundaries are gone the way they are in a professional's file.
    -> (runs, per-point plan-run index): the second is the ground truth
    `validate` reads."""
    out, labels, n = [], [], 0
    cur, lab, thread, rgb, start = [], [], None, None, 0
    pi = -1
    for b in plan.blocks:
        for r in b.runs:
            pi += 1
            pts = [tuple(map(float, p)) for p in (r.points or [])]
            if not pts:
                continue
            if (r.jump or r.trim or str(b.thread_number) != thread) and cur:
                if len(cur) >= 2:
                    out.append(Run(cur, thread, rgb, "", start))
                    labels.append(lab)
                cur, lab = [], []
            if not cur:
                start = n
            thread, rgb = str(b.thread_number), tuple(b.rgb)
            cur += pts
            lab += [pi] * len(pts)
            n += len(pts)
    if len(cur) >= 2:
        out.append(Run(cur, thread, rgb, "", start))
        labels.append(lab)
    return out, labels


def plan_kinds(plan) -> list[str]:
    return [str(r.kind) for b in plan.blocks for r in b.runs]


def validate(runs: list[Run], labels: list[list[int]], kinds: list[str], ps: list[Piece],
             select=None, min_stitches: int = 20) -> dict:
    """Read the pieces against the plan's own satin runs (each a loop or bar
    the ladder sewed whole) after the run boundaries were dropped
    (`machine_runs`). A stitch belongs to a plan run when both its points do.
    Per plan satin run of `min_stitches` or more: COVERAGE, the share of its
    stitches inside a top piece; the pieces touching it and the lowest
    PURITY among them, the share of a piece's stitches from this run. A bar
    is READ when coverage >= 0.85 and every piece touching it has purity
    >= 0.95 (nothing merged across two bars or into a travel). A loop round
    a corner is several pieces by design; `pieces` counts them.
    `false_pieces`: top pieces at least half made of non-satin stitches."""
    piece_at: dict = {}
    for k, p in enumerate(ps):
        if p.top:
            for i in range(p.i0, p.i1):
                piece_at[(p.run, i)] = k
    piece_size = {k: p.i1 - p.i0 for k, p in enumerate(ps)}
    stitches_of: dict = {}
    piece_from: dict = {}
    for ri, r in enumerate(runs):
        if select is not None and not select(r):
            continue
        lab = labels[ri]
        for i in range(len(r.pts) - 1):
            g = lab[i] if lab[i] == lab[i + 1] else None
            k = piece_at.get((ri, i))
            if g is not None:
                stitches_of.setdefault(g, []).append(k)
            if k is not None:
                piece_from.setdefault(k, {}).setdefault(g, 0)
                piece_from[k][g] += 1
    rows = []
    for g, ks in sorted(stitches_of.items()):
        if kinds[g] != "satin" or len(ks) < min_stitches:
            continue
        hit = [k for k in ks if k is not None]
        touching = sorted(set(hit))
        pur = [piece_from[k].get(g, 0) / max(1, piece_size[k]) for k in touching]
        cov = len(hit) / len(ks)
        rows.append({"plan_run": g, "stitches": len(ks), "coverage": round(cov, 2),
                     "pieces": len(touching), "purity_min": round(min(pur), 2) if pur else None,
                     "read": cov >= 0.85 and bool(pur) and min(pur) >= 0.95})
    false = [k for k, src in piece_from.items()
             if sum(v for g, v in src.items() if g is not None and kinds[g] == "satin")
             < 0.5 * piece_size[k]]
    return {"bars": len(rows), "read": sum(r["read"] for r in rows),
            "false_pieces": len(false), "pieces_total": sum(1 for p in ps if p.top),
            "rows": rows}


def digitize_ours(slug: str, width_mm: float, extra: dict | None = None):
    """Our plan for `slug`'s art (pro_baseline.JOBS) at `width_mm`."""
    from tools import pro_pair
    from tools.pro_baseline import JOBS
    garment, _w, art, *_ = JOBS[slug]
    return pro_pair.digitize(_resolve(art), width_mm, garment, extra).plan


def _resolve(spec: str) -> Path:
    kind, _sep, rel = spec.partition(":")
    root = Path(__file__).resolve().parent.parent
    if kind == "testdata":
        return root / "testdata" / rel
    if kind == "kent":
        from tools import word_legibility as wl
        k = wl.kent_root()
        if k is None:
            raise SystemExit("no scratch_kent/: run tools.tripwire materialise first")
        return k / rel
    return Path(rel)


# ------------------------------------------------------------------ cli
def _load(args):
    """-> (runs, validation inputs or None)."""
    if args.pro:
        from tools import tripwire
        from tools.pro_baseline import JOBS
        tripwire.materialise(Path(args.scratch), [args.pro])
        spec = JOBS[args.pro][4] or JOBS[args.pro][3]
        return pro_runs(_resolve(spec)), None
    if args.file:
        return pro_runs(args.file), None
    extra = json.loads(args.extra) if args.extra else None
    plan = digitize_ours(args.ours, args.width, extra)
    runs, labels = machine_runs(plan)
    return runs, (labels, plan_kinds(plan))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pro", help="pro_baseline.JOBS slug: the professional's file (PES, else DST)")
    src.add_argument("--ours", help="pro_baseline.JOBS slug: our digitize of its art")
    src.add_argument("--file", help="any machine file")
    ap.add_argument("--width", type=float, help="--ours: width mm (default the job's)")
    ap.add_argument("--extra", help="--ours: cfg.extra JSON")
    ap.add_argument("--at", action="append", default=[], help="x,y[,r] mm from the extents' top-left")
    ap.add_argument("--r", type=float, default=2.5)
    ap.add_argument("--all-threads", action="store_true", help="every colour, not white only")
    ap.add_argument("--validate", action="store_true", help="--ours: compare with the ladder's bars")
    ap.add_argument("--list", action="store_true", help="print every piece")
    ap.add_argument("--json", help="write the report here")
    ap.add_argument("--scratch", default="scratch_kent_census",
                    help="--pro: where the zip member is extracted (gitignored scratch)")
    args = ap.parse_args(argv)
    if args.ours and args.width is None:
        from tools.pro_baseline import JOBS
        args.width = JOBS[args.ours][1]
    runs, bars = _load(args)
    sel = None if args.all_threads else (lambda r: is_white(r.rgb))
    tl = extents_top_left(runs)
    ps = pieces(runs, sel)
    rep: dict = {"source": args.pro or args.ours or args.file, "top_left": [round(v, 2) for v in tl],
                 "pieces": len(ps), "top_pieces": sum(p.top for p in ps)}
    if args.list:
        rep["all"] = [p.row(tl) for p in ps]
    if args.validate:
        if bars is None:
            raise SystemExit("--validate needs --ours")
        rep["validate"] = validate(runs, bars[0], bars[1], ps, sel)
    rep["junctions"] = []
    for spec in args.at:
        v = [float(t) for t in spec.split(",")]
        r = v[2] if len(v) > 2 else args.r
        rep["junctions"].append(junction(runs, ps, v[:2], r, tl, sel))
    text = json.dumps(rep, indent=1)
    if args.json:
        Path(args.json).write_text(text)
    print(_summary(rep))
    return 0


def _summary(rep: dict) -> str:
    out = [f"{rep['source']}: {rep['pieces']} pieces ({rep['top_pieces']} top satin), top-left {rep['top_left']}"]
    v = rep.get("validate")
    if v:
        out.append(f"validate: {v['read']} of {v['bars']} satin bars read; "
                   f"{v['false_pieces']} of {v['pieces_total']} top pieces not satin")
        for r in v["rows"]:
            if not r["read"]:
                out.append(f"  unread: {r}")
    for j in rep.get("junctions", []):
        L = j["layers"]
        out.append(f"\n@ {j['at']} r {j['r']}: layers mean {L['mean']} max {L['max']} "
                   f"3+ {L['deep3']} covered {L['covered_mm2']} mm2")
        for p in j["pieces"]:
            out.append(f"  [{p['id']}] order {p['order']} run {p['run']} {p['throws']} throws "
                       f"cross {p['cross_deg']} (+-{p['cross_span_deg']}) len {p['length_mm']} "
                       f"w {p['width_mm']} (max {p['width_max_mm']}) pitch {p['pitch_mm']} "
                       f"{p['from']}->{p['to']} {p['at_junction']} disk {p['in_disk_mm2']} mm2")
        for q in j["pairs"]:
            out.append(f"   b{q['b']} on a{q['a']}: start {q.get('start')} end {q.get('end')} "
                       f"shared {q.get('shared_mm2')} mm2 dangle {q.get('cross_diff_deg')}")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
