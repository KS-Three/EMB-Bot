"""The Column object and its construction engine for traced lettering.

A Column is what an `.embf` glyph already is (`src/satinplay.js`: two rails
plus rungs, "no skeletonization, no guessing"): a list of STATIONS, each a
rail-to-rail cross `(pa, pb)` in mm, plus the piece of the letter it covers.
`outline_cut.letter_columns` produces them from a traced letter; this module
turns them into stitches with the rules a typed glyph gets and a traced one
never did (`docs/lettering-route-review-2026-09-19.md` §3, the construction
gap; `docs/lettering-architecture-rd-2026-10-07.md` §5 L5, Kent's pick
2026-10-07: port the glyph rules to Python rather than play Columns back in
the Studio).

What this first cut carries, and what it does not (each later rule is a
measured step on the MARINE yardstick, not a guess):

- pull compensation on the RAILS, per side, by the fabric's own
  `pull_comp_mm`, held back across a counter (`stage6_satin._push_rails`,
  the same function the shipped satin tier uses, on the same artwork
  polygon);
- the cross floor (`machine.SATIN_MIN_CROSS_MM`): a cross the needle cannot
  resolve is dropped and counted, never sewn as a smear;
- split satin above `split_above_mm` with the column-wide comb
  (`_comb_thresholds`, `_split_points`: Kent's 2026-09-30 "smooth and flow"
  rule), so a wide stem is a split column, never a fill;
- a centre-run underlay per column where the letter is large enough for
  underlay at all (the caller passes "none" under
  `machine.SATIN_UNDERLAY_MIN_EXTENT_MM`, as it does for the satin tier);
- the nearest-next order between a letter's columns, each column entered at
  the end nearer the needle, and the shipped sew-or-jump rule between runs
  (a short hop inside the letter is a stitch, a long one or one over bare
  fabric a jump, a jump past `trim_at_mm` a trim).

NOT yet: the Euler walk across a letter's columns (`satinfont.js`
`routeGlyph`; the single biggest trim lever, the route review's 41 vs 3),
junction overlap between a butting column and the one it butts, short
stitches on the inside of a bend, tie stitches, an edge-walk underlay for
tall caps. Every one of those is a Column consumer and goes here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, Polygon

from . import machine, stitches
from .stitches import StitchRun


@dataclass
class Column:
    """One satin column of a letter: rail-to-rail crosses in sew order."""

    stations: list[tuple[tuple[float, float], tuple[float, float]]]
    piece: Polygon                      # the stroke piece these crosses cover
    kind: str                           # "straight" | "curved" | "ring"
    axis: tuple[float, float] | None    # unit axis of a straight piece
    width_mm: float                     # the letter's mean stroke width
    rail_a: list[tuple[float, float]] = field(default_factory=list)
    rail_b: list[tuple[float, float]] = field(default_factory=list)

    @property
    def start(self) -> tuple[float, float]:
        a, b = self.stations[0]
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    @property
    def end(self) -> tuple[float, float]:
        a, b = self.stations[-1]
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    def reversed(self) -> "Column":
        return Column(stations=self.stations[::-1], piece=self.piece, kind=self.kind,
                      axis=self.axis, width_mm=self.width_mm,
                      rail_a=self.rail_a[::-1], rail_b=self.rail_b[::-1])


def _pick_nearest(left: list[Column], cursor) -> Column:
    """The column with an end nearest the needle, oriented to start there."""
    if cursor is None:
        return left[0]
    best = None
    for c in left:
        for flip, p in ((False, c.start), (True, c.end)):
            d = math.dist(cursor, p)
            if best is None or d < best[0]:
                best = (d, c, flip)
    _, pick, flip = best
    return pick.reversed() if flip else pick


def _underlay_run(stations, shape_id: str) -> StitchRun | None:
    """A centre run down the column's stations, inset from both ends, at
    the structural underlay stitch length."""
    mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in stations]
    ln = LineString(mids)
    inset = 0.4
    if ln.length <= 2 * inset + machine.TINY_STITCH_MM:
        return None
    n = max(2, int(math.ceil((ln.length - 2 * inset) / machine.UNDERLAY_STITCH_MM)) + 1)
    pts = [ln.interpolate(inset + (ln.length - 2 * inset) * k / (n - 1)).coords[0] for k in range(n)]
    return StitchRun(points=pts, kind=stitches.UNDERLAY, shape_id=shape_id)


def is_lettering(region) -> bool:
    """Does the lane take this shape? Either tagger says lettering: the text
    cluster (`textcluster.tag`, `text_candidate`) or the house-angle group
    (`set_lettering_house_angle`, `lettering_group`). The two disagree on
    real logos and merging them is the architecture's L1; until then the
    lane reads both."""
    m = region.meta or {}
    return bool(m.get("text_candidate") or m.get("lettering_group"))


def column_runs(columns: list[Column], poly: Polygon, shape_id: str, *,
                trim_at_mm: float,
                spacing_mm: float = machine.SATIN_SPACING_MM,
                split_above_mm: float | None = None,
                pull_mm: float = 0.0,
                pull_floor_mm: float = 0.0,
                underlay_style: str = "none",
                start_near: tuple[float, float] | None = None,
                min_cross_mm: float = machine.SATIN_MIN_CROSS_MM,
                ) -> tuple[list[StitchRun], dict]:
    """Columns of ONE letter -> runs in sew order, plus a report in the
    satin tier's contract (`empty`, `too_thin`, `jumps`), extended with the
    column census stage 7 copies into the plan's counters."""
    from .stage6_satin import _comb_thresholds, _push_rails, _split_points   # same package, same rules

    report = {"too_thin": False, "jumps": 0, "empty": False,
              "columns": 0, "columns_unsewn": 0, "thin_crosses": 0, "stations": 0}
    above = split_above_mm if split_above_mm is not None else machine.SPLIT_SATIN_ABOVE_MM
    runs: list[StitchRun] = []
    left = list(columns)
    cursor = start_near
    while left:
        # Nearest-next from where the needle actually IS -- after the
        # previous column's last stitch, which under an underlay is the
        # column's START end (it sews back over its own underlay).
        col = _pick_nearest(left, cursor)
        left = [c for c in left if c is not col and c.piece is not col.piece]
        a_pts = [a for a, _ in col.stations]
        b_pts = [b for _, b in col.stations]
        if pull_mm > 0:
            a_pts, b_pts = _push_rails(a_pts, b_pts, poly, pull_mm, pull_floor_mm)
        kept = [(a, b) for a, b in zip(a_pts, b_pts) if math.dist(a, b) >= min_cross_mm]
        report["thin_crosses"] += len(col.stations) - len(kept)
        if len(kept) < 3:
            report["columns_unsewn"] += 1
            continue
        if underlay_style != "none":
            ul = _underlay_run(kept, shape_id)
            if ul is not None:
                runs.append(ul)
                kept = kept[::-1]       # the column sews back over its own underlay
        legs = [math.dist(a, b) for a, b in kept]
        thr = _comb_thresholds(legs, above)
        pts: list[tuple[float, float]] = []
        prev = None
        for i, (a, b) in enumerate(kept):
            near, far = (a, b) if i % 2 == 0 else (b, a)
            if prev is not None and math.dist(prev, near) < stitches.SAME_POINT_MM:
                pts.pop()
            pts.append(near)
            pts.extend(_split_points(near, far, i, thr[i] if i < len(thr) else above))
            pts.append(far)
            prev = far
        if len(pts) < 4:
            report["columns_unsewn"] += 1
            continue
        runs.append(StitchRun(points=pts, kind=stitches.SATIN, shape_id=shape_id))
        report["columns"] += 1
        report["stations"] += len(kept)
        cursor = pts[-1]
    if not runs or report["columns"] == 0:
        report["empty"] = True
        return [], report
    # Link consecutive runs: the satin tier's own sew-or-jump rule, verbatim
    # (`satin_shape`'s tail). Under rail comp the rails sit a pull outside
    # the artwork and a hop that ends on one is still inside the column.
    poly_link = poly.buffer(0.1 + pull_mm)
    for prev_run, cur in zip(runs, runs[1:]):
        a, b = prev_run.points[-1], cur.points[0]
        d = math.dist(a, b)
        if d < machine.TINY_STITCH_MM:
            continue
        if d <= trim_at_mm and poly_link.covers(LineString([a, b])):
            continue
        cur.jump = True
        cur.trim = d > trim_at_mm
        report["jumps"] += 1
    return runs, report


def lettering_columns_shape(poly: Polygon, shape_id: str, *, trim_at_mm: float,
                            spacing_mm: float = machine.SATIN_SPACING_MM,
                            split_above_mm: float | None = None,
                            pull_mm: float = 0.0, pull_floor_mm: float = 0.0,
                            underlay_style: str = "none",
                            start_near: tuple[float, float] | None = None,
                            ) -> tuple[list[StitchRun], dict]:
    """One text-tagged letter (its ARTWORK polygon) -> runs, report. The
    stage 7 entry point behind `cfg.lettering_columns`: cut, then construct."""
    from .outline_cut import letter_columns

    # One station per `spacing_mm` along the rail, rails alternating: the
    # engine's own meaning of satin spacing (`_resample_by_pitch`). The spike
    # stationed at half that and sewed every letter twice as dense.
    cut = letter_columns(poly, pitch_mm=spacing_mm)
    runs, report = column_runs(cut.columns, cut.poly, shape_id, trim_at_mm=trim_at_mm,
                               spacing_mm=spacing_mm, split_above_mm=split_above_mm,
                               pull_mm=pull_mm, pull_floor_mm=pull_floor_mm,
                               underlay_style=underlay_style, start_near=start_near)
    report["cuts"] = len(cut.cuts)
    report["columns_unsewn"] += len(cut.unsewn)
    return runs, report
