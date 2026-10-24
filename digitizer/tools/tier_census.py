#!/usr/bin/env python
"""tier_census: which stitch TYPE the pro gives each shape, and which we do.

L9 (2026-10-24). The cross-underlay lane found MFab hat's black silhouette
sewn as split satin by us and filled by the pro. Whether that is one shape
or a rule is a tier question -- fill / satin / split satin / run per shape --
and this asks it of every shape on every paired job (lettering flagged).

One reader, both files. Ours is written to DST and read back
(`border_census.digitize_one`), so the pro's file and ours go through the
same code; shapes are OUR segmentation's, mapped into the pro's frame by
`pairframe.register_pair`. Per shape, the needle-down stitches whose
midpoint lies inside it are read in sew order:

  cross   a maximal chain of consecutive stitches on one line, one sense: a
          satin cross (whole, or split into pieces) or a fill row.
  dense   a cross whose sequence neighbour comes back anti-parallel within
          DENSE_GAP_MM: top stitching, not underlay or travel.
  peak    share of the dense crosses' length lying at ONE angle (+/- 4 deg).
          A fill sews one angle across its object; satin follows its column
          and turns with it. The one place the two look alike is a straight
          bar whose one angle runs square across it -- called BAR, not
          guessed.

  oblique share of the dense crosses at the peak angle that meet the edge
          less square than SQUARE_DEG at their ends. A satin cross lands
          square on its rails; a fill row lands at the fill angle. A fill
          under a satin border (MFab's silhouette) shares the region with the
          border's crosses, so its peak drops and this keeps it.

  tier = RUN    covered share under DENSE_MIN, or too few dense crosses
         FILL   peak >= PEAK_FILL, or peak >= PEAK_UNDER with oblique >=
                OBLIQUE_UNDER (a fill under a border); not a bar
         BAR    peak >= PEAK_FILL on a bar, square across it
         SATIN  peak below; under SPLIT_SEGS stitches per cross
         SPLIT  peak below; split crosses

Ours is ALSO read off the plan (`ours.json` kinds: satin / fill / run), so
the reader's error on our side -- where the truth is known -- is printed
beside the census: a reader that misreads ours is not trusted on his.

  python tools/tier_census.py run [--only SLUG ...] [--jobs 3]   # digitize, then table
  python tools/tier_census.py table [--json OUT]                   # re-read the cache
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
for p in (str(DIGITIZER), str(DIGITIZER / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools import border_census as bc                               # noqa: E402

# Jobs with art beyond the border census's sixteen (pro-rules 2026-10-21).
EXTRA_PAIRS = [
    ("toat_machine_hat", "To a T Machine/Machine HAT.DST", "To a T Machine/Machine.png", "hat_front"),
    ("toat_machine_lc", "To a T Machine/Machine LC.DST", "To a T Machine/Machine.png", "left_chest"),
    ("toat_machine_beanie", "To a T Machine/Machine beanie E (1).DST", "To a T Machine/Machine.png", "beanie"),
    ("toat_beanie", "To a T_Becker Beanies/To a T Beanie.DST", "To a T_Becker Beanies/To a T.png", "beanie"),
    ("goldentee_hat", "Golden Tee/GOLF HAT.DST", "Golden Tee/Golden Tee Logo.jpg", "hat_front"),
]
EXTRA_FALLBACK = {
    "toat_machine": bc._T / "art" / "logo_toat_machine.png",
    "toat_beanie": bc._T / "art" / "logo_toat_beanie.png",
    "goldentee": bc._T / "photo" / "logo_golden_tee.jpg",
}
bc.PAIRS = bc.PAIRS + [p for p in EXTRA_PAIRS if p[0] not in {r[0] for r in bc.PAIRS}]
bc.ART_FALLBACK.update(EXTRA_FALLBACK)

MIN_AREA_MM2 = 4.0      # a tier on a speck is noise
SEG_MIN_MM = 0.5        # shorter stitches are locks, travel nubs, split remainders
TURN_DEG = 12.0         # a stitch this far off the last one's line starts a new cross
CROSS_MIN_MM = 1.0      # a cross (row) shorter than this says nothing about direction
DENSE_GAP_MM = 0.9      # the next cross back within this of the last one: top stitching
PEAK_HALF_DEG = 4.0     # one angle, +/- this
PEAK_FILL = 0.70        # share at one angle that reads as a fill: the pro's fills read
                        # 0.73-0.93 on Becker, his whole-satin straight stems 0.56-0.61
PEAK_UNDER = 0.50       # a fill under a satin border shares the region with the
OBLIQUE_UNDER = 0.35    # border's crosses: half at one angle, a third landing oblique
                        # (MFab's band 0.59 / 0.40; satin reads <= 0.15 oblique)
BAR_ASPECT = 3.0        # a shape this long for its width ...
BAR_SQUARE_DEG = 25.0   # ... whose one angle is this close to square across it
SPLIT_SEGS = 1.3        # stitches per satin cross from which a column is split
DENSE_MIN = 0.45        # covered share of the shape below which it is a run (or nothing)
THREAD_MM = 0.4
RES = 10.0


def _segments(runs):
    """-> array [x0, y0, x1, y1, run, k]: every needle-down stitch, in sew order."""
    import numpy as np
    out = []
    for ri, r in enumerate(runs):
        pts = r["pts"]
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            out.append((a[0], a[1], b[0], b[1], ri, k))
    return np.asarray(out, float) if out else np.zeros((0, 6))


class Index:
    """Stitch segments bucketed on a 2 mm grid for per-shape lookups."""

    def __init__(self, segs, cell=2.0):
        import numpy as np
        self.cell = cell
        self.segs = segs
        mid = (segs[:, :2] + segs[:, 2:4]) / 2
        g = np.floor(mid / cell).astype(int)
        self.grid: dict[tuple[int, int], list[int]] = {}
        for i, (gx, gy) in enumerate(g):
            self.grid.setdefault((int(gx), int(gy)), []).append(i)

    def near(self, bounds):
        import numpy as np
        x0, y0, x1, y1 = bounds
        c = self.cell
        out = []
        for gx in range(int(x0 // c) - 1, int(x1 // c) + 2):
            for gy in range(int(y0 // c) - 1, int(y1 // c) + 2):
                out.extend(self.grid.get((gx, gy), ()))
        return self.segs[np.sort(np.asarray(out, int))] if out else self.segs[:0]


def _cover(poly, segs) -> float:
    """Share of `poly` within half a thread of any of `segs` (0.1 mm raster)."""
    import cv2
    import numpy as np
    b = poly.bounds
    w = int((b[2] - b[0]) * RES) + 3
    h = int((b[3] - b[1]) * RES) + 3
    if w * h > 9_000_000 or w <= 2 or h <= 2:
        return 0.0

    def px(x, y):
        return int(round((x - b[0]) * RES)) + 1, int(round((y - b[1]) * RES)) + 1

    inside = np.zeros((h, w), np.uint8)
    for part in getattr(poly, "geoms", [poly]):      # a MultiPolygon: every piece
        cv2.fillPoly(inside, [np.array([px(x, y) for x, y in part.exterior.coords], np.int32)], 1)
        for hole in part.interiors:
            cv2.fillPoly(inside, [np.array([px(x, y) for x, y in hole.coords], np.int32)], 0)
    thr = np.zeros((h, w), np.uint8)
    t = max(1, int(round(THREAD_MM * RES)))
    for x0, y0, x1, y1 in segs[:, :4]:
        cv2.line(thr, px(x0, y0), px(x1, y1), 1, t)
    ins = inside > 0
    return float((thr[ins] > 0).mean()) if ins.any() else 0.0


def _crosses(a):
    """Inside stitches (sew order) -> crosses: maximal chains of consecutive
    stitches on one line in one sense. -> [(x0, y0, x1, y1, nseg, run)]."""
    out = []
    cur = None
    for x0, y0, x1, y1, ri, k in a:
        if math.hypot(x1 - x0, y1 - y0) < SEG_MIN_MM:
            if cur is not None:
                out.append(cur)
            cur = None
            continue
        d = math.atan2(y1 - y0, x1 - x0)
        if (cur is not None and cur[5] == ri and cur[6] == k - 1
                and abs((d - cur[7] + math.pi) % (2 * math.pi) - math.pi) <= math.radians(TURN_DEG)):
            cur = [cur[0], cur[1], x1, y1, cur[4] + 1, ri, k, cur[7]]
        else:
            if cur is not None:
                out.append(cur)
            cur = [x0, y0, x1, y1, 1, ri, k, d]
    if cur is not None:
        out.append(cur)
    return [c[:6] for c in out]


def _dense(cr):
    """Crosses whose sequence neighbour comes back anti-parallel within
    DENSE_GAP_MM of it: satin crosses and fill rows, not underlay or travel."""
    keep = [False] * len(cr)
    for i in range(len(cr) - 1):
        a, b = cr[i], cr[i + 1]
        if a[5] != b[5]:
            continue
        ax, ay = a[2] - a[0], a[3] - a[1]
        bx, by = b[2] - b[0], b[3] - b[1]
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        if la < CROSS_MIN_MM or lb < CROSS_MIN_MM:
            continue
        if (ax * bx + ay * by) / (la * lb) > -math.cos(math.radians(15.0)):
            continue
        mx, my = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if abs((mx - a[0]) * ay - (my - a[1]) * ax) / la <= DENSE_GAP_MM:
            keep[i] = keep[i + 1] = True
    return [c for c, k in zip(cr, keep) if k]


def _peak(cr):
    """-> (share of length at the best single angle +/- PEAK_HALF_DEG, that angle, deg)."""
    import numpy as np
    if not cr:
        return 0.0, None
    c = np.asarray([x[:4] for x in cr])
    th = np.degrees(np.arctan2(c[:, 3] - c[:, 1], c[:, 2] - c[:, 0])) % 180.0
    w = np.hypot(c[:, 2] - c[:, 0], c[:, 3] - c[:, 1])
    best, at = 0.0, None
    for t in np.arange(0, 180, 1.0):
        s = float(w[np.abs((th - t + 90) % 180 - 90) <= PEAK_HALF_DEG].sum())
        if s > best:
            best, at = s, float(t)
    return best / float(w.sum()), at


def _edge_samples(poly, step=0.1):
    """Boundary points every `step` mm with the edge direction there (rad, mod pi)."""
    import numpy as np
    pts, angs = [], []
    for ring in [poly.exterior, *poly.interiors]:
        c = np.asarray(ring.coords)
        for p, q in zip(c[:-1], c[1:]):
            L = float(np.hypot(*(q - p)))
            if L <= 1e-9:
                continue
            n = max(1, int(L / step))
            pts.append(p + (np.arange(n)[:, None] / n) * (q - p))
            angs.append(np.full(n, math.atan2(q[1] - p[1], q[0] - p[0]) % math.pi))
    return np.vstack(pts), np.concatenate(angs)


SQUARE_DEG = 55.0       # a cross meeting the edge at least this square lands like satin


def _incidence(cr, poly, peak_deg):
    """How the crosses MEET the shape's edge, at both ends: a satin cross lands
    square on its rails (lean caps keep it within ~35 deg of square); a fill
    row lands at whatever its one angle makes with the edge there.
    -> (share of length landing square, share at the peak angle landing oblique)."""
    import numpy as np
    from scipy.spatial import cKDTree
    bp, ba = _edge_samples(poly)
    tree = cKDTree(bp)
    c = np.asarray([x[:4] for x in cr])
    th = np.arctan2(c[:, 3] - c[:, 1], c[:, 2] - c[:, 0]) % math.pi
    w = np.hypot(c[:, 2] - c[:, 0], c[:, 3] - c[:, 1])
    inc = np.zeros(len(c))
    for cols in ((0, 1), (2, 3)):
        _d, j = tree.query(c[:, cols])
        inc += np.abs(((th - ba[j]) + math.pi / 2) % math.pi - math.pi / 2)
    sq = np.degrees(inc / 2) >= SQUARE_DEG
    on = np.abs((np.degrees(th) - (peak_deg or 0.0) + 90) % 180 - 90) <= PEAK_HALF_DEG
    tot = float(w.sum())
    return round(float(w[sq].sum()) / tot, 2), round(float(w[on & ~sq].sum()) / tot, 2)


def _long_axis(poly):
    """-> (direction of the minimum rotated rectangle's long side, deg; its aspect)."""
    import numpy as np
    c = np.asarray(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    e = [c[1] - c[0], c[2] - c[1]]
    ls = [float(np.hypot(*v)) for v in e]
    v = e[int(np.argmax(ls))]
    return math.degrees(math.atan2(v[1], v[0])) % 180.0, max(ls) / max(min(ls), 1e-6)


def read_tier(poly, index: Index) -> dict:
    """One shape against one file's stitches -> tier and the readings."""
    import shapely
    if not poly.is_valid:
        poly = poly.buffer(0)
    a = index.near(poly.bounds)
    if len(a):
        mid = (a[:, :2] + a[:, 2:4]) / 2
        a = a[shapely.contains_xy(poly, mid[:, 0], mid[:, 1])]
    cov = _cover(poly, a)
    dn = _dense(_crosses(a))
    peak, ang = _peak(dn)
    res = {"cover": round(cov, 2), "crosses": len(dn), "peak": round(peak, 2),
           "angle": ang, "spc": None, "square": None, "oblique_peak": None}
    if dn:
        res["square"], res["oblique_peak"] = _incidence(dn, poly, ang)
    if cov < DENSE_MIN or len(dn) < 6:
        res["tier"] = "RUN" if len(a) else "NONE"
        return res
    spc = sum(c[4] for c in dn) / len(dn)
    res["spc"] = round(spc, 2)
    if peak >= PEAK_FILL or (peak >= PEAK_UNDER and res["oblique_peak"] >= OBLIQUE_UNDER):
        long_deg, aspect = _long_axis(poly)
        across = abs((ang - long_deg) % 180 - 90)
        res["tier"] = "BAR" if aspect >= BAR_ASPECT and across <= BAR_SQUARE_DEG else "FILL"
    else:
        res["tier"] = "SPLIT" if spc >= SPLIT_SEGS else "SATIN"
    return res


def geometry(poly) -> dict:
    """Width (inscribed diameter, and median stroke = 2 x distance along the
    medial axis), area, length (skeleton) and aspect of one shape."""
    import cv2
    import numpy as np
    from skimage.morphology import skeletonize
    b = poly.bounds
    r = 10.0
    w = int((b[2] - b[0]) * r) + 3
    h = int((b[3] - b[1]) * r) + 3
    m = np.zeros((h, w), np.uint8)

    def px(x, y):
        return int(round((x - b[0]) * r)) + 1, int(round((y - b[1]) * r)) + 1

    cv2.fillPoly(m, [np.array([px(x, y) for x, y in poly.exterior.coords], np.int32)], 1)
    for hole in poly.interiors:
        cv2.fillPoly(m, [np.array([px(x, y) for x, y in hole.coords], np.int32)], 0)
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5) / r
    sk = skeletonize(m > 0)
    vals = dist[sk]
    stroke = float(2 * np.median(vals)) if vals.size else float(2 * dist.max())
    length = float(sk.sum()) / r
    from digitizer_core.stage6_satin import ribbon_width_mm
    return {"area": round(poly.area, 1), "inscribed": round(float(2 * dist.max()), 2),
            "ribbon_w": round(float(ribbon_width_mm(poly)), 2),
            "stroke": round(stroke, 2), "length": round(length, 1),
            "aspect": round(length / stroke, 1) if stroke > 0 else None,
            "holes": len(poly.interiors)}


def plan_tier(kinds: dict) -> str:
    """Ours, read off the plan: the kind carrying most of the shape's thread."""
    tally: dict[str, int] = {}
    for k, n in (kinds or {}).items():
        base = k.split(":")[0]
        if base in ("travel", "tie", "underlay", "jump"):
            continue
        base = {"bean": "run", "border": "satin"}.get(base, base)
        tally[base] = tally.get(base, 0) + n
    if not tally:
        return "NONE"
    return max(tally, key=tally.get).upper()


LETTER_KEYS = ("text_cluster_id", "lettering_group", "bean_letter", "small_text_stray")


def analyse(slug: str, cache: Path) -> dict:
    from shapely import wkt
    from shapely.affinity import affine_transform
    from tools.pro_parity.pairframe import register_pair
    from tools.study_pro import load_runs

    out = cache / slug
    info = json.loads((out / "ours.json").read_text(encoding="utf-8"))
    pro = Path(info["pro"])
    if not pro.exists():        # a Drive path that went away: find it again
        row = next(r for r in bc.PAIRS if r[0] == slug)
        pro = Path(bc.find_pair(*row[:3])[0] or pro)
    if pro.suffix.lower() == ".pes":
        for q in pro.parent.iterdir():
            if q.stem.lower() == pro.stem.lower() and q.suffix.lower() == ".dst":
                pro = q
    ours_runs, _t, _j = load_runs(out / "ours.dst")
    pro_runs, _t, _j = load_runs(pro)
    reg = register_pair(pro, out / "ours.dst")
    i_ours = Index(_segments(ours_runs))
    i_pro = Index(_segments(pro_runs))
    rows = []
    for r in info["regions"]:
        po = wkt.loads(r["wkt"])
        if not po.is_valid:
            po = po.buffer(0)
        if po.is_empty or po.area < MIN_AREA_MM2 or po.geom_type != "Polygon":
            continue
        pp = affine_transform(po, reg.matrix())
        meta = r.get("meta") or {}
        rows.append({
            "slug": slug, "id": r["id"], "lettering": any(k in meta for k in LETTER_KEYS),
            "geom": geometry(po), "plan": plan_tier(r["kinds"]),
            "ours": read_tier(po, i_ours), "pro": read_tier(pp, i_pro),
        })
    return {"slug": slug, "pro_file": pro.name, "reg": reg.as_dict(), "garment": info["garment"],
            "width_mm": info["width_mm"], "rows": rows}


def kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa of two label lists."""
    n = len(a)
    if not n:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in set(a) | set(b))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def table_cmd(args) -> int:
    cache = Path(args.cache)
    res = []
    for slug, *_ in bc.PAIRS:
        if args.only and slug not in args.only:
            continue
        if not (cache / slug / "ours.json").exists():
            print("no cache for", slug)
            continue
        try:
            r = analyse(slug, cache)
        except OSError as e:     # the Drive drops files mid-run; say so, keep going
            print(f"{slug}: SKIPPED ({e})", flush=True)
            continue
        res.append(r)
        print(f"{slug}: {len(r['rows'])} shapes, reg {r['reg']}", flush=True)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print_table(res)
    return 0


def print_table(res) -> None:
    print("\n| job | id | let | area | inscr | stroke | len | aspect | plan | ours read | pro read | pro peak/spc |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res:
        for row in sorted(r["rows"], key=lambda x: -x["geom"]["area"]):
            g, o, p = row["geom"], row["ours"], row["pro"]
            print(f"| {r['slug']} | {row['id']} | {'L' if row['lettering'] else ''} | {g['area']} | "
                  f"{g['inscribed']} | {g['stroke']} | {g['length']} | {g['aspect']} | {row['plan']} | "
                  f"{o['tier']} {o['peak']}/{o['spc']}/{o['square']}/{o['oblique_peak']} | "
                  f"{p['tier']} | {p['peak']}/{p['spc']}/{p['square']}/{p['oblique_peak']} |")


def one_cmd(args) -> int:
    bc.digitize_one(args.slug, Path(args.cache))
    return 0


def run_cmd(args) -> int:
    cache = Path(args.cache)
    slugs = [r[0] for r in bc.PAIRS if not args.only or r[0] in args.only]
    todo = [s for s in slugs if not (cache / s / "ours.json").exists() or args.redo]
    from concurrent.futures import ThreadPoolExecutor

    def go(s):
        print("digitizing", s, flush=True)
        return subprocess.run([sys.executable, str(Path(__file__)), "one", s, "--cache", str(cache)]).returncode

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        codes = list(ex.map(go, todo))
    if any(codes):
        print("digitize failures:", [s for s, c in zip(todo, codes) if c])
    return table_cmd(args)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", run_cmd), ("table", table_cmd), ("one", one_cmd)):
        p = sub.add_parser(name)
        p.add_argument("--cache", default=str(DIGITIZER / "debug_out" / "tier_census"))
        p.add_argument("--only", nargs="*")
        p.add_argument("--jobs", type=int, default=3)
        p.add_argument("--redo", action="store_true")
        p.add_argument("--json", default=None)
        if name == "one":
            p.add_argument("slug")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
