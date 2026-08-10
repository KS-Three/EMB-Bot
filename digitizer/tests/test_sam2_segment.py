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
    """Four big blocks around a real -1 corridor — a stand-in for SAM2
    output that exercises real regions AND the -1 (no mask covered this
    pixel) case the seam has to handle.

    The corridor sits at columns [0.45w, 0.50w) of the BOTTOM half only
    (the top half is fully covered by labels 0/1) — deliberately NOT at the
    image edge. `region_blobs.png`'s own foreground is a set of blobs sitting
    well inside the canvas (measured bbox: y in [61, 554], x in [141, 712]
    of a 600x900 canvas), so a corridor carved at the far edge (this
    fixture's original design) never actually overlaps `base_valid` — the
    -1 handling it was meant to exercise was silently untested. This
    placement measurably does intersect real foreground (~11.3k px at full
    resolution) — see
    `test_seam_returns_a_real_quant_from_a_worker_label_map`'s pinned
    region count below, which only holds if the corridor became its own
    region."""
    labels = np.full((h, w), -1, np.int32)
    gap0, gap1 = int(w * 0.45), int(w * 0.50)
    labels[: h // 2, : w // 2] = 0
    labels[: h // 2, w // 2:] = 1
    labels[h // 2:, :gap0] = 2
    labels[h // 2:, gap1:] = 3
    # labels[h // 2:, gap0:gap1] is left at -1 — the corridor.
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
    # Pinned, not just "some positive number": region_blobs.png's four label
    # blocks plus the -1 corridor between labels 2 and 3 (see
    # `_quadrant_labels`'s own docstring) survive `resolve_small_regions`
    # as exactly 5 regions — 4 labeled blobs + 1 for the corridor. If `-1`
    # handling were ever deleted (e.g. a `if lbl < 0: continue` guard added
    # to `_regions_from_label_map`), this drops to 4 and the assertion
    # fails; confirmed directly against this fixture before writing this
    # assertion.
    assert region_count["count"] == 5, (
        "expected 4 SAM2-labeled quadrants + 1 region from the -1 "
        "(uncovered) corridor; a count of 4 would mean -1 pixels were "
        "silently dropped instead of becoming their own region"
    )
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
    # The area floor must be expressed in pixels of the image the worker
    # actually receives — `small`, computed via the same
    # `_downscale_for_sam2` the seam itself calls — not the full-resolution
    # image `p.px_per_mm` describes. At the default max_side_px (1024,
    # bigger than this fixture's 900px long side) no downscale happens, so
    # `scale` is 1.0 here and this case alone would NOT catch a formula that
    # forgot to scale at all; see
    # `test_seam_scales_the_area_floor_to_the_downscaled_image` below for a
    # case where it actually does.
    small = s2._downscale_for_sam2(p.rgb, cfg.photo_segment_sam2_max_side_px)
    scale = max(small.shape[:2]) / float(max(p.rgb.shape[:2]))
    assert int(cmd[6]) == int((cfg.min_detail_mm * p.px_per_mm * scale) ** 2)


def test_seam_scales_the_area_floor_to_the_downscaled_image(monkeypatch):
    """C1 regression: `min_mask_region_area` is a PIXEL floor consumed by
    the worker against the image it actually receives (`small`), not the
    full-resolution image `p.px_per_mm` describes. Handing it the
    full-resolution figure unscaled over-filters by `1 / scale ** 2` —
    silently deleting sewable detail on essentially every real input that
    gets downscaled at all. This test forces an actual downscale (fixture
    is 900px wide, cap set to 64px) so it cannot silently degenerate to
    `scale == 1.0` the way the general argv test above does."""
    s2 = _available(monkeypatch)
    seen: list[list[str]] = []

    def _spy(cmd, **kwargs):
        seen.append([str(c) for c in cmd])
        return _fake_worker(_quadrant_labels)(cmd, **kwargs)

    monkeypatch.setattr(s2.subprocess, "run", _spy)
    p, cfg = _prepped(photo_segment_sam2_max_side_px=64)
    s2.sam2_segment_seam(p, cfg)

    assert len(seen) == 1
    cmd = seen[0]
    small = s2._downscale_for_sam2(p.rgb, cfg.photo_segment_sam2_max_side_px)
    assert max(small.shape[:2]) == 64, "fixture must actually downscale here"
    scale = max(small.shape[:2]) / float(max(p.rgb.shape[:2]))
    expected = int((cfg.min_detail_mm * p.px_per_mm * scale) ** 2)
    full_res_unscaled = int((cfg.min_detail_mm * p.px_per_mm) ** 2)
    assert expected < full_res_unscaled, (
        "the fixture must actually downscale for this test to discriminate "
        "the bug from the correct behavior"
    )
    assert int(cmd[6]) == expected


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


def test_higher_dimensional_output_degrades_to_none_with_a_reason(monkeypatch):
    """C2 regression: a worker that writes a non-2-D `labels` array (e.g.
    (H, W, 3) instead of (H, W)) has the SAME leading two dims as a correct
    array, so a `shape[:2]`-only comparison lets it through. Unguarded, that
    survives `_upsample_labels` (also `shape[:2]`-only) and only fails deep
    inside `_regions_from_label_map`'s `labels == lbl` broadcast against the
    2-D `base_valid` — a ValueError raised OUTSIDE every try block, breaking
    the never-raises contract for a worker that writes syntactically valid
    but wrong-shaped output."""
    s2 = _available(monkeypatch)

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(cmd, **kwargs):
        in_path, out_path = cmd[2], cmd[3]
        image = cv2.imread(str(in_path), cv2.IMREAD_COLOR)
        h, w = image.shape[:2]
        labels = np.zeros((h, w, 3), np.int32)  # same leading dims, wrong ndim
        np.savez_compressed(
            out_path,
            labels=labels,
            area=np.zeros(0, np.int64),
            predicted_iou=np.zeros(0, np.float32),
            stability_score=np.zeros(0, np.float32),
            raw_mask_count=np.int64(0),
        )
        return _Proc()

    monkeypatch.setattr(s2.subprocess, "run", _run)
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "label map" in reason


def test_no_usable_regions_after_the_floor_degrades_to_none_with_a_reason(monkeypatch):
    """A worker that technically succeeded — real masks, genuinely
    intersecting the design's foreground — but every single resulting
    region is smaller than the sewable floor must still fall back to the
    classical segmenter, not hand the pipeline a design with zero regions.

    Unlike the sibling empty-regions test below, this drives real,
    non-trivial regions (region_blobs.png's own quadrant blobs, tens of
    thousands of px each) all the way through `resolve_small_regions`'s
    real absorb-or-drop loop: `min_detail_mm=50.0` puts the floor
    (`(50 * 7.15) ** 2 ~= 127,806 px²`) comfortably above every blob's own
    area (the biggest measures ~61,819 px²), and `small_shape_rescue=False`
    means a floor-filtered region with no `keep`-list neighbor to absorb
    into (there isn't one — nothing starts above this floor) has nowhere
    else to survive, so every region provably drops rather than merges into
    something else. This is what actually empties `kept` here — `regions`
    itself is non-empty going in, unlike the sibling test."""
    s2 = _available(monkeypatch)
    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(_quadrant_labels))

    p, cfg = _prepped(min_detail_mm=50.0, small_shape_rescue=False)
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None
    assert "no usable regions" in reason
    assert "50 mm detail floor" in reason


def test_no_usable_regions_from_empty_input_degrades_to_none_with_a_reason(monkeypatch):
    """The OTHER way `kept` can end up empty: no SAM2-labeled pixel — not
    even a -1 one — ever falls inside `base_valid` (background/enclosed
    everywhere), so `regions` is already `[]` before `resolve_small_regions`
    ever runs. The min-detail floor had nothing to do with this outcome, so
    the reason must say so rather than blaming the floor — contrast with
    `test_no_usable_regions_after_the_floor_degrades_to_none_with_a_reason`
    above, where real regions genuinely lose to the floor."""
    s2 = _available(monkeypatch)

    def _empty(h, w):
        return np.full((h, w), -1, np.int32)

    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(_empty))
    p, cfg = _prepped()
    p.bg_mask = np.ones(p.rgb.shape[:2], bool)
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None
    assert "no usable regions" in reason
    assert "detail floor" not in reason, (
        "no region ever existed to be filtered by the floor here — the "
        "reason must not blame it"
    )


def test_seam_absorbs_real_sub_floor_regions_via_resolve_small_regions(monkeypatch):
    """I4 regression: every OTHER test in this file drives `resolve_small_
    regions` through its empty-input early return only (`if not small:
    return regions, []`) — either every region is already big enough
    (the quadrant happy-path fixture) or `base_valid` is entirely False
    (the all-True `bg_mask` fixture the old "no usable regions" test used),
    so the actual absorb-or-drop loop never ran anywhere in this file.

    Builds a `Prep` directly (not through the real `prep()` pipeline) for
    full control over geometry: a real, non-degenerate `bg_mask` (only rows
    5:85, cols 5:50 of a 90x90 canvas are foreground — not all-True,
    not all-False) with one big host label (0) and three small islands
    (labels 1/2/3, 25px^2 each) touching its right edge. At
    `min_detail_mm=1.0` and `px_per_mm=10.0` the floor is
    `(1.0 * 10.0) ** 2 == 100px^2`, so the 25px^2 islands are real
    sub-floor regions with a real `keep`-list neighbor (the host) to
    absorb into — the actual absorb path, not its early exit."""
    s2 = _available(monkeypatch)

    from digitizer_core.stage1_prep import Prep

    h, w = 90, 90
    rgb = np.full((h, w, 3), (200, 60, 60), np.uint8)
    bg_mask = np.ones((h, w), bool)
    bg_mask[5:85, 5:50] = False  # the only foreground: a 80x45 interior

    p = Prep(
        rgb=rgb,
        bg_mask=bg_mask,
        px_per_mm=10.0,
        art_bbox=(5, 5, 50, 85),
        enclosed_mask=None,
    )

    def labels_for(hh: int, ww: int) -> np.ndarray:
        assert (hh, ww) == (h, w)
        labels = np.zeros((hh, ww), np.int32)  # host fills everything...
        labels[10:15, 45:50] = 1  # ...except 3 small islands carved
        labels[35:40, 45:50] = 2  # out of its own right edge, each
        labels[60:65, 45:50] = 3  # 5x5 = 25px^2, below the 100px^2 floor.
        return labels

    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(labels_for))
    cfg = _cfg(min_detail_mm=1.0)
    quant, reason = s2.sam2_segment_seam(p, cfg)

    assert reason is None, reason
    assert quant is not None

    from digitizer_core.warnings_codes import ABSORBED_SMALL_SHAPES

    absorbed = next(
        (w_ for w_ in quant.warnings if w_["code"] == ABSORBED_SMALL_SHAPES), None
    )
    assert absorbed is not None, (
        "resolve_small_regions's real absorb path never ran: no "
        "ABSORBED_SMALL_SHAPES warning came back"
    )
    assert absorbed["count"] == 3

    # The 3 absorbed islands' pixels must have actually landed inside the
    # host's own final region, not been silently dropped.
    host_label = quant.labels[20, 20]  # inside the host, away from any island
    assert host_label >= 0
    for y0, y1 in ((10, 15), (35, 40), (60, 65)):
        island_labels = set(quant.labels[y0:y1, 45:50].ravel().tolist())
        assert island_labels == {host_label}, (
            f"absorbed island at rows {y0}:{y1} did not end up labeled as "
            "the host region it was absorbed into"
        )


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
