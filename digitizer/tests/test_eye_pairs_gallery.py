"""The reveal gallery, on a synthetic eye_pairs_out/ built from the
yardstick's schemas (spec 2026-09-17-eye-pairs-design.md section 3.4).
No digitize, no real logo, no real render."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import eye_pairs_gallery as g  # noqa: E402

# Restated from the yardstick spec, sections 3.2 and 3.7 / analysis.METRICS.
SPEC_ARMS = ["per_stroke", "patch_junctions", "polygon_axis", "area_weighted",
             "design_angle", "rail_comp", "wide_columns", "lettering_column",
             "phantom_dissolve", "directional_comp", "ref_0827"]
SPEC_METRICS = {
    "trims_per_1000": "lower", "preflight_raw_score": "higher",
    "preflight_blocks": "lower", "uncovered_total_mm2": "lower",
    "thread_worst_delta_e": "lower", "artfid": "higher",
    "artfid_no_colour": "higher", "artfid_coverage": "higher",
    "artfid_structure": "higher", "artfid_colour": "higher",
    "lost_elements": "lower", "lost_frac": "lower", "ragged_mm": "lower",
    "hausdorff_mm": "lower", "roughness_deg": "lower", "thin_recall": "higher",
    "legibility": "higher",
}


def _row(**kw):
    base = {"stitches": 1000, "stops": 3, "cones": 4, "trims_per_1000": 3.0,
            "artfid": 70.0, "lost_elements": 2, "ragged_mm": 0.30,
            "legibility": None, "refusals": {}, "notes": {}}
    base.update(kw)
    return base


PUBLIC = [
    {"pair": "P001", "left": "P001_L.jpg", "right": "P001_R.jpg", "art": "P001_art.png"},
    {"pair": "P002", "left": "P002_L.jpg", "right": "P002_R.jpg", "art": "P002_art.png"},
    {"pair": "P003", "left": "P003_L.jpg", "right": "P003_R.jpg", "art": "P003_art.png"},
    {"pair": "P004", "left": "P004_L.jpg", "right": "P004_R.jpg", "art": "P004_art.png"},
]
SEALED = {
    "P001": {"fixture": "fx_a", "left_arm": "per_stroke", "right_arm": "base",
             "kind": "live", "repeat_of": None},
    "P002": {"fixture": "fx_a", "left_arm": "base", "right_arm": "base",
             "kind": "identical", "repeat_of": None},
    "P003": {"fixture": "fx_b", "left_arm": "base", "right_arm": "polygon_axis",
             "kind": "live", "repeat_of": None},
    "P004": {"fixture": "fx_a", "left_arm": "base", "right_arm": "per_stroke",
             "kind": "repeat", "repeat_of": "P001"},
}
FEATS = {
    "fx_a": {"base": _row(),
             "per_stroke": _row(stitches=1100, trims_per_1000=2.0, artfid=72.0,
                                ragged_mm=0.35)},
    "fx_b": {"base": _row(artfid=60.0, refusals={"artfid": "ink ambiguous"}),
             "polygon_axis": _row(artfid=65.0, lost_elements=1,
                                  refusals={"artfid": "ink ambiguous"})},
}
SKIPPED = [{"fixture": "fx_b", "arm": "design_angle", "reason": "identical_to_base"}]
PICKS = {"P001": "L", "P002": "tie", "P003": "R", "P004": "R"}


def _img(path: Path, colour: tuple[int, int, int], size=(40, 60)) -> None:
    arr = np.zeros((size[0], size[1], 3), np.uint8)
    arr[:] = colour
    cv2.imwrite(str(path), arr)


def make_set(tmp_path: Path, picks: dict[str, str] | None = PICKS,
             renders: bool = True, extra_lines: list[dict] | None = None) -> Path:
    src = tmp_path / "eye_pairs_out"
    (src / "img").mkdir(parents=True)
    (src / "pairs.json").write_text(json.dumps(PUBLIC), encoding="utf-8")
    (src / "arms.json").write_text(json.dumps(SEALED), encoding="utf-8")
    (src / "features.json").write_text(json.dumps(FEATS), encoding="utf-8")
    (src / "skipped.json").write_text(json.dumps(SKIPPED), encoding="utf-8")
    colours = {("fx_a", "base"): (10, 10, 10), ("fx_a", "per_stroke"): (20, 20, 20),
               ("fx_b", "base"): (30, 30, 30), ("fx_b", "polygon_axis"): (40, 40, 40)}
    if renders:
        (src / "renders").mkdir()
        for (fx, arm), c in colours.items():
            _img(src / "renders" / f"{fx}__{arm}.jpg", c)
        _img(src / "renders" / "fx_a__art.png", (200, 200, 200))
        _img(src / "renders" / "fx_b__art.png", (210, 210, 210))
    for p in PUBLIC:
        s = SEALED[p["pair"]]
        _img(src / "img" / p["left"], colours[(s["fixture"], s["left_arm"])])
        _img(src / "img" / p["right"], colours[(s["fixture"], s["right_arm"])])
        _img(src / "img" / p["art"], (200, 200, 200) if s["fixture"] == "fx_a" else (210, 210, 210))
    lines = []
    if picks:
        for n, (pid, choice) in enumerate(picks.items()):
            lines.append({"pair": pid, "choice": choice, "ms": 1000 + n,
                          "ts": "2026-09-17T20:00:00", "undo_of": None})
    lines += extra_lines or []
    (src / "picks.jsonl").write_text(
        "".join(json.dumps(l) + "\n" for l in lines), encoding="utf-8")
    return src


# ---- tables ---------------------------------------------------------------

def test_arm_table_pins_the_yardstick_spec():
    assert sorted(g.ARM_INTENT) == sorted(SPEC_ARMS)
    for arm, (change, intent) in g.ARM_INTENT.items():
        assert change and intent, arm


def test_metric_table_pins_the_yardstick_spec():
    assert g.METRIC_BETTER == SPEC_METRICS


def test_tables_match_the_yardstick_package_when_it_is_here():
    try:
        from tools.eye_pairs import pairs as yp  # noqa: F401
        from tools.eye_pairs import analysis as ya
    except ImportError:
        pytest.skip("yardstick package not on this checkout")
    assert set(yp.ARMS) == set(g.ARM_INTENT)
    assert {m: d for m, d in ya.METRICS.items() if d != "none"} == g.METRIC_BETTER


# ---- picks and the refusal ------------------------------------------------

def test_last_line_wins_and_undo_returns_the_pair(tmp_path):
    src = make_set(tmp_path, picks={"P001": "L"}, extra_lines=[
        {"pair": "P001", "choice": "R", "ms": 5, "ts": "t", "undo_of": None},
        {"pair": "P001", "choice": None, "ms": 6, "ts": "t", "undo_of": "P001"},
        {"pair": "P002", "choice": "tie", "ms": 7, "ts": "t", "undo_of": None},
    ])
    picks = g.final_picks(src / "picks.jsonl")
    assert "P001" not in picks
    assert picks["P002"]["choice"] == "tie"


def test_refuses_on_a_missing_pick(tmp_path):
    src = make_set(tmp_path, picks={"P001": "L", "P002": "tie", "P003": "R"})
    with pytest.raises(SystemExit, match=r"REFUSED.*1 of 4 pairs unpicked.*P004"):
        g.build(src, tmp_path / "gallery")


def test_refuses_on_an_undone_pick(tmp_path):
    src = make_set(tmp_path, extra_lines=[
        {"pair": "P003", "choice": None, "ms": 9, "ts": "t", "undo_of": "P003"}])
    with pytest.raises(SystemExit, match="P003"):
        g.build(src, tmp_path / "gallery")


def test_refuses_on_an_unknown_pair_id(tmp_path):
    src = make_set(tmp_path, extra_lines=[
        {"pair": "P999", "choice": "L", "ms": 9, "ts": "t", "undo_of": None}])
    with pytest.raises(SystemExit, match="unknown"):
        g.build(src, tmp_path / "gallery")


def test_missing_picks_file_is_a_refusal_not_a_crash(tmp_path):
    src = make_set(tmp_path, picks=None)
    (src / "picks.jsonl").unlink()
    with pytest.raises(SystemExit, match="4 of 4"):
        g.build(src, tmp_path / "gallery")


# ---- records --------------------------------------------------------------

def _records():
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in PICKS.items()}
    return {r["pair"]: r for r in g.pair_records(PUBLIC, SEALED, picks, FEATS,
                                                 {"fx_a": (100.0, "left_chest")})}


def test_sides_and_arms_are_read_off_the_sealed_map():
    r = _records()
    assert (r["P001"]["shipped_side"], r["P001"]["arm_side"], r["P001"]["arm"]) == ("R", "L", "per_stroke")
    assert (r["P003"]["shipped_side"], r["P003"]["arm_side"], r["P003"]["arm"]) == ("L", "R", "polygon_axis")
    assert (r["P002"]["shipped_side"], r["P002"]["arm_side"], r["P002"]["arm"]) == (None, None, None)


def test_picked_arm_names_the_arm_on_the_picked_side():
    r = _records()
    assert r["P001"]["picked_arm"] == "per_stroke"   # picked L, L is per_stroke
    assert r["P003"]["picked_arm"] == "polygon_axis"  # picked R, R is polygon_axis
    assert r["P002"]["picked_arm"] == "tie"


def test_width_and_garment_come_from_the_sizes_table_or_are_blank():
    r = _records()
    assert (r["P001"]["width_mm"], r["P001"]["garment"]) == (100.0, "left_chest")
    assert (r["P003"]["width_mm"], r["P003"]["garment"]) == (None, None)


def test_arm_change_and_intent_travel_with_the_record():
    r = _records()
    assert r["P001"]["arm_change"] == g.ARM_INTENT["per_stroke"][0]
    assert r["P002"]["arm_change"] == "" and r["P002"]["arm_intent"] == ""


def test_counts_are_per_side():
    r = _records()
    assert r["P001"]["counts"]["L"]["stitches"] == 1100   # per_stroke on the left
    assert r["P001"]["counts"]["R"]["stitches"] == 1000
    assert r["P001"]["counts"]["L"]["trims_per_1000"] == 2.0


def test_repeat_consistency_compares_the_arm_chosen_not_the_side():
    r = _records()
    # P001 picked L = per_stroke; P004 (sides swapped) picked R = per_stroke.
    assert r["P004"]["consistent"] is True
    assert r["P001"]["consistent"] is None


def test_repeat_flipped_and_tie_tie():
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P004": "L"}.items()}
    r = {x["pair"]: x for x in g.pair_records(PUBLIC, SEALED, picks, FEATS, {})}
    assert r["P004"]["consistent"] is False
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P001": "tie", "P004": "tie"}.items()}
    r = {x["pair"]: x for x in g.pair_records(PUBLIC, SEALED, picks, FEATS, {})}
    assert r["P004"]["consistent"] is True


# ---- chips ----------------------------------------------------------------

def _chip(chips, metric):
    return next(c for c in chips if c["metric"] == metric)


def test_chips_follow_direction_and_agreement():
    r = _records()
    c = r["P001"]["chips"]   # arm on L, Kent picked L
    assert _chip(c, "trims_per_1000")["prefers"] == "L"    # lower is better: 2.0 < 3.0
    assert _chip(c, "trims_per_1000")["agrees"] is True
    assert _chip(c, "artfid")["prefers"] == "L"            # higher: 72 > 70
    assert _chip(c, "ragged_mm")["prefers"] == "R"         # lower: 0.30 < 0.35
    assert _chip(c, "ragged_mm")["agrees"] is False


def test_no_chip_when_null_or_equal():
    r = _records()
    names = {c["metric"] for c in r["P001"]["chips"]}
    assert "legibility" not in names       # None on both
    assert "lost_elements" not in names    # 2 == 2
    assert "stitches" not in names         # descriptive, never a chip


def test_no_chips_on_ties_or_controls():
    r = _records()
    assert r["P002"]["chips"] == []
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P001": "tie"}.items()}
    r2 = {x["pair"]: x for x in g.pair_records(PUBLIC, SEALED, picks, FEATS, {})}
    assert r2["P001"]["chips"] == []


def test_refused_metric_is_flagged_not_dropped():
    r = _records()
    art = _chip(r["P003"]["chips"], "artfid")
    assert art["refused"] is True and art["prefers"] == "R" and art["agrees"] is True
