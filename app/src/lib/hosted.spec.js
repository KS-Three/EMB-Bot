import { test, expect, vi, afterEach } from "vitest";
import { isHosted } from "./hosted.js";

afterEach(() => {
  vi.unstubAllEnvs();
});

test("unset VITE_HOSTED is not hosted", () => {
  expect(isHosted()).toBe(false);
});

test("the exact string \"1\" is hosted", () => {
  vi.stubEnv("VITE_HOSTED", "1");
  expect(isHosted()).toBe(true);
});

// Deliberate: a truthy-looking value must NOT flip the posture. The flag is
// set in exactly two places (the Pages job, the hosted Playwright config) and
// a typo there should fail closed to the desktop behaviour, not silently
// publish a build that stops probing on Kent's own machine.
test("any other value is not hosted", () => {
  vi.stubEnv("VITE_HOSTED", "true");
  expect(isHosted()).toBe(false);
  vi.stubEnv("VITE_HOSTED", "");
  expect(isHosted()).toBe(false);
});
