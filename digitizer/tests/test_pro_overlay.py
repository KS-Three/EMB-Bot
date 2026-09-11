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


def test_crop_set_renders_the_window_at_36_ppm(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "cr", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    files = overlay.crop_set(pair, reg, d / "overlay", (0.0, -2.0, 10.0, 3.0), "arm")
    assert {p.name for p in files} == {"overlay_crop_arm.png", "pro_only_crop_arm.png",
                                       "ours_only_crop_arm.png", "flicker_pro_crop_arm.png",
                                       "flicker_ours_crop_arm.png"}
    img = cv2.imread(str(d / "overlay" / "flicker_pro_crop_arm.png"))
    assert abs(img.shape[1] - 10.0 * 36) <= 2 and abs(img.shape[0] - 5.0 * 36) <= 2


def test_match_blocks_by_ciede2000():
    m = overlay.match_blocks([(200, 30, 30), (30, 30, 200)], [(205, 28, 35), (20, 200, 20), (25, 35, 190)])
    assert m == {0: [0], 1: [2]}
    assert overlay.match_blocks([(0, 0, 0)], [(255, 255, 255)]) == {0: []}


def test_by_thread_writes_one_sheet_per_pro_block(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "bt", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    files = overlay.by_thread(pair, reg, d / "overlay")
    assert [p.name for p in files] == ["0_c81e1e.png", "1_1e1ec8.png"]


def test_redigitize_writes_a_cached_arm(tmp_path, monkeypatch):
    """Uses a REAL fixture through the engine once (~5 s on the 400 px bar):
    the arm dir carries ours.dst + regions + flags.json and a second call
    does not re-run."""
    import shutil
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.export import write_dst
    art = HERE.parent / "testdata" / "logo_whitebg.png"
    d = tmp_path / "real" / "wb"
    d.mkdir(parents=True)
    _res, plan = digitize(art, PipelineConfig(target_width_mm=40.0))
    write_dst(plan, d / "ours.dst")
    shutil.copy(d / "ours.dst", d / "pro.dst")          # the pro is ours; only the arm matters here
    (d / "ours_regions.json").write_text("[]")
    (d / "ours_blocks.json").write_text("[]")
    (d / "pro_blocks.json").write_text("[]")
    shutil.copy(art, d / "art.png")
    (tmp_path / "real" / "manifest.json").write_text(json.dumps(
        [{"slug": "wb", "file": str(d / "pro.dst"), "garment_id": "left_chest"}]))
    pair = pairframe.load_pair(d)
    calls = []
    real = pairframe.digitize
    monkeypatch.setattr(pairframe, "digitize", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    arm = pairframe.redigitize(pair, {"curve_turn_deg": 0})
    assert (arm / "ours.dst").exists() and (arm / "ours_regions.json").exists()
    assert json.loads((arm / "flags.json").read_text()) == {"curve_turn_deg": 0}
    pairframe.redigitize(pair, {"curve_turn_deg": 0})
    assert len(calls) == 1
    arm_pair = pairframe.load_pair(arm)
    assert arm_pair.pro_path == pair.pro_path and arm_pair.ours_path == arm / "ours.dst"


def test_cli_writes_the_overlay_dir(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "cli", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    assert overlay.main(["--dir", str(d)]) == 0
    assert (d / "overlay" / "overlay.png").exists()
    assert overlay.main(["--dir", str(d), "--crop", "0", "-2", "10", "3", "--crop-name", "arm"]) == 0
    assert (d / "overlay" / "overlay_crop_arm.png").exists()


def test_flag_suffix_is_filename_safe():
    s = overlay._suffix_for({"forced_class": "a/b:c", "satin_angle_deg": 45.0, "x": None})
    assert s.startswith("_") and all(ch.isalnum() or ch in "._-" for ch in s)


def test_crop_name_with_a_slash_still_writes_its_files(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "sl", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    files = overlay.crop_set(pair, reg, d / "overlay", (0.0, -2.0, 10.0, 3.0), "sleeve/cuff")
    assert files and all(p.exists() for p in files)


def test_an_unwritable_image_raises(tmp_path, monkeypatch):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "uw", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg)
    monkeypatch.setattr(overlay.cv2, "imwrite", lambda *a, **k: False)
    with pytest.raises(RuntimeError, match="could not write"):
        overlay.write_overlay_set(d / "overlay", r, title="uw")


def test_against_baseline_writes_its_own_files(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "ag", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    assert overlay.main(["--dir", str(d)]) == 0
    assert overlay.main(["--dir", str(d), "--against", "baseline"]) == 0
    assert (d / "overlay" / "overlay.png").exists()
    assert (d / "overlay" / "overlay_vs-baseline.png").exists()
    assert (d / "overlay" / "registration_vs-baseline.json").exists()


def test_against_a_missing_arm_names_the_arms_that_exist(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "ma", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    with pytest.raises(SystemExit, match="deadbeef"):
        overlay.main(["--dir", str(d), "--against", "deadbeef"])


def test_against_crop_writes_its_own_files(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "ac", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    args = ["--dir", str(d), "--crop", "0", "-2", "10", "3", "--crop-name", "arm"]
    assert overlay.main(args) == 0
    assert overlay.main(args + ["--against", "baseline"]) == 0
    assert (d / "overlay" / "overlay_crop_arm.png").exists()
    assert (d / "overlay" / "overlay_crop_arm_vs-baseline.png").exists()


def test_against_by_thread_writes_its_own_sheets(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "bt2", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    assert overlay.main(["--dir", str(d), "--by-thread"]) == 0
    assert overlay.main(["--dir", str(d), "--by-thread", "--against", "baseline"]) == 0
    names = sorted(p.name for p in (d / "overlay" / "by_thread").iterdir())
    assert "0_c81e1e.png" in names and "0_c81e1e_vs-baseline.png" in names
