# Eight PRs: the DST axis, and a number the app asserted instead of measuring

2026-09-08. #414 through #421, all merged. The day's shape: one long-standing
physical-sounding question turned out to be a documented format detail, and the
rest of the day was one defect family — **the app stating a number it had not
measured, beside numbers it had.**

## The DST axis, both halves (#414, #415)

`src/dst.js` / `src/dstimport.js` put X in the HIGH nibble of every record byte
and Y in the LOW one; the standard is the reverse. It round-tripped correctly
with itself and was wrong everywhere else, in both directions.

**The entry said "transposed" and the Studio told customers to rotate.**
Rendered 2026-09-07, a standard reader saw the design a quarter turn round AND
mirror-imaged — letters backwards — which no rotation repairs. **A swapped
bounding box fits a turn and a mirror equally, and only a picture separates
them: when a claim is about ORIENTATION, render it.**

Fixed by swapping the two weight tables in the writer and in `decodeDelta`, so
both match `pystitch.DstWriter.encode_record` bit-for-bit — 10/10 byte-identical
across a spread of deltas, crossval DST control reads `identity` beside PES and
EXP, and a "FRITSCH" export draws upright at its own 127.2 × 22.6 mm where it
drew a vertical column of reversed letters before. `decodeDSTStandard` collapsed
into a plain alias of `decodeDST`, exactly as its own comment predicted.

**ROADMAP gate 1 should never have held this, and being on that list cost six
weeks.** The gate's own test is the sentence under it: *fabric settles these*.
Which nibble carries X is settled by a documented format with a reference
implementation sitting in `digitizer/.venv`, and five sources already agreed —
none of which own a machine. **Before adding anything to gate 1, ask which kind
it is: if every source you would consult owns no machine, the gate does not
apply.** A sew-out could not have answered this faster, or at all.

Still true: a `.dst` EMB-Bot wrote BEFORE the fix is in the old dialect, so
re-importing one reads transposed. Old files are not repaired by this.

## The recurring defect: asserted beside measured (#416, #417, #421)

Three instances, same shape, found by driving the app rather than reading it.

**The second starter design failed the app's own quality check on click**
(#416). `chest-name` was the only template pinning a size — 76.2 mm — where its
own default text sews 7.6 mm caps with **69% of the lettering under the 1 mm
column floor**. The first screen says *"One click starts a ready-made design"*
and then condemned it. Two constraints decide the replacement and **finding the
second is the point**: the lettering check alone argues for the placement's full
width (101.6, where cap height saturates), and `field-chrome.spec.js` failed
that correctly — `nudgeSelected` and pointer drags clamp against the **garment
placement box**, so a design sewing 101.8 mm has zero slack and cannot be moved
at all. 92 mm is the first width with no thin lettering AND 4.7 mm of slack.

**The review summarised a mixed design as its digitized element alone** (#417):
`2,253 stitches` shown for a **3,367-stitch** design — the commonest thing a
customer combines. The gate asked *"is there a quality report?"* when the
question is *"does it cover the design?"*. A residual where two logos gave no
total at all was fixed the same day (#418).

**The colour count came from the slider on two screens** (#421) — the best find
of the day. The review card read:

    Colors          4 · background removed
    Thread changes  1

One thread change is two colour blocks; those rows are two apart and cannot both
be right. `Thread changes` is counted from the design's own `{type:"color"}`
records; `Colors` was `element.nColors`, a CEILING the customer asked for, and
never looked at the design. **Money, not tidiness — a colour is a cone to buy
and a re-thread on a single-needle machine.** The same slider read the content
step's element chip (`Image · 4 colors` above a two-swatch strip). One shared
rule now (`flatten.js` `MIN_SWATCH_SHARE` / `sewnColorCount`), and five surfaces
agree: 2 swatches → chip 2 → Colors 2 → Thread changes 1 → 2 cone rows.

**No empty palette slot is needed for the slider and the sewn count to part
company** — median-cut returns only as many entries as the art needs (two at
every setting from 2 to 8). A first draft of the comment claimed the absorb pass
"can empty some of them"; that case could not be constructed, so the claim was
left attributed to ImagePanel's author rather than restated.

## Rules earned

- **Read a summary card as a system of equations, not a list of facts.**
  DOCTRINE already had *"when two displays of one quantity disagree, one is
  measuring the input"*. The extension: **they need not be the same quantity,
  only linked ones** — and that is the harder case, because nothing looks
  duplicated. `Colors 4` and `Thread changes 1` are not the same number, so no
  eye and no test compared them. Any two rows with an arithmetic relation are a
  free consistency check.
- **After a fix, check the whole surface, not the screen the report named.**
  The chip half of #421 surfaced only when the production bundle was re-driven
  to confirm the review-card fix.
- **A loose one-off PROBE produces false positives at a steady rate** (#420,
  five in one session) — read the tool's OWN report (`ERR` lines, exit codes,
  what a click resolved to) and re-measure against the narrowest element that
  can carry the answer, `.fieldmeta` rather than the whole page. It caught three
  wrong bug reports later the same day: "the artwork lane can't work on a phone"
  (it does — `ContentStep`'s comment says it falls back to the browser engine;
  3,011 stitches measured), a duplicate DOCTRINE rule, and a wrong explanation
  for an e2e count in my own PR body.
- **A phone-sized viewport on a machine running the service is not a phone.**
  `docs/scope/3`'s phone section measured the artwork lane at 390×844 with the
  digitizer reachable, which no real phone is (`127.0.0.1:8721` is the phone's
  own loopback). Conclusion survived — artwork works there — but by the browser
  flatten lane, 3,011 stitches, not the auto-digitizer's 2,187.

## Traps that cost time

- **`npx vitest run` from the repo root resolves a DIFFERENT vitest** (5.0.0 vs
  app's 4.1.10), globs the node:test engine files as "No test suite found"
  errors, runs a subset and **exits 0**. Mirror: `node --test` from `app/` gives
  `# tests 0 · # pass 0 · # fail 0`, also exit 0. Both read as a pass; the tell
  is a count you recognise. Now in `.claude/skills/run-emb-bot/SKILL.md`.
- **`git checkout <file>` on an UNCOMMITTED file destroys it.** Wiped a set of
  derivations mid-session; an hour later auto-mode's classifier blocked the same
  reflex. Back up to the scratchpad first — see COOKBOOK.
- **`git cherry-pick A..B` excludes A.** Use `A^..B`.
- **A stale baseline quoted from an old PR body.** Studio was 1075, not the 1074
  a previous PR body said — measured by stashing the two spec files and
  re-running. Test counts move; measure the DELTA, never quote a remembered
  total.
- **The doc-path sweep is still a measured negative** (2026-09-06, re-confirmed
  today: 651 → 363 → 19, all deliberate) — **but the hand-pass that cleared it
  is not trustworthy either.** `PRODUCT.md` row 7, the licence row gating the
  first dollar, cited `src/fonts/milli_marif_bold.LICENSE.txt` as proof research
  had been done. That file was deleted 2026-08-04 BY that research — the font
  was pulled. The hand-pass cleared it on the rule *"a path is either right or
  cited inside a sentence saying it was deleted"*, and row 7 does say "pulled
  from the build" — one sentence later. Ruling stands (don't build the checker),
  with a second half: don't trust the hand-pass either.

## Verified negatives, so they are not re-derived

Worksheet complete on a mixed design; simulator counter correct at 0 and max;
`.embproj` v1→v2 migration; `hoopFit`'s zero-margin rule (a hoop's stated size
IS its embroidery field); undo/redo across a structural add; custom fabric
colour at both extremes; every visible control has an accessible name; drawing
tools functional; the font-licence chain end to end (85 fonts / 85 sidecars / 85
binaries, credits dialog renders 85 rows, a sidecar link serves 200 text/plain).

Chain verified end to end on a mixed design: canvas caption, review recap, PDF
worksheet and the downloaded DST read by `pystitch` all give **3,367 stitches /
2 colour changes / 26 trims / 92.2 × 22.9 mm**.

## Read before

Proposing a physical-constant gate, quoting a test total from a PR body, running
the Studio suite from anywhere but `app/`, or reporting a defect from a single
one-off probe.
