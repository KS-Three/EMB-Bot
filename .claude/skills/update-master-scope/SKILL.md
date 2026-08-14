---
name: update-master-scope
description: Refresh MASTER_SCOPE.md, EMB-Bot's live status dashboard, after PR-sized work changes a capability area's status or confidence, or on request for a checkpoint. Use when asked to update the master scope, project status, or PRD, or proactively after finishing feature/fix work worth a COOKBOOK.md entry.
---

# Updating Master Scope

`MASTER_SCOPE.md` is EMB-Bot's live status dashboard — five capability areas,
each scored on two independent axes (Status, Confidence), plus a
cross-cutting issues list. It exists so Kent and any Claude session can see
where the project actually stands without re-deriving it from specs and
plans each time. Read it in full before touching it.

**It is one file in a set of three, and writing to the wrong one is the
failure mode this skill exists to prevent:**

| File | Holds | Rule |
|---|---|---|
| `MASTER_SCOPE.md` | current state only | **800-line budget** |
| `docs/scope-history.md` | dated snapshots | append-only, never edited |
| `docs/scope/<area>.md` | per-area supporting detail | linked from the verdict |

This split was made 2026-08-14 after a fact-check found 30 of 56 sampled
claims stale and 17 false. The cause was structural, not careless: history and
live status shared one stream, so every historical measurement read as a
current claim. **Note that this skill already said "don't turn this into a
changelog" and the file reached 5,400 lines regardless** — which is why the
rules below are mechanical rather than advisory.

## When this runs

- **Proactively**, as part of finishing PR-sized work — anything that would
  currently earn a COOKBOOK.md entry or a new spec/plan doc. Small stuff
  (typos, doc tweaks) doesn't trigger it.
- **On demand**, whenever invoked directly (`/update-master-scope`) for a
  checkpoint read, even if nothing obviously changed.

## What to do

0. **Classify every single thing you are about to write, before you write
   it.** Ask: *does this still govern a decision today, or was it true at a
   moment?*
   - **Still in force** — a ruling from Kent, a scope call, a known defect, an
     invariant, an open question, a "don't rebuild this" record → **MASTER_SCOPE**.
   - **Was true then** — a test count, a stitch count, a corpus grade, "landed
     PR #N", "the suite is green", "as of today X is broken" → **append to
     `docs/scope-history.md`**, at the top, under its own `**Last updated:**`
     line.

   Two things people get wrong here. **The cut is by force, not by date:**
   Kent's rulings are historical in origin and current in effect, so they stay,
   while an *undated* measurement is still a measurement and still goes. And
   **when in doubt, move it out** — history is recoverable from
   `scope-history.md`, whereas a stale claim sitting in MASTER_SCOPE reads as
   live and gets acted on.

1. Identify which capability area(s) the just-finished work touches. The
   five areas are fixed (don't add/remove/rename one without asking Kent —
   that reopens a structural decision, not a status update):
   - Auto-digitizing quality (image → stitches)
   - Font library & lettering
   - Studio app / guided wizard
   - Export formats
   - Stitch-out review & manual editing tools
2. Re-check that area's Status and Confidence against current evidence —
   new tests, new known issues, a defect that got fixed, a doc that landed.
   Don't soften or round up uncertain findings.

   **Every claim you write in MASTER_SCOPE carries a pointer:**
   `(verb date — source)`. The verb is not decoration and is not optional:

   - `confirmed` — checked against code or a passing test
   - `measured` — a number was produced
   - `suspected` — neither of the above

   A claim with no pointer is unverified by definition; if you find one, either
   verify it or move it to history. **Write `suspected` and mean it.** Two
   hedged observations in this document hardened into stated defects as they
   were copied forward, and measurement later disproved both — a parenthetical
   hedge gets dropped when a sentence is rewritten, a verb cannot be. The
   "Corrections" section exists to keep that pattern visible; don't tidy it away.
3. **Confidence authority is hybrid, not solely mine.** I propose a score
   with cited evidence; Kent has override authority. If a score depends on
   physical machine verification (sew-outs, real stitch quality, fabric
   accuracy) and no new sew-out happened, leave it `pending sew-out` — don't
   upgrade a hardware-dependent score just because the code changed.
4. Check whether the change affects a cross-cutting issue (DST axis bug,
   font license compliance gap, no-sew-out-yet) — update that section too if
   so, and keep it as the single source for that issue rather than
   duplicating detail back into the area row.
5. Update the "At a glance" table to match.
5b. Re-check the **"Waiting on Kent"** section (right after At a glance).
   It is the decision queue — everything blocked on Kent rather than on
   effort. Add an item when work stops for a call only he can make; REMOVE
   one the moment he makes that call, and record the ruling in the area it
   belongs to. A queue that only grows is a queue nobody reads.
6. Update the "Last updated" line at the top.
7. If Kent previously overrode a score, don't silently revert it back to my
   own proposal on the next pass — carry his correction forward unless the
   evidence has genuinely changed since.
8. **Check the budget last: `wc -l MASTER_SCOPE.md` must be ≤ 800.** Over it,
   compact before you finish — do not leave it over and move on.

   **Compact by moving, never by deleting.** In order of preference:
   1. Anything "was true then" that slipped in → `docs/scope-history.md`.
   2. Per-area supporting detail → the matching `docs/scope/<area>.md`, leaving
      the verdict plus a link behind.
   3. A research catalogue or a closed investigation →
      `docs/scope/research-backlog.md`.

   If you genuinely cannot get under 800 without cutting something still in
   force, that is a real signal — say so to Kent rather than deleting it. The
   budget exists to force compaction, not to justify destroying content.

## What NOT to do

- Don't turn this into a changelog. It reflects current state, not history —
  that's what `docs/scope-history.md`, git log and the spec/plan docs are for.
  If you catch yourself writing "Previously," or "Prior update below," or
  stacking a second `**Last updated:**` block above the first, you are writing
  history into the status file. Stop and move it.
- **Don't put test counts, suite totals or corpus grades in MASTER_SCOPE
  prose.** They are stale within a day, nothing reads them, and every one the
  2026-08-14 fact-check sampled was wrong. They belong in `scope-history.md`
  attached to their date, or in the per-area file, or nowhere.
- Don't edit `docs/scope-history.md` to make an old entry true. It is
  append-only; its entries are snapshots and are allowed to be wrong about
  today. Corrections go in MASTER_SCOPE.
- Don't duplicate COOKBOOK.md's architecture/conventions content here, and
  don't let COOKBOOK.md's "Known limitations" section grow back — it points
  here on purpose, to avoid the two drifting out of sync.
- Don't invent a confidence score for anything you can't actually verify.
  `pending sew-out` (or "insufficient evidence" for anything else) is an
  honest answer; a guessed Medium is not.
