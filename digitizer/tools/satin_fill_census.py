#!/usr/bin/env python
"""Defect 5 re-measured: satin-vs-fill routing against the pro, on today's main.

MEASUREMENT ONLY. Every paired job in `tools.pro_baseline.JOBS` is digitized
ONCE per arm with the Studio's request at the pro's width and garment
(`pro_pair.digitize`, `--set KEY=JSON` laid over it), and the one plan feeds
three readings, so they cannot disagree about what was sewn:

  job kappa     `pro_parity.scorecard`'s stitch-type kappa (satin / fill / run,
                2 mm cells over the shared solid area) -- `pro_baseline.kappas`,
                byte for byte. CHANCE-CORRECTED ONLY (ROADMAP gate 4); the
                chance floor rides beside it.
  oracle        the same cells, with every cell inside one of OUR regions
                relabelled to the pro's majority type in that region: the
                ceiling a perfect per-region classifier reaches on our
                segmentation (`satin-gate-attribution-2026-08-16.md` §4's
                76.6%, now as a kappa). Its gap above `job kappa` is what
                routing can still buy; the gap below 1 is segmentation.
  straddle      cells in regions under 75% one pro type, split by
                `splitprobe.classify_straddle` (ring / split / speckle), and
                the minority cells' connected-component sizes -- the test of
                `segmentation-alignment-2026-08-17.md`'s "speckle is grid
                noise" reading, beside the pro's own map read against itself
                half a cell off (`pro_self_kappa`: what 2 mm cells cost a
                PERFECT engine; also at a quarter cell).
  shape kappa   `tier_census`'s reader on the pro's file per OUR shape
                (FILL / SATIN / SPLIT / RUN; BAR left out as undecidable)
                against our tier from the PLAN, where it is known; grounds
                (a shape with another sewn shape inside) left out, since the
                pro's pieces sewn on them read as their tier. Read it by AREA:
                the same reader scores our own plan ~0.2 by count
                (`reader_on_ours`), which is its noise on small shapes.

    python -m tools.satin_fill_census digitize --runs DIR [--set KEY=JSON ...] [--only SLUG ...]
    python -m tools.satin_fill_census measure --runs DIR [--only SLUG ...]
    python -m tools.satin_fill_census table --runs DIR [--vs DIR2]
    python -m tools.satin_fill_census flip --runs OFF --vs ON              # a flag's two arms
    python -m tools.satin_fill_census render --runs OFF --vs ON --out docs/renders/NAME

`digitize` writes `DIR/<slug>/{ours.dst, design.json, ours.json}`; `measure`
writes `DIR/census.json`; `render` writes OFF | ON crops round every shape whose
tier moved to `--out` and the pro's crop to gitignored `pro_renders/` (Kent
2026-10-27, `tools.pro_renders`). The pro files are gitignored third-party files
(`EMB_SCRATCH_KENT`, `EMB_BRIDGE_PRO`; `tools/pro_baseline.py`). Nothing here
writes a pro render under docs/; the doc it feeds carries numbers only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
for p in (str(DIGITIZER), str(DIGITIZER / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

PURITY = 0.75           # splitprobe / gateprobe's straddle threshold
HALF_CELL_MM = 1.0      # the pro read against itself this far off: 2 mm cells' own noise
SATIN_TIERS = {"SATIN": "satin", "SPLIT": "satin", "FILL": "fill", "RUN": "run"}


# ------------------------------------------------------------------ digitize
def digitize(runs: Path, slugs: list[str], extra: dict) -> None:
    from digitizer_core.export import write_dst
    from digitizer_core.preflight import run_preflight
    from tools import border_census as bc
    from tools import pro_pair
    from tools.pro_baseline import JOBS, resolve
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "arm.json").write_text(json.dumps({"set": extra}), encoding="utf-8")
    for s in slugs:
        out = runs / s
        if (out / "plan.json").exists():           # written last: a killed run leaves none
            print(s, "cached", flush=True)
            continue
        garment, width, art, pro_dst, *_ = JOBS[s]
        d = pro_pair.digitize(resolve(art), width, garment, extra or None)
        out.mkdir(parents=True, exist_ok=True)
        write_dst(d.plan, out / "ours.dst")
        (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
        # tier_census's cache, from the SAME plan (its own digitize would be a second run)
        bc.write_ours(out, s, garment, width, resolve(pro_dst), resolve(art), d.result, d.plan, d.secs)
        # bare cloth the way the flag's own guard test reads it (preflight's uncovered)
        m = run_preflight(d.result, d.plan, d.cfg, image=str(resolve(art)))["metrics"]
        (out / "plan.json").write_text(json.dumps({
            "stitches": d.plan.stats.stitch_count, "trims": d.plan.stats.trims, "secs": round(d.secs, 1),
            "uncovered_total_mm2": m.get("uncovered_total_mm2"),
            "uncovered_worst_mm2": m.get("uncovered_worst_mm2")}), encoding="utf-8")
        print(s, d.plan.stats.stitch_count, d.plan.stats.trims, f"{d.secs:.0f}s",
              "bare", m.get("uncovered_total_mm2"), flush=True)


# ------------------------------------------------------------------- kappas
def _kappa_of(pt, ot) -> tuple[float, float]:
    """scorecard's own corrected sttype: (kappa, chance) over two equal-length type arrays."""
    from tools.pro_parity import scorecard
    if pt.size == 0:
        return 0.0, 0.0
    raw = float((pt == ot).mean())
    ch = scorecard.type_chance(pt, ot)
    return scorecard.chance_correct(raw, ch), ch


def _components(mask) -> list[int]:
    import cv2
    import numpy as np
    n, lab = cv2.connectedComponents(mask.astype(np.uint8), connectivity=4)
    return [int((lab == k).sum()) for k in range(1, n)]


def cell_census(slug: str, runs: Path) -> dict:
    """job kappa, oracle kappa, straddle anatomy and the pro's half-cell self kappa."""
    import numpy as np
    import shapely.wkt
    from shapely.affinity import translate
    from tools.pro_parity import scorecard
    from tools.pro_parity.splitprobe import _cells_of, classify_straddle

    work = runs / slug / "score" / slug                 # written by pro_baseline.kappas
    _r, pro, _s, _t = scorecard.load_side(work, "pro", slug)
    _r, our, _s, _t = scorecard.load_side(work, "ours", slug)
    dx, dy, _iou = scorecard.register(pro, our, scorecard.bounds(pro, our))
    our_r = scorecard.shifted(our, dx, dy)
    bb = scorecard.bounds(pro, our_r)
    pa, pt, _ = scorecard.cell_stats(pro, bb)
    oa, ot, _ = scorecard.cell_stats(our_r, bb)
    _cov, sp, so, _d = scorecard.coverage_component(pro, our_r, bb, scorecard.load_blocks(work, "pro"),
                                                    scorecard.load_blocks(work, "ours"))
    shared = scorecard.solid_cells(sp & so, bb)
    h = min(pa.shape[0], shared.shape[0]); w = min(pa.shape[1], shared.shape[1])
    both = np.zeros(pa.shape, bool)
    both[:h, :w] = shared[:h, :w]
    both &= ~np.isnan(pa) & ~np.isnan(oa)
    tboth = both & (pt >= 0) & (ot >= 0)

    info = json.loads((runs / slug / "ours.json").read_text(encoding="utf-8"))
    oracle = ot.copy()
    # A cell belongs to the SMALLEST sewn region over it. Regions overlap on
    # purpose (an under-fill silhouette, a patch ground, Fremont's 2,137 mm2
    # field under its letters): taken in list order the ground claimed every
    # cell and the "oracle" fell below the engine it is the ceiling of. The
    # smallest is the one sewn on top, which is the thread the cell shows.
    polys = []
    for k, r in enumerate(info["regions"]):
        if not any(key.split(":")[0] in ("fill", "satin", "run", "bean", "border")
                   for key in (r.get("kinds") or {})):
            continue                                    # never becomes thread
        poly = shapely.wkt.loads(r["wkt"])
        if poly.is_empty:
            continue
        if not poly.is_valid:
            poly = poly.buffer(0)
        polys.append((poly.area, k, poly))
    owner = np.full(pt.shape, -1, int)
    for _a, k, poly in sorted(polys, key=lambda t: t[0], reverse=True):
        for c in _cells_of(translate(poly, dx, dy), bb, pt.shape):
            owner[c] = k                                # smaller ones overwrite
    shapes = []
    for _a, k, _poly in sorted(polys, key=lambda t: t[1]):
        r = info["regions"][k]
        cells = [tuple(c) for c in np.argwhere(owner == k)]
        graded = [c for c in cells if tboth[c]]
        if not graded:
            continue
        hist = Counter(int(pt[c]) for c in graded)
        dom, n_dom = hist.most_common(1)[0]
        for c in cells:
            if pt[c] >= 0:
                oracle[c] = dom
        # straddle anatomy on the graded cells of this region
        i0 = min(i for i, _ in graded); i1 = max(i for i, _ in graded)
        j0 = min(j for _, j in graded); j1 = max(j for _, j in graded)
        grid = np.full((i1 - i0 + 1, j1 - j0 + 1), -1, int)
        for i, j in graded:
            grid[i - i0, j - j0] = pt[i, j]
        minority = (grid >= 0) & (grid != dom)
        sizes = _components(minority)
        meta = r.get("meta") or {}
        shapes.append({"id": r["id"], "cells": len(graded), "purity": round(n_dom / len(graded), 3),
                       "pattern": classify_straddle(grid), "pro_dom": dom,
                       "ours_dom": Counter(int(ot[c]) for c in graded).most_common(1)[0][0],
                       "minority_sizes": sizes,
                       "lettering": any(k2 in meta for k2 in
                                        ("text_cluster_id", "lettering_group", "bean_letter", "small_text_stray"))})

    jk, jc = _kappa_of(pt[tboth], ot[tboth])
    ok, oc = _kappa_of(pt[tboth], oracle[tboth])
    in_shape = tboth & (owner >= 0)

    # the pro against himself a little off: what 2 mm cells and a registration
    # error that size cost a PERFECT engine (the same population rule as tboth)
    def self_kappa(off):
        _pa2, pt2, _ = scorecard.cell_stats(scorecard.shifted(pro, off, off), bb)
        hh = min(pt.shape[0], pt2.shape[0]); ww = min(pt.shape[1], pt2.shape[1])
        a, b = pt[:hh, :ww], pt2[:hh, :ww]
        m = (a >= 0) & (b >= 0)
        return _kappa_of(a[m], b[m])
    sk, sc = self_kappa(HALF_CELL_MM)
    qk, _qc = self_kappa(HALF_CELL_MM / 2)

    return {"job_kappa": round(jk, 3), "job_chance": round(jc, 3), "type_cells": int(tboth.sum()),
            "oracle_kappa": round(ok, 3), "oracle_chance": round(oc, 3),
            "cells_in_regions": int(in_shape.sum()),
            "pro_self_kappa": round(sk, 3), "pro_self_chance": round(sc, 3), "pro_self_kappa_half": round(qk, 3),
            "registration_mm": [round(dx, 2), round(dy, 2)], "shapes": shapes}


def region_census(slug: str, runs: Path) -> dict:
    """tier_census's per-shape reading of both files. `ground`: another sewn region
    sits inside this one, so the pro's pieces sewn ON it read as its tier."""
    import shapely.wkt
    from tools import tier_census as tc
    res = tc.analyse(slug, runs)
    info = json.loads((runs / slug / "ours.json").read_text(encoding="utf-8"))
    sewn = {}
    for r in info["regions"]:
        if any(k.split(":")[0] in ("fill", "satin", "run", "bean", "border") for k in r["kinds"]):
            p = shapely.wkt.loads(r["wkt"])
            sewn[r["id"]] = p if p.is_valid else p.buffer(0)
    ground = {i for i, p in sewn.items()
              if any(j != i and q.area < p.area and p.contains(q.representative_point())
                     for j, q in sewn.items())}
    rows = []
    for row in res["rows"]:
        rows.append({"id": row["id"], "lettering": row["lettering"], "area": row["geom"]["area"],
                     "stroke": row["geom"]["stroke"], "plan": row["plan"], "ground": row["id"] in ground,
                     "ours": row["ours"]["tier"], "pro": row["pro"]["tier"]})
    return {"rows": rows}


def measure(runs: Path, slugs: list[str]) -> dict:
    from tools.pro_baseline import JOBS, kappas, resolve
    path = runs / "census.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"jobs": {}}
    for s in slugs:
        if not (runs / s / "ours.json").exists():
            print(s, "not digitized", flush=True)
            continue
        pro = resolve(JOBS[s][3])
        row = {"baseline": kappas(runs / s / "ours.dst", pro, runs / s / "score" / s)}
        row["cells"] = cell_census(s, runs)
        try:
            row["regions"] = region_census(s, runs)
        except Exception as e:                                   # noqa: BLE001 -- a row, not a crash
            row["regions"] = {"error": f"{type(e).__name__}: {e}"[:300]}
        res["jobs"][s] = row
        c = row["cells"]
        print(s, "job", c["job_kappa"], "oracle", c["oracle_kappa"], "self", c["pro_self_kappa"], flush=True)
        path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# -------------------------------------------------------------------- table
def _shape_kappa(rows, weight=False):
    """Cohen's kappa over shapes both files read as satin / fill / run; `weight` by area."""
    pairs = [(SATIN_TIERS[r["ours"]], SATIN_TIERS[r["pro"]], r["area"] if weight else 1.0)
             for r in rows if r["ours"] in SATIN_TIERS and r["pro"] in SATIN_TIERS]
    n = sum(w for *_, w in pairs)
    if not n:
        return None, 0
    po = sum(w for a, b, w in pairs if a == b) / n
    labs = {a for a, *_ in pairs} | {b for _, b, _ in pairs}
    pe = sum((sum(w for a, _, w in pairs if a == lab) / n) * (sum(w for _, b, w in pairs if b == lab) / n)
             for lab in labs)
    return (round((po - pe) / (1 - pe), 3) if pe < 1 else None), len(pairs)


def summary(res: dict) -> dict:
    """Cell figures per job; shape figures as `plan` (our tier, known) against the
    pro's READ tier, grounds out, by AREA. By count the reader is the noise: it
    scores our own known plan ~0.2 (`reader_on_ours`), so count columns ride
    along only to show that."""
    from tools.pro_parity import scorecard
    out = {"jobs": {}}
    pat = Counter(); pat_cells = Counter(); minority = Counter()
    shapes, reader = [], []
    for s, row in res["jobs"].items():
        c = row["cells"]
        regs = row["regions"].get("rows", []) if isinstance(row.get("regions"), dict) else []
        for r in regs:
            plan = r["plan"] if r["plan"] in SATIN_TIERS else "NONE"
            reader.append({**r, "pro": plan})                      # the reader against the truth
            if not r["ground"]:
                shapes.append({**r, "ours": plan, "slug": s})
        straddled = [sh for sh in c["shapes"] if sh["purity"] <= PURITY]
        for sh in c["shapes"]:
            key = "pure" if sh["purity"] > PURITY else sh["pattern"]
            pat[key] += 1
            pat_cells[key] += sh["cells"]
        for sh in straddled:
            for sz in sh["minority_sizes"]:
                minority["1" if sz == 1 else "2-3" if sz <= 3 else "4-9" if sz <= 9 else "10+"] += sz
        out["jobs"][s] = {
            "job_kappa": c["job_kappa"], "job_chance": c["job_chance"],
            "oracle_kappa": c["oracle_kappa"], "pro_self_kappa": c["pro_self_kappa"],
            "pro_self_kappa_half": c.get("pro_self_kappa_half"),
            # the pro sews ONE type: his side of the floor is degenerate, the kappa undefined
            "degenerate": c.get("pro_self_chance", 0) >= scorecard.CHANCE_DEGENERATE,
            "straddled_share": round(sum(sh["cells"] for sh in straddled)
                                     / max(1, sum(sh["cells"] for sh in c["shapes"])), 3),
        }
    out["patterns"] = {k: {"shapes": pat[k], "cells": pat_cells[k]} for k in pat}
    out["minority_cells_by_component"] = dict(minority)
    let = [r for r in shapes if r["lettering"]]
    rest = [r for r in shapes if not r["lettering"]]
    out["shape_kappa"] = {name: {"area": _shape_kappa(rs, True), "count": _shape_kappa(rs)}
                          for name, rs in (("all", shapes), ("lettering", let), ("rest", rest),
                                           ("reader_on_ours", reader))}
    conf = Counter()
    for r in shapes:
        if r["ours"] in SATIN_TIERS and r["pro"] in SATIN_TIERS:
            conf[(SATIN_TIERS[r["ours"]], SATIN_TIERS[r["pro"]])] += r["area"]
    out["confusion_mm2"] = {f"{a}->{b}": round(n) for (a, b), n in sorted(conf.items())}
    ks = [j for j in out["jobs"].values() if not j["degenerate"]]
    out["n_jobs"] = len(ks)
    for k in ("job_kappa", "oracle_kappa", "pro_self_kappa", "pro_self_kappa_half"):
        out[f"mean_{k}"] = round(sum(j[k] for j in ks) / len(ks), 3) if ks else None
    out["oracle_wins"] = sum(j["oracle_kappa"] > j["job_kappa"] for j in ks)
    return out


def _fmt(k):
    v, n = k
    return "-" if v is None else f"{v:.2f} (n {n})"


def table(runs: Path, vs: Path | None) -> str:
    res = json.loads((runs / "census.json").read_text(encoding="utf-8"))
    sm = summary(res)
    other = summary(json.loads((vs / "census.json").read_text(encoding="utf-8"))) if vs else None
    L = ["| job | sttype kappa (chance) | oracle | pro vs pro 0.5 / 1.0 mm | straddled |"
         + (" kappa ON |" if other else ""), "|---|---|---|---|---|" + ("---|" if other else "")]
    for s, j in sm["jobs"].items():
        if j["degenerate"]:
            L.append(f"| {s} | {j['job_kappa']:.2f} ({j['job_chance']:.2f}), undefined | - | - | "
                     f"{100 * j['straddled_share']:.0f}% |" + (" - |" if other else ""))
            continue
        line = (f"| {s} | {j['job_kappa']:.2f} ({j['job_chance']:.2f}) | {j['oracle_kappa']:.2f} | "
                f"{j['pro_self_kappa_half']:.2f} / {j['pro_self_kappa']:.2f} | {100 * j['straddled_share']:.0f}% |")
        if other:
            o = other["jobs"].get(s)
            line += f" {o['job_kappa']:.2f} |" if o else " - |"
        L.append(line)
    L += ["", f"mean of {sm['n_jobs']}: job kappa {sm['mean_job_kappa']}, oracle {sm['mean_oracle_kappa']} "
          f"(wins {sm['oracle_wins']}), pro self 0.5 / 1.0 mm {sm['mean_pro_self_kappa_half']} / "
          f"{sm['mean_pro_self_kappa']}" + (f"; ON {other['mean_job_kappa']}" if other else "")]
    for name, k in sm["shape_kappa"].items():
        L.append(f"shape kappa {name}: area {_fmt(k['area'])}, count {_fmt(k['count'])}"
                 + (f"; ON area {_fmt(other['shape_kappa'][name]['area'])}" if other else ""))
    L.append(f"confusion ours->pro (mm2, grounds out) {sm['confusion_mm2']}")
    L.append(f"patterns {sm['patterns']}")
    L.append(f"straddled minority cells by blob size {sm['minority_cells_by_component']}")
    return "\n".join(L)


# ---------------------------------------------------------- a flag's two arms
def _md5(path: Path) -> str:
    import hashlib
    return hashlib.md5(path.read_bytes()).hexdigest()


def moved_shapes(off: Path, on: Path, slug: str) -> list[dict]:
    """Shapes whose plan tier (the kind carrying most of their thread) differs."""
    from tools.tier_census import plan_tier
    a = {r["id"]: r for r in json.loads((off / slug / "ours.json").read_text(encoding="utf-8"))["regions"]}
    b = {r["id"]: r for r in json.loads((on / slug / "ours.json").read_text(encoding="utf-8"))["regions"]}
    out = []
    import shapely.wkt
    for sid in sorted(set(a) | set(b)):
        ta = plan_tier(a[sid]["kinds"]) if sid in a else "ABSENT"
        tb = plan_tier(b[sid]["kinds"]) if sid in b else "ABSENT"
        if ta != tb:
            poly = shapely.wkt.loads((a.get(sid) or b[sid])["wkt"])
            out.append({"id": sid, "off": ta, "on": tb, "area": round(poly.area, 1),
                        "bounds": [round(v, 2) for v in poly.bounds]})
    return out


def flip_table(off: Path, on: Path) -> str:
    co = json.loads((off / "census.json").read_text(encoding="utf-8"))["jobs"]
    cn = json.loads((on / "census.json").read_text(encoding="utf-8"))["jobs"]
    L = ["| job | identical | shapes moved (mm²) | sttype kappa OFF / ON | stitches OFF / ON | trims OFF / ON "
         "| bare mm² OFF / ON (worst) |", "|---|---|---|---|---|---|---|"]
    for s in co:
        if s not in cn:
            continue
        po = json.loads((off / s / "plan.json").read_text(encoding="utf-8"))
        pn = json.loads((on / s / "plan.json").read_text(encoding="utf-8"))
        same = _md5(off / s / "ours.dst") == _md5(on / s / "ours.dst")
        mv = [] if same else moved_shapes(off, on, s)
        mvs = ", ".join(f"{m['off'].lower()}->{m['on'].lower()} {m['area']}" for m in mv) or ("-" if same else "none")
        ko, kn = co[s]["cells"]["job_kappa"], cn[s]["cells"]["job_kappa"]
        L.append(f"| {s} | {'yes' if same else 'NO'} | {mvs} | {ko:.2f} / {kn:.2f} | "
                 f"{po['stitches']:,} / {pn['stitches']:,} | {po['trims']} / {pn['trims']} | "
                 f"{po['uncovered_total_mm2']} / {pn['uncovered_total_mm2']} "
                 f"({po['uncovered_worst_mm2']} / {pn['uncovered_worst_mm2']}) |")
    return "\n".join(L)


def render(off: Path, on: Path, out: Path, pro_out: Path, slugs: list[str], ppm: float = 20.0) -> None:
    """OFF | ON crops around every moved shape (committed) and the pro's crop (local only)."""
    import cv2
    from tools import flip_sheet_renders as fsr
    from tools import pro_pair
    from tools.pro_baseline import JOBS, resolve
    from tools.pro_parity import pairframe
    out.mkdir(parents=True, exist_ok=True)
    pro_out.mkdir(parents=True, exist_ok=True)
    for s in slugs:
        if not (on / s / "ours.dst").exists() or _md5(off / s / "ours.dst") == _md5(on / s / "ours.dst"):
            continue
        mv = moved_shapes(off, on, s)
        if not mv:
            continue
        x0 = min(m["bounds"][0] for m in mv) - 3; y0 = min(m["bounds"][1] for m in mv) - 3
        x1 = max(m["bounds"][2] for m in mv) + 3; y1 = max(m["bounds"][3] for m in mv) + 3
        box = (x0, y0, x1, y1)
        do = json.loads((off / s / "design.json").read_text(encoding="utf-8"))
        dn = json.loads((on / s / "design.json").read_text(encoding="utf-8"))
        tiles = [pro_pair._label(fsr.render_crop(do, box, ppm), "OFF"),
                 pro_pair._label(fsr.render_crop(dn, box, ppm), "ON")]
        cv2.imwrite(str(out / f"{s}.jpg"), pro_pair._hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])
        _g, _w, _a, pro_dst, pro_pes, _wl = JOBS[s]
        dp = pairframe.design_for(resolve(pro_pes or pro_dst), None, None, s)
        pb = fsr.pro_box(dp, fsr._design_frame(do), box)
        cv2.imwrite(str(pro_out / f"{s}_pro.jpg"),
                    pro_pair._label(fsr.render_crop(dp, pb, ppm), "pro"), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(s, len(mv), "shapes", out / f"{s}.jpg", flush=True)


def main(argv=None) -> int:
    from tools.pro_baseline import JOBS
    from tools.pro_pair import parse_sets
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("digitize", "measure", "table", "flip", "render"))
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("--vs", type=Path, help="the ON arm's runs (table, flip, render)")
    ap.add_argument("--out", type=Path, help="render: where OUR crops go (committable)")
    a = ap.parse_args(argv)
    slugs = [s for s in JOBS if not a.only or s in a.only]
    if a.cmd == "digitize":
        digitize(a.runs, slugs, parse_sets(a.set))
    elif a.cmd == "measure":
        measure(a.runs, slugs)
    elif a.cmd == "flip":
        print(flip_table(a.runs, a.vs))
    elif a.cmd == "render":
        from tools import pro_renders
        render(a.runs, a.vs, a.out, pro_renders.out_dir(a.out.name), slugs)
    else:
        print(table(a.runs, a.vs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
