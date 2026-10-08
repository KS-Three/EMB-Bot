"""OpenAPI-only models for the service.

These describe the wire shapes for `/docs` and `/openapi.json`. They are NEVER
used as `response_model` or request validators: the routes return plain dicts
and `Response`s exactly as before, so documenting a field here cannot change
what a client receives. Keep them in step with the route bodies by hand;
`tests/test_service_openapi.py` pins that every route is listed and documented.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    """Every handled failure: FastAPI's `HTTPException` body."""

    detail: str = Field(description="Human-readable reason, safe to show a customer.")

    model_config = ConfigDict(json_schema_extra={"example": {"detail": "No image received."}})


class JobSubmitted(BaseModel):
    job_id: str
    state: str = Field(description="queued | running | done | error")
    cached: bool = Field(description="True when an identical request already had a job.")

    model_config = ConfigDict(
        json_schema_extra={"example": {"job_id": "3f2a9c", "state": "queued", "cached": False}}
    )


class JobStatus(BaseModel):
    """`state` plus, once `done`, the result keys; once `error`, `error`/`detail`."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {"job_id": "3f2a9c", "state": "error",
                        "error": "The whole image read as background, so there was nothing to stitch."}
        },
    )

    job_id: str
    state: str = Field(description="queued | running | done | error")
    design: dict[str, Any] | None = Field(None, description="Done only: stitches, threads, runs.")
    review: dict[str, Any] | None = Field(None, description="Done only: shape-layers review payload.")
    stats: dict[str, Any] | None = Field(None, description="Done only.")
    warnings: list[Any] | None = Field(None, description="Done only.")
    preflight: dict[str, Any] | None = Field(None, description="Done only; null if turned off.")
    generation_cache: str | None = Field(None, description="Done only: 'hit' or 'miss'.")
    error: str | None = Field(None, description="Error only: customer-facing message.")
    detail: str | None = Field(None, description="Error only: raw exception and traceback.")


class Health(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {
            "status": "ok", "service": "digitizer", "version": "0.0.0", "auth": "none",
            "default_brand": "madeira", "brands": [], "formats": ["dst", "pes"],
            "limits": {"max_upload_bytes": 12582912, "max_pixels": 40000000},
            "jobs": {"jobs": 0, "states": {}}, "generations": {"entries": 0, "max": 8},
        }}
    )

    status: str
    service: str
    version: str
    auth: str = Field(description="'token' when EMBBOT_SERVICE_TOKEN is set, else 'none'.")
    default_brand: str
    brands: list[Any]
    formats: list[Any]
    limits: dict[str, int]
    jobs: dict[str, Any]
    generations: dict[str, Any]


class OpenObject(BaseModel):
    """A JSON object whose keys are documented in the route description."""

    model_config = ConfigDict(extra="allow")


MANUAL_EXAMPLE = {
    "shapes": [{
        "polygon": [[0, 0], [20, 0], [20, 10], [0, 10]],
        "technique": "fill",
        "thread_rgb": [200, 30, 30],
    }],
    "config": {},
}

EXPORT_EXAMPLE = {
    "design": {"stitches": [[0, 0, 0], [10, 0, 0]]},
    "format": "dst",
    "label": "Sample",
}


def error(description: str) -> dict:
    return {"model": ErrorBody, "description": description}


UNAUTHORIZED = {401: error("Service has a token set and `X-EMBBOT-Token` is missing or wrong.")}
BUSY = {503: error("The digitizer is busy with other designs; try again in a minute.")}
TIMEOUT = {504: error("The request exceeded the service's request deadline.")}
