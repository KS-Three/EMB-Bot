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
             "design_angle", "rails_follow_edge", "rail_comp", "wide_columns",
             "lettering_column", "phantom_dissolve", "directional_comp", "ref_0827"]
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


def test_chips_carry_direction_only_never_the_values():
    # acceptance_ab's rule: no scorecard number on a review sheet. The values
    # live in features.json for whoever needs them; the page gets the sign.
    r = _records()
    for c in r["P001"]["chips"]:
        assert set(c) == {"metric", "prefers", "agrees", "refused"}


# ---- the 08-27 engine arm -------------------------------------------------

REF_PUBLIC = [{"pair": "P010", "left": "P010_L.jpg", "right": "P010_R.jpg", "art": "P010_art.png"},
              {"pair": "P011", "left": "P011_L.jpg", "right": "P011_R.jpg", "art": "P011_art.png"}]
REF_SEALED = {"P010": {"fixture": "fx_a", "left_arm": "base", "right_arm": "ref_0827",
                       "kind": "live", "repeat_of": None},
              "P011": {"fixture": "fx_p", "left_arm": "ref_0827", "right_arm": "base",
                       "kind": "live", "repeat_of": None}}
REF_FEATS = {"fx_a": {"base": _row(design_class="flat"), "ref_0827": _row(stitches=900)},
             "fx_p": {"base": _row(design_class="photo_subject"), "ref_0827": _row(stitches=900)}}


def test_photo_classes_pin_the_pipeline_config():
    from digitizer_core.config import PHOTO_CLASSES
    assert tuple(g.PHOTO_CLASSES) == tuple(PHOTO_CLASSES)


def test_ref_arm_is_marked_and_a_photo_fixture_is_confounded():
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {"P010": "R", "P011": "R"}.items()}
    r = {x["pair"]: x for x in g.pair_records(REF_PUBLIC, REF_SEALED, picks, REF_FEATS, {})}
    assert r["P010"]["is_ref"] is True and r["P010"]["confounded"] is False
    assert r["P011"]["is_ref"] is True and r["P011"]["confounded"] is True
    live = _records()
    assert live["P001"]["is_ref"] is False and live["P001"]["confounded"] is False
    # P010: Kent picked R = the old engine; P011: picked R = today's.
    t = g.arm_tally(list(r.values()), [])
    assert (t["ref_0827"]["wins"], t["ref_0827"]["losses"]) == (1, 1)


# ---- tallies --------------------------------------------------------------

def test_arm_tally_counts_live_pairs_only_and_identical_skips():
    recs = list(_records().values())
    t = g.arm_tally(recs, SKIPPED)
    assert t["per_stroke"] == {"wins": 1, "losses": 0, "ties": 0, "skipped": 0,
                               "by_fixture": {"fx_a": "win"}}   # the repeat P004 is not counted
    assert t["polygon_axis"]["wins"] == 1
    assert t["design_angle"] == {"wins": 0, "losses": 0, "ties": 0, "skipped": 1,
                                 "by_fixture": {}}
    assert g.BASE not in t


def test_arm_tally_loss_and_tie():
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P001": "R", "P003": "tie"}.items()}
    recs = g.pair_records(PUBLIC, SEALED, picks, FEATS, {})
    t = g.arm_tally(recs, [])
    assert (t["per_stroke"]["losses"], t["per_stroke"]["by_fixture"]) == (1, {"fx_a": "loss"})
    assert (t["polygon_axis"]["ties"], t["polygon_axis"]["by_fixture"]) == (1, {"fx_b": "tie"})


def test_fixture_sizes_reads_the_real_art_table():
    sizes = g.fixture_sizes()
    assert sizes["becker"] == (100.0, "left_chest")
    assert sizes["fremont"] == (92.5, "patch")


# ---- images ---------------------------------------------------------------

def test_images_are_deduplicated_by_content(tmp_path):
    src = make_set(tmp_path)
    names, total = g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img")
    files = sorted(p.name for p in (tmp_path / "g" / "img").iterdir())
    # 4 distinct renders + 2 artworks; P001/P002/P004 share fx_a base, P002 is base|base.
    assert len(files) == 6
    assert names["P001"]["R"] == names["P002"]["L"] == names["P002"]["R"] == names["P004"]["L"]
    assert names["P001"]["L"] == names["P004"]["R"]
    assert names["P001"]["art"] == names["P002"]["art"] == names["P004"]["art"]
    assert names["P003"]["art"] != names["P001"]["art"]
    assert all(v.startswith("img/") for v in names["P001"].values())
    assert total == sum((tmp_path / "g" / "img" / f).stat().st_size for f in files)


def test_images_fall_back_to_the_per_pair_copies_without_renders(tmp_path):
    src = make_set(tmp_path, renders=False)
    names, _ = g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img")
    assert len(list((tmp_path / "g" / "img").iterdir())) == 6
    assert names["P001"]["R"] == names["P004"]["L"]


def test_renders_are_capped_to_the_long_edge(tmp_path, monkeypatch):
    src = make_set(tmp_path)
    big = np.zeros((300, 3000, 3), np.uint8)
    cv2.imwrite(str(src / "renders" / "fx_a__base.jpg"), big)
    monkeypatch.setattr(g, "MAX_EDGE", 1000)
    names, _ = g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img")
    out = cv2.imread(str(tmp_path / "g" / names["P001"]["R"]))
    assert out.shape[1] == 1000 and out.shape[0] == 100


def test_over_budget_is_refused_with_the_total_named(tmp_path):
    src = make_set(tmp_path)
    with pytest.raises(SystemExit, match=r"REFUSED: gallery images total .* over the 0 MB"):
        g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img", budget=10)


def test_missing_source_image_is_a_refusal_not_a_traceback(tmp_path):
    src = make_set(tmp_path, renders=False)
    (src / "img" / "P003_R.jpg").unlink()
    with pytest.raises(SystemExit, match=r"REFUSED: .*P003_R\.jpg"):
        g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img")


# ---- html and the whole build ---------------------------------------------

def _strip_style(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "", html, flags=re.S)


def test_build_writes_index_and_every_referenced_image_exists(tmp_path):
    src = make_set(tmp_path)
    out = tmp_path / "gallery"
    data = g.build(src, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert g.DATA_TOKEN not in html
    refs = set(re.findall(r'img/[0-9a-f]{12}\.(?:jpg|png)', html))
    assert refs and all((out / r).exists() for r in refs)
    assert data["n_pairs"] == 4
    assert data["pairs"][0]["img"]["L"].startswith("img/")
    assert set(data["arms"]) == {"per_stroke", "polygon_axis", "design_angle"}
    assert data["arms"]["design_angle"]["skipped"] == 1
    assert data["arms"]["per_stroke"]["intent"] == g.ARM_INTENT["per_stroke"][1]


def test_html_carries_no_absolute_path_and_no_percent_outside_css(tmp_path):
    src = make_set(tmp_path)
    out = tmp_path / "gallery"
    g.build(src, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert str(tmp_path) not in html and "C:\\" not in html and 'src="/' not in html
    assert "%" not in _strip_style(html)


def test_inlined_json_cannot_close_the_script_tag():
    html = g.build_html({"pairs": [{"arm_intent": "a </script> b"}], "arms": {},
                         "generated": "d", "n_pairs": 1})
    assert "</script> b" not in html and "<\\/script> b" in html


def test_cli_refuses_before_the_sitting_is_complete(tmp_path, capsys):
    src = make_set(tmp_path, picks={"P001": "L"})
    with pytest.raises(SystemExit, match="3 of 4"):
        g.main(["--src", str(src), "--out", str(tmp_path / "gallery")])


def test_cli_builds_and_prints_the_totals(tmp_path, capsys):
    src = make_set(tmp_path)
    assert g.main(["--src", str(src), "--out", str(tmp_path / "gallery")]) == 0
    out = capsys.readouterr().out
    assert "4 pairs" in out and "6 images" in out and "index.html" in out


# ---- labelled mode --------------------------------------------------------
# Before | after with the arm named, built from --render's output alone: no
# pairs.json, no arms.json, no picks.jsonl. Kent's 2026-09-18 flag-review page.

LAB_FEATS = {
    "fx_a": {"base": _row(design_class="flat"),
             "per_stroke": _row(stitches=1100, trims_per_1000=2.0, artfid=72.0,
                                ragged_mm=0.35),
             "design_angle": _row(),                       # same stitches as base below
             "wide_columns": {"error": "ValueError: boom"}},
    "fx_p": {"base": _row(design_class="photo_subject"),
             "ref_0827": _row(stitches=900, design_only=True)},
}
LAB_STITCHES = {("fx_a", "base"): [[0, 0], [1, 1]], ("fx_a", "per_stroke"): [[0, 0], [2, 2]],
                ("fx_a", "design_angle"): [[0, 0], [1, 1]],
                ("fx_p", "base"): [[5, 5], [6, 6]], ("fx_p", "ref_0827"): [[5, 5], [7, 7]]}


def make_labelled_set(tmp_path: Path) -> Path:
    src = tmp_path / "eye_pairs_out"
    (src / "designs").mkdir(parents=True)
    (src / "renders").mkdir()
    (src / "features.json").write_text(json.dumps(LAB_FEATS), encoding="utf-8")
    for n, ((fx, arm), st) in enumerate(LAB_STITCHES.items()):
        (src / "designs" / f"{fx}__{arm}.json").write_text(json.dumps({"stitches": st}),
                                                           encoding="utf-8")
        _img(src / "renders" / f"{fx}__{arm}.jpg", (10 * n + 5,) * 3)
    _img(src / "renders" / "fx_a__art.png", (200, 200, 200))
    _img(src / "renders" / "fx_p__art.png", (210, 210, 210))
    return src


def test_labelled_builds_without_a_sitting(tmp_path):
    src = make_labelled_set(tmp_path)
    out = tmp_path / "gallery"
    data = g.build(src, out, labelled=True)
    assert not (src / "picks.jsonl").exists() and not (src / "pairs.json").exists()
    assert data["labelled"] is True and data["n_pairs"] == 2
    # Spec-order arms, readable ids: a note keyed by one survives a rebuild.
    assert [p["pair"] for p in data["pairs"]] == ["per_stroke__fx_a", "ref_0827__fx_p"]
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "<title>Flag Before After</title>" in html and g.TITLE_TOKEN not in html
    refs = set(re.findall(r'img/[0-9a-f]{12}\.(?:jpg|png)', html))
    assert refs and all((out / r).exists() for r in refs)
    assert "%" not in _strip_style(html)


def test_labelled_before_is_left_for_a_flag_and_the_old_engine_for_the_ref(tmp_path):
    data = g.build(make_labelled_set(tmp_path), tmp_path / "g", labelled=True)
    flag, ref = data["pairs"]
    assert (flag["shipped_side"], flag["arm_side"], flag["is_ref"]) == ("L", "R", False)
    assert (flag["counts"]["L"]["stitches"], flag["counts"]["R"]["stitches"]) == (1000, 1100)
    assert (ref["shipped_side"], ref["arm_side"], ref["is_ref"], ref["confounded"]) == ("R", "L", True, True)
    assert (ref["counts"]["L"]["stitches"], ref["counts"]["R"]["stitches"]) == (900, 1000)
    assert flag["pick"] is None and flag["picked_arm"] is None and flag["kind"] == "live"
    assert flag["img"]["L"] != flag["img"]["R"] and flag["img"]["art"] != ref["img"]["art"]


def test_labelled_skips_identical_arms_and_counts_failures_but_never_scores(tmp_path):
    data = g.build(make_labelled_set(tmp_path), tmp_path / "g", labelled=True)
    arms = data["arms"]
    assert list(arms) == ["per_stroke", "design_angle", "wide_columns", "ref_0827"]
    assert arms["design_angle"] == {"change": g.ARM_INTENT["design_angle"][0],
                                    "intent": g.ARM_INTENT["design_angle"][1],
                                    "is_ref": False, "n_pairs": 0, "skipped": 1, "failed": 0}
    assert (arms["wide_columns"]["failed"], arms["wide_columns"]["n_pairs"]) == (1, 0)
    assert (arms["per_stroke"]["n_pairs"], arms["ref_0827"]["is_ref"]) == (1, True)
    # A null pick is not a loss: the page counts verdicts as Kent gives them.
    for a in arms.values():
        assert not {"wins", "losses", "ties", "by_fixture"} & set(a)
    assert data["_skipped"] == [{"fixture": "fx_a", "arm": "design_angle",
                                 "reason": "identical_to_base"}]
    assert data["_failed"] == [{"fixture": "fx_a", "arm": "wide_columns",
                                "reason": "ValueError: boom"}]


def test_labelled_chips_carry_direction_and_refusal_only(tmp_path):
    data = g.build(make_labelled_set(tmp_path), tmp_path / "g", labelled=True)
    chips = data["pairs"][0]["chips"]
    assert chips and all(set(c) == {"metric", "prefers", "refused"} for c in chips)
    assert _chip(chips, "trims_per_1000")["prefers"] == "R"   # lower is better: the arm, on the right
    assert _chip(chips, "ragged_mm")["prefers"] == "L"


def test_labelled_refuses_on_a_missing_render_or_design(tmp_path):
    src = make_labelled_set(tmp_path)
    (src / "renders" / "fx_a__per_stroke.jpg").unlink()
    with pytest.raises(SystemExit, match=r"REFUSED: .*fx_a__per_stroke\.jpg"):
        g.build(src, tmp_path / "g", labelled=True)
    src2 = make_labelled_set(tmp_path / "two")
    (src2 / "designs" / "fx_a__per_stroke.json").unlink()
    with pytest.raises(SystemExit, match=r"REFUSED: .*fx_a / per_stroke"):
        g.build(src2, tmp_path / "g2", labelled=True)


def test_labelled_ids_survive_a_new_arm(tmp_path):
    src = make_labelled_set(tmp_path)
    before = g.build(src, tmp_path / "g1", labelled=True)
    feats = json.loads((src / "features.json").read_text(encoding="utf-8"))
    feats["fx_a"]["polygon_axis"] = _row(stitches=1200)
    (src / "features.json").write_text(json.dumps(feats), encoding="utf-8")
    (src / "designs" / "fx_a__polygon_axis.json").write_text(json.dumps({"stitches": [[9, 9]]}),
                                                             encoding="utf-8")
    _img(src / "renders" / "fx_a__polygon_axis.jpg", (77, 77, 77))
    after = g.build(src, tmp_path / "g2", labelled=True)
    assert {p["pair"] for p in before["pairs"]} < {p["pair"] for p in after["pairs"]}


def test_reveal_build_keeps_its_title_and_is_not_labelled(tmp_path):
    data = g.build(make_set(tmp_path), tmp_path / "gallery")
    html = (tmp_path / "gallery" / "index.html").read_text(encoding="utf-8")
    assert "<title>Eye Pairs Reveal</title>" in html and g.TITLE_TOKEN not in html
    assert data["labelled"] is False


def test_cli_labelled_prints_the_skips_and_failures(tmp_path, capsys):
    src = make_labelled_set(tmp_path)
    assert g.main(["--src", str(src), "--out", str(tmp_path / "g"), "--labelled"]) == 0
    out = capsys.readouterr().out
    assert "2 pairs" in out and "1 arm-runs identical" in out and "1 failed" in out
    assert "FAILED fx_a / wide_columns: ValueError: boom" in out
