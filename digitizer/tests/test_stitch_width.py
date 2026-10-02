"""Per-shape stitch width (`digitizer_core/stitchwidth.py`, contract v1.8,
2026-09-29).

What this file pins, in the order it would cost the shop if it broke:

- with nothing overridden, the pass changes NOTHING a fixture sews — on the
  two real-lettering art fixtures whose words it WOULD even out with
  `stitch_width_auto` on — and every column still gets a measured width for
  the panel to show;
- the guards: a hole is held open, a gap between strokes is never bridged,
  a narrowing that would split the shape is clamped, and a change under a
  hair is no change;
- the letters of one word take the word's median width, and only when their
  own reading is off it; a word is never widened by a neighbouring shape;
- a review-screen `stitch_width_mm` sets the SEWN column outright, both
  ways, and end to end the bars it names sew as satin columns of that
  width where they sewed as bean runs;
- the wire rejects a bad value with a 400 that names the range, and the
  review payload reports the block the Studio reads.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, stitches
from digitizer_core import stitchwidth as sw
from digitizer_core.pipeline import digitize, fabric_for
from digitizer_core.regions import Region, apply_shape_edits
from digitizer_core.stage5_overlap import widened_lettering
from digitizer_core.threads import CHART

from .conftest import TESTDATA
from .test_widened_lettering_tier import _satin_columns_of, _thin_bars

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

ART = TESTDATA / "logo_whitebg.png"


# --- helpers --------------------------------------------------------------------

def _region(poly: Polygon, sid: str = "S1", **meta) -> Region:
    return Region(sid, poly, 0, CHART[0].number, poly.area, meta={"layer": 0, **meta})


def _ring(r_out: float, r_in: float, n: int = 48) -> Polygon:
    outer = [(r_out * math.cos(2 * math.pi * k / n), r_out * math.sin(2 * math.pi * k / n)) for k in range(n)]
    inner = [(r_in * math.cos(2 * math.pi * k / n), r_in * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return Polygon(outer, [inner])


def _letter_e(stroke: float = 0.4, gap: float = 1.4) -> Polygon:
    """A stem and three arms; the arms sit `gap` apart."""
    stem = box(0, 0, stroke, 2 * gap + 3 * stroke)
    arms = [box(0, y, 2.0, y + stroke) for y in (0, gap + stroke, 2 * (gap + stroke))]
    return unary_union([stem] + arms)


def _plan_md5(plan) -> str:
    h = hashlib.md5()
    for _b, run in plan.iter_runs():
        h.update(run.kind.encode())
        for x, y in run.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


# --- measurement and units ----------------------------------------------------------

def test_a_bar_measures_its_own_width_and_sewn_adds_the_pull_on_both_rails():
    w = sw.measure_width_mm(box(0, 0, 0.6, 8.0))
    assert w is not None and abs(w - 0.6) <= 0.15 * 0.6, w
    assert sw.sewn_width_mm(0.6, 0.2) == pytest.approx(1.0)
    assert sw.art_width_mm(1.0, 0.2) == pytest.approx(0.6)
    assert sw.art_width_mm(0.2, 0.2) == 0.0          # never negative


def test_measure_pass_records_a_width_on_column_shapes_and_leaves_fill_alone():
    bar = _region(box(0, 0, 0.5, 6.0), "bar")
    slab = _region(box(10, 10, 60, 60), "slab")
    sw.measure_stitch_widths([bar, slab], satin_max=5.0)
    assert sw.MEASURED_KEY in bar.meta
    assert sw.MEASURED_KEY not in slab.meta            # 2*area/perimeter = 25 mm: never a column
    assert sw.review_block(slab)["measured_mm"] is None


# --- the guards --------------------------------------------------------------------

def test_a_change_under_a_hair_is_no_change():
    poly = box(0, 0, 0.5, 6.0)
    out, applied, reason = sw.offset_polygon(poly, sw.MIN_DELTA_MM / 2)
    assert out is poly and applied == 0.0 and reason == "no_change"


def test_widening_never_bridges_the_gaps_between_strokes():
    e = _letter_e(stroke=0.4, gap=1.4)
    # 0.3 mm per side closes 0.6 of a 1.4 gap: fine, in full.
    out, applied, reason = sw.offset_polygon(e, 0.3)
    assert reason is None and applied == pytest.approx(0.3)
    assert out.is_valid and not out.interiors
    # 0.8 per side would close 1.6 of it: clamped to under half the gap.
    out, applied, reason = sw.offset_polygon(e, 0.8)
    assert reason is None and 0.5 <= applied < 0.7, applied
    assert not out.interiors, "a bridged gap shows up as a new hole"


def test_widening_holds_a_counter_open_where_growth_would_close_it():
    o = _ring(1.5, 1.1)
    out, applied, reason = sw.offset_polygon(o, 0.5)
    assert reason is None and applied == pytest.approx(0.5)
    assert len(out.interiors) == 1
    assert Polygon(out.interiors[0]).area == pytest.approx(math.pi * 0.6 ** 2, rel=0.05)
    # 1.0 per side would leave a 0.1 mm hole (0.03 mm², under the floor):
    # the hole is held at its ORIGINAL size instead of closing.
    out, applied, reason = sw.offset_polygon(o, 1.0)
    assert reason is None and len(out.interiors) == 1
    assert Polygon(out.interiors[0]).area == pytest.approx(math.pi * 1.1 ** 2, rel=0.05)


def test_narrowing_stops_short_of_splitting_or_vanishing():
    o = _ring(1.5, 1.1)          # a 0.4 mm ring
    out, applied, reason = sw.offset_polygon(o, -0.1)
    assert reason is None and applied == pytest.approx(-0.1) and len(out.interiors) == 1
    out, applied, reason = sw.offset_polygon(o, -0.3)   # past half the stroke
    assert out is not None and reason is None and -0.2 < applied < 0.0, applied
    # A dumbbell: two 3 mm discs joined by a 0.3 mm neck. Erode past the
    # neck and the shape would split — refused before it does.
    bell = unary_union([box(0, 0, 3, 3), box(5, 0, 8, 3), box(3, 1.35, 5, 1.65)])
    out, applied, reason = sw.offset_polygon(bell, -0.5)
    assert out is not None and out.geom_type == "Polygon" and -0.15 <= applied < 0.0, (applied, reason)


# --- the auto decision ----------------------------------------------------------------

def test_the_letters_of_one_word_take_its_median_and_a_neighbour_does_not():
    bars = [_region(box(4 * k, 0, 4 * k + 0.3, 3.0), f"b{k}", text_cluster_id="W") for k in range(4)]
    fat = _region(box(16, 0, 16.38, 3.0), "fat", text_cluster_id="W")     # traced a quarter heavier
    other = _region(box(30, 0, 30.3, 3.0), "other")                          # same size, not in the word
    regions = bars + [fat, other]
    sw.measure_stitch_widths(regions, satin_max=5.0)
    assert {r.meta[sw.GROUP_KEY] for r in bars + [fat]} == {"W"}
    assert sw.GROUP_KEY not in other.meta
    shared = bars[0].meta[sw.AUTO_KEY]
    assert all(r.meta[sw.AUTO_KEY] == shared for r in bars + [fat])
    assert abs(shared - 0.3) <= 0.05, shared

    # Off (the default): the word is named, nothing moves.
    assert sw.apply_stitch_widths(regions, pull_mm=0.0) == 0
    assert fat.meta[sw.SOURCE_KEY] == "shape" and sw.SIZED_KEY not in fat.meta
    moved = sw.apply_stitch_widths(regions, pull_mm=0.0, auto=True)
    assert moved == 1
    assert fat.meta[sw.SOURCE_KEY] == "group" and abs(fat.meta[sw.SIZED_KEY] - shared) <= 0.02
    assert fat.meta[sw.DELTA_KEY] < 0 and widened_lettering(fat)
    for r in bars:                    # within tolerance of the median: untouched
        assert sw.SIZED_KEY not in r.meta and not widened_lettering(r)
    assert sw.SIZED_KEY not in other.meta and sw.SOURCE_KEY in other.meta


def test_two_weights_on_one_line_are_two_groups_and_neither_word_moves():
    """Gaulke Roofing's line (2026-09-29 survey): eight letters at ~0.78 mm and
    thirteen at ~1.2 mm in ONE text cluster. A single median (0.95) moved all
    twenty-one to a width neither word has."""
    light = [_region(box(3 * k, 0, 3 * k + 0.78 + 0.01 * k, 4.0), f"l{k}", text_cluster_id="LINE") for k in range(5)]
    bold = [_region(box(30 + 3 * k, 0, 30 + 3 * k + 1.2 + 0.02 * k, 4.0), f"b{k}", text_cluster_id="LINE") for k in range(6)]
    lone = [_region(box(60, 0, 62.0, 4.0), "lone", text_cluster_id="LINE")]     # a 2 mm bar: its own weight
    regions = light + bold + lone
    sw.measure_stitch_widths(regions, satin_max=5.0)
    modes = sw.split_weight_modes(regions)
    assert [len(m) for m in modes] == [5, 6, 1]
    assert len({r.meta[sw.GROUP_KEY] for r in light}) == 1
    assert len({r.meta[sw.GROUP_KEY] for r in bold}) == 1
    assert light[0].meta[sw.GROUP_KEY] != bold[0].meta[sw.GROUP_KEY] != lone[0].meta[sw.GROUP_KEY]
    assert sw.AUTO_KEY not in lone[0].meta                       # shares with nobody
    assert 1.4 < bold[0].meta[sw.AUTO_KEY] / light[0].meta[sw.AUTO_KEY] < 1.7
    assert sw.apply_stitch_widths(regions, pull_mm=0.0, auto=True) == 0     # every letter already its word's weight


def test_a_chain_of_weights_is_cut_at_its_largest_steps_until_every_mode_fits():
    """Neighbours each inside the ratio, ends 2x apart: single-linkage kept
    all five together (reviewer, 2026-09-29) and moved four of them."""
    widths = [0.54, 0.64, 0.78, 0.92, 1.08]
    regions = [_region(box(4 * k, 0, 4 * k + w, 4.0), f"c{k}", text_cluster_id="C") for k, w in enumerate(widths)]
    sw.measure_stitch_widths(regions, satin_max=5.0)
    modes = sw.split_weight_modes(regions)
    for mode in modes:
        ws = [m.meta[sw.MEASURED_KEY] for m in mode]
        assert max(ws) <= min(ws) * sw.WEIGHT_SPLIT_RATIO + 1e-9
    assert 2 <= len(modes) <= 3


def test_the_floor_reaches_small_shapes_and_lettering_but_not_a_big_ribbon():
    pull = 0.3
    small = _region(box(0, 0, 0.3, 3.0), "small")                                  # 3 mm tall: small
    letter = _region(box(10, 0, 0.3 + 10, 8.0), "letter", text_cluster_id="W")   # tall, but lettering
    ribbon = _region(box(20, 0, 20.3, 12.0), "ribbon")                             # a 12 mm hairline: not small
    regions = [small, letter, ribbon]
    sw.measure_stitch_widths(regions, satin_max=5.0)
    assert sw.apply_stitch_widths(regions, pull_mm=pull, auto=True) == 0          # no floor: nothing moves
    # The floor alone keeps its 2026-09-09 meaning (door-1 only, upstream):
    # it reaches these shapes only with auto on.
    assert sw.apply_stitch_widths(regions, pull_mm=pull, floor_sewn_mm=1.0) == 0
    assert sw.apply_stitch_widths(regions, pull_mm=pull, floor_sewn_mm=1.0, auto=True) == 2
    for r in (small, letter):
        assert r.meta[sw.SOURCE_KEY] == "floor"
        assert r.meta[sw.SIZED_KEY] == pytest.approx(1.0 - 2 * pull, abs=0.03)
        assert sw.review_block(r)["sewn_mm"] == pytest.approx(1.0, abs=0.05)
    assert sw.SIZED_KEY not in ribbon.meta and ribbon.meta[sw.SOURCE_KEY] == "shape"


def test_auto_leaves_forced_fill_hand_edited_and_unstitched_shapes_alone():
    fill = _region(box(0, 0, 0.3, 3.0), "fill", tier="fill", text_cluster_id="W")
    hand = _region(box(5, 0, 5.3, 3.0), "hand", boundary_override=[(0, 0)], text_cluster_id="W")
    off = _region(box(10, 0, 10.3, 3.0), "off", stitched=False, text_cluster_id="W")
    fat = _region(box(15, 0, 15.38, 3.0), "fat", text_cluster_id="W")
    thin = _region(box(20, 0, 20.3, 3.0), "thin", text_cluster_id="W")
    regions = [fill, hand, off, fat, thin]
    sw.measure_stitch_widths(regions, satin_max=5.0)
    sw.apply_stitch_widths(regions, pull_mm=0.0, auto=True)
    assert sw.SIZED_KEY not in fill.meta and sw.SOURCE_KEY not in fill.meta
    assert hand.meta[sw.SKIP_KEY] == "hand_edited_outline" and sw.SIZED_KEY not in hand.meta
    assert sw.SIZED_KEY not in off.meta and sw.SOURCE_KEY not in off.meta
    assert sw.SIZED_KEY in fat.meta        # the one ordinary member off its word's weight moves
    assert sw.SIZED_KEY not in thin.meta


def test_an_override_sets_the_sewn_width_both_ways_and_beats_the_group():
    pull = 0.2
    a = _region(box(0, 0, 0.4, 3.0), "a", text_cluster_id="W")
    b = _region(box(5, 0, 5.4, 3.0), "b", text_cluster_id="W")
    regions = [a, b]
    sw.measure_stitch_widths(regions, satin_max=5.0)
    a.meta[sw.OVERRIDE_KEY] = 1.2
    b.meta[sw.OVERRIDE_KEY] = 0.6
    assert sw.apply_stitch_widths(regions, pull_mm=pull) == 2
    assert a.meta[sw.SOURCE_KEY] == "override" and a.meta[sw.SIZED_KEY] == pytest.approx(1.2 - 2 * pull, abs=0.03)
    assert b.meta[sw.SOURCE_KEY] == "override" and b.meta[sw.SIZED_KEY] == pytest.approx(0.6 - 2 * pull, abs=0.03)
    assert a.polygon.area > 0.4 * 3.0 and b.polygon.area < 0.4 * 3.0
    blk = sw.review_block(a)
    assert blk["override_mm"] == 1.2 and blk["sewn_mm"] == pytest.approx(1.2, abs=0.05)
    assert blk["measured_mm"] == pytest.approx(0.4 + 2 * pull, abs=0.05) and blk["group"] == "W"
    # A merged shape minted after the measurement pass is measured late, so
    # the panel can offer it the control; with an override it applies.
    late = _region(box(9, 0, 9.4, 3.0), "late")
    assert sw.apply_stitch_widths([late], pull_mm=0.0) == 0 and sw.MEASURED_KEY in late.meta
    late.meta[sw.OVERRIDE_KEY] = 1.0
    assert sw.apply_stitch_widths([late], pull_mm=0.0) == 1


def test_narrowing_never_erases_a_stroke_thinner_than_the_step():
    """An E with a 0.8 mm stem and 0.25 mm arms, narrowed 0.15 per side:
    the arms went and the E sewed as an I (reviewer, 2026-09-29)."""
    stem = box(0, 0, 0.8, 4.0)
    arms = [box(0, y, 2.4, y + 0.25) for y in (0, 1.875, 3.75)]
    e = unary_union([stem] + arms)
    out, applied, reason = sw.offset_polygon(e, -0.15)
    x0, _y0, x1, _y1 = (out.bounds if out is not None else (0, 0, 0, 0))
    assert out is None or (x1 - x0) > 2.0, (applied, reason, x1 - x0)   # the arms survive, or nothing moves
    assert reason is not None or abs(applied) < 0.125                     # a step under half an arm at most


def test_an_override_the_fabric_pull_alone_exceeds_is_a_named_skip():
    a = _region(box(0, 0, 0.4, 3.0), "a")
    sw.measure_stitch_widths([a], satin_max=5.0)
    a.meta[sw.OVERRIDE_KEY] = 0.5
    assert sw.apply_stitch_widths([a], pull_mm=0.3) == 0      # 2 x 0.3 = 0.6 > 0.5
    assert a.meta[sw.SKIP_KEY] == "below_fabric_pull" and sw.SIZED_KEY not in a.meta
    assert sw.review_block(a)["skip_reason"] == "below_fabric_pull"


def test_the_auto_flag_defaults_off_and_rides_the_wire():
    from digitizer_service.app import _CONFIG_FIELDS
    assert PipelineConfig().stitch_width_auto is False
    assert "stitch_width_auto" in _CONFIG_FIELDS


def test_a_limited_override_is_reported_as_limited():
    e = _region(_letter_e(stroke=0.4, gap=1.4), "e")
    sw.measure_stitch_widths([e], satin_max=5.0)
    e.meta[sw.OVERRIDE_KEY] = 2.5       # +1.05 per side; the gap allows < 0.7
    assert sw.apply_stitch_widths([e], pull_mm=0.0) == 1
    assert e.meta[sw.LIMITED_KEY] is True and sw.review_block(e)["limited"] is True
    assert e.meta[sw.SIZED_KEY] < 2.5


# --- the wire's half ------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["0.8", True, float("nan"), 0.49, 6.51, -1])
def test_validate_override_rejects_what_the_machine_cannot_sew(bad):
    with pytest.raises(ValueError, match="stitch_width_mm"):
        sw.validate_override_mm(bad)
    assert sw.validate_override_mm(0.5) == 0.5 and sw.validate_override_mm(6.5) == 6.5


def test_apply_shape_edits_writes_the_override_and_refuses_a_bad_one():
    r = _region(box(0, 0, 0.4, 3.0), "S1")
    regions, _idx, warnings = apply_shape_edits([r], [0], [], {"S1": {"stitch_width_mm": 0.9}}, CHART)
    assert regions[0].meta[sw.OVERRIDE_KEY] == 0.9 and not warnings
    with pytest.raises(ValueError, match=r"shape_overrides\['S1'\]\.stitch_width_mm"):
        apply_shape_edits([_region(box(0, 0, 0.4, 3.0), "S1")], [0], [], {"S1": {"stitch_width_mm": 9}}, CHART)


def test_the_service_400s_a_bad_stitch_width_naming_the_range(client):
    for bad in ("0.8", 0.2, 12):
        with ART.open("rb") as f:
            r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                            data={"config": json.dumps({"shape_overrides": {"Sx": {"stitch_width_mm": bad}}})})
        assert r.status_code == 400, r.text
        assert "stitch_width_mm" in r.json()["detail"]
    from digitizer_service.app import _OVERRIDE_KEYS
    assert "stitch_width_mm" in _OVERRIDE_KEYS


def test_the_review_payload_carries_the_stitch_width_block(client):
    from .test_service import _digitize
    state = _digitize(client, {"target_width_mm": 80.0})
    shapes = state["review"]["shapes"]
    assert all("stitch_width" in s for s in shapes)
    keys = {"art_mm", "measured_mm", "auto_mm", "sewn_mm", "override_mm", "source", "group", "limited", "skip_reason"}
    assert all(set(s["stitch_width"]) == keys for s in shapes)
    measured = [s for s in shapes if s["stitch_width"]["measured_mm"] is not None]
    assert measured, "the logo's thin bar and ring are columns and must be measured"
    assert all(s["stitch_width"]["source"] in (None, "shape", "group") for s in shapes)
    assert all(s["stitch_width"]["override_mm"] is None for s in shapes)
    # And an override on a real shape comes back as the override in effect,
    # on a shape the plan sews wider than before.
    narrowest = min(measured, key=lambda s: s["stitch_width"]["sewn_mm"])
    sid = narrowest["shape_id"]
    before = narrowest["stitch_width"]["sewn_mm"]
    target = min(6.5, before + 1.0)
    assert target > before
    state2 = _digitize(client, {"target_width_mm": 80.0,
                                "shape_overrides": {sid: {"stitch_width_mm": target}}})
    row = next(s for s in state2["review"]["shapes"] if s["shape_id"] == sid)
    assert row["stitch_width"]["source"] == "override"
    assert row["stitch_width"]["override_mm"] == pytest.approx(target)
    assert row["stitch_width"]["sewn_mm"] > before


# --- end to end ---------------------------------------------------------------------------

@pytest.mark.parametrize("art, moves_when_on", [
    ("art/logo_hotel_fremont_patch.png", False),
    ("art/logo_golke_roofing.png", True),
])
@pytest.mark.usefixtures("source_line_grid")
def test_with_nothing_asked_the_pass_changes_no_stitch_on_real_lettering(art, moves_when_on):
    """Two real-lettering fixtures with detected words, so the equality here
    is not vacuous: with the flag off, the plan is the plan without the pass.
    With it on, Golke's chain of weights moves letters (the reason the flag is
    off); Fremont's words sit inside the tolerance once the chain is cut at
    its steps, and nothing moves there either way."""
    path = TESTDATA / art
    result, plan = digitize(path, PipelineConfig(target_width_mm=80.0))
    with patch.object(sw, "offset_polygon", lambda poly, d: (poly, 0.0, "no_change")):
        _r2, plan_off = digitize(path, PipelineConfig(target_width_mm=80.0))
    assert _plan_md5(plan) == _plan_md5(plan_off)
    assert not any(widened_lettering(r) for r in result.regions)
    grouped = [r for r in result.regions if r.meta.get(sw.GROUP_KEY)]
    assert grouped and all(sw.MEASURED_KEY in r.meta for r in grouped)
    assert all(r.meta.get(sw.SOURCE_KEY) == "shape" for r in grouped)
    # And with the flag ON, something in a word moves — the arm the flag guards.
    on, plan_on = digitize(path, PipelineConfig(target_width_mm=80.0, stitch_width_auto=True))
    moved = [r for r in on.regions if r.meta.get(sw.SOURCE_KEY) == "group" and sw.SIZED_KEY in r.meta]
    if moves_when_on:
        assert moved and _plan_md5(plan_on) != _plan_md5(plan)
    else:
        assert not moved and _plan_md5(plan_on) == _plan_md5(plan)


def test_an_override_on_the_thin_bars_sews_them_as_columns_of_that_width(tmp_path):
    """The bars of `test_widened_lettering_tier` — sub-floor, sewn as bean
    runs by default — with `stitch_width_mm` 1.0 on each: satin columns a
    millimetre wide, read off the crosses, with no floor flag set."""
    art = tmp_path / "bars.png"
    _thin_bars(art)
    base = PipelineConfig(target_width_mm=50.0, garment_id="left_chest")
    off, off_plan = digitize(art, base)
    bars = [r for r in off.regions if r.meta.get("text_cluster_id")]
    assert len(bars) >= 5
    kinds_off = {}
    ids = {r.shape_id for r in bars}
    for _b, run in off_plan.iter_runs():
        if run.shape_id in ids:
            kinds_off[run.kind] = kinds_off.get(run.kind, 0) + len(run.points)
    assert kinds_off.get(stitches.SATIN, 0) == 0 and kinds_off.get(stitches.RUN, 0) > 0, kinds_off

    on_cfg = PipelineConfig(target_width_mm=50.0, garment_id="left_chest",
                            shape_overrides={sid: {"stitch_width_mm": 1.0} for sid in ids})
    on, on_plan = digitize(art, on_cfg)
    sized = [r for r in on.regions if r.shape_id in ids]
    assert all(r.meta.get(sw.SOURCE_KEY) == "override" and sw.SIZED_KEY in r.meta for r in sized), \
        [(r.shape_id, r.meta.get(sw.SOURCE_KEY), r.meta.get(sw.SKIP_KEY)) for r in sized]
    pull = fabric_for(on_cfg).pull_comp_mm
    for r in sized:
        assert r.meta[sw.SIZED_KEY] == pytest.approx(1.0 - 2 * pull, abs=0.03)
    m = _satin_columns_of(on_plan, sized)
    assert m["columns"] >= 5 * 6, m
    assert 0.8 <= m["median_mm"] <= 1.25, m
