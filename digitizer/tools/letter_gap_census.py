"""letter_gap_census: where neighbouring letters of a word TOUCH in thread,
ours beside the professional's, and why ours do.

W3-07 (2026-10-25). At the 2026-10-23 band reader's 1.0 mm opening our
serifs fused Fremont's O-T-E and N-T where the pro's letters stood apart
(`docs/lettering-5-10mm-2026-10-23.md`). This counts it on every paired job
with a word in or near the 5-10 mm band, and says for each of OUR touching
pairs whether the trace, the construction or the pull compensation closed it.

THE READER (`tools/small_text_columns.py`, one reader, both files as DST,
each in its own frame): needle-down stitches drawn 0.4 mm wide at 20 px/mm,
opened 0.55 mm, connected pieces; a line of text is found by its height and
its place as a share of the file's own height (`WORDS`); `word_letters`
shares a joined piece out between the letters of the known text and parts
it. Per pair of neighbours: the VISIBLE gap (nearest distance between the
two letters' thread, 0 when they touch); a touch is a TIP when the letters
part at a 1.0 mm opening and FUSED when they do not; `contact_mm` is the
thread they share. Per word: the minimum gap, the pairs that touch, the
pairs fused, the median gap of the pairs that do not touch.

ATTRIBUTION (ours only: the plan is ours to read). Each letter of our file
is matched to the plan's shapes with needle points in it, in the letter's
own colour block; for every pair `d4` (below) is kept, and for a pair that
touches:
  - `d4`: the distance between the two letters' stage-4 polygons (the trace)
    and `d5` between their stage-5 sewing polygons; 0 when one traced shape
    holds a real share of both letters (the trace joined them);
  - `over_a` / `over_b`: how far each letter's needle points FACING the other
    letter (within d4 + 1 mm of it) lie outside its own traced polygon, and
    whether the furthest is a column END (first or last three crosses of its
    run) or a RAIL;
  - `comp_a` / `comp_b`: the letter's own rail offset -- the median distance
    of its needle points that lie outside its polygon (underlay left out),
    which is the pull compensation the rails carry (ROADMAP gate 1:
    reported, never changed).
  A needle laid exactly on the outline still shows 0.2 mm of thread each
  side, so with the reader's own 0.4 mm thread:
    trace         d4 <= 0.4: the polygons touch or nearly touch;
    pull comp     d4 - 0.4 - comp_a - comp_b <= 0: the rails' compensation
                  alone closes what is left;
    construction  otherwise: needles past outline + comp close it -- a fan
                  or end cross run past the outline, or a serif absorbed.

PROTOTYPE (`--hold-back`, harness only, never the engine): for a pair
attributed to construction or pull comp, every needle of either letter that
comes within 0.25 + 0.4 mm of the other's needle path is pushed back, the
two sharing the shortfall by what each overruns past outline + comp --
0.25 is the re-set's sewn-gap candidate (`cfg.small_text_cap_letter_gap_mm`,
A GATE-1 CANDIDATE: whether 0.25 mm stays open on cloth depends on pull and
thread spread) -- and the pair is read again (`hold_back`).

LEGIBILITY: `tools.word_legibility` at a 4 mm shrink, imported, for the
jobs whose words it pins; the others are named as not pinned, never 0.

  python -m tools.letter_gap_census --digitize hotel_fremont_hat,precision_drone --cache DIR
  python -m tools.letter_gap_census --read hotel_fremont_hat,precision_drone --cache DIR \\
      [--crops DIR] [--hold-back] [--legibility] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools import small_text_columns as stc  # noqa: E402

THREAD_MM = stc.THREAD_MM
#: the re-set's sewn-gap candidate (`cfg.small_text_cap_letter_gap_mm`), gate 1
HOLD_GAP_MM = 0.25
FACING_MM = 1.0       # a needle point within d4 + this of the other letter faces it
END_CROSSES = 3       # a needle point in a run's first or last this-many crosses is a column END

#: pair slug (`tools.pro_intake` registry) -> its lines of text: (text, the
#: line's centre as a share of the file's own height, optional x share range),
#: and the `tools.word_legibility` job that pins its words (None: not pinned)
WORDS = {
    "hotel_fremont_hat": {"lines": [("HOTEL FREMONT", 0.50, None)], "legibility": "fremont"},
    "hotel_fremont_patch": {"lines": [("HOTEL FREMONT", 0.50, None)], "legibility": None},
    "precision_drone": {"lines": [("PRECISION", 0.70, None)], "legibility": None},
    "proseal_hat": {"lines": [("PROSEAL", 0.78, None)], "legibility": "proseal"},
    "mfab_hat": {"lines": [("AND WELDING", 0.71, (0.0, 0.77))], "legibility": "mfab"},
    "gaulke_roofing_hat": {"lines": [("C GOLKE INDUSTRIES", 0.75, None),
                                     ("STEEL ROOFING & SUPPLY", 0.93, None)], "legibility": None},
    "gaulke_roofing_lc": {"lines": [("C GOLKE INDUSTRIES", 0.75, None),
                                    ("STEEL ROOFING & SUPPLY", 0.93, None)], "legibility": None},
    "becker_hat_small": {"lines": [("MARINE", 0.85, None)], "legibility": "becker"},
}


# ------------------------------------------------------------------ reading a file
def find_line(pcs, y_share: float, x_share=None) -> list[dict]:
    """The pieces of the line of text nearest `y_share` of the file's own
    height (lines of two pieces or more), inside `x_share` of its width."""
    W = max(p["x1"] for p in pcs)
    H = max(p["y1"] for p in pcs)
    lines = [ln for ln in stc.text_lines(pcs) if len(ln["pieces"]) >= 2]
    if not lines:
        return []
    ln = min(lines, key=lambda l: abs(l["cy"] - y_share * H))
    lo, hi = x_share or (0.0, 1.0)
    return [p for p in ln["pieces"] if lo * W <= (p["x0"] + p["x1"]) / 2 <= hi * W]


def word_rows(text: str, read: dict) -> list[dict]:
    """A line read by `word_letters` -> one row per word: letters, pairs,
    minimum gap, touching / fused pairs, median gap of the pairs apart."""
    words = text.split()
    rows, i = [], 0
    pairs = read["pairs"]
    for w in words:
        n = len(w)
        ps = [p for p in pairs if i <= p["i"] < i + n - 1] if read["letters"] else []
        apart = [p["gap_mm"] for p in ps if p["gap_mm"] > 0]
        lt = read["letters"][i:i + n]
        cx = [(l["x0"] + l["x1"]) / 2 for l in lt]
        rows.append({"word": w, "letters": n, "pairs": len(ps), "note": read["note"],
                     "width_med": round(float(np.median([l["x1"] - l["x0"] for l in lt])), 2) if lt else None,
                     "pitch_med": round(float(np.median(np.diff(cx))), 2) if len(cx) > 1 else None,
                     "span_mm": round(lt[-1]["x1"] - lt[0]["x0"], 2) if lt else None,
                     "cap_mm": (round(float(np.median([l["y1"] - l["y0"] for l in read["letters"][i:i + n]]))
                                      - THREAD_MM, 2) if read["letters"] else None),
                     "min_gap": round(min(p["gap_mm"] for p in ps), 2) if ps else None,
                     "touch": [p["pair"] for p in ps if p["gap_mm"] == 0],
                     "fused": [p["pair"] for p in ps if p["gap_mm"] == 0 and p["fused"]],
                     "gap_med": round(float(np.median(apart)), 2) if apart else None,
                     "gaps": [p["gap_mm"] for p in ps]})
        i += n
    return rows


def knocked_out(pcs, line) -> bool:
    """True when a piece of the line's own thread holds the whole line in its
    box: the letters are holes in a backdrop (MFab's white letters left as
    fabric inside their black keyline), and the pieces read are slivers of
    backdrop, not letters."""
    if not line:
        return False
    blocks = {p["block"] for p in line}
    x0, x1 = min(p["x0"] for p in line), max(p["x1"] for p in line)
    y0, y1 = min(p["y0"] for p in line), max(p["y1"] for p in line)
    return any(p["block"] in blocks and all(p is not q for q in line)
               and p["x0"] <= x0 and p["x1"] >= x1 and p["y0"] <= y0 and p["y1"] >= y1 for p in pcs)


def read_side(blocks, spec) -> list[dict]:
    """Every line of `spec` read in one file -> [{"text", "read", "words"}]."""
    pcs = stc.pieces(blocks)
    out = []
    for text, ys, xs in spec["lines"]:
        line = find_line(pcs, ys, xs)
        if knocked_out(pcs, line):
            read = {"letters": [], "pairs": [], "units": len(line),
                    "note": "letters knocked out of a backdrop of their own thread: no letter thread"}
        else:
            read = stc.word_letters(line, text)
        out.append({"text": text, "read": read, "words": word_rows(text, read)})
    return out


# ------------------------------------------------------------------ ours: digitize + keep the plan's geometry
def _rembg_venv():
    """The isolated rembg venv this checkout has, else the primary
    checkout's (a lane under .claude/worktrees/ has none of its own, and
    MFab's photo path needs it); None when neither exists."""
    from digitizer_core import stage1_photo_prep as s1
    if s1.REMBG_VENV_PYTHON.is_file():
        return s1.REMBG_VENV_PYTHON
    for p in DIGITIZER.parents:
        for cand in (p / "digitizer" / "rembg_isolated" / "venv" / "Scripts" / "python.exe",
                     p / "digitizer" / "rembg_isolated" / "venv" / "bin" / "python"):
            if cand.is_file():
                s1.REMBG_VENV_PYTHON = cand
                return cand
    return None


def digitize(slug: str, cache: Path) -> Path:
    """Ours for `slug` at the pro's width, the Studio's request
    (`small_text_columns.digitize_dst`) -> cache/<slug>/: ours.dst,
    design.json (`plan_to_design`, for word_legibility) and geometry.json
    (stage-4 regions, stage-5 sewing polygons, every run with its shape)."""
    from digitizer_core import pipeline
    from tools.pro_intake import pair_record
    rec = pair_record(slug)
    if rec is None:
        raise SystemExit(f"{slug}: not in the pro_intake registry on this machine")
    venv = _rembg_venv()
    job = {"art": rec["art"], "width_mm": rec["width_mm"], "garment": rec["garment_id"] or "hat_front"}
    got: dict = {}
    resolve = pipeline.resolve_overlaps

    def spy(regions, *a, **k):
        planned, warn = resolve(regions, *a, **k)
        got["planned"] = [{"id": p.region.shape_id, "wkt": p.polygon.wkt} for p in planned]
        return planned, warn
    pipeline.resolve_overlaps = spy
    try:
        path, d = stc.digitize_dst(job, {}, cache / slug)
    finally:
        pipeline.resolve_overlaps = resolve
    import pystitch
    pat = pystitch.read(str(path))
    xy = [(x, y) for x, y, c in pat.stitches if c & pystitch.COMMAND_MASK == pystitch.STITCH]
    offset = [min(x for x, _ in xy) / 10.0, min(y for _, y in xy) / 10.0]
    keep = (str, int, float, bool, type(None))
    try:
        engine = subprocess.run(["git", "-C", str(DIGITIZER), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        engine = ""
    geo = {"slug": slug, "width_mm": job["width_mm"], "garment": job["garment"], "offset": offset,
           "rembg": str(venv) if venv else None, "engine": engine,
           "regions": [{"id": r.shape_id, "wkt": r.polygon.wkt,
                        "meta": {k: v for k, v in r.meta.items() if isinstance(v, keep)}} for r in d.result.regions],
           "planned": got.get("planned", []),
           "runs": [{"id": r.shape_id, "kind": r.kind, "role": r.role, "block": bi,
                     "points": [[round(x, 4), round(y, 4)] for x, y in r.points]}
                    for bi, b in enumerate(d.plan.blocks) for r in b.runs]}
    (cache / slug / "geometry.json").write_text(json.dumps(geo), encoding="utf-8")
    (cache / slug / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
    print(f"{slug}: {d.plan.stats.stitch_count} stitches, {d.plan.stats.trims} trims, {d.secs:.0f} s"
          f"{'' if venv else ' (NO rembg venv)'}", flush=True)
    return path


# ------------------------------------------------------------------ attribution
def _in_mask(letter, x, y) -> bool:
    u, v = int(round(x * stc.PPM)) - letter["ox"], int(round(y * stc.PPM)) - letter["oy"]
    m = letter["mask"]
    return 0 <= v < m.shape[0] and 0 <= u < m.shape[1] and bool(m[v, u])


def _sewn(r) -> bool:
    return r["kind"] not in ("travel", "tie")


def letter_shapes(letter, runs, offset) -> dict[str, int]:
    """shape id -> how many of its needle points fall inside `letter`'s
    thread, in the letter's own colour block (a plan block is a DST colour
    block, one to one: a backdrop fill sewn under the letters is another
    block); shapes with fewer than five are left out."""
    hits: dict[str, int] = {}
    for r in runs:
        if not _sewn(r) or r["block"] != letter["block"]:
            continue
        for x, y in r["points"]:
            if _in_mask(letter, x - offset[0], y - offset[1]):
                hits[r["id"]] = hits.get(r["id"], 0) + 1
    return {k: v for k, v in hits.items() if v >= 5}


def _points(shapes, runs) -> list[tuple]:
    """Every needle point of `shapes` (plan mm, all of them: an end cross run
    into the neighbour's thread is still this letter's) -> (kind, end, xy);
    `end` = in its run's first or last END_CROSSES crosses."""
    out = []
    for r in runs:
        if r["id"] in shapes and _sewn(r):
            n = len(r["points"])
            out += [(r["kind"], min(j, n - 1 - j) < 2 * END_CROSSES, tuple(p)) for j, p in enumerate(r["points"])]
    return out


def attribute(a, b, geo, regions, planned) -> dict:
    """Why letters `a` and `b` (word_letters' dicts, ours) touch (module
    docstring) -> the row of the attribution table."""
    from shapely.geometry import MultiPoint, Point
    from shapely.ops import unary_union
    off = geo["offset"]
    sa, sb = letter_shapes(a, geo["runs"], off), letter_shapes(b, geo["runs"], off)
    both = set()
    for k in set(sa) & set(sb):
        if min(sa[k], sb[k]) >= 0.3 * (sa[k] + sb[k]):
            both.add(k)         # a real share of it in each letter
        else:                   # a few needles over the line: it is the other letter's
            (sa if sa[k] < sb[k] else sb).pop(k)
    if both:                    # one traced shape holds both letters: the trace joined them
        return {"cause": "trace", "why": "one traced shape holds both letters", "d4": 0.0, "d5": 0.0,
                "needle_gap": None, "over_a": None, "over_b": None, "comp_a": None, "comp_b": None,
                "excess_a": None, "excess_b": None, "where_a": None, "where_b": None,
                "kind_a": None, "kind_b": None, "shapes_a": sorted(sa), "shapes_b": sorted(sb)}
    if not sa or not sb:
        return {"cause": "unread", "why": "no plan shape found in a letter"}
    pa = unary_union([regions[k] for k in sa if k in regions])
    pb = unary_union([regions[k] for k in sb if k in regions])
    qa = unary_union([planned[k] for k in sa if k in planned]) if any(k in planned for k in sa) else pa
    qb = unary_union([planned[k] for k in sb if k in planned]) if any(k in planned for k in sb) else pb
    d4, d5 = pa.distance(pb), qa.distance(qb)

    def side(shapes, own, other):
        pts = [(kind, end, p) for kind, end, p in _points(shapes, geo["runs"]) if kind != "underlay"]
        outside = [o for o in (own.distance(Point(p)) for _k, _e, p in pts) if o > 1e-6]
        comp = float(np.median(outside)) if outside else 0.0
        facing = [(own.distance(Point(p)), end, kind, p) for kind, end, p in pts
                  if other.distance(Point(p)) <= d4 + FACING_MM]
        if not facing:
            return comp, 0.0, None, None, []
        o, end, kind, _p = max(facing, key=lambda t: t[0])
        return comp, o, ("end" if end else "rail"), kind, [q for *_r, q in facing]
    comp_a, over_a, where_a, kind_a, face_a = side(sa, pa, pb)
    comp_b, over_b, where_b, kind_b, face_b = side(sb, pb, pa)
    needle = (MultiPoint(face_a).distance(MultiPoint(face_b)) if face_a and face_b else None)
    if d4 <= THREAD_MM:
        cause = "trace"
    elif d4 - THREAD_MM - comp_a - comp_b <= 0:
        cause = "pull comp"
    else:
        cause = "construction"
    return {"cause": cause, "d4": round(d4, 2), "d5": round(d5, 2),
            "needle_gap": None if needle is None else round(needle, 2),
            "over_a": round(over_a, 2), "over_b": round(over_b, 2),
            "comp_a": round(comp_a, 2), "comp_b": round(comp_b, 2),
            "excess_a": round(over_a - comp_a, 2), "excess_b": round(over_b - comp_b, 2),
            "where_a": where_a, "where_b": where_b, "kind_a": kind_a, "kind_b": kind_b,
            "shapes_a": sorted(sa), "shapes_b": sorted(sb)}


# ------------------------------------------------------------------ prototype: hold a column end back
def _path(blocks, member):
    """The needle path of the points `member` accepts, as lines (None when
    it has fewer than two consecutive points)."""
    from shapely.geometry import LineString, MultiLineString
    segs = []
    for b in blocks:
        cur = []
        for q in b + [None]:
            if q is not None and member(q):
                cur.append(q)
                continue
            if len(cur) > 1:
                segs.append(LineString(cur))
            cur = []
    return MultiLineString(segs) if segs else None


def hold_back(blocks, in_a, in_b, share_a: float = 0.5, gap_mm: float = HOLD_GAP_MM):
    """`blocks` with the two letters' facing needles held apart: every point
    of letter A (`in_a(q)`) closer than gap + 0.4 mm to B's needle path, and
    every point of B closer to A's, pushed straight away from the other's
    ORIGINAL path, A taking `share_a` of the shortfall and B the rest ->
    (blocks, {"a", "b"} points moved, largest move mm). Harness only: what
    holding the column ends back buys, never the engine."""
    from shapely.geometry import Point
    from shapely.ops import nearest_points
    L = gap_mm + THREAD_MM
    pa, pb = _path(blocks, in_a), _path(blocks, in_b)
    if pa is None or pb is None:
        return blocks, {"a": 0, "b": 0}, 0.0
    out, moved, biggest = [], {"a": 0, "b": 0}, 0.0
    for b in blocks:
        nb = []
        for q in b:
            side = None if q is None else ("a" if in_a(q) else "b" if in_b(q) else None)
            share = share_a if side == "a" else 1.0 - share_a
            other = pb if side == "a" else pa
            if side is None or share <= 0:
                nb.append(q)
                continue
            d = other.distance(Point(q))
            if d >= L:
                nb.append(q)
                continue
            n = nearest_points(other, Point(q))[0]
            vx, vy = q[0] - n.x, q[1] - n.y
            if math.hypot(vx, vy) < 1e-6:      # on the other's path: away from its middle
                c = other.centroid
                vx, vy = q[0] - c.x, q[1] - c.y
            ln = math.hypot(vx, vy) or 1e-9
            step = (L - d) * share
            nq = (q[0] + vx / ln * step, q[1] + vy / ln * step)
            biggest = max(biggest, step)
            moved[side] += 1
            nb.append(nq)
        out.append(nb)
    return out, moved, round(biggest, 2)


def shape_member(shapes, geo):
    """A predicate on our DST's points (own frame, mm): is this needle point
    one of `shapes`' run points? Matched on the file's exact 0.1 mm grid."""
    ox, oy = round(geo["offset"][0] * 10), round(geo["offset"][1] * 10)
    keys = {(round(x * 10) - ox, round(y * 10) - oy) for r in geo["runs"] if r["id"] in shapes and _sewn(r)
            for x, y in r["points"]}
    return lambda q: (round(q[0] * 10), round(q[1] * 10)) in keys


# ------------------------------------------------------------------ crops
def crop(blocks, letters_pair, ppm: float = 40.0, pad: float = 1.2):
    """Two neighbours drawn in their file's own frame (`render_band`), the
    pair's colour blocks dark."""
    a, b = letters_pair
    band = [min(a["y0"], b["y0"]), max(a["y1"], b["y1"]), a["x0"], b["x1"]]
    return stc.render_band(blocks, band, {a["block"], b["block"]}, ppm=ppm, pad_mm=pad)


def _label(img, text):
    import cv2
    out = np.full((img.shape[0] + 34, img.shape[1], 3), 255, np.uint8)
    out[34:] = img
    cv2.putText(out, text, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
    return out


def _hstack(imgs, gap: int = 20):
    h = max(i.shape[0] for i in imgs)
    w = sum(i.shape[1] for i in imgs) + gap * (len(imgs) - 1)
    out = np.full((h, w, 3), 255, np.uint8)
    x = 0
    for i in imgs:
        out[:i.shape[0], x:x + i.shape[1]] = i
        x += i.shape[1] + gap
    return out


# ------------------------------------------------------------------ one pair
def read_pair(slug: str, cache: Path, crops: Path | None = None, hold: bool = False,
              legibility: bool = False) -> dict:
    """The census of one paired job (module docstring)."""
    from shapely import wkt as swkt
    from tools.pro_intake import pair_record
    spec = WORDS[slug]
    rec = pair_record(slug)
    ours_path = cache / slug / "ours.dst"
    geo_path = cache / slug / "geometry.json"
    if rec is None or not ours_path.is_file() or not geo_path.is_file():
        return {"slug": slug, "skipped": "not digitized here (run --digitize) or not registered"}
    geo = json.loads(geo_path.read_text(encoding="utf-8"))
    sides = {"ours": stc.read_blocks(ours_path), "pro": stc.read_blocks(rec["dst"])}
    reads = {s: read_side(b, spec) for s, b in sides.items()}
    regions = {r["id"]: swkt.loads(r["wkt"]) for r in geo["regions"]}
    planned = {r["id"]: swkt.loads(r["wkt"]) for r in geo["planned"]}
    out = {"slug": slug, "width_mm": geo["width_mm"], "garment": geo["garment"], "engine": geo.get("engine"),
           "rembg": geo.get("rembg"), "lines": []}
    for li, (text, _y, _x) in enumerate(spec["lines"]):
        ro, rp = reads["ours"][li], reads["pro"][li]
        row = {"text": text, "words": {"ours": ro["words"], "pro": rp["words"]}, "pairs": [], "attribution": []}
        lo, lp = ro["read"]["letters"], rp["read"]["letters"]
        for pr in ro["read"]["pairs"]:
            if pr["space"]:
                continue
            i = pr["i"]
            a, b = lo[i], lo[i + 1]
            pro_pair = next((q for q in rp["read"]["pairs"] if q["i"] == i), None) if len(lp) == len(lo) else None
            att = {"pair": pr["pair"], "i": i, "ours_gap": pr["gap_mm"], "ours_fused": pr["fused"],
                   "ours_contact": pr["contact_mm"],
                   "pro_gap": pro_pair["gap_mm"] if pro_pair else None,
                   "pro_contact": pro_pair["contact_mm"] if pro_pair else None,
                   **attribute(a, b, geo, regions, planned)}
            row["pairs"].append({**{k: att.get(k) for k in ("pair", "i", "d4", "ours_gap", "pro_gap")},
                                 # where each file puts the two letters: centre to centre, and their widths
                                 "ours_pitch": round((b["x0"] + b["x1"] - a["x0"] - a["x1"]) / 2, 2),
                                 "ours_w": [round(a["x1"] - a["x0"], 2), round(b["x1"] - b["x0"], 2)],
                                 **({"pro_pitch": round((lp[i + 1]["x0"] + lp[i + 1]["x1"] - lp[i]["x0"]
                                                         - lp[i]["x1"]) / 2, 2),
                                     "pro_w": [round(lp[i]["x1"] - lp[i]["x0"], 2),
                                               round(lp[i + 1]["x1"] - lp[i + 1]["x0"], 2)]}
                                    if pro_pair else {})})
            if pr["gap_mm"] > 0:
                continue
            if hold and att["cause"] in ("construction", "pull comp"):
                # the shortfall is shared by what each letter overruns past outline + comp;
                # with neither past it (pull comp alone) it is shared evenly
                ea, eb = max(0.0, att["excess_a"]), max(0.0, att["excess_b"])
                share_a = 0.5 if ea + eb < 0.02 else ea / (ea + eb)
                nb, moved, big = hold_back(sides["ours"], shape_member(att["shapes_a"], geo),
                                           shape_member(att["shapes_b"], geo), share_a)
                again = stc.word_letters(find_line(stc.pieces(nb), *spec["lines"][li][1:]), text)
                hp = next((q for q in again["pairs"] if q["i"] == i), None)
                att["hold_back"] = {"share_a": round(share_a, 2), "points": moved, "max_move_mm": big,
                                    "gap_mm": hp["gap_mm"] if hp else None,
                                    "contact_mm": hp["contact_mm"] if hp else None}
                if crops is not None:
                    att["_held"] = (nb, again)
            if crops is not None and len(lp) == len(lo):
                import cv2
                crops.mkdir(parents=True, exist_ok=True)
                imgs = [_label(crop(sides["ours"], (a, b)),
                               f"ours {pr['pair']}  {'FUSED' if pr['fused'] else 'tip'} {pr['contact_mm']:.2f} mm"),
                        _label(crop(sides["pro"], (lp[i], lp[i + 1])),
                               f"pro  gap {pro_pair['gap_mm']:.2f} mm" if pro_pair else "pro")]
                held = att.pop("_held", None)
                if held is not None and len(held[1]["letters"]) == len(lo):
                    hb = att["hold_back"]
                    imgs.insert(1, _label(crop(held[0], (held[1]["letters"][i], held[1]["letters"][i + 1])),
                                          f"held 0.25 (gate 1)  gap {hb['gap_mm']:.2f} mm"))
                name = f"{slug}_{li}_{i:02d}_{pr['pair']}.png".replace("&", "and")
                cv2.imwrite(str(crops / name), _hstack(imgs))
                att["crop"] = name
            att.pop("_held", None)
            row["attribution"].append(att)
        out["lines"].append(row)
    if legibility:
        out["legibility"] = legibility_4mm(slug, spec, cache, rec)
    return out


def legibility_4mm(slug, spec, cache, rec) -> dict:
    """`tools.word_legibility` at a 4 mm shrink for the census's words, ours
    and the pro's (imported, run as that tool runs it); a job it does not pin
    is named, not scored."""
    from tools import word_legibility as wl
    job = spec.get("legibility")
    if not job:
        return {"note": "no words pinned in word_legibility for this art"}
    if not wl.tesseract_available():
        return {"note": "OCR UNAVAILABLE (no tesseract on this box)"}
    from tools.glyph_legibility import load_source
    want = {w for text, *_ in spec["lines"] for w in text.split()}
    words = [w for w in wl.pinned_words(job) if w["text"] in want]
    ours = json.loads((cache / slug / "design.json").read_text(encoding="utf-8"))
    pro = wl.load_pro_design(Path(rec["pes"] or rec["dst"]))
    rgb, alpha = load_source(Path(rec["art"]))
    res = wl.read_job(job, ours, pro, words, rgb, alpha, heights=(4.0,), ours_width_mm=rec["width_mm"])
    rows = {}
    for r in res["rows"]:
        if r.get("size") == "4mm":
            rows.setdefault(r["text"], {})[r["file"]] = {"read": r.get("read"), "cc": r.get("cc")}
        elif not r.get("located") and "size" not in r:
            rows.setdefault(r["text"], {})[r["file"]] = {"read": None, "cc": None, "note": r.get("note")}
    return {"words": rows, "ours": res["figures"].get("ours/4mm"), "pro": res["figures"].get("pro/4mm")}


# ------------------------------------------------------------------ tables
def table(results: list[dict]) -> str:
    """The census as markdown: one row per word and side."""
    out = ["| job | word | side | cap mm | span mm | letter w med | pitch med | min gap | touching pairs | "
           "fused (1.0 mm) | gap med (apart) |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for res in results:
        if res.get("skipped"):
            out.append(f"| {res['slug']} | — | — | skipped: {res['skipped']} | | | | | | | |")
            continue
        for ln in res["lines"]:
            for wo, wp in zip(ln["words"]["ours"], ln["words"]["pro"]):
                if wo["letters"] < 2:
                    continue
                for side, w in (("ours", wo), ("pro", wp)):
                    if w["note"]:
                        out.append(f"| {res['slug']} | {w['word']} | {side} | n/a: {w['note']} | | | | | | | |")
                        continue
                    out.append(f"| {res['slug']} | {w['word']} | {side} | {w['cap_mm']} | {w['span_mm']} | "
                               f"{w['width_med']} | {w['pitch_med']} | {w['min_gap']} | "
                               f"{len(w['touch'])} {' '.join(w['touch'])} | {len(w['fused'])} {' '.join(w['fused'])} | "
                               f"{w['gap_med']} |")
    return "\n".join(out)


def pair_table(results: list[dict]) -> str:
    """Every pair of neighbours: the traced gap (our stage-4 polygons, the
    art's spacing at the job's width) beside both visible gaps."""
    out = ["| job | line | traced gap d4 / ours visible / pro visible, per pair |", "|---|---|---|"]
    for res in results:
        for ln in res.get("lines", []):
            cells = [f"{p['pair']} {p['d4'] if p['d4'] is not None else '-'} / {p['ours_gap']} / "
                     f"{p['pro_gap'] if p['pro_gap'] is not None else '-'}" for p in ln["pairs"]]
            out.append(f"| {res['slug']} | {ln['text']} | {'; '.join(cells)} |")
    return "\n".join(out)


def attribution_table(results: list[dict]) -> str:
    out = ["| job | pair | ours touch | pro gap | d4 | d5 | over a / b | comp a / b | where a / b | cause | hold-back 0.25 |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for res in results:
        for ln in res.get("lines", []):
            for a in ln["attribution"]:
                if a["cause"] == "unread":
                    out.append(f"| {res['slug']} | {a['pair']} | | | | | | | | unread: {a['why']} | |")
                    continue
                hb = a.get("hold_back")
                hbs = (f"{hb['points']['a']} + {hb['points']['b']} pts (a takes {hb['share_a']}), "
                       f"max {hb['max_move_mm']} mm -> gap {hb['gap_mm']}" if hb else "")
                out.append(f"| {res['slug']} | {a['pair']} | {'FUSED' if a['ours_fused'] else 'tip'} "
                           f"{a['ours_contact']:.2f} | {a['pro_gap']} | {a['d4']} | {a['d5']} | "
                           f"{a['over_a']} / {a['over_b']} | {a['comp_a']} / {a['comp_b']} | "
                           f"{a['where_a']} {a['kind_a']} / {a['where_b']} {a['kind_b']} | {a['cause']} | {hbs} |")
    return "\n".join(out)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--digitize", help="comma-separated pair slugs to digitize into --cache")
    ap.add_argument("--read", help="comma-separated pair slugs to read from --cache ('all': every WORDS pair)")
    ap.add_argument("--cache", type=Path, default=Path("letter_gap_census_out"))
    ap.add_argument("--crops", type=Path, help="write ours | pro crops of every pair of ours that touches")
    ap.add_argument("--hold-back", action="store_true", help="prototype the 0.25 mm hold-back (harness only)")
    ap.add_argument("--legibility", action="store_true", help="word_legibility at a 4 mm shrink (tesseract)")
    ap.add_argument("--json", type=Path, help="write the full result here")
    return ap.parse_args(argv)


def _slugs(s: str) -> list[str]:
    out = list(WORDS) if s == "all" else [x.strip() for x in s.split(",") if x.strip()]
    bad = [x for x in out if x not in WORDS]
    if bad:
        raise SystemExit(f"unknown pair(s) {bad}; known: {sorted(WORDS)}")
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.digitize:
        for slug in _slugs(args.digitize):
            digitize(slug, args.cache)
    if args.read:
        results = [read_pair(s, args.cache, args.crops, args.hold_back, args.legibility) for s in _slugs(args.read)]
        print(table(results))
        print()
        print(pair_table(results))
        print()
        print(attribution_table(results))
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
