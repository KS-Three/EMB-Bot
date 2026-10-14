"""The hairline line route on the GRADIENT lane, as a supplement
(`cfg.hairline_lines_gradient`, default OFF, 2026-10-14;
`stage6_hairline_lines.supplements` / `supplement_zone`, `stage7_sequence`).

The Studio sends owl_kent down `gradient`, where the line route never ran
(#915). With the flag on (and `hairline`, `hairline_from_lines`,
`hairline_lines_strand_test` all on), the region tier runs there as before
and the line route adds only the strands it laid nothing near. Every number
is a property of the file, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import json

import pytest
import shapely
from shapely.geometry import box

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.stage6_hairline_lines import (
    _SUPPLEMENT_COVERED_SHARE, applies, covered_share, is_stroke, strand_blocks, supplement_test,
    supplement_zone, supplements)
from tests.test_hairline_lines import _md5
from tests.test_hairline_lines_chain import _pair, _sp
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5

ALL = dict(hairline=True, hairline_from_lines=True, hairline_lines_strand_test=True,
           hairline_lines_gradient=True)


# --- OFF is byte-identical, and the flag needs all three others ---------------

def test_the_flag_defaults_off():
    assert PipelineConfig().hairline_lines_gradient is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_flag_alone_is_byte_identical_to_the_flat_golden(fixture):
    """#848's pins: the flag without the line route is inert."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _r, plan = digitize(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                       hairline_lines_gradient=True))
    assert _md5(plan) == GOLDEN_MD5[fixture]


@pytest.mark.parametrize("missing", ["hairline", "hairline_from_lines",
                                     "hairline_lines_strand_test", "hairline_lines_gradient"])
def test_any_one_flag_off_is_inert(missing):
    cfg = PipelineConfig(**dict(ALL, **{missing: False}))
    assert not supplements(cfg, "gradient")


def test_gradient_only_and_never_beside_the_photo_route():
    cfg = PipelineConfig(**ALL)
    assert supplements(cfg, "gradient")
    for cls in ("flat", "photo_subject", "photo_scene", None):
        assert not supplements(cfg, cls)
    # On a photo lane the route itself runs (and replaces the region tier).
    assert applies(cfg, "photo_scene") and not applies(cfg, "gradient")


# --- the zone and the share ------------------------------------------------------

class _SP:
    px_per_mm = 8.0


def test_the_zone_is_the_walked_shapes_grown_by_half_a_run_and_one_pixel():
    cfg = PipelineConfig(**ALL)
    zone = supplement_zone([box(0, 0, 1, 10)], _SP(), cfg)
    reach = 0.5 * machine.thread_profile(40).hairline_run_width_mm + 1.0 / 8.0
    assert zone.contains(shapely.Point(1.0 + reach - 0.01, 5.0))
    assert not zone.contains(shapely.Point(1.0 + reach + 0.01, 5.0))
    assert supplement_zone([], _SP(), cfg).is_empty


def test_covered_share_reads_the_length_inside():
    zone = box(0, 0, 5, 1)
    assert covered_share([(0, 0.5), (10, 0.5)], zone) == pytest.approx(0.5, abs=0.02)
    assert covered_share([(1, 0.5), (4, 0.5)], zone) == 1.0
    assert covered_share([(0, 5), (10, 5)], zone) == 0.0
    assert covered_share([(0, 5), (10, 5)], shapely.Polygon()) == 0.0


# --- strand_blocks: a refused line is not sewn, a free one is ---------------------

class _R:
    def __init__(self, sid, poly, thread):
        self.shape_id, self.polygon, self.thread_index = sid, poly, thread


def _blocks(regions=None, walked=()):
    cfg = PipelineConfig(**ALL)
    sp = _sp(_pair(40))
    refuse = None if regions is None else supplement_test(regions, set(walked), sp, cfg)
    return strand_blocks(sp, cfg, entry=None, trim_at_mm=machine.TRIM_AT_MM,
                         allowed_threads=[0], refuse=refuse)


def _first_box():
    b0, _r0 = _blocks()
    xs = [p[0] for p in b0[0][1][0].points]
    # A box over the first strand only (the pair are 5 mm apart).
    return box(min(xs) - 0.5, -100, max(xs) + 0.5, 100)


def _thread(lightness: str) -> int:
    """A chart index whose L* is the lightest / darkest."""
    from digitizer_core.threads import chart_for
    L = chart_for(PipelineConfig()).lab[:, 0]
    return int(L.argmax() if lightness == "light" else L.argmin())


def test_without_a_test_nothing_changes():
    _b, rep = _blocks()
    assert "refused_region" not in rep and "refused_own_tone" not in rep
    assert rep["strands"] == 2


def test_no_shapes_refuse_nothing():
    b0, _r0 = _blocks()
    b1, r1 = _blocks(regions=[])
    assert r1["refused_region"] == {"dark": 0, "light": 0}
    assert r1["refused_own_tone"] == {"dark": 0, "light": 0}
    assert [r.points for _t, rr in b1 for r in rr] == [r.points for _t, rr in b0 for r in rr]


def test_a_line_on_a_walked_shape_is_not_sewn():
    cover = _first_box()
    b1, r1 = _blocks(regions=[_R("s1", cover, _thread("light"))], walked=["s1"])
    assert r1["strands"] == 1 and sum(r1["refused_region"].values()) == 1
    sewn = [r.points for _t, rr in b1 for r in rr if r.kind == "run"]
    assert all(covered_share(p, cover) < _SUPPLEMENT_COVERED_SHARE for p in sewn)


def test_a_dark_line_on_a_dark_shape_is_line_art_and_not_sewn():
    """The bridge logo's case: the line's ink is already a shape of its tone."""
    _b, r1 = _blocks(regions=[_R("s1", _first_box(), _thread("dark"))])
    assert r1["strands"] == 1 and sum(r1["refused_own_tone"].values()) == 1


def test_a_dark_line_inside_a_wide_dark_fill_is_kept():
    """Own tone counts only on a STROKE shape: a strand the segmenter merged
    into a wide fill of its tone (owl_kent's white bristles in its white
    mass) is not line art."""
    wide = box(-100, -100, 100, 100)
    assert not is_stroke(wide) and is_stroke(_first_box())
    _b, r1 = _blocks(regions=[_R("s1", wide, _thread("dark"))])
    assert r1["strands"] == 2 and sum(r1["refused_own_tone"].values()) == 0


def test_a_dark_line_on_a_light_fill_is_a_strand_and_sewn():
    """The owl's case: a strand the fill under it does not carry."""
    _b, r1 = _blocks(regions=[_R("s1", box(-100, -100, 100, 100), _thread("light"))])
    assert r1["strands"] == 2 and sum(r1["refused_own_tone"].values()) == 0


# --- the pipeline: drawn hair on gradient ------------------------------------------

@pytest.fixture(scope="module")
def drawn():
    base = dict(target_width_mm=80.0)
    result = run_stages(TESTDATA / "synthetic" / "hair_strands.png", PipelineConfig(**base))
    assert result.design_class == "gradient"
    plans = {name: plan_stitches(result, PipelineConfig(**base, **kw)) for name, kw in {
        "region": dict(hairline=True),
        "no_test": dict(ALL, hairline_lines_strand_test=False),
        "supp": ALL}.items()}
    return plans


def test_without_the_strand_test_the_flag_is_inert_on_gradient(drawn):
    assert _md5(drawn["no_test"]) == _md5(drawn["region"])


def test_on_drawn_hair_the_supplement_adds_nothing(drawn):
    """#915's A/B bar 1: on drawn hair the region tier already sews every
    strand as a shape, so the supplement must not add any. Measured
    (tools/hairline_lines_gradient.py): every ridge line it keeps lies on a
    walked shape, and the plan is the region plan, byte for byte."""
    assert _md5(drawn["supp"]) == _md5(drawn["region"])
    w = next(w for w in drawn["supp"].warnings
             if w["code"] == "HAIRLINE_TIER_SEWN" and w.get("source") == "lines_gradient")
    assert w["strands"] == 0 and sum(w["refused_region"].values()) > 0
