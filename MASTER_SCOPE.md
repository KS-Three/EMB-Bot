# EMB-Bot — Master Scope

**What this is:** a live status dashboard, not a requirements doc. It exists so
Kent and any Claude session can answer "where do we actually stand?" without
re-deriving it from a dozen spec/plan docs each time. It tracks five product
capability areas on two independent axes — **Status** (is it built) and
**Confidence** (do we trust it) — plus cross-cutting issues that don't respect
area boundaries.

**How it's kept current:** updated proactively after PR-sized work lands, and
on demand via the `/update-master-scope` skill. See "How this document works"
at the bottom for the authority model behind the confidence ratings.

**Last updated:** 2026-08-04 (font-license audit items 4–10 + 12 executed —
full license texts on disk/served/embedded, complete attributions, credits
links; the lawyer consult (item 11) is now the only open compliance gate.
Prior update 2026-08-03: the gradient angle-fragmentation fix landed
that session; `BACKGROUND_ENCLOSED`'s root cause was corrected to
`stage1_prep.py`, still unresolved).

---

## At a glance

| Area | Status | Confidence |
|---|---|---|
| 1. Auto-digitizing quality (image → stitches) | In progress | **Low** beyond flat spot-color art |
| 2. Font library & lettering | Implemented (library + license remediation) | High (tech) / Medium (compliance — one lawyer consult still open, blocking first dollar) |
| 3. Studio app / guided wizard | Implemented | Medium (fabric-preset accuracy: pending sew-out) |
| 4. Export formats | Implemented | Varies by format — see below |
| 5. Stitch-out review & manual editing tools | Implemented (narrow scope) | High |

---

## Cross-cutting issues

Things that don't respect one capability area's boundary. Referenced from the
area they drag down, documented once here.

### DST codec axis bug

EMB-Bot's own browser DST codec (`src/dst.js` / `src/dstimport.js`) is
transposed vs. the Tajima/pyembroidery standard — confirmed, unresolved.
It round-trips correctly against itself but reads a quarter-turn wrong in
third-party software. Full evidence trail: `dst-codec-axis-discrepancy` in
memory, `docs/dst-axis-verdict-2026-07-31.md`, `digitizer/README.md`'s "Open
finding" section.

**A nuance worth flagging, not a fix:** CLAUDE.md says "treat browser DST as
EMB-Bot-internal only," while `digitizer/README.md`/`digitizer_service/formats.py`
say browser DST stays the Studio's *default* encoder "because it is the one
with sewn evidence behind it." These aren't necessarily contradictory — the
first is about trusting browser DST as correct-orientation for arbitrary
third-party software; the second is about which of EMB-Bot's own two encoders
Studio picks internally — but they read differently enough side-by-side that
it's worth Kent confirming the intended reading rather than assuming.

**Resolution path:** a sew-out or third-party read of a browser-encoded DST
(the "third opinion" `digitizer/README.md` calls for). Fixing the codec itself
is explicitly Kent's call — every existing EMB-Bot DST is affected by any fix.

### Font license compliance gap — REMEDIATED 2026-08-04 except the lawyer consult

`docs/font-license-audit-2026-07-31.md` action checklist: **items 1–3 done**
(the 4 flagged fonts pulled, 72 → 68 — see the audit's §7) and **items 4–10 +
12 done** the same day (see its §8): every one of the 68 fonts now has its
full upstream license text on disk (`src/fonts/<key>.LICENSE.txt`), shipped
by `copy-engine.mjs` at `/fonts/<key>.LICENSE.txt`, linked per-font in the
credits dialog, AND embedded verbatim in the `.embf` binary metadata (closes
the bare-download hole); manifest attributions are complete notices
(adapter + upstream copyright + Reserved-Font-Name declarations, emails
stripped); guard tests pin all of it. No Reserved Font Name surfaces as a
primary name anywhere.

**Still open — the one remaining launch gate:** audit item 11, the one-hour
lawyer consult on the CC-BY-SA ShareAlike question (does BY-SA attach to the
14 CC-BY-SA-derived `.embf` binaries and customers' stitch files?). The
ready-to-send brief is `docs/lawyer-brief-cc-by-sa-2026-08-04.md`; booking it
is Kent's real-world action, before first dollar. Worst case per the audit:
relabel 14 binaries + customer note, or pull 14 fonts. Also parked for Kent:
the `satin-fonts.js` legacy-registry residual (audit §7) if `EMB-Bot.html` is
ever distributed, and the bluenesia permission screenshots (audit §8).

### No physical sew-out testing has occurred yet

Zero sew-out testing has been done anywhere in this project — confirmed
independently across three separate research passes (auto-digitizing, Studio
fabric presets, export formats). `docs/hardening-closeout-2026-08-02.md`
states it plainly: "Nothing was sewn. Every number above... is geometry."
This is the single biggest confidence ceiling in the project: fabric-preset
accuracy, real stitch quality beyond test-suite geometry checks, and the DST
axis question all wait on this. Four hoopings are already specified in
`docs/hardening-closeout-2026-08-02.md` and would resolve nine currently-open
geometric questions at once — the highest-leverage next action across the
whole project, whenever Kent's ready to schedule it (his explicit call, not
something to push for).

---

## Capability areas

### 1. Auto-digitizing quality (image → stitches)

Covers both implementations that turn an image into stitches: the original
browser JS engine (`src/flatten.js`, `digitize.js`, `geometry.js`, `fill.js`,
`satin.js`) and the Python pipeline (`digitizer/digitizer_core/`) — tracked as
one capability regardless of which implementation is responsible, since
that's how feedback on digitizing quality actually needs to land.

**Status:** In progress. The JS engine is complete but frozen — COOKBOOK.md
notes it was retired in favor of "feed it clean flat art," not because it's
broken. The Python pipeline is the active target: `digitizer/README.md`
states "build steps 1, 3, 4 and 8 of 11" — SAM2 segmentation deferred,
stitch processor / preflight scoring / review-UI polish still to come.

**Confidence: Low** beyond flat spot-color art. Flat-logo digitizing (both
implementations) is Medium — 265/265 JS tests and 402/402 Python tests pass,
and the geometry is internally consistent. `hardening-closeout-2026-08-02.md`
independently re-measured the five newest Python features and found
defects the shipped test suites couldn't see in all five; one of those five
is now fixed (see below), four remain open:

- **Chaining (needle-down travel between shapes) — FIXED 2026-08-03.** Was:
  sews needle-down thread on bare fabric on a stock preset, up to 16.15mm
  exposed, invisible to the shipped test suite because it measured polygon
  cover instead of actual thread position. `_link_cover`
  (`digitizer_core/stage7_sequence.py`) now builds the "already laid" half
  of its cover from the block's own emitted stitch centrelines (buffered to
  real thread width) instead of each shape's sewing polygon. Measured on the
  committed `logo_alpha` fixture: chaining's extra links (10→14) now add
  **zero** bare-fabric exposure — exposed-run count and worst clearance both
  land exactly on the chain-off baseline — while still cutting trims (13→9)
  and stitch count (3012→2992); confirmed independently via the rebuilt
  `tools/chain_probe.py` (which had its own pre-existing bug making its
  before/after comparison a no-op — also fixed). `chain_links` **stays off
  by default**: the fix closes one of the three preconditions
  `PipelineConfig.chain_links`'s docstring names for reopening it — still
  open are an inset on `covered_by` (a later colour's sewing polygon,
  standing in for thread that hasn't been planned yet — the same class of
  approximation, just not yet fixable the same way) and a physical sew-out
  to validate `LINK_COVER_TOL_MM`, which is still a thread spec, not a
  measurement. The other four closeout defects below are unaffected by this
  fix and remain open.
- **Gradient blend tier** — shipped (`stage6_blend.py`), then within one day
  found to fragment into 23 independent-angle regions instead of one shared
  ramp, plus a separate `BACKGROUND_ENCLOSED` defect that silently drops
  enclosed white icon linework as holes
  (`docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`).
  **The angle-fragmentation half is FIXED, same-day follow-up session.**
  Root cause turned out narrower than first diagnosed: all 23 k-means
  fragments were falling to `blend_fill`'s ordinary-tatami fallback (already
  near-uniform post-quantize color, so per-fragment ramp detection almost
  never fires), and that fallback hardcoded `angle_deg=None` — 23
  independent `principal_angle_deg` calls on small, irregular silhouettes,
  the actual "patchwork of differently angled wedges." Fix: one shared
  `design_row_angle_deg` computed per-design (`stage6_blend.
  detect_design_ramp_angle`, fitting L/a/b independently and taking
  whichever channel actually carries the ramp — plain lightness fit misses
  the repro fixture entirely, r2 0.003, because it's a hue rotation not a
  lightness slope; b* carries it at r2 0.45), threaded into both the
  fallback and the true-ramp branch. Verified against the repro fixture end
  to end: every fragment's fill rows now land within 0.55° of each other,
  vs. up to 64° apart before. Fragment COUNT (still 23) and radial-ramp
  angle sharing remain explicit, documented non-goals of this fix. Full
  writeup: the plan doc's "Defect 1 update" section.

  **`BACKGROUND_ENCLOSED` (enclosed-white-icon drop) remains unresolved.**
  Root cause: `stage1_prep.py::prep` (the no-alpha color-heuristic branch),
  not `stage3_segment.py` as first suspected — enclosed pixels are folded
  into `bg`/excluded from `fg` before stage 3 or vectorization ever run, so
  they never become a `Region` with a `shape_id`. The warning's own "toggle
  it back on in review" claim is currently **false**: there is no shape for
  a review-screen edit to reference. **A full design pass landed
  2026-08-04**
  (`docs/superpowers/plans/2026-08-04-enclosed-background-restore-design.md`):
  enclosed pixels join `fg` instead of `bg`, get tagged
  `meta["enclosed_background"]` post-vectorization, a new `stitched`
  shape-override key (same shape as `border`/`tier`) restores one,
  excluded from stitching at `plan_stitches` only — never from
  `PipelineResult.regions`, so Studio's existing Layers-panel delete/
  restore UI has something real to render. Still not built — bigger than a
  DT-first M0/M1 slice, spans pipeline internals, the service contract, and
  Studio UI. Open questions (overlap-threshold tuning, stage-5 interaction)
  are flagged in the design doc for whoever builds it.
- **Contour fill** — explicitly marked not-ready (commit `eac414e`): a
  0.640mm bare core in the primary fixture (7× worse than tatami's
  0.090mm), a starved-fill gate miscalibrated in both directions, and
  ring-to-ring transition chords that land stitches outside the polygon.
  Ships off by default.
- **Satin/fill classifier** — the shipped rule misclassifies compact/noisy
  shapes (a serrated 20mm disc computes as "5.03mm" and gets satin-stitched
  instead of filled). The proposed DT-based replacement (`VP90`) was
  measured and **rejected 2026-08-02** at `SATIN_MAX_WIDTH_MM = 3.0`
  (`main`'s cap at the time) — it scored worse than the shipped rule there,
  and its "pure tightening, cannot get worse" safety claim was proven
  logically inverted (it can only convert true positives into false
  negatives, never the reverse, and FN is the expensive error). **Verdict
  status: STALE, not confirmed or reversed.** An unrelated, later,
  corpus-driven change moved the shipped cap to 5.0 (already on `main`);
  re-running the SAME instrument at the new cap flips the result (`VP90`
  0/21 wrong vs. the shipped rule's 6/21) — but that's the same class of
  small-synthetic-set evidence 2026-08-02's audit already showed can't be
  trusted alone. Needs the 37-file `scratch_corpus/` run at today's cap
  before this verdict can be re-decided either way — see
  `docs/superpowers/plans/2026-08-04-m0-shape-lens-measurement.md`
  ("M0" of the DT-first migration).
- **Fill row spacing (law 19)** — unresolved two-population finding: the
  0.20mm figure is a satin-rail artifact for one file population (refuted)
  but looks like a genuine denser pitch on 43 commissioned cap logos (still
  alive). Shipped `FILL_ROW_MM=0.40` unchanged pending sew-out.

Every claim about visual/sew quality beyond internal geometry checks is
**pending sew-out** — see the cross-cutting item above.

**Next step:** the chaining fix and the gradient angle-fragmentation fix are
both landed. M0 of the DT-first migration is measured (see the satin/fill
classifier item above) — corpus leg pending a local run, M1 (`ShapeField`
hoist, byte-identical) not started. The enclosed-white-icon drop
(`BACKGROUND_ENCLOSED`) has a full design pass as of 2026-08-04
(`docs/superpowers/plans/2026-08-04-enclosed-background-restore-design.md`)
— ready to build, not started; the Python-side slice (stage 1 + tagging +
tests, no service/Studio change yet) is buildable on its own per the design
doc's sizing note. Then schedule the first sew-out session.

---

### 2. Font library & lettering

The 69-font pre-digitized satin library, browser UI, EMBF binary format, the
add-font QC/tier pipeline, and Text mode. Expandable — but every addition is
gated by the license rule below (Kent: don't risk copyright infringement if
this ever sells).

**Status:** Implemented (library/UI/format itself) — license remediation
**done 2026-08-04** (audit items 1–10 + 12; see the cross-cutting item
above), with the lawyer consult (item 11) as the one remaining compliance
gate.

**Confidence:**
- Library/tech: **High.** `src/fontbin.js` (EMBF codec), `manifest.json` +
  55 `.embf` files (72 → 68 after the audit pulls → 55 after the 2026-08-04
  ShareAlike removal), lazy loading,
  `FontBrowser.svelte`/credits UI, and the QC/tier pipeline
  (`tools/qc-font.mjs`, `tools/build-embf.mjs`, `tools/font-license.mjs`,
  `tools/patch-embf-licenses.mjs`) all exist and pass the engine suite.
- License compliance: **High — the open legal question was resolved by
  removal (Kent's call, 2026-08-04).** All 13 ShareAlike fonts pulled
  (audit §9); the remaining 55 are 52 OFL-1.1 + 1 CC-BY-4.0 + 2 CC0, zero
  ShareAlike. Full license texts ship three ways (sidecar file, served
  `/fonts/<key>.LICENSE.txt`, embedded in each binary), attributions are
  complete notices, guard tests pin it. The item-11 lawyer consult is now
  OPTIONAL — kept as the restore path for the 13
  (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`), no longer launch-gating.

**Open issues:** the item-11 consult (above); the `satin-fonts.js` legacy
residual (audit §7). On the tech side: the font-editing round deferred
condensed/expanded width and mixed per-letter size (both risk uneven satin
distortion) — minor, not blocking.

**Next step:** Kent books the lawyer consult (send
`docs/lawyer-brief-cc-by-sa-2026-08-04.md` as-is); font-library expansion is
unblocked otherwise, with the add-font skill's compliance note now backed by
guard tests.

---

### 3. Studio app / guided wizard

The Svelte guided flow (garment → content → review → download), saved
projects, the Layers panel entry point — plus fabric & garment presets
(`src/fabrics.js`, `src/garments.js`), folded in here since they're wizard
inputs, not a separate product surface.

**Status:** Implemented. 8 studio slices built and merged, plus two later
feature commits (the auto-digitize review flow, the Layers panel). README
calls it "the primary product."

**Confidence: Medium** for wizard navigability/UI quality. 321/321 Studio
(vitest) tests pass, and nearly every `app/src/lib/*.js` logic module has a
paired spec — but that coverage is **logic-only**, not UI-behavior; no
component/interaction tests exist for the actual step screens. One
documented, unfixed UI bug: rotation doesn't re-trigger hoop auto-fit, so a
design that auto-fit before a non-180° rotation can visually overflow the
hoop.

**Fabric-preset accuracy: pending sew-out** — kept as an explicit separate
note, not blended into the wizard's own score. README says it outright:
"Presets are starting points — stitch a test on your machine and tell me if
a fabric needs tuning." No physical validation has happened yet.

**Next step:** a thin Playwright smoke test covering the full
garment→content→review→download path end-to-end (the new `playwright` MCP
server makes this practical now) — would move navigability confidence from
Medium to High and catch regressions like the rotation/hoop-fit bug class
before they ship.

---

### 4. Export formats

DST, EXP, PES, SVG, and the PDF worksheet — both the browser JS encoders and
the Python digitizer service's `/export` route (pyembroidery-based).

**Status:** Implemented, all five formats, both paths.

**Confidence — varies by format, not one score:**
- **DST:** split by path. Browser DST is Medium as Studio's sewn-and-shipping
  default; Low if treated as verified-correct-orientation in the abstract —
  see the cross-cutting DST item, this is the same bug. Python `/export` DST
  (pyembroidery, standard-conformant) is Medium-High by spec, not yet
  sew-verified itself.
- **EXP: Medium.** README: "Solid, standard support, incl. trim control."
  4 targeted tests, no known open issues.
- **PES: Medium-Low**, matching README's own "best-effort — reverse-
  engineered" framing. Thinnest coverage of the stitch formats (3 tests).
- **SVG: Medium** — lower stakes (vector proof, not a stitch file), but thin
  coverage (1 test).
- **PDF worksheet: Low-Medium** — no dedicated test file exists at all;
  functionality is asserted by README description only.

**Open issues:** DST axis bug (cross-cutting, see above); PES has had no
hardening evidence found since README's best-effort caveat was written; PDF
worksheet has zero automated test coverage.

**Next step:** same as the DST cross-cutting item — a third-party sew-out/
read settles the axis question, which is the one thing actually blocking a
clean DST confidence rating. Separately, a PDF worksheet test would close
the one format with literally no automated coverage.

---

### 5. Stitch-out review & manual editing tools

The professional-quality refinement toolkit: can a user take auto-digitized
output and manually fix/improve it — delete, recolor, re-tier, adjust angle,
reorder layers — distinct from whether auto-digitizing itself is good
(area 1) or whether the wizard is easy to navigate (area 3).

**Status:** Implemented, narrow scope. Landed 2026-08-02 in two same-day
commits: the review-screen shape-edit plumbing (`c390e9f`) and the Studio
Layers panel UI (`ce8f021`).

**Confidence: High** — unusually, both the wire-protocol plumbing *and* the
user-facing UI are confirmed with matching evidence (not "backend exists, no
UI" or vice versa). The service round-trips `deleted_shape_ids` and
per-shape `shape_overrides` (recolor, tier, fill angle, border, sew layer);
`DigitizePanel.svelte`'s Layers list exposes recolor, tier, fill-angle,
reorder, delete/restore. The landing commit reports live-browser
measurements against the real service confirming all of the above plus
undo/redo and offline-queued edits.

**Open issues (self-flagged in the landing commit, not undocumented gaps):**
- No true shape-recognition re-editing — no reshaping/redrawing outlines,
  no splitting/merging shapes, no manual point editing.
- Per-shape border override is engine-supported but has no UI control.
- Backstitch/underlay adjustment is entirely engine-internal, not exposed
  to the user at all.
- Within-layer sew order is shown, not controllable — it's the machine's
  nearest-neighbor pathing.
- The "stale/unmatched edit" recovery flow was never driven in a live
  browser.

**Next step:** browser-drive the untested stale-edit-recovery flow, and
decide whether per-shape border override deserves a Layers-panel control —
both explicitly flagged as gaps in the landing commit itself.

---

## How this document works

- **Two independent axes per area:** Status (is it built) and Confidence (do
  we trust it) — kept separate on purpose. Something can be fully
  Implemented and still Low confidence (the DST codec is the standing
  example), or In progress and High confidence (on track, just not done).
- **Confidence authority is hybrid.** Claude proposes a score with cited
  evidence (tests, docs, known defects); Kent has override authority.
  Anything whose real confidence depends on physical machine verification —
  fabric presets, real stitch quality, the DST orientation question — gets
  an explicit **pending sew-out** flag instead of a guessed score, because
  no sew-out testing has happened on this project yet.
- **This document is the source of truth for current status.**
  COOKBOOK.md's former "Known limitations" section pointed here instead of
  maintaining a parallel list, to avoid the two drifting out of sync.
- **Updates:** proactively after PR-sized work changes an area's status or
  confidence, plus on demand via `/update-master-scope` for a checkpoint
  whenever Kent wants a fresh read.
