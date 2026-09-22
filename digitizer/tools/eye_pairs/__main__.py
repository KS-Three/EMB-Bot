"""python -m tools.eye_pairs --render | --pair | --serve | --reveal | --verify

The order is the blinding: --render digitizes and renders every arm (any
scope, resumable), --pair builds the sitting and SEALS what each picture is,
--serve collects picks, --reveal refuses until every pair has one.

--pair is its own verb, not the tail of --render (review finding 3,
2026-09-17): a scoped `--render --fixtures x --arms y` used to rebuild the
pairs from every cached arm and reshuffle the whole sitting under a fixed
seed, with nothing to refuse it while picks.jsonl was still empty.
Spec: docs/superpowers/specs/2026-09-17-eye-pairs-design.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

import cv2

from digitizer_core.config import PHOTO_CLASSES
from digitizer_core.stitchviz import render_design

from tools import dropped_elements, edge_smoothness
from tools.artfid_eye_rank import VIEW_PX_PER_MM, _normalise_art
from tools.artfidelity_self import score_image
from tools.thin_strokes import STUDIO_MAX_COLORS, corpus_cases

from . import analysis as an
from . import features as ft
from .features import base_cfg, digitize_once, features_design_only, features_full
from .pairs import (ARMS, BASE, ArmRun, build_pairs, design_hash, load_picks,
                    sealed_hash, unpicked)
from .refarm import add_worktree, remove_worktree, run_ref_design
from .server import PORT, make_server

DIGITIZER = Path(__file__).resolve().parents[2]
REPO = DIGITIZER.parent
OUT = DIGITIZER / "eye_pairs_out"
# Re-exported so a test can monkeypatch the schema the cache key reads.
FEATURES_SCHEMA = ft.FEATURES_SCHEMA


def _say(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _default_ref_runner(ref: str):
    """-> (runner, closer) for ONE commit. The worktree lives under the
    system temp dir — never inside the repo (`refarm.guard_scratch`)."""
    dest = Path(tempfile.gettempdir()).resolve() / f"eye-pairs-ref-{ref}"
    remove_worktree(REPO, dest)                       # a crashed earlier run
    shutil.rmtree(dest, ignore_errors=True)
    engine = add_worktree(REPO, ref, dest) / "digitizer"

    def runner(image, width_mm, garment, max_colors):
        return run_ref_design(sys.executable, engine, image, width_mm, garment, max_colors)

    return runner, lambda: remove_worktree(REPO, dest)


def render(out=OUT, cases=None, arms=None, fixtures=None, only_arms=None,
           ref_factory=None) -> int:
    """Digitize and render every (fixture, arm); -> the number now ready.

    Resume-safe: a row is reused only when its `source_sha256` matches the
    image on disk AND its `schema` matches `FEATURES_SCHEMA` AND its design
    and render files exist. Name-only keying let a re-exported image stay
    'cached' for a whole sitting (review finding 7, 2026-09-17).

    `ref_factory(commit) -> (runner, closer)` is built once PER COMMIT, so
    two `__ref__` rows on different commits each get their own engine —
    the cache used to be 'has any ref been built' (review finding 6).
    Never builds pairs: that is `pair()`.
    """
    out = Path(out)
    for sub in ("designs", "renders"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    cases = list(corpus_cases() if cases is None else cases)
    arms = dict(ARMS if arms is None else arms)
    if fixtures:
        cases = [c for c in cases if c[0] in fixtures]
    if only_arms:
        arms = {k: v for k, v in arms.items() if k in only_arms}
    ref_factory = ref_factory or _default_ref_runner

    feats_path = out / "features.json"
    feats = json.loads(feats_path.read_text(encoding="utf-8")) if feats_path.exists() else {}
    runners: dict[str, object] = {}
    closers: list = []
    ready = 0
    try:
        for name, path, width_mm, garment in cases:
            src_hash = _sha256(path)
            art = out / "renders" / f"{name}__art.png"
            sources = feats.setdefault("__sources__", {})
            if not art.exists() or sources.get(name) != src_hash:
                _normalise_art(Path(path), art)
                sources[name] = src_hash
            for arm, kw in [(BASE, {})] + list(arms.items()):
                dpath = out / "designs" / f"{name}__{arm}.json"
                rpath = out / "renders" / f"{name}__{arm}.jpg"
                row = feats.get(name, {}).get(arm)
                if (row and "error" not in row
                        and row.get("source_sha256") == src_hash
                        and row.get("schema") == FEATURES_SCHEMA
                        and dpath.exists() and rpath.exists()):
                    _say(f"[{name} / {arm}] cached")
                    ready += 1
                    continue
                _say(f"[{name} / {arm}] digitizing...")
                started = time.time()
                try:
                    if "__ref__" in kw:
                        commit = kw["__ref__"]
                        if commit not in runners:
                            runner, closer = ref_factory(commit)
                            runners[commit] = runner
                            closers.append(closer)
                        design = runners[commit](path, width_mm, garment, STUDIO_MAX_COLORS)
                        row = features_design_only(path, design)
                        row["design_only"] = True
                    else:
                        cfg = base_cfg(width_mm, garment, **kw)
                        gen, result, plan, design = digitize_once(path, cfg)
                        row = features_full(path, cfg, gen, result, plan, design)
                        row["design_class"] = result.design_class
                except Exception as exc:  # noqa: BLE001 - one bad arm must not
                    # take the other hundred down; it is recorded and dropped.
                    feats.setdefault(name, {})[arm] = {"error": f"{type(exc).__name__}: {exc}"}
                    _write_json(feats_path, feats)
                    _say(f"[{name} / {arm}] FAILED: {type(exc).__name__}")
                    continue
                row["wall_s"] = round(time.time() - started, 1)
                row["source_sha256"] = src_hash
                row["schema"] = FEATURES_SCHEMA
                dpath.write_text(json.dumps(design), encoding="utf-8")
                cv2.imwrite(str(rpath), render_design(design, px_per_mm=VIEW_PX_PER_MM),
                            [cv2.IMWRITE_JPEG_QUALITY, 92])
                feats.setdefault(name, {})[arm] = row
                _write_json(feats_path, feats)          # checkpoint per arm
                ready += 1
    finally:
        for closer in closers:
            closer()
    print(f"{ready} arm-runs ready in {out}. Next: python -m tools.eye_pairs --pair")
    return ready


def pair(out=OUT) -> int:
    """Build the sitting from every rendered arm; -> the pair count.

    The identity of a sitting is the SEALED map — what each opaque id
    actually shows. `sitting.json` records its hash, and once picks exist
    this refuses to build anything but the same map: a guard that compared
    the public lists could not see an arm swap at equal count, and skipped
    itself entirely when pairs.json was missing (review finding 2,
    2026-09-17, both halves shown empirically).
    """
    out = Path(out)
    feats = json.loads((out / "features.json").read_text(encoding="utf-8"))
    runs = []
    for name, by_arm in feats.items():
        if name == "__sources__":
            continue
        for arm, row in by_arm.items():
            dpath = out / "designs" / f"{name}__{arm}.json"
            if "error" in row or not dpath.exists():
                continue
            runs.append(ArmRun(name, arm,
                               design_hash(json.loads(dpath.read_text(encoding="utf-8"))),
                               design_only=bool(row.get("design_only", False))))
    public, sealed, skipped = build_pairs(runs)
    new_hash = sealed_hash(sealed)

    picks_log, sitting = out / "picks.jsonl", out / "sitting.json"
    if picks_log.exists() and picks_log.stat().st_size:
        if not sitting.exists():
            raise SystemExit("REFUSED: picks.jsonl holds picks but sitting.json is missing, "
                             "so nothing proves they belong to the pair set about to be "
                             "built. Move the picks aside or restore sitting.json.")
        old_hash = json.loads(sitting.read_text(encoding="utf-8")).get("sealed_sha256")
        if old_hash != new_hash:
            raise SystemExit("REFUSED: picks.jsonl already holds picks for a different "
                             "pair set (sealed map changed). Move it aside before "
                             "rebuilding, or the picks would be read against the wrong "
                             "pictures.")

    img = out / "img"
    shutil.rmtree(img, ignore_errors=True)
    img.mkdir()
    for p in public:
        s = sealed[p["pair"]]
        shutil.copyfile(out / "renders" / f"{s['fixture']}__{s['left_arm']}.jpg", img / p["left"])
        shutil.copyfile(out / "renders" / f"{s['fixture']}__{s['right_arm']}.jpg", img / p["right"])
        shutil.copyfile(out / "renders" / f"{s['fixture']}__art.png", img / p["art"])
    _write_json(out / "pairs.json", public)
    _write_json(out / "arms.json", sealed)
    _write_json(out / "skipped.json", skipped)
    _write_json(sitting, {"sealed_sha256": new_hash, "n_pairs": len(public),
                          "built_ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    print(f"{len(public)} pairs ready in {out}. Next: python -m tools.eye_pairs --serve")
    return len(public)


def serve(out=OUT, port: int = PORT, open_browser: bool = True) -> int:
    httpd = make_server(out, port=port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"Picker at {url}  (Ctrl+C to stop; picks are already on disk)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def reveal(out=OUT) -> dict:
    out = Path(out)
    public = json.loads((out / "pairs.json").read_text(encoding="utf-8"))
    sealed = json.loads((out / "arms.json").read_text(encoding="utf-8"))
    feats = json.loads((out / "features.json").read_text(encoding="utf-8"))
    skipped = json.loads((out / "skipped.json").read_text(encoding="utf-8"))
    picks = load_picks(out / "picks.jsonl")
    ids = [p["pair"] for p in public]
    unknown = sorted(set(picks) - set(ids))
    if unknown:
        raise SystemExit(f"REFUSED: picks name pairs that do not exist: {', '.join(unknown)}")
    missing = unpicked(ids, picks)
    if missing:
        raise SystemExit(f"REFUSED: {len(missing)} of {len(ids)} pairs have no pick yet "
                         f"(first: {missing[0]}). Every pair is picked before any score is read.")

    flag_rows = an.decided_rows(sealed, picks, ref=False)
    ref_rows = an.decided_rows(sealed, picks, ref=True)
    primary, descriptive, clause, per_fx = [], [], {}, {}
    for metric, direction in an.METRICS.items():
        if direction == "none":
            descriptive.append(an.lean(flag_rows, feats, metric))
            continue
        primary.append({"metric": metric,
                        "headline": an.sign_agreement(flag_rows, feats, metric),
                        "all_pairs": an.sign_agreement(flag_rows, feats, metric,
                                                       include_refused=True)})
        clause[metric] = an.exit_clause(flag_rows, feats, metric)
        per_fx[metric] = an.per_fixture_sign(flag_rows, feats, metric)

    table = an.flag_table(sealed, picks)
    ref_table = []
    for r in ref_rows:
        # The ref worktree has no rembg venv, so a photo-class fixture's old
        # arm skipped photo prep for an ENVIRONMENT reason, not an engine one.
        confounded = feats.get(r["fixture"], {}).get(BASE, {}).get("design_class") in PHOTO_CLASSES
        ref_table.append({"pair": r["pair"], "fixture": r["fixture"], "arm": r["arm"],
                          "today_won": not r["picked_is_arm"], "confounded": confounded})

    results = {
        "n_pairs": len(ids), "decided_flag_pairs": len(flag_rows),
        "ceiling": an.ceiling(sealed, picks), "controls": an.controls(sealed, picks),
        "primary": primary, "descriptive": descriptive, "exit_clause": clause,
        "per_fixture": per_fx, "flag_table": table, "ref_table": ref_table,
        "exploratory": an.exploratory_fit(flag_rows, feats), "skipped": skipped,
    }
    _write_json(out / "results.json", results)
    _print(results)
    return results


def _print(res: dict) -> None:
    c, k = res["ceiling"], res["controls"]
    print("=" * 78)
    print(f"EYE PAIRS - {res['n_pairs']} pairs, {res['decided_flag_pairs']} decided flag pairs")
    print("=" * 78)
    share = "n/a" if c["share"] is None else f"{c['share']:.2f}"
    print(f"CEILING  Kent agrees with himself on {c['consistent']}/{c['n']} repeats ({share})")
    if k["left_share_all"] is not None and abs(k["left_share_all"] - 0.5) > 0.15:
        print(f"WARNING  left-share over all decided picks is {k['left_share_all']:.2f} - a side habit")
    print(f"CONTROLS identical pairs: n={k['identical_n']} tie rate={k['identical_tie_rate']}")
    print()
    print("PRIMARY - agreement above the chance floor pe (from the observed marginals;")
    print("kappa_m = (a-pe)/(1-pe), 0 = chance). 2a-1 is the pre-registered figure,")
    print("right only when pe = 0.5. 'fixtures' = fixtures where the metric agrees")
    print("with the majority of that fixture's pairs / fixtures scored: nine fixtures")
    print("are the real n. Headline excludes refused pairs; all-pairs beside it.")
    print(f"{'metric':<22}{'n':>4}{'a':>6}{'pe':>6}{'kappa_m':>8}{'2a-1':>6}"
          f"{'95% CI on a':>14}  {'verdict':<12}{'fixtures':>9}{'all n':>6}{'k_m':>6}")
    per_fx = res.get("per_fixture", {})
    for row in res["primary"]:
        h, a = row["headline"], row["all_pairs"]

        def f(v, spec="+.2f"):
            return "n/a" if v is None else format(v, spec)

        pf = per_fx.get(row["metric"], {})
        fx = f"{pf.get('agree', 0)}/{len(pf.get('fixtures', {}))}"
        ci = "[%.2f, %.2f]" % (h["lo"], h["hi"])
        flag = " skew" if h.get("skewed") else ""
        print(f"{row['metric']:<22}{h['n']:>4}{f(h['a'], '.2f'):>6}{f(h['pe'], '.2f'):>6}"
              f"{f(h['kappa_marginal']):>8}{f(h['kappa']):>6}{ci:>14}  "
              f"{h['verdict']:<12}{fx:>9}{a['n']:>6}{f(a['kappa_marginal']):>6}{flag}")
    print()
    print("DESCRIPTIVE - no direction; how often Kent picked the HIGHER value")
    for d in res.get("descriptive", []):
        print(f"  {d['metric']:<14} picked higher on {d['picked_higher']} of {d['n']} differing pairs")
    print()
    print("EXIT CLAUSE - pairs where Kent picked the arm a metric scores WORSE")
    for metric, rows in res["exit_clause"].items():
        if rows:
            print(f"  {metric}: " + ", ".join(f"{r['pair']}({r['fixture']}/{r['arm']})" for r in rows))
    print()
    print("FLAG TABLE - arm vs shipped (wins = Kent picked the arm). Evidence, not a flip.")
    skips: dict[str, int] = {}
    for s in res["skipped"]:
        skips[s["arm"]] = skips.get(s["arm"], 0) + 1
    for arm in sorted(set(res["flag_table"]) | set(skips)):
        t = res["flag_table"].get(arm, {"wins": 0, "losses": 0, "ties": 0})
        print(f"  {arm:<20} W{t['wins']:>3}  L{t['losses']:>3}  T{t['ties']:>3}"
              f"   identical to shipped on {skips.get(arm, 0)} fixture(s)")
    for arm in sorted({r["arm"] for r in res["ref_table"]}):
        rows = [r for r in res["ref_table"] if r["arm"] == arm]
        won = sum(1 for r in rows if r["today_won"])
        print(f"\nTODAY vs {arm}: today preferred on {won} of {len(rows)} decided"
              + (" (photo-class fixtures are environment-confounded; see results.json)"
                 if any(r["confounded"] for r in rows) else ""))
    fit = res["exploratory"]
    print("\nEXPLORATORY fit: " + ("not run (fewer than 40 decided pairs)" if fit is None else
          f"LOFO accuracy {fit['lofo_accuracy']:.2f} vs best single "
          f"{fit['best_single']['metric']} {fit['best_single']['accuracy']:.2f} (n={fit['n']})"))


def verify(image, width_mm: float, garment: str) -> bool:
    """Drift control: the numbers this tool reads off a held plan must equal
    what each instrument reports when it digitizes for itself."""
    cfg = base_cfg(width_mm, garment)
    gen, result, plan, design = digitize_once(image, cfg)
    mine = features_full(image, cfg, gen, result, plan, design)
    lost = dropped_elements.analyse(image, cfg)
    edge = edge_smoothness.analyse(image, cfg)
    # The artfid family was the one metric family this tool composed by hand
    # rather than imported, and the one --verify did not check (review
    # finding 8, 2026-09-17). `score_image` digitizes for itself; that is the
    # point of a drift control.
    fid = score_image(image, cfg)
    checks = [("lost_elements", mine["lost_elements"], int(lost["lost"])),
              ("lost_frac", mine["lost_frac"], round(float(lost["lost_frac"]), 4)),
              ("unsewn_frac", mine["unsewn_frac"], round(float(lost["unsewn_frac"]), 4)),
              ("overshoot_frac", mine["overshoot_frac"],
               round(float(lost["overshoot_frac"]), 4)),
              ("ragged_mm", mine["ragged_mm"], round(float(edge["ragged_mm"]), 4)),
              ("hausdorff_mm", mine["hausdorff_mm"], round(float(edge["hausdorff_mm"]), 4)),
              ("artfid", mine["artfid"], fid["artfid"]),
              ("artfid_coverage", round(mine["artfid_coverage"], 3), fid["coverage"]),
              ("artfid_colour", round(mine["artfid_colour"], 3), fid["colour"]),
              ("artfid_structure", round(mine["artfid_structure"], 3), fid["structure"]),
              ("refusal", mine["refusals"].get("artfid"), fid["refusal"])]
    ok = True
    for name, a, b in checks:
        same = bool(a == b)          # numpy floats compare to np.bool_
        ok &= same
        print(f"  {name:<16} held={a!r:<12} own={b!r:<12} {'OK' if same else 'DRIFT'}")
    print("MATCH" if ok else "DRIFT - the held-plan path diverged from the instruments")
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--render", action="store_true",
                    help="digitize + render every arm (resumable; --fixtures/--arms scope it)")
    ap.add_argument("--pair", action="store_true",
                    help="build the sitting from every rendered arm; refuses over existing picks")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--reveal", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--fixtures", help="comma-separated corpus names, e.g. becker,fremont")
    ap.add_argument("--arms", help="comma-separated arm ids")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    split = lambda s: [x for x in s.split(",") if x] if s else None  # noqa: E731
    if args.render:
        render(args.out, fixtures=split(args.fixtures), only_arms=split(args.arms))
        return 0
    if args.pair:
        pair(args.out)
        return 0
    if args.serve:
        return serve(args.out, port=args.port, open_browser=not args.no_browser)
    if args.reveal:
        reveal(args.out)
        return 0
    if args.verify:
        name, path, width_mm, garment = corpus_cases()[1]      # "tires": the cheapest real logo
        print(f"verifying on {name}")
        return 0 if verify(path, width_mm, garment) else 1
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
