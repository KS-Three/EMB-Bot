#!/usr/bin/env python
"""Which lane does each pro job reach, and what does each route cost against the pro's file?

The largest step between an upload and a file that still needs a human hand is the
customer noticing a misroute and clicking "Sew as flat art" (DOCTRINE 2026-09-30).
Kent's open ruling is plan 2026-09-08's PR 6b, "route by consequence". This is
MEASUREMENT ONLY (ROADMAP gate 2): it builds nothing, edits no engine file, and
changes no routing. It puts the three routes side by side on the pro jobs, each
judged against the pro's file for the same job, so the ruling can be made from a
table.

THE ARMS (every one the Studio's request, `tools.pro_pair.request`, at the job's
pro width and garment: detect_photographic, faces_route_flat, max_colors 6):

  auto     what an upload gets today.
  flat     `forced_class="flat"`, the Studio's "Sew as flat art" button. The key is
           `tools.flip_sheet.PROXIES["flat_off"]`, imported, not retyped.
  6b       Kent's 6b AS WRITTEN (`SIXB_TEXT`, verbatim from the plan): when the
           design ramp REFUSES a gradient-class design and nothing is photographic,
           segment with `stage2_quantize.quantize` and KEEP the gradient class for
           reporting. Measured with a shim around three names in
           `digitizer_core.pipeline` for the length of one run (`sixb_shim`); no
           engine file is touched. Everything after stage 2 still sees "gradient",
           which is the literal reading, and a hybrid nobody has sewn.
  planner  the planner's variant, labelled as the planner's and NOT Kent's: flat
           (the whole flat route) only where stage 0 says gradient, the ramp gate
           refuses, and nothing is photographic. Where that gate does not fire the
           planner's route IS auto, and where it fires the planner's route IS flat,
           so this arm costs no run of its own: it is a pick between two arms.

THE ROW, per arm: the lane (stage 0's class and which region former ran), stitches
and trims READ FROM THE WRITTEN DST (one pystitch reader on ours and the pro's:
`pro_pair.pro_counts`), cones against the Studio's max_colors 6 (distinct thread
numbers that sew; DOCTRINE 2026-09-10: forced flat once sewed Golden Tee in 24
cones under a budget of 12), and two CHANCE-CORRECTED agreements with the pro's
file (ROADMAP gate 4: no raw agreement is quoted anywhere):

  thread kappa  `blockcensus.grouping_join`: each sewn region of ours is assigned
                to the pro colour block it sits on most; kappa of that against the
                pro's visible block map, over the area both cover. It asks "does
                our region partition reproduce the pro's colour allocation".
  sttype kappa  `scorecard`'s stitch-type (satin / fill / run) agreement over the
                shared solid area, the figure `pro_parity/kappacheck.py` compares.

and, on the four jobs `testdata/word_legibility_words.json` pins words for, the
chance-corrected per-word legibility cc of `tools/word_legibility.py`.

    python -m tools.lane_census premise [--local]       # which lane, every job (stops at the region former)
    python -m tools.lane_census run [--only SLUG ...] [--arms auto,flat,sixb] [--local]
    python -m tools.lane_census cc                      # word legibility, from the cache
    python -m tools.lane_census table                   # the tables, markdown
    python -m tools.lane_census sheet [--only SLUG ...] # art | auto | flat | 6b | pro

Everything is cached under `--cache` (default digitizer/debug_out/lane_census), one
JSON per (job, arm); `run` skips what is cached for the SAME engine tree. Run one at a
time: the laptop is shared. Rows whose art or pro file is not committed (ProSeal's art,
Bridge's pro file) are measured where the file exists and are never written into a
committed doc (`Job.committed`).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

# The test environment's OpenCV pins IPP's AVX2 path on every host (tests/conftest.py),
# because a stitch stream's bytes follow the path IPP dispatches to. The census pins
# it too, so a row measured on Kent's laptop and one measured on CI agree.
os.environ.setdefault("OPENCV_IPP", "avx2")
# One OpenMP team per process: this pass shares the machine with other sessions.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

DIGITIZER = Path(__file__).resolve().parent.parent
REPO = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

PLAN_FILE = REPO / "docs" / "superpowers" / "plans" / "2026-09-08-real-logo-lane-and-thin-strokes.md"
DEFAULT_CACHE = DIGITIZER / "debug_out" / "lane_census"
OUT_RENDERS = REPO / "docs" / "renders" / "lane-census-2026-10-25"

#: The Studio's colour budget (app/src/lib/project.js DEFAULT_DIGITIZE_PARAMS), which
#: `tools.pro_pair.request` carries.
STUDIO_MAX_COLORS = 6

#: `scorecard.CHANCE_DEGENERATE`: past this chance floor the two sides share one label,
#: there is nothing to discriminate, and the "kappa" is the raw number passed through.
#: Such a cell is marked `d` and is not evidence of agreement.
DEGENERATE = 0.999

#: Kent's 6b, VERBATIM from the plan (section 5a, "It does not." bullet), whitespace
#: collapsed. A test pins that this is a substring of the plan, so the doc cannot
#: quote a paraphrase.
SIXB_TEXT = (
    "PR 6b routes by consequence instead of by statistic: when "
    "`design_ramp.fit_design_ramp` REFUSES a gradient-class design and "
    "`is_photographic` is false (declared, or detected per review item 13), segment "
    "with `stage2_quantize.quantize` while keeping the gradient class for reporting."
)

ARMS = ("auto", "flat", "sixb", "planner")
#: the arms that are an engine run of their own; `planner` is a pick between two of them
RUN_ARMS = ("auto", "flat", "sixb")
ARM_LABEL = {
    "auto": "auto",
    "flat": "forced flat (Sew as flat art)",
    "sixb": "6b, as written (Kent's text)",
    "planner": "planner's variant (NOT Kent's)",
}

#: The brief's pairs, in its order. `bridge_hat` has no pro file on this box.
SLUGS = [
    "becker_hat_large", "becker_lc_large", "becker_hat_small", "becker_chest_small",
    "becker_beanie", "hotel_fremont_hat", "hotel_fremont_patch", "bridge_hat",
    "gaulke_roofing_hat", "gaulke_roofing_lc", "golf_hat", "precision_drone",
    "tires_hat_3d", "mfab_hat", "mfab_lc", "proseal_hat",
]

#: slug -> word_legibility job key (the four jobs with pinned words)
WL_JOBS = {"hotel_fremont_hat": "fremont", "becker_hat_large": "becker",
           "mfab_hat": "mfab", "proseal_hat": "proseal"}

#: The two committed fixtures the tests pin, with the pro width and garment each pair
#: is run at. The widths are the registered DST extents (`pro_intake.pair_record`,
#: 2026-10-25); `tests/test_lane_census.py` re-reads the pro file where it exists.
PINNED = {
    "becker_lc_large": {"art": "becker_marine_logo.png", "garment": "left_chest", "width_mm": 95.7},
    "hotel_fremont_hat": {"art": "photo/logo_hotel_fremont.webp", "garment": "hat_front", "width_mm": 92.6},
}


# ------------------------------------------------------------------ jobs
@dataclass
class Job:
    slug: str
    art: Path
    pro_dst: Path
    pro_pes: Path | None
    garment: str
    width_mm: float

    @property
    def committed(self) -> bool:
        """True when the art is a file this repo already ships (under testdata/).
        A row whose art is not is measured locally and never written to a doc."""
        try:
            self.art.resolve().relative_to((DIGITIZER / "testdata").resolve())
            return True
        except ValueError:
            return False


def resolve_job(slug: str) -> tuple[Job | None, str]:
    """-> (job, "") or (None, why not). Resolved through `tools.pro_intake`'s registry,
    which carries the committed art, the pro's DST (and PES where there is one), the
    garment its name says and the width its stitches span."""
    from tools.pro_intake import pair_record
    rec = pair_record(slug)
    if rec is None:
        return None, "not registered: no pro file for this pair on this box"
    if not rec.get("art"):
        return None, "no source art registered for this pair"
    if not rec.get("dst"):
        return None, "no pro DST"
    return Job(slug, Path(rec["art"]), Path(rec["dst"]), Path(rec["pes"]) if rec.get("pes") else None,
               rec.get("garment_id") or "hat_front", float(rec["width_mm"])), ""


def pinned_job(slug: str) -> Job:
    """A pinned fixture as a `Job`, with no registry and no pro file (CI has neither)."""
    spec = PINNED[slug]
    return Job(slug, DIGITIZER / "testdata" / spec["art"], Path(""), None, spec["garment"], spec["width_mm"])


# ------------------------------------------------------------------ the rule
def lane_facts(gen, cfg) -> dict:
    """What the 6b / planner rule reads, off a `Generation` and the caller's config.
    `ramp` is "fitted" or "none": none means the gate refused, or the design is not
    gradient-class and the gate never ran (read it with `class`)."""
    codes = {w.get("code") for w in (getattr(gen, "prep_warnings", None) or [])}
    return {
        "class": gen.classification_class,
        "ramp": "fitted" if getattr(gen, "design_ramp", None) is not None else "none",
        "ramp_enabled": bool(getattr(cfg, "design_ramp", True)),
        "photographic": bool(getattr(gen, "detected_photographic", False))
        or getattr(cfg, "is_photographic", None) is True,
        "faces_routed_flat": "FACE_ROUTED_FLAT" in codes,
        "segmenter": getattr(gen, "seg_name", None),
    }


def sixb_gate(facts: dict) -> tuple[bool, str]:
    """Kent's 6b condition, from `SIXB_TEXT`: "fit_design_ramp REFUSES a gradient-class
    design and is_photographic is false (declared, or detected)". -> (fires, why).
    The planner's variant uses the SAME gate and differs only in what it does when it
    fires, so there is one rule here and it cannot drift between the two arms."""
    if facts["class"] != "gradient":
        return False, f"stage 0 says {facts['class']}"
    if not facts.get("ramp_enabled", True):
        return False, "design_ramp is off: there is no gate to refuse"
    if facts["ramp"] == "fitted":
        return False, "the ramp gate FITS a sweep"
    if facts["photographic"]:
        return False, "photographic (declared or detected)"
    return True, "gradient class, ramp refused, not photographic"


def planner_arm(auto_facts: dict) -> str:
    """The run the planner's variant IS: flat where the gate fires, auto where not."""
    return "flat" if sixb_gate(auto_facts)[0] else "auto"


def sixb_arm(auto_facts: dict) -> str:
    """The run Kent's 6b IS: its own (shimmed) run where the gate fires, auto where not."""
    return "sixb" if sixb_gate(auto_facts)[0] else "auto"


def arm_extra(arm: str) -> dict:
    """The `--set` keys an arm lays over the Studio request."""
    if arm == "flat":
        from tools.flip_sheet import PROXIES
        return dict(PROXIES["flat_off"])      # {"forced_class": "flat"}, the proxy flip_sheet runs
    if arm in ("auto", "sixb"):
        return {}
    raise ValueError(f"{arm!r} is not an arm that runs; the planner's variant is a pick")


def studio_request(job: Job, arm: str) -> dict:
    from tools import pro_pair
    return pro_pair.request(job.width_mm, job.garment, arm_extra(arm))


# ------------------------------------------------------------------ the shim
class _Stop(BaseException):
    """Raised by the probe at the region-former dispatch to end `build_generation` there.
    A BaseException so no `except Exception` between the dispatch and the caller eats it."""


@contextmanager
def sixb_shim(active: bool, *, stop: bool = False):
    """Observe the lane, and measure 6b AS WRITTEN, without editing the engine.

    Wraps `digitizer_core.pipeline`'s `classify`, `fit_design_ramp`, `photo_segment` and
    `quantize` for the length of the `with`. `fit_design_ramp` is only called for a
    gradient-class design with the ramp enabled, so a recorded refusal is exactly
    "REFUSES a gradient-class design". With `active`, `photo_segment` then hands the work
    to `quantize` when that refusal stands and `cfg.is_photographic` is not True (the
    pipeline's local cfg, so "declared, or detected"). The classification is not touched:
    the gradient class stays for everything after stage 2, the plan's "keeping the
    gradient class for reporting" read literally. Inactive, it only records, so every
    arm's lane is OBSERVED, not inferred. With `stop`, the first region former to be
    reached ends the build (`_Stop`): the premise needs the dispatch, not stages 2-4.
    -> a dict: class, former, swapped, ramp_called, ramp_refused, photographic,
    faces_routed_flat."""
    from digitizer_core import pipeline
    seen = {"class": None, "former": None, "swapped": False, "ramp_called": False, "ramp_refused": False,
            "photographic": False, "faces_routed_flat": False}
    real_cls, real_fit = pipeline.classify, pipeline.fit_design_ramp
    real_seg, real_q = pipeline.photo_segment, pipeline.quantize

    def cls(image, cfg, *a, forced_class=None, **k):
        out = real_cls(image, cfg, *a, forced_class=forced_class, **k)
        seen["class"] = out.class_
        # the faces route re-asks stage 0 with forced_class="flat" on a config that did not force it
        if forced_class == "flat" and getattr(cfg, "forced_class", None) is None:
            seen["faces_routed_flat"] = True
        return out

    def fit(*a, **k):
        out = real_fit(*a, **k)
        seen["ramp_called"], seen["ramp_refused"] = True, out is None
        return out

    def seg(p, cfg, *a, **k):
        seen["photographic"] = getattr(cfg, "is_photographic", None) is True
        if active and seen["ramp_called"] and seen["ramp_refused"] and not seen["photographic"]:
            seen["swapped"], seen["former"] = True, "quantize"
            if stop:
                raise _Stop()
            return real_q(p, cfg)
        seen["former"] = "photo_segment"
        if stop:
            raise _Stop()
        return real_seg(p, cfg, *a, **k)

    def quant(p, cfg):
        seen["former"] = "quantize"
        seen["photographic"] = getattr(cfg, "is_photographic", None) is True
        if stop:
            raise _Stop()
        return real_q(p, cfg)

    pipeline.classify, pipeline.fit_design_ramp = cls, fit
    pipeline.photo_segment, pipeline.quantize = seg, quant
    try:
        yield seen
    finally:
        pipeline.classify, pipeline.fit_design_ramp = real_cls, real_fit
        pipeline.photo_segment, pipeline.quantize = real_seg, real_q


def parse_request(job: Job, arm: str):
    """The Studio's request for (job, arm) as the service parses it -> (cfg, upload bytes)."""
    from digitizer_core import PipelineConfig
    from digitizer_service.app import _parse_config
    return (PipelineConfig(**_parse_config(json.dumps(studio_request(job, arm)))), job.art.read_bytes())


def probe_facts(seen: dict, cfg) -> dict:
    """`lane_facts` for a probe, which has the shim's record and no `Generation`."""
    return {"class": seen["class"], "ramp": "fitted" if seen["ramp_called"] and not seen["ramp_refused"] else "none",
            "ramp_enabled": bool(getattr(cfg, "design_ramp", True)), "photographic": seen["photographic"],
            "faces_routed_flat": seen["faces_routed_flat"], "segmenter": None}


def lane_of(job: Job, arm: str) -> dict:
    """The lane an arm reaches on a job: stages 0-1 and the ramp fit, stopped at the
    region-former dispatch. -> class, former, whether 6b's swap happened, the rule's facts.
    Minutes cheaper than a run, and the same decision: the dispatch is where the pipeline
    commits to a lane."""
    from digitizer_core.pipeline import build_generation
    from digitizer_service.app import _decode as svc_decode
    cfg, data = parse_request(job, arm)
    with sixb_shim(arm == "sixb", stop=True) as seen:
        try:
            build_generation(svc_decode(data), cfg, exif_source=data)
        except _Stop:
            pass
    facts = probe_facts(seen, cfg)
    return {"arm": arm, "class": facts["class"], "former": seen["former"], "swapped": seen["swapped"],
            "facts": facts}


# ------------------------------------------------------------------ counting
def cones_of(plan) -> int:
    """Distinct thread numbers that sew (`tools/color_cap.py`'s count)."""
    return len({b.thread_number for b in plan.blocks if any(len(r.points) for r in b.runs)})


def pes_cones(pes: Path | None) -> int | None:
    """Distinct thread colours in the pro's PES, or None for a DST-only job (a DST
    carries no palette: the stops are all it can say)."""
    if pes is None or not Path(pes).exists():
        return None
    import pystitch
    pat = pystitch.read(str(pes))
    return len({t.color for t in pat.threadlist}) if pat is not None else None


def file_counts(path: Path, pes: Path | None = None) -> dict:
    """Stitches, trims and colour changes as ONE pystitch reader reads a machine file
    (`pro_pair.pro_counts`), plus the stops it implies and the cones the PES names."""
    from tools import pro_pair
    c = pro_pair.pro_counts(path)
    return {"stitches": c["stitches"], "trims": c["trims"], "stops": c["colour_changes"] + 1,
            "width_mm": c["width_mm"], "height_mm": c["height_mm"], "cones": pes_cones(pes)}


# ------------------------------------------------------------------ kappa
def thread_join(pro_dst: Path, plan, result) -> dict:
    """The thread kappa: `blockcensus.grouping_join` of our SEWN regions onto the pro's
    colour blocks, registered the way `blockcensus.join_fixture` registers (the shipped
    scorecard's translation search). Regions with no stitch of their own (an unsewn
    enclosed background) are left out: they have no thread to agree with."""
    from tools.pro_parity import blockcensus as bc, prep_all, scorecard
    p_blocks = prep_all.decode(pro_dst)[0]
    pro_segs = bc.runs_to_segs(p_blocks)
    plan_blocks = [[list(r.points) for r in b.runs] for b in plan.blocks]
    our_segs = bc.runs_to_segs(plan_blocks)
    bb0 = scorecard.bounds(pro_segs, our_segs)
    dx, dy, reg_iou = scorecard.register(pro_segs, our_segs, bb0)
    bb = scorecard.bounds(pro_segs, scorecard.shifted(our_segs, dx, dy))
    pro_closed, _raw, _areas = bc.paint_block_masks(p_blocks, bb)
    sewn = {str(run.shape_id) for _b, run in plan.iter_runs()}
    regions = [r for r in result.regions if str(r.shape_id) in sewn]
    masks = bc.paint_polygon_masks([r.polygon for r in regions], bb, shift=(dx, dy))
    j = bc.grouping_join(pro_closed, masks)
    keep = ("kappa", "raw_agreement", "chance", "degenerate", "regions", "regions_assigned",
            "pro_blocks", "blocks_unhit", "joint_area_mm2", "error")
    return {**{k: j[k] for k in keep if k in j}, "reg_iou": round(float(reg_iou), 3),
            "shift_mm": [round(float(dx), 2), round(float(dy), 2)]}


def write_score_dir(out: Path, pro_dst: Path, plan) -> Path:
    """The two stitch CSVs and two block files `scorecard.score_design` reads, written
    the way `prep_all.main` (pro) and `prep_all.run_ours` (ours) write them."""
    from tools.pro_parity import prep_all
    out.mkdir(parents=True, exist_ok=True)
    blocks, breaks, threads, _bounds, _j, _t = prep_all.decode(pro_dst)
    with open(out / "pro_stitches.csv", "w") as f:
        f.write("block,run,trim,jump,x_mm,y_mm\n")
        for i, runs in enumerate(blocks):
            for ri, (r, kind) in enumerate(zip(runs, breaks[i])):
                t = 1 if kind in ("trim", "color") else 0
                j = 1 if kind == "jump" else 0
                for k, (x, y) in enumerate(r):
                    f.write(f"{i},{ri},{t if k == 0 else 0},{j if k == 0 else 0},{x:.2f},{y:.2f}\n")
    (out / "pro_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(threads[i])} for i in range(len(blocks))]), encoding="utf-8")
    with open(out / "ours_stitches.csv", "w") as f:
        f.write("block,run,trim,jump,x_mm,y_mm\n")
        started = False
        for i, b in enumerate(plan.blocks):
            for ri, r in enumerate(b.runs):
                if not r.points:
                    continue
                trim = 1 if (getattr(r, "trim", False) or (ri == 0 and i > 0)) else 0
                jump = 1 if (getattr(r, "jump", False) and started and not trim) else 0
                for k, (x, y) in enumerate(r.points):
                    f.write(f"{i},{ri},{trim if k == 0 else 0},{jump if k == 0 else 0},{x:.2f},{y:.2f}\n")
                started = True
    (out / "ours_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(b.rgb)} for i, b in enumerate(plan.blocks)]), encoding="utf-8")
    return out


def sttype_kappa(score: dict) -> dict:
    """The stitch-type kappa out of a `score_design` result: corrected, raw and the
    chance floor beside it (`pro_parity/kappacheck.py`'s three columns), and direction."""
    return {"kappa": score["parts"]["sttype"], "raw": score["parts_raw"]["sttype"],
            "chance": score["detail"]["chance_floor"].get("sttype"),
            "direction_kappa": score["parts"]["direction"],
            "solid_iou": score["detail"].get("solid_iou"),
            "type_cells": score["detail"].get("type_cells")}


# ------------------------------------------------------------------ the engine
def engine_identity() -> dict:
    """The tree the numbers were measured on: HEAD, and the tree hash of the two
    directories the engine lives in, so a docs-only commit does not look like a new
    engine and an engine edit cannot hide behind a clean HEAD."""
    def git(*args) -> str:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = git("status", "--porcelain", "--", "digitizer/digitizer_core", "src")
    return {"head": git("rev-parse", "--short=8", "HEAD"),
            "tree": (git("rev-parse", "--short=12", "HEAD:digitizer/digitizer_core")
                     + "+" + git("rev-parse", "--short=12", "HEAD:src")),
            "dirty": bool(dirty), "opencv_ipp": os.environ.get("OPENCV_IPP")}


# ------------------------------------------------------------------ one run
def cache_path(cache: Path, slug: str, arm: str) -> Path:
    return cache / "rows" / f"{slug}__{arm}.json"


def measure(job: Job, arm: str, cache: Path, *, kappas: bool = True) -> dict:
    """One (job, arm) full run through the product's own path (`pro_pair.digitize`),
    its DST written and read back, its lane observed, its kappas computed."""
    from digitizer_core.export import write_dst
    from tools import pro_pair
    t0 = time.time()
    with sixb_shim(arm == "sixb") as seen:
        d = pro_pair.digitize(job.art, job.width_mm, job.garment, arm_extra(arm))
    facts = lane_facts(d.gen, d.cfg)
    out = cache / "files" / job.slug / arm
    out.mkdir(parents=True, exist_ok=True)
    dst = write_dst(d.plan, out / "ours.dst")
    row = {
        "slug": job.slug, "arm": arm, "width_mm": job.width_mm, "garment": job.garment,
        "engine": engine_identity(), "facts": facts, "former": seen["former"],
        "swapped": seen["swapped"], "gate": dict(zip(("fires", "why"), sixb_gate(facts))),
        "ours": {**file_counts(dst), "cones": cones_of(d.plan), "plan_stitches": d.plan.stats.stitch_count,
                 "plan_trims": d.plan.stats.trims},
        "warnings": sorted({w.get("code") for w in (getattr(d.plan, "warnings", None) or []) if w.get("code")}),
        "regions": len(d.result.regions),
        "pro": file_counts(job.pro_dst, job.pro_pes),
    }
    if kappas:
        try:
            row["thread"] = thread_join(job.pro_dst, d.plan, d.result)
        except Exception as e:                                         # noqa: BLE001 -- a row, not a crash
            row["thread"] = {"error": f"{type(e).__name__}: {e}"[:300]}
        try:
            from tools.pro_parity import scorecard
            sd = write_score_dir(out / "score" / job.slug, job.pro_dst, d.plan)
            row["sttype"] = sttype_kappa(scorecard.score_design(sd))
        except Exception as e:                                         # noqa: BLE001
            row["sttype"] = {"error": f"{type(e).__name__}: {e}"[:300]}
    with gzip.open(out / "design.json.gz", "wt", encoding="utf-8") as f:
        json.dump(d.design, f)
    row["secs"] = round(time.time() - t0, 1)
    path = cache_path(cache, job.slug, arm)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=1, default=str), encoding="utf-8")
    return row


def load_row(cache: Path, slug: str, arm: str) -> dict | None:
    p = cache_path(cache, slug, arm)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ------------------------------------------------------------------ the derived arms
def effective_row(rows: dict[str, dict], arm: str) -> tuple[dict | None, str]:
    """The row an arm stands for on one job: -> (row, "own" | "= auto" | "= flat").
    `rows` maps run-arm -> row. `planner` and a 6b whose gate does not fire are picks."""
    auto = rows.get("auto")
    if arm in ("auto", "flat"):
        return rows.get(arm), "own"
    if auto is None:
        return None, "own"
    if arm == "planner":
        pick = planner_arm(auto["facts"])
        return rows.get(pick), f"= {pick}" if pick != "auto" else "= auto"
    if arm == "sixb":
        if not sixb_gate(auto["facts"])[0]:
            return auto, "= auto"
        return rows.get("sixb"), "own"
    raise ValueError(arm)


def lane_label(row: dict | None) -> str:
    if row is None:
        return "-"
    return f"{row['facts']['class']} / {row['former'] or '?'}"


def kappa_cell(block: dict | None) -> str:
    if not block:
        return "-"
    if "error" in block and "kappa" not in block:
        return "err"
    k = block.get("kappa")
    if k is None:
        return "-"
    return f"{k:+.2f}" + ("d" if block.get("degenerate") else "")


def sttype_cell(block: dict | None) -> str:
    if not block:
        return "-"
    if "error" in block and "kappa" not in block:
        return "err"
    k, raw, ch = block.get("kappa"), block.get("raw"), block.get("chance")
    if k is None:
        return "-"
    if raw is None or ch is None:
        return f"{k:.2f}"
    return f"{k:.2f}{'d' if ch >= DEGENERATE else ''} ({raw:.2f} / {ch:.2f})"


def cones_cell(n: int | None) -> str:
    if n is None:
        return "n/a"
    return f"{n}" + (f" (+{n - STUDIO_MAX_COLORS})" if n > STUDIO_MAX_COLORS else "")


def job_block(slug: str, rows: dict[str, dict], cc: dict | None = None) -> str:
    """One job's rows as a markdown table: the pro, then the four arms."""
    auto = rows.get("auto")
    if auto is None:
        return f"### {slug}\n\n(not measured)\n"
    fires, why = sixb_gate(auto["facts"])
    head = (f"### {slug} - {auto['garment']}, {auto['width_mm']:g} mm\n\n"
            f"6b gate: **{'fires' if fires else 'does not fire'}** ({why}).\n\n")
    lines = ["| route | lane (class / former) | stitches | trims | cones (budget 6) | thread kappa | sttype kappa (raw / chance) | cc |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    pro = auto["pro"]
    cc_pro = "-" if not cc or cc.get("pro") is None else f"{cc['pro']:+.2f}"
    lines.append(f"| the pro | - | {pro['stitches']} | {pro['trims']} | {cones_cell(pro['cones'])}"
                 f"{'' if pro['cones'] is not None else f' ({pro['stops']} stops)'} | - | - | {cc_pro} |")
    for arm in ARMS:
        row, how = effective_row(rows, arm)
        label = ARM_LABEL[arm] + ("" if how == "own" else f" - {how}")
        if row is None:
            lines.append(f"| {label} | not run | | | | | | |")
            continue
        o = row["ours"]
        cc_cell = "-"
        if cc:
            src = row["arm"]
            v = (cc.get("arms") or {}).get(src)
            cc_cell = "-" if v is None else f"{v:+.2f}"
        lines.append(f"| {label} | {lane_label(row)} | {o['stitches']} | {o['trims']} | {cones_cell(o['cones'])} "
                     f"| {kappa_cell(row.get('thread'))} | {sttype_cell(row.get('sttype'))} | {cc_cell} |")
    return head + "\n".join(lines) + "\n"


def load_premise(cache: Path) -> dict | None:
    f = cache / "premise.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def premise_table(premise: dict, *, local: bool) -> str:
    """Which lane each job reaches on today's engine under the Studio's request
    (the probe: stages 0-1 and the ramp fit, stopped at the region-former dispatch)."""
    lines = ["| job | garment | pro width | lane today (class / former) | ramp gate | photographic | 6b gate |",
             "|---|---|---:|---|---|---|---|"]
    for slug, j in premise["jobs"].items():
        if not j["committed"] and not local:
            continue
        f, gate = j["facts"], j["gate"]
        ramp = ("fits" if f["ramp"] == "fitted"
                else "refuses" if f["class"] == "gradient" else "n/a (not gradient)")
        lines.append(f"| {slug} | {j['garment']} | {j['width_mm']:g} mm | {j['class']} / {j['former']} | {ramp} | "
                     f"{'yes' if f['photographic'] else 'no'} | "
                     f"{'**fires**' if gate['fires'] else 'shut: ' + gate['why']} |")
    return "\n".join(lines) + "\n"


def lane_counts(premise: dict, *, local: bool) -> dict:
    """{class: n} over the jobs the table shows, and how many the 6b gate fires on."""
    jobs = [j for j in premise["jobs"].values() if j["committed"] or local]
    counts: dict[str, int] = {}
    for j in jobs:
        counts[j["class"]] = counts.get(j["class"], 0) + 1
    return {"jobs": len(jobs), "classes": counts, "gate_fires": sum(1 for j in jobs if j["gate"]["fires"])}


def probe_vs_runs(premise: dict, all_rows: dict[str, dict[str, dict]]) -> tuple[int, list[str]]:
    """Does the cheap probe name the same class and the same gate as the full run, per job?
    -> (jobs compared, the slugs that disagree)."""
    bad, n = [], 0
    for slug, rows in all_rows.items():
        auto, pj = rows.get("auto"), premise["jobs"].get(slug)
        if auto is None or pj is None:
            continue
        n += 1
        if auto["facts"]["class"] != pj["class"] or auto["gate"]["fires"] != pj["gate"]["fires"]:
            bad.append(slug)
    return n, bad


def dst_md5(cache: Path, slug: str, arm: str) -> str | None:
    f = cache / "files" / slug / arm / "ours.dst"
    return hashlib.md5(f.read_bytes()).hexdigest()[:8] if f.exists() else None


def _good_thread(row: dict) -> float | None:
    """The thread kappa of a row, or None when it is missing or DEGENERATE (the joint
    area is one label: nothing to discriminate, the figure is the raw number)."""
    t = row.get("thread") or {}
    return None if "kappa" not in t or t.get("degenerate") else t["kappa"]


def _good_sttype(row: dict) -> float | None:
    t = row.get("sttype") or {}
    if "kappa" not in t or (t.get("chance") or 0.0) >= DEGENERATE:
        return None
    return t["kappa"]


def identity_table(cache: Path, all_rows: dict[str, dict[str, dict]]) -> str:
    """Byte identity of the written DSTs: forced flat against auto, and 6b as written
    against forced flat. Where the 6b gate does not fire 6b IS auto and is not listed."""
    lines = ["| job | auto class | forced flat == auto | 6b == forced flat | 6b minus flat (stitches / trims) |",
             "|---|---|---|---|---|"]
    for slug, rows in all_rows.items():
        auto, flat, sixb = rows.get("auto"), rows.get("flat"), rows.get("sixb")
        if auto is None or flat is None:
            continue
        same_af = dst_md5(cache, slug, "auto") == dst_md5(cache, slug, "flat")
        if sixb is None:
            s6, d6 = "n/a (gate shut)", ""
        else:
            same_sf = dst_md5(cache, slug, "sixb") == dst_md5(cache, slug, "flat")
            s6 = "byte-identical" if same_sf else "differs"
            d6 = "" if same_sf else (f"{sixb['ours']['stitches'] - flat['ours']['stitches']:+d} / "
                                     f"{sixb['ours']['trims'] - flat['ours']['trims']:+d}")
        lines.append(f"| {slug} | {auto['facts']['class']} | {'byte-identical' if same_af else 'differs'} | {s6} | {d6} |")
    return "\n".join(lines) + "\n"


def paired_table(cache: Path, all_rows: dict[str, dict[str, dict]], arm: str = "flat") -> str:
    """`arm` minus auto, on the jobs where the arm's DST differs from auto's, with the pro's
    counts beside so a delta can be read as toward or away from the pro. Thread and sttype
    kappa are skipped (shown `-`) on a degenerate row."""
    lines = [f"| job | stitches auto -> {arm} (pro) | trims auto -> {arm} (pro) | thread kappa delta | sttype kappa delta |",
             "|---|---|---|---:|---:|"]
    n = {"jobs": 0, "st_closer": 0, "tr_closer": 0, "th_up": 0, "th_down": 0, "th_same": 0,
         "ty_up": 0, "ty_down": 0, "ty_same": 0}
    for slug, rows in all_rows.items():
        auto, other = rows.get("auto"), effective_row(rows, arm)[0]
        if auto is None or other is None or dst_md5(cache, slug, auto["arm"]) == dst_md5(cache, slug, other["arm"]):
            continue
        ps, pt = auto["pro"]["stitches"], auto["pro"]["trims"]
        a, b = auto["ours"], other["ours"]
        n["jobs"] += 1
        n["st_closer"] += abs(b["stitches"] - ps) < abs(a["stitches"] - ps)
        n["tr_closer"] += abs(b["trims"] - pt) < abs(a["trims"] - pt)
        cells = []
        for good, key in ((_good_thread, "th"), (_good_sttype, "ty")):
            ka, kb = good(auto), good(other)
            if ka is None or kb is None:
                cells.append("-")
                continue
            d = kb - ka
            n[key + ("_same" if abs(d) < 0.005 else "_up" if d > 0 else "_down")] += 1
            cells.append("0.00" if abs(d) < 0.005 else f"{d:+.2f}")
        lines.append(f"| {slug} | {a['stitches']} -> {b['stitches']} ({ps}) | {a['trims']} -> {b['trims']} ({pt}) "
                     f"| {cells[0]} | {cells[1]} |")
    if n["jobs"]:
        lines.append(f"| **{n['jobs']} jobs** | closer to the pro's count on {n['st_closer']} | closer on {n['tr_closer']} "
                     f"| up {n['th_up']} / same {n['th_same']} / down {n['th_down']} "
                     f"| up {n['ty_up']} / same {n['ty_same']} / down {n['ty_down']} |")
    return "\n".join(lines) + "\n"


def summary_table(all_rows: dict[str, dict[str, dict]]) -> str:
    """Per arm across the jobs: lanes reached, stitches and trims against the pro,
    jobs over the cone budget, mean kappas. A mean is over the jobs where the figure
    exists and is NOT degenerate; n is stated beside each. Four of the 14 jobs are one
    logo (Becker) at four sizes, so a mean is dominated by what that logo does."""
    out = ["| route | jobs | lanes reached | median stitches / pro | median trims / pro | jobs over 6 cones | mean thread kappa | mean sttype kappa |",
           "|---|---:|---|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        picks = []
        for slug, rows in all_rows.items():
            row, _how = effective_row(rows, arm)
            if row is not None:
                picks.append((slug, row))
        if not picks:
            continue
        lanes: dict[str, int] = {}
        for _s, r in picks:
            lanes[lane_label(r)] = lanes.get(lane_label(r), 0) + 1
        st = [r["ours"]["stitches"] / r["pro"]["stitches"] for _s, r in picks if r["pro"]["stitches"]]
        tr = [r["ours"]["trims"] / r["pro"]["trims"] for _s, r in picks if r["pro"]["trims"]]
        over = sum(1 for _s, r in picks if r["ours"]["cones"] > STUDIO_MAX_COLORS)
        tk = [k for _s, r in picks if (k := _good_thread(r)) is not None]
        sk = [k for _s, r in picks if (k := _good_sttype(r)) is not None]
        lane_txt = ", ".join(f"{k} x{v}" for k, v in sorted(lanes.items()))
        out.append(f"| {ARM_LABEL[arm]} | {len(picks)} | {lane_txt} | {statistics.median(st):.2f} | "
                   f"{statistics.median(tr):.2f} | {over} | "
                   f"{statistics.mean(tk):+.2f} (n={len(tk)}) | {statistics.mean(sk):.2f} (n={len(sk)}) |")
    return "\n".join(out) + "\n"


def moved_table(old: Path, new: Path, *, local: bool) -> str:
    """Which rows moved between two caches (two engine trees): the lane, then the written
    DST. A row whose DST is byte-identical is counted, not listed."""
    lines = ["| job | arm | lane old -> new | stitches | trims | cones |", "|---|---|---|---|---|---|"]
    same = total = 0
    for slug in SLUGS:
        job, _ = resolve_job(slug)
        if job is None or (not job.committed and not local):
            continue
        for arm in RUN_ARMS:
            a, b = load_row(old, slug, arm), load_row(new, slug, arm)
            if a is None or b is None:
                continue
            total += 1
            if dst_md5(old, slug, arm) == dst_md5(new, slug, arm):
                same += 1
                continue
            la, lb = lane_label(a), lane_label(b)
            lines.append(f"| {slug} | {arm} | {la if la == lb else la + ' -> ' + lb} | "
                         f"{a['ours']['stitches']} -> {b['ours']['stitches']} | "
                         f"{a['ours']['trims']} -> {b['ours']['trims']} | {a['ours']['cones']} -> {b['ours']['cones']} |")
    lines.append(f"| **{same} of {total} rows byte-identical** | | | | | |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ commands
def pick_jobs(only: list[str] | None, *, allow_local: bool) -> list[Job]:
    jobs = []
    for slug in (only or SLUGS):
        job, why = resolve_job(slug)
        if job is None:
            print(f"skip {slug}: {why}")
            continue
        if not job.committed and not allow_local:
            print(f"skip {slug}: art is not committed (measure it with --local; never commit the row)")
            continue
        jobs.append(job)
    return jobs


def cmd_premise(a) -> int:
    """Stages 0-4 under the Studio request, on origin/main's engine: which lane."""
    a.cache.mkdir(parents=True, exist_ok=True)
    eng = engine_identity()
    print(f"engine {eng}")
    out = {}
    for job in pick_jobs(a.only, allow_local=a.local):
        t0 = time.time()
        lane = lane_of(job, "auto")
        fires, why = sixb_gate(lane["facts"])
        out[job.slug] = {"garment": job.garment, "width_mm": job.width_mm, "committed": job.committed,
                         **{k: lane[k] for k in ("class", "former")}, "facts": lane["facts"],
                         "gate": {"fires": fires, "why": why}}
        print(f"{job.slug:22s} {job.garment:11s} {job.width_mm:6.1f} mm  {lane['class']:9s} "
              f"ramp={lane['facts']['ramp']:6s} photo={lane['facts']['photographic']!s:5s} "
              f"faces->flat={lane['facts']['faces_routed_flat']!s:5s} 6b-gate={fires!s:5s} ({time.time() - t0:.0f}s)",
              flush=True)
    (a.cache / "premise.json").write_text(json.dumps({"engine": eng, "jobs": out}, indent=1), encoding="utf-8")
    return 0


def cmd_run(a) -> int:
    eng = engine_identity()
    print(f"engine {eng}")
    arms = [x for x in a.arms.split(",") if x]
    for job in pick_jobs(a.only, allow_local=a.local):
        for arm in arms:
            have = load_row(a.cache, job.slug, arm)
            if arm == "sixb":
                auto = load_row(a.cache, job.slug, "auto")
                if auto is not None and not sixb_gate(auto["facts"])[0]:
                    print(f"{job.slug:22s} {arm:5s} = auto (the 6b gate does not fire)")
                    continue
            if have and have["engine"]["tree"] == eng["tree"] and not a.force:
                print(f"{job.slug:22s} {arm:5s} cached")
                continue
            try:
                row = measure(job, arm, a.cache, kappas=not a.no_kappa)
            except Exception as e:                                     # noqa: BLE001 -- a failed run is a row
                import traceback
                (a.cache / "errors").mkdir(parents=True, exist_ok=True)
                (a.cache / "errors" / f"{job.slug}__{arm}.txt").write_text(traceback.format_exc(), encoding="utf-8")
                print(f"{job.slug:22s} {arm:5s} FAILED {type(e).__name__}: {str(e)[:200]}", flush=True)
                continue
            o = row["ours"]
            print(f"{job.slug:22s} {arm:5s} {lane_label(row):26s} st {o['stitches']:6d} trims {o['trims']:4d} "
                  f"cones {o['cones']:3d}  thread {kappa_cell(row.get('thread'))} sttype {sttype_cell(row.get('sttype'))} "
                  f"({row['secs']}s)", flush=True)
    return 0


def all_cached(cache: Path, *, local: bool) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for slug in SLUGS:
        rows = {arm: r for arm in RUN_ARMS if (r := load_row(cache, slug, arm))}
        if not rows:
            continue
        job, _ = resolve_job(slug)
        if job is not None and not job.committed and not local:
            continue
        out[slug] = rows
    return out


def load_cc(cache: Path, slug: str) -> dict | None:
    p = cache / "cc" / f"{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def cmd_table(a) -> int:
    allr = all_cached(a.cache, local=a.local)
    if not allr:
        print("nothing cached: run `run` first")
        return 1
    eng = next(iter(next(iter(allr.values())).values()))["engine"]
    print(f"engine {eng}\n")
    prem = load_premise(a.cache)
    if prem:
        counts = lane_counts(prem, local=a.local)
        print(f"PREMISE: {counts['jobs']} jobs, lanes {counts['classes']}, the 6b gate fires on {counts['gate_fires']}\n")
        print(premise_table(prem, local=a.local))
        n, bad = probe_vs_runs(prem, allr)
        print(f"the probe names the same class and gate as the full run on {n - len(bad)} of {n} jobs"
              f"{'' if not bad else ' (differs: ' + ', '.join(bad) + ')'}\n")
    print(summary_table(allr))
    print("Byte identity of the written DSTs:\n")
    print(identity_table(a.cache, allr))
    for arm in ("flat", "sixb", "planner"):
        print(f"{ARM_LABEL[arm]} minus auto, where it differs:\n")
        print(paired_table(a.cache, allr, arm))
    for slug, rows in allr.items():
        print(job_block(slug, rows, load_cc(a.cache, slug)))
    return 0


def cmd_cc(a) -> int:
    """Per-word legibility cc (`tools/word_legibility.read_job`) of every cached arm on
    the jobs with pinned words. Chance-corrected: cc is the reading's similarity to the
    word minus a shuffled-letters baseline, over the words scored in BOTH files."""
    from tools import word_legibility as wl
    from tools.glyph_legibility import load_source
    wl.JOBS.update({j: s for j, s in wl.registered_jobs().items() if j not in wl.JOBS})
    for slug, key in WL_JOBS.items():
        if a.only and slug not in a.only:
            continue
        words = wl.pinned_words(key)
        rows = {arm: r for arm in RUN_ARMS if (r := load_row(a.cache, slug, arm))}
        if not words or not rows:
            continue
        job, _ = resolve_job(slug)
        if job is None or (not job.committed and not a.local):
            continue
        spec = wl.JOBS[key]
        rgb, alpha = load_source(wl.resolve(spec["art"]))
        pro_design = wl.load_pro_design(wl.resolve(spec["pro"]))
        out = {"slug": slug, "key": key, "words": [w["text"] for w in words], "arms": {}, "arm_n": {},
               "tesseract": tesseract_version()}
        for arm, row in rows.items():
            with gzip.open(a.cache / "files" / slug / arm / "design.json.gz", "rt", encoding="utf-8") as f:
                design = json.load(f)
            res = wl.read_job(key, design, pro_design, words, rgb, alpha, True, None,
                              ours_width_mm=row["width_mm"], ladder=False)
            figs = res["figures"]
            ours, pro = figs.get("ours/native/both"), figs.get("pro/native/both")
            out["arms"][arm] = None if not ours or ours.get("cc") is None else ours["cc"]
            out["arm_n"][arm] = None if not ours else ours.get("words")
            out["pro"] = None if not pro or pro.get("cc") is None else pro["cc"]
            print(f"{slug:20s} {arm:5s} cc ours {out['arms'][arm]} pro {out['pro']} (n={out['arm_n'][arm]})", flush=True)
        (a.cache / "cc").mkdir(parents=True, exist_ok=True)
        (a.cache / "cc" / f"{slug}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


def tesseract_version() -> str | None:
    try:
        r = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        return (r.stdout or r.stderr).splitlines()[0].strip()
    except OSError:
        return None


def _label_lines(img, lines):
    """`pro_pair._label`, with a second line: a lane and its counts do not fit one band
    at the sheet's tile width."""
    import cv2
    import numpy as np
    band = np.full((22 * len(lines) + 8, img.shape[1], 3), 255, np.uint8)
    for i, text in enumerate(lines):
        cv2.putText(band, text, (6, 20 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([band, img[:, :, :3]])


def cmd_sheet(a) -> int:
    """art | auto | flat | 6b (where it ran) | pro, one JPG per job, through
    `tools.pro_pair`'s own tile helpers (imported). Drawn from the cached designs."""
    import cv2
    from digitizer_core import stitchviz
    from tools import pro_pair
    from tools.pro_parity import pairframe
    a.out.mkdir(parents=True, exist_ok=True)
    for slug, rows in all_cached(a.cache, local=a.local).items():
        if a.only and slug not in a.only:
            continue
        job, _ = resolve_job(slug)
        auto = rows.get("auto")
        if job is None or auto is None:
            continue
        ppm = 400.0 / job.width_mm
        tiles = [(["art", f"{job.width_mm:g} mm, {job.garment}"],
                  pro_pair._scaled(pro_pair._art_ink(job.art), job.width_mm, ppm, cv2.INTER_AREA))]
        for arm in ("auto", "flat", "sixb"):
            row = rows.get(arm)
            if row is None:
                continue
            with gzip.open(a.cache / "files" / slug / arm / "design.json.gz", "rt", encoding="utf-8") as f:
                design = json.load(f)
            o = row["ours"]
            tiles.append(([f"{arm}: {lane_label(row)}", f"{o['stitches']} st, {o['trims']} tr, {o['cones']} cones"],
                          stitchviz.render_design(design, px_per_mm=ppm)))
        pro_design = pairframe.design_for(job.pro_pes or job.pro_dst, None, None, slug)
        p = auto["pro"]
        tiles.append((["pro", f"{p['stitches']} st, {p['trims']} tr"],
                      stitchviz.render_design(pro_design, px_per_mm=ppm)))
        img = pro_pair._hstack([_label_lines(im, text) for text, im in tiles], gap=16)
        dest = a.out / f"{slug}.jpg"
        cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print("wrote", dest, flush=True)
    return 0


def cmd_diff(a) -> int:
    if a.old is None:
        print("diff needs --old CACHE")
        return 2
    print(moved_table(a.old, a.cache, local=a.local))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.lane_census", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("cmd", choices=["premise", "run", "cc", "table", "sheet", "diff"])
    ap.add_argument("--only", nargs="+", metavar="SLUG")
    ap.add_argument("--arms", default=",".join(RUN_ARMS), help="comma list of run arms")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--out", type=Path, default=OUT_RENDERS)
    ap.add_argument("--local", action="store_true",
                    help="also rows whose art is not committed (ProSeal): local use only, never a doc")
    ap.add_argument("--old", type=Path, help="diff: the cache of the engine to compare against")
    ap.add_argument("--force", action="store_true", help="re-run what is cached")
    ap.add_argument("--no-kappa", action="store_true", help="skip the two kappas (faster)")
    a = ap.parse_args(argv)
    return {"premise": cmd_premise, "run": cmd_run, "cc": cmd_cc, "table": cmd_table, "sheet": cmd_sheet,
            "diff": cmd_diff}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
