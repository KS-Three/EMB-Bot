"""The Task-1 hard invariant: extracting `stage2_photo_segment.segment()`'s
`kept regions -> Quant` tail into the shared `kept_masks_to_quant()` must not
move ONE pixel or ONE label on the classical SLIC+RAG lane.

`testdata/photo_lane_segment_golden.json` is captured by
`tools/capture_photo_lane_golden.py`, run once BEFORE the extraction lands.
This module re-runs the same fixtures through today's `segment()` and asserts
an exact match on the full `Quant`: the label array's sha256, the thread
index list, the pre-snap cluster colors, and every warning dict.

SCOPE, deliberately narrow (the lesson `tests/test_shapefield_byte_identical.py`
records in its own HISTORY section): this golden pins STAGE 2's output only,
not the whole pipeline's. A frozen whole-pipeline snapshot goes stale the
first time anything downstream legitimately changes, and then tests
"nothing anywhere ever changes" instead of the claim it was written for.
Stage 2's own output moving IS this file's claim, so it only goes red for a
real stage-2 change — at which point the change's author re-runs the capture
script deliberately, the same way `testdata/flat_lane_golden.json` documents
its own two deliberate re-captures.

If this goes red during the extraction, the extraction is wrong — not this
test.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import segment

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
GOLDEN_PATH = TESTDATA / "photo_lane_segment_golden.json"

# Every committed fixture that can route through `segment()`, chosen for
# structural variety rather than count: two real busy gradient designs (the
# pair `MERGE_DELTAE00_THRESH` was itself tuned against), the synthetic blob
# fixture, a fur ramp, the enclosed-white-icon repro (the ONLY fixture that
# exercises the tail's separate enclosed population), and a photo-class stub.
# The trailing "#bgmask" key re-runs one fixture with a real `bg_mask`
# argument so the tail's `_region_classes` subject/background branch — and
# therefore `palette.region_weight`'s class multipliers — is covered too.
FIXTURES = [
    "photo/drone_render.png",
    "photo/summit_badge.png",
    "photo/region_blobs.png",
    "photo/fur_ramp.png",
    "photo/repro_gradient_white_icon.png",
    "photo/photo_subject_stub.png",
    "photo/region_blobs.png#bgmask",
]

GOLDEN: dict = (
    json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if GOLDEN_PATH.is_file()
    else {}
)


def _jsonable(value):
    """numpy scalars/arrays out of the warning dicts become plain JSON."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _synthetic_bg_mask(shape: tuple[int, int]) -> np.ndarray:
    """A deterministic stand-in for a real rembg subject/background mask:
    the left half is background. Nothing about it needs to be plausible —
    it exists so the tail's class-weight branch runs on a fixed input."""
    mask = np.zeros(shape, bool)
    mask[:, : shape[1] // 2] = True
    return mask


def _snapshot(key: str) -> dict:
    name, _, variant = key.partition("#")
    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(TESTDATA / name, cfg)
    bg_mask = _synthetic_bg_mask(p.rgb.shape[:2]) if variant == "bgmask" else None
    q = segment(p, cfg, face_regions=None, bg_mask=bg_mask)
    return {
        "shape": list(q.labels.shape),
        "labels_dtype": str(q.labels.dtype),
        "labels_sha256": hashlib.sha256(
            np.ascontiguousarray(q.labels, dtype=np.int32).tobytes()
        ).hexdigest(),
        "thread_indices": [int(i) for i in q.thread_indices],
        "cluster_rgb": [
            [round(float(v), 6) for v in row]
            for row in np.asarray(q.cluster_rgb, np.float64).reshape(-1, 3)
        ],
        "warnings": [_jsonable(w) for w in q.warnings],
    }


@pytest.mark.parametrize("fixture", FIXTURES)
def test_photo_lane_stage2_is_byte_identical_to_the_pre_refactor_golden(fixture):
    assert GOLDEN, f"{GOLDEN_PATH} missing — run tools/capture_photo_lane_golden.py"
    assert _snapshot(fixture) == GOLDEN[fixture]


def test_golden_file_actually_covers_something():
    """A guard against the golden silently becoming empty (a capture-script
    bug) and this whole module passing vacuously — the same guard
    tests/test_flat_lane_byte_identical.py keeps over its own golden."""
    assert sorted(GOLDEN.keys()) == sorted(FIXTURES)
    for name, snap in GOLDEN.items():
        assert snap["thread_indices"], f"{name}: golden has zero thread colors"
        assert snap["warnings"], f"{name}: golden has zero warnings"
