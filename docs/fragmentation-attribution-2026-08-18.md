# Fragmentation and trims — unit error, and a measured mechanism (2026-08-18)

Detail behind `MASTER_SCOPE.md` live defect 4. Two separate things: the
headline was measured in the wrong unit, and the cause it recorded as
undiagnosed now has a mechanism.

**Provenance warning up front.** The new measurements here were taken in the
SHARED checkout, not a pinned worktree. `MASTER_SCOPE.md`'s own gotchas and
`docs/handoff-2026-08-16.md` §1 both require a pinned worktree for parity
numbers — three baselines died mid-run on 2026-08-15 for exactly this reason.
**Treat every number below as directional and re-measure before quoting one.**

## 1. "129 runs vs the pro's 15" compared two different objects

- **129** was `plan.iter_runs()` — plan OBJECTS. One per fill, satin, underlay
  or travel segment.
- **15** was the pro's THREAD PATHS, cut at JUMP / TRIM / STOP.

Travel is thread-down, so the machine sews straight through it and one path
swallows however many plan objects it was assembled from. The harness already
knows this. `digitizer/tools/pro_parity/prep_all.py:233-251`, verbatim:

> A `StitchPlan` run is a PLAN OBJECT ... A decoded run is a THREAD PATH ...
> The two counts are not the same measurement and were never comparable

with its own worked figures:

```
becker_hat_small   pro 13 runs   ours 290 plan objects   ours 35 paths
becker_beanie      pro 14 runs   ours 241 plan objects   ours 37 paths
```

The field was renamed `plan_runs` in the same change (`prep_all.py:700-702`):
*"it never meant what the pro side's `runs` meant ... Anything comparing the
two files must read `runs`."*

**Why it never reached the docs.** The fix is `da42947` (2026-08-15) — one of
the four commits `docs/handoff-2026-08-16.md:122-124` records as belonging to a
parallel session. `plan_runs` and `run_breaks` appear in zero markdown files in
this repo; the correction existed only in a Python docstring.

**Two traps when quoting a replacement number.**

1. `35 paths vs 13` is `becker_hat_small`. The `129 vs 15` headline is
   `becker_marine_logo` at 76.5 mm `left_chest` — a different design. The
   like-for-like path count for the headline design has not been measured.
2. Re-running the headline's own repro
   (`docs/becker-pro-parity-2026-08-15.md:91-101`) suggests the plan-run count
   has moved with the engine since 2026-08-15 while the trim rate has not.

**The durable statement is the trim rate: 8.49/1k against the pro's 1.27.**
That is separately measured and is unaffected by the unit error. Quote it, and
stop quoting run counts until one is measured in the pro's unit in a worktree.

## 2. Mechanism: `_graph_travel` never returns a path

`digitizer/README.md:316-322` describes a needle-down travel-graph walk as
shipped — "the corpus trick behind 740-stitch runs and 0.8 trims per 1000". It
does not fire.

Measured across flat designs: **0 successful returns out of 57 calls.**

Root cause is in the snap. `_graph_travel`'s `snap()`
(`digitizer/digitizer_core/stage6_satin.py:2145`) uses a fixed tolerance:

```python
def snap(p):
    best, bd = None, 0.8
```

The graph's nodes are *spine* endpoints (`_build_travel_graph`,
`stage6_satin.py:2084-2134`). The cursor at that moment is the end of the
previous satin **column** — a rail point, off-spine by roughly half-width plus
the cap extension. The tolerance is not scaled to the stroke's half-width, so
on strokes meaningfully wider than 0.8 mm the cursor cannot snap at all. The
target end snaps fine; it is the cursor that fails.

Consequence: every inter-stroke hop lifts, and every hop past `trim_at_mm`
becomes a trim. On the Becker measurement none of the trimmed hops were cut by
the "path leaves the shape" rule — all were pure `d > trim_at_mm`.
`.claude/memory/pro-trim-threshold.md` records the professional floating well
past that distance uncut, so distance alone is not the pro's decision variable
either.

**No test references `_graph_travel` or `_build_travel_graph`** (grepped over
`digitizer/tests/`). This is the failure class `conventions-memory.md` already
names: a module can be committed, imported and documented and still never
execute.

### Honest limit

Fixing the snap is necessary, not proven sufficient. In the calls where both
ends *did* snap, the walk still returned nothing — separate glyphs are
genuinely disconnected components, and legs over already-sewn strokes are
forbidden by design. **Size the recovery before promising it.**

### Gate status

No ROADMAP hard gate applies. It is not a default-OFF tier (gate 3 covers
chaining, contour, tonal splitting) and it does not set a physical constant
(gate 1 covers `trim_at_mm`; the point here is to avoid needing the hop, not to
retune the threshold). It **will** move `test_flat_lane_byte_identical` and
stroke-level goldens, so it needs the same-failure-set discipline and Kent's
re-capture call — on Linux CI, never Windows.

## 3. The attribution instrument already exists and has never been read

`prep_all.py:709` (ours) and `:790` (the pro's) each write a `run_breaks`
histogram labelling every run boundary `start` / `color` / `trim` / `jump` /
`hop`, both sides decoded by the same function (`prep_all.py:149-162`). Reader:
`machine_meta` at `prep_all.py:754-759`. Per-block plan detail rides alongside
as `plan_runs_by_kind` (`prep_all.py:732-733`).

That is a direct attribution of fragmentation cause, and it is a read rather
than a build — run `prep_both.py`, diff the two dicts:

| dominant break kind | implicated mechanism |
|---|---|
| `trim` | chaining / `trim_at_mm` — see the latent `chain_links` entry |
| `hop` | `travel_path` giving up (`stage6_fill.py:558` budget, `:467` ring cap) — and §2 above |
| `color` | block structure and sequencing |

The three are mutually exclusive and the file already distinguishes them.
`docs/becker-pro-parity-2026-08-15.md:113` closed with "why fragmentation
happens ... is the next piece of work", written the same day the field landed.

## What to do with this

1. Re-measure the Becker repro in a pinned worktree, recording `runs` (paths),
   `plan_runs`, and `run_breaks` for both sides.
2. Read the `run_breaks` diff before writing any fix — it says whether §2 is
   the whole story or one of three contributors.
3. Only then size the `_graph_travel` snap fix.
