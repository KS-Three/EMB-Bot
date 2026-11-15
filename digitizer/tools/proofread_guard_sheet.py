"""The proof-read guard, OFF against ON, on kept proof-read jobs.

    python -m tools.proofread_guard_sheet --out DIR --name N [--name N ...] --dest DIR

For each kept job (`tools.proofread run --keep`: the PipelineResult, the plan
and the graded raster), plans the design twice back to back from the same
result, guard OFF and guard ON (`cfg.proofread_guard_clipped`), on the
traced raster the job kept, and writes to DEST:

  <name>.guard.png    art | OFF render | ON render, the proof-read's counts under each
  guard.json          per job: both plans' md5 (stitch coordinates, kinds, jump/trim),
                      plan seconds OFF and ON, the guard's record, the proof-read's
                      unexplained / misfire / explained and `worse_mm2` OFF and ON

The OFF plan is also compared with the kept plan (same tree: the same md5).
Times are wall seconds on whatever else the machine was running; read the
ON - OFF difference, not either alone.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def plan_md5(plan) -> str:
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim] for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def _label(img: np.ndarray, text: str) -> np.ndarray:
    head = np.full((26, img.shape[1], 3), 255, np.uint8)
    cv2.putText(head, text[:120], (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack([head, img])


def one(out: Path, name: str, dest: Path) -> dict:
    from digitizer_core import proofread as pr
    from digitizer_core import proofread_guard as pg
    from digitizer_core.pipeline import plan_stitches
    job = pickle.load(open(out / f"{name}.job.pkl", "rb"))
    g = job["graded"]
    art = g                                  # the graded raster, page mask and page colour with it
    cfg_off = copy.copy(job["cfg"])
    cfg_off.proofread_guard_clipped = False
    cfg_on = copy.copy(job["cfg"])
    cfg_on.proofread_guard_clipped = True
    r_off = copy.deepcopy(job["result"])
    r_on = copy.deepcopy(job["result"])
    r_on.proof_art = art
    t0 = time.time()
    p_off = plan_stitches(r_off, cfg_off)
    t_off = time.time() - t0
    t0 = time.time()
    p_on = plan_stitches(r_on, cfg_on)
    t_on = time.time() - t0
    rep_off = pr.read(art, r_off, p_off, cfg_off)
    rep_on = pr.read(art, r_on, p_on, cfg_on)

    def counts(rep):
        return {"unexplained": rep["unexplained"], "misfire": rep["misfires"], "explained": rep["explained"],
                "worse_mm2": pg.worse_mm2(rep), "counts": rep["counts"]}
    rec = {"name": name, "md5_kept": plan_md5(job["plan"]), "md5_off": plan_md5(p_off), "md5_on": plan_md5(p_on),
           "plan_s_off": round(t_off, 1), "plan_s_on": round(t_on, 1), "guard": getattr(p_on, "proofread_guard", None),
           "off": counts(rep_off), "on": counts(rep_on)}
    rec["changed"] = rec["md5_on"] != rec["md5_off"]
    # sheet: art | OFF | ON
    from digitizer_core.adapter import plan_to_design
    from digitizer_core import stitchviz
    ro = stitchviz.render_design(plan_to_design(p_off, name="d"), px_per_mm=10.0, pad_mm=2.0)
    rn = stitchviz.render_design(plan_to_design(p_on, name="d"), px_per_mm=10.0, pad_mm=2.0)
    h = max(ro.shape[0], rn.shape[0])
    src = cv2.cvtColor(g.rgb, cv2.COLOR_RGB2BGR)
    bg = pr.page_mask(g)                    # the page (bg + enclosed holes), shown pale
    src[bg] = (src[bg] * 0.2 + 255 * 0.8).astype(np.uint8)
    s = h / src.shape[0]
    src = cv2.resize(src, (max(1, int(src.shape[1] * s)), h), interpolation=cv2.INTER_AREA)

    def padh(im):
        return np.vstack([im, np.full((h - im.shape[0], im.shape[1], 3), 255, np.uint8)]) if im.shape[0] < h else im
    gap = np.full((h + 26, 8, 3), 255, np.uint8)
    o, n = rec["off"], rec["on"]
    sheet = np.hstack([_label(padh(src), f"{name}: art"), gap,
                       _label(padh(ro), f"OFF  unexpl {o['unexplained']} misfire {o['misfire']} worse {o['worse_mm2']} mm2"),
                       gap,
                       _label(padh(rn), f"ON  unexpl {n['unexplained']} misfire {n['misfire']} worse {n['worse_mm2']} mm2"
                                        f"  {'CHANGED' if rec['changed'] else 'same md5'}")])
    dest.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest / f"{name}.guard.png"), sheet)
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", action="append", required=True)
    ap.add_argument("--dest", required=True)
    a = ap.parse_args(argv)
    dest = Path(a.dest)
    path = dest / "guard.json"
    allrec = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for name in a.name:
        rec = one(Path(a.out), name, dest)
        allrec[name] = rec
        path.write_text(json.dumps(allrec, indent=1, default=str) + "\n", encoding="utf-8")
        g = rec["guard"] or {}
        print(name, "changed" if rec["changed"] else "same", "kept==off" if rec["md5_kept"] == rec["md5_off"] else "KEPT!=OFF",
              "t", rec["plan_s_off"], "->", rec["plan_s_on"], "guard", {k: g.get(k) for k in
              ("candidates", "candidate_ink_mm2", "worse_mm2_before", "worse_mm2_after", "accepted")},
              "off", rec["off"]["worse_mm2"], "on", rec["on"]["worse_mm2"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
