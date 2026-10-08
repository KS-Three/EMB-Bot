#!/usr/bin/env python
"""Where the envelope's reaches END: on unsewn ground, or on ground another
stroke of the same shape already sews.

The instrument behind `docs/renders/envelope-escapes-2026-09-30/` (Kent's
note on the envelope's sitting: Becker's lettering "looks like it is just
trying to fill a void"). `satin_rails_follow_edge="envelope"` extends a
rail where its own side's profile is short of the edge, and at a junction
that profile is not the stroke's edge at all: the far ray runs along the
meeting arm and hits the arm's end, for as long as the arm is thick. Over
nine logos 313 of 459 reached stations landed on another stroke's satin;
the rule that now refuses them (`stage6_satin._in_sibling_ribbon`) took
that to 46 of 157.

Two runs per design, `envelope` and `False`, both under a trace hook on
`_rail_points` that reads each call's station arrays at return (the
symmetric width, the per-side offsets, the placed rails) -- no engine
source is touched. Then, per shape, the symmetric arm's returned rails are
rasterized per stroke at 20 px/mm, and every station the envelope extends
is classed by where the extension lands:

- **escape** -- at least half of the extension lies on satin another
  stroke of the same shape sews under the symmetric rails;
- **genuine** -- it does not.

For each class the extension length, its ratio to the symmetric width and
the boundary distance at its end are reported, and the screen at the end
says how each candidate rule would have sorted them. The sibling test
here is the instrument's own copy (nearest-vertex distance against the
sibling's symmetric width at that vertex, +0.1 mm); the engine's reads
the width field's median along the sibling spine's interior plus the pull,
against the exact segment distance. They are not the same rule: the screen
predicted 89% of genuine reaches kept and 5% of escapes let through, and
the shipped rule's own census (this tool on the fixed tree) is what says
what it realized.

    .venv/bin/python tools/envelope_escapes.py [case ...] [--json out.json]

Cases: the `tools.thin_strokes.REAL_ART` names (becker, golden_tee, tires,
enthusiast, fremont, bridge, gaulke, drone, screenshot; thermal is drone's
byte-identical twin and a full run skips it), each at its own width and
garment, `max_colors=6`. Budget a minute or two per logo: the trace hook
costs little, two digitize() runs do not.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from shapely.geometry import Point  # noqa: E402

from digitizer_core import PipelineConfig, digitize, machine, stage6_satin  # noqa: E402
from tools.thin_strokes import REAL_ART, corpus_cases  # noqa: E402

PX = 20.0                       # raster scale for the symmetric satin, px per mm
OVERLAY_FRAC = 0.5              # an extension is an escape at or above this share on other strokes' satin
_KEYS = ("spine", "closed", "follow_edge", "width", "off_a", "off_b", "side_a", "side_b",
         "rail_a", "rail_b", "zs", "ze")


def capture(path: Path, cfg: PipelineConfig) -> tuple[list[dict], object]:
    """`digitize(path, cfg)` with a trace hook on `_rail_points`: -> (one
    record per call, in call order, with the station arrays at return; the
    PipelineResult)."""
    target = stage6_satin._rail_points.__code__
    caps: list[dict] = []

    def local_tracer(frame, event, arg):
        if event == "return":
            loc = frame.f_locals
            rec = {k: (list(loc[k]) if isinstance(loc.get(k), list) else loc.get(k)) for k in _KEYS if k in loc}
            rec["poly_bounds"] = tuple(loc["poly"].bounds)
            rec["ret"] = (list(arg[0]), list(arg[1])) if arg is not None else None
            caps.append(rec)
        return local_tracer

    def tracer(frame, event, arg):
        if frame.f_code is target:
            frame.f_trace_lines = False
            return local_tracer
        return None

    sys.settrace(tracer)
    try:
        result, _plan = digitize(path, cfg)
    finally:
        sys.settrace(None)
    return caps, result


def _body_mask(c: dict) -> list[bool]:
    n = len(c["spine"])
    zs, ze, closed = c.get("zs") or 0, c.get("ze") or 0, c["closed"]
    return [bool(closed or (0 < i < n - 1 and not (zs and i <= zs) and not (ze and i >= n - 1 - ze)))
            for i in range(n)]


def _ckey(c: dict) -> tuple:
    s = c["spine"]
    return (len(s), tuple(round(v, 3) for v in s[0]), tuple(round(v, 3) for v in s[-1]))


def census(name: str, path: Path, kw: dict) -> list[dict]:
    """-> one row per station the envelope extends, classed escape / genuine."""
    env_caps, result = capture(path, PipelineConfig(satin_rails_follow_edge="envelope", **kw))
    sym_caps, _ = capture(path, PipelineConfig(satin_rails_follow_edge=False, **kw))
    regions = {r.shape_id: r for r in result.regions}
    letters = {sid for sid, r in regions.items() if r.meta.get("text_candidate")}
    by_bounds = {tuple(round(v, 6) for v in r.polygon.bounds): sid for sid, r in regions.items()}
    symk = {_ckey(c): c for c in sym_caps}
    top = [c for c in env_caps if c["follow_edge"] == "envelope"]

    def shape_of(c: dict) -> str | None:
        key = tuple(round(v, 6) for v in c["poly_bounds"])
        if key in by_bounds:
            return by_bounds[key]
        mid = Point(c["spine"][len(c["spine"]) // 2])
        best = None
        for sid, r in regions.items():
            if r.polygon.buffer(0.3).covers(mid):
                d = r.polygon.boundary.distance(mid)
                if best is None or d > best[0]:
                    best = (d, sid)
        return best[1] if best else None

    caps_by_shape: dict[str, list[dict]] = {}
    for c in top:
        sid = shape_of(c)
        if sid is not None:
            caps_by_shape.setdefault(sid, []).append(c)

    rows: list[dict] = []
    tw = max(1, int(round(machine.COVERAGE_THREAD_W_MM * PX)))
    for sid, caps in caps_by_shape.items():
        poly = regions[sid].polygon
        b = poly.bounds
        ox, oy = b[0] - 2.0, b[1] - 2.0
        w, h = int((b[2] - b[0] + 4.0) * PX) + 1, int((b[3] - b[1] + 4.0) * PX) + 1

        def tp(p):
            return (int(round((p[0] - ox) * PX)), int(round((p[1] - oy) * PX)))

        # the symmetric arm's satin, one layer per stroke
        layers = []
        for c in caps:
            cs = symk.get(_ckey(c))
            lay = np.zeros((h, w), np.uint8)
            if cs is not None:
                for pa, pb in zip(*cs["ret"]):
                    if math.dist(pa, pb) >= machine.SATIN_MIN_CROSS_MM:
                        cv2.line(lay, tp(pa), tp(pb), 1, tw)
            layers.append(lay)
        bnd = poly.boundary
        for k, c in enumerate(caps):
            cs = symk.get(_ckey(c))
            if cs is None:
                continue
            others = np.zeros((h, w), np.uint8)
            for j, lay in enumerate(layers):
                if j != k:
                    others |= lay
            bm = _body_mask(c)
            width = c["width"]
            for side, off, rail_env, rail_sym in (("a", c["off_a"], c["rail_a"], cs["rail_a"]),
                                                  ("b", c["off_b"], c["rail_b"], cs["rail_b"])):
                for i in range(len(c["spine"])):
                    if not bm[i]:
                        continue
                    ext = off[i] - width[i]
                    if ext <= 1e-9:
                        continue
                    p0, p1 = rail_sym[i], rail_env[i]
                    ts = np.linspace(0.1, 1.0, 8)
                    hits = 0
                    for t in ts:
                        x, y = tp((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t))
                        if 0 <= y < h and 0 <= x < w and others[y, x]:
                            hits += 1
                    inrib = False
                    for j, oc in enumerate(caps):
                        if j == k:
                            continue
                        sp = np.asarray(oc["spine"])
                        d = np.hypot(sp[:, 0] - p1[0], sp[:, 1] - p1[1])
                        m = int(np.argmin(d))
                        if d[m] < oc["width"][m] + 0.1:
                            inrib = True
                            break
                    rows.append(dict(logo=name, shape=sid, letter=sid in letters, side=side, station=i,
                                     ext=round(float(ext), 3), width=round(float(width[i]), 3),
                                     ratio=round(float(off[i] / max(width[i], 1e-6)), 3),
                                     overlay=round(hits / len(ts), 2), escape=hits / len(ts) >= OVERLAY_FRAC,
                                     dt_end=round(float(bnd.distance(Point(p1))), 3), in_sibling_ribbon=inrib))
    return rows


def _q(arr) -> str:
    return f"p50 {np.median(arr):.2f} p90 {np.percentile(arr, 90):.2f} max {np.max(arr):.2f}" if len(arr) else "-"


def report(name: str, rows: list[dict]) -> None:
    esc = [r for r in rows if r["escape"]]
    gen = [r for r in rows if not r["escape"]]
    print(f"== {name}: reached stations {len(rows)} (on lettering {sum(1 for r in rows if r['letter'])}); "
          f"escapes {len(esc)}, genuine {len(gen)}")
    for lab, sel in (("escape", esc), ("genuine", gen)):
        if sel:
            print(f"   {lab:8}: ext {_q([r['ext'] for r in sel])} | off/width {_q([r['ratio'] for r in sel])} | "
                  f"boundary distance at the end {_q([r['dt_end'] for r in sel])} | "
                  f"end in a sibling ribbon {100 * np.mean([r['in_sibling_ribbon'] for r in sel]):.0f}%")


SCREEN = (
    ("extension <= 1.0 mm", lambda r: r["ext"] <= 1.0),
    ("extension <= 1.5 mm", lambda r: r["ext"] <= 1.5),
    ("offset / width <= 1.5", lambda r: r["ratio"] <= 1.5),
    ("offset / width <= 1.3", lambda r: r["ratio"] <= 1.3),
    ("boundary distance at the end <= 0.5", lambda r: r["dt_end"] <= 0.5),
    ("boundary distance at the end <= 1.0", lambda r: r["dt_end"] <= 1.0),
    ("end not in a sibling ribbon", lambda r: not r["in_sibling_ribbon"]),
)


def screen(rows: list[dict]) -> None:
    esc = [r for r in rows if r["escape"]]
    gen = [r for r in rows if not r["escape"]]
    print(f"\nALL: reached {len(rows)}, escapes {len(esc)}, genuine {len(gen)}")
    for lab, test in SCREEN:
        ke, kg = sum(1 for r in esc if test(r)), sum(1 for r in gen if test(r))
        print(f"  keep if {lab:38}: keeps {kg}/{len(gen)} genuine ({100 * kg / max(len(gen), 1):.0f}%), "
              f"lets through {ke}/{len(esc)} escapes ({100 * ke / max(len(esc), 1):.0f}%)")


def main(argv: list[str]) -> None:
    out = None
    if "--json" in argv:
        out = Path(argv[argv.index("--json") + 1])
        argv = [a for i, a in enumerate(argv) if a != "--json" and (i == 0 or argv[i - 1] != "--json")]
    # `corpus_cases` drops a name whose file is byte-identical to an earlier
    # one (thermal is drone), so a full run counts each design once.
    names = [a for a in argv if not a.startswith("--")] or [c[0] for c in corpus_cases(ROOT)]
    everything: list[dict] = []
    for name in names:
        rel, w, g = REAL_ART[name]
        rows = census(name, ROOT / "testdata" / rel, dict(target_width_mm=w, garment_id=g, max_colors=6))
        report(name, rows)
        everything.extend(rows)
    screen(everything)
    if out is not None:
        out.write_text(json.dumps(everything, indent=1), encoding="utf-8")
        print("wrote", out)


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    main(sys.argv[1:])
