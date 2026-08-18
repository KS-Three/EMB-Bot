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
def enthusiast_logo_82mm():
    # 82mm, not this file's usual 80mm default: test_chaining.py's two
    # corpus-benchmark tests moved here from logo_alpha.png (2026-08-06) after
    # the satin/fill classifier's flat-lane DT-tightening fix correctly
    # reclassified two of that fixture's shapes from satin to fill, which
    # incidentally eliminated the narrow gap chain_links used to bridge on
    # logo_alpha specifically -- a fixture-geometry change, not a chaining
    # regression (every synthetic-geometry chaining test elsewhere in this
    # file is unaffected). enthusiast_logo.png is this repo's own primary
    # real-art benchmark (COOKBOOK.md); swept across widths, 82mm is the
    # first ordinary value that lands the chained trim rate safely inside the
    # corpus band with margin (3.41/1k vs the 4.1 ceiling) while still
    # showing a large, unambiguous chaining win (links 2->17, trims 21->9,
    # zero bare-fabric exposure either way) -- not cherry-picked to the edge
    # of the threshold.
    return run_stages(TESTDATA / "photo/enthusiast_logo.png", cfg(target_width_mm=82.0))


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
