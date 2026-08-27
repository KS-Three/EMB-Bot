# Kent's review of fourteen stitch-outs — 2026-08-27

The first time Kent has given per-design feedback on auto-digitized output in
his own words. Fourteen designs, fourteen notes. This file is the record; the
notes are quoted verbatim because paraphrasing them is how the signal gets lost.

Collected through the validation artifact
(`claude.ai/code/artifact/b313a4a6-5089-45ad-a2b2-815c142b1c85`), which saves
his notes by republishing itself — **do not republish that page from a script
or a check-in, it will overwrite what he has written.**

## The headline number

> **"The artwork is nice improvement, i would put these at 60% of the way
> there."**

"There" is market parity with Ember (`PRODUCT.md`: Wilcom and Hatch are
explicitly not the bar). Against that, the two instruments that existed both
averaged ~80 on the same designs:

| | mean over the 8 scored |
|---|---:|
| `artfidelity_self` ARTFID | 83.7 |
| `preflight` score | 80.0 |
| **Kent's eye** | **60%** |

They correlate with each other at only **rho = 0.405**. Two instruments, both
averaging ~80, neither anywhere near his number and barely agreeing with each
other.

**The rule that falls out: ARTFID must never be quoted as a quality
percentage.** It is a fidelity score. 83.7 does not mean "84% of the way
there", and the gap is not the metric being 24 points optimistic — it is the
metric measuring a different thing.

## The two themes

### 1. Smoothness — raised on EIGHT of fourteen

> *"Lines/circles are not smooth like the photo, **Shapes are accurate but
> smoothness is not**."* (written on both `logo_whitebg` and `ribbon_curve`)

That middle sentence is the whole problem statement, and it is Kent
independently describing the fidelity-vs-craft split: the shape is right and
the craft is not.

Confirmed 2026-08-27 that this is **two** complaints, not one, and that both
matter to him about equally:

* **Edge noise** — *"the edges around BECKER... they are jaged"*, *"it's
  sawtoothed and jaged"*, *"ENTHUSIAST looks to wavey and not crisp/clean"*.
* **Curve fidelity** — *"Lines/circles are not smooth like the photo"*. A
  curve sewn as a polygon; `enginefidelity.py`'s docstring already names this
  case ("a 20 mm circle RDP'd into a 20-gon").

### 2. Whole elements missing — raised on SEVEN of fourteen

> *"The red 'arm' on the right side of the logo was lost."*
> *"EAT | STAY | PLAY was completely lost."*
> *"Resturant was dropped completely."*
> *"the left side trees were lost."*
> *"Text on the bottom was dropped out."*

Both designs he marked **out of place** are the two that lost an element.

## The fourteen notes, verbatim

Ranked rows first, in the order the instrument put them.

| # | fixture | verdict | note |
|---|---|---|---|
| 1 | `bg_uncertain.png` | rank looks right | "The lines through the center gap are not straight, like the original artwork." |
| 2 | `logo_alpha.png` | rank looks right | *(no note)* |
| 3 | `logo_whitebg.png` | — | "Lines/circles are not smooth like the photo, Shapes are accurate but smoothness is not." |
| 4 | `ribbon_curve.png` | rank looks right | "Lines/circles are not smooth like the photo, Shapes are accurate but smoothness is not." |
| 5 | `becker_marine_logo.png` | **OUT OF PLACE** | "The text in Marine is not smooth enough, along with the edges around BECKER not being smooth, they are jaged. also, the C infill was completely lost." |
| 6 | `logo_script_tires.png` | rank looks right | "The edge of the text is not smooth enough, it's sawtoothed and jaged." |
| 7 | `enthusiast_logo.png` | **OUT OF PLACE** | "The red 'arm' on the right side of the logo was lost. ENTHUSIAST looks to wavey and not crisp/clean." |
| 8 | `region_blobs.png` | — | "Way to difficult to digitize something like this accuratly." |

Refused rows — the instrument declines to score these, but the pictures still
drew feedback:

| fixture | note |
|---|---|
| `logo_hotel_fremont.webp` | "EAT \| STAY \| PLAY was completely lost. EST on top was dropped out. THE is incomplete and the rope stitching around the border is intermittantly in and out." |
| `logo_bridge_bar.jpg` | "Resturant was dropped completely. The logo looks clean at 80%. but BRIDGE text should be cleaner and more crisp" |
| `drone_render.png` | "Huge improvement on this logot, the left side trees were lost and some minor details were ommited from the final stitch out (the "E" on drone and the cross hairs on top and bottom)" |
| `logo_golden_tee.jpg` | "This is actually pretty nice/okay, i would just clean up the edges and make the artwork more \"crisp\"" |
| `summit_badge.png` | "Text on the bottom was dropped out and i'm not sure what happened with the background, it's half missing." |
| `logo_gaulke_roofing.png` | "The logo is 5% completed at most, this is way wrong." |

## Kent's rulings this session

* **Both smoothness complaints matter about equally.** Not one instrument.
* **`logo_alpha` is "a bit rough too"** — so it is NOT a clean control. This
  reframes `edge_smoothness`'s narrow 0.131-0.217 spread as probably correct
  rather than broken: everything is somewhat rough, and what is missing is a
  bar, not a different metric.
* **`region_blobs` stays in the ranked set.** "Hard cases matter" — dropping
  the designs we do worst on is how a fixture set quietly becomes flattering,
  even though it is the noisiest row in every sweep run today.

## What the instruments could and could not see

`ARTWORK_UNCOVERED` — preflight's own "artwork the engine never covered" check
— fired on **one** of the seven designs Kent says lost elements, and reported
`0.0 mm2` on the rest with `uncovered_checked: True`. It ran and saw nothing.
Its own message says why: the area it measures is *"claimed by a shape the
design sews"*, so an element dropped before it ever became a region has no
shape to be uncovered.

| fixture | ARTWORK_UNCOVERED | Kent |
|---|---|---|
| `becker_marine` | 18.8 mm2, **fired** | C infill lost |
| `enthusiast` | 0.0 | red arm lost |
| `hotel_fremont` | 0.0 | EAT \| STAY \| PLAY lost |
| `bridge_bar` | 0.0 | Restaurant dropped |
| `summit_badge` | 0.0 | bottom text dropped |
| `drone_render` | 0.0 | left trees lost |

`preflight` graded `logo_whitebg` **A 100** on a design he says is not smooth,
and `enthusiast_logo` **B 88** with a limb missing.

## Two engine defects found, neither fixed

1. **`summit_badge`'s background is half removed.** Stage 1 strips the
   vignette's corners and sews the rest as a grey blob — Kent's "it's half
   missing" is exactly right. An earlier claim in PR #276's body that "the
   engine is correct at the shipped 6.0" is **wrong** and should be read with
   that correction; the instrument fix in that PR stands regardless.
2. **`stage1_prep.py:254-266` couples a structural question to a colour
   threshold.** `agreement` is computed from `close`, which is computed from
   `bg_tolerance_lab`, so the `BACKGROUND_ABSENT` gate trips more easily the
   stricter the tolerance. Measured: the gate (0.75) is crossed between
   `bg_tolerance_lab` 4.5 (agreement 0.7454, nothing floods) and 4.8 (0.7687,
   floods 24%). Nothing is broken at the shipped 6.0; the coupling is not what
   the comment there claims.

## The `bg_tolerance_lab` search, answered

The parameter search left open by the lost session is resolved: **nothing to
apply.** The swept curve over 3.0-8.0 has no stable optimum — mean ARTFID
deltas `+4.83, +2.43, +4.51, +0.06, 0, +1.22, +1.30`, non-monotonic, with
**99.5%+ of every delta coming from two fixtures**. The original
"6.0 -> 4.5 = +4.28" was the metric being wrong (`summit_badge`'s saturated ink
mask, fixed in PR #276), not the engine improving.

## Open — needs Kent

* **Where should `becker_marine` and `enthusiast_logo` actually rank?** He
  marked both out of place but not where they belong, and ROADMAP phase 1's
  exit condition is phrased on the ranking.
* **The composite weights stay provisional.** 0.40/0.25/0.35 reproduce the
  table they were solved from and have earned nothing else. Hard gate 4's
  preferred reading is `--components`.

## Next build

**Curve fidelity must read the stitch path, not a raster.** Proven, not
assumed — see `tools/edge_smoothness.py`'s docstring for the experiment: a
rasterised 20 mm circle reads *more* angular than a 40-gon at every resample
step tested, because a raster boundary is itself a staircase. `plan.iter_runs()`
carries the vertices the machine actually sews, where a 20-gon has 20 of them.

The general form of that lesson, which applies past this one instrument:
**several of today's dead ends came from measuring pictures of stitches instead
of the stitches.**
