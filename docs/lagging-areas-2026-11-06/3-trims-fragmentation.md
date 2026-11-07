# Trims, needle-up breaks and fragmentation: external sourcing (2026-11-06)

Scope: MASTER_SCOPE defects 4 and 6. Baseline is the 17-pair measure on main 44ecf1cb (`docs/trim-defects-4-6-2026-10-29.md`): cuts 391 vs pro 409, needle-up 879 vs 425, 488 uncut floats vs 16. Of our 104 in-piece cuts, 32 are fill sections (pro 0), 27 satin splits, 42 shape-to-shape. [V] = checked at the primary source today; [U] = not checked.

## (a) Verdict

There is almost nothing to adopt, and that is the finding. No permissive library or published code plans an embroidery fill or satin chain. The one idea that matches the pro's "fill is one connected piece" is an **Euler-tour fill**: put the rows and the shape boundary in one graph, double some boundary edges until an Euler path exists, and walk it. Its sources are a 2003 theory paper (Arkin, Fekete, Mitchell, lawn mowing and milling) and a 2017 public description of Ink/Stitch's version. It needs no new dependency: `networkx` (BSD-3) is already pinned and `shapely` is already in use. It is the single **PROTOTYPE**, scoped as an offline census first. The other 3 directions come back negative: satin splitting has no library and the remaining pool is small; underpath travel is already built and closed by geometry; the adjacent-field slicer and CAM code is wrong-shaped or copyleft. The biggest number, the 488 uncut floats, has no external solution. It is a fabric question (gate 1) that only `cut_every_jump` plus a sew-out settles.

## (b) Verdict table

| Candidate | Licence | Stars / last push | Verdict | Serves |
|---|---|---|---|---|
| Euler-tour fill (Arkin-Fekete-Mitchell, arXiv cs/0309014 [V]; Ink/Stitch idea via 2017 mailing-list post [V]) | Paper: idea. Ink/Stitch code: GPL, never read | n/a | **PROTOTYPE** (in-house) | 32 fill-section cuts; Fremont's 10 underlay-ring hops |
| `networkx` `eulerian_path`, `min_weight_matching` | BSD-3 [V] LICENSE.txt | 17.4k, 2026-11-04; 3.7 declares `!=3.14.1,>=3.12`, classifiers list 3.12 to 3.15 [V] | **ADOPT as the toolkit** (already pinned 3.6.1) | the prototype; do NOT use `eulerize` as is |
| Fields2Cover (boustrophedon/trapezoidal decomposition) | BSD-3 [V] | 923, 2026-10-27 [V] | **REJECT** as a dependency | wrong direction (it splits fields, we need to join) |
| Connected Fermat Spirals (Zhao et al. SIGGRAPH 2016) | no code released [V: page lists paper, slides, supplement.zip only] | n/a | **WATCH** | contour-parallel fill type only; not tatami |
| Tian-Luo-Hu 2005, "Shape Decomposition Algorithm in Embroidery" (J. CAD and CG) | paper, no code [U beyond the abstract] | n/a | **WATCH** | satin splits; same idea as `classify_ribbon` |
| Brother patent US7996103 (jump to running stitch under a later segment) | patent | n/a | **WATCH** (caution) | underpath; already built |
| Variable-width-contouring (mfx-inria) | BSD-3 [V]; optional CGAL dependency is GPL [U] | 18, 2026-10-19 | **REJECT** | satin width, not trims |
| libArachne / CuraEngine Arachne | AGPL-3.0 [V] | 14, 2020-07-06 | **REJECT** (output only) | none |
| Kiri:Moto (GridSpace/grid-apps, JS) | MIT [V] | 929, 2026-10-22 | **REJECT** | 3D-print infill; its fill internals were not confirmed [U] |
| Ink/Stitch auto-fill, auto-route satin, jump-to-stroke | GPL-3 | n/a | docs read for the idea only | confirms the target |

## (c) PROTOTYPE: Euler-tour fill, census first

**What it is.** Build a graph per shape. Nodes are row endpoints and boundary vertices. Edges are the row segments and the boundary arcs, with the holes' rings included. Take the odd-degree nodes and pair them by minimum-weight matching on shortest-path length. Duplicate the edges along those paths so every node has even degree. Then `networkx.eulerian_path` gives one connected walk. The 2017 description credits the milling paper and adds that any border stretch is sewn at most twice, with heuristics added so rows are not scattered. The author said the graph part was sound and the conversion to stitches was "busywork" [V]. The problem is NP-hard for polygons with holes, so heuristic and not optimal.

**Where it plugs in.** `stage6_fill._plan_sections` (line 2140) already asks `fill_section_travel.plan` for 2 orders and prices them with `_score`. The Euler walk would be a third candidate from the same hook. It keeps that function's contract: the last path is pinned, no other shape moves, and a plan is kept only if it cuts no more and lays no more on finished fill than the incoming order. It goes behind `cfg.extra["fill_euler_tour"]`, built OFF. Stage two of the same idea is the `edge_lattice` underlay: the rings and connections form the same kind of graph (Fremont's 10 underlay cuts, `fill_section_travel` docstring).

**Cost.** 2 sessions. Session 1 is an offline census in `tools/` with no engine change. Session 2 is the planner candidate and its flip-sheet row. The tour conversion is the real work, as the 2017 author found.

**The catches (read these before agreeing).**
1. The existing planner already finds fewer-cut section orders: Becker's small field goes 4 to 3 cuts and MFab's hat field 8 to 6. `_score` refuses them for the extra hidden travel, and `fill_section_cuts_first` (#1193, OFF, held) prices that away. The flip-sheet row shows it moves 9 of 17 jobs by 0 to 2 cuts. An Euler walk is a stronger *construction* of the same thing, not a new idea. It may move little beyond what #1193 already does.
2. Edge doubling lays a second pass along the boundary. Hidden under the next rows it is the pro's own way across a fill; on the visible edge it is exposed thread. Keep routes inside `TRAVEL_INSET_MM` and under rows still to come, as `fill_section_travel.bridge` does, and no new constant is needed. If the walk wants the uncovered rim, that is the one place a sew-out is needed: a Becker-size fill block with the doubled rim sewn bare vs covered. Until then it is built OFF, Kent's flip (gate 1).
3. `nx.eulerize` is not a Chinese-postman solver. Its matching is `max_weight_matching` on `(len(G)+1) - len(path)` with no `maxcardinality`, so it can leave odd nodes unmatched [V, read in the stable source]. Use `nx.min_weight_matching` over the odd nodes' shortest-path matrix, and assert the result is Eulerian.
4. networkx 3.7 refuses Python 3.14.1 (`!=3.14.1`) [V]. The repo is on 3.6.1; keep the pin when bumping.
5. Ruling check: this is not TSP segment ordering (Kent 11-05 "SKIP"). It changes what is *connected*, not the visit order. But it shares the 11-05 evidence that order is not the gap (18 of 145 extra cuts), so expect a modest result.

**First measurable experiment (no engine change).** A `tools/` script over the 17-pair baseline replays the 32 fill-section cuts' shapes from the pickled stage 0-4 results. For each shape it builds the row+boundary graph and reports: (i) sections the rows fall into today; (ii) whether the Euler walk exists with every added edge inside the inset and under later rows; (iii) added boundary mm. Pass bar: at least 20 of the 32 become one walk with 0 mm exposed. If fewer, stop; the finding is that the cuts need a route the shape does not offer, as `buried-walk` found for between-shape cuts. Then session 2 reports cuts, needle-up count, `travel_cover` exposed mm and `bare_by_band` against the 17-pair table, ON beside `fill_section_cuts_first` ON, because that is the true comparator.

## (d) Rejected, one line each

- **Fields2Cover** [V]: BSD-3 but builds from source (`pip` sdist only [V]), needs GDAL, GEOS, Boost, OR-tools (EPL-2.0 chain already rejected 09-12); holes unconfirmed. It splits a concave field into cells, the opposite of what fragmentation needs.
- **Connected Fermat Spirals**: no released code, and a spiral is a contour fill, not the tatami the pro sews. Revisit only if Kent asks for a contour fill type.
- **Satin-split libraries**: none found. Of 27 satin_split cuts, `satin-split-cuts-2026-10-27` places 16 in band loops (the chain, #1143), 2 in Drone, 8 in Column-lane letters. The slot guard fixes 3 of the 8 letter cuts (261 to 258 trims) at a second `column_runs` per letter. A decomposition paper cannot beat that, so no library here changes the count.
- **Underpath routing** (Ink/Stitch jump-to-stroke docs [V], Brother US7996103): the idea is built (`trim_bury_under_later` ON; `buried-walk-2026-10-26`: 0 of our 176 between-shape cuts have ANY route under later thread). A literature find cannot create a route the geometry lacks. [U] whether the Brother patent is still in force; the existing code predates this note, so flag it to Kent, not a blocker.
- **Arachne / variable-width contouring**: AGPL (libArachne [V]) or CGAL-optional (mfx-inria); both are about width control, which is satin quality (defect 5), not trims.
- **Kiri:Moto**: MIT, JS, but a 3D-print slicer; infill assumes layered extrusion, and its clipper use was not confirmed [U].
- **OR-Tools, penkit-optimize, vpype**: stay rejected per 09-12 and Kent's 11-05 "SKIP". Not re-proposed.
- **Commercial packages** (Hatch "Apply Closest Join", Wilcom): behaviour descriptions only; Closest Join "will not completely eliminate" jumps, per the vendor's own post [V].

## The uncut floats (488) need a sew-out, not a library

`cut_every_jump` (OFF) turns the floats into cuts for about +80 cuts. Whether a short float may stay is thread, fabric and hop length. The ladder that would settle it is one block with identical 1, 2, 3 and 5 mm floats on the target fabric, sewn cut and uncut, then judged by Kent. That is the same shape as the earlier hop-length ladder, and it is his flip. The literature search found nothing that substitutes for it.

## (e) Sources

- Zhao et al., Connected Fermat Spirals: https://haisenzhao.github.io/CFS
- Arkin, Fekete, Mitchell, lawn mowing and milling: https://arxiv.org/pdf/cs/0309014
- Lex Neva, Euler-path fill, Inkscape-devel, 22 Sep 2017 (idea only): https://lists.inkscape.org/hyperkitty/list/inkscape-devel@lists.inkscape.org/message/3HTQQJOF6GUG3QILKWJVCUA5SYJOFBPV/
- Ink/Stitch routing docs (idea only): https://inkstitch.org/tutorials/routing/
- networkx Euler source: https://networkx.org/documentation/stable/_modules/networkx/algorithms/euler.html ; licence https://raw.githubusercontent.com/networkx/networkx/main/LICENSE.txt ; PyPI https://pypi.org/pypi/networkx/json
- Fields2Cover: https://github.com/Fields2Cover/Fields2Cover
- mfx-inria Variable-width-contouring: https://github.com/mfx-inria/Variable-width-contouring ; libArachne: https://www.github.com/Ultimaker/libArachne
- Kuipers et al. paper: https://arxiv.org/abs/2004.13497
- Kiri:Moto / grid-apps: https://github.com/GridSpace/grid-apps
- Brother patent: https://patents.google.com/patent/US7996103
- Tian, Luo, Hu 2005 abstract (via search only): https://jcad.cn/en/article/id/b1b145e8-cb50-4a0a-941c-78c12b179e9c
- Hatch on jumps: https://blog.hatchembroidery.com/avoid-the-jump-kangaroo-free-design/
- Repo: `docs/trim-defects-4-6-2026-10-29.md`, `docs/flip-sheet-2026-10-30.md`, `docs/external-repo-sourcing-2026-09-12.md`, `docs/external-repo-sourcing-2026-11-06.md`, `digitizer/digitizer_core/fill_section_travel.py`, `digitizer/digitizer_core/stage6_fill.py`
