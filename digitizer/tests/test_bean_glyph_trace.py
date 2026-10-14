"""`tools/bean_glyph_trace.py`: the per-glyph thread trace, on a synthetic letter.

No digitizing: a hand-built "L" ink polygon, a bean-letter run laid by the real
`bean_letter` along its centreline, `apply_ties` folded in as stage 7 does, and
one run of a neighbour's that cuts across the L's bay. The trace must tell the
three apart by the construction step, and say the bay was filled by the stray
run and not by the bean legs. Under a minute, no tesseract.
"""
from __future__ import annotations

import math
import types

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import machine, stitches
from digitizer_core import stage6_beanletter as bl
from digitizer_core.config import PipelineConfig
from tools import bean_glyph_trace as bgt

# A "U" 1.0 mm wide, 1.6 mm tall, strokes 0.25 mm, slot 0.5 mm: a bay the closing fills.
L_INK = Polygon([(0.0, 0.0), (0.25, 0.0), (0.25, 1.35), (0.75, 1.35), (0.75, 0.0), (1.0, 0.0),
                 (1.0, 1.6), (0.0, 1.6)])
L_SPINE = [(0.125, 0.0), (0.125, 1.475), (0.875, 1.475), (0.875, 0.0)]
# A bar 0.3 mm to the right of the U, so the gap strip exists.
NB_INK = Polygon([(1.3, 0.0), (1.55, 0.0), (1.55, 1.6), (1.3, 1.6)])


def _cfg() -> PipelineConfig:
    return PipelineConfig(small_text_true_size=True)


def _run(stray: bool):
    cfg = _cfg()
    runs, report = bl.bean_letter([L_SPINE], "L", entry=None, trim_at_mm=3.0,
                                  stitch_mm=cfg.bean_letter_stitch_mm, serif_mm=cfg.bean_letter_serif_mm,
                                  min_arm_mm=cfg.bean_letter_min_arm_mm, corner_deg=cfg.bean_letter_corner_deg)
    assert not report["empty"]
    bean = {"L": [{"spines": [list(L_SPINE)], "kw": {}, "entry": None, "report": dict(report),
                   "runs": [{"points": [tuple(p) for p in r.points], "jump": r.jump, "trim": r.trim} for r in runs]}]}
    block_runs = list(runs)
    if stray:
        # a neighbour's run that sews straight up the U's slot
        block_runs.append(stitches.StitchRun(points=[(0.5, 0.5), (0.5, 1.2)], kind=stitches.RUN,
                                             jump=True, trim=False, shape_id="N"))
    stitches.apply_ties(block_runs)
    plan = stitches.StitchPlan(
        blocks=[stitches.StitchBlock(thread_index=0, thread_number="1", rgb=(20, 20, 20), runs=block_runs)],
        palette=[{}])
    regions = [types.SimpleNamespace(shape_id="L", polygon=L_INK, meta={"bean_letter_spines": [L_SPINE]}),
               types.SimpleNamespace(shape_id="N", polygon=NB_INK, meta={})]
    result = types.SimpleNamespace(regions=regions)
    return {"cell": "synthetic", "arm": "switch", "plan": plan, "result": result, "cfg": cfg,
            "bean": bean, "skel": {}}


def _trace(stray: bool):
    run = _run(stray)
    ev = bgt.build_events(run)
    glyphs = [L_INK, NB_INK]
    tr = bgt.trace_glyph(run, "est", 0, glyphs, ev, {0: ["L"], 1: ["N"]}, None)
    return run, ev, glyphs, tr


def test_tie_counts_finds_a_lock_at_each_end_only():
    a, b = (0.0, 0.0), (0.8, 0.0)
    run = stitches.StitchRun(points=[(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)], kind=stitches.RUN)
    stitches.apply_ties([run])
    assert bgt._tie_counts(run.points) == (4, 4)
    assert bgt._tie_counts([a, b, (1.6, 0.0), (2.4, 0.0), (3.2, 0.0)]) == (0, 0)


def test_events_label_every_needle_point_by_its_step():
    _run_, ev, _g, _tr = _trace(stray=False)
    labels = {e["label"] for e in ev["points"]}
    assert bgt.L_TIE in labels and bgt.L_BEAN in labels
    # the U's spine has two 90 degree corners and `bean_letter_corner_deg` is 50: a corner station exists
    assert bgt.L_CORNER in labels
    assert not any(e["label"] == bgt.L_OTHER for e in ev["points"])


def test_a_clean_bean_letter_leaves_no_needle_point_off_the_ink():
    _run_, _ev, _g, tr = _trace(stray=False)
    assert tr["tier"] == "bean letter"
    assert tr["points_outside"] == []
    assert tr["segments_outside"] == []
    assert tr["lock_stitches"], "the run's two folded-in locks were not counted"
    assert all(leg <= machine.TIE_STITCH_MM + 1e-9 for leg in tr["lock_leg_mm"])
    nb = tr["needle_bbox_mm"]
    assert nb[0] == pytest.approx(0.125, abs=1e-6) and nb[2] == pytest.approx(0.875, abs=1e-6)
    assert nb[3] == pytest.approx(1.475, abs=1e-6)


def test_the_spine_table_matches_the_tiers_own_stroke_count():
    run, _ev, _g, tr = _trace(stray=False)
    table = bgt.spine_table(run["bean"]["L"][0]["spines"], run["cfg"])
    assert bgt.check_spines(table, run["bean"]["L"])
    assert [t["sews"] for t in table] == [True]
    assert table[0]["corners"] == 2 and table[0]["free_ends"] == 2


def test_a_strangers_run_across_the_bay_is_named_and_fills_it():
    _run_, _ev, _g, tr = _trace(stray=True)
    assert tr["bays"], "the L has a bay: the closing of its ink minus its ink"
    bay = max(tr["bays"], key=lambda b: b["mm2"])
    assert bay["status"] == "FILLED" or bay["covered_mm2"] > 0
    by_step = bay["covered_by_step_mm2"]
    assert any(bgt.L_FOREIGN in k for k in by_step), by_step
    # ... and the foreign run's points are off the L's ink, attributed to it, not to the bean legs
    off = tr["points_outside"]
    assert off and all(not r["owner"] for r in off)
    assert all(r["d_mm"] > 0.1 for r in off)
    assert {r["shape"] for r in off} == {"N"}


def test_the_gap_strip_is_measured_between_the_two_letters():
    _run_, _ev, _g, tr = _trace(stray=False)
    (gap,) = tr["gaps"]
    assert gap["side"] == "right" and gap["src_gap_mm"] == pytest.approx(0.3, abs=1e-9)
    assert gap["gap_mm2"] > 0


def test_pick_glyph_by_character_nth_match_and_index():
    glyphs = [object()] * 4
    assert bgt.pick_glyph("1", glyphs, "1895") == 0
    assert bgt.pick_glyph("5", glyphs, "1895") == 3
    assert bgt.pick_glyph("#2", glyphs, "1895") == 2
    with pytest.raises(SystemExit):
        bgt.pick_glyph("E", glyphs, "1895")
    # THE has three letters; a count that disagrees falls back to indices
    assert bgt.labels_for("the", 3) == ["T", "H", "E"]
    assert bgt.labels_for("the", 5) == [f"#{i}" for i in range(5)]


def test_dist_to_is_zero_in_the_ink_and_positive_in_a_counter():
    ring = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)], [[(1, 1), (2, 1), (2, 2), (1, 2)]])
    d = bgt.dist_to(ring, [(0.5, 0.5), (1.5, 1.5), (4.0, 0.5)])
    assert d[0] == 0.0 and d[1] == pytest.approx(0.5) and d[2] == pytest.approx(1.0)


def test_render_writes_a_three_panel_png(tmp_path):
    cv2 = pytest.importorskip("cv2")
    run, ev, glyphs, tr = _trace(stray=True)
    path = tmp_path / "L.png"
    bgt.render_glyph(run, glyphs, tr, ev, path, ppm=60.0)
    img = cv2.imread(str(path))
    assert img is not None and img.shape[1] % 3 == 0 and img.shape[0] > 50
    assert np.any(img.reshape(-1, 3) != 255)


def test_main_lists_cells_in_help(capsys):
    with pytest.raises(SystemExit) as e:
        bgt.main(["--help"])
    assert e.value.code == 0
    assert "hat81" in capsys.readouterr().out
