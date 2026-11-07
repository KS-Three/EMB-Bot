"""ARTWORK_ELEMENT_DROPPED: preflight reads the pipeline's own losses.

The 2026-10-27 logo census (`docs/logo-style-census-2026-10-27.md` items 3-4)
found whole elements leaving the design with the grade unmoved: `qr_code` lost
10 modules (864 mm2) at stage 5's clip, the WPA poster's disc was colour-capped
into its ground, the mascot's pupils were left unsewn as enclosed background.
The pipeline wrote a warning every time; preflight read none of them.
`_element_drop_findings` reads them, by area, under one finding.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from shapely.geometry import box

from digitizer_core import preflight as pf
from digitizer_core import run_stages
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import plan_stitches
from digitizer_core.preflight import (
    _ELEMENT_BLOCK_FRAC,
    _ELEMENT_MIN_MM2,
    ARTWORK_ELEMENT_DROPPED,
    _element_drop_findings,
    run_preflight,
)
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import prep
from digitizer_core.warnings_codes import (
    DROPPED_SMALL_SHAPES,
    SHAPE_NOT_STITCHED,
    SHAPES_LEFT_UNSEWN,
    warn,
)

from .conftest import cfg

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
WHITEBG = TESTDATA / "logo_whitebg.png"
GARMENT = (235, 232, 223)


def _region(sid: str, poly, thread: int, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=f"{thread:04d}", area_mm2=float(poly.area),
                  meta=dict(meta))


def _plan(*warnings) -> SimpleNamespace:
    return SimpleNamespace(warnings=list(warnings))


def _codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


def _only(findings: list[dict]) -> dict:
    assert [f["code"] for f in findings] == [ARTWORK_ELEMENT_DROPPED]
    return findings[0]


# --- the floors are the measured ones ---------------------------------------

def test_the_floors_are_the_ones_the_comment_names():
    assert _ELEMENT_MIN_MM2 == pf._THREAD_MATCH_MIN_PATCH_MM2 == 5.0
    assert _ELEMENT_BLOCK_FRAC == 0.10


# --- a healthy design says nothing ------------------------------------------

def test_a_healthy_design_drops_nothing_and_says_so(whitebg):
    plan = plan_stitches(whitebg, cfg())
    report = run_preflight(whitebg, plan, cfg(), image=WHITEBG)
    m = report["metrics"]
    assert m["element_drop_checked"] is True
    assert m["element_dropped_count"] == 0
    assert m["element_dropped_mm2"] == 0.0
    assert ARTWORK_ELEMENT_DROPPED not in _codes(report)


def test_no_regions_means_no_check():
    findings, metrics = _element_drop_findings(
        None, SimpleNamespace(regions=[]), _plan(), cfg())
    assert findings == []
    assert metrics["element_drop_checked"] is False
    assert metrics["element_dropped_mm2"] is None


# --- clipped: stage 5 named the shapes it lost ------------------------------

def test_a_shape_clipped_away_at_stage_5_is_a_dropped_element():
    ground = _region("G", box(0, 0, 40, 40), 1)
    lost = _region("S", box(50, 50, 56, 56), 2)          # 36 mm2
    result = SimpleNamespace(regions=[ground, lost])
    plan = _plan(warn(SHAPE_NOT_STITCHED, "x", count=1, ids=["S"],
                      threads=["0002"], total_mm2=36.0, largest_mm2=36.0))
    f = _only(_element_drop_findings(None, result, plan, cfg())[0])
    assert f["severity"] == "warn"
    assert f["extra"]["causes"] == {"clipped": 1, "unsewn_enclosed": 0,
                                    "folded": 0, "unsewable": 0}
    assert f["extra"]["shapes"] == [{"shape_id": "S", "mm2": 36.0,
                                     "cause": "clipped", "thread": "0002"}]
    assert f["extra"]["show_shape_ids"] == ["S"]
    assert f["extra"]["frac"] == round(36.0 / 1636.0, 3)
    assert "vanished where a neighbouring colour" in f["message"]


def test_losing_a_tenth_of_the_artwork_blocks():
    ground = _region("G", box(0, 0, 40, 40), 1)          # 1600 mm2
    lost = _region("S", box(50, 50, 70, 70), 2)          # 400 mm2 = 20%
    result = SimpleNamespace(regions=[ground, lost])
    plan = _plan(warn(SHAPE_NOT_STITCHED, "x", count=1, ids=["S"]))
    f = _only(_element_drop_findings(None, result, plan, cfg())[0])
    assert f["severity"] == "block"
    assert f["extra"]["frac"] == 0.2


def test_a_sub_floor_sliver_is_a_detail_not_an_element():
    ground = _region("G", box(0, 0, 40, 40), 1)
    sliver = _region("S", box(50, 50, 52, 52), 2)        # 4 mm2 < 5
    result = SimpleNamespace(regions=[ground, sliver])
    plan = _plan(warn(SHAPE_NOT_STITCHED, "x", count=1, ids=["S"]))
    findings, metrics = _element_drop_findings(None, result, plan, cfg())
    assert findings == []
    assert metrics["element_dropped_count"] == 0


def test_an_id_the_regions_no_longer_carry_is_skipped():
    result = SimpleNamespace(regions=[_region("G", box(0, 0, 40, 40), 1)])
    plan = _plan(warn(SHAPE_NOT_STITCHED, "x", count=1, ids=["gone"]))
    assert _element_drop_findings(None, result, plan, cfg())[0] == []


# --- unsewable: stage 4 dropped a whole outline -----------------------------

def test_a_whole_outline_stage_4_could_not_trace_counts_by_its_largest():
    result = SimpleNamespace(regions=[_region("G", box(0, 0, 40, 40), 1)])
    plan = _plan(warn(DROPPED_SMALL_SHAPES, "x", count=2, cleaned_total=9,
                      largest_mm2=50.0, all_small=False))
    f = _only(_element_drop_findings(None, result, plan, cfg())[0])
    assert f["extra"]["causes"]["unsewable"] == 2
    assert f["extra"]["total_mm2"] == 50.0 and f["extra"]["shapes"] == []
    assert "could not be traced" in f["message"]


@pytest.mark.parametrize("w", [
    # stage 4, every drop a detail
    warn(DROPPED_SMALL_SHAPES, "x", count=3, cleaned_total=3, largest_mm2=3.44,
         all_small=True),
    # stage 3's variant: a count of sub-detail pieces, no area at all
    warn(DROPPED_SMALL_SHAPES, "x", count=58, cleaned_total=705),
])
def test_detail_drops_are_not_elements(w):
    result = SimpleNamespace(regions=[_region("G", box(0, 0, 40, 40), 1)])
    assert _element_drop_findings(None, result, _plan(w), cfg())[0] == []


# --- folded: the colour cap re-threaded a shape into its neighbour -----------

def _folded_fixture(piece_box=box(20, 20, 30, 30)):
    ground = _region("G", box(0, 0, 50, 50), 5)
    piece = _region("P", piece_box, 5, color_cap_merged_from="0123")
    return SimpleNamespace(regions=[ground, piece])


def test_a_capped_shape_touching_its_new_thread_and_far_from_it_is_folded():
    rows = [{"shape_id": "P", "thread_index": 5, "delta_e": 30.0},
            {"shape_id": "G", "thread_index": 5, "delta_e": 1.0}]
    f = _only(_element_drop_findings(object(), _folded_fixture(), _plan(),
                                     cfg(), rows=rows)[0])
    assert f["extra"]["causes"]["folded"] == 1
    assert f["extra"]["shapes"][0] == {"shape_id": "P", "mm2": 100.0,
                                       "cause": "folded", "thread": "0005"}
    assert f"{cfg().max_colors}-colour limit" in f["message"]


def test_a_capped_shape_that_still_reads_as_its_thread_is_not_folded():
    rows = [{"shape_id": "P", "thread_index": 5, "delta_e": 4.0}]
    assert _element_drop_findings(object(), _folded_fixture(), _plan(), cfg(),
                                  rows=rows)[0] == []


def test_a_capped_shape_standing_alone_is_a_colour_change_not_a_drop():
    rows = [{"shape_id": "P", "thread_index": 5, "delta_e": 30.0}]
    alone = _folded_fixture(box(100, 100, 110, 110))
    assert _element_drop_findings(object(), alone, _plan(), cfg(),
                                  rows=rows)[0] == []


def test_without_the_graders_rows_the_fold_is_not_judged_and_says_so():
    findings, metrics = _element_drop_findings(None, _folded_fixture(), _plan(),
                                               cfg())
    assert findings == []
    assert metrics["element_drop_colour_checked"] is False


# --- unsewn_enclosed: a hole showing the garment where the picture had ink --

def _ink_square(path: Path) -> Path:
    """A 240x240 white card with one 90x90 black square: the cheapest artwork
    whose one region can be tagged enclosed background and judged against a
    garment colour."""
    img = np.full((240, 240, 3), 255, np.uint8)
    cv2.rectangle(img, (75, 75), (164, 164), (0, 0, 0), -1)
    cv2.imwrite(str(path), img)
    return path


def _unsewn_fixture(tmp_path, garment, by_override=False):
    c = cfg(garment_rgb=garment,
            shape_overrides={"S": {"stitched": False}} if by_override else None)
    p = prep(_ink_square(tmp_path / "ink.png"), c)
    # The square is the whole artwork, so in design mm it is centred on the
    # origin at the width `cfg` asked for.
    half = c.target_width_mm / 2.0
    square = _region("S", box(-half, -half, half, half), 2,
                     enclosed_background=True, stitched=False)
    result = SimpleNamespace(regions=[square])
    plan = _plan(warn(SHAPES_LEFT_UNSEWN, "x", count=1, ids=["S"],
                      threads=["0002"], total_mm2=square.area_mm2,
                      largest_mm2=square.area_mm2, enclosed_background=1,
                      by_override=int(by_override)))
    return p, result, plan, c


@pytest.mark.parametrize("v2", [False, True])
def test_black_ink_left_as_a_hole_on_a_cream_garment_is_a_dropped_element(tmp_path, v2):
    # A hole found by COLOUR keeps v1's judgment under `dropped_element_v2`.
    p, result, plan, c = _unsewn_fixture(tmp_path, GARMENT)
    if v2:
        c = dataclasses.replace(c, extra={"dropped_element_v2": True})
    findings, metrics = _element_drop_findings(p, result, plan, c, rows=[])
    f = _only(findings)
    assert f["extra"]["causes"]["unsewn_enclosed"] == 1
    assert f["severity"] == "block"           # it is the whole artwork
    assert metrics["element_drop_colour_checked"] is True
    assert "showing the garment" in f["message"]


def test_a_hole_the_garment_fills_in_the_pictures_own_colour_is_not_a_drop(tmp_path):
    p, result, plan, c = _unsewn_fixture(tmp_path, (0, 0, 0))
    assert _element_drop_findings(p, result, plan, c, rows=[])[0] == []


def test_a_shape_the_customer_left_out_in_review_is_their_call(tmp_path):
    p, result, plan, c = _unsewn_fixture(tmp_path, GARMENT, by_override=True)
    assert _element_drop_findings(p, result, plan, c, rows=[])[0] == []


def _alpha_ring(path: Path) -> Path:
    """A red ring on a transparent page whose hole is transparent too, with
    the black (0, 0, 0) an exporter flattens under alpha 0 -- the shape of
    both of Kent's Good/Great rows v1 fired on (`gradient_mascot`'s eye
    whites, `pixel_art_sprite`'s eye and belly holes, 2026-11-07)."""
    img = np.zeros((240, 240, 4), np.uint8)
    cv2.rectangle(img, (60, 60), (179, 179), (20, 20, 160, 255), -1)
    cv2.rectangle(img, (100, 100), (139, 139), (0, 0, 0, 0), -1)
    cv2.imwrite(str(path), img)
    return path


def test_a_hole_the_art_leaves_transparent_fires_v1_and_not_v2(tmp_path):
    """The page showing through a transparent hole is the art, not a lost
    element: v1 reads the flattened black and blocks, v2 says nothing and
    counts the hole in metrics. Same digitize, same plan, same score
    arithmetic: only the finding moves."""
    art = _alpha_ring(tmp_path / "ring.png")
    c = cfg(garment_rgb=GARMENT)
    result = run_stages(art, c)
    plan = plan_stitches(result, c)
    hole = [r for r in result.regions if r.meta.get("enclosed_background")]
    assert len(hole) == 1 and hole[0].meta.get("enclosed_colour_unknown")
    assert hole[0].meta.get("stitched") is False

    off = run_preflight(result, plan, c, image=art)
    f = next(f for f in off["findings"] if f["code"] == ARTWORK_ELEMENT_DROPPED)
    assert f["extra"]["causes"]["unsewn_enclosed"] == 1
    assert "element_drop_transparent_count" not in off["metrics"]

    on = run_preflight(result, plan,
                       dataclasses.replace(c, extra={"dropped_element_v2": True}),
                       image=art)
    assert ARTWORK_ELEMENT_DROPPED not in _codes(on)
    m = on["metrics"]
    assert m["element_dropped_count"] == 0
    assert m["element_drop_transparent_count"] == 1
    assert m["element_drop_transparent_mm2"] == round(hole[0].area_mm2, 1)
    # the finding was the only difference, and the score moves by its deduction
    rest = lambda r: sorted((g["code"], g["severity"]) for g in r["findings"]  # noqa: E731
                            if g["code"] != ARTWORK_ELEMENT_DROPPED)
    assert rest(off) == rest(on)
    assert on["score"] - off["score"] == pf._DEDUCT[f["severity"]]


def test_without_a_garment_colour_the_hole_is_not_judged(tmp_path):
    p, result, plan, c = _unsewn_fixture(tmp_path, None)
    findings, metrics = _element_drop_findings(p, result, plan, c, rows=[])
    assert findings == []
    assert metrics["element_drop_colour_checked"] is False


# --- one finding, every cause, worst piece first ----------------------------

def test_causes_pool_into_one_finding_sorted_by_area():
    ground = _region("G", box(0, 0, 60, 60), 5)
    clipped = _region("C", box(70, 0, 80, 10), 2)                  # 100
    folded = _region("P", box(10, 10, 30, 30), 5, color_cap_merged_from="0123")  # 400
    result = SimpleNamespace(regions=[ground, clipped, folded])
    plan = _plan(warn(SHAPE_NOT_STITCHED, "x", count=1, ids=["C"]),
                 warn(DROPPED_SMALL_SHAPES, "x", count=1, cleaned_total=1,
                      largest_mm2=20.0, all_small=False))
    rows = [{"shape_id": "P", "thread_index": 5, "delta_e": 25.0}]
    findings, metrics = _element_drop_findings(object(), result, plan, cfg(),
                                               rows=rows)
    f = _only(findings)
    assert f["extra"]["causes"] == {"clipped": 1, "unsewn_enclosed": 0,
                                    "folded": 1, "unsewable": 1}
    assert [x["shape_id"] for x in f["extra"]["shapes"]] == ["P", "C"]
    assert f["extra"]["total_mm2"] == 520.0 and f["extra"]["largest_mm2"] == 400.0
    assert metrics["element_dropped_count"] == 3
    # 520 of 4100 mm2 of artwork
    assert f["severity"] == "block" and f["extra"]["frac"] == round(520 / 4100, 3)
