"""`tools/seam_underlap.py` — the seam instrument, pinned on two rectangles.

The rule it reads is stage 5's: the earlier colour reaches `pull + overlap_mm`
under the later one along their shared boundary; same-thread neighbours get
no underlap at all; regions that do not touch share no seam.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.fabrics import fabric_for_garment  # noqa: E402
from digitizer_core.regions import Region  # noqa: E402
from digitizer_core.stage5_overlap import resolve_overlaps  # noqa: E402
from seam_underlap import measure  # noqa: E402


def _region(shape_id, poly, thread_index, layer):
    return Region(shape_id=shape_id, polygon=poly, thread_index=thread_index,
                  thread_number=str(thread_index), area_mm2=poly.area, source="test",
                  meta={"layer": layer})


def _plan(regions, overlap_mm=0.25, garment="left_chest"):
    cfg = PipelineConfig(overlap_mm=overlap_mm)
    fabric = fabric_for_garment(garment)
    planned, _ = resolve_overlaps(regions, fabric, cfg)
    return measure(regions, planned), fabric


def test_two_colours_share_a_seam_and_the_earlier_reaches_under_by_pull_plus_overlap():
    a = _region("A", box(0, 0, 10, 8), 5, 0)     # layer 0 sews first
    b = _region("B", box(10, 0, 20, 8), 9, 1)
    m, fabric = _plan([a, b])
    assert len(m["pairs"]) == 1
    p = m["pairs"][0]
    assert p["earlier"] == "A" and p["later"] == "B"
    # B's sewn boundary on A's polygon: the 8 mm seam, B's pull growth top and
    # bottom, and the corner where A's own growth wraps B's edge.
    assert 8.0 <= p["shared_mm"] <= 10.5
    assert p["depth_mm"] == pytest.approx(fabric.pull_comp_mm + 0.25, abs=0.08)
    assert m["under"][1.0] == pytest.approx(p["shared_mm"], abs=0.01)   # 0.55 sits under the 1.0 rung
    assert m["under"][0.25] == 0.0


def test_overlap_zero_leaves_only_the_pull():
    a = _region("A", box(0, 0, 10, 8), 5, 0)
    b = _region("B", box(10, 0, 20, 8), 9, 1)
    m, fabric = _plan([a, b], overlap_mm=0.0)
    assert m["pairs"][0]["depth_mm"] == pytest.approx(fabric.pull_comp_mm, abs=0.08)


def test_same_thread_neighbours_are_reported_apart_and_get_no_depth():
    a = _region("A", box(0, 0, 10, 8), 5, 0)
    b = _region("B", box(10, 0, 20, 8), 5, 0)
    m, _ = _plan([a, b])
    assert m["pairs"] == []
    assert m["same_thread_pairs"] == 1
    assert m["same_thread_mm"] == pytest.approx(8.0, abs=0.7)


def test_regions_that_do_not_touch_share_no_seam():
    a = _region("A", box(0, 0, 10, 8), 5, 0)
    b = _region("B", box(12, 0, 22, 8), 9, 1)
    m, _ = _plan([a, b])
    assert m["pairs"] == [] and m["shared_mm"] == 0.0 and m["mean_depth_mm"] is None
