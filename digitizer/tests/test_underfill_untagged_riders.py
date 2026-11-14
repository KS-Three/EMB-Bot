"""`cfg.underfill_untagged_riders` (2026-11-05, built OFF).

MFab hat on the Studio's own route classes photo_scene at every width. Stage 2
keeps every small-line letter as its own black region; what loses them is the
under-fill's rider rule, which reads only TEXT-TAGGED shapes: at 60 mm nothing
in AND WELDING LLC is tagged (0 riders), at 100.8 mm W and E arrive joined
(one untagged 53.6 mm2 region), and an untagged shape merges into the black
under-fill and sews under the white panel. ON, a lettering-thin untagged shape
in a hole of the sewn white field, standing in a row of others, rides too.
`docs/photo-superpixel-merge-2026-11-05.md`.
"""
from __future__ import annotations

import cv2
import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, silhouette_underfill as su
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.regions import Region

from .conftest import TESTDATA


def _reg(sid, poly, thread, meta=None):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": 0, **(meta or {})})


def _keyline_art():
    """A black band (the ring) round a white field whose holes hold: a row of
    three thin black letters, one thin black bar alone (M-FAB's hyphen) and one
    thick black body (a big letter's)."""
    letters = [box(x, 10, x + 0.8, 16) for x in (20, 24, 28)]   # stroke 0.71 mm
    hyphen = box(10, 25, 16, 27)                                 # stroke 1.50 mm, no row
    body = box(40, 8, 90, 32)                                    # stroke 16.9 mm
    black = letters + [hyphen, body]
    field = Polygon(box(5, 5, 95, 35).exterior.coords,
                    [s.buffer(0.5, join_style=2).exterior.coords for s in black])
    ring = Polygon(box(-20, -10, 120, 50).exterior.coords, [box(5, 5, 95, 35).exterior.coords])
    regions = [_reg("ring", ring, 0), _reg("field", field, 1, {"sew_enclosed_white": "field"})]
    regions += [_reg(f"L{i}", p, 0) for i, p in enumerate(letters)]
    regions += [_reg("hyphen", hyphen, 0), _reg("body", body, 0)]
    return regions


def test_off_reads_no_untagged_shape():
    assert su.find_riders(_keyline_art()) == []
    assert su.find_riders(_keyline_art(), untagged=False) == []


def test_on_rides_the_row_of_thin_letters_only():
    assert su.find_riders(_keyline_art(), untagged=True) == ["L0", "L1", "L2"]


def test_the_flag_is_off_by_default():
    assert PipelineConfig().underfill_untagged_riders is False


# --- MFab hat, the Studio's route (photo_scene), three widths -----------------------

BLACK_WHITE_BLACK = ["0020 Black", "0015 White", "0020 Black"]


def _mfab(width_mm, untagged):
    # photo_prep=False: the no-cutout lane CI runs (no rembg venv there);
    # the cutout lane is tests/test_mfab_cutout_lane.py.
    cfg = PipelineConfig(photo_prep=False, target_width_mm=width_mm, max_colors=6, satin=True,
                         detail_layer=False, edge_cap="none", sew_enclosed_white=True,
                         sew_enclosed_rgb=(255, 255, 255), faces_route_flat=True,
                         garment_id="hat_front", garment_rgb=(235, 232, 223),
                         underfill_untagged_riders=untagged)
    pix = cv2.imread(str(TESTDATA / "art" / "logo_mfab_hat.png"), cv2.IMREAD_UNCHANGED)
    seen = {}
    real = su.find_riders

    def spy(*a, **kw):
        seen["riders"] = real(*a, **kw)
        return seen["riders"]
    su.find_riders = spy
    try:
        res = finish_generation(build_generation(pix, cfg), cfg)
        plan = plan_stitches(res, cfg)
    finally:
        su.find_riders = real
    return [c["name"] for c in plan_to_design(plan, name="t")["colors"]], seen.get("riders", [])


@pytest.mark.parametrize("width", [60.0, 100.8, 113.5])
def test_mfab_hat_small_line_rides_on(width):
    blocks_off, riders_off = _mfab(width, False)
    blocks_on, riders_on = _mfab(width, True)
    assert blocks_on == BLACK_WHITE_BLACK
    assert set(riders_off) <= set(riders_on)
    if width < 113.5:
        # 60: the tagger reads none of the small line; 100.8: W+E arrive untagged
        assert len(riders_on) > len(riders_off)
    else:
        # every small letter is already tagged at the hat's own size: nothing moves
        assert riders_on == riders_off and blocks_on == blocks_off


# --- a real photograph: nothing to ride, nothing refused -------------------------------

class _Stop(Exception):
    pass


def test_owl_photograph_rides_nothing_on(monkeypatch):
    """owl_kent.jpg (a real photograph) on the Studio's 80 mm request, stopped
    at the under-fill call in `plan_stitches`: the rider read is the same OFF
    and ON (the census of 39 Commons rows + 8 scorecard photo rows moved one
    row only, the line-art logo `outline_lineart_logo`)."""
    seen = {}

    def probe(regions, unsewn, cfg, outlines, pinned=()):
        seen["off"] = su.find_riders(regions, unsewn, outlines)
        seen["on"] = su.find_riders(regions, unsewn, outlines, untagged=True)
        raise _Stop
    monkeypatch.setattr(su, "apply_cfg", probe)
    # `silhouette_underfill_photo=True`: Kent's 2026-11-05 gate
    # (`pipeline.gate_underfill_for_photo`) skips the under-fill call on a
    # photo class, so the probe below is never reached on the owl without the
    # old arm. This test reads the RIDER census on a photograph's regions, so
    # it opts in; the gate has its own tests (`test_photo_underfill_gate.py`).
    cfg = PipelineConfig(target_width_mm=80.0, max_colors=6, satin=True, garment_id="left_chest",
                         sew_enclosed_white=True, underfill_untagged_riders=True,
                         silhouette_underfill_photo=True)
    pix = cv2.imread(str(TESTDATA / "photo" / "owl_kent.jpg"), cv2.IMREAD_UNCHANGED)
    with pytest.raises(_Stop):
        plan_stitches(finish_generation(build_generation(pix, cfg), cfg), cfg)
    assert seen["on"] == seen["off"]
