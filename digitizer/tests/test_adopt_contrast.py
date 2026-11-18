"""`cfg.extra["text_cluster_adopt_contrast"]` (built OFF 2026-11-18).

The letter door refuses a glyph whose stroke width varies by more than
`LETTER_STROKE_CV_MAX`. A serif capital with a bold stem and hairline arms
varies more than that: on the Defense seal at 90 mm the E's and F's of "OF
DEFENSE" read 0.58-0.63, were refused, and took the N and S between them out
of the line too. `_adopt_contrast` regrows each found line with the refused
glyphs in the pool; a refused glyph only ever JOINS a line the door found.
"""
from types import SimpleNamespace

from shapely.geometry import box

from digitizer_core.textcluster import (CONTRAST_STROKE_CV_MAX, LETTER_STROKE_CV_MAX,
                                        MIN_CLUSTER_MEMBERS, _adopt_contrast, _Candidate)

H, STROKE = 6.0, 0.5


def _cand(sid, x, cv=0.45, height=H, stroke=STROKE, y=0.0):
    poly = box(x, y, x + 4.0, y + height)
    region = SimpleNamespace(shape_id=sid, polygon=poly, thread_index=0, meta={})
    return _Candidate(region=region, height_mm=height, width_mm=4.0, stroke_mean_mm=stroke,
                      stroke_cv=cv, cx=x + 2.0, cy=y + height / 2.0)


def _ids(groups):
    return sorted(sorted(c.region.shape_id for c in g) for g in groups)


def _no_blobs(_group):
    return False


def test_the_bound_sits_above_the_door():
    assert CONTRAST_STROKE_CV_MAX > LETTER_STROKE_CV_MAX


def test_a_refused_glyph_beside_a_line_joins_it():
    line = [_cand(f"L{i}", 6.0 * i) for i in range(3)]
    e = _cand("E", 18.0, cv=0.6)
    out = _adopt_contrast([line], line, [e], None, _no_blobs)
    assert _ids(out) == [["E", "L0", "L1", "L2"]]


def test_refused_glyphs_chain_and_bring_the_stranded_door_letters_with_them():
    """D | E F E | N S: the E's and F were the gap; N and S pass the door but
    were short of a line of three without them."""
    line = [_cand(f"L{i}", 6.0 * i) for i in range(3)]                 # ends at x = 16
    refused = [_cand("E1", 30.0, cv=0.6), _cand("F", 46.0, cv=0.6), _cand("E2", 62.0, cv=0.6)]
    stranded = [_cand("N", 78.0), _cand("S", 94.0)]
    assert len(stranded) < MIN_CLUSTER_MEMBERS
    out = _adopt_contrast([line], line + stranded, refused, None, _no_blobs)
    assert _ids(out) == [["E1", "E2", "F", "L0", "L1", "L2", "N", "S"]]


def test_refused_glyphs_never_make_a_line_of_their_own():
    line = [_cand(f"L{i}", 6.0 * i) for i in range(3)]
    far = [_cand(f"X{i}", 200.0 + 6.0 * i, cv=0.6) for i in range(4)]
    out = _adopt_contrast([line], line, far, None, _no_blobs)
    assert _ids(out) == [["L0", "L1", "L2"]]


def test_a_refused_glyph_of_another_height_or_weight_is_not_adopted():
    line = [_cand(f"L{i}", 6.0 * i) for i in range(3)]
    tall = _cand("tall", 18.0, cv=0.6, height=2.0 * H)
    heavy = _cand("heavy", 18.0, cv=0.6, stroke=3.0 * STROKE)
    out = _adopt_contrast([line], line, [tall, heavy], None, _no_blobs)
    assert _ids(out) == [["L0", "L1", "L2"]]


def test_a_regrown_row_of_blobs_leaves_the_line_as_it_was():
    line = [_cand(f"L{i}", 6.0 * i) for i in range(3)]
    e = _cand("E", 18.0, cv=0.6)
    out = _adopt_contrast([line], line, [e], None, lambda g: len(g) > 3)
    assert _ids(out) == [["L0", "L1", "L2"]]


def test_two_lines_a_refused_glyph_bridges_become_one():
    left = [_cand(f"A{i}", 6.0 * i) for i in range(3)]                  # ends at x = 16
    right = [_cand(f"B{i}", 46.0 + 6.0 * i) for i in range(3)]          # starts at x = 46
    bridge = _cand("E", 30.0, cv=0.6)
    out = _adopt_contrast([left, right], left + right, [bridge], None, _no_blobs)
    assert _ids(out) == [["A0", "A1", "A2", "B0", "B1", "B2", "E"]]


def test_nothing_refused_returns_the_groups_themselves():
    line = [_cand(f"L{i}", 6.0 * i) for i in range(3)]
    groups = [line]
    assert _adopt_contrast(groups, line, [], None, _no_blobs) is groups


def test_the_result_does_not_depend_on_input_order():
    line = [_cand(f"L{i}", 6.0 * i) for i in range(3)]
    refused = [_cand("E1", 18.0, cv=0.6), _cand("E2", 24.0, cv=0.6)]
    a = _adopt_contrast([line], line, refused, None, _no_blobs)
    b = _adopt_contrast([line[::-1]], line[::-1], refused[::-1], None, _no_blobs)
    assert _ids(a) == _ids(b)


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("text_cluster_adopt_contrast")
