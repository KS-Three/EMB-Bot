"""`cfg.resnap_hairline_never_lightens` (built OFF 2026-11-11): a drawn line
keeps its ink colour through stage 4's thread re-check.

The defect (Kent on `C_low_poly` pin 2, `docs/border-colour-change-2026-11-11.md`):
`revalidate_threads` re-matches a shape to the median of the pixels its final
polygon covers. A hairline's footprint is mostly its own anti-alias halo and
the pale face beside it, so a black outline reads grey and is re-snapped to a
grey spool, and the outline changes colour mid-run at no seam of the art.

Pinned here, on a hand-built `Prep` (no corpus file needed, the real rows are
gitignored):

1. OFF (the default) is the engine as it was: the hairline IS re-snapped.
2. ON, a hairline the re-check would LIGHTEN keeps its thread.
3. ON, a hairline the re-check would DARKEN still re-snaps.
4. ON, a body wider than a line re-snaps as before.
"""
from types import SimpleNamespace

import numpy as np
from shapely.geometry import box

from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage4_vectorize import revalidate_threads
from digitizer_core.threads import chart_for, rgb_to_lab
from digitizer_core import bean_rule

PX_PER_MM = 5.0
W, H = 400, 240


def _idx(chart, rgb):
    return chart.nearest_index(rgb_to_lab(np.array([rgb], dtype=np.float64))[0])


def _prep(rows_rgb):
    """A flat image; `rows_rgb` paints (y0, y1, rgb) bands across the full width."""
    rgb = np.full((H, W, 3), 235, np.uint8)
    for y0, y1, c in rows_rgb:
        rgb[y0:y1, :, :] = c
    return SimpleNamespace(
        rgb=rgb, bg_mask=np.zeros((H, W), bool), px_per_mm=PX_PER_MM,
        art_bbox=(0, 0, W, H),
    )


def _region(chart, sid, y_mm, h_mm, rgb):
    """A 40 mm long, `h_mm` tall band centred at `y_mm` (mm from the design
    centre), wearing the spool nearest `rgb`."""
    t = _idx(chart, rgb)
    poly = box(-20.0, y_mm - h_mm / 2, 20.0, y_mm + h_mm / 2)
    return Region(shape_id=sid, polygon=poly, thread_index=t,
                  thread_number=chart[t].number, area_mm2=poly.area)


def _run(flag: bool, regions, prep):
    cfg = PipelineConfig(target_width_mm=80.0, resnap_hairline_never_lightens=flag)
    revalidate_threads(regions, prep, cfg, design_class="flat")
    return regions


def _cfg_chart():
    return chart_for(PipelineConfig(target_width_mm=80.0))


def test_the_flag_defaults_off():
    assert PipelineConfig().resnap_hairline_never_lightens is False


def test_a_hairline_is_a_line_and_a_body_is_not():
    chart = _cfg_chart()
    assert bean_rule.min_dim_mm(_region(chart, "a", 0, 1.0, (0, 0, 0)).polygon) <= bean_rule.LINE_MAX_MM
    assert bean_rule.min_dim_mm(_region(chart, "b", 0, 4.0, (0, 0, 0)).polygon) > bean_rule.LINE_MAX_MM


def _hairline_case():
    """A 1.0 mm black line (5 px at 5 px/mm) whose pixels, once the grader's
    3 x 3 erosion has eaten its edge rows, are pale: the median reads grey."""
    chart = _cfg_chart()
    # image rows 118..123 hold the line's footprint (y_mm 0 -> row 120, +-2.5 px)
    prep = _prep([(117, 124, (225, 225, 225))])
    prep.rgb[120, :, :] = 0          # the ink itself: one row in the middle
    return chart, prep


def test_off_the_hairline_is_resnapped_to_the_light_spool():
    chart, prep = _hairline_case()
    black = _idx(chart, (0, 0, 0))
    (r,) = _run(False, [_region(chart, "H", 0.0, 1.0, (0, 0, 0))], prep)
    assert r.thread_index != black
    assert chart.lab[r.thread_index][0] > chart.lab[black][0]
    assert "thread_resnapped_de00" in r.meta


def test_on_the_hairline_keeps_its_ink():
    chart, prep = _hairline_case()
    black = _idx(chart, (0, 0, 0))
    (r,) = _run(True, [_region(chart, "H", 0.0, 1.0, (0, 0, 0))], prep)
    assert r.thread_index == black
    assert "thread_resnapped_de00" not in r.meta


def test_on_a_hairline_that_would_darken_still_resnaps():
    """The rule is `never lightens`: a light line over a dark face is moved."""
    chart = _cfg_chart()
    prep = _prep([(117, 124, (20, 20, 20))])
    prep.rgb[120, :, :] = 255
    white = _idx(chart, (255, 255, 255))
    (r,) = _run(True, [_region(chart, "H", 0.0, 1.0, (255, 255, 255))], prep)
    assert r.thread_index != white
    assert chart.lab[r.thread_index][0] < chart.lab[white][0]


def test_on_a_body_wider_than_a_line_resnaps_as_before():
    chart = _cfg_chart()
    black = _idx(chart, (0, 0, 0))
    prep = _prep([(108, 132, (225, 225, 225))])     # a 4.8 mm band of pale pixels
    off = _run(False, [_region(chart, "B", 0.0, 4.0, (0, 0, 0))], prep)
    on = _run(True, [_region(chart, "B", 0.0, 4.0, (0, 0, 0))], prep)
    assert off[0].thread_index != black
    assert on[0].thread_index == off[0].thread_index
