"""The Studio's "Flatten shading" tick on the wire: `config.bevel_ring_fold`.

Kent's ruling 2026-11-14 on `bevel_ring_fold` (PR #1486): "Studio tickbox,
OFF". The engine default stays False. The Studio sends the key only when the
box is ticked (`app/src/lib/digitizer.js` `buildDigitizeConfig`), so absent
must read as OFF, and a ticked request must reach the pipeline's config and
must not be served a generation cached for the unticked one (the fold runs in
`build_generation`, stages 0-4, which the service caches)."""
from __future__ import annotations

import json
from pathlib import Path

from digitizer_core.config import PipelineConfig

from .conftest import wait_for_job

ART = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"


def test_the_field_is_a_config_field_and_absent_is_off():
    from digitizer_service.app import _CONFIG_FIELDS, _parse_config
    assert "bevel_ring_fold" in _CONFIG_FIELDS
    assert PipelineConfig().bevel_ring_fold is False
    assert PipelineConfig(**_parse_config(json.dumps({}))).bevel_ring_fold is False
    assert PipelineConfig(**_parse_config(json.dumps({"bevel_ring_fold": True}))).bevel_ring_fold is True


def test_ticked_and_unticked_never_share_a_cached_generation():
    from digitizer_service.jobs import content_key, generation_key
    data = ART.read_bytes()
    off, on = {"target_width_mm": 40.0}, {"target_width_mm": 40.0, "bevel_ring_fold": True}
    assert generation_key(data, off) != generation_key(data, on)
    assert content_key(data, off) != content_key(data, on)


def _submit(client, config):
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps(config)})
    assert r.status_code == 202, r.text
    state = wait_for_job(client, r.json()["job_id"])
    assert state["state"] == "done", state.get("detail") or state.get("error")
    return state


def test_the_tick_reaches_the_pipeline_config(client, monkeypatch):
    import importlib
    # the package re-exports the FastAPI object as `app`, which shadows the
    # module on attribute access
    service = importlib.import_module("digitizer_service.app")
    seen = []
    real = service.build_generation

    def spy(pixels, cfg, *a, **k):
        seen.append(cfg.bevel_ring_fold)
        return real(pixels, cfg, *a, **k)
    monkeypatch.setattr(service, "build_generation", spy)
    # an odd width no other test asks for, so neither the job replay nor the
    # generation cache can answer from an earlier test in this worker
    base = {"target_width_mm": 41.5, "preflight": False}
    off = _submit(client, base)
    on = _submit(client, {**base, "bevel_ring_fold": True})
    assert seen == [False, True]
    assert off["design"]["stitchCount"] > 0 and on["design"]["stitchCount"] > 0
