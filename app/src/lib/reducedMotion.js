// True when the user has asked their system for less motion. Read live (not
// cached) so a change in OS settings applies to the next animation. No
// matchMedia (jsdom, SSR) means no preference was expressed.
export function prefersReducedMotion() {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
