"""`cfg.dark_ink_bean_by_width`, `thin_ink.bean_dark_ink(by_width=True)`, built
OFF 2026-11-16: which dark-ink strokes sew as a bean is decided by the
group's median stroke width, not by thread contrast.

NOAA's ring text (0.46 mm, contrast 66.8) lost strokes as satin; EPA's (0.91
mm, contrast 44.9) sewed as thin bean lines for bold lettering. Synthetic
strips only: a strip `w` mm wide and 8 mm long has mean width
2 x area / perimeter = 8w / (8 + w): 0.435 mm for w 0.46, 0.809 mm for w 0.9.
"""
from __future__ import annotations

from shapely.geometry import Polygon, box

from digitizer_core import machine
from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.thin_ink import (BEAN_MAX_GROUND_DE00, DARK_INK_BEAN_MAX_WIDTH_MM,
                                     DARK_INK_GROUND_KEY, _thread_de00, bean_dark_ink)
from digitizer_core.threads import CHART

from .conftest import BEAN_BY_WIDTH_2026_11_16_OFF

_IDX = {c.number: i for i, c in enumerate(CHART)}
POT, PEN = _IDX["0763"], _IDX["1233"]          # 17.8 dE00 apart: a "pen line"
WHITE, BLACK = _IDX["0015"], _IDX["0020"]      # 100 dE00 apart: "designed lettering"


def _r(sid, poly: Polygon, thread_index: int, layer: int, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread_index,
                  thread_number=CHART[thread_index].number, area_mm2=float(poly.area),
                  meta={"layer": layer, **meta})


def _strip(x: float, w: float, y0: float = 2.0) -> Polygon:
    return box(x, y0, x + w, y0 + 8.0)


GROUND = box(0, 0, 40, 40)


def _stroke(sid, x, w, thread, **kw):
    return _r(sid, _strip(x, w), thread, 1, dark_ink=True, **kw)


def _tagged(regions):
    return {r.shape_id for r in regions if BEAN_LETTER_KEY in r.meta}


def test_the_flag_is_on_by_default_since_the_flip():
    # Kent 2026-11-16: "Flip ON (Recommended)".
    assert PipelineConfig().dark_ink_bean_by_width is True
    assert PipelineConfig(**BEAN_BY_WIDTH_2026_11_16_OFF).dark_ink_bean_by_width is False


def test_the_width_gate_is_one_and_a_half_cross_floors():
    assert DARK_INK_BEAN_MAX_WIDTH_MM == 1.5 * machine.SATIN_MIN_CROSS_MM == 0.75


def test_thin_strokes_over_the_contrast_gate_bean_only_by_width():
    assert _thread_de00(BLACK, WHITE) > BEAN_MAX_GROUND_DE00
    def build():
        return [_r("G", GROUND, WHITE, 0)] + [_stroke(f"K{i}", 2 + 3 * i, 0.46, BLACK)
                                               for i in range(4)]
    off, on = build(), build()
    assert bean_dark_ink(off) == 0 and not _tagged(off)
    assert bean_dark_ink(on, by_width=True) == 4
    assert _tagged(on) == {"K0", "K1", "K2", "K3"}
    assert all(r.meta[DARK_INK_GROUND_KEY] == "G" for r in on if r.shape_id != "G")


def test_bold_strokes_under_the_contrast_gate_bean_only_without_width():
    assert _thread_de00(PEN, POT) < BEAN_MAX_GROUND_DE00
    def build():
        return [_r("G", GROUND, POT, 0)] + [_stroke(f"K{i}", 2 + 3 * i, 0.9, PEN)
                                             for i in range(4)]
    off, on = build(), build()
    assert bean_dark_ink(off) == 4 and len(_tagged(off)) == 4
    assert bean_dark_ink(on, by_width=True) == 0 and not _tagged(on)


def test_a_group_decides_together():
    # three thin strokes and one 1.2 mm one: the median is thin, all four bean
    thin = [_r("G", GROUND, WHITE, 0)] + [_stroke(f"K{i}", 2 + 3 * i, 0.46, BLACK)
                                          for i in range(3)] + [_stroke("W", 14, 1.2, BLACK)]
    assert bean_dark_ink(thin, by_width=True) == 4
    assert _tagged(thin) == {"K0", "K1", "K2", "W"}
    # three bold and one 0.3 mm one: the median is bold, none bean
    bold = [_r("G", GROUND, POT, 0)] + [_stroke(f"K{i}", 2 + 3 * i, 0.9, PEN)
                                        for i in range(3)] + [_stroke("T", 14, 0.3, PEN)]
    assert bean_dark_ink(bold, by_width=True) == 0
    assert not _tagged(bold)


def test_two_threads_on_one_ground_decide_separately():
    regions = ([_r("G", GROUND, WHITE, 0)]
               + [_stroke(f"T{i}", 2 + 3 * i, 0.46, BLACK) for i in range(2)]
               + [_stroke(f"B{i}", 20 + 3 * i, 0.9, PEN) for i in range(2)])
    assert bean_dark_ink(regions, by_width=True) == 2
    assert _tagged(regions) == {"T0", "T1"}


def test_two_grounds_decide_separately():
    g2 = box(50, 0, 90, 40)
    regions = ([_r("G", GROUND, WHITE, 0), _r("H", g2, WHITE, 0)]
               + [_stroke("T", 2, 0.46, BLACK), _stroke("B", 52, 0.9, BLACK)])
    assert bean_dark_ink(regions, by_width=True) == 1
    assert _tagged(regions) == {"T"}


def test_a_stroke_on_no_ground_is_tagged_neither_way():
    for by_width in (False, True):
        s = [_stroke("K", 2, 0.46, BLACK)]
        assert bean_dark_ink(s, by_width=by_width) == 0
        assert BEAN_LETTER_KEY not in s[0].meta


def test_by_width_false_is_the_function_without_the_keyword():
    def build():
        return ([_r("G", GROUND, POT, 0), _r("H", box(50, 0, 90, 40), WHITE, 0)]
                + [_stroke("A", 2, 0.9, PEN), _stroke("B", 5, 0.46, PEN),
                   _stroke("C", 52, 0.46, BLACK), _stroke("D", 55, 0.9, BLACK)])
    a, b = build(), build()
    assert bean_dark_ink(a) == bean_dark_ink(b, by_width=False)
    assert [(r.shape_id, r.meta) for r in a] == [(r.shape_id, r.meta) for r in b]
    assert _tagged(a) == {"A", "B"}
