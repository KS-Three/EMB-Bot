// Whether the configurator's "Advanced" disclosure is open (spec 2026-09-30
// §2.2: closed by default, remembered for the session, NOT persisted).
//
// A module-level store rather than component state on purpose: the editor
// panels are rebuilt every time another element is selected (ContentStep keys
// them on the element id), and a customer who opened Advanced should not have
// it snap shut because they clicked a different row. A page reload starts
// closed again -- nothing here touches localStorage or the project file.
import { writable } from "svelte/store";

export const advancedOpen = writable(false);

export function toggleAdvanced() {
  advancedOpen.update((open) => !open);
}

// Tests only: the store outlives a rendered component, as it should.
export function resetAdvanced() {
  advancedOpen.set(false);
}
