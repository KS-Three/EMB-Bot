"""Tabulate a `second_digitize_timing` run: one row per digitize, with queue
wait, run wall, run CPU (the worker thread's own), wall/CPU, per-stage wall,
and for a cancelled run how long the worker kept running after Cancel.

  python -m tools.second_digitize_report <runs-*.jsonl> <probe-*.jsonl>
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict

GROUPS = ["s0", "s1", "s1.5", "s2", "s3", "s4", "finish", "s5", "s6-7", "preflight"]


def group(label: str, prev: str | None) -> str:
    """The stage whose work ENDS at a seam with this label. A pipeline seam
    names the stage that just finished (`pipeline.py`: "each check names the
    stage that finished before it"); `finish_generation`, `plan_stitches`
    and the first `preflight` sit at the TOP of the next function, so the
    time before them belongs to what ran before."""
    m = re.match(r"stage (\d(?:\.\d+)?)", label)
    if m and m.group(1) in ("0", "1", "1.5", "2", "3", "4"):
        return "s" + m.group(1)      # incl. stage 2's k-means, stage 4's passes
    if label == "finish_generation":
        return "s4"                  # build_generation's tail (OCR, text)
    if label == "plan_stitches":
        return "finish"
    if label == "stage 5":
        return "s5"
    if label in ("preflight", "render"):
        return "preflight" if prev == "preflight" else "s6-7"
    return "s6-7"                    # per-shape seams inside stages 6-7


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main(runs_path: str, probe_path: str) -> None:
    raw = load(runs_path)
    runs = [r for r in raw if "run" in r]
    idles = [r["idle"] for r in raw if "idle" in r]
    ev = load(probe_path)
    # Per key: the non-cached submissions in order and the work spans in order.
    spans_by_key: dict[str, list] = defaultdict(list)
    worker_ev: dict[str, list] = defaultdict(list)
    open_span: dict[str, dict] = {}
    job_key = {}
    fresh_jobs_by_key: dict[str, list] = defaultdict(list)
    aborts = []
    for e in ev:
        if e["ev"] == "submit":
            job_key[e["job"]] = e["key"]
            if not e["cached"]:
                fresh_jobs_by_key[e["key"]].append(e["job"])
        elif e["ev"] == "work_start":
            open_span[e["th"]] = {"key": e["key"], "t0": e["t"], "c0": e["cpu"],
                                  "p0": e.get("pcpu"), "chk": []}
        elif e["ev"] == "work_end":
            sp = open_span.pop(e["th"])
            sp.update(t1=e["t"], c1=e["cpu"], p1=e.get("pcpu"), ok=e["ok"])
            spans_by_key[sp["key"]].append(sp)
        elif e["ev"] in ("chk", "abandon"):
            sp = open_span.get(e["th"])
            if sp is not None:
                sp["chk"].append(e)
            elif e["s"] != "the queue":             # read just before the work starts
                worker_ev[e["th"]].append(e)        # /recount or /classify threads
    span_of_job = {}
    for key, jobs in fresh_jobs_by_key.items():
        for jid, sp in zip(jobs, spans_by_key.get(key, [])):
            span_of_job[jid] = sp

    hdr = ["run", "state", "queue_s", "run_wall_s", "run_cpu_s", "wall/cpu", "probe_cores",
           "machine_cores", "others_cores", "busy_at_start", "freed_after_cancel_s",
           "gen_cache"] + GROUPS
    print("\t".join(hdr))
    for r in runs:
        sp = None if r.get("cached") else span_of_job.get(r["job"])
        row = {"run": r["run"], "state": r["state"]}
        m = r.get("machine") or {}
        row["busy_at_start"] = m.get("busy_cores", "")
        row["machine_cores"] = r.get("machine_busy_cores_during", "")
        row["gen_cache"] = r.get("generation_cache", "")
        if r.get("cached"):
            row["queue_s"] = 0
            row["run_wall_s"] = r["t_end"]
            row["state"] = "cached"
        if sp:
            row["queue_s"] = round(sp["t0"] - r["t_submit_mono"], 2)
            row["run_wall_s"] = round(sp["t1"] - sp["t0"], 2)
            row["run_cpu_s"] = round(sp["c1"] - sp["c0"], 2)
            row["wall/cpu"] = round((sp["t1"] - sp["t0"]) / max(1e-6, sp["c1"] - sp["c0"]), 2)
            if sp.get("p1") is not None:
                pc = (sp["p1"] - sp["p0"]) / max(1e-6, sp["t1"] - sp["t0"])
                row["probe_cores"] = round(pc, 2)
                if row["machine_cores"] not in ("", None):
                    row["others_cores"] = round(row["machine_cores"] - pc, 2)
            stage_wall = defaultdict(float)
            g, t_prev = None, sp["t0"]
            for e in sp["chk"]:
                g = group(e["s"], g)
                stage_wall[g] += e["t"] - t_prev
                t_prev = e["t"]
            # After the last seam: the rest of the preflight on a finished
            # run; on a cancelled one the time from the seam that raised to
            # the end of the work is ~0.
            stage_wall["preflight" if g == "preflight" else (g or "s0")] += sp["t1"] - t_prev
            for g in GROUPS:
                row[g] = round(stage_wall[g], 2) if g in stage_wall else ""
            if r.get("t_cancel_sent") is not None:
                row["freed_after_cancel_s"] = round(
                    sp["t1"] - (r["t_submit_mono"] + r["t_cancel_sent"]), 2)
                ab = [e for e in sp["chk"] if e["ev"] == "abandon"]
                if ab:
                    row["state"] += f" @{ab[0]['s']}"
        print("\t".join(str(row.get(h, "")) for h in hdr))
    for i in idles:
        print(f"{i['run']}: probe {i['probe_cores']} cores over 3 s, inflight {i['inflight']}, "
              f"threads {i['threads']}")
    if worker_ev:
        print("\nnon-worker threads that hit stage seams (recount/classify):")
        for th, es in worker_ev.items():
            print(f"  {th}: {len(es)} seam events, {es[0]['t']:.1f}..{es[-1]['t']:.1f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
