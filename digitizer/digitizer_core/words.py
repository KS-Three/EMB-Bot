"""L1 of the lettering lane: ONE tagger, one word model.

`docs/lettering-architecture-rd-2026-10-07.md` §5, failure E: lettering was
found twice. `textcluster.detect_text_clusters` (two doors, a stroke-CV and
height screen, the one-ink link) writes `text_candidate` / `text_cluster_id`;
`textcluster._lettering_groups` (no ink link, no CV screen) groups for the
house angle and writes `lettering_group`. They disagree on real logos, and
every lettering flag read one or the other or both -- the split flag the
first, the house angle the second, the Column lane both.

`tag_words` is the one reading, and under `cfg.lettering_words` (default
OFF) the lettering readers downstream of it take their groups from it:
`columns.is_lettering`, the satin split's ceiling, the cap-skip cover, the
bean-letter word, the shared stitch width, the house angle and the
letterform priors. ONE stitch-affecting reader keeps the text cluster on
purpose: `regularize_text_clusters`, which runs before this and redraws
rescued members (and widens them under `lettering_min_column_mm`), because
its evidence is the rescued population only. OFF, `tag_words` is never
called and no `word_*` key is written; `is_text` / `word_key` then answer
exactly what each reader asked before.

Not a third set of rules. It is the two taggers' common geometry with the
gates that each one got wrong on the labelled logos replaced:

  * ADMISSION: every region whose box could be a glyph (one door, so a
    rescued glyph and an ordinary one are judged alike -- the text cluster's
    rescued door threw the Fremont PLAY letters away at the 0.32 CV it was
    calibrated with on blobs), screened by height and stroke CV.
  * LINKS: one size (`textcluster.LETTER_HEIGHT_RATIO`), one weight, one
    ink (`textcluster._same_ink`), near each other -- `textcluster._linked`
    itself, with the chart.
  * LINES: a component whose members sit in two rows (gaulke's two lines,
    one 35-member cluster in BOTH old taggers) is split at the widest gap
    across its line of text (`_split_lines`).
  * NOT A PATTERN: a candidate congruent with many others it links with
    -- a rope's twists -- is a pattern element, not a glyph, and leaves
    before words form (`_pattern_ids`). Letters repeat only as often as a
    word spells them.

What a word carries (`Word`, and the `word_*` meta keys): its members in
reading order, the line of text and the stems' slant (the house angle's own
readings, `textcluster._line_of_text_deg` / `_stem_slant_deg`), the cap
height (median member extent across the line), the stroke width (median of
the members' full skeleton widths) and its spread, and the baseline. The
OCR string is joined later, from the per-member read, by `word_ocr_text`.

Measured against hand labels on eight real logos by
`tools/word_tagger_eval.py` (`testdata/lettering_truth.json`), chance-
corrected per ROADMAP gate 4: Cohen's kappa for "is this region a letter",
the adjusted Rand index for "which line is it on".
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

from . import threads
from .regions import Region
from .textcluster import (ASPECT_RATIO_MIN, LETTER_HEIGHT_RATIO, MIN_CLUSTER_MEMBERS,
                          _Candidate, _cluster, _drop_nested, _house_chains,
                          _line_of_text_deg, _skeleton_stroke_stats, _stem_slant_deg)

# Widest box a glyph is taken at. The text cluster's 1.4 was set on a
# rescued-blob fixture whose non-letter fragments read 1.8-2.1; whole letters
# are wider than that population's: drone's M is 1.41, its A 1.44, a bridge
# blob holding two arc letters 1.59. A capital M or W in an extended face
# runs to ~1.6, and two touching letters segmented as one region to ~2.
# The non-letters this lets in still have to find two more of their own
# size, weight and ink nearby, and not be a repeat.
WORD_ASPECT_MAX = 2.0

# Under this a region is not taken as a glyph at all. Below 1 mm a cap is
# under a needle's reach (the size policy's business, L3, not the tagger's),
# and what is left there on the labelled logos is anti-alias crumbs and
# counter slivers: every labelled letter is 1.64 mm or taller. Over the
# ceiling, a background-sized region is not skeletonised on the chance it is
# one -- `textcluster.LETTER_MAX_HEIGHT_MM`'s cost reasoning.
WORD_MIN_HEIGHT_MM = 1.0
WORD_MAX_HEIGHT_MM = 60.0

# Stroke-width CV screen (std / mean of the skeleton half-width). The letter
# door's 0.55 refuses Fremont's PLAY P and A at 0.56 / 0.57 (2.4 mm caps,
# where a junction is a large share of the skeleton), leaving a word whose
# letters split across two treatments; 0.60 admits every labelled letter.
# FITTED on the labelled logos and thin: 0.03 over the highest letter.
# `tools/word_tagger_eval.py`'s sweep, pooled kappa: 0.55 -> 0.899 (P, A
# lost), 0.60 -> best, 0.65 -> six more scenery and icon crumbs tagged,
# 0.75 -> 0.737. The screen's job is the non-letters' irregular quarter
# (their 75th percentile is 0.52, 95th 0.72); linking does the rest.
WORD_STROKE_CV_MAX = 0.60

# Two rows of one component are two lines when the widest gap between
# members' positions across the line exceeds this share of the median
# member height. One straight line's members spread across it by their
# ascenders, descenders and punctuation -- a fraction of a cap; an arched
# line spreads continuously, with no single gap. Two lines sit a cap height
# plus leading apart: gaulke's rows are 6.2 mm apart at 4.5 mm caps, a gap
# of 1.4 caps.
LINE_GAP_FRAC = 0.75

# Two glyphs are CONGRUENT when their shapes, normalised for position,
# size, rotation and mirror, overlap by this intersection-over-union. A
# rope's twists, a window's panes and a border's beads are one shape laid
# down again and again; letters repeat only as often as a word spells them.
# Measured on the labelled logos (`tools/word_tagger_eval.py`): Fremont's
# rope twists have a median 23-25 congruent twins each at 0.8, and the most
# any labelled letter has is 3 (the four I's of PLOWING DIVISION).
CONGRUENT_IOU = 0.8
# A candidate with at least this many congruent twins NEAR it is a pattern
# element and leaves before words are formed. 5 sits above every labelled
# letter (3) and far below the rope's median.
PATTERN_MIN_TWINS = 5
# "Near" is within this many of the candidate's own heights, centre to
# centre. A lockup repeats a LETTER across its words and lines (MILLION
# DOLLAR BILLS: six L's; congruence also pairs b/d/p/q, n/u, M/W, 6/9 and
# plain bars), and counted over the whole linked component those would be
# dropped as a pattern -- review finding 2026-10-08. A rope repeats its
# twist at well under a height's pitch: within 5 heights Fremont's twists
# have a median 10-14 twins (2.5 heights: 4-8, too few), and no labelled
# letter more than 3. The labelled score is the same at 4, 5, 6 and 8
# heights (`tools/word_tagger_eval.py`); 5 is the middle of that plateau.
PATTERN_REACH_HEIGHTS = 5.0


@dataclass
class Word:
    """One line of lettering: members in reading order and what the line
    knows about itself. Lengths in mm, angles in degrees."""
    word_id: str
    members: list[Region]
    line_deg: float | None
    slant_deg: float | None
    cap_mm: float
    stroke_mm: float | None
    stroke_spread: float | None
    baseline: tuple[tuple[float, float], tuple[float, float]] | None = None


def _word_id(shape_ids: list[str]) -> str:
    """The `textcluster._text_cluster_id` digest with its own prefix, so a
    word id can never be mistaken for a cluster id."""
    key = ":".join(sorted(shape_ids)).encode()
    return "WD" + hashlib.blake2s(key, digest_size=4).hexdigest()


def _candidates(regions: list[Region]) -> list[_Candidate]:
    raw: list[_Candidate] = []
    for r in regions:
        x0, y0, x1, y1 = r.polygon.bounds
        w, h = x1 - x0, y1 - y0
        if h <= 0 or w <= 0:
            continue
        if not (ASPECT_RATIO_MIN <= w / h <= WORD_ASPECT_MAX):
            continue
        if not (WORD_MIN_HEIGHT_MM <= h <= WORD_MAX_HEIGHT_MM):
            continue
        stats = _skeleton_stroke_stats(r)
        if stats is None or stats.cv > WORD_STROKE_CV_MAX:
            continue
        raw.append(_Candidate(region=r, height_mm=h, width_mm=w,
                              stroke_mean_mm=stats.mean_mm, stroke_cv=stats.cv,
                              cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0))
    return _drop_nested(raw)


def _axis(cands: list[_Candidate]) -> tuple[float, float]:
    """Unit vector of the members' principal axis (the line of text), or
    (1, 0) where it is undefined -- fewer than two, or all coincident."""
    if len(cands) < 2:
        return 1.0, 0.0
    c = np.array([[k.cx, k.cy] for k in cands], float)
    c -= c.mean(axis=0)
    _u, sv, vt = np.linalg.svd(c, full_matrices=False)
    if sv[0] <= 0.0:
        return 1.0, 0.0
    return float(vt[0][0]), float(vt[0][1])


def _split_lines(cands: list[_Candidate]) -> list[list[_Candidate]]:
    """A linked component cut into rows: across its own principal axis, at
    the widest gap between consecutive members when that gap exceeds
    `LINE_GAP_FRAC` of the median height, recursively. Order-free: the
    projection sorts, ties broken by shape id."""
    if len(cands) < 2 * MIN_CLUSTER_MEMBERS:
        return [cands]
    ux, uy = _axis(cands)
    nx, ny = -uy, ux
    proj = sorted(((k.cx * nx + k.cy * ny, k.region.shape_id, k) for k in cands),
                  key=lambda t: (t[0], t[1]))
    gaps = [(proj[i + 1][0] - proj[i][0], i) for i in range(len(proj) - 1)]
    gap, i = max(gaps, key=lambda g: (g[0], -g[1]))
    h = float(np.median([k.height_mm for k in cands]))
    if gap <= LINE_GAP_FRAC * h:
        return [cands]
    lo = [t[2] for t in proj[:i + 1]]
    hi = [t[2] for t in proj[i + 1:]]
    return _split_lines(lo) + _split_lines(hi)


def _normalised(region: Region):
    """The region's polygon moved to its centroid, scaled to unit area and
    turned so its principal axis lies along x -- the frame `_congruent`
    compares in. None for a degenerate shape."""
    from shapely import affinity
    poly = region.polygon
    if poly.is_empty or poly.area <= 0:
        return None
    c = poly.centroid
    poly = affinity.translate(poly, -c.x, -c.y)
    s = math.sqrt(poly.area)
    poly = affinity.scale(poly, 1.0 / s, 1.0 / s, origin=(0, 0))
    geoms = getattr(poly, "geoms", [poly])
    xy = np.vstack([np.asarray(g.exterior.coords, float) for g in geoms])
    if len(xy) < 3:
        return None
    _w, v = np.linalg.eigh(np.cov(xy.T))
    return affinity.rotate(poly, -math.degrees(math.atan2(v[1, 1], v[0, 1])), origin=(0, 0))


def _congruent(a, b) -> bool:
    """IoU of two `_normalised` shapes at or over `CONGRUENT_IOU`, under the
    four sign flips the principal axis cannot tell apart (a turn of 180
    degrees and the two mirrors)."""
    from shapely import affinity
    for sx, sy in ((1, 1), (-1, -1), (-1, 1), (1, -1)):
        bb = b if sx == sy == 1 else affinity.scale(b, sx, sy, origin=(0, 0))
        inter = a.intersection(bb).area
        if inter <= 0:
            continue
        union = a.area + bb.area - inter
        if union > 0 and inter / union >= CONGRUENT_IOU:
            return True
    return False


def _pattern_ids(cands: list[_Candidate]) -> set[str]:
    """Shape ids of the candidates with `PATTERN_MIN_TWINS` or more
    congruent twins in `cands` within `PATTERN_REACH_HEIGHTS` of their own
    height. Pairs whose box aspect ratios differ by more than a quarter are
    not compared (they cannot reach the IoU), which is what keeps a
    120-twist rope to seconds."""
    norm = [_normalised(c.region) for c in cands]
    asp = [max(c.width_mm, c.height_mm) / max(min(c.width_mm, c.height_mm), 1e-9)
           for c in cands]
    twins = [0] * len(cands)
    for i in range(len(cands)):
        if norm[i] is None:
            continue
        for j in range(i + 1, len(cands)):
            if norm[j] is None:
                continue
            lo, hi = sorted((asp[i], asp[j]))
            if hi > 1.25 * lo:
                continue
            d = math.hypot(cands[i].cx - cands[j].cx, cands[i].cy - cands[j].cy)
            near_i = d <= PATTERN_REACH_HEIGHTS * cands[i].height_mm
            near_j = d <= PATTERN_REACH_HEIGHTS * cands[j].height_mm
            if not (near_i or near_j) or not _congruent(norm[i], norm[j]):
                continue
            twins[i] += near_i
            twins[j] += near_j
    return {c.region.shape_id for c, n in zip(cands, twins) if n >= PATTERN_MIN_TWINS}


def _describe(members: list[Region], cands: list[_Candidate]) -> Word:
    line = _line_of_text_deg(members)
    ux, uy = ((math.cos(math.radians(line)), math.sin(math.radians(line)))
              if line is not None else (1.0, 0.0))
    # A line angle is an axis (mod 180): 179.9 and -0.1 are the same line.
    # Read a line nearer horizontal left to right and one nearer vertical
    # top to bottom, so the order is reading order and, for upright text,
    # +normal points down the y-down page -- the baseline's side. The two
    # rules meet at 45 deg, not at 90, so a near-vertical line (89 vs 91)
    # keeps one direction. A line steeper than 45 deg reads top to bottom
    # whichever way its letters face; nothing reads the order for stitches.
    if abs(ux) >= abs(uy):
        if ux < 0:
            ux, uy = -ux, -uy
    elif uy < 0:
        ux, uy = -ux, -uy
    nx, ny = -uy, ux
    # reading order along the line; a tie (stacked glyphs) by shape id
    order = sorted(zip(members, cands),
                   key=lambda t: (t[1].cx * ux + t[1].cy * uy, t[0].shape_id))
    members = [m for m, _c in order]
    caps, lows = [], []
    for r in members:
        pts = np.asarray(r.polygon.exterior.coords if hasattr(r.polygon, "exterior")
                         else [c for g in r.polygon.geoms for c in g.exterior.coords], float)
        across = pts[:, 0] * nx + pts[:, 1] * ny
        caps.append(float(across.max() - across.min()))
        lows.append(float(across.max()))     # +normal is "down" for y-down art
    halfs = [c.stroke_mean_mm for c in cands]
    stroke = 2.0 * float(np.median(halfs)) if halfs else None
    spread = (float(np.std(halfs) / np.mean(halfs))
              if halfs and np.mean(halfs) > 0 else None)
    base = float(np.median(lows))
    along = [c.cx * ux + c.cy * uy for c in cands]
    a0, a1 = min(along), max(along)
    baseline = ((a0 * ux + base * nx, a0 * uy + base * ny),
                (a1 * ux + base * nx, a1 * uy + base * ny))
    slant = _stem_slant_deg(_house_chains(members), line) if line is not None else None
    return Word(word_id=_word_id([r.shape_id for r in members]), members=members,
                line_deg=line, slant_deg=slant, cap_mm=float(np.median(caps)),
                stroke_mm=stroke, stroke_spread=spread, baseline=baseline)


def detect_words(regions: list[Region], *, chart=None) -> list[Word]:
    """Every line of lettering in `regions`, nothing written. Deterministic:
    the linking is `textcluster._cluster`'s order-free union-find, the line
    split and the reading order sort with shape-id tie-breaks."""
    if chart is None:
        chart = threads.CHART
    words: list[Word] = []
    for comp in _cluster(_candidates(regions), LETTER_HEIGHT_RATIO, chart):
        if len(comp) < MIN_CLUSTER_MEMBERS:
            continue
        # Pattern elements leave first, and the rest re-link without them:
        # a rope laid next to a line of text chains the two into one
        # component, and the letters must not keep the rope's links.
        pattern = _pattern_ids(comp)
        kept = [c for c in comp if c.region.shape_id not in pattern]
        for sub in (_cluster(kept, LETTER_HEIGHT_RATIO, chart) if pattern else [comp]):
            for row in _split_lines(sub):
                if len(row) < MIN_CLUSTER_MEMBERS:
                    continue
                words.append(_describe([c.region for c in row], row))
    words.sort(key=lambda w: w.word_id)
    return words


WORD_KEYS = ("word_id", "word_index", "word_size", "word_line_deg", "word_slant_deg",
             "word_cap_mm", "word_stroke_mm")


def tag_words(regions: list[Region], *, chart=None) -> list[Word]:
    """`detect_words`, and every member's meta stamped with its word. A
    region in no word carries none of the keys (absent means false, the
    text cluster's convention). Returns the words for callers that group."""
    for r in regions:
        for k in WORD_KEYS:
            r.meta.pop(k, None)
    words = detect_words(regions, chart=chart)
    for w in words:
        for i, r in enumerate(w.members):
            r.meta["word_id"] = w.word_id
            r.meta["word_index"] = i
            r.meta["word_size"] = len(w.members)
            r.meta["word_line_deg"] = None if w.line_deg is None else round(w.line_deg, 2)
            r.meta["word_slant_deg"] = None if w.slant_deg is None else round(w.slant_deg, 2)
            r.meta["word_cap_mm"] = round(w.cap_mm, 3)
            r.meta["word_stroke_mm"] = None if w.stroke_mm is None else round(w.stroke_mm, 3)
    return words


def word_groups(regions: list[Region]) -> list[list[Region]]:
    """The tagged words as member lists in reading order, from the meta
    `tag_words` wrote -- for a reader that runs after it on the same
    regions. Sorted by word id, so callers iterate deterministically."""
    by: dict[str, list[tuple[int, Region]]] = {}
    for r in regions:
        wid = r.meta.get("word_id")
        if wid:
            by.setdefault(wid, []).append((int(r.meta.get("word_index", 0)), r))
    return [[r for _i, r in sorted(v, key=lambda t: t[0])] for _k, v in sorted(by.items())]


def is_text(region: Region, cfg) -> bool:
    """THE question every stitch-affecting lettering reader asks. Under
    `cfg.lettering_words` a word member; off, what each reader asked
    before -- the text cluster's `text_candidate`."""
    if getattr(cfg, "lettering_words", False):
        return bool(region.meta.get("word_id"))
    return bool(region.meta.get("text_candidate"))


def word_key(region: Region, cfg) -> str | None:
    """The group a reader keys a word by: `word_id` under
    `cfg.lettering_words`, else the text cluster's `text_cluster_id`."""
    if getattr(cfg, "lettering_words", False):
        return region.meta.get("word_id")
    return region.meta.get("text_cluster_id")


def word_ocr_text(regions: list[Region]) -> None:
    """Join the per-member OCR read (`textcluster.ocr_suggest_text`'s
    `ocr_char`) into each word's string, in reading order, as
    `word_ocr_text` on every member. Advisory, like the read itself; a
    member with no read contributes '?'. Written only where some member
    was read."""
    for members in word_groups(regions):
        chars = [r.meta.get("ocr_char") for r in members]
        if not any(chars):
            continue
        text = "".join(c if c else "?" for c in chars)
        for r in members:
            r.meta["word_ocr_text"] = text
