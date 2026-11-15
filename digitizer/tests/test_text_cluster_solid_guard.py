"""`cfg.text_cluster_solid_guard` (built OFF 2026-11-13 as an extra, ON since
2026-11-14 by Kent's flip, "Flip both ON"): a solid
blob is no glyph.

+Jakarta's mark is a grid of equal solid squares. At 80 mm three of them in a
row (2.54 x 2.62 mm, 2.71-2.75 mm apart) passed the letter door -- aspect
0.97, a square's skeleton a tidy X -- and clustered as a three-letter word.
The small-text re-set grew that "word" x1.52 plus 0.52 mm a side and closed
its gaps to 0.59 mm; sewn as satin the squares' needle paths touched, and Kent
saw three of the five squares twice their size, fused into one bar.

ON, a cluster `SOLID_GROUP_SHARE` (3/4) of whose members are solid blobs --
the stroke (2 x the mean skeleton half-width) at least `SOLID_STROKE_FRAC` of
the longer side -- is not tagged. One blob is not enough: a small letter whose
counter stage 4 filled is one too. Every blob is too much to ask: the mark's
cluster at 80 mm was its five squares and its corner triangle (0.33). OFF: the
tagger as it was, byte for byte.
"""
from __future__ import annotations

import inspect

from shapely.geometry import Polygon, box

from digitizer_core import textcluster as tc
from digitizer_core.regions import Region
from tests.test_small_text import _glyphs, _scene


def _squares(n: int = 3, side: float = 2.6, gap: float = 2.7, x0: float = -12.0, y0: float = -8.0):
    return [Region(f"Ssq{i}", box(x0 + i * (side + gap), y0, x0 + i * (side + gap) + side, y0 + side),
                   3, "3", side * side) for i in range(n)]


def _tags(regions):
    return {r.shape_id: r.meta.get("text_cluster_id") for r in regions}


def test_a_row_of_solid_squares_is_a_word_off_and_no_word_on():
    regions = _squares()
    tc.detect_text_clusters(regions, None)
    assert len({v for v in _tags(regions).values() if v}) == 1, _tags(regions)
    assert all(_tags(regions).values()), "OFF: the three squares tag as one cluster (the fault)"

    regions = _squares()
    tc.detect_text_clusters(regions, None, solid_guard=True)
    assert not any(_tags(regions).values()), _tags(regions)


def _mark():
    """+Jakarta's mark as stage 4 traced it at 80 mm: a corner triangle over a
    grid of equal squares (a 3-square row, one square above and one below)."""
    tri = Region("Stri", Polygon([(-40.0, -14.5), (-37.46, -14.5), (-40.0, -11.9)]), 3, "3", 3.3)
    sq = [Region(f"Sm{i}", box(x, y, x + 2.62, y + 2.62), 3, "3", 6.9)
          for i, (x, y) in enumerate([(-34.75, -14.6), (-40.0, -11.54), (-34.75, -11.54),
                                      (-29.38, -11.54), (-34.75, -6.2)])]
    return [tri] + sq


def test_the_marks_squares_and_corner_triangle_are_no_word_on():
    off = _mark()
    tc.detect_text_clusters(off, None, part_touching=True, nest_door_aspect=True)
    assert all(_tags(off).values()), _tags(off)
    on = _mark()
    tc.detect_text_clusters(on, None, part_touching=True, nest_door_aspect=True, solid_guard=True)
    assert not any(_tags(on).values()), _tags(on)


def _cand(r: Region) -> tc._Candidate:
    st = tc._stats_of_polygon(r.polygon)
    x0, y0, x1, y1 = r.polygon.bounds
    return tc._Candidate(region=r, height_mm=y1 - y0, width_mm=x1 - x0, stroke_mean_mm=st.mean_mm,
                         stroke_cv=st.cv, cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0)


def test_a_square_reads_solid_an_open_letter_does_not_and_a_filled_o_does():
    """Why the rule is per CLUSTER: one blob may be a letter whose counter
    stage 4 filled (the scene's tracer drops every counter, as stage 4 does
    under its hole floor)."""
    assert tc._solid(_cand(_squares(1)[0]))
    regions, _p = _scene(text_at=((180, 262),), words=("beyond coal",))
    g = {r.shape_id: r for r in _glyphs(regions)}
    assert not tc._solid(_cand(g["Sg0"])) and not tc._solid(_cand(g["Sg9"]))     # b, l
    assert tc._solid(_cand(g["Sg3"]))                                            # o, filled


def test_a_line_of_letters_beside_the_squares_tags_the_same_on_and_off():
    def scene():
        regions, _p = _scene(text_at=((180, 262),), words=("beyond coal",))
        return regions + _squares()

    off = scene()
    tc.detect_text_clusters(off, None)
    on = scene()
    tc.detect_text_clusters(on, None, solid_guard=True)
    letters = [r.shape_id for r in _glyphs(off)]
    assert sum(bool(_tags(off)[s]) for s in letters) >= 3
    assert {s: _tags(on)[s] for s in letters} == {s: _tags(off)[s] for s in letters}
    assert all(_tags(off)[f"Ssq{i}"] for i in range(3))
    assert not any(_tags(on)[f"Ssq{i}"] for i in range(3))


def test_on_is_the_shipped_default_and_the_pipeline_passes_the_field():
    # Kent's flip 2026-11-14 ("Flip both ON"): the callee keeps False as its
    # own default (the call as it was), the pipeline passes the field
    from digitizer_core import PipelineConfig, pipeline
    assert inspect.signature(tc.detect_text_clusters).parameters["solid_guard"].default is False
    assert PipelineConfig().text_cluster_solid_guard is True
    assert PipelineConfig().small_text_reset_one_baseline is True
    src = inspect.getsource(pipeline)
    assert "if cfg.text_cluster_solid_guard else" in src
    assert "if cfg.small_text_reset_one_baseline else" in src
    assert 'cfg.extra.get("text_cluster_solid_guard")' not in src
    assert 'cfg.extra.get("small_text_reset_one_baseline")' not in src
