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

**Phase 1 — Foundation.** In parallel: **Phase 4 — Finish (tonal)**, un-tabled
by Kent 2026-08-18 (decision record:
`docs/superpowers/plans/2026-08-18-photo-tonal-v1-spec.md`). Phases 2–3 remain
open; phase-4 v1 works around stage 0 with an explicit user override, not by
advancing them.

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
4. **Finish — tonal work.** Gradient and photo art. Un-tabled by Kent 2026-08-18 — v1 in progress.
   *Exit:* tonal artwork stops being a special case.
5. **Inspection — sew-out.** *Exit:* thread has met cloth.

## Launch track — parallel

Starter design pack (sourcing decision and billing pending).

## Hard gates — refuse, name the blocker, stop

1. **No sew-out, no physical constants.** Fill row spacing, the satin width floor,
   link cover tolerance, fabric presets, DST orientation. Fabric settles these,
   geometry cannot.
2. **No stage-0 recalibration without real tonal artwork.** Four approaches were
   measured and rejected; synthetic fixtures are barred as substitutes.
3. **No default-OFF tier flipped on until its instrument is rebuilt.** Chaining
   and contour. A green suite has already hidden needle-down thread on bare
   fabric here. **Tonal-region splitting LEFT this gate 2026-08-19** — Kent's
   spec decision 2, shipped in `d3f3c547`: photo classes split by default
   (`pipeline.effective_split_tonal`), and the config flag is an override that
   can only turn it ON. Re-confirmed as deliberate 2026-09-02. Its density cost
   is real and tracked as a defect, not as a gate.
4. **No quality claim on a raw agreement number.** Use the chance-corrected
   figure — raw moves when the mix moves, so a "gain" can be the floor shifting.

## Advisory ordering
Hoist distance transform before satin work. Pull compensation before underlay.
Standing rules (main-green, goldens-on-Linux, read-scope-first): moved to `MASTER_SCOPE.md` gotchas.