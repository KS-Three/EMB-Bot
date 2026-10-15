#!/usr/bin/env python
"""Bean stations held off open bays (`cfg.bean_letter_bay_hold`, built OFF
2026-10-15): Fremont's 1895 and THE, the corpus, the renders.

The defect (#953's `bean_glyph_trace`): under `small_text_true_size` (ON by
default since #955) a bean letter sews its ink's centreline, and a 0.40 mm
thread on 0.19 mm strokes lays 0.10 mm past each edge. At 81 mm the 5's upper
bay sews 64% covered (#905's 50% rule: FILLED) and the 5 reads A; at 92.5 mm
the slit between THE's E tick and its middle arm sews shut into a false
counter. The hold moves each bean station within the hold of a bay to the
point of its own spine's ink furthest from the bays (#952's rule, served to
bays): the thread lies on the stroke's side away from the bay.

Every value is a CANDIDATE (ROADMAP gate 1); nothing here was sewn. Fremont
is an UNREPRESENTATIVE fixture: it reproduces the defect and sizes nothing.

The flag is read in stage 7 only, so one digitize serves every arm: the
cell digitizes once and PLANS once per arm (`plan_stitches` on the same
result). `--check-replan` pins that against a fresh digitize.

    # Fremont, one fixture, every arm (DIR/<fixture>__<arm>.json + _design.json)
    .venv/Scripts/python -m tools.bean_bay_hold --cell hat81 --out DIR
    .venv/Scripts/python -m tools.bean_bay_hold --table --out DIR
    .venv/Scripts/python -m tools.bean_bay_hold --sheets --out DIR --renders DIR2
    # the corpus (`small_lettering_compare`'s 17 designs), switch vs + bay hold
    .venv/Scripts/python -m tools.bean_bay_hold --corpus becker --out DIR
    .venv/Scripts/python -m tools.bean_bay_hold --corpus-table --out DIR

Per glyph it reports #953's reads: each source BAY's bare share (open at
`OPEN_SHARE`), the THREAD HOLES the thread encloses that are no source
counter (strict, and bridged under `BRIDGE_GAP_MM`), and `glyph_legibility`'s
row (legibility, spurious sewn counters, OCR) as secondary columns.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Half the 40 wt laid width; and #952's chosen counter hold, one pixel of margin past it.
HOLD_HALF_THREAD_MM = 0.2
HOLD_MM = 0.25
# name -> (PipelineConfig overrides on the request, label). "switch" is main's
# defaults: `small_text_true_size` is ON since #955.
ARMS = {
    "switch": ({}, "main defaults (small_text_true_size ON)"),
    "bay20": ({"bean_letter_bay_hold": HOLD_HALF_THREAD_MM}, f"switch + bay hold {HOLD_HALF_THREAD_MM}"),
    "bay": ({"bean_letter_bay_hold": HOLD_MM}, f"switch + bay hold {HOLD_MM}"),
}
ARM_ORDER = list(ARMS)
FIXTURES = {"hat81": 81.0, "hat925": 92.5}
WORDS = ["est", "1895", "the", "tagline"]
CORPUS_BASE, CORPUS_ARM = "switch", "bay"
OPEN_SHARE = 0.5


# --- pure helpers (the tests pin these) --------------------------------------------

def glyph_summary(tr: dict, gl_row: dict | None) -> dict:
    """One glyph's row from a `bean_glyph_trace.trace_glyph` record and its
    `glyph_legibility` row."""
    holes = [h for h in tr["thread_holes"] if not h["source_counter"]]
    g = gl_row or {}
    return {"glyph": tr["glyph"], "tier": tr["tier"],
            "bays": [{"where": b["where"], "mm2": b["mm2"], "bare": b["bare_share"]} for b in tr["bays"]],
            "bays_filled": sum(1 for b in tr["bays"] if b["bare_share"] is not None
                               and b["bare_share"] < OPEN_SHARE),
            "holes_strict": sum(1 for h in holes if h["reading"] == "strict"),
            "holes_bridged": sum(1 for h in holes if h["reading"] == "bridged"),
            "legibility": g.get("legibility"), "counters": g.get("counters"),
            "spurious": g.get("sewn_counters_spurious"),
            "ocr": f"{g.get('ocr_src', '?')}->{g.get('ocr_sewn', '?')}" if g.get("ocr_src") else None}


def fmt_bays(row: dict) -> str:
    return " ".join(f"{b['where']} {b['mm2']:.3f}:{b['bare']:.2f}" for b in row["bays"]) or "-"


def glyph_table(cells: dict[str, dict]) -> str:
    """Per glyph, every arm: bay bare shares, filled bays, thread holes
    (strict / bridged), spurious sewn counters; legibility and OCR last."""
    lines = ["| size | word | glyph | arm | bays (where mm2:bare) | filled | thread holes strict / bridged | "
             "spurious sewn counters | legibility | OCR src->sewn |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for fx, width in FIXTURES.items():
        arms = [a for a in ARM_ORDER if f"{fx}__{a}" in cells]
        if not arms:
            continue
        for w in WORDS:
            n = len(cells[f"{fx}__{arms[0]}"]["words"][w]["glyphs"])
            for i in range(n):
                rows = [cells[f"{fx}__{a}"]["words"][w]["glyphs"][i] for a in arms]
                if all(r == rows[0] for r in rows[1:]):
                    continue                   # unchanged in every arm: not listed
                for a, r in zip(arms, rows):
                    leg = "-" if r["legibility"] is None else f"{r['legibility']:.3f}"
                    lines.append(f"| {width:g} | {w} | {r['glyph']} | {a} | {fmt_bays(r)} | {r['bays_filled']} | "
                                 f"{r['holes_strict']} / {r['holes_bridged']} | {r['spurious']} | {leg} | "
                                 f"{r['ocr'] or '-'} |")
    return "\n".join(lines)


def word_table(cells: dict[str, dict]) -> str:
    """Per fixture and arm: stitches / trims / md5, then per word legibility and OCR (Wilson 95%)."""
    from tools import small_lettering_compare as slc
    lines = ["| size | arm | st / tr | md5 | " + " | ".join(f"{w} legibility, OCR" for w in WORDS) + " |",
             "|---|---|---|---|" + "---|" * len(WORDS)]
    for fx, width in FIXTURES.items():
        for a in ARM_ORDER:
            c = cells.get(f"{fx}__{a}")
            if not c:
                continue
            ws = " | ".join(f"{c['words'][w]['legibility']:.3f}, {slc.fmt_ocr(c['words'][w]['ocr'])}"
                            for w in WORDS)
            lines.append(f"| {width:g} | {a} | {c['stitches']:,} / {c['trims']} | `{c['md5'][:8]}` | {ws} |")
    return "\n".join(lines)


def corpus_rows(cells: dict[str, dict[str, dict]]) -> list[dict]:
    """One row per design with both arms: identical?, shapes changed, AU, bare, legibility."""
    from tools import small_lettering_compare as slc
    rows = []
    for name in slc._ordered(cells):
        b, c = cells[name].get(CORPUS_BASE), cells[name].get(CORPUS_ARM)
        if not b or not c:
            continue
        legs = {w: round(c["words"][w]["legibility"] - b["words"][w]["legibility"], 3)
                for w in c["words"] if w in b["words"] and c["words"][w].get("legibility") is not None
                and b["words"][w].get("legibility") is not None}
        rows.append({"design": name, "base": f"{b['stitches']:,} / {b['trims']}",
                     "arm": f"{c['stitches']:,} / {c['trims']}", "identical": b["md5"] == c["md5"],
                     "changed": slc.changed_shapes(b["shape_digests"], c["shape_digests"]),
                     "au": f"{b['uncovered_total_mm2']} -> {c['uncovered_total_mm2']}",
                     "au_up": (c["uncovered_total_mm2"] or 0) > (b["uncovered_total_mm2"] or 0) + 1e-9,
                     "new_au": bool(set(c["uncovered_shapes"]) - set(b["uncovered_shapes"])),
                     "d_bare": round(c["bare_mm2"] - b["bare_mm2"], 2), "d_leg": legs,
                     "satin_same": b.get("satin_md5") == c.get("satin_md5"),
                     "bean": c.get("bean_shapes")})
    return rows


def corpus_table(cells: dict[str, dict[str, dict]]) -> str:
    lines = ["| design | switch st / tr | + bay hold st / tr | identical | shapes changed | "
             "ARTWORK_UNCOVERED mm2 | new AU shape | dBare mm2 | satin runs identical | legibility change |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in corpus_rows(cells):
        leg = ", ".join(f"{w} {d:+.3f}" for w, d in r["d_leg"].items() if d) or ("none moved" if r["d_leg"] else "-")
        lines.append(f"| {r['design']} | {r['base']} | {r['arm']} | {'yes' if r['identical'] else 'NO'} | "
                     f"{r['changed']} | {r['au']} | {'YES' if r['new_au'] else 'no'} | {r['d_bare']:+.2f} | "
                     f"{'yes' if r['satin_same'] else 'NO'} | {leg} |")
    return "\n".join(lines)


# --- digitizing ---------------------------------------------------------------------

def _plan(run: dict, overrides: dict, spies: tuple[dict, dict]) -> dict:
    """`run` re-planned under `overrides` (stage 7 only), tier functions spied."""
    from dataclasses import replace

    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import plan_stitches
    from tools import bean_glyph_trace as bgt
    cfg = replace(run["cfg"], **overrides)
    bean, skel = spies
    with bgt.spy_tiers(bean, skel):
        plan = plan_stitches(run["result"], cfg)
    return {**run, "cfg": cfg, "plan": plan, "design": plan_to_design(plan, name="Digitized design"),
            "bean": bean, "skel": skel}


def read_fremont(run: dict, fixture: str, arm: str) -> dict:
    """Every word of one planned Fremont arm: `glyph_legibility` (OCR on) and
    #953's per-glyph trace (bays, thread holes)."""
    from tools import bean_glyph_trace as bgt
    from tools import fremont_triage as ft
    from tools import glyph_legibility as gl
    from tools import small_lettering_compare as slc
    run = {**run, "cell": fixture, "arm": arm}
    words, _dbg, _reg = gl.read_case("fremont", run["design"], use_ocr=True, words=WORDS)
    census = ft.roi_census(run)
    out = {}
    for w in words:
        row = slc.word_row(w.summary(), [{k: v for k, v in g.items()
                                          if k in ("counters", "src_counters_openable", "sewn_counters_spurious")}
                                         for g in w.glyphs])
        n = len(bgt.word_glyphs(run["gen"].p, w.name))
        traces = bgt.analyse(run, [f"{w.name}:#{i}" for i in range(n)], ocr=False)
        gl_rows = w.glyphs if len(w.glyphs) == n else [None] * n
        row["glyphs"] = [glyph_summary(tr, g) for tr, g in zip(traces, gl_rows)]
        row["stitches"], row["trims"] = census[w.name]["stitches"], census[w.name]["trims"]
        row["box_mm"] = census[w.name]["box_mm"]
        out[w.name] = row
    return out


def run_cell(fixture: str, out: Path, arms: list[str] | None = None) -> list[dict]:
    """Digitize Fremont once at `fixture`, plan and read every arm, save each."""
    from tools import fremont_triage as ft
    from tools import small_lettering_compare as slc
    t = time.time()
    run = ft.run_arm(f"{fixture}__base", FIXTURES[fixture], None, preflight=False, overrides={})
    out.mkdir(parents=True, exist_ok=True)
    tabs = []
    for arm in arms or ARM_ORDER:
        overrides, label = ARMS[arm]
        pr = _plan(run, overrides, ({}, {}))
        p = pr["gen"].p
        h, wpx = p.bg_mask.shape
        s = pr["plan"].stats
        tab = {"fixture": fixture, "arm": arm, "label": label, "overrides": overrides,
               "stitches": s.stitch_count, "trims": s.trims, "md5": slc.stream_md5(pr["plan"]),
               "bean_shapes": sum(1 for v in pr["bean"].values() if not v[-1]["report"].get("empty")),
               "words": read_fremont(pr, fixture, arm),
               "frame": {"hw": [int(h), int(wpx)], "art_bbox": [float(v) for v in p.art_bbox],
                         "px_per_mm": float(p.px_per_mm)}, "secs": round(time.time() - t)}
        (out / f"{fixture}__{arm}.json").write_text(json.dumps(tab, indent=1))
        (out / f"{fixture}__{arm}_design.json").write_text(json.dumps(pr["design"]))
        print(f"{fixture}__{arm}: {tab['stitches']:,} st, {tab['trims']} tr, md5 {tab['md5'][:8]}, "
              f"{tab['secs']} s", flush=True)
        tabs.append(tab)
    return tabs


def check_replan(fixture: str, arm: str) -> dict:
    """A fresh digitize of `arm` against the base digitize re-planned: the md5s
    must agree, or `run_cell`'s shortcut is not the engine."""
    from tools import fremont_triage as ft
    from tools import small_lettering_compare as slc
    base = ft.run_arm(f"{fixture}__base", FIXTURES[fixture], None, preflight=False, overrides={})
    _plan(base, ARMS[ARM_ORDER[0]][0], ({}, {}))       # planned first, as `run_cell` does
    replanned = slc.stream_md5(_plan(base, ARMS[arm][0], ({}, {}))["plan"])
    fresh = ft.run_arm(f"{fixture}__{arm}", FIXTURES[fixture], None, preflight=False, overrides=ARMS[arm][0])
    res = {"fixture": fixture, "arm": arm, "replanned": replanned, "fresh": slc.stream_md5(fresh["plan"])}
    res["same"] = res["replanned"] == res["fresh"]
    print(json.dumps(res), flush=True)
    return res


def satin_md5(plan) -> str:
    """md5 of the SATIN runs alone, in sew order (`stream_md5`'s recipe): the
    satin tier the DOCTRINE 2026-09-30 notch-guard negative was measured on."""
    import hashlib

    from digitizer_core import stitches
    coords = [[round(x, 4), round(y, 4), r.jump, r.trim]
              for _, r in plan.iter_runs() if r.kind == stitches.SATIN for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def corpus_cell(name: str, out: Path) -> list[dict]:
    """One `small_lettering_compare` corpus design: digitized once, planned
    under the base and the hold arm, recorded the way that tool records it."""
    from digitizer_core.adapter import plan_to_design
    from tools import fremont_triage as ft
    from tools import small_lettering_compare as slc
    spec = slc.corpus_designs()[name]
    t = time.time()
    extra: dict = {}
    if spec["kind"] == "logo":
        run = slc._digitize(spec["path"], dict(spec["cfg"]))
    elif spec["kind"] == "hat":
        run = ft.run_arm(name, spec["width_mm"], None, preflight=False, overrides={})
    else:
        run, extra = slc._digitize_small_print(spec, {}, out)
    recs = []
    for arm in (CORPUS_BASE, CORPUS_ARM):
        pr = _plan(run, ARMS[arm][0], ({}, {}))
        rec = {"design": name, "arm": arm, "kind": spec["kind"], "overrides": ARMS[arm][0],
               **slc.corpus_metrics(pr), "satin_md5": satin_md5(pr["plan"]),
               "bean_shapes": sum(1 for v in pr["bean"].values() if not v[-1]["report"].get("empty"))}
        if arm == CORPUS_BASE:
            rec.update(extra)                  # the small-print census reads the base cfg only
        case = slc.LEGIBILITY_CASE.get(name)
        rec["words"] = slc.corpus_words(case, plan_to_design(pr["plan"], name=name)) if case else {}
        rec["secs"] = round(time.time() - t)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"corpus_{name}__{arm}.json").write_text(json.dumps(rec, indent=1))
        print(f"{name}__{arm}: {rec['stitches']:,} st, {rec['trims']} tr, md5 {rec['md5'][:8]}, "
              f"AU {rec['uncovered_total_mm2']} mm2, bare {rec['bare_mm2']} mm2, bean {rec['bean_shapes']}, "
              f"{rec['secs']} s", flush=True)
        recs.append(rec)
    return recs


def load_cells(out: Path) -> dict[str, dict]:
    cells = {}
    for p in sorted(out.glob("*__*.json")):
        if p.stem.endswith("_design") or p.stem.startswith("corpus_"):
            continue
        d = json.loads(p.read_text())
        if "words" in d:
            cells[p.stem] = d
    return cells


def load_corpus(out: Path) -> dict[str, dict[str, dict]]:
    cells: dict[str, dict[str, dict]] = {}
    for p in sorted(out.glob("corpus_*__*.json")):
        d = json.loads(p.read_text())
        cells.setdefault(d["design"], {})[d["arm"]] = d
    return cells


# --- renders ------------------------------------------------------------------------

SHEETS = {"1895": 110, "the": 80}


def sheets(out: Path, renders: Path) -> list[Path]:
    """`<fixture>_<word>.png`: 1895 and THE, one row per saved arm, artwork
    outline red, thread at its laid width. stitchviz draws a three-pass bean
    as ONE thread width, so every bean letter here is under-drawn."""
    import cv2
    import numpy as np
    from tools import bean_counter_hold as bch
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    written = []
    for fx, width in FIXTURES.items():
        have = [a for a in ARM_ORDER if (out / f"{fx}__{a}.json").exists()
                and (out / f"{fx}__{a}_design.json").exists()]
        for word, ppm in SHEETS.items():
            rows = []
            for a in have:
                tab = json.loads((out / f"{fx}__{a}.json").read_text())
                design = json.loads((out / f"{fx}__{a}_design.json").read_text())
                r = tab["words"][word]
                filled = sum(g["bays_filled"] for g in r["glyphs"])
                holes = sum(g["holes_strict"] for g in r["glyphs"])
                cap = (f"{ARMS[a][1]}: {word} legibility {r['legibility']:.3f} | bays filled {filled} | "
                       f"thread holes {holes} | {tab['stitches']:,} st {tab['trims']} tr")
                rows.append(bch._panel(design, r["box_mm"], bch._rings(tab["frame"], word), ppm, cap))
            if not rows:
                continue
            wd = max(x.shape[1] for x in rows)
            sheet = np.vstack([np.pad(x, ((0, 8), (0, wd - x.shape[1]), (0, 0)), constant_values=255)
                               for x in rows])
            sheet = ft._label(sheet, f"Fremont {width:g} mm Hat, {word}: {ppm} px/mm, artwork outline red, thread at "
                                     "its laid width; a 3-pass bean is drawn as ONE thread (under-drawn). A picture of "
                                     "the file, not of cloth", width=wd)
            path = renders / f"{fx}_{word}.png"
            cv2.imwrite(str(path), sheet)
            written.append(path)
    return written


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cell", choices=list(FIXTURES), help="digitize Fremont once, plan and read every arm")
    ap.add_argument("--arm", action="append", choices=ARM_ORDER, help="only these arms (repeatable)")
    ap.add_argument("--check-replan", nargs=2, metavar=("FIXTURE", "ARM"),
                    help="a fresh digitize of ARM against the re-planned base")
    ap.add_argument("--table", action="store_true", help="print the Fremont tables from the saved cells")
    ap.add_argument("--sheets", action="store_true", help="render 1895 and THE per saved arm")
    ap.add_argument("--corpus", help="digitize one small_lettering_compare corpus design, both arms")
    ap.add_argument("--corpus-table", action="store_true", help="print the corpus table from the saved cells")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.out is None and not a.check_replan:
        ap.error("--out is required")
    if a.cell:
        run_cell(a.cell, a.out, a.arm)
    if a.check_replan:
        check_replan(*a.check_replan)
    if a.corpus:
        corpus_cell(a.corpus, a.out)
    if a.table:
        cells = load_cells(a.out)
        print(word_table(cells), "\n")
        print(glyph_table(cells))
    if a.corpus_table:
        print(corpus_table(load_corpus(a.out)))
    if a.sheets:
        for pth in sheets(a.out, a.renders or a.out / "renders"):
            print(pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
