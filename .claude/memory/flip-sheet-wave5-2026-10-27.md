---
name: flip-sheet-wave5-2026-10-27
description: Flip sheet wave 5 -- every layout flag still waiting on Kent, OFF|ON|pro on main ce8cc87d (4a087210); four asked, gate 3 clear on all; Kent flipped bean ink + part_touching + italic lean ON, held fill_section_travel OFF; the keyline trio is inert off MFab so its three switches are not asked
metadata:
  type: project
---

2026-10-27, follow-on to [[flip-sheet-wave3-2026-10-26]]. One inlined sheet
(`report --w5 --inline --artifact`), rows ASKED or SHOWN; OFF is main ce8cc87d
merged into the sheet lane (`4a087210`). Main moved three times mid-render
(#1127, #1134, then #1136's script_strokes flip); each time OFF was re-digitized
on the merge and an ON cell kept only where its job's OFF stayed byte for byte
(#1136 moved only Bridge and Tires, as its PR said). The committed doc carries
OFF / ON / where crops only: no pro panels in the public repo (#1136's rule);
they live in the private Artifact.

Asked, all gate 3 clear (bare thread at 0.20/0.25/0.30 mm never rose). Trims
are DST records, OFF -> ON (pro):
- `bean_ink_outlined_letters` + `text_cluster_part_touching` belong together:
  on MFab LC each alone leaves a letter of AND hollow (bean ink: the N still
  white wedges; part_touching: A and N sew as white with a black ring); both
  ON sew A N D solid black like the pro, trims 19 -> 14 (20). MFab hat:
  part_touching 22 -> 18 (19); bean ink byte-identical (the control).
- `fill_section_travel`: changes 6 of 7 hats, DST trims by one at most
  (Becker large +1, MFab hat and the drone -1); invisible at viewing size.
- `lettering_columns_italic_lean`: ProSeal hat / beanie bar angles only,
  34 / 28 trims unchanged.

**Finding:** the keyline trio (fold slivers + skip covered + absorb fragments
all ON) sews OFF's DST byte for byte on all ten white jobs off MFab. The three
switches act only on MFab, where the gate (#1122) already has them ON, so no
render can judge a global flip; the sheet shows the trio row and asks none.

**Trap:** cells from an older tool lack `bare_mm`, so gate 3 reads them as
n/a and the verdict silently covers fewer jobs. Re-render an ASKED row's
adopted cells (Bridge's fill_section_travel came back byte-identical to the
adopted ones, confirming the OFF-md5 adopt rule, and gave the read).

Kent's answers, 2026-10-27, relayed by the director (flip PR off #1140):
- bean ink + part_touching: "Both ON (Recommended)" -- both flipped ON.
  Trade-offs taken with them: on #1128's lettering board (LC 6-10 mm line)
  reach dips 0.57 -> 0.50 and rail wobble p90 rises 0.035 -> 0.043 mm; exposed
  travel (`travel_cover`, no veto) rises on MFab, hat 23.3 -> 36.1 mm and LC
  35.8 -> 41.1 mm with both, bare thread 0 at every clearance.
- `fill_section_travel`: "Hold OFF (Recommended)" -- stays an OFF `cfg.extra` key.
- `lettering_columns_italic_lean`: "Flip ON (Recommended)" -- flipped ON.
The OFF arms are `tests/conftest.py`'s `FLIP_2026_10_27` (in PRE_FLIP).

**How to apply:** before asking a cluster of flags, run one combined arm per
job and ask only where its DST differs from OFF; and pair flags whose cures
need each other (bean ink with part_touching) in one third cell, since each
alone reads as a regression.
