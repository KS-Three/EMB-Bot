"""A monoline script stroke sews satin, never fill (`cfg.monoline_script_satin`,
built OFF 2026-10-24, L7).

Tires' joined "ires" (919 mm², ribbon 4.5 mm, dt_cv 0.149, elongation 42.4)
is refused by the satin classifier on `dt_p90_cap` alone and sews a 45-degree
tatami; the pro sews it as satin columns, 8.9 % of his crosses over 5 mm.
ON, such a shape gets the lettering split's ceiling. The fixtures: MONO, a
4.4 mm pen line with eight 6.2 mm ball joins (dt_p90 5.38 > 5.0, dt_cv 0.09,
elongation 25), and THICK_THIN, the same path drawn with a calligraphic
2.4-5.6 mm width (dt_cv 0.36) -- refused on the same gate, and like Golden
Tee's and MFab's shapes the rule leaves it to the fill. OFF byte-identical
(md5 pinned on main's engine, dd7caef6).
"""
from __future__ import annotations

import hashlib
import math

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.machine import satin_ceiling_mm
from digitizer_core.monoline import monoline_stroke
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_satin import classify_ribbon
from digitizer_core.stage7_sequence import _sews_satin, sequence

PATH = LineString([(x * 0.5, 6 * math.sin(x * 0.5 / 8)) for x in range(240)])
MONO = unary_union([PATH.buffer(2.2)] + [PATH.interpolate(i / 9, normalized=True).buffer(3.1)
                                         for i in range(1, 9)])
THICK_THIN = unary_union([Point(PATH.interpolate(t / 400, normalized=True))
                          .buffer(1.2 + 1.6 * abs(math.sin(t / 400 * math.pi * 3)))
                          for t in range(401)])
#: the OFF md5s of `_runs(MONO)` / `_runs(THICK_THIN)`, captured on main (dd7caef6)
OFF_MD5 = {"mono": "df33ff6ec369c35717949fbf99af31b9", "thick_thin": "392b67cfa90cc6735a283b7cbfe6601e"}


def _region(poly) -> Region:
    return Region(shape_id="Sword", polygon=poly, thread_index=0, thread_number="0020",
                  area_mm2=poly.area, source="test", meta={"layer": 0})


def _runs(poly, **cfg_kw):
    cfg = PipelineConfig(underlay=False, **cfg_kw)
    reg = _region(poly)
    blocks, _ = sequence([PlannedRegion(region=reg, polygon=poly, sew_index=0)],
                         fabric_for_garment("hat_front"), cfg)
    return [r for b in blocks for r in b.runs if r.shape_id == "Sword"]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _kinds(runs) -> set[str]:
    return {str(r.kind) for r in runs if r.points}


def test_default_off():
    assert PipelineConfig().monoline_script_satin is False


def test_fixtures_sit_where_the_rule_reads():
    """Both refused on `dt_p90_cap` alone; only MONO is a monoline."""
    for poly in (MONO, THICK_THIN):
        v = classify_ribbon(poly, 5.0)
        assert v.reason == "dt_p90_cap"
        assert v.metrics["ribbon_w"] < 5.0
    assert classify_ribbon(MONO, 5.0).metrics["dt_cv"] < 0.25 < classify_ribbon(THICK_THIN, 5.0).metrics["dt_cv"]
    cfg = PipelineConfig(monoline_script_satin=True)
    assert monoline_stroke(_region(MONO), cfg, 5.0)
    assert not monoline_stroke(_region(THICK_THIN), cfg, 5.0)


def test_off_is_byte_identical():
    assert _md5(_runs(MONO)) == OFF_MD5["mono"]
    assert _md5(_runs(THICK_THIN)) == OFF_MD5["thick_thin"]
    assert "fill" in _kinds(_runs(MONO))


def test_on_sews_the_monoline_satin():
    on = _runs(MONO, monoline_script_satin=True)
    assert "satin" in _kinds(on)
    assert "fill" not in _kinds(on)


def test_on_leaves_a_thick_thin_stroke_to_the_fill():
    assert _md5(_runs(THICK_THIN, monoline_script_satin=True)) == OFF_MD5["thick_thin"]


def test_prediction_agrees_with_the_emitter():
    """`_sews_satin` (borders-last, seam ownership) reads the same ceiling."""
    for flag in (False, True):
        cfg = PipelineConfig(underlay=False, monoline_script_satin=flag)
        predicted = _sews_satin(_region(MONO), cfg, satin_ceiling_mm(cfg), "flat")
        assert predicted is flag
        assert ("satin" in _kinds(_runs(MONO, monoline_script_satin=flag))) is flag
