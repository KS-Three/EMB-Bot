# digitizer/tests/test_acceptance_ab.py
"""The A/B harness's pure logic: variant matrix, sheet rows, and the job
stats `_job_stats` folds a finished job into. The wire calls are the probe
scripts' pattern and are exercised live, not here."""
from digitizer_core.tools_acceptance import variant_matrix, sheet_row
from tools.acceptance_ab import _job_stats

def test_variant_matrix_without_sam2_carries_both_routes():
    # SIX arms always. The toggle route now opens with the deconfounding
    # ladder — classical, then classical_prep (2026-08-23, prep alone, no
    # SAM2 venv needed) — followed by bound_shade, the shade-palette-bind
    # experiment's arm (docs/superpowers/plans/2026-08-23-shade-palette-
    # binding.md option (a): cfg.shade_palette_bind=True on the classical
    # route, nothing else). Then relaxed, measured INERT on this route and
    # kept as the proof, and the default-route pair (stock + relaxed), which
    # is where the blend tier — and therefore the speckle override Kent
    # funded — actually lives: stage 0 sends real photos to gradient, not
    # photo_subject. Measured on the first real portraits 2026-08-23.
    #
    # bound_shade sits AFTER the ladder rather than beside classical: the
    # ladder's adjacency is load-bearing for attributing prep vs SAM2, and
    # a two-column read against classical works from anywhere on the sheet.
    # Every pre-existing arm keeps its tag and config.
    assert variant_matrix(sam2_available=False) == [
        {"tag": "classical", "config": {"forced_class": "photo_subject"}},
        {"tag": "classical_prep",
         "config": {"forced_class": "photo_subject", "photo_prep": True}},
        {"tag": "bound_shade",
         "config": {"forced_class": "photo_subject",
                    "shade_palette_bind": True}},
        {"tag": "relaxed_speckle",
         "config": {"forced_class": "photo_subject",
                    "blend_speckle_r2_override": 0.5}},
        {"tag": "default_stock", "config": {}},
        {"tag": "default_relaxed",
         "config": {"blend_speckle_r2_override": 0.5}},
    ]

def test_variant_matrix_with_sam2_adds_the_ab_arm():
    # 6 -> 7 with SAM2: two arms landed the same day from separate lanes —
    # classical_prep (the deconfounding rung) and bound_shade (the
    # shade-palette-bind experiment). Both are pinned above.
    m = variant_matrix(sam2_available=True)
    assert {"tag": "sam2", "config": {"forced_class": "photo_subject",
            "photo_prep": True, "photo_segment_sam2": True}} in m and len(m) == 7

def test_sam2_slots_in_as_the_ladders_third_rung():
    # The deconfounded attribution ladder (the classical_prep comment in
    # tools_acceptance.py carries the measured evidence): one flag flipped
    # per rung, adjacent on the sheet — prep's effect is column 2 minus
    # column 1, SAM2's own effect is column 3 minus column 2. Before
    # 2026-08-23 the sam2 arm's "vs classical" delta bundled both flags,
    # so the harness could not attribute either.
    m = variant_matrix(sam2_available=True)
    assert [v["tag"] for v in m[:3]] == ["classical", "classical_prep", "sam2"]

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
