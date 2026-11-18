"""`cfg.extra["keyline_bean_between_fills"]` (built OFF 2026-11-18).

`keyline_bean.keyline_regions` reads keylines per THREAD: a thread's hairline
rings sew as a bean only when it draws nearly nothing else. The Air Force
seal at 90 mm: its gold outer band sits between black rings drawn 0.38-0.50
mm wide, black also draws the lettering, and each ring sewed as a 1.51 mm
satin over the gold. ON, a hairline ring with a sewn shape of another thread
along most of BOTH its edges is a dividing line and sews as the bean.
"""
from types import SimpleNamespace

from shapely.geometry import Point

from digitizer_core.keyline_bean import BETWEEN_FILLS_KEY, DIVIDING_EDGE_SHARE, _dividing_lines

GOLD, BLACK, WHITE = 1, 2, 3
LIMIT = 0.6


def _region(sid, poly, thread, stitched=True):
    return SimpleNamespace(shape_id=sid, polygon=poly, thread_index=thread,
                           meta={"stitched": stitched})


def _annulus(r_out, r_in):
    return Point(0, 0).buffer(r_out, 128).difference(Point(0, 0).buffer(r_in, 128))


def _find(regions, taken=frozenset(), p95=0.5):
    return _dividing_lines(regions, set(taken), lambda r: bool(r.polygon.interiors),
                           lambda r: LIMIT, lambda r, lim: {"width_p95_mm": p95})


def _seal(line_w=0.4, outside=True, inside=True):
    regs = [_region("line", _annulus(30.0, 30.0 - line_w), BLACK)]
    if outside:
        regs.append(_region("gold", _annulus(33.0, 30.0), GOLD))
    if inside:
        regs.append(_region("white", _annulus(30.0 - line_w, 20.0), WHITE))
    return regs


def test_a_hairline_ring_between_two_sewn_colours_is_a_dividing_line():
    assert _find(_seal()) == {"line"}


def test_a_ring_with_the_page_on_one_side_is_a_frame_not_a_dividing_line():
    """To-a-T Machine's black frame, which the pro borders."""
    assert _find(_seal(outside=False)) == set()
    assert _find(_seal(inside=False)) == set()


def test_an_unsewn_neighbour_is_the_page():
    regs = _seal()
    next(r for r in regs if r.shape_id == "gold").meta["stitched"] = False
    assert _find(regs) == set()


def test_a_neighbour_of_the_rings_own_thread_does_not_count():
    regs = _seal()
    next(r for r in regs if r.shape_id == "gold").thread_index = BLACK
    assert _find(regs) == set()


def test_a_band_wider_than_a_hairline_is_not_taken():
    assert _find(_seal(line_w=1.5)) == set()


def test_a_blob_on_the_ring_is_not_taken():
    assert _find(_seal(), p95=3.0) == set()


def test_a_ring_the_thread_gate_already_took_is_not_named_twice():
    assert _find(_seal(), taken={"line"}) == set()


def test_the_share_is_a_ratio_and_the_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert 0.0 < DIVIDING_EDGE_SHARE <= 1.0
    assert not (PipelineConfig().extra or {}).get(BETWEEN_FILLS_KEY)
