import { writable } from "svelte/store";

// Which thread chart THIS design's cones came out of.
//
// The engine snaps every cone to a real manufacturer catalog and records the
// brand on the element (`review.brandId`, from the service's own
// `palette[0].brand_id`). Two screens need that fact and neither is where it
// lives:
//
//   - the Download step's shopping list, which re-derives a NAME for every
//     cone from the chosen chart;
//   - `ThreadPicker`, which offers replacements from the chosen chart.
//
// Both defaulted to Studio's 56 generic shades for anyone who had never
// picked a chart — every first-time customer. The Download step was fixed
// 2026-09-07 by passing the id down; the picker was not, and was found
// half an hour later showing "Studio basics" directly above a label reading
// `0134 Smoky`. It is used in NINE places across seven components, so a prop
// threaded through every one of them is the wrong shape for a fact that
// belongs to the project.
//
// A store instead: App sets it from the project, and any picker anywhere
// reads it. `chartIdForProject` stays pure and exported so the rule itself
// is testable without a component.

/**
 * The chart id this project's cones were snapped from, or null.
 *
 * Every element in a project shares the brand (the service digitizes them
 * all against the same chart), so the first element carrying one wins. A
 * lettering-only project has none, and null is the honest answer — the
 * caller falls back to generic shade names.
 */
export function chartIdForProject(project) {
  const els = (project && project.elements) || [];
  for (const el of els) {
    const id = el && el.review && el.review.brandId;
    if (id) return id;
  }
  return null;
}

export const designChartId = writable(null);
