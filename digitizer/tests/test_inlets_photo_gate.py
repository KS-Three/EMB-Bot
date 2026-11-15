"""`outline_inlets_kept` / `_teeth`: logos only, never a photo class (2026-11-16,
as `point_touch_split` and `lone_glyph_keep`). A photograph's quantised blobs
have inlets everywhere, and none of the flip's combined-check photo moves was
read by eye. `pipeline.plan_stitches` turns the flag off on a photo class, so
the photo plans byte for byte as with it off. Runs on the CI route (no rembg
cutout), as `test_photo_underfill_gate.py` does.
"""
from __future__ import annotations

import hashlib
import json

from digitizer_core import PipelineConfig, digitize
from digitizer_core import stage1_photo_prep as s1
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import plan_stitches

from .conftest import TESTDATA


def _md5(plan):
    return hashlib.md5(json.dumps(plan_to_design(plan)["stitches"]).encode()).hexdigest()


def test_the_inlets_flags_leave_a_photo_as_it_was(monkeypatch):
    monkeypatch.setattr(s1, "REMBG_VENV_PYTHON", TESTDATA / "no_such_rembg" / "python")
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    assert cfg.outline_inlets_kept                      # ON by default since the flip
    res, plan = digitize(TESTDATA / "photo" / "photo_dof_meadow.png", cfg)
    assert res.design_class == "photo_scene"
    off = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", outline_inlets_kept=False)
    assert _md5(plan_stitches(res, off)) == _md5(plan)
