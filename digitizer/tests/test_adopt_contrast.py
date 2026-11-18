"""`cfg.extra["text_cluster_adopt_contrast"]` (built OFF 2026-11-18).

The letter door refuses a glyph whose stroke width varies by more than
`LETTER_STROKE_CV_MAX`. A serif capital with a bold stem and hairline arms
varies more than that: on the Defense seal at 90 mm the E's and F's of "OF
DEFENSE" read 0.58-0.63, were refused, and took the N between them out of
the line too. `_adopt_contrast` regrows each found line with the refused
glyphs that sit BETWEEN two door candidates in the pool; a refused glyph
only ever joins a line the door found, and a row of one shape repeated (a
ring of stars) is left alone.
"""
from types import SimpleNamespace

from shapely.geometry import box

from digitizer_core.textcluster import (CONTRAST_STROKE_CV_MAX, LETTER_STROKE_CV_MAX,
                                        _adopt_contrast, _between, _Candidate, _repeats)

H, STROKE = 6.0, 0.5
WIDTHS = (3.0, 4.2, 5.0, 3.6, 4.6, 2.6, 5.4, 3.3)      # a word's letters differ


def _cand(sid, x, cv=0.45, height=H, stroke=STROKE, y=0.0, width=4.0):
    poly = box(x, y, x + width, y + height)
    region = SimpleNamespace(shape_id=sid, polygon=poly, thread_index=0, meta={})
    return _Candidate(region=region, height_mm=height, width_mm=width, stroke_mean_mm=stroke,
                      stroke_cv=cv, cx=x + width / 2.0, cy=y + height / 2.0)


def _word(prefix, x0, n, pitch=6.0):
    return [_cand(f"{prefix}{i}", x0 + pitch * i, width=WIDTHS[i % len(WIDTHS)]) for i in range(n)]


def _ids(groups):
    return sorted(sorted(c.region.shape_id for c in g) for g in groups)


def _no_blobs(_group):
    return False


def test_the_bound_sits_above_the_door():
    assert CONTRAST_STROKE_CV_MAX > LETTER_STROKE_CV_MAX


def test_a_refused_glyph_between_two_letters_joins_their_line():
    line = _word("L", 0.0, 3)                       # x 0, 6, 12
    after = _cand("N", 30.0, width=4.4)             # a door letter stranded past the gap
    e = _cand("E", 19.0, cv=0.6, width=3.8)
    out = _adopt_contrast([line], line + [after], [e], None, _no_blobs)
    assert _ids(out) == [["E", "L0", "L1", "L2", "N"]]


def test_a_refused_glyph_past_the_end_of_a_line_is_not_offered():
    """Beside a line, with the line all on one side: a rope strand, an ornament."""
    line = _word("L", 0.0, 3)
    e = _cand("E", 19.0, cv=0.6, width=3.8)
    assert not _between(e, line, None)
    groups = [line]
    assert _adopt_contrast(groups, line, [e], None, _no_blobs) is groups


def test_between_reads_the_opening_not_the_distance():
    left, right = _cand("a", 0.0), _cand("b", 12.0)
    assert _between(_cand("mid", 6.0, cv=0.6), [left, right], None)
    above = _cand("above", 6.0, cv=0.6, y=9.0)      # both neighbours down and to the sides
    assert not _between(above, [left, right], None)


def test_refused_glyphs_never_make_a_line_of_their_own():
    line = _word("L", 0.0, 3)
    far = [_cand(f"X{i}", 200.0 + 6.0 * i, cv=0.6, width=WIDTHS[i]) for i in range(4)]
    out = _adopt_contrast([line], line, far, None, _no_blobs)
    assert _ids(out) == [["L0", "L1", "L2"]]


def test_a_refused_glyph_of_another_height_or_weight_is_not_adopted():
    line = _word("L", 0.0, 3)
    after = _cand("N", 30.0, width=4.4)
    tall = _cand("tall", 19.0, cv=0.6, height=2.0 * H)
    heavy = _cand("heavy", 19.0, cv=0.6, stroke=3.0 * STROKE)
    out = _adopt_contrast([line], line + [after], [tall, heavy], None, _no_blobs)
    assert _ids(out) == [["L0", "L1", "L2"]]


def test_a_row_of_one_shape_repeated_is_left_alone():
    """The FBI seal's ring of stars: the door had tagged some, the bare rule
    adopted the rest, and the lane sewed them worse."""
    stars = [_cand(f"S{i}", 6.0 * i) for i in range(3)] + [_cand("S9", 24.0)]
    refused = _cand("S4", 18.0, cv=0.56)
    assert _repeats(stars + [refused])
    groups = [stars[:3]]
    out = _adopt_contrast(groups, stars, [refused], None, _no_blobs)
    assert _ids(out) == [["S0", "S1", "S2"]]


def test_a_word_is_not_a_row_of_repeats():
    assert not _repeats(_word("L", 0.0, 8))


def test_a_regrown_row_of_blobs_leaves_the_line_as_it_was():
    line = _word("L", 0.0, 3)
    after = _cand("N", 30.0, width=4.4)
    e = _cand("E", 19.0, cv=0.6, width=3.8)
    out = _adopt_contrast([line], line + [after], [e], None, lambda g: len(g) > 3)
    assert _ids(out) == [["L0", "L1", "L2"]]


def test_two_lines_a_refused_glyph_bridges_become_one():
    left = _word("A", 0.0, 3)                       # x 0, 6, 12
    right = _word("B", 26.0, 3)                     # x 26, 32, 38
    bridge = _cand("E", 19.0, cv=0.6, width=3.8)
    out = _adopt_contrast([left, right], left + right, [bridge], None, _no_blobs)
    assert _ids(out) == [["A0", "A1", "A2", "B0", "B1", "B2", "E"]]


def test_nothing_refused_returns_the_groups_themselves():
    line = _word("L", 0.0, 3)
    groups = [line]
    assert _adopt_contrast(groups, line, [], None, _no_blobs) is groups


def test_the_result_does_not_depend_on_input_order():
    line = _word("L", 0.0, 3)
    after = _cand("N", 30.0, width=4.4)
    refused = [_cand("E1", 18.5, cv=0.6, width=3.8), _cand("E2", 24.0, cv=0.6, width=4.9)]
    a = _adopt_contrast([line], line + [after], refused, None, _no_blobs)
    b = _adopt_contrast([line[::-1]], [after] + line[::-1], refused[::-1], None, _no_blobs)
    assert _ids(a) == _ids(b)


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("text_cluster_adopt_contrast")
