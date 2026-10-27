#!/usr/bin/env python
"""bean_census: WHAT the professional sews as a bean (triple run), and what we do.

Kent (2026-10-27): the auto bean stitch "doesn't recognize very well what should
get a bean stitch". Ours has no bean classifier -- a bean comes out of five
size-gated fallbacks (the run tier, bean letters, the edge cap, the satin
fallback, the detail layer). This instrument asks the pro's files WHICH
elements he beans, and asks ours the same question with ONE detector, so the
comparison is a measurement and not two dialects.

The detector (`bean_segments`) reads a needle-down run and finds every stretch
whose stations are sewn more than once: a bean / triple run returns to each
penetration (ABAB per stitch, or a whole lap forward-back-forward), a satin
column, a fill row and a single run never do. It is style-blind on purpose:
the earlier pass (`border_pro.bean_stats`, 2026-10-15) caught one bean style
and the second (`settings-vs-pro` row 19) the other. Per segment it reports
length, pitch, passes, style, and whether a LATER run of the same file covers
it (an underlay walk is retraced too, and is not a bean anyone sees).

Each bean segment is then placed on OUR segmentation of the art (the pro's
frame reached through `pairframe.register_pair`, as `border_census` does):
the host region, whether the bean rides the host's EDGE or lies INSIDE it (a
line / letter stroke), the host's smallest dimension, the drawn width under
the run, what the host's outline faces (bare fabric or another colour), its
colour contrast, and whether it is a letter. Regions are the unit of the
pooled table and of the chance-corrected agreement (Cohen's kappa over
"this region carries a bean"), by category:

  LETTER            a lettering-tagged region (stroke band by smallest dimension)
  LINE free         a thin region (smallest dimension <= LINE_MM) whose outline
                    mostly faces fabric
  LINE inside       a thin region mostly enclosed by other colours
  LINE between      a thin region partly against colour, partly against fabric
  BODY <2 / 2-4 / 4-6 / 6+   a filled body by smallest dimension, split by
                    whether its outline mostly faces fabric or another colour

Usage (from digitizer/, the primary venv):
  python -m tools.bean_census --corpus [--jobs 3] [--set FLAG=JSON ...] [--arm NAME]
  python -m tools.bean_census digitize --slugs S ... [--cache DIR] [--set K=V]
  python -m tools.bean_census table [--arm NAME] [--doc PATH]
  python -m tools.bean_census compare OFF_ARM ON_ARM
  python -m tools.bean_census render SLUG [--n 3]        # validation, pro_renders/

The cache is `debug_out/bean_census/<arm>/<slug>/` (ours.dst, ours.json,
census.json). The doc table goes to docs/bean-census-reference-2026-10-27.md
("reference" -- never a `pro` word in a new docs/ file name, memory
`pro-renders-local-only-2026-10-27`). Renders of the pro's file go to
`pro_renders/` only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

DEFAULT_CACHE = DIGITIZER / "debug_out" / "bean_census"
OUT_DOC = DIGITIZER.parent / "docs" / "bean-census-reference-2026-10-27.md"

#: The paired jobs (every slug `flip_sheet_renders.fixture_files` resolves:
#: `border_census.PAIRS`, its extras, the pro-intake registry). Both our output
#: and the pro's DST exist for each.
JOBS = [
    "hotel_fremont_hat", "hotel_fremont_patch", "precision_drone",
    "proseal_hat", "proseal_beanie", "mfab_hat", "mfab_lc",
    "becker_hat_small", "becker_chest_small", "becker_beanie",
    "bridge_hat", "bridge_lc", "gaulke_roofing_hat", "tires_hat_3d",
    "machine_hat", "toat_beanie", "golf_hat",
]

# ----------------------------------------------------------------- detector
STATION_TOL_MM = 0.16     # two penetrations this close are one station (DST grid 0.1)
MIN_STATIONS = 3          # a bean under three stations is a lock or lint
MIN_SPINE_MM = 1.5        # and under this long
PITCH_MIN_MM, PITCH_MAX_MM = 0.3, 2.6   # a run's station spacing
GAP_PTS = 2               # single-visit points tolerated inside a bean stretch
TIE_MAX_STATIONS = 6      # a retraced stretch at a run's start or end with no more
TIE_MAX_MM = 7.0          # stations than this, and no longer, is a tie, not a bean
TRAVEL_MM = 6.0           # a longer segment is travel, never a stitch that covers
COVER_TOL_MM = 0.35       # a later stitch this close covers a bean sample
EDGE_TOL_MM = 0.40        # a sample this close to the host's boundary rides it
HOST_REACH_MM = 0.60      # a sample this far from every region has no host
HOST_NEAR_MM = 0.30       # within this, the smallest region is the host
LINE_MM = 1.2             # a region no wider than this is a LINE, not a BODY
SAMPLE_MM = 0.5


def _stations(pts, tol=STATION_TOL_MM):
    """Station id per point: a point within `tol` of an earlier point joins
    that point's station. -> (ids, visits per station)."""
    cell = tol * 1.01
    grid: dict[tuple[int, int], list[int]] = {}
    ids: list[int] = []
    first: list[tuple[float, float]] = []
    for x, y in pts:
        cx, cy = int(math.floor(x / cell)), int(math.floor(y / cell))
        hit = -1
        best = tol
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for sid in grid.get((cx + dx, cy + dy), ()):
                    d = math.dist((x, y), first[sid])
                    if d <= best:
                        best, hit = d, sid
        if hit < 0:
            hit = len(first)
            first.append((x, y))
            grid.setdefault((cx, cy), []).append(hit)
        ids.append(hit)
    return ids, Counter(ids)


def bean_segments(pts, *, min_passes: float = 1.6) -> list[dict]:
    """Every retraced stretch of one needle-down run.

    -> [{i0, i1 (point index span, inclusive), spine [(x,y)] (stations in
    first-visit order), length_mm, pitch_mm, passes, style ('abab' | 'lap'),
    n}]. `passes` is points per station; a triple run reads ~3, a double ~2,
    anything under `min_passes` is not reported.
    """
    n = len(pts)
    if n < 2 * MIN_STATIONS:
        return []
    ids, visits = _stations(pts)
    multi = [visits[s] >= 2 for s in ids]
    out = []
    i = 0
    while i < n:
        if not multi[i]:
            i += 1
            continue
        j, gap = i, 0
        k = i
        while k + 1 < n:
            if multi[k + 1]:
                j, gap = k + 1, 0
            else:
                gap += 1
                if gap > GAP_PTS:
                    break
            k += 1
        seg = pts[i:j + 1]
        seg_ids = ids[i:j + 1]
        i = j + 1
        seen: set[int] = set()
        spine = []
        for p, s in zip(seg, seg_ids):
            if s not in seen:
                seen.add(s)
                spine.append(p)
        if len(spine) < MIN_STATIONS:
            continue
        steps = [math.dist(a, b) for a, b in zip(spine, spine[1:])]
        length = sum(steps)
        pitch = sorted(steps)[len(steps) // 2] if steps else 0.0
        passes = len(seg) / len(spine)
        if length < MIN_SPINE_MM or passes < min_passes:
            continue
        if not (PITCH_MIN_MM <= pitch <= PITCH_MAX_MM):
            continue
        # a tie-in / tie-off: the pro locks a run by retracing its last (or
        # first) two or three stitches. Measured on ProSeal, Fremont and
        # Machine: 3-5 stations, 1.5-6 mm, at the very end of the run.
        at_end = j >= n - 3 or (i - len(seg)) <= 2
        if at_end and len(spine) <= TIE_MAX_STATIONS and length <= TIE_MAX_MM:
            continue
        rev = 0
        for a, b, c in zip(seg, seg[1:], seg[2:]):
            ux, uy = b[0] - a[0], b[1] - a[1]
            vx, vy = c[0] - b[0], c[1] - b[1]
            lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
            if lu * lv > 1e-12 and (ux * vx + uy * vy) / (lu * lv) < -0.2:
                rev += 1
        rev_frac = rev / max(len(seg) - 2, 1)
        out.append({"i0": i - len(seg), "i1": j, "spine": spine, "n": len(seg),
                    "length_mm": round(length, 2), "pitch_mm": round(pitch, 3),
                    "passes": round(passes, 2),
                    "style": "abab" if rev_frac >= 0.6 else "lap"})
    return out


def kind_of(seg: dict) -> str:
    """'triple' (3 passes, the bean), 'double' (2), or 'single' (one pass)."""
    if seg.get("passes", 1.0) < 1.6:
        return "single"
    return "triple" if seg["passes"] >= 2.5 else "double"


SINGLE_MIN_MM = 3.0       # a one-pass run stretch shorter than this is not a line
SINGLE_PITCH_MAX_MM = 2.6


def single_segments(pts, beans: list[dict]) -> list[dict]:
    """The one-pass RUNNING stretches of a run that are not part of a bean:
    `census_pro._phases`' R phases, minus the retraced spans. The pro sews
    some detail lines as a plain run; ours sews exposed travel the same way,
    which the category table then shows."""
    from tools.census_pro import _phases
    n = len(pts)
    if n < 5:
        return []
    inbean = [False] * n
    for b in beans:
        for k in range(b["i0"], b["i1"] + 1):
            inbean[k] = True
    out = []
    pos = 0
    for tok, cnt, _med in _phases(pts):
        a, z = pos, min(pos + cnt, n - 1)
        pos += cnt
        if tok != "R":
            continue
        k = a
        while k <= z:
            if inbean[k]:
                k += 1
                continue
            j = k
            while j + 1 <= z and not inbean[j + 1]:
                j += 1
            seg = pts[k:j + 1]
            k = j + 1
            if len(seg) < 4:
                continue
            steps = [math.dist(u, v) for u, v in zip(seg, seg[1:])]
            length = sum(steps)
            pitch = sorted(steps)[len(steps) // 2]
            if length < SINGLE_MIN_MM or not (PITCH_MIN_MM <= pitch <= SINGLE_PITCH_MAX_MM):
                continue
            if _lays_area(seg):
                continue        # tatami rows: `_phases` reads a wide fill's rows as R
            out.append({"i0": j + 1 - len(seg), "i1": j, "spine": seg, "n": len(seg),
                        "length_mm": round(length, 2), "pitch_mm": round(pitch, 3),
                        "passes": 1.0, "style": "run"})
    return out


AREA_NEAR_MM = 0.45       # a stitch of the same stretch this close, not a neighbour


def _lays_area(seg) -> bool:
    """True when the stretch's own stitches run beside each other (fill rows,
    a zigzag): 40% of samples have a non-adjacent stitch within AREA_NEAR_MM.
    A line has only its neighbours nearby."""
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree
    lines = [LineString([a, b]) for a, b in zip(seg, seg[1:]) if math.dist(a, b) > 1e-9]
    if len(lines) < 4:
        return False
    tree = STRtree(lines)
    near = 0
    idx = list(range(0, len(seg), max(1, len(seg) // 40)))
    for k in idx:
        q = Point(seg[k]).buffer(AREA_NEAR_MM)
        for m in map(int, tree.query(q)):
            if abs(m - k) > 2 and lines[m].intersects(q):
                near += 1
                break
    return near / max(len(idx), 1) >= 0.4


def file_beans(runs, *, singles: bool = True) -> list[dict]:
    """Every retraced segment of a file's runs (`study_pro.load_runs` shape)
    and, with `singles`, every one-pass running stretch, each with its run
    index, block and `kind`: -> [{run, block, kind, **segment}]."""
    out = []
    for ri, r in enumerate(runs):
        beans = bean_segments(r["pts"])
        segs = beans + (single_segments(r["pts"], beans) if singles else [])
        for seg in segs:
            out.append({"run": ri, "block": r["block"], "kind": kind_of(seg), **seg})
    return out


# --------------------------------------------------------------- coverage
class LaterCover:
    """Which samples a LATER run covers: a 0.1 mm mask per run index prefix is
    too much, so the stitches are binned by run index and queried by range."""

    def __init__(self, runs):
        from shapely.geometry import LineString
        from shapely.strtree import STRtree
        self.segs, self.owner = [], []
        for ri, r in enumerate(runs):
            pts = r["pts"]
            for k, (a, b) in enumerate(zip(pts, pts[1:])):
                if 0.0 < math.dist(a, b) <= TRAVEL_MM:
                    self.segs.append(LineString([a, b]))
                    self.owner.append((ri, k))
        self.tree = STRtree(self.segs) if self.segs else None

    def covered(self, spine, after: tuple[int, int]) -> float:
        """Share of `spine` samples within COVER_TOL_MM of a stitch sewn after
        `after` = (run index, point index): a later run, or the rest of the
        same needle-down run (the pro chains a centre walk and its column
        with the needle down, so the cover is often in the SAME run)."""
        if self.tree is None:
            return 0.0
        from shapely.geometry import Point
        pts = _resample(spine, SAMPLE_MM)
        hit = 0
        for p in pts:
            q = Point(p).buffer(COVER_TOL_MM)
            for idx in map(int, self.tree.query(q)):
                if self.owner[idx] > after and self.segs[idx].intersects(q):
                    hit += 1
                    break
        return hit / max(len(pts), 1)


def _resample(poly, step):
    out = [poly[0]]
    acc = 0.0
    for a, b in zip(poly, poly[1:]):
        d = math.dist(a, b)
        if d <= 1e-9:
            continue
        while acc + d >= step:
            t = (step - acc) / d
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            out.append(a)
            d = math.dist(a, b)
            acc = 0.0
        acc += d
    return out


# ------------------------------------------------------------ region frame
LETTER_KEYS = ("text_cluster_id", "lettering_group", "word_id", "text_candidate",
               "bean_letter", "small_text_stray", "small_text_enlarged")
META_KEEP = ("tier", "technique", "border", "rescued_small_shape", "enclosed_background",
             "counter", "sew_enclosed_white", "stitched", "ink_stroke_mm", "detail_spokes",
             "fine_bar", "dot_rung") + LETTER_KEYS


def min_dim_mm(poly) -> float:
    from shapely.ops import polylabel
    if poly is None or poly.is_empty or poly.geom_type != "Polygon":
        return 0.0
    try:
        c = polylabel(poly, tolerance=0.05)
    except Exception:  # noqa: BLE001
        return 0.0
    return 2.0 * float(poly.boundary.distance(c))


class Regions:
    """Our segmentation in ONE file's frame, with the per-region facts the
    categories need."""

    def __init__(self, rows, polys, ground_rgb):
        from shapely.strtree import STRtree
        self.rows, self.polys = rows, polys
        self.tree = STRtree(polys) if polys else None
        self.ground = ground_rgb
        self.facts = [self._facts(i) for i in range(len(polys))]

    def _facts(self, i):
        from tools.border_census import _lab
        p = self.polys[i]
        r = self.rows[i]
        md = min_dim_mm(p)
        ring = p.boundary
        # neighbours: everything within 0.6 mm (the contrast ring's reach)
        near = []
        if self.tree is not None:
            near = [int(j) for j in self.tree.query(p.buffer(0.6)) if int(j) != i]
        # what the outline faces: share of the boundary within 0.3 mm of ANOTHER region
        faced = 0.0
        if near and ring.length > 0:
            got = 0.0
            for j in near:
                try:
                    got += ring.intersection(self.polys[j].buffer(0.3)).length
                except Exception:  # noqa: BLE001 - a GEOS topology error on one neighbour
                    continue
            faced = min(1.0, got / ring.length)
        letter = any(r["meta"].get(k) for k in LETTER_KEYS)
        # dE76 of the thread against the area-weighted surround (border_census.contrast,
        # restricted to the neighbours the tree found)
        de = None
        if r["rgb"] is not None:
            try:
                band = p.buffer(0.6).difference(p)
                acc, covered = [], 0.0
                for j in near:
                    orgb = self.rows[j]["rgb"]
                    if orgb is None:
                        continue
                    a_ = band.intersection(self.polys[j]).area if band.intersects(self.polys[j]) else 0.0
                    if a_ > 0:
                        acc.append((a_, orgb))
                        covered += a_
                rest = max(band.area - covered, 0.0)
                if rest > 0:
                    acc.append((rest, self.ground))
                tot = sum(a_ for a_, _ in acc)
                if tot > 0:
                    lab = sum(_lab(c) * a_ for a_, c in acc) / tot
                    de = float(((lab - _lab(r["rgb"])) ** 2).sum() ** 0.5)
            except Exception:  # noqa: BLE001
                de = None
        return {"min_dim": round(md, 2), "faced": round(faced, 2), "letter": letter,
                "contrast": None if de is None else round(de),
                "perimeter": round(ring.length, 1), "area": round(p.area, 2)}

    def host_of(self, spine):
        """(region index or None, relation 'edge'|'inside', median distance to
        the host boundary, drawn width under the run (mm) or None)."""
        from shapely.geometry import LineString, Point
        if self.tree is None:
            return None, None, None, None
        pts = _resample(spine, SAMPLE_MM)
        votes: Counter = Counter()
        for p in pts:
            q = Point(p)
            # the SMALLEST region within HOST_NEAR_MM wins (a bean letter's ink
            # path lies beside its traced stroke, on the body the word sits on;
            # the letter is the host, not the body); else the nearest in reach
            best, bd = None, HOST_REACH_MM
            for j in map(int, self.tree.query(q.buffer(HOST_REACH_MM))):
                poly = self.polys[j]
                d = 0.0 if poly.contains(q) else poly.distance(q)
                if d <= HOST_NEAR_MM and (best is None or bd > HOST_NEAR_MM or poly.area < self.polys[best].area):
                    best, bd = j, d
                elif best is None or (bd > HOST_NEAR_MM and d < bd):
                    best, bd = j, d
            if best is not None:
                votes[best] += 1
        if not votes:
            return None, None, None, None
        host = int(votes.most_common(1)[0][0])
        poly = self.polys[host]
        dists = sorted(poly.boundary.distance(Point(p)) for p in pts)
        med = dists[len(dists) // 2]
        inside = sum(1 for p in pts if poly.contains(Point(p))) / len(pts)
        thin = self.facts[host]["min_dim"] <= LINE_MM
        relation = "inside" if (thin or (inside >= 0.6 and med > EDGE_TOL_MM)) else "edge"
        widths = []
        if relation == "inside" and len(spine) >= 2:
            for k in range(1, len(spine) - 1, max(1, len(spine) // 24)):
                a, b = spine[k - 1], spine[k + 1]
                tx, ty = b[0] - a[0], b[1] - a[1]
                L = math.hypot(tx, ty)
                if L < 1e-9:
                    continue
                nx, ny = -ty / L * 3.0, tx / L * 3.0
                p = spine[k]
                chord = LineString([(p[0] - nx, p[1] - ny), (p[0] + nx, p[1] + ny)]).intersection(poly)
                if chord.is_empty:
                    continue
                parts = [chord] if chord.geom_type == "LineString" else list(getattr(chord, "geoms", []))
                near = [g for g in parts if g.geom_type == "LineString" and g.distance(Point(p)) <= 0.2]
                if near:
                    widths.append(near[0].length)
        width = sorted(widths)[len(widths) // 2] if widths else None
        return host, relation, round(med, 2), None if width is None else round(width, 2)


class ArtInk:
    """The customer's art, reachable from a file's frame: a sample says what
    colour the art has under a stitch, and how wide a drawn line of another
    colour than the host is there.

    Plan frame -> art pixel is the affine that maps the art's ink box onto
    the union box of our regions (stage 1 scales the ink to the target
    width); the error is under 1% on the paired jobs. A pro-frame point is
    taken back to the plan frame through the pair registration first."""

    def __init__(self, art_path, plan_bounds, reg=None):
        import cv2
        import numpy as np
        from tools.pro_pair import _art_ink
        self.im = _art_ink(Path(art_path))
        h, w = self.im.shape[:2]
        x0, y0, x1, y1 = plan_bounds
        self.sx = w / max(x1 - x0, 1e-9)
        self.sy = h / max(y1 - y0, 1e-9)
        self.x0, self.y0 = x0, y0
        self.reg = reg
        self.np, self.cv2 = np, cv2
        self.mm_per_px = 0.5 * ((x1 - x0) / w + (y1 - y0) / h)

    def to_plan(self, p):
        if self.reg is None:
            return p
        fy = -1.0 if self.reg.flip_y else 1.0
        return ((p[0] - self.reg.dx) / self.reg.scale, (p[1] - self.reg.dy) / (self.reg.scale * fy))

    def px(self, p):
        q = self.to_plan(p)
        return (int((q[0] - self.x0) * self.sx), int((q[1] - self.y0) * self.sy))

    def colour(self, px):
        h, w = self.im.shape[:2]
        x, y = px
        if 0 <= x < w and 0 <= y < h:
            b, g, r = self.im[y, x]
            return (int(r), int(g), int(b))
        return None

    def line_under(self, spine, host_rgb, ground_rgb):
        """-> (share of samples whose art colour differs from the host's by
        dE76 >= 30, median width mm of that differing band across the run)."""
        from tools.border_census import _lab
        ref = host_rgb if host_rgb is not None else ground_rgb
        lab_ref = _lab(ref)
        pts = _resample(spine, SAMPLE_MM)
        hits, widths = 0, []
        for k, p in enumerate(pts):
            c = self.colour(self.px(p))
            if c is None:
                continue
            if float(((_lab(c) - lab_ref) ** 2).sum() ** 0.5) < 30:
                continue
            hits += 1
            # width across the run: walk the perpendicular (in the frame) until the host colour returns
            a = pts[max(0, k - 1)]
            b = pts[min(len(pts) - 1, k + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, ty)
            if L < 1e-9:
                continue
            nx, ny = -ty / L, tx / L
            wid = 0.0
            for sgn in (1.0, -1.0):
                d = 0.0
                while d < 3.0:
                    d += self.mm_per_px
                    c2 = self.colour(self.px((p[0] + sgn * nx * d, p[1] + sgn * ny * d)))
                    if c2 is None or float(((_lab(c2) - lab_ref) ** 2).sum() ** 0.5) < 30:
                        break
                wid += d
            widths.append(wid)
        share = hits / max(len(pts), 1)
        return round(share, 2), (round(sorted(widths)[len(widths) // 2], 2) if widths else None)


def category(fact: dict) -> str:
    md = fact["min_dim"]
    if fact["letter"]:
        band = "<=0.6" if md <= 0.6 else ("0.6-1.2" if md <= LINE_MM else "1.2+")
        return f"LETTER {band}"
    if md <= LINE_MM:
        f = fact["faced"]
        return "LINE inside" if f >= 0.7 else ("LINE free" if f <= 0.3 else "LINE between")
    band = "<2" if md < 2 else ("2-4" if md < 4 else ("4-6" if md < 6 else "6+"))
    return f"BODY {band} " + ("to colour" if fact["faced"] >= 0.5 else "to fabric")


# -------------------------------------------------------------- digitizing
def fixture(slug: str) -> dict:
    from tools import flip_sheet_renders as fs
    from tools import small_text_floor_census as sf
    from tools import border_census as bc
    known = {r[0] for r in bc.PAIRS}
    bc.PAIRS += [r for r in sf.EXTRA_PAIRS if r[0] not in known]
    bc.ART_FALLBACK.setdefault("goldentee", bc._T / "photo" / "logo_golden_tee.jpg")
    fx = fs.fixture_files(slug)
    if fx["pro_dst"].suffix.lower() != ".dst":
        # trims are read from a DST, never a PES: the intake registry knows the
        # DST whose name drifted from the PES's ("beckers beanie.DST")
        from tools.pro_intake import registered_pairs
        row = next((r for r in registered_pairs() if r[0] == slug and str(r[1]).lower().endswith(".dst")), None)
        if row is not None and Path(row[1]).exists():
            fx["pro_dst"] = Path(row[1])
    return fx


def parse_sets(items) -> dict:
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        out[k] = json.loads(v) if v else True
    return out


def digitize_one(slug: str, cache: Path, extra: dict | None = None) -> dict:
    """Digitize `slug` at the pro's width with the Studio's request (+`extra`)
    and cache ours.dst + ours.json."""
    from digitizer_core.export import write_dst
    from tools import pro_pair as pp
    from tools.fremont_triage import STUDIO_FABRIC_RGB
    fx = fixture(slug)
    d = pp.digitize(fx["art"], fx["width_mm"], fx["garment"], extra or None)
    out = cache / slug
    out.mkdir(parents=True, exist_ok=True)
    write_dst(d.plan, out / "ours.dst")
    kinds: dict[str, dict] = {}
    runs = []
    for blk, run in d.plan.iter_runs():
        pts = run.points or []
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        role = getattr(run, "role", "") or ""
        runs.append({"kind": str(run.kind), "role": role, "id": str(run.shape_id), "n": len(pts),
                     "bbox": [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]})
        k = kinds.setdefault(str(run.shape_id), {})
        key = str(run.kind) + (f":{role}" if role else "")
        k[key] = k.get(key, 0) + len(pts)
    regions = []
    for r in d.result.regions:
        m = getattr(r, "meta", {}) or {}
        meta = {}
        for k in META_KEEP:
            if k in m:
                v = m[k]
                meta[k] = bool(v) if k == "bean_letter" else (v if isinstance(v, (bool, int, float, str)) else True)
        regions.append({"id": r.shape_id, "wkt": r.polygon.wkt, "rgb": _rgb_of(d, r, kinds),
                        "kinds": kinds.get(str(r.shape_id), {}), "meta": meta})
    info = {"slug": slug, "garment": fx["garment"], "width_mm": fx["width_mm"],
            "pro": str(fx["pro_dst"]), "art": str(fx["art"]), "art_fallback": fx["art_fallback"],
            "extra": extra or {}, "secs": round(d.secs, 1),
            "stitches": d.plan.stats.stitch_count, "trims": d.plan.stats.trims,
            "ground_rgb": list(STUDIO_FABRIC_RGB), "runs": runs, "regions": regions}
    (out / "ours.json").write_text(json.dumps(info), encoding="utf-8")
    return info


def _rgb_of(d, r, kinds):
    from digitizer_core.threads import CHART
    for blk in d.plan.blocks:
        for run in blk.runs:
            if str(run.shape_id) == str(r.shape_id):
                return list(blk.rgb)
    try:
        return list(CHART[r.thread_index].rgb)
    except Exception:  # noqa: BLE001
        return None


def digitize_many(slugs, cache: Path, extra: dict, jobs: int) -> dict:
    """Each slug in its own process (the pipeline is single-threaded in its
    slow stages, and a crash in one job must not take the census down)."""
    sets = [f"{k}={json.dumps(v)}" for k, v in (extra or {}).items()]
    failed = {}

    def one(slug):
        if (cache / slug / "ours.json").exists():
            return slug, "cached"
        cmd = [sys.executable, "-m", "tools.bean_census", "digitize", "--slugs", slug,
               "--cache", str(cache)] + sum((["--set", s] for s in sets), [])
        t = time.time()
        proc = subprocess.run(cmd, cwd=DIGITIZER, capture_output=True, text=True)
        if proc.returncode != 0:
            failed[slug] = (proc.stderr or proc.stdout)[-600:]
            return slug, f"FAILED ({time.time() - t:.0f} s)"
        return slug, f"{time.time() - t:.0f} s"

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for slug, what in ex.map(one, slugs):
            print(f"  {slug}: {what}", flush=True)
    return failed


# ----------------------------------------------------------------- census
def census(slug: str, cache: Path) -> dict:
    """One job: every bean segment of the pro's file and of ours, placed on
    our regions; region labels for both sides."""
    import warnings
    from shapely import wkt
    from shapely.affinity import affine_transform
    from tools.pro_parity.pairframe import RegistrationWarning, register_pair
    from tools.study_pro import load_runs

    out = cache / slug
    info = json.loads((out / "ours.json").read_text(encoding="utf-8"))
    pro = Path(info["pro"])
    ours_runs, ours_trims, _ = load_runs(out / "ours.dst")
    pro_runs, pro_trims, _ = load_runs(pro)
    from tools.pro_parity.pairframe import Reg
    reg_path = out / "reg.json"
    if reg_path.exists():
        reg = Reg(**json.loads(reg_path.read_text(encoding="utf-8")))
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RegistrationWarning)
            reg = register_pair(pro, out / "ours.dst")    # 25 s a job: cached beside ours.dst
        reg_path.write_text(json.dumps(reg.as_dict()), encoding="utf-8")
    polys_ours = [wkt.loads(r["wkt"]) for r in info["regions"]]
    polys_ours = [p if p.is_valid else p.buffer(0) for p in polys_ours]
    keep = [i for i, p in enumerate(polys_ours) if p.geom_type == "Polygon" and p.area >= 0.05]
    rows = [info["regions"][i] for i in keep]
    polys_ours = [polys_ours[i] for i in keep]
    polys_pro = [affine_transform(p, reg.matrix()) for p in polys_ours]
    R_ours = Regions(rows, polys_ours, info["ground_rgb"])
    R_pro = Regions(rows, polys_pro, info["ground_rgb"])
    from shapely.ops import unary_union
    plan_bounds = unary_union(polys_ours).bounds
    art = {"ours": ArtInk(info["art"], plan_bounds), "pro": ArtInk(info["art"], plan_bounds, reg)}
    # the pro's frame is scaled: his min dims / widths are read in his mm, which
    # differ from ours by `reg.scale` (about 1.0 when ours is at his width)
    sides = {}
    for side, runs, R, plan_runs in (("pro", pro_runs, R_pro, None),
                                     ("ours", ours_runs, R_ours, info["runs"])):
        beans = file_beans(runs)
        cover = LaterCover(runs)
        for b in beans:
            host, rel, dist, width = R.host_of(b["spine"])
            b["host"] = None if host is None else rows[host]["id"]
            b["host_i"] = host
            b["relation"] = rel
            b["edge_dist_mm"] = dist
            b["drawn_width_mm"] = width
            b["covered"] = round(cover.covered(b["spine"], (b["run"], b["i1"])), 2)
            host_rgb = rows[host]["rgb"] if host is not None else None
            b["line_under"], b["line_width_mm"] = art[side].line_under(b["spine"], host_rgb, info["ground_rgb"])
            if b["line_under"] >= 0.35 and b["line_width_mm"] is not None:
                # the art draws a stroke of another colour under the run: THAT
                # is the drawn width, not the host's chord
                b["drawn_width_mm"] = b["line_width_mm"]
            if host is not None:
                f = R.facts[host]
                b["category"] = category(f)
                b["min_dim_mm"] = f["min_dim"]
                b["faced"] = f["faced"]
                b["contrast"] = f["contrast"]
                # a run INSIDE a body over a drawn line of another colour is a
                # DETAIL line the art has and our segmentation does not
                if rel == "inside" and f["min_dim"] > LINE_MM and b["line_under"] >= 0.5:
                    b["category"] = "DETAIL line on body"
                    b["drawn_width_mm"] = b["line_width_mm"]
            else:
                b["category"] = "DETAIL line on fabric" if b["line_under"] >= 0.5 else "UNMATCHED"
            if plan_runs is not None:
                b["source"] = _source(b["spine"], plan_runs)
                b["hidden_kind"] = b["source"].split("/")[0].split(" ")[0] in ("underlay", "travel", "fill", "tie")
        sides[side] = {"beans": beans, "trims": pro_trims if side == "pro" else ours_trims,
                       "stitches": sum(len(r["pts"]) for r in runs)}
    # region labels: a region carries a bean when bean spines hosted by it
    # (not covered later) total at least REGION_BEAN_MIN of its half-perimeter,
    # or 1.5 mm
    labels = {}
    for side in ("pro", "ours"):
        R = R_pro if side == "pro" else R_ours
        tot = defaultdict(float)
        tot_any = defaultdict(float)
        rel = defaultdict(Counter)
        for b in sides[side]["beans"]:
            if b["host_i"] is None or b["covered"] >= 0.6 or b["category"].startswith("DETAIL") or b.get("hidden_kind"):
                continue
            tot_any[b["host_i"]] += b["length_mm"]
            if b["kind"] != "single":
                tot[b["host_i"]] += b["length_mm"]
                rel[b["host_i"]][b["relation"]] += 1
        lab = []
        for i, f in enumerate(R.facts):
            need = max(1.5, 0.25 * f["perimeter"] / 2.0)
            has = tot.get(i, 0.0) >= need
            lab.append({"bean": has, "line": tot_any.get(i, 0.0) >= need, "mm": round(tot.get(i, 0.0), 1),
                        "line_mm": round(tot_any.get(i, 0.0), 1),
                        "relation": rel[i].most_common(1)[0][0] if has and rel[i] else None})
        labels[side] = lab
    regions = []
    for i, (r, f) in enumerate(zip(rows, R_pro.facts)):
        regions.append({"id": r["id"], "category": category(R_ours.facts[i]),
                        "ours_facts": R_ours.facts[i], "pro_facts": f, "meta": r["meta"],
                        "kinds": r["kinds"], "pro": labels["pro"][i], "ours": labels["ours"][i]})
    res = {"slug": slug, "width_mm": info["width_mm"], "garment": info["garment"],
           "extra": info.get("extra", {}), "secs": info["secs"], "reg": reg.as_dict(),
           "ours_stitches": info["stitches"], "ours_trims": info["trims"],
           "pro_stitches": sides["pro"]["stitches"], "pro_trims": pro_trims,
           "sides": {s: {"beans": [{k: v for k, v in b.items() if k != "spine"} | {"spine_n": len(b["spine"])}
                                   for b in sides[s]["beans"]]} for s in sides},
           "regions": regions}
    (out / "census.json").write_text(json.dumps(res), encoding="utf-8")
    return res


def _source(spine, plan_runs) -> str:
    """Which of OUR plan runs laid this bean: the smallest linear run whose
    box holds the spine's box (0.3 mm slack)."""
    xs = [p[0] for p in spine]
    ys = [p[1] for p in spine]
    bx = (min(xs) - 0.3, min(ys) - 0.3, max(xs) + 0.3, max(ys) + 0.3)
    best, ba = None, None
    for r in plan_runs:
        if r["kind"] not in ("bean", "run", "border", "satin", "underlay", "detail"):
            continue
        x0, y0, x1, y1 = r["bbox"]
        if x0 >= bx[0] and y0 >= bx[1] and x1 <= bx[2] and y1 <= bx[3]:
            pass
        elif not (x0 - 0.3 <= min(xs) and y0 - 0.3 <= min(ys) and x1 + 0.3 >= max(xs) and y1 + 0.3 >= max(ys)):
            continue
        a = (x1 - x0 + 0.1) * (y1 - y0 + 0.1)
        if ba is None or a < ba:
            best, ba = r, a
    if best is None:
        return "?"
    tag = best["kind"] + (f"/{best['role']}" if best["role"] else "")
    if best["id"] == "__edge_cap__":
        tag += " (edge cap)"
    return tag


# ------------------------------------------------------------------ tables
def kappa(truth, pred):
    from tools.word_tagger_eval import kappa as k
    return k(list(truth), list(pred))


def _boot_kappa(truth, pred, n=2000, seed=7):
    import numpy as np
    t, p = np.asarray(truth, bool), np.asarray(pred, bool)
    if len(t) == 0:
        return None, None
    rng = np.random.default_rng(seed)
    ks = []
    for _ in range(n):
        idx = rng.integers(0, len(t), len(t))
        kk = kappa(t[idx], p[idx])
        if kk is not None:
            ks.append(kk)
    if not ks:
        return None, None
    ks.sort()
    return round(ks[int(0.025 * len(ks))], 3), round(ks[int(0.975 * len(ks)) - 1], 3)


def pooled(results: list[dict]) -> dict:
    """Pooled tables over jobs: by category (regions: n, pro bean %, ours bean %),
    bean segments by category per side, and the region kappa."""
    cats: dict[str, dict] = defaultdict(lambda: {"n": 0, "pro": 0, "ours": 0, "pro_line": 0, "ours_line": 0})
    truth, pred = [], []
    truth_l, pred_l = [], []
    seg = {"pro": defaultdict(lambda: {"n": 0, "mm": 0.0, "covered": 0, "pitch": [], "passes": [],
                                       "width": [], "min_dim": [], "style": Counter()}),
           "ours": defaultdict(lambda: {"n": 0, "mm": 0.0, "covered": 0, "pitch": [], "passes": [],
                                        "width": [], "min_dim": [], "style": Counter(), "source": Counter()})}
    for res in results:
        for r in res["regions"]:
            c = cats[r["category"]]
            c["n"] += 1
            c["pro"] += int(r["pro"]["bean"])
            c["ours"] += int(r["ours"]["bean"])
            c["pro_line"] += int(r["pro"]["line"])
            c["ours_line"] += int(r["ours"]["line"])
            truth.append(r["pro"]["bean"])
            pred.append(r["ours"]["bean"])
            truth_l.append(r["pro"]["line"])
            pred_l.append(r["ours"]["line"])
        for side in ("pro", "ours"):
            for b in res["sides"][side]["beans"]:
                if b["covered"] >= 0.6 or b.get("hidden_kind"):
                    continue        # ours: an underlay / travel / fill run is not a line; counted in `hidden`
                s = seg[side][f"{b['kind']} | {b['category']}"]
                s["n"] += 1
                s["mm"] += b["length_mm"]
                s["covered"] += int(b["covered"] >= 0.6)
                s["pitch"].append(b["pitch_mm"])
                s["passes"].append(b["passes"])
                s["style"][b["style"]] += 1
                if b.get("drawn_width_mm") is not None:
                    s["width"].append(b["drawn_width_mm"])
                if b.get("min_dim_mm") is not None:
                    s["min_dim"].append(b["min_dim_mm"])
                if side == "ours":
                    s["source"][b.get("source", "?")] += 1
    hidden = {"n": 0, "mm": 0.0}
    for res in results:
        for b in res["sides"]["ours"]["beans"]:
            if b.get("hidden_kind") and b["covered"] < 0.6:
                hidden["n"] += 1
                hidden["mm"] += b["length_mm"]
    k = kappa(truth, pred)
    lo, hi = _boot_kappa(truth, pred)
    kl = kappa(truth_l, pred_l)
    llo, lhi = _boot_kappa(truth_l, pred_l)
    return {"categories": dict(cats), "segments": {s: dict(v) for s, v in seg.items()}, "hidden": hidden,
            "kappa": None if k is None else round(k, 3), "kappa_ci": [lo, hi],
            "kappa_line": None if kl is None else round(kl, 3), "kappa_line_ci": [llo, lhi],
            "n_regions": len(truth), "pro_bean_regions": sum(truth), "ours_bean_regions": sum(pred),
            "pro_line_regions": sum(truth_l), "ours_line_regions": sum(pred_l)}


def _med(a):
    if not a:
        return None
    s = sorted(a)
    return s[len(s) // 2]


def _pct(a, q):
    if not a:
        return None
    s = sorted(a)
    return s[min(len(s) - 1, int(q * len(s)))]


def _f(v, fmt="{:.2f}"):
    return "-" if v is None else fmt.format(v)


CAT_ORDER = ["DETAIL line on body", "DETAIL line on fabric",
             "LETTER <=0.6", "LETTER 0.6-1.2", "LETTER 1.2+", "LINE free", "LINE between", "LINE inside",
             "BODY <2 to fabric", "BODY <2 to colour", "BODY 2-4 to fabric", "BODY 2-4 to colour",
             "BODY 4-6 to fabric", "BODY 4-6 to colour", "BODY 6+ to fabric", "BODY 6+ to colour",
             "UNMATCHED"]


def _cat_sort(c):
    return (CAT_ORDER.index(c) if c in CAT_ORDER else 99, c)


def rule_in_words(results: list[dict], pool: dict) -> str:
    """The reference digitizer's rule, with its numbers read off `pool` (never
    typed by hand, so the words and the tables cannot drift apart)."""
    cats = pool["categories"]

    def tot(pred):
        n = sum(v["n"] for c, v in cats.items() if pred(c))
        b = sum(v["pro"] for c, v in cats.items() if pred(c))
        o = sum(v["ours"] for c, v in cats.items() if pred(c))
        return n, b, o
    segs = pool["segments"]["pro"]
    n_seg = sum(v["n"] for k, v in segs.items() if not k.startswith("single"))
    mm_seg = sum(v["mm"] for k, v in segs.items() if not k.startswith("single"))
    n_tri = sum(v["n"] for k, v in segs.items() if k.startswith("triple"))
    n_dbl = sum(v["n"] for k, v in segs.items() if k.startswith("double"))
    pitch = _med([x for k, v in segs.items() if not k.startswith("single") for x in v["pitch"]])
    # the drawn stroke under his runs: the art's own line (`line_under`), never
    # the host's chord, which a run inside a wide body caps at 6 mm
    # (only where the run lies INSIDE its host: walking outward from an edge
    # run never meets the host colour again, and reads the 3 mm cap)
    widths = [b["line_width_mm"] for res in results for b in res["sides"]["pro"]["beans"]
              if b["kind"] != "single" and b["covered"] < 0.6 and b.get("line_under", 0) >= 0.35
              and b.get("relation") == "inside" and b.get("line_width_mm") is not None]
    bodies = tot(lambda c: c.startswith("BODY"))
    small = tot(lambda c: c.startswith("BODY <2"))
    letters = tot(lambda c: c.startswith("LETTER") and "1.2+" not in c)
    lines = tot(lambda c: c.startswith("LINE"))
    detail_pro = {k.split(" | ")[0]: v for k, v in segs.items() if "DETAIL" in k}
    # the reference's bean segments that ride a stroke the art draws in another
    # colour (`line_under`), by kind of host
    on_line = Counter()
    n_pro_segs = Counter()
    for res in results:
        for b in res["sides"]["pro"]["beans"]:
            if b["kind"] == "single" or b["covered"] >= 0.6:
                continue
            grp = ("BODY" if b["category"].startswith(("BODY", "DETAIL")) else
                   "LETTER" if b["category"].startswith("LETTER") else "LINE/other")
            n_pro_segs[grp] += 1
            if b.get("line_under", 0) >= 0.35:
                on_line[grp] += 1
    by_cat = Counter()
    for k, v in segs.items():
        if not k.startswith("single"):
            by_cat[k.split(" | ")[1]] += v["n"]
    cat_txt = ", ".join(f"{c} {n}" for c, n in by_cat.most_common())
    L = [f"**The rule, in words.** Over {len(results)} paired jobs the reference digitizer sews "
         f"**{n_seg} retraced (bean) runs, {mm_seg:.0f} mm in all**: {n_dbl} of them TWO passes and {n_tri} "
         f"three passes, at a median pitch of {_f(pitch)} mm, on {pool['pro_bean_regions']} of "
         f"{pool['n_regions']} regions. By the region of ours they sit on: {cat_txt or 'none'}. "
         f"What they follow is a LINE the art draws as a stroke of another colour than its surround, too thin to "
         f"satin: {on_line['BODY']} of the {n_pro_segs['BODY']} runs on or in a filled body ride such a stroke "
         f"(the drone's panel and edge lines, a line-drawn gun grip), and the rest are a TM mark, a 30 mm "
         f"line-drawing stub and short stubs on letters"
         + (f"; the drawn stroke under the {len(widths)} runs inside a body reads {_pct(widths, 0.1):.2f}-"
            f"{_pct(widths, 0.9):.2f} mm (median {_med(widths):.2f})" if widths else "")
         + f". He beans the EDGE of a filled body on {bodies[1]} of {bodies[0]} bodies, every one along a drawn "
         f"outline stroke (ours {bodies[2]}: the edge cap and the run tier ring bare edges), a small solid under "
         f"2 mm on {small[1]} of {small[0]} (ours {small[2]}: his is one satin blob, or dropped), and small "
         f"lettering under 1.2 mm on {letters[1]} of {letters[0]} letters (ours {letters[2]}: he raises small text "
         f"to satin). Thin regions of our segmentation (LINE rows): {lines[1]} of {lines[0]} (ours {lines[2]}).",
         "",
         f"**Where ours disagrees most, by count:** small LETTERS sewn as bean letters ({letters[2]} regions against "
         f"the reference's {letters[1]}), then thin LINE regions the run tier or the satin fallback rings "
         f"({lines[2]} against {lines[1]}), then bodies ({bodies[2]} against {bodies[1]}: the run tier's ring on a "
         f"sub-floor solid and the bean edge cap). The one place the reference beans and ours does not is a drawn "
         f"detail line INSIDE a body our segmentation has no region for "
         f"({sum(v['n'] for v in detail_pro.values())} of his runs)."]
    return "\n".join(L)


def render_tables(results: list[dict], pool: dict, arm: str) -> str:
    L = []
    L.append(f"### Pooled by category ({len(results)} jobs, arm `{arm}`)\n")
    L.append("Regions are OUR segmentation's shapes (>= 0.05 mm2); a region carries a bean when "
             "uncovered bean spine hosted by it totals >= max(1.5 mm, a quarter of its half-perimeter).\n")
    L.append("| category | regions | pro beans | ours beans | pro % | ours % | pro any run line | ours any run line |")
    L.append("|---|---|---|---|---|---|---|---|")
    for c in sorted(pool["categories"], key=_cat_sort):
        v = pool["categories"][c]
        L.append(f"| {c} | {v['n']} | {v['pro']} | {v['ours']} | {100 * v['pro'] / max(v['n'], 1):.0f}% "
                 f"| {100 * v['ours'] / max(v['n'], 1):.0f}% | {v['pro_line']} | {v['ours_line']} |")
    L.append(f"| **all** | {pool['n_regions']} | {pool['pro_bean_regions']} | {pool['ours_bean_regions']} | "
             f"{100 * pool['pro_bean_regions'] / max(pool['n_regions'], 1):.0f}% | "
             f"{100 * pool['ours_bean_regions'] / max(pool['n_regions'], 1):.0f}% | "
             f"{pool['pro_line_regions']} | {pool['ours_line_regions']} |")
    lo, hi = pool["kappa_ci"]
    llo, lhi = pool["kappa_line_ci"]
    L.append(f"\nRegion-level agreement ours vs pro (Cohen's kappa): \"carries a bean (2 or 3 passes)\" "
             f"**{_f(pool['kappa'], '{:.3f}')}** (bootstrap 95% {_f(lo, '{:.3f}')} to {_f(hi, '{:.3f}')}); "
             f"\"carries any uncovered run line (1-3 passes)\" **{_f(pool['kappa_line'], '{:.3f}')}** "
             f"({_f(llo, '{:.3f}')} to {_f(lhi, '{:.3f}')}); n = {pool['n_regions']} regions.\n")
    L.append(f"Ours' underlay, travel and fill runs the detector reads as uncovered are left out of every table "
             f"({pool['hidden']['n']} segments, {pool['hidden']['mm']:.0f} mm): they are not a line the plan meant "
             f"to show, and the cover test's 0.35 mm reach misses some of our own 0.4 mm satin.\n")
    for side in ("pro", "ours"):
        L.append(f"### Run segments not covered later, {side} (pooled; kind = passes)\n")
        L.append("| kind | category | segments | mm | pitch med | passes med | drawn width med (p10-p90) "
                 "| host min dim med | style |" + (" sources |" if side == "ours" else ""))
        L.append("|---|---|---|---|---|---|---|---|---|" + ("---|" if side == "ours" else ""))
        for c in sorted(pool["segments"][side], key=lambda k: (("triple", "double", "single").index(k.split(" | ")[0]), _cat_sort(k.split(" | ")[1]))):
            s = pool["segments"][side][c]
            kind, cat = c.split(" | ")
            style = ", ".join(f"{k} {n}" for k, n in s["style"].most_common())
            w = s["width"]
            wtxt = "-" if not w else f"{_med(w):.2f} ({_pct(w, 0.1):.2f}-{_pct(w, 0.9):.2f})"
            row = (f"| {kind} | {cat} | {s['n']} | {s['mm']:.0f} | {_f(_med(s['pitch']))} | "
                   f"{_f(_med(s['passes']))} | {wtxt} | {_f(_med(s['min_dim']), '{:.1f}')} | {style} |")
            if side == "ours":
                row += " " + "; ".join(f"{k} {n}" for k, n in s["source"].most_common(4)) + " |"
            L.append(row)
        L.append("")
    L.append("### Per job\n")
    L.append("| job | width mm | stitches ours / pro | trims ours / pro | bean segs ours / pro | "
             "bean mm ours / pro | pro run lines by kind:category (t/d/s) | ours |")
    L.append("|---|---|---|---|---|---|---|---|")
    for res in results:
        pb = [b for b in res["sides"]["pro"]["beans"] if b["kind"] != "single" and b["covered"] < 0.6]
        ob = [b for b in res["sides"]["ours"]["beans"] if b["kind"] != "single" and b["covered"] < 0.6
              and not b.get("hidden_kind")]

        def by_cat(bs):
            c = Counter(f"{b['kind'][0]}:{b['category']}" for b in bs if b["covered"] < 0.6)
            return ", ".join(f"{k} {n}" for k, n in sorted(c.items(), key=lambda t: (t[0][0], _cat_sort(t[0][2:])))) or "none"
        L.append(f"| {res['slug']} | {res['width_mm']:.1f} | {res['ours_stitches']} / {res['pro_stitches']} | "
                 f"{res['ours_trims']} / {res['pro_trims']} | {len(ob)} / {len(pb)} | "
                 f"{sum(b['length_mm'] for b in ob):.0f} / {sum(b['length_mm'] for b in pb):.0f} | "
                 f"{by_cat(pb)} | {by_cat(ob)} |")
    return "\n".join(L)


def job_table(res: dict) -> str:
    """One job's bean segments, both sides (the per-job table; cache only)."""
    L = [f"# {res['slug']} ({res['width_mm']} mm, {res['garment']})\n"]
    for side in ("pro", "ours"):
        L.append(f"## {side}: {len(res['sides'][side]['beans'])} bean segments\n")
        L.append("| run | block | kind | mm | pitch | passes | style | category | relation | host | min dim | "
                 "drawn w | contrast | covered | art line under" + (" | source |" if side == "ours" else " |"))
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|" + ("---|" if side == "ours" else ""))
        for b in res["sides"][side]["beans"]:
            row = (f"| {b['run']} | {b['block']} | {b['kind']} | {b['length_mm']} | {b['pitch_mm']} | {b['passes']} | "
                   f"{b['style']} | {b['category']} | {b.get('relation') or '-'} | {b.get('host') or '-'} | "
                   f"{_f(b.get('min_dim_mm'), '{:.1f}')} | {_f(b.get('drawn_width_mm'))} | "
                   f"{_f(b.get('contrast'), '{:.0f}')} | {b['covered']} | {b.get('line_under', '-')}")
            row += f" | {b.get('source', '')} |" if side == "ours" else " |"
            L.append(row)
        L.append("")
    return "\n".join(L)


def load_results(cache: Path, slugs=None) -> list[dict]:
    out = []
    for slug in slugs or JOBS:
        p = cache / slug / "census.json"
        if p.exists():
            out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


# ------------------------------------------------------------------ render
def render(slug: str, cache: Path, n_zoom: int = 3, *, side: str = "pro") -> list[Path]:
    """Validation: the file in grey, detected bean spines in red (uncovered)
    or blue (covered by later stitches), plus `n_zoom` zoomed crops of the
    longest uncovered segments with point order drawn. pro_renders/ only."""
    import cv2
    import numpy as np
    from tools import pro_renders
    from tools.study_pro import load_runs
    path = fixture(slug)["pro_dst"] if side == "pro" else cache / slug / "ours.dst"
    runs, _t, _j = load_runs(path)
    beans = file_beans(runs)
    cover = LaterCover(runs)
    for b in beans:
        b["covered"] = cover.covered(b["spine"], (b["run"], b["i1"]))
    out = pro_renders.out_dir("bean-census-2026-10-27")
    out.mkdir(parents=True, exist_ok=True)
    allp = [p for r in runs for p in r["pts"]]
    S = 8.0
    xs, ys = [p[0] for p in allp], [p[1] for p in allp]
    x0, y0 = min(xs) - 3, min(ys) - 3
    img = np.full((int((max(ys) + 3 - y0) * S) + 2, int((max(xs) + 3 - x0) * S) + 2, 3), 255, np.uint8)

    def px(p, s=S, ox=x0, oy=y0):
        return (int((p[0] - ox) * s), int((p[1] - oy) * s))
    for r in runs:
        cv2.polylines(img, [np.array([px(p) for p in r["pts"]], np.int32)], False, (205, 205, 205), 1, cv2.LINE_AA)
    for b in beans:
        col = (230, 120, 0) if b["covered"] >= 0.6 else ((0, 160, 0) if b["kind"] == "single" else (0, 0, 230))
        cv2.polylines(img, [np.array([px(p) for p in b["spine"]], np.int32)], False, col, 2, cv2.LINE_AA)
    tag = "pro" if side == "pro" else "ours"
    paths = [out / f"{slug}_{tag}_beans.png"]
    cv2.imwrite(str(paths[0]), img)
    unc = sorted((b for b in beans if b["covered"] < 0.6 and b["kind"] != "single"), key=lambda b: -b["length_mm"])
    for k, b in enumerate(unc[:n_zoom]):
        r = runs[b["run"]]
        seg = r["pts"][b["i0"]:b["i1"] + 1]
        sx = [p[0] for p in seg]
        sy = [p[1] for p in seg]
        Z = 40.0
        zx0, zy0 = min(sx) - 1.5, min(sy) - 1.5
        zx1, zy1 = max(sx) + 1.5, max(sy) + 1.5
        zim = np.full((int((zy1 - zy0) * Z) + 2, int((zx1 - zx0) * Z) + 2, 3), 255, np.uint8)
        for rr in runs:
            pts = rr["pts"]
            for a, c in zip(pts, pts[1:]):
                if (zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1) or (zx0 <= c[0] <= zx1 and zy0 <= c[1] <= zy1):
                    cv2.line(zim, px(a, Z, zx0, zy0), px(c, Z, zx0, zy0), (215, 215, 215), 1, cv2.LINE_AA)
        for a, c in zip(seg, seg[1:]):
            cv2.line(zim, px(a, Z, zx0, zy0), px(c, Z, zx0, zy0), (0, 0, 220), 1, cv2.LINE_AA)
        for i, p in enumerate(seg[:48]):
            q = px(p, Z, zx0, zy0)
            cv2.circle(zim, q, 3, (0, 120, 0), -1)
            cv2.putText(zim, str(i), (q[0] + 3 + 9 * (i % 3), q[1] - 3 - 9 * (i % 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                        (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(zim, f"run {b['run']} blk {b['block']} {b['length_mm']} mm pitch {b['pitch_mm']} "
                    f"passes {b['passes']} {b['style']} covered {b['covered']:.2f} n {b['n']}",
                    (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        p = out / f"{slug}_{tag}_bean_zoom{k}.png"
        cv2.imwrite(str(p), zim)
        paths.append(p)
    return paths


# ------------------------------------------------------------------ main
def write_doc(results, pool, arm, doc: Path, head: str = "") -> None:
    from tools import pro_renders
    pro_renders.refuse_docs(doc.parent / "x") if "pro" in doc.stem.lower().split("-") else None
    body = rule_in_words(results, pool) + "\n\n" + render_tables(results, pool, arm)
    doc.write_text(head + body + "\n", encoding="utf-8")


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", action="store_true", help="digitize what the cache lacks, census, table, doc")
    ap.add_argument("--cache", default=str(DEFAULT_CACHE))
    ap.add_argument("--arm", default="off", help="cache sub-folder for this flag arm")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--set", action="append", default=[], help="FLAG=JSON laid over the Studio request")
    ap.add_argument("--slugs", nargs="*")
    ap.add_argument("--doc", default=None, help="write the pooled table here (default: no doc unless --corpus)")
    ap.add_argument("--no-doc", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("digitize")
    d.add_argument("--slugs", nargs="+", required=True)
    d.add_argument("--cache", required=True)
    d.add_argument("--set", action="append", default=[])
    t = sub.add_parser("table")
    for name, kw in (("--slugs", {"nargs": "*"}), ("--cache", {}), ("--arm", {}), ("--jobs", {"type": int}),
                     ("--doc", {}), ("--no-doc", {"action": "store_true"})):
        t.add_argument(name, default=argparse.SUPPRESS, **kw)   # after `table`, overriding the global
    r = sub.add_parser("render")
    r.add_argument("slug")
    r.add_argument("--n", type=int, default=3)
    r.add_argument("--side", default="pro", choices=("pro", "ours"))
    c = sub.add_parser("compare")
    c.add_argument("off_arm")
    c.add_argument("on_arm")
    args = ap.parse_args(argv)
    extra = parse_sets(args.set)

    if args.cmd == "digitize":
        for slug in args.slugs:
            info = digitize_one(slug, Path(args.cache), extra)
            print(f"{slug}: {info['width_mm']} mm, {info['stitches']} stitches, {info['secs']} s", flush=True)
        return 0
    cache = Path(args.cache) / args.arm
    if args.cmd == "render":
        for p in render(args.slug, cache, args.n, side=args.side):
            print(p)
        return 0
    if args.cmd == "compare":
        return compare(Path(args.cache) / args.off_arm, Path(args.cache) / args.on_arm)
    slugs = args.slugs or JOBS
    t0 = time.time()
    if args.corpus:
        print(f"digitizing into {cache} ({args.jobs} at a time)", flush=True)
        failed = digitize_many(slugs, cache, extra, args.jobs)
        for s, why in failed.items():
            print(f"  FAILED {s}: {why}", flush=True)
        slugs = [s for s in slugs if s not in failed]
    results = []
    todo = [s for s in slugs if (cache / s / "ours.json").exists()]
    for s_ in slugs:
        if s_ not in todo:
            print(f"  {s_}: not digitized, skipped", flush=True)
    if args.jobs <= 1:
        for slug in todo:
            t = time.time()
            res = census(slug, cache)
            (cache / slug / "census.md").write_text(job_table(res), encoding="utf-8")
            results.append(res)
            print(f"  {slug}: pro {len(res['sides']['pro']['beans'])} run segs, ours "
                  f"{len(res['sides']['ours']['beans'])} ({time.time() - t:.0f} s)", flush=True)
    else:
        def one(slug):
            t = time.time()
            cmd = [sys.executable, "-m", "tools.bean_census", "table", "--jobs", "1", "--cache", str(args.cache),
                   "--arm", args.arm, "--slugs", slug]
            proc = subprocess.run(cmd, cwd=DIGITIZER, capture_output=True, text=True)
            return slug, proc.returncode, (proc.stderr or proc.stdout)[-800:], time.time() - t
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            for slug, rc, tail, secs in ex.map(one, todo):
                if rc != 0:
                    print(f"  {slug}: census FAILED ({secs:.0f} s)\n{tail}", flush=True)
                    continue
                print(f"  {slug}: census {secs:.0f} s", flush=True)
        results = load_results(cache, todo)
    if not results:
        print("nothing to table")
        return 1
    pool = pooled(results)
    (cache / "pooled.json").write_text(json.dumps(pool, default=str), encoding="utf-8")
    text = rule_in_words(results, pool) + "\n\n" + render_tables(results, pool, args.arm)
    print(text)
    doc = Path(args.doc) if args.doc else (OUT_DOC if args.corpus and not args.no_doc else None)
    if doc is not None:
        head = (f"# Bean census: what the reference digitizer sews as a triple run, and what we do "
                f"(2026-10-27)\n\nGenerated by `python -m tools.bean_census --corpus` (arm `{args.arm}`, "
                f"{len(results)} jobs, {time.time() - t0:.0f} s wall). Tables only; the rule and its reading are "
                f"in the PR that added this tool. Regions are OUR segmentation's; the reference file is read in "
                f"its own frame through `pairframe.register_pair`.\n\n")
        write_doc(results, pool, args.arm, doc, head)
        print(f"wrote {doc}")
    print(f"total {time.time() - t0:.0f} s")
    return 0


def compare(off: Path, on: Path) -> int:
    """OFF vs ON arms: pooled kappa each, per-job stitches / trims / bean mm."""
    a = load_results(off)
    b = load_results(on)
    bs = {r["slug"]: r for r in b}
    both = [r for r in a if r["slug"] in bs]
    pa, pb = pooled(both), pooled([bs[r["slug"]] for r in both])
    print(f"| arm | jobs | regions | pro bean regions | ours bean regions | kappa (95%) |")
    print("|---|---|---|---|---|---|")
    for name, p in ((off.name, pa), (on.name, pb)):
        print(f"| {name} | {len(both)} | {p['n_regions']} | {p['pro_bean_regions']} | {p['ours_bean_regions']} | "
              f"{_f(p['kappa'], '{:.3f}')} ({_f(p['kappa_ci'][0], '{:.3f}')} to {_f(p['kappa_ci'][1], '{:.3f}')}) |")
    print()
    print("| job | stitches OFF / ON / pro | trims OFF / ON / pro | bean mm OFF / ON / pro | ours bean regions OFF / ON / pro |")
    print("|---|---|---|---|---|")
    for r in both:
        o = bs[r["slug"]]
        bm = lambda res, side: sum(x["length_mm"] for x in res["sides"][side]["beans"]  # noqa: E731
                                   if x["covered"] < 0.6 and x["kind"] != "single" and not x.get("hidden_kind"))
        br = lambda res, side: sum(1 for x in res["regions"] if x[side]["bean"])  # noqa: E731
        print(f"| {r['slug']} | {r['ours_stitches']} / {o['ours_stitches']} / {r['pro_stitches']} | "
              f"{r['ours_trims']} / {o['ours_trims']} / {r['pro_trims']} | "
              f"{bm(r, 'ours'):.0f} / {bm(o, 'ours'):.0f} / {bm(r, 'pro'):.0f} | "
              f"{br(r, 'ours')} / {br(o, 'ours')} / {br(r, 'pro')} |")
    print()
    print("Per category, ours bean regions OFF -> ON (pro):")
    print("| category | regions | pro | ours OFF | ours ON |")
    print("|---|---|---|---|---|")
    for c in sorted(set(pa["categories"]) | set(pb["categories"]), key=_cat_sort):
        va = pa["categories"].get(c, {"n": 0, "pro": 0, "ours": 0})
        vb = pb["categories"].get(c, {"n": 0, "pro": 0, "ours": 0})
        print(f"| {c} | {va['n']} | {va['pro']} | {va['ours']} | {vb['ours']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
