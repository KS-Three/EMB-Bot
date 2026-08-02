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


# The shape-layers contract v1: what a shape_overrides entry may hold, and the
# closed vocabularies two of its fields draw from. Kept in lockstep with
# `digitizer_core.regions.apply_shape_edits`, which enforces the same rules —
# the service checks here so a bad edit is a 400 at submit, not a failed job.
_OVERRIDE_KEYS = {"thread_index", "fill_angle_deg", "tier", "border", "layer"}
_TIER_VALUES = {"auto", "satin", "fill", "run"}
_BORDER_VALUES = {"off", "auto", "bean"}


def _canonicalize_shape_edits(data: dict, chart_len: int) -> None:
    """Validate and canonicalize the review-edit fields, in place.

    Canonicalization is load-bearing, not tidiness: the job cache keys on
    sha256(image) + the JSON-canonical config (`jobs.content_key`), so two
    spellings of one edit — a reordered deleted list, an explicitly-empty
    overrides dict, a null field — must collapse to one key or an edited
    re-digitize returns a stale cached job (and a no-op edit re-runs a job the
    cache already holds).
    """
    # A JSON null is the same statement as absence, for both fields.
    for key in ("deleted_shape_ids", "shape_overrides"):
        if key in data and data[key] is None:
            data.pop(key)

    deleted = data.get("deleted_shape_ids")
    if deleted is not None:
        if not isinstance(deleted, list) or not all(isinstance(s, str) for s in deleted):
            raise HTTPException(
                status_code=400,
                detail="deleted_shape_ids must be a list of shape id strings.",
            )
        deleted = sorted(set(deleted))
        if deleted:
            data["deleted_shape_ids"] = deleted
        else:
            data.pop("deleted_shape_ids")

    overrides = data.get("shape_overrides")
    if overrides is None:
        return
    if not isinstance(overrides, dict):
        raise HTTPException(
            status_code=400,
            detail="shape_overrides must be an object keyed by shape_id.",
        )
    clean: dict = {}
    for sid, ov in overrides.items():
        if not isinstance(ov, dict):
            raise HTTPException(
                status_code=400,
                detail=f"shape_overrides[{sid!r}] must be an object.",
            )
        unknown = sorted(set(ov) - _OVERRIDE_KEYS)
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"unknown shape_overrides[{sid!r}] field(s): {', '.join(unknown)}. "
                       f"Allowed: {', '.join(sorted(_OVERRIDE_KEYS))}",
            )
        entry = {k: v for k, v in ov.items() if v is not None}
        bad = None
        t = entry.get("thread_index")
        if t is not None and (not isinstance(t, int) or isinstance(t, bool)
                              or not 0 <= t < chart_len):
            bad = f"thread_index must be an integer 0..{chart_len - 1}"
        L = entry.get("layer")
        if L is not None and (not isinstance(L, int) or isinstance(L, bool)):
            bad = "layer must be an integer"
        a = entry.get("fill_angle_deg")
        if a is not None and (not isinstance(a, (int, float)) or isinstance(a, bool)):
            bad = "fill_angle_deg must be a number"
        tier = entry.get("tier")
        if tier is not None:
            if not isinstance(tier, str) or tier.lower() not in _TIER_VALUES:
                bad = f"tier must be one of {', '.join(sorted(_TIER_VALUES))}"
            else:
                entry["tier"] = tier.lower()
                if entry["tier"] == "auto":
                    entry.pop("tier")      # "auto" IS the absence of an override
        border = entry.get("border")
        if border is not None and not isinstance(border, bool):
            if not isinstance(border, str) or border.lower() not in _BORDER_VALUES:
                bad = f"border must be one of {', '.join(sorted(_BORDER_VALUES))}"
            else:
                entry["border"] = border.lower()
        if bad:
            raise HTTPException(
                status_code=400, detail=f"shape_overrides[{sid!r}]: {bad}.",
            )
        if entry:
            clean[sid] = entry
    if clean:
        data["shape_overrides"] = clean
    else:
        data.pop("shape_overrides")


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
    _canonicalize_shape_edits(data, len(load_chart(brand or DEFAULT_BRAND)))
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


# What a plan-level run kind says about the tier a shape ACTUALLY sewed as.
# Underlay, travel, ties and borders are companions to a tier, not a tier.
_KIND_TIER_RANK = {"satin": 3, "fill": 2, "run": 1, "bean": 1}
_RANK_TIER = {3: "satin", 2: "fill", 1: "run"}


def _sew_facts(plan) -> dict[str, dict]:
    """shape_id -> {sew_index, sew_block, tier}, read off the EMITTED plan.

    The layers panel needs to order shapes by when they sew and to name the
    tier each one sewed as. Both are read from the finished plan rather than
    re-deriving stage 7's classification: the plan's runs carry shape_id and
    kind, so this is the same decision stage 7 made — including every rescue
    and fall-through — not a prediction of it.
    """
    facts: dict[str, dict] = {}
    for bi, block in enumerate(plan.blocks):
        for run in block.runs:
            sid = run.shape_id
            if not sid:
                continue
            f = facts.setdefault(sid, {"sew_index": len(facts), "sew_block": bi,
                                       "_rank": 0})
            f["_rank"] = max(f["_rank"], _KIND_TIER_RANK.get(run.kind, 0))
    for f in facts.values():
        f["tier"] = _RANK_TIER.get(f.pop("_rank"))
    return facts


def _review_payload(result, plan=None) -> dict:
    """The half a review screen edits: what shapes are here, in what thread —
    and, when the plan is in hand, when each sews and as what tier."""
    facts = _sew_facts(plan) if plan is not None else {}
    none = {"sew_index": None, "sew_block": None, "tier": None}
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
                "layer": r.meta.get("layer"),
                # The sew position and effective tier the layers panel orders
                # by. None means the shape produced no stitches (the plan's
                # SHAPE_NOT_STITCHED warning says how many did).
                **{k: facts.get(r.shape_id, none)[k]
                   for k in ("sew_index", "sew_block", "tier")},
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
            "review": _review_payload(result, plan),
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
