"""Satin columns — how thin strokes, borders and lettering get sewn.

A shape narrower than a few millimetres must not be filled: tatami rows have
nowhere to run and the result is a lumpy scribble. It is sewn as SATIN — zigzag
crosses perpendicular to the stroke, reading as one solid band of parallel
thread. This is the single technique that most separates professional
embroidery from hobby output, and it is why lettering is satin practically
everywhere it fits.

The pipeline mirrors the browser engine's `medialSatin` (src/satin.js), whose
design lessons were learned the hard way and are kept deliberately:

- The stroke's spine comes from the **medial axis** of a raster of the shape.
  scikit-image's `medial_axis` returns the distance transform with the
  skeleton, so the local half-width comes free — the browser engine has to
  ray-cast for it.
- Skeleton branch points are detected with the **Rutovitz crossing number**
  (arms leaving the pixel), never the raw 8-neighbour count: a pixelated curve
  is a staircase, a staircase pixel has 3 raw neighbours, and raw degree would
  shatter a smooth O into hundreds of fragments.
- Thinning grows **spurs** — short dead-end twigs at curvature bumps — and they
  are pruned (short, exactly one free end) before strokes are read off,
  iterating because removing one spur can expose another.
- Pure cycles (O, 0, a counter's wall) contain no node at all, so they are
  walked separately as closed strokes: no free ends, no end trim.
- Normal angles along the spine are **unwrapped** (±π jumps folded away) then
  smoothed, so the crosses never flip direction partway along a stroke.
- Free stroke ends are **trimmed by about half the stroke width**: the medial
  axis bends toward corners at a cap, and crosses placed there degenerate.

Split satin, and the rail-parity contract
-----------------------------------------
A cross longer than `machine.SPLIT_SATIN_ABOVE_MM` carries intermediate
penetrations (split satin): long stitches float, snag, and pull, and the
professional corpus splits them — 53% of 5 mm crosses, ~100% from 7.5 mm.
The split points are staggered station to station so the holes never trench a
line down the column, mirroring the corpus's 3-6-station cycles.

That collides with a load-bearing contract: emitted satin points strictly
alternate rails (A, B, A, B, ...), and every instrument reads them that way —
the tests slice rails as even/odd points, `tools/audit.py` and the fan test
scan same-rail pairs two apart. The resolution, chosen over flagging split
crosses as separate runs or length-classifying in every instrument:

1. Below the threshold nothing changes — a column with no over-threshold
   cross emits byte-identical points, so every existing fixture, benchmark
   and instrument keeps its exact parity read (current fixtures top out at
   3.71 mm crosses against the 5.0 threshold).
2. An over-threshold cross keeps its rail penetrations in strict A/B order
   and inserts split points BETWEEN them, exactly on the cross segment
   (`_split_points` lerps along A->B). `strip_splits` removes them exactly —
   a point collinear with and between its neighbours can only be a split
   penetration, because a real rail-to-rail step always turns (the return
   leg reverses; degenerate crosses are dropped) — the same
   strip-before-reading contract `stitches.strip_ties` established for lock
   stitches. Instruments that may meet wide columns strip ties first, then
   splits, then read parity as ever.

Everything works in mm, y-down, the space stage 4 produced.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field as _dc_field

import cv2
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as SPoint
from skimage.morphology import medial_axis

from . import machine, stitches
from .shapefield import build_shape_field
from .stitches import StitchRun

# Raster resolution for the medial axis. Enough that a 0.8 mm stroke is ~5 px
# wide (thinning needs a few pixels of meat to find the middle); capped so a
# huge shape cannot allocate an absurd grid.
_RASTER_PX_PER_MM = 6.0
_RASTER_MAX_PX = 900
# A stroke shorter than this many half-widths is skeleton noise, not artwork.
_MIN_STROKE_HALFWIDTHS = 1.2
# The half-width profile is median-filtered over this many samples to drop rays
# that escaped through a junction, then averaged this many times to make the
# two rails run parallel instead of tracking every wobble in the boundary.
_WIDTH_MEDIAN_WINDOW = 5
_WIDTH_SMOOTH_PASSES = 4
# Distance, in stroke half-widths, over which a cross's direction is measured.
_TANGENT_WIDTHS = 1.0
# How opposed two arms must be to count as one stroke through a node. -0.5 welds
# arms 120 deg apart -- a stroke turning 60 deg, which pivots and sprays.
_WELD_MAX_DOT = -0.5
# A spine turning more than this many degrees within about one stroke width
# gets the column CUT there. This started at 35 and the corpus overruled it:
# across 19 professional files, 1,436 corner events sit INSIDE a continuing
# run and only 18 are splits — pros sew through corners, letting the outside
# rail fan while the short-stitch guard protects the inside. Splitting is the
# fallback for corners so sharp the column would fold back over itself.
_SPLIT_TURN_DEG = 90.0
# THE GOLDMAN CORNER JOIN (2026-09-03, the stitch-angle rule's pass 2; Kent's
# call, `docs/stitch-angle-convention-2026-09-03.md` §5 item 5). Two straight
# members meeting at 45 deg or more are NOT a bend to sew round: the expired
# Goldman/SoftSight disclosure (US6804573B2) breaks the column there -- one
# member runs THROUGH and is extended to the outer edge, the other is
# shortened and BUTTS into it -- and that is the mitre the Wilcom guide draws.
# What the fan did instead: a merged arm-to-slab chain on Hotel Fremont's
# slab serifs turned its cross 90 deg across ~±1.5 mm of a 5 mm arm, which is
# Kent's "E heavy on top and bottom", "L heavy on the bottom", "T's left side
# drops". The 1,436 : 18 corpus statistic behind `_SPLIT_TURN_DEG` is about
# a column turning round a BEND, and a bend keeps sewing through: a cut here
# needs both the spine turning >= `_JOIN_TURN_DEG` over one half-width AND
# the ARTWORK turning >= `_CORNER_BOUNDARY_TURN_DEG` within a
# `_CORNER_BOUNDARY_WINDOW_MM` stretch of its boundary near the apex -- a
# corner has a vertex there (pull comp rounds a convex one into a ~0.5 mm
# arc, and leaves the reflex one sharp), a bend has neither. Measured before
# building: whitebg, alpha and ribbon_curve carry no spine turn over 40 deg
# at 80 mm, Fremont's twelve capitals carry 13 corners at 48-62.
_JOIN_TURN_DEG = 45.0
_CORNER_BOUNDARY_TURN_DEG = 45.0
_CORNER_BOUNDARY_WINDOW_MM = 1.0
# A free end is a TAPERED TIP (not a square cap) when the ray-measured
# corridor ONE STATION IN is already narrower than this fraction of the
# stroke's half-width. Square caps read 0.85-0.94 there (BAR 0.851 is the
# floor of the measured fixtures — the terminal ray tilt costs a few percent);
# the ribbon_curve taper reads 0.59. The terminal station itself cannot be
# the tell: ON a cap face the perpendicular ray skims the boundary and reads
# 0.0 for square caps and tips alike (measured 0.0 on BAR, C and the ribbon).
_TAPER_ZONE_FRAC = 0.8
_RING8 = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


@dataclass
class Stroke:
    spine: list[tuple[float, float]]   # mm
    free_start: bool
    free_end: bool
    closed: bool
    # A free end that is free because `_merge_through_junctions` found a corner
    # or a cap where the skeleton had a branch node, rather than because the
    # skeleton ended there. It is a cap in every way that matters — it extends
    # to the artwork edge like one — but the geometry it comes from is a
    # squared-off letterform edge, not a taper, and `_extend_to_cap` treats the
    # two differently at the very last station.
    capped_start: bool = False
    capped_end: bool = False
    # At an end that tucks under ONE known neighbour — the other arm of a
    # corner, which took the corner itself — how wide that neighbour's own
    # corridor is there, in mm. `satin_stroke` clears that instead of the
    # omnidirectional reading at the node, which at a corner blob is a
    # diagonal across the whole meeting and costs the stub a millimetre of
    # ribbon it should have kept. None everywhere else: a T's stem still has
    # a whole bar to clear and reads the blob, exactly as before.
    tuck_under_start: float | None = None
    tuck_under_end: float | None = None
    # Goldman corner joins INSIDE this stroke (2026-09-03): (index into
    # `spine` of the apex, True if the member BEFORE the apex owns the corner
    # -- runs through and is extended -- and the member after it butts in).
    # The stroke stays one stroke for sequencing, underlay and the travel
    # web; only `satin_stroke` reads this, sewing the members as separate
    # columns joined end to end. See `_split_sharp_corners`.
    corners: list = _dc_field(default_factory=list)


@dataclass
class _WidthField:
    """The medial-axis distance transform kept queryable in mm space.

    The local half-width at any point of the shape, for free, from the same
    computation that produced the skeleton. Used to keep a cross from escaping
    its own stroke: at a junction (the top of a T) a perpendicular ray from the
    stem hits the BAR's far boundary, and without a local cap those crosses
    span the whole junction as an X of thread.

    A thin view over the same numbers `digitizer_core.shapefield.ShapeField`
    carries (`dist`/`scale`/`ox`/`oy`, and `half_at` reads them identically) —
    this class predates that module and stays the type `extract_strokes`
    returns either way; `ShapeField` additionally carries `mask`/`skel` for
    whatever downstream stage the DT-first migration eventually gives them to.
    """

    dist: np.ndarray
    scale: float
    ox: float
    oy: float

    def half_at(self, pt: tuple[float, float]) -> float:
        x = int((pt[0] - self.ox) * self.scale)
        y = int((pt[1] - self.oy) * self.scale)
        h, w = self.dist.shape
        if 0 <= y < h and 0 <= x < w:
            v = float(self.dist[y, x])
            if v > 0:
                return v / self.scale
        return 0.0


# --- Classification --------------------------------------------------------

def ribbon_width_mm(poly: Polygon) -> float:
    """Mean stroke width of a shape treated as a ribbon: 2·area / perimeter.

    Exact for a long rectangle, close enough for letterforms, and cheap enough
    to run on every region. Counters subtract from the area and add to the
    perimeter, which is what makes it right for an O as well.
    """
    perim = poly.exterior.length + sum(r.length for r in poly.interiors)
    if perim <= 0:
        return 0.0
    return 2.0 * poly.area / perim


def is_satin_candidate(poly: Polygon, max_width_mm: float, *,
                        design_class: str = "flat") -> bool:
    """Should this shape be satin rather than fill?

    Two conditions, both about how the result reads on fabric: the ribbon must
    be narrow enough that crosses do not float (`max_width_mm`), and it must
    actually BE a ribbon — long relative to its width — rather than a small
    compact blob, which sews better as a few rows of fill.

    Both conditions are read off `2*area/perimeter` and the raw perimeter,
    and both share one blind spot: boundary NOISE inflates the perimeter,
    which shrinks the measured width and inflates the length estimate at the
    same time — so a compact, organic blob with a jittery outline can read as
    a narrow, long ribbon on both tests at once. Measured on
    `docs/dt-classifier-spike-2026-08-02.md`'s synthetic case: a 20mm
    serrated disc (tooth 0.6mm) reads `ribbon_width_mm` 2.12mm against a 5mm
    cap and passes the aspect gate too, purely from the noise, not from
    being a stroke. Confirmed on this repo's own committed fixtures too —
    `testdata/photo/region_blobs.png`'s `Sd12bfc9e`/`S94f29987` and
    `testdata/photo/summit_badge.png`'s `Sed818ef7`/`S00d736bf`/`S6096e7a9`
    are near-square, organic, segmentation-noisy regions (bounding-box
    aspect 1.05-1.13) that this test alone waves through as satin.

    A second, independent width read off the exact distance transform at the
    shape's own medial axis (`docs/dt-classifier-spike-2026-08-02.md`'s
    `VP90` arm — a pure TIGHTENING, it can only turn a satin call into a
    fill call, never the reverse) runs for every `design_class`, `"flat"`
    included. It did not always: the DT check first landed
    (`satin-classifier-organic-shapes`) scoped to `"gradient"`/
    `"photo_subject"`/`"photo_scene"` only, on the premise that flat art's
    clean, spot-colour, vector-like boundaries do not carry the
    segmentation-derived noise this check exists to catch. That premise
    does not hold: this repo's own `testdata/photo/enthusiast_logo.png`
    benchmark — flat-classified, hand-picked as the fixture that reproduces
    what Kent complains about (see `COOKBOOK.md`'s "Hard-won lessons") —
    contains compact, jittery-boundary shapes the perimeter-only rule
    satin-stitches into a literal starburst (crosses fanning from a single
    point instead of a parallel column): `Scd89ad66` and `Sff37b029` at
    90mm both flip satin->fill under the DT check, and rendering their
    pre-fix stitch output confirms the fan by eye, not just by the numeric
    disagreement. `design_class` is kept as a parameter (every existing
    caller passes one) but no longer changes this function's verdict; the
    four letterform archetypes (`BAR`/`O_RING`/`C_STROKE`/`T_SHAPE` in
    `tests/test_satin.py`) keep their satin call under the DT check exactly
    as already proven for the non-flat classes — this is a widening of
    scope, not a new rule. **`classify_ribbon` below is the implementation**;
    this is a thin bool wrapper over it. (It used to point at
    `_dt_regular_and_within_cap`, deleted 2026-08-17 once `classify_ribbon`
    absorbed both of its checks.)
    """
    return classify_ribbon(poly, max_width_mm,
                           design_class=design_class).satin


# Law 31's satin minimum width, adopted VERBATIM from the printed rule
# (docs/dt-first-verdict-2026-08-11.md §4: "under 1 mm: convert to multi-ply
# run") — deliberately NOT tuned or swept: ROADMAP hard gate 1 names the
# satin width floor a physical constant fabric settles, so the value here is
# a citation, not a calibration, and any retune waits on cloth. Photo
# classes only: live defect 2 measured the sub-millimetre-satin defect on
# photo-family art and DISPROVED the reroute for flat logo art (61 of 64
# sub-1.0mm satin shapes on real customer logos are ground the pro also
# satined — professionals satin hairline strokes on flat art routinely), and
# the disproof population classifies "gradient" like most real logo art, so
# the only gate consistent with both measurements is the photo lane itself.
PHOTO_MIN_SATIN_WIDTH_MM = 1.0
# Mirrored, verbatim, from stage7_sequence.PHOTO_CLASSES — importing it here
# would cycle (stage7 imports this module). Kept in lockstep the same way
# regions.py mirrors the service's _TIER_VALUES.
from .config import PHOTO_CLASSES as _PHOTO_CLASSES  # canonical copy lives in config.py


@dataclass(frozen=True)
class RibbonVerdict:
    """`is_satin_candidate`'s verdict, plus WHICH gate produced it.

    `reason` is the first gate that fired, in the same short-circuit order the
    checks run: `width_cap`, `aspect`, `dt_irregular`, `dt_p90_cap`,
    `dt_degenerate` (the raster was too small to skeletonize, so the DT check
    deferred), `photo_width_floor` (the shape EARNED satin but its doubled
    p90 medial width sits under `PHOTO_MIN_SATIN_WIDTH_MM` and this is a
    photo-class design — stage 7 reroutes it to the outline run), or `satin`
    for a shape that passed everything.

    `metrics` carries what each gate measured, so a rejection can be read as a
    MARGIN rather than a bare no — `docs/superpowers/specs/2026-08-16-satin-
    routing-gate-attribution-design.md` §3b: a promotion path is only cheap if
    the misses cluster just past the line.
    """

    satin: bool
    reason: str
    metrics: dict[str, float]


def classify_ribbon(poly: Polygon, max_width_mm: float, *,
                    design_class: str = "flat",
                    full_metrics: bool = False) -> RibbonVerdict:
    """`is_satin_candidate`'s implementation. Same verdict, with attribution.

    `full_metrics` runs the distance transform even for a shape an earlier
    gate already rejected, so a probe can ask "would the DT have taken this
    one?" of a shape the width cap threw out. It costs a rasterize plus a
    medial axis per shape, which is why the pipeline's own path leaves it
    False and sees byte-identical cost to before this function existed.
    """
    perim = poly.exterior.length + sum(r.length for r in poly.interiors)
    w = ribbon_width_mm(poly)
    # Ribbon length estimate: half the perimeter minus one width. For a blob
    # (circle: w = r) this comes out ~2.1 w and fails the aspect test.
    length_est = perim / 2.0 - w
    metrics: dict[str, float] = {
        "ribbon_w": w,
        "length_est": length_est,
        "aspect": (length_est / w) if w > 0 else 0.0,
        "area_mm2": float(poly.area),
        "dt_mean": 0.0,
        "dt_std": 0.0,
        "dt_cv": 0.0,
        "dt_p90_mm": 0.0,
        "spine_len_mm": 0.0,
        "explained": 0.0,
        "elongation": 0.0,
    }

    def _with_dt() -> _DtStats | None:
        stats = _dt_stats(poly)
        if stats is None:
            return None
        metrics["dt_mean"] = stats.mean
        metrics["dt_std"] = stats.std
        metrics["dt_cv"] = (stats.std / stats.mean) if stats.mean > 0 else 0.0
        metrics["dt_p90_mm"] = stats.p90_mm
        metrics["spine_len_mm"] = stats.spine_len_mm
        metrics["explained"] = stats.explained
        metrics["elongation"] = stats.elongation
        return stats

    def _reject(reason: str) -> RibbonVerdict:
        if full_metrics:
            _with_dt()
        return RibbonVerdict(False, reason, metrics)

    if w <= 0 or w > max_width_mm:
        return _reject("width_cap")
    if length_est < 3.0 * w:
        return _reject("aspect")

    stats = _with_dt()
    if stats is None:
        # A shape too small or thin to skeletonize is not the DT check's
        # problem to solve; it defers to the verdict already reached. Named
        # rather than folded into "satin" so the probe does not count a
        # deferral as a shape the check positively approved.
        return RibbonVerdict(True, "dt_degenerate", metrics)
    if 2.0 * stats.std >= stats.mean:
        # The regularity term is a PROXY for ribbon-ness, and on real
        # lettering it is a poor one: a taper, a serif or a script stroke's
        # thick-and-thin body spreads the radii without making the shape any
        # less of a ribbon. `explained` measures ribbon-ness directly, so
        # where the two disagree and the shape is within the width the
        # machine can hold, the direct measurement wins. This is the one path
        # in this function that can turn a fill call back into a satin call.
        if (stats.p90_mm <= max_width_mm
                and _PROMOTE_EXPLAINED_MIN <= stats.explained
                <= _PROMOTE_EXPLAINED_MAX
                and stats.elongation >= _PROMOTE_ELONGATION_MIN):
            return _floor_or(RibbonVerdict(True, "promoted_ribbon", metrics),
                             stats, design_class, metrics)
        return RibbonVerdict(False, "dt_irregular", metrics)
    if stats.p90_mm > max_width_mm:
        return RibbonVerdict(False, "dt_p90_cap", metrics)
    return _floor_or(RibbonVerdict(True, "satin", metrics),
                     stats, design_class, metrics)


def _floor_or(earned: RibbonVerdict, stats: _DtStats, design_class: str,
              metrics: dict) -> RibbonVerdict:
    """Law 31's width floor, applied only to a shape that already EARNED
    satin, only in the photo classes. `stats.p90_mm` is the DOUBLED p90
    medial radius — the ARTWORK column width, before stage 5's pull comp
    widens the sewn cross (up to ~2x pull_comp_mm on top; the classifier
    deliberately reads the artwork polygon, same as the satin call itself)
    — so the comparison is the verdict doc's `2·p90/scale < 1.0 mm`
    verbatim. A `dt_degenerate` deferral never reaches here: no DT numbers,
    no floor — the rule reads off measurements it does not have.
    """
    if (design_class in _PHOTO_CLASSES
            and stats.p90_mm < PHOTO_MIN_SATIN_WIDTH_MM):
        return RibbonVerdict(False, "photo_width_floor", metrics)
    return earned


# The percentile Melco's own patent (US9702070) is documented to use is 70;
# the spike measured 90 sits above every letterform junction spike (a serif
# crossbar's inscribed circle running sqrt(2) times its stroke) while still
# rejecting a wide compact blob. Not swept against 70/80/95 here -- flagged
# in the spike doc as the one open tuning question before this ships wider.
_DT_TIGHTEN_PERCENTILE = 90.0


# The DT arm's reasoning, kept here after `_dt_regular_and_within_cap` was
# deleted on 2026-08-17. That function was the original home of these two
# checks; `classify_ribbon` absorbed them when it took over so it could report
# WHICH one fired, leaving the old one with no callers while three docstrings
# still pointed at it as the live check. Deleted rather than left as a trap
# (the `match_shape_ids` lesson), and its argument preserved:
#
# The DT reads the exact distance transform at the medial axis instead of
# `2*area/perimeter`. Local, per-point measurements are immune to the
# perimeter-based test's failure mode: boundary noise moves individual radii by
# the noise amplitude, not by a global perimeter sum, so a compact blob's radii
# stay large (its true half-size) no matter how jittery its outline is. Two AND
# terms, exactly `docs/dt-classifier-spike-2026-08-02.md`'s recommended `VP90`
# arm — both now live in `classify_ribbon`:
#
# - **Regularity** (`2*sigma < mu` at skeletal pixels): a uniform-thickness
#   stroke has a tight radius distribution; a blob's medial axis collapses
#   toward its centre, spreading the radii out. This is what actually separates
#   a ribbon from a blob -- not `max_width_mm`, which both can satisfy. It is
#   also the term the promotion path can overrule, on `explained`, because on
#   real lettering a taper or serif spreads the radii without making the shape
#   any less of a ribbon.
# - **The 90th-percentile width stays under the cap**: `max` is a junction
#   artefact (a serif crossbar's inscribed circle runs sqrt(2) times its
#   stroke) and rejects real letterforms; `p90` strips that spike while still
#   catching a genuinely wide blob. The promotion path does NOT reopen this
#   one -- it is a physical limit, not a proxy.


# How much of a shape's area its own spine has to account for before the
# promotion path will overrule the regularity term. A ribbon IS its spine swept
# by its width, so this sits near 1: the four letterform archetypes read
# 0.85-0.94 and a 60 mm taper reads 0.90, while the serrated disc the DT check
# exists to catch reads 0.11-0.13 — boundary noise moves this statistic the
# opposite way to `2*area/perimeter`, which is what makes it safe to promote
# on. 0.80 measured best of a 0.5-0.85 sweep across 15 real customer designs
# (net +333 cells, helping 12 designs and hurting 2), on a plateau rather than
# a knife edge: 0.70 and 0.75 give +309 and +316.
_PROMOTE_EXPLAINED_MIN = 0.80
# Above ~1 the spine has COLLAPSED — a compact shape thins to a point or two,
# the swept area goes to nothing and the ratio explodes (a plain disc reads
# 38). Such a shape is a blob, not a ribbon, and the earlier gates normally
# catch it; this bound closes the path rather than relying on that. Costs one
# shape and one net cell across the corpus.
_PROMOTE_EXPLAINED_MAX = 1.25
# `explained` alone is not enough, and the shape that proves it is this repo's
# own benchmark star (`photo/enthusiast_logo.png`'s `Sff37b029`): it reads 0.974
# — a compact 5-pointed star IS well described by its spine — and satinning it
# produces the literal starburst, crosses fanning from a single point, that
# `test_flat_lane_starburst_shapes_correctly_flip_to_fill` exists to prevent.
# What separates it from a stroke is how LONG that spine is relative to the
# width: the star runs 8.3, real ribbons 12-25. 10.0 clears the star by ~20%
# and costs 32 net cells across the 15-design corpus (332 -> 300), which is the
# right trade against a rendering defect confirmed by eye.
_PROMOTE_ELONGATION_MIN = 10.0


@dataclass(frozen=True)
class _DtStats:
    """What the distance transform says about a shape, at its own skeleton.

    `explained` is the shape's area over what its spine sweeps
    (`spine_len_mm * 2 * mean radius`) — how much of the shape is accounted
    for by "a stroke of this length at this width".
    """

    mean: float
    std: float
    p90_mm: float
    spine_len_mm: float
    explained: float
    elongation: float


def _dt_stats(poly: Polygon) -> _DtStats | None:
    """None on a degenerate raster — a shape too small or thin to skeletonize
    — which every caller reads as "the DT has no opinion here", not as a
    rejection. Split out of `_dt_regular_and_within_cap` so `classify_ribbon`
    can report the numbers as well as the verdict; the shipped arithmetic is
    unchanged and the two new fields are additions.
    """
    field = build_shape_field(poly)
    if field is None or not field.skel.any():
        return None
    r = field.dist[field.skel]
    if r.size == 0 or r.mean() <= 0:
        return None
    p90_mm = 2.0 * float(np.percentile(r, _DT_TIGHTEN_PERCENTILE)) / field.scale
    # Spine length from the skeleton's pixel count: a 1-px thinning lays one
    # pixel per unit of spine. Diagonal runs cost up to sqrt(2) more pixels
    # than orthogonal ones, which is well inside the margin `explained` is
    # asked to discriminate across (0.13 for a blob against 0.85+ for a
    # ribbon).
    spine_len_mm = float(r.size) / field.scale
    width_mm = 2.0 * float(r.mean()) / field.scale
    swept = spine_len_mm * width_mm
    return _DtStats(
        mean=float(r.mean()),
        std=float(r.std()),
        p90_mm=p90_mm,
        spine_len_mm=spine_len_mm,
        explained=(float(poly.area) / swept) if swept > 0 else 0.0,
        elongation=(spine_len_mm / width_mm) if width_mm > 0 else 0.0,
    )


# --- Skeleton extraction ---------------------------------------------------

def _rasterize(poly: Polygon) -> tuple[np.ndarray, float, float, float]:
    """-> (binary mask, scale px/mm, x-origin mm, y-origin mm).

    The scale adapts to the ribbon: thinning a wall under ~8 px wide invents
    branch points at every wiggle and the skeleton shatters (a 0.8 mm S-curve
    came back as 14 strokes at the base resolution). Narrow shapes are small,
    so raising their resolution never threatens the grid cap.
    """
    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0)
    wall = ribbon_width_mm(poly)
    need = _RASTER_PX_PER_MM if wall <= 0 else max(_RASTER_PX_PER_MM, 8.0 / wall)
    scale = min(need, _RASTER_MAX_PX / max(dim, 1e-6))
    w = int(math.ceil((x1 - x0) * scale)) + 4
    h = int(math.ceil((y1 - y0) * scale)) + 4
    img = np.zeros((h, w), np.uint8)

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)
        return np.column_stack([(a[:, 0] - x0) * scale + 2, (a[:, 1] - y0) * scale + 2]).astype(np.int32)

    cv2.fillPoly(img, [to_px(poly.exterior.coords)], 255)
    for ring in poly.interiors:
        cv2.fillPoly(img, [to_px(ring.coords)], 0)
    return img, scale, x0 - 2 / scale, y0 - 2 / scale


def _crossing_number(mask: np.ndarray, x: int, y: int) -> int:
    h, w = mask.shape
    c = 0
    for k in range(8):
        ax, ay = _RING8[k]
        bx, by = _RING8[(k + 1) % 8]
        a = mask[y + ay, x + ax] if 0 <= y + ay < h and 0 <= x + ax < w else 0
        b = mask[y + by, x + bx] if 0 <= y + by < h and 0 <= x + bx < w else 0
        if not a and b:
            c += 1
    return c


def _skeleton_edges(mask: np.ndarray) -> list[dict]:
    """Decompose a 1-px skeleton into edges between nodes, plus closed loops.

    A faithful port of the browser engine's `skeletonEdges` — see the module
    docstring for why crossing number and the separate loop walk matter.
    Returns [{"pts": [(x, y), ...], "free_start": bool, "free_end": bool,
    "closed": bool}].
    """
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    pixels = set(zip(xs.tolist(), ys.tolist()))

    def nbrs(x: int, y: int) -> list[tuple[int, int]]:
        return [(x + dx, y + dy) for dx, dy in _RING8 if (x + dx, y + dy) in pixels]

    # Node-ness depends only on the mask, so compute it once: the walks below
    # ask "is this a node" for nearly every pixel on every step, and doing the
    # 8-neighbour scan each time multiplied the whole decomposition by ~4.
    node_set = {p for p in pixels
                if len(nbrs(*p)) == 1 or _crossing_number(mask, *p) >= 3}

    def is_node(x: int, y: int) -> bool:
        return (x, y) in node_set

    edges: list[dict] = []
    used_dir: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    # Non-node pixels each belong to exactly ONE edge. Consuming them as they
    # are walked is what makes that true: without it, a walk that slipped past
    # a junction diagonally could re-traverse another walk's corridor, and the
    # review measured segments emitted at up to 4x multiplicity — thread laid
    # down 2-4 times as dense along the doubled strokes.
    consumed: set[tuple[int, int]] = set()

    def walk(start: tuple[int, int], first: tuple[int, int]) -> list[tuple[int, int]]:
        path = [start, first]
        if not is_node(*first):
            consumed.add(first)
        prev, cur = start, first
        for _ in range(len(pixels) + 1):
            if is_node(*cur):
                break
            cand = [p for p in nbrs(*cur) if p != prev]
            # A node neighbour ends the edge NOW. _RING8 order puts some
            # diagonals before their adjacent orthogonals, so preferring plain
            # order can step past the junction pixel and keep walking into the
            # next stroke — the node-slip the review confirmed on Arial glyphs.
            node_next = next((p for p in cand if is_node(*p)), None)
            if node_next is not None:
                path.append(node_next)
                break
            cand = [p for p in cand if p not in consumed]
            if not cand:
                break
            prev, cur = cur, cand[0]
            path.append(cur)
            consumed.add(cur)
        return path

    for node in sorted(node_set):
        for nb in nbrs(*node):
            if (node, nb) in used_dir or (nb in consumed and not is_node(*nb)):
                continue
            used_dir.add((node, nb))
            path = walk(node, nb)
            if len(path) >= 2:
                used_dir.add((path[-1], path[-2]))
            edges.append({
                "pts": path,
                "free_start": len(nbrs(*node)) == 1,
                "free_end": len(nbrs(*path[-1])) == 1,
                "closed": False,
            })

    # Pure cycles never contain a node, so the scan above never touched them.
    # Walk only through still-unconsumed pixels, and NEVER close a path that
    # did not come back to its start on its own: appending the start
    # unconditionally welded stray leftover pixels into phantom "loops" whose
    # closing chord sewed a satin band across up to 12 mm of bare fabric (the
    # review's one confirmed-high finding). A walk that dead-ends is emitted as
    # an open stroke instead.
    for start in sorted(pixels):
        if start in consumed or is_node(*start):
            continue
        ring = [p for p in nbrs(*start) if not is_node(*p) and p not in consumed]
        if len(ring) != 2:
            continue
        path = [start]
        consumed.add(start)
        prev, cur = start, ring[0]
        closed = False
        for _ in range(len(pixels) + 1):
            if cur == start:
                closed = True
                break
            path.append(cur)
            consumed.add(cur)
            cand = [p for p in nbrs(*cur) if p != prev
                    and (p == start or (p not in consumed and not is_node(*p)))]
            if not cand:
                break
            prev, cur = cur, cand[0]
        if closed and len(path) >= 5:
            path.append(start)
            edges.append({"pts": path, "free_start": False, "free_end": False, "closed": True})
        elif len(path) >= 2:
            edges.append({"pts": path, "free_start": True, "free_end": True, "closed": False})
    return edges


# --- corner forks: skeleton branches that are not arms ---------------------
#
# Thinning a bold corner does not stop at the corner. The medial axis forks
# there and runs a branch all the way into the corner POINT, where the
# distance transform is zero. That branch is not an arm of the letterform; it
# IS the corner, expressed as skeleton. The same happens at a flat cap, whose
# axis forks toward both cap corners — `_prune_spurs` erases most of those,
# but a corner of a bold stroke reaches about 1.4 half-widths past the node
# and the ones that clear the pruning threshold survive as full branches.
#
# A branch like that has no ribbon anywhere along it: its corridor runs from
# the junction blob's width straight down to nothing, so a column built on it
# is a WEDGE, and a zigzag across a wedge is the radiating fan this module
# exists to prevent. Worse, it is also a weld candidate — its tangent at the
# node is the most anti-aligned thing a bar's end has to offer, so the bar
# welds to it and the finished column hooks into the cap corner and sprays
# there (measured on `becker_lc_large`'s "E": both its top and bottom bar).
# Neither the arm nor the weld should exist, so this finds them before either
# happens.
#
# Three conditions, and all three are geometry, not taste:
#
#  * exactly one free end, and the corridor AT that end is essentially zero —
#    it runs to a point, not to a cap. A real arm's free end is a cap, where
#    the axis stops a half-width short of the boundary and the corridor there
#    reads its own half-width. Measured on `becker_lc_large`: every corner
#    fork reads 0.08-0.14 of the shape's half-width at its tip, and the
#    shortest real arm that ends in a point (the "R"'s leg) reads 0.09 —
#    which is why this alone is not enough.
#  * short relative to the corridor AT ITS NODE, and this is the load-bearing
#    one. A fork into a wedge of half-angle T reaches node/sin(T) past the
#    node: 1.41 at a right-angle corner, 2 at a 60-degree V, unbounded as the
#    vertex sharpens. So the SHORT ones are exactly the square corners this is
#    about, and the long ones are acute VERTICES — the point of a "V", a "W",
#    an "A" — where the fork is not a decoration, it is the only skeleton the
#    letter's point has and dropping it sews bare fabric (measured on
#    `mfab_lc`'s "W": at 1.78-1.89 node-radii its two inner points went bare).
#    1.7 admits a right angle with raster slop to spare and refuses the "W".
#    The arms that have to survive for other reasons — the "R"'s leg (2.95),
#    the "N"'s bottom diagonal (2.17), the "M"'s right stem (3.64) — clear it
#    comfortably too.
#  * no plateau: the corridor narrows at every probe from the node to the tip.
#    The "R"'s leg holds 2.17 mm flat for its first 3 mm before it tapers;
#    that flat stretch is a ribbon and a ribbon is a stroke. A fork's profile
#    is a straight ramp — 0.71 mm per mm on a right-angle corner, which is
#    exactly 1/sqrt(2) and no coincidence.
_FORK_TIP_FRAC = 0.35
_FORK_NODE_MULT = 1.7
_FORK_STEP_MM = 0.4
# One raster quantum is 1/_RASTER_PX_PER_MM = 0.167 mm, so a staircase can
# hold flat for one probe and then drop two quanta. "Still narrowing" is
# therefore judged against a tolerance a little under one quantum.
_FORK_FLAT_MM = 0.12


def _corner_forks(edges: list[dict], dt_mm, half_mm: float, scale: float) -> set[int]:
    """Indices of the edges that are corner forks, not arms. See the note above."""
    out: set[int] = set()
    if half_mm <= 0:
        return out
    step = max(1, int(round(_FORK_STEP_MM * scale)))
    for i, e in enumerate(edges):
        if e["closed"] or e["free_start"] == e["free_end"]:
            continue                       # a fork has exactly one free end
        pts = list(e["pts"]) if e["free_end"] else list(reversed(e["pts"]))
        if len(pts) < 3:
            continue
        if dt_mm(pts[-1]) > _FORK_TIP_FRAC * half_mm:
            continue                       # ends at a cap, not at a point
        node = dt_mm(pts[0])
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) / scale
        if length > _FORK_NODE_MULT * node:
            continue                       # too long to be this blob's corner
        prof = [dt_mm(p) for p in pts[::step]]
        # A plateau is judged over TWO probes (0.8 mm), not one: the node pixel
        # itself is often a hair narrower than the pixel inside it, and a
        # single-step test reads that one blip as a plateau and keeps every
        # fork (measured on `becker_lc_large`'s "M", node 3.35 then 3.37).
        # Over 0.8 mm a right-angle corner has narrowed by 0.57 mm and even a
        # gentle 0.3 mm/mm ramp by 0.24, so nothing real is close to the bar.
        if any(prof[k + 2] > prof[k] - _FORK_FLAT_MM for k in range(len(prof) - 2)):
            continue                       # a plateau: there is a ribbon in here
        out.add(i)
    return out


def _arm_corridor(edge: dict, at_start: bool, dt_mm, reach_px: int) -> float:
    """How wide this arm's own corridor is just outside the node it starts at.

    Median over the first `reach_px` pixels rather than the value at any one of
    them: right at the node every arm reads the blob, and a single sample a
    fixed distance in lands wherever the raster staircase put it.
    """
    pts = edge["pts"] if at_start else list(reversed(edge["pts"]))
    seen = [dt_mm(p) for p in pts[1:reach_px + 1]] or [dt_mm(pts[0])]
    return sorted(seen)[len(seen) // 2]


def _merge_through_junctions(edges: list[dict], dt_mm=None, half_mm: float = 0.0,
                             scale: float = 1.0) -> list[dict]:
    """Join skeleton edges that run straight through a branch node.

    The skeleton of a T is three edges meeting at one node — but the BAR is one
    stroke that happens to have a stem joining it, not two half-bars. Sewing it
    as two trimmed halves leaves a gap of bare fabric in the middle of the bar
    (measured on the T fixture). At every node, the two incident arms whose
    tangents are most nearly opposite are welded into a single stroke; arms
    that genuinely turn a corner stay separate and later yield to the through
    stroke at the junction.

    `dt_mm` (a pixel -> corridor half-width in mm lookup, with `half_mm` the
    shape's own half-width and `scale` its raster pitch) turns on the corner
    handling. Without it this is exactly the node-welding it always was —
    `textcluster`'s skeleton-buffer path passes nothing, and gets byte-identical
    chains. With it, two things happen before any welding:

      * corner FORKS are removed outright (see `_corner_forks`): they are not
        arms, they have no ribbon, and they must not become strokes OR weld
        partners;
      * a node that is left with fewer than three arms is no longer a
        junction, and ONE arm's end there is re-flagged FREE. This is the half
        that makes the removal safe. A branch node with two arms and a fork is
        a CORNER of the letterform: today the fork covers that corner (badly)
        while both arms trim back out of the blob by `field.half_at(node)`, so
        deleting the fork alone would leave the corner bare. Flagged free, the
        arm keeps its full length and `_extend_to_cap` runs it out to the
        artwork edge, covering the corner square with its own column; the
        other arm tucks under it, now clearing that arm's measured corridor
        instead of the blob (`Stroke.tuck_under_start`). A node left with ONE
        arm is the same story at a flat cap whose two forks both went: the arm
        ends at a cap and is extended to it, instead of hooking into whichever
        fork won the weld.

    Ends that still have a through-partner, and every end at a node with three
    or more surviving arms, are untouched — a T's stem still tucks under its
    bar exactly as before.
    """
    corners = dt_mm is not None and half_mm > 0
    # How far along an arm its direction at the node is measured. Five pixels
    # is under a millimetre, and at a corner the medial axis has already
    # started bending toward the fork by then: measured on the E fixture, the
    # bottom bar reads (0.93, -0.37) and the stem (-0.20, 0.98) over five
    # pixels — dot -0.55, just past the weld threshold — where over one stroke
    # width they read (0.98, -0.20) and (0.00, 1.00), dot -0.20, which is what
    # a right angle actually is. `_rail_points` measures its tangents over one
    # stroke width for the same reason and says so at length; a column cannot
    # resolve direction finer than its own width, and a weld is a decision
    # about where a column goes. Only the corner-aware path uses the wider
    # baseline, so `textcluster`'s chains are untouched.
    arm_px = max(5, int(round(2.0 * half_mm * scale))) if corners else 5

    def arm_dir(edge: dict, at_start: bool) -> tuple[float, float]:
        pts = edge["pts"] if at_start else list(reversed(edge["pts"]))
        far = pts[min(arm_px, len(pts) - 1)]
        dx, dy = far[0] - pts[0][0], far[1] - pts[0][1]
        d = math.hypot(dx, dy) or 1.0
        return dx / d, dy / d

    if corners:
        forks = _corner_forks(edges, dt_mm, half_mm, scale)
        if forks:
            kept = [e for i, e in enumerate(edges) if i not in forks]
            # A corner fork is a DETAIL of a stroke. If the forks are the
            # longest thing in the shape then the shape is not strokes with
            # corners, it is something else — `logo_alpha`'s `Sf5200f3f` is a
            # 9.7 mm-wide glyph apex whose four arms all run from one fat blob
            # to a point, and every one of them satisfies a fork's local
            # geometry. Removing them leaves a 1.2 mm crumb and the shape sews
            # as nothing at all. Where that is the picture the classification
            # does not apply and every edge stands.
            if kept and max(len(e["pts"]) for e in kept) >= \
                    max(len(edges[i]["pts"]) for i in forks):
                edges = kept

    # node pixel -> [(edge_index, end_is_start)]
    incident: dict[tuple[int, int], list[tuple[int, bool]]] = {}
    for i, e in enumerate(edges):
        if e["closed"]:
            continue
        if not e["free_start"]:
            incident.setdefault(e["pts"][0], []).append((i, True))
        if not e["free_end"]:
            incident.setdefault(e["pts"][-1], []).append((i, False))

    parent = list(range(len(edges)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    # (edge_index, end) pairs already welded, so an edge merges at most once
    # per end and a three-way junction cannot chain all its arms together.
    welded: set[tuple[int, bool]] = set()
    joins: list[tuple[tuple[int, bool], tuple[int, bool]]] = []
    # Ends at a node that is not a junction any more — see the docstring.
    caps: set[tuple[int, bool]] = set()
    # end -> the corridor half-width of the single arm it tucks under.
    tucks: dict[tuple[int, bool], float] = {}
    for node, arms in incident.items():
        degree = len(arms)
        # Keep pairing while a through-pair remains: an X crossing has FOUR
        # arms and two of the pairs run straight through each other.
        while len(arms) >= 2:
            best = None
            for ai in range(len(arms)):
                for bi in range(ai + 1, len(arms)):
                    (ei, es), (ej, js) = arms[ai], arms[bi]
                    if ei == ej or (ei, es) in welded or (ej, js) in welded:
                        continue
                    da, db = arm_dir(edges[ei], es), arm_dir(edges[ej], js)
                    dot = da[0] * db[0] + da[1] * db[1]
                    if best is None or dot < best[0]:
                        best = (dot, (ei, es), (ej, js))
            # Anti-aligned means straight-through; the threshold admits a bend
            # but refuses a corner sharp enough that the column would have to
            # pivot, which no parallel-rail satin can sew.
            if best is None or best[0] >= _WELD_MAX_DOT:
                break
            welded.add(best[1])
            welded.add(best[2])
            joins.append((best[1], best[2]))
            arms = [a for a in arms if a != best[1] and a != best[2]]
        # `arms` now holds this node's ends that found no through-partner. If
        # nothing welded here and fewer than three arms are left standing, this
        # is a corner (two arms) or a cap (one), not a junction.
        #
        # ONE of them owns it. At a cap there is only one arm and it takes its
        # own cap, which is the whole point. At a corner, letting both arms
        # extend would sew the corner square twice — about a third of a bold
        # "E"'s area, at every corner, doubled — so the wider corridor takes
        # the corner and the other still tucks under it exactly as it does
        # under a T's bar today. Wider, not longer: on the E fixture the
        # bottom bar is a hair LONGER than the stem (5.32 vs 5.25 mm) and the
        # stem is plainly the stroke that should run corner to corner, which
        # its 1.05 mm corridor against the bar's 0.82 says and nothing else
        # does.
        if corners and degree <= 2 and len(arms) == degree and arms:
            owner = max(arms, key=lambda a: (_arm_corridor(edges[a[0]], a[1],
                                                           dt_mm, arm_px),
                                             len(edges[a[0]]["pts"])))
            caps.add(owner)
            # Whoever did NOT take the corner now has exactly one thing to
            # tuck under, and it is measurable: the owner's own corridor.
            for other in arms:
                if other != owner:
                    tucks[other] = _arm_corridor(edges[owner[0]], owner[1],
                                                 dt_mm, arm_px)

    # A capped end is flagged free — but it is not the same thing as an end
    # that was free in the skeleton, and one caller has to know the difference:
    # `extract_strokes` drops a sub-minimum edge UNLESS both its ends are free,
    # because a short chain between two branch nodes is junction noise while a
    # short free-standing stroke is a dot or a dash. Capping both ends of a
    # quarter-millimetre fragment inside a corner blob would smuggle it past
    # that filter, and `_extend_to_cap` then blows it up into a cross of
    # full-width crosses — a fan built out of nothing. `capped_*` keeps the
    # filter reading the skeleton's own answer.
    edges = [dict(e) for e in edges]
    for e in edges:
        e.setdefault("capped_start", False)
        e.setdefault("capped_end", False)
        e.setdefault("tuck_under_start", None)
        e.setdefault("tuck_under_end", None)
    for ei, at_start in caps:
        edges[ei]["free_start" if at_start else "free_end"] = True
        edges[ei]["capped_start" if at_start else "capped_end"] = True
    for (ei, at_start), width in tucks.items():
        edges[ei]["tuck_under_start" if at_start else "tuck_under_end"] = width

    chains: dict[int, dict] = {i: dict(e) for i, e in enumerate(edges)}
    for (ei, es), (ej, js) in joins:
        ri, rj = find(ei), find(ej)
        if ri == rj:
            continue  # would close a cycle; leave as separate strokes
        # Orient by the weld NODE, not by the original edges' end flags: after
        # a first weld the chain's pts run node-to-node across several edges,
        # and edge ei's "start" may now be buried in the middle of the chain.
        # The node pixel is unambiguous — a ends at it, b starts at it.
        node = edges[ei]["pts"][0] if es else edges[ei]["pts"][-1]
        a, b = chains[ri], chains[rj]
        if a["pts"][-1] == node:
            a_pts, a_free, a_cap = a["pts"], a["free_start"], a.get("capped_start", False)
            a_tuck = a.get("tuck_under_start")
        elif a["pts"][0] == node:
            a_pts, a_free, a_cap = (list(reversed(a["pts"])), a["free_end"],
                                    a.get("capped_end", False))
            a_tuck = a.get("tuck_under_end")
        else:
            continue  # node no longer an endpoint of the chain: skip the weld
        if b["pts"][0] == node:
            b_pts, b_free, b_cap = b["pts"], b["free_end"], b.get("capped_end", False)
            b_tuck = b.get("tuck_under_end")
        elif b["pts"][-1] == node:
            b_pts, b_free, b_cap = (list(reversed(b["pts"])), b["free_start"],
                                    b.get("capped_start", False))
            b_tuck = b.get("tuck_under_start")
        else:
            continue
        chains[ri] = {
            "pts": a_pts + b_pts[1:],
            "free_start": a_free,
            "free_end": b_free,
            "capped_start": a_cap,
            "capped_end": b_cap,
            "tuck_under_start": a_tuck,
            "tuck_under_end": b_tuck,
            "closed": False,
        }
        parent[rj] = ri
        del chains[rj]
    return [c for i, c in chains.items() if find(i) == i]


def _prune_spurs(mask: np.ndarray, spur_len_px: float) -> None:
    """Erase short dead-end twigs in place, keeping their branch node.

    Repeats so a twig hidden behind another twig still goes — but only ever
    erases dead ends the skeleton grew on its own. Deleting a spur leaves its
    branch node standing, and a node left holding one arm turns that arm into
    a dead end through no thinning of its own. Re-measuring such a stem
    against `spur_len_px` deletes real limb: on `enthusiast_logo.png` the left
    bracket's tab is a stem plus two twigs, pass 1 correctly takes both twigs,
    and pass 2 then takes the 19.000 px stem against a 19.4770 px bar. Its
    mirror twin's stem is 20.000 px against 19.1152 px and survives — one
    raster pixel (0.167 mm at 6 px/mm) between a sewn tab and a 7.8 mm2 hole,
    on shapes whose areas differ by 0.06%. So a dead end this function itself
    exposed is remembered and never counted as a spur tip.

    The guard is deliberately narrow. A node going 3 arms -> 2 welds its two
    survivors into one longer edge whose free end is somewhere else entirely;
    that edge stays prunable on its own length, as before.
    """
    exposed: set[tuple[int, int]] = set()
    for _ in range(4):
        removed = 0
        for e in _skeleton_edges(mask):
            if e["closed"] or (e["free_start"] == e["free_end"]):
                continue  # spur = exactly one free end
            tip = e["pts"][0] if e["free_start"] else e["pts"][-1]
            if tip in exposed:
                continue  # a stem we un-branched, not a twig that grew short
            length = sum(math.dist(a, b) for a, b in zip(e["pts"], e["pts"][1:]))
            if length >= spur_len_px:
                continue
            keep = e["pts"][-1] if e["free_start"] else e["pts"][0]
            exposed.add(keep)
            for px in e["pts"]:
                if px != keep:
                    mask[px[1], px[0]] = 0
                    removed += 1
        if not removed:
            return


def _boundary_corner_near(poly: Polygon, at: tuple[float, float],
                          reach_mm: float) -> bool:
    """Does the artwork turn a REFLEX corner of `_CORNER_BOUNDARY_TURN_DEG`
    within `_CORNER_BOUNDARY_WINDOW_MM` of boundary arc, somewhere within
    `reach_mm` of `at`? Two members meeting always make one on the inside of
    the meeting (the crotch of an L, the underside of a slab serif), and pull
    comp leaves a reflex vertex sharp where it rounds a convex one into a
    ~0.5 mm arc. A bend has no sharp reflex vertex, and neither does a
    TAPERED TIP -- whose point is convex, and which the first draft of this
    test cut 1.6 mm from the ribbon_curve golden's end.

    Rings are read with the material on the LEFT (exterior counter-clockwise,
    holes clockwise), so a right turn is a reflex corner of the material.
    
    Every vertex of a HOLE is reflex from the material's side, so a tiny
    counter within reach counts as a corner too -- the spine-turn test the
    caller applies first is what keeps a round counter's stroke uncut.
    """
    half_win = 0.5 * _CORNER_BOUNDARY_WINDOW_MM
    r2 = reach_mm * reach_mm
    for ring, hole in ((poly.exterior, False), *((r, True) for r in poly.interiors)):
        pts = list(ring.coords)
        if len(pts) < 4:
            continue
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        n = len(pts)
        if n < 3:
            continue
        # material on the left: exterior CCW, hole CW
        if ring.is_ccw == hole:
            pts = list(reversed(pts))
        near = [i for i, q in enumerate(pts)
                if (q[0] - at[0]) ** 2 + (q[1] - at[1]) ** 2 <= r2]
        if not near:
            continue
        reflex = [0.0] * n
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            d1 = math.atan2(b[1] - a[1], b[0] - a[0])
            d2 = math.atan2(c[1] - b[1], c[0] - b[0])
            signed = math.degrees((d2 - d1 + math.pi) % (2 * math.pi) - math.pi)
            reflex[i] = -signed if signed < 0 else 0.0      # right turns only
        for i in near:
            total = reflex[i]
            for step in (1, -1):
                walked = 0.0
                j = i
                while True:
                    k = (j + step) % n
                    walked += math.dist(pts[j], pts[k])
                    if walked > half_win or k == i:
                        break
                    total += reflex[k]
                    j = k
            if total >= _CORNER_BOUNDARY_TURN_DEG:
                return True
    return False


def _split_sharp_corners(strokes: list[Stroke], half_mm: float,
                         poly: Polygon | None = None,
                         field: _WidthField | None = None) -> list[Stroke]:
    """Cut stroke spines at concentrated corners so each piece sews as its own
    column -- and JOIN the pieces the Goldman way: at every cut the longer
    piece owns the corner (its cut end is a capped free end, so
    `_extend_to_cap` runs its column out to the artwork edge and covers the
    corner square), and the other piece butts into it (its cut end is a
    junction-style end tucking under the owner's own corridor,
    `Stroke.tuck_under_*`, exactly as a T's stem tucks under its bar).

    Two cut rules, in order of strength. A turn of `_SPLIT_TURN_DEG` (90) over
    one half-width is a FOLD and is cut wherever it occurs -- the column would
    otherwise sew back over itself. A turn of `_JOIN_TURN_DEG` (45) is cut
    only where `poly` says the artwork itself has a corner there
    (`_boundary_corner_near`): a bend of the same angle keeps sewing through,
    which is what the corpus counts pros doing 1,436 times to 18. Without
    `poly` only the fold rule runs, byte-identical to before the join.

    The turn at each sample is measured over a baseline of one half-width per
    side -- the same resolution the crosses themselves have -- so a smooth
    curve (turn spread over many widths, like the C fixture's 13 mm radius)
    never trips either rule.
    """
    if half_mm <= 0:
        return strokes
    out: list[Stroke] = []
    for st in strokes:
        pts = st.spine
        n = len(pts)
        seg = [math.dist(pts[i], pts[i + 1]) for i in range(n - 1)]
        spacing = sorted(seg)[len(seg) // 2] if seg else 0.0
        if n < 5 or spacing <= 0:
            out.append(st)
            continue
        k = max(1, round(half_mm / spacing))
        if n <= 2 * k + 1 and not st.closed:
            out.append(st)          # shorter than one baseline: nothing to see
            continue

        # Turns are measured on a SMOOTHED copy of the spine (cuts are applied
        # to the original -- indices align). The raw medial axis dips toward the
        # stem at every junction weld, and over a one-half-width baseline that
        # raster dip reads ~36 deg -- the T fixture's bar was being cut at a
        # corner the artwork does not have. Smoothing flattens the dip; a real
        # corner (N diagonal 56 deg, hexagon 60, star point 100+) survives it.
        sm = _smooth(pts, 3, st.closed)
        idx = range(n) if st.closed else range(k, n - k)
        turns: list[tuple[float, int]] = []
        turn_at: dict[int, float] = {}
        for i in idx:
            a, b, c = sm[(i - k) % n], sm[i], sm[(i + k) % n]
            d1 = math.atan2(b[1] - a[1], b[0] - a[0])
            d2 = math.atan2(c[1] - b[1], c[0] - b[0])
            turn = abs(math.degrees((d2 - d1 + math.pi) % (2 * math.pi) - math.pi))
            turns.append((turn, i))
            turn_at[i] = turn

        # Strongest corners first, and no second cut within a baseline of one
        # already made -- a corner is one apex, not every sample on its shoulder.
        #
        # A corner is where two MEMBERS meet, and a member is at least one
        # column width long and ends at a CAP, not a point. A join-rule apex
        # closer than a column width to a free end of an open stroke is a
        # tapered tip curling (the ribbon_curve golden, cut 1.6 mm from its
        # point): left to the cap machinery. And a free-ended piece whose tip
        # has no corridor -- the distance transform there under
        # `_FORK_TIP_FRAC` of the half-width -- is a corner TWIG the skeleton
        # welded onto a stem, the very geometry `_corner_forks` removes at a
        # node (THERMAL's H: a 2.3 mm 45 deg arm into the crossbar corner,
        # which then tilted the stem's cap 45 deg): it is cut off and DROPPED,
        # and the stem it hijacked is capped square over the corner instead.
        # The fold rule still cuts anywhere, as it always did.
        reach = 2.0 * half_mm + 0.5
        member = 2.0 * half_mm
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        # No join on a HAIRLINE: a column under the minimum cross (plus the
        # 20% the rails lose to the nearer-hit symmetry and `place`) sews no
        # crosses at all, and `satin_shape` reports it empty so stage 7
        # falls back to fill. Joining its corner rescued a 0.5 mm-wide,
        # 3.4 mm^2 squiggle on drone_render into four satin points and 79%
        # bare fabric (2026-09-03). Below this width the fold rule alone
        # runs; the lettering the join exists for is 0.7 mm and up.
        joinable = 2.0 * half_mm >= 1.2 * machine.SATIN_MIN_CROSS_MM
        cuts: list[int] = []
        twigs: dict[int, str] = {}       # cut index -> the side ("start"/"end") that is a twig
        for turn, i in sorted(turns, reverse=True):
            if turn < _JOIN_TURN_DEG:
                break
            gap = (min(abs(i - j), n - abs(i - j)) for j in cuts) if st.closed \
                else (abs(i - j) for j in cuts)
            if not all(g > 2 * k for g in gap):
                continue                # on the shoulder of a cut already made
            twig = ""
            if turn < _SPLIT_TURN_DEG:
                # The join rule. Not on a closed ring: a ring has no ends to
                # own a corner, and cutting it open at whichever of its
                # corners happened to read over 45 deg on the raster
                # (measured on a hexagon border: two, three, two, one of six,
                # by rotation) buys cap pairs and hops for nothing -- rings
                # keep the fold rule, byte-identical to before the join.
                if not joinable or st.closed:
                    continue
                # Both sides must be MEMBERS -- at least one column width
                # long. A short side is a twig (free and pointed: cut off and
                # dropped), a tapered tip (free and capped: no cut), or a stub
                # against a junction (not free: no cut -- trimmed at both
                # ends it would sew doubled and untrimmed).
                pointed: list[tuple[float, str]] = []
                blocked = False
                for side, free, tip, length in (("start", st.free_start, pts[0], cum[i]),
                                                ("end", st.free_end, pts[-1], cum[-1] - cum[i])):
                    if length >= member:
                        continue
                    if free and field is not None and \
                            field.half_at(tip) < _FORK_TIP_FRAC * half_mm:
                        pointed.append((length, side))
                    else:
                        blocked = True
                if blocked:
                    continue
                if pointed:
                    twig = min(pointed)[1]      # the shorter pointed side
                # The boundary walk is the expensive test: last, and only for
                # a candidate that has passed everything else.
                if poly is None or not _boundary_corner_near(poly, pts[i], reach):
                    continue            # a bend, not a corner: sew through it
            cuts.append(i)
            if twig:
                twigs[i] = twig
        if not cuts:
            out.append(st)
            continue
        cuts.sort()

        def length(piece: list[tuple[float, float]]) -> float:
            return sum(math.dist(a, b) for a, b in zip(piece, piece[1:]))

        def keep(piece: list[tuple[float, float]]) -> bool:
            return len(piece) >= 3 and length(piece) >= 0.6 * half_mm

        if st.closed:
            # Only fold cuts reach a ring (see above): opened into free-ended
            # pieces that meet in mitred caps, exactly as before the join.
            ring = cuts + [cuts[0] + n]
            for s0, s1 in zip(ring, ring[1:]):
                piece = [pts[j % n] for j in range(s0, s1 + 1)]
                if keep(piece):
                    out.append(Stroke(spine=piece, free_start=True,
                                      free_end=True, closed=False))
            continue

        # Open chain. Twig cuts drop their twig and cap the survivor; fold
        # cuts split the chain into separate strokes (both sides capped, the
        # mitred overlap the fold rule always made); join cuts stay INSIDE the
        # stroke as `Stroke.corners`, so the chain sews as one stroke whose
        # members `satin_stroke` joins the Goldman way.
        lo, hi = 0, n - 1
        free_start, capped_start, tuck_start = st.free_start, st.capped_start, st.tuck_under_start
        free_end, capped_end, tuck_end = st.free_end, st.capped_end, st.tuck_under_end
        inner: list[int] = []
        for i in cuts:
            if i in twigs:
                # the twig side is cut off; the survivor is capped at i
                if twigs[i] == "end":
                    hi = min(hi, i)
                    free_end, capped_end, tuck_end = True, True, None
                else:
                    lo = max(lo, i)
                    free_start, capped_start, tuck_start = True, True, None
            else:
                inner.append(i)
        inner = [i for i in inner if lo < i < hi]
        if hi - lo < 2:
            continue
        fold_cuts = [i for i in inner if turn_at[i] >= _SPLIT_TURN_DEG]
        bounds = [lo, *fold_cuts, hi]
        for bi, (s0, s1) in enumerate(zip(bounds, bounds[1:])):
            piece = pts[s0:s1 + 1]
            if not keep(piece):
                continue
            joins = [i - s0 for i in inner if s0 < i < s1 and turn_at[i] < _SPLIT_TURN_DEG]
            corners: list[tuple[int, bool]] = []
            edges_ = [0, *joins, len(piece) - 1]
            for ci, j in enumerate(joins):
                left = piece[edges_[ci]:j + 1]
                right = piece[j:edges_[ci + 2] + 1]
                corners.append((j, length(left) >= length(right)))
            out.append(Stroke(
                spine=piece,
                free_start=free_start if bi == 0 else True,
                free_end=free_end if s1 == hi else True,
                closed=False,
                capped_start=capped_start if bi == 0 else False,
                capped_end=capped_end if s1 == hi else False,
                tuck_under_start=tuck_start if bi == 0 else None,
                tuck_under_end=tuck_end if s1 == hi else None,
                corners=corners,
            ))
    return out


def extract_strokes(poly: Polygon, *,
                     use_shapefield: bool = False,
                     ) -> tuple[list[Stroke], float, _WidthField | None]:
    """-> (strokes in mm, mean half-width in mm, local width field).

    Strokes are sorted longest first, so a letter's main stem sews before its
    serifs and the between-stroke hops stay short.

    `use_shapefield` (DT-first migration M1, off by default) routes the
    rasterize + `medial_axis(rng=0)` pair below through
    `digitizer_core.shapefield.build_shape_field` instead of the inline call
    that follows. Both paths compute the identical raster and the identical
    `medial_axis` result — the flag exists purely to prove the new, shared
    module byte-identical before anything downstream depends on it; see
    `shapefield.py`'s module docstring and
    `tests/test_shapefield_byte_identical.py`. Off (the default) never
    imports or executes any of `shapefield.py`'s work.
    """
    if use_shapefield:
        sf = build_shape_field(poly)
        if sf is None:
            return [], 0.0, None
        scale, ox, oy, skel, dist = sf.scale, sf.ox, sf.oy, sf.skel, sf.dist
    else:
        mask, scale, ox, oy = _rasterize(poly)
        if not mask.any():
            return [], 0.0, None
        # rng is REQUIRED for determinism: medial_axis breaks ties between
        # equally valid skeleton pixels in a randomly permuted order, and
        # unseeded it returns a different skeleton on every call — which
        # came out as the same artwork digitizing to different stitches run
        # to run.
        skel, dist = medial_axis(mask > 0, return_distance=True, rng=0)
    skel_mask = skel.astype(np.uint8)
    half_px = float(dist[skel].mean()) if skel.any() else 0.0
    field = _WidthField(dist=dist, scale=scale, ox=ox, oy=oy)
    _prune_spurs(skel_mask, max(3.0, half_px * 1.6))
    if not skel_mask.any():
        return [], half_px / scale, field

    def to_mm(p: tuple[int, int]) -> tuple[float, float]:
        return (ox + (p[0] + 0.5) / scale, oy + (p[1] + 0.5) / scale)

    def dt_mm(p: tuple[int, int]) -> float:
        return float(dist[p[1], p[0]]) / scale

    strokes: list[Stroke] = []
    min_len_px = max(3.0, _MIN_STROKE_HALFWIDTHS * half_px)
    for e in _merge_through_junctions(_skeleton_edges(skel_mask), dt_mm,
                                      half_px / scale, scale):
        length = sum(math.dist(a, b) for a, b in zip(e["pts"], e["pts"][1:]))
        # "Free" here means free in the SKELETON — a corner end re-flagged by
        # `_merge_through_junctions` is still a chain between two branch nodes
        # for the purposes of this filter, and a quarter-millimetre one is
        # still noise. See the `capped_*` note there.
        skel_free_start = e["free_start"] and not e.get("capped_start", False)
        skel_free_end = e["free_end"] and not e.get("capped_end", False)
        if length < min_len_px and not (skel_free_start and skel_free_end):
            continue  # stub between two branch nodes: junction noise
        strokes.append(Stroke(
            spine=[to_mm(p) for p in e["pts"]],
            free_start=e["free_start"],
            free_end=e["free_end"],
            closed=e["closed"],
            capped_start=e.get("capped_start", False),
            capped_end=e.get("capped_end", False),
            tuck_under_start=e.get("tuck_under_start"),
            tuck_under_end=e.get("tuck_under_end"),
        ))
    strokes = _split_sharp_corners(strokes, half_px / scale, poly, field)
    strokes.sort(key=lambda s: -sum(math.dist(a, b) for a, b in zip(s.spine, s.spine[1:])))
    return strokes, half_px / scale, field


# --- Geometry along a stroke ----------------------------------------------

def _smooth(pts: list[tuple[float, float]], passes: int, closed: bool) -> list[tuple[float, float]]:
    out = list(pts)
    n = len(out)
    if n < 3:
        return out
    for _ in range(passes):
        prev = list(out)
        rng = range(n) if closed else range(1, n - 1)
        for i in rng:
            a, b, c = prev[i - 1], prev[i], prev[(i + 1) % n]
            out[i] = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)
    return out


def _median_filter(vals: list[float], window: int) -> list[float]:
    """Median of each value's neighbourhood — drops single-sample outliers.

    A ray that escapes a junction reports one wildly long half-width between
    two honest ones. An average would spread that error over the neighbours; a
    median discards it outright, which is what a width profile needs.
    """
    n = len(vals)
    if n == 0 or window < 3:
        return list(vals)
    half = window // 2
    return [sorted(vals[max(0, i - half):min(n, i + half + 1)])[
        len(vals[max(0, i - half):min(n, i + half + 1)]) // 2] for i in range(n)]


def _resample(pts: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    line = LineString(pts)
    if line.length <= 0 or n < 2:
        return list(pts[:1]) * max(n, 1)
    return [(p.x, p.y) for p in (line.interpolate(line.length * i / (n - 1)) for i in range(n))]


def _resample_by_pitch(pts: list[tuple[float, float]], leans: list[float],
                       spacing_mm: float) -> list[tuple[float, float]]:
    """`pts` re-stationed so that consecutive crosses, each leaning
    `leans[i]` off the perpendicular, sit `spacing_mm` apart MEASURED ACROSS
    THE THREADS -- the constant-perpendicular-pitch rule (Pulse, expired;
    `docs/stitch-angle-convention-2026-09-03.md` item 4).

    Two crosses `s` apart along the spine and leaning by `lean` are
    `s * cos(lean)` apart perpendicular to the thread, so holding the SPINE
    spacing at 0.4 mm under a 30 deg lean packs thread at 0.35 mm, and at
    the 48 deg the old bisector put on an N, at 0.27 -- the "pile" seen on
    enthusiast_logo. The compensated arc `∫ cos(lean) ds` is what the
    stations are spread evenly along, so the along-spine step becomes
    `spacing / cos(lean)` and the perpendicular pitch stays the spacing the
    constant already means. This changes NO physical constant; it makes the
    existing one hold under lean (ROADMAP gate 1 untouched).

    Keeps both ends, like `_resample`. With every lean 0 the compensated arc
    is the arc, and the caller skips this entirely so the no-house path
    stays byte-identical.
    """
    n = len(pts)
    if n < 2:
        return list(pts)
    cum = [0.0]
    for i in range(1, n):
        w = 0.5 * (max(math.cos(leans[i - 1]), _LEAN_COS_FLOOR)
                   + max(math.cos(leans[i]), _LEAN_COS_FLOOR))
        cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]) * w)
    total = cum[-1]
    if total <= 0.0:
        return list(pts)
    steps = max(2, int(math.ceil(total / spacing_mm)))
    out: list[tuple[float, float]] = []
    j = 1
    for k in range(steps):
        target = total * k / (steps - 1)
        while j < n - 1 and cum[j] < target:
            j += 1
        seg = cum[j] - cum[j - 1]
        t = 0.0 if seg <= 0.0 else min(1.0, max(0.0, (target - cum[j - 1]) / seg))
        (x0, y0), (x1, y1) = pts[j - 1], pts[j]
        out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    out[0], out[-1] = pts[0], pts[-1]       # both ends exactly, not to float dust
    return out


# --- The house angle for satin lettering (2026-08-26) ------------------------
# Kent, on a sewn Becker Marine logo: *"When doing lettering, fill angle should
# be the same (for almost every block style font like this). Why is the 'N'
# running Vertically?"* He was right, and it was structural: every cross angle
# came from that stroke's OWN spine tangent, so each letter -- and each stroke
# inside a letter -- chose in isolation. Measured on that logo, EMB-Bot's letter
# angles were statistically indistinguishable from random (9/43 within +/-20 deg
# of the mode, against a 22% chance baseline); the pro's were not.
#
# `fill_angle_deg` has carried this idea for the FILL tier all along. This is
# satin's counterpart, and it is deliberately the same shape: None = today's
# behaviour exactly, a number forces the house angle.
#
# WHY IT IS A CLAMP AND NOT AN ASSIGNMENT. A satin cross has to SPAN its
# column. Forced onto a stroke it runs near-parallel to -- an E's arms under a
# horizontal house angle -- the "cross" would lie along the stroke and the
# column collapses. So the house angle is held where the stroke allows it and
# rotated to the nearest angle that still spans where it does not. That is also
# the honest reading of the pro's file: its crosses cluster near horizontal on
# stems, which for block letters largely FOLLOWS from vertical strokes carrying
# most of the area -- it is not evidence of horizontal crosses forced onto
# horizontal strokes.
#
# HOW FAR A CROSS MAY LEAN, and what happens past that (2026-09-03, the
# stitch-angle rule Kent adopted -- `docs/stitch-angle-convention-2026-09-03.md`).
#
# The floor below is a SPAN floor: a cross may sit at most (90 - floor) deg
# off the perpendicular to its own stroke, which is a LEAN of 30 deg at 60.
# Three independent sources agree on the band a professional leans a satin
# column: the Becker Marine pro file (diagonals p50 16 deg, p75 26, p90 43),
# the 86 shipped Ink/Stitch fonts (p50 18, diagonals-only 29.5) and neither
# ever holds a bar's cross 45 deg off its perpendicular, which is exactly
# where the previous floor (45) put every clamped stroke. 60 puts the cap
# inside both bands; cross length at the cap is 1/sin(60) = 1.15x, well
# under the ~1.6x `_rail_points` allows a rail for an unrelated reason.
#
# PAST the cap the old clamp snapped to the cap on whichever SIDE the folded
# difference fell -- and for a bar running along the house's own axis that
# side is decided by sub-degree tangent noise, so an E's three arms took
# +30, -30 and +30 and the smoothing pass swept each one through the flip.
# Rendered at house = 0 on Hotel Fremont the bars came out worse than with
# no house angle at all (2026-09-02), which is why a 45 deg bisector was
# tried and retired. What every font does with a bar is sew it
# PERPENDICULAR (86 fonts: 3.0 deg), and perpendicular has no side. So past
# the cap the lean FADES: linearly from the full cap at the cap's edge to
# zero where the stroke runs along the house axis. Continuous everywhere,
# no side to choose, and a true 45 deg diagonal still leans 22.5 deg
# toward the house (fonts diagonals-only p50 29.5, pro p75 26).
SATIN_HOUSE_MIN_SPAN_DEG = 60.0


def _clamp_to_span(house: float, tangent: float) -> float:
    """The cross angle for a stroke running at `tangent` under `house`: the
    house where the stroke can span it within the lean cap, a fading lean
    toward the house past it, its own perpendicular where the house runs
    along the stroke. Both radians; returns radians.

    d is the signed house-to-perpendicular difference folded to (-90, 90]
    because a cross sewn either way round is the same cross. |d| <= cap:
    the house, exactly. Beyond: lean = cap * (90 - |d|) / (90 - cap), on
    d's side -- the cap at |d| = cap, zero at |d| = 90, so the two sides of
    the fold meet at the perpendicular instead of 2 * cap apart.
    """
    ideal = tangent + math.pi / 2.0
    diff = (house - ideal + math.pi / 2.0) % math.pi - math.pi / 2.0
    limit = math.radians(90.0 - SATIN_HOUSE_MIN_SPAN_DEG)
    if abs(diff) <= limit:
        return house
    lean = limit * (math.pi / 2.0 - abs(diff)) / (math.pi / 2.0 - limit)
    return ideal + math.copysign(lean, diff)


# COLUMNS UNDER ~0.6 mm LOSE CROSSES UNDER A HOUSE ANGLE, and no lean floor
# fixes it (tried 2026-09-03, withdrawn the same hour). Hotel Fremont's 2.6 mm
# "THE" has 0.40-0.45 mm bars and 0.52 mm stems; a perpendicular cross on
# them is at or under `SATIN_MIN_CROSS_MM` (0.5) once the rails sit symmetric
# at the nearer boundary hit and `place` dents one, so `satin_stroke` drops
# it. The shipped default already loses THE's bars (its stems survive only
# because the raster wander, ~19 deg, happens to lengthen the cross), and the
# retired 45 deg bisector kept them by accident at 0.62 mm. Leaning such a
# column as far as a target cross length demands -- acos(width / target),
# per station from the boundary distance -- was built and measured: the
# boundary distance collapses toward the caps, the lean fans 45-2-45 deg
# over a 2.5 mm stem, and the crosses still come out 0.44-0.49 (H stems 0 of
# 10 kept against the stock's 8-10). Lettering that small wants a different
# tier (running stitch, or a bar sewn as a wide column), not a lean hack;
# recorded as a limit, see `docs/stitch-angle-convention-2026-09-03.md` §7.
#
# No lean the rule produces exceeds the cap, so no compensation may divide by
# less than its cosine: the lean is a difference of two separately unwrapped
# sequences, and a spine turning ~60 deg between adjacent stations (nothing
# `_smooth` + `_round_corners` + `_split_at_turns` deliver today) would push
# the two unwraps a half-turn apart and the smoothed difference through 90 --
# pitch x60, a 1.4 mm station gap, silently. A floor on the cosine makes that
# impossible by construction (review, 2026-09-03).
_LEAN_COS_FLOOR = math.cos(math.radians(90.0 - SATIN_HOUSE_MIN_SPAN_DEG))


def _cross_angles(spine: list[tuple[float, float]], closed: bool,
                  fallback_half_mm: float, angle_deg: float | None,
                  ) -> tuple[list[float], list[float]]:
    """(cross angle, lean) per station, both radians, the cross angles
    unwrapped and smoothed exactly as `_rail_points` always laid them.

    The lean is how far each station's cross sits from the cross this
    stroke would carry with NO house angle -- the smoothed perpendicular --
    folded to [0, 90 deg]. It is what the station spacing compensates for
    (`_resample_by_pitch`) and what the outer-rail refinement targets. With
    `angle_deg` None every lean is exactly 0.0 and the angles are the same
    floats they were before this function existed.
    """
    n = len(spine)
    # Tangent angles, unwrapped so a cross never flips direction mid-stroke.
    # The tangent is measured across ONE STROKE WIDTH, not one sample. The
    # spine is a raster staircase: over a ±1-sample baseline (a third of a
    # millimetre here) its direction can only take the eight neighbour
    # directions, so every cross inherits up to ±22.5 deg of quantisation
    # noise. With ray-cast rails that noise was partly hidden — the two
    # boundary hits smoothed it away — but a parallel-offset rail lays the
    # cross exactly along the normal, so the path itself has to be honest. A
    # satin column cannot resolve curvature finer than its own width, so
    # measuring the direction over that distance discards nothing real.
    seg = [math.dist(spine[i], spine[i + 1]) for i in range(n - 1)]
    spacing = sorted(seg)[len(seg) // 2] if seg else 0.0
    k = 1 if spacing <= 0 else max(1, round(fallback_half_mm * _TANGENT_WIDTHS / spacing))

    raw: list[float] = []
    for i in range(n):
        a = spine[max(0, i - k)] if not closed else spine[(i - k) % n]
        b = spine[min(n - 1, i + k)] if not closed else spine[(i + k) % n]
        raw.append(math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2)

    def settle(angles: list[float]) -> list[float]:
        for i in range(1, n):
            while angles[i] - angles[i - 1] > math.pi / 2:
                angles[i] -= math.pi
            while angles[i] - angles[i - 1] < -math.pi / 2:
                angles[i] += math.pi
        for _ in range(6):
            prev = list(angles)
            for i in range(1, n - 1):
                angles[i] = (prev[i - 1] + prev[i] + prev[i + 1]) / 3.0
        return angles

    if angle_deg is None:
        return settle(list(raw)), [0.0] * n

    # The house angle: hold it where this stroke can span it, lean toward it
    # where it cannot (`_clamp_to_span`). Applied BEFORE the unwrap and the
    # smoothing so both still do their job -- a clamped sequence can still
    # step, and the smoothing is what keeps that step from becoming a
    # visible kink. The lean is read against the smoothed perpendicular the
    # stroke would otherwise carry, not the raw one, so a bend's own
    # smoothing does not count as lean.
    house = math.radians(angle_deg)
    plain = settle(list(raw))
    housed = settle([_clamp_to_span(house, a - math.pi / 2.0) for a in raw])
    leans = [abs((h - q + math.pi / 2.0) % math.pi - math.pi / 2.0)
             for h, q in zip(housed, plain)]
    return housed, leans


def _rail_points(poly: Polygon, spine: list[tuple[float, float]], closed: bool,
                 fallback_half_mm: float,
                 field: _WidthField | None = None,
                 spacing_mm: float = machine.SATIN_SPACING_MM,
                 angle_deg: float | None = None) -> tuple[list, list]:
    """Cast the smoothed, unwrapped normals both ways to find the two rails.

    Each rail is capped at ~1.6x the LOCAL medial half-width: at a branch
    junction the ray escapes the stroke's own ribbon and hits another arm's far
    boundary, and uncapped that draws an X of full-width crosses over the
    junction. Capped, each stroke covers its own corridor and the junction gets
    the modest overlap of its arms — which is exactly what a human digitizer
    does there.

    `spacing_mm` is the outer-rail density target the refinement pass below
    holds stations to (default `machine.SATIN_SPACING_MM`) — a caller-scaled
    number when the fabric preset's `density_adjust` applies (task A2), the
    bare constant otherwise, byte-identical to before that flag existed.
    """
    n = len(spine)
    boundary = poly.boundary
    angles, leans = _cross_angles(spine, closed, fallback_half_mm, angle_deg)

    reach = max(fallback_half_mm * 4.0, 2.0)
    rail_a: list = []
    rail_b: list = []
    norms: list[tuple[float, float]] = []
    raw: list[float] = []
    floors: list[float] = []
    for i, (px, py) in enumerate(spine):
        nx, ny = math.cos(angles[i]), math.sin(angles[i])

        def hit(dx: float, dy: float):
            ray = LineString([(px, py), (px + dx * reach, py + dy * reach)])
            inter = ray.intersection(boundary)
            if inter.is_empty:
                return None
            pts = []
            for g in getattr(inter, "geoms", [inter]):
                if g.geom_type == "Point":
                    pts.append((g.x, g.y))
                else:
                    pts.extend((c[0], c[1]) for c in g.coords)
            # The terminal station sits ON the boundary (the cap extension put
            # it there), so the nearest intersection is the station itself and
            # keeping it collapses the final cross to a point. Skipping
            # near-zero hits lets the tip's perpendicular ray run along the cap
            # face and land on the cap CORNERS — the square-end terminal stitch
            # a professional column finishes with.
            pts = [q for q in pts if (q[0] - px) ** 2 + (q[1] - py) ** 2 > 0.0025]
            if not pts:
                return None
            return min(pts, key=lambda q: (q[0] - px) ** 2 + (q[1] - py) ** 2)

        def fallback(dx: float, dy: float) -> tuple[float, float]:
            # No ray hit (a corner shadow, a cap tangent skimming the edge).
            # The guess must still be INSIDE the artwork: at free ends the
            # extended tangent can skew, and an unchecked guess put crosses
            # up to ~1 mm outside the C fixture. Shrink the guess until the
            # polygon covers it; a point at the station itself just makes a
            # degenerate cross that the minimum-cross rule drops.
            for f in (1.0, 0.6, 0.35, 0.15):
                q = (px + dx * fallback_half_mm * f, py + dy * fallback_half_mm * f)
                if poly.covers(SPoint(q)):
                    return q
            return (px, py)

        pa = hit(nx, ny) or fallback(nx, ny)
        pb = hit(-nx, -ny) or fallback(-nx, -ny)
        norms.append((nx, ny))
        # The HALF-WIDTH this sample is evidence for. The nearer of the two hits
        # is the honest one: a ray that escapes through a junction into the next
        # arm reports a distance belonging to a different part of the shape, and
        # it is always the longer of the pair.
        raw.append(min(math.dist((px, py), pa), math.dist((px, py), pb)))
        floors.append(max(field.half_at((px, py)), 0.75 * fallback_half_mm)
                      if field is not None else fallback_half_mm)

    # --- width profile -> parallel rails ----------------------------------
    #
    # The rails are PARALLEL OFFSETS of the spine at a smoothed half-width, not
    # two independently ray-cast boundary points. Casting per sample and taking
    # the nearest hit lets consecutive samples land on different boundary
    # features — one cross ends on the edge it belongs to, the next on the far
    # side of a junction — and clamping each side on its own then walks the
    # column's centre off its own spine. Measured on the real logo, 27% of
    # crosses ended up rotated more than 15 deg from the cross two before them:
    # that is the spray, and it is a property of the model, not a tuning error.
    #
    # The medial axis is equidistant from both edges by construction, so a
    # symmetric offset is the correct shape for a ribbon; a median filter drops
    # the junction escapes before the profile is smoothed, and the result is
    # capped by the local corridor so a cross can never span a junction.
    width = _median_filter(raw, _WIDTH_MEDIAN_WINDOW)
    for _ in range(_WIDTH_SMOOTH_PASSES):
        prev = list(width)
        for i in range(1, n - 1):
            width[i] = (prev[i - 1] + prev[i] + prev[i + 1]) / 3.0
    # Found and fixed 2026-08-05 (satin self-overlap). First read as a
    # junction measurement artifact (`field.half_at()` reporting a MERGED
    # footprint where several strokes meet) and a local-neighbourhood
    # outlier cap was tried -- reverted, disproven by direct inspection:
    # `logo_alpha.png`'s `Sf5200f3f` stroke 0 (a glyph's apex, both ends
    # FREE, no junction node on this stroke at all) profiles as a smooth,
    # continuous, single-peaked taper across all 36 of its own stations --
    # half-width ramping 0.17 -> 4.67mm -> 0.17mm, no isolated spike a local
    # window could tell apart from its neighbours, because EVERY neighbour
    # near the peak agrees. This is the shape's real medial-axis width, not
    # noise: an "A"-like apex genuinely is that wide where its two legs
    # converge. It is real width, but width the corpus never validates satin
    # crosses for at all -- `SATIN_MAX_WIDTH_MM` is exactly the ceiling this
    # module's own classifier gates satin-vs-fill on ("ribbons wider than
    # this sew better as fill", machine.py), the same one `_stroke_
    # underlay`'s oversize check and `SPLIT_SATIN_ABOVE_MM` already reuse for
    # the identical reason -- so a flat per-station cap at that ceiling,
    # not a new number, is the same "don't extrapolate into an unvalidated
    # regime" call this module already made twice. Measured on `Sf5200f3f`:
    # eliminates all 2580 non-adjacent self-crossing segment pairs the
    # uncapped peak produced and drops the shape's own isolated coverage
    # peak from 9.57 to 3.41 layers (`tests/test_satin.py::
    # test_satin_crosses_do_not_self_overlap_across_a_wide_junction`,
    # `tests/test_preflight.py::
    # test_a_wide_oversize_satin_stroke_does_not_block_on_underlay_glue`).
    #
    # This cap is a hard ceiling, not a proportional one, so it also (lightly)
    # touches a column whose GROWN width crosses the ceiling only because
    # directional pull comp (Law 22, axial) legitimately widened it a few
    # tenths of a millimetre past 5.0mm -- `tests/test_pushcomp.py`'s 4.5mm
    # bar grows to 5.1mm and loses ~0.02mm of that growth to this cap. That
    # is not a separate bug to route around: a satin cross this module will
    # not classify past 5.0mm in the first place should not be asked to sew
    # one past 5.0mm because comp grew it there either -- see that test's own
    # updated fixture comment.
    for i in range(n):
        width[i] = min(width[i], floors[i] * 1.6 + 0.2, machine.SATIN_MAX_WIDTH_MM / 2)

    # --- taper zones at free ends ------------------------------------------
    #
    # Where a stroke ends in a TAPERED TIP the corridor pinches to zero, and
    # the smoothed profile above — a median over neighbours — cannot follow
    # it down (it read 0.938 mm at the ribbon_curve tip whose true corridor
    # is 0). The containment fallback in `place` then decides the rails by
    # which discrete shrink factor happens to fit, and on the pinched side
    # the offsets jump between factors instead of ramping with the taper:
    # measured on ribbon_curve at 80 mm, the tip's pinched-side penetration
    # degenerated onto the spine (no factor fit), the next station's offset
    # popped to 0.93 mm — a 0.96 mm same-rail hole — and two stations later
    # the recovering offset cancelled the spine advance down to a 0.16 mm
    # crawl, tripping the short-stitch guard mid-taper. Capping the interior
    # taper-zone widths to the honest per-station ray measurement makes the
    # rails ramp with the taper itself: the same intervals measure 0.30-0.56.
    # The terminal station is NOT capped — its cross is the designed cap
    # finish — and a floor of half the minimum cross keeps a mid-zone ray
    # miss from collapsing a station that `place` can still fit.
    zs = ze = 0
    if not closed and n >= 4:
        while zs + 1 < n - 1 and raw[zs + 1] < _TAPER_ZONE_FRAC * fallback_half_mm:
            zs += 1
            width[zs] = min(width[zs],
                            max(raw[zs], machine.SATIN_MIN_CROSS_MM / 2))
        while ze + 1 < n - 1 - zs and \
                raw[n - 2 - ze] < _TAPER_ZONE_FRAC * fallback_half_mm:
            ze += 1
            width[n - 1 - ze] = min(width[n - 1 - ze],
                                    max(raw[n - 1 - ze], machine.SATIN_MIN_CROSS_MM / 2))

    # Containment still governs: a smoothed width can overshoot where the
    # ribbon pinches, and thread outside the artwork is the one defect this
    # module is never allowed to ship. Each side yields on its own — pulling
    # both in because one overshot drags the good rail off the artwork edge,
    # which is what left the fixture bar's cap bare by 0.06 mm.
    def place(px: float, py: float, sx: float, sy: float, w: float):
        for f in (1.0, 0.85, 0.7, 0.5, 0.3):
            q = (px + sx * w * f, py + sy * w * f)
            if poly.covers(SPoint(q)):
                return q
        return (px, py)

    for i, (px, py) in enumerate(spine):
        nx, ny = norms[i]
        rail_a.append(place(px, py, nx, ny, width[i]))
        rail_b.append(place(px, py, -nx, -ny, width[i]))

    # --- outer-rail density -----------------------------------------------
    #
    # Stations are spaced along the SPINE, but thread lands on the RAILS, and
    # on a bend the outer rail runs further than the spine by (half-width x
    # angle turned) — measured 0.59 mm between outer penetrations against the
    # 0.40 target on a tight ring, 47% under density. Where the faster rail
    # outruns SATIN_SPACING, extra stations are INTERPOLATED into that
    # interval: spine, normal angle, and width all lerp between two already
    # -filtered stations, so the proven profile is untouched, no new rays are
    # cast, and a straight column (every interval already at spacing) comes
    # out byte-identical. A first attempt fine-sampled the whole spine and
    # re-ran the profile instead — the width filters are sample-count-based,
    # so 3x sampling shrank their mm reach 3x and rail noise tripled (outer
    # p95 0.49 -> 1.04 mm). Interpolation is the version that does not touch
    # what already works.
    ref_a: list = [rail_a[0]]
    ref_b: list = [rail_b[0]]
    for i in range(1, n):
        # Only refine intervals that are genuinely over-wide: at exactly one
        # spacing, adv/SPACING is 1.0 plus float dust and a bare ceil() doubled
        # EVERY interval of a straight bar (measured: 120 crosses where 60
        # belong, alternating full and guard-mangled). And never refine the
        # cap zone — those stations are the deliberate terminal fan onto the
        # cap corners, and packing crosses into it rebuilds the starburst this
        # module exists to prevent. EXCEPT at a tapered tip: there is no fan
        # to protect (the rails pinch, the terminal cross is a fraction of the
        # column), and the tip's first interval is where the pinched rail
        # jumps — 0.96 mm on ribbon_curve — so the taper zone refines by the
        # same gate as everywhere else.
        in_taper = not closed and ((zs and i <= zs + 1)
                                   or (ze and i >= n - 1 - ze))
        near_cap = not closed and (i <= 2 or i >= n - 2) and not in_taper
        adv = max(math.dist(rail_a[i - 1], rail_a[i]),
                  math.dist(rail_b[i - 1], rail_b[i]))
        # Under a house angle the crosses may LEAN, and a leaned column's
        # penetrations are further apart along the rail than its threads
        # are apart across it, by 1/cos(lean) -- so the rail target here is
        # the same perpendicular pitch `_resample_by_pitch` spaced the
        # stations to, not the bare spacing. Lean 0 divides by exactly 1.0.
        pitch = spacing_mm / max(math.cos(0.5 * (leans[i - 1] + leans[i])),
                                 _LEAN_COS_FLOOR)
        if near_cap or adv <= pitch * 1.3:
            ref_a.append(rail_a[i])
            ref_b.append(rail_b[i])
            continue
        m = int(math.ceil(adv / pitch))
        if in_taper:
            # In the taper zone the pieces must also stay ABOVE the guard
            # threshold: a bare ceil splits a 0.53 mm interval into 0.26 mm
            # halves, the guard fires on every one, and the retracted points
            # read as fresh ~0.8 mm same-rail steps — the defect rebuilt by
            # its own repair (measured on the ribbon tail before this floor).
            m = max(1, min(m, int(adv / machine.SATIN_SHORT_STITCH_AT_MM)))
        for j in range(1, m):
            t = j / m
            px = spine[i - 1][0] * (1 - t) + spine[i][0] * t
            py = spine[i - 1][1] * (1 - t) + spine[i][1] * t
            ang = angles[i - 1] * (1 - t) + angles[i] * t   # unwrapped: lerp-safe
            w = width[i - 1] * (1 - t) + width[i] * t
            nx, ny = math.cos(ang), math.sin(ang)
            ref_a.append(place(px, py, nx, ny, w))
            ref_b.append(place(px, py, -nx, -ny, w))
        ref_a.append(rail_a[i])
        ref_b.append(rail_b[i])
    return ref_a, ref_b


def _short_stitch_guard(rail_a: list, rail_b: list) -> list[tuple]:
    """Shorten alternate crosses where a rail's penetrations bunch up.

    -> [(pa, pb), ...] with the crowded side of every other cross pulled toward
    the middle. On the inside of a curve the rail is shorter than the spine, so
    penetrations land closer together than the satin spacing; below the
    threshold the needle starts re-entering the same hole and the edge frays.

    The pull is a FRACTION of the cross capped at an ABSOLUTE distance. Its job
    is to clear the previous needle hole, and a hole is the same size whatever
    the column width — but a plain fraction scales with the column, and on a
    wide column it threw the retracted penetration far past where any hole
    could be: 0.35 x a 2.78 mm cross moved the point 0.97 mm off its rail,
    which any rail-based density read (the pinned tests, tools/audit.py) sees
    as two ~1.0 mm same-rail gaps. Capped, the same stitch retracts 0.6 mm —
    two same-hole radii: a full radius clear of the old hole, still supporting
    the inner edge it was pulled from.

    Found and fixed 2026-08-07 (satin free-end corner coverage). The pull is
    ALSO bounded so it can never take a cross under `SATIN_MIN_CROSS_MM`
    itself — without that, a cross that was a legitimate, keepable stitch
    (comfortably above the floor) came out of the pull thinner than the
    floor and `satin_stroke`'s own degenerate-cross filter dropped it a few
    lines later, for a reason that has nothing to do with why the filter
    exists (a real pinch, both rails meeting at a point). Measured on
    `photo/enthusiast_logo.png`'s "E": the free end at the glyph's stem
    caps 0.15mm from its own flush corner (`_extend_to_cap` already lands it
    there), and the very next station's cross is a real 0.57-0.60mm stitch —
    comfortably keepable on its own — until this guard fires (that station's
    same-rail step off the cap station is 0.27mm, under
    `SATIN_SHORT_STITCH_AT_MM`) and its stock 35%-capped-at-0.6mm pull takes
    it to 0.37-0.39mm, under the 0.5mm floor: the filter drops it, and the
    corner sews as bare fabric even though `_extend_to_cap` did its job.
    This is not a letterform-specific fix — any cap zone, corner, or tight
    curve whose next-station cross starts out only a little above
    `SATIN_MIN_CROSS_MM` can hit the identical interaction, independent of
    what put the crosses there. A curve with real room to spare (the guard's
    normal case, columns several mm wide) never reaches this new bound —
    only a pull that would have landed the result below the floor is
    reined in, to land AT the floor instead of past it.
    """
    out = []
    for i, (pa, pb) in enumerate(zip(rail_a, rail_b)):
        if 0 < i and i % 2 == 1:
            if math.dist(pa, rail_a[i - 1]) < machine.SATIN_SHORT_STITCH_AT_MM:
                pa = _pull_short(pa, pb)
            if math.dist(pb, rail_b[i - 1]) < machine.SATIN_SHORT_STITCH_AT_MM:
                pb = _pull_short(pb, pa)
        out.append((pa, pb))
    return out


def _pull_short(p: tuple, toward: tuple) -> tuple:
    """Retract one penetration toward the far rail, by fraction-with-a-cap.

    Never past the point where the cross itself would drop under
    `SATIN_MIN_CROSS_MM` — see `_short_stitch_guard`'s own note on why a
    pull that starts from an already-narrow cross needs that floor too. The
    target is nudged a hair above the exact floor (1.01x, not 1.0x) so a
    cross landing there clears `satin_stroke`'s strict `<` drop check
    despite float rounding in the two `dist()` calls along the way — the
    floor is a keepability guarantee, not a value that needs to be exact.
    """
    cross = math.dist(p, toward)
    f = machine.SATIN_SHORT_STITCH_PULL
    if cross > 1e-9:
        f = min(f, machine.SATIN_SHORT_STITCH_PULL_MAX_MM / cross)
        f = min(f, max(0.0, 1.0 - 1.01 * machine.SATIN_MIN_CROSS_MM / cross))
    return (p[0] + (toward[0] - p[0]) * f, p[1] + (toward[1] - p[1]) * f)


# --- The column ------------------------------------------------------------

def _extend_to_cap(spine: list[tuple[float, float]], poly: Polygon, half_mm: float,
                   at_start: bool, corner: bool = False) -> list[tuple[float, float]]:
    """Push a free spine end out to the shape's cap edge along its tangent.

    The medial axis of a stroke stops half a width short of each cap (the
    skeleton of a rectangle ends where the corner diagonals meet), so a column
    built on the raw spine leaves the cap unsewn — measured at 1.8 mm of bare
    fabric per end on the fixture bar. Extending along the end tangent until
    the boundary puts the final cross ON the cap edge, which is where a
    professional column ends. Degenerate crosses in a tapering tip are dropped
    later by the minimum-cross rule, so overshooting into a point is safe.
    """
    pts = list(reversed(spine)) if at_start else list(spine)
    if len(pts) < 2:
        return spine
    tip = pts[-1]
    prev = pts[-2]
    if corner:
        # At a CORNER end the direction is the chord back over one stroke
        # width, not the last segment. A raster spine's final segment is a
        # sixth of a millimetre of staircase and can point anywhere within
        # 45 deg of the truth, and the extension multiplies that error by its
        # own length: measured on the E fixture's stem, whose skeleton now
        # ends at the corner node itself, the last segment ran 26 deg off the
        # stem's own axis and threw the cap 0.6 mm sideways — far enough that
        # the flush corner the cap exists to cover came out bare. Same
        # reasoning as `_rail_points`'s tangent baseline: a column cannot
        # resolve direction finer than its own width.
        #
        # Only at a corner end. A spine that ends where the SKELETON ends has
        # been through spur pruning and `_retract_cap_corner` and is aimed by
        # its own last segment on purpose, and re-aiming it moves stitches on
        # every flat fixture — the byte-identical goldens are the contract
        # that says don't.
        back = 2.0 * half_mm if half_mm > 0 else 0.0
        walked = 0.0
        for j in range(len(pts) - 1, 0, -1):
            walked += math.dist(pts[j], pts[j - 1])
            prev = pts[j - 1]
            if walked >= back:
                break
    d = math.dist(prev, tip)
    if d < 1e-9:
        return spine
    ux, uy = (tip[0] - prev[0]) / d, (tip[1] - prev[1]) / d
    # Long enough to still find the cap after `_retract_cap_corner` has walked
    # the end back in. The nearest hit is the one taken, so a longer ray can
    # only find a cap where there was none — never move one.
    reach = half_mm * 4.5 + 0.5
    ray = LineString([tip, (tip[0] + ux * reach, tip[1] + uy * reach)])
    inter = ray.intersection(poly.boundary)
    if inter.is_empty:
        return spine
    cands = []
    for g in getattr(inter, "geoms", [inter]):
        if g.geom_type == "Point":
            cands.append((g.x, g.y))
        else:
            cands.extend((c[0], c[1]) for c in g.coords)
    if not cands:
        return spine
    cap = min(cands, key=lambda q: (q[0] - tip[0]) ** 2 + (q[1] - tip[1]) ** 2)
    # At a CORNER cap, a hair inside rather than exactly on. The terminal
    # station's cross runs along the cap face, and `_rail_points` only keeps a
    # rail point the polygon covers: from a station sitting exactly ON the
    # boundary, a normal that rounds a hundredth of a millimetre to the outside
    # loses that whole side of the cross, and the cap sews as half a stitch.
    # Measured on the E fixture's stem cap, whose normal tilts 0.8 deg off the
    # cap face: the left rail landed 0.012 mm outside, every containment
    # fallback with it, and the corner the cap exists to cover came out 0.5 mm
    # bare. `corner` is only true for the ends `_merge_through_junctions`
    # opened up, whose cap is a square letterform edge — a TAPERED tip is a
    # different geometry (its corridor is pinching, so stepping back widens the
    # terminal cross and opens a rail gap: measured 0.82 mm on ribbon_curve)
    # and keeps today's exact behaviour.
    if corner:
        ins = min(_CAP_INSET_MM, 0.25 * math.dist(cap, tip))
        if ins > 0:
            cap = (cap[0] - ux * ins, cap[1] - uy * ins)
    pts.append(cap)
    return list(reversed(pts)) if at_start else pts


# How far short of the artwork edge a cap-extended station stops. Small enough
# to be under a tenth of a satin spacing, large enough to swallow the normal's
# own rounding at the terminal cross — see `_extend_to_cap`.
_CAP_INSET_MM = 0.03

# A free end whose corridor is narrower than this fraction of the stroke's own
# half-width is not the stroke any more, it is a cap corner.
_CAP_CORNER_FRAC = 0.8
# Never chase a corner further in than this many half-widths: on a genuinely
# tapering stroke the corridor narrows all the way and there is nothing wrong
# with that.
_CAP_CORNER_REACH_HALFWIDTHS = 1.5


def _retract_cap_corner(spine: list[tuple[float, float]], field: _WidthField | None,
                        half_mm: float, at_start: bool) -> list[tuple[float, float]]:
    """Walk a free spine end back out of the cap corner it ran into.

    A flat cap's medial axis forks toward the two corners. Spur pruning removes
    most of each fork, but what survives leaves the last millimetre of the
    spine running diagonally at a corner instead of down the middle of the
    stroke. Every cross built on that stretch pivots on the same needle hole
    and swings across the cap — the starburst measured on the curved-ribbon
    case: five penetrations in one hole and 3.3 mm crosses on a 2.8 mm ribbon,
    thread laid outside the artwork at the tip and the cap itself left bare.

    The corridor width is the tell — at a corner the distance transform reads a
    fraction of the stroke's half-width. Walk in until it does not, and let
    `_extend_to_cap` rebuild a square end from a point that is genuinely in the
    middle of the stroke.
    """
    if field is None or len(spine) < 4 or half_mm <= 0:
        return spine
    pts = list(reversed(spine)) if at_start else list(spine)
    floor = _CAP_CORNER_FRAC * half_mm
    budget = _CAP_CORNER_REACH_HALFWIDTHS * half_mm
    eaten = 0.0
    cut = 0
    for i in range(len(pts) - 1, 1, -1):
        if field.half_at(pts[i]) >= floor:
            break
        eaten += math.dist(pts[i], pts[i - 1])
        if eaten > budget:
            break
        cut += 1
    if not cut:
        return spine
    pts = pts[: len(pts) - cut]
    return list(reversed(pts)) if at_start else pts


def _trim_chain(pts: list[tuple[float, float]], from_start_mm: float,
                from_end_mm: float) -> list[tuple[float, float]]:
    line = LineString(pts)
    s0, s1 = from_start_mm, line.length - from_end_mm
    if line.length <= 0 or s1 - s0 < 0.5:
        return list(pts)
    n = max(2, int(math.ceil((s1 - s0) / 0.2)))
    return [(p.x, p.y) for p in (line.interpolate(s0 + (s1 - s0) * i / (n - 1)) for i in range(n))]


# How far a stroke reaches under the arm it joins at a junction. Enough that
# fabric pull cannot open a gap between stem and bar, small enough that the
# doubled coverage never reads as a lump.
_JUNCTION_TUCK_MM = 0.4

# --- where an arm's own ribbon begins, at a junction-anchored end -----------
#
# The corridor is walked in these steps. The distance transform is quantised
# at the raster pitch (1 / _RASTER_PX_PER_MM = 0.167 mm), so "the corridor
# stopped narrowing" has to tolerate about one quantum of staircase noise
# before it will fire on a genuinely flat stretch.
_JUNCTION_STEP_MM = 0.2
_JUNCTION_STABLE_MM = 0.10
# ... and it has to HOLD for this far to count. Measured plateaus on real
# corpus letterforms: `becker_lc_large`'s "E" (S0cdd6202) stroke 2 holds
# 2.33 mm from 1.25 to 3.75 mm in, its "R" (S6a8697e1) stroke 0 holds 2.17 mm
# from 2.0 mm in, and the pinned T_SHORT_STEM fixture's stem holds its 1.5 mm
# half-width for the stem's whole 6 mm. 0.6 mm is comfortably under the
# shortest of those and comfortably over one raster quantum.
_JUNCTION_PLATEAU_MM = 0.6
# The junction's influence does not reach further in than this many of the
# shape's half-widths, so neither does the search. Past it a stroke is simply
# in its own body and the fixed offset stands — a plateau found 40 mm down a
# 90 mm column is not "where this arm's ribbon begins", it is just the column.
_JUNCTION_REACH_HALFWIDTHS = 3.0


def _junction_entry_mm(spine: list[tuple[float, float]], field: _WidthField | None,
                       half_mm: float, at_start: bool) -> float | None:
    """How far in from a junction-anchored end this arm's own ribbon starts.

    -> mm along the spine, or None when the arm never has a ribbon at all.

    The end trim at a junction exists because the skeleton's branch node sits
    in the MIDDLE of the junction, not at its edge: the node of a T is halfway
    up the bar, so an untrimmed stem sews back across crosses the bar already
    laid down. `field.half_at(node)` is the obvious offset and it is exactly
    right on a clean T — the node's distance transform IS the bar's half-width
    there, so stepping that far puts the stem's first cross on the bar's edge.

    It stops being right on a real letterform, because `half_at` is an
    OMNIDIRECTIONAL clearance: at a corner or a 3+-arm meeting the widest
    thing near the node is a diagonal across the whole blob, not the arm the
    stroke has to clear. Measured on `becker_lc_large`'s "E", whose stroke
    half-width is 1.75 mm: the top-bar arm reads `half_at` 2.67 at its node
    and its corridor is already flat at 2.33 by 1.25 mm in — the fixed rule
    steps 2.27 mm and eats a full millimetre of ribbon that was never part of
    the junction. Walking in until the corridor STOPS NARROWING finds where
    the blob ends and the arm begins.

    On a clean T that walk returns 0 — the corridor is flat from the node up,
    because there is no blob, just two equal ribbons crossing. 0 is not the
    answer there (it would sew the stem back across the bar), which is why
    `satin_stroke` floors this against the stroke's own half-width rather
    than using it raw; see the bounds note at the call site.

    None means the arm never has a ribbon at all: thinning a bold corner forks
    the skeleton diagonally into the corner and leaves a 3-4 mm twig whose
    corridor falls from the blob straight to the point, with no flat stretch
    anywhere along it — measured on the same "E", 2.33 mm at the node down to
    0.17 mm at the tip in a near-constant 0.66 mm-per-mm ramp. There is no
    ribbon in such a twig to find the start of: it is a wedge, and a zigzag
    across a wedge is the radiating fan this module exists to prevent.

    This function does NOT decide those twigs' fate, and an earlier version of
    it that did was wrong to. `satin_stroke` used to drop a no-plateau arm
    outright when it was also short, and that left BARE FABRIC — 9.95 mm² of
    it on `hotel_fremont_patch`, including a 5.41 mm² hole in the "N" of
    FREMONT — because a corner twig is only safe to discard once something
    else is known to cover the corner it occupies, and a length bound cannot
    know that. `_corner_forks` is where that call belongs: it classifies the
    same geometry BEFORE welding, and hands the corner to a named arm that
    extends over it. Here, None simply means "no honest inward reading", and
    the caller falls back to the `half_at` ceiling.
    """
    if field is None or len(spine) < 2 or half_mm <= 0:
        return 0.0
    pts = list(spine) if at_start else list(reversed(spine))
    line = LineString(pts)
    length = line.length
    if length <= 0:
        return 0.0
    reach = min(length, _JUNCTION_REACH_HALFWIDTHS * half_mm)
    n = int(reach / _JUNCTION_STEP_MM)
    halves = []
    for k in range(n + 1):
        p = line.interpolate(min(k * _JUNCTION_STEP_MM, length))
        halves.append(field.half_at((p.x, p.y)))
    hold = max(1, int(round(_JUNCTION_PLATEAU_MM / _JUNCTION_STEP_MM)))
    for i in range(len(halves)):
        if i + hold >= len(halves):
            break   # only the taper into the far end is left: no plateau here
        if all(halves[j] >= halves[j - 1] - _JUNCTION_STABLE_MM
               for j in range(i + 1, i + 1 + hold)):
            return min(i * _JUNCTION_STEP_MM, length)
    return None


def _round_corners(spine: list[tuple[float, float]], half_mm: float,
                   closed: bool) -> list[tuple[float, float]]:
    """Spread each sharp corner's turn across about one column width.

    The professional in-run corner (every file in the corpus) is a gradual
    fan: crosses rotate a few degrees each, spokes around the bend. That falls
    out of the geometry only if the SPINE bends gradually — a hard apex packs
    the whole turn into the two or three crosses nearest it, which is the
    uncontrolled sweep the N junction showed once splitting was demoted.
    Extra smoothing passes confined to a window around each apex turn the
    corner into an arc of roughly the column's own radius; straight stretches
    keep their exact line because the window never reaches them.
    """
    n = len(spine)
    if n < 5 or half_mm <= 0:
        return spine
    seg = [math.dist(spine[i], spine[i + 1]) for i in range(n - 1)]
    spacing = sorted(seg)[len(seg) // 2] if seg else 0.0
    if spacing <= 0:
        return spine
    k = max(1, round(half_mm / spacing))
    sm = _smooth(spine, 3, closed)
    apexes: list[int] = []
    idx = range(n) if closed else range(k, n - k)
    for i in idx:
        a, b, c = sm[(i - k) % n], sm[i], sm[(i + k) % n]
        d1 = math.atan2(b[1] - a[1], b[0] - a[0])
        d2 = math.atan2(c[1] - b[1], c[0] - b[0])
        turn = abs(math.degrees((d2 - d1 + math.pi) % (2 * math.pi) - math.pi))
        if turn >= 30.0 and (not apexes or i - apexes[-1] > k):
            apexes.append(i)
    if not apexes:
        return spine
    out = list(spine)
    for ap in apexes:
        lo, hi = ap - k, ap + k
        for _ in range(8):
            prev = list(out)
            for i in range(lo, hi + 1):
                j = i % n if closed else i
                if not closed and (j <= 0 or j >= n - 1):
                    continue
                a, b, c = prev[(j - 1) % n], prev[j], prev[(j + 1) % n]
                out[j] = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)
    return out


def _split_points(pa: tuple[float, float], pb: tuple[float, float],
                  station: int, above_mm: float) -> list[tuple[float, float]]:
    """Intermediate penetrations for one cross, or [] when it needs none.

    A cross longer than `above_mm` is divided into k = ceil(len /
    SPLIT_SEGMENT_MM) segments with penetrations at j/k along it, the whole
    comb shifted by the station's phase of the stagger wave so consecutive
    stations never stack their holes (corpus: aligned split holes are the
    minority, 131 columns of 1,922 — see machine.py for all the numbers).

    Points are exact lerps on the A->B segment: `strip_splits` depends on
    that collinearity to remove them exactly. The shift is +-0.23 of one
    segment, so the shortest end segment is 0.77 * len/k — above 1.9 mm at
    the 5.0 threshold, comfortably clear of MIN_STITCH_MM — and the longest
    is 1.23 * len/k, under 3.7 mm for any splittable cross up to the format
    ceiling.
    """
    cross = math.dist(pa, pb)
    if cross <= above_mm:
        return []
    k = int(math.ceil(cross / machine.SPLIT_SEGMENT_MM))
    wave = machine.SPLIT_STAGGER_WAVE[station % machine.SPLIT_STAGGER_PERIOD]
    shift = machine.SPLIT_STAGGER_STEP_SEGS * wave
    out = []
    for j in range(1, k):
        t = (j + shift) / k
        out.append((pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t))
    return out


def _on_segment(a: tuple, p: tuple, b: tuple, eps: float = 1e-6) -> bool:
    """Is p strictly between a and b, on the segment to within eps mm?"""
    abx, aby = b[0] - a[0], b[1] - a[1]
    apx, apy = p[0] - a[0], p[1] - a[1]
    len2 = abx * abx + aby * aby
    if len2 <= eps * eps:
        return False
    if abs(apx * aby - apy * abx) > eps * math.sqrt(len2):
        return False
    t = (apx * abx + apy * aby) / len2
    return 0.0 < t < 1.0


def strip_splits(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """A satin run's points with split penetrations removed — rails only.

    The exact inverse of `_split_points`, for any instrument that reads a
    run's points as alternating rail penetrations: split points lie ON the
    segment between their neighbours (they are lerps along the cross), and no
    real rail penetration ever can — consecutive rail points always turn,
    because the return leg reverses direction and degenerate crosses are
    dropped at SATIN_MIN_CROSS_MM. Same reading contract as
    `stitches.strip_ties`; strip ties first on plan-level runs (tie bounces
    revisit one point, so their zero-length base segments never read as
    collinear here).
    """
    if len(points) < 3:
        return list(points)
    out = [points[0]]
    for i in range(1, len(points) - 1):
        if _on_segment(out[-1], points[i], points[i + 1]):
            continue
        out.append(points[i])
    out.append(points[-1])
    return out


def _member_corridor(piece: list[tuple[float, float]], from_start: bool,
                     field: _WidthField | None, half_mm: float) -> float:
    """A member's own half-width just past the corner blob: the median
    corridor between one and three half-widths in from its corner end;
    `half_mm` when the member is too short to read or there is no field."""
    if field is None:
        return half_mm
    seq = piece if from_start else list(reversed(piece))
    line = LineString(seq)
    lo, hi = half_mm, min(3.0 * half_mm, line.length)
    if hi <= lo:
        return half_mm
    vals = [field.half_at((q.x, q.y)) for q in
            (line.interpolate(lo + (hi - lo) * t / 6.0) for t in range(7))]
    return sorted(vals)[len(vals) // 2] or half_mm


def _satin_joined(poly: Polygon, stroke: Stroke, half_mm: float,
                  field: _WidthField | None, split_above_mm: float | None,
                  end_cutback_mm: float, spacing_mm: float,
                  angle_deg: float | None) -> list[tuple[float, float]]:
    """A stroke with Goldman corners (`Stroke.corners`) -> its members sewn as
    separate columns and laid end to end in chain order.

    At each corner the OWNER's end is a capped free end -- `_extend_to_cap`
    runs its column out to the artwork edge, over the corner square -- and
    the other member's end is a junction-style end tucking under the owner's
    own corridor (`tuck_under_*`), the way a T's stem tucks under its bar.
    The hop between consecutive members is the corner itself: from the first
    member's last cross to the second's first, inside the corner square,
    under the owner's column when the butting member sews first and lapped
    over its cap when the owner does -- both are corners the trade sews.
    """
    pts = stroke.spine
    edges_ = [0, *[c[0] for c in stroke.corners], len(pts) - 1]
    owners = [c[1] for c in stroke.corners]
    out: list[tuple[float, float]] = []
    for m, (s0, s1) in enumerate(zip(edges_, edges_[1:])):
        piece = pts[s0:s1 + 1]
        if len(piece) < 2:
            continue
        if m == 0:
            free_s, capped_s, tuck_s = stroke.free_start, stroke.capped_start, stroke.tuck_under_start
        elif owners[m - 1]:                    # the member before owns
            free_s, capped_s = False, False
            tuck_s = _member_corridor(pts[edges_[m - 1]:s0 + 1], False, field, half_mm)
        else:
            free_s, capped_s, tuck_s = True, True, None
        if m == len(edges_) - 2:
            free_e, capped_e, tuck_e = stroke.free_end, stroke.capped_end, stroke.tuck_under_end
        elif owners[m]:                        # this member owns
            free_e, capped_e, tuck_e = True, True, None
        else:
            free_e, capped_e = False, False
            tuck_e = _member_corridor(pts[s1:edges_[m + 2] + 1], True, field, half_mm)
        member = Stroke(spine=piece, free_start=free_s, free_end=free_e, closed=False,
                        capped_start=capped_s, capped_end=capped_e,
                        tuck_under_start=tuck_s, tuck_under_end=tuck_e)
        pts_m = satin_stroke(poly, member, half_mm, field, split_above_mm,
                             end_cutback_mm, spacing_mm, angle_deg)
        if out and pts_m:
            # The seam hop across the corner is a stitch like any other and
            # splits like its neighbours when it is over the length cap.
            above = machine.SPLIT_SATIN_ABOVE_MM if split_above_mm is None else split_above_mm
            out.extend(_split_points(out[-1], pts_m[0], 0, above))
        out.extend(pts_m)
    return out


def satin_stroke(poly: Polygon, stroke: Stroke, half_mm: float,
                 field: _WidthField | None = None,
                 split_above_mm: float | None = None,
                 end_cutback_mm: float = 0.0,
                 spacing_mm: float = machine.SATIN_SPACING_MM,
                 angle_deg: float | None = None) -> list[tuple[float, float]]:
    """One stroke -> flat zigzag points (A1, B1, A2, B2, ...).

    `angle_deg` is the house cross angle for satin lettering (2026-08-26).
    None -- the default, and what every caller that never mentions it gets --
    keeps today's output exactly: each cross perpendicular to this stroke's own
    spine tangent. A number holds that angle wherever the stroke can span it;
    see `_clamp_to_span` for why it is a clamp and not an assignment.

    `spacing_mm` (task A2, default `machine.SATIN_SPACING_MM`) is the
    along-column cross spacing this stroke targets — every caller before the
    fabric preset's `density_adjust` reached satin left it at the bare
    constant, so this is byte-identical unless a caller passes a different
    number.

    Rails strictly alternate, so EVERY consecutive pair of points is a stitch
    that crosses the column: the outbound leg A(i)->B(i) square across, the
    return leg B(i)->A(i+1) leaning one spacing forward. That is what a satin
    column is on the machine.

    One exception, and it is fenced: a cross longer than `split_above_mm`
    (None = machine.SPLIT_SATIN_ABOVE_MM) carries intermediate split
    penetrations between its rail points — see the module docstring for the
    contract and `strip_splits` for the exact way back to pure rails.

    `end_cutback_mm` is push compensation (Law 24), applied to OPEN ends only.
    Zero is the shipped behaviour; stage 7 supplies the number when
    `PipelineConfig.directional_comp` is on.
    """
    if stroke.corners:
        return _satin_joined(poly, stroke, half_mm, field, split_above_mm,
                             end_cutback_mm, spacing_mm, angle_deg)

    spine = _smooth(stroke.spine, 3, stroke.closed)
    spine = _round_corners(spine, half_mm, stroke.closed)

    # An end at a branch NODE sits in the middle of the junction — the skeleton
    # of a T puts the node halfway up the bar, so an untrimmed stem sews right
    # across crosses the bar already laid down. Step back to the junction edge
    # plus a small tuck; the free ends, by contrast, get EXTENDED to the cap.
    #
    # `field.half_at(node)` is the starting answer and the CEILING: it is an
    # omnidirectional clearance, so it is never too small, only too generous.
    # Two independent readings are allowed to walk it back in, and both only
    # ever GIVE RIBBON BACK — neither can trim more than the old rule did:
    #
    #  * `_junction_entry_mm` walks this arm's own corridor inward until it
    #    stops narrowing. On a clean T that agrees with `half_at`; on a real
    #    letterform's corner blob the blob reading is a diagonal across the
    #    whole corner and eats a millimetre of ribbon that was never part of
    #    the junction. Floored at the shape's own half-width, because whatever
    #    arm this one meets is at least that wide and has to be cleared —
    #    without the floor both arms of a corner recover past each other and
    #    sew the corner TWICE (measured on `becker_lc_large`'s "E"). The floor
    #    is also what makes this a no-op on a clean junction: on T_SHAPE and
    #    T_SHORT_STEM `half_at(node)` IS the stroke half-width, so the bounds
    #    coincide and the trim is bit-for-bit what it was before.
    #
    #  * `stroke.tuck_under_*` is set where this end is known to be tucking
    #    under ONE identified neighbour rather than into a meeting of several
    #    (see `_corner_forks`). That neighbour's own measured corridor is the
    #    honest number, and it is the only reading here that knows WHICH arm
    #    has to be cleared rather than how much room there is in every
    #    direction at once.
    if not stroke.closed and field is not None:
        trims = []
        for at_start in (True, False):
            free = stroke.free_start if at_start else stroke.free_end
            if free:
                trims.append(0.0)
                continue
            end = spine[0] if at_start else spine[-1]
            under = stroke.tuck_under_start if at_start else stroke.tuck_under_end
            edge = field.half_at(end)
            if under is not None:
                edge = min(edge, under)
            entry = _junction_entry_mm(spine, field, half_mm, at_start)
            if entry is not None:
                edge = min(edge, max(entry, half_mm))
            trims.append(max(0.0, edge - _JUNCTION_TUCK_MM))
        if trims[0] or trims[1]:
            spine = _trim_chain(spine, trims[0], trims[1])

    if stroke.free_start:
        spine = _retract_cap_corner(spine, field, half_mm, at_start=True)
        spine = _extend_to_cap(spine, poly, half_mm, at_start=True,
                               corner=stroke.capped_start)
    if stroke.free_end:
        spine = _retract_cap_corner(spine, field, half_mm, at_start=False)
        spine = _extend_to_cap(spine, poly, half_mm, at_start=False,
                               corner=stroke.capped_end)

    # Push compensation (Law 24). Pull comp is a WIDTH and stage 5 owns it;
    # push is a LENGTH and only this line of the pipeline knows where a column's
    # length ends. The stitches run across the column, so the fabric their
    # tension gathers is shoved out the ends — a column sewn flush to the
    # artwork cap lands past it, which is exactly what a border is later asked
    # to hide. Cutting the last cross back fixes it at the source.
    #
    # Only OPEN ends: an end at a junction is not a cap, it is tucked under the
    # arm it meets (`_JUNCTION_TUCK_MM` above), and shortening it would open the
    # gap that tuck exists to close. A closed stroke has no ends at all.
    #
    # `_trim_chain` leaves a stroke alone when the cutbacks would take it under
    # half a millimetre, so a short stub degrades to today's behaviour instead
    # of vanishing.
    if end_cutback_mm > 0 and not stroke.closed:
        c0 = end_cutback_mm if stroke.free_start else 0.0
        c1 = end_cutback_mm if stroke.free_end else 0.0
        if c0 or c1:
            spine = _trim_chain(spine, c0, c1)

    length = sum(math.dist(a, b) for a, b in zip(spine, spine[1:]))
    if length <= 0:
        return []

    steps = max(2, int(math.ceil(length / spacing_mm)))
    spine = _resample(spine, steps)
    if angle_deg is not None:
        # Density compensation for lean (2026-09-03): read how far each
        # station's cross will lean off its perpendicular under the house
        # angle, then re-station the spine so the pitch ACROSS the threads
        # is `spacing_mm` -- see `_resample_by_pitch`. Skipped when nothing
        # leans, so a column the house already runs square across keeps the
        # stations `_resample` gave it.
        _angles, leans = _cross_angles(spine, stroke.closed, half_mm, angle_deg)
        if max(leans) > 1e-6:
            spine = _resample_by_pitch(spine, leans, spacing_mm)
    rail_a, rail_b = _rail_points(poly, spine, stroke.closed, half_mm, field,
                                  spacing_mm, angle_deg)
    crosses = _short_stitch_guard(rail_a, rail_b)
    above = machine.SPLIT_SATIN_ABOVE_MM if split_above_mm is None else split_above_mm

    out: list[tuple[float, float]] = []
    prev_kept: tuple | None = None
    kept = 0
    for i, (pa, pb) in enumerate(crosses):
        if math.dist(pa, pb) < machine.SATIN_MIN_CROSS_MM:
            continue  # rails pinched together: shared tip or degenerate cap
        # Corridor capping at a junction can leave consecutive crosses nearly
        # coincident — both penetrations landing in the previous needle holes.
        if prev_kept is not None and \
                math.dist(pa, prev_kept[0]) < 0.05 and math.dist(pb, prev_kept[1]) < 0.05:
            continue
        prev_kept = (pa, pb)
        # Rail order is CONSTANT: A, B, A, B, ... Flipping alternate crosses to
        # (B, A) makes consecutive crosses meet on the same rail, and the step
        # between them is then a hop ALONG that rail — one satin spacing long,
        # 0.41 mm measured, into the hole the previous penetration just made.
        # Keeping the order constant turns that step into the RETURN LEG of the
        # zigzag: same two penetrations, but the thread crosses the column
        # instead of running up its edge.
        #
        # An over-threshold stitch gets its split penetrations HERE, between
        # its rail points, from the final guarded geometry — so the guard,
        # the dedup and the rail order never see them. BOTH legs split: the
        # return leg B(i)->A(i+1) spans the same column as the cross (one
        # spacing of lean longer), and the corpus's split columns split every
        # traverse in both directions — splitting only the outbound leg would
        # leave every other stitch over-length. Stagger phase runs on the
        # KEPT-station count: dropped stations must not advance the wave.
        if out:
            out.extend(_split_points(out[-1], pa, kept, above))
        out.append(pa)
        out.extend(_split_points(pa, pb, kept, above))
        out.append(pb)
        kept += 1
    return out


def _stroke_underlay(poly: Polygon, st: Stroke, style: str, shape_id: str,
                     field: _WidthField | None) -> list[StitchRun]:
    """Underlay for ONE stroke: a center run down its spine, plus a sparse
    zigzag for the styles that ask for it. Built from the same spine the satin
    will follow, so it always sits under the column."""
    if style == "none":
        return []
    runs: list[StitchRun] = []
    spine = _smooth(st.spine, 3, st.closed)
    length = sum(math.dist(a, b) for a, b in zip(spine, spine[1:]))
    if length < machine.UNDERLAY_STITCH_MM:
        return []
    n = max(2, int(math.ceil(length / machine.UNDERLAY_STITCH_MM)))
    runs.append(StitchRun(points=_resample(spine, n), kind=stitches.UNDERLAY,
                          shape_id=shape_id))
    # Law 23's 1.45mm pitch / 0.82x-width figures are corpus-measured over
    # columns up to the corpus's own 4.5-7.0mm width bucket (docs/corpus-
    # laws-round3-2026-08-01.md law 22/23) -- and satin classification
    # (`is_satin_candidate`) gates on a shape's MEAN width (`ribbon_width_
    # mm`), so a multi-stroke glyph can stay classified satin overall while
    # one skeleton stroke's own LOCAL corridor runs well past SATIN_MAX_
    # WIDTH_MM (measured on `logo_alpha.png`'s `Sf5200f3f`: shape mean
    # ~5.0mm, one stroke's local width 0.33-10.33mm). The corpus's own
    # >7.0mm bucket is flagged "junk" (82% non-ribbon fragments) in that
    # same doc, so neither law 23's new figures nor the pre-law-23 defaults
    # were ever validated for a corridor that wide -- extrapolating either
    # one is a guess, not a corpus finding. Skip the zigzag pass entirely
    # for a stroke whose local width anywhere exceeds SATIN_MAX_WIDTH_MM
    # (the same corpus-validated ceiling `SPLIT_SATIN_ABOVE_MM` already
    # reuses, not a new number): the center-run walk above still covers it,
    # which is the honest, corpus-supported fallback rather than a chosen
    # pitch/width for a regime nobody measured.
    #
    # Found and fixed 2026-08-05: an independent stitch-geometry audit of
    # the initial law 23 landing caught `logo_alpha.png`'s DENSITY_STACKED
    # finding flipping warn -> block on exactly this shape (coverage_max
    # 13.11 -> 16.69, peak driven by the satin crosses' own pre-existing
    # self-overlap on this wide/blob stroke -- unrelated to law 23 and
    # unchanged by THIS fix -- with the widened, denser zigzag underlay
    # supplying just enough extra "glue" thread to bridge that pre-existing
    # near-miss over `_COVERAGE_MIN_PATCH_MM2`'s 25mm2 connected-patch
    # gate). See test_preflight.py's logo_alpha regression test.
    #
    # The self-overlap itself is FIXED, same day, separate pass: see
    # `_rail_points`'s own `SATIN_MAX_WIDTH_MM / 2` per-station cap comment
    # above (root cause: this same OVERSIZE stroke -- its own apex genuinely,
    # smoothly widens to ~9.3mm, no junction or measurement artifact
    # involved -- was still casting full-width crosses there; capped now the
    # same way the zigzag skip above already treats this regime, at the same
    # ceiling). This shape's `coverage_max` before any of these fixes was
    # 13.11 -- now 3.24, see the updated regression pin below.
    oversize = field is not None and any(
        field.half_at(p) * 2.0 > machine.SATIN_MAX_WIDTH_MM for p in spine)
    if style == "zigzag" and not oversize:
        steps = max(2, int(math.ceil(length / machine.SATIN_ZIGZAG_PITCH_MM)))
        sp = _resample(spine, steps)
        ra, rb = _rail_points(poly, sp, st.closed, ribbon_width_mm(poly) / 2, field)
        pts: list[tuple[float, float]] = []
        for i, (pa0, pb0) in enumerate(zip(ra, rb)):
            # Narrow both ends from the ORIGINALS — pulling pb toward an
            # already-moved pa drifts the zigzag off the column's center.
            # 0.09 (corpus law 23): each leg spans 0.82x the RAIL SPAN
            # (1 - 2*0.09), not the old 0.4x (1 - 2*0.3) -- the prior
            # narrowing left satin's zigzag underlay too under-specified to
            # actually anchor the rails it sits beneath.
            #
            # Defense in depth alongside the oversize skip above: `sp` is a
            # coarser resample than the `spine` the skip check walks, and
            # `_rail_points`'s own smoothing can measure a rail span the
            # per-point field check didn't quite catch. Cap the leg the same
            # way, at what a column pinned to SATIN_MAX_WIDTH_MM would
            # produce (SATIN_MAX_WIDTH_MM * 0.82 =~ 4.1mm) -- below that
            # width nothing changes (frac is exactly the corpus's 0.09);
            # above it, frac rises smoothly so leg length asymptotes toward
            # the cap instead of continuing to grow with a corridor width
            # the corpus never measured.
            rail_span = math.dist(pa0, pb0)
            frac = 0.09
            if rail_span > machine.SATIN_MAX_WIDTH_MM:
                capped_leg = machine.SATIN_MAX_WIDTH_MM * 0.82
                frac = max(frac, 0.5 * (1.0 - capped_leg / rail_span))
            pa = (pa0[0] + (pb0[0] - pa0[0]) * frac, pa0[1] + (pb0[1] - pa0[1]) * frac)
            pb = (pb0[0] + (pa0[0] - pb0[0]) * frac, pb0[1] + (pa0[1] - pb0[1]) * frac)
            if math.dist(pa, pb) < machine.SATIN_MIN_CROSS_MM:
                continue
            pts.extend((pa, pb) if i % 2 == 0 else (pb, pa))
        if len(pts) >= 2:
            runs.append(StitchRun(points=pts, kind=stitches.UNDERLAY,
                                  shape_id=shape_id))
    return runs


def _build_travel_graph(strokes: list[Stroke]):
    """-> (nodes, edges, adjacency) over the strokes' spines.

    The skeleton the strokes came from is one connected web for a connected
    shape, and the professional trick the corpus files all use is to TRAVEL
    along that web with the needle down — the leg is covered when the stroke
    it follows sews its own column later. Endpoints within 0.5 mm share a
    node; a stroke whose end lands on another's interior (a T's stem on its
    bar) splits that spine so the junction is reachable.
    """
    endpoints = []
    for st in strokes:
        endpoints += [st.spine[0], st.spine[-1]]
    segs: list[tuple[int, list]] = []
    for k, st in enumerate(strokes):
        sp = st.spine
        cuts: set[int] = set()
        for p in endpoints:
            best_i, best_d = None, 0.5
            for i in range(1, len(sp) - 1):
                d = math.dist(p, sp[i])
                if d < best_d:
                    best_i, best_d = i, d
            if best_i is not None:
                cuts.add(best_i)
        idxs = [0, *sorted(cuts), len(sp) - 1]
        for a, b in zip(idxs, idxs[1:]):
            if b > a:
                segs.append((k, sp[a:b + 1]))

    nodes: list[tuple[float, float]] = []

    def node_at(p) -> int:
        for i, q in enumerate(nodes):
            if math.dist(p, q) <= 0.5:
                return i
        nodes.append(p)
        return len(nodes) - 1

    edges: list[dict] = []
    adj: dict[int, list[int]] = {}
    for k, poly in segs:
        if len(poly) < 2:
            continue
        a, b = node_at(poly[0]), node_at(poly[-1])
        ei = len(edges)
        edges.append({"a": a, "b": b, "k": k, "pts": poly,
                      "len": sum(math.dist(p, q) for p, q in zip(poly, poly[1:]))})
        adj.setdefault(a, []).append(ei)
        adj.setdefault(b, []).append(ei)
    return nodes, edges, adj


def _graph_travel(cur, target, sewn: set[int], allow: set[int],
                  nodes, edges, adj, *,
                  trim_at_mm: float) -> list[tuple[float, float]] | None:
    """Needle-down path from cur to target over UNSEWN spines, or None.

    Edges belonging to already-sewn strokes are forbidden: running stitches on
    top of finished satin show, which is the same reason the fill path prefers
    a trim over long travel across finished coverage.

    `trim_at_mm` is the caller's sew-vs-jump bound (the linking loop's), used
    only as the cursor-side snap retry radius below — the value itself is the
    caller's business. Note the design coupling this buys: a future
    cloth-driven retune of trim_at_mm also moves how far off the web a cursor
    may sit and still walk. Intended — both answer "how long a leg is sewable
    needle-down" — but it is one knob, not two.
    """
    def snap(p):
        best, bd = None, 0.8
        for i, q in enumerate(nodes):
            d = math.dist(p, q)
            if d < bd:
                best, bd = i, d
        return best

    s, t = snap(cur), snap(target)
    if s is None and nodes:
        # Cursor-side retry: the needle sits wherever the previous run ended —
        # often a cap-extended point a millimetre or two off the spine web —
        # and the strict 0.8mm snap killed the whole walk there, turning a
        # walkable move into a trim (real-art lane: only 112 of 1,178 travel
        # calls succeeded; median cursor miss 1.03mm, and 75.2% of cursors sit
        # within 3.0mm of a node). Snap to the
        # NEAREST node instead, within the same trim_at_mm the linking loop
        # uses to sew short hops needle-down: the returned path starts ON the
        # web, and the short leg from the true cursor onto it is exactly the
        # kind of hop that loop already covers. Target side stays strict — the
        # target is a stroke start the graph was built from, so a 0.8mm miss
        # there means the web genuinely does not reach it.
        ni = min(range(len(nodes)), key=lambda i: math.dist(cur, nodes[i]))
        if math.dist(cur, nodes[ni]) <= trim_at_mm:
            s = ni
    if s is None or t is None:
        return None
    if s == t:
        return []
    dist = {s: 0.0}
    prev: dict[int, tuple[int, int]] = {}
    pq = [(0.0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t:
            break
        if d > dist.get(u, 1e18):
            continue
        for ei in adj.get(u, []):
            e = edges[ei]
            if e["k"] in sewn and e["k"] not in allow:
                continue
            v = e["b"] if e["a"] == u else e["a"]
            nd = d + e["len"]
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = (u, ei)
                heapq.heappush(pq, (nd, v))
    if t not in prev:
        return None
    chain: list[list] = []
    u = t
    while u != s:
        pu, ei = prev[u]
        e = edges[ei]
        pts = list(e["pts"]) if e["a"] == pu else list(reversed(e["pts"]))
        chain.append(pts)
        u = pu
    chain.reverse()
    out: list[tuple[float, float]] = []
    for pts in chain:
        out.extend(pts if not out else pts[1:])
    return out


def _choose_stroke_entry(cur: tuple[float, float],
                         a: tuple[float, float], free_a: bool,
                         b: tuple[float, float], free_b: bool) -> bool:
    """True if a stroke between ends `a` and `b` should be entered at `b`
    (needle currently at `cur`), false if it should be entered at `a`.

    Laws 27/29 (`machine.STRUCTURAL_ENTRY_BUDGET_MM`): pros enter at a
    stroke's free end (its open cap) far more often than at whichever end is
    merely nearest, and will pay up to that budget of extra travel to reach
    it. `free_a == free_b` means neither end is structurally preferred over
    the other (both free, or both welded into a junction) — nothing to lean
    on, so proximity is the whole rule there, same as before this law.
    """
    d_a = math.dist(cur, a)
    d_b = math.dist(cur, b)
    if free_a == free_b:
        return d_b < d_a
    cap_is_b = free_b
    cap_d, other_d = (d_b, d_a) if cap_is_b else (d_a, d_b)
    if cap_d - other_d <= machine.STRUCTURAL_ENTRY_BUDGET_MM:
        return cap_is_b
    return d_b < d_a


def _order_strokes(strokes: list[Stroke],
                   start_near: tuple[float, float] | None) -> list[Stroke]:
    """Sew order within one shape: whichever stroke's preferred entry (Laws
    27-29, `_choose_stroke_entry`) is closest to where the needle already is,
    then on by the same rule.

    `extract_strokes` sorts longest-first, which keeps a letter's main stem
    ahead of its serifs but says nothing about the hops between them. Sewing
    in that order alone means the needle can be sent back across a whole
    glyph — and between shapes it meant every letter started at its own
    longest stroke however far that was from the last stitch of the letter
    before it. With nothing sewn yet the longest stroke still goes first.
    """
    remaining = list(range(len(strokes)))
    out: list[Stroke] = []
    cur = start_near
    while remaining:
        if cur is None:
            pick = remaining[0]
        else:
            pick = min(remaining, key=lambda i: (
                round(min(math.dist(cur, strokes[i].spine[0]),
                          math.dist(cur, strokes[i].spine[-1])), 6), i))
        st = strokes[pick]
        remaining.remove(pick)
        out.append(st)
        # It comes out of the end it did not go in at.
        a, b = st.spine[0], st.spine[-1]
        if cur is None:
            cur = b
        else:
            cur = a if _choose_stroke_entry(cur, a, st.free_start, b, st.free_end) else b
    return out


def satin_shape(poly: Polygon, shape_id: str, *, underlay_style: str,
                trim_at_mm: float,
                start_near: tuple[float, float] | None = None,
                split_above_mm: float | None = None,
                end_cutback_mm: float = 0.0,
                use_shapefield: bool = False,
                spacing_mm: float = machine.SATIN_SPACING_MM,
                angle_deg: float | None = None,
                ) -> tuple[list[StitchRun], dict]:
    """One satin-classified shape -> runs in sew order, plus the same report
    contract `stitch_shape` uses, so stage 7 can treat the two identically.

    `start_near` is where the needle is when this shape's turn comes.
    `split_above_mm` caps the stitch length before crosses split (None =
    machine.SPLIT_SATIN_ABOVE_MM; `math.inf` disables splitting — the
    mapping stage 7 applies for `PipelineConfig.split_satin = False`).

    `spacing_mm` (task A2) is the along-column cross spacing every stroke in
    this shape targets, forwarded to `satin_stroke` unchanged — default
    `machine.SATIN_SPACING_MM`, so a caller that never mentions it keeps
    today's output exactly. Stage 7 passes the fabric preset's
    `density_adjust`-scaled number, the same multiplier `row_mm` already
    gets for fill (`fabrics.py`'s own "mirror src/fabrics.js exactly" table
    — the browser engine already applies `densityAdjust` to its own satin
    spacing this way; this closes the one place the Python engine had not).

    `end_cutback_mm` is push compensation at open column ends (Law 24); 0.0 is
    the shipped behaviour. It is a length taken off the spine, NOT a shrink of
    `poly`, which is why it cannot live in stage 5 — see `satin_stroke`.

    `use_shapefield` forwards to `extract_strokes` — see its docstring. Off
    by default; stage 7 sets it from `cfg.extra["shapefield"]`.
    """
    report = {"too_thin": False, "jumps": 0, "empty": False}
    strokes, half_mm, field = extract_strokes(poly, use_shapefield=use_shapefield)
    if not strokes:
        report["empty"] = True
        return [], report
    strokes = _order_strokes(strokes, start_near)

    # Per stroke: its underlay, then its column, then move on. Sewing ALL the
    # underlay first meant hopping back across the whole letter to start the
    # first column — on the drone logo that pattern alone put 100+ extra trims
    # in the file, and a trim is 2-3 seconds of machine time each.
    #
    # Each run is also ORIENTED to start at whichever of its ends is nearer to
    # where the needle already is. The center run walks the spine one way and
    # the column would otherwise start back where the underlay began — a full
    # stroke-length hop between them, once per stroke. Reversing an
    # alternating zigzag keeps it an alternating zigzag, so orientation is
    # free to choose.
    kept: list[tuple[Stroke, list]] = []
    for st in strokes:
        pts = satin_stroke(poly, st, half_mm, field, split_above_mm,
                           end_cutback_mm, spacing_mm, angle_deg)
        if len(pts) >= 4:
            kept.append((st, pts))
    if not kept:
        report["empty"] = True
        return [], report

    # The travel graph spans only strokes that will actually sew — a leg over
    # a stub the emitter skipped would never be covered by anything.
    nodes, g_edges, g_adj = _build_travel_graph([st for st, _ in kept])
    sewn: set[int] = set()

    runs: list[StitchRun] = []
    for ki, (st, pts) in enumerate(kept):
        # Wide columns carry zigzag underlay or their crosses float — every
        # wide-satin file in the corpus shows the support passes.
        if field is not None and st.spine:
            step = max(1, len(st.spine) // 8)
            halves = [field.half_at(p) for p in st.spine[::step]]
            stroke_w = 2.0 * (sum(halves) / len(halves)) if halves else 2.0 * half_mm
        else:
            stroke_w = 2.0 * half_mm
        eff_style = "zigzag" if (underlay_style != "none"
                                 and stroke_w > machine.SATIN_ZIGZAG_ABOVE_MM) \
            else underlay_style

        stroke_runs = [*_stroke_underlay(poly, st, eff_style, shape_id, field),
                       StitchRun(points=pts, kind=stitches.SATIN, shape_id=shape_id)]
        first_of_stroke = True
        for run in stroke_runs:
            cursor = runs[-1].points[-1] if runs else start_near
            if cursor is not None:
                # Laws 27-29 (STRUCTURAL_ENTRY_BUDGET_MM): the visible satin
                # column is what the corpus measured entering at a free cap
                # over the nearer end, so it alone gets that preference.
                # Underlay stays pure-nearest — hidden support stitching, not
                # what the law's professional decisions were read off of, and
                # its orientation is already tuned to avoid extra hops
                # between strokes (see the loop's own note below).
                if run.kind == stitches.SATIN:
                    if _choose_stroke_entry(cursor, run.points[0], st.free_start,
                                            run.points[-1], st.free_end):
                        run.points.reverse()
                elif math.dist(cursor, run.points[-1]) < math.dist(cursor, run.points[0]):
                    run.points.reverse()
            if first_of_stroke and cursor is not None:
                # Between strokes, walk the unsewn web instead of lifting.
                direct = math.dist(cursor, run.points[0])
                if direct >= machine.TINY_STITCH_MM:
                    path = _graph_travel(cursor, run.points[0], sewn, {ki},
                                         nodes, g_edges, g_adj,
                                         trim_at_mm=trim_at_mm)
                    if path is not None and len(path) >= 2:
                        plen = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
                        # Same cap as the fill path: past this, travel under
                        # future coverage reads worse than the trim it saves.
                        if plen <= max(20.0, 4.0 * direct):
                            n = max(2, int(math.ceil(plen / machine.TRAVEL_STITCH_MM)) + 1)
                            runs.append(StitchRun(points=_resample(path, n),
                                                  kind=stitches.TRAVEL,
                                                  shape_id=shape_id))
            first_of_stroke = False
            runs.append(run)
        sewn.add(ki)

    if not any(r.kind == stitches.SATIN for r in runs):
        report["empty"] = True
        return [], report

    # Link EVERY consecutive run pair, underlay included. A short hop whose
    # stitch would stay INSIDE the shape is sewn as a stitch, not jumped —
    # this is where the corpus's 180-880-stitch runs come from: a column's
    # cap-extended start sits a millimetre past the underlay walk that led to
    # it, and lifting there fragmented every stroke into ~25-stitch runs
    # (measured: ~50 short jumps on the benchmark logo). A hop is only a jump
    # when it is long, or when the straight line between the runs would cross
    # outside the artwork (a counter's hole, the gap between two strokes) —
    # thread over bare fabric is a float no matter how short.
    poly_link = poly.buffer(0.1)
    for prev, cur in zip(runs, runs[1:]):
        a, b = prev.points[-1], cur.points[0]
        d = math.dist(a, b)
        if d < machine.TINY_STITCH_MM:
            continue
        if d <= trim_at_mm and poly_link.covers(LineString([a, b])):
            continue        # needle-down: encoder sews end -> start as one stitch
        cur.jump = True
        cur.trim = d > trim_at_mm
        report["jumps"] += 1
    return runs, report

