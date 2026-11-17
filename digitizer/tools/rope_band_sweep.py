"""rope_band OFF | ON: a labelled ORIGINAL | BEFORE | AFTER picture for every design the
flag moves (Kent 2026-11-16 ruling), plus a json of md5s of the STITCHES.

  python -m tools.rope_band_sweep --out ../docs/renders/rope-band-2026-11-17            # 9 pro jobs
  python -m tools.rope_band_sweep --fixtures --out DIR [--shard K/N]   # corpus_scorecard.FIXTURES, 80 mm left_chest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))


def _jobs(fixtures: bool, only):
    from tools import pro_baseline as pb
    if fixtures:
        from tools import corpus_scorecard
        jobs = [(f, "left_chest", 80.0, DIGITIZER / "testdata" / f) for f in corpus_scorecard.FIXTURES]
    else:
        from tools import prime_grader
        jobs = [(s, pb.JOBS[s][0], float(pb.JOBS[s][1]), pb.resolve(pb.JOBS[s][2]))
                for s in prime_grader.population()]
    return [j for j in jobs if not only or j[0] in only]


def main(argv=None) -> int:
    import cv2
    from digitizer_core import stitchviz
    from tools import pro_pair as pp
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--fixtures", action="store_true")
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    k, n = (int(v) for v in a.shard.split("/"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = {}
    for name, garment, width, art in _jobs(a.fixtures, a.only)[k::n]:
        stem = Path(name).stem
        try:
            d0 = pp.digitize(art, width, garment, extra={pp.EXTRA_PREFIX + "rope_band": False})
            d1 = pp.digitize(art, width, garment, extra={pp.EXTRA_PREFIX + "rope_band": True})
        except Exception as e:  # noqa: BLE001 - recorded, not hidden
            rows[name] = {"error": repr(e)[:200]}
            print(name, "ERROR", repr(e)[:120], flush=True)
            continue
        h = [hashlib.md5(json.dumps(d.design["stitches"], sort_keys=True, default=str).encode()).hexdigest()
             for d in (d0, d1)]
        n_st = [len(d.design["stitches"]) for d in (d0, d1)]
        moved = h[0] != h[1]
        rows[name] = {"moved": moved, "stitches_off": n_st[0], "stitches_on": n_st[1], "width_mm": width,
                      "garment": garment}
        print(name, "MOVED" if moved else "same", n_st, flush=True)
        if moved:
            ppm = 20.0
            imgs = [pp._label(pp._scaled(pp._art_ink(art), width, ppm, cv2.INTER_AREA), "ORIGINAL"),
                    pp._label(stitchviz.render_design(d0.design, px_per_mm=ppm), "BEFORE (rope_band OFF)"),
                    pp._label(stitchviz.render_design(d1.design, px_per_mm=ppm), "AFTER (rope_band ON)")]
            cv2.imwrite(str(out / f"{stem}.png"), pp._hstack(imgs))
    tag = "fixtures" if a.fixtures else "sweep"
    (out / f"{tag}{'' if n == 1 else f'-{k}of{n}'}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
