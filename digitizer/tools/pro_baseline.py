#!/usr/bin/env python
"""Today's main against the pro, on every paired job: the baseline the teams rank work by.

MEASUREMENT ONLY. Each paired job is digitized ONCE with the Studio's request at
the pro's width and garment (`tools.pro_pair.digitize`, today's defaults), and the
written DST is put beside the pro's file. Everything is read from the two machine
files through ONE reader, so ours and the pro's are counted the same way:

  stitches / trims / colour changes   `pro_pair.pro_counts` (pystitch).
  needle-up mm                        the straight gap the needle flies with the
                                      thread up: from the last stitch before any
                                      JUMP / TRIM / COLOR_CHANGE / STOP to the
                                      first stitch after it, summed (`needle_up`).
                                      `hops` is how many such gaps there are.
  sttype kappa, direction kappa       `pro_parity.scorecard.score_design` over the
                                      shared solid area, both sides decoded by
                                      `prep_all.decode` from their DSTs.
                                      CHANCE-CORRECTED ONLY (ROADMAP gate 4): the
                                      raw agreement is never printed as a figure;
                                      the chance floor rides beside the kappa so a
                                      degenerate cell (`d`) can be seen.
  word cc                             `tools.word_legibility`'s chance-corrected
                                      per-word reading, on the four jobs whose words
                                      are pinned (`testdata/word_legibility_words.json`),
                                      native size only (`--no-ladder`). A word not
                                      located is n/loc and left out, never scored 0.

    python -m tools.pro_baseline digitize --runs DIR [--only SLUG ...]   # ours.dst + design.json per job
    python -m tools.pro_baseline measure --runs DIR [--only SLUG ...] [--no-words]
    python -m tools.pro_baseline table --runs DIR                         # markdown

`--runs DIR` holds `DIR/<slug>/ours.dst` and `DIR/<slug>/design.json`; `measure`
writes `DIR/baseline.json` and `DIR/<slug>/score/`. The pro files and some art are
gitignored third-party files: `kent:` paths resolve under `scratch_kent/` (or
`EMB_SCRATCH_KENT`), `bridge:` paths under the `Embroidery/Digitized Designs/Bridge
Logo/` folder above this checkout (or `EMB_BRIDGE_PRO`). Nothing here writes a pro
render; the doc it feeds carries numbers only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

#: slug -> (garment, pro width mm, art, pro DST, pro PES or None, word_legibility job or None)
JOBS: dict[str, tuple] = {
    "bridge_hat": ("hat_front", 63.3, "testdata:photo/logo_bridge_bar.jpg",
                   "bridge:BRIDGE LOGO HAT.DST", "bridge:BRIDGE LOGO HAT.PES", None),
    "bridge_lc": ("left_chest", 76.6, "testdata:photo/logo_bridge_bar.jpg",
                  "bridge:BRIDGE LOGO LC.DST", "bridge:BRIDGE LOGO LC.PES", None),
    "becker_hat_large": ("hat_front", 101.9, "testdata:becker_marine_logo.png",
                         "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Large/beckers logo hat.DST",
                         "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Large/beckers logo hat.PES", "becker"),
    "becker_lc_large": ("left_chest", 95.7, "testdata:becker_marine_logo.png",
                        "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Large/beckers logolc.DST",
                        "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Large/beckers logolc.PES", None),
    "becker_hat_small": ("hat_front", 76.5, "testdata:becker_marine_logo.png",
                         "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.DST",
                         "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.PES", None),
    "becker_chest_small": ("left_chest", 76.5, "testdata:becker_marine_logo.png",
                           "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.DST",
                           "kent:Embroidery Files/Becker Marine/Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.PES", None),
    "becker_beanie": ("beanie", 79.8, "testdata:becker_marine_logo.png",
                      "kent:Embroidery Files/To a T-Becker Beanies/beckers beanie.DST",
                      "kent:Embroidery Files/To a T-Becker Beanies/beckers logo hat 2 A a.PES", None),
    "gaulke_roofing_hat": ("hat_front", 114.2, "testdata:photo/logo_gaulke_roofing.png",
                           "kent:Embroidery Files/Gaulke Roofing/c golke logo hat.DST", None, None),
    "gaulke_roofing_lc": ("left_chest", 95.2, "testdata:photo/logo_gaulke_roofing.png",
                          "kent:Embroidery Files/Gaulke Roofing/c golke logo LC.DST", None, None),
    "gaulke_roofing_beanie": ("beanie", 93.8, "testdata:photo/logo_gaulke_roofing.png",
                              "kent:Embroidery Files/Gaulke Roofing/c golke logo HAT BEANI.DST", None, None),
    "hotel_fremont_hat": ("hat_front", 92.6, "testdata:photo/logo_hotel_fremont.webp",
                          "kent:Embroidery Files/Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.DST",
                          "kent:Embroidery Files/Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES", "fremont"),
    "hotel_fremont_patch": ("patch", 92.5, "testdata:photo/logo_hotel_fremont.webp",
                            "kent:Embroidery Files/Hotel Fremont/Hotel Patch/HOTEL FREMONT .DST",
                            "kent:Embroidery Files/Hotel Fremont/Hotel Patch/HOTEL FREMONT .PES", None),
    "mfab_hat": ("hat_front", 104.9, "testdata:art/logo_mfab_hat.png",
                 "kent:Embroidery Files/MFAB/Mfab Hat & Polo/mf4b logo hat.DST",
                 "kent:Embroidery Files/MFAB/Mfab Hat & Polo/mf4b logo hat.PES", "mfab"),
    "mfab_lc": ("left_chest", 96.7, "testdata:art/logo_mfab_lc.png",
                "kent:Embroidery Files/MFAB/Mfab Hat & Polo/mf4b logo lc.DST",
                "kent:Embroidery Files/MFAB/Mfab Hat & Polo/mf4b logo lc.PES", None),
    "precision_drone": ("hat_front", 62.6, "testdata:photo/logo_drone_thermal_badge.png",
                        "kent:Embroidery Files/Precision Drone/PRECISION DRON HAT 2.DST",
                        "kent:Embroidery Files/Precision Drone/PRECISION DRON HAT 2.PES", None),
    "proseal_hat": ("hat_front", 85.9, "kent:Embroidery Files/Proseal/PROSeal Logo.jpg",
                    "kent:Embroidery Files/Proseal/PROSEALHAT.DST", None, "proseal"),
    "proseal_beanie": ("beanie", 75.0, "kent:Embroidery Files/Proseal/PROSeal Logo.jpg",
                       "kent:Embroidery Files/Proseal/PROSEALHAT BEANI.DST", None, None),
    "tires_hat_3d": ("hat_front", 114.3, "testdata:logo_script_tires.png",
                     "kent:Embroidery Files/TIRES/fwdyourdigitizingorderisreadytireslogo (1)/TIRES HAT 3D.DST",
                     "kent:Embroidery Files/TIRES/fwdyourdigitizingorderisreadytireslogo (1)/TIRES HAT 3D.PES", None),
    "goldentee_hat": ("hat_front", 74.9, "testdata:photo/logo_golden_tee.jpg",
                      "kent:Embroidery Files/ Golden Tee/GOLF HAT.DST", "kent:Embroidery Files/ Golden Tee/GOLF HAT.PES", None),
    "toat_machine_hat": ("hat_front", 89.5, "testdata:art/logo_toat_machine.png",
                         "kent:Embroidery Files/To a T Machine/Machine HAT.DST", None, None),
    "toat_machine_beanie": ("beanie", 81.0, "testdata:art/logo_toat_machine.png",
                            "kent:Embroidery Files/To a T Machine/Machine beanie E (1).DST",
                            "kent:Embroidery Files/To a T Machine/Machine beanie E-1 (1).PES", None),
    "toat_beanie": ("beanie", 82.3, "testdata:art/logo_toat_beanie.png",
                    "kent:Embroidery Files/To a T-Becker Beanies/To a T Beanie.DST",
                    "kent:Embroidery Files/To a T-Becker Beanies/Machine beanie.PES", None),
}

#: near-duplicates: jobs that are one artwork, so a ranking counts the artwork once
ARTWORK = {"bridge": ("bridge_hat", "bridge_lc"),
           "becker": ("becker_hat_large", "becker_lc_large", "becker_hat_small", "becker_chest_small", "becker_beanie"),
           "gaulke": ("gaulke_roofing_hat", "gaulke_roofing_lc", "gaulke_roofing_beanie"),
           "fremont": ("hotel_fremont_hat", "hotel_fremont_patch"),
           "mfab": ("mfab_hat", "mfab_lc"),
           "drone": ("precision_drone",),
           "proseal": ("proseal_hat", "proseal_beanie"),
           "tires": ("tires_hat_3d",),
           "goldentee": ("goldentee_hat",),
           "toat": ("toat_machine_hat", "toat_machine_beanie", "toat_beanie")}


def resolve(spec: str) -> Path:
    kind, _sep, rel = spec.partition(":")
    if kind == "bridge":
        env = os.environ.get("EMB_BRIDGE_PRO")
        roots = [Path(env)] if env else [p / "Embroidery" / "Digitized Designs" / "Bridge Logo"
                                         for p in DIGITIZER.parents]
        for r in roots:
            if (r / rel).exists():
                return r / rel
        raise SystemExit(f"{rel!r} not found: set EMB_BRIDGE_PRO to the folder holding the Bridge pro files")
    from tools.word_legibility import resolve as wl_resolve
    return wl_resolve(spec)


def needle_up(path: Path) -> dict:
    """Needle-up travel in a machine file: the straight gap from the last stitch before
    a lift (JUMP / TRIM / COLOR_CHANGE / STOP) to the first stitch after it, summed."""
    import pystitch
    pat = pystitch.read(str(path))
    m = pystitch.COMMAND_MASK
    mm, hops, last, lifted = 0.0, 0, None, False
    for x, y, c in pat.stitches:
        c &= m
        if c == pystitch.STITCH:
            p = (x / 10.0, y / 10.0)
            if lifted and last is not None:
                mm += math.dist(last, p)
                hops += 1
            last, lifted = p, False
        elif c in (pystitch.JUMP, pystitch.TRIM, pystitch.COLOR_CHANGE, pystitch.STOP):
            lifted = True
        elif c == pystitch.END:
            break
    return {"needle_up_mm": round(mm, 1), "hops": hops}


def write_side(out: Path, side: str, dst: Path) -> None:
    """One side's stitch CSV and block file, written from its DST the way
    `prep_all.main` writes the pro's (so ours and the pro's share one decoder)."""
    from tools.pro_parity import prep_all
    blocks, breaks, threads, _bounds, _j, _t = prep_all.decode(dst)
    with open(out / f"{side}_stitches.csv", "w") as f:
        f.write("block,run,trim,jump,x_mm,y_mm\n")
        for i, runs in enumerate(blocks):
            for ri, (r, kind) in enumerate(zip(runs, breaks[i])):
                t = 1 if kind in ("trim", "color") else 0
                j = 1 if kind == "jump" else 0
                for k, (x, y) in enumerate(r):
                    f.write(f"{i},{ri},{t if k == 0 else 0},{j if k == 0 else 0},{x:.2f},{y:.2f}\n")
    (out / f"{side}_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(threads[i])} for i in range(len(blocks))]), encoding="utf-8")


def kappas(ours: Path, pro: Path, work: Path) -> dict:
    from tools.lane_census import sttype_kappa
    from tools.pro_parity import scorecard
    work.mkdir(parents=True, exist_ok=True)
    write_side(work, "pro", pro)
    write_side(work, "ours", ours)
    k = sttype_kappa(scorecard.score_design(work))
    return {"sttype_kappa": k["kappa"], "sttype_chance": k["chance"], "direction_kappa": k["direction_kappa"],
            "solid_iou": k["solid_iou"]}


def digitize(runs: Path, slugs: list[str]) -> None:
    from digitizer_core.export import write_dst
    from tools import pro_pair
    for s in slugs:
        garment, width, art, *_ = JOBS[s]
        d = pro_pair.digitize(resolve(art), width, garment)
        out = runs / s
        out.mkdir(parents=True, exist_ok=True)
        write_dst(d.plan, out / "ours.dst")
        (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
        print(s, d.plan.stats.stitch_count, d.plan.stats.trims, flush=True)


def words(runs: Path, slugs: list[str]) -> dict:
    """word_legibility's per-job figure for ours and the pro's, native size only."""
    from tools import word_legibility as wl
    jobs = {JOBS[s][5]: s for s in slugs if JOBS[s][5]}
    if not jobs:
        return {}
    cache = runs / "_words"
    cache.mkdir(parents=True, exist_ok=True)
    for job, s in jobs.items():
        design = json.loads((runs / s / "design.json").read_text(encoding="utf-8"))
        (cache / f"ours_{job}.json").write_text(json.dumps(
            {"job": job, "width_mm": JOBS[s][1], "garment": JOBS[s][0], "design": design}), encoding="utf-8")
    out = cache / "read.json"
    wl.main(["--read", ",".join(jobs), "--cache", str(cache), "--json", str(out), "--no-ladder"])
    return {"by_job": jobs, "read": json.loads(out.read_text(encoding="utf-8")) if out.exists() else None}


def measure(runs: Path, slugs: list[str], with_words: bool) -> dict:
    from tools import pro_pair
    path = runs / "baseline.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"jobs": {}}
    for s in slugs:
        garment, width, _art, pro_dst, _pes, _w = JOBS[s]
        ours, pro = runs / s / "ours.dst", resolve(pro_dst)
        row = {"garment": garment, "width_mm": width}
        for side, f in (("ours", ours), ("pro", pro)):
            c = pro_pair.pro_counts(f)
            row[side] = {"stitches": c["stitches"], "trims": c["trims"], "colour_changes": c["colour_changes"],
                         **needle_up(f)}
        try:
            row["kappa"] = kappas(ours, pro, runs / s / "score" / s)
        except Exception as e:                                   # noqa: BLE001 -- a row, not a crash
            row["kappa"] = {"error": f"{type(e).__name__}: {e}"[:300]}
        res["jobs"][s] = row
        print(s, json.dumps(row), flush=True)
    if with_words:
        res["words"] = words(runs, slugs)
    path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def _pct(o, p):
    return None if not p else round(100.0 * (o - p) / p)


def word_figures(res: dict) -> dict:
    """slug -> {ours, pro, words}: word_legibility's letter-weighted cc at native size
    over the words located in BOTH files (`<file>/native/both`)."""
    w = res.get("words") or {}
    by_job = w.get("by_job") or {}
    out = {}
    for j in w.get("read") or []:
        s = by_job.get(j.get("job"))
        if s is None:
            continue
        f = j.get("figures", {})
        o, p = f.get("ours/native/both", {}), f.get("pro/native/both", {})
        out[s] = {"ours": o.get("cc"), "pro": p.get("cc"), "words": o.get("words"), "ocr": j.get("ocr")}
    return out


def table(runs: Path) -> str:
    res = json.loads((runs / "baseline.json").read_text(encoding="utf-8"))
    rows = res["jobs"]
    wf = word_figures(res)
    L = ["| job | stitches ours / pro (gap) | trims ours / pro (gap) | colour changes ours / pro | "
         "needle-up mm ours / pro (gap) | sttype kappa (chance) | direction kappa | word cc ours / pro |",
         "|---|---|---|---|---|---|---|---|"]
    for s in JOBS:
        r = rows.get(s)
        if not r:
            continue
        o, p, k = r["ours"], r["pro"], r.get("kappa", {})
        st = f"{o['stitches']:,} / {p['stitches']:,} ({_pct(o['stitches'], p['stitches']):+d}%)"
        tr = f"{o['trims']} / {p['trims']} ({o['trims'] - p['trims']:+d})"
        cc = f"{o['colour_changes']} / {p['colour_changes']}"
        nu = (f"{o['needle_up_mm']:,.0f} / {p['needle_up_mm']:,.0f} "
              f"({_pct(o['needle_up_mm'], p['needle_up_mm']):+d}%)" if p["needle_up_mm"] else "-")
        if "error" in k:
            kk, kd = "err", "err"
        else:
            deg = "d" if (k.get("sttype_chance") or 0) >= 0.999 else ""
            kk = f"{k['sttype_kappa']:.2f}{deg} ({k['sttype_chance']:.2f})"
            kd = f"{k['direction_kappa']:.2f}"
        w = wf.get(s)
        wc = "-" if not w else (f"{w['ours']:.2f} / {w['pro']:.2f} (n {w['words']})"
                                if w.get("ours") is not None and w.get("pro") is not None else "n/loc")
        L.append(f"| {s} | {st} | {tr} | {cc} | {nu} | {kk} | {kd} | {wc} |")
    return "\n".join(L)


def per_job(runs: Path) -> str:
    """One small table per job: each count ours / pro / gap, then the kappas and word cc."""
    res = json.loads((runs / "baseline.json").read_text(encoding="utf-8"))
    wf = word_figures(res)
    out = []
    for s in JOBS:
        r = res["jobs"].get(s)
        if not r:
            continue
        o, p, k = r["ours"], r["pro"], r.get("kappa", {})
        L = [f"#### {s} ({r['garment']}, {r['width_mm']} mm)", "",
             "| | ours | pro | gap |", "|---|---|---|---|"]
        for key, label in (("stitches", "stitches"), ("trims", "trims"), ("colour_changes", "colour changes"),
                           ("needle_up_mm", "needle-up mm"), ("hops", "needle-up hops")):
            a, b = o[key], p[key]
            gap = f"{a - b:+,.0f}" + (f" ({_pct(a, b):+d}%)" if b else "")
            L.append(f"| {label} | {a:,.0f} | {b:,.0f} | {gap} |")
        if "error" not in k:
            L.append(f"| sttype kappa (chance floor) | {k['sttype_kappa']:.2f} ({k['sttype_chance']:.2f}) | | |")
            L.append(f"| direction kappa | {k['direction_kappa']:.2f} | | |")
        w = wf.get(s)
        if w and w.get("ours") is not None:
            L.append(f"| word cc, native ({w['words']} words) | {w['ours']:.2f} | {w['pro']:.2f} | "
                     f"{w['ours'] - w['pro']:+.2f} |")
        out.append("\n".join(L))
    return "\n\n".join(out)


def worst(res: dict, key: str, n: int = 5) -> list[tuple]:
    """The n artworks with the largest excess over the pro on `key` (ours - pro, as a
    share of the pro), each artwork by its worst job (near-duplicates counted once)."""
    rows = res["jobs"]
    best = []
    for art, slugs in ARTWORK.items():
        cand = [(s, rows[s]["ours"][key], rows[s]["pro"][key]) for s in slugs if s in rows]
        if not cand:
            continue
        s, o, p = max(cand, key=lambda t: (t[1] - t[2]) / max(1, t[2]))
        best.append((art, s, o, p, o - p, _pct(o, p)))
    return sorted(best, key=lambda t: -(t[4] / max(1, t[3])))[:n]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("digitize", "measure", "table"))
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--no-words", action="store_true")
    a = ap.parse_args(argv)
    slugs = a.only or list(JOBS)
    if a.cmd == "digitize":
        digitize(a.runs, slugs)
    elif a.cmd == "measure":
        measure(a.runs, slugs, not a.no_words)
    else:
        print(table(a.runs))
        res = json.loads((a.runs / "baseline.json").read_text(encoding="utf-8"))
        for key in ("trims", "stitches"):
            print(f"\nworst by {key} (artwork, job, ours, pro, gap, %):")
            for t in worst(res, key):
                print("  ", t)
        print("\n" + per_job(a.runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
