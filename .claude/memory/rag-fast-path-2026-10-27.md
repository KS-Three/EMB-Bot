---
name: rag-fast-path-2026-10-27
description: skimage's rag_mean_color was 37-53 s of a ~250 s gradient-lane digitize (a Python callback per pixel); fast_skimage.rag_mean_color replays the same add_edge calls in first-discovery order, 0.2-0.7 s, all 7 gradient fixtures md5-identical
metadata:
  type: project
---

2026-10-27, Kent asked "can we speed the digitizer up without losing
quality?" Bench on main dd76ea0a, laptop quiet: the 14 tracked fixtures took
1,505 s, of which the six gradient-lane photos took 46-266 s each (Golden
Tee 266, Fremont 253, Summit 229, Drone 224).

**Where Fremont's time went (cProfile, 283 s):** stage 2 `segment` 112 s,
of which `skgraph.rag_mean_color` 57 s (`generic_filter` calling
`_add_edge_filter` 3.36M times, then an `np.ndindex` colour loop) and
`merge_hierarchical` 22 s; stage 7 `sequence` 69 s (fill angle search 23 s);
`enlarge_small_text` 24 s; `revalidate_threads` 18 s; `ocr_suggest_text`
16 s (36 serial tesseract reads).

**Built:** `fast_skimage.rag_mean_color`. Neighbour pairs from shifted
arrays, then the SAME `add_edge` calls replayed in the order the filter made
them (pixel C order, footprint row-major, first discovery per pair), so node
order, adjacency order, edge order and `max_id` match; colour sums by
`np.bincount` (float64, pixel order, same as the loop). Checked against
skimage inside the pipeline on all 7 gradient fixtures: graph identical,
design md5 identical. skimage vs fast per job: Fremont 41 -> 0.6 s, Golden
Tee 53 -> 0.7, Drone 17.5 -> 0.3, Bridge 10.6 -> 0.2, Summit 9.2 -> 0.2,
Gaulke 7.9 -> 0.2, blobs 4.0 -> 0.1.

**Next candidates, not built:** `ocr_suggest_text` 4-at-a-time like
`legibility._ocr_all` (its "serial ON PURPOSE" comment predates the outer
`OMP_THREAD_LIMIT=1` fix that made legibility's pool 2.3-2.8x); the fill
angle search in stage 6; `merge_hierarchical`'s `_weight_mean_color`.

**How to apply:** a `fast_skimage` replacement must reproduce INSERTION
ORDER, not just the graph; `merge_hierarchical` and `_weight_mean_color` read
it. Related: [[digitize-speed-2026-10-26]], [[column-lane-memo-2026-10-26]].
