"""The under-fill rim sews only on fabric edges (`cfg.silhouette_underfill_rim_fabric_edges`, ON since 2026-11-16).

`silhouette_underfill_rim` closes one satin loop round the host's whole
outline. It was read off MFab's band and Fremont's ground, whose outlines are
the design's own edge. On the US National Park Service arrowhead (Commons
PNG, 75 mm) the orange ground hosts its under-fill among other sewn shapes,
and its rim ran along the tree and the mountain: a raised orange halo round
a tree the art draws with none (30,074 stitches; 25,336 with this ON).

ON, the rim skips every stretch of the host's visible outline another sewn
shape shares and sews the rest as open arcs. An outline nothing shares keeps
the closed loop, byte for byte.

Synthetic shapes: the arrowhead itself is not in the repo.
"""
from __future__ import annotations

from shapely.geometry import LineString, Point, box

from digitizer_core import PipelineConfig, stitches
from tests.test_silhouette_underfill import _md5, _reg, _sew, mfab

RIM = dict(silhouette_underfill=True, silhouette_underfill_rim=True,
           silhouette_underfill_rim_fabric_edges=False)
ON = {**RIM, "silhouette_underfill_rim_fabric_edges": True}
#: the band's right edge, x = 60, where the neighbour abuts it
SEAM = LineString([(60, 2), (60, 22)])
LEFT = LineString([(0, 2), (0, 22)])


def with_neighbour():
    """MFab's band with another colour's block abutting its whole right edge,
    sewn after it."""
    return mfab() + [_reg("Sside", box(60, 0, 80, 24), 2, 2)]


def _rim_points(blocks, near, reach=1.2):
    """The band's satin / border needle points within `reach` of `near`,
    sewn after its last fill run."""
    out = []
    for b in blocks:
        mine = [r for r in b.runs if r.shape_id == "Sring"]
        fills = [i for i, r in enumerate(mine) if r.kind == stitches.FILL]
        if not fills:
            continue
        for r in mine[fills[-1] + 1:]:
            if r.kind in (stitches.SATIN, stitches.BORDER):
                out += [p for p in r.points if near.distance(Point(p)) <= reach]
    return out


def test_flag_default_is_on():
    # ON since 2026-11-16 (Kent, from the ten-logo sheets: "Flip both ON")
    assert PipelineConfig().silhouette_underfill_rim_fabric_edges is True


def test_the_defect_the_rim_runs_along_a_neighbour():
    _planned, blocks = _sew(with_neighbour(), **RIM)
    assert len(_rim_points(blocks, SEAM)) > 20
    assert len(_rim_points(blocks, LEFT)) > 20


def test_on_the_rim_skips_the_shared_edge_and_keeps_the_fabric_edge():
    _planned, blocks = _sew(with_neighbour(), **ON)
    assert _rim_points(blocks, SEAM, reach=0.8) == []
    assert len(_rim_points(blocks, LEFT)) > 20


def test_on_an_outline_nothing_shares_keeps_its_closed_loop_byte_for_byte():
    assert _md5(_sew(mfab(), **ON)[1]) == _md5(_sew(mfab(), **RIM)[1])


def test_on_a_short_touch_is_not_a_seam():
    """A neighbour along 1 mm of the edge (under twice the rim's width even
    with stage 5's pull growth on both its sides): a touch, and the loop
    stays closed."""
    regs = mfab() + [_reg("Stab", box(60, 10, 70, 11), 2, 2)]
    assert _md5(_sew(regs, **ON)[1]) == _md5(_sew(regs, **RIM)[1])


def test_read_only_with_the_rim():
    regs = with_neighbour()
    no_rim = dict(silhouette_underfill=True, silhouette_underfill_rim=False)
    assert (_md5(_sew(regs, silhouette_underfill_rim_fabric_edges=True, **no_rim)[1])
            == _md5(_sew(regs, silhouette_underfill_rim_fabric_edges=False, **no_rim)[1]))
