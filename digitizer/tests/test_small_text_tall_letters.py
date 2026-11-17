"""`cfg.extra["small_text_keep_tall_letters"]` (built OFF 2026-11-17).

`small_text._core` keeps a line's letters of one height, which in a lowercase
line is its x-height, so a capital or a tall ascender was set aside as a
stray and lost its lettering tags. SBA's subtitle at 90 mm: the A of
"Administration" (1.38x its line) and its d (1.57x) were stripped, and the A
took the fill tier and sewed as a blob. `small_text._tall_letters` names the
strays that are capitals, ascenders or descenders of the line.
"""
from types import SimpleNamespace

from shapely.geometry import box

from digitizer_core.small_text import TALL_MAX_RATIO, _core, _tall_letters

INK, OTHER = 5, 9
X_HEIGHT = 2.7
BASE = 19.1                      # y down: the baseline


def _letter(sid, x0, height, width=2.0, thread=INK, base=BASE):
    poly = box(x0, base - height, x0 + width, base)
    return SimpleNamespace(shape_id=sid, polygon=poly, thread_index=thread, meta={})


def _lowercase_line(n=6, x0=10.0):
    return [_letter(f"x{i}", x0 + 3.0 * i, X_HEIGHT) for i in range(n)]


def test_core_sets_a_capital_aside():
    """The premise: `_core` drops the tall letter."""
    line = _lowercase_line()
    cap = _letter("A", 6.0, 1.38 * X_HEIGHT, width=3.7)
    assert all(r is not cap for r in _core(line + [cap]))


def test_a_capital_on_the_baseline_is_a_tall_letter():
    line = _lowercase_line()
    cap = _letter("A", 6.0, 1.38 * X_HEIGHT, width=3.7)
    assert _tall_letters([cap], line, X_HEIGHT) == [cap]


def test_an_ascender_is_a_tall_letter():
    line = _lowercase_line()
    d = _letter("d", 29.0, 1.57 * X_HEIGHT, width=2.9)
    assert _tall_letters([d], line, X_HEIGHT) == [d]


def test_a_descender_hanging_from_the_lines_top_is_a_tall_letter():
    line = _lowercase_line()
    p = _letter("p", 29.0, 1.4 * X_HEIGHT, base=BASE + 0.4 * X_HEIGHT)
    assert _tall_letters([p], line, X_HEIGHT) == [p]


def test_a_shape_too_tall_is_not():
    line = _lowercase_line()
    bar = _letter("bar", 6.0, (TALL_MAX_RATIO + 0.2) * X_HEIGHT)
    assert _tall_letters([bar], line, X_HEIGHT) == []


def test_a_tall_shape_off_the_baseline_and_the_top_is_not():
    line = _lowercase_line()
    floater = _letter("f", 6.0, 1.4 * X_HEIGHT, base=BASE + 0.2 * X_HEIGHT)
    assert _tall_letters([floater], line, X_HEIGHT) == []


def test_a_tall_shape_of_another_thread_is_not():
    line = _lowercase_line()
    rule = _letter("r", 6.0, 1.4 * X_HEIGHT, thread=OTHER)
    assert _tall_letters([rule], line, X_HEIGHT) == []


def test_a_tall_shape_far_from_the_line_is_not():
    line = _lowercase_line()
    far = _letter("far", 60.0, 1.4 * X_HEIGHT)
    assert _tall_letters([far], line, X_HEIGHT) == []


def test_a_wide_tall_shape_is_not_a_letter():
    line = _lowercase_line()
    plate = _letter("plate", 2.0, 1.4 * X_HEIGHT, width=6.0)
    assert _tall_letters([plate], line, X_HEIGHT) == []


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("small_text_keep_tall_letters")
