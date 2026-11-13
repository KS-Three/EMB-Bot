"""`tools.inconsistency_fault_reader` pure helpers and its pin list. No engine.

Synthetic top-thread / run-kind rasters at the reader's own 12 px/mm: like
shapes sewn alike (silent), one of three sewn in another colour or run kind
(only it flagged), a pair that disagrees (both flagged), rotated bars sewn
the same way relative to their own axis (silent), and an outlined sibling.
"""
import json
from pathlib import Path

import numpy as np

from tools import fault_reader_harness as h
from tools import inconsistency_fault_reader as ifr

DOCS = Path(__file__).resolve().parents[2] / "docs"
K = {k: i for i, k in enumerate(ifr.KINDS)}


def _disc(shape, cx, cy, r):
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def _canvas(shape=(160, 400)):
    return np.full(shape, -1, np.int16), np.full(shape, 255, np.uint8)


def _put(thr, kind, m, cls, k="fill"):
    thr[m] = cls
    kind[m] = K[k]


def test_constants_are_the_documented_ones():
    doc = (DOCS / "inconsistency-fault-reader-2026-11-12.md").read_text(encoding="utf-8")
    for name in ("MIN_HALF_MM", "AREA_RATIO", "ELONG_RATIO", "SOLIDITY_DIFF", "ROUND_ELONG", "ANGLE_MIN_SEGS",
                 "ANGLE_MIN_R", "ANGLE_TOL_DEG", "RIM_MM", "OUTLINED", "PLAIN", "SPACING_MM"):
        assert f"`{name}`" in doc, name
    assert (ifr.AREA_RATIO, ifr.ELONG_RATIO, ifr.SOLIDITY_DIFF) == (1.5, 1.25, 0.10)
    assert (ifr.ROUND_ELONG, ifr.ANGLE_MIN_SEGS, ifr.ANGLE_MIN_R, ifr.ANGLE_TOL_DEG) == (1.5, 3, 0.5, 45.0)
    assert ifr.MIN_HALF_MM == ifr.THREAD_MM == 0.4 and ifr.SPACING_MM == 2.0
    from tools import infill_fault_reader as inf
    assert (ifr.RIM_MM, ifr.OUTLINED, ifr.PLAIN, ifr.KINDS) == (inf.RIM_MM, inf.OUTLINED, inf.PLAIN, inf.KINDS)


def test_three_alike_discs_sewn_alike_are_silent_but_candidates():
    thr, kind = _canvas()
    for cx in (60, 200, 340):
        _put(thr, kind, _disc(thr.shape, cx, 80, 30), 0)
    flags, cands, cand, mem = ifr.read_shapes(thr, kind)
    assert len(mem) == 3 and len({g["group"] for g in mem}) == 1
    assert flags == [] and len(cands) >= 3 and cand.any()


def test_one_of_three_in_another_colour_is_the_only_flag():
    thr, kind = _canvas()
    for cx, c in ((60, 0), (200, 0), (340, 1)):
        _put(thr, kind, _disc(thr.shape, cx, 80, 30), c)
    flags, _c, _m, mem = ifr.read_shapes(thr, kind)
    assert [g["odd"] for g in mem] == [[], [], ["colour"]]
    assert flags and all(f["shape"] == 2 and f["odd"] == ["colour"] for f in flags)
    assert all(f["x_mm"] >= 23.8 for f in flags)                 # on the right-hand disc (23.8-28.8 mm)


def test_a_pair_that_disagrees_flags_both():
    thr, kind = _canvas()
    _put(thr, kind, _disc(thr.shape, 100, 80, 30), 0, "fill")
    _put(thr, kind, _disc(thr.shape, 300, 80, 30), 0, "satin")
    _f, _c, _m, mem = ifr.read_shapes(thr, kind)
    assert [g["odd"] for g in mem] == [["kind"], ["kind"]]


def test_unlike_shapes_are_never_compared():
    thr, kind = _canvas()
    _put(thr, kind, _disc(thr.shape, 80, 80, 40), 0)
    _put(thr, kind, _disc(thr.shape, 300, 80, 15), 1)            # 7x smaller: not alike
    flags, cands, _m, mem = ifr.read_shapes(thr, kind)
    assert len({g["group"] for g in mem}) == 2 and flags == [] and cands == []


def test_thin_sliver_is_not_a_shape():
    thr, kind = _canvas()
    thr[50:54, 20:300] = 0                                       # 4 px = 0.33 mm across: under two filaments
    kind[50:54, 20:300] = K["fill"]
    assert ifr.read_shapes(thr, kind)[3] == []


def test_odd_members_majority_rule():
    assert ifr.odd_members(["a", "a", "b"]) == [False, False, True]
    assert ifr.odd_members(["a", "b"]) == [True, True]
    assert ifr.odd_members(["a", "b", "c"]) == [True, True, True]
    assert ifr.odd_members(["a", "a", "b", "b"]) == [True, True, True, True]
    assert ifr.odd_members(["a", None, "a"]) == [False, False, False]
    assert ifr.odd_members(["a", None]) == [False, False]


def test_rotated_bars_sewn_the_same_way_relative_to_their_axis_agree():
    a = {"kind": "fill", "elong": 4.0, "orient": 0.0, "angle": 90.0}
    b = {"kind": "fill", "elong": 4.0, "orient": 60.0, "angle": 150.0}          # rotated copy
    mirror = {"kind": "fill", "elong": 4.0, "orient": 0.0, "angle": 90.0}
    c = {"kind": "fill", "elong": 4.0, "orient": 60.0, "angle": 60.0}           # rows along its axis
    assert not ifr.angle_disagree(a, b) and not ifr.angle_disagree(a, mirror)
    assert ifr.angle_disagree(a, c)
    r1 = {"kind": "fill", "elong": 1.0, "orient": 0.0, "angle": 10.0}
    r2 = {"kind": "fill", "elong": 1.0, "orient": 90.0, "angle": 170.0}         # round: absolute, mod 180
    assert not ifr.angle_disagree(r1, r2)
    assert ifr.angle_disagree(r1, {**r2, "angle": 100.0})
    assert ifr.angle_disagree(a, {**c, "kind": "satin"}) is None                # different kinds: not compared


def test_axial_mean():
    a, r = ifr.axial_mean(np.array([179.0, 1.0, 0.0]), np.ones(3))
    assert min(a, 180 - a) < 0.5 and r > 0.99
    _a, r = ifr.axial_mean(np.array([0.0, 90.0]), np.ones(2))
    assert r < 1e-9


def test_angles_from_segments_flag_the_cross_filled_sibling():
    thr, kind = _canvas()
    for cx in (60, 200, 340):
        _put(thr, kind, _disc(thr.shape, cx, 80, 30), 0)
    segs = {"mx": [], "my": [], "angle": [], "length": [], "cls": []}
    for cx, ang in ((60, 0.0), (200, 0.0), (340, 90.0)):
        for dy in (-10, 0, 10):
            segs["mx"].append(cx)
            segs["my"].append(80 + dy)
            segs["angle"].append(ang)
            segs["length"].append(4.0)
            segs["cls"].append(0)
    segs = {k: np.asarray(v, float) for k, v in segs.items()}
    _f, _c, _m, mem = ifr.read_shapes(thr, kind, segs)
    assert [g["odd"] for g in mem] == [[], [], ["angle"]]


def test_outlined_sibling_is_odd_on_rim():
    thr, kind = _canvas()
    for cx in (60, 200, 340):
        _put(thr, kind, _disc(thr.shape, cx, 80, 30), 0)
    ring = _disc(thr.shape, 340, 80, 31) & ~_disc(thr.shape, 340, 80, 27)
    kind[ring] = K["bean"]
    _f, _c, _m, mem = ifr.read_shapes(thr, kind)
    assert [g["rim"] for g in mem] == ["plain", "plain", "outlined"]
    assert "rim" in mem[2]["odd"] and not mem[0]["odd"]


def test_spread_points_grid_and_fallback():
    m = np.zeros((100, 100), bool)
    m[10:90, 10:90] = True
    pts = ifr.spread_points(m)
    assert len(pts) == 9 and all(x % 24 == 0 and y % 24 == 0 for x, y in pts)
    small = np.zeros((100, 100), bool)
    small[30:35, 30:35] = True
    assert ifr.spread_points(small) == [(32.0, 32.0)]


def test_stitch_hash_is_the_workers():
    d = {"stitches": [{"x": 1, "y": 2, "type": "stitch"}, {"x": 3, "y": 4, "type": "jump"}]}
    import hashlib
    assert ifr.stitches_sha(d) == hashlib.sha256(b'[[1, 2, "stitch"], [3, 4, "jump"]]').hexdigest()


def test_segments_match_the_render_frame_and_refuse_a_wrong_one():
    d = {"stitches": [{"x": 0, "y": 0, "type": "stitch"}, {"x": 100, "y": 0, "type": "stitch"},
                      {"x": 100, "y": 100, "type": "stitch"}],
         "runs": [{"i0": 0, "i1": 2, "kind": "fill"}], "colors": [{"r": 0, "g": 0, "b": 0}]}
    hw = (int((10 + 4) * 12), int((10 + 4) * 12))
    s = ifr.segments(d, hw, class_of_colour=[0])
    assert len(s["angle"]) == 2 and sorted(np.round(s["angle"])) == [0.0, 90.0]
    assert np.allclose(sorted(s["length"]), [10.0, 10.0])
    try:
        ifr.segments(d, (10, 10))
    except ValueError:
        pass
    else:
        raise AssertionError("a wrong frame must refuse")


def test_inconsistency_pins_are_the_committed_list():
    got = []
    for sit, px in (("defect-marks-2026-11-10", "L_"), ("defect-marks-2026-11-11", "C_")):
        marks = json.loads((DOCS / sit / "marks.json").read_text(encoding="utf-8"))
        got += h.select_inconsistency_pins(marks, px)
    committed = json.loads((DOCS / "inconsistency-fault-reader-2026-11-12" / "pins.json")
                           .read_text(encoding="utf-8"))["pins"]
    assert got == committed
    notes = {(p["item"], p["note_pin"]) for p in got}
    assert (len(got), len(notes), len({p["item"] for p in got})) == (39, 10, 7)


def test_inconsistency_rule_wording():
    r = h.inconsistency_reason
    assert r({"note": "#2-#3 feet are differnt colors, they should be the same"})      # colour counts here
    assert r({"note": "the M is correct, but the F is wrong"})
    assert r({"note": "This is the only letter that is thinly stitched"})
    assert r({"note": "This random stitch in the middle doesnt match the pros"}) is None
    assert r({"note": "The stitching is thicker than what the image shows"}) is None
    assert r({"note": "The stitching directions and angles are very inconsistent here."}) is None
    assert r({"note": ""}) is None


def test_harness_scores_an_inconsistency_dir(tmp_path):
    thr, kind = _canvas()
    for cx, c in ((60, 0), (200, 0), (340, 1)):
        _put(thr, kind, _disc(thr.shape, cx, 80, 30), c)
    flags, cands, cand, _mem = ifr.read_shapes(thr, kind)
    (tmp_path / "C_x.flags.json").write_text(json.dumps(
        {"flags": flags, "candidates": cands, "px_per_mm": ifr.PXMM, "pad_mm": ifr.PAD_MM}), encoding="utf-8")
    np.savez_compressed(tmp_path / "C_x.mask.npz", mask=thr >= 0, cand=cand)
    x, y = ifr.to_mm(340, 80)
    marks = {"items": {"C_x": {"pins": [{"x_mm": x, "y_mm": y, "what": "colour",
                                         "note": "this one doesn't match the others"}]}}}
    res = h.score_dir(marks, tmp_path, "C_", "inconsistency")
    b = res["items"]["C_x"]["by_radius"]["3.0"]
    assert b["hit"] == 1 and 0 < b["chance_pick"] < 1
    assert res["pooled_notes"]["3.0"]["chance_pick"]["notes"] == 1
