import copy
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import __main__ as cli  # noqa: E402
from tools.eye_pairs.pairs import BASE, append_pick  # noqa: E402

# Measured 2026-09-17 on this image: fill_angle_deg=45 changes the stitches,
# design_angle=True does not. The second is the identical-skip rule's test.
# TWO ref arms on different commits: review finding 6 (2026-09-17) — the
# runner used to be memoised on "any ref built", and the analysis picked the
# ref bucket by name.
ARMS = {"angle45": {"fill_angle_deg": 45.0}, "inert": {"design_angle": True},
        "ref_a": {"__ref__": "aaaaaaa"}, "ref_b": {"__ref__": "bbbbbbb"}}
DELTA = {"aaaaaaa": 7, "bbbbbbb": 9}


def tiny_image(path: Path, extra_dot: bool = False) -> Path:
    img = np.full((160, 240, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 40), (110, 120), (0, 0, 0), -1)
    cv2.circle(img, (170, 80), 35, (0, 0, 200), -1)
    if extra_dot:
        cv2.circle(img, (40, 140), 6, (0, 0, 0), -1)
    cv2.imwrite(str(path), img)
    return path


def fake_factory(out: Path, seen: dict):
    """A ref-engine factory that answers per COMMIT: the base design nudged
    by a commit-specific amount, so the two refs differ from the base and
    from each other."""
    def factory(commit: str):
        seen.setdefault("commits", []).append(commit)

        def runner(image, width_mm, garment, max_colors):
            seen["asked"] = (Path(image).name, width_mm, garment, max_colors)
            design = copy.deepcopy(json.loads(
                (out / "designs" / f"tiny__{BASE}.json").read_text()))
            design["stitches"][0]["x"] += DELTA[commit]
            return design

        def closer():
            seen.setdefault("closed", []).append(commit)

        return runner, closer
    return factory


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    root = tmp_path_factory.mktemp("cli")
    art = tiny_image(root / "tiny.png")
    out = root / "out"
    seen: dict = {}
    n_arms = cli.render(out, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
                        ref_factory=fake_factory(out, seen))
    n_pairs = cli.pair(out)
    return out, art, n_arms, n_pairs, seen


def test_render_digitizes_and_pair_builds_the_sitting(rendered):
    out, _art, n_arms, n_pairs, seen = rendered
    assert n_arms == 5                                   # base + 4 arms
    sealed = json.loads((out / "arms.json").read_text())
    kinds = sorted(s["kind"] for s in sealed.values())
    # live: angle45, ref_a, ref_b. identical: 1 (one fixture). repeats: min(8, 3).
    assert kinds == ["identical", "live", "live", "live", "repeat", "repeat", "repeat"]
    assert n_pairs == 7
    assert json.loads((out / "skipped.json").read_text()) == [
        {"fixture": "tiny", "arm": "inert", "reason": "identical_to_base"}]
    assert seen["asked"] == ("tiny.png", 40.0, "left_chest", 6)
    public = json.loads((out / "pairs.json").read_text())
    for p in public:
        for k in ("left", "right", "art"):
            assert (out / "img" / p[k]).stat().st_size > 0
    assert "tiny" not in (out / "pairs.json").read_text()
    assert json.loads((out / "sitting.json").read_text())["n_pairs"] == 7


def test_each_ref_arm_runs_its_own_commit_and_is_marked_design_only(rendered):
    out, _art, _n, _np, seen = rendered
    assert sorted(seen["commits"]) == ["aaaaaaa", "bbbbbbb"]
    assert sorted(seen["closed"]) == ["aaaaaaa", "bbbbbbb"]
    feats = json.loads((out / "features.json").read_text())["tiny"]
    assert feats["ref_a"]["design_only"] is True and feats["ref_b"]["design_only"] is True
    assert not feats[BASE].get("design_only") and not feats["angle45"].get("design_only")
    da = json.loads((out / "designs" / "tiny__ref_a.json").read_text())
    db = json.loads((out / "designs" / "tiny__ref_b.json").read_text())
    assert da["stitches"][0]["x"] - db["stitches"][0]["x"] == DELTA["aaaaaaa"] - DELTA["bbbbbbb"]
    sealed = json.loads((out / "arms.json").read_text())
    for s in sealed.values():
        arm = s["right_arm"] if s["left_arm"] == BASE else s["left_arm"]
        assert s["design_only"] == (arm in ("ref_a", "ref_b"))


def test_features_are_sealed_per_arm_and_the_ref_arm_is_design_only(rendered):
    out, _art, _n, _np, _seen = rendered
    feats = json.loads((out / "features.json").read_text())["tiny"]
    assert "preflight_raw_score" in feats[BASE] and "wall_s" in feats[BASE]
    assert "preflight_raw_score" not in feats["ref_a"]
    assert feats["ref_a"]["stitches"] == feats[BASE]["stitches"]
    assert feats[BASE]["source_sha256"] == feats["ref_a"]["source_sha256"]
    assert feats[BASE]["schema"] == cli.FEATURES_SCHEMA


def test_a_second_render_is_all_cache(rendered, monkeypatch):
    out, art, n_arms, _np, _seen = rendered

    def boom(*_a, **_k):
        raise AssertionError("a finished arm must not be digitized again")

    monkeypatch.setattr(cli, "digitize_once", boom)
    assert cli.render(out, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
                      ref_factory=boom) == n_arms


def test_a_changed_source_image_is_a_cache_miss(rendered, tmp_path, monkeypatch):
    """Review finding 7 (2026-09-17): the cache was keyed on the fixture
    NAME alone, so a re-exported image under the same name stayed 'cached'."""
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out2"
    shutil.copytree(out, out2)
    art2 = tiny_image(tmp_path / "tiny.png", extra_dot=True)     # same NAME, new bytes
    calls = []
    real = cli.digitize_once

    def counting(image, cfg):
        calls.append(cfg)
        return real(image, cfg)

    monkeypatch.setattr(cli, "digitize_once", counting)
    seen: dict = {}
    cli.render(out2, cases=[("tiny", art2, 40.0, "left_chest")], arms=ARMS,
               ref_factory=fake_factory(out2, seen))
    assert len(calls) == 3                       # base + angle45 + inert, all redone
    assert sorted(seen["commits"]) == ["aaaaaaa", "bbbbbbb"]
    feats = json.loads((out2 / "features.json").read_text())["tiny"]
    old = json.loads((out / "features.json").read_text())["tiny"]
    assert feats[BASE]["source_sha256"] != old[BASE]["source_sha256"]


def test_a_schema_bump_is_a_cache_miss(rendered, tmp_path, monkeypatch):
    out, art, _n, _np, _seen = rendered
    out2 = tmp_path / "out3"
    shutil.copytree(out, out2)
    monkeypatch.setattr(cli, "FEATURES_SCHEMA", cli.FEATURES_SCHEMA + 1)
    calls = []
    real = cli.digitize_once
    monkeypatch.setattr(cli, "digitize_once",
                        lambda image, cfg: (calls.append(1), real(image, cfg))[1])
    cli.render(out2, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
               ref_factory=fake_factory(out2, {}))
    assert len(calls) == 3


def test_a_scoped_render_never_rebuilds_the_sitting(rendered, tmp_path):
    """Review finding 3 (2026-09-17): a `--fixtures/--arms` smoke test used
    to reshuffle every pair in the sitting. Render now only digitizes."""
    out, art, _n, _np, _seen = rendered
    out2 = tmp_path / "out4"
    shutil.copytree(out, out2)
    before = (out2 / "arms.json").read_bytes()
    cli.render(out2, cases=[("tiny", art, 40.0, "left_chest")],
               arms={**ARMS, "angle30": {"fill_angle_deg": 30.0}}, only_arms=["angle30"],
               ref_factory=fake_factory(out2, {}))
    assert (out2 / "arms.json").read_bytes() == before
    feats = json.loads((out2 / "features.json").read_text())["tiny"]
    assert "angle30" in feats


def test_pair_refuses_a_different_sealed_map_over_existing_picks(rendered, tmp_path):
    """Review finding 2 (2026-09-17): the guard compared the PUBLIC lists,
    which are identity-blind — an arm swap at equal count passed."""
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out5"
    shutil.copytree(out, out2)
    append_pick(out2 / "picks.jsonl", "P001", "L", 100)
    assert cli.pair(out2) == 7                              # same map: allowed
    # Swap one arm for another of the same shape: the public list is
    # byte-identical, the sealed map is not.
    feats = json.loads((out2 / "features.json").read_text())
    feats["tiny"]["angle46"] = feats["tiny"].pop("angle45")
    (out2 / "features.json").write_text(json.dumps(feats))
    (out2 / "designs" / "tiny__angle45.json").rename(out2 / "designs" / "tiny__angle46.json")
    (out2 / "renders" / "tiny__angle45.jpg").rename(out2 / "renders" / "tiny__angle46.jpg")
    with pytest.raises(SystemExit, match="REFUSED.*different"):
        cli.pair(out2)


def test_pair_refuses_picks_it_cannot_prove_belong_to_this_sitting(rendered, tmp_path):
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out6"
    shutil.copytree(out, out2)
    append_pick(out2 / "picks.jsonl", "P001", "L", 100)
    (out2 / "sitting.json").unlink()
    with pytest.raises(SystemExit, match="REFUSED.*sitting.json"):
        cli.pair(out2)


def test_reveal_refuses_until_every_pair_is_picked(rendered):
    out, _art, _n, _np, _seen = rendered
    with pytest.raises(SystemExit, match="REFUSED"):
        cli.reveal(out)


def test_reveal_reports_every_section_once_picked(rendered, tmp_path):
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out7"
    shutil.copytree(out, out2)
    for p in json.loads((out2 / "pairs.json").read_text()):
        append_pick(out2 / "picks.jsonl", p["pair"], "L", 100)
    res = cli.reveal(out2)
    assert set(res) >= {"n_pairs", "ceiling", "controls", "primary", "descriptive",
                        "exit_clause", "per_fixture", "flag_table", "ref_table",
                        "exploratory", "skipped"}
    assert res["exploratory"] is None                      # far under 40 pairs
    assert res["ceiling"]["n"] == 3
    assert {row["metric"] for row in res["primary"]} >= {"ragged_mm", "artfid"}
    assert all({"headline", "all_pairs"} <= set(row) for row in res["primary"])
    assert sorted({r["arm"] for r in res["ref_table"]}) == ["ref_a", "ref_b"]
    assert json.loads((out2 / "results.json").read_text())["n_pairs"] == res["n_pairs"]


def test_reveal_refuses_a_pick_for_a_pair_that_does_not_exist(rendered, tmp_path):
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out8"
    shutil.copytree(out, out2)
    for p in json.loads((out2 / "pairs.json").read_text()):
        append_pick(out2 / "picks.jsonl", p["pair"], "R", 100)
    append_pick(out2 / "picks.jsonl", "P999", "L", 1)
    with pytest.raises(SystemExit, match="REFUSED.*P999"):
        cli.reveal(out2)


def test_verify_finds_no_drift_on_the_synthetic_image(rendered, capsys):
    _out, art, _n, _np, _seen = rendered
    assert cli.verify(art, 40.0, "left_chest") is True
    printed = capsys.readouterr().out
    # Review finding 8: the artfid family and the refusal are checked too.
    assert "artfid" in printed and "refusal" in printed
