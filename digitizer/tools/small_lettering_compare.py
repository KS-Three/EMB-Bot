"""Small lettering, head to head, on ONE render set: which option should be on?

MASTER_SCOPE "Waiting on Kent" 56 says it plainly: the true-size route
(`small_text_restore_mm` + `bean_letter_*`, PRs #911/#914) and the skeleton run
(`small_lettering_skeleton`, PR #913) attack the same small Hotel Fremont
lettering, "the two have not been compared on one render and only one should be
on: his". Each was built and measured alone, on its own render set, with its own
reader. This puts them side by side, with ONE reader, on the same two renders.
It changes no engine code, flips nothing, sets no constant (ROADMAP gate 1: the
floors, pitches and the 3.0 mm line height are candidates).

Fixtures: the Studio request of `fremont_triage.studio_request` (Hat) at 81 mm
(Kent's stitch-out) and at 92.5 mm (the pro's size). Arms:

    main      both flags off
    sk073     small_lettering_skeleton ON, floor 0.73 mm (BEAN_STITCH_MM)
    sk100     small_lettering_skeleton ON, floor 1.0 mm (the default)
    true      small_text_restore_mm 3.0 + bean_letter_max_stroke_mm 0.4 +
              bean_letter_stitch_mm 0.45 + bean_letter_serif_mm 0.45
    both073   true + skeleton ON, floor 0.73 (bean letters are tried first,
              so the skeleton run only sees what they decline)
    both100   true + skeleton ON, floor 1.0

Per word (EST, 1895, THE, the EAT | STAY | PLAY tagline), per arm, from
`glyph_legibility.read_case` (the repo's per-glyph shape read of the sewn
thread, one reader for every arm and for the pro's file): glyph legibility
(the weakest of strokes, clean, counters), legibility with negative space
added, source counters still open, OCR glyphs recovered with a Wilson 95%
interval (tesseract on each glyph alone), and the stitches and trims whose
needle points fall inside the word's box. The pro's Hat and Patch files are
read by the same instrument as reference rows; they carry no stitch or trim
split (their frame is not ours). CAVEAT, from the instrument's own docstring:
the pro sews EST, 1895 and the tagline as bold block letters about 2 mm off the
artwork, so the pro's score on those is a comparison of two designs.

Every cell is its own process (a digitize is minutes and gigabytes). A cell's
table is saved as JSON, so the printed table is re-runnable from DIR without
digitizing, and a lane that changes the engine re-runs only its cells:

    # one cell: <fixture> hat81|hat925, <arm> (writes DIR/<fixture>__<arm>.json + _design.json)
    .venv/Scripts/python -m tools.small_lettering_compare --cell hat81 main --out DIR
    # the pro's two files as reference rows (reads the committed zip)
    .venv/Scripts/python -m tools.small_lettering_compare --pro --out DIR
    # the table, from the saved cells (no digitizing)
    .venv/Scripts/python -m tools.small_lettering_compare --table --out DIR
    # render sheets (artwork, then one row per arm; red outline = artwork)
    .venv/Scripts/python -m tools.small_lettering_compare --sheets --out DIR --renders DIR2
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRO_WIDTH_MM = 92.5
FIXTURES = {"hat81": 81.0, "hat925": PRO_WIDTH_MM}
WORDS = ["est", "1895", "the", "tagline"]
WORD_TITLE = {"est": "EST", "1895": "1895", "the": "THE", "tagline": "tagline"}

SKELETON = {"small_lettering_skeleton": True}
FLOOR_073 = {"small_lettering_skeleton_floor_mm": 0.73}        # machine.BEAN_STITCH_MM
# #911 + #914: the four values MASTER_SCOPE 56 renders Fremont's date with
# (candidates, gate 1; unsewn).
TRUE_SIZE = {"small_text_restore_mm": 3.0, "bean_letter_max_stroke_mm": 0.4,
             "bean_letter_stitch_mm": 0.45, "bean_letter_serif_mm": 0.45}

# name -> (PipelineConfig overrides on the Studio request, label)
ARMS = {
    "main": ({}, "main (both options off)"),
    "sk073": ({**SKELETON, **FLOOR_073}, "skeleton ON, floor 0.73 mm"),
    "sk100": (dict(SKELETON), "skeleton ON, floor 1.0 mm (default)"),
    "true": (dict(TRUE_SIZE), "true size: restore 3.0, bean 0.4 / pitch 0.45 / serif 0.45"),
    "both073": ({**TRUE_SIZE, **SKELETON, **FLOOR_073}, "true size + skeleton, floor 0.73 mm"),
    "both100": ({**TRUE_SIZE, **SKELETON}, "true size + skeleton, floor 1.0 mm"),
}
ARM_ORDER = list(ARMS)

# The pro's two Hotel Fremont files, inside the committed zip (public already).
PRO_ZIP = ROOT.parent / "Embroidery Files.zip"
PRO_FILES = {
    "pro_hat": "Embroidery Files/Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES",
    "pro_patch": "Embroidery Files/Hotel Fremont/Hotel Patch/HOTEL FREMONT .PES",
}


# --- pure helpers (no digitizing; the tests pin these) ----------------------------

def wilson(k: int, n: int, z: float = 1.96):
    """Wilson score interval, the instrument's own (`glyph_legibility.wilson`)."""
    from tools import glyph_legibility as gl
    return gl.wilson(k, n, z)


def counters_open(glyphs: list[dict]) -> tuple[int, int]:
    """(source counters still open, source counters a reader can see), summed
    over a word's glyph rows. The instrument scores `counters` as matched /
    (openable + spurious), one sewn hole answering at most one source counter,
    so the matched count is that score times the denominator."""
    k = n = 0
    for g in glyphs:
        openable = int(g.get("src_counters_openable", 0))
        spurious = int(g.get("sewn_counters_spurious", 0))
        n += openable
        k += min(openable, int(round(float(g.get("counters", 0.0)) * (openable + spurious))))
    return k, n


def word_row(summary: dict, glyphs: list[dict]) -> dict:
    """One word of one arm -> the numbers the table prints."""
    ocr = summary.get("ocr")
    if isinstance(ocr, dict):
        o = {"recovered": ocr["recovered"], "read": ocr["read_on_source"], "ci95": ocr["ci95"]}
    else:
        o = {"recovered": None, "read": None, "ci95": None, "note": str(ocr)}
    k, n = counters_open(glyphs)
    return {"glyphs": summary["glyphs"], "legibility": summary["legibility"],
            "legibility_space": summary["legibility_space"], "worst_glyph": summary["worst_glyph"],
            "counters_open": [k, n], "ocr": o}


def fmt_ocr(o: dict) -> str:
    if o.get("recovered") is None:
        return "n/a"
    s = f"{o['recovered']}/{o['read']}"
    return s + ("" if o["ci95"] is None else f" [{o['ci95'][0]:.2f}-{o['ci95'][1]:.2f}]")


def fmt_word(w: dict) -> str:
    """The table cell: legibility / +space / counters open / OCR / st / tr."""
    if w.get("legibility") is None:
        return "no glyphs read"
    k, n = w["counters_open"]
    st = "-" if w.get("stitches") is None else f"{w['stitches']}"
    tr = "-" if w.get("trims") is None else f"{w['trims']}"
    return (f"{w['legibility']:.3f} / {w['legibility_space']:.3f} / ctr {k}of{n} / "
            f"OCR {fmt_ocr(w['ocr'])} / {st} st / {tr} tr")


def table(cells: dict[str, dict], arm_order=None) -> str:
    """Markdown. One block per fixture, one block per word: a row per arm.
    `cells` maps '<fixture>__<arm>' (or '<pro name>') to a saved cell."""
    arms = list(arm_order or ARM_ORDER)
    lines = []
    for fx, width in FIXTURES.items():
        have = [a for a in arms if f"{fx}__{a}" in cells]
        if not have:
            continue
        lines.append(f"#### Hotel Fremont, Hat, {width:g} mm\n")
        lines.append("| arm | stitches | trims | built as (EST / 1895 / THE / tagline: skeleton, bean, outline) |")
        lines.append("|---|---|---|---|")
        for a in have:
            c = cells[f"{fx}__{a}"]
            built = " / ".join("{}, {}, {}".format(*(c["words"][w]["built"][k] for k in ("skeleton", "bean", "outline")))
                               for w in WORDS)
            lines.append(f"| {a} | {c['stitches']:,} | {c['trims']} | {built} |")
        lines.append("")
        for w in WORDS:
            lines.append(f"**{WORD_TITLE[w]}** (legibility / +space / counters open of source / "
                         "OCR glyphs recovered, Wilson 95% / stitches and trims in the word's box)\n")
            lines.append("| arm | legibility | +space | counters open | OCR recovered | stitches | trims |")
            lines.append("|---|---|---|---|---|---|---|")
            for a in have:
                r = cells[f"{fx}__{a}"]["words"][w]
                lines.append(_row(a, r))
            if fx == "hat925":
                for pro in PRO_FILES:
                    if pro in cells and w in cells[pro]["words"]:
                        lines.append(_row(f"{pro} (reference)", cells[pro]["words"][w]))
            lines.append("")
    return "\n".join(lines)


def _row(name: str, r: dict) -> str:
    if r.get("legibility") is None:
        return f"| {name} | no glyphs read | | | | | |"
    k, n = r["counters_open"]
    return (f"| {name} | {r['legibility']:.3f} | {r['legibility_space']:.3f} | {k} of {n} | "
            f"{fmt_ocr(r['ocr'])} | {'-' if r.get('stitches') is None else r['stitches']} | "
            f"{'-' if r.get('trims') is None else r['trims']} |")


def pick_table(cells: dict[str, dict]) -> str:
    """One line per fixture and arm, for the end of the PR body: stitches,
    trims, mean legibility of each word, and the OCR glyphs recovered over all
    four words with a Wilson 95% interval. No cut-off is claimed anywhere in
    the instrument, so nothing here is a verdict; it is the table to choose
    from."""
    lines = ["| fixture | arm | stitches | trims | mean legibility EST / 1895 / THE / tagline | "
             "OCR glyphs recovered (all four words) |",
             "|---|---|---|---|---|---|"]
    for fx, width in FIXTURES.items():
        for a in ARM_ORDER:
            c = cells.get(f"{fx}__{a}")
            if not c:
                continue
            legs = " / ".join("-" if c["words"][w].get("legibility") is None
                              else f"{c['words'][w]['legibility']:.2f}" for w in WORDS)
            k = sum(c["words"][w]["ocr"].get("recovered") or 0 for w in WORDS)
            n = sum(c["words"][w]["ocr"].get("read") or 0 for w in WORDS)
            ci = wilson(k, n)
            ocr = "n/a" if not n else f"{k}/{n}" + (f" [{ci[0]:.2f}-{ci[1]:.2f}]" if ci else "")
            lines.append(f"| {width:g} mm | {a} | {c['stitches']:,} | {c['trims']} | {legs} | {ocr} |")
    return "\n".join(lines)


# --- one cell ----------------------------------------------------------------------

@contextlib.contextmanager
def spy_tiers(sk: dict, bean: dict):
    """Record every shape stage 7 hands the skeleton tier and the bean-letter
    tier: {shape_id: report}. The runs are returned untouched."""
    from digitizer_core import stage7_sequence as s7
    real_sk, real_bean = s7.skeleton_letter_runs, s7.bean_letter

    def spy_sk(poly, shape_id, **kw):
        runs, report = real_sk(poly, shape_id, **kw)
        sk[shape_id] = dict(report)
        return runs, report

    def spy_bean(spines, shape_id, **kw):
        runs, report = real_bean(spines, shape_id, **kw)
        bean[shape_id] = dict(report)
        return runs, report
    s7.skeleton_letter_runs, s7.bean_letter = spy_sk, spy_bean
    try:
        yield
    finally:
        s7.skeleton_letter_runs, s7.bean_letter = real_sk, real_bean


def _owners(run: dict, glyphs: list) -> dict[int, list[str]]:
    from tools import small_lettering_skeleton as sls
    return sls._owners(run["result"], run["plan"], glyphs)


def built_as(owners: list[str], sk: dict, bean: dict) -> str:
    """How a source glyph's own shapes were sewn: skeleton / bean / outline
    (anything else: the ladder the options leave alone)."""
    if any(s in sk and not sk[s].get("empty") for s in owners):
        return "skeleton"
    if any(s in bean and not bean[s].get("empty") for s in owners):
        return "bean"
    return "outline"


def analyze_run(arm: str, fixture: str, run: dict, sk: dict, bean: dict) -> dict:
    """One digitized cell -> its saved table."""
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    from tools import glyph_legibility as gl
    p = run["gen"].p
    words, _dbg, _reg = gl.read_case("fremont", run["design"], use_ocr=True, words=WORDS)
    census = ft.roi_census(run)
    out_words = {}
    for w in words:
        s = w.summary()
        glyphs = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in g.items()
                   if k in ("legibility", "legibility_space", "strokes", "clean", "counters", "space",
                            "src_counters_openable", "sewn_counters", "sewn_counters_spurious",
                            "ocr_src", "ocr_sewn", "ocr_recovered", "ocr_readable_src", "bbox_mm")}
                  for g in w.glyphs]
        row = word_row(s, glyphs)
        row["stitches"], row["trims"] = census[w.name]["stitches"], census[w.name]["trims"]
        row["box_mm"] = census[w.name]["box_mm"]
        src = fsl.source_glyphs(p, ft.ROIS[w.name])
        owners = _owners(run, src)
        kinds = [built_as(owners[i], sk, bean) for i in range(len(src))]
        row["built"] = {k: kinds.count(k) for k in ("skeleton", "bean", "outline")}
        row["glyph_rows"] = glyphs
        out_words[w.name] = row
    s = run["plan"].stats
    h, wpx = p.bg_mask.shape
    return {"fixture": fixture, "arm": arm, "width_mm": FIXTURES[fixture],
            "label": ARMS[arm][1], "overrides": ARMS[arm][0],
            "stitches": s.stitch_count, "trims": s.trims, "size_mm": [round(v, 1) for v in s.size_mm],
            "skeleton_shapes": sum(1 for r in sk.values() if not r.get("empty")),
            "bean_shapes": sum(1 for r in bean.values() if not r.get("empty")),
            "words": out_words,
            "frame": {"hw": [int(h), int(wpx)], "art_bbox": [float(v) for v in p.art_bbox],
                      "px_per_mm": float(p.px_per_mm)}}


def run_cell(fixture: str, arm: str, out: Path) -> dict:
    """Digitize one arm of one fixture the way /digitize does, read it, save it."""
    from tools import fremont_triage as ft
    overrides = ARMS[arm][0]
    t = time.time()
    sk: dict = {}
    bean: dict = {}
    with spy_tiers(sk, bean):
        run = ft.run_arm(f"{fixture}__{arm}", FIXTURES[fixture], None, preflight=False, overrides=overrides)
    tab = analyze_run(arm, fixture, run, sk, bean)
    tab["secs"] = round(time.time() - t)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{fixture}__{arm}.json").write_text(json.dumps(tab, indent=1))
    (out / f"{fixture}__{arm}_design.json").write_text(json.dumps(run["design"]))
    print(f"{fixture}__{arm}: {tab['stitches']:,} stitches, {tab['trims']} trims, skeleton {tab['skeleton_shapes']}, "
          f"bean {tab['bean_shapes']}, {tab['secs']} s", flush=True)
    for w in WORDS:
        print(f"  {w:8s} {fmt_word(tab['words'][w])}", flush=True)
    return tab


# --- the pro's files -----------------------------------------------------------------

def run_pro(out: Path) -> dict:
    """The pro's Hat and Patch PES, read by the same instrument. No stitch or
    trim split per word: their frame is not ours."""
    from tools import glyph_legibility as gl
    out.mkdir(parents=True, exist_ok=True)
    cells = {}
    with zipfile.ZipFile(PRO_ZIP) as z, tempfile.TemporaryDirectory(prefix="slc_pro_") as tmp:
        for name, member in PRO_FILES.items():
            path = Path(tmp) / Path(member).name
            path.write_bytes(z.read(member))
            design = gl.design_from_pes(path)
            words, _d, _r = gl.read_case("fremont", design, use_ocr=True, words=WORDS)
            recs = design["stitches"]
            xs = [r["x"] for r in recs]
            ys = [r["y"] for r in recs]
            tab = {"fixture": name, "arm": name, "label": f"the pro's {name[4:]} file ({member.rsplit('/', 1)[-1]})",
                   "stitches": sum(1 for r in recs if r["type"] == "stitch"),
                   "trims": sum(1 for r in recs if r["type"] == "trim"),
                   "size_mm": [round((max(xs) - min(xs)) / 10, 1), round((max(ys) - min(ys)) / 10, 1)],
                   "words": {}}
            for w in words:
                s = w.summary()
                row = word_row(s, w.glyphs)
                row["stitches"] = row["trims"] = None
                tab["words"][w.name] = row
            (out / f"{name}.json").write_text(json.dumps(tab, indent=1))
            cells[name] = tab
            print(f"{name}: {tab['size_mm']} mm, {tab['stitches']:,} stitches, {tab['trims']} trims", flush=True)
            for w in WORDS:
                print(f"  {w:8s} {fmt_word(tab['words'][w])}", flush=True)
    return cells


def load_cells(out: Path) -> dict[str, dict]:
    cells = {}
    for p in sorted(out.glob("*.json")):
        if p.stem.endswith("_design"):
            continue
        d = json.loads(p.read_text())
        if "words" in d:
            cells[p.stem] = d
    return cells


# --- render sheets ---------------------------------------------------------------------

SHEET_PPM = {"tagline": 60, "the": 60, "est": 110, "1895": 110}


def sheets(out: Path, renders: Path) -> list[Path]:
    """Per fixture and word: the artwork, then every arm's render over the
    word's box, one px/mm per sheet, the artwork outline in red. A picture of
    the file, thread drawn at its laid width, not of cloth."""
    import cv2
    import numpy as np
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    written = []
    for fx, width in FIXTURES.items():
        have = [a for a in ARM_ORDER if (out / f"{fx}__{a}.json").exists()
                and (out / f"{fx}__{a}_design.json").exists()]
        if not have:
            continue
        rows: dict[str, list] = {w: [] for w in WORDS}
        art: dict[str, object] = {}
        rings: dict = {}
        for ppm in sorted(set(SHEET_PPM.values())):
            word_set = [w for w in WORDS if SHEET_PPM[w] == ppm]
            for a in have:
                tab = json.loads((out / f"{fx}__{a}.json").read_text())
                design = json.loads((out / f"{fx}__{a}_design.json").read_text())
                img, to_px = ft._render(design, ppm)
                fr = tab["frame"]
                p = SimpleNamespace(bg_mask=np.zeros(fr["hw"], np.uint8), art_bbox=fr["art_bbox"],
                                    px_per_mm=fr["px_per_mm"])
                for w in word_set:
                    r = tab["words"][w]
                    box = r["box_mm"]
                    crop = ft._crop(img, to_px, box, margin_mm=0.6).copy()
                    ax, ay = to_px(box[0] - 0.6, box[1] - 0.6)
                    ox, oy = int(max(0, ax)), int(max(0, ay))
                    if (fx, w) not in rings:
                        rings[(fx, w)] = _glyph_rings(p, w)
                    for g in rings[(fx, w)]:
                        pts = np.array([[to_px(x, y)[0] - ox, to_px(x, y)[1] - oy] for x, y in g], np.int32)
                        cv2.polylines(crop, [pts], True, (40, 40, 220), 1, cv2.LINE_AA)
                    ocr = r["ocr"]
                    cap = (f"{a} ({tab['label']}) | built sk {r['built']['skeleton']} bean {r['built']['bean']} "
                           f"outline {r['built']['outline']} | legibility {r['legibility']} +space "
                           f"{r['legibility_space']} | ctr {r['counters_open'][0]}of{r['counters_open'][1]} | "
                           f"OCR {fmt_ocr(ocr)} | st {r['stitches']} tr {r['trims']}")
                    rows[w].append(ft._label(crop, cap))
                    if w not in art:
                        art[w] = ft._label(fsl._source_crop_mm(p, box, 0.6, ppm, (crop.shape[1], crop.shape[0])),
                                           f"artwork, same scale ({ppm} px/mm)")
                del img
        for w in WORDS:
            if w not in art:
                continue
            panels = [art[w]] + rows[w]
            wd = max(x.shape[1] for x in panels)
            sheet = np.vstack([np.pad(x, ((0, 8), (0, wd - x.shape[1]), (0, 0)), constant_values=255)
                               for x in panels])
            sheet = ft._label(sheet, f"{WORD_TITLE[w]} at {width:g} mm (Hat): every row {SHEET_PPM[w]} px/mm, artwork "
                                     "outline red; thread at its laid width, a picture of the file, not of cloth",
                              width=wd)
            path = renders / f"{fx}_{w}.png"
            cv2.imwrite(str(path), sheet)
            written.append(path)
    return written


def _glyph_rings(p, word: str) -> list:
    """The source glyphs' rings (exterior and counters) of `word` in design mm."""
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    rings = []
    for g in fsl.source_glyphs(p, ft.ROIS[word]):
        rings.extend([list(g.exterior.coords), *[list(r.coords) for r in g.interiors]])
    return rings


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cell", nargs=2, metavar=("FIXTURE", "ARM"),
                    help=f"digitize and read one cell; FIXTURE in {list(FIXTURES)}, ARM in {ARM_ORDER}")
    ap.add_argument("--pro", action="store_true", help="read the pro's Hat and Patch files")
    ap.add_argument("--table", action="store_true", help="print the markdown tables from the saved cells")
    ap.add_argument("--pick", action="store_true", help="print the one-line-per-arm table for the PR body")
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.cell:
        fixture, arm = a.cell
        if fixture not in FIXTURES or arm not in ARMS:
            raise SystemExit(f"--cell FIXTURE in {list(FIXTURES)}, ARM in {ARM_ORDER}")
        run_cell(fixture, arm, a.out)
    if a.pro:
        run_pro(a.out)
    if a.table or a.pick:
        cells = load_cells(a.out)
        if a.table:
            print(table(cells))
        if a.pick:
            print(pick_table(cells))
    if a.sheets:
        for pth in sheets(a.out, a.renders or a.out / "renders"):
            print(pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
