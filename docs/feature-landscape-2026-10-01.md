# Feature landscape: Kent's 18-item list against the repo — 2026-10-01

Kent pasted an 18-item list of things no embroidery tool does and asked which
are easy at EMB-Bot's current state. This doc sets each item against the tree
as it stood at `origin/main` `e851e5aa`, with the weight on the items that are
**not** easy, so the reasoning does not have to be re-derived next time.

**How this was checked.** Code and docs were read; nothing was run. Every
status line carries a pointer to the file or symbol that supports it. A
coordinating session sorted the list first from file headers only; where its
claim did not survive a check, the entry says **Corrected**.

**What this doc is not.** It is not a plan and not a commitment. Nothing here
advances a ROADMAP phase or reopens a PRODUCT decision. Those are Kent's.

## The sort at a glance

| # | Item | Verdict |
|---|---|---|
| 1 | Physics-based sew-out simulation | Not easy — no data to build on |
| 2 | Closed-loop learning from stitch-outs | Built, default OFF, blocked on cloth |
| 3 | Auto-digitize that understands structure | Not easy — it is the engine (phases 2–3) |
| 4 | Open object-level interchange format | Cheap to write, hard to make matter |
| 5 | Thread-break prediction | Mostly in the repo; being extended |
| 6 | Accurate time/cost quoting | Easy — sibling lane today |
| 7 | One design, many placements | Partly in the repo; being audited |
| 8 | Machine-specific optimization | Table is easy; re-planning is engine work |
| 9 | Order pipeline integration | Not easy — needs a backend |
| 10 | Batch colour-sequence minimization | Easy maths, no place to live |
| 11 | Version control with stitch diff | Medium — file is git-ready, diff is not built |
| 12 | Stabilizer / needle / topping advice | Easy — sibling lane today |
| 13 | AR hooping and placement | Not easy — product is desktop-only |
| 14 | Design library search by facts | Easy — sibling lane today |
| 15 | Camera thread colour matching | Easy — sibling lane today |
| 16 | Small-lettering engine | Partly built; the gap is construction, plus cloth |
| 17 | Stitch-to-object conversion | Not easy, and a stated non-goal |
| 18 | Live machine diagnostics | Not easy — needs a machine connection |

## Easy — being built today

One line each. Detail lives in each lane's PR. All four branches existed
locally with nothing pushed when this was written.

- **6. Time/cost quoting** — `claude/sew-quote-profiles`. Builds on
  `src/sewtime.js` (`PLAN_SPM`, `TRIM_COST_STITCHES`) and
  `app/src/lib/estimate.js`, both already on `main`.
- **12. Stabilizer, topper and needle advice** — `claude/hooping-advice`.
  Builds on `assumedBacking` / `needsTopper` in `src/fabrics.js` and
  `STABILIZER_CUTAWAY` in `preflight.py`. Needle advice has no trace on `main`.
- **14. Library filter by measurable facts** — `claude/library-filter`. Today
  the index holds only `{id, name, updatedAt, autoName}`
  (`app/src/lib/projects.js`), so a design can be found by name and nothing else.
- **15. Thread from photo** — `claude/thread-from-photo`. Builds on
  `nearestInList` in `app/src/lib/threads.js` and the 68 brand charts
  (`PRODUCT.md` row 5). **Note:** that matcher is plain RGB distance, not
  delta-E. The service side already uses CIEDE2000 (`COLOR_STOPS_HEAVY`'s
  `closest_pair_delta_e`, `DELTA_E_VISIBLE` in `preflight.py`).

## Already in the repo — being extended

### 5. Thread-break prediction

**What exists.** `digitizer/digitizer_core/preflight.py` already reads a
finished plan for most of what the list asks:

| The list asks for | What `preflight.py` has |
|---|---|
| Density stacking over 3 layers | `DENSITY_STACKED` — `_coverage_findings`, whole-plan coverage map, warn at 2.5 and block at 3.5 fill layers, with the location of the worst patch |
| Stitches under 0.5 mm | `STITCHES_TOO_SHORT` — `_stitch_length_findings`; `machine.TINY_STITCH_MM = 0.5` |
| Needle penetration clusters | `SAME_HOLE_HEAVY` — `_same_hole_findings`, with max strikes and where |
| Tight gaps | `SATIN_GAPS_TIGHT` — `_tight_gap_findings` |
| Sharp satin angles under 15° | **Nothing.** No angle check in the file |

**The gap.** These are five separate findings, each with its own wording. None
is presented as "break risk here", and there is no sharp-angle check. The
`claude/break-risk` lane (queued) is the one to close that.

**The catch.** The block threshold on coverage is sew-out-gated
(`docs/scope/machine-physics-backlog.md` row 12). A break-risk score can be
shown; a break-risk *number* cannot be claimed as measured (gate 1).

### 7. One design to many placements

**What exists.** Ten garments with placement boxes (`GARMENTS` in
`src/garments.js`), hoop fit (`suggestHoop`, `hoopFit`), and fabric presets
(`src/fabrics.js`).

**Corrected.** The coordinator wrote "cap ordering in `digitize.js`" as if one
thing. It is two, and they disagree:

- **Browser engine: cap order is ON.** `capMode` in `src/digitize.js` sews
  centre-out per colour block for `hat_front` and `beanie`, for both artwork
  and lettering.
- **Python engine: cap order is built and parked OFF.** `cap_center_out: bool
  = False` in `digitizer_core/config.py`, pinned by
  `tests/test_cap_center_out.py`. Measured cost was +111% travel, and the one
  professional cap-versus-flat pair in the corpus backs bottom-up while
  contradicting centre-out (`.claude/memory/cap-order-and-the-pair-experiment-2026-09-19.md`,
  DOCTRINE "Measured negatives").

So "one click per placement, sew order rebuilt" is true where the browser
engine sews (typed lettering, browser-traced art) and false for the
service-digitized lane, which is the lane a customer's logo goes through.

**What blocks it.** The config comment says it plainly: "only cloth settles
it". Flipping `cap_center_out` on is a gate-1 question. The "more comp on
caps" half is a fabric-preset constant, also gate 1.

**What is not blocked.** Auditing that a placement change re-fits, re-hoops
and re-sequences consistently across both engines — the queued
`claude/placement-retarget` lane.

## Already in the repo — blocked on cloth

### 2. Closed-loop learning from stitch-outs

**What exists.** The whole loop, end to end, merged in PR #569 on 2026-09-30:
download a test card, sew it, photograph it, and the reader returns a draft
fabric profile of three adjustments that both engines sew under
(`digitizer_core/calibration/` — `card_v2.py`, `reader.py`, `profile.py`;
`app/src/lib/calibration.js`; `MASTER_SCOPE.md` "Closed-loop sew-out
calibration SHIPS"). Default OFF.

**How it differs from the list.** The list says a camera on the machine. This
reads a **phone photo of a sewn test card**
(`docs/sewout-calibration-brief-2026-09-30.md`). It tunes a fabric preset. It
does not compare a finished customer design back to its file.

**What blocks it.** No photo of a sewn card exists. The reader recovers
planted pull values to 0.01 mm on a *simulated* photo, and the brief says so:
"every number in it is still a number about a picture." Phase 0 — sew the card
and photograph it — was deferred by Kent. `MASTER_SCOPE.md` "No CONTROLLED
sew-out card has been sewn" is the standing status.

**What unblocks it.** One hooping. That is the only thing between this and a
real reading. Gate 1; Kent's 2026-08-21 ruling is that the sew-out is accepted
as-is and is not to be re-raised as the next action, so this doc records it
and does not push it.

### 16. Small-lettering engine

**What exists.**
- 85 satin fonts built for stitches (`PRODUCT.md` row 7).
- `LETTERING_TOO_SMALL` at a 4.0 mm floor — `_lettering_findings` in
  `preflight.py`.
- `LETTERING_ILLEGIBLE` — `digitizer_core/legibility.py` reads the thread
  render with OCR and compares it to the artwork.
- Text detection and redraw on traced art — `textcluster.py`.
- Minimum column width warnings — `MIN_COLUMN_MM`, `STITCHES_TOO_SHORT`.

**Corrected.** The coordinator wrote that making this reliable "means settling
the satin width floor, a gate-1 constant". That is half of it and the smaller
half. `MASTER_SCOPE.md` defect 2 records the width floor as **disproved for
flat art**: 61 of 64 sub-1.0 mm satins on real logos are ground the
professional also satined. And the professional's own file sews a tagline
legibly in 0.8 mm satin
(`.claude/memory/pro-files-refute-scale-limit-2026-09-03.md`). So the engine's
loss on small traced lettering is how it *constructs* the letters, not a
physical limit.

**What blocks it.**
1. Construction on traced lettering — ROADMAP phase 3 work, tracked in
   `docs/superpowers/plans/2026-09-19-lettering-construction.md`.
2. "Auto-comp per fabric" is the pull-compensation table, one scalar per
   preset today (`docs/scope/machine-physics-backlog.md` row 2). Gate 1.
3. The OCR check is a lower bound, not a guarantee — `legibility.py`'s own
   header lists a case where it reads 1.00 on a render missing a letter arm.

## Not easy

### 1. Physics-based sew-out simulation

**What exists.** A thread renderer, `digitizer_core/stitchviz.py`. Its own
header rules it out as a simulator: "no thread tension, no fabric distortion
or pull, no nap, no needle-penetration dimple, no bobbin show-through." It
draws where the thread was told to go, not where cloth lets it land.

**What blocks it.** There is no data. A distortion model needs measured pairs
of "what the file said" against "what the cloth did", across fabrics and
backings. The repo has one uncontrolled sew-out of one icon on one fabric
(`MASTER_SCOPE.md`, 2026-09-01). The fabric presets are the same thing the
list criticises in Wilcom and Hatch: compensation numbers.

**What would unblock it.** Item 2. The calibration card measures pull per
column width on real cloth. Enough sewn cards across fabrics is the dataset a
first, honest simulator would be fitted to. So the order is: sew the card,
collect readings, then model. Skipping to the model produces a picture that
looks like physics and is not.

**Runs into.** Gate 1, directly. Any distortion figure shown to a customer
before cloth backs it is a physical constant with no sew-out.

### 3. Auto-digitize that understands structure

**What exists.** This is the product's main engine, and parts of the list are
already there: text detection (`textcluster.py`), satin-or-fill choice per
shape, underlay, sequencing and trims (stages 5–7), a direction field for
photo fills (`directionfield.py`, `stage6_streamline.py`), layer order.

**Honest status.** `MASTER_SCOPE.md` area 1: "In progress · Low confidence
beyond flat spot-color art", human faces tabled. Kent's own eye puts the
stitch-outs near 60% of the competitor benchmark
(`.claude/memory/kent-eye-vs-instruments-2026-08-27.md`).

**What blocks it.** It is ROADMAP phases 2 and 3, in order, and phase 1 (a
yardstick that agrees with Kent's eye) is not exited. There is no shortcut
feature here; "understands structure" is the sum of the engine's open defects.

**On "AI can finally do this".** Checked, not assumed. A general segmentation
model was measured as a region former for logo art and refuted
(`docs/sam2-on-logo-art-2026-09-22.md`), and a tooling sweep found no
repository, plugin or model that improves digitizing
(`docs/tooling-research-2026-09-12.md`). A model that knows "that is fur" does
not exist in the tree; the direction field follows image gradients, it does
not name materials.

**Runs into.** Gate 2 (no stage-0 recalibration without real tonal artwork),
gate 3 (chaining and contour stay OFF until their instruments are rebuilt),
gate 4 (no quality claim on a raw agreement number).

### 4. Open object-level interchange format

**What exists.** `.embproj` — `app/src/lib/projectFile.js`, a versioned JSON
envelope around the project (`PROJECT_FILE_VERSION = 2`).

**Corrected.** The coordinator called it "already an object-level file". It is
object-level for some content and not for the rest
(`app/src/lib/project.js`):

| Element | What the file stores |
|---|---|
| Lettering (`text`) | Parameters: text, font, size, arc, spacing. Fully object-level |
| Preset shape (`shape`) | The recipe only: kind and parameters |
| Hand-drawn (`manual`) | The outlines |
| Auto-digitized (`digitized`) | The source image, the settings, per-shape overrides, and the **baked stitches** |
| Imported file (`design`) | The raw DST bytes |

So for a traced logo — the common case — the file holds stitches plus a recipe
to regenerate them, and regenerating needs this engine. Another tool could not
open it and get editable satin columns. It also names fonts by this library's
keys.

**What blocks it.** Two different things.
1. *Engineering, medium:* a real interchange format needs the auto-digitized
   lane to save its objects (columns, fills, angles, underlay) rather than
   their stitches. That is a new export of the plan, not a doc.
2. *Adoption, not engineering:* the list says it itself — "political, not
   technical". A spec nobody else reads is documentation of our save file.

**Cheap and honest today:** publish the `.embproj` layout as documentation,
described as what it is. That is a scope call for Kent, and it would freeze a
format the app still changes.

### 8. Machine-specific optimization

**Corrected.** `app/src/lib/machines.js` exists on `main`, but it is not a
behaviour profile. It maps a brand to the file format it reads — seven rows of
`{id, label, format}`. Nothing in the tree knows a machine's needle count,
trim time or maximum stitch length per brand. The engine has one set of limits
for every machine (`machine.py`: `MAX_STITCH_MM = 12.1`, `PLAN_SPM = 650`,
`TRIM_COST_STITCHES = 120`).

**The easy half.** A profile table — speed, trim cost, needles — feeding the
*quote*. That is in `claude/sew-quote-profiles` today. It changes what the
operator is told and never where a needle goes, so gate 1 does not apply
(the reasoning is in `src/sewtime.js`'s header).

**The hard half.** Using a profile to *re-plan* a design: re-sequence to fit a
needle count, re-split for a shorter maximum stitch, trade trims for travel
where trims are slow. That is stage 7 work in both engines, and its payoff is
measured in trims and travel — where the engine already has its worst-measured
parity gap.

**What blocks it.** Per-machine numbers are trade-table figures, not
measurements; Kent owns one machine. Re-planning on unmeasured numbers moves
stitches on a guess. Gate 1 for anything physical, phase 3 for the sequencing.

### 9. Order pipeline integration

**What exists.** Nothing. No server, no job queue, no shop connection. The
digitizer service runs on the customer's own machine at `127.0.0.1:8721`.

**What blocks it.** `PRODUCT.md` "Open — not yet decided": backend and billing
are tabled, and the lean is toward projects staying local with no server-side
storage. An order pipeline is a hosted service that holds customer orders and
talks to a store — the opposite posture. The last step, "queued to a specific
machine", also hits item 18's wall.

**What would unblock it.** A backend decision by Kent, first. Then it is
ordinary web engineering, with personalization (the name "Sarah") being the
part the lettering engine can already do.

### 10. Batch colour-sequence minimization

**What exists.** Per-design colour counting only (`COLOR_STOPS_HEAVY` in
`preflight.py` names the closest pair of cones within one design).

**Why it is not easy despite being pure maths.** Assigning needles and
ordering jobs to minimise thread swaps is a well-understood optimisation. The
problem is that the app has no idea of "today's jobs". It holds one open
design at a time and a list of saved ones (`app/src/lib/projects.js`). There
is no queue, no machine with a current needle loading, no day.

**What would unblock it.** A job-list surface in the Studio. That is a scope
call: it turns a digitizing tool toward shop management. No gate applies; it
is a product-direction question for `PRODUCT.md`.

### 11. Version control with stitch-level diff

**What exists.**
- `.embproj` is JSON text and can sit in git today.
- `priorRun` on a digitized element keeps five headline figures from the
  previous run (`app/src/lib/project.js`) — a one-step "what changed".

**Corrected.** The coordinator pointed at `claude/pro-overlay-diff` as a
related local lane. Two corrections. It is pushed to `origin`, not local-only,
and has no PR. And it is **not** a version diff: its tool
(`digitizer/tools/pro_parity/diff.py`, 766 lines) compares our output against
a professional's file of the same artwork. The overlay rendering would be
reusable; the tool does not answer "what changed between v3 and v4".

**What blocks it.**
1. A git diff of an `.embproj` is unreadable for traced art: the baked
   stitches and the base64 source image change wholesale on every re-run.
2. Stitch-level diff needs alignment — two runs of the same design do not
   share stitch indices, so "this column moved" has to be worked out per shape.
3. Branching ("cap version") overlaps item 7.

**Size.** Medium. A visual before/after overlay of two saved versions is the
smallest useful slice and needs no gate. Git-style branch and merge is a much
larger product.

### 13. AR hooping and placement

**What exists.** Nothing on a phone. Placement in the Studio is a garment
picture with a placement box (`GARMENTS` in `src/garments.js`).

**What blocks it.** `PRODUCT.md` launch posture: "Desktop-only, stated on the
site." A tablet audit is listed as a fast-follow, after launch. AR needs a
phone camera, device pose tracking and real-world scale — a separate mobile
app, not a feature of this one.

**What would unblock it.** Reversing the desktop-only decision. Kent's call.

### 17. Stitch-to-object conversion

**What exists.** `src/dstimport.js` decodes a DST into stitches. An imported
design is stored as its raw bytes (`dstBase64` on the `design` element) and
can be placed, recoloured per block and re-exported. There is no object
recovery of any kind.

**What blocks it.** `PRODUCT.md` "Explicit non-goals" lists both
"stitch-level editing" and "imported-design re-density (Wilcom-style stitch
processor)". This item is the larger version of both. On the engineering
side, the list is right that it is a research problem: recovering columns,
fills and underlay from needle points is ambiguous. The nearest thing the
repo has is `diff.py` on `claude/pro-overlay-diff`, which labels passes in a
professional's file per region; its own commit log is nine rounds of fixes to
that labelling, and for our side it reads the tier from the plan rather than
from stitches.

**What would unblock it.** A scope reversal by Kent, then a research spike.
The 37-file third-party DST corpus (`scratch_corpus/`, gitignored) is the only
test material, and it has no object-level ground truth.

### 18. Live machine diagnostics

**What exists.** Nothing reads from a machine. The nearest thing is the
static side: `SAME_HOLE_HEAVY` and `DENSITY_STACKED` already report *where* in
the design the risk is, which is the half of this item that needs no machine.

**What blocks it.** `PRODUCT.md` "Direct send to embroidery machine (WiFi)",
2026-09-30: the S-1501's transfer protocol (RnEmbNet, by Raynen) is closed and
undocumented. If a file cannot be *sent* over that link, break events cannot
be *read* from it. What shipped instead is "save to a folder".

**What would unblock it.** Vendor documentation or an SDK. Or a manual path:
the operator types the stitch number where it broke, and the app shows that
spot with the static findings beside it. That slice needs no machine link and
no gate, and is small. It is not "live".

## What the hard items have in common

Four walls account for all of them:

1. **Cloth (gate 1)** — items 1, 2, 7's cap half, 16's comp half, 8's
   re-planning. One sewn calibration card is the single cheapest unblock in
   this whole list, and it is Kent's standing ruling that it waits.
2. **The engine itself (phases 2–3)** — items 3, 16's construction half, 8.
3. **No backend, local-first (`PRODUCT.md` open decision)** — items 9, 10, 18.
4. **Stated scope** — items 13 (desktop-only) and 17 (non-goal).

Items 4 and 11 sit outside those walls: both are buildable, and both are
blocked mainly by the question of whether they are worth it.

## Corrections to the coordinator's sort, in one place

| Claim | What the tree says |
|---|---|
| Cap ordering lives in `digitize.js` | ON in the browser engine; built and parked OFF in the Python engine (`cap_center_out`) |
| `.embproj` is an object-level file | Object-level for lettering and shapes; baked stitches for auto-digitized art |
| `claude/pro-overlay-diff` is local and a stitch diff | Pushed to `origin`, no PR; it diffs ours against a professional's file, not two versions |
| The machine profile table lands today | True, but `machines.js` on `main` is brand-to-format only; there is no behaviour data yet |
| Small lettering needs the satin width floor settled | The floor is disproved for flat art (defect 2); the measured gap is construction |
| Thread-break checks exist | True for four of the list's five; there is no sharp-angle check |

*(read 2026-10-01 — code and docs at `origin/main` `e851e5aa`; nothing run)*
