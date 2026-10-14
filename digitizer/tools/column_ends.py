"""Column END shapes in the lettering Column lane: how each column ends against
the letter's own outline, OFF vs `cfg.lettering_columns_square_ends`.

Kent, 2026-10-13: "we need to work on lettering and how they start / end".
The Fremont 81 mm Hat triage (`tools/fremont_triage.py`, PR #898) traced three
of his circles to Column-lane END shapes: HOTEL's E upper arm ends in a
slanted stub (circle 5), FREMONT's M vertex sews a wedge (circle 6) and the
N's diagonal ends in a stub past its stem foot (circle 7).

Per letter, on the lane's own construction (`outline_cut.letter_columns`):

- an END-FACE penetration is a cross end that starts ON an outline edge
  running ACROSS its column there (more than `columns.END_FACE_DEG` off the
  column's direction), or on a TERMINAL face of the letter (an edge some
  column's end cross lies along: `columns.end_faces`). Every other cross end
  is on a side, and a side is pulled out on purpose.
- `stub_mm` (per column end): how far the furthest of that end's end-face
  penetrations stands OUTSIDE the outline once the fabric's pull is applied
  (`columns.sewn_rails`, the lane's own step 1). An end with no end-face
  penetration is at a cut and is not listed.
- `cap_deg`: the angle between the end's last sewn cross and the face nearest
  it, 0 (along the face: square or mitred to it) to 90.
- `fan`: construction crosses in the end's last six that share a pivot with
  the one before; `crossings`: sewn zigzag segments of OTHER columns within
  1.6 W of the end that cross this one's (overlap at a vertex or a tuck).
- An end OVERSHOOTS when `stub_mm` > `--tol` (`TOL_MM`, a CANDIDATE: under
  half a 40 wt thread's laid width, so a penetration that close to the face
  reads as on it; nothing here is sewn, ROADMAP gate 1).

And, on what the lane actually SEWS (every satin leg as `columns._satin_points`
receives it, tucks included -- independent of the face rule):

- `beyond_reach`: satin penetrations further outside the outline than the
  rails' own side reach (`pull_mm - columns.RAIL_REACH_INSET_MM`) plus
  0.02 mm -- a tuck run out of the letter, a fan face reached past a cut;
- `travel_off_mm`: needle-down travel and underlay further outside the outline
  than that reach, i.e. over bare fabric;
- `bare_mm2`: outline area no satin stitch's thread covers (each zigzag
  stitch read `THREAD_HALF_MM` either side) -- the price of holding a face.

Fremont is an UNREPRESENTATIVE fixture: reproduce defects on it, never size a
constant on it. Measurement only; the flag stays OFF.

    # one fixture, OFF then ON, writes <out>/<name>.json
    .venv/Scripts/python -m tools.column_ends --fixture becker --out DIR
    # Kent's Fremont replay (81 mm, Hat, the Studio request) + zoom panels
    .venv/Scripts/python -m tools.column_ends --fremont81 --out DIR --renders DIR2
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTDATA = ROOT / "testdata"

TOL_MM = 0.10           # candidate overshoot tolerance past an end face
FAN_ZONE = 6            # last crosses read for a fan
ZONE_WIDTHS = 1.6       # neighbourhood of an end, in letter stroke widths
REACH_SLACK_MM = 0.02   # float slack over the side reach for `beyond_reach`
THREAD_HALF_MM = 0.2    # half the render's laid thread (`stitchviz.THREAD_MM` 0.4)

# The corpus check (name -> fixture, request). Widths: the scorecard's 80 mm
# left chest; golden_tee at #869's 50 mm and fremont at the pro's 92.5 mm.
CORPUS = {
    "becker": ("becker_marine_logo.png", {"target_width_mm": 80.0, "garment_id": "left_chest"}),
    "bridge": ("photo/logo_bridge_bar.jpg", {"target_width_mm": 80.0, "garment_id": "left_chest"}),
    "fremont92": ("photo/logo_hotel_fremont.webp", {"target_width_mm": 92.5, "garment_id": "left_chest"}),
    "golden_tee": ("photo/logo_golden_tee.jpg", {"target_width_mm": 50.0, "garment_id": "left_chest"}),
    "drone": ("photo/drone_render.png", {"target_width_mm": 80.0, "garment_id": "left_chest"}),
}

# Kent's three end circles on the 81 mm replay: shape ids of the letters
# (`fremont_triage` census, main) and the triage's own boxes.
FREMONT_ENDS = {
    "accent_e": ("Se394be84", "5. HOTEL's E: upper arm end"),
    "m_o_junction": ("S9a48e915", "6. FREMONT's M: the vertex (M->O)"),
    "final_t": ("Sd4bf6420", "7. FREMONT's N: diagonal foot"),
}


# --- one letter ----------------------------------------------------------------

def _lane(poly, kw: dict, square_ends: bool, inside_connectors: bool = False):
    """The lane on one letter, its sewn legs captured. -> (runs, report, legs, cut)."""
    from digitizer_core import columns as C
    from digitizer_core.outline_cut import letter_columns

    legs: list[list] = []
    real = C._satin_points

    def spy(stations, *a, **k):
        legs.append([(tuple(p), tuple(q)) for p, q in stations])
        return real(stations, *a, **k)

    kw = {k: v for k, v in kw.items() if k not in ("square_ends", "inside_connectors")}
    C._satin_points = spy
    try:
        runs, report = C.lettering_columns_shape(
            poly, "census", **kw,
            **({"square_ends": True} if square_ends else {}),
            **({"inside_connectors": True} if inside_connectors else {}))
    finally:
        C._satin_points = real
    cut = letter_columns(poly, pitch_mm=kw.get("spacing_mm", 0.4),
                         fold_cuts=bool(kw.get("fold_cuts", False)),
                         **({"mitre_ends": True} if square_ends else {}))
    return runs, report, legs, cut


def _angle(u, v) -> float:
    """Unsigned angle between two LINES, 0..90 deg."""
    c = abs(u[0] * v[0] + u[1] * v[1]) / max(math.hypot(*u) * math.hypot(*v), 1e-12)
    return math.degrees(math.acos(min(1.0, c)))


def _past_line(p, edge, outline) -> float:
    """Signed distance of `p` from the infinite line through `edge`,
    positive on the side away from the letter."""
    from shapely.geometry import Point
    (ax, ay), (bx, by), (ux, uy) = edge
    nx, ny = -uy, ux
    mx, my = (ax + bx) / 2, (ay + by) / 2
    if outline.covers(Point(mx + nx * 0.01, my + ny * 0.01)):
        nx, ny = -nx, -ny
    return (p[0] - ax) * nx + (p[1] - ay) * ny


def letter_ends(poly, kw: dict, square_ends: bool = False, tol_mm: float = TOL_MM,
                inside_connectors: bool = False) -> dict:
    """Every outline END of one letter's columns (see the module docstring)."""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    from digitizer_core import columns as C, stitches

    runs, report, legs, cut = _lane(poly, kw, square_ends, inside_connectors)
    outline = cut.poly
    edges = C._ring_edges(outline)
    lim = math.cos(math.radians(C.END_FACE_DEG))
    W = cut.W
    R = ZONE_WIDTHS * W
    pull = kw.get("pull_mm", 0.0)
    terminal = set(C.end_faces(cut.columns, outline))
    hold = C.end_face_hold(cut.columns, outline) if square_ends else None
    segs = []                                   # (leg, (p, q)) in zigzag order
    for li, leg in enumerate(legs):
        flat = [p for st in leg for p in st]
        segs.extend((li, (flat[k], flat[k + 1])) for k in range(len(flat) - 1))

    ends = []
    for ci, col in enumerate(cut.columns):
        n = len(col.stations)
        if n < 2:
            continue
        dirs = C._station_dirs(col)
        a1, b1 = C.sewn_rails(col, outline, pull, kw.get("pull_floor_mm", 0.0), hold)
        per_end = {"first": [], "last": []}     # (station, face edge, distance outside)
        for i, ((a0, b0), d) in enumerate(zip(col.stations, dirs)):
            for p0, p1 in ((a0, a1[i]), (b0, b1[i])):
                near = [k for k, e in enumerate(edges) if C._seg_dist(p0, e) <= C._FACE_EPS_MM]
                faces = [k for k in near
                         if abs(d[0] * edges[k][2][0] + d[1] * edges[k][2][1]) < lim or k in terminal]
                if not faces:
                    continue
                # how far past the face's own LINE, outward: a square cap's
                # corner pushed along its face (the column's side pull) stays
                # on that line and is no stub
                k = min(faces, key=lambda k: C._seg_dist(p0, edges[k]))
                out = max(0.0, _past_line(p1, edges[k], outline))
                per_end["first" if i < n / 2 else "last"].append((i, k, out))
        for end, hits in per_end.items():
            if not hits:
                continue                        # this end is at a cut
            i = 0 if end == "first" else n - 1
            mid0 = ((col.stations[i][0][0] + col.stations[i][1][0]) / 2,
                    (col.stations[i][0][1] + col.stations[i][1][1]) / 2)
            fk = min({h[1] for h in hits}, key=lambda k: C._seg_dist(mid0, edges[k]))
            cap = _angle((b1[i][0] - a1[i][0], b1[i][1] - a1[i][1]), edges[fk][2]) \
                if math.dist(a1[i], b1[i]) > 1e-9 else None
            order = list(range(n)) if end == "first" else list(range(n))[::-1]
            fz = order[:FAN_ZONE]
            fan = sum(1 for x, y in zip(fz, fz[1:])
                      if set(col.stations[x]) & set(col.stations[y]))
            near_segs = [s for s in segs if math.dist(s[1][0], mid0) <= R and math.dist(s[1][1], mid0) <= R]
            crossings = 0
            for x in range(len(near_segs)):
                for y in range(x + 1, len(near_segs)):
                    (l1, s1), (l2, s2) = near_segs[x], near_segs[y]
                    if l1 != l2 and not (set(s1) & set(s2)) and LineString(s1).crosses(LineString(s2)):
                        crossings += 1
            stub = float(max(h[2] for h in hits))
            ends.append({"column": ci, "end": end, "kind": col.kind,
                         "at_mm": [round(float(mid0[0]), 2), round(float(mid0[1]), 2)],
                         "stub_mm": round(stub, 3),
                         "cap_deg": None if cap is None else round(float(cap), 1),
                         "fan": fan, "crossings": crossings,
                         "overshoot": bool(stub > tol_mm)})
    reach = max(0.0, pull - C.RAIL_REACH_INSET_MM)
    beyond = [float(outline.boundary.distance(Point(p))) for leg in legs for st in leg for p in st
              if not outline.covers(Point(p))]
    # past the whole pull: further than any rail's own push can take it (a
    # cross under 0.44 mm is inset by a quarter of itself, not by the 0.11,
    # so its side push legitimately passes `reach`)
    beyond_pull = sum(1 for d in beyond if d > pull + REACH_SLACK_MM)
    beyond = [d for d in beyond if d > reach + REACH_SLACK_MM]
    grown = outline.buffer(reach + 1e-6)
    laid = unary_union([LineString(s[1]).buffer(THREAD_HALF_MM) for s in segs]) if segs else None
    bare = outline.area if laid is None else outline.difference(laid).area
    # over BARE fabric: outside both the grown outline and the letter's own
    # laid satin (a thin cross's rail is pushed past `reach`, and a hop from
    # it runs on satin, not on cloth)
    cloth = grown if laid is None else grown.union(laid)
    travel = [LineString(r.points) for r in runs
              if r.kind in (stitches.TRAVEL, stitches.UNDERLAY) and len(r.points) >= 2]
    # the needle-down stitch from one run's last point to the next run's
    # first, where the link rule sewed it (no jump): not part of any run
    links = [LineString([r0.points[-1], r1.points[0]]) for r0, r1 in zip(runs, runs[1:])
             if not r1.jump and math.dist(r0.points[-1], r1.points[0]) > 1e-9]
    travel_off = sum(t.difference(grown).length for t in travel)
    link_off = sum(t.difference(grown).length for t in links)
    connector_bare = sum(t.difference(cloth).length for t in travel + links)
    return {"W_mm": round(float(W), 3), "ends": ends,
            "overshoots": sum(e["overshoot"] for e in ends),
            "worst_stub_mm": round(max((e["stub_mm"] for e in ends), default=0.0), 3),
            "beyond_reach": len(beyond),
            "beyond_reach_max_mm": round(max(beyond, default=0.0), 3),
            "beyond_pull": beyond_pull,
            "travel_off_mm": round(travel_off, 3),
            "link_off_mm": round(link_off, 3),
            "connector_bare_mm": round(connector_bare, 3),
            "bare_mm2": round(bare, 3),
            "stitches": sum(len(r.points) for r in runs),
            "jumps": report.get("jumps", 0),
            "trims": sum(1 for r in runs if r.trim)}


# --- whole designs ---------------------------------------------------------------

def capture(fixture: str, cfg_kw: dict, overrides: dict | None = None):
    """Run the pipeline the scorecard way and record every Column-lane call.
    -> (calls [(poly, shape_id, kw)], plan, design)."""
    from digitizer_core import PipelineConfig
    from digitizer_core import stage7_sequence as s7
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import plan_stitches, run_stages

    calls = []
    real = s7.lettering_columns_shape

    def spy(poly, shape_id, **kw):
        runs, report = real(poly, shape_id, **kw)
        if not report.get("empty"):
            calls.append((poly, shape_id, dict(kw)))
        return runs, report

    s7.lettering_columns_shape = spy
    try:
        res = run_stages(str(TESTDATA / fixture), PipelineConfig(**{**cfg_kw, **(overrides or {})}))
        plan = plan_stitches(res, PipelineConfig(**{**cfg_kw, **(overrides or {})}))
    finally:
        s7.lettering_columns_shape = real
    return calls, plan, plan_to_design(plan)


def design_census(calls, square_ends: bool, tol_mm: float = TOL_MM,
                  inside_connectors: bool = False) -> dict:
    rows = {}
    for poly, sid, kw in calls:
        rows[sid] = letter_ends(poly, kw, square_ends=square_ends, tol_mm=tol_mm,
                                inside_connectors=inside_connectors)
    return {
        "letters": len(rows),
        "ends": sum(len(r["ends"]) for r in rows.values()),
        "overshoots": sum(r["overshoots"] for r in rows.values()),
        "worst_stub_mm": round(max((r["worst_stub_mm"] for r in rows.values()), default=0.0), 3),
        "beyond_reach": sum(r["beyond_reach"] for r in rows.values()),
        "beyond_reach_max_mm": round(max((r["beyond_reach_max_mm"] for r in rows.values()), default=0.0), 3),
        "beyond_pull": sum(r["beyond_pull"] for r in rows.values()),
        "travel_off_mm": round(sum(r["travel_off_mm"] for r in rows.values()), 2),
        "link_off_mm": round(sum(r["link_off_mm"] for r in rows.values()), 2),
        "connector_bare_mm": round(sum(r["connector_bare_mm"] for r in rows.values()), 2),
        "letter_jumps": sum(r["jumps"] for r in rows.values()),
        "letter_trims": sum(r["trims"] for r in rows.values()),
        "bare_mm2": round(sum(r["bare_mm2"] for r in rows.values()), 2),
        "crossings": sum(e["crossings"] for r in rows.values() for e in r["ends"]),
        "fan_ends": sum(1 for r in rows.values() for e in r["ends"] if e["fan"]),
        "per_letter": rows,
    }


def fixture_census(name: str, tol_mm: float = TOL_MM, full_on: bool = False) -> dict:
    """A CORPUS fixture: one whole-design OFF run records every letter the
    Column lane takes (polygon and arguments); both arms are then measured
    by re-running the lane on those letters, OFF and ON. The ON arm so
    reads each letter from the needle position the OFF run handed it -- the
    flag changes a letter's ends, not which letters the lane takes. With
    `full_on` the ON arm is a whole-design run of its own instead (slower)."""
    fixture, cfg_kw = CORPUS[name]
    calls, plan, design = capture(fixture, cfg_kw)
    s = plan.stats
    out = {"fixture": fixture, "request": cfg_kw, "tol_mm": tol_mm,
           "off": {"stitches": s.stitch_count, "trims": s.trims, "jumps": s.jumps,
                   "design_md5": _md5(design), **design_census(calls, False, tol_mm)}}
    if full_on:
        calls, plan, design = capture(fixture, cfg_kw, {"lettering_columns_square_ends": True})
        s = plan.stats
        out["on"] = {"stitches": s.stitch_count, "trims": s.trims, "jumps": s.jumps,
                     "design_md5": _md5(design), **design_census(calls, True, tol_mm)}
    else:
        out["on"] = {"replayed_on_off_calls": True, **design_census(calls, True, tol_mm)}
    return out


def _md5(design: dict) -> str:
    import hashlib
    return hashlib.md5(json.dumps(design["stitches"]).encode()).hexdigest()


# --- Kent's replay ----------------------------------------------------------------

def fremont81(out: Path, renders: Path | None, tol_mm: float = TOL_MM,
              arms: tuple[str, ...] = ()) -> dict:
    """The triage's exact replay (Studio request, 81 mm, Hat), OFF and ON;
    per-letter end census on the three circled letters, and zoom panels."""
    from tools import fremont_triage as ft
    from digitizer_core import stage7_sequence as s7

    res = {}
    designs = {}
    for arm, ov in (("off", {}), ("on", {"lettering_columns_square_ends": True})):
        if arms and arm not in arms:
            continue
        ft.ARMS[f"square_ends_{arm}"] = ov
        calls = []
        real = s7.lettering_columns_shape

        def spy(poly, shape_id, **kw):
            calls.append((poly, shape_id, dict(kw)))
            return real(poly, shape_id, **kw)

        s7.lettering_columns_shape = spy
        try:
            run = ft.run_arm(f"square_ends_{arm}", preflight=False)
        finally:
            s7.lettering_columns_shape = real
        p = run["gen"].p
        boxes = {k: ft.roi_mm(p, ft.ROIS[k]) for k in FREMONT_ENDS}
        by_sid = {sid: (poly, kw) for poly, sid, kw in calls}
        circles = {}
        for key, (sid, title) in FREMONT_ENDS.items():
            poly, kw = by_sid[sid]
            circles[key] = {"shape_id": sid, "title": title,
                            **letter_ends(poly, kw, square_ends=bool(ov), tol_mm=tol_mm)}
        s = run["plan"].stats
        designs[arm] = (run["design"], boxes)
        res[arm] = {"stitches": s.stitch_count, "trims": s.trims, "jumps": s.jumps,
                    "design_md5": _md5(run["design"]), "circles": circles,
                    **{k: v for k, v in design_census(calls, bool(ov), tol_mm).items() if k != "per_letter"}}
        out.mkdir(parents=True, exist_ok=True)
        (out / f"fremont81_{arm}.json").write_text(json.dumps(res[arm], indent=1))
        (out / f"fremont81_{arm}_design.json").write_text(json.dumps({"design": run["design"], "boxes": boxes}))
        if arm == "off":
            # the three circled letters as the lane received them, for the tests
            (out / "fremont81_end_letters.json").write_text(json.dumps({
                key: {"shape_id": sid,
                      "exterior": [list(map(float, c)) for c in by_sid[sid][0].exterior.coords],
                      "holes": [[list(map(float, c)) for c in r.coords] for r in by_sid[sid][0].interiors],
                      "kw": {k: (list(map(float, v)) if isinstance(v, tuple) else v)
                             for k, v in by_sid[sid][1].items()}}
                for key, (sid, _t) in FREMONT_ENDS.items()}, indent=1))
    if renders is not None:
        zoom_panels(load_designs(out), renders)
    return res


def load_designs(out: Path) -> dict:
    designs = {}
    for arm in ("off", "on"):
        p = out / f"fremont81_{arm}_design.json"
        if p.exists():
            d = json.loads(p.read_text())
            designs[arm] = (d["design"], {k: tuple(v) for k, v in d["boxes"].items()})
    return designs


def zoom_panels(designs: dict, renders: Path, px_per_mm: float = 40.0, zoom_px_per_mm: float = 120.0):
    """One panel per circle: artwork | OFF | ON at `px_per_mm`, then a zoom
    of the letter's end at `zoom_px_per_mm` (detail under 1 mm)."""
    import cv2
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    written = []
    rend = {arm: ft._render(d, px_per_mm) for arm, (d, _b) in designs.items()}
    zr = {arm: ft._render(d, zoom_px_per_mm) for arm, (d, _b) in designs.items()}
    for key, (sid, title) in FREMONT_ENDS.items():
        cols = []
        crop0 = None
        for arm in designs:
            img, tp = rend[arm]
            box = designs[arm][1][key]
            c = ft._crop(img, tp, box)
            crop0 = crop0 if crop0 is not None else c
            cols.append(ft._label(c, f"square_ends {arm.upper()}"))
        src = ft._source_crop(ft.ROIS[key], crop0.shape[0])
        panel = ft._label(ft._hstack([ft._label(src, "artwork")] + cols), title)
        zooms = []
        for arm in designs:
            img, tp = zr[arm]
            x0, y0, x1, y1 = designs[arm][1][key]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            zb = ZOOM_BOX[key]
            c = ft._crop(img, tp, (cx + zb[0], cy + zb[1], cx + zb[2], cy + zb[3]), margin_mm=0.0)
            zooms.append(ft._label(c, f"zoom {arm.upper()} ({zoom_px_per_mm:g} px/mm)"))
        z = ft._hstack(zooms)
        w = max(panel.shape[1], z.shape[1])
        import numpy as np
        pad = lambda im: np.pad(im, ((0, 6), (0, w - im.shape[1]), (0, 0)), constant_values=255)
        p = renders / f"{key}.png"
        cv2.imwrite(str(p), np.vstack([pad(panel), pad(z)]))
        written.append(p)
    return written


def word_panel(name: str, renders: Path, px_per_mm: float = 60.0) -> Path:
    """A corpus fixture's lane letters, OFF above ON, whole-design runs of
    each arm, cropped to the letters the OFF run gave the lane."""
    import cv2
    import numpy as np
    from shapely.ops import unary_union
    from tools import fremont_triage as ft
    fixture, cfg_kw = CORPUS[name]
    rows = []
    box = None
    for arm, ov in (("off", {}), ("on", {"lettering_columns_square_ends": True})):
        calls, plan, design = capture(fixture, cfg_kw, ov)
        if box is None:
            box = unary_union([p for p, _s, _k in calls]).bounds
        img, tp = ft._render(design, px_per_mm)
        s = plan.stats
        rows.append(ft._label(ft._crop(img, tp, box, margin_mm=0.8),
                              f"{name} square_ends {arm.upper()}: {s.stitch_count:,} stitches, {s.trims} trims"))
    w = max(r.shape[1] for r in rows)
    out = np.vstack([np.pad(r, ((0, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    renders.mkdir(parents=True, exist_ok=True)
    p = renders / f"{name}_word.png"
    cv2.imwrite(str(p), out)
    return p


# Zoom windows, mm offsets from the circle box's centre (x0, y0, x1, y1).
ZOOM_BOX = {
    "accent_e": (0.0, -3.4, 3.4, -0.6),
    "m_o_junction": (-2.2, 0.0, 2.6, 3.6),
    "final_t": (-3.0, 0.0, 1.0, 3.6),
}


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fixture", choices=sorted(CORPUS))
    ap.add_argument("--fremont81", action="store_true")
    ap.add_argument("--arm", choices=("off", "on"), action="append",
                    help="with --fremont81: run only this arm (repeatable; default both)")
    ap.add_argument("--full-on", action="store_true",
                    help="with --fixture: digitize the ON arm too, instead of replaying the OFF run's letters")
    ap.add_argument("--panels", action="store_true",
                    help="render the zoom panels from saved --fremont81 arms, digitizing nothing")
    ap.add_argument("--word", choices=sorted(CORPUS),
                    help="render that fixture's lane letters OFF above ON (two whole-design runs)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--renders", type=Path)
    ap.add_argument("--tol", type=float, default=TOL_MM)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    a.out.mkdir(parents=True, exist_ok=True)
    if a.fremont81:
        r = fremont81(a.out, None, a.tol, tuple(a.arm or ()))
        for arm, row in r.items():
            print(arm, {k: v for k, v in row.items() if k != "circles"})
            for key, c in row["circles"].items():
                print(f"  {key}: overshoots {c['overshoots']} worst stub {c['worst_stub_mm']} mm "
                      f"beyond reach {c['beyond_reach']} travel off {c['travel_off_mm']} mm")
    if a.word:
        print(word_panel(a.word, a.renders or a.out / "renders"))
    if a.panels:
        for p in zoom_panels(load_designs(a.out), a.renders or a.out / "renders"):
            print(p)
    if a.fixture:
        r = fixture_census(a.fixture, a.tol, a.full_on)
        (a.out / f"{a.fixture}.json").write_text(json.dumps(r, indent=1))
        for arm in ("off", "on"):
            if arm in r:
                print(a.fixture, arm, {k: v for k, v in r[arm].items() if k != "per_letter"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
