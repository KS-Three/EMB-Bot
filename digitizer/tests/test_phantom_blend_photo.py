"""The photo lane dissolves compression halos too (`cfg.dissolve_phantom_blends`).

The flat lane has folded phantom blend colours since before the photo lane
existed — `stage2_quantize._quantize_population`, "anti-alias: majority
filter, then phantom-blend dissolve", whose own comment records what happens
without it: *"two extra pale threads, plus ~30 sliver regions that then had
to be absorbed downstream"*. The photo/gradient lane never got that pass, and
`docs/kent-review-2026-09-03.md` bills the gap on `logo_bridge_bar.jpg`: a
four-colour logo arriving on **13 cones**, four of them grey — Skylight,
Saturn Grey, Silver, Umber — sewing nothing but the JPEG's ringing around the
black spokes.

Measured on that fixture @ 80 mm, `max_colors=6`, satin on:

    regions           74 -> 20
    blocks            13 -> 10
    stitches      14,607 -> 10,991      (-24.8%)
    trims            114 -> 55          (-51.8%)
    thread          30.7 -> 26.0 m
    palette worst-excess dE00  20.76 -> 6.08

`tools/halo_spools.py` is the instrument that bills it, and it reads 44 halo
regions before and 0 after. Across the committed corpus it finds halo cones on
exactly three fixtures — bridge (4), golden_tee (1), gaulke (1) — and none on
becker, fremont, enthusiast, drone, whitebg, golke, summit or tires, which is
the evidence that the test is specific to compression artefacts rather than to
thin features generally.

DEFAULT OFF. It moves the region set on every gradient-class design, so it
waits on Kent's look at a render (`docs/renders/halo-dissolve-2026-09-04/`),
not on a green suite.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.stage2_photo_segment import (_PAGE, _blend_side,
                                                 dissolve_phantom_blends)
from digitizer_core.warnings_codes import PHOTO_BLEND_DISSOLVED

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
BRIDGE = TESTDATA / "photo" / "logo_bridge_bar.jpg"

BLACK = np.array([10.0, 0.0, 0.0])
WHITE = np.array([97.0, 0.0, 0.0])
GREY = np.array([53.0, 0.0, 0.0])       # halfway BLACK->WHITE
TEAL = np.array([53.0, -20.0, -17.0])   # same lightness, nowhere near the line


# --- the colour test, on its own ----------------------------------------------

def test_a_midpoint_grey_is_a_blend_of_black_and_white():
    assert _blend_side(GREY, [(1, BLACK), (2, WHITE)], 6.0) is not None


def test_teal_at_the_same_lightness_is_NOT_a_blend():
    """The property that makes this safe to ship. A designer's thin keyline
    is a CHOSEN colour: it can sit at the same L as the halo would and still
    be nowhere near the Lab segment. Drop this test and the pass eats
    lettering."""
    assert _blend_side(TEAL, [(1, BLACK), (2, WHITE)], 6.0) is None


def test_a_blend_goes_to_the_END_IT_IS_NEARER():
    """Not to the nearest colour anywhere — see the note in the pass. A ring
    at t 0.2 belongs to the shape it hugs; at t 0.8 to what lies beyond."""
    near_black = BLACK + 0.25 * (WHITE - BLACK)
    near_white = BLACK + 0.75 * (WHITE - BLACK)
    assert _blend_side(near_black, [(1, BLACK), (2, WHITE)], 6.0) == 1
    assert _blend_side(near_white, [(1, BLACK), (2, WHITE)], 6.0) == 2


def test_the_page_can_be_the_nearer_end():
    """`_PAGE` is a real answer, not a sentinel that falls through: the
    commonest halo in the corpus is the one around dark art on a white page,
    and its outer band belongs to the page."""
    near_page = BLACK + 0.8 * (WHITE - BLACK)
    assert _blend_side(near_page, [(1, BLACK), (_PAGE, WHITE)], 6.0) == _PAGE


def test_a_colour_at_either_END_of_the_segment_is_not_a_blend():
    """The 0.15-0.85 window, the flat lane's own: a colour sitting on top of
    one of its neighbours is that neighbour, not an interpolation."""
    assert _blend_side(BLACK + 0.05 * (WHITE - BLACK),
                       [(1, BLACK), (2, WHITE)], 6.0) is None
    assert _blend_side(BLACK + 0.95 * (WHITE - BLACK),
                       [(1, BLACK), (2, WHITE)], 6.0) is None


# --- the pass over a label array ----------------------------------------------

def _striped(bands: list[tuple[int, np.ndarray, int]], h: int = 40):
    """A label array of vertical bands: [(label, lab, width_px), ...]."""
    total = sum(w for _, _, w in bands)
    labels = np.zeros((h, total), np.int64)
    lab_img = np.zeros((h, total, 3), np.float64)
    x = 0
    for lbl, lab, w in bands:
        labels[:, x:x + w] = lbl
        lab_img[:, x:x + w] = lab
        x += w
    return labels, lab_img, np.ones((h, total), bool)


def test_a_thin_grey_band_between_two_wide_ones_dissolves():
    labels, lab_img, valid = _striped(
        [(1, BLACK, 20), (2, GREY, 2), (3, WHITE, 20)])
    out, drop, warns = dissolve_phantom_blends(
        labels, valid, lab_img, PipelineConfig(), None, 4.0)
    assert drop is None, "no page here — nothing should leave the design"
    assert set(np.unique(out).tolist()) == {1, 3}, "the grey band is gone"
    assert warns and warns[0]["code"] == PHOTO_BLEND_DISSOLVED
    assert warns[0]["count"] == 1


def test_a_WIDE_grey_band_survives():
    """The edge-fraction gate. A grey stripe as wide as its neighbours is a
    colour the design uses, not a transition between two others."""
    labels, lab_img, valid = _striped(
        [(1, BLACK, 20), (2, GREY, 20), (3, WHITE, 20)])
    out, _drop, warns = dissolve_phantom_blends(
        labels, valid, lab_img, PipelineConfig(), None, 4.0)
    assert set(np.unique(out).tolist()) == {1, 2, 3}
    assert warns == []


def test_a_thin_TEAL_band_survives():
    """The colour gate, at the width where the edge gate has already given
    up. This is the case that would cost real lettering."""
    labels, lab_img, valid = _striped(
        [(1, BLACK, 20), (2, TEAL, 2), (3, WHITE, 20)])
    out, _drop, warns = dissolve_phantom_blends(
        labels, valid, lab_img, PipelineConfig(), None, 4.0)
    assert set(np.unique(out).tolist()) == {1, 2, 3}
    assert warns == []


def test_a_stack_of_rings_all_settles_on_real_labels():
    """Chained folds. Ringing arrives as several bands, each one's nearer
    side being the next band in; an unresolved pointer would leave a band
    wearing a dissolved band's id, which is not a label any more."""
    dark = BLACK + 0.3 * (WHITE - BLACK)
    mid = BLACK + 0.5 * (WHITE - BLACK)
    labels, lab_img, valid = _striped(
        [(1, BLACK, 20), (2, dark, 2), (3, mid, 2), (4, WHITE, 20)])
    out, _drop, _warns = dissolve_phantom_blends(
        labels, valid, lab_img, PipelineConfig(), None, 4.0)
    survivors = set(np.unique(out).tolist())
    assert survivors <= {1, 4}, f"a band landed on a dissolved id: {survivors}"


def test_fewer_than_three_labels_is_a_no_op():
    labels, lab_img, valid = _striped([(1, BLACK, 20), (2, WHITE, 20)])
    out, drop, warns = dissolve_phantom_blends(
        labels, valid, lab_img, PipelineConfig(), None, 4.0)
    assert out is labels and drop is None and warns == []


def test_page_side_halo_is_returned_to_the_background():
    """The band nearer the page leaves the foreground rather than growing
    the shape by the full halo stack."""
    near_page = BLACK + 0.8 * (WHITE - BLACK)
    labels, lab_img, valid = _striped(
        [(1, BLACK, 20), (2, near_page, 2), (3, WHITE, 20)])
    # WHITE here stands in for a real region; the page endpoint is the RGB.
    out, drop, warns = dissolve_phantom_blends(
        labels, valid, lab_img, PipelineConfig(), np.array([248, 248, 248]), 4.0)
    assert warns and warns[0]["count"] >= 1
    assert drop is None or drop.any() or set(np.unique(out).tolist()) < {1, 2, 3}


# --- the fixture the defect was found on --------------------------------------

@pytest.fixture(scope="module")
def bridge_pair():
    def run(on: bool):
        return digitize(BRIDGE, PipelineConfig(
            target_width_mm=80.0, max_colors=6, satin=True,
            garment_id="left_chest", dissolve_phantom_blends=on))
    return run(False), run(True)


def test_default_is_off():
    assert PipelineConfig().dissolve_phantom_blends is False


def test_bridge_bar_loses_its_grey_cones(bridge_pair):
    """The four cones `docs/kent-review-2026-09-03.md` named, by number."""
    (off_r, off_p), (on_r, on_p) = bridge_pair
    off_cones = {c.get("number") for c in off_p.palette}
    on_cones = {c.get("number") for c in on_p.palette}
    for grey in ("0145", "0182", "0465", "3971", "0108", "0111"):
        assert grey in off_cones, f"{grey} should be there to lose"
        assert grey not in on_cones, f"{grey} still sewing halo"


def test_bridge_bar_costs_much_less(bridge_pair):
    (off_r, off_p), (on_r, on_p) = bridge_pair
    assert len(on_r.regions) < len(off_r.regions) / 3
    assert on_p.stats.trims < off_p.stats.trims / 1.8
    assert on_p.stats.stitch_count < off_p.stats.stitch_count
    assert len(on_p.blocks) < len(off_p.blocks)


def test_bridge_bar_keeps_its_artwork(bridge_pair):
    """The four colours the logo actually has still sew: yellow, black, red
    and the teal lettering. Losing one of these would make the trim saving
    worthless."""
    (_off_r, _off_p), (on_r, on_p) = bridge_pair
    cones = {c.get("number") for c in on_p.palette}
    for kept in ("0501", "0020", "1720", "4531"):
        assert kept in cones, f"{kept} — real artwork — was dissolved"


def test_bridge_bar_palette_fits_the_design_better(bridge_pair):
    """An independent read: the palette's own worst excess. Spending medoids
    on ringing is why it was 20 dE00 out."""
    (off_r, _), (on_r, _) = bridge_pair

    def excess(result):
        for w in result.warnings:
            if w["code"] == "PHOTO_PALETTE_SELECTED":
                return w["max_excess_de00"]
        return None

    assert excess(on_r) < excess(off_r) / 2


def test_bridge_bar_silhouette_barely_moves(bridge_pair):
    """Returning page-side halo to the background must not shrink the
    design meaningfully — the halo straddles the true edge, so removing its
    outer half and folding its inner half should roughly cancel."""
    (off_r, _), (on_r, _) = bridge_pair
    off_area = sum(r.area_mm2 for r in off_r.regions)
    on_area = sum(r.area_mm2 for r in on_r.regions)
    assert 0.90 < on_area / off_area <= 1.0, f"{on_area:.0f} vs {off_area:.0f} mm²"
