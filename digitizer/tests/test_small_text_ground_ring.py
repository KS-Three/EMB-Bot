"""`cfg.small_text_reset_ground_ring` (ON since 2026-11-15, Kent; built OFF 2026-11-14): the
ground a re-set line sits IN is its ground, not an obstacle.

Fremont's "1895" sits in a hole of the design-wide white field. The field
covers 0.48 of the line's hull (the digits' ink and their own counters take
the rest), under the half the ground test asked for, so it counted as an
obstacle at distance 0 and held the date -- and "EST", its other half -- at
the drawn size (`no_room`, `blocked_by` a thread-2 shape spanning the design).
"""
from __future__ import annotations

from shapely.geometry import Point, Polygon, box

from digitizer_core import small_text as st

HULL = box(0, 0, 6, 2)                       # a short line of digits, 6 x 2 mm


def _field_with_letters(ink_share: float) -> Polygon:
    """A design-wide field with the line's letters cut out of it, leaving the
    field `1 - ink_share` of the hull."""
    w = 6.0 * ink_share
    letters = [box(0.2 + i * 1.5, 0.0, 0.2 + i * 1.5 + w / 4, 2.0) for i in range(4)]
    field = box(-40, -20, 40, 20)
    for g in letters:
        field = field.difference(g)
    return field


def test_off_is_the_half_hull_rule():
    field = _field_with_letters(0.52)
    share = field.intersection(HULL).area / HULL.area
    assert 0.45 < share < 0.5
    assert st._is_ground(field, HULL) is False
    assert st._is_ground(field, HULL, ring=False) is False
    assert st._is_ground(_field_with_letters(0.3), HULL) is True


def test_on_the_field_the_line_sits_in_is_its_ground():
    assert st._is_ground(_field_with_letters(0.52), HULL, ring=True) is True


def test_a_thin_frame_hugging_the_line_is_still_in_its_way():
    frame = box(-0.2, -0.2, 6.2, 2.2).difference(box(-0.05, -0.05, 6.05, 2.05))
    assert st._is_ground(frame, HULL, ring=True) is False


def test_fremont_est_1895_is_raised_and_sews_as_grown_only_on():
    """The real case, stages 0-4 of the Studio's request for the 92.6 mm hat:
    OFF the date is `no_room` (the field in its way); ON it is re-set, and
    its letters' bean spines (read at the drawn size, which stage 7 sews)
    follow the grown letter (`small_text_reset_bean_follows`)."""
    from pathlib import Path

    from digitizer_core.pipeline import build_generation
    from digitizer_service.app import _decode
    from tools import pro_pair as pp
    art = Path(__file__).resolve().parents[1] / "testdata" / "photo" / "logo_hotel_fremont.webp"
    data = art.read_bytes()

    def date_rows(extra):
        gen = build_generation(_decode(data), pp.config(92.6, "hat_front", extra), exif_source=data)
        rows = [r for r in gen.small_text_reset or [] if r.get("cap_mm") and r["cap_mm"] < 2.0]
        date = [r for r in gen.regions if r.thread_number == "0862" and -15.5 < r.polygon.centroid.y < -9.5
                and abs(r.polygon.centroid.x) < 14 and r.meta.get("small_text_enlarged")]
        return rows, date
    rows, date = date_rows({"small_text_reset_ground_ring": False,
                            "small_text_reset_bean_follows": False})
    assert len(rows) == 2 and all(r.get("skipped") == "no_room" for r in rows), rows
    assert date == []
    rows, date = date_rows({"small_text_reset_ground_ring": True,
                            "small_text_reset_bean_follows": True})
    assert len(rows) == 2 and all(r.get("scale", 0) > 1.5 for r in rows), rows
    assert len(date) == 7
    assert min(r.polygon.bounds[3] - r.polygon.bounds[1] for r in date) > 3.5   # was 1.9 mm
    for r in date:          # every spine point inside its grown letter (not at the drawn place)
        pts = [pt for chain in r.meta["bean_letter_spines"] for pt in chain]
        assert pts
        grown = r.polygon.buffer(0.3)
        assert sum(grown.contains(Point(pt)) for pt in pts) >= 0.9 * len(pts), r.shape_id


def test_a_neighbour_beside_the_line_is_still_in_its_way():
    # a shape along one long side, overlapping the hull's edge a little
    beside = box(-1, -1.5, 7, 0.6)
    assert beside.intersection(HULL).area / HULL.area >= st.GROUND_MIN_IN
    assert st._is_ground(beside, HULL, ring=True) is False
