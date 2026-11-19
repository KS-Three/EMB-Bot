"""`cfg.extra["underfill_keeps_thin_letters"]` (built OFF 2026-11-19).

The Merchant Marine seal at 90 mm: the black keyline round the eagle and the
disc is one ring, black covers most of its outline, so the ring is its own
under-fill and every black shape inside merges into it -- its 27 black ring
letters too, each on a 0.7 mm stroke in a hole of the white disc. The disc
sews on top with every row laid long for pull, the holes close, and "UNITED
STATES MERCHANT MARINE" is gone. ON, a stroke that thin in a hole of another
colour's fill is never merged, and a dark-ink stroke never names a shape of
its own thread as its ground; `thin_letters_after_ground` and
`ink_after_ground` then sew the letters after the white.
"""
from shapely.geometry import Polygon, box

from digitizer_core import silhouette_underfill as su
from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.regions import Region
from digitizer_core.stitchwidth import MEASURED_KEY, PULL_KEY
from digitizer_core.thin_ink import (THIN_LETTER_PULLS, ink_after_ground,
                                     thin_letters_after_ground)

BLACK, WHITE = 4, 2
PULL = 0.3
THIN = 0.7
BOLD = THIN_LETTER_PULLS * PULL + 1.0


def _reg(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, "stitched": True, **meta})


def _holed(outer, *holes):
    return Polygon(outer.exterior.coords, [list(h.exterior.coords)[::-1] for h in holes])


def _letter(i, width):
    x = 8.0 + 6.0 * i
    return box(x, 10.0, x + width, 16.0)


def seal(width=THIN, tagged=True, disc_width=None):
    """A black keyline ring round a white disc; black letters in the disc's
    holes. Black sews first (layer 0), white after (layer 1)."""
    letters = [_letter(i, width) for i in range(4)]
    disc = box(2, 2, 38, 24)
    meta = {MEASURED_KEY: width, PULL_KEY: PULL, **({"text_cluster_id": "TC1"} if tagged else {})}
    disc_meta = {MEASURED_KEY: disc_width, PULL_KEY: PULL} if disc_width else {}
    return [_reg("Sring", _holed(box(-20, -20, 60, 46), disc), BLACK, 0),
            _reg("Sdisc", _holed(disc, *letters), WHITE, 1, **disc_meta),
            *[_reg(f"L{i}", p, BLACK, 0, **meta) for i, p in enumerate(letters)]]


def _merged(regions, **kw):
    (_ring, host, _outline, merged, _inner), = su.plan(regions, **kw)
    assert host.shape_id == "Sring"
    return sorted(merged)


def test_off_the_thin_letters_merge_into_the_black():
    assert _merged(seal()) == ["L0", "L1", "L2", "L3"]


def test_on_thin_letters_in_the_discs_holes_are_kept():
    assert _merged(seal(), keep_thin=True) == []


def test_on_bold_letters_still_merge():
    """MFab's letters: 2-6 mm wide, they show through their holes."""
    assert _merged(seal(width=BOLD), keep_thin=True) == ["L0", "L1", "L2", "L3"]


def test_a_shape_with_no_measured_width_still_merges():
    regs = seal()
    for r in regs:
        r.meta.pop(MEASURED_KEY, None)
    assert _merged(regs, keep_thin=True) == ["L0", "L1", "L2", "L3"]


def test_a_hole_in_a_narrow_column_is_no_ground_hole():
    """The holed shape must be a FILL: only a fill lays its rows long."""
    assert _merged(seal(disc_width=THIN), keep_thin=True) == ["L0", "L1", "L2", "L3"]


def test_a_white_keyline_fields_holes_are_the_riders():
    regs = seal()
    regs[1].meta["sew_enclosed_white"] = "field"
    assert _merged(regs, keep_thin=True) == ["L0", "L1", "L2", "L3"]


def test_a_letter_traced_a_little_onto_the_disc_is_still_in_its_hole():
    """The seal's C and E lie 0.12-0.14 on the white: under `ON_RING_MAX`."""
    regs = seal()
    x0, y0, x1, y1 = regs[2].polygon.bounds
    regs[2].polygon = box(x0, y0, x1, y1 + 0.14 * (y1 - y0))
    assert "L0" not in _merged(regs, keep_thin=True)


def test_kept_letters_sew_after_the_white():
    out, _report = su.apply(seal(), keep_thin=True)
    out = thin_letters_after_ground(out)
    lay = {r.shape_id: r.meta["layer"] for r in out}
    assert lay["Sring"] < lay["Sdisc"] < lay["L0"] == lay["L3"]


def test_a_dark_ink_strokes_ground_is_never_its_own_thread():
    regs = seal()
    for r in regs[2:]:
        r.meta.update({"dark_ink": True, BEAN_LETTER_KEY: [[(0.0, 0.0), (1.0, 1.0)]]})
    kept, _report = su.apply(regs, keep_thin=True)
    before = {r.shape_id: r.meta["layer"] for r in ink_after_ground(kept)}
    assert before["L0"] < before["Sdisc"]                       # after the black ring: buried
    after = {r.shape_id: r.meta["layer"] for r in ink_after_ground(kept, other_thread=True)}
    assert after["Sring"] < after["Sdisc"] < after["L0"]


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("underfill_keeps_thin_letters")
