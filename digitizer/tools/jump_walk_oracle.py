"""The dense oracle for a sewn hop, judging the Python lane's `cut_every_jump`
walk from the DST BYTES (2026-11-01, the K3 handoff's "nitpick before card v8").

`stage7_sequence._cut_or_bury_jumps` samples a hop every `_BURY_STEP_MM`
(0.1 mm) at its centre and both thread edges before sewing it needle-down on
the work. The browser twin (`src/digitize.js` cutOrBuryJumps) samples every
0.01 mm because its test's oracle -- a thread-footprint raster of the file,
`tools/lettering-uncut-jumps.mjs` `bareNewSegments` -- found 17 segments on a
seventh of the font library whose centre ran along a satin rail and dipped up
to 0.015 mm off the thread between two stitch tips when the walk sampled at
0.1 mm. The Python walk had the same blind spot and was unmeasured. This is
that oracle, ported line for line (readDSTRecords, uncutMoves, threadSegments,
newSegments, bareNewSegments), run over an OFF and an ON file of one job:

- an UNCUT MOVE is one or two jump records between two stitch records of one
  thread (three or more are a cut to the machine);
- every needle-down segment the ON file has and the OFF file has not (the
  walks, the buries and the locks at new cuts) is sampled every `CELL_MM`
  along its centre and both edges of a `THREAD_W_MM` thread and read against
  a raster of the segments BOTH files have, where a cell is thread when its
  centre lies within half a thread plus half a cell diagonal of a segment;
- a lock (a five-record bounce p q p q p) is judged by its centreline alone,
  as the JS does: it rides the stitch it locks, and its far point rounded to
  the file's unit sits up to 0.035 mm past that stitch's edge in OFF files too.

It shares no code with the walk: the records are read from the bytes by the
Tajima layout here, not by `src/dst.js`, `src/dstimport.js` or pystitch, and
the DST is the service's own writer (`plan_to_pattern` + `formats.write`),
the path a machine file takes. `judge` reports every off-thread segment with
how far past the thread's edge its worst sample lies.

    python -m tools.jump_walk_oracle OFF.json ON.json     # two card-v8 cut dumps
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402

THREAD_W_MM = 0.4      # machine.COVERAGE_THREAD_W_MM, the width stage7's _UnderThread uses
CELL_MM = 0.01         # the raster's cell: ten times finer than _BURY_STEP_MM
U = 10                 # DST units per mm


def read_dst_records(b: bytes) -> list[tuple[int, int, str]]:
    """Every 3-byte record as (x, y, kind) in file units, kind one of
    stitch / jump / color, from the Tajima layout."""
    out = []
    x = y = 0
    for i in range(512, len(b) - 2, 3):
        b0, b1, b2 = b[i], b[i + 1], b[i + 2]
        if (b2 & 0xF3) == 0xF3:
            break

        def bit(bb, m, v):
            return v if bb & m else 0
        x += (bit(b0, 1, 1) - bit(b0, 2, 1) + bit(b0, 4, 9) - bit(b0, 8, 9) + bit(b1, 1, 3) - bit(b1, 2, 3)
              + bit(b1, 4, 27) - bit(b1, 8, 27) + bit(b2, 4, 81) - bit(b2, 8, 81))
        y += (bit(b0, 0x80, 1) - bit(b0, 0x40, 1) + bit(b0, 0x20, 9) - bit(b0, 0x10, 9) + bit(b1, 0x80, 3)
              - bit(b1, 0x40, 3) + bit(b1, 0x20, 27) - bit(b1, 0x10, 27) + bit(b2, 0x20, 81) - bit(b2, 0x10, 81))
        out.append((x, y, "color" if b2 & 0x40 else "jump" if b2 & 0x80 else "stitch"))
    return out


def uncut_moves(recs) -> list[tuple]:
    """(stitch before, stitch after, index of the stitch after, jump records)
    for every one-or-two-jump move between two stitches of one thread."""
    out = []
    last = None
    i = 0
    while i < len(recs):
        r = recs[i]
        if r[2] == "stitch":
            last = r
            i += 1
            continue
        if r[2] == "color":
            last = None
            i += 1
            continue
        j = i
        while j < len(recs) and recs[j][2] == "jump":
            j += 1
        n = j - i
        nxt = recs[j] if j < len(recs) else None
        if last and n < 3 and nxt and nxt[2] == "stitch":
            out.append((last, nxt, j, n))
        if n >= 3:
            last = None
        i = j
    return out


def thread_segments(recs) -> list[tuple]:
    """Every needle-down segment (ax, ay, bx, by, k), k the index of its second record."""
    return [(p[0], p[1], q[0], q[1], k) for k, (p, q) in enumerate(zip(recs, recs[1:]), start=1)
            if p[2] == "stitch" and q[2] == "stitch" and (p[0], p[1]) != (q[0], q[1])]


def _samples(ax, ay, bx, by, half, step, edges):
    d = math.hypot(bx - ax, by - ay)
    n = max(2, math.ceil(d / step) + 1)
    nx, ny = ((ay - by) / d, (bx - ax) / d) if d > 0 else (0.0, 0.0)
    t = np.linspace(0.0, 1.0, n)
    cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
    offs = (-half, 0.0, half) if edges else (0.0,)
    return np.concatenate([cx + o * nx for o in offs]), np.concatenate([cy + o * ny for o in offs])


def bare_samples(ax, ay, bx, by, cover, centre_only: bool) -> list[tuple[float, float]]:
    """The samples of the segment a->b (file units) that fall on no cell of a
    `CELL_MM` raster of `cover`'s thread: empty when the segment is on thread."""
    half, cell = THREAD_W_MM / 2 * U, CELL_MM * U
    px, py = _samples(ax, ay, bx, by, half, cell, not centre_only)
    x0, y0 = px.min() - cell, py.min() - cell
    x1, y1 = px.max() + cell, py.max() + cell
    W, H = math.ceil((x1 - x0) / cell) + 1, math.ceil((y1 - y0) / cell) + 1
    raster = np.zeros((H, W), bool)
    reach = half + cell * math.sqrt(0.5)
    gx, gy = np.meshgrid((np.arange(W) + 0.5) * cell + x0, (np.arange(H) + 0.5) * cell + y0)
    for sax, say, sbx, sby, _k in cover:
        sx0, sx1 = min(sax, sbx) - reach, max(sax, sbx) + reach
        sy0, sy1 = min(say, sby) - reach, max(say, sby) + reach
        if sx1 < x0 or sx0 > x1 or sy1 < y0 or sy0 > y1:
            continue
        c0, c1 = max(0, int((sx0 - x0) // cell)), min(W - 1, math.ceil((sx1 - x0) / cell))
        r0, r1 = max(0, int((sy0 - y0) // cell)), min(H - 1, math.ceil((sy1 - y0) / cell))
        X, Y = gx[r0:r1 + 1, c0:c1 + 1], gy[r0:r1 + 1, c0:c1 + 1]
        dx, dy = sbx - sax, sby - say
        L2 = dx * dx + dy * dy
        t = np.clip(((X - sax) * dx + (Y - say) * dy) / L2, 0, 1) if L2 > 0 else np.zeros_like(X)
        raster[r0:r1 + 1, c0:c1 + 1] |= np.hypot(X - (sax + t * dx), Y - (say + t * dy)) <= reach
    c = ((px - x0) // cell).astype(int)
    r = ((py - y0) // cell).astype(int)
    hit = raster[r, c]
    return [(float(px[i]), float(py[i])) for i in np.where(~hit)[0]]


def new_segments(on_recs, off_recs):
    """(fresh, old): the needle-down segments of ON that OFF has not, as a
    multiset of their two ends, each with whether it lies inside a lock
    bounce; and the ones both have."""
    left = Counter((s[0], s[1], s[2], s[3]) for s in thread_segments(off_recs))
    in_lock = np.zeros(len(on_recs), bool)

    def same(p, q):
        return (p[0], p[1]) == (q[0], q[1])
    for i in range(len(on_recs) - 4):
        f = on_recs[i:i + 5]
        if (all(r[2] == "stitch" for r in f) and same(f[0], f[2]) and same(f[2], f[4])
                and same(f[1], f[3]) and not same(f[0], f[1])):
            in_lock[i + 1:i + 5] = True
    fresh, old = [], []
    for s in thread_segments(on_recs):
        k = (s[0], s[1], s[2], s[3])
        if left[k] > 0:
            left[k] -= 1
            old.append(s)
        else:
            fresh.append((s, bool(in_lock[s[4]])))
    return fresh, old


def _closest(px, py, s):
    ax, ay, bx, by, _k = s
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return (ax + t * dx, ay + t * dy)


def bare_new_segments(on_recs, off_recs):
    """(fresh, bare, worst_mm): the ON-only segments, those with a sample on
    no thread of the segments both files have, and the furthest any such
    sample lies past the thread's edge, in mm."""
    fresh, old = new_segments(on_recs, off_recs)
    oldarr = np.array([(s[0], s[1], s[2], s[3]) for s in old], float).reshape(-1, 4)
    bad = []
    worst = 0.0
    for s, lock in fresh:
        ax, ay, bx, by, _k = s
        near = 2 * U
        m = ((np.minimum(oldarr[:, 0], oldarr[:, 2]) <= max(ax, bx) + near)
             & (np.maximum(oldarr[:, 0], oldarr[:, 2]) >= min(ax, bx) - near)
             & (np.minimum(oldarr[:, 1], oldarr[:, 3]) <= max(ay, by) + near)
             & (np.maximum(oldarr[:, 1], oldarr[:, 3]) >= min(ay, by) - near))
        cover = [old[i] for i in np.where(m)[0]]
        bare = bare_samples(ax, ay, bx, by, cover, lock)
        if bare:
            dev = 0.0
            for (qx, qy) in bare:
                dmin = min((math.dist((qx, qy), _closest(qx, qy, c)) for c in cover), default=float("inf"))
                dev = max(dev, dmin - THREAD_W_MM / 2 * U)
            worst = max(worst, dev)
            bad.append((s, lock, len(bare), dev / U))
    return fresh, bad, worst / U


def dst_bytes(plan: StitchPlan) -> bytes:
    return formats.write(plan_to_pattern(plan), "dst")


def judge(off_plan: StitchPlan, on_plan: StitchPlan, label: str = "") -> dict:
    """The verdict on ON against OFF, both written as the service writes them."""
    ro, rn = read_dst_records(dst_bytes(off_plan)), read_dst_records(dst_bytes(on_plan))
    fresh, bad, worst = bare_new_segments(rn, ro)
    walks = [(s, lk) for s, lk in fresh if not lk]
    return {"label": label, "sample_step_mm": CELL_MM, "walk_step_mm": 0.1,
            "off_uncut_moves": len(uncut_moves(ro)), "on_uncut_moves": len(uncut_moves(rn)),
            "off_stitches": sum(1 for r in ro if r[2] == "stitch"),
            "on_stitches": sum(1 for r in rn if r[2] == "stitch"),
            "on_new_segments": len(fresh), "of_them_locks": len(fresh) - len(walks),
            "walked_segments": len(walks),
            "walked_mm": round(sum(math.hypot(s[2] - s[0], s[3] - s[1]) for s, _lk in walks) / U, 2),
            "bare_segments": len(bad), "bare_walked_segments": sum(1 for b in bad if not b[1]),
            "worst_off_thread_mm": round(worst, 4),
            "bare_detail": [{"from_mm": [round(b[0][0] / U, 2), round(b[0][1] / U, 2)],
                             "to_mm": [round(b[0][2] / U, 2), round(b[0][3] / U, 2)],
                             "length_mm": round(math.hypot(b[0][2] - b[0][0], b[0][3] - b[0][1]) / U, 2),
                             "lock": b[1], "bare_samples": b[2], "off_thread_mm": round(b[3], 4)}
                            for b in bad[:40]]}


def plan_from_dump(d: dict) -> StitchPlan:
    """A card-v8 cut dump's whole plan (`runs` with `b`, `kind`, `shape_id`,
    `rgb`, `jump`, `trim`, `points`) back as a StitchPlan."""
    blocks: dict = {}
    for r in d["runs"]:
        blocks.setdefault(r["b"], (tuple(r["rgb"]), []))[1].append(
            StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=bool(r["jump"]),
                      trim=bool(r["trim"]), shape_id=r["shape_id"]))
    return StitchPlan(blocks=[StitchBlock(thread_index=i, thread_number=str(i + 1), rgb=rgb, runs=runs)
                              for i, (rgb, runs) in sorted(blocks.items())], palette=[], warnings=[])


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        print(__doc__)
        return 2
    off = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    on = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    print(json.dumps(judge(plan_from_dump(off), plan_from_dump(on), args[2] if len(args) > 2 else ""), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
