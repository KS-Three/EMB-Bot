# Eye pairs, 2026-10-13: WoK 42's blinded sitting kit (`wok42-1013`)

Built under Kent's delegation (the EMB-Bot director, 2026-10-13); **the sitting
and its timing are Kent's.** Nothing here is judged, flipped or advanced. Read
`PRE-REGISTRATION.md` first: it was committed before anything was rendered, and
`spec.json` beside it is what the builder reads.

## What is ready

27 blind pairs: **19 live** (an arm against the base on one logo), 4 identical
pairs and 4 repeats as controls. Sides are shuffled under seed 20261013 with the
arm on the left in exactly half the live pairs; the picker shows opaque ids
only. Six logos, six arms (three of them reserves that replaced arms which
failed the manipulation check; `manifest.json` has pass or fail per arm and
nothing finer). The sealed key (`arms.json`) is NOT in this folder: it stays in
the render directory and is committed after the sitting, as every earlier
sitting's was. `manifest.json` carries its SHA-256, so the key cannot change.

**This is short of the 48 to 60 pairs asked for, and why:** only six logos
qualify (two customer logos already committed, four synthetic fixtures), and
three of the six arms did not isolate their variable on them. Sourcing more flat
logos with lettering is Kent's; the kit takes them from one `logos[]` edit in
`spec.json`.

## Where it lives

`digitizer/eye_pairs_out/wok42-1013/` in the primary checkout (gitignored, like
every render directory; it holds client logos' stitches). **Do not open
`arms.json`, `features.json`, `designs/` or `manipulation.json` there before the
sitting is over.** `picks.jsonl` is Kent's sitting and cannot be regenerated:
copy it here with the rest once it exists.

## To sit it

```
cd "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer"
.venv\Scripts\python -m tools.eye_pairs --serve --out eye_pairs_out\wok42-1013
```

LEFT, RIGHT or tie per pair (keys left / right / space, u to undo). Do not run
`--pair` while the picker is up.

## After the sitting

```
.venv\Scripts\python -m tools.eye_pairs.sitting analyse ..\docs\eye-pairs-2026-10-13\wok42\spec.json --out eye_pairs_out\wok42-1013 --markdown ..\docs\eye-pairs-2026-10-13\wok42\analysis.txt --inputs ..\docs\eye-pairs-2026-10-13\wok42\sitting-inputs.json
```

It refuses until every pair is picked, then prints Cohen's kappa with its
two bootstrap intervals and n for the four registered leads (trims is the
control), the trims-held split, the passing arms alone, and how well the
expected picks predicted him; **no raw agreement figure is computed.** Use this,
not `--reveal`, for the reading: `--reveal` is the older reader and still prints
a raw `a` beside its kappa. `--append-to` merges the sitting into a
density-flow inputs file so the pooled instrument can be re-run at the larger n.

Then commit, from `docs/eye-pairs-2026-10-13/wok42/`: `picks.jsonl`,
`pairs.json`, `arms.json`, `sitting.json`, `manipulation.json` (the table of
deltas the manifest withholds), the analysis text and `sitting-inputs.json`.

## To rebuild the kit

```
cd digitizer
python -m tools.eye_pairs.sitting prepare ..\docs\eye-pairs-2026-10-13\wok42\spec.json --out <dir> --workers 5 --link-photo-prep <primary checkout> --manifest <path>
```

About 25 minutes of CPU on four to five lanes (mfab is photo-class and reads the
rembg venv, which a worktree lacks until it is linked). It refuses to run over
picks. On the same machine, `designs_sha256` and `sealed_sha256` in the manifest
come out the same; on another platform the designs can differ at the margins
(`flag-before-after-2026-09-18`).
