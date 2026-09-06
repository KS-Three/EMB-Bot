"""`cfg.bind_resnap_all_classes` — the re-snap stops pulling in spools the
palette never chose. DEFAULT OFF.

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
row count: with the flag ON, no region may wear a spool outside the selection
the palette handed the pass.
"""

import hashlib
from functools import lru_cache
from typing import NamedTuple

import pytest

from digitizer_core import pipeline as pl
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import plan_stitches, run_stages

from .conftest import TESTDATA

# Two gradient fixtures with a measured escape (7 and 5 cones), one photo-class
# fixture that already binds (must be byte-identical either way), and a flat
# control.
ESCAPERS = ["photo/screenshot_phone_ui_golke.jpg", "photo/drone_render.png"]
CONTROLS = ["photo/photo_dof_meadow.png", "logo_alpha.png"]


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


class _Case(NamedTuple):
    """Everything this file asks of one (fixture, flag) pipeline run — plain
    immutable values, never the `PipelineResult`, because the cache below
    shares one object across every test that asks for the same case."""
    digest: tuple           # (sha20 of the emitted stitches, stitch count)
    palette: frozenset      # the spools handed to the re-snap
    cones: frozenset        # the spools the design ends up sewing
    geometry: dict          # shape_id -> polygon WKT


@lru_cache(maxsize=None)
def _case(fixture: str, bind: bool) -> _Case:
    """One pipeline run per (fixture, flag), reused by every test.

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

    cfg = _cfg(bind_resnap_all_classes=bind)
    pl.revalidate_threads = probe
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


@lru_cache(maxsize=None)
def _default_digest(fixture: str) -> tuple:
    """The shipped engine with NO flag mentioned, for the byte-identity
    contract. Deliberately not `_case(fixture, False)`: that passes the flag
    explicitly, and comparing the two is the whole point — they agree only
    while the default is False."""
    cfg = _cfg()
    result = run_stages(TESTDATA / fixture, cfg)
    plan = plan_stitches(result, cfg)
    coords = [(round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
              for _b, run in plan.iter_runs() for x, y in run.points]
    return hashlib.sha256(repr(coords).encode()).hexdigest()[:20], len(coords)


def test_flag_defaults_off():
    assert PipelineConfig().bind_resnap_all_classes is False


@pytest.mark.parametrize("fixture", ESCAPERS + CONTROLS)
def test_off_is_byte_identical_to_the_shipped_engine(fixture):
    """Explicit False against the default, so a change to the default shows up
    as a difference rather than silently agreeing with itself."""
    assert _default_digest(fixture) == _case(fixture, False).digest


@pytest.mark.parametrize("fixture", ESCAPERS)
def test_on_closes_the_escape(fixture):
    """The whole point: with the flag ON no region wears a spool the palette
    never selected. Asserted as a set difference so the failure message names
    the offending cones."""
    case = _case(fixture, True)
    assert case.palette, "fixture drift: no palette reached the re-snap"
    assert not (case.cones - case.palette), sorted(case.cones - case.palette)


@pytest.mark.parametrize("fixture", ESCAPERS)
def test_the_escape_is_really_there_with_the_flag_off(fixture):
    """A control on the test above — without it, `test_on_closes_the_escape`
    would still pass on a fixture that never escaped, and prove nothing."""
    case = _case(fixture, False)
    assert case.cones - case.palette, (
        "no escape on this fixture any more; re-derive from "
        "tools/resnap_escape.py rather than deleting the test")


@pytest.mark.parametrize("fixture", CONTROLS)
def test_a_photo_class_fixture_is_unaffected(fixture):
    """`photo_dof_meadow` already binds, `logo_alpha` has nothing to escape
    with — both must be byte-identical with the flag ON, which is what says
    this change reaches only the lane it is aimed at."""
    assert _default_digest(fixture) == _case(fixture, True).digest


@pytest.mark.parametrize("fixture", ESCAPERS)
def test_on_never_changes_a_shape_id_or_its_geometry(fixture):
    """Threads only, never geometry — `revalidate_threads`' own invariant
    (*"the polygon that came out of simplification is the one that sews
    well"*). Compared as a shape_id -> WKT map, not two ordered lists:
    `rehome_resnapped_regions` moves a re-snapped region between layers, so
    the ORDER is expected to change and a positional comparison reads that as
    a geometry change.
    """
    assert _case(fixture, True).geometry == _case(fixture, False).geometry
