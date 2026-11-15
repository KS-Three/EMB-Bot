"""Digitize seconds and Cancel latency for a set of flags, design by design.

Built 2026-11-14 for the timing pass over the day's flips (#1515: redraw 0.75,
piece lift, the two small-text flags, group tier + fill angle, blend band).

    # one job, one arm: a JSON line on stdout
    python -m tools.flip_timing run SLUG ARM [KEY=JSON ...]
    #   ARM "main"  : the engine's defaults
    #   ARM "pre"   : the defaults with #1515's flips set back (`PRE_1515`)
    #   KEY=JSON    : extra config on top of the arm (a flag about to flip)
    # every job's pre / main / next (`NEXT`) arms in one process
    python -m tools.flip_timing arms SLUG [SLUG ...]

Each run digitizes the job at its pro size through `tools.pro_pair` (the
Studio's request, the service's parser), with `deadline.check` wrapped by a
recorder that only reads the clock: seconds per pipeline step (generation,
finish, plan), seconds per stage label (the time from one check to the next,
charged to the label that opened it), the longest stretch with no check
(`tests/test_cancel_seams_1113.py`'s measure) and the md5 of the plan's runs.
One design at a time: the seconds are laptop seconds and move with load.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DIGITIZER))

#: #1515's flips, set back to the engine before it (config.py history).
PRE_1515 = {
    "outline_redraw_k": None,
    "inshape_piece_lift": False,
    "small_text_reset_one_baseline": False,
    "text_cluster_solid_guard": False,
    "group_consistent_tier": False,
    "group_consistent_fill_angle": False,
    "flat_blend_band_any_scale": False,
}


_WARM: list = []

#: the flags Kent has ruled ON that are about to flip (#1533 and the two
#: group flags with their guards, #1516 / #1517)
NEXT = {
    "lettering_columns_connectors_edge_walk": True,
    "lettering_columns_corner_fold_apex_side": True,
    "group_consistent_thread": True,
    "group_consistent_outline_body": True,
}


def plan_md5(plan) -> str:
    fp = [(b.thread_number, [(r.kind, r.jump, r.trim, r.shape_id,
                              tuple((round(x, 6), round(y, 6)) for x, y in r.points))
                             for r in b.runs]) for b in plan.blocks]
    return hashlib.md5(json.dumps(fp).encode()).hexdigest()


def stage_of(label: str) -> str:
    parts = label.split()
    if len(parts) >= 2 and parts[0] == "stage":
        return " ".join(parts[:2])
    return label


def run(slug: str, arm: str, extra: dict) -> dict:
    from digitizer_core import PipelineConfig, deadline
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools import pro_baseline as pb, pro_pair

    garment, width, art, *_ = pb.JOBS[slug]
    path = pb.resolve(art)
    cfg = PipelineConfig(**_parse_config(json.dumps(pro_pair.request(width, garment, {}))))
    over = dict(PRE_1515) if arm == "pre" else {}
    over.update(extra)
    for k, v in over.items():
        setattr(cfg, k, v)
    calls: list[tuple[float, str]] = []
    real = deadline.check

    def rec(stage: str) -> None:
        calls.append((time.perf_counter(), stage))
        real(stage)

    if not _WARM:
        # warm-up, untimed, once a process: the first digitize loads models
        # and tables (5 s before stage 0's first check on Tires); the service
        # pays that once per process, not per job
        warm = DIGITIZER / "testdata" / "logo_alpha.png"
        wcfg = PipelineConfig(**_parse_config(json.dumps(pro_pair.request(40.0, garment, {}))))
        plan_stitches(finish_generation(build_generation(_decode(warm.read_bytes()), wcfg), wcfg), wcfg)
        _WARM.append(True)
    deadline.check = rec
    try:
        data = path.read_bytes()
        pixels = _decode(data)
        c0 = time.process_time()
        t0 = time.perf_counter()
        gen = build_generation(pixels, cfg, exif_source=data)
        t1, c1 = time.perf_counter(), time.process_time()
        result = finish_generation(gen.fork(), cfg)
        t2, c2 = time.perf_counter(), time.process_time()
        plan = plan_stitches(result, cfg)
        t3, c3 = time.perf_counter(), time.process_time()
    finally:
        deadline.check = real
    seq = [(t0, "start")] + calls + [(t3, "end")]
    gaps = sorted(((b[0] - a[0], a[1], b[1]) for a, b in zip(seq, seq[1:])), reverse=True)
    per: dict[str, float] = {}
    for a, b in zip(seq, seq[1:]):
        per[stage_of(a[1])] = per.get(stage_of(a[1]), 0.0) + (b[0] - a[0])
    return {"slug": slug, "arm": arm, "extra": extra, "width": width, "garment": garment,
            "secs": round(t3 - t0, 2), "generation": round(t1 - t0, 2),
            "finish": round(t2 - t1, 2), "plan": round(t3 - t2, 2),
            # CPU seconds of this process (all its threads): far less moved by
            # the other sessions on the laptop than the wall clock above
            "cpu": round(c3 - c0, 2), "cpu_generation": round(c1 - c0, 2),
            "cpu_finish": round(c2 - c1, 2), "cpu_plan": round(c3 - c2, 2),
            "stitches": plan.stats.stitch_count, "md5": plan_md5(plan), "checks": len(calls),
            "max_gap": [round(gaps[0][0], 3), gaps[0][1], gaps[0][2]] if gaps else None,
            "gaps_over_1s": [[round(g, 3), a, b] for g, a, b in gaps if g > 1.0][:8],
            "per_stage": {k: round(v, 2) for k, v in sorted(per.items(), key=lambda kv: -kv[1])[:12]}}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv.pop(0)
    if cmd == "arms":
        # every arm of every job in ONE process (one warm-up): pre, main, next
        for slug in argv:
            for arm, extra in (("pre", {}), ("main", {}), ("next", NEXT)):
                r = run(slug, "main" if arm == "next" else arm, extra)
                r["arm"] = arm
                print(json.dumps(r), flush=True)
        return 0
    if cmd == "run":
        slug, arm, *kv = argv
        extra = {k: json.loads(v) for k, v in (s.split("=", 1) for s in kv)}
        print(json.dumps(run(slug, arm, extra)), flush=True)
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
