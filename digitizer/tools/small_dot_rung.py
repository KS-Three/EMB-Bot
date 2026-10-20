#!/usr/bin/env python
"""The small-dot rung (`cfg.small_dot_rung`, built OFF 2026-10-14): what it
sews, and what it costs. MASTER_SCOPE "Waiting on Kent" 52 asks "lower the
floor or a dot rung"; this prices the rung. `machine.RUN_MIN_LOOP_MM` (2.2)
is not touched (ROADMAP gate 1).

Where the parts under the loop floor are lost, traced on origin/main:

- the 80 mm i dot (0.446 mm^2, 0.75 mm across) and the j dot never reach
  stage 7. Stage 3's cheap perimeter proxy, 2 x max(w, h) = 1.5 mm against
  2.2, drops them (the real ring is 2.49 mm, over the floor). So the rung is
  admission first: stage 3's proxy and stage 4's real-ring test go down to
  `machine.DOT_RUNG_MIN_LOOP_MM` (3 stations of `DOT_RUNG_STITCH_MM`), and the
  run tier sews an OUTER ring under 2.2 mm as a tack ring instead of skipping
  it. A part nine tenths ringed by other small regions is a small glyph's
  counter and is not admitted (the first cut admitted Fremont's 8 and 9
  counters as white runs);
- Fremont 81 mm Hat's 8: its 2.05 mm counter ring IS skipped by the run
  tier's loop floor, but sewing it SHUT that counter: 1895's glyph
  legibility 0.551 -> 0.426, the 8's open counters 1 of 2 -> 0 of 2. The
  counter the 8 loses on main is the OTHER one: a 0.413 mm^2 hole whose
  2.39 mm ring the 0.73 mm bean sews, centred on an edge 0.2 mm from the
  outline run. That is the outline bean on a stroke thinner than the thread
  (the skeleton lanes' ground), not this floor. So the rung never sews a
  hole ring, and Fremont's 1895 is left exactly as main sews it.

    python -m tools.small_dot_rung dots                  # synthetic i/j dots, OFF / ON / scope
    python -m tools.small_dot_rung fremont [--renders DIR] [--hole-ring]
    python -m tools.small_dot_rung census [--only NAME,NAME] [--arms off,on,scope] [--jsonl PATH]
    python -m tools.small_dot_rung render DIR            # i/j dot stitch paths, OFF / ON / scope
    python -m tools.small_dot_rung render-photo DIR [NAME]   # a photo's stitch path, the three arms

Three arms throughout: OFF (pre-flip), ON (`small_dot_rung`), and scope (shipped since 2026-10-20; the
rung with `small_dot_rung_lettering`, 2026-10-15: a part is admitted only
over a same-colour stem, which a photo speck does not have). Measured
2026-10-15: the scope keeps every synthetic i/j dot ON keeps (byte-identical
to ON at 60 and 80 mm) and is byte-identical to OFF on all 26 scorecard
fixtures, the five Studio-route logos and Fremont 81 mm Hat, where ON adds
+77 small parts to photo_sunset_backlit and +20 to photo_dof_meadow.

`--hole-ring` reproduces the measured negative: it sews sub-floor HOLE rings
too, through the same tack ring (a test seam, `_HOLE_RING`).
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

TESTDATA = ROOT / "testdata"
DOT_WIDTH_MM = 80.0
SMALL_DOT_WIDTH_MM = 60.0
WORD = "hijlij"
FIXTURE_PX_PER_MM = 28.125     # lowercase_aileron at 80 mm: the word is drawn to match
# The five real logos #902 read on the Studio route (80 mm, Hat).
LOGOS = ("becker_marine_logo.png", "photo/logo_bridge_bar.jpg", "photo/enthusiast_logo.png",
         "photo/logo_golden_tee.jpg", "photo/drone_render.png")


# The three arms: overrides on the shipped config.
# Every arm explicit: the rung and its scope are ON by default since
# 2026-10-20 (Kent's flip), so "off" pins the pre-flip engine and "on" is
# the unscoped rung.
ARMS = {"off": {"small_dot_rung": False, "small_dot_rung_lettering": False},
        "on": {"small_dot_rung": True, "small_dot_rung_lettering": False},
        "scope": {"small_dot_rung": True, "small_dot_rung_lettering": True}}


def arm(on) -> tuple[str, dict]:
    """(name, overrides) for an arm given as a name, or as a bool (OFF/ON)."""
    name = on if isinstance(on, str) else ("on" if on else "off")
    return name, ARMS[name]


def plan_md5(plan) -> str:
    """The stitch stream's md5, the recipe `test_small_glyph_keep.py` pins."""
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@contextlib.contextmanager
def count_dot_rings(hole_ring: bool = False):
    """Count the tack rings stage 7's run routing sews (its report's
    `dot_rings`). `hole_ring` swaps in a copy of the run tier that sews a
    sub-floor HOLE ring as well -- the measured negative, never the engine."""
    from digitizer_core import stage7_sequence as s7
    real = s7.run_outline
    box = {"dot_rings": 0}

    def spy(poly, shape_id, **kw):
        if hole_ring and kw.get("dot_rung"):
            runs, report = _hole_ring_outline(real, poly, shape_id, **kw)
        else:
            runs, report = real(poly, shape_id, **kw)
        box["dot_rings"] += int(report.get("dot_rings", 0))
        return runs, report
    s7.run_outline = spy
    try:
        yield box
    finally:
        s7.run_outline = real


def _hole_ring_outline(real, poly, shape_id, **kw):
    """`run_outline` with each sub-floor hole ring promoted to a part of its
    own (its ring sews as the rung's tack ring): what sewing the 8's small
    counter ring would lay, for the negative measurement only."""
    from shapely.geometry import Polygon
    from digitizer_core import machine
    from digitizer_core.stage6_border import _parts
    runs, report = real(poly, shape_id, **kw)
    if report["empty"]:
        return runs, report
    for part in _parts(poly):
        for hole in part.interiors:
            if machine.DOT_RUNG_MIN_LOOP_MM <= hole.length < machine.RUN_MIN_LOOP_MM:
                extra, rep = real(Polygon(hole), shape_id, **{**kw, "entry": runs[-1].points[-1]})
                if not rep["empty"]:
                    extra[0].jump = True
                    runs = runs + extra
                    report["dot_rings"] = report.get("dot_rings", 0) + rep.get("dot_rings", 0)
    return runs, report


def _sewn(plan) -> dict:
    out: dict = {}
    for _b, r in plan.iter_runs():
        d = out.setdefault(r.shape_id, {})
        d[r.kind] = d.get(r.kind, 0) + len(r.points)
    return out


def _codes(result, plan) -> dict:
    out: dict = {}
    for w in list(result.warnings or []) + list(plan.warnings or []):
        out[w.get("code")] = out.get(w.get("code"), 0) + 1
    return out


# --- the synthetic dots ---------------------------------------------------------

def dot_cases(tmp: Path):
    """(name, image, glyph meta, width mm): the fixture's i, and WORD drawn in
    the same CC0 face at the fixture's pixels per mm (it carries a j)."""
    from tools.lowercase_angle import FIXTURE
    from tools.stem_trace import word_image
    fx = json.loads(FIXTURE.with_suffix(".json").read_text(encoding="utf-8"))
    # At 60 mm the i dot's own ring is under 2.2 mm, so the tack ring sews it.
    cases = [("fixture", FIXTURE.with_suffix(".png"), fx, DOT_WIDTH_MM),
             ("fixture60", FIXTURE.with_suffix(".png"), fx, SMALL_DOT_WIDTH_MM)]
    meta = word_image(WORD, tmp / "small_dot_rung_word.png")
    xs = [g["box"][0] for g in meta["glyphs"]] + [g["box"][2] for g in meta["glyphs"]]
    cases.append((f"word {WORD}", tmp / "small_dot_rung_word.png", meta,
                  round((max(xs) - min(xs)) / FIXTURE_PX_PER_MM, 3)))
    # The same word at the fixture's 60 mm scale (its dots under 2.2 mm).
    cases.append((f"word60 {WORD}", tmp / "small_dot_rung_word.png", meta,
                  round((max(xs) - min(xs)) * SMALL_DOT_WIDTH_MM
                        / (FIXTURE_PX_PER_MM * DOT_WIDTH_MM), 3)))
    return cases


def dots(on: bool, tmp: Path) -> list[dict]:
    """Per case: every i/j dot region (centroid above the glyph's x-height
    band), what it sewed, and the design's stitch / trim / md5 / warnings."""
    from digitizer_core import PipelineConfig, digitize
    from tools.lowercase_angle import mm_to_px
    from tools.stem_trace import _glyph_at
    rows = []
    tag, over = arm(on)
    for name, path, meta, width in dot_cases(tmp):
        cfg = PipelineConfig(target_width_mm=width, forced_class="flat", **over)
        with count_dot_rings() as box:
            result, plan = digitize(path, cfg)
        to_px, _s = mm_to_px(result, meta["image"])
        sewn = _sewn(plan)
        found = []
        for r in result.regions:
            c = r.polygon.centroid
            px, py = to_px(c.x, c.y)
            g = _glyph_at(meta, px, py)
            if g is None or g["ch"] not in "ij":
                continue
            top = g["box"][1] + 0.3 * (g["box"][3] - g["box"][1])
            if py < top:
                found.append(dict(ch=g["ch"], shape=r.shape_id, area_mm2=round(r.polygon.area, 3),
                                  ring_mm=round(r.polygon.exterior.length, 3),
                                  sewn=sewn.get(r.shape_id, {})))
        n_dots = sum(1 for g in meta["glyphs"] if g["ch"] in "ij")
        codes = _codes(result, plan)
        rows.append(dict(case=name, width_mm=width, arm=tag, dots_in_art=n_dots, dots=found,
                         dots_sewn=sum(1 for d in found if d["sewn"]),
                         stitches=plan.stats.stitch_count, trims=plan.stats.trims,
                         shapes=len(result.regions),
                         md5=plan_md5(plan), dot_rings=box["dot_rings"],
                         shape_not_stitched=codes.get("SHAPE_NOT_STITCHED", 0),
                         dropped_small_shapes=codes.get("DROPPED_SMALL_SHAPES", 0)))
    return rows


# --- Fremont 81 mm Hat -------------------------------------------------------------

def fremont(on: bool, hole_ring: bool = False, renders: Path | None = None) -> dict:
    """Fremont 81 mm Hat on the Studio route (`fremont_triage.run_arm`):
    stitches, trims, md5, and the 1895 glyph legibility with the 8's
    counters (`tools/glyph_legibility.py`)."""
    from tools import fremont_triage as ft
    from tools import glyph_legibility as gl
    t = time.time()
    tag, over = arm(on)
    with count_dot_rings(hole_ring) as box:
        run = ft.run_arm("main", preflight=False, overrides=dict(over))
    plan = run["plan"]
    words, dbg, _reg = gl.read_case("fremont", run["design"], use_ocr=False, words=["1895"])
    w = next(x for x in words if x.name == "1895")
    # The glyphs read left to right: 1 8 9 5.
    eight = w.glyphs[1] if len(w.glyphs) == 4 else None
    if renders is not None:
        import cv2
        renders.mkdir(parents=True, exist_ok=True)
        tag = "on-hole-ring" if hole_ring else tag
        cv2.imwrite(str(renders / f"fremont81-1895-{tag}.png"),
                    gl.word_panel(w, dbg["1895"], f"1895 small_dot_rung {tag}"))
    return dict(arm=tag, hole_ring=hole_ring, stitches=plan.stats.stitch_count,
                trims=plan.stats.trims, shapes=len(run["result"].regions), md5=plan_md5(plan), dot_rings=box["dot_rings"],
                legibility_1895=w.summary()["legibility"],
                counters_1895=w.summary()["counters"],
                eight_counters=(None if eight is None else
                                dict(src=eight["src_counters"], sewn=eight["sewn_counters"])),
                secs=round(time.time() - t, 1))


# --- the census ------------------------------------------------------------------------

def _studio_plan(rel: str, width_mm: float, on):
    """A logo the way /digitize sees a Studio upload on a Hat (the request
    `fremont_triage.studio_request` writes, the fixture swapped)."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools.fremont_triage import studio_request
    data = (TESTDATA / rel).read_bytes()
    cfg = PipelineConfig(**{**_parse_config(json.dumps(studio_request(width_mm))),
                            **arm(on)[1]})
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    return result, plan_stitches(result, cfg)


def census_targets() -> list[tuple[str, str, str]]:
    """(name, route, fixture): the 26 scorecard fixtures at 80 mm left
    chest, then the five logos on the Studio route at 80 mm Hat."""
    from tools.corpus_scorecard import FIXTURES
    return ([(f, "lc80", f) for f in FIXTURES]
            + [(f"studio:{f}", "studio_hat80", f) for f in LOGOS])


def census_row(name: str, route: str, rel: str, arms_wanted=tuple(ARMS)) -> dict:
    from digitizer_core import PipelineConfig, digitize
    arms = {}
    for tag in ("off",) + tuple(a for a in arms_wanted if a != "off"):
        t = time.time()
        with count_dot_rings() as box:
            if route == "lc80":
                result, plan = digitize(TESTDATA / rel, PipelineConfig(
                    target_width_mm=80.0, garment_id="left_chest", **ARMS[tag]))
            else:
                result, plan = _studio_plan(rel, 80.0, tag)
        arms[tag] = dict(ids={r.shape_id for r in result.regions},
                         stitches=plan.stats.stitch_count, trims=plan.stats.trims,
                         md5=plan_md5(plan), dot_rings=box["dot_rings"],
                         secs=round(time.time() - t, 1))
    off = arms["off"]
    return dict(name=name, route=route,
                identical={t: a["md5"] == off["md5"] for t, a in arms.items() if t != "off"},
                arms=list(arms),
                stitches=[a["stitches"] for a in arms.values()],
                trims=[a["trims"] for a in arms.values()],
                shapes=[len(a["ids"]) for a in arms.values()],
                shapes_added={t: len(a["ids"] - off["ids"]) for t, a in arms.items() if t != "off"},
                shapes_removed={t: len(off["ids"] - a["ids"]) for t, a in arms.items() if t != "off"},
                dot_rings={t: a["dot_rings"] for t, a in arms.items()},
                md5={t: a["md5"] for t, a in arms.items()},
                secs=[a["secs"] for a in arms.values()])


# --- render -------------------------------------------------------------------------------

def _label_bar(width: int, label: str):
    import cv2
    import numpy as np
    bar = np.full((36, width, 3), 255, np.uint8)
    cv2.putText(bar, label, (6, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    return bar


def _stack(panes, axis: int = 0):
    """Panes padded white to a common size and joined with a grey rule."""
    import numpy as np
    if axis == 0:
        w = max(p.shape[1] for p in panes)
        panes = [np.pad(p, ((0, 0), (0, w - p.shape[1]), (0, 0)), constant_values=255) for p in panes]
        rule = np.full((6, w, 3), 200, np.uint8)
    else:
        h = max(p.shape[0] for p in panes)
        panes = [np.pad(p, ((0, h - p.shape[0]), (0, 0), (0, 0)), constant_values=255) for p in panes]
        rule = np.full((h, 6, 3), 200, np.uint8)
    out = [panes[0]]
    for p in panes[1:]:
        out += [rule, p]
    return np.concatenate(out, axis=axis)


ARM_LABEL = {"off": "OFF (pre-flip)", "on": "ON  small_dot_rung",
             "scope": "ON + small_dot_rung_lettering"}
INK = {"satin": (60, 60, 60), "underlay": (215, 160, 120), "travel": (120, 190, 120),
       "run": (40, 40, 200), "fill": (150, 150, 150)}


def render(out: Path, tmp: Path, ppm: float = 60.0) -> list[Path]:
    """OFF, ON, scope top to bottom: the stitch path round each i/j of the
    synthetic word (run red, satin dark, travel green, underlay blue) at
    `ppm` px per mm."""
    import cv2
    import numpy as np
    from digitizer_core import PipelineConfig, digitize
    from tools.lowercase_angle import mm_to_px
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, path, meta, width in dot_cases(tmp):
        panes = []
        for tag, over in ARMS.items():
            result, plan = digitize(path, PipelineConfig(target_width_mm=width, forced_class="flat",
                                                         **over))
            to_px, s = mm_to_px(result, meta["image"])
            cx, cy = to_px(0.0, 0.0)
            gl = [g for g in meta["glyphs"] if g["ch"] in "ij"]
            if name.startswith("fixture"):
                gl = [g for g in gl if g["line"] == 1]
            x0 = min((g["box"][0] - cx) / s for g in gl) - 0.8
            x1 = max((g["box"][2] - cx) / s for g in gl) + 0.8
            y0 = min((g["box"][1] - cy) / s for g in gl) - 1.6
            y1 = max((g["box"][3] - cy) / s for g in gl) + 0.6
            pane = np.full((int((y1 - y0) * ppm), int((x1 - x0) * ppm), 3), 255, np.uint8)

            def P(p):
                return (int(round((p[0] - x0) * ppm)), int(round((p[1] - y0) * ppm)))
            for kind in ("travel", "underlay", "run", "satin"):
                for _b, run in plan.iter_runs():
                    if run.kind == kind:
                        for a, b in zip(run.points[:-1], run.points[1:]):
                            cv2.line(pane, P(a), P(b), INK[kind], 1, cv2.LINE_AA)
            panes.append(np.vstack([_label_bar(pane.shape[1], f"{ARM_LABEL[tag]}  {name} {width:g} mm"),
                                    pane]))
        dest = out / f"dots-{name.split()[0]}-off-on-scope.png"
        cv2.imwrite(str(dest), _stack(panes))
        written.append(dest)
    return written


def render_photo(out: Path, rel: str, ppm: float = 10.0) -> Path:
    """A photo at 80 mm left chest, OFF / ON / scope side by side: the whole
    stitch path in grey, and every shape an arm sews that OFF does not drawn
    thick magenta -- the specks the rung admits, and what the scope leaves."""
    import cv2
    import numpy as np
    from digitizer_core import PipelineConfig, digitize
    out.mkdir(parents=True, exist_ok=True)
    plans = {}
    for tag, over in ARMS.items():
        result, plan = digitize(TESTDATA / rel, PipelineConfig(
            target_width_mm=80.0, garment_id="left_chest", **over))
        plans[tag] = (result, plan)
    pts = [p for _b, r in plans["off"][1].iter_runs() for p in r.points]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0 = min(xs) - 1.0, min(ys) - 1.0
    W, H = int((max(xs) + 1.0 - x0) * ppm), int((max(ys) + 1.0 - y0) * ppm)
    # New by GEOMETRY, not by id (an admitted part renumbers the shapes after
    # it), and small: the part the rung admits is under the detail floor;
    # the large shape it was cut out of changes outline too, and is not new.
    floor_mm2 = PipelineConfig().min_detail_mm ** 2

    def key(r):
        return (tuple(round(v, 2) for v in r.polygon.bounds), round(r.polygon.area, 3))
    off_keys = {key(r) for r in plans["off"][0].regions}

    def P(p):
        return (int(round((p[0] - x0) * ppm)), int(round((p[1] - y0) * ppm)))
    panes = []
    for tag, (result, plan) in plans.items():
        pane = np.full((H, W, 3), 255, np.uint8)
        new = {r.shape_id for r in result.regions
               if key(r) not in off_keys and r.polygon.area < floor_mm2}
        for _b, run in plan.iter_runs():
            if run.shape_id in new:
                continue
            for a, b in zip(run.points[:-1], run.points[1:]):
                cv2.line(pane, P(a), P(b), (190, 190, 190), 1, cv2.LINE_AA)
        for _b, run in plan.iter_runs():
            if run.shape_id in new and run.kind != "travel":
                for a, b in zip(run.points[:-1], run.points[1:]):
                    cv2.line(pane, P(a), P(b), (200, 0, 200), 2, cv2.LINE_AA)
        label = (f"{ARM_LABEL[tag]}: +{len(new)} small parts, "
                 f"{plan.stats.stitch_count} st, {plan.stats.trims} trims")
        panes.append(np.vstack([_label_bar(W, label), pane]))
    dest = out / f"{Path(rel).stem}-off-on-scope.png"
    cv2.imwrite(str(dest), _stack(panes, axis=1))
    return dest


def main(argv: list[str]) -> int:
    from tools._console import utf8_console
    utf8_console()
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if not argv:
        print(__doc__)
        return 2
    tmp = Path(__import__("tempfile").mkdtemp(prefix="small_dot_rung_"))
    cmd = argv[0]
    if cmd == "dots":
        for tag in ARMS:
            for row in dots(tag, tmp):
                print(json.dumps(row))
    elif cmd == "fremont":
        renders = Path(argv[argv.index("--renders") + 1]) if "--renders" in argv else None
        arms = ([(t, False) for t in ARMS]
                + ([("on", True)] if "--hole-ring" in argv else []))
        for on, hole in arms:
            print(json.dumps(fremont(on, hole, renders)))
    elif cmd == "census":
        only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
        jsonl = Path(argv[argv.index("--jsonl") + 1]) if "--jsonl" in argv else None
        wanted = tuple(argv[argv.index("--arms") + 1].split(",")) if "--arms" in argv else tuple(ARMS)
        for name, route, rel in census_targets():
            if only and not any(o in name for o in only):
                continue
            row = census_row(name, route, rel, wanted)
            print(json.dumps(row), flush=True)
            if jsonl is not None:
                with jsonl.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row) + "\n")
    elif cmd == "render":
        for p in render(Path(argv[1]), tmp):
            print("wrote", p)
    elif cmd == "render-photo":
        name = argv[2] if len(argv) > 2 else "photo/photo_sunset_backlit.png"
        print("wrote", render_photo(Path(argv[1]), name))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
