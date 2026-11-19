"""`tools/logo_trial_batch.py`: the parts a batch depends on that need no
network and no digitize -- the width rule, the keep-art-out-of-the-repo
guard, the licence gate, and the sheet's shared frame.

The fetch and the digitize themselves were checked by hand on 2026-11-19:
the tool's sheets for two batch-4 logos are byte-identical to the scratch
script's that made batch 4, at the same commit.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools import logo_trial_batch as ltb


@pytest.mark.parametrize("w, h, mm", [
    (960, 960, 80.0),     # square seal
    (960, 437, 80.0),     # 2.2:1 wordmark with a subline
    (960, 384, 80.0),     # exactly 2.5:1 is NOT "wider than"
    (960, 383, 100.0),
    (960, 172, 100.0),    # 5.6:1 wordmark
])
def test_width_rule(w, h, mm):
    assert ltb.width_for(w, h) == mm


def test_a_batch_folder_inside_the_checkout_is_refused(tmp_path):
    """The repo is public; a batch folder in it is one `git add -A` from
    publishing someone's logo and our render of it."""
    for inside in (ltb.DIGITIZER.parent, ltb.DIGITIZER / "scratch_k3", ltb.DIGITIZER.parent / "docs" / "x"):
        with pytest.raises(SystemExit, match="public"):
            ltb.outside_checkout(inside)
    assert ltb.outside_checkout(tmp_path) == tmp_path.resolve()


def _meta(short, lic, cats=""):
    return {"LicenseShortName": {"value": short}, "License": {"value": lic},
            "UsageTerms": {"value": short}, "Categories": {"value": cats}}


def test_only_a_public_domain_file_passes_the_licence_gate():
    pd = ltb.licence_of(_meta("Public domain", "pd", "With trademark|PD textlogo|SVG text logos"))
    assert pd["public_domain"]
    assert ltb.licence_text(pd) == "Public domain; License=pd; Commons tag: PD textlogo"
    # markup in the field is stripped before it is read
    assert ltb.licence_of(_meta("<span>Public domain</span>", ""))["public_domain"]
    for short, lic in (("CC BY-SA 4.0", "cc-by-sa-4.0"), ("Fair use", ""), ("", "")):
        assert not ltb.licence_of(_meta(short, lic))["public_domain"]
    assert not ltb.licence_of({})["public_domain"]


def test_art_tile_is_width_mm_at_ten_px_per_mm_on_fabric_grey():
    raw = np.zeros((50, 200, 4), np.uint8)              # fully transparent
    raw[10:40, 20:180] = (0, 0, 255, 255)               # an opaque red bar (BGRA)
    tile = ltb.art_tile(raw, 100.0)
    pad = int(ltb.PAD_MM * ltb.PPM)
    assert tile.shape == (250 + 2 * pad, 1000 + 2 * pad, 3)
    assert tuple(tile[0, 0]) == ltb.FABRIC_BGR                    # the pad
    assert tuple(tile[pad + 5, pad + 5]) == ltb.FABRIC_BGR        # transparent art
    assert tuple(tile[pad + 125, pad + 500]) == (0, 0, 255)       # the bar
    assert ltb.art_tile(np.full((50, 200), 255, np.uint8), 80.0).shape == (200 + 2 * pad, 800 + 2 * pad, 3)


def test_sheet_puts_both_tiles_on_one_frame_without_resizing_either():
    art = np.full((300, 1040, 3), 10, np.uint8)
    render = np.full((240, 1037, 3), 200, np.uint8)     # the render's own extents differ
    out = ltb.sheet(art, render, "abc1234")
    fw, fh = 1040, 300
    assert out.shape == (fh + ltb.LABEL_BAR_PX, 2 * fw + ltb.TILE_GAP_PX, 3)
    body = out[ltb.LABEL_BAR_PX:]
    left, right = body[:, :fw], body[:, fw + ltb.TILE_GAP_PX:]
    assert (left == 10).all()                                     # the art fills its frame
    assert int((right == 200).all(axis=2).sum()) == 240 * 1037    # the render, pixel for pixel
    assert tuple(right[0, 0]) == ltb.FABRIC_BGR                   # centred on fabric grey
    assert (out[:ltb.LABEL_BAR_PX, -5:] == 255).all()             # white label bar


def test_stats_line_reports_an_error_instead_of_numbers():
    ok = {"error": None, "stitches": 3203, "trims": 4, "jumps": 3, "size_mm": [100.07, 19.16],
          "blocks": 2, "design_class": "flat", "secs": 4.0, "threads": ["0015 White"],
          "warnings": []}
    line = ltb.stats_line(ok)
    assert line.startswith("3,203 stitches") and "2 blocks" in line and line.endswith("warnings: none")
    bad = dict(ok, error="ValueError: <no ink>")
    assert ltb.stats_line(bad) == '<span class="err">ERROR</span> ValueError: &lt;no ink&gt;'


def test_page_needs_the_artifact_title():
    with pytest.raises(SystemExit):
        ltb.parse_args(["page", "/tmp/x"])
    assert ltb.parse_args(["page", "/tmp/x", "--title", "K3 Batch 5 Sheets"]).title == "K3 Batch 5 Sheets"
