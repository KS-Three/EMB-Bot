# EMB Bot — Product

Snapshot of current product scope and launch decisions — not a changelog.
README.md is user-facing; COOKBOOK.md is the technical handoff; this one
records *what we're building, for whom, and what's explicitly out of scope*.
Update it when a scope or launch decision changes, not on a schedule.

## What this is

Started as Kent's own embroidery-digitizing tool — Ink/Stitch felt confusing
and he didn't want a subscription. Target machine/format is Tajima/DST
(byte-verified export, low file-format risk).

Scope expanded on 2026-07-29 to a market-parity launch, benchmarked
explicitly against **Ember** (emberdesign.net) — Wilcom and Hatch are
explicitly *not* the bar.

Since that pivot, most engineering effort has gone into a professional-grade
Python auto-digitizing engine (photo/logo → stitch file), which was
originally tabled and then un-tabled the same day the launch scope below was
set.

**Ruled 2026-08-11 (Kent): engine quality is a parallel investment, not a
launch gate.** The launch checklist below is the launch bar; engine quality
keeps improving alongside it but does not block shipping.

## Launch scope checklist

Status verified against the repo on 2026-08-11, and **every row re-verified
2026-09-08** (not just taken from memory). What moved since 2026-08-11: row 1
became genuinely reachable (#403 gave JEF a button — the row had been verified
against the module that can write JEF, not the product that exposes it), and
row 7's sidecar count grew from 55 to 85 while staying one-per-font. Rows 2, 4,
5 and 6 re-checked in place; row 3 is still ❌ with no trace in the repo.

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | PES hardened to byte-verified + JEF export | ✅ Done — JEF only became REACHABLE 2026-09-07 | PES/JEF live in `digitizer/digitizer_service/formats.py` (pyembroidery-backed; `digitizer_core/export.py` itself is DST-only); PES/JEF round-trip verified. **This row was verified against the module that can write JEF, not against the product that exposes it** — the Studio's Download step offered DST/PES/EXP only, so from 2026-08-11 to 2026-09-07 a Janome owner could not export anything, while this line said the item was done. The button now exists (`DownloadStep.svelte`, disabled with a reason when the service is down — there is no browser JEF encoder), and the bytes it produces were decoded with `pystitch` rather than inferred: 80.5×16.6 mm, 1 colour change, 2 threads, matching the design the app promised. |
| 2 | Home-machine hoop picker (4×4 / 5×7 / 6×10 / 8×8 presets) | ✅ Done | `src/garments.js` `HOOPS`/`suggestHoop`/`hoopFit` (orientation-aware ceiling check, replaces the generic 200×200mm one); Studio picker on the Garment step with per-garment suggestion + manual override, persisted as `project.hoopId` (`.embproj`-safe); chosen hoop on the review stats line, Review summary, and PDF worksheet. Auto-rotating an only-fits-rotated design is a noted follow-up (the warning names the rotate fix) |
| 3 | Curated starter design pack (12–24 licensed designs via DST import) | ❌ Not started | no trace in repo |
| 4 | Basic shapes tool (circle / rect / heart / star) | ✅ Done | `app/src/lib/shapePresets.js` generators + `ShapePanel.svelte`, new `"shape"` element type riding the manual-draw lane (`shapesToRegions → buildQualityDesign`); all four kinds verified digitizing live 2026-08-11 (star-tip coverage pinned in vitest); recipe (`kind`+`params`) persists in `.embproj` |
| 5 | Thread palette sweep (remaining Ink/Stitch `.gpl` brands) | ✅ Done | 68 brand charts in `tools/palettes/`, matching the policy-filtered count (brands from companies that sell embroidery machines/software are excluded on purpose) |
| 6 | `.embproj` project file save/load | ✅ Done | `app/src/lib/projectFile.js` |
| 7 | Font-license compliance (hard gate before first dollar) | ✅ Done (shipping posture) | Per-font research was done on every flagged case, and **every one of them was pulled** — `milli_marif_bold`, `tt_directors`, `tt_masters`, `dejavufont` by name, each with its reasoning, in the `PULLED` set in `tools/build-embf.mjs` (enforced in the build, not a note), plus all 13 ShareAlike fonts on Kent's 2026-08-04 call. **`milli_marif_bold` is the case to read:** it *had* an adapter's permission email and full OFL-1.1 text, and that was still not enough — nothing on file confirmed the grant covered commercial embroidery distribution, so it went. (Until 2026-09-08 this row cited that font's `src/fonts/milli_marif_bold.LICENSE.txt` as the evidence that research had been done. The research is what deleted that file, on 2026-08-04 — so the row gating the first dollar was offering a pulled font's removed sidecar as proof of compliance.) The "zero sidecars ship" gap is closed, and is now closed BY CONSTRUCTION rather than by a count: **85 fonts ship in `app/public/fonts/bin/` and 85 `.LICENSE.txt` sidecars ship beside them** (re-counted 2026-09-08; it was 55 when this row was written, so the invariant has held across a 30-font expansion). It is not a manual count any more — `test/font-license.test.js` asserts that *every shipped font's sidecar still resolves to its manifest `licenseId`*, and pins the two mislabels this project has actually hit (an NC/ND variant resolving to a permissive id, and the ALLOWED set widening silently); `test/embf-guard.test.js` guards the binary library. Both run in the `engine` CI job, which is required on `main`, so a font added without a sidecar or with a non-allowed licence fails the build rather than shipping. All license-flagged fonts were pulled from the build in the 2026-08-04 audit pass rather than kept; the remaining legal question only gates *restoring* pulled fonts (see "Known compliance risk"). |

## Launch posture (decided)

- Desktop-only, stated on the site.
- **SAM2 photo segmentation ships post-v1** (ruled 2026-08-11): v1 launches
  without it; it returns as an opt-in "enhanced photo mode" download
  (~1 GB) after launch, gated on re-measuring `points_per_side=12` on a
  real photo and resolving the white-subject background hypothesis. The
  localStorage dev seam stays for internal use. Server-side segmentation
  rejected — breaks the local-first, no-account promise. Full analysis:
  `docs/sam2-ship-path-brief-2026-08-11.md`.
- ~70 fonts is enough — launch does not wait on font expansion.
- Fast-follow order after launch: ~~`ltr/` importer (mai_en_fleur)~~ **done** (mai_en_fleur ships in the 55-font manifest) → tablet audit → cloud sync (post-revenue).
- **The border decision lives on the canvas too (Kent's call 2026-09-09):**
  right-click a recognised shape on the field for Add border / Remove border
  (and Use design setting once a shape has its own). It writes the same
  per-shape override the Digitize panel's Border select does, so the panel
  stays the place for the finer choice (bean vs auto). A shape sewn as satin
  gets no border from either — the engine's rule, stated on the item.

## Explicit non-goals (parking list — not the Ember bar)

Team names, monogram frames, appliqué, envelopes beyond arc, 3D puff,
stitch-level editing, decorative fills, imported-design re-density
(Wilcom-style stitch processor), a sharing gallery. No user-upload gallery
is a deliberate choice for the starter design pack (item 3) too —
copyright/moderation exposure declined.

"Full freehand draw tools" used to sit on this list, but manual draw mode
has since shipped (`app/src/lib/manualShapes.js` — the Studio's third
content type: hand-drawn outlines with curved edges and point editing), so
it is no longer a non-goal. (The separate item 4 preset shapes tool also
shipped — verified live 2026-08-11; see the checklist above.)

## Open — not yet decided

- **Backend / billing.** Leaning toward Stripe payments + an entitlement
  check, with projects staying local (no server-side project storage) — but
  this was tabled, not committed. Pricing tiers and font-gating are tabled
  with it. Needs its own decision session before it can block launch.

## Known compliance risk

- **Zero CC-BY-SA fonts ship.** All 13 ShareAlike fonts were pulled from
  the build on 2026-08-04 (Kent's call), which made the paid launch
  independent of the CC-BY-SA legal question. Whether the `.embf` binary
  font format counts as a "derived work" under CC-BY-SA remains an open
  legal question flagged for a lawyer — but it now only gates *restoring*
  those 13 pulled fonts, not launching.
