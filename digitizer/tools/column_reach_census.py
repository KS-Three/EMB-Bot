#!/usr/bin/env python
"""column_reach_census: does every hand-labelled letter of a paired job reach
the Column lettering lane, and when it does not, why not?

The Column lane (`cfg.lettering_columns`, `columns.lettering_columns_shape`)
carries every lettering construction gain of the week -- folds, lean, the
inside stagger, small_bold -- but only for a shape `columns.is_lettering`
admits, and only when stage 7 hands that shape to it. A letter it never sees
sews on the skeleton satin tier with its fans and patchwork. This counts, per
paired job at the PRO's width (the Studio's request, `tools.pro_pair`), how
many labelled letters arrive, and gives every one that does not a reason.

LABELS. `testdata/lettering_truth.json`:
  fixtures   the corpus hand labels (`tools/word_tagger_eval.py`), shape ids
             of `build_generation` at the corpus width. A pair of that art is
             at another width, so its ids differ: the labels are CARRIED
             (`word_tagger_eval.transfer_labels`, by geometry about the design
             centre), and at the corpus width the carry must give the hand
             labels back exactly (`carry_check`; the tool refuses a fixture
             whose carry does not).
  pairs      labels for pairs the corpus has none for (MFab, ProSeal), added
             2026-10-25 as NEW keys (agent-labelled, each with the width and
             garment it was labelled at): shape ids of the regions THIS tool's
             digitize hands to the text tagger (`pre_tag`: stage 4's regions,
             before any tagger can split one), on the Studio request at that
             width -- MFab on the rembg path, which a worktree must borrow
             from the primary checkout (`_rembg_venv`). `carry_from` names
             another pair to carry from instead (ProSeal's beanie).
A labelled letter no region of the pair carries is LOST (`no_region`): the
pair's segmentation merged it into another shape or dropped it.

PER LETTER (each labelled letter, on the final regions stage 7 plans):
  detected   `columns.is_lettering(region, cfg)`
  reached    detected AND `lettering_columns_shape` built it (non-empty) --
             recorded by wrapping the rungs' names in `stage7_sequence` while
             the pipeline runs; the plan itself keeps no per-shape report.

THE REASON for a miss, the first that applies:
  no_region        the letter is no region of its own at this width
  stage7_route     tagged, but not built by the lane: a lane guard in
                   `columns.is_lettering` (`guard:solid_blob`, `guard:ink_stray`,
                   `guard:icon`), a rung ahead of the lane took it (the rung's
                   name, e.g. `run_outline`, `bean_letter`, `keyline_runs`),
                   or the lane was asked and declined (`lane_declined`)
  untagged: the text tagger's own test, replayed on the regions it was given
  (`pre_tag`) with its shipped constants (`replay_text_door`, parity-pinned
  against `detect_text_clusters`):
  aspect           width/height outside `ASPECT_RATIO_MIN`..`ASPECT_RATIO_MAX`
  height_bounds / stroke_cv / no_skeleton / nested   the door's other tests
  height_ratio     admitted, but its nearest-to-linking labelled line-mate is
                   further than `LETTER_HEIGHT_RATIO` in height
  other_thread     ... in another ink (`TEXT_CLUSTER_DELTA_E_MAX`)
  stroke_ratio / distance   ... the link's other two terms
  cluster_of_one   admitted and linkable, but its line has fewer than
                   `MIN_CLUSTER_MEMBERS` admitted letters
The house-angle group (the other tagger `is_lettering` reads) missed it too, or
it would be detected; its reason is listed beside (`house`).

DETECTION is Cohen's kappa of "letter" (labelled) against `is_lettering`,
over every scored region of a pair, and pooled (ROADMAP gate 4: never a raw
agreement). REACH kappa is the same with "built by the lane".

    python -m tools.column_reach_census digitize --cache DIR [SLUG ...]
    python -m tools.column_reach_census read --cache DIR [--json OUT] [--md OUT]
    python -m tools.column_reach_census map --cache DIR SLUG --out PNG    # indexed regions, to label

`digitize` caches one pickle per pair (`DIR/<slug>/<arm>.pkl`, 3-10 min a
pair on the loaded laptop); `--arm NAME --kw key=json` runs the pipeline with
`detect_text_clusters` given that keyword (a monkeypatch: the keyword is NOT
wired through `pipeline.py`), for a prototype's ON arm.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import functools
import json
import math
import pickle
import sys
import time
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

TRUTH = DIGITIZER / "testdata" / "lettering_truth.json"
PAIRS_KEY = "pairs"

#: the paired jobs this census reads, and the job each belongs to (a held-out
#: split leaves a whole JOB out: two widths of one artwork are not independent)
CENSUS_PAIRS = {
    "hotel_fremont_hat": "fremont", "hotel_fremont_patch": "fremont",
    "precision_drone": "drone",
    "proseal_hat": "proseal", "proseal_beanie": "proseal",
    "mfab_hat": "mfab", "mfab_lc": "mfab",
    "becker_hat_large": "becker", "becker_lc_large": "becker",
    "becker_hat_small": "becker", "becker_chest_small": "becker",
    "gaulke_roofing_hat": "gaulke", "gaulke_roofing_lc": "gaulke",
    "tires_hat_3d": "tires",
    "goldentee_hat": "goldentee",
}
#: pair slug prefix -> the corpus fixture whose hand labels it carries
SOURCE_FIXTURE = (("becker", "becker"), ("gaulke_roofing", "gaulke"),
                  ("hotel_fremont", "fremont"), ("precision_drone", "drone"),
                  ("tires", "tires"), ("bridge", "bridge"))

#: the stage-7 rungs whose calls are recorded per shape id (each takes the
#: shape id as its second positional argument and returns (runs, report))
RUNGS = ("bean_letter", "skeleton_letter_runs", "small_solid_satin", "run_outline",
         "keyline_runs", "stitch_shape", "lettering_columns_shape", "satin_shape",
         "contour_fill", "blend_fill", "sketch_fill", "hairline_tier_runs",
         "monoline_stroke", "detail_runs", "scanline_fill", "meander_fill",
         "streamline_fill")
LANE = "lettering_columns_shape"

BUCKETS = ("aspect", "height_ratio", "other_thread", "cluster_of_one", "stage7_route")


# ------------------------------------------------------------------ labels

def source_fixture(slug: str) -> str | None:
    for prefix, name in SOURCE_FIXTURE:
        if slug.startswith(prefix):
            return name
    return None


def load_truth() -> dict:
    return json.loads(TRUTH.read_text(encoding="utf-8"))


def corpus_regions(name: str, cache: Path | None):
    """The corpus fixture's regions as the hand labels name them
    (`word_tagger_eval._regions` at `thin_strokes.REAL_ART`'s width)."""
    from tools.thin_strokes import REAL_ART
    from tools.word_tagger_eval import _regions
    rel, width, garment = REAL_ART[name]
    return _regions(DIGITIZER / "testdata" / rel, width, garment, cache), width


def corpus_labels(name: str, regions, truth: dict) -> tuple[dict | None, str]:
    """The fixture's hand labels on today's corpus generation: the
    'fixtures' entry when every labelled id is still a region, else its
    'relabels' entry (a later commit's, for segmentation that moved) when
    that one is whole, else None (STALE: never scored against the wrong
    regions). -> (labels, which)."""
    have = {r.shape_id for r in regions}
    for key in ("fixtures", "relabels"):
        tr = truth.get(key, {}).get(name)
        if tr is None:
            continue
        ids = [s for v in tr["lines"].values() for s in v]
        if all(s in have for s in ids):
            return tr, key
    return None, "stale"


def carry_check(name: str, cache: Path | None, truth: dict | None = None) -> dict:
    """The label carry onto the fixture's OWN generation, at the corpus
    width: it must reproduce the hand labels exactly (the backup lane's
    check, `word_tagger_eval._same_labels`). -> {ok, stale, letters, which}."""
    from tools.word_tagger_eval import _same_labels, transfer_labels
    truth = truth or load_truth()
    regions, _w = corpus_regions(name, cache)
    tr, which = corpus_labels(name, regions, truth)
    if tr is None:
        tr = truth["fixtures"][name]
        have = {r.shape_id for r in regions}
        ids = [s for v in tr["lines"].values() for s in v]
        return {"fixture": name, "ok": False, "stale": sum(s not in have for s in ids),
                "letters": len(ids), "which": which}
    ids = [s for v in tr["lines"].values() for s in v]
    ok = _same_labels(transfer_labels(regions, tr, regions, 1.0), tr)
    return {"fixture": name, "ok": bool(ok), "stale": 0, "letters": len(ids), "which": which}


def _lost(src_regions, truth: dict, carried: dict, regions, scale: float) -> list[dict]:
    """Labelled source letters no carried region took: each with the share
    of it the best target region covers (a merge reads high, a drop low)."""
    from shapely import affinity
    got = {sid for ids in carried["lines"].values() for sid in ids}
    by_id = {r.shape_id: r for r in src_regions}
    tgt = {r.shape_id: r for r in regions}
    took: dict[str, set] = {}
    for line, ids in truth["lines"].items():
        for sid in ids:
            took.setdefault(sid, set())
    # which source letters are represented: a target letter's best source
    for r in regions:
        if r.shape_id not in got:
            continue
        p = affinity.scale(r.polygon, 1.0 / scale, 1.0 / scale, origin=(0, 0)).buffer(0)
        best, share = None, 0.0
        for sid in took:
            q = by_id[sid].polygon.buffer(0)
            if not p.intersects(q):
                continue
            s = p.intersection(q).area / max(p.area, 1e-12)
            if s > share:
                best, share = sid, s
        if best is not None:
            took[best].add(r.shape_id)
    out = []
    for line, ids in truth["lines"].items():
        for sid in ids:
            if took[sid]:
                continue
            q = affinity.scale(by_id[sid].polygon, scale, scale, origin=(0, 0)).buffer(0)
            cover, host = 0.0, None
            for t in tgt.values():
                if t.polygon.intersects(q):
                    c = t.polygon.buffer(0).intersection(q).area / max(q.area, 1e-12)
                    if c > cover:
                        cover, host = c, t.shape_id
            out.append({"source_id": sid, "line": line, "cover": round(cover, 3), "host": host})
    return out


def labels_for(slug: str, data: dict, cache: Path | None, truth: dict | None = None) -> dict | None:
    """The hand labels on the pair's FINAL regions: {"lines": {line: [ids]},
    "ignore": [ids], "lost": [...], "how": str}; None when the pair has no
    labels (named, never scored 0)."""
    from tools.word_tagger_eval import transfer_labels
    truth = truth or load_truth()
    pl = truth.get(PAIRS_KEY, {}).get(slug)
    regions = data["regions"]
    if pl is not None and pl.get("carry_from"):
        src = pl["carry_from"]
        sdata = read_pickle(cache, src, data.get("arm", "off"))
        if sdata is None:
            return None
        sl = truth[PAIRS_KEY][src]
        src_regions = sdata["pre_tag"]
        scale = data["width_mm"] / sl["width_mm"]
        lab = {"lines": sl["lines"], "ignore": sl.get("ignore", [])}
        how = f"carried from {src} ({sl['width_mm']:g} mm, scale {scale:.3f})"
    elif pl is not None:
        src_regions, scale = data["pre_tag"], data["width_mm"] / pl["width_mm"]
        lab = {"lines": pl["lines"], "ignore": pl.get("ignore", [])}
        how = f"labelled at {pl['width_mm']:g} mm on this tool's pre-tag regions"
    else:
        name = source_fixture(slug)
        if name is None or name not in truth["fixtures"]:
            return None
        src_regions, w = corpus_regions(name, cache)
        scale = data["width_mm"] / w
        lab, which = corpus_labels(name, src_regions, truth)
        if lab is None:
            return None
        how = f"carried from corpus {name} ({which}, {w:g} mm, scale {scale:.3f})"
    carried = transfer_labels(src_regions, lab, regions, scale)
    carried["lost"] = _lost(src_regions, lab, carried, regions, scale)
    carried["how"] = how
    return carried


# ------------------------------------------------------------------ the text door, replayed

def door_rules() -> dict:
    """The text tagger's shipped constants, read off the module (never copied)."""
    from digitizer_core import textcluster as T
    return {"aspect_min": T.ASPECT_RATIO_MIN, "aspect_max": T.ASPECT_RATIO_MAX,
            "h_min": T.LETTER_MIN_HEIGHT_MM, "h_max": T.LETTER_MAX_HEIGHT_MM,
            "cv_max": T.LETTER_STROKE_CV_MAX, "rescued_cv_max": T.STROKE_CV_MAX,
            "height_ratio": T.LETTER_HEIGHT_RATIO, "stroke_ratio": T.SIMILARITY_RATIO,
            "ink_de": T.TEXT_CLUSTER_DELTA_E_MAX, "prox_mult": T.PROXIMITY_HEIGHT_MULT,
            "min_members": T.MIN_CLUSTER_MEMBERS}


def _admit(region, specks, chart, rules: dict, counters_as_drawn: bool):
    """-> (candidate or None, (rule, value, threshold) or None): the letter
    door's tests (`_letter_candidates`; the rescued door `_candidates` for a
    rescued shape) in its order."""
    from digitizer_core.textcluster import (_as_drawn, _Candidate, _skeleton_stroke_stats,
                                            _stats_of_polygon)
    x0, y0, x1, y1 = region.polygon.bounds
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return None, ("degenerate", None, None)
    rescued = bool(region.meta.get("rescued_small_shape"))
    if rescued:
        stats = _skeleton_stroke_stats(region)
        if stats is None:
            return None, ("no_skeleton", None, None)
        if stats.cv > rules["rescued_cv_max"]:
            return None, ("stroke_cv", stats.cv, rules["rescued_cv_max"])
    asp = w / h
    if not (rules["aspect_min"] <= asp <= rules["aspect_max"]):
        lim = rules["aspect_max"] if asp > rules["aspect_max"] else rules["aspect_min"]
        return None, ("aspect", asp, lim)
    if not rescued:
        if not (rules["h_min"] <= h <= rules["h_max"]):
            return None, ("height_bounds", h, rules["h_min"] if h < rules["h_min"] else rules["h_max"])
        stats = (_stats_of_polygon(_as_drawn(region, specks, chart)) if counters_as_drawn
                 else _skeleton_stroke_stats(region))
        if stats is None:
            return None, ("no_skeleton", None, None)
        if stats.cv > rules["cv_max"]:
            return None, ("stroke_cv", stats.cv, rules["cv_max"])
    return _Candidate(region=region, height_mm=h, width_mm=w, stroke_mean_mm=stats.mean_mm,
                      stroke_cv=stats.cv, cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0), None


def link_fails(a, b, chart, rules: dict) -> list[tuple]:
    """Every `textcluster._linked` term (letter round: `LETTER_HEIGHT_RATIO`
    and the ink link) the pair fails, as (rule, value, threshold, severity),
    severity > 1 meaning past the line. Empty: they link."""
    from digitizer_core.textcluster import _same_ink
    out = []
    lo, hi = sorted((a.height_mm, b.height_mm))
    r = lo / hi if hi > 0 else 0.0
    if r < rules["height_ratio"]:
        out.append(("height_ratio", r, rules["height_ratio"], rules["height_ratio"] / max(r, 1e-9)))
    if chart is not None and not _same_ink(a.region, b.region, chart):
        try:
            de = float(chart.delta_e(a.region.thread_index, b.region.thread_index))
        except (IndexError, TypeError, ValueError):
            de = float("nan")
        out.append(("other_thread", de, rules["ink_de"], de / rules["ink_de"]))
    lo, hi = sorted((a.stroke_mean_mm, b.stroke_mean_mm))
    r = lo / hi if hi > 0 else 0.0
    if r < rules["stroke_ratio"]:
        out.append(("stroke_ratio", r, rules["stroke_ratio"], rules["stroke_ratio"] / max(r, 1e-9)))
    d = math.hypot(a.cx - b.cx, a.cy - b.cy)
    reach = rules["prox_mult"] * max(a.height_mm, b.height_mm)
    if d > reach:
        out.append(("distance", d, reach, d / reach))
    return out


def replay_text_door(regions, chart, *, counters_as_drawn: bool = True,
                     rescued_ink_link: bool = True, rules: dict | None = None) -> dict:
    """`detect_text_clusters`' default path (wide_letters and part_touching
    aside: their splits change the region list, and a split piece is read
    on the final regions), replayed with every refusal named. ->
    {"cands": {sid: cand}, "refused": {sid: (rule, value, thr)},
     "nested": set, "tagged": set, "component": {sid: [sids]}}"""
    from digitizer_core.textcluster import _cluster, _drop_nested
    rules = rules or door_rules()
    specks = [r for r in regions if r.meta.get("rescued_small_shape")] if counters_as_drawn else []
    cands, refused = {}, {}
    rescued_c, letter_c = [], []
    for r in regions:
        c, why = _admit(r, specks, chart, rules, counters_as_drawn)
        if c is None:
            refused[r.shape_id] = why
            continue
        cands[r.shape_id] = c
        (rescued_c if r.meta.get("rescued_small_shape") else letter_c).append(c)
    rescued_kept = _drop_nested(rescued_c)
    nested = {c.region.shape_id for c in rescued_c} - {c.region.shape_id for c in rescued_kept}
    tagged: set[str] = set()
    component: dict[str, list[str]] = {}
    for g in _cluster(rescued_kept, rules["stroke_ratio"], chart if rescued_ink_link else None):
        if len(g) >= rules["min_members"]:
            ids = [c.region.shape_id for c in g]
            tagged.update(ids)
            for s in ids:
                component[s] = ids
    pool = [c for c in rescued_kept if c.region.shape_id not in tagged] + letter_c
    kept = _drop_nested(pool)
    nested |= {c.region.shape_id for c in pool} - {c.region.shape_id for c in kept}
    for g in _cluster(kept, rules["height_ratio"], chart):
        ids = [c.region.shape_id for c in g]
        for s in ids:
            component.setdefault(s, ids)
        if len(g) >= rules["min_members"]:
            tagged.update(ids)
            for s in ids:
                component[s] = ids
    return {"cands": cands, "refused": refused, "nested": nested, "tagged": tagged,
            "component": component}


def door_reason(sid: str, mates: list[str], replay: dict, chart, rules: dict | None = None) -> dict:
    """Why the text tagger left `sid` (a labelled letter) untagged, given its
    labelled line-mates `mates` (shape ids in the same replay)."""
    rules = rules or door_rules()
    if sid in replay["refused"]:
        rule, v, thr = replay["refused"][sid]
        return {"reason": rule, "value": v, "threshold": thr}
    if sid in replay["nested"]:
        return {"reason": "nested", "value": None, "threshold": None}
    if sid in replay["tagged"]:
        return {"reason": "tagged", "value": None, "threshold": None}
    me = replay["cands"][sid]
    admitted = [m for m in mates if m in replay["cands"] and m not in replay["nested"] and m != sid]
    if not admitted:
        return {"reason": "cluster_of_one", "value": 0, "threshold": rules["min_members"],
                "detail": "no line-mate admitted"}
    fails = {m: link_fails(me, replay["cands"][m], chart, rules) for m in admitted}
    if any(not f for f in fails.values()):
        n = len(replay["component"].get(sid, [sid]))
        return {"reason": "cluster_of_one", "value": n, "threshold": rules["min_members"],
                "detail": f"links, but its component holds {n}"}
    # the partner closest to linking: fewest failed terms, then the mildest
    best = min(fails, key=lambda m: (len(fails[m]), max(f[3] for f in fails[m]), m))
    rule, v, thr, _sev = max(fails[best], key=lambda f: f[3])
    return {"reason": rule, "value": v, "threshold": thr, "partner": best,
            "all": [f[0] for f in fails[best]]}


def house_reason(sid: str, mates: list[str], regions) -> str:
    """`textcluster._lettering_groups`' refusal of `sid`, shortly: its own
    admission (aspect, no_skeleton), the nesting drop, or its link/size."""
    from digitizer_core.textcluster import (ASPECT_RATIO_MAX, ASPECT_RATIO_MIN,
                                            MIN_CLUSTER_MEMBERS, SATIN_ANGLE_HEIGHT_RATIO,
                                            _Candidate, _cluster, _drop_nested,
                                            _skeleton_stroke_stats)
    raw = []
    for r in regions:
        st = _skeleton_stroke_stats(r)
        if st is None:
            if r.shape_id == sid:
                return "no_skeleton"
            continue
        x0, y0, x1, y1 = r.polygon.bounds
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0 or not (ASPECT_RATIO_MIN <= w / h <= ASPECT_RATIO_MAX):
            if r.shape_id == sid:
                return "aspect"
            continue
        raw.append(_Candidate(region=r, height_mm=h, width_mm=w, stroke_mean_mm=st.mean_mm,
                              stroke_cv=st.cv, cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0))
    kept = _drop_nested(raw)
    if sid not in {c.region.shape_id for c in kept}:
        return "nested"
    for g in _cluster(kept, SATIN_ANGLE_HEIGHT_RATIO):
        ids = {c.region.shape_id for c in g}
        if sid in ids:
            return "grouped" if len(g) >= MIN_CLUSTER_MEMBERS else f"group_of_{len(g)}"
    return "?"


def bucket(reason: str) -> str:
    """The brief's five buckets; anything else keeps its own name."""
    if reason.startswith(("guard:", "rung:")) or reason in ("lane_declined", "unsewn"):
        return "stage7_route"
    return reason


# ------------------------------------------------------------------ digitize (one pair, recorded)

def _rembg_venv():
    from tools.letter_gap_census import _rembg_venv as f
    return f()


@contextlib.contextmanager
def recording(record: dict, tagger_kw: dict | None = None):
    """While the pipeline runs: snapshot the regions handed to
    `detect_text_clusters` (the LAST call: the cored-counter pre-pass, when
    it runs, calls it first on its own generation), give it `tagger_kw`,
    and record every stage-7 rung call by shape id."""
    from digitizer_core import pipeline, stage7_sequence as s7
    orig_dtc = pipeline.detect_text_clusters
    saved = {n: getattr(s7, n) for n in RUNGS if hasattr(s7, n)}
    record.setdefault("rungs", {})
    record.setdefault("tag_calls", 0)

    def dtc(regions, p, **kw):
        record["pre_tag"] = copy.deepcopy(list(regions))
        record["tag_calls"] += 1
        record["tag_kwargs"] = {k: v for k, v in kw.items() if k != "chart"}
        return orig_dtc(regions, p, **{**kw, **(tagger_kw or {})})

    def wrap(name, f):
        @functools.wraps(f)
        def g(*a, **k):
            res = f(*a, **k)
            sid = a[1] if len(a) > 1 and isinstance(a[1], str) else k.get("shape_id")
            if sid is not None:
                try:
                    empty = bool(res[1].get("empty")) if isinstance(res[1], dict) else not res[0]
                except (TypeError, IndexError, AttributeError):
                    empty = not res
                record["rungs"].setdefault(sid, []).append((name, empty))
            return res
        return g
    pipeline.detect_text_clusters = dtc
    for n, f in saved.items():
        setattr(s7, n, wrap(n, f))
    try:
        yield record
    finally:
        pipeline.detect_text_clusters = orig_dtc
        for n, f in saved.items():
            setattr(s7, n, f)


def pickle_path(cache: Path, slug: str, arm: str) -> Path:
    return Path(cache) / slug / f"{arm}.pkl"


def read_pickle(cache, slug: str, arm: str = "off") -> dict | None:
    if cache is None:
        return None
    f = pickle_path(cache, slug, arm)
    return pickle.loads(f.read_bytes()) if f.exists() else None


def digitize_pair(slug: str, cache: Path, arm: str = "off", tagger_kw: dict | None = None,
                  sets: dict | None = None) -> dict:
    """Ours for `slug` at the pro's width (the Studio request, `pro_pair`),
    recorded (see `recording`), pickled to `cache/<slug>/<arm>.pkl`."""
    from tools import lettering_board as lb
    from tools import pro_pair as pp
    pair = lb.resolve_pair(slug)
    if pair.pro is None or pair.art is None:
        raise SystemExit(f"{slug}: missing {'pro' if pair.pro is None else 'art'} file")
    # every pair on the photo path the primary checkout has (a lane has no
    # rembg venv of its own, and MFab's regions are wrong without it)
    if _rembg_venv() is None and slug.startswith("mfab"):
        raise SystemExit(f"{slug}: no rembg venv on this machine (MFab's ids need its photo path)")
    width = pp.pro_counts(pair.pro)["width_mm"]
    record: dict = {}
    t = time.time()
    with recording(record, tagger_kw):
        d = pp.digitize(pair.art, width, pair.garment, sets)
    data = {"slug": slug, "arm": arm, "tagger_kw": tagger_kw or {}, "sets": sets or {},
            "width_mm": float(width), "garment": pair.garment, "art": str(pair.art),
            "pro": str(pair.pro), "cfg": d.cfg, "pre_tag": record.get("pre_tag", []),
            "tag_calls": record.get("tag_calls", 0), "tag_kwargs": record.get("tag_kwargs"),
            "regions": list(d.result.regions), "rungs": record["rungs"], "plan": d.plan,
            "secs": round(time.time() - t, 1)}
    f = pickle_path(cache, slug, arm)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(pickle.dumps(data))
    return data


# ------------------------------------------------------------------ read (one pair)

def lane_built(rungs: dict) -> set[str]:
    return {sid for sid, calls in rungs.items() if any(n == LANE and not e for n, e in calls)}


def route_reason(region, cfg, rungs: dict) -> str:
    """Why a DETECTED letter is not built by the lane (stage 7)."""
    calls = rungs.get(region.shape_id, [])
    if any(n == LANE for n, _e in calls):
        return "lane_declined"
    first = next((n for n, e in calls if not e), None)
    return f"rung:{first}" if first else "unsewn"


def guard_reason(region, cfg) -> str | None:
    """A tagged shape `is_lettering` refuses: which guard."""
    from digitizer_core.columns import is_drawing_fragment, is_solid_blob
    m = region.meta or {}
    if not (m.get("text_candidate") or m.get("lettering_group")):
        return None
    if getattr(cfg, "sew_enclosed_white_fields_fill", False) and m.get("sew_enclosed_white"):
        return "guard:white_field"
    if getattr(cfg, "lettering_columns_skip_blobs", False) and is_solid_blob(region.polygon):
        return "guard:solid_blob"
    if getattr(cfg, "lettering_columns_ink_link", False) and m.get("lettering_ink_stray"):
        return "guard:ink_stray"
    if (getattr(cfg, "lettering_columns_icon_guard", False) and m.get("lettering_group")
            and not m.get("text_candidate") and is_drawing_fragment(region.polygon)):
        return "guard:icon"
    return "guard:?"


def _pre_tag_of(region, pre_by_id: dict, pre_regions):
    """The pre-tag region a final region came from: same id, else the one
    holding most of it (a neck-split piece)."""
    if region.shape_id in pre_by_id:
        return pre_by_id[region.shape_id]
    best, share = None, 0.0
    p = region.polygon.buffer(0)
    for q in pre_regions:
        if q.polygon.intersects(p):
            s = q.polygon.buffer(0).intersection(p).area / max(p.area, 1e-12)
            if s > share:
                best, share = q, s
    return best


def census_pair(slug: str, data: dict, labels: dict, *, detect=None, replay=None) -> dict:
    """One pair's census. `detect`: {sid: bool} overriding `is_lettering`
    (the held-out grid reads detection without stage 7); `replay`: a
    precomputed `replay_text_door` of `data["pre_tag"]`."""
    from digitizer_core.columns import is_lettering
    from digitizer_core.threads import chart_for
    from tools.word_tagger_eval import kappa
    cfg, regions, rungs = data["cfg"], data["regions"], data["rungs"]
    chart = chart_for(cfg)
    line_of = {sid: line for line, ids in labels["lines"].items() for sid in ids}
    ignore = set(labels.get("ignore", []))
    scored = [r for r in regions if r.shape_id not in ignore]
    det = {r.shape_id: (detect[r.shape_id] if detect is not None and r.shape_id in detect
                        else bool(is_lettering(r, cfg))) for r in scored}
    built = lane_built(rungs)
    reach = {sid: d and sid in built for sid, d in det.items()}
    t = [r.shape_id in line_of for r in scored]
    pre = data["pre_tag"]
    pre_by_id = {r.shape_id: r for r in pre}
    if replay is None:
        replay = replay_text_door(pre, chart,
                                  counters_as_drawn=bool(getattr(cfg, "text_cluster_counters_as_drawn", True)),
                                  rescued_ink_link=bool(getattr(cfg, "text_cluster_rescued_ink_link", True)))
    misses = []
    for r in scored:
        sid = r.shape_id
        if sid not in line_of or reach[sid]:
            continue
        line = line_of[sid]
        row = {"sid": sid, "line": line, "h_mm": round(r.polygon.bounds[3] - r.polygon.bounds[1], 2),
               "w_mm": round(r.polygon.bounds[2] - r.polygon.bounds[0], 2)}
        if det[sid]:
            row["reason"] = route_reason(r, cfg, rungs)
        elif guard_reason(r, cfg):
            row["reason"] = guard_reason(r, cfg)
        else:
            src = _pre_tag_of(r, pre_by_id, pre)
            mates_final = [s for s in labels["lines"][line] if s != sid]
            mates = []
            for s in mates_final:
                fr = next((x for x in regions if x.shape_id == s), None)
                q = _pre_tag_of(fr, pre_by_id, pre) if fr is not None else None
                if q is not None and q is not src:
                    mates.append(q.shape_id)
            why = door_reason(src.shape_id, mates, replay, chart) if src is not None else \
                {"reason": "no_pre_tag_region"}
            if why["reason"] == "tagged":
                why = {"reason": "split_untagged",
                       "detail": "its pre-tag region was tagged; this piece was not"}
            row.update({k: (round(v, 3) if isinstance(v, float) else v) for k, v in why.items()})
            row["house"] = house_reason(sid, mates_final, regions)
        row["bucket"] = bucket(row["reason"])
        misses.append(row)
    for lost in labels.get("lost", []):
        misses.append({"sid": None, "source_id": lost["source_id"], "line": lost["line"],
                       "reason": "no_region", "bucket": "no_region", "cover": lost["cover"],
                       "host": lost["host"]})
    n_letters = sum(t) + len(labels.get("lost", []))
    out = {"slug": slug, "job": CENSUS_PAIRS.get(slug), "width_mm": data["width_mm"],
           "garment": data["garment"], "how": labels.get("how"), "regions": len(scored),
           "letters": n_letters, "letters_carried": sum(t),
           "detected": sum(1 for r in scored if r.shape_id in line_of and det[r.shape_id]),
           "reached": sum(1 for r in scored if r.shape_id in line_of and reach[r.shape_id]),
           "kappa_detect": kappa(t, [det[r.shape_id] for r in scored]),
           "kappa_reach": kappa(t, [reach[r.shape_id] for r in scored]),
           "false_pos": sum(1 for r in scored if r.shape_id not in line_of and det[r.shape_id]),
           "misses": misses,
           "_t": t, "_d": [det[r.shape_id] for r in scored],
           "_r": [reach[r.shape_id] for r in scored]}
    return out


def pooled_kappa(results: list[dict], key: str, rng=None, boot: int = 2000) -> dict:
    """Pooled kappa over every region of `results` ("_d" detection, "_r"
    reach), with a JOB-bootstrap 95% interval."""
    from tools.word_tagger_eval import kappa
    t = [x for r in results for x in r["_t"]]
    p = [x for r in results for x in r[key]]
    out = {"kappa": kappa(t, p)}
    if rng is not None and results:
        jobs = sorted({r["job"] for r in results})
        ks = []
        for _ in range(boot):
            pick = rng.choice(jobs, size=len(jobs), replace=True)
            tt = [x for j in pick for r in results if r["job"] == j for x in r["_t"]]
            pp = [x for j in pick for r in results if r["job"] == j for x in r[key]]
            k = kappa(tt, pp)
            if k is not None:
                ks.append(k)
        if ks:
            out["ci95"] = [float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))]
    return out


# ------------------------------------------------------------------ tables

def _k(x):
    return "n/a" if x is None else f"{x + 0.0:.3f}"


def census_table(results: list[dict], skipped: list[tuple[str, str]]) -> str:
    md = ["| pair | job | width mm | letters | detected | reached | detect kappa | reach kappa | false + | "
          + " | ".join(BUCKETS) + " | other |",
          "|" + "---|" * (9 + len(BUCKETS) + 1)]
    tot = {b: 0 for b in BUCKETS}
    tot_other: dict[str, int] = {}
    for r in results:
        cnt = {b: 0 for b in BUCKETS}
        other: dict[str, int] = {}
        for m in r["misses"]:
            b = m["bucket"]
            if b in cnt:
                cnt[b] += 1
                tot[b] += 1
            else:
                other[b] = other.get(b, 0) + 1
                tot_other[b] = tot_other.get(b, 0) + 1
        md.append(f"| {r['slug']} | {r['job']} | {r['width_mm']:.1f} | {r['letters']} | {r['detected']} | "
                  f"{r['reached']} | {_k(r['kappa_detect'])} | {_k(r['kappa_reach'])} | {r['false_pos']} | "
                  + " | ".join(str(cnt[b]) for b in BUCKETS) + " | "
                  + (", ".join(f"{k} {v}" for k, v in sorted(other.items())) or "0") + " |")
    letters = sum(r["letters"] for r in results)
    reached = sum(r["reached"] for r in results)
    detected = sum(r["detected"] for r in results)
    rng = np.random.default_rng(0)
    kd, kr = pooled_kappa(results, "_d", rng), pooled_kappa(results, "_r", rng)

    def ci(k):
        return f"{_k(k['kappa'])} [{k['ci95'][0]:.3f}, {k['ci95'][1]:.3f}]" if "ci95" in k else _k(k["kappa"])
    md.append(f"| **all** | | | {letters} | {detected} | {reached} | {ci(kd)} | {ci(kr)} | "
              f"{sum(r['false_pos'] for r in results)} | " + " | ".join(str(tot[b]) for b in BUCKETS) + " | "
              + (", ".join(f"{k} {v}" for k, v in sorted(tot_other.items())) or "0") + " |")
    if skipped:
        md += ["", "Not scored: " + "; ".join(f"{s} ({why})" for s, why in skipped)]
    return "\n".join(md) + "\n"


def miss_table(results: list[dict]) -> str:
    md = ["| pair | line | shape | h x w mm | reason | value / threshold | partner | house |",
          "|---|---|---|---|---|---|---|---|"]
    for r in results:
        for m in r["misses"]:
            vt = ""
            if m.get("value") is not None and m.get("threshold") is not None:
                v, th = m["value"], m["threshold"]
                vt = f"{v:.3f} / {th:.3f}" if isinstance(v, float) or isinstance(th, float) else f"{v} / {th}"
            elif m.get("cover") is not None:
                vt = f"cover {m['cover']:.2f} by {m['host']}"
            size = f"{m['h_mm']} x {m['w_mm']}" if "h_mm" in m else ""
            md.append(f"| {r['slug']} | {m['line']} | {m.get('sid') or m.get('source_id')} | {size} | "
                      f"{m['reason']} | {vt} | {m.get('partner', '')} | {m.get('house', '')} |")
    return "\n".join(md) + "\n"


def _clean(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.startswith("_")}


# ------------------------------------------------------------------ map (to label by eye)

def region_map(data: dict, out: Path, which: str = "pre_tag", ppm: float = 14.0,
               crop: tuple | None = None) -> list[dict]:
    """Draw `data[which]` regions in their thread colours with each one's
    index at its centroid, for labelling by eye. -> [{i, sid, h, w}]."""
    from PIL import Image, ImageDraw, ImageFont
    from digitizer_core.threads import chart_for
    chart = chart_for(data["cfg"])
    regs = data[which]
    xs = [b for r in regs for b in (r.polygon.bounds[0], r.polygon.bounds[2])]
    ys = [b for r in regs for b in (r.polygon.bounds[1], r.polygon.bounds[3])]
    x0, y0, x1, y1 = (min(xs), min(ys), max(xs), max(ys)) if crop is None else crop
    W, H = int((x1 - x0) * ppm) + 40, int((y1 - y0) * ppm) + 40
    img = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    def px(x, y):
        return ((x - x0) * ppm + 20, (y - y0) * ppm + 20)
    order = sorted(range(len(regs)), key=lambda i: -regs[i].polygon.area)
    rows = []
    for i in order:
        r = regs[i]
        try:
            rgb = tuple(int(c) for c in chart[r.thread_index].rgb)
        except Exception:                                   # noqa: BLE001 -- a picture only
            rgb = (180, 180, 180)
        geoms = getattr(r.polygon, "geoms", [r.polygon])
        for g in geoms:
            dr.polygon([px(*c) for c in g.exterior.coords], fill=rgb, outline=(255, 0, 255))
            for h in g.interiors:
                dr.polygon([px(*c) for c in h.coords], fill=(255, 255, 255), outline=(255, 0, 255))
    for i, r in enumerate(regs):
        c = r.polygon.representative_point()
        bx = r.polygon.bounds
        if crop is not None and not (x0 <= c.x <= x1 and y0 <= c.y <= y1):
            continue
        dr.text(px(c.x, c.y), str(i), fill=(255, 0, 0), font=font, anchor="mm")
        rows.append({"i": i, "sid": r.shape_id, "h": round(bx[3] - bx[1], 2),
                     "w": round(bx[2] - bx[0], 2), "thread": r.thread_index,
                     "rescued": bool(r.meta.get("rescued_small_shape"))})
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return rows


# ------------------------------------------------------------------ CLI

def _parse_kw(items):
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        out[k] = json.loads(v)
    return out


def run_census(cache: Path, slugs, arm: str = "off", truth: dict | None = None):
    truth = truth or load_truth()
    results, skipped = [], []
    for slug in slugs:
        data = read_pickle(cache, slug, arm)
        if data is None:
            skipped.append((slug, "not digitized"))
            continue
        labels = labels_for(slug, data, cache / "_corpus", truth)
        if labels is None:
            skipped.append((slug, "no hand labels (Golden Tee: its bevel has no honest letter call)"
                            if slug.startswith("goldentee") else "no hand labels"))
            continue
        results.append(census_pair(slug, data, labels))
    return results, skipped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("digitize")
    d.add_argument("--cache", type=Path, required=True)
    d.add_argument("--arm", default="off")
    d.add_argument("--kw", action="append", help="detect_text_clusters keyword, key=json")
    d.add_argument("--force", action="store_true")
    d.add_argument("slugs", nargs="*")
    r = sub.add_parser("read")
    r.add_argument("--cache", type=Path, required=True)
    r.add_argument("--arm", default="off")
    r.add_argument("--json", type=Path)
    r.add_argument("--md", type=Path)
    r.add_argument("slugs", nargs="*")
    c = sub.add_parser("check")
    c.add_argument("--cache", type=Path, required=True)
    m = sub.add_parser("map")
    m.add_argument("--cache", type=Path, required=True)
    m.add_argument("--arm", default="off")
    m.add_argument("--which", default="pre_tag")
    m.add_argument("--crop", help="x0,y0,x1,y1 mm")
    m.add_argument("--ppm", type=float, default=14.0)
    m.add_argument("slug")
    m.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)

    if a.cmd == "digitize":
        kw = _parse_kw(a.kw)
        for slug in a.slugs or list(CENSUS_PAIRS):
            if not a.force and pickle_path(a.cache, slug, a.arm).exists():
                print(f"{slug}: cached", flush=True)
                continue
            try:
                data = digitize_pair(slug, a.cache, a.arm, kw)
            except SystemExit as e:
                print(f"{slug}: SKIPPED -- {e}", flush=True)
                continue
            print(f"{slug}: {len(data['regions'])} regions, {data['secs']} s, "
                  f"tagger calls {data['tag_calls']}", flush=True)
        return 0
    if a.cmd == "check":
        from tools.thin_strokes import REAL_ART
        truth = load_truth()
        bad = 0
        for name in truth["fixtures"]:
            if name not in REAL_ART:
                continue
            res = carry_check(name, a.cache / "_corpus", truth)
            bad += not res["ok"]
            print(f"{name:12s} {res['which']:9s} letters {res['letters']:3d} stale {res['stale']:3d} "
                  f"carry {'exact' if res['ok'] else 'NOT EXACT'}", flush=True)
        return 1 if bad else 0
    if a.cmd == "map":
        data = read_pickle(a.cache, a.slug, a.arm)
        crop = tuple(float(x) for x in a.crop.split(",")) if a.crop else None
        rows = region_map(data, a.out, a.which, a.ppm, crop)
        for row in rows:
            print(json.dumps(row))
        return 0
    results, skipped = run_census(a.cache, a.slugs or list(CENSUS_PAIRS), a.arm)
    text = census_table(results, skipped) + "\n" + miss_table(results)
    print(text)
    if a.md:
        a.md.write_text(text, encoding="utf-8")
    if a.json:
        a.json.write_text(json.dumps({"pairs": [_clean(r) for r in results], "skipped": skipped},
                                     indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
