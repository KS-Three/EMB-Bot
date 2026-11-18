# Prime grader scorecard, 2026-11-18

A Claude session graded 9 designs by eye against the original artwork, under rubric 2026-11-17 (`96eff44f4baa`), on tree `2bae00d5`. Each figure is an instrument reading, not a quality claim (ROADMAP gate 4). The grader's repeat agreement with itself is not measured yet, so a one-step move on one night is not evidence by itself.

## Grades

| Great | Good | Okay | Bad | Terrible | mean step (0 = Great, 4 = Terrible) |
|---|---|---|---|---|---|
| 0 | 0 | 6 | 3 | 0 | 2.33 |

## Designs

| design | size | grade | computed yardstick | ruins | noticeable | nitpick | gross fault classes | whole-design |
|---|---|---|---|---|---|---|---|---|
| `L_becker_hat_large` | 102.1 x 65.0 mm on hat_front | Okay | A 100 | 0 | 5 | 7 | edge 1, missing 1, pen_flow 3 | detail_lost |
| `L_gaulke_roofing_hat` | 114.2 x 47.6 mm on hat_front | Okay | B 88 | 0 | 9 | 7 | edge 1, gap 2, letter 6 | detail_lost |
| `L_hotel_fremont_hat` | 93.3 x 50.6 mm on hat_front | Okay | B 88 | 0 | 7 | 6 | artefact 2, edge 1, letter 3, stitch_type 1 | detail_lost |
| `L_mfab_hat` | 105.3 x 40.5 mm on hat_front | Bad | B 76 | 1 | 17 | 3 | artefact 5, gap 1, letter 10, other 1, stitch_type 1 | detail_lost |
| `L_precision_drone` | 63.2 x 65.0 mm on hat_front | Bad | D 40 | 2 | 14 | 2 | artefact 3, colour 2, extra 1, gap 1, letter 4, missing 2, other 1, pen_flow 2 | detail_lost, too_busy |
| `L_tires_hat_3d` | 114.4 x 42.3 mm on hat_front | Okay | A 100 | 0 | 8 | 8 | artefact 1, edge 5, letter 1, stitch_type 1 | - |
| `L_goldentee_hat` | 75.4 x 62.9 mm on hat_front | Bad | F 0 | 1 | 7 | 3 | artefact 2, colour 1, edge 1, extra 1, letter 1, missing 1, pen_flow 1 | detail_lost, too_busy |
| `L_toat_machine_hat` | 90.6 x 64.7 mm on hat_front | Okay | D 46 | 0 | 11 | 9 | artefact 3, edge 1, letter 3, pen_flow 1, stitch_type 3 | detail_lost |
| `L_toat_beanie` | 83.4 x 56.1 mm on beanie | Okay | F 34 | 0 | 7 | 7 | artefact 2, edge 3, letter 1, pen_flow 1 | detail_lost |

## Gross faults by class (designs affected)

- **letter**: 8 of 9 (`L_gaulke_roofing_hat`, `L_goldentee_hat`, `L_hotel_fremont_hat`, `L_mfab_hat`, `L_precision_drone`, `L_tires_hat_3d`, `L_toat_beanie`, `L_toat_machine_hat`)
- **artefact**: 7 of 9 (`L_goldentee_hat`, `L_hotel_fremont_hat`, `L_mfab_hat`, `L_precision_drone`, `L_tires_hat_3d`, `L_toat_beanie`, `L_toat_machine_hat`)
- **edge**: 7 of 9 (`L_becker_hat_large`, `L_gaulke_roofing_hat`, `L_goldentee_hat`, `L_hotel_fremont_hat`, `L_tires_hat_3d`, `L_toat_beanie`, `L_toat_machine_hat`)
- **pen_flow**: 5 of 9 (`L_becker_hat_large`, `L_goldentee_hat`, `L_precision_drone`, `L_toat_beanie`, `L_toat_machine_hat`)
- **stitch_type**: 4 of 9 (`L_hotel_fremont_hat`, `L_mfab_hat`, `L_tires_hat_3d`, `L_toat_machine_hat`)
- **gap**: 3 of 9 (`L_gaulke_roofing_hat`, `L_mfab_hat`, `L_precision_drone`)
- **missing**: 3 of 9 (`L_becker_hat_large`, `L_goldentee_hat`, `L_precision_drone`)
- **colour**: 2 of 9 (`L_goldentee_hat`, `L_precision_drone`)
- **extra**: 2 of 9 (`L_goldentee_hat`, `L_precision_drone`)
- **other**: 2 of 9 (`L_mfab_hat`, `L_precision_drone`)

## Since the last scorecard

Against 2026-11-17 (tree `3608ef63`):
- `L_becker_hat_large`: still Okay; gained edge, missing; cleared artefact, letter
- `L_gaulke_roofing_hat`: still Okay; gained gap; cleared extra, missing
- `L_hotel_fremont_hat`: still Okay; gained artefact
- `L_mfab_hat`: Okay -> Bad; gained other, stitch_type; cleared edge
- `L_precision_drone`: still Bad; gained other
- `L_tires_hat_3d`: still Okay; gained stitch_type
- `L_goldentee_hat`: still Bad; gained missing; cleared gap
- `L_toat_machine_hat`: still Okay; gained stitch_type; cleared other

## Why each grade

- `L_becker_hat_large` (Okay): The MARINE lettering is sewn with fan-shaped, radiating stitch angles in the R, N and E and the A counter is filled in, which a customer would see straight away. BECKER is recognisable with a clean outline, but the C counter ring is lumpy and the outline bands are rough in places. Long needle-up travels cross the lettering.
- `L_gaulke_roofing_hat` (Okay): The logo is recognisably right and the lettering reads, but the fine detail is lost: the white gaps between the sun and roof bands have closed or become ragged, and counters in the lettering are choked. Every edge is scalloped rather than clean, and letter strokes are fattened against the original. It needs a clean-up before it ships.
- `L_hotel_fremont_hat` (Okay): The small tan lettering (EST 1895, EAT STAY PLAY) is sewn as lumpy blobby strokes with wrong letter forms, which is what most holds it back. The big black HOTEL FREMONT, the Wisconsin shape and the layout are recognisably right, but the rope border is a plain zigzag and the dividers are wrong. Needs a clean-up on the small text and dividers.
- `L_mfab_hat` (Bad): The small AND WELDING LLC line is mushed: thread outlines are thin and ragged, black fill ovals pile over the letter edges, and the LLC and the A/N counters are hard to read. The big M-FAB top half is recognisable and mostly clean, but the inner F and B details are blobby or misshaped and several junctions pile up. A customer would see the bottom line as a different, worse logo than the art.
- `L_precision_drone` (Bad): The drone, which is the focal point, is lost: the body, camera and arms are a mush of black and grey fragments, and the split-scope scene is a vague blob with a black background sewn over it. The wordmark is readable but PRECISION and THERMAL have lumpy, misdirected fills and AND DRONE is weak. Travel is chaotic with long jumps across the whole design.
- `L_tires_hat_3d` (Okay): The word reads clearly as Tires and every stroke, the i dot and the open e and s counters are present. What holds it back is the scalloped, saw-toothed edge along nearly every stroke, plus the messy e crossing and the pinched s counter. A customer would see the rough edges and a clean-up would be needed.
- `L_goldentee_hat` (Bad): The GOLF wordmark is mushed: black outline stitches pile over the yellow/orange fills so the O counter and the L and F are barely readable, and a grey shadow fringe is sewn under it that the art only has as a soft blur. The GT block and tee are recognisable but the bevel colours are blocky and the travel moves are long and tangled across the face. The TM is missing.
- `L_toat_machine_hat` (Okay): The badge, border and the script word Machine are recognisably right, but the thin tapering speed lines are sewn as fat uniform bars and the script strokes carry lumps, pile-ups and crossover stitches where letters join. The A of To A T and the C of LLC are visibly misshapen, so it needs a clean-up before shipping.
- `L_toat_beanie` (Okay): The Machine script is recognisable but its strokes are lumpy and the c, h and i are tangled with piled stitches and direction changes mid-stroke. The To A T lettering, frame and LLC read cleanly, though the speed lines are blobby and several lose their taper. Needs a clean-up on the script before it ships.

## Every fault

**`L_becker_hat_large`**
- (48.5, 52.0) mm, direction, noticeable, seen in C2: The R of MARINE fans its stitches out from one point across the bowl instead of following the stroke, unlike the straight columns in the original.
- (90.0, 56.0) mm, direction, noticeable, seen in C3: The E of MARINE has stitches radiating from a point at its spine, so the arms and spine run in conflicting directions.
- (72.0, 54.0) mm, direction, noticeable, seen in C3: The N diagonal meets the left upright with a starburst of stitch angles and a visible seam, rather than a clean join.
- (27.0, 54.0) mm, missing, noticeable, seen in C1: The triangular counter of the A is filled with thread, so the A reads as a solid block, against the open hole in the original.
- (27.0, 61.0) mm, direction, nitpick, seen in C1: The A crossbar is a slanted patch of stitches that clashes with the vertical columns around it.
- (13.0, 55.0) mm, direction, nitpick, seen in C1: The V notch of the M is sewn with stitches at diagonal angles that differ from the upright columns, leaving visible seams.
- (43.0, 13.0) mm, lumpy_curve, noticeable, seen in A2: The C counter is a ring of outline with a fill of mixed angles and a lumpy notch at its top, not the clean smooth solid shape in the original.
- (57.0, 8.0) mm, letter_shape, nitpick, seen in A2: The dark slash between the C and K is a thin, uneven bar and is narrower than the original.
- (10.0, 38.0) mm, jagged, nitpick, seen in B1: The outer border stitches around the lower left of the B fan irregularly at the corner and show ragged ends (this repeats around the border).
- (90.0, 38.0) mm, jagged, nitpick, seen in B3: The border on the right R is saw-toothed on its outer edge with uneven stitch ends.
- (14.0, 31.0) mm, mushed, nitpick, seen in B1: The B counter fill has radiating stitch angles that look messy, and its outline is a little lumpy.
- (60.0, 40.0) mm, stray, nitpick, seen in travel: Long needle-up moves run across the BECKER and from BECKER to MARINE, so they need trimming or they leave loose threads on the face.

**`L_gaulke_roofing_hat`**
- (45.0, 14.0) mm, gap, noticeable, seen in A2: The white sliver between the sun disc and the top roof band is ragged and partly closed, where the original has a clean even white stripe.
- (62.0, 14.5) mm, mushed, noticeable, seen in A3: The roof peak and its inner stripes near the apex fuse into one black mass, losing the separate chevron lines and the small triangle seen in the original.
- (60.0, 20.0) mm, gap, noticeable, seen in A3: The thin white gaps between the parallel roof bands are choked, uneven and broken into dashes.
- (57.0, 24.5) mm, letter_shape, noticeable, seen in B2: The window panes are barely separated: the white mullions of the four-pane window are mostly filled in.
- (35.0, 24.0) mm, jagged, nitpick, seen in A2: The upper roof wing edge is scalloped with small steps; this repeats along every roof band.
- (38.0, 28.5) mm, gap, nitpick, seen in B2: The white line between the lower two roof wings is thin and uneven compared with the original.
- (19.5, 35.5) mm, letter_shape, noticeable, seen in B1: The G is fattened and its crossbar blob nearly fills the counter, so the opening of the G is much smaller than in the original.
- (10.0, 35.0) mm, jagged, noticeable, seen in B1: The C has a heavily scalloped rim and thickened terminals; this scalloping repeats on every round letter.
- (6.0, 44.0) mm, letter_shape, noticeable, seen in B1: The S of STEEL is lumpy with a fat spine and uneven terminals.
- (98.0, 35.5) mm, mushed, noticeable, seen in B4: The counter of the R and the tongue of the E are nearly closed, and the arm of the E is a squeezed slit.
- (104.0, 37.0) mm, stray, nitpick, seen in B4: The S of INDUSTRIES has a small notch and a sharp crack in its lower curve.
- (74.0, 44.0) mm, mushed, noticeable, seen in B3: The ampersand is clogged: its small upper counter and the lower openings are mostly filled.
- (104.0, 44.0) mm, mushed, nitpick, seen in B4: The counters in P and P of SUPPLY are small, though still open; they repeat on the other letters of the line.
- (68.0, 36.5) mm, pen_flow, nitpick, seen in B3: The bowl of the U in INDUSTRIES shows a hard seam in the curve where fill direction changes.
- (45.0, 44.0) mm, jagged, nitpick, seen in B2: The O's of ROOFING have saw-toothed outer and inner edges; this repeats across both lines.
- (100.0, 6.0) mm, other, nitpick, seen in travel: The travel shows two very long needle-up jumps across the logo and the letters; they would need trims.

**`L_goldentee_hat`**
- (42.0, 41.0) mm, mushed, ruins, seen in B2: The GOLF letters O, L and F are buried under heavy black outline blobs and overlapping fills so the word is hard to read.
- (57.0, 41.0) mm, blob, noticeable, seen in B3: The F of GOLF has black blocks and jumbled fill directions where the arms should be clean bars.
- (35.0, 47.0) mm, extra, noticeable, seen in B2: A grey-white fringe of stitches is sewn under GOLF for the soft drop shadow, which reads as a fuzzy halo rather than art.
- (68.0, 40.0) mm, missing, noticeable, seen in B3: The TM mark to the right of the F is not sewn.
- (28.0, 24.0) mm, colour, noticeable, seen in A2: The G bevel is a thick red-brown satin with patches of yellow and white, where the art has a thin red line with a gold-to-cream gradient.
- (10.0, 18.0) mm, jagged, noticeable, seen in A1: The black outer edge of the swoosh is bumpy and scalloped, and the white fill is a thin stitch-end ladder; this repeats along the arc.
- (4.0, 27.0) mm, other, nitpick, seen in A1: The swoosh tail point is doubled with a white fringe beside the black tip and is wider than the art's fine point.
- (10.0, 37.0) mm, direction, noticeable, seen in B1: The tee neck has overlapping stitch angles and a ragged jumble where the top bar turns into the stem.
- (20.0, 35.0) mm, letter_shape, nitpick, seen in B1: The tee top-bar tip is a stubby curl against the art's sharp barb.
- (60.0, 21.0) mm, stitch_type, nitpick, seen in A3: The T bevel lines are blocky, with the cream band as a separate white bead row and a red block corner that is not in the art.
- (40.0, 32.0) mm, stray, noticeable, seen in travel: Many long needle-up jumps cross the face of GT and GOLF between seven colour blocks, which would need trimming and risk visible tack-downs.

**`L_hotel_fremont_hat`**
- (40.0, 13.0) mm, mushed, noticeable, seen in A2: EST is sewn as fat bumpy tubes with the S and T barely readable against the clean slab serif letters of the original.
- (57.0, 13.0) mm, letter_shape, noticeable, seen in A2: The 1895 digits are distorted, the 8 and 9 are lumpy with blobby loops and the 1 has lost its flag and serif.
- (47.5, 11.0) mm, letter_shape, nitpick, seen in A2: The white star in the Wisconsin shape is sewn as a fat asterisk and sits low and off-centre.
- (50.0, 36.0) mm, letter_shape, noticeable, seen in B2: STAY and PLAY are built from tube-like strokes: the Y and A read as lambda shapes and the serifs are gone, and the same repeats across EAT.
- (40.0, 37.0) mm, blob, noticeable, seen in B2: The two vertical dividers in EAT | STAY | PLAY are sewn about twice as thick and taller than the thin bars in the art and crowd the letters beside them; the second one repeats this near x 53.
- (30.0, 10.0) mm, stitch_type, noticeable, seen in A1: The twisted rope border is replaced by a plain zigzag satin band with no twist, and it repeats along every rope segment.
- (47.0, 47.0) mm, jagged, noticeable, seen in B2: At the bottom point the rope and black border meet in a ragged pile-up with stitches that fold over each other instead of a clean mitre.
- (18.0, 15.0) mm, blob, nitpick, seen in A1: The rope end near the top-left corner is a tangled lump of stitches that does not match the neat rope end in the art.
- (75.0, 35.0) mm, stray, noticeable, seen in B3: The rope end at the right shoulder is a messy fold of stitches with loose stitch ends, and the Y of PLAY pokes past the border beside it.
- (47.0, 3.0) mm, other, nitpick, seen in A2: The black border has a visible seam at the apex and the rope pieces meet there with a gap.
- (20.0, 23.0) mm, lumpy_curve, nitpick, seen in A1: The edges of the HOTEL FREMONT letters are scalloped and bumpy where the art has crisp straight stems and curves, and this repeats across all letters; the slab serifs are rounded off.
- (35.0, 18.0) mm, other, nitpick, seen in A2: The black rule bars have visible butt joints where separate satin runs meet, and the bars are thicker than in the art.
- (45.0, 30.0) mm, stray, nitpick, seen in travel: Long needle-up travel runs cross the open design and a trim/jump from the tagline to the top is not hidden.

**`L_mfab_hat`**
- (16.0, 18.5) mm, letter_shape, noticeable, seen in A1: The small crown/V notch under the M centre is distorted, with a lump on the left arm and a pile-up at the base, unlike the clean wedge in the art.
- (16.0, 10.0) mm, blob, nitpick, seen in A1: The M's centre V point has crossing stitches piled where the two diagonals meet.
- (35.0, 6.0) mm, blob, nitpick, seen in A2: The upper junction of the first upright with the F top bar has stitches fanning and piling.
- (45.0, 12.5) mm, blob, noticeable, seen in A2: The F diagonal meets its horizontal arm with overlapping, doubled stitch blocks and a stepped joint that the art does not have.
- (36.0, 17.0) mm, stray, noticeable, seen in A2: A stray diagonal run and uneven stitch columns sit across the small counter of the H-like bar of the dash/F junction.
- (70.0, 16.0) mm, stitch_type, noticeable, seen in A3: The small triangle of the A is filled with crowded, ragged slanted stitches with a rough upper edge, unlike the clean triangle in the art.
- (91.0, 11.5) mm, letter_shape, noticeable, seen in A4: The B's upper slot is a short lumpy sausage that is too narrow and rounded compared with the angular parallelogram in the art.
- (89.0, 18.5) mm, letter_shape, noticeable, seen in A4: The B's lower slot has a lumpy messy left end and a shorter right end, and is not the clean angled bar of the art.
- (100.0, 14.5) mm, jagged, nitpick, seen in A4: The B's right outline kinks and bulges around the notch instead of running as a clean line.
- (18.0, 28.0) mm, mushed, noticeable, seen in B1: The A and N of AND have thread outlines so thin and broken that black fill balls cover the letter edges and the A counter nearly closes; this repeats across the small lettering.
- (15.0, 21.5) mm, blob, noticeable, seen in B1: Black fill pile sits at the base of the M notch and runs into the top of the N.
- (28.0, 28.0) mm, gap, noticeable, seen in B1: The D counter is filled with diagonal fabric-coloured thread showing a ragged edge instead of a clean small triangle.
- (35.0, 28.0) mm, mushed, noticeable, seen in B2: The W of WELDING has a double-line, saw-edged diagonal and black blobs covering strokes so its zigzag is hard to follow.
- (45.0, 28.0) mm, mushed, noticeable, seen in B2: The E has thin uneven thread lines and its arms are not distinct, with black overflow in the stem.
- (63.0, 23.5) mm, blob, noticeable, seen in B3: The top bar over the D and I has a messy knot of fanning stitches at its corner.
- (68.0, 28.0) mm, mushed, noticeable, seen in B3: The I and N strokes merge with broken outlines and black overlaps so the letters run together.
- (73.0, 31.0) mm, letter_shape, noticeable, seen in B3: The G is hard to read, with black fill covering its inner arm and ragged outline on its descending tail.
- (87.0, 28.0) mm, mushed, ruins, seen in B4: The two L letters of LLC are tangled with fanning crossed stitches and no clear thin inner lines, so they read as one smudge.
- (90.0, 24.5) mm, stray, noticeable, seen in B4: A long thin straight run crosses along the top of the L and C letters, not in the art.
- (98.0, 28.0) mm, letter_shape, noticeable, seen in B4: The C's upper right end and counter are lumpy with a distorted opening compared with the art.
- (50.0, 25.0) mm, other, noticeable, seen in travel: Long needle-up jumps (about 40 to 100 mm) cross the face of the design between the letters and will need trimming or leave loose threads.

**`L_precision_drone`**
- (20.0, 12.0) mm, missing, ruins, seen in overview: The drone body, camera housing and arms are not recognisable; they are broken into disconnected grey and black patches.
- (30.0, 22.0) mm, missing, ruins, seen in A1: The orange thermal camera lens and dark lens are reduced to a small orange scribble and the lens is not readable.
- (18.0, 28.0) mm, other, noticeable, seen in B1: The grey forest and lake on the left half are a flat grey blob with no trees or shoreline, against the original's pines.
- (8.0, 10.0) mm, extra, noticeable, seen in A1: Black background is sewn behind the ring where the art has cream and the ring outline loses its silver bezel, so the shape bulges beyond the art.
- (20.0, 14.0) mm, direction, noticeable, seen in A1: The left propellers are sewn as thick black wedges with stitches across the blade and are wider than the thin blades in the original.
- (50.0, 12.0) mm, letter_shape, noticeable, seen in A2: The right propeller blades are thick dark blobs fused with the arm and no longer read as blades; this repeats on the lower right propeller.
- (43.0, 28.0) mm, colour, noticeable, seen in B2: Orange forest is a solid wedge with spiky bar tips and sky blue is replaced by black, with a stray blue dot at 43,27 in the orange.
- (35.0, 36.0) mm, stray, noticeable, seen in B2: The crosshair reticle is broken into white lumps and the circle is a tangle of fragments, not a clean ring.
- (38.0, 37.0) mm, gap, noticeable, seen in B2: Water is a few blue bars with black gaps between them instead of a continuous reflection.
- (12.0, 40.0) mm, lumpy_curve, nitpick, seen in B1: The silver bezel on the lower left is chopped into sections of different grey and white with visible breaks.
- (5.0, 46.0) mm, pen_flow, noticeable, seen in C1: The P and R of PRECISION have stitches that swirl and cross in the bowls and the R leg, against clean block letters; this repeats across the word.
- (46.0, 47.0) mm, mushed, noticeable, seen in C2: The O and N of PRECISION have tangled direction changes, the O counter is cramped, and the S is lumpy.
- (18.0, 53.0) mm, letter_shape, noticeable, seen in C1: The T, H and E of THERMAL have overlapping fills and pile-ups where letters touch, with a darker orange crossover on the E.
- (42.0, 53.0) mm, blob, noticeable, seen in C2: The R, M and A of THERMAL are lumpy with overlapping fills and the A counter is almost closed.
- (18.0, 58.0) mm, colour, noticeable, seen in C1: The A of AND is sewn in near black, unlike the mid grey of the rest of the line, and its shape is a blob.
- (40.0, 58.0) mm, letter_shape, noticeable, seen in C2: AND DRONE letters at this size are rings of swirling stitches; the R and O are poorly formed and the E is sketchy.
- (31.0, 63.0) mm, blob, noticeable, seen in C1: The orange target icon is a solid lump with its rings and centre dot lost.
- (32.0, 30.0) mm, stray, nitpick, seen in travel: The travel plan makes dozens of long needle-up jumps across the whole design, which means many trims or loose threads on the hat.

**`L_tires_hat_3d`**
- (10.0, 10.0) mm, jagged, noticeable, seen in A1: The inner edge of the T crossbar curl is saw-toothed with visible gaps between stitch ends, where the original edge is smooth.
- (14.0, 14.5) mm, jagged, noticeable, seen in A1: The lower inner edge of the T curl shows comb-like stitch ends, and the terminal tip is cut off square instead of round.
- (63.0, 2.0) mm, jagged, noticeable, seen in A3: The upper edge and tip of the crossbar's right end are comb-toothed and the tip is squared off rather than rounded.
- (102.5, 19.0) mm, jagged, noticeable, seen in A4: The top of the s stem has fanned, spiky stitch ends on its left shoulder instead of a smooth curve; the edge scallop repeats along the whole s.
- (78.0, 19.0) mm, jagged, nitpick, seen in A3: The top of the e bowl has fanned stitch ends along its outer edge, where the original is smooth.
- (22.5, 37.0) mm, letter_shape, nitpick, seen in B1: The start of the r/i stroke has a flat angled cut end rather than the rounded terminal in the original.
- (12.0, 36.0) mm, gap, nitpick, seen in B1: Small slits show between stitch blocks on the T stem's lower outer edge, which sits wavy.
- (40.0, 35.0) mm, gap, nitpick, seen in B2: Narrow slits open in the inner bottom of the i/r curve where stitch fans meet.
- (33.0, 30.0) mm, gap, nitpick, seen in B2: Thin white slits cut across the diagonal i stroke where segments join.
- (72.5, 31.0) mm, blob, noticeable, seen in B3: The r to e junction is a lumpy pile-up with a hard rectangular step and ragged seams where the strokes cross, not the smooth crossing in the original.
- (76.5, 28.5) mm, stitch_type, noticeable, seen in B3: The e counter pinches down to a small sliver and its lower left corner is jagged, so it is smaller than in the original.
- (60.0, 34.5) mm, jagged, nitpick, seen in B3: The r bowl inner bottom has a hard flat step in the edge, and the heavy fan teeth along the bottom edge of r and e repeat across the baseline.
- (102.0, 28.0) mm, letter_shape, noticeable, seen in B4: The s counter right wall is a straight, ruler-flat edge with a notch at the top, where the original curves, and the counter is narrower.
- (96.0, 36.0) mm, jagged, noticeable, seen in B4: The s lower left has a blocky square-cornered step where strokes meet, and the bottom edge is heavily fanned and scalloped.
- (110.0, 31.0) mm, letter_shape, nitpick, seen in B4: The s exit stroke ends with a flat angled cut and a ragged outline rather than a rounded terminal.
- (10.0, 25.0) mm, stray, nitpick, seen in travel: Long needle-up jump across the T from the curl end down to the stem foot (a trim risk, though hidden under later stitching).

**`L_toat_beanie`**
- (43.0, 33.0) mm, mushed, noticeable, seen in B2: The c and h of Machine are a tangle of overlapping stitch angles, so the letter shapes and the join between them are hard to read.
- (37.0, 31.0) mm, pen_flow, noticeable, seen in B2: The a bowl changes stitch direction abruptly inside the stroke instead of following the pen path.
- (67.0, 32.0) mm, blob, noticeable, seen in B3: The e of Machine has a pile-up of crossing stitches at its crossbar and left side.
- (19.0, 23.0) mm, blob, noticeable, seen in A1: The second stem of the M has a small crossover stitch cluster where two stroke pieces meet.
- (11.0, 38.0) mm, lumpy_curve, noticeable, seen in B1: The bottoms of the M strokes are lumpy and stepped rather than a smooth curve (repeats along the M).
- (23.0, 30.0) mm, stray, nitpick, seen in B1: The small isolated tick above the M's right loop has a stub and is not in the art as drawn.
- (8.0, 16.0) mm, wavy, noticeable, seen in A1: The M's left uprights show uneven edges and ragged stitch ends compared with the clean straight originals.
- (30.0, 41.5) mm, wavy, noticeable, seen in B2: The top lower speed line varies in thickness along its length, bulging and pinching where the original tapers evenly.
- (18.0, 42.0) mm, jagged, nitpick, seen in B1: The left end of the lower speed line stutters into beads, and the line below ends in a spike (repeats on the neighbouring lines).
- (80.0, 39.5) mm, stray, nitpick, seen in B3: The right speed line next to LLC ends in an arrowhead barb that is not in the art.
- (63.0, 44.5) mm, other, nitpick, seen in B3: The period after LLC is a tiny blob that reads as a smudge.
- (13.0, 13.0) mm, stitch_type, nitpick, seen in A1: The thin upper speed lines are sewn as thick satin bars and lose the tapered thin look of the original (repeats on the right).
- (41.0, 13.0) mm, letter_shape, nitpick, seen in A2: The A is smaller and rounder than the original and its crossbar is crowded, so it is slightly squashed.
- (20.0, 20.0) mm, other, nitpick, seen in travel: Long needle-up jumps cross the design between the script, the top lettering and the bottom lines, leaving many trims to clean.

**`L_toat_machine_hat`**
- (20.0, 14.5) mm, stitch_type, noticeable, seen in A1: The thin tapering speed lines left of the T are sewn as thick uniform satin bars instead of fine tapered strokes; this repeats on every speed line.
- (70.0, 16.0) mm, stitch_type, noticeable, seen in A3: The three speed lines right of the second T are fat blunt bars rather than thin lines that taper to a point; the same is true under Machine.
- (42.0, 48.5) mm, stitch_type, noticeable, seen in C2: The three long lines left of LLC are far heavier than the hairline originals, and the ends are blunt with small stubs at about x=54.
- (47.5, 18.0) mm, letter_shape, noticeable, seen in A2: The A in To A T is a lumpy block whose crossbar and counter have filled in, and its apex is square with a ragged leg bottom, unlike the clean triangle of the original.
- (38.5, 14.5) mm, letter_shape, nitpick, seen in A2: The counter of the small o is narrower and rounder than the squared original counter, and the stitches fan radially around it.
- (9.5, 22.5) mm, stray, noticeable, seen in B1: A short crossover stitch pokes out where the M's thin first upstroke joins the thick stem.
- (19.5, 23.5) mm, stray, noticeable, seen in B1: Crossover stitches sit at the top of the M's second thin upstroke where it meets the thick stem.
- (10.5, 31.0) mm, jagged, nitpick, seen in B1: The M's thick left stem has a stepped edge and a visible seam where one satin section ends and the next starts, instead of one smooth stroke.
- (12.5, 41.5) mm, lumpy_curve, nitpick, seen in B1: The foot of the M's thick stem and the join into the thin stroke are lumpy with overlapping stitch bands.
- (40.0, 33.5) mm, blob, noticeable, seen in B2: The terminal of the c is a pile of short overlapping stitches with a stub, not the clean pointed hook of the original.
- (50.0, 36.0) mm, lumpy_curve, noticeable, seen in B2: The h arch joins the stem in a lumpy mass with direction changes and a visible seam, and the arch looks wider and rounder than the original.
- (47.5, 43.0) mm, mushed, nitpick, seen in B2: The bottom of the c and h curves fan out in a radial pinch where stitch direction swings sharply; the same is repeated at the bottoms of i, n and e.
- (63.5, 35.5) mm, mushed, noticeable, seen in B3: The i and n merge into a pile of crossing stitch blocks and the i dot is joined to the body, so the two letters are hard to separate.
- (68.0, 41.0) mm, blob, nitpick, seen in B3: The base of the n curls into a tight radial fan with pinched stitching.
- (76.0, 37.5) mm, pen_flow, noticeable, seen in B3: Where the e crosses its own stroke the stitches are stacked and criss-crossed with direction changes mid-stroke, rather than following the pen.
- (68.0, 47.0) mm, letter_shape, noticeable, seen in C3: The C of LLC is broken into several stitch blocks with a notch at the top terminal and a ragged lower hook, and is crowded against the L.
- (71.5, 51.0) mm, extra, nitpick, seen in C3: The period after LLC is a small block that reads as a stitched square, and the dash left of the lines has a stray nub at x=71.
- (57.0, 50.0) mm, letter_shape, nitpick, seen in C2: The first L of LLC has a seam at the corner where its foot joins the upright, and the top is slanted off.
- (1.5, 16.5) mm, jagged, nitpick, seen in A1: The top-left border corner is a rounded, broken join with an overlapping stitch pile rather than a sharp mitre.
- (45.0, 30.0) mm, other, nitpick, seen in travel: Long needle-up jumps cross the open art between the letters and the speed lines, many in a single colour block, which means many trims and a poor sew order.
