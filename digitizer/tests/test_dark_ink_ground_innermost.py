"""`cfg.extra["dark_ink_ground_innermost"]` (built OFF 2026-11-17).

A dark-ink stroke's ground is the shape whose OUTLINE covers most of it
(`thin_ink._ground_of`). Outlines nest, so a seal's field, its ring and
everything between cover a ring letter equally and the first in list order
won. The US Coast Guard seal at 90 mm: 25 navy ring letters named the aqua
field, not the white ring they stand on; `ink_after_ground` left them where
they were, the white ring sewed after them, and the ring text was buried.
ON, the smallest of the equally covering outlines is the ground.
"""
from shapely.geometry import Point, box

from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.regions import Region
from digitizer_core.thin_ink import _ground_of, ink_after_ground

AQUA, WHITE, NAVY = 1, 2, 3


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, "stitched": True, **meta})


def _seal():
    """A field with a hole, a ring in the hole, and a letter cut out of the ring."""
    letter_poly = box(18.0, -2.0, 19.0, 2.0)
    disc = Point(0, 0).buffer(22.0)
    field = _region("field", box(-45, -45, 45, 45).difference(disc), AQUA, 0)
    ring = _region("ring", disc.difference(Point(0, 0).buffer(14.0)).difference(letter_poly), WHITE, 2)
    letter = _region("letter", letter_poly, NAVY, 1, dark_ink=True, **{BEAN_LETTER_KEY: [[(18.5, -2), (18.5, 2)]]})
    return field, ring, letter


def test_off_the_first_of_equal_outlines_wins():
    field, ring, letter = _seal()
    assert _ground_of(letter, [field, ring]) is field
    assert _ground_of(letter, [ring, field]) is ring


def test_on_the_innermost_outline_is_the_ground_whatever_the_order():
    field, ring, letter = _seal()
    assert _ground_of(letter, [field, ring], innermost=True) is ring
    assert _ground_of(letter, [ring, field], innermost=True) is ring


def test_on_a_shape_that_covers_more_still_wins_over_a_smaller_one():
    """Innermost breaks TIES only: a small shape that covers half the stroke
    does not beat a large one that covers all of it."""
    _field, ring, letter = _seal()
    half = _region("half", box(18.0, -2.0, 19.0, 0.0), WHITE, 0)
    assert _ground_of(letter, [half, ring], innermost=True) is ring


def test_on_a_stroke_under_half_covered_has_no_ground():
    _field, _ring, letter = _seal()
    sliver = _region("sliver", box(18.0, -2.0, 19.0, -1.0), WHITE, 0)
    assert _ground_of(letter, [sliver], innermost=True) is None


def test_the_letter_moves_to_sew_after_its_ring_only_with_the_flag():
    """The fault itself: the ring's layer is later than the letter's."""
    regions = list(_seal())

    def order(regs):
        return [r.shape_id for r in sorted(regs, key=lambda r: r.meta["layer"])]

    off = ink_after_ground(regions)
    assert order(off).index("letter") < order(off).index("ring")        # buried
    on = ink_after_ground(regions, innermost=True)
    assert order(on).index("letter") > order(on).index("ring")          # on top


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("dark_ink_ground_innermost")
