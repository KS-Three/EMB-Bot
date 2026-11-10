"""`cfg.blend_shade_median` (built OFF 2026-11-09): MASTER_SCOPE defect 28, the
last gradient-lane thread block that is not the photo stub.

`summit_badge`'s background is one region with a per-region radial ramp. Its
t = 1 bucket holds 9 of 2,500 samples; the mean of those snaps to `0111` (a
mid grey, L* 48.8) for a band whose artwork is L* 30, a 21.5 dE00 block. The
median of the same samples is L* 29.5 and snaps to `0134`. What is pinned:

* OFF (the default) is the mean, byte for byte, so nothing moves unflagged.
* ON, a bucket with outliers reads its median; a clean bucket reads the same
  either way.
* The flag has one reader, the per-region path in `stage6_blend.blend_fill`.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core.stage6_blend import _shade_lab_colors


def _ramp_with_speckled_end():
    ts = np.concatenate([np.linspace(0.0, 0.8, 200), np.full(9, 1.0)])
    lab = np.tile(np.array([30.0, 0.5, 2.0]), (len(ts), 1))
    lab[-3:, 0] = 80.0            # 3 bright speckle samples in the end bucket
    return ts, lab


def test_default_is_off():
    assert PipelineConfig().blend_shade_median is False


def test_off_is_the_mean():
    ts, lab = _ramp_with_speckled_end()
    out = _shade_lab_colors(ts, lab, 5)
    assert out[-1][0] == lab[-9:, 0].mean()
    assert out[-1][0] > 40.0      # pulled up by the speckle


def test_on_reads_the_median_of_a_speckled_bucket():
    ts, lab = _ramp_with_speckled_end()
    out = _shade_lab_colors(ts, lab, 5, median=True)
    assert out[-1][0] == 30.0


def test_clean_buckets_agree():
    ts = np.linspace(0.0, 1.0, 300)
    lab = np.column_stack([100.0 - 60.0 * ts, np.zeros_like(ts), np.zeros_like(ts)])
    a = _shade_lab_colors(ts, lab, 4)
    b = _shade_lab_colors(ts, lab, 4, median=True)
    for x, y in zip(a, b):
        assert abs(x[0] - y[0]) < 1.0


def test_empty_bucket_falls_back_to_the_overall_mean():
    ts = np.array([0.0, 0.1, 0.2])
    lab = np.array([[10.0, 0, 0], [20.0, 0, 0], [30.0, 0, 0]])
    for med in (False, True):
        out = _shade_lab_colors(ts, lab, 5, median=med)
        assert out[-1][0] == 20.0


def test_one_reader():
    src = Path(__file__).resolve().parent.parent / "digitizer_core"
    hits = [p.name for p in src.glob("*.py")
            if re.search(r"\.blend_shade_median\b", p.read_text(encoding="utf-8"))]
    assert hits == ["stage6_blend.py"]
