# Where EMB Bot's files live

Quick reference for Kent — updated 2026-07-27.

## The working project (the real thing you edit and run)

`C:\Users\EE-LT-11030\EMB-Bot\` — this folder. Git repository.
Run the Studio: `cd app`, `npm install` (first time), `npm run dev`, open
http://localhost:5173

Do NOT move this folder into Google Drive — Drive sync breaks live git
repositories. Drive is for backups; this folder is the workbench.

## Backups on Google Drive (kentschaefer3@gmail.com)

Folder: `G:\My Drive\EMB-Bot\` (also visible at drive.google.com under
"My Drive > EMB-Bot")

- `EMB-Bot-2026-07-27.bundle` — the ENTIRE project history, every version of
  every file, every branch. To restore on any computer with git:
  `git clone EMB-Bot-2026-07-27.bundle EMB-Bot`
- `EMB-Bot-2026-07-27-files.zip` — plain zip of the project files as of
  2026-07-27 (includes the 70-font binary library). For when you just need to
  grab a file without git.

## GitHub (stays current — best reference copy)

https://github.com/kent746/EMB-Bot — pushed 2026-07-27. Every future push
updates it; the Drive files above are point-in-time snapshots.

## Font source material (not in the repo)

- `C:\Users\EE-LT-11030\Desktop\Ink-Stitch Fonts\` — your downloaded clone of
  the Ink/Stitch open font collection (140 fonts, ~300 MB). Original/master
  copy.
- `C:\Users\EE-LT-11030\EMB-Bot\scratch_ink\` — working copy of the same,
  plus measurement results (`_tiers.json` = the verified/unverified font
  classification, `_out\` = trial-imported font JSONs). Git-ignored;
  regenerable from the Desktop folder if deleted.

## Not backed up (on purpose, all regenerable)

- `node_modules\` — restore with `npm install` inside `app\`
- `scratch_ink\` — restore by re-copying from the Desktop folder
