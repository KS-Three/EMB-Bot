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

## When this runs

- **Proactively**, as part of finishing PR-sized work — anything that would
  currently earn a COOKBOOK.md entry or a new spec/plan doc. Small stuff
  (typos, doc tweaks) doesn't trigger it.
- **On demand**, whenever invoked directly (`/update-master-scope`) for a
  checkpoint read, even if nothing obviously changed.

## What to do

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
   Cite specifics (file, commit, test count) the way the existing entries
   do; don't soften or round up uncertain findings.
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
6. Update the "Last updated" line at the top.
7. If Kent previously overrode a score, don't silently revert it back to my
   own proposal on the next pass — carry his correction forward unless the
   evidence has genuinely changed since.

## What NOT to do

- Don't turn this into a changelog. It reflects current state, not history —
  that's what git log and the spec/plan docs are for.
- Don't duplicate COOKBOOK.md's architecture/conventions content here, and
  don't let COOKBOOK.md's "Known limitations" section grow back — it points
  here on purpose, to avoid the two drifting out of sync.
- Don't invent a confidence score for anything you can't actually verify.
  `pending sew-out` (or "insufficient evidence" for anything else) is an
  honest answer; a guessed Medium is not.
