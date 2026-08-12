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
set. That work's relationship to the launch checklist isn't restated
anywhere — worth Kent confirming whether digitizer-engine quality is itself
a launch gate, or a parallel, longer-term investment.

## Launch scope checklist

Status verified against the repo on 2026-08-11 (not just taken from memory).

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | PES hardened to byte-verified + JEF export | ✅ Done | PES/JEF live in `digitizer/digitizer_service/formats.py` (pyembroidery-backed; `digitizer_core/export.py` itself is DST-only); PES/JEF round-trip verified |
| 2 | Home-machine hoop picker (4×4 / 5×7 / 6×10 / 8×8 presets) | ❌ Not started | `src/garments.js` has garment-*type* presets (hat front, left chest, full back, ...) plus one generic 200×200mm ceiling — no selectable hoop-size picker exists |
| 3 | Curated starter design pack (12–24 licensed designs via DST import) | ❌ Not started | no trace in repo |
| 4 | Basic shapes tool (circle / rect / heart / star) | ❌ Not started | no preset-shapes trace in repo — explicitly *not* full freehand draw (which has since shipped as manual draw mode; see the parking-list note below) |
| 5 | Thread palette sweep (remaining Ink/Stitch `.gpl` brands) | ✅ Done | 68 brand charts in `tools/palettes/`, matching the policy-filtered count (brands from companies that sell embroidery machines/software are excluded on purpose) |
| 6 | `.embproj` project file save/load | ✅ Done | `app/src/lib/projectFile.js` |
| 7 | Font-license compliance (hard gate before first dollar) | ✅ Done (shipping posture) | Per-font research done for flagged cases (e.g. `milli_marif_bold` — full permission-email trail + OFL text on file in `src/fonts/milli_marif_bold.LICENSE.txt`). The "zero sidecars ship" gap is closed: 55 `.LICENSE.txt` sidecars ship in `app/public/fonts/` (one per shipping font, counted 2026-08-11). All license-flagged fonts were pulled from the build in the 2026-08-04 audit pass rather than kept; the remaining legal question only gates *restoring* pulled fonts (see "Known compliance risk"). |

## Launch posture (decided)

- Desktop-only, stated on the site.
- ~70 fonts is enough — launch does not wait on font expansion.
- Fast-follow order after launch: ~~`ltr/` importer (mai_en_fleur)~~ **done** (mai_en_fleur ships in the 55-font manifest) → tablet audit → cloud sync (post-revenue).

## Explicit non-goals (parking list — not the Ember bar)

Team names, monogram frames, appliqué, envelopes beyond arc, 3D puff,
stitch-level editing, decorative fills, imported-design re-density
(Wilcom-style stitch processor), a sharing gallery. No user-upload gallery
is a deliberate choice for the starter design pack (item 3) too —
copyright/moderation exposure declined.

"Full freehand draw tools" used to sit on this list, but manual draw mode
has since shipped (`app/src/lib/manualShapes.js` — the Studio's third
content type: hand-drawn outlines with curved edges and point editing), so
it is no longer a non-goal. Item 4's basic *preset* shapes tool
(circle/rect/heart/star) is still separate and still not started.

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
