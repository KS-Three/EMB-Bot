# The baseline was sound, and a shallow clone said otherwise — 2026-09-02

## The expensive mistake, first

I published a claim that the scorecard baseline was **incoherent** and needed
recapturing. It was wrong, and the cause was mechanical: a cloud session clones
**shallow**, and `git log -1 -- <path>` on a shallow clone returns the **graft
root** as the last author of every file — wearing that commit's own real
subject line, hash and date. Three independent checks (`git log --all`, a
`ls-tree` sweep over `rev-list --all`, a filesystem `find`) all corroborated one
stale snapshot, which is exactly the failure CLAUDE.md item 8 describes.

`git fetch --unshallow` took the clone from **219 to 1390 commits** and put the
real capture at **`4f7d80f3` (2026-08-12)** — **206 merges** before the date I
had reported. Re-scored on that commit: **38 of 38 rows agree.** The baseline
was never incoherent. Retracted in-chat and in
`docs/scorecard-baseline-attribution-2026-09-02.md`.

**Check `git rev-parse --is-shallow-repository` before attributing anything to
a commit.** Now in DOCTRINE gotchas.

Two smaller retractions in the same lane: the missing `captured_at_commit`
stamp is not a defect (`capture()` at `4f7d80f3` had no such field), and a
`satin_steps` bisect that used a hand-rolled proxy metric (read 1448 where
preflight read 1416) never matched on equality, collapsed, and named a commit
confidently — re-run with **preflight's own metric** it lands on `070a1136`.

## Every flagged mover is attributed

`2d58da8` (yardstick, moves both directions), `d2184fa2` (summit_badge — a fix),
`b37cd808` (ramps), `da7fc806` (drone), `070a1136` (satin_steps), the preflight
link-instrument defect (link_segments), `d3f3c547` (density). The photo lane
reproduces **bit-for-bit on Linux**, so cloud captures are comparable to Kent's
box. Also: the duplicate-fixture "discovery" was not mine — `blockcensus.py`
documented it 2026-08-23 with a runtime md5 check; credit corrected.

## Gate 3 and the density bill

Tonal-region splitting sits OUTSIDE gate 3 — Kent's spec decision 2, shipped in
`d3f3c547`, re-confirmed **deliberate** 2026-09-02 when I flagged the
discrepancy. The docs were what was wrong, not the code. But its **density cost
is real and now tracked as defect 20**: `photo_scene_stub` `coverage_max`
4.40 → 6.44 → **7.18** against a 3.5-layer ceiling, `same_hole_fraction` up
4–7x (the needle-breakage signal).

`effective_split_tonal` also had **no off switch** — it ORed the flag with the
class, so the config could only ever turn the tier ON. Now tri-state
(`None` = never called). The test guarding it was named
`test_explicit_flag_still_wins_everywhere` and asserted **one direction only**.

**The benefit half is still unmeasurable.** Cost is known (fires on 4 of 8 photo
fixtures, +2,331 to +3,249 stitches); `artfidelity_self` refuses all 8 photo
rows with `ink mask saturates the frame`, so nothing can score the gain. Needs a
photo-capable fidelity instrument first.

## Studio UI (PR #317) and quality audit 8/10/3 (PR #318)

Shipped: the picked hoop is actually **drawn** (`hoopTransform` returns the
placement box AND the real hoop, fits to the larger) and gates stitch exports
that will not fit; the shape list moved behind an "Edit shapes (N)" disclosure;
a re-digitize shows a **before/after delta** against `priorRun`; three preflight
findings render as **one-click adjustment chips offered after the run** (Kent's
call — an adjustment, not a pre-run form); `QualityReport` surfaces trims.

**Two live consequences worth remembering.** The stock **Tote / Full Back preset
is 203.2 mm against a 200 mm max hoop**, so the new confirm fires on shipped
artwork — whether auto-fit should cap at the hoop is open and has NOT been put
to Kent. And `cfg.border` **could never reach its own default**: `project.js`
seeded `"off"` and `digitizer.js` sent the key unconditionally, so no user had
ever seen the engine's own border behaviour. Sentinel now `null`.

**The cone merge did NOT ship, on purpose.** Folding layer *palette slots* is
the wrong population — palette (16 on `drone_render`) is not the region cone
list (19), blocks key on region `thread_index`, and folding discards
`rehome_resnapped_regions`' re-snap. It ran, found nothing, reported success.
Reverted; `tools/cone_merge_survey.py` and `threads.delta_e` are what survived.
**Kent has since TABLED the colour question entirely** (MASTER_SCOPE queue 12) —
do not build the shade-merge until he reopens it.

## Left open, nobody's assigned

UI audit 4 (mobile empty canvas) and 9 (shape-list a11y); quality audit 9
(edge_cap fragmentation guard — Kent passed on it); quality audit 5
(`chain_links`, a gate 1 refusal); the Tote hoop-ceiling call; tonal splitting's
benefit, blocked on the instrument.
