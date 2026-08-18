# Where EMB Bot's files live

Quick reference for Kent — updated 2026-08-14.

## The working project (the real thing you edit and run)

`<repo-root>\` — this folder. Git repository.
Run the Studio: `cd app`, `npm install` (first time), `npm run dev`, open
http://localhost:5173

Do NOT move this folder into Google Drive — Drive sync breaks live git
repositories. Drive is for backups; this folder is the workbench.

## Backups on Google Drive (kentschaefer3@gmail.com)

Folder: `G:\My Drive\EMB-Bot\` (also visible at drive.google.com under
"My Drive > EMB-Bot")

- `EMB-Bot-2026-08-11.bundle` — most recent full-history snapshot. Every
  version of every file, every branch. To restore on any computer with git:
  `git clone EMB-Bot-2026-08-11.bundle EMB-Bot`
- `EMB-Bot-2026-07-27.bundle` — the same thing, one snapshot older. Kept as a
  second restore point; the 08-11 bundle supersedes it.
- `EMB-Bot-2026-07-27-files.zip` — plain zip of the project files as of
  2026-07-27 (includes the 70-font binary library). For when you just need to
  grab a file without git.
- `scratch_ink-2026-08-11.zip` — snapshot of the `scratch_ink\` working folder
  (font imports plus `_tiers.json` classification results). Regenerable, but
  re-deriving the tier measurements takes a full pipeline run, so it's kept.

## GitHub (stays current — best reference copy)

https://github.com/KS-Three/EMB-Bot — pushed 2026-07-27, transferred to the
KS-Three account 2026-08-06. Every future push updates it; the Drive files
above are point-in-time snapshots. (The old `kent746/EMB-Bot` URL still
redirects here for a while, per GitHub's own transfer behavior, but treat
this one as current.)

## Font source material (not in the repo)

- `G:\My Drive\EMB-Bot\Ink-Stitch Fonts\` — your downloaded clone of the
  Ink/Stitch open font collection (140 fonts, ~366 MB). Original/master copy.
  Moved here from the Desktop on 2026-08-14 so it lives with the other
  backups and syncs off-machine. It is reference material, not a git repo,
  so Drive sync is safe for it.
- `<repo-root>\scratch_ink\` — working copy of the same,
  plus measurement results (`_tiers.json` = the verified/unverified font
  classification, `_out\` = trial-imported font JSONs). Git-ignored;
  regenerable from the Drive folder above if deleted.

## Not backed up (on purpose, all regenerable)

- `node_modules\` — restore with `npm install` inside `app\`
- `scratch_ink\` — restore by re-copying from
  `G:\My Drive\EMB-Bot\Ink-Stitch Fonts\`
