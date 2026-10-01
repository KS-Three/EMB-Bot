---
name: studio-configurator-pr1-2026-09-30
description: The Studio wizard was replaced by a Tesla-style configurator (PR #585, 1 of 4); what Kent picked, what driving the app found that 12 reviews did not, and what PRs 2-4 still owe
metadata:
  type: project
---

Kent's brief 2026-09-30: "modern and sleek, like an Apple, SpaceX or Tesla website"; he dislikes the "Choose your garment" tile blocks and the Step 1-2-3-4 stepper. His picks in brainstorm: Tesla configurator (one right-hand scrolling panel, no numbers), light theme, opens on a ready garment + one prompt, sticky summary bar with Download opening a sheet, progressive disclosure for power tools, layout A (fixed right panel), stage = stitches close-up with an Original chip (no garment silhouette view), keep the dark `--surround`.

Spec `docs/superpowers/specs/2026-09-30-studio-configurator-design.md`; PR 1 plan `docs/superpowers/plans/2026-09-30-studio-configurator-pr1-structure.md`. PR 1 = KS-Three/EMB-Bot#585: `Configurator` + `SummaryBar` + `DownloadSheet`, `StepNav`/`stepHistory`/`flow.js` steps deleted, panel on the right, templates in the My designs drawer, 24 e2e specs migrated through `e2e/helpers.js`. **PRs 2-4 are NOT planned yet** (garment pill row + Original chip; progressive disclosure; theme pass) — each needs its own plan from the same spec, written against PR 1's real shape.

**Why:** the wizard read as dated to Kent; structure had to change before any restyle would land.

**How to apply:**
- Three defects were found only by DRIVING the app or running e2e, after per-task reviews had approved the code: (1) `$: size = row("Size")` in Svelte depends on the FUNCTION, not the prop it closes over, so the bar never updated — the unit test set props at render and passed; test prop updates with `rerender`. (2) Moving `TemplateRow` into the drawer squeezed the project list to 32 px at 1280x720. (3) A template click in the drawer overwrote the open design — the old step-1 placement had hidden that `applyTemplate` replaces the whole project. See [[run-the-app-color-cap-2026-09-07]] and [[studio-display-layer-2026-08-25]].
- Once a second `role=dialog` exists (the sheet), a bare `getByRole("dialog")` fails Playwright strict mode — name the dialog.
- The unit suite on Kent's box reds 2-12 engine-loading specs on their 10 s `beforeAll` hooks whenever other sessions load the CPU (18 node processes seen); `npx vitest run --hookTimeout=90000 --testTimeout=60000` gave 71/71, 1391/1391. Pre-existing, not a regression.
- A worktree session can serve its own app for the browser pane: `npm run dev -- --port 5190 --strictPort` in the background, then `preview_start` with the URL (the launch.json route reads the MAIN checkout). See [[worktree-session-harness-guard-2026-09-17]].
- A worktree session cannot Write into the memory junction (it points at the main checkout) — put the note in the worktree's `.claude/memory/` and commit it on the lane.
- Open calls left for Kent in the PR body: four template cards now sit above his designs in the drawer; the interim panel has duplicate add controls (start control + ContentStep's buttons) until PR 3.
