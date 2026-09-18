# 3D puff — research pass, 2026-09-17

**Read this only after `docs/specialty-techniques-2026-08-01.md` §3.** That section is
already a complete parametric puff spec: twelve subsections, a full config block, a
ten-row failure table. This document does not replace it and does not repeat it. It
does three things:

1. **Corrects it** where six weeks of engine work made a number wrong, and where a
   citation turned out to be false.
2. **Adds** what seven source lanes found that §3 does not have — a missing gate, a
   missing primitive, a missing worksheet step, and the licence/prior-art sweep.
3. **Triages every parameter** against the amended ROADMAP gate 1, so the next
   session knows which numbers it may wire in from the desk and which ones need
   thread.

Pointer convention: `(verb date — source)`. **Verified 2026-09-17** means I read it
in this checkout today. **Reported 2026-09-17** means a scout lane measured or
fetched it and I did not independently reproduce it — treat those as one source, not
two. Anything with no pointer is unverified and is labelled so inline.

Provenance of this pass: seven scout lanes (repo spec extraction, repo-wide doc
sweep, code integration points, foam/materials vendors, commercial digitizing
software, end-cap geometry + open-source prior art, machine mechanics), a gate-1
triage, and a three-lens adversarial pass over the six riskiest claims. **Four of
those six claims were refuted.** They are in their own section below so nobody
resurrects them.

---

## 1. The headline: §5.6's first blocking constant was already wrong the day it was written

`docs/specialty-techniques-2026-08-01.md:742` says:

> `SATIN_MAX_WIDTH_MM = 3.0` — correct for flat goods, wrong for pile, and fatal for
> puff, whose legal range starts where this constant stops.

**That is false, and it was false when the line was committed.** `SATIN_MAX_WIDTH_MM`
is **5.0** (verified 2026-09-17 — `digitizer/digitizer_core/machine.py:391`). It moved
3.0 → 5.0 in commit `270e1f1` on 2026-07-30; the spec landed in `f02b138` on
2026-08-01, and `git show f02b138:digitizer/digitizer_core/machine.py` already read
5.0 (reported 2026-09-17 — doc-sweep lane). The spec's own introducing commit
contains the value that refutes its claim.

Three other docs already carry the correction — `digitizer/docs/pro-digitizing-playbook.md:104`,
`docs/dt-first-architecture-2026-08-01.md:392` (struck in place, "RESOLVED: main is
5.0 now"), `docs/sewout-card-2026-07-31.md:148`. The specialty spec is the only
holdout, and `docs/scope-digest/craft-laws.md` contradicts *itself* about it: line 9
states 5.0 correctly, line 131 files the same constant as an unresolved four-way
disagreement (reported 2026-09-17 — doc-sweep lane).

**The direction survives the wrong number, and this is the part that matters for a
build decision.** Puff's legal band is 3.0–11.0 mm. Today's engine admits:

| Lane | Ceiling | Where |
|---|---|---|
| Python, default | **5.0 mm** | `machine.py:391` (verified 2026-09-17) |
| Python, `cfg.wide_columns` | **6.5 mm** | `machine.py:407`; `config.py:1724` defaults `False` (verified 2026-09-17) |
| Browser engine | **3.0 mm** | `src/satinfont.js:119`, `src/digitize.js:344` (`o.satinMaxWidthMm \|\| 3.0`), `app/src/lib/generate.js:101` (verified 2026-09-17) |

So Python covers the bottom quarter of the band and the browser covers exactly the
floor and nothing above it. **"Fatal" overstates it; "stops well short" is right.**

And there is a second constant nobody flagged that is worse than a missing ceiling:
`SPLIT_SATIN_ABOVE_MM = 5.0` (verified 2026-09-17 — `machine.py:506`) injects
interior penetrations into every cross over 5 mm. That is not "puff columns get
routed to tatami", it is "puff columns get crushed down the centreline" — the spec's
own failure row 5 mechanism (`docs/specialty-techniques-2026-08-01.md:627`). An
uncapped column loses its foam at the ends; a split column loses its loft
everywhere.

**Do not fix the ceiling by raising the constant.** `DOCTRINE.md:1061-1087` records
5.0 → 7.0 breaking both coherent routes (18 and 13 failures against a 3-failure
baseline), and `DOCTRINE.md:4302-4310` retires that entry's *reasoning* while
leaving the caution: `cfg.wide_columns` reaches 6.5 and ships **OFF** because the
admitted columns were "the right width and the wrong shapes" (reported 2026-09-17 —
doc-sweep lane). The standing rule from that entry applies directly here: *when a
policy admits a new population, render what it produces before pricing it.*

### Two citations in §3 do not hold

- **`tackdown_walk.inset_mm: 0.2` is fabricated.** `docs/specialty-techniques-2026-08-01.md:489-495`
  presents it under the heading "What replaces it, with hard numbers `[V]` Melco PDF
  p.2" (verified 2026-09-17 — I read those lines). Two independent lanes extracted
  that PDF's text layer and found **zero** occurrences of the string, against hits
  for `3points`, `200`, `20point`, `25pts` in the same extraction; the PDF says only
  "inside the edge of the puff shape" (reported 2026-09-17 — end-cap lane and
  software lane, independently). I could not re-fetch the PDF today
  (melco.zendesk.com returns 403 to WebFetch). The 2.0 mm length and the 2 passes
  **are** verbatim in the source; only the inset is invented, and 0.2 mm on a 3 mm
  column is within one satin cross of the rail.
- **The headline 0.18 mm density carries "fetched, verified" and is not in that
  PDF's text either** — it is read off a screenshot on p.4 (reported 2026-09-17 —
  end-cap lane). It may well be right; it is not a quotable verbatim vendor number.
  Melco's own live help article says **1.5–1.7 pt (0.15–0.17 mm)**, so the density
  table at `:410-411` lists one vendor twice as if two houses agreed.

### `[B]` / "Jagger" is uncitable

The spec's legend (`:3`) defines exactly four tiers — `[V]` `[S]` `[P]` `[D]` — and
§3 leans on `[A]`, `[B]`, `[C]`, `[A/V]`, `[A/B]`, none defined, while `:427` appeals
to "all five tier-A sources". `[B]`/"Jagger" is the **sole** source for Convention A's
compensation (0.60–0.70 mm pull, ≥25 % width, 0.9 mm cap comp), the 8.0 mm design
ceiling, the entire bean-perimeter table and the 80/12 needle. Two lanes searched the
web and the repo and could not find it: 10–11 hits across `docs/**.md`, no URL, no
author, no date (reported 2026-09-17 — software lane and end-cap lane). One of its
numbers is actively contradicted by the source it sits beside: asked directly about
80/12, Wilcom's own Q&A answers *"I haven't found they help the process"* and
recommends 75/11.

Separately, `docs/research-partials-2026-07-31.md:22` still records
`specialty-techniques-mastery | 0 of 6` under a header forbidding any constant in it
being wired into the engine. That is a **stale table, not a tainted spec** — it means
that file harvested nothing from the killed run, and the spec came from a re-run the
next day. Do not quote it as evidence the research never landed.

---

## 2. What this pass ADDS to §3

### 2.1 A missing gate that can ruin a garment: minimum void

§3's eligibility block gates on stroke width, height and cap seam. It has **no
minimum void / counter-gap parameter at all** (verified 2026-09-17 —
`docs/specialty-techniques-2026-08-01.md:544-550`). `:443` quotes half of the
sentence it needs. The full quote from Wilcom's Q&A is:

> "The size of the text isn't going to dictate the possibility of applying 3D puff.
> The satin width of the elements themselves, **as well as the 'voided' areas**, will
> be the deciding factors."

(reported 2026-09-17 — software lane.) For a raster-to-vector auto-digitizer this is
the more dangerous half: a counter or inter-stem gap too narrow to perforate leaves an
island of foam **inside** a letter that nobody can tear out. No source publishes a
number. **This is the single most important omission in §3 and it is sew-out-gated.**

### 2.2 A missing primitive: joins (caps that deliberately do NOT cut)

Embrilliance StitchArtist L2 splits end geometry into two named primitives:

> "These are called 'caps' and 'joins'. These underlay elements either 'perforate' or
> 'cap' the end of a satin stroke like this letter 'S' **or allow the foam to stay
> cohesive and 'join' in the middle of a letter such as at the bridge of a capital
> letter 'A'**."

(reported 2026-09-17 — software lane, embrilliance.com.) §3's only junction rule is
`overlap_at_junctions_mm: 0.4`, which is about thread coverage at a butt joint, not
about *suppressing* perforation. On a medial-axis engine every branch point is a
candidate join. **This is a missing primitive, not a missing number** — deciding to
have it needs no machine.

### 2.3 A missing worksheet step: the placement contour

§6.3's puff worksheet runs `FLAT DONE → FOAM → TACK → PUFF → TEAR`. Two machine
vendors sew a contour on bare fabric *first*, and say that contour is how the operator
knows where the foam goes:

- Tajima: "Insert a stop cord that stops the machine after the contour is sewn. This
  will tell you where to place the urethane… If you forget to put the stop code in
  digitizing, you will miss the timing to place the urethane."
- Ricoma: "first color stop should be the outline."

(reported 2026-09-17 — machine-mechanics lane.) Melco argues the opposite —
"the foam is cut oversized and doesn't have to be placed accurately" — so this is a
real branch, not an oversight by one vendor. Appliqué **already builds this object**:
`Step(code="PLACE", …)` at `stage6_applique.py:955-959`.

### 2.4 The materials reality §3 does not know

- **`hardness: hard` and `color: match_thread` are jointly unsatisfiable.** Madeira's
  firm BodyBuilder ships in *white and black*; its soft E-Zee ships in eleven colours.
  Gunold: Dense 7 colours, Classic 14 (reported 2026-09-17 — materials lane,
  manufacturer instruction sheets). Choosing firm foam costs 9 of 11 thread matches.
- **Nobody sells 5 mm foam.** Stocked set across four brands is 2/3/4/6 mm. The repo's
  `hard_limit_mm: 5.0` is a limit on a SKU that does not exist; the real decision is
  4 vs 6 (reported 2026-09-17 — materials lane).
- **The two largest foam vendors publish zero stitch parameters.** Madeira's two
  instruction sheets contain five numbered steps and one dimension each, and defer
  digitizing entirely to a document ("Prof. T.H. Read, *Creating 3D Embroidery*") that
  the lane could not locate. So every number in §3.3–§3.8 comes from *software*
  vendors, and the materials side corroborates none of it (reported 2026-09-17 —
  materials lane). **That is the highest-value unretrieved primary source in this
  whole pass.**
- **Colour match has a second mechanism §3 does not record**: dark foam hides residual
  *whiskers* at the edge after a clean tear (SPSI). Show-through is fixable by
  density; whiskers are not. So colour match cannot be traded against density
  (reported 2026-09-17 — materials lane).
- **Madeira's own sheet supports the stacking ban from the other side**: two callout
  captions, "Sharp edges achieved with 1 piece" / "Extra loft achieved with 2 pieces".
  An auto-digitizer optimising letterforms wants sharp edges (reported 2026-09-17 —
  materials lane). Note the OEM dissent: Happy's tech note explicitly permits stacking.

### 2.5 Hatch **is** Wilcom — the density table has ~3 houses, not 6

hatchembroidery.com's puff page carries "Wilcom International Pty Ltd.", a Wilcom logo
asset, CSS comments reading `WILCOM EDITS`, and the same article is served from
wilcom.com (reported 2026-09-17 — software lane). So the density table's "Wilcom 0.18"
and "Hatch 0.16" rows are two Wilcom-published numbers disagreeing with each other by
12.5 %, and Melco appears twice (0.18 PDF, 0.15–0.17 help article). **Six values, about
three houses, two of which contradict themselves.**

### 2.6 Licence and prior-art sweep — there is nothing to copy

- **Ink/Stitch is GPL-3.0 by its actual LICENSE file** (read directly, not a badge) and
  contains **zero** puff/foam code — the only hits are thread-palette names ("Cream
  Puff", "Sea Foam"). Its satin module has no end-cap generation of any kind
  (reported 2026-09-17 — end-cap lane).
- **pystitch is genuinely MIT** by the LICENSE file in our own venv and on GitHub — but
  it is format I/O only, nothing to reuse (reported 2026-09-17 — end-cap lane).
- **libembroidery is zlib/libpng** and does have satin generation, but it is a
  constant-thickness mitred ribbon with no caps, no variable width and no density
  normalisation — below where we already are (reported 2026-09-17 — end-cap lane).
- **PEmbroider is a harder blocker than GPL**: its LICENSE forbids using it to build
  commercial digitizing software *by name*. Its GitHub licence tag is `NOASSERTION`,
  which is exactly the case where the tag tells you nothing. **Do not use it in any
  form** (reported 2026-09-17 — end-cap lane).
- **No open-source foam/puff satin implementation exists** — measured negative across
  four `gh search` queries and a Hub search returning only style LoRAs. The one
  genuinely adjacent Hub repo (`LLYszs070206/image-to-embroidery-private`) is gated;
  its `MODEL_LICENSE.md` is **unread**, not permissive (reported 2026-09-17 — end-cap
  lane).
- **Ember does not do puff.** `grep -niE 'puff|foam|raised|dimensional'` across all
  three teardowns returns one line about tonal shading (reported 2026-09-17 —
  doc-sweep lane). **Read that as weak evidence against puff being parity pressure,
  not as absence of evidence.**
- **The raised-embroidery patent question is still open.** `docs/masters-teardown-2026-08-01.md:469`
  lists Wilcom's AU provisional `AUPQ977000A0` (raised embroidery) as an unresolved IP
  item; a repo-wide grep finds that one line and no answer. §5.5's "everything is free
  to implement" all-clear is scoped to the G1–G15 gap table, which is entirely
  flat-pipeline work — **it does not cover puff** (reported 2026-09-17 — doc-sweep
  lane).

### 2.7 What is already built that §3 assumes is not

| §3 asks for | State today |
|---|---|
| `density_normalized_columns: true` ("Melco Column 2") | **Built.** `stage6_satin.py:2684-2760` measures the longer rail — the same rule Melco, Wilcom Auto Spacing and Ink/Stitch's `rails.py` all state, reached independently (reported 2026-09-17 — end-cap lane) |
| `overlap_at_junctions_mm: 0.4` | **Built.** `_JUNCTION_TUCK_MM = 0.4` (verified 2026-09-17 — `stage6_satin.py:3084`, applied `:3518`) |
| Step/stop IR, "one color stop = one human action" | **Built and validated, reaches nobody** — see §5 |
| A closed loop of perimeter penetrations (cap method #3) | **An emitter exists**: `stage6_border.silhouette_cap`, default ON via `config.py` `edge_cap: "bean"` — literally method #3 at a different stitch length (reported 2026-09-17 — adversarial lens 3) |
| A machine STOP opcode | **Not needed.** `stitches.py:56-59` has four verbs and no STOP (verified 2026-09-17), and that is correct: DST/EXP/PES all compile STOP and COLOR_CHANGE to identical bytes, and PES *forcibly rewrites* STOP as a duplicate colour (reported 2026-09-17 — machine lane, read from pystitch's writers) |

---

## 3. Parameter triage

ROADMAP gate 1's amended test: *"if every source you would consult to settle it owns
no machine, this gate does not apply."* Applied per parameter, not to the feature.

### 3.1 Desk-settled — wire these in without a sew-out

| Parameter | Value | Note |
|---|---|---|
| `foam.thickness_mm` default | 3.0 | Only thickness every vendor stocks; Madeira sells nothing else |
| `foam.hard_limit_mm` | **re-express as max 4.0, reject 6.0** | 5.0 is a limit on a SKU nobody sells |
| `foam.color` | match thread, unconditional | Two mechanisms (show-through + edge whiskers); the second is not fixable by density |
| `foam.oversize_mm` | 12.7 (Ricoma says ~25) | Operator cutting margin; take the larger |
| `foam.multi_color_gap_mm` | 6.35 | Unsourced, but the cost of being wrong is an operator note |
| `foam.layers` | 1 | Manufacturer's own caption states the trade-off |
| `satin.density_ratio` | `spacing_flat / 2.0` | **Ship the RATIO, not 0.18.** Every house publishes 1.75–2.25×. `FILL_ROW_MM` already moved 0.40 → 0.15 on 2026-09-03 while `SATIN_SPACING_MM` stayed 0.4 — an absolute would silently drift |
| `gate.min_stroke_width_mm` | 3.0 | Only number with two independent verified Melco fetches agreeing; unanimous across three houses |
| `gate.design_width_ceiling_mm` | 8.0 | Derivable from `width + 2·comp ≤ 12` regardless of whether "Jagger" exists |
| `satin.compensation.invariant` | `width + 2·comp ≤ 12.0` | Arithmetic over two published ceilings; Melco ships the same guard as "Max Pull Comp" |
| `satin.auto_split` | OFF (`split_above_mm = inf`) | Melco 200 pt vs 300 pt is not load-bearing; the rule is "never let it fire inside the band" |
| `satin.short_stitches` | OFF | Suppress `_short_stitch_guard` (`stage6_satin.py:2864`); a suppression needs no number |
| `satin.density_normalized_columns` | true | **Already built** |
| `satin.overlap_at_junctions` | 0.4 mm → **re-express in stitches** | Wilcom: "at least 3 stitches" = 0.54 mm at 0.18; in mm it silently loosens as density tightens |
| `machine.tie_stitches` | 5 | pystitch cannot emit it (fixed 4-point `lock_stitch`), so we emit the geometry; §5.6's "policy not a constant" |
| `sequencing.puff_block` | LAST | Unanimous; emission order is code |
| `sequencing.stop_code_before_puff` (file side) | emit **COLOR_CHANGE**, not a STOP verb | Documented format + reference impl in our own venv + a passing test. **This is the textbook case the 2026-09-08 gate amendment was written for** |
| `sequencing.placement_contour` | **ADD** | Two machine vendors publish it; appliqué already builds the object |
| `sequencing.element_order` | bottom-up, centre-out (caps) | Already echoed in our `structured_cap` preset |
| `end_caps.method` | #3 baseline + #1 at termini | Architecture choice; the two houses that automated anything both automated end geometry |
| `end_caps.order` | before the top satin | Stated identically by a software vendor and an OEM |
| `end_caps.joins` | **ADD the primitive** | Topology, not physics |
| `underlay.standard_underlay` | OFF, zigzag exposed as a variant | Right answer, wrong reason in §3 — see §7 |
| `underlay.tackdown_walk` len/passes | 2.0 mm × 2 | 2.0–4.0 all work; nothing about being wrong here is expensive |
| `machine.bobbin_detection` | OFF for the puff colour | Published mechanism (foam dust), no number |
| `forbidden.tatami/complex_fill` | forbid as **auto output** | A scope call, not a physics claim |
| `worksheet.do_not_resize` | hard flag | Cap overhang / tack inset / cover width are absolute, not proportional |
| `scope.refuse washed/dry-cleaned goods` | refuse | Vendors' own care labels; conservative refusal costs nothing |
| `pricing` | time-priced, never stitch-priced | A stopwatch owns no machine; published shop pricing corroborates the *ruling* |
| stitch-count ratio puff vs flat | **measure locally** | One fixture at 0.40 vs 0.18, read `StitchPlan.stats` |
| `gate.max_element_height_mm` | 57.0 — **re-derive** | Orphan constant, no prose, no tier. It is a cap field and a ruler; just measure the frame |

### 3.2 Sew-out gated — blocker named

| Parameter | Blocker |
|---|---|
| **`machine.same_needle_halt` (physical)** | The file half is **measured green** (`test_applique.py:124-149`: one literal `b"\x00\x00\xc3"` survives write and pystitch decode). The machine half is a per-machine, per-firmware needle-sequence-table setting. The one Tajima-specific claim came from a search summary of a forum page whose host does not resolve. **Five minutes at the Tajima. Gates puff, appliqué and ITH simultaneously.** |
| **`gate.min_void_mm`** | No number exists anywhere. "How narrow a gap will hard 3 mm foam still tear out of" is a foam-and-needle question. Highest-consequence gap in §3 |
| **`satin.compensation` (direction + magnitude)** | Exactly one house on earth publishes a lateral puff-comp figure and it publishes **both signs**: Wilcom ES support says "Pull Compensation… increased to 0.3–0.5 mm"; Wilcom's own 2024 Q&A says "I don't use pull compensation… I only use push", 0.3–0.4 mm. Melco/Tajima/Ricoma/Ignition/Embrilliance publish nothing; Hatch documents the mechanism and explicitly no number. **Run the sew-out at a WIDE column** — %-vs-mm means the two conventions agree near 3 mm and diverge ~4× at 11 mm |
| **`end_caps.spacing_mm`** | Melco 0.30 vs Hatch 0.16 (same as its top satin), 2× apart, with *opposite stated purposes* for the cap. §3:460's reconciliation is reasoning, not measurement |
| **`end_caps.overhang_mm`** | The "0.5–0.9 range" is one verified point (Wilcom, 0.5) plus an uncitable one. The failure symptom is a visual verdict |
| **`end_caps` geometry** (taper ratio, cap length, feather angle) | **No parametric source exists at any tier.** Every source is prose or a picture; Embrilliance's entire Foam Underlay help page is 1,396 bytes with no number in it |
| **`underlay.tackdown_walk.inset_mm`** | The 0.2 citation is false (§1). With it struck there is no source |
| **`machine.needle`** | Five sources, five answers (75/11 sharp, 80/12 sharp, 90 sharp KK, ballpoint, 14/90), mechanisms pointing in opposite directions. Our value is the only one nobody recommends. Note the coupling: a *short-shank* system (Schmetz DBxK5 KK) moves the thickness cutoff |
| **`machine.speed_spm`** | 500–750 across four parties who all own machines; ours (600) is below Melco's 700 and above Ricoma's 500–600 |
| **`machine.presser_foot`** | "Max" is not a number and differs per machine; one source says 2–3 mm, one says not mandatory |
| **`machine.top_tension`** | "Loosen slightly" — no number anywhere, no config field |
| **`machine.backing`** | No vendor pairs a backing with foam at all |
| **8–11 mm of the width band** | Our ceiling is 5.0 / 6.5-under-a-flag, shipped OFF because the admitted columns were "the right width and the wrong shapes". **Render first, then sew** |

---

## 4. What could be built tomorrow, and what it costs

Model: appliqué, exactly — 1,373 lines in `stage6_applique.py`, 1,621 lines / 58 tests
in `test_applique.py`, 8 config fields, **one** import into stage 7
(`stage7_sequence.py:63`), **one** call site (`:1680`), default False, byte-identical
when off (all verified 2026-09-17).

**Do the step-IR plumbing FIRST, as its own PR, whether or not puff ever ships.**
See §5 — it ships appliqué's operator worksheet, which is computed, validated and
thrown away today, and puff is unusable without it because half the deliverable is
operator instructions.

Then, if authorised:

- **`digitizer/digitizer_core/stage6_puff.py`** exporting `puff_pass(planned, cfg, chart)
  → (blocks, warnings, remaining, cursor)`, reusing `nn_group_key` rather than
  redefining it. Called from stage 7 **after** the colour loop — the mirror of
  appliqué's pre-loop call, because puff sews LAST.
  - **Structural fork to decide first:** do puff regions leave `planned` (appliqué's
    model) or stay in the colour loop and get partitioned by `step_key`? I recommend
    **stay** — puff is a satin variant on ordinary regions, not a separate fabric
    piece. That makes puff the **first production writer** of `region.meta["step_key"]`,
    a path only tests have exercised.
- **`machine.py` `PUFF_*` block**, modelled on the 124-line `APPLIQUE_*` block, every
  constant carrying its tier in a comment and every sew-out-gated one saying so.
- **~7 `PipelineConfig` fields** — they reach HTTP for free because `_CONFIG_FIELDS` is
  derived from the dataclass. **Add puff's enums to `_validate_config_dict`** rather
  than inheriting appliqué's hole (a typo'd enum today arrives as a 500, not a 400).
- **A puff satin band in preflight.** `preflight.py:2008` reads
  `satin_target = machine.SATIN_SPACING_MM` with no override and `DENSITY_RATIO_MAX = 1.5`
  (`:232`) — both verified 2026-09-17 — so a correct 0.18 mm puff satin reads ratio
  0.45 and fires `DENSITY_EXTREME` ("denser: expect the fabric to pucker") on a file
  that is exactly right. **An adversarial lens ran this and watched it fire.** The
  precedent is one branch up: `_TONAL_FILL_BAND_MM` (`:1953`) exists because a correct
  streamline result warned on 9 of 12 jobs. **Do not dodge it by giving puff its own
  run kind** — `preflight.py:1906` skips anything that is not `stitches.SATIN`, so that
  silences the warning by leaving the best-documented parameter in the spec with no
  instrument at all.
- **`PUFF_*` warning codes WITH Studio copy in the same PR.** `warnings_codes.py` has
  58 codes, 8 of them `APPLIQUE_*` (verified 2026-09-17), and `grep -rni applique app/src/`
  returns **0** (verified 2026-09-17) — so appliqué's gates print engine prose to
  customers today. `app/src/lib/digitizer.spec.js` pins a **hand-maintained** code
  list, so the test passes while the copy is missing.
- **Skip the per-shape override.** Appliqué's `Region.meta["applique"]` is read twice
  and **written by nothing** — `apply_shape_edits` never writes it and it is absent
  from `_CARRIED_META_KEYS` (reported 2026-09-17 — integration lane). Copying that
  pattern ships another dead path. Design-wide boolean only, modelled on `edge_cap`.
- **`test_puff_off_is_byte_identical`**, copied from `test_applique.py:194-205`. Assert
  on exported **DST bytes**, not stitch counts — that test's docstring gives the
  reason: "a count can stay equal while geometry moves."

**Cost estimate:** ~700–900 lines for `stage6_puff.py` (lighter than appliqué — no
fabric piece, no cutting-line solver, no placement-error model; heavier because caps
are new geometry), ~500–700 lines / 30–40 tests, ~120 lines of constants, ~50 config,
~10 stage 7, ~40 preflight, ~30 warnings, ~60 Studio. **Call it ~1,500 lines and 35
tests.** The step-plumbing PR is separate and small (~150 lines across three files).

**Free and worth doing before any of it:**

1. **Measure the stitch-count ratio.** Digitize one fixture at 0.40 vs 0.18 satin
   spacing, read `StitchPlan.stats`. This settles the sharpest contradiction in the
   dossier and it is the number the pricing story rests on.
2. **Render a 3–11 mm column.** DOCTRINE's standing rule, and it costs nothing.
3. **Doc hygiene** (§1): the stale 3.0, the false `[V]` label on `inset_mm: 0.2`, the
   0.18 provenance, `craft-laws.md:9` vs `:131`, and the Hatch-is-Wilcom collapse.

**The JS engine is out of scope for phase 1, and say so explicitly.** `src/` has no
block, step or stop container — it emits a flat array with `{type:"color"}` records —
and `app/src/lib/generate.js:101` hardcodes `satinMaxWidthMm: 3.0`, the puff band's
floor. Puff would be a **service-route-only** capability. Do not let the two engines
diverge silently the way `SATIN_MAX_WIDTH_MM` already did.

---

## 5. The step/stop IR: built, validated, and reaching nobody

`craft-laws.md:98` called this "built but orphaned" on 2026-08-18. **It is still
literally true a month after appliqué shipped** (all verified 2026-09-17):

- `Step` at `stage6_applique.py:761`, `as_meta` `:786`, `assert_steps_valid` `:804`
  (it **raises**, not warns, on a colour-change step with an empty action),
  `plan_steps` `:818` — documented as "THE READ INTERFACE".
- **`plan_steps` has zero production callers.** The only call sites are
  `test_applique.py:1002`, `:1021`, `:1085`.
- `digitizer_service/app.py:721-725` builds its block payload as
  `{**cone, "shape_ids": …, "design_edge"?}` — `block.step` is not read.
- `src/pdfsheet.js:261` still prints `(i + 1) + ". " + (color.name || "Color " + (i + 1))`
  under a heading called "Thread Sequence".

And `stitches.py:117-118` asserts the opposite — that the step dict "rides the service
response with no schema work". **It does not.** The invariant is enforced on data that
reaches no consumer.

**The good news, against the pessimistic read:** the container is genuinely generic.
`Step`'s appliqué-flavoured fields (`material`, `piece`, `layers`, `spm`) all default
to empty; `assert_steps_valid` tests exactly one thing; `plan_steps` treats
`block.step` as an opaque dict and synthesises a thread-change step for ordinary
blocks. `PLACEMENT/CUTTING/TACKDOWN/COVER` are run **kinds** consumed by `_tie_layers`,
not Step fields. **No refactor of a shipping tier is implied** — the cost is a move (or
an import) plus three plumbing hops appliqué itself never paid.

---

## 6. Claims the adversarial pass KILLED

These were in the dossier's riskiest-claims list and did **not** survive. They are
recorded so nobody rebuilds the argument.

### K1 — "The end-cap is the #1 engine change and it is new geometry nobody has published" — REFUTED 3/3

Broken on the spec's own text. `:384` says the reason caps exist is **release** — "every
puff region must be enclosed by a closed loop of needle penetrations" — and `:466-475`
then makes method #3, a **bean perimeter run on the element outline**, the BASELINE
("maps directly onto our existing bean tier and is the cheapest high-value addition we
have"). An outline run already closes that loop. We already ship an emitter of that
shape: `stage6_border.silhouette_cap`, three passes, default ON. Happy's OEM note gives
a second cheap published answer — 1 mm running stitches across the end, before the
satin. **Only method #1's tapered perpendicular satin bar is invention**, so "~40 %
invention" is unsupported. And it is not #1: the engine cannot emit 6.5–11 mm of the
legal band at all, and `SPLIT_SATIN_ABOVE_MM = 5.0` actively crushes what it does emit.
**What survives:** if method #1 is built, its dimensions are sew-out-gated from day one.

**Also killed, and important — the "capped puff FONTS are cheaper" counter-proposal.**
Melco and Ricoma ship *pre-digitized stitch* alphabets; EMB-Bot's fonts are
**parametric** (`src/fontbin.js` stores rails/rungs, `src/satinfont.js` generates satin
at render time), so a capped puff font here **is** the cap generator applied to font
outlines. It is browser-only, that engine's ceiling is 3.0 mm, and the Python pipeline
has no font path at all. **Fonts do nothing for the raster-logo product.**

### K2 — "Revenue is a flat $7–9/logo surcharge against a cost concentrated in three half-built places" — REFUTED 3/3

Four breaks. **(a)** "Flat" misreads the unit: the price list quotes "$7.00 EACH LOGO"
under a 6-piece minimum per logo per location — a **per-piece** surcharge, which
against ~2 min of handling is ~$210/hr of marginal labour. **(b)** It merges two
businesses — the shop's per-piece revenue and EMB-Bot's one-time digitizing fee
($15–50). **(c)** The dossier's own sources contradict the shape: Gunold says "at least
25 % more", aggregators say 25–50 % markup — **a percentage of a stitch-priced flat
price does scale with stitch count**. **(d)** "Three places already half-built" omits at
least four that are not built at all and are shared with nothing: no region-selection
predicate (and appliqué's per-shape template is a dead path), zero Studio surface,
preflight actively firing on a correct design, and the JS engine having no block
container. **The Ember half holds** — zero mentions across three teardowns.

### K3 — "The step/stop IR carries appliqué-shaped assumptions, so 'free' becomes a refactor" — REFUTED 3/3

The feared risk is not there (see §5): optional fields with neutral defaults, one
assertion, a tier-agnostic reader, kinds that live outside `Step`. **"Free" is still
false, for a different and verified reason** — the output reaches no consumer. *Free up
to the Python plan object, and nothing past it.*

### K4 — "A 0.18 mm puff satin will not trip the coverage grader (~2.7 units vs a 6.67 warn line)" — REFUTED 2/3

**One lens actually ran it** and the *conclusion* holds with ~2× headroom: a 5 mm column
at 0.40 mm reads p50 0.98; at 0.18 mm it reads p50 2.18 / max 2.36; the full stack
(cover + 2-pass tackdown + 3-repeat bean, all on one rail line) peaks at **3.32**, against
`COVERAGE_WARN_UNITS` 6.67 and `COVERAGE_BLOCK_UNITS` 9.33 (verified 2026-09-17 —
`machine.py:872-873, 888`, off `FILL_ROW_MM = 0.15` at `:75`). But the **stated number
was wrong** (~2.7 omitted the cap and perimeter layers), and the claim points at the
wrong instrument: on the same run the 0.18 pass **fired `DENSITY_EXTREME`**. The stale
comment is confirmed verbatim: `machine.py:788` still says "the ribbons tile and the map
reads exactly 1.0" seventy-three lines above `:861-870`'s "a single plain fill now reads
0.40 / 0.15 = 2.67 units". **Anyone sizing puff from the first comment is off by 2.67×.**

### K5 — "Only satin over foam, and interior penetrations forbidden — our config would refuse what two vendors require" — REFUTED 2/3

The scoping bug is **real and worse than stated**: the spec refuses its own mandatory
pass. `:614-616` lists `stitch_penetrations_inside_shape` in `forbidden` while `:489-494`
prescribes a 2-pass walk 0.2 mm *inside* the boundary, and §3.5's cap puts a second
satin object under the column (verified 2026-09-17 — I read both blocks). §3.11:627
shows the rule was scoped to the **cover** pass. But: **there is no config** — nothing
refuses anything today, so "makes a first sew-out fail" is wrong; it is a spec defect an
implementer would inherit. And the fill half is **not** a blind spot — `:480` already
records Wilcom's exception, reasons about it, and forbids it as *auto output*, which is
a scope call. **Carry the interior-penetration scoping fix; drop "both halves".**

### Survived: K6 — the spec's provenance claim ("nothing here is invented") does not hold — 2/3 held

Covered in §1. The one correction the lenses insisted on: **do not quote
`research-partials-2026-07-31.md:22` as evidence.** It proves a stale table, not a
tainted spec.

---

## 7. Open contradictions — unresolved, listed as open

1. **Puff satin density, three ways inside §3 itself**: prose clamp `[0.15, 0.20]`
   (`:422`), config `spacing_range_mm [0.16, 0.20]` (`:564`), failure table `0.16–0.18`
   (`:623`). Only the 0.18 target is consistent.
2. **Compensation semantics**: prose says "+0.3–0.4 **over** flat-satin compensation"
   (`:505`, a delta); config says `value_mm: 0.35` (`:571-575`, an absolute). An
   implementer reading the YAML gets a different number than one reading the prose.
3. **Compensation convention** — the genuine split, and worse than §3 says: one house,
   both signs, in two of its own documents.
4. **End-cap density** — Melco 0.30 vs Hatch 0.16, 2× apart, opposite stated purposes.
5. **Tackdown path** — Melco/repo edge-inset ×2 at 2.0 mm vs Hatch centre-run ×1 at
   4.0 mm; Melco's own help article permits either ("Edge Walk or Center Walk").
6. **Max satin width** — Hatch 7 (self-declared as *its own auto-split trigger*, not a
   foam limit), Melco 11, Wilcom 12.
7. **Needle** — five sources, five answers, opposite mechanisms.
8. **Speed** — 500–750; one source calls 600 a hard friction-melt threshold, which would
   make our 750 upper bound affirmatively wrong.
9. **Foam stacking** — Wilcom/Ignition forbid; Madeira sells it; Happy (OEM) endorses it.
10. **Foam max thickness** — "don't recommend over 4 mm" vs Melco's 5 mm shank limit vs
    6 mm stocked by two vendors.
11. **Dry-cleanability** — Gunold Dense says yes, PuffyStitch and Sulky say no.
    Brand-level material difference, unresolved.
12. **Stitch count, puff vs flat** — Melco: "generally very low"; web sources: 1.9–2.0×.
    Probably different denominators. **Measurable locally in one run.**
13. **Water-dissolvable puff ("Puff Stuff")** — vendor claims *no stitch-setting changes*
    and *suitability for fine detail and small lettering*, which are precisely the two
    constraints the whole spec rests on. Marketing copy, no independent source, and its
    own restriction to non-wearables may put it outside the caps market anyway. **Treat
    as a hypothesis to sew, not a spec.**
14. **`tires_hat_3d`** — one of our own scorecard fixtures is a 3D-puff design, and four
    docs give four accounts of what that costs. `docs/stage0-tires-photo-scene-2026-09-11.md:448-468`
    goes furthest: the pro's file is a 279-stitch "Puff Grip" tack plus a 5,359-stitch
    "Black 3D" on **one thread with a foam stop**, so a colour- or block-count comparison
    against it is measuring puff *procedure*. `digitizer/tools/pro_parity/smoke.py` scores against
    it. Nothing reconciles the four (reported 2026-09-17 — doc-sweep lane).
15. **`MASTER_SCOPE.md` has zero lines on appliqué, puff, foam or specialty** across 839
    lines, while `PRODUCT.md:98-99` says that is exactly where a capability's status
    belongs (reported 2026-09-17 — doc-sweep lane). Puff would be built beside a
    capability the live dashboard does not know exists.

---

## 8. Scope reality — the decision is Kent's and is not made

`PRODUCT.md:67` lists **3D puff** in the explicit non-goals parking list (verified
2026-09-17). **The appliqué precedent does not transfer.** Appliqué left that list on
2026-09-14 because 1,373 lines and 58 tests had *silently already been built* and the
doc "said the product would not do something it could already do". For puff, after
`git fetch --all`, `git log --all -S puff -- digitizer/ src/ app/` returns four commits
whose diffs mention puff only in comments; the only tree hits are the `structured_cap`
fabric note (that "Foam" is the cap's own buckram, not puff foam) and two
forward-looking comments in `stitches.py` (reported 2026-09-17 — doc-sweep lane;
`fabrics.py:31` and `stitches.py:110, :241` verified 2026-09-17). **There is nothing to
discover. This is a genuine scope addition, not a correction of the record.**

What signing up for it means, honestly:

- **Roughly 1,500 lines and 35 tests**, plus a ~150-line step-plumbing PR that is worth
  doing on appliqué's account alone.
- **Service-route only.** The browser engine cannot emit a single legal puff column.
- **It ships OFF and stays OFF until a sew-out.** Five parameters cannot be chosen from
  any document — cap density, cap dimensions, compensation, the minimum void, and the
  physical same-needle halt. Two of them (min void, cap dimensions) are the difference
  between a puff design that tears clean and one that does not.
- **The ceiling problem is real and separate.** Even a perfect puff tier is limited to
  3.0–5.0 mm columns today, and moving that is its own measured-negative-laden project.

What it is worth, honestly: the revenue evidence is **weak in both directions**. The
per-piece surcharge figures are real but come from one shop's list and aggregator blogs;
the "door-opener for cap accounts" story is unmeasured; and the tracked competitor does
not do puff at all, which is mild evidence *against* parity pressure rather than for it.
One of our own benchmark fixtures being a puff design is the strongest in-repo argument,
and it argues for understanding puff, not necessarily for shipping it.

What it competes with: the step-IR plumbing (which appliqué needs today), the satin
ceiling work, and whatever is next on the ROADMAP. **My read: the honest sequencing is**

1. **Five minutes at the Tajima** — write a two-block same-thread DST, enter the needle
   twice, press start. Does it halt? That unblocks three tiers and costs nothing.
2. **The step-IR plumbing PR** — valuable whether or not puff ever ships, and it is the
   reason appliqué's worksheet is invisible today.
3. **The free measurements** — the 0.40-vs-0.18 stitch-count run, and a render of a
   3–11 mm column.
4. **Then** the scope call on `PRODUCT.md:67`, with those three results in hand.

Building `stage6_puff.py` before step 1 is building on a question that takes five
minutes to answer.
