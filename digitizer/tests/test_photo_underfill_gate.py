"""Under-fill gated off for photo classes (Kent 2026-11-05, "Gate under-fill off
for photo classes"). `pipeline.gate_underfill_for_photo`.

#1143 made the white-keyline recipe's switches plain defaults, so on a photo's
tonal split every band sewed on a full ground fill: DENSITY_STACKED on
dof_meadow left_chest (21,437 stitches, peak 9.48). Gated off the same row
sews ~20,873 and carries no finding; `silhouette_underfill_photo=True` is the
old arm. Logos are untouched: their plan hashes were taken on origin/main
13c0eb85 BEFORE the gate and must not move.

The photo rows run on the CI route (no rembg cutout), as the scorecard does.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from digitizer_core import PipelineConfig, digitize
from digitizer_core import stage1_photo_prep as s1
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import gate_underfill_for_photo
from digitizer_core.preflight import run_preflight

from .conftest import TESTDATA

# pin-rides-defaults: the logo md5s are the live engine on purpose; they prove the gate moved no logo,
# and a later flip that moves them re-pins them (tools.ci_repin).

#: plan md5 (json of plan_to_design stitches) at 80 mm / left_chest, taken
#: before the gate on origin/main 13c0eb85: (md5, stitch count).
LOGO_PINS = {
    "logo_whitebg.png": ("flat", "6cbfbb8c9ab9b7701b99b88f89644051", 6711),
    "photo/gradient_ramp_linear.png": ("gradient", "06bad7d0e0d1c4acd342b87fa28169ff", 10938),
}


def _md5(plan):
    return hashlib.md5(json.dumps(plan_to_design(plan)["stitches"]).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(LOGO_PINS))
def test_logo_plans_are_byte_identical_to_before_the_gate(fixture):
    cls, md5, n = LOGO_PINS[fixture]
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    res, plan = digitize(TESTDATA / fixture, cfg)
    assert res.design_class == cls
    assert (_md5(plan), len(plan_to_design(plan)["stitches"])) == (md5, n)


def test_gate_only_touches_photo_classes_and_the_flag_restores_them():
    cfg = PipelineConfig()
    assert cfg.silhouette_underfill and cfg.silhouette_underfill_panels and cfg.silhouette_underfill_rim
    for c in ("photo_subject", "photo_scene"):
        g = gate_underfill_for_photo(cfg, c)
        assert not (g.silhouette_underfill or g.silhouette_underfill_panels or g.silhouette_underfill_rim)
        assert gate_underfill_for_photo(PipelineConfig(silhouette_underfill_photo=True), c).silhouette_underfill
    for c in ("flat", "gradient", None):
        assert gate_underfill_for_photo(cfg, c) is cfg
    # white-keyline art keeps it even when stage 0 calls it a photo (MFab hat)
    assert gate_underfill_for_photo(cfg, "photo_scene", True) is cfg


def _meadow(monkeypatch, **kw):
    monkeypatch.setattr(s1, "REMBG_VENV_PYTHON", TESTDATA / "no_such_rembg" / "python")
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)
    path = TESTDATA / "photo" / "photo_dof_meadow.png"
    res, plan = digitize(path, cfg)
    rep = run_preflight(res, plan, cfg, image=path)
    codes = [f["code"] for f in rep["findings"]]
    return res.design_class, rep["metrics"]["stitch_count"], codes


def test_meadow_gated_has_no_density_stacked(monkeypatch):
    cls, n, codes = _meadow(monkeypatch)
    assert cls == "photo_scene"
    assert "DENSITY_STACKED" not in codes
    assert n == pytest.approx(20873, rel=0.01)


def test_meadow_with_the_photo_flag_is_todays_stacked_plan(monkeypatch):
    cls, n, codes = _meadow(monkeypatch, silhouette_underfill_photo=True)
    assert cls == "photo_scene"
    assert "DENSITY_STACKED" in codes
    assert n == pytest.approx(21437, rel=0.01)
