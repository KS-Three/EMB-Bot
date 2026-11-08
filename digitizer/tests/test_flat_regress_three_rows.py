"""The three wrong-way tripwire rows #1321 pinned on `stage0_scale_relative_grad`
without a region-level cause (`docs/flat-regress-three-rows-2026-11-07.md`).
Measurement only: nothing here moves a default or calibrates a gate.

Each row gets a LANE CLASS from the doc's two arms (shipped defaults vs
`stage0_scale_relative_grad` False, through `tools.pro_pair.digitize` at the
pro's width) and a width-jitter check (the same two arms at the pro's width
+-0.1 and +-0.2 mm):

- ``gaulke_roofing_hat`` trims 30 -> 32: ROUTE. Both lanes hand stage 7 the
  same 53 regions (by shape id) and their polygons differ by 0.72 mm2 in all;
  the sew route through the lettering diverges at lift 11 of 45, and two
  more letter entries land past the trim. From -0.2 to +0.2 mm of width the
  flat-minus-gradient trim delta is 0 / -2 / +2 / +2 / 0: the sign is not
  the lane's.
- ``hotel_fremont_patch`` trims 20 -> 24: CURED on main by
  `flat_light_text_runs` (#1328, ON in #1329). On today's main both arms read
  20 trims, 175 hops, 475.9 mm; the 24 / 149 / 467.3 of #1321 comes back
  only with that switch off, because the flat lane then has no dark-ink
  labels on the patch's tan small text.
- ``mfab_lc`` needle-up 345.2 -> 389.3 mm: ROUTE. The +44.1 mm is the white
  block's entry (+58.2), the white keyline's own route (+40.3) and the black
  body's (-57.7). From -0.2 to +0.2 mm of width the delta is
  -17.8 / -87.4 / +44.1 / -32.3 / +73.4.

Pinned here: the population, the stage-0 route of all three, Fremont patch's
flat-lane dark-ink read (on with the switch, none without), Gaulke's
same-regions fact (full stages 0-6, both arms), and the doc's attributed
deltas against today's ledger, so a re-seed that moves a row marks the doc
stale. Polygon and count bounds carry headroom for a Linux runner.
"""
from __future__ import annotations

import dataclasses
import json

import pytest

from digitizer_core import stage0_classify as s0

from .conftest import TESTDATA

#: slug -> (art, garment, the pro's width mm), as `tools.pro_baseline.JOBS`
JOBS = {
    "gaulke_roofing_hat": (TESTDATA / "photo" / "logo_gaulke_roofing.png", "hat_front", 114.2),
    "hotel_fremont_patch": (TESTDATA / "photo" / "logo_hotel_fremont.webp", "patch", 92.5),
    "mfab_lc": (TESTDATA / "art" / "logo_mfab_lc.png", "left_chest", 96.7),
}

#: The doc's measurement (Windows, main 21b8b57d), machine-file figures read
#: back from each arm's DST the way `tools.pro_baseline` reads them.
#: figure -> (gradient arm, flat arm as shipped, lane class)
ROWS = {
    ("gaulke_roofing_hat", "trims"): (30, 32, "route"),
    ("hotel_fremont_patch", "trims"): (20, 20, "cured by flat_light_text_runs"),
    ("mfab_lc", "needle_up_mm"): (345.2, 389.3, "route"),
}

#: Per-row delta by region kind (the doc's tables; the needle-up and trim of
#: a lift belong to the shape the needle lands on). Each row's kinds sum to
#: its total delta; "unowned" is a run whose shape id names no region.
#: Fremont patch's row is #1321's arm (flat lane with flat_light_text_runs
#: off) against the gradient arm, matched by shape id, kind from the
#: gradient arm.
ATTRIBUTION = {
    ("gaulke_roofing_hat", "trims"): {"lettering, drawn": 2, "body": 0, "unowned": 0},
    ("hotel_fremont_patch", "trims"): {"lettering, drawn": 3, "lettering, rescued small text": 1,
                                       "rescued speck": 0, "dark-ink read": 0, "body": 0,
                                       "unowned": 0},
    ("mfab_lc", "needle_up_mm"): {"enclosed white (keyline + counters)": 99.3, "body": -57.7,
                                  "lettering, drawn": -4.4, "lettering, rescued small text": 6.8,
                                  "unowned": 0.0},
}
TOTALS = {("gaulke_roofing_hat", "trims"): 2, ("hotel_fremont_patch", "trims"): 4,
          ("mfab_lc", "needle_up_mm"): 44.1}

#: flat-minus-gradient delta at the pro's width -0.2, -0.1, 0, +0.1, +0.2 mm
#: The sign is not stable on either route row.
JITTER = {
    ("gaulke_roofing_hat", "trims"): (0, -2, 2, 2, 0),
    ("mfab_lc", "needle_up_mm"): (-17.8, -87.4, 44.1, -32.3, 73.4),
}


def _cfg(slug: str, extra: dict | None = None):
    from tools import pro_pair as pp
    _art, garment, width = JOBS[slug]
    return pp.config(width, garment, extra)


def _pixels(slug: str):
    from digitizer_service.app import _decode
    return _decode(JOBS[slug][0].read_bytes())


def test_the_jobs_match_the_tripwire_population():
    from tools.pro_baseline import JOBS as PB
    for slug, (art, garment, width) in JOBS.items():
        g, w, spec, *_ = PB[slug]
        assert (g, w) == (garment, width)
        assert spec == "testdata:" + art.relative_to(TESTDATA).as_posix()


@pytest.mark.parametrize("slug", sorted(JOBS))
def test_stage0_routes_each_job_flat_on_and_gradient_off(slug):
    cfg = _cfg(slug)
    assert cfg.stage0_scale_relative_grad is True
    px = _pixels(slug)
    on = s0.classify(px, cfg)
    off = s0.classify(px, dataclasses.replace(cfg, stage0_scale_relative_grad=False))
    assert (on.class_, off.class_) == ("flat", "gradient")


def test_the_doc_rows_are_todays_ledger_baselines():
    """The flat arm the doc attributes IS the tripwire's floor today. A
    re-seed that moves one of these rows fails here: re-measure the doc."""
    from tools.tripwire import LEDGER  # noqa: F401  (the ledger's own path)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    base = {(r["job"], r["figure"]): r["baseline"] for r in ledger["rows"]}
    for key, (_grad, flat, _cls) in ROWS.items():
        assert base[key] == pytest.approx(flat, abs=0.05), key


def test_every_row_is_at_least_90_percent_attributed_to_named_kinds():
    for key, parts in ATTRIBUTION.items():
        total = TOTALS[key]
        assert sum(parts.values()) == pytest.approx(total, abs=0.15), key
        assert abs(parts["unowned"]) <= 0.10 * abs(total), key
    for key, (grad, flat, cls) in ROWS.items():
        if cls == "route":
            assert flat - grad == pytest.approx(TOTALS[key], abs=0.05)


def test_route_rows_change_sign_within_a_fifth_of_a_millimetre_of_width():
    for key, deltas in JITTER.items():
        seen = [d for d in deltas if d is not None]
        assert min(seen) < 0 < max(seen), key
        assert ROWS[key][2] == "route"


def test_fremont_patch_flat_lane_reads_dark_ink_only_with_the_switch():
    """`flat_light_text_runs` gives the flat lane the gradient lane's dark-ink
    carve. On the patch it finds the tan small text; without it the flat
    quantiser has no dark-ink labels and the patch sews #1321's 24 trims."""
    from digitizer_core import two_tone
    from digitizer_core.stage1_prep import prep
    from digitizer_core.stage2_quantize import quantize
    from digitizer_core.thin_ink import carve_flat_dark_ink
    cfg = _cfg("hotel_fremont_patch")
    assert cfg.flat_light_text_runs is True and cfg.keep_dark_thin_strokes
    p = prep(_pixels("hotel_fremont_patch"), cfg, design_class="flat")
    if cfg.two_tone_snap:
        two_tone.apply(p)
    q = quantize(p, cfg)
    assert not q.dark_ink_labels
    carved = carve_flat_dark_ink(p, cfg, q)
    assert carved.dark_ink_labels


def _regions(slug: str, extra: dict):
    from digitizer_core.pipeline import build_generation, finish_generation
    cfg = _cfg(slug, extra)
    gen = build_generation(_pixels(slug), cfg, exif_source=JOBS[slug][0].read_bytes())
    res = finish_generation(gen.fork(), cfg)
    return res.design_class, {r.shape_id: r for r in res.regions}


def test_gaulke_both_lanes_hand_stage7_the_same_regions():
    """53 regions on each lane, the same shape ids, 0.72 mm2 of polygon
    change in all (max 0.27 mm2, one letter). The +2 trims are the route
    through the lettering, not a region the flat lane adds or splits."""
    cls_on, on = _regions("gaulke_roofing_hat", {})
    cls_off, off = _regions("gaulke_roofing_hat", {"stage0_scale_relative_grad": False})
    assert (cls_on, cls_off) == ("flat", "gradient")
    assert len(on) == len(off)
    shared = set(on) & set(off)
    assert len(shared) >= 0.95 * len(on)
    moved = [on[k].polygon.symmetric_difference(off[k].polygon).area for k in shared]
    assert sum(moved) < 3.0
    assert max(moved) < 1.0
