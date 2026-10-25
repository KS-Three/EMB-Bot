"""`cfg.preflight_glyph_metric` -- glyph legibility as preflight METRICS.

The per-glyph shape read of `tools/glyph_legibility.py` (#906), moved into
`digitizer_core/glyph_read.py`, run by preflight on every word of
text-tagged shapes. Pinned here:

  * it is OFF by default, and OFF writes no key (the report is the
    pre-change report byte for byte);
  * ON adds metrics and nothing else: findings, score and grade are the
    same report with or without it, and the plan is untouched (the three
    flat-lane goldens' md5s);
  * the read itself, on synthetic glyphs in the plan's own frame: an open
    counter reads open, a counter sewn shut is counted, an untagged letter on
    a tagged word's line is read, ink outside the word is not;
  * the tool and preflight run the same code.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import glyph_read  # noqa: E402
from digitizer_core import preflight as pf  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
GLYPH_KEYS = {"glyph_legibility_min", "glyph_legibility_mean", "counters_shut",
              "glyph_legibility_glyphs", "glyph_legibility_pull_mm", "glyph_legibility_words"}


# --- the flag and the report ----------------------------------------------------

def test_flag_is_off_by_default():
    assert PipelineConfig().preflight_glyph_metric is False


ART = TESTDATA / "photo" / "enthusiast_logo.png"     # two text clusters (test_legibility_check.py)


@lru_cache(maxsize=None)
def _enthusiast():
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    return digitize(ART, cfg)


def _report(flag: bool) -> dict:
    result, plan = _enthusiast()
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                         preflight_glyph_metric=flag)
    return pf.run_preflight(result, plan, cfg, image=ART)


def test_on_adds_metrics_and_changes_no_finding_score_or_grade():
    off, on = _report(False), _report(True)
    assert not GLYPH_KEYS & set(off["metrics"])            # OFF writes no key
    assert GLYPH_KEYS <= set(on["metrics"])
    assert on["metrics"]["glyph_legibility_glyphs"] > 0    # it read real lettering
    assert 0.0 <= on["metrics"]["glyph_legibility_min"] <= on["metrics"]["glyph_legibility_mean"] <= 1.0
    assert on["metrics"]["counters_shut"] >= 0
    assert json.dumps(on["findings"], sort_keys=True) == json.dumps(off["findings"], sort_keys=True)
    assert (on["score"], on["grade"]) == (off["score"], off["grade"])
    assert {k: v for k, v in on["metrics"].items() if k not in GLYPH_KEYS} == off["metrics"]
    json.dumps(on, allow_nan=False)                        # the service's serialiser


def test_on_without_the_artwork_reads_nothing_and_says_none():
    result, plan = _enthusiast()
    r = pf.run_preflight(result, plan, PipelineConfig(target_width_mm=80.0,
                                                      preflight_glyph_metric=True))
    assert all(r["metrics"][k] is None for k in GLYPH_KEYS)


# The three flat-lane goldens' stitch streams, as `test_small_print.py` pins
# them: the flag is read by preflight only, so the plan cannot move.
GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_flag_leaves_the_flat_goldens_plan_byte_identical(fixture):
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            preflight_glyph_metric=True))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert hashlib.md5(json.dumps(coords).encode()).hexdigest() == GOLDEN_MD5[fixture]


def test_the_tool_reads_with_the_same_code():
    from tools import glyph_legibility as gl
    assert gl.glyph_scores is glyph_read.glyph_scores
    assert gl.read_glyphs is glyph_read.read_glyphs
    assert gl.pull_erode is glyph_read.pull_erode


# --- the read, on synthetic glyphs ----------------------------------------------

PPM = 30.0                      # artwork px per mm
W_MM, H_MM = 24.0, 12.0         # the sheet; the plan's (0, 0) is its centre
O_SHEET, O_R, O_STROKE = (6.0, 6.0), 2.2, 0.7     # ring: counter radius 1.85 mm


def _plan(x_sheet: float, y_sheet: float) -> tuple[float, float]:
    return x_sheet - W_MM / 2.0, y_sheet - H_MM / 2.0


def _prep(strokes_sheet):
    """A stand-in for stage 1's `Prep`: a white sheet with black strokes,
    its art box the whole sheet, so mm = (px - centre) / PPM."""
    h, w = int(H_MM * PPM), int(W_MM * PPM)
    img = np.full((h, w), 255, np.uint8)
    for pl in strokes_sheet:
        pts = np.round(np.array([[x * PPM, y * PPM] for x, y in pl], np.float32)).astype(np.int32)
        cv2.polylines(img, [pts], False, 0, int(round(O_STROKE * PPM)), cv2.LINE_AA)
    rgb = np.repeat(img[..., None], 3, axis=2)
    return SimpleNamespace(rgb=rgb, bg_mask=img > 128, px_per_mm=PPM,
                           art_bbox=(0, 0, w, h), bg_from_alpha=False)


def _ring(cx, cy, r, n=96):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
            for k in range(n + 1)]


BAR = [(10.0, 3.8), (10.0, 8.2)]                  # an "I" beside the O, on its line
FAR_E = [[(15.0, 3.8), (15.0, 8.2)], [(15.0, 3.8), (18.0, 3.8)], [(15.0, 6.0), (17.5, 6.0)],
         [(15.0, 8.2), (18.0, 8.2)]]              # a letter well past the word's reach


def _design(paths_sheet, step=0.4) -> dict:
    """A Design (0.1 mm, y up) running along each sheet polyline, in the
    plan's frame."""
    recs = []
    for pl in paths_sheet:
        for i, ((x0, y0), (x1, y1)) in enumerate(zip(pl[:-1], pl[1:])):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
            for k in range(0 if i == 0 else 1, n + 1):
                px, py = _plan(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
                if i == 0 and k == 0:
                    recs.append({"x": px * 10, "y": -py * 10, "type": "jump"})
                recs.append({"x": px * 10, "y": -py * 10, "type": "stitch"})
    return {"stitches": recs, "colors": [{"r": 0, "g": 0, "b": 0}]}


def _o_region(**meta):
    cx, cy = _plan(*O_SHEET)
    ring = Point(cx, cy).buffer(O_R + O_STROKE / 2).difference(Point(cx, cy).buffer(O_R - O_STROKE / 2))
    return SimpleNamespace(shape_id="S_o", polygon=ring, meta=meta)


TAGGED = {"text_candidate": True, "text_cluster_id": "TC_test"}
OPEN = [_ring(*O_SHEET, r) for r in (1.95, 2.2, 2.45)] + [BAR] + FAR_E
SHUT = [_ring(*O_SHEET, r) for r in np.arange(0.2, 2.5, 0.25)] + [BAR] + FAR_E


def _read(paths, regions, cfg=None):
    p = _prep([_ring(*O_SHEET, O_R), BAR] + FAR_E)
    return glyph_read.read_design_words(p, regions, _design(paths), cfg)


def test_an_open_counter_reads_open_and_the_plan_frame_registers_without_a_search():
    read = _read(OPEN, [_o_region(**TAGGED)])
    assert [w["word"] for w in read] == ["TC_test"]
    rows = read[0]["rows"]
    # the O and the untagged bar on its line; the E past the word's reach is not read
    assert len(rows) == 2
    o = rows[0]
    assert o["src_counters_openable"] == 1 and o["counters"] == 1.0
    assert glyph_read.counters_shut(o) == 0
    assert min(g["strokes"] for g in rows) > 0.9
    assert max(g["offset_mm"] for g in rows) <= 0.1      # the frame is right; the shift did not rescue it
    m = glyph_read.design_metrics(read)
    assert m["counters_shut"] == 0 and m["glyph_legibility_glyphs"] == 2
    assert m["glyph_legibility_min"] > 0.9


def test_a_counter_sewn_shut_is_counted():
    read = _read(SHUT, [_o_region(**TAGGED)])
    o = read[0]["rows"][0]
    assert o["counters"] == 0.0 and glyph_read.counters_shut(o) == 1
    m = glyph_read.design_metrics(read)
    assert m["counters_shut"] == 1 and m["glyph_legibility_min"] == 0.0
    assert m["glyph_legibility_words"][0]["counters_shut"] == 1


def test_no_text_tagged_shape_reads_nothing_and_every_metric_is_none():
    assert _read(OPEN, [_o_region()]) == []
    assert all(v is None for v in glyph_read.design_metrics([]).values())


def test_lettering_words_reads_the_one_taggers_words():
    """Under `cfg.lettering_words` a word is a `word_id`, not a text
    cluster (`words.is_text`)."""
    cfg = PipelineConfig(lettering_words=True)
    assert _read(OPEN, [_o_region(**TAGGED)], cfg) == []
    read = _read(OPEN, [_o_region(word_id="W1", word_index=0)], cfg)
    assert [w["word"] for w in read] == ["W1"] and len(read[0]["rows"]) == 2


def test_counters_shut_reads_kept_back_from_the_ratio():
    row = {"src_counters_openable": 2, "sewn_counters_spurious": 1, "counters": round(1 / 3, 3)}
    assert glyph_read.counters_shut(row) == 1
    assert glyph_read.counters_shut({"src_counters_openable": 0, "sewn_counters_spurious": 1,
                                     "counters": 0.0}) == 0
