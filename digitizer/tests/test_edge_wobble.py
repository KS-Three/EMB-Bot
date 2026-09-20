"""`tools/edge_wobble.py` — does the sewn edge wander about the outline it was given?

Every case is a synthetic plan on a synthetic polygon, so the right answer is
known before the instrument runs. The one engine-backed case pins the
synthetic-logo control the 2026-09-19 spike measured clean.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import edge_wobble as ew  # noqa: E402
from digitizer_core import machine, stitches  # noqa: E402
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun  # noqa: E402

R_OUT, R_IN, STEP_MM = 10.0, 8.0, 0.4


def ring() -> Polygon:
    return Point(0, 0).buffer(R_OUT, 256).difference(Point(0, 0).buffer(R_IN, 256))


def ring_satin(outer=lambda i: 0.0, inner=lambda i: 0.0, arc=(0.0, 1.5 * math.pi)):
    """An alternating zigzag round the ring: station i sews outer then inner.
    `outer(i)` / `inner(i)` displace that station's penetration OUTWARD, mm."""
    n = int((arc[1] - arc[0]) * R_OUT / STEP_MM)
    pts = []
    for i in range(n):
        a = arc[0] + (arc[1] - arc[0]) * i / n
        for r in (R_OUT + outer(i), R_IN - inner(i)):
            pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def plan_with(runs) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="0000", rgb=(0, 0, 0), runs=list(runs))
    return StitchPlan(blocks=[block], palette=[{}])


def plan_of(points, kind=stitches.SATIN, shape_id="s") -> StitchPlan:
    return plan_with([StitchRun(points=list(points), kind=kind, shape_id=shape_id)])


def measure(points, kind=stitches.SATIN, poly=None):
    return ew.analyse_plan({"s": poly or ring()}, plan_of(points, kind))


def test_rails_on_the_outline_read_zero():
    row = measure(ring_satin())
    assert row["points"] > 200                     # 117 stations, two rails
    assert row["wobble_std_mm"] < 0.005
    assert row["wobble_p95_mm"] < 0.01
    assert row["share_over"] == 0.0


def test_a_sawtooth_is_recovered_at_its_own_amplitude():
    # +/-0.2 mm on alternate OUTER penetrations; the inner rail stays clean,
    # so half the points carry |dev| ~0.2 and the pooled std is ~0.2/sqrt(2).
    row = measure(ring_satin(outer=lambda i: 0.2 if i % 2 else -0.2))
    assert row["wobble_std_mm"] == pytest.approx(0.2 / math.sqrt(2), abs=0.02)
    assert row["wobble_p95_mm"] == pytest.approx(0.2, abs=0.03)
    assert row["share_over"] == pytest.approx(0.5, abs=0.05)
    assert row["short_stitches_excused"] == 0


def test_a_constant_pull_offset_is_not_wobble():
    # Pull compensation sews every penetration a constant distance OUTSIDE the
    # outline. That is displacement, which `edge_smoothness.offset_mm` owns.
    row = measure(ring_satin(outer=lambda i: 0.4, inner=lambda i: 0.4))
    assert row["wobble_std_mm"] < 0.005
    assert row["offset_mm"] == pytest.approx(0.4, abs=0.01)


def test_a_slow_taper_is_not_wobble():
    n = int(1.5 * math.pi * R_OUT / STEP_MM)
    row = measure(ring_satin(outer=lambda i: 0.4 * i / n))
    assert row["wobble_std_mm"] < 0.01


def test_a_single_dent_shows_in_the_tail_not_the_median():
    row = measure(ring_satin(outer=lambda i: -0.5 if i == 60 else 0.0))
    assert row["wobble_max_mm"] == pytest.approx(0.5, abs=0.05)
    assert row["wobble_p95_mm"] < 0.02
    worst = row["worst"][0]
    assert worst["shape_id"] == "s"
    a = 1.5 * math.pi * 60 / int(1.5 * math.pi * R_OUT / STEP_MM)
    assert math.dist(worst["at_mm"], (R_OUT * math.cos(a), R_OUT * math.sin(a))) < 1.0


def test_the_engines_own_short_stitches_are_excused():
    """`stage6_satin._short_stitch_guard` retracts ALTERNATE penetrations where
    a rail bunches under SATIN_SHORT_STITCH_AT_MM. Deliberate, and inward."""
    tight_in, tight_out = 0.6, 2.6                 # inner rail steps ~0.09 mm
    poly = Point(0, 0).buffer(tight_out, 256).difference(Point(0, 0).buffer(tight_in, 256))
    n = int(1.5 * math.pi * tight_out / STEP_MM)
    assert 1.5 * math.pi * tight_in / n < machine.SATIN_SHORT_STITCH_AT_MM
    pts = []
    for i in range(n):
        a = 1.5 * math.pi * i / n
        r_in = tight_in + (0.6 if i % 2 else 0.0)  # the capped 0.6 mm retraction
        pts += [(tight_out * math.cos(a), tight_out * math.sin(a)),
                (r_in * math.cos(a), r_in * math.sin(a))]
    row = measure(pts, poly=poly)
    assert row["short_stitches_excused"] == pytest.approx(n // 2, abs=2)
    assert row["wobble_std_mm"] < 0.01


def test_a_sawtooth_on_an_unbunched_rail_is_never_excused():
    # Same inward dips as a short stitch, but the rail steps a full 0.4 mm:
    # nothing in the engine retracts there, so this is a defect, not a technique.
    row = measure(ring_satin(outer=lambda i: -0.4 if i % 2 else 0.0))
    assert row["short_stitches_excused"] == 0
    assert row["wobble_p95_mm"] > 0.15


def test_fill_row_ends_are_an_edge_too():
    # Boustrophedon rows across a 20 x 10 mm bar; the RIGHT ends sawtooth.
    bar = Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])
    pts, rows = [], int(10 / 0.4)
    for j in range(1, rows):
        y = j * 0.4
        x_r = 20.0 - (0.3 if j % 4 < 2 else 0.0)
        row_pts = [(x, y) for x in np.arange(0.0, x_r, 3.0)] + [(x_r, y)]
        pts += row_pts if j % 2 else row_pts[::-1]
    ends = ew._row_ends(np.asarray(pts, float))
    # Every row end, jogged or not — a turn-angle test found 12 of these 24.
    assert (ends[:, 0] > 19).sum() == rows - 1
    row = ew.analyse_plan({"s": bar}, plan_of(pts, stitches.FILL))
    assert row["by_tier"]["fill"]["points"] >= 2 * (rows - 4)
    assert row["by_tier"]["fill"]["wobble_p95_mm"] == pytest.approx(0.15, abs=0.05)
    assert "satin" not in row["by_tier"]


def test_underlay_travel_and_orphans_are_not_measured():
    plan = plan_with([
        StitchRun(points=ring_satin(outer=lambda i: 0.3 * (i % 2)), kind=stitches.UNDERLAY, shape_id="s"),
        StitchRun(points=ring_satin(outer=lambda i: 0.3 * (i % 2)), kind=stitches.TRAVEL, shape_id="s"),
        StitchRun(points=ring_satin(outer=lambda i: 0.3 * (i % 2)), kind=stitches.SATIN, shape_id="gone"),
    ])
    row = ew.analyse_plan({"s": ring()}, plan)
    assert row["points"] == 0
    assert row["wobble_std_mm"] is None


def _square_loop(half: float, round_mm: float, n: int) -> list[tuple[float, float]]:
    """n points, evenly spaced round a square of half-side `half` whose corners
    are rounded at `round_mm` (0 = sharp), starting mid-way along the bottom."""
    from shapely.geometry import box
    sq = box(-half, -half, half, half)
    ring = (sq.buffer(-round_mm).buffer(round_mm, 64) if round_mm else sq).exterior
    start = ring.project(Point(0, -half))
    L = ring.length
    return [ring.interpolate((start + L * i / n) % L).coords[0] for i in range(n)]


def square_frame_satin(round_mm: float):
    """A 2 mm satin frame. The inner rail sits on its outline; the outer rail
    cuts every corner at `round_mm` — the deepest penetration sits
    round_mm * (1 - cos 45) inside the nearer SIDE (not sqrt2 - 1: that is the
    distance to the corner vertex, and the outline is its sides)."""
    from shapely.geometry import box
    frame = box(-10, -10, 10, 10).difference(box(-8, -8, 8, 8))
    n = int(80 / STEP_MM)
    outer, inner = _square_loop(10, round_mm, n), _square_loop(8, 0.0, n)
    return frame, [p for pair in zip(outer, inner) for p in pair]


def test_rounded_corners_are_binned_as_corners_not_as_wobble_everywhere():
    frame, pts = square_frame_satin(round_mm=1.0)
    zones = measure(pts, poly=frame)["rail_zones"]
    assert set(zones) == {"corner", "end", "mid"}
    row = measure(pts, poly=frame)
    # A corner-cutting penetration is NOT a short stitch: the rail steps a full
    # 0.4 mm along itself there. Projected onto the outline the same step reads
    # 0.28, and the first cut of `_excused` waved all four corners through.
    assert row["short_stitches_excused"] == 0
    assert zones["corner"]["share_over"] > 0.1
    assert zones["corner"]["wobble_max_mm"] == pytest.approx(1 - math.cos(math.pi / 4), abs=0.1)
    assert zones["mid"]["share_over"] == 0.0
    assert zones["mid"]["points"] > zones["corner"]["points"]


def test_sharp_rails_on_a_sharp_frame_read_clean_in_every_zone():
    frame, pts = square_frame_satin(round_mm=0.0)
    zones = measure(pts, poly=frame)["rail_zones"]
    assert all(z["share_over"] == 0.0 for z in zones.values())


def test_a_polygonised_circle_has_no_corners():
    # 256-gon: 1.4 deg a vertex. A curve is not a corner.
    zones = measure(ring_satin())["rail_zones"]
    assert zones.get("corner", {"points": 0})["points"] == 0


def test_fill_and_line_tiers_stay_out_of_the_rail_zones():
    bar = Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])
    pts = []
    for j in range(1, 25):
        row_pts = [(x, j * 0.4) for x in (0.0, 5.0, 10.0, 15.0, 20.0)]
        pts += row_pts if j % 2 else row_pts[::-1]
    row = ew.analyse_plan({"s": bar}, plan_of(pts, stitches.FILL))
    assert row["points"] > 0
    assert row["rail_zones"] == {}


def test_render_draws_one_tile_per_worst_spot(tmp_path):
    import cv2
    frame, pts = square_frame_satin(round_mm=1.0)
    plan = plan_of(pts)
    row = ew.analyse_plan({"s": frame}, plan)
    out = ew.render_worst({"s": frame}, plan, row, tmp_path / "w.png", box_mm=8.0, px_per_mm=20)
    img = cv2.imread(str(out))
    assert img.shape[0] == 160 and img.shape[1] == 160 * len(row["worst"])
    assert len(row["worst"]) >= 4                      # four corners, 2 mm apart rule
    assert (img.reshape(-1, 3) != 255).any(1).mean() > 0.05


def test_synthetic_logo_control_stays_clean():
    """The spike's control (2026-09-19): `logo_whitebg` sews on its outline.
    A ceiling, not a golden — it moves only if rails start to wander."""
    row = ew.analyse(ROOT / "testdata" / "logo_whitebg.png")
    assert row["points"] > 100
    # 0.038 measured on Windows 2026-09-19; real logos read ~0.10. The margin
    # is for per-platform polygon numerics, which this statistic barely sees.
    assert row["by_tier"]["satin"]["wobble_std_mm"] < 0.07
