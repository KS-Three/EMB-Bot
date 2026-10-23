#!/usr/bin/env python
"""border_census: where WE sew a satin border and the PRO does not (and back).

Over every logo that has both the customer's art and a professional's stitch
file (the 15 designs of docs/pro-parity-real-art-2026-08-15.md section 2, plus
ProSeal's hat), digitize the art at the pro's width with the matching Studio
preset, then ask the SAME question of both stitch files for every closed shape
of our segmentation: is there a satin column riding the shape's outline?

One detector for both sides, so the comparison is a measurement and not two
dialects. Both files are read as machine stitches (ours is written to DST
first and read back), satin phases come from `census_pro._phases` through
`border_pro.columns`, and each is painted into a 0.1 mm mask:

  band  = fraction of the shape's outline (outer and hole rings) lying on satin
  core  = satin share of the shape's interior further from the edge than the
          column width found along that edge (the part a ring leaves alone)
  class = BORDER  a satin column whose SPINE is a closed loop that follows the
                  shape's outline (mean spine distance to the outline within
                  half a column width + 0.5 mm, spanning the shape)
          OUTLINE the same with a run / bean loop (the first lap of a needle-down
                  run that returns to its start, round, hugging the outline)
          BORDER  also: satin rides >= 60% of the outline in open half-columns and
                  the centre of the shape (dist >= 0.8 x inradius) is < 35% satin
          SATIN   band >= 0.60 without either (a column, a bar, a letter)
          FILL    some other stitch coverage of the interior >= 0.50
          RUN     the outline carries stitches but the interior does not
          NONE    nothing sewn there (covered by a neighbour, or left bare)

Row classes (shapes of >= 1.0 mm2 only):
  a "ring" is BORDER (a satin loop) or OUTLINE (a run / bean loop):
  (a) ours rings, pro does not     (b) pro rings, ours does not
  (c) both ring, but of a different kind or satin widths differ by >= 0.4 mm

Shapes are OUR segmentation's, mapped into the pro's frame by the same
registration the pro-parity harness uses (`pairframe.register_pair`). A pro
ring that rides an outline our segmentation does not have shows as a (b) row
on whichever of our shapes it crosses: read the crop before trusting a row.

  python tools/border_census.py run [--only SLUG ...] [--jobs 3]  # digitize + analyse
  python tools/border_census.py table                             # re-analyse the cache
  python tools/border_census.py one SLUG                          # digitize one (cache)

The cache is `--cache` (default digitizer/debug_out/border_census). Art and pro
files are found under PRO_PARITY_ROOT, then G:/My Drive/EMB-Bot/Embroidery
Files, then the primary checkout's scratch_kent/Embroidery Files; the committed
fixtures stand in for art the Drive lacks. Nothing client-owned is written
outside the cache except the doc table and small crops.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools._console import utf8_console  # noqa: E402

RES = 10.0              # mask pixels per mm
MIN_AREA_MM2 = 1.0      # shapes smaller than this are not listed
BAND_MIN = 0.60         # outline share on satin that makes a ring

RUN_WIDTH_MM = 0.4      # what a run loop's tolerance assumes of its thread
CORE_SATIN_MAX = 0.35   # a centre this satin belongs to one column, not a ring
LOOP_GAP_MM = 1.0       # a ring's spine ends meet within this
LOOP_ROUND_MIN = 0.25   # 4 pi A / L^2 of the spine: a line ~0, a hexagon 0.9
RING = ("BORDER", "OUTLINE")
WIDTH_DIFF_MM = 0.4     # (c) rows
SATIN_PAINT_MM = 0.5    # a chord is painted this thick so a column is solid
OUT_DOC = DIGITIZER.parent / "docs" / "border-census-2026-10-23.md"
OUT_CROPS = DIGITIZER.parent / "docs" / "renders" / "border-census-2026-10-23"

#: (slug, pro file, customer art, garment_id) -- prep_both.DESIGNS' rows, with
#: ProSeal added. Paths are relative to the Embroidery Files root.
PAIRS = [
    ("becker_hat_large", "Becker Marine/Becker Hat & Polo Large/beckers logo hat.PES",
     "Becker Marine/Becker Marine Logo.png", "hat_front"),
    ("becker_lc_large", "Becker Marine/Becker Hat & Polo Large/beckers logolc.PES",
     "Becker Marine/Becker Marine Logo.png", "left_chest"),
    ("becker_hat_small", "Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.PES",
     "Becker Marine/Becker Marine Logo.png", "hat_front"),
    ("becker_chest_small", "Becker Marine/Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.PES",
     "Becker Marine/Becker Marine Logo.png", "left_chest"),
    ("becker_beanie", "To a T_Becker Beanies/beckers logo hat 2 A a.PES",
     "Becker Marine/Becker Marine Logo.png", "beanie"),
    ("gaulke_roofing_hat", "Gaulke Roofing/c golke logo hat.DST",
     "Gaulke Roofing/Gaulke Roofing Logo.png", "hat_front"),
    ("gaulke_roofing_lc", "Gaulke Roofing/c golke logo LC.DST",
     "Gaulke Roofing/Gaulke Roofing Logo.png", "left_chest"),
    ("hotel_fremont_hat", "Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES",
     "Hotel Fremont/Hotel Fremont Logo.webp", "hat_front"),
    ("hotel_fremont_patch", "Hotel Fremont/Hotel Patch/HOTEL FREMONT .PES",
     "Hotel Fremont/Hotel Fremont Logo.webp", "patch"),
    ("mfab_hat", "MFAB/Mfab Hat & Polo/mf4b logo hat.PES",
     "MFAB/MFab Logo.png", "hat_front"),
    ("mfab_lc", "MFAB/Mfab Hat & Polo/mf4b logo lc.PES",
     "MFAB/MFab Logo.png", "left_chest"),
    ("precision_drone", "Precision Drone/PRECISION DRON HAT 2.PES",
     "Precision Drone/Precision Thermal Drone Logo.png", "hat_front"),
    ("tires_hat_3d", "TIRES/fwdyourdigitizingorderisreadytireslogo (1)/TIRES HAT 3D.PES",
     "TIRES/Tires Logo.png", "hat_front"),
    ("bridge_hat", "Bridge Bar/Bridge Bar Embroidery Files/BRIDGE LOGO HAT.PES",
     "Bridge Bar/Bridge Bar Logo.jpg", "hat_front"),
    ("bridge_lc", "Bridge Bar/Bridge Bar Embroidery Files/BRIDGE LOGO LC.PES",
     "Bridge Bar/Bridge Bar Logo.jpg", "left_chest"),
    ("proseal_hat", "Proseal/PROSEALHAT.DST", "Proseal/PROSeal Logo.jpg", "hat_front"),
]

_T = DIGITIZER / "testdata"
ART_FALLBACK = {
    "becker": _T / "becker_marine_logo.png",
    "gaulke_roofing": _T / "photo" / "logo_gaulke_roofing.png",
    "hotel_fremont": _T / "photo" / "logo_hotel_fremont.webp",
    "precision_drone": _T / "photo" / "drone_render.png",
    "tires": _T / "logo_script_tires.png",
    "bridge": _T / "photo" / "logo_bridge_bar.jpg",
}


# ------------------------------------------------------------------ files
def roots() -> list[Path]:
    out = []
    if os.environ.get("PRO_PARITY_ROOT"):
        out.append(Path(os.environ["PRO_PARITY_ROOT"]))
    out.append(Path("G:/My Drive/EMB-Bot/Embroidery Files"))
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=DIGITIZER,
                                capture_output=True, text=True).stdout.strip()
        out.append(Path(common).resolve().parent / "scratch_kent" / "Embroidery Files")
    except OSError:
        pass
    return out


def find(rel: str) -> Path | None:
    """`rel` under the first root that has it; Drive's `_` for the zip's `:`."""
    for root in roots():
        for cand in (rel, rel.replace("To a T_", "To a T-")):
            p = root / cand
            if p.exists():
                return p
        # the same folder with a sibling extension case (.PES vs .pes, .DST)
        p = root / rel
        if p.parent.exists():
            for q in p.parent.iterdir():
                if q.name.lower() == p.name.lower():
                    return q
    return None


def find_pair(slug: str, pro_rel: str, art_rel: str):
    pro = find(pro_rel)
    art = find(art_rel)
    if art is None:
        for key, fb in ART_FALLBACK.items():
            if slug.startswith(key) and fb.exists():
                art = fb
                break
    if pro is None and pro_rel.endswith(".PES"):
        pro = find(pro_rel[:-4] + ".DST")
    return pro, art


# ------------------------------------------------------------- digitizing
def digitize_one(slug: str, cache: Path) -> dict:
    """Digitize `slug` at the pro's width and cache ours.dst + ours.json."""
    from tools import pro_pair as pp
    from digitizer_core.export import write_dst
    from tools.fremont_triage import STUDIO_FABRIC_RGB

    row = next(r for r in PAIRS if r[0] == slug)
    pro, art = find_pair(*row[:3])
    if pro is None or art is None:
        raise SystemExit(f"{slug}: missing {'pro' if pro is None else 'art'} file")
    width = pp.pro_counts(pro)["width_mm"]
    d = pp.digitize(art, width, row[3])
    out = cache / slug
    out.mkdir(parents=True, exist_ok=True)
    write_dst(d.plan, out / "ours.dst")

    kinds: dict[str, dict] = {}
    rgbs: dict[str, list] = {}
    ring_runs = []
    for blk, run in d.plan.iter_runs():
        role = getattr(run, "role", "") or ""
        if str(run.kind) in ("border", "bean", "run") or role in ("border", "edge_cap"):
            xs = [p[0] for p in run.points or []]
            ys = [p[1] for p in run.points or []]
            if xs:
                ring_runs.append({"id": str(run.shape_id), "kind": str(run.kind), "role": role,
                                  "bbox": [min(xs), min(ys), max(xs), max(ys)], "n": len(xs)})
        k = kinds.setdefault(str(run.shape_id), {})
        key = str(run.kind) + (f":{run.role}" if getattr(run, "role", "") else "")
        k[key] = k.get(key, 0) + len(run.points or [])
        rgbs[str(run.shape_id)] = list(blk.rgb)
    regions = []
    for r in d.result.regions:
        m = getattr(r, "meta", {}) or {}
        from digitizer_core.threads import CHART
        try:
            chart_rgb = list(CHART[r.thread_index].rgb)
        except Exception:  # noqa: BLE001
            chart_rgb = None
        regions.append({
            "id": r.shape_id, "wkt": r.polygon.wkt, "rgb": rgbs.get(str(r.shape_id)) or chart_rgb,
            "kinds": kinds.get(str(r.shape_id), {}),
            "meta": {k: m[k] for k in ("tier", "technique", "border", "text_cluster_id",
                                       "lettering_group", "rescued_small_shape",
                                       "bean_letter", "small_text_stray") if k in m},
        })
    info = {"slug": slug, "garment": row[3], "width_mm": width, "pro": str(pro), "art": str(art),
            "ground_rgb": list(STUDIO_FABRIC_RGB), "secs": round(d.secs, 1),
            "warnings": [w.get("code") for w in getattr(d.plan, "warnings", [])],
            "blocks": [list(b.rgb) for b in d.plan.blocks], "ring_runs": ring_runs, "regions": regions}
    (out / "ours.json").write_text(json.dumps(info), encoding="utf-8")
    return info


# -------------------------------------------------------------- detection
def satin_segments(runs):
    """-> (satin chords, all other stitch segments), each [(x0,y0,x1,y1)] mm."""
    from tools.border_pro import columns
    sat, oth = [], []
    for r in runs:
        pts = r["pts"]
        if len(pts) < 2:
            continue
        cols, _t, _c = columns(pts)
        insat = [False] * (len(pts) - 1)
        for a, b in cols:
            for i in range(a, min(b, len(pts) - 1)):
                insat[i] = True
        for i in range(len(pts) - 1):
            seg = (pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
            (sat if insat[i] else oth).append(seg)
    return sat, oth


def closed_satin_loops(runs):
    """Satin columns whose SPINE closes on itself: -> [{spine, width}].

    A border is a column laid along a closed outline; a letter or a bar is a
    column along an open path. The spine is the midpoints of consecutive stitch
    pairs (every pair spans the column); it is closed when its ends meet within
    a column width and a half, and it encloses some area.
    """
    from shapely.geometry import Polygon
    from tools.border_pro import columns
    out = []
    for ri, r in enumerate(runs):
        pts = r["pts"]
        if len(pts) < 8:
            continue
        cols, _t, _c = columns(pts)
        for a, b in cols:
            seg = pts[a:b + 1]
            if len(seg) < 8:
                continue
            spine = [((p[0] + q[0]) / 2, (p[1] + q[1]) / 2) for p, q in zip(seg, seg[1:])]
            wid = float(sorted(math.dist(p, q) for p, q in zip(seg, seg[1:]))[len(seg) // 2])
            gap = math.dist(spine[0], spine[-1])
            length = sum(math.dist(p, q) for p, q in zip(spine, spine[1:]))
            if length < 3.0 or gap > LOOP_GAP_MM:
                continue
            try:
                area = Polygon(spine).buffer(0).area
            except Exception:  # noqa: BLE001
                continue
            # a fill's rows run back and forth across a shape: its spine is a
            # line, whose "area" is nothing. A ring's spine is round.
            if area < 0.2 or 4.0 * math.pi * area / (length * length) < LOOP_ROUND_MIN:
                continue
            out.append({"spine": spine, "width": wid, "kind": "satin", "idx": ri, "span": (a, b)})
    out += closed_run_loops(runs)
    return out


def closed_run_loops(runs):
    """Run / bean outlines: a needle-down run phase that laps back to its start.

    A bean ring is the same ring walked three times, so the FIRST lap is the
    spine (the loop closes the first time the path returns to its start).
    """
    from shapely.geometry import Polygon
    from tools.census_pro import _phases
    out = []
    for ri, r in enumerate(runs):
        pts = r["pts"]
        if len(pts) < 10:
            continue
        pos = 0
        for tok, cnt, _med in _phases(pts):
            chunk = pts[pos:pos + cnt + 1]
            start = pos
            pos += cnt
            if tok != "R" or len(chunk) < 10:
                continue
            lap, run_len = None, 0.0
            for j in range(1, len(chunk)):
                run_len += math.dist(chunk[j - 1], chunk[j])
                if j >= 6 and run_len >= 3.0 and math.dist(chunk[j], chunk[0]) <= LOOP_GAP_MM:
                    lap = chunk[:j + 1]
                    break
            if lap is None:
                continue
            length = sum(math.dist(p, q) for p, q in zip(lap, lap[1:]))
            try:
                area = Polygon(lap).buffer(0).area
            except Exception:  # noqa: BLE001
                continue
            if area < 0.2 or 4.0 * math.pi * area / (length * length) < LOOP_ROUND_MIN:
                continue
            out.append({"spine": lap, "width": RUN_WIDTH_MM, "kind": "run", "idx": ri, "span": (start, start + len(lap))})
    return out


def interior_order(poly, masks, idx: int, span=None) -> tuple[int, int]:
    """Stitches of OTHER runs inside `poly` (shrunk 0.3 mm): -> (sewn before run
    `idx`, sewn after it). A border is sewn over its interior; underlay under it."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    core = poly.buffer(-0.3)
    if core.is_empty:
        return 0, 0
    pc, b = prep(core), core.bounds
    before = after = 0
    for j, (r, bx) in enumerate(zip(masks.runs, masks.run_box)):
        if bx is None or bx[2] < b[0] or bx[0] > b[2] or bx[3] < b[1] or bx[1] > b[3]:
            continue
        if j == idx and span is not None:
            # the same needle-down run: what it laid before / after the loop
            for k, (x, y) in enumerate(r["pts"]):
                if span[0] <= k <= span[1] or not pc.contains(Point(x, y)):
                    continue
                if k < span[0]:
                    before += 1
                else:
                    after += 1
            continue
        if j == idx:
            continue
        n = sum(1 for x, y in r["pts"][::2] if pc.contains(Point(x, y)))
        if j < idx:
            before += n
        else:
            after += n
    return before, after


def hugging_loop(poly, loops, inr: float, masks=None):
    """The closed column whose spine best follows `poly`'s outline, or None."""
    from shapely.geometry import Point
    b = poly.bounds
    cands = []
    for lp in loops:
        # a ring-shaped stroke (an O) or a shape the column's own reach covers
        # is ONE column, not a border round something else
        if inr <= 0.5 * lp["width"] + 0.3:
            continue
        xs = [p[0] for p in lp["spine"]]
        ys = [p[1] for p in lp["spine"]]
        if (min(xs) > b[2] + 1.5 or max(xs) < b[0] - 1.5 or min(ys) > b[3] + 1.5 or max(ys) < b[1] - 1.5):
            continue
        # the spine must span the shape, not merely cross it
        if (max(xs) - min(xs)) < 0.5 * (b[2] - b[0]) or (max(ys) - min(ys)) < 0.5 * (b[3] - b[1]):
            continue
        tol = 0.5 * lp["width"] + 0.5
        d = [poly.boundary.distance(Point(x, y)) for x, y in lp["spine"][::2]]
        mean = sum(d) / len(d)
        if mean <= tol and max(d) <= 2.0 * tol:
            cands.append((mean, lp))
    for _mean, lp in sorted(cands, key=lambda t: t[0]):
        if masks is None:
            return lp
        before, after = interior_order(poly, masks, lp["idx"], lp.get("span"))
        # sewn OVER its interior, or alone (an outline-only shape); not underlay
        if before >= after:
            return lp
    return None


class Masks:
    """Satin and other-stitch masks for ONE stitch file over a fixed frame."""

    def __init__(self, runs, bounds):
        import cv2
        import numpy as np
        self.x0, self.y0 = bounds[0] - 3.0, bounds[1] - 3.0
        w = int((bounds[2] - bounds[0] + 6.0) * RES) + 2
        h = int((bounds[3] - bounds[1] + 6.0) * RES) + 2
        self.sat = np.zeros((h, w), np.uint8)
        self.oth = np.zeros((h, w), np.uint8)
        sat, oth = satin_segments(runs)
        self.sat_segs = sat
        self.loops = closed_satin_loops(runs)
        self.runs = runs
        self.run_box = [(min(p[0] for p in r["pts"]), min(p[1] for p in r["pts"]),
                         max(p[0] for p in r["pts"]), max(p[1] for p in r["pts"])) if r["pts"] else None
                        for r in runs]
        t = max(1, int(round(SATIN_PAINT_MM * RES)))
        for segs, m in ((sat, self.sat), (oth, self.oth)):
            for x0, y0, x1, y1 in segs:
                cv2.line(m, self.px(x0, y0), self.px(x1, y1), 255, t)
        # every stitch, for "something rides the outline"
        self.any = cv2.bitwise_or(self.sat, self.oth)

    def px(self, x, y):
        return (int(round((x - self.x0) * RES)), int(round((y - self.y0) * RES)))


def _ring_pts(poly):
    rings = [poly.exterior] + list(poly.interiors)
    return [[(x, y) for x, y in r.coords] for r in rings]


def shape_class(poly, masks: Masks) -> dict:
    """Classify one polygon (in `masks`' frame) against that file's stitches."""
    import cv2
    import numpy as np
    from shapely.geometry import Point
    b = poly.bounds
    pad = 2.5
    ix0 = max(0, int((b[0] - pad - masks.x0) * RES))
    iy0 = max(0, int((b[1] - pad - masks.y0) * RES))
    ix1 = min(masks.sat.shape[1], int((b[2] + pad - masks.x0) * RES) + 1)
    iy1 = min(masks.sat.shape[0], int((b[3] + pad - masks.y0) * RES) + 1)
    if ix1 <= ix0 or iy1 <= iy0:
        return {"cls": "NONE", "band": 0.0, "core": 0.0, "width": None, "inr": 0.0}
    sat = masks.sat[iy0:iy1, ix0:ix1]
    anyst = masks.any[iy0:iy1, ix0:ix1]
    h, w = sat.shape

    def loc(x, y):
        px, py = masks.px(x, y)
        return (px - ix0, py - iy0)

    inside = np.zeros((h, w), np.uint8)
    cv2.fillPoly(inside, [np.array([loc(x, y) for x, y in poly.exterior.coords], np.int32)], 255)
    for hole in poly.interiors:
        cv2.fillPoly(inside, [np.array([loc(x, y) for x, y in hole.coords], np.int32)], 0)
    edge = np.zeros((h, w), np.uint8)
    for ring in _ring_pts(poly):
        cv2.polylines(edge, [np.array([loc(x, y) for x, y in ring], np.int32)], True, 255, 1)
    sat_d = cv2.dilate(sat, np.ones((3, 3), np.uint8))
    any_d = cv2.dilate(anyst, np.ones((3, 3), np.uint8))
    ep = edge > 0
    band = float((sat_d[ep] > 0).mean()) if ep.any() else 0.0
    band_any = float((any_d[ep] > 0).mean()) if ep.any() else 0.0
    dist = cv2.distanceTransform((inside > 0).astype(np.uint8), cv2.DIST_L2, 5) / RES
    inr = float(dist.max()) if dist.size else 0.0

    # column width along the edge: chords whose middle sits within 1 mm of it
    wid = []
    for x0, y0, x1, y1 in masks.sat_segs:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if not (b[0] - 1 <= mx <= b[2] + 1 and b[1] - 1 <= my <= b[3] + 1):
            continue
        p = Point(mx, my)
        if poly.boundary.distance(p) <= 1.0:
            wid.append(math.hypot(x1 - x0, y1 - y0))
    width = float(np.median(wid)) if wid else None

    # the centre test: pixels within 20% of the shape's own inradius of its
    # deepest point. A column that spans the shape covers them; a ring leaves
    # them to whatever the shape's interior got.
    core = dist >= 0.8 * inr if inr >= 0.5 else (dist >= 0)
    core_area = float((dist >= 0.8 * inr).sum()) / (RES * RES) if inr >= 0.5 else 0.0
    core_sat = float((sat[core & (inside > 0)] > 0).mean()) if (core & (inside > 0)).any() else 0.0
    ins = inside > 0
    inner_any = float((anyst[ins] > 0).mean()) if ins.any() else 0.0

    loop = hugging_loop(poly, masks.loops, inr, masks)
    if loop is not None:
        cls = "BORDER" if loop["kind"] == "satin" else "OUTLINE"
        width = round(loop["width"], 2) if loop["kind"] == "satin" else None
    elif (band >= BAND_MIN and inr > 0.5 * (width or 1.0) + 0.3 and core_sat < CORE_SATIN_MAX):
        # the pro often splits a border into two OPEN half-columns (Hotel
        # Fremont's shield): no closed spine, but satin rides the outline
        # and the middle of the shape is something else
        cls = "BORDER"
    elif band >= BAND_MIN:
        cls = "SATIN"
    elif inner_any >= 0.5:
        cls = "FILL"
    elif band_any >= 0.5:
        cls = "RUN"
    else:
        cls = "NONE"
    return {"cls": cls, "band": round(band, 2), "core": round(core_sat, 2),
            "core_mm2": round(core_area, 2), "width": None if width is None else round(width, 2),
            "inr": round(inr, 2), "interior": round(inner_any, 2)}


# ----------------------------------------------------------------- colour
def _lab(rgb):
    import numpy as np
    c = np.array(rgb, float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    x, y, z = (m @ c) / np.array([0.95047, 1.0, 1.08883])
    f = lambda t: np.cbrt(t) if t > 0.008856 else 7.787 * t + 16 / 116
    return np.array([116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))])


def contrast(poly, rgb, regions_polys, ground):
    """dE76 of the shape's thread against its area-weighted surround."""
    from shapely.ops import unary_union
    if rgb is None:
        return None
    ring = poly.buffer(0.6).difference(poly)
    if ring.area <= 0:
        return None
    acc, covered = [], 0.0
    for other, orgb in regions_polys:
        if other is poly or orgb is None:
            continue
        a = ring.intersection(other).area if ring.intersects(other) else 0.0
        if a > 0:
            acc.append((a, orgb))
            covered += a
    rest = max(ring.area - covered, 0.0)
    if rest > 0:
        acc.append((rest, ground))
    tot = sum(a for a, _ in acc)
    lab = sum(_lab(c) * a for a, c in acc) / tot
    return float(((lab - _lab(rgb)) ** 2).sum() ** 0.5)


# ---------------------------------------------------------------- analysis
def analyse(slug: str, cache: Path) -> dict:
    from shapely import wkt
    from shapely.affinity import affine_transform
    from tools.pro_parity.pairframe import register_pair
    from tools.study_pro import load_runs

    out = cache / slug
    info = json.loads((out / "ours.json").read_text(encoding="utf-8"))
    pro = Path(info["pro"])
    ours_runs, _t, _j = load_runs(out / "ours.dst")
    pro_runs, _t, _j = load_runs(pro)
    reg = register_pair(pro, out / "ours.dst")
    regs = [(r, wkt.loads(r["wkt"])) for r in info["regions"]]
    polys_ours = [p for _r, p in regs]
    polys_pro = [affine_transform(p, reg.matrix()) for p in polys_ours]

    def bounds(polys, runs):
        xs = [v for p in polys for v in (p.bounds[0], p.bounds[2])]
        ys = [v for p in polys for v in (p.bounds[1], p.bounds[3])]
        for r in runs:
            for x, y in r["pts"]:
                xs.append(x)
                ys.append(y)
        return min(xs), min(ys), max(xs), max(ys)

    m_ours = Masks(ours_runs, bounds(polys_ours, ours_runs))
    m_pro = Masks(pro_runs, bounds(polys_pro, pro_runs))
    pairs = [(p, r["rgb"]) for r, p in regs]
    rows = []
    for (r, po), pp_ in zip(regs, polys_pro):
        if po.area < MIN_AREA_MM2 or not po.is_valid and po.buffer(0).area < MIN_AREA_MM2:
            continue
        o = shape_class(po, m_ours)
        p = shape_class(pp_, m_pro)
        rs = ring_source(po.bounds, info.get("ring_runs", []), r["id"])
        if not r["kinds"] and not rs:
            # stage 7 sewed nothing for this shape; a loop here is a neighbour's
            o = dict(o, cls="UNSEWN", width=None)
        bb = po.bounds
        rows.append({
            "id": r["id"], "area": round(po.area, 1),
            "bbox": [round(bb[2] - bb[0], 1), round(bb[3] - bb[1], 1)],
            "mindim": round(2 * max(o["inr"], 0.0), 1),
            "holes": len(po.interiors), "rgb": r["rgb"],
            "contrast": None if (c := contrast(po, r["rgb"], pairs, info["ground_rgb"])) is None else round(c),
            "kinds": r["kinds"], "meta": r["meta"], "ours": o, "pro": p,
            "ring_src": rs,
            "xy": [round(bb[0], 1), round(bb[1], 1), round(bb[2], 1), round(bb[3], 1)],
        })
    return {"slug": slug, "info": {k: info[k] for k in ("garment", "width_mm", "secs", "warnings")},
            "reg": reg.as_dict(), "rows": rows}


def ring_source(bb, ring_runs, sid) -> list[str]:
    """Which of OUR run kinds ride this shape's box: its own ring-ish runs, and
    cap / border pieces filed under another id whose box sits on it."""
    out: dict[str, int] = {}
    cx0, cy0, cx1, cy1 = bb
    for rr in ring_runs:
        x0, y0, x1, y1 = rr["bbox"]
        own = rr["id"] == sid
        if not own:
            if x1 < cx0 - 0.5 or x0 > cx1 + 0.5 or y1 < cy0 - 0.5 or y0 > cy1 + 0.5:
                continue
            # the run's box must be about this shape's, not a big neighbour's
            if (x1 - x0) > 1.6 * (cx1 - cx0) + 1.0 or (y1 - y0) > 1.6 * (cy1 - cy0) + 1.0:
                continue
        key = rr["kind"] + (f"/{rr['role']}" if rr["role"] else "") + ("" if own else " (other id)")
        out[key] = out.get(key, 0) + 1
    return [f"{k} x{n}" for k, n in sorted(out.items())]


def row_class(row) -> str | None:
    o, p = row["ours"], row["pro"]
    if o["cls"] == "UNSEWN":
        return None
    ro, rp = o["cls"] in RING, p["cls"] in RING
    # a ring-shaped region sewn as one satin ring is a ring on BOTH sides,
    # however this detector happened to label each
    if row["holes"] and "SATIN" in (o["cls"], p["cls"]) and (ro or rp) and row["mindim"] <= 2.0 * max(
            o["width"] or 0.0, p["width"] or 0.0, 1.0):
        return None
    if ro and not rp:
        return "a"
    if rp and not ro:
        return "b"
    if ro and rp:
        if o["cls"] != p["cls"]:
            return "c"
        if o["width"] is not None and p["width"] is not None and abs(o["width"] - p["width"]) >= WIDTH_DIFF_MM:
            return "c"
    return None


def our_rule(row) -> str:
    """Which of our functions produced what we sewed, from the run kinds."""
    k = row["kinds"]
    keys = " ".join(k) + " " + " ".join(row.get("ring_src", []))
    if "edge_cap" in keys and row["ours"]["cls"] in RING:
        return "edge cap, stage 7 (`edge_cap=bean` cap pieces)"
    if "border" in k or "border/" in keys:
        return "stage6_border.border_runs via _border_wanted"
    if "satin" in k and row["holes"]:
        return "satin tier (stage6_satin) on a ring-shaped region"
    if "satin" in k:
        return "satin tier (stage6_satin)"
    if "bean" in keys or "edge_cap" in keys:
        return "edge cap (bean ring)"
    if "run" in k:
        return "run tier (small-shape rescue)"
    if "fill" in k:
        return "fill tier (stage6_fill)"
    return "unsewn / covered"


def sewn_instead(row) -> str:
    k = row["kinds"]
    parts = [f"{n} {kind}" for kind, n in sorted(k.items(), key=lambda kv: -kv[1]) if kind not in ("travel", "tie")]
    return ", ".join(parts[:3]) or "nothing"


def table(results: list[dict]) -> str:
    lines = ["| pair | shape | size mm (bbox / min dim) | holes | contrast dE | ours (class, width) | we sewed | rule | pro (class, width) | row |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for res in results:
        for row in res["rows"]:
            rc = row_class(row)
            if not rc:
                continue
            o, p = row["ours"], row["pro"]
            wo = "" if o["width"] is None else f", {o['width']}"
            wp = "" if p["width"] is None else f", {p['width']}"
            lines.append(
                f"| {res['slug']} | {row['id']} | {row['bbox'][0]}x{row['bbox'][1]} / {row['mindim']} | "
                f"{row['holes']} | {row['contrast']} | {o['cls']}{wo} | {sewn_instead(row)} | {our_rule(row)} | "
                f"{p['cls']}{wp} | {rc} |")
    return "\n".join(lines)


def summary(results: list[dict]) -> str:
    """Per pair counts, and the pro's BORDER shapes against its non-borders."""
    import statistics as st
    lines = ["| pair | shapes >=1 mm2 | ours ring | pro ring | both | (a) | (b) | (c) | pro width mm |",
             "|---|---|---|---|---|---|---|---|---|"]
    allrows = []
    for res in results:
        rows = res["rows"]
        allrows += [dict(r, slug=res["slug"]) for r in rows]
        ob = sum(r["ours"]["cls"] in RING for r in rows)
        pb = sum(r["pro"]["cls"] in RING for r in rows)
        both = sum(r["ours"]["cls"] in RING and r["pro"]["cls"] in RING for r in rows)
        cnt = {k: sum(row_class(r) == k for r in rows) for k in "abc"}
        lines.append(f"| {res['slug']} | {len(rows)} | {ob} | {pb} | {both} | {cnt['a']} | {cnt['b']} | {cnt['c']} | {res['info']['width_mm']} |")

    def stats(sel, label):
        if not sel:
            return f"- {label}: none"
        md = [r["mindim"] for r in sel]
        ar = [r["area"] for r in sel]
        ct = [r["contrast"] for r in sel if r["contrast"] is not None]
        return (f"- {label}: n={len(sel)}, min dim median {st.median(md):.1f} mm "
                f"(range {min(md):.1f}-{max(md):.1f}), area median {st.median(ar):.1f} mm2, "
                f"contrast median {st.median(ct) if ct else float('nan'):.0f} dE, "
                f"with a hole {sum(r['holes'] > 0 for r in sel)}")
    lines.append("")
    lines.append(stats([r for r in allrows if r["pro"]["cls"] in RING], "pro ringed shapes"))
    lines.append(stats([r for r in allrows if r["ours"]["cls"] in RING], "our ringed shapes"))
    lines.append(stats([r for r in allrows if r["pro"]["cls"] not in RING],
                       "pro shapes with no ring (FILL, SATIN, RUN, NONE)"))
    # by min-dimension bucket
    lines.append("")
    lines.append("| min dim (mm) | shapes | pro ring | our ring |")
    lines.append("|---|---|---|---|")
    for lo, hi in ((0, 2), (2, 3), (3, 4), (4, 6), (6, 10), (10, 999)):
        sel = [r for r in allrows if lo <= r["mindim"] < hi]
        lines.append(f"| {lo}-{hi if hi < 999 else 'up'} | {len(sel)} | "
                     f"{sum(r['pro']['cls'] in RING for r in sel)} | "
                     f"{sum(r['ours']['cls'] in RING for r in sel)} |")
    return "\n".join(lines)


# ------------------------------------------------------------------ crops
def crop_row(slug: str, row: dict, cache: Path, out: Path, name: str, reg: dict) -> None:
    """art | ours | pro, 40 px/mm, around one shape."""
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    from tools import pro_pair as pp
    from tools.pro_parity import pairframe
    info = json.loads((cache / slug / "ours.json").read_text(encoding="utf-8"))
    ours_d = pairframe.design_for(cache / slug / "ours.dst", None, info["blocks"] or None, slug)
    pro_p = Path(info["pro"])
    pro_d = pairframe.design_for(pro_p, None, None, pro_p.stem)
    ppm, pad = pp.PPM_CROP, pp.PAD_MM
    x0, y0, x1, y1 = row["xy"]
    m = 3.0
    s, fy, dx, dy = reg["scale"], (-1.0 if reg["flip_y"] else 1.0), reg["dx"], reg["dy"]
    px = [s * x + dx for x in (x0, x1)]
    py = sorted([s * fy * y + dy for y in (y0, y1)])
    ox, oy = pp._design_top_left_mm(ours_d)
    qx, qy = pp._design_top_left_mm(pro_d)
    ours_img = stitchviz.render_design(ours_d, px_per_mm=ppm)
    pro_img = stitchviz.render_design(pro_d, px_per_mm=ppm)
    ink = pp._art_ink(Path(info["art"]))
    art_img = pp._scaled(ink, info["width_mm"], ppm, cv2.INTER_CUBIC)
    c_o = (x0 - ox - m, y0 - oy - m, x1 - ox + m, y1 - oy + m)
    c_p = (min(px) - qx - m * s, py[0] - qy - m * s, max(px) - qx + m * s, py[1] - qy + m * s)
    tiles = [pp._crop_px(art_img, c_o, 0.0, ppm), pp._crop_px(ours_img, c_o, pad, ppm),
             pp._crop_px(pro_img, c_p, pad, ppm)]
    hh = min(t.shape[0] for t in tiles)
    tiles = [pp._label(t[:hh], lab) for t, lab in zip(tiles, ("art", "ours", "pro"))]
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / name), pp._hstack(tiles, gap=12))


# -------------------------------------------------------------------- main
def run_cmd(args) -> int:
    cache = Path(args.cache)
    slugs = [r[0] for r in PAIRS if not args.only or r[0] in args.only]
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


def table_cmd(args) -> int:
    cache = Path(args.cache)
    results = []
    for slug, *_ in PAIRS:
        if args.only and slug not in args.only:
            continue
        if not (cache / slug / "ours.json").exists():
            print("no cache for", slug)
            continue
        res = analyse(slug, cache)
        (cache / slug / "census.json").write_text(json.dumps(res), encoding="utf-8")
        results.append(res)
    body = ("## Per pair\n\n" + summary(results) + "\n\n## Rows (a) ours borders, pro does not; "
            "(b) pro borders, ours does not; (c) both, widths differ\n\n" + table(results) + "\n")
    Path(args.table_out).write_text(body, encoding="utf-8")
    print(body)
    if args.crop_ids:
        by = {(r["slug"], x["id"]): (r, x) for r in results for x in r["rows"]}
        for tag in args.crop_ids:
            slug, _, sid = tag.partition(":")
            if (slug, sid) in by:
                res, row = by[(slug, sid)]
                crop_row(slug, row, cache, OUT_CROPS, f"{slug}_{sid}_{row_class(row) or 'none'}.png", res["reg"])
    elif args.crops:
        for cls in "abc":
            sel = [(r, x) for r in results for x in r["rows"] if row_class(x) == cls]
            sel.sort(key=lambda t: -t[1]["area"])
            for i, (res, row) in enumerate(sel[:2]):
                crop_row(res["slug"], row, cache, OUT_CROPS, f"class_{cls}_{i + 1}_{res['slug']}_{row['id']}.png", res["reg"])
    return 0


def one_cmd(args) -> int:
    digitize_one(args.slug, Path(args.cache))
    return 0


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", run_cmd), ("table", table_cmd), ("one", one_cmd)):
        p = sub.add_parser(name)
        p.add_argument("--cache", default=str(DIGITIZER / "debug_out" / "border_census"))
        p.add_argument("--only", nargs="*")
        p.add_argument("--jobs", type=int, default=3)
        p.add_argument("--redo", action="store_true")
        p.add_argument("--crop-ids", nargs="*", help="slug:shape_id pairs to crop (replaces --crops' picks)")
        p.add_argument("--crops", action="store_true", help="write the per-class crops into docs/renders")
        p.add_argument("--table-out", default=str(Path(os.environ.get("TEMP", ".")) / "border_census_table.md"))
        if name == "one":
            p.add_argument("slug")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
