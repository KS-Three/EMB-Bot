"""The enclosed-background restore fix (2026-08-04).

`stage1_prep.py`'s no-alpha branch used to fold `enclosed` (background-
colored pixels not reachable from the true image border — e.g. white icon
linework inside a colored logo) into `bg`, so those pixels never became a
Region and could never be reviewed/restored even though the
BACKGROUND_ENCLOSED warning's own text claims "toggle them on in review if
they should sew." This slice: `enclosed` pixels join `fg` instead (stage 1,
same warning/count), `stage4_vectorize.tag_enclosed_background` tags the
resulting Region(s), and `region.meta["stitched"]` resolves to False by
default for a tagged region and is excluded from the stitch plan at
`plan_stitches`.

See docs/superpowers/plans/2026-08-04-enclosed-background-restore-design.md
(design) and docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-
and-enclosed-white-defects.md ("Defect 2", original diagnosis).

Python-side slice only: no `shape_overrides["stitched"]` override key yet
(that needs the service contract — `digitizer_service/app.py` — out of
scope here), no Studio UI. `regions.py::apply_shape_edits`/`app.py` tests
are therefore not part of this file.
"""
from __future__ import annotations

import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.stage1_prep import prep
from digitizer_core.warnings_codes import BACKGROUND_ENCLOSED

from .conftest import TESTDATA, cfg, codes

REPRO = TESTDATA / "photo" / "repro_gradient_white_icon.png"

# The background-existence guard (2026-08-11, bg_border_agreement_min) now
# correctly refuses to flood this full-bleed fixture at all — its border ring
# only agrees 35.5% with its own modal color, so at defaults there IS no
# background and therefore nothing enclosed (that end-to-end truth is pinned
# by test_stages.py::test_full_bleed_art_keeps_all_of_itself). These tests
# pin a DIFFERENT, orthogonal mechanism — enclosed bg-colored pixels becoming
# real, restorable Regions — and the repro fixture only reaches that
# machinery with the existence guards off, which is exactly how the pipeline
# behaved when this file's diagnosis was made.
def repro_cfg(**kw):
    kw.setdefault("bg_border_agreement_min", 0.0)
    kw.setdefault("bg_border_rival_min", 0.0)
    return cfg(**kw)


# --- stage 1: enclosed pixels join fg; byte-identical when there are none --


@pytest.mark.parametrize(
    "name",
    ["ribbon_curve.png", "bg_uncertain.png", "photo/gradient_ramp_linear.png"],
)
def test_no_enclosed_region_is_the_common_case(name):
    """`Prep.enclosed_mask` is None whenever the design has no bg-colored
    area disconnected from the true canvas border — the common case, and
    the one case this fix has a hard requirement to leave byte-identical.
    `bg_mask` reduces to exactly `border_bg` here with nothing folded out of
    it either, so it is untouched by this change.

    The stronger, full-pipeline claim — that STITCH OUTPUT for a design
    with no enclosed region is bit-for-bit unchanged — is what
    `tests/test_pushcomp.py`'s and `tests/test_flat_lane_byte_identical.
    py`'s `ribbon_curve.png` golden-hash entries continuously pin (both
    fixtures/entries were left untouched by this change and still pass);
    this test pins the narrower stage-1 precondition those goldens rely on.
    """
    p = prep(TESTDATA / name, cfg())
    assert p.enclosed_mask is None


def test_ring_hole_pixels_join_fg_not_bg(whitebg):
    """The ring's donut hole is bg-colored but not border-connected — it
    must show up in `Prep.enclosed_mask`, and (this is the actual bug fix)
    must NOT be part of `Prep.bg_mask` any more."""
    p = prep(TESTDATA / "logo_whitebg.png", cfg())
    assert p.enclosed_mask is not None
    assert p.enclosed_mask.any()
    # No overlap: a pixel is either background or enclosed-but-foreground,
    # never both.
    assert not (p.enclosed_mask & p.bg_mask).any()


def test_repro_fixture_enclosed_mask_is_populated():
    """The real-world repro: a gradient logo with white icon linework
    dropped as holes (docs/superpowers/plans/2026-08-03-gradient-tier-
    fragmentation-and-enclosed-white-defects.md, "Defect 2")."""
    p = prep(REPRO, repro_cfg())
    assert p.enclosed_mask is not None
    assert p.enclosed_mask.any()


# --- post-vectorization tagging --------------------------------------------


def test_only_the_enclosed_region_is_tagged_on_the_ring_hole_fixture(whitebg):
    """Positive case (the donut hole) AND the negative case in one
    assertion: exactly one of the fixture's regions is tagged — the other
    six real shapes (red circle, ring, two orange pieces, purple rectangle,
    green bar) must not be false-positived by the overlap-threshold test in
    `tag_enclosed_background`."""
    tagged = [r for r in whitebg.regions if r.meta.get("enclosed_background")]
    assert len(tagged) == 1
    assert tagged[0].thread_number == "0015"  # White — the ring's own hole colour
    untagged_threads = {
        r.thread_number for r in whitebg.regions if not r.meta.get("enclosed_background")
    }
    assert "0015" not in untagged_threads


def test_repro_fixture_icon_regions_are_tagged_and_excluded_by_default():
    result = run_stages(REPRO, repro_cfg())
    assert BACKGROUND_ENCLOSED in codes(result)
    enclosed_warning = next(w for w in result.warnings if w["code"] == BACKGROUND_ENCLOSED)

    tagged = [r for r in result.regions if r.meta.get("enclosed_background")]
    # One tagged Region per BACKGROUND_ENCLOSED connected component stage 1
    # found — the overlap test does not need to be 1:1 in general (see
    # `tag_enclosed_background`'s docstring), but on this fixture it is.
    assert len(tagged) == enclosed_warning["count"]
    assert tagged, "the repro fixture's whole point is that these regions now exist"
    for r in tagged:
        assert r.meta["stitched"] is False

    plan = plan_stitches(result, repro_cfg(garment_id="left_chest"))
    stitched_ids = {r.shape_id for _b, r in plan.iter_runs()}
    tagged_ids = {r.shape_id for r in tagged}
    assert not (stitched_ids & tagged_ids), "tagged regions must not reach the stitch plan"


def test_untagged_regions_default_to_stitched(whitebg):
    for r in whitebg.regions:
        if r.meta.get("enclosed_background"):
            assert r.meta["stitched"] is False
        else:
            assert r.meta["stitched"] is True


# --- plan_stitches is the one exclusion point -------------------------------


def test_plan_stitches_excludes_unstitched_regions_but_run_stages_keeps_them():
    """`PipelineResult.regions` (from `run_stages`) keeps every region,
    tagged ones included — a review screen needs the full list to show a
    restorable shape. `plan_stitches` is the one seam that actually removes
    an unstitched region from what reaches stage 5 (resolve_overlaps)."""
    result = run_stages(REPRO, repro_cfg())
    tagged_ids = {r.shape_id for r in result.regions if r.meta.get("enclosed_background")}
    assert tagged_ids
    assert tagged_ids <= {r.shape_id for r in result.regions}  # still in .regions

    plan = plan_stitches(result, repro_cfg(garment_id="left_chest"))
    stitched_ids = {r.shape_id for _b, r in plan.iter_runs()}
    assert not (tagged_ids & stitched_ids)


def test_fully_opaque_alpha_behaves_like_its_rgb_twin():
    """Studio's DigitizePanel re-encodes uploads through a canvas, which
    manufactures a fully-opaque alpha channel onto RGB art. Measured live
    2026-08-04: routed through stage 1's alpha branch, that killed
    background detection outright (bg detected False — the white canvas
    itself would sew) and silently disabled BACKGROUND_ENCLOSED for every
    panel upload. A fully-opaque alpha carries no background information;
    stage 1 now discards it and the image takes the color-heuristic branch
    exactly like its RGB twin."""
    import cv2

    from digitizer_core.pipeline import run_stages

    bgr = cv2.imread(str(REPRO), cv2.IMREAD_COLOR)
    ok, buf = cv2.imencode(".png", cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA))
    assert ok

    opaque = run_stages(bytes(buf), repro_cfg(target_width_mm=90.0))
    plain = run_stages(REPRO, repro_cfg(target_width_mm=90.0))

    assert opaque.background.detected is True
    assert BACKGROUND_ENCLOSED in codes(opaque)
    tag = lambda r: sorted(
        x.shape_id for x in r.regions if x.meta.get("enclosed_background")
    )
    assert tag(opaque) == tag(plain) and tag(plain)
    assert sorted(opaque.shape_ids) == sorted(plain.shape_ids)
