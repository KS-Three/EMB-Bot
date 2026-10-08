"""Per-shape stitch width — the sewn satin column, measured, shared across
a word, and adjustable one shape at a time (Kent's ask, 2026-09-29).

WHY THIS EXISTS. Small shapes, letters and words are where the auto path
looks worst, and until now nothing about the column a shape sews at was
visible or adjustable: the Studio's only "width" was the design's, and the
column a satin shape sews is simply whatever the artwork measures, raster
noise and JPEG blur included. Three things fix that here, in this order:

1. MEASURE. Every column-shaped region gets `meta["stitch_width_measured_mm"]`
   — twice the mean skeleton half-width of its ARTWORK polygon (the same
   `textcluster._stats_of_polygon` read the text doors take, memoized on the
   polygon so it is free where those passes already asked). The review
   payload echoes it as a SEWN width (artwork + twice the fabric's pull,
   which stage 5 or the rails add on every satin shape), because the sewn
   width is the one the customer sees on cloth.

2. GROUP. A detected text cluster (`textcluster.detect_text_clusters`, both
   doors) is the word; its members name it in `meta["stitch_width_group"]`
   — per WEIGHT MODE, not per cluster (`split_weight_modes`): a line holding
   a bold word and a light one is two groups, and a letter with no
   weight-mate shares with nobody. A mode of two or more records its median
   as `meta["stitch_width_auto_mm"]` on every member. The Studio's "whole
   word" scope writes one override to every member of the group — that is
   how a word gets one width, and it is always on.

   EVENING OUT a word automatically — offsetting a member more than
   `AUTO_TOLERANCE` off its mode's median to it — is OPT-IN
   (`cfg.stitch_width_auto`, default False, the Studio's "Even out lettering
   widths" box), and the reason is a measurement, not caution: on Gaulke
   Roofing's line the 35 letters of ONE cluster measure a smooth chain from
   0.77 to 1.33 mm with no step anywhere, because an I, an M and an O of one
   font genuinely measure differently at the skeleton (junctions read wide,
   caps narrow). A median there is nobody's width — the first cut moved all
   21 letters outside the tolerance to 0.95 mm, thinning the bold word and
   fattening the light one — and the weight split cannot cut a chain. What
   auto CAN fix is an outlier: on the drone render two letters of a 0.65 mm
   word trace at 0.79 and 0.82 mm and come back to the word. Off, nothing
   moves and every fixture is byte-identical; on, the panel says which
   shapes moved (`source == "group"`) so the reading can be checked.

3. FLOOR and OVERRIDE. `cfg.lettering_min_column_mm` (Kent's 1.0 mm pick,
   default None — ROADMAP gate 1, a sew-out number) keeps exactly the
   2026-09-09 meaning on its own; with `stitch_width_auto` on it also raises
   a small shape's or a lettering member's target to that sewn width.
   `shape_overrides[sid].stitch_width_mm` (contract v1.8) sets a sewn width
   outright, wider or narrower, on any shape, always — the correction for
   when auto reads it wrong.

HOW A WIDTH IS APPLIED. `offset_polygon` grows or shrinks the region's own
polygon by half the difference — a plain Minkowski offset, never a redraw —
so a letter keeps its counters, its corners and its taper. Two guards, both
geometric, both bisected to the largest change that passes rather than
refused outright:

- a HOLE that the growth would close (its area under `RUN_MIN_AREA_MM2`) is
  held open at its original size, the rule stage 5's own pull growth already
  applies (`resolve_overlaps`' "held" holes);
- a GAP between strokes that the growth would bridge — the arms of an E, the
  legs of an M — is read off a morphological closing of the shell with
  mitre joins (the mitre keeps corners exactly, so the closing gains area
  only where two edges meet; holes are the hold's job, so the shell alone is
  closed): a gain over `GAP_CLOSE_FRACTION` of the shape's area refuses that
  step. Narrowing has the mirror guard: an OPENING that loses more than the
  same fraction has erased a stroke thinner than the step (an E's arms
  going before its stem), and is refused the same way. Neither is a
  glyph-height gate — a plain bar passes at any width — so the floor stays
  exactly as gated in `config.py`.

A shape whose polygon this pass changed carries `meta["stitch_width_sized_mm"]`
and is treated downstream exactly as the regularizer's widened lettering is
(`stage5_overlap.widened_lettering`, now `column_sized`): exempt from the
sub-floor run routing, classified and sewn on its compensated polygon, its
growth kept over the ground beneath it, and its pull on the polygon rather
than the rails. Nothing tagged means every stage is byte-identical.

WHAT THIS DOES NOT DO. It does not choose a physical number. The floor is
Kent's and stays None until he flips it; the tolerance is the regularizer's;
the guards are the engine's own sewability floors. "Best looking" here
means: one width per word, the word's own weight, and every counter and gap
still open — the three things a person can check by looking.
"""
from __future__ import annotations

import math
from statistics import median

from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from . import machine
from .regions import Region

# --- meta keys ---------------------------------------------------------------
MEASURED_KEY = "stitch_width_measured_mm"    # artwork width, 2 x mean skeleton half-width
AUTO_KEY = "stitch_width_auto_mm"            # artwork width the group wants (median)
GROUP_KEY = "stitch_width_group"             # the text cluster this width is shared with
OVERRIDE_KEY = "stitch_width_override_mm"    # SEWN width from the wire (contract v1.8)
SIZED_KEY = "stitch_width_sized_mm"          # artwork width the polygon was offset TO
DELTA_KEY = "stitch_width_delta_mm"          # radius change actually applied (signed)
SOURCE_KEY = "stitch_width_source"           # "shape" | "group" | "floor" | "override"
SKIP_KEY = "stitch_width_skip_reason"        # why a wanted change was not made
LIMITED_KEY = "stitch_width_limited"         # True when a guard clamped the change
PULL_KEY = "stitch_width_pull_mm"            # the fabric pull the sewn readings add back

# A member within this fraction of its group's half-width is left alone —
# `textcluster._REGULARIZE_SKIP_TOLERANCE`, the same "already consistent"
# reading, restated here so the two passes agree on what a deviation is.
AUTO_TOLERANCE = 0.15
# A change under this radius is noise, not a request: one pixel at the
# raster's own floor. Overrides and floors move past it; auto does not.
MIN_DELTA_MM = 0.01
# A change past this fraction of the radius is not what the request asked
# for, and is reported as `LIMITED_KEY`.
_LIMIT_REPORT_FRACTION = 0.02
# The closing-gain fraction past which a growth step is read as bridging a
# gap between strokes (see the module docstring).
GAP_CLOSE_FRACTION = 0.03
GAP_CLOSE_MIN_MM2 = 0.01
# Bisection depth for the guards: 6 halvings of the requested radius reach
# ~1.5% of it, well under MIN_DELTA_MM for any request this pass makes.
_BISECT_STEPS = 6
# Shapes wider than this many satin ceilings (2*area/perimeter) are never
# columns and are not measured — the cheap gate that keeps a photo's eighty
# fill regions from each paying a rasterize + medial axis.
_MEASURE_RIBBON_CEILINGS = 2.0
# The vocabulary the wire accepts (`digitizer_service.app`, `regions.
# apply_shape_edits`): a sewn width the machine can hold as a column.
OVERRIDE_MIN_MM = machine.SATIN_MIN_CROSS_MM
OVERRIDE_MAX_MM = machine.SATIN_WIDE_COLUMN_MAX_MM


# --- unit helpers -------------------------------------------------------------

def sewn_width_mm(art_mm: float, pull_mm: float) -> float:
    """Artwork width -> the column sewn on cloth: pull lands on both rails."""
    return art_mm + 2.0 * max(0.0, pull_mm)


def art_width_mm(sewn_mm: float, pull_mm: float) -> float:
    """The inverse: the artwork width that sews `sewn_mm` once compensated."""
    return max(0.0, sewn_mm - 2.0 * max(0.0, pull_mm))


def column_sized(region: Region) -> bool:
    """True for a shape whose polygon this pass offset to a width."""
    return region.meta.get(SIZED_KEY) is not None


def is_small_shape(poly: Polygon) -> bool:
    """`machine.SATIN_UNDERLAY_MIN_EXTENT_MM` is the engine's own "small
    lettering" extent (stage 7 sews such shapes bare); the floor reaches the
    same population."""
    x0, y0, x1, y1 = poly.bounds
    return max(x1 - x0, y1 - y0) < machine.SATIN_UNDERLAY_MIN_EXTENT_MM


# --- measurement ----------------------------------------------------------------

def measure_width_mm(poly: Polygon) -> float | None:
    """Twice the mean skeleton half-width, or None where the polygon is too
    degenerate to field. Memoized by `textcluster._stats_of_polygon`."""
    from .textcluster import _stats_of_polygon  # late: textcluster imports regions
    stats = _stats_of_polygon(poly)
    if stats is None or stats.mean_mm <= 0:
        return None
    return 2.0 * stats.mean_mm


def _column_shaped(region: Region, satin_max: float, word_key: str = "text_cluster_id") -> bool:
    if region.meta.get(word_key) or is_small_shape(region.polygon):
        return True
    poly = region.polygon
    if poly.length <= 0:
        return False
    return 2.0 * poly.area / poly.length <= _MEASURE_RIBBON_CEILINGS * satin_max


def measure_stitch_widths(regions: list[Region], *, satin_max: float,
                          words: bool = False) -> None:
    """Generation-time pass (after the text doors and the regularizer, whose
    polygons this reads): record each column-shaped region's measured width
    and, for every text cluster, the shared width its members will take.
    Metadata only — geometry moves in `apply_stitch_widths`, at finish time,
    where the override and the fabric are known.

    `words` (`cfg.lettering_words`) keys a word by the one tagger's
    `word_id` instead of the text cluster's `text_cluster_id`."""
    key = "word_id" if words else "text_cluster_id"
    groups: dict[str, list[Region]] = {}
    for r in regions:
        for k in (MEASURED_KEY, AUTO_KEY, GROUP_KEY):
            r.meta.pop(k, None)
        if not _column_shaped(r, satin_max, key):
            continue
        w = measure_width_mm(r.polygon)
        if w is None:
            continue
        r.meta[MEASURED_KEY] = round(w, 4)
        gid = r.meta.get(key)
        if gid:
            r.meta[GROUP_KEY] = gid
            groups.setdefault(gid, []).append(r)
    _share_group_widths(groups)


def _share_group_widths(groups: dict[str, list[Region]]) -> None:
    for gid, members in groups.items():
        modes = split_weight_modes(members)
        for k, mode in enumerate(modes):
            # One cluster can hold two words set at two weights — Gaulke
            # Roofing's line measures 0.78 mm on eight letters and 1.2 mm on
            # thirteen — and a single median would pull both words to a
            # width neither has. A weight mode is the association; the
            # cluster is only the line. A lone member shares with no one.
            sub_id = gid if len(modes) == 1 else f"{gid}:{k}"
            for m in mode:
                m.meta[GROUP_KEY] = sub_id
            if len(mode) < 2:
                continue
            shared = float(median(m.meta[MEASURED_KEY] for m in mode))
            for m in mode:
                m.meta[AUTO_KEY] = round(shared, 4)


# Two letters can only share a width if each sits within AUTO_TOLERANCE of
# one median, so the widest spread one weight can hold is this ratio; a
# larger step between neighbours in width order is a second weight. Derived
# from the tolerance, not chosen.
WEIGHT_SPLIT_RATIO = (1.0 + AUTO_TOLERANCE) / (1.0 - AUTO_TOLERANCE)


def split_weight_modes(members: list[Region]) -> list[list[Region]]:
    """Members of one text cluster, partitioned by stroke weight: sorted by
    measured width, and any run whose widest is more than
    `WEIGHT_SPLIT_RATIO` times its narrowest is cut at its largest step,
    recursively, until every mode fits inside the ratio. Order within a mode
    is the sort order. A smooth chain (Gaulke, 0.77 → 1.33 with no step) is
    cut where the steps are largest, which is a partition, not a detection —
    see the module docstring for why the auto offset is opt-in."""
    ordered = sorted(members, key=lambda m: float(m.meta[MEASURED_KEY]))

    def cut(run: list[Region]) -> list[list[Region]]:
        if len(run) < 2:
            return [run]
        lo = float(run[0].meta[MEASURED_KEY])
        hi = float(run[-1].meta[MEASURED_KEY])
        if lo <= 0 or hi <= lo * WEIGHT_SPLIT_RATIO:
            return [run]
        widths = [float(m.meta[MEASURED_KEY]) for m in run]
        at = max(range(1, len(run)), key=lambda i: widths[i] / max(widths[i - 1], 1e-9))
        return cut(run[:at]) + cut(run[at:])

    return cut(ordered)


# --- geometry -----------------------------------------------------------------

def _one_polygon(geom) -> Polygon | None:
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    if len(parts) != 1:
        return None
    return parts[0]


def _sewable(poly: Polygon) -> bool:
    return (poly.is_valid and not poly.is_empty
            and poly.area >= machine.RUN_MIN_AREA_MM2
            and poly.exterior.length >= machine.RUN_MIN_LOOP_MM)


def _hold_holes(grown: Polygon, original: Polygon) -> Polygon | None:
    """Stage 5's rule on this pass's growth: a hole the growth would close
    is held open at its original size; every other hole keeps its shrunk
    outline."""
    if not original.interiors:
        return grown
    kept = [list(h.coords) for h in grown.interiors
            if Polygon(h).area >= machine.RUN_MIN_AREA_MM2]
    covered = [Polygon(h) for h in kept]
    for ring in original.interiors:
        hole = Polygon(ring)
        if hole.area < machine.RUN_MIN_AREA_MM2:
            continue
        pt = hole.representative_point()
        if any(c.contains(pt) for c in covered):
            continue
        kept.append(list(ring.coords))
    try:
        held = Polygon(grown.exterior.coords, kept)
    except Exception:
        return None
    if not held.is_valid:
        held = held.buffer(0)
        held = _one_polygon(held)
    return held


def _bridges_gap(original: Polygon, delta: float) -> bool:
    """Does growing by `delta` fuse two strokes? A mitre closing of the SHELL
    keeps every corner exactly, so its gain over the shell is gap area alone
    (a counter closing is `_hold_holes`' case, not this one)."""
    shell = Polygon(original.exterior.coords)
    try:
        closed = shell.buffer(delta, join_style=2).buffer(-delta, join_style=2)
    except Exception:
        return True
    gain = closed.area - shell.area
    return gain > max(GAP_CLOSE_MIN_MM2, GAP_CLOSE_FRACTION * shell.area)


def _erases_stroke(original: Polygon, delta: float) -> bool:
    """Does shrinking by `-delta` delete a stroke thinner than the step? A
    mitre opening loses area only where a stroke is narrower than twice the
    radius — the arms of an E before its stem — so a loss past the gap
    fraction means the offset would sew an I for an E."""
    try:
        opened = original.buffer(delta, join_style=2).buffer(-delta, join_style=2)
    except Exception:
        return True
    loss = original.area - opened.area
    return loss > max(GAP_CLOSE_MIN_MM2, GAP_CLOSE_FRACTION * original.area)


def _try_offset(original: Polygon, delta: float) -> Polygon | None:
    if delta > 0:
        if _bridges_gap(original, delta):
            return None
        grown = _one_polygon(original.buffer(delta))
        if grown is None:
            return None
        grown = _hold_holes(grown, original)
    else:
        if _erases_stroke(original, delta):
            return None
        grown = _one_polygon(original.buffer(delta))
    if grown is None or not _sewable(grown):
        return None
    return orient(grown)


def offset_polygon(poly: Polygon, delta_mm: float) -> tuple[Polygon | None, float, str | None]:
    """-> (polygon, radius actually applied, skip reason). The full offset
    when the guards pass; otherwise the largest fraction of it that does,
    found by bisection; None with a reason when even a hair of it fails."""
    if abs(delta_mm) < MIN_DELTA_MM:
        return poly, 0.0, "no_change"
    full = _try_offset(poly, delta_mm)
    if full is not None:
        return full, delta_mm, None
    lo, hi = 0.0, delta_mm          # lo passes (the shape itself), hi fails
    best: Polygon | None = None
    best_d = 0.0
    for _ in range(_BISECT_STEPS):
        mid = 0.5 * (lo + hi)
        cand = _try_offset(poly, mid)
        if cand is None:
            hi = mid
        else:
            lo, best, best_d = mid, cand, mid
    if best is None or abs(best_d) < MIN_DELTA_MM:
        return None, 0.0, "gap_or_hole_would_close" if delta_mm > 0 else "would_split_or_vanish"
    return best, best_d, None


# --- application ----------------------------------------------------------------

def _wanted_art_width(region: Region, *, pull_mm: float,
                      floor_sewn_mm: float | None,
                      auto: bool) -> tuple[float | None, str | None, bool]:
    """-> (target artwork width, source, deliberate). `deliberate` is True
    for an override or a floor — a change that moves past the auto
    tolerance — and False for the group median, which does not. A source
    with no target is a skip reason."""
    ov = region.meta.get(OVERRIDE_KEY)
    if ov is not None:
        if float(ov) <= 2.0 * pull_mm:
            # The fabric's pull alone sews wider than this: no artwork width
            # reaches it, so say so rather than shrink the shape to nothing.
            return None, "below_fabric_pull", True
        return art_width_mm(float(ov), pull_mm), "override", True
    tier = str(region.meta.get("tier", "auto")).lower()
    if tier not in ("auto", "satin"):
        return None, None, False
    if region.meta.get("boundary_override") is not None:
        return None, "hand_edited_outline", False
    measured = region.meta.get(MEASURED_KEY)
    if measured is None:
        return None, None, False
    target, source, deliberate = float(measured), "shape", False
    if not auto:
        return target, source, deliberate
    auto_mm = region.meta.get(AUTO_KEY)
    if auto_mm is not None:
        target, source = float(auto_mm), "group"
    if floor_sewn_mm and (region.meta.get(GROUP_KEY) or is_small_shape(region.polygon)):
        floor_art = art_width_mm(float(floor_sewn_mm), pull_mm)
        if floor_art > target:
            target, source, deliberate = floor_art, "floor", True
    return target, source, deliberate


_SKIP_SOURCES = ("hand_edited_outline", "below_fabric_pull")


def apply_stitch_widths(regions: list[Region], *, pull_mm: float,
                        floor_sewn_mm: float | None = None,
                        auto: bool = False,
                        satin_max: float = machine.SATIN_MAX_WIDTH_MM,
                        words: bool = False) -> int:
    """Finish-time pass (after `apply_shape_edits`, whose override this
    reads): offset every region whose wanted width differs from its measured
    one. `auto` (`cfg.stitch_width_auto`) admits the group median and the
    floor; off, only an override moves a shape. Returns how many polygons
    moved. Every decision is written to meta whether or not the polygon
    changed, so the review payload can say what was measured, what was
    wanted and why nothing happened."""
    moved = 0
    pull_mm = max(0.0, float(pull_mm))
    for r in regions:
        for k in (SIZED_KEY, DELTA_KEY, SOURCE_KEY, SKIP_KEY, LIMITED_KEY):
            r.meta.pop(k, None)
        r.meta[PULL_KEY] = pull_mm
        if r.meta.get("stitched") is False:
            continue
        measured = r.meta.get(MEASURED_KEY)
        if measured is None and _column_shaped(
                r, satin_max, "word_id" if words else "text_cluster_id"):
            # A merged or split shape, minted after the measurement pass:
            # measured late so the panel can offer it the same control.
            w = measure_width_mm(r.polygon)
            if w is not None:
                measured = r.meta[MEASURED_KEY] = round(w, 4)
        if measured is None or measured <= 0:
            continue
        target, source, deliberate = _wanted_art_width(
            r, pull_mm=pull_mm, floor_sewn_mm=floor_sewn_mm, auto=auto)
        if source is not None and source not in _SKIP_SOURCES:
            r.meta[SOURCE_KEY] = source
        if target is None:
            if source in _SKIP_SOURCES:
                r.meta[SKIP_KEY] = source
                r.meta[SOURCE_KEY] = "shape"
            continue
        delta = 0.5 * (target - float(measured))
        if not deliberate and abs(delta) <= AUTO_TOLERANCE * 0.5 * float(measured):
            continue
        if abs(delta) < MIN_DELTA_MM:
            continue
        new_poly, applied, reason = offset_polygon(r.polygon, delta)
        if new_poly is None or reason is not None:
            r.meta[SKIP_KEY] = reason or "offset_failed"
            continue
        r.polygon = new_poly
        r.area_mm2 = new_poly.area
        r.meta[SIZED_KEY] = round(float(measured) + 2.0 * applied, 4)
        r.meta[DELTA_KEY] = round(applied, 4)
        if abs(applied - delta) > max(MIN_DELTA_MM, _LIMIT_REPORT_FRACTION * abs(delta)):
            r.meta[LIMITED_KEY] = True
        moved += 1
    return moved


def review_block(region: Region) -> dict:
    """The per-shape `stitch_width` entry of the review payload, in SEWN mm
    (artwork plus the pull on both rails, `PULL_KEY` as `apply_stitch_widths`
    stamped it). Every field None when the shape was never measured — a fill
    region, or one too degenerate to field."""
    measured = region.meta.get(MEASURED_KEY)
    pull_mm = float(region.meta.get(PULL_KEY, 0.0))
    if measured is None:
        return {"art_mm": None, "measured_mm": None, "auto_mm": None, "sewn_mm": None,
                "override_mm": None, "source": None, "group": None,
                "limited": False, "skip_reason": None}
    sized = region.meta.get(SIZED_KEY)
    auto = region.meta.get(AUTO_KEY)
    ov = region.meta.get(OVERRIDE_KEY)
    return {
        # The artwork's own stroke, no pull: what a shape the plan sews as a
        # RUN (a sub-floor bean on its outline, no compensation) actually
        # is. The sewn figures below hold for a satin column; the client
        # knows the tier from the plan and picks which to show.
        "art_mm": round(float(sized if sized is not None else measured), 3),
        "measured_mm": round(sewn_width_mm(float(measured), pull_mm), 3),
        "auto_mm": round(sewn_width_mm(float(auto if auto is not None else measured), pull_mm), 3),
        "sewn_mm": round(sewn_width_mm(float(sized if sized is not None else measured), pull_mm), 3),
        "override_mm": None if ov is None else round(float(ov), 3),
        "source": region.meta.get(SOURCE_KEY),
        "group": region.meta.get(GROUP_KEY),
        "limited": bool(region.meta.get(LIMITED_KEY, False)),
        "skip_reason": region.meta.get(SKIP_KEY),
    }


def validate_override_mm(value) -> float:
    """The one range check both the service (a 400) and `apply_shape_edits`
    (a ValueError) apply: a finite number the machine can sew as a column."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("stitch_width_mm must be a number")
    v = float(value)
    if not math.isfinite(v) or not OVERRIDE_MIN_MM <= v <= OVERRIDE_MAX_MM:
        raise ValueError(
            f"stitch_width_mm must be between {OVERRIDE_MIN_MM} and "
            f"{OVERRIDE_MAX_MM} mm (got {value!r})")
    return v
