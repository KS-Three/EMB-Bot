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
            "jobs": {"jobs": 0, "states": {}, "inflight": 0}, "generations": {"entries": 0, "max": 8},
            "engine": {"commit": "0123456789abcdef0123456789abcdef01234567", "dirty": False,
                       "release": None, "started_at": "2026-10-25T12:00:00+00:00",
                       "defaults_sha": "0" * 64},
            "capabilities": {"background_removal": True, "ocr": True,
                             "face_priors": True, "sam2": False},
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
    engine: dict[str, Any] = Field(description=(
        "Which engine answered. `commit` and `dirty` (a tracked change under "
        "digitizer_core/ or digitizer_service/) and `started_at` are read when "
        "the process starts, so they name the code it LOADED, not what the "
        "working tree holds now; `commit`/`dirty` are null when git is "
        "unavailable. A frozen build (the Windows app) never asks git: all "
        "three come from the stamp written when it was built, with `release` "
        "its name (the tag, or `dev-<commit>`); `release` is null in a "
        "checkout. `defaults_sha` is the sha256 of the engine's default "
        "config, read per request."))
    capabilities: dict[str, bool] = Field(description=(
        "What this machine can run, from the pipeline's own probes: "
        "`background_removal`, `ocr` (tesseract on PATH), `face_priors` and "
        "`sam2`. Environment checks only; a worker can still fail at run time."))


class Classified(BaseModel):
    """`/classify`: stage 0's lane for the upload, before any run."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "class": "gradient", "confidence": 1.0,
        "signals": {"unique_color_mass": 0.12, "gradient_smoothness": 0.004,
                    "alpha_softness": 0.0, "unique_color_mass_seed": 0},
        "warnings": [{"code": "CLASSIFIED_GRADIENT", "message": "..."}],
        "forced_class_accepted": False, "elapsed_ms": 2189.4,
    }})

    class_: str = Field(alias="class", description="flat | gradient | photo_subject | photo_scene")
    confidence: float
    signals: dict[str, Any] = Field(description="Stage 0's measurements; empty under a forced class.")
    warnings: list[Any] = Field(description=(
        "The CLASSIFIED_* / CLASSIFICATION_UNCERTAIN codes stage 0 emits, plus "
        "FACE_ROUTED_FLAT or PHOTO_DETECTED when stage 1.25 fires."))
    forced_class_accepted: bool
    elapsed_ms: float


class Recounted(BaseModel):
    """`/recount`: how many shapes and colours the run would produce at the
    requested size. Additive route (2026-11-05); counts only."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "shape_count": 22, "color_count": 2, "size_mm": [36.7, 24.1],
        "generation_cache": "miss", "elapsed_ms": 7390.0,
    }})

    shape_count: int = Field(description="Regions that sew; unstitched ones (enclosed background) are not counted.")
    color_count: int = Field(description="Distinct threads among the sewn regions.")
    size_mm: list[float] = Field(description="[width, height] of the design at this config, mm.")
    generation_cache: str = Field(description="hit | miss: whether stages 0-4 were reused. A miss leaves them cached for /digitize.")
    elapsed_ms: float


class OpenObject(BaseModel):
    """A JSON object whose keys are documented in the route description."""

    model_config = ConfigDict(extra="allow")


class OutlineFont(BaseModel):
    """One row of `GET /fonts/outline`: a TrueType/OpenType font the service
    digitizes on demand (`POST /lettering`)."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "key": "montserrat-bold", "name": "Montserrat Bold", "family": "Montserrat",
        "group": "Sans", "style": "Bold", "weight": 700, "variable": True,
        "licenseId": "OFL-1.1", "kind": "outline",
        "source": "https://github.com/google/fonts/tree/86aced91/ofl/montserrat",
        "coverage": [[32, 126], 160, [161, 255]],
        "file": "/fonts/outline/montserrat-bold/file",
        "license": "/fonts/outline/montserrat-bold/license",
    }})

    key: str
    name: str
    family: str
    group: str = Field(description="Sans | Serif | Script | Display — the font browser's chips.")
    style: str
    weight: int
    variable: bool = Field(description="True when the shipped file is a variable font instanced to `weight`.")
    licenseId: str
    kind: str = Field(description="Always \"outline\"; the .embf manifest's rows have no `kind`.")
    source: str
    coverage: list[Any] = Field(description="Codepoints drawn: a bare codepoint or an inclusive [lo, hi] run.")
    file: str
    license: str


class OutlineFonts(BaseModel):
    version: int
    fonts: list[OutlineFont]


MANUAL_EXAMPLE = {
    "shapes": [{
        "polygon": [[0, 0], [20, 0], [20, 10], [0, 10]],
        "technique": "fill",
        "thread_rgb": [200, 30, 30],
    }],
    "config": {},
}

LETTERING_EXAMPLE = {
    "font": "montserrat-bold",
    "text": "Fremont",
    "width_mm": 76,
    "thread_rgb": [0, 0, 0],
    "config": {"garment_id": "left_chest"},
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
