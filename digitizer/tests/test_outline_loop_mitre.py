"""`cfg.outline_loop_mitre` (2026-10-25; ON since Kent's flip 2026-10-26, "Outline
corners pivot" -- `PRE_FLIP` names the OFF arm): a satin loop round a
letter keeps its far rail at the satin pitch through the letter's convex
corners, as the professional's keyline and outline satin do
(`stage6_border._pivot_ring`).

`keyline_runs` sews `enclosed_white_keyline`'s keyline loops and
`border_from_outline`'s outline loops: one rail on the letter's outline, the
crosses out into the band. Each cross is cast along a normal smoothed over
half a width either side, so through a convex corner the crosses rotate while
their near ends advance one step each and their far ends spread round the
arc -- 1.1 mm apart where the pro's sit 0.4 mm apart, the spikes on MFab's
white keyline at every M-FAB corner (#1059, #1065). The pro's corner is that
same round arc, not a mitre point. ON: crosses put between two whose far ends
part, one per step of the far rail, the near ends' pile short-stitched.
"""
from __future__ import annotations

import hashlib
import math

from shapely.geometry import Point, Polygon, box

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage6_border as sb
from tests.conftest import PRE_FLIP

#: a 10 mm square letter in a 4 mm band round it (y down): its four corners are
#: convex, the band is what the loop crosses into
LETTER = box(0, 0, 10, 10)
BAND = Polygon(box(-4, -4, 14, 14).exterior, [LETTER.exterior.coords])
#: a round letter: no corner anywhere
DISC = Point(5, 5).buffer(5, 64)
ROUND_BAND = Polygon(box(-4, -4, 14, 14).exterior, [DISC.exterior.coords])
#: an L: five convex corners and one concave one, at (4, 4)
ELL = Polygon([(0, 0), (4, 0), (4, 4), (10, 4), (10, 10), (0, 10)])
ELL_BAND = Polygon(box(-4, -4, 14, 14).exterior, [ELL.exterior.coords])
WIDTH = 2.4


def _run(band, letter, on: bool, outline: bool = True):
    """The loop's penetrations in sewing order. `outline`: the
    `border_from_outline` call (holes given, exact cut); False is
    `enclosed_white_keyline`'s (the band's own holes)."""
    kw = {"holes": [(Polygon(letter.exterior), WIDTH)]} if outline else {"width_mm": WIDTH}
    with sb.loop_mitre_scope(on):
        runs, rep = sb.keyline_runs(band, "k", reach=band, entry=(-3.0, -3.0), trim_at_mm=3.0, **kw)
    sat = [r for r in runs if r.kind == "satin"]
    assert len(sat) == 1
    return list(sat[0].points), rep


def _md5(pts) -> str:
    h = hashlib.md5()
    for p in pts:
        h.update(f"{p[0]:.6f},{p[1]:.6f}|".encode())
    return h.hexdigest()


def _far(pts, letter, corner, within):
    """The far rail's penetrations (out in the band) round `corner`, in
    sewing order."""
    ring = letter.exterior
    return [p for p in pts
            if ring.distance(Point(p)) > 0.5 * WIDTH and math.dist(p, corner) < within]


def _max_step(seq) -> float:
    return max(math.dist(a, b) for a, b in zip(seq, seq[1:]))


def test_flag_is_on_by_default():
    # Kent's flip on the wave-3 flip sheet 2026-10-26: "Outline corners pivot"
    assert PipelineConfig().outline_loop_mitre is True
    assert PRE_FLIP["outline_loop_mitre"] is False


def test_the_scope_sets_the_flag_and_puts_it_back():
    assert sb._LOOP_MITRE.get() is False
    with sb.loop_mitre_scope(True):
        assert sb._LOOP_MITRE.get() is True
    assert sb._LOOP_MITRE.get() is False
    with sb.loop_mitre_scope(False):
        assert sb._LOOP_MITRE.get() is False


def test_a_plan_sets_the_flag_from_its_config(monkeypatch):
    from digitizer_core import pipeline
    seen = []
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda _r, _c: seen.append(sb._LOOP_MITRE.get()))
    pipeline.plan_stitches(object(), PipelineConfig(outline_loop_mitre=PRE_FLIP["outline_loop_mitre"]))
    pipeline.plan_stitches(object(), PipelineConfig(outline_loop_mitre=True))
    pipeline.plan_stitches(object(), PipelineConfig())          # the default: ON
    assert seen == [False, True, True]
    assert sb._LOOP_MITRE.get() is False


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("outline_loop_mitre code reached with the flag off")
    monkeypatch.setattr(sb, "_pivot_ring", boom)
    for outline in (True, False):
        _run(BAND, LETTER, False, outline)
        _run(ROUND_BAND, DISC, False, outline)


def test_off_is_the_loop_as_it_was():
    # md5 of the loops main sewed before the flag existed (c97fecd4), both
    # call forms: border_from_outline's and enclosed_white_keyline's
    assert _md5(_run(BAND, LETTER, False)[0]) == OFF_SQUARE_MD5
    assert _md5(_run(ROUND_BAND, DISC, False)[0]) == OFF_DISC_MD5
    # (the band is wide enough that neither form cuts a cross: the same loop)
    assert _md5(_run(BAND, LETTER, False, outline=False)[0]) == OFF_SQUARE_MD5
    assert _md5(_run(ELL_BAND, ELL, False)[0]) == OFF_ELL_MD5


def test_off_the_corner_fans_its_far_rail_apart():
    pts, _ = _run(BAND, LETTER, False)
    fars = _far(pts, LETTER, (10.0, 10.0), 1.6 * WIDTH)
    # the far ends round the arc: more than twice the satin pitch apart
    assert _max_step(fars) > 2.0 * machine.BORDER_DENSITY_MM


def test_on_the_far_rail_keeps_the_satin_pitch_round_every_corner():
    pts, rep = _run(BAND, LETTER, True)
    assert rep["loops"] == 1
    # (0, 0) is where the loop joins itself, from the entry: its far rail is
    # two passes in sewing order, read on the other three
    for corner in ((10.0, 0.0), (10.0, 10.0), (0.0, 10.0)):
        fars = _far(pts, LETTER, corner, 1.6 * WIDTH)
        # the pro's: 0.41-0.44 mm median through a corner; OFF's 0.87-1.12
        assert _max_step(fars) <= 1.25 * machine.BORDER_DENSITY_MM, corner


def test_on_the_corner_is_the_round_arc_not_a_mitre_point():
    pts, _ = _run(BAND, LETTER, True)
    # nothing further from the letter than the loop's width: no overshoot
    assert all(LETTER.buffer(WIDTH + 0.02, 64).contains(Point(p)) for p in pts)
    # and the corner of the square offset, where a mitre's point would sit
    # (sqrt 2 widths out), stays as bare as the round arc leaves it
    mitre = (10.0 + WIDTH, 10.0 + WIDTH)
    assert min(math.dist(p, mitre) for p in pts) > 0.9 * (math.sqrt(2.0) - 1.0) * WIDTH


def test_on_the_pivot_never_sews_one_hole_twice():
    pts, _ = _run(BAND, LETTER, True)
    # stitches alternate rails: a rail's consecutive holes sit two apart
    holes = [math.dist(pts[j], pts[j - 2]) for j in range(2, len(pts))]
    assert min(holes) >= machine.SATIN_SHORT_STITCH_AT_MM - 1e-9
    # and the pile on the corner is short-stitched: some near ends pulled
    # out into the band, off the outline
    ring = LETTER.exterior
    corner = (10.0, 10.0)
    near = [p for p in pts if math.dist(p, corner) < 0.6 * WIDTH]
    assert any(0.2 < ring.distance(Point(p)) < 0.5 * WIDTH for p in near)


def test_on_adds_crosses_only_round_the_convex_corners(monkeypatch):
    seen = []
    real = sb._pivot_ring

    def spy(ring_pts, normals, width, step):
        out = real(ring_pts, normals, width, step)
        seen.append((list(ring_pts), out))
        return out
    monkeypatch.setattr(sb, "_pivot_ring", spy)
    off, _ = _run(ELL_BAND, ELL, False)
    on, _ = _run(ELL_BAND, ELL, True)
    assert len(on) > len(off)
    (ring, (out_p, _n)), = seen
    old = set(ring)
    new = [p for p in out_p if p not in old]
    assert new
    convex = [(0, 0), (4, 0), (10, 4), (10, 10), (0, 10)]
    assert all(min(math.dist(p, c) for c in convex) < 0.6 * WIDTH for p in new)
    # the concave corner keeps its crosses as they were
    assert all(math.dist(p, (4.0, 4.0)) > WIDTH for p in new)


def test_on_a_round_letter_is_the_loop_as_it_was():
    assert _md5(_run(ROUND_BAND, DISC, True)[0]) == _md5(_run(ROUND_BAND, DISC, False)[0])


OFF_SQUARE_MD5 = "6970ba8f13ade30553b9824dd0e6787c"
OFF_DISC_MD5 = "1953a4080923f86d10bf9ba58b3620ea"
OFF_ELL_MD5 = "9fdcfbd5e0fc9c654d8632ba732225ef"
