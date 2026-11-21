"""The re-snap stops pulling in spools the palette never chose (the
`bind_resnap_all_classes` switch, folded into the code 2026-11-20).

`stage4_vectorize.revalidate_threads` binds its argmin to the selected palette
on photo classes only (2026-08-23). Off that route it runs over the WHOLE
chart, so a re-snapped shape can land on a spool nothing selected and the
operator loads a cone the plan does not name — MASTER_SCOPE 15's *"sews more
spools than the cone list names"*.

Counted 2026-09-06 (`tools/resnap_escape.py`): across the corpus the pass adds
**34 cones, 25 of them outside the selected palette, and every escape is on the
GRADIENT lane** — `screenshot_phone_ui_golke` 7, `drone_render` 5,
`logo_bridge_bar` 5, `logo_golden_tee` 4, `logo_gaulke_roofing` 3. All nine
photo-class fixtures add none, which is the control: the binding works, and the
lane real customer logo art routes to never got it.

The invariant these tests pin is stated on the DESIGN's cone list, not on the
row count: no region may wear a spool outside the selection the palette handed
the pass.
"""

import hashlib
from functools import lru_cache
from typing import NamedTuple

import pytest

from digitizer_core import pipeline as pl
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import plan_stitches, run_stages

from .conftest import PRE_FLIP, TESTDATA
from tests.conftest import own_thread_only

# Two gradient fixtures with a measured escape (7 and 5 cones).
ESCAPERS = ["photo/screenshot_phone_ui_golke.jpg", "photo/drone_render.png"]


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


class _Case(NamedTuple):
    """Everything this file asks of one fixture's pipeline run — plain
    immutable values, never the `PipelineResult`, because the cache below
    shares one object across every test that asks for the same case."""
    digest: tuple           # (sha20 of the emitted stitches, stitch count)
    palette: frozenset      # the spools handed to the re-snap
    cones: frozenset        # the spools the design ends up sewing
    geometry: dict          # shape_id -> polygon WKT


@lru_cache(maxsize=None)
def _case(fixture: str) -> _Case:
    """One pipeline run per fixture, reused by every test.

    WHY THE CACHE. Written straight through this file ran `run_stages` 20-odd
    times over 8 distinct (fixture, flag) pairs. MASTER_SCOPE's "CI feedback
    speed" section records that GitHub's runners are 2-core, so `-n auto` gets
    two workers and *"the remaining lever is `--durations`, not parallelism"*.
    The same change on `test_revalidate_small_shapes.py` measured
    **9m34s -> 2m56s**.

    The palette probe patches `pipeline.revalidate_threads`, NOT
    `stage4_vectorize`'s — `pipeline` binds the name at import, so patching the
    defining module silently records an empty run — and takes `**kw` rather
    than an explicit signature, because `pipeline` also forwards
    `small_shapes` and a spelled-out probe breaks when another is added.
    """
    real = pl.revalidate_threads
    seen: dict = {}

    def probe(regions, p, cfg, **kw):
        seen["palette"] = frozenset(kw.get("palette_indices") or ())
        return real(regions, p, cfg, **kw)

    cfg = _cfg(**PRE_FLIP)   # over the pre-flip engine
    pl.revalidate_threads = own_thread_only(probe, real)
    try:
        result = run_stages(TESTDATA / fixture, cfg)
    finally:
        pl.revalidate_threads = real
    plan = plan_stitches(result, cfg)

    coords = [(round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
              for _b, run in plan.iter_runs() for x, y in run.points]
    return _Case(
        digest=(hashlib.sha256(repr(coords).encode()).hexdigest()[:20],
                len(coords)),
        palette=seen["palette"],
        cones=frozenset(r.thread_index for r in result.regions),
        geometry={r.shape_id: r.polygon.wkt for r in result.regions},
    )


# Retired 2026-11-20 (bundle roll-forward): `test_the_shipped_engine_is_the_three_flags_on`
# compared the default engine with `BUNDLE_ON`, which is empty now that the colour bundle
# is folded, so it compared a run with itself. `test_on_closes_the_escape` below is the
# ON behaviour.


@pytest.mark.parametrize("fixture", ESCAPERS)
def test_on_closes_the_escape(fixture):
    """The whole point: no region wears a spool the palette never selected.
    Asserted as a set difference so the failure message names the offending
    cones."""
    case = _case(fixture)
    assert case.palette, "fixture drift: no palette reached the re-snap"
    assert not (case.cones - case.palette), sorted(case.cones - case.palette)
