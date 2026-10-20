import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, run_stages

# CI sharding (DIGITIZER_SHARD=k/n); a no-op when unset. See tests/_ci_shard.py.
from tests._ci_shard import pytest_collection_modifyitems  # noqa: F401


def own_thread_only(fake, real):
    """Gate a module-global patch to the thread that installed it.

    `monkeypatch.setattr(module, "fn", fake)` swaps the name for EVERY thread
    in the process, and under xdist the service's `JobRegistry` pool (the
    session-long `client` fixture's background thread, `digitizer_service.jobs`)
    can still be sewing a job another test submitted while this test's patch is
    live. Its calls then land in this test's counter, list or tripwire (CI on
    #925, shard 5: `test_fill_bridge_cut` read `[True] * 4`; 6fb67c65 fixed that
    one test inline). Build `fake` exactly as before, keep the original as
    `real`, and install `own_thread_only(fake, real)`: `fake` runs for the
    calling thread of THIS call (captured now, so call it from the test or the
    fixture body, not from a helper that runs on another thread) and every
    other thread gets the unpatched function. The pipeline is single-threaded
    (the service pool is the only thread pool), so the test's own pipeline
    calls all run on this thread.

    Do NOT use it where the code under test deliberately runs on the service
    pool (a test that drives `/digitize` through `client` and counts there).
    """
    import threading

    me = threading.get_ident()

    def gated(*args, **kwargs):
        if threading.get_ident() == me:
            return fake(*args, **kwargs)
        return real(*args, **kwargs)

    return gated


# CI scheduling (`--dist loadgroup`); a no-op otherwise. See
# tests/_xdist_groups.py. A plugin rather than a hook here because this
# conftest already exports the shard hook under the same name.
def pytest_configure(config):
    from tests import _xdist_groups
    if not config.pluginmanager.is_registered(_xdist_groups):
        config.pluginmanager.register(_xdist_groups, "digitizer-xdist-groups")


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


# A client that is NEVER entered as a context manager, so no lifespan runs
# and the shared app's job pool is never shut down (see `client` above).
# For a throwaway app built inside a test, or for the shared app when a test
# needs `raise_server_exceptions=False` to see the 500 a real server sends.
# Lives here because `test_client_fixture_is_shared.py` allows `TestClient(`
# calls in conftest only — that tripwire is about the lifespan, which this
# fixture by construction never triggers.
@pytest.fixture
def make_client():
    pytest.importorskip("fastapi", reason="service extra not installed")
    from fastapi.testclient import TestClient

    return lambda app, **kw: TestClient(app, **kw)


# The deadline every service test waits on. Here, beside `client`, so one
# rule serves every module that drives `/digitize` or `/digitize-manual`
# through the shared app; the service import is inside the function for the
# same reason `client`'s is (fastapi is the optional extra).
#
# WHY A DEADLINE TIED TO THE SERVICE, NOT A LOOP COUNT. Every module here
# used to poll `for _ in range(600): ... sleep(0.1)`, a 60 s wall budget
# (test_manual_sew_order.py had already quietly doubled its own to 1200).
# That number measured the MACHINE, not the contract: `registry` is one
# worker thread per process, so a job's wait is the queue ahead of it (the
# cache-identity tests deliberately submit real digitizes and never read
# them, so they are still sewing when the next test's job lands behind
# them) PLUS its own run, and the own-run half moves with the host and its
# load. `test_review_payload_carries_text_cluster_fields_over_http`
# (`enthusiast_logo` at 90 mm, 24 tesseract spawns) measures 10.4 s serial
# on a 4-core cloud box, 19 s under `-n 4` there, 12.4 s on the reference
# box -- and tripped the 60 s budget as `'running' == 'done'` in CI on
# 10ae9cc, three times in one `-n auto` session on 2026-09-03, and on
# Kent's laptop under `-n 2` on 2026-10-19 (PR #987's body), each time
# passing on re-run with nothing changed. 0 of 30 runs of this file alone
# reproduced it here (2026-10-20, `-n 2`, `-n 4`, serial): the loss is to
# contention, not to the code under test.
#
# The service's own guarantee is `JOB_TIMEOUT_S`: a RUNNING job past it is
# reported `error` on the next read (`JobRegistry._expire_locked`), so a
# genuine runaway still fails every caller's `state == "done"` assertion,
# with `TIMED_OUT` in `error` and the registry's detail instead of a bare
# `'running' == 'done'`. This waits for that terminal state and gives up
# only past the service's own limit plus a margin, naming the registry's
# counts when it does, so the next person reads "queued behind N" instead
# of guessing.
JOB_WAIT_MARGIN_S = 30.0


def wait_for_job(client, job_id: str, *, interval_s: float = 0.1) -> dict:
    """Poll `/jobs/{job_id}` until it is `done` or `error`; return that state.

    Raises AssertionError past `JOB_TIMEOUT_S + JOB_WAIT_MARGIN_S`, naming
    the states seen (and when), and `/health`'s registry counts.
    """
    from digitizer_service.jobs import JOB_TIMEOUT_S

    t0 = time.monotonic()
    deadline = t0 + JOB_TIMEOUT_S + JOB_WAIT_MARGIN_S
    seen: dict[str, float] = {}
    while True:
        r = client.get(f"/jobs/{job_id}")
        state = r.json()
        if r.status_code != 200 or "state" not in state:
            raise AssertionError(f"job {job_id}: HTTP {r.status_code} {state!r}")
        seen.setdefault(state["state"], round(time.monotonic() - t0, 1))
        if state["state"] in ("done", "error"):
            return state
        if time.monotonic() > deadline:
            jobs = client.get("/health").json().get("jobs")
            raise AssertionError(
                f"job {job_id} still {state['state']!r} after "
                f"{time.monotonic() - t0:.0f}s (state first seen at s: {seen}); "
                f"registry {jobs}")
        time.sleep(interval_s)


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
# `two_tone_snap` joined the flipped set 2026-10-11 (defect 58, Kent's
# approval 2026-10-08), for the reason every entry above gives. ON, a
# black-and-white raster is thresholded to its two inks before any region
# exists, so gaulke's grey halo -- the Silver `3971` escape, the 0.58 mm²
# shard, the enclosed `4174` that the resnap and thread-match files take as
# their PREMISE -- is never segmented at all. The test that is ABOUT the snap
# is `tests/test_two_tone.py`.
PRE_FLIP["two_tone_snap"] = False
# `lettering_columns_square_ends` and `lettering_columns_inside_connectors`
# joined the flipped set 2026-10-13 (Kent's ruling), for the reason every
# entry above gives. ON, the Column lane ends every column on the letter's
# own outline and keeps its connectors on the letter, so a lettering fixture's
# stitches, trims and penetrations move; a test pricing one OTHER flag must
# measure against the engine its arms were made on. The tests ABOUT them are
# `tests/test_column_ends.py`.
PRE_FLIP["lettering_columns_square_ends"] = False
PRE_FLIP["lettering_columns_inside_connectors"] = False
# `small_glyph_keep` joined the flipped set 2026-10-13 (Kent's ruling), for the
# reason every entry above gives. ON, stage 4 keeps the counters and the ground
# hole of a rescued small glyph, which on `screenshot_phone_ui_golke` adds one
# cone (15 -> 16) under `revalidate_small_shapes` alone -- the premise
# `test_revalidate_small_shapes` prices that flag against ("16 -> 16 cones").
# The test that is ABOUT the keep is `tests/test_small_glyph_keep.py`.
PRE_FLIP["small_glyph_keep"] = False
# `small_text_true_size` joined the flipped set 2026-10-14 (Kent, WoK 56
# option A, after PR #948's drone fix), for the reason every entry above
# gives. ON, small lettering is re-traced at its true size and thin letters
# sew as bean centrelines (`config.SMALL_TEXT_TRUE_SIZE`), which moves the
# stitches, trims and tiers of every fixture with lettering under 3 mm caps.
# The tests ABOUT it are `tests/test_small_text.py`,
# `tests/test_bean_letters_pipeline.py` and `tests/test_bean_ink_shape_gate.py`.
PRE_FLIP["small_text_true_size"] = False
# ...and its counter guard (Kent, WoK 56 option A; 0.45 mm x 40 / thread_wt,
# replacing a 1.6 mm cap-height guard), which came with the flip: None is no
# guard. With the switch OFF the guard is never read
# (`config.true_size_min_counter`), so this pin is the posture, not a second
# lever. The tests ABOUT it are `tests/test_small_text_counter_guard.py`.
PRE_FLIP["small_text_true_size_min_counter_mm"] = None
# ...and the value the switch fills into `small_text_keep_stray_lines` (True,
# PR #960's 65 mm THE fix, carried by the flip; VP 2026-10-15). None is the
# pre-flip engine: never filled, read as False.
PRE_FLIP["small_text_keep_stray_lines"] = None
# ...and the one-ink link in the text tagger's RESCUED round (2026-10-15,
# Fremont's THE at 80 mm: its one rescued letter joined the tan date and left
# T and H short of a cluster). False is the pre-flip engine: round 1 links
# on size alone. The tests ABOUT it are in `tests/test_textcluster.py`.
PRE_FLIP["text_cluster_rescued_ink_link"] = False
# The two bean-letter holds (Kent's flip 2026-10-15, "flip both holds ON"):
# needle points 0.25 mm off a small counter (#952) and stations 0.2 mm off an
# open bay (#967). Plain defaults, not switch values: None is OFF, the engine
# as the sew-out cards were cut. The tests ABOUT them are
# `tests/test_bean_counter_hold.py` and `tests/test_bean_bay_hold.py`.
PRE_FLIP["bean_letter_counter_hold_mm"] = None
PRE_FLIP["bean_letter_bay_hold"] = None
# Spoked detail marks (Kent's flip 2026-10-16, "ON, tightened"): a small
# enclosed detail of another colour with four or more tips sews as a spoked
# mark on top of its host (Fremont's Wisconsin star). False is the pre-flip
# engine: the detail is absorbed and painted over. The tests ABOUT it are in
# `tests/test_detail_spokes.py`.
PRE_FLIP["detail_spokes"] = False
# The photo lane's phantom-blend dissolve (defect 27; Kent banked it OFF
# 2026-09-04 and flipped it ON 2026-10-20, MASTER_SCOPE item 46, on PR
# #1003's pricing): a merged label that is mostly boundary and a blend of its
# two sides folds into the nearer side, so a JPEG's halo cones are never
# planned. False is the pre-flip engine, with every halo shard the colour
# files take as their premise. The tests ABOUT it are
# `tests/test_phantom_blend_photo.py`.
PRE_FLIP["dissolve_phantom_blends"] = False
BUNDLE_ON = {name: True for name in COLOUR_BUNDLE}
