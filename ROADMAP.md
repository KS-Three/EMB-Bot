# EMB-Bot — Roadmap

Itinerary and dependency gates. **Not a status doc** — status is `MASTER_SCOPE.md`,
history is `docs/scope-history.md`, evidence is `docs/scope-digest/`.

**The rule that keeps this file honest: no numbers, no dates, no status, ever.**
Only phase names, exit conditions, gates and pointers — so the only thing that can
go stale is a phase genuinely completing, which is an event someone notices.
Budget: 60 lines. Over it, cut or move — never grow.

**Only Kent advances a phase.** Claude may propose an advance, with evidence, and
must say so out loud. It may not move the marker itself.

## Where we are

**Phase 1 — Foundation.**

## Engine track

1. **Foundation — a yardstick that agrees with Kent's eyes.** The scorecard
   measures conformance to one professional's choices, not quality: changes that
   visibly improved a garment have scored *worse*.
   *Exit:* on real customer designs, the metric's ranking agrees with Kent's
   visual ranking, and nothing he judges better ever scores worse.
2. **Framing — the engine sees the image correctly.** Stage 0 is not
   scale-invariant: one artwork reaches different lanes purely by export
   resolution, and most real logos reach the wrong one.
   *Exit:* the same artwork routes the same way at any export resolution, and
   real logos reach the lane their content actually is.
3. **Dry-in — right technique, coherent path.** Satin-vs-fill placement, the
   satin width floor, and fragmentation into far more runs than a pro uses.
   *Exit:* stitch-type agreement clears its chance floor by a real margin, and
   trim rate sits under the ceiling this repo's own chaining test pins.
4. **Finish — tonal work.** Gradient and photo art. Tabled by Kent.
   *Exit:* tonal artwork stops being a special case.
5. **Inspection — sew-out.** *Exit:* thread has met cloth.

## Launch track — parallel

Neither gates nor is gated by the engine track (Kent's standing ruling). Open: the
starter design pack, which needs a sourcing decision, and billing.

## Hard gates — refuse, name the blocker, stop

1. **No sew-out, no physical constants.** Fill row spacing, the satin width floor,
   link cover tolerance, fabric presets, DST orientation. Fabric settles these,
   geometry cannot.
2. **No stage-0 recalibration without real tonal artwork.** Four approaches were
   measured and rejected; synthetic fixtures are barred as substitutes.
3. **No default-OFF tier flipped on until its instrument is rebuilt.** Chaining,
   contour, tonal-region splitting. A green suite has already hidden needle-down
   thread on bare fabric here.
4. **No quality claim on a raw agreement number.** Use the chance-corrected
   figure — raw moves when the mix moves, so a "gain" can be the floor shifting.

## Advisory ordering — state it, never enforce it

Hoist the distance transform before the satin work that depends on it. Pull
compensation before underlay. Sequencing laws ship together or trims show.
Validate on a dozen designs, not five. Measure in a pinned worktree.

## Standing item

A red `main` is scaffolding left standing: nothing can be judged by "same failure
set" until it is green. Re-capture goldens on Linux, never on Windows.

## Before proposing any work

Read `MASTER_SCOPE.md` for status and `docs/scope-digest/` for what has already
been built, measured and rejected. Those do-not-rebuild records are the most
expensive knowledge in this repo.
