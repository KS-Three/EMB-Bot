"""`digitizer_core.shape_memo`: the per-job memo of stage 6's pure emitters.

Stage 7 sews a lane-ON design twice (the OFF pass is read for its sew
order), and the memo answers the second pass from the first. Pinned here:
a hit is the miss, byte for byte, and an independent copy; the memo is dead
outside a scope and emptied when the scope closes; a knob set through a
ContextVar is part of the key; a closure argument bypasses it; the ambient
list covers every ContextVar in the package; and `sequence` itself returns
the same blocks with the memo as without.
"""
from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import machine, shape_memo, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.stage6_fill import stitch_shape
from digitizer_core.stage6_satin import satin_shape

CORE = Path(__file__).resolve().parents[1] / "digitizer_core"


def _rect(x0, y0, x1, y1):
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


# A plate with a hole: two columns, so the fill plans travel and reorders.
PLATE = Polygon([(0, 0), (12, 0), (12, 8), (0, 8)], [[(5, 2), (7, 2), (7, 6), (5, 6)]])
FILL_KW = dict(angle_deg=None, row_mm=machine.FILL_ROW_MM, stitch_mm=machine.FILL_STITCH_MM,
               underlay_style="none", trim_at_mm=5.0, start_near=(0.0, 0.0))


def _runs(runs):
    return [asdict(r) for r in runs]


@pytest.fixture(autouse=True)
def _fresh():
    shape_memo.clear()
    shape_memo.reset_stats()
    yield
    shape_memo.clear()
    shape_memo.reset_stats()


def test_dead_outside_a_scope():
    assert not shape_memo.active()
    a = stitch_shape(PLATE, "s1", **FILL_KW)
    b = stitch_shape(PLATE, "s1", **FILL_KW)
    assert _runs(a[0]) == _runs(b[0]) and a[1] == b[1]
    assert shape_memo.stats == {"hit": 0, "miss": 0, "bypass": 0}
    assert not shape_memo._memo


def test_a_hit_is_the_miss_and_an_independent_copy():
    with shape_memo.scope():
        miss = stitch_shape(PLATE, "s1", **FILL_KW)
        assert shape_memo.stats["miss"] == 1
        # the caller owns the miss: ties, hop burying and tier reports write on it
        miss[0][0].trim = not miss[0][0].trim
        miss[0][0].points.append((99.0, 99.0))
        miss[1]["scribble"] = 1
        hit = stitch_shape(PLATE, "s1", **FILL_KW)
        assert shape_memo.stats["hit"] == 1
    cold = stitch_shape(PLATE, "s1", **FILL_KW)           # outside: computed afresh
    assert _runs(hit[0]) == _runs(cold[0])
    assert hit[1] == cold[1]
    assert hit[0][0] is not miss[0][0]
    assert hit[0][0].trim == cold[0][0].trim and (99.0, 99.0) not in hit[0][0].points
    assert "scribble" not in hit[1]


def test_satin_and_rim_emitters_are_memoized_too():
    from digitizer_core.stage6_border import underfill_rim_runs
    bar = _rect(0, 0, 2, 12)
    ring = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)], [[(3, 3), (17, 3), (17, 17), (3, 17)]])
    with shape_memo.scope():
        s1 = satin_shape(bar, "b", underlay_style="none", trim_at_mm=5.0, start_near=(0.0, 0.0))
        s2 = satin_shape(bar, "b", underlay_style="none", trim_at_mm=5.0, start_near=(0.0, 0.0))
        r1 = underfill_rim_runs(ring, "r", entry=(0.0, 0.0), trim_at_mm=5.0)
        r2 = underfill_rim_runs(ring, "r", entry=(0.0, 0.0), trim_at_mm=5.0)
    assert shape_memo.stats["hit"] == 2 and shape_memo.stats["miss"] == 2
    assert _runs(s1[0]) == _runs(s2[0]) and s1[1] == s2[1]
    assert _runs(r1[0]) == _runs(r2[0]) and r1[1] == r2[1]
    assert r1[0], "the rim fixture sewed nothing, so the rim half proves nothing"


def test_the_scope_closes_empty_and_nested_scopes_share():
    with shape_memo.scope():
        stitch_shape(PLATE, "s1", **FILL_KW)
        with shape_memo.scope():
            stitch_shape(PLATE, "s1", **FILL_KW)
            assert shape_memo.stats["hit"] == 1
        assert shape_memo._memo, "the inner scope must not empty the outer's memo"
    assert not shape_memo._memo and not shape_memo.active()
    with shape_memo.scope(enabled=False):
        stitch_shape(PLATE, "s1", **FILL_KW)
    assert shape_memo.stats["miss"] == 1 and not shape_memo._memo


def test_a_different_argument_is_a_different_key():
    with shape_memo.scope():
        a = stitch_shape(PLATE, "s1", **FILL_KW)
        b = stitch_shape(PLATE, "s1", **{**FILL_KW, "start_near": (12.0, 8.0)})
        c = stitch_shape(PLATE, "s2", **FILL_KW)
    assert shape_memo.stats["hit"] == 0 and shape_memo.stats["miss"] == 3
    assert _runs(a[0]) != _runs(b[0])
    assert all(r.shape_id == "s2" for r in c[0])


def test_an_ambient_contextvar_is_part_of_the_key():
    from digitizer_core import outline_cut
    with shape_memo.scope():
        stitch_shape(PLATE, "s1", **FILL_KW)
        token = outline_cut._APEX_CUT.set(True)
        try:
            stitch_shape(PLATE, "s1", **FILL_KW)
        finally:
            outline_cut._APEX_CUT.reset(token)
        stitch_shape(PLATE, "s1", **FILL_KW)
    assert shape_memo.stats == {"hit": 1, "miss": 2, "bypass": 0}


def test_a_closure_argument_bypasses_the_memo():
    with shape_memo.scope():
        a = stitch_shape(PLATE, "s1", **FILL_KW, keep_row=lambda y: True)
        b = stitch_shape(PLATE, "s1", **FILL_KW, keep_row=lambda y: True)
    assert shape_memo.stats == {"hit": 0, "miss": 0, "bypass": 2}
    assert _runs(a[0]) == _runs(b[0])


def test_every_contextvar_in_the_package_is_ambient_or_a_cache():
    """A knob an emitter reads through a ContextVar must be in the key, or a
    hit could answer a question asked under a different knob. Adding one
    means adding it here (or to `_CACHES`, with the reason)."""
    found = set()
    for path in CORE.glob("*.py"):
        for m in re.finditer(r"^(\w+)\s*:\s*contextvars\.ContextVar", path.read_text(encoding="utf-8"), re.M):
            found.add((path.stem, m.group(1)))
    assert found, "the scan found no ContextVar; the pattern is stale"
    listed = set(shape_memo._AMBIENT) | set(shape_memo._CACHES)
    assert found == listed, {"unlisted": found - listed, "stale": listed - found}


def test_sequence_is_byte_identical_with_the_memo(monkeypatch):
    """The real consumer: a lane-ON design with a letter sews twice inside
    `sequence`, and with the memo the second pass must hand back the same
    blocks the un-memoized run does -- while actually hitting."""
    import digitizer_core.stage7_sequence as S7
    from digitizer_core.fabrics import fabric_for_garment
    from digitizer_core.regions import Region
    from digitizer_core.stage5_overlap import PlannedRegion
    shapes = {"A": _rect(-24, -5, -22, 5), "L": _rect(-1, -5, 1, 5),
              "B": _rect(6, -20, 8, -10), "P": PLATE}

    def planned():
        out = []
        for sid, poly in shapes.items():
            meta = {"layer": 0, **({"text_candidate": True} if sid == "L" else {})}
            reg = Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="0134",
                         area_mm2=poly.area, source="test", meta=meta)
            out.append(PlannedRegion(region=reg, polygon=poly, sew_index=0))
        return out

    cfg = PipelineConfig(underlay=False, lettering_columns=True)
    fabric = fabric_for_garment("left_chest")
    plain, _ = S7.sequence(planned(), fabric, cfg)
    assert shape_memo.stats == {"hit": 0, "miss": 0, "bypass": 0}
    with shape_memo.scope():
        memo, _ = S7.sequence(planned(), fabric, cfg)
    assert shape_memo.stats["hit"] > 0, "no second-pass repeat was served; the test proves nothing"
    assert [(b.thread_index, _runs(b.runs)) for b in memo] == \
           [(b.thread_index, _runs(b.runs)) for b in plain]
    assert sum(len(r.points) for b in plain for r in b.runs) > 0


def test_no_lettering_means_no_scope_and_no_pickling():
    """The scope opens only when stage 7 will take its lane-OFF pass, i.e. a
    shape is lettering. A design without one pays nothing for the memo."""
    from digitizer_core.pipeline import _lane_has_letters
    from digitizer_core.regions import Region
    from digitizer_core.stage5_overlap import PlannedRegion
    cfg = PipelineConfig(lettering_columns=True, satin=True)
    plain = [PlannedRegion(region=Region(shape_id="p", polygon=PLATE, thread_index=0,
                                         thread_number="0134", area_mm2=PLATE.area,
                                         source="test", meta={"layer": 0}),
                           polygon=PLATE, sew_index=0)]
    assert not _lane_has_letters(plain, cfg)
    lettered = [PlannedRegion(region=Region(shape_id="L", polygon=PLATE, thread_index=0,
                                            thread_number="0134", area_mm2=PLATE.area,
                                            source="test",
                                            meta={"layer": 0, "text_candidate": True}),
                              polygon=PLATE, sew_index=0)]
    assert _lane_has_letters(lettered, cfg)
    assert not _lane_has_letters(lettered, PipelineConfig(lettering_columns=False, satin=True))
