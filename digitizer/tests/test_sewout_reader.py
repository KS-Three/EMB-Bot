"""Calibration for digitizer_core.calibration.reader — the card-from-a-photo instrument.

No photo of a sewn card exists yet, so the reader is calibrated the way
`test_fill_pitch.py` calibrates its instrument: plant KNOWN distortions in the
card's own design, fake a phone photo of it, and require the reader to hand
them back. The load-bearing test is `recovers_two_different_pulls` — one
recovered value proves nothing (a stopped clock reads 0.4), two different
ones prove the reader reads the picture.

The card here is REDUCED — blocks 1, 2, 3 and 6 (lock bars, fill squares,
satin bars, seam pairs) — because block 5 runs the full pipeline four times
(~14 s) and the words are exercised by the CLI's `--simulate`, not here.
Block 4's paths are not measured by the reader at all.

What this cannot certify, stated so nobody reads green as "sew-out settled":
the simulator draws thread the way `stitchviz` draws it. Real cloth thins a
filament under tension, has nap, puckers and stretches in the hoop. The
tolerances below are the reader's floor on a PICTURE; the cloth's floor is
Kent's to measure (ROADMAP gate 1 stands).
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core.adapter import plan_to_design
from digitizer_core.calibration import reader as R

from digitizer_core.calibration import card as C

PHOTO_PX_PER_MM = 12.0     # a phone at ~15 cm; well under the 20 px/mm read raster
# Measured 2026-09-30 on the simulated photo: heights within 0.01 mm of the
# planted value, widths within 0.067 (a systematic under-read of row ends).
# 0.1 is the figure the brief asks of the reader, and leaves room for a
# different JPEG decoder (Kent's box is Windows) to move a pixel.
TOL_MM = 0.1


@pytest.fixture(scope="module")
def card() -> dict:
    """Blocks 1-3 and 6 of the real card, through the real builders."""
    keep = ("1 LOCK", "2 FILL", "3 WSATIN", "6 SEAMA", "6 SEAMB")
    saved = C.BLOCKS
    C.BLOCKS = [b for b in saved if b[0] in keep]
    try:
        plan, _ = C.build_card()
    finally:
        C.BLOCKS = saved
    return plan_to_design(plan, name="reduced card")


@pytest.fixture(scope="module")
def reference(card) -> dict:
    return R.read_reference(card)


def _row(cmp: dict, name: str) -> dict:
    return next(r for r in cmp["features"] if r["name"] == name)


def _photo_compare(card, reference, distortions, mode="corners", seed=0, px=PHOTO_PX_PER_MM):
    bent = R.distort(card, distortions) if distortions else card
    photo, corners = R.simulate_photo(bent, px, seed=seed)
    rd = R.read_card(photo, card, corners_px=corners, mode=mode)
    return R.compare(rd, reference), rd


# --- layout ------------------------------------------------------------------

def test_features_come_from_the_run_index(card):
    feats = {f.name: f for f in R.features_from_design(card)}
    for bar in ("lock-A", "lock-B", "satin-3mm", "satin-4mm", "satin-5mm"):
        assert feats[bar].role == "bar"
    for sq in ("fill-A-0.40", "fill-B-0.20", "fill-C"):
        assert feats[sq].role == "square"
    assert feats["fill-C"].shapes == ("fill-C-pass1", "fill-C-pass2")
    seams = [f for f in feats.values() if f.role == "seam"]
    assert len(seams) == 8
    # Nominal boxes are the emitter's own: the 4 mm bar is 25 mm long and
    # its satin rails sit 3.8 mm apart (ribbon width 3.45 + rail inset).
    x0, y0, x1, y1 = feats["satin-4mm"].bbox_mm
    assert x1 - x0 == pytest.approx(25.0, abs=0.05)
    assert 3.0 < y1 - y0 < 4.0


def test_words_cluster_per_run_not_per_shape():
    """Two words whose letters share a pipeline shape id must still come
    out as two features — the ids collide on the real card (2026-09-30)."""
    st, runs = [], []

    def letter(x_mm, shape):
        i0 = len(st)
        for k in range(6):
            st.append({"x": int((x_mm + 0.4 * k) * 10), "y": 0 if k % 2 else 40, "type": "stitch"})
        runs.append({"i0": i0, "i1": len(st) - 1, "kind": "satin", "shape": shape, "role": "", "block": 9})

    letter(0.0, "Sshared")
    letter(3.0, "Sother")
    letter(20.0, "Sshared")      # the same id, a word away
    st.append({"x": 0, "y": 0, "type": "end"})
    design = {"stitches": st, "runs": runs, "colors": [{"r": 0, "g": 0, "b": 0}] * 10}
    words = [f for f in R.features_from_design(design) if f.role == "word"]
    assert [w.name for w in words] == ["word-0", "word-1"]
    assert words[0].bbox_mm[2] < 10 < words[1].bbox_mm[0]


# --- the reader against itself ------------------------------------------------

def test_an_undistorted_photo_reads_as_the_render(card, reference):
    cmp, _ = _photo_compare(card, reference, [])
    for r in cmp["features"]:
        if r["role"] in ("bar", "square"):
            assert abs(r["d_width_mm"]) <= TOL_MM, r
            assert abs(r["d_height_mm"]) <= TOL_MM, r
            assert abs(r["d_coverage"]) <= 0.01, r
    assert all(abs(g) <= 0.05 for g in cmp["seam_gap_delta_mm"].values())


@pytest.mark.parametrize("pull4, pull5, fillx", [(-0.3, -0.5, -0.4), (-0.6, -0.2, -0.8)])
def test_recovers_two_different_pulls(card, reference, pull4, pull5, fillx):
    """The load-bearing calibration: two distortion sets, each recovered to
    its OWN value. A satin bar's zigzag runs across the bar, so its pull-in
    is a height change; a fill square's rows run along x, so its pull-in is
    a width change."""
    truth = [R.Distortion("satin-4mm", dx_mm=0.4, dy_mm=pull4),
             R.Distortion("satin-5mm", dx_mm=0.4, dy_mm=pull5),
             R.Distortion("fill-B-0.20", dx_mm=fillx)]
    cmp, _ = _photo_compare(card, reference, truth)
    assert _row(cmp, "satin-4mm")["d_height_mm"] == pytest.approx(pull4, abs=TOL_MM)
    assert _row(cmp, "satin-5mm")["d_height_mm"] == pytest.approx(pull5, abs=TOL_MM)
    assert _row(cmp, "fill-B-0.20")["d_width_mm"] == pytest.approx(fillx, abs=TOL_MM)
    # Push along the bar is read too, and the untouched bar stays put.
    assert _row(cmp, "satin-4mm")["d_width_mm"] == pytest.approx(0.4, abs=TOL_MM)
    assert abs(_row(cmp, "satin-3mm")["d_height_mm"]) <= TOL_MM
    assert abs(_row(cmp, "fill-A-0.40")["d_width_mm"]) <= TOL_MM
    # The draft averages the three wide-satin bars, the untouched 3 mm one
    # included — a profile is a fabric's number, not a bar's.
    draft = cmp["draft_profile_delta"]
    assert draft["satin_pull_in_mm"] == pytest.approx(-(pull4 + pull5 + 0.0) / 3, abs=TOL_MM)


def test_auto_registration_needs_no_marks(card, reference):
    """minAreaRect + ECC against the plan's own ink, no corners given."""
    truth = [R.Distortion("satin-4mm", dy_mm=-0.4), R.Distortion("fill-B-0.20", dx_mm=-0.5)]
    cmp, rd = _photo_compare(card, reference, truth, mode="auto", seed=2)
    assert rd["ecc"] is not None and rd["ecc"] > 0.9
    assert _row(cmp, "satin-4mm")["d_height_mm"] == pytest.approx(-0.4, abs=0.1)
    assert _row(cmp, "fill-B-0.20")["d_width_mm"] == pytest.approx(-0.5, abs=0.1)


def test_fiducials_register_off_the_marks(card, reference):
    """The proposed card change: four corner marks, read by centroid."""
    truth = [R.Distortion("satin-5mm", dy_mm=-0.35), R.Distortion("fill-B-0.20", dx_mm=-0.6)]
    fid = R.with_fiducials(card)
    bent = R.distort(fid, truth)
    photo, _ = R.simulate_photo(bent, PHOTO_PX_PER_MM, seed=5)
    rd = R.read_card(photo, fid, mode="fiducials")
    cmp = R.compare(rd, reference)
    assert _row(cmp, "satin-5mm")["d_height_mm"] == pytest.approx(-0.35, abs=TOL_MM)
    assert _row(cmp, "fill-B-0.20")["d_width_mm"] == pytest.approx(-0.6, abs=TOL_MM)
    # The marks are outside the artwork and not features themselves.
    assert all(f.name != "__fiducial__" for f in R.features_from_design(fid))


def test_seam_opens_when_the_rows_pull_back(card, reference):
    """Block 6: the zero-underlap pair opens a bare gap when the left half's
    rows pull back 1 mm per side; the other rungs, untouched, do not. The
    ink overlaps the penetrations by half a filament each side, so 2.0 mm
    of shrink is ~0.6 mm of bare cloth, and blur under-reads a hairline."""
    truth = [R.Distortion("seam-A-0", dx_mm=-2.0)]
    cmp, _ = _photo_compare(card, reference, truth, seed=7)
    gaps = cmp["seam_gap_delta_mm"]
    assert 0.3 <= gaps["0"] <= 0.8, gaps      # read 0.45 here, 0.40 at 6 px/mm
    for rung in ("0.25", "0.5", "1"):
        assert abs(gaps[rung]) <= 0.05, gaps


def test_distort_matches_exactly_unless_starred(card):
    with pytest.raises(ValueError):
        R.distort(card, [R.Distortion("seam-A")])
    d = R.distort(card, [R.Distortion("seam-A-*", dx_mm=-0.2)])
    n = sum(1 for r in d["runs"] if r["shape"].startswith("seam-A-"))
    assert n == sum(1 for r in card["runs"] if r["shape"].startswith("seam-A-"))
    only = R.distort(card, [R.Distortion("seam-A-0", dx_mm=-0.2)])
    moved = [r["shape"] for r, q in zip(only["runs"], card["runs"])
             if any(only["stitches"][i] != card["stitches"][i] for i in range(r["i0"], r["i1"] + 1))]
    assert set(moved) == {"seam-A-0"}


def test_no_thread_is_reported_not_invented(card):
    """A feature cut out of the picture reads 'no thread found', never a
    number."""
    _, _, W, H = R._frame(card)
    blank = np.full((int((H + 6) * 20), int((W + 6) * 20), 3), (196, 203, 208), np.uint8)
    rd = R.read_card(blank, card, corners_px=R.plan_corners_px(W, H), mode="corners")
    assert all(r["note"] == "no thread found" for r in rd["features"])
    with pytest.raises(ValueError):
        R.auto_corners(blank)
