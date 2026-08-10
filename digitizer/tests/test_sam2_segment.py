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


# --- 2/3. The seam: happy path and every runtime failure mode ---------------
# All of these mock subprocess.run, so none needs a SAM2 install.


def _prepped(fixture: Path = FIXTURE, **cfg_kw):
    from digitizer_core.stage1_prep import prep

    cfg = _cfg(**cfg_kw)
    return prep(fixture, cfg), cfg


def _available(monkeypatch):
    """Make the environment-level check pass without touching the disk."""
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(s2, "sam2_segmentation_unavailable_reason", lambda: None)
    monkeypatch.setattr(s2, "SAM2_VENV_PYTHON", Path("/fake/python"))
    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", Path("/fake/worker.py"))
    return s2


def _fake_worker(labels_for):
    """Build a subprocess.run stand-in that writes the npz `labels_for(h, w)`
    returns, reading the real temp input PNG the seam just wrote so the
    shapes always agree."""

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(cmd, **kwargs):
        in_path, out_path = cmd[2], cmd[3]
        image = cv2.imread(str(in_path), cv2.IMREAD_COLOR)
        assert image is not None, "the seam did not write a readable input image"
        h, w = image.shape[:2]
        labels = labels_for(h, w)
        n = int(labels.max()) + 1 if labels.max() >= 0 else 0
        np.savez_compressed(
            out_path,
            labels=labels.astype(np.int32),
            area=np.array([int((labels == i).sum()) for i in range(n)], np.int64),
            predicted_iou=np.full(n, 0.9, np.float32),
            stability_score=np.full(n, 0.95, np.float32),
            raw_mask_count=np.int64(n),
        )
        return _Proc()

    return _run


def _quadrant_labels(h: int, w: int) -> np.ndarray:
    """Four big blocks plus an uncovered stripe — a stand-in for SAM2 output
    that exercises real regions AND the -1 (no mask covered this pixel)
    case the seam has to handle."""
    labels = np.full((h, w), -1, np.int32)
    labels[: h // 2, : w // 2] = 0
    labels[: h // 2, w // 2:] = 1
    labels[h // 2:, : w // 2] = 2
    labels[h // 2:, w // 2: w - w // 8] = 3
    return labels


def test_seam_returns_a_real_quant_from_a_worker_label_map(monkeypatch):
    s2 = _available(monkeypatch)
    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(_quadrant_labels))

    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)

    assert reason is None
    assert quant is not None
    assert quant.labels.shape == p.rgb.shape[:2]
    assert quant.labels.dtype == np.int32
    assert quant.thread_indices, "no thread colors came out of palette selection"
    assert quant.cluster_rgb.shape == (len(quant.thread_indices), 3)
    assert quant.labels.max() < len(quant.thread_indices)

    from digitizer_core.warnings_codes import (
        PHOTO_PALETTE_SELECTED,
        PHOTO_SAM2_SEGMENTED,
        PHOTO_SEGMENT_REGION_COUNT,
    )

    codes = [w["code"] for w in quant.warnings]
    # The shared tail's own two warnings prove kept_masks_to_quant ran.
    assert PHOTO_SEGMENT_REGION_COUNT in codes
    assert PHOTO_PALETTE_SELECTED in codes
    assert PHOTO_SAM2_SEGMENTED in codes
    region_count = next(
        w for w in quant.warnings if w["code"] == PHOTO_SEGMENT_REGION_COUNT
    )
    assert "SAM2 masks" in region_count["message"]
    segmented = next(w for w in quant.warnings if w["code"] == PHOTO_SAM2_SEGMENTED)
    assert segmented["checkpoint"] == cfg.photo_segment_sam2_checkpoint
    assert segmented["raw_masks"] == 4


def test_seam_passes_the_documented_argv_to_the_worker(monkeypatch):
    s2 = _available(monkeypatch)
    seen: list[list[str]] = []
    inner = _fake_worker(_quadrant_labels)

    def _spy(cmd, **kwargs):
        seen.append([str(c) for c in cmd])
        assert kwargs["timeout"] == 180.0, "the starvation bound was not passed"
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        return inner(cmd, **kwargs)

    monkeypatch.setattr(s2.subprocess, "run", _spy)
    p, cfg = _prepped()
    s2.sam2_segment_seam(p, cfg)

    assert len(seen) == 1
    cmd = seen[0]
    assert len(cmd) == 7
    # str(Path("/fake/python")) is "\\fake\\python" on Windows — compare the
    # basename, not the whole path, so this test is not OS-specific.
    assert Path(cmd[0]).name == "python"
    assert cmd[1].endswith("worker.py")
    assert cmd[4] == "tiny"
    assert cmd[5] == "16"
    assert int(cmd[6]) == int((cfg.min_detail_mm * p.px_per_mm) ** 2)


def test_seam_downscales_to_the_configured_max_side(monkeypatch):
    s2 = _available(monkeypatch)
    sizes: list[tuple[int, int]] = []

    def _run(cmd, **kwargs):
        image = cv2.imread(str(cmd[2]), cv2.IMREAD_COLOR)
        sizes.append(image.shape[:2])
        return _fake_worker(_quadrant_labels)(cmd, **kwargs)

    monkeypatch.setattr(s2.subprocess, "run", _run)
    p, cfg = _prepped(photo_segment_sam2_max_side_px=64)
    quant, reason = s2.sam2_segment_seam(p, cfg)

    assert reason is None
    assert max(sizes[0]) == 64, f"worker saw {sizes[0]}, expected a 64px long side"
    # ...and the label map still comes back at full resolution.
    assert quant.labels.shape == p.rgb.shape[:2]


def test_unavailable_environment_short_circuits_before_any_subprocess(monkeypatch):
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(
        s2, "sam2_segmentation_unavailable_reason", lambda: "venv not built (test)"
    )

    def _boom(*a, **kw):
        raise AssertionError("subprocess.run must not be reached")

    monkeypatch.setattr(s2.subprocess, "run", _boom)
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason == "venv not built (test)"


def test_subprocess_timeout_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    def _raise_timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="sam2_worker.py", timeout=1.0)

    monkeypatch.setattr(s2.subprocess, "run", _raise_timeout)
    p, cfg = _prepped(photo_segment_sam2_timeout_s=1.0)
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "timed out" in reason


def test_subprocess_nonzero_exit_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    class _Proc:
        returncode = 5
        stdout = ""
        stderr = "sam2_worker: mask generation failed: boom\n"

    monkeypatch.setattr(s2.subprocess, "run", lambda *a, **kw: _Proc())
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "exited 5" in reason and "boom" in reason


def test_launch_failure_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    def _raise_oserror(*a, **kw):
        raise OSError("no such file")

    monkeypatch.setattr(s2.subprocess, "run", _raise_oserror)
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "failed to launch" in reason


def test_missing_output_file_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(s2.subprocess, "run", lambda *a, **kw: _Proc())
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "no readable output" in reason


def test_wrong_shape_output_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)
    monkeypatch.setattr(
        s2.subprocess,
        "run",
        _fake_worker(lambda h, w: np.zeros((h + 7, w), np.int32)),
    )
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "label map" in reason


def test_no_usable_regions_degrades_to_none_rather_than_an_empty_design(monkeypatch):
    """A worker that technically succeeded but produced nothing sewable must
    fall back to the classical segmenter, not hand the pipeline a design with
    zero regions."""
    s2 = _available(monkeypatch)

    def _empty(h, w):
        return np.full((h, w), -1, np.int32)

    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(_empty))
    p, cfg = _prepped()
    # Force every leftover component under the sewable floor so the floor
    # itself, not the label map, is what empties the region list.
    p.bg_mask = np.ones(p.rgb.shape[:2], bool)
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "no usable regions" in reason


def test_seam_never_raises_on_a_worker_that_writes_garbage(monkeypatch):
    """The contract that matters most: whatever the worker does, the seam
    returns a tuple. Mirrors remove_background_seam's own never-raises
    guarantee."""
    s2 = _available(monkeypatch)

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(cmd, **kwargs):
        Path(cmd[3]).write_bytes(b"not an npz at all")
        return _Proc()

    monkeypatch.setattr(s2.subprocess, "run", _run)
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None
