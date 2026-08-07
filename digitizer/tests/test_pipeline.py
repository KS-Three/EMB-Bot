"""End-to-end contract invariants: determinism, palette integrity, ID carry-forward."""
import copy

import numpy as np

from digitizer_core import PipelineConfig, run_stages
from digitizer_core.regions import match_shape_ids

from .conftest import TESTDATA, cfg


def fingerprint(result) -> list[tuple[str, str, float]]:
    return [(r.shape_id, r.thread_number, round(r.area_mm2, 3)) for r in result.regions]


def test_two_runs_of_the_same_input_are_identical():
    a = run_stages(TESTDATA / "logo_whitebg.png", cfg())
    b = run_stages(TESTDATA / "logo_whitebg.png", cfg())
    assert fingerprint(a) == fingerprint(b)
    assert a.palette == b.palette
    assert [w["code"] for w in a.warnings] == [w["code"] for w in b.warnings]


def test_bytes_and_path_inputs_agree():
    from_path = run_stages(TESTDATA / "logo_whitebg.png", cfg())
    from_bytes = run_stages((TESTDATA / "logo_whitebg.png").read_bytes(), cfg())
    assert fingerprint(from_path) == fingerprint(from_bytes)


def test_palette_never_lists_a_thread_with_nothing_to_sew(whitebg, alpha, uncertain):
    # Regression: a mask survived segmentation, was dropped during
    # simplification, and left its thread in the palette — sending the
    # operator to the rack for a cone the design never uses.
    for result in (whitebg, alpha, uncertain):
        layers = {r.meta["layer"] for r in result.regions}
        assert len(result.palette) == len(layers)
        assert layers == set(range(len(result.palette)))


def test_every_region_thread_matches_its_palette_entry(whitebg):
    for r in whitebg.regions:
        assert whitebg.palette[r.meta["layer"]]["number"] == r.thread_number


def test_warnings_are_machine_readable_and_deduplicated(whitebg):
    seen = set()
    for w in whitebg.warnings:
        assert w["code"] == w["code"].upper()
        assert w["message"] and isinstance(w["message"], str)
        assert w["code"] not in seen, f"duplicate warning code {w['code']}"
        seen.add(w["code"])


def test_shape_ids_survive_a_boundary_change(whitebg, alpha):
    # The alpha fixture is the same artwork with slightly different edges —
    # a stand-in for the SAM segmenter refining boundaries in build step 2.
    # deleted_shape_ids round-trips through these IDs, so they must not churn.
    #
    # The one region excluded from this comparison: BACKGROUND_ENCLOSED's
    # ring-hole region. `match_shape_ids` only matches within the SAME
    # thread, correctly — but a fully-transparent alpha pixel carries no
    # real color (this fixture's underlying RGB there is (0,0,0), an
    # artifact of how the PNG was authored, not visible content), so it
    # quantizes to a different spool ("Black") than the opaque whitebg
    # variant's actual white icon linework ("White"). Two different colors
    # correctly not matching is not an ID-carry-forward bug; it is this
    # specific fixture pair's alpha channel carrying no meaningful color
    # under full transparency.
    current = copy.deepcopy(alpha.regions)
    match_shape_ids(whitebg.regions, current)
    carried = {r.shape_id for r in current if not r.meta.get("enclosed_background")}
    original = {
        r.shape_id for r in whitebg.regions if not r.meta.get("enclosed_background")
    }
    assert carried == original, "IDs failed to carry across a boundary change"


def test_a_moved_shape_gets_a_new_id_rather_than_stealing_one(whitebg):
    from shapely.affinity import translate

    moved = copy.deepcopy(whitebg.regions)
    for r in moved:
        r.polygon = translate(r.polygon, xoff=40.0)  # far beyond the tolerance
        r.shape_id = "TEMP-" + r.shape_id
    match_shape_ids(whitebg.regions, moved)
    assert all(r.shape_id.startswith("TEMP-") for r in moved)


def test_target_size_drives_the_output_size():
    small = run_stages(TESTDATA / "logo_whitebg.png", cfg(target_width_mm=40.0))
    big = run_stages(TESTDATA / "logo_whitebg.png", cfg(target_width_mm=120.0))
    assert abs(small.design_size_mm[0] - 40.0) < 0.5
    assert abs(big.design_size_mm[0] - 120.0) < 0.5

    # A shape present at both sizes scales with the square of the linear
    # factor (40 -> 120 mm is 3x linear, 9x area).
    def area_of(result, number):
        return next(r.area_mm2 for r in result.regions if r.thread_number == number)

    ratio = area_of(big, "1704") / area_of(small, "1704")
    assert 8.0 < ratio < 10.0, ratio


def test_minimum_detail_is_physical_so_size_changes_what_survives():
    # min_detail_mm is a MACHINE constraint (1.5 mm), not an image constant:
    # the fixture's ~1 mm features are unsewable on a 40 mm design and
    # genuinely sewable on a 120 mm one. Region counts therefore must NOT be
    # scale-invariant — asserting they were is how this behavior got noticed.
    small = run_stages(TESTDATA / "logo_whitebg.png", cfg(target_width_mm=40.0))
    big = run_stages(TESTDATA / "logo_whitebg.png", cfg(target_width_mm=120.0))
    assert len(big.regions) > len(small.regions)
    # The tiny teal patch is one of them: dropped small, sewable big.
    assert not any(r.thread_number == "4531" for r in small.regions)
    assert any(r.thread_number == "4531" for r in big.regions)


def test_pipeline_reports_its_segmenter_and_scale(whitebg):
    assert whitebg.segmenter == "classical"
    assert whitebg.px_per_mm > 0
    assert whitebg.background.stitched is False


# --- text-cluster detection wiring (Step 3) --------------------------------


def test_full_pipeline_tags_a_text_cluster_on_the_benchmark_subline():
    """`detect_text_clusters` is wired into `run_stages` right after
    `tag_enclosed_background` (`pipeline.py`). This is the plan's acceptance
    bar for that wiring step: the FULL pipeline, not the module in isolation,
    must tag a shared `text_cluster_id` across several rescued shapes on the
    real benchmark fixture — `testdata/photo/enthusiast_logo.png`'s
    "ENTERPRISES INC." subline (`test_run_tier.py`'s docstring; the subline
    is a real logo's independently-rescued sub-detail glyphs, exactly the
    shape this detector exists for), at its documented benchmark size, 90 mm.
    """
    result = run_stages(TESTDATA / "photo" / "enthusiast_logo.png",
                         cfg(target_width_mm=90.0))

    rescued = [r for r in result.regions if r.meta.get("rescued_small_shape")]
    assert rescued, "the benchmark fixture must still rescue its subline glyphs"

    tagged = [r for r in result.regions if r.meta.get("text_cluster_id")]
    assert tagged, "the wired pipeline must tag at least one text cluster"

    cluster_ids = {r.meta["text_cluster_id"] for r in tagged}
    # One dominant cluster is the documented real-world shape of this fixture
    # (the subline reads as one word) — assert the actual shape_id evidence,
    # not just that tagging happened somewhere.
    biggest_id = max(cluster_ids, key=lambda cid: sum(
        1 for r in tagged if r.meta["text_cluster_id"] == cid))
    members = {r.shape_id for r in tagged if r.meta["text_cluster_id"] == biggest_id}
    assert len(members) >= 10, (
        f"expected most of the subline's rescued glyphs in one cluster, got "
        f"{len(members)} member shape_ids: {sorted(members)}"
    )
    # Every member of that cluster must actually be a rescued shape and carry
    # a real stroke-width value (not just the id) — the detector's own
    # contract per `textcluster.py`.
    for r in tagged:
        if r.meta["text_cluster_id"] == biggest_id:
            assert r.meta.get("rescued_small_shape") is True
            assert r.meta.get("text_candidate") is True
            assert isinstance(r.meta.get("text_cluster_stroke_mm"), float)


# --- regularization wiring (Step 5) -----------------------------------------


def _biggest_cluster_strokes(result):
    """shape_id -> own-skeleton stroke half-width (mm) for every member of
    the biggest tagged cluster in a `run_stages` result."""
    from digitizer_core.textcluster import _stroke_stats_mm

    tagged = [r for r in result.regions if r.meta.get("text_cluster_id")]
    by_cluster: dict[str, list] = {}
    for r in tagged:
        by_cluster.setdefault(r.meta["text_cluster_id"], []).append(r)
    biggest = max(by_cluster.values(), key=len)
    return {r.shape_id: _stroke_stats_mm(r) for r in biggest}


def test_full_pipeline_regularization_reduces_stroke_width_variance_on_benchmark_subline():
    """`regularize_text_clusters` is wired into `run_stages` right after
    `detect_text_clusters` (`pipeline.py`). This is Step 5's acceptance bar,
    at the full-pipeline level rather than the module in isolation: on the
    real benchmark fixture, the biggest tagged cluster's members' individual
    stroke-width variance must be LOWER with regularization wired in than
    without it — measured from the actual emitted `Region` polygons of two
    real pipeline runs, not from the unit-level synthetic fixture.

    The "before" run patches `regularize_text_clusters` to a no-op at its
    `pipeline` call site (rather than reverting the wiring by hand) so it
    exercises the exact same code path up to that point, including
    `detect_text_clusters`'s tagging — the only difference between the two
    runs is whether Step 5's geometry replacement happened. shape_ids are
    unaffected by that patch (assigned earlier, in `vectorize`), so the two
    runs' cluster members line up 1:1 by shape_id.

    The "after" run also patches the OCR-confidence gate
    (`textcluster._ocr_regularization_hurts_legibility`) to a permissive
    no-op, to isolate what THIS test is about — the skeleton-buffer layer's
    wiring — from that separate, later safety layer. On this real fixture
    the gate legitimately blocks the ONE member the un-gated buffer would
    otherwise replace (measured OCR confidence 77.0 -> 0.0, see
    `textcluster.py`'s module docstring), which is that layer doing its job
    correctly, not a regression in this one; `test_ocr_gate.py` covers that
    real block directly, on this same fixture and member.
    """
    from unittest.mock import patch

    with patch("digitizer_core.pipeline.regularize_text_clusters",
               lambda regions, p: None):
        before_result = run_stages(TESTDATA / "photo" / "enthusiast_logo.png",
                                    cfg(target_width_mm=90.0))
    with patch("digitizer_core.textcluster._ocr_regularization_hurts_legibility",
               return_value=False):
        after_result = run_stages(TESTDATA / "photo" / "enthusiast_logo.png",
                                   cfg(target_width_mm=90.0))

    before = _biggest_cluster_strokes(before_result)
    after = _biggest_cluster_strokes(after_result)

    shared_ids = set(before) & set(after)
    assert len(shared_ids) >= 10, (
        "the two runs' biggest clusters must line up on (most of) the same "
        f"shape_ids: before={sorted(before)}, after={sorted(after)}"
    )

    before_vals = [before[sid] for sid in shared_ids]
    after_vals = [after[sid] for sid in shared_ids]
    assert all(v is not None for v in before_vals)
    assert all(v is not None for v in after_vals)

    before_var = float(np.var(before_vals))
    after_var = float(np.var(after_vals))
    assert after_var < before_var, (
        f"regularization must reduce stroke-width variance on the real "
        f"fixture: before={before_vals} (var={before_var:.6g}), "
        f"after={after_vals} (var={after_var:.6g})"
    )


# --- OCR-suggested text wiring -----------------------------------------------


def test_full_pipeline_stamps_ocr_fields_on_the_benchmark_subline():
    """`ocr_suggest_text` is wired into `run_stages` right after
    `regularize_text_clusters` (`pipeline.py`). This is that wiring step's
    acceptance bar: on the real benchmark fixture, every member of the
    biggest tagged cluster ("ENTERPRISES INC.") must come back from the
    FULL pipeline with both OCR fields present (not just the module in
    isolation) -- `ocr_char` is `None` or a single character, `ocr_confidence`
    is `None` or a float in Tesseract's own 0..100 range. This is a wiring
    check (the fields exist and are well-formed), not a legibility
    assertion -- individual real-world OCR reads are allowed to be wrong or
    low-confidence; the client-side gate (`digitizer.js`) is what decides
    whether to trust any of it.
    """
    result = run_stages(TESTDATA / "photo" / "enthusiast_logo.png",
                         cfg(target_width_mm=90.0))

    tagged = [r for r in result.regions if r.meta.get("text_cluster_id")]
    cluster_ids = {r.meta["text_cluster_id"] for r in tagged}
    biggest_id = max(cluster_ids, key=lambda cid: sum(
        1 for r in tagged if r.meta["text_cluster_id"] == cid))
    members = [r for r in tagged if r.meta["text_cluster_id"] == biggest_id]
    assert len(members) >= 10

    saw_a_real_character = False
    for r in members:
        assert "ocr_char" in r.meta
        assert "ocr_confidence" in r.meta
        char, confidence = r.meta["ocr_char"], r.meta["ocr_confidence"]
        assert char is None or (isinstance(char, str) and len(char) == 1)
        assert confidence is None or (isinstance(confidence, float) and 0.0 <= confidence <= 100.0)
        if char is not None:
            saw_a_real_character = True
    assert saw_a_real_character, (
        "the real benchmark fixture's subline is clean/legible enough that "
        "at least one member must produce a real OCR character read"
    )

    # An ordinary, never-tagged shape gets no OCR fields at all (absent
    # means "no suggestion" -- same convention `text_candidate` follows).
    untagged = [r for r in result.regions if not r.meta.get("text_cluster_id")]
    assert untagged, "the fixture must also produce ordinary, untagged shapes"
    for r in untagged:
        assert "ocr_char" not in r.meta
        assert "ocr_confidence" not in r.meta
