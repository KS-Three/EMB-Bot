#!/usr/bin/env python
"""Nightly regression tripwire over the pro pairs whose pro files are committed.

A PR can move any job's cuts, hops, needle-up mm or kappa the wrong way and go
green: the byte goldens pin frozen engines, and the push-to-main report jobs
compare nothing against a tolerance. This tool digitizes every COMMITTED pair
once at the pro's size (`tools.pro_baseline`: Studio request, one reader for
ours and the pro's DST), then compares each figure against a ledger that
names, per job and figure, the baseline measured on cloud Linux, the direction
that counts as worse, and a tolerance seeded from run-to-run noise (several
passes of the same tree on the runner, never a desk guess).

    python -m tools.tripwire measure --runs DIR --figures OUT.json [--only SLUG ...]
    python -m tools.tripwire capture --from PASS1.json [PASS2.json ...] --ledger PATH [--run-url URL]
    python -m tools.tripwire check --ledger PATH [--runs DIR] [--figures F.json] [--table OUT.md] [--json OUT.json]
    python -m tools.tripwire table --ledger PATH
    python -m tools.tripwire jobs

`measure` writes one pass: every figure for every committed job, plus the
environment it ran in. `capture` turns one or more passes of the SAME tree into
the ledger: baseline = the lower median across passes, spread = max - min,
tolerance = the spread rounded up to the figure's own resolution (0 when the
passes agree). `check` runs the pairs (or reads `--figures`, a pass written
earlier), prints a markdown table of the movers and exits 1 on any wrong-way
move past tolerance, on a figure the ledger has that the run lost, or on a
pro-side figure that moved (the READER changed, so nothing else can be read);
0 otherwise. A right-way move past tolerance is listed and exits 0.

Figures (ours, read from the written DST): stitches, trims (cuts), hops and
needle-up mm (more is worse), stitch-type kappa and direction kappa over the
shared solid area and word cc at native size (less is worse). CHANCE-CORRECTED
ONLY (ROADMAP gate 4): the raw agreement is never written or printed; the
kappa rides with its chance floor the way `pro_baseline` prints it.

The population is `pro_baseline.JOBS` filtered to the pairs whose art is under
`testdata/` and whose pro DST is in the repo: `testdata/reference/` or the
committed `Embroidery Files.zip` at the repo root (a known exposure, root
CLAUDE.md). Bridge (files outside the repo) and ProSeal (art not committed)
are out; nothing gitignored is added. On a machine without `scratch_kent/`
the needed members are extracted from the zip into `--kent-dir` (default
`RUNS/_kent`) and `EMB_SCRATCH_KENT` is pointed there.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import zipfile
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
REPO = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

SCHEMA = 1
LEDGER = DIGITIZER / "testdata" / "tripwire_ledger.json"
ZIP = REPO / "Embroidery Files.zip"
#: Folder names inside the zip that differ from the `kent:` paths the code
#: tables use (a macOS ':' that `scratch_kent/` carries as '-').
ZIP_RENAMES = {"To a T:Becker Beanies": "To a T-Becker Beanies"}
EPS = 1e-9

#: figure -> direction that counts as worse, the resolution a tolerance is
#: rounded up to, and the table label. Order is the table order.
FIGURES: dict[str, dict] = {
    "stitches": {"worse": "up", "res": 1, "label": "stitches"},
    "trims": {"worse": "up", "res": 1, "label": "trims (cuts)"},
    "hops": {"worse": "up", "res": 1, "label": "needle-up hops"},
    "needle_up_mm": {"worse": "up", "res": 0.1, "label": "needle-up mm"},
    "sttype_kappa": {"worse": "down", "res": 0.01, "label": "stitch-type kappa (chance)"},
    "direction_kappa": {"worse": "down", "res": 0.01, "label": "direction kappa"},
    "word_cc": {"worse": "down", "res": 0.01, "label": "word cc, native"},
}
#: figures the pro's file also yields; a move here is the reader, not the engine
PRO_SIDE = ("stitches", "trims", "hops", "needle_up_mm", "word_cc")
FORBIDDEN_KEYS = ("raw", "agreement")   # never in a ledger or a pass (gate 4)


# ------------------------------------------------------------------ population
def _zip_members() -> set[str]:
    if not ZIP.exists():
        return set()
    with zipfile.ZipFile(ZIP) as z:
        return {_renamed(n) for n in z.namelist() if not n.startswith("__MACOSX/")}


def _renamed(member: str) -> str:
    for old, new in ZIP_RENAMES.items():
        member = member.replace(old + "/", new + "/")
    return member


def _committed(spec: str, members: set[str]) -> bool:
    kind, _sep, rel = spec.partition(":")
    if kind == "testdata":
        return (DIGITIZER / "testdata" / rel).exists()
    if kind == "kent":
        return rel in members
    return False          # bridge:, path: -- outside the repo


def committed_jobs() -> list[str]:
    """Slugs of `pro_baseline.JOBS` whose art and pro DST are both in the repo."""
    from tools.pro_baseline import JOBS
    members = _zip_members()
    return [s for s, (_g, _w, art, pro_dst, *_rest) in JOBS.items()
            if _committed(art, members) and _committed(pro_dst, members)]


def needed_members(slugs: list[str]) -> list[str]:
    """`kent:` files the pairs and their word readings use, as zip members (renamed)."""
    from tools import word_legibility as wl
    from tools.pro_baseline import JOBS
    out = []
    for s in slugs:
        _g, _w, art, pro_dst, pes, wjob = JOBS[s]
        specs = [art, pro_dst, pes]
        if wjob and wjob in wl.JOBS:
            specs += [wl.JOBS[wjob]["art"], wl.JOBS[wjob]["pro"]]
        for spec in specs:
            if spec and spec.startswith("kent:"):
                rel = spec.partition(":")[2]
                if rel not in out:
                    out.append(rel)
    return out


def materialise(dest: Path, slugs: list[str]) -> Path | None:
    """Make every `kent:` file the pairs need resolvable. Kent's `scratch_kent/`
    (or `EMB_SCRATCH_KENT`) is used when it already holds them; otherwise the
    members are extracted from the committed zip into `dest` and
    `EMB_SCRATCH_KENT` is set to it. Returns the root in use, None when nothing
    `kent:` is needed."""
    from tools import word_legibility as wl
    need = needed_members(slugs)
    if not need:
        return None
    root = wl.kent_root()
    if root is not None and all((root / rel).exists() for rel in need):
        return root
    if not ZIP.exists():
        raise SystemExit(f"{ZIP.name} is not in this checkout and no scratch_kent/ holds the pro files")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as z:
        by_renamed = {_renamed(n): n for n in z.namelist() if not n.startswith("__MACOSX/")}
        for rel in need:
            member = by_renamed.get(rel)
            if member is None:
                raise SystemExit(f"{rel!r} is not in {ZIP.name}")
            target = dest / rel
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(member))
    os.environ["EMB_SCRATCH_KENT"] = str(dest)
    return dest


# ------------------------------------------------------------------ one pass
def environment() -> dict:
    import platform
    from tools.lane_census import engine_identity, tesseract_version
    try:
        import cv2
        cv2_version = cv2.__version__
    except Exception:                                      # noqa: BLE001 -- a stamp, not a gate
        cv2_version = None
    try:
        from importlib.metadata import version
        pystitch_version = version("pystitch")
    except Exception:                                      # noqa: BLE001
        pystitch_version = None
    return {"python": platform.python_version(), "platform": platform.platform(),
            "machine": platform.machine(), "opencv_ipp": os.environ.get("OPENCV_IPP"),
            "cv2": cv2_version, "pystitch": pystitch_version, "tesseract": tesseract_version(),
            "rembg_venv": (DIGITIZER / "rembg_isolated" / "venv").exists(),
            "engine": engine_identity(), "github_run": os.environ.get("GITHUB_RUN_ID")}


def _kappa_value(k: dict, key: str):
    v = k.get(key) if "error" not in k else None
    return None if v is None else round(float(v), 4)


def figures_from_baseline(res: dict, secs: dict | None = None) -> dict:
    """`pro_baseline.measure`'s result -> one pass: values[job][figure], the pro's
    side, each job's chance floor and word count, and the digitize seconds."""
    from tools.pro_baseline import word_figures
    values, pro, chance, words = {}, {}, {}, {}
    wf = word_figures(res)
    for s, r in res["jobs"].items():
        o, p, k = r["ours"], r["pro"], r.get("kappa", {})
        values[s] = {"stitches": o["stitches"], "trims": o["trims"], "hops": o["hops"],
                     "needle_up_mm": round(float(o["needle_up_mm"]), 1),
                     "sttype_kappa": _kappa_value(k, "sttype_kappa"),
                     "direction_kappa": _kappa_value(k, "direction_kappa")}
        pro[s] = {"stitches": p["stitches"], "trims": p["trims"], "hops": p["hops"],
                  "needle_up_mm": round(float(p["needle_up_mm"]), 1)}
        chance[s] = _kappa_value(k, "sttype_chance")
        w = wf.get(s)
        if w and w.get("ours") is not None:
            values[s]["word_cc"] = round(float(w["ours"]), 4)
            pro[s]["word_cc"] = None if w.get("pro") is None else round(float(w["pro"]), 4)
            words[s] = w.get("words")
        if "error" in k:
            values[s]["kappa_error"] = k["error"]
    return {"schema": SCHEMA, "values": values, "pro": pro, "chance": chance, "words": words,
            "secs": secs or {}}


def measure(runs: Path, slugs: list[str], with_words: bool, kent_dir: Path | None) -> dict:
    from tools import pro_baseline as pb
    runs.mkdir(parents=True, exist_ok=True)
    root = materialise(kent_dir or runs / "_kent", slugs)
    print(f"pro files: {root}", flush=True)
    secs = {}
    for s in slugs:
        t = time.time()
        pb.digitize(runs, [s])
        secs[s] = round(time.time() - t, 1)
        print(f"  {s}: digitized in {secs[s]} s", flush=True)
    res = pb.measure(runs, slugs, with_words)
    out = figures_from_baseline(res, secs)
    out["env"] = environment()
    out["jobs"] = slugs
    return out


# ------------------------------------------------------------------ the ledger
def _median_low(xs: list) -> float:
    xs = sorted(xs)
    return xs[(len(xs) - 1) // 2]


def _ceil_to(x: float, res: float) -> float:
    if x <= EPS:
        return 0 if res == 1 else 0.0
    n = math.ceil(x / res - EPS)
    return int(n) if res == 1 else round(n * res, 6)


def build_ledger(passes: list[dict], run_url: str | None = None) -> dict:
    """Passes of the SAME tree -> the ledger. Baseline = lower median, spread =
    max - min, tolerance = spread rounded up to the figure's resolution."""
    if not passes:
        raise ValueError("at least one pass")
    jobs = passes[0].get("jobs") or sorted(passes[0]["values"])
    rows = []
    for s in jobs:
        for fig, spec in FIGURES.items():
            vals = [p["values"].get(s, {}).get(fig) for p in passes]
            if any(v is None for v in vals):
                continue                            # not read in every pass: no row
            lo, hi = min(vals), max(vals)
            spread = round(hi - lo, 6)
            row = {"job": s, "figure": fig, "baseline": _median_low(vals), "worse": spec["worse"],
                   "tolerance": _ceil_to(spread, spec["res"]), "spread": spread}
            if fig in PRO_SIDE:
                row["pro"] = passes[0]["pro"].get(s, {}).get(fig)
            if fig == "sttype_kappa":
                row["chance"] = passes[0]["chance"].get(s)
            if fig == "word_cc":
                row["words"] = passes[0]["words"].get(s)
            rows.append(row)
    return {"schema": SCHEMA,
            "captured": {"date": time.strftime("%Y-%m-%d"), "passes": len(passes), "run_url": run_url,
                         "engine": (passes[0].get("env") or {}).get("engine")},
            "env": passes[0].get("env"),
            "figures": {f: {"worse": v["worse"], "res": v["res"]} for f, v in FIGURES.items()},
            "secs": {s: [p.get("secs", {}).get(s) for p in passes] for s in jobs},
            "rows": rows}


def validate_ledger(led: dict) -> list[str]:
    """Schema problems, [] when the ledger is well-formed."""
    bad = []
    if led.get("schema") != SCHEMA:
        bad.append(f"schema {led.get('schema')!r} != {SCHEMA}")
    rows = led.get("rows")
    if not isinstance(rows, list) or not rows:
        return bad + ["no rows"]
    seen = set()
    for i, r in enumerate(rows):
        for key in ("job", "figure", "baseline", "tolerance", "worse"):
            if key not in r:
                bad.append(f"row {i}: no {key}")
        if r.get("figure") not in FIGURES:
            bad.append(f"row {i}: unknown figure {r.get('figure')!r}")
        elif r.get("worse") != FIGURES[r["figure"]]["worse"]:
            bad.append(f"row {i}: {r['figure']} worse={r.get('worse')!r}, expected {FIGURES[r['figure']]['worse']!r}")
        if not isinstance(r.get("tolerance"), (int, float)) or r.get("tolerance", -1) < 0:
            bad.append(f"row {i}: tolerance {r.get('tolerance')!r}")
        if not isinstance(r.get("baseline"), (int, float)):
            bad.append(f"row {i}: baseline {r.get('baseline')!r}")
        if r.get("figure") == "sttype_kappa" and "chance" not in r:
            bad.append(f"row {i}: sttype_kappa without its chance floor")
        key = (r.get("job"), r.get("figure"))
        if key in seen:
            bad.append(f"row {i}: duplicate {key}")
        seen.add(key)
        for k in r:
            if any(f in k.lower() for f in FORBIDDEN_KEYS):
                bad.append(f"row {i}: forbidden key {k!r}")
    return bad


# ------------------------------------------------------------------ the compare
def compare(led: dict, run: dict, only: list[str] | None = None) -> dict:
    """Every ledger row against the run. verdict: ok | better | WORSE | missing |
    reader_moved. `fail` is True when any row is WORSE, missing or reader_moved."""
    out = []
    for r in led["rows"]:
        s, fig, tol = r["job"], r["figure"], r["tolerance"]
        if only and s not in only:
            continue
        now = run["values"].get(s, {}).get(fig)
        row = {**{k: r[k] for k in ("job", "figure", "baseline", "tolerance", "worse")},
               "now": now, "delta": None, "verdict": "ok"}
        if fig == "sttype_kappa":
            row["chance"], row["chance_now"] = r.get("chance"), run.get("chance", {}).get(s)
        if now is None:
            row["verdict"] = "missing"
        else:
            d = now - r["baseline"]
            row["delta"] = round(d, 4)
            sign = 1 if r["worse"] == "up" else -1
            if sign * d > tol + EPS:
                row["verdict"] = "WORSE"
            elif -sign * d > tol + EPS:
                row["verdict"] = "better"
            if fig in PRO_SIDE and r.get("pro") is not None:
                pro_now = run.get("pro", {}).get(s, {}).get(fig)
                if pro_now is not None and abs(pro_now - r["pro"]) > EPS:
                    row["verdict"] = "reader_moved"
                    row["pro"], row["pro_now"] = r["pro"], pro_now
        out.append(row)
    counts = {v: sum(1 for r in out if r["verdict"] == v) for v in ("ok", "better", "WORSE", "missing", "reader_moved")}
    return {"rows": out, "counts": counts,
            "fail": bool(counts["WORSE"] or counts["missing"] or counts["reader_moved"])}


def _fmt(fig: str, v, chance=None) -> str:
    if v is None:
        return "-"
    if fig == "sttype_kappa":
        deg = "d" if (chance or 0) >= 0.999 else ""
        return f"{v:.2f}{deg} ({chance:.2f})" if chance is not None else f"{v:.2f}{deg}"
    if fig in ("direction_kappa", "word_cc"):
        return f"{v:.2f}"
    if fig == "needle_up_mm":
        return f"{v:,.1f}"
    return f"{v:,}"


def _fmt_delta(fig: str, d) -> str:
    if d is None:
        return "-"
    if fig in ("sttype_kappa", "direction_kappa", "word_cc"):
        return f"{d:+.2f}"
    if fig == "needle_up_mm":
        return f"{d:+,.1f}"
    return f"{d:+,}"


def _fmt_tol(fig: str, tol) -> str:
    if fig in ("sttype_kappa", "direction_kappa", "word_cc"):
        return f"{tol:.2f}"
    return _fmt(fig, tol)


def movers_table(cmp: dict, all_rows: bool = False) -> str:
    """Markdown: the movers (anything not `ok`), or every row with `all_rows`."""
    c = cmp["counts"]
    head = (f"{c['WORSE']} wrong-way past tolerance, {c['missing']} missing, {c['reader_moved']} reader moved, "
            f"{c['better']} right-way past tolerance, {c['ok']} within tolerance "
            f"-> {'FAIL' if cmp['fail'] else 'pass'}")
    rows = [r for r in cmp["rows"] if all_rows or r["verdict"] != "ok"]
    if not rows:
        return head + "\n\nNo movers."
    L = [head, "", "| job | figure | baseline | now | delta | tolerance | worse is | verdict |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        fig = r["figure"]
        base = _fmt(fig, r["baseline"], r.get("chance"))
        now = _fmt(fig, r["now"], r.get("chance_now"))
        if r["verdict"] == "reader_moved":
            now += f" (pro {_fmt(fig, r['pro'])} -> {_fmt(fig, r['pro_now'])})"
        L.append(f"| {r['job']} | {FIGURES[fig]['label']} | {base} | {now} | {_fmt_delta(fig, r['delta'])} | "
                 f"{_fmt_tol(fig, r['tolerance'])} | {r['worse']} | {r['verdict']} |")
    return "\n".join(L)


def ledger_table(led: dict) -> str:
    """Markdown: job, figure, baseline, tolerance, direction, spread, pro's value."""
    L = [f"Captured {led['captured'].get('date')} on {(led.get('env') or {}).get('platform')}, "
         f"{led['captured'].get('passes')} pass(es)"
         + (f", engine {led['captured']['engine']['head']} ({led['captured']['engine']['tree']})"
            if led["captured"].get("engine") else "")
         + (f", run {led['captured']['run_url']}" if led["captured"].get("run_url") else ""),
         "", "| job | figure | baseline | tolerance | worse is | spread seen | pro |", "|---|---|---|---|---|---|---|"]
    for r in led["rows"]:
        fig = r["figure"]
        tol = _fmt_tol(fig, r["tolerance"])
        spread = r.get("spread")
        sp = "-" if spread is None else (f"{spread:.3f}" if isinstance(spread, float) and fig != "needle_up_mm"
                                         else _fmt(fig, spread))
        pro = _fmt(fig, r.get("pro")) if fig in PRO_SIDE else "-"
        if fig == "word_cc" and r.get("words") is not None:
            pro += f" (n {r['words']})"
        L.append(f"| {r['job']} | {FIGURES[fig]['label']} | {_fmt(fig, r['baseline'], r.get('chance'))} | {tol} | "
                 f"{r['worse']} | {sp} | {pro} |")
    return "\n".join(L)


# ------------------------------------------------------------------ files
def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(obj: dict, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.tripwire", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("cmd", choices=("measure", "capture", "check", "table", "jobs"))
    ap.add_argument("--ledger", type=Path, default=LEDGER, help=f"default {LEDGER.relative_to(DIGITIZER)}")
    ap.add_argument("--runs", type=Path, default=Path("tripwire_runs"),
                    help="where ours.dst / design.json / score/ land (measure, check)")
    ap.add_argument("--kent-dir", type=Path, help="where the zip's pro files are extracted (default RUNS/_kent)")
    ap.add_argument("--figures", type=Path, help="measure: write the pass here; check: read this pass instead of running")
    ap.add_argument("--from", dest="passes", nargs="+", type=Path, help="capture: the passes (measure outputs)")
    ap.add_argument("--run-url", help="capture: the Actions run the passes came from")
    ap.add_argument("--only", nargs="*", help="a subset of the committed jobs")
    ap.add_argument("--no-words", action="store_true", help="skip the word cc reading (no tesseract)")
    ap.add_argument("--table", type=Path, help="check: write the markdown table here too")
    ap.add_argument("--json", dest="json_out", type=Path, help="check: write the compare as JSON here")
    ap.add_argument("--all", action="store_true", help="check: print every row, not only the movers")
    a = ap.parse_args(argv)

    if a.cmd == "jobs":
        for s in committed_jobs():
            print(s)
        return 0

    if a.cmd == "capture":
        if not a.passes:
            ap.error("capture needs --from PASS.json [PASS.json ...]")
        passes = [_load(p) for p in a.passes]
        led = build_ledger(passes, a.run_url)
        bad = validate_ledger(led)
        if bad:
            raise SystemExit("ledger would be malformed: " + "; ".join(bad))
        _dump(led, a.ledger)
        if len(passes) < 2:
            print("WARNING: one pass only -- every tolerance is 0 and unmeasured; capture from 2+ passes", file=sys.stderr)
        print(ledger_table(led))
        print(f"\nwrote {a.ledger} ({len(led['rows'])} rows, {len(passes)} pass(es))")
        return 0

    if a.cmd == "table":
        print(ledger_table(_load(a.ledger)))
        return 0

    slugs = a.only or committed_jobs()
    unknown = sorted(set(slugs) - set(committed_jobs()))
    if unknown:
        ap.error(f"not committed pairs: {unknown}")

    if a.cmd == "measure":
        run = measure(a.runs, slugs, not a.no_words, a.kent_dir)
        out = a.figures or (a.runs / "figures.json")
        _dump(run, out)
        print(f"wrote {out}")
        return 0

    # check
    led = _load(a.ledger)
    bad = validate_ledger(led)
    if bad:
        raise SystemExit("malformed ledger: " + "; ".join(bad))
    if a.figures and a.figures.exists():
        run = _load(a.figures)
    else:
        run = measure(a.runs, slugs, not a.no_words, a.kent_dir)
        _dump(run, a.figures or (a.runs / "figures.json"))
    cmp = compare(led, run, a.only)
    text = movers_table(cmp, a.all)
    print(text)
    if a.table:
        a.table.parent.mkdir(parents=True, exist_ok=True)
        a.table.write_text(text + "\n", encoding="utf-8")
    if a.json_out:
        _dump(cmp, a.json_out)
    return 1 if cmp["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
