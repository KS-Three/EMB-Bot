"""Bean letters held off their small counters (`cfg.bean_letter_counter_hold_mm`,
built OFF 2026-10-14): Fremont's 81 mm 8, the arms, the corpus, the renders.

The defect: Fremont 81 mm Hat, the 8 in "1895" sews one of its two counters
shut on main, and both under `small_text_true_size` (Kent's ruling: the switch
goes ON). Its strokes are 0.22 mm of ink under a 0.40 mm thread. On main the
8 is a run outline and its 0.41 mm2 counter's ring is sewn 0.2 mm from the
outline run; under the switch it is a bean letter on its ink's centreline,
and the thread lays half its width into both counters. The hold moves each
bean-letter needle point within the hold of a small counter to the ink pixel
furthest from it (up to the hold): the thread lies on the stroke's outer
side. It touches bean letters only, so main (no bean letters) is untouched.

Every value is a CANDIDATE (ROADMAP gate 1); nothing here was sewn. Fremont
is an UNREPRESENTATIVE fixture: it reproduces the defect and sizes nothing.

Every cell is its own process (a digitize is minutes and gigabytes):

    # Fremont 81 mm Hat, one arm (DIR/<fixture>__<arm>.json + _design.json)
    .venv/Scripts/python -m tools.bean_counter_hold --cell hat81 switch_hold --out DIR
    .venv/Scripts/python -m tools.bean_counter_hold --table --out DIR
    # the render sheets: 1895 per arm, and the 8 zoomed (artwork outline red)
    .venv/Scripts/python -m tools.bean_counter_hold --sheets --out DIR --renders DIR2
    # the corpus (`small_lettering_compare`'s 17 designs), switch vs switch + hold
    .venv/Scripts/python -m tools.bean_counter_hold --corpus becker switch_hold --out DIR
    .venv/Scripts/python -m tools.bean_counter_hold --corpus-table --out DIR

Counters are read two ways. #905's reader (`fremont_small_lettering.glyph_row`):
a source counter is OPEN when at least half its area is bare of thread laid at
its width (`OPEN_SHARE`). And `glyph_legibility`, the per-glyph shape read
(`legibility`, `counters`), the same instrument `small_lettering_compare` uses.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Half the 40 wt laid width (0.40 mm): the thread's inner edge on the counter's.
HOLD_HALF_THREAD_MM = 0.2
# As far as Fremont's 0.22 mm strokes let the needle go: at 0.2 the 8's upper
# counter reads exactly 0.500 bare, on #905's line; at 0.25, 0.544.
HOLD_MM = 0.25
SWITCH = {"small_text_true_size": True}

# name -> (PipelineConfig overrides on the request, label)
# `small_text_true_size` is ON by default since 2026-10-14, so "main" pins it
# OFF: the engine before the flip, as these arms were measured.
OFF = {"small_text_true_size": False}
ARMS = {
    "main": (dict(OFF), "main"),
    "main_hold": ({**OFF, "bean_letter_counter_hold_mm": HOLD_MM}, f"main + hold {HOLD_MM}"),
    "switch": (dict(SWITCH), "small_text_true_size"),
    "switch_hold20": ({**SWITCH, "bean_letter_counter_hold_mm": HOLD_HALF_THREAD_MM},
                      f"small_text_true_size + hold {HOLD_HALF_THREAD_MM}"),
    "switch_hold": ({**SWITCH, "bean_letter_counter_hold_mm": HOLD_MM},
                    f"small_text_true_size + hold {HOLD_MM}"),
}
ARM_ORDER = list(ARMS)
FIXTURES = {"hat81": 81.0, "hat925": 92.5}       # Kent's stitch-out; the pro's size
WORDS = ["est", "1895", "the", "tagline"]
# The corpus pair: the switch (the default to be) without and with the hold.
CORPUS_BASE, CORPUS_ARM = "switch", "switch_hold"


# --- pure helpers (the tests pin these) --------------------------------------------

def open_counters(rows: list[dict]) -> tuple[int, int]:
    """(counters at least half bare, source counters) over glyph rows, #905's
    50%-bare rule (`fremont_small_lettering.OPEN_SHARE`)."""
    from tools.fremont_small_lettering import OPEN_SHARE
    shares = [c for g in rows for c in g["bare"]]
    return sum(1 for b in shares if b >= OPEN_SHARE), len(shares)


def corpus_rows(cells: dict[str, dict[str, dict]]) -> list[dict]:
    """One row per design holding both corpus arms: what the hold changed."""
    rows = []
    for name, arms in cells.items():
        a, b = arms.get(CORPUS_BASE), arms.get(CORPUS_ARM)
        if not a or not b:
            continue
        legs = {w: round(b["words"][w]["legibility"] - a["words"][w]["legibility"], 3)
                for w in b["words"] if w in a["words"]
                and b["words"][w].get("legibility") is not None
                and a["words"][w].get("legibility") is not None}
        rows.append({
            "design": name, "identical": a["md5"] == b["md5"],
            "stitches": (a["stitches"], b["stitches"]), "trims": (a["trims"], b["trims"]),
            "changed": sum(1 for k in set(a["shape_digests"]) | set(b["shape_digests"])
                           if a["shape_digests"].get(k) != b["shape_digests"].get(k)),
            "au": (a["uncovered_fires"], b["uncovered_fires"]),
            "au_mm2": (a["uncovered_total_mm2"], b["uncovered_total_mm2"]),
            "new_au": bool(b["uncovered_fires"] and not a["uncovered_fires"])
            or (set(b["uncovered_shapes"]) - set(a["uncovered_shapes"]) != set()),
            # the small-print censuses' own counter read (`small_print.measure`)
            "sp_shut": ((a["sp"]["counters_shut"], b["sp"]["counters_shut"], b["sp"]["counters"])
                        if a.get("sp") and b.get("sp") else None),
            "d_leg": legs})
    return rows


def corpus_table(cells: dict[str, dict[str, dict]]) -> str:
    lines = [f"| design | {CORPUS_BASE} st / tr | + hold st / tr | identical | shapes changed | "
             "ARTWORK_UNCOVERED (mm2) | new AU shape | legibility change | small-print counters shut |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in corpus_rows(cells):
        (s0, s1), (t0, t1) = r["stitches"], r["trims"]
        (u0, u1) = r["au_mm2"]
        legs = ", ".join(f"{w} {v:+.3f}" for w, v in r["d_leg"].items() if v) or "none moved"
        if not r["d_leg"]:
            legs = "-"
        sp = "-" if not r["sp_shut"] else f"{r['sp_shut'][0]} -> {r['sp_shut'][1]} of {r['sp_shut'][2]}"
        lines.append(f"| {r['design']} | {s0:,} / {t0} | {s1:,} / {t1} | {'yes' if r['identical'] else 'NO'} | "
                     f"{r['changed']} | {u0} -> {u1} | {'YES' if r['new_au'] else 'no'} | {legs} | {sp} |")
    return "\n".join(lines)


# --- one Fremont cell --------------------------------------------------------------

def glyph_counters(run: dict, word: str) -> list[dict]:
    """Per source glyph of `word`: #905's counter bare shares and sewn width."""
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    from tools import small_lettering_skeleton as sls
    p = run["gen"].p
    glyphs = fsl.source_glyphs(p, ft.ROIS[word])
    owners = sls._owners(run["result"], run["plan"], glyphs)
    rows = []
    for i, g in enumerate(glyphs):
        row = fsl.glyph_row(run, g, f"{word}[{i}]", owners[i], set(), False)
        rows.append({"glyph": i, "bbox_mm": row["bbox_mm"], "tier": row["tier"],
                     "stitches": row["stitches"], "sewn_w_mm": row["sewn_w_mm"],
                     "needle_offset_p50_mm": row["needle_offset_p50_mm"],
                     "counters_mm2": [c["mm2"] for c in row["counters"]],
                     "bare": [c["bare_share"] for c in row["counters"]]})
    return rows


def run_cell(fixture: str, arm: str, out: Path) -> dict:
    """Digitize one arm of Fremont the way /digitize does, read it, save it."""
    from tools import fremont_triage as ft
    from tools import glyph_legibility as gl
    from tools import small_lettering_compare as slc
    overrides, label = ARMS[arm]
    t = time.time()
    sk: dict = {}
    bean: dict = {}
    with slc.spy_tiers(sk, bean):
        run = ft.run_arm(f"{fixture}__{arm}", FIXTURES[fixture], None, preflight=False,
                         overrides=overrides)
    words, _dbg, _reg = gl.read_case("fremont", run["design"], use_ocr=True, words=WORDS)
    census = ft.roi_census(run)
    tab_words = {}
    for w in words:
        row = slc.word_row(w.summary(), [{k: v for k, v in g.items()
                                          if k in ("counters", "src_counters_openable",
                                                   "sewn_counters_spurious")} for g in w.glyphs])
        row["glyph_legibility"] = [round(float(g["legibility"]), 3) for g in w.glyphs]
        row["stitches"], row["trims"] = census[w.name]["stitches"], census[w.name]["trims"]
        row["box_mm"] = census[w.name]["box_mm"]
        row["glyphs_905"] = glyph_counters(run, w.name)
        tab_words[w.name] = row
    s = run["plan"].stats
    p = run["gen"].p
    h, wpx = p.bg_mask.shape
    tab = {"fixture": fixture, "arm": arm, "label": label, "overrides": overrides,
           "stitches": s.stitch_count, "trims": s.trims,
           "md5": slc.stream_md5(run["plan"]),
           "bean_shapes": sum(1 for r in bean.values() if not r.get("empty")),
           "held_shapes": sum(1 for r in run["result"].regions if r.meta.get("bean_counter_held")),
           "words": tab_words, "secs": round(time.time() - t),
           "frame": {"hw": [int(h), int(wpx)], "art_bbox": [float(v) for v in p.art_bbox],
                     "px_per_mm": float(p.px_per_mm)}}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{fixture}__{arm}.json").write_text(json.dumps(tab, indent=1))
    (out / f"{fixture}__{arm}_design.json").write_text(json.dumps(run["design"]))
    print(fmt_cell(tab), flush=True)
    return tab


def fmt_cell(tab: dict) -> str:
    lines = [f"{tab['fixture']}__{tab['arm']}: {tab['stitches']:,} st, {tab['trims']} tr, "
             f"bean {tab['bean_shapes']}, held {tab['held_shapes']}, md5 {tab['md5'][:8]}"]
    for w in WORDS:
        r = tab["words"][w]
        k, n = open_counters(r["glyphs_905"])
        ctr = " ".join("[" + "/".join(f"{b:.2f}" for b in g["bare"]) + "]"
                       for g in r["glyphs_905"] if g["bare"])
        lines.append(f"  {w:8s} legibility {r['legibility']:.3f} (per glyph {r['glyph_legibility']}), "
                     f"open by 50% bare {k}/{n} {ctr}, {r['stitches']} st {r['trims']} tr")
    return "\n".join(lines)


def load_cells(out: Path) -> dict[str, dict]:
    cells = {}
    for p in sorted(out.glob("*__*.json")):
        if p.stem.endswith("_design") or p.stem.startswith("corpus_"):
            continue
        d = json.loads(p.read_text())
        if "words" in d:
            cells[p.stem] = d
    return cells


def table(cells: dict[str, dict]) -> str:
    """Markdown: per arm, stitches / trims, then per word legibility and #905's
    open counters; and the 8's own two counters."""
    lines = ["| size | arm | stitches | trims | EST | 1895 | THE | tagline | the 8's counters (bare share) | 9 | "
             "open (50% rule), 1895 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for fx, width in FIXTURES.items():
        for a in ARM_ORDER:
            c = cells.get(f"{fx}__{a}")
            if not c:
                continue
            legs = " | ".join(f"{c['words'][w]['legibility']:.3f}" for w in WORDS)
            g = c["words"]["1895"]["glyphs_905"]
            eight = "/".join(f"{b:.3f}" for b in g[1]["bare"]) if len(g) > 1 else "-"
            nine = "/".join(f"{b:.3f}" for b in g[2]["bare"]) if len(g) > 2 else "-"
            k, n = open_counters(g)
            lines.append(f"| {width:g} mm | {a} | {c['stitches']:,} | {c['trims']} | {legs} | {eight} | {nine} | {k} of {n} |")
    return "\n".join(lines)


# --- renders ------------------------------------------------------------------------

def _rings(frame: dict, word: str, index: int | None = None) -> list:
    import numpy as np
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    p = SimpleNamespace(bg_mask=np.zeros(frame["hw"], np.uint8), art_bbox=frame["art_bbox"],
                        px_per_mm=frame["px_per_mm"])
    glyphs = fsl.source_glyphs(p, ft.ROIS[word])
    if index is not None:
        glyphs = glyphs[index:index + 1]
    return [list(r.coords) for g in glyphs for r in (g.exterior, *g.interiors)]


def _panel(design: dict, box: list, rings: list, ppm: float, caption: str):
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    img, to_px = ft._render(design, ppm)
    crop = ft._crop(img, to_px, box, margin_mm=0.3).copy()
    ax, ay = to_px(box[0] - 0.3, box[1] - 0.3)
    ox, oy = int(max(0, ax)), int(max(0, ay))
    for ring in rings:
        pts = np.array([[to_px(x, y)[0] - ox, to_px(x, y)[1] - oy] for x, y in ring], np.int32)
        cv2.polylines(crop, [pts], True, (40, 40, 220), 1, cv2.LINE_AA)
    return ft._label(crop, caption)


def sheets(out: Path, renders: Path) -> list[Path]:
    """`<fixture>_1895.png` (every arm's 1895 at 110 px/mm) and
    `<fixture>_eight.png` (the 8 at 300 px/mm), artwork outline red, thread at
    its laid width: a picture of the file, not of cloth."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    written = []
    for fx, width in FIXTURES.items():
        have = [a for a in ARM_ORDER if (out / f"{fx}__{a}.json").exists()
                and (out / f"{fx}__{a}_design.json").exists()]
        for name, ppm, word_box in (("1895", 110, None), ("eight", 300, 1)):
            rows = []
            for a in have:
                tab = json.loads((out / f"{fx}__{a}.json").read_text())
                design = json.loads((out / f"{fx}__{a}_design.json").read_text())
                r = tab["words"]["1895"]
                g = r["glyphs_905"]
                box = r["box_mm"] if word_box is None else g[word_box]["bbox_mm"]
                rings = _rings(tab["frame"], "1895", word_box)
                k, n = open_counters(g if word_box is None else [g[word_box]])
                bares = "/".join(f"{b:.2f}" for b in (g[1]["bare"] if len(g) > 1 else []))
                cap = (f"{a}: 1895 legibility {r['legibility']:.3f} | 8 bare {bares} | "
                       f"open {k}/{n} | {tab['stitches']:,} st {tab['trims']} tr")
                rows.append(_panel(design, box, rings, ppm, cap))
            if not rows:
                continue
            wd = max(x.shape[1] for x in rows)
            sheet = np.vstack([np.pad(x, ((0, 8), (0, wd - x.shape[1]), (0, 0)), constant_values=255)
                               for x in rows])
            sheet = ft._label(sheet, f"Fremont {width:g} mm Hat, {name}: {ppm} px/mm, artwork outline red, "
                                     "thread at its laid width (a picture of the file, not of cloth)", width=wd)
            path = renders / f"{fx}_{name}.png"
            cv2.imwrite(str(path), sheet)
            written.append(path)
    return written


# --- the corpus ---------------------------------------------------------------------

def corpus_cell(name: str, arm: str, out: Path) -> dict:
    """One `small_lettering_compare` corpus design under one arm, recorded the
    way that tool records it (stitches, trims, md5, ARTWORK_UNCOVERED, the
    words `glyph_legibility` can read)."""
    from digitizer_core.adapter import plan_to_design
    from tools import fremont_triage as ft
    from tools import small_lettering_compare as slc
    spec = slc.corpus_designs()[name]
    overrides = ARMS[arm][0]
    t = time.time()
    sk: dict = {}
    bean: dict = {}
    with slc.spy_tiers(sk, bean):
        if spec["kind"] == "logo":
            run = slc._digitize(spec["path"], {**spec["cfg"], **overrides})
        elif spec["kind"] == "hat":
            run = ft.run_arm(name, spec["width_mm"], None, preflight=False, overrides=overrides)
        else:
            run, extra = slc._digitize_small_print(spec, overrides, out)
    rec = {"design": name, "arm": arm, "kind": spec["kind"], "overrides": overrides,
           **slc.corpus_metrics(run), **(extra if spec["kind"] == "small_print" else {}),
           "bean_shapes": sum(1 for r in bean.values() if not r.get("empty")),
           "held_shapes": sum(1 for r in run["result"].regions if r.meta.get("bean_counter_held"))}
    case = slc.LEGIBILITY_CASE.get(name)
    rec["words"] = slc.corpus_words(case, plan_to_design(run["plan"], name=name)) if case else {}
    rec["secs"] = round(time.time() - t)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"corpus_{name}__{arm}.json").write_text(json.dumps(rec, indent=1))
    print(f"{name}__{arm}: {rec['stitches']:,} st, {rec['trims']} tr, md5 {rec['md5'][:8]}, "
          f"AU {rec['uncovered_total_mm2']} mm2, bean {rec['bean_shapes']}, held {rec['held_shapes']}, "
          f"{rec['secs']} s", flush=True)
    return rec


def load_corpus(out: Path) -> dict[str, dict[str, dict]]:
    cells: dict[str, dict[str, dict]] = {}
    for p in sorted(out.glob("corpus_*__*.json")):
        d = json.loads(p.read_text())
        cells.setdefault(d["design"], {})[d["arm"]] = d
    return cells


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cell", nargs=2, metavar=("FIXTURE", "ARM"),
                    help=f"digitize and read one Fremont cell; FIXTURE in {list(FIXTURES)}, ARM in {ARM_ORDER}")
    ap.add_argument("--table", action="store_true", help="print the Fremont table from the saved cells")
    ap.add_argument("--sheets", action="store_true", help="render 1895 and the 8 per saved arm")
    ap.add_argument("--corpus", nargs=2, metavar=("DESIGN", "ARM"),
                    help=f"digitize one small_lettering_compare corpus design; ARM in {[CORPUS_BASE, CORPUS_ARM]}")
    ap.add_argument("--corpus-table", action="store_true", help="print the corpus table from the saved cells")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.out is None:
        ap.error("--out is required")
    if a.cell:
        fx, arm = a.cell
        if fx not in FIXTURES or arm not in ARMS:
            raise SystemExit(f"--cell FIXTURE in {list(FIXTURES)}, ARM in {ARM_ORDER}")
        run_cell(fx, arm, a.out)
    if a.corpus:
        from tools import small_lettering_compare as slc
        name, arm = a.corpus
        if name not in slc.corpus_designs() or arm not in (CORPUS_BASE, CORPUS_ARM):
            raise SystemExit(f"--corpus DESIGN in {list(slc.corpus_designs())}, ARM in {[CORPUS_BASE, CORPUS_ARM]}")
        corpus_cell(name, arm, a.out)
    if a.table:
        print(table(load_cells(a.out)))
    if a.corpus_table:
        print(corpus_table(load_corpus(a.out)))
    if a.sheets:
        for pth in sheets(a.out, a.renders or a.out / "renders"):
            print(pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
