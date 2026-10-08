"""`cfg.satin_slab_serifs`: a slab serif's axis is its own column, not a
cap. Kent's pick after the join-square flip (2026-10-06): "T-shaped slabs:
own column, not a cap".

Two fixtures, two mechanisms, both read off Hotel Fremont at 80 mm on the
real path (the seam-closed polygon `satin_shape` skeletonises -- a direct
`extract_strokes` on the stage-5 polygon reads a DIFFERENT skeleton, which
is how the first draft of this flag was built against a defect the shipped
engine did not have):

* The T (`testdata/fremont_T_slab_foot.json`): its foot's two halves run
  into the foot's corners, so neither end was exposed by a pruned fork and
  the twig rule (`_CAP_ARM_MAX_SPURS`) took the pair for a square cap's
  I-beam and erased both. The stem then ended free at the foot and the
  foot's protrusions sewed as nothing but its terminal fan: 0.48 mm2 of
  the foot's bottom millimetre bare. ON, `_prune_spurs` keeps a pair that
  is square to the stem (`_slab_pair`), the merge welds it, and the foot
  is a 2.5 mm column of its own -- 0.02 mm2 bare, +14 stitches, +1 hop.

* The N (`testdata/fremont_N_slab_foot.json`): its left foot's halves
  survived the twig rule but meet at 144 deg, and `satin_junction_stack`'s
  30 deg weld limit refused the pair; one half fell to the stub filter and
  the foot sewed as a half column from the stem outward. ON, the merge
  welds slab halves whatever their turn, and the foot runs rail to rail.

What stays: a cap's I-beam (forks 45 deg off the stem's axis) and a corner
twig beside a hanging slab (the E's arms, the T's bar: 125-135 deg apart,
the twig 40 deg off square) are not slab pairs -- the T's bar and its two
hanging slabs are byte-identical ON and OFF.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from shapely import wkt
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.stage6_satin import satin_shape

ROOT = Path(__file__).resolve().parent.parent
T_FIXTURE = ROOT / "testdata" / "fremont_T_slab_foot.json"
N_FIXTURE = ROOT / "testdata" / "fremont_N_slab_foot.json"


def _fixture(path):
    f = json.loads(path.read_text(encoding="utf-8"))
    kw = dict(f["kwargs"])
    kw["max_width_mm"] = math.inf if kw["max_width_mm"] == "inf" else kw["max_width_mm"]
    kw["start_near"] = tuple(kw["start_near"])
    kw["end_near"] = tuple(kw["end_near"])
    return wkt.loads(f["poly_wkt"]), wkt.loads(f["art_poly_wkt"]), kw


def _runs(path, slab_serifs):
    poly, art, kw = _fixture(path)
    runs, report = satin_shape(poly, "S1", art_poly=art, join_square=True,
                               slab_serifs=slab_serifs, **kw)
    assert not report["empty"]
    return runs, art


def _foot_band(art, depth_mm=1.0):
    x0, y0, x1, y1 = art.bounds
    return box(x0 - 1.0, y1 - depth_mm, x1 + 1.0, y1 + 1.0).intersection(art)


def _bare(runs, region):
    thread = unary_union([LineString(r.points).buffer(machine.COVERAGE_THREAD_W_MM / 2)
                          for r in runs if r.kind in ("satin", "underlay") and len(r.points) > 1])
    return region.difference(thread).area


def _foot_columns(runs, art, depth_mm=1.3):
    """Satin runs that lie WHOLLY in the artwork's bottom `depth_mm`: the
    foot is 0.8 mm tall and its column's crosses carry the 0.3 mm pull on
    each rail, so a foot column reaches 1.1 mm up; a stem's column spans
    the letter."""
    floor = art.bounds[3] - depth_mm
    return [r for r in runs if r.kind == "satin" and all(p[1] >= floor for p in r.points)]


def test_defaults_are_off():
    """Built OFF: the function default and the config default both. The
    flip is Kent's, on the renders."""
    assert PipelineConfig().satin_slab_serifs is False
    poly, art, kw = _fixture(T_FIXTURE)
    dflt, _ = satin_shape(poly, "S1", art_poly=art, join_square=True, **kw)
    off, _ = satin_shape(poly, "S1", art_poly=art, join_square=True, slab_serifs=False, **kw)
    assert [r.points for r in dflt] == [r.points for r in off]


def test_the_t_foot_is_a_cap_off():
    """OFF the T's foot has no column of its own: nothing sews wholly in
    the foot's bottom millimetre, and a third of it is bare. Pinned so the
    fixture cannot quietly stop reproducing the defect."""
    runs, art = _runs(T_FIXTURE, False)
    assert _foot_columns(runs, art) == []
    bare = _bare(runs, _foot_band(art))
    assert bare >= 0.3, f"the T's foot is no longer bare OFF ({bare:.3f} mm2)"


def test_the_t_foot_is_its_own_column_on():
    runs, art = _runs(T_FIXTURE, True)
    feet = _foot_columns(runs, art)
    assert len(feet) == 1, f"{len(feet)} columns wholly in the foot band"
    foot = feet[0]
    xs = [p[0] for p in foot.points]
    # the whole slab, rail to rail: 2.46 mm wide at 80 mm (2026-10-07),
    # seven crosses
    assert max(xs) - min(xs) >= 2.0
    assert len(foot.points) >= 10
    bare = _bare(runs, _foot_band(art))
    assert bare <= 0.1, f"{bare:.3f} mm2 bare in the T's foot with slab_serifs on"


def test_the_t_bar_and_its_hanging_slabs_are_untouched():
    """The L-corners are not slab pairs: the bar's column (with both
    hanging slabs folded into it) is byte-identical, and so is the stem's.
    The flag adds the foot and changes nothing else."""
    off, art = _runs(T_FIXTURE, False)
    on, _ = _runs(T_FIXTURE, True)
    off_sat = [r.points for r in off if r.kind == "satin"]
    on_sat = [r.points for r in on if r.kind == "satin"]
    assert len(on_sat) == len(off_sat) + 1
    for pts in off_sat:
        assert pts in on_sat


def _head_columns(runs, art, depth_mm=1.3):
    ceiling = art.bounds[1] + depth_mm
    return [r for r in runs if r.kind == "satin" and all(p[1] <= ceiling for p in r.points)]


def test_the_n_foot_and_serif_weld_rail_to_rail():
    """The merge-side half. OFF the N's left foot is one half-column of
    four crosses fanned from the stem and its top-right serif is TWO
    half-columns meeting at the stem; the stack refused both welds at
    144 and 148 deg. ON each is one column across the slab: six crosses on
    the foot, seven on the serif, and the foot's bottom millimetre goes
    from 0.12 mm2 bare to under 0.01 (2026-10-07)."""
    off, art = _runs(N_FIXTURE, False)
    on, _ = _runs(N_FIXTURE, True)
    assert len(_head_columns(off, art)) == 2
    assert len(_foot_columns(off, art)) == 1
    heads, feet = _head_columns(on, art), _foot_columns(on, art)
    assert len(heads) == 1 and len(feet) == 1
    for col in (heads[0], feet[0]):
        xs = [p[0] for p in col.points]
        assert max(xs) - min(xs) >= 2.0
        assert len(col.points) >= 12
    assert _bare(off, _foot_band(art)) >= 0.08
    assert _bare(on, _foot_band(art)) <= 0.03
    # the stems and the diagonal are byte-identical: the flag re-welds the
    # slabs and touches nothing else
    off_long = sorted(r.points for r in off if r.kind == "satin" and len(r.points) >= 30)
    on_long = sorted(r.points for r in on if r.kind == "satin" and len(r.points) >= 30)
    assert on_long == off_long and len(on_long) == 3
