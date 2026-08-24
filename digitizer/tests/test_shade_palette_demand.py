"""Stage-2 shade demand (`cfg.shade_palette_demand`, 2026-08-23) — option (b)
of docs/superpowers/plans/2026-08-23-shade-palette-binding.md, the second half
of Kent's (a)+(b) decision: feed each kept region's proxy shade Labs into
`select_palette` so the palette CONTAINS the anchors the shade bind (option
(a), `cfg.shade_palette_bind`) needs, and carry the selected palette — anchor
spools included — to stage 7's bind set.

What these tests pin, in order of load-bearing-ness:

1. **Flag off is byte-identical to today, on every route.** The config
   default is False; the OFF path never computes demand and hands
   `select_palette` exactly the region rows it always has (proved by spy at
   the seam); `Quant.palette_spools` stays None; and the pipeline gate
   resolves False for every non-photo class even with the flag on, proved by
   whole-pipeline identity on the gradient route (flag on == flag off, same
   regions, same spools, same warnings). The rest of the OFF guarantee is
   the pre-existing byte-identity suites: the photo-lane and flat-lane
   goldens run the OFF path over real fixtures against pre-change captures.

2. **Demand actually reaches `select_palette`** — the ON path's call grows
   extra rows, the region rows are byte-equal to the OFF call's (append-only
   by construction), the extra rows are exactly `_shade_demand_points`'
   output, and the selection's full medoid set lands on
   `Quant.palette_spools`.

3. **The proxy mirrors the stage-6 machinery it predicts** — constants and
   the shade-count formula are cross-pinned against `stage6_blend` /
   `stage6_streamline` (the mirrored-constant lockstep,
   `stage4_vectorize._PHOTO_CLASSES` precedent), and the decomposition is
   deterministic run to run (the seeded `_sample_pixels`-style cap).

4. **Gating is the strict class verdict** — photo classes only, resolved in
   `pipeline.run_stages`, mirroring the region resnap and the stage-7 bind:
   gradient and flat never feed demand however the flag is set.

5. **Anchors reach the stage-7 bind** — `sequence`'s `palette_spools` joins
   the bind's allowed set only under BOTH cfg flags and the photo class, a
   stale carrier is ignored on a flag-off re-plan, and end to end the
   emitted blocks can actually sew an anchor spool no planned region owns.

Spool choices are derived from the live chart by criteria, never hardcoded
(the `test_thread_revalidate_palette.py` convention).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Polygon
from skimage.color import deltaE_ciede2000

import digitizer_core.stage2_photo_segment as S2
from digitizer_core import stage6_blend as S6B
from digitizer_core import stage6_streamline as S6S
from digitizer_core import stage7_sequence as S7
from digitizer_core.config import PipelineConfig
from digitizer_core.fabrics import get_fabric
from digitizer_core.pipeline import run_stages
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import prep
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.threads import CHART, rgb_to_lab
from digitizer_core.warnings_codes import PHOTO_SHADE_DEMAND

TESTDATA = str(Path(__file__).resolve().parent.parent / "testdata" / "photo")
FAB = get_fabric("pique_knit")


class _SelectSpy:
    """Records every (labs, weights) `kept_masks_to_quant` hands
    `select_palette`, passing through to the real implementation."""

    def __init__(self):
        self.calls: list[tuple[np.ndarray, np.ndarray]] = []
        from digitizer_core.palette import select_palette
        self._real = select_palette

    def __call__(self, labs, weights, chart, max_k, *a, **kw):
        self.calls.append((np.array(labs, np.float64).reshape(-1, 3),
                           np.array(weights, np.float64).reshape(-1)))
        return self._real(labs, weights, chart, max_k, *a, **kw)


def _segment_with_spy(monkeypatch, fixture: str, *, shade_demand: bool,
                      split_tonal: bool = True):
    spy = _SelectSpy()
    monkeypatch.setattr(S2, "select_palette", spy)
    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(f"{TESTDATA}/{fixture}", cfg)
    q = S2.segment(p, cfg, split_tonal=split_tonal, shade_demand=shade_demand)
    assert len(spy.calls) == 1
    return p, q, spy.calls[0]


# --- 1. Flag off is byte-identical to today ----------------------------------

def test_flag_defaults_off():
    assert PipelineConfig().shade_palette_demand is False


def test_off_path_feeds_select_palette_exactly_the_region_rows(monkeypatch):
    """OFF (the default every pre-existing caller gets): no demand is even
    computed — a tripwire on `_shade_demand_points` proves the call never
    happens — and `select_palette` receives one row per kept region with the
    plain area weights this seam has always sent, so the OFF call is the
    pre-change call by construction (the photo-lane golden pins the same
    fact byte-for-byte against a pre-change capture)."""
    def tripwire(*a, **kw):  # pragma: no cover - the point is it never runs
        raise AssertionError("_shade_demand_points ran on the OFF path")

    monkeypatch.setattr(S2, "_shade_demand_points", tripwire)
    _p, q, (labs, weights) = _segment_with_spy(
        monkeypatch, "fur_ramp.png", shade_demand=False)

    region_count = next(w for w in q.warnings
                        if w["code"] == "PHOTO_SEGMENT_REGION_COUNT")["count"]
    assert len(labs) == region_count
    assert len(weights) == region_count
    assert (weights == np.round(weights)).all(), (
        "no face/bg classes in this call -> weights are plain pixel areas")
    assert q.palette_spools is None
    assert not any(w["code"] == PHOTO_SHADE_DEMAND for w in q.warnings)


def test_pipeline_gate_gradient_route_is_identical_with_the_flag_on():
    """The whole-pipeline OFF==ON identity on a non-photo route: gradient
    routes through the SAME `segment()` (`photo_segment` handles gradient
    too), so this is the route where a sloppy gate would actually leak.
    Regions, spools, palette and warning codes must all match; the flat
    lane can't leak structurally (quantize() never sees the bool) and its
    goldens already pin it byte-for-byte."""
    base = PipelineConfig(forced_class="gradient")
    on = PipelineConfig(forced_class="gradient", shade_palette_demand=True)
    r0 = run_stages(f"{TESTDATA}/fur_ramp.png", base)
    r1 = run_stages(f"{TESTDATA}/fur_ramp.png", on)

    assert r1.palette_spools is None
    assert [(r.shape_id, r.thread_index) for r in r0.regions] \
        == [(r.shape_id, r.thread_index) for r in r1.regions]
    assert r0.palette == r1.palette
    assert [w["code"] for w in r0.warnings] == [w["code"] for w in r1.warnings]
    assert not any(w["code"] == PHOTO_SHADE_DEMAND for w in r1.warnings)


# --- 2. Demand reaches select_palette ----------------------------------------

def test_demand_rows_reach_select_palette_append_only(monkeypatch):
    """ON: the call grows past the region rows; the region rows are
    byte-equal to the OFF call's own (the demand is APPENDED, never
    interleaved — `region_spools[:len(kept)]`'s correctness rests on this);
    the extra rows are exactly `_shade_demand_points`' output; and the full
    medoid set lands on `Quant.palette_spools` with the PHOTO_SHADE_DEMAND
    warning carrying the same accounting."""
    _p0, _q0, (labs_off, w_off) = _segment_with_spy(
        monkeypatch, "fur_ramp.png", shade_demand=False)
    p, q, (labs_on, w_on) = _segment_with_spy(
        monkeypatch, "fur_ramp.png", shade_demand=True)

    n = len(labs_off)
    assert len(labs_on) > n, "demand must add rows on a tonal fixture"
    assert (labs_on[:n] == labs_off).all()
    assert (w_on[:n] == w_off).all()

    wd = next(w for w in q.warnings if w["code"] == PHOTO_SHADE_DEMAND)
    assert wd["points"] == len(labs_on) - n
    assert 0 < wd["regions_with_demand"] <= n
    assert q.palette_spools is not None
    assert wd["palette_k"] == len(q.palette_spools)
    # Every spool a MAIN region sews is a medoid (the enclosed population
    # quantizes separately and may append spools of its own; fur_ramp has
    # none, so the whole list must be inside the palette here).
    assert set(q.thread_indices) <= set(q.palette_spools)

    # The extra rows are the proxy, exactly.
    kept, _ = _kept_for(p)
    weights = [float(m.area) for m in kept]
    d_labs, d_ws, d_regions = S2._shade_demand_points(p, kept, weights)
    assert wd["regions_with_demand"] == d_regions
    assert np.allclose(labs_on[n:], np.asarray(d_labs))
    assert np.allclose(w_on[n:], np.asarray(d_ws))


def _kept_for(p):
    """The exact kept-region list `segment()` feeds `kept_masks_to_quant`,
    reproduced through the same public seams (labels -> masks would be
    lossy; instead re-run the front half via segment's own tail hook)."""
    # segment() has no public "give me kept" seam; recompute demand from the
    # Quant's own label masks instead — labels ARE the deduped mapping, so
    # instead we re-derive kept by running the front half again with a spy.
    captured = {}
    real = S2.kept_masks_to_quant

    def grab(p_, cfg_, kept, *a, **kw):
        captured["kept"] = kept
        return real(p_, cfg_, kept, *a, **kw)

    S2.kept_masks_to_quant = grab
    try:
        cfg = PipelineConfig(target_width_mm=80.0)
        S2.segment(p, cfg, split_tonal=True, shade_demand=False)
    finally:
        S2.kept_masks_to_quant = real
    return captured["kept"], None


def test_demand_is_deterministic():
    """Seeded sampling (the `_sample_pixels` mirror): two computations over
    the same prep produce identical rows — this feeds byte-identity goldens
    downstream, nothing here may wobble."""
    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(f"{TESTDATA}/fur_ramp.png", cfg)
    kept, _ = _kept_for(p)
    weights = [float(m.area) for m in kept]
    a_labs, a_ws, a_n = S2._shade_demand_points(p, kept, weights)
    b_labs, b_ws, b_n = S2._shade_demand_points(p, kept, weights)
    assert a_n == b_n
    assert np.array_equal(np.asarray(a_labs), np.asarray(b_labs))
    assert np.array_equal(np.asarray(a_ws), np.asarray(b_ws))
    # And the demand is real: a big tonal region contributes 3-5 shades
    # whose weights sum to its own region weight.
    assert len(a_labs) >= 3
    total_w_regions = sum(
        w for w, m in zip(weights, kept)
        if m.area >= S2._SHADE_DEMAND_MIN_SAMPLES)
    assert np.isclose(sum(a_ws), total_w_regions), (
        "each region's shade rows must together weigh exactly the region")


# --- 3. The proxy mirrors stage 6 --------------------------------------------

def test_mirrored_constants_lockstep_with_stage6():
    """The hoisted constants ARE stage 6's — a membership change there must
    land here too, and this pin is what makes the drift loud (the
    `_PHOTO_CLASSES` / `PALETTE_EXCESS_DELTAE` mirrored-constant
    arrangement)."""
    assert S2._SHADE_DEMAND_BLUR_MM == S6S.STREAMLINE_BLUR_MM
    assert S2._SHADE_DEMAND_MIN_SAMPLES == S6S._SHADE_MIN_SAMPLES
    assert S2._SHADE_DEMAND_MAX_SAMPLES == S6B.RAMP_MAX_SAMPLES
    assert S2._SHADE_DEMAND_SAMPLE_SEED == S6B.RAMP_SAMPLE_SEED
    assert S2._SHADE_DEMAND_STEP_DELTAE == S6B.SHADE_STEP_DELTAE
    assert S2._SHADE_DEMAND_COUNT_MIN == S6B.SHADE_COUNT_MIN
    assert S2._SHADE_DEMAND_COUNT_MAX == S6B.SHADE_COUNT_MAX


def test_shade_count_formula_matches_stage6_verbatim():
    for de in np.linspace(0.0, 60.0, 601):
        assert S2._shade_demand_count(float(de)) \
            == S6B._choose_shade_count(float(de)), de


# --- 4. Gating is the strict class verdict -----------------------------------

@pytest.mark.parametrize("forced,fixture", [
    ("photo_subject", "photo/photo_subject_stub.png"),
    ("gradient", "photo/photo_subject_stub.png"),
    # The flat arm runs a REAL flat fixture: forcing a photo raster down the
    # flat lane fragments it into a pathological region count (measured:
    # >13 GB in vectorize) and proves nothing extra — the flat lane never
    # reaches `kept_masks_to_quant` at all, so any flat design demonstrates
    # the gate.
    ("flat", "logo_whitebg.png"),
])
def test_pipeline_gate_photo_classes_only(forced, fixture):
    """`run_stages` resolves the bool: photo classes feed demand, gradient
    (which routes through the SAME segment()) and flat (which never reaches
    it) do not — the region resnap's own `_PHOTO_CLASSES` posture."""
    cfg = PipelineConfig(forced_class=forced, shade_palette_demand=True)
    r = run_stages(str(Path(TESTDATA).parent / fixture), cfg)
    fed = any(w["code"] == PHOTO_SHADE_DEMAND for w in r.warnings)
    if forced == "photo_subject":
        assert fed and r.palette_spools
    else:
        assert not fed and r.palette_spools is None


# --- 5. Anchors reach the stage-7 bind ---------------------------------------

_PX_PER_MM = 4.0


def _source(gray_img: np.ndarray) -> SourcePixels:
    h, w = gray_img.shape[:2]
    rgb = np.dstack([gray_img] * 3) if gray_img.ndim == 2 else gray_img
    return SourcePixels(rgb=rgb.astype(np.uint8), px_per_mm=_PX_PER_MM,
                        origin_px=(w / 2.0, h / 2.0))


def _full_ramp(w_px: int = 320, h_px: int = 240) -> np.ndarray:
    return np.tile(np.linspace(250, 5, w_px), (h_px, 1)).astype(np.uint8)


def _region(poly: Polygon) -> Region:
    return Region(shape_id="Stest", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area,
                  meta={"layer": 0, "tier": "fill"})


def _nearest_spool_to(rgb: tuple[int, int, int]) -> int:
    lab = rgb_to_lab(np.array([rgb], np.uint8))
    d = deltaE_ciede2000(np.repeat(lab, len(CHART.lab), axis=0), CHART.lab)
    return int(np.argmin(d))


def _bind_palettes_seen(monkeypatch, cfg, *, palette_spools, design_class):
    seen: list[object] = []
    real = S7.streamline_fill

    def spy(region, source_pixels, cfg_, **kw):
        seen.append(kw.get("shade_palette_indices", "MISSING"))
        return real(region, source_pixels, cfg_, **kw)

    monkeypatch.setattr(S7, "streamline_fill", spy)
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    planned, _ = resolve_overlaps([_region(poly)], FAB, cfg,
                                  design_class=design_class)
    S7.sequence(planned, FAB, cfg, source_pixels=_source(_full_ramp()),
                design_class=design_class, palette_spools=palette_spools)
    return seen


def test_sequence_unions_anchor_spools_into_the_bind_set(monkeypatch):
    """Both flags on, photo class: the bind's allowed set is the planned
    regions' spools UNION the demand palette — the anchor a region never
    claimed is exactly what (b) selected the palette FOR."""
    anchor = _nearest_spool_to((10, 10, 10))
    assert anchor != 0
    cfg = PipelineConfig(fill_technique="streamline",
                         streamline_mode="layered",
                         shade_palette_bind=True, shade_palette_demand=True)
    seen = _bind_palettes_seen(monkeypatch, cfg,
                               palette_spools=[0, anchor],
                               design_class="photo_subject")
    assert seen == [sorted({0, anchor})]


def test_sequence_ignores_a_stale_carrier_when_the_demand_flag_is_off(
        monkeypatch):
    """Bind on, demand OFF: a `palette_spools` carrier (e.g. a re-plan of a
    demand-built generation with the flag since turned off) must NOT widen
    the bind — explicit config wins, exactly as for every other resolved
    parameter `sequence` takes."""
    anchor = _nearest_spool_to((10, 10, 10))
    cfg = PipelineConfig(fill_technique="streamline",
                         streamline_mode="layered",
                         shade_palette_bind=True)
    seen = _bind_palettes_seen(monkeypatch, cfg,
                               palette_spools=[0, anchor],
                               design_class="photo_subject")
    assert seen == [[0]], "stale anchors must not leak into a flag-off bind"


def test_sequence_still_passes_none_when_the_bind_is_off(monkeypatch):
    """Demand alone does not bind: with `shade_palette_bind` off the tier
    receives None however the demand side is configured — (b) shapes the
    palette, (a) is what masks the snap.

    The bind must be turned off EXPLICITLY here since 2026-08-24: Kent's
    ruling took (a) and declined (b), so a bare config now has the bind on
    and this test would be measuring the bound path instead."""
    anchor = _nearest_spool_to((10, 10, 10))
    cfg = PipelineConfig(fill_technique="streamline",
                         streamline_mode="layered",
                         shade_palette_bind=False,
                         shade_palette_demand=True)
    seen = _bind_palettes_seen(monkeypatch, cfg,
                               palette_spools=[0, anchor],
                               design_class="photo_subject")
    assert seen == [None]


def test_end_to_end_blocks_can_sew_an_anchor_no_region_owns():
    """The carrier's whole point, measured from EMITTED blocks: with both
    flags on and a demand palette carrying a dark and a light anchor, the
    one-region ramp fixture sews blocks ONLY in {region spool} ∪ anchors,
    and at least one block lands on an anchor — a spool that, without the
    union, could never have been sewn (the bind would have collapsed
    everything onto the region's own thread 0, which is exactly what the
    bind suite's own end-to-end test pins for (a) alone)."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    source = _source(_full_ramp())
    dark = _nearest_spool_to((10, 10, 10))
    light = _nearest_spool_to((250, 250, 250))
    assert dark != 0 and light != dark

    cfg = PipelineConfig(fill_technique="streamline",
                         streamline_mode="layered",
                         shade_palette_bind=True, shade_palette_demand=True)
    planned, _ = resolve_overlaps([_region(poly)], FAB, cfg,
                                  design_class="photo_subject")
    blocks, _w = S7.sequence(planned, FAB, cfg, source_pixels=source,
                             design_class="photo_subject",
                             palette_spools=[dark, light])
    sewn = {b.thread_index for b in blocks}
    assert sewn <= {0, dark, light}
    assert sewn & {dark, light}, (
        f"anchors never sewn: blocks only in {sorted(sewn)}")
    assert all(sum(len(b.runs) for b in blocks if b.thread_index == t) > 0
               for t in sewn)
