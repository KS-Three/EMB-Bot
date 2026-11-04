"""`tools.eye_pairs.vlm_judge`: the two frames, the sealed-key mapping, the
analysis on a made-up sitting whose answer is known, and the pin between the
module and its pre-registration. Nothing here touches the API."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.eye_pairs import pooled, vlm_judge as vj

REPO = Path(__file__).resolve().parents[2]
PREREG = REPO / "docs" / "eye-pairs-2026-11-04" / "vlm-judge" / "PRE-REGISTRATION.md"


@pytest.fixture(autouse=True)
def _few_resamples(monkeypatch):
    """The intervals are not under test; 10,000 resamples x 24 bootstraps per
    analyse() is seconds for nothing."""
    monkeypatch.setattr(pooled, "B", 200)


# ------------------------------------------------------------- the pin ----

def test_the_pre_registration_pins_this_module():
    text = PREREG.read_text(encoding="utf-8")
    s = vj.settings()
    assert s["prompt_sha256"] in text, "PRE-REGISTRATION.md does not carry the prompt's sha256"
    assert vj.PROMPT.splitlines()[0] in text, "the prompt is not quoted verbatim"
    assert f"`{s['effort']}`" in text and f"`max_tokens` {s['max_tokens']}" in text
    for model in s["models"]:
        assert f"`{model}`" in text, f"{model} is not named"
    assert "order B" in text and "swapped" in text


# ------------------------------------------------------------ the frames ----

def test_frame_a_swaps_only_order_b_sides():
    assert [vj.frame_a(c, "A") for c in ("L", "R", "tie")] == ["L", "R", "tie"]
    assert [vj.frame_a(c, "B") for c in ("L", "R", "tie")] == ["R", "L", "tie"]
    for c in ("L", "R", "tie"):           # its own inverse
        assert vj.frame_a(vj.frame_a(c, "B"), "B") == c


def test_to_label_reads_the_sealed_key():
    s = {"left_arm": "base", "right_arm": "lane_off"}
    assert [vj.to_label(c, s) for c in ("L", "R", "tie")] == ["before", "after", "tie"]
    s = {"left_arm": "lane_off", "right_arm": "base"}
    assert [vj.to_label(c, s) for c in ("L", "R", "tie")] == ["after", "before", "tie"]
    assert vj.to_label("L", {"left_arm": "base", "right_arm": "base"}) is None


def test_parse_verdict_takes_plain_json_and_a_stray_fence():
    v = vj.parse_verdict('{"choice": "L", "confidence": 4, "reason": "x"}')
    assert v["choice"] == "L" and v["confidence_in_range"]
    v = vj.parse_verdict('```json\n{"choice": "tie", "confidence": 9, "reason": "x"}\n```')
    assert v["choice"] == "tie" and not v["confidence_in_range"]
    with pytest.raises(ValueError):
        vj.parse_verdict('{"choice": "left", "confidence": 3, "reason": ""}')


# ------------------------------------------------- a sitting with an answer ----

def _sitting(n_live: int = 12) -> dict:
    """12 live pairs over four designs, Kent cycling L / R / tie, the base on
    the left in every other pair; one identical pair, one repeat of P001."""
    sealed, picks, design_of, expected = {}, {}, {}, {}
    arms = ("corner_fold_off", "lane_off")
    for i in range(n_live):
        pid, fx = f"P{i + 1:03d}", f"logo{i % 4}"
        design_of[fx] = f"d{i % 4}"
        base_left = i % 2 == 0
        sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None, "design_only": False,
                       "left_arm": "base" if base_left else arms[i % 2],
                       "right_arm": arms[i % 2] if base_left else "base"}
        picks[pid] = ("L", "R", "tie")[i % 3]
        expected[pid] = "before" if i % 2 == 0 else "after"
    sealed["P013"] = {"fixture": "logo0", "kind": "identical", "repeat_of": None, "design_only": False,
                      "left_arm": "base", "right_arm": "base"}
    picks["P013"] = "tie"
    sealed["P014"] = dict(sealed["P001"], kind="repeat", repeat_of="P001")
    picks["P014"] = picks["P001"]
    return {"sealed": sealed, "picks": picks, "design_of": design_of,
            "passing_arms": ["corner_fold_off"], "expected": expected}


def _verdicts(sitting: dict, choose) -> dict:
    """choose(pid, order) -> the judge's choice IN THAT ORDER'S OWN FRAME."""
    out: dict = {"m": {"A": {}, "B": {}}}
    for order in ("A", "B"):
        for pid in sitting["sealed"]:
            c = choose(pid, order)
            out["m"][order][pid] = {"pair": pid, "order": order, "model": "m", "choice": c,
                                    "choice_frame_a": vj.frame_a(c, order), "confidence": 4,
                                    "reason": "r", "input_tokens": 10, "output_tokens": 1,
                                    "stop_reason": "end_turn"}
    return out


def _like_kent(kent):
    return lambda pid, order: kent[pid] if order == "A" else vj.frame_a(kent[pid], "B")


def test_a_judge_that_copies_kent_scores_kappa_one_in_both_orders():
    st = _sitting()
    rep = vj.analyse(st, _verdicts(st, _like_kent(st["picks"])))
    m = rep["models"]["m"]
    for order in ("A", "B"):
        r = m["orders"][order]["reads"]["live"]
        assert r["n_scored"] == 12 and r["n_kent_decided"] == 8 and r["n_decided"] == 8
        assert r["kappa_3way"] == pytest.approx(1.0) and r["kappa_sides"] == pytest.approx(1.0)
        assert m["orders"][order]["opposite_side"] == []
        assert m["orders"][order]["reads"]["passing_arms_only"]["n_scored"] == 6
        assert m["orders"][order]["reads"]["vs_kit_expected_label"]["n_scored"] == 12
    assert m["swap"] == {"pairs_in_both_orders": 14, "same_verdict_after_swap": 14,
                         "side_flipped_with_swap": 0}
    ctrl = m["orders"]["A"]["controls"]
    assert (ctrl["identical_called_tie"], ctrl["identical_answered"]) == (1, 1)
    assert (ctrl["repeat_consistent"], ctrl["repeat_answered"]) == (1, 1)
    assert rep["kent"] == {"identical_called_tie": 1, "identical_pairs": 1,
                           "repeat_consistent": 1, "repeat_pairs": 1,
                           "left_picks": 5, "right_picks": 4, "ties_live": 4}


def test_a_judge_on_the_other_side_scores_below_zero_and_lists_every_pair():
    st = _sitting()
    flip = {"L": "R", "R": "L", "tie": "tie"}
    other = lambda pid, order: _like_kent({p: flip[c] for p, c in st["picks"].items()})(pid, order)
    rep = vj.analyse(st, _verdicts(st, other))
    r = rep["models"]["m"]["orders"]["A"]["reads"]["live"]
    assert r["kappa_sides"] == pytest.approx(-1.0) and r["kappa_3way"] < 0
    assert len(rep["models"]["m"]["orders"]["A"]["opposite_side"]) == 8
    row = rep["models"]["m"]["orders"]["A"]["opposite_side"][0]
    assert set(row) == {"pair", "fixture", "arm", "kent", "judge", "confidence", "reason"}


def test_a_screen_side_habit_shows_in_the_swap_count_not_in_kappa_alone():
    st = _sitting()
    rep = vj.analyse(st, _verdicts(st, lambda pid, order: "L"))
    s = rep["models"]["m"]["swap"]
    assert s == {"pairs_in_both_orders": 14, "same_verdict_after_swap": 0,
                 "side_flipped_with_swap": 14}
    ctrl = rep["models"]["m"]["orders"]["A"]["controls"]
    assert ctrl["left_picks_own_frame"] == 14 and ctrl["identical_called_tie"] == 0


def test_a_judge_that_only_ties_earns_nothing():
    st = _sitting()
    rep = vj.analyse(st, _verdicts(st, lambda pid, order: "tie"))
    r = rep["models"]["m"]["orders"]["A"]["reads"]["live"]
    assert r["n_decided"] == 0 and r["kappa_sides"] is None
    assert r["kappa_3way"] is None or r["kappa_3way"] <= 0
    assert r["judge_silent_on_decided"] == 8


def test_markdown_carries_every_scope_and_the_controls():
    st = _sitting()
    md = vj.markdown(vj.analyse(st, _verdicts(st, _like_kent(st["picks"]))))
    for needle in ("passing_arms_only", "vs_kit_expected_label", "Judge controls",
                   "Swap:", "ceiling", "| **before** |"):
        assert needle in md, needle
    assert "% agree" not in md.lower() and "agreement rate" not in md.lower()


def test_record_appends_in_run_shape_and_refuses_a_second_verdict(tmp_path):
    rows = [{"pair": "P001", "choice": "L", "confidence": 4, "reason": "a"},
            {"pair": "P002", "choice": "tie", "confidence": 9, "reason": "b"}]
    assert vj.record_rows(tmp_path, rows) == 2
    got = vj.load_verdicts(tmp_path)[vj.SESSION_MODEL]["A"]
    assert got["P001"]["choice_frame_a"] == "L" and got["P001"]["confidence_in_range"]
    assert got["P002"]["choice"] == "tie" and not got["P002"]["confidence_in_range"]
    assert got["P001"]["prompt_sha256"] == vj.prompt_sha()
    assert got["P001"]["input_tokens"] == 0 and got["P001"]["stop_reason"] == "end_turn"
    with pytest.raises(SystemExit, match="already recorded"):
        vj.record_rows(tmp_path, [{"pair": "P001", "choice": "R", "confidence": 1, "reason": ""}])
    with pytest.raises(SystemExit, match="not in"):
        vj.record_rows(tmp_path, [{"pair": "P003", "choice": "left", "confidence": 1, "reason": ""}])
    assert len(vj.load_verdicts(tmp_path)[vj.SESSION_MODEL]["A"]) == 2


def test_exclude_drops_a_pair_from_every_read_and_control_and_one_order_reads_clean():
    st = _sitting()
    v = _verdicts(st, _like_kent(st["picks"]))
    v["m"].pop("B")                                  # the session judge: order A only
    rep = vj.analyse(st, v, exclude=frozenset({"P001", "P013", "P999"}))
    assert rep["excluded"] == ["P001", "P013"]
    assert list(rep["models"]["m"]["orders"]) == ["A"]
    r = rep["models"]["m"]["orders"]["A"]["reads"]["live"]
    assert r["n_scored"] == 11 and r["kappa_3way"] == pytest.approx(1.0)
    assert rep["kent"]["identical_pairs"] == 0
    assert rep["kent"]["repeat_pairs"] == 0          # P014 repeats P001, which is gone
    ctrl = rep["models"]["m"]["orders"]["A"]["controls"]
    assert ctrl["identical_answered"] == 0 and ctrl["repeat_answered"] == 0
    assert rep["models"]["m"]["swap"]["pairs_in_both_orders"] == 0
    md = vj.markdown(rep)
    assert "Excluded from every read" in md and "P001, P013" in md
    assert "Swap: not run (one order only)." in md and "no API spend" in md


# ------------------------------------------------------ the 100-pair kit ----

PREREG100 = REPO / "docs" / "eye-pairs-2026-11-04" / "vlm-judge-100" / "PRE-REGISTRATION.md"


def test_the_100_pair_pre_registration_pins_prompt_seed_and_size_rule():
    text = PREREG100.read_text(encoding="utf-8")
    assert vj.prompt_sha() in text
    assert str(vj.PRO100_SEED) in text and "`--sitting-size`" in text
    assert "flags-0918-0928" in text and "off-flags-1003:cap_recentre:becker" in text
    assert f"{vj.VIEW_PX_PER_MM:g} px/mm" in text


def test_kit_pro100_builds_a_balanced_blind_kit(tmp_path, monkeypatch):
    import json as _json
    from PIL import Image
    from tools.eye_pairs import pro_pooled_build as pb
    runs, kit, art_root = tmp_path / "runs", tmp_path / "kit", tmp_path / "art"
    art_root.mkdir()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(art_root / "a.png")
    monkeypatch.setattr(pb, "FIXTURE_ART", {"fx": "a.png", "fy": "a.png"})
    pairs = []
    for i in range(10):
        fx, tree = ("fx" if i % 2 else "fy"), f"t{i % 3}"
        if i % 4 == 0:                                    # a ref-engine arm: before is another tree's base
            arm, before, after = "ref_x", ("ref", "base", {}), (tree, "base", {})
        else:
            arm, before, after = "armA", (tree, "base", {}), (tree, "armA", {"flag": True})
        pairs.append({"id": f"s:{arm}:{fx}:{i}", "sitting": "flags-0918-0928" if i < 6 else "other",
                      "arm": arm, "fixture": fx, "kent": "tie", "before_design": before, "after_design": after})
        for t, s, _kw in (before, after):
            d = pb.design_dir(runs, t, fx, s)
            d.mkdir(parents=True, exist_ok=True)
            (d / "design.json").write_text(_json.dumps({"stitches": [], "colors": []}))
    pairs.append({"id": "s:armA:fx:missing", "sitting": "other", "arm": "armA", "fixture": "fx", "kent": "tie",
                  "before_design": ("nope", "base", {}), "after_design": ("nope", "armA", {})})
    monkeypatch.setattr(pb, "labelled_pairs", lambda: pairs)

    def stub_jpg(d):
        j = d / "render.jpg"
        j.write_bytes(str(d).encode())
        return j

    summary = vj.kit_pro100(runs, kit, seed=1, exclude_ids=frozenset({pairs[0]["id"]}),
                            n_identical=2, art_root=art_root, design_jpg=stub_jpg)
    assert (summary["n_live"], summary["n_identical"], summary["n_total"]) == (9, 2, 11)
    assert summary["missing_designs"] == ["s:armA:fx:missing"] and summary["excluded"] == [pairs[0]["id"]]
    sealed = _json.loads((kit / "arms.json").read_text(encoding="utf-8"))
    listed = _json.loads((kit / "pairs.json").read_text(encoding="utf-8"))
    assert [p["pair"] for p in listed] == [f"P{i:03d}" for i in range(1, 12)]
    live = [s for s in sealed.values() if s["kind"] == "live"]
    assert sum(s["left_arm"] == "base" for s in live) == 4            # 9 // 2
    assert all({s["left_arm"], s["right_arm"]} == {"base", s["arm"]} for s in live)
    for pid, s in sealed.items():
        left = (kit / "img" / f"{pid}_L.jpg").read_bytes()
        right = (kit / "img" / f"{pid}_R.jpg").read_bytes()
        assert (left == right) == (s["kind"] == "identical"), pid
        assert (kit / "img" / f"{pid}_art.png").exists()
    text = "".join((kit / n).read_text(encoding="utf-8") for n in ("arms.json", "pairs.json", "kit.json"))
    assert "kent" not in text and "label" not in text
    # the same seed pairs the same way twice
    kit2 = tmp_path / "kit2"
    vj.kit_pro100(runs, kit2, seed=1, exclude_ids=frozenset({pairs[0]["id"]}),
                  n_identical=2, art_root=art_root, design_jpg=stub_jpg)
    assert (kit2 / "arms.json").read_text(encoding="utf-8") == (kit / "arms.json").read_text(encoding="utf-8")


def test_load_pro100_maps_kents_labels_through_the_sealed_key(tmp_path, monkeypatch):
    import json as _json
    from tools.eye_pairs import pooled
    common = {"fixture": "fx", "repeat_of": None, "design_only": False}
    sealed = {"P001": {**common, "kind": "live", "left_arm": "base", "right_arm": "armA",
                       "source_id": "a", "sitting": "flags-0918-0928", "arm": "armA"},
              "P002": {**common, "kind": "live", "left_arm": "armA", "right_arm": "base",
                       "source_id": "b", "sitting": "other", "arm": "armA"},
              "P003": {**common, "kind": "live", "left_arm": "base", "right_arm": "ref_x",
                       "source_id": "c", "sitting": "other", "arm": "ref_x"},
              "P004": {**common, "kind": "identical", "left_arm": "base", "right_arm": "base",
                       "source_id": "a", "sitting": "flags-0918-0928", "arm": "armA"}}
    (tmp_path / "arms.json").write_text(_json.dumps(sealed), encoding="utf-8")
    inputs = tmp_path / "inputs.json"
    inputs.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pooled, "INPUTS", inputs)
    monkeypatch.setattr(pooled, "pooled_pairs", lambda _inputs: [
        {"id": "a", "kent": "before"}, {"id": "b", "kent": "before"}, {"id": "c", "kent": "after"}])
    st = vj.load_pro100(tmp_path)
    assert st["picks"] == {"P001": "L", "P002": "R", "P003": "R"}
    assert st["scopes"]["flags_0918_0928_cloud_render"] == ["P001"]
    assert st["scopes"]["other_sittings"] == ["P002", "P003"]
    assert st["scopes"]["ref_engine_arms"] == ["P003"] and st["scopes"]["flag_arms"] == ["P001", "P002"]
    assert st["design_of"] == {"fx": "fx"} and st["passing_arms"] == [] and st["expected"] == {}
    judge = {"P001": "L", "P002": "R", "P003": "R", "P004": "tie"}
    v = {"m": {"A": {pid: {"pair": pid, "order": "A", "model": "m", "choice": c, "choice_frame_a": c,
                           "confidence": 4, "reason": "r", "input_tokens": 0, "output_tokens": 0,
                           "stop_reason": "end_turn"} for pid, c in judge.items()}}}
    rep = vj.analyse(st, v)
    assert rep["sitting"] == "vlm-judge-pro100"
    reads = rep["models"]["m"]["orders"]["A"]["reads"]
    assert set(reads) == {"live", "flags_0918_0928_cloud_render", "other_sittings",
                          "ref_engine_arms", "flag_arms"}
    assert reads["live"]["n_scored"] == 3 and reads["live"]["kappa_sides"] == pytest.approx(1.0)
    assert rep["kent"]["identical_pairs"] == 0            # the kit's identical pairs carry no pick of his
    ctrl = rep["models"]["m"]["orders"]["A"]["controls"]
    assert (ctrl["identical_called_tie"], ctrl["identical_answered"]) == (1, 1)
    assert "vs_kit_expected_label" not in reads and "passing_arms_only" not in reads


# ------------------------------------------------- the committed sitting ----

def test_the_committed_sitting_loads_as_the_write_up_describes():
    st = vj.load_sitting()
    kinds = [s["kind"] for s in st["sealed"].values()]
    assert (kinds.count("live"), kinds.count("identical"), kinds.count("repeat")) == (56, 4, 4)
    assert len(st["picks"]) == 64 and len(st["expected"]) == 56
    assert st["passing_arms"] == ["corner_fold_off", "inside_stagger_off", "text_lean_off"]
    assert len(set(st["design_of"].values())) == 12
