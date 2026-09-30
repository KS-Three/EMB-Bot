"""The customer calibration card (tools/sewout_card_v2.py): what Kent decided
on 2026-09-30, pinned — fiducials outside the artwork in block 1's thread,
a 0.15 mm density arm, a 5x7 hoop fit — and the reader reading it.

Builds the FULL card once per module (block 5 runs the pipeline four times,
~14 s). Skipped, not failed, on a box with no TrueType font, which is the
one thing block 5 needs that the reduced card in test_sewout_reader.py
does not.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core.adapter import plan_to_design
from tools import sewout_card as v1
from tools import sewout_card_v2 as v2
from tools import sewout_reader as R

pytestmark = pytest.mark.skipif(v1.FONT is None, reason="block 5 needs a TrueType font")


@pytest.fixture(scope="module")
def built():
    plan, report = v2.build_card_v2()
    return plan, report, plan_to_design(plan, name="v2")


def _fiducial_spans(design):
    return [r for r in design["runs"] if r["shape"] == v2.FIDUCIAL_SHAPE]


def test_fits_the_5x7_hoop_with_margin(built):
    plan, report, _ = built
    w, h = plan.design_size_mm
    assert w <= v2.HOOP_MM[0] - 2 * v2.HOOP_MARGIN_MM
    assert h <= v2.HOOP_MM[1] - 2 * v2.HOOP_MARGIN_MM
    # ...and would NOT fit 4x4, which is why 5x7 was the call.
    assert w > 66.0 and h > 96.0
    assert report["hoop"]["target_mm"] == [130.0, 180.0]


def test_four_marks_frame_the_artwork_in_the_first_block(built):
    plan, report, design = built
    spans = _fiducial_spans(design)
    assert len(spans) == 4
    assert all(sp["block"] == 0 for sp in spans)
    assert [r["shape"] for r in design["runs"][:4]] == [v2.FIDUCIAL_SHAPE] * 4   # sewn first
    # Each mark sits outside the artwork's box by the gap, at its own corner.
    x0, y0, x1, y1 = report["fiducials"]["artwork_bbox_mm"]
    centres = report["fiducials"]["centres_mm"]
    half = v2.FIDUCIAL_MM / 2
    want = [(x0 - v2.FIDUCIAL_GAP_MM - half, y0 - v2.FIDUCIAL_GAP_MM - half),
            (x1 + v2.FIDUCIAL_GAP_MM + half, y0 - v2.FIDUCIAL_GAP_MM - half),
            (x1 + v2.FIDUCIAL_GAP_MM + half, y1 + v2.FIDUCIAL_GAP_MM + half),
            (x0 - v2.FIDUCIAL_GAP_MM - half, y1 + v2.FIDUCIAL_GAP_MM + half)]
    for (cx, cy), (wx, wy) in zip(centres, want):
        assert cx == pytest.approx(wx, abs=0.05) and cy == pytest.approx(wy, abs=0.05)
    # No extra colour stop for them: v1's seven blocks, six changes.
    assert len(plan.blocks) == 7
    assert plan.stats.color_changes == 6


def test_every_mark_is_locked(built):
    plan, _, _ = built
    marks = [r for r in plan.blocks[0].runs if r.shape_id == v2.FIDUCIAL_SHAPE]
    for m in marks:
        assert m.trim and m.jump
        head = np.hypot(*(np.subtract(m.points[1], m.points[0])))
        assert head == pytest.approx(v1.machine.TIE_STITCH_MM, abs=1e-6)


def test_square_d_sews_the_professionals_pitch(built):
    _, report, design = built
    info = report["blocks"]["2 FILL"]["fill-D-0.15"]
    assert info["row_mm"] == 0.15
    assert info["measured_row_pitch_mm"] == pytest.approx(0.15, abs=0.02)
    # v1's three arms are still there, unchanged in their spacing.
    for tag, row in (("fill-A-0.40", 0.40), ("fill-B-0.20", 0.20), ("fill-C-pass1", 0.40)):
        assert report["blocks"]["2 FILL"][tag]["row_mm"] == row
    feats = {f.name: f for f in R.features_from_design(design)}
    assert feats["fill-D-0.15"].role == "square"
    assert v2.FIDUCIAL_SHAPE not in feats


def test_v1_is_untouched_by_importing_v2():
    names = [b[0] for b in v1.BLOCKS]
    assert names == ["1 LOCK", "2 FILL", "3 WSATIN", "4 TRAVEL", "5 TEXT", "6 SEAMA", "6 SEAMB"]
    assert v1.BLOCKS[1][1] is v1.block2_fill
    assert v2.BLOCKS[1][1] is v2.block2_fill_v2


def test_the_reader_registers_off_the_marks(built):
    """The whole point of v2: a photo reads in `fiducials` mode, with a
    planted pull recovered, and the marks themselves are not features."""
    _, _, design = built
    truth = [R.Distortion("satin-5mm", dy_mm=-0.4), R.Distortion("fill-D-0.15", dx_mm=-0.5)]
    photo, _ = R.simulate_photo(R.distort(design, truth), 10.0, seed=9)
    rd = R.read_card(photo, design, mode="fiducials")
    cmp = R.compare(rd, R.read_reference(design))
    rows = {r["name"]: r for r in cmp["features"]}
    assert rows["satin-5mm"]["d_height_mm"] == pytest.approx(-0.4, abs=0.1)
    assert rows["fill-D-0.15"]["d_width_mm"] == pytest.approx(-0.5, abs=0.1)
    assert abs(rows["fill-A-0.40"]["d_width_mm"]) <= 0.1
    assert len([r for r in rd["features"] if r["role"] == "word"]) == 4
