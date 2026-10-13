"""What the Column lane takes that is not a letter.

`tools/column_capture_census.py` counts the shapes `columns.is_lettering`
admits. The house-angle group (`lettering_group`) has no ink link and no
"is this a stroke" test, so a grid of colour patches (`test_preflight`'s
12-patch fixture, #863) and a ramp of 14.4 mm discs (`photo/fur_ramp.png`)
read as lines of lettering. `cfg.lettering_columns_skip_blobs` (default OFF)
refuses a tagged shape that is a solid blob.

Pins here are at the TAG level (`run_stages` + `is_lettering`): the lane's
reach, not its stitches, which is what a tripwire on "gains captures" needs
and what keeps this file cheap.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core.columns import is_lettering, is_solid_blob
from digitizer_core.pipeline import run_stages
from tests.conftest import TESTDATA


def _grid_image():
    colors = [(230, 40, 40), (40, 180, 40), (40, 40, 230), (230, 230, 40),
              (230, 40, 230), (40, 230, 230), (140, 70, 20), (250, 140, 20),
              (120, 20, 160), (20, 120, 90), (90, 90, 90), (10, 10, 10)]
    img = np.full((340, 460, 3), 255, np.uint8)
    for i, c in enumerate(colors):
        row, col = divmod(i, 4)
        y, x = 20 + row * 105, 20 + col * 110
        img[y:y + 85, x:x + 90] = c
    return img


def _taken(source, **kw) -> set[str]:
    cfg = PipelineConfig(target_width_mm=kw.pop("target_width_mm", 80.0), **kw)
    res = run_stages(source, cfg)
    return {r.shape_id for r in res.regions if is_lettering(r, cfg)}


# --- the predicate ----------------------------------------------------------

def test_blob_predicate_separates_patches_from_strokes():
    assert is_solid_blob(box(0, 0, 14.4, 14.4))                 # a patch
    assert is_solid_blob(Point(0, 0).buffer(8.0, 64))           # a disc
    assert not is_solid_blob(box(0, 0, 1.5, 6.5))               # an I
    assert not is_solid_blob(box(0, 0, 6.5, 1.5))               # a bar
    ell = unary_union([box(0, 0, 1.6, 6.5), box(0, 0, 4.5, 1.6)])
    assert not is_solid_blob(ell)                               # an L
    ring = Point(0, 0).buffer(3.2, 64).difference(Point(0, 0).buffer(1.9, 64))
    assert not is_solid_blob(ring)                              # an O
    bold = box(0, 0, 5.0, 16.7)                                 # Becker's bold cap stem
    assert not is_solid_blob(bold)


def test_guard_is_off_by_default():
    assert PipelineConfig().lettering_columns_skip_blobs is False


# --- the tripwire: known non-text fixtures take nothing --------------------

@pytest.mark.parametrize("fixture", ["logo_alpha.png", "ribbon_curve.png",
                                     "bg_uncertain.png", "photo/region_blobs.png"])
def test_non_text_fixtures_gain_no_lane_captures(fixture):
    """Census 2026-10-13: these scorecard fixtures carry no lettering, and the
    lane takes 0 of their shapes. A change to either tagger that makes the
    lane take one fails here, before it reaches a customer's design."""
    assert _taken(TESTDATA / fixture, garment_id="left_chest", max_colors=6) == set()


def test_colour_grid_capture_is_pinned_and_the_guard_clears_it():
    """The synthetic grid is the KNOWN false capture: with the guard OFF the
    lane takes all 12 patches (house group only, `text_candidate` False);
    with it ON, none. If the OFF count moves, the taggers moved: re-read the
    census before editing the number."""
    grid = _grid_image()
    assert len(_taken(grid, target_width_mm=100.0)) == 12
    assert _taken(grid, target_width_mm=100.0, lettering_columns_skip_blobs=True) == set()


def test_fur_ramp_discs_are_the_second_known_false_capture():
    """`photo/fur_ramp.png`: eight 14.4 mm discs, all tagged by the house
    group alone (census 2026-10-13); the guard clears all eight."""
    path = TESTDATA / "photo/fur_ramp.png"
    kw = dict(garment_id="left_chest", max_colors=6)
    assert len(_taken(path, **kw)) == 8
    assert _taken(path, lettering_columns_skip_blobs=True, **kw) == set()


def test_guard_keeps_the_letters_on_enthusiast():
    """Every letter the lane takes on the enthusiast wordmark is still taken
    with the guard ON (the one extra shape the lane takes there, the shield
    star, is not a solid blob and is out of this guard's reach)."""
    path = TESTDATA / "photo/enthusiast_logo.png"
    off = _taken(path, garment_id="left_chest", max_colors=6)
    on = _taken(path, garment_id="left_chest", max_colors=6, lettering_columns_skip_blobs=True)
    assert len(off) >= 10        # tag level: stage 7 builds columns for 11 of them
    assert on == off
