"""Run the merged letter_fault_reader (79fa7646), logic unchanged, on corpus rows.

The reader's `run` is wired to pro jobs (item `L_<slug>`, art from
`pro_baseline.JOBS`). This driver changes only WHERE the art comes from
(`spec["art"]`, the corpus image) and the item prefix (`C_`). The worker body,
`read_faults` and every constant are the reader's own.

    python run_reader_corpus.py RUN_DIR PHOTOS_DIR OUT_DIR TREE SLUG [SLUG...]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from tools import letter_fault_reader as lr
from tools import photo_corpus as pc

run_dir, photos, out, tree = (Path(a) for a in sys.argv[1:5])
slugs = sys.argv[5:]
OLD = 'art = pb.resolve(pb.JOBS[spec["slug"]][2])'
assert lr.WORKER.count(OLD) == 1, "worker art line moved"
WORKER = lr.WORKER.replace(OLD, 'art = spec["art"]')
out.mkdir(parents=True, exist_ok=True)
sha = lr._tree_sha(tree)
env = {**os.environ, "OPENCV_IPP": "avx2", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
       "MKL_NUM_THREADS": "1", "OPENCV_FOR_THREADS_NUM": "1", "PYTHONIOENCODING": "utf-8"}
env.pop("PYTHONPATH", None)          # the worker must import the TREE's code (cwd), not the lane's
bad = 0
for slug in slugs:
    iid = f"C_{slug}"
    job = run_dir / f"{slug}.json"
    stored = json.loads(job.read_text(encoding="utf-8"))
    classes = lr.colour_classes(stored["design"]["colors"])
    raw = out / f"{iid}.raw.json"
    labels = out / f"{iid}.labels.npz"
    spec = {"tree": str(tree), "slug": slug, "job": str(job), "out": str(raw),
            "art": str(pc.photo_path(photos, slug)),
            "mask": str(out / f"{iid}.mask.npz"), "labels": str(labels), "pxmm": lr.PXMM,
            "pad": lr.PAD_MM, "thread_mm": lr.THREAD_MM, "classes": [list(c) for c in classes]}
    proc = subprocess.run([sys.executable, "-c", WORKER, json.dumps(spec)], cwd=str(tree), env=env,
                          capture_output=True, text=True, timeout=1800.0)
    if proc.returncode != 0:
        print(slug, "ERROR", proc.stderr.strip().splitlines()[-6:], flush=True)
        bad += 1
        continue
    r = json.loads(raw.read_text(encoding="utf-8"))
    if not r["same_stitches"]:
        print(slug, "REFUSED: re-run stitches differ from the stored design", flush=True)
        bad += 1
        continue
    lab = np.load(labels)
    flags = lr.read_faults(lab["art"], lab["thread"])
    kinds = {}
    for f in flags:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    rec = {"item": iid, "reader": "letter_fault_reader", "tree_sha": sha,
           "stored_tree_sha": (stored.get("_meta") or {}).get("tree_sha"),
           "stitches_sha256": r["stored_sha"], "px_per_mm": lr.PXMM, "pad_mm": lr.PAD_MM,
           "img_w": r["img_w"], "img_h": r["img_h"], "art_px_per_mm": r["art_px_per_mm"],
           "classes": [list(c) for c in classes], "by_kind": kinds, "flags": flags}
    (out / f"{iid}.flags.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    raw.unlink()
    print(slug, "flags", len(flags), kinds, flush=True)
raise SystemExit(1 if bad else 0)
