"""`cfg.text_cluster_mixed_caps` (built OFF 2026-11-17): a line set in two cap
heights is still a word.

The TOAT badge's "To A T" (hat, 89.5 mm): two T's 11.9 mm tall, an o 7.2 mm and
an A 7.7 mm. The letter door links two glyphs only within `LETTER_HEIGHT_RATIO`
(0.8) of each other's height, so the T's pair (1.0), the o and A pair (0.94),
the T and A do not (0.65), and no pair reaches `MIN_CLUSTER_MEMBERS`: nothing
tags, the column lane never sees the row, and the small A sews as the generic
satin's three patches with its counter shut. ON, the glyphs no cluster took
cluster once more at `HEIGHT_BAND_MIN` (0.6). OFF is the tagger as it was.
"""
from __future__ import annotations

from shapely.geometry import Polygon, box

from digitizer_core import textcluster as tc
from digitizer_core.regions import Region


def _t(x: float, h: float = 11.9, w: float = 7.5, stroke: float = 1.0) -> Polygon:
    bar = box(x, 0.0, x + w, 1.9)
    stem = box(x + (w - stroke) / 2, 0.0, x + (w + stroke) / 2, h)
    return bar.union(stem)


def _o(x: float, h: float = 7.2, w: float = 6.3, stroke: float = 1.0) -> Polygon:
    return box(x, 4.7, x + w, 4.7 + h).difference(box(x + stroke, 4.7 + stroke, x + w - stroke, 4.7 + h - stroke))


def _a(x: float, h: float = 7.7, w: float = 5.2, stroke: float = 1.1) -> Polygon:
    outer = Polygon([(x, 4.2 + h), (x + w * 0.3, 4.2), (x + w * 0.7, 4.2), (x + w, 4.2 + h),
                     (x + w - stroke, 4.2 + h), (x + w * 0.5 + 0.2, 4.2 + h - 2.5),
                     (x + w * 0.5 - 0.2, 4.2 + h - 2.5), (x + stroke, 4.2 + h)])
    return outer.union(box(x + 1.0, 4.2 + h - 2.4, x + w - 1.0, 4.2 + h - 1.2))


def _row():
    shapes = [_t(0.0), _o(10.0), _a(19.0), _t(28.0)]
    return [Region(f"S{i}", p, 3, "3", p.area) for i, p in enumerate(shapes)]


def _tags(regions):
    return {r.shape_id: r.meta.get("text_cluster_id") for r in regions}


def test_the_row_pairs_at_the_door_and_tags_nothing_off():
    regions = _row()
    tc.detect_text_clusters(regions, None, part_touching=True)
    assert not any(_tags(regions).values()), _tags(regions)


def test_the_row_tags_as_one_line_on():
    regions = _row()
    tc.detect_text_clusters(regions, None, part_touching=True, mixed_caps=True)
    tags = _tags(regions)
    assert all(tags.values()) and len(set(tags.values())) == 1, tags


def test_on_reaches_every_branch_of_the_round():
    for kw in ({}, {"part_touching": True}, {"part_touching": True, "nest_door_aspect": True},
               {"nest_door_aspect": True}):
        regions = _row()
        tc.detect_text_clusters(regions, None, mixed_caps=True, **kw)
        assert all(_tags(regions).values()), (kw, _tags(regions))


def test_two_heights_that_are_no_line_stay_apart_on():
    """0.6 is the floor: a 4.0 mm glyph beside 11.9 mm ones (0.34) never joins."""
    shapes = [_t(0.0), _t(28.0), _o(10.0, h=4.0, w=3.5)]
    regions = [Region(f"S{i}", p, 3, "3", p.area) for i, p in enumerate(shapes)]
    tc.detect_text_clusters(regions, None, part_touching=True, mixed_caps=True)
    assert not any(_tags(regions).values()), _tags(regions)


def test_a_group_that_tagged_keeps_its_members_on():
    """Three equal letters tag with or without the flag, and the odd-height
    letter beside them is not pulled in by it (it is one candidate, not three)."""
    shapes = [_t(0.0), _t(10.0), _t(20.0), _o(30.0)]
    base = [Region(f"S{i}", p, 3, "3", p.area) for i, p in enumerate(shapes)]
    on = [Region(f"S{i}", p, 3, "3", p.area) for i, p in enumerate(shapes)]
    tc.detect_text_clusters(base, None, part_touching=True)
    tc.detect_text_clusters(on, None, part_touching=True, mixed_caps=True)
    assert _tags(base) == _tags(on)


def test_the_config_field_defaults_off_and_the_frozen_engine_pins_it():
    import json
    from pathlib import Path
    from digitizer_core import PipelineConfig
    assert PipelineConfig().text_cluster_mixed_caps is False
    pinned = json.loads((Path(__file__).parent / "engine_2026_10_27.json").read_text(encoding="utf-8"))
    assert pinned["text_cluster_mixed_caps"] is False
