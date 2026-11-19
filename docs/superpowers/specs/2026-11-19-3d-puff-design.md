# 3D puff for uploaded logos — design

2026-11-19. Kent's scope call this day took "3D puff" off PRODUCT.md's
non-goals. Spec of record for the technique: `docs/specialty-techniques-2026-08-01.md`
§3 (cited below as **§3**). Reference pro file: `TIRES HAT 3D.PES/.DST`
(`scratch_kent/Embroidery Files/TIRES/fwdyourdigitizingorderisreadytireslogo (1)/`,
gitignored, NOT on every machine — pull it with the `pull-corpus` skill).

## Intent

A customer who uploads a logo can ask for 3D puff and get a file a shop can
sew on foam: the puffed shapes raised, the flat shapes flat, the machine
stopping at the right moment for the operator to lay foam, and a worksheet
that says so. Puff sells at a premium on caps and was parked only because the
project was too early, not because it was out of reach. The bar is the pro's
`TIRES HAT 3D`: one thread, a "Puff Grip" tack-down run (279 st), a stop for
foam, then "Black 3D" puff satin (5,359 st at 114.3 mm), 11 trims.

## Goals

1. A **3D Puff** switch on the review screen (`app/src/ui/DigitizePanel.svelte`).
   Under it, two modes (Kent's flow, 2026-11-19):
   *Puff all eligible shapes* or *Select puff shapes*, the latter a per-shape
   checkbox in the shape list.
2. Puff construction for every puffed shape, per §3: satin only,
   density-normalized columns, perpendicular end-caps at every open column
   terminus, no underlay (with §3's inset walk), 0.4 mm overlap at junctions,
   5-stitch ties.
3. Sequencing: all flat stitching first; then, per puff thread, a tack-down
   run → foam stop → puff satin. Puff blocks are operator-step blocks
   (`StitchBlock.step`) and are never merged with neighbours.
4. The foam stop reaches the customer: the service serialises step metadata,
   and the worksheet (`src/pdfsheet.js`) prints the step's action ("Stop: lay
   3 mm foam") instead of "Color N". Appliqué's orphaned steps
   (`stage6_applique.plan_steps`) ride the same wiring.
5. **OFF is byte-identical.** With the switch off a design sews exactly what
   it sews today, pinned by a test like
   `test_applique_off_is_byte_identical`.

## Non-goals (for this build)

- Puff on Studio lettering (JS engine, `src/satinfont.js`) — a later build.
- Puff on fills. §3: tatami on foam is manual-mode only, never auto output.
- Automatic puff detection. Foam is a production decision invisible in the
  pixels (`docs/stage0-tires-photo-scene-2026-09-11.md` §10).
- Refusing by garment. Washables crumble foam (§3); this build warns, it
  does not refuse.
- Time-based pricing for puff (§3 notes stitch count lies about it).

## Anti-goals

- A puff column whose ends are open. Foam leaks out; §3's design rule is a
  closed loop of penetrations around every puff region.
- A foam stop with no instruction. `assert_steps_valid` already refuses this
  for appliqué; puff steps go through it.
- Any change to output with the switch off.
- Puff shipped as default-ON or as "ready" before a sew-out (ROADMAP gates 1
  and 3).

## Constraints

- **ROADMAP gate 1.** Puff density, compensation (push 0.3–0.4 vs pull
  0.6–0.7, unresolved in documents), the 3–11 mm satin width range, and
  whether the Tajima halts on a same-needle colour change in DST are physical
  constants. Build with values measured from `TIRES HAT 3D` (a sewn pro file),
  behind the switch; the "ready" claim waits for a sew-out.
- `SATIN_MAX_WIDTH_MM` sends wide columns to tatami today; puff needs satin to
  11 mm, so puffed shapes need their own width ceiling, not the flat one.
- Per-shape settings go through the shape-layers contract
  (`digitizer_service/app.py` `_OVERRIDE_KEYS`, kept in lockstep with
  `regions.apply_shape_edits`). A new key bumps the contract version.
- Region intent carries forward across re-digitize via `Region.meta`, as
  appliqué's does (`config.py` near `applique: bool`).

## Approaches considered

- **A. Per-shape toggle only.** Correct for mixed designs; more UI.
- **B. One whole-design switch.** Simplest; can't keep a wide shape flat.
- **C. Automatic.** Rejected: foam is invisible in the artwork.
- **Chosen (Kent, 2026-11-19): A and B combined** — a master switch, then
  "puff all eligible" or "select shapes". Same stitch engine underneath.

## Decided

- Master switch + two modes, as above (Kent).
- Uploaded logos only; lettering later (Claude's call, accepted).
- Ineligible shapes (satin columns outside the puff width range, or not satin)
  show greyed with the reason in select mode and are skipped by "puff all";
  the job still digitizes and returns a warning naming them (Claude's call,
  accepted).
- Puff last, one tack-down + foam stop per puff thread (§3, accepted).
- Constants from measuring `TIRES HAT 3D` (accepted).

## Settled after the builder check (Claude's calls unless marked)

- **The stop in the machine file.** Every block boundary already exports as a
  colour change (`export.py`, `CMD_COLOR_CHANGE` → `pattern.color_change()`),
  so a puff step boundary writes a colour change on the same thread in every
  format; nothing new in the writer. Whether a Tajima halts there on the same
  needle is gate 1's open question (§3 item 6), so until a sew-out the
  worksheet is what guarantees the operator stops. Answered by the project.
- **Eligibility.** A shape is eligible when its column width along the spine
  sits inside the puff range (start from §3's 3–11 mm; replace with the
  TIRES-measured range if it differs). A shape the flat pipeline would send to
  tatami only for exceeding `SATIN_MAX_WIDTH_MM` is re-routed to satin under
  puff, since puff's own ceiling applies. Wider than the puff ceiling, or not a
  column at all → ineligible. So the puff decision is made before the
  satin/tatami split for puffed shapes.
- **If TIRES HAT 3D can't be pulled,** build on §3's values marked
  `unmeasured` in code and docs; tests pin structure (ordering, stops,
  closed ends, OFF byte-identical), not the constants. Measurement replaces
  the values when the file is in hand.
- **Multi-colour puff.** Group puff shapes by thread; each puff thread gets its
  own tack-down + foam stop, in sew order (§3: leave about 6 mm between puff
  colours, never overlap foam). Single-thread designs like TIRES get one.
- **Foam thickness.** Fixed at 3 mm in this build (§3's default), named in the
  worksheet text; a thickness option is later.
- **Tack-down.** Part of the construction, not extra output: a run around each
  puff thread's shapes sewn before the stop, holding the foam's position, as
  the pro's 279-stitch "Puff Grip" does. The inset walk replaces underlay on
  the puff satin itself, after the stop.
- **Contract.** Additive: per-shape `puff: true/false` joins `_OVERRIDE_KEYS`
  with a minor version bump; an older client that never sends it gets today's
  behaviour. `puff` and `puff_mode` are job-level config.
- **Cap-front seam (§3.9).** Placement is unknown at digitize time, so a
  worksheet note only, no rejection.
- **Preview.** The Studio draws the `Design` the service returns, so puff
  needs no JS engine change to preview; a raised look is out of scope.

## Left to the builder

- Config shape: e.g. `PipelineConfig.puff: bool` + `puff_mode`, and a
  per-shape override key (`puff: true/false`) mirroring appliqué's
  `Region.meta` pattern.
- Where the puff pass lives (a `stage6_puff.py` beside `stage6_applique.py`,
  called from `stage7_sequence.py` where `applique_pass` is).
- How end-caps are generated on the medial-axis satin, and the eligibility
  test (§3: gate on stroke width, not glyph height).
- The measurement tool for `TIRES HAT 3D` (density, cap geometry, tack-down
  path, ties) and where its numbers are recorded.
- Warning codes and their customer text in `app/src/lib/digitizer.js`, next
  to the `APPLIQUE_*` ones.
- A "Flag Before After" picture set (CLAUDE.md "A flip question comes with
  pictures") before any default changes.
