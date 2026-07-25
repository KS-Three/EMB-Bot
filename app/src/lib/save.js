import { defaultProject, migrateProject } from "./project.js";

export function serialize(project) {
  return JSON.stringify(project);
}

export function deserialize(str) {
  try {
    const o = JSON.parse(str);
    return migrateProject(o);
  } catch (e) {
    return defaultProject();
  }
}

const KEY = "embstudio:last";

export function saveLocal(project) {
  try {
    localStorage.setItem(KEY, serialize(project));
  } catch (e) {}
}

export function loadLocal() {
  try {
    const s = localStorage.getItem(KEY);
    return s ? deserialize(s) : null;
  } catch (e) {
    return null;
  }
}
