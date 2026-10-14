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


@pytest.mark.parametrize("kw, digest", [
    ({}, "f9fba8281d8d318cf5740e5d226426027238a662667a8ce855526a28aca404bd"),
    ({"seed": 7}, "dadef395a28220f242f77d4c52bfbdaa64e995e753ca288420c21fd7d0f2cdfd"),
    ({"seed": 7, "n_identical": 2, "n_repeat": 6},
     "ceb0b28af3412667a2f7887bc9f392dba4012f02f9f58a494562c2fa2285b093"),
], ids=["shipped-seed", "seed-7", "seed-7-small-controls"])
def test_the_sitting_a_seed_builds_is_pinned(kw, digest):
    """Captured 2026-09-18 from the implementation PR #506 shipped, BEFORE
    `build_pairs` was restructured, so that refactor — and the next — is
    held to byte-identical output. Not a platform golden: this is pure
    `random.Random` over strings, and the three digests were checked equal
    on Python 3.12.10 (CI's) and 3.14.6 (Kent's).

    Why it is worth a pin at all: the sealed map IS the identity of a
    sitting. A change that reshuffles it makes `--pair` refuse a sitting
    that already has picks — loudly, but after the fact. If this fails, the
    order Kent will be shown has changed. Re-pin only on purpose, and never
    while a sitting with picks is waiting on `--reveal`."""
    import hashlib
    blob = json.dumps(ep.build_pairs(runs(), **kw), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(blob.encode()).hexdigest() == digest


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


def test_a_pick_is_stamped_with_its_utc_offset(tmp_path):
    """Review 2026-09-17: `ts` was naive local time. picks.jsonl is the one
    file here that is not regenerable and is committed as the audit trail;
    a stamp with no offset cannot be ordered against a CI log, a commit, or
    a pick made across a DST change."""
    import re
    from datetime import datetime, timezone
    log = tmp_path / "picks.jsonl"
    ep.append_pick(log, "P001", "L", 900)
    ts = json.loads(log.read_text(encoding="utf-8").splitlines()[0])["ts"]
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", ts), ts
    stamped = datetime.fromisoformat(ts)
    assert stamped.utcoffset() is not None
    assert abs((datetime.now(timezone.utc) - stamped).total_seconds()) < 60
    # A caller's own stamp is still written as given.
    ep.append_pick(log, "P002", "R", 1, ts="t1")
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[1])["ts"] == "t1"


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

def _arm_on_left(sealed):
    live = [s for s in sealed.values() if s["kind"] == "live"]
    return sum(1 for s in live if s["left_arm"] != ep.BASE), len(live)


@pytest.mark.parametrize("seed", [1, 7, 20260917, 20261013])
def test_balance_live_puts_the_arm_on_the_left_in_exactly_half_the_live_pairs(seed):
    _p, sealed, _s = ep.build_pairs(runs(), seed=seed, n_identical=4, n_repeat=4,
                                    balance_live=True)
    left, n = _arm_on_left(sealed)
    assert n == 12 and left == 6


def test_balance_live_takes_the_extra_pair_on_the_right_when_the_count_is_odd():
    _p, sealed, _s = ep.build_pairs(runs(identical={("becker", "design_angle")}), seed=3,
                                    n_identical=2, n_repeat=0, balance_live=True)
    left, n = _arm_on_left(sealed)
    assert n == 11 and left == 5


def test_without_balance_live_the_live_pairs_alone_can_be_lopsided():
    """Why the option exists: the half is taken over live + identical, and an
    identical pair shows no arm."""
    counts = {_arm_on_left(ep.build_pairs(runs(), seed=s, n_identical=4, n_repeat=0)[1])[0]
              for s in range(40)}
    assert counts - {6}


def test_a_repeat_still_shows_the_other_side_under_balance_live():
    _p, sealed, _s = ep.build_pairs(runs(), seed=5, n_identical=2, n_repeat=4, balance_live=True)
    for s in sealed.values():
        if s["kind"] == "repeat":
            orig = sealed[s["repeat_of"]]
            assert (s["left_arm"], s["right_arm"]) == (orig["right_arm"], orig["left_arm"])


def test_no_arm_equals_the_base():
    """The retirement rule in `pairs.py`: an arm whose every flag already
    equals the config default IS the base, and would pair as
    `identical_to_base` on every fixture. A flag that ships ON (or a default
    that moves) must take its arm out of the table in the same change."""
    from digitizer_core.config import PipelineConfig
    base = PipelineConfig()
    fields = set(PipelineConfig.__dataclass_fields__)
    for arm, kw in ep.ARMS.items():
        if "__ref__" in kw or "__file__" in kw:
            continue                       # an older engine / a pro's file
        assert kw, arm
        assert set(kw) <= fields, (arm, sorted(set(kw) - fields))
        same = [k for k, v in kw.items() if getattr(base, k) == v]
        assert not same, (
            f"arm {arm!r} sets {same} to what the config already defaults to; "
            "retire the arm (or drop the flag) -- see the rule in pairs.py")
