"""`cfg.lettering_min_column_mm` — widen rescued lettering to a sewable column
(plan §4d, `textcluster.regularize_text_clusters`).

The contract. None is today's pass, byte for byte (the flat goldens pin the
pipeline; the first test pins the function on the same regions). Set, the
target radius is at least half the SEWN floor less the fabric's pull, never
narrower than the cluster's own median: a door-1 cluster of 0.3 mm strokes
comes out about 0.6 mm wide in the artwork at a 1.0 mm floor on a 0.2 mm
fabric, and stage 5 then adds the pull back. Door 2 (ordinary lettering) is
untouched whatever the floor; a floor the pull swallows widens nothing; a
floor under the median is the plain pass. The pipeline hands the regularizer
the config's floor and the garment's pull.
"""
from __future__ import annotations

import inspect
from unittest.mock import patch

import numpy as np
import pytest

from digitizer_core import pipeline
from digitizer_core.config import PipelineConfig
from digitizer_core.textcluster import regularize_text_clusters

from .test_textcluster import _OCR_GATE_PATH, _P, _row, _stroke_mm_of

FLOOR_MM = 1.0        # Kent's pick: `stage6_satin.PHOTO_MIN_SATIN_WIDTH_MM`
PULL_MM = 0.2


def _door_one_cluster(prefix: str = "L", n: int = 5, w: float = 0.3):
    """A row of rescued 0.3 mm strokes tagged as one cluster at their own
    median half-width — the shape `keep_thin_strokes` hands this pass."""
    regions = _row(prefix, n, w=w)
    strokes = [_stroke_mm_of(r.polygon) for r in regions]
    assert all(s is not None for s in strokes)
    median = float(np.median(strokes))
    for r in regions:
        r.meta["text_cluster_id"] = "TCcol"
        r.meta["text_cluster_stroke_mm"] = median
    return regions, median


def _widths(regions) -> list[float]:
    return [float(r.polygon.bounds[2] - r.polygon.bounds[0]) for r in regions]


def test_none_is_todays_pass_byte_for_byte():
    a, _ = _door_one_cluster()
    b, _ = _door_one_cluster()
    with patch(_OCR_GATE_PATH, return_value=False):
        regularize_text_clusters(a, _P)
        regularize_text_clusters(b, _P, min_column_mm=None, pull_mm=PULL_MM)
    assert [list(r.polygon.exterior.coords) for r in a] == [list(r.polygon.exterior.coords) for r in b]
    assert [r.meta for r in a] == [r.meta for r in b]


def test_the_floor_widens_a_thin_cluster_to_the_column_less_the_pull():
    regions, median = _door_one_cluster()
    before = _widths(regions)
    assert max(before) < 0.4
    with patch(_OCR_GATE_PATH, return_value=False):
        regularize_text_clusters(regions, _P, min_column_mm=FLOOR_MM, pull_mm=PULL_MM)
    target_radius = FLOOR_MM / 2.0 - PULL_MM              # 0.3 mm of artwork radius
    assert target_radius > median
    widened = [r for r in regions if r.meta.get("text_cluster_widened_mm")]
    assert widened, [r.meta.get("text_cluster_regularize_skip_reason") for r in regions]
    for r in widened:
        assert r.meta["text_cluster_widened_mm"] == pytest.approx(target_radius - median, abs=1e-3)
        w = r.polygon.bounds[2] - r.polygon.bounds[0]
        assert 2 * target_radius * 0.85 <= w <= 2 * target_radius * 1.25, w
        assert r.area_mm2 == pytest.approx(r.polygon.area)
        assert _stroke_mm_of(r.polygon) == pytest.approx(target_radius, rel=0.2)


def test_a_floor_the_pull_swallows_widens_nothing():
    a, _ = _door_one_cluster()
    b, _ = _door_one_cluster()
    with patch(_OCR_GATE_PATH, return_value=False):
        regularize_text_clusters(a, _P)
        regularize_text_clusters(b, _P, min_column_mm=FLOOR_MM, pull_mm=FLOOR_MM / 2.0)
    assert [list(r.polygon.exterior.coords) for r in a] == [list(r.polygon.exterior.coords) for r in b]
    assert not any(r.meta.get("text_cluster_widened_mm") for r in b)


def test_a_floor_under_the_median_is_the_plain_pass():
    a, median = _door_one_cluster()
    b, _ = _door_one_cluster()
    with patch(_OCR_GATE_PATH, return_value=False):
        regularize_text_clusters(a, _P)
        regularize_text_clusters(b, _P, min_column_mm=median, pull_mm=0.0)   # radius floor = median / 2
    assert [list(r.polygon.exterior.coords) for r in a] == [list(r.polygon.exterior.coords) for r in b]


def test_door_two_lettering_is_untouched_whatever_the_floor():
    regions, median = _door_one_cluster()
    for r in regions:
        r.meta["text_cluster_all_rescued"] = False          # an ordinary glyph in the cluster
    before = [list(r.polygon.exterior.coords) for r in regions]
    with patch(_OCR_GATE_PATH, return_value=False):
        regularize_text_clusters(regions, _P, min_column_mm=FLOOR_MM, pull_mm=PULL_MM)
    assert [list(r.polygon.exterior.coords) for r in regions] == before
    assert all(r.meta.get("text_cluster_regularize_skip_reason") == "cluster_not_all_rescued"
               for r in regions)


def test_the_pipeline_hands_the_pass_the_floor_and_the_garments_pull():
    src = inspect.getsource(pipeline.build_generation)
    assert "min_column_mm=cfg.lettering_min_column_mm" in src
    assert "pull_mm=fabric_for(cfg).pull_comp_mm" in src
    assert PipelineConfig().lettering_min_column_mm is None
    sig = inspect.signature(regularize_text_clusters)
    assert sig.parameters["min_column_mm"].default is None
    assert sig.parameters["pull_mm"].default == 0.0
