"""Free ends and junction blobs of the satin skeleton, across the corpus —
the instrument for item 5, PR 2 (quality review 2026-09-08: serifs, oblique
caps, the junction cover).

The wide-column measurement (#434) left MARINE at 100 mm with 251 satin
self-crossing pairs and a story about serifs. This reads every stroke END
of every satin shape so the story is a table instead: what kind of end it
is, how far the skeleton stops short of the cap, whether the cap face is
SQUARE to the column's crosses or OBLIQUE to them, whether the artwork
FLARES along the cap face (a serif or a foot wider than its stem), and how
many crossing pairs sit at it -- with the pairs split into those WITHIN one
column (a column folding over itself, the defect the count was built for)
and those BETWEEN two columns (a mitre, which a pro's file is full of).
Per junction NODE it reads the bare artwork inside the node's blob, so a
crotch is a number.

Columns, per end:
  kind       free (the skeleton ends there) / capped (a corner the merge
             opened, see `Stroke.capped_*`) / junction
  reach_mm   skeleton end -> cap along the end tangent (free and capped)
  obliq_deg  angle between the cap face and the direction the column's
             crosses run there; 0 is a square cap, 40 is a 50 deg leg on a
             horizontal baseline
  flare      chord ALONG THE CAP FACE just inside the cap, over the chord
             in that same direction one stroke width further in; above 1
             the end widens toward the cap (a slab serif reads ~1.5), an
             oblique cap reads under 1 because the inner chord is the
             stroke's oblique section
  width_mm   the stroke's own width near the end (median chord across the
             tangent, one to three half-widths in)
  crossings  satin self-crossing pairs seated within 1.5 half-widths

Usage:
  python tools/letterforms.py [--widths 80 100] [--flag NAME[=VALUE] ...]
                              [--json PATH] [--ends N] [cases ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize                 # noqa: E402
from digitizer_core import stage6_satin as s6                      # noqa: E402
from digitizer_core import stage7_sequence as s7                   # noqa: E402
from digitizer_core.stitches import StitchRun, strip_ties          # noqa: E402
from curve_tiers import CASES                                       # noqa: E402
from thin_strokes import parse_flags                                # noqa: E402
from wide_columns import _seg_cross                                 # noqa: E402

ROOT = HERE.parent
OBLIQ_BINS = ((15.0, "<=15"), (30.0, "<=30"), (45.0, "<=45"), (90.0, ">45"))
FLARE_BINS = ((0.9, "<0.9"), (1.1, "<1.1"), (1.3, "<1.3"), (math.inf, ">=1.3"))
NEAR_HALFWIDTHS = 1.5
BARE_FLOOR_MM2 = 0.5


def end_frame(spine, at_start: bool, half_mm: float):
    """(skeleton end, outward unit tangent) — the tangent read as the chord
    back over one stroke width, the way `_extend_to_cap` reads a corner."""
    pts = list(reversed(spine)) if at_start else list(spine)
    tip = pts[-1]
    prev = pts[-2]
    walked = 0.0
    for j in range(len(pts) - 1, 0, -1):
        walked += math.dist(pts[j], pts[j - 1])
        prev = pts[j - 1]
        if walked >= 2.0 * half_mm:
            break
    d = math.dist(prev, tip)
    if d < 1e-9:
        return tip, None
    return tip, ((tip[0] - prev[0]) / d, (tip[1] - prev[1]) / d)


def chord_mm(poly, p, direction, reach: float) -> float:
    """Length of the polygon's chord through `p` along `direction` — the
    piece containing `p`, 0 when `p` is outside."""
    line = LineString([(p[0] - direction[0] * reach, p[1] - direction[1] * reach),
                       (p[0] + direction[0] * reach, p[1] + direction[1] * reach)])
    inter = line.intersection(poly)
    if inter.is_empty:
        return 0.0
    pt = Point(p)
    best = None
    for g in getattr(inter, "geoms", [inter]):
        if g.geom_type != "LineString" or g.length <= 0:
            continue
        dd = g.distance(pt)
        if best is None or dd < best[0]:
            best = (dd, g.length)
    return best[1] if best is not None and best[0] <= 1e-6 else 0.0


def cap_face(poly, tip, u, reach: float):
    """(cap point, unit direction of the cap face there, reach_mm) along the
    tangent from the skeleton end, or None when the ray finds no boundary.
    The face direction is the principal axis of the boundary within 0.75 mm
    of the hit, on a boundary densified to 0.1 mm — a raster ring's vertices
    are too sparse on a straight face and too dense on a staircase for a
    single segment to be the answer."""
    ray = LineString([tip, (tip[0] + u[0] * reach, tip[1] + u[1] * reach)])
    inter = ray.intersection(poly.boundary)
    if inter.is_empty:
        return None
    cands = []
    for g in getattr(inter, "geoms", [inter]):
        if g.geom_type == "Point":
            cands.append((g.x, g.y))
        else:
            cands.extend((c[0], c[1]) for c in g.coords)
    cands = [q for q in cands if (q[0] - tip[0]) ** 2 + (q[1] - tip[1]) ** 2 > 1e-8]
    if not cands:
        return None
    cap = min(cands, key=lambda q: (q[0] - tip[0]) ** 2 + (q[1] - tip[1]) ** 2)
    dense = poly.boundary.segmentize(0.1)
    near = []
    for g in getattr(dense, "geoms", [dense]):
        for c in g.coords:
            if (c[0] - cap[0]) ** 2 + (c[1] - cap[1]) ** 2 <= 0.75 ** 2:
                near.append(c)
    if len(near) < 3:
        return cap, None, math.dist(tip, cap)
    arr = np.asarray(near, float)
    arr -= arr.mean(axis=0)
    _w, v = np.linalg.eigh(arr.T @ arr)
    axis = v[:, -1]
    return cap, (float(axis[0]), float(axis[1])), math.dist(tip, cap)


def members(st: s6.Stroke) -> list[s6.Stroke]:
    """The columns `satin_stroke` sews for one stroke: the stroke itself, or
    its Goldman members (`_satin_joined`): at each corner the owner's end is
    a capped free end and the other member's end tucks under it."""
    if not st.corners:
        return [st]
    pts = st.spine
    edges_ = [0, *[c[0] for c in st.corners], len(pts) - 1]
    owners = [c[1] for c in st.corners]
    out = []
    for m, (s0, s1) in enumerate(zip(edges_, edges_[1:])):
        piece = pts[s0:s1 + 1]
        if len(piece) < 2:
            continue
        if m == 0:
            free_s, capped_s = st.free_start, st.capped_start
        elif owners[m - 1]:
            free_s, capped_s = False, False
        else:
            free_s, capped_s = True, True
        if m == len(edges_) - 2:
            free_e, capped_e = st.free_end, st.capped_end
        elif owners[m]:
            free_e, capped_e = True, True
        else:
            free_e, capped_e = False, False
        out.append(s6.Stroke(spine=piece, free_start=free_s, free_end=free_e, closed=False,
                             capped_start=capped_s, capped_end=capped_e))
    return out


def end_row(poly, st: s6.Stroke, at_start: bool, half_mm: float, field) -> dict:
    free = st.free_start if at_start else st.free_end
    capped = st.capped_start if at_start else st.capped_end
    kind = "junction" if not free else ("capped" if capped else "free")
    tip, u = end_frame(st.spine, at_start, half_mm)
    row = {"kind": kind, "at": (round(tip[0], 2), round(tip[1], 2)),
           "reach_mm": None, "obliq_deg": None, "flare": None, "width_mm": None}
    if u is None:
        return row
    v = (-u[1], u[0])
    reach = 20.0 * half_mm + 10.0
    # the stroke's own width: twice the medial radius along the spine one to
    # three half-widths in from the end -- a chord there escapes into the
    # next junction on every letter, the distance transform does not
    line = LineString(list(reversed(st.spine)) if at_start else st.spine)
    lo, hi = min(1.0 * half_mm, line.length), min(3.0 * half_mm, line.length)
    inner = [2.0 * field.half_at((q.x, q.y)) for q in
             (line.interpolate(lo + (hi - lo) * t / 6.0) for t in range(7))]
    inner = [w for w in inner if w > 0]
    width = float(np.median(inner)) if inner else None
    row["width_mm"] = round(width, 2) if width else None
    if kind == "junction":
        return row
    hit = cap_face(poly, tip, u, 6.0 * half_mm + 2.0)
    if hit is None:
        return row
    cap, face, reach_mm = hit
    row["reach_mm"] = round(reach_mm, 2)
    if face is None or width is None:
        return row
    obliq = math.degrees(math.acos(min(1.0, abs(face[0] * v[0] + face[1] * v[1]))))
    row["obliq_deg"] = round(obliq, 1)
    if obliq > 45.0:
        # the face runs closer to the column's own direction than across it:
        # a side, not a cap, and a chord along it is the stroke's length
        return row
    # the flare: along the cap face just inside the cap, over the same
    # direction one stroke width further in
    inset = min(0.4, 0.25 * reach_mm) if reach_mm > 0 else 0.4
    p_cap = (cap[0] - u[0] * inset, cap[1] - u[1] * inset)
    p_in = (cap[0] - u[0] * (inset + width), cap[1] - u[1] * (inset + width))
    w_cap = chord_mm(poly, p_cap, face, reach)
    w_in = chord_mm(poly, p_in, face, reach)
    row["flare"] = round(w_cap / w_in, 2) if w_cap > 0 and w_in > 0 else None
    return row


def crossing_seats(points, window: int = 40) -> list[tuple[tuple[float, float], float]]:
    """(midpoint, direction in radians) of the first segment of every
    properly crossing pair. The direction is what says which column laid
    the segment: a cross runs across ITS column, and two columns meeting at
    a corner lay their crosses at different angles."""
    p = np.asarray(points, float)
    if len(p) < 4:
        return []
    a, b = p[:-1], p[1:]
    n = len(a)
    out = []
    for k in range(2, min(window, n - 1) + 1):
        m = n - k
        hit = _seg_cross(a[:m], b[:m], a[k:k + m], b[k:k + m])
        for i in np.nonzero(hit)[0]:
            out.append((((a[i, 0] + b[i, 0]) / 2, (a[i, 1] + b[i, 1]) / 2),
                        math.atan2(b[i, 1] - a[i, 1], b[i, 0] - a[i, 0])))
    return out


def shape_rows(shape_id: str, poly, runs: list[StitchRun]) -> tuple[list[dict], list[dict]]:
    """-> (end rows, node rows) for one satin shape and its sewn runs."""
    strokes, half, field = s6.extract_strokes(poly)
    if not strokes or half <= 0 or field is None:
        return [], []
    ends: list[dict] = []
    for si, st in enumerate(strokes):
        for mi, member in enumerate(members(st)):
            length = sum(math.dist(a, b) for a, b in zip(member.spine, member.spine[1:]))
            for at_start in (True, False):
                r = end_row(poly, member, at_start, half, field)
                r.update({"shape_id": shape_id, "stroke": si, "member": mi,
                          "end": "start" if at_start else "end",
                          "stroke_len_mm": round(length, 1), "half_mm": round(half, 2),
                          "crossings": 0})
                ends.append(r)
    seats = []
    for run in runs:
        if run.kind == "satin":
            seats.extend(crossing_seats(s6.strip_splits(strip_ties(run.points))))
    near = NEAR_HALFWIDTHS * half
    unseated = 0
    # A seat belongs to the column that LAID the segment: among the members
    # whose spine passes within two half-widths of it, the one whose crosses
    # run nearest the segment's own direction -- two columns meeting at a
    # corner lay their crosses at different angles, and a cross is three
    # half-widths long, so its seat sits well off its own spine and often
    # nearer the other member's. Within that column, the nearer end when it
    # is within 1.5 half-widths of it, else the column's interior.
    axes: dict[tuple, LineString] = {}
    for si, st in enumerate(strokes):
        for mi, member in enumerate(members(st)):
            if len(member.spine) > 1:
                axes[(shape_id, si, mi)] = LineString(member.spine)
    for c, ang in seats:
        pt = Point(c)
        best_key, best_score = None, None
        for key, line in axes.items():
            if line.distance(pt) > 2.0 * near:
                continue
            s = line.project(pt)
            q0 = line.interpolate(max(0.0, s - half))
            q1 = line.interpolate(min(line.length, s + half))
            tangent = math.atan2(q1.y - q0.y, q1.x - q0.x)
            # the cross direction is the tangent turned a quarter; compare mod 180
            off = abs((ang - (tangent + math.pi / 2) + math.pi / 2) % math.pi - math.pi / 2)
            score = off + 0.05 * line.distance(pt)
            if best_score is None or score < best_score:
                best_key, best_score = key, score
        if best_key is None:
            unseated += 1
            continue
        cands = [e for e in ends if (e["shape_id"], e["stroke"], e["member"]) == best_key]
        best = min(cands, key=lambda e: math.dist(c, e["at"]))
        if math.dist(c, best["at"]) <= near:
            best["crossings"] += 1
        else:
            unseated += 1
    nodes: list[dict] = []
    junction_ends = [e for e in ends if e["kind"] == "junction"]
    if junction_ends:
        patches = s6._uncovered_patches(poly, runs, min_mm2=BARE_FLOOR_MM2)
        seen: set[tuple] = set()
        for e in junction_ends:
            key = (round(e["at"][0] / near), round(e["at"][1] / near))
            if key in seen:
                continue
            seen.add(key)
            # the patches come back grown by `_JUNCTION_PATCH_GROW_MM` so
            # they overlap their arms when sewn; the bare AREA is read with
            # that grow taken off again
            bare = sum(g.buffer(-s6._JUNCTION_PATCH_GROW_MM).area for g in patches
                       if math.dist((g.centroid.x, g.centroid.y), e["at"]) <= near)
            nodes.append({"shape_id": shape_id, "at": e["at"], "half_mm": e["half_mm"],
                          "bare_mm2": round(bare, 2)})
    for e in ends:
        e["unseated"] = unseated
        # the shape's bare artwork the grader would count: every patch over
        # the finder's floor, read with the sewing grow taken off again
        e["bare_total_mm2"] = round(sum(
            g.buffer(-s6._JUNCTION_PATCH_GROW_MM).area
            for g in s6._uncovered_patches(poly, runs)), 2)
    return ends, nodes


def scan(case: str, rel: str, kw: dict, width_mm: float | None, flags: dict) -> dict:
    seen: list[tuple[str, object]] = []
    real = s6.satin_shape
    real_stroke = s6.satin_stroke
    current: list[str] = [""]
    # Crossing pairs come in two kinds, and only one is a defect: a column
    # folding over ITSELF (the 2026-08-05 apex spray, the fan at a cap) and
    # two columns meeting at a corner or a junction, whose crosses run at
    # different angles through the same square -- which is what a mitred
    # join looks like, in a pro's file as much as here. The census keeps
    # them apart: `satin_stroke` is wrapped so every COLUMN's own points
    # (a plain stroke, or one member of a Goldman join) are counted on
    # their own, and the seam count is what the sewn run has beyond that.
    self_pairs: dict[str, int] = {}

    def spy_stroke(poly, stroke, *args, **kwargs):
        out = real_stroke(poly, stroke, *args, **kwargs)
        if not stroke.corners and out:
            self_pairs[current[0]] = self_pairs.get(current[0], 0) + \
                len(crossing_seats(s6.strip_splits(out)))
        return out

    def spy(poly, shape_id, **kwargs):
        seen.append((shape_id, poly))
        current[0] = shape_id
        return real(poly, shape_id, **kwargs)

    cfg = dict(kw)
    if width_mm is not None:
        cfg["target_width_mm"] = width_mm
    cfg.update(flags)
    s7.satin_shape = spy
    s6.satin_stroke = spy_stroke
    try:
        _result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**cfg))
    finally:
        s7.satin_shape = real
        s6.satin_stroke = real_stroke
    by_shape: dict[str, list[StitchRun]] = {}
    for _b, run in plan.iter_runs():
        by_shape.setdefault(run.shape_id, []).append(run)
    out = {"case": case, "width_mm": cfg.get("target_width_mm"), "flags": flags,
           "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
           "shapes": len(seen), "ends": [], "nodes": [], "self_pairs": 0, "seam_pairs": 0,
           "by_shape": {}, "bare_total_mm2": 0.0}
    for shape_id, poly in seen:
        ends, nodes = shape_rows(shape_id, poly, by_shape.get(shape_id, []))
        out["ends"].extend(ends)
        out["nodes"].extend(nodes)
        if ends:
            out["bare_total_mm2"] = round(out["bare_total_mm2"] + ends[0]["bare_total_mm2"], 2)
        total = sum(len(crossing_seats(s6.strip_splits(strip_ties(r.points))))
                    for r in by_shape.get(shape_id, []) if r.kind == "satin")
        own = self_pairs.get(shape_id, 0)
        out["by_shape"][shape_id] = {"self": own, "seam": max(0, total - own), "total": total}
        out["self_pairs"] += own
        out["seam_pairs"] += max(0, total - own)
    return out


def _bin(value, bins):
    if value is None:
        return "n/a"
    for hi, label in bins:
        if value <= hi if bins is OBLIQ_BINS else value < hi:
            return label
    return bins[-1][1]


def summarize(r: dict, n_ends: int) -> str:
    ends = r["ends"]
    kinds = Counter(e["kind"] for e in ends)
    x_kind = Counter()
    for e in ends:
        x_kind[e["kind"]] += e["crossings"]
    caps = [e for e in ends if e["kind"] != "junction"]
    ob = Counter(); ob_x = Counter(); fl = Counter(); fl_x = Counter()
    for e in caps:
        b = _bin(e["obliq_deg"], OBLIQ_BINS)
        ob[b] += 1; ob_x[b] += e["crossings"]
        f = _bin(e["flare"], FLARE_BINS)
        fl[f] += 1; fl_x[f] += e["crossings"]
    total_x = sum(e["crossings"] for e in ends) + (ends[0]["unseated"] if ends else 0)
    lines = [f"== {r['case']:12} {r['width_mm'] or 'default':>7} mm  shapes {r['shapes']:3}  "
             f"ends {len(ends):4} ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))})  "
             f"stitches {r['stitches']}  trims {r['trims']}  bare over the floor {r['bare_total_mm2']} mm2  "
             f"crossing pairs {total_x}: within a column {r['self_pairs']}, between columns {r['seam_pairs']} "
             f"(seated: {', '.join(f'{k} {v}' for k, v in sorted(x_kind.items()))})",
             "     caps by obliquity: " + "  ".join(f"{lab}: {ob[lab]} ends / {ob_x[lab]} pairs"
                                                    for _h, lab in OBLIQ_BINS) + f"  n/a: {ob['n/a']}",
             "     caps by flare:     " + "  ".join(f"{lab}: {fl[lab]} ends / {fl_x[lab]} pairs"
                                                    for _h, lab in FLARE_BINS) + f"  n/a: {fl['n/a']}"]
    flared = sorted((e for e in caps if e["flare"] is not None and e["flare"] >= 1.3),
                    key=lambda e: -e["flare"])
    if flared:
        lines.append("     flared ends: " + "; ".join(
            f"{e['shape_id']} s{e['stroke']}m{e['member']}.{e['end'][0]} flare {e['flare']} w {e['width_mm']} "
            f"reach {e['reach_mm']} obliq {e['obliq_deg']}" for e in flared[:6]))
    worst = sorted(ends, key=lambda e: -e["crossings"])[:n_ends]
    for e in worst:
        if e["crossings"] <= 0:
            break
        lines.append(f"     {e['shape_id']} s{e['stroke']}m{e['member']}.{e['end'][0]:1} {e['kind']:8} pairs {e['crossings']:3}  "
                     f"w {e['width_mm']}  reach {e['reach_mm']}  obliq {e['obliq_deg']}  flare {e['flare']}  "
                     f"len {e['stroke_len_mm']}  at {e['at']}")
    bare = sorted((n for n in r["nodes"] if n["bare_mm2"] >= BARE_FLOOR_MM2), key=lambda n: -n["bare_mm2"])
    if bare:
        lines.append("     bare junction blobs: " + "; ".join(
            f"{n['shape_id']} at {n['at']} {n['bare_mm2']} mm2" for n in bare[:8]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--widths", type=float, nargs="*", default=None,
                    help="design widths to digitize at; default: each case's own")
    ap.add_argument("--flag", action="append", default=[],
                    help="PipelineConfig field to set, NAME or NAME=VALUE; repeatable")
    ap.add_argument("--json", default=None)
    ap.add_argument("--ends", type=int, default=6, help="worst ends to list per case")
    a = ap.parse_args(argv)
    flags = parse_flags(a.flag)
    names = a.cases or list(CASES)
    print(f"satin stroke ends and junction blobs — flags {flags or 'default'}")
    report = []
    for name in names:
        rel, kw = CASES[name]
        for w in (a.widths or [None]):
            kw2 = {k: v for k, v in kw.items() if not (w is not None and k == "target_width_mm")}
            r = scan(name, rel, kw2, w, flags)
            report.append(r)
            print(summarize(r, a.ends), flush=True)
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
