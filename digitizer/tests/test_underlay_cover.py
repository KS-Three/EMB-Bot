"""tools/underlay_cover: back stitching read off the stitches, by one rule.

Synthetic runs, so each case has one answer: a run sewn under a column is
back stitching, a column alone is not, a hole down the middle of a stroke
is interior and one on a rail is not, and the three patterns are told
apart by their own geometry -- including this engine's ladder-shaped satin
zigzag, which the column detector cannot see.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from tools import underlay_cover as uc


def column(x0: float, x1: float, y0: float, y1: float, pitch: float = 0.4):
    """A satin column along x between the rails y0 and y1."""
    pts = []
    n = int((x1 - x0) / pitch)
    for i in range(n + 1):
        x = x0 + i * pitch
        pts.append((x, y0 if i % 2 == 0 else y1))
    return pts


def centre_run(x0: float, x1: float, y: float, step: float = 2.5):
    n = max(2, int(math.ceil((x1 - x0) / step)))
    return [(x0 + (x1 - x0) * i / n, y) for i in range(n + 1)]


def sawtooth(x0: float, x1: float, y0: float, y1: float, pitch: float = 1.5):
    return column(x0, x1, y0, y1, pitch)


def ladder(x0: float, x1: float, y0: float, y1: float, walk: float = 1.45):
    """Cross, walk along the rail, cross back: the engine's satin zigzag underlay."""
    pts = []
    x = x0
    i = 0
    while x <= x1:
        if i % 2 == 0:
            pts.extend([(x, y0), (x, y1)])
        else:
            pts.extend([(x, y1), (x, y0)])
        x += walk
        i += 1
    return pts


def rows(x0: float, x1: float, y0: float, y1: float, spacing: float = 2.0, step: float = 3.0):
    """Lattice rows: straight runs that turn back at the ends."""
    pts = []
    y = y0
    forward = True
    while y <= y1:
        xs = np.arange(x0, x1 + 1e-9, step)
        if not forward:
            xs = xs[::-1]
        pts.extend((float(x), y) for x in xs)
        y += spacing
        forward = not forward
    return pts


def test_a_run_under_a_column_is_back_stitching_and_the_column_is_not():
    # Two passes (a trim between them): one pass would add a 30 mm hop from
    # the run's end back to the column's start, and that hop is sewn under
    # the column too.
    runs = [{"block": 0, "pts": centre_run(0, 30, 2.0)}, {"block": 0, "pts": column(0, 30, 0.0, 4.0)}]
    rep = uc.measure(runs)
    w = rep["whole"]
    assert rep["back_pieces"] == 1
    assert 25 <= w["back_thread_mm"] <= 31          # the 30 mm centre run and nothing else
    assert w["back_by_pattern_mm"]["running"] == pytest.approx(w["back_thread_mm"])
    assert w["back_by_pattern_mm"]["zigzag"] == 0
    # The column's thread sits on the run where they cross: a 0.4 mm thread
    # across a 4 mm column is a tenth of each cross, give or take the raster.
    assert 0.04 <= w["top_support"] <= 0.25


def test_a_column_alone_has_no_back_stitching_and_no_support():
    rep = uc.measure([{"block": 0, "pts": column(0, 30, 0.0, 4.0)}])
    assert rep["back_pieces"] == 0
    assert rep["whole"]["back_thread_mm"] == 0
    assert rep["whole"]["top_support"] == 0


def test_interior_holes_are_the_ones_off_the_rails():
    run = centre_run(3, 27, 2.0)         # inside the column's ends too
    col = column(0, 30, 0.0, 4.0)
    rep = uc.measure([{"block": 0, "pts": run}, {"block": 0, "pts": col}])
    w = rep["whole"]
    # Every centre-run hole is 2 mm inside the column; every rail hole is on
    # the sewn area's edge (within a thread width of it).
    assert w["interior_back"] == len(run)
    assert w["interior_top"] == 0


@pytest.mark.parametrize("maker, expect", [
    (lambda: centre_run(0, 40, 0.0), "running"),
    (lambda: sawtooth(0, 40, 0.0, 3.0), "zigzag"),
    (lambda: ladder(0, 40, 0.0, 3.0), "zigzag"),
    (lambda: rows(0, 30, 0.0, 10.0), "lattice"),
])
def test_pattern_of_reads_the_three_shapes(maker, expect):
    assert uc.pattern_of(maker()) == expect


def test_the_ladder_is_a_zigzag_even_though_the_column_detector_is_blind_to_it():
    from tools.satin_columns import _crosses
    pts = ladder(0, 40, 0.0, 3.0)
    inside, _ = _crosses(pts)
    assert inside.mean() < 0.5, "the column detector should NOT see a ladder (that is the point of the two-rail rule)"
    assert uc.pattern_of(pts) == "zigzag"


def test_a_crop_reports_one_band_and_the_blocks_report_each_colour():
    top = [{"block": 0, "pts": centre_run(0, 30, 2.0)}, {"block": 0, "pts": column(0, 30, 0.0, 4.0)}]
    bottom = [{"block": 1, "pts": column(0, 30, 20.0, 24.0)}]
    rep = uc.measure(top + bottom, crop=(0.5, 1.0))
    assert set(rep["by_block"]) == {"0", "1"}
    assert rep["by_block"]["0"]["back_thread_mm"] > 0
    assert rep["by_block"]["1"]["back_thread_mm"] == 0
    assert rep["crop"]["back_thread_mm"] == 0
    assert rep["crop"]["penetrations"] == len(bottom[0]["pts"])


def test_runs_from_design_reads_our_own_design_dict():
    # 0.1 mm units, y-UP in a Design; a jump and a trim end a pass.
    stitches = [{"x": 0, "y": 0, "type": "jump"}]
    for i in range(6):
        stitches.append({"x": i * 10, "y": 0 if i % 2 == 0 else 30, "type": "stitch"})
    stitches.append({"x": 50, "y": 30, "type": "trim"})
    for i in range(4):
        stitches.append({"x": 100 + i * 10, "y": 0, "type": "stitch"})
    stitches.append({"x": 130, "y": 0, "type": "end"})
    design = {"stitches": stitches, "colors": [{"r": 0, "g": 0, "b": 0}]}
    runs = uc.runs_from_design(design)
    assert [len(r["pts"]) for r in runs] == [6, 4]
    assert runs[0]["pts"][1] == pytest.approx((1.0, -3.0))   # y flipped to the file's frame, mm
