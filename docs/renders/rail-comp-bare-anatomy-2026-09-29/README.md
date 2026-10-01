# What `satin_rail_comp`'s bare artwork actually is — ENTHUSIAST's A, 2026-09-29

Kent's pick after the flip landed: isolate the two costs of `cfg.satin_rail_comp`
that had no cause in the record. This is the ENTHUSIAST half.

`docs/kent-review-2026-09-28.md` recorded the cost as bare artwork **6.27 →
7.10%**, with the rise *"along the rails (mid-rail 2.06 → 4.12%), cause not yet
isolated"*. The framing was wrong, and one picture is why.

## The pair

| | |
|---|---|
| [`enthusiast_off_Scd87e08f.png`](enthusiast_off_Scd87e08f.png) | `satin_rail_comp=False` — the pull in the polygon |
| [`enthusiast_on_Scd87e08f.png`](enthusiast_on_Scd87e08f.png) | shipped default — the pull on the rails |

Drawn by `tools/bare_anatomy.py --render` at 40 px/mm. Artwork pale grey, sewn
crosses blue at the coverage model's own 0.4 mm thread width, **amber** where
bare artwork sits at a run's terminal cross (an `end` gap), **red** where it
sits along the rails (a `side` gap).

## What the pair shows

**The apex of the A is unsewn.** Off the rails the column reaches within
**0.08 mm** of the artwork's top; on them it stops **1.63 mm** short, and no
penetration lands within 1.5 mm of the apex at all (20 within 3 mm off, 13 on).
That leaves one **3.61 mm² triangle at 0.71 mm half-width** — the largest bare
component anywhere on the fixture, against a worst of 1.18 mm² @ 0.26 mm off
the rails.

**Nothing reports it.** `preflight`'s `ARTWORK_UNCOVERED` counts patches at or
over `_UNCOVERED_MIN_PATCH_MM2` = 5.0 mm², so 3.61 sits under the floor. (The
two measures are not the same geometry — preflight works on a grid, this on a
shapely difference — so read the comparison as "near the floor", not as an
exact 1.39 mm² of headroom.)

**And the "mid-rail" half is not a defect at all.** The red is hairlines: 80%
of the side area sits in components under 0.10 mm half-width, and the worst
side component is *smaller* on the rails than off them (0.45 against 0.50 mm²).
The same-rail step distribution barely moves (p50 0.427 → 0.419 mm; share over
0.45 mm 35.1 → 33.6%; summed overshoot past the 0.4 mm pitch 88.2 → 71.5 mm).
A 0.4 mm thread at the 0.4 mm pitch just touches, so every rail step over the
pitch leaves a sliver the model counts as bare — rail comp makes **more of
them, each thinner**, which raises the percentage while improving the worst
case.

**That is the trap worth keeping:** one percentage moved by two populations at
once, in opposite directions, and the number alone cannot say which. Read
`bare_anatomy`'s thickness column before reading its total.

## Reproducing

    cd digitizer
    .venv/bin/python tools/bare_anatomy.py enthusiast          # the table
    .venv/bin/python tools/bare_anatomy.py enthusiast \
        --shape Scd87e08f --render ../docs/renders/rail-comp-bare-anatomy-2026-09-29

The shape id is stable for this fixture at 80 mm / `left_chest` but is
generated, so re-read it off the `worst:` line rather than trusting it. The
numbers are pinned in
`tests/test_rail_comp.py::test_the_flips_bare_artwork_is_hairlines_on_the_sides_and_a_hole_at_a_tapered_end`,
as ceilings — closing the apex lowers them and leaves the test green.
