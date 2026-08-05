"""End-to-end contract invariants: determinism, palette integrity, ID carry-forward."""
import copy

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
