// Build-time posture flag, set ONLY by the GitHub Pages deploy job and the
// hosted Playwright config (VITE_HOSTED=1). A local `npm run dev` or
// `npm run build` leaves it unset, so Kent's own machine keeps probing the
// localhost digitizer service and nothing about the desktop workflow changes.
//
// Read through a function rather than a module-level const so vitest's
// vi.stubEnv can drive both postures inside a single run. The try/catch
// mirrors the house pattern digitizer.js already uses for localStorage: an
// environment that does not define import.meta.env is "not hosted", never a
// throw.
export function isHosted() {
  try {
    return import.meta.env.VITE_HOSTED === "1";
  } catch (e) {
    return false;
  }
}
