"""`tools/hair_reach.py`: the hair reach census (2026-10-13). Measure only.

The census itself takes minutes per image and lives in the PR body. What is
pinned here is what makes its numbers mean what they say:

- the one thing the tool forces, `LINE_CLASSES`, is widened for the length of
  a `with` block and restored after it, on error too, so no plan outside the
  tool ever sees `gradient` as a line-route lane (core is not edited);
- the Studio route's config and each arm's flags are what the PR says;
- the zone rule is #882's box, first match wins, read as a fraction of the
  raster the route read;
- the line route, forced onto the drawn `hair_fine` fixture's lane, reaches
  it and finds strands, while without the patch `applies()` is False for it
  (the claim "this flag does not fire on the Studio route today").
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import stage6_hairline_lines as L  # noqa: E402
from tools import hair_reach as H  # noqa: E402


def test_lines_on_widens_and_restores():
    before = L.LINE_CLASSES
    assert "gradient" not in before
    with H.lines_on() as inside:
        assert "gradient" in inside and "gradient" in L.LINE_CLASSES
        assert set(before) <= set(L.LINE_CLASSES)
        assert L.applies(SimpleNamespace(hairline=True, hairline_from_lines=True), "gradient")
    assert L.LINE_CLASSES == before
    assert not L.applies(SimpleNamespace(hairline=True, hairline_from_lines=True), "gradient")


def test_lines_on_restores_after_an_error():
    before = L.LINE_CLASSES
    with pytest.raises(RuntimeError):
        with H.lines_on():
            raise RuntimeError("boom")
    assert L.LINE_CLASSES == before


def test_arm_flags_and_the_studio_route():
    off, region = H.cfg_for(arm="off"), H.cfg_for(arm="region")
    lines, st = H.cfg_for(arm="lines"), H.cfg_for(127.0, 16.0, "lines_st", 60)
    for c in (off, region, lines, st):
        assert c.detect_photographic is True and c.faces_route_flat is True
        assert c.forced_class is None            # stage 0 picks the lane
    assert (off.hairline, off.hairline_from_lines) == (False, False)
    assert (region.hairline, region.hairline_from_lines) == (True, False)
    assert (lines.hairline, lines.hairline_from_lines,
            lines.hairline_lines_strand_test) == (True, True, False)
    assert (st.hairline_lines_strand_test, st.work_px_per_mm, st.thread_wt) == (True, 16.0, 60)
    assert H.cfg_for(250.0).target_width_mm == 250.0


class _SP:
    """A SourcePixels stand-in: 100 x 200 px raster, 2 px per mm, mm 0 at (0, 0)."""
    rgb = np.zeros((200, 100, 3), np.uint8)

    @staticmethod
    def to_px(x, y):
        return x * 2.0, y * 2.0


def test_zone_rule_is_882s_box_first_match_wins():
    # bristles (0.36, 0.18, 0.68, 0.48); eyes (0.25, 0.12, 0.75, 0.25) overlaps it
    assert H.zone_of("owl_kent", 0.5, 0.3) == "bristles"
    assert H.zone_of("owl_kent", 0.5, 0.15) == "eyes"
    assert H.zone_of("owl_kent", 0.5, 0.7) == "breast"
    assert H.zone_of("owl_kent", 0.05, 0.3) == "elsewhere"
    assert H.zone_of("hair_fine", 0.5, 0.5) == "elsewhere"       # no zones: all elsewhere


def test_zone_counts_read_the_centroid_as_a_fraction_of_the_raster():
    outside = {"pts": [(40.0, 40.0), (44.0, 40.0)], "length_mm": 4.0}  # px (84, 80): .84, .4
    breast = {"pts": [(30.0, 60.0), (34.0, 60.0)], "length_mm": 4.0}   # px (64, 120): .64, .6
    real = {"pts": [(24.0, 30.0), (26.0, 30.0)], "length_mm": 2.0}     # px (50, 60): .5, .3
    z = H.zone_counts("owl_kent", [outside, breast, real], _SP)
    assert z["bristles"] == {"n": 1, "mm": 2.0}
    assert z["breast"]["n"] == 1 and z["elsewhere"]["n"] == 1


def test_tables_render_every_row():
    cen = [{"image": "owl_kent", "width_mm": 127.0, "work_px_per_mm": 8.0, "strand_test": False,
            "design_class": "gradient", "reached": True, "px_per_mm": 8.0,
            "found": {"dark": 3, "light": 4}, "ridge_lines": 5, "strands": 4, "dropped": 1,
            "light": 2, "zones": {"bristles": {"n": 1, "mm": 3.0}, "elsewhere": {"n": 3, "mm": 9.0}}},
           {"image": "x", "width_mm": 80.0, "work_px_per_mm": 8.0, "strand_test": True,
            "design_class": "flat", "reached": False}]
    t = H.census_table(cen).splitlines()
    assert len(t) == 4 and "| 7 |" in t[2] and t[3].count("-") > 5
    run = [{"image": "owl_kent", "width_mm": 127.0, "work_px_per_mm": 8.0, "arm": "lines",
            "stitches": 1234, "trims": 5, "color_changes": 2, "thread_m": 1.5, "bare_mm2": 9.0,
            "bare_new_mm2": 0.5, "hairline": {"strands": 4, "dropped": 1},
            "zones": {"bristles": {"n": 2, "mm": 1.0}}}]
    r = H.run_table(run).splitlines()
    assert len(r) == 3 and "1,234" in r[2] and "| 0.5 |" in r[2]


def test_the_line_route_reaches_the_drawn_hair_lane_only_when_forced(tmp_path, monkeypatch):
    """hair_fine classifies `gradient` (#882). Without the tool's patch the
    line route does not apply there; with it, the route reads the raster and
    finds strands. A crop keeps this to seconds."""
    import cv2
    full = cv2.imread(str(H.IMAGES["hair_fine"]), cv2.IMREAD_UNCHANGED)
    h, w = full.shape[:2]
    crop = full[int(h * 0.1):int(h * 0.6), int(w * 0.2):int(w * 0.8)]
    f = tmp_path / "hair_fine_crop.png"
    cv2.imwrite(str(f), crop)
    monkeypatch.setitem(H.IMAGES, "hair_fine_crop", f)
    row = H.census("hair_fine_crop", 40.0, 8.0, False)
    assert row["design_class"] == "gradient", row
    assert row["reached"] and row["strands"] >= 3, row
    assert L.LINE_CLASSES == tuple(L.PHOTO_CLASSES), "the tool's patch leaked"
