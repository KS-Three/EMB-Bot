# digitizer/tests/test_acceptance_ab.py
"""The A/B harness's pure logic: variant matrix, sheet rows, and the job
stats `_job_stats` folds a finished job into. The wire calls are the probe
scripts' pattern and are exercised live, not here."""
from digitizer_core.tools_acceptance import variant_matrix, sheet_row
from tools.acceptance_ab import _job_stats

def test_variant_matrix_without_sam2_is_classical_plus_relaxed_speckle():
    # The relaxed-speckle arm rides every run (Kent's 2026-08-23 funding of
    # the speckle A/B); stock classical stays first so the comparison
    # column is always present.
    assert variant_matrix(sam2_available=False) == [
        {"tag": "classical", "config": {"forced_class": "photo_subject"}},
        {"tag": "relaxed_speckle",
         "config": {"forced_class": "photo_subject",
                    "blend_speckle_r2_override": 0.5}},
    ]

def test_variant_matrix_with_sam2_adds_the_ab_arm():
    m = variant_matrix(sam2_available=True)
    assert {"tag": "sam2", "config": {"forced_class": "photo_subject",
            "photo_prep": True, "photo_segment_sam2": True}} in m and len(m) == 3

def test_sheet_row_carries_counts_not_scores():
    row = sheet_row("dog.jpg", "classical",
                    {"shapes": 30, "stitches": 12000, "trims": 40,
                     "threads": 9, "warnings": ["photo_auto_tier"], "wall_s": 14.2})
    assert "score" not in row and row["threads"] == 9


def test_job_stats_does_not_count_a_missing_thread_index_as_a_phantom_thread():
    """F5: `{s.get("thread_index") for s in shapes}` folded a shape with no
    `thread_index` key into the set as `None` -- one phantom "thread" on top
    of every real one whenever a review shape was missing the field."""
    job = {
        "review": {"shapes": [
            {"thread_index": 0}, {"thread_index": 0}, {"thread_index": 1},
            {"shape_id": "no_thread_index_here"},
        ]},
        "design": {"stitchCount": 100},
        "stats": {"trims": 2},
        "warnings": [],
    }
    stats = _job_stats(job, wall_s=1.0)
    assert stats["threads"] == 2, (
        "a shape missing thread_index must not add a phantom thread")
