import { describe, it, expect, beforeEach } from "vitest";
import { get } from "svelte/store";
import { digitizeBusy, markDigitizeBusy } from "./digitizeBusy.js";

describe("digitizeBusy", () => {
  beforeEach(() => digitizeBusy.set(new Set()));

  it("is empty until a run starts, and empty again when it ends", () => {
    expect(get(digitizeBusy).size).toBe(0);
    markDigitizeBusy("e1", true);
    expect(get(digitizeBusy).has("e1")).toBe(true);
    markDigitizeBusy("e1", false);
    expect(get(digitizeBusy).size).toBe(0);
  });

  it("one element finishing leaves another's run showing", () => {
    markDigitizeBusy("e1", true);
    markDigitizeBusy("e2", true);
    markDigitizeBusy("e1", false);
    expect([...get(digitizeBusy)]).toEqual(["e2"]);
  });

  it("does not notify subscribers when nothing changed, and ignores a missing id", () => {
    markDigitizeBusy("e1", true);
    let calls = 0;
    const stop = digitizeBusy.subscribe(() => calls++);
    markDigitizeBusy("e1", true);
    markDigitizeBusy(null, true);
    markDigitizeBusy(undefined, false);
    stop();
    expect(calls).toBe(1); // the subscribe call itself
  });
});
