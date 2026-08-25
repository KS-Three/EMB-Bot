# The Studio's display layer, and what a green suite cannot see (2026-08-25)

Kent: "Are you able to work side by side with the embot if i have another code
session running? I NEED YOU TO HELP WITH THE DISPLAY / UI.... IT NEEDS ALOT OF
WORK!!!!" — a cloud session on `claude/display-ui-improvements-iyc20h`, running
beside his own local one. Four passes, merged as PRs #239, #240, #242, #244.

**Numbers and PR-by-PR detail: `docs/scope-history.md`, 2026-08-25 entry.
Standing consequences: `docs/scope/3-studio-app-wizard.md`.** What follows is
what a future session should carry into the work, not the record of it.

## The headline finding

**787 passing specs said nothing about whether the app was usable.** Every
defect below was live on `main` and none of them failed a test:

- The wizard's `Next` button rendered **white on white on every step** — a
  cascade collision where a neutral `background` matched `button.primary` at
  equal specificity and won on source order ~490 lines later, while the white
  `color` came from `button.primary` and was never overridden.
- The field's right-click tool menu **created elements you could not see**. It
  is on every step; element editors are only in the Content step's panel. From
  the Garment step it appended and persisted a real element with no visible
  change anywhere, accumulating orphans.
- The digitize panel was an **8.8-screen scroll held open by a column of
  icons** — seven stacked action buttons made their container 138px tall and,
  as the tallest child, it set every layer row's height. Roughly 97px of every
  151px row was empty space.
- The embroidery field canvas was a **hardcoded 760×560 bitmap in a 980×836
  pane** that never grew, and three pieces of chrome were painted on top of the
  sewable field inside the hoop guide.

The method that found all of it was the same: drive the running app in a real
browser at several widths and **measure** — read computed styles and bounding
boxes, not the stylesheet. A cascade bug is invisible in the rule you are
reading. Screenshot every step; a defect like the invisible CTA is obvious in a
picture and undetectable in the source.

## Two traps worth more than the fixes

**A regression test proves nothing until you have watched it go red.** The
first spec written to pin the simulator regression *passed with the bug
deliberately re-introduced* — worthless. The repro was narrower than assumed:
`.simbar` merely being in flow does not reproduce it, because side by side the
control row's height is unchanged. Only *stacking* the bars does. Always run a
new regression spec against the real broken state.

**`var(--x, fallback)` with an undefined name is not a fallback — it is a
silent bespoke value.** `--warn-text` (×20), `--warn-bg` (×3) and `--fs-s` (×1)
were consumed by code and defined nowhere, so the app shipped two different
warning colours, one bypassing the token system entirely. Defining the names
fixed all 24 call sites without touching one of them. Audit with: collect
`var(--…,` names across the components, subtract the ones declared in
`theme.css`'s `:root`, and look at what is left.

**Contrast must be measured against the ground a string actually sits on.**
`--muted` and `--warn` both passed on white and both failed WCAG AA on
`--field-bg` and `--tint` — which is where much of the app's secondary text
lives. Walk up for the first non-transparent ancestor rather than trusting the
rule's own `background`.

## The live coupling to know about

`paint()` opens with `stopSim()`, and `stopSim()` reads `simActive`, so the
paint effect's dependency set reaches the simulator flag. **Any layout change
that resizes the field canvas while the simulator is starting will re-enter
`paint()` after `startSim()` set the flag and switch the simulator off in the
same tick.** That is exactly what happened when the control bars briefly
stacked: opening the simulator shrank `.hoop`, fired the ResizeObserver, and
the simulator became impossible to open at all. `.fieldbars` exists to keep the
control row's height independent of `simActive`; `app/e2e/field-chrome.spec.js`
fails if a future change lets them stack again.

Observed and deliberately not fixed: that same effect re-runs on a simulator
toggle with `project`, `runtime` and `canvas` all unchanged, regenerating the
whole design for nothing. Harmless today because it fires before `simActive` is
set. It is render scheduling rather than display, so it was left rather than
folded into a UI pass — and flagged to Kent as his call.

## What the design-system audit did NOT find

Worth recording so nobody re-runs it: the **spacing scale is respected** (the
bespoke px in `theme.css` are borders, icon boxes and grid gutters), **elevation
is consistent** across two tokens plus one deliberately directional drawer
shadow, and the **card/tile treatments already agree**. Only `.fs-trigger` was
out of step. The system was in better shape than "a real visual design pass"
implies; the real defects were contrast, line height and off-scale sizes.

## Process, for whoever works beside Kent next

**He merges within about a minute of a PR opening, usually before CI finishes**
— three of the four went in while `studio-e2e` and `digitizer` were still
running. Twice that stranded later commits on a branch whose PR had already
merged, each needing a rebase onto the new main and a **fresh** PR (a merged PR
cannot track new work). If you are pushing in stages, expect the branch to be
merged out from under you; check `git log origin/main..HEAD` before assuming
your last push is in the PR you think it is. Every merge run on main did come
back green.

He also answered "do the visual design pass" **without** giving a direction,
after being told plainly that a direction was needed. The pass was anchored on
measurable violations of the app's own declared token system instead of on
taste, and the three genuinely subjective items (irregular scale ratios, `h3`
at body size, untokenised weights) were left and tracked as MASTER_SCOPE
"Waiting on Kent" item 10. That split — do the measurable half, escalate the
taste half — is the shape to reuse.

**Building the digitizer venv takes two installs.** CLAUDE.md correctly sends
you to `pip install -e .` rather than `requirements.txt` (only the former
enforces the 3.12 floor), but the web stack is an optional extra: that command
alone yields a venv that imports `digitizer_core` and dies on
`ModuleNotFoundError: No module named 'fastapi'`. Use
`pip install -e ".[service]"`. Now also in COOKBOOK's "Run the service".
