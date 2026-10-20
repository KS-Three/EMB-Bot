"""`cfg.open_cored_counters` -- a small counter with a page-coloured middle stays open.

MASTER_SCOPE 47's residue (2026-10-19): golden_tee's bevelled O at a 4 and 5 mm
cap. Its counter is a white core (stage 1's `enclosed_mask`) inside a dark keyline,
a grey bevel and two slivers, each under the area floor and under a thread wide.
`resolve_small_regions` gave every band to the O at 5 mm (0.00 open) and kept the
keyline as a ring stage 4 filled to a Silver disc at 4 mm (0.15 open). Built OFF.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from digitizer_core import PipelineConfig, digitize
from digitizer_core.stage3_segment import RegionMask, cored_counters, resolve_small_regions

from .conftest import TESTDATA

PX_PER_MM = 20.0         # floor (1.5 mm x 20)^2 = 900 px; thread 0.4 mm = 8 px
LAYER_LAB = np.array([[78.0, 11.0, 75.0],    # 0 the gold letter
                      [14.0, -7.0, -6.0],    # 1 the dark keyline
                      [77.0, 0.0, 0.0],      # 2 the grey bevel
                      [100.0, 0.0, 0.0],     # 3 the white core
                      [40.0, 0.0, 0.0]])     # 4 a dark detail


def _disc(shape, cy, cx, r):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r


def _o(letter_r=40, counter_r=16, keyline=2, bevel=2, core=True, stroke=None):
    """A gold O (outer radius `letter_r` px) on the page, its counter of radius
    `counter_r` ringed from outside in by a `keyline`-px dark band and a
    `bevel`-px grey band round a white core. -> (regions, core mask).
    `stroke` replaces the O's ring by a band that narrow (the letter itself
    under a thread wide). `core=False` paints the middle grey instead (no page
    colour in it)."""
    shape = (120, 120)
    c = 60
    outer = _disc(shape, c, c, letter_r)
    hole = _disc(shape, c, c, counter_r)
    if stroke is not None:
        outer = _disc(shape, c, c, counter_r + stroke)
    letter = outer & ~hole
    k = hole & ~_disc(shape, c, c, counter_r - keyline)
    b = _disc(shape, c, c, counter_r - keyline) & ~_disc(shape, c, c, counter_r - keyline - bevel)
    mid = _disc(shape, c, c, counter_r - keyline - bevel)
    regions = [RegionMask.from_full(letter, 0), RegionMask.from_full(k, 1),
               RegionMask.from_full(b, 2)]
    if core:
        regions.append(RegionMask.from_full(mid, 3))
        core_mask = mid
    else:
        regions[-1] = RegionMask.from_full(b | mid, 2)
        core_mask = np.zeros(shape, bool)
    return regions, core_mask


def _resolve(regions, core):
    # chain_rescue=False: the gradient lane's call, where golden_tee's bands
    # are lost (the bands and core here sum over the floor and would chain).
    return resolve_small_regions(regions, PipelineConfig(), PX_PER_MM, enclosed_mask=core,
                                 layer_lab=LAYER_LAB, chain_rescue=False, counter_core=core)[0]


def _letter_holes(kept) -> int:
    """Holes in the letter's mask (4-connected components of its complement
    that do not reach the frame's edge)."""
    import cv2
    letter = next(r for r in kept if r.layer == 0)
    full = letter.full_mask()
    pad = np.ones((full.shape[0] + 2, full.shape[1] + 2), np.uint8)
    pad[1:-1, 1:-1] = ~full
    n, lab = cv2.connectedComponents(pad, connectivity=4)
    return n - 2   # minus the page and the background label 0


def test_the_flag_ships_off():
    assert PipelineConfig().open_cored_counters is False


def test_the_scene_is_what_its_docstring_says():
    regions, core = _o()
    floor = (1.5 * PX_PER_MM) ** 2
    assert regions[0].area >= floor                         # the letter is full-size
    assert all(r.area < floor for r in regions[1:])          # every band is sub-floor
    assert core.sum() >= 0.16 * PX_PER_MM ** 2               # the core clears the run floor


def test_off_every_band_stays_in_a_shape_that_sews():
    """OFF, the contrasting bands clear the run floors and are rescued as
    shapes of their own (`keep_thin_strokes`, golden_tee's 4 mm path, where the
    keyline ring became a Silver disc), or are absorbed into the letter (its
    5 mm path). Either way no pixel of a band is left out as a counter."""
    regions, core = _o()
    bands = regions[1].full_mask() | regions[2].full_mask()
    kept = resolve_small_regions(regions, PipelineConfig(), PX_PER_MM, enclosed_mask=core,
                                 layer_lab=LAYER_LAB, chain_rescue=False)[0]
    assert not [r for r in kept if r.source == "counter"]
    sewn = np.zeros_like(bands)
    for r in kept:
        sewn |= r.full_mask()
    assert (bands & ~sewn).sum() == 0


def test_on_every_band_and_the_core_stay_out_of_the_letter():
    regions, core = _o()
    letter_area = regions[0].area
    kept = _resolve(regions, core)
    letter = next(r for r in kept if r.layer == 0)
    assert letter.area == letter_area                        # nothing absorbed
    assert sorted(r.layer for r in kept if r.source == "counter") == [1, 2]
    assert _letter_holes(kept) == 1


def test_cored_counters_names_the_bands_and_walks_past_a_band_encloser():
    regions, core = _o()
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    got = cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 0.4 * PX_PER_MM)
    # the keyline and the bevel (the core is the enclosed guard's already)
    assert {1, 2} <= got
    assert 0 not in got


def test_no_page_colour_in_the_middle_no_counter():
    """A dark detail inside a letter (no enclosed core) is absorbed as before."""
    regions, core = _o(core=False)
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 8.0) == set()
    kept = _resolve(regions, core)
    assert not [r for r in kept if r.source == "counter"]


def test_a_counter_at_or_over_the_floor_is_not_the_floors_to_close():
    regions, core = _o(letter_r=58, counter_r=30)
    floor = (1.5 * PX_PER_MM) ** 2
    assert np.pi * 30 ** 2 >= floor
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 8.0) == set()


def test_a_letter_narrower_than_a_thread_is_a_band_and_ends_the_walk_empty():
    """The innermost non-band shape round the core is the letter; when every
    shape round it is a band, nothing is a counter (the page is not a letter)."""
    regions, core = _o(stroke=3)
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 8.0) == set()


def test_a_core_under_the_run_floor_is_noise():
    regions, core = _o()
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, float(core.sum()) + 1, 8.0) == set()


# --- OFF is byte-identical on the flat goldens; ON leaves them alone too --------------

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("flag", [False, True])
def test_goldens_are_byte_identical_either_way(fixture, flag):
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            open_cored_counters=flag))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
