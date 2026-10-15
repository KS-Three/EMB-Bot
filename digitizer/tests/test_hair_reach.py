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
    crop = full[int(h * 0.12):int(h * 0.47), int(w * 0.25):int(w * 0.55)]
    f = tmp_path / "hair_fine_crop.png"
    cv2.imwrite(str(f), crop)
    monkeypatch.setitem(H.IMAGES, "hair_fine_crop", f)
    row = H.census("hair_fine_crop", 24.0, 8.0, False)
    assert row["design_class"] == "gradient", row
    assert row["reached"] and row["strands"] >= 3, row
    assert L.LINE_CLASSES == tuple(L.PHOTO_CLASSES), "the tool's patch leaked"
    # the probe on the same crop: a row that says so, core restored
    probe = H.census("hair_fine_crop", 24.0, 8.0, False, probe="side")
    assert probe["probe"] == "side" and probe["side_scale"] == round(24.0 / 127.0, 4)
    assert row["probe"] == "main" and row["side_scale"] == 1.0
    assert L.ridge_contrast.__name__ == "ridge_contrast", "the probe's wrapper leaked"


# ---------------------------------------------------------------- size probe
# (2026-10-15) The ridge test's side sample read in SOURCE pixels. Measure
# only: the probe is a wrapper the tool puts round `L.ridge_contrast`; no
# constant in core moves.

def test_source_scale_is_the_ratio_of_design_widths():
    # a source pixel is design-width / source-width mm: 250 mm is 250/127 times
    # wider than at the 127 mm reference, whatever the file's own width
    assert H.source_scale("owl_kent", 127.0) == pytest.approx(1.0)
    assert H.source_scale("owl_kent", 250.0) == pytest.approx(250.0 / 127.0)
    assert H.source_scale("owl_kent", 90.0, ref_width=180.0) == pytest.approx(0.5)


def _recorder(monkeypatch):
    seen = []

    def rec(pts, light, sp, *, polarity, core_mm, side0_mm, side1_mm, step_mm):
        seen.append(dict(core=core_mm, side0=side0_mm, side1=side1_mm, step=step_mm))
        return 99.0
    monkeypatch.setattr(L, "ridge_contrast", rec)
    return seen, rec


def _call():
    return L.ridge_contrast([(0, 0), (1, 0)], None, None, polarity="dark", core_mm=0.1,
                            side0_mm=0.25, side1_mm=0.375, step_mm=0.5)


def test_ridge_probe_scales_the_side_offset_and_reach_not_the_step(monkeypatch):
    seen, rec = _recorder(monkeypatch)
    with H.ridge_probe("side", 2.0):
        assert L.ridge_contrast is not rec
        assert _call() == 99.0
    assert seen[0] == dict(core=0.1, side0=0.5, side1=0.5 + 0.25, step=0.5)
    assert L.ridge_contrast is rec               # restored


def test_ridge_probe_side_core_scales_the_core_too(monkeypatch):
    seen, _rec = _recorder(monkeypatch)
    with H.ridge_probe("side_core", 2.0):
        _call()
    assert seen[0]["core"] == pytest.approx(0.2) and seen[0]["side0"] == pytest.approx(0.5)


def test_ridge_probe_main_is_no_wrapper_and_identity_at_scale_one(monkeypatch):
    seen, rec = _recorder(monkeypatch)
    with H.ridge_probe("main", 2.0):
        assert L.ridge_contrast is rec           # untouched
    with H.ridge_probe("side", 1.0):
        _call()
    assert seen[0] == dict(core=0.1, side0=0.25, side1=0.375, step=0.5)


def test_ridge_probe_restores_after_an_error_and_refuses_an_unknown_mode():
    before = L.ridge_contrast
    with pytest.raises(RuntimeError):
        with H.ridge_probe("side", 2.0):
            raise RuntimeError("boom")
    assert L.ridge_contrast is before
    with pytest.raises(ValueError):
        with H.ridge_probe("nope", 1.0):
            pass


class _Raster:
    """Work raster at 8 px/mm, mm 0 at px 0."""
    px_per_mm = 8.0

    @staticmethod
    def to_px(x, y):
        return x * 8.0, y * 8.0


def test_a_bristle_wider_in_mm_fails_the_main_reading_and_passes_the_probe():
    """The mechanism, on a drawn line. A light bristle 9 work px wide (its
    width at 2x the design size) with the side window at 2.0-3.0 px: main
    samples the bristle itself and reads 0; the probe, offset x2 to 4.0-5.0
    px, reaches the ground beyond its edge and reads the full contrast. Same
    core, same function, only the unit of the offset."""
    light = np.full((200, 200), 20.0, np.float32)
    light[96:105, :] = 80.0                       # rows 96..104: +-4 px about row 100
    pts = [(5.0, 12.5), (20.0, 12.5)]             # px y = 100
    kw = dict(polarity="light", core_mm=0.05, side0_mm=0.25, side1_mm=0.375, step_mm=0.5)
    main = L.ridge_contrast(pts, light, _Raster, **kw)
    with H.ridge_probe("side", 2.0):
        probe = L.ridge_contrast(pts, light, _Raster, **kw)
    assert main < 12.0 <= probe, (main, probe)
    assert probe == pytest.approx(60.0)


def test_size_table_and_verdict_render_every_cell():
    def row(w, probe, bristle, st=False):
        return {"image": "owl_kent", "width_mm": w, "work_px_per_mm": 8.0, "strand_test": st,
                "probe": probe, "design_class": "gradient", "reached": True, "side_scale": 1.0,
                "found": {"dark": 3, "light": 4}, "ridge_lines": 9, "strands": 5, "light": 2,
                "zones": {"bristles": {"n": bristle, "mm": 3.0}, "breast": {"n": 2, "mm": 5.0},
                          "elsewhere": {"n": 1, "mm": 1.0}}}
    rows = [row(127.0, "main", 4), row(250.0, "main", 1), row(250.0, "side", 4),
            {"image": "x", "width_mm": 1.0, "strand_test": False, "probe": "main",
             "reached": False}]
    t = H.size_table(rows).splitlines()
    assert len(t) == 2 + 3 and "| 250 | off | side |" in t[4]
    v = H.verdict(rows)
    assert "main: 127 mm = 4 / 250 mm = 1" in v and "side: 250 mm = 4" in v
