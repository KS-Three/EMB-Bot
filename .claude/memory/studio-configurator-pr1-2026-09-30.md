---
name: studio-configurator-pr1-2026-09-30
description: The Studio redesign Kent asked for (Tesla-style configurator) — PRs 1, 2 and 4 built 2026-09-30/10-01, PR 3 (hide the power tools) NOT planned; what he picked, what only driving/measuring found, and what is still open
metadata:
  type: project
---

Kent's brief 2026-09-30: "modern and sleek, like an Apple, SpaceX or Tesla website"; he dislikes the "Choose your garment" tile blocks and the Step 1-2-3-4 stepper. His picks in brainstorm: Tesla configurator (one right-hand scrolling panel, no numbers), light theme, opens on a ready garment + one prompt, sticky summary bar with Download opening a sheet, progressive disclosure for power tools, layout A (fixed right panel), stage = stitches close-up, keep the dark `--surround`.

Spec `docs/superpowers/specs/2026-09-30-studio-configurator-design.md`. One plan per PR under `docs/superpowers/plans/`:
- **PR 1, structure — #585, merged.** `Configurator` + `SummaryBar` + `DownloadSheet`; `StepNav`/`stepHistory`/`flow.js` steps deleted; panel on the right; templates in the My designs drawer; e2e through `e2e/helpers.js`.
- **PR 2, garment row + Original view — #586, merged.** `GarmentPicker` (Polo · Hat · Tee · More ›, a `role=menu`, never a dialog); "Original" is a fourth View segment painted on the canvas.
- **PR 4, theme — built 2026-10-01 on `claude/configurator-theme`, BEFORE PR 3 by Kent's call.** White page, `--fill #f4f4f4` for control grounds, body 13 px, two weights, accent only for CTA/selection/links/focus, 44 px `EMB·BOT` top bar, `e2e/theme-contrast.spec.js`.
- **PR 3, progressive disclosure (spec §5) — NOT planned, NOT built.** The panel is restyled but still long; the duplicate add controls (start control + ContentStep's buttons) wait on it.

**Why:** the wizard read as dated to Kent; structure had to change before any restyle would land.

**How to apply:**
- **Open, Kent's to call:** Original view lines up with the stitches only on the browser `image` lane (flat content box → stitch rect, within 2 px, e2e-pinned). On the auto-digitize lane the service returns only `px_per_mm` and the design size, so the artwork is fitted to the placement box — closing that needs the SERVICE to return the content box. Also open: four template cards sit above his designs in the drawer; "Polo" pill vs "Left Chest" subtitle; lettering is not shown in Original view; whether 13 px body / 10 px labels read too small (one token each).
- **Defects that only driving, measuring or looking found — after reviews had approved the code.** (1) Svelte `$: size = row("Size")` depends on the FUNCTION, not the prop it closes over; the unit test set props at render and passed — test prop updates with `rerender`. (2) `applyTemplate` replaces the whole project; moving templates into the drawer made one click overwrite the open design. (3) My plan fitted the image FRAME into a stitch bbox that corresponds to the artwork's CONTENT — a 12×12 px square against 23×20 stitched. (4) An e2e that passed with the feature stubbed out — run the mutation before trusting a pixel test. (5) Four layout defects the contrast sweep could not see (a note colliding with a field, a 31 px project name on a phone) — screenshots, read by eye. See [[run-the-app-color-cap-2026-09-07]], [[studio-display-layer-2026-08-25]].
- **Two grep/cascade traps in a theme pass.** `grep "var(--bg)"` cannot see `var(--bg, #f6f7fb)` — search `--bg[,)]` and the literal hex. And an element-selector rule (`input { font-size: 16px }`) loses to every class-styled field: the iOS no-zoom guard needs `!important`.
- Once a second `role=dialog` exists (the sheet), a bare `getByRole("dialog")` fails Playwright strict mode — name the dialog.
- The unit suite on Kent's box reds 2-12 engine-loading specs on their 10 s `beforeAll` hooks whenever other sessions load the CPU; `npx vitest run --hookTimeout=90000 --testTimeout=60000` is the honest local run (74/74, 1419/1419 on 2026-10-01). Pre-existing.
- `configurator-smoke`'s "no console errors" test fails locally with `[requestfailed] …:8721/health` whenever the digitizer service is down (a worktree cannot start it) — environment, not a regression; CI runs it with the service.
- **Screenshots from a worktree session:** the app's browser pane throttles timers when hidden, so scripts stall. A self-contained headless script works every time: spawn `node app/node_modules/vite/bin/vite.js --port 5190 --strictPort`, drive with `@playwright/test`'s `chromium`, `page.screenshot`, then Read the PNGs. Keep it in the git-ignored `.superpowers/sdd/<plan>/`.
- **Worktree shell grammar:** a bare `cd app` works and persists; any chain that mixes `cd`/loops with git is refused; `npm --prefix app exec playwright` does not find the config (add `--config`). A worktree session cannot Write into the memory junction — put the note in the worktree's `.claude/memory/` and commit it on the lane. See [[worktree-session-harness-guard-2026-09-17]].
- **A reboot mid-build cost nothing** because every lane was pushed and each plan had a ledger at `.superpowers/sdd/<plan>/progress.md` — resume = `git status`, read the ledger's tail, continue.
