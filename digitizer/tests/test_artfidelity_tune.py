"""The tuner's search space must name fields the engine actually has.

`tools/artfidelity_tune.py` refuses by NAME: a parameter is searchable only if
it is in `TUNABLE`, excluded if it is in `DENIED`, and refused outright if it
is in `GATE3_FLAGS`. Every one of those refusals is silent when the name is
wrong - a misspelt entry in `DENIED` or `GATE3_FLAGS` does not fail, it simply
stops guarding anything, and the knob it was meant to fence goes unnamed.

That is not hypothetical. `GATE3_FLAGS` carried `contour_fill` from the tool's
first draft (2026-08-26) until 2026-09-01; `PipelineConfig` has never had such
a field. The contour tier is a VALUE of `fill_technique`, so ROADMAP gate 3's
refusal for contour pointed at nothing. These tests exist so a rename in
`config.py` breaks the tuner's fence loudly rather than quietly.
"""
from __future__ import annotations

import dataclasses
import importlib.util
from pathlib import Path

import pytest

from digitizer_core.config import PipelineConfig

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def _tune():
    spec = importlib.util.spec_from_file_location(
        "artfidelity_tune", TOOLS / "artfidelity_tune.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tune():
    return _tune()


@pytest.fixture(scope="module")
def config_fields():
    return {f.name for f in dataclasses.fields(PipelineConfig)}


@pytest.mark.parametrize("bucket", ["TUNABLE", "DENIED", "GATE3_FLAGS"])
def test_every_named_parameter_is_a_real_config_field(tune, config_fields,
                                                      bucket):
    unknown = sorted(n for n in getattr(tune, bucket) if n not in config_fields)
    assert not unknown, (
        f"{bucket} names {unknown}, which PipelineConfig does not have. "
        "A name that is not a field guards nothing.")


def test_a_gate3_tier_is_refused_by_name(tune):
    for flag in tune.GATE3_FLAGS:
        with pytest.raises(SystemExit) as exc:
            tune._check_space([flag])
        assert "gate 3" in str(exc.value)


def test_a_denied_parameter_is_refused_with_its_ruling(tune):
    name = next(iter(tune.DENIED))
    with pytest.raises(SystemExit) as exc:
        tune._check_space([name])
    assert tune.DENIED[name] in str(exc.value)


def test_an_unlisted_parameter_is_refused_rather_than_searched(tune,
                                                              config_fields):
    stranger = next(n for n in sorted(config_fields)
                    if n not in tune.TUNABLE and n not in tune.DENIED
                    and n not in tune.GATE3_FLAGS)
    with pytest.raises(SystemExit) as exc:
        tune._check_space([stranger])
    assert "not on the allowlist" in str(exc.value)


def test_the_allowlist_is_searchable_as_written(tune):
    tune._check_space(list(tune.TUNABLE))          # raises if any is fenced
    for name, (values, why) in tune.TUNABLE.items():
        assert len(list(values)) >= 2, f"{name} has nothing to search"
        assert why.strip(), f"{name} carries no reason it is not a constant"
