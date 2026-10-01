# Plan 1 of 3 — cut a hole in a hand-drawn shape

Spec: [`2026-09-30-manual-digitizing-gaps-design.md`](../specs/2026-09-30-manual-digitizing-gaps-design.md).
Rulings this plan implements: **3** (a drag clamps at containment), **4** (mode
buttons on the side canvas), **10** (the hole floor is the existing sewability
floor). Plans 2 (columns) and 3 (runs) come off the same spec and are not
started until this merges.

**Why this one first.** It needs no engine change at all — `digitize.js` has
read `shape.holes` since Image mode shipped (`:612`, even-odd fill at `:661`,
pull-comp inset with the winding-flip guard at `:727-733`, running outline at
`:228`) and `manualShapes.js:609` simply hardcodes `holes: []`. So it proves the
`holes` half of the model and the authoring surface with zero risk to any
golden.

## Task 0 — baseline

- [ ] **Step 1** — Worktree is on `claude/manual-holes` at `origin/main`
      (already current with #586, verified 2026-10-01). Re-check the line
      anchors this plan quotes before trusting them; they move weekly.
- [ ] **Step 2** — Baselines, recorded in the PR body: `node --test` from the
      repo root, and `cd app && npm test` — read the RUN banner, never a tail
      (CLAUDE.md: a piped `tail` reports its own exit code and a red run reads
      green).

## Task 1 — the model and the hand-off (`lib/manualShapes.js`)

- [ ] **Step 1: failing tests** in `app/src/lib/manualShapes.spec.js`:
      - `shapesToRegions` on a shape with one hole emits `holes: [ring]`, the
        ring flattened with `closed=true` like the shell.
      - A shape with `holes` absent, `[]`, or holding only invalid rings emits
        `holes: []` — **the byte-identity case for every design saved before
        today.**
      - New `holeIssues(shellFlat, holeFlat, otherHolesFlat)` returns `[]` for a
        hole fully inside, and a reason string for each of: a point outside the
        shell, a segment crossing the shell, a segment crossing another hole,
        under three points, self-crossing, under the area floor.
- [ ] **Step 2: implement.**
      - `holeIssues` beside `shapeIssues`, reusing the module's own
        `pointInShape` (`:152`) and private `segmentsIntersect` (`:58`) — no new
        geometry primitives. Reason strings, not a boolean, matching
        `shapeIssues`' established pattern so callers can say WHY.
      - The area floor is the existing `MIN_AREA_PX2` (ruling 10). Do **not**
        introduce a second constant.
      - `shapesToRegions`: `holes` = each `flattenShape(h.points, h.curves, true)`
        kept only when `isValidShape` agrees. An invalid hole ring is dropped,
        not thrown — the posture the function already takes on an invalid shell.
      - `defaultManualShape` (`lib/project.js`) gains `holes: []`.
- [ ] **Step 3: verify** — `cd app && npx vitest run src/lib/manualShapes.spec.js`,
      then full `npm test`. Engine suite untouched and still at baseline.
- [ ] **Step 4: commit** — `manualShapes: a hand-drawn shape carries holes, and they reach the engine`.

## Task 2 — containment is an invariant (`lib/fieldNodeEdit.js`)

- [ ] **Step 1: failing tests** in `app/src/lib/fieldNodeEdit.spec.js`:
      - `holesContained(shape)` — true for a hole inside, false when the shell
        is pulled across it, false when two holes cross.
      - `editedElementPatch` refuses an edit that breaks containment with
        `{ error }` carrying the hole reason, exactly as it already refuses a
        self-crossing shell.
      - A hole-anchor drag that stays inside commits and **nothing unedited
        moves** — #570's invariance assertion extended to holes: unedited points
        move by at most the engine's offset-rounding residual (≤ 0.05 mm/axis)
        and `mmPerPx` holds to 1e-12.
      - `flatBBox` is unchanged by holes (a hole is inside its shell, so the
        design bbox cannot move). Pin it, so a later change has to argue.
- [ ] **Step 2: implement** — export `holesContained(shape)`. It is the clamp's
      predicate AND the patch's guard, and those two must never disagree: one
      function, two callers. `editedElementPatch` calls it after its existing
      `shapeIssues` check.
- [ ] **Step 3: verify + commit** — `fieldNodeEdit: a hole stays inside its shell, and an edit that breaks that is refused`.

## Task 3 — Hole mode on the side canvas (`ManualPanel.svelte`)

Ruling 4: a segmented strip above the existing draft buttons. **This plan ships
two segments — `Shape` and `Hole`.** `Column` and `Line` arrive with plans 2 and
3; do not build disabled placeholders for them.

- [ ] **Step 1: failing tests** in `ManualPanel.spec.js`:
      - The strip renders, `Shape` is the default, and `Hole` is **disabled with
        its reason** when no shape is selected.
      - In Hole mode, `Finish shape` commits the draft into
        `selectedShape.holes` rather than appending a shape — the shape count
        does not change.
      - A draft that breaks containment surfaces the `holeIssues` reason and
        `canFinish` is false.
      - `Enter` finishes a hole draft exactly as it finishes a shape (the
        existing `canFinish` gate, `:675`).
      - Switching mode clears the draft — a half-drawn shell is not a hole.
- [ ] **Step 2: implement.**
      - `let drawMode = "shape"` plus the strip, styled as #564's hoop strip:
        same tokens, same `aria-pressed` pattern, a segment is a pick not a
        toggle.
      - `draftIssues` branches on the mode — `shapeIssues(draftFlat)` for a
        shape, `holeIssues(...)` for a hole. Shape mode is byte-identical.
      - `finishShape` branches: hole mode patches
        `shapes[selected].holes = [...holes, { points: draft, curves: draftCurves }]`
        through the same `patch()` every other edit uses (one undo step), then
        clears the draft. Recompute validity fresh rather than reading the
        reactive value — the reason the comment at `:226-229` already gives.
      - `drawShape` already takes `closed` and a `fillStyle`: draw a holed shape
        as one even-odd path here too. Leaving the shell solid on the drawing
        surface would make it disagree with both the hoop canvas and the
        stitch-out.
- [ ] **Step 3: verify** — `npm test`, then drive it: draw a shape, select it,
      Hole mode, draw inside, Finish, see the hole. Screenshot.
- [ ] **Step 4: commit** — `ManualPanel: Hole mode — draw a hole inside the selected shape`.

## Task 4 — the hoop canvas (`EmbroideryField.svelte`)

- [ ] **Step 1: draw it** — the manual branch of `drawShapeOutlines` draws shell
      + holes as one even-odd path, and a selected shape's hole anchors get the
      amber dots and green handles #570 gave the shell. Every node-edit repaint
      goes through `repaintNodeChrome()`, never a bare `drawOverlay()` — #570's
      smear lesson, recorded in its own comment.
- [ ] **Step 2: address a hole's nodes** — `focusedAnchor` and the
      `authoredInFieldMm` / `hitAuthored` pair gain a `holeIndex` (null = the
      shell). Hole anchors are then hit, dragged, bowed, inserted and removed by
      the functions that already exist; only the address widens.
      `removeAnchor`'s floor of three applies per ring.
- [ ] **Step 3: the clamp (ruling 3)** — in the node-drag pointermove, after the
      existing `clampAuthoredToBox`, build the proposed shape and test
      `holesContained`. On failure keep the last good position and show *"A hole
      has to stay inside its shape."* Same posture as the placement-box clamp,
      which `clampMmToBox`'s comment records as Kent's ruling. **Do not** refuse
      the edit the way the digitized lane's `apply_shape_edits` does.
- [ ] **Step 4: verify** — drag a shell anchor inward until it stops at the
      hole; drag the hole's own anchor outward until it stops at the shell; no
      smear; nothing else in the design moved. Screenshots at 1440×900 and
      1024×768.
- [ ] **Step 5: commit** — `Field: holes draw even-odd, their nodes edit, and a drag clamps at containment`.

## Task 5 — say that a hole forces fill (`lib/shapePopover.js`)

Engine law, not a bug to route around: `digitize.js:619` drops the satin tier
whenever `holes.length` is non-zero, because satin cannot go round a hole.

- [ ] **Step 1: failing tests** (`shapePopover.spec.js`): a holed shape's
      `stitchType` row reads Fill and carries the note; the caption
      (`shapePopover.js:76` — `Shape 134 · Satin|Fill`) reads Fill for a holed
      shape even when the stored `stitchType` is `"satin"`.
- [ ] **Step 2: implement** — `popoverModel` adds a note to the `stitchType` row
      when the shape has holes: *"Shapes with a hole sew as fill — satin cannot
      go round a hole."* **Leave the stored value alone** — re-tiering the record
      would lose the author's choice if they later delete the hole; what is
      DISPLAYED is the truth about what will sew.
- [ ] **Step 3: verify + commit** — `Popover: a holed shape says it sews as fill, because the engine makes it so`.

## Task 6 — e2e and the browser

- [ ] **Step 1** — `app/e2e/manual-holes.spec.js` against the live service: draw
      a shape, read the caption's stitch count, cut a hole, assert the count
      DROPPED and the hole is visible. **Sample pixels inside the fabric** via
      the `FABRIC_BOX_SRC` helper the three existing pixel specs carry — #564's
      dark surround breaks any spec that counts dark pixels across the whole
      canvas, and that has already bitten twice (#570's spec, 8/8 failing).
- [ ] **Step 2** — a second e2e: node-edit a hole's anchor on the hoop canvas
      and assert the invariance.
- [ ] **Step 3** — `npx playwright test` in full, logged with the code appended
      (`> log 2>&1; echo "EXIT=$?" >> log`), never piped to `tail`.
- [ ] **Step 4: commit** — `e2e: cutting a hole changes the stitch-out, and editing one moves nothing else`.

## Done means

- [ ] Engine `node --test` at baseline and **no golden re-captured** — if one
      moves, stop: this plan is not supposed to be able to do that.
- [ ] `cd app && npm test` green, read off the RUN banner.
- [ ] `npx playwright test` green in full, from the log's recorded exit code.
- [ ] A manual design saved before this branch generates and exports **byte for
      byte** as it does on `main`. Pin it as a test, not an impression.
- [ ] Driven in a real browser at 1440×900 and 1024×768, screenshots in the PR —
      MASTER_SCOPE's standing rule: a Studio change is not verified until it has
      been looked at, and six buyer-visible defects got in past a green suite.
- [ ] PR ready-for-review, not a draft; auto-merge armed while
      `mergeStateStatus` is `BLOCKED` (budget eighty minutes for `digitizer`, and
      spend one `curl /actions/runs/<id>/jobs` before calling it stuck).
- [ ] PR body names the three rulings implemented, the residue left standing
      (the silent skip of an invalid shape — ruling 3's half Kent did not take),
      and what plans 2 and 3 still owe.

## Not in this plan

Columns (plan 2), runs (plan 3), lock stitches (ruling 7 — its own measured PR,
since `buildQualityDesign` has no tie code at all), drawing on the hoop canvas
(ruling 4 deferred it), closed↔open conversion (ruling 8 excluded it), and holes
on the digitized lane, which already has them.
