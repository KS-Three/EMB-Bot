#!/usr/bin/env python
"""garment_border_census: does the pro's border / bean choice change with the garment?

Kent (2026-11-19) asked whether a fabric rule should pick satin vs bean borders
(a web guide: lighter borders on thin knits, no bean on pile). Before building
one, this asks the professional's own files. Every artwork in
`pro_baseline.ARTWORK` with more than one job is the same art sewn on different
garments (cap, pique polo, jersey beanie, canvas patch), so a garment rule in
his practice would show as a difference between those files.

Reads ONLY the pro's DSTs (no digitize, no registration to our segmentation).
Per job:

  satin_*   every satin column `border_pro.study` finds: count, spine mm,
            true width median / p90, rail density
  border_*  the satin columns that ride a fill's edge (`fill_edge`): count, mm,
            width, how many close as a loop
  bean_*    retraced runs (`bean_census.file_beans`, double or triple) that no
            later stitch covers by half or more: count, mm, pitch, passes
  single_mm one-pass running lines nothing later covers
  fills     area fills (`border_pro.area_fills`): area mm2, stitches per mm2 and
            the colour block, so a sparse first-block knockdown shows

  python -m tools.garment_border_census [--json OUT] [--fills]

Prints one JSON line per job. Nothing is written unless `--json` is given.
Result and reading: DOCTRINE "Measured negatives", 2026-11-19 entry.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
for p in (DIGITIZER, DIGITIZER / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tools import bean_census as bc  # noqa: E402
from tools import border_pro as bp  # noqa: E402
from tools import pro_baseline as pb  # noqa: E402
from study_pro import load_runs  # noqa: E402

#: a bean / run this share covered by later stitches is underlay, not a line anyone sees
HIDDEN_COVER = 0.5


def _med(a):
    return round(st.median(a), 2) if a else None


def _p90(a):
    if not a:
        return None
    s = sorted(a)
    return round(s[min(len(s) - 1, int(0.9 * len(s)))], 2)


def job(slug: str, *, with_fills: bool = False) -> dict:
    garment, width, _art, dst, *_ = pb.JOBS[slug]
    path = pb.resolve(dst)
    recs, fills, n_trim, _ = bp.study(path)
    cols = [r for r in recs if r["kind"] == "col"]
    edge = [r for r in cols if r.get("fill_edge")]
    runs, _t, _j = load_runs(path)
    cover = bc.LaterCover(runs)
    seen = [b for b in bc.file_beans(runs, singles=True)
            if cover.covered(b["spine"], (b["run"], b["i1"])) < HIDDEN_COVER]
    beans = [b for b in seen if b["kind"] != "single"]
    singles = [b for b in seen if b["kind"] == "single"]
    wt = [r["width_true"] for r in cols if r.get("width_true")]
    ew = [r["width_true"] for r in edge if r.get("width_true")]
    out = {
        "slug": slug, "garment": garment, "width_mm": width,
        "stitches": sum(len(r["pts"]) for r in runs), "trims": n_trim,
        "blocks": len({r["block"] for r in runs}),
        "satin_cols": len(cols), "satin_mm": round(sum(r["path_mm"] for r in cols)),
        "satin_w_med": _med(wt), "satin_w_p90": _p90(wt),
        "satin_dens_med": _med([r["dens_med"] for r in cols if r.get("dens_med")]),
        "border_cols": len(edge), "border_mm": round(sum(r["path_mm"] for r in edge)),
        "border_w_med": _med(ew), "border_closed": sum(1 for r in edge if r["closed"]),
        "bean_n": len(beans), "bean_mm": round(sum(b["length_mm"] for b in beans)),
        "bean_pitch": _med([b["pitch_mm"] for b in beans]),
        "bean_passes": _med([b["passes"] for b in beans]),
        "single_mm": round(sum(b["length_mm"] for b in singles)),
    }
    if with_fills:
        out["fills"] = [{"run": f["idx"], "block": f["block"], "area_mm2": round(f["area"]),
                         "st_per_mm2": round(len(runs[f["idx"]]["pts"]) / max(f["area"], 1.0), 2)}
                        for f in bp.area_fills(runs)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, help="also write every row to this file")
    ap.add_argument("--fills", action="store_true", help="list each job's area fills")
    a = ap.parse_args(argv)
    rows = []
    for art, slugs in pb.ARTWORK.items():
        if len(slugs) < 2:
            continue
        for s in slugs:
            try:
                r = job(s, with_fills=a.fills)
            except SystemExit as e:          # pro file not on this machine
                r = {"slug": s, "error": str(e)}
            r["art"] = art
            rows.append(r)
            print(json.dumps(r), flush=True)
    if a.json:
        a.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
