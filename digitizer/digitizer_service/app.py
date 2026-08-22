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
import math
import os
from contextlib import asynccontextmanager
from dataclasses import fields as dataclass_fields

import cv2
import numpy as np
from fastapi import Body, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from shapely.geometry import Polygon
from starlette.concurrency import run_in_threadpool

from digitizer_core import PipelineConfig, __doc__ as core_doc  # noqa: F401
from digitizer_core import machine
from digitizer_core.adapter import design_size_mm, design_to_pattern, plan_to_design
from digitizer_core.manual import build_manual_result
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.preflight import run_preflight
from digitizer_core.stage0_classify import CLASSES
from digitizer_core.threads import DEFAULT_BRAND, brand_index, load_chart

from . import formats
from .jobs import DONE, GenerationCache, JobRegistry, content_key, generation_key

VERSION = "0.5.0"

# An upload this large is a photograph someone dragged in by mistake, and the
# pipeline would spend minutes on it before saying so.
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 40_000_000

# Config keys a caller may set. Everything else on PipelineConfig is either
# internal (debug_dir) or would let a request write to disk.
_CONFIG_FIELDS = {f.name for f in dataclass_fields(PipelineConfig)} - {"debug_dir", "extra"}

registry = JobRegistry(workers=1)
# Stage 0-4 generations, cached across review edits — the reason a boundary
# edit re-runs only `finish_generation` + `plan_stitches` instead of the
# whole pipeline (area 5's measured table: stages 0-4 are 53-81% of a job).
generations = GenerationCache()


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
# Exception: "stitched" is not read by `apply_shape_edits` — `pipeline.py`
# resolves it directly off `cfg.shape_overrides` (see the comment above that
# resolution) — but it is still validated here, in this same closed set, so a
# bad value is still a 400 at submit.
_OVERRIDE_KEYS = {"thread_index", "fill_angle_deg", "tier", "border", "layer",
                  "sew_order", "stitched", "underlay_style", "boundary_override"}
# Kept in lockstep with digitizer_core.regions._TIER_VALUES — see that
# copy's own comment for what "wave"/"chevron"/"brick" (alongside
# "crosshatch") each do.
_TIER_VALUES = {"auto", "satin", "fill", "run", "sketch", "streamline", "crosshatch",
                "wave", "chevron", "brick"}
_BORDER_VALUES = {"off", "auto", "bean"}
# fabrics.py's own vocabulary, verbatim — the one place that spells out the
# closed set stage6_fill._underlay_paths actually interprets. Anything
# outside it silently falls through to "edge_lattice" there (unrecognised ->
# the coarse default), which is fine for a fabric-preset id nobody mistypes
# by hand but not for a free-text field a review-screen edit sends over the
# wire — so this validates it as a 400 instead of a shape quietly getting the
# wrong underlay.
_UNDERLAY_VALUES = {"none", "edge_run", "center_run", "edge_zigzag", "edge_lattice",
                    "double_lattice", "zigzag"}
# `boundary_override` (contract v1.4) point-count bounds — mirrored,
# verbatim, in `digitizer_core.regions`'s own copy (the defense-in-depth
# check for any caller that isn't this service). This layer also pre-checks
# the shell alone for validity and the same sewability floor
# `apply_shape_edits` holds it to (self-intersection, degenerate/zero area) —
# a fast 400 on the common mistakes. What it cannot pre-check is hole
# containment: this is validating a request, not a Region, so it has never
# seen the shape's existing holes. That one check still only runs in
# `apply_shape_edits`, at job-run time — still a clean error there, never a
# crash, just not a submit-time 400.
_MIN_BOUNDARY_POINTS = 3
_MAX_BOUNDARY_POINTS = 500
# `merge_shape_ids` / `split_shapes` (contract v1.5) — top-level config keys,
# not `shape_overrides` entries: they change the SET of shapes, not one
# shape's attributes, so they cannot be keyed by a single shape_id the way
# every `_OVERRIDE_KEYS` field is. Mirrored, verbatim bounds, in
# `digitizer_core.regions`'s own copy (`_MERGE_MIN_SHAPES`) — the defense in
# depth for any caller that isn't this service. What this layer CANNOT
# pre-check, same reasoning as `boundary_override`'s hole-containment gap:
# whether the merge group's shapes actually share one thread/have no holes/
# touch each other, and whether a split line actually crosses its shape
# cleanly without crossing a hole — all of that needs the shapes' real
# geometry, which parsing a request never sees. Those checks run only in
# `regions.apply_shape_merges`/`apply_shape_splits`, at job-run time — a
# clean `ValueError` there (a failed job, never a crash), not a submit-time
# 400, exactly like the boundary_override hole case.
_MIN_MERGE_SHAPES = 2


def _dedupe_ring(points: list) -> list:
    """Drop consecutive duplicate points, including a closing point that
    repeats the first — see `digitizer_core.regions._dedupe_ring` (the same
    function, mirrored) for why a client may send either convention."""
    out: list = []
    for pt in points:
        if out and out[-1] == pt:
            continue
        out.append(pt)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _canonicalize_shape_edits(data: dict, chart_len: int) -> None:
    """Validate and canonicalize the review-edit fields, in place.

    Canonicalization is load-bearing, not tidiness: the job cache keys on
    sha256(image) + the JSON-canonical config (`jobs.content_key`), so two
    spellings of one edit — a reordered deleted list, an explicitly-empty
    overrides dict, a null field — must collapse to one key or an edited
    re-digitize returns a stale cached job (and a no-op edit re-runs a job the
    cache already holds).
    """
    # A JSON null is the same statement as absence, for every field here.
    for key in ("deleted_shape_ids", "shape_overrides", "merge_shape_ids", "split_shapes"):
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

    # `merge_shape_ids` (contract v1.5): [[shape_id, shape_id, ...], ...].
    # Canonicalized the same way `deleted_shape_ids` is — each group
    # de-duplicated and sorted, then the whole list of groups sorted — so two
    # spellings of one merge request (different group/id order) are ONE cache
    # key, same load-bearing reasoning this function's own docstring gives.
    # What this layer cannot check (shared thread, no holes, adjacency) is
    # validated in `regions.apply_shape_merges` — see `_MIN_MERGE_SHAPES`'s
    # comment above.
    merges = data.get("merge_shape_ids")
    if merges is not None:
        if not isinstance(merges, list):
            raise HTTPException(
                status_code=400,
                detail="merge_shape_ids must be a list of shape id groups.",
            )
        clean_groups = []
        for group in merges:
            if not isinstance(group, list) or not all(isinstance(s, str) and s for s in group):
                raise HTTPException(
                    status_code=400,
                    detail="merge_shape_ids groups must be lists of non-empty shape id strings.",
                )
            g = sorted(set(group))
            if len(g) < _MIN_MERGE_SHAPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"merge_shape_ids group {group!r} needs at least "
                           f"{_MIN_MERGE_SHAPES} distinct shape ids.",
                )
            clean_groups.append(g)
        if clean_groups:
            data["merge_shape_ids"] = sorted(clean_groups)
        else:
            data.pop("merge_shape_ids")

    # `split_shapes` (contract v1.5): {shape_id: [[x0, y0], [x1, y1]]}. Same
    # shallow-cheap-check-here, real-geometry-check-in-`regions.
    # apply_shape_splits posture `boundary_override` already uses — this
    # layer confirms the SHAPE of the request (a 2-point finite line), not
    # whether that line actually crosses the named shape's geometry cleanly.
    splits = data.get("split_shapes")
    if splits is not None:
        if not isinstance(splits, dict):
            raise HTTPException(
                status_code=400,
                detail="split_shapes must be an object keyed by shape_id.",
            )
        clean_splits = {}
        for sid, line in splits.items():
            bad_line = (
                not isinstance(line, list) or len(line) != 2
                or not all(
                    isinstance(pt, list) and len(pt) == 2
                    and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in pt)
                    for pt in line
                )
                or not all(math.isfinite(c) for pt in line for c in pt)
            )
            if bad_line:
                raise HTTPException(
                    status_code=400,
                    detail=f"split_shapes[{sid!r}] must be a line of exactly two "
                           "[x, y] points of finite numbers.",
                )
            (x0, y0), (x1, y1) = line
            if math.hypot(x1 - x0, y1 - y0) < 1e-6:
                raise HTTPException(
                    status_code=400,
                    detail=f"split_shapes[{sid!r}] line has zero length.",
                )
            # Canonicalize the two endpoints' order (mirrors `regions.
            # apply_shape_splits`'s own copy of this normalization) so
            # submitting the same drag with its two points swapped is the
            # SAME cache key, not a different one for an identical cut.
            (nx0, ny0), (nx1, ny1) = sorted([(float(x0), float(y0)), (float(x1), float(y1))])
            clean_splits[sid] = [[nx0, ny0], [nx1, ny1]]
        if clean_splits:
            data["split_shapes"] = clean_splits
        else:
            data.pop("split_shapes")

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
        so = entry.get("sew_order")
        if so is not None and (not isinstance(so, int) or isinstance(so, bool) or so < 0):
            bad = "sew_order must be a non-negative integer"
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
        underlay = entry.get("underlay_style")
        if underlay is not None:
            if not isinstance(underlay, str) or underlay.lower() not in _UNDERLAY_VALUES:
                bad = f"underlay_style must be one of {', '.join(sorted(_UNDERLAY_VALUES))}"
            else:
                entry["underlay_style"] = underlay.lower()
        st = entry.get("stitched")
        if st is not None and not isinstance(st, bool):
            bad = "stitched must be a boolean"
        bo = entry.get("boundary_override")
        if bo is not None:
            if not isinstance(bo, list):
                bad = "boundary_override must be a list of [x, y] points"
            else:
                pts = _dedupe_ring(bo)
                if not _MIN_BOUNDARY_POINTS <= len(pts) <= _MAX_BOUNDARY_POINTS:
                    bad = (f"boundary_override must have {_MIN_BOUNDARY_POINTS}.."
                           f"{_MAX_BOUNDARY_POINTS} distinct points (got {len(pts)})")
                elif not all(
                    isinstance(pt, list) and len(pt) == 2
                    and all(isinstance(c, (int, float)) and not isinstance(c, bool)
                            for c in pt)
                    for pt in pts
                ):
                    bad = "boundary_override points must be [x, y] pairs of numbers"
                elif not all(math.isfinite(c) for pt in pts for c in pt):
                    bad = "boundary_override points must be finite numbers"
                else:
                    # The shell-only half of `apply_shape_edits`'s geometry
                    # check, pre-run here for a fast 400 on the common
                    # mistake (a drag that crosses itself, or collapses the
                    # shape to a sliver) — the same `is_valid` + sewability-
                    # floor test, minus hole containment: this layer never
                    # sees the shape's existing holes (it is validating a
                    # request, not a Region), so a hole poking outside the
                    # new shell surfaces at job-run time instead, still as a
                    # clean error (`apply_shape_edits` raises, the job
                    # registry reports it), never a crash.
                    poly = Polygon(pts)
                    if not poly.is_valid or poly.is_empty:
                        bad = ("boundary_override is not a valid simple polygon "
                               "— check for self-intersections")
                    elif (poly.area < machine.RUN_MIN_AREA_MM2
                          or poly.exterior.length < machine.RUN_MIN_LOOP_MM):
                        bad = (f"boundary_override is too small to sew "
                               f"({poly.area:.4f} mm², floor "
                               f"{machine.RUN_MIN_AREA_MM2} mm²)")
                    else:
                        entry["boundary_override"] = [[float(x), float(y)] for x, y in pts]
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


def _validate_config_dict(data: dict, allowed_fields: set[str]) -> dict:
    """The field-allowlist + shape-edit canonicalization shared by every
    config-carrying route. `allowed_fields` differs by route: manual
    digitizing has no prior generation for `deleted_shape_ids`/
    `shape_overrides` to reference, so it excludes both (see
    `_MANUAL_CONFIG_FIELDS`) rather than silently accepting a field that
    would then do nothing.
    """
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="config must be a JSON object.")
    unknown = sorted(set(data) - allowed_fields)
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
    # `forced_class` skips stage 0's signal computation entirely, so a value
    # outside CLASSES matches no downstream branch and silently takes the flat
    # path. Checked here so a client typo is a 400 naming the valid values,
    # rather than the ValueError `stage0_classify.classify` raises — which
    # would reach the caller as a 500.
    forced = data.get("forced_class")
    if forced is not None and forced not in CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown forced_class {forced!r}. Valid: {', '.join(CLASSES)}.",
        )
    if "deleted_shape_ids" in allowed_fields or "shape_overrides" in allowed_fields:
        _canonicalize_shape_edits(data, len(load_chart(brand or DEFAULT_BRAND)))
    return data


def _parse_config(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"config is not valid JSON: {exc}") from exc
    return _validate_config_dict(data, _CONFIG_FIELDS)


# Manual digitizing skips stages 1-4 entirely (no auto-digitize generation to
# have assigned shape_ids in the first place), so the review-edit fields that
# reference a PRIOR generation's ids are meaningless here — excluded rather
# than silently accepted-and-ignored, the same reasoning `debug_dir` is
# already excluded from `_CONFIG_FIELDS` for. `merge_shape_ids`/`split_shapes`
# (contract v1.5) reference prior-generation ids exactly as much as
# `deleted_shape_ids`/`shape_overrides` do, so they are excluded here too.
_MANUAL_CONFIG_FIELDS = _CONFIG_FIELDS - {
    "deleted_shape_ids", "shape_overrides", "merge_shape_ids", "split_shapes",
}


def _parse_manual_config(data: dict | None) -> dict:
    return _validate_config_dict(data if data is not None else {}, _MANUAL_CONFIG_FIELDS)


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
                # The within-layer sew-order override in effect, if any
                # (shape-layers contract v1.2) — echoed back the same way
                # `layer` is, so the panel can tell an applied override from
                # the nearest-neighbour default it falls back to.
                "sew_order": r.meta.get("sew_order"),
                # Effective stitched state (pipeline.py resolves this off
                # shape_overrides, defaulting an enclosed-background region to
                # False) — exposed so a client can tell which shapes are
                # excluded by default and need a restore action.
                "stitched": r.meta.get("stitched", True),
                # Whether this enclosed region's colour is a flattening
                # artifact rather than a decision (contract v1.7, server-
                # computed, read-only — no `_OVERRIDE_KEYS` entry, same
                # category as `text_candidate` below): an ALPHA-derived hole
                # inherits whatever RGB the exporter flattened under the
                # transparency, usually the enclosing ring's own colour
                # (stage4_vectorize.py's setter comment has the full story).
                # Exposed so a client restoring such a shape can mark it as
                # needing a real thread choice instead of sewing the
                # inherited one silently. Always present; False for a
                # colour-KNOWN enclosed region and for everything untagged.
                "enclosed_colour_unknown": r.meta.get(
                    "enclosed_colour_unknown", False),
                # Text-cluster detection (server-computed, read-only — no
                # `_OVERRIDE_KEYS` entry, same category as `layer` and
                # `enclosed_background`): whether this shape was tagged as a
                # member of a detected text cluster, and which one.
                "text_candidate": r.meta.get("text_candidate", False),
                "text_cluster_id": r.meta.get("text_cluster_id"),
                # Per-member OCR read of a tagged member (server-computed,
                # read-only — same category as `text_candidate` above, no
                # `_OVERRIDE_KEYS` entry, never client-submitted): a single
                # best-guess character plus Tesseract's own confidence
                # (0..100), or both `None` when nothing was tagged, or when
                # the measurement itself failed. Studio decides whether/how
                # to use this (the confidence GATE is Studio's call, not the
                # service's) — see `digitizer_core/textcluster.py`'s
                # `ocr_suggest_text` and `app/src/lib/digitizer.js`'s
                # `textClusterSeed`.
                "ocr_char": r.meta.get("ocr_char"),
                "ocr_confidence": r.meta.get("ocr_confidence"),
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
        "generations": generations.stats(),
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
    gen_key = generation_key(data, cfg_dict)
    pixels = await run_in_threadpool(_decode, data)

    def work() -> dict:
        cfg = PipelineConfig(**cfg_dict)
        # The generation cache: stages 0-4 keyed on artwork + every config
        # field EXCEPT the review-edit keys, so an edited re-digitize reuses
        # the expensive prefix. The cached original stays pristine — every
        # use (cold path included, since the original goes into the cache)
        # finishes from a fork; see `Generation.fork` for what that isolates.
        gen = generations.get(gen_key)
        gen_hit = gen is not None
        if gen is None:
            gen = build_generation(pixels, cfg)
            generations.put(gen_key, gen)
        result = finish_generation(gen.fork(), cfg)
        plan = plan_stitches(result, cfg)
        design = plan_to_design(plan, name="Digitized design")
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
            # Observability for the loop this cache exists for (and for the
            # tests that pin it): whether stages 0-4 were reused. Studio
            # ignores it.
            "generation_cache": "hit" if gen_hit else "miss",
        }

    job, cached = registry.submit(key, work)
    return {"job_id": job.id, "state": job.state, "cached": cached}


# The upper bound on how many shapes one manual request may carry. Not a
# machine limit (a design this dense would already be a bad idea to sew) —
# it exists so a pathological body cannot make polygon validation itself the
# expensive part of the request.
MAX_MANUAL_SHAPES = 2000


@app.post("/digitize-manual", status_code=202)
async def start_digitize_manual(
    payload: dict = Body(...),
    x_embbot_token: str | None = Header(None),
) -> dict:
    """Hand-authored shapes in — no image, stages 1-4 skipped entirely — a
    job id out. Poll `/jobs/{id}` exactly as `/digitize`'s caller does: the
    finished job carries the identical `{design, review, stats, warnings,
    preflight}` shape, because it is built from the same `PipelineResult` /
    `StitchPlan` contract and handed to the same response helpers.

    Body: `{"shapes": [...], "config": {...}}`. Each shape:
        polygon: [[x, y], ...]        required, mm, y-axis down, >= 3 points
        holes: [[[x, y], ...], ...]   optional interior rings, mm
        technique: "satin"|"fill"|"run"   required — no "auto": a manual
                                       shape is a deliberate choice
        thread_index: int             exactly one of thread_index /
        thread_rgb: [r, g, b]         thread_rgb (nearest CIEDE2000 snap)
        fill_angle_deg: number        optional per-shape fill angle

    `config` is the same `PipelineConfig` field set `/digitize` accepts,
    minus `deleted_shape_ids`/`shape_overrides` (nothing here for those to
    reference — see `_MANUAL_CONFIG_FIELDS`). `target_width_mm` is accepted
    but unused: a shape's polygon is already literal millimetres, not pixels
    to be scaled against a target width.

    A malformed shape (empty list, self-intersecting/degenerate polygon, bad
    thread selection, unsupported technique) is a 400 at submit, same as a
    bad shape_overrides entry on `/digitize` — never a failed job.
    """
    _require_token(x_embbot_token)

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be a JSON object.")
    shapes = payload.get("shapes")
    if not isinstance(shapes, list) or not shapes:
        raise HTTPException(
            status_code=400, detail="payload.shapes must be a non-empty list of shapes."
        )
    if len(shapes) > MAX_MANUAL_SHAPES:
        raise HTTPException(
            status_code=413,
            detail=f"{len(shapes)} shapes were submitted; the limit is {MAX_MANUAL_SHAPES}.",
        )

    cfg_dict = _parse_manual_config(payload.get("config"))
    key = content_key(
        json.dumps(shapes, sort_keys=True, separators=(",", ":"), default=str).encode(),
        cfg_dict,
    )
    cfg = PipelineConfig(**cfg_dict)

    # Validation/construction runs before the job queue, same split
    # `/digitize` makes with `_decode`: a bad request fails at submit, and a
    # job slot is never spent on it. Off the event loop thread since it is
    # real (if cheap) geometry work, not because it is typically slow.
    try:
        result = await run_in_threadpool(build_manual_result, shapes, cfg)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def work() -> dict:
        plan = plan_stitches(result, cfg)
        design = plan_to_design(plan, name="Manual design")
        return {
            "design": design,
            "review": _review_payload(result, plan),
            "stats": _stats_payload(plan, design),
            "warnings": plan.warnings,
            # No artwork ever backed this generation, so the thread-match and
            # photo-guardrail checks are skipped exactly as they are for a
            # caller re-scoring a stored plan (`run_preflight`'s own
            # documented image=None contract) — everything else still runs.
            "preflight": run_preflight(result, plan, cfg, image=None)
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
