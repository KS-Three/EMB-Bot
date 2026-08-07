"""Stage 6 — the appliqué tier, and the `steps[]` container it is built on.

Source of every number: `docs/specialty-techniques-2026-08-01.md` §0 and §2,
with source tiers carried intact ([V] vendor, [S] supplier, [P] production,
[D] derived). The constants live in `machine.py`; this module is the geometry
and the sequencing.

--------------------------------------------------------------------------
The prerequisite: one color stop = one human action
--------------------------------------------------------------------------

A specialty design is not artwork, it is **a program with operator interrupts**.
The container that makes that expressible is an ordered list of steps, where a
step boundary is a machine function PLUS an operator-action string.

Three consequences that are code, not doctrine (§0):

1. **DST has no STOP opcode.** Color change and stop are the same record,
   `0xC3`. Wilcom is explicit that a frame-out "must be specified as a Stop
   function or Color Change respectively" — Stop for multi-head, Color Change
   for single-head [V]. We are single-head, so every inter-layer break is a
   color change, and appliqué layers are frequently all one thread.

2. **The writer must never merge adjacent same-color blocks.** Measured, not
   assumed (`tests/test_applique.py::test_same_thread_stop_survives_dst` and
   `::test_empty_step_cannot_swallow_its_stop`): two same-thread blocks write
   one literal `00 00 C3` record, three with an empty middle write two adjacent
   `00 00 C3` records, and both survive decode. `export.py` needed no change.
   The real hazard is upstream and is handled here — stage 7 drops a block that
   produces no runs, which would take the stop with it, so an empty step is
   refused and warned (`APPLIQUE_STEP_EMPTY`) rather than silently vanishing.

3. **Step granularity is a design decision.** Merging two objects to save a
   stop destroys an operator instruction, so the nearest-neighbour resequencer
   is forbidden from crossing a boundary. `nn_group_key` is that guard: stage 7
   partitions its candidate pool by it, and two regions in different steps can
   never be reordered into each other or welded into one block.

--------------------------------------------------------------------------
The offset chain
--------------------------------------------------------------------------

**B** = the digitized boundary = the intended finished location of the raw
fabric edge. Signed normal `s`: `s < 0` inward onto the appliqué, `s > 0`
outward onto the ground garment.

Vendors **chain** the offsets rather than referencing them all to B, and §2.2
warns that the published numbers will not transfer unless we match that:

    placement  s = 0.00                       relative to the outline B   [V]
    cutting    s = 0.00                       coincident with B           [V]
    tackdown   s = placement + (-1.00)        relative to the GUIDE RUN   [V]
    cover      rails straddle B               relative to the TACKDOWN    [V]

The cover needs care, because the spec places it twice and the two placements
are not the same construction. **§2.4's worked default is wrong and we do not
implement it** — see `cover_rails` for the table, but the short version is that
splitting the whole width 65/35 about B (§2.4's `c_in = -1.95, c_out = +1.05`)
leaves **-0.60 mm** of headroom over the raw edge at loose trim discipline.
Negative headroom is §2.15's first failure mode — fabric peeking outside the
satin — turned from a risk into a certainty. §2.13's solver, which starts the
rails where the tolerance stack requires and distributes only the SURPLUS by
`inside_share`, holds +0.50 mm at every discipline and is the implementable
statement of the inequality §2.3 spends the section deriving. So §2.13 wins,
and §2.4's printed rails are treated as an illustrative simplification.

What survives from §2.4 unchanged is everything the width depends on: the
§2.3 validation table's `W_req` column (2.5 / 3.0 / 4.0 mm for tight / normal /
loose) falls out of `solve_cover_width` untouched, as do the two pre-cut rows
(2.5 mm hand-placed, 1.8 mm heat-tacked — the Stahls' Poly-Twill number).

`APPLIQUE_COVER_MARGINAL` still exists, because a caller can override the width
downward and the 5.0 mm ceiling can bite on a thick material at loose
discipline. It fires with the measured headroom whenever the cover reaches less
than `m_edge` past the furthest the raw edge can land.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polylabel, unary_union

from . import machine, stitches
from .config import PipelineConfig
from .machine import APPLIQUE_QUANTIZE_MM
from .stage6_border import _parts, _ring_arc_samples, _satin_loop, round_inward
from .stitches import StitchRun
from .warnings_codes import (APPLIQUE_COVER_MARGINAL,
                             APPLIQUE_COVER_WIDTH_CLAMPED,
                             APPLIQUE_CUTTING_LINE_SUPPRESSED,
                             APPLIQUE_FORCED_PRE_CUT,
                             APPLIQUE_NO_FABRIC_VISIBLE,
                             APPLIQUE_PIECES_OVERLAP,
                             APPLIQUE_PRECUT_TOO_NARROW,
                             APPLIQUE_STEP_EMPTY, warn)

TRIM_IN_PLACE = "trim_in_place"
PRE_CUT = "pre_cut"

# Machine functions a step boundary can be. On a single head there is exactly
# one that stops the machine mid-design, and it is the color change (§0.1).
COLOR_CHANGE = "color_change"
END = "end"

# Run kinds, so a debug render and a density audit can tell the four layers
# apart. They are `stitches.RUN` / `stitches.BORDER` techniques underneath;
# the kind records which LAYER a run is, which is what the operator cares about.
PLACEMENT = "applique_placement"
CUTTING = "applique_cutting"
TACKDOWN = "applique_tackdown"
COVER = "applique_cover"

# Hair-width tolerance for "inside the shape", matching stage 6 border's.
_SLACK_MM = 1e-3


def q(v: float) -> float:
    """Quantize an offset to the DST grid (0.1 mm) — §2.2's unit note.

    Half-away-from-zero, explicitly, because the two rounding modes Python
    hands you both get this wrong. `round()` is banker's: `round(-19.5)` is -20
    but `round(10.5)` is 10, so §2.4's own worked rails (-1.95 and +1.05, both
    exactly on the half-quantum) would round in opposite directions and the
    column would come out 0.1 mm narrow. And `v / 0.1` is not exact in binary —
    `1.95 / 0.1` is 19.499999999999996 — so the scaled value is rounded to 9
    decimals before the half is taken.

    Away-from-zero is also the right direction on the merits: it pushes each
    rail outward from B, and §2.15's fix for a gap at the inner edge is "move
    `c_in` inward".
    """
    scaled = round(v / APPLIQUE_QUANTIZE_MM, 9)
    n = math.floor(abs(scaled) + 0.5)
    return round(math.copysign(n, scaled) * APPLIQUE_QUANTIZE_MM, 6)


# --- The tolerance solver (§2.3, §2.13) ------------------------------------

def solve_cover_width(
    *,
    mode: str = TRIM_IN_PLACE,
    o_tack: float = machine.APPLIQUE_TACK_OFFSET_MM,
    trim_discipline: str = "normal",
    placement: str = "hand",
    material: str = "woven",
    m_bury: float = machine.APPLIQUE_MARGIN_BURY_MM,
    m_edge: float = machine.APPLIQUE_MARGIN_EDGE_MM,
) -> dict:
    """Cover width from the tolerance stack. -> dict of the whole derivation.

    Trim-in-place, §2.13 verbatim::

        c_out_req = o_tack + t_hi + m_edge
        c_in_req  = min(o_tack - m_bury, o_tack + t_lo - m_edge)
        W_req     = c_out_req - c_in_req

    At the "normal" defaults (o_tack -1.00, t_lo 0.30, t_hi 2.00, both margins
    0.50) this is `c_out_req = +1.50`, `c_in_req = -1.50`, **W_req = 3.00 mm** —
    the §2.3 validation table's own figure, which it cross-checks against
    "beginner safe zone 3.0-3.8" and Hatch's 3.00 baseline [P]. Tight gives
    2.50 and loose 4.00, matching the other two published rows.

    Pre-cut has no trim step, so the placement error is the whole budget and
    the requirement is symmetric — §2.3: `W_req = 2*(e + m_edge)`. Hand
    placement (e 0.75) gives 2.50 mm; heat-tacked (e 0.40) gives 1.80 mm, which
    is the Stahls' Poly-Twill row and the strongest confirmation in the spec.

    The `[2.5, 5.0]` clamp is §2.13's. Note it sits above Stahls' published
    2 mm, so on pre-cut twill the clamp binds rather than the material floor —
    deliberate conservatism, flagged here because it is the one place our
    output is knowingly wider than a supplier tech sheet.
    """
    t_lo, t_hi = machine.APPLIQUE_TRIM_CLEARANCE_MM[trim_discipline]
    w_floor = machine.APPLIQUE_COVER_FLOOR_BY_MATERIAL[material]

    if mode == PRE_CUT:
        eps = machine.APPLIQUE_PLACEMENT_ERROR_MM[placement]
        w_req = 2.0 * (eps + m_edge)
        c_out_req, c_in_req = w_req / 2.0, -w_req / 2.0
    else:
        eps = None
        c_out_req = o_tack + t_hi + m_edge
        c_in_req = min(o_tack - m_bury, o_tack + t_lo - m_edge)
        w_req = c_out_req - c_in_req

    width = min(machine.APPLIQUE_COVER_WIDTH_MAX_MM,
                max(machine.APPLIQUE_COVER_WIDTH_FLOOR_MM, w_req, w_floor))
    return {
        "width_mm": q(width),
        "w_req_mm": round(w_req, 4),
        "w_floor_mm": w_floor,
        "c_out_req_mm": round(c_out_req, 4),
        "c_in_req_mm": round(c_in_req, 4),
        "t_lo_mm": t_lo,
        "t_hi_mm": t_hi,
        "placement_error_mm": eps,
        "clamped": width != max(w_req, w_floor),
    }


@dataclass(frozen=True)
class AppliqueGeometry:
    """The solved offset chain for one piece, every value quantized to 0.1 mm."""

    mode: str
    s_placement: float      # signed normal of the guide run, rel. B
    s_cutting: float        # signed normal of the cutting line, rel. B
    s_tack: float           # signed normal of the tackdown, rel. B
    c_in: float             # cover inner rail, rel. B
    c_out: float            # cover outer rail, rel. B
    width_mm: float         # c_out - c_in
    inside_share: float
    spacing_mm: float
    # Chain reporting, §2.2: what each offset is RELATIVE TO, as vendors state it.
    tack_offset_from_placement: float
    cover_offset_from_tack: float
    # The tolerance audit, so a warning can quote real numbers.
    raw_edge_inner: float   # innermost the raw edge can land = o_tack + t_lo
    raw_edge_outer: float   # outermost = o_tack + t_hi
    bury_mm: float          # how far the tackdown sits inside c_in
    edge_headroom_mm: float # how far c_out reaches past the outermost raw edge
    solved: dict = field(default_factory=dict, compare=False)


def cover_rails(solved: dict, inside_share: float) -> tuple[float, float]:
    """Place the solved cover width against the tolerance stack. -> (c_in, c_out).

    §2.13's solver verbatim: the rails start at the positions the stack
    REQUIRES, and only the surplus over `W_req` is distributed by
    `inside_share`. Surplus goes inward because the error is asymmetric — an
    operator can under-trim and leave fabric hanging outward, but the tackdown
    thread hard-stops over-trimming inward. The floor calls it the 65/35
    rule [P].

    **This is NOT §2.4's construction, and the divergence is deliberate.**
    §2.4's worked default prints `c_in = -1.95, c_out = +1.05`, which is the
    whole 3.00 mm width split 65/35 about B rather than the surplus. Those two
    readings agree nowhere, and §2.4's loses:

    ==========  ===============  ==================  ==================
    discipline  W (both agree)   §2.4 headroom       §2.13 headroom
    ==========  ===============  ==================  ==================
    tight       3.0 mm           +0.50 mm            +0.70 mm
    normal      3.0 mm           +0.00 mm            +0.50 mm
    loose       4.0 mm           **-0.60 mm**        +0.50 mm
    ==========  ===============  ==================  ==================

    "Headroom" is `c_out - (o_tack + t_hi)`: how far the cover reaches past the
    furthest the raw edge can land. §2.4's construction goes **negative** at
    loose discipline — the fabric lands 0.6 mm outside the satin, which is
    §2.15's first failure mode, guaranteed rather than risked. §2.4 itself
    flags its own default as "marginal" at +0.05 mm, and §2.3 states the
    governing inequality `c_out >= o_tack + t_hi + m_edge` that §2.4's numbers
    violate by 0.45 mm. §2.13's pseudocode is the implementable statement of
    §2.3, it holds the inequality at every discipline by construction, and it
    is what the tolerance stack is FOR. So it wins.

    The visible consequence: at the trim-in-place default we sew rails of
    (-1.5, +1.5) where §2.4 prints (-1.95, +1.05). Same 3.00 mm width, same
    tackdown bury margin (0.50 mm, exactly `m_bury`), 0.50 mm of outer headroom
    instead of 0.05.

    **Only the inner rail is quantized; the outer is derived as `c_in + W`** —
    §2.2's unit note taken seriously. 1 DST unit is 0.1 mm, so a rail at
    1.05 mm is 10.5 units and not representable. Rounding two rails
    independently is how a 3.00 mm solve sews as 3.10; deriving the outer from
    the quantized inner and the quantized width makes `c_out - c_in` exactly
    `W`, always.
    """
    w = q(solved["width_mm"])
    surplus = max(0.0, w - solved["w_req_mm"])
    c_in = q(solved["c_in_req_mm"] - surplus * inside_share)
    return c_in, q(c_in + w)


def solve_geometry(
    *,
    mode: str = TRIM_IN_PLACE,
    trim_discipline: str = "normal",
    placement: str = "hand",
    material: str = "woven",
    width_mm: float | None = None,
    o_tack: float | None = None,
    s_placement: float = machine.APPLIQUE_PLACEMENT_OFFSET_MM,
    spacing_mm: float = machine.APPLIQUE_COVER_SPACING_MM,
) -> AppliqueGeometry:
    """The whole offset chain for one piece, solved and quantized.

    `width_mm` overrides the solver (still clamped); `o_tack` overrides the
    tackdown offset. Everything else derives.
    """
    if mode not in (TRIM_IN_PLACE, PRE_CUT):
        raise ValueError(f"unknown appliqué mode {mode!r}")

    # Pre-cut's tackdown is a zigzag/E column straddling B, not a run inside it
    # (§2.7 table) — so its spine offset is 0, and that is what makes "cover
    # offset 0 relative to the tackdown" and "cover centred on B" the same
    # statement for pre-cut (§2.9).
    if o_tack is None:
        o_tack = (0.0 if mode == PRE_CUT else machine.APPLIQUE_TACK_OFFSET_MM)

    solved = solve_cover_width(mode=mode, o_tack=o_tack,
                               trim_discipline=trim_discipline,
                               placement=placement, material=material)
    if width_mm is not None:
        # An explicit override replaces the solver's own request, so
        # "clamped" has to be recomputed against THIS number, not left over
        # from the pre-override solve — config.py calls `applique_cover_width_
        # mm` "an escape hatch for a sew-out comparison, still clamped to
        # [2.5, 5.0]", and that clamp is the more likely real-world way to
        # actually hit the 5.0 mm ceiling, since the solver's own W_req rarely
        # gets there (§2.3's validation table tops out at 4.0 mm, loose).
        requested = float(width_mm)
        solved = dict(solved, width_mm=q(min(
            machine.APPLIQUE_COVER_WIDTH_MAX_MM,
            max(machine.APPLIQUE_COVER_WIDTH_FLOOR_MM, requested))),
            clamped=(requested < machine.APPLIQUE_COVER_WIDTH_FLOOR_MM
                     or requested > machine.APPLIQUE_COVER_WIDTH_MAX_MM))

    inside_share = (machine.APPLIQUE_INSIDE_SHARE_PRECUT if mode == PRE_CUT
                    else machine.APPLIQUE_INSIDE_SHARE_TRIM)
    c_in, c_out = cover_rails(solved, inside_share)

    s_place = q(s_placement)
    s_tack = q(s_place + o_tack)          # chained off the guide run, §2.2
    t_lo, t_hi = machine.APPLIQUE_TRIM_CLEARANCE_MM[trim_discipline]

    if mode == PRE_CUT:
        eps = machine.APPLIQUE_PLACEMENT_ERROR_MM[placement]
        raw_in, raw_out = -eps, eps
    else:
        raw_in, raw_out = s_tack + t_lo, s_tack + t_hi

    return AppliqueGeometry(
        mode=mode,
        s_placement=s_place,
        s_cutting=q(machine.APPLIQUE_CUTTING_OFFSET_MM),
        s_tack=s_tack,
        c_in=c_in,
        c_out=c_out,
        width_mm=q(c_out - c_in),
        inside_share=inside_share,
        spacing_mm=spacing_mm,
        tack_offset_from_placement=q(o_tack),
        cover_offset_from_tack=q((c_in + c_out) / 2.0 - s_tack),
        raw_edge_inner=round(raw_in, 4),
        raw_edge_outer=round(raw_out, 4),
        bury_mm=round(s_tack - c_in, 4),
        edge_headroom_mm=round(c_out - raw_out, 4),
        solved=solved,
    )


# --- Gates (§2.12) ---------------------------------------------------------

def min_inscribed_diameter(poly: Polygon) -> float:
    """Twice the radius of the largest circle that fits inside. -> mm.

    `polylabel` finds the pole of inaccessibility — the interior point furthest
    from the boundary — which is the centre of that circle. Distance is taken
    to `boundary`, not `exterior`, so a hole correctly shrinks the answer: on a
    20 mm square this returns 20.0, and on the same square with a 10 mm hole in
    the middle it returns the 5 mm ring width, which is what a pair of scissors
    actually has to fit into.
    """
    if poly.is_empty:
        return 0.0
    try:
        pole = polylabel(poly, tolerance=0.05)
    except Exception:
        pole = poly.representative_point()
    return 2.0 * pole.distance(poly.boundary)


def _topology(geom) -> tuple[int, int]:
    parts = _parts(geom)
    return len(parts), sum(len(p.interiors) for p in parts)


def narrowest_passage_diameter(poly: Polygon) -> float:
    """Twice the erosion radius at which `poly` first changes topology. -> mm.

    `min_inscribed_diameter` answers "how big is the single best spot in this
    shape" — the ONE largest inscribed circle, found once by `polylabel`. That
    is the wrong question for "can scissors get all the way around this
    piece": a shape can have one huge lobe (a big single circle) and still be
    strangled by a narrow neck the polylabel search never has to visit,
    because the neck's own inscribed circle is nowhere near the global
    maximum. Measured on a synthetic two-lobe "dog bone" (two 20 mm circles
    joined by a 3 mm neck): `min_inscribed_diameter` reports **19.94 mm** —
    one lobe — even though nothing wider than 3 mm can pass through the neck,
    and the gate this feeds (`APPLIQUE_CUTTING_LINE_SUPPRESSED`, "below 12 mm
    scissors don't fit") never fires. Same failure mode on a ring whose hole
    is not centred: the thin side measures 5 mm, `min_inscribed_diameter`
    reports **24.99 mm**, because polylabel's single point lands on the
    ring's fat side instead.

    Found by bisecting the erosion radius at which `poly.buffer(-r)` first
    changes topology relative to `poly` — a new exterior piece appears (the
    dog-bone's neck severing into two lobes), or an interior ring disappears
    by merging into the exterior (the off-centre ring's thin side pinching
    shut) — the standard morphological definition of a bottleneck. On a shape
    with no such neck (a plain square, a plain disc, a centred ring) this
    converges to exactly `min_inscribed_diameter`, so it is a strict
    refinement and not a different number on the ordinary shapes the shipped
    tests already covered.
    """
    if poly.is_empty:
        return 0.0
    lo, hi = 0.0, min_inscribed_diameter(poly) / 2.0
    if hi <= 0.0:
        return 0.0
    base = _topology(poly)
    for _ in range(24):
        mid = (lo + hi) / 2.0
        eroded = poly.buffer(-mid)
        if eroded.is_empty:
            hi = mid
            continue
        t = _topology(eroded)
        if t[0] != base[0] or t[1] < base[1]:
            hi = mid
        else:
            lo = mid
    return 2.0 * lo


def visible_fabric_width(poly: Polygon, c_in: float) -> float:
    """How wide the appliqué fabric still reads between the two inner rails.

    The direct test, not a proxy. §2.12's gate is
    `min_feature_width >= 2*|c_in| + 1.0 mm`, and rearranged that is exactly
    "after eroding the shape by |c_in| — i.e. after both inner cover rails eat
    inward — at least 1.0 mm of fabric is left". So erode and measure what
    survives. A ribbon narrower than 2*|c_in| erodes to nothing and returns
    0.0.

    §2.12 prints the threshold as 5.9 mm, but that is `2*1.95 + 1.0` — §2.4's
    rails, which `cover_rails` does not implement. At the rails we actually sew
    (c_in -1.50 at the 3.0 mm default) the floor is **4.0 mm**. Measured by
    ribbon sweep at 0.5 mm steps: 3.5 mm leaves 0.50 mm and fails, 4.0 mm leaves
    exactly 1.00 mm and passes. A 40 mm square returns 37.00 mm of visible
    fabric, and a 2.5 mm ribbon returns 0.0.
    """
    core = poly.buffer(c_in) if abs(c_in) > 1e-9 else poly
    if core.is_empty:
        return 0.0
    parts = _parts(core)
    if not parts:
        return 0.0
    return max(min_inscribed_diameter(p) for p in parts)


def check_gates(poly: Polygon, geom: AppliqueGeometry) -> list[dict]:
    """Every §2.12 gate, evaluated. -> list of {"code", ...} findings.

    Findings, not exceptions: a gate that fails changes what we emit (drop the
    cutting line, force pre-cut, fall through to plain satin) and the engine
    must SAY it did. §2.12 is explicit that a shape failing `min_feature_width`
    "falls through to plain satin, and the engine must say so rather than
    silently emitting an appliqué with no visible fabric".
    """
    out: list[dict] = []

    # No fabric shows: the two inner rails meet. Threshold `2*|c_in| + 1.0`,
    # which is 4.0 mm at the rails we sew — see `visible_fabric_width` for why
    # that is not §2.12's printed 5.9 mm.
    visible = visible_fabric_width(poly, geom.c_in)
    if visible < machine.APPLIQUE_MIN_FEATURE_MARGIN_MM:
        out.append({"code": APPLIQUE_NO_FABRIC_VISIBLE,
                    "measured_mm": round(visible, 3),
                    "floor_mm": machine.APPLIQUE_MIN_FEATURE_MARGIN_MM,
                    "shape_floor_mm": round(
                        2.0 * abs(geom.c_in)
                        + machine.APPLIQUE_MIN_FEATURE_MARGIN_MM, 3)})

    # Scissors must fit to trim in the hoop — and must fit all the way
    # THROUGH, not just somewhere: `narrowest_passage_diameter`, not
    # `min_inscribed_diameter` (see that function's docstring for the
    # dog-bone/off-centre-ring case this distinction exists for).
    if geom.mode == TRIM_IN_PLACE:
        passage = narrowest_passage_diameter(poly)
        if passage < machine.APPLIQUE_MIN_INSCRIBED_TRIM_MM:
            out.append({"code": APPLIQUE_CUTTING_LINE_SUPPRESSED,
                        "measured_mm": round(passage, 3),
                        "floor_mm": machine.APPLIQUE_MIN_INSCRIBED_TRIM_MM})
        # A hole too small to get scissors into forces the whole piece pre-cut.
        for ring in poly.interiors:
            d = narrowest_passage_diameter(Polygon(ring))
            if d < machine.APPLIQUE_MIN_HOLE_DIAMETER_MM:
                out.append({"code": APPLIQUE_FORCED_PRE_CUT,
                            "measured_mm": round(d, 3),
                            "floor_mm": machine.APPLIQUE_MIN_HOLE_DIAMETER_MM})
                break

    # Pre-cut's own, lower scissors floor (§2.12): the piece has to be hand-cut
    # from sheet stock BEFORE placement, with no in-hoop trim step to fall back
    # to. Trim-in-place has its own separate, higher floor above — the two are
    # mutually exclusive by `geom.mode`, so a piece is never measured against
    # both. `narrowest_passage_diameter`, not `min_inscribed_diameter`, for the
    # same reason the trim-in-place gate uses it: a dog-bone-shaped piece can
    # have a huge single inscribed circle in either lobe while its neck is
    # nowhere near cuttable.
    if geom.mode == PRE_CUT:
        passage = narrowest_passage_diameter(poly)
        if passage < machine.APPLIQUE_MIN_INSCRIBED_PRECUT_MM:
            out.append({"code": APPLIQUE_PRECUT_TOO_NARROW,
                        "measured_mm": round(passage, 3),
                        "floor_mm": machine.APPLIQUE_MIN_INSCRIBED_PRECUT_MM})

    # §2.4 ships the "normal" default at 0.05 mm of headroom against a 0.50 mm
    # margin and says so. Below m_edge the §2.15 top failure mode is one
    # under-trim away.
    if geom.edge_headroom_mm < machine.APPLIQUE_MARGIN_EDGE_MM:
        out.append({"code": APPLIQUE_COVER_MARGINAL,
                    "headroom_mm": geom.edge_headroom_mm,
                    "floor_mm": machine.APPLIQUE_MARGIN_EDGE_MM})

    # `solve_cover_width` has always computed whether the width it returned is
    # the tolerance stack's own number or one of the two hard bounds — no
    # caller read it. Silent at the floor is "risky" (§2.13's own word);
    # silent at the ceiling is §2.12's named snag-risk limit. Both are worth
    # saying out loud, so both fire this one code with which bound it was.
    if geom.solved.get("clamped"):
        bound = ("ceiling" if geom.width_mm >= machine.APPLIQUE_COVER_WIDTH_MAX_MM - 1e-6
                 else "floor")
        out.append({"code": APPLIQUE_COVER_WIDTH_CLAMPED,
                    "width_mm": geom.width_mm,
                    "bound": bound})
    return out


# --- Layer geometry --------------------------------------------------------

def _offset_rings(poly: Polygon, s: float) -> list[list[tuple[float, float]]]:
    """Every closed ring of `poly` offset by signed normal `s`. -> ring coords.

    `s < 0` shrinks (inward, onto the appliqué), `s > 0` grows. Shapely's
    `buffer` handles both and correctly drops a ring that the offset closes up,
    which is the behaviour we want: an offset that swallows a hole means there
    is no hole left to sew around.
    """
    geom = poly if abs(s) < 1e-9 else poly.buffer(s, join_style=2, mitre_limit=3.0)
    rings: list[list[tuple[float, float]]] = []
    for part in _parts(geom):
        rings.append(list(part.exterior.coords))
        rings.extend(list(r.coords) for r in part.interiors)
    return rings


def _run_layer(poly: Polygon, s: float, stitch_mm: float, passes: int,
               kind: str, shape_id: str,
               entry: tuple[float, float] | None) -> list[StitchRun]:
    """A run-stitch layer on the boundary offset by `s`. Placement / cut / tack.

    `passes` > 1 is the double run of §2.7: the same ring walked back, which is
    what holds a fraying woven flat against the stabilizer while the operator
    cuts. Passes retrace rather than offset — a second ring beside the first
    would be a two-line tackdown, not a double run.
    """
    runs: list[StitchRun] = []
    cursor = entry
    for coords in _offset_rings(poly, s):
        length = LineString(coords).length
        if length < machine.RUN_MIN_LOOP_MM:
            continue
        n = max(3, int(round(length / stitch_mm)))
        ring_pts, _total = _ring_arc_samples(coords, n)
        if not ring_pts:
            continue
        # Enter the ring nearest the needle, so a layer change is a hop and not
        # a flight across the design.
        if cursor is not None:
            start = min(range(len(ring_pts)),
                        key=lambda i: (round(math.dist(ring_pts[i], cursor), 6), i))
        else:
            start = 0
        lap = [ring_pts[(start + i) % len(ring_pts)] for i in range(len(ring_pts))]
        lap.append(ring_pts[start])
        pts = list(lap)
        for p in range(1, max(1, passes)):
            leg = list(reversed(lap)) if p % 2 == 1 else list(lap)
            pts.extend(leg[1:])
        if len(pts) < 2:
            continue
        runs.append(StitchRun(points=stitches.split_long_moves(pts), kind=kind,
                              shape_id=shape_id))
        cursor = pts[-1]
    return runs


def _rail_column(poly: Polygon, c_in: float, c_out: float, spacing_mm: float,
                 kind: str, shape_id: str,
                 entry: tuple[float, float] | None,
                 overlap_stitches: int | None = None
                 ) -> tuple[list[StitchRun], int]:
    """A satin-style column straddling B from `c_in` to `c_out`. -> (runs, crosses).

    Built on the border module's proven column emitter rather than a second
    copy of one: it already alternates rails on the count of KEPT crosses,
    guards short stitches on the inside of a turn, and closes the circuit past
    its own start on a phase shift. What differs here is only where the rails
    go — the outer rail rides the boundary grown by `c_out`, and the column
    reaches `width` inward from there, landing the inner rail on `c_in`.

    Shared by the cover (§2.8, `_cover_layer`) and the zigzag/E-stitch
    tackdown (§2.7, `_zigzag_tack_layer`) — same rail-alternating column, only
    the rails and spacing differ.

    `overlap_stitches` is the closure overlap stated as an exact station
    count (`_cover_layer` passes `APPLIQUE_CLOSURE_OVERLAP_STITCHES`); `None`
    (the tackdown's call) falls through to `_satin_loop`'s own
    `BORDER_CLOSURE_OVERLAP_MM` default, unchanged.
    """
    runs: list[StitchRun] = []
    crosses = 0
    cursor = entry
    width = c_out - c_in
    # Same relationship the zigzag has everywhere else in the engine: `spacing`
    # is the gap between consecutive penetrations on the SAME rail, and every
    # stitch crosses the column, so stations sit at half the spacing.
    step = spacing_mm / 2.0

    outer_geom = poly.buffer(c_out) if abs(c_out) > 1e-9 else poly
    for host in _parts(outer_geom):
        # The column needs a turn radius or its inner rail folds back on itself
        # — §2.15's "satin breaks on tight concave corner", whose stated fix is
        # to fillet to r >= |c_in| + 0.3 BEFORE rail generation.
        r_corner = abs(c_in) + machine.APPLIQUE_MIN_CONCAVE_MARGIN_MM
        rounded = round_inward(host, r_corner, step)
        for part in _parts(rounded):
            slack = part.buffer(_SLACK_MM)
            for coords in ([list(part.exterior.coords)]
                           + [list(r.coords) for r in part.interiors]):
                length = LineString(coords).length
                if length < machine.BORDER_MIN_LOOP_MM:
                    continue
                n = max(8, int(round(length / step)))
                ring_pts, total = _ring_arc_samples(coords, n)
                if not ring_pts:
                    continue
                k_tan = max(1, int(round((width / 2.0) / step)))
                pts, kept, _clamped = _satin_loop(
                    ring_pts, total, total / n, width, slack, cursor,
                    k_tan, overlap_stitches=overlap_stitches)
                if len(pts) < 2:
                    continue
                runs.append(StitchRun(points=stitches.split_long_moves(pts),
                                      kind=kind, shape_id=shape_id))
                cursor = pts[-1]
                crosses += kept
    return runs, crosses


def _cover_layer(poly: Polygon, geom: AppliqueGeometry, shape_id: str,
                 entry: tuple[float, float] | None) -> tuple[list[StitchRun], int]:
    """The cover column, straddling B from `c_in` to `c_out`. -> (runs, crosses).

    Pull compensation (§2.8, `APPLIQUE_COVER_PULL_COMP_MM`, 0.20 mm): thread
    tension pulls each cross's two penetrations together, so a column digitized
    at exactly the solved width sews narrower than that — the same effect
    `Fabric.pull_comp_mm` compensates for on an ordinary satin column (see
    `machine.py`'s Law 24 note: "a column loses width ALONG its stitch
    direction"). Stage 5's own pull comp is deliberately NOT in this path —
    `applique_pass` passes the raw artwork polygon, because B has to stay the
    exact tolerance-stack offset chain's reference point, not something a
    fabric preset already grew. So the cover gets its OWN, appliqué-specific
    compensation, applied the same way stage 5 applies its: `poly.buffer(pull)`
    grows every edge of a shape outward by `pull`, and for a ribbon that means
    BOTH long edges move away from the ribbon by `pull`, widening it by
    `2 * pull` total (confirmed on `Fabric` "pique_knit", pull_comp_mm 0.3: a
    4.5 mm bar sews at 5.1 mm, `tests/test_pushcomp.py`). Here the two "edges"
    are the two rails, so `c_in` moves `pull` further inward and `c_out`
    moves `pull` further outward — the STITCHED column only; `geom.c_in`/
    `geom.c_out`/`width_mm` are left alone, because those are what the
    tolerance-stack gates (`edge_headroom_mm`, `bury_mm`, §2.12's checks) and
    every existing test measure against, and they describe the DESIGNED
    width, not the sewn one. Measured on `SHIELD` at the trim-in-place
    default: the cover's rails moved from (-1.50, +1.50) to (-1.70, +1.70),
    i.e. exactly `geom.c_in - 0.20` / `geom.c_out + 0.20`, a 3.00 mm design
    now sewing a 3.40 mm column.

    Closure overlap (§2.8, `APPLIQUE_CLOSURE_OVERLAP_STITCHES`, 6): the
    appliqué-specific stitch count, not `BORDER_CLOSURE_OVERLAP_MM` (1.40 mm,
    the border module's own generic number) which `_cover_layer` used to
    inherit unconditionally through `_satin_loop`'s hardcoded default. At the
    0.40 mm cover spacing the two land close — 1.40 mm / 0.20 mm-per-station
    rounds to 7 stitches, 1 more than the appliqué constant's 6 — and BOTH
    numbers sit inside Stahls' published 4-8 stitch window [S], so this was
    never a visible defect. It is fixed anyway: `APPLIQUE_CLOSURE_OVERLAP_
    STITCHES` exists specifically for this call site (§2.8's own row, not
    §2.6/§2.7's), the border number is a coincidence that only holds while
    `APPLIQUE_COVER_SPACING_MM` stays 0.40 mm (nothing enforces that), and an
    exact station count sidesteps the `int(overlap_mm / step)` rounding
    `_loop_stations` does for the mm path, so what's requested is exactly
    what's sewn regardless of how a given ring's arc length divides. See
    `_rail_column`'s `overlap_stitches` param.
    """
    pull = machine.APPLIQUE_COVER_PULL_COMP_MM
    c_in = q(geom.c_in - pull)
    c_out = q(geom.c_out + pull)
    return _rail_column(poly, c_in, c_out, geom.spacing_mm, COVER, shape_id,
                        entry, overlap_stitches=machine.APPLIQUE_CLOSURE_OVERLAP_STITCHES)


def _zigzag_tack_layer(poly: Polygon, geom: AppliqueGeometry, shape_id: str,
                       entry: tuple[float, float] | None
                       ) -> tuple[list[StitchRun], int]:
    """The zigzag/E tackdown column for pre-cut (§2.7). -> (runs, crosses).

    §2.7's table gives the tackdown a real WIDTH for zigzag/E ("positioned by
    column width, centered on the line", §2.2) — a straddling column that
    compresses the fabric, unlike the run/double-run tackdown which is a
    single line. Before this function existed, `tackdown="zigzag"` (the
    pre-cut default — see `applique_steps`) fell into `_run_layer` exactly
    like `"run"`, and the pass-count branch there only distinguishes
    `"double_run"` from everything else — so it silently sewed a zero-width,
    single-pass running stitch on B. `APPLIQUE_TACK_WIDTH_MM` existed as a
    constant and was never read by any code path.

    Width is the hard vendor constraint verbatim: `W_tack <= W_cover -
    2*m_bury` (Hatch: "Width is constrained by width of cover stitch, if
    used"). Centered on `geom.s_tack`, not split — for pre-cut `o_tack` is
    already 0 (`solve_geometry`'s own choice, "centered on B" per §2.7's row
    for this stitch type), so centering on the tackdown line and centering on
    B are the same statement here. §2.7's worked example prints an 80/20
    in/out split landing off-center; that number is not reproducible from
    the row it sits next to (which states the offset IS centered) and this
    module already treats an inconsistency between a spec's worked example
    and its own stated rule as decided in the rule's favour once (`cover_
    rails` over §2.4's worked default) — same call here.
    """
    width = min(machine.APPLIQUE_TACK_WIDTH_MM,
               max(0.0, geom.width_mm - 2.0 * machine.APPLIQUE_MARGIN_BURY_MM))
    c_in = q(geom.s_tack - width / 2.0)
    c_out = q(c_in + width)
    return _rail_column(poly, c_in, c_out, machine.APPLIQUE_TACK_STITCH_MM,
                        TACKDOWN, shape_id, entry)


# --- Steps -----------------------------------------------------------------

@dataclass
class Step:
    """One block of sewing plus the boundary that ends it.

    The boundary is the whole point. `function` is what the machine does
    (`color_change` on a single head, `end` for the last step) and `action` is
    what the HUMAN does while it is stopped. §6.5: every step must carry a
    non-empty action or the emitter should refuse to build the file — a stop
    with no instruction is worse than no stop.
    """

    code: str                      # operator verb: PLACE / CUT+TACK / COVER
    label: str                     # what the machine sews in this step
    runs: list[StitchRun]
    action: str = ""               # what the operator does at the boundary
    function: str = COLOR_CHANGE
    flags: tuple[str, ...] = ()
    material: str = ""
    piece: str = ""
    layers: tuple[str, ...] = ()
    spm: int | None = None

    @property
    def stitch_count(self) -> int:
        return sum(len(r.points) for r in self.runs)

    def as_meta(self, index: int, thread_number: str) -> dict:
        """The JSON-shaped dict that rides `StitchBlock.step` to the worksheet."""
        return {
            "index": index,
            "code": self.code,
            "label": self.label,
            "action": self.action,
            "function": self.function,
            "flags": list(self.flags),
            "material": self.material,
            "piece": self.piece,
            "layers": list(self.layers),
            "stitches": self.stitch_count,
            "thread": thread_number,
            "spm": self.spm,
        }


def assert_steps_valid(steps: list[Step]) -> None:
    """§6.5's refusal. A stop with no instruction is worse than no stop.

    Raised, not warned: this is the invariant the entire worksheet rests on. If
    the sheet and the file can disagree about what happens at a stop, the
    operator does the wrong thing at the right time.
    """
    for i, st in enumerate(steps):
        if st.function == COLOR_CHANGE and not st.action.strip():
            raise ValueError(
                f"step {i} ({st.code}) ends in a color change with no operator "
                "action — one color stop = one human action")


def plan_steps(plan) -> list[dict]:
    """Ordered `steps[]` for a whole plan, one per block. -> list of dicts.

    THE READ INTERFACE, and it is uniform: a specialty block carries real step
    metadata, an ordinary artwork block gets a synthesized thread-change step,
    and the worksheet renders one list either way without asking which tier
    produced the design. Keys are documented on `Step.as_meta`.

    `function` on the last step is `end`, not `color_change` — the machine
    stops there because the file is over, and the sheet should not print a
    change the operator will wait for.
    """
    out: list[dict] = []
    last = len(plan.blocks) - 1
    for i, block in enumerate(plan.blocks):
        meta = dict(block.step) if block.step else {
            "code": "COLOR",
            "label": f"Thread {block.thread_number}",
            "action": f"Change thread to {block.thread_number}",
            "function": COLOR_CHANGE,
            "flags": [],
            "material": "",
            "piece": "",
            "layers": [],
            "spm": None,
        }
        meta["index"] = i + 1
        meta["stitches"] = block.stitch_count
        meta["thread"] = block.thread_number
        meta["rgb"] = list(block.rgb)
        if i == last:
            # The machine halts here because the file is over, not because
            # anyone has to do anything. Printing a change the operator would
            # wait for is exactly the kind of wrong-thing-at-the-right-time
            # §6.5 is about.
            meta["function"] = END
            meta["action"] = "Design complete"
            meta["flags"] = []
        out.append(meta)
    return out


def _tie_layers(runs: list[StitchRun]) -> None:
    """Tie in and tie off at the start and end of every LAYER. §2.14.

    Not per block: a step can hold two layers back to back (cutting line then
    tackdown), and §2.14 asks for a lock at each layer's own ends — three
    stitches, about 0.7 mm. There are deliberately no trims WITHIN a layer, so
    the only tie points are the layer seams.

    Layers are told apart by `run.kind`, which is why the four layer kinds are
    distinct constants rather than all being `stitches.RUN`.
    """
    if not runs:
        return
    groups: list[list[StitchRun]] = []
    for r in runs:
        if groups and groups[-1][0].kind == r.kind:
            groups[-1].append(r)
        else:
            groups.append([r])
    for grp in groups:
        first, last = grp[0], grp[-1]
        if len(first.points) >= 2:
            pts = stitches.tie_run(first.points[0], first.points[1]).points
            first.points = pts[:-1] + first.points
        if len(last.points) >= 2:
            pts = stitches.tie_run(last.points[-1], last.points[-2]).points
            last.points = last.points + pts[1:]


# --- The emitter (§2.14) ---------------------------------------------------

def applique_steps(poly: Polygon, shape_id: str, geom: AppliqueGeometry, *,
                   entry: tuple[float, float] | None = None,
                   tackdown: str | None = None,
                   cover: str = "satin",
                   material_label: str = "appliqué fabric",
                   ) -> tuple[list[Step], dict]:
    """Emit one piece's four (or three) layers, grouped into steps. §2.14.

    Trim-in-place — 4 layers, 2 stops::

        guide run -> [CC, lay fabric] -> cutting line -> tackdown
                  -> [CC, trim] -> cover

    The trim happens **after** the tack, not between cutting line and tack:
    cutting line and tackdown run back-to-back inside one block. Wilcom is
    explicit — "Set a Frame Out after the tack stitching in order to trim the
    appliqué patch" [V] — and §2.1 notes most hobby writeups get this wrong.
    The reason is mechanical: the tackdown is what holds the fabric flat while
    the operator cuts, so it must already be down.

    Pre-cut — 3 layers, 1 stop::

        guide run -> [CC, lay pre-cut piece] -> tackdown -> cover

    Melco makes exactly this an explicit checkbox, "Enable Color Change After
    Tackdown", which you leave off for pre-cut [V]. The tackdown runs straight
    into the cover with no stop (§2.7 terminate rule).

    The placement run is **never** suppressed, in either mode — §2.15's
    "misaligned appliqué" failure mode is the placement line being skipped.
    """
    report = {"crosses": 0, "layers": 0, "gates": check_gates(poly, geom),
              "cutting_line": False}
    codes = {g["code"] for g in report["gates"]}

    mode = geom.mode
    if APPLIQUE_FORCED_PRE_CUT in codes:
        mode = PRE_CUT           # a hole too small to trim decides for us

    if tackdown is None:
        # §2.7: trim-in-place wants run/double run, because a zigzag tack gets
        # clipped by the scissors and leaves fabric whiskers [P]. Pre-cut has
        # nothing to trim, so a column can straddle the edge and compress it.
        tackdown = "double_run" if mode == TRIM_IN_PLACE else "zigzag"

    cursor = entry

    # --- Layer 1: placement / guide run.
    place = _run_layer(poly, geom.s_placement, machine.APPLIQUE_PLACEMENT_STITCH_MM,
                       machine.APPLIQUE_PLACEMENT_PASSES, PLACEMENT, shape_id,
                       cursor)
    if place:
        cursor = place[-1].points[-1]
        report["layers"] += 1

    steps = [Step(
        code="PLACE",
        label="Sew the placement outline",
        runs=place,
        action=f"Lay {material_label} over the placement outline",
        function=COLOR_CHANGE,
        flags=("FRAME OUT", "SAME NEEDLE"),
        material=material_label,
        piece=shape_id,
        layers=(PLACEMENT,),
    )]

    # --- Layers 2+3: cutting line, then tackdown, back-to-back in one block.
    middle: list[StitchRun] = []
    layers_here: list[str] = []
    if mode == TRIM_IN_PLACE and APPLIQUE_CUTTING_LINE_SUPPRESSED not in codes:
        cut = _run_layer(poly, geom.s_cutting, machine.APPLIQUE_CUTTING_STITCH_MM,
                         1, CUTTING, shape_id, cursor)
        if cut:
            middle.extend(cut)
            layers_here.append(CUTTING)
            cursor = cut[-1].points[-1]
            report["layers"] += 1
            report["cutting_line"] = True

    if tackdown != "none":
        if tackdown in ("zigzag", "e_stitch"):
            # A straddling column, not a run — see `_zigzag_tack_layer`.
            tack, _tack_crosses = _zigzag_tack_layer(poly, geom, shape_id, cursor)
        else:
            passes = (machine.APPLIQUE_TACK_PASSES if tackdown == "double_run" else 1)
            tack = _run_layer(poly, geom.s_tack, machine.APPLIQUE_TACK_STITCH_MM,
                              passes, TACKDOWN, shape_id, cursor)
        if tack:
            middle.extend(tack)
            layers_here.append(TACKDOWN)
            cursor = tack[-1].points[-1]
            report["layers"] += 1

    if mode == TRIM_IN_PLACE:
        steps.append(Step(
            code="CUT+TACK" if report["cutting_line"] else "TACK",
            label=("Cutting line, then tackdown" if report["cutting_line"]
                   else "Tackdown"),
            runs=middle,
            action="Trim close to the tackdown, just outside the stitch line",
            function=COLOR_CHANGE,
            flags=("FRAME OUT", "SAME NEEDLE"),
            material=material_label,
            piece=shape_id,
            layers=tuple(layers_here),
            spm=machine.APPLIQUE_TRIM_HEAVY_SPM,
        ))
        cover_runs, crosses = _cover_layer(poly, geom, shape_id, cursor)
        report["crosses"] = crosses
        if cover_runs:
            report["layers"] += 1
        steps.append(Step(
            code="COVER",
            label=f"{geom.width_mm:.2f} mm {cover} cover, "
                  f"{geom.spacing_mm:.2f} mm spacing",
            runs=cover_runs,
            # Every appliqué step ends in a color change; `plan_steps` rewrites
            # the plan's FINAL block to `end`, because only the plan knows
            # whether more artwork follows this piece.
            action="Appliqué piece complete",
            function=COLOR_CHANGE,
            piece=shape_id,
            layers=(COVER,),
            spm=machine.APPLIQUE_COVER_SPM,
        ))
    else:
        # Pre-cut: the tackdown runs straight into the cover with NO stop —
        # Melco's "Enable Color Change After Tackdown" checkbox, left off [V].
        cover_runs, crosses = _cover_layer(poly, geom, shape_id, cursor)
        report["crosses"] = crosses
        if cover_runs:
            report["layers"] += 1
        steps.append(Step(
            code="TACK+COVER",
            label=f"Tackdown, then {geom.width_mm:.2f} mm {cover} cover at "
                  f"{geom.spacing_mm:.2f} mm spacing",
            runs=middle + cover_runs,
            action="Appliqué piece complete",
            function=COLOR_CHANGE,
            material=material_label,
            piece=shape_id,
            layers=tuple(layers_here) + (COVER,),
            spm=machine.APPLIQUE_COVER_SPM,
        ))

    report["mode"] = mode
    return steps, report


# --- The stage-7 boundary guard -------------------------------------------

def nn_group_key(planned) -> tuple:
    """The key stage 7 partitions its nearest-neighbour pool by.

    **This is consequence 3 of §0, as code.** The resequencer reorders shapes
    to save needle travel, and left alone it would happily merge two objects
    into one block to save a color stop. On ordinary artwork that is a pure
    win. Across a step boundary it destroys an operator instruction — the file
    stops carrying "lay the twill here" and the operator sews the cover onto
    bare garment.

    So a region carrying `meta["step_key"]` never shares a pool, and therefore
    never shares a BLOCK, with a region from another step. Regions without one
    key on `("", )` and group exactly as they always did: for a design with no
    steps this returns `(sew_index, "", thread)` for every region and the sort
    order is identical to the old `sorted({p.sew_index for p in planned})`.

    The thread is in the key for the shape-layers contract's `layer` override:
    a shape moved into another thread's layer shares that layer's SEW POSITION
    but must not share its block — a block is sewn in ONE thread, and stage 7
    takes the block's thread from its first region. In every unedited design a
    layer holds exactly one thread, so the extra key partitions nothing and
    the order is untouched.
    """
    return (planned.sew_index, str(planned.region.meta.get("step_key", "")),
            planned.region.thread_index)


# --- Stage 7 entry point ---------------------------------------------------

def _wants_applique(region, cfg: PipelineConfig) -> bool:
    """Per-shape intent beats the mode in both directions, exactly like border."""
    want = region.meta.get("applique")
    if want is None:
        return bool(cfg.applique)
    return bool(want)


def applique_pass(planned, cfg: PipelineConfig, chart
                  ) -> tuple[list, list[dict], list, tuple[float, float] | None]:
    """The stage-7 tier branch. -> (blocks, warnings, remaining, cursor).

    Appliqué pieces sew FIRST and come out of the normal color loop entirely:
    the fabric goes down before anything decorates it, and every piece's steps
    are consecutive blocks so no other color can land between "lay the twill"
    and "trim it". Ordering across pieces is §2.11 Mode A, per-piece
    `P1 T1 C1 · P2 T2 C2` — always correct, 2 stops per piece. Mode B batching
    (2 stops total) is NOT built: it is only valid when no piece overlaps
    another, and the overlap case needs the partial-cover arc suppression that
    is also not built. Overlaps are detected and warned instead of being sewn
    as two stacked satins on one band, which at the 0.40 mm default is 0.20 mm
    effective — below the 0.30 mm floor, i.e. guaranteed fabric damage (§2.11).

    Returns the blocks, the warnings, the regions the normal loop should still
    handle, and where the needle was left.
    """
    from .stitches import StitchBlock

    if not cfg.applique and not any(
            p.region.meta.get("applique") for p in planned):
        return [], [], list(planned), None

    picked = [p for p in planned if _wants_applique(p.region, cfg)]
    remaining = [p for p in planned if not _wants_applique(p.region, cfg)]
    if not picked:
        return [], [], remaining, None

    # Bottom-to-top: stage 5 already settled which layer sews under which.
    picked.sort(key=lambda p: (p.region.meta.get("layer", 0), p.sew_index,
                               p.shape_id))

    counts = {APPLIQUE_NO_FABRIC_VISIBLE: 0, APPLIQUE_CUTTING_LINE_SUPPRESSED: 0,
              APPLIQUE_FORCED_PRE_CUT: 0, APPLIQUE_COVER_MARGINAL: 0,
              APPLIQUE_STEP_EMPTY: 0, APPLIQUE_COVER_WIDTH_CLAMPED: 0,
              APPLIQUE_PRECUT_TOO_NARROW: 0}
    headroom: float | None = None
    clamp_bounds: set[str] = set()

    overlaps = 0
    for i in range(len(picked)):
        for j in range(i + 1, len(picked)):
            if picked[i].polygon.intersects(picked[j].polygon) and \
                    picked[i].polygon.intersection(picked[j].polygon).area > 1e-6:
                overlaps += 1

    blocks = []
    cursor: tuple[float, float] | None = None
    for p in picked:
        geom = solve_geometry(
            mode=cfg.applique_mode,
            trim_discipline=cfg.applique_trim_discipline,
            placement=cfg.applique_placement,
            material=cfg.applique_material,
            width_mm=cfg.applique_cover_width_mm,
        )
        # The artwork polygon, not stage 5's pull-compensated one: B is the
        # intended finished location of the raw fabric edge, and the offset
        # chain measures from it. Growing B by the fabric's pull comp first
        # would move every published offset by that much.
        steps, report = applique_steps(
            p.region.polygon, p.shape_id, geom, entry=cursor,
            tackdown=cfg.applique_tackdown, cover=cfg.applique_cover)
        for g in report["gates"]:
            counts[g["code"]] = counts.get(g["code"], 0) + 1
            if g["code"] == APPLIQUE_COVER_MARGINAL:
                headroom = g["headroom_mm"] if headroom is None else min(
                    headroom, g["headroom_mm"])
            elif g["code"] == APPLIQUE_COVER_WIDTH_CLAMPED:
                clamp_bounds.add(g["bound"])

        # §0.2's hazard, caught where it actually lives. Stage 7 drops a block
        # with no runs (`if not ordered: continue`), which would take the stop
        # with it and leave the operator an instruction short. An empty step is
        # refused loudly rather than silently welding its neighbours together.
        kept = [s for s in steps if s.runs]
        counts[APPLIQUE_STEP_EMPTY] += len(steps) - len(kept)
        if not kept:
            continue
        assert_steps_valid(kept)

        thread = chart[p.region.thread_index]
        for s in kept:
            _tie_layers(s.runs)
            # The needle always lifts into a new block and the thread is always
            # cut coming out of the previous one — the same rule stage 7
            # applies to a color block, because this IS a color block.
            s.runs[0].jump = True
            s.runs[0].trim = True
            blocks.append(StitchBlock(
                thread_index=p.region.thread_index,
                thread_number=thread.number,
                rgb=tuple(thread.rgb),
                runs=s.runs,
                step=s.as_meta(len(blocks) + 1, thread.number),
            ))
            cursor = s.runs[-1].points[-1]

    warnings: list[dict] = []
    n = counts[APPLIQUE_NO_FABRIC_VISIBLE]
    if n:
        warnings.append(warn(
            APPLIQUE_NO_FABRIC_VISIBLE,
            f"{n} appliqué piece{'s are' if n != 1 else ' is'} too narrow for "
            "the cover satin to leave any fabric showing — the two inner rails "
            "meet. It will read as plain satin, not appliqué.",
            count=n))
    n = counts[APPLIQUE_CUTTING_LINE_SUPPRESSED]
    if n:
        warnings.append(warn(
            APPLIQUE_CUTTING_LINE_SUPPRESSED,
            f"{n} piece{'s were' if n != 1 else ' was'} too small to get "
            "scissors into, so no cutting line was sewn. Pre-cut "
            f"{'them' if n != 1 else 'it'} instead.",
            count=n))
    n = counts[APPLIQUE_FORCED_PRE_CUT]
    if n:
        warnings.append(warn(
            APPLIQUE_FORCED_PRE_CUT,
            f"{n} piece{'s have' if n != 1 else ' has'} a hole too small to "
            "trim in the hoop, so it was switched to pre-cut.",
            count=n))
    n = counts[APPLIQUE_PRECUT_TOO_NARROW]
    if n:
        warnings.append(warn(
            APPLIQUE_PRECUT_TOO_NARROW,
            f"{n} pre-cut piece{'s have' if n != 1 else ' has'} a bottleneck "
            "under 8 mm somewhere in the shape, too narrow to cut cleanly "
            "with scissors before placing it.",
            count=n))
    n = counts[APPLIQUE_COVER_MARGINAL]
    if n:
        warnings.append(warn(
            APPLIQUE_COVER_MARGINAL,
            f"The cover reaches only {headroom:.2f} mm past the furthest the "
            "raw edge can land. An under-trim will show fabric outside the "
            "satin — widen the cover or tighten the trim discipline.",
            count=n, headroom_mm=headroom))
    n = counts[APPLIQUE_STEP_EMPTY]
    if n:
        warnings.append(warn(
            APPLIQUE_STEP_EMPTY,
            f"{n} appliqué step{'s' if n != 1 else ''} produced no stitches "
            "and were dropped along with the machine stop they carried.",
            count=n))
    n = counts[APPLIQUE_COVER_WIDTH_CLAMPED]
    if n:
        which = " and ".join(sorted(clamp_bounds))
        warnings.append(warn(
            APPLIQUE_COVER_WIDTH_CLAMPED,
            f"{n} piece{'s hit' if n != 1 else ' hit'} the cover width "
            f"{which} bound (2.5-5.0 mm) rather than sewing the tolerance "
            "stack's own solved width — at the ceiling this is §2.12's "
            "snag-risk limit, at the floor §2.13's own \"risky\" minimum.",
            count=n, bounds=sorted(clamp_bounds)))
    if overlaps:
        warnings.append(warn(
            APPLIQUE_PIECES_OVERLAP,
            f"{overlaps} pair{'s' if overlaps != 1 else ''} of appliqué pieces "
            "overlap. Their covers will stack on the same band — sew them as "
            "separate pieces or move them apart.",
            count=overlaps))

    return blocks, warnings, remaining, cursor
