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
