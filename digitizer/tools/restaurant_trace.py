"""Bridge's BAR & RESTAURANT, glyph by glyph: which reader refuses each letter?

`logo_bridge_bar.jpg`'s blue line is the corpus's least legible word
(`tools/small_lettering_compare.py --corpus bridge`: legibility 0.227, worst
glyph 0.0) and no small-text tier reaches it: the true-size switch and the
skeleton run leave bridge byte-identical (#944). Every small-text tier reads
its letters through a TAGGER first -- bean letters and the true-size restore
key on the text cluster (`words.word_key`), the Column lane and the skeleton
run on `columns.is_lettering` (the text cluster OR the house-angle group) --
so a letter no tagger holds is out of reach of all of them and sews on the
ordinary ladder.

This digitizes bridge once at its corpus size (80 mm, the Studio's six
colours, today's defaults plus any `--set`), captures the regions each tagger
saw (a wrapper on the pipeline's two tagger calls; nothing in the engine
changes), replays both old taggers step by step on them and prints, per
labelled glyph of the line (`testdata/lettering_truth.json`):

  cap      the glyph's box height and width, mm
  stroke   2 x area / perimeter (the traced shape's mean width), mm, and the
           skeleton stroke mean (half-width x 2) with its CV
  ink      `ink_path.read_cluster_ink`'s stroke over the line's twelve
           members read as one cluster (what bean letters would read), mm
  text cluster   tagged? else the door that refused it, with the value
  house group    tagged? else the rule
  L1 words       `tools/word_tagger_trace` (`cfg.lettering_words`, OFF)
  lane     `columns.is_lettering` and what the Column lane did with it
  sewn     the run kinds stage 7 laid for it, and its needle points
  tiers    the gate each small-text tier tests it on (`tier_gates`)

The "text cluster" / "house group" / "L1 words" columns are always the
SHIPPED taggers replayed on what they saw; `--adopt` changes what the tiers
are handed after the text cluster has run, not that replay.

    .venv/Scripts/python -m tools.restaurant_trace
    .venv/Scripts/python -m tools.restaurant_trace --legibility --json out.json
    .venv/Scripts/python -m tools.restaurant_trace --adopt --design-out adopt.json
    .venv/Scripts/python -m tools.restaurant_trace --set lettering_columns=false

`--adopt` is a census arm, never an engine option: the line's untagged
glyphs in the line's ink join the text cluster their neighbours share, i.e.
what a FIXED tagger would hand every tier. Measured 2026-10-15 it moves
three glyphs onto the Column lane and does not make the word legible (the
PR body of claude/bridge-restaurant-tier has the table and the renders).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRUTH = ROOT / "testdata" / "lettering_truth.json"
CASE = "bridge"
LINE = "BAR & RESTAURANT"
# Which letters each labelled region is, read by eye off the region outlines
# drawn over the prep raster (docs/renders/bridge-restaurant-tier/regions.png,
# 2026-10-15). Twelve regions for fourteen glyphs: ST and NT are traced fused.
LETTERS = {"Sc1dfc688": "B", "S5afda564": "A", "S673d856d": "R", "S4fdc326d": "&",
           "Sf6fe55e0": "R", "Seaf63fed": "E", "S2c4ea3ad": "ST", "S2953082f": "A",
           "Se05b0bea": "U", "S3963a893": "R", "Sc434b18d": "A", "S2242b799": "NT"}


def _parse_set(items: list[str]) -> dict:
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        lv = v.strip().lower()
        if lv in ("true", "false"):
            out[k] = lv == "true"
        elif lv == "none":
            out[k] = None
        else:
            try:
                out[k] = int(v)
            except ValueError:
                out[k] = float(v)
    return out


def adopt_line(regions, glyphs: list[str], chart) -> list[str]:
    """Census-only, the counterfactual of a FIXED tagger: every glyph of the
    line the text cluster left untagged joins the cluster its tagged
    neighbours share, when its thread is within the cluster's own ink link
    (`textcluster.TEXT_CLUSTER_DELTA_E_MAX`) of a tagged member's -- the "&",
    sewn in the black of the wheel, stays out. -> the shape ids adopted."""
    from digitizer_core.textcluster import TEXT_CLUSTER_DELTA_E_MAX
    by = {r.shape_id: r for r in regions}
    tagged = [by[s] for s in glyphs if s in by and by[s].meta.get("text_candidate")]
    if not tagged:
        return []
    src = tagged[0].meta
    adopted = []
    for s in glyphs:
        r = by.get(s)
        if r is None or r.meta.get("text_candidate"):
            continue
        try:
            de = min(0.0 if t.thread_index == r.thread_index
                     else float(chart.delta_e(t.thread_index, r.thread_index)) for t in tagged)
        except (IndexError, TypeError, ValueError):
            de = 0.0
        if de > TEXT_CLUSTER_DELTA_E_MAX:
            continue
        for k in ("text_candidate", "text_cluster_id", "text_cluster_stroke_mm"):
            r.meta[k] = src[k]
        r.meta["text_cluster_all_rescued"] = False
        adopted.append(s)
    return adopted


class _Capture:
    """Wrap the pipeline's tagger calls; keep a snapshot of the regions each
    saw. `adopt` (census only): after the text cluster runs, `adopt_line`."""

    def __init__(self, adopt: list[str] | None = None, chart=None):
        self.text_regions = None
        self.house_regions = None
        self.lane: dict[str, dict] = {}
        self.adopt, self.chart, self.adopted = adopt, chart, []

    def __enter__(self):
        from digitizer_core import pipeline as P
        from digitizer_core import stage7_sequence as s7
        self._P, self._s7 = P, s7
        self._dtc, self._house, self._lane = (P.detect_text_clusters, P.set_lettering_house_angle,
                                              s7.lettering_columns_shape)

        def dtc(regions, p, **kw):
            self.text_regions = _snapshot(regions)
            out = self._dtc(regions, p, **kw)
            if self.adopt:
                self.adopted = adopt_line(regions, self.adopt, self.chart)
            return out

        def house(regions, p, **kw):
            self.house_regions = _snapshot(regions)
            return self._house(regions, p, **kw)

        def lane(poly, shape_id, **kw):
            runs, report = self._lane(poly, shape_id, **kw)
            self.lane[shape_id] = {"empty": bool(report.get("empty"))}
            return runs, report
        P.detect_text_clusters, P.set_lettering_house_angle = dtc, house
        s7.lettering_columns_shape = lane
        return self

    def __exit__(self, *exc):
        self._P.detect_text_clusters, self._P.set_lettering_house_angle = self._dtc, self._house
        self._s7.lettering_columns_shape = self._lane
        return False


def _snapshot(regions):
    from dataclasses import replace
    return [replace(r, meta=dict(r.meta)) for r in regions]


def _cands_by_id(cands):
    return {c.region.shape_id: c for c in cands}


def _nest_host(cid, cands):
    """The smallest candidate whose box holds `cid`'s box (`_drop_nested`'s test)."""
    me = cands[cid]
    b = me.region.polygon.bounds

    def area(x):
        return (x[2] - x[0]) * (x[3] - x[1])
    hosts = []
    for o in cands.values():
        if o is me:
            continue
        ob = o.region.polygon.bounds
        if ob[0] <= b[0] and ob[1] <= b[1] and ob[2] >= b[2] and ob[3] >= b[3] and area(ob) > area(b):
            hosts.append(o)
    if not hosts:
        return None
    h = min(hosts, key=lambda o: area(o.region.polygon.bounds))
    return f"nested in {h.region.shape_id} ({h.height_mm:.1f} x {h.width_mm:.1f} mm)"


def _component_why(sid, comp_of, cands, chart, rules):
    """A glyph in a component under three: its component's size and the
    nearest-to-linking partner among the line's other admitted glyphs."""
    from tools.word_tagger_trace import link_failures
    me = cands[sid]
    comp = comp_of[sid]
    best = None
    for o in cands.values():
        if o is me or o.region.shape_id in comp:
            continue
        fails = link_failures(me, o, chart, rules)
        worst = max((f.ratio for f in fails), default=0.0)
        if best is None or worst < best[0]:
            best = (worst, o.region.shape_id, fails)
    text = f"component of {len(comp)}"
    if best is not None and best[2]:
        text += f"; nearest {best[1]}: " + ", ".join(f.text() for f in best[2])
    return text


def text_cluster_trace(regions, chart, glyphs: list[str]) -> dict[str, dict]:
    """`textcluster.detect_text_clusters`, replayed: per glyph, tagged or the
    first rule that refused it."""
    from dataclasses import replace

    from digitizer_core import textcluster as T
    from tools.word_tagger_trace import base_rules
    by = {r.shape_id: r for r in regions}
    rescued = T._candidates(regions)
    taken = set()
    for g in T._cluster(rescued):
        if len(g) >= T.MIN_CLUSTER_MEMBERS:
            taken.update(c.region.shape_id for c in g)
    pool = [c for c in rescued if c.region.shape_id not in taken] + T._letter_candidates(regions)
    pool_ids = _cands_by_id(pool)
    kept = T._drop_nested(pool)
    kept_ids = _cands_by_id(kept)
    comps = T._cluster(kept, T.LETTER_HEIGHT_RATIO, chart)
    comp_of = {}
    for g in comps:
        ids = {c.region.shape_id for c in g}
        for s in ids:
            comp_of[s] = ids
    rules = replace(base_rules(), height_ratio=T.LETTER_HEIGHT_RATIO,
                    stroke_ratio=T.SIMILARITY_RATIO, ink_de=T.TEXT_CLUSTER_DELTA_E_MAX)
    out = {}
    for sid in glyphs:
        r = by.get(sid)
        if r is None:
            out[sid] = {"tagged": False, "why": "no region"}
            continue
        if sid in taken:
            out[sid] = {"tagged": True, "why": "rescued door"}
            continue
        if sid not in pool_ids:
            out[sid] = {"tagged": False, "why": _letter_door_why(r)}
            continue
        if sid not in kept_ids:
            out[sid] = {"tagged": False, "why": _nest_host(sid, pool_ids)}
            continue
        if len(comp_of[sid]) >= T.MIN_CLUSTER_MEMBERS:
            out[sid] = {"tagged": True, "why": f"letter door, component of {len(comp_of[sid])}"}
            continue
        out[sid] = {"tagged": False, "why": _component_why(sid, comp_of, kept_ids, chart, rules)}
    return out


def _letter_door_why(r) -> str:
    from digitizer_core import textcluster as T
    if r.meta.get("rescued_small_shape"):
        st = T._skeleton_stroke_stats(r)
        if st is None:
            return "rescued door: no skeleton"
        if st.cv > T.STROKE_CV_MAX:
            return f"rescued door: stroke_cv {st.cv:.2f} > {T.STROKE_CV_MAX}"
        x0, y0, x1, y1 = r.polygon.bounds
        return f"rescued door: aspect {(x1 - x0) / max(y1 - y0, 1e-9):.2f}"
    x0, y0, x1, y1 = r.polygon.bounds
    w, h = x1 - x0, y1 - y0
    a = w / max(h, 1e-9)
    if not (T.ASPECT_RATIO_MIN <= a <= T.ASPECT_RATIO_MAX):
        return f"aspect {a:.2f} > {T.ASPECT_RATIO_MAX}"
    if not (T.LETTER_MIN_HEIGHT_MM <= h <= T.LETTER_MAX_HEIGHT_MM):
        return f"height {h:.2f} outside {T.LETTER_MIN_HEIGHT_MM}-{T.LETTER_MAX_HEIGHT_MM}"
    st = T._skeleton_stroke_stats(r)
    if st is None:
        return "no skeleton"
    return f"stroke_cv {st.cv:.2f} > {T.LETTER_STROKE_CV_MAX}"


def house_group_trace(regions, glyphs: list[str]) -> dict[str, dict]:
    """`textcluster._lettering_groups`, replayed."""
    from dataclasses import replace

    from digitizer_core import textcluster as T
    from tools.word_tagger_trace import base_rules
    by = {r.shape_id: r for r in regions}
    raw = []
    refused = {}
    for r in regions:
        st = T._skeleton_stroke_stats(r)
        x0, y0, x1, y1 = r.polygon.bounds
        w, h = x1 - x0, y1 - y0
        if st is None:
            refused[r.shape_id] = "no skeleton"
            continue
        if h <= 0 or w <= 0:
            refused[r.shape_id] = "empty box"
            continue
        if not (T.ASPECT_RATIO_MIN <= w / h <= T.ASPECT_RATIO_MAX):
            refused[r.shape_id] = f"aspect {w / h:.2f} > {T.ASPECT_RATIO_MAX}"
            continue
        raw.append(T._Candidate(region=r, height_mm=h, width_mm=w, stroke_mean_mm=st.mean_mm,
                                stroke_cv=st.cv, cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0))
    raw_ids = _cands_by_id(raw)
    kept = T._drop_nested(raw)
    kept_ids = _cands_by_id(kept)
    comp_of = {}
    for g in T._cluster(kept, T.SATIN_ANGLE_HEIGHT_RATIO):
        ids = {c.region.shape_id for c in g}
        for s in ids:
            comp_of[s] = ids
    rules = replace(base_rules(), height_ratio=T.SATIN_ANGLE_HEIGHT_RATIO,
                    stroke_ratio=T.SIMILARITY_RATIO)
    out = {}
    for sid in glyphs:
        if sid not in by:
            out[sid] = {"tagged": False, "why": "no region"}
        elif sid in refused:
            out[sid] = {"tagged": False, "why": refused[sid]}
        elif sid not in kept_ids:
            out[sid] = {"tagged": False, "why": _nest_host(sid, raw_ids)}
        elif len(comp_of[sid]) >= T.MIN_CLUSTER_MEMBERS:
            out[sid] = {"tagged": True, "why": f"component of {len(comp_of[sid])}"}
        else:
            out[sid] = {"tagged": False, "why": _component_why(sid, comp_of, kept_ids, None, rules)}
    return out


def words_trace(regions, chart, glyphs: list[str]) -> dict[str, str]:
    """L1 (`words.detect_words`, `cfg.lettering_words` OFF) through
    `tools.word_tagger_trace.trace`."""
    from tools.word_tagger_trace import trace
    t = trace(regions, chart)
    in_word = {s for w in t.words for s in w}
    out = {}
    for sid in glyphs:
        if sid in in_word:
            out[sid] = "in a word"
        elif sid in t.rejected:
            w = t.rejected[sid]
            out[sid] = w.text().split(" [")[0]
        elif sid in t.fate:
            out[sid] = t.fate[sid].text()
        else:
            out[sid] = "admitted, in no word"
    return out


def tier_gates(rows: list[dict], line_regions, cfg) -> None:
    """Per glyph, the gate each small-text tier would test it on, at the
    true-size switch's own values (`config.SMALL_TEXT_TRUE_SIZE`, gate-1
    candidates) or the config's where set. Written as `row["tiers"]`:

      restore    `small_text.restore_small_text`: the line's core (`_core`:
                 ONE thread, heights 0.8-1.25 x the median, centres within
                 half a cap of the median centre -- a straight line) and its
                 median cap under `small_text_restore_mm`
      bean       `beanletters.weight_groups`: ink stroke under
                 `bean_letter_max_stroke_mm` (the cluster median decides when
                 the line does not split in two)
      skeleton   `small_lettering_skeleton`: only a shape the area rescue
                 sends to the run tier (`polygon.area < min_detail_mm^2`)
    """
    from digitizer_core.config import SMALL_TEXT_TRUE_SIZE
    from digitizer_core.small_text import _core
    restore = cfg.small_text_restore_mm or SMALL_TEXT_TRUE_SIZE["small_text_restore_mm"]
    bean = cfg.bean_letter_max_stroke_mm or SMALL_TEXT_TRUE_SIZE["bean_letter_max_stroke_mm"]
    floor = cfg.min_detail_mm ** 2
    clusters: dict[str, list] = {}
    for r in line_regions:
        cid = (r.meta or {}).get("text_cluster_id")
        if cid:
            clusters.setdefault(cid, []).append(r)
    core_ids, caps = set(), []
    for members in clusters.values():
        core = _core(members)
        core_ids.update(r.shape_id for r in core)
        if core:
            caps.append(float(sorted(r.polygon.bounds[3] - r.polygon.bounds[1] for r in core)
                              [len(core) // 2]))
    line_cap = max(caps) if caps else None
    for row in rows:
        if row.get("missing"):
            continue
        sid = row["sid"]
        if line_cap is None:
            rs = "no text cluster on the line"
        elif sid not in core_ids:
            rs = "off the line core (_core)"
        elif line_cap >= restore:
            rs = f"line cap {line_cap:.2f} >= {restore:g}"
        else:
            rs = "reached"
        ink = row["ink_stroke_mm"]
        bs = ("no ink read" if ink is None else
              ("reached" if ink < bean else f"ink {ink:.2f} >= {bean:g}"))
        ss = ("reached" if row["area_mm2"] < floor else f"area {row['area_mm2']:.1f} >= {floor:.2f}")
        row["tiers"] = {"restore": rs, "bean": bs, "skeleton": ss}


def run(overrides: dict | None = None, adopt: bool = False, design_out: Path | None = None,
        legibility: bool = False) -> dict:
    """Digitize bridge (80 mm, six colours, today's defaults + `overrides`)
    and trace the line. `adopt`: the census-only `adopt_line` arm.
    `design_out`: write the Design json there. `legibility`: also read the
    words with `tools.glyph_legibility` (OCR where tesseract is on PATH)."""
    from digitizer_core import PipelineConfig
    from digitizer_core.columns import is_lettering, is_solid_blob
    from digitizer_core.ink_path import read_cluster_ink
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.textcluster import _skeleton_stroke_stats
    from digitizer_core.threads import chart_for
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS

    rel, width, garment = REAL_ART[CASE]
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                         max_colors=STUDIO_MAX_COLORS, **(overrides or {}))
    glyphs = json.loads(TRUTH.read_text())["fixtures"][CASE]["lines"][LINE]
    chart = chart_for(cfg)
    with _Capture(adopt=glyphs if adopt else None, chart=chart) as cap:
        gen = build_generation(str(ROOT / "testdata" / rel), cfg)
        result = finish_generation(gen.fork(), cfg)
        plan = plan_stitches(result, cfg)
    final = {r.shape_id: r for r in result.regions}
    tc = text_cluster_trace(cap.text_regions, chart, glyphs)
    hg = house_group_trace(cap.house_regions, glyphs)
    wd = words_trace(cap.text_regions, chart, glyphs)
    members = [final[s] for s in glyphs if s in final]
    inks = {r.shape_id: i for r, i in zip(members, read_cluster_ink(gen.p, members))}
    sewn: dict[str, dict] = {}
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id in glyphs:
                d = sewn.setdefault(r.shape_id, {"kinds": {}, "points": 0})
                d["kinds"][r.kind] = d["kinds"].get(r.kind, 0) + 1
                d["points"] += len(r.points)
    rows = []
    for sid in glyphs:
        r = final.get(sid) or next((x for x in cap.text_regions if x.shape_id == sid), None)
        if r is None:
            rows.append({"sid": sid, "missing": True})
            continue
        x0, y0, x1, y1 = r.polygon.bounds
        st = _skeleton_stroke_stats(r)
        m = r.meta or {}
        ink = inks.get(sid)
        rows.append({
            "sid": sid, "cx": round((x0 + x1) / 2, 2), "cy": round((y0 + y1) / 2, 2),
            "cap_mm": round(y1 - y0, 2), "w_mm": round(x1 - x0, 2),
            "area_mm2": round(r.polygon.area, 2),
            "holes": len(getattr(r.polygon, "interiors", []) or []),
            "mean_width_mm": round(2 * r.polygon.area / max(r.polygon.length, 1e-9), 3),
            "skel_stroke_mm": None if st is None else round(2 * st.mean_mm, 3),
            "skel_cv": None if st is None else round(st.cv, 2),
            "ink_stroke_mm": None if ink is None or ink.stroke_mm is None else round(ink.stroke_mm, 3),
            "thread": r.thread_number,
            "rescued": bool(m.get("rescued_small_shape")),
            "text_cluster": tc[sid], "house_group": hg[sid], "words": wd[sid],
            "meta_text_candidate": bool(m.get("text_candidate")),
            "meta_lettering_group": bool(m.get("lettering_group")),
            "ink_stray": bool(m.get("lettering_ink_stray")),
            "solid_blob": bool(is_solid_blob(r.polygon)),
            "is_lettering": bool(is_lettering(r, cfg)),
            "lane": cap.lane.get(sid),
            "sewn": sewn.get(sid, {"kinds": {}, "points": 0}),
        })
    rows.sort(key=lambda x: x.get("cx", 0.0))
    tier_gates(rows, [final[s] for s in glyphs if s in final], cfg)
    s = plan.stats
    from tools.small_lettering_compare import stream_md5
    out = {"case": CASE, "line": LINE, "width_mm": width, "overrides": overrides or {},
           "adopted": cap.adopted, "stitches": s.stitch_count, "trims": s.trims,
           "md5": stream_md5(plan), "rows": rows}
    if design_out is not None or legibility:
        from digitizer_core.adapter import plan_to_design
        design = plan_to_design(plan, name=CASE)
        if design_out is not None:
            design_out.write_text(json.dumps(design))
        if legibility:
            from tools import glyph_legibility as gl
            words, _dbg, _reg = gl.read_case(CASE, design, use_ocr=True)
            out["legibility"] = {w.name: w.summary() for w in words}
    return out


def table(res: dict) -> str:
    head = ("| glyph | cap x w mm | holes | mean w / skel mm (cv) | ink mm | text cluster | house group "
            "| L1 words | lane | sewn | restore / bean / skeleton |")
    arm = res["overrides"] or "defaults"
    if res.get("adopted"):
        arm = f"{arm} + adopt_line {res['adopted']}"
    lines = [f"{res['case']} {res['width_mm']:g} mm {arm}: "
             f"{res['stitches']:,} st / {res['trims']} trims, md5 {res['md5'][:8]}"]
    for name, w in (res.get("legibility") or {}).items():
        o = w.get("ocr") or {}
        lines.append(f"  {name}: {w['glyphs']} source glyphs, legibility {w['legibility']}, "
                     f"worst {w['worst_glyph']}, OCR {o.get('recovered')}/{o.get('read_on_source')} "
                     f"{o.get('ci95')}")
    lines += ["", head, "|" + "---|" * 11]
    for r in res["rows"]:
        if r.get("missing"):
            lines.append(f"| {r['sid']} | missing |" + " |" * 9)
            continue
        t = r.get("tiers") or {}
        tiers = " / ".join(t.get(k, "-") for k in ("restore", "bean", "skeleton"))
        tc = "yes" if r["text_cluster"]["tagged"] else r["text_cluster"]["why"]
        hg = "yes" if r["house_group"]["tagged"] else r["house_group"]["why"]
        lane = ("not asked" if r["lane"] is None else ("empty" if r["lane"]["empty"] else "columns"))
        if r["is_lettering"] is False and r["lane"] is None:
            lane = "refused (is_lettering False)"
        kinds = ", ".join(f"{k} x{v}" for k, v in sorted(r["sewn"]["kinds"].items())) or "nothing"
        lines.append(
            f"| {LETTERS.get(r['sid'], '?')} {r['sid']} | {r['cap_mm']:.2f} x {r['w_mm']:.2f} | {r['holes']} "
            f"| {r['mean_width_mm']:.2f} / {r['skel_stroke_mm']} ({r['skel_cv']}) | {r['ink_stroke_mm']} "
            f"| {tc} | {hg} | {r['words']} | {lane} | {kinds}, {r['sewn']['points']} pts | {tiers} |")
    return "\n".join(lines)


# The line's band in plan millimetres (y down), with a margin: the arc runs
# from about (-18.5, 3.8) to (17.8, 5.7) through (-2.7, 18.4) at 80 mm.
BAND_MM = (-22.0, 0.0, 22.0, 22.0)


def band_render(designs: list[tuple[str, dict]], out: Path, px_per_mm: float = 24.0,
                scale: float = 0.6) -> None:
    """Thread renders (`stitchviz.render_design`) of the line's band, one row
    per (label, Design), stacked, written to `out`."""
    import cv2
    import numpy as np

    from digitizer_core import stitchviz
    from digitizer_core.stitchviz import UNITS_PER_MM
    X0, Y0, X1, Y1 = BAND_MM
    rows = []
    for label, d in designs:
        img = stitchviz.render_design(d, px_per_mm=px_per_mm, pad_mm=2.0)
        pts = [s for s in d["stitches"] if s.get("type") in ("stitch", "jump")]
        x0, y1 = min(s["x"] for s in pts), max(s["y"] for s in pts)

        def px(x, y):         # plan mm (y down) -> render pixel (the Design's y is up)
            return (int(((x * UNITS_PER_MM - x0) / UNITS_PER_MM + 2.0) * px_per_mm),
                    int(((y1 + y * UNITS_PER_MM) / UNITS_PER_MM + 2.0) * px_per_mm))
        a, b = px(X0, Y0), px(X1, Y1)
        crop = img[max(0, a[1]):b[1], max(0, a[0]):b[0]].copy()
        cv2.rectangle(crop, (0, 0), (min(crop.shape[1], 18 * len(label) + 20), 40), (255, 255, 255), -1)
        cv2.putText(crop, label, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
        rows.append(crop)
    w = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows]
    img = np.vstack(rows)
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])


def regions_render(out: Path, px_per_mm: float = 22.5) -> None:
    """The prep raster of the line's band with every region outlined: the
    line's labelled regions in red (holes magenta) with their ids, the rest
    cyan. What `LETTERS` was read off."""
    from PIL import Image, ImageDraw

    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS
    rel, width, garment = REAL_ART[CASE]
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=STUDIO_MAX_COLORS)
    gen = build_generation(str(ROOT / "testdata" / rel), cfg)
    glyphs = set(json.loads(TRUTH.read_text())["fixtures"][CASE]["lines"][LINE])
    p = gen.p
    x0, y0, x1, y1 = p.art_bbox
    cx, cy, ppm = (x0 + x1) / 2.0, (y0 + y1) / 2.0, p.px_per_mm
    X0, Y0, X1, Y1 = BAND_MM
    crop = Image.fromarray(p.rgb[int(Y0 * ppm + cy):int(Y1 * ppm + cy),
                                 int(X0 * ppm + cx):int(X1 * ppm + cx)])
    crop = crop.resize((int((X1 - X0) * px_per_mm), int((Y1 - Y0) * px_per_mm)), Image.BICUBIC)
    d = ImageDraw.Draw(crop)

    def to_px(x, y):
        return ((x - X0) * px_per_mm, (y - Y0) * px_per_mm)
    for r in gen.regions:
        b = r.polygon.bounds
        if r.shape_id in glyphs or b[2] < X0 or b[0] > X1 or b[3] < Y0 or b[1] > Y1:
            continue
        for g in getattr(r.polygon, "geoms", [r.polygon]):
            d.line([to_px(*q) for q in g.exterior.coords], fill=(0, 200, 200), width=1)
    for r in gen.regions:
        if r.shape_id not in glyphs:
            continue
        for g in getattr(r.polygon, "geoms", [r.polygon]):
            d.line([to_px(*q) for q in g.exterior.coords], fill=(255, 0, 0), width=2)
            for hole in g.interiors:
                d.line([to_px(*q) for q in hole.coords], fill=(255, 0, 255), width=2)
        c = r.polygon.centroid
        bx = to_px(c.x, r.polygon.bounds[1] - 0.9)
        d.rectangle([bx[0] - 34, bx[1] - 9, bx[0] + 34, bx[1] + 9], fill=(255, 255, 255))
        d.text((bx[0] - 32, bx[1] - 7), f"{LETTERS.get(r.shape_id, '?')} {r.shape_id[:6]}", fill=(0, 0, 0))
    crop.save(out, optimize=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE",
                    help="PipelineConfig overrides (true/false/none/number)")
    ap.add_argument("--adopt", action="store_true",
                    help="census-only arm: the line's untagged glyphs in the line's ink join its "
                         "text cluster (what a fixed tagger would hand the tiers)")
    ap.add_argument("--legibility", action="store_true",
                    help="also read the words with tools.glyph_legibility")
    ap.add_argument("--design-out", type=Path, help="write the Design json here")
    ap.add_argument("--json", type=Path, help="write the rows here")
    ap.add_argument("--band", nargs="+", metavar=("OUT.png", "LABEL=DESIGN.json"),
                    help="no digitize: stack thread renders of the line's band from saved Designs")
    ap.add_argument("--regions", type=Path, metavar="OUT.png",
                    help="stages 1-4 only: the band's prep raster with the regions outlined")
    a = ap.parse_args(argv)
    if a.regions:
        regions_render(a.regions)
        print("wrote", a.regions)
        return 0
    if a.band:
        out, specs = Path(a.band[0]), a.band[1:]
        band_render([(s.split("=", 1)[0], json.loads(Path(s.split("=", 1)[1]).read_text()))
                     for s in specs], out)
        print("wrote", out)
        return 0
    res = run(_parse_set(a.set), adopt=a.adopt, design_out=a.design_out, legibility=a.legibility)
    print(table(res))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
