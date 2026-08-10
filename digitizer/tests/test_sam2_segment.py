"""SAM2 photo segmentation — `digitizer_core/stage2_sam2_segment.py`.

What this file pins, section by section:

1. The environment-only availability check: worker script missing and
   isolated venv missing each produce one honest reason; both present
   produces None. Mirrors tests/test_background_removal.py section 2.
2. The seam's never-raises contract in every runtime failure mode (timeout,
   nonzero exit, launch failure, unreadable output, shape mismatch, no
   usable regions) — all mock `subprocess.run` directly, so they need no
   SAM2 install and always run.
3. The seam's happy path against a SYNTHETIC worker output: a hand-built
   label map goes in, a real `Quant` built by the shared
   `kept_masks_to_quant` tail comes out. The real SAM2 install is Task 6's
   manual acceptance step, not this file's job.
4. The pipeline gate: photo classes with the flag on try SAM2; "gradient"
   and "flat" never do; any failure falls back to the classical segmenter
   with PHOTO_SAM2_SEGMENTATION_UNAVAILABLE and the job still completes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig

from .test_flat_lane_byte_identical import GOLDEN

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
FIXTURE = TESTDATA / "photo" / "region_blobs.png"


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- 1. Availability: environment-only, two file-existence facts -------------


def test_missing_worker_script_gives_a_reason(monkeypatch, tmp_path):
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", tmp_path / "not_there.py")
    reason = s2.sam2_segmentation_unavailable_reason()
    assert reason is not None and "worker script missing" in reason


def test_missing_isolated_venv_gives_a_reason(monkeypatch, tmp_path):
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", tmp_path / "worker.py")
    (tmp_path / "worker.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(s2, "SAM2_VENV_PYTHON", tmp_path / "venv" / "bin" / "python")
    reason = s2.sam2_segmentation_unavailable_reason()
    assert reason is not None and "isolated SAM2 venv not found" in reason
    assert "sam2_isolated/README.md" in reason


def test_both_present_is_available(monkeypatch, tmp_path):
    import digitizer_core.stage2_sam2_segment as s2

    worker = tmp_path / "worker.py"
    python = tmp_path / "python"
    worker.write_text("", encoding="utf-8")
    python.write_text("", encoding="utf-8")
    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", worker)
    monkeypatch.setattr(s2, "SAM2_VENV_PYTHON", python)
    assert s2.sam2_segmentation_unavailable_reason() is None


def test_the_real_worker_script_is_actually_on_disk():
    """The half of the availability check this repo controls: the worker
    script ships with the package, so only the venv half should ever be the
    reason SAM2 is unavailable in a real checkout."""
    import digitizer_core.stage2_sam2_segment as s2

    assert s2.SAM2_WORKER_PATH.is_file()


# --- 1b. The config gate's defaults ------------------------------------------


def test_sam2_is_off_by_default_with_the_documented_defaults():
    cfg = PipelineConfig()
    assert cfg.photo_segment_sam2 is False
    assert cfg.photo_segment_sam2_checkpoint == "tiny"
    assert cfg.photo_segment_sam2_points_per_side == 16
    assert cfg.photo_segment_sam2_max_side_px == 1024
    assert cfg.photo_segment_sam2_timeout_s == 180.0


def test_the_default_checkpoint_tier_is_one_the_worker_knows():
    from digitizer_core import sam2_worker

    assert PipelineConfig().photo_segment_sam2_checkpoint in sam2_worker.CHECKPOINTS
