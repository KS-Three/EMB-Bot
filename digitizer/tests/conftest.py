from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, run_stages

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"

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
