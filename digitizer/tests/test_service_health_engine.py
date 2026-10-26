"""`/health` names the engine that answered, so a number can name what made it.

On 2026-10-15 four of Kent's five red circles were a stale service on port
8721 holding old code (memory `the-80mm-ink-link-2026-10-15`). `/health`
carried a hand-set version and nothing that moved with the code. It now
carries `engine` {commit, dirty, started_at, defaults_sha} and `capabilities`
{background_removal, ocr, face_priors, sam2}; `tools/service-check.mjs` reads
the first to decide whether a running service is stale.
"""
from __future__ import annotations

import dataclasses
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="service extra not installed")

# `digitizer_service.app` the ATTRIBUTE is the FastAPI object (the package
# re-exports it), so the module is read from sys.modules.
from digitizer_service import app as _app_object  # noqa: E402,F401
service = sys.modules["digitizer_service.app"]

DIGITIZER = Path(__file__).resolve().parent.parent
SHA = re.compile(r"^[0-9a-f]{64}$")


def _health(client) -> dict:
    r = client.get("/health")
    assert r.status_code == 200, r.text
    return r.json()


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=DIGITIZER, capture_output=True,
                              text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


# ------------------------------------------------------------------ engine

def test_health_carries_the_engine_stamp(client):
    eng = _health(client)["engine"]
    assert set(eng) == {"commit", "dirty", "started_at", "defaults_sha"}
    assert SHA.match(eng["defaults_sha"])
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$", eng["started_at"])


def test_commit_is_the_checkout_the_process_loaded():
    """Read from git here independently. A source tarball has no git: then
    the stamp says so (null) rather than guessing."""
    head = _git("rev-parse", "HEAD")
    eng = service.engine_stamp()
    if head is None:
        assert eng["commit"] is None and eng["dirty"] is None
    else:
        assert eng["commit"] == head
        assert isinstance(eng["dirty"], bool)


def test_commit_and_start_are_taken_once_defaults_are_read_live(client, monkeypatch):
    """The stamp describes the code the process imported, so a checkout made
    after start must not change it; the defaults fingerprint is per request."""
    before = _health(client)["engine"]
    monkeypatch.setattr(service, "_git", lambda *a: "f" * 40)
    after = _health(client)["engine"]
    assert after["commit"] == before["commit"]
    assert after["started_at"] == before["started_at"]
    assert after["defaults_sha"] == before["defaults_sha"]


def test_dirty_is_a_tracked_change_under_the_two_imported_packages(monkeypatch):
    seen = []

    def fake_git(*args):
        seen.append(args)
        return "f" * 40 if args[0] == "rev-parse" else " M digitizer_core/config.py"

    monkeypatch.setattr(service, "_git", fake_git)
    got = service._read_engine_checkout()
    assert got["commit"] == "f" * 40 and got["dirty"] is True
    status = next(a for a in seen if a[0] == "status")
    # A docs edit or a tool does not make the running engine different, and an
    # untracked file is not imported unless something tracked names it.
    assert "--untracked-files=no" in status
    assert status[status.index("--") + 1:] == ("digitizer_core", "digitizer_service")

    monkeypatch.setattr(service, "_git", lambda *a: "f" * 40 if a[0] == "rev-parse" else "")
    assert service._read_engine_checkout()["dirty"] is False

    monkeypatch.setattr(service, "_git", lambda *a: None)
    assert service._read_engine_checkout() | {"started_at": 0} == {
        "commit": None, "dirty": None, "started_at": 0}


def test_defaults_sha_is_stable_between_requests(client):
    assert _health(client)["engine"]["defaults_sha"] == _health(client)["engine"]["defaults_sha"]


def test_defaults_sha_is_stable_across_processes():
    """A default whose repr carries an address would make the fingerprint move
    on every start and the launcher cry stale; a fresh interpreter agrees."""
    code = ("import sys; sys.path.insert(0, '.');"
            "from digitizer_service import app; import sys as s;"
            "print(s.modules['digitizer_service.app']._defaults_sha())")
    fresh = subprocess.run([sys.executable, "-I", "-c", code], cwd=DIGITIZER, capture_output=True,
                           text=True, timeout=240, check=True).stdout.strip().splitlines()[-1]
    assert SHA.match(fresh)
    assert fresh == service._defaults_sha()


def test_defaults_sha_moves_when_a_default_is_patched(client, monkeypatch):
    """The fingerprint is `asdict(PipelineConfig())`, so it follows whatever
    the engine would run a bare request with: flip a default and it moves."""
    base = _health(client)["engine"]["defaults_sha"]
    real = service.PipelineConfig
    field = next(f for f in dataclasses.fields(real) if f.name == "satin")
    assert isinstance(field.default, bool)

    @dataclasses.dataclass
    class Flipped(real):
        satin: bool = not field.default

    monkeypatch.setattr(service, "PipelineConfig", Flipped)
    moved = _health(client)["engine"]["defaults_sha"]
    assert moved != base
    monkeypatch.setattr(service, "PipelineConfig", real)
    assert _health(client)["engine"]["defaults_sha"] == base


# ------------------------------------------------------------ capabilities

_PROBES = {
    "background_removal": (service.stage1_photo_prep, "background_removal_unavailable_reason"),
    "face_priors": (service.stage1_photo_prep, "face_detector_unavailable_reason"),
    "sam2": (service.stage2_sam2_segment, "sam2_segmentation_unavailable_reason"),
}


def test_capabilities_are_the_four_booleans(client):
    caps = _health(client)["capabilities"]
    assert set(caps) == {"background_removal", "ocr", "face_priors", "sam2"}
    assert all(isinstance(v, bool) for v in caps.values())


def test_capabilities_follow_the_probes(client, monkeypatch):
    for key, (mod, name) in _PROBES.items():
        monkeypatch.setattr(mod, name, lambda: None)
    monkeypatch.setattr(service.legibility, "tesseract_available", lambda: True)
    assert set(_health(client)["capabilities"].values()) == {True}

    for key, (mod, name) in _PROBES.items():
        monkeypatch.setattr(mod, name, lambda: "not here")
    monkeypatch.setattr(service.legibility, "tesseract_available", lambda: False)
    assert set(_health(client)["capabilities"].values()) == {False}

    # One at a time: each key follows ITS probe and no other.
    for want, (mod, name) in _PROBES.items():
        for _k, (m2, n2) in _PROBES.items():
            monkeypatch.setattr(m2, n2, lambda: "not here")
        monkeypatch.setattr(mod, name, lambda: None)
        caps = _health(client)["capabilities"]
        assert {k for k, v in caps.items() if v} == {want}, (want, caps)
    for _k, (m2, n2) in _PROBES.items():
        monkeypatch.setattr(m2, n2, lambda: "not here")
    monkeypatch.setattr(service.legibility, "tesseract_available", lambda: True)
    assert {k for k, v in _health(client)["capabilities"].items() if v} == {"ocr"}


def test_a_probe_that_raises_is_unavailable_not_a_failed_health(client, monkeypatch):
    def boom():
        raise OSError("disk went away")

    monkeypatch.setattr(service.stage2_sam2_segment, "sam2_segmentation_unavailable_reason", boom)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["capabilities"]["sam2"] is False


def test_the_schema_documents_both_blocks():
    from digitizer_service import schemas
    props = schemas.Health.model_json_schema()["properties"]
    assert {"engine", "capabilities"} <= set(props)
    ex = schemas.Health.model_config["json_schema_extra"]["example"]
    assert set(ex["engine"]) == {"commit", "dirty", "started_at", "defaults_sha"}
    assert set(ex["capabilities"]) == {"background_removal", "ocr", "face_priors", "sam2"}
