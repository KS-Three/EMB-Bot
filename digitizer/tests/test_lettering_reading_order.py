"""`cfg.lettering_columns_reading_order` (built OFF 2026-11-16 as a `cfg.extra`
key; ON since 2026-11-16, Kent's flip "On!"): a
span's letters sewn in reading order, not nearest-neighbour from the needle.

Under the Column lane a word's letters went nearest-neighbour from wherever
the last letter ENDED, so the word's order followed every letter's exit: one
end moved by `lettering_columns_lean_flat_ends` turned Gaulke's LC word round,
and the G, entered from its other side, sewed every satin the other way
(`reading_order`'s docstring has the numbers). The pro sews his lettering in
reading order.

Both arms are pinned on the stage-7 harness `test_lettering_columns` uses: the
lane stubbed to a run that ends where the test says. Nothing digitizes.
"""
from __future__ import annotations

import pytest

from digitizer_core import PipelineConfig, stitches
from digitizer_core.reading_order import reading_ranks
from tests.conftest import own_thread_only
from tests.test_lettering_columns import _one_colour, _rect, _sew_order

FLAG = "lettering_columns_reading_order"


def _orders(monkeypatch, shapes, letters, end_at, extra):
    """(OFF path's order, lane order) with the lane stubbed to a run up the
    letter's middle that ends at `end_at(off_order)`."""
    import digitizer_core.stage7_sequence as S7
    from digitizer_core.fabrics import fabric_for_garment

    fabric = fabric_for_garment("left_chest")
    off = _sew_order(S7.sequence(_one_colour(shapes, letters), fabric,
                                 PipelineConfig(underlay=False, **{FLAG: False}))[0])
    end = end_at(off)

    def fake_lane(poly, sid, **kw):
        cx, cy = poly.centroid.x, poly.centroid.y
        return [stitches.StitchRun(points=[(cx, cy - 4), (cx, cy + 4), end],
                                   kind=stitches.SATIN, shape_id=sid)], \
            {"empty": False, "jumps": 0}

    monkeypatch.setattr(S7, "lettering_columns_shape",
                        own_thread_only(fake_lane, S7.lettering_columns_shape))
    cfg = PipelineConfig(underlay=False, lettering_columns=True, **extra)
    return off, _sew_order(S7.sequence(_one_colour(shapes, letters), fabric, cfg)[0])


LETTERS = {"L1", "L2", "L3"}
WORD = {"A": _rect(-24, -5, -22, 5), "L1": _rect(-1, -5, 1, 5),
        "L2": _rect(4, -5, 6, 5), "L3": _rect(9, -5, 11, 5), "B": _rect(30, -5, 32, 5)}


def _on_l3(off):
    assert off == ["A", "L1", "L2", "L3", "B"], off
    c = WORD["L3"].centroid
    return (c.x, c.y)


def test_on_by_default():
    """Kent's flip, 2026-11-16 ("On!")."""
    assert PipelineConfig().lettering_columns_reading_order is True
    assert PipelineConfig().lettering_columns_judge_entry_free is True


@pytest.mark.parametrize("extra", [{FLAG: False}])
def test_off_a_letters_exit_reorders_the_word(monkeypatch, extra):
    """The OFF arm, the field False: every letter ends
    on L3, so L3 is sewn second -- the exit decides the word's order."""
    import digitizer_core.stage7_sequence as S7
    calls = []
    monkeypatch.setattr(S7, "reading_ranks", lambda polys: calls.append(polys) or {})
    _off, on = _orders(monkeypatch, WORD, LETTERS, _on_l3, extra)
    assert on == ["A", "L1", "L3", "L2", "B"]
    assert calls == []


def test_on_the_word_is_sewn_in_reading_order_wherever_its_letters_end(monkeypatch):
    """The same stub, the flag ON: the exits no longer move the word."""
    _off, on = _orders(monkeypatch, WORD, LETTERS, _on_l3, {FLAG: True})
    assert on == ["A", "L1", "L2", "L3", "B"]


def test_on_a_word_entered_from_its_right_still_reads_left_to_right(monkeypatch):
    """The needle arrives from the right (the bar there sews first): OFF the
    word runs right to left, as every Becker line did against the pro's left
    to right; ON it reads left to right."""
    shapes = {"A": _rect(39, -5, 41, 5), "L1": _rect(-1, -5, 1, 5),
              "L2": _rect(4, -5, 6, 5), "L3": _rect(9, -5, 11, 5), "B": _rect(-21, -5, -19, 5)}

    def at_l3_top(off):
        assert off == ["A", "L3", "L2", "L1", "B"], off
        return (10.0, -5.0)
    _off, off_lane = _orders(monkeypatch, shapes, LETTERS, at_l3_top, {FLAG: False})
    _off, on = _orders(monkeypatch, shapes, LETTERS, at_l3_top, {FLAG: True})
    assert off_lane == ["A", "L3", "L2", "L1", "B"]
    assert on == ["A", "L1", "L2", "L3", "B"]


def test_on_lines_top_first_each_left_to_right(monkeypatch):
    shapes = {"A": _rect(-24, -5, -22, 5),
              "T2": _rect(4, -12, 6, -4), "T1": _rect(-1, -12, 1, -4),
              "U1": _rect(-1, 4, 1, 12), "U2": _rect(4, 4, 6, 12)}
    letters = {"T1", "T2", "U1", "U2"}

    def at_u2(off):
        assert off[0] == "A" and set(off[1:]) == letters, off
        c = shapes["U2"].centroid
        return (c.x, c.y)
    _off, on = _orders(monkeypatch, shapes, letters, at_u2, {FLAG: True})
    assert on == ["A", "T1", "T2", "U1", "U2"]


# ------------------------------------------------------------ reading_ranks

def _order(polys):
    r = reading_ranks(polys)
    return sorted(r, key=r.get)


def test_ranks_an_arc_as_one_line():
    """A word on an arc: each letter overlaps its neighbour's height, so the
    line chains letter to letter and reads left to right, though its ends sit
    lower than its middle by more than a letter's height."""
    ys = [7.5, 5.0, 2.5, 0.0, 2.5, 5.0, 7.5]
    polys = {f"L{i}": _rect(4 * i, y, 4 * i + 2, y + 6) for i, y in enumerate(ys)}
    assert _order(polys) == [f"L{i}" for i in range(7)]


def test_ranks_a_dot_with_the_line_it_sits_over():
    """A mark under half the median height joins the line, at its own x."""
    polys = {"i": _rect(0, 0, 1, 6), "dot": _rect(0.2, -2, 1.2, -1),
             "n": _rect(2, 0, 6, 6), "x": _rect(-5, 0, -2, 6)}
    assert _order(polys) == ["x", "i", "dot", "n"]


def test_ranks_two_lines_top_first():
    polys = {"b1": _rect(0, 10, 2, 16), "a2": _rect(4, 0, 6, 6),
             "a1": _rect(0, 0, 2, 6), "b2": _rect(4, 10, 6, 16)}
    assert _order(polys) == ["a1", "a2", "b1", "b2"]


def test_ranks_no_letters():
    assert reading_ranks({}) == {}
