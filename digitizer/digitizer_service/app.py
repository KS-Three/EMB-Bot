"""The localhost digitizing service — build step 8.

Artwork goes in, an EMB-Bot `Design` comes out. Machine files come out of a
second route that every EMB-Bot design can use, whether it was digitized here,
typed as lettering, or imported from a DST.

Posture for v1 is deliberately small: it binds 127.0.0.1, the artwork never
leaves the machine, and there is no hosting bill. The shared-secret seam exists
but is off — set `EMBBOT_SERVICE_TOKEN` and every route but `/health` starts
requiring `X-EMBBOT-Token`. That switch is what has to be thrown before this
ever listens on anything but loopback.

Run it:  .venv/Scripts/python -m digitizer_service
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import fields as dataclass_fields

import cv2
import numpy as np
from fastapi import Body, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from digitizer_core import PipelineConfig, __doc__ as core_doc  # noqa: F401
from digitizer_core.adapter import design_size_mm, design_to_pattern, plan_to_design
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import run_preflight
from digitizer_core.threads import DEFAULT_BRAND, brand_index, load_chart

from . import formats
from .jobs import DONE, JobRegistry, content_key

VERSION = "0.5.0"

# An upload this large is a photograph someone dragged in by mistake, and the
# pipeline would spend minutes on it before saying so.
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 40_000_000

# Config keys a caller may set. Everything else on PipelineConfig is either
# internal (debug_dir) or would let a request write to disk.
_CONFIG_FIELDS = {f.name for f in dataclass_fields(PipelineConfig)} - {"debug_dir", "extra"}

registry = JobRegistry(workers=1)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    registry.shutdown()


app = FastAPI(title="Fritsch's Stitches digitizer", version=VERSION, lifespan=lifespan)

# Studio runs on a localhost dev server or a localhost static host. `null`
# (every file:// page on the machine) is deliberately not allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _require_token(supplied: str | None) -> None:
    expected = os.environ.get("EMBBOT_SERVICE_TOKEN")
    if expected and supplied != expected:
        raise HTTPException(status_code=401, detail="Missing or wrong X-EMBBOT-Token.")


def _parse_config(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"config is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="config must be a JSON object.")
    unknown = sorted(set(data) - _CONFIG_FIELDS)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown config field(s): {', '.join(unknown)}",
        )
    brand = data.get("thread_brand")
    if brand:
        try:
            load_chart(brand)
        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"unknown thread brand {brand!r}. See /health for the list.",
            ) from exc
    return data


def _decode(data: bytes) -> np.ndarray:
    """Decode and size-check once, here, instead of discovering minutes later.

    The array goes to the pipeline as-is: `stage1_prep._load` treats an ndarray
    exactly as it treats the bytes it would have decoded itself, so this costs
    nothing extra and lets an oversized image fail as a 413 at submit time
    rather than as a job that hogs the worker.
    """
    raw = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise HTTPException(
            status_code=400,
            detail="That file isn't an image the engine can read. PNG, JPEG, "
                   "WebP and TIFF all work; PDF and SVG don't.",
        )
    h, w = raw.shape[:2]
    if h * w > MAX_PIXELS:
        raise HTTPException(
            status_code=413,
            detail=f"Artwork is {w}x{h} ({h*w//1_000_000} megapixels); the limit is "
                   f"{MAX_PIXELS//1_000_000}. Embroidery needs far less — "
                   "2000 px across is plenty.",
        )
    return raw


def _review_payload(result) -> dict:
    """The half a review screen edits: what shapes are here, in what thread."""
    return {
        "palette": result.palette,
        "design_size_mm": list(result.design_size_mm),
        "px_per_mm": result.px_per_mm,
        "segmenter": result.segmenter,
        "background": {
            "detected": result.background.detected,
            "stitched": result.background.stitched,
            "outline_mm": result.background.outline_mm,
        },
        "shapes": [
            {
                "shape_id": r.shape_id,
                "thread_index": r.thread_index,
                "thread_number": r.thread_number,
                "area_mm2": round(r.area_mm2, 3),
                "source": r.source,
                "outline_mm": [[round(x, 3), round(y, 3)] for x, y in r.polygon.exterior.coords],
                "holes_mm": [
                    [[round(x, 3), round(y, 3)] for x, y in h.coords]
                    for h in r.polygon.interiors
                ],
            }
            for r in result.regions
        ],
    }


def _stats_payload(plan, design: dict) -> dict:
    """What the operator is about to sew.

    Counts come from the DESIGN, not the plan, wherever the two can differ. The
    plan marks the first run of every color block as trimmed, but the first
    block has no thread to cut yet, so plan.stats reports one trim more than the
    file contains — a fifth of the total on a five-color design. Thread lengths
    come from the plan, which is the only thing that knows them.
    """
    s = plan.stats
    kinds: dict[str, int] = {}
    for rec in design["stitches"]:
        kinds[rec["type"]] = kinds.get(rec["type"], 0) + 1
    return {
        "stitch_count": design["stitchCount"],
        "color_changes": kinds.get("color", 0),
        "trims": kinds.get("trim", 0),
        "jumps": kinds.get("jump", 0),
        "size_mm": [design["widthMM"], design["heightMM"]],
        "thread_m_total": round(s.thread_m_total, 2),
        "thread_m_by_color": [round(v / 1000.0, 2) for v in s.thread_mm_by_color],
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "digitizer",
        "version": VERSION,
        "auth": "token" if os.environ.get("EMBBOT_SERVICE_TOKEN") else "none",
        "default_brand": DEFAULT_BRAND,
        "brands": brand_index(),
        "formats": formats.supported(),
        "limits": {"max_upload_bytes": MAX_UPLOAD_BYTES, "max_pixels": MAX_PIXELS},
        "jobs": registry.stats(),
    }


@app.post("/digitize", status_code=202)
async def start_digitize(
    image: UploadFile = File(...),
    config: str | None = Form(None),
    x_embbot_token: str | None = Header(None),
) -> dict:
    """Artwork in, a job id out. Poll `/jobs/{id}`.

    A repeat of an identical request returns the finished job straight away —
    the review screen's parameter loop depends on that.
    """
    _require_token(x_embbot_token)

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="No image received.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Artwork is {len(data)//1024//1024} MB; the limit is "
                   f"{MAX_UPLOAD_BYTES//1024//1024} MB. Export it smaller and try again.",
        )

    cfg_dict = _parse_config(config)
    key = content_key(data, cfg_dict)
    pixels = await run_in_threadpool(_decode, data)

    def work() -> dict:
        cfg = PipelineConfig(**cfg_dict)
        result, plan = digitize(pixels, cfg)
        design = plan_to_design(plan, name=cfg_dict.get("name") or "Digitized design")
        return {
            "design": design,
            "review": _review_payload(result),
            "stats": _stats_payload(plan, design),
            "warnings": plan.warnings,
            # Step 9: what will go wrong on the machine, said before sewing.
            # None (not a passing report) when the caller turned it off, so
            # Studio can tell "clean" apart from "never checked".
            "preflight": run_preflight(result, plan, cfg, image=pixels)
                         if cfg.preflight else None,
        }

    job, cached = registry.submit(key, work)
    return {"job_id": job.id, "state": job.state, "cached": cached}


@app.get("/jobs/{job_id}")
def job_status(job_id: str, x_embbot_token: str | None = Header(None)) -> dict:
    _require_token(x_embbot_token)
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No such job. It may have been evicted.")
    return job.public()


@app.post("/export")
def export(
    payload: dict = Body(...),
    x_embbot_token: str | None = Header(None),
) -> Response:
    """Any EMB-Bot design in, a machine file out.

    This is the one export path for every design the product makes — lettering,
    imported, or digitized — which is how PES and JEF arrive without either
    being written by hand in JavaScript.
    """
    _require_token(x_embbot_token)

    design = payload.get("design")
    if not isinstance(design, dict) or not design.get("stitches"):
        raise HTTPException(status_code=400, detail="payload.design must be a design with stitches.")

    fmt = str(payload.get("format", "dst")).lower().lstrip(".")
    if fmt not in formats.FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported format {fmt!r}. Supported: {', '.join(sorted(formats.FORMATS))}",
        )

    label = str(payload.get("label") or "EMBBOT")
    try:
        pattern = design_to_pattern(design, label=label)
        data = formats.write(pattern, fmt)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"could not write {fmt}: {exc}") from exc

    meta = formats.FORMATS[fmt]
    w_mm, h_mm = design_size_mm(design)
    filename = f"{_safe_stem(label)}.{fmt}"
    return Response(
        content=data,
        media_type=meta["mime"],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Design-Width-Mm": f"{w_mm:.2f}",
            "X-Design-Height-Mm": f"{h_mm:.2f}",
            "X-Stitch-Convention": meta["convention"],
        },
    )


def _safe_stem(label: str) -> str:
    keep = [c if c.isalnum() or c in "-_" else "-" for c in label.strip()]
    stem = "".join(keep).strip("-") or "design"
    return stem[:48]
