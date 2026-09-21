# The display revamp, and a fleet that outran its budget (2026-09-15/16)

Three PRs merged (`ccd0520` #491, `129ba4a` #492, `b3fd982` #493). Then ~886
agents were launched across six workflows and 783 of them were killed by a
session limit. Read the budget section before fanning out at scale.

## What shipped

**#492 — the plan's run structure now reaches the browser.** `StitchRun.role`
(`"" | "border" | "edge_cap"`, declared LAST so positional `StitchRun(points,
kind)` does not shift) plus `design["runs"]`: per-run spans
`{i0,i1,kind,shape,role,block}` indexed into the final stitches array.
Per-run, not per-stitch — becker is 6,833 stitches in 131 runs (52:1), Fremont
16,480 in 389 (42:1); measured payload cost +4.3% / +5.3%. Spans partition the
stitch records exactly; plan bytes unchanged (SHA-256 identical both fixtures,
no golden recaptured). Studio: per-kind thread rendering and a border readout
that reports what was SEWN rather than what was requested.

## The contract error that nearly shipped, and how it was caught

The brief given to three agents said `kind` is
`satin | fill | run | underlay | travel`. **`stitches.py` defines EIGHT** —
`underlay fill satin border bean run travel tie` — and the missing one was
`border`, the exact thread Kent complained he could not see. Built to the
five-kind list, a `kind: "border"` strand renders as ordinary stitching **with
a fully green suite.**

Two agents found it independently by reading `stitches.py` and driving the real
service instead of trusting the brief. **`kind` is an OPEN set; treat an unknown
kind as ordinary stitching rather than dropping it.** Related trap: a border's
bridge TRAVEL run carries `role="border"` (`stage6_border.py:833-836`), so a
role modifier must be exempt for `travel`/`underlay`/`tie` — otherwise a
connector the design hides lifts off the cloth and casts a border's shadow.

## Two findings that ARE verified

**1. The two DST encoders disagree, and it reaches customers on JEF/XXX/VP3.**
An oversized SEWN move splits into STITCHES in `src/dst.js` and into JUMPS via
pystitch. Thread becomes travel — the defect `src/dst.js` was fixed for on
2026-09-07, still live on the service path. Verified end to end:
  - `src/dst.js:238-249` — splits into stitches, "exp.js's identical loop has
    always split a stitch into STITCHES"
  - `digitizer_service/formats.py:104-112` — calls `pystitch.write_*` with no
    settings override
  - `pystitch/EmbEncoder.py:44-45` — `long_stitch_contingency` defaults to
    `CONTINGENCY_LONG_STITCH_JUMP_NEEDLE`
  - `app/src/lib/exporters.js:97` — `SERVICE_ONLY_FORMATS = {jef, xxx, vp3}`
**Identical bounds, identical size, different thread — so no round-trip
geometry check can see it.** A monogram exported as JEF gets jumps where the
same monogram as DST gets stitches. NOT FIXED.

**2. `digitizer/tools/revalidate_floor.py` is dead.** Its documented command
raises `TypeError: probe() got an unexpected keyword argument 'small_shapes'`
(`pipeline.py:710` passes it; the tool's probe signature predates it). Its
premise is also already closed: `revalidate_small_shapes` defaults True since
09-10, so the 200-vs-50 gap it exists to count is 50-vs-50. Third instance this
week of the `spool_remedy` class — a diagnostic that stops being a diagnostic
the moment the thing it diagnoses ships. NOT FIXED.

## The budget lesson — read this before fanning out

886 agents launched, 103 finished, **783 killed by a session limit**, ~16M
subagent tokens, two confirmed findings. The sweeps largely SUCCEEDED (158 raw
findings); it was the **verification tier that died**, leaving findings nobody
can stand behind.

The design error was specific: **three adversarial skeptics per finding turns
158 findings into 474 verification calls.** The fan-out is not the sweep count,
it is sweep × findings × verifiers, and it is unbounded at author time.

- **Verify with ONE skeptic; escalate to three only for what survives.**
- **Check the session budget BEFORE launching, not after.**
- Concurrency is capped per workflow at `min(16, nproc-2)` — **2 on this
  4-core box** — so many small workflows beat one large one. Load hit 19 on 4
  cores while CPU read 25-47%: load counts I/O-blocked work, and it is the
  number that predicts whether more agents help.

## Where the unfinished work is

- `claude/wip-six-lanes-unverified` (`b8d3673`) — ~670 lines from six lanes
  killed mid-task. **Unverified, do not merge as-is**; the commit message
  inventories each lane. Highest value: the `EDGE_CAP_APPLIED`-bills-a-dropped-
  cap fix, whose BUG is verified (`stage7_sequence` assigns `cap_cost` outside
  its `if not cap_dropped`) though the FIX is not.
- 158 unverified findings live in each workflow's `journal.jsonl`; every
  workflow can `resumeFromRunId` and replay cached sweeps, re-running only the
  dead verifiers.

## Also true, and cheap to rediscover the hard way

- **All four `scratch_*` dirs are ABSENT in a cloud container.** The 23-design
  pro corpus DOCTRINE cites is not here, and `tools/build-embf.mjs` cannot run
  at all without `scratch_ink/`. What IS committed:
  `digitizer/testdata/reference/` — five professional designs as `.dst` + `.pes`
  WITH their source `.jpg`.
- **The Agent tool's worktree isolation creates dirs under
  `.claude/worktrees/`** — the path CLAUDE.md says never to touch. They are the
  parallel lanes that rule protects, gitignored at `.gitignore:5`, and the
  harness cleans them.
- **Piping `git apply` into `head` reports head's exit code**, so a failed
  patch reads as applied and two lanes were silently dropped. Same trap
  CLAUDE.md records for `pytest | tail`. It is not pytest-specific — it is any
  pipeline whose last command is not the one you are testing.
