"""`cfg.white_keyline_art_recipe` (built OFF 2026-10-26): white-keyline art turns
its own recipe on.

Kent, 2026-10-26: "Gate to MFab art first (Recommended)". The recipe
(`white_keyline_art.RECIPE`) as a default for all art damaged four of 20 other
paired jobs, so it turns on only where a dark host holds a white field that
outlines letters. This pins the read (each of its three parts refuses alone),
that any other art leaves the config the very same object, that the gate's plan
is the explicit recipe's, and the verdict on real art: MFab LC reads, Becker
(white letter faces in a black band) does not.

Kent, 2026-10-27: "Every job (Recommended)" -- the recipe's switches are plain
defaults since, so the gate changes a config only where a caller turned one off.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, white_keyline_art as wka
from digitizer_core.regions import Region

from .conftest import TESTDATA

B1, B2 = box(10, 10, 20, 30), box(22, 10, 32, 30)          # two letters, 2 mm apart
FIELD = unary_union([B1.buffer(1.5, join_style=2), B2.buffer(1.5, join_style=2)]).difference(
    unary_union([B1, B2]))                                     # a 1.5 mm keyline round both
RING = Polygon(FIELD.exterior).buffer(3.0, join_style=2).difference(Polygon(FIELD.exterior))


def _reg(sid, poly, thread, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(4000 + thread),
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def keyline_art(field_meta=None, letter_meta=None, ring=True):
    regs = [_reg("Sfield", FIELD, 1, **({"enclosed_background": True} if field_meta is None else field_meta)),
            _reg("Sb1", B1, 0, **({"text_cluster_id": "TC1"} if letter_meta is None else letter_meta)),
            _reg("Sb2", B2, 0, **({"text_cluster_id": "TC1"} if letter_meta is None else letter_meta))]
    if ring:
        regs.append(_reg("Sring", RING, 0))
    return regs


ON = PipelineConfig(white_keyline_art_recipe=True)


def test_on_by_default_kent_2026_10_26():
    # "Gate to MFab art first (Recommended)": the recipe turns on by default
    # only on white-keyline art
    assert PipelineConfig().white_keyline_art_recipe is True


def test_the_recipe_is_the_default_on_every_job_kent_2026_10_27():
    # "Every job (Recommended)": every switch of the recipe ON by default, so
    # the gate's apply on any art is the config the caller already had
    from digitizer_core import fragment_absorb
    cfg = PipelineConfig()
    assert all(getattr(cfg, k) is True for k in wka.RECIPE)
    assert fragment_absorb.enabled(cfg)
    assert set(wka.RECIPE_EXTRA) == {fragment_absorb.KEY}
    got = wka.apply(cfg, True)
    assert all(getattr(got, k) == getattr(cfg, k) for k in wka.RECIPE)
    # an explicit OFF still holds on art the gate does not read (the Studio's
    # unticked "sew the white inside" sends sew_enclosed_white=False)
    off = PipelineConfig(sew_enclosed_white=False, extra={fragment_absorb.KEY: False})
    assert wka.apply(off, False) is off and not fragment_absorb.enabled(off)


def test_the_fixture_is_one_keyline_round_two_letters():
    assert FIELD.geom_type == "Polygon" and len(FIELD.interiors) == 2


def test_white_keyline_art_reads():
    assert wka.detect(keyline_art(), ON) is True


@pytest.mark.parametrize("why, regs, cfg", [
    ("flag off", keyline_art(), PipelineConfig(white_keyline_art_recipe=False)),
    ("no outline pass", keyline_art(), replace(ON, border_from_outline=False)),
    ("field is not background", keyline_art(field_meta={}), ON),
    ("letters are not text", keyline_art(letter_meta={}), ON),
    ("letters are background (Becker's white faces)",
     keyline_art(letter_meta={"text_cluster_id": "TC1", "enclosed_background": True}), ON),
    ("no host round it", keyline_art(ring=False), ON),
])
def test_each_part_refuses_alone(why, regs, cfg):
    assert wka.detect(regs, cfg) is False, why


def test_any_other_art_leaves_the_config_the_same_object():
    assert wka.apply(ON, False) is ON
    off = PipelineConfig(white_keyline_art_recipe=False)
    assert wka.apply(off, True) is off              # the flag off: a verdict changes nothing


def test_the_recipe_is_every_switch_on():
    got = wka.apply(ON, True)
    assert all(getattr(got, k) is True for k in wka.RECIPE)
    assert all(got.extra.get(k) is True for k in wka.RECIPE_EXTRA)
    assert set(wka.RECIPE) >= {"silhouette_underfill", "sew_enclosed_white", "enclosed_white_keyline",
                               "silhouette_underfill_panels", "outline_loop_mitre"}


def test_the_mfab_extras_ride_the_gate_kent_2026_10_26():
    # "MFab extras into the gate": the sliver fold, fragment absorb, the
    # covered-shape skip and the black outer edge, on MFab-type art only
    assert {"keyline_fold_slivers", "skip_covered_shapes", "silhouette_underfill_rim"} <= set(wka.RECIPE)
    assert "absorb_fragments" in wka.RECIPE_EXTRA
    from digitizer_core import fragment_absorb
    mine = replace(ON, extra={"fill_section_travel": True})
    got = wka.apply(mine, True)
    assert fragment_absorb.enabled(got) and got.extra["fill_section_travel"] is True
    assert mine.extra == {"fill_section_travel": True}     # the caller's dict untouched
    assert not fragment_absorb.enabled(wka.apply(replace(ON, absorb_fragments=False), False))


def test_the_loop_chain_rides_the_gate_kent_2026_10_27():
    # "MFab gate only (Recommended)": the white loops chain on MFab-type art;
    # since 2026-10-27 ("Every job (Recommended)") on every job by default
    assert "keyline_loop_chain" in wka.RECIPE
    assert wka.apply(ON, True).keyline_loop_chain is True
    off = replace(ON, keyline_loop_chain=False)
    assert wka.apply(off, True).keyline_loop_chain is True
    assert wka.apply(off, False).keyline_loop_chain is False
    assert PipelineConfig().keyline_loop_chain is True


def test_the_gates_plan_is_the_recipes(monkeypatch):
    from digitizer_core.pipeline import BackgroundInfo, PipelineResult, plan_stitches

    def result(verdict):
        return PipelineResult(regions=[replace(r, meta={**r.meta, "stitched": True}) for r in keyline_art()],
                              palette=[], background=BackgroundInfo(detected=False),
                              px_per_mm=10.0, design_size_mm=(40.0, 30.0), white_keyline_art=verdict)

    def coords(plan):
        return [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
                for _b, r in plan.iter_runs() for x, y in r.points]
    gated = plan_stitches(result(True), ON)
    recipe = plan_stitches(result(False), replace(PipelineConfig(), **{k: True for k in wka.RECIPE},
                                                  extra={k: True for k in wka.RECIPE_EXTRA}))
    assert coords(gated) == coords(recipe)
    assert coords(plan_stitches(result(False), ON)) == coords(plan_stitches(result(False), PipelineConfig()))


def _verdict(art, width_mm, garment):
    from digitizer_service.app import _decode, _parse_config
    from digitizer_core.pipeline import build_generation, finish_generation
    from tools import pro_pair as pp
    data = (TESTDATA / art).read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps(
        pp.request(width_mm, garment, {"white_keyline_art_recipe": True}))))
    gen = build_generation(_decode(data), cfg, exif_source=data)
    return finish_generation(gen.fork(), cfg).white_keyline_art


def test_real_art_mfab_lc_reads_and_becker_does_not():
    # the Studio's request at the pro's widths (`tools.pro_pair.request`)
    assert _verdict("art/logo_mfab_lc.png", 96.7, "left_chest") is True
    assert _verdict("becker_marine_logo.png", 76.5, "hat_front") is False
