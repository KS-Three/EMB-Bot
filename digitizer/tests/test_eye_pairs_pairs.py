import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import pairs as ep  # noqa: E402

FIXTURES = ["becker", "fremont", "gaulke", "drone"]
ARM_IDS = ["per_stroke", "polygon_axis", "design_angle"]


def runs(identical=()):
    out = []
    for fx in FIXTURES:
        out.append(ep.ArmRun(fx, ep.BASE, f"h-{fx}"))
        for arm in ARM_IDS:
            same = (fx, arm) in identical
            out.append(ep.ArmRun(fx, arm, f"h-{fx}" if same else f"h-{fx}-{arm}"))
    return out


def test_same_seed_same_pairs():
    assert ep.build_pairs(runs(), seed=7) == ep.build_pairs(runs(), seed=7)
    assert ep.build_pairs(runs(), seed=7)[0] != ep.build_pairs(runs(), seed=8)[0] \
        or ep.build_pairs(runs(), seed=7)[1] != ep.build_pairs(runs(), seed=8)[1]


def test_an_arm_identical_to_base_is_skipped_and_logged():
    public, sealed, skipped = ep.build_pairs(runs(identical={("becker", "design_angle")}),
                                             n_identical=0, n_repeat=0)
    assert skipped == [{"fixture": "becker", "arm": "design_angle",
                        "reason": "identical_to_base"}]
    assert len(public) == len(FIXTURES) * len(ARM_IDS) - 1
    assert not any(s["fixture"] == "becker" and "design_angle" in (s["left_arm"], s["right_arm"])
                   for s in sealed.values())


def test_control_counts_are_honoured():
    _public, sealed, _ = ep.build_pairs(runs(), n_identical=3, n_repeat=5)
    kinds = [s["kind"] for s in sealed.values()]
    assert kinds.count("identical") == 3
    assert kinds.count("repeat") == 5
    assert kinds.count("live") == len(FIXTURES) * len(ARM_IDS)
    for s in sealed.values():
        if s["kind"] == "identical":
            assert s["left_arm"] == s["right_arm"] == ep.BASE


def test_a_repeat_swaps_sides_and_never_sits_beside_its_original():
    public, sealed, _ = ep.build_pairs(runs(), n_identical=2, n_repeat=6)
    order = [p["pair"] for p in public]
    for pid, s in sealed.items():
        if s["kind"] != "repeat":
            continue
        orig = sealed[s["repeat_of"]]
        assert orig["kind"] == "live" and orig["fixture"] == s["fixture"]
        assert (s["left_arm"], s["right_arm"]) == (orig["right_arm"], orig["left_arm"])
        assert abs(order.index(pid) - order.index(s["repeat_of"])) >= 2


def test_sides_are_balanced():
    _public, sealed, _ = ep.build_pairs(runs(), n_identical=0, n_repeat=0)
    base_left = sum(1 for s in sealed.values() if s["left_arm"] == ep.BASE)
    assert abs(base_left - (len(sealed) - base_left)) <= 1


def test_design_only_is_a_stored_fact_on_the_sealed_map():
    """Review finding 6 (2026-09-17): the analysis used to pick the ref
    bucket by the literal arm NAME. A second `__ref__` row would have been
    scored in the flag bucket. The capability is stored, not inferred."""
    rs = runs() + [ep.ArmRun("becker", "ref_0901", "h-old", design_only=True)]
    _public, sealed, _ = ep.build_pairs(rs, n_identical=1, n_repeat=0)
    by_arm = {}
    for s in sealed.values():
        arm = s["right_arm"] if s["left_arm"] == ep.BASE else s["left_arm"]
        by_arm.setdefault(arm, set()).add(s["design_only"])
    assert by_arm["ref_0901"] == {True}
    assert by_arm["per_stroke"] == {False}
    assert by_arm[ep.BASE] == {False}          # the identical control


def test_the_public_file_leaks_nothing():
    public, _sealed, _ = ep.build_pairs(runs())
    text = json.dumps(public)
    for secret in FIXTURES + ARM_IDS + list(ep.ARMS) + [ep.BASE, "satin", "flag"]:
        assert secret not in text, secret
    assert set(public[0]) == {"pair", "left", "right", "art"}


def test_picks_are_append_only_and_the_last_line_wins(tmp_path):
    log = tmp_path / "picks.jsonl"
    ep.append_pick(log, "P001", "L", 900, ts="t0")
    ep.append_pick(log, "P002", "tie", 700, ts="t1")
    ep.append_pick(log, "P001", "R", 400, ts="t2")
    assert len(log.read_text(encoding="utf-8").splitlines()) == 3
    picks = ep.load_picks(log)
    assert picks["P001"]["choice"] == "R" and picks["P002"]["choice"] == "tie"


def test_undo_returns_the_pair_to_the_queue(tmp_path):
    log = tmp_path / "picks.jsonl"
    ep.append_pick(log, "P001", "L", 900, ts="t0")
    ep.append_pick(log, "P001", None, 0, undo_of="P001", ts="t1")
    picks = ep.load_picks(log)
    assert "P001" not in picks
    assert ep.unpicked(["P001", "P002"], picks) == ["P001", "P002"]


def test_a_bad_choice_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ep.append_pick(tmp_path / "picks.jsonl", "P001", "left", 1)


def test_a_missing_log_is_no_picks(tmp_path):
    assert ep.load_picks(tmp_path / "nope.jsonl") == {}
