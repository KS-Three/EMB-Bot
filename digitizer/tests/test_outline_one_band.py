"""`cfg.outline_one_band` (2026-11-18, built OFF): an outline band shared by two
or more bodies with a stem between them is sewn as a column per stem and ONE
loop on the band's outer ring, not a loop per face (Becker large's B/E dip).

Gate: no stem, one body, or a gap of two loop widths or more changes nothing."""
from __future__ import annotations

import numpy as np
from shapely.geometry import Point, Polygon, box

from digitizer_core import config as cfgmod
from digitizer_core import machine
from digitizer_core.outline_band import one_band_runs, stem_pieces

W = 2.4


def _band(gap: float, n: int = 2):
    """A 12 mm tall outline with `n` 8 mm wide faces `gap` apart, 3 mm of band round all."""
    faces, x = [], 3.0
    for _ in range(n):
        faces.append(box(x, 3.0, x + 8.0, 21.0))
        x += 8.0 + gap
    outer = box(0.0, 0.0, x - gap + 3.0, 24.0)
    band = Polygon(outer.exterior, [f.exterior for f in faces])
    return band, [(Polygon(f.exterior), W) for f in faces]


def _kw():
    return {"underlay_style": "none", "trim_at_mm": 4.0, "spacing_mm": machine.SATIN_SPACING_MM}


def test_field_defaults_off():
    assert cfgmod.PipelineConfig().outline_one_band is False


def test_a_stem_between_two_faces_is_found():
    band, rings = _band(3.0)
    stems, outer, w = stem_pieces(band, rings)
    assert w == W and len(stems) == 1
    s = stems[0]
    # the stem is the strip between the faces, its middle on the gap's middle line
    assert 11.5 < s.centroid.x < 13.5
    assert s.minimum_rotated_rectangle.area > 20.0


def test_one_face_or_a_wide_gap_has_no_stem():
    band, rings = _band(3.0, n=1)
    assert stem_pieces(band, rings)[0] == []
    band, rings = _band(2.0 * W + 1.0)
    assert stem_pieces(band, rings)[0] == []


def test_no_stem_returns_nothing_so_the_caller_keeps_its_loops():
    band, rings = _band(2.0 * W + 1.0)
    runs, rep = one_band_runs(band, rings, "x", entry=None, trim_at_mm=4.0, underlay=False, satin_kw=_kw())
    assert runs == [] and rep["empty"]


def test_stem_column_and_outer_loop_cover_the_band_and_never_enter_a_face():
    band, rings = _band(3.0)
    runs, rep = one_band_runs(band, rings, "x", entry=None, trim_at_mm=4.0, underlay=False, satin_kw=_kw())
    assert not rep["empty"] and rep["stems"] == 1
    faces = [h for h, _w in rings]
    satin = [r for r in runs if r.kind == "satin"]
    assert len(satin) >= 2
    for r in satin:
        for x, y in r.points:
            for f in faces:
                assert not f.buffer(-0.05).contains(Point(x, y))
    # the outer loop is the last run sewn (the stem is covered once: test below)
    last = np.asarray(satin[-1].points)
    assert last[:, 0].min() < 1.0 and last[:, 0].max() > 21.0     # round the whole word


def test_the_stem_is_sewn_once():
    """The point of the flag: no two satin runs of the stem both cross it."""
    band, rings = _band(3.0)
    runs, _ = one_band_runs(band, rings, "x", entry=None, trim_at_mm=4.0, underlay=False, satin_kw=_kw())
    mid = Polygon([(10.9, 7.0), (14.1, 7.0), (14.1, 17.0), (10.9, 17.0)])
    covering = 0
    for r in runs:
        if r.kind != "satin":
            continue
        p = np.asarray(r.points)
        hit = ((p[:, 0] > 10.9) & (p[:, 0] < 14.1) & (p[:, 1] > 7.0) & (p[:, 1] < 17.0)).any()
        covering += int(hit)
    assert covering == 1
