"""Reading order of a word's letters: lines top to bottom, each left to right.

`cfg.extra["lettering_columns_reading_order"]` (built OFF 2026-11-16) sews the
letters of one span -- letters stage 7's OFF path sews back to back -- in this
order, in place of nearest-neighbour from the needle (`stage7_sequence`).

Why: under the Column lane the span's order followed the needle, so it
followed each letter's EXIT, and any change to one letter's end moved it.
`lettering_columns_lean_flat_ends` moved one end on Gaulke's LC and the word
flipped: entered from the other side, the G sewed every satin the other way.
A satin sewn backwards leans its returns the other way and lays its last
column on top at the bar, and `tools/apex_pro.py` read the G 12.7 -> 23.4
(satin only) on needle-identical stations.

The pro sews his lettering in reading order. Sew order against x, per line,
corpus captures and his DSTs: +0.77 to +1.00 on all five Becker jobs, the
Gaulke hat and LC lines and Drone (16 of 22 lines positive). Ours: -1.00 on
every Becker line, +0.06 and +0.48 on Gaulke LC.

Lines are read from the letters' boxes (`reading_ranks`): two letters share a
line when their vertical extents overlap by `LINE_OVERLAP` of the shorter.
A mark under `SMALL_MARK_FRAC` of the span's median height (an i's dot, an
accent, a full stop) joins the line it sits nearest, at its own x. A line on
an arc chains letter to letter, so it stays one line. Geometric guards, not
physical constants: nothing here is decided by a sew-out.
"""
from __future__ import annotations

from statistics import median

LINE_OVERLAP = 0.5        # shared vertical extent, as a share of the shorter letter
SMALL_MARK_FRAC = 0.5     # a mark this far under the median height joins a line, not makes one


def reading_ranks(polys: dict) -> dict:
    """shape id -> its 0-based place in reading order, for one span's letter
    polygons: lines top first (y runs down), letters left first; ties on id."""
    if not polys:
        return {}
    box = {sid: p.bounds for sid, p in polys.items()}
    cx = {sid: (b[0] + b[2]) / 2 for sid, b in box.items()}
    cy = {sid: (b[1] + b[3]) / 2 for sid, b in box.items()}
    h = {sid: max(b[3] - b[1], 1e-9) for sid, b in box.items()}
    med = median(h.values())
    big = sorted(sid for sid in box if h[sid] >= SMALL_MARK_FRAC * med)
    small = sorted(sid for sid in box if sid not in set(big))
    if not big:                       # every mark small: they are the line
        big, small = sorted(box), []

    parent = {sid: sid for sid in big}

    def find(s):
        while parent[s] != s:
            parent[s] = parent[parent[s]]
            s = parent[s]
        return s

    for i, a in enumerate(big):
        for b in big[i + 1:]:
            ov = min(box[a][3], box[b][3]) - max(box[a][1], box[b][1])
            if ov >= LINE_OVERLAP * min(h[a], h[b]):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    lines: dict = {}
    for sid in big:
        lines.setdefault(find(sid), []).append(sid)
    span = {k: (min(box[s][1] for s in v), max(box[s][3] for s in v),
                min(box[s][0] for s in v), max(box[s][2] for s in v)) for k, v in lines.items()}

    def gap(sid, k):
        y0, y1, x0, x1 = span[k]
        dy = max(0.0, y0 - box[sid][3], box[sid][1] - y1)
        dx = max(0.0, x0 - cx[sid], cx[sid] - x1)
        return (dx > med, dy + dx, k)          # a line under or over the mark first
    for sid in small:
        lines[min(lines, key=lambda k: gap(sid, k))].append(sid)
    order = sorted(lines, key=lambda k: (median(cy[s] for s in lines[k] if s in parent), k))
    out: dict = {}
    for k in order:
        for sid in sorted(lines[k], key=lambda s: (cx[s], s)):
            out[sid] = len(out)
    return out
