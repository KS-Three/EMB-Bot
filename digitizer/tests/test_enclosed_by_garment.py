"""`cfg.enclosed_by_garment` — enclosed background-coloured regions (letter
bodies, counters, donut holes: the `enclosed_background` tag) sew by default
when the GARMENT is a clearly different colour from the background they were
cut from, and stay holes when it is not. Quality review 2026-09-08 item 9;
plan and census `docs/superpowers/plans/2026-09-10-enclosed-by-garment.md`.

The 2026-08-15 verdict (`docs/enclosed-background-verdict-2026-08-15.md`)
left these unstitched because sewing white into a white polo is wrong; it
was made without knowing the garment. This flag is that missing input:
DEFAULT ON since 2026-09-10 (Kent's ruling over the renders, the same day it
was built OFF; False is the pre-flip engine byte for byte, and with no
garment colour the rule declines, so the goldens never see it), one verdict
per design
(`stage4_vectorize.garment_sews_enclosed`), a review override still wins,
and an alpha hole — whose colour nobody knows — is left exactly as before.
"""
from __future__ import annotations

import hashlib

import pytest
from shapely.geometry import Polygon

from digitizer_core import preflight
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import prep
from digitizer_core.stage4_vectorize import enforce_color_cap, garment_sews_enclosed
from digitizer_core.threads import chart_for
from tests.conftest import TESTDATA

WHITEBG = TESTDATA / "logo_whitebg.png"            # white bg, one white hole
GAULKE = TESTDATA / "photo" / "logo_gaulke_roofing.png"  # black frame -> black bg, 46 holes
ALPHA = TESTDATA / "logo_alpha.png"                # alpha cutout: hole colour unknown
UNCERTAIN = TESTDATA / "bg_uncertain.png"

WHITE, NATURAL, NAVY, BLACK = (255, 255, 255), (235, 232, 223), (28, 42, 84), (0, 0, 0)


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


def _digest(plan) -> str:
    h = hashlib.sha1()
    for b in plan.blocks:
        h.update(str(b.thread_number).encode())
        for run in b.runs:
            h.update(str(len(run.points)).encode())
            for x, y in run.points:
                h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def _enclosed(result):
    return [r for r in result.regions if r.meta.get("enclosed_background")]


def _enclosed_warning(result) -> dict:
    ws = [w for w in result.warnings if w["code"] == "BACKGROUND_ENCLOSED"]
    assert len(ws) == 1
    return ws[0]


@pytest.fixture(scope="module")
def whitebg_off():
    return digitize(WHITEBG, _cfg())


@pytest.fixture(scope="module")
def whitebg_navy():
    return digitize(WHITEBG, _cfg(enclosed_by_garment=True, garment_rgb=NAVY))


@pytest.fixture(scope="module")
def gaulke_off():
    return digitize(GAULKE, _cfg())


@pytest.fixture(scope="module")
def gaulke_natural():
    return digitize(GAULKE, _cfg(enclosed_by_garment=True, garment_rgb=NATURAL))


# --- defaults and the byte-identity off ---------------------------------------

def test_defaults_on_and_the_threshold_is_preflights_clearly_different():
    cfg = PipelineConfig()
    assert cfg.enclosed_by_garment is True      # Kent's flip, 2026-09-10
    assert cfg.garment_rgb is None
    # config.py cannot import preflight (preflight imports config), so the
    # equality is pinned here: the rule's "clearly different" IS the
    # scorecard's, not a third number.
    assert cfg.enclosed_by_garment_de00 == preflight.DELTA_E_CLEARLY_DIFFERENT == 10.0


def test_off_is_byte_identical_with_a_garment_colour_given(whitebg_off):
    """False is the pre-flip engine: a garment given and the rule OFF
    re-digitizes to the same bytes as no garment at all."""
    _, plan = digitize(WHITEBG, _cfg(enclosed_by_garment=False, garment_rgb=NAVY))
    assert _digest(plan) == _digest(whitebg_off[1])


def test_the_default_engine_on_the_studios_default_garment(whitebg_off, gaulke_natural):
    """What the flip changes for a customer who never touches the swatch:
    Natural (235, 232, 223) is 6.4 from a white hole, under the threshold,
    so whitebg is the pre-flip engine byte for byte — and 88.6 from a black
    one, so gaulke's 46 letter bodies now sew by default."""
    _, plan = digitize(WHITEBG, _cfg(garment_rgb=NATURAL))
    assert _digest(plan) == _digest(whitebg_off[1])
    _, plan_g = digitize(GAULKE, _cfg(garment_rgb=NATURAL))
    assert _digest(plan_g) == _digest(gaulke_natural[1])


def test_on_with_no_garment_colour_is_the_default_engine(whitebg_off):
    _, plan = digitize(WHITEBG, _cfg(enclosed_by_garment=True))
    assert _digest(plan) == _digest(whitebg_off[1])


# --- Prep.bg_rgb: the colour a flood hole would sew in ------------------------

def test_prep_carries_the_flood_colour_and_declines_where_it_cannot_know_it():
    assert prep(WHITEBG, PipelineConfig(target_width_mm=80.0)).bg_rgb == WHITE
    assert prep(GAULKE, PipelineConfig(target_width_mm=80.0)).bg_rgb == BLACK
    alpha = prep(ALPHA, PipelineConfig(target_width_mm=80.0))
    assert alpha.bg_from_alpha and alpha.bg_rgb is None
    # No enclosed pixels at all: the colour is known but there is nothing for
    # the rule to decide — the verdict helper returns (False, de) unused.
    unc = prep(UNCERTAIN, PipelineConfig(target_width_mm=80.0))
    assert unc.enclosed_mask is None


# --- the verdict, once per design ----------------------------------------------

def test_the_verdict_reads_the_threshold_on_de00():
    p = prep(WHITEBG, PipelineConfig(target_width_mm=80.0))
    assert garment_sews_enclosed(p, _cfg(enclosed_by_garment=False, garment_rgb=NAVY)) == (False, None)  # off
    assert garment_sews_enclosed(p, _cfg()) == (False, None)                       # ON, no garment
    sews, de = garment_sews_enclosed(p, _cfg(enclosed_by_garment=True, garment_rgb=WHITE))
    assert (sews, de) == (False, 0.0)
    sews, de = garment_sews_enclosed(p, _cfg(enclosed_by_garment=True, garment_rgb=NATURAL))
    # The Studio's default garment against a white hole: visible (over 5),
    # not clearly different (under 10) — the census's whitebg row, 6.4.
    assert not sews and preflight.DELTA_E_VISIBLE < de < preflight.DELTA_E_CLEARLY_DIFFERENT
    sews, de = garment_sews_enclosed(p, _cfg(enclosed_by_garment=True, garment_rgb=NAVY))
    assert sews and de > 50
    # Lower the bar to the visible threshold and Natural sews it — the §5
    # decision the plan puts to Kent, as one number.
    sews, _ = garment_sews_enclosed(
        p, _cfg(enclosed_by_garment=True, garment_rgb=NATURAL,
                enclosed_by_garment_de00=preflight.DELTA_E_VISIBLE))
    assert sews
    # A list from JSON is as good as a tuple.
    assert garment_sews_enclosed(p, _cfg(enclosed_by_garment=True, garment_rgb=list(NAVY)))[0]


def test_the_verdict_declines_on_an_alpha_hole():
    p = prep(ALPHA, PipelineConfig(target_width_mm=80.0))
    assert p.enclosed_mask is not None
    assert garment_sews_enclosed(p, _cfg(enclosed_by_garment=True, garment_rgb=NAVY)) == (False, None)


# --- whitebg: one white hole ---------------------------------------------------

def test_whitebg_hole_stays_a_hole_on_white_and_natural(whitebg_off):
    for garment in (WHITE, NATURAL):
        r, plan = digitize(WHITEBG, _cfg(enclosed_by_garment=True, garment_rgb=garment))
        enc = _enclosed(r)
        assert len(enc) == 1 and enc[0].meta["stitched"] is False
        assert not enc[0].meta.get("enclosed_by_garment")
        assert _digest(plan) == _digest(whitebg_off[1])
        w = _enclosed_warning(r)
        assert w["sews_by_garment"] is False and w["sewn_by_garment"] == 0
        assert "stay holes" in w["message"]


def test_whitebg_hole_sews_white_on_navy(whitebg_off, whitebg_navy):
    r, plan = whitebg_navy
    enc = _enclosed(r)
    assert len(enc) == 1
    hole = enc[0]
    assert hole.meta["stitched"] is True and hole.meta["enclosed_by_garment"] is True
    # In the thread it already carried — stage 2 quantized it from the
    # background colour, so that is White, and the plan gains its block.
    assert hole.thread_number == "0015"
    assert {b.thread_number for b in plan.blocks} - {b.thread_number for b in whitebg_off[1].blocks} == {"0015"}
    assert plan.stats.stitch_count > whitebg_off[1].stats.stitch_count
    w = _enclosed_warning(r)
    assert w["sews_by_garment"] is True and w["sewn_by_garment"] == 1
    assert w["garment_rgb"] == list(NAVY) and w["bg_rgb"] == list(WHITE)
    assert w["delta_e00"] > 50 and "SEW" in w["message"]


def test_a_review_override_still_wins_over_the_garment(whitebg_navy):
    r, _ = whitebg_navy
    sid = _enclosed(r)[0].shape_id
    r2, plan2 = digitize(WHITEBG, _cfg(enclosed_by_garment=True, garment_rgb=NAVY,
                                       shape_overrides={sid: {"stitched": False}}))
    hole = _enclosed(r2)[0]
    assert hole.shape_id == sid
    assert hole.meta["stitched"] is False
    # The rule still reports what it would have done; the override is the
    # user's, the verdict is the design's.
    assert hole.meta.get("enclosed_by_garment") is True
    assert "0015" not in {b.thread_number for b in plan2.blocks}


# --- gaulke: black frame, black background, 46 black letter bodies ------------

def test_gaulke_letter_bodies_sew_on_natural_and_stay_holes_on_black(gaulke_off, gaulke_natural):
    r_off, plan_off = gaulke_off
    r_nat, plan_nat = gaulke_natural
    assert len(_enclosed(r_off)) == len(_enclosed(r_nat)) >= 40
    assert all(x.meta["stitched"] is False for x in _enclosed(r_off))
    assert all(x.meta["stitched"] is True and x.meta["enclosed_by_garment"] for x in _enclosed(r_nat))
    assert plan_nat.stats.stitch_count > plan_off.stats.stitch_count * 1.2
    assert _enclosed_warning(r_nat)["sewn_by_garment"] == len(_enclosed(r_nat))
    # On a black garment the black bodies ARE the fabric: the default engine.
    _, plan_black = digitize(GAULKE, _cfg(enclosed_by_garment=True, garment_rgb=BLACK))
    assert _digest(plan_black) == _digest(plan_off)


# --- alpha holes are not this flag's --------------------------------------------

def test_an_alpha_hole_is_untouched_on_any_garment():
    r_off, plan_off = digitize(ALPHA, _cfg())
    r_on, plan_on = digitize(ALPHA, _cfg(enclosed_by_garment=True, garment_rgb=NAVY))
    assert _enclosed(r_off) and all(x.meta.get("enclosed_colour_unknown") for x in _enclosed(r_off))
    assert all(x.meta["stitched"] is False and not x.meta.get("enclosed_by_garment")
               for x in _enclosed(r_on))
    assert _digest(plan_on) == _digest(plan_off)
    w = _enclosed_warning(r_on)
    assert "sews_by_garment" not in w      # the rule never looked


# --- the colour cap counts a hole that sews ------------------------------------

CHART = chart_for(PipelineConfig())


def _sq(x: float, size: float) -> Polygon:
    return Polygon([(x, 0), (x + size, 0), (x + size, size), (x, size)])


def _region(sid, thread, area, *, enclosed=False, unknown=False) -> Region:
    meta = {}
    if enclosed:
        meta["enclosed_background"] = True
    if unknown:
        meta["enclosed_colour_unknown"] = True
    return Region(shape_id=sid, polygon=_sq(0.0, max(area, 0.01) ** 0.5),
                  thread_index=thread, thread_number=CHART[thread].number,
                  area_mm2=area, meta=meta)


def test_the_cap_ranks_a_sewing_hole_as_sewn_area_and_an_alpha_hole_never():
    def regions():
        return [_region("Sa", 3, 10.0), _region("Sb", 7, 2.0),
                _region("Sh", 11, 100.0, enclosed=True)]
    # Default: the hole buys no slot; the big enclosed thread 11 is remapped.
    rs = regions()
    enforce_color_cap(rs, CHART, 2)
    assert {r.thread_index for r in rs if r.shape_id != "Sh"} == {3, 7}
    assert rs[2].thread_index in (3, 7) and rs[2].meta["color_cap_merged_from"] == CHART[11].number
    # The garment rule says the holes sew: 100 mm² of thread 11 outranks 2 mm²
    # of thread 7, and the hole keeps its own cone.
    rs = regions()
    enforce_color_cap(rs, CHART, 2, count_enclosed=True)
    assert rs[2].thread_index == 11 and "color_cap_merged_from" not in rs[2].meta
    assert rs[1].thread_index in (3, 11)
    # An alpha hole never sews under the rule, so it never buys a slot.
    rs = [_region("Sa", 3, 10.0), _region("Sb", 7, 2.0),
          _region("Sh", 11, 100.0, enclosed=True, unknown=True)]
    enforce_color_cap(rs, CHART, 2, count_enclosed=True)
    assert rs[2].thread_index in (3, 7)
