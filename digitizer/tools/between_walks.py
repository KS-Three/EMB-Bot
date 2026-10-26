"""between_walks: how a machine file gets from one piece to the next, same reader both sides.

    python -m tools.between_walks FILE [FILE ...] [--steps] [--json OUT]

Built 2026-10-26 for W4-03 (#1072's third trim item): on Precision Drone the
pro walks about a metre needle-down between pieces and cuts 38 times for 84
pieces, where we cut 82 times for 90. Before building a walk, read what his
walks are: how long, and what they lie under.

Pieces and visits are `tools.sequence_pro`'s (one colour block's footprint,
a lone run line opened away, a visit a maximal stretch of penetrations in one
piece), so the step counts here are that tool's `inter_moves`. Read the DST,
never the PES (the PES reader reports a TRIM at every jump); each file in its
own frame.

Every STEP from one piece's visit to a different piece's next visit is one of

- `cut`: a TRIM record on the way (any needle-down thread on the way is
  counted too, as `walked_mm`);
- `flown`: needle-up with no trim (an uncut jump, a float to snip);
- `walked`: needle-down the whole way.

Each needle-down step stitch is sampled every 0.1 mm at its centre and both
thread edges (half of `COVERAGE_THREAD_W_MM` either side: stage 7's
`_UnderThread` samples) and every point is read against the file's OTHER
needle-down segments, each a centreline buffered half a thread:

- `buried`: all three samples under a centreline sewn LATER than this
  stitch (or within a thread width of either end of the step, where the
  needle penetrates anyway: stage 7's end allowance). Split by the block of
  the covering thread (`same` = all three under this colour's later thread,
  the end allowance included; `later` = the rest, some of it under a later
  colour) and by its stitch (`zigzag` = a segment that reverses against
  both neighbours, satin or zigzag underlay; else `straight` = fill rows,
  runs, run underlay -- the DST cannot tell those apart);
- `on_work`: not buried, but all three under SOME other thread, sewn before
  or after (a walk on top of finished work, or under thread that only
  covers part of its width); `on_own` is the part of it on this block's own
  thread, and `edge` the not-buried part whose CENTRE sample is buried (a
  thread edge out);
- `bare`: the rest -- some of the thread lies on fabric.

A lone run line is opened away by the piece rule, so a design's run-stitch
outline reads as a walk too: on the pro's Drone most of the `on_work` mm is
the drone body's outline. Look at the sew path before calling it travel.

For a `cut` or `flown` step, the same reading is taken of the straight hop
from the needle's last penetration in the first piece to its first in the
second (`hop_*`), against thread sewn after the step: what a straight walk
there would have lain under.

`diagnose_plan(plan)` reads OUR side from the stitch plan instead: for every
cut left inside a colour block, whether any route under later thread joins
its ends (stage 7's own cover and raster, no length budget), and if none,
what the cheapest route's uncovered part lies on (see its docstring).

It reads; it does not judge. Measured with it 2026-10-26
(`docs/buried-walk-2026-10-26.md`): the pro's buried walks sit inside stage
7's detour budget at his p90, and none of our between-piece cuts on five
hats has a route under later thread at any length -- the gap is layering and
colour order, not the walk rule.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import sequence_pro as sp  # noqa: E402

HALF_MM = 0.2          # half of machine.COVERAGE_THREAD_W_MM
END_MM = 0.4           # stage 7's end allowance: one thread width
STEP_MM = 0.1          # stage 7's _BURY_STEP_MM
ZIGZAG_DEG = 140.0     # a turn sharper than this against both neighbours reads as a zigzag


def visits(ids: list[int]) -> list[dict]:
    """`sequence_pro.read_block`'s visits: maximal stretches of one piece
    id, crumbs under `MIN_PIECE_PTS` dropped, neighbours re-merged."""
    out: list[dict] = []
    for i, pid in enumerate(ids):
        if pid == 0:
            continue
        if out and out[-1]["pid"] == pid:
            out[-1]["last"] = i
            out[-1]["n"] += 1
        else:
            out.append({"pid": pid, "first": i, "last": i, "n": 1})
    counts: dict[int, int] = {}
    for v in out:
        counts[v["pid"]] = counts.get(v["pid"], 0) + v["n"]
    keep = {p for p, n in counts.items() if n >= sp.MIN_PIECE_PTS}
    merged: list[dict] = []
    for v in out:
        if v["pid"] not in keep:
            continue
        if merged and merged[-1]["pid"] == v["pid"]:
            merged[-1]["last"] = v["last"]
            merged[-1]["n"] += v["n"]
        else:
            merged.append(dict(v))
    return merged


def _turn_deg(u, v) -> float:
    nu, nv = math.hypot(*u), math.hypot(*v)
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    c = max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / (nu * nv)))
    return math.degrees(math.acos(c))


class _Thread:
    """Every needle-down segment of a file, in sew order, as an STRtree of
    centrelines: `segs[i] = (order, block, a, b)`, `zigzag[i]`."""

    def __init__(self, blocks_moves):
        import numpy as np
        import shapely
        from shapely.geometry import LineString
        segs, zz = [], []
        # sew order of the move INTO penetration j of block bi: base[bi] + j
        self.base: list[int] = []
        base = 0
        for mv in blocks_moves:
            self.base.append(base)
            base += len(mv) + 1
        for bi, mv in enumerate(blocks_moves):
            for j in range(1, len(mv)):
                if mv[j]["up"]:
                    continue
                a, b = mv[j - 1]["p"], mv[j]["p"]
                order = self.base[bi] + j
                u = (b[0] - a[0], b[1] - a[1])
                rev = []
                for jj in (j - 1, j + 1):
                    if 1 <= jj < len(mv) and not mv[jj]["up"]:
                        p, q = mv[jj - 1]["p"], mv[jj]["p"]
                        w = (q[0] - p[0], q[1] - p[1])
                        rev.append(_turn_deg(u, w) > ZIGZAG_DEG)
                    else:
                        rev.append(False)
                zz.append(all(rev))
                segs.append((order, bi, a, b))
        self.segs = segs
        self.ords = np.array([s[0] for s in segs], np.int64)
        self.blks = np.array([s[1] for s in segs], np.int64)
        self.zigzag = np.array(zz, bool)
        lines = []
        for _o, _b, a, b in segs:
            if math.dist(a, b) < 1e-6:
                b = (a[0] + 1e-4, a[1])
            lines.append(LineString([a, b]))
        self.tree = shapely.STRtree(lines)
        self._shapely = shapely

    def read(self, a, b, after: int, own: tuple[int, int], ends, block: int) -> dict:
        """mm of the segment a-b that is buried (split same/later block and
        zigzag/straight), on_work, bare. `after`: thread with order > after
        is later. `own`: the (lo, hi) order range of the step itself, never
        cover. `ends`: points with the end allowance."""
        import numpy as np
        d = math.dist(a, b)
        out = dict(buried=0.0, same=0.0, later=0.0, zigzag=0.0, straight=0.0, edge=0.0, on_work=0.0, on_own=0.0,
                   bare=0.0)
        if d < 1e-9:
            return out
        n = max(2, int(math.ceil(d / STEP_MM)) + 1)
        t = np.linspace(0.0, 1.0, n)
        cx, cy = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        nx, ny = (a[1] - b[1]) / d, (b[0] - a[0]) / d
        lo, hi = own
        bur = np.ones(n, bool)
        anyc = np.ones(n, bool)
        own_c = np.ones(n, bool)
        same = np.ones(n, bool)
        zig = np.zeros(n, bool)
        mid = np.zeros(n, bool)
        for o in (-HALF_MM, 0.0, HALF_MM):
            px, py = cx + o * nx, cy + o * ny
            at_end = np.zeros(n, bool)
            for ex, ey in ends:
                at_end |= np.hypot(px - ex, py - ey) <= END_MM
            hp, hl = self.tree.query(self._shapely.points(px, py), predicate="dwithin", distance=HALF_MM)
            other = (self.ords[hl] < lo) | (self.ords[hl] > hi)
            hp, hl = hp[other], hl[other]
            later = self.ords[hl] > after
            b_ok = np.zeros(n, bool)
            b_ok[hp[later]] = True
            a_ok = np.zeros(n, bool)
            a_ok[hp] = True
            o_ok = np.zeros(n, bool)
            o_ok[hp[self.blks[hl] == block]] = True
            s_ok = np.zeros(n, bool)
            s_ok[hp[later & (self.blks[hl] == block)]] = True
            z_ok = np.zeros(n, bool)
            z_ok[hp[later & self.zigzag[hl]]] = True
            if o == 0.0:
                mid = b_ok | at_end
            bur &= b_ok | at_end
            anyc &= a_ok | at_end
            own_c &= o_ok | at_end
            same &= s_ok | at_end
            zig |= z_ok
        w = d / n
        out["buried"] = float(bur.sum()) * w
        out["same"] = float((bur & same).sum()) * w
        out["later"] = out["buried"] - out["same"]
        out["zigzag"] = float((bur & zig).sum()) * w
        out["straight"] = out["buried"] - out["zigzag"]
        out["edge"] = float((mid & ~bur).sum()) * w
        out["on_work"] = float((anyc & ~bur).sum()) * w
        out["on_own"] = float((own_c & ~bur).sum()) * w
        out["bare"] = d - out["buried"] - out["on_work"]
        return out


def read_steps(path) -> dict:
    """-> {"file", "steps": [...], "pieces": n} for one machine file."""
    f = sp.read(path)
    bm = [sp.moves(b) for b in f["blocks"]]
    th = _Thread(bm)
    steps = []
    n_pieces = 0
    for bi, mv in enumerate(bm):
        _lab, ids, _o = sp.pieces(mv, f["extents"])
        vs = visits(ids)
        n_pieces += len({v["pid"] for v in vs})
        for va, vb in zip(vs, vs[1:]):
            if va["pid"] == vb["pid"]:
                continue
            j0, j1 = va["last"] + 1, vb["first"]
            exit_p, entry_p = mv[va["last"]]["p"], mv[vb["first"]]["p"]
            lo, hi = th.base[bi] + j0, th.base[bi] + j1
            row = dict(block=bi, a=va["pid"], b=vb["pid"], walked_mm=0.0, up_mm=0.0, trims=0, jumps=0,
                       stitches=0, buried=0.0, same=0.0, later=0.0, zigzag=0.0, straight=0.0,
                       edge=0.0, on_work=0.0, on_own=0.0, bare=0.0, hop_mm=round(math.dist(exit_p, entry_p), 2),
                       at=[round(entry_p[0], 2), round(entry_p[1], 2)])
            for j in range(j0, j1 + 1):
                a, b = mv[j - 1]["p"], mv[j]["p"]
                d = math.dist(a, b)
                if mv[j]["up"]:
                    row["up_mm"] += d
                    row["jumps"] += 1
                    row["trims"] += mv[j]["trim"]
                    continue
                row["walked_mm"] += d
                row["stitches"] += 1
                r = th.read(a, b, th.base[bi] + j, (lo, hi), (exit_p, entry_p), bi)
                for k in ("buried", "same", "later", "zigzag", "straight", "edge", "on_work", "on_own", "bare"):
                    row[k] += r[k]
            row["cls"] = "cut" if row["trims"] else ("flown" if row["jumps"] else "walked")
            if row["cls"] != "walked":
                r = th.read(exit_p, entry_p, hi, (lo, hi), (exit_p, entry_p), bi)
                row.update({f"hop_{k}": round(v, 2) for k, v in r.items()})
            for k in ("walked_mm", "up_mm", "buried", "same", "later", "zigzag", "straight", "edge", "on_work",
                      "on_own", "bare"):
                row[k] = round(row[k], 2)
            steps.append(row)
    return {"file": Path(path).name, "pieces": n_pieces, "steps": steps}


def summary(reading: dict) -> dict:
    """Per class: steps, walked / up mm, and the walked thread's cover."""
    st = reading["steps"]
    out = {"file": reading["file"], "pieces": reading["pieces"], "steps": len(st)}
    for cls in ("cut", "flown", "walked"):
        rr = [s for s in st if s["cls"] == cls]
        out[cls] = len(rr)
        out[f"{cls}_up_mm"] = round(sum(s["up_mm"] for s in rr), 1)
    out["cut_trims"] = sum(s["trims"] for s in st)
    w = [s for s in st if s["walked_mm"] > 0]
    for k in ("walked_mm", "buried", "same", "later", "zigzag", "straight", "edge", "on_work", "on_own", "bare"):
        out[k] = round(sum(s[k] for s in w), 1)
    # the walks a pure walk rule would copy: needle-down the whole way, every
    # mm under later thread (bare and on-work under 0.5 mm, sampling slack)
    clean = sorted(s["walked_mm"] for s in st if s["cls"] == "walked" and s["bare"] + s["on_work"] < 0.5)
    out["clean_walks"] = len(clean)
    out["clean_walk_mm"] = round(sum(clean), 1)
    if clean:
        out["clean_walk_p50_p90_max"] = [round(_q(clean, 0.5), 1), round(_q(clean, 0.9), 1), round(clean[-1], 1)]
    hops = [s for s in st if s["cls"] != "walked"]
    out["cut_hop_mm"] = round(sum(s["hop_mm"] for s in hops), 1)
    for k in ("buried", "on_work", "bare"):
        out[f"cut_hop_{k}"] = round(sum(s.get(f"hop_{k}", 0.0) for s in hops), 1)
    out["cut_hop_fully_buried"] = sum(1 for s in hops if s.get("hop_bare", 0) + s.get("hop_on_work", 0) < 0.05)
    return out


def diagnose_plan(plan, margin_mm: float = 15.0) -> list[dict]:
    """Every cut left inside a colour block of OUR plan, and what refuses a
    buried walk there. -> one row per cut.

    The cover is stage 7's own (`_later_thread_burier` on the finished
    blocks: every non-travel run sewn at or after the cut, a centreline
    buffered half a thread), and the route search is `_bury_route`'s raster
    (later centrelines drawn one thread wide at `_BURY_PX_PER_MM`, eroded by
    half a thread and a half more), but with NO length budget, over the hop's
    box grown by `margin_mm` (at most) each side. Classes:

    - `takes_now`: `bury(k)` on the finished layout finds a route (thread
      added after the bury pass -- the edge cap, hairlines -- covers it);
    - `gap_cap`: a buried route exists but the hop is longer than
      `LINK_MAX_GAP_MM`;
    - `budget`: a buried route exists, longer than `_link_budget_mm(gap)`;
    - `in_budget`: a raster route inside the budget, refused by the exact
      test or the stitch cap;
    - `no_route`: nothing under later thread joins the two ends. Then the
      cheapest route that leaves the later thread as little as possible
      (`off_mm`) is split by what that part lies on: this colour's own
      earlier stitches (`off_on_own_mm`: the order of shapes inside the
      colour), another colour sewn earlier (`off_on_earlier_mm`: the colour
      order would have to change to bury it), or fabric (`off_bare_mm`)."""
    import cv2
    import numpy as np
    import shapely
    from shapely.geometry import LineString
    from skimage.graph import MCP_Geometric
    from digitizer_core import machine, stitches
    from digitizer_core.stage7_sequence import _BURY_PX_PER_MM, _later_thread_burier, _link_budget_mm
    seq, bury = _later_thread_burier(plan.blocks)
    half = machine.COVERAGE_THREAD_W_MM / 2.0
    lines: list = []
    for k, (_bi, r) in enumerate(seq):
        pts = list(r.points)
        if k > 0 and not r.jump and seq[k - 1][1].points:
            pts = [seq[k - 1][1].points[-1]] + pts
        lines.append(LineString(pts) if r.kind != stitches.TRAVEL and len(pts) >= 2 else None)
    idx = [k for k, g in enumerate(lines) if g is not None]
    tree = shapely.STRtree([lines[k] for k in idx])
    ppm = _BURY_PX_PER_MM
    lw = max(1, int(round(2 * half * ppm)))
    er = int(math.ceil((half + half / 2.0) * ppm)) + 1
    kern = np.ones((2 * er + 1, 2 * er + 1), np.uint8)
    rows = []
    for k in range(1, len(seq)):
        bi, run = seq[k]
        prev = seq[k - 1][1]
        if not run.trim or seq[k - 1][0] != bi or not prev.points or not run.points:
            continue
        a, b = prev.points[-1], run.points[0]
        gap = math.dist(a, b)
        row = dict(block=bi, k=k, gap_mm=round(gap, 2), between=prev.shape_id != run.shape_id,
                   pair=f"{prev.shape_id}:{prev.kind}>{run.shape_id}:{run.kind}",
                   budget_mm=round(_link_budget_mm(gap), 1), at=[round(b[0], 2), round(b[1], 2)])
        if bury(k) is not None:
            row["cls"] = "takes_now"
            rows.append(row)
            continue
        m = min(margin_mm, max(5.0, gap))
        x0, y0 = min(a[0], b[0]) - m, min(a[1], b[1]) - m
        nx = int(math.ceil((abs(a[0] - b[0]) + 2 * m) * ppm)) + 1
        ny = int(math.ceil((abs(a[1] - b[1]) + 2 * m) * ppm)) + 1
        box = shapely.box(x0, y0, x0 + nx / ppm, y0 + ny / ppm)
        later = np.zeros((ny, nx), np.uint8)
        earlier = np.zeros((ny, nx), np.uint8)
        own = np.zeros((ny, nx), np.uint8)
        for j in tree.query(box):
            kk = idx[j]
            pts = np.round((np.asarray(lines[kk].coords) - (x0, y0)) * ppm).astype(np.int32)
            if kk >= k:
                cv2.polylines(later, [pts], False, 1, lw)
            else:
                cv2.polylines(own if seq[kk][0] == bi else earlier, [pts], False, 1, lw)
        mask = cv2.erode(later, kern)
        ia = (int(round((a[1] - y0) * ppm)), int(round((a[0] - x0) * ppm)))
        ib = (int(round((b[1] - y0) * ppm)), int(round((b[0] - x0) * ppm)))
        for (yy, xx) in (ia, ib):
            cv2.circle(mask, (xx, yy), int(machine.COVERAGE_THREAD_W_MM * ppm), 1, -1)
        costs, _ = MCP_Geometric(np.where(mask > 0, 1.0, np.inf)).find_costs([ia], [ib])
        if np.isfinite(costs[ib]):
            L = costs[ib] / ppm
            row["route_mm"] = round(L, 1)
            row["route_ratio"] = round(L / max(gap, 1e-6), 2)
            if gap > machine.LINK_MAX_GAP_MM:
                row["cls"] = "gap_cap"
            elif L > _link_budget_mm(gap):
                row["cls"] = "budget"
            else:
                row["cls"] = "in_budget"
            rows.append(row)
            continue
        row["cls"] = "no_route"
        off = 200.0
        mcp = MCP_Geometric(np.where(mask > 0, 1.0, off))
        mcp.find_costs([ia], [ib])
        path = np.array(mcp.traceback(ib))
        outside = mask[path[:, 0], path[:, 1]] == 0
        on_own = own[path[:, 0], path[:, 1]] > 0
        on_earlier = (earlier[path[:, 0], path[:, 1]] > 0) & ~on_own
        step = np.r_[0.0, np.hypot(*np.diff(path, axis=0).T)] / ppm
        row["off_mm"] = round(float(step[outside].sum()), 2)
        row["off_on_own_mm"] = round(float(step[outside & on_own].sum()), 2)
        row["off_on_earlier_mm"] = round(float(step[outside & on_earlier].sum()), 2)
        row["off_bare_mm"] = round(row["off_mm"] - row["off_on_own_mm"] - row["off_on_earlier_mm"], 2)
        row["route_mm"] = round(float(step.sum()), 1)
        rows.append(row)
    return rows


def _q(xs, q):
    if not xs:
        return 0.0
    i = q * (len(xs) - 1)
    lo = int(math.floor(i))
    hi = min(len(xs) - 1, lo + 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.between_walks",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--steps", action="store_true", help="print every step")
    ap.add_argument("--json", type=Path, help="write every file's steps here")
    args = ap.parse_args(argv)
    out = []
    for fp in args.files:
        r = read_steps(fp)
        out.append(r)
        print(json.dumps(summary(r)))
        if args.steps:
            for s in r["steps"]:
                print("  ", json.dumps(s))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
