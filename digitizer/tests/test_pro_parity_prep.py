"""Guards on the corpus harness's SOURCE-ART reconstruction (tools/pro_parity).

Everything here is a defect the harness actually shipped: it fused whole words
into one blob, inked the machine's travel walks as if they were artwork, opened
run-stitch linework out of existence, and drew white thread onto a white canvas
where nothing downstream could see it. The engine was then graded on that
damage. Each test below is one of those failures, written so it cannot come
back quietly.
"""
import importlib.util
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "pro_parity" / "prep_all.py"
spec = importlib.util.spec_from_file_location("pro_parity_prep", TOOL)
prep = importlib.util.module_from_spec(spec)
sys.modules["pro_parity_prep"] = prep
spec.loader.exec_module(prep)


def satin_bar(x0, y0, w, h, spacing=0.4):
    """A satin column: rows across `w`, stepping `spacing` down `h`."""
    pts, k = [], 0
    y = y0
    while y <= y0 + h:
        pts.append((x0, y) if k % 2 == 0 else (x0 + w, y))
        pts.append((x0 + w, y) if k % 2 == 0 else (x0, y))
        y += spacing
        k += 1
    return pts


def canvas_for(*runs, pad_mm=3.0):
    pts = [p for r in runs for p in r]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return prep.Canvas((min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1), pad_mm=pad_mm)


def components(mask, scale, min_mm2=0.5):
    n, lab, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    return [st[i, cv2.CC_STAT_AREA] / (scale * scale) for i in range(1, n)
            if st[i, cv2.CC_STAT_AREA] / (scale * scale) >= min_mm2]


# --------------------------------------------------------------- close radius
def test_close_radius_comes_from_measured_spacing_not_stitch_length():
    """The old rule was `len_p50 >= 2.8 mm -> close 3.8 mm`, which selected
    exactly backwards: a wide satin has LONG stitches and TIGHT rows, so the
    letters most in need of separation got the widest close."""
    wide = satin_bar(0, 0, 4.0, 12.0)          # 4 mm stitches, 0.4 mm rows
    cvs = canvas_for(wide)
    _, meas, _ = prep.analyse_block([wide], cvs)
    stitch_len = math.dist(wide[0], wide[1])
    assert stitch_len >= 2.8, "fixture must sit on the wrong side of the old rule"
    assert meas["row_spacing_mm"] == pytest.approx(0.4, abs=0.15)
    assert meas["close_mm"] < 1.0, "long-stitch satin must not get a wide close"


def test_two_letters_two_millimetres_apart_stay_two_shapes():
    """becker_hat_large: MARINE's six letters (2.4-4.1 mm apart) fused into a
    single 1460 mm^2 blob, so the engine was handed a slab and graded on it."""
    a = satin_bar(0, 0, 3.0, 10.0)
    b = satin_bar(5.4, 0, 3.0, 10.0)           # 2.4 mm of daylight between them
    cvs = canvas_for(a, b)
    mask, meas, _ = prep.analyse_block([a, b], cvs)
    assert len(components(mask, cvs.scale)) == 2
    assert meas["close_mm"] < 2.4


def test_dense_rows_still_close_into_one_solid_shape():
    """The close must still do its job: a fill's rows are artwork solid."""
    bar = satin_bar(0, 0, 6.0, 8.0, spacing=0.55)
    cvs = canvas_for(bar)
    mask, _, _ = prep.analyse_block([bar], cvs)
    comps = components(mask, cvs.scale)
    assert len(comps) == 1
    assert comps[0] > 6.0 * 8.0 * 0.8


# ------------------------------------------------------------------- travel
def test_connector_walk_between_two_bodies_is_not_painted():
    """proseal_beanie's tagline reconstructed as 2 blobs built almost entirely
    out of letter-to-letter walks. A walk lays thread, but not artwork."""
    a = satin_bar(0, 0, 3.0, 8.0)
    b = satin_bar(6.0, 0, 3.0, 8.0)
    walk = [a[-1], (4.5, 4.0), b[0]]           # one run, no trim: pure connector
    run = a + walk[1:2] + b
    cvs = canvas_for(run)
    mask, meas, flags = prep.analyse_block([run], cvs)
    assert meas["travel_segments"] >= 2
    assert len(components(mask, cvs.scale)) == 2, "the walk bridged the letters"


def test_long_single_pass_linework_survives():
    """MORPH_OPEN erased run-stitch linework outright (gaulke's sunburst
    spokes; proseal_beanie's blue spray). A long thin path is the artwork."""
    line = [(x, 0.0) for x in np.arange(0, 20.0, 2.0)]
    cvs = canvas_for(line)
    mask, meas, _ = prep.analyse_block([line], cvs)
    assert meas["travel_segments"] == 0
    comps = components(mask, cvs.scale, min_mm2=0.1)
    assert comps and max(comps) > 20.0 * prep.THREAD_W_MM * 0.7


def test_isolated_linework_gets_no_wide_close():
    """No row structure means no measured spacing means no bridging."""
    line = [(x, 0.0) for x in np.arange(0, 20.0, 2.0)]
    cvs = canvas_for(line)
    _, meas, _ = prep.analyse_block([line], cvs)
    assert meas["row_spacing_mm"] is None
    assert meas["close_mm"] == prep.CLOSE_MIN_MM


# --------------------------------------------------------------------- art
def test_art_is_rgba_with_transparent_ground_and_visible_white_thread():
    """PES writes white as (240,240,240). On the old 255 canvas that was
    invisible, and the white layer dropped out of mfab_lc, hotel_fremont_*,
    golf_hat and machine_beanie entirely."""
    white = satin_bar(0, 0, 4.0, 8.0)
    cvs = canvas_for(white)
    out = Path(__import__("tempfile").mkdtemp())
    prep.reconstruct([[white]], [(240, 240, 240)], cvs,
                     out / "art.png", out / "art_meta.json")
    img = cv2.imread(str(out / "art.png"), cv2.IMREAD_UNCHANGED)
    assert img.shape[2] == 4, "art must carry alpha — stage 1 reads it as ground truth"
    opaque = img[:, :, 3] > 127
    assert opaque.any() and not opaque.all()
    painted = img[:, :, :3][opaque]
    assert (painted == np.array([240, 240, 240])).all(), "white thread must survive"


def test_meta_records_the_measurements_the_art_cannot_carry():
    bar = satin_bar(0, 0, 4.0, 8.0)
    cvs = canvas_for(bar)
    out = Path(__import__("tempfile").mkdtemp())
    prep.reconstruct([[bar]], [(10, 10, 10)], cvs, out / "art.png", out / "art_meta.json")
    meta = __import__("json").loads((out / "art_meta.json").read_text())
    b = meta["blocks"][0]
    for k in ("row_spacing_mm", "close_mm", "open_fill", "angle_deg",
              "travel_segments", "visible_mm2"):
        assert k in b
    assert meta["scale_px_per_mm"] == prep.SCALE


# ------------------------------------------------------------------ decode
def test_decode_breaks_runs_on_every_command_the_file_records():
    pytest.importorskip("pystitch")
    import pystitch
    pat = pystitch.EmbPattern()
    for x in range(0, 40, 10):
        pat.add_stitch_absolute(pystitch.STITCH, x, 0)
    pat.add_stitch_absolute(pystitch.TRIM, 40, 0)
    for x in range(60, 100, 10):                 # 2 mm away: under TRAVEL_MM
        pat.add_stitch_absolute(pystitch.STITCH, x, 0)
    pat.add_stitch_absolute(pystitch.COLOR_CHANGE, 100, 0)
    for x in range(100, 140, 10):
        pat.add_stitch_absolute(pystitch.STITCH, x, 0)
    pat.add_stitch_absolute(pystitch.END, 140, 0)
    tmp = Path(__import__("tempfile").mkdtemp()) / "t.dst"
    pystitch.write(pat, str(tmp))
    blocks, breaks, _threads, _bounds, _j, _t = prep.decode(tmp)
    assert len(blocks) == 2, "a colour change ends a block"
    assert len(blocks[0]) == 2, "a trim ends a run even when the gap is 2 mm"
    assert breaks[0][0] == "start" and breaks[0][1] in ("trim", "jump")
    assert breaks[1][0] == "color"
    # and the gap the trim spans is never painted
    cvs = canvas_for(*blocks[0])
    mask, _, _ = prep.analyse_block(blocks[0], cvs)
    assert len(components(mask, cvs.scale, min_mm2=0.1)) == 2
