"""All seven logos through the letterform fit, and the go/no-go table the
brief asks for:

  1. byte-identical WKB on the clean uploads (enthusiast, drone) -- the hash
     of every text-tagged polygon before and after;
  2. against the pro where he exists (Becker): per letter, Hausdorff and
     IoU of the traced and the refit outline vs his sewn outline, in the
     registered frame and centred on ours;
  3. structure: primitives per letter, stem-angle spread within a word,
     stroke-width CV, before / after;
  4. downstream: stages 5-7 re-run (`plan_stitches`) on the traced and on
     the refit polygons, read by `digitizer_core.edge_wobble.analyse_plan`
     and `tools/rail_edge.bare_area` on the text shapes, and the outline-cut
     spike's construction (`oc.letter_columns`, a copy of the sibling lane's
     file dropped in `<scratch>/oc/`) with its own over-long and clean checks.

Usage (from the spike folder; the inputs come from `run.py`):

    python batch.py [logo ...] [--k 0.75] [--no-downstream] [--no-oc] [--sheets] [--tag NAME]

Prints a markdown table and writes `<scratch>/batch_<tag>.json`.
"""
from __future__ import annotations

import copy
import json
import os
import pickle
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                               # digitizer/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
SCRATCH = Path(os.environ.get("LETTERFORM_SCRATCH", ROOT.parent / "scratch_letterform_priors"))

from refit import apply, refit_logo, source_px_mm, summarize              # noqa: E402
from fit import K_DEFAULT, polygon_wkb_hash                                  # noqa: E402

LOGOS = ["becker", "bridge", "gaulke", "drone", "enthusiast", "fremont", "tires"]
HELD_OUT = {"gaulke"}
PRO = {"becker": ROOT / "testdata" / "reference" / "becker_hat_polo_large_beckers_logolc.dst"}


# ------------------------------------------------------------ downstream
def downstream(d: dict, name: str, rows, k: float) -> dict | None:
    """Stages 5-7 on the traced and on the refit polygons; the two edge
    instruments on the text shapes of each plan."""
    rp = SCRATCH / f"{name}.result.pkl"
    if not rp.exists():
        return None
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import plan_stitches
    from digitizer_core.edge_wobble import analyse_plan
    from rail_edge import bare_area
    saved = pickle.load(open(rp, "rb"))
    cfg = PipelineConfig(**saved["cfg_kwargs"])
    text_ids = {r.shape_id for r in rows}
    out = {}
    for arm in ("traced", "refit"):
        result = copy.deepcopy(saved["result"])
        if arm == "refit":
            apply(result.regions, rows)
        t = time.time()
        plan = plan_stitches(result, cfg)
        polys = {r.shape_id: r.polygon for r in result.regions if r.shape_id in text_ids}
        wob = analyse_plan(polys, plan, unsewn=False)
        bare_num, bare_den = bare_area(polys, plan)
        n_text_st = sum(len(run.points) for _b, run in plan.iter_runs() if run.shape_id in text_ids)
        out[arm] = dict(
            stitches=plan.stats.stitch_count, trims=plan.stats.trims, text_stitches=n_text_st,
            wobble_std=wob.get("wobble_std_mm"), wobble_p95=wob.get("wobble_p95_mm"),
            satin_wobble_std=(wob.get("by_tier", {}).get("satin") or {}).get("wobble_std_mm"),
            satin_wobble_p95=(wob.get("by_tier", {}).get("satin") or {}).get("wobble_p95_mm"),
            bare_pct=100.0 * bare_num / bare_den if bare_den else None, satin_art_mm2=bare_den,
            secs=round(time.time() - t, 1))
    return out


# ----------------------------------------------------------- outline-cut
def outline_cut(rows) -> dict | None:
    """The sibling spike's construction on traced and refit polygons, with
    its own two numbers: thread off the artwork, and stitches longer than
    1.6 x the letter's stroke width (both as shares of thread length), plus
    its 'clean' check. Coverage here is shapely (thread buffered to 0.4 mm)
    rather than the sibling's 30 px/mm raster -- same definition, not the
    same instrument, so compare its two arms with each other only."""
    oc_dir = SCRATCH / "oc"
    if not (oc_dir / "oc.py").exists():
        return None
    sys.path.insert(0, str(oc_dir))
    import oc
    out = {}
    for arm in ("traced", "refit"):
        tot = out_len = long_len = 0.0
        letters = clean = crashed = 0
        per = []
        for row in rows:
            poly = row.traced if arm == "traced" else row.refit
            letters += 1
            try:
                res = oc.letter_columns(poly)
            except Exception:                                # noqa: BLE001
                crashed += 1
                continue
            safe = res["poly"].buffer(0.15)
            l_tot = l_out = l_long = 0.0
            unsewn = 0
            sewn = []
            for c in res["cols"]:
                if not c["stitches"]:
                    unsewn += 1
                    continue
                for p, q in zip(c["stitches"][:-1], c["stitches"][1:]):
                    seg = LineString([p, q])
                    l_tot += seg.length
                    l_out += seg.length - seg.intersection(safe).length
                    if seg.length > 1.6 * res["W"]:
                        l_long += seg.length
                    sewn.append(seg)
            cov = 0.0
            if sewn:
                cov = unary_union([s.buffer(0.2, cap_style=2) for s in sewn]).intersection(res["poly"]).area / max(res["poly"].area, 1e-9)
            ok = unsewn == 0 and l_tot > 0 and l_out / l_tot < 0.02 and l_long / l_tot < 0.05 and cov > 0.9
            clean += int(ok)
            tot += l_tot
            out_len += l_out
            long_len += l_long
            per.append(dict(shape_id=row.shape_id, char=row.char, status=row.fit.status, clean=ok,
                            over_long=l_long / max(l_tot, 1e-9), off_art=l_out / max(l_tot, 1e-9),
                            covered=cov, pieces=len(res["cols"]), W=res["W"]))
        out[arm] = dict(letters=letters, clean=clean, crashed=crashed,
                        over_long=long_len / max(tot, 1e-9), off_art=out_len / max(tot, 1e-9), per=per)
    return out


# ------------------------------------------------------------------ pro
def pro_compare(name: str, d: dict, rows) -> dict | None:
    path = PRO.get(name)
    if path is None or not path.exists():
        return None
    import pro
    letters = {r.shape_id: r.traced for r in rows}
    design = [r["polygon"] for r in d["regions"]]
    pro_map, regs, block_of, reg0, _whole, _outl = pro.pro_letters_for(path, letters, design, d["width"])
    per = []
    for r in rows:
        pp = pro_map.get(r.shape_id)
        ht, it, htc, itc = pro.compare(r.traced, pp)
        hr, ir, hrc, irc = pro.compare(r.refit, pp)
        per.append(dict(shape_id=r.shape_id, char=r.char, word=r.word, status=r.fit.status,
                        block=block_of.get(r.shape_id), matched=ht is not None,
                        H_traced=ht, H_refit=hr, IoU_traced=it, IoU_refit=ir,
                        Hc_traced=htc, Hc_refit=hrc, IoUc_traced=itc, IoUc_refit=irc))
    done = [p for p in per if p["matched"] and p["status"] == "refit"]
    away = [p for p in done if p["IoUc_refit"] < p["IoUc_traced"] - 0.005 or p["Hc_refit"] > p["Hc_traced"] + 0.05]
    toward = [p for p in done if p["IoUc_refit"] > p["IoUc_traced"] + 0.005 or p["Hc_refit"] < p["Hc_traced"] - 0.05]
    return dict(whole_iou=reg0.iou, flip_y=reg0.flip_y,
                blocks={int(b): dict(iou=r.iou, dx=r.dx, dy=r.dy) for b, r in regs.items()},
                matched=sum(p["matched"] for p in per), compared=len(done), away=len(away),
                toward=len(toward),
                d_iou_centred_mean=float(np.mean([p["IoUc_refit"] - p["IoUc_traced"] for p in done])) if done else None,
                d_h_centred_mean=float(np.mean([p["Hc_refit"] - p["Hc_traced"] for p in done])) if done else None,
                per=per)


# --------------------------------------------------------------- sheets
def sheets(name: str, d: dict, rows, tag: str, pro_map=None) -> list[Path]:
    from sheet import letter_sheet
    outs = []
    words = sorted({r.word for r in rows})
    for w in words:
        wr = [r for r in rows if r.word == w]
        outs.append(letter_sheet(d, ROOT / "testdata" / d["rel"], wr,
                                 SCRATCH / "sheets" / f"{tag}_{name}_w{w}.png", pro=pro_map,
                                 title=f"{name} word {w}: artwork / traced / refit"
                                       + (" / pro" if pro_map else "")))
    return outs


# ----------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    k = K_DEFAULT
    if "--k" in argv:
        k = float(argv[argv.index("--k") + 1])
    tag = argv[argv.index("--tag") + 1] if "--tag" in argv else f"k{k:g}"
    do_down = "--no-downstream" not in argv
    do_oc = "--no-oc" not in argv
    do_sheets = "--sheets" in argv
    names = [a for a in argv if not a.startswith("--") and a in LOGOS] or LOGOS
    report = {}
    for name in names:
        p = SCRATCH / f"{name}.pkl"
        if not p.exists():
            print(f"{name}: no input ({p}); run run.py first")
            continue
        d = pickle.load(open(p, "rb"))
        t0 = time.time()
        try:
            regions, rows = refit_logo(d, k)
        except Exception:                                    # noqa: BLE001
            print(f"{name}: refit CRASHED")
            traceback.print_exc()
            continue
        text_ids = [r["shape_id"] for r in d["regions"] if r["meta"].get("text_candidate")]
        before = polygon_wkb_hash({r["shape_id"]: r["polygon"] for r in d["regions"] if r["shape_id"] in text_ids})
        apply(regions, rows)
        after = polygon_wkb_hash({r.shape_id: r.polygon for r in regions if r.shape_id in text_ids})
        s = summarize(rows)
        entry = dict(name=name, held_out=name in HELD_OUT, src_px_mm=source_px_mm(d),
                     grid_px_mm=1.0 / float(d["px_per_mm"]), tol_mm=k * source_px_mm(d),
                     text_tagged=len(text_ids), grouped=len(rows),
                     wkb_before=before, wkb_after=after, byte_identical=(before == after),
                     summary=s, secs_fit=round(time.time() - t0, 1),
                     letters=[dict(shape_id=r.shape_id, char=r.char, word=r.word, status=r.fit.status,
                                   reason=r.fit.reason, prims_before=r.fit.before_n_prims,
                                   prims_after=r.fit.n_prims, lines=r.fit.n_line, arcs=r.fit.n_arc,
                                   passes=r.fit.n_pass, moved_max=r.fit.moved_max_mm,
                                   moved_p95=r.fit.moved_p95_mm, unexplained=r.fit.unexplained_share,
                                   cv_before=r.width_cv_before, cv_after=r.width_cv_after)
                              for r in rows])
        print(f"{name}: text {len(text_ids)} grouped {len(rows)} refit {s['refit']} pass {s['passed']} "
              f"refused {s['refused']} {s['reasons']} tol {entry['tol_mm']:.3f} grid {entry['grid_px_mm']:.3f} "
              f"byte-identical {entry['byte_identical']} ({entry['secs_fit']}s)", flush=True)
        pro_map = None
        if name in PRO:
            try:
                entry["pro"] = pro_compare(name, d, rows)
                pc = entry["pro"]
                print(f"  pro: whole iou {pc['whole_iou']:.3f}, {pc['matched']} matched, {pc['compared']} compared, "
                      f"{pc['away']} away / {pc['toward']} toward, d IoU(centred) {pc['d_iou_centred_mean']:+.4f}, "
                      f"d H(centred) {pc['d_h_centred_mean']:+.3f} mm", flush=True)
            except Exception:                                # noqa: BLE001
                print("  pro comparison CRASHED")
                traceback.print_exc()
        if do_down and rows:
            try:
                entry["downstream"] = downstream(d, name, rows, k)
                dd = entry["downstream"]
                if dd:
                    for arm in ("traced", "refit"):
                        a = dd[arm]
                        print(f"  {arm:6}: st {a['stitches']} trims {a['trims']} text-st {a['text_stitches']} "
                              f"wobble std {a['wobble_std']} p95 {a['wobble_p95']} satin std {a['satin_wobble_std']} "
                              f"bare {a['bare_pct'] if a['bare_pct'] is None else round(a['bare_pct'], 2)}% "
                              f"of {a['satin_art_mm2']:.0f} mm2 ({a['secs']}s)", flush=True)
            except Exception:                                # noqa: BLE001
                print("  downstream CRASHED")
                traceback.print_exc()
        if do_oc and rows:
            try:
                entry["outline_cut"] = outline_cut(rows)
                oc = entry["outline_cut"]
                if oc:
                    for arm in ("traced", "refit"):
                        a = oc[arm]
                        print(f"  outline-cut {arm:6}: clean {a['clean']}/{a['letters']} crashed {a['crashed']} "
                              f"over-long {a['over_long']:.1%} off-art {a['off_art']:.1%}", flush=True)
            except Exception:                                # noqa: BLE001
                print("  outline-cut CRASHED")
                traceback.print_exc()
        if do_sheets and rows:
            try:
                pm = None
                if name in PRO and entry.get("pro"):
                    import pro
                    letters = {r.shape_id: r.traced for r in rows}
                    pm, *_ = pro.pro_letters_for(PRO[name], letters, [r["polygon"] for r in d["regions"]], d["width"])
                for pth in sheets(name, d, rows, tag, pm):
                    print(f"  sheet {pth}")
            except Exception:                                # noqa: BLE001
                print("  sheets CRASHED")
                traceback.print_exc()
        report[name] = entry
    out = SCRATCH / f"batch_{tag}.json"
    json.dump(report, open(out, "w"), indent=1, default=str)
    print(f"\nwrote {out}\n")
    print(table(report))
    return 0


def table(report: dict) -> str:
    lines = ["| logo | src px | cap | letters | refit / pass / refused | byte-identical | prims before -> after | stem spread deg | width CV | pro d IoU | wobble std traced -> refit | bare % | outline-cut over-long |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, e in report.items():
        s = e["summary"]
        pr = e.get("pro") or {}
        dd = e.get("downstream") or {}
        oc = e.get("outline_cut") or {}

        def f(x, fmt="{:.2f}"):
            return "-" if x is None else fmt.format(x)
        lines.append("| {name}{ho} | {px:.3f} | {tol:.3f} | {n} | {r} / {p} / {x} | {bi} | {pb} -> {pa} | {sb} -> {sa} | {cb} -> {ca} | {pro} | {wt} -> {wr} | {bt} -> {br} | {ot} -> {orf} |".format(
            name=name, ho=" (held out)" if e["held_out"] else "", px=e["src_px_mm"], tol=e["tol_mm"],
            n=e["grouped"], r=s["refit"], p=s["passed"], x=s["refused"],
            bi="yes" if e["byte_identical"] else "NO",
            pb=f(s.get("prims_before"), "{:.1f}"), pa=f(s.get("prims_after"), "{:.1f}"),
            sb=f(s.get("stem_spread_before")), sa=f(s.get("stem_spread_after")),
            cb=f(s.get("width_cv_before"), "{:.3f}"), ca=f(s.get("width_cv_after"), "{:.3f}"),
            pro=f(pr.get("d_iou_centred_mean"), "{:+.4f}") + (f" ({pr.get('away')} away)" if pr else ""),
            wt=f((dd.get("traced") or {}).get("wobble_std"), "{:.4f}"), wr=f((dd.get("refit") or {}).get("wobble_std"), "{:.4f}"),
            bt=f((dd.get("traced") or {}).get("bare_pct")), br=f((dd.get("refit") or {}).get("bare_pct")),
            ot=f((oc.get("traced") or {}).get("over_long"), "{:.1%}"), orf=f((oc.get("refit") or {}).get("over_long"), "{:.1%}")))
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
