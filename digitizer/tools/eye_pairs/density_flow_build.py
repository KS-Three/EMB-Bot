"""Build docs/eye-pairs-2026-10-12/density-flow-inputs.json from the stored designs.

    python -m tools.eye_pairs.density_flow_build --src flags-0918-0928=<dir> \\
        --src density-1007=<dir> ... --pro-root <scratch_kent/Embroidery Files> \\
        --cache <scratch json> --out ../docs/eye-pairs-2026-10-12/density-flow-inputs.json

A ONE-OFF, like `pooled_build.py`, kept so the committed numbers can be
audited and rebuilt. The labels are `pooled-inputs.json`'s (PR #842), pair
for pair; nothing is relabelled. Each `--src` is the render directory
(`designs/<fixture>__<arm>.json`) of the page a sitting was judged on. Those
directories are gitignored or scratch on Kent's laptop, and hold our engine's
stitches for client logos, so only the NUMBERS are copied out.

A pair is measured only when BOTH stored designs' stitch counts equal the
counts `pooled-inputs.json` already holds for that pair (from the sitting's
own price table or features): a mismatch means the directory is not the page
he judged, and the pair is left unscored with the reason, never measured on a
look-alike. The pros' files are read from Kent's `scratch_kent/` (the same
paths `tools/pro_parity/prep_all.py` names).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.eye_pairs import density_flow as df
from tools.eye_pairs.pooled_build import REF_ARMS
from tools.eye_pairs_price import changed_shapes

ROOT = Path(__file__).resolve().parents[3]
POOLED = ROOT / "docs" / "eye-pairs-2026-10-11" / "pooled-inputs.json"
BASE = "base"
# Values copied from pooled-inputs for the both-bad question (reused, not rebuilt).
POOLED_LEVELS = ("unsewn_frac", "uncovered_ink_frac", "uncovered_total_mm2", "lost_frac")
# fixture -> the professional's file of that logo, under scratch_kent/Embroidery Files/
# (paths as tools/pro_parity/prep_all.py). tires' file is 3D puff (a different
# construction, foam under satin) and gaulke is off the comparison: neither is used.
PRO_FILES = {
    "becker": "Becker Marine/Becker Hat & Polo Large/beckers logo hat.PES",
    "fremont": "Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES",
    "drone": "Precision Drone/PRECISION DRON HAT 2.PES",
    "golden_tee": " Golden Tee/GOLF HAT.PES",
}
WHERE = {
    "flags-0918-0928": "digitizer/eye_pairs_out/ of 2026-09-18 (primary checkout, gitignored)",
    "density-1007": "columns-sitting worktree's digitizer/eye_pairs_out/ (gitignored)",
    "letterform-1007": "letterform-priors worktree's digitizer/eye_pairs_out/ (gitignored)",
    "off-flags-1003": "the 10-03 sitting's merged render (session scratchpad), its stitches and trims "
                      "equal docs/eye-pairs-2026-10-03/price-tables.json on every fixture",
    "columns-flip-1008": "the 10-08 flip sitting's merged render (session scratchpad), equal to "
                         "docs/eye-pairs-2026-10-08/flip/price-tables.json on every fixture",
}


def _utf(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


class Cache:
    def __init__(self, path: Path | None):
        self.path = path
        self.data = _utf(path) if path and path.exists() else {}

    def get(self, key, fn):
        if key not in self.data:
            self.data[key] = fn()
            self.save()
        return self.data[key]

    def save(self):
        if self.path:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data), encoding="utf-8")
            tmp.replace(self.path)


def _job(args):
    """One cache entry, in a worker process: (key, path, shapes or None, what)."""
    key, path, shapes, what = args
    d = _utf(Path(path))
    if what == "support":
        return key, _support(d)
    return key, df.measure(d, set(shapes) if shapes else None, support=False)


def prefetch(pooled_inputs: dict, srcs: dict[str, Path], cache: Cache, workers: int) -> None:
    """Fill the cache for every design measurement `build` will ask for, in
    parallel. Same pairing logic as `_measure_pair`, nothing recorded here."""
    from concurrent.futures import ProcessPoolExecutor

    jobs = {}
    for sid, s in pooled_inputs["sittings"].items():
        src = srcs.get(sid)
        if src is None:
            continue
        for p in s["pairs"]:
            if p.get("unscored_why"):
                continue
            fx, arm = p["fixture"], p["arm"]
            pb, pa = src / "designs" / f"{fx}__{BASE}.json", src / "designs" / f"{fx}__{arm}.json"
            if not (pb.exists() and pa.exists()):
                continue
            ch = changed_shapes(_utf(pb), _utf(pa)) or None
            for path in (pb, pa):
                for key, what in ((_key(path, ch), "scoped"), (f"{path}|support", "support")):
                    if key not in cache.data:
                        jobs[key] = (key, str(path), sorted(ch) if ch else None, what)
    print(f"{len(jobs)} measurements to run on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (key, val) in enumerate(ex.map(_job, jobs.values()), 1):
            cache.data[key] = val
            if i % 10 == 0:
                cache.save()
                print(f"  {i}/{len(jobs)}", flush=True)
    cache.save()


def _key(path: Path, shapes) -> str:
    h = hashlib.sha1(json.dumps(sorted(shapes)).encode()).hexdigest()[:12] if shapes else "whole"
    return f"{path}|{h}"


def pro_densities(pro_root: Path | None) -> dict:
    out = {}
    if pro_root is None:
        return out
    import pystitch
    from digitizer_core.adapter import pattern_to_design

    for fx, rel in PRO_FILES.items():
        p = pro_root / rel
        if not p.exists():
            out[fx] = {"file": rel, "missing": True}
            continue
        d = pattern_to_design(pystitch.read(str(p)))
        segs = df.segments(d)
        out[fx] = {"file": rel, "thread_density_whole": round(df.thread_density(segs), 4),
                   "stitches": sum(1 for s in d["stitches"] if s["type"] == "stitch")}
    return out


def build(pooled_inputs: dict, srcs: dict[str, Path], pro: dict, cache: Cache) -> dict:
    sittings = {}
    for sid, s in pooled_inputs["sittings"].items():
        pairs = []
        for p in s["pairs"]:
            q = {k: p[k] for k in ("id", "arm", "fixture", "label", "judged") if k in p}
            q["before"], q["after"] = {}, {}
            for side in ("before", "after"):
                for k in POOLED_LEVELS:
                    if k in p[side]:
                        q[side][k] = p[side][k]
            if p.get("refused"):
                q["refused"] = p["refused"]
            src = srcs.get(sid)
            if p.get("unscored_why"):
                q["unscored_why"] = p["unscored_why"]
            elif src is None:
                q["unscored_why"] = "no stored designs of this sitting's page found"
            else:
                _measure_pair(q, p, src, pro, cache)
            pairs.append(q)
        sittings[sid] = {"date": s["date"], "labels": s.get("labels", ""),
                         "designs": WHERE.get(sid, "none found"), "pairs": pairs}
    return sittings


def _measure_pair(q: dict, p: dict, src: Path, pro: dict, cache: Cache) -> None:
    fx, arm = p["fixture"], p["arm"]
    pb, pa = src / "designs" / f"{fx}__{BASE}.json", src / "designs" / f"{fx}__{arm}.json"
    if not (pb.exists() and pa.exists()):
        q["unscored_why"] = "design file missing from the render directory"
        return
    db, da = _utf(pb), _utf(pa)
    # before / after are the page's LEFT / RIGHT: the old engine is LEFT on the ref arms
    (dl, pl), (dr, pr) = ((da, pa), (db, pb)) if arm in REF_ARMS else ((db, pb), (da, pa))
    for side, d in (("before", dl), ("after", dr)):
        want = p[side].get("stitches")
        if want is None or int(want) != int(d.get("stitchCount") or 0):
            q["unscored_why"] = (f"stitch count {d.get('stitchCount')} on the {side} design does not "
                                 f"equal the sitting's {want}: not the page he judged")
            return
    ch = changed_shapes(db, da) or None
    for side, d, path in (("before", dl, pl), ("after", dr, pr)):
        m = dict(cache.get(_key(path, ch), lambda d=d: df.measure(d, ch, support=False)))
        m.update(cache.get(f"{path}|support", lambda d=d: _support(d)))
        if fx in pro and "thread_density_whole" in pro[fx]:
            m["density_pro_gap"] = abs(m["thread_density_whole"] - pro[fx]["thread_density_whole"])
        q[side].update({k: (round(v, 6) if isinstance(v, float) else v)
                        for k, v in m.items() if v is not None})
    q["designs"] = {"changed_shapes": len(ch) if ch else 0,
                    "stitches": [int(dl["stitchCount"]), int(dr["stitchCount"])]}


def _support(d: dict) -> dict:
    from tools.underlay_cover import measure, runs_from_design

    w = measure(runs_from_design(d))["whole"]
    return {"back_share_thread": w["back_share_thread"], "top_support": w["top_support"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", action="append", default=[], help="sitting=render_dir")
    ap.add_argument("--pro-root", type=Path, default=None)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--only", default=None, help="measure one sitting (fills the cache)")
    ap.add_argument("--workers", type=int, default=1, help="processes for the measurements")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    srcs = dict((s.split("=", 1)[0], Path(s.split("=", 1)[1])) for s in args.src)
    if args.only:
        srcs = {k: v for k, v in srcs.items() if k == args.only}
    pro = pro_densities(args.pro_root)
    cache = Cache(args.cache)
    if args.workers > 1:
        prefetch(_utf(POOLED), srcs, cache, args.workers)
    sittings = build(_utf(POOLED), srcs, pro, cache)
    data = {"schema": 1, "built": "2026-10-12",
            "labels_from": "docs/eye-pairs-2026-10-11/pooled-inputs.json (PR #842), unchanged",
            "pro": pro, "candidates": {k: list(v) for k, v in df.CANDIDATES.items()},
            "sittings": sittings}
    n = sum(1 for s in sittings.values() for p in s["pairs"] if p.get("designs"))
    print(f"{n} pairs measured from stored designs")
    for s in sittings.values():
        for p in s["pairs"]:
            if p.get("unscored_why") and "not the page" in p["unscored_why"]:
                print("MISMATCH", p["id"], p["unscored_why"])
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
