"""`textcluster.ocr_suggest_text` — the per-member OCR read that feeds
Studio's "Convert to text" prefill (module docstring's "OCR-suggested text"
section).

Fixtures are REAL, OCR-legible letterforms, not the bare-rectangle stand-ins
`test_textcluster.py` uses for the geometric layer (Tesseract has no opinion
about a plain rectangle either way — see that file's own module comment).
Rather than depending on a system font file being present and predictable
across every machine and CI runner this repo's tests run on, each letter is
built as a small union of grid cells (a classic 5x7 dot-matrix block-letter
definition) — self-contained, deterministic, no external font dependency.
Same technique `text-cluster-ocr-confidence-gate`'s `test_ocr_gate.py` uses
for the same reason (a parallel, independently-scoped effort — see
`textcluster.py`'s module docstring).
"""
from __future__ import annotations

import shutil
from unittest.mock import patch

import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.textcluster import _ocr_glyph_guess, ocr_suggest_text

_P = Prep(rgb=None, bg_mask=None, px_per_mm=1.0, art_bbox=(0, 0, 1, 1))

# Classic 5x7 dot-matrix block-letter patterns.
_PATTERNS = {
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
}


def _block_letter_polygon(ch: str, cap_mm: float = 1.8) -> Polygon:
    pattern = _PATTERNS[ch]
    rows = len(pattern)
    cell = cap_mm / rows
    boxes = [box(cx * cell, ry * cell, (cx + 1) * cell, (ry + 1) * cell)
              for ry, row in enumerate(pattern) for cx, bit in enumerate(row) if bit == "1"]
    poly = unary_union(boxes)
    assert poly.geom_type == "Polygon", f"{ch}'s grid cells must all be edge-connected"
    return poly


def _region(shape_id: str, poly: Polygon, tagged: bool = True) -> Region:
    meta = {"text_cluster_id": "TCsuggest"} if tagged else {}
    return Region(shape_id=shape_id, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=poly.area, meta=meta)


def test_untagged_region_gets_no_new_meta_keys():
    """Same "absent means false, never an explicit sentinel" convention
    `text_candidate` already follows: a region that was never tagged a text
    cluster member is left completely alone by this pass."""
    r = _region("A", _block_letter_polygon("T"), tagged=False)
    ocr_suggest_text([r], _P)
    assert "ocr_char" not in r.meta
    assert "ocr_confidence" not in r.meta


@pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="needs the real tesseract binary on PATH (CI installs tesseract-ocr)")
def test_tagged_member_gets_a_real_ocr_read_stamped():
    """A real, clean, legible letterform reads back its own character with a
    real (measured, not mocked) Tesseract call — the actual end-to-end path
    Studio's "Convert to text" prefill depends on."""
    r = _region("T", _block_letter_polygon("T"))
    ocr_suggest_text([r], _P)
    assert r.meta["ocr_char"] == "T"
    assert isinstance(r.meta["ocr_confidence"], float)
    assert r.meta["ocr_confidence"] > 50.0, \
        f"a clean block-letter T should read with real confidence, got {r.meta['ocr_confidence']}"


@pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="needs the real tesseract binary on PATH (CI installs tesseract-ocr)")
def test_multiple_tagged_members_each_get_their_own_independent_read():
    t = _region("T", _block_letter_polygon("T"))
    l = _region("L", _block_letter_polygon("L"))
    ocr_suggest_text([t, l], _P)
    assert t.meta["ocr_char"] == "T"
    assert l.meta["ocr_char"] == "L"


def test_measurement_failure_stamps_none_for_both_fields_not_a_crash():
    """Tesseract erroring (missing binary, any runtime failure) must fail
    open exactly like every other uncertain case in this module: both
    fields read `None` (this pass's "I don't know," matching
    `_ocr_glyph_guess`'s own contract), never an exception that would take
    the whole pipeline down with it."""
    r = _region("T", _block_letter_polygon("T"))
    with patch("digitizer_core.textcluster.pytesseract.image_to_data",
               side_effect=RuntimeError("tesseract not found")):
        ocr_suggest_text([r], _P)
    assert r.meta["ocr_char"] is None
    assert r.meta["ocr_confidence"] is None


def test_degenerate_polygon_stamps_none_for_both_fields():
    """A polygon that rasterizes to nothing (mirrors `build_shape_field`'s
    own degenerate guard) is a measurement failure, not a zero-confidence
    read — `_ocr_raster` returns `None` before Tesseract is ever called."""
    ring = [(0, 0), (1, 0), (1, 1), (0, 1)]
    poly = Polygon(ring, [ring])  # a shell exactly cancelled by its own hole
    r = _region("Z", poly)
    ocr_suggest_text([r], _P)
    assert r.meta["ocr_char"] is None
    assert r.meta["ocr_confidence"] is None


def test_no_detected_text_reads_as_zero_confidence_not_none():
    """An empty `conf`/`text` result (Tesseract ran, found nothing) is a
    real, low measurement — 0.0, the metric's floor — not the same as a
    measurement FAILING outright. This is the one case where `character` is
    `None` (nothing detected) but `confidence` is a real `0.0`, not `None`
    — the two fields' "I don't know" cases are not identical, see
    `_ocr_glyph_guess`'s own docstring."""
    with patch("digitizer_core.textcluster.pytesseract.image_to_data",
               return_value={"conf": ["-1", "-1"], "text": ["", ""]}):
        char, confidence = _ocr_glyph_guess(_block_letter_polygon("T"))
    assert char is None
    assert confidence == 0.0


def test_ocr_char_is_truncated_to_a_single_character():
    """`_ocr_glyph_guess` must never hand back more than one character even
    if Tesseract's own token happens to be longer than one glyph (stray
    multi-character detection on a single-glyph crop) — the Studio-side
    concatenation (`digitizer.js`'s `textClusterSeed`) assumes one member
    contributes exactly one character to the suggested word."""
    with patch("digitizer_core.textcluster.pytesseract.image_to_data",
               return_value={"conf": ["91"], "text": ["TT"]}):
        char, confidence = _ocr_glyph_guess(_block_letter_polygon("T"))
    assert char == "T"
    assert confidence == 91.0


def test_ocr_suggest_never_mutates_the_polygon_itself():
    """This pass is read-only metadata, same discipline as
    `text_candidate`/`text_cluster_id` — unlike `regularize_text_clusters`
    immediately before it in the pipeline, it must never touch
    `region.polygon` or `region.area_mm2`."""
    r = _region("T", _block_letter_polygon("T"))
    original_coords = list(r.polygon.exterior.coords)
    original_area = r.area_mm2
    ocr_suggest_text([r], _P)
    assert list(r.polygon.exterior.coords) == original_coords
    assert r.area_mm2 == original_area
