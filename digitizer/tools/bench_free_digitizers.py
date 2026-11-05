#!/usr/bin/env python
"""A third-party auto-digitizer's DST against the pro's, beside ours (2026-11-04 survey, Tier 1).

`docs/free-digitizer-survey-2026-11-04.md` named three free engines (Nuizu,
heatstitch, openstitch) and asked what they do on OUR artwork at the pro's size.
This tool reads their machine files through the SAME instruments the nightly
tripwire uses (`tools.tripwire`, `tools.pro_baseline`): one reader (pystitch)
for ours, the pro's and the competitor's DST, and the same seven figures --
stitches, trims (cuts), hops, needle-up mm, stitch-type kappa, direction kappa,
word cc -- CHANCE-CORRECTED ONLY (ROADMAP gate 4; no raw agreement is printed).
Each figure is competitor-vs-pro beside ours-vs-pro. Competitor extras: raw
stitch count, trims, colour changes, bounding box in mm (a tool that silently
sews at its own size is read before it is quoted).

    python -m tools.bench_free_digitizers prep    [--bench DIR] [--only SLUG ...]
    python -m tools.bench_free_digitizers ours    [--bench DIR] [--only SLUG ...]
    python -m tools.bench_free_digitizers measure --engine NAME [--bench DIR] [--only SLUG ...] [--date D] [--no-words] [--no-sheets]
    python -m tools.bench_free_digitizers table   --engine NAME [--bench DIR]
    python -m tools.bench_free_digitizers scoreboard --engines A B C [--write OUT.md]   # numbers only

Layout (everything under `--bench`, default `<repo>/scratch_bench`, GITIGNORED:
the competitor files and any render drawn from them are third-party and must
never be committed or land under docs/):

    _art/<slug>.png                 the art cut to its ink box (what the tools are fed)
    jobs.json                       per slug: garment, pro width, art size, longest side mm
    _ours/figures.json              ours + the pro's, digitized once and shared by every engine
    <engine>/<slug>.dst             the competitor's file at the pro's size (you put these here)
    <engine>/renders/<slug>.png     art | ours | competitor | pro at 20 px/mm
    report-<engine>-<date>.md/.json

The population is `tripwire.committed_jobs()` (18 pairs whose art and pro DST
are committed). A job with no competitor file is listed as missing, not scored.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
REPO = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

DEFAULT_BENCH = REPO / "scratch_bench"
PPM = 20.0                      # px/mm of every render sheet
FIGS = ("stitches", "trims", "hops", "needle_up_mm", "sttype_kappa", "direction_kappa", "word_cc")


# ------------------------------------------------------------------ jobs and art
def job_slugs(only=None) -> list[str]:
    from tools import tripwire
    slugs = tripwire.committed_jobs()
    if only:
        bad = [s for s in only if s not in slugs]
        if bad:
            raise SystemExit(f"not committed pairs: {bad}; try `python -m tools.tripwire jobs`")
        slugs = [s for s in slugs if s in only]
    return slugs


def art_path(slug: str) -> Path:
    from tools import pro_baseline as pb
    return pb.resolve(pb.JOBS[slug][2])


def longest_side_mm(width_mm: float, shape: tuple) -> float:
    """The art's INK box is `width_mm` wide; the longest side of that box in mm."""
    h, w = shape[:2]
    return round(max(w, h) / w * width_mm, 2)


def _panel_crop(img):
    """The largest bright (> 200 grey) connected panel, for art shot on a black screen
    (Gaulke's phone screenshot: `_art_ink` reads the black bars as ink)."""
    import cv2
    import numpy as np
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    n, _lab, st, _c = cv2.connectedComponentsWithStats((g > 200).astype(np.uint8))
    if n < 2:
        return img
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = st[i, :4]
    return img[y:y + h, x:x + w]


def ink_crop(slug: str, pro_aspect: float | None = None):
    """The art cut to its ink box, with the panel fallback when the box disagrees with the
    pro's own width:height by more than 25% (the pro is the truth about what was sewn)."""
    import cv2
    from tools.pro_pair import _art_ink
    ink = _art_ink(art_path(slug))
    if pro_aspect and abs(ink.shape[1] / ink.shape[0] / pro_aspect - 1) > 0.25:
        panel = _art_ink_of(_panel_crop(_composite(art_path(slug))))
        if abs(panel.shape[1] / panel.shape[0] / pro_aspect - 1) < abs(ink.shape[1] / ink.shape[0] / pro_aspect - 1):
            return panel
    return ink


def _composite(path):
    import cv2
    import numpy as np
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im.ndim == 2:
        return cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    if im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        return (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im


def _art_ink_of(im):
    import cv2
    import numpy as np
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(g < 200)
    return im[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(xs) else im


def pro_aspect_of(slug: str) -> float:
    from tools import pro_baseline as pb
    from tools import pro_pair
    c = pro_pair.pro_counts(pb.resolve(pb.JOBS[slug][3]))
    return c["width_mm"] / c["height_mm"]


def prep(bench: Path, slugs: list[str]) -> dict:
    """Write the ink-cropped art and `jobs.json`; return the table."""
    import cv2
    from tools import pro_baseline as pb
    from tools import tripwire
    tripwire.materialise(bench / "_ours" / "_kent", slugs)
    (bench / "_art").mkdir(parents=True, exist_ok=True)
    jobs = {}
    for s in slugs:
        garment, width, *_ = pb.JOBS[s]
        asp = pro_aspect_of(s)
        ink = ink_crop(s, asp)
        cv2.imwrite(str(bench / "_art" / f"{s}.png"), ink)
        jobs[s] = {"garment": garment, "width_mm": width, "art_px": [int(ink.shape[1]), int(ink.shape[0])],
                   "art_aspect": round(ink.shape[1] / ink.shape[0], 3), "pro_aspect": round(asp, 3),
                   "longest_mm": longest_side_mm(width, ink.shape)}
    (bench / "jobs.json").write_text(json.dumps(jobs, indent=1), encoding="utf-8")
    return jobs


# ------------------------------------------------------------------ ours + pro (shared)
def ours_figures(bench: Path, slugs: list[str], with_words: bool = True) -> dict:
    """Ours and the pro's, digitized ONCE (`tripwire.measure`) and cached; every engine reads the cache."""
    path = bench / "_ours" / "figures.json"
    have = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if have and all(s in have.get("values", {}) for s in slugs):
        return have
    from tools import tripwire
    out = tripwire.measure(bench / "_ours" / "runs", slugs, with_words, bench / "_ours" / "_kent")
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


# ------------------------------------------------------------------ the competitor side
def competitor_words(runs: Path, slug: str, dst: Path):
    """word_legibility's reading of the competitor's file in place of 'ours': its own frame
    (width_mm None -> registered like the pro's, never at the pro's width)."""
    from tools import pro_baseline as pb
    from tools import word_legibility as wl
    from tools.glyph_legibility import design_from_pes
    job = pb.JOBS[slug][5]
    if not job:
        return None
    cache = runs / "_words"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"ours_{job}.json").write_text(json.dumps(
        {"job": job, "width_mm": None, "garment": pb.JOBS[slug][0], "design": design_from_pes(dst)}), encoding="utf-8")
    out = cache / f"read_{job}.json"
    wl.main(["--read", job, "--cache", str(cache), "--json", str(out), "--no-ladder"])
    return {"by_job": {job: slug}, "read": json.loads(out.read_text(encoding="utf-8")) if out.exists() else None}


def competitor_figures(dst: Path, pro: Path, work: Path, slug: str = "job", words: dict | None = None) -> dict:
    """The seven figures for `dst` against `pro`, plus the competitor's own counts and box.
    `work` is a scratch folder (the kappa CSVs go there). Pure reading: nothing is digitized."""
    from tools import pro_baseline as pb
    from tools import pro_pair, tripwire
    c = pro_pair.pro_counts(dst)
    row = {"stitches": c["stitches"], "trims": c["trims"], "colour_changes": c["colour_changes"],
           **pb.needle_up(dst)}
    p = pro_pair.pro_counts(pro)
    prow = {"stitches": p["stitches"], "trims": p["trims"], "colour_changes": p["colour_changes"],
            **pb.needle_up(pro)}
    try:
        k = pb.kappas(dst, pro, work)
    except Exception as e:                                   # noqa: BLE001 -- a row, not a crash
        k = {"error": f"{type(e).__name__}: {e}"[:300]}
    res = {"jobs": {slug: {"ours": row, "pro": prow, "kappa": k}}}
    if words:
        res["words"] = words
    fig = tripwire.figures_from_baseline(res)
    return {"values": fig["values"][slug], "pro": fig["pro"][slug], "chance": fig["chance"].get(slug),
            "words": fig["words"].get(slug),
            "own": {"stitches": c["stitches"], "trims": c["trims"], "colour_changes": c["colour_changes"],
                    "thread_colours": c["thread_colours"], "width_mm": c["width_mm"], "height_mm": c["height_mm"]}}


# ------------------------------------------------------------------ the tool's own claims
def load_manifest(src: Path) -> dict:
    """`<engine>/manifest.json`, if the engine's operator wrote one: slug -> what the tool
    SAID it produced. A missing or unreadable file is {} (the measurement never needs it)."""
    p = src / "manifest.json"
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    m = m.get("jobs", m) if isinstance(m, dict) else {}
    return {k: v for k, v in m.items() if isinstance(v, dict)}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def manifest_check(claim: dict, own: dict) -> dict:
    """Stated stitch count / trims / colour changes beside what OUR reader counts in the DST.
    Keys are matched loosely (`stitch_count`, `stitches`, ...); an absent claim is skipped."""
    out = {}
    for label, keys, read in (("stitches", ("stitch_count", "stitches"), own["stitches"]),
                              ("trims", ("trims",), own["trims"]),
                              ("colour_changes", ("colour_changes", "color_changes", "colours", "colors"), own["colour_changes"])):
        for k in keys:
            v = _num(claim.get(k))
            if v is not None:
                out[label] = {"stated": v, "read": read, "diff": round(read - v, 1)}
                break
    return out


# ------------------------------------------------------------------ sheets
def render_sheet(slug: str, ours_dst: Path, ours_design: dict | None, comp_dst: Path, pro_dst: Path,
                 out: Path, label: str, counts: dict) -> None:
    """art | ours | competitor | pro at PPM px/mm. Never written under docs/."""
    import cv2
    from digitizer_core import stitchviz
    from tools import pro_baseline as pb
    from tools.pro_pair import _hstack, _label, _scaled
    from tools.pro_parity import pairframe
    width = pb.JOBS[slug][1]
    ours = ours_design or pairframe.design_for(ours_dst, None, None, slug)
    imgs = [_label(_scaled(ink_crop(slug, pro_aspect_of(slug)), width, PPM, cv2.INTER_AREA), f"art, {width} mm wide")]
    comp = pairframe.design_for(comp_dst, None, None, comp_dst.stem)
    pro = pairframe.design_for(pro_dst, None, None, slug)
    ours_c = counts["ours"]
    imgs += [_label(stitchviz.render_design(ours, px_per_mm=PPM), f"ours: {ours_c['stitches']} st, {ours_c['trims']} trims"),
             _label(stitchviz.render_design(comp, px_per_mm=PPM),
                    f"{label}: {counts['comp']['stitches']} st, {counts['comp']['trims']} trims, "
                    f"{counts['comp']['width_mm']}x{counts['comp']['height_mm']} mm"),
             _label(stitchviz.render_design(pro, px_per_mm=PPM), f"pro: {counts['pro']['stitches']} st, {counts['pro']['trims']} trims")]
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), _hstack(imgs))


# ------------------------------------------------------------------ the engine run
def measure(bench: Path, engine: str, slugs: list[str], date: str, with_words=True, sheets=True,
            out_dir: Path | None = None) -> dict:
    from tools import pro_baseline as pb
    from tools import tripwire
    src = bench / engine                 # the competitor's files: READ ONLY
    root = (out_dir or bench) / engine   # runs, renders, reports are written here
    out_dir = out_dir or bench
    manifest = load_manifest(src)
    ours = ours_figures(bench, slugs, with_words)
    kent = tripwire.materialise(bench / "_ours" / "_kent", slugs)
    print(f"pro files: {kent}", flush=True)
    jobs = json.loads((bench / "jobs.json").read_text(encoding="utf-8")) if (bench / "jobs.json").exists() else prep(bench, slugs)
    rows, missing = {}, []
    for s in slugs:
        dst = src / f"{s}.dst"
        if not dst.exists():
            missing.append(s)
            continue
        pro_dst = pb.resolve(pb.JOBS[s][3])
        work = root / "runs" / s
        work.mkdir(parents=True, exist_ok=True)
        t = time.time()
        words = competitor_words(root / "runs", s, dst) if with_words else None
        r = competitor_figures(dst, pro_dst, work / "score", s, words)
        r["ours"] = {k: v for k, v in ours["values"][s].items()}
        r["pro"] = ours["pro"][s]
        r["pro_size"] = {"width_mm": pb.JOBS[s][1], "garment": pb.JOBS[s][0]}
        r["asked_longest_mm"] = jobs[s]["longest_mm"]
        pc = r["own"]
        r["size_ratio"] = round(pc["width_mm"] / pb.JOBS[s][1], 3)
        if s in manifest:
            r["manifest"] = manifest[s]
            r["manifest_check"] = manifest_check(manifest[s], pc)
        rows[s] = r
        if sheets:
            oc = {"stitches": ours["values"][s]["stitches"], "trims": ours["values"][s]["trims"]}
            pcounts = {"stitches": ours["pro"][s]["stitches"], "trims": ours["pro"][s]["trims"]}
            try:
                dj = bench / "_ours" / "runs" / s / "design.json"
                od = json.loads(dj.read_text(encoding="utf-8")) if dj.exists() else None
                render_sheet(s, bench / "_ours" / "runs" / s / "ours.dst", od, dst, pro_dst,
                             root / "renders" / f"{s}.png", engine,
                             {"ours": oc, "comp": pc, "pro": pcounts})
            except Exception as e:                           # noqa: BLE001 -- the numbers stand without the picture
                r["sheet_error"] = f"{type(e).__name__}: {e}"[:300]
        print(f"  {s}: {pc['stitches']} st, {pc['width_mm']}x{pc['height_mm']} mm ({round(time.time() - t, 1)} s)", flush=True)
    out = {"engine": engine, "date": date, "jobs": rows, "missing": missing,
           "env": tripwire.environment()}
    (out_dir / f"report-{engine}-{date}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (out_dir / f"report-{engine}-{date}.md").write_text(table(out), encoding="utf-8")
    return out


# ------------------------------------------------------------------ the table
def _f(fig, v, chance=None):
    from tools.tripwire import _fmt
    return _fmt(fig, v, chance)


def table(rep: dict) -> str:
    """Markdown: per job, ours-vs-pro beside competitor-vs-pro. Kappas and cc are the
    competitor's/ours' reading AGAINST the pro; count figures sit beside the pro's own."""
    rows = rep["jobs"]
    L = [f"# {rep['engine']} against the pro and ours ({rep['date']})", "",
         f"{len(rows)} jobs scored, {len(rep['missing'])} with no competitor file"
         + (f" ({', '.join(rep['missing'])})" if rep["missing"] else "") + ".", "",
         "Counts: ours / competitor / pro. Kappas and word cc: ours-vs-pro / competitor-vs-pro "
         "(stitch-type kappa carries its chance floor; chance-corrected only, ROADMAP gate 4).", "",
         "| job | competitor size mm (vs pro width) | stitches | trims | hops | needle-up mm | colour chg | "
         "sttype kappa | direction kappa | word cc |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for s, r in rows.items():
        o, c, p, own = r["ours"], r["values"], r["pro"], r["own"]
        k_o = _f("sttype_kappa", o.get("sttype_kappa"))
        k_c = _f("sttype_kappa", c.get("sttype_kappa"), r.get("chance"))
        size = f"{own['width_mm']}x{own['height_mm']} ({r['size_ratio']:.2f}x)"
        L.append(
            f"| {s} | {size} | {_f('stitches', o['stitches'])} / {_f('stitches', c['stitches'])} / {_f('stitches', p['stitches'])} "
            f"| {o['trims']} / {c['trims']} / {p['trims']} | {o['hops']} / {c['hops']} / {p['hops']} "
            f"| {_f('needle_up_mm', o['needle_up_mm'])} / {_f('needle_up_mm', c['needle_up_mm'])} / {_f('needle_up_mm', p['needle_up_mm'])} "
            f"| {own['colour_changes']} "
            f"| {k_o} / {k_c} | {_f('direction_kappa', o.get('direction_kappa'))} / {_f('direction_kappa', c.get('direction_kappa'))} "
            f"| {_f('word_cc', o.get('word_cc'))} / {_f('word_cc', c.get('word_cc'))} |")
    sm = summary(rep)
    if sm:
        L += ["", "Medians over the scored jobs: " + "; ".join(f"{k} {v}" for k, v in sm.items()) + "."]
    chk = [(s, r["manifest_check"]) for s, r in rows.items() if r.get("manifest_check")]
    if chk:
        L += ["", "The tool's own production sheet against what our reader counts in its DST "
                  "(stated -> read):", ""]
        for s, c in chk:
            L.append(f"- {s}: " + ", ".join(f"{k} {v['stated']:g} -> {v['read']}" for k, v in c.items()))
    return "\n".join(L) + "\n"


def _reports(folder: Path, engine: str) -> list[Path]:
    """`report-<engine>-<date>.json`, oldest first. An exact match: `report-nuizu-*` would
    also take `report-nuizu-satin-auto-<date>.json` (a different engine's arm)."""
    import re
    pat = re.compile(rf"report-{re.escape(engine)}-\d{{4}}-\d{{2}}-\d{{2}}\.json")
    return sorted(p for p in folder.glob("report-*.json") if pat.fullmatch(p.name))


def _med(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def summary(rep: dict) -> dict:
    """Medians over the scored jobs: competitor/pro ratios for the counts, the kappas of
    ours and the competitor against the pro, and how many jobs the competitor's
    stitch-type kappa is at or above ours (chance-corrected figures only)."""
    rows = list(rep["jobs"].values())
    if not rows:
        return {}

    def ratio(k):
        return _med([r["values"][k] / r["pro"][k] for r in rows if r["pro"].get(k)])
    out = {"stitches vs pro (x)": ratio("stitches"), "needle-up mm vs pro (x)": ratio("needle_up_mm"),
           "trims vs pro (delta)": _med([r["values"]["trims"] - r["pro"]["trims"] for r in rows]),
           "hops vs pro (delta)": _med([r["values"]["hops"] - r["pro"]["hops"] for r in rows]),
           "sttype kappa ours": _med([r["ours"].get("sttype_kappa") for r in rows]),
           "sttype kappa competitor": _med([r["values"].get("sttype_kappa") for r in rows]),
           "direction kappa ours": _med([r["ours"].get("direction_kappa") for r in rows]),
           "direction kappa competitor": _med([r["values"].get("direction_kappa") for r in rows])}
    both = [(r["ours"].get("sttype_kappa"), r["values"].get("sttype_kappa")) for r in rows]
    both = [(o, c) for o, c in both if o is not None and c is not None]
    out["jobs competitor sttype kappa >= ours"] = f"{sum(c >= o for o, c in both)} of {len(both)}"
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in out.items() if v is not None}


def scoreboard(bench: Path, engines: list[str], out_dir: Path | None = None) -> str:
    """The numbers-only markdown for the docs scoreboard: a headline row per engine, then a
    table per engine (the newest report of each)."""
    reps = {}
    for e in engines:
        found = _reports(out_dir or bench, e)
        if found:
            reps[e] = json.loads(found[-1].read_text(encoding="utf-8"))
    L = ["| engine | jobs | stitches vs pro (median x) | trims vs pro (median delta) | hops vs pro (median delta) | "
         "needle-up vs pro (median x) | sttype kappa ours / engine (median) | direction kappa ours / engine (median) | "
         "jobs engine sttype kappa >= ours |", "|---|---|---|---|---|---|---|---|---|"]
    for e, r in reps.items():
        m = summary(r)
        L.append(f"| {e} | {len(r['jobs'])} | {m.get('stitches vs pro (x)')} | {m.get('trims vs pro (delta)')} | "
                 f"{m.get('hops vs pro (delta)')} | {m.get('needle-up mm vs pro (x)')} | "
                 f"{m.get('sttype kappa ours')} / {m.get('sttype kappa competitor')} | "
                 f"{m.get('direction kappa ours')} / {m.get('direction kappa competitor')} | "
                 f"{m.get('jobs competitor sttype kappa >= ours')} |")
    if reps:                              # ours, for scale: the same medians of ours against the pro
        first = next(iter(reps.values()))
        rows = list(first["jobs"].values())
        L.append(f"| ours (today's main) | {len(rows)} | {round(_med([r['ours']['stitches'] / r['pro']['stitches'] for r in rows]), 2)} | "
                 f"{_med([r['ours']['trims'] - r['pro']['trims'] for r in rows])} | "
                 f"{_med([r['ours']['hops'] - r['pro']['hops'] for r in rows])} | "
                 f"{round(_med([r['ours']['needle_up_mm'] / r['pro']['needle_up_mm'] for r in rows if r['pro']['needle_up_mm']]), 2)} | "
                 f"{summary(first).get('sttype kappa ours')} | {summary(first).get('direction kappa ours')} | - |")
    L.append("")
    for e, r in reps.items():
        L += [table(r).replace("# ", "### ", 1), ""]
    return "\n".join(L)


# ------------------------------------------------------------------ cli
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("prep", "ours", "measure", "table", "scoreboard"))
    ap.add_argument("--bench-dir", "--bench", dest="bench", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--out-dir", type=Path, help="where runs/renders/reports go (default: --bench-dir); set it when the engine folder is not ours to write")
    ap.add_argument("--engine")
    ap.add_argument("--engines", nargs="*", help="scoreboard: engines, in table order")
    ap.add_argument("--write", type=Path, help="scoreboard: write the markdown here")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--date", default=time.strftime("%Y-%m-%d"))
    ap.add_argument("--no-words", action="store_true")
    ap.add_argument("--no-sheets", action="store_true")
    a = ap.parse_args(argv)
    slugs = job_slugs(a.only)
    a.bench.mkdir(parents=True, exist_ok=True)
    if a.cmd == "prep":
        for s, j in prep(a.bench, slugs).items():
            print(f"{s:24} {j['garment']:11} width {j['width_mm']:6} mm  longest side {j['longest_mm']} mm  art/pro aspect {j['art_aspect']}/{j['pro_aspect']}")
    elif a.cmd == "ours":
        ours_figures(a.bench, slugs, not a.no_words)
    elif a.cmd == "measure":
        if not a.engine:
            ap.error("--engine NAME")
        measure(a.bench, a.engine, slugs, a.date, not a.no_words, not a.no_sheets, a.out_dir)
    elif a.cmd == "scoreboard":
        md = scoreboard(a.bench, a.engines or [], a.out_dir)
        if a.write:
            a.write.write_text(md, encoding="utf-8")
        print(md)
    else:
        if not a.engine:
            ap.error("--engine NAME")
        reps = _reports(a.out_dir or a.bench, a.engine)
        print(table(json.loads(reps[-1].read_text(encoding="utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
