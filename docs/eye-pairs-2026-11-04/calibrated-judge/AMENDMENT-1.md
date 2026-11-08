# Amendment 1 (2026-11-07): the rubric comes from Kent's reasons, and is frozen here

This amends `PRE-REGISTRATION.md` in this folder. It does not change the split,
the held-out labels, the primary statistic or the bar.

## The rubric freeze

**`RUBRIC.md` sha256:
`16836a48790c2738ab581dda75de9e4eac83ee4e8eb30ea8cdb875ec1b81b243`**

- The hash is taken over the file's bytes as committed: ASCII, LF line
  endings. `.gitattributes` pins `RUBRIC.md` to `eol=lf`, so a
  `core.autocrlf=true` checkout hashes the same. Check it with
  `git show <this commit>:docs/eye-pairs-2026-11-04/calibrated-judge/RUBRIC.md | sha256sum`.
- **This file is the freeze record** that `PRE-REGISTRATION.md` calls
  `RUBRIC-FREEZE.md`. It carries a different name, and it is the commit that
  comes before any held-out picture is opened. Every held-out verdict row must
  carry this `rubric_sha256`, and a row with any other value is not scored.
- `vlm_judge.PROMPT` is unchanged (sha256
  `24acb29674ecca4b045c176cbb00ac971512ef510d4a7bea69233ce1c928095a`).
  `RUBRIC.md` is appended to it as plain text, as the pre-registration says.

## What changed, and why

- **The rubric's source is Kent's own reasons.** The pre-registration said the
  rubric would be written from the calibration kit, Kent's reasons, and the
  calibration pairs' pictures and verdicts. Kent wrote those reasons
  2026-11-07 (`reasons.json`, stamped 02:23 to 02:33 UTC on 11-08). This
  amendment narrows the source further. **Every principle in `RUBRIC.md` rests
  on a quote of Kent's, cited by kit id.** The pictures were used only to check
  that each quote matched what the pair shows. No principle comes from the old
  judge's reasons, or from the author's own eye.
- **A QUESTION line.** Kent wrote on C20: "please improve questions for what
  i'm judging next time". `RUBRIC.md` opens with a QUESTION line that states
  exactly what the judge decides: lettering first (pen-stroke flow, true shape,
  smooth curves, straight strokes), then the rest of the art (nothing breaks
  off, crosses over or blobs). It also says when an answer is a tie. The line
  is part of the frozen rubric, so it is hashed with it.
- **Calibration relabels.** 14 of the 22 reasons revise Kent's original pick.
  `CALIBRATION-RELABELS.md` lists each one with his words. They are
  calibration-only. They informed the rubric and are used nowhere else.

## What did NOT change

- **Held-out labels.** Kent's original labels on the 92 HELD-OUT pairs stand
  exactly as `judge_calibration.pool()` reads them. No reason was asked for,
  or written, on any held-out pair.
- **The split.** `split-calibration.json` and `split-held-out.json` are
  untouched (`pool_sha256`
  `bc0f78c8253e52b2ad96ae7f1d6895804fb7eac6508f213d425c474fe1951376`).
- **The primary and the bar.** The statistic is unchanged: 3-way
  linear-weighted kappa against Kent, ties in, on the 92 held-out pairs. The
  pass bar is unchanged: **kappa >= +0.55 AND a pair-bootstrap CI lower bound
  > +0.34**, both required. The secondaries, the baseline, the controls and the
  one-run rule are unchanged.

## What this lane opened

- It opened all 22 calibration pairs' pictures (art, LEFT, RIGHT, and both 3x
  crops, `img/C01_*` to `img/C22_*`), with `kit.json` and `reasons.json`.
- It did not open `split-held-out.json`, any held-out picture, or the
  `pro-lettering-1102` sitting's images. It also did not open any file
  under `vlm-judge*/`.
- **No held-out picture exists for the 11-06 set yet.** Phase B re-draws those
  pictures after this commit. The 11-04 sitting's original images do exist on
  disk from 11-02, but this lane did not open them.
- This lane judges nothing. The held-out run belongs to a fresh session, under
  the pre-registration's rules.
