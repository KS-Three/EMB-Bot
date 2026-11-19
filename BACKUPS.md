# Where EMB Bot's files live

Quick reference for Kent — rewritten 2026-11-19 to match what is actually on
Drive. (The 2026-08-14 version listed bundles and zips that are no longer there.)

## The working project (the real thing you edit and run)

`<repo-root>\` — this folder. Git repository.
Run the Studio: `cd app`, `npm install` (first time), `npm run dev`, open
http://localhost:5173

Do NOT move this folder into Google Drive — Drive sync breaks live git
repositories. Drive is for backups; this folder is the workbench.

## What is on Google Drive now (kentschaefer3@gmail.com)

Folder: `G:\My Drive\EMB-Bot\` (also visible at drive.google.com under
"My Drive > EMB-Bot"). Listed read-only on 2026-11-19:

| Item | Contents |
|---|---|
| `Ink-Stitch Fonts\` | 637 files, about 364 MB: the downloaded clone of the Ink/Stitch open font collection (see below). |
| `Embroidery Files\` | 139 files, about 15 MB, in 13 client and test folders (Becker Marine, Bridge Bar, C Gaulke Plowing, Gaulke Roofing, Golden Tee, Hotel Fremont, MFAB, Precision Drone, Proseal, Test Files, TIRES, To a T Machine, To a T_Becker Beanies): reference stitch files and art. |
| `worktree-leftovers-2026-11-08\` | 52 small files in 12 or more `wt-*` folders: what was left behind when old git worktrees were cleaned up on 2026-11-08. Not a backup of anything current. |
| `software-board\` | 17 files, including a `.git` folder and `node_modules`. Work project, moved to `Claude Work\software-board` on 2026-08-17; this copy dates from 2026-08-14. A `.git` on Drive is the thing the rule above warns about; treat it as a stale copy. |
| `.claude\` | Two small files from 2026-08-14 (`scheduled_tasks.lock`, `settings.local.json`). |
| `corpus\` | Empty. |

**There is no git bundle and no `scratch_*` zip on Drive.** The files the
2026-08-14 version of this page described (`EMB-Bot-2026-08-11.bundle`,
`EMB-Bot-2026-07-27.bundle`, `EMB-Bot-2026-07-27-files.zip`,
`scratch_ink-2026-08-11.zip`) were not found on 2026-11-19. So Drive holds no
copy of the repository's history and no copy of any gitignored `scratch_*`
folder other than what is regenerable from `Ink-Stitch Fonts\`. **Whether to cut
new bundles or zips is Kent's decision and is still open**; nothing here
decides it.

## GitHub (stays current — best reference copy)

https://github.com/KS-Three/EMB-Bot — transferred to the KS-Three account
2026-08-06. Every push updates it, so it is the only current off-machine copy of
the tracked files. It does not hold the gitignored `scratch_*` folders. (The old
`kent746/EMB-Bot` URL redirected here for a while after the transfer; treat
this one as current.)

## Procedure, if new snapshots are ever made

This is how the old snapshots were made; it is not a statement that they exist.

- Full-history bundle (every version of every file, every branch), from the
  repo root: `git bundle create <name>.bundle --all`, copied to the Drive
  folder. Restore on any computer with git: `git clone <name>.bundle EMB-Bot`.
- Plain files zip: zip the project folder without `.git` and `node_modules`.
- `scratch_ink\` zip: the font imports plus `_tiers.json` classification
  results. Regenerable, but re-deriving the tier measurements takes a full
  pipeline run.

## Font source material (not in the repo)

- `G:\My Drive\EMB-Bot\Ink-Stitch Fonts\` — your downloaded clone of the
  Ink/Stitch open font collection. Original/master copy. Moved here from the
  Desktop on 2026-08-14. It is reference material, not a git repo, so Drive
  sync is safe for it.
- `<repo-root>\scratch_ink\` — working copy of the same, plus measurement
  results (`_tiers.json` = the verified/unverified font classification,
  `_out\` = trial-imported font JSONs). Git-ignored. The font clone part can be
  re-copied from the Drive folder above; the measurement results cannot (no zip
  of them is on Drive now).

## Not backed up (all regenerable except where noted)

- `node_modules\` — restore with `npm install` inside `app\`
- `scratch_ink\` — the font clone is restorable from the Drive folder; the
  `_tiers.json` and `_out\` results are not backed up.
- `scratch_corpus\`, `scratch_kent\`, `scratch_packs\` — gitignored and not
  disposable (CLAUDE.md footgun 5); no Drive copy.
