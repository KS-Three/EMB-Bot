"""tools/lane_census.py: which lane each route reaches, pinned on two committed fixtures.

MEASUREMENT ONLY (ROADMAP gate 2). Nothing here changes routing or touches an engine
file; the 6b arm is measured by a shim that wraps four names in
`digitizer_core.pipeline` for one `with` and puts them back. The tests pin:

  * the 6b text the doc quotes is the plan's, word for word;
  * the one gate Kent's 6b and the planner's variant share, case by case;
  * the shim swaps the region former only where the gate fires, and leaves the
    pipeline exactly as it found it;
  * on Becker's left-chest job and Hotel Fremont's hat (both committed, at their pro
    width and garment, under the Studio's request) the lane each arm reaches, and that
    the 6b arm segments with the flat quantizer if and only if the gate fires on that
    job's auto facts.
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import lane_census as lc

REPO = Path(__file__).resolve().parents[2]


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ----------------------------------------------------------------- the quote
def test_the_6b_text_is_the_plans_word_for_word():
    plan = _squash(lc.PLAN_FILE.read_text(encoding="utf-8"))
    assert _squash(lc.SIXB_TEXT) in plan


# ------------------------------------------------------------------ the gate
def _facts(**kw) -> dict:
    base = {"class": "gradient", "ramp": "none", "ramp_enabled": True, "photographic": False,
            "faces_routed_flat": False, "segmenter": None}
    base.update(kw)
    return base


def test_gate_fires_on_a_refused_gradient_that_is_not_a_photograph():
    fires, why = lc.sixb_gate(_facts())
    assert fires and "refused" in why


@pytest.mark.parametrize("kw, reason", [
    ({"class": "flat"}, "stage 0 says flat"),
    ({"class": "photo_subject"}, "photo_subject"),
    ({"ramp": "fitted"}, "FITS"),
    ({"photographic": True}, "photographic"),
    ({"ramp_enabled": False}, "off"),
    ({"class": "flat", "faces_routed_flat": True}, "flat"),
])
def test_gate_stays_shut_everywhere_else(kw, reason):
    fires, why = lc.sixb_gate(_facts(**kw))
    assert not fires and reason in why


def test_planner_and_6b_share_one_gate_and_differ_only_in_what_they_run():
    shut, open_ = _facts(ramp="fitted"), _facts()
    assert lc.planner_arm(shut) == "auto" and lc.sixb_arm(shut) == "auto"
    assert lc.planner_arm(open_) == "flat"       # the planner's variant is the WHOLE flat route
    assert lc.sixb_arm(open_) == "sixb"          # Kent's text is a segmenter swap, its own run


def test_effective_row_is_a_pick_where_the_gate_is_shut_and_its_own_run_where_it_fires():
    auto = {"arm": "auto", "facts": _facts(ramp="fitted")}
    flat = {"arm": "flat", "facts": _facts(class_="flat")}
    row, how = lc.effective_row({"auto": auto, "flat": flat}, "planner")
    assert row is auto and how == "= auto"
    row, how = lc.effective_row({"auto": auto, "flat": flat}, "sixb")
    assert row is auto and how == "= auto"
    fired = {"arm": "auto", "facts": _facts()}
    sixb = {"arm": "sixb", "facts": _facts()}
    assert lc.effective_row({"auto": fired, "flat": flat, "sixb": sixb}, "planner")[0] is flat
    assert lc.effective_row({"auto": fired, "flat": flat, "sixb": sixb}, "sixb") == (sixb, "own")
    assert lc.effective_row({"auto": fired, "flat": flat}, "sixb")[0] is None   # not run yet


# ---------------------------------------------------------------------- arms
def test_the_flat_arm_is_the_flip_sheet_proxy_and_the_studio_button():
    from tools.flip_sheet import PROXIES
    assert lc.arm_extra("flat") == PROXIES["flat_off"] == {"forced_class": "flat"}
    assert lc.arm_extra("auto") == {} and lc.arm_extra("sixb") == {}
    with pytest.raises(ValueError):
        lc.arm_extra("planner")      # a pick, not a run


def test_every_arm_is_the_studio_request_at_the_pro_width_and_garment():
    job = lc.pinned_job("becker_lc_large")
    for arm in lc.RUN_ARMS:
        req = lc.studio_request(job, arm)
        assert req["detect_photographic"] is True and req["faces_route_flat"] is True
        assert req["max_colors"] == lc.STUDIO_MAX_COLORS == 6
        assert req["target_width_mm"] == 95.7 and req["garment_id"] == "left_chest"
        assert (req.get("forced_class") == "flat") == (arm == "flat")


# ------------------------------------------------------------------ counting
def _plan(*blocks):
    return SimpleNamespace(blocks=[
        SimpleNamespace(thread_number=n, runs=[SimpleNamespace(points=pts) for pts in runs])
        for n, runs in blocks])


def test_cones_are_distinct_threads_that_sew():
    plan = _plan((5, [[(0, 0), (1, 1)]]), (9, [[]]), (5, [[(2, 2)]]), (7, [[(3, 3)]]))
    assert lc.cones_of(plan) == 2          # thread 5 (twice) and 7; thread 9 sews nothing


def test_cone_cell_marks_the_budget_overrun():
    assert lc.cones_cell(6) == "6" and lc.cones_cell(24) == "24 (+18)" and lc.cones_cell(None) == "n/a"


# ---------------------------------------------------------------------- shim
def test_the_shim_swaps_the_former_only_on_a_refusal_and_restores_the_pipeline(monkeypatch):
    from digitizer_core import pipeline
    calls = []

    def stub_cls(image, cfg, *a, forced_class=None, **k):
        return SimpleNamespace(class_="gradient")

    monkeypatch.setattr(pipeline, "classify", stub_cls)
    monkeypatch.setattr(pipeline, "fit_design_ramp", lambda prep: None)               # the gate refuses
    monkeypatch.setattr(pipeline, "photo_segment", lambda p, cfg, *a, **k: calls.append("slic") or "SLIC")
    monkeypatch.setattr(pipeline, "quantize", lambda p, cfg: calls.append("kmeans") or "KMEANS")
    real = (pipeline.classify, pipeline.fit_design_ramp, pipeline.photo_segment, pipeline.quantize)
    cfg = SimpleNamespace(is_photographic=None, forced_class=None)

    with lc.sixb_shim(True) as seen:
        pipeline.classify(None, cfg, forced_class=None)
        assert pipeline.fit_design_ramp(None) is None
        assert pipeline.photo_segment("p", cfg, face_regions=None) == "KMEANS"
    assert seen["swapped"] and seen["former"] == "quantize" and seen["class"] == "gradient"
    assert (pipeline.classify, pipeline.fit_design_ramp, pipeline.photo_segment, pipeline.quantize) == real

    with lc.sixb_shim(True) as seen:                  # a declared/detected photograph: the swap must not happen
        pipeline.fit_design_ramp(None)
        assert pipeline.photo_segment("p", SimpleNamespace(is_photographic=True)) == "SLIC"
    assert not seen["swapped"] and seen["photographic"] and seen["former"] == "photo_segment"

    with lc.sixb_shim(False) as seen:                 # inactive: it only watches
        pipeline.fit_design_ramp(None)
        assert pipeline.photo_segment("p", cfg) == "SLIC"
    assert not seen["swapped"]


def test_the_shim_does_not_swap_when_the_ramp_gate_never_ran(monkeypatch):
    """`fit_design_ramp` is only called for a gradient-class design, so a design that
    never reached it (flat, photo) must not be swapped by the 6b arm."""
    from digitizer_core import pipeline
    monkeypatch.setattr(pipeline, "photo_segment", lambda p, cfg, *a, **k: "SLIC")
    monkeypatch.setattr(pipeline, "quantize", lambda p, cfg: "KMEANS")
    with lc.sixb_shim(True) as seen:
        assert pipeline.photo_segment("p", SimpleNamespace(is_photographic=None)) == "SLIC"
    assert not seen["swapped"]


def test_the_probe_ends_the_build_at_the_dispatch(monkeypatch):
    from digitizer_core import pipeline
    monkeypatch.setattr(pipeline, "quantize", lambda p, cfg: pytest.fail("must stop first"))
    with lc.sixb_shim(False, stop=True) as seen:
        with pytest.raises(lc._Stop):
            pipeline.quantize("p", SimpleNamespace(is_photographic=None))
    assert seen["former"] == "quantize"


# ---------------------------------------------------------------- the report
def _row(arm, cls, former, stitches, trims, cones, **kw):
    return {"slug": "j", "arm": arm, "width_mm": 80.0, "garment": "hat_front",
            "facts": _facts(**{"class": cls, **kw.pop("facts", {})}), "former": former, "swapped": False,
            "ours": {"stitches": stitches, "trims": trims, "cones": cones, "stops": cones},
            "pro": {"stitches": 1000, "trims": 10, "cones": 4, "stops": 4},
            "thread": {"kappa": 0.5}, "sttype": {"kappa": 0.4, "raw": 0.7, "chance": 0.5},
            "engine": {"tree": "t"}, **kw}


def test_the_job_block_names_the_pro_and_the_four_routes_and_flags_the_overrun():
    rows = {"auto": _row("auto", "gradient", "photo_segment", 2000, 40, 9),
            "flat": _row("flat", "flat", "quantize", 1100, 12, 5),
            "sixb": _row("sixb", "gradient", "quantize", 1500, 20, 6)}
    text = lc.job_block("j", rows)
    assert "6b gate: **fires**" in text
    for needle in ("the pro", "auto", "forced flat", "6b, as written", "planner's variant (NOT Kent's)",
                   "9 (+3)", "0.40 (0.70 / 0.50)"):
        assert needle in text
    table = lc.summary_table({"j": rows})
    assert "gradient / photo_segment x1" in table and "jobs over 6 cones" in table


# ----------------------------------------------------- the two committed fixtures
@pytest.fixture(scope="module")
def lanes():
    """Each arm's lane on Becker's left chest and Fremont's hat, by the probe."""
    return {slug: {arm: lc.lane_of(lc.pinned_job(slug), arm) for arm in lc.RUN_ARMS} for slug in lc.PINNED}


def test_fixture_widths_are_the_pro_files(lanes):
    """The pinned width is what the registry reads off the pro's DST. Skipped where the
    pro file is not on the box (CI)."""
    for slug, spec in lc.PINNED.items():
        job, why = lc.resolve_job(slug)
        if job is None:
            pytest.skip(f"{slug}: {why}")
        assert job.width_mm == spec["width_mm"] and job.garment == spec["garment"]


def test_becker_left_chest_is_already_flat_so_every_arm_is_the_same_lane(lanes):
    """The premise: a real logo does not always reach the gradient lane. Becker's left
    chest, at its pro width under the Studio's request, is classed FLAT by stage 0."""
    arms = lanes["becker_lc_large"]
    for arm in lc.RUN_ARMS:
        assert (arms[arm]["class"], arms[arm]["former"]) == ("flat", "quantize"), arm
    assert not lc.sixb_gate(arms["auto"]["facts"])[0]
    assert lc.planner_arm(arms["auto"]["facts"]) == "auto" and lc.sixb_arm(arms["auto"]["facts"]) == "auto"
    assert not arms["sixb"]["swapped"]


def test_fremont_hat_is_gradient_and_each_arm_reaches_its_own_lane(lanes):
    arms = lanes["hotel_fremont_hat"]
    assert (arms["auto"]["class"], arms["auto"]["former"]) == ("gradient", "photo_segment")
    assert arms["auto"]["facts"]["ramp"] == "none" and not arms["auto"]["facts"]["photographic"]
    assert (arms["flat"]["class"], arms["flat"]["former"]) == ("flat", "quantize")
    # 6b as written: the segmenter is the flat quantizer, the class stays gradient
    assert (arms["sixb"]["class"], arms["sixb"]["former"]) == ("gradient", "quantize")
    assert arms["sixb"]["swapped"]
    assert lc.planner_arm(arms["auto"]["facts"]) == "flat"


def test_6b_segments_with_the_flat_quantizer_only_where_its_rule_says_so(lanes):
    for slug, arms in lanes.items():
        fires, _why = lc.sixb_gate(arms["auto"]["facts"])
        assert arms["sixb"]["swapped"] == fires, slug
        assert arms["sixb"]["class"] == arms["auto"]["class"], slug       # 6b never changes the class
        if not fires:
            assert arms["sixb"]["former"] == arms["auto"]["former"], slug  # off the gate it IS auto
