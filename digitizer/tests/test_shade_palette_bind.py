"""The shade-path palette binding EXPERIMENT (`cfg.shade_palette_bind`,
2026-08-23) — option (a) of docs/superpowers/plans/2026-08-23-shade-palette-
binding.md, built as an instrument for Kent's quality call, not as a default.

What these tests pin, in order of load-bearing-ness:

1. **Flag off is byte-identical to today.** The OFF path is proved untouched
   at every seam the flag added: the config default is False; `sequence`
   passes `shade_palette_indices=None` for a photo class with the flag off
   AND for every non-photo class with the flag on (the strict class gate,
   mirroring `stage4_vectorize.revalidate_threads`' own); and
   `_shade_layers` with `palette_indices` absent / None / empty produces the
   identical decomposition — same spools, same membership values — as the
   parameter not existing. The rest of the OFF guarantee is the pre-existing
   suite itself: every layered-mode test and every golden runs with the flag
   defaulted off, so a behaviour change there fails loud without this file's
   help.

2. **Bound shades stay inside the palette**, and the fixture is proved to
   actually exercise the mask (the unbound run picks a spool outside it).

3. **Adjacent same-spool shades merge into one honest layer** — fewer
   layers, no adjacent duplicates, membership a plateau covering every
   constituent shade's own center, and the layers still partition coverage
   (shares sum to 1 above the highlight cutoff) exactly as the unbound tents
   do.

4. **End to end through the real stage 5 + stage 7**, the instrument's whole
   claim: flag on, a photo-class plan's blocks sew ONLY the planned regions'
   own spools; flag off, the same fixture sews 3+ chart-wide shade spools —
   the escape the experiment exists to measure.

Spool choices are derived from the live chart by criteria (the
`test_thread_revalidate_palette.py` convention), never hardcoded, so a chart
update moves the selection rather than invalidating the test.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon
from skimage.color import deltaE_ciede2000

from digitizer_core import stage7_sequence as S7
from digitizer_core.config import PipelineConfig
from digitizer_core.fabrics import get_fabric
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_streamline import (
    STREAMLINE_CUTOFF_DARKNESS,
    _darkness_sampler,
    _shade_layers,
)
from digitizer_core.threads import CHART, rgb_to_lab

_PX_PER_MM = 4.0
FAB = get_fabric("pique_knit")


def _source(gray_img: np.ndarray) -> SourcePixels:
    h, w = gray_img.shape[:2]
    rgb = np.dstack([gray_img] * 3) if gray_img.ndim == 2 else gray_img
    return SourcePixels(rgb=rgb.astype(np.uint8), px_per_mm=_PX_PER_MM,
                        origin_px=(w / 2.0, h / 2.0))


def _full_ramp(w_px: int = 320, h_px: int = 240) -> np.ndarray:
    """The layered suite's own light-to-dark ramp — spans nearly the full
    luminance range so every canonical shade position gets real samples."""
    return np.tile(np.linspace(250, 5, w_px), (h_px, 1)).astype(np.uint8)


def _region(poly: Polygon, meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id="Stest", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area, meta=m)


def _decomposition(palette_indices=None, **kw):
    """One `_shade_layers` call on the shared ramp fixture."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    source = _source(_full_ramp())
    darkness = _darkness_sampler(source)
    cfg = PipelineConfig(streamline_mode="layered")
    return _shade_layers(poly, source, darkness, _region(poly), cfg,
                         palette_indices=palette_indices, **kw), darkness


def _membership_samples(shades, xs=np.linspace(-34.0, 34.0, 200)):
    """Every layer's membership sampled along the ramp axis — the byte-level
    fingerprint of a decomposition's coverage maps."""
    return [[m(float(x), 0.0) for x in xs] for _t, _rgb, m in shades]


def _nearest_spool_to(rgb: tuple[int, int, int]) -> int:
    lab = rgb_to_lab(np.array([rgb], np.uint8))
    d = deltaE_ciede2000(np.repeat(lab, len(CHART.lab), axis=0), CHART.lab)
    return int(np.argmin(d))


# --- 1. Flag off is byte-identical to the pre-ruling route -------------------

def test_flag_defaults_on_and_the_unbound_paths_are_one_path():
    """`shade_palette_bind` defaults TRUE since Kent's 2026-08-24 ruling, and
    every spelling of "no palette" — parameter absent, None, empty list — is
    still one decomposition down to the sampled membership values.

    The default assertion is the load-bearing half: a silent revert to False
    would re-open the cone escape (43/45/50/14 spools against palettes of
    15/12/12/7) with nothing in the UI to show it, since the review screen's
    thread count comes from shape thread_index and IS palette-bound while the
    sewing blocks are not. The unbound path stays reachable through an
    explicit False, so it is exercised here rather than left dead."""
    assert PipelineConfig().shade_palette_bind is True
    assert PipelineConfig(shade_palette_bind=False).shade_palette_bind is False

    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    source = _source(_full_ramp())
    darkness = _darkness_sampler(source)
    cfg = PipelineConfig(streamline_mode="layered", shade_palette_bind=False)
    absent = _shade_layers(poly, source, darkness, _region(poly), cfg)
    (none_arg, _), (empty, _) = _decomposition(None), _decomposition([])

    for other in (none_arg, empty):
        assert [t for t, _r, _m in absent] == [t for t, _r, _m in other]
        assert [r for _t, r, _m in absent] == [r for _t, r, _m in other]
        assert _membership_samples(absent) == _membership_samples(other)


def test_sequence_passes_no_palette_when_the_flag_is_off(monkeypatch):
    """Photo class, flag explicitly OFF (the pre-2026-08-24 shipped route):
    the tier must receive `shade_palette_indices=None` — the exact argument
    value the unbound-path test above proves is the pre-change code path.

    Explicit since the default flipped ON: this no longer follows from
    constructing a bare config, so the opt-out has to be spelled out or the
    test would silently stop testing the unbound path."""
    seen: list[object] = []
    real = S7.streamline_fill

    def spy(region, source_pixels, cfg, **kw):
        seen.append(kw.get("shade_palette_indices", "MISSING"))
        return real(region, source_pixels, cfg, **kw)

    monkeypatch.setattr(S7, "streamline_fill", spy)
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    cfg = PipelineConfig(fill_technique="streamline", streamline_mode="layered",
                         shade_palette_bind=False)
    planned, _ = resolve_overlaps([_region(poly, meta={"tier": "fill"})], FAB,
                                  cfg, design_class="photo_subject")
    S7.sequence(planned, FAB, cfg, source_pixels=_source(_full_ramp()),
                design_class="photo_subject")
    assert seen == [None]


def test_sequence_gate_is_the_strict_class_verdict(monkeypatch):
    """Flag ON but a non-photo class: no palette reaches the tier — the same
    strict class gate the region-level binding keys on
    (`revalidate_threads`' `_PHOTO_CLASSES`), so the two bindings can never
    disagree about which designs are bound. Flat AND gradient both checked —
    the two lanes whose byte-identity the phase-4 spec pins."""
    seen: list[object] = []
    real = S7.streamline_fill

    def spy(region, source_pixels, cfg, **kw):
        seen.append(kw.get("shade_palette_indices", "MISSING"))
        return real(region, source_pixels, cfg, **kw)

    monkeypatch.setattr(S7, "streamline_fill", spy)
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    cfg = PipelineConfig(fill_technique="streamline", streamline_mode="layered",
                         shade_palette_bind=True)
    for cls in ("flat", "gradient"):
        planned, _ = resolve_overlaps([_region(poly, meta={"tier": "fill"})],
                                      FAB, cfg, design_class=cls)
        S7.sequence(planned, FAB, cfg, source_pixels=_source(_full_ramp()),
                    design_class=cls)
    assert seen == [None, None]


# --- 2. The bind itself -------------------------------------------------------

def test_bound_shades_stay_inside_the_palette():
    """Masked snap: every bound shade spool is a palette member. The palette
    is built to provably exercise the mask — it keeps exactly one of the
    unbound run's own spools, so at least one shade HAD to move."""
    unbound, _ = _decomposition(None)
    unbound_spools = [t for t, _r, _m in unbound]
    assert len(set(unbound_spools)) >= 2, (
        "fixture must give the full chart room to pick several spools")

    palette = [unbound_spools[0], _nearest_spool_to((255, 0, 0))]
    assert set(unbound_spools) - set(palette), (
        "palette must exclude at least one unbound spool to exercise the mask")

    bound, _ = _decomposition(palette)
    assert {t for t, _r, _m in bound} <= set(palette)
    for t, rgb, _m in bound:
        assert rgb == tuple(int(v) for v in CHART[t].rgb)


def test_bound_snap_is_the_nearest_palette_spool_not_just_any_member():
    """The mask changes the candidate set, not the metric: each shade lands
    on the palette spool nearest ITS OWN colour, verified against a direct
    CIEDE2000 computation from the unbound decomposition's own spool colours
    (a stand-in for the shade labs, exact whenever the unbound snap was) —
    here checked on the extreme dark shade, whose unbound spool colour is
    measurably nearer the dark palette anchor than the light one."""
    unbound, _ = _decomposition(None)
    dark_spool = unbound[0][0]  # dark-first order
    dark_anchor = _nearest_spool_to((10, 10, 10))
    light_anchor = _nearest_spool_to((250, 250, 250))
    assert dark_anchor != light_anchor

    d = deltaE_ciede2000(
        np.repeat(CHART.lab[dark_spool:dark_spool + 1], 2, axis=0),
        CHART.lab[[dark_anchor, light_anchor]])
    assert d[0] < d[1], "scenario arithmetic: the dark shade's spool must " \
                        "sit nearer the dark anchor"

    bound, _ = _decomposition([light_anchor, dark_anchor])
    assert bound[0][0] == dark_anchor, (
        f"dark shade bound to {bound[0][0]}, expected the nearer palette "
        f"member {dark_anchor}")


# --- 3. The adjacent-same-spool merge ----------------------------------------

def test_adjacent_same_spool_shades_merge_into_one_honest_layer():
    """A two-spool palette forces the 3-5 shade decomposition to collapse:
    fewer layers than unbound shades, NO adjacent layers on one spool left,
    and each merged layer's membership reads 1.0 at every constituent
    shade's own canonical center — a plateau, the sum of the merged tents,
    not one surviving tent with the others silently dropped."""
    unbound, _ = _decomposition(None)
    n = len(unbound)
    assert n >= 3

    dark_anchor = _nearest_spool_to((10, 10, 10))
    light_anchor = _nearest_spool_to((250, 250, 250))
    bound, _ = _decomposition([dark_anchor, light_anchor])

    assert len(bound) < n, "two spools under 3+ shades must merge somewhere"
    spools = [t for t, _r, _m in bound]
    assert all(a != b for a, b in zip(spools, spools[1:])), (
        f"adjacent duplicate spools survived the merge: {spools}")
    assert set(spools) <= {dark_anchor, light_anchor}

    # Every unbound shade's own membership must be DOMINATED by some bound
    # layer at that shade's own peak (the plateau is the sum of its member
    # tents, so it covers each of them pointwise) — no constituent silently
    # dropped. Grid-sampled, so compare against the tent's own sampled peak
    # value, not an exact 1.0 the grid never lands on.
    xs = np.linspace(-34.0, 34.0, 400)
    for _t, _r, tent in unbound:
        shares = np.array([tent(float(x), 0.0) for x in xs])
        peak_x = float(xs[int(np.argmax(shares))])
        if shares.max() < 0.9:  # a shade the fixture never fully reaches
            continue
        covering = max(m(peak_x, 0.0) for _bt, _br, m in bound)
        assert covering >= float(shares.max()) - 1e-9 and covering > 0.99, (
            f"no bound layer owns the shade peaking at x={peak_x:.1f}: "
            f"cover {covering} vs tent {shares.max()}")


def test_merged_layers_still_partition_coverage():
    """The tents partition coverage (shares sum to 1 above the highlight
    cutoff — `_shade_layers`' own docstring contract); the merge must
    preserve that, not double-count the seam between merged neighbours."""
    dark_anchor = _nearest_spool_to((10, 10, 10))
    light_anchor = _nearest_spool_to((250, 250, 250))
    unbound, _ = _decomposition(None)
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    source = _source(_full_ramp())
    dark = _darkness_sampler(source)
    cfg = PipelineConfig(streamline_mode="layered")
    bound = _shade_layers(poly, source, dark, _region(poly), cfg,
                          palette_indices=[dark_anchor, light_anchor])

    for x in np.linspace(-34.0, 34.0, 200):
        d = dark(float(x), 0.0)
        total_bound = sum(m(float(x), 0.0) for _t, _r, m in bound)
        total_unbound = sum(m(float(x), 0.0) for _t, _r, m in unbound)
        if d < STREAMLINE_CUTOFF_DARKNESS:
            assert total_bound == 0.0
        else:
            assert abs(total_bound - 1.0) < 1e-9, (x, total_bound)
            assert abs(total_bound - total_unbound) < 1e-9


# --- 4. End to end through the real stage 5 + stage 7 ------------------------

def test_end_to_end_flag_flips_blocks_from_chart_wide_to_palette_only():
    """The instrument's whole claim, measured from EMITTED blocks: the same
    photo-class fixture sews 3+ chart-wide shade spools with the flag off
    (today's escape) and ONLY the planned regions' own spools with it on —
    here one region, thread 0, so every shade merges into the single honest
    layer and the plan sews exactly one block in exactly that spool."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    source = _source(_full_ramp())

    def blocks_for(bind: bool):
        cfg = PipelineConfig(fill_technique="streamline",
                             streamline_mode="layered",
                             shade_palette_bind=bind)
        planned, _ = resolve_overlaps([_region(poly, meta={"tier": "fill"})],
                                      FAB, cfg, design_class="photo_subject")
        blocks, _w = S7.sequence(planned, FAB, cfg, source_pixels=source,
                                 design_class="photo_subject")
        return blocks

    off = blocks_for(False)
    assert len({b.thread_index for b in off}) >= 3, (
        "fixture must exercise the chart-wide escape with the flag off")

    on = blocks_for(True)
    assert {b.thread_index for b in on} == {0}, (
        f"bound plan must sew only the region palette {{0}}, got "
        f"{sorted({b.thread_index for b in on})}")
    assert len(on) == 1, "all shades share one spool -> one merged block"
    assert sum(len(b.runs) for b in on) > 0, (
        "the merged layer must still sew — binding is a recolour, "
        "not a deletion")
