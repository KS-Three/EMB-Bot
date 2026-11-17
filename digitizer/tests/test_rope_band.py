"""`cfg.rope_band` (built OFF 2026-11-17): a chain of rescued rope strands is
ONE band, so the satin tier sews it, and nothing else moves.

Hotel Fremont's hexagon rope is ~100 sub-floor strand blobs, each rescued and
sewn as its own run-stitch loop (prime grader scorecard 2026-11-17); the
pro sews one plain satin band. Hand-built here: who is a strand, what the
chain becomes, and that OFF is the plan as it was."""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core import rope_band as rb
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from tests.conftest import frozen_cfg

ON = frozen_cfg(extra={rb.KEY: True})
OFF = frozen_cfg()


def test_flag_default_is_on_and_the_frozen_engine_and_off_arm_are_off():
    """ON by default since 2026-11-17 (Kent "Flip ON (Recommended)"); the
    frozen snapshot and `conftest.ROPE_BAND_2026_11_17_OFF` keep the old engine."""
    from digitizer_core import PipelineConfig
    from tests.conftest import PRE_FLIP, ROPE_BAND_2026_11_17_OFF
    assert PipelineConfig().rope_band is True
    assert rb.enabled(PipelineConfig()) and not rb.enabled(OFF)
    assert ROPE_BAND_2026_11_17_OFF == {"rope_band": False} and PRE_FLIP["rope_band"] is False


def _pr(name, poly, **meta):
    m = {"layer": 1, "stitched": True, "rescued_small_shape": True, "dark_ink": True,
         "bean_letter_spines": [[0, 0]], "stitch_width_measured_mm": 0.5, **meta}
    r = Region(shape_id=name, polygon=poly, thread_index=3, thread_number="0862",
               area_mm2=poly.area, meta=m)
    return PlannedRegion(region=r, polygon=poly, sew_index=1)


def _rope(n=20, step=0.9, **meta):
    """n strands 1.2 x 0.7 mm in a row, 0.1 mm apart (a straight rope)."""
    return [_pr(f"R{i}", box(i * step, 0, i * step + 0.8, 1.2), **meta) for i in range(n)]


def test_off_returns_the_same_list():
    planned = _rope()
    assert rb.join(planned, OFF) == (planned, {})


def test_chain_becomes_one_band_with_strand_keys_removed():
    planned = _rope() + [_pr("Z", box(50, 50, 51, 51))]
    out, merged = rb.join(planned, ON)
    bands = [p for p in out if p.region.meta.get("rope_band") is not None]
    assert len(bands) == 1 and len(out) == 2        # band + the lone speck
    b = bands[0].region
    assert len(merged) == 19 and set(merged.values()) == {b.shape_id}
    assert b.polygon.geom_type == "Polygon" and not b.polygon.interiors
    assert b.polygon.bounds[0] <= 0.0 and b.polygon.bounds[2] >= 19 * 0.9 + 0.8 - 0.01
    for k in rb._STRAND_KEYS:                        # nothing that sends it to the bean tier
        assert k not in b.meta
    assert abs(b.area_mm2 - b.polygon.area) < 1e-9


def test_every_strand_area_is_inside_the_band():
    planned = _rope()
    out, _ = rb.join(planned, ON)
    band = out[0].region.polygon
    for p in planned:
        assert p.region.polygon.difference(band).area < 0.05 * p.region.polygon.area  # rounded corners only


def test_a_short_chain_is_left_alone():
    planned = _rope(n=rb.MIN_STRANDS - 1)
    assert rb.join(planned, ON)[0] == planned


def test_a_text_cluster_is_never_a_rope():
    planned = _rope(text_cluster_id="TC1")
    assert rb.join(planned, ON)[0] == planned


def test_a_big_piece_is_not_a_strand():
    planned = _rope()
    planned.append(_pr("Big", box(0, 2, 10, 4)))     # 20 mm2: a glyph piece, not a strand
    out, _ = rb.join(planned, ON)
    assert any(p.region.shape_id == "Big" for p in out)


def test_two_threads_do_not_chain():
    planned = _rope(n=10)
    for p in planned[::2]:
        p.region.thread_index = 4
    assert rb.join(planned, ON)[0] == planned


def test_far_apart_strands_do_not_chain():
    planned = _rope(n=20, step=3.0)                  # 2.2 mm gaps
    assert rb.join(planned, ON)[0] == planned
