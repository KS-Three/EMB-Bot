---
name: the-80mm-ink-link-2026-10-15
description: Kent's five red circles on Fremont at 80 mm were mostly a STALE SERVICE; the one real defect (THE garbled at 80, clean at 81) was the text tagger's rescued round linking across inks, fixed by `text_cluster_rescued_ink_link` (ON); a letter at the small-shape floor flips doors
metadata:
  type: project
---

Kent, 2026-10-15, a Studio screenshot of Hotel Fremont at 80 mm on a Hat
(15,149 stitches) with EST, 1895, THE, the N of FREMONT and PLAY circled:
*"the fine detail and lettering has to be better than this ... Everything in
red needs to be resolved."*

**Four of the five were already cured on `main` and his service had not been
restarted.** The digitizer service was not even running on 8721 when the
session started; the job on his screen predated #955 (true size ON, 10-15
10:34 UTC) and #922 (Column lane ends, 10-14). Driving the real Studio on
today's service at his exact settings (Hat, design width 80, bean cap):
EST, 1895 and EAT | STAY | PLAY read as clean line letters, the N's foot is
clean. **When a screenshot disagrees with main, check the service's start
time before the engine** -- `Get-NetTCPConnection -LocalPort 8721` and the
process's `CreationDate`.

**The one real defect: THE at 80 mm, garbled; at 81 mm, clean.** The
Studio sends `target_width_mm` 80, every lane measurement had used 81.
`fremont_triage.run_arm(width_mm=80)` reproduces the Studio's 14,897 / 46
exactly. At 81 THE's E traces at 2.25 mm2 -- ON the 2.25 mm2 small-shape
floor (`min_detail_mm`^2), not rescued -- so T, H and E enter the text
tagger by the LETTER door together and form a 3-member cluster. At 80 the
E is 2.19 mm2, rescued, and goes through the RESCUED door (round 1), which
linked on size alone (`SIMILARITY_RATIO` 0.5, no colour): the black E
joined the tan 1895 (heights 2.62 / 1.66, strokes 0.39 / 0.21, 5.7 mm
apart, every term within 0.5), `restore_small_text` stripped it as a stray
(`small_text_keep_stray_lines` keeps stray LINES of 3+, not one letter),
and T + H alone could not reach `MIN_CLUSTER_MEMBERS` in round 2. T and H
went to the Column lane as crossing satin; the E to the run rescue.

**Fix: `cfg.text_cluster_rescued_ink_link` (ON), round 1 gets the one-ink
link (`_same_ink`, CIEDE2000 20) round 2 has had since 2026-09-03.** A link
can only be refused in round 1, so its partition only gets finer; a freed
letter goes to round 2 and may rejoin its line, so the FINAL partition can
be coarser -- the 3 mm tagline crop's EAT STAY PLAY went from lines of 6 + 3
(two letters held by the black separator bars) to one line of 11, and reads
STAY instead of ST^Y. Fremont 80 mm: 14,897 / 46 -> 14,812 / 43, THE three
bean letters, EST / 1895 / tagline shape-for-shape unchanged. 81 mm and the
92.5 mm patch byte-identical (`1541421f`, `6d132b3e`). Of the 17-design
corpus only the phone screenshot moves besides (8,511 / 63 -> 8,502 / 62):
five ignore-list icon pieces (Silver, dE 73 from the text's Black) leave the
text clusters, so the Column lane's own ink guard now refuses the icons
before the icon guard sees them; two `test_column_capture` censuses were
re-labelled to that, with the pre-flip reading kept as an explicit arm.

**Why:** the "two doors" trap named in [[lettering-architecture-2026-10-07]]
(failure E) bit at a one-millimetre change of size: a letter straddling the
rescue floor changes door, and the doors had different link rules. The 81 mm
cell everyone measured on could not show it.
**How to apply:** measure at the width the Studio SENDS (read it off the
panel's "Design width"), not the size the canvas shows; when a word breaks at
one size and not its neighbour, diff `text_cluster_id` / `rescued_small_shape`
/ `small_text_stray` across the two runs' region meta before touching any
tier. Session traps: the worktree Bash guard refuses `~`-paths and `$?`
(use the long AppData path and no exit echo); a `Get-CimInstance ... -match`
kill also matches its own shell; the built-in browser cannot upload a file
(Playwright MCP's `browser_file_upload` can, against the vite the preview
started on 5174). Related: [[small-text-true-size-guard-2026-10-15]],
[[hotel-fremont-pro-parity-findings]], [[run-the-app-color-cap-2026-09-07]].
