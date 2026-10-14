"""Which lettering sews as bean runs, and along what
(`cfg.bean_letter_max_stroke_mm`, 2026-10-02;
`docs/superpowers/specs/2026-10-02-bean-letters-design.md`).

`tag_bean_letters` reads each text cluster's ink once (`ink_path`), decides
per WEIGHT GROUP, and writes the bean paths on the members that go:
`meta[BEAN_LETTER_KEY]` (polylines in design mm) and `meta["ink_stroke_mm"]`.
Stage 5 and stage 7 only read the key.

Weight, not line of text. The spec first asked for lines; bridge's words run
on an arc and Golke's word gaps equal its line gap, so a geometric line
splitter has no clean rule, while the thing being decided IS the weight. A
cluster splits in two only when both groups are real -- three members each --
and sit on opposite sides of the line; otherwise the cluster's median decides
for all of it, which is what carries bridge's two fused pairs (1.08 and
1.17 mm) along with the six letters at 0.6-0.8.
"""
from __future__ import annotations

import numpy as np

from .config import PipelineConfig
from .ink_path import read_cluster_ink
from .words import word_key

BEAN_LETTER_KEY = "bean_letter_spines"
# A weight group smaller than this is a few fused letters, not a second line.
MIN_GROUP_MEMBERS = 3
# An ink read is the LETTER only when the traced shape agrees with it: the
# shape's own mean width (2 x area / perimeter) is at most this many times the
# ink's stroke. Past it the read found texture INSIDE a bold letter, not the
# letter -- drone's chrome "PRECISION" (7-8 mm caps, traced 1.6-2.0 mm wide,
# ink 0.28-0.35 mm off the highlight between its bevel lines, 4.7-6.7x) went
# bean and sewed as hollow outlines (+170.8 mm2 ARTWORK_UNCOVERED, PR #944).
# Measured 2026-10-14 over every member the tagger read in the corpus: every
# letter that went bean and should is 0.66-1.34x, bridge's counter-closed
# blobs 2.11-2.28x (the case the ink read exists for). A CANDIDATE (ROADMAP
# gate 1), set between those two populations; nothing sewn.
INK_SHAPE_MAX_RATIO = 3.0


def ink_reads_shape(polygon, stroke_mm: float | None) -> bool:
    """False when `polygon` is far wider than the ink read `stroke_mm` says
    (`INK_SHAPE_MAX_RATIO`): the read is not this letter's stroke. No read is
    no agreement; no polygon is nothing to disagree with."""
    if stroke_mm is None:
        return False
    if polygon is None or stroke_mm <= 0:
        return True
    perimeter = float(polygon.length)
    if perimeter <= 0:
        return True
    return 2.0 * float(polygon.area) / perimeter <= INK_SHAPE_MAX_RATIO * stroke_mm


def weight_groups(widths: list[float | None], line_mm: float) -> list[bool]:
    """-> per member, True if it sews as bean. `widths` are ink stroke widths
    in mm (None: no ink read -- never bean)."""
    known = sorted(w for w in widths if w is not None)
    if not known:
        return [False] * len(widths)
    # The NATURAL two-way split of the sorted widths (least within-group
    # spread, over every cut), taken only if both sides of it are real groups.
    # Searching among the allowed cuts instead would always find one: bridge's
    # six thin letters and two fused pairs split 5 | 3 that way, and three of
    # one word's letters stayed satin.
    cut = None
    if len(known) >= 2:
        a = np.asarray(known, np.float64)
        costs = [(float(a[:k].var() * k + a[k:].var() * (len(a) - k)), k)
                 for k in range(1, len(a))]
        _cost, k = min(costs)
        if (min(k, len(a) - k) >= MIN_GROUP_MEMBERS
                and float(np.median(a[:k])) < line_mm <= float(np.median(a[k:]))):
            cut = float(a[k - 1] + a[k]) / 2.0
    if cut is not None:
        return [w is not None and w < cut for w in widths]
    whole = float(np.median(known)) < line_mm
    return [whole and w is not None for w in widths]


def tag_bean_letters(regions, p, cfg: PipelineConfig) -> int:
    """Tag the members that sew as bean letters; -> how many. None on the
    config tags nothing and reads nothing. A member the review screen pinned
    to a tier, or switched off, is left out of the decision and untouched."""
    line = cfg.bean_letter_max_stroke_mm
    if line is None or p is None:
        return 0
    clusters: dict[str, list] = {}
    for r in regions:
        cid = word_key(r, cfg)
        if (cid and r.meta.get("stitched", True)
                and str(r.meta.get("tier", "auto")).lower() == "auto"):
            clusters.setdefault(cid, []).append(r)
    tagged = 0
    for members in clusters.values():
        inks = read_cluster_ink(p, members)
        # A read the traced shape disagrees with is no read: left out of the
        # decision and never bean (`INK_SHAPE_MAX_RATIO`).
        widths = [i.stroke_mm if ink_reads_shape(getattr(r, "polygon", None), i.stroke_mm) else None
                  for r, i in zip(members, inks)]
        if cfg.lettering_word_tiers:
            # L3: one tier per word -- the whole word goes bean or none of
            # it does, on the median of its members' ink.
            known = [w for w in widths if w is not None]
            whole = bool(known) and float(np.median(known)) < float(line)
            goes = [whole and w is not None for w in widths]
        else:
            goes = weight_groups(widths, float(line))
        for r, ink, go in zip(members, inks, goes):
            if ink.stroke_mm is not None:
                r.meta["ink_stroke_mm"] = round(ink.stroke_mm, 3)
            if go and ink.spines:
                r.meta[BEAN_LETTER_KEY] = ink.spines
                tagged += 1
    return tagged
