# The 80 mm ink link: Fremont's THE, and the text tagger's rescued round (2026-10-15)

Kent's 2026-10-15 Studio screenshot of Hotel Fremont on a Hat, design width 80 mm, with
EST, 1895, THE, the N of FREMONT and PLAY circled. Four of the five were already cured
on `main` (#922, #955) and his service predated them. The fifth, THE, was garbled at
80 mm and clean at 81 mm, the width every lane measurement had used. Thread renders of
EMB-Bot's own output (`digitizer_core.stitchviz` through `tools/fremont_triage`'s panel
helpers), not cloth. Nothing was sewn. Fremont is an UNREPRESENTATIVE fixture: it
reproduces the defect and sizes nothing.

## The mechanism

At 81 mm THE's E traces at 2.25 mm², on the 2.25 mm² small-shape floor, so it is not a
rescued small shape: T, H and E enter `detect_text_clusters` by the letter door together
and make a three-member cluster. At 80 mm the E is 2.19 mm², rescued, and enters by the
rescued door, whose round linked on size alone: the black E joined the tan 1895 (heights
2.62 / 1.66, strokes 0.39 / 0.21, 5.7 mm apart, every term within `SIMILARITY_RATIO`
0.5), `restore_small_text` stripped it as a stray, and T and H alone could not make
`MIN_CLUSTER_MEMBERS`. T and H went to the Column lane as crossing satin, the E to the
run rescue.

`cfg.text_cluster_rescued_ink_link` (ON) gives the rescued round the one-ink link
(`_same_ink`, CIEDE2000 20 on the job's chart) the letter round has had since 2026-09-03.

## Fremont, Hat, the Studio's request (`tools/fremont_triage.run_arm`)

| width | link OFF (today's main) | link ON | changed shapes |
|---|---|---|---|
| **80 mm (Kent's job)** | 14,897 st / 46 tr, `dd43ae1e` | **14,812 / 43**, `aed530f4` | 16 |
| 81 mm | 15,330 / 41, `1541421f` | 15,330 / 41, `1541421f` | 0 (byte-identical) |
| 92.5 mm | 18,675 / 54, `e0d9323c` | 18,675 / 54, `e0d9323c` | 0 (byte-identical) |

At 80 mm: `the80_the.png` (artwork | OFF | ON), `the80_full_pair.png` (whole design),
and `the80_est.png`, `the80_1895.png`, `the80_tagline.png`, whose shapes are unchanged
shape for shape (the 13 other changed shapes are the black block's re-routing round the
three new bean letters).

## The 17-design lettering corpus (`small_lettering_compare.corpus_designs`)

Round-1 clusters probed OFF vs ON on every design (stages 1-4 once, the tagger twice):
12 of 17 identical partitions. The five that differ, digitized to the plan OFF and ON:

| design | OFF | ON | changed shapes | what moved |
|---|---|---|---|---|
| fremont (92.5 mm patch) | 20,832 / 48, `6d132b3e` | identical | 0 | the tagline cluster drops its two black separator bars (restore stripped them anyway); EAT and STAY PLAY become two lines of 3 and 9, both restored |
| fremont_hat81 | 15,330 / 41, `1541421f` | identical | 0 | the bars leave the tagline cluster |
| fremont_hat925 | 18,675 / 54, `e0d9323c` | identical | 0 | as the patch |
| screenshot | 8,511 / 63, `be7d0d38` | 8,502 / 62, `a89b01ea` | 36 | five ignore-list icon pieces (Silver 0308, dE 73 from the text's Black; grey, dE 40) leave two text clusters; the Column lane's ink guard then refuses the icon-coloured house shapes before the icon guard sees them. Both labelled lines keep their clusters. `screenshot_pair.png` |
| sp_fremont_tagline_3 (3 mm caps) | 719 / 5, `4a197c3d` | 719 / 5, `04773460` | 10 | two rescued tan letters had been held in a cluster with the black bars, splitting EAT STAY PLAY into lines of 6 and 3; freed, round 2 reads one line of 11 and STAY reads STAY, not ST^Y. `sp_tagline3_pair.png` |

A link can only be refused in round 1, so that round's partition only gets finer; a
freed letter goes to round 2 and may rejoin its line, so the final partition can be
coarser (the 3 mm crop).

## Tests

`tests/test_textcluster.py`: the Fremont miniature both arms (a rescued glyph in another
ink is not a letter of the rescued word, and then clusters with its own ink's ordinary
glyphs), one-ink rows and one-step neighbours unchanged, the pipeline wire.
`tests/test_column_capture.py`: the screenshot censuses re-labelled (the ink link now
sees the status icons, none a labelled letter; the icon guard read on the pre-flip
clusters it was calibrated on, with a live arm).
