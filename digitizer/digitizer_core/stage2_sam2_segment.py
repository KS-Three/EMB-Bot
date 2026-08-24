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


def _resolve_venv_python(venv_dir: Path) -> Path:
    """POSIX venvs put the interpreter under bin/, Windows under Scripts/.
    Prefer whichever actually exists; POSIX is the default name used in the
    "missing" reason message when neither does (matching this repo's other
    tooling, which targets POSIX first — see COOKBOOK.md)."""
    posix = venv_dir / "bin" / "python"
    windows = venv_dir / "Scripts" / "python.exe"
    if windows.is_file() and not posix.is_file():
        return windows
    return posix


def _site_packages_exists(venv_dir: Path) -> bool:
    """Did packages actually get installed into this venv?

    Two layouts, same as `_resolve_venv_python` above: Windows puts them at
    `Lib/site-packages` flat, POSIX at `lib/pythonX.Y/site-packages` behind a
    VERSIONED directory — so a single hardcoded path can only ever be right on
    one platform. It was `Lib/site-packages` only until 2026-08-19, which
    rejected every healthy Linux/macOS venv with an "incomplete, rebuild"
    reason no rebuild could fix, silently downgrading SAM2 to the classical
    segmenter on the platform this repo's CI (`ubuntu-latest`) and its golden
    captures both use.
    """
    if (venv_dir / "Lib" / "site-packages").is_dir():
        return True
    return any((venv_dir / "lib").glob("python*/site-packages"))


SAM2_VENV_DIR = _SAM2_ISOLATED_DIR / "venv"
SAM2_VENV_PYTHON = _resolve_venv_python(SAM2_VENV_DIR)

# Hard upper clamp on `cfg.photo_segment_sam2_timeout_s`, applied here in the
# seam regardless of what a caller asked for. `PipelineConfig` round-trips
# over HTTP (see digitizer_service's job-submission API) with no server-side
# bound on this field, so a request could otherwise set an arbitrarily large
# timeout and tie up the single-worker job queue (see this function's own
# docstring on why `timeout=` is load-bearing) for as long as it likes. 300s
# = ~2x the measured 155.98s cold-start baseline (checkpoint download +
# torch's own cold import, Task 6, docs/sam2-segmentation-live-acceptance-
# 2026-08-10.md) plus margin: generous enough that a legitimate cold-cache
# run set close to that baseline is never clipped, small enough that no
# single request can starve the queue for more than a few minutes. Defense
# in depth only — this same exposure exists, unclamped, for the older
# `photo_prep_background_removal_timeout_s` field; fixing that is out of
# scope here.
SAM2_TIMEOUT_HARD_CAP_S = 300.0


def sam2_segmentation_unavailable_reason(venv_dir: Path | None = None) -> str | None:
    """None when the isolated SAM2 venv + worker script look runnable here;
    otherwise one honest sentence why not.

    `venv_dir` defaults to the real deploy-time location (`SAM2_VENV_DIR`,
    i.e. `sam2_isolated/venv`) and only exists as a parameter so tests can
    point this at a `tmp_path` fixture instead of building a real venv —
    every real caller (`sam2_segment_seam` included) calls this with no
    argument.

    Checks, in order: the worker script exists; the venv's python
    interpreter exists (a husk venv — `Scripts/`/`bin/` stubs with nothing
    real installed — still passes this one, which is exactly the gap the
    2026-08-18 probe found: such a husk read as "available" here and then
    died mid-job with "worker exited 106: failed to locate pyvenv.cfg");
    `pyvenv.cfg` exists (venv creation actually completed); and
    site-packages exists in whichever layout this platform uses (packages
    actually got installed into it — see `_site_packages_exists`).
    The last two are what a husk venv fails and a real one never does — a
    real `python -m venv` always writes `pyvenv.cfg` before anything else,
    and every subsequent `pip install` needs a site-packages directory to
    unpack into.

    ENVIRONMENT-ONLY: a per-call runtime failure (a subprocess crash, a
    timeout, a first-use checkpoint download failing on a machine with no
    route to Meta's release host) is not knowable from files on disk alone,
    so it is NOT covered here — `sam2_segment_seam` reports that half itself,
    in its own return value. The two never disagree about the
    environment-level half because both read the exact same paths. Same
    split, for the same reason, as
    `stage1_photo_prep.background_removal_unavailable_reason`.
    """
    if not SAM2_WORKER_PATH.is_file():
        return f"SAM2 worker script missing at {SAM2_WORKER_PATH}"

    if venv_dir is None:
        venv_dir = SAM2_VENV_DIR
        venv_python = SAM2_VENV_PYTHON
    else:
        venv_python = _resolve_venv_python(venv_dir)

    if not venv_python.is_file():
        return (
            f"isolated SAM2 venv not found at {venv_python} — see "
            "digitizer/sam2_isolated/README.md to build it"
        )
    if not (venv_dir / "pyvenv.cfg").is_file():
        return (
            f"sam2 venv incomplete at {venv_dir}: pyvenv.cfg missing "
            "(rebuild per sam2_isolated/README.md)"
        )
    if not _site_packages_exists(venv_dir):
        return (
            f"sam2 venv incomplete at {venv_dir}: site-packages missing "
            "(rebuild per sam2_isolated/README.md)"
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
        n_cc, cc, cc_stats, _ = cv2.connectedComponentsWithStats(comp_mask, connectivity=8)
        for c in range(1, n_cc):
            # Cropped at birth (2026-08-24), same as the classical segmenter:
            # `connectedComponentsWithStats` hands back each component's box,
            # so no frame-sized bool per region is ever built.
            cx0, cy0, cw, ch = (int(v) for v in cc_stats[c, :4])
            regions.append(RegionMask(
                crop=np.ascontiguousarray(cc[cy0:cy0 + ch, cx0:cx0 + cw] == c),
                origin=(cy0, cx0), frame_shape=tuple(comp_mask.shape),
                layer=0, source="photo_sam2"))
    return regions


def sam2_segment_seam(
    p: Prep,
    cfg: PipelineConfig,
    face_regions=None,
    bg_mask: np.ndarray | None = None,
    split_tonal: bool = False,
    shade_demand: bool = False,
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
    #
    # MUST be expressed in `small`'s own pixels, not the full-resolution
    # image's: `small` (built first, just below) is the only image the
    # worker ever sees, and `SAM2AutomaticMaskGenerator.min_mask_region_area`
    # is applied against whatever image it was actually given (see
    # `sam2_worker.py`'s own docstring). `p.px_per_mm` describes the
    # full-resolution raster, so the raw `(cfg.min_detail_mm * p.px_per_mm)
    # ** 2` figure is too large by `1 / scale ** 2` whenever downscaling
    # actually happens — at the default 1024px cap, a 2048px source over-
    # filters by 4x, a 4000px source by ~15x, silently deleting sewable
    # detail on essentially every real (non-tiny) input. `scale == 1.0`
    # when `small` is untouched (`_downscale_for_sam2`'s no-op branch), so
    # this reduces to the original formula exactly whenever there is
    # nothing to correct for.
    small = _downscale_for_sam2(p.rgb, cfg.photo_segment_sam2_max_side_px)
    scale = max(small.shape[:2]) / float(max(h, w))
    min_mask_region_area = int((cfg.min_detail_mm * p.px_per_mm * scale) ** 2)

    with tempfile.TemporaryDirectory(prefix="sam2_seam_") as tmp:
        in_path = Path(tmp) / "in.png"
        out_path = Path(tmp) / "masks.npz"
        if not cv2.imwrite(str(in_path), cv2.cvtColor(small, cv2.COLOR_RGB2BGR)):
            return None, "failed to write a temp input image for the SAM2 worker"

        timeout_s = min(cfg.photo_segment_sam2_timeout_s, SAM2_TIMEOUT_HARD_CAP_S)
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
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return None, f"SAM2 worker timed out after {timeout_s:g}s"
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

    # `ndim != 2` catches a malformed (e.g. (H, W, 3)) array that a
    # `shape[:2]`-only comparison would let through — such an array still
    # has the right leading two dims, so it would otherwise survive this
    # guard and `_upsample_labels` (which also only reads `shape[:2]`) and
    # only fail deep inside `_regions_from_label_map`'s `labels == lbl`
    # broadcast against the 2-D `base_valid`, OUTSIDE every try block here —
    # a real hole in the never-raises contract for a worker that writes
    # syntactically-valid-but-wrong-shaped output.
    if raw_labels.ndim != 2 or raw_labels.shape != small.shape[:2]:
        return None, (
            f"SAM2 worker returned a {raw_labels.shape} label map "
            f"(expected a single 2-D {small.shape[:2]} array)"
        )

    labels = _upsample_labels(raw_labels, (h, w))
    regions = _regions_from_label_map(labels, base_valid)
    merged_count = len(set(np.unique(labels[base_valid]).tolist()))
    # chain_rescue=False: the chained-structure rescue is gated OFF on the
    # photo lane -- see stage3_segment.resolve_small_regions for the
    # measurement. Photo quantisation makes sub-floor fragments mutually
    # adjacent everywhere, so chaining stops discriminating here.
    kept, floor_warnings = resolve_small_regions(
        regions, cfg, p.px_per_mm, chain_rescue=False)
    if not kept:
        if not regions:
            # `regions` was already empty BEFORE `resolve_small_regions` ever
            # ran — every SAM2-labeled pixel (including -1) fell outside
            # `base_valid` (background/enclosed). The min-detail floor had
            # nothing to do with this outcome, so the reason must not blame
            # it — see the sibling branch below for the case it actually did.
            return None, (
                f"SAM2 produced no usable regions ({raw_mask_count} raw "
                "masks, none of whose pixels intersected the design's "
                "foreground)"
            )
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
        split_tonal=split_tonal,
        shade_demand=shade_demand,
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
