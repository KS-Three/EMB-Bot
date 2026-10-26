#!/usr/bin/env python
"""reset_room_census: where the pro finds the ROOM for a re-set line of small
text -- does he move the line, re-lay a bar, shrink a neighbour? -- beside
where our re-set (`small_text.enlarge_small_text`) puts it and why it stops.

Measure only: nothing in `digitizer_core/` is read differently or changed.

WHY. The pro re-sets every line drawn under ~3.2 mm to ~4-4.6 mm
(`docs/small-text-floor-2026-10-24.md`). Ours stops short where the design
is crowded: the ProSeal beanie's tagline at x1.15 (his x1.49), Drone at
x1.32 (his x1.57). This reads, line by line, how far he moved the line, how
much it grew, and what became of the shapes around it.
`docs/reset-room-2026-10-25.md` has the census and the rule it gives.

PER LINE (one reader on every file):
  art     the line's shapes as traced at the pro's width, BEFORE the re-set
          (`art.json`, snapshotted as `enlarge_small_text` is called).
  frame   a line's x extremes, its CAP LINE and its BASELINE: the median top
          and bottom of the letters at least 0.6 of the tallest
          (`line_frame`), so an O's overshoot moves nothing. In a machine
          file the letters are `sewn_line`'s: letter pieces of every colour
          block, read painted and opened (letters the pro joins through
          travel come apart), grouped into rows; the row covering the art
          line's span, nearest it, wins, and a same-height letter of
          another colour at its ends joins it. Painted 0.3 mm wide; the
          frame is their needle extents (half the thread off each side).
          The search box is generous (`search_box`): the floor census's
          own reader drops a letter more than a cap off the art line, and
          the pro moved Fremont's EST 1895 further than that.
  carry   the pro's file is carried into ours (`register`): SCALE from the
          design's own big lettering (PROSEAL, THERMAL, HOTEL FREMONT read
          in both files: `REFS`), since the x-extent ratio the census
          registration uses is not the content's wherever one file has
          thread the other lacks (the beanie: his width includes his
          knockdown, so his content is x0.96 ours, where the extents say
          0.955 and an IoU search 0.945); then the TRANSLATION by thread IoU
          at that scale, 0.5 mm then 0.1 mm. A move under ~0.25 mm is none.
  move    the sewn frame against the art's (mm, our frame, y DOWN: + is
          down): dy of the cap line (`dy_top`), the centre and the baseline
          (`dy_bottom`), dx of the centre, h and w and their scale on the
          art's.
  neighbours  every art shape within 3 caps above or below the line's span,
          or in its band within 2 caps either side (a bar, a badge, the
          word above), and its counterpart in each file (`match`): each
          colour block's thread clipped to the art box grown by a quarter of
          its short side (at least 1 mm), slivers of other shapes dropped;
          the block whose pieces overlap the art box best (IoU >= 0.3).
          Their move: dx, dy, dw, dh. Not found is a reading too -- the pro
          sews no rope on Fremont -- but so is a neighbour moved over ~1 mm
          or sewn joined into the line's own block (Drone's dashes).
  room    the free fabric from the line to its OWN neighbours above and
          below as each file sews them (the art's polygons; a file's thread,
          edge to edge), per column of the line's span: min and median. A
          ground under the line is never in it, since only matched
          neighbours count. None: no neighbour there.
  growth  ours: `enlarge_small_text`'s report rows of the line's clusters
          (scale, width_scale, shift_mm, skipped, blocked_by).

  python -m tools.reset_room_census digitize --cache DIR [--set K=JSON ...] SLUG ...
  python -m tools.reset_room_census --cache DIR [--only SLUG] [--crops OUT] [--json OUT]

`digitize` runs `tools.pro_pair.digitize` at the pro's width with the re-set
set explicit (`RESET_SET`, #1057's defaults; None on main when written) and
caches ours.dst + ours.json (`border_census.write_ours`), art.json and
growth.json per slug. The pro's files and ProSeal's art are read through
`border_census.roots()`; nothing here copies one into the repo.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools.small_text_floor_census import RESET_SET  # noqa: E402  #1057's defaults, explicit

PPM = 20.0
THREAD_MM = 0.3         # the census reader's painted thread
TALL_FRAC = 0.6
ABOVE_CAPS = 3.0        # how far above / below a neighbour is looked for, in caps
SIDE_CAPS = 2.0         # and either side in the line's band
NEIGHBOUR_IOU = 0.3
MIN_SHAPE_MM2 = 0.05

MATCH_GROW_MM = 1.0     # a neighbour moved up to ~1 mm is still found
MIN_COVER = 0.3         # of the art line's span a sewn row must cover
OPEN_MM = 0.55          # `small_text_columns.OPEN_MM`: travel between letters falls away
OPENED_KEEP = 0.9       # the opened read wins unless it covers under this share of the plain one's score
ROW_OFF_WEIGHT = 0.25   # a row's score falls by this per cap its centre sits off the art line's
ROW_FILL_MIN = 0.3      # a row of type: its pieces' widths fill at least this share of its span

#: (slug, label, box x0, y0, x1, y1 in our frame, mm[, art height]) -- the
#: floor census's (`small_text_floor_census.ELEMENTS`) re-set lines of the
#: five pairs, each WHOLE: a line's words either side of a "+", a badge or a
#: bar are one line of type, and the pro re-lays it as one. Golden Tee's TM
#: is a row only (never traced by us: its height is given).
LINES = [
    ("proseal_hat", "SPRAY FOAM + COATINGS", (-36.5, 28.3, 35.6, 31.5)),
    ("proseal_beanie", "SPRAY FOAM + COATINGS", (-32.0, 24.7, 31.2, 27.6)),
    # the census's box less its first A, which traces in a thread of its own
    ("precision_drone", "AND DRONE", (-18.7, 24.0, 17.8, 26.5)),
    ("hotel_fremont_patch", "EST 1895", (-10.5, -14.8, 10.4, -12.9)),
    ("hotel_fremont_patch", "THE", (-5.0, -8.7, 5.0, -5.7)),
    ("hotel_fremont_patch", "EAT | STAY | PLAY", (-13.7, 10.2, 16.2, 12.8)),
    ("hotel_fremont_hat", "EST 1895", (-10.5, -14.8, 10.4, -12.9)),
    ("hotel_fremont_hat", "THE", (-5.0, -8.7, 5.0, -5.7)),
    ("hotel_fremont_hat", "EAT | STAY | PLAY", (-13.7, 10.2, 16.2, 12.8)),
    ("goldentee_hat", "TM", (24.5, 6.0, 30.5, 10.5), 0.86),
]

#: the design's big lettering, read in both files for the carry's scale
#: (box in our frame, drawn height)
REFS = {
    "proseal_hat": ((-41.3, 14.5, 39.3, 23.7), 9.22),
    "proseal_beanie": ((-36.1, 12.6, 34.3, 20.7), 8.05),
    "precision_drone": ((-31.1, 10.2, 31.2, 16.9), 5.99),
    "hotel_fremont_hat": ((-43.1, -3.6, 43.0, 3.5), 6.8),
    "hotel_fremont_patch": ((-43.1, -3.6, 43.0, 3.5), 6.8),
}


# ------------------------------------------------------------------ digitize
def digitize_main(argv) -> int:
    """`digitize`: ours.dst + ours.json + art.json + growth.json per SLUG."""
    import time
    from digitizer_core import small_text
    from tools import border_census as bc
    from tools import pro_pair as pp
    from tools import small_text_floor_census as stf
    ap = argparse.ArgumentParser(prog="reset_room_census digitize")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("slugs", nargs="+")
    args = ap.parse_args(argv)
    extra = {**RESET_SET, **pp.parse_sets(args.set)}
    known = {r[0] for r in bc.PAIRS}
    bc.PAIRS += [r for r in stf.EXTRA_PAIRS if r[0] not in known]
    bc.ART_FALLBACK.setdefault("goldentee", bc._T / "photo" / "logo_golden_tee.jpg")
    grow = small_text.enlarge_small_text
    for slug in args.slugs:
        row = next(r for r in bc.PAIRS if r[0] == slug)
        pro, art = bc.find_pair(*row[:3])
        if pro is None or art is None:
            raise SystemExit(f"{slug}: missing {'pro' if pro is None else 'art'} file")
        width = pp.pro_counts(pro)["width_mm"]
        seen: dict = {}

        def enlarge(regions, *a, **k):
            seen["art"] = [art_row(r) for r in regions]
            seen["growth"] = grow(regions, *a, **k)
            return seen["growth"]
        small_text.enlarge_small_text = enlarge
        try:
            t = time.time()
            d = pp.digitize(art, width, row[3], extra)
        finally:
            small_text.enlarge_small_text = grow
        out = Path(args.cache) / slug
        bc.write_ours(out, slug, row[3], width, pro, art, d.result, d.plan, time.time() - t)
        (out / "art.json").write_text(json.dumps(seen.get("art", [])), encoding="utf-8")
        (out / "growth.json").write_text(json.dumps({"set": extra, "report": seen.get("growth", [])},
                                                    default=str), encoding="utf-8")
        print(slug, width, round(time.time() - t), "s", flush=True)
    return 0


def art_row(r) -> dict:
    """One region as the art snapshot keeps it."""
    return {"id": getattr(r, "shape_id", None), "thread": r.thread_index,
            "cluster": r.meta.get("text_cluster_id"), "wkt": r.polygon.wkt}


# ------------------------------------------------------------------ geometry
def box_of(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def iou(a, b) -> float:
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def x_overlap(a, b) -> float:
    """Overlap of two boxes' x spans as a share of the narrower span."""
    o = min(a[2], b[2]) - max(a[0], b[0])
    return max(0.0, o) / max(min(a[2] - a[0], b[2] - b[0]), 1e-9)


def inside_share(b, outer) -> float:
    """Share of box `b`'s area inside box `outer`."""
    ix = min(b[2], outer[2]) - max(b[0], outer[0])
    iy = min(b[3], outer[3]) - max(b[1], outer[1])
    area = (b[2] - b[0]) * (b[3] - b[1])
    return 0.0 if ix <= 0 or iy <= 0 or area <= 0 else ix * iy / area


def line_frame(boxes) -> tuple:
    """A line's (x0, cap line, x1, baseline) from its letters' boxes: the x
    extremes, and the MEDIAN top and bottom of the letters at least
    `TALL_FRAC` of the tallest -- an O's overshoot or a joined pair's
    tail does not move a line."""
    hmax = max(b[3] - b[1] for b in boxes)
    tall = [b for b in boxes if b[3] - b[1] >= TALL_FRAC * hmax]
    return (min(b[0] for b in boxes), float(statistics.median(b[1] for b in tall)),
            max(b[2] for b in boxes), float(statistics.median(b[3] for b in tall)))


def move(art, sewn) -> dict:
    """A sewn line frame against the art's, both in our frame (`line_frame`;
    + dy is DOWN)."""
    h, w = sewn[3] - sewn[1], sewn[2] - sewn[0]
    return {"dx": round((sewn[0] + sewn[2] - art[0] - art[2]) / 2.0, 2),
            "dy": round((sewn[1] + sewn[3] - art[1] - art[3]) / 2.0, 2),
            "dy_top": round(sewn[1] - art[1], 2), "dy_bottom": round(sewn[3] - art[3], 2),
            "h": round(h, 2), "w": round(w, 2),
            "h_scale": round(h / max(art[3] - art[1], 1e-9), 3),
            "w_scale": round(w / max(art[2] - art[0], 1e-9), 3)}


def gaps(line_mask, other_mask, ppm: float = PPM) -> dict:
    """Free fabric above and below `line_mask` up to `other_mask` (boolean
    rasters of one window, y down), per column of the line's span: the
    distance from the line's outermost ink to the nearest other ink beyond
    it. -> {"up_min", "up_med", "down_min", "down_med", "up_cols",
    "down_cols", "cols"} (mm; None when no column has any)."""
    import numpy as np
    ups, downs = [], []
    cols = np.where(line_mask.any(axis=0))[0]
    for x in cols:
        ys = np.where(line_mask[:, x])[0]
        top, bot = int(ys.min()), int(ys.max())
        o = np.where(other_mask[:, x])[0]
        above, below = o[o < top], o[o > bot]
        if above.size:
            ups.append((top - int(above.max()) - 1) / ppm)
        if below.size:
            downs.append((int(below.min()) - bot - 1) / ppm)

    def st(v):
        return (round(min(v), 2), round(float(statistics.median(v)), 2)) if v else (None, None)
    (umin, umed), (dmin, dmed) = st(ups), st(downs)
    return {"up_min": umin, "up_med": umed, "down_min": dmin, "down_med": dmed,
            "up_cols": len(ups), "down_cols": len(downs), "cols": int(cols.size)}


def distance(a_mask, b_mask, ppm: float = PPM) -> float | None:
    """Nearest distance (mm) between two masks of one window, edge to edge."""
    import cv2
    import numpy as np
    if not a_mask.any() or not b_mask.any():
        return None
    if (a_mask & b_mask).any():
        return 0.0
    d = cv2.distanceTransform((~a_mask).astype(np.uint8), cv2.DIST_L2, 5)
    return round(max(0.0, float(d[b_mask].min()) - 1.0) / ppm, 2)


class Window:
    """A raster over a box of one frame, `PPM` px/mm."""

    def __init__(self, box, ppm: float = PPM):
        self.box, self.ppm = tuple(box), ppm
        self.w = int(math.ceil((box[2] - box[0]) * ppm)) + 1
        self.h = int(math.ceil((box[3] - box[1]) * ppm)) + 1

    def empty(self):
        import numpy as np
        return np.zeros((self.h, self.w), bool)

    def px(self, x, y):
        return int(round((x - self.box[0]) * self.ppm)), int(round((y - self.box[1]) * self.ppm))

    def polys(self, geoms):
        """Polygons (holes cut out) painted into a mask."""
        import cv2
        import numpy as np
        m = np.zeros((self.h, self.w), np.uint8)
        o = np.array(self.box[:2])
        for p in geoms:
            for g in (getattr(p, "geoms", None) or [p]):
                cv2.fillPoly(m, [np.round((np.asarray(g.exterior.coords)[:, :2] - o) * self.ppm).astype(np.int32)], 1)
                for ring in g.interiors:
                    cv2.fillPoly(m, [np.round((np.asarray(ring.coords)[:, :2] - o) * self.ppm).astype(np.int32)], 0)
        return m.astype(bool)

    def segs(self, segs):
        """Needle segments (x0, y0, x1, y1, ...) painted `THREAD_MM` wide."""
        import cv2
        import numpy as np
        m = np.zeros((self.h, self.w), np.uint8)
        th = max(1, int(round(THREAD_MM * self.ppm)))
        for s in segs:
            cv2.line(m, self.px(s[0], s[1]), self.px(s[2], s[3]), 1, th)
        return m.astype(bool)

    def comps(self, comps):
        """`components` rows (their own masks, same window) into one mask."""
        m = self.empty()
        for c in comps:
            q = c["mask"]
            m[c["oy"]:c["oy"] + q.shape[0], c["ox"]:c["ox"] + q.shape[1]] |= q
        return m


# ------------------------------------------------------------------ the art
def art_line(art: list[dict], box, art_h_mm: float | None = None):
    """The art shapes inside `box` (0.3 mm slack, over 0.02 mm2) -> (their
    indices, the line's frame, cap h); None when there are none and no
    height is given. A given height wins over the read one."""
    from shapely import wkt
    x0, y0, x1, y1 = box
    idx = []
    for i, r in enumerate(art):
        if "_poly" not in r:
            r["_poly"] = wkt.loads(r["wkt"])
        b = r["_poly"].bounds
        if b[0] >= x0 - 0.3 and b[2] <= x1 + 0.3 and b[1] >= y0 - 0.3 and b[3] <= y1 + 0.3 \
                and r["_poly"].area > 0.02:
            idx.append(i)
    if not idx:
        return ([], None, art_h_mm) if art_h_mm else None
    fr = line_frame([art[i]["_poly"].bounds for i in idx])
    return idx, fr, (art_h_mm or fr[3] - fr[1])


def art_neighbours(art: list[dict], line_idx, fr, cap: float) -> list[dict]:
    """Art shapes near the line (module docstring): `inline` in its band
    within `SIDE_CAPS` caps of its ends, `above` / `below` within
    `ABOVE_CAPS` caps over a quarter of its span; per role only those within
    a cap of the nearest. A ground (holding the line's centre, larger than
    the line) is not a neighbour. Sorted by role, then gap."""
    from shapely import wkt
    cx, cy = (fr[0] + fr[2]) / 2.0, (fr[1] + fr[3]) / 2.0
    taken = set(line_idx)
    cand = []
    for i, r in enumerate(art):
        if i in taken:
            continue
        if "_poly" not in r:
            r["_poly"] = wkt.loads(r["wkt"])
        p = r["_poly"]
        if p.area < MIN_SHAPE_MM2:
            continue
        b = p.bounds
        if b[0] <= cx <= b[2] and b[1] <= cy <= b[3] and p.area > (fr[2] - fr[0]) * (fr[3] - fr[1]):
            continue
        band = min(b[3], fr[3]) - max(b[1], fr[1]) >= 0.5 * min(b[3] - b[1], fr[3] - fr[1])
        if band and fr[0] - SIDE_CAPS * cap <= b[2] and b[0] <= fr[2] + SIDE_CAPS * cap:
            role, gap = "inline", max(fr[0] - b[2], b[0] - fr[2], 0.0)
        elif x_overlap(b, fr) >= 0.25 or (fr[0] <= b[0] and b[2] <= fr[2]):
            if b[3] <= fr[1] + 0.25 * cap and fr[1] - b[3] <= ABOVE_CAPS * cap:
                role, gap = "above", fr[1] - b[3]
            elif b[1] >= fr[3] - 0.25 * cap and b[1] - fr[3] <= ABOVE_CAPS * cap:
                role, gap = "below", b[1] - fr[3]
            else:
                continue
        else:
            continue
        cand.append({"i": i, "role": role, "gap": round(gap, 2), "box": [round(v, 2) for v in b],
                     "c": [round(p.centroid.x, 3), round(p.centroid.y, 3)],
                     "thread": r.get("thread"), "bar": (b[2] - b[0]) >= 3.0 * (b[3] - b[1]),
                     "area": round(p.area, 2)})
    near = {}
    for n in cand:
        near[n["role"]] = min(near.get(n["role"], math.inf), n["gap"])
    out = [n for n in cand if n["role"] == "inline" or n["gap"] <= near[n["role"]] + cap]
    out.sort(key=lambda n: ({"above": 0, "inline": 1, "below": 2}[n["role"]], n["gap"]))
    return out


# ------------------------------------------------------------------ a file
def components(runs, win: Window) -> list[dict]:
    """Every thread component in `win`, block by block: needle-down segments
    painted `THREAD_MM` wide, a non-satin, non-bean stitch over the census's
    `TRAVEL_MM` left out (`small_text_floor_census.components`' painting).
    -> [{"block", "box" (painted, mm, this frame), "mask", "ox", "oy"}]."""
    import cv2
    import numpy as np
    from tools import small_text_floor_census as stf
    x0, y0 = win.box[:2]
    th = max(1, int(round(THREAD_MM * win.ppm)))
    out = []
    for blk, segs in stf._segments(runs, win.box).items():
        kinds = stf.seg_kinds(runs, segs)
        img = np.zeros((win.h, win.w), np.uint8)
        for s, k in zip(segs, kinds):
            if k == "other" and stf._seg_len(s) > stf.TRAVEL_MM:
                continue
            cv2.line(img, win.px(s[0], s[1]), win.px(s[2], s[3]), 255, th)
        n, lab, st, _c = cv2.connectedComponentsWithStats(img, 8)
        for i in range(1, n):
            cx, cy, cw, ch, _area = (int(v) for v in st[i])
            out.append({"block": blk, "box": (cx / win.ppm + x0, cy / win.ppm + y0,
                                              (cx + cw) / win.ppm + x0, (cy + ch) / win.ppm + y0),
                        "mask": lab[cy:cy + ch, cx:cx + cw] == i, "ox": cx, "oy": cy})
    return out


def rows_of(comps) -> list[list]:
    """Letter boxes grouped into rows of type: a box joins the first row
    whose median centre lies within 0.35 of the taller one's height and
    whose median height is 0.5-2x its own."""
    rows: list[list] = []
    for b in sorted(comps, key=lambda b: (b[1] + b[3]) / 2.0):
        cy, h = (b[1] + b[3]) / 2.0, b[3] - b[1]
        for r in rows:
            rc = statistics.median((q[1] + q[3]) / 2.0 for q in r)
            rh = statistics.median(q[3] - q[1] for q in r)
            if abs(rc - cy) <= 0.35 * max(rh, h) and 0.5 <= h / rh <= 2.0:
                r.append(b)
                break
        else:
            rows.append([b])
    return rows


def letter_pieces(segs, kinds, box, art_h: float, open_mm: float):
    """`small_text_floor_census.components`' painting and filter (not
    touching the box edge, at least 0.3 x the art height tall), with no
    centre reach -- the pro MOVES lines -- and the paint first OPENED by
    `open_mm`: letters the pro joins through short travel (Fremont's EST
    1895, Drone's AND DRONE, joined to a dash or to the patch's field) part
    there, as `small_text_columns.pieces` parts them. A piece's box is its
    opened extent. -> ([painted boxes], [indices of segments inside them])."""
    import cv2
    import numpy as np
    from tools import small_text_floor_census as stf
    win = Window(box)
    img = np.zeros((win.h, win.w), np.uint8)
    th = max(1, int(round(THREAD_MM * win.ppm)))
    painted = [j for j, (s, k) in enumerate(zip(segs, kinds)) if k != "other" or stf._seg_len(s) <= stf.TRAVEL_MM]
    for j in painted:
        s = segs[j]
        cv2.line(img, win.px(s[0], s[1]), win.px(s[2], s[3]), 255, th)
    if open_mm > 0:
        k = int(round(open_mm * win.ppm)) | 1
        img = cv2.morphologyEx(img, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, st, _c = cv2.connectedComponentsWithStats(img, 8)
    keep = {}
    for i in range(1, n):
        x, y, w, h, _a = (int(v) for v in st[i])
        if x <= 0 or y <= 0 or x + w >= win.w - 1 or y + h >= win.h - 1 or h / win.ppm < 0.3 * art_h:
            continue
        keep[i] = (x / win.ppm + box[0], y / win.ppm + box[1], (x + w) / win.ppm + box[0], (y + h) / win.ppm + box[1])
    idx = []
    for j in painted:
        s = segs[j]
        mx, my = win.px(0.5 * (s[0] + s[2]), 0.5 * (s[1] + s[3]))
        if 0 <= my < win.h and 0 <= mx < win.w and lab[my, mx] in keep:
            idx.append(j)
    return list(keep.values()), idx


def sewn_line(runs, box, art_fr, art_h: float) -> dict | None:
    """The line in a machine file, searched in `box` (this file's frame):
    every colour block's letter pieces (`letter_pieces`), grouped into rows
    (`rows_of`). The row that covers most of the art line's x span --
    `art_fr` carried into this frame -- weighted by its height up to the
    art's and down by how far it sits from the art line (`ROW_OFF_WEIGHT`
    per cap: a moved line still wins, a word of the next line down does
    not), is the line; at least `MIN_COVER` of the span. Read twice, as
    painted and opened by `OPEN_MM`, and the opened row is taken unless
    its score is under `OPENED_KEEP` of the plain one's: opening parts
    letters joined through travel (the pro's Fremont EST 1895, Drone's E
    joined to the dash after it), and loses a run-stitched mark or a letter
    grown into a bar of its own thread, which the plain read keeps (our
    re-set THE on the Fremont patch). -> {"block", "comps" (painted boxes),
    "segs" (the segments in them), "frame" (needle extents, `line_frame`),
    "opened"} or None."""
    plain = _best_row(runs, box, art_fr, art_h, 0.0)
    opened = _best_row(runs, box, art_fr, art_h, OPEN_MM)
    if opened is not None and (plain is None or opened["score"] >= OPENED_KEEP * plain["score"]):
        return {**opened, "opened": True}
    return None if plain is None else {**plain, "opened": False}


def _inside(seg, b) -> bool:
    return b[0] <= 0.5 * (seg[0] + seg[2]) <= b[2] and b[1] <= 0.5 * (seg[1] + seg[3]) <= b[3]


def _best_row(runs, box, art_fr, art_h, open_mm):
    """`sewn_line`'s pick for one read. The row is one block's; a piece of
    ANOTHER block in the row's band, 0.6-1.4x its median height and within
    two caps of its span, joins it -- a letter traced in a thread of its own
    (Drone's first A, ProSeal's A of SPRAY) is still a letter of the line."""
    from tools import small_text_floor_census as stf
    pieces = {}
    for blk, segs in stf._segments(runs, box).items():
        kinds = stf.seg_kinds(runs, segs)
        comps, idx = letter_pieces(segs, kinds, box, art_h, open_mm)
        pieces[blk] = (comps, [segs[j] for j in idx])
    best = None
    for blk, (comps, segs) in pieces.items():
        for row in rows_of(comps):
            fr = line_frame(row)
            if sum(b[2] - b[0] for b in row) < ROW_FILL_MIN * (fr[2] - fr[0]):
                continue            # pieces strewn along a span (a rope's twists), not type
            cover = max(0.0, min(fr[2], art_fr[2]) - max(fr[0], art_fr[0])) / max(art_fr[2] - art_fr[0], 1e-9)
            off = abs((fr[1] + fr[3]) - (art_fr[1] + art_fr[3])) / 2.0
            score = cover * min(1.0, (fr[3] - fr[1]) / max(art_h, 1e-9)) / (1.0 + ROW_OFF_WEIGHT * off / art_h)
            if cover >= MIN_COVER and (best is None or score > best[0]):
                best = (score, blk, row, fr)
    if best is None:
        return None
    score, blk, row, fr = best
    h = statistics.median(b[3] - b[1] for b in row)
    cy = (fr[1] + fr[3]) / 2.0
    row = list(row)
    for blk2, (comps, _segs) in pieces.items():
        if blk2 == blk:
            continue
        for b in comps:
            if (0.6 * h <= b[3] - b[1] <= 1.4 * h and abs((b[1] + b[3]) / 2.0 - cy) <= 0.35 * h
                    and fr[0] - 2.0 * h <= b[0] and b[2] <= fr[2] + 2.0 * h):
                row.append(b)
    fr = line_frame(row)
    inside = [s for comps, segs in pieces.values() for s in segs if any(_inside(s, b) for b in row)]
    half = THREAD_MM / 2.0
    return {"block": blk, "comps": row, "segs": inside, "score": score,
            "frame": (fr[0] + half, fr[1] + half, fr[2] - half, fr[3] - half)}


def match(art_box, block_masks: dict, win: Window, carry, uncarry, art_c=None) -> dict | None:
    """An art neighbour's counterpart in a file (module docstring). Each
    block's thread (the line's own letters already left out) is clipped to
    `art_box` grown by a quarter of its short side (at least
    `MATCH_GROW_MM`), carried into the file's frame by `uncarry`; of the
    pieces left, one the clip CUT that lies mostly (half its box) outside
    `art_box` and covers under a quarter of it is a sliver of something
    else and is dropped. The block whose pieces' union box, carried back by
    `carry` and less half the thread each side, overlaps `art_box` best --
    at least `NEIGHBOUR_IOU` -- is the counterpart. A piece connected to
    other thread of its block (a bar sewn on with a frame) is read by its
    clip, not by its component. dy: its thread's centroid against `art_c`
    (the art shape's centroid; its box's centre when None); dx, dw, dh:
    its box's against the art's.
    -> {"mask" (this window), "block", "iou", "box", "dx", "dy", "dw", "dh"}
    or None."""
    import cv2
    import numpy as np
    g = max(MATCH_GROW_MM, 0.25 * min(art_box[2] - art_box[0], art_box[3] - art_box[1]))
    grown = uncarry((art_box[0] - g, art_box[1] - g, art_box[2] + g, art_box[3] + g))
    gx0, gy0 = win.px(grown[0], grown[1])
    gx1, gy1 = win.px(grown[2], grown[3])
    gx0, gy0, gx1, gy1 = max(0, gx0), max(0, gy0), min(win.w, gx1 + 1), min(win.h, gy1 + 1)
    if gx1 - gx0 < 2 or gy1 - gy0 < 2:
        return None
    half = THREAD_MM / 2.0
    best = None
    for blk, M in block_masks.items():
        sub = M[gy0:gy1, gx0:gx1]
        if not sub.any():
            continue
        n, lab, st, _c = cv2.connectedComponentsWithStats(sub.astype(np.uint8), 8)
        keep, boxes = np.zeros_like(sub), []
        for i in range(1, n):
            x, y, w, h, _a = (int(v) for v in st[i])
            b = carry((win.box[0] + (gx0 + x) / win.ppm, win.box[1] + (gy0 + y) / win.ppm,
                       win.box[0] + (gx0 + x + w) / win.ppm, win.box[1] + (gy0 + y + h) / win.ppm))
            cut = x == 0 or y == 0 or x + w >= sub.shape[1] or y + h >= sub.shape[0]
            if cut and inside_share(b, art_box) < 0.5 and inside_share(art_box, b) < 0.25:
                continue
            keep |= lab == i
            boxes.append(b)
        if not boxes:
            continue
        u = box_of(boxes)
        u = (u[0] + half, u[1] + half, u[2] - half, u[3] - half)
        v = iou(art_box, u)
        if v >= NEIGHBOUR_IOU and (best is None or v > best[0]):
            mask = win.empty()
            mask[gy0:gy1, gx0:gx1] = keep
            best = (v, blk, u, mask)
    if best is None:
        return None
    v, blk, b, mask = best
    # dy is the thread's centroid against the art shape's: a stub of other
    # thread the clip let in barely moves it, where it moves a box. dx is the
    # box's: along a long bar the centroid follows where the thread is
    # densest, not where the bar is
    ys, _xs = np.nonzero(mask)
    c = carry((win.box[0], win.box[1] + ys.mean() / win.ppm) * 2)
    acy = art_c[1] if art_c else (art_box[1] + art_box[3]) / 2.0
    return {"mask": mask, "block": blk, "iou": round(v, 2), "box": [round(q, 2) for q in b],
            "dx": round((b[0] + b[2] - art_box[0] - art_box[2]) / 2.0, 2), "dy": round(c[1] - acy, 2),
            "dw": round((b[2] - b[0]) - (art_box[2] - art_box[0]), 2),
            "dh": round((b[3] - b[1]) - (art_box[3] - art_box[1]), 2)}


def room(win: Window, line_mask, neighbours: list[dict], masks: list) -> dict:
    """The free fabric from the line to its neighbours, one file: `gaps`
    against the union of the `above` and of the `below` neighbours' masks,
    and each `inline` neighbour's `distance`. `masks[k]` is neighbour k's
    mask in this window (None: not found)."""
    import numpy as np
    out = {}
    for role in ("above", "below"):
        ms = [m for n, m in zip(neighbours, masks) if n["role"] == role and m is not None]
        if ms:
            g = gaps(line_mask, np.logical_or.reduce(ms), win.ppm)
            key = "up" if role == "above" else "down"
            out[f"{key}_min"], out[f"{key}_med"] = g[f"{key}_min"], g[f"{key}_med"]
    out["inline"] = [None if m is None else distance(line_mask, m, win.ppm)
                     for n, m in zip(neighbours, masks) if n["role"] == "inline"]
    return out


# ------------------------------------------------------------------ carry
def _raster(runs, bb, ppm, scale=1.0, shift=(0.0, 0.0)):
    """Needle-down thread (0.4 mm wide, a stitch over 3 mm left out) of
    `runs` carried by p -> scale * p + shift, on `bb` at `ppm`."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = bb
    img = np.zeros((int((y1 - y0) * ppm) + 1, int((x1 - x0) * ppm) + 1), np.uint8)
    for r in runs:
        p = np.asarray(r["pts"], float)
        if len(p) < 2:
            continue
        p = p * scale + shift
        q = np.round((p - (x0, y0)) * ppm).astype(np.int32)
        seg = np.hypot(*np.diff(p, axis=0).T)
        start = 0
        for k in np.where(seg > 3.0)[0].tolist() + [len(p) - 1]:
            if k + 1 - start >= 2:
                cv2.polylines(img, [q[start:k + 1]], False, 1, max(1, int(round(0.4 * ppm))))
            start = k + 1
    return img.astype(bool)


def _iou_masks(a, b) -> float:
    import numpy as np
    union = np.count_nonzero(a | b)
    return np.count_nonzero(a & b) / union if union else 0.0


def ref_scale(slug: str, pro_runs, ours_runs, reg) -> float | None:
    """His big lettering's needle width over ours (`REFS`), or None."""
    from tools import small_text_floor_census as stf
    if slug not in REFS:
        return None
    box, h = REFS[slug]
    m_x, m_y = 3.0, 2.5
    ob = (box[0] - m_x, box[1] - m_y, box[2] + m_x, box[3] + m_y)
    eo = stf.read_element(ours_runs, ob, h, 0.5 * (box[1] + box[3]))
    pb = stf._map_box(box, reg, m_x * reg.scale, m_y * reg.scale)
    ep = stf.read_element(pro_runs, pb, h * reg.scale, reg.scale * 0.5 * (box[1] + box[3]) + reg.dy)
    if not eo.get("w_mm") or not ep.get("w_mm"):
        return None
    return (ep["w_mm"] - THREAD_MM) / (eo["w_mm"] - THREAD_MM)


def register(slug, pro_path, ours_path, pro_runs, ours_runs):
    """Our frame carried into the pro's (module docstring, `carry`).
    -> (pairframe.Reg, where the scale came from)."""
    import numpy as np
    from tools import small_text_floor_census as stf
    from tools.pro_parity import pairframe as pf
    reg = stf.register(Path(pro_path), Path(ours_path))
    s = ref_scale(slug, pro_runs, ours_runs, reg)
    src = "ref"
    if s is None or abs(s - reg.scale) > 0.08:
        s, src = reg.scale, "extent"
    pts = np.array([q for r in pro_runs for q in r["pts"]])
    bb = (pts[:, 0].min() - 4, pts[:, 1].min() - 4, pts[:, 0].max() + 4, pts[:, 1].max() + 4)
    opts = np.array([q for r in ours_runs for q in r["pts"]])
    oc = (opts.min(0) + opts.max(0)) / 2.0
    d = reg.scale * oc + (reg.dx, reg.dy) - s * oc      # our centre where the census put it
    best = (float(d[0]), float(d[1]), -1.0)
    for ppm, span, step in ((2.0, 2.0, 0.5), (10.0, 0.4, 0.1)):
        pm = _raster(pro_runs, bb, ppm)
        om = _raster(ours_runs, bb, ppm, scale=s, shift=(best[0], best[1]))
        bx, by = best[0], best[1]
        n = int(round(span / step))
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                v = _iou_masks(np.roll(om, (int(round(j * step * ppm)), int(round(i * step * ppm))),
                                       axis=(0, 1)), pm)
                if v > best[2]:
                    best = (bx + i * step, by + j * step, v)
    return pf.Reg(scale=round(float(s), 4), flip_y=False, dx=round(best[0], 3), dy=round(best[1], 3),
                  iou=round(best[2], 4)), src


def to_ours(b, reg):
    """A box in the pro's frame -> ours (the inverse of `reg`)."""
    s = reg.scale
    return ((b[0] - reg.dx) / s, (b[1] - reg.dy) / s, (b[2] - reg.dx) / s, (b[3] - reg.dy) / s)


def to_pro(b, reg):
    s = reg.scale
    return (s * b[0] + reg.dx, s * b[1] + reg.dy, s * b[2] + reg.dx, s * b[3] + reg.dy)


# ------------------------------------------------------------------ census
def read_side(runs, win: Window, sbox, art_h, carry, uncarry, art_fr, neighbours, debug=None) -> dict:
    """One machine file: the line (`sewn_line`), its move against the art,
    each art neighbour's counterpart (`match`) and the room (`room`).
    `win` / `sbox` are in THIS file's frame; `carry` maps a box of it into
    ours, `uncarry` back; `art_fr` is the art line's frame (ours) or, for a
    line we never trace, its search box. `debug`: a path, the window drawn
    there (line red, matched neighbours blue, other thread grey)."""
    import numpy as np
    ln = sewn_line(runs, sbox, uncarry(art_fr), art_h)
    if ln is None:
        return {"read": "DROPPED"}
    out = {"read": {"block": ln["block"], "letters": len(ln["comps"])}}
    line_mask = win.segs(ln["segs"])
    ofr = carry(ln["frame"])
    out["frame"] = [round(v, 2) for v in ofr]
    if neighbours is not None:
        out["move"] = move(art_fr, ofr)
    comps = components(runs, win)
    blocks: dict = {}
    for c in comps:
        blocks.setdefault(c["block"], []).append(c)
    block_masks = {b: win.comps(cs) & ~line_mask for b, cs in blocks.items()}
    ms = [match(tuple(n["box"]), block_masks, win, carry, uncarry, n.get("c")) for n in (neighbours or [])]
    out["neighbours"] = [None if m is None else {k: v for k, v in m.items() if k != "mask"} for m in ms]
    out["room"] = room(win, line_mask, neighbours or [], [None if m is None else m["mask"] for m in ms])
    if debug:
        import cv2
        img = np.full((win.h, win.w, 3), 255, np.uint8)
        for M in block_masks.values():
            img[M] = (190, 190, 190)
        for m in ms:
            if m is not None:
                img[m["mask"]] = (200, 90, 0)
        img[line_mask] = (0, 0, 210)
        for b, col in [(uncarry(art_fr), (0, 160, 0))] + [(uncarry(tuple(n["box"])), (0, 120, 220))
                                                          for n in (neighbours or [])]:
            cv2.rectangle(img, win.px(b[0], b[1]), win.px(b[2], b[3]), col, 1)
        cv2.imwrite(str(debug), img)
    return out


def search_box(box, art_h: float):
    """Where a file's line is looked for: the art box grown 1 + 2.5 caps up
    and down (the pro moved Fremont's EST 1895 ~2 mm, ours 3.3) and
    2 + 0.5 cap + a quarter of the line sideways (he spreads the ProSeal
    beanie's tagline ~5 mm past the art's ends, EST 1895 ~3 mm each side).
    Anything touching its edge is not a letter of the line
    (`letter_pieces`)."""
    m_y = 1.0 + 2.5 * art_h
    m_x = 2.0 + 0.5 * art_h + 0.25 * (box[2] - box[0])
    return (box[0] - m_x, box[1] - m_y, box[2] + m_x, box[3] + m_y)


def census(caches: list[Path], lines=LINES, only=None, debug: Path | None = None) -> list[dict]:
    """Every line of `lines` whose slug has a cache (the first of `caches`
    holding its art.json) -> rows (module docstring)."""
    from tools import small_text_floor_census as stf
    from tools.study_pro import load_runs
    rows = []
    loaded: dict = {}
    for slug, label, box, *art_h_mm in lines:
        if only and slug not in only:
            continue
        base = next((c / slug for c in caches if (c / slug / "art.json").exists()), None)
        if base is None:
            continue
        if slug not in loaded:
            info = json.loads((base / "ours.json").read_text(encoding="utf-8"))
            pro = stf._local(info["pro"])
            pro_runs, ours_runs = load_runs(pro)[0], load_runs(base / "ours.dst")[0]
            loaded[slug] = {
                "info": info, "pro_runs": pro_runs, "ours_runs": ours_runs,
                "art": json.loads((base / "art.json").read_text(encoding="utf-8")),
                "growth": json.loads((base / "growth.json").read_text(encoding="utf-8")),
                "reg": register(slug, pro, base / "ours.dst", pro_runs, ours_runs)}
        L = loaded[slug]
        al = art_line(L["art"], box, art_h_mm[0] if art_h_mm else None)
        if al is None:
            continue
        idx, fr, art_h = al
        nbrs = art_neighbours(L["art"], idx, fr, art_h) if idx else None
        sbox = search_box(box, art_h)
        span = [sbox, *[n["box"] for n in nbrs or []]]
        win_box = (min(b[0] for b in span) - 1.0, min(b[1] for b in span) - 1.0,
                   max(b[2] for b in span) + 1.0, max(b[3] for b in span) + 1.0)
        reg, src = L["reg"]
        row = {"slug": slug, "label": label, "width_mm": L["info"]["width_mm"],
               "art": {"frame": None if fr is None else [round(v, 2) for v in fr], "h": round(art_h, 2),
                       "w": None if fr is None else round(fr[2] - fr[0], 2)},
               "neighbours": [{k: v for k, v in n.items() if k != "i"} for n in nbrs or []],
               "reg": {**reg.as_dict(), "scale_from": src}, "box": [round(v, 2) for v in win_box],
               "pro_box": [round(v, 2) for v in to_pro(win_box, reg)]}
        if idx:
            aw = Window(win_box)
            row["art"]["room"] = room(aw, aw.polys([L["art"][i]["_poly"] for i in idx]), nbrs,
                                      [aw.polys([L["art"][n["i"]]["_poly"]]) for n in nbrs])
        name = None if debug is None else f"{slug}_{''.join(ch if ch.isalnum() else '_' for ch in label)}"
        if debug is not None:
            debug.mkdir(parents=True, exist_ok=True)
        row["ours"] = read_side(L["ours_runs"], Window(win_box), sbox, art_h,
                                lambda b: b, lambda b: b, fr or box, nbrs,
                                None if name is None else debug / f"{name}_ours.png")
        row["pro"] = read_side(L["pro_runs"], Window(to_pro(win_box, reg)), to_pro(sbox, reg),
                               art_h * reg.scale,
                               lambda b, reg=reg: to_ours(b, reg), lambda b, reg=reg: to_pro(b, reg),
                               fr or box, nbrs, None if name is None else debug / f"{name}_pro.png")
        clusters = {L["art"][i].get("cluster") for i in idx} - {None}
        row["growth"] = [{k: v for k, v in g.items() if k in (
            "cluster", "cap_mm", "scale", "width_scale", "shift_mm", "skipped", "blocked_by", "joined",
            "merged_into", "bars", "bar_moves", "widened_mm")}
            for g in L["growth"]["report"] if g.get("cluster") in clusters]
        rows.append(row)
    return rows


# ------------------------------------------------------------------ report
def _f(v) -> str:
    return "-" if v is None else f"{v}"


def _growth_cell(gs) -> str:
    out = []
    for g in gs:
        if "scale" in g:
            out.append(f"x{g['scale']} w{g.get('width_scale')} shift {g.get('shift_mm')}")
        elif g.get("merged_into"):
            out.append("merged")
        else:
            out.append(f"{g.get('skipped')} {g.get('blocked_by') or ''}".strip())
    return "; ".join(out)


def table(rows) -> str:
    """The moves and the room, three rows per line of text: art, ours, pro."""
    lines = ["| job | line | side | h (x art) | w (x art) | dy cap / centre / base | dx "
             "| room up min / med | room down min / med | inline | ours' re-set |",
             "|" + "---|" * 11]
    for r in rows:
        a, ar = r["art"], r["art"].get("room") or {}
        lines.append(f"| {r['slug']} | {r['label']} | art | {a['h']} | {_f(a['w'])} | | | "
                     f"{_f(ar.get('up_min'))} / {_f(ar.get('up_med'))} | "
                     f"{_f(ar.get('down_min'))} / {_f(ar.get('down_med'))} | {_f(ar.get('inline'))} | |")
        for side in ("ours", "pro"):
            s = r.get(side) or {}
            mv, rm = s.get("move"), s.get("room") or {}
            g = _growth_cell(r.get("growth", [])) if side == "ours" else ""
            if mv is None:
                fr = s.get("frame")
                what = "DROPPED" if fr is None else f"{round(fr[3] - fr[1], 2)} at {fr}"
                lines.append(f"| | | {side} | {what} | | | | | | | {g} |")
                continue
            lines.append(
                f"| | | {side} | {mv['h']} (x{mv['h_scale']}) | {mv['w']} (x{mv['w_scale']}) | "
                f"{mv['dy_top']:+.2f} / {mv['dy']:+.2f} / {mv['dy_bottom']:+.2f} | {mv['dx']:+.2f} | "
                f"{_f(rm.get('up_min'))} / {_f(rm.get('up_med'))} | "
                f"{_f(rm.get('down_min'))} / {_f(rm.get('down_med'))} | {_f(rm.get('inline'))} | {g} |")
    return "\n".join(lines)


def neighbour_table(rows) -> str:
    """What each file did with the shapes around each line: per role, how
    many art shapes and how many each file still sews there (`match`), then
    one row per bar, inline shape or shape of at least half a cap squared
    (a rope's twists and a word's letters are counted, not listed)."""
    lines = ["| job | line | neighbour: role, art box mm | art gap | ours dx / dy / dw / dh | "
             "pro dx / dy / dw / dh |", "|---|---|---|---|---|---|"]

    def cell(m):
        return "not found" if m is None else \
            f"{m['dx']:+.2f} / {m['dy']:+.2f} / {m['dw']:+.2f} / {m['dh']:+.2f} (IoU {m['iou']})"
    for r in rows:
        ms = {s: (r.get(s) or {}).get("neighbours") or [None] * len(r["neighbours"]) for s in ("ours", "pro")}
        cap = r["art"]["h"]
        for role in ("above", "inline", "below"):
            ks = [k for k, n in enumerate(r["neighbours"]) if n["role"] == role]
            if not ks:
                continue
            found = {s: sum(ms[s][k] is not None for k in ks) for s in ms}
            lines.append(f"| {r['slug']} | {r['label']} | {role}: {len(ks)} shapes | "
                         f"{min(r['neighbours'][k]['gap'] for k in ks)} | {found['ours']} found | "
                         f"{found['pro']} found |")
            for k in ks:
                n = r["neighbours"][k]
                if n["bar"] or role == "inline" or n["area"] >= 0.5 * cap * cap:
                    tag = "bar " if n["bar"] else ""
                    lines.append(f"| | | {tag}{n['box']} | {n['gap']} | {cell(ms['ours'][k])} | "
                                 f"{cell(ms['pro'][k])} |")
    return "\n".join(lines)


def crop_box(r) -> tuple | None:
    """Our-frame box a crop shows: the art line's, our and the pro's frames
    together, 1.5 caps up and down (where the room is) and 2 mm sideways."""
    frs = [r["art"].get("frame")] + [(r.get(s) or {}).get("frame") for s in ("ours", "pro")]
    frs = [f for f in frs if f]
    if not frs:
        return None
    b = box_of(frs)
    m = max(1.5 * r["art"]["h"], 2.0)
    return (b[0] - 2.0, b[1] - m, b[2] + 2.0, b[3] + m)


def crops(rows, caches: list[Path], out: Path) -> None:
    """art | ours | pro around each line (`crop_box`), each in its own frame
    (`small_text_floor_census.crops`, one arm)."""
    from tools import small_text_floor_census as stf
    from tools.pro_parity.pairframe import Reg
    by_slug: dict = {}
    for r in rows:
        b = crop_box(r)
        if b is None:
            continue
        reg = Reg(**{k: v for k, v in r["reg"].items() if k != "scale_from"})
        by_slug.setdefault(r["slug"], []).append({**r, "box": list(b), "pro_box": list(to_pro(b, reg))})
    for slug, rs in by_slug.items():
        base = next(c for c in caches if (c / slug / "ours.json").exists())
        stf.crops(rs, {"ours": base}, out)


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["digitize"]:
        return digitize_main(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cache", action="append", required=True,
                    help="`digitize`'s cache(s), searched in order")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--crops", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--debug", default=None, help="draw each file's reading of each line here")
    args = ap.parse_args(argv)
    caches = [Path(c) for c in args.cache]
    rows = census(caches, only=args.only or None, debug=Path(args.debug) if args.debug else None)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    print(table(rows))
    print()
    print(neighbour_table(rows))
    if args.crops:
        crops(rows, caches, Path(args.crops))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
