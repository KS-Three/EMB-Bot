"""The small-text re-set's record kept (`cfg.extra["small_text_reset_report"]`,
2026-11-14, built OFF; the Director's next-wave brief).

`pipeline.build_generation` called `enlarge_small_text` and dropped its rows,
so no record could say why a line was not raised: the pro-redraws census
(2026-11-13) left Fremont's EST 1895 and Bridge's arc UNCONFIRMED for want of
it. The rows now ride `Generation.small_text_reset` and
`PipelineResult.small_text_reset`, and preflight reports them as the metric
`small_text_reset` under the flag. Metrics only: no finding, no score.
"""
from __future__ import annotations

import dataclasses
import inspect
from types import SimpleNamespace

import numpy as np

from digitizer_core import pipeline
from digitizer_core import preflight as pf
from digitizer_core.pipeline import Generation, PipelineResult
from digitizer_core.stitches import StitchBlock, StitchPlan
from tests.conftest import cfg


def _plan() -> StitchPlan:
    return StitchPlan(blocks=[StitchBlock(thread_index=0, thread_number="1704", rgb=(230, 60, 60), runs=[])],
                      palette=[])


def test_the_report_reaches_metrics_only_under_its_flag_as_plain_json():
    rows = [{"cluster": "TCa", "members": 4, "skipped": "no_room", "blocked_by": [[3, (1.0, 2.0)]],
             "shift_mm": (np.float64(0.5), 1), "cap_mm": np.float64(2.56)}]
    result = SimpleNamespace(small_text_reset=rows, regions=[], design_class="flat")
    off = pf.run_preflight(result, _plan(), cfg())
    assert "small_text_reset" not in off["metrics"]
    on = pf.run_preflight(result, _plan(), cfg(extra={"small_text_reset_report": True}))
    got = on["metrics"]["small_text_reset"]
    assert got == [{"cluster": "TCa", "members": 4, "skipped": "no_room", "blocked_by": [[3, [1.0, 2.0]]],
                    "shift_mm": [0.5, 1], "cap_mm": 2.56}]
    assert type(got[0]["cap_mm"]) is float
    # the rows are copied, never handed out by reference
    got[0]["cluster"] = "changed"
    assert rows[0]["cluster"] == "TCa"


def test_no_rows_reads_none_under_the_flag():
    flag = cfg(extra={"small_text_reset_report": True})
    assert pf.run_preflight(None, _plan(), flag)["metrics"]["small_text_reset"] is None
    bare = SimpleNamespace(small_text_reset=None, regions=[], design_class="flat")
    assert pf.run_preflight(bare, _plan(), flag)["metrics"]["small_text_reset"] is None


def test_the_generation_carries_the_rows_through_a_fork():
    assert Generation.__dataclass_fields__["small_text_reset"].default is None
    assert PipelineResult.__dataclass_fields__["small_text_reset"].default is None
    g = Generation.__new__(Generation)
    for f in dataclasses.fields(Generation):
        setattr(g, f.name, f.default if f.default is not dataclasses.MISSING else None)
    g.classification_warnings, g.quant_thread_indices, g.quant_warnings = [], [], []
    g.regions, g.dropped_areas, g.prep_warnings, g.small_warnings, g.resnap_warnings = [], [], [], [], []
    g.small_text_reset = [{"cluster": "TCa", "skipped": "tall_enough"}]
    f = g.fork()
    assert f.small_text_reset == g.small_text_reset and f.small_text_reset is not g.small_text_reset


def test_the_pipeline_keeps_the_rows_and_hands_them_on():
    """The wiring, read off the source: the re-set's return value is kept,
    written to the generation, and handed to the result."""
    build = inspect.getsource(pipeline.build_generation)
    assert "small_text_rows = enlarge_small_text(" in build
    assert "small_text_reset=small_text_rows" in build
    assert "small_text_reset=gen.small_text_reset" in inspect.getsource(pipeline.finish_generation)
