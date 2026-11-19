"""`cfg.extra["dark_ink_line_one_lane"]` (built OFF 2026-11-19).

The NSA seal at 90 mm: the white ring carries a bold line (median 0.98 mm)
and a thin one (0.68). The dark read tagged 14 of the bold line's 22
letters; `bean_dark_ink(by_width=True)` judged them with the thin line on
the same ground, under the gate, so they sewed as thin beans beside 8 bold
satin mates. ON, each line takes the lane its own median width names.
"""
from shapely.geometry import box

from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.regions import Region
from digitizer_core.thin_ink import (DARK_INK_BEAN_MAX_WIDTH_MM, DARK_INK_GROUND_KEY, ONE_LANE_KEY,
                                     one_lane_per_line)

SPINE = [[(0.0, 0.0), (0.0, 1.0)]]


def _letter(i, width, bean, tc="TC1", thread=4, **meta):
    m = {"layer": 1, "text_cluster_id": tc, **meta}
    if bean:
        m.update({BEAN_LETTER_KEY: SPINE, DARK_INK_GROUND_KEY: "Sring", "dark_ink": True})
    p = box(4.0 * i, 0.0, 4.0 * i + width, 4.0)
    return Region(shape_id=f"L{i}", polygon=p, thread_index=thread, thread_number=str(thread),
                  area_mm2=p.area, source="test", meta=m)


BOLD = 2.4        # a 2.4 x 4 box: 2A/P = 1.5 mm, over the gate
THIN = 0.6        # 2A/P ~0.52 mm, under it


def test_a_bold_line_half_bean_sews_as_one_column_line():
    regs = [_letter(i, BOLD, bean=i % 2 == 0) for i in range(6)]
    assert one_lane_per_line(regs) == 3
    assert not any(r.meta.get(BEAN_LETTER_KEY) for r in regs)
    assert all(r.meta.get(ONE_LANE_KEY) == "column" for r in regs[::2])


def test_a_thin_line_half_bean_sews_as_one_bean_line():
    regs = [_letter(i, THIN, bean=i % 2 == 0) for i in range(6)]
    assert one_lane_per_line(regs) == 3
    assert all(r.meta.get(BEAN_LETTER_KEY) for r in regs)
    assert all(r.meta.get(DARK_INK_GROUND_KEY) == "Sring" for r in regs)
    assert all(r.meta.get("dark_ink") for r in regs)


def test_the_gate_is_the_bean_by_width_gate():
    assert 2 * BOLD * 4 / (2 * (BOLD + 4)) > DARK_INK_BEAN_MAX_WIDTH_MM > 2 * THIN * 4 / (2 * (THIN + 4))


def test_a_line_already_in_one_lane_is_left():
    for bean in (True, False):
        regs = [_letter(i, BOLD, bean=bean) for i in range(4)]
        assert one_lane_per_line(regs) == 0


def test_lines_are_judged_apart():
    """NSA: the thin line's widths never pull the bold one under the gate."""
    top = [_letter(i, BOLD, bean=i < 2, tc="TOP") for i in range(4)]
    bottom = [_letter(10 + i, THIN, bean=True, tc="BOT") for i in range(8)]
    one_lane_per_line(top + bottom)
    assert not any(r.meta.get(BEAN_LETTER_KEY) for r in top)
    assert all(r.meta.get(BEAN_LETTER_KEY) for r in bottom)


def test_a_shape_the_review_pinned_is_never_moved():
    regs = [_letter(i, BOLD, bean=True) for i in range(3)]
    regs.append(_letter(3, BOLD, bean=False, tier="satin"))
    assert one_lane_per_line(regs) == 0
    assert all(r.meta.get(BEAN_LETTER_KEY) for r in regs[:3])


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("dark_ink_line_one_lane")
