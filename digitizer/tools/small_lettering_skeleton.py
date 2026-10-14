"""Small lettering as ONE skeleton run (`cfg.small_lettering_skeleton`, OFF):
what it sews on Hotel Fremont at Kent's 81 mm Hat replay, and that it moves
nothing on the corpus.

PR #905 (`tools/fremont_small_lettering.py`) found that no existing flag
changes how the tagline (EAT | STAY | PLAY) and EST sew at 81 mm: strokes of
0.22-0.30 mm, under the 0.40 mm a 40 wt strand lays, each sewn as a bean run
on its OUTLINE (1.6-3.2x the stroke, counters shut). The new tier
(`digitizer_core/stage6_small_letter.py`) sews such a glyph as one run down
its medial axis. This measures it, per glyph, with #905's reader
(`fremont_small_lettering.glyph_row`: tier, counters still bare, sewn width)
and the legibility instrument (`glyph_legibility.read_case`: strokes,
clean, counters per glyph). Fremont is UNREPRESENTATIVE: it reproduces the
defect, it sizes nothing. Every number the tier uses is a candidate (gate 1).

Arms (the Studio request of `fremont_triage.studio_request`, Hat, 81 mm):

    off_81      main, the flag off
    on_81       small_lettering_skeleton ON, the needle floor (1.0 mm)
    on073_81    ON, floor 0.73 mm (`machine.BEAN_STITCH_MM`, the run tier's
                own stitch on these glyphs today)

    # one arm at a time (a digitize is minutes and gigabytes; ONE process)
    .venv/Scripts/python -m tools.small_lettering_skeleton --arm on_81 --out DIR
    .venv/Scripts/python -m tools.small_lettering_skeleton --analyze --out DIR
    .venv/Scripts/python -m tools.small_lettering_skeleton --sheets --out DIR --renders DIR2
    # the corpus: stitch-stream md5 OFF vs ON, one case and arm per call
    .venv/Scripts/python -m tools.small_lettering_skeleton --corpus becker --corpus-arm on --out DIR
    .venv/Scripts/python -m tools.small_lettering_skeleton --corpus-table --out DIR
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FLAG = {"small_lettering_skeleton": True}
ARMS = {
    "off_81": (81.0, {}, "main (flag off)"),
    "on_81": (81.0, dict(FLAG), "ON, floor 1.0 mm (MIN_STITCH_MM)"),
    "on073_81": (81.0, {**FLAG, "small_lettering_skeleton_floor_mm": 0.73},
                 "ON, floor 0.73 mm (BEAN_STITCH_MM)"),
}
ARM_ORDER = list(ARMS)
BOXES = ["the", "tagline", "est"]
LEGIBILITY_WORDS = ["the", "tagline", "est"]

# The corpus the brief names, at 80 mm on a left chest (`thin_strokes.REAL_ART`
# paths; becker at 80 here, not its 100).
CORPUS = {
    "becker": "becker_marine_logo.png",
    "bridge": "photo/logo_bridge_bar.jpg",
    "enthusiast": "photo/enthusiast_logo.png",
    "golden_tee": "photo/logo_golden_tee.jpg",
    "drone": "photo/drone_render.png",
}
CORPUS_WIDTH_MM = 80.0
CORPUS_ARMS = {"off": {}, "on": dict(FLAG),
               "on073": {**FLAG, "small_lettering_skeleton_floor_mm": 0.73}}


@contextlib.contextmanager
def spy_skeleton(log: dict):
    """Record every glyph stage 7 offers the tier: {shape_id: report}."""
    from digitizer_core import stage7_sequence as s7
    real = s7.skeleton_letter_runs

    def spy(poly, shape_id, **kw):
        runs, report = real(poly, shape_id, **kw)
        log[shape_id] = {k: v for k, v in report.items()}
        return runs, report
    s7.skeleton_letter_runs = spy
    try:
        yield log
    finally:
        s7.skeleton_letter_runs = real


def run_one(name: str, out: Path) -> Path:
    """Digitize one Fremont arm the way /digitize does and pickle it."""
    from tools import fremont_triage as ft
    width, overrides, _label = ARMS[name]
    t = time.time()
    log: dict = {}
    with spy_skeleton(log):
        run = ft.run_arm(name, width, None, preflight=False, overrides=overrides)
    run["skeleton"] = log
    out.mkdir(parents=True, exist_ok=True)
    pk = out / f"{name}.pkl"
    pk.write_bytes(pickle.dumps(run))
    s = run["plan"].stats
    sewn = sum(1 for r in log.values() if not r["empty"])
    print(f"{name}: {s.stitch_count:,} stitches, {s.trims} trims, offered {len(log)}, "
          f"skeleton {sewn}, {time.time() - t:.0f} s -> {pk}", flush=True)
    return pk


def _owners(result, plan, glyphs) -> dict[int, list[str]]:
    """Source glyph index -> the shape ids sewn over it (#905's rule: the
    region overlapping the glyph most, by over a fifth of the smaller)."""
    from tools import fremont_triage as ft
    nonwhite = [r for r in result.regions if min(ft._thread_rgb(r, plan)) < ft.WHITE_MIN]
    owners: dict[int, list] = {i: [] for i in range(len(glyphs))}
    for r in nonwhite:
        best, bi = 0.0, None
        for i, g in enumerate(glyphs):
            a = r.polygon.intersection(g).area if r.polygon.intersects(g) else 0.0
            if a > best:
                best, bi = a, i
        if bi is not None and best > 0.2 * min(r.polygon.area, glyphs[bi].area):
            owners[bi].append(r.shape_id)
    return owners


def analyze_arm(name: str, run: dict) -> dict:
    """Per glyph per box: #905's row, plus how the tier treated it
    (`construction`: skeleton / declined:<why> / outline), plus the
    legibility instrument per word and glyph."""
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    from tools import glyph_legibility as gl
    p = run["gen"].p
    result, plan = run["result"], run["plan"]
    taken = set(run["taken"])
    log = run.get("skeleton", {})
    boxes = {}
    for b in BOXES:
        glyphs = fsl.source_glyphs(p, ft.ROIS[b])
        owners = _owners(result, plan, glyphs)
        rows = []
        for i, g in enumerate(glyphs):
            row = fsl.glyph_row(run, g, f"{b}[{i}]", owners[i], taken, False)
            row["label"] = fsl.label_of(b, i, len(glyphs))
            reps = [log[s] for s in owners[i] if s in log]
            if any(not r["empty"] for r in reps):
                row["construction"] = "skeleton"
            elif reps:
                row["construction"] = "declined:" + ",".join(sorted({str(r["declined"]) for r in reps}))
            else:
                row["construction"] = "not offered"
            row["skeleton_report"] = {k: v for r in reps for k, v in r.items()
                                      if k in ("width_mm", "stitches", "min_stitch_mm", "counter_crossings",
                                               "counter_depth_mm", "outside_mm", "missed_share",
                                               "retrace_mm", "declined")}
            rows.append(row)
        boxes[b] = {"glyphs": rows}
    census = ft.roi_census(run)
    for b in BOXES:
        for k in ("box_mm", "ink_mm2", "ink_bare_mm2", "stitches", "trims"):
            boxes[b][k] = census[b][k]
    words, _dbg, _reg = gl.read_case("fremont", run["design"], use_ocr=False, words=LEGIBILITY_WORDS)
    leg = {}
    for w in words:
        leg[w.name] = {"summary": w.summary(),
                       "glyphs": [{k: (round(v, 3) if isinstance(v, float) else v)
                                   for k, v in x.items()
                                   if k in ("legibility", "legibility_space", "strokes", "clean",
                                            "counters", "space", "euler_match", "width")}
                                  for x in w.glyphs]}
    s = plan.stats
    width, overrides, label = ARMS[name]
    return {"arm": name, "label": label, "width_mm": width, "overrides": overrides,
            "size_mm": [round(v, 1) for v in s.size_mm], "stitches": s.stitch_count,
            "trims": s.trims, "offered": len(log),
            "skeleton_sewn": sum(1 for r in log.values() if not r["empty"]),
            "declined": {k: sum(1 for r in log.values() if r["declined"] == k)
                         for k in ("width", "empty", "counter", "shape")},
            "boxes": boxes, "legibility": leg}


def markdown(tabs: dict) -> str:
    lines = []
    for b in BOXES:
        lines.append(f"### {'EAT | STAY | PLAY' if b == 'tagline' else b.upper()}\n")
        lines.append("| arm | " + " | ".join(g["label"] for g in tabs[ARM_ORDER[0]]["boxes"][b]["glyphs"]) + " |")
        lines.append("|---|" + "---|" * len(tabs[ARM_ORDER[0]]["boxes"][b]["glyphs"]))
        for name, tab in tabs.items():
            cells = []
            for g in tab["boxes"][b]["glyphs"]:
                c = {"skeleton": "SK", "not offered": "-"}.get(g["construction"],
                                                             "d:" + g["construction"].split(":")[-1])
                cs = "/".join(f"{x['bare_share']:.2f}" for x in g["counters"])
                cells.append(f"{c} {g['sewn_w_mm']:.2f}" + (f" [{cs}]" if cs else ""))
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines.append("")
    lines.append("| arm | stitches | trims | offered | skeleton | declined (width/empty/counter/shape) | "
                 + " | ".join(f"{w} legibility (worst)" for w in LEGIBILITY_WORDS) + " |")
    lines.append("|---|---|---|---|---|---|" + "---|" * len(LEGIBILITY_WORDS))
    for name, tab in tabs.items():
        d = tab["declined"]
        leg = " | ".join(f"{tab['legibility'][w]['summary']['legibility']} "
                         f"({tab['legibility'][w]['summary']['worst_glyph']})"
                         if w in tab["legibility"] else "-" for w in LEGIBILITY_WORDS)
        lines.append(f"| {name} | {tab['stitches']:,} | {tab['trims']} | {tab['offered']} | "
                     f"{tab['skeleton_sewn']} | {d['width']}/{d['empty']}/{d['counter']}/{d['shape']} | {leg} |")
    return "\n".join(lines)


# --- the corpus ----------------------------------------------------------------

def corpus_one(case: str, arm: str, out: Path) -> dict:
    """Digitize one corpus case at 80 mm (left chest) under one arm; -> its
    stitch-stream md5 and what the tier was offered."""
    from digitizer_core import PipelineConfig
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import digitize
    t = time.time()
    log: dict = {}
    cfg = PipelineConfig(target_width_mm=CORPUS_WIDTH_MM, garment_id="left_chest",
                         **CORPUS_ARMS[arm])
    with spy_skeleton(log):
        result, plan = digitize(ROOT / "testdata" / CORPUS[case], cfg)
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    by = {r.shape_id: r for r in result.regions}
    bounds = [by[s].polygon.bounds for s in log if s in by]
    rec = {"case": case, "arm": arm, "md5": hashlib.md5(json.dumps(coords).encode()).hexdigest(),
           "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
           "offered": len(log), "skeleton_sewn": sum(1 for r in log.values() if not r["empty"]),
           "declined": sorted(str(r["declined"]) for r in log.values() if r["empty"]),
           "offered_box_mm": ([round(min(b[0] for b in bounds), 2), round(min(b[1] for b in bounds), 2),
                               round(max(b[2] for b in bounds), 2), round(max(b[3] for b in bounds), 2)]
                              if bounds else None),
           "secs": round(time.time() - t, 1)}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"corpus_{case}_{arm}.json").write_text(json.dumps(rec, indent=1))
    (out / f"corpus_{case}_{arm}_design.json").write_text(json.dumps(plan_to_design(plan, name=case)))
    print(json.dumps(rec), flush=True)
    return rec


def corpus_table(out: Path) -> str:
    lines = ["| case (80 mm) | OFF md5 | ON md5 | ON 0.73 md5 | offered ON | skeleton ON / ON 0.73 | identical |",
             "|---|---|---|---|---|---|---|"]
    for case in CORPUS:
        recs = {a: json.loads((out / f"corpus_{case}_{a}.json").read_text())
                for a in CORPUS_ARMS if (out / f"corpus_{case}_{a}.json").exists()}
        if "off" not in recs:
            continue
        md = {a: recs[a]["md5"][:8] if a in recs else "-" for a in CORPUS_ARMS}
        same = all(recs[a]["md5"] == recs["off"]["md5"] for a in recs)
        lines.append(f"| {case} | {md['off']} | {md['on']} | {md['on073']} | "
                     f"{recs.get('on', {}).get('offered', '-')} | "
                     f"{recs.get('on', {}).get('skeleton_sewn', '-')} / "
                     f"{recs.get('on073', {}).get('skeleton_sewn', '-')} | {'yes' if same else 'NO'} |")
    return "\n".join(lines)


def corpus_sheet(case: str, out: Path, renders: Path, ppm: int = 60) -> Path | None:
    """A corpus case the tier changed: every arm over the box of the glyphs it
    was offered, one px/mm, stacked."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    recs = {a: json.loads((out / f"corpus_{case}_{a}.json").read_text())
            for a in CORPUS_ARMS if (out / f"corpus_{case}_{a}_design.json").exists()}
    box = next((r["offered_box_mm"] for r in recs.values() if r.get("offered_box_mm")), None)
    if box is None:
        return None
    rows = []
    for a, rec in recs.items():
        design = json.loads((out / f"corpus_{case}_{a}_design.json").read_text())
        img, to_px = ft._render(design, ppm)
        crop = ft._crop(img, to_px, box, margin_mm=0.8)
        rows.append(ft._label(crop, f"{case} 80 mm, {a} ({CORPUS_ARMS[a] or 'flag off'}) | "
                                    f"st {rec['stitches']} tr {rec['trims']} | offered {rec['offered']}, "
                                    f"skeleton {rec['skeleton_sewn']}"))
    w = max(r.shape[1] for r in rows)
    sheet = np.vstack([np.pad(r, ((0, 8), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    sheet = ft._label(sheet, f"{case} at 80 mm (left chest): every row {ppm} px/mm, thread at its laid width",
                      width=w)
    renders.mkdir(parents=True, exist_ok=True)
    path = renders / f"corpus_{case}.png"
    cv2.imwrite(str(path), sheet)
    return path


# --- render sheets -----------------------------------------------------------

SHEET_PPM = 60
ZOOM_PPM = 150


def sheets(out: Path, renders: Path) -> list[Path]:
    """Per box, the artwork then every arm at one px/mm; and a zoom of the
    tagline and EST at 150 px/mm with the artwork outline in red."""
    import cv2
    import numpy as np
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    written = []
    for ppm, boxes, tag in ((SHEET_PPM, BOXES, "arms"), (ZOOM_PPM, ["tagline", "est"], "zoom")):
        rows: dict[str, list] = {b: [] for b in boxes}
        art: dict = {}
        for name in ARM_ORDER:
            pk, tj = out / f"{name}.pkl", out / f"{name}_table.json"
            if not (pk.exists() and tj.exists()):
                continue
            run = pickle.loads(pk.read_bytes())          # our own scratch file
            tab = json.loads(tj.read_text())
            img, to_px = ft._render(run["design"], ppm)
            p = run["gen"].p
            for b in boxes:
                box = tab["boxes"][b]["box_mm"]
                crop = ft._crop(img, to_px, box, margin_mm=0.6).copy()
                if tag == "zoom":
                    a = to_px(box[0] - 0.6, box[1] - 0.6)
                    ox, oy = int(max(0, a[0])), int(max(0, a[1]))
                    for g in fsl.source_glyphs(p, ft.ROIS[b]):
                        for ring in [g.exterior, *g.interiors]:
                            pts = np.array([[to_px(x, y)[0] - ox, to_px(x, y)[1] - oy]
                                            for x, y in ring.coords], np.int32)
                            cv2.polylines(crop, [pts], True, (40, 40, 220), 1, cv2.LINE_AA)
                kinds = " ".join({"skeleton": "K"}.get(g["construction"], "o") for g in tab["boxes"][b]["glyphs"])
                leg = tab["legibility"].get(b, {}).get("summary", {})
                cap = (f"{name} ({tab['label']}) | K skeleton, o outline: {kinds} | "
                       f"st {tab['boxes'][b]['stitches']} tr {tab['boxes'][b]['trims']} | "
                       f"legibility {leg.get('legibility')} worst {leg.get('worst_glyph')}")
                rows[b].append(ft._label(crop, cap))
                if b not in art:
                    art[b] = ft._label(fsl._source_crop_mm(p, box, 0.6, ppm, (crop.shape[1], crop.shape[0])),
                                       f"artwork, same scale ({ppm} px/mm)")
            del img, run
        for b in boxes:
            if b not in art:
                continue
            panels = [art[b]] + rows[b]
            w = max(x.shape[1] for x in panels)
            sheet = np.vstack([np.pad(x, ((0, 8), (0, w - x.shape[1]), (0, 0)), constant_values=255)
                               for x in panels])
            title = {"the": "THE", "tagline": "EAT | STAY | PLAY", "est": "EST"}[b]
            extra = ", artwork outline red" if tag == "zoom" else ""
            sheet = ft._label(sheet, f"{title} at 81 mm (Hat): every row {ppm} px/mm{extra}; "
                                     "thread drawn at its laid width, a picture of the file, not of cloth",
                              width=w)
            path = renders / f"{tag}_{b}.png"
            cv2.imwrite(str(path), sheet)
            written.append(path)
    return written


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", choices=ARM_ORDER)
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--corpus", choices=list(CORPUS))
    ap.add_argument("--corpus-arm", choices=list(CORPUS_ARMS), default="on")
    ap.add_argument("--corpus-table", action="store_true")
    ap.add_argument("--corpus-sheet", choices=list(CORPUS))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.arm:
        run_one(a.arm, a.out)
    if a.analyze:
        for name in ARM_ORDER:
            pk = a.out / f"{name}.pkl"
            if not pk.exists():
                continue
            res = analyze_arm(name, pickle.loads(pk.read_bytes()))   # our own scratch file
            (a.out / f"{name}_table.json").write_text(json.dumps(res, indent=1))
            print(f"{name}: analysed", flush=True)
    if a.markdown:
        tabs = {n: json.loads((a.out / f"{n}_table.json").read_text())
                for n in ARM_ORDER if (a.out / f"{n}_table.json").exists()}
        print(markdown(tabs))
    if a.corpus:
        corpus_one(a.corpus, a.corpus_arm, a.out)
    if a.corpus_table:
        print(corpus_table(a.out))
    if a.corpus_sheet:
        print(corpus_sheet(a.corpus_sheet, a.out, a.renders or a.out / "renders"))
    if a.sheets:
        for pth in sheets(a.out, a.renders or a.out / "renders"):
            print(pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
