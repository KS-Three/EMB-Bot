"""The pro-parity scorecard has to measure truth, not flatter the engine.

Each test here is one of the four ways the pre-fix scorer lied, reduced to a
synthetic design small enough to reason about by hand:

  1. registration  — pro keeps its hoop origin, ours is bbox-centred, so two
     IDENTICAL designs scored as strangers (machine_beanie, 26.7 mm apart in y,
     scored coverage 0.219)
  2. coverage      — a 1 mm raster dilated to a ~3 mm swath made a 41%-density
     fill read as 98% covered
  3. travel        — counting "long moves per 1000 stitches" awarded 1.0 to any
     output that trims less than the pro, and missed drag walked in short steps
  4. underlay      — "first stitch in this cell is short" invented underlay on
     single-pass satin and on degenerate sub-0.5 mm defect stitches
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "pro_parity_scorecard",
    Path(__file__).resolve().parent.parent / "tools" / "pro_parity" / "scorecard.py",
)
sc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sc)


# ----------------------------------------------------------------- builders
def seg(x0, y0, x1, y1, block=0, trimmed=False):
    return (x0, y0, x1, y1, math.hypot(x1 - x0, y1 - y0), block, trimmed)


def rows_to_segs(pts, block=0, trims=()):
    """pts -> segment tuples; `trims` holds indices whose INCOMING move is cut."""
    return [seg(*pts[i], *pts[i + 1], block=block, trimmed=(i + 1) in trims)
            for i in range(len(pts) - 1)]


def fill_block(x0, y0, w, h, spacing, block=0, stitch=3.5):
    """Horizontal fill rows `spacing` mm apart, sewn boustrophedon, broken into
    machine-legal stitches (a real row is never one 30 mm needle move)."""
    pts = []
    y = y0
    flip = False
    n = max(2, int(w / stitch) + 1)
    while y <= y0 + h + 1e-9:
        a, b = (x0 + w, x0) if flip else (x0, x0 + w)
        pts += [(a + (b - a) * i / (n - 1), y) for i in range(n)]
        flip = not flip
        y += spacing
    return rows_to_segs(pts, block=block)


def satin_column(x0, y0, length, width, pitch=0.4, block=0):
    """A single-pass satin column running +x, zigzagging across `width`."""
    pts = []
    x = x0
    top = True
    while x <= x0 + length + 1e-9:
        pts.append((x, y0 + (width if top else 0.0)))
        top = not top
        x += pitch
    return rows_to_segs(pts, block=block)


# --------------------------------------------------------- 1. registration
def test_registration_recovers_a_pure_translation():
    """Same design, 26.7 mm apart in y — machine_beanie's exact failure. Without
    registration the two never overlap; with it they must read as identical."""
    pro = fill_block(0, 0, 30, 20, 0.4)
    ours = [seg(a, b + 26.7, c, d + 26.7) for (a, b, c, d, _l, _bk, _t) in pro]
    bb = sc.bounds(pro, ours)

    raw = sc._iou(sc.solid(sc.raster(pro, bb)), sc.solid(sc.raster(ours, bb)))
    dx, dy, reg = sc.register(pro, ours, bb)

    assert raw < 0.05, "un-registered copies must not overlap at all"
    assert dy == pytest.approx(-26.7, abs=0.3)
    assert dx == pytest.approx(0.0, abs=0.3)
    assert reg > 0.95, "a pure translation must register back to near-identity"


def test_registration_will_not_teleport_a_design_to_fake_agreement():
    """The search is bounded, so it cannot solve a real placement error by
    sliding a design halfway across the hoop."""
    pro = fill_block(0, 0, 20, 20, 0.4)
    ours = [seg(a + 500, b, c + 500, d) for (a, b, c, d, _l, _bk, _t) in pro]
    bb = sc.bounds(pro, ours)

    dx, dy, _reg = sc.register(pro, ours, bb)

    assert math.hypot(dx, dy) <= sc.REG_MAX


# -------------------------------------------------------------- 2. coverage
def test_a_widely_spaced_fill_does_not_read_as_solid():
    """1.2 mm row spacing with 0.5 mm thread is 42% covered ground. The old
    1 mm raster + dilation called that 98% covered; the opacity gate must not."""
    dense = fill_block(0, 0, 30, 20, 0.4)
    sparse = fill_block(0, 0, 30, 20, 1.2)
    bb = sc.bounds(dense, sparse)

    solid_dense = sc.solid(sc.raster(dense, bb))
    solid_sparse = sc.solid(sc.raster(sparse, bb))

    assert solid_dense.sum() > 0
    assert solid_sparse.sum() < 0.5 * solid_dense.sum(), (
        "rows spaced past the thread width leave fabric showing and must not "
        "count as solid coverage")

    wider = sc.solid(sc.raster(fill_block(0, 0, 30, 20, 1.5), bb))
    assert wider.sum() < 0.05 * solid_dense.sum(), (
        "1.5 mm rows of 0.5 mm thread are 1 mm of bare fabric apart — nothing "
        "about that reads as covered")


def test_coverage_penalises_overspill_as_well_as_gaps():
    """proseal_hat's 332 mm2 of thread outside the pro's shape has to cost
    something: the metric is symmetric, so painting extra is not free."""
    pro = fill_block(0, 0, 20, 20, 0.4)
    over = fill_block(0, 0, 30, 20, 0.4)     # same design, 50% wider
    bb = sc.bounds(pro, over)

    sp = sc.solid(sc.raster(pro, bb))
    so = sc.solid(sc.raster(over, bb))
    iou = sc._iou(sp, so)
    recall = float((sp & so).sum()) / float(sp.sum())

    assert recall > 0.95, "everything the pro sewed is covered"
    assert iou < 0.75, "...but the overspill still has to show up in the score"


def test_a_missing_colour_cannot_hide_behind_a_good_iou():
    """becker_beanie: MARINE replaced by the slab it sits on. Same ground, same
    mm2 — only the visible colour changed, and that must be visible."""
    bb = (-2.0, -2.0, 34.0, 24.0)
    gold = fill_block(0, 0, 30, 20, 0.4, block=0)
    word = fill_block(4, 4, 10, 6, 0.4, block=1)
    pro_segs = gold + word
    pro_blocks = [{"block": 0, "rgb": [208, 166, 96]}, {"block": 1, "rgb": [0, 0, 0]}]
    ours_blocks = [{"block": 0, "rgb": [208, 166, 96]}]

    faithful, _sp, _so, d_ok = sc.coverage_component(
        pro_segs, pro_segs, bb, pro_blocks, pro_blocks)
    slab, _sp2, _so2, d_bad = sc.coverage_component(
        pro_segs, gold, bb, pro_blocks, ours_blocks)

    assert faithful > 0.97
    assert d_bad["recall"] > 0.95, "the slab does cover the word's ground"
    assert d_bad["worst_colour_recall"] < 0.2, "but the word is not there"
    assert slab < 0.85


# ---------------------------------------------------------------- 3. travel
def test_drag_across_bare_fabric_is_measured_in_mm():
    """Two blobs joined by one untrimmed 20 mm move. That thread lies on fabric
    nothing else ever covers, so ~20 mm of drag must be reported."""
    left = fill_block(0, 0, 10, 10, 0.4)
    right = fill_block(30, 0, 10, 10, 0.4)
    bridge = [seg(10.0, 5.0, 30.0, 5.0)]
    segs = left + bridge + right
    bb = sc.bounds(segs)

    drag, walks, worst = sc.exposed_drag(segs, bb, sc.hidden_mask(segs, bb))

    assert drag == pytest.approx(20.0, abs=3.0)
    assert walks == 1
    assert worst == pytest.approx(20.0, abs=3.0)


def test_walking_the_same_drag_in_short_steps_costs_the_same():
    """The engine's evasion: 2.5 mm sewn steps instead of one long move. Length
    thresholds miss it; sampling the path does not."""
    left = fill_block(0, 0, 10, 10, 0.4)
    right = fill_block(30, 0, 10, 10, 0.4)
    walk = rows_to_segs([(10.0 + 2.5 * i, 5.0) for i in range(9)])
    stepped = left + walk + right
    one_move = left + [seg(10.0, 5.0, 30.0, 5.0)] + right
    bb = sc.bounds(stepped)

    d_steps, _w, _x = sc.exposed_drag(stepped, bb, sc.hidden_mask(stepped, bb))
    d_one, _w2, _x2 = sc.exposed_drag(one_move, bb, sc.hidden_mask(one_move, bb))

    assert d_steps > 12.0, "sewing the drag in short steps must not hide it"
    assert d_steps > 0.8 * d_one, (
        "the same 20 mm of bare fabric is crossed either way")


def test_a_trimmed_jump_is_invisible_and_free():
    """Same geometry, thread cut before the move. No thread crosses the fabric,
    so the drag is zero — trims cost nothing here by design."""
    left = fill_block(0, 0, 10, 10, 0.4)
    right = fill_block(30, 0, 10, 10, 0.4)
    bridge = [seg(10.0, 5.0, 30.0, 5.0, trimmed=True)]
    segs = left + bridge + right
    bb = sc.bounds(segs)

    drag, walks, _worst = sc.exposed_drag(segs, bb, sc.hidden_mask(segs, bb))

    assert drag < 1.0
    assert walks == 0


def test_travel_under_later_coverage_is_not_drag():
    """Thread walked across ground a fill later covers is hidden thread. It is
    an economy question, not a visible defect, and must not be charged here."""
    walk = rows_to_segs([(2.0 + 2.0 * i, 5.0) for i in range(9)])
    cover = fill_block(0, 0, 20, 10, 0.4)
    segs = walk + cover
    bb = sc.bounds(segs)

    drag, _walks, _worst = sc.exposed_drag(segs, bb, sc.hidden_mask(segs, bb))

    assert drag < 2.0


def test_zero_trims_no_longer_buys_a_perfect_travel_score():
    """The headline bug: the old metric handed 1.0 to any output that trimmed
    less often than the pro, however much thread it dragged across the fabric."""
    left = fill_block(0, 0, 10, 10, 0.4)
    right = fill_block(30, 0, 10, 10, 0.4)
    dragged = left + [seg(10.0, 5.0, 30.0, 5.0)] + right
    trimmed = left + [seg(10.0, 5.0, 30.0, 5.0, trimmed=True)] + right
    bb = sc.bounds(dragged)

    d_drag, _w, _x = sc.exposed_drag(dragged, bb, sc.hidden_mask(dragged, bb))
    d_trim, _w2, _x2 = sc.exposed_drag(trimmed, bb, sc.hidden_mask(trimmed, bb))
    tol = 0.2 * 40.0
    score_drag = 1.0 / (1.0 + max(0.0, d_drag - d_trim) / tol)

    assert sum(1 for s in dragged if s[6]) == 0, "the dragging output trims nothing"
    assert score_drag < 0.35


# -------------------------------------------------------------- 4. underlay
def test_single_pass_satin_has_no_underlay():
    """gaulke_plowing_lc's ghost: 1.6 mm single-pass satin, no underlay pass,
    yet the old first-stitch-under-2mm rule scored it 0.82."""
    segs = satin_column(0, 0, 40, 1.6)
    bb = sc.bounds(segs)

    under_mm, sewn_mm, _mask = sc.underlay_stats(segs, bb)

    assert sewn_mm > 100.0
    assert under_mm / sewn_mm < 0.05


def test_a_real_underlay_pass_is_found():
    """Centre run first, satin over it second. That first pass IS underlay and
    the classifier has to say so."""
    run = rows_to_segs([(x, 0.8) for x in np.arange(0.0, 40.0, 2.0)])
    cover = satin_column(0, 0, 40, 1.6)
    segs = run + cover
    bb = sc.bounds(segs)

    under_mm, sewn_mm, mask = sc.underlay_stats(segs, bb)

    assert under_mm / sewn_mm > 0.05
    assert mask.any()


def test_degenerate_stitches_are_defects_not_underlay():
    """machine_beanie's 935 sub-0.5 mm stitches piled in one spot scored a
    perfect 1.0 underlay share. They lay no structure and must not count."""
    junk = rows_to_segs([(10.0 + 0.1 * (i % 2), 5.0) for i in range(936)])
    cover = fill_block(0, 0, 20, 10, 0.4)
    segs = junk + cover
    bb = sc.bounds(segs)

    under_mm, sewn_mm, _mask = sc.underlay_stats(segs, bb)
    junk_mm = sum(s[4] for s in junk)

    assert junk_mm > 90.0, "the defect really is ~94 mm of thread"
    assert under_mm < 0.5 * junk_mm


def test_underlay_component_charges_for_overspend():
    """Four times the pro's underlay is not four times as good. The old rule
    capped the ratio at 1.0, so becker_beanie's overspend scored perfect."""
    pro = rows_to_segs(
        [(x, 0.8) for x in np.arange(0.0, 40.0, 2.0)]) + satin_column(0, 0, 40, 1.6)
    bb = sc.bounds(pro)
    pu, ps, _m = sc.underlay_stats(pro, bb)
    pf = pu / ps

    lean = sc.underlay_component(pro, pro, bb)[0]

    assert lean > 0.9, "matching the pro exactly scores well"
    assert pf > 0.0
    r = (4 * pf + 0.02) / (pf + 0.02)
    assert min(r, 1 / r) < 0.4, "4x the pro's underlay must not score 1.0"


def test_a_background_fill_under_other_lettering_is_not_underlay():
    """Layered artwork is not underlay: the cover has to be the same needle.
    Counting a gold background under black letters invents underlay the pro
    never sewed (it is what pushed pro shares to 0.5+ across the corpus)."""
    background = fill_block(0, 0, 20, 12, 0.4, block=0)
    lettering = fill_block(2, 2, 16, 8, 0.4, block=1)
    segs = background + lettering
    bb = sc.bounds(segs)

    under_mm, sewn_mm, _mask = sc.underlay_stats(segs, bb)

    assert under_mm / sewn_mm < 0.05


# ------------------------------------------------------------ trim recovery
def test_trim_inference_reads_an_isolated_long_move_as_a_jump():
    """No command column in the CSV: an isolated long move between ordinary
    stitches is a machine jump, while a chain of long steps is a sewn walk."""
    pts = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (20.0, 0.0), (21.0, 0.0)]
    jump = sc.infer_trims(rows_to_segs(pts))
    walk = sc.infer_trims(rows_to_segs(
        [(0.0, 0.0), (1.0, 0.0), (6.0, 0.0), (11.0, 0.0), (16.0, 0.0)]))

    assert [s[6] for s in jump] == [False, False, True, False]
    assert not any(s[6] for s in walk), "a chain of long steps is sewn thread"


# ------------------------------------------------------- 5. chance correction
# `direction` and `sttype` are bounded agreement measures: both used to pay out
# ~0.5 for a wrong answer, so ~21 of their combined 40 points were free. They
# are now rescaled so chance reads 0. These tests pin the floor, and pin that a
# real answer still scores.
def test_random_directions_score_nothing_after_correction():
    """The floor this fixes: two unrelated designs agreed 'half' on direction.
    The analytic floor must match what random angles actually do."""
    rng = np.random.default_rng(0)
    pro = rng.uniform(-math.pi / 2, math.pi / 2, size=20000)
    ours = rng.uniform(-math.pi / 2, math.pi / 2, size=20000)
    diff = np.abs(pro - ours)
    diff = np.minimum(diff, math.pi - diff)

    observed = float(np.mean(1 - diff / (math.pi / 2)))

    assert observed == pytest.approx(sc.DIRECTION_CHANCE, abs=0.01), (
        "the analytic floor has to be what random angles really score")
    assert sc.chance_correct(observed, sc.DIRECTION_CHANCE) < 0.02


def test_matching_directions_still_score_full_marks():
    """Correction rescales the floor, it must not move the ceiling."""
    assert sc.chance_correct(1.0, sc.DIRECTION_CHANCE) == pytest.approx(1.0)


def test_doing_worse_than_chance_clamps_to_zero():
    """A perpendicular answer is wrong, not worth negative points that could
    claw marks off another component."""
    assert sc.chance_correct(0.0, sc.DIRECTION_CHANCE) == 0.0
    assert sc.chance_correct(0.2, sc.DIRECTION_CHANCE) == 0.0


def test_calling_everything_fill_on_a_fill_heavy_design_earns_nothing():
    """The measurement this unblocks. A design the pro sewed 95% as fill is
    matched 95% of the time by an engine that only knows how to fill, and the
    old scale paid 19 of 20 points for it. Corrected, that is worth ~0 — so
    fill-vs-satin routing work has something honest to move."""
    pro = np.array([2] * 95 + [1] * 5)      # 0=run 1=satin 2=fill
    ours = np.full(100, 2)                  # everything is a fill

    observed = float(np.mean(pro == ours))
    chance = sc.type_chance(pro, ours)

    assert observed == pytest.approx(0.95)
    assert chance == pytest.approx(0.95), (
        "an all-fill guess agrees exactly as often as chance predicts")
    assert sc.chance_correct(observed, chance) == 0.0


def test_getting_the_satin_fill_split_right_still_scores():
    """The other half of the contract: an engine that actually routes the
    satins as satins must be paid for it."""
    pro = np.array([2] * 60 + [1] * 40)
    right = pro.copy()
    wrong = np.full(100, 2)

    assert sc.chance_correct(float(np.mean(pro == right)),
                             sc.type_chance(pro, right)) == pytest.approx(1.0)
    assert sc.chance_correct(float(np.mean(pro == wrong)),
                             sc.type_chance(pro, wrong)) == 0.0


def test_a_partly_right_split_lands_between_the_two():
    """Half the satins found is real progress and has to read as such."""
    pro = np.array([2] * 60 + [1] * 40)
    half = np.array([2] * 60 + [1] * 20 + [2] * 20)

    score = sc.chance_correct(float(np.mean(pro == half)), sc.type_chance(pro, half))

    assert 0.2 < score < 0.9


def test_degenerate_agreement_passes_through_instead_of_dividing_by_zero():
    """Both sides all fill: chance agreement is 1.0 and the correction is 0/0.
    A design whose types genuinely all match must not be marked down for the
    task having been easy."""
    allfill = np.full(50, 2)

    chance = sc.type_chance(allfill, allfill)

    assert chance == pytest.approx(1.0)
    assert sc.chance_correct(1.0, chance) == pytest.approx(1.0)


def _write_csv(path, pts, block=0):
    path.write_text("block,x_mm,y_mm\n"
                    + "".join(f"{block},{x},{y}\n" for x, y in pts))


def _fill_points(x0, y0, w, h, spacing, stitch=3.5):
    pts, y, flip = [], y0, False
    n = max(2, int(w / stitch) + 1)
    while y <= y0 + h + 1e-9:
        a, b = (x0 + w, x0) if flip else (x0, x0 + w)
        pts += [(a + (b - a) * i / (n - 1), y) for i in range(n)]
        flip = not flip
        y += spacing
    return pts


def test_score_design_reports_both_scales(tmp_path):
    """Wiring check: the corrected score is what `score` means now, the old
    number survives as `score_raw`, and identical designs still score at the
    top of both scales."""
    pts = _fill_points(0, 0, 20, 12, 0.4)
    _write_csv(tmp_path / "pro_stitches.csv", pts)
    _write_csv(tmp_path / "ours_stitches.csv", pts)

    s = sc.score_design(tmp_path)

    assert s["parts"]["direction"] == pytest.approx(1.0, abs=0.05)
    assert s["parts_raw"]["direction"] == pytest.approx(1.0, abs=0.05)
    assert s["detail"]["chance_floor"]["direction"] == pytest.approx(0.5)
    assert s["score"] > 90 and s["score_raw"] > 90


def test_a_forty_five_degree_fill_stops_collecting_half_the_direction_points(tmp_path):
    """Where the correction actually bites. A fill sewn 45 deg off the pro's
    angle is the chance case exactly — the old scale paid it 10 of the 20
    direction points for being wrong, and the corrected scale pays none."""
    base = _fill_points(0, 0, 16, 16, 0.4)
    a, cx, cy = math.radians(45), 8.0, 8.0
    rot = [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a),
            cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)) for x, y in base]
    _write_csv(tmp_path / "pro_stitches.csv", base)
    _write_csv(tmp_path / "ours_stitches.csv", rot)

    s = sc.score_design(tmp_path)

    assert s["parts_raw"]["direction"] == pytest.approx(0.5, abs=0.05)
    assert s["parts"]["direction"] == 0.0
    assert s["score_raw"] - s["score"] == pytest.approx(10.0, abs=1.0)


def test_a_perpendicular_fill_was_already_scoring_zero(tmp_path):
    """The other end, and the reason the 45 deg case is the one that matters:
    an exact 90 deg miss is 0.0 raw, so the correction has nothing to take and
    must not push it negative."""
    _write_csv(tmp_path / "pro_stitches.csv", _fill_points(0, 0, 20, 12, 0.4))
    _write_csv(tmp_path / "ours_stitches.csv",
               [(y, x) for x, y in _fill_points(0, 0, 12, 20, 0.4)])

    s = sc.score_design(tmp_path)

    assert s["parts_raw"]["direction"] == pytest.approx(0.0, abs=0.05)
    assert s["parts"]["direction"] == 0.0
