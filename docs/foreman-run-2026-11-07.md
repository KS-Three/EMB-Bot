# Foreman run 2026-11-07/08: merge and push findings

The k3 foreman ran from 11-07 11:14 to 11-08 ~03:00 local, in five windows: monitor, then UI simulation, then ultra K3, then usage burn, then wrap-up. In that time **62 PRs merged** (#1301 to #1362) and `main` ended green. This file covers what the merging and pushing taught. Product results stay in their own PR bodies and memory notes.

## What ran where

- **Cloud lanes.** Two waves of 10 started and landed: #1284 to #1298, and #1303 to #1312. They started only from a desktop-app turn in which Kent spoke. A Remote Control turn, a cron turn and a notification turn are all refused ("Start sessions only on the user's own words"). From the ultra wave, 7 cards were never clicked, so no session exists for them.
- **Local lanes.** Every other refill ran as an Agent in its own scratchpad worktree (`wt-*`), using a shared lane preamble. About 40 lanes ran.
- **Workflows.** These were the local-lane batches, the bug hunts, the post-merge reviews and the judge phase B.

## Merge and push findings

These are the ones that cost time and would cost it again.

1. **`git branch -d` refuses every squash-merged branch.** The repo merges by squash, so the branch tip is never an ancestor of `main`. `-d` therefore refuses, and `-D` is barred. Cleanup on 11-08 left 21 local `claude/*-1107` branches whose PRs were all MERGED. They are harmless and need a decision of their own (see "Left over" below). Do not try to pass the `-d` check by pushing the branch back.
2. **A Playwright `test.fail()` is an expected failure.** A results parser that counts `status != passed` as red reads a known `test.fail()` spec as a new regression. `scratchpad/pw_fail.py` now skips a result whose `status == expectedStatus`. Main "went red" after #1345 partly through this miscount. The real causes were a field-compare poll throw and noisy perf medians, fixed in #1356.
3. **An empty job log is not the absence of a failure.** Run `gh run download <run> -n studio-e2e-shard-N`, then parse `results-parallel.json`. The log endpoint returned nothing for several red shards.
4. **A static import can need the engine before `beforeAll`.** #1360 went red with `Engine not loaded`. `projectThumb.js` had started importing `generate.js`, and a spec imported it at module scope. The fix was to load the engine in `vi.hoisted` before the imports, the same way `projectThumb.spec.js` already did.
5. **Studio DOM invariants that broke CI:**
   - `.hoop` holds exactly one `<canvas>`. In #1342 a second canvas broke the strict locators; the fix was an offscreen canvas shown as an `<img>`.
   - Nothing in-flow goes in `.fieldwrap`. In #1313 an edit bar shrank `.hoop` in the middle of a gesture.
   - A field render resets canvas state first. In #1341 a round `lineCap` leaked into the hoop dash.
   - A spec that reads canvas pixels sets `reducedMotion: "reduce"`. In #1347 the 2.6 s outline pulse was read while it faded, which a faster repaint exposed.
   - Studio specs live beside their component, never in `app/test/`, because the root `node --test` collects every `test/` folder (#1313).
6. **Fix lanes collided on branch names.** The post-merge review named fix branches by PR number plus file. Two findings on #1344's `projectThumb.js` therefore got the same branch and the same worktree, and one owner had to absorb the other (#1360). Put a finding index in fix-lane branch names.
7. **The app's PR state for archived sessions lags GitHub.** `list_sessions` reported 9 PRs as OPEN that GitHub showed MERGED, some of them weeks old (#643, #647, #648). Check `gh pr view` before acting on the app's `prState`.
8. **Local lanes filled the disk.** C: reached 143 MB free at about 02:15 on 11-08, and agents failed with ENOSPC. Each lane carries its own `npm ci` node_modules of about 900 MB. Remove a lane as soon as its PR merges and stop starting lanes below about 10 GB free (memory `local-lanes-fill-disk-2026-11-08`).
9. **A dev server or watcher left running locks its worktree.** `git worktree remove` then unregisters the lane but cannot delete the folder ("Invalid argument"). Stop the process (a `node` from the lane's `node_modules/.bin`) and send the leftover folder to the Recycle Bin.
10. **Arm auto-merge while the PR is BLOCKED.** That worked for every foreman PR. The only manual merges were PRs that had already gone CLEAN, and under Kent's 11-06 ruling the foreman merges those itself.

## Cleanup done 2026-11-08

- **Worktrees removed:** 30. All of them were clean, or their leftover diffs had been copied to Drive first.
- **Leftover diffs backed up:** before removal, each dirty lane's `git diff HEAD` and untracked files were copied to `G:\My Drive\EMB-Bot\worktree-leftovers-2026-11-08\<lane>\` and verified with `cmp`. Most were debug lines and lane-local Playwright/Vite configs.
- **Sessions deleted:** 85 archived app sessions whose PRs were MERGED, or CLOSED with the branch still on origin.
- **Sessions still archived:** 8 with no PR were left archived, not deleted, because nothing shows their results were recorded. The 4 sessions whose lanes are still on disk were also kept (`d2-floor-content-gate`, `d6-fill-sections`).
- **Judge phase B:** pushed and opened as #1363 (held-out FAIL, measurement only; auto-merge armed).

## Left over, with the reason

These worktrees were kept, and their diffs are also on Drive:

- **`wt-smoothpan`** (`claude/smooth-pan-1107`, pushed at f7237168). Smooth pan with a shifted bitmap. It conflicts with `main` in `EmbroideryField.svelte`, and no PR has been opened.
- **`wt-thinink` and `wt-thinink-counters`.** Bug-hunt fix attempts in `thin_ink.py`, with new tests, uncommitted. Not verified.
- **`wt-smalltext`.** Two new small-text retrace tests, uncommitted. Not verified.

Two `.claude/worktrees/` lanes are also still on disk:

- **`d2-floor-content-gate-545b86`.** HEAD 4b77d1e9 is on no origin branch.
- **`d6-fill-sections-6da150`.** HEAD b9d3fd34 is on no origin branch, and the lane holds `pro_renders/` (footgun 5).

The squash-merged local branches from point 1 also remain.
