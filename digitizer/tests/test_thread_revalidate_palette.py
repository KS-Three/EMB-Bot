"""The photo-route palette binding on `stage4_vectorize.revalidate_threads`
(2026-08-23).

The defect, measured live on Kent's four acceptance portraits
(`forced_class="photo_subject"`, the toggle route): `select_palette` picks a
capped palette — 12 spools on `baby_deck_laugh` — and this pass then re-snaps
drifted shapes with an argmin over the FULL ~300-spool chart, pulling spools
the palette never chose back into the design. On that portrait: 45 shapes
resnapped onto 19 out-of-palette spools, 55 block-level threads sewn off a
12-cone colour list, 92 machine colour stops. The resnapped shape ids equal
the `PALETTE_THREAD_MISMATCH` ids exactly.

The binding is CLASS-GATED, and the gate is load-bearing: fix #6.3's own
motivating case (`repro_gradient_white_icon.png`, pinned end-to-end with
measured numbers in `tests/test_thread_revalidate.py`) is GRADIENT-lane, and
the flat/gradient byte-identity guards require those lanes untouched — so
every non-photo class keeps the unrestricted chart argmin even when a caller
passes a palette. The gate mirrors `stage7_sequence.PHOTO_CLASSES` the same
way `stage6_satin._PHOTO_CLASSES` does; the lockstep is pinned here exactly
as `tests/test_photo_width_floor.py` pins that one.

Spool indices in these tests are selected from the real Isacord chart by
CRITERIA (distance bands measured in-test), not hardcoded — a chart update
moves the selection, not the test's validity.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from digitizer_core import stage4_vectorize as V
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.stage7_sequence import PHOTO_CLASSES
from digitizer_core.threads import chart_for, rgb_to_lab
from digitizer_core.warnings_codes import THREAD_RESNAPPED_AFTER_DRIFT

try:
    from skimage.color import deltaE_ciede2000
except ImportError:  # pragma: no cover - matches stage4's own fallback
    from skimage.color.delta_e import deltaE_ciede2000


CFG = PipelineConfig()
CHART = chart_for(CFG)


def _de_to_chart(rgb: tuple[int, int, int]) -> np.ndarray:
    """dE00 of one solid colour against every chart spool — exactly the
    per-spool score `revalidate_threads` computes for a solid region (its
    per-pixel median collapses to the single pixel value)."""
    lab = rgb_to_lab(np.array([rgb], np.uint8))
    return deltaE_ciede2000(
        np.repeat(lab, len(CHART.lab), axis=0), CHART.lab
    ).reshape(-1)


def _pick(de: np.ndarray, lo: float, hi: float, *, exclude: set[int]) -> int:
    """Lowest-index spool whose distance to the scenario colour sits in
    [lo, hi) — bands wide enough that the real chart always populates them."""
    for i in np.argsort(de):
        i = int(i)
        if i in exclude:
            continue
        if lo <= de[i] < hi:
            return i
    raise AssertionError(f"no chart spool with dE00 in [{lo}, {hi}) — "
                         "scenario colour needs re-choosing for this chart")


def _scenario():
    """-> (prep, colour_de, global_best). A 60x60 solid-colour raster whose
    single region footprint (40x40 px = 1,600 px) clears
    THREAD_REVALIDATE_MIN_PX with room.

    The colour is an exact chart spool's own RGB (the chart's nearest match
    to a mid-red, resolved at run time) so the chart-wide best sits at
    dE00 == 0 and every band below is measured from a true floor — a first
    draft used a raw CSS red and its NEAREST chart spool turned out to be
    5.36 dE00 away, which silently broke the improvement-gate scenario's
    arithmetic."""
    colour_rgb = tuple(int(v) for v in
                       CHART[int(np.argmin(_de_to_chart((178, 34, 34))))].rgb)
    rgb = np.zeros((60, 60, 3), np.uint8)
    rgb[:] = colour_rgb
    p = Prep(
        rgb=rgb,
        bg_mask=np.zeros((60, 60), bool),
        px_per_mm=2.0,
        art_bbox=(0, 0, 60, 60),
    )
    de = _de_to_chart(colour_rgb)
    return p, de, int(np.argmin(de))


def _region(thread_index: int) -> Region:
    poly = Polygon([(-10, -10), (10, -10), (10, 10), (-10, 10)])
    return Region(
        shape_id="Stest0001",
        polygon=poly,
        thread_index=thread_index,
        thread_number=CHART[thread_index].number,
        area_mm2=poly.area,
        meta={"layer": 0},
    )


def test_photo_class_resnap_stays_inside_the_palette():
    """The fix itself: a drifted photo-route shape re-snaps to the best spool
    IN THE PALETTE, not the chart-wide best sitting outside it."""
    p, de, global_best = _scenario()
    wrong = _pick(de, 20.0, 60.0, exclude={global_best})
    in_palette = _pick(de, 5.0, 15.0, exclude={global_best, wrong})
    assert de[wrong] - de[in_palette] >= V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00

    r = _region(wrong)
    warnings = V.revalidate_threads(
        [r], p, CFG,
        palette_indices=[wrong, in_palette],
        design_class="photo_subject",
    )
    assert r.thread_index == in_palette, (
        f"snapped to {r.thread_index} (dE {de[r.thread_index]:.2f}) — "
        f"expected palette member {in_palette} (dE {de[in_palette]:.2f}); "
        f"chart-wide best was {global_best} (dE {de[global_best]:.2f})"
    )
    assert r.thread_index != global_best  # the escape this fix closes
    assert r.thread_number == CHART[in_palette].number
    assert len(warnings) == 1
    w = warnings[0]
    assert w["code"] == THREAD_RESNAPPED_AFTER_DRIFT
    assert w["ids"] == ["Stest0001"]


def test_flat_and_gradient_keep_the_unrestricted_chart_argmin():
    """The load-bearing gate: even with a palette PASSED, a non-photo class
    re-snaps chart-wide — fix #6.3's gradient-lane behaviour, byte-identical
    to before the parameter existed (the flat/gradient goldens rely on it)."""
    p, de, global_best = _scenario()
    wrong = _pick(de, 20.0, 60.0, exclude={global_best})
    in_palette = _pick(de, 5.0, 15.0, exclude={global_best, wrong})

    for cls in ("flat", "gradient"):
        r = _region(wrong)
        V.revalidate_threads(
            [r], p, CFG,
            palette_indices=[wrong, in_palette],
            design_class=cls,
        )
        assert r.thread_index == global_best, (cls, r.thread_index)


def test_the_default_arguments_are_the_old_signature():
    """A caller that passes neither palette nor class gets exactly the old
    unrestricted behaviour — no argument means no restriction."""
    p, de, global_best = _scenario()
    wrong = _pick(de, 20.0, 60.0, exclude={global_best})
    r = _region(wrong)
    V.revalidate_threads([r], p, CFG)
    assert r.thread_index == global_best


def test_a_photo_class_with_no_palette_is_unrestricted_too():
    """Defensive half of the gate: an empty/absent palette must degrade to
    the old argmin, never to a crash or a snap-to-nothing."""
    p, de, global_best = _scenario()
    wrong = _pick(de, 20.0, 60.0, exclude={global_best})
    for palette in (None, []):
        r = _region(wrong)
        V.revalidate_threads(
            [r], p, CFG, palette_indices=palette, design_class="photo_subject"
        )
        assert r.thread_index == global_best


def test_the_improvement_gate_reads_the_restricted_candidate():
    """The 3.0-dE00 churn guard measures the best PALETTE spool, not the
    chart-wide best: when the only in-palette improvement is under the gate,
    the shape keeps its thread — even though an out-of-palette spool would
    have cleared it. Without this, binding would trade the escape hatch for
    palette-internal churn."""
    p, de, global_best = _scenario()
    # Walk the chart's own sorted distances for two ADJACENT spools whose
    # gap is a real improvement but under the gate — fixed bands don't work
    # here, the chart's neighbourhood around any one colour is too sparse to
    # promise a spool at an arbitrary offset (measured: the anchor red's
    # nearest non-identical spools jump straight from 0 to 5.6 dE00).
    order = [int(i) for i in np.argsort(de) if int(i) != global_best]
    rival = assigned = None
    for r_i, a_i in zip(order, order[1:]):
        gap = de[a_i] - de[r_i]
        if (de[r_i] >= V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 + 0.5
                and 0.05 < gap < V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00):
            rival, assigned = r_i, a_i
            break
    assert rival is not None, "no adjacent spool pair fits the gate scenario"
    # Scenario arithmetic the test relies on, restated as checks: the
    # chart-wide best clears the gate from `assigned`; the palette rival
    # does not.
    assert de[assigned] - de[global_best] >= V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00
    assert 0.0 < de[assigned] - de[rival] < V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00

    r = _region(assigned)
    warnings = V.revalidate_threads(
        [r], p, CFG,
        palette_indices=[assigned, rival],
        design_class="photo_subject",
    )
    assert r.thread_index == assigned, (
        f"churned to {r.thread_index} for a "
        f"{de[assigned] - de[r.thread_index]:.2f} dE00 gain"
    )
    assert warnings == []

    # Control: the identical shape on the flat lane DOES clear the gate via
    # the chart-wide best — proving the restriction, not the scenario, held
    # the photo-route shape back.
    r2 = _region(assigned)
    V.revalidate_threads([r2], p, CFG, design_class="flat")
    assert r2.thread_index == global_best


def test_photo_class_mirror_is_in_lockstep():
    """stage4_vectorize mirrors stage7's PHOTO_CLASSES (stage6_satin already
    keeps the same mirror for the same reason); drift here fails SILENT in
    production — a new photo class would get photo sequencing but keep the
    full-chart resnap escape — so the lockstep is pinned, exactly as
    tests/test_photo_width_floor.py pins stage6_satin's copy."""
    assert V._PHOTO_CLASSES == PHOTO_CLASSES
