"""float_census: every needle-up move in ours and the pro's by class, and what `cut_every_jump` does with each float.

    python -m tools.float_census gen    [--jobs SLUG ...] [--cache DIR]   # stages 0-4 once per job, pickled
    python -m tools.float_census arms   [--jobs SLUG ...] [--cache DIR]   # OFF | ON | ON+fine off the pickle
    python -m tools.float_census report [--cache DIR] [--md OUT.md]       # per job and pooled, three definitions
    python -m tools.float_census dst    FILE [FILE ...]                   # any machine file's moves, by class

Built 2026-11-06 for MASTER_SCOPE defect 4. `docs/trim-defects-4-6-2026-10-29.md`
found we cut at the pro's rate (391 vs 409 over 17 jobs) while our needle-up
moves are 2.07x his (879 vs 425): 488 short floats left uncut against his 16.
That ratio counts every needle-up move as a break. Whether a needle-DOWN walk
on sewn thread -- what `cut_every_jump` makes of most floats on a field, and
the pro's own habit letter to letter (card v8, 2026-11-01) -- is a break was
unmeasured, so the 2.07x may overstate. This reads it.

ONE READER ON BOTH DSTs (`dst_moves`): every move between two penetrations
of one colour block is

  cut      a TRIM on the way (a run of TRIM records counts once);
  uncut    needle-up with no TRIM: a float someone snips by hand;
  walked   needle-down from one PIECE to another (`tools.between_walks`'
           `walked` step: pieces and visits are `tools.sequence_pro`'s, so
           a walk inside one piece -- letter to letter in a word that
           touches -- reads as stitching, not a walk).

The first penetration of a block is a colour change and is never counted.
Each cut's hop is also classed by `tools.trim_classes` (under_later /
on_work / bare_*), and the cuts inside one piece are `sequence_pro`'s
`trims - inter_trims`.

THE REPLAY (`replay`, ours only): `cut_every_jump` ON on the same plan
pickle, with `stage7_sequence._cut_or_bury_jumps` recorded through its own
`_later_thread_burier` calls -- no second copy of the rule. Per float: its
length, the engine's outcome (`buried` under later thread, `walked` on
thread already sewn, `cut` on bare cloth, locked both sides) and what its
straight thread LIES ON, read with the walk's own samples (every
`_BURY_STEP_MM` at the centre and both thread edges, the end allowance
included) against the plan's thread as it stood when the pass ran:

  same     every sample on this block's own thread;
  white    the rest on a white block's thread (the field `sew_enclosed_white`
           lays: a block whose rgb reads >= WHITE_MIN on every channel);
  other    the rest on another colour's thread;
  bare     some sample on no thread at all.

The ON+fine arm is ON with `cfg.extra["bury_step_fine"]` (built OFF 2026-11-06):
the pass's thread tests, bury and walk, at 0.01 mm instead of 0.1. Each ON
arm is judged by `tools.jump_walk_oracle` (the browser test's raster oracle,
0.01 mm cells, from the DST bytes) against the OFF arm's file: sewn-hop
segments (the oracle calls every fresh needle-down segment a walk, the
buried ones included), those with a sample off the thread, and the worst
distance past the thread's edge.

THREE BREAK DEFINITIONS, per file and pooled (`breaks`):

  A  cut + uncut            every needle-up move, as the 10-29 doc counted;
  B  cut                    a float is not a break;
  C  cut + uncut not walked a float the replay would WALK on sewn thread is
                            not a break (OFF: its floats minus the ones ON
                            walks; ON and the pro: uncut needle-up moves
                            are all still breaks, so C = A there).

Gate 3 instruments ride along: `tools.travel_cover` exposed travel mm and
`tools.flip_sheet_renders.bare_by_band` bare thread mm at 0.20. CPU is
`time.process_time` round `plan_stitches` (stages 5-7) and round the pass
itself.

JOBS: `tools.border_census.PAIRS` plus `tools.flip_sheet_renders.EXTRA_PAIRS`
through `fixture_files`, which needs the client's Embroidery Files folder.
A fresh clone has none of those, so the five Becker pairs fall back to the
committed `testdata/reference/becker_*.dst` and `testdata/becker_marine_logo.png`
(`REFERENCE`); every other pair reports n/a, never an estimate.

It reads; it does not judge. Nothing here flips a flag or moves a constant.
Measured with it 2026-11-06: `docs/float-census-2026-11-06.md`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import sys
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

ARMS = ("off", "on", "on_fine")
OUTCOMES = ("buried", "walked", "cut")
LIES_ON = ("same", "white", "other", "bare")
WHITE_MIN = 225          # a block this light on every channel is the white field

#: slug -> (committed pro DST stem, garment): the pairs a fresh clone can
#: census. Widths come from the pro's file. The art is the one Becker logo.
REFERENCE = {
    "becker_hat_large": ("becker_hat_polo_large_beckers_logo_hat", "hat_front"),
    "becker_lc_large": ("becker_hat_polo_large_beckers_logolc", "left_chest"),
    "becker_hat_small": ("becker_hat_small_beckers_logo_hat_2_a", "hat_front"),
    "becker_chest_small": ("becker_chest_small_beckers_logo_lc_2_a", "left_chest"),
    "becker_hat_smaller": ("becker_hat_small_beckers_logo_hat_smaller", "hat_front"),
}
REFERENCE_ART = DIGITIZER / "testdata" / "becker_marine_logo.png"
#: slug -> (committed art, garment, width mm): jobs with our art but no pro
#: file in a fresh clone, run for the WALK alone (the oracle, the replay);
#: their pro side is n/a. Widths are the pro's (card v8's Fremont and Drone,
#: `test_cut_every_jump`'s roofing hat).
ORACLE_JOBS = {
    "hotel_fremont_hat": ("photo/logo_hotel_fremont.webp", "hat_front", 92.5),
    "gaulke_roofing_hat": ("art/logo_golke_roofing.png", "hat_front", 114.2),
    "precision_drone": ("photo/drone_render.png", "hat_front", 62.6),
}
DEFAULT_CACHE = DIGITIZER / "debug_out" / "float_census"


# ------------------------------------------------------------------ jobs
def all_slugs() -> list[str]:
    from tools import border_census as bc
    from tools import flip_sheet_renders as fsr
    slugs = [r[0] for r in bc.PAIRS] + [r[0] for r in fsr.EXTRA_PAIRS]
    return slugs + [s for s in REFERENCE if s not in slugs]


def job_files(slug: str) -> dict | None:
    """{"art", "pro_dst", "garment", "width_mm", "source"} or None (n/a here).
    The client folder first (`flip_sheet_renders.fixture_files`), then the
    committed reference pair."""
    try:
        from tools.flip_sheet_renders import fixture_files
        fx = fixture_files(slug)
        return {"art": Path(fx["art"]), "pro_dst": Path(fx["pro_dst"]), "garment": fx["garment"],
                "width_mm": float(fx["width_mm"]), "source": "client files"}
    except (SystemExit, StopIteration, OSError, KeyError, ValueError):
        pass
    if slug in REFERENCE and REFERENCE_ART.exists():
        from tools.pro_pair import pro_counts
        stem, garment = REFERENCE[slug]
        dst = DIGITIZER / "testdata" / "reference" / f"{stem}.dst"
        if dst.exists():
            return {"art": REFERENCE_ART, "pro_dst": dst, "garment": garment,
                    "width_mm": pro_counts(dst)["width_mm"], "source": "committed reference"}
    if slug in ORACLE_JOBS:
        rel, garment, width = ORACLE_JOBS[slug]
        art = DIGITIZER / "testdata" / rel
        if art.exists():
            return {"art": art, "pro_dst": None, "garment": garment, "width_mm": width,
                    "source": "committed art, no pro file"}
    return None


def config(width_mm: float, garment: str):
    """The Studio's request for the job, through the service's own parser."""
    from digitizer_core import PipelineConfig
    from digitizer_service.app import _parse_config
    from tools.pro_pair import request
    return PipelineConfig(**_parse_config(json.dumps(request(width_mm, garment))))


def arm_config(cfg, arm: str):
    if arm == "off":
        return cfg
    extra = dict(cfg.extra or {})
    if arm == "on_fine":
        extra["bury_step_fine"] = True
    return replace(cfg, cut_every_jump=True, extra=extra)


# ------------------------------------------------------------------ DST
def dst_moves(path) -> dict:
    """Every move of a machine file by class (see the module docstring):
    counts, lengths, the cut classes and the cuts inside one piece."""
    from tools import between_walks as bw
    from tools import sequence_pro as sp
    from tools import trim_classes as tc
    from digitizer_core import machine
    f = sp.read(path)
    cut_mm, uncut_mm = [], []
    for block in f["blocks"]:
        mv = sp.moves(block)
        for j in range(1, len(mv)):
            if not mv[j]["up"]:
                continue
            d = math.dist(mv[j - 1]["p"], mv[j]["p"])
            (cut_mm if mv[j]["trim"] else uncut_mm).append(round(d, 2))
    steps = bw.read_steps(path)["steps"]
    walked = [s for s in steps if s["cls"] == "walked"]
    seq = sp.read_file(path)["total"]
    classes = Counter(r["cls"] for r in tc.classify(path))
    # An uncut move longer than a DST record can hold is how the writer
    # encodes a needle-DOWN stitch over `MAX_STITCH_MM` (pystitch's
    # long-stitch contingency: jump records, then the needle): not a jump
    # the plan made, but the machine flies it with the thread uncut all the
    # same. `plan_long_segments` (ours) says which runs they come from.
    uncut_long = [d for d in uncut_mm if d > machine.MAX_STITCH_MM]
    return {"file": Path(path).name, "cuts": len(cut_mm), "uncut": len(uncut_mm),
            "uncut_long": len(uncut_long),
            "walked": len(walked), "walked_mm": round(sum(s["walked_mm"] for s in walked), 1),
            "walked_buried_mm": round(sum(s["buried"] for s in walked), 1),
            "walked_on_work_mm": round(sum(s["on_work"] for s in walked), 1),
            "walked_bare_mm": round(sum(s["bare"] for s in walked), 1),
            "cut_mm": sorted(cut_mm), "uncut_mm": sorted(uncut_mm),
            "inpiece_cuts": int(seq["trims"] - seq["inter_trims"]),
            "trim_classes": {k: classes.get(k, 0) for k in tc.CLASSES}}


def plan_long_segments(plan) -> list[dict]:
    """Every needle-down segment of the plan longer than `MAX_STITCH_MM`:
    the DST writer encodes each as jump records, a float the machine lays
    with the thread uncut, that no jump pass can see (it is a stitch to the
    plan). One row per segment: block, run kind, shape, length."""
    from digitizer_core import machine
    rows = []
    for bi, b in enumerate(plan.blocks):
        last = None
        for r in b.runs:
            pts = list(r.points)
            if not pts:
                continue
            if last is not None and not r.jump:
                pts = [last] + pts
            for p, q in zip(pts, pts[1:]):
                d = math.dist(p, q)
                if d > machine.MAX_STITCH_MM:
                    rows.append({"block": bi, "kind": str(r.kind), "shape": r.shape_id,
                                 "len_mm": round(d, 1), "at": [round(v, 1) for v in q]})
            last = r.points[-1]
    return rows


# ------------------------------------------------------------------ replay
def _is_white(rgb) -> bool:
    return rgb is not None and all(c >= WHITE_MIN for c in rgb[:3])


def _lies_on_reader(blocks, seq):
    """-> lies_on(k): what the straight hop into `seq[k]` lies on, with the
    walk's own samples, against every non-travel run as it stands now."""
    import numpy as np
    import shapely
    from shapely.geometry import LineString
    from digitizer_core import machine, stitches
    from digitizer_core.stage7_sequence import _BURY_STEP_MM
    half = machine.COVERAGE_THREAD_W_MM / 2.0
    lines, owner = [], []
    for k, (bi, r) in enumerate(seq):
        pts = list(r.points)
        if k > 0 and not r.jump and seq[k - 1][1].points:
            pts = [seq[k - 1][1].points[-1]] + pts
        if r.kind != stitches.TRAVEL and len(pts) >= 2:
            lines.append(LineString(pts))
            owner.append(bi)
    tree = shapely.STRtree(lines) if lines else None
    owner_arr = np.array(owner, np.int64)
    white = np.array([_is_white(b.rgb) for b in blocks], bool)

    def lies_on(k: int) -> dict:
        bi = seq[k][0]
        a, b = seq[k - 1][1].points[-1], seq[k][1].points[0]
        d = math.dist(a, b)
        n = max(2, int(math.ceil(d / _BURY_STEP_MM)) + 1)
        t = np.linspace(0.0, 1.0, n)
        cx, cy = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        nx, ny = ((a[1] - b[1]) / d, (b[0] - a[0]) / d) if d > 0 else (0.0, 0.0)
        px = np.concatenate([cx + o * nx for o in (-half, 0.0, half)])
        py = np.concatenate([cy + o * ny for o in (-half, 0.0, half)])
        at_end = np.zeros(len(px), bool)
        for ex, ey in (a, b):
            at_end |= np.hypot(px - ex, py - ey) <= machine.COVERAGE_THREAD_W_MM
        own = at_end.copy()
        wht = np.zeros(len(px), bool)
        oth = np.zeros(len(px), bool)
        if tree is not None:
            hp, hl = tree.query(shapely.points(px, py), predicate="dwithin", distance=half)
            blk = owner_arr[hl]
            own[hp[blk == bi]] = True
            wht[hp[(blk != bi) & white[blk]]] = True
            oth[hp[(blk != bi) & ~white[blk]]] = True
        covered = own | wht | oth
        if not covered.all():
            cls = "bare"
        elif own.all():
            cls = "same"
        elif (own | wht).all():
            cls = "white"
        else:
            cls = "other"
        return {"lies_on": cls, "bare_frac": round(float((~covered).mean()), 3),
                "white_frac": round(float((wht & ~own).mean()), 3),
                "other_frac": round(float((oth & ~own & ~wht).mean()), 3)}

    return lies_on


@contextmanager
def recording(rows: list, timing: dict | None = None):
    """Run `stage7_sequence._cut_or_bury_jumps` with every float's bury /
    walk verdict recorded into `rows` (one dict per float: k, block, the
    shape ids either side, length, outcome, lies_on, and `_run`, the run
    object the float lifts into). The rule itself is the engine's: only its
    `_later_thread_burier` call is wrapped, and only for the length of the
    pass. Every call of the pass is recorded: stage 7 runs `sequence` once
    more on a trial sub-layout inside a plan (`column_lean`), and the
    beanie knockdown runs the pass again over its own block, so
    `plan_floats` keeps the rows whose run is in the finished plan."""
    from digitizer_core import stage7_sequence as s7
    real_pass, real_burier = s7._cut_or_bury_jumps, s7._later_thread_burier

    def wrapped_pass(blocks, small_letters=None, step=s7._BURY_STEP_MM):
        state: dict = {}

        def burier(blocks_, step_=s7._BURY_STEP_MM):
            seq, bury = real_burier(blocks_, step_)
            state["seq"] = seq
            state["calls"] = {}
            state["lies_on"] = _lies_on_reader(blocks_, seq)

            def wrapped_bury(k, on_work=False):
                rec = state["calls"].setdefault(k, {})
                if "where" not in rec:
                    bi, run = seq[k]
                    prev = seq[k - 1][1]
                    rec["where"] = {"k": k, "block": bi, "from_shape": prev.shape_id,
                                    "to_shape": run.shape_id,
                                    "len_mm": round(math.dist(prev.points[-1], run.points[0]), 3),
                                    "at": [round(v, 2) for v in run.points[0]],
                                    **state["lies_on"](k), "_run": run}
                r = bury(k, on_work)
                rec["walk" if on_work else "bury"] = r is not None
                return r
            return seq, wrapped_bury

        s7._later_thread_burier = burier
        c0 = time.process_time()
        try:
            out = real_pass(blocks, small_letters, step)
        finally:
            s7._later_thread_burier = real_burier
        if timing is not None:
            timing["pass_cpu_s"] = round(time.process_time() - c0, 2)
            timing["step_mm"] = step
        for k in sorted(state.get("calls", {})):
            rec = state["calls"][k]
            outcome = "buried" if rec.get("bury") else "walked" if rec.get("walk") else "cut"
            rows.append({**rec["where"], "outcome": outcome})
        return out

    s7._cut_or_bury_jumps = wrapped_pass
    try:
        yield
    finally:
        s7._cut_or_bury_jumps = real_pass


def replay(blocks, fine: bool = False, small_letters=None) -> tuple[list[dict], tuple[int, int, int]]:
    """`cut_every_jump` ON over finished blocks (mutated in place, as the
    engine does), recorded. -> (rows, (buried, walked, cut))."""
    from digitizer_core import stage7_sequence as s7
    rows: list[dict] = []
    with recording(rows):
        counts = s7._cut_or_bury_jumps(blocks, small_letters,
                                       s7._BURY_STEP_FINE_MM if fine else s7._BURY_STEP_MM)
    for r in rows:
        r.pop("_run", None)
    return rows, counts


def plan_floats(rows: list[dict], plan) -> list[dict]:
    """The recorded rows whose run the finished plan sews (a trial
    sub-layout's rows dropped), without the run object."""
    final = {id(r) for b in plan.blocks for r in b.runs}
    return [{k: v for k, v in r.items() if k != "_run"} for r in rows if id(r["_run"]) in final]


def breaks(cuts: int, uncut: int, walked_floats: int = 0) -> dict:
    """The three definitions. `walked_floats`: the file's uncut floats the
    replay WALKS (0 for a file that is not the OFF arm)."""
    return {"A_cut_plus_uncut": cuts + uncut, "B_cut": cuts,
            "C_cut_plus_uncut_not_walked": cuts + uncut - walked_floats}


# ------------------------------------------------------------------ gen / arms
def gen(slug: str, cache: Path) -> dict:
    """Stages 0-4 once (the expensive part), pickled: every arm plans off
    this one result, so the arms differ in stage 7 alone."""
    from digitizer_core.pipeline import build_generation, finish_generation
    from digitizer_service.app import _decode
    files = job_files(slug)
    if files is None:
        raise SystemExit(f"{slug}: no art and pro file here (n/a)")
    cfg = config(files["width_mm"], files["garment"])
    data = files["art"].read_bytes()
    t0, c0 = time.time(), time.process_time()
    g = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(g.fork(), cfg)
    out = cache / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.pkl").write_bytes(pickle.dumps(result))
    info = {"slug": slug, "source": files["source"], "art": str(files["art"]),
            "pro_dst": str(files["pro_dst"]) if files["pro_dst"] else None, "garment": files["garment"],
            "width_mm": files["width_mm"], "head": _head(),
            "wall_s": round(time.time() - t0, 1), "cpu_s": round(time.process_time() - c0, 1),
            "warnings": [w.get("code") if isinstance(w, dict) else str(w)
                         for w in getattr(result, "warnings", []) or []]}
    (out / "gen.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return info


def arms(slug: str, cache: Path, which=ARMS) -> dict:
    """Stages 5-7 per arm off the pickle: DST, moves, the replay rows, the
    oracle, gate 3 and CPU. -> arms.json's content."""
    from digitizer_core.export import write_dst
    from digitizer_core.pipeline import plan_stitches
    from tools import jump_walk_oracle as oracle
    from tools.flip_sheet_renders import bare_by_band
    from tools.travel_cover import travel_exposure
    out = cache / slug
    info = json.loads((out / "gen.json").read_text(encoding="utf-8"))
    result = pickle.loads((out / "result.pkl").read_bytes())
    base = config(info["width_mm"], info["garment"])
    plans = {}
    report = {"slug": slug, "head": _head(), "source": info["source"],
              "pro": dst_moves(info["pro_dst"]) if info.get("pro_dst") else None, "arms": {}}
    for arm in which:
        cfg = arm_config(base, arm)
        rows: list[dict] = []
        timing: dict = {}
        c0 = time.process_time()
        if arm == "off":
            plan = plan_stitches(result, cfg)
        else:
            with recording(rows, timing):
                plan = plan_stitches(result, cfg)
        cpu = time.process_time() - c0
        plans[arm] = plan
        rows = plan_floats(rows, plan)
        dst = out / f"{arm}.dst"
        write_dst(plan, dst)
        (out / f"{arm}_floats.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
        cell = {"arm": arm, "dst": str(dst), "md5": hashlib.md5(dst.read_bytes()).hexdigest(),
                "plan_cpu_s": round(cpu, 1), **timing,
                "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
                "moves": dst_moves(dst), "plan_long_segments": plan_long_segments(plan),
                "exposed_mm": round(travel_exposure(plan)["exposed_mm"], 1),
                "bare_mm_020": bare_by_band(plan)["0.20"]}
        if rows:
            cell["floats"] = len(rows)
            cell["outcomes"] = {o: sum(1 for r in rows if r["outcome"] == o) for o in OUTCOMES}
            cell["lies_on"] = {w: sum(1 for r in rows if r["lies_on"] == w) for w in LIES_ON}
            cell["outcome_by_lies_on"] = {o: {w: sum(1 for r in rows if r["outcome"] == o and r["lies_on"] == w)
                                              for w in LIES_ON} for o in OUTCOMES}
            cell["float_mm"] = {o: [r["len_mm"] for r in rows if r["outcome"] == o] for o in OUTCOMES}
        if arm != "off" and "off" in plans:
            v = oracle.judge(plans["off"], plan, f"{slug}:{arm}")
            cell["oracle"] = {k: v[k] for k in ("walked_segments", "walked_mm", "bare_segments",
                                                "bare_walked_segments", "worst_off_thread_mm")}
            cell["oracle"]["bare_detail"] = v["bare_detail"]
        report["arms"][arm] = cell
    (out / "arms.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def _head() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=DIGITIZER,
                              capture_output=True, text=True).stdout.strip()
    except OSError:
        return "?"


# ------------------------------------------------------------------ report
def job_summary(rep: dict) -> dict:
    """One job's figures: per side the move classes and the three
    definitions, the replay's outcomes, gate 3 and the oracle."""
    pro = rep.get("pro")
    out = {"slug": rep["slug"], "source": rep.get("source", "")}
    if pro is not None:
        out["pro"] = {**_moves(pro), **breaks(pro["cuts"], pro["uncut"])}
    for arm, cell in rep["arms"].items():
        m = cell["moves"]
        row = {**_moves(m), "exposed_mm": cell["exposed_mm"], "bare_mm_020": cell["bare_mm_020"],
               "plan_cpu_s": cell["plan_cpu_s"], "md5": cell["md5"],
               "long_segments": len(cell.get("plan_long_segments", []))}
        if arm == "off":
            on = rep["arms"].get("on")
            walked = on["outcomes"]["walked"] if on and "outcomes" in on else 0
            row.update(breaks(m["cuts"], m["uncut"], walked))
            row["floats_on_walks"] = walked
        else:
            row.update(breaks(m["cuts"], m["uncut"]))
            for k in ("floats", "outcomes", "lies_on", "outcome_by_lies_on", "pass_cpu_s", "oracle"):
                if k in cell:
                    row[k] = cell[k]
        out[arm] = row
    return out


def _moves(m: dict) -> dict:
    return {"cuts": m["cuts"], "uncut": m["uncut"], "uncut_long": m.get("uncut_long", 0),
            "walked": m["walked"], "walked_mm": m["walked_mm"],
            "inpiece_cuts": m["inpiece_cuts"], "under_later": m["trim_classes"]["under_later"],
            "on_work": m["trim_classes"]["on_work"],
            "bare_cuts": m["trim_classes"]["bare_letters"] + m["trim_classes"]["bare_other"]}


def pooled(summaries: list[dict]) -> dict:
    """Sums over the jobs with files; the oracle's worst is a max."""
    out: dict = {"jobs": [s["slug"] for s in summaries]}
    sides = ["pro"] + [a for a in ARMS if all(a in s for s in summaries)]
    for side in sides:
        tot: dict = {}
        for s in summaries:
            if side not in s:
                continue
            for k, v in s[side].items():
                if isinstance(v, (int, float)) and k not in ("md5",):
                    tot[k] = round(tot.get(k, 0) + v, 2)
                elif isinstance(v, dict) and k in ("outcomes", "lies_on"):
                    t = tot.setdefault(k, {})
                    for kk, vv in v.items():
                        t[kk] = t.get(kk, 0) + vv
                elif isinstance(v, dict) and k == "oracle":
                    t = tot.setdefault(k, {"walked_segments": 0, "bare_walked_segments": 0,
                                           "worst_off_thread_mm": 0.0})
                    t["walked_segments"] += v["walked_segments"]
                    t["bare_walked_segments"] += v["bare_walked_segments"]
                    t["worst_off_thread_mm"] = max(t["worst_off_thread_mm"], v["worst_off_thread_mm"])
        out[side] = tot
    return out


def _ratio(a, b) -> str:
    return "n/a" if not b else f"{a / b:.2f}x"


def markdown(summaries: list[dict], na: list[str], pool: dict) -> str:
    """The doc tables: three definitions per job and pooled, the replay's
    outcomes by what each float lies on, gate 3 and the oracle."""
    paired = [s for s in summaries if "pro" in s]
    pool = pooled(paired) if paired else {"jobs": []}
    L = []
    L.append("| job | side | cuts | uncut | of them long-stitch | walked (DST) | A cut+uncut | B cut | C cut+uncut not walked |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for s in paired + ([pool] if paired else []):
        name = s.get("slug") or f"**pooled ({len(pool['jobs'])} jobs)**"
        for side in ("pro", *ARMS):
            if side not in s:
                continue
            r = s[side]
            L.append(f"| {name} | {side} | {r['cuts']} | {r['uncut']} | {r['uncut_long']} | {r['walked']} "
                     f"| {r['A_cut_plus_uncut']} | {r['B_cut']} | {r['C_cut_plus_uncut_not_walked']} |")
            name = ""
    if paired:
        p = pool["pro"]
        L.append("")
        L.append("Ratios to the pro, pooled:")
        L.append("")
        L.append("| ours | A / pro A | B / pro B | C / pro A |")
        L.append("|---|---|---|---|")
        for arm in ARMS:
            if arm in pool:
                o = pool[arm]
                L.append(f"| {arm} | {_ratio(o['A_cut_plus_uncut'], p['A_cut_plus_uncut'])} "
                         f"| {_ratio(o['B_cut'], p['B_cut'])} | {_ratio(o['C_cut_plus_uncut_not_walked'], p['A_cut_plus_uncut'])} |")
    L.append("")
    L.append("| job | arm | floats | buried | walked | cut | on same colour | on white field | on other colour | bare | "
             "exposed mm | bare mm @0.20 | plan CPU s | pass CPU s | oracle walked segs | off thread | worst mm |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for s in summaries:
        name = s["slug"] + ("" if "pro" in s else " (no pro file)")
        off = s["off"]
        L.append(f"| {name} | off | {off['uncut']} floats, {off.get('floats_on_walks', '')} walked by ON | | | | | | | | {off['exposed_mm']} "
                 f"| {off['bare_mm_020']} | {off['plan_cpu_s']} | | | | |")
        for arm in ("on", "on_fine"):
            if arm not in s:
                continue
            r = s[arm]
            oc, lo, orc = r.get("outcomes", {}), r.get("lies_on", {}), r.get("oracle", {})
            L.append(f"| | {arm} | {r.get('floats', 0)} | {oc.get('buried', 0)} | {oc.get('walked', 0)} | {oc.get('cut', 0)} "
                     f"| {lo.get('same', 0)} | {lo.get('white', 0)} | {lo.get('other', 0)} | {lo.get('bare', 0)} "
                     f"| {r['exposed_mm']} | {r['bare_mm_020']} | {r['plan_cpu_s']} | {r.get('pass_cpu_s', '')} "
                     f"| {orc.get('walked_segments', '')} | {orc.get('bare_walked_segments', '')} "
                     f"| {orc.get('worst_off_thread_mm', '')} |")
    if na:
        L.append("")
        L.append("n/a here (no art or pro file in this checkout): " + ", ".join(na) + ".")
    return "\n".join(L) + "\n"


def report(cache: Path, md: Path | None = None) -> dict:
    summaries, na = [], []
    for slug in all_slugs():
        f = cache / slug / "arms.json"
        if f.exists():
            summaries.append(job_summary(json.loads(f.read_text(encoding="utf-8"))))
        else:
            na.append(slug)
    pool = pooled([s for s in summaries if "pro" in s]) if summaries else {"jobs": []}
    text = markdown(summaries, na, pool) if summaries else "no job censused\n"
    print(text)
    if md is not None:
        md.write_text(text, encoding="utf-8")
    (cache / "report.json").write_text(json.dumps({"jobs": summaries, "pooled": pool, "na": na}, indent=1),
                                       encoding="utf-8")
    return {"jobs": summaries, "pooled": pool, "na": na}


# ------------------------------------------------------------------ cli
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.float_census",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gen", "arms"):
        p = sub.add_parser(name)
        p.add_argument("--jobs", nargs="*", help="slugs (default: every job with files here)")
        p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
        if name == "arms":
            p.add_argument("--arms", nargs="*", default=list(ARMS), choices=ARMS)
    p = sub.add_parser("report")
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--md", type=Path, help="write the tables here")
    p = sub.add_parser("dst")
    p.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "dst":
        for f in a.files:
            m = dst_moves(f)
            print(json.dumps({k: v for k, v in m.items() if k not in ("cut_mm", "uncut_mm")}))
        return 0
    if a.cmd == "report":
        report(a.cache, a.md)
        return 0
    slugs = a.jobs or [s for s in all_slugs() if job_files(s) is not None]
    for slug in slugs:
        if a.cmd == "gen":
            print(json.dumps(gen(slug, a.cache)))
        else:
            rep = arms(slug, a.cache, a.arms)
            print(json.dumps(job_summary(rep)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
