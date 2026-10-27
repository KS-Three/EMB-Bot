"""The small lettering on a white panel (`cfg.silhouette_underfill_panels`, built OFF 2026-10-25).

The pro's MFab: one black tatami under the silhouette, the white keyline as
satin loops round each M-FAB letter on it, and the small second line (AND
WELDING, LLC) as black satin sewn AFTER the white on a white panel CLOSED
under them (white under them 1.000, black under them 0.12-0.18). The
under-fill alone merged those letters into the black.

ON (with `silhouette_underfill`, `sew_enclosed_white` and
`border_from_outline`): a RIDER -- a text-tagged shape in the host's thread,
in a hole of a sewn white field, whose word is mostly not the art outline's
bodies -- is never merged, sews in its own layer right after the field's,
and the field fills its rider holes as one closed panel the black gives up.
OFF, byte-identical (md5 pinned on origin/main cdb96d63, the same pins
reproduced on this branch with the flag off).
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, silhouette_underfill as su, stitches
from tests.conftest import FLIP_2026_10_23, FLIP_2026_10_26, RECIPE_2026_10_27
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence

from .test_silhouette_underfill import becker, mfab

FABRIC = fabric_for_garment("hat_front")

B1, B2 = box(8, 8, 30, 26), box(34, 8, 56, 26)                       # two wide bodies
S = [box(62 + 4.5 * i, 22, 65 + 4.5 * i, 28) for i in range(3)]     # three small letters
FIELD = box(4, 4, 76, 36)
#: the art outline pass's read: the field is the outline of the two bodies
OUTLINES = {"Sfield": [("Sb1", Polygon(B1.exterior), 2.2), ("Sb2", Polygon(B2.exterior), 2.2)]}
ON = dict(silhouette_underfill=True, sew_enclosed_white=True)

#: captured on origin/main cdb96d63 (main's `su.apply`, no riders), and
#: reproduced on this branch with the flag off
OFF_MD5 = {"panel_off": "4743a430dd2677f2724593708c4d9f2a",
           "panel_underfill": "52bdd7bf2159110c6821b9fcfa3aaf92",
           "mfab_underfill": "a429f57a0a79155e7d63ffea56fdabc6",
           "becker_underfill": "cd652df0ebca32d933202309b29e2bc4"}


def _reg(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(4000 + thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _holed(outer, *holes):
    return Polygon(outer.exterior.coords, [list(h.exterior.coords)[::-1] for h in holes])


def panel():
    """A black ring round a white field (MFab's keyline) that holds two wide
    bodies and, in its wide right part, three small black letters."""
    return [_reg("Sfield", _holed(FIELD, B1, B2, *S), 1, 0, sew_enclosed_white="field"),
            _reg("Sring", _holed(box(-6, -6, 86, 46), FIELD), 0, 1),
            _reg("Sb1", B1, 0, 1, text_candidate=True, text_cluster_id="TCbig"),
            _reg("Sb2", B2, 0, 1, text_candidate=True, text_cluster_id="TCbig"),
            *[_reg(f"Ss{i}", s, 0, 1, text_candidate=True, text_cluster_id="TCsmall")
              for i, s in enumerate(S)]]


def _md5(blocks) -> str:
    rows = [[b.thread_index, r.shape_id, r.kind, bool(r.jump), bool(r.trim),
             [[round(x, 4), round(y, 4)] for x, y in r.points]] for b in blocks for r in b.runs]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _sew(regs, outlines=None, **kw):
    """`plan_stitches`' order: the under-fill (`apply_cfg`), stage 5, stage 7."""
    # the OFF md5s predate the 2026-10-23, 2026-10-26 and 2026-10-27 flips (conftest): pinned off,
    # so "without the white sewn" below means it (an arm that wants it sets it)
    cfg = PipelineConfig(underlay=False, **{**FLIP_2026_10_23, **FLIP_2026_10_26, **RECIPE_2026_10_27, **kw})
    report = None
    if cfg.silhouette_underfill:
        regs, report, outlines = su.apply_cfg(regs, (), cfg, outlines)
    planned, _ = resolve_overlaps(regs, FABRIC, cfg)
    blocks, _ = sequence(planned, FABRIC, cfg, art_outlines=outlines)
    return regs, report, planned, blocks


@lru_cache(maxsize=None)
def _panel_md5(**kw) -> str:
    return _md5(_sew(panel(), OUTLINES, **kw)[3])


def test_flag_default_is_on():
    # ON since the recipe went to every job (Kent 2026-10-27, "Every job (Recommended)")
    assert PipelineConfig().silhouette_underfill_panels is True


def test_off_is_byte_identical_to_main():
    assert _panel_md5() == OFF_MD5["panel_off"]
    assert _panel_md5(**ON) == OFF_MD5["panel_underfill"]
    assert _md5(_sew(mfab(), silhouette_underfill=True)[3]) == OFF_MD5["mfab_underfill"]
    assert _md5(_sew(becker(), silhouette_underfill=True)[3]) == OFF_MD5["becker_underfill"]


def test_inert_without_the_white_sewn_or_the_underfill():
    assert (_panel_md5(silhouette_underfill_panels=True, silhouette_underfill=True)
            == _panel_md5(silhouette_underfill=True))
    assert (_panel_md5(silhouette_underfill_panels=True, sew_enclosed_white=True)
            == _panel_md5(sew_enclosed_white=True))
    assert _panel_md5(silhouette_underfill_panels=True) == OFF_MD5["panel_off"]


def test_on_the_riders_are_not_merged_and_sew_after_the_white():
    regs, report, _planned, blocks = _sew(panel(), OUTLINES, silhouette_underfill_panels=True, **ON)
    ids = {r.shape_id: r for r in regs}
    assert report[0]["merged"] == ["Sb1", "Sb2"]
    assert report[1]["riders"] == ["Ss0", "Ss1", "Ss2"]
    host, field = ids["Sring"].meta["layer"], ids["Sfield"].meta["layer"]
    riders = {ids[f"Ss{i}"].meta["layer"] for i in range(3)}
    assert riders == {field + 1} and host < field
    assert all(ids[f"Ss{i}"].meta[su.RIDER_OF_KEY] == "Sfield" for i in range(3))
    assert len(ids["Sfield"].meta[su.RIDER_HOLES_KEY]) == 3
    # black, white, black
    order = [b.thread_index for b in blocks if any(r.shape_id in ids for r in b.runs)]
    assert order[:3] == [0, 1, 0]
    assert {r.shape_id for b in blocks[2:] for r in b.runs} >= {"Ss0", "Ss1", "Ss2"}


def test_on_the_black_gives_up_the_panel_and_the_white_fills_it():
    regs, _report, _planned, blocks = _sew(panel(), OUTLINES, silhouette_underfill_panels=True, **ON)
    host = next(r for r in regs if r.shape_id == "Sring")
    outline = host.meta[su.UNDERFILL_KEY]
    for s in S:
        assert outline.intersection(s).area < 1e-6          # no black under a rider
    # ... but it still fills under the bodies and their loops
    assert outline.intersection(B1).area >= 0.99 * B1.area
    runs = [r for b in blocks for r in b.runs if r.shape_id == "Sfield"]
    fill = unary_union([LineString(r.points).buffer(0.2) for r in runs
                        if r.kind == stitches.FILL and len(r.points) > 1])
    satin = unary_union([LineString(r.points).buffer(0.2) for r in runs
                         if r.kind == stitches.SATIN and len(r.points) > 1])
    for s in S:
        assert fill.intersection(s).area >= 0.95 * s.area   # white closed under the rider
        assert satin.intersection(s.buffer(-0.3)).area < 1e-6
    # loops only round the bodies
    off = _sew(panel(), OUTLINES, **ON)[3]
    loops = lambda bs: sum(1 for b in bs for r in b.runs  # noqa: E731
                           if r.shape_id == "Sfield" and r.kind == stitches.SATIN)
    assert loops(blocks) < loops(off)
    assert satin.intersection(B1.buffer(2.0)).area > 0


def test_a_word_rides_by_majority():
    # WELDING's I: a body of the outline, but its word is mostly not -- it rides
    outlines = {"Sfield": OUTLINES["Sfield"] + [("Ss1", Polygon(S[1].exterior), 2.2)]}
    assert su.find_riders(panel(), (), outlines) == ["Ss0", "Ss1", "Ss2"]
    # a letter whose word is mostly bodies does not: Ss0 joins the bodies' word
    regs = panel()
    regs[4] = _reg("Ss0", S[0], 0, 1, text_candidate=True, text_cluster_id="TCbig")
    assert su.find_riders(regs, (), OUTLINES) == ["Ss1", "Ss2"]
    # a rider is no outline's body after the call
    cfg = PipelineConfig(silhouette_underfill_panels=True, **ON)
    _regs, _rep, out = su.apply_cfg(panel(), (), cfg, outlines)
    assert [b[0] for b in out["Sfield"]] == ["Sb1", "Sb2"]
