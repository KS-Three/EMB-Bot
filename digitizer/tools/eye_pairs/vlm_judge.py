"""Claude as the eye: does a vision model's BLIND pick agree with Kent's?

The judge test behind `docs/eye-pairs-2026-11-04/vlm-judge/PRE-REGISTRATION.md`
(committed before any call was made; a test pins this module's prompt and
settings to that file). It reads the one sitting whose renders survive,
`pro-lettering-1102` (64 pairs: 56 live, 4 identical, 4 repeat), shows a
vision model exactly the three files Kent saw per pair (ARTWORK, LEFT, RIGHT:
`img/P###_art.png`, `img/P###_L.jpg`, `img/P###_R.jpg`) and asks for L / R /
tie. Every pair is asked twice: order A as Kent saw it, order B with LEFT and
RIGHT swapped, so a side habit shows up as disagreement with itself.

    python -m tools.eye_pairs.vlm_judge run --kit <eye_pairs_out/pro-lettering-1102> \
        --model claude-opus-5-5 [--orders A,B] [--key-file <path>] [--limit N]
    python -m tools.eye_pairs.vlm_judge analyse [--out <dir>]

`run` appends one JSON line per call to `<out>/verdicts-<model>.jsonl` and is
resumable (a (pair, order) already on file is skipped). It needs the
`anthropic` package and a key (`ANTHROPIC_API_KEY`, or `--key-file`); nothing
else in this module does. `analyse` reads the committed sitting files
(`arms.json`, `picks.jsonl`, `manifest.json`, `sitting-inputs.json`) plus the
verdicts and writes `analysis.json` + `analysis.md`: Cohen's kappa (3-way
linear-weighted with ties; 2x2 on the pairs both decided), 95% percentile
bootstrap over pairs and over designs, the repo's own `pooled.reading` rule,
and the controls. **No raw agreement figure is computed** (ROADMAP gate 4).
This tool judges nothing about the engine and flips nothing.

The judge never sees a pair id, an arm name, a flag, or Kent's pick.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
DIGITIZER = HERE.parents[2]
REPO = DIGITIZER.parent
SITTING = REPO / "docs" / "eye-pairs-2026-11-02" / "pro-size-lettering"
OUT = REPO / "docs" / "eye-pairs-2026-11-04" / "vlm-judge"
KIT = DIGITIZER / "eye_pairs_out" / "pro-lettering-1102"

#: $ per million tokens (input, output) - the claude-api skill's table, cached 2026-10-06.
RATES = {"claude-opus-5-5": (4.00, 20.00), "claude-haiku-5-5": (0.10, 0.50)}
EFFORT = "medium"
MAX_TOKENS = 1500
ORDERS = ("A", "B")            # A = as Kent saw it; B = LEFT and RIGHT swapped
CHOICES = ("L", "R", "tie")
SIDES = ("before", "tie", "after")   # the order the weighted kappa uses (pooled.SIDES)

#: The one pre-registered prompt. Its sha256 is pinned in PRE-REGISTRATION.md;
#: a prompt change after a run is a different experiment, not a re-run.
PROMPT = (
    "You are standing in for an experienced embroidery digitizer at a blind sitting.\n"
    "Three images follow: the customer's ARTWORK, then two machine-embroidery stitch "
    "simulations of it, LEFT and RIGHT, made by two versions of the same digitizing "
    "engine. They may be identical.\n"
    "Judge them the way a digitizer judges a sew-out before it goes on the garment, "
    "and pick the one you would rather sew and hand to the customer. If you cannot "
    "tell them apart, or neither is better, answer tie.\n"
    "Answer as JSON only: {\"choice\": \"L\" | \"R\" | \"tie\", \"confidence\": 1-5, "
    "\"reason\": \"at most 40 words\"}."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "choice": {"type": "string", "enum": list(CHOICES)},
        "confidence": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["choice", "confidence", "reason"],
    "additionalProperties": False,
}


def prompt_sha() -> str:
    return hashlib.sha256(PROMPT.encode("utf-8")).hexdigest()


def settings() -> dict:
    """What the pre-registration pins, in one place for the test to compare."""
    return {"prompt_sha256": prompt_sha(), "effort": EFFORT, "max_tokens": MAX_TOKENS,
            "orders": list(ORDERS), "models": sorted(RATES), "schema": SCHEMA}


# ----------------------------------------------------------------- frames ----

def frame_a(choice: str, order: str) -> str:
    """A judge's choice, mapped into the frame Kent saw (order A). In order B
    the files were swapped, so its L is Kent's R."""
    if choice == "tie" or order == "A":
        return choice
    return "R" if choice == "L" else "L"


def to_label(choice: str, sealed: dict) -> str | None:
    """L / R / tie in order-A frame -> before / tie / after through the sealed
    key (`base` is before, the arm is after). None for an identical pair,
    which has no before or after."""
    if sealed["left_arm"] == sealed["right_arm"]:
        return None
    if choice == "tie":
        return "tie"
    side = sealed["left_arm"] if choice == "L" else sealed["right_arm"]
    return "before" if side == "base" else "after"


# ------------------------------------------------------------------- run ----

def _b64(path: Path) -> tuple[str, str]:
    media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}[path.suffix.lower()]
    return media, base64.standard_b64encode(path.read_bytes()).decode("ascii")


def content_for(art: Path, left: Path, right: Path) -> list[dict]:
    blocks: list[dict] = [{"type": "text", "text": PROMPT}]
    for label, path in (("ARTWORK", art), ("LEFT", left), ("RIGHT", right)):
        media, data = _b64(path)
        blocks.append({"type": "text", "text": f"{label}:"})
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
    return blocks


def parse_verdict(text: str) -> dict:
    """The structured-output text block; a forgiving fallback for a stray
    code fence. Confidence outside 1-5 is kept as sent and flagged."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):t.rfind("}") + 1]
    data = json.loads(t)
    if data.get("choice") not in CHOICES:
        raise ValueError(f"choice not in {CHOICES}: {data.get('choice')!r}")
    c = data.get("confidence")
    data["confidence_in_range"] = isinstance(c, int) and 1 <= c <= 5
    return data


def _client(key_file: str | None):
    import anthropic  # the only place it is needed
    if key_file:
        return anthropic.Anthropic(api_key=Path(key_file).read_text(encoding="utf-8").strip())
    return anthropic.Anthropic()


def judge_once(client, model: str, blocks: list[dict], *, effort: str = EFFORT,
               max_tokens: int = MAX_TOKENS, tries: int = 6) -> dict:
    """One blind call. No `fallbacks`: a fallback model is a different
    instrument, so a refusal is recorded as a refusal. No `system`, no
    `temperature` (rejected on these models), thinking left at the model's
    adaptive default; `effort` is the pre-registered knob."""
    import anthropic
    delay = 5.0
    for attempt in range(1, tries + 1):
        t0 = time.perf_counter()
        try:
            resp = client.messages.create(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": blocks}],
                output_config={"effort": effort,
                               "format": {"type": "json_schema", "schema": SCHEMA}},
            )
        except (anthropic.RateLimitError, anthropic.InternalServerError,
                anthropic.APIConnectionError) as e:
            if attempt == tries:
                raise
            print(f"  retry {attempt}: {type(e).__name__}; sleeping {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
            continue
        elapsed = time.perf_counter() - t0
        row = {"stop_reason": resp.stop_reason, "request_id": resp.id,
               "served_model": resp.model, "elapsed_s": round(elapsed, 2),
               "input_tokens": resp.usage.input_tokens,
               "output_tokens": resp.usage.output_tokens}
        if resp.stop_reason == "refusal":
            sd = getattr(resp, "stop_details", None)
            row.update(choice=None, confidence=None, reason=None,
                       refusal_category=getattr(sd, "category", None))
            return row
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        try:
            v = parse_verdict(text)
        except (ValueError, json.JSONDecodeError) as e:
            row.update(choice=None, confidence=None, reason=None,
                       parse_error=f"{type(e).__name__}: {e}", raw_text=text[:400])
            return row
        row.update(choice=v["choice"], confidence=v.get("confidence"), reason=v.get("reason"),
                   confidence_in_range=v["confidence_in_range"])
        return row
    raise RuntimeError("unreachable")


def load_kit(kit: Path) -> list[dict]:
    return json.loads((kit / "pairs.json").read_text(encoding="utf-8"))


def _done(path: Path) -> set[tuple[str, str]]:
    seen = set()
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                r = json.loads(raw)
                if r.get("choice") is not None or r.get("stop_reason") == "refusal":
                    seen.add((r["pair"], r["order"]))
    return seen


def run(a) -> int:
    kit = Path(a.kit)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pairs = load_kit(kit)
    if a.pairs:
        want = set(a.pairs.split(","))
        pairs = [p for p in pairs if p["pair"] in want]
    if a.limit:
        pairs = pairs[: a.limit]
    orders = tuple(o.strip() for o in a.orders.split(","))
    for o in orders:
        if o not in ORDERS:
            raise SystemExit(f"order must be one of {ORDERS}: {o!r}")
    log = out / f"verdicts-{a.model}.jsonl"
    done = _done(log)
    client = _client(a.key_file)
    sha = prompt_sha()
    todo = [(p, o) for p in pairs for o in orders if (p["pair"], o) not in done]
    print(f"{a.model}: {len(todo)} calls to make ({len(done)} already on file) -> {log}", flush=True)
    tin = tout = 0
    for i, (p, order) in enumerate(todo, 1):
        left, right = kit / "img" / p["left"], kit / "img" / p["right"]
        if order == "B":
            left, right = right, left
        blocks = content_for(kit / "img" / p["art"], left, right)
        row = judge_once(client, a.model, blocks, effort=a.effort)
        row.update(pair=p["pair"], order=order, model=a.model, effort=a.effort,
                   prompt_sha256=sha, ts=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        if row.get("choice") is not None:
            row["choice_frame_a"] = frame_a(row["choice"], order)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        tin += row["input_tokens"]
        tout += row["output_tokens"]
        print(f"  {i}/{len(todo)} {p['pair']} {order}: {row.get('choice')} "
              f"c{row.get('confidence')} {row['elapsed_s']}s "
              f"in {row['input_tokens']} out {row['output_tokens']}", flush=True)
    rate = RATES.get(a.model)
    cost = (tin * rate[0] + tout * rate[1]) / 1e6 if rate else None
    print(json.dumps({"model": a.model, "calls": len(todo), "input_tokens": tin,
                      "output_tokens": tout, "usd_this_run": None if cost is None else round(cost, 3)}))
    return 0


# --------------------------------------------------------------- analyse ----

def load_sitting(sitting: Path = SITTING) -> dict:
    from tools.eye_pairs.pairs import load_picks
    sealed = json.loads((sitting / "arms.json").read_text(encoding="utf-8"))
    picks = {k: v["choice"] for k, v in load_picks(sitting / "picks.jsonl").items()}
    man = json.loads((sitting / "manifest.json").read_text(encoding="utf-8"))
    design_of = {lg["name"]: lg["design"] for lg in man["logos"]}
    passing = sorted(n for n, m in man["manipulation"].items() if m.get("passes"))
    inputs = json.loads((sitting / "sitting-inputs.json").read_text(encoding="utf-8"))
    expected = {p["id"]: p["expected_label"]
                for s in inputs["sittings"].values() for p in s["pairs"]}
    return {"sealed": sealed, "picks": picks, "design_of": design_of,
            "passing_arms": passing, "expected": expected}


def load_verdicts(out: Path) -> dict[str, dict[str, dict[str, dict]]]:
    """model -> order -> pair -> the LAST usable row (a resumed run may hold
    an earlier parse failure for the same key)."""
    by: dict[str, dict[str, dict[str, dict]]] = {}
    for path in sorted(out.glob("verdicts-*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            r = json.loads(raw)
            by.setdefault(r["model"], {}).setdefault(r["order"], {})[r["pair"]] = r
    return by


def _kappas(rows: list[tuple[str, str, str]], seed: int = 20261104) -> dict:
    """rows = (kent_label, judge_label, design). Three-way linear-weighted
    kappa with ties, 2x2 on the pairs both decided, each with percentile
    intervals over pairs and over designs, and the repo's reading."""
    import numpy as np
    from tools.eye_pairs import pooled
    rng = np.random.default_rng(seed)
    res = {"n_scored": len(rows),
           "n_kent_decided": sum(1 for k, _, _ in rows if k != "tie"),
           "n_judge_decided": sum(1 for _, j, _ in rows if j != "tie"),
           "judge_silent_on_decided": sum(1 for k, j, _ in rows if k != "tie" and j == "tie")}
    if not rows:
        res.update(kappa_3way=None, reading_3way="n too small (<10)",
                   kappa_sides=None, reading_sides="n too small (<10)", n_decided=0)
        return res
    k3 = np.array([SIDES.index(k) for k, _, _ in rows], dtype=int)
    j3 = np.array([SIDES.index(j) for _, j, _ in rows], dtype=int)
    d3 = [d for _, _, d in rows]
    res["kappa_3way"] = pooled.kappa_from_table(pooled._table(k3, j3, 3), "linear")
    lo, hi, _ = pooled._boot(k3, j3, d3, 3, "linear", cluster=False, rng=rng)
    clo, chi, _ = pooled._boot(k3, j3, d3, 3, "linear", cluster=True, rng=rng)
    res.update(ci3_pairs=[lo, hi], ci3_designs=[clo, chi],
               reading_3way=pooled.reading(len(rows), (lo, hi), (clo, chi)))
    dec = [(k, j, d) for k, j, d in rows if k != "tie" and j != "tie"]
    res["n_decided"] = len(dec)
    k2 = np.array([0 if k == "before" else 1 for k, _, _ in dec], dtype=int)
    j2 = np.array([0 if j == "before" else 1 for _, j, _ in dec], dtype=int)
    res["kappa_sides"] = pooled.kappa_from_table(pooled._table(k2, j2, 2)) if dec else None
    lo, hi, _ = pooled._boot(k2, j2, [d for _, _, d in dec], 2, "none", cluster=False, rng=rng)
    clo, chi, _ = pooled._boot(k2, j2, [d for _, _, d in dec], 2, "none", cluster=True, rng=rng)
    res.update(ci2_pairs=[lo, hi], ci2_designs=[clo, chi],
               reading_sides=pooled.reading(len(dec), (lo, hi), (clo, chi)))
    table = [[0] * 3 for _ in SIDES]
    for k, j, _ in rows:
        table[SIDES.index(k)][SIDES.index(j)] += 1
    res["table_kent_rows_judge_cols"] = table
    return res


def analyse(sitting: dict, verdicts: dict[str, dict[str, dict[str, dict]]]) -> dict:
    sealed, picks = sitting["sealed"], sitting["picks"]
    design_of, expected = sitting["design_of"], sitting["expected"]
    passing = set(sitting["passing_arms"])
    live = sorted(p for p, s in sealed.items() if s["kind"] == "live")
    ident = sorted(p for p, s in sealed.items() if s["kind"] == "identical")
    repeats = {p: s["repeat_of"] for p, s in sealed.items() if s["kind"] == "repeat"}
    kent = {p: to_label(picks[p], sealed[p]) for p in sealed if p in picks and sealed[p]["kind"] != "identical"}
    out: dict = {"sitting": "pro-lettering-1102", "n_live": len(live),
                 "kent": {"identical_called_tie": sum(1 for p in ident if picks.get(p) == "tie"),
                          "identical_pairs": len(ident),
                          "repeat_consistent": sum(1 for p, o in repeats.items()
                                                   if picks.get(p) == picks.get(o)),
                          "repeat_pairs": len(repeats),
                          "left_picks": sum(1 for p in sealed if picks.get(p) == "L"),
                          "right_picks": sum(1 for p in sealed if picks.get(p) == "R"),
                          "ties_live": sum(1 for p in live if picks.get(p) == "tie")},
                 "passing_arms": sorted(passing), "models": {}}
    for model, by_order in sorted(verdicts.items()):
        m: dict = {"orders": {}, "cost": {}}
        tin = sum(r.get("input_tokens", 0) for o in by_order.values() for r in o.values())
        tout = sum(r.get("output_tokens", 0) for o in by_order.values() for r in o.values())
        rate = RATES.get(model)
        m["cost"] = {"calls": sum(len(o) for o in by_order.values()), "input_tokens": tin,
                     "output_tokens": tout,
                     "usd": None if rate is None else round((tin * rate[0] + tout * rate[1]) / 1e6, 3)}
        for order in ORDERS:
            rows_o = by_order.get(order, {})
            judge = {p: to_label(r["choice_frame_a"], sealed[p]) for p, r in rows_o.items()
                     if r.get("choice") is not None and sealed[p]["kind"] != "identical"}
            reads: dict = {}
            scope = {"live": live,
                     "passing_arms_only": [p for p in live if sealed[p]["right_arm"] in passing
                                           or sealed[p]["left_arm"] in passing]}
            for name, ids in scope.items():
                rows = [(kent[p], judge[p], design_of[sealed[p]["fixture"]])
                        for p in ids if p in judge and p in kent]
                reads[name] = _kappas(rows)
            rows = [(expected[p], judge[p], design_of[sealed[p]["fixture"]])
                    for p in live if p in judge and p in expected]
            reads["vs_kit_expected_label"] = _kappas(rows)
            dec_side = [r["choice"] for r in rows_o.values() if r.get("choice") in ("L", "R")]
            ctrl = {"answered": len(rows_o),
                    "refused": sum(1 for r in rows_o.values() if r.get("stop_reason") == "refusal"),
                    "unparsed": sum(1 for r in rows_o.values() if r.get("parse_error")),
                    "identical_called_tie": sum(1 for p in ident if rows_o.get(p, {}).get("choice") == "tie"),
                    "identical_answered": sum(1 for p in ident if p in rows_o),
                    "repeat_consistent": sum(1 for p, o in repeats.items()
                                             if p in rows_o and o in rows_o
                                             and rows_o[p].get("choice_frame_a") == rows_o[o].get("choice_frame_a")),
                    "repeat_answered": sum(1 for p, o in repeats.items() if p in rows_o and o in rows_o),
                    "left_picks_own_frame": dec_side.count("L"),
                    "right_picks_own_frame": dec_side.count("R"),
                    "ties_live": sum(1 for p in live if rows_o.get(p, {}).get("choice") == "tie"),
                    "mean_confidence": (round(sum(r["confidence"] for r in rows_o.values()
                                                  if isinstance(r.get("confidence"), int))
                                              / max(1, sum(1 for r in rows_o.values()
                                                           if isinstance(r.get("confidence"), int))), 2)
                                        if rows_o else None)}
            disagree = []
            for p in live:
                r = rows_o.get(p)
                if not r or r.get("choice") is None or p not in kent:
                    continue
                jl = judge[p]
                if kent[p] != "tie" and jl != "tie" and jl != kent[p]:
                    disagree.append({"pair": p, "fixture": sealed[p]["fixture"],
                                     "arm": sealed[p]["left_arm"] if sealed[p]["left_arm"] != "base" else sealed[p]["right_arm"],
                                     "kent": kent[p], "judge": jl,
                                     "confidence": r.get("confidence"), "reason": r.get("reason")})
            m["orders"][order] = {"reads": reads, "controls": ctrl, "opposite_side": disagree}
        a_rows, b_rows = by_order.get("A", {}), by_order.get("B", {})
        both = [p for p in sealed if p in a_rows and p in b_rows
                and a_rows[p].get("choice") is not None and b_rows[p].get("choice") is not None]
        m["swap"] = {"pairs_in_both_orders": len(both),
                     "same_verdict_after_swap": sum(1 for p in both
                                                    if a_rows[p]["choice_frame_a"] == b_rows[p]["choice_frame_a"]),
                     "side_flipped_with_swap": sum(1 for p in both
                                                   if a_rows[p]["choice"] in ("L", "R")
                                                   and a_rows[p]["choice"] == b_rows[p]["choice"])}
        out["models"][model] = m
    return out


def _f(v) -> str:
    return "n/a" if v is None else f"{v:+.2f}"


def _ci(v) -> str:
    return "n/a" if not v or v[0] is None else f"[{v[0]:+.2f}, {v[1]:+.2f}]"


def markdown(rep: dict) -> str:
    L = [f"# vlm-judge on {rep['sitting']}: analysis (kappa with 95% bootstrap intervals; n beside every figure)", "",
         "Chance-corrected throughout; no raw agreement figure exists here (ROADMAP gate 4). "
         "`before` = the base side, `after` = the arm. Order A is the sitting as Kent saw it; "
         "order B had LEFT and RIGHT swapped, mapped back into A's frame before scoring.", "",
         "## Kent's own controls on this sitting (the ceiling)", "",
         f"- identical pairs called a tie: {rep['kent']['identical_called_tie']} of {rep['kent']['identical_pairs']}",
         f"- repeat pairs answered the same: {rep['kent']['repeat_consistent']} of {rep['kent']['repeat_pairs']}",
         f"- sides: {rep['kent']['left_picks']} left, {rep['kent']['right_picks']} right; "
         f"{rep['kent']['ties_live']} of {rep['n_live']} live pairs tied", ""]
    for model, m in rep["models"].items():
        c = m["cost"]
        L += [f"## `{model}`", "",
              f"{c['calls']} calls, {c['input_tokens']:,} input tokens, {c['output_tokens']:,} output tokens, "
              f"about ${c['usd']} at the cached rate.", "",
              "| scope | order | n scored | n Kent decided | kappa ties in | CI pairs | CI designs | reading "
              "| n both decided | kappa sides only | CI pairs | CI designs | reading |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for order, o in m["orders"].items():
            for scope, r in o["reads"].items():
                L.append(f"| {scope} | {order} | {r['n_scored']} | {r['n_kent_decided']} | "
                         f"{_f(r.get('kappa_3way'))} | {_ci(r.get('ci3_pairs'))} | {_ci(r.get('ci3_designs'))} | "
                         f"{r.get('reading_3way')} | {r.get('n_decided', 0)} | {_f(r.get('kappa_sides'))} | "
                         f"{_ci(r.get('ci2_pairs'))} | {_ci(r.get('ci2_designs'))} | {r.get('reading_sides')} |")
        L += ["", "### Judge controls", "",
              "| order | answered | refused | unparsed | identical called tie | repeats answered the same "
              "| L / R in its own frame | ties on live | mean confidence |",
              "|---|---|---|---|---|---|---|---|---|"]
        for order, o in m["orders"].items():
            k = o["controls"]
            L.append(f"| {order} | {k['answered']} | {k['refused']} | {k['unparsed']} | "
                     f"{k['identical_called_tie']} of {k['identical_answered']} | "
                     f"{k['repeat_consistent']} of {k['repeat_answered']} | "
                     f"{k['left_picks_own_frame']} / {k['right_picks_own_frame']} | {k['ties_live']} | "
                     f"{k['mean_confidence']} |")
        s = m["swap"]
        L += ["", f"Swap: same verdict in both orders on {s['same_verdict_after_swap']} of "
              f"{s['pairs_in_both_orders']} pairs; picked the same SCREEN side after the swap "
              f"(a side habit) on {s['side_flipped_with_swap']}.", ""]
        for order, o in m["orders"].items():
            t = o["reads"]["live"].get("table_kent_rows_judge_cols")
            if t:
                L += [f"Order {order}, live pairs, Kent (rows) x judge (cols), before / tie / after:", "",
                      "| | before | tie | after |", "|---|---|---|---|"]
                for name, row in zip(SIDES, t):
                    L.append(f"| **{name}** | {row[0]} | {row[1]} | {row[2]} |")
                L.append("")
        dis = m["orders"].get("A", {}).get("opposite_side", [])
        L += [f"### Pairs where Kent chose a side and the judge (order A) chose the other: {len(dis)}", ""]
        for d in dis:
            L.append(f"- `{d['pair']}` {d['fixture']} / `{d['arm']}`: Kent {d['kent']}, judge {d['judge']} "
                     f"(confidence {d['confidence']}): {d['reason']}")
        L.append("")
    return "\n".join(L)


def do_analyse(a) -> int:
    out = Path(a.out)
    sitting = load_sitting(Path(a.sitting))
    verdicts = load_verdicts(out)
    if not verdicts:
        raise SystemExit(f"no verdicts-*.jsonl under {out}")
    rep = analyse(sitting, verdicts)
    (out / "analysis.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    (out / "analysis.md").write_text(markdown(rep), encoding="utf-8")
    brief = {model: {order: {scope: {"n": r["n_scored"], "kappa_3way": r.get("kappa_3way"),
                                     "reading": r.get("reading_3way")}
                             for scope, r in o["reads"].items()}
                     for order, o in m["orders"].items()}
             for model, m in rep["models"].items()}
    print(json.dumps(brief, indent=1))
    print(f"wrote {out / 'analysis.json'} and analysis.md")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ask the model about every pair, both orders")
    r.add_argument("--kit", default=str(KIT), help="the sitting's render directory (img/, pairs.json)")
    r.add_argument("--model", required=True, choices=sorted(RATES))
    r.add_argument("--effort", default=EFFORT)
    r.add_argument("--orders", default=",".join(ORDERS))
    r.add_argument("--out", default=str(OUT))
    r.add_argument("--key-file", default=None, help="file holding the API key (else ANTHROPIC_API_KEY)")
    r.add_argument("--pairs", default=None, help="comma-separated pair ids (pilot)")
    r.add_argument("--limit", type=int, default=0)
    r.set_defaults(fn=run)
    an = sub.add_parser("analyse", help="score the verdicts against Kent's picks")
    an.add_argument("--out", default=str(OUT))
    an.add_argument("--sitting", default=str(SITTING))
    an.set_defaults(fn=do_analyse)
    a = ap.parse_args(argv)
    if a.cmd == "run" and not a.key_file and not os.environ.get("ANTHROPIC_API_KEY"):
        print("no ANTHROPIC_API_KEY in the environment and no --key-file", file=sys.stderr)
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
