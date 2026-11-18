"""`cfg.extra["thin_letters_after_ground"]` (built OFF 2026-11-18).

Light lettering on a darker ring: white is the first thread, so the letters
sewed first and the ring filled round them afterwards. Each fill row is laid
long at both ends for the fabric's pull, so the ring's thread covered about
half of every letter stroke from its two edges. The Commerce seal at 90 mm:
44 white ring letters on 1.0-1.3 mm strokes read as hairlines. ON, a line
that thin sews after the ground it is written on.
"""
from shapely.geometry import Point, box

from digitizer_core.regions import Region
from digitizer_core.stitchwidth import MEASURED_KEY, PULL_KEY
from digitizer_core.thin_ink import THIN_LETTER_KEY, THIN_LETTER_PULLS, thin_letters_after_ground

WHITE, BLUE, BLACK = 0, 3, 5
PULL = 0.3


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, "stitched": True, **meta})


def _letter(sid, x, width, tagged=True, thread=WHITE, layer=0):
    meta = {MEASURED_KEY: width, PULL_KEY: PULL}
    if tagged:
        meta["text_cluster_id"] = "TC1"
    return _region(sid, box(x, 17.0, x + width, 20.0), thread, layer, **meta)


def _seal(widths=(1.0, 1.1, 1.3), ring_layer=2):
    letters = [_letter(f"L{i}", -3.0 + 2.5 * i, w) for i, w in enumerate(widths)]
    disc = Point(0, 0).buffer(24.0)
    ring_poly = disc.difference(Point(0, 0).buffer(14.0))
    for l_ in letters:
        ring_poly = ring_poly.difference(l_.polygon)
    field = _region("field", box(-45, -45, 45, 45).difference(disc), BLACK, 1)
    ring = _region("ring", ring_poly, BLUE, ring_layer)
    return field, ring, letters


def _layers(regs):
    return {r.shape_id: r.meta["layer"] for r in regs}


def test_thin_letters_move_to_sew_right_after_their_ring():
    field, ring, letters = _seal()
    out = thin_letters_after_ground([*letters, field, ring])
    lay = _layers(out)
    assert all(lay[l_.shape_id] == lay["ring"] + 1 for l_ in letters)
    assert lay["field"] < lay["ring"]
    assert all(r.meta.get(THIN_LETTER_KEY) for r in out if r.shape_id.startswith("L"))
    assert not any(r.meta.get(THIN_LETTER_KEY) for r in out if not r.shape_id.startswith("L"))


def test_the_line_is_judged_whole_not_letter_by_letter():
    """Commerce: strokes read 0.97 to 1.30 mm. A per-letter limit split the
    ring text into fat and hairline letters; the median decides for all."""
    limit = THIN_LETTER_PULLS * PULL
    field, ring, letters = _seal(widths=(limit - 0.5, limit - 0.4, limit - 0.1))
    lay = _layers(thin_letters_after_ground([*letters, field, ring]))
    assert len({lay[l_.shape_id] for l_ in letters}) == 1 and lay["L0"] > lay["ring"]


def test_bold_lettering_stays_where_it_is():
    limit = THIN_LETTER_PULLS * PULL
    field, ring, letters = _seal(widths=(limit + 0.2, limit + 0.4, limit + 0.6))
    regs = [*letters, field, ring]
    assert thin_letters_after_ground(regs) is regs


def test_letters_already_after_their_ground_are_left():
    field, ring, letters = _seal()
    regs = [field, ring, *[_letter(l_.shape_id, l_.polygon.bounds[0], 1.0, layer=4) for l_ in letters]]
    assert thin_letters_after_ground(regs) is regs


def test_an_untagged_narrow_shape_of_the_thread_moves_with_the_line():
    """A star, or a letter the text read missed, on the same ring."""
    field, ring, letters = _seal()
    star = _letter("star", 6.0, 1.2, tagged=False)
    ring.polygon = ring.polygon.difference(star.polygon)
    lay = _layers(thin_letters_after_ground([*letters, star, field, ring]))
    assert lay["star"] == lay["L0"] > lay["ring"]


def test_untagged_shapes_alone_never_move():
    field, ring, _letters = _seal()
    star = _letter("star", 6.0, 1.2, tagged=False)
    regs = [star, field, ring]
    assert thin_letters_after_ground(regs) is regs


def test_dark_ink_strokes_are_not_this_rules():
    field, ring, letters = _seal()
    for l_ in letters:
        l_.meta["dark_ink"] = True
    regs = [*letters, field, ring]
    assert thin_letters_after_ground(regs) is regs


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("thin_letters_after_ground")
