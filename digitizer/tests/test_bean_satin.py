"""Bean letters as a narrow satin column (`cfg.bean_letter_satin_mm`, 2026-10-20).

Kent's card v4 sew-out beside the pro's Fremont patch: our small letters sit in
the art's footprint but sew as a hairline; the pro satins them ~0.85 mm wide.
The option sews each bean spine as a centre run out and a zigzag back, the
column `satin_mm` across. OFF (None) is bean, byte for byte. Gate 1: the width
is a candidate until sewn.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402
from digitizer_core.stage6_beanletter import _satin_along, bean_letter  # noqa: E402

STEM = [(0.0, 0.0), (0.0, 2.5)]                       # a 2.5 mm stem, like THE's T
EIGHT = [[(0.0, 0.0), (0.6, 0.6), (0.0, 1.2), (-0.6, 0.6), (0.0, 0.0)]]


def test_off_by_default_and_none_is_bean_byte_for_byte():
    assert PipelineConfig().bean_letter_satin_mm is None
    a, ra = bean_letter([STEM], "S1", entry=None, trim_at_mm=3.0)
    b, rb = bean_letter([STEM], "S1", entry=None, trim_at_mm=3.0, satin_mm=None)
    assert [r.points for r in a] == [r.points for r in b] and ra == rb
    assert all(r.kind == stitches.RUN for r in a)


def test_the_column_is_as_wide_as_asked_and_square_to_the_spine():
    under, zig = _satin_along(STEM, 0.85, None)
    xs = [p[0] for p in zig]
    assert math.isclose(max(xs) - min(xs), 0.85, abs_tol=1e-6)
    assert math.isclose(max(xs), 0.425, abs_tol=1e-6)            # centred on the spine
    # the ends taper: the first and last crosses are narrower than the middle ones
    assert abs(zig[0][0]) < 0.425 - 1e-6 and abs(zig[-1][0]) < 0.425 - 1e-6
    # crosses SATIN_SPACING_MM apart along it, alternating sides
    ys = sorted(p[1] for p in zig)
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    assert max(gaps) <= machine.SATIN_SPACING_MM + 1e-9
    assert all((zig[i][0] > 0) != (zig[i + 1][0] > 0) for i in range(len(zig) - 1))
    # the underlay runs out along the spine and the zigzag comes back to its start
    assert under[0] == STEM[0] and math.isclose(under[-1][1], 2.5)
    assert math.isclose(zig[-1][1], 0.0, abs_tol=1e-9)


def test_a_letter_sews_underlay_then_satin_per_stroke():
    runs, report = bean_letter(EIGHT, "S8", entry=None, trim_at_mm=3.0, satin_mm=0.85)
    assert not report["empty"] and report["strokes"] == 1
    assert [r.kind for r in runs] == [stitches.UNDERLAY, stitches.SATIN]
    # the column starts where the underlay ended: one continuous path
    assert runs[1].points[0] == runs[0].points[-1]


def test_the_bay_hold_and_passes_do_not_apply():
    a, _ = bean_letter(EIGHT, "S8", entry=None, trim_at_mm=3.0, satin_mm=0.85)
    b, _ = bean_letter(EIGHT, "S8", entry=None, trim_at_mm=3.0, satin_mm=0.85, passes=1,
                       bay_hold_mm=0.2, stroke_mm=0.3)
    assert [r.points for r in a] == [r.points for r in b]
