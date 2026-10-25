#!/usr/bin/env python
"""lettering_board: the lettering scoreboard -- ours beside the pro's, by job
and by letter size, so a lettering PR quotes ONE board delta instead of
hand-picked numbers.

WHAT IT IS FOR. Every lettering PR so far carried its own numbers, picked
by whoever wrote it, on whichever jobs and lines they looked at. This runs
today's engine (main's defaults, or a flag set with `--set flag=value`) on
every pair that carries lettering, reads each pinned line of lettering in OUR
file and in the pro's -- one reader on both, each in its own frame -- and
reports per job (a pair: artwork + the pro's file + garment) and per size band
of the letters: under 4 mm, 4-6, 6-10, 10 and up. `--compare A.json B.json`
prints what moved. Nothing here changes the engine.

THE LINES. `testdata/lettering_board_lines.json` pins, per pair, every line of
lettering: its text, its box in OUR frame (the art traced at the pro's width),
the height it is DRAWN at (`art_h`, which sets its band, so a line stays in its
band whatever a flag does to the sewn size) and the words
`tools/word_legibility.py` pins for it. Text and numbers only: no artwork, no
pro file. A pair is on the board when it has lines there. The pairs come from
`tools.border_census.PAIRS` and the extras `small_text_floor_census` adds (the
same list every other census reads); a new pair joins the board by getting a
row in that list and its lines in the JSON (`--propose SLUG` prints the
tagger's clusters to name them from).

PER LINE, PER FILE (the same code on `ours.dst` and on the pro's file):
  locate     `small_text_floor_census.register` maps the box into the pro's
             frame; `read_element` picks the line's own thread (the block with
             the most thread in letter-like components) and its letter heights.
  columns    `column_harness.census` on the line's needle-down runs.
  stitches   needle penetrations in the line's letters.
  satin w    mean of `letter_band.crosses_xy` widths over those runs (mm).
  trims      `trim_classes` hops (read from the DST, never the PES: the PES
             reader reports a TRIM at every jump) with BOTH ends inside one
             letter of the line -- a cut inside a letter. A hop from one
             letter to the next is stage 7's order, on both sides, and a
             colour change is not a cut.
  cc         `word_legibility`: tesseract reads each pinned word of the line
             at its native size, `cc = (raw - base) / (1 - base)` (ROADMAP gate
             4: no quality claim on a raw agreement number). Needs tesseract.
  rail run   rail wobble p90 (mm) over the line's RUN windows only
             (`letter_band.rail_classes`, 2026-10-25): `rail_jitter`'s
             9-penetration windows that span no corner of the letters'
             outline and stay on it. A per-letter rail p90 is mostly windows
             that cross a notch, an end face or a cut (straight stems read
             0.000-0.04 on their run windows while the letters read
             0.10-0.26), which is construction, not wobble. The outline is
             OUR text-tagged regions in the line's box (`ours.json`), carried
             into the pro's frame by the pair's registration. The cell is
             the line p90s' mean weighted by run windows.

THE CELL. A job x band cell pools its lines, and only the lines BOTH files have
a value for, so ours and the pro's always cover the same lines (the cell says
`n` of `of`). A figure that could not be read is `n/a` with its reason, never
0: a pro file with no DST sibling has no trims, a word the locator could not
find in a file has no cc, a line a reader saw as a blob has no columns. The
height a reader finds is checked against the drawn height (0.5x to 2.6x) before
any of the line's numbers are kept.

WHAT IT CANNOT TELL YOU. The line reader is `small_text_floor_census`'s, and
it has that tool's limits: it can read more than the line (BECKER is an arch,
and in BOTH files its letters join into one piece 1.5x the drawn height) or
less (MFab's pro sews MFAB as a white keyline: its pieces read 0.5x, so the
pro's figures are n/a and the cell is ours alone). The 0.5x to 2.6x guard stops
the worst of it, not all of it: read `sewn mm` beside `drawn mm` in the line
table before quoting a cell. `cc` is coarse: most words read 1.00 or 0.00, and
it moves a whole step on one letter. Pairs the line reader cannot separate are
in the JSON's `left_off` with the reason (Golden Tee), and a pair whose pro
file is not on the machine (Bridge Bar) is listed under the board, not scored.

    python -m tools.lettering_board --cache DIR [--set flag=value ...] [--only SLUG ...]
    python -m tools.lettering_board --compare A.json B.json
    python -m tools.lettering_board --propose SLUG --cache DIR

`--cache DIR` holds each pair's `ours.dst` + `ours.json` (`border_census`
format; the board digitizes what is missing). A cache is for ONE flag set: it
records the set it was made with and the board refuses another.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import datetime
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))
REPO = DIGITIZER.parent

LINES_FILE = DIGITIZER / "testdata" / "lettering_board_lines.json"
OUT_DIR = REPO / "docs" / "scoreboards"
CACHE_RECORD = "board_cache.json"
ENGINE_STAMP = "engine.txt"

#: size bands by the letters' height in mm: (name, low, high)
BANDS = (("<4", 0.0, 4.0), ("4-6", 4.0, 6.0), ("6-10", 6.0, 10.0), ("10+", 10.0, math.inf))
BAND_NAMES = tuple(b[0] for b in BANDS)

#: the board's figures: key -> (heading, kind, format). `sum` pools by adding,
#: `mean` pools weighted by the slot's own weight (a mean of crosses, of letters).
METRICS = {
    "cc": ("word legibility cc", "mean", "{:+.2f}"),
    "columns": ("columns", "sum", "{:.0f}"),
    "trims": ("trims inside letters", "sum", "{:.0f}"),
    "stitches": ("stitches", "sum", "{:.0f}"),
    "satin_w": ("mean satin width mm", "mean", "{:.2f}"),
    "rail_run": ("rail wobble p90 run windows mm", "mean", "{:.3f}"),
}

HEIGHT_RATIO = (0.5, 2.6)     # a read letter height, in the drawn one, that is still "the line"
#: slack, mm, the line's box is grown by above/below and either side before the reader looks. The
#: floor census used 1.5 x the drawn height, which for an 18 mm word is 27 mm: room for the badge's
#: own outline to sit INSIDE the box (so it is not dropped as a frame touching the edge) and win
#: the "most thread in letter-like pieces" vote. The slack is for registration, not for search.
MARGIN_Y_MM = (2.5, 4.0)
MARGIN_X_MM = (2.0, 4.0)
LETTER_PAD_MM = 0.3           # a hop is "inside" a letter when both ends are within this of its box

#: the committed pro files, for a machine that has no Embroidery Files folder
REFERENCE_PRO = {
    "becker_hat_large": "becker_hat_polo_large_beckers_logo_hat",
    "becker_lc_large": "becker_hat_polo_large_beckers_logolc",
    "becker_hat_small": "becker_hat_small_beckers_logo_hat_2_a",
    "becker_chest_small": "becker_chest_small_beckers_logo_lc_2_a",
}


# --- bands, slots, pooling (pure) ----------------------------------------------

def band_of(h_mm):
    """The size band of a letter height in mm; None for no height."""
    if h_mm is None:
        return None
    for name, lo, hi in BANDS:
        if lo <= h_mm < hi:
            return name
    return None


def slot(v, w=None, why=None):
    """One figure of one side of one line. `v` None is MISSING and carries
    its reason; a real zero stays a zero. `w` is the weight of a mean."""
    if v is None:
        return {"v": None, "w": None, "why": why or "n/a"}
    return {"v": v, "w": w, "why": None}


def _slot(line, side, key):
    return line.get(side, {}).get(key) or slot(None, why="not read")


def pool(lines, key):
    """One cell's figure over `lines`: -> {ours, pro, n, of, why}. Only the
    lines both sides have a value for are pooled, so the two columns cover the
    same lines. With none, both are None and `why` is the commonest reason."""
    kind = METRICS[key][1]
    use, reasons = [], collections.Counter()
    for ln in lines:
        o, p = _slot(ln, "ours", key), _slot(ln, "pro", key)
        if o["v"] is not None and p["v"] is not None:
            use.append((o, p))
        else:
            reasons[o["why"] if o["v"] is None else p["why"]] += 1
    out = {"ours": None, "pro": None, "n": len(use), "of": len(lines), "why": None}
    if not use:
        out["why"] = reasons.most_common(1)[0][0] if reasons else "no lines"
        return out
    for side, idx in (("ours", 0), ("pro", 1)):
        if kind == "sum":
            v = sum(u[idx]["v"] for u in use)
        else:
            wt = sum((u[idx]["w"] or 0) for u in use)
            v = (sum(u[idx]["v"] * (u[idx]["w"] or 0) for u in use) / wt) if wt else None
        out[side] = None if v is None else (int(round(v)) if kind == "sum" else round(v, 3))
    if out["ours"] is None:
        out["why"] = "no weight"
    return out


def cells(lines):
    """-> {pair or "ALL": {band: {"lines": [text], <metric>: pool}}}."""
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for ln in lines:
        b = ln.get("band") or band_of(ln.get("art_h"))
        by[ln["slug"]][b].append(ln)
        by["ALL"][b].append(ln)
    out = {}
    for slug in sorted(by, key=lambda s: (s == "ALL", s)):
        out[slug] = {}
        for b in BAND_NAMES:
            ls = by[slug].get(b)
            if ls:
                out[slug][b] = {"lines": [l["text"] for l in ls], **{k: pool(ls, k) for k in METRICS}}
    return out


# --- the markdown ---------------------------------------------------------------

def fmt_pair(p, key):
    """`ours / pro` of a pooled figure (with `(n/of)` when it left lines out),
    or `n/a` -- never a 0 for a missing one."""
    if p["ours"] is None or p["pro"] is None:
        return "n/a"
    f = METRICS[key][2]
    left = f" ({p['n']}/{p['of']})" if p["n"] != p["of"] else ""
    return f"{f.format(p['ours'])} / {f.format(p['pro'])}{left}"


def _fmt_side(s, key):
    return "n/a" if s is None or s.get("v") is None else METRICS[key][2].format(s["v"])


def render_md(board):
    meta, lines, cs = board["meta"], board["lines"], board["cells"]
    sets = meta.get("sets") or {}
    md = [f"# Lettering board {meta.get('date', '')}", "",
          f"Engine: `{meta.get('git', '?')}`, flags: {json.dumps(sets, sort_keys=True) if sets else 'main defaults'}. "
          f"OCR: {meta.get('tesseract') or 'none (cc is n/a)'}. "
          "Each cell is `ours / pro`, pooled over the lines both files have a figure for "
          "(`n/of`). Bands are the DRAWN letter height, so a line stays in its band whatever a flag does to "
          "its sewn size. `n/a` is a figure that could not be read; the reason is under the board.", ""]
    head = ["pair", "band", "lines"] + [METRICS[k][0] for k in METRICS]
    md += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    na = []
    for slug, bands in cs.items():
        for b in BAND_NAMES:
            c = bands.get(b)
            if not c:
                continue
            row = [slug, b, ", ".join(c["lines"]) if slug != "ALL" else str(c["cc"]["of"])]
            for k in METRICS:
                row.append(fmt_pair(c[k], k))
                if c[k]["ours"] is None or c[k]["pro"] is None:
                    na.append((slug, b, METRICS[k][0], c[k]["why"]))
            md.append("| " + " | ".join(row) + " |")
    if na:
        md += ["", "## n/a, and why", ""]
        md += [f"- {s} {b}, {k}: {why}" for s, b, k, why in na]
    md += ["", "## Every line", "",
           "| pair | line | band | drawn mm | sewn mm ours / pro | " + " | ".join(METRICS[k][0] for k in METRICS) + " |",
           "|" + "---|" * (5 + len(METRICS))]
    for ln in lines:
        rd = ln.get("read", {})
        sewn = " / ".join("n/a" if rd.get(s, {}).get("h_mm") is None else f"{rd[s]['h_mm']:.2f}"
                          for s in ("ours", "pro"))
        row = [ln["slug"], ln["text"], ln.get("band") or "?", f"{ln['art_h']:.2f}", sewn]
        for k in METRICS:
            o, p = _slot(ln, "ours", k), _slot(ln, "pro", k)
            row.append(f"{_fmt_side(o, k)} / {_fmt_side(p, k)}")
        md.append("| " + " | ".join(row) + " |")
    why = collections.defaultdict(list)
    for ln in lines:
        for side in ("ours", "pro"):
            for k in METRICS:
                s = _slot(ln, side, k)
                if s["v"] is None:
                    why[(ln["slug"], ln["text"], side, s["why"])].append(METRICS[k][0])
    if why:
        md += ["", "### Line-level n/a", ""]
        md += [f"- {slug} / {text}, {side}: {w} ({', '.join(ks)})" for (slug, text, side, w), ks in why.items()]
    skipped = meta.get("skipped") or []
    if skipped:
        md += ["", "## Pairs not on this board", ""] + [f"- {s['slug']}: {s['why']}" for s in skipped]
    return "\n".join(md) + "\n"


# --- compare ---------------------------------------------------------------------

def _index(board):
    return {(ln["slug"], ln["text"]): ln for ln in board["lines"]}


def _usable(ln, key):
    return _slot(ln, "ours", key)["v"] is not None and _slot(ln, "pro", key)["v"] is not None


def compare_boards(a, b):
    """The delta of ours from board `a` to board `b`, on the lines BOTH boards
    could read (a line one run lost is listed, not counted as a change)."""
    ia, ib = _index(a), _index(b)
    ma, mb = a["meta"], b["meta"]

    def tag(m):
        return f"{m.get('date', '?')} {m.get('git', '?')} {json.dumps(m.get('sets') or 'main defaults')}"
    out = [f"# Lettering board delta: {tag(ma)} -> {tag(mb)}", "",
           "Ours, A -> B, on the lines both boards could read; the pro's figure beside it (it does "
           "not move). Per-pair rows only where a cell moved; the ALL rows always.", "",
           "| pair | band | figure | ours A -> B | delta | pro | n/of |", "|---|---|---|---|---|---|---|"]
    moved, notes = 0, []
    for key in METRICS:
        head, kind, f = METRICS[key]
        both = [k for k in ia if k in ib]
        ok = [k for k in both if _usable(ia[k], key) and _usable(ib[k], key)]
        for k in both:
            ua, ub = _usable(ia[k], key), _usable(ib[k], key)
            if ua and not ub:
                o, p = _slot(ib[k], "ours", key), _slot(ib[k], "pro", key)
                why = o["why"] if o["v"] is None else p["why"]
                notes.append(f"- lost: {k[0]} / {k[1]}, {head}: B reads n/a ({why})")
            elif ub and not ua:
                notes.append(f"- gained: {k[0]} / {k[1]}, {head}: A read n/a")
        ca, cb = cells([ia[k] for k in ok]), cells([ib[k] for k in ok])
        for slug in cb:
            for band in BAND_NAMES:
                x, y = ca.get(slug, {}).get(band), cb[slug].get(band)
                if not x or not y or x[key]["ours"] is None or y[key]["ours"] is None:
                    continue
                same = x[key]["ours"] == y[key]["ours"]
                if same and slug != "ALL":
                    continue
                moved += 0 if same else 1
                delta = y[key]["ours"] - x[key]["ours"]
                d = (f"{delta:+.3f}" if f.endswith(".3f}") else f"{delta:+.2f}") if kind == "mean" \
                    else f"{delta:+d}"
                out.append(f"| {slug} | {band} | {head} | {f.format(x[key]['ours'])} -> {f.format(y[key]['ours'])} "
                           f"| {d} | {f.format(x[key]['pro'])} | {y[key]['n']}/{y[key]['of']} |")
    notes += [f"- gone: {k[0]} / {k[1]} (in A, not in B)" for k in ia if k not in ib]
    notes += [f"- new: {k[0]} / {k[1]} (in B, not in A)" for k in ib if k not in ia]
    if not moved:
        out += ["", "No change in any cell."]
    if notes:
        out += ["", "## Lines that left or joined a cell", ""] + sorted(set(notes))
    return "\n".join(out) + "\n"


# --- pairs and pinned lines ---------------------------------------------------

def load_lines(path: Path = LINES_FILE) -> dict:
    """slug -> {"legibility_job", "lines": [{text, box, art_h, words}]}."""
    return json.loads(Path(path).read_text(encoding="utf-8"))["pairs"]


def load_left_off(path: Path = LINES_FILE) -> dict:
    """slug -> why a pair that carries lettering is NOT on the board."""
    return json.loads(Path(path).read_text(encoding="utf-8")).get("left_off", {})


def pair_rows():
    """Every pair the repo's tools know, in `border_census.PAIRS`' row shape:
    its list plus the extras the floor census adds."""
    from tools import border_census as bc
    from tools import small_text_floor_census as sf
    rows = list(bc.PAIRS)
    known = {r[0] for r in rows}
    return rows + [r for r in sf.EXTRA_PAIRS if r[0] not in known]


@dataclass
class Pair:
    slug: str
    garment: str
    pro: Path | None       # the file the pro is READ from: its DST when it has one
    pro_pes: Path | None
    art: Path | None


def _sibling(path: Path, ext: str):
    for q in path.parent.iterdir():
        if q.stem == path.stem and q.suffix.lower() == ext:
            return q
    return None


def resolve_pair(slug: str, find=None) -> Pair:
    """`find`: the finder to ask for the files (`border_census.find_pair`
    unless `_studio` has swapped that for ours -- it passes the real one)."""
    from tools import border_census as bc
    row = next((r for r in pair_rows() if r[0] == slug), None)
    if row is None:
        raise SystemExit(f"{slug}: not a known pair")
    bc.ART_FALLBACK.setdefault("goldentee", bc._T / "photo" / "logo_golden_tee.jpg")
    pro, art = (find or bc.find_pair)(*row[:3])
    if art is None:
        from tools import flip_sheet_renders as fs     # MFab's art: the committed corpus crops
        art = fs.ART_FALLBACK.get(slug)
        art = art if art is not None and art.exists() else None
    ref = DIGITIZER / "testdata" / "reference"
    if pro is None and slug in REFERENCE_PRO and (ref / f"{REFERENCE_PRO[slug]}.dst").exists():
        pro = ref / f"{REFERENCE_PRO[slug]}.dst"
    if pro is None:
        return Pair(slug, row[3], None, None, art)
    dst = pro if pro.suffix.lower() == ".dst" else _sibling(pro, ".dst")
    pes = pro if pro.suffix.lower() == ".pes" else _sibling(pro, ".pes")
    return Pair(slug, row[3], dst or pro, pes, art)


# --- digitizing (the cache) -----------------------------------------------------

def git_sha() -> str:
    """The engine a board was made with: the last commit that touched
    `digitizer_core/` (a tool-only commit does not change the numbers, so it
    does not change this), `+dirty` when that folder has uncommitted edits."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=DIGITIZER, capture_output=True, text=True).stdout.strip()
    try:
        sha = git("log", "-1", "--format=%h", "--", "digitizer_core") or git("rev-parse", "--short", "HEAD") or "?"
        return sha + ("+dirty" if git("status", "--porcelain", "--", "digitizer_core") else "")
    except OSError:
        return "?"


@contextlib.contextmanager
def _studio(sets: dict):
    """`border_census.digitize_one` with the board's pair list, its file
    resolver, and the flag set laid over the Studio request."""
    from tools import border_census as bc
    from tools import pro_pair as pp
    saved_rows, saved_find, saved_dig = list(bc.PAIRS), bc.find_pair, pp.digitize
    known = {r[0] for r in bc.PAIRS}
    bc.PAIRS.extend(r for r in pair_rows() if r[0] not in known)

    def find_pair(slug, _pro_rel, _art_rel):
        p = resolve_pair(slug, find=saved_find)
        return p.pro, p.art
    bc.find_pair = find_pair
    if sets:
        pp.digitize = lambda art, w, g="hat_front", e=None: saved_dig(art, w, g, {**sets, **(e or {})})
    try:
        yield bc
    finally:
        bc.PAIRS[:] = saved_rows
        bc.find_pair, pp.digitize = saved_find, saved_dig


def prepare_cache(cache: Path, sets: dict, trust: bool = False):
    cache.mkdir(parents=True, exist_ok=True)
    rec = cache / CACHE_RECORD
    if rec.exists():
        have = json.loads(rec.read_text(encoding="utf-8")).get("sets", {})
        if have != sets:
            raise SystemExit(f"{cache} was made with flags {have}, not {sets}: use another --cache")
    elif any(cache.iterdir()) and not trust:
        raise SystemExit(f"{cache} has files but no {CACHE_RECORD}: it does not say which flags made it. "
                         f"--trust-cache records it as made with {sets or 'main defaults'}.")
    if not rec.exists():
        rec.write_text(json.dumps({"sets": sets, "git": git_sha()}, indent=1), encoding="utf-8")


def digitize_missing(slugs, cache: Path, sets: dict, log=print) -> dict:
    """Digitize every slug the cache lacks. -> {slug: why} for the ones that
    could not be (a missing file is a listed gap, not a dead run)."""
    failed = {}
    todo = [s for s in slugs if not (cache / s / "ours.json").exists()]
    if not todo:
        return failed
    with _studio(sets) as bc:
        for slug in todo:
            try:
                info = bc.digitize_one(slug, cache)
            except (SystemExit, Exception) as e:  # noqa: BLE001
                failed[slug] = str(e) or type(e).__name__
                log(f"{slug}: not digitized: {failed[slug]}")
                continue
            (cache / slug / ENGINE_STAMP).write_text(git_sha(), encoding="utf-8")
            log(f"digitized {slug} at {info['width_mm']} mm in {info['secs']} s")
    return failed


def cache_engine(cache: Path, slugs) -> str:
    """The engine the cached files were digitized with: each pair's stamp
    (written when the board digitized it), else the cache record's. A board
    labelled with the CURRENT tree's engine would be wrong the day a
    commit lands between digitizing and reading."""
    rec = cache / CACHE_RECORD
    base = json.loads(rec.read_text(encoding="utf-8")).get("git", "?") if rec.exists() else "?"
    seen = set()
    for s in slugs:
        stamp = cache / s / ENGINE_STAMP
        seen.add(stamp.read_text(encoding="utf-8").strip() if stamp.exists() else base)
    return ", ".join(sorted(seen)) or base


# --- reading one file ------------------------------------------------------------

def inbox(p, bx, pad=LETTER_PAD_MM):
    return bx[0] - pad <= p[0] <= bx[2] + pad and bx[1] - pad <= p[1] <= bx[3] + pad


def trims_inside(rows, boxes, pad=LETTER_PAD_MM) -> int:
    """TRIM hops with both ends in one letter box: a cut inside a letter. A
    colour change is not a cut, and a hop between letters is stage 7's."""
    n = 0
    for r in rows:
        if r.get("cls") == "colour":
            continue
        if any(inbox(r["a"], bx, pad) and inbox(r["b"], bx, pad) for bx in boxes):
            n += 1
    return n


def point_runs(segs):
    """The line's needle-down segments -> runs of consecutive points."""
    by = collections.defaultdict(list)
    for s in segs:
        by[s[4]].append(s)
    runs = []
    for _ri, ss in sorted(by.items()):
        ss.sort(key=lambda s: s[5])
        cur, last = [], None
        for s in ss:
            if last is not None and s[5] == last + 1:
                cur.append((s[2], s[3]))
            else:
                if len(cur) > 1:
                    runs.append(cur)
                cur = [(s[0], s[1]), (s[2], s[3])]
            last = s[5]
        if len(cur) > 1:
            runs.append(cur)
    return runs


class FileReader:
    """One machine file, read lines of lettering from in its own frame."""

    def __init__(self, path: Path, trim_why: str | None = None):
        from tools.study_pro import load_runs
        self.path = Path(path)
        self.runs = load_runs(self.path)[0]
        self.trim_why = trim_why
        self._trims = None

    def trim_rows(self):
        if self.trim_why:
            return None
        if self._trims is None:
            from tools import trim_classes
            self._trims = trim_classes.classify(self.path)
        return self._trims

    def line(self, box, art_h, cy, outline=None) -> dict:
        """-> {"read": reader's summary, <metric>: slot}. Every figure is a
        missing slot with its reason when the line was not found. `outline`:
        the line's letters in this file's frame, for `rail_run` (None: n/a)."""
        from tools import small_text_floor_census as sf
        keep: dict = {}
        e = sf.read_element(self.runs, box, art_h, cy, keep=keep)
        why = None
        if e.get("verdict") == "DROPPED":
            why = "no letter-like thread in the line's box"
        elif e["h_mm"] / art_h > HEIGHT_RATIO[1]:
            why = f"read {e['h_mm']} mm against {art_h:.1f} drawn: a field or a blob, not the line"
        elif e["h_mm"] / art_h < HEIGHT_RATIO[0]:
            why = f"read {e['h_mm']} mm against {art_h:.1f} drawn: a fragment of the line, not the line"
        out = {"read": {k: e.get(k) for k in ("verdict", "block", "h_mm", "w_mm", "n", "gap_mm", "fused",
                                               "stroke_mm", "satin", "bean")}}
        if why:
            out["read"]["why"] = why
            out.update({k: slot(None, why=why) for k in ("columns", "stitches", "satin_w", "trims", "rail_run")})
            return out
        from tools import column_harness, letter_band
        runs = point_runs(keep["segs"])
        out["columns"] = slot(int(column_harness.census(runs, [], 0)["columns"]))
        out["stitches"] = slot(sum(len(r) for r in runs))
        ws = [w for r in runs for _x, _y, w, _l in letter_band.crosses_xy(r)]
        out["satin_w"] = slot(round(sum(ws) / len(ws), 3), w=len(ws)) if ws else slot(None, why="no satin crosses")
        rows = self.trim_rows()
        out["trims"] = (slot(None, why=self.trim_why) if rows is None
                        else slot(trims_inside(rows, keep["comps"])))
        out["rail_run"] = rail_run(runs, outline)
        return out


def rail_run(runs, outline) -> dict:
    """The `rail_run` slot: run-window rail wobble p90, weighted by its windows."""
    if outline is None or outline.is_empty:
        return slot(None, why="no text-tagged region of ours in the line's box")
    from tools import letter_band
    c = letter_band.rail_classes(runs, outline)
    if not c["run"]:
        return slot(None, why=f"no run windows ({c['n']} windows, every one on a corner or off the outline)")
    return slot(round(c["run_p90"], 3), w=c["run"])


def line_outline(info: dict, box, pad: float = 0.5):
    """OUR text-tagged regions whose representative point lies in the line's
    `box` (grown by `pad`), as one geometry in our frame; None for none."""
    from shapely import wkt
    from shapely.ops import unary_union
    keys = ("text_candidate", "text_cluster_id", "lettering_group", "word_id")
    got = []
    for r in info.get("regions", []):
        if not any((r.get("meta") or {}).get(k) for k in keys):
            continue
        g = wkt.loads(r["wkt"])
        q = g.representative_point()
        if box[0] - pad <= q.x <= box[2] + pad and box[1] - pad <= q.y <= box[3] + pad:
            got.append(g)
    return unary_union(got) if got else None


# --- word legibility -------------------------------------------------------------

def read_words(pair: Pair, spec: dict, info: dict, ours_dst: Path, words_wanted, ocr: bool):
    """word -> {"ours": row or None, "pro": row or None, "why": reason} at the
    words' native size, through `word_legibility.read_job`."""
    from tools import word_legibility as wl
    from tools.glyph_legibility import design_from_pes, load_source
    job = spec["legibility_job"]
    pinned = [w for w in wl.pinned_words(job) if w["text"] in words_wanted]
    pro_file = pair.pro_pes or pair.pro
    if not pinned or pair.art is None or pro_file is None:
        return {}
    ours = design_from_pes(ours_dst)
    ours["colors"] = [{"r": int(c[0]), "g": int(c[1]), "b": int(c[2])} for c in info["blocks"]] or ours["colors"]
    rgb, alpha = load_source(pair.art)
    res = wl.read_job(job, ours, wl.load_pro_design(pro_file), pinned, rgb, alpha, use_ocr=ocr,
                      heights=(), ours_width_mm=info["width_mm"])
    out = {}
    for w in pinned:
        t = w["text"]
        row = {"ours": None, "pro": None, "why": {}}
        for f in ("ours", "pro"):
            mine = [r for r in res["rows"] if r["file"] == f and r["text"] == t]
            nat = next((r for r in mine if r.get("size") == "native"), None)
            if nat is None:
                row["why"][f] = (mine[0].get("note") if mine else "not read") or "not located"
            elif nat.get("read") is None:
                row["why"][f] = "tesseract not installed" if not ocr or res["ocr"] != "ok" else "not read"
            elif nat.get("cc") is None:
                row["why"][f] = "cc undefined (one letter, or one letter repeated)"
            else:
                row[f] = nat
        out[t] = row
    return out


def line_cc(words, got):
    """A line's cc, ours and the pro's, over the words scored in BOTH files,
    each weighted by its letters. -> (ours slot, pro slot)."""
    from tools import word_legibility as wl
    if not words:
        w = slot(None, why="no words pinned for this line")
        return w, w
    use, reasons = [], []
    for t in words:
        g = got.get(t)
        if g and g["ours"] and g["pro"]:
            use.append((t, g))
        else:
            r = (g or {"why": {"ours": "word not pinned for this art"}})["why"]
            reasons.append(f"{t}: " + "; ".join(f"{f} {v}" for f, v in r.items()))
    if not use:
        w = slot(None, why="; ".join(reasons) or "no word read")
        return w, w
    wt = sum(len(wl.norm(t)) for t, _ in use)
    return tuple(slot(round(sum(g[f]["cc"] * len(wl.norm(t)) for t, g in use) / wt, 3), w=wt)
                 for f in ("ours", "pro"))


# --- one pair, the whole board -------------------------------------------------

def read_pair(slug: str, spec: dict, cache: Path, ocr: bool = True, log=print) -> list[dict]:
    from shapely.affinity import affine_transform
    from tools import small_text_floor_census as sf
    pair = resolve_pair(slug)
    if pair.pro is None:
        raise SystemExit(f"{slug}: the pro's file is not on this machine")
    d = cache / slug
    info = json.loads((d / "ours.json").read_text(encoding="utf-8"))
    ours_dst = d / "ours.dst"
    reg = sf.register(pair.pro, ours_dst)
    ours = FileReader(ours_dst)
    pro = FileReader(pair.pro, trim_why=None if pair.pro.suffix.lower() == ".dst"
                     else "no DST of the pro's (the PES reader reports a TRIM at every jump)")
    wanted = {w for ln in spec["lines"] for w in ln.get("words", [])}
    got = {}
    if spec.get("legibility_job") and wanted:
        try:
            got = read_words(pair, spec, info, ours_dst, wanted, ocr)
        except Exception as e:  # noqa: BLE001 -- a broken legibility read is a n/a, not a dead board
            log(f"  {slug}: legibility read failed: {type(e).__name__}: {e}")
            got = {t: {"ours": None, "pro": None, "why": {"ours": f"legibility read failed: {type(e).__name__}"}}
                   for t in wanted}
    out = []
    for ln in spec["lines"]:
        box, art_h = ln["box"], float(ln["art_h"])
        m_y = min(max(MARGIN_Y_MM[0], 1.5 * art_h), MARGIN_Y_MM[1])
        m_x = min(max(MARGIN_X_MM[0], 2.0 + 0.5 * art_h), MARGIN_X_MM[1])
        cy = 0.5 * (box[1] + box[3])
        ob = (box[0] - m_x, box[1] - m_y, box[2] + m_x, box[3] + m_y)
        pb = sf._map_box(box, reg, m_x * reg.scale, m_y * reg.scale)
        letters = line_outline(info, box)
        o = ours.line(ob, art_h, cy, letters)
        p = pro.line(pb, art_h * reg.scale, reg.scale * cy + reg.dy,
                     None if letters is None else affine_transform(letters, reg.matrix()))
        cc_o, cc_p = line_cc(ln.get("words", []), got) if spec.get("legibility_job") else (
            slot(None, why="no words pinned for this art"),) * 2
        out.append({"slug": slug, "text": ln["text"], "art_h": art_h, "band": band_of(art_h),
                    "words": ln.get("words", []),
                    "read": {"ours": o.pop("read"), "pro": p.pop("read")},
                    "ours": {**o, "cc": cc_o}, "pro": {**p, "cc": cc_p}})
        log(f"  {slug} / {ln['text']}: ours {o['columns']['v']} cols, pro {p['columns']['v']} cols")
    return out


def tesseract_version():
    from tools import word_legibility as wl
    if not wl.tesseract_available():
        return None
    try:
        return subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    except (OSError, IndexError):
        return "tesseract"


def build(slugs, cache: Path, sets: dict, ocr: bool = True, date=None, log=print, failed=None) -> dict:
    """`failed`: {slug: why} from `digitize_missing`."""
    reg = load_lines()
    lines, skipped, files = [], [], {}
    for slug in slugs:
        if failed and slug in failed:
            skipped.append({"slug": slug, "why": f"not digitized: {failed[slug]}"})
            continue
        try:
            lines += read_pair(slug, reg[slug], cache, ocr, log)
            p = resolve_pair(slug)
            files[slug] = {"pro": p.pro.name, "pro_pes": p.pro_pes.name if p.pro_pes else None,
                           "art": p.art.name if p.art else None}
        except (SystemExit, Exception) as e:  # noqa: BLE001 -- one bad pair is a listed gap, not a dead board
            skipped.append({"slug": slug, "why": str(e) or type(e).__name__})
            log(f"  {slug}: skipped: {e}")
    left_off = load_left_off()
    for slug in [r[0] for r in pair_rows()]:
        if slug not in reg:
            gone = " (and the pro's file is not on this machine)" if resolve_pair(slug).pro is None else ""
            skipped.append({"slug": slug, "why": left_off.get(slug) or "no lettering lines pinned" + gone})
    meta = {"date": date or datetime.date.today().isoformat(), "git": cache_engine(cache, slugs), "sets": sets,
            "tesseract": tesseract_version() if ocr else None, "pairs": list(slugs), "files": files,
            "skipped": skipped}
    return {"meta": meta, "lines": lines, "cells": cells(lines)}


# --- the tagger's clusters, to name new lines from -------------------------------

def candidate_rows(info: dict) -> list[dict]:
    """The tagger's text clusters of a cached digitization, each split into
    ROWS (regions whose y-ranges overlap), as `{cluster, box, n, art_h}`:
    what to name when pinning a pair's lines. `art_h` is the floor census's
    drawn height (`art_letters`) of the row's box."""
    from shapely import wkt
    from tools import small_text_floor_census as sf
    by = collections.defaultdict(list)
    for r in info["regions"]:
        cid = r["meta"].get("text_cluster_id")
        if cid:
            by[cid].append(wkt.loads(r["wkt"]).bounds)
    rows = []
    for cid, bs in by.items():
        cur = []
        for b in sorted(bs, key=lambda b: (b[1] + b[3]) / 2):
            if cur and (min(b[3], max(c[3] for c in cur)) - max(b[1], min(c[1] for c in cur))) \
                    > 0.5 * min(b[3] - b[1], max(c[3] for c in cur) - min(c[1] for c in cur)):
                cur.append(b)
            else:
                if cur:
                    rows.append((cid, cur))
                cur = [b]
        if cur:
            rows.append((cid, cur))
    out = []
    for cid, bs in rows:
        box = [round(v, 1) for v in (min(b[0] for b in bs), min(b[1] for b in bs),
                                     max(b[2] for b in bs), max(b[3] for b in bs))]
        _u, h, _w = sf.art_letters(info, box)
        out.append({"cluster": cid, "box": box, "n": len(bs), "art_h": round(h, 2)})
    return sorted(out, key=lambda r: (r["box"][1], r["box"][0]))


def propose(slug: str, cache: Path) -> None:
    info = json.loads((cache / slug / "ours.json").read_text(encoding="utf-8"))
    print(f"{slug} at {info['width_mm']} mm ({info['garment']}): name each row, then add "
          f'{{"text", "box", "art_h", "words"}} to {LINES_FILE.name}')
    for r in candidate_rows(info):
        print(f"  {r['cluster']}: {r['n']:2d} regions  box {r['box']}  drawn {r['art_h']} mm")


# --- command line ----------------------------------------------------------------

def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.lettering_board", description=__doc__.split("\n\n")[0])
    ap.add_argument("--cache", type=Path, help="per-pair ours.dst + ours.json (made if missing)")
    ap.add_argument("--set", action="append", default=[], metavar="FLAG=VALUE",
                    help="a config field over the Studio request (JSON value); repeatable")
    ap.add_argument("--only", action="append", default=[], metavar="SLUG")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--date", default=None)
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--trust-cache", action="store_true")
    ap.add_argument("--compare", nargs=2, type=Path, metavar=("A.json", "B.json"))
    ap.add_argument("--propose", metavar="SLUG")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console(sys.stdout)
    a = parse_args(argv)
    if a.compare:
        la, lb_ = (json.loads(p.read_text(encoding="utf-8")) for p in a.compare)
        print(compare_boards(la, lb_))
        return 0
    if not a.cache:
        raise SystemExit("--cache DIR is required")
    from tools import pro_pair
    sets = pro_pair.parse_sets(a.set)
    if a.propose:
        propose(a.propose, a.cache)
        return 0
    reg = load_lines()
    unknown = [s for s in a.only if s not in reg]
    if unknown:
        raise SystemExit(f"--only {unknown}: no lines pinned for that pair; pinned: {', '.join(reg)}")
    slugs = [s for s in reg if not a.only or s in a.only]
    prepare_cache(a.cache, sets, a.trust_cache)
    failed = digitize_missing(slugs, a.cache, sets)
    board = build(slugs, a.cache, sets, ocr=not a.no_ocr, date=a.date, failed=failed)
    day = board["meta"]["date"]
    tag = "" if not sets else "-" + "-".join(f"{k}" for k in sorted(sets))
    a.out_dir.mkdir(parents=True, exist_ok=True)
    stem = a.out_dir / f"lettering-board-{day}{tag}"
    stem.with_suffix(".json").write_text(json.dumps(board, indent=1), encoding="utf-8")
    stem.with_suffix(".md").write_text(render_md(board), encoding="utf-8")
    print(render_md(board))
    print("wrote", stem.with_suffix(".md"), "and", stem.with_suffix(".json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
