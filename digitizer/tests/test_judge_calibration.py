"""The calibrated judge's phase A (`tools.eye_pairs.judge_calibration`): the
split is deterministic and disjoint, the committed manifest is the one the
code makes, the kit builder never reads the held-out list, and the page loads.

Kent 2026-11-07: "a side by side camparison of ambiguous photos that can point
you in the right direction." The protocol is
`docs/eye-pairs-2026-11-04/calibrated-judge/PRE-REGISTRATION.md`.
"""
from __future__ import annotations

import json
from collections import Counter

import pytest

from tools.eye_pairs import judge_calibration as jc
from tools.eye_pairs import vlm_judge as vj

PREREG = jc.OUT / "PRE-REGISTRATION.md"


@pytest.fixture(scope="module")
def committed_pool():
    return jc.pool()


# ---------------------------------------------------------------- the split ----

def test_the_pre_registration_pins_seed_fraction_bar_and_manifest(committed_pool):
    text = " ".join(PREREG.read_text(encoding="utf-8").split())
    assert f"Seed {jc.SEED}, fraction {jc.CAL_FRACTION:.2f}" in text
    assert f"kappa >= +{jc.PASS_KAPPA:.2f}" in text and f"> +{jc.PASS_CI_LOWER:.2f}" in text
    assert jc.pool_sha(committed_pool) in text
    assert vj.prompt_sha() in text
    assert f"up to {jc.KIT_MAX}" in text
    sp = jc.split(committed_pool)
    assert f"CALIBRATION {len(sp['calibration'])}" in text and f"HELD-OUT {len(sp['held_out'])}" in text
    assert f"The pool is **{len(committed_pool)}**" in text


def test_the_pool_is_the_two_judged_sets_without_a_duplicate(committed_pool):
    by_set = Counter(r["set"] for r in committed_pool)
    assert by_set == {jc.SET_1104: 54, jc.SET_1106: 99}
    assert len({r["id"] for r in committed_pool}) == len(committed_pool)
    assert {r["kent"] for r in committed_pool} <= set(vj.SIDES)


def test_the_rebuilt_1106_key_reproduces_the_committed_analysis():
    """The 11-06 kit's arms.json is gone; `pro100_sealed` rebuilds it. Scoring
    the committed verdicts through it must give the committed table."""
    sealed = vj.pro100_sealed()
    verdicts = vj.load_verdicts(vj.PRO100_OUT)["claude-opus-5-5-session"]["A"]
    table = [[0] * 3 for _ in vj.SIDES]
    for pid, s in sealed.items():
        if s["kind"] == "live":
            j = vj.to_label(verdicts[pid]["choice_frame_a"], s)
            table[vj.SIDES.index(s["kent"])][vj.SIDES.index(j)] += 1
    committed = json.loads((vj.PRO100_OUT / "analysis.json").read_text(encoding="utf-8"))
    live = committed["models"]["claude-opus-5-5-session"]["orders"]["A"]["reads"]["live"]
    assert table == live["table_kent_rows_judge_cols"]
    opp = committed["models"]["claude-opus-5-5-session"]["orders"]["A"]["opposite_side"]
    assert all((sealed[d["pair"]]["fixture"], sealed[d["pair"]]["arm"]) == (d["fixture"], d["arm"]) for d in opp)
    assert all(verdicts[p]["choice"] == "tie" for p, s in sealed.items() if s["kind"] == "identical")


def test_the_split_is_deterministic_disjoint_and_complete(committed_pool):
    a, b = jc.split(committed_pool), jc.split(list(reversed(committed_pool)))
    assert a == b
    cal, held = set(a["calibration"]), set(a["held_out"])
    assert not cal & held
    assert cal | held == {r["id"] for r in committed_pool}
    assert abs(len(cal) - round(jc.CAL_FRACTION * len(committed_pool))) <= 1
    # every stratum gets its share to within one pair
    for key in {jc.stratum(r) for r in committed_pool}:
        ids = [r["id"] for r in committed_pool if jc.stratum(r) == key]
        n_cal = sum(i in cal for i in ids)
        assert abs(n_cal - jc.CAL_FRACTION * len(ids)) < 1 + 1e-9, key
    assert jc.split(committed_pool, seed=jc.SEED + 1) != a


def test_the_committed_manifest_is_the_one_the_code_makes(committed_pool):
    for name, payload in jc.manifest_payloads(committed_pool).items():
        on_disk = json.loads((jc.OUT / name).read_text(encoding="utf-8"))
        assert on_disk == payload, name
        assert set(on_disk) == {"seed", "fraction", "n_pool", "pool_sha256", "rule", "part", "ids"}
        text = (jc.OUT / name).read_text(encoding="utf-8")
        for word in ("before", "after", "tie", "base", "kent"):     # ids only: no label, no side
            assert word not in text.lower().replace("held_out", ""), (name, word)


def test_split_refuses_to_overwrite_a_different_manifest(tmp_path, monkeypatch):
    rows = [{"id": f"s:P{i:03d}", "set": "s", "pair": f"P{i:03d}", "design": "d", "kent": "tie"}
            for i in range(10)]
    monkeypatch.setattr(jc, "pool", lambda: rows)
    assert jc.main(["split", "--out", str(tmp_path)]) == 0
    assert jc.main(["split", "--out", str(tmp_path)]) == 0          # same bytes: fine
    assert jc.main(["split", "--out", str(tmp_path), "--check"]) == 0
    rows.append({"id": "s:P999", "set": "s", "pair": "P999", "design": "d", "kent": "tie"})
    assert jc.main(["split", "--out", str(tmp_path), "--check"]) == 1
    with pytest.raises(SystemExit, match="REFUSED"):
        jc.main(["split", "--out", str(tmp_path)])


def test_primary_applies_both_halves_of_the_bar():
    perfect = [("before", "before", f"d{i % 5}") for i in range(20)] + \
              [("after", "after", f"d{i % 5}") for i in range(20)] + \
              [("tie", "tie", f"d{i % 5}") for i in range(20)]
    assert jc.primary(perfect)["passes"] is True
    ties_only = [(k, "tie", f"d{i % 5}") for i, (k, _, _) in enumerate(perfect)]
    assert jc.primary(ties_only)["passes"] is False
