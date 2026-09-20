"""The lettering census and every lettering flip, on the FILE and on the raster
the Studio actually uploads — committed so the numbers in scope-history
2026-09-20 keep their definition (DOCTRINE 2026-09-11: a throwaway probe's
numbers expire with the probe).

`DigitizePanel` re-encodes every upload through a 1,200-px canvas before the
service sees a pixel (DOCTRINE 2026-09-19/20: the cap, premultiplied alpha
rewriting the RGB under transparency that stage 1 reads, Chrome's default
"low" smoothing). `tools/studio-raster.mjs` at the repo root writes that
raster into `digitizer/.cache/studio-raster/<stem>.studio.png` (and
`<stem>.studio-high.png` with `--smoothing high`); this tool reads them.

    node ../tools/studio-raster.mjs <every case file>          # once, from digitizer/
    node ../tools/studio-raster.mjs --smoothing high <files>   # for the studio_high rasters
    .venv/bin/python -m tools.studio_raster_census run --out census.json
    .venv/bin/python -m tools.studio_raster_census tables census.json

Rasters: `native` (the file), `studio` (the panel's PNG), `area` (cv2
INTER_AREA at the Studio's exact size — the Python-only stand-in candidate,
measured NOT to be one), `native_bleed` / `studio_bleed` (every non-opaque
pixel given the RGB of its nearest opaque pixel — the cure for the
under-alpha rewrite), `studio_high` / `studio_high_bleed` (the candidate
Studio fix), `native_black` (the file with RGB zeroed under alpha == 0 — the
hostile exporter, what a canvas does minus its partial-alpha noise). Arms:
today's defaults, then each lettering flip OFF against them (plus
`fill_bridge_cut`, whose trade was read on the file too), and `extend` —
stage 1's `alpha_edge_extend` ON. One `build_generation` per raster; a
stage-6/7 arm finishes from a fork, which is identical to a fresh build for
those flags (checked 2026-09-20 on three of them); the stage-1 arm rebuilds. Per row: stitches, trims, lettering trims by cause (the
2026-09-19 census's rule, with `_graph_travel` spied for refusals), exposed
travel (`travel_cover`), uncovered area, coverage_max, grade, findings.
Rows append to the JSON as they land, and a rerun skips rows already there.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent            # digitizer/
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import stage6_satin as s6  # noqa: E402
from digitizer_core import textcluster as tc  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402
from digitizer_core.preflight import run_preflight  # noqa: E402
from digitizer_core.stage1_prep import extend_opaque_colour  # noqa: E402
from tools.thin_strokes import corpus_cases  # noqa: E402
from tools.travel_cover import travel_exposure  # noqa: E402

CACHE = ROOT / ".cache" / "studio-raster"
RENDERS = REPO / "docs" / "renders"
FIXTURES = [
    ("marine80", RENDERS / "lettering-route-2026-09-19" / "marine_80mm_traced_input.png", 80.2, "left_chest"),
    ("marine127", RENDERS / "lettering-split-2026-09-19" / "marine_127mm_traced_input.png", 127.4, "left_chest"),
    ("becker100", ROOT / "testdata" / "becker_marine_logo.png", 100.0, "left_chest"),
]
NINE = ["tires", "enthusiast", "fremont", "bridge", "golden_tee", "gaulke", "drone", "screenshot", "becker"]

# Each lettering flip OFF against today's defaults; the bridge cut rides along.
ARMS: dict[str, dict] = {
    "default": {},
    "house_line": {"satin_house_from_line": False},
    "anchor": {"satin_house_anchor": False},
    "euler": {"satin_stroke_order": "nearest"},
    "twigs": {"satin_corner_twigs": False},
    "split": {"satin_lettering_split": False},
    "stack": {"satin_junction_stack": False},
    "cap_skip": {"edge_cap_skip_lettering": False},
    "exit": {"satin_exit_toward_next": False},
    "bridge_cut": {"fill_bridge_cut": False},
    # Stage 1's alpha edge extension (built OFF 2026-09-20): ON against the
    # defaults. A stage-1 flag changes the generation, so this arm rebuilds.
    "extend": {"alpha_edge_extend": True},
}
PREFIX_ARMS = {"extend"}
RASTERS = ["native", "studio", "area", "native_bleed", "studio_bleed", "studio_high", "studio_high_bleed", "native_black"]
# The per-flag arms run on the file and the panel's raster; the candidate-fix
# rasters carry the defaults (and, for `native_black`, the extend arm).
FULL_ARM_RASTERS = {"native", "studio"}


def cases() -> list[tuple[str, Path, float, str]]:
    return [(n, Path(p), float(w), g) for n, p, w, g in corpus_cases()] + FIXTURES


def studio_path(path: Path, smoothing: str | None = None) -> Path:
    return CACHE / f"{path.stem}.studio{'-' + smoothing if smoothing else ''}.png"


def bleed(img: np.ndarray) -> np.ndarray | None:
    """The naive whole-image fill (§E's "bleed"): every non-opaque pixel takes
    the RGB of its NEAREST opaque pixel — `stage1_prep.extend_opaque_colour`,
    applied to the file itself so bg_edge_rgb and the enclosed holes read it
    too (which is what broke Fremont). None when there is nothing to do (no
    alpha, no partial alpha, or nothing opaque) — the identity, not a copy."""
    if img.ndim != 3 or img.shape[2] != 4:
        return None
    a = img[..., 3]
    opaque = a >= 255
    if opaque.all() or not opaque.any():
        return None
    out = img.copy()
    out[..., :3] = extend_opaque_colour(img[..., :3], a)
    return out


def black_under_alpha(img: np.ndarray) -> np.ndarray | None:
    """The hostile exporter: RGB zeroed wherever alpha == 0 (what a browser
    canvas does to every fully transparent pixel, minus its partial-alpha
    noise). None for an image with no fully transparent pixel."""
    if img.ndim != 3 or img.shape[2] != 4 or not (img[..., 3] == 0).any():
        return None
    out = img.copy()
    out[img[..., 3] == 0, :3] = 0
    return out


def area_raster(path: Path, out_dir: Path) -> Path | None:
    """cv2 INTER_AREA at exactly the Studio's (w, h); None when the Studio
    does not resize this file."""
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    st = cv2.imread(str(studio_path(path)), cv2.IMREAD_UNCHANGED)
    if st is None or im.shape[:2] == st.shape[:2]:
        return None
    out = out_dir / f"{path.stem}.area.png"
    if not out.exists():
        cv2.imwrite(str(out), cv2.resize(im, (st.shape[1], st.shape[0]), interpolation=cv2.INTER_AREA))
    return out


def raster_file(name: str, path: Path, out_dir: Path) -> Path | None:
    """The file to build from for a raster name, written under out_dir when it
    is derived; None when the raster is the identity for this case."""
    if name == "native":
        return path
    if name == "studio":
        return studio_path(path)
    if name == "area":
        return area_raster(path, out_dir)
    src = path if name in ("native_bleed", "native_black") else studio_path(path, "high" if name.startswith("studio_high") else None)
    if not src.exists():
        return None
    raw = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
    if name == "studio_high":
        st = cv2.imread(str(studio_path(path)), cv2.IMREAD_UNCHANGED)
        if st is not None and raw.shape[:2] == st.shape[:2] and np.array_equal(raw, st):
            return None      # not resized: the smoothing setting cannot matter
        return src
    img = black_under_alpha(raw) if name == "native_black" else bleed(raw)
    if img is None:
        return None          # no real transparency: the bleed is the identity
    out = out_dir / f"{path.stem}.{name}.png"
    cv2.imwrite(str(out), img)
    return out


class _Spy:
    """Wraps `_graph_travel` to record (cursor, target, refused) per call."""

    def __init__(self) -> None:
        self.log: list[tuple[tuple, tuple, bool]] = []
        self.orig = s6._graph_travel

    def __enter__(self) -> "_Spy":
        def spy(cur, target, sewn, allow, nodes, edges, adj, *, trim_at_mm, **kw):
            path = self.orig(cur, target, sewn, allow, nodes, edges, adj, trim_at_mm=trim_at_mm, **kw)
            self.log.append((tuple(cur), tuple(target), path is None))
            return path
        s6._graph_travel = spy
        return self

    def __exit__(self, *exc) -> None:
        s6._graph_travel = self.orig


def measure(gen, rpath: Path, cfg: PipelineConfig) -> dict:
    with _Spy() as spy:
        result = finish_generation(gen.fork(), cfg)
        plan = plan_stitches(result, cfg)
    pf = run_preflight(result, plan, cfg, image=str(rpath))
    letters = {r.shape_id for g in tc._lettering_groups(result.regions) for r in g}
    runs = [(b, run) for b, run in plan.iter_runs()]
    by: collections.Counter = collections.Counter()
    for i, (b, cur) in enumerate(runs):
        if not getattr(cur, "trim", False) or cur.shape_id not in letters:
            continue
        prev = runs[i - 1][1] if i else None
        same = prev is not None and prev.shape_id == cur.shape_id
        asked = [l for l in spy.log
                 if math.dist(l[1], cur.points[0]) < 0.6 and prev is not None and math.dist(l[0], prev.points[-1]) < 0.6]
        why = ("first" if prev is None else
               "colour" if b.thread_index != runs[i - 1][0].thread_index else
               "letter-to-shape" if not same else
               "walk-refused" if asked and asked[-1][2] else f"{prev.kind}->{cur.kind}")
        by[why] += 1
    tx = travel_exposure(plan)
    return dict(stitches=plan.stats.stitch_count, trims=plan.stats.trims, letters=len(letters),
                regions=len(result.regions), klass=gen.classification_class,
                letter_trims=sum(by.values()), by=dict(by), exposed_mm=round(tx["exposed_mm"], 1),
                uncovered=pf["metrics"].get("uncovered_total_mm2"), coverage_max=pf["metrics"].get("coverage_max"),
                grade=pf.get("grade"), findings=sorted({f["code"] for f in pf["findings"]}))


def run(args: argparse.Namespace) -> None:
    out_path = Path(args.out)
    rows = json.loads(out_path.read_text()) if out_path.exists() else []
    done = {(r["case"], r["raster"], r["arm"]) for r in rows}
    derived = out_path.resolve().parent / "studio-raster-census-rasters"
    derived.mkdir(parents=True, exist_ok=True)
    only = set(args.cases or [])
    t0 = time.time()
    for name, path, width, garment in cases():
        if only and name not in only:
            continue
        for raster in args.rasters:
            rpath = raster_file(raster, path, derived)
            if rpath is None or not rpath.exists():
                continue
            arms = ARMS if raster in FULL_ARM_RASTERS else {a: ARMS[a] for a in ("default", *PREFIX_ARMS)}
            todo = [a for a in arms if a in args.arms and (name, raster, a) not in done]
            if not todo:
                continue
            im = cv2.imread(str(rpath), cv2.IMREAD_UNCHANGED)
            h, w = im.shape[:2]
            gen = build_generation(str(rpath), PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6))
            for arm in todo:
                cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6, **arms[arm])
                # A stage-6/7 arm finishes from the shared generation; a
                # stage-1 arm has to build its own.
                g = build_generation(str(rpath), cfg) if arm in PREFIX_ARMS else gen
                row = dict(case=name, raster=raster, arm=arm, px=f"{w}x{h}", px_per_mm=round(w / width, 2),
                           **measure(g, rpath, cfg))
                rows.append(row)
                print(f"[{(time.time() - t0) / 60:5.1f} min] {json.dumps(row)}", flush=True)
                out_path.write_text(json.dumps(rows, indent=1))
    print("done", flush=True)


def tables(rows: list[dict]) -> str:
    """The scope-history 2026-09-20 tables: defaults per raster, each flag
    OFF -> ON on the file and the Studio, sign agreement, the fixtures."""
    R = {(r["case"], r["raster"], r["arm"]): r for r in rows}
    order = NINE + [f[0] for f in FIXTURES]
    flags = [a for a in ARMS if a != "default"]

    def g(c, ras, arm="default"):
        return R.get((c, ras, arm))

    def by(r):
        return ", ".join(f"{k} {v}" for k, v in sorted(r["by"].items())) or "—"

    out = ["## A. Today's defaults per raster", "",
           "| case | raster | px | px/mm | stitches | trims | lettering trims by cause | exposed mm | uncovered | grade | findings |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in order:
        for ras in RASTERS:
            r = g(c, ras)
            if r:
                out.append(f"| {c} | {ras} | {r['px']} | {r['px_per_mm']} | {r['stitches']:,} | {r['trims']} | {by(r)} | "
                           f"{r['exposed_mm']} | {r['uncovered']} | {r['grade']} | {', '.join(r['findings']) or '—'} |")
    tot: collections.Counter = collections.Counter()
    for ras in RASTERS:
        rs = [g(c, ras) or g(c, "studio" if ras.startswith("studio") else "native") for c in NINE]
        if all(rs):
            tot[ras] = (sum(r["stitches"] for r in rs), sum(r["trims"] for r in rs))
    out += ["", "Nine logos (a case without that raster counts its base raster): " +
            "; ".join(f"{ras} {st:,} stitches / {tr} trims" for ras, (st, tr) in tot.items()), "",
            "## B. Each flip OFF -> today's default, file / Studio (nine logos)", "",
            "| flag | trims OFF -> ON: file / Studio | stitches OFF -> ON: file / Studio | per-logo trim delta (ON - OFF) file / Studio |",
            "|---|---|---|---|"]
    agree: collections.Counter = collections.Counter()
    for f in flags:
        parts, sums = [], collections.Counter()
        for c in NINE:
            nd, no, sd, so = g(c, "native"), g(c, "native", f), g(c, "studio"), g(c, "studio", f)
            if not (nd and no and sd and so):
                parts.append(f"{c} ?")
                continue
            dn, ds = nd["trims"] - no["trims"], sd["trims"] - so["trims"]
            for k, r in (("n_off", no), ("n_on", nd), ("s_off", so), ("s_on", sd)):
                sums[k] += r["trims"]
                sums[k + "_st"] += r["stitches"]
            parts.append(f"{c} {dn:+d}/{ds:+d}")
            key = ("same" if dn == 0 and ds == 0 else "agree" if dn * ds > 0
                   else "one zero" if dn == 0 or ds == 0 else "OPPOSITE")
            agree[(f, key)] += 1
        out.append(f"| {f} | {sums['n_off']} -> {sums['n_on']} / {sums['s_off']} -> {sums['s_on']} | "
                   f"{sums['n_off_st']:,} -> {sums['n_on_st']:,} / {sums['s_off_st']:,} -> {sums['s_on_st']:,} | {'; '.join(parts)} |")
    out += ["", "## C. Sign agreement of the per-logo trim deltas, file vs Studio", ""]
    for f in flags:
        out.append(f"- {f}: " + ", ".join(f"{k} {agree[(f, k)]}" for k in ("agree", "same", "one zero", "OPPOSITE") if agree[(f, k)]))
    out += ["", "## D. The fixtures, arm by arm (file — Studio)", ""]
    for c, *_ in FIXTURES:
        for f in ARMS:
            n, s = g(c, "native", f), g(c, "studio", f)
            if n and s:
                out.append(f"- {c} {f}: file {n['stitches']:,} / {n['trims']} ({by(n)}) — Studio {s['stitches']:,} / {s['trims']} ({by(s)})")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="studio_raster_census", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="measure; rows append to --out as they land")
    r.add_argument("--out", default="studio_raster_census.json")
    r.add_argument("--cases", nargs="*", help="case names (default: all)")
    r.add_argument("--rasters", nargs="*", default=RASTERS, choices=RASTERS)
    r.add_argument("--arms", nargs="*", default=list(ARMS), choices=list(ARMS))
    t = sub.add_parser("tables", help="markdown tables from a census JSON")
    t.add_argument("json")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        run(args)
    else:
        print(tables(json.loads(Path(args.json).read_text())))


if __name__ == "__main__":
    main()
