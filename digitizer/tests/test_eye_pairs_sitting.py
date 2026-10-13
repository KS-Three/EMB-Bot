"""tools.eye_pairs.sitting: the kit builder for a pre-registered blind sitting.

What is pinned here, and why each is worth a test:

* the COMMITTED spec validates against the real repository (the logos exist,
  are the files the spec pinned, are not byte-equal to a logo Kent has judged,
  and every flag is a PipelineConfig field), and its pre-registration document
  names every arm and logo the spec holds, so the two cannot drift;
* the blinding guard refuses a judged logo, a byte-duplicate of one, a logo
  with no provenance, an arm that equals the base, an unknown flag;
* the manipulation check passes, fails and swaps an arm exactly as registered,
  from designs alone;
* the analysis refuses a part-picked sitting, maps LEFT/RIGHT/tie onto the
  page's before/after/same by the side shown (never by arm), and prints kappa
  with intervals and n, never a raw agreement figure;
* an end-to-end kit (two tiny logos, real engine) comes out blind: the public
  manifest names no pair, the sealed hash is the sitting's, a failing arm was
  replaced once, and a reserve that was swapped out is not paired.
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import __main__ as cli  # noqa: E402
from tools.eye_pairs import pooled, sitting  # noqa: E402
from tools.eye_pairs.pairs import BASE, append_pick  # noqa: E402

from .conftest import draw_tiny_logo, held_on_source_line  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PREREG = REPO / "docs" / "eye-pairs-2026-10-13" / "wok42" / "PRE-REGISTRATION.md"


@pytest.fixture(autouse=True)
def _small_bootstrap(monkeypatch):
    """10,000 resamples is the reported figure; these tests read signs and
    keys, so 300 keeps the module in seconds."""
    monkeypatch.setattr(pooled, "B", 300)


# ------------------------------------------------------- the real spec ----

def test_the_committed_spec_validates_against_the_repository():
    sitting.validate_spec(sitting.load_spec())


def test_no_logo_in_the_spec_is_a_judged_one():
    spec = sitting.load_spec()
    judged = set(spec["judged_fixtures"]) | set(sitting.judged_files())
    for lg in spec["logos"]:
        assert lg["name"] not in judged and lg["design"] not in judged
        assert lg["provenance"].strip()


def test_the_preregistration_names_every_arm_logo_and_base_flag_of_the_spec():
    spec = sitting.load_spec()
    text = PREREG.read_text(encoding="utf-8")
    names = (list(spec["arms"]) + [r["name"] for r in spec["reserve_arms"]]
             + [lg["name"] for lg in spec["logos"]] + list(spec["base_flags"]))
    missing = [n for n in names if f"`{n}`" not in text]
    assert not missing, f"PRE-REGISTRATION never names: {missing}"
    for arm in spec["arms"].values():
        assert f"**{arm['expected_pick']}" in text


def test_the_four_registered_leads_carry_the_directions_the_doc_wrote_down():
    leads = {l["metric"]: l["direction"] for l in sitting.load_spec()["leads"]["primary"]}
    assert leads == {"flow_circvar": "lower", "long_share": "lower",
                     "thread_density": "higher", "trims_per_1000": "lower"}


# ---------------------------------------------------- the blinding guard ----

def mini_spec(tmp_path, *, same_as_judged=False):
    """A valid two-logo spec over files in a throwaway `testdata`. Returns
    (spec, testdata, judged)."""
    td = tmp_path / "digitizer" / "testdata"
    td.mkdir(parents=True)
    a = draw_tiny_logo(td / "a.png")
    b = draw_tiny_logo(td / "b.png", extra_dot=True)
    judged = {"becker": td / ("a.png" if same_as_judged else "becker.png")}
    if not same_as_judged:
        draw_tiny_logo(judged["becker"], extra_dot=False)
        judged["becker"].write_bytes(b"not a logo anyone shipped")
    spec = {
        "schema": 1, "sitting": "t-1", "seed": 7, "n_identical": 1, "n_repeat": 1,
        "base_flags": {"lettering_columns": True},
        "judged_fixtures": ["becker"],
        "logos": [
            {"name": "a", "design": "a", "kind": "synthetic_committed", "width_mm": 40.0,
             "garment": "left_chest", "provenance": "drawn by conftest.draw_tiny_logo",
             "source": {"kind": "file", "path": "testdata/a.png", "sha256_16": sitting._sha16(a)}},
            {"name": "b", "design": "b", "kind": "synthetic_committed", "width_mm": 40.0,
             "garment": "left_chest", "provenance": "the same card with a dot",
             "source": {"kind": "file", "path": "testdata/b.png", "sha256_16": sitting._sha16(b)}}],
        "arms": {"angle45": {"flags": {"fill_angle_deg": 45.0}, "stratum": "flow",
                             "variable": "row angle", "moves": {}, "holds": [],
                             "expected_pick": "tie"}},
        "reserve_arms": [],
        "manipulation": {"thresholds": {"trims_per_1000": {"kind": "abs", "value": 0.5},
                                        "flow_circvar": {"kind": "abs", "value": 0.02},
                                        "long_share": {"kind": "abs", "value": 0.02},
                                        "thread_density_whole": {"kind": "rel", "value": 0.05}},
                         "density_matched_tolerance": 0.10},
        "leads": {"primary": [{"metric": "trims_per_1000", "direction": "lower"}],
                  "secondary": []},
    }
    return spec, td, judged


def test_a_valid_mini_spec_passes(tmp_path):
    spec, td, judged = mini_spec(tmp_path)
    sitting.validate_spec(spec, testdata=td, judged=judged)


@pytest.mark.parametrize("mutate,needle", [
    (lambda s: s["logos"][0].update(name="becker"), "judged"),
    (lambda s: s["logos"][0].update(design="becker"), "judged"),
    (lambda s: s["logos"][0].update(provenance="  "), "no provenance"),
    (lambda s: s["logos"][0].update(kind="client_art_new"), "kind"),
    (lambda s: s["logos"][0]["source"].update(sha256_16="0" * 16), "not the file the spec pinned"),
    (lambda s: s["logos"][0]["source"].update(path="testdata/missing.png"), "does not exist"),
    (lambda s: s["logos"][1].update(name="a"), "twice"),
    (lambda s: s["logos"][0]["source"].update(kind="generator", id="nobody"), "not registered"),
    (lambda s: s["arms"]["angle45"]["flags"].update(no_such_flag=True), "not a PipelineConfig field"),
    (lambda s: s["arms"]["angle45"]["flags"].update(lettering_columns=True), "already runs"),
    (lambda s: s["arms"].update(base=copy.deepcopy(s["arms"]["angle45"])), "reserved"),
    (lambda s: s["arms"].update(twin=copy.deepcopy(s["arms"]["angle45"])), "same flags"),
    (lambda s: s["arms"]["angle45"].update(expected_pick="maybe"), "expected_pick"),
    (lambda s: s["arms"]["angle45"].update(moves={"stitches": "up"}), "no threshold"),
    (lambda s: s["arms"]["angle45"].update(holds=["stitches"]), "no threshold"),
    (lambda s: s["leads"]["primary"][0].update(direction="sideways"), "direction"),
    (lambda s: s["base_flags"].update(imaginary=True), "base flag"),
])
def test_the_spec_is_refused_for(tmp_path, mutate, needle):
    spec, td, judged = mini_spec(tmp_path)
    mutate(spec)
    with pytest.raises(sitting.SpecError, match=re.escape(needle)):
        sitting.validate_spec(spec, testdata=td, judged=judged)


def test_a_logo_byte_equal_to_a_judged_one_is_refused_whatever_it_is_called(tmp_path):
    spec, td, judged = mini_spec(tmp_path, same_as_judged=True)
    with pytest.raises(sitting.SpecError, match="byte-equal to the judged 'becker'"):
        sitting.validate_spec(spec, testdata=td, judged=judged)


def test_two_logos_that_are_the_same_file_are_refused(tmp_path):
    spec, td, judged = mini_spec(tmp_path)
    spec["logos"][1]["source"] = copy.deepcopy(spec["logos"][0]["source"])
    with pytest.raises(sitting.SpecError, match="byte-equal to logo 'a'"):
        sitting.validate_spec(spec, testdata=td, judged=judged)


def test_every_problem_is_listed_not_just_the_first(tmp_path):
    spec, td, judged = mini_spec(tmp_path)
    spec["logos"][0]["provenance"] = ""
    spec["arms"]["angle45"]["expected_pick"] = "maybe"
    with pytest.raises(sitting.SpecError) as e:
        sitting.validate_spec(spec, testdata=td, judged=judged)
    assert "no provenance" in str(e.value) and "expected_pick" in str(e.value)


def test_a_generator_logo_is_drawn_the_same_every_time(tmp_path):
    spec = sitting.load_spec()
    gens = [lg for lg in spec["logos"] if lg["source"]["kind"] == "generator"]
    assert {g["source"]["id"] for g in gens} == set(sitting.GENERATORS)
    first = sitting.materialise({**spec, "logos": gens}, tmp_path / "one")
    again = sitting.materialise({**spec, "logos": gens}, tmp_path / "two")
    assert [l["sha256"] for l in first] == [l["sha256"] for l in again]
    assert all(Path(l["path"]).stat().st_size > 1000 for l in first)


# -------------------------------------------- the manipulation check ----

def _design(trims=0, rows=1, pitch=0.15, angle_pts=None):
    """A Design dict in 0.1 mm units: `rows` fill rows of one run, then
    `trims` further one-row runs each preceded by a trim and a jump."""
    st, runs = [], []

    def run(y0):
        i0 = len(st)
        for r in range(rows):
            y = y0 + r * pitch
            pts = [(0, y), (3, y), (6, y), (9, y)]
            pts = pts if r % 2 == 0 else pts[::-1]
            st.extend({"x": x * 10, "y": yy * 10, "type": "stitch"} for x, yy in pts)
        runs.append({"i0": i0, "i1": len(st) - 1, "kind": "fill", "shape": f"S{len(runs)}",
                     "role": "", "block": 0})

    run(0.0)
    for k in range(trims):
        st.append({"x": st[-1]["x"], "y": st[-1]["y"], "type": "trim"})
        st.append({"x": 0, "y": (k + 1) * 100, "type": "jump"})
        run((k + 1) * 10.0)
    st.append({"x": st[-1]["x"], "y": st[-1]["y"], "type": "end"})
    return {"stitches": st, "runs": runs, "stitchCount": sum(1 for s in st if s["type"] == "stitch")}


def _checked_spec(moves=None, holds=None, logos=("a", "b", "c")):
    spec, _td, _j = {"manipulation": {"thresholds": {
        "trims_per_1000": {"kind": "abs", "value": 0.5},
        "flow_circvar": {"kind": "abs", "value": 0.02},
        "long_share": {"kind": "abs", "value": 0.02},
        "thread_density_whole": {"kind": "rel", "value": 0.05}}},
        "logos": [{"name": n} for n in logos], "arms": {}, "reserve_arms": []}, None, None
    spec["arms"]["x"] = {"stratum": "trims", "moves": moves or {}, "holds": holds or []}
    return spec


def test_an_arm_that_moves_its_metric_and_holds_the_rest_passes():
    spec = _checked_spec(moves={"trims_per_1000": "down"}, holds=["flow_circvar", "long_share"])
    designs = {}
    for lg in "abc":
        designs[(lg, BASE)] = _design(trims=6, rows=4)
        designs[(lg, "x")] = _design(trims=2, rows=4)
    t = sitting.manipulation_check(spec, designs)["x"]
    assert t["passes"] and t["active"] == ["a", "b", "c"] and not t["identical"]
    cell = t["per_logo"]["a"]["metrics"]["trims_per_1000"]
    assert cell["delta"] < -0.5 and cell["moved_as_registered"]


def test_an_arm_that_moves_the_wrong_way_fails():
    spec = _checked_spec(moves={"trims_per_1000": "down"})
    designs = {}
    for lg in "abc":
        designs[(lg, BASE)] = _design(trims=2, rows=4)
        designs[(lg, "x")] = _design(trims=6, rows=4)
    t = sitting.manipulation_check(spec, designs)["x"]
    assert not t["passes"] and "0 of 3" in t["why"]


def test_a_held_metric_that_moves_fails_the_arm():
    spec = _checked_spec(holds=["thread_density_whole"])
    designs = {}
    for lg in "abc":
        designs[(lg, BASE)] = _design(rows=8, pitch=0.15)
        designs[(lg, "x")] = _design(rows=8, pitch=0.30)
    assert not sitting.manipulation_check(spec, designs)["x"]["passes"]


def test_an_arm_identical_to_base_on_four_logos_is_inert():
    spec = _checked_spec(logos=("a", "b", "c", "d", "e", "f"))
    designs = {}
    for lg in "abcdef":
        designs[(lg, BASE)] = _design(trims=1)
        designs[(lg, "x")] = _design(trims=1) if lg in "abcd" else _design(trims=3)
    t = sitting.manipulation_check(spec, designs)["x"]
    assert not t["passes"] and "identical to base on 4 of 6" in t["why"]


def test_an_arm_that_changes_one_logo_cannot_pass():
    spec = _checked_spec()
    designs = {("a", BASE): _design(trims=1), ("a", "x"): _design(trims=3),
               ("b", BASE): _design(trims=1), ("b", "x"): _design(trims=1),
               ("c", BASE): _design(trims=1), ("c", "x"): _design(trims=1)}
    assert not sitting.manipulation_check(spec, designs)["x"]["passes"]


def test_a_failing_arm_is_replaced_once_by_the_first_reserve_of_its_stratum():
    spec = _checked_spec(moves={"trims_per_1000": "down"})
    spec["arms"]["y"] = {"stratum": "flow", "moves": {}, "holds": []}
    spec["reserve_arms"] = [
        {"name": "r_flow", "stratum": "flow", "moves": {}, "holds": [], "flags": {}},
        {"name": "r_trims", "stratum": "trims", "moves": {"trims_per_1000": "down"},
         "holds": [], "flags": {}},
        {"name": "r_trims2", "stratum": "trims", "moves": {}, "holds": [], "flags": {}}]
    designs = {}
    for lg in "abc":
        designs[(lg, BASE)] = _design(trims=2, rows=4)
        designs[(lg, "x")] = _design(trims=6, rows=4)         # the wrong way: fails
        designs[(lg, "y")] = _design(trims=3, rows=4)         # moves, no requirement: passes
    rendered = []

    def render(reserve):
        rendered.append(reserve["name"])
        for lg in "abc":
            designs[(lg, reserve["name"])] = _design(trims=0, rows=4)   # the right way

    arms, repl, table = sitting.settle_arms(spec, lambda: designs, render)
    assert set(arms) == {"y", "r_trims"} and rendered == ["r_trims"]
    assert repl == [{"arm": "x", "reason": "failed: moved and held as registered on 0 of 3 logos",
                     "replaced_by": "r_trims", "reserve_passes": True}]
    assert set(table) == {"y", "r_trims"} and all(t["passes"] for t in table.values())


def test_a_reserve_that_fails_too_stays_and_is_flagged_not_swapped_again():
    spec = _checked_spec(moves={"trims_per_1000": "down"})
    spec["reserve_arms"] = [{"name": "r1", "stratum": "trims", "moves": {"trims_per_1000": "down"},
                             "holds": [], "flags": {}},
                            {"name": "r2", "stratum": "trims", "moves": {}, "holds": [], "flags": {}}]
    designs = {}
    for lg in "abc":
        designs[(lg, BASE)] = _design(trims=2, rows=4)
        designs[(lg, "x")] = _design(trims=6, rows=4)

    def render(reserve):
        for lg in "abc":
            designs[(lg, reserve["name"])] = _design(trims=9, rows=4)   # also the wrong way

    arms, repl, table = sitting.settle_arms(spec, lambda: designs, render)
    assert set(arms) == {"r1"} and repl[0]["reserve_passes"] is False
    assert not table["r1"]["passes"]            # r2 is never tried


def test_a_failing_arm_with_no_reserve_stays_and_says_so():
    spec = _checked_spec(moves={"trims_per_1000": "down"})
    designs = {}
    for lg in "abc":
        designs[(lg, BASE)] = _design(trims=2, rows=4)
        designs[(lg, "x")] = _design(trims=6, rows=4)
    arms, repl, table = sitting.settle_arms(spec, lambda: designs, lambda r: None)
    assert set(arms) == {"x"} and repl[0]["replaced_by"] is None and not table["x"]["passes"]


# ------------------------------------------------------------ analysis ----

def _kit(picks, trims_for_arm=2, base_trims=6, n=12, expected="tie", isolates=True):
    """A hand-built sealed map over `n` live pairs of one arm on 4 logos, the
    arm on the LEFT of the pairs in `left_pairs`, with designs whose trims
    differ so the trims instrument always has a side."""
    logos = ["a", "b", "c", "d"]
    sealed, designs, pick_rows = {}, {}, {}
    for i in range(n):
        pid, lg = f"P{i + 1:03d}", logos[i % 4]
        arm_left = i % 2 == 0
        sealed[pid] = {"fixture": lg, "left_arm": "arm" if arm_left else BASE,
                       "right_arm": BASE if arm_left else "arm", "kind": "live",
                       "repeat_of": None, "design_only": False}
        pick_rows[pid] = {"pair": pid, "choice": picks[i], "ms": 1, "ts": "t", "undo_of": None}
    for lg in logos:
        designs[(lg, BASE)] = _design(trims=base_trims, rows=4)
        designs[(lg, "arm")] = _design(trims=trims_for_arm, rows=4)
    man = {"sitting": "t-1", "built": "2026-10-13T00:00:00+00:00",
           "logos": [{"name": lg, "design": lg} for lg in logos],
           "arms": {"arm": {"stratum": "trims", "expected_pick": expected}},
           "manipulation": {"arm": {"passes": isolates}}}
    spec = {"manipulation": {"density_matched_tolerance": 0.10,
                             "thresholds": {"trims_per_1000": {"kind": "abs", "value": 0.5}}},
            "leads": {"primary": [{"metric": "trims_per_1000", "direction": "lower"},
                                  {"metric": "flow_circvar", "direction": "lower"}],
                      "secondary": []}}
    return spec, man, sealed, pick_rows, designs


def _kent_picks_fewer_trims(n=12):
    # arm (fewer trims) is LEFT on even i: Kent picks it, i.e. L on even, R on odd; with
    # a few ties so both statistics have something to say
    picks = ["L" if i % 2 == 0 else "R" for i in range(n)]
    picks[3] = picks[7] = "tie"
    return picks


def test_left_right_and_tie_become_before_after_same_by_the_side_shown():
    spec, man, sealed, picks, designs = _kit(["L", "R", "tie"] * 4)
    inp = sitting.labelled_inputs(spec, man, sealed, picks, designs)
    pairs = inp["sittings"]["t-1"]["pairs"]
    assert [p["label"] for p in pairs[:3]] == ["before", "after", "same"]
    # the arm is LEFT on P001 and Kent picked LEFT: the label never names the arm
    assert pairs[0]["arm"] == "arm" and pairs[1]["arm"] == "arm"
    assert pairs[0]["before"]["trims_per_1000"] < pairs[0]["after"]["trims_per_1000"]
    assert pairs[1]["after"]["trims_per_1000"] < pairs[1]["before"]["trims_per_1000"]


def test_the_expected_pick_is_mapped_to_the_side_the_arm_or_base_was_shown_on():
    for expected, want_p1, want_p2 in (("arm", "before", "after"), ("base", "after", "before"),
                                       ("tie", "same", "same")):
        spec, man, sealed, picks, designs = _kit(["L"] * 12, expected=expected)
        pairs = sitting.labelled_inputs(spec, man, sealed, picks, designs)["sittings"]["t-1"]["pairs"]
        assert (pairs[0]["expected_label"], pairs[1]["expected_label"]) == (want_p1, want_p2)


def test_controls_and_repeats_are_not_pooled_as_live_pairs():
    spec, man, sealed, picks, designs = _kit(["L"] * 12)
    sealed["P013"] = {"fixture": "a", "left_arm": BASE, "right_arm": BASE, "kind": "identical",
                      "repeat_of": None, "design_only": False}
    sealed["P014"] = {**sealed["P001"], "kind": "repeat", "repeat_of": "P001"}
    picks["P013"] = {"pair": "P013", "choice": "tie", "ms": 1, "ts": "t", "undo_of": None}
    picks["P014"] = {"pair": "P014", "choice": "L", "ms": 1, "ts": "t", "undo_of": None}
    pairs = sitting.labelled_inputs(spec, man, sealed, picks, designs)["sittings"]["t-1"]["pairs"]
    assert len(pairs) == 12
    c = sitting.controls_report(sealed, picks)
    assert c["identical_pairs"] == 1 and c["identical_called_tie"] == 1
    assert c["repeat_pairs"] == 1 and c["repeat_answered_differently"] == 0


def test_trims_agreeing_with_him_is_read_above_chance_and_the_control_replicates():
    spec, man, sealed, picks, designs = _kit(_kent_picks_fewer_trims())
    inp = sitting.labelled_inputs(spec, man, sealed, picks, designs)
    rep = sitting.confirmatory(inp, spec)
    lead = rep["leads"]["trims_per_1000"]
    assert lead["kappa_sides"] == pytest.approx(1.0) and lead["n_decided"] == 10
    assert lead["reading_sides"] == "above chance" and rep["control_replicates"] is True
    assert rep["trims_split"]["trims_per_1000"]["trims_held"]["n_pairs"] == 0
    assert rep["trims_split"]["trims_per_1000"]["trims_moved"]["n_pairs"] == 12


def test_a_lead_that_never_separates_a_pair_is_not_read():
    """flow_circvar cannot choose a side on any pair here (every stitch runs
    the same way, and the arm sews fewer shapes): nothing is read off it."""
    spec, man, sealed, picks, designs = _kit(_kent_picks_fewer_trims())
    rep = sitting.confirmatory(sitting.labelled_inputs(spec, man, sealed, picks, designs), spec)
    flow = rep["leads"]["flow_circvar"]
    assert flow["n_decided"] == 0
    assert flow["reading_sides"].startswith("n too small")


def test_a_registered_direction_overrides_the_one_a_candidate_ships_with():
    spec, *_ = _kit(["L"] * 12)
    spec["leads"]["primary"].append({"metric": "long_share", "direction": "lower"})
    assert pooled.INSTRUMENTS.get("long_share") is None
    from tools.eye_pairs import density_flow as df
    assert df.CANDIDATES["long_share"][0] == "higher"          # the doc's original hypothesis
    assert sitting._directions(spec)["long_share"][0] == "lower"   # the registered one


def test_the_report_carries_kappa_intervals_and_n_and_never_a_raw_agreement():
    spec, man, sealed, picks, designs = _kit(_kent_picks_fewer_trims())
    rep = sitting.confirmatory(sitting.labelled_inputs(spec, man, sealed, picks, designs), spec)
    ctrl = sitting.controls_report(sealed, picks)
    text = sitting.markdown(rep, ctrl, {"sitting": "t-1"})
    flat = json.dumps(rep).lower()
    for banned in ("raw", "accuracy", "percent_agree", "share"):
        assert banned not in flat, banned
    assert "kappa" in text and "CI pairs" in text and "n decided" in text
    assert re.search(r"[+-]\d\.\d\d \[", text)                  # a kappa with its interval
    assert "agree" not in text.lower()


def test_the_prereg_instrument_scores_how_well_the_expected_picks_predicted_him():
    spec, man, sealed, picks, designs = _kit(_kent_picks_fewer_trims(), expected="arm")
    rep = sitting.confirmatory(sitting.labelled_inputs(spec, man, sealed, picks, designs), spec)
    assert rep["prereg"]["kappa_sides"] == pytest.approx(1.0)
    spec, man, sealed, picks, designs = _kit(_kent_picks_fewer_trims(), expected="base")
    rep = sitting.confirmatory(sitting.labelled_inputs(spec, man, sealed, picks, designs), spec)
    assert rep["prereg"]["kappa_sides"] < -0.9


def test_the_leads_are_also_read_on_the_arms_that_passed_the_manipulation_check_alone():
    spec, man, sealed, picks, designs = _kit(_kent_picks_fewer_trims())
    rep = sitting.confirmatory(sitting.labelled_inputs(spec, man, sealed, picks, designs), spec)
    assert rep["isolating_only"]["trims_per_1000"]["n_pairs"] == 12
    spec, man, sealed, picks, designs = _kit(_kent_picks_fewer_trims(), isolates=False)
    rep = sitting.confirmatory(sitting.labelled_inputs(spec, man, sealed, picks, designs), spec)
    iso = rep["isolating_only"]["trims_per_1000"]
    assert iso["n_pairs"] == 0 and iso["n_decided"] == 0 and iso["reading_sides"].startswith("n too small")


def test_density_matched_is_read_from_the_designs_not_assumed():
    spec, man, sealed, picks, designs = _kit(["L"] * 12)
    for lg in "abcd":
        designs[(lg, "arm")] = _design(trims=6, rows=4, pitch=0.30)     # half the density
    rep = sitting.confirmatory(sitting.labelled_inputs(spec, man, sealed, picks, designs), spec)
    assert rep["density_matched"] == {"matched": 0, "not_matched": 12}


def test_merge_inputs_appends_the_sitting_and_refuses_a_repeat():
    spec, man, sealed, picks, designs = _kit(["L"] * 12)
    new = sitting.labelled_inputs(spec, man, sealed, picks, designs)
    existing = {"schema": 1, "sittings": {"old": {"pairs": []}}}
    merged = sitting.merge_inputs(existing, new)
    assert set(merged["sittings"]) == {"old", "t-1"} and set(existing["sittings"]) == {"old"}
    with pytest.raises(sitting.SpecError, match="already in"):
        sitting.merge_inputs(merged, new)


def test_analysis_refuses_a_part_picked_sitting_and_a_pick_for_no_pair(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "pairs.json").write_text(json.dumps([{"pair": "P001"}, {"pair": "P002"}]))
    (out / "arms.json").write_text(json.dumps({"P001": {}, "P002": {}}))
    append_pick(out / "picks.jsonl", "P001", "L", 10)
    with pytest.raises(SystemExit, match="1 of 2 pairs have no pick"):
        sitting.require_complete(out)
    append_pick(out / "picks.jsonl", "P002", "R", 10)
    sealed, picks = sitting.require_complete(out)
    assert set(picks) == {"P001", "P002"}
    append_pick(out / "picks.jsonl", "P999", "R", 10)
    with pytest.raises(SystemExit, match="do not exist"):
        sitting.require_complete(out)


# -------------------------------------------------- end to end, tiny ----

def _tiny_a():
    import cv2
    import numpy as np

    img = np.full((160, 240, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 40), (110, 120), (0, 0, 0), -1)
    cv2.circle(img, (170, 80), 35, (0, 0, 200), -1)
    return img


def _tiny_b():
    import cv2

    img = _tiny_a()
    cv2.circle(img, (40, 140), 6, (0, 0, 0), -1)
    return img


@pytest.fixture(scope="module")
def kit(tmp_path_factory):
    """Two tiny generator logos, three arms: `angle45` changes the stitches,
    `inert` (design_angle) does not on this card, `angle30` is its stratum's
    reserve. A real engine, one spec, one `prepare`."""
    td = tmp_path_factory.mktemp("kit")
    spec = {
        "schema": 1, "sitting": "tiny-1", "seed": 11, "n_identical": 1, "n_repeat": 1,
        "base_flags": {"lettering_columns": True}, "judged_fixtures": ["becker"],
        "logos": [{"name": n, "design": n, "kind": "synthetic_generator", "width_mm": 40.0,
                   "garment": "left_chest", "provenance": f"conftest card {n}",
                   "source": {"kind": "generator", "id": f"tiny_{n}"}} for n in ("a", "b")],
        "arms": {"angle45": {"flags": {"fill_angle_deg": 45.0}, "stratum": "flow",
                             "variable": "row angle", "moves": {}, "holds": [],
                             "expected_pick": "tie"},
                 "inert": {"flags": {"design_angle": True}, "stratum": "flow",
                           "variable": "angle across shapes", "moves": {}, "holds": [],
                           "expected_pick": "tie"}},
        "reserve_arms": [{"name": "angle30", "flags": {"fill_angle_deg": 30.0}, "stratum": "flow",
                          "variable": "row angle", "moves": {}, "holds": [],
                          "expected_pick": "base"}],
        "manipulation": {"thresholds": {"trims_per_1000": {"kind": "abs", "value": 0.5},
                                        "flow_circvar": {"kind": "abs", "value": 0.02},
                                        "long_share": {"kind": "abs", "value": 0.02},
                                        "thread_density_whole": {"kind": "rel", "value": 0.05}},
                         "density_matched_tolerance": 0.10},
        "leads": {"primary": [{"metric": "trims_per_1000", "direction": "lower"}],
                  "secondary": []},
    }
    path = td / "spec.json"
    path.write_text(json.dumps(spec))
    sitting.GENERATORS["tiny_a"] = ("tests.test_eye_pairs_sitting", "_tiny_a")
    sitting.GENERATORS["tiny_b"] = ("tests.test_eye_pairs_sitting", "_tiny_b")
    out = td / "out"
    try:
        with held_on_source_line():
            man = sitting.prepare(path, out, manifest_to=td / "manifest-copy.json")
        yield spec, path, out, man, td
    finally:
        sitting.GENERATORS.pop("tiny_a", None)
        sitting.GENERATORS.pop("tiny_b", None)


def test_the_inert_arm_was_replaced_once_by_its_strata_reserve(kit):
    _spec, _path, _out, man, _td = kit
    assert set(man["arms"]) == {"angle45", "angle30"}
    assert [r["arm"] for r in man["replacements"]] == ["inert"]
    assert man["replacements"][0]["replaced_by"] == "angle30"
    assert "changes 0 logo(s)" in man["replacements"][0]["reason"]
    assert all(v["passes"] for v in man["manipulation"].values())


def test_the_replaced_arm_is_not_in_the_sitting_though_it_was_rendered(kit):
    _spec, _path, out, man, _td = kit
    feats = json.loads((out / "features.json").read_text())
    assert "inert" in feats["a"]                       # it was rendered
    sealed = json.loads((out / "arms.json").read_text())
    shown = {s["left_arm"] for s in sealed.values()} | {s["right_arm"] for s in sealed.values()}
    assert shown == {BASE, "angle45", "angle30"}


def test_the_public_manifest_names_no_pair_and_no_side(kit):
    _spec, _path, out, man, td = kit
    text = json.dumps(man)
    sealed = json.loads((out / "arms.json").read_text())
    assert not re.search(r"P\d{3}", text) and "left_arm" not in text and "right_arm" not in text
    assert man["pairs"] == {"total": len(sealed), "live": 4, "identical": 1, "repeat": 1,
                            "live_base_left": 2, "live_per_logo": {"a": 2, "b": 2}}
    assert json.loads((td / "manifest-copy.json").read_text()) == man


def test_the_manifest_commits_to_the_sealed_map_the_picker_will_serve(kit):
    _spec, _path, out, man, _td = kit
    sitting_json = json.loads((out / "sitting.json").read_text())
    assert man["sealed_sha256"] == sitting_json["sealed_sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", man["designs_sha256"])


def test_exactly_half_the_live_pairs_put_the_base_on_the_left(kit):
    _spec, _path, out, _man, _td = kit
    sealed = json.loads((out / "arms.json").read_text())
    live = [s for s in sealed.values() if s["kind"] == "live"]
    assert sum(1 for s in live if s["left_arm"] == BASE) == len(live) // 2


def test_analyse_runs_end_to_end_once_every_pair_is_picked(kit, tmp_path, capsys):
    spec, path, out, man, _td = kit
    work = tmp_path / "picked"
    import shutil
    shutil.copytree(out, work)
    public = json.loads((work / "pairs.json").read_text())
    with pytest.raises(SystemExit, match="have no pick yet"):
        sitting.analyse(path, work)
    for i, p in enumerate(public):
        append_pick(work / "picks.jsonl", p["pair"], ["L", "R", "tie"][i % 3], 5)
    res = sitting.analyse(path, work, markdown_to=tmp_path / "a.txt", inputs_to=tmp_path / "in.json")
    assert res["report"]["n_live_pairs"] == 4
    assert (work / "analysis.json").exists()
    assert "kappa" in capsys.readouterr().out
    inputs = json.loads((tmp_path / "in.json").read_text())
    assert len(inputs["sittings"]["tiny-1"]["pairs"]) == 4
    pooled.validate(inputs)                               # the pool's own vocabulary guard


def test_a_kit_is_not_rebuilt_over_picks(kit, tmp_path):
    spec, path, out, man, _td = kit
    work = tmp_path / "again"
    import shutil
    shutil.copytree(out, work)
    append_pick(work / "picks.jsonl", "P001", "L", 5)
    with pytest.raises(SystemExit, match="not rebuilt over a sitting"):
        sitting.prepare(path, work)


def test_pair_still_defaults_to_the_seed_and_counts_every_earlier_sitting_used():
    import inspect

    sig = inspect.signature(cli.pair)
    assert sig.parameters["seed"].default == 20260917
    assert sig.parameters["n_identical"].default == 8 and sig.parameters["n_repeat"].default == 8
    assert sig.parameters["arms"].default is None
