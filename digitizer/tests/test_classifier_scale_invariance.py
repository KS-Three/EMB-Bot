"""Stage 0 must give one answer per artwork, whatever resolution it arrives at.

**These tests are EXPECTED TO FAIL.** They pin a known, measured defect rather
than a fix. Design and evidence:
`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`
and `docs/classifier-misroutes-real-logos-2026-08-15.md`.

The defect: `_gradient_smoothness` and `_unique_color_mass` are computed on the
raw file with pixel-absolute constants (`GRAD_VAR_WIN = 5`,
`CANNY_DILATE_PX = 3`). At low resolution a 1-px anti-aliased edge is entirely
swallowed by the 3-px dilation and reads as zero variance; at high resolution the
same transition survives inside the window and reads as a tonal ramp. So the lane
a design is routed down depends on how many pixels it was saved at.

Measured consequences:

* `photo/enthusiast_logo.png` — this repo's own primary real-art benchmark, and
  the fixture `GRAD_VAR_GRADIENT_MIN`'s calibration comment cites as reading
  "<0.0006" — is `flat` at its native 1400x316 and `gradient` at 500 px under
  every resampling filter tried, including NEAREST, which interpolates nothing.
* On real customer artwork, 10 of 15 designs classify `gradient` at confidence
  1.00, including a solid black script wordmark. Ground truth is that 1 of the 7
  artworks is genuinely tonal.

Why `xfail(strict=True)`: when the defect is fixed these tests will XPASS, which
strict mode reports as a failure. That is deliberate — it forces whoever fixes it
to delete the marker, so the property converts from "known bug" to "pinned
invariant" instead of silently passing and being forgotten. Their turning green
is the acceptance criterion named in the spec's §2.

Scope note: these assert INVARIANCE only, never a particular class. Which class
is correct needs a threshold, and the spec records why one cannot yet be sited —
six flat real artworks and one gradient cannot calibrate a boundary.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from digitizer_core import stage0_classify
from digitizer_core.config import PipelineConfig

from .conftest import TESTDATA

# Downscale only. Upscaling would invent detail that was never in the file, and
# any flip could fairly be blamed on the interpolator rather than the classifier
# — so every width here stays below the NARROWEST fixture below (`logo_alpha`,
# `logo_whitebg` and `ribbon_curve` are 800px wide). `_classify_at` asserts this
# rather than trusting the comment: an upscale would make these tests fail for a
# reason that is about the test, not the classifier, which is exactly the trap
# a first draft of this file fell into.
WIDTHS = (250, 400, 640)

# One entry per fixture whose native classification is unambiguous, spanning both
# sides of the gate so a degenerate "always answer gradient" implementation would
# not pass. Native class is asserted separately in `test_native_classes_are_the
# _baseline_these_sweeps_depart_from` so that a change THERE is not silently
# absorbed into an xfail.
FIXTURES = {
    "logo_alpha.png": "flat",
    "logo_whitebg.png": "flat",
    "ribbon_curve.png": "flat",
    "photo/enthusiast_logo.png": "flat",
    "photo/drone_render.png": "gradient",
    "photo/summit_badge.png": "gradient",
}

# The defect is real but NOT universal, so it is declared per fixture rather than
# with one blanket marker. Measured 2026-08-15 on the sweep widths above; a first
# draft marked every case xfail and five of them XPASSed, which is precisely the
# thing strict mode exists to catch. Recording the exact set means that if a
# fixture joins or leaves it, the suite says so.
#
# `photo/summit_badge.png` is the one fixture stable on both counts — it is a
# 900x900 badge whose gradient reading (0.458) sits far enough above the 0.0015
# threshold that no amount of downscaling in this range crosses it. That it is
# stable for a reason unrelated to correctness is itself worth knowing.
FLIPS_ACROSS_SWEEP = {
    "photo/drone_render.png",       # 250px=photo_subject, then gradient
    "photo/enthusiast_logo.png",    # 250/400=photo_scene, 640=gradient
}
DEPARTS_FROM_NATIVE = {
    "logo_alpha.png",               # native flat, 250px=gradient
    "logo_whitebg.png",             # native flat, 250px=gradient
    "ribbon_curve.png",             # native flat, downscaled=gradient
    "photo/drone_render.png",       # native gradient, 250px=photo_subject
    "photo/enthusiast_logo.png",    # native flat, every width=not flat
}

KNOWN_DEFECT = (
    "known defect: pixel-absolute signal windows make the class "
    "resolution-dependent. See docs/superpowers/specs/"
    "2026-08-15-stage0-flat-gradient-recalibration-design.md"
)


def _params(broken: set[str]):
    """One param per fixture, xfail(strict) only on the ones measured broken."""
    return [
        pytest.param(
            rel,
            marks=pytest.mark.xfail(strict=True, reason=KNOWN_DEFECT),
        )
        if rel in broken
        else pytest.param(rel)
        for rel in sorted(FIXTURES)
    ]


def _classify_at(path: Path, width: int, tmp: Path) -> str:
    im = Image.open(path)
    conv = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    assert width < conv.width, f"{path.name} is only {conv.width}px — would upscale"
    height = max(1, round(conv.height / conv.width * width))
    out = tmp / f"{path.stem}_{width}.png"
    conv.resize((width, height), Image.LANCZOS).save(out)
    return stage0_classify.classify(str(out), PipelineConfig()).class_


def test_native_classes_are_the_baseline_these_sweeps_depart_from():
    """Not xfail — this one passes today, and must keep passing.

    The thresholds are correct ON THE COMMITTED FIXTURES AT NATIVE RESOLUTION;
    that is what they were calibrated against. Pinning it here means the sweep
    failures below can only ever be about scale, and a future recalibration that
    breaks the native answers gets caught by this test rather than hiding inside
    an expected failure.
    """
    for rel, expected in FIXTURES.items():
        got = stage0_classify.classify(str(TESTDATA / rel), PipelineConfig()).class_
        assert got == expected, f"{rel}: native class {got}, expected {expected}"


@pytest.mark.parametrize("rel", _params(FLIPS_ACROSS_SWEEP))
def test_one_artwork_classifies_the_same_at_every_resolution(rel, tmp_path):
    seen = {w: _classify_at(TESTDATA / rel, w, tmp_path) for w in WIDTHS}
    assert len(set(seen.values())) == 1, (
        f"{rel} classifies differently by resolution: "
        + ", ".join(f"{w}px={c}" for w, c in seen.items())
    )


@pytest.mark.parametrize("rel", _params(DEPARTS_FROM_NATIVE))
def test_downscaling_does_not_change_an_artwork_class(rel, tmp_path):
    """Stricter than invariance across the sweep, and the one that matters to a
    user: a customer who exports the same logo smaller must get the same lane.
    A sweep could in principle be self-consistent yet wrong at every size, so
    this anchors it to the native answer."""
    native = stage0_classify.classify(str(TESTDATA / rel), PipelineConfig()).class_
    for w in WIDTHS:
        got = _classify_at(TESTDATA / rel, w, tmp_path)
        assert got == native, f"{rel} at {w}px is {got}, native is {native}"
