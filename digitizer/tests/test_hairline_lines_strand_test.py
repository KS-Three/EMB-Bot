"""The line route's strand test (`cfg.hairline_lines_strand_test`, default
OFF, 2026-10-13; `stage6_hairline_lines.stack_share`).

A thin bar passes the ridge test like a strand: on owl_kent 31 of the line
route's 75 strands were the breast barring (#882). With the flag on, a ridge
that sits in a stack of parallel lines of its own polarity is a bar and is
not sewn; and the route's widths follow the colour block's thread weight.
Every number is a property of the file, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import collections
import json

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize, run_stages
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_hairline_lines import extract_strands, strand_blocks
from tests.test_hairline_lines import _md5
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5

PX_PER_MM = 8.0
SIZE_PX = 320
ON = dict(hairline=True, hairline_from_lines=True)


def _sp(img) -> SourcePixels:
    h, w = img.shape[:2]
    return SourcePixels(rgb=img, px_per_mm=PX_PER_MM, origin_px=(w / 2.0, h / 2.0))


def _ground():
    img = np.full((SIZE_PX, SIZE_PX, 3), (200, 190, 180), np.uint8)
    return img


def _strands(img):
    """Three lone dark strands, far (> 6 mm) from each other and from
    anything else, none parallel to a neighbour: what the test keeps."""
    t = np.linspace(0.0, 1.0, 40)
    for pts in (np.column_stack([200 + 8 * np.sin(3 * t), 30 + 100 * t]),
                np.column_stack([285 - 10 * t ** 2, 40 + 90 * t]),
                np.column_stack([60 + 100 * t, 230 + 20 * np.sin(2.5 * t)])):
        cv2.polylines(img, [np.round(pts).astype(np.int32)], False, (40, 35, 30), 2,
                      cv2.LINE_AA)
    return img


def _bars(img):
    """Six evenly spaced (2.5 mm) parallel thin dark bars: a barred breast."""
    for y in range(40, 141, 20):
        cv2.line(img, (20, y), (150, y + 6), (40, 35, 30), 2, cv2.LINE_AA)
    return img


def _sewable(strands):
    return [s for s in strands if s["length_mm"] >= machine.RUN_MIN_LOOP_MM]


# --- OFF is byte-identical ---------------------------------------------------

def test_the_flag_defaults_off():
    assert PipelineConfig().hairline_lines_strand_test is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_flag_alone_is_byte_identical_to_the_flat_golden(fixture):
    """#848's pins: the flag without the line route is inert."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _r, plan = digitize(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                       hairline_lines_strand_test=True))
    assert _md5(plan) == GOLDEN_MD5[fixture]


def test_off_the_census_and_strands_are_unchanged():
    """Off, no strand carries a `stack` share and the census has no
    `refused_bar`: the route reads exactly as #882 shipped it."""
    sp = _sp(_bars(_strands(_ground())))
    strands, census = extract_strands(sp, PipelineConfig(**ON))
    assert set(census) == {"found", "refused_no_ridge"}
    assert all("stack" not in s for s in strands)


# --- the strand test ---------------------------------------------------------

def test_a_stack_of_bars_is_refused_and_lone_strands_are_kept():
    sp = _sp(_bars(_strands(_ground())))
    off, _c = extract_strands(sp, PipelineConfig(**ON))
    on, census = extract_strands(sp, PipelineConfig(**ON, hairline_lines_strand_test=True))

    def bars(strands):
        return [s for s in _sewable(strands) if sp.to_px(*s["pts"][0])[1] < 160
                and sp.to_px(*s["pts"][0])[0] < 170]

    def lone(strands):
        return [s for s in _sewable(strands) if s not in bars(strands)]

    # Off, every bar is sewn as a strand; on, none is.
    assert len(bars(off)) >= 5
    assert bars(on) == []
    assert census["refused_bar"]["dark"] >= 5
    # The lone strands are untouched by the test.
    assert len(lone(off)) == 3
    assert [s["pts"] for s in lone(on)] == [s["pts"] for s in lone(off)]
    assert all(s["stack"] < 0.4 for s in on)


def test_strands_only_change_nothing():
    """No stack in the picture: the test refuses nothing and the sewn
    blocks are byte-identical to the flag off."""
    sp = _sp(_strands(_ground()))
    off_blocks, off_rep = strand_blocks(sp, PipelineConfig(**ON), entry=None,
                                        trim_at_mm=machine.TRIM_AT_MM, allowed_threads=[0])
    on_blocks, on_rep = strand_blocks(sp, PipelineConfig(**ON, hairline_lines_strand_test=True),
                                      entry=None, trim_at_mm=machine.TRIM_AT_MM,
                                      allowed_threads=[0], block_wt={})
    assert on_rep["refused_bar"] == {"dark": 0, "light": 0}
    assert off_rep["strands"] == on_rep["strands"] == 3

    def pts(blocks):
        return [(t, [r.points for r in runs]) for t, runs in blocks]
    assert pts(on_blocks) == pts(off_blocks)


# --- the colour block's thread weight ---------------------------------------

def test_the_block_weight_is_read_only_with_the_flag():
    """`block_wt` names 60 wt for the block's thread: on, the strands are
    read and stitched at 60 wt; at 40 wt (the design's) the blocks are
    byte-identical to no override; off, the override is ignored."""
    sp = _sp(_strands(_ground()))
    kw = dict(entry=None, trim_at_mm=machine.TRIM_AT_MM, allowed_threads=[0])
    on = PipelineConfig(**ON, hairline_lines_strand_test=True)
    off = PipelineConfig(**ON)

    def pts(blocks):
        return [(t, [r.points for r in runs]) for t, runs in blocks]

    b60, r60 = strand_blocks(sp, on, block_wt={0: 60}, **kw)
    b40, r40 = strand_blocks(sp, on, block_wt={0: 40}, **kw)
    bnone, rnone = strand_blocks(sp, on, block_wt={}, **kw)
    assert r60["thread_wt"]["dark"] == 60
    assert r40["thread_wt"]["dark"] == rnone["thread_wt"]["dark"] == 40
    assert pts(b40) == pts(bnone)
    assert r60["strands"] >= 1
    boff60, roff60 = strand_blocks(sp, off, block_wt={0: 60}, **kw)
    boff, _ = strand_blocks(sp, off, **kw)
    assert "thread_wt" not in roff60
    assert pts(boff60) == pts(boff)


def test_the_block_weight_moves_the_ridge_widths(monkeypatch):
    """At 60 wt the ridge is read with 60 wt's narrower widths: the
    re-read passes `thread_wt=60` to the extraction for that polarity."""
    from digitizer_core import stage6_hairline_lines as L
    seen = []
    real = L.extract_strands

    def spy(sp, cfg, **kw):
        seen.append(kw)
        return real(sp, cfg, **kw)
    monkeypatch.setattr(L, "extract_strands", spy)
    sp = _sp(_strands(_ground()))
    L.strand_blocks(sp, PipelineConfig(**ON, hairline_lines_strand_test=True), entry=None,
                    trim_at_mm=machine.TRIM_AT_MM, allowed_threads=[0], block_wt={0: 60})
    assert seen[0] == {}
    assert {"thread_wt": 60, "polarities": ("dark",)} in seen


# --- the done-test on the real photo -----------------------------------------

OWL = TESTDATA / "photo" / "owl_kent.jpg"
# #882's zones, fractions of the source photo (tools/hairline_lines_trial.py).
ZONES = {"beak_bristles": (0.36, 0.18, 0.68, 0.48),
         "eyes": (0.25, 0.12, 0.75, 0.25),
         "breast": (0.0, 0.55, 1.0, 1.0)}


def _zones(sp, strands):
    h, w = sp.rgb.shape[:2]
    out = collections.Counter()
    for s in _sewable(strands):
        fx, fy = np.array([sp.to_px(x, y) for x, y in s["pts"]]).mean(axis=0) / [w, h]
        out[next((z for z, (x0, y0, x1, y1) in ZONES.items()
                  if x0 <= fx < x1 and y0 <= fy < y1), "elsewhere")] += 1
    return out


def test_owl_breast_barring_halves_and_the_bristles_stay():
    """owl_kent, #876's `classical` route, 40 wt, 127 mm: the breast strands
    fall from 31 to at most 15, and the 5 on the facial bristles stay."""
    cfg = PipelineConfig(target_width_mm=127.0, forced_class="photo_subject",
                         photo_prep=False, **ON)
    sp = run_stages(OWL, cfg).source_pixels
    off = _zones(sp, extract_strands(sp, cfg)[0])
    on = _zones(sp, extract_strands(sp, PipelineConfig(
        target_width_mm=127.0, forced_class="photo_subject", photo_prep=False, **ON,
        hairline_lines_strand_test=True))[0])
    assert off["breast"] == 31 and off["beak_bristles"] == 5
    assert on["breast"] <= off["breast"] // 2
    assert on["beak_bristles"] >= 5
