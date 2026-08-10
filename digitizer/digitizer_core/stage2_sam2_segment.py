"""Stage 2 (photo path) — SAM2 region former.

An OPTIONAL alternative front half for `stage2_photo_segment.segment()`, for
photo_subject/photo_scene designs only. Same output contract (`Quant`), and
literally the same back half: this module produces a list of non-overlapping
`RegionMask`s from SAM2's instance masks and then hands them to
`stage2_photo_segment.kept_masks_to_quant`, the shared tail the classical
SLIC+RAG lane also calls. The ONLY difference between the two segmenters is
how the region list gets built; palette selection, spool dedupe, the enclosed
population and the warnings are one implementation, not two.

Why SAM2 might beat SLIC+RAG here: SLIC/SEEDS group pixels that are close in
BOTH color and space, then merge on a perceptual color threshold — so a
region boundary is wherever color changes enough, which is not always where
an object ends. SAM2 segments by learned visual saliency, so a subject whose
interior varies smoothly (a face, a jacket, a dog) can come back as one mask
instead of a color-ramp's worth of merged superpixels. Whether that actually
improves the SEWN result is an open, measurable question — see this lane's
plan doc, `docs/superpowers/plans/2026-08-10-sam2-segmentation.md`, and its
Task 6 acceptance criteria. Nothing here assumes it does.

Why a subprocess: SAM2 needs PyTorch, which cannot go in the shared venv —
see `digitizer/sam2_isolated/README.md` and `sam2_worker.py`'s own docstring.
The bridge, its timeout, and its never-raises contract mirror
`stage1_photo_prep.remove_background_seam` exactly.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .config import PipelineConfig
from .stage1_prep import Prep
from .stage2_photo_segment import kept_masks_to_quant
from .stage2_quantize import Quant
from .stage3_segment import RegionMask, resolve_small_regions
from .warnings_codes import PHOTO_SAM2_SEGMENTED, warn

# Where the isolated SAM2 venv + its worker script live. Module-level
# constants (not cfg fields) so tests can monkeypatch them exactly the way
# stage1_photo_prep's REMBG_* constants are monkeypatched, without threading
# a path override through PipelineConfig for something that is a deploy-time
# file location, not a per-job parameter.
SAM2_WORKER_PATH = Path(__file__).resolve().parent / "sam2_worker.py"
_SAM2_ISOLATED_DIR = Path(__file__).resolve().parents[1] / "sam2_isolated"


def _default_sam2_venv_python() -> Path:
    """POSIX venvs put the interpreter under bin/, Windows under Scripts/.
    Prefer whichever actually exists; POSIX is the default name used in the
    "missing" reason message when neither does (matching this repo's other
    tooling, which targets POSIX first — see COOKBOOK.md)."""
    posix = _SAM2_ISOLATED_DIR / "venv" / "bin" / "python"
    windows = _SAM2_ISOLATED_DIR / "venv" / "Scripts" / "python.exe"
    if windows.is_file() and not posix.is_file():
        return windows
    return posix


SAM2_VENV_PYTHON = _default_sam2_venv_python()


def sam2_segmentation_unavailable_reason() -> str | None:
    """None when the isolated SAM2 venv + worker script look runnable here;
    otherwise one honest sentence why not.

    ENVIRONMENT-ONLY: a per-call runtime failure (a subprocess crash, a
    timeout, a first-use checkpoint download failing on a machine with no
    route to Meta's release host) is not knowable from files on disk alone,
    so it is NOT covered here — `sam2_segment_seam` reports that half itself,
    in its own return value. The two never disagree about the
    environment-level half because both read the exact same two paths. Same
    split, for the same reason, as
    `stage1_photo_prep.background_removal_unavailable_reason`.
    """
    if not SAM2_WORKER_PATH.is_file():
        return f"SAM2 worker script missing at {SAM2_WORKER_PATH}"
    if not SAM2_VENV_PYTHON.is_file():
        return (
            f"isolated SAM2 venv not found at {SAM2_VENV_PYTHON} — see "
            "digitizer/sam2_isolated/README.md to build it"
        )
    return None


def _downscale_for_sam2(
    rgb: np.ndarray, max_side_px: int
) -> np.ndarray:
    """Shrink the raster to `max_side_px` on its long side, or return it
    untouched. INTER_AREA because this is a downsample and it is the right
    filter for one — the same choice `tests/test_background_removal.py`'s own
    fixture helper makes."""
    h, w = rgb.shape[:2]
    longest = max(h, w)
    if max_side_px <= 0 or longest <= max_side_px:
        return rgb
    scale = max_side_px / float(longest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _upsample_labels(labels: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Nearest-neighbour upsample of a label array to `shape`.

    Done with numpy index arithmetic, not `cv2.resize`: OpenCV's resize does
    not accept CV_32S input, and round-tripping label ids through float32
    to work around that is a silent-corruption risk this code has no reason
    to take. Nearest-neighbour is the only correct filter for label data —
    any interpolation would invent label ids that no mask ever produced.
    """
    h, w = shape
    src_h, src_w = labels.shape[:2]
    if (src_h, src_w) == (h, w):
        return labels
    ys = np.clip((np.arange(h) * src_h) // h, 0, src_h - 1)
    xs = np.clip((np.arange(w) * src_w) // w, 0, src_w - 1)
    return labels[ys][:, xs]


def _regions_from_label_map(
    labels: np.ndarray, base_valid: np.ndarray
) -> list[RegionMask]:
    """One RegionMask per 8-connected component of every label id.

    Mirrors `stage2_photo_segment.segment`'s own step 4 exactly, including
    the `& base_valid` intersection: a label id is not on its own proof of
    foreground, and intersecting with the real per-population mask is what
    keeps background AND enclosed pixels out of every RegionMask regardless
    of which id they wear.

    The `-1` id — pixels no SAM2 mask covered — is deliberately NOT special-
    cased. SAM2's automatic generator returns instance masks, not a partition,
    so uncovered foreground is normal and expected; dropping it would delete
    real artwork from the design. Its components compete for survival on
    exactly the same terms as every other region, in `resolve_small_regions`.
    """
    regions: list[RegionMask] = []
    for lbl in sorted(set(np.unique(labels[base_valid]).tolist())):
        comp_mask = ((labels == lbl) & base_valid).astype(np.uint8)
        n_cc, cc = cv2.connectedComponents(comp_mask, connectivity=8)
        for c in range(1, n_cc):
            regions.append(RegionMask(mask=(cc == c), layer=0, source="photo_sam2"))
    return regions


def sam2_segment_seam(
    p: Prep,
    cfg: PipelineConfig,
    face_regions=None,
    bg_mask: np.ndarray | None = None,
) -> tuple[Quant | None, str | None]:
    """SAM2-backed stage 2, run in the isolated venv documented at
    `digitizer/sam2_isolated/README.md` — NEVER the shared `digitizer/.venv`.

    Returns `(quant, reason)`:
      * `(quant, None)` — the worker ran and produced usable regions. `quant`
        is a full `Quant`, built by the same `kept_masks_to_quant` tail the
        classical lane uses, plus a `PHOTO_SAM2_SEGMENTED` info warning.
      * `(None, reason)` — cannot run here (isolated venv/worker missing, per
        `sam2_segmentation_unavailable_reason`) OR the subprocess failed at
        runtime (timeout, crash, unreadable output, a first-use checkpoint
        download failing, no usable regions, ...). One honest sentence either
        way. The documented fallback: the caller runs
        `stage2_photo_segment.segment()` instead and says so via
        `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE`.

    Never raises: every failure mode funnels into the `(None, reason)` arm so
    a SAM2 problem degrades a job, never crashes it — the same contract
    `stage1_photo_prep.remove_background_seam` gives rembg failures.

    The `timeout=` on the subprocess call below is load-bearing beyond the
    usual hygiene: `digitizer_service/jobs.py`'s JobRegistry is a
    single-worker ThreadPoolExecutor with no per-job timeout and no
    cancellation, so this is the only thing that stops a hung SAM2 call from
    starving every queued job behind it.
    """
    reason = sam2_segmentation_unavailable_reason()
    if reason is not None:
        return None, reason

    h, w = p.rgb.shape[:2]
    enclosed = p.enclosed_mask
    has_enclosed = enclosed is not None and enclosed.any()
    base_valid = (~p.bg_mask & ~enclosed) if has_enclosed else ~p.bg_mask

    # The same "too small to sew" area the min-detail floor means everywhere
    # else in this codebase (stage3_segment.resolve_small_regions,
    # stage1_photo_prep._clean_background_mask) — handed to SAM2 so it drops
    # sub-sewable masks itself instead of shipping thousands of them back
    # over the pipe. Whatever survives still faces the real floor below.
    min_mask_region_area = int((cfg.min_detail_mm * p.px_per_mm) ** 2)
    small = _downscale_for_sam2(p.rgb, cfg.photo_segment_sam2_max_side_px)

    with tempfile.TemporaryDirectory(prefix="sam2_seam_") as tmp:
        in_path = Path(tmp) / "in.png"
        out_path = Path(tmp) / "masks.npz"
        if not cv2.imwrite(str(in_path), cv2.cvtColor(small, cv2.COLOR_RGB2BGR)):
            return None, "failed to write a temp input image for the SAM2 worker"

        try:
            proc = subprocess.run(
                [
                    str(SAM2_VENV_PYTHON),
                    str(SAM2_WORKER_PATH),
                    str(in_path),
                    str(out_path),
                    str(cfg.photo_segment_sam2_checkpoint),
                    str(int(cfg.photo_segment_sam2_points_per_side)),
                    str(min_mask_region_area),
                ],
                capture_output=True,
                text=True,
                timeout=cfg.photo_segment_sam2_timeout_s,
            )
        except subprocess.TimeoutExpired:
            return None, (
                "SAM2 worker timed out after "
                f"{cfg.photo_segment_sam2_timeout_s:g}s"
            )
        except OSError as exc:
            return None, f"failed to launch the isolated SAM2 venv: {exc}"

        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()
            detail = tail[-1] if tail else "no stderr output"
            return None, f"SAM2 worker exited {proc.returncode}: {detail}"

        try:
            with np.load(out_path, allow_pickle=False) as data:
                raw_labels = np.asarray(data["labels"], np.int32)
                raw_mask_count = int(data["raw_mask_count"])
        except Exception as exc:  # noqa: BLE001 -- any unreadable output degrades
            return None, f"SAM2 worker reported success but wrote no readable output: {exc}"

    if raw_labels.shape[:2] != small.shape[:2]:
        return None, (
            f"SAM2 worker returned a {raw_labels.shape[:2]} label map for a "
            f"{small.shape[:2]} image"
        )

    labels = _upsample_labels(raw_labels, (h, w))
    regions = _regions_from_label_map(labels, base_valid)
    merged_count = len(set(np.unique(labels[base_valid]).tolist()))
    kept, floor_warnings = resolve_small_regions(regions, cfg, p.px_per_mm)
    if not kept:
        return None, (
            f"SAM2 produced no usable regions ({raw_mask_count} raw masks, "
            f"{len(regions)} components, all below the "
            f"{cfg.min_detail_mm:g} mm detail floor)"
        )

    quant = kept_masks_to_quant(
        p,
        cfg,
        kept,
        floor_warnings,
        face_regions=face_regions,
        bg_mask=bg_mask,
        raw_count=raw_mask_count,
        merged_count=merged_count,
        raw_unit_label="SAM2 masks",
        oversegment_labels=labels,
    )
    quant.warnings.append(
        warn(
            PHOTO_SAM2_SEGMENTED,
            f"SAM2 segmentation produced {len(kept)} region"
            f"{'s' if len(kept) != 1 else ''} from {raw_mask_count} raw mask"
            f"{'s' if raw_mask_count != 1 else ''} "
            f"({cfg.photo_segment_sam2_checkpoint} checkpoint, CPU).",
            raw_masks=raw_mask_count,
            regions=len(kept),
            checkpoint=cfg.photo_segment_sam2_checkpoint,
        )
    )
    return quant, None
