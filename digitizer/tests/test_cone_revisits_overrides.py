"""`tools/cone_revisits.py`'s `key=value` config overrides (2026-10-11).

Kept apart from `test_cone_revisits.py`, whose test count MASTER_SCOPE cites
(`test_doc_claims` pins it at 8). The overrides let the corpus sweep re-run
under any `PipelineConfig` field, which is how the 10-11 re-measure of the
band route was done.
"""


def test_the_corpus_sweep_parses_its_config_overrides():
    """`python -m tools.cone_revisits some_flag=True` re-runs the sweep with
    that field set; a bool left as the string "False" would be truthy and
    silently measure the wrong arm."""
    from tools.cone_revisits import _overrides
    assert _overrides(["merge_adjacent_same_thread=False",
                       "target_width_mm=50", "edge_cap=none"]) == {
        "merge_adjacent_same_thread": False, "target_width_mm": 50.0,
        "edge_cap": "none"}
