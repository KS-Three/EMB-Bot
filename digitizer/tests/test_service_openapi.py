"""The OpenAPI schema builds and documents every route the service serves."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="service extra not installed")
from digitizer_service.app import app  # noqa: E402

_HTTP = {"get", "post", "put", "patch", "delete"}
_DOCS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def _routes():
    return {
        (m.lower(), r.path)
        for r in app.routes
        if hasattr(r, "methods") and r.path not in _DOCS
        for m in r.methods
        if m.lower() in _HTTP
    }


def test_schema_builds_and_lists_every_route():
    app.openapi_schema = None
    schema = app.openapi()
    listed = {(m, p) for p, ops in schema["paths"].items() for m in ops if m in _HTTP}
    assert listed == _routes()
    assert len(listed) == 8


def test_every_operation_has_summary_and_error_responses():
    schema = app.openapi()
    for path, ops in schema["paths"].items():
        for method, op in ops.items():
            assert op.get("summary", "").strip(), (method, path)
            codes = set(op["responses"])
            assert "200" in codes or "202" in codes, (method, path)
            if path == "/health":
                continue
            assert "401" in codes, (method, path)
            if path != "/calibration/info":
                assert codes & {"400", "404"}, (method, path)


def test_error_and_job_models_are_referenced():
    schema = app.openapi()
    names = set(schema["components"]["schemas"])
    assert {"ErrorBody", "JobSubmitted", "JobStatus", "Health"} <= names
