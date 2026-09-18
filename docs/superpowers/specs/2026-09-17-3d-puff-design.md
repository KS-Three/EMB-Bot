# 3D puff — design spec

**Rulings:** 2026-09-17 · **written:** 2026-09-18
**Status:** Design approved by Kent in a brainstorming session — sections 1–2
individually, sections 3–4 together when he said "document this". **This written
spec is awaiting his review.** Nothing is built.
**Lane:** branch `claude/3d-puff`, worktree `.claude/worktrees/3d-puff`.
**Next step after his review:** `superpowers:writing-plans` against this file — see §12.

## Read these first, in this order

1. **This file** — what was decided, and why.
2. [`docs/puff-research-2026-09-17.md`](../../puff-research-2026-09-17.md) — the
   evidence: a 12-agent pass (7 scout lanes, a gate-1 triage, a 3-lens adversarial
   verify that killed 4 of 6 claims). Every number below traces there or to a code
   line cited inline.
3. [`docs/specialty-techniques-2026-08-01.md`](../../specialty-techniques-2026-08-01.md)
   §3 (lines 373–638) — the original parametric puff spec. **Where it and this file
   disagree, this file wins.** §11 lists every correction.

ROADMAP gate 1 — *no sew-out, no physical constants* — governs this tier. Its
amended test (*if every source you would consult to settle it owns no machine, the
gate does not apply*) is applied **per parameter** in §7, never to the feature as a
whole.

Pointer convention as elsewhere in the repo: **verified** = read in a checkout on
that date; **research §N** = measured or fetched by a scout lane and not
independently reproduced — one source, not two.

---

## 1. Kent's rulings, 2026-09-17

R1 came as a direct instruction. R2–R8 were each put to him as a multiple-choice
question with the trade-offs stated on every option. Rejected alternatives are
listed so nobody re-proposes them without new evidence.

| # | Question | Ruling | Rejected, and why |
|---|---|---|---|
| R1 | Scope | **Build 3D puff.** Moves it off PRODUCT.md's non-goal list. | The research recommended settling the Tajima halt test, a stitch-count run and a render *before* the scope call (research §8). Kent was told and chose to proceed; those items are now preconditions for PR 1 (§8), not for the decision. |
| R2 | Engine | **Python digitizer first** — `digitizer_core/`, service route only. | JS lettering first: no block/step/stop container, and `src/satinfont.js:119` caps satin at 3.0 mm, the puff band's floor. Both at once: widest diff, longest to anything sewable. |
| R3 | Designation | **Per-shape override + canvas right-click menu**, mirroring `borderMenu.js`. | Engine-only like appliqué: repeats appliqué's state exactly — a capability no customer can reach. Design-level toggle: a real logo puffs one element, not all of them. |
| R4 | Compensation | **Single Wilcom default: push 0.3–0.4 mm (0.35), no pull compensation.** Jagger's pull 0.6–0.7 mm + 25 % recorded in a code comment only. | Two named presets; no default; defer the number. **Kent was told this settles a constant §5.7 lists as sew-out-gated and chose it knowingly.** A ruling on an unsettled constant, not a measurement — see §5 and §7. |
| R5 | Out-of-band shapes | **Refuse, with the reason on the menu item** — e.g. *"stroke 2.1 mm: too narrow for foam, 3.0 mm minimum"*. | Allow + warn: the failure is physical and invisible on screen. Auto-repair: widening changes the art, and splitting a wide column IS the crush failure. |
| R6 | Colours | **Multi-colour from the start.** N puff threads, one foam slab and one stop per thread. | Single colour in v1; single colour, multiple shapes. |
| R7 | Width band | **3.0–5.0 mm; refuse above 5.0.** | Suppress `SPLIT_SATIN_ABOVE_MM` for puff regions only: the 5–11 mm path has never been exercised. Raise it globally: re-sews the corpus, and `DOCTRINE.md:1061-1087` records 5.0 → 7.0 breaking both coherent routes (research §1). |
| R8 | Minimum void | **Warn on every interior void with its measured gap in mm; refuse nothing.** New code `PUFF_VOID_UNVERIFIED`. | Refuse under a provisional number: invents a physical constant. Refuse all holed shapes: refuses O, A, B, D, e, o. Ignore: a trapped foam island is found after the garment is sewn. |

---

## 2. What already exists — do not rebuild it

| Need | What exists | Where |
|---|---|---|
| Operator-interrupt IR — *one colour stop = one human action* | `Step` (code, label, runs, action, function, flags, material, piece, layers, spm); `assert_steps_valid` **raises** on a colour-change step with an empty action; `plan_steps` is the read interface | `stage6_applique.py:761, :804, :818` (verified 2026-09-17) |
| A DST stop | Not a STOP opcode — DST/EXP/PES compile STOP and COLOR_CHANGE to identical bytes, so emit `CMD_COLOR_CHANGE`. The file half is measured green | `stitches.py:56-59`; `test_applique.py:124` `test_same_thread_stop_survives_dst`, `:152` `test_empty_step_cannot_swallow_its_stop` (verified 2026-09-18) |
| Step-aware resequencing | `nn_group_key` → `(sew_index, step_key, thread_index)`; stage 7 groups by `(sew_index, step_key)` | `stage6_applique.py:1081`; `stage7_sequence.py:1716` (verified 2026-09-18) |
| Density on the true arc (Melco "Column 2") | `spacing_mm` is the **outer-rail** target; pitch ÷ cos(lean) | `stage6_satin.py:2121, :2396, :2723` (verified 2026-09-17) |
| Junction overlap | `_JUNCTION_TUCK_MM = 0.4` | `stage6_satin.py:3084` (verified 2026-09-18) |
| A closed perimeter penetration loop (end-cap method #3) | `silhouette_cap`, default ON via `edge_cap: "bean"` | `stage6_border.py:929`; `config.py:1596` (verified 2026-09-18) |
| Bean loop emitter | `_bean_loop(ring_pts, entry, …)`; `BEAN_PASSES = 3`, `BEAN_STITCH_MM = 0.73` | `stage6_border.py:523`; `machine.py:703-704` (verified 2026-09-17) |
| Stroke width field | `Stroke`, `_WidthField`, `ribbon_width_mm`, `classify_strokes`, `extract_strokes` | `stage6_satin.py:174, :206, :240, :833, :1965` (verified 2026-09-17) |
| A **live** per-shape override path | Studio `element.shapeOverrides[sid].<key>` → `digitizer.js:325` packs `shape_overrides` → `apply_shape_edits` validates and writes `r.meta[key]` → `_CARRIED_META_KEYS` carries it through region merges | `regions.py:256, :345-353, :553` (verified 2026-09-18) |
| Canvas menu precedent | `borderMenu.js` — effective value and its source, the engine's rule stated on the item, `null` clears | `app/src/lib/borderMenu.js` (verified 2026-09-17) |
| Tier template | `applique_pass(planned, cfg, chart) → (blocks, warnings, remaining, cursor)`; one import, one call site, default False, byte-identical when off | `stage6_applique.py:1130`; `stage7_sequence.py:63, :1680`; `test_applique.py:194` (verified 2026-09-18) |

**Two traps in that table.**

- **The step IR reaches nobody.** `plan_steps` has zero production callers — only
  `test_applique.py:1002, :1021, :1085` (verified 2026-09-18).
  `digitizer_service/app.py:721-725` builds each block payload as
  `{**cone, "shape_ids": …, "design_edge"?}` with no `step` (verified 2026-09-18).
  `src/pdfsheet.js:261` still prints `"Color " + (i + 1)` (verified 2026-09-18). The
  comment in `stitches.py` claiming the step dict "rides the service response with no
  schema work" is false (research §5). **PR 0 fixes this.**
- **Appliqué's per-shape key is a dead path — do not copy it.**
  `Region.meta["applique"]` is read at `stage6_applique.py:1089, :1163` and written by
  nothing; it is absent from `_CARRIED_META_KEYS` (verified 2026-09-18). **Mirror
  `border`, which is live**: validated and written in `apply_shape_edits`
  (`regions.py:345-353`) and carried at `regions.py:553`. The research's advice to
  skip per-shape entirely (research §4) was about appliqué's dead copy; R3 stands on
  border's live one.

---

## 3. Architecture

**Module:** `digitizer/digitizer_core/stage6_puff.py`, exporting

```python
puff_pass(planned, cfg, chart) -> (blocks, warnings, remaining, cursor)
```

— the same signature and return contract as `applique_pass`, reusing `nn_group_key`
rather than redefining it. Appliqué comes out at the **front** of stage 7, because
fabric goes down before anything decorates it. Puff sews **last** — old §3.9: *"the
portion of the design that will be puffed must be the last section to sew"*,
unanimous across sources — so its call site sits after the colour loop in
`stage7_sequence.py`.

**Shared IR.** `Step`, `assert_steps_valid`, `plan_steps` and the function
constants move out of `stage6_applique.py` into a module both tiers import. A move,
not a rewrite: the research's adversarial pass refuted 3/3 the fear that the
container is appliqué-shaped (research K3) — its appliqué fields default empty,
`assert_steps_valid` tests exactly one thing, and `plan_steps` treats `block.step`
as opaque.

**Structural fork — decide in writing-plans with the code open, not before.** The
approved design has puff regions **leave** `planned`, as appliqué's do. The
research recommends they **stay** in the colour loop and be partitioned by
`step_key`, because puff is a satin variant on ordinary regions rather than a
separate fabric piece (research §4). That would make puff the first production
*writer* of `meta["step_key"]` — only tests write it today, while stage 7 and
`stage4_vectorize.py:935-944` already read it (verified 2026-09-18). **Nothing
Kent-facing differs between the two**: operator flow, config and UI are identical.
What decides it: which one keeps a puff thread that is *also* sewn flat elsewhere
from merging into one block, and which one can force every puff step to the end.

**Constants become policy** (old spec §5.6). `TIE_STITCHES = 3`
(`machine.py:756`) becomes a tie mode — puff 5, appliqué 3, flat 3. pystitch's
`lock_stitch` is a fixed 4-point lock, so the 5-stitch tie is emitted as geometry,
not requested from the writer (research §3.1). Nothing that sews today changes.

---

## 4. Geometry

One puff region sews five layers — one thread, one `Step`.

| # | Layer | Parameters | Source status | Build |
|---|---|---|---|---|
| 1 | Tackdown walk | 2.0 mm stitch, 2 passes, inset **provisional** | length and passes verbatim in Melco; **the 0.2 mm inset is uncited** (research §1) | offset ring + resample — exists |
| 2 | Perimeter knife — closes the penetration loop | 1.5 mm × 3, offset 0.0, start lock, start at the bottom | the bean table is `[B]`/Jagger, uncitable; the *loop* is unanimous | `silhouette_cap` / `_bean_loop` at a different stitch length — reuse |
| 3 | End-caps, method #1, at open termini only | tapered perpendicular satin bar, wide outboard, narrow inboard; spacing, overhang, taper **all sew-out-gated** | Melco 0.30 vs Hatch 0.16 spacing, opposite stated purposes; no parametric geometry source at any tier | **new — the only invented geometry** |
| 4 | Joins, at branch points | suppress perforation so foam stays cohesive (the bridge of an A) | Embrilliance StitchArtist's "caps and joins" (research §2.2) | **new, cheap** — branch points already come out of `extract_strokes` |
| 5 | Top satin | spacing `SATIN_SPACING_MM / 2.0`; comp per R4; junction overlap ≥ 3 stitches | ratio unanimous at 1.75–2.25×; the absolute is not | `satin_shape` + four suppressions |

**Sew order:** 1 → 2 → 3 → 5, with 4 applied as a suppression rule across 2 and 3.
Caps sew **under** the top satin — stated identically by a software vendor and an
OEM (research §3.1).

**The design rule, from old §3.1:** *every puff region must be enclosed by a closed
loop of needle penetrations.* Sides come free from the satin; ends are
manufactured. **Joins are the deliberate exception** — a branch point the design
chooses not to cut. So the invariant test walks each region's boundary and asserts
no gap between penetrations exceeds the perforation pitch **except across a
declared join**.

**End-caps are not "the #1 engine change".** An early draft of this design said
they were; the research refuted it 3/3 (research K1). Method #3 already closes the
loop and we ship its emitter. Caps are belt-and-braces at termini — build them,
knowing their dimensions are gated from day one.

**Density: ship the ratio, not 0.18.** `spacing = SATIN_SPACING_MM / 2.0` = 0.20
today, with `puff_spacing_mm` as an explicit override. An absolute 0.18 would drift
silently the moment `SATIN_SPACING_MM` moves — `FILL_ROW_MM` already moved 0.40 →
0.15 on 2026-09-03 while satin stayed at 0.4. The six published density values are
about three houses — **Hatch is Wilcom** — two of them contradicting themselves
(research §2.5).

**Junction overlap in stitches, not millimetres.** Wilcom: *"at least 3 stitches"*
— 0.54 mm at 0.18. A fixed 0.4 mm silently loosens as density tightens (research
§3.1).

**Four suppressions on puff columns.** Each turns off something that works today,
so each gets its own test.

1. `SPLIT_SATIN_ABOVE_MM` never fires inside a puff region. Moot under R7's 5.0
   ceiling, but asserted, so a later band change cannot reintroduce the crush.
2. Short stitches off — `_short_stitch_guard` (`stage6_satin.py:2864`).
3. Conventional underlay off — layer 1 replaces it.
4. Tatami / fill refused over foam as auto output. Old §3.6 — a scope call; Wilcom's
   tatami-with-a-satin-edge exception is manual work, never auto output.

**A spec defect not to inherit (research K5).** Old §3.10's `forbidden` list
includes `stitch_penetrations_inside_shape`, while old §3.7 prescribes a walk
*inside* the boundary and old §3.5 puts a cap *under* the column. The rule was
meant for the **cover** pass. Scope it that way, or the tier refuses its own
mandatory layers.

---

## 5. Config surface and data flow

**Four `PipelineConfig` fields** — appliqué has eight:

```python
puff: bool = False                    # load-bearing OFF, exactly as `applique`
puff_foam_thickness_mm: float = 3.0   # one of {2.0, 3.0, 4.0}; anything else refused
puff_spacing_mm: float | None = None  # None = SATIN_SPACING_MM / 2.0
puff_tackdown: str = "walk"           # "walk" | "zigzag" — the variant old §3.7 says to expose
```

- **Foam.** Nobody sells 5 mm; the stocked set across four brands is 2/3/4/6
  (research §2.4). So the allowed set is {2, 3, 4} and 6 is refused. Old §3.2's
  "hard limit 5.0" was a limit on a size that does not exist.
- **Validation.** `_CONFIG_FIELDS` derives from the dataclass, so the fields reach
  HTTP for free. **Add the puff enums to `_validate_config_dict`**
  (`digitizer_service/app.py:436`) — appliqué's are not validated there, so a typo
  arrives as a 500 instead of a 400 (research §4). Do not inherit that hole.

**Constants, not config** — the `APPLIQUE_*` precedent (`machine.py:1041, :1137`).
A `PUFF_*` block, every value carrying its source tier in a comment and every
sew-out-gated one saying so:

```python
PUFF_MIN_STROKE_MM     = 3.0    # desk: unanimous; two independent Melco fetches
PUFF_MAX_STROKE_MM     = 5.0    # R7: the ENGINE ceiling (SPLIT_SATIN_ABOVE_MM), not the physical band (3-11)
PUFF_PUSH_COMP_MM      = 0.35   # R4 ruling 2026-09-17 — UNSETTLED, see comment
PUFF_TIE_STITCHES      = 5      # desk: Melco
PUFF_SPM               = 600    # sew-out gated: 500-750 across four machine owners
PUFF_FOAM_OVERSIZE_MM  = 12.7   # desk: operator cutting margin (Ricoma says ~25)
PUFF_SLAB_CLEARANCE_MM = 6.35   # desk: operator note; unsourced
```

**What the R4 comment must say, in substance.** Kent ruled Wilcom's convention on
2026-09-17 knowing it was sew-out-gated. Wilcom itself publishes both signs — its
ES support says pull compensation *"increased to 0.3–0.5 mm"*, its 2024 Q&A says
*"I don't use pull compensation… I only use push"*, 0.3–0.4 mm — so this is one of
one house's two answers (research §3.2). Jagger's pull 0.6–0.7 mm + 25 % is
recorded, but the source is uncitable. The two conventions agree near 3 mm and
diverge ~4× at 11 mm, so the sew-out that settles it must use a **wide** column.

**Mapping R4 onto the engine is unresolved — settle it in writing-plans against the
code, not by guessing.** EMB-Bot has `Fabric.pull_comp_mm` (lateral —
`machine.py:472, :1057`) and an `end_cutback_mm` path in `stage6_satin.py` (`:3312`).
Old §3 is itself ambiguous: its prose says *"+0.3–0.4 mm **over** flat-satin
compensation"* (a delta) while its config says `value_mm: 0.35` (an absolute)
(research §7 item 2). R4's "no pull comp" means puff columns carry **zero** pull
compensation; confirm the chosen knob does exactly that.

**Per-shape data flow.** Every hop is paved except the ones marked NEW:

```
element.shapeOverrides[sid].puff = true    app/src/lib/puffMenu.js        NEW — mirrors borderMenu.js
  -> out.shape_overrides                   app/src/lib/digitizer.js:325   exists
  -> cfg.shape_overrides                   config.py                      exists
  -> apply_shape_edits: r.meta["puff"]     regions.py:345-353 pattern     NEW, with validation
  -> _CARRIED_META_KEYS += "puff"          regions.py:553                 NEW — without it a merge drops it
  -> puff_pass(planned, cfg, chart)        stage7_sequence.py             NEW call site
```

The master `puff` flag is **derived in the Studio** —
`out.puff = Object.values(overrides).some(o => o.puff)` — so a user who
right-clicks a shape never meets it, and the engine keeps one clean switch for the
byte-identical pin.

---

## 6. Multi-slab operator flow, gates, warnings

**Steps.** Each puff thread is one slab: one stop, one human action, laid only when
its turn comes.

| Step | `function` | `action` (example wording) |
|---|---|---|
| last flat block | `color_change` | *"Lay 3 mm foam colour-matched to thread 4 over the crown. Sheet ≥ 61 × 34 mm (design + 12.7 mm on every side)."* |
| puff slab 1 | `color_change` | *"Lay 3 mm foam colour-matched to thread 7 over the left panel. Keep ≥ 6.35 mm clear of the first piece — foam must not overlap."* |
| puff slab N | `end` | *"Tear away all foam. Tweezers for small areas; heat gun on lowest setting for remnants."* |

Sheet sizes are computed per slab — the hull of that thread's puff regions plus
`PUFF_FOAM_OVERSIZE_MM` — so the operator gets a number, not a rule.
`assert_steps_valid` already refuses a colour-change step with no action.

**Gates and codes.** Append-only in `warnings_codes.py`, **each with its Studio copy
in the same PR.** Appliqué's eight codes print engine prose to customers today —
`grep -ri applique app/src/` returns nothing — and `app/src/lib/digitizer.spec.js`
pins a hand-maintained code list, so that test passes while the copy is missing
(research §4).

| Code | Fires when | Behaviour |
|---|---|---|
| `PUFF_STROKE_TOO_NARROW` | stroke < 3.0 mm | refuse the shape (R5); extra `{shape_id, width_mm, floor_mm}` |
| `PUFF_STROKE_TOO_WIDE` | stroke > 5.0 mm | refuse the shape (R5, R7); extra `{shape_id, width_mm, ceiling_mm}` |
| `PUFF_SLAB_CLEARANCE` | two puff threads' regions closer than 6.35 mm | refuse — two slabs that close cannot be laid without overlapping |
| `PUFF_VOID_UNVERIFIED` | any interior void in a puff region | warn, never refuse (R8); extra `{shape_id, void_id, gap_mm}` — the measurement the first sew-out turns into a threshold |
| `PUFF_OPEN_PERFORATION` | the closed-loop invariant fails outside declared joins | tripwire — should be impossible |
| `PUFF_APPLIED` | puff was built | info; extra carries per-slab sheet sizes |

The canvas menu shows the refusal reason **before** the user commits, as
`borderMenu.js` already states the engine's rule on its item. The engine refuses
too, so a request that bypasses the menu gets the same answer.

**Preflight.** `preflight.py:2008` reads `satin_target = machine.SATIN_SPACING_MM`
with no override, and `DENSITY_RATIO_MAX = 1.5` (`:232`) (both verified
2026-09-18), so a correct puff satin reads a ratio near 0.5 and fires
`DENSITY_EXTREME` — *"expect the fabric to pucker"* — on a file that is exactly
right. An adversarial lens ran it and watched it fire (research §4). **Fix: a puff
satin band**, on the `_TONAL_FILL_BAND_MM` precedent (`:1953`), so the instrument
measures puff density against puff's own target. **Do not** dodge it by giving
puff its own run kind: `preflight.py:1907` skips everything that is not
`stitches.SATIN`, which would silence the only instrument that can check the
best-documented parameter in the spec. Coverage needs no change — the full stack
peaks at 3.32 units against `COVERAGE_WARN_UNITS` 6.67 (research K4).

**Out of scope, blocker named:**

| Item | Blocker |
|---|---|
| Reject if the element crosses a cap front seam (old §3.9) | The engine digitizes artwork; there is no garment-placement data to test a region against |
| 5–11 mm puff columns | R7. `SPLIT_SATIN_ABOVE_MM = 5.0` (`machine.py:506`); the 6.5 mm `wide_columns` path (`config.py:1724`) ships OFF because its admitted columns were "the right width and the wrong shapes". Render first, then sew |
| Browser / JS puff | R2. No step container; `satinMaxWidthMm: 3.0` hardcoded at `app/src/lib/generate.js:101` |
| End-cap method #2, pinching | Old §3.5 calls it a later optimisation |
| A minimum-void threshold | R8. No number exists anywhere |
| Foam stacking | Refused. Madeira's own sheet: one piece gives sharp edges, two give loft |
| `max_element_height_mm: 57` | An orphan constant with no source (research §3.1). Re-derive from the frame if it is ever needed |

---

## 7. Parameters — value and gate

| Parameter | Value | Desk or sew-out |
|---|---|---|
| Stroke floor | 3.0 mm | desk — unanimous |
| Stroke ceiling | 5.0 mm | engine limit (R7), not physics |
| Foam thickness | 3.0 default; {2, 3, 4} allowed | desk — catalogues |
| Foam colour | match thread, unconditional | desk — two mechanisms: show-through, and edge whiskers density cannot fix |
| Foam oversize | 12.7 mm | desk |
| Slab clearance | 6.35 mm | desk, unsourced |
| Top satin spacing | `SATIN_SPACING_MM / 2.0` | **ratio desk, absolute sew-out** |
| Junction overlap | ≥ 3 stitches | desk — Wilcom |
| Compensation | push 0.35, no pull | **ruled (R4), not settled** — sew-out at a wide column |
| Tackdown | 2.0 mm × 2 passes | desk |
| Tackdown inset | provisional | **sew-out** — the 0.2 citation is false |
| Perimeter knife | 1.5 mm × 3 | table uncitable; the loop is unanimous |
| End-cap spacing, overhang, taper | provisional | **sew-out** — no parametric source at any tier |
| Tie stitches | 5 | desk |
| Speed | 600 SPM | **sew-out** — 500–750 across four machine owners |
| Minimum void | none; warn only | **sew-out** (R8) |
| Same-needle physical halt | — | **sew-out, five minutes** — §8 |

Needle (five sources, five answers — Wilcom recommends 75/11, not old §3's 80/12),
presser-foot height, top tension and backing are **operator-sheet text, not engine
parameters**. None is settled; none changes a stitch.

---

## 8. Build order

**Before PR 1 — Kent, at the machine, about five minutes.** Write a two-block
same-thread DST, enter the needle twice, press start. Does the Tajima halt? The
file half is proven (`test_applique.py:124`); the machine half is a per-machine
needle-sequence setting nobody has measured (research §3.2). **It gates puff,
appliqué and ITH at once.** If the machine does not halt, the operator-interrupt
model needs a different stop mechanism before PR 1 is worth writing.

**Also before PR 1 — free, and a session can do them:**

- Digitize one fixture at 0.40 and at 0.20 satin spacing and read
  `StitchPlan.stats`. Settles the puff-vs-flat stitch-count contradiction (Melco
  "generally very low" vs web sources' 1.9–2.0×).
- Read `tires_hat_3d`, a scorecard fixture whose pro file is a 279-stitch
  "Puff Grip" tack-down — after which *"the machine stops for the operator to lay
  foam"* — and a 5,359-stitch "Black 3D"
  (`docs/stage0-tires-photo-scene-2026-09-11.md:452-453`, verified 2026-09-18). It is
  the only professional puff digitizing in the repo and the natural reference to
  render PR 1's output against. `digitizer/tools/pro_parity/smoke.py` already scores against
  it, and four docs give four accounts of what that comparison measures (research
  §7 item 14).

**PR 0 — step-IR plumbing, ~150 lines, three files.** `plan_steps` → the service
block payload (`digitizer_service/app.py:721-725`) → `src/pdfsheet.js:261`. Worth
landing whether or not puff ever ships: it turns appliqué's computed, validated and
discarded operator worksheet into one a customer can read. Independent of the
Tajima test.

**PR 1 — the puff tier.** `stage6_puff.py`; the shared step module; the `PUFF_*`
constants; four config fields plus validator enums; the `regions.py` write and
carry; the stage 7 call; the preflight band; six warning codes **with their Studio
copy**. About 1,500 lines and 35 tests on the appliqué model (research §4). Ships
with `puff = False`.

**PR 2 — the Studio surface.** `app/src/lib/puffMenu.js`, the refusal strings on
the menu item, the derived master flag.

---

## 9. Tests that decide whether it works

- **`test_puff_off_is_byte_identical`** — load-bearing. Assert on exported **DST
  bytes**, not stitch counts; appliqué's own test (`test_applique.py:194`) explains
  why — a count can stay equal while geometry moves.
- **The closed-perforation-loop invariant** — walk each region's boundary; no gap
  above the perforation pitch except across a declared join.
- Joins: a branch point is not perforated; an open terminus is capped.
- Refusal at 2.9 mm and at 5.1 mm, each carrying its reason; acceptance at 3.0 and 5.0.
- Every interior void reported once, with its gap in mm, and never refused.
- Two puff threads 6.3 mm apart refused, 6.4 mm accepted. Each slab's sheet size
  equals its hull plus 12.7 mm.
- Every puff step carries a non-empty action — inherited, since `assert_steps_valid` raises.
- Each suppression on its own: no split cross, no short stitch, no underlay run, no
  fill run inside a puff region.
- The preflight band: a correct puff design raises no `DENSITY_EXTREME`; a puff
  design sewn at flat density does.
- `puff` survives a region merge — the `_CARRIED_META_KEYS` entry, exactly what
  appliqué's key lacks.
- A misspelt `puff_tackdown` is a 400, not a 500.
- Studio: outside 3.0–5.0 the menu greys the item and states the reason; the code
  list in `digitizer.spec.js` includes all six `PUFF_*` codes.

---

## 10. Open — not decided, and whose call

| Item | Whose | Note |
|---|---|---|
| Does PR 2 — the customer-reachable surface — wait for the first sew-out? | **Kent** | Five parameters in §7 are unsettled. Exposing puff before thread has touched foam means shipping designs nobody has seen sew. PR 0 and PR 1 are safe either way: PR 1 ships OFF and unreachable. |
| Placement contour step | **Kent** | Tajima and Ricoma sew an outline on bare fabric first so the operator knows where the foam goes; Melco says oversized foam needs no placement. The research triage calls it desk-settled and recommends adding it (research §2.3); appliqué already builds the object (`Step(code="PLACE", …)`, `stage6_applique.py:955`). Costs one extra stop per slab. |
| Foam hardness vs colour match | **Kent** | Old §3's `hardness: hard` and `color: match_thread` cannot both hold: firm foam ships in white and black, soft in eleven colours (research §2.4). This spec keeps colour match unconditional and leaves hardness to the operator sheet. |
| Raised-embroidery IP | **Kent / counsel** | Wilcom's AU provisional `AUPQ977000A0` (raised embroidery) is listed unresolved at `docs/masters-teardown-2026-08-01.md:469` (verified 2026-09-18). The old spec's §5.5 all-clear covers only the flat-pipeline gap table, not puff (research §2.6). Its filing date and status are the first things to check. |
| Leave `planned` vs stay in the colour loop | writing-plans | §3. |
| Which engine knob R4's "push" is | writing-plans | §5. |
| Water-dissolvable puff ("Puff Stuff") | — | A vendor claims it needs no stitch changes and suits fine lettering — the two constraints this whole spec rests on. A hypothesis to sew, not a spec (research §7 item 13). |

---

## 11. Corrections to `docs/specialty-techniques-2026-08-01.md` §3

Evidence for each is in the research doc. This list exists so the old spec is not
trusted where it is wrong.

1. **§5.6's `SATIN_MAX_WIDTH_MM = 3.0`, "fatal for puff", was false when written.**
   It is 5.0 (`machine.py:391`) and was already 5.0 in the spec's own introducing
   commit `f02b138`. The browser engine is the one at 3.0.
2. **The worse constant is `SPLIT_SATIN_ABOVE_MM = 5.0`** (`machine.py:506`). It puts
   interior penetrations into every cross over 5 mm — the old spec's own crush failure.
3. **End-caps are not "the #1 engine change."** Method #3, the old spec's own
   baseline, closes the loop, and `silhouette_cap` already emits it.
4. **`tackdown_walk.inset_mm: 0.2`, cited "[V] Melco PDF p.2", is not in that PDF** —
   two lanes, independently.
5. **0.18 mm, marked "fetched, verified", was read off a screenshot**, not the text
   layer. Melco's live help article says 0.15–0.17.
6. **Hatch is Wilcom.** The density table's six rows are about three houses.
7. **`[B]`/"Jagger" is uncitable**, and it alone carries compensation Convention A,
   the 8 mm design ceiling, the bean table and the 80/12 needle.
8. **`forbidden: stitch_penetrations_inside_shape`** contradicts old §3.7 and §3.5;
   it belongs to the cover pass only.
9. **No minimum-void gate.** Wilcom names "voided areas" as a deciding factor; the
   old spec quotes only the other half of that sentence.
10. **No joins primitive.** The old junction rule is about thread coverage, not
    about choosing not to perforate.
11. **Foam hard limit 5.0** is a limit on a thickness nobody sells.
12. **Density appears three ways inside old §3:** `[0.15, 0.20]` (`:422`),
    `[0.16, 0.20]` (`:564`), `0.16–0.18` (`:623`).

---

## 12. Next session starts here

1. **Confirm Kent has reviewed this spec.** If he asked for changes, make them first.
2. **Work in the lane:** `.claude/worktrees/3d-puff`, branch `claude/3d-puff`. The
   worktree has no `.venv` — use the main checkout's Python.
3. **Invoke `superpowers:writing-plans` against this file.** PR 0 is independent and
   can be planned and started at once; PR 1 waits on §8's Tajima test.
4. **Resolve in the plan, with the code open:** §3's structural fork and §5's R4
   knob mapping.
5. **Put §10's Kent-owned items to him with `AskUserQuestion`,** one at a time —
   never as prose offers.
