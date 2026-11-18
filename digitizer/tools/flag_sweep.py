#!/usr/bin/env python
"""One flag, OFF vs ON, over every placement the nightly tripwire runs plus the corpus fixtures.

A flip's evidence sweep missed a second placement of the same artwork on
2026-11-18 (#1656 was reported as moving `mfab_hat` only; it also moved
`mfab_lc`, docs/tripwire-trace-2026-11-18.md) because each worker wrote their
own sweep script. This is the one tool.

    python -m tools.flag_sweep --flag NAME [--set key=value ...] --out DIR
                               [--on JSON] [--off JSON] [--pictures] [--only SLUG ...]
                               [--no-tripwire] [--no-corpus]

Population (nothing else, nothing less):
  * every `tools.tripwire.committed_jobs()` placement (18 on 2026-11-18), at the
    pro's width and garment, the Studio request the tripwire's `measure` uses
    (`pro_pair.digitize`);
  * every `tools.corpus_scorecard.FIXTURES` entry (26), at the Studio's own
    request (`fremont_triage.KENT_WIDTH_MM`, hat_front).

Arms: OFF sets `--flag` to `--off` (default `false`), ON to `--on` (default
`true`); each `--set key=value` is laid over BOTH arms (a context flag), spelled
as `pro_pair --set` spells it (`extra.KEY` goes to `cfg.extra`). For a flag that
carries a value, `--on 0.5 --off null`.

Per run, both ways: the stitch md5 (the machine's STITCH/JUMP/TRIM/COLOR
records as pystitch reads the written DST), stitches, trims, jumps, needle-up
mm, colour count, and moved yes/no (md5 differs). Writes `sweep.json` and
`sweep.md` in `--out`. A run that cannot digitize is a row with its error, never
a silent drop; the exit code is 0 either way (this reports, it gates nothing).

`--pictures` writes ORIGINAL | BEFORE | AFTER for each mover to
`--out/pictures/<slug>.png`: OUR renders of OUR stitches only (never a
professional's file). The original is the client's art, so `--out` is scratch:
commit nothing under `digitizer/eye_pairs_out/` or a kit's own artwork.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

SCHEMA = 1
PPM = 20.0
FIGS = ("stitches", "trims", "jumps", "needle_up_mm", "colours")


# ------------------------------------------------------------------ population
def population(tripwire: bool = True, corpus: bool = True, only: list[str] | None = None) -> list[dict]:
    """[{slug, kind, art, width_mm, garment}] in tripwire-then-corpus order."""
    from tools import tripwire as tw
    from tools.corpus_scorecard import FIXTURES, TESTDATA
    from tools.fremont_triage import KENT_WIDTH_MM
    from tools.pro_baseline import JOBS
    rows: list[dict] = []
    if tripwire:
        for s in tw.committed_jobs():
            garment, width, art, *_ = JOBS[s]
            rows.append({"slug": s, "kind": "tripwire", "spec": art, "width_mm": float(width),
                         "garment": garment})
    if corpus:
        for f in FIXTURES:
            rows.append({"slug": "corpus:" + f, "kind": "corpus", "path": str(TESTDATA / f),
                         "width_mm": float(KENT_WIDTH_MM), "garment": "hat_front"})
    if only:
        want = set(only)
        rows = [r for r in rows if r["slug"] in want or r["slug"].removeprefix("corpus:") in want]
    return rows


def _resolve_art(row: dict, scratch: Path | None) -> Path:
    if "path" in row:
        return Path(row["path"])
    from tools.pro_baseline import resolve
    return resolve(row["spec"])


def arms(flag: str, sets: dict, on=True, off=False) -> dict[str, dict]:
    """The two `extra` dicts handed to `pro_pair.digitize`."""
    return {"off": {**sets, flag: off}, "on": {**sets, flag: on}}


# ------------------------------------------------------------------ one run
def measure_dst(dst: Path) -> dict:
    """The figures of a written DST, read the way the tripwire reads one."""
    import pystitch
    from tools.pro_baseline import needle_up
    pat = pystitch.read(str(dst))
    m = pystitch.COMMAND_MASK
    h = hashlib.md5()
    n = {"stitches": 0, "trims": 0, "jumps": 0, "colours": 1}
    for x, y, c in pat.stitches:
        c &= m
        h.update(f"{x},{y},{c};".encode())
        if c == pystitch.STITCH:
            n["stitches"] += 1
        elif c == pystitch.TRIM:
            n["trims"] += 1
        elif c == pystitch.JUMP:
            n["jumps"] += 1
        elif c == pystitch.COLOR_CHANGE:
            n["colours"] += 1
    return {"md5": h.hexdigest(), **n, "needle_up_mm": needle_up(dst)["needle_up_mm"]}


def run_arm(art: Path, row: dict, extra: dict, out: Path, arm: str):
    """Digitize once; write `out/<arm>.dst` and `out/<arm>.design.json`; -> (figures, design)."""
    from digitizer_core.export import write_dst
    from tools import pro_pair
    d = pro_pair.digitize(art, row["width_mm"], row["garment"], extra)
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{arm}.dst"
    write_dst(d.plan, dst)
    (out / f"{arm}.design.json").write_text(json.dumps(d.design), encoding="utf-8")
    fig = measure_dst(dst)
    fig["colours"] = max(fig["colours"], len(d.design.get("colors", []) or []))
    return fig, d.design


def sweep_one(row: dict, flag: str, arm_extra: dict, out: Path) -> dict:
    res = {"slug": row["slug"], "kind": row["kind"], "width_mm": row["width_mm"],
           "garment": row["garment"]}
    safe = row["slug"].replace(":", "_").replace("/", "_")
    t = time.time()
    try:
        art = _resolve_art(row, None)
        res["art"] = art.name
        for arm in ("off", "on"):
            res[arm], _design = run_arm(art, row, arm_extra[arm], out / "runs" / safe, arm)
        res["moved"] = res["off"]["md5"] != res["on"]["md5"]
        res["_art_path"] = str(art)
    except SystemExit as e:                                    # a missing file is a row, not a crash
        res["error"] = f"SystemExit: {e}"[:300]
    except Exception as e:                                     # noqa: BLE001
        res["error"] = f"{type(e).__name__}: {e}"[:300]
    res["secs"] = round(time.time() - t, 1)
    return res


# ------------------------------------------------------------------ report
def _delta(a, b) -> str:
    d = b - a
    if isinstance(d, float):
        d = round(d, 1)
    return f"{d:+g}"


def table(doc: dict) -> str:
    rows = doc["rows"]
    moved = [r for r in rows if r.get("moved")]
    errs = [r for r in rows if "error" in r]
    lines = [f"# flag sweep: `{doc['flag']}` OFF={json.dumps(doc['off'])} vs ON={json.dumps(doc['on'])}", ""]
    if doc["sets"]:
        lines += [f"Context `--set`: `{json.dumps(doc['sets'])}` (both arms)", ""]
    lines += [f"{len(rows)} runs ({sum(r['kind'] == 'tripwire' for r in rows)} tripwire placements, "
              f"{sum(r['kind'] == 'corpus' for r in rows)} corpus fixtures): "
              f"**{len(moved)} moved**, {len(rows) - len(moved) - len(errs)} unchanged, {len(errs)} errored.", ""]
    lines += ["| run | moved | md5 off | md5 on | stitches | trims | jumps | needle-up mm | colours |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['slug']} | ERROR | | | {r['error']} | | | | |")
            continue
        o, n = r["off"], r["on"]
        cells = [f"{o[k]} -> {n[k]} ({_delta(o[k], n[k])})" if o[k] != n[k] else f"{o[k]}" for k in FIGS]
        lines.append(f"| {r['slug']} | {'yes' if r['moved'] else 'no'} | `{o['md5'][:10]}` | "
                     f"`{n['md5'][:10]}` | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def picture(row: dict, out: Path):
    """ORIGINAL | BEFORE | AFTER, our renders only, to `out/pictures/<slug>.png`."""
    import cv2
    from digitizer_core import stitchviz
    from tools import pro_pair
    safe = row["slug"].replace(":", "_").replace("/", "_")
    rd = out / "runs" / safe
    imgs = [pro_pair._label(pro_pair._scaled(pro_pair._art_ink(Path(row["_art_path"])),
                                             row["width_mm"], PPM, cv2.INTER_AREA), "ORIGINAL")]
    for arm, name in (("off", "BEFORE (flag OFF)"), ("on", "AFTER (flag ON)")):
        design = json.loads((rd / f"{arm}.design.json").read_text(encoding="utf-8"))
        imgs.append(pro_pair._label(stitchviz.render_design(design, px_per_mm=PPM), name))
    dest = out / "pictures"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{safe}.png"
    cv2.imwrite(str(path), pro_pair._hstack(imgs))
    return path


# ------------------------------------------------------------------ main
def parse_value(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.flag_sweep",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--flag", required=True, help="the PipelineConfig field (or extra.KEY) to flip")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="a config field laid over BOTH arms; repeatable")
    ap.add_argument("--on", default="true", help="the flag's ON value as JSON (default true)")
    ap.add_argument("--off", default="false", help="the flag's OFF value as JSON (default false)")
    ap.add_argument("--out", type=Path, required=True, help="scratch dir for sweep.json/.md, runs/, pictures/")
    ap.add_argument("--pictures", action="store_true",
                    help="write ORIGINAL | BEFORE | AFTER for each mover (our renders only) to OUT/pictures/")
    ap.add_argument("--only", nargs="*", help="a subset of slugs (tripwire slug, or fixture path / corpus:path)")
    ap.add_argument("--no-tripwire", action="store_true", help="skip the tripwire placements")
    ap.add_argument("--no-corpus", action="store_true", help="skip the corpus fixtures")
    ap.add_argument("--kent-dir", type=Path, help="where the zip's pro files are extracted (default OUT/_kent)")
    a = ap.parse_args(argv)
    from tools._console import utf8_console
    utf8_console()

    sets = {}
    for item in a.set:
        k, _, v = item.partition("=")
        sets[k.strip()] = parse_value(v)
    on, off = parse_value(a.on), parse_value(a.off)
    arm_extra = arms(a.flag, sets, on, off)
    pop = population(not a.no_tripwire, not a.no_corpus, a.only)
    if not pop:
        ap.error("the population is empty")
    a.out.mkdir(parents=True, exist_ok=True)
    tw_slugs = [r["slug"] for r in pop if r["kind"] == "tripwire"]
    if tw_slugs:
        from tools import tripwire as tw
        root = tw.materialise(a.kent_dir or a.out / "_kent", tw_slugs)
        print(f"pro files: {root}", flush=True)
    rows = []
    for i, row in enumerate(pop, 1):
        r = sweep_one(row, a.flag, arm_extra, a.out)
        rows.append(r)
        state = "ERROR " + r["error"] if "error" in r else ("MOVED" if r["moved"] else "same")
        print(f"[{i}/{len(pop)}] {r['slug']}: {state} ({r['secs']} s)", flush=True)
        if a.pictures and r.get("moved"):
            picture(r, a.out)
    for r in rows:
        r.pop("_art_path", None)
    doc = {"schema": SCHEMA, "flag": a.flag, "on": on, "off": off, "sets": sets, "rows": rows,
           "moved": [r["slug"] for r in rows if r.get("moved")],
           "errors": [r["slug"] for r in rows if "error" in r]}
    (a.out / "sweep.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    md = table(doc)
    (a.out / "sweep.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
