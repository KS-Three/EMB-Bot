"""`cfg.page_line_front` (built OFF 2026-11-17): the art's thin white lines
(`two_tone.keep_lines`) sew BEFORE the ink beside them, so the black line under
gaulke's inner roof is not covered by a white satin bar.

Prime grader scorecard 2026-11-17, `gaulke_roofing_hat`; module note in
`digitizer_core/page_line.py`.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
from shapely.geometry import box

from digitizer_core.config import PipelineConfig
from digitizer_core.page_line import apply_page_lines, plan_page_lines
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep

ART = "logo_gaulke_roofing.png"


def _prep(lines: np.ndarray | None) -> Prep:
    h, w = 40, 80
    return Prep(rgb=np.zeros((h, w, 3), np.uint8), bg_mask=np.zeros((h, w), bool),
                px_per_mm=10.0, art_bbox=(0, 0, w, h), page_lines=lines)


def _region(sid: str, poly, thread: int, layer: int) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number="x",
                  area_mm2=poly.area, source="classical", meta={"layer": layer})


def test_default_is_off():
    assert PipelineConfig().page_line_front is False


def test_no_lines_changes_nothing():
    regs = [_region("a", box(-3, -1, 3, 1), 4, 0)]
    out, n = apply_page_lines(regs, [4], _prep(None))
    assert (out, n) == ([4], 0)
    assert regs[0].meta["layer"] == 0 and "page_line" not in regs[0].meta


def test_a_line_region_takes_a_front_layer_and_the_rest_shift():
    # frame 80 x 40 px at 10 px/mm, art centre (40, 20): mm (x, y) -> px (40+10x, 20+10y)
    lines = np.zeros((40, 80), bool)
    lines[19:22, 10:70] = True                       # a 3 px x 60 px white line
    line = _region("line", box(-3.0, -0.1, 3.0, 0.2), 2, 1)
    ink = _region("ink", box(-3.0, 0.5, 3.0, 1.5), 4, 0)
    regs = [ink, line]
    assert plan_page_lines(regs, _prep(lines)) == [line]
    out, n = apply_page_lines(regs, [4, 2], _prep(lines))
    assert n == 1
    assert out == [2, 4, 2]                          # white in front; old layers behind it
    assert line.meta["layer"] == 0 and line.meta["page_line"] is True
    assert ink.meta["layer"] == 1 and "page_line" not in ink.meta


def test_a_region_off_the_lines_is_not_one():
    lines = np.zeros((40, 80), bool)
    lines[19:22, 10:70] = True
    far = _region("far", box(-3.0, 1.0, 3.0, 1.8), 2, 0)
    assert plan_page_lines([far], _prep(lines)) == []


@pytest.fixture(scope="module")
def gaulke():
    from tools import pro_baseline as pb, pro_pair
    slug = "gaulke_roofing_hat"
    garment, width, art = pb.JOBS[slug][0], float(pb.JOBS[slug][1]), pb.resolve(pb.JOBS[slug][2])
    if not art.exists():
        pytest.skip("gaulke art not in this checkout")
    off = pro_pair.digitize(art, width, garment, None)
    on = pro_pair.digitize(art, width, garment, {"page_line_front": True})
    return off, on


def _md5(d) -> str:
    return hashlib.md5(json.dumps(d.design["stitches"], sort_keys=True).encode()).hexdigest()


def test_gaulke_off_is_the_default_and_on_moves_the_white_first(gaulke):
    off, on = gaulke
    assert off.cfg.page_line_front is False and on.cfg.page_line_front is True
    assert _md5(off) != _md5(on)
    tagged = [r for r in on.result.regions if r.meta.get("page_line")]
    assert tagged, "the inner roof's white gap should be read as a page line"
    # sewn first: every page line sits on a lower layer than every other sewn region
    top = max(int(r.meta["layer"]) for r in tagged)
    others = [int(r.meta["layer"]) for r in on.result.regions
              if not r.meta.get("page_line") and r.meta.get("stitched")]
    assert top < min(others)
    # and OFF has no such tag at all
    assert not any(r.meta.get("page_line") for r in off.result.regions)


# --- `cfg.page_line_open` (built OFF 2026-11-17): the line stays bare fabric ---

def test_open_default_is_off():
    assert PipelineConfig().page_line_open is False


@pytest.fixture(scope="module")
def gaulke_open():
    from tools import pro_baseline as pb, pro_pair
    slug = "gaulke_roofing_hat"
    garment, width, art = pb.JOBS[slug][0], float(pb.JOBS[slug][1]), pb.resolve(pb.JOBS[slug][2])
    if not art.exists():
        pytest.skip("gaulke art not in this checkout")
    return pro_pair.digitize(art, width, garment, {"page_line_open": True})


def test_gaulke_open_leaves_the_roof_gap_unsewn(gaulke, gaulke_open):
    off, _ = gaulke
    tagged = [r for r in gaulke_open.result.regions if r.meta.get("page_line_open")]
    assert tagged, "the inner roof's white gap should be read as a page line"
    assert all(r.meta["stitched"] is False for r in tagged)
    # the black either side still sews
    black = [r for r in gaulke_open.result.regions
             if not r.meta.get("page_line_open") and r.meta.get("stitched")]
    assert black
    assert _md5(off) != _md5(gaulke_open)
    assert not any(r.meta.get("page_line_open") for r in off.result.regions)


def test_a_review_stitched_override_still_wins():
    from tools import pro_baseline as pb, pro_pair
    slug = "gaulke_roofing_hat"
    garment, width, art = pb.JOBS[slug][0], float(pb.JOBS[slug][1]), pb.resolve(pb.JOBS[slug][2])
    if not art.exists():
        pytest.skip("gaulke art not in this checkout")
    first = pro_pair.digitize(art, width, garment, {"page_line_open": True})
    sid = next(r.shape_id for r in first.result.regions if r.meta.get("page_line_open"))
    cfg = pro_pair.config(width, garment, {"page_line_open": True})
    import dataclasses
    cfg = dataclasses.replace(cfg, shape_overrides={sid: {"stitched": True}})
    from digitizer_core.pipeline import finish_generation
    res = finish_generation(first.gen.fork(), cfg)
    assert next(r for r in res.regions if r.shape_id == sid).meta["stitched"] is True
