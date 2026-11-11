"""`tools.fault_reader_harness`: pin selection, hits, chance, pooling. No engine.

The two properties that matter: the committed pin list is exactly what the
written rule selects from the committed marks (so the rule can be audited and
cannot drift), and the chance figure is the right number for a case whose
answer is known in closed form.
"""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from tools import edge_fault_reader as efr
from tools import fault_reader_harness as h

DOCS = Path(__file__).resolve().parents[2] / "docs" / "defect-marks-2026-11-10"


def _pin(note="", what=None, x=0.0, y=0.0):
    return {"x_mm": x, "y_mm": y, "what": what, "severity": "noticeable", "note": note}


# --------------------------------------------------------------- selection ----

@pytest.mark.parametrize("note,what,expect", [
    ("Its jagged and should be smooth", "lumpy_curve", "edge kind"),
    ("The circle edges should be smooth", None, "edge word"),          # rule 1, no kind
    ("This doesn;t look clean here", "wavy", "edge kind"),             # rule 2: the kind carries it
    ("Black showing through", "gap", None),
    ("The stitching isn't smooth, it has no flow here", "mushed", None),  # rule 3
    ("The R should be smooth and it has a bump here.", "lumpy_curve", "edge kind"),
    ("Gap in the line", "wavy", None),                                 # edge kind, other fault named
    ("The end of this rope doesn't finish cleanly", "direction", None),
])
def test_edge_reason(note, what, expect):
    assert h.edge_reason(_pin(note, what)) == expect


def test_bare_pins_inherit_only_from_a_relevant_same_as_note():
    marks = {"items": {
        "L_a": {"pins": [_pin("Jagged edges (marks 1-4 are te same issue)", "jagged"), _pin(), _pin()]},
        "L_b": {"pins": [_pin("Bean makes it busy (same for 1-20)", "stitch_type"), _pin()]},
        "P_c": {"pins": [_pin("jagged", "jagged")]}}}
    got = [(p["item"], p["pin"], p["rule"]) for p in h.select_edge_pins(marks)]
    assert got == [("L_a", 1, "edge kind"), ("L_a", 2, "same as pin 1"), ("L_a", 3, "same as pin 1")]


def test_committed_pin_list_is_what_the_rule_selects():
    marks = json.loads((DOCS / "marks.json").read_text(encoding="utf-8"))
    committed = json.loads((DOCS / "edge-reader-pins.json").read_text(encoding="utf-8"))["pins"]
    assert h.select_edge_pins(marks) == committed
    assert len(committed) == 20 and len({p["item"] for p in committed}) == 7


# ----------------------------------------------------------------- scoring ----

def test_hits_and_nearest():
    flags = [{"x_mm": 0, "y_mm": 0, "strength": 0.3}, {"x_mm": 10, "y_mm": 0, "strength": 0.2}]
    pins = [_pin(x=2.9), _pin(x=6.0), _pin(x=10, y=3.0)]
    assert h.hits(pins, flags, 3.0).tolist() == [True, False, True]
    assert h.nearest_mm(pins, []).tolist() == [math.inf] * 3
    assert h.local_strength(pins, flags, 3.0).tolist() == [0.3, 0.0, 0.2]


def test_mask_points_land_in_the_pins_frame():
    m = np.zeros((48, 48), bool)
    m[24:36, 12:24] = True                        # pixels 12-23 x, 24-35 y at 12 px/mm
    pts = h.mask_points_mm(m, 500, np.random.default_rng(0), 12.0, 2.0)
    assert pts[:, 0].min() >= 12 / 12 - 2 and pts[:, 0].max() <= 24 / 12 - 2
    assert pts[:, 1].min() >= 24 / 12 - 2 and pts[:, 1].max() <= 36 / 12 - 2


def test_chance_rate_matches_closed_form_and_is_seeded():
    # 40 x 40 mm all thread, one flag in the middle, r = 3: chance = pi r^2 / area
    m = np.ones((480, 480), bool)
    flags = [{"x_mm": 18.0, "y_mm": 18.0, "strength": 1.0}]
    c = h.chance_rate(flags, m, 5, 12.0, 2.0, 3.0, draws=4000)
    assert c == pytest.approx(math.pi * 9 / 1600, abs=0.002)
    assert c == h.chance_rate(flags, m, 5, 12.0, 2.0, 3.0, draws=4000)


def test_edge_band_is_the_rim():
    m = np.zeros((100, 100), bool)
    m[10:90, 10:90] = True
    b = h.edge_band(m, 12.0, 1.0)
    assert b[10, 50] and b[21, 50] and not b[50, 50] and not b[5, 5]


def test_strength_auc():
    assert h.strength_auc([1.0, 1.0], [0.0, 0.0, 0.0]) == 1.0
    assert h.strength_auc([0.0], [0.0, 0.0]) == 0.5
    assert h.strength_auc([0.0], [1.0]) == 0.0


def _row(pins, hit, chance):
    return {"pins": pins, "by_radius": {"3.0": {"hit": hit, "chance_area": chance, "chance_edge": chance}}}


def test_pool_is_pin_weighted_and_clustered_by_item():
    rows = {"a": _row(4, 4, 0.25), "b": _row(1, 0, 0.5), "z": _row(0, 0, float("nan"))}
    p = h.pool(rows, 3.0, boots=500)
    assert p["items"] == 2 and p["pins"] == 5
    assert p["hit_rate"] == 0.8 and p["chance"] == pytest.approx(1.5 / 5)
    assert p["diff"] == pytest.approx(0.5)
    lo, hi = p["ci95"]
    # two items: the bootstrap can only ever see {a,a}, {a,b}, {b,b}
    assert lo == pytest.approx(-0.5) and hi == pytest.approx(0.75)


def test_item_score_end_to_end_perfect_reader_beats_chance():
    m = np.zeros((600, 600), bool)
    m[60:540, 60:540] = True
    pins = [_pin(x=10, y=10), _pin(x=30, y=30)]
    flags = [{"x_mm": 10.5, "y_mm": 10, "strength": 0.4}, {"x_mm": 30, "y_mm": 30.5, "strength": 0.4}]
    row = h.item_score(pins, flags, m, 12.0, 2.0, draws=500)
    b = row["by_radius"]["3.0"]
    assert b["hit"] == 2 and b["chance_area"] < 0.15
    assert row["auc_area"] > 0.9
    assert h.unpinned_flags(flags + [{"x_mm": 20, "y_mm": 20, "strength": 0.2}], pins) == \
        [{"x_mm": 20, "y_mm": 20, "strength": 0.2}]


# ----------------------------------------------------------------- reader ----

def test_plan_to_render_matches_stitchviz_frame():
    """The reader's mapping lands on the pixel `render_design` draws, read
    back the way `defect_marks.mark_mm` reads a pin."""
    from digitizer_core.adapter import _u
    from digitizer_core.stitchviz import _frame
    pts_mm = [(3.0, 4.0), (40.0, 22.5), (12.3, 30.7)]      # on the 0.1 mm design-unit grid
    stitches = [{"x": x, "y": y, "type": "stitch"} for x, y in (_u(*p) for p in pts_mm)]
    (_hw, to_px) = _frame(stitches, 12.0, 2.0)
    origin = efr.design_origin(stitches)
    for p, s in zip(pts_mm, stitches):
        px, py = to_px(s)
        x, y = efr.plan_to_render_mm(*p, origin)
        assert x == pytest.approx(px / 12.0 - 2.0, abs=1 / 12) and y == pytest.approx(py / 12.0 - 2.0, abs=1 / 12)


def test_cluster_keeps_strongest_and_merges_within_radius():
    pts = [{"x_mm": 0.0, "y_mm": 0.0, "dev_mm": 0.2, "tier": "satin"},
           {"x_mm": 1.0, "y_mm": 0.0, "dev_mm": -0.5, "tier": "fill"},
           {"x_mm": 5.0, "y_mm": 0.0, "dev_mm": 0.16, "tier": "satin"}]
    spots = efr.cluster(pts, 2.0)
    assert [(s["x_mm"], s["strength"], s["n"]) for s in spots] == [(1.0, 0.5, 2), (5.0, 0.16, 1)]
    assert spots[0]["tiers"] == {"fill": 1, "satin": 1}


def test_over_mm_is_the_instruments_own_line():
    from digitizer_core import edge_wobble
    assert efr.OVER_MM == edge_wobble.OVER_MM
