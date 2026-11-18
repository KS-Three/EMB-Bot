"""`lettering_columns_off_line_mark` OFF vs ON over the 9 committed pro jobs and
the 26 `corpus_scorecard.FIXTURES` (2026-11-18).

    python -m tools.off_line_mark_sweep --list
    python -m tools.off_line_mark_sweep --job KEY --out DIR

One job per process (the driver fans them out). A pro job runs at its own width
and garment (`tools.pro_baseline.JOBS`); a fixture at the Studio request at
80 mm on `left_chest`. Writes `DIR/KEY.json`: the md5 of `design["stitches"]`
with the flag OFF and ON, the shapes the flag tagged, and, on a mover, both
designs for rendering. Compare STITCHES, not a metric."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAG = "lettering_columns_off_line_mark"


def jobs() -> dict[str, tuple[str, float, str]]:
    """key -> (garment_id, width_mm, art spec); pro jobs first."""
    from tools.corpus_scorecard import FIXTURES
    from tools.pro_baseline import JOBS
    from tools.prime_grader import population
    out = {}
    for s in population():
        g, w, art, *_ = JOBS[s]
        out[s] = (g, float(w), art)
    for f in FIXTURES:
        out["fx:" + f] = ("left_chest", 80.0, "testdata:" + f)
    return out


def _md5(design: dict) -> str:
    return hashlib.md5(str(design["stitches"]).encode()).hexdigest()


def run_job(key: str, out: Path) -> dict:
    from tools import pro_pair as pp
    from tools.pro_baseline import resolve
    from tools.tripwire import materialise
    garment, width, spec = jobs()[key]
    if spec.startswith("kent:"):
        materialise(out / "_kent", [key])
    art = resolve(spec)
    rec: dict = {"key": key, "width_mm": width, "garment": garment}
    try:
        t = time.time()
        off = pp.digitize(art, width, garment)
        on = pp.digitize(art, width, garment, {FLAG: True})
        rec["secs"] = round(time.time() - t, 1)
        rec["md5_off"], rec["md5_on"] = _md5(off.design), _md5(on.design)
        rec["stitches_off"], rec["stitches_on"] = off.plan.stats.stitch_count, on.plan.stats.stitch_count
        tagged = [r for r in on.result.regions if (r.meta or {}).get("lettering_off_line")]
        rec["tagged"] = [{"shape_id": r.shape_id, "bounds": [round(v, 2) for v in r.polygon.bounds],
                          "area": round(r.polygon.area, 2),
                          "cluster": (r.meta or {}).get("text_cluster_id")} for r in tagged]
        rec["moved"] = rec["md5_off"] != rec["md5_on"]
        if rec["moved"]:
            (out / f"{key.replace('/', '_').replace(':', '_')}.designs.json").write_text(
                json.dumps({"off": off.design, "on": on.design}))
    except Exception as e:  # noqa: BLE001 -- an error is a finding
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--job")
    ap.add_argument("--out", default="eye_pairs_out/off_line_mark")
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(jobs()))
        return 0
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rec = run_job(a.job, out)
    (out / f"{a.job.replace('/', '_').replace(':', '_')}.json").write_text(json.dumps(rec, indent=1))
    print(a.job, rec.get("moved"), rec.get("error", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
