"""`cap_merged_layer_home` and `shadow_to_page` (ON since 2026-11-18; the arms name both fields) OFF vs ON over every committed pro
job (`tools.tripwire.committed_jobs`, every placement) and the 26
`corpus_scorecard.FIXTURES` (2026-11-18).

    python -m tools.layer_shadow_sweep --list
    python -m tools.layer_shadow_sweep --job KEY --out DIR

One job per process. A pro job runs at its own width and garment
(`tools.pro_baseline.JOBS`); a fixture at the Studio request, 80 mm `left_chest`.
Four arms: OFF, A (`cap_merged_layer_home`), B (`shadow_to_page`), AB. Writes
`DIR/KEY.json`: stitch md5 per arm, the movers' figures (stitches, trims, jumps,
needle-up mm, bare thread, preflight) and the plan (shapes dropped, layers
moved, block order); on a mover also both designs for rendering."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

ARMS = {"OFF": {"cap_merged_layer_home": False, "shadow_to_page": False},
        "A": {"cap_merged_layer_home": True, "shadow_to_page": False},
        "B": {"cap_merged_layer_home": False, "shadow_to_page": True},
        "AB": {"cap_merged_layer_home": True, "shadow_to_page": True}}


def jobs() -> dict[str, tuple[str, float, str]]:
    from tools.corpus_scorecard import FIXTURES
    from tools.pro_baseline import JOBS
    from tools.tripwire import committed_jobs
    out = {}
    for s in committed_jobs():
        g, w, art, *_ = JOBS[s]
        out[s] = (g, float(w), art)
    for f in FIXTURES:
        out["fx:" + f] = ("left_chest", 80.0, "testdata:" + f)
    return out


def _md5(design: dict) -> str:
    return hashlib.md5(str(design["stitches"]).encode()).hexdigest()


def needle_up_mm(plan) -> float:
    tot, prev = 0.0, None
    for b in plan.blocks:
        for r in b.runs:
            if r.jump and prev is not None and r.points:
                tot += math.dist(prev, r.points[0])
            if r.points:
                prev = r.points[-1]
    return round(tot, 1)


def figures(d) -> dict:
    from digitizer_core.preflight import run_preflight
    from tools.flip_sheet_renders import bare_by_band
    st = d.plan.stats
    out = {"stitches": st.stitch_count, "trims": st.trims, "jumps": st.jumps,
           "needle_up_mm": needle_up_mm(d.plan), "threads": len(d.plan.blocks),
           "bare": bare_by_band(d.plan), "regions": len(d.result.regions)}
    try:
        pf = run_preflight(d.result, d.plan, d.cfg)
        out["preflight"] = {"grade": pf.get("grade"), "score": pf.get("score"),
                            "findings": [f.get("code") if isinstance(f, dict) else str(f)
                                         for f in pf.get("findings") or []][:40],
                            "metrics": {k: v for k, v in (pf.get("metrics") or {}).items()
                                        if isinstance(v, (int, float))}}
    except Exception as e:  # noqa: BLE001
        out["preflight"] = {"error": f"{type(e).__name__}: {e}"[:200]}
    return out


def plan_shapes(d) -> dict:
    return {r.shape_id: {"thr": r.thread_number, "layer": (r.meta or {}).get("layer"),
                         "area": round(r.area_mm2, 2),
                         "capm": (r.meta or {}).get("color_cap_merged_from")}
            for r in d.result.regions}


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
        ds = {a: pp.digitize(art, width, garment, e) for a, e in ARMS.items()}
        rec["secs"] = round(time.time() - t, 1)
        rec["md5"] = {a: _md5(d.design) for a, d in ds.items()}
        rec["moved"] = {a: rec["md5"][a] != rec["md5"]["OFF"] for a in ("A", "B", "AB")}
        if any(rec["moved"].values()):
            rec["figures"] = {a: figures(ds[a]) for a in ARMS if a == "OFF" or rec["moved"].get(a)}
            base = plan_shapes(ds["OFF"])
            rec["plan"] = {}
            for a in ("A", "B", "AB"):
                if not rec["moved"][a]:
                    continue
                cur = plan_shapes(ds[a])
                rec["plan"][a] = {
                    "dropped": [{"id": i, **base[i]} for i in base if i not in cur],
                    "added": [{"id": i, **cur[i]} for i in cur if i not in base],
                    "layer_moved": [{"id": i, "from": base[i]["layer"], "to": cur[i]["layer"],
                                     "thr": cur[i]["thr"], "area": cur[i]["area"]}
                                    for i in cur if i in base and cur[i]["layer"] != base[i]["layer"]],
                    "blocks": [b.thread_number for b in ds[a].plan.blocks]}
            rec["plan"]["OFF_blocks"] = [b.thread_number for b in ds["OFF"].plan.blocks]
            (out / f"{key.replace('/', '_').replace(':', '_')}.designs.json").write_text(
                json.dumps({a: ds[a].design for a in ARMS}))
    except Exception as e:  # noqa: BLE001 -- an error is a finding
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--job")
    ap.add_argument("--out", default="eye_pairs_out/layer_shadow")
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
