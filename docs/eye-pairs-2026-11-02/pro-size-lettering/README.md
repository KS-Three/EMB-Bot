# Eye pairs, 2026-11-02: the pro-sized lettering sitting (`pro-lettering-1102`)

Built for Kent by the EMB-Bot director's delegation; **the sitting and its
timing are Kent's.** Nothing here is judged, flipped or advanced. Read
`PRE-REGISTRATION.md` first (committed before anything was rendered); `spec.json`
beside it is what the builder reads. It supersedes the never-sat wok42-1013 kit.

## To sit it

```
cd "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer"
.venv\Scripts\python -m tools.eye_pairs --serve --out eye_pairs_out\pro-lettering-1102
```

LEFT, RIGHT or tie per pair (keys left / right / space, `u` to undo). Do not run
`--pair` while the picker is up. **Do not open `arms.json`, `features.json`,
`manipulation.json` or `designs/` in that folder before the sitting is over.**
`manifest.json` here is the public description of the kit; it carries the sealed
key's hash and no pair-to-arm mapping.

## After the sitting

```
.venv\Scripts\python -m tools.eye_pairs.sitting analyse ..\docs\eye-pairs-2026-11-02\pro-size-lettering\spec.json --out eye_pairs_out\pro-lettering-1102 --markdown ..\docs\eye-pairs-2026-11-02\pro-size-lettering\analysis.txt --inputs ..\docs\eye-pairs-2026-11-02\pro-size-lettering\sitting-inputs.json
```

It refuses until every pair is picked. It prints kappa with both bootstrap
intervals and n for the registered leads on every live pair, then the new
**population A distance-to-the-pro reading** of cuts, hops and needle-up mm (all
pairs, and per stratum so the trims control stands apart), with the plain-cost
reading beside it. No raw agreement figure is computed. The pro's DSTs are read
from `scratch_kent/` (`EMB_SCRATCH_KENT`); on a machine without them the section
says so instead of failing. Do not copy any `designs/*.dst` under `docs/`.

## To rebuild the kit

A worktree has no `.venv` and no rembg venv; use the primary checkout's.

```
cd digitizer
"C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer\.venv\Scripts\python.exe" -m tools.eye_pairs.sitting prepare ..\docs\eye-pairs-2026-11-02\pro-size-lettering\spec.json --out "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer\eye_pairs_out\pro-lettering-1102" --workers 3 --link-photo-prep "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot" --manifest ..\docs\eye-pairs-2026-11-02\pro-size-lettering\manifest.json
```

Take the laptop's shared CPU slot first (`%TEMP%\embwt\cpu.lock`, handoff
section 5); `--workers 3` inside one hold is fine. `prepare` refuses to run over
picks, writes `designs/<logo>__<arm>.dst` beside each design, and the manifest's
`designs_sha256` and `sealed_sha256` come out the same on the same machine.
