"""Metric-core tests for tools/artfidelity_self.py.

Pure-array tests only: no corpus, no engine run, no service — the same rule
`test_enginefidelity.py` states for its sibling instrument, and for the same
reason. The instrument's job is to answer "does our stitch-out look like the
artwork" without a professional reference, so these pin the geometry and the
composite on inputs with hand-computable answers before the CLI ever touches a
real design. The full-corpus run is the CI job's business, not the suite's.

The `test_published_weights_*` pair is the load-bearing one. This instrument
was rebuilt on 2026-08-27 from a validation artifact after the original was
lost unpushed, and the composite weights are the one thing that was recovered
EXACTLY rather than re-chosen — by least squares over the 14 rows that artifact
published. Those rows are embedded below so the recovery is a regression guard:
if someone retunes the weights, these fail and say what they are breaking.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from skimage.color import deltaE_ciede2000

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import artfidelity_self as afs  # noqa: E402

# The validation artifact's published table, verbatim:
# (fixture, coverage, colour, structure, ARTFID). Nine scored rows then five
# refused; the composite is computed the same way for both, which is why the
# refused rows are just as good a constraint on the weights.
PUBLISHED = [
    ("bg_uncertain",      0.979, 1.000, 0.941, 97.1),
    ("logo_alpha",        0.927, 1.000, 0.892, 93.3),
    ("logo_whitebg",      0.927, 1.000, 0.887, 93.1),
    ("ribbon_curve",      0.805, 1.000, 0.932, 89.8),
    ("logo_script_tires", 0.824, 1.000, 0.805, 86.1),
    ("becker_marine",     0.805, 1.000, 0.763, 83.9),
    ("enthusiast",        0.662, 1.000, 0.774, 78.6),
    ("summit_badge",      0.748, 0.786, 0.559, 69.1),
    ("region_blobs",      0.443, 0.625, 0.492, 50.6),
    ("hotel_fremont",     0.984, 1.000, 0.840, 93.8),
    ("bridge_bar",        0.963, 0.802, 0.830, 87.6),
    ("drone_render",      0.895, 0.415, 0.631, 68.2),
    ("golden_tee",        0.723, 0.397, 0.825, 67.8),
    ("gaulke_roofing",    0.055, 0.000, 0.195, 9.0),
]

# The artifact rounds components to 3 decimals and the composite to 1, so a
# perfect weight vector still cannot reproduce a row exactly. Worst case for
# 0.40/0.25/0.35 over these rows is 0.08; anything materially above that is a
# different weighting, not rounding.
ROUNDING_SLACK = 0.09


def field(mask: np.ndarray) -> np.ndarray:
    return mask.astype(np.float64)


def disc(r_px, size=None, center=None):
    size = size or (2 * r_px + 21)
    cy, cx = center or (size // 2, size // 2)
    yy, xx = np.mgrid[:size, :size]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r_px ** 2


def write_rgba(path, rgba):
    Image.fromarray(rgba.astype(np.uint8), "RGBA").save(path)


# ---------------------------------------------------------------- constants

def test_rasterisation_constant_matches_the_sibling_probes():
    # artfidelity.py's THREAD_W_MM comment is explicit that a probe drifting
    # off the family's px/mm stops agreeing with the others about what
    # "covered" means. Read the sibling's own value rather than restating it,
    # so this fails if EITHER side moves.
    sys.path.insert(
        0, str(Path(__file__).resolve().parents[1] / "tools" / "pro_parity"))
    import artfidelity as sibling

    assert afs.RES == sibling.RES
    assert afs.SHIFT_MM == sibling.SHIFT_MM
    assert afs.SHIFT_STEP_MM == sibling.SHIFT_STEP_MM


def test_weights_sum_to_one():
    # Not cosmetic: the composite is reported on a 0-100 scale, so weights
    # summing to anything else silently rescales every published number.
    assert sum(afs.WEIGHTS) == pytest.approx(1.0)


# ------------------------------------------------------ the recovered weights

@pytest.mark.parametrize("name,cov,col,struct,artfid", PUBLISHED)
def test_published_weights_reproduce_each_artifact_row(name, cov, col, struct,
                                                       artfid):
    got = 100.0 * (afs.WEIGHTS[0] * cov
                   + afs.WEIGHTS[1] * col
                   + afs.WEIGHTS[2] * struct)
    assert got == pytest.approx(artfid, abs=ROUNDING_SLACK), (
        f"{name}: weights {afs.WEIGHTS} give {got:.2f}, artifact published "
        f"{artfid}. These weights were RECOVERED from that table by least "
        f"squares, not chosen — retuning them needs a new validation pass, "
        f"not a slack bump.")


def test_published_weights_are_the_least_squares_solution():
    # The stronger claim: 0.40/0.25/0.35 is not merely consistent with the
    # table, it is what the table solves to. Normal equations, no numpy.linalg
    # dependency beyond lstsq itself.
    A = np.array([[c, k, s] for _, c, k, s, _ in PUBLISHED])
    y = np.array([a / 100.0 for *_, a in PUBLISHED])
    solved, *_ = np.linalg.lstsq(A, y, rcond=None)
    assert solved == pytest.approx(np.array(afs.WEIGHTS), abs=0.005)


# ------------------------------------------------------------- artwork side

def test_art_ink_field_rasterises_to_the_requested_physical_width(tmp_path):
    # stage1_prep's sizing rule: physical width is the width of the art's
    # FOREGROUND bbox, not of the file. So padding must not change the raster.
    a = np.zeros((200, 200, 4), np.uint8)
    a[80:120, 60:140] = (0, 0, 0, 255)          # 80 px wide ink, lots of pad
    p = tmp_path / "pad.png"
    write_rgba(p, a)

    out = afs.art_ink_field(p, width_mm=20.0)
    assert out.shape[1] == int(round(20.0 * afs.RES))
    # 80x40 ink bbox, so the height follows the ink's aspect, not the file's.
    assert out.shape[0] == pytest.approx(out.shape[1] / 2, abs=1)


def test_art_ink_field_is_continuous_not_boolean(tmp_path):
    # The deliberate difference from the sibling's boolean mask: INTER_AREA
    # downsampling leaves real edge fractions, and SSIM needs that soft edge
    # or it reads manufactured staircase structure.
    # A DISC, not a square: cropping to the ink bbox is the last thing
    # `art_ink_field` does, so a square's bbox is solid ink edge to edge and
    # has no boundary left inside the raster to be partial about.
    a = np.full((400, 400, 4), (255, 255, 255, 255), np.uint8)
    a[disc(150, size=400)] = (0, 0, 0, 255)
    p = tmp_path / "disc.png"
    write_rgba(p, a)

    out = afs.art_ink_field(p, width_mm=7.3)      # deliberately non-integral
    assert ((out > 0.02) & (out < 0.98)).any(), "no partial-coverage pixels"
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_art_ink_field_reads_alpha_when_the_file_carries_one(tmp_path):
    # White ink on transparent: the darkness branch would find NO ink at all,
    # so this pins that alpha wins when alpha is present.
    a = np.zeros((100, 100, 4), np.uint8)
    a[30:70, 30:70] = (255, 255, 255, 255)       # white, opaque
    p = tmp_path / "alpha.png"
    write_rgba(p, a)

    out = afs.art_ink_field(p, width_mm=10.0)
    assert out.mean() > 0.9, "alpha ink read as empty"


def test_art_ink_field_reads_darkness_when_the_file_is_opaque(tmp_path):
    a = np.full((100, 100, 4), (255, 255, 255, 255), np.uint8)
    a[40:60, 20:80] = (10, 10, 10, 255)
    p = tmp_path / "opaque.png"
    write_rgba(p, a)

    out = afs.art_ink_field(p, width_mm=12.0)
    assert out.mean() > 0.9


# ---------------------------------------------------------------- refusals

def test_ink_is_ambiguous_fires_on_knocked_out_lettering(tmp_path):
    # A dark panel with light shapes knocked out of it — the case that charged
    # the engine for a hole it was right to leave, and drove a wrong
    # attribution into a published doc on 2026-08-17.
    #
    # ALPHA-KEYED deliberately, because that is the branch with the trap. On
    # opaque art the darkness rule excludes the light lettering and the mask
    # is right; it is the alpha rule — every opaque pixel is ink — that swallows
    # panel and knockout alike. Building this fixture opaque makes it pass for
    # the wrong reason and tests nothing.
    a = np.zeros((200, 200, 4), np.uint8)
    a[20:180, 20:180] = (20, 20, 20, 255)        # opaque dark panel
    a[60:140, 40:160] = (245, 245, 245, 255)     # knocked-out light lettering
    p = tmp_path / "knockout.png"
    write_rgba(p, a)

    assert afs.ink_is_ambiguous(p) is True


def test_ink_is_ambiguous_stays_quiet_on_ordinary_spot_colour_art(tmp_path):
    # One tonal population of ink on a light ground: the mask knows exactly
    # what the ink is, and refusing here would hide every flat logo we can
    # actually score.
    a = np.full((200, 200, 4), (255, 255, 255, 255), np.uint8)
    a[60:140, 40:160] = (30, 40, 180, 255)
    p = tmp_path / "flat.png"
    write_rgba(p, a)

    assert afs.ink_is_ambiguous(p) is False


def test_ink_is_ambiguous_stays_quiet_on_ordinary_alpha_keyed_art(tmp_path):
    # The negative that matters on the trapped branch. Every opaque pixel is
    # ink here too — but it is ONE tonal population, so there is no knockout to
    # be confused about. A refusal rule that fired on this would refuse
    # `logo_alpha.png`, which the validation artifact scored second.
    a = np.zeros((200, 200, 4), np.uint8)
    a[40:160, 30:170] = (35, 45, 120, 255)       # one dark ink, alpha-keyed
    p = tmp_path / "alpha_flat.png"
    write_rgba(p, a)

    assert afs.ink_is_ambiguous(p) is False


def test_ink_saturation_refuses_a_mask_that_claims_the_whole_frame(tmp_path):
    """The defect found the day after this instrument shipped.

    A design on a DARK backdrop: the opaque-art rule (mean RGB < 240) calls the
    backdrop ink too, so the mask claims the entire frame. Coverage is then an
    IoU against all-ones — "what fraction of the canvas did you sew" — and it
    rewards the engine for sewing a background it was right to remove. On
    `summit_badge` that was worth 21 points of coverage in the wrong direction.
    """
    a = np.full((300, 300, 4), (60, 56, 52, 255), np.uint8)   # dark backdrop
    a[100:200, 100:200] = (200, 120, 40, 255)                 # the actual mark
    p = tmp_path / "on_dark.png"
    write_rgba(p, a)

    assert afs.ink_saturation(p) == pytest.approx(1.0, abs=0.01)
    assert afs.ink_saturation(p) > afs.INK_SATURATION_MAX


def test_ink_saturation_is_low_for_a_mark_on_a_light_ground(tmp_path):
    a = np.full((300, 300, 4), (255, 255, 255, 255), np.uint8)
    a[120:180, 120:180] = (20, 20, 20, 255)
    p = tmp_path / "on_light.png"
    write_rgba(p, a)

    sat = afs.ink_saturation(p)
    assert sat == pytest.approx(0.04, abs=0.01)
    assert sat < afs.INK_SATURATION_MAX


def test_ink_saturation_measures_the_frame_not_the_crop(tmp_path):
    """`art_ink_field` crops to the ink bbox, and the crop is exactly what
    hides this failure: a mask claiming the whole frame crops to the whole
    frame and then looks like an ordinary solid design. So saturation must be
    read BEFORE the crop — a small mark on a light ground must stay low even
    though its own bbox is 100% ink."""
    a = np.full((400, 400, 4), (255, 255, 255, 255), np.uint8)
    a[190:210, 190:210] = (0, 0, 0, 255)          # 20x20 solid mark
    p = tmp_path / "small.png"
    write_rgba(p, a)

    # Its cropped bbox IS entirely ink...
    assert afs.art_ink_field(p, width_mm=5.0).mean() > 0.95
    # ...but the frame is not, and that is the number the refusal reads.
    assert afs.ink_saturation(p) < 0.01


def test_ink_saturation_cut_sits_between_the_observed_populations():
    # Measured over the tracked set 2026-08-27: legitimate fixtures span
    # 4.7%-62.9%, `summit_badge` saturates at 100.0%. Wide room on both sides,
    # not a cut fitted to the data.
    assert 0.63 < afs.INK_SATURATION_MAX < 1.0


def test_mismatch_cut_sits_between_the_observed_populations():
    # The artifact's one subject-mismatch row measured 5.1x and every scored
    # row sat far below the cut. Pin that the cut still separates them, so a
    # future tweak cannot quietly start refusing real results.
    assert 1.0 < afs.MISMATCH_MAX < 5.1


# ----------------------------------------------------------- registration

def test_register_recovers_a_known_shift():
    # A disc, and the same disc moved 2.0 mm right and 1.2 mm down. The search
    # steps at SHIFT_STEP_MM (0.4), so both are exactly representable.
    d = disc(30, size=140)
    ours = field(d)
    dx_px, dy_px = int(2.0 * afs.RES), int(1.2 * afs.RES)
    shifted = np.zeros_like(d)
    shifted[dy_px:, dx_px:] = d[:d.shape[0] - dy_px, :d.shape[1] - dx_px]

    iou, _, _, dx_mm, dy_mm = afs.register(ours, field(shifted))
    # `art` is shifted +x/+y, so recovering it means moving it back.
    assert (dx_mm, dy_mm) == pytest.approx((-2.0, -1.2), abs=0.05)
    assert iou > 0.99


def test_register_scores_identical_fields_at_one():
    d = field(disc(25, size=120))
    iou, _, _, dx, dy = afs.register(d, d)
    assert iou == pytest.approx(1.0)
    assert (dx, dy) == (0.0, 0.0)


def test_register_never_rescales():
    # Translation only, like the scorecard. A disc twice the radius must NOT
    # register as a match — a rescaling registration would hide a size error
    # as an alignment success, which is the whole reason the sibling refuses
    # pairs outside its size window.
    small = field(disc(20, size=200))
    big = field(disc(40, size=200))
    iou, *_ = afs.register(small, big)
    assert iou < 0.35


# ----------------------------------------------------------------- ms_ssim

def test_ms_ssim_is_one_for_identical_fields():
    d = field(disc(30, size=150))
    assert afs.ms_ssim(d, d) == pytest.approx(1.0, abs=1e-6)


def test_ms_ssim_separates_arrangement_at_equal_area():
    # The reason `structure` is a component at all: two fields can carry the
    # same amount of ink and still not look alike. One disc vs. the same ink
    # split into scattered specks — same pixel budget, different picture.
    rng = np.random.default_rng(20260827)        # seeded: this suite is deterministic
    d = disc(24, size=160)
    n = int(d.sum())

    speckle = np.zeros(d.shape, bool)
    flat = rng.permutation(speckle.size)[:n]
    speckle.flat[flat] = True

    assert speckle.sum() == d.sum()
    assert afs.ms_ssim(field(d), field(speckle)) < afs.ms_ssim(field(d), field(d))


def test_ms_ssim_truncates_a_short_pyramid_rather_than_padding():
    # A field smaller than one SSIM window has no scale to measure; padding it
    # would invent structure where the pyramid ran out. Returning 0.0 is the
    # refusal, and it must not raise.
    tiny = np.ones((3, 3), np.float64)
    assert afs.ms_ssim(tiny, tiny) == 0.0

    # And a field that fits exactly one scale still scores, on that one scale.
    one = field(disc(3, size=afs.SSIM_WIN + 2))
    assert afs.ms_ssim(one, one) == pytest.approx(1.0, abs=1e-6)


# --------------------------------------------------------------- composite

def test_composite_is_bounded_by_its_components():
    # A convex combination of three 0..1 numbers cannot leave 0..100, so any
    # ARTFID outside that range is an arithmetic bug and not a bad design.
    for cov, col, st in [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (1.0, 0.0, 0.5)]:
        v = 100.0 * (afs.WEIGHTS[0] * cov + afs.WEIGHTS[1] * col
                     + afs.WEIGHTS[2] * st)
        assert 0.0 <= v <= 100.0


# ------------------------------------------------------------------ colour

def _tiny_chart():
    """Three widely separated Lab spools: near-black, mid red, near-white."""
    return np.array([[10.0, 0.0, 0.0],
                     [50.0, 60.0, 40.0],
                     [95.0, 0.0, 0.0]])


def test_excess_is_zero_when_we_sewed_the_best_spool_available():
    chart = _tiny_chart()
    # A region of near-black pixels, assigned the near-black spool.
    lab_px = np.tile(np.array([[11.0, 0.5, -0.5]]), (40, 1))
    assert afs.region_excess_over_best(lab_px, 0, chart) == pytest.approx(0.0)


def test_excess_charges_the_gap_to_the_better_spool_we_passed_over():
    chart = _tiny_chart()
    # The same near-black region, sewn in near-WHITE when near-black was there.
    lab_px = np.tile(np.array([[11.0, 0.5, -0.5]]), (40, 1))
    assert afs.region_excess_over_best(lab_px, 2, chart) > 5.0


def test_excess_is_never_negative():
    chart = _tiny_chart()
    rng = np.random.default_rng(20260827)
    for assigned in range(len(chart)):
        lab_px = np.column_stack([rng.uniform(0, 100, 64),
                                  rng.uniform(-60, 60, 64),
                                  rng.uniform(-60, 60, 64)])
        assert afs.region_excess_over_best(lab_px, assigned, chart) >= 0.0


def test_a_bimodal_region_is_charged_for_the_half_its_thread_cannot_serve():
    """The tonal-compression signal, and the reason the floor is per-PIXEL.

    Half near-black, half near-white, and only ONE thread to sew it with.
    Whichever spool is assigned, half the pixels had a demonstrably better
    spool sitting on the chart — so the region must be charged. This is what
    compressing a smooth ramp into a handful of cones does, and it is exactly
    what the component exists to see.
    """
    chart = _tiny_chart()
    lab_px = np.vstack([np.tile(np.array([[10.0, 0.0, 0.0]]), (32, 1)),
                        np.tile(np.array([[95.0, 0.0, 0.0]]), (32, 1))])
    for assigned in (0, 2):
        assert afs.region_excess_over_best(lab_px, assigned, chart) > 20.0


def test_the_subtraction_must_happen_before_the_median_not_after():
    """The exact ordering bug, pinned on a region that separates the two.

    `median(excess_per_pixel)` vs `median(d_assigned) - min_spool
    median(d_spool)` are not the same number, and only the first can fire.
    Taking medians first asks whether a better SINGLE spool existed for the
    whole region — which is the question stage 4 already answered by snapping
    it there — so on this bimodal region it returns ~0 while half the pixels
    are visibly on the wrong thread.
    """
    chart = _tiny_chart()
    lab_px = np.vstack([np.tile(np.array([[10.0, 0.0, 0.0]]), (32, 1)),
                        np.tile(np.array([[95.0, 0.0, 0.0]]), (32, 1))])
    assigned = 0

    n, s_count = len(lab_px), len(chart)
    d = deltaE_ciede2000(
        np.repeat(lab_px[:, None, :], s_count, axis=1).reshape(-1, 3),
        np.tile(chart, (n, 1)),
    ).reshape(n, s_count)

    medians_first = max(0.0, np.median(d, axis=0)[assigned]
                        - np.median(d, axis=0).min())
    subtract_first = afs.region_excess_over_best(lab_px, assigned, chart)

    assert medians_first < 1.0, "the dead ordering should be ~0 here"
    assert subtract_first > 20.0, "the live ordering must fire here"


def test_the_floor_must_search_the_whole_chart_or_the_component_is_dead():
    """The bug this instrument was rebuilt with twice on 2026-08-27, pinned.

    Reading "best AVAILABLE spool" as "best spool this design already sews"
    makes the excess identically zero — stage 4 snaps every region to its
    nearest such spool, so the assigned thread IS the floor. That produced
    colour 1.000 on all fourteen fixtures while carrying a quarter of the
    composite's weight.

    Reproduced deliberately: hand the function a one-spool "chart" (a design
    that loaded one cone) and the excess must be zero however wrong that spool
    is. Against the real chart it must be able to fire.
    """
    chart = _tiny_chart()
    lab_px = np.tile(np.array([[11.0, 0.5, -0.5]]), (40, 1))

    narrow = chart[[2]]     # only the near-WHITE spool "available"
    assert afs.region_excess_over_best(lab_px, 0, narrow) == pytest.approx(0.0), (
        "a floor restricted to the spools already sewn is the dead read")

    assert afs.region_excess_over_best(lab_px, 2, chart) > 5.0, (
        "against the whole chart the excess must fire — if this goes quiet "
        "the component is dead again")


def test_floor_subsample_is_deterministic():
    # No seed is carried anywhere in this instrument; a metric that moves
    # between two runs of one input cannot be a baseline.
    chart = _tiny_chart()
    rng = np.random.default_rng(7)
    big = np.column_stack([rng.uniform(0, 100, afs._FLOOR_SAMPLE_PX * 4),
                           rng.uniform(-50, 50, afs._FLOOR_SAMPLE_PX * 4),
                           rng.uniform(-50, 50, afs._FLOOR_SAMPLE_PX * 4)])
    a = afs.region_excess_over_best(big, 1, chart)
    b = afs.region_excess_over_best(big, 1, chart)
    assert a == b


def test_colour_scale_is_the_shipped_clearly_different_threshold():
    # Stated choice, pinned so it cannot drift silently away from the
    # instrument it borrowed its meaning from.
    from digitizer_core.preflight import DELTA_E_CLEARLY_DIFFERENT

    assert afs.COLOUR_SCALE_DE == DELTA_E_CLEARLY_DIFFERENT
