#!/usr/bin/env python
"""What `THREAD_MATCH_POOR`'s patch floor does to the scorecard corpus.

Quality review 2026-09-08 item 11: the check had NO area floor while every
sibling has one, so a 0.58 mm² shard and a 1,648 mm² field both said "do not
sew" (yardstick-disagreements row 3). `_THREAD_MATCH_MIN_PATCH_MM2` (2026-09-10)
is the sibling's 5.0 mm²; this sweep reads the same designs under 0 (the old
check), 2, 5 and 10 so the choice is seen rather than assumed.

Per (fixture, garment) in the scorecard matrix (80 mm, the engine's 12
colours): one digitize, then preflight once per floor with the module
constant overridden — a scoring rule, no stitch moves — recording every
THREAD_MATCH_POOR finding (thread, severity, the footprint that judged, the
sub-floor count) beside the score, the raw score, the grade and the block /
warn counts.

    .venv/bin/python tools/thread_match_floor.py run      # resumable, --out
    .venv/bin/python tools/thread_match_floor.py report   # the tables
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

TESTDATA = ROOT / "testdata"
FLOORS = (0.0, 2.0, 5.0, 10.0)


def _cases():
    from tools.corpus_scorecard import FIXTURES, MATRIX
    return [(f, dict(kw)) for f in FIXTURES for kw in MATRIX]


def _key(fixture: str, kw: dict) -> str:
    return f"{fixture.replace('/', '__')}__{kw['garment_id']}"


def measure(fixture: str, kw: dict) -> dict:
    from digitizer_core import preflight as pf
    from digitizer_core.config import PipelineConfig
    from digitizer_core.pipeline import digitize
    path = TESTDATA / fixture
    cfg = PipelineConfig(**kw)
    result, plan = digitize(path, cfg)
    out = {"fixture": fixture, "garment": kw["garment_id"], "floors": {}}
    for floor in FLOORS:
        pf._THREAD_MATCH_MIN_PATCH_MM2 = floor
        rep = pf.run_preflight(result, plan, cfg, image=path)
        tm = [f for f in rep["findings"] if f["code"] == pf.THREAD_MATCH_POOR]
        out["floors"][str(floor)] = {
            "score": rep["score"], "raw_score": rep["metrics"]["raw_score"],
            "grade": rep["grade"],
            "blocks": sum(1 for f in rep["findings"] if f["severity"] == "block"),
            "warns": sum(1 for f in rep["findings"] if f["severity"] == "warn"),
            "thread_match": [{
                "thread": f["extra"]["thread_number"], "severity": f["severity"],
                "delta_e": f["extra"]["delta_e"], "yardstick": f["extra"]["yardstick"],
                "worst_patch_mm2": f["extra"].get("worst_patch_mm2"),
                "worst_shape_area_mm2": f["extra"].get("worst_shape_area_mm2"),
                "region_count": f["extra"]["region_count"],
                "sub_floor_count": f["extra"].get("sub_floor_count", 0),
                "regions": f["extra"]["regions"],
            } for f in tm],
        }
    return out


def _run_one(args):
    fixture, kw, out_dir = args
    dest = out_dir / f"{_key(fixture, kw)}.json"
    if dest.exists():
        return _key(fixture, kw), "cached"
    try:
        row = measure(fixture, kw)
    except Exception as exc:  # noqa: BLE001 — one bad fixture must not sink the sweep
        row = {"fixture": fixture, "garment": kw["garment_id"], "error": f"{type(exc).__name__}: {exc}"}
    dest.write_text(json.dumps(row, indent=1), encoding="utf-8")
    return _key(fixture, kw), "done" if "error" not in row else row["error"]


def run(out_dir: Path, workers: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(f, kw, out_dir) for f, kw in _cases()]
    print(f"{len(jobs)} (fixture, garment) pairs, {workers} workers")
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (key, status) in enumerate(ex.map(_run_one, jobs), 1):
            print(f"[{i}/{len(jobs)}] {key}: {status}", flush=True)


def report(out_dir: Path) -> None:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out_dir.glob("*.json"))]
    rows = [r for r in rows if "error" not in r]
    print(f"# THREAD_MATCH_POOR under a patch floor — {len(rows)} (fixture, garment) pairs\n")
    # 1. Every finding at floor 0 with the footprint that judged it.
    print("## Every finding on the old check (floor 0): the footprint that judged\n")
    print(f"{'fixture':<34} {'garment':<11} {'thread':<6} {'sev':<5} {'dE':>6} {'patch mm2':>10} {'shape mm2':>10} {'yard':<6}")
    fps = []
    for r in rows:
        for f in r["floors"]["0.0"]["thread_match"]:
            fps.append((f["worst_patch_mm2"] or 0.0, f["severity"]))
            print(f"{r['fixture']:<34} {r['garment']:<11} {f['thread']:<6} {f['severity']:<5} {f['delta_e']:6.1f} "
                  f"{(f['worst_patch_mm2'] or 0):10.2f} {(f['worst_shape_area_mm2'] or 0):10.2f} {f['yardstick']:<6}")
    blocks = sorted(fp for fp, sev in fps if sev == "block")
    if blocks:
        import statistics
        print(f"\nblocking findings {len(blocks)}: worst patch min {blocks[0]:.2f}, p50 {statistics.median(blocks):.2f}, "
              f"max {blocks[-1]:.2f} mm2; under 2: {sum(1 for b in blocks if b < 2)}, under 5: {sum(1 for b in blocks if b < 5)}, "
              f"under 10: {sum(1 for b in blocks if b < 10)}")
    # 2. Per floor: what moves.
    print("\n## What each floor moves, per pair (only pairs where something moves)\n")
    print(f"{'fixture':<34} {'garment':<11} " + " ".join(f"{'floor ' + str(int(fl)):<22}" for fl in FLOORS))
    for r in rows:
        cells, moved = [], False
        base = r["floors"]["0.0"]
        for fl in FLOORS:
            d = r["floors"][str(fl)]
            tm_b = sum(1 for f in d["thread_match"] if f["severity"] == "block")
            tm_w = sum(1 for f in d["thread_match"] if f["severity"] == "warn")
            cells.append(f"{d['grade']} {d['score']:3d} (raw {d['raw_score']:4d}) tm {tm_b}b/{tm_w}w")
            if (d["score"], d["raw_score"], tm_b, tm_w) != (base["score"], base["raw_score"],
                    sum(1 for f in base["thread_match"] if f["severity"] == "block"),
                    sum(1 for f in base["thread_match"] if f["severity"] == "warn")):
                moved = True
        if moved:
            print(f"{r['fixture']:<34} {r['garment']:<11} " + " ".join(f"{c:<22}" for c in cells))
    # 3. The floor depth today (yardstick-disagreements row 6, re-read on
    #    this engine): every pair on the clamped 0, with its raw score under
    #    the old check and under the shipped floor.
    print("\n## Floor depth today — pairs on the clamped 0 (raw score: old check -> floor 5)\n")
    floored = [r for r in rows if r["floors"]["0.0"]["score"] == 0 or r["floors"]["5.0"]["score"] == 0]
    for r in sorted(floored, key=lambda r: r["floors"]["0.0"]["raw_score"]):
        a, b = r["floors"]["0.0"], r["floors"]["5.0"]
        print(f"{r['fixture']:<34} {r['garment']:<11} {a['grade']} {a['score']:3d} raw {a['raw_score']:5d} -> "
              f"{b['grade']} {b['score']:3d} raw {b['raw_score']:5d}   blocks {a['blocks']} -> {b['blocks']}")
    print(f"\n{len(floored)} of {len(rows)} pairs on the 0 floor under the old check or the new; "
          f"raw scores under the old check span "
          f"{min((r['floors']['0.0']['raw_score'] for r in floored), default=0)} .. "
          f"{max((r['floors']['0.0']['raw_score'] for r in floored), default=0)}")
    # 4. Totals.
    print("\n## Totals over the matrix\n")
    print(f"{'floor':<8} {'tm blocks':>10} {'tm warns':>9} {'all blocks':>11} {'on the 0 floor':>15} {'grade moves':>12} {'raw sum':>9}")
    for fl in FLOORS:
        tmb = sum(sum(1 for f in r["floors"][str(fl)]["thread_match"] if f["severity"] == "block") for r in rows)
        tmw = sum(sum(1 for f in r["floors"][str(fl)]["thread_match"] if f["severity"] == "warn") for r in rows)
        allb = sum(r["floors"][str(fl)]["blocks"] for r in rows)
        floored = sum(1 for r in rows if r["floors"][str(fl)]["score"] == 0)
        moves = sum(1 for r in rows if r["floors"][str(fl)]["grade"] != r["floors"]["0.0"]["grade"])
        raw = sum(r["floors"][str(fl)]["raw_score"] for r in rows)
        print(f"{fl:<8g} {tmb:>10} {tmw:>9} {allb:>11} {floored:>15} {moves:>12} {raw:>9}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=["run", "report"])
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "thread_match_floor")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args(argv)
    if a.mode == "run":
        run(a.out, a.workers)
    else:
        report(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
