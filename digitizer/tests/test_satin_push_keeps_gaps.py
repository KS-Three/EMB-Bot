"""`cfg.satin_push_keeps_gaps` (built OFF 2026-11-14): the satin rail
push is held out of a shape's bays and its gaps to same-thread ink exactly as
it is held out of a counter (`stage6_satin.PUSH_KEEP_MARGIN_MM`).

Kent's merged-letter pins, traced in `docs/closed-counters-traced-2026-11-14.md`:
Gaulke's E and S kept their gaps through stage 5 and lost them to the rail
push, which already held back from a hole but not from a bay or a neighbour.
"""
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core.stage6_satin import _push_rails

PULL = 0.3
FLOOR = 1.5


def _u_shape(slot: float = 1.0) -> Polygon:
    """Two 2 mm arms, `slot` mm apart, joined by a 2 mm bar at the bottom: the
    slot is a BAY (exterior concavity), not a hole."""
    left = box(0.0, 0.0, 2.0, 10.0)
    right = box(2.0 + slot, 0.0, 4.0 + slot, 10.0)
    bar = box(0.0, 0.0, 4.0 + slot, 2.0)
    return unary_union([left, right, bar])


def test_off_is_the_engine_as_it_was():
    poly = _u_shape()
    a, b = [(2.0, 6.0)], [(0.0, 6.0)]
    assert _push_rails(a, b, poly, PULL, FLOOR) == _push_rails(a, b, poly, PULL, FLOOR, keep=None)
    out_a, out_b = _push_rails(a, b, poly, PULL, FLOOR)
    # off: the rail facing the bay is pushed the full pull into it
    assert abs(out_a[0][0] - 2.3) < 1e-9 and abs(out_b[0][0] + 0.3) < 1e-9


def test_a_bay_narrower_than_the_floor_takes_no_push_on():
    poly = _u_shape(slot=1.0)
    out_a, out_b = _push_rails([(2.0, 6.0)], [(0.0, 6.0)], poly, PULL, FLOOR, keep=poly)
    assert abs(out_a[0][0] - 2.0) < 1e-9          # held at the bay's edge
    assert abs(out_b[0][0] + 0.3) < 1e-9          # open fabric: the full pull, as before


def test_a_wider_bay_gives_up_what_the_floor_spares():
    poly = _u_shape(slot=2.0)
    out_a, _ = _push_rails([(2.0, 6.0)], [(0.0, 6.0)], poly, PULL, FLOOR, keep=poly)
    # (2.0 - 1.5) / 2 = 0.25 mm each side, under the 0.3 mm pull
    assert abs(out_a[0][0] - 2.25) < 1e-9


def test_a_counter_reads_as_before():
    """A hole is held by the old rule; `keep` adds nothing there."""
    poly = box(0.0, 0.0, 5.0, 10.0).difference(box(2.0, 3.0, 3.0, 7.0))
    a, b = [(2.0, 5.0)], [(0.0, 5.0)]
    assert _push_rails(a, b, poly, PULL, FLOOR, keep=poly) == _push_rails(a, b, poly, PULL, FLOOR)


def test_same_thread_neighbour_is_a_gap():
    me = box(0.0, 0.0, 2.0, 10.0)
    nb = box(2.8, 0.0, 4.8, 10.0)
    a, b = [(2.0, 5.0)], [(0.0, 5.0)]
    out_a, _ = _push_rails(a, b, me, PULL, FLOOR, keep=unary_union([me, nb]))
    assert abs(out_a[0][0] - 2.0) < 1e-9
    # its own artwork alone is no neighbour: the full pull
    out_a, _ = _push_rails(a, b, me, PULL, FLOOR, keep=me)
    assert abs(out_a[0][0] - 2.3) < 1e-9


def test_far_neighbour_is_not_reached():
    me = box(0.0, 0.0, 2.0, 10.0)
    nb = box(6.0, 0.0, 8.0, 10.0)
    out_a, _ = _push_rails([(2.0, 5.0)], [(0.0, 5.0)], me, PULL, FLOOR, keep=unary_union([me, nb]))
    assert abs(out_a[0][0] - 2.3) < 1e-9


def test_a_floor_given_with_the_ink_is_the_gap_floor():
    """`satin_push_keeps_gaps` as a number: that floor for gaps, the counter
    rule's own floor untouched."""
    poly = _u_shape(slot=1.0)
    out_a, _ = _push_rails([(2.0, 6.0)], [(0.0, 6.0)], poly, PULL, FLOOR, keep=(poly, 0.5))
    assert abs(out_a[0][0] - 2.25) < 1e-9          # (1.0 - 0.5) / 2


def test_a_cancel_lands_inside_the_ray_pass():
    """The ray pass checks the deadline per block of rays, so a Cancel pressed
    during a long column stops it there (the review's Cancel-latency rule)."""
    import threading

    import pytest

    from digitizer_core import deadline
    from digitizer_core.stage6_satin import _kept_limits
    poly = _u_shape(slot=1.0)
    stop = threading.Event()
    stop.set()
    with deadline.scope(None, cancel=stop):
        with pytest.raises(deadline.Cancelled) as hit:
            _kept_limits([(2.0, 6.0)], [(0.0, 6.0)], poly, None, 2.6, PULL, FLOOR)
    assert "keep" in str(hit.value)


def test_limits_match_the_rule_on_a_column():
    """Every cross of a U's left arm: the rail facing the slot is held, the
    outer rail takes the full pull."""
    from digitizer_core.stage6_satin import _kept_limits
    poly = _u_shape(slot=1.0)
    ys = [3.0 + 0.5 * k for k in range(12)]
    lim_a, lim_b = _kept_limits([(2.0, y) for y in ys], [(0.0, y) for y in ys], poly, None,
                                2.0 * PULL + FLOOR + 0.5, PULL, FLOOR)
    assert all(v == 0.0 for v in lim_a)
    assert all(v == float("inf") for v in lim_b)
