"""Smoke: every default-OFF boolean cfg flag, turned ON, runs the pipeline.

The list is read off `PipelineConfig` itself, so a flag added later is
covered the day it lands. This asserts only "no crash and a plan comes back"
-- not quality, and never a default (a flag that flips ON drops out of the
list on its own).
"""
import dataclasses
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, run_stages

FIXTURE = Path(__file__).resolve().parent.parent / "testdata" / "logo_whitebg.png"

OFF_FLAGS = sorted(
    f.name
    for f in dataclasses.fields(PipelineConfig)
    if f.default is False and "bool" in str(f.type)
)


def test_flag_list_is_not_empty():
    assert len(OFF_FLAGS) >= 25


@pytest.mark.parametrize("flag", OFF_FLAGS)
def test_flag_on_does_not_crash(flag):
    result = run_stages(FIXTURE, PipelineConfig(target_width_mm=80.0, **{flag: True}))
    assert result is not None
