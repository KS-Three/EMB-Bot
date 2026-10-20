"""MASTER_SCOPE defect 28, separated: one test per case of the F wall.

`THREAD_MATCH_POOR:block` holds the corpus's F grades, and it is several
problems wearing one code. Re-measured 2026-10-08 on main (left_chest, 80 mm):
12 blocking findings over six F fixtures. Each case below is a different
problem with a different owner, and `tools/spool_remedy.py` is the instrument
that tells them apart, so the instrument must judge exactly as the check does.

* RAW YARDSTICK — 10 of 12: nothing loaded is meaningfully closer, so the
  block clears under excess. Kent RULED 2026-09-10 the gradient lane stays on
  raw (a logo's cone can be bought). Not a bug.
* SURVIVES EXCESS — 1 of 12 (`summit_badge`'s `0111` shade band, raw 21.5,
  excess 16.9, `0134` loaded). A real reassignment the check already names.
* THE TWO FLOORS 4x APART — re-snap 200 px vs preflight 50 px. Closed by
  `cfg.revalidate_small_shapes` (ON since 2026-09-10); pinned here too.
* THE INSTRUMENT'S OWN BUG, fixed with this file: `spool_remedy` took each
  thread's top over EVERY row, ignoring the 5.0 mm² patch floor the check has
  applied since 2026-09-10, so a sub-floor shard read as a block the
  scorecard never carries.

(The clamp floor — score `max(0, ...)` — is a product call, Kent's, and is
not tested here.)
"""
from types import SimpleNamespace

import numpy as np

from digitizer_core import preflight as pf
from digitizer_core import stage4_vectorize as s4
from digitizer_core.config import PipelineConfig
from digitizer_core.threads import chart_for
from tools.spool_remedy import thread_blocks

FLOOR = pf._THREAD_MATCH_MIN_PATCH_MM2


def _row(de, exc, mm2):
    return {"delta_e": de, "_exc": exc, "footprint_mm2": mm2}


def test_raw_yardstick_case_blocks_raw_and_clears_on_excess():
    rb, eb, _, _ = thread_blocks([_row(12.2, 0.0, 2232.4)])
    assert rb and not eb


def test_survives_excess_case_blocks_on_both_yardsticks():
    rb, eb, _, _ = thread_blocks([_row(21.5, 16.9, 166.3)])
    assert rb and eb


def test_sub_floor_shard_cannot_block_in_the_instrument():
    # The bug: a 0.58 mm² shard at 63.6 dE00 beside a judged 6.0 warn.
    rows = [_row(63.6, 58.6, 0.58), _row(6.0, 0.0, 12.0)]
    rb, eb, raw_top, exc_top = thread_blocks(rows)
    assert not rb and not eb
    assert raw_top["footprint_mm2"] >= FLOOR and exc_top["footprint_mm2"] >= FLOOR


def test_all_sub_floor_thread_is_not_judged():
    assert thread_blocks([_row(40.0, 30.0, FLOOR - 0.01)]) == (
        False, False, None, None)


def test_instrument_agrees_with_the_shipped_check(monkeypatch):
    """Same rows into `_thread_match_findings` and `thread_blocks`: same
    verdict. A sub-floor 0111 shard on a thread whose judged patch is fine,
    and a judged 0111 patch on a second thread that blocks."""
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    chart = chart_for(cfg)
    # The chart's lightest and darkest spools: far apart on any chart.
    a, b = int(np.argmax(chart.lab[:, 0])), int(np.argmin(chart.lab[:, 0]))
    far = chart.lab[b].reshape(1, 3)        # pixels the colour of spool b
    near = chart.lab[a].reshape(1, 3)

    def de(t, lab):
        from skimage.color import deltaE_ciede2000
        return float(deltaE_ciede2000(lab, chart.lab[t].reshape(1, 3))[0])

    raw_far = de(a, far)
    assert raw_far > pf.DELTA_E_CLEARLY_DIFFERENT, "fixture spools too close"
    rows = [
        {"shape_id": "shard", "thread_index": a, "delta_e": raw_far,
         "footprint_mm2": 0.58, "_lab_px": far, "artwork_rgb": [0, 0, 0]},
        {"shape_id": "body", "thread_index": a, "delta_e": 0.0,
         "footprint_mm2": 40.0, "_lab_px": near, "artwork_rgb": [0, 0, 0]},
        {"shape_id": "other", "thread_index": b, "delta_e": de(b, near),
         "footprint_mm2": 40.0, "_lab_px": near, "artwork_rgb": [0, 0, 0]},
    ]
    monkeypatch.setattr(pf, "_region_color_errors", lambda *a_, **k: rows)
    monkeypatch.setattr(pf, "_is_photo_class", lambda *a_, **k: False)
    plan = SimpleNamespace(blocks=[])
    result = SimpleNamespace(regions=[])
    findings, _ = pf._thread_match_findings(None, result, plan, cfg)
    shipped_blocks = {f["extra"]["thread_number"] for f in findings
                      if f["severity"] == "block"}

    for r in rows:
        r["_exc"] = 0.0
    tool_blocks = set()
    for t in (a, b):
        rb, _, _, _ = thread_blocks([r for r in rows if r["thread_index"] == t])
        if rb:
            tool_blocks.add(chart[t].number)
    assert tool_blocks == shipped_blocks
    assert chart[a].number not in tool_blocks, "sub-floor shard judged"
    assert chart[b].number in tool_blocks


def test_the_two_floors_are_one_floor_when_the_flag_is_on():
    """The 4x gap (200 vs 50 px) is closed by `revalidate_small_shapes`,
    which is ON by default."""
    assert s4.THREAD_REVALIDATE_MIN_PX_SMALL == pf._MIN_COLOR_PIXELS
    assert PipelineConfig().revalidate_small_shapes is True
