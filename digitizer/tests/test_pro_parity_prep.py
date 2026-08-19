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
def _one_block_plan(*runs):
    from digitizer_core.stitches import StitchBlock, StitchPlan
    return StitchPlan(blocks=[StitchBlock(0, "1000", (0, 0, 0), runs=list(runs))],
                      palette=[{}])


def test_a_travel_segment_is_not_a_machine_run():
    """`ours_blocks.json` counted `len(block.runs)` — PLAN objects, one per
    fill / satin / underlay / travel segment. `pro_blocks.json` counts MACHINE
    runs, in which a travel walk is thread-down and merges into the path it
    connects. Read side by side the two inflated ours 6-22x: becker_hat_small
    reported 290 runs against the pro's 13, and the same design's exported DST
    decodes to 35.
    """
    from digitizer_core.stitches import StitchRun, FILL, TRAVEL
    a = [(0.0, 0.0), (0.0, 4.0), (1.0, 4.0), (1.0, 0.0)]
    walk = [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]      # under TRAVEL_MM per step
    b = [(3.0, 0.0), (3.0, 4.0), (4.0, 4.0), (4.0, 0.0)]
    plan = _one_block_plan(StitchRun(a, FILL), StitchRun(walk, TRAVEL),
                           StitchRun(b, FILL))
    assert sum(len(bl.runs) for bl in plan.blocks) == 3, "three plan objects"
    out = Path(__import__("tempfile").mkdtemp())
    blocks, _breaks, _t, _bnds, _j, _tr = prep.decode_plan(plan, out / "ours.dst")
    assert sum(len(r) for r in blocks) == 1, "one continuous thread path"


def test_a_trimmed_run_does_open_a_machine_run():
    """The counterpart guard: the fix must not merge everything. A cut thread
    is a real break on both sides of the comparison."""
    from digitizer_core.stitches import StitchRun, FILL
    a = [(0.0, 0.0), (0.0, 4.0), (1.0, 4.0), (1.0, 0.0)]
    b = [(3.0, 0.0), (3.0, 4.0), (4.0, 4.0), (4.0, 0.0)]
    plan = _one_block_plan(StitchRun(a, FILL), StitchRun(b, FILL, jump=True, trim=True))
    out = Path(__import__("tempfile").mkdtemp())
    blocks, breaks, _t, _bnds, _j, trims = prep.decode_plan(plan, out / "ours.dst")
    assert sum(len(r) for r in blocks) == 2
    assert breaks[0][1] == "trim"
    assert trims >= 1


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


# ------------------------------------------------ one pro block, both harnesses
def _prep_both():
    """`prep_both.py`, loaded the way this file loads `prep_all.py`. It puts its
    own directory on `sys.path` and imports `prep_all` under that name, so the
    instance it holds is NOT the `prep` above — compare behaviour, not identity.
    """
    tool = TOOL.parent / "prep_both.py"
    s = importlib.util.spec_from_file_location("pro_parity_prep_both", tool)
    mod = importlib.util.module_from_spec(s)
    sys.modules["pro_parity_prep_both"] = mod
    s.loader.exec_module(mod)
    return mod


def _fake_decode():
    """Two blocks, five runs, one of EVERY break kind that can open a run.

    `hop` earns its place: it is the bucket only third-party files produce — a
    break inferred from distance where the file carries no explicit record —
    and it is the pro side's second-largest, 368 of 1,054 runs corpus-wide. Our
    own writer always emits an explicit record, so a fixture built only from
    kinds WE emit would assert `hop: 0` and pass on a hard-coded zero.
    """
    blocks = [[[(0.0, 0.0), (0.0, 4.0)], [(6.0, 0.0), (6.0, 4.0)],
               [(12.0, 0.0), (12.0, 4.0)], [(18.0, 0.0), (18.0, 4.0)]],
              [[(0.0, 6.0), (4.0, 6.0)]]]
    breaks = [["start", "trim", "jump", "hop"], ["color"]]
    meas = [{"travel_segments": 2, "travel_mm": 11.25},
            {"travel_segments": 0, "travel_mm": 0.0}]
    return blocks, breaks, meas


def test_pro_meta_histogram_labels_every_run_break():
    """The `run_breaks` histogram is the instrument that attributes
    fragmentation to a mechanism — trim vs jump vs colour. Every decoded run
    must land in exactly one bucket, or the diff under-counts silently."""
    blocks, breaks, meas = _fake_decode()
    pro = prep.pro_meta(blocks, breaks, (0.0, 0.0, 20.0, 8.0), jumps=1, trims=1,
                        meas=meas)
    assert pro["run_breaks"] == {"start": 1, "color": 1, "trim": 1, "jump": 1,
                                 "hop": 1}
    assert sum(pro["run_breaks"].values()) == pro["runs"] == 5
    assert pro["travel_segments"] == 2 and pro["travel_mm"] == 11.2


def test_prep_both_pro_block_is_the_shared_builder_output(tmp_path, monkeypatch):
    """`prep_both.py` hand-rolled its own `pro` block and omitted `run_breaks`,
    so the REAL-ART lane could not produce the trim attribution the recon lane
    already carried — docs/fragmentation-attribution-2026-08-18.md §4's last
    caveat. The two harnesses decode the same pro file with the same `decode()`;
    they must summarise it with the same code too.

    Asserted on the OUTPUT, not on the source text. An earlier version of this
    test grepped `prep_one` for the call, which was wrong in both directions: a
    mutant that called the shared builder and then dropped `run_breaks` from the
    result passed it, and a harmless rename turned it red. Equality against
    `pro_meta`'s own return value catches a divergent copy, a dropped key and a
    mutated value alike.

    Every heavy dependency is stubbed, so this needs neither the engine nor the
    Google Drive corpus — the point under test is the summary, not the pipeline.
    """
    both = _prep_both()
    pa, ra = both.prep_all, both.real_art
    blocks, breaks, meas = _fake_decode()
    bounds = (0.0, 0.0, 20.0, 8.0)
    threads = [(0, 0, 0), (255, 255, 255)]

    class _Res:
        regions = []
        warnings = []

    monkeypatch.setenv("PRO_PARITY_OUT", str(tmp_path))
    monkeypatch.setattr(both, "OUT", None)
    monkeypatch.setattr(pa, "find_file", lambda rel: tmp_path / "fake_source")
    monkeypatch.setattr(pa, "decode", lambda path: (blocks, breaks, threads, bounds, 1, 1))
    monkeypatch.setattr(pa, "Canvas", lambda b, **kw: object())
    monkeypatch.setattr(pa, "reconstruct", lambda *a, **k: (meas, None))
    monkeypatch.setattr(pa, "block_summary", lambda *a, **k: [])
    monkeypatch.setattr(pa, "render", lambda *a, **k: Path(a[3]).write_bytes(b"png"))
    monkeypatch.setattr(pa, "run_ours", lambda *a, **k: (_Res(), None, blocks, threads))
    monkeypatch.setattr(pa, "machine_meta", lambda d: {})
    monkeypatch.setattr(ra, "prepare", lambda src, dst: {"ink_bbox_px": [100, 50]})
    monkeypatch.setattr(ra, "dpi", lambda px, mm: 42.0)

    entry = both.prep_one("fixture", "fake.pes", "fake.png", "left_chest")

    assert entry["pro"] == pa.pro_meta(blocks, breaks, bounds, jumps=1, trims=1,
                                       meas=meas)
    # named explicitly: these three are exactly what the private copy dropped
    for key in ("run_breaks", "travel_segments", "travel_mm"):
        assert key in entry["pro"], f"the real-art lane lost {key} again"
