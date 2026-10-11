"""`cfg.fill_inside_satin_border` -- defect 5, one misroute class, DEFAULT OFF.

The misroute, on real art: `becker_marine_logo`'s BECKER letters sit inside
the black outline band, which sews satin. Against all four committed Becker
pro files the pro tatamis those letter bodies and satins MARINE's solid
letters -- the same stroke width -- while we satined both. Containment
separates them where no width or aspect threshold does (defect 26's
thresholds are a measured negative, DOCTRINE): every BECKER body lies wholly
inside the band's outline, every MARINE letter wholly outside it.

Measured 2026-10-08 with `tools/pro_parity` against the four committed Becker
pro files, chance-corrected sttype only (unclamped kappa off scorecard's own
cells and floor; raw is not quoted, ROADMAP gate 4), OFF -> ON:
chest_small -0.009 -> 0.033, hat_large -0.077 -> -0.032, hat_small
0.029 -> 0.095, lc_large -0.052 -> -0.050. Mean -0.027 -> +0.012: off the
floor, still near chance. Pinned here at lc_large's pro width (95.7 mm).
"""
from __future__ import annotations

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import _fill_inside_satin_border, digitize
from tests.conftest import TESTDATA

ART = TESTDATA / "becker_marine_logo.png"
KW = dict(target_width_mm=95.7, garment_id="left_chest")


def _kinds(plan) -> dict[str, set]:
    out: dict[str, set] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id:
            out.setdefault(run.shape_id, set()).add(str(run.kind))
    return out


def _points(plan) -> list:
    return [tuple(map(tuple, r.points)) for _b, r in plan.iter_runs()]


def _band_and_bodies(regions):
    """The outline band (largest holed region) and what lies inside it."""
    band = max((r for r in regions
                if r.polygon.geom_type == "Polygon" and r.polygon.interiors),
               key=lambda r: r.area_mm2)
    outline = Polygon(band.polygon.exterior)
    inside = {r.shape_id for r in regions if r is not band
              and r.polygon.intersection(outline).area >= 0.9 * r.polygon.area}
    return band, inside


def test_the_flag_is_off_by_default():
    """ROADMAP gate 3: a default-OFF tier is not flipped without Kent."""
    assert PipelineConfig().fill_inside_satin_border is False


def test_off_is_byte_identical_on_the_art_the_flag_moves():
    _r1, p1 = digitize(ART, PipelineConfig(**KW))
    _r2, p2 = digitize(ART, PipelineConfig(**KW, fill_inside_satin_border=False))
    assert _points(p1) == _points(p2)


def test_on_routes_the_becker_bodies_fill_and_leaves_marine_alone():
    """The misrouted region, pinned on the stitches: OFF, BECKER's bodies
    carry satin; ON, none of them do, and nothing outside the band moves."""
    r_off, off = digitize(ART, PipelineConfig(**KW))
    _r_on, on = digitize(ART, PipelineConfig(**KW, fill_inside_satin_border=True))
    band, bodies = _band_and_bodies(r_off.regions)
    k_off, k_on = _kinds(off), _kinds(on)

    satined_bodies = {s for s in bodies if "satin" in k_off.get(s, set())}
    assert len(satined_bodies) >= 2, \
        f"the misroute this flag exists for: {sorted(satined_bodies)}"
    still = {s for s in bodies if "satin" in k_on.get(s, set())}
    assert not still, f"bodies inside the satin band still satin: {sorted(still)}"

    assert "satin" in k_on.get(band.shape_id, set()), "the border stays satin"
    outside = set(k_off) - bodies - {band.shape_id}
    assert outside, "MARINE's letters must be in the plan"
    # Routing only: a travel run may move when sequencing reorders around
    # the re-routed bodies, which is not a satin/fill decision.
    def route(k, s):
        return k.get(s, set()) & {"satin", "fill"}
    assert {s: route(k_off, s) for s in outside} == \
        {s: route(k_on, s) for s in outside}


def test_a_per_shape_override_wins_and_the_input_is_not_mutated():
    r, _p = digitize(ART, PipelineConfig(**KW))
    _band, bodies = _band_and_bodies(r.regions)
    pinned = sorted(bodies)[0]
    regions = [type(x)(**{**x.__dict__, "meta": {**x.meta, "tier": "satin"}})
               if x.shape_id == pinned else x for x in r.regions]
    before = [dict(x.meta) for x in regions]
    out = _fill_inside_satin_border(regions, PipelineConfig(**KW), r.design_class)
    assert [dict(x.meta) for x in regions] == before
    tiers = {x.shape_id: x.meta.get("tier", "auto") for x in out}
    assert tiers[pinned] == "satin"
    assert all(tiers[s] == "fill" for s in bodies if s != pinned)
