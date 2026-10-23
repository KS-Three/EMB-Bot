"""`cfg.fill_underlay_cross` (2026-10-21, built OFF): the pro's crossing pass
under a fill, in the hat / left-chest / beanie presets.

Every dense fill on every job in the professional's zip sews one sparse
tatami pass first, ~1.0 mm rows of ~4 mm stitches at ~90 degrees to the top
rows (`docs/underlay-audit-2026-10-05.md`; `docs/settings-vs-pro-2026-10-21.md`
rows 13-15). Ours walks the edge (`edge_run`, LC and beanie) or runs an edge
plus a 2.0 mm zigzag (`edge_zigzag`, hat). `cross_tatami` already exists as a
picker choice; this flag puts it in the three presets.

A fabric preset is a physical constant (ROADMAP gate 1), so the flag waits on
the sew-out card's arm and Kent's flip. What is asserted here is wiring, not
a value: OFF is the preset's own underlay, ON is exactly what an explicit
`underlay_style="cross_tatami"` sews, only the listed presets move, and every
override that beat the preset still beats it.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, fabrics, get_fabric, stitches
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART

# Wide enough that no tier but fill can take it.
FIELD = Polygon([(-15, -10), (15, -10), (15, 10), (-15, 10)])


def _region(meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id="Sfield", polygon=FIELD, thread_index=5,
                  thread_number=CHART[5].number, area_mm2=FIELD.area, meta=m)


def _plan(fabric_id: str, meta: dict | None = None, **cfg_kw):
    cfg_kw.setdefault("edge_cap", "none")
    fab = get_fabric(fabric_id)
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps([_region(meta)], fab, c)
    blocks, _w = sequence(planned, fab, c)
    return [(r.kind, r.points) for b in blocks for r in b.runs]


def _underlay(runs):
    return [pts for kind, pts in runs if kind == stitches.UNDERLAY]


def test_default_is_off():
    assert PipelineConfig().fill_underlay_cross is False


def test_the_table_itself_is_untouched():
    # Gate 1: the flag is the swap; the presets keep their own values.
    assert all(f.fill_underlay != "cross_tatami" for f in fabrics.FABRICS)


@pytest.mark.parametrize("fabric_id", fabrics.CROSS_UNDERLAY_FABRICS)
def test_off_sews_the_preset_s_own_underlay(fabric_id):
    own = get_fabric(fabric_id).fill_underlay
    assert _plan(fabric_id) == _plan(fabric_id, underlay_style=own)


@pytest.mark.parametrize("fabric_id", fabrics.CROSS_UNDERLAY_FABRICS)
def test_on_sews_exactly_the_cross_pass(fabric_id):
    on = _plan(fabric_id, fill_underlay_cross=True)
    assert on == _plan(fabric_id, underlay_style="cross_tatami")
    assert on != _plan(fabric_id)
    assert _underlay(on), "the field sewed no underlay at all"


def test_the_set_covers_hat_left_chest_and_beanie():
    garments = {g for g, f in fabrics.GARMENT_FABRIC.items()
                if f in fabrics.CROSS_UNDERLAY_FABRICS}
    assert {"hat_front", "left_chest", "beanie"} <= garments


@pytest.mark.parametrize("fabric_id", sorted(
    {f.id for f in fabrics.FABRICS} - set(fabrics.CROSS_UNDERLAY_FABRICS)))
def test_other_presets_do_not_move(fabric_id):
    assert _plan(fabric_id, fill_underlay_cross=True) == _plan(fabric_id)


def test_an_explicit_style_still_wins():
    a = _plan("structured_cap", fill_underlay_cross=True, underlay_style="edge_run")
    assert a == _plan("structured_cap", underlay_style="edge_run")


def test_a_shape_override_still_wins():
    meta = {"underlay_style": "edge_run"}
    assert (_plan("pique_knit", meta, fill_underlay_cross=True)
            == _plan("pique_knit", meta))


def test_underlay_off_still_means_none():
    a = _plan("jersey_tee", fill_underlay_cross=True, underlay=False)
    assert not _underlay(a)
