"""`tools/ground_clip.band_stats` -- the reading behind the 2026-09-16 finding
that stage 5's earlier-colour clip takes a lettering column's pull back.

Geometry only; the pipeline half of the tool is exercised by running it.
"""
from __future__ import annotations

import pytest
from shapely.geometry import box

from tools.ground_clip import band_stats

PULL = 0.3


def test_a_bar_in_a_ground_hole_that_was_clipped_back_keeps_none_of_its_band():
    bar = box(0.0, 0.0, 0.4, 5.0)
    ground = box(-2.0, -2.0, 2.4, 7.0).difference(bar)
    s = band_stats(bar, bar, PULL, ground)
    assert s["kept"] == pytest.approx(0.0, abs=1e-9)
    assert s["to_ground"] == pytest.approx(1.0, abs=1e-6)


def test_a_bar_on_bare_cloth_keeps_its_whole_band():
    bar = box(0.0, 0.0, 0.4, 5.0)
    s = band_stats(bar, bar.buffer(PULL), PULL, None)
    assert s["kept"] == pytest.approx(1.0, abs=1e-6)
    assert s["to_ground"] == 0.0


def test_a_loss_not_on_an_earlier_colour_is_not_charged_to_the_ground():
    bar = box(0.0, 0.0, 0.4, 5.0)
    # grown only on one side; the lost side lies over bare cloth
    grown = bar.union(box(-PULL, 0.0, 0.0, 5.0))
    far_ground = box(10.0, 10.0, 12.0, 12.0)
    s = band_stats(bar, grown, PULL, far_ground)
    assert 0.3 < s["kept"] < 0.6
    assert s["to_ground"] == 0.0


def test_zero_pull_has_no_band_to_lose():
    bar = box(0.0, 0.0, 0.4, 5.0)
    s = band_stats(bar, bar, 0.0, box(-1, -1, 1, 6))
    assert (s["kept"], s["to_ground"]) == (1.0, 0.0)


def test_width_proxy_reads_a_thin_bar_true():
    s = band_stats(box(0.0, 0.0, 0.4, 5.0), box(-0.3, 0.0, 0.7, 5.0), PULL, None)
    assert s["art_w"] == pytest.approx(0.4, rel=0.1)
    assert s["grown_w"] == pytest.approx(1.0, rel=0.2)
