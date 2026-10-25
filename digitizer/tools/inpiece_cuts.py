"""inpiece_cuts: WHY a file cuts inside one sewn piece, ours beside the pro's.

    python -m tools.inpiece_cuts SLUG [SLUG ...] [--set k=v ...] [--extra k=v ...]
    python -m tools.inpiece_cuts --pro FILE.DST [FILE.DST ...]

Built 2026-10-25 for W4-01. `tools/sequence_pro.py` (#1072) counts the cuts
inside one piece -- a TRIM between two penetrations of the same connected
footprint, every needle-down segment one thread wide -- and found 84 ours
against 25 his over five hats. This reads WHERE each of those cuts comes
from, with the same piece rule (`sequence_pro.pieces`, the same crumbs and
visits), so its totals are `sequence_pro`'s `trims - inter_trims`.

OURS: every DST command is attributed to the plan run that emitted it
(`stitches.iter_machine_commands`, re-walked with the run alongside), and
each cut inside a piece is classed by the runs either side of it, an
underlay or travel run standing for the top stitching of its own shape:

- `fill_section`: one shape, fill on both sides -- the travel between two
  sections of one fill (or two of its underlay passes);
- `satin_split`: one shape, satin on both sides -- a split satin restarting,
  usually stroke to stroke with its underlay first; `satin_fill_section`
  when one side is satin and the other fill of the same shape;
- `edge_cap`: either side is the `__edge_cap__` run tier;
- `shape_to_shape`: two different shapes whose thread touches;
- `same_shape_other`: anything else inside one shape.

THE PRO: his DST carries no shapes, so each cut is read by the stitch
character of the twelve penetrations either side (`character`): satin
(consecutive steps reverse direction), fill (long parallel steps), run
(steady 1.2-3.2 mm steps), else `?` (tiny satin reads here: 0.5-0.9 mm
steps with direction flips under 0.6 of the time).

Reads; judges nothing. Ours via `tools.pro_pair.digitize` at the pro's
width, garment and Studio request (`tools.flip_sheet_renders.fixture_files`).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from tools import sequence_pro as sp  # noqa: E402

CAUSES = ("fill_section", "satin_split", "satin_fill_section", "edge_cap",
          "shape_to_shape", "same_shape_other")


def _visits_inside(mv, ids) -> set[int]:
    """Indices j of `mv` whose TRIM lies BETWEEN two pieces (sequence_pro's
    `inter_trims`); every other trim is inside one piece."""
    visits = []
    for i, pid in enumerate(ids):
        if pid == 0:
            continue
        if visits and visits[-1]["pid"] == pid:
            visits[-1]["last"] = i
            visits[-1]["n"] += 1
        else:
            visits.append({"pid": pid, "first": i, "last": i, "n": 1})
    counts = Counter()
    for v in visits:
        counts[v["pid"]] += v["n"]
    keep = {p for p, n in counts.items() if n >= sp.MIN_PIECE_PTS}
    merged = []
    for v in (v for v in visits if v["pid"] in keep):
        if merged and merged[-1]["pid"] == v["pid"]:
            merged[-1]["last"] = v["last"]
            merged[-1]["n"] += v["n"]
        else:
            merged.append(dict(v))
    inter = set()
    for va, vb in zip(merged, merged[1:]):
        if va["pid"] == vb["pid"]:
            continue
        for j in range(va["last"] + 1, vb["first"] + 1):
            if mv[j]["up"] and mv[j]["trim"]:
                inter.add(j)
    return inter


# --------------------------------------------------------------------- ours --

def attributed(plan):
    """-> per colour block, [(x, y, cmd, (block, run))] in DST units (0.1 mm
    rounding, as the file stores it): `stitches.iter_machine_commands`'
    stream with the run each command came from."""
    import pystitch
    from digitizer_core.stitches import SAME_POINT_MM
    out = []
    started = False
    for bi, block in enumerate(plan.blocks):
        cur, last = [], None
        for ri, run in enumerate(block.runs):
            if not run.points:
                continue
            if run.trim:
                cur.append((0.0, 0.0, pystitch.TRIM, (bi, ri)))
                last = None
            if run.jump and started:
                cur.append((*run.points[0], pystitch.JUMP, (bi, ri)))
                last = None
            for p in run.points:
                if last is not None and math.dist(last, p) < SAME_POINT_MM:
                    continue
                cur.append((round(p[0] * 10) / 10, round(p[1] * 10) / 10, pystitch.STITCH, (bi, ri)))
                last = p
                started = True
            last = run.points[-1]
        out.append(cur)
    return out


def _top(runs, i) -> str:
    """What run i belongs to: its own kind, or for underlay/travel the next
    top-stitching run of the same shape (else the previous one)."""
    k = runs[i].kind
    if k not in ("underlay", "travel"):
        return k
    sid = runs[i].shape_id
    for r in (*runs[i + 1:], *reversed(runs[:i])):
        if r.shape_id != sid:
            continue
        if r.kind not in ("underlay", "travel"):
            return r.kind
    return k


def classify_plan(plan) -> list[dict]:
    """Every cut inside one piece of our plan, with its cause."""
    import pystitch
    blocks = attributed(plan)
    pts = [(x, y) for b in blocks for x, y, c, _a in b if c == pystitch.STITCH]
    ext = (min(p[0] for p in pts), min(p[1] for p in pts),
           max(p[0] for p in pts), max(p[1] for p in pts))
    rows = []
    for blk in blocks:
        mv, att = [], []
        up = True
        trim = False
        for x, y, c, a in blk:
            if c == pystitch.STITCH:
                mv.append({"p": (x, y), "up": up, "trim": trim})
                att.append(a)
                up = trim = False
            elif c == pystitch.JUMP:
                up = True
            elif c == pystitch.TRIM:
                up = trim = True
        if not mv:
            continue
        _lab, ids, _o = sp.pieces(mv, ext)
        inter = _visits_inside(mv, ids)
        for j in range(1, len(mv)):
            if not mv[j]["trim"] or j in inter:
                continue
            (b0, r0), (b1, r1) = att[j - 1], att[j]
            runs_a, runs_b = plan.blocks[b0].runs, plan.blocks[b1].runs
            ra, rb = runs_a[r0], runs_b[r1]
            if "__edge_cap__" in (ra.shape_id, rb.shape_id):
                cause = "edge_cap"
            elif ra.shape_id != rb.shape_id:
                cause = "shape_to_shape"
            else:
                ea, eb = _top(runs_a, r0), _top(runs_b, r1)
                if ea == eb == "fill":
                    cause = "fill_section"
                elif ea in ("satin", "fill") and eb in ("satin", "fill"):
                    cause = "satin_split" if ea == eb else "satin_fill_section"
                else:
                    cause = "same_shape_other"
            rows.append({"cause": cause, "shape": ra.shape_id,
                         "kinds": f"{ra.kind}>{rb.kind}",
                         "gap_mm": round(math.dist(mv[j - 1]["p"], mv[j]["p"]), 2)})
    return rows


# ---------------------------------------------------------------------- pro --

def character(mv, j0: int, j1: int) -> str:
    """Stitch character of the needle-down steps among `mv[j0:j1]`."""
    segs = []
    for a, b in zip(mv[j0:j1], mv[j0 + 1:j1]):
        if b["up"]:
            break
        segs.append((b["p"][0] - a["p"][0], b["p"][1] - a["p"][1]))
    if len(segs) < 3:
        return "short"
    lengths = sorted(math.hypot(*s) for s in segs)
    med = lengths[len(lengths) // 2]
    flips = 0
    for s, t in zip(segs, segs[1:]):
        ls, lt = math.hypot(*s), math.hypot(*t)
        if ls > 1e-6 and lt > 1e-6 and (s[0] * t[0] + s[1] * t[1]) / (ls * lt) < -0.7:
            flips += 1
    fr = flips / max(1, len(segs) - 1)
    if fr > 0.6:
        return "satin"
    if med > 2.8 and fr < 0.3:
        return "fill"
    if 1.2 <= med <= 3.2 and fr < 0.2:
        return "run"
    return "?"


def classify_dst(path) -> list[dict]:
    """Every cut inside one piece of a machine file, by stitch character."""
    f = sp.read(path)
    rows = []
    for blk in f["blocks"]:
        mv = sp.moves(blk)
        _lab, ids, _o = sp.pieces(mv, f["extents"])
        inter = _visits_inside(mv, ids)
        for j in range(1, len(mv)):
            if mv[j]["trim"] and j not in inter:
                rows.append({"before": character(mv, max(0, j - 12), j),
                             "after": character(mv, j, min(len(mv), j + 12)),
                             "gap_mm": round(math.dist(mv[j - 1]["p"], mv[j]["p"]), 1)})
    return rows


def _kv(items):
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        out[k] = json.loads(v)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.inpiece_cuts",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--pro", nargs="*", default=[], help="machine files to read on their own")
    ap.add_argument("--set", action="append", help="cfg field=json for our arm")
    ap.add_argument("--extra", action="append", help="cfg.extra key=json for our arm")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    out = {}
    for fp in args.pro:
        rows = classify_dst(fp)
        out[Path(fp).name] = rows
        print(Path(fp).name, len(rows), dict(Counter(f"{r['before']}>{r['after']}" for r in rows)))
    if args.slugs:
        import dataclasses
        from tools import flip_sheet_renders as fsr
        from tools import pro_pair as pp
        sets, extra = _kv(args.set), _kv(args.extra)
        for slug in args.slugs:
            fx = fsr.fixture_files(slug)
            d = pp.digitize(fx["art"], fx["width_mm"], fx["garment"], sets)
            if extra:
                from digitizer_core.pipeline import plan_stitches
                cfg = dataclasses.replace(d.cfg, extra={**d.cfg.extra, **extra})
                plan = plan_stitches(d.result, cfg)
            else:
                plan = d.plan
            ours = classify_plan(plan)
            pro = classify_dst(fx["pro_dst"])
            out[slug] = {"ours": ours, "pro": pro}
            print(slug, "ours", len(ours), dict(Counter(r["cause"] for r in ours)),
                  "| pro", len(pro), dict(Counter(f"{r['before']}>{r['after']}" for r in pro)))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
