// "Jumps per trim" on the Download step: how many consecutive jump records a
// written .dst uses to encode one trim. Machines differ in how many they read
// as a cut; 3 is the Tajima convention and the default, so an untouched
// setting writes the same bytes as before the control existed.
//
// Remembered across projects like the machine pick (lib/machines.js), with
// the same try/catch contract: storage that is missing or refuses a write
// just means the choice lasts the session.

export const TRIM_JUMPS_KEY = "embstudio:trimJumps";
export const TRIM_JUMPS_DEFAULT = 3;
export const TRIM_JUMPS_MIN = 1;
export const TRIM_JUMPS_MAX = 10;

// Any input -> an integer 1..10; anything unusable -> the default.
export function clampTrimJumps(v) {
  const n = Math.round(Number(v));
  if (!Number.isFinite(n)) return TRIM_JUMPS_DEFAULT;
  return Math.min(TRIM_JUMPS_MAX, Math.max(TRIM_JUMPS_MIN, n));
}

export function loadTrimJumps() {
  try {
    const raw = localStorage.getItem(TRIM_JUMPS_KEY);
    return raw == null ? TRIM_JUMPS_DEFAULT : clampTrimJumps(raw);
  } catch (e) {
    return TRIM_JUMPS_DEFAULT;
  }
}

export function saveTrimJumps(n) {
  try {
    localStorage.setItem(TRIM_JUMPS_KEY, String(clampTrimJumps(n)));
  } catch (e) {
    // no storage; nothing to do
  }
}
