"""`textcluster`'s OCR-confidence quality gate (module docstring's
"OCR-confidence quality gate" section) — the additional safety layer on top
of `_REGULARIZE_SKIP_TOLERANCE`/hole-preservation from
`tests/test_textcluster.py`'s own "Selective regularization" section.

Fixtures here are REAL, OCR-legible letterforms, not the bare-rectangle
stand-ins `test_textcluster.py` uses for the geometric layer (Tesseract has
no opinion about a plain rectangle either way — see that file's own module
comment). Rather than depending on a system font file being present and
predictable across every machine and CI runner this repo's tests run on,
each letter is built as a small union of grid cells (a classic 5x7
dot-matrix block-letter definition) — self-contained, deterministic, no
external font dependency, and (fittingly for an embroidery digitizer) itself
a real multi-stroke letterform with corners and crossbars, not a blob.

Both regression cases below were measured directly (not assumed) with the
real Tesseract binary installed in this environment, at generous margins
either side of `_OCR_CONFIDENCE_DROP_THRESHOLD` (20.0 points) so ordinary
Tesseract version drift across machines/CI runners is very unlikely to flip
either outcome:

- **"T" (regularization is fine): 93.0 -> 92.0, a 1-point drop.** The
  skeleton buffer redraws it, same as before this gate existed, because 1
  point is nowhere near the 20-point floor.
- **"I" (regularization visibly damages it): 92.0 -> 0.0, a 92-point
  drop.** Buffering an "I" this way collapses the vertical bar's two serif
  caps into the stem, and Tesseract goes from reading it confidently to not
  finding any text in the crop at all. The gate discards the buffer and
  falls back to the original polygon, exactly like `buffer_failed`.
"""
from __future__ import annotations

import shutil
from unittest.mock import patch

import numpy as np
import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.textcluster import (
    _OCR_CONFIDENCE_DROP_THRESHOLD,
    _ocr_confidence,
    _ocr_regularization_hurts_legibility,
    regularize_text_clusters,
)

_P = Prep(rgb=None, bg_mask=None, px_per_mm=1.0, art_bbox=(0, 0, 1, 1))

# Classic 5x7 dot-matrix block-letter patterns -- see module docstring for
# why hand-built rather than font-rendered.
_PATTERNS = {
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
}

# The cluster target (mm, a stroke HALF-width — see textcluster.py's module
# docstring for why) both fixtures below are regularized against. Chosen,
# and confirmed by direct measurement (this file's own docstring), to sit
# far enough from each letter's own perturbed stroke width that BOTH clear
# `_REGULARIZE_SKIP_TOLERANCE` and reach the OCR gate — the geometric
# skip/hole checks are `test_textcluster.py`'s job, not this file's.
_TARGET_STROKE_MM = 0.1542


def _block_letter_polygon(ch: str, cap_mm: float = 1.8) -> Polygon:
    pattern = _PATTERNS[ch]
    rows = len(pattern)
    cell = cap_mm / rows
    boxes = [box(cx * cell, ry * cell, (cx + 1) * cell, (ry + 1) * cell)
              for ry, row in enumerate(pattern) for cx, bit in enumerate(row) if bit == "1"]
    poly = unary_union(boxes)
    assert poly.geom_type == "Polygon", f"{ch}'s grid cells must all be edge-connected"
    return poly


def _tagged_member(shape_id: str, poly: Polygon) -> Region:
    return Region(shape_id=shape_id, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=poly.area,
                  meta={"rescued_small_shape": True, "text_cluster_id": "TCgate",
                        "text_cluster_stroke_mm": _TARGET_STROKE_MM})


def test_regularization_fine_gate_does_not_fire():
    """"T", thinned (buffer -0.03 mm) enough to clear
    `_REGULARIZE_SKIP_TOLERANCE` against `_TARGET_STROKE_MM` — it genuinely
    reaches the buffer step, not skipped by the existing geometric checks.
    Measured real OCR confidence drop is 1 point (93.0 -> 92.0), nowhere
    near `_OCR_CONFIDENCE_DROP_THRESHOLD` (20.0): the gate must not block
    it, and the skeleton-buffer redraw must go through exactly as it did
    before this layer existed."""
    poly = _block_letter_polygon("T").buffer(-0.03, join_style=2)
    r = _tagged_member("T", poly)
    original_coords = list(r.polygon.exterior.coords)

    regularize_text_clusters([r], _P)

    assert not r.meta.get("text_cluster_regularize_skipped"), (
        "a member whose OCR confidence barely moves must still regularize; "
        f"skip_reason={r.meta.get('text_cluster_regularize_skip_reason')}"
    )
    assert list(r.polygon.exterior.coords) != original_coords, \
        "the skeleton buffer must actually have replaced the polygon"


# Only this test skips without the binary: it needs Tesseract to actually
# REPORT the 92-point confidence drop for the gate to fire. Its sibling above
# stays un-marked on purpose — without Tesseract the gate fails open (see
# test_gate_never_fires_when_ocr_is_unavailable) and the skeleton-buffer
# redraw it asserts still goes through.
@pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="needs the real tesseract binary on PATH (CI installs tesseract-ocr)")
def test_regularization_damaging_gate_falls_back_to_original():
    """"I", thickened (buffer +0.06 mm) enough to clear
    `_REGULARIZE_SKIP_TOLERANCE` the same way. Measured real OCR confidence
    drop is 92 points (92.0 -> 0.0, Tesseract finds no text at all in the
    buffered crop): the gate must discard the buffer and leave the ORIGINAL
    polygon completely untouched, the same fail-open contract
    `buffer_failed` already uses."""
    poly = _block_letter_polygon("I").buffer(0.06, join_style=2)
    r = _tagged_member("I", poly)
    original_coords = list(r.polygon.exterior.coords)

    regularize_text_clusters([r], _P)

    assert r.meta.get("text_cluster_regularize_skipped") is True
    assert r.meta.get("text_cluster_regularize_skip_reason") == "ocr_confidence_drop"
    assert list(r.polygon.exterior.coords) == original_coords, \
        "a gated regularization must leave the polygon byte-identical"


def test_gate_never_fires_when_ocr_is_unavailable():
    """If Tesseract can't be measured at all (missing binary, any runtime
    error) `_ocr_confidence` returns `None` for both crops, and the gate
    must fail open exactly like every other uncertain case in this module —
    NOT block a regularization that, absent this new layer, would have gone
    through cleanly. This is what keeps the OCR gate an ADDITIONAL layer:
    an environment without Tesseract must behave exactly like this layer
    doesn't exist, not like it blocks everything."""
    with patch("digitizer_core.textcluster._ocr_confidence", return_value=None):
        assert _ocr_regularization_hurts_legibility(
            _block_letter_polygon("I"), _block_letter_polygon("T")) is False


def test_gate_fires_exactly_at_the_threshold_boundary():
    """Pins the exact comparison (`>=`, not `>`) with mocked confidence
    values -- deterministic, independent of any real OCR reading, so this
    one bit of control flow stays pinned even if Tesseract's own numbers
    ever drift on some other machine."""
    with patch("digitizer_core.textcluster._ocr_confidence",
               side_effect=[80.0, 80.0 - _OCR_CONFIDENCE_DROP_THRESHOLD]):
        assert _ocr_regularization_hurts_legibility(
            _block_letter_polygon("I"), _block_letter_polygon("T")) is True

    with patch("digitizer_core.textcluster._ocr_confidence",
               side_effect=[80.0, 80.0 - _OCR_CONFIDENCE_DROP_THRESHOLD + 0.1]):
        assert _ocr_regularization_hurts_legibility(
            _block_letter_polygon("I"), _block_letter_polygon("T")) is False


def test_ocr_confidence_never_reads_the_decoded_text_field():
    """Proves the "never touch decoded text" contract by construction, not
    just by code inspection: `pytesseract.image_to_data`'s return value is
    replaced with a dict subclass that RAISES if anything ever reads its
    "text" key. `_ocr_confidence` must still return a plain float
    (`data["conf"]` is legitimate to read) without ever touching "text"."""

    class _TextTripwire(dict):
        def __getitem__(self, key):
            if key == "text":
                raise AssertionError(
                    "decoded OCR text must never be read by _ocr_confidence")
            return dict.__getitem__(self, key)

    fake_data = _TextTripwire(
        conf=[91.0, 88.0],
        text=["classified", "do-not-store-this"],  # must never be touched
    )
    with patch("digitizer_core.textcluster.pytesseract.image_to_data", return_value=fake_data):
        conf = _ocr_confidence(_block_letter_polygon("T"))

    assert isinstance(conf, float)
    assert conf == pytest.approx(89.5)


def test_ocr_confidence_treats_no_detected_text_as_zero_not_none():
    """An empty `conf` list (Tesseract found nothing worth a confidence
    value) is a real, low measurement -- 0.0, the metric's floor -- not
    `None` (this function's ONLY "couldn't measure at all" signal). See the
    module docstring for why that distinction matters: `None` from BOTH
    sides makes the gate's drop-check unreachable (fails open), so
    collapsing a real "nothing recognized" reading into `None` would let a
    catastrophically bad redraw slip past the gate instead of triggering
    it."""
    with patch("digitizer_core.textcluster.pytesseract.image_to_data",
               return_value={"conf": ["-1", "-1"], "text": ["", ""]}):
        conf = _ocr_confidence(_block_letter_polygon("I"))
    assert conf == 0.0
