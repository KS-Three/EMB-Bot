#!/usr/bin/env python
"""One table for every parked default-OFF flag: what flipping it costs and buys.

Five flags are built, measured and OFF, each priced against `main` on its own
by the session that wrote it, each in its own units. That is enough to review a
PR and not enough to decide a default, for two reasons this tool exists to fix:

  1. **Nobody has measured them TOGETHER.** Every number in MASTER_SCOPE is a
     one-flag-vs-baseline reading. Four of the five move the region set or the
     thread assignment on the same lane (`gradient`), so "flip these three"
     is not the sum of three rows, and a sheet that implies it is would be
     wrong in the direction that costs a recapture to discover.
  2. **They are priced in different units** — one in cones, one in ΔE00, one
     in bare mm², one in grade. A decision needs them side by side in the
     units the machine bills and the grader reads.

    .venv/bin/python tools/flip_sheet.py run      # measure (resumable)
    .venv/bin/python tools/flip_sheet.py report   # the sheet

`run` caches one JSON per (fixture, arm) under `--out`, so an interrupted pass
resumes instead of restarting. Nothing here changes stitches: every arm is a
`PipelineConfig` keyword.

**Read the grade with the floor in mind.** `docs/yardstick-disagreements-
2026-09-06.md` row 6: twelve of the corpus's combos score exactly 0 with
unclamped scores from -272 to -38, so on those designs a real improvement
moves no grade and the grade is not evidence either way. This tool prints
`stitches`, `trims`, `blocks` and `cones` alongside it for that reason — they
are not saturated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# One OpenMP team per worker, or four processes fight over four cores and the
# pass runs slower than serial. The repo has been here before (the OCR gate's
# own note in `preflight`).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

TESTDATA = ROOT / "testdata"

# The arms. `off` is the shipped default and every other arm is that plus one
# keyword, so a row that reads identical to `off` IS byte-identical rather than
# merely close. `all` is the combination nobody had measured.
ARMS: dict[str, dict] = {
    "off": {},
    "halo": {"dissolve_phantom_blends": True},
    "resnap_small": {"revalidate_small_shapes": True},
    "resnap_bind": {"bind_resnap_all_classes": True},
    "satin_stroke": {"satin_per_stroke": True},
    "satin_patch": {"satin_patch_junctions": True},
    # Added 2026-09-07. `revalidate_threads` scored its argmin on a raw
    # `cv2.fillPoly` footprint while the grader erodes and drops the
    # background, so on a thin shape the re-snap chose a thread for the
    # anti-alias halo — `logo_gaulke_roofing`'s `Se6eddd27` reads 11.4 dE00
    # there and 63.6 in preflight. A sixth parked flag belongs in the sheet
    # that exists to price parked flags.
    "resnap_mask": {"resnap_mask_matches_grader": True},
    # --- combinations -------------------------------------------------------
    # `all` answers "flip everything"; nobody flips everything. These are the
    # combinations someone would actually ship, and the reason they are arms
    # rather than arithmetic is the header above: a combination is not the sum
    # of its rows, and this sheet's OWN recommendation was three flags nobody
    # had run together.
    "rec3": {
        "revalidate_small_shapes": True,
        "bind_resnap_all_classes": True,
        "satin_patch_junctions": True,
    },
    "rec4": {
        "revalidate_small_shapes": True,
        "bind_resnap_all_classes": True,
        "satin_patch_junctions": True,
        "satin_per_stroke": True,
    },
    # `rec4` plus the sixth flag. The sheet's recommendation was measured
    # before `resnap_mask_matches_grader` existed, and a combination is not
    # the sum of its rows — the whole thesis of this tool. Both flags touch
    # the thread assignment (one lowers the re-snap's floor, one changes the
    # pixels it reads), so this pair in particular could not be inferred.
    "rec4_mask": {
        "revalidate_small_shapes": True,
        "bind_resnap_all_classes": True,
        "satin_patch_junctions": True,
        "satin_per_stroke": True,
        "resnap_mask_matches_grader": True,
    },
    # The only pair in the ten that takes any fixture down a grade. `halo`
    # splits `logo_script_tires` into two more satin strokes and `satin_patch`
    # then finds junctions to fill that do not exist without it; neither flag
    # alone moves that fixture off A 100. Kept as an arm so the interaction is
    # reproducible rather than a number in a doc.
    "halo_patch": {
        "dissolve_phantom_blends": True,
        "satin_patch_junctions": True,
    },
    "all": {
        "dissolve_phantom_blends": True,
        "revalidate_small_shapes": True,
        "bind_resnap_all_classes": True,
        "satin_per_stroke": True,
        "satin_patch_junctions": True,
    },
}

# An arm is a "single" if it flips exactly one flag. Derived, not listed, so
# adding a combination above cannot silently make it a baseline for the
# interaction table.
SINGLES = [a for a, kw in ARMS.items() if len(kw) == 1]

# `edge_cap` and `chain_links` are deliberately NOT arms here.
#   * `edge_cap` ("bean"/"satin", defect 19) is gate 1: which cap, if either,
#     is a question cloth answers. Measuring it would produce a number that
#     cannot be acted on.
#   * `chain_links` is barred permanently (ROADMAP gate 3, and gate 1 names
#     link cover tolerance): it sews needle-down thread on bare fabric, and a
#     green suite has already concealed that once.
BARRED = {
    "edge_cap": "gate 1 — a sew-out settles which cap, if either (defect 19)",
    "chain_links": "gate 3, permanently — sews needle-down thread on bare cloth",
}

GARMENT = "left_chest"
WIDTH_MM = 80.0


def fixtures() -> list[str]:
    from tools.corpus_scorecard import FIXTURES
    return list(FIXTURES)


_HEAD: str | None = None   # computed once per process, not per measurement


def _head() -> str:
    """The engine tree a row was measured on.

    Not decoration. The first pass of this sheet was cached before
    `dissolve_phantom_blends` was fixed, the fixed arms were re-measured into a
    SECOND directory, and the published sheet drew rows from both — resting on
    the reasonable but unverified inference that the four untouched arms could
    not have moved. A row that names its own tree makes that detectable instead
    of inferable, and `report` refuses to mix trees silently.
    """
    global _HEAD
    if _HEAD is not None:
        return _HEAD
    import subprocess

    def _git(*args) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=10, check=True).stdout
    try:
        head = _git("rev-parse", "--short", "HEAD").strip()
        # A dirty tree is NOT the commit it sits on, and a row that claims to
        # be is exactly the over-claim this field exists to stop. Engine and
        # tool changes both count: a tool edit cannot move a stitch, but
        # proving that per row is not this function's job.
        if _git("status", "--porcelain").strip():
            head += "-dirty"
    except Exception:  # noqa: BLE001 — a missing git must not sink a measurement
        head = "?"
    _HEAD = head
    return _HEAD


def _stitch_digest(plan) -> str:
    """A stable fingerprint of the sewn result, so "unchanged" is provable.

    Rounded to the micron: the plan's own coordinates are floats and an
    identical geometry can differ in the last bit across a rebuild. Blocks and
    their cones are folded in, because two arms can lay the same thread path
    and load different spools.
    """
    h = hashlib.blake2b(digest_size=16)
    for i, b in enumerate(plan.blocks):
        num = plan.palette[i].get("number", "?") if i < len(plan.palette) else "?"
        h.update(f"|B{i}:{num}".encode())
        for r in b.runs:
            h.update(f"|{r.kind}:{int(r.trim)}:{int(r.jump)}".encode())
            for x, y in r.points:
                h.update(f"{x:.3f},{y:.3f};".encode())
    return h.hexdigest()


def measure(fixture: str, arm: str) -> dict:
    """Digitize one fixture under one arm. -> the row."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import digitize
    from digitizer_core.preflight import run_preflight

    path = TESTDATA / fixture
    kw = dict(target_width_mm=WIDTH_MM, garment_id=GARMENT, **ARMS[arm])
    t0 = time.time()
    try:
        result, plan = digitize(path, PipelineConfig(**kw))
        report = run_preflight(result, plan, PipelineConfig(**kw), image=path)
    except Exception as exc:  # noqa: BLE001 — one bad fixture must not sink the pass
        return {"fixture": fixture, "arm": arm,
                "error": f"{type(exc).__name__}: {exc}"}
    st = plan.stats
    cones = [p.get("number", "?") for p in plan.palette]
    return {
        "fixture": fixture,
        "arm": arm,
        "class": result.design_class,
        "stitches": st.stitch_count,
        "trims": st.trims,
        "jumps": st.jumps,
        "changes": st.color_changes,
        "blocks": len(plan.blocks),
        "cones": len(set(cones)),
        "cone_list": cones,
        "regions": len(result.regions),
        "thread_m": round(st.thread_m_total, 2),
        "grade": report["grade"],
        "score": report["score"],
        "findings": sorted(f"{f['code']}:{f['severity']}" for f in report["findings"]),
        "digest": _stitch_digest(plan),
        "head": _head(),
        "secs": round(time.time() - t0, 1),
    }


def _job(args) -> dict:
    return measure(*args)


def run(out: Path, workers: int, only: list[str] | None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    arms = only or list(ARMS)
    todo = []
    for arm in arms:
        for fx in fixtures():
            dest = out / f"{arm}__{fx.replace('/', '_')}.json"
            if dest.exists():
                continue
            todo.append((fx, arm))
    print(f"{len(todo)} runs to do ({len(arms)} arms x {len(fixtures())} fixtures, "
          f"{workers} workers)", flush=True)
    if not todo:
        return 0
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for row in ex.map(_job, todo):
            dest = out / f"{row['arm']}__{row['fixture'].replace('/', '_')}.json"
            dest.write_text(json.dumps(row, indent=1))
            done += 1
            tag = row.get("error") or (f"{row['grade']} st={row['stitches']} "
                                       f"tr={row['trims']} cones={row['cones']}")
            print(f"[{done}/{len(todo)}] {row['arm']:<13} {row['fixture']:<38} {tag}",
                  flush=True)
    return 0


def _load(out: Path) -> dict[tuple[str, str], dict]:
    rows: dict[tuple[str, str], dict] = {}
    for p in sorted(out.glob("*.json")):
        r = json.loads(p.read_text())
        rows[(r["arm"], r["fixture"])] = r
    return rows


def report(out: Path) -> int:
    rows = _load(out)
    if not rows:
        print("nothing measured yet — run `flip_sheet.py run` first")
        return 1
    fxs = fixtures()
    base = {f: rows.get(("off", f)) for f in fxs}

    print(f"# Flip sheet — {len(fxs)} fixtures @ {WIDTH_MM:g} mm / {GARMENT}\n")
    # Two different findings, and the banner must not conflate them: rows
    # stamped with DIFFERENT commits were provably measured on different
    # engines; rows with no stamp at all predate `head` (2026-09-07) and are
    # merely unknown. Saying "different engines" about unknown rows would be
    # the same over-claim this banner exists to catch.
    heads: dict[str, list[str]] = {}
    for (arm, fx), r in rows.items():
        heads.setdefault(r.get("head") or "unrecorded", []).append(f"{arm}/{fx}")
    known = {h: w for h, w in heads.items() if h != "unrecorded"}
    unknown = heads.get("unrecorded", [])

    def _line(h, who):
        arms = sorted({w.split("/")[0] for w in who})
        print(f"  - `{h}`: {len(who)} rows, arms {', '.join(arms)}")

    if len(known) > 1:
        print("**MIXED TREES — these rows were measured on different engines.** "
              "A cross-arm comparison below may be an artifact of the "
              "difference between them, not of the flags:")
        for h, who in sorted(known.items()):
            _line(h, who)
        if unknown:
            _line("unrecorded", unknown)
        print()
    elif unknown:
        print(f"**PROVENANCE UNKNOWN for {len(unknown)} of {len(rows)} rows** — "
              "they predate `head` stamping (2026-09-07), so this sheet cannot "
              "show they came from one engine. Re-run those arms to be sure:")
        _line("unrecorded", unknown)
        for h, who in sorted(known.items()):
            _line(h, who)
        print()
    print("Barred from this sheet on purpose:")
    for k, why in BARRED.items():
        print(f"  - `{k}`: {why}")
    print()

    for arm in ARMS:
        if arm == "off":
            continue
        moved, ident, errs = [], 0, []
        d_st = d_tr = d_bl = d_cn = 0
        up, down = [], []
        for f in fxs:
            b, a = base.get(f), rows.get((arm, f))
            if not b or not a:
                continue
            if "error" in a or "error" in b:
                errs.append(f)
                continue
            if a["digest"] == b["digest"]:
                ident += 1
                continue
            moved.append(f)
            d_st += a["stitches"] - b["stitches"]
            d_tr += a["trims"] - b["trims"]
            d_bl += a["blocks"] - b["blocks"]
            d_cn += a["cones"] - b["cones"]
            if a["score"] > b["score"]:
                up.append(f"{f} {b['grade']} {b['score']}->{a['grade']} {a['score']}")
            elif a["score"] < b["score"]:
                down.append(f"{f} {b['grade']} {b['score']}->{a['grade']} {a['score']}")
        print(f"## {arm}   {', '.join(f'{k}={v}' for k, v in ARMS[arm].items())}")
        print(f"  moved {len(moved)} / identical {ident}"
              + (f" / errors {len(errs)}" if errs else ""))
        print(f"  net   stitches {d_st:+d}  trims {d_tr:+d}  blocks {d_bl:+d}  "
              f"cones {d_cn:+d}")
        if up:
            print("  grade UP   : " + "; ".join(up))
        if down:
            print("  grade DOWN : " + "; ".join(down))
        if not up and not down and moved:
            print("  grade      : no letter moves (see the floor note in the docstring)")
        if moved:
            print("  moved      : " + ", ".join(moved))
        if errs:
            print("  ERRORS     : " + ", ".join(errs))
        print()

    # Interaction: does `all` equal the fixtures each single flag moved?
    singles = SINGLES
    print("## interaction — does `all` behave like the union of the singles?\n")
    print(f"{'fixture':<40} {'singles that move it':<34} {'all == that single?'}")
    for f in fxs:
        b = base.get(f)
        if not b or "error" in b:
            continue
        movers = [a for a in singles
                  if rows.get((a, f)) and "error" not in rows[(a, f)]
                  and rows[(a, f)]["digest"] != b["digest"]]
        allrow = rows.get(("all", f))
        if not allrow or "error" in allrow:
            continue
        all_moved = allrow["digest"] != b["digest"]
        if not movers and not all_moved:
            continue
        if len(movers) == 1 and all_moved:
            same = allrow["digest"] == rows[(movers[0], f)]["digest"]
            verdict = "yes" if same else "NO — the pair interacts"
        elif not movers and all_moved:
            verdict = "NO — moves only in combination"
        elif movers and not all_moved:
            verdict = "NO — the combination CANCELS it"
        else:
            verdict = f"n/a ({len(movers)} singles move it)"
        print(f"{f:<40} {','.join(movers) or '-':<34} {verdict}")

    # Every multi-flag arm against the singles it is made of. `all` answers
    # "flip everything" and nobody flips everything; this answers the question
    # a flip decision actually asks.
    combos = [a for a in ARMS if len(ARMS[a]) > 1]
    print("\n## combinations — where a combination differs from its parts\n")
    for arm in combos:
        parts = [s_ for s_ in SINGLES
                 if ARMS[s_].items() <= ARMS[arm].items()]
        print(f"### {arm} = {' + '.join(parts)}")
        surprises = 0
        for f in fxs:
            b, a = base.get(f), rows.get((arm, f))
            if not b or not a or "error" in b or "error" in a:
                continue
            movers = [s_ for s_ in parts
                      if rows.get((s_, f)) and "error" not in rows[(s_, f)]
                      and rows[(s_, f)]["digest"] != b["digest"]]
            moved = a["digest"] != b["digest"]
            # The combination is "as expected" when no part moves it and it
            # does not move, or when exactly one part moves it and the
            # combination reproduces that part byte for byte.
            if not movers and not moved:
                continue
            if len(movers) == 1 and moved and a["digest"] == rows[(movers[0], f)]["digest"]:
                continue
            surprises += 1
            best = max((rows[(s_, f)]["score"] for s_ in movers), default=b["score"])
            worst = min((rows[(s_, f)]["score"] for s_ in movers), default=b["score"])
            if a["score"] < min(worst, b["score"]):
                tag = "WORSE than any part"
            elif a["score"] > max(best, b["score"]):
                tag = "better than any part"
            elif movers:
                tag = "best part's grade, different geometry"
            else:
                tag = "moves only in combination"
            print(f"  {f:<38} parts:{','.join(movers) or '-':<26} "
                  f"{b['grade']} {b['score']} -> {a['grade']} {a['score']}  "
                  f"tr {b['trims']}->{a['trims']}  {tag}")
        if not surprises:
            print("  behaves as the union of its parts on all "
                  f"{len(fxs)} fixtures")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["run", "report"])
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "flip_sheet")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--arm", action="append", dest="arms")
    args = ap.parse_args(argv)
    if args.mode == "run":
        return run(args.out, args.workers, args.arms)
    return report(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
