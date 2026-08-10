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
