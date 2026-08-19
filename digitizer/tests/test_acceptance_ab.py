# digitizer/tests/test_acceptance_ab.py
"""The A/B harness's pure logic: variant matrix and sheet rows. The wire
calls are the probe scripts' pattern and are exercised live, not here."""
from digitizer_core.tools_acceptance import variant_matrix, sheet_row

def test_variant_matrix_without_sam2_is_classical_only():
    assert variant_matrix(sam2_available=False) == [
        {"tag": "classical", "config": {"forced_class": "photo_subject"}},
    ]

def test_variant_matrix_with_sam2_adds_the_ab_arm():
    m = variant_matrix(sam2_available=True)
    assert {"tag": "sam2", "config": {"forced_class": "photo_subject",
            "photo_prep": True, "photo_segment_sam2": True}} in m and len(m) == 2

def test_sheet_row_carries_counts_not_scores():
    row = sheet_row("dog.jpg", "classical",
                    {"shapes": 30, "stitches": 12000, "trims": 40,
                     "threads": 9, "warnings": ["photo_auto_tier"], "wall_s": 14.2})
    assert "score" not in row and row["threads"] == 9
