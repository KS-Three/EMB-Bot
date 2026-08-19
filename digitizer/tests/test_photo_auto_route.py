"""Spec decision 3 (2026-08-18): the automatic tier map for photo classes.
photo_subject -> streamline (+ detail layer with faces); photo_scene ->
tatami+split; explicit caller choice always wins."""
import numpy as np
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import (
    BackgroundInfo,
    PipelineResult,
    auto_photo_tier,
    plan_stitches,
    run_stages,
)
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.threads import CHART
from digitizer_core.warnings_codes import PHOTO_AUTO_TIER


def test_photo_subject_defaults_to_streamline():
    assert auto_photo_tier(PipelineConfig(), "photo_subject", faces_present=False) == "streamline"


def test_photo_scene_defaults_to_tatami():
    # None = leave fill_technique alone; scene tone comes from split regions.
    assert auto_photo_tier(PipelineConfig(), "photo_scene", faces_present=False) is None


def test_explicit_caller_choice_wins():
    cfg = PipelineConfig(fill_technique="meander_tonal")
    assert auto_photo_tier(cfg, "photo_subject", faces_present=False) is None


def test_gradient_and_flat_untouched():
    assert auto_photo_tier(PipelineConfig(), "gradient", faces_present=False) is None
    assert auto_photo_tier(PipelineConfig(), "flat", faces_present=False) is None


# --- Wiring: run_stages' source_pixels gate + the PHOTO_AUTO_TIER warning ---
#
# The four tests above pin the pure decision function only; none of them
# call `run_stages`. `auto_photo_tier`'s return value is inert until
# something reads it — these pin the one reader (the source_pixels gate
# block pipeline.py:456-490 used to comment "automatic photo routing is a
# later slice" — this is that slice), measured from what a real caller
# actually gets back: `PipelineResult.source_pixels` and `.warnings`, never
# a re-read of `auto_photo_tier`'s own return value.

def _two_square_image() -> np.ndarray:
    """Same fixture shape as test_photo_sequencing.py's own helper: two flat
    squares on a transparent field. `forced_class` decides which lane runs,
    not real photo content, so this is enough to exercise the gate without
    a real photo fixture."""
    img = np.zeros((300, 300, 4), np.uint8)
    img[20:200, 20:200] = (245, 240, 235, 255)
    img[230:290, 230:290] = (30, 30, 35, 255)
    return img


def _warning(result, code: str) -> dict | None:
    return next((w for w in result.warnings if w["code"] == code), None)


def test_default_photo_subject_gets_source_pixels_and_the_warning():
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject")
    result = run_stages(_two_square_image(), cfg)
    assert result.source_pixels is not None
    w = _warning(result, PHOTO_AUTO_TIER)
    assert w is not None, "auto-route decided streamline but never said so"
    assert w["tier"] == "streamline"
    # photo_prep defaults False (v1): no face detector ran, so there are no
    # faces to report and no auto-on detail layer either.
    assert w["detail_layer"] is False


def test_explicit_fill_technique_suppresses_the_warning_in_the_real_pipeline():
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                         fill_technique="meander_tonal")
    result = run_stages(_two_square_image(), cfg)
    assert _warning(result, PHOTO_AUTO_TIER) is None, (
        "an explicit caller fill_technique must win inside run_stages, not "
        "just in auto_photo_tier's own return value")


def test_explicit_detail_layer_suppresses_the_warning_in_the_real_pipeline():
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                         detail_layer=True)
    result = run_stages(_two_square_image(), cfg)
    assert _warning(result, PHOTO_AUTO_TIER) is None


def test_photo_scene_gets_no_warning_and_no_source_pixels_by_default():
    # Spec decision 3: photo_scene stays tatami in v1 (tone arrives via
    # Task 2's split_tonal_regions, not a source-reading fill tier) — the
    # brief's own "leave scenes off want_tonal for v1" instruction, pinned
    # here from the PipelineResult a caller actually sees, not just from
    # auto_photo_tier returning None.
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_scene")
    result = run_stages(_two_square_image(), cfg)
    assert _warning(result, PHOTO_AUTO_TIER) is None
    assert result.source_pixels is None


def test_flat_and_gradient_get_no_auto_tier_warning():
    for class_ in ("flat", "gradient"):
        cfg = PipelineConfig(target_width_mm=80.0, forced_class=class_)
        result = run_stages(_two_square_image(), cfg)
        assert _warning(result, PHOTO_AUTO_TIER) is None, class_


def _astronaut(size: int = 256):
    """The rights-safe real-face fixture test_face_priors.py's own module
    docstring documents: `skimage.data.astronaut()`, public-domain, shipped
    inside the scikit-image wheel this venv already pins — a real face
    YuNet actually detects, above its measured 160px detection floor.
    Reimplemented locally (4 lines) rather than importing a private helper
    across test modules, matching every other fixture helper in this suite."""
    import cv2
    from skimage import data
    return cv2.resize(data.astronaut(), (size, size), interpolation=cv2.INTER_AREA)


def test_faces_present_turns_the_detail_layer_on_in_the_real_pipeline():
    # The one part of the wiring the pure-function tests structurally cannot
    # reach: `auto_photo_tier` accepts `faces_present` but never reads it
    # (the tier name does not change) — it is `run_stages` that turns the
    # detail layer on when the auto-route fires AND stage 1.5 actually found
    # a face. Proven on a real detector run, not a stubbed face list.
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                         photo_prep=True)
    result = run_stages(_astronaut(), cfg)
    w = _warning(result, PHOTO_AUTO_TIER)
    assert w is not None
    assert w["tier"] == "streamline"
    assert w["detail_layer"] is True, (
        "a real detected face must turn the auto-route's detail layer on")


# --- Fix round 1: the decision must actually SEW, not just warn -------------
#
# Everything above proves `PipelineResult.source_pixels`/`.warnings` — the
# decision layer. None of it calls `plan_stitches`, so none of it could have
# caught (and did not catch) that `stage7_sequence.sequence()` read `cfg.
# fill_technique` straight off the unmutated `cfg`, ignoring the auto-route
# entirely: a photo_subject job with no explicit `fill_technique` warned
# "streamline" and then sewed plain tatami. These pin the fix — measured
# from the EMITTED plan (`StitchPlan.blocks`), never from a re-read of the
# warning or of `auto_photo_tier`'s own return value.

def _big_region(poly: Polygon, thread_index: int = 0) -> Region:
    # tier="fill" sidesteps satin/run-rescue auto-classification the same
    # way test_shade_thread_emission.py's and this file's own earlier
    # streamline test's region helpers do — this region exists to test
    # tonal-tier dispatch, not the satin/run ladder.
    return Region(shape_id="Sphoto", polygon=poly, thread_index=thread_index,
                 thread_number=CHART[thread_index].number, area_mm2=poly.area,
                 meta={"layer": 0, "tier": "fill"})


def _ramp_source_pixels(w_px: int = 320, h_px: int = 240,
                        px_per_mm: float = 4.0) -> SourcePixels:
    """The same light-to-dark horizontal ramp construction test_stage6_
    streamline.py's own `_full_ramp` uses — real tonal range for both the
    direction field (concern 1) and shade decomposition (concern 4)."""
    ramp = np.tile(np.linspace(250, 5, w_px), (h_px, 1)).astype(np.uint8)
    rgb = np.dstack([ramp] * 3)
    return SourcePixels(rgb=rgb, px_per_mm=px_per_mm,
                        origin_px=(w_px / 2.0, h_px / 2.0))


def _photo_subject_result(poly: Polygon, source_pixels: SourcePixels) -> PipelineResult:
    """A hand-built `PipelineResult` — one region over a controlled ramp,
    `design_class="photo_subject"` — so `plan_stitches` (the function under
    test) runs for real while the region topology stays fully deterministic,
    unlike a `digitize()` call through real segmentation. Mirrors how
    `test_photo_sequencing.py`'s own `plan_for` helper and `test_shade_
    thread_emission.py`'s chain-guard test build inputs by hand."""
    region = _big_region(poly)
    return PipelineResult(
        regions=[region],
        palette=[{"brand": CHART.label, "brand_id": CHART.id,
                  "number": region.thread_number, "name": "x", "rgb": [0, 0, 0]}],
        background=BackgroundInfo(detected=False),
        px_per_mm=source_pixels.px_per_mm,
        design_size_mm=(70.0, 50.0),
        source_pixels=source_pixels,
        design_class="photo_subject",
    )


def _geometry(plan) -> list:
    return [(b.thread_index, [(r.kind, r.jump, r.trim, r.points) for r in b.runs])
            for b in plan.blocks]


def test_default_photo_subject_plan_actually_stitches_streamline_not_tatami():
    """Concern 1 fix: `plan_stitches` must thread the auto-route's decision
    into stage7's own technique dispatch. Proven by structural equality
    against an EXPLICIT `fill_technique="streamline", streamline_mode=
    "layered"` plan on identical region/source geometry — that pair, not
    bare `fill_technique="streamline"` alone, is what the auto-route
    actually resolves to (concern 4 forces layered too; a bare
    `fill_technique="streamline"` control would default to MONO and differ
    from the auto-route for an unrelated reason, which is exactly the bug
    this test's own first draft had — caught by this same test failing for
    the wrong reason before this fix, see the fix-round report). Fresh
    PipelineResult per call, so nothing one plan_stitches call does can leak
    into the next.

    The control is `fill_technique="meander_tonal"`, not `"tatami"`:
    `auto_photo_tier`'s own "explicit" gate reads `(cfg.fill_technique or
    "tatami").lower() != "tatami"` — "tatami" is the field's own default, so
    an EXPLICIT `fill_technique="tatami"` is indistinguishable from never
    setting it at all, and the auto-route fires for it too (this task's
    given `auto_photo_tier` implementation, unchanged; not a bug this fix
    round introduced or is in scope to change — a photo_subject job cannot
    force plain tatami by naming it explicitly, only by picking a real
    non-tatami technique or setting `detail_layer=True`). `meander_tonal`
    is unambiguous and proves the comparison above is not vacuous (i.e.
    that streamline really does produce different stitches on this ramp)."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])

    def plan_for(cfg: PipelineConfig):
        result = _photo_subject_result(poly, _ramp_source_pixels())
        return plan_stitches(result, cfg)

    plan_auto = plan_for(PipelineConfig())
    plan_explicit = plan_for(PipelineConfig(fill_technique="streamline",
                                            streamline_mode="layered"))
    plan_other_tonal = plan_for(PipelineConfig(fill_technique="meander_tonal"))

    assert _geometry(plan_auto) == _geometry(plan_explicit), (
        "a default-config photo_subject plan must actually stitch the same "
        "layered-streamline geometry an explicit caller would get, not "
        "plain tatami")
    assert _geometry(plan_auto) != _geometry(plan_other_tonal), (
        "fixture sanity: streamline and an explicit different technique "
        "must differ on this ramp, or the equality assertion above would "
        "be meaningless")


def test_default_photo_subject_plan_uses_layered_streamline_multi_thread():
    """Concern 4 fix: the auto-route must select streamline's LAYERED mode,
    not mono — mono sews every shade of a photo region in one thread,
    defeating the dark->light tone chain Task 1's shade_thread_index
    emission and this task's own streamline-layer shade-stamping fix exist
    to carry. Measured the same way test_shade_thread_emission.py's own
    job-level test measures the sibling blend-tier defect: distinct
    `thread_index` values across the EMITTED plan's blocks, on a
    default-config plan — no explicit fill_technique OR streamline_mode
    anywhere."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    result = _photo_subject_result(poly, _ramp_source_pixels())

    plan = plan_stitches(result, PipelineConfig())

    distinct = {b.thread_index for b in plan.blocks}
    assert len(distinct) >= 3, (
        f"default-config photo_subject plan sewed {len(distinct)} thread(s) "
        "— the auto-route did not select streamline's layered mode")
