"""Lock stitches on small letters: count them, weigh the thread they pile.

The scout's count (2026-10-14) was a heuristic: 31 A,B,A,B,A bounces in Hotel
Fremont's four small-lettering boxes at 81 mm, legs 0.14-0.80 mm, on glyphs
2.9 mm tall with 0.2 mm strokes. A bounce is `stitches.tie_run`'s lock, folded
by `stitches.apply_ties` into the run it protects -- leg = min(`TIE_STITCH_MM`
0.8, the first stitch), four legs, so at the 0.45 mm bean-letter pitch a lock
is 1.8 mm of thread on ONE station gap, at both ends of every trimmed letter.
`bean_glyph_trace` (PR #953) labels those points by the bounce pattern
(`strip_ties`' rule); that cannot see a lock that is NOT a bounce, which is
what `cfg.small_letter_ties` lays. So this tool reads ties at their source:
it wraps `apply_ties` (stage 7's `_apply_ties` alias and the module function)
and records, per run, the points the call added before and after the run's own
points -- a laid lock is exactly those, whatever its shape -- and the slots
where the rule asked for a lock and none was laid (a three-pass bean that
already sews over its own opening stitch, `stitches.opened_by_retrace`).

Per word box (EST, 1895, THE, the EAT | STAY | PLAY tagline: `fremont_triage
.ROIS`) and per source glyph (`fremont_small_lettering.source_glyphs`, the tie
going to the glyph nearest its anchor): ties laid, slots left untied, leg
lengths, thread mm, the thread they PILE at 0.4 mm (thread mm x 0.4, overlaps
counted, which is what stacks on a 0.2 mm stroke) and their FOOTPRINT (the
union of the legs at 0.4 mm). Plus, for the same render, the reader every
small-lettering lane uses (`glyph_legibility.read_case`: legibility, legibility
with negative space, OCR with a Wilson interval) and the stitches / trims whose
needle points fall in each box (`fremont_triage.roi_census`).

    # one Fremont cell (Studio Hat request, `fremont_triage.run_arm`) under --set overrides
    python -m tools.small_letter_ties --cell hat81 --tag switch --set small_text_true_size=true --out DIR
    python -m tools.small_letter_ties --cell hat81 --tag ties --set small_text_true_size=true \\
        --set small_letter_ties=true --out DIR
    # a corpus logo (the nine `thin_strokes.corpus_cases`), same --set
    python -m tools.small_letter_ties --logo becker --tag switch --set small_text_true_size=true --out DIR
    # the before/after table, and the render (tie legs drawn red over the file's render)
    python -m tools.small_letter_ties --table --before switch --after ties --out DIR
    python -m tools.small_letter_ties --render --before switch --after ties --out DIR --renders DIR2

Measure only: no engine value is set here. Every number is a picture of the
file, not of cloth (ROADMAP gate 1); `stitchviz` draws a three-pass bean as ONE
thread width, so a bean render under-draws the sewn weight.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THREAD_MM = 0.4          # 40 wt laid width: the pile and footprint are read at it
FIXTURES = {"hat81": 81.0, "hat925": 92.5}
WORDS = ["est", "1895", "the", "tagline"]
RENDER_PPM = {"est": 110, "1895": 110, "the": 60, "tagline": 60}


# --- pure helpers (the tests pin these) -------------------------------------------

def parse_sets(items: list[str] | None) -> dict:
    """["k=v", ...] -> PipelineConfig overrides; true/false/none and numbers parsed."""
    out: dict = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--set wants key=value, got {it!r}")
        k, v = it.split("=", 1)
        low = v.strip().lower()
        if low in ("true", "false"):
            out[k.strip()] = low == "true"
        elif low in ("none", "null"):
            out[k.strip()] = None
        else:
            try:
                out[k.strip()] = int(v) if v.strip().lstrip("-").isdigit() else float(v)
            except ValueError:
                out[k.strip()] = v
    return out


def tie_slots(runs) -> list[tuple[int, str]]:
    """Where `stitches.apply_ties` asks for a lock: (run index, "in"|"out").
    The rule's own: the first run and every trimmed run are tied in; the run
    before a trim, and the last run, are tied off. A run under two points is
    never tied."""
    slots: list[tuple[int, str]] = []
    for i, r in enumerate(runs):
        if (i == 0 or r.trim) and len(r.points) >= 2:
            slots.append((i, "in"))
        if r.trim and i > 0 and len(runs[i - 1].points) >= 2:
            slots.append((i - 1, "out"))
    if runs and len(runs[-1].points) >= 2:
        slots.append((len(runs) - 1, "out"))
    return slots


def split_added(pre: list, post: list, want_in: bool, want_out: bool) -> tuple[list, list]:
    """The points `apply_ties` put before and after a run's own: (head, tail)."""
    n, m = len(pre), len(post)
    if m == n:
        return [], []
    if want_in and not want_out:
        cands = [m - n]
    elif want_out and not want_in:
        cands = [0]
    else:
        cands = range(0, m - n + 1)
    for h in cands:
        if post[h:h + n] == pre:
            return post[:h], post[h + n:]
    raise ValueError("tie points are not a prefix/suffix of the run")


def tie_legs(pre: list, head: list, tail: list) -> tuple[list | None, list | None]:
    """The lock's polyline at each end (None: no lock laid there)."""
    lead = (list(head) + [pre[0]]) if head else None
    trail = ([pre[-1]] + list(tail)) if tail else None
    return lead, trail


def legs_mm(legs: list) -> list[float]:
    return [math.dist(a, b) for a, b in zip(legs, legs[1:])]


def summarize(ties: list[dict], thread_mm: float = THREAD_MM) -> dict:
    """Ties (laid or not) -> counts, thread mm, pile and footprint mm2."""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    laid = [t for t in ties if t["laid"]]
    legs = [m for t in laid for m in legs_mm(t["legs"])]
    geoms = []
    for t in laid:
        pts = [tuple(p) for p in t["legs"]]
        uniq = {(round(x, 6), round(y, 6)) for x, y in pts}
        g = LineString(pts) if len(uniq) > 1 else Point(pts[0])
        geoms.append(g.buffer(thread_mm / 2.0))
    thread = sum(legs)
    return {"slots": len(ties), "laid": len(laid), "untied": len(ties) - len(laid),
            "legs": len(legs), "thread_mm": round(thread, 3),
            "pile_mm2": round(thread * thread_mm, 3),
            "footprint_mm2": round(unary_union(geoms).area, 3) if geoms else 0.0,
            "leg_mm": [round(min(legs), 3), round(max(legs), 3)] if legs else None}


def word_ties(row: dict, thread_mm: float = THREAD_MM) -> dict:
    """One word's saved ties -> the three readings, widest first:
    `ties` every lock anchored in the word's box (any colour, any shape: the
    ground's fill locks too, which no small-letter construction touches);
    `ties_glyph_box` those in a source glyph's bounding box grown by half a
    thread; `ties_ink` those in a non-white thread within half a thread of a
    glyph's own ink -- the lock that lands ON a letter, in its colour;
    `ties_ink_small` the part of those on bean-letter / skeleton runs, the
    only locks `cfg.small_letter_ties` reaches. `glyph_ties`: `ties_ink` per glyph.
    `by_tier`: the box's locks counted by the tier that sewed their run."""
    from shapely import wkt
    from shapely.geometry import Point
    glyphs = [wkt.loads(g) for g in row.get("glyphs_wkt", [])]
    half = thread_mm / 2.0
    ties = row["ties_detail"]

    def in_gbox(t):
        x, y = t["anchor"]
        return any(g.bounds[0] - half <= x <= g.bounds[2] + half and g.bounds[1] - half <= y <= g.bounds[3] + half
                   for g in glyphs)

    from tools.fremont_triage import WHITE_MIN

    def near(t, g):
        # in a LETTER's thread: the white patch fill under the words is not
        # the letter (`fremont_triage.WHITE_MIN`, the census's own rule)
        rgb = t.get("rgb")
        return (rgb is None or min(rgb) < WHITE_MIN) and g.distance(Point(t["anchor"])) <= half
    tiers: dict[str, int] = {}
    for t in ties:
        k = f"{t.get('tier', t['kind'])}{'' if t['laid'] else ' (untied)'}"
        tiers[k] = tiers.get(k, 0) + 1
    return {"ties": summarize(ties),
            "ties_glyph_box": summarize([t for t in ties if in_gbox(t)]),
            "ties_ink": summarize([t for t in ties if any(near(t, g) for g in glyphs)]),
            "ties_ink_small": summarize([t for t in ties if t.get("small") and any(near(t, g) for g in glyphs)]),
            "glyph_ties": [{"bbox_mm": [round(v, 2) for v in g.bounds],
                            **summarize([t for t in ties if near(t, g)])} for g in glyphs],
            "by_tier": dict(sorted(tiers.items()))}


def in_box(xy, box) -> bool:
    x0, y0, x1, y1 = box
    return x0 <= xy[0] <= x1 and y0 <= xy[1] <= y1


def change(before: float | None, after: float | None) -> str:
    if before in (None, 0) or after is None:
        return "-"
    return f"{100.0 * (after - before) / before:+.0f}%"


# --- digitizing, with the ties recorded at their source -----------------------------

@contextlib.contextmanager
def spy_ties(log: list):
    """Wrap `apply_ties` (stage 7's alias and the module function the appliqué
    fall-through calls): append one record per tie slot to `log`."""
    from digitizer_core import stage7_sequence as s7
    from digitizer_core import stitches as st
    real_s7, real_st = s7._apply_ties, st.apply_ties

    def make(real):
        def spy(runs, *a, **kw):
            pre = [list(r.points) for r in runs]
            slots = tie_slots(runs)
            real(runs, *a, **kw)
            want: dict[int, set] = {}
            for i, end in slots:
                want.setdefault(i, set()).add(end)
            for i, ends in want.items():
                r = runs[i]
                head, tail = split_added(pre[i], list(r.points), "in" in ends, "out" in ends)
                lead, trail = tie_legs(pre[i], head, tail)
                for end, legs, anchor in (("in", lead, pre[i][0]), ("out", trail, pre[i][-1])):
                    if end in ends:
                        log.append({"shape_id": r.shape_id, "kind": r.kind, "end": end, "_run": r,
                                    "anchor": [anchor[0], anchor[1]], "laid": legs is not None,
                                    "legs": [[x, y] for x, y in (legs or [])]})
        return spy
    s7._apply_ties, st.apply_ties = make(real_s7), make(real_st)
    try:
        yield
    finally:
        s7._apply_ties, st.apply_ties = real_s7, real_st


def _digitize(kind: str, name: str, overrides: dict):
    from tools import small_lettering_compare as slc
    sk: dict = {}
    bean: dict = {}
    log: list = []
    with slc.spy_tiers(sk, bean), spy_ties(log):
        if kind == "hat":
            from tools import fremont_triage as ft
            run = ft.run_arm(f"{name}__ties", FIXTURES[name], None, preflight=False, overrides=overrides)
        else:
            spec = slc.corpus_designs()[name]
            run = slc._digitize(spec["path"], {**spec["cfg"], **overrides})
    small = sorted(s for s, rep in {**bean, **sk}.items() if not rep.get("empty"))
    # Stage 7 can be run more than once per digitize (a trial plan whose runs
    # are thrown away): only a lock on a run of the FINAL plan is sewn. The
    # log holds each run itself, so no id is reused while this is read.
    rgb = {id(r): list(b.rgb) for b, r in run["plan"].iter_runs()}
    regions = {r.shape_id: r for r in run["result"].regions}
    final = [t for t in log if id(t["_run"]) in rgb]
    run["unsewn_tie_slots"] = len(log) - len(final)
    for t in final:
        t["small"] = t["shape_id"] in small and t["kind"] == "run"
        t["rgb"] = rgb[id(t.pop("_run"))]
        reg = regions.get(t["shape_id"])
        meta = (reg.meta or {}) if reg is not None else {}
        t["text"] = bool(meta.get("text_candidate") or meta.get("lettering_group"))
        t["tier"] = ("bean" if t["shape_id"] in bean and not bean[t["shape_id"]].get("empty") else
                     "skeleton" if t["shape_id"] in sk and not sk[t["shape_id"]].get("empty") else t["kind"])
    return run, final, small


def _plan_record(run: dict, log: list, small: list) -> dict:
    from tools.hairline_logo_bill import shape_digests
    from tools.small_lettering_compare import stream_md5
    s = run["plan"].stats
    return {"stitches": s.stitch_count, "trims": s.trims, "md5": stream_md5(run["plan"]),
            "shape_digests": shape_digests(run["plan"]), "small_shapes": small,
            "ties_all": summarize(log), "ties_small": summarize([t for t in log if t["small"]])}


def run_cell(fixture: str, tag: str, overrides: dict, out: Path) -> dict:
    """Digitize Fremont at a Hat size under `overrides`; ties per word and glyph."""
    from digitizer_core.adapter import plan_to_design
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    from tools import glyph_legibility as gl
    from tools import small_lettering_compare as slc
    t0 = time.time()
    run, log, small = _digitize("hat", fixture, overrides)
    p = run["gen"].p
    census = ft.roi_census(run)
    words, _dbg, _reg = gl.read_case("fremont", run["design"], use_ocr=True, words=WORDS)
    read = {w.name: w for w in words}
    rec = {"fixture": fixture, "tag": tag, "overrides": overrides, "width_mm": FIXTURES[fixture],
           **_plan_record(run, log, small), "words": {}}
    for name in WORDS:
        box = census[name]["box_mm"]
        glyphs = fsl.source_glyphs(p, ft.ROIS[name])
        ties = [t for t in log if in_box(t["anchor"], box)]
        w = read.get(name)
        row = slc.word_row(w.summary(), w.glyphs) if w else {}
        row.update(box_mm=box, stitches=census[name]["stitches"], trims=census[name]["trims"],
                   ties_detail=ties, glyphs_wkt=[g.wkt for g in glyphs])
        row.update(word_ties(row))
        rec["words"][name] = row
    rec["secs"] = round(time.time() - t0)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{fixture}__{tag}.json").write_text(json.dumps(rec, indent=1))
    (out / f"{fixture}__{tag}_design.json").write_text(json.dumps(plan_to_design(run["plan"], name=fixture)))
    print(f"{fixture}__{tag}: {rec['stitches']:,} st, {rec['trims']} tr, small shapes {len(small)}, "
          f"ties (small letters) {rec['ties_small']['laid']} laid / {rec['ties_small']['slots']} slots, "
          f"{rec['secs']} s", flush=True)
    for name in WORDS:
        r = rec["words"][name]
        t, g, k = r["ties"], r["ties_glyph_box"], r["ties_ink"]
        print(f"  {name:8s} box {t['laid']}/{t['slots']} pile {t['pile_mm2']} | glyph boxes {g['laid']}/{g['slots']} "
              f"pile {g['pile_mm2']} | on ink {k['laid']}/{k['slots']} pile {k['pile_mm2']} foot {k['footprint_mm2']}"
              f" | legib {r.get('legibility')} +sp {r.get('legibility_space')} | {r['stitches']} st "
              f"{r['trims']} tr | {r['by_tier']}", flush=True)
    return rec


def run_logo(name: str, tag: str, overrides: dict, out: Path) -> dict:
    """One corpus logo under `overrides`: the plan's per-shape digests and its ties."""
    t0 = time.time()
    run, log, small = _digitize("logo", name, overrides)
    rec = {"logo": name, "tag": tag, "overrides": overrides, **_plan_record(run, log, small)}
    rec["secs"] = round(time.time() - t0)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"logo_{name}__{tag}.json").write_text(json.dumps(rec, indent=1))
    print(f"logo {name}__{tag}: {rec['stitches']:,} st, {rec['trims']} tr, md5 {rec['md5'][:8]}, "
          f"small shapes {len(small)}, small-letter ties {rec['ties_small']['laid']}/"
          f"{rec['ties_small']['slots']}, {rec['secs']} s", flush=True)
    return rec


# --- before / after -------------------------------------------------------------------

def outside_small(before: dict, after: dict) -> dict:
    """Shapes laid differently that are NOT small letters in either plan."""
    small = set(before["small_shapes"]) | set(after["small_shapes"])
    a, b = before["shape_digests"], after["shape_digests"]
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return {"changed": len(diff), "changed_small": sum(1 for k in diff if k in small),
            "changed_other": [k for k in diff if k not in small]}


def _load(out: Path, stem: str) -> dict | None:
    p = out / f"{stem}.json"
    return json.loads(p.read_text()) if p.exists() else None


def table(out: Path, before: str, after: str) -> str:
    from tools.small_lettering_compare import fmt_ocr
    lines = []
    for fx in FIXTURES:
        a, b = _load(out, f"{fx}__{before}"), _load(out, f"{fx}__{after}")
        if not (a and b):
            continue
        o = outside_small(a, b)
        lines.append(f"## {fx}: {a['stitches']:,} -> {b['stitches']:,} st, trims {a['trims']} -> {b['trims']}, "
                     f"shapes changed {o['changed']} ({o['changed_small']} small letters, "
                     f"{len(o['changed_other'])} other)")
        lines.append("| word | locks in word box, laid (slots) | pile mm2: word box | glyph boxes | on the ink | on the ink, bean/skeleton runs | "
                     "ink footprint mm2 | legibility | +space | OCR | trims | stitches |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        keys = ("ties", "ties_glyph_box", "ties_ink", "ties_ink_small")
        tot = {k: [0.0, 0.0] for k in keys}
        for w in WORDS:
            x, y = a["words"][w], b["words"][w]
            for k in keys:
                tot[k][0] += x[k]["pile_mm2"]
                tot[k][1] += y[k]["pile_mm2"]
            tx, ty = x["ties"], y["ties"]
            piles = " | ".join(f"{x[k]['pile_mm2']} -> {y[k]['pile_mm2']} ({change(x[k]['pile_mm2'], y[k]['pile_mm2'])})"
                               for k in keys)
            lines.append(
                f"| {w} | {tx['laid']} ({tx['slots']}) -> {ty['laid']} ({ty['slots']}) | {piles} | "
                f"{x['ties_ink']['footprint_mm2']} -> {y['ties_ink']['footprint_mm2']} | "
                f"{x.get('legibility')} -> {y.get('legibility')} | "
                f"{x.get('legibility_space')} -> {y.get('legibility_space')} | "
                f"{fmt_ocr(x['ocr'])} -> {fmt_ocr(y['ocr'])} | {x['trims']} -> {y['trims']} | "
                f"{x['stitches']} -> {y['stitches']} |")
        piles = " | ".join(f"**{tot[k][0]:.3f} -> {tot[k][1]:.3f} ({change(tot[k][0], tot[k][1])})**" for k in keys)
        lines.append(f"| **four words** | | {piles} | | | | | | |")
        lines.append("")
    rows = []
    for p in sorted(out.glob(f"logo_*__{before}.json")):
        name = p.stem[len("logo_"):-len(f"__{before}")]
        a, b = json.loads(p.read_text()), _load(out, f"logo_{name}__{after}")
        if not b:
            continue
        o = outside_small(a, b)
        rows.append(f"| {name} | {len(a['small_shapes'])} | {a['md5'][:8]} -> {b['md5'][:8]} | "
                    f"{o['changed_small']} | {len(o['changed_other'])} | {a['trims']} -> {b['trims']} | "
                    f"{a['stitches']:,} -> {b['stitches']:,} | {a['ties_small']['pile_mm2']} -> "
                    f"{b['ties_small']['pile_mm2']} |")
    if rows:
        lines.append("| logo | small-letter shapes | stream md5 | small shapes changed | other shapes changed | "
                     "trims | stitches | small-letter tie pile mm2 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        lines.extend(rows)
    return "\n".join(lines)


def render(out: Path, renders: Path, before: str, after: str) -> list[Path]:
    """Per fixture: each word box, before | after, at the box's px/mm, the
    tie legs drawn red over the file's render."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    paths = []
    for fx in FIXTURES:
        recs = {t: _load(out, f"{fx}__{t}") for t in (before, after)}
        if not all(recs.values()):
            continue
        designs = {t: json.loads((out / f"{fx}__{t}_design.json").read_text()) for t in recs}
        rows = []
        width = 0
        for w in WORDS:
            ppm = RENDER_PPM[w]
            pair = []
            for t in (before, after):
                img, to_px = ft._render(designs[t], ppm)
                img = np.ascontiguousarray(img)
                row = recs[t]["words"][w]
                for tie in row["ties_detail"]:
                    pts = np.array([to_px(x, y) for x, y in tie["legs"]], np.int32)
                    if len(pts) > 1:
                        cv2.polylines(img, [pts], False, (0, 0, 230), 1, cv2.LINE_AA)
                    elif not tie["laid"]:
                        cx, cy = to_px(*tie["anchor"])
                        cv2.circle(img, (int(cx), int(cy)), 3, (230, 120, 0), 1, cv2.LINE_AA)
                crop = ft._crop(img, to_px, row["box_mm"], margin_mm=0.3)
                ti = row["ties_ink"]
                pair.append(ft._label(crop, f"{w} | {t}: locks on the ink {ti['laid']}/{ti['slots']}, pile "
                                            f"{ti['pile_mm2']} mm2, legib {row.get('legibility')}, trims {row['trims']}"))
            strip = ft._hstack(pair, gap=10)
            rows.append(strip)
            width = max(width, strip.shape[1])
        sheet = np.vstack([np.pad(r, ((0, 8), (0, width - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
        sheet = ft._label(sheet, f"Fremont {fx}: left {before}, right {after}. Red: lock-stitch legs; blue ring: a "
                                 "slot left untied. stitchviz draws a 3-pass bean as ONE thread width.", width=width)
        path = renders / f"{fx}__{before}_vs_{after}.png"
        cv2.imwrite(str(path), sheet)
        paths.append(path)
        print(path, flush=True)
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell", choices=list(FIXTURES), help="digitize Fremont at this Hat size")
    ap.add_argument("--logo", help="digitize one corpus logo (thin_strokes.corpus_cases)")
    ap.add_argument("--tag", default="main", help="name of this cell's arm (file stem)")
    ap.add_argument("--set", action="append", metavar="KEY=VALUE", help="a PipelineConfig override (repeatable)")
    ap.add_argument("--table", action="store_true", help="print the before/after table from saved cells")
    ap.add_argument("--render", action="store_true", help="write the before/after sheets")
    ap.add_argument("--reanalyze", action="store_true",
                    help="re-read the saved Fremont cells' locks (`word_ties`) without digitizing")
    ap.add_argument("--before", default="switch")
    ap.add_argument("--after", default="ties")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    overrides = parse_sets(a.set)
    if a.cell:
        run_cell(a.cell, a.tag, overrides, a.out)
    if a.logo:
        run_logo(a.logo, a.tag, overrides, a.out)
    if a.reanalyze:
        for p in sorted(a.out.glob("hat*__*.json")):
            if p.stem.endswith("_design"):
                continue
            rec = json.loads(p.read_text())
            for row in rec["words"].values():
                row.update(word_ties(row))
            p.write_text(json.dumps(rec, indent=1))
    if a.table:
        print(table(a.out, a.before, a.after))
    if a.render:
        render(a.out, a.renders or a.out, a.before, a.after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
