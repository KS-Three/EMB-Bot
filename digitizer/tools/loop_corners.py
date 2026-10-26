"""loop_corners: how a satin loop round a letter turns the letter's convex
corners, read one way on our file and the professional's (2026-10-25,
`cfg.outline_loop_mitre`).

The keyline and outline loops (`stage6_border.keyline_runs`) put one rail on
the letter's outline and cross out into the band. Through a convex corner of
the letter the crosses rotate while their near ends sit near the corner, so
the far ends spread round an arc: how far apart they spread is the "spike".

WHAT IT READS. Crosses: needle-down runs, split legs fused, zigzag chains
(`tools.letter_pieces`). Corners: the CLEAN convex corners of the LETTER
polygons the loops go round -- `outline_cut.corners`, turn >= `MIN_TURN`,
a straight edge of at least one loop width on both sides, so a traced
notch or a serif's step is not read as a corner -- read on our plan and
carried into the pro's frame by the two loops' boxes, then snapped onto the
pro's near rail. A cross belongs to a corner when its near end (the end on
the letter's outline, within `NEAR_MM`) lies within `REACH_W` loop widths of
it. Per corner:

  turn      the corner's turn, degrees
  far_n     distinct far ends whose direction from the corner lies inside the
            corner's wedge (between the two edges' normals): the arc's crosses
  pitch     median step between those far ends in order round the arc -- the
            far rail's pitch through the corner (the satin pitch, 0.4, where
            the far rail stays dense)
  pitch_max the widest such step: a fan's spike
  radius    median distance of those far ends from the corner, over the loop
            width: 1.00 is a round pivot; 1 / cos(turn / 2) (`mitre`) is a
            mitre point
  rot_mm    how far along the outline, before + after the corner, the crosses
            stand more than `ROT_DEG` off square to their own edge
  bis_deg   the cross nearest the bisector, its angle off the bisector
  over_mm   how far the furthest far end lies outside the letter grown by the
            loop width with a ROUND join (beyond the round arc)

    python -m tools.loop_corners --ours RUNS.pkl#SID --faces GEN.pkl#SID[#holes]
        --pro FILE.dst@B1,B2 --width MM [--out JSON] [--png OUT]

`RUNS.pkl` is a list of {block, shape_id, kind, role, trim, jump, pts} runs (the
plan's runs, as a harness dumps them); `GEN.pkl#SID` is a pickled
{"result": PipelineResult} and the shape whose polygon holds the letters:
`#holes` reads its holes (an outline / keyline band round the letters), no
suffix the shape itself.
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from shapely import affinity  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402

MIN_TURN = 70.0      # a corner, not a traced bend (a letter's square corner turns ~90)
NEAR_MM = 0.45       # a cross's near end lies on the letter's outline within this
REACH_W = 1.5        # loop widths round a corner whose crosses belong to it
ROT_DEG = 12.0       # off square to its own edge by more than this: rotating
FAN_MM = 0.8         # a far-rail step wider than this (twice the satin pitch): a spike


# ------------------------------------------------------------------ input
def runs_from_pickle(spec: str) -> list[dict]:
    """`RUNS.pkl#SID[,SID]` -> needle-down runs of those shapes, consecutive
    runs joined unless the next starts with a jump or a trim."""
    path, _, sids = spec.partition("#")
    keep = set(sids.split(",")) if sids else None
    out, cur, prev = [], [], None
    for r in pickle.loads(Path(path).read_bytes()):
        if (keep is not None and r["shape_id"] not in keep) or not r["pts"] or r["kind"] != "satin":
            if len(cur) >= 2:
                out.append({"block": prev, "pts": np.array(cur, float)})
            cur, prev = [], None
            continue
        if cur and (r["jump"] or r["trim"] or r["block"] != prev):
            if len(cur) >= 2:
                out.append({"block": prev, "pts": np.array(cur, float)})
            cur = []
        cur += [tuple(p) for p in r["pts"]]
        prev = r["block"]
    if len(cur) >= 2:
        out.append({"block": prev, "pts": np.array(cur, float)})
    return out


def runs_from_file(spec: str) -> list[dict]:
    """`FILE[@B1,B2]` -> the machine file's needle-down runs in those blocks."""
    from tools import letter_pieces as lp
    path, _, blk = spec.partition("@")
    keep = {int(b) for b in blk.split(",")} if blk else None
    return [r for r in lp.runs_of(Path(path)) if keep is None or r["block"] in keep]


def crosses_of(runs: list[dict]) -> list[tuple[np.ndarray, np.ndarray]]:
    """Every zigzag cross of the runs, in sewing order."""
    from tools import letter_pieces as lp
    out = []
    for r in runs:
        for ch in lp.chains(lp.fuse(r["pts"])):
            out += [(np.array(s[0], float), np.array(s[1], float)) for s in ch]
    return out


def faces_from_pickle(spec: str) -> list[Polygon]:
    path, _, rest = spec.partition("#")
    sid, _, holes = rest.partition("#")
    res = pickle.loads(Path(path).read_bytes())["result"]
    poly = next(r.polygon for r in res.regions if r.shape_id == sid)
    if holes:
        return [Polygon(h) for h in poly.interiors]
    return [poly]


def box_of(crosses) -> tuple[float, float, float, float]:
    P = np.array([p for c in crosses for p in c])
    return float(P[:, 0].min()), float(P[:, 1].min()), float(P[:, 0].max()), float(P[:, 1].max())


def carry(faces: list[Polygon], src, dst) -> list[Polygon]:
    """Our letters into the other file's frame, box onto box (`snap` then
    moves each onto that file's own near rail)."""
    sx = (dst[2] - dst[0]) / max(src[2] - src[0], 1e-9)
    sy = (dst[3] - dst[1]) / max(src[3] - src[1], 1e-9)
    out = []
    for f in faces:
        g = affinity.translate(f, -src[0], -src[1])
        g = affinity.scale(g, sx, sy, origin=(0, 0))
        out.append(affinity.translate(g, dst[0], dst[1]))
    return out


def snap(face: Polygon, crosses, reach_mm: float = 2.5, step_mm: float = 0.1) -> Polygon:
    """`face` moved (translation only, within `reach_mm`) to where the most
    cross ends lie on its outline -- the other file's near rail. Box-onto-box
    leaves a letter 1-2 mm off where one file's loop is wider on one side
    (Becker's drop shadow)."""
    import cv2
    ppm = 20.0
    x0, y0, x1, y1 = face.bounds
    x0, y0, x1, y1 = x0 - reach_mm - 4, y0 - reach_mm - 4, x1 + reach_mm + 4, y1 + reach_mm + 4
    P = np.array([q for c in crosses for q in c])
    P = P[(P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > y0) & (P[:, 1] < y1)]
    if len(P) == 0:
        return face
    Wd, Hd = int((x1 - x0) * ppm) + 1, int((y1 - y0) * ppm) + 1
    img = np.full((Hd, Wd), 255, np.uint8)
    pts = np.array([((x - x0) * ppm, (y - y0) * ppm) for x, y in face.exterior.coords], np.int32)
    cv2.polylines(img, [pts], True, 0, 1)
    dist = cv2.distanceTransform(img, cv2.DIST_L2, 5) / ppm
    best = (-1, 0.0, 0.0)
    shifts = np.arange(-reach_mm, reach_mm + 1e-9, step_mm)
    for dx in shifts:
        for dy in shifts:
            # a point p lies on the shifted ring where p - shift lies on the ring
            u = ((P[:, 0] - dx - x0) * ppm).astype(int)
            v = ((P[:, 1] - dy - y0) * ppm).astype(int)
            ok = (u >= 0) & (u < Wd) & (v >= 0) & (v < Hd)
            score = int((dist[v[ok], u[ok]] <= 0.2).sum())
            if score > best[0]:
                best = (score, float(dx), float(dy))
    return affinity.translate(face, best[1], best[2])


# ---------------------------------------------------------------- corners
def convex_corners(face: Polygon, width: float) -> list[dict]:
    """The face's clean convex corners (module notes)."""
    from digitizer_core import outline_cut as oc
    _reflex, convex = oc.corners(face, width)
    return [c for c in convex
            if c["turn"] >= MIN_TURN and c["len_in"] >= width and c["len_out"] >= width]


def _signed_arc(ring: LineString, p, c) -> float:
    """Arc position of p along the ring relative to c, signed, the short way."""
    L = ring.length
    d = ring.project(Point(p)) - ring.project(Point(c))
    if d > L / 2:
        d -= L
    elif d < -L / 2:
        d += L
    return d


def _edge_normal(ring: LineString, p, corner_s: float) -> np.ndarray:
    """The outline's unit normal at p, read as a 1 mm chord on p's own side
    of the corner (a traced edge's single segments wobble)."""
    L = ring.length
    s = ring.project(Point(p))
    d = s - corner_s
    if d > L / 2:
        d -= L
    elif d < -L / 2:
        d += L
    lo, hi = (s - 1.0, s) if d < 0 else (s, s + 1.0)
    a, b = ring.interpolate(lo % L), ring.interpolate(hi % L)
    t = np.array([b.x - a.x, b.y - a.y], float)
    t /= max(float(np.hypot(*t)), 1e-12)
    return np.array([-t[1], t[0]])


def _ang(u, v) -> float:
    """Undirected angle between two directions, degrees 0-90."""
    cu = abs(float(u @ v)) / max(float(np.hypot(*u) * np.hypot(*v)), 1e-12)
    return math.degrees(math.acos(min(1.0, cu)))


def _arc_fars(group, c: dict, width: float) -> list[np.ndarray]:
    """The group's distinct far ends inside the corner's wedge, in order
    round the arc."""
    p = np.array(c["p"], float)
    out = -np.array(c["bis"], float)

    def nrm(d):
        n = np.array([-d[1], d[0]], float)
        return n if n @ out > 0 else -n
    na, nb = nrm(c["d_in"]), nrm(c["d_out"])
    a0 = math.atan2(na[1], na[0])
    span = (math.atan2(nb[1], nb[0]) - a0 + math.pi) % (2 * math.pi) - math.pi
    fars = {}
    for _k, _near, far in group:
        v = far - p
        if float(np.hypot(*v)) < 0.5 * width or abs(span) < 1e-6:
            continue
        t = ((math.atan2(v[1], v[0]) - a0 + math.pi) % (2 * math.pi) - math.pi) / span
        if -0.05 <= t <= 1.05:
            fars[(round(float(far[0]), 3), round(float(far[1]), 3))] = t
    return [np.array(k) for k, _t in sorted(fars.items(), key=lambda kv: kv[1])]


def read_corner(crosses, face: Polygon, c: dict, width: float) -> dict | None:
    ring = LineString(face.exterior.coords)
    p = np.array(c["p"], float)
    group = []
    for k, (a, b) in enumerate(crosses):
        da, db = ring.distance(Point(a)), ring.distance(Point(b))
        near, far = (a, b) if da <= db else (b, a)
        if min(da, db) > NEAR_MM or float(np.hypot(*(near - p))) > REACH_W * width:
            continue
        group.append((k, near, far))
    arc = _arc_fars(group, c, width)
    if len(group) < 3 or len(arc) < 2:
        return None
    out_bis = -np.array(c["bis"], float)
    rot = []
    cs = ring.project(Point(p))
    for _k, near, far in group:
        n = _edge_normal(ring, near, cs)
        if _ang(far - near, n) > ROT_DEG:
            rot.append(_signed_arc(ring, near, p))
    before = max(0.0, -min(rot)) if rot else 0.0
    after = max(0.0, max(rot)) if rot else 0.0
    _k, near_b, far_b = min(group, key=lambda g: _ang(g[2] - g[1], out_bis))
    steps = [float(np.hypot(*(b - a))) for a, b in zip(arc, arc[1:])]
    radii = [float(np.hypot(*(q - p))) / width for q in arc]
    grown = face.buffer(width, 64)
    over = max((grown.exterior.distance(Point(g[2])) if not grown.contains(Point(g[2])) else 0.0)
               for g in group)
    return {"p": [round(float(v), 2) for v in p], "turn": round(c["turn"]),
            "far_n": len(arc), "pitch": round(float(np.median(steps)), 2),
            "pitch_max": round(max(steps), 2),
            "radius": round(float(np.median(radii)), 2),
            "mitre": round(1.0 / max(math.cos(math.radians(c["turn"]) / 2.0), 0.2), 2),
            "rot_mm": [round(before, 2), round(after, 2)],
            "bis_deg": round(_ang(far_b - near_b, out_bis), 1),
            "over_mm": round(over, 2)}


def read_file(crosses, faces: list[Polygon], width: float) -> list[dict]:
    rows = []
    for fi, face in enumerate(faces):
        for c in convex_corners(face, width):
            r = read_corner(crosses, face, c, width)
            if r is not None:
                r["face"] = fi
                rows.append(r)
    return rows


def summary(rows: list[dict]) -> dict:
    if not rows:
        return {"corners": 0}
    med = lambda k: round(float(np.median([r[k] for r in rows])), 2)  # noqa: E731
    return {"corners": len(rows), "far_n": med("far_n"), "pitch": med("pitch"),
            "pitch_max": med("pitch_max"),
            "worst": round(max(r["pitch_max"] for r in rows), 2),
            "fans": sum(r["pitch_max"] > FAN_MM for r in rows),
            "radius": med("radius"), "mitre": med("mitre"),
            "rot_mm": round(float(np.median([sum(r["rot_mm"]) for r in rows])), 2),
            "bis_deg": med("bis_deg"), "over_mm": med("over_mm"),
            "over_max": round(max(r["over_mm"] for r in rows), 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", action="append", required=True,
                    help="RUNS.pkl#SID (repeat for arms: label=RUNS.pkl#SID)")
    ap.add_argument("--faces", required=True, help="GEN.pkl#SID[#holes]")
    ap.add_argument("--pro", help="FILE.dst@B1,B2")
    ap.add_argument("--width", type=float, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    faces = faces_from_pickle(a.faces)
    res = {}
    first_box = None
    for spec in a.ours:
        label, _, s = spec.rpartition("=")
        cr = crosses_of(runs_from_pickle(s))
        first_box = first_box or box_of(cr)
        rows = read_file(cr, faces, a.width)
        res[label or "ours"] = {"summary": summary(rows), "corners": rows}
    if a.pro:
        cr = crosses_of(runs_from_file(a.pro))
        pf = [snap(f, cr) for f in carry(faces, first_box, box_of(cr))]
        rows = read_file(cr, pf, a.width)
        res["pro"] = {"summary": summary(rows), "corners": rows}
    for k, v in res.items():
        print(k, json.dumps(v["summary"]))
    if a.out:
        a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
