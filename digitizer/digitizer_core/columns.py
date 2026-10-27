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

What this carries (each rule is the font engine's, `src/satinfont.js`
`routeGlyph`, ported):

- pull compensation on the RAILS, per side, by the fabric's own
  `pull_comp_mm`, held back across a counter (`stage6_satin._push_rails`,
  the same function the shipped satin tier uses, on the same artwork
  polygon), from rails set `RAIL_REACH_INSET_MM` inside the outline so the
  lane reaches where that tier's rails reach (Kent's ruling 2026-10-11);
- the cross floor (`machine.SATIN_MIN_CROSS_MM`): a cross the needle cannot
  resolve is dropped and counted, never sewn as a smear;
- split satin above `split_above_mm` with the column-wide comb
  (`_comb_thresholds`, `_split_points`: Kent's 2026-09-30 "smooth and flow"
  rule), so a wide stem is a split column, never a fill;
- **the Euler walk** (Kent's pick 2026-10-07, second step of the lane): a
  letter's columns are the edges of a span graph -- column ends merged
  into nodes, a column end that lands mid-stroke on another column cutting
  that column into spans -- made Eulerian per component by duplicating a
  minimal set of spans along shortest paths between odd nodes
  (Chinese-postman, greedy), walked by Hierholzer's trail; a span sews
  SATIN on its last visit and a running UNDERPATH on every earlier one, so
  every travel lies under a column sewn later and the needle never leaves
  the letter inside one component. Before this the order was nearest-next
  and every hop that left the letter was a jump (enthusiast 13 -> 22
  trims, Fremont 17 -> 38 on the first wiring);
- a centre-walk underlay laid immediately before each satin span, out and
  back so the needle is where the satin starts, where the letter is large
  enough for underlay at all (the caller passes "none" under
  `machine.SATIN_UNDERLAY_MIN_EXTENT_MM`, as it does for the satin tier);
- the shipped sew-or-jump rule between runs (a short hop inside the letter
  is a stitch, a long one or one over bare fabric a jump, a jump past
  `trim_at_mm` a trim).

- **the junction tuck** (Kent's pick 2026-10-07, fourth step): a column
  that butts another mid-stroke -- the M's diagonal on its stem, the T's
  stem on its bar -- and sews BEFORE it is extended under it by the satin
  tier's own `_JUNCTION_TUCK_MM` plus the pull, capped at half a stroke,
  so the stroke sewn later covers the seam instead of meeting it at a line
  of needle holes. A butting column that sews AFTER the one it butts stays
  square: an overlap on top is a lump, not a tuck.

- **the buried hop** (2026-10-08): a hop between runs that the link rule
  would cut is sewn when it can run inside the letter with no more of it
  left on top than a hop that rule already sews; the rest lies on ground a
  later satin leg covers.

NOT yet: tie stitches, an edge-walk underlay for tall caps. Every one of those is a Column consumer and goes here.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, substring, unary_union

from . import machine, stitches
from .letter_walk import SLOT_GUARD_GROW_MM
from .stitches import StitchRun

# A column end within this many stroke widths (plus a constant for the pull)
# of another column's centreline sits ON that column: the two meet there.
# routeGlyph's `mergeR = max(2, 1.3 * medW)`; at 0.75 Becker's M left its
# stem as a component of its own (the mitred diagonal starts a width away).
_MERGE_WIDTHS = 1.3
_MERGE_PAD_MM = 0.3
# A hop between two legs that stays INSIDE the letter is sewn as a connector
# up to this many stroke widths long, whatever `trim_at_mm` says: the font
# engine's walk is continuous along the glyph and the pro's Becker file cuts
# 12 times for the whole design. Past it the sew-or-jump rule decides.
_CONNECTOR_WIDTHS = 2.0
# A junction closer than this fraction of a column's length to one of its
# ends IS that end, not a mid-stroke cut (routeGlyph: 0.06 / 0.94).
_END_FRAC = 0.06
# The tuck never reaches past the middle of the stroke it goes under: the
# other side of that stroke is bare fabric or the next junction.
_TUCK_MAX_WIDTHS = 0.5
# The running underpath under a later column: the font engine's 2 mm step.
_UNDERPATH_STEP_MM = 2.0
# Centre-walk underlay: step and end inset (satinfont.js UNDERLAY_*).
_UNDERLAY_STEP_MM = 3.0
_UNDERLAY_INSET_MM = 0.4
# The walk-in lands this far inside the letter's near edge (or a quarter
# stroke, if less): inside the satin that will cover it, clear of the edge.
_ENTRY_INSET_MM = 0.3
# `apex_cut` (`cfg.lettering_columns_apex_cut`): a column end whose middle
# lies within a pitch plus this many stroke widths of a merged tip's cross
# meets the tip there (the last station of a cut piece sits up to a pitch
# short of its cut: 0.0-0.42 mm on MFab's W, 0.14-0.2 at the tips' own ends)
_APEX_END_WIDTHS = 0.25
# ... and a tip column is one whose far cross has closed to this share of
# the cross at its cut (the tips: 0.03-0.17; MARINE's slab-side wedge, built
# on the same cross, does not close)
_APEX_CLOSED = 0.5
# ... and the needle leaving a tip's last cross steps this far past its cut
# before it turns: half the 0.4 mm laid thread, off the tip's own edge
_APEX_EXIT_MM = 0.2
# Each rail starts this far INSIDE the outline, along its own cross, before
# the pull pushes it out (or a quarter of the cross, if less) -- so the lane
# reaches as far past the edge as the shipped satin tier does, under the same
# `pull_comp_mm` (Kent's ruling 2026-10-11). Not a fabric constant and not a
# new reach: the satin tier has no inset constant of its own; its rails are a
# smoothed SYMMETRIC offset at the nearer edge's half-width
# (`stage6_satin._rail_points`), which stops short of the outline, and only
# then `_push_rails` adds the pull. The lane cut its rails ON the outline and
# so stood that undershoot further out. Measured on #828's letters: median
# satin penetration -0.157 / -0.173 / -0.109 mm shipped against -0.274 /
# -0.265 / -0.231 lane (enthusiast / drone / bridge, negative outside), gaps
# 0.117 / 0.092 / 0.122; this is their mean. Pre-push, the shipped rails sit
# a mean +0.11-0.12 mm inside (median +0.04-0.06), the lane's +0.03-0.05.
RAIL_REACH_INSET_MM = 0.11
# `cfg.lettering_columns_small_bold` (2026-10-21, built OFF): a letter under
# `machine.SATIN_UNDERLAY_MIN_EXTENT_MM` (stage 7's `_small`) sews like the
# pro's ~4 mm bold letters. Its pull is a share of its stroke width, not the
# fabric's fixed `pull_comp_mm`: 0.4 mm a rail on Hat sewed the grown Fremont
# tagline's 0.8 mm strokes 1.23 mm wide (median satin stitch) against the
# pro's 0.86, and the letters ran together. Industry pull is a fraction of
# the column; this share puts the median back at the pro's. A candidate
# until sewn (gate 1).
SMALL_BOLD_PULL_FRAC = 0.15
# `small_bold`: a letter whose satin covers less of it than this (crosses
# widened by half the 40 wt laid thread) is cut again at the plain
# `outline_cut.SIMPLIFY_MM` and the better-covered of the two is sewn. The
# 0.06 mm floor that keeps a condensed grown serif square cut the diagonal
# legs off the bold re-set A's of Fremont's tagline
# (`cfg.small_text_cap_letter_gap_mm`): 0.68-0.72 of each A sewn, 0.85-0.95
# at 0.12. Every letter of #1025's condensed fixture covers 0.96 or more, so
# none of them is cut twice. Still under it at 0.12, the letter is cut once
# more with the lane's own construction (small_bold's pull kept) and that is
# sewn when it covers at least `SMALL_BOLD_PLAIN_GAIN` more: the re-set A's
# left leg went unsewn under small_bold's straight rescan at either floor
# (0.83 / 0.85 / 0.95 -> 0.95 / 0.95 / 0.97), at the price of an apex
# zigzag across its 0.3 mm counter.
SMALL_BOLD_COVER_MIN = 0.9
SMALL_BOLD_PLAIN_GAIN = 0.05
# `cfg.pull_comp_by_stroke` (2026-10-22, built OFF): each column's pull is
# read off its OWN drawn stroke width, by the rule the professional's hat
# files sew. Measured 2026-10-22 over the pro's files in `Embroidery
# Files.zip` -- sewn satin cross (needle to needle, median per letter)
# against the art's stroke (2 x EDT on the letter's skeleton, the art
# scaled to the pro's design width), letters the pro kept at the art's size
# only, per-job medians:
#     drawn 0.85 -> sewn 1.43 (+0.58)  Fremont HOTEL FREMONT, hat and patch
#     drawn 1.29 -> sewn 1.80 (+0.59)  Drone THERMAL
#     drawn 2.61 -> sewn 3.02 (+0.42)  Proseal PROSEAL
#     drawn 4.22 -> sewn 4.00 (-0.22)  Becker MARINE (art 0.53 mm/px: +/-0.6)
# A fixed pull adds the same on every width; the pro's addition FALLS with
# the width, and at 4 mm he adds nothing (his LC and beanie Becker files
# agree: -0.45 / -0.40). The line through those four job medians:
#     sewn = PULL_BY_STROKE_A * drawn + PULL_BY_STROKE_B
# so the pull a rail gets (`pull_for_width`) is half the addition plus the
# `RAIL_REACH_INSET_MM` each rail starts inside the outline, read on the
# hat preset's 0.4 mm and scaled to another preset by its own pull, never
# above the preset's own pull and never below zero. At 0.85 mm it is the
# hat's 0.4 (the pro sews HOTEL FREMONT at exactly our width); at 2.6 mm
# 0.23; at 4 mm 0.07. The thin-stroke floor the pro's RAISED small text
# sews (0.9-1.26 mm columns) is not in this fit: he redraws those letters,
# and `SMALL_BOLD_PULL_FRAC` is the lane's rule for them. Pull is a
# physical constant (ROADMAP gate 1): Kent flips after a sew-out.
PULL_BY_STROKE_A = 0.77
PULL_BY_STROKE_B = 0.835
PULL_BY_STROKE_FABRIC_MM = 0.4          # the preset the fit was read on


def pull_for_width(width_mm: float, fabric_pull_mm: float) -> float:
    """The pull one rail gets on a column `width_mm` wide, under
    `cfg.pull_comp_by_stroke`, on a preset whose fixed pull is
    `fabric_pull_mm` (module constants above)."""
    add = (PULL_BY_STROKE_A - 1.0) * width_mm + PULL_BY_STROKE_B
    pull = (add / 2.0 + RAIL_REACH_INSET_MM) * fabric_pull_mm / PULL_BY_STROKE_FABRIC_MM
    return min(max(0.0, pull), max(0.0, fabric_pull_mm))


def column_width(col: "Column") -> float:
    """A column's own drawn stroke width: the median of its station
    crosses (rail to rail, on the outline, before any inset or pull)."""
    ws = sorted(math.dist(a, b) for a, b in col.stations)
    return ws[len(ws) // 2] if ws else 0.0


@dataclass
class Column:
    """One satin column of a letter: rail-to-rail crosses in sew order."""

    stations: list[tuple[tuple[float, float], tuple[float, float]]]
    piece: Polygon                      # the stroke piece these crosses cover
    kind: str                           # "straight" | "curved" | "ring" | "folded" (corner_fold: legs + a fold)
    axis: tuple[float, float] | None    # unit axis of a straight piece
    width_mm: float                     # the letter's mean stroke width
    rail_a: list[tuple[float, float]] = field(default_factory=list)
    rail_b: list[tuple[float, float]] = field(default_factory=list)
    dropped_mm: float = 0.0             # scanline length a straight scan left unstationed

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
                      rail_a=self.rail_a[::-1], rail_b=self.rail_b[::-1], dropped_mm=self.dropped_mm)


def is_lettering(region, cfg=None) -> bool:
    """Does the lane take this shape? Under `cfg.lettering_words` the one
    tagger's word (`words.tag_words`, `word_id`, L1). Off, either old
    tagger: the text cluster (`textcluster.tag`, `text_candidate`) or the
    house-angle group (`set_lettering_house_angle`, `lettering_group`),
    which disagree on real logos (`tools/word_tagger_eval.py`)."""
    m = region.meta or {}
    if getattr(cfg, "sew_enclosed_white_fields_fill", False) and m.get("sew_enclosed_white"):
        return False        # a white field the option sews is never a letter
    if getattr(cfg, "lettering_words", False):
        tagged = bool(m.get("word_id"))
    else:
        tagged = bool(m.get("text_candidate") or m.get("lettering_group"))
    if tagged and getattr(cfg, "lettering_columns_skip_blobs", False) \
            and is_solid_blob(region.polygon):
        return False
    if tagged and getattr(cfg, "lettering_columns_ink_link", False) \
            and m.get("lettering_ink_stray"):
        return False
    if tagged and getattr(cfg, "lettering_columns_icon_guard", False) \
            and m.get("lettering_group") and not m.get("text_candidate") \
            and is_drawing_fragment(region.polygon):
        return False
    return tagged


# `cfg.lettering_columns_ink_link`: the text cluster links two letters only
# when their chart threads sit within `textcluster.TEXT_CLUSTER_DELTA_E_MAX`
# (CIEDE2000 20); the house-angle group has no such link, so a glyph-sized
# shape in another colour beside a wordmark joins its line. `ink_strays`
# refuses a HOUSE-GROUP-ONLY shape (`lettering_group`, not `text_candidate`)
# whose thread is further than that from EVERY text-cluster letter's thread,
# unless it ABUTS a text-cluster letter. Census at the corpus settings
# (`tools/column_capture_census.py --corpus --guard
# lettering_columns_ink_link`, 2026-10-13): the one house-only
# shape past 20 on the seven labelled-or-rendered fixtures is enthusiast's
# shield star (34.2 from the wordmark's 0134); every other house-only shape
# reads <= 12.2, golden_tee's three swashes 0.0 (their inks 0811/1102/0020
# are inks of its text letters too).
#
# ABUTS: within `INK_LINK_TOUCH_MM` of a text-cluster letter, polygon to
# polygon. 1.0 mm is the widest gap between two letters of one measured word
# (enthusiast's subline, 0.88-1.0; its wordmark 0.18-0.48, fremont's
# 0.15-0.47), so a part as close to a letter as the word's own letters are
# to each other counts as part of the word. golden_tee's swashes that touch
# the GT letters sit at 0.0 and 0.0 (the third, the black arc, at 2.81, and
# passes on ink); the star sits 6.28 mm from the nearest letter. A CANDIDATE
# shape ratio from one corpus, not a cloth constant.
INK_LINK_TOUCH_MM = 1.0


def ink_strays(regions, chart, *, max_delta_e: float | None = None,
               touch_mm: float = INK_LINK_TOUCH_MM) -> list[str]:
    """Shape ids of house-group-only shapes the ink link refuses (see
    `INK_LINK_TOUCH_MM`). No text-cluster letter in the design means no text
    ink to compare with: nothing is refused (fails open, like
    `textcluster._same_ink`). A thread the chart cannot place is no colour
    evidence either, and is kept."""
    if max_delta_e is None:
        from .textcluster import TEXT_CLUSTER_DELTA_E_MAX
        max_delta_e = TEXT_CLUSTER_DELTA_E_MAX
    text = [r for r in regions if (r.meta or {}).get("text_candidate")]
    if not text:
        return []
    inks = sorted({r.thread_index for r in text})
    out: list[str] = []
    for r in regions:
        m = r.meta or {}
        if not m.get("lettering_group") or m.get("text_candidate"):
            continue
        if r.thread_index in inks:
            continue
        try:
            near = min(float(chart.delta_e(r.thread_index, i)) for i in inks)
        except (IndexError, TypeError, ValueError):
            continue
        if near <= max_delta_e:
            continue
        if any(r.polygon.distance(t.polygon) <= touch_mm for t in text):
            continue
        out.append(r.shape_id)
    return out


def tag_ink_strays(regions, chart) -> int:
    """Write `meta["lettering_ink_stray"] = True` on every `ink_strays`
    shape; returns how many. Called only under
    `cfg.lettering_columns_ink_link`, so OFF no key is written."""
    ids = set(ink_strays(regions, chart))
    for r in regions:
        if r.shape_id in ids:
            r.meta["lettering_ink_stray"] = True
    return len(ids)


# `cfg.lettering_columns_skip_blobs`: a tagged shape that is a solid blob, not
# a stroke, is not a letter. Both old taggers ask only for glyph-sized,
# glyph-aspect, alike shapes; `tools/column_capture_census.py` found the
# house-angle group (no ink link) admitting twelve colour patches
# (`test_preflight`'s grid) and eight 14.4 mm ramp discs (`photo/
# fur_ramp.png`), which the lane then sewed as 20 mm split satin. The two
# numbers are read off the polygon: mean stroke width (2 x area / perimeter)
# over the longer bbox side, and solidity (area / convex hull). Census, real
# art at the labelled settings: every labelled letter reads <= 0.31 on the
# first (Becker's bold caps, the maximum) and no solid one reaches 0.4; the
# patches and discs read 0.49-0.50 at solidity 0.99. CANDIDATES, not cloth
# constants: they are shape ratios, set from one corpus.
BLOB_STROKE_OVER_H = 0.40
BLOB_MIN_SOLIDITY = 0.95


def is_solid_blob(poly) -> bool:
    x0, y0, x1, y1 = poly.bounds
    side = max(x1 - x0, y1 - y0)
    if side <= 0 or poly.length <= 0:
        return False
    stroke = 2.0 * poly.area / poly.length
    hull = poly.convex_hull.area
    return (stroke / side >= BLOB_STROKE_OVER_H
            and hull > 0 and poly.area / hull >= BLOB_MIN_SOLIDITY)


# `cfg.lettering_columns_small_stem`: a thin STEM under the area floor.
# Stage 7 sends every auto-tier shape under `min_detail_mm`^2 (1.5 mm ->
# 2.25 mm^2) to the run tier before the Column lane is asked
# (`stage7_sequence.routes_to_run`, the small-shape rescue). The floor is an
# AREA, so a stroke clears it by length as much as by width: the synthetic
# word's capital I (0.57 x 4.87 mm at 80 mm, 2.771 mm^2) sews satin, and its
# lowercase i stem at the SAME width (0.57 x 3.73 mm, 2.124 mm^2) sews a
# two-line run (`tools/stem_trace.py`, 2026-10-13). A stem is a shape that
#   - is at least the floor's own width long (`min_detail_mm`),
#   - is at least `machine.SATIN_MIN_CROSS_MM` (0.5) across -- narrower, the
#     lane's own cross floor makes it a hairline anyway -- and
#   - is at least `STEM_MIN_ASPECT` times as long as it is wide.
# The i stem reads 3.73 x 0.57 mm, aspect 6.5; a dot or a blob reads 1.0-1.3.
# The aspect bar is set by the corpus, not by the stem: the phone-UI
# screenshot has seven lettering shapes under the floor that are stems by
# length alone (`tools/stem_trace.py --census`), three of them 0.31-0.39 mm
# across (held out by the cross floor) and three 0.63-0.90 mm across at
# aspect 3.1-4.1, which stay run. CANDIDATES, shape ratios from one
# synthetic face and one UI screenshot, not cloth constants (ROADMAP gate 1).
STEM_MIN_ASPECT = 6.0


def is_thin_stem(poly, min_long_mm: float,
                 min_short_mm: float = machine.SATIN_MIN_CROSS_MM) -> bool:
    """A sub-floor shape that is a stroke, not a dot (see `STEM_MIN_ASPECT`)."""
    if not isinstance(poly, Polygon) or poly.is_empty:
        return False
    rect = poly.minimum_rotated_rectangle
    if not isinstance(rect, Polygon):
        return False
    pts = list(rect.exterior.coords)
    a = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
    b = math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
    long_side, short_side = max(a, b), min(a, b)
    return short_side >= min_short_mm and long_side >= min_long_mm \
        and long_side / short_side >= STEM_MIN_ASPECT


# `cfg.fine_bars_satin` (built OFF 2026-10-25): a free-standing thin INK bar
# under the area floor. The pro satins every such bar, at its drawn width
# plus his ordinary pull, in 5 of 5 artworks that have them (To a T's speed
# rules, the Precision Drone's AND DRONE rule, Hotel Fremont's separators,
# Gaulke, Golden Tee: the small-symbols census, 2026-10-25), where the area
# floor sends ours to a hollow bean ring 0.3-0.7 mm wide. In ours' polygons
# the targets read aspect 4.8-24.7 (one 1.52 mm stub at 5.3, short side
# 0.29) against Fremont's rope strands at 3.8 or less and Golden Tee's teal
# keyline at 4.69, so a bar is a STEM by `STEM_MIN_ASPECT` -- or, the thin
# margin, anything under a satin cross across (targets 0.38 mm or less,
# rope 0.59 and up) -- at least two crosses long. An aspect of 2.5 admitted
# 116 rope strands and the teal fragment (region kappa 0.29); this reached
# 0.93 over 38 target regions in-sample. No constant of its own.
def is_fine_bar(region, poly, sewn_neighbours, cfg) -> bool:
    """A sub-floor shape the pro sews as ONE satin bar (see above).

    All of:
      * not lettering (`is_lettering`) -- the Column lane's population;
      * one Polygon, no hole;
      * at least 2 x `machine.SATIN_MIN_CROSS_MM` long, and a stem
        (`is_thin_stem`, aspect `STEM_MIN_ASPECT`) or under one cross across;
      * INK: its thread not within `cfg.enclosed_by_garment_de00` of the
        garment (`cfg.garment_rgb`, when known), nor the thread of any sewn
        `enclosed_background` region in `sewn_neighbours`;
      * not a highlight: not lighter (CIE L*) than EVERY sewn region it
        touches, where "touches" is within 0.25 mm. A bar that touches no
        sewn region qualifies (21 of the 38 targets touch nothing).

    `sewn_neighbours`: the design's other sewn Regions, any order; the ones
    that touch are found here."""
    from .threads import chart_for
    if is_lettering(region, cfg):
        return False
    if not isinstance(poly, Polygon) or poly.is_empty or poly.interiors:
        return False
    long_min = 2.0 * machine.SATIN_MIN_CROSS_MM
    rect = poly.minimum_rotated_rectangle
    if not isinstance(rect, Polygon):
        return False
    pts = list(rect.exterior.coords)
    short_side, long_side = sorted((math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])))
    if long_side < long_min:
        return False
    if not (short_side < machine.SATIN_MIN_CROSS_MM
            or is_thin_stem(poly, long_min, min_short_mm=0.0)):
        return False
    chart = chart_for(cfg)
    lab = _lab_of(chart[region.thread_index].rgb)
    if cfg.garment_rgb is not None and \
            _de00(lab, _lab_of(tuple(cfg.garment_rgb)[:3])) <= cfg.enclosed_by_garment_de00:
        return False
    others = [n for n in sewn_neighbours if n.shape_id != region.shape_id]
    if any(n.meta.get("enclosed_background") and n.thread_index == region.thread_index
           for n in others):
        return False
    near = poly.buffer(0.25)
    touching = [n for n in others if near.intersects(n.polygon)]
    if touching and all(lab[0] > _lab_of(chart[n.thread_index].rgb)[0] for n in touching):
        return False                # a highlight on everything it touches
    return True


def _lab_of(rgb) -> tuple[float, float, float]:
    import numpy as np
    from skimage.color import rgb2lab
    v = rgb2lab(np.array([[rgb]], dtype=float) / 255.0)[0, 0]
    return float(v[0]), float(v[1]), float(v[2])


def _de00(a, b) -> float:
    import numpy as np
    from skimage.color import deltaE_ciede2000
    return float(deltaE_ciede2000(np.array(a), np.array(b)))


# `cfg.lettering_columns_icon_guard`: a house-group-only shape whose medial
# axis is a TANGLE is a piece of drawing, not a letter. Neither guard above
# reaches the phone screenshot's three 4.5-6 mm captures (S4a2d12c4,
# Sf90dec39, S84f354eb: thin-stroked pieces of the truck drawing, not solid
# blobs, and in the text's own grey). What they have that no letter has is a
# skeleton with many nodes: `skeleton_nodes` counts junctions plus free ends
# of the shape's own medial axis (`shapefield.build_shape_field`, whose grid
# is set by the stroke width, so the count does not move with size), after
# spurs shorter than one stroke width are pruned away (edge noise, not
# strokes). Census at the corpus settings (`tools/column_capture_census.py
# --signals`, 2026-10-13, both other guards ON): the three captures read 36,
# 39 and 45; the 130 hand-labelled letters of eight fixtures read at most 13
# (Fremont's slab-serif H and M: every serif is a junction and two ends);
# golden_tee's three house-only swashes read 4, 4 and 8. 24 sits between.
# Judged on HOUSE-GROUP-ONLY shapes, as the ink link is: the text cluster
# has its own ink link and letter door. A CANDIDATE shape count from one
# corpus, not a cloth constant.
ICON_GUARD_MIN_NODES = 24


def skeleton_nodes(poly) -> int:
    """Junctions plus free ends of `poly`'s pruned medial axis (see
    `ICON_GUARD_MIN_NODES`). 0 for anything the shape field cannot raster:
    no evidence, so the guard fails open."""
    if not isinstance(poly, Polygon) or poly.is_empty:
        return 0
    return _skeleton_nodes(poly)


@lru_cache(maxsize=1024)
def _skeleton_nodes(poly: Polygon) -> int:
    import cv2
    import numpy as np
    from .shapefield import build_shape_field

    f = build_shape_field(poly)
    if f is None or not f.skel.any():
        return 0
    sk = f.skel.astype(np.uint8)
    kernel = np.ones((3, 3), np.float32)

    def neighbours():
        n = cv2.filter2D(sk, -1, kernel, borderType=cv2.BORDER_CONSTANT)
        return (n.astype(np.int32) - 1) * sk

    # Peel free ends one pixel at a time for one stroke width: a spur that
    # short is gone, a real stroke is only shortened.
    for _ in range(int(round(2.0 * float(np.median(f.dist[f.skel]))))):
        ends = (sk > 0) & (neighbours() <= 1)
        if not ends.any():
            break
        sk[ends] = 0
    nb = neighbours()
    ends = int(((sk > 0) & (nb == 1)).sum())
    n_junctions, _ = cv2.connectedComponents(((sk > 0) & (nb >= 3)).astype(np.uint8),
                                             connectivity=8)
    return ends + n_junctions - 1


def is_drawing_fragment(poly) -> bool:
    return skeleton_nodes(poly) >= ICON_GUARD_MIN_NODES


# ----------------------------------------------------------------- geometry

def _walk_corners(path, step_mm: float) -> list[tuple[float, float]]:
    """`path` resampled every `step_mm` on each of its legs, every corner
    kept (`_walk_points` keeps only the two ends)."""
    out: list[tuple[float, float]] = [tuple(path[0])]
    for p, q in zip(path, path[1:]):
        if math.dist(p, q) > 1e-9:
            out.extend(_walk_points([p, q], step_mm)[1:])
    return out if len(out) >= 2 else [tuple(path[0]), tuple(path[-1])]


def _mids(stations):
    return [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in stations]


def _walk_points(path, step_mm: float) -> list[tuple[float, float]]:
    """`path` resampled every `step_mm` of arc length, both ends kept."""
    ln = LineString(path)
    if ln.length < 1e-9:
        return [tuple(path[0]), tuple(path[-1])]
    n = max(1, int(math.ceil(ln.length / step_mm)))
    return [ln.interpolate(ln.length * k / n).coords[0] for k in range(n + 1)]


def _satin_points(stations, split_above_mm: float, comb_thresholds, split_points):
    """Stations in traversal order -> the zigzag's penetrations, split comb on.
    BOTH ends of every station, the engine's flat zigzag (`satin_stroke`:
    A1, B1, A2, B2, ...): the needle crosses from a_i to b_i and crosses
    back from b_i to a_(i+1), so each rail gets a penetration every station,
    one `SATIN_SPACING_MM` apart -- what the satin tier lays on the same
    stem (MARINE's I: 0.40 mm per rail). The 10-07 wiring put ONE end down
    per station, rails alternating, and sewed every rail at 0.80 mm, half
    the engine's density; it had read the spike's 0.2 mm stations with both
    ends down (double density, boxes) as the ends being the error rather
    than the pitch."""
    legs = [math.dist(a, b) for a, b in stations]
    thr = comb_thresholds(legs, split_above_mm)
    pts: list[tuple[float, float]] = []
    for i, (a, b) in enumerate(stations):
        for pt in (a, b):
            if pts:
                if math.dist(pts[-1], pt) < stitches.SAME_POINT_MM:
                    continue
                pts.extend(split_points(pts[-1], pt, i, thr[i] if i < len(thr) else split_above_mm))
            pts.append(pt)
    return pts


def _centre_underlay(mids, short_columns: bool = False) -> list[tuple[float, float]] | None:
    """Centre walk down the span, inset at both ends, out and back.

    `short_columns` (`cfg.satin_underlay_short_columns`, built OFF
    2026-10-22): a span that holds one stitch (`machine.MIN_STITCH_MM`)
    gets its walk, the end inset giving way first -- the pro runs a centre
    walk under his serif blocks and 1.5 mm bars (Fremont's H at 92.5 mm
    carried 13 bare spans of 1.1-2.0 mm under the lane's own 1.8 mm floor
    with the satin tier's floor already lowered). Off, the floor is
    `2 * _UNDERLAY_INSET_MM + MIN_STITCH_MM`, as shipped."""
    ln = LineString(mids)
    inset = _UNDERLAY_INSET_MM
    if short_columns:
        if ln.length < machine.MIN_STITCH_MM - 1e-6:
            return None
        inset = min(inset, max(0.0, (ln.length - machine.MIN_STITCH_MM) / 2.0))
    elif ln.length <= 2 * inset + machine.MIN_STITCH_MM:
        return None
    core = substring(ln, inset, ln.length - inset)
    path = _walk_points(list(core.coords), _UNDERLAY_STEP_MM)
    return path + path[-2::-1]


def _inset_rails(stations, inset_mm: float) -> tuple[list, list]:
    """Both rails of every cross moved `inset_mm` toward each other along the
    cross (a quarter of the cross at most, the bound `stage6_satin`'s cap
    inset takes), so the push that follows lands where the satin tier's rails
    land. A cross with no direction stays as it is."""
    a_pts, b_pts = [], []
    for pa, pb in stations:
        d = math.dist(pa, pb)
        if d < 1e-9:
            a_pts.append(pa)
            b_pts.append(pb)
            continue
        k = min(inset_mm, 0.25 * d) / d
        ux, uy = (pa[0] - pb[0]) * k, (pa[1] - pb[1]) * k
        a_pts.append((pa[0] - ux, pa[1] - uy))
        b_pts.append((pb[0] + ux, pb[1] + uy))
    return a_pts, b_pts


def _reach_fan_faces(stations, a_pts, b_pts, reach_mm: float,
                     outline: Polygon | None = None) -> tuple[list, list]:
    """The slant cross of a fanned end (`outline_cut._fan_ends`: the last
    cross lies ON the slant, its pivot shared with the cross before it)
    moved `reach_mm` outward, square to itself -- away from the cross
    before it. The rails stand `pull - RAIL_REACH_INSET_MM` off the outline
    after the push, but a cross lying along an edge is pushed only along
    that edge, so the slant face stood on the traced outline itself, short
    of where the satin tier's thread reaches there: the Becker A's feet
    read as a strip of unsewn ink (2.65 mm2 against shipped's 1.3 on that
    letter, 2026-10-11, `docs/renders/columns-slant-fan-2026-10-11/`).
    The face gets the rails' own net reach, no constant of its own. Ends
    that are not fanned are returned as they are.
    `outline` (`cfg.lettering_columns_square_ends` only): a fan face that
    does not lie on that polygon's boundary is a CUT, the far side of which
    is the next column's (the M's V, where both diagonals fan to one cut);
    it gets no reach."""
    a_pts, b_pts = list(a_pts), list(b_pts)
    if len(stations) < 2 or abs(reach_mm) < 1e-12:
        return a_pts, b_pts
    for i, j in ((len(stations) - 1, len(stations) - 2), (0, 1)):
        if not ({tuple(p) for p in stations[i]} & {tuple(p) for p in stations[j]}):
            continue                                    # no shared pivot: not a fan end
        if outline is not None:
            fa, fb = stations[i]
            if outline.boundary.distance(Point((fa[0] + fb[0]) / 2, (fa[1] + fb[1]) / 2)) > _FACE_EPS_MM:
                continue                                # the fan lies on a cut, not on the letter's edge
        a, b = a_pts[i], b_pts[i]
        L = math.dist(a, b)
        if L < 1e-9:
            continue
        nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ox, oy = (a_pts[j][0] + b_pts[j][0]) / 2, (a_pts[j][1] + b_pts[j][1]) / 2
        if (mx - ox) * nx + (my - oy) * ny < 0:
            nx, ny = -nx, -ny
        a_pts[i] = (a[0] + nx * reach_mm, a[1] + ny * reach_mm)
        b_pts[i] = (b[0] + nx * reach_mm, b[1] + ny * reach_mm)
    return a_pts, b_pts


# `cfg.lettering_columns_square_ends` (2026-10-13, built OFF). An outline
# edge that runs ACROSS a column -- more than this far off the column's own
# direction at that station -- is an END face of that column, not one of its
# sides. Geometry, not cloth: 45 deg is the bisector (an edge nearer the
# column's direction than across it is a side). A CANDIDATE, set by no fixture.
END_FACE_DEG = 45.0
# A station end this close to an outline edge lies on it: a square cap's last
# cross sits `outline_cut.CAP_INSET_MM` (0.03) inside its face, plus a hair.
_FACE_EPS_MM = 0.05
# Two end faces whose directions differ by more than this (as a sine: 10 deg)
# meet at a CORNER, and a penetration on both is held at it (`_hold_end_faces`).
# Under it they are one face traced in two pieces. Geometry, a CANDIDATE.
_CORNER_SIN = math.sin(math.radians(10.0))


def _ring_edges(poly: Polygon) -> list[tuple[tuple, tuple, tuple]]:
    """Every edge of `poly`'s rings as (p, q, unit direction), degenerate
    edges skipped."""
    out = []
    for ring in [poly.exterior, *poly.interiors]:
        cs = list(ring.coords)
        for p, q in zip(cs[:-1], cs[1:]):
            L = math.dist(p, q)
            if L > 1e-9:
                out.append((tuple(p), tuple(q), ((q[0] - p[0]) / L, (q[1] - p[1]) / L)))
    return out


def _seg_dist(p, e) -> float:
    (ax, ay), (bx, by), (ux, uy) = e
    L = math.dist((ax, ay), (bx, by))
    t = max(0.0, min(L, (p[0] - ax) * ux + (p[1] - ay) * uy))
    return math.dist(p, (ax + ux * t, ay + uy * t))


def _station_dirs(col: Column) -> list[tuple[float, float]]:
    """The column's own direction at each station: its axis when straight,
    else the centreline's local tangent."""
    if col.axis is not None:
        return [tuple(col.axis)] * len(col.stations)
    m = _mids(col.stations)
    out = []
    for i in range(len(m)):
        p, q = m[max(0, i - 1)], m[min(len(m) - 1, i + 1)]
        L = math.dist(p, q)
        out.append(((q[0] - p[0]) / L, (q[1] - p[1]) / L) if L > 1e-9 else (1.0, 0.0))
    return out


def end_faces(columns: list[Column], poly: Polygon) -> list[int]:
    """Indices into `_ring_edges(poly)` of the letter's TERMINAL faces: the
    edges a column's first or last cross lies ALONG (its midpoint on the
    edge, the cross within `END_FACE_DEG` of the edge's direction) -- a
    square cap on its face, a fan's final cross on its slant."""
    edges = _ring_edges(poly)
    lim = math.cos(math.radians(END_FACE_DEG))
    faces: set[int] = set()
    for col in columns:
        for a, b in (col.stations[0], col.stations[-1]):
            L = math.dist(a, b)
            if L < 1e-9:
                continue
            c = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            for k, e in enumerate(edges):
                if abs(c[0] * e[2][0] + c[1] * e[2][1]) >= lim and _seg_dist(mid, e) <= _FACE_EPS_MM:
                    faces.add(k)
    return sorted(faces)


def end_face_hold(columns: list[Column], poly: Polygon):
    """What `_hold_end_faces` needs for one letter: (edges, terminal faces)."""
    return _ring_edges(poly), frozenset(end_faces(columns, poly))


def sewn_rails(col: Column, poly: Polygon, pull_mm: float, pull_floor_mm: float, hold=None):
    """One column's crosses as the fabric gets them, before the cross floor:
    rails inset, pushed by the pull, a fanned straight end's face given the
    rails' reach -- and, with `hold` (`end_face_hold`, under
    `cfg.lettering_columns_square_ends`), every end-face penetration held on
    its face. -> (a_pts, b_pts). `tools/column_ends.py` reads it too."""
    from .stage6_satin import _push_rails
    a_pts, b_pts = _inset_rails(col.stations, RAIL_REACH_INSET_MM)
    if pull_mm > 0:
        a_pts, b_pts = _push_rails(a_pts, b_pts, poly, pull_mm, pull_floor_mm)
    if col.kind in ("straight", "folded"):      # a folded column's ends are its legs' straight ends
        a_pts, b_pts = _reach_fan_faces(col.stations, a_pts, b_pts,
                                        pull_mm - RAIL_REACH_INSET_MM,
                                        **({"outline": poly} if hold is not None else {}))
    if hold is not None:
        a_pts, b_pts = _hold_end_faces(col, a_pts, b_pts, *hold, poly,
                                       max(0.0, pull_mm - RAIL_REACH_INSET_MM), pull_mm)
    return a_pts, b_pts


def _hold_end_faces(col: Column, a_pts, b_pts, edges, letter_faces, poly: Polygon, reach_mm: float,
                    pull_mm: float | None = None):
    """`cfg.lettering_columns_square_ends`: every penetration that started ON
    an end face keeps only the part of its displacement (rail inset, pull
    push, fan-face reach) that runs ALONG that face -- it slides on the
    outline, never off it -- so a column ends on the letter's own edge.

    A face, for one station end, is an outline edge within `_FACE_EPS_MM`
    whose direction is more than `END_FACE_DEG` off the column's own
    direction there (`_station_dirs`); a side is pushed as before. Every
    column also holds on the letter's TERMINAL faces (`end_faces`: an edge
    some column's end cross lies along), so a serif whose side continues an
    arm's end face ends flush with it (HOTEL's E, where the upper serif's
    side stood 0.29 mm past the arm's end). Where a point lies on a face and
    a side (a square cap's corner) the face holds it; on two faces that
    meet at a corner (more than `_CORNER_SIN` apart) it does not move.

    A slide that runs off the face's end (a square cap's corner, pushed
    sideways along its face: the column's own side pull) is kept. No
    penetration, held or not, ends further outside `poly` than the rails'
    side reach `reach_mm`: the move is cut back along itself (the M's top
    joint, where a fan face's reach on top of the push stood 0.37 mm out)."""
    lim = math.cos(math.radians(END_FACE_DEG))
    dirs = _station_dirs(col)
    out_a, out_b = list(a_pts), list(b_pts)
    boundary = poly.boundary
    # each cross's own side reach: the pull less the inset that cross got
    # (`_inset_rails`: a quarter of a cross under 0.44 mm)
    side_reach = None if pull_mm is None else [
        max(0.0, pull_mm - min(RAIL_REACH_INSET_MM, 0.25 * math.dist(a, b)))
        for a, b in col.stations]

    def outside(q) -> float:
        pt = Point(q)
        return 0.0 if poly.covers(pt) else boundary.distance(pt)
    for i, ((a0, b0), d) in enumerate(zip(col.stations, dirs)):
        for p0, out in ((a0, out_a), (b0, out_b)):
            best, bd = None, _FACE_EPS_MM
            faces = []
            for k, e in enumerate(edges):
                dist = _seg_dist(p0, e)
                if dist > _FACE_EPS_MM:
                    continue
                face = abs(d[0] * e[2][0] + d[1] * e[2][1]) < lim or k in letter_faces
                if face:
                    faces.append(e)
                    if dist <= bd:
                        best, bd = e, dist
            p1 = out[i]
            if len(faces) >= 2 and any(
                    abs(f[2][0] * g[2][1] - f[2][1] * g[2][0]) > _CORNER_SIN
                    for f in faces for g in faces):
                # On two end faces that meet at an angle (the M's V, whose
                # flat foot meets the right diagonal's outer edge): a slide
                # along either runs off the other, 0.17 mm under the flat on
                # Fremont 81 mm. Held on both, the corner stays where it is.
                out[i] = p0
                continue
            if best is not None:
                f = best[2]
                s = (p1[0] - p0[0]) * f[0] + (p1[1] - p0[1]) * f[1]
                p1 = (p0[0] + f[0] * s, p0[1] + f[1] * s)
            # Each cross keeps its own side reach. A cross under 0.44 mm is
            # inset by a quarter of itself, not by RAIL_REACH_INSET_MM, so its
            # push reaches further than `reach_mm`; cut back to that,
            # golden_tee's 0.10 mm bars fell under the cross floor and went
            # unsewn (+0.56 mm2 bare on one letter at 50 mm). A held point
            # stays on its face's line either way.
            limit = side_reach[i] if side_reach is not None else reach_mm
            if outside(p1) > limit + 1e-9:
                # the longest part of the move that stays inside the reach
                # (a fan face's reach on top of the push stood 0.37 mm out)
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                lo, hi = 0.0, 1.0
                for _ in range(16):
                    t = (lo + hi) / 2
                    if outside((p0[0] + dx * t, p0[1] + dy * t)) > limit:
                        hi = t
                    else:
                        lo = t
                p1 = (p0[0] + dx * lo, p0[1] + dy * lo)
            out[i] = p1
    return out_a, out_b


def small_print_counters(poly: Polygon, rings, min_width_mm: float) -> Polygon:
    """`cfg.small_print_floor`: the letter `poly` with the counters stage 4's
    sliver floor dropped (`meta["small_counters"]`) punched back -- each one
    whose widest inscribed circle is at least `min_width_mm` across
    (`thread_profile(wt).counter_min_width_mm`) and that lies inside the
    letter. A counter narrower than that cannot stay open under thread and
    stays sewn, as before. Returns `poly` itself when nothing qualifies."""
    keep = _wide_counters(poly, rings, min_width_mm)
    if not keep:
        return poly
    out = poly.difference(unary_union(keep))
    return out if out.geom_type == "Polygon" and not out.is_empty else poly


def _wide_counters(poly: Polygon, rings, min_width_mm: float) -> list[Polygon]:
    """The recorded counters (`meta["small_counters"]`) that lie inside
    `poly` and are at least `min_width_mm` across (largest inscribed
    circle) -- the ones `small_print_counters` punches back."""
    from shapely.ops import polylabel

    keep = []
    for ring in rings or ():
        if len(ring) < 3:
            continue
        c = Polygon(ring).buffer(0)
        if c.is_empty or c.geom_type != "Polygon" or not poly.contains(c):
            continue
        centre = polylabel(c, tolerance=0.01)
        if 2.0 * centre.distance(c.exterior) >= min_width_mm:
            keep.append(c)
    return keep


def small_print_counter_set(art: Polygon, rings, min_width_mm: float,
                            lettering: bool) -> list[Polygon]:
    """`cfg.small_print_floor` outside the Column lane: the counters a run-
    or fill-tier shape must keep open. Every recorded counter stage 4's
    sliver floor dropped that is one laid width across (`_wide_counters`),
    and -- when the shape is lettering, the Column lane's own scope -- the
    counters its artwork polygon still has. A shape that is not tagged as
    lettering but had a counter of that width dropped is small print by the
    same evidence (the synthetic 8 and 0 lose their text tag at a 3 mm cap
    and fall to the fill tier); its other holes are left as they were."""
    if art is None or art.is_empty or art.geom_type != "Polygon":
        return []
    out = _wide_counters(art, rings, min_width_mm)
    if lettering:
        out += [Polygon(r) for r in art.interiors]
    return [c for c in out if not c.is_empty]


def small_print_clear(poly, counters, clear_mm: float, art=None, chord_mm: float | None = None,
                      bar_mm: float | None = None):
    """`poly` (the shape a run or fill tier is about to sew) with every
    counter grown by `clear_mm` cut out of it: a fill's rows and a run's
    ring then lie that far off the counter, so the thread's EDGE, not its
    centre, meets the counter's edge (half the block's laid width, the
    Column lane's `_clear_counters` hold). The counter itself is a hole, so
    the tier's own travel stays out of it.

    A stroke the growth would eat is kept whole: ink of `art` (the
    artwork letter) within `clear_mm` of one counter and of another, or of
    the letter's outside, is a bar thinner than one laid width -- a B's
    middle bar, a slashed zero's slash, an O's ring -- and cutting it
    would change the glyph, not open it. The Column lane's own rule is the
    same: it never takes a cross under the cross floor. Returns `poly`
    itself when there is nothing to cut or the cut would leave nothing.

    `chord_mm` (the run tier's bean stitch, `machine.BEAN_STITCH_MM`): the
    run tier sews a counter's ring as `round(length / chord_mm)` straight
    stitches between points ON the ring, and every one of those chords cuts
    INTO the counter by its sagitta -- golden_tee's O at a 3 mm cap sewed
    its 0.76 mm counter as a pentagon of 0.73 mm chords, 0.42 open with the
    ring held half a width off (`tools/small_print.py`). Given, each
    counter grows further, to the ring whose chords' midpoints sit
    `clear_mm` off it (`_chord_hold`), never past the letter's outside.
    None (the fill tier, whose rows are clipped to the ring exactly): as
    before."""
    if not counters or clear_mm <= 0 or poly is None or poly.is_empty:
        return poly
    # A traced polygon can self-touch (golden_tee's italic O at a 3 mm cap);
    # GEOS then returns a collection or nothing from the cut. Repaired here,
    # where the flag is on and there is a counter to cut, and nowhere else.
    src = poly
    poly = _polygonal(poly if poly.is_valid else poly.buffer(0))
    if art is not None and not art.is_valid:
        art = _polygonal(art.buffer(0))
    grown = [c.buffer(clear_mm) for c in counters]
    cut = unary_union(grown)
    if art is not None and not art.is_empty:
        ink = art.difference(unary_union(counters))
        filled = unary_union([Polygon(g.exterior) for g in getattr(art, "geoms", [art])])
        thin = []
        thin_out = []
        for i, g in enumerate(grown):
            # through the letter's outside, or into another counter's growth
            t = g.difference(filled)
            if bar_mm and not t.is_empty:
                thin_out.append(t)
            others = [h for j, h in enumerate(grown) if j != i]
            if others:
                t = t.union(g.difference(counters[i]).intersection(unary_union(others)))
            if not t.is_empty:
                thin.append(t)
        if thin:
            keep = unary_union(thin).buffer(clear_mm).intersection(ink)
            if bar_mm:
                narrow = _narrow_bars(counters, grown, thin_out, clear_mm, bar_mm, ink)
                # never at the price of the letter's connectivity: a band
                # that leaves the sewn shape in more pieces than the whole
                # bar did is not taken
                if (_n_parts(_polygonal(poly.difference(cut.difference(narrow))))
                        <= _n_parts(_polygonal(poly.difference(cut.difference(keep))))):
                    keep = narrow
            cut = cut.difference(keep)
        if chord_mm:
            cut = _chord_hold(cut, counters, clear_mm, chord_mm, filled,
                              keep if thin else None)
    out = _polygonal(poly.difference(cut))
    if out.is_empty or out.geom_type not in ("Polygon", "MultiPolygon"):
        return src
    return out


def _narrow_bars(counters, grown, thin_out, clear_mm: float, bar_mm: float, ink):
    """`small_print_clear`'s fill-tier keep: a bar between two counters
    thinner than the hold, narrowed to `bar_mm` (the tier's row spacing)
    about its middle instead of kept edge to edge.

    A fill row's penetrations sit on the polygon's edge and its thread
    spreads half a laid width past them. A bar kept whole is sewn edge to
    edge, so it lays `w + 2 * clear_mm` of thread and spills `clear_mm`
    into the counter on each side -- the synthetic slashed 0 at a 3 mm cap:
    a 0.32 mm slash between two 0.5 mm counters, 0.42 open (`tools/
    small_print.py`). Narrowed to a band `w'` wide about its middle (the
    points whose distances to the two counters differ by at most
    `bar_mm`), the thread still covers the whole bar (`w' + 2 * clear_mm
    >= w` for any bar under `2 * clear_mm`) and spills `clear_mm - (w -
    w') / 2` instead of `clear_mm`. The band is the tier's row spacing
    wide, so one row still lands in a bar that runs along the rows; the
    core every point of which is within the hold of both counters (what
    today's keep grows from) is always kept, and nothing is kept outside
    today's keep. A bar no wider than a row is kept whole, as before. No
    new constant: the band is the row spacing, the hold half a laid width.

    A stroke between a counter and the letter's outside (an O's ring) is
    kept whole, as before: what it spills outward is outline, not a
    counter."""
    parts = []
    if thin_out:
        parts.append(unary_union(thin_out).buffer(clear_mm).intersection(ink))
    half = bar_mm / 2.0
    step = bar_mm / 4.0
    n_steps = int(math.ceil(2.0 * clear_mm / step)) + 1
    for i in range(len(counters)):
        for j in range(i + 1, len(counters)):
            core = grown[i].difference(counters[i]).intersection(grown[j].difference(counters[j]))
            if core.is_empty:
                continue
            whole = core.buffer(clear_mm).intersection(ink)     # today's keep
            if counters[i].distance(counters[j]) <= bar_mm + 1e-9:
                parts.append(whole)         # no wider than a row: kept whole
                continue
            # the band |d_i - d_j| <= bar_mm about the bar's middle: the
            # union, over a ladder of distances s, of the points within
            # bar_mm / 2 of s from both counters
            band = []
            for k in range(n_steps):
                s = k * step
                lo = max(0.0, s - half)
                ai = counters[i].buffer(s + half)
                aj = counters[j].buffer(s + half)
                if lo > 0:
                    ai = ai.difference(counters[i].buffer(lo))
                    aj = aj.difference(counters[j].buffer(lo))
                band.append(ai.intersection(aj))
            keep = whole.intersection(unary_union(band + [core]))
            parts.append(keep if not keep.is_empty else whole)
    parts = [g for g in parts if not g.is_empty]
    return unary_union(parts) if parts else Polygon()


def _chord_hold(cut, counters, clear_mm: float, chord_mm: float, filled, keep):
    """`small_print_clear`'s run-tier growth: each counter grown to the
    ring whose `n` chords (`n = max(3, round(length / chord_mm))`, the run
    tier's own sampling) have their midpoints `clear_mm` off the counter.
    On a circle of radius `rho` that ring is `(rho + clear_mm) / cos(pi /
    n)`; `rho` is read as `2 * area / perimeter` of the grown ring (exact
    on a circle), and `n` follows the ring it sets, so the two are iterated
    to a fixed point. No new constant: the chord is the bean stitch, the
    hold is half a laid width.

    The growth stops a same-point hair inside the letter's outside
    (`filled`): a stroke thinner than the growth is not cut through, the
    counter's ring only moves out to the letter's edge (where the outline's
    own run already lays its thread). A thin bar `small_print_clear` kept
    (`keep`) stays kept."""
    if filled is None or filled.is_empty:
        return cut
    lim = filled.buffer(-stitches.SAME_POINT_MM)
    extra = []
    for c in counters:
        if c.is_empty:
            continue
        r = clear_mm
        for _ in range(6):
            g = c.buffer(r)
            per = g.length
            if per <= 0:
                break
            n = max(3, int(round(per / chord_mm)))
            rho = 2.0 * g.area / per
            r_new = (rho - r + clear_mm) / math.cos(math.pi / n) - (rho - r)
            if abs(r_new - r) < 1e-4:
                r = r_new
                break
            r = r_new
        if r > clear_mm:
            extra.append(c.buffer(r))
    if not extra:
        return cut
    add = unary_union(extra).intersection(lim)
    if keep is not None and not keep.is_empty:
        add = add.difference(keep)
    return cut.union(add)


def _n_parts(g) -> int:
    return 0 if g.is_empty else len(getattr(g, "geoms", [g]))


def _polygonal(g):
    """The polygon parts of `g` (a GEOS cut can return a collection)."""
    if g.geom_type == "GeometryCollection":
        parts = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
        return unary_union(parts) if parts else Polygon()
    return g


def _clear_counters(a_pts, b_pts, poly: Polygon, clear_mm: float,
                    min_cross_mm: float) -> tuple[list, list]:
    """`cfg.small_print_floor`: every penetration that lands within
    `clear_mm` (half the block's laid thread width) of one of the letter's
    counters is moved back along its own cross until it sits `clear_mm`
    off the counter, so the thread's EDGE, not its centre, meets the
    counter's edge. Never past the point where the cross would fall under
    `min_cross_mm`; a cross with no room is left as it is."""
    holes = [Polygon(r) for r in poly.interiors]
    if not holes or clear_mm <= 0:
        return a_pts, b_pts
    zone = unary_union([h.buffer(clear_mm) for h in holes])
    out_a, out_b = list(a_pts), list(b_pts)
    for i, (pa, pb) in enumerate(zip(a_pts, b_pts)):
        d = math.dist(pa, pb)
        if d < 1e-9:
            continue
        for side in (0, 1):
            p = out_a[i] if side == 0 else out_b[i]
            q = out_b[i] if side == 0 else out_a[i]
            if not zone.contains(Point(p)):
                continue
            seg = LineString([p, q])
            outside = seg.difference(zone)
            if outside.is_empty:
                continue
            # where the cross first leaves the zone, walking from p toward q
            t = min(seg.project(Point(c)) for g in getattr(outside, "geoms", [outside])
                    for c in g.coords)
            L = seg.length
            # held AT the floor lands a float hair under it, and the floor
            # filter in `column_runs` then dropped the cross the hold meant
            # to keep: two of Fremont's EAT A crosses at a 3 mm cap went,
            # and the zigzag laid a 2.2 mm stitch over the counter
            # (`tools/small_print.py`, #878). Held a hair short of it.
            t = min(t, max(0.0, L - min_cross_mm - _FLOOR_EPS_MM))
            if t <= 0:
                continue
            np_ = seg.interpolate(t).coords[0]
            if side == 0:
                out_a[i] = np_
            else:
                out_b[i] = np_
    return out_a, out_b


_FLOOR_EPS_MM = 1e-9     # a float hair, not a tolerance: far under any stitch


def _counter_safe_pieces(stations, poly: Polygon, min_cross_mm: float,
                         clear_mm: float) -> tuple[list[list], int]:
    """`cfg.small_print_floor`: one column's stations (after every hold and
    guard) -> the runs of them that sew as satin with no stitch passing
    over one of the letter's counters, plus how many stations were not
    kept. Two ways a column laid a stitch over a counter, both measured
    with `tools/small_print.py` (#878):

    - **A gap.** The floor filter drops a run of crosses under
      `min_cross_mm`, and the zigzag joins the crosses either side of the
      gap with one long stitch -- at a 3 mm cap, straight over the counter
      beside the gap (Fremont's EAT A and P). Where that join would cross
      a counter, the dropped crosses come back when every one is at least
      one laid thread wide (`2 * clear_mm`) and neither they nor the joins
      between them cross a counter; otherwise the column is split there.
    - **A cross through the counter.** `outline_cut` can lay a column's
      crosses straight across a counter (the synthetic 0's and 8's at 4
      and 5 mm). Such a cross is cut at the counter and each stretch of
      it that is still a cross -- the halves either side, a bar between
      two counters -- sews in a column of its own (`subs`). The 0's
      slash is only CLIPPED by its ring's crosses (0.23-0.40 mm of it,
      under one laid width), so cutting them left it bare; it gets a
      column of its own from `_bar_columns`.

    A split column's pieces are linked by the walk's own link rule, which
    already keeps out of counters."""
    holes = [Polygon(r) for r in poly.interiors]
    zone = unary_union([h.buffer(-stitches.SAME_POINT_MM) for h in holes]) if holes else None
    if zone is not None and zone.is_empty:
        zone = None
    cut = unary_union(holes) if holes else None
    hold = unary_union([h.buffer(clear_mm) for h in holes]) if holes else None

    def over(p, q) -> bool:
        return zone is not None and math.dist(p, q) > 1e-9 and LineString([p, q]).intersects(zone)

    def join_ok(s, t) -> bool:
        # the stitch the zigzag lays between two crosses: b0 -> a1 walked
        # forward, b1 -> a0 walked back (`_satin_points`)
        (a0, b0), (a1, b1) = s, t
        return not (over(b0, a1) or over(a0, b1))

    def lines(g):
        return [x for x in getattr(g, "geoms", [g])
                if not x.is_empty and x.geom_type == "LineString" and x.length > 1e-9]

    def subs(a, b):
        """-> [(track, cross)]: the whole cross, or -- where it passes over
        a counter -- each stretch of it between counters: the half from
        rail a ("a"), the half to rail b ("b") and any bar between two
        counters ("m1", "m2", ...: the slash of a slashed zero). Each is
        held `clear_mm` off the counters where it stays a cross
        (`min_cross_mm`) and kept whole where only one laid width is left
        (`small_print_clear`'s rule: a bar the hold would eat is kept)."""
        if not over(a, b):
            return [("full", (a, b))] if math.dist(a, b) >= min_cross_mm else []
        seg = LineString([a, b])
        parts = sorted(lines(seg.difference(cut)), key=lambda g: seg.project(Point(g.centroid)))
        out = []
        for k, g in enumerate(parts):
            held = max(lines(g.difference(hold)), key=lambda x: x.length, default=None)
            x = (held if held is not None and held.length >= min_cross_mm
                 else g if g.length >= keep_mm else None)
            if x is None:
                continue
            p, q = x.coords[0], x.coords[-1]
            if seg.project(Point(p)) > seg.project(Point(q)):
                p, q = q, p
            track = ("a" if math.dist(g.coords[0], a) < 1e-6 or math.dist(g.coords[-1], a) < 1e-6
                     else "b" if math.dist(g.coords[0], b) < 1e-6 or math.dist(g.coords[-1], b) < 1e-6
                     else f"m{k}")
            out.append((track, (p, q)))
        return [(t, s) for t, s in out if not over(*s)]

    n = len(stations)
    pieces: list[dict] = []          # track, idx (station indices), sts
    open_: dict[str, dict] = {}
    keep_mm = 2.0 * clear_mm
    used: set[int] = set()

    def attach(piece, i, s, track) -> bool:
        last = piece["idx"][-1]
        if join_ok(piece["sts"][-1], s):
            pass
        elif (i > last + 1 and piece["track"] == "full" and track == "full"
              and all(k not in used and math.dist(*stations[k]) >= keep_mm
                      and not over(*stations[k]) for k in range(last + 1, i))
              and all(join_ok(x, y) for x, y in zip([piece["sts"][-1]] + stations[last + 1:i],
                                                      stations[last + 1:i] + [s]))):
            # the dropped crosses come back rather than a stitch over the counter
            piece["idx"].extend(range(last + 1, i))
            piece["sts"].extend(stations[last + 1:i])
            used.update(range(last + 1, i))
        else:
            return False
        piece["idx"].append(i)
        piece["sts"].append(s)
        used.add(i)
        if piece["track"] != track:
            if open_.get(piece["track"]) is piece:
                del open_[piece["track"]]
            piece["track"] = track
        open_[track] = piece
        return True

    for i, (a, b) in enumerate(stations):
        for track, s in subs(a, b):
            cands = [open_.get(track)] + ([open_.get("full")] if track != "full"
                                          else [v for k, v in open_.items() if k != "full"])
            seen = []
            for c in cands:
                if c is None or any(c is x for x in seen) or c["idx"][-1] == i:
                    continue
                seen.append(c)
                if attach(c, i, s, track):
                    break
            else:
                pc = dict(track=track, idx=[i], sts=[s])
                used.add(i)
                pieces.append(pc)
                open_[track] = pc
    return [p["sts"] for p in pieces], n - len(used)


def _bar_columns(poly: Polygon, ready: list[Column], spacing_mm: float) -> list[Column]:
    """`cfg.small_print_floor`: a column for each bar of ink between two of
    the letter's counters that the letter's columns leave unsewn.

    `outline_cut` builds the slashed 0 as ONE ring column and never builds
    its slash: the ring's crosses reached over the counter and into the
    slash, and that was the only thread the slash got. Once no cross may
    pass over a counter (`_counter_safe_pieces`) the slash went bare at 4
    and 5 mm caps (`tools/small_print.py` renders). The bar is the ink in
    the convex hull of the two counters, less the counters; when the
    columns' crosses cover under half of it, it is stationed across its
    long axis every `spacing_mm`, rail on its outline. Like a bar the hold
    would eat (`small_print_clear`), it is sewn whole -- its crosses run
    edge to edge between the counters -- down to the same-hole line
    (`machine.SATIN_SHORT_STITCH_AT_MM`)."""
    holes = [Polygon(r) for r in poly.interiors]
    if len(holes) < 2:
        return []
    sewn = unary_union([Polygon([a for a, _ in c.stations] + [b for _, b in c.stations][::-1]).buffer(0)
                        for c in ready])
    floor = machine.SATIN_SHORT_STITCH_AT_MM
    out = []
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            gap = unary_union([holes[i], holes[j]]).convex_hull.difference(holes[i]).difference(holes[j])
            bar = gap.intersection(poly)
            bar = max((g for g in getattr(bar, "geoms", [bar]) if g.geom_type == "Polygon"),
                      key=lambda g: g.area, default=None)
            if bar is None or bar.area < floor * floor:
                continue
            if bar.difference(sewn).area < 0.5 * bar.area:
                continue
            rect = list(bar.minimum_rotated_rectangle.exterior.coords)
            e1 = (rect[1][0] - rect[0][0], rect[1][1] - rect[0][1])
            e2 = (rect[2][0] - rect[1][0], rect[2][1] - rect[1][1])
            long_, short = (e1, e2) if math.hypot(*e1) >= math.hypot(*e2) else (e2, e1)
            L, Wd = math.hypot(*long_), math.hypot(*short)
            if L < 2 * spacing_mm or Wd < 1e-9:
                continue
            u = (long_[0] / L, long_[1] / L)
            v = (-u[1], u[0])
            cx = sum(p[0] for p in rect[:4]) / 4
            cy = sum(p[1] for p in rect[:4]) / 4
            stations = []
            n = int(L // spacing_mm)
            for k in range(n):
                t = -L / 2 + (k + 0.5) * L / n
                q = (cx + u[0] * t, cy + u[1] * t)
                line = LineString([(q[0] - v[0] * Wd, q[1] - v[1] * Wd),
                                   (q[0] + v[0] * Wd, q[1] + v[1] * Wd)])
                hit = bar.intersection(line)
                seg = max((g for g in getattr(hit, "geoms", [hit]) if g.geom_type == "LineString"),
                          key=lambda g: g.length, default=None)
                if seg is None or seg.length < floor:
                    continue
                p0, p1 = seg.coords[0], seg.coords[-1]
                if (p1[0] - p0[0]) * v[0] + (p1[1] - p0[1]) * v[1] < 0:
                    p0, p1 = p1, p0
                stations.append((p0, p1))
            if len(stations) >= 3:
                w = sorted(math.dist(a, b) for a, b in stations)[len(stations) // 2]
                out.append(Column(stations=stations, piece=bar, kind="straight", axis=u, width_mm=w))
    return out


def _tuck_stations(col: Column, end: int, through: Polygon, tuck_mm: float,
                   max_reach_mm: float, pitch_mm: float, poly_link, avoid=None):
    """Stations continuing `col` past the given end (0 or -1) into the piece
    it butts: one per `pitch_mm`, in order away from the column, until the
    cut line plus `tuck_mm` is reached (0 for a plain butt), never more
    than `max_reach_mm` past the cut, and stopping at the first cross the
    letter does not cover. The last station of a cut piece sits up to a
    pitch short of the cut, so even a plain butt usually gains a station.
    `avoid` (`cfg.lettering_columns_apex_cut`, the merged tips): none when
    the way to the cut line crosses it -- the piece is butted across a tip,
    not at it (MARINE's M at 95.7 mm: each leg's end reached the other leg
    over the V, and laid 3.4 mm of satin across it)."""
    sts = col.stations if end == 0 else col.stations[::-1]
    (a0, b0), (a1, b1) = sts[0], sts[1]
    m0 = ((a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2)
    m1 = ((a1[0] + b1[0]) / 2, (a1[1] + b1[1]) / 2)
    L = math.dist(m0, m1)
    if L < 1e-9:
        return []
    d = ((m0[0] - m1[0]) / L, (m0[1] - m1[1]) / L)
    reach = 4.0 * col.width_mm
    ray = LineString([m0, (m0[0] + d[0] * reach, m0[1] + d[1] * reach)])
    if through.covers(ray.interpolate(0.0)):
        gap = 0.0
    else:
        gap = min((math.dist(m0, g) for g in _coords(ray.intersection(through.boundary))), default=reach)
    if gap >= reach:
        return []
    if avoid is not None and gap > 0 and LineString([m0, ray.interpolate(gap).coords[0]]).intersects(avoid):
        return []
    out = []
    k = 1
    while True:
        sh = k * pitch_mm
        if sh - pitch_mm - gap >= tuck_mm - 1e-9:      # the previous station already reached
            break
        if sh - gap > max_reach_mm + 1e-9:            # never past the middle of the stroke
            break
        a = (a0[0] + d[0] * sh, a0[1] + d[1] * sh)
        b = (b0[0] + d[0] * sh, b0[1] + d[1] * sh)
        if not poly_link.covers(LineString([a, b])):
            break
        out.append((a, b))
        k += 1
    return out


def _coords(geom):
    if geom.is_empty:
        return []
    if hasattr(geom, "geoms"):
        return [c for g in geom.geoms for c in _coords(g)]
    return list(geom.coords)


def _inside_path(columns: list[Column], nodes, spans, a, b, reach_mm: float,
                 inside: Polygon, strict: bool = False) -> list[tuple[float, float]] | None:
    """The shortest way from `a` to `b` along the columns' centrelines (the
    walk's own graph: consecutive station midpoints, joined at span nodes),
    stepping on and off within `reach_mm` where that step stays `inside`.
    None when either point cannot step on, or the two are not connected.
    `strict` (`cfg.small_print_floor`): every edge of the graph stays
    `inside` too -- a split column's centreline can cross a counter."""
    import heapq

    mids = [_mids(c.stations) for c in columns]
    vid = {}
    pts: list[tuple[float, float]] = []

    def v(key, p):
        if key not in vid:
            vid[key] = len(pts)
            pts.append(p)
        return vid[key]

    adj: dict[int, list[tuple[int, float]]] = {}

    def link(i, j):
        if strict and not inside.covers(LineString([pts[i], pts[j]])):
            return
        w = math.dist(pts[i], pts[j])
        adj.setdefault(i, []).append((j, w))
        adj.setdefault(j, []).append((i, w))

    for ci, m in enumerate(mids):
        for k in range(1, len(m)):
            link(v((ci, k - 1), m[k - 1]), v((ci, k), m[k]))
    for s in spans:
        for key, idx in (("na", s["i0"]), ("nb", s["i1"])):
            link(v(("n", s[key]), nodes[s[key]]), v((s["ci"], idx), mids[s["ci"]][idx]))
    ia, ib = v("a", a), v("b", b)
    for end in (ia, ib):
        p = pts[end]
        near = sorted(range(len(pts) - 2), key=lambda i: math.dist(pts[i], p))[:8]
        for i in near:
            if (math.dist(pts[i], p) <= reach_mm
                    and inside.covers(LineString([p, pts[i]]))):
                link(end, i)
        if end not in adj:
            return None
    dist, prev, heap = {ia: 0.0}, {}, [(0.0, ia)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == ib:
            break
        if d > dist.get(u, math.inf):
            continue
        for w_, c in adj.get(u, ()):
            nd = d + c
            if nd < dist.get(w_, math.inf):
                dist[w_], prev[w_] = nd, u
                heapq.heappush(heap, (nd, w_))
    if ib not in dist:
        return None
    path, u = [pts[ib]], ib
    while u != ia:
        u = prev[u]
        path.append(pts[u])
    return path[::-1]


# ---------------------------------------------------------------- the walk

def _apex_tip_columns(columns: list[Column], crosses, tol: float, merge_r: float | None = None) -> dict:
    """`apex_cut`: the columns that sew a merged tip -> {column index:
    {"cut": the end (0 or -1) at its cross, "line": that cross, "ends":
    the (column, end) pairs that meet it there}}. A tip column's piece is
    the cut's tip piece (`outline_cut._apex_tip_piece`), one end lies on the
    cross (within `tol`) and the far end has closed (`_APEX_CLOSED`): the
    point. `merge_r` (`_span_graph`'s radius): or the far end is blunt and
    the radius alone would join it to another column's end it lies apart
    from (farther than `tol` from every other centreline): PROSEAL's bold,
    flat-topped A (2.3 mm across the top, 4.3 at the cut), whose top fell
    into one node with its left leg's foot 4.1 mm off -- sewn up into the
    top, the walk hopped 3.3 mm back down over it. A blunt end the radius
    leaves alone is a dead end the walk already doubles (MFab's 4, its IN).
    A cross split at its crotch is two records; the line is both. An
    end meets a tip when its middle lies within `tol` of the cross -- each
    column's nearer end, to one tip. A tip nothing meets that way is left
    out, and the walk takes it as it always has: MARINE's M at 76.5 mm,
    whose V hangs between the flanks of its stems, which run on past it."""
    from .outline_cut import _apex_tip_piece
    lines = [LineString(c) for c in crosses]
    tips = {}
    for ci, c in enumerate(columns):
        if len(c.stations) < 2 or _apex_tip_piece(c.piece, crosses) is None:
            continue
        d0 = min(ln.distance(Point(c.start)) for ln in lines)
        d1 = min(ln.distance(Point(c.end)) for ln in lines)
        cut = 0 if d0 <= d1 else -1
        w_cut, w_far = math.dist(*c.stations[cut]), math.dist(*c.stations[-1 - cut])
        if min(d0, d1) > tol:
            continue
        if w_far > _APEX_CLOSED * w_cut:
            far = Point(c.end if cut == 0 else c.start)
            others = [o for cj, o in enumerate(columns) if cj != ci]
            if (merge_r is None or not others
                    or min(far.distance(Point(e)) for o in others for e in (o.start, o.end)) > merge_r
                    or min(far.distance(LineString(_mids(o.stations)) if len(o.stations) > 1
                                        else Point(o.start)) for o in others) <= tol):
                continue
        m = Point(c.start if cut == 0 else c.end)
        near = {i for i, ln in enumerate(lines) if ln.distance(m) <= tol}
        # ... and the record it meets at the crotch, however far its middle
        # lies: PROSEAL's bold A, its left half 1.4 mm off the cut's end
        near |= {i for i, ln in enumerate(lines) if any(ln.distance(lines[k]) <= 1e-6 for k in near)}
        tips[ci] = {"cut": cut, "line": unary_union([lines[i] for i in sorted(near)]),
                    "at": (m.x, m.y), "ends": []}
    for cj, c in enumerate(columns):
        if cj in tips or not tips:
            continue
        # nearest the tip's own cut end first: the W's stub between two
        # tips lies within 0.37-0.42 mm of BOTH crosses at both its ends
        near = sorted((math.dist(tips[t]["at"], p), tips[t]["line"].distance(Point(p)), end, t)
                      for end, p in ((0, c.start), (-1, c.end)) for t in tips)
        took_end, took_tip = set(), set()
        for _d, d, end, t in near:
            if d <= tol and end not in took_end and t not in took_tip:
                tips[t]["ends"].append((cj, end))
                took_end.add(end)
                took_tip.add(t)
    return {t: v for t, v in tips.items() if v["ends"]}


def _span_graph(columns: list[Column], merge_r: float, within: Polygon | None = None,
                tips: dict | None = None):
    """Columns -> (nodes, spans, junctions). A span is a stretch of one
    column between two station indices, with its two node ids; a column is
    cut where another column's END lands on its centreline away from its
    own ends, and each such landing is a junction (the butting column and
    end, the through column and the station it lands on).
    `within` (`cfg.lettering_columns_corner_fold`, a letter with a folded
    column only): two ends within `merge_r` of each other are one node only
    when the letter covers the line between them. The radius alone (1.3 W +
    0.3 + the pull, 2.5 mm on Drone's E) made the E's top-arm and middle-arm
    TIPS one node across the slot, which gave the top tip an even degree:
    the walk could no longer start there, so it started at the bottom tip
    and sewed the middle arm from the top tip with an 18.8 mm routed hop.
    `tips` (`cfg.lettering_columns_apex_cut`, `_apex_tip_columns`): a merged
    tip's two ends are nodes of their own, read off the cut, not the radius:
    its point a free end, its cut end one node with the ends that lie on its
    cross. A tip's ends land on no column and nothing lands on a tip. By the
    radius alone (1.3 W + 0.3 + the pull) MFab's W fell into three
    components (a trim) when its middle stroke's stub took a tip's node
    first. An end on a tip's cross may still butt another column (the W's
    stub, which the radius also puts on its third stroke: that tuck covers
    the crotch); a butt that reaches its column across a tip lays no tuck
    (`_tuck_stations`' `avoid`)."""
    mids = [_mids(c.stations) for c in columns]
    tips = tips or {}
    attach = {e: t for t, v in tips.items() for e in v["ends"]}     # (column, end) -> its tip
    ends = [(cj, 0, m[0]) for cj, m in enumerate(mids)] + [(cj, -1, m[-1]) for cj, m in enumerate(mids)]
    cuts_per: list[list[int]] = []
    junctions: list[dict] = []      # butting column `ci`/`end` meets `through` at station `k`
    for ci, m in enumerate(mids):
        n = len(m)
        idx = {0, n - 1}
        lo, hi = _END_FRAC * (n - 1), (1 - _END_FRAC) * (n - 1)
        for cj, end, p in ends:
            if cj == ci:
                continue
            if tips and (ci in tips or cj in tips):
                continue
            best = min(range(n), key=lambda k: math.dist(m[k], p))
            if math.dist(m[best], p) <= merge_r and lo < best < hi:
                idx.add(best)
                junctions.append(dict(ci=cj, end=end, through=ci, k=best))
        cuts = sorted(idx)
        uniq = [cuts[0]]
        for k in cuts[1:]:
            if k - uniq[-1] >= 2:
                uniq.append(k)
        if uniq[-1] != n - 1:
            uniq[-1] = n - 1
        cuts_per.append(uniq)
    nodes: list[tuple[float, float]] = []
    fixed: dict[tuple[int, int], int] = {}      # (column, station) -> its node, read off the cut
    for t, info in tips.items():
        n = len(mids[t])
        k_cut = 0 if info["cut"] == 0 else n - 1
        for k in (k_cut, n - 1 - k_cut):
            nodes.append(mids[t][k])
            fixed[(t, k)] = len(nodes) - 1
    for (cj, end), t in attach.items():
        fixed[(cj, 0 if end == 0 else len(mids[cj]) - 1)] = fixed[(t, 0 if tips[t]["cut"] == 0
                                                                  else len(mids[t]) - 1)]
    own_nodes = set(fixed.values())

    def node_of(p, key=None):
        if key in fixed:
            return fixed[key]
        for i, q in enumerate(nodes):
            if i in own_nodes:
                continue
            if math.dist(q, p) <= merge_r and (within is None or within.covers(LineString([q, p]))):
                return i
        nodes.append(p)
        return len(nodes) - 1

    spans = []      # dict(ci, i0, i1, na, nb)
    for ci, cuts in enumerate(cuts_per):
        own = []
        for i0, i1 in zip(cuts, cuts[1:]):
            own.append(dict(ci=ci, i0=i0, i1=i1,
                            na=node_of(mids[ci][i0], (ci, i0)), nb=node_of(mids[ci][i1], (ci, i1))))
        # A stub at a column's END whose two ends fall in ONE node is not a
        # span of its own (a bold letter's merge radius swallows the tail
        # past a junction): it rides with its neighbour, so the walk never
        # finishes a leg a stub's length away from the node it reports.
        while len(own) > 1 and own[0]["na"] == own[0]["nb"]:
            own[1]["i0"], own[1]["na"] = own[0]["i0"], own[0]["na"]
            own.pop(0)
        while len(own) > 1 and own[-1]["na"] == own[-1]["nb"]:
            own[-2]["i1"], own[-2]["nb"] = own[-1]["i1"], own[-1]["nb"]
            own.pop()
        spans.extend(own)
    return nodes, spans, junctions


def _euler_trail(nodes, spans, start_near, prefer=frozenset(), prefer_within_mm=math.inf,
                 end_near=None, dead_ends=frozenset(), span_mm=()):
    """Chinese-postman duplication plus Hierholzer, per component.
    -> list of components, each a list of (span index, from node, to node)
    in walk order; components ordered nearest-first from `start_near`.
    `prefer` names nodes to START a trail from when they are odd -- the free
    ends of butting columns, so the stem of a T is sewn before the bar it
    goes under: the trail's endpoints are the odd nodes left unpaired, and
    the pairing below consumes every other odd node first. A preferred
    start farther than `prefer_within_mm` from the needle is not taken:
    on 4 mm caps it turned the entry hop into a trim on 7 of 39 letters
    (gaulke 23 -> 30) for a tuck the letter is too small to show.
    `dead_ends` (`cfg.lettering_columns_apex_cut`): merged tips' points, and
    `span_mm` each span's length. A component holding one is walked by
    `postman`: a trail may START at a dead end, never end there -- an odd one
    that does not start the trail is paired (its tip span doubled: run in
    under it, satin out from the point). The pro sews every tip from its
    point up; ended at the point, the walk sewed into it and hopped out of
    a dead end."""
    import heapq
    adj: list[list[tuple[int, int]]] = [[] for _ in nodes]     # (instance id, to)
    inst: list[tuple[int, int, int]] = []                        # (span, a, b)

    def add_inst(si, a, b):
        iid = len(inst)
        inst.append((si, a, b))
        adj[a].append((iid, b))
        adj[b].append((iid, a))

    for si, s in enumerate(spans):
        add_inst(si, s["na"], s["nb"])
    comp = [-1] * len(nodes)
    comps: list[list[int]] = []
    for s0 in range(len(nodes)):
        if comp[s0] != -1 or not adj[s0]:
            continue
        comp[s0] = len(comps)
        members = [s0]
        q = [s0]
        while q:
            u = q.pop()
            for _, v in adj[u]:
                if comp[v] == -1:
                    comp[v] = comp[s0]
                    members.append(v)
                    q.append(v)
        comps.append(members)

    def trail(cnodes, cursor, exit_to=None):
        if dead_ends and any(i in dead_ends for i in cnodes):
            return postman(cnodes, cursor, exit_to)
        deg = {i: len(adj[i]) for i in cnodes}
        rank = sorted(cnodes, key=lambda i: i in prefer)       # preferred nodes last
        odd = [i for i in rank if deg[i] % 2 == 1]
        # `end_near` on the LAST component (the satin tier's
        # `satin_exit_toward_next`, ported): the trail's two ends are chosen
        # together -- the start nearest the needle (a butting column's free
        # end within reach, when there is one, for the tuck), the end nearest
        # where the needle goes next -- and kept out of the pairing, so
        # Hierholzer from the start finishes at the end. Without it the walk
        # ended wherever the pairing left it and the hop into the next letter
        # was a trim (Fremont's entry trims 15 -> 21 under the lane).
        reserved = None
        if exit_to is not None and cursor is not None and len(odd) >= 2:
            near_pref = [i for i in odd if i in prefer
                         and math.dist(nodes[i], cursor) <= prefer_within_mm]
            starts = near_pref or odd
            # never trade the hop IN for the hop out: a start the needle can
            # sew to (within the trim distance, or no farther than the nearest
            # start) -- unguarded, drone's inside-letter trims rose 4 -> 6
            d0 = min(math.dist(cursor, nodes[i]) for i in starts)
            starts = [i for i in starts
                      if math.dist(cursor, nodes[i]) <= max(prefer_within_mm, d0 + 1e-9)]
            reserved = min(((a, b) for a in starts for b in odd if a != b),
                           key=lambda ab: (math.dist(cursor, nodes[ab[0]])
                                           + math.dist(nodes[ab[1]], exit_to), ab))
        free = lambda: [i for i in odd if reserved is None or i not in reserved]
        guard = 0
        while len(free()) > (0 if reserved else 2) and guard < 200:
            guard += 1
            u = free()[0]
            prev_n, prev_i, seen = {}, {}, {u}
            q = deque([u])
            tgt, fallback = -1, -1
            while q:
                x = q.popleft()
                if x != u and deg[x] % 2 == 1 and (reserved is None or x not in reserved):
                    # a preferred node is paired only when nothing else is
                    # odd: paired, it goes even and can no longer start the
                    # trail (a T's junction paired with the stem's foot
                    # doubled the stem and split the bar in two)
                    if x not in prefer:
                        tgt = x
                        break
                    if fallback < 0:
                        fallback = x
                for iid, v in adj[x]:
                    if v not in seen:
                        seen.add(v)
                        prev_n[v], prev_i[v] = x, iid
                        q.append(v)
            if tgt < 0:
                tgt = fallback
            if tgt < 0:
                break
            x = tgt
            while x != u:
                p = prev_n[x]
                si, a, b = inst[prev_i[x]]
                add_inst(si, a, b)
                deg[x] += 1
                deg[p] += 1
                x = p
            odd = [i for i in rank if deg[i] % 2 == 1]
        pool = odd if odd else cnodes
        if reserved is not None:
            start = reserved[0]
        elif exit_to is not None and cursor is not None and not odd:
            # a closed web ends where it starts: one node pays both hops
            # (within the same reach as above)
            d0 = min(math.dist(cursor, nodes[i]) for i in cnodes)
            ok = [i for i in cnodes if math.dist(cursor, nodes[i]) <= max(prefer_within_mm, d0 + 1e-9)]
            start = min(ok, key=lambda i: (math.dist(cursor, nodes[i])
                                           + math.dist(nodes[i], exit_to), i))
        elif cursor is None:
            start = min(pool, key=lambda i: (i not in prefer, i))
        else:
            near = [i for i in pool if i in prefer and math.dist(nodes[i], cursor) <= prefer_within_mm]
            start = min(near or pool, key=lambda i: math.dist(nodes[i], cursor))
        return walk_from(start, cnodes)

    def postman(cnodes, cursor, exit_to=None):
        # `dead_ends`: the trail's two ends and the paths doubled to pair the
        # other odd nodes are chosen TOGETHER, by millimetres -- the hop in,
        # the hop out, and every doubled span's length (a min-weight perfect
        # matching over shortest paths; a letter has a handful of odd nodes).
        # The pairing above takes the first odd node by hops, not length: on
        # MARINE's M at 95.7 mm it paired the tip's point with the far stem's
        # foot and doubled 29 mm of strokes for a 3 mm tip.
        odd = sorted(i for i in cnodes if len(adj[i]) % 2 == 1)
        sp: dict[int, tuple[dict, dict]] = {}
        for u in odd:
            dist, prev, heap = {u: 0.0}, {}, [(0.0, u)]
            while heap:
                d, x = heapq.heappop(heap)
                if d > dist[x]:
                    continue
                for iid, v in adj[x]:
                    nd = d + span_mm[inst[iid][0]]
                    if nd < dist.get(v, math.inf):
                        dist[v], prev[v] = nd, (x, iid)
                        heapq.heappush(heap, (nd, v))
            sp[u] = (dist, prev)
        memo: dict[frozenset, tuple[float, tuple]] = {}

        def match(rest: frozenset):
            if not rest:
                return 0.0, ()
            if rest not in memo:
                u = min(rest)
                memo[rest] = min(((sp[u][0][v] + match(rest - {u, v})[0], ((u, v),) + match(rest - {u, v})[1])
                                  for v in rest if v != u), key=lambda t: t[0])
            return memo[rest]

        def hop(a, b):
            return 0.0 if a is None or b is None else math.dist(a, b)

        def reach(pool):
            # the same reach as the pairing's: a start within the trim
            # distance, or no farther than the nearest start
            if cursor is None or not pool:
                return pool
            near = [i for i in pool if i in prefer and math.dist(nodes[i], cursor) <= prefer_within_mm]
            pool = near or pool
            d0 = min(math.dist(cursor, nodes[i]) for i in pool)
            return [i for i in pool if math.dist(cursor, nodes[i]) <= max(prefer_within_mm, d0 + 1e-9)]
        options = []        # (mm, start, end or None for a closed walk)
        for a in reach(odd):
            for b in odd:
                if b != a and b not in dead_ends:
                    options.append((hop(cursor, nodes[a]) + hop(nodes[b], exit_to)
                                    + match(frozenset(odd) - {a, b})[0], a, b))
        # a closed walk ends where it starts: never at a dead end (it would
        # leave the point along its first visit, an underpath, and come back
        # into it with the satin)
        whole = match(frozenset(odd))[0]
        for a in reach([i for i in cnodes if i not in dead_ends]):
            options.append((whole + hop(cursor, nodes[a]) + hop(nodes[a], exit_to), a, None))
        _mm, start, end = min(options, key=lambda o: (o[0], o[1], -1 if o[2] is None else o[2]))
        rest = frozenset(odd) - ({start, end} if end is not None else set())
        for u, v in match(rest)[1]:
            x = v
            while x != u:
                p, iid = sp[u][1][x]
                si, a, b = inst[iid]
                add_inst(si, a, b)
                x = p
        return walk_from(start, cnodes)

    def walk_from(start, cnodes):
        used: set[int] = set()
        ptr = {i: 0 for i in cnodes}
        stack, edge_stack, circuit = [start], [], []
        while stack:
            v = stack[-1]
            while ptr[v] < len(adj[v]) and adj[v][ptr[v]][0] in used:
                ptr[v] += 1
            if ptr[v] < len(adj[v]):
                iid, to = adj[v][ptr[v]]
                ptr[v] += 1
                used.add(iid)
                edge_stack.append((inst[iid][0], v, to))
                stack.append(to)
            else:
                stack.pop()
                if edge_stack:
                    circuit.append(edge_stack.pop())
        circuit.reverse()
        return circuit

    # Components in the order the needle meets them: each next component is
    # the one with a node nearest where the last walk ended, entered there.
    out = []
    cursor = start_near
    left = list(comps)
    while left:
        if cursor is None:
            pick = left[0]
        else:
            pick = min(left, key=lambda c: min(math.dist(nodes[i], cursor) for i in c))
        left.remove(pick)
        circuit = trail(pick, cursor, end_near if not left else None)
        if circuit:
            out.append(circuit)
            cursor = nodes[circuit[-1][2]]
    return out


# --------------------------------------------------------------- the engine

# `inside_stagger` (`cfg.lettering_columns_inside_stagger`, 2026-10-23): the
# inside of a pivot -- an L fold's corner, an S's curl -- the professional's
# way, in place of `_short_stitch_guard`'s alternate pull-back. Read off his
# hat DSTs (Fremont, Drone, MFab, Proseal, Becker; one reader on both files,
# `tools/inside_stagger.py`): his full-length inner ends step ~0.3 mm along
# the inner edge (median 0.28-0.32 per pair; under 0.1 mm in 2-7% of
# steps, 2-5 same-hole re-entries per band), and a third or more of the
# crosses (0.28-0.40) are shortened by ~20% of their length (0.19-0.23 of the cross:
# 0.29 mm on Fremont's 1.4 mm strokes, 0.57 on Becker's wider ones). The
# guard shortens every other crowded cross by 35% (capped 0.6 mm) and leaves
# the full ones in one hole: 28-56% of long steps under 0.1 mm, 16-79
# same-hole re-entries per band. Layout, judged in the preview; candidates.
STAGGER_SHORT_FRAC = 0.20      # a short stitch's pull, as a share of its own cross
STAGGER_SHORT_GAPS = (1, 2)    # full-length crosses between short ones, in turn: two in five
STAGGER_PILE_MM = 0.1          # two rail ends this close are one needle hole (the reader's)
STAGGER_WALK_MM = 0.30         # a pile's full-length ends are spaced this far along the rail's course
STAGGER_REACH = 2              # ... reaching at most this many stations into each leg for the room


def _inside_stagger(rail_a: list, rail_b: list) -> list[tuple]:
    """`inside_stagger`: (pa, pb) per station, each rail read on its own.
    CROWDED: a penetration whose step from the one before it on its rail
    (as the rail put them) is under `SATIN_SHORT_STITCH_AT_MM`. PILE: a
    stretch of crowded steps holding one under `STAGGER_PILE_MM` -- the
    inside corner of an L fold, every fold cross starting at one point, the
    pull's push spreading them in clumps. A pile's full-length penetrations
    are spaced evenly along the rail's own course through it, from the
    penetration before the stretch to the one after it (up to
    `STAGGER_REACH` stations into either leg, for `STAGGER_WALK_MM` each):
    the inner ends walk the corner instead of re-entering one hole. SHORT:
    a crowded penetration with `STAGGER_SHORT_GAPS` full-length crosses
    before it on its rail (one, then two, in turn) is pulled
    `STAGGER_SHORT_FRAC` of its cross toward the far rail, never under
    `SATIN_MIN_CROSS_MM` -- a share of the cross, so a wide column's short
    stitch is deeper (Becker's 0.57 mm against Fremont's 0.29). A curl's
    crowded stretch with no pile keeps its ends where the rail put them,
    short stitches apart."""
    n = min(len(rail_a), len(rail_b))
    out = [list(rail_a[:n]), list(rail_b[:n])]
    shorts = []
    for side in (0, 1):
        rail, sewn = (rail_a, out[0]) if side == 0 else (rail_b, out[1])
        step = [math.dist(rail[i], rail[i - 1]) if i else math.inf for i in range(n)]
        short = [False] * n
        gaps = 0                                    # short stitches so far: picks the next gap
        since = STAGGER_SHORT_GAPS[0]               # full-length crosses since the last short one
        for i in range(n):
            if (step[i] < machine.SATIN_SHORT_STITCH_AT_MM
                    and since >= STAGGER_SHORT_GAPS[gaps % len(STAGGER_SHORT_GAPS)]):
                short[i], since, gaps = True, 0, gaps + 1
            else:
                since += 1
        i, floor = 1, 0                             # no window reaches back past `floor`
        while i < n:
            if step[i] >= machine.SATIN_SHORT_STITCH_AT_MM:
                i += 1
                continue
            # stations i..j: each within a crowded step of SOME end already
            # in the stretch -- a fold's clumps sit a crowded step apart and
            # hop back and forth, so a step from the one before breaks them up
            j = i
            while j + 1 < n and any(math.dist(rail[j + 1], rail[k]) < machine.SATIN_SHORT_STITCH_AT_MM
                                    for k in range(i - 1, j + 1)):
                j += 1
            if min(step[i:j + 1]) < STAGGER_PILE_MM:
                # the course from the penetration before the stretch to the
                # one after, through the rail's own ends in order but only
                # those that go ON along the way (a W's V hops between clumps
                # and back, MFab; a pushed pile sticks out past the corner
                # and back, Fremont -- 2026-10-23), widened a station each way
                # into the legs until it holds `STAGGER_WALK_MM` per end --
                # at most `STAGGER_REACH` stations: further, the legs' own
                # crosses would lean to make room
                lo, hi, reach = max(floor, i - 1), min(n - 1, j + 1), 0
                while True:
                    course = [rail[lo]]
                    ux, uy = rail[hi][0] - rail[lo][0], rail[hi][1] - rail[lo][1]
                    ul = math.hypot(ux, uy) or 1.0
                    along = [((q[0] - rail[lo][0]) * ux + (q[1] - rail[lo][1]) * uy) / ul for q in rail]
                    last = 0.0
                    for k in range(lo + 1, hi):
                        if along[k] - last >= STAGGER_PILE_MM:
                            course.append(rail[k])
                            last = along[k]
                    course.append(rail[hi])
                    full = [k for k in range(lo + 1, hi) if not short[k]]
                    length = sum(math.dist(a, b) for a, b in zip(course, course[1:]))
                    if (length >= (len(full) + 1) * STAGGER_WALK_MM or reach >= STAGGER_REACH
                            or (lo == floor and hi == n - 1)):
                        break
                    lo, hi, reach = max(floor, lo - 1), min(n - 1, hi + 1), reach + 1
                if len(course) >= 2 and full:
                    path = LineString(course)
                    for m, k in enumerate(full):
                        t = path.interpolate((m + 1) / (len(full) + 1), normalized=True)
                        sewn[k] = (float(t.x), float(t.y))
                j, floor = max(j, hi - 1), hi
            i = j + 1
        shorts.append(short)
    # the short stitches last, each against the far rail as sewn so far, so
    # two crowded rails on one cross never pull it under the floor together
    for side in (0, 1):
        rail, sewn, far = (rail_a, out[0], out[1]) if side == 0 else (rail_b, out[1], out[0])
        for i in range(n):
            if shorts[side][i]:
                p, q = rail[i], far[i]
                cross = math.dist(p, q)
                f = STAGGER_SHORT_FRAC
                if cross > 1e-9:
                    f = min(f, max(0.0, 1.0 - 1.01 * machine.SATIN_MIN_CROSS_MM / cross))
                sewn[i] = (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
    return list(zip(out[0], out[1]))


def column_runs(columns: list[Column], poly: Polygon, shape_id: str, *,
                trim_at_mm: float,
                spacing_mm: float = machine.SATIN_SPACING_MM,
                split_above_mm: float | None = None,
                pull_mm: float = 0.0,
                pull_floor_mm: float = 0.0,
                underlay_style: str = "none",
                start_near: tuple[float, float] | None = None,
                min_cross_mm: float = machine.SATIN_MIN_CROSS_MM,
                end_near: tuple[float, float] | None = None,
                counter_clear_mm: float = 0.0,
                square_ends: bool = False,
                inside_connectors: bool = False,
                counter_poly: Polygon | None = None,
                thin_floor: bool = False,
                pull_of=None,
                short_columns: bool = False,
                inside_stagger: bool = False,
                apex_crosses: list | None = None,
                slot_guard: bool = False,
                ) -> tuple[list[StitchRun], dict]:
    """Columns of ONE letter -> runs in sew order, plus a report in the
    satin tier's contract (`empty`, `too_thin`, `jumps`), extended with the
    column census stage 7 copies into the plan's counters.
    `counter_clear_mm` > 0 (`cfg.small_print_floor`) holds every
    penetration that far off the letter's counters (`_clear_counters`).
    `counter_poly` (`cfg.open_cored_counters`, 2026-10-19): the polygon
    whose INTERIORS are the counters that hold reads -- `poly` itself when
    None, every hole of the letter, as the floor has always had it. Given
    (`counter_hold_polygon`), only the holes stage 3 kept as cored
    counters are held, and the letter's other holes sew as the lane sews
    them with the floor off. Reads the hold's interiors and nothing else:
    rails, end faces and the walk still read `poly`.
    `square_ends` (`cfg.lettering_columns_square_ends`) holds every
    penetration that starts on an end face on that face (`_hold_end_faces`).
    `inside_connectors` (`cfg.lettering_columns_inside_connectors`) keeps
    every needle-down connector within the rails' side reach of the letter
    (`poly_hop` in step 3).
    `thin_floor` (`cfg.lettering_columns_small_bold`): a column that would
    keep fewer than three crosses over `min_cross_mm` has its thin ones
    widened to it about their own middles (`_floor_crosses`) instead of
    dropped, so a serif or bar thinner than the floor sews at the floor
    rather than vanishing; a column that keeps three drops them as before.
    `pull_of` (`cfg.pull_comp_by_stroke`): a callable, column width (mm) ->
    the pull one rail gets; given, each column's rails are pushed by
    `pull_of(column_width(col))` in place of `pull_mm`, read on its own
    drawn stations. `pull_mm` stays the letter's pull everywhere else (the
    merge radius, the tuck, the link rule's and the tuck cover's buffers).
    `inside_stagger` (`cfg.lettering_columns_inside_stagger`): the inside of
    every pivot sewn by `_inside_stagger` instead of `_short_stitch_guard`.
    `apex_crosses` (`cfg.lettering_columns_apex_cut`, the cut's "apex"
    crosses; None or empty is the walk as it was): each merged tip is a
    dead end the walk enters from its cut and sews from its point
    (`_apex_tip_columns`, `_span_graph`'s `tips`, `_euler_trail`'s
    `dead_ends`), and its satin leaves on the rail nearer the next leg;
    every other leg of the letter ends on the rail whose hop lies least
    outside the satin still to come, and a hop keeps off a tip sewn before
    it. The cut and every station are the flag's: only the walk moves."""
    from .stage6_satin import (_JUNCTION_TUCK_MM, _comb_thresholds,   # same package,
                               _short_stitch_guard, _split_points)      # same rules

    report = {"too_thin": False, "jumps": 0, "empty": False,
              "columns": 0, "columns_unsewn": 0, "thin_crosses": 0, "stations": 0,
              "spans": 0, "underpath_mm": 0.0, "junctions": 0, "tucks": 0}
    above = split_above_mm if split_above_mm is not None else machine.SPLIT_SATIN_ABOVE_MM
    cpoly = counter_poly if counter_poly is not None else poly

    # 1. Each column's stations as the fabric will get them: pushed on the
    #    rails, crosses under the floor dropped.
    ready: list[Column] = []
    hold = end_face_hold(columns, poly) if square_ends else None
    for col in columns:
        col_pull = pull_mm if pull_of is None else pull_of(column_width(col))
        a_pts, b_pts = sewn_rails(col, poly, col_pull, pull_floor_mm, hold)
        if counter_clear_mm > 0:
            a_pts, b_pts = _clear_counters(a_pts, b_pts, cpoly, counter_clear_mm, min_cross_mm)
        # Short stitches on the inside of a bend (`satinplay.js` pullShort;
        # the engine's own guard): where a rail's penetrations bunch up
        # under SATIN_SHORT_STITCH_AT_MM -- the inner rail of an S's curl is
        # a single point every outer cross converges on -- every other cross
        # is pulled back toward the outer rail, so the inside stops re-entering
        # one needle hole. The pro's S: the outer rail dense, the inner rail
        # short-stitched (lettering-thickness-fremont-2026-10-06).
        guarded = (_inside_stagger(a_pts, b_pts) if inside_stagger    # the pro's inside
                   else _short_stitch_guard(a_pts, b_pts))
        if counter_clear_mm > 0:
            # Small print: no zigzag stitch over a counter
            # (`_counter_safe_pieces`); one column may sew as several.
            pieces, dropped = _counter_safe_pieces(guarded, cpoly, min_cross_mm,
                                                   counter_clear_mm)
            report["thin_crosses"] += dropped
            sewn_pieces = [p for p in pieces if len(p) >= 3]
            report["thin_crosses"] += sum(len(p) for p in pieces if len(p) < 3)
            if not sewn_pieces:
                report["columns_unsewn"] += 1
            for kept in sewn_pieces:
                ready.append(Column(stations=kept, piece=col.piece, kind=col.kind, axis=col.axis,
                                    width_mm=col.width_mm, rail_a=col.rail_a, rail_b=col.rail_b))
            continue
        kept = [(a, b) for a, b in guarded if math.dist(a, b) >= min_cross_mm]
        if thin_floor and len(kept) < 3 and len(guarded) >= 3:
            # a whole piece under the floor (a serif, a bar): sewn at the
            # floor rather than lost; a column that keeps three crosses
            # drops its thin ones as before -- widened, a fan's converging
            # tip crosses each other
            kept = _floor_crosses(guarded, min_cross_mm)
            report["floored"] = report.get("floored", 0) + 1
        report["thin_crosses"] += len(col.stations) - len(kept)
        if len(kept) < 3:
            report["columns_unsewn"] += 1
            continue
        ready.append(Column(stations=kept, piece=col.piece, kind=col.kind, axis=col.axis,
                            width_mm=col.width_mm, rail_a=col.rail_a, rail_b=col.rail_b))
    if counter_clear_mm > 0 and ready:
        # Small print: a bar between two counters that no column sews (the
        # slashed 0's slash, once its crosses stop running over the
        # counters beside it) gets a column of its own (`_bar_columns`).
        bars = _bar_columns(cpoly, ready, spacing_mm)
        if bars:
            report["bars"] = len(bars)
            ready.extend(bars)
    if not ready:
        report["empty"] = True
        return [], report
    report["columns"] = len(ready)
    report["stations"] = sum(len(c.stations) for c in ready)

    # 2. The span graph and the walk.
    W = sorted(c.width_mm for c in ready)[len(ready) // 2]
    merge_r = _MERGE_WIDTHS * W + _MERGE_PAD_MM + pull_mm
    tip_tol = spacing_mm + _APEX_END_WIDTHS * W
    tips = _apex_tip_columns(ready, apex_crosses, tip_tol, merge_r) if apex_crosses else {}
    nodes, spans, junctions = _span_graph(
        ready, merge_r,
        # `cfg.lettering_columns_corner_fold`: a folded letter's nodes must
        # be joined through the letter (`_span_graph`); off, the radius alone.
        # `slot_guard` (`cfg.lettering_columns_slot_guard`, `letter_walk`):
        # every letter's, against the letter barely grown, so no slot closes
        poly.buffer(SLOT_GUARD_GROW_MM) if slot_guard
        else poly.buffer(0.1 + pull_mm) if any(c.kind == "folded" for c in ready) else None,
        **({"tips": tips} if tips else {}))
    report["junctions"] = len(junctions)
    # The free end of a butting column (its other end, when nothing else
    # meets it there) is where its component's walk should start -- when
    # the stroke has room for the whole tuck. Where the half-stroke cap
    # already truncates it (gaulke's 0.96 mm strokes at 0.3 pull) the
    # reorder bought a sliver and cost six entry trims over 39 letters.
    tuck_mm = min(_JUNCTION_TUCK_MM + pull_mm, _TUCK_MAX_WIDTHS * W)
    roomy = _TUCK_MAX_WIDTHS * W >= _JUNCTION_TUCK_MM + pull_mm
    touch: dict[int, int] = {}
    for sp in spans:
        touch[sp["na"]] = touch.get(sp["na"], 0) + 1
        touch[sp["nb"]] = touch.get(sp["nb"], 0) + 1
    prefer: set[int] = set()
    for j in junctions if roomy else ():
        if ready[j["through"]].kind == "folded":
            # `cfg.lettering_columns_corner_fold`: an arm butting a FOLDED
            # column (an E's middle arm on the stem of its top-arm / stem /
            # bottom-arm column) does not start the walk: the trail would
            # then have to double one of the folded column's long spans to
            # reach its far tip (Drone's E: 3.7 -> 18.8 mm of travel and a
            # trim). Started at a tip, the walk runs out under the arm and
            # sews it back onto the stem: a plain butt, one arm of travel.
            continue
        n = len(ready[j["ci"]].stations)
        free_idx = n - 1 if j["end"] == 0 else 0
        for sp in spans:
            if sp["ci"] != j["ci"]:
                continue
            for key, idx in (("na", sp["i0"]), ("nb", sp["i1"])):
                if idx == free_idx and touch.get(sp[key], 0) == 1:
                    prefer.add(sp[key])
    # `apex_crosses`: a merged tip's point may start a trail, never end one
    dead = frozenset(sp[key] for sp in spans if sp["ci"] in tips
                     for key, idx in (("na", sp["i0"]), ("nb", sp["i1"]))
                     if idx == (len(ready[sp["ci"]].stations) - 1 if tips[sp["ci"]]["cut"] == 0 else 0))
    span_mm = [LineString(_mids(ready[sp["ci"]].stations[sp["i0"]:sp["i1"] + 1])).length
               if sp["i1"] > sp["i0"] else 0.0 for sp in spans] if dead else ()
    components = _euler_trail(nodes, spans, start_near, frozenset(prefer), trim_at_mm,
                              end_near=end_near,
                              **({"dead_ends": dead, "span_mm": span_mm} if dead else {}))

    # 3. Emit: the last visit of a span sews satin, earlier visits run under it.
    #    (`poly_link` is the sew-or-jump rule's polygon, see step 4; the
    #    connector below asks it the same question one leg early.)
    poly_link = poly.buffer(0.1 + pull_mm)
    if counter_clear_mm > 0 and cpoly.interiors:
        # Small print: the buffer closes every counter narrower than twice
        # (0.1 + pull) -- at 0.3 mm pull, every counter under 0.8 mm -- and
        # a hop the link rule then sews runs needle-down across the bare
        # counter (the B's and the 8's diagonals, `tools/small_print.py`
        # renders at 4 mm). A counter is not inside the letter.
        _counters = unary_union([Polygon(r).buffer(-stitches.SAME_POINT_MM)
                                 for r in cpoly.interiors])
        if not _counters.is_empty:
            poly_link = poly_link.difference(_counters)
    # `inside_connectors`: a needle-down connector (the hop below, the
    # walk-in, the link rule) must stay on the letter -- within its outline
    # grown by the rails' side reach, or on the ground its own satin covers
    # (a thin cross's rail reaches further: it is inset by a quarter of
    # itself) -- not inside the link rule's 0.1 + pull, which closes a narrow
    # notch: the Fremont 81 mm M sewed 2.5 mm from its right foot to its
    # vertex, 1.65 mm of it over the bare notch (Kent's M->O "loop"). A
    # routed path walks only graph edges that stay on it and keeps its
    # corners; a hop with no such route jumps (a trim past `trim_at_mm`).
    if inside_connectors:
        ground = [Polygon([a for a, _ in c.stations] + [b for _, b in c.stations][::-1]).buffer(0)
                  for c in ready if len(c.stations) >= 2]
        poly_hop = unary_union([poly.buffer(max(0.0, pull_mm - RAIL_REACH_INSET_MM) + _FACE_EPS_MM),
                                *ground])
        if counter_clear_mm > 0 and cpoly.interiors and not _counters.is_empty:
            poly_hop = poly_hop.difference(_counters)
    else:
        poly_hop = poly_link
    hop_strict = inside_connectors or counter_clear_mm > 0
    all_legs: list[dict] = []       # ci, sat, i0, i1 in traversal order (i0 may be > i1)
    for circuit in components:
        seen: set[int] = set()
        is_satin = [False] * len(circuit)
        for k in range(len(circuit) - 1, -1, -1):
            si = circuit[k][0]
            if si not in seen:
                seen.add(si)
                is_satin[k] = True
        # collapse contiguous visits of one column, same type, same direction
        legs: list[dict] = []
        for k, (si, frm, _to) in enumerate(circuit):
            s = spans[si]
            fwd = frm == s["na"] or s["na"] == s["nb"]      # a ring's self-loop walks forward
            i0, i1 = (s["i0"], s["i1"]) if fwd else (s["i1"], s["i0"])
            prev = legs[-1] if legs else None
            if prev and prev["ci"] == s["ci"] and prev["sat"] == is_satin[k] and prev["i1"] == i0:
                prev["i1"] = i1
            else:
                legs.append(dict(ci=s["ci"], sat=is_satin[k], i0=i0, i1=i1, head=[], tail=[]))
        all_legs.extend(legs)
    # The junction tuck: a butting column that sews BEFORE the column it
    # butts runs on under it, so the later stroke covers the seam. Decided on
    # the satin order the walk produced -- sewn after, it stays square.
    # `square_ends`: a tuck station must lie within the letter grown by the
    # rails' own side reach, not the link rule's looser 0.1 + pull -- at the
    # M's V the left diagonal's tuck ran on past the vertex and 0.5 mm out
    # under the baseline (Fremont 81 mm, circle 6).
    tuck_cover = poly.buffer(max(0.0, pull_mm - RAIL_REACH_INSET_MM) + _FACE_EPS_MM) if square_ends else None
    # `apex_crosses`: the merged tips' ground, which no tuck crosses to
    # reach the column it butts (`_tuck_stations`' `avoid`)
    tip_ground = unary_union([ready[t].piece for t in tips]).buffer(-_FACE_EPS_MM) if tips else None
    for j in junctions:
        n = len(ready[j["ci"]].stations)
        end_idx = 0 if j["end"] == 0 else n - 1
        mine = [k for k, lg in enumerate(all_legs) if lg["sat"] and lg["ci"] == j["ci"]
                and min(lg["i0"], lg["i1"]) <= end_idx <= max(lg["i0"], lg["i1"])]
        theirs = [k for k, lg in enumerate(all_legs) if lg["sat"] and lg["ci"] == j["through"]
                  and min(lg["i0"], lg["i1"]) <= j["k"] <= max(lg["i0"], lg["i1"])]
        if not mine or not theirs:
            continue
        # Sewn before the stroke it meets (before the later of that stroke's
        # halves when the junction splits it): go under it by the tuck.
        # Sewn after: a plain butt, up to the cut line and no further.
        before = mine[0] < max(theirs)
        ext = _tuck_stations(ready[j["ci"]], j["end"], ready[j["through"]].piece,
                             tuck_mm if before else 0.0, _TUCK_MAX_WIDTHS * W,
                             spacing_mm, tuck_cover if square_ends else poly_link,
                             **({"avoid": tip_ground} if tips else {}))
        if not ext:
            continue
        if before:
            report["tucks"] += 1
        leg = all_legs[mine[0]]
        at_start = (leg["i0"] <= leg["i1"]) == (j["end"] == 0)      # the end in traversal terms
        if at_start:
            leg["head"] = ext[::-1]
        else:
            leg["tail"] = ext
    runs: list[StitchRun] = []
    run_leg: list[int] = []         # the leg each run belongs to, for step 4
    sewn: dict[int, Polygon] = {}   # leg -> the ground its satin covers
    tip_exit = None                 # `apex_crosses`: set by a tip's satin leg, read by the next
    # `apex_crosses`: every column on a cut tip piece, handled or not, and
    # the ground of those already sewn (a connector keeps off it)
    if apex_crosses:
        from .outline_cut import _apex_tip_piece
        tip_cols = {ci for ci, c in enumerate(ready) if _apex_tip_piece(c.piece, apex_crosses) is not None}
    else:
        tip_cols = set()
    tips_sewn: list[Polygon] = []
    # ... each satin leg's ground on its stations (its tuck included), and
    # every stitch's reach: half a 0.4 mm thread past them
    leg_ground: list = []
    laid = None
    if apex_crosses:
        for x in all_legs:
            if not x["sat"]:
                leg_ground.append(None)
                continue
            lo_, hi_ = min(x["i0"], x["i1"]), max(x["i0"], x["i1"])
            st_ = ready[x["ci"]].stations[lo_:hi_ + 1]
            st_ = x["head"] + (st_[::-1] if x["i1"] < x["i0"] else st_) + x["tail"]
            leg_ground.append(Polygon([a for a, _ in st_] + [b for _, b in st_][::-1]).buffer(0)
                              if len(st_) >= 2 else None)
        laid = unary_union([g_ for g_ in leg_ground if g_ is not None]).buffer(_APEX_EXIT_MM)
    for li, leg in enumerate(all_legs):
        col = ready[leg["ci"]]
        lo, hi = min(leg["i0"], leg["i1"]), max(leg["i0"], leg["i1"])
        sts = col.stations[lo:hi + 1]
        if leg["i1"] < leg["i0"]:
            sts = sts[::-1]
        # `apex_crosses`: the needle leaving a tip's satin, which ended at its
        # cut: (the unit step out past the cut, its length); else None
        leaving = (tip_exit if tip_exit is not None and runs and run_leg
                   and run_leg[-1] == li - 1 and runs[-1].kind == stitches.SATIN else None)
        tip_exit = None
        if leg["sat"]:
            sts = leg["head"] + sts + leg["tail"]
            if leg["ci"] in tips and li + 1 < len(all_legs):
                # `apex_crosses`: a tip's last cross spans both strokes, and the
                # zigzag ends on its b rail; the hop to the next leg ran along
                # that cross on top of the tip just sewn (PROSEAL's A, MFab's N:
                # 2.5 mm a tip). Begun on the other rail, it ends beside the leg.
                nxt = all_legs[li + 1]
                nst = (nxt["head"] or ready[nxt["ci"]].stations[nxt["i0"]:nxt["i0"] + 1])[0]
                goal = list(nst) if nxt["sat"] else _mids([nst])
                if (min(math.dist(sts[-1][0], g) for g in goal)
                        < min(math.dist(sts[-1][1], g) for g in goal)):
                    sts = [(b, a) for a, b in sts]
            if leg["ci"] in tips and len(sts) >= 2:
                # sewn from the point up, the needle stops on the last cross,
                # up to a pitch short of the cut: it steps out square to the
                # cut, past it, before it goes anywhere -- along that cross it
                # lay on the tip's own edge (MARINE's M at 95.7 mm: 2.1 mm)
                m1, m0 = _mids(sts[-2:])
                line = tips[leg["ci"]]["line"]
                gap = line.distance(Point(m0))
                L = math.dist(m0, m1)
                if gap < line.distance(Point(_mids(sts[:1])[0])) and L > 1e-9:
                    tip_exit = (((m0[0] - m1[0]) / L, (m0[1] - m1[1]) / L), gap + _APEX_EXIT_MM,
                                leg["ci"])
            elif leaving is not None and (underlay_style == "none"
                                          or _centre_underlay(_mids(sts), short_columns) is None):
                # ... and the leg after it begins on the rail beside that step
                # (a leg with a centre walk is reached at its centre: its
                # rails are the next leg's to choose, below -- PROSEAL's A
                # ran its left leg out to the far rail, 4.7 mm from the bar)
                (dx, dy), step, _t = leaving
                e = runs[-1].points[-1]
                e = (e[0] + dx * step, e[1] + dy * step)
                if math.dist(e, sts[0][1]) < math.dist(e, sts[0][0]):
                    sts = [(b, a) for a, b in sts]
            elif apex_crosses and li + 1 < len(all_legs):
                # ... and every other leg of a cut letter ends on the rail
                # whose hop to the next leg's centre lies least on fabric no
                # satin of the letter reaches, then least outside the satin
                # still to come, then the shorter: the cut re-pieces the
                # whole letter, and the rail a leg ended on, by its stations'
                # count, put the hop on the far edge (MFab's 4: its top bar,
                # 1.7 mm down the corner on bare fabric, 0.5 OFF). Read on
                # the legs' stations, not their pieces: a piece fills the
                # notch between two strokes that no stitch reaches (PROSEAL's
                # small N: the shorter hop crossed it, 0.2 mm bare).
                # A hop neither rail can make straight is routed (step 4),
                # which this cannot read: the stations' rail stands.
                nxt = all_legs[li + 1]
                nst = (nxt["head"] or ready[nxt["ci"]].stations[nxt["i0"]:nxt["i0"] + 1])[0]
                g = _mids([nst])[0]
                later = unary_union([g_ for g_ in leg_ground[li + 1:] if g_ is not None])

                def bare(e):
                    if math.dist(e, g) < machine.TINY_STITCH_MM:      # no hop is sewn
                        return (False, 0.0, 0.0, 0.0)
                    hop = LineString([e, g])
                    return (not poly_hop.covers(hop), round(hop.length - hop.intersection(laid).length, 2),
                            round(hop.length - hop.intersection(later).length, 2), hop.length)
                ba, bb = bare(sts[-1][0]), bare(sts[-1][1])
                if not (ba[0] and bb[0]) and ba < bb:
                    sts = [(b, a) for a, b in sts]
        mids = _mids(sts)
        # The walk is continuous along CENTRELINES; a zigzag ends on a
        # rail. From that rail point to the next leg's first penetration
        # the straight hop can cut the outer corner of a mitre and read
        # as a jump, so the hop goes through the junction: a connector
        # run to this leg's first centre point, inside the letter.
        if runs and runs[-1].shape_id == shape_id:
            tail = runs[-1].points[-1]
            hop = math.dist(tail, mids[0])
            out = None
            if leaving is not None:
                # `apex_crosses`: out of the tip square to its cut, then to
                # the leg's first stitch -- straight to it when no centre
                # walk begins the leg, else to its centre. Where the straight
                # way skims the tip (the leg begins on the cut: MARINE's M at
                # 95.7 mm, 0.2 mm of it), it runs past the cut and turns in
                # square to the leg.
                (dx, dy), step, t = leaving
                goal = (sts[0][0] if leg["sat"] and (underlay_style == "none"
                                                      or _centre_underlay(mids, short_columns) is None)
                        else mids[0])
                s = (tail[0] + dx * step, tail[1] + dy * step)
                ground = ready[t].piece.buffer(_FACE_EPS_MM)
                for path in sorted(([tail, s, goal], [tail, s, (goal[0] + dx * step, goal[1] + dy * step), goal]),
                                   key=lambda q: (round(LineString(q[1:]).intersection(ground).length, 2),
                                                  LineString(q).length)):
                    if (LineString(path).length <= max(trim_at_mm, _CONNECTOR_WIDTHS * W) + 2 * step
                            and poly_hop.covers(LineString(path))):
                        out = path
                        break
            elif (tips_sewn and machine.TINY_STITCH_MM <= hop <= max(trim_at_mm, _CONNECTOR_WIDTHS * W)
                    and poly_hop.covers(LineString([tail, mids[0]]))):
                # `apex_crosses`: a hop that runs on a tip sewn before it --
                # along its cut, from the stroke beside it (MFab's IN: 0.12 mm
                # at the N's foot) -- steps off it square to the hop and
                # back, onto ground still to be sewn
                ground = unary_union(tips_sewn)
                goal = mids[0]

                def skim(q):
                    return round(LineString(q).intersection(ground).length, 2)
                if skim([tail, goal]) > 0:
                    ux, uy = (goal[0] - tail[0]) / hop, (goal[1] - tail[1]) / hop
                    best = None
                    for sgn in (1, -1):
                        for d in (_APEX_EXIT_MM, 2 * _APEX_EXIT_MM):
                            ox, oy = -uy * sgn * d, ux * sgn * d
                            s = (tail[0] + ox, tail[1] + oy)
                            for q in ([tail, s, goal], [tail, s, (goal[0] + ox, goal[1] + oy), goal]):
                                if (LineString(q).length <= max(trim_at_mm, _CONNECTOR_WIDTHS * W) + 2 * d
                                        and poly_hop.covers(LineString(q))):
                                    key = (skim(q), LineString(q).length)
                                    if key[0] < skim([tail, goal]) and (best is None or key < best[0]):
                                        best = (key, q)
                    if best is not None:
                        out = best[1]
            if out is not None:
                runs.append(StitchRun(points=_walk_corners(out, _UNDERPATH_STEP_MM),
                                      kind=stitches.TRAVEL, shape_id=shape_id))
            elif (machine.TINY_STITCH_MM <= hop <= max(trim_at_mm, _CONNECTOR_WIDTHS * W)
                    and poly_hop.covers(LineString([tail, mids[0]]))):
                runs.append(StitchRun(points=_walk_points([tail, mids[0]], _UNDERPATH_STEP_MM),
                                      kind=stitches.TRAVEL, shape_id=shape_id))
            # else a real gap: the link rule in step 4 decides
        if leg["sat"]:
            report["spans"] += 1
            if underlay_style != "none":
                ul = _centre_underlay(mids, short_columns)
                if (ul is not None and counter_clear_mm > 0
                        and not poly_link.covers(LineString(ul))):
                    ul = None       # small print: a split piece's centre over a counter
                if ul is not None:
                    runs.append(StitchRun(points=ul, kind=stitches.UNDERLAY, shape_id=shape_id))
            pts = _satin_points(sts, above, _comb_thresholds, _split_points)
            if len(pts) >= 4:
                runs.append(StitchRun(points=pts, kind=stitches.SATIN, shape_id=shape_id))
                run_leg.extend([li] * (len(runs) - len(run_leg)))
                sewn[li] = Polygon([a for a, _ in sts] + [b for _, b in sts][::-1]).buffer(0)
                if leg["ci"] in tip_cols:
                    # its thread's reach (half a 0.4 mm thread) on its own
                    # piece, past its last stitch: a hop leaving the tip
                    # starts on it, whichever way it goes
                    tips_sewn.append(sewn[li].buffer(_APEX_EXIT_MM).intersection(
                        col.piece.buffer(_FACE_EPS_MM)).difference(
                        Point(pts[-1]).buffer(2 * _APEX_EXIT_MM + _FACE_EPS_MM)))
                continue
        # an underpath (an earlier visit), or a satin span too short to
        # sew: the needle still has to reach the far end, under later thread.
        # A one-station leg has no far end: Becker at 100 mm left chest with
        # `sew_enclosed_white` ON (2026-10-24) raised GEOS's "point array must
        # contain 0 or >1 elements" here (`tests/test_satin_per_stroke_flag.py`'s
        # Becker digitize is the regression); the link rule in step 4 moves on.
        path = _walk_points(mids, _UNDERPATH_STEP_MM) if len(mids) >= 2 else []
        if (len(path) >= 2 and counter_clear_mm > 0
                and not poly_link.covers(LineString(path))):
            # Small print: an underpath whose centreline crosses a counter
            # (a split column's pieces) is not walked; the link rule in
            # step 4, which keeps out of counters, takes the needle on.
            path = []
        if len(path) >= 2:
            runs.append(StitchRun(points=path, kind=stitches.TRAVEL, shape_id=shape_id))
            report["underpath_mm"] += LineString(path).length
        run_leg.extend([li] * (len(runs) - len(run_leg)))
    if not any(r.kind == stitches.SATIN for r in runs):
        report["empty"] = True
        return [], report
    # 3b. Walk in from the letter's near edge (the satin tier's entry: its
    #     first run is a travel from where the needle arrives). A walk
    #     starts at a column END, which sits mid-stroke, and the hop from
    #     the previous letter straight to it crossed the 3 mm trim line on
    #     Fremont where the gap between letters is under a millimetre (the
    #     first stitch landed 2.5-3.7 mm in, against 1.1-1.5 under the
    #     satin tier). The needle now lands just inside the near edge and
    #     runs to the start under the thread sewn after it -- only where
    #     that run stays inside the letter.
    def walk(path):
        # Small print: a routed path keeps its corners -- resampled by arc
        # length, the synthetic 0's 0.42 mm hop round a counter's corner
        # came out as one straight stitch across it.
        if hop_strict:
            return _walk_corners(path, _UNDERPATH_STEP_MM)
        return _walk_points(path, _UNDERPATH_STEP_MM)

    if start_near is not None and runs:
        f = runs[0].points[0]
        inner = poly.buffer(-min(_ENTRY_INSET_MM, 0.25 * W))
        if not inner.is_empty:
            e = nearest_points(inner, Point(start_near))[0].coords[0]
            if (math.dist(start_near, e) + machine.TINY_STITCH_MM < math.dist(start_near, f)
                    and math.dist(e, f) >= machine.TINY_STITCH_MM):
                # Straight where it stays inside; otherwise along the
                # centrelines (the start is round a bend from the near edge
                # -- 3 of Fremont's 4 lane-only entry trims, 2026-10-08).
                path = ([e, f] if poly_hop.covers(LineString([e, f]))
                        else _inside_path(ready, nodes, spans, e, f,
                                          _CONNECTOR_WIDTHS * W, poly_hop,
                                          strict=hop_strict))
                if path is not None:
                    runs.insert(0, StitchRun(points=walk(path),
                                             kind=stitches.TRAVEL, shape_id=shape_id))
                    run_leg.insert(0, -1)
                    report["entry_walk_mm"] = LineString(path).length
    # 4. Link consecutive runs: the satin tier's own sew-or-jump rule, verbatim
    #    (`satin_shape`'s tail). Under rail comp the rails sit a pull outside
    #    the artwork and a hop that ends on one is still inside the column.
    #    A hop the rule would cut is sewn after all when it can run inside
    #    the letter -- straight, or along the centrelines -- with no more of
    #    it left on top than a hop the rule already sews (`allow`): the rest
    #    lies on ground a later satin leg buries. Drone's five inside-letter
    #    trims were hops of 3.1-4.0 mm against an `allow` of 3.0-3.4, four of
    #    them wholly inside the letter (2026-10-08).
    allow = max(trim_at_mm, _CONNECTOR_WIDTHS * W)
    linked: list[StitchRun] = runs[:1]
    for k in range(1, len(runs)):
        prev_run, cur = runs[k - 1], runs[k]
        a, b = prev_run.points[-1], cur.points[0]
        d = math.dist(a, b)
        tiny = d < machine.TINY_STITCH_MM and (counter_clear_mm <= 0 or d < 1e-9
                                               or poly_hop.covers(LineString([a, b])))
        if tiny or (d <= allow and poly_hop.covers(LineString([a, b]))):
            linked.append(cur)      # needle-down inside the letter, under thread sewn later
            continue
        path = ([a, b] if poly_hop.covers(LineString([a, b]))
                else _inside_path(ready, nodes, spans, a, b, _CONNECTOR_WIDTHS * W, poly_hop,
                                  strict=hop_strict))
        later = [g for li, g in sewn.items() if li >= run_leg[k]]
        if path is not None and later:
            line = LineString(path)
            if line.difference(unary_union(later)).length <= allow:
                linked.append(StitchRun(points=walk(path),
                                        kind=stitches.TRAVEL, shape_id=shape_id))
                linked.append(cur)
                report["hops_buried"] = report.get("hops_buried", 0) + 1
                report["underpath_mm"] += line.length
                continue
        cur.jump = True
        cur.trim = d > trim_at_mm
        report["jumps"] += 1
        linked.append(cur)
    return linked, report


def _floor_crosses(stations, min_cross_mm: float):
    """`cfg.lettering_columns_small_bold`: every cross under `min_cross_mm`
    widened to it about its own middle, along its own direction -- or, for a
    cross with none (both rails on one point, a fan's tip), along the
    nearest cross that has one. A grown 4 mm letter's serifs and bars run
    0.3-0.5 mm; dropped under the floor, P's whole bowl and E's arms went
    unsewn on the Fremont tagline at the pro's pull."""
    dirs = []
    for a, b in stations:
        d = math.dist(a, b)
        dirs.append(((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d > 1e-9 else None)
    have = [i for i, u in enumerate(dirs) if u is not None]
    out = []
    for i, (a, b) in enumerate(stations):
        if math.dist(a, b) >= min_cross_mm:
            out.append((a, b))
            continue
        u = dirs[i]
        if u is None:
            if not have:
                out.append((a, b))
                continue
            u = dirs[min(have, key=lambda k: abs(k - i))]
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        h = min_cross_mm / 2
        out.append(((m[0] - u[0] * h, m[1] - u[1] * h), (m[0] + u[0] * h, m[1] + u[1] * h)))
    return out


def _recorded_counters(cut_poly: Polygon, letter: Polygon) -> Polygon:
    """`cfg.small_print_floor`: the cut's polygon holding the letter's own
    counters (the recorded ones, `small_print_counters`) as holes, not the
    cut's copy of them -- that copy can be a few hundredths smaller, and
    the synthetic R's entry walk at a 5 mm cap ran 0.14 mm into the
    recorded counter while clear of the cut's (`tools/small_print.py`)."""
    if not letter.interiors:
        return cut_poly
    both = cut_poly.difference(unary_union([Polygon(r) for r in letter.interiors]))
    return both if both.geom_type == "Polygon" and not both.is_empty else cut_poly


def counter_hold_polygon(poly: Polygon, counters) -> Polygon:
    """`cfg.open_cored_counters` (2026-10-19): `poly`'s exterior with ONLY
    the holes that are cored counters as its interiors -- the polygon the
    counter holds (`_clear_counters`, `_counter_safe_pieces`, `_bar_columns`,
    the link rule's cut) read their counters from, so a shape's other holes
    sew exactly as the lane sews them with the floor off. Each counter
    (a polygon, the counter region stage 3 kept) names the interior of
    `poly` it covers -- the shape's own traced ring, not the counter's,
    for `_recorded_counters`' reason -- and a counter that covers none of
    `poly`'s interiors names nothing. Only the interiors are read by every
    consumer; the exterior is `poly`'s."""
    rings = []
    for ring in poly.interiors:
        hole = Polygon(ring)
        if hole.is_empty:
            continue
        pt = hole.representative_point()
        if any(c.covers(pt) for c in counters):
            rings.append(ring.coords)
    return Polygon(poly.exterior.coords, rings)


def lettering_columns_shape(poly: Polygon, shape_id: str, *, trim_at_mm: float,
                            spacing_mm: float = machine.SATIN_SPACING_MM,
                            split_above_mm: float | None = None,
                            pull_mm: float = 0.0, pull_floor_mm: float = 0.0,
                            underlay_style: str = "none",
                            start_near: tuple[float, float] | None = None,
                            end_near: tuple[float, float] | None = None,
                            counter_clear_mm: float = 0.0,
                            fold_cuts: bool = False,
                            square_ends: bool = False,
                            short_columns: bool = False,
                            inside_connectors: bool = False,
                            counter_holes: list | None = None,
                            rail_axis: bool = False,
                            small_bold: bool = False,
                            pull_by_stroke: bool = False,
                            corner_fold: bool = False,
                            text_lean_deg: float | None = None,
                            inside_stagger: bool = False,
                            slot_guard: bool = False,
                            ) -> tuple[list[StitchRun], dict]:
    """One lettering shape (its ARTWORK polygon) -> runs, report. The
    stage 7 entry point behind `cfg.lettering_columns`: cut, then construct.
    `counter_clear_mm`: see `column_runs` (`cfg.small_print_floor`).
    `counter_holes` (`cfg.open_cored_counters`, 2026-10-19): the cored
    counters of this letter (polygons); with `counter_clear_mm` > 0 the
    floor's two holds -- no cross over a counter, every penetration half a
    laid width off it -- are applied to THOSE holes only
    (`counter_hold_polygon`), and the cut's polygon is handed over as it
    is, the letter's other holes sewn as the lane sews them with the floor
    off. None, the floor's own reading: every hole of the letter.
    `fold_cuts`: `cfg.lettering_columns_fold_cuts` (`outline_cut._fold_refine`).
    `rail_axis`: `cfg.lettering_columns_rail_axis` (`outline_cut.straight_axis`).
    `small_bold`: `cfg.lettering_columns_small_bold`, stage 7 passes it for
    a letter under `machine.SATIN_UNDERLAY_MIN_EXTENT_MM` only -- the pull a
    `SMALL_BOLD_PULL_FRAC` share of the stroke width when that is less, and
    the cross floor widening instead of dropping (`_floor_crosses`).
    `pull_by_stroke`: `cfg.pull_comp_by_stroke` (2026-10-22) -- `pull_mm`
    is the preset's fixed pull, and each column's rails get
    `pull_for_width(its own width, pull_mm)` instead, the letter's pull
    (merge, tuck, link buffers) read the same way off the letter's mean
    stroke; neither ever above `pull_mm`, nor, under `small_bold`, above its
    share of the stroke. Read at digitize time on the drawn stroke, so a
    resize keeps its pull (ruling 12, `column-width-on-resize-2026-10-01`).
    `corner_fold`: `cfg.lettering_columns_corner_fold` (2026-10-23) -- one
    column folded round each L corner of the letter
    (`outline_cut._fold_corners`); off, the cut's columns as they are.
    `text_lean_deg` (`cfg.lettering_columns_text_lean`, 2026-10-23): the
    word's house cross angle (degrees, `satin_angle_deg`); given, every
    straight column the house can span within the lean cap is re-stationed
    with its crosses along the house (`column_lean.lean_columns`), the way
    the pro sews a diagonal with the stems' cross. None is the lane as it
    was, station for station.
    `inside_stagger`: `cfg.lettering_columns_inside_stagger` (2026-10-23) --
    the inside of every pivot walked and short-stitched the pro's way
    (`_inside_stagger`); off, `_short_stitch_guard` as before.
    `slot_guard`: `cfg.lettering_columns_slot_guard` (2026-10-27) -- the
    chosen cut's walk also tried with ends joined only through the letter,
    kept where it is cheaper (`letter_walk.pick`); off, today's walk."""
    from .outline_cut import letter_columns, stroke_width

    walk = column_runs
    if slot_guard:
        from .letter_walk import pick

        def walk(cols, cpoly, sid, **kw):
            return pick(column_runs, cols, cpoly, sid, **kw)

    if small_bold:
        pull_mm = min(pull_mm, SMALL_BOLD_PULL_FRAC * stroke_width(poly))
    pull_of = None
    if pull_by_stroke:
        fabric_pull, cap = pull_mm, pull_mm      # the preset's, or small_bold's share

        def pull_of(w: float) -> float:
            return min(cap, pull_for_width(w, fabric_pull))
        pull_mm = pull_of(stroke_width(poly))

    # One station per `spacing_mm` along the rail, both ends of each sewn:
    # the engine's own meaning of satin spacing (a needle every `spacing_mm`
    # on EACH rail). The spike stationed at half that with both ends down
    # and sewed every letter twice as dense.
    lc_kw = {**({"fold_cuts": True} if fold_cuts else {}),
             # `cfg.lettering_columns_square_ends`: a slanted end face is mitred
             **({"mitre_ends": True} if square_ends else {}),
             # `cfg.lettering_columns_rail_axis`: a short italic bar runs along its rails
             **({"rail_axis": True} if rail_axis else {}),
             **({"small_bold": True} if small_bold else {}),
             # `cfg.lettering_columns_corner_fold`: one column round an L corner
             **({"corner_fold": True} if corner_fold else {})}
    cored = bool(counter_holes) and counter_clear_mm > 0        # none named: the floor's reading
    run_kw = dict(trim_at_mm=trim_at_mm,
                  spacing_mm=spacing_mm, split_above_mm=split_above_mm,
                  pull_mm=pull_mm, pull_floor_mm=pull_floor_mm,
                  underlay_style=underlay_style, start_near=start_near,
                  end_near=end_near, counter_clear_mm=counter_clear_mm,
                  **({"pull_of": pull_of} if pull_of is not None else {}),
                  **({"square_ends": True} if square_ends else {}),
                  **({"inside_connectors": True} if inside_connectors else {}),
                  **({"thin_floor": True} if small_bold else {}),
                  # `cfg.satin_underlay_short_columns`: a walk under any span that holds a stitch
                  **({"short_columns": True} if short_columns else {}),
                  # `cfg.lettering_columns_inside_stagger`: the pro's inside at a pivot
                  **({"inside_stagger": True} if inside_stagger else {}),
                  **({"counter_poly": counter_hold_polygon(poly, counter_holes)} if cored else {}))

    def recorded(cpoly):
        # the floor: the letter's own rings for every hole; the cored
        # counters alone ride in `counter_poly`, the cut's polygon untouched
        return _recorded_counters(cpoly, poly) if counter_clear_mm > 0 and not cored else cpoly
    if fold_cuts:
        # `fold_cuts`' sewn judge: a fold-look candidate is sewn exactly as
        # this letter will be, and read for folds and knots
        # (`outline_cut._fold_refine`, `outline_cut.sewn_knots`)
        from .outline_cut import sewn_knots

        def judge(cols, cpoly):
            # today's walk: the pick (`slot_guard`) chooses how the chosen cut
            # is walked, never which cut is chosen
            return sewn_knots(column_runs(leaned(cols), recorded(cpoly), shape_id, **run_kw)[0])
        lc_kw["judge"] = judge

    def leaned(cols):
        # `text_lean_deg`: the convention's crosses on every straight column
        # the house can span; None hands the cut's columns back untouched
        if text_lean_deg is None:
            return cols
        from .column_lean import lean_columns
        return lean_columns(cols, text_lean_deg, spacing_mm)

    def sew(plain: bool = False, **extra):
        lk, rk = lc_kw, run_kw
        if plain:           # the lane's own construction, small_bold's pull kept
            lk = {k: v for k, v in lc_kw.items() if k != "small_bold"}
            rk = {k: v for k, v in run_kw.items() if k != "thin_floor"}
        cut = letter_columns(poly, pitch_mm=spacing_mm, **lk, **extra)
        # `cfg.lettering_columns_apex_cut`: the merged tips' crosses, for the
        # walk (`column_runs`); a cut with none, the call is today's
        apex_x = [(c[0], c[1]) for c in cut.cuts if c[2] == "apex"]
        if apex_x:
            rk = {**rk, "apex_crosses": apex_x}
        runs, report = walk(leaned(cut.columns), recorded(cut.poly), shape_id, **rk)
        report["cuts"] = len(cut.cuts)
        report["columns_unsewn"] += len(cut.unsewn)
        return runs, report
    runs, report = sew()
    if small_bold:
        from .outline_cut import SIMPLIFY_MM
        cover = satin_cover(runs, poly)
        if cover < SMALL_BOLD_COVER_MIN:
            runs2, report2 = sew(simplify_mm=SIMPLIFY_MM)
            cover2 = satin_cover(runs2, poly)
            if cover2 > cover:
                runs, report, cover = runs2, report2, cover2
                report["resimplified"] = 1
            if cover < SMALL_BOLD_COVER_MIN:
                runs3, report3 = sew(plain=True)
                if satin_cover(runs3, poly) >= cover + SMALL_BOLD_PLAIN_GAIN:
                    runs, report = runs3, report3
                    report["small_bold_plain"] = 1
    return runs, report


def satin_cover(runs: list[StitchRun], poly: Polygon, half_mm: float = 0.2) -> float:
    """Share of `poly` the satin of `runs` covers, each needle-to-needle
    stitch widened by `half_mm` (half the 40 wt laid thread) each side."""
    segs = [LineString([a, b]) for r in runs if r.kind == stitches.SATIN
            for a, b in zip(r.points, r.points[1:]) if math.dist(a, b) > 1e-9]
    if not segs or poly.area <= 0:
        return 0.0
    return unary_union([q.buffer(half_mm) for q in segs]).intersection(poly).area / poly.area
