import copy
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import __main__ as cli  # noqa: E402
from tools.eye_pairs.pairs import BASE, REF_ARM, append_pick  # noqa: E402

# Measured 2026-09-17 on this image: fill_angle_deg=45 changes the stitches,
# design_angle=True does not. The second is the identical-skip rule's test.
ARMS = {"angle45": {"fill_angle_deg": 45.0}, "inert": {"design_angle": True},
        REF_ARM: {"__ref__": "unused-in-tests"}}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    root = tmp_path_factory.mktemp("cli")
    img = np.full((160, 240, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 40), (110, 120), (0, 0, 0), -1)
    cv2.circle(img, (170, 80), 35, (0, 0, 200), -1)
    art = root / "tiny.png"
    cv2.imwrite(str(art), img)
    out = root / "out"
    seen = {}

    def fake_old_engine(image, width_mm, garment, max_colors):
        seen["asked"] = (Path(image).name, width_mm, garment, max_colors)
        design = copy.deepcopy(json.loads((out / "designs" / f"tiny__{BASE}.json").read_text()))
        design["stitches"][0]["x"] += 7           # "an older engine sewed it differently"
        return design

    n = cli.render(out, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
                   ref_runner=fake_old_engine)
    return out, n, seen


def test_render_builds_blind_pairs_and_skips_the_inert_arm(rendered):
    out, n, seen = rendered
    sealed = json.loads((out / "arms.json").read_text())
    kinds = sorted(s["kind"] for s in sealed.values())
    # live: angle45 + ref. identical: 1 (one fixture). repeats: min(8, 2).
    assert kinds == ["identical", "live", "live", "repeat", "repeat"] and n == 5
    assert json.loads((out / "skipped.json").read_text()) == [
        {"fixture": "tiny", "arm": "inert", "reason": "identical_to_base"}]
    assert seen["asked"] == ("tiny.png", 40.0, "left_chest", 6)
    public = json.loads((out / "pairs.json").read_text())
    for p in public:
        for k in ("left", "right", "art"):
            assert (out / "img" / p[k]).stat().st_size > 0
    assert "tiny" not in (out / "pairs.json").read_text()


def test_features_are_sealed_per_arm_and_the_ref_arm_is_design_only(rendered):
    out, _n, _seen = rendered
    feats = json.loads((out / "features.json").read_text())["tiny"]
    assert "preflight_raw_score" in feats[BASE] and "wall_s" in feats[BASE]
    assert "preflight_raw_score" not in feats[REF_ARM]
    assert feats[REF_ARM]["stitches"] == feats[BASE]["stitches"]


def test_a_second_render_is_all_cache(rendered, monkeypatch):
    out, n, _seen = rendered

    def boom(*_a, **_k):
        raise AssertionError("a finished arm must not be digitized again")

    monkeypatch.setattr(cli, "digitize_once", boom)
    art = out.parent / "tiny.png"
    assert cli.render(out, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
                      ref_runner=boom) == n


def test_reveal_refuses_until_every_pair_is_picked(rendered):
    out, _n, _seen = rendered
    with pytest.raises(SystemExit, match="REFUSED"):
        cli.reveal(out)


def test_reveal_reports_every_section_once_picked(rendered):
    out, _n, _seen = rendered
    for p in json.loads((out / "pairs.json").read_text()):
        append_pick(out / "picks.jsonl", p["pair"], "L", 100)
    res = cli.reveal(out)
    assert set(res) >= {"n_pairs", "ceiling", "controls", "primary", "descriptive",
                        "exit_clause", "per_fixture", "flag_table", "ref_table",
                        "exploratory", "skipped"}
    assert res["exploratory"] is None                      # far under 40 pairs
    assert res["ceiling"]["n"] == 2
    assert {row["metric"] for row in res["primary"]} >= {"ragged_mm", "artfid"}
    assert all({"headline", "all_pairs"} <= set(row) for row in res["primary"])
    assert json.loads((out / "results.json").read_text())["n_pairs"] == res["n_pairs"]
    (out / "picks.jsonl").unlink()


def test_reveal_refuses_a_pick_for_a_pair_that_does_not_exist(rendered):
    out, _n, _seen = rendered
    for p in json.loads((out / "pairs.json").read_text()):
        append_pick(out / "picks.jsonl", p["pair"], "R", 100)
    append_pick(out / "picks.jsonl", "P999", "L", 1)
    with pytest.raises(SystemExit, match="REFUSED.*P999"):
        cli.reveal(out)
    (out / "picks.jsonl").unlink()


def test_verify_finds_no_drift_on_the_synthetic_image(rendered):
    out, _n, _seen = rendered
    assert cli.verify(out.parent / "tiny.png", 40.0, "left_chest") is True
