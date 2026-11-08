# Calibration relabels: where Kent's reason revises his original pick

On 2026-11-07, Kent wrote a one-line reason on each of the 22 CALIBRATION
pairs in the phase-A kit (`judge_calibration` kit, `kit_sha256`
`850d2c0601776c6dcf9d261ae6c5d318d6e65bcd884138808400c42c49169314`). For 14
of them the reason names a different answer from his original pick. This file
lists them.

**Scope.** These relabels are calibration-only. They fed the writing of
`RUBRIC.md` and nothing else. **No HELD-OUT label is changed.** The primary
is still scored against Kent's original labels on the 92 held-out pairs
(`AMENDMENT-1.md`). The relabels are not pooled with any sitting and do not
feed `pooled-inputs.json` or a picks file.

**Frame.** "Original" is the kit's `kent` field, Kent's label mapped into
the frame the kit shows (LEFT / RIGHT as on the page). "Revised" is the answer
his reason gives in that same frame. "Both bad" is read as a tie.

## The 14 revised pairs

| Kit | Pool id | Original | Revised | Kent's words |
|---|---|---|---|---|
| C01 | vlm-judge-100:P017 | L | R | "They are bothe poor, but the right one is better becuase the stitching follows the flow of the "R". The left one has that straight satin stitching across the top the breaks up the flow." |
| C03 | vlm-judge-100:P035 | L | tie (both bad) | "They both suck, they don;t follow the rules of writting letters with a pen/pencil." |
| C04 | vlm-judge-100:P048 | R | L | "Left is better, my bad." |
| C07 | vlm-judge-100:P083 | L | R | "Right is better, my bad (see previous comment)" |
| C12 | vlm-judge-100:P019 | tie | R | "Right is better, the letters follow the rules of penmenship." |
| C13 | vlm-judge-100:P051 | tie | L | "Left is better, the right anchor breaks off on the left side." |
| C14 | vlm-judge-100:P066 | tie | L | "Left is better." |
| C15 | vlm-judge-100:P085 | tie | L | "Left is better. much smoother lettering." |
| C16 | vlm-judge:P008 | tie | L | "Left is better, the circle blob of stitching in the middle of the "M" is wierd" |
| C17 | vlm-judge:P047 | tie | R | "Right is better for letter shape (the left side made the top of the "L"s on an angle, which is wrong)." |
| C18 | vlm-judge:P055 | tie | L | "Left is correct." |
| C19 | vlm-judge:P058 | tie | L | "I choose left, because of the stitching on the "A" has better flow." |
| C20 | vlm-judge-100:P037 | L | R | "Right, by far. please improve questions for what i'm judging next time, i never should have choosen left." |
| C22 | vlm-judge:P030 | L | tie (both bad) | "These both suck." |

By kind: 4 sides flipped to the other side (C01, C04, C07, C20), 8 ties
became sides (C12 to C19), and 2 sides became ties (C03, C22).

## The 8 pairs his reason keeps

| Kit | Pool id | Pick | Kent's words |
|---|---|---|---|
| C02 | vlm-judge-100:P024 | L | "Left is way better, no brainer." |
| C05 | vlm-judge-100:P049 | R | "Right is better, notice how straight the "I" is, it;s not wavey like the left one." |
| C06 | vlm-judge-100:P052 | R | "Right is better, but these are damn near the same." |
| C08 | vlm-judge:P034 | L | "Left is better the "O" is smoother and has better flow." |
| C09 | vlm-judge:P037 | L | "Left is better, the "P" flows smoothly, and does not have the abrubt flat spot like the right "P"" |
| C10 | vlm-judge:P054 | R (read) | "The left is better w/ spacing between letters, but the right is better for lettering shape, it doesn't not have as much of an ab" |
| C11 | vlm-judge:P060 | L | "Left is better, that cross over stitch on the right one is wierd." |
| C21 | vlm-judge:P022 | R | "Right is better, notice how the stitching doesnt flow like the rules of penmenship on the "h"." |

**C10 is a reading, not a statement.** The reason names a merit on each side,
and it is cut off mid-word in `reasons.json`. His original pick was RIGHT, and
the reason favours RIGHT on letter shape, so it is kept as RIGHT.

## Caveats on reading these

- **The 11-06 pairs were re-drawn.** Kent first labelled the 12 `vlm-judge-100`
  pairs on the 09-18 to 10-08 renders. The kit shows renders re-drawn under the
  11-06 rule (`PRE-REGISTRATION.md`, "Known limits"). So 9 of the 14 revisions
  (C01, C03, C04, C07, C12, C13, C14, C15, C20) may partly reflect different
  pictures rather than a change of mind. The 5 `vlm-judge` revisions (C16 to
  C19, C22) are on the same pictures he saw on 11-02.
- **"see previous comment" (C07)** is quoted as written. C07 shows the same
  design as C01, with a different arm, so the comment most likely points back
  to C01's reason about the flow of the "R". That is a reading.
- **The old judge, against the revised labels.** Of the 14 revised pairs, the
  revised label now matches the old judge's verdict on 7 (C03, C12, C14, C15,
  C16, C18, C20). It is the opposite side on 3 (C13, C17, C19). It is a side
  against a tie on 4: the judge said tie and Kent now picks a side on C01,
  C04 and C07, and the judge picked a side where Kent now says both bad on
  C22. This is calibration data only. It says nothing about the
  held-out score.
