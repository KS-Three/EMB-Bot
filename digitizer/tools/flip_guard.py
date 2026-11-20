#!/usr/bin/env python
"""Flip guard: a standing BASE vs FLIP check that any default-flip PR runs.

PR #1641 flipped `satin_seam_hold` ON on 14 logos' evidence and silently broke
Ahora's gear, a design those 14 did not include. This digitizes a fixed, wide
design set twice (the current defaults, then the defaults with the flip's
overrides) and reports every design that MOVED, so "what did this flip touch
that its evidence did not cover" is a table, not a hope.

    .venv/Scripts/python -m tools.flip_guard OUT_DIR satin_seam_hold=True \\
        --evidence logo_mfab_lc --evidence logo_toat_machine
    .venv/Scripts/python -m tools.flip_guard OUT_DIR extra.some_key=1

Overrides are `field=value` (a PipelineConfig field; value parsed as a Python
literal, else a string) or `extra.key=value` (into `cfg.extra`). `--base k=v`
(repeatable) is applied to BOTH arms, to pin an engine other than today's
defaults (e.g. to replay a flip that is already merged).

Design set: the 26 `tools.corpus_scorecard.FIXTURES` plus
`testdata/art/commons_lettering/*.png` and `testdata/art/logo_*.png`
(deduplicated by bytes), at 80 mm `left_chest`; the lettering and logo art also
at `hat_front`. One JSON per (design, garment, arm) under OUT_DIR/cells, so a
re-run resumes; `--fresh` wipes them (do that after any code change: the cache
key is the inputs, not the engine).

Flags (reporting only; the exit code is always 0):
  OUTSIDE EVIDENCE  a design moved that is not in --evidence
  TRIMS +N          trims rose by 2 or more
  BARE THREAD       bare-fabric thread rose (`tools.hairline_travel.scan`, the
                    reader `tests/test_chaining.py::_thread_bare_mm` uses)

Writes OUT_DIR/flip_guard.html (summary table first, OFF | ON sheets below,
base64 JPEG <= 1600 px wide) and OUT_DIR/summary.json. Never raise a quality
ceiling (bare thread, chaining, coverage) to get a flip's tests passing.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import html
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TESTDATA = ROOT / "testdata"
WIDTH_MM = 80.0
LEFT_CHEST = "left_chest"
HAT = "hat_front"
TRIM_RISE = 2          # trims up by this many or more is flagged
BARE_RISE_MM = 0.1     # bare-thread mm up by more than this is flagged
MAX_PX = 1600


# --- overrides -------------------------------------------------------------

def parse_override(text: str) -> tuple[str, object]:
    """'field=value' or 'extra.key=value' -> (dotted key, parsed value)."""
    if "=" not in text:
        raise ValueError(f"override {text!r} is not field=value")
    key, raw = text.split("=", 1)
    key = key.strip()
    try:
        val = ast.literal_eval(raw.strip())
    except (ValueError, SyntaxError):
        val = raw.strip()
    return key, val


def split_overrides(items: list[str]) -> tuple[dict, dict]:
    """-> (config fields, cfg.extra entries)."""
    fields, extra = {}, {}
    for it in items or []:
        k, v = parse_override(it)
        if k.startswith("extra."):
            extra[k[len("extra."):]] = v
        else:
            fields[k] = v
    return fields, extra


def arm_kwargs(base: list[str], flip: list[str] | None) -> dict:
    """The PipelineConfig kwargs for one arm (flip=None is the BASE arm)."""
    f, e = split_overrides(base)
    if flip is not None:
        f2, e2 = split_overrides(flip)
        f.update(f2)
        e.update(e2)
    if e:
        f["extra"] = e
    return f


# --- design set ------------------------------------------------------------

def design_set(testdata: Path = TESTDATA) -> list[dict]:
    """[{name, path, garments}] -- see the module docstring. Deduplicated by
    bytes so one design never counts twice."""
    from tools.corpus_scorecard import FIXTURES
    out: list[dict] = []
    seen: set[str] = set()

    def add(path: Path, name: str, garments: list[str]) -> None:
        if not path.is_file():
            return
        h = hashlib.md5(path.read_bytes()).hexdigest()
        if h in seen:
            return
        seen.add(h)
        out.append({"name": name, "path": str(path), "garments": garments})

    for f in FIXTURES:
        add(testdata / f, f, [LEFT_CHEST])
    art = testdata / "art"
    extra = sorted((art / "commons_lettering").glob("*.png")) + sorted(art.glob("logo_*.png"))
    for p in extra:
        add(p, p.relative_to(testdata).as_posix(), [LEFT_CHEST, HAT])
    return out


# --- one cell --------------------------------------------------------------

def _init_worker() -> None:
    try:
        from tools.lettering_board import rembg_from_primary
        rembg_from_primary()
    except Exception:
        pass


def _cell_subprocess(job: tuple, timeout: float) -> dict:
    """run_cell in its own interpreter, killed after `timeout` seconds."""
    import subprocess
    path, name, garment, arm, kw, dest = job
    spec = Path(dest).with_suffix(".job")
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(json.dumps(job))
    try:
        subprocess.run([sys.executable, "-m", "tools.flip_guard", "--_cell", str(spec)], cwd=ROOT,
                       timeout=timeout, capture_output=True)
    except subprocess.TimeoutExpired:
        return {"name": name, "garment": garment, "arm": arm, "error": f"TIMEOUT after {timeout:.0f}s"}
    finally:
        spec.unlink(missing_ok=True)
    if Path(dest).is_file():
        return json.loads(Path(dest).read_text())
    return {"name": name, "garment": garment, "arm": arm, "error": "cell subprocess wrote nothing"}


def cell_path(out: Path, name: str, garment: str, arm: str, kw: dict) -> Path:
    key = hashlib.sha1(json.dumps([name, garment, WIDTH_MM, arm, kw], sort_keys=True,
                                  default=str).encode()).hexdigest()[:12]
    stem = Path(name).stem
    return out / "cells" / f"{stem}__{garment}__{arm}__{key}.json"


def run_cell(job: tuple) -> dict:
    """Digitize one (design, garment, arm); cached as one JSON. Never raises."""
    path, name, garment, arm, kw, dest = job
    dest = Path(dest)
    if dest.is_file():
        try:
            return json.loads(dest.read_text())
        except Exception:
            pass
    rec = {"name": name, "garment": garment, "arm": arm}
    t0 = time.perf_counter()
    try:
        from tools.eye_pairs.features import base_cfg, digitize_once
        from tools import hairline_travel as ht
        _g, _r, plan, design = digitize_once(path, base_cfg(WIDTH_MM, garment, **kw))
        s = ht.scan(plan)
        recs = design.get("stitches") or []
        rec.update({
            "stitches": sum(1 for r in recs if r["type"] == "stitch"),
            "trims": sum(1 for r in recs if r["type"] == "trim"),
            "colours": sum(1 for r in recs if r["type"] == "color"),
            "bare_mm": round(float(s["thread"]), 2),
            "exposed_legs": int(s["thread_legs"]),
            "travel_runs": int(s["travel_runs"]),
            "md5": hashlib.md5(json.dumps(recs, sort_keys=True).encode()).hexdigest(),
            "design": design,
        })
    except Exception as exc:  # a failed cell is reported, not fatal
        rec["error"] = f"{type(exc).__name__}: {exc}"
    rec["seconds"] = round(time.perf_counter() - t0, 1)
    if "error" not in rec:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(rec, separators=(",", ":")))
    return rec


# --- comparison ------------------------------------------------------------

def in_evidence(name: str, evidence: list[str]) -> bool:
    n = name.lower()
    stem = Path(name).stem.lower()
    return any(e.lower() in (n, stem) or e.lower() in n for e in evidence)


def compare(base: dict, flip: dict, evidence: list[str]) -> dict:
    """One row per design cell. Pure, so the unit test can drive it."""
    row = {"name": base["name"], "garment": base["garment"]}
    if "error" in base or "error" in flip:
        row.update(error=base.get("error") or flip.get("error"), moved=False, flags=["ERROR"])
        return row
    moved = base["md5"] != flip["md5"]
    row.update(
        moved=moved,
        base={k: base[k] for k in ("stitches", "trims", "colours", "bare_mm")},
        flip={k: flip[k] for k in ("stitches", "trims", "colours", "bare_mm")},
        evidenced=in_evidence(base["name"], evidence),
    )
    flags = []
    if moved:
        if not row["evidenced"]:
            flags.append("OUTSIDE EVIDENCE")
        if flip["trims"] - base["trims"] >= TRIM_RISE:
            flags.append(f"TRIMS +{flip['trims'] - base['trims']}")
        if flip["bare_mm"] - base["bare_mm"] > BARE_RISE_MM:
            flags.append(f"BARE THREAD +{flip['bare_mm'] - base['bare_mm']:.1f} mm")
    row["flags"] = flags
    return row


# --- report ----------------------------------------------------------------

def _jpeg_b64(img) -> str:
    import cv2
    h, w = img.shape[:2]
    if w > MAX_PX:
        img = cv2.resize(img, (MAX_PX, max(1, int(h * MAX_PX / w))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return base64.b64encode(buf.tobytes()).decode()


def make_sheet(base: dict, flip: dict, label: str):
    from tools.off_flags_sheet import sheet
    img, _m = sheet(label, f"{base['name']} [{base['garment']}]", base["design"], flip["design"],
                    note=f"{WIDTH_MM:g} mm, {base['garment']}", mark_trims=True, zoom_mm=12)
    return img


def table_text(rows: list[dict]) -> str:
    lines = [f"{'design':44} {'garment':10} {'stitches':>17} {'trims':>9} {'colours':>8} {'bare mm':>13}  flags"]
    for r in rows:
        if r.get("error"):
            lines.append(f"{r['name']:44} {r['garment']:10} ERROR {r['error']}")
            continue
        if not r["moved"]:
            continue
        b, f = r["base"], r["flip"]
        lines.append(f"{r['name']:44} {r['garment']:10} {b['stitches']:>7,}->{f['stitches']:<7,} "
                     f"{b['trims']:>3}->{f['trims']:<3} {b['colours']:>3}->{f['colours']:<3} "
                     f"{b['bare_mm']:>6.1f}->{f['bare_mm']:<6.1f}  {', '.join(r['flags'])}")
    return "\n".join(lines)


def write_html(out: Path, label: str, rows: list[dict], images: dict, n_cells: int, secs: float) -> Path:
    moved = [r for r in rows if r.get("moved")]
    flagged = [r for r in moved if r["flags"]]
    h = ["<!doctype html><meta charset=utf-8><title>flip guard</title>",
         "<style>body{font:14px system-ui;margin:16px;color:#222}table{border-collapse:collapse}"
         "td,th{border:1px solid #ccc;padding:3px 8px;text-align:right}td:first-child,th:first-child,"
         "td.f{text-align:left}.flag{background:#fde8e8}img{max-width:100%;border:1px solid #bbb}</style>",
         f"<h1>flip guard: {html.escape(label)}</h1>",
         f"<p>{len(rows)} design cells, {len(moved)} moved, {len(flagged)} flagged "
         f"({secs / 60:.1f} min). BASE -> FLIP; reporting only.</p>",
         "<table><tr><th>design</th><th>garment</th><th>stitches</th><th>trims</th><th>colours</th>"
         "<th>bare mm</th><th>flags</th></tr>"]
    for r in rows:
        if r.get("error"):
            h.append(f"<tr class=flag><td>{html.escape(r['name'])}</td><td>{r['garment']}</td>"
                     f"<td colspan=4>{html.escape(r['error'])}</td><td class=f>ERROR</td></tr>")
        elif r["moved"]:
            b, f = r["base"], r["flip"]
            h.append(f"<tr{' class=flag' if r['flags'] else ''}><td><a href='#{r['name']}|{r['garment']}'>"
                     f"{html.escape(r['name'])}</a></td><td>{r['garment']}</td>"
                     f"<td>{b['stitches']:,} -> {f['stitches']:,}</td><td>{b['trims']} -> {f['trims']}</td>"
                     f"<td>{b['colours']} -> {f['colours']}</td><td>{b['bare_mm']:.1f} -> {f['bare_mm']:.1f}</td>"
                     f"<td class=f>{html.escape(', '.join(r['flags']))}</td></tr>")
    h.append("</table>")
    if not moved:
        h.append("<p>No design moved.</p>")
    for r in moved:
        key = f"{r['name']}|{r['garment']}"
        if key in images:
            h.append(f"<h3 id='{html.escape(key)}'>{html.escape(r['name'])} [{r['garment']}] "
                     f"{html.escape(', '.join(r['flags']))}</h3>"
                     f"<img src='data:image/jpeg;base64,{images[key]}'>")
    p = out / "flip_guard.html"
    p.write_text("\n".join(h), encoding="utf-8")
    return p


def run(out: Path, flip: list[str], base: list[str] | None = None, evidence: list[str] | None = None,
        jobs: int = 8, designs: list[dict] | None = None, fresh: bool = False,
        cell_timeout: float = 900.0, only: list[str] | None = None) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    if fresh:
        for p in (out / "cells").glob("*.json"):
            p.unlink()
    designs = designs if designs is not None else design_set()
    if only:
        designs = [d for d in designs if any(o.lower() in d["name"].lower() for o in only)]
    kw = {"base": arm_kwargs(base or [], None), "flip": arm_kwargs(base or [], flip)}
    label = " ".join(flip) + (f"  (both arms: {' '.join(base)})" if base else "")
    todo = [(d["path"], d["name"], g, arm, kw[arm], str(cell_path(out, d["name"], g, arm, kw[arm])))
            for d in designs for g in d["garments"] for arm in ("base", "flip")]
    t0 = time.perf_counter()
    if jobs <= 1:
        _init_worker()
        results = [run_cell(j) for j in todo]
    else:
        # one subprocess per cell, so a stuck photo-lane digitize can be killed at
        # --cell-timeout (a pool worker cannot) and reported as TIMEOUT
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(lambda j: _cell_subprocess(j, cell_timeout), todo))
    cells = {(r["name"], r["garment"], r["arm"]): r for r in results}
    rows = []
    for d in designs:
        for g in d["garments"]:
            rows.append(compare(cells[(d["name"], g, "base")], cells[(d["name"], g, "flip")], evidence or []))
    images = {}
    for r in rows:
        if r.get("moved"):
            img = make_sheet(cells[(r["name"], r["garment"], "base")], cells[(r["name"], r["garment"], "flip")], label)
            images[f"{r['name']}|{r['garment']}"] = _jpeg_b64(img)
    secs = time.perf_counter() - t0
    write_html(out, label, rows, images, len(todo), secs)
    (out / "summary.json").write_text(json.dumps({"flip": flip, "base": base or [], "evidence": evidence or [],
                                                  "seconds": round(secs, 1), "rows": rows}, indent=1))
    print(f"flip_guard {label}: {sum(1 for r in rows if r.get('moved'))} moved of {len(rows)} cells, "
          f"{sum(1 for r in rows if r['flags'])} flagged, {secs / 60:.1f} min")
    print(table_text(rows))
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", type=Path, nargs="?")
    ap.add_argument("override", nargs="*", help="field=value or extra.key=value (the flip)")
    ap.add_argument("--_cell", help=argparse.SUPPRESS)
    ap.add_argument("--cell-timeout", type=float, default=900.0,
                    help="seconds before a stuck cell is killed and reported TIMEOUT (default 900)")
    ap.add_argument("--only", action="append", default=[], help="keep designs whose name contains this; repeatable")
    ap.add_argument("--base", action="append", default=[], help="override applied to BOTH arms")
    ap.add_argument("--evidence", action="append", default=[],
                    help="a design the PR's evidence covers (name, stem or substring); repeatable")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--fresh", action="store_true", help="discard cached cells first")
    a = ap.parse_args(argv)
    if a._cell:
        _init_worker()
        run_cell(tuple(json.loads(Path(a._cell).read_text())))
        return 0
    if a.out is None or not a.override:
        ap.error("OUT_DIR and at least one override are required")
    run(a.out, a.override, a.base, a.evidence, a.jobs, fresh=a.fresh,
        cell_timeout=a.cell_timeout, only=a.only)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
