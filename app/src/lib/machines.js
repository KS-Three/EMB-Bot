// "Your machine" on the Download step (2026-09-30). A customer knows the
// brand on the front of their machine; they do not know that Brother reads
// PES and Janome reads JEF, and the nine-button format grid asked them to.
// One table, brand -> the format that machine reads, and the one chosen
// remembered across projects, since a customer owns one machine.
//
// The format keys are the ones DownloadStep's askThenDl already takes. The
// grid stays beneath as "All formats", so a customer with a machine not
// listed here, or two machines, loses nothing.

export const MACHINES = [
  { id: "brother", label: "Brother / Baby Lock", format: "pes" },
  { id: "janome", label: "Janome / Elna / Kenmore", format: "jef" },
  { id: "tajima", label: "Tajima and other commercial", format: "dst" },
  { id: "bernina", label: "Bernina / Melco", format: "exp" },
  { id: "husqvarna", label: "Husqvarna Viking / Pfaff", format: "vp3" },
  { id: "singer", label: "Singer", format: "xxx" },
  { id: "ricoma", label: "Ricoma / SWF / Barudan / Happy", format: "dst" },
];

export const MACHINE_KEY = "embstudio:machine";

export function machineById(id) {
  return MACHINES.find((m) => m.id === id) || null;
}

// The stored choice, or null when none was made or storage is unreadable.
// A stored id this build no longer lists reads as null too, so a removed
// entry can never leave the step pointing at a format that does not exist.
export function loadMachineId() {
  try {
    const id = localStorage.getItem(MACHINE_KEY);
    return id && machineById(id) ? id : null;
  } catch (e) {
    return null;
  }
}

// Same try/catch contract as hints.js: a write that fails (quota, denied)
// simply does not persist; the in-page choice still applies for the session.
export function saveMachineId(id) {
  try {
    if (id) localStorage.setItem(MACHINE_KEY, id);
    else localStorage.removeItem(MACHINE_KEY);
  } catch (e) {
    // no storage; nothing to do
  }
}
