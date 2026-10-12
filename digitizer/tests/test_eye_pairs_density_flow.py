"""tools.eye_pairs.density_flow: each candidate on a synthetic design whose
density, direction and stitch lengths are known lands within 2%, and the
pooling refuses a label it does not know (the #842 vocabulary guard)."""
from __future__ import annotations

import json
import math

import pytest

from tools.eye_pairs import density_flow as df
from tools.eye_pairs import density_flow_build as dfb
from tools.eye_pairs import pooled

R = df.THREAD_MM / 2.0


def _design(points_by_run, kinds=None, shapes=None, extra=None):
    """points_by_run: list of [(x_mm, y_mm), ...]; each run is sewn needle-down,
    runs joined by a jump. -> a Design dict in 0.1 mm units with runs."""
    st, runs = [], []
    for k, pts in enumerate(points_by_run):
        if st:
            st.append({"x": pts[0][0] * 10, "y": pts[0][1] * 10, "type": "jump"})
        i0 = len(st)
        st += [{"x": x * 10, "y": y * 10, "type": "stitch"} for x, y in pts]
        runs.append({"i0": i0, "i1": len(st) - 1, "kind": (kinds or ["fill"] * 99)[k],
                     "shape": (shapes or [f"S{k}" for k in range(99)])[k], "role": "", "block": 0})
    st += extra or []
    st.append({"x": st[-1]["x"], "y": st[-1]["y"], "type": "end"})
    return {"stitches": st, "runs": runs,
            "stitchCount": sum(1 for s in st if s["type"] == "stitch")}


def _rows(w, h, pitch, step=3.0, angle_deg=0.0):
    """Boustrophedon fill of a w x h rectangle, rows `pitch` apart, needle
    every `step` mm along a row; rotated by `angle_deg`."""
    n = int(round(h / pitch)) + 1
    xs = [min(i * step, w) for i in range(int(math.ceil(w / step)) + 1)]
    pts = []
    for r in range(n):
        y = r * pitch
        row = xs if r % 2 == 0 else xs[::-1]
        pts += [(x, y) for x in row]
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def _rect_footprint(w, h, r=R):
    return (w + 2 * r) * (h + 2 * r) - (4 - math.pi) * r * r


# ------------------------------------------------------------- density ---

@pytest.mark.parametrize("pitch", [0.15, 0.30])
def test_density_of_a_known_fill(pitch):
    w = h = 20.0
    d = _design([_rows(w, h, pitch)])
    n = int(round(h / pitch)) + 1
    thread = n * w + (n - 1) * pitch
    want = thread / _rect_footprint(w, h)
    got = df.measure(d, support=False)["thread_density"]
    assert got == pytest.approx(want, rel=0.02)


def test_density_halves_when_the_pitch_doubles_and_is_rotation_free():
    a = df.measure(_design([_rows(20, 20, 0.15)]), support=False)["thread_density"]
    b = df.measure(_design([_rows(20, 20, 0.30)]), support=False)["thread_density"]
    c = df.measure(_design([_rows(20, 20, 0.15, angle_deg=37)]), support=False)["thread_density"]
    assert b / a == pytest.approx(0.5, rel=0.02)
    assert c == pytest.approx(a, rel=0.02)


def test_sparse_thread_reads_one_over_the_thread_width():
    """Rows far apart: footprint is each row's own 0.4 mm strip."""
    d = _design([[(0, 0), (50, 0)], [(0, 5), (50, 5)], [(0, 10), (50, 10)]])
    want = 150.0 / (3 * (50 * 2 * R + math.pi * R * R))
    assert df.measure(d, support=False)["thread_density"] == pytest.approx(want, rel=0.02)


def test_changed_shapes_scope_density_and_whole_design_stays_whole():
    dense, sparse = _rows(10, 10, 0.15), _rows(10, 10, 0.60)
    sparse = [(x + 30, y) for x, y in sparse]
    d = _design([dense, sparse], shapes=["A", "B"])
    whole = df.measure(d, support=False)
    only_b = df.measure(d, {"B"}, support=False)
    assert only_b["thread_density"] < whole["thread_density"] < df.measure(d, {"A"}, support=False)["thread_density"]
    assert only_b["thread_density_whole"] == pytest.approx(whole["thread_density"], rel=1e-9)


# ----------------------------------------------------------- direction ---

def _strokes(angles_deg, length=3.0, per=20):
    pts = [(0.0, 0.0)]
    for a in angles_deg:
        dx, dy = length * math.cos(math.radians(a)), length * math.sin(math.radians(a))
        for _ in range(per):
            x, y = pts[-1]
            pts.append((x + dx, y + dy))
            dx, dy = -dx, -dy          # back and forth along one axis, as a satin does
    return pts


@pytest.mark.parametrize("angles,want", [([30], 0.0), ([0, 90], 1.0), ([0, 45], 1 - math.sqrt(0.5))])
def test_flow_circular_variance(angles, want):
    d = _design([_strokes(angles)])
    assert df.measure(d, support=False)["flow_circvar"] == pytest.approx(want, abs=0.02 * max(want, 1.0))


def test_turns_per_100mm_counts_one_turn():
    d = _design([_strokes([0, 90], length=3.0, per=20)])
    # 40 stitches of 3 mm, one axial change > 30 deg
    assert df.measure(d, support=False)["turns_per_100mm"] == pytest.approx(100.0 / 120.0, rel=0.02)


def test_flow_ignores_runs_and_underlay_kinds():
    d = _design([_strokes([0]), _strokes([90])], kinds=["fill", "underlay"], shapes=["A", "A"])
    assert df.measure(d, support=False)["flow_circvar"] == pytest.approx(0.0, abs=1e-9)


# ------------------------------------------------------ stitch lengths ---

def test_stitch_length_distribution():
    pts, x = [(0.0, 0.0)], 0.0
    for ln in [0.5] * 10 + [2.0] * 20 + [5.0] * 10:
        x += ln
        pts.append((x, 0.0))
    m = df.measure(_design([pts]), support=False)
    assert m["stitch_median_mm"] == pytest.approx(2.0, rel=0.02)
    assert m["short_share"] == pytest.approx(0.25, rel=0.02)
    assert m["long_share"] == pytest.approx(0.25, rel=0.02)


# -------------------------------------------------------------- travel ---

def test_jumps_trims_and_longest_jump():
    a = [(0, 0), (1, 0), (2, 0)]
    b = [(32, 0), (33, 0)]          # a 30 mm move
    c = [(33, 10), (34, 10)]        # a 10 mm move, trimmed
    d = _design([a, b])
    st = d["stitches"][:-1]
    st += [{"x": 330, "y": 0, "type": "trim"}, {"x": 330, "y": 100, "type": "jump"}]
    st += [{"x": x * 10, "y": y * 10, "type": "stitch"} for x, y in c]
    st.append({"x": 340, "y": 100, "type": "end"})
    d = {"stitches": st, "runs": d["runs"], "stitchCount": 7}
    m = df.measure(d, support=False)
    assert m["jumps_per_1000"] == pytest.approx(2 * 1000 / 7, rel=0.02)
    assert m["trims_per_1000"] == pytest.approx(1000 / 7, rel=0.02)
    assert m["longest_jump_mm"] == pytest.approx(30.0, rel=0.02)


def test_runs_per_shape():
    d = _design([_strokes([0]), [(0, 0), (5, 0)], _strokes([0]), _strokes([0])],
                kinds=["fill", "travel", "satin", "run"], shapes=["A", "A", "B", "B"])
    assert df.measure(d, support=False)["runs_per_shape"] == pytest.approx(1.5, rel=1e-9)


def test_a_design_without_runs_is_one_group():
    d = _design([_strokes([0, 90])])
    d.pop("runs")
    m = df.measure(d, support=False)
    assert m["flow_circvar"] == pytest.approx(1.0, abs=0.02)
    assert m["runs_per_shape"] is None


# ------------------------------------------------------------- pooling ---

def _pair(i, label, before, after, fixture="fx"):
    return {"id": f"s:a:{fixture}{i}", "arm": "a", "fixture": f"{fixture}{i % 3}", "label": label,
            "judged": "2026-10-12", "before": before, "after": after}


def test_pooling_refuses_an_unknown_label():
    bad = {"schema": 1, "sittings": {"s": {"pairs": [_pair(0, "maybe", {}, {})]}}}
    with pytest.raises(pooled.LabelVocabularyError):
        df.full_report(bad)


def test_denser_pick_agrees_through_pooled_kappa():
    """Kent picks the denser side every time -> sides-only kappa +1 for the
    'higher is better' density candidate and -1 for a 'lower is better' one."""
    pairs = []
    for i in range(6):
        if i % 2:
            pairs.append(_pair(i, "after", {"thread_density": 5.0}, {"thread_density": 7.0}))
        else:
            pairs.append(_pair(i, "before", {"thread_density": 7.0}, {"thread_density": 5.0}))
    rows = pooled.select(pooled.pooled_pairs({"schema": 1, "sittings": {"s": {"pairs": pairs}}}))
    dirs = df.directions()
    assert pooled.agreement(rows, "thread_density", directions=dirs)["kappa_decided"] == pytest.approx(1.0)
    flipped = {**dirs, "thread_density": ("lower", "")}
    assert pooled.agreement(rows, "thread_density", directions=flipped)["kappa_decided"] == pytest.approx(-1.0)
    # the default table is untouched: pooled's own instruments still score as before
    assert "thread_density" not in pooled.INSTRUMENTS


def test_both_bad_level_split():
    pairs = [_pair(i, "both_bad" if i < 4 else "same", {"unsewn_frac": v}, {"unsewn_frac": v})
             for i, v in enumerate([0.9, 0.8, 0.7, 0.6, 0.1, 0.2, 0.3, 0.05])]
    rows = pooled.select(pooled.pooled_pairs({"schema": 1, "sittings": {"s": {"pairs": pairs}}}))
    r = df.both_bad_agreement(rows, "unsewn_frac", "lower")
    assert r["n"] == 8 and r["n_both_bad"] == 4 and r["kappa"] == pytest.approx(1.0)


# ------------------------------------------------------------- builder ---

def test_builder_refuses_a_design_whose_stitch_count_is_not_the_judged_page(tmp_path):
    (tmp_path / "designs").mkdir()
    base = _design([_rows(5, 5, 0.3)])
    arm = _design([_rows(5, 5, 0.15)])
    (tmp_path / "designs" / "fx__base.json").write_text(json.dumps(base))
    (tmp_path / "designs" / "fx__a.json").write_text(json.dumps(arm))
    p = {"id": "s:a:fx", "arm": "a", "fixture": "fx", "label": "after",
         "before": {"stitches": base["stitchCount"]}, "after": {"stitches": arm["stitchCount"] + 1}}
    q = {"before": {}, "after": {}}
    dfb._measure_pair(q, p, tmp_path, {}, dfb.Cache(None))
    assert "not the page he judged" in q["unscored_why"] and not q["before"]
    p["after"]["stitches"] = arm["stitchCount"]
    q = {"before": {}, "after": {}}
    dfb._measure_pair(q, p, tmp_path, {}, dfb.Cache(None))
    assert "unscored_why" not in q
    assert q["after"]["thread_density"] > q["before"]["thread_density"]
