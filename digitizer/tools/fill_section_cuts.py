"""fill_section_cuts: the cuts between two sections of ONE fill, ours beside the
pro's, per arm, on the paired jobs -- defect 6's table in one command.

    python -m tools.fill_section_cuts [--slugs a,b] [--arm NAME=JSON ...] [--out DIR] [--repeat N]

Built 2026-11-06 for `docs/fill-one-pass-sections-2026-11-06.md`. Each job is
digitized once at the pro's width and garment through the Studio's request
(`tools.pro_pair.digitize`, `tools.flip_sheet_renders.fixture_files`), stages
0-4 are pickled under `--out`, and `plan_stitches` is replayed from the pickle
once per arm (`--repeat N`: plan CPU is the best of N). An arm's JSON is a dict
of `PipelineConfig` fields; a key `extra.K` goes to `cfg.extra`. The bare arm
`main` is the request as the Studio sends it.

One reader on both DSTs, the 10-29 doc's set: `tools.sequence_pro` (cuts, and
how many lie inside one piece), `tools.inpiece_cuts` (the cause of each cut
inside a piece; the pro's by stitch character), `tools.trim_locality`,
`tools.travel_cover` (exposed travel), `tools.flip_sheet_renders.bare_by_band`
(bare thread at 0.20/0.25/0.30 mm, gate 3), the DST md5 and plan CPU. Reads;
judges nothing. The pairs a fresh clone has are the five Becker jobs; the
others need the client files (`tools.border_census.roots`, `PRO_PARITY_ROOT`).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

BECKER = ["becker_hat_large", "becker_lc_large", "becker_hat_small", "becker_chest_small",
          "becker_beanie"]
DEFAULT_OUT = HERE.parent / "debug_out" / "fill_section_cuts"


def arm_cfg(cfg, sets: dict):
    extra = dict(cfg.extra)
    fields = {}
    for k, v in sets.items():
        if k.startswith("extra."):
            extra[k[len("extra."):]] = v
        else:
            fields[k] = v
    return dataclasses.replace(cfg, extra=extra, **fields)


def digitized(slug: str, cache: Path):
    """(fixture, result, cfg): stages 0-4, from the pickle when one exists."""
    from tools import flip_sheet_renders as fsr
    from tools import pro_pair as pp
    fx = fsr.fixture_files(slug)
    pk = cache / f"{slug}.pkl"
    if pk.exists():
        d = pickle.loads(pk.read_bytes())
        return fx, d["result"], d["cfg"]
    t = time.process_time()
    d = pp.digitize(fx["art"], fx["width_mm"], fx["garment"], {})
    pk.write_bytes(pickle.dumps({"result": d.result, "cfg": d.cfg,
                                 "whole_cpu_s": round(time.process_time() - t, 1)}))
    return fx, d.result, d.cfg


def read_plan(plan, dst_path: Path) -> dict:
    from digitizer_core.export import write_dst
    from tools import flip_sheet_renders as fsr
    from tools import inpiece_cuts as ic
    from tools import sequence_pro as sp
    from tools import trim_locality as tl
    from tools.travel_cover import travel_exposure
    write_dst(plan, dst_path)
    seq = sp.read_file(dst_path)["total"]
    causes = ic.classify_plan(plan)
    by_cause = Counter(r["cause"] for r in causes)
    loc = tl.split(plan)
    return {"md5": hashlib.md5(dst_path.read_bytes()).hexdigest(),
            "stitches": plan.stats.stitch_count,
            "cuts": int(seq["trims"]), "inpiece_cuts": int(seq["trims"] - seq["inter_trims"]),
            "uncut_moves": int(seq["up_moves"] - seq["trims"]),
            "by_cause": dict(by_cause), "fill_section": by_cause.get("fill_section", 0),
            "fill_section_shapes": dict(Counter(r["shape"] for r in causes if r["cause"] == "fill_section")),
            "locality": {"in_shape": loc["in_shape"], "between": loc["between"]},
            "exposed_mm": round(travel_exposure(plan)["exposed_mm"], 1),
            "bare_mm": fsr.bare_by_band(plan)}


def read_pro(path: Path) -> dict:
    from tools import inpiece_cuts as ic
    from tools import sequence_pro as sp
    seq = sp.read_file(path)["total"]
    rows = ic.classify_dst(path)
    return {"file": path.name, "cuts": int(seq["trims"]),
            "inpiece_cuts": int(seq["trims"] - seq["inter_trims"]),
            "uncut_moves": int(seq["up_moves"] - seq["trims"]),
            "inpiece_by_character": dict(Counter(f"{r['before']}>{r['after']}" for r in rows))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.fill_section_cuts",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--slugs", default=",".join(BECKER))
    ap.add_argument("--arm", action="append", default=[], help="NAME=JSON; `main` is always run")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--repeat", type=int, default=1, help="plan CPU: the best of N replays")
    a = ap.parse_args(argv)
    arms = {"main": {}}
    for s in a.arm:
        name, js = s.split("=", 1)
        arms[name] = json.loads(js)
    a.out.mkdir(parents=True, exist_ok=True)
    from digitizer_core.pipeline import plan_stitches
    report = {}
    for slug in a.slugs.split(","):
        fx, result, cfg = digitized(slug, a.out)
        row = {"width_mm": fx["width_mm"], "garment": fx["garment"], "art": str(fx["art"]),
               "pro_dst": str(fx["pro_dst"]), "pro": read_pro(fx["pro_dst"]), "arms": {}}
        for name, sets in arms.items():
            c = arm_cfg(cfg, sets)
            best = None
            for _ in range(max(1, a.repeat)):
                t = time.process_time()
                plan = plan_stitches(result, c)
                cpu = time.process_time() - t
                best = cpu if best is None else min(best, cpu)
            got = read_plan(plan, a.out / f"{slug}__{name}.dst")
            got["plan_cpu_s"] = round(best, 1)
            row["arms"][name] = got
            print(slug, name, {k: got[k] for k in ("cuts", "inpiece_cuts", "fill_section", "stitches",
                                                   "exposed_mm", "bare_mm", "plan_cpu_s", "md5")},
                  got["fill_section_shapes"], flush=True)
        print(slug, "pro", row["pro"], flush=True)
        report[slug] = row
        (a.out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
