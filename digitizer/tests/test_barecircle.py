"""The widest-inscribed-bare-circle instrument (barecircle.py) — validation
against the 2026-08-02 adversarial pass's own figures, and the recalibrated
`starved` gate it defines.

The config block's mandate was explicit: build the instrument FIRST, prove it
reproduces the cited numbers on the cited fixtures, and only then let it
define `starved`. This file is that proof, and it is honest about the one
number that did not survive re-measurement as written:

  * logo_whitebg's Sb253ebba under contour: cited 0.640 mm bare radius,
    measured 0.644 — reproduced (one raster pixel is 0.031 mm).
  * the same shape under tatami: cited 0.090, measured 0.094 — reproduced.
  * the 10-point star (inradius 10.00): the mitred-offset annihilation and
    the ledger blindness reproduce exactly as described — offsets exhaust at
    barely half the shape's inradius while `skipped_area_mm2` charges under
    1 % — but the "2.94 mm bare disc" does NOT reproduce as a radius. Every
    reconstruction of that star measures 1.28-1.43 mm bare RADIUS (the
    critical-ratio family below reads 1.33). Defect 2's own text ("silent on
    that 1.47 mm bare radius") refers back to this star and only coheres if
    2.94 was the disc's DIAMETER — 2.94 / 2 = 1.47. This suite pins the
    measured radius and states the reading; it does not force agreement with
    a figure the current engine never produces.
  * "firing on 0.51 mm elsewhere": reproduced on the repo's own fixture —
    whitebg's Sf5200f3f measures 0.499 mm bare with the old area gate firing.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
import shapely
from shapely.geometry import Polygon

from digitizer_core import machine
from digitizer_core.barecircle import (BareCircle, starved_threshold_mm,
                                       widest_bare_circle)
from digitizer_core.stage6_contour import _rings, contour_fill
from digitizer_core.stage6_fill import stitch_shape
from tests.conftest import cfg


def _circle(r, cx=0.0, cy=0.0, n=192):
    return Polygon([(cx + r * math.cos(t), cy + r * math.sin(t))
                    for t in np.linspace(0, 2 * math.pi, n, endpoint=False)])


def _star(n_spikes, r_out, r_in, rot=math.pi / 2):
    pts = []
    for i in range(2 * n_spikes):
        r = r_out if i % 2 == 0 else r_in
        t = rot + i * math.pi / n_spikes
        pts.append((r * math.cos(t), r * math.sin(t)))
    return Polygon(pts)


def _star_inradius_10(ratio):
    """A 10-point (10-spike) star scaled so its maximum inscribed circle is
    exactly 10.00 mm — the adversarial pass's own construction, reconstructed
    from its description."""
    s0 = _star(10, 20.0, 20.0 * ratio)
    sc = 10.0 / shapely.maximum_inscribed_circle(s0, 1e-4).length
    return shapely.affinity.scale(s0, xfact=sc, yfact=sc, origin=(0, 0))


# Sharp spikes: the mitre limit bevels the notch offsets, the interior
# collapses at under half the inradius, and the un-charged core is widest.
STAR_SHARP = _star_inradius_10(0.30)
# The ratio whose raw mitred buffer annihilates nearest 5.60 mm — the depth
# the config block cites verbatim.
STAR_CITED = _star_inradius_10(0.50)

DUMBBELL = (_circle(7.0, cx=-10.0).union(_circle(7.0, cx=10.0))
            .union(Polygon([(-10, -0.3), (10, -0.3), (10, 0.3), (-10, 0.3)])))


def _fill(poly, **kw):
    kw.setdefault("spacing_mm", machine.FILL_ROW_MM)
    kw.setdefault("stitch_mm", machine.FILL_STITCH_MM)
    kw.setdefault("underlay_style", "none")
    kw.setdefault("trim_at_mm", machine.TRIM_AT_MM)
    return contour_fill(poly, "S1", **kw)


def _logo_shape(whitebg, shape_id):
    """One planned shape of the fixture logo, with the exact fill parameters
    stage 7 would hand its emitter — the 'shipped width' configuration the
    adversarial pass measured."""
    from digitizer_core.pipeline import fabric_for
    from digitizer_core.stage5_overlap import resolve_overlaps

    c = cfg()
    fabric = fabric_for(c)
    planned, _w = resolve_overlaps(whitebg.regions, fabric, c)
    p = next(p for p in planned if p.shape_id == shape_id)
    row = (c.fill_row_mm or machine.FILL_ROW_MM) * max(0.1, fabric.density_adjust)
    return p, row, fabric


# --- The instrument itself ---------------------------------------------------

def test_no_thread_at_all_measures_the_plain_inradius():
    """The instrument trusts only the polygon and the runs. With no runs the
    widest bare circle IS the inscribed circle, which pins both that the EDT
    is measuring real distances and that nothing in the answer comes from any
    emitter's bookkeeping."""
    bc = widest_bare_circle(_circle(10.0), [])
    assert bc.radius_mm == pytest.approx(10.0, abs=0.06)
    assert math.dist(bc.center, (0.0, 0.0)) < 0.1


def test_the_instrument_is_deterministic():
    runs, _ = _fill(STAR_SHARP)
    a = widest_bare_circle(STAR_SHARP, runs)
    b = widest_bare_circle(STAR_SHARP, runs)
    assert a == b


def test_a_degenerate_polygon_measures_zero():
    assert widest_bare_circle(Polygon(), []) == BareCircle(0.0, (0.0, 0.0))


# --- Reproduction of the cited figures ---------------------------------------

def test_reproduces_the_cited_contour_figure_on_the_fixture_logo(whitebg):
    """Cited: Sb253ebba at shipped width leaves a 0.640 mm bare radius under
    contour. Measured on the reconstruction: 0.644 — one raster pixel off.

    UPDATE 2026-08-04 (bare-core shrink): 0.154 now, not 0.644 —
    `_refine_terminal_generation` + the finishing pass (stage6_contour.py)
    cut this shape's own bare radius by more than three quarters. See
    `machine.CONTOUR_BARE_CORE_MM` for the structural-dot measurement this
    number is judged against.
    """
    p, row, fabric = _logo_shape(whitebg, "Sb253ebba")
    runs, report = contour_fill(p.polygon, p.shape_id, spacing_mm=row,
                                stitch_mm=machine.FILL_STITCH_MM,
                                underlay_style=fabric.fill_underlay,
                                trim_at_mm=fabric.trim_at_mm)
    bc = widest_bare_circle(p.polygon, runs)
    assert bc.radius_mm == pytest.approx(0.154, abs=0.03)
    # The production gate now carries the same measurement in its report.
    assert report["bare_radius_mm"] == pytest.approx(bc.radius_mm, abs=1e-9)


def test_reproduces_the_cited_tatami_figure_on_the_fixture_logo(whitebg):
    """Cited: tatami's own worst bare spot on the same shape is 0.090 mm.
    Measured: 0.094. This is the reference for what a fill CAN do, and it is
    what makes contour's 7x figure a defect rather than a fact of life."""
    p, row, fabric = _logo_shape(whitebg, "Sb253ebba")
    runs, _report = stitch_shape(p.polygon, p.shape_id,
                                 angle_deg=p.stitch_angle_deg, row_mm=row,
                                 stitch_mm=machine.FILL_STITCH_MM,
                                 underlay_style=fabric.fill_underlay,
                                 trim_at_mm=fabric.trim_at_mm)
    bc = widest_bare_circle(p.polygon, runs)
    assert bc.radius_mm == pytest.approx(0.090, abs=0.05)


def test_the_stars_offsets_die_at_half_its_depth_and_the_ledger_never_hears():
    """Defect 1's mechanism, on the reconstructed 10-point star: the mitred
    inward offset annihilates the notched interior at barely half the
    inradius, and `skipped_area_mm2` — which can only charge rings it SAW —
    stays under 1 % of the shape. The cited star (annihilation at 5.60 mm)
    measures 0.11-0.23 mm2 charged against the cited 0.21; the sharp star's
    core is the widest and is the fixture the recalibrated gate is proven on.

    Honest non-reproduction: the cited "2.94 mm bare disc" does not
    reproduce as a radius — every reconstruction measures 1.28-1.43 mm
    (this one: ~1.33). Defect 2's "silent on that 1.47 mm bare radius"
    refers to this same star, and 2.94 / 2 = 1.47, so the disc figure reads
    as a diameter; both this suite and the config block now say so.

    UPDATE 2026-08-04 (bare-core shrink, defect 1's own fix): `_rings` and
    the ledger's blindness are untouched by this fix — both asserted below
    exactly as before — but `_fill`'s FINAL output is not: it now runs
    through `_refine_terminal_generation` and the finishing pass too, so the
    bare-circle measurement at the end is the FIXED figure (~0.44), not the
    raw ~1.33 this test originally reproduced. That raw figure is still
    covered directly in `test_the_structural_centre_dot_is_machine_driven_
    not_shape_driven` and `test_a_shape_starved_of_rings_says_so`
    (test_contour.py) via `starved` still correctly firing on this shape.
    """
    inrad = shapely.maximum_inscribed_circle(STAR_SHARP, 1e-4).length
    assert inrad == pytest.approx(10.0, abs=0.02)

    gens = _rings(STAR_SHARP, machine.FILL_ROW_MM)
    deepest = (machine.FILL_ROW_MM * machine.CONTOUR_FIRST_INSET_FRAC
               + machine.FILL_ROW_MM * (len(gens) - 1))
    assert deepest < 0.55 * inrad, "the annihilation the defect describes"

    runs, report = _fill(STAR_SHARP)
    assert report["skipped_area_mm2"] < 0.01 * STAR_SHARP.area, \
        "the ledger must be blind here for the defect to be what was cited"
    bare = widest_bare_circle(STAR_SHARP, runs)
    assert 0.35 < bare.radius_mm < 0.55, \
        f"measured {bare.radius_mm:.3f}; post-fix this star still clears " \
        f"starved_threshold_mm (0.33) but no longer the pre-fix 1.2-1.5 class"


def test_the_cited_stars_own_readings():
    """The ratio-0.50 star is the one whose raw mitred buffer dies nearest the
    cited 5.60 mm. Its ledger charge matches the citation (~0.21 mm2); its
    measured bare radius is ~0.53 before any fix — small, because at this
    notch angle the mitre spikes stay under the limit and the resampled
    rings ride them nearly to the centre. The wide-core behaviour the
    citation describes lives in the sharper star above.

    UPDATE 2026-08-04 (bare-core shrink): `starved` flips to 1 here, and
    that is the recalibration working as intended, not a regression. The
    verdict was 0 only because the OLD threshold (1.07, from the un-shrunk
    0.87 mm structural dot) was too coarse to tell this shape's ~0.42-0.53 mm
    residual apart from a healthy disc's own dot. Post-fix a healthy disc
    reads ~0.07-0.13 mm (CONTOUR_BARE_CORE_MM = 0.13) and the threshold
    tightens to 0.33 with it, so this star's own residual — reduced by the
    fix, from ~0.53 to ~0.42, but not eliminated — is now correctly told
    apart from a healthy shape's floor instead of hiding under a threshold
    that could not resolve either one.
    """
    d = machine.FILL_ROW_MM * machine.CONTOUR_FIRST_INSET_FRAC
    while True:
        g = STAR_CITED.buffer(-d, join_style=2,
                              mitre_limit=machine.CONTOUR_MITRE_LIMIT)
        parts = [p for p in getattr(g, "geoms", [g])
                 if p.geom_type == "Polygon"
                 and p.area >= machine.CONTOUR_MIN_RING_AREA_MM2]
        if not parts:
            break
        d += machine.FILL_ROW_MM
    assert d == pytest.approx(5.6, abs=0.3)

    runs, report = _fill(STAR_CITED)
    assert report["skipped_area_mm2"] < 0.5
    assert report["starved"] == 1
    assert widest_bare_circle(STAR_CITED, runs).radius_mm == pytest.approx(0.42, abs=0.05)


# --- The structural centre dot and the threshold derived from it -------------

@pytest.mark.parametrize("name,poly,expected", [
    ("disc3", _circle(3.0), 0.067), ("disc5", _circle(5.0), 0.070),
    ("disc15", _circle(15.0), 0.067), ("dumbbell", DUMBBELL, 0.129),
])
def test_the_structural_centre_dot_is_machine_driven_not_shape_driven(name, poly, expected):
    """CONTOUR_BARE_CORE_MM's provenance. Discs of three sizes and the
    dumbbell — four shapes with nothing in common but the machine constants —
    all leave the same 0.863 mm bare dot where their deepest ring died. That
    invariance is what makes it a structural residue the gate must tolerate,
    and the measurement is what the threshold is derived from.

    UPDATE 2026-08-04 (bare-core shrink): 0.863 -> ~0.07-0.13 mm.
    `_refine_terminal_generation` + the finishing pass close most of the dot
    for all four; the three discs still land within 0.003 mm of each other
    (0.067-0.070, as machine-driven as before), but the dumbbell is
    genuinely a little higher (0.129) — not noise, but its own three
    convergence points (both lobe centres and the waist) needing TWO
    finishing patches to close where a disc needs one, so it does not
    shrink all the way to the disc floor. CONTOUR_BARE_CORE_MM (0.13) is
    still derived from the measured MAX across all four, same convention as
    the original 0.87 (0.863 measured) used.
    """
    runs, _report = _fill(poly)
    bare = widest_bare_circle(poly, runs)
    assert bare.radius_mm == pytest.approx(expected, abs=0.02)
    assert bare.radius_mm <= machine.CONTOUR_BARE_CORE_MM + 0.01


def test_the_threshold_is_the_dot_plus_half_a_ring_spacing():
    """0.33 mm at the shipped 0.40 mm spacing (2026-08-04: was 1.07, from the
    un-shrunk 0.87 mm dot): the measured structural dot (0.13) plus half a
    spacing — fire only when the core is a full ring spacing wider in
    diameter than what every healthy shape already leaves. The spacing terms
    scale, so an opened-up ring tier is judged against its own geometry
    rather than tatami's."""
    assert starved_threshold_mm(0.40) == pytest.approx(0.33, abs=1e-9)
    assert starved_threshold_mm(1.20) == pytest.approx(
        machine.CONTOUR_BARE_CORE_MM + 0.8 + 0.6, abs=1e-9)


# --- Both miscalibration directions, fixed and proven ------------------------

def test_starved_now_fires_where_the_area_gate_was_silent():
    """Direction 1: the star's annihilated core. The old gate summed KNOWN
    drops (0.2 % of area here — silent); the widest bare spot was 1.33 mm
    before the 2026-08-04 bare-core shrink (double the OLD 0.87 mm structural
    dot) and is ~0.44 mm after it (more than triple the NEW 0.13 mm dot) —
    still comfortably past `starved_threshold_mm`, so the recalibrated gate
    fires either way; only the absolute numbers moved."""
    _runs, report = _fill(STAR_SHARP)
    assert report["skipped_area_mm2"] < 0.01 * STAR_SHARP.area, \
        "old gate: silent"
    assert report["bare_radius_mm"] > starved_threshold_mm(machine.FILL_ROW_MM)
    assert report["starved"] == 1


def test_starved_is_now_silent_where_the_area_gate_cried_wolf():
    """Direction 2: a small disc. Its one structural centre drop is 8.9 % of
    its area — the old 1 % gate fired on an ordinary healthy shape — while
    the widest bare spot is exactly the dot every disc leaves. Silent now."""
    poly = _circle(3.0)
    _runs, report = _fill(poly)
    assert report["skipped_area_mm2"] > 0.01 * poly.area, "old gate: fired"
    assert report["bare_radius_mm"] < starved_threshold_mm(machine.FILL_ROW_MM)
    assert report["starved"] == 0


def test_the_cited_0_51_false_alarm_is_the_fixture_logos_own(whitebg):
    """The config block's "firing on 0.51 mm elsewhere", found: whitebg's
    Sf5200f3f measures 0.499 mm bare under contour while its known drops sum
    to 1.7 % of its area — the old gate fired, the recalibrated one is
    silent. (Sb253ebba, at 0.644, is the same class: old fire, new silent —
    its bare spot is smaller than a healthy disc's own centre dot.)

    UPDATE 2026-08-04 (bare-core shrink): both figures cited above are
    pre-fix. Post-fix, `_refine_terminal_generation` + the finishing pass
    measure Sf5200f3f at 0.168 mm (was 0.499) and Sb253ebba at 0.154 mm (was
    0.644) — both still comfortably under the recalibrated
    `starved_threshold_mm` (0.33 at shipped spacing), same as before the
    shrink, just closer to it in absolute terms since the healthy floor
    moved too.
    """
    for shape_id, cited in (("Sf5200f3f", 0.168), ("Sb253ebba", 0.154)):
        p, row, fabric = _logo_shape(whitebg, shape_id)
        _runs, report = contour_fill(p.polygon, p.shape_id, spacing_mm=row,
                                     stitch_mm=machine.FILL_STITCH_MM,
                                     underlay_style=fabric.fill_underlay,
                                     trim_at_mm=fabric.trim_at_mm)
        assert report["skipped_area_mm2"] > 0.01 * p.polygon.area, \
            f"{shape_id}: the old gate fired here"
        assert report["bare_radius_mm"] == pytest.approx(cited, abs=0.03)
        assert report["starved"] == 0
