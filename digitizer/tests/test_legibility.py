"""`tools/legibility.py` — OCR on the render against the artwork, pinned.

The geometry half (crop mapping, cluster boxes, similarity) needs no OCR
engine and runs everywhere; the one real-read test takes the same
`requires_tesseract` skip the OCR suite takes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

from legibility import (cluster_boxes, normalise, prepare_for_ocr,  # noqa: E402
                        render_crop, render_to_px, similarity)

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.regions import Region  # noqa: E402
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun  # noqa: E402
from digitizer_core.stitchviz import render_design  # noqa: E402
from shapely.geometry import box  # noqa: E402

from .conftest import requires_tesseract


def test_normalise_keeps_only_letters_and_digits_upper_cased():
    assert normalise("Eat | Stay | Play") == "EATSTAYPLAY"
    assert normalise("est. 1895\n") == "EST1895"
    assert normalise("") == ""


def test_similarity_is_one_when_the_thread_reads_as_the_art_and_none_without_truth():
    assert similarity("BECKER MARINE", "BECKER MARINE") == 1.0
    assert similarity("BECKER", "B ECKER") == 1.0
    assert similarity("EAT STAY PLAY", "") == 0.0
    assert similarity("", "anything") is None
    assert 0.0 < similarity("HOTEL FREMONT", "HOTEL FRFMONT") < 1.0


def test_cluster_boxes_union_members_and_ignore_untagged_regions():
    def region(sid, poly, cid=None):
        meta = {"layer": 0}
        if cid:
            meta["text_cluster_id"] = cid
        return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="0000",
                      area_mm2=poly.area, source="test", meta=meta)
    regions = [region("a", box(0, 0, 2, 3), "T1"), region("b", box(3, 0, 5, 3), "T1"),
               region("c", box(10, 10, 12, 12)), region("d", box(20, 0, 22, 4), "T2")]
    got = cluster_boxes(regions)
    assert got == [("T1", (0.0, 0.0, 5.0, 3.0)), ("T2", (20.0, 0.0, 22.0, 4.0))]


def _two_line_plan() -> StitchPlan:
    """Two 20 mm black lines, at y = 0 and y = 10 (plan mm, y down), so the
    render is tall enough to hold a crop between them."""
    def line(y_mm: float) -> StitchRun:
        return StitchRun(points=[(x / 2.0, y_mm) for x in range(-20, 21)])
    block = StitchBlock(thread_index=0, thread_number="0020", rgb=(0, 0, 0),
                        runs=[line(0.0), StitchRun(points=line(10.0).points, jump=True)])
    return StitchPlan(blocks=[block], palette=[{"number": "0020", "name": "Black"}])


def test_render_crop_maps_plan_millimetres_onto_the_rendered_thread():
    """The line at y = 0 lands in the crop asked for at y = 0, the line at
    y = 10 in the crop at y = 10, and the crop between them holds no thread —
    the y flip, the pad and the clamp are right."""
    plan = _two_line_plan()
    design = plan_to_design(plan)
    img = render_design(design, px_per_mm=12.0)
    top = render_crop(img, design, (-10.0, -0.5, 10.0, 0.5), 12.0, pad_mm=0.3)
    mid = render_crop(img, design, (-10.0, 4.0, 10.0, 6.0), 12.0, pad_mm=0.3)
    low = render_crop(img, design, (-10.0, 9.5, 10.0, 10.5), 12.0, pad_mm=0.3)
    assert top.size and mid.size and low.size
    assert cv2.cvtColor(top, cv2.COLOR_BGR2GRAY).min() < 80, "no thread where the first line is"
    assert cv2.cvtColor(low, cv2.COLOR_BGR2GRAY).min() < 80, "no thread where the second line is"
    assert cv2.cvtColor(mid, cv2.COLOR_BGR2GRAY).min() > 150, "thread between the lines"
    # A box wholly outside the render is an EMPTY crop, never a wrapped one.
    assert render_crop(img, design, (-10.0, -50.0, 10.0, -40.0), 12.0).size == 0
    to_px = render_to_px(design, 12.0)
    h, w = img.shape[:2]
    for x, y in ((-10.0, 0.0), (10.0, 10.0)):
        px, py = to_px(x, y)
        assert 0 <= px < w and 0 <= py < h


def test_prepare_for_ocr_gives_white_ground_either_way():
    dark_on_light = np.full((20, 60, 3), 240, np.uint8)
    cv2.rectangle(dark_on_light, (10, 5), (50, 15), (20, 20, 20), -1)
    light_on_dark = 255 - dark_on_light
    a = prepare_for_ocr(dark_on_light)
    b = prepare_for_ocr(light_on_dark)
    for out in (a, b):
        assert out.shape[0] >= 96
        border = np.concatenate([out[0, :], out[-1, :], out[:, 0], out[:, -1]])
        assert border.min() == 255


@requires_tesseract
def test_a_block_capital_word_reads_back_from_a_plain_raster():
    from legibility import ocr

    img = np.full((120, 520, 3), 255, np.uint8)
    cv2.putText(img, "BECKER", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 0), 8, cv2.LINE_AA)
    text, conf = ocr(img, 7)
    assert similarity("BECKER", text) >= 0.8, text
    assert conf > 50.0, conf
