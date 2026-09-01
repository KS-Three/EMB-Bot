import os
import shutil
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, run_stages

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"

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
