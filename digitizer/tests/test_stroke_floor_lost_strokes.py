"""`cfg.extra["stroke_floor_keeps_lost_strokes"]` (built OFF 2026-11-18).

`columns._stroke_floor_judged` keeps a floored sew only when it adds more
thread inside the letter than outside it ("net"). A hairline stroke is
narrower than the thread, so floored it always adds more outside, the rule
refuses it and the stroke sews nothing. The Marine Corps emblem at 90 mm (a
4.4 mm serif face): the S of STATES lost its top curve and the C of CORPS
everything but its back. ON, the floored sew is also kept when the letter is
not whole without it (`SMALL_BOLD_COVER_MIN`) and whole with it.
"""
from shapely.geometry import box

from digitizer_core import stitches
from digitizer_core.columns import SMALL_BOLD_COVER_MIN, satin_cover, stroke_floor_restores
from digitizer_core.stitches import StitchRun

LETTER = box(0.0, 0.0, 1.0, 4.0)          # a 1 x 4 mm stroke


def _zigzag(y0, y1, step=0.2):
    pts, y, left = [], y0, True
    while y <= y1 + 1e-9:
        pts.append((0.0 if left else 1.0, round(y, 4)))
        left = not left
        y += step
    return [StitchRun(points=pts, kind=stitches.SATIN, shape_id="L")]


def test_a_letter_not_whole_without_the_floor_and_whole_with_it_is_restored():
    half, whole = _zigzag(0.0, 2.4), _zigzag(0.0, 4.0)
    assert satin_cover(half, LETTER) < SMALL_BOLD_COVER_MIN <= satin_cover(whole, LETTER)
    assert stroke_floor_restores(half, whole, LETTER)


def test_a_letter_already_whole_is_left_to_the_net_rule():
    """Commons Bukit's e (cover 0.92 -> 0.98, more spill than cover): refused."""
    nearly, whole = _zigzag(0.0, 3.8), _zigzag(0.0, 4.0)
    assert satin_cover(nearly, LETTER) >= SMALL_BOLD_COVER_MIN
    assert not stroke_floor_restores(nearly, whole, LETTER)


def test_a_floor_that_does_not_make_the_letter_whole_is_not_kept():
    half, more = _zigzag(0.0, 2.0), _zigzag(0.0, 2.8)
    assert satin_cover(more, LETTER) < SMALL_BOLD_COVER_MIN
    assert not stroke_floor_restores(half, more, LETTER)


def test_the_judge_reads_the_rule_only_with_the_flag(monkeypatch):
    """`_stroke_floor_judged`: "net" refuses; the unfloored sew comes back
    without the kwarg and the floored one with it."""
    from digitizer_core import columns

    half, whole = _zigzag(0.0, 2.4), _zigzag(0.0, 4.0)

    def fake_shape(**args):
        fired = columns._STROKE_JUDGING.get()
        if fired is not None:               # the floored sew: the floor reached a column
            fired.append(object())
            return whole, {}
        return half, {}

    monkeypatch.setattr(columns, "lettering_columns_shape", fake_shape)
    monkeypatch.setattr(columns, "handback_wins", lambda *a, **k: False)
    runs, report = columns._stroke_floor_judged({"poly": LETTER})
    assert runs is half and "stroke_floor_kept" not in report
    runs, report = columns._stroke_floor_judged({"poly": LETTER, "stroke_floor_lost_stroke": True})
    assert runs is whole and report["stroke_floor_lost_stroke"] == 1 and report["stroke_floor_kept"] == 1


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("stroke_floor_keeps_lost_strokes")
