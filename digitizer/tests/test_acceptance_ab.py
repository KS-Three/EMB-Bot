# digitizer/tests/test_acceptance_ab.py
"""The A/B harness's pure logic: variant matrix, sheet rows, and the job
stats `_job_stats` folds a finished job into. The wire calls are the probe
scripts' pattern and are exercised live, not here."""
from digitizer_core.tools_acceptance import variant_matrix, sheet_row
from tools.acceptance_ab import _job_stats

def test_variant_matrix_without_sam2_carries_both_routes():
    # SEVEN arms always. The toggle route now opens with the deconfounding
    # ladder — classical, then classical_prep (2026-08-23, prep alone, no
    # SAM2 venv needed) — followed by the shade-palette pair from
    # docs/superpowers/plans/2026-08-23-shade-palette-binding.md:
    # bound_shade (option (a): cfg.shade_palette_bind=True on the classical
    # route, nothing else) and bound_shade_demand (Kent's (a)+(b) decision,
    # 2026-08-23: the bind PLUS cfg.shade_palette_demand, which feeds
    # stage-2 proxy shade demand into select_palette so the palette holds
    # the anchors the bound shades need). Then relaxed, measured INERT on
    # this route and kept as the proof, and the default-route pair (stock +
    # relaxed), which is where the blend tier — and therefore the speckle
    # override Kent funded — actually lives: stage 0 sends real photos to
    # gradient, not photo_subject. Measured on the first real portraits
    # 2026-08-23.
    #
    # The shade pair sits AFTER the ladder rather than beside classical: the
    # ladder's adjacency is load-bearing for attributing prep vs SAM2, and
    # a two-column read against classical works from anywhere on the sheet.
    # bound_shade_demand sits directly after bound_shade so (b)'s own effect
    # reads as one column step off (a). Every pre-existing arm keeps its tag
    # and config.
    #
    # Every forced-class arm pins `shade_palette_bind` EXPLICITLY as of
    # 2026-08-24. Kent's ruling flipped that config default ON, so an arm
    # that inherited it would have changed meaning silently — `classical`
    # would have become a second `bound_shade` and the sheet would compare
    # the bound route against itself. The `default_*` pair deliberately does
    # NOT pin it: showing whatever the shipped default currently is, is the
    # entire reason that pair exists.
    assert variant_matrix(sam2_available=False) == [
        {"tag": "classical", "config": {"forced_class": "photo_subject",
                                        "shade_palette_bind": False}},
        {"tag": "classical_prep",
         "config": {"forced_class": "photo_subject", "photo_prep": True,
                    "shade_palette_bind": False}},
        {"tag": "bound_shade",
         "config": {"forced_class": "photo_subject",
                    "shade_palette_bind": True}},
        {"tag": "bound_shade_demand",
         "config": {"forced_class": "photo_subject",
                    "shade_palette_bind": True,
                    "shade_palette_demand": True}},
        {"tag": "bound_axis",
         "config": {"forced_class": "photo_subject",
                    "shade_palette_bind": True,
                    "shade_axis_normalize": True}},
        {"tag": "relaxed_speckle",
         "config": {"forced_class": "photo_subject",
                    "blend_speckle_r2_override": 0.5,
                    "shade_palette_bind": False}},
        {"tag": "default_stock", "config": {}},
        {"tag": "default_relaxed",
         "config": {"blend_speckle_r2_override": 0.5}},
    ]

def test_variant_matrix_with_sam2_adds_the_ab_arm():
    # 8 -> 9 with SAM2 (bound_axis landed 2026-08-24): three arms landed 2026-08-23 from separate lanes —
    # classical_prep (the deconfounding rung), bound_shade (the
    # shade-palette-bind experiment), and bound_shade_demand ((a)+(b), the
    # shade-aware palette). All are pinned above.
    m = variant_matrix(sam2_available=True)
    assert {"tag": "sam2", "config": {"forced_class": "photo_subject",
            "photo_prep": True, "photo_segment_sam2": True,
            "shade_palette_bind": False}} in m and len(m) == 9

def test_sam2_slots_in_as_the_ladders_third_rung():
    # The deconfounded attribution ladder (the classical_prep comment in
    # tools_acceptance.py carries the measured evidence): one flag flipped
    # per rung, adjacent on the sheet — prep's effect is column 2 minus
    # column 1, SAM2's own effect is column 3 minus column 2. Before
    # 2026-08-23 the sam2 arm's "vs classical" delta bundled both flags,
    # so the harness could not attribute either.
    m = variant_matrix(sam2_available=True)
    assert [v["tag"] for v in m[:3]] == ["classical", "classical_prep", "sam2"]

# --- the subject-cutout arm (2026-08-24) -------------------------------------

def test_subject_cutout_is_gated_on_the_isolated_rembg_venv():
    """Absent unless the caller says rembg can actually run — and the
    default is absent, which is what keeps every assertion above true.

    The gate is not caution, it is correctness: with the isolated venv
    missing, `photo_prep_background_removal` degrades to a documented
    no-op, so an ungated arm would produce a byte-identical copy of
    `classical_prep` under a tag promising a subject cutout. A column that
    silently measures nothing is worse than a missing one — it reads as
    'the cutout changed nothing'.
    """
    for m in (variant_matrix(sam2_available=False),
              variant_matrix(sam2_available=True),
              variant_matrix(sam2_available=True, rembg_available=False)):
        assert "subject_cutout" not in [v["tag"] for v in m]


def test_subject_cutout_carries_both_gates_of_the_double_gate():
    """`photo_prep_background_removal` rides ON TOP of `photo_prep` (that
    flag's own docstring): setting it alone does nothing at all, so the arm
    must set both or it is another silently-inert column."""
    m = variant_matrix(sam2_available=False, rembg_available=True)
    arm = next(v for v in m if v["tag"] == "subject_cutout")
    assert arm["config"] == {
        "forced_class": "photo_subject",
        "photo_prep": True,
        "photo_prep_background_removal": True,
        "shade_palette_bind": False,
    }


def test_subject_cutout_is_one_flag_from_its_control():
    """The attribution property, DERIVED from the matrix rather than
    restated: `classical_prep` is this arm's control, and the sheet can
    only attribute the delta to the cutout if exactly one flag separates
    them. Computed, so a future edit to either arm's config fails here
    instead of quietly making the comparison mean two things — the exact
    confound the ladder itself was added to repair.
    """
    m = variant_matrix(sam2_available=True, rembg_available=True)
    prep = next(v for v in m if v["tag"] == "classical_prep")["config"]
    cut = next(v for v in m if v["tag"] == "subject_cutout")["config"]
    differing = {k for k in set(prep) | set(cut)
                 if prep.get(k) != cut.get(k)}
    assert differing == {"photo_prep_background_removal"}


def test_subject_cutout_never_splits_the_attribution_ladder():
    """Placement, in both availability worlds. With SAM2 present the arm
    sits immediately AFTER the three-rung ladder (whose adjacency is
    load-bearing — see `test_sam2_slots_in_as_the_ladders_third_rung`);
    without it, the arm inherits the free slot directly beside the
    `classical_prep` it is one flag from."""
    with_sam2 = [v["tag"] for v in
                 variant_matrix(sam2_available=True, rembg_available=True)]
    assert with_sam2[:4] == ["classical", "classical_prep", "sam2",
                             "subject_cutout"]

    without = [v["tag"] for v in
               variant_matrix(sam2_available=False, rembg_available=True)]
    assert without[:3] == ["classical", "classical_prep", "subject_cutout"]


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
