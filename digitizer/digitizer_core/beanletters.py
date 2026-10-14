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
        if cfg.lettering_word_tiers:
            # L3: one tier per word -- the whole word goes bean or none of
            # it does, on the median of its members' ink.
            known = [i.stroke_mm for i in inks if i.stroke_mm is not None]
            whole = bool(known) and float(np.median(known)) < float(line)
            goes = [whole and i.stroke_mm is not None for i in inks]
        else:
            goes = weight_groups([i.stroke_mm for i in inks], float(line))
        for r, ink, go in zip(members, inks, goes):
            if ink.stroke_mm is not None:
                r.meta["ink_stroke_mm"] = round(ink.stroke_mm, 3)
            if go and ink.spines:
                r.meta[BEAN_LETTER_KEY] = ink.spines
                tagged += 1
    return tagged


# The widest counter whose bean letter is held off it
# (`cfg.bean_letter_counter_hold_mm`), across its widest point. Fremont's 81 mm
# counters are 0.5-0.85 mm across (8, 9, the tagline's A's and P); past about
# a millimetre a 0.4 mm thread centred on the stroke leaves most of a counter
# bare anyway, and the letter is no longer the small lettering this is for.
# A CANDIDATE (gate 1).
COUNTER_HOLD_MAX_MM = 1.0


def hold_bean_counters(regions, p, cfg: PipelineConfig) -> int:
    """Re-read the ink of every cluster `tag_bean_letters` tagged, with each
    needle point held `cfg.bean_letter_counter_hold_mm` off the ink's small
    counters (`ink_path.hold_off_counters`), and swap in those spines. The
    clusters are formed exactly as `tag_bean_letters` forms them, so the
    skeleton is the same one and only points near a counter move. -> how many
    members' spines changed. None on the config reads nothing."""
    hold = cfg.bean_letter_counter_hold_mm
    if not hold or hold <= 0 or p is None:
        return 0
    clusters: dict[str, list] = {}
    for r in regions:
        cid = word_key(r, cfg)
        if (cid and r.meta.get("stitched", True)
                and str(r.meta.get("tier", "auto")).lower() == "auto"):
            clusters.setdefault(cid, []).append(r)
    changed = 0
    for members in clusters.values():
        if not any(r.meta.get(BEAN_LETTER_KEY) for r in members):
            continue
        inks = read_cluster_ink(p, members, counter_hold_mm=float(hold),
                                counter_max_mm=COUNTER_HOLD_MAX_MM)
        for r, ink in zip(members, inks):
            old = r.meta.get(BEAN_LETTER_KEY)
            # Same skeleton, same edges: only the points move. A read that
            # disagrees on the spines' shape is not this letter's -- keep it.
            if not old or len(ink.spines) != len(old) or any(
                    len(a) != len(b) for a, b in zip(ink.spines, old)):
                continue
            if ink.spines != old:
                r.meta[BEAN_LETTER_KEY] = ink.spines
                r.meta["bean_counter_held"] = True
                changed += 1
    return changed
