"""Column-lane cover hand-back (`cfg.lettering_columns_cover_handback`, built
OFF 2026-11-13; Kent's ruling that day, "Hand-back, built OFF").

A text-tagged shape the Column lane sews covering under
`columns.HANDBACK_COVER_MIN` of it (`columns.satin_cover`) goes back to the
ordinary ladder and sews as it would untagged. The starter monarch's V-shaped
wing cell `Sfe1be372`, read as a letter only at targets 90.50 and 91.75 mm,
sewed one arm in the lane (cover 0.653 here); handed back it sews both
(docs/monarch-size-cliff-2026-11-13.md). Fixtures: the cell as stage 7
received it at both widths (`testdata/handback_monarch_cells.json`).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from shapely import wkt

from digitizer_core import PipelineConfig
from digitizer_core.columns import HANDBACK_COVER_MIN, SMALL_BOLD_COVER_MIN, satin_cover
from digitizer_core.pipeline import fabric_for
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence

CELLS = json.loads((Path(__file__).resolve().parent.parent / "testdata"
                    / "handback_monarch_cells.json").read_text(encoding="utf-8"))["cells"]


def _sew(cell, **cfg_kw):
    poly = wkt.loads(cell["wkt"])
    cfg = PipelineConfig(**cfg_kw)
    r = Region(shape_id=cell["shape_id"], polygon=poly, thread_index=0, thread_number=cell["thread"],
               area_mm2=poly.area, source="test", meta=dict(cell["meta"]))
    blocks, _ = sequence([PlannedRegion(region=r, polygon=poly, sew_index=0)], fabric_for(cfg), cfg)
    return poly, [x for b in blocks for x in b.runs if x.shape_id == cell["shape_id"]]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def test_flag_is_built_off_and_the_floor_is_the_lanes_own():
    assert PipelineConfig().lettering_columns_cover_handback is False
    assert HANDBACK_COVER_MIN == SMALL_BOLD_COVER_MIN == 0.9


@pytest.mark.parametrize("cell", CELLS, ids=[f"{c['target_mm']}mm" for c in CELLS])
def test_off_the_lane_sews_one_arm(cell):
    poly, runs = _sew(cell)
    assert satin_cover(runs, poly) < HANDBACK_COVER_MIN


@pytest.mark.parametrize("cell", CELLS, ids=[f"{c['target_mm']}mm" for c in CELLS])
def test_on_the_cell_is_handed_back_and_sews_both_arms(cell):
    poly, off = _sew(cell)
    _, on = _sew(cell, lettering_columns_cover_handback=True)
    assert satin_cover(on, poly) >= 0.95 > satin_cover(off, poly) + 0.25
    assert _md5(on) != _md5(off)


@pytest.mark.parametrize("cell", CELLS, ids=[f"{c['target_mm']}mm" for c in CELLS])
def test_off_is_the_lane_byte_for_byte(cell):
    # the flag spelled False is the default: the lane's output is final
    _, a = _sew(cell)
    _, b = _sew(cell, lettering_columns_cover_handback=False)
    assert _md5(a) == _md5(b)


def test_a_letter_the_lane_covers_is_not_handed_back():
    # a plain bar, tagged as a letter: the lane covers it, ON changes nothing
    from shapely.geometry import box
    cell = {"shape_id": "Sbar", "thread": "0020", "wkt": box(0, 0, 2.0, 12.0).wkt,
            "meta": {"layer": 0, "text_candidate": True, "text_cluster_id": "TCbar"}}
    _, off = _sew(cell)
    _, on = _sew(cell, lettering_columns_cover_handback=True)
    assert _md5(on) == _md5(off)


# --- narrowed 2026-11-13 (Kent: "Narrow it, re-census"): the ladder must win --
SMALL = json.loads((Path(__file__).resolve().parent.parent / "testdata"
                    / "handback_monarch_cells.json").read_text(encoding="utf-8"))["small_kept"]


@pytest.mark.parametrize("cell", SMALL, ids=[c["job"].split(":")[0] + "-" + c["shape_id"] for c in SMALL])
def test_a_small_shape_the_ladder_would_spill_over_keeps_the_lane(cell):
    poly, off = _sew(cell)
    _, on = _sew(cell, lettering_columns_cover_handback=True)
    assert satin_cover(off, poly) < HANDBACK_COVER_MIN          # it is a candidate
    assert _md5(on) == _md5(off)                                # and the lane is kept


def test_handback_wins_reads_spill_as_well_as_cover():
    from shapely.geometry import LineString, box
    from digitizer_core.columns import handback_wins, thread_cover_spill
    from digitizer_core.stitches import SATIN, StitchRun
    shape = box(0, 0, 10, 2)
    half = [StitchRun(points=[(x, 0.2), (x, 1.0)], kind=SATIN) for x in (1, 3, 5)]
    whole = [StitchRun(points=[(x, 0.2), (x, 1.8)], kind=SATIN) for x in (1, 3, 5, 7, 9)]
    sprawl = [StitchRun(points=[(x, -3.0), (x, 5.0)], kind=SATIN) for x in (1, 3, 5, 7, 9)]
    assert thread_cover_spill(whole, shape)[0] > thread_cover_spill(half, shape)[0]
    assert handback_wins(half, whole, shape)                    # more in, nothing more out
    assert not handback_wins(half, sprawl, shape)               # more in, far more out
    assert not handback_wins(whole, half, shape)                # less in
    assert handback_wins(half, whole, shape, rule="strict")
