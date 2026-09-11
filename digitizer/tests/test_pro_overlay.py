"""The pro-overlay loop: registration, the shared frame, and the overlay set.

Spec: docs/superpowers/specs/2026-09-09-pro-overlay-loop-design.md §3-§4.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                       # proloop_synth
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parent / "tools" / "pro_parity"))

import proloop_synth as synth                        # noqa: E402
import pairframe                                     # noqa: E402
import overlay                                       # noqa: E402


def _design_blocks(offset=(0.0, 0.0)):
    """An asymmetric design: an L of two satin columns and a fill slab.

    Vertical arm lengthened 12 -> 16mm per the brief's Step 4 note: at 12mm
    the L-shape is too symmetric under a y-flip and the identity test's
    fixture registers with lower IoU than the 0.95 floor; at 16mm it
    registers under exactly one flip, at IoU ~0.995.
    """
    ox, oy = offset
    return [((200, 30, 30), [synth.satin_pass(ox + 0, oy + 0, 20, 2.0),
                             synth.satin_pass(ox + 0, oy + 0, 16, 2.0, angle_deg=90)]),
            ((30, 30, 200), [*synth.fill_passes(ox + 6, oy + 6, 10, 6)])]


def test_register_identity_under_shift_scale_and_flip(tmp_path):
    ours = _design_blocks()
    pro = [(rgb, synth.transform_passes(p, scale=0.95, flip_y=True, dx=7.3, dy=-4.1)) for rgb, p in ours]
    d = synth.make_prep_dir(tmp_path, "ident", pro, ours, [], [(0, 0, 20, 12)], 19.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    assert reg.iou >= 0.95
    assert abs(reg.scale - 0.95) < 0.02
    assert reg.flip_y is True


def test_register_reports_no_flip_when_none_is_needed(tmp_path):
    ours = _design_blocks()
    pro = [(rgb, synth.transform_passes(p, dx=3.0, dy=2.0)) for rgb, p in ours]
    d = synth.make_prep_dir(tmp_path, "noflip", pro, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    assert reg.iou >= 0.95 and reg.flip_y is False
    x, y = reg.apply_xy(0.0, 0.0)
    assert abs(x - 3.0) < 0.3 and abs(y - 2.0) < 0.3


def test_load_pair_reads_manifest_regions_and_colours(tmp_path):
    from shapely.geometry import box
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "lp", ours, ours,
                            [("S1", "satin", box(-1, -1, 21, 1))], [(0, 0, 20, 2)], 20.0,
                            garment_id="hat_front")
    pair = pairframe.load_pair(d)
    assert pair.slug == "lp" and pair.garment_id == "hat_front"
    assert pair.pro_path.name == "pro.pes" and pair.ours_path.name == "ours.dst"
    assert [r["shape_id"] for r in pair.regions] == ["S1"]
    assert pair.pro_rgb == [(200, 30, 30), (30, 30, 200)]
    assert 19.0 < pair.width_mm < 21.0


def test_read_pattern_names_a_missing_file(tmp_path):
    with pytest.raises(SystemExit, match="unreadable"):
        pairframe.file_segs(tmp_path / "nope.dst", False)


def test_read_pattern_refuses_garbage_bytes_with_a_stitch_extension(tmp_path):
    # Measured (digitizer/.venv): `bytes(range(256)) * 4` decodes to n=68
    # STITCH records -- pystitch treats it as a live, if nonsensical,
    # pattern, so it would NOT trip the zero-stitch guard. `b"\x00" * 600`
    # decodes to n=29 (0-delta stitches count), also not zero. `b"\xff" *
    # 600` measured n=0 -- 0xFF is the END/colour-change control byte, so a
    # run of them decodes to no STITCH records at all. Using that here.
    bad = tmp_path / "garbage.dst"
    bad.write_bytes(b"\xff" * 600)
    with pytest.raises(SystemExit, match="unreadable"):
        pairframe.file_segs(bad, False)
    with pytest.raises(SystemExit, match="unreadable"):
        pairframe.design_for(bad, None, None, "x")


def test_read_pattern_refuses_an_empty_file(tmp_path):
    empty = tmp_path / "empty.dst"
    empty.write_bytes(b"")
    with pytest.raises(SystemExit, match="no stitches|unreadable"):
        pairframe.file_segs(empty, False)


def test_masks_agree_with_renders_and_overlap_reads_dark(tmp_path):
    ours = _design_blocks()
    pro = [(rgb, synth.transform_passes(p, dx=2.0, dy=0.0)) for rgb, p in ours]
    d = synth.make_prep_dir(tmp_path, "ov", pro, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg, ppm=12.0)
    assert r["pro"].shape == r["ours"].shape == r["overlay"].shape
    assert r["pro_mask"].any() and r["ours_mask"].any()
    both = r["pro_mask"] & r["ours_mask"]
    assert both.sum() > 0.8 * r["pro_mask"].sum()            # registered: most thread overlaps
    assert r["overlay"][both].mean() < 120                    # multiply of two tints is dark
    assert not (r["pro_only"] & r["ours_only"]).any()
    # pro_only image: magenta where pro-only, near-white elsewhere except the grey ghost
    po = r["pro_only_img"]
    assert po.shape == r["pro"].shape


def test_write_overlay_set_writes_five_files(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "ws", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg)
    files = overlay.write_overlay_set(d / "overlay", r, title="ws 20.0 mm")
    assert sorted(p.name for p in files) == sorted([
        "overlay.png", "pro_only.png", "ours_only.png", "flicker_pro.png", "flicker_ours.png"])
    a = cv2.imread(str(d / "overlay" / "flicker_pro.png"))
    b = cv2.imread(str(d / "overlay" / "flicker_ours.png"))
    assert a.shape == b.shape


def test_restricting_one_side_to_nothing_keeps_the_shared_frame(tmp_path):
    ours = _design_blocks(offset=(40.0, 25.0))          # away from the origin, so a sentinel would show
    d = synth.make_prep_dir(tmp_path, "fr", ours, ours, [], [(40, 25, 60, 37)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    full = overlay.render_pair(pair, reg)
    empty = overlay.render_pair(pair, reg, only_ours_blocks=set())
    assert empty["frame"].bounds_units == full["frame"].bounds_units
    assert empty["ours"].shape == full["ours"].shape
    assert not empty["ours_mask"].any() and empty["pro_mask"].any()


def test_frame_for_matches_the_renderers_own_bounds(tmp_path):
    """The frame is `stitchviz._bounds` of the pinned design, in the same
    field order, so the pins land on the corners and the canvas is the
    renderer's own size — no resize anywhere."""
    from digitizer_core.stitchviz import _bounds
    ours = _design_blocks(offset=(40.0, 25.0))
    d = synth.make_prep_dir(tmp_path, "fb", ours, ours, [], [(40, 25, 60, 37)], 20.0)
    pair = pairframe.load_pair(d)
    design = pairframe.design_for(pair.pro_path, None, pair.pro_rgb, "p")
    frame = pairframe.frame_for([design], 12.0)
    assert frame.bounds_units == _bounds(design["stitches"])
    x0, x1, y0, y1 = frame.bounds_units
    assert x0 < x1 and y0 < y1
    img = overlay.render_side(design, frame)
    w, h = frame.size
    assert img.shape[:2] == (h, w)
    # to_px of the design's own min-x/max-y file-frame point lands `pad` inside the canvas
    px, py = frame.to_px(x0 / 10.0, -y1 / 10.0)
    assert abs(px - frame.pad_mm * frame.ppm) < 1.0 and abs(py - frame.pad_mm * frame.ppm) < 1.0


def test_fit_to_frame_clips_a_crossing_segment_and_clamps_travel():
    design = {"stitches": [
        {"x": -500, "y": -500, "type": "jump"},
        {"x": 0, "y": 0, "type": "stitch"},
        {"x": 100, "y": 0, "type": "stitch"},
        {"x": 0, "y": 0, "type": "end"},
    ], "colors": [{"r": 0, "g": 0, "b": 0}]}
    frame = pairframe.Frame(20, 60, -10, 10, 0.0, 12.0)
    got = [(s["x"], s["y"], s["type"]) for s in overlay._fit_to_frame(design, frame)["stitches"]]
    assert got == [(20, -10, "jump"), (20, 0, "jump"), (20, 0, "stitch"), (60, 0, "stitch"), (0, 0, "end")]


def test_fit_to_frame_leaves_an_inside_design_alone():
    design = {"stitches": [
        {"x": 25, "y": 0, "type": "stitch"},
        {"x": 30, "y": 5, "type": "stitch"},
        {"x": 40, "y": 5, "type": "trim"},
        {"x": 45, "y": -5, "type": "stitch"},
    ], "colors": [{"r": 0, "g": 0, "b": 0}]}
    frame = pairframe.Frame(20, 60, -10, 10, 0.0, 12.0)
    assert overlay._fit_to_frame(design, frame)["stitches"] == design["stitches"]


def test_travel_outside_the_sewn_area_does_not_grow_the_canvas(tmp_path):
    ours = _design_blocks(offset=(40.0, 25.0))      # the DST lead-in brings jumps back toward the origin
    d = synth.make_prep_dir(tmp_path, "tr", ours, ours, [], [(40, 25, 60, 37)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg)
    w, h = r["frame"].size
    assert r["pro"].shape[:2] == r["ours"].shape[:2] == (h, w)
    both = r["pro_mask"] & r["ours_mask"]
    assert both.sum() > 0.8 * r["pro_mask"].sum()


def test_a_crop_window_renders_at_exactly_its_own_size(tmp_path):
    ours = _design_blocks(offset=(40.0, 25.0))
    d = synth.make_prep_dir(tmp_path, "cw", ours, ours, [], [(40, 25, 60, 37)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg, ppm=36.0, crop_mm=(40.0, 24.0, 50.0, 30.0))
    assert r["pro"].shape[:2] == r["ours"].shape[:2] == (6 * 36, 10 * 36)
    assert r["pro_mask"].any() and r["ours_mask"].any()
