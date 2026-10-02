import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, run_stages


# SESSION-scoped, and shared by every module that needs a client. It must not
# be per-module, and that is not a style preference -- a per-module client
# breaks the modules that run after it.
#
# `digitizer_service.app` holds `registry = JobRegistry(workers=1)` as a
# MODULE-LEVEL singleton, and the app's `lifespan` calls `registry.shutdown()`
# on shutdown, which is `ThreadPoolExecutor.shutdown(wait=False,
# cancel_futures=True)` -- permanent. A module-scoped client therefore kills
# the pool for every LATER module in the same process, and a fresh TestClient
# does not revive it: only shutdown acts, startup does not rebuild the pool.
#
# Two modules used to build their own (test_service.py and
# test_jef_hoop_code.py, the latter added 2026-09-07); both now take this one.
# Under `-n auto` the collision only bites when xdist happens to put both in
# the same worker, which is why it was intermittent: green locally and on one
# main run, red on two consecutive CI runs of the same tree -- 13 failures in
# test_service.py reading `RuntimeError: cannot schedule new futures after
# shutdown` and `assert 'queued' == 'done'`.
#
# Measured 2026-09-08, single process: the two fast manual tests pass ALONE in
# 0.86s and fail in 62s when test_jef_hoop_code.py runs first.
#
# One client per session means the app starts and stops once per worker, so no
# module can take the pool away from another. Do not re-add a module-scoped
# `client` fixture; add users to this one.
#
# Imported INSIDE the fixture, not at module scope: fastapi is the optional
# `service` extra (pyproject keeps it optional so digitizer-core stays usable
# as a plain library), and conftest.py is imported for EVERY test here -- a
# module-level `from fastapi.testclient import TestClient` would fail
# collection of the whole suite on a no-extras install, not just the service
# tests. The modules that use this fixture already `pytest.importorskip`
# fastapi themselves; the guard here keeps the conftest honest on its own.
@pytest.fixture(scope="session")
def client():
    pytest.importorskip("fastapi", reason="service extra not installed")
    from fastapi.testclient import TestClient

    from digitizer_service.app import app

    with TestClient(app) as c:
        yield c


TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def draw_tiny_logo(path: Path, extra_dot: bool = False) -> Path:
    """A 240x160 white card with a black rectangle and a red disc: the
    cheapest image that digitizes to two regions (~2 s). Three modules each
    hand-built this, pixel for pixel, until 2026-09-18 — the instrument
    splits, the eye-pairs features and the eye-pairs CLI. `extra_dot` is the
    same artwork re-exported with one more mark: same NAME, different bytes,
    for the cache-key test. cv2/numpy are imported here, not at module
    scope, for the reason the `client` fixture above gives."""
    import cv2
    import numpy as np

    img = np.full((160, 240, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 40), (110, 120), (0, 0, 0), -1)
    cv2.circle(img, (170, 80), 35, (0, 0, 200), -1)
    if extra_dot:
        cv2.circle(img, (40, 140), 6, (0, 0, 0), -1)
    cv2.imwrite(str(path), img)
    return path


@pytest.fixture(scope="session")
def tiny_logo(tmp_path_factory) -> Path:
    """`draw_tiny_logo` on disk as `tiny.png`, once per session. Read-only:
    a test that needs to change it draws its own under `tmp_path`."""
    return draw_tiny_logo(tmp_path_factory.mktemp("tiny_logo") / "tiny.png")

@contextmanager
def held_on_source_line():
    """The tracing grid as it was before `cfg.work_px_per_mm` went ON
    (Kent's flip, 2026-10-01): a low-resolution source enlarged to
    `min_px_per_mm` and no further.

    For a test whose NUMBERS were read on that grid and whose subject is
    something else — a golden, a census, a threshold on a 6-7 px/mm
    synthetic. Under the working grid the fixture is a different raster and
    the pinned number is no longer the thing the test is about; the rule is
    the one `alpha_edge_extend`'s flip set ("a test whose numbers were read
    on the pre-flip engine holds OFF"). It patches the three readers of the
    grid rather than a config, so it also reaches a run whose
    `PipelineConfig` is built inside a tool. Not for a test ABOUT the grid:
    `tests/test_work_grid.py` passes `work_px_per_mm` itself.

    Two spellings. A test that digitizes for itself wears the
    `source_line_grid` fixture below. A run SHARED between tests — a
    module-scoped fixture, an `lru_cache`d digitize — wraps the run in this
    context instead, because a function-scoped patch arrives after a
    module-scoped fixture has already been built and a cache hands one
    test's raster to the next.

    A few of the tests that hold it are real costs of the flip and not just
    moved pins — `gradient_ramp_radial` sews two regions for one on the
    working grid, the face-local split four for two.
    `docs/fine-detail-work-grid-2026-09-30.md` lists them."""
    from digitizer_core import alpha_edge, preflight, stage1_prep

    def line(cfg, class_=None):
        return float(cfg.min_px_per_mm)

    patch = pytest.MonkeyPatch()
    try:
        for mod in (stage1_prep, alpha_edge, preflight):
            patch.setattr(mod, "work_grid_px_per_mm", line)
        yield
    finally:
        patch.undo()


@pytest.fixture
def source_line_grid():
    """`held_on_source_line` for the length of one test."""
    with held_on_source_line():
        yield


# The real-read OCR tests skip when the tesseract binary is absent — but
# never on CI, where the workflow apt-installs it: if that provisioning is
# ever lost in a refactor, the five OCR tests must fail loud, not go dark
# behind quiet skips (the same rule the studio-e2e job enforces for its
# specs). GitHub Actions always sets CI=true.
requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None and not os.environ.get("CI"),
    reason="needs the real tesseract binary on PATH (CI installs tesseract-ocr)")

# The fixture logo's true colors and the Isacord threads they resolve to
# (CIEDE2000). Pinned so a change in the matcher or the chart is visible.
EXPECTED_THREADS = {
    "1704": "Candy Apple",    # red circle
    "3902": "Colonial Blue",  # ring
    "1305": "Fox Fire",       # orange rectangle
    "2905": "Iris Blue",      # purple rectangle
    "5510": "Emerald",        # thin green bar
}


def cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


@pytest.fixture(scope="session")
def whitebg():
    return run_stages(TESTDATA / "logo_whitebg.png", cfg())


@pytest.fixture(scope="session")
def whitebg_pre_flip():
    """The same fixture on the engine BEFORE `cfg.keep_thin_strokes` was
    flipped ON by default (2026-09-13, Kent's ruling on
    `docs/thin-strokes-flip-2026-09-13.md`).

    ON, whitebg's ~1.2 mm² teal patch is contrasting, clears the run tier's
    floors and is KEPT as its own teal run instead of being absorbed into
    the white ground it touches; a second former absorbee (~0.42 mm²) fails
    those floors and drops instead. So the fixture gains a region, a block
    and a cone, `ABSORBED_SMALL_SHAPES` stops being emitted, and two
    neighbours' polygons shrink by the pieces they no longer swallow. That
    is the shipped engine now, pinned in `tests/test_keep_thin_strokes.py`
    and in the flat-lane golden — use the plain `whitebg` fixture for
    anything asking what the engine DOES.

    This one exists for the handful of claims that were MEASURED on the old
    polygons and are about something else entirely (stage 3's absorb
    reporting, the bare-core gate's false-alarm analysis): the posture
    `PRE_FLIP` below documents, as a fixture because three tests in two
    files need the same run."""
    return run_stages(TESTDATA / "logo_whitebg.png", cfg(keep_thin_strokes=False))


@pytest.fixture(scope="session")
def alpha():
    return run_stages(TESTDATA / "logo_alpha.png", cfg())


@pytest.fixture(scope="session")
def uncertain():
    return run_stages(TESTDATA / "bg_uncertain.png", cfg())


@pytest.fixture(scope="session")
def enthusiast_logo_93mm():
    # Not this file's usual 80mm default: test_chaining.py's two
    # corpus-benchmark tests moved here from logo_alpha.png (2026-08-06) after
    # the satin/fill classifier's flat-lane DT-tightening fix correctly
    # reclassified two of that fixture's shapes from satin to fill, which
    # incidentally eliminated the narrow gap chain_links used to bridge on
    # logo_alpha specifically -- a fixture-geometry change, not a chaining
    # regression (every synthetic-geometry chaining test elsewhere in this
    # file is unaffected). enthusiast_logo.png is this repo's own primary
    # real-art benchmark (COOKBOOK.md).
    #
    # 82mm -> 93mm, 2026-09-01, Kent's call. The width is a BENCHMARK CHOICE,
    # not a law: it was picked in the first place by sweeping widths for one
    # that sits inside the corpus band with margin, and 82mm had drifted out
    # of it. `main` went red at 903c937 (the #302 borders_last default flip)
    # on 4.16/1k against the 4.1 ceiling -- but the drift was mostly already
    # there: 82mm was chosen at a claimed 3.41/1k and measured 3.76 with the
    # flag OFF the day it broke, so the flip only added the last 0.40. See
    # PR #305 for the three fixes to borders_last that were tried and
    # rejected with measurements; re-picking the fixture is what was left,
    # and it leaves the 4.1 corpus ceiling untouched.
    #
    # Re-swept 70-100mm at 2mm, then 87-95mm at 1mm (2026-09-01, this
    # container, borders_last at its new default). 93mm is not the single
    # best number -- it is the one whose NEIGHBOURHOOD is safe, which is the
    # property 82mm turned out not to have:
    #
    #   92mm 2.82/1k   93mm 2.43/1k   94mm 3.06/1k
    #
    # so the whole +/-1mm window stays at or under 3.06 against a 4.1
    # ceiling. 93mm itself carries the strongest chaining win in the sweep
    # (trims 19->8, links 4->17) and zero bare-fabric exposure on BOTH
    # garments the acceptance tests use -- 0.0000mm on left_chest and
    # full_back alike, chaining on or off.
    #
    # That last point is why this is 93 and not 88 or 92, which score just as
    # well on trims: at both of those, full_back's chain-off exposure floor
    # is non-zero (0.4021mm and 0.2014mm), which would quietly falsify
    # test_chaining_adds_zero_bare_thread_on_every_acceptance_fixture's
    # documented claim that the floor IS zero there, while its on/off
    # equality assertion carried on passing.
    return run_stages(TESTDATA / "photo/enthusiast_logo.png", cfg(target_width_mm=93.0))


@pytest.fixture(scope="session")
def ribbon():
    # The satin-only fixture (one ~2 mm stroke curved through an S — see
    # tools/make_test_logo.py). One colour, so chaining's future-colour
    # cover is empty by construction: any link it sewed here would ride the
    # block's own already-laid thread or nothing.
    return run_stages(TESTDATA / "ribbon_curve.png", cfg())


def codes(result) -> set[str]:
    return {w["code"] for w in result.warnings}


# --- Stitch planning (build step 3) ---------------------------------------

PLAN_CFG_KW = {"garment_id": "left_chest"}   # pique knit: 0.3 mm pull comp


@pytest.fixture(scope="session")
def plan(whitebg):
    """The fixture logo planned for stitching, with its sewing geometry.

    Both halves are returned because the interesting invariants are about the
    relationship between them — a stitch is only inside or outside a hole
    relative to the geometry it was planned against, not the raw artwork.
    """
    from digitizer_core import plan_stitches
    from digitizer_core.pipeline import fabric_for
    from digitizer_core.stage5_overlap import resolve_overlaps

    c = cfg(**PLAN_CFG_KW)
    planned, warnings = resolve_overlaps(whitebg.regions, fabric_for(c), c)
    return plan_stitches(whitebg, c), planned, warnings


def segments(stitch_plan):
    """Every needle-DOWN move in the plan, as (block, run, a, b)."""
    for b, run in stitch_plan.iter_runs():
        for a, c in zip(run.points, run.points[1:]):
            yield b, run, a, c


# The colour bundle (quality review 2026-09-08 item 8): four flags Kent
# flipped ON by default as one set on 2026-09-10 (`docs/colour-bundle-
# decision-2026-09-10.md`), and a fifth later the same day --
# `robust_region_colour`, the stage-2 repair for the loss that flip's own
# test run found (PR #445 built it OFF; the PR after flipped it on his
# ruling). Each flag's own test file still prices the flag ALONE, so its
# baseline is the PRE-FLIP engine -- the five False -- and "on" is that
# baseline plus the one flag; otherwise "off" would mean "this flag off,
# the others on", which is not the engine any measurement was made on. The
# shipped engine is BUNDLE_ON (the fifth flag is the default there), and
# each file pins that once.
COLOUR_BUNDLE = ("enforce_color_cap", "resnap_mask_matches_grader",
                 "revalidate_small_shapes", "bind_resnap_all_classes")
PRE_FLIP = {name: False for name in COLOUR_BUNDLE + ("robust_region_colour",)}
# `edge_cap` joined the flipped set 2026-09-11 ("bean", Kent's ruling after
# item 14). It is a STRING, not a bool, so it cannot ride the dict
# comprehension above -- and it is in PRE_FLIP for the same reason the five
# are: a test pricing one flag alone must measure against the engine its
# measurement was made on, and every cap arm before today was made with the
# cap off.
PRE_FLIP["edge_cap"] = "none"
# `keep_thin_strokes` joined the flipped set 2026-09-13 (Kent's ruling on
# `docs/thin-strokes-flip-2026-09-13.md`), and is in PRE_FLIP for the same
# reason as the six above: ON it keeps a contrasting sub-floor region for the
# run tier instead of absorbing it, which adds regions, blocks and cones to
# real logos -- so an arm measured before today was measured without it, and
# a test pricing one OTHER flag must not silently pick it up. Measured: with
# it left ON, twelve such arms across seven files moved (the owl, Bridge Bar,
# gaulke, the screenshot, drone).
PRE_FLIP["keep_thin_strokes"] = False
# `strip_letterbox` joined the flipped set 2026-09-14, and is in PRE_FLIP for
# exactly the reason stated above: a test pricing one flag alone must measure
# against the engine its measurement was made on. Every arm in the resnap and
# thread-match files was measured on `photo/logo_gaulke_roofing.png` WITH its
# letterbox bars — 16.1 px/mm, the 247-vs-54 px footprint, the 63.6 dE00
# Silver — and cropping the bars changes the raster those numbers describe.
#
# This is NOT a way of dodging the re-point work. The distinction that
# settles it: those tests are about the COLOUR flags, and `strip_letterbox`
# is orthogonal to every one of them, so pinning it here keeps each test
# measuring the thing it is named for, on the pixels it measured. The tests
# that are genuinely ABOUT the crop (`test_letterbox`, the full-bleed guard,
# `test_enclosed_by_garment`) do not use PRE_FLIP and were re-pointed
# properly instead.
#
# Measured before choosing this: no single fixture in the corpus reproduces
# gaulke's uncropped severity on BOTH axes the resnap premise asserts.
# `photo/logo_bridge_bar.jpg` has the footprint inflation (raw 229 px vs
# grader 39, ratio 5.87 against the test's `> 3`) but not the bimodality
# (26 dark pixels against `> 50`, because it decodes at 4.0 px/mm);
# `photo/screenshot_phone_ui_golke.jpg` has the bimodality (92 dark / 102
# light at 12.75 px/mm) but not the ratio (2.20). Splitting one premise
# across two fixtures to keep a number green would have been the
# fit-to-output move this repo's doctrine warns about.
PRE_FLIP["strip_letterbox"] = False
# `satin_rail_comp` joined the flipped set 2026-09-29 (Kent's pick on the
# labelled sitting, `docs/kent-review-2026-09-28.md`), for the reason every
# entry above gives: ON, a satin-tier shape keeps its artwork polygon in
# stage 5 and takes the fabric's pull on its rails in stage 6, so every satin
# column's crosses, caps, underlay and trims move -- and an arm measured
# before that day was measured on the grown polygon. Measured at the flip:
# left ON, 29 tests across 14 files moved (`docs/kent-review-2026-09-28.md`,
# "Outcome"); none of them reads this dict, so the entry is the posture, kept
# for the next test that prices a colour flag on a satin fixture. A test that
# is ABOUT the rails is `tests/test_rail_comp.py` and names the flag itself.
PRE_FLIP["satin_rail_comp"] = False
# `snap_region_edges` joined the flipped set 2026-09-30 (Kent's flip on
# renders of his Instagram icon, drone, Bridge Bar and the repro), for the
# reason every entry above gives. ON, a gradient-lane region's edge follows
# the pixels instead of the SEEDS superpixels, which removes exactly the
# slivers and halo fragments the colour files use as their PREMISE -- the
# resnap's Silver-on-near-black shape, the drifted sliver, the repeated cone
# -- so an arm measured before that day was measured with them present.
# Measured at the flip: left ON, 26 tests across 13 files moved, and in the
# files that read this dict every one was a premise assert ("fixture drift",
# "should be there to lose"), not the flag under test getting worse. The
# test that is ABOUT the snap is `tests/test_snap_region_edges.py`.
PRE_FLIP["snap_region_edges"] = False
BUNDLE_ON = {name: True for name in COLOUR_BUNDLE}
