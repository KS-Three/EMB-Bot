"""`cfg.extra["point_touch_split"]` (built OFF 2026-11-14): two shapes of one ink
touching at a point are two shapes.

NSYNC at 70.9 mm (eye sweep 2026-11-14, fault 11): the star's arm tip touches
the italic N at one point (a neck of about 0.05 mm), the two traced as one
region, and the column build fanned the N's top-left into spikes. Opened at
half `TOUCH_MAX_MM` the region parts into the N (125.5 mm2) and the star (19.0,
13% of the whole -- under the text tagger's 15% piece floor).
"""
from __future__ import annotations

from shapely.geometry import Polygon, box

from digitizer_core.config import PipelineConfig
from digitizer_core.point_touch import apply_point_touch_split
from digitizer_core.regions import Region


def _r(poly, sid="S1", **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=3, thread_number="0020",
                  area_mm2=poly.area, meta=dict(meta))


def _star_on_n(neck):
    """A 10 x 12 mm body with a 4 x 4 mm square touching its left edge
    through a neck `neck` mm tall (the star's arm tip)."""
    n = box(0, 0, 10, 12)
    arm = box(-0.6, 5.0, 0.0, 5.0 + neck)
    star = box(-4.6, 3.0, -0.6, 7.0)
    return n.union(arm).union(star)


def test_a_point_touch_parts_into_two_shapes():
    regions = [_r(_star_on_n(0.05), layer=1)]
    rows = apply_point_touch_split(regions)
    assert len(rows) == 1 and len(regions) == 2
    areas = sorted(round(r.area_mm2, 1) for r in regions)
    assert areas[0] >= 16.0 and areas[1] >= 120.0
    assert all(r.meta["point_touch_split_from"] == "S1" and r.meta["layer"] == 1 for r in regions)
    assert len({r.shape_id for r in regions}) == 2
    assert abs(sum(r.area_mm2 for r in regions) - _star_on_n(0.05).area) < 1e-6


def test_a_waist_is_not_a_touch():
    """A neck wider than `TOUCH_MAX_MM` (0.15) is the shape's own waist."""
    regions = [_r(_star_on_n(0.6))]
    assert apply_point_touch_split(regions) == [] and len(regions) == 1


def test_a_spike_is_not_a_piece():
    """What hangs off at a point must be a body itself, not a spike."""
    n = box(0, 0, 10, 12)
    spike = Polygon([(0, 5.0), (-3.0, 5.02), (0, 5.05)])
    regions = [_r(n.union(spike))]
    assert apply_point_touch_split(regions) == [] and len(regions) == 1


def test_lettering_and_rescued_details_are_left_alone():
    for meta in ({"text_cluster_id": "TC1"}, {"rescued_small_shape": True}, {"counter": True}):
        regions = [_r(_star_on_n(0.05), **meta)]
        assert apply_point_touch_split(regions) == [] and len(regions) == 1


def test_flag_is_off_by_default():
    assert not PipelineConfig().extra.get("point_touch_split")


def test_the_photo_lanes_never_call_it(monkeypatch):
    """Logos only (2026-11-15): MFab hat is classed `photo_scene`, and there
    the cut broke WELDING's W into a "~"; every corpus photo it ran on moved.
    The pipeline calls it on a flat design and never on a photo class."""
    from pathlib import Path

    from digitizer_core import point_touch
    from digitizer_core.pipeline import build_generation

    calls = []
    monkeypatch.setattr(point_touch, "apply_point_touch_split",
                        lambda regions: calls.append(len(regions)) or [])
    art = Path(__file__).resolve().parent.parent / "testdata" / "logo_whitebg.png"
    for forced, expect in (("photo_scene", 0), ("photo_subject", 0), ("flat", 1)):
        calls.clear()
        build_generation(art, PipelineConfig(target_width_mm=60.0, forced_class=forced,
                                             extra={"point_touch_split": True}))
        assert len(calls) == expect, forced
