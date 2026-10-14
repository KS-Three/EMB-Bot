"""`tools/detail_vs_lines.py`: detail_layer vs hairline_from_lines (2026-10-14).

Measure only; core is untouched. The full census takes tens of minutes on
`owl_kent` and lives in the PR body. What is pinned here is what makes its
numbers mean what they say:

- each arm turns on exactly the flags the PR names, and `off` turns on none;
- the overlap metric: a strand on the other route's centreline is shared, one
  a thread-width-and-a-bit off it is not, and the share is by LENGTH;
- one real row on a small drawn fixture forced down the photo lane: the two
  routes find the same dark line, so the line route's dark strand and the
  detail layer's bean line lie on top of each other, and the row's counts hold.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import machine  # noqa: E402
from tools import detail_vs_lines as D  # noqa: E402


def test_arm_flags():
    off = D.arm_cfg("off")
    assert (off.detail_layer, off.hairline, off.hairline_from_lines,
            off.hairline_lines_chain) == (False, False, False, False)
    d = D.arm_cfg("detail")
    assert (d.detail_layer, d.hairline, d.hairline_from_lines) == (True, False, False)
    ln = D.arm_cfg("lines")
    assert (ln.detail_layer, ln.hairline, ln.hairline_from_lines,
            ln.hairline_lines_chain) == (False, True, True, False)
    assert D.arm_cfg("lines_chain").hairline_lines_chain is True
    b = D.arm_cfg("both")
    assert (b.detail_layer, b.hairline, b.hairline_from_lines) == (True, True, True)
    for arm in D.ARMS:     # #882's route: photo lane forced, no rembg, 40 wt, 127 mm
        c = D.arm_cfg(arm)
        assert (c.forced_class, c.photo_prep, c.thread_wt, c.target_width_mm) == (
            "photo_subject", False, 40, 127.0)


def _line(x0, x1, y):
    n = int((x1 - x0) / 0.5)
    return [(x0 + (x1 - x0) * i / n, y) for i in range(n + 1)]


def test_overlap_is_by_length_and_inside_the_tolerance():
    detail = [{"pts": _line(0, 10, 0.0), "mm": 10.0},
              {"pts": _line(0, 10, 5.0), "mm": 10.0}]
    lines = [{"pts": _line(0, 10, 0.1), "mm": 10.0},          # on the first line
             {"pts": _line(0, 10, 5.0 + 3 * D.TOL_MM), "mm": 10.0},   # beside the second
             {"pts": _line(0, 10, 9.0), "mm": 10.0}]          # nowhere near
    ov = D.overlap(detail, lines)
    assert (ov["detail"]["shared"]["n"], ov["detail"]["only"]["n"]) == (1, 1)
    assert (ov["lines"]["shared"]["n"], ov["lines"]["only"]["n"]) == (1, 2)
    assert ov["lines"]["shared"]["mm"] == 10.0 and ov["detail"]["near_mm"] == 10.0
    # half of a strand on the other route's line is partial, and half its length near
    half = [{"pts": _line(0, 10, 0.0)[:11] + _line(5.0, 10, 4.0), "mm": 10.0}]
    sh = D.near_share(half[0]["pts"], D._tree(detail))
    assert 0.3 < sh < 0.75 and D.classify(sh) == "partial"


def test_a_missing_route_reads_as_no_overlap():
    assert D.near_share(_line(0, 5, 0), None) == 0.0
    ov = D.overlap([{"pts": _line(0, 5, 0), "mm": 5.0}], [])
    assert ov["detail"]["only"]["n"] == 1 and ov["lines"]["n"] == 0


def test_one_real_row_the_routes_find_the_same_dark_lines():
    """`synthetic/hair_fine.png` (a drawn design) forced down #882's photo lane at
    40 mm: ~50 s. Measured 2026-10-14: detail_layer sews 100 lines (513 mm),
    the line route 94 strands (487 mm); 68 detail lines and 82 strands lie
    on the other route's thread. Bands, not exact counts, so a different
    libm does not flip it; the claim is that most of each route sits on the
    other's lines."""
    from digitizer_core.pipeline import plan_stitches, run_stages
    width = 40.0
    result = run_stages(ROOT / "testdata" / "synthetic" / "hair_fine.png", D.arm_cfg("both", width))
    assert result.design_class == "photo_subject"
    detail = D.detail_strands(plan_stitches(result, D.arm_cfg("detail", width)))
    lines = D.line_strands(plan_stitches(result, D.arm_cfg("lines", width)))
    assert 90 <= len(detail) <= 110 and 85 <= len(lines) <= 100
    ov = D.overlap(detail, lines)
    assert ov["detail"]["shared"]["n"] >= 0.6 * len(detail)
    assert ov["lines"]["shared"]["n"] >= 0.8 * len(lines)
    # the line route is single runs, the detail layer three-pass beans: on the
    # same lines the detail layer lays about BEAN_PASSES x the thread per mm
    thread = lambda ss: sum(D._path_mm(s["pts"]) for s in ss)   # noqa: E731
    assert thread(detail) > 2.0 * thread(lines) * 0.9
    assert machine.BEAN_PASSES == 3


def test_tolerance_is_one_laid_thread():
    assert D.TOL_MM == machine.COVERAGE_THREAD_W_MM
    assert D.classify(1.0) == "shared" and D.classify(0.5) == "partial" and D.classify(0.1) == "only"
