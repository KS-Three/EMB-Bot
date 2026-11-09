# Eye pairs, 2026-11-08: the DreamSim confirmation sitting (`dreamsim-confirm-1108`)

Built for Kent by the EMB-Bot director's delegation; **the sitting and its
timing are Kent's.** Nothing here is judged, flipped or advanced. Read
`PRE-REGISTRATION.md` first (committed before anything was rendered or scored);
`spec.json` beside it is what the builder reads. This sitting is NOT blind to
prior judging, by Kent's ruling (the `rejudge_pro_jobs` key); the pair's side
is still hidden.

## To rebuild the kit (before the sitting)

A worktree has no `.venv` and no rembg venv; use the primary checkout's.
Take the laptop's shared CPU slot first (`%TEMP%\embwt\cpu.lock`); `--workers 3`
inside one hold is fine. Point the pro-file lookups at Kent's folders:

```
$env:EMB_BRIDGE_PRO = "C:\Users\EE-LT-11030\Claude Personal\Embroidery\Digitized Designs\Bridge Logo"
$env:EMB_SCRATCH_KENT = "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\scratch_kent"
cd digitizer
"C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer\.venv\Scripts\python.exe" -m tools.eye_pairs.sitting prepare ..\docs\eye-pairs-2026-11-08\dreamsim-confirm\spec.json --out "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer\eye_pairs_out\dreamsim-confirm-1108" --workers 3 --link-photo-prep "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot" --manifest ..\docs\eye-pairs-2026-11-08\dreamsim-confirm\manifest.json
```

`prepare` refuses to run over picks and writes `designs/<logo>__<arm>.dst`
beside each design. It does not enforce the budget: if the manifest reports more
than 70 live pairs, drop whole logos in the `drop_order_if_over_budget` order of
`spec.json` as a dated amendment to `PRE-REGISTRATION.md` and rebuild, before
any pick exists.

## To sit it

```
cd "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer"
.venv\Scripts\python -m tools.eye_pairs --serve --out eye_pairs_out\dreamsim-confirm-1108
```

LEFT, RIGHT or tie per pair (keys left / right / space, `u` to undo). Do not run
`--pair` while the picker is up. **Do not open `arms.json`, `features.json`,
`manipulation.json` or `designs/` in that folder before the sitting is over.**
`manifest.json` here is the public description of the kit; it carries the sealed
key's hash and no pair-to-arm mapping.

## After the sitting

From `digitizer/`, with the same two environment variables set:

```
.venv\Scripts\python -m tools.eye_pairs.sitting analyse ..\docs\eye-pairs-2026-11-08\dreamsim-confirm\spec.json --out eye_pairs_out\dreamsim-confirm-1108 --markdown ..\docs\eye-pairs-2026-11-08\dreamsim-confirm\analysis.txt --inputs ..\docs\eye-pairs-2026-11-08\dreamsim-confirm\sitting-inputs.json
```

Then the DreamSim reading, from the repo root with the yardstick venv
(`tools/requirements-yardstick.txt`; `docs/yardstick-perceptual.md`). The pair
list is the live population-A pairs; `from-sitting` refuses until every pair is
picked and prints skip counts and reasons to stderr. **Check it reports 0
pro-file skips before scoring** (it relies on the two environment variables):

```
python -m tools.yardstick_perceptual from-sitting docs\eye-pairs-2026-11-08\dreamsim-confirm\spec.json --out-dir digitizer\eye_pairs_out\dreamsim-confirm-1108 --out <R>\pairs.csv
python -m tools.yardstick_perceptual score <R>\pairs.csv --labels --oracles --out <R>\score
```

`<R>` is a scratch folder outside `docs/`. Shipped defaults only (ppm 12, pad 3,
max-px 1024, registration on, monochrome, tie-band 0, ensemble); changing any is
a new pre-registration.

The hold-out (reported separately, never pooled), on the 1102 sitting:

```
python -m tools.yardstick_perceptual from-sitting docs\eye-pairs-2026-11-02\pro-size-lettering\spec.json --out-dir digitizer\eye_pairs_out\pro-lettering-1102 --out <R1102>\pairs.csv
python -m tools.yardstick_perceptual score <R1102>\pairs.csv --labels --oracles --out <R1102>\score
```

Do not copy any `designs/*.dst`, pro DST or render under `docs/`.
