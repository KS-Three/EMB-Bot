# Fragmentation and trims — unit error, and a measured mechanism (2026-08-18)

Detail behind `MASTER_SCOPE.md` live defect 4. Two separate things: the
headline was measured in the wrong unit, and the cause it recorded as
undiagnosed now has a mechanism.

**Provenance, per section — they differ.** §4's corpus diff was run in the
pinned worktree `.claude/worktrees/parity-measure` at `751f205` and is the
quotable one. §2's `_graph_travel` counts were taken in the SHARED checkout,
which `MASTER_SCOPE.md`'s gotchas and `docs/handoff-2026-08-16.md` §1 both
forbid for parity numbers — three baselines died mid-run on 2026-08-15 for
exactly that reason. **Treat §2's numbers as directional; re-measure before
quoting one.**

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

**Superseded by §4 — read that before quoting anything.** This section
originally concluded that the trim RATE (8.49/1k against the pro's 1.27) was
the durable half. The 2026-08-18 corpus run did not reproduce either side of
that figure. §4 has the like-for-like replacement: **we trim 3.1x as often as
the pro**, same decoder, same 23 designs.

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

`prep_all.py:731` (ours) and `:812` (the pro's) each write a `run_breaks`
histogram labelling every run boundary `start` / `color` / `trim` / `jump` /
`hop`, both sides decoded by the same function (`prep_all.py:149-162`).
Per-block plan detail rides alongside as `plan_runs_by_kind`.

**Run `prep_all.py`, not `prep_both.py`.** `prep_both` builds its own `pro`
block and omits `run_breaks`, so it cannot produce this diff — confirmed the
hard way 2026-08-18. It is a read rather than a build:

| dominant break kind | implicated mechanism |
|---|---|
| `trim` | chaining / `trim_at_mm` — see the latent `chain_links` entry |
| `hop` | *only meaningful for THIRD-PARTY files.* A `hop` is a break inferred from distance where the file carries no explicit record (`prep_all.py:221`). Our writer always emits explicit records, so our `hop` is structurally 0 and can never implicate `travel_path`. Do not read our 0 as evidence either way. |
| `color` | block structure and sequencing |

The three are mutually exclusive and the file already distinguishes them.
`docs/becker-pro-parity-2026-08-15.md:113` closed with "why fragmentation
happens ... is the next piece of work", written the same day the field landed.

## 4. MEASURED 2026-08-18 — the diff, and the number that replaces the headline

Run in the pinned worktree `.claude/worktrees/parity-measure` at `751f205`,
`prep_all.py` over all 23 designs, `PRO_PARITY_ROOT` on the Drive copy. Both
sides decoded by the same `decode()`, so this IS like-for-like.

| | PRO | OURS | ratio |
|---|---|---|---|
| thread paths (`runs`) | 1,054 | 2,103 | **2.0x** |
| `trim` breaks | 555 | **1,715** | **3.1x** |
| `jump` breaks | 0 | 292 | — |
| `hop` breaks | 368 | 0 | — |
| `color` breaks | 121 | 73 | — |

**Read the jump/hop split as an artifact, not a finding.** The pro's files pair
every jump with a trim, so precedence labels it `trim` and leaves `jump` at 0;
their remaining breaks carry no explicit record and fall to `hop`. Ours always
emit explicit jump records, so our `hop` is structurally 0. Summed, the
mechanical (non-cut) breaks are comparable: pro 368, ours 292.

**The whole gap is thread cuts. We trim 3.1x as often as the professional.**
Use that. Same unit, same decoder, 23 designs.

**Use `run_breaks['trim']`, NEVER the raw `trims` count, when comparing sides.**
The raw counts are not commensurable: pystitch emits several TRIM commands per
actual cut on the pro's files (on `becker_hat_small`, 30 of 40 TRIMs are
followed by another TRIM before any stitch), while our writer emits exactly
one. Corpus-wide the pro inflates **2.0x** (1,090 raw -> 555 breaks) and we
inflate **1.0x** (1,715 -> 1,715). A first pass at this comparison divided raw
commands on one side against real events on the other and wrongly concluded
that `becker-pro-parity`'s **1.27 trims/1k for the pro was unreproducible**. It
is correct. `run_breaks` de-duplicates, so the 3.1x above is unaffected.

### What it attributes the cause to

**Trim-dominated, decisively.** Not hop-dominated. Per §3's table that points
at the chaining / `trim_at_mm` policy rather than at travel giving up.

That matters for sequencing: `chain_links` is already measured at
**9.82 -> 4.06 trims/1k** on the benchmark and **7.35 -> 4.73** on `full_back`,
with zero added bare thread on four fixtures, and is blocked only on the
sew-out that fixes `LINK_COVER_TOL_MM`. **The largest measured lever on this
defect is already built and waiting on cloth, not on code.**

`_graph_travel` returning nothing (§2) is still a real defect and still worth
fixing — but this diff says it is not where the bulk of the gap sits, so do not
size it as though it were.

### The pro's actual cut rule, measured

Distance the pro moves after each trim on `becker_hat_small`:

| | mm |
|---|---|
| minimum | **11.8** |
| median | 23.6 |
| maximum | 71.7 |
| under our `trim_at_mm` of 3.0 | **0 of 35** |

The pro never cuts for a move shorter than ~11.8 mm. Our `trim_at_mm` is
**3.0**, so we cut across a whole band of distances they simply float —
consistent with `.claude/memory/pro-trim-threshold.md` recording floats up to
16.1 mm uncut.

That is a second measured mechanism for the 3.1x, independent of §2's travel
snap, and it is the one the corpus actually attributes the bulk to. **It is
also gate-1 territory** — `trim_at_mm` governs when thread is cut and how far a
float is allowed to sit on fabric, which is a cloth question, not a geometric
one. Do not retune it on this evidence alone. What this measurement DOES
support without touching a constant is chaining: `chain_links` removes the need
for the hop instead of re-deciding what to do about it.

### Caveats that must travel with these numbers

- **Recon lane**, not real-art. Artwork is rebuilt from the pro's own stitches,
  which the 2026-08-16 handoff measured as flattering the engine by 11.3 points
  on the scorecard. Trim counts are less exposed to that than shape scores are,
  but the lane is not the real-art lane.
- One run, one corpus. Evidence, not proof.
- The pro-side `run_breaks` exist only in `prep_all.py`'s manifest.
  `prep_both.py` builds its own `pro` block without them — so the real-art lane
  cannot produce this table today.

## What to do with this

1. ~~Re-measure in a pinned worktree; read the `run_breaks` diff first.~~
   **Done 2026-08-18 — §4.** Verdict: trim-dominated, 3.1x the pro.
2. Treat `chain_links` as the primary lever. It is built, measured, and blocked
   only on the sew-out — no code work will beat it.
3. Size the `_graph_travel` snap fix as a secondary contributor, not the cure.
4. If the real-art lane's version of §4 is wanted, teach `prep_both.py` to carry
   `run_breaks` on its `pro` block the way `prep_all.py:812` already does.
