"""`config.RETIRED_FIELDS`: the plumbing that lets flag consolidation remove a field.

A removed field must not break (1) the frozen engine snapshots, which still name it and are
never edited, or (2) an old client / script that still sends it to the service.
docs/flag-audit-2026-11-19.md, "What a fold actually costs".
"""
from __future__ import annotations

import dataclasses
import importlib
import json
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.config import RETIRED_FIELDS
from tests.conftest import engine_snapshot, read_engine_snapshot, wait_for_job

TESTS = Path(__file__).resolve().parent
ART = TESTS.parent / "testdata" / "logo_whitebg.png"
FIELDS = {f.name for f in dataclasses.fields(PipelineConfig)}
SNAPSHOTS = sorted(p.name for p in TESTS.glob("engine_20*_*_*.json"))


def test_no_name_is_both_a_field_and_retired():
    assert not FIELDS & RETIRED_FIELDS, sorted(FIELDS & RETIRED_FIELDS)


@pytest.mark.parametrize("name", SNAPSHOTS)
def test_every_snapshot_key_is_a_field_or_retired(name):
    stray = sorted(set(read_engine_snapshot(name)) - FIELDS - RETIRED_FIELDS)
    assert not stray, f"{name} names {stray}: neither a PipelineConfig field nor in RETIRED_FIELDS"


@pytest.mark.parametrize("name", SNAPSHOTS)
def test_engine_snapshot_drops_retired_keys(name):
    assert not set(engine_snapshot(name)) & RETIRED_FIELDS
    PipelineConfig(**engine_snapshot(name))      # and spreads into a live config


def test_the_service_drops_a_retired_field_instead_of_refusing_it(monkeypatch):
    pytest.importorskip("fastapi", reason="service extra not installed")
    svc = importlib.import_module("digitizer_service.app")   # the package re-exports `app` (the FastAPI object)
    monkeypatch.setattr(svc, "RETIRED_FIELDS", frozenset({"gone_flag"}))
    data = {"gone_flag": True, "target_width_mm": 40.0}
    assert svc._validate_config_dict(data, svc._CONFIG_FIELDS) == {"target_width_mm": 40.0}
    with pytest.raises(svc.HTTPException) as e:          # a genuinely unknown name still 400s
        svc._validate_config_dict({"gone_flag": 1, "not_a_flag": 1}, svc._CONFIG_FIELDS)
    assert e.value.status_code == 400 and "not_a_flag" in e.value.detail
    assert "gone_flag" not in e.value.detail


def test_a_request_carrying_a_retired_field_is_accepted(client, monkeypatch):
    pytest.importorskip("fastapi", reason="service extra not installed")
    svc = importlib.import_module("digitizer_service.app")   # the package re-exports `app` (the FastAPI object)
    monkeypatch.setattr(svc, "RETIRED_FIELDS", frozenset({"gone_flag"}))
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps({"gone_flag": True, "target_width_mm": 40.0})})
    assert r.status_code == 202, r.text
    assert wait_for_job(client, r.json()["job_id"])["state"] == "done"
