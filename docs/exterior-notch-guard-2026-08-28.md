# The exterior-notch guard: built, measured, NOT shipped

**Status: prototyped and costed. Kent's call 2026-08-28 — hold it.**
The patch is `docs/prototypes/exterior-notch-guard-2026-08-28.patch` and applies
cleanly to `930cff9`. Nothing in `digitizer/` was changed on `main`.

## The defect it fixes

`stage5_overlap.py` holds a feature open when pull compensation would shrink it
below the sewable floor — but only when that feature is an **interior ring**:

```python
for ring in poly.interiors:
```

An `O`'s counter is protected. An `E`'s arm slots and an `N`'s crotch are
notches in the **exterior** boundary, so `poly.interiors` is empty for them and
they get no test at all. They close by exactly `2 x pull`.

Recorded in `.claude/memory/letterform-fidelity-2026-08-26.md`: `THERMAL`'s `E`
arm slots go **0.936 → 0.336 mm**, narrower than one 0.4 mm thread; `DRONE`'s
go **0.728 → 0.128 mm**, sealed.

## The prototype

`_exterior_pockets(poly)` returns the concave pockets — the exterior
counterpart of `interiors` — and the caller applies the identical area floor
and the identical hold. Two things had to be right:

- **Difference against the shape with its holes FILLED.** `convex_hull - poly`
  looks correct and is not: a hole is absent from `poly` and present in its
  hull, so an `O`'s counter comes back as a "pocket" and is held twice. Harmless
  geometrically, but it doubles the count `HOLE_NEARLY_CLOSED` reports.
- **Convex hull, not bounding box.** An axis-aligned envelope makes the result
  depend on rotation — the exact defect this file already records ("the same
  artwork sewed differently rotated 45 degrees").

Safe by construction: a pocket is disjoint from `poly`, so `grown - pocket`
still contains all of `poly`. Holding a notch open can restore the original
outline but can never cut into artwork or split a shape further than it was.

## What it buys

Synthetic block `E`, 0.8 mm slots at 0.3 mm pull: **0.800 → 0.200 mm** today,
**0.800 → 0.800 mm** with the guard.

`logo_drone_thermal_badge.png` @ 80 mm — 128 exterior pockets over 74 regions:

| | count | widths |
| --- | --- | --- |
| held by the guard | 15 | 0.528 – 0.920 mm |
| skipped, already under the floor | 82 | median **0.140 mm** |

The held band covers the slots the defect was reported against. The skipped
band is vectorization slivers.

**The area floor is imperfect and knowingly so.** Area conflates a slot's width
with its length, so a short wide slot can fall under a floor a long narrow one
clears — measured, the boundary sits between 0.53 mm held at 2.59 mm² and
0.61 mm skipped at 2.16 mm². Using the interior branch's own floor keeps the
two sides asking one question; a width criterion would buy a narrow band around
0.6 mm at the cost of a new tuned constant.

## What it costs — the reason it is not shipped

It **reds `test_chaining.py::test_chaining_cuts_the_benchmark_fixtures_trim_rate`**,
a fourth failure on top of the three known platform goldens.

`enthusiast_logo.png` @ 82 mm, `left_chest`:

| | trims, chaining off | trims, chaining on | rate |
| --- | --- | --- | --- |
| guard off (today) | 22 | 10 | **3.8 / 1k** pass |
| guard on | 24 | 16 | **6.4 / 1k** fail (ceiling 4.1) |

Mechanism: restoring the notches breaks the gaps chaining had been bridging, so
each restored slot becomes a cut. Nine pockets are held on that fixture, on 4 of
31 shapes, at 0.626 – 0.887 mm — all genuine letterform slots. **The guard is
not misfiring; the cost is real.**

Note the shipped default is `chain_links = False`, where the cost is +2 trims
(22 → 24). The 6.4 figure appears only on a path that is off by default and
gate-1 frozen. That does not make the test wrong to fail — it exists because
this rate regressed silently once already.

## What is NOT measured, and what would settle it

**The fidelity gain has no number.** The cost side is quantified; the benefit is
argued from slot widths, not from a letterform metric. `_prune_spurs` has an
ablation (bare 12.54 → 5.84 mm², 7 letters improved, 0 worse); this has nothing
equivalent, because the instrument that would produce it is itself an open
defect — bare-fabric coverage scores a visibly deformed `H` at "1.9% bare".

So this trades a *measured* trim regression against an *unmeasured* fidelity
gain, between two defects the project already records: lettering deformation,
and "we trim 3.1x the pro". That is the whole reason it is parked rather than
argued either way.

To settle it, in order of what each buys:
1. Rebuild the letterform instrument, then re-run this with both sides measured.
2. Failing that, a sew-out of one fixture with and without — the only test that
   answers what a 0.336 mm slot actually looks like in thread.
