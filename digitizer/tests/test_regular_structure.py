"""`cfg.regular_structure` (built OFF 2026-11-13): what the art repeats sews as one shape repeated.

Kent on Bridge's ship's wheel: "All of the wheel handles look different from
eachother, this would be better if they all looked the same." The fixtures here
are the synthetic cases of that: eight noisy copies round a circle, a jittered
3 x 3 grid, five stripes of uneven width, a wheel traced as ONE region, and the
set that must NOT group (look-alikes that are deliberately different sizes).
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import regular_structure as rs
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region

SRC = 0.2                     # one source pixel, mm
P = SimpleNamespace(input_px_per_mm=1.0 / SRC, px_per_mm=8.0)


def _jitter(poly, rng, amp):
    """Every vertex moved up to `amp` mm: a raster trace's noise."""
    dense = poly.segmentize(0.4)
    ext = np.asarray(dense.exterior.coords)[:-1]
    ext = ext + rng.uniform(-amp, amp, ext.shape)
    holes = []
    for h in dense.interiors:
        hc = np.asarray(h.coords)[:-1]
        holes.append(hc + rng.uniform(-amp, amp, hc.shape))
    out = Polygon(ext, holes)
    return out if out.is_valid else rs._largest(out.buffer(0))


def _region(poly, thread=5, sid=None, **meta):
    return Region(shape_id=sid or f"S{abs(hash(poly.wkb)) % 10**8:08d}", polygon=poly,
                  thread_index=thread, thread_number=str(thread), area_mm2=poly.area, meta=dict(meta))


def _handle():
    """A handle: a knob on a stem, pointing +x from the origin."""
    stem = box(0.0, -0.6, 5.0, 0.6)
    knob = Point(5.8, 0.0).buffer(1.2, 32)
    return unary_union([stem, knob])


def _spread(polys):
    """Worst mean boundary distance between any member and the first, each
    brought onto the first's frame by its centroid and the best rotation."""
    ref = rs._shape(0, polys[0])
    ref_c = rs._canon(ref.poly, ref.cx, ref.cy, 0.0, False)
    worst = 0.0
    for p in polys[1:]:
        d, _, _ = rs._align(ref_c, rs._shape(0, p))
        worst = max(worst, d)
    return worst


def _wheel_members(rng, n=8, radius=20.0, amp=0.08, pos=0.08):
    base = _handle()
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        g = affinity.rotate(base, a, origin=(0, 0), use_radians=True)
        g = affinity.translate(g, radius * math.cos(a) + rng.uniform(-pos, pos),
                               radius * math.sin(a) + rng.uniform(-pos, pos))
        out.append(_jitter(g, rng, amp))
    return out


def test_eight_noisy_copies_on_a_circle_become_one_shape_on_eight_equal_angles():
    rng = np.random.default_rng(1)
    regions = [_region(p, sid=f"H{k}") for k, p in enumerate(_wheel_members(rng))]
    before = _spread([r.polygon for r in regions])
    report = rs.apply_regular_structure(regions, P)
    g, = report["groups"]
    assert g["kind"] == "rotation" and g["fold"] == 8
    assert all(m["moved"] for m in g["members"]), g
    after = _spread([r.polygon for r in regions])
    assert before > 0.02 and after < 0.25 * before, (before, after)
    # equal angles about the fitted centre
    c = g["centre"]
    phis = sorted(math.atan2(r.polygon.centroid.y - c[1], r.polygon.centroid.x - c[0]) for r in regions)
    steps = np.diff(phis + [phis[0] + 2 * math.pi])
    assert np.ptp(steps) < math.radians(0.2)
    assert all(r.meta[rs.META_KEY]["kind"] == "rotation" for r in regions)


def test_jittered_three_by_three_grid_sits_on_one_pitch():
    rng = np.random.default_rng(2)
    regions = []
    for i in range(3):
        for j in range(3):
            sq = box(0, 0, 3.0, 3.0)
            sq = affinity.translate(sq, 5.0 * i + rng.uniform(-0.1, 0.1), 5.0 * j + rng.uniform(-0.1, 0.1))
            regions.append(_region(_jitter(sq, rng, 0.07), sid=f"Q{i}{j}"))
    before = _spread([r.polygon for r in regions])
    report = rs.apply_regular_structure(regions, P)
    g, = report["groups"]
    assert g["kind"] == "grid"
    assert all(m["moved"] for m in g["members"])
    assert _spread([r.polygon for r in regions]) < 0.25 * before
    # one lattice: every step along a row, and every step along a column, the same
    pos = {r.shape_id: np.array([r.polygon.centroid.x, r.polygon.centroid.y]) for r in regions}
    across = [pos[f"Q{i + 1}{j}"] - pos[f"Q{i}{j}"] for i in range(2) for j in range(3)]
    down = [pos[f"Q{i}{j + 1}"] - pos[f"Q{i}{j}"] for i in range(3) for j in range(2)]
    for steps in (across, down):
        assert max(np.hypot(*(s - steps[0])) for s in steps) < 1e-6


def _widths(regions):
    return [r.polygon.bounds[3] - r.polygon.bounds[1] for r in regions]


def test_five_stripes_of_uneven_width_sew_one_width_at_one_pitch():
    rng = np.random.default_rng(3)
    widths = [3.9, 4.1, 3.95, 4.08, 3.97]           # within half a source pixel of 4
    regions = []
    for k, w in enumerate(widths):
        y = 8.0 * k + rng.uniform(-0.2, 0.2)
        regions.append(_region(box(-40.0, y, 40.0, y + w), sid=f"T{k}"))
    report = rs.apply_regular_structure(regions, P)
    g, = report["groups"]
    assert g["kind"] == "row"
    after = _widths(regions)
    assert max(after) - min(after) < 0.02, after
    tops = sorted(r.polygon.bounds[1] for r in regions)
    assert np.ptp(np.diff(tops)) < 0.02


def test_an_already_regular_group_keeps_its_outlines_and_its_tag():
    """Kent's flag: stripes that agree below the Design's 0.1 mm unit are not
    redrawn (redrawing them re-planned the long satin for nothing), but later
    stages still get the group."""
    regions = [_region(box(-40.0, 8.0 * k + 0.01 * k, 40.0, 8.0 * k + 4.0 + 0.02 * (k % 2)), sid=f"F{k}")
               for k in range(5)]
    before = [r.polygon.wkb for r in regions]
    report = rs.apply_regular_structure(regions, P)
    g, = report["groups"]
    assert g["confirmed"] and g["kind"] == "row"
    assert all(m.get("held") == "already regular" and not m["moved"] for m in g["members"])
    assert [r.polygon.wkb for r in regions] == before
    assert all(r.meta[rs.META_KEY]["id"] == g["id"] and r.meta[rs.META_KEY]["moved"] is False
               for r in regions)


def test_look_alikes_of_deliberately_different_sizes_do_not_group():
    regions = []
    for k, side in enumerate((3.0, 3.4, 3.8, 4.2, 4.6)):     # a two-pixel size step
        regions.append(_region(box(8.0 * k, 0.0, 8.0 * k + side, side), sid=f"D{k}"))
    for k, rad in enumerate((1.5, 1.75, 2.0)):
        regions.append(_region(Point(8.0 * k, 20.0).buffer(rad, 64), sid=f"C{k}"))
    before = [r.polygon.wkb for r in regions]
    report = rs.apply_regular_structure(regions, P)
    # look-alikes may be REPORTED, but a size step refuses every member
    assert not any(g["confirmed"] for g in report["groups"]), report["groups"]
    # each square repeats itself four times, but is already exact: left as traced
    assert not any(s["moved"] for s in report["self"])
    held = [m["held"] for g in report["groups"] for m in g["members"]]
    assert "size step" in held
    assert [r.polygon.wkb for r in regions] == before
    assert not any(rs.META_KEY in r.meta for r in regions)


def test_a_wheel_traced_as_one_region_repeats_one_handle():
    rng = np.random.default_rng(4)
    rim = Point(0, 0).buffer(16.5, 128).difference(Point(0, 0).buffer(13.0, 128))
    handles = [affinity.rotate(_handle(), 360.0 * k / 8, origin=(0, 0)) for k in range(8)]
    handles = [affinity.translate(h, 16.0 * math.cos(math.radians(45 * k)),
                                  16.0 * math.sin(math.radians(45 * k))) for k, h in enumerate(handles)]
    wheel = _jitter(unary_union([rim, *handles]), rng, 0.1)
    assert isinstance(wheel, Polygon) and len(wheel.interiors) == 1
    regions = [_region(wheel, sid="W")]
    report = rs.apply_regular_structure(regions, P)
    s, = report["self"]
    assert s["fold"] == 8 and s["moved"], s
    new = regions[0].polygon
    c = new.centroid
    d = rs.mean_dev(new, affinity.rotate(new, 45.0, origin=c))
    assert d < 0.25 * rs.mean_dev(wheel, affinity.rotate(wheel, 45.0, origin=wheel.centroid))
    assert regions[0].meta[rs.META_KEY]["kind"] == "self_rotation"


def test_a_seam_with_another_colour_is_held():
    """A member abutting another colour keeps that edge where it was traced."""
    rng = np.random.default_rng(5)
    regions = [_region(p, sid=f"H{k}") for k, p in enumerate(_wheel_members(rng))]
    # a disc of another colour touching the first handle's knob
    knob = regions[0].polygon
    neighbour = Point(knob.bounds[2] + 1.0, knob.centroid.y).buffer(1.05, 64)
    neighbour = neighbour.difference(knob)
    regions.append(_region(neighbour, thread=9, sid="N"))
    before = regions[0].polygon
    rs.apply_regular_structure(regions, P)
    after = regions[0].polygon
    assert after.intersection(neighbour).area <= before.intersection(neighbour).area + 1e-6


def test_lettering_is_never_a_member():
    rng = np.random.default_rng(6)
    regions = [_region(p, sid=f"H{k}", text_candidate=True, text_cluster_id=1)
               for k, p in enumerate(_wheel_members(rng))]
    before = [r.polygon.wkb for r in regions]
    report = rs.apply_regular_structure(regions, P)
    assert report["groups"] == []
    assert [r.polygon.wkb for r in regions] == before


def test_mirrored_pair_is_found_and_made_exact_mirrors():
    rng = np.random.default_rng(7)
    # a boot: an L with unequal arms has no mirror symmetry of its own
    foot = Polygon([(0, 0), (7, 0), (7, 1.5), (2.5, 1.5), (2.5, 6), (0, 6)])
    left = _jitter(affinity.translate(foot, -9.0, 0.0), rng, 0.1)
    right = _jitter(affinity.scale(affinity.translate(foot, -9.2, 0.15), -1.0, 1.0, origin=(0, 0)), rng, 0.1)
    regions = [_region(left, sid="L"), _region(right, sid="R")]
    report = rs.apply_regular_structure(regions, P)
    g, = report["groups"]
    assert g["kind"] == "mirror_pair" and all(m["moved"] for m in g["members"])
    a, b = regions[0].polygon, regions[1].polygon
    axis = math.radians(g["axis_deg"])
    m = rs._reflect(a, Point(g["midpoint"]), axis)
    assert rs.mean_dev(m, b) < 0.01


def test_a_convex_blob_is_never_a_self_repeat():
    """Precision drone's 2 mm2 grey blob read as a rounded triangle (3-fold
    and mirror within the gates) until the solidity guard: nothing sticks
    out of it, so nothing repeats."""
    rng = np.random.default_rng(8)
    tri = Polygon([(0, 0), (3, 0), (1.5, 2.6)]).buffer(0.4, 16)
    regions = [_region(_jitter(tri, rng, 0.05), sid="B")]
    report = rs.apply_regular_structure(regions, P)
    assert report["self"] == []


def test_a_member_on_another_colours_layer_still_moves():
    """Stage-4 regions stack (a QR finder's black core lies ON a white
    square, not in a hole of it). The layer under a member is not a seam."""
    rng = np.random.default_rng(9)
    regions = []
    for i in range(3):
        for j in range(3):
            sq = affinity.translate(box(0, 0, 3.0, 3.0), 6.0 * i + rng.uniform(-0.1, 0.1),
                                    6.0 * j + rng.uniform(-0.1, 0.1))
            regions.append(_region(_jitter(sq, rng, 0.07), sid=f"Q{i}{j}"))
    regions.append(_region(box(-3, -3, 18, 18), thread=9, sid="PLATE"))
    report = rs.apply_regular_structure(regions, P)
    g, = report["groups"]
    assert g["kind"] == "grid" and all(m["moved"] for m in g["members"]), g


def _wheel_bgr():
    """A ship's wheel drawn large and shrunk to a few px per mm, as Bridge's
    400 px JPEG is: the trace of each handle comes out a different shape."""
    import cv2
    big = np.full((480, 480, 3), 255, np.uint8)
    c = (240, 240)
    cv2.circle(big, c, 130, (0, 0, 0), 26)
    for k in range(8):
        a = 2 * math.pi * k / 8 + 0.13
        p0 = (int(c[0] + 140 * math.cos(a)), int(c[1] + 140 * math.sin(a)))
        p1 = (int(c[0] + 185 * math.cos(a)), int(c[1] + 185 * math.sin(a)))
        cv2.line(big, p0, p1, (0, 0, 0), 14)
        cv2.circle(big, (int(c[0] + 200 * math.cos(a)), int(c[1] + 200 * math.sin(a))), 22, (0, 0, 0), -1)
    return cv2.resize(big, (150, 150), interpolation=cv2.INTER_AREA)


def test_the_pipeline_is_untouched_off_and_repeats_the_handle_on(monkeypatch):
    from digitizer_core import pipeline

    calls = []
    real = rs.apply_regular_structure
    monkeypatch.setattr(rs, "apply_regular_structure",
                        lambda *a, **k: calls.append(1) or real(*a, **k))
    kw = dict(max_colors=2, forced_class="flat", target_width_mm=60.0)
    off = pipeline.build_generation(_wheel_bgr(), PipelineConfig(**kw))
    assert calls == []
    assert not any(rs.META_KEY in r.meta for r in off.regions)
    on = pipeline.build_generation(_wheel_bgr(), PipelineConfig(regular_structure=True, **kw))
    assert calls == [1]
    wheel = [r for r in on.regions if r.meta.get(rs.META_KEY, {}).get("kind") == "self_rotation"]
    assert len(wheel) == 1 and wheel[0].meta[rs.META_KEY]["fold"] == 8
    # the outline (rim and handles: free edges) repeats; the inner edge is a
    # seam with the enclosed white and is held where it was traced
    old = Polygon(next(r for r in off.regions if r.shape_id == wheel[0].shape_id).polygon.exterior)
    new = Polygon(wheel[0].polygon.exterior)
    c = wheel[0].meta[rs.META_KEY]["centre"]
    turn = lambda g: rs.mean_dev(g, affinity.rotate(g, 45.0, origin=tuple(c)))
    assert turn(new) < 0.25 * turn(old), (turn(new), turn(old))
    # every other region is the same polygon, byte for byte
    rest_off = {r.shape_id: r.polygon.wkb for r in off.regions if r.shape_id != wheel[0].shape_id}
    rest_on = {r.shape_id: r.polygon.wkb for r in on.regions if r.shape_id != wheel[0].shape_id}
    assert rest_on == rest_off


def test_flag_is_off_by_default():
    assert PipelineConfig().regular_structure is False
