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
              (both skeleton arms carry the config's own default for the
              small-glyph second try, `small_lettering_skeleton_small_floor_mm`
              0.5, PR #936: EST and 1895 only reach the skeleton through it)
    true      small_text_restore_mm 3.0 + bean_letter_max_stroke_mm 0.4 +
              bean_letter_stitch_mm 0.45 + bean_letter_serif_mm 0.45
    both073   true + skeleton ON, floor 0.73 (bean letters are tried first,
              so the skeleton run only sees what they decline)
    both100   true + skeleton ON, floor 1.0
    switch    small_text_true_size ON: the true values behind one switch,
              bean stroke 0.5 (THE at 92.5 mm sews as a centre line)

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

The CORPUS cost of the true-size arm (the section "the corpus" below): the same
three arms (main, true, sk073) over the nine corpus logos, Fremont's two Hat
renders and the small-print censuses' two fixtures at 2.5 / 3 / 4 mm caps:

    .venv/Scripts/python -m tools.small_lettering_compare --corpus-list
    .venv/Scripts/python -m tools.small_lettering_compare --corpus becker true --out DIR
    .venv/Scripts/python -m tools.small_lettering_compare --corpus-table --out DIR
    # a render re-run (sidecars in DIR2, the saved cells untouched), then the sheet
    .venv/Scripts/python -m tools.small_lettering_compare --corpus drone true --out DIR --renders DIR2
    .venv/Scripts/python -m tools.small_lettering_compare --corpus-sheet drone --out DIR --renders DIR2
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
    # cfg.small_text_true_size: the four true-size values behind one switch,
    # bean stroke 0.5 (Kent 2026-10-14: THE as a centre line is fine).
    "switch": ({"small_text_true_size": True}, "small_text_true_size ON (bean 0.5)"),
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
        if p.stem.endswith("_design") or p.stem.startswith("corpus_"):
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


# --- the corpus: what the true-size arm COSTS everywhere else --------------------------
#
# #938 found, on Fremont alone, that the true-size arm beats the skeleton on every
# word. Its cost on the rest of the corpus was never read. `--corpus` digitizes ONE
# design under ONE of three arms (every cell its own process), the way the pipeline
# does, and records what a customer would see change: stitches, trims, the md5 of
# the stitch stream (byte-identical or not), which shapes stage 7 laid differently,
# `ARTWORK_UNCOVERED` and the bare-artwork area (preflight's own instrument, whole
# design), and, where `glyph_legibility` can read the design's words (Fremont,
# Becker, Bridge), the legibility and OCR read of each word.
#
# The designs: the nine corpus logos at `thin_strokes.REAL_ART`'s own size and the
# Studio's six colours (the byte-duplicate thermal badge runs once, as the other
# corpus tools do); Fremont's two Hat renders #938 used; and the two fixtures the
# small-print censuses used (the synthetic BOARD 80 word and Fremont's tagline crop)
# at 2.5 / 3 / 4 mm caps, 40 wt. The arms are the two options MASTER_SCOPE 56 names
# (candidates, gate 1); "main" has both off.

CORPUS_ARMS = ["main", "true", "sk073"]
CORPUS_ARM_LABEL = {"main": "main (both off)", "true": "true size", "sk073": "skeleton @ 0.73"}
HAT_CORPUS = {"fremont_hat81": 81.0, "fremont_hat925": PRO_WIDTH_MM}
SMALL_PRINT_CORPUS = ("synthetic", "fremont_tagline")
SMALL_PRINT_CAPS = (2.5, 3.0, 4.0)
# corpus design -> the `glyph_legibility.CASES` entry that can read its words.
LEGIBILITY_CASE = {"fremont": "fremont", "fremont_hat81": "fremont", "fremont_hat925": "fremont",
                   "becker": "becker", "bridge": "bridge"}


def corpus_designs() -> dict[str, dict]:
    """name -> spec, in run order. `kind` is logo / hat / small_print."""
    from tools.thin_strokes import STUDIO_MAX_COLORS, corpus_cases
    out: dict[str, dict] = {}
    for name, path, width, garment in corpus_cases():
        out[name] = {"kind": "logo", "path": str(path),
                     "cfg": {"target_width_mm": width, "garment_id": garment,
                             "max_colors": STUDIO_MAX_COLORS}}
    for name, width in HAT_CORPUS.items():
        out[name] = {"kind": "hat", "width_mm": width}
    for fx in SMALL_PRINT_CORPUS:
        for cap in SMALL_PRINT_CAPS:
            out[f"sp_{fx}_{cap:g}"] = {"kind": "small_print", "fixture": fx, "cap": cap}
    return out


def stream_md5(plan) -> str:
    """The stitch stream's md5, `small_lettering_skeleton.corpus_one`'s own recipe."""
    import hashlib
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def changed_shapes(base: dict[str, str], arm: dict[str, str]) -> int:
    """Shapes stage 7 laid differently: an id whose runs differ, or one that only
    one of the two plans has (the options can retire a shape or add one)."""
    return sum(1 for k in set(base) | set(arm) if base.get(k) != arm.get(k))


def ocr_total(words: dict) -> tuple[int, int]:
    """(recovered, read) summed over a design's words; words with no OCR count 0."""
    k = n = 0
    for w in words.values():
        o = w.get("ocr") or {}
        k += o.get("recovered") or 0
        n += o.get("read") or 0
    return k, n


def mean_legibility(words: dict):
    vals = [w["legibility"] for w in words.values() if w.get("legibility") is not None]
    return None if not vals else sum(vals) / len(vals)


def _digitize(source, cfg_kw: dict) -> dict:
    """Stages 0-7 the way `/digitize` runs them, keeping the pieces the metrics read."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    cfg = PipelineConfig(**cfg_kw)
    gen = build_generation(source, cfg)
    result = finish_generation(gen.fork(), cfg)
    return {"gen": gen, "result": result, "plan": plan_stitches(result, cfg), "cfg": cfg}


def corpus_metrics(run: dict) -> dict:
    """The design-level numbers of one digitized cell (no words)."""
    from digitizer_core import preflight
    from tools.hairline_logo_bill import plan_counts, shape_digests
    from tools.hairline_renders import bare_cells
    plan, result, p = run["plan"], run["result"], run["gen"].p
    counts = plan_counts(plan)
    findings, metrics = preflight._uncovered_findings(p, result, plan)
    unc = next((f for f in findings if f["code"] == preflight.ARTWORK_UNCOVERED), None)
    bare = bare_cells(plan, result, p)
    s = plan.stats
    return {"stitches": s.stitch_count, "trims": s.trims, "jumps": counts["jumps"],
            "thread_m": counts["thread_m"], "size_mm": [round(v, 1) for v in s.size_mm],
            "md5": stream_md5(plan), "shape_digests": shape_digests(plan),
            "uncovered_total_mm2": metrics.get("uncovered_total_mm2"),
            "uncovered_wanted_mm2": metrics.get("uncovered_wanted_mm2"),
            "uncovered_worst_mm2": metrics.get("uncovered_hole_mm2"),
            "uncovered_fires": unc is not None,
            "uncovered_shapes": ([x["shape_id"] for x in unc["extra"]["shapes"]] if unc else []),
            "bare_mm2": round(float(bare[0].sum()) * bare[2] ** 2, 2)}


def corpus_words(case: str, design: dict) -> dict:
    """Every word `glyph_legibility` can read in `design`, as `word_row` rows."""
    from tools import glyph_legibility as gl
    words, _dbg, _reg = gl.read_case(case, design, use_ocr=True)
    out = {}
    for w in words:
        g = [{k: v for k, v in x.items()
              if k in ("legibility", "counters", "src_counters_openable", "sewn_counters_spurious")}
             for x in w.glyphs]
        out[w.name] = word_row(w.summary(), g)
    return out


def _digitize_small_print(spec: dict, overrides: dict, out: Path):
    """A small-print census cell: the fixture scaled so its reference line lands
    at `cap` mm, 40 wt. Also reads the census's own counters (the instrument the
    small-print censuses used) from the same cfg."""
    from digitizer_core import PipelineConfig
    from tools import small_print
    fx, cap = spec["fixture"], spec["cap"]
    image = small_print.load(fx)
    ref_path = out / f"sp_ref_{fx}.json"
    if fx == "synthetic":
        ref = json.loads((ROOT / "testdata" / "small_print_synthetic_ref.json").read_text())
    elif ref_path.exists():
        ref = json.loads(ref_path.read_text())
    else:
        ref = small_print.reference(image, PipelineConfig(target_width_mm=small_print.FIXTURES[fx][2]),
                                    small_print.FIXTURES[fx][1])
        out.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(json.dumps(ref))
    kw = {"target_width_mm": round(cap / ref["cap"], 2), **overrides}
    run = _digitize(image, kw)
    m, _ = small_print.measure(image, run["cfg"], ref)
    keep = ("width_mm", "cap_mm", "counters", "counters_shut", "counter_open", "covered", "spill", "dust")
    extra = {"sp": {k: (None if isinstance(m[k], float) and math.isnan(m[k]) else m[k]) for k in keep}}
    return run, extra


def _corpus_sidecar(name: str, arm: str, run: dict, sk: dict, bean: dict, out: Path, renders: Path) -> dict:
    """What a render sheet needs: the design, and (for an option arm) which shapes
    stage 7 laid differently from the saved main cell, their area, box and tier
    reports. The saved cells are not rewritten."""
    from digitizer_core.adapter import plan_to_design
    from tools.hairline_logo_bill import shape_digests
    renders.mkdir(parents=True, exist_ok=True)
    (renders / f"corpus_{name}__{arm}_design.json").write_text(
        json.dumps(plan_to_design(run["plan"], name=name)))
    main_cell = out / f"corpus_{name}__main.json"
    base = json.loads(main_cell.read_text())["shape_digests"] if arm != "main" and main_cell.exists() else {}
    now = shape_digests(run["plan"])
    by = {r.shape_id: r for r in run["result"].regions}
    shapes = []
    for sid in sorted(k for k in set(base) | set(now) if base and base.get(k) != now.get(k)):
        r = by.get(sid)
        if r is None:
            continue
        shapes.append({"shape_id": sid, "area_mm2": round(r.polygon.area, 2),
                       "bounds_mm": [round(v, 2) for v in r.polygon.bounds],
                       "bean": bean.get(sid), "skeleton": sk.get(sid)})
    box = ([min(s["bounds_mm"][0] for s in shapes), min(s["bounds_mm"][1] for s in shapes),
            max(s["bounds_mm"][2] for s in shapes), max(s["bounds_mm"][3] for s in shapes)]
           if shapes else None)
    side = {"design": name, "arm": arm, "box_mm": box, "changed_shapes": shapes}
    (renders / f"corpus_{name}__{arm}_changed.json").write_text(json.dumps(side, indent=1, default=str))
    print(f"{name}__{arm}: {len(shapes)} changed shapes, box {box}", flush=True)
    return side


def corpus_sheet(name: str, out: Path, renders: Path, ppm: float = 30.0):
    """Every arm of one design over the box of the shapes the options changed
    (the whole design when none changed), one px/mm, the saved cell's numbers in
    each caption."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    cells = load_corpus(out).get(name, {})
    arms = [a for a in CORPUS_ARMS if (renders / f"corpus_{name}__{a}_design.json").exists()]
    boxes = [json.loads(p.read_text())["box_mm"] for a in arms
             if (p := renders / f"corpus_{name}__{a}_changed.json").exists()]
    boxes = [b for b in boxes if b]
    rows = []
    box = None
    if boxes:
        box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        ppm = min(ppm, 1700.0 / max(box[2] - box[0], box[3] - box[1], 1.0))
    for a in arms:
        design = json.loads((renders / f"corpus_{name}__{a}_design.json").read_text())
        img, to_px = ft._render(design, ppm)
        crop = img if box is None else ft._crop(img, to_px, box, margin_mm=1.0)
        c = cells.get(a)
        cap = f"{name} | {CORPUS_ARM_LABEL[a]}"
        if c:
            cap += f" | {c['stitches']:,} st, {c['trims']} tr, uncovered {c['uncovered_total_mm2']} mm2, bare {c['bare_mm2']} mm2"
        rows.append(ft._label(crop, cap))
    if not rows:
        return None
    w = max(r.shape[1] for r in rows)
    sheet = np.vstack([np.pad(r, ((0, 8), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    sheet = ft._label(sheet, f"{name}: every row {ppm:.0f} px/mm over the shapes the options changed; thread at its "
                             "laid width, a picture of the file, not of cloth", width=w)
    path = renders / f"corpus_{name}.png"
    cv2.imwrite(str(path), sheet)
    return path


def corpus_cell(name: str, arm: str, out: Path, renders: Path | None = None) -> dict:
    """Digitize one corpus design under one arm and save its record. With
    `renders`, a re-run for the render sheets instead (`_corpus_sidecar`)."""
    from digitizer_core.adapter import plan_to_design
    spec = corpus_designs()[name]
    overrides = ARMS[arm][0]
    t = time.time()
    sk: dict = {}
    bean: dict = {}
    extra: dict = {}
    with spy_tiers(sk, bean):
        if spec["kind"] == "logo":
            run = _digitize(spec["path"], {**spec["cfg"], **overrides})
        elif spec["kind"] == "hat":
            from tools import fremont_triage as ft
            run = ft.run_arm(name, spec["width_mm"], None, preflight=False, overrides=overrides)
        else:
            run, extra = _digitize_small_print(spec, overrides, out)
    if renders is not None:         # a render re-run: sidecars only, the saved cell stays as it is
        return _corpus_sidecar(name, arm, run, sk, bean, out, renders)
    rec = {"design": name, "arm": arm, "kind": spec["kind"], "overrides": overrides,
           **corpus_metrics(run), "skeleton_shapes": sum(1 for r in sk.values() if not r.get("empty")),
           "bean_shapes": sum(1 for r in bean.values() if not r.get("empty")), **extra}
    case = LEGIBILITY_CASE.get(name)
    rec["words"] = corpus_words(case, plan_to_design(run["plan"], name=name)) if case else {}
    rec["secs"] = round(time.time() - t)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"corpus_{name}__{arm}.json").write_text(json.dumps(rec, indent=1))
    print(f"{name}__{arm}: {rec['stitches']:,} st, {rec['trims']} tr, md5 {rec['md5'][:8]}, "
          f"AU {rec['uncovered_total_mm2']} mm2, bare {rec['bare_mm2']} mm2, skeleton {rec['skeleton_shapes']}, "
          f"bean {rec['bean_shapes']}, {rec['secs']} s", flush=True)
    for w, r in rec["words"].items():
        print(f"  {w:8s} leg {r['legibility']} OCR {fmt_ocr(r['ocr'])}", flush=True)
    return rec


def load_corpus(out: Path) -> dict[str, dict[str, dict]]:
    """{design: {arm: record}} from the saved corpus cells."""
    cells: dict[str, dict[str, dict]] = {}
    for p in sorted(out.glob("corpus_*__*.json")):
        d = json.loads(p.read_text())
        cells.setdefault(d["design"], {})[d["arm"]] = d
    return cells


def _ordered(cells: dict) -> list[str]:
    order = list(corpus_designs())
    return sorted(cells, key=lambda n: order.index(n) if n in order else len(order))


def corpus_deltas(cells: dict) -> list[dict]:
    """One row per design and non-main arm, against that design's main cell."""
    rows = []
    for name in _ordered(cells):
        base = cells[name].get("main")
        if not base:
            continue
        for arm in CORPUS_ARMS[1:]:
            c = cells[name].get(arm)
            if not c:
                continue
            bw, cw = base["words"], c["words"]
            legs = {w: round(cw[w]["legibility"] - bw[w]["legibility"], 3)
                    for w in cw if w in bw and cw[w].get("legibility") is not None
                    and bw[w].get("legibility") is not None}
            rows.append({
                "design": name, "arm": arm, "identical": c["md5"] == base["md5"],
                "d_stitches": c["stitches"] - base["stitches"], "d_trims": c["trims"] - base["trims"],
                "d_stitch_pct": 100.0 * (c["stitches"] - base["stitches"]) / max(base["stitches"], 1),
                "changed": changed_shapes(base["shape_digests"], c["shape_digests"]),
                "d_au": round((c["uncovered_total_mm2"] or 0) - (base["uncovered_total_mm2"] or 0), 2),
                "d_bare": round(c["bare_mm2"] - base["bare_mm2"], 2),
                "d_leg": legs})
    return rows


def _cnt(c: dict) -> str:
    return f"{c['stitches']:,} / {c['trims']}"


def corpus_table(cells: dict) -> str:
    """The PR table: per design, main vs true size vs skeleton @ 0.73."""
    lines = ["| design | main st / tr | true size st / tr | same? | shapes changed | dAU mm2 | dBare mm2 | "
             "skeleton@0.73 st / tr | same? | shapes changed | dAU mm2 | dBare mm2 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    by = {(r["design"], r["arm"]): r for r in corpus_deltas(cells)}
    for name in _ordered(cells):
        base = cells[name].get("main")
        if not base:
            continue
        cols = [name, _cnt(base)]
        for arm in CORPUS_ARMS[1:]:
            c, d = cells[name].get(arm), by.get((name, arm))
            if not c or not d:
                cols += ["-"] * 5
                continue
            cols += [_cnt(c), "yes" if d["identical"] else "NO", str(d["changed"]),
                     f"{d['d_au']:+.2f}", f"{d['d_bare']:+.2f}"]
        lines.append("| " + " | ".join(cols) + " |")
    return "\n".join(lines)


def corpus_legibility_table(cells: dict) -> str:
    """Per design `glyph_legibility` can read: mean legibility, the worst word and
    the OCR glyphs recovered (Wilson 95%) per arm."""
    lines = ["| design | arm | words | mean legibility | worst word | OCR glyphs recovered (Wilson 95%) |",
             "|---|---|---|---|---|---|"]
    for name in _ordered(cells):
        for arm in CORPUS_ARMS:
            c = cells[name].get(arm)
            if not c or not c["words"]:
                continue
            m = mean_legibility(c["words"])
            vals = {w: r["legibility"] for w, r in c["words"].items() if r.get("legibility") is not None}
            worst = min(vals, key=vals.get) if vals else None
            k, n = ocr_total(c["words"])
            ci = wilson(k, n)
            ocr = "n/a" if not n else f"{k}/{n}" + (f" [{ci[0]:.2f}-{ci[1]:.2f}]" if ci else "")
            lines.append(f"| {name} | {arm} | {len(c['words'])} | "
                         f"{'-' if m is None else f'{m:.3f}'} | "
                         f"{'-' if worst is None else f'{worst} {vals[worst]:.3f}'} | {ocr} |")
    return "\n".join(lines)


def corpus_small_print_table(cells: dict) -> str:
    """The small-print rows read by the censuses' own instrument
    (`small_print.measure`): counters still shut / of source, the share of counter
    area open, source letters covered by thread, thread spilled outside them."""
    lines = ["| design | arm | counters shut / of | counter area open | source covered | spill |",
             "|---|---|---|---|---|---|"]
    for name in _ordered(cells):
        for arm in CORPUS_ARMS:
            sp = (cells[name].get(arm) or {}).get("sp")
            if not sp:
                continue

            def f(k):
                return "-" if sp.get(k) is None else f"{sp[k]:.2f}"
            lines.append(f"| {name} | {arm} | {sp['counters_shut']} / {sp['counters']} | "
                         f"{f('counter_open')} | {f('covered')} | {f('spill')} |")
    return "\n".join(lines)


def _worst(value, fmt: str, design: str) -> str:
    """A regression cell: 'none' when the worst change anywhere is zero or an improvement."""
    return "no increase anywhere" if value <= 0 else f"worst {fmt.format(value)} ({design})"


def worst_regressions(cells: dict) -> list[str]:
    """One plain line per non-main arm: the worst thing it does anywhere."""
    rows = corpus_deltas(cells)
    out = []
    for arm in CORPUS_ARMS[1:]:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        moved = [r for r in rs if not r["identical"]]
        parts = [f"{CORPUS_ARM_LABEL[arm]} changed {len(moved)} of {len(rs)} designs"]
        if moved:
            a = max(rs, key=lambda r: r["d_au"])
            t = max(rs, key=lambda r: r["d_trims"])
            s = max(rs, key=lambda r: r["d_stitch_pct"])
            parts.append(f"new uncovered artwork: {_worst(a['d_au'], '{:+.2f} mm2', a['design'])}")
            parts.append(f"trims: {_worst(t['d_trims'], '{:+d}', t['design'])}")
            parts.append(f"stitches: {_worst(s['d_stitch_pct'], '{:+.1f}%', s['design'])}")
            legs = [(v, r["design"], w) for r in rs for w, v in r["d_leg"].items()]
            if legs:
                v, d, w = min(legs)
                parts.append("legibility: " + ("never lower" if v >= 0 else f"worst {v:+.3f} ({d} {w})"))
        out.append("; ".join(parts))
    return out


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
    ap.add_argument("--corpus", nargs=2, metavar=("DESIGN", "ARM"),
                    help="digitize one corpus design under one arm (ARM in %s); see the corpus section" % CORPUS_ARMS)
    ap.add_argument("--corpus-list", action="store_true", help="print the corpus design names")
    ap.add_argument("--corpus-sheet", metavar="DESIGN",
                    help="render sheet of one design from the --renders sidecars (written by --corpus ... --renders)")
    ap.add_argument("--corpus-table", action="store_true",
                    help="print the corpus tables and the worst-regression lines from the saved cells")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.corpus_list:
        print("\n".join(corpus_designs()))
        return 0
    if a.out is None:
        ap.error("--out is required")
    if a.corpus:
        design, arm = a.corpus
        if design not in corpus_designs() or arm not in CORPUS_ARMS:
            raise SystemExit(f"--corpus DESIGN in {list(corpus_designs())}, ARM in {CORPUS_ARMS}")
        corpus_cell(design, arm, a.out, a.renders)
    if a.corpus_sheet:
        print(corpus_sheet(a.corpus_sheet, a.out, a.renders or a.out / "renders"))
    if a.corpus_table:
        cc = load_corpus(a.out)
        print(corpus_table(cc), "", corpus_legibility_table(cc), "", corpus_small_print_table(cc), "",
              *worst_regressions(cc), sep="\n")
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
