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
| `scratch-backup-2026-11-19.zip` | 146.6 MB, 721 files: the gitignored, not-disposable folders `scratch_kent\`, `scratch_corpus\`, `scratch_packs\`, `scratch_digitized_study\`, `scratch_pro_pair_proseal\`, `scratch_commons_logos\` (Kent's call 2026-11-19). Verified the same day: entry count matches the source file count and the Drive copy's hash matches the zip built locally. |
| `Ink-Stitch Fonts\` | 637 files, about 364 MB: the downloaded clone of the Ink/Stitch open font collection (see below). |
| `Embroidery Files\` | 139 files, about 15 MB, in 13 client and test folders (Becker Marine, Bridge Bar, C Gaulke Plowing, Gaulke Roofing, Golden Tee, Hotel Fremont, MFAB, Precision Drone, Proseal, Test Files, TIRES, To a T Machine, To a T_Becker Beanies): reference stitch files and art. |
| `worktree-leftovers-2026-11-08\` | 52 small files in 12 or more `wt-*` folders: what was left behind when old git worktrees were cleaned up on 2026-11-08. Not a backup of anything current. |
| `software-board\` | 17 files, including a `.git` folder and `node_modules`. Work project, moved to `Claude Work\software-board` on 2026-08-17; this copy dates from 2026-08-14. A `.git` on Drive is the thing the rule above warns about; treat it as a stale copy. |
| `.claude\` | Two small files from 2026-08-14 (`scheduled_tasks.lock`, `settings.local.json`). |
| `corpus\` | Empty. |

**There is no git bundle on Drive.** The files the 2026-08-14 version of this
page described (`EMB-Bot-2026-08-11.bundle`, `EMB-Bot-2026-07-27.bundle`,
`EMB-Bot-2026-07-27-files.zip`, `scratch_ink-2026-08-11.zip`) were not found on
2026-11-19. Kent decided the same day: zip the irreplaceable `scratch_*` folders
(the row above), and no git bundle, because GitHub already holds every pushed
branch. The zip is a point-in-time copy; re-cut it (procedure below) after
adding anything to those folders that matters.

## GitHub (stays current — best reference copy)

https://github.com/KS-Three/EMB-Bot — transferred to the KS-Three account
2026-08-06. Every push updates it, so it is the only current off-machine copy of
the tracked files. It does not hold the gitignored `scratch_*` folders. (The old
`kent746/EMB-Bot` URL redirected here for a while after the transfer; treat
this one as current.)

## Procedure for new snapshots

- Scratch zip (how the 2026-11-19 one was made), PowerShell from the repo root:
  `Compress-Archive -Path scratch_kent,scratch_corpus,scratch_packs,scratch_digitized_study,scratch_pro_pair_proseal,scratch_commons_logos -DestinationPath <scratchpad>\scratch-backup-<date>.zip`,
  then copy it to the Drive folder and check the zip's entry count against
  the source file count before trusting it.
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
- `scratch_bench\`, `scratch_trials\`, `scratch_lanes\` — run outputs, not in
  the 2026-11-19 zip.
