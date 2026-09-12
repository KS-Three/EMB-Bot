// @vitest-environment jsdom
//
// Two layers, because the two questions are different:
//
// 1. Against jsdom's REAL session history (it implements the whole thing —
//    replaceState does not grow `length`, pushState truncates the forward
//    entries, back()/forward() fire popstate with the right state, and back()
//    on the first entry does nothing at all). This is where the trail is
//    proved end to end, including the one that matters most: **Back from the
//    first step leaves the Studio.**
// 2. Against a history double, for WHICH VERB a navigation picks. push vs.
//    back is the whole behavioural difference between the in-app Back button
//    stacking a near-duplicate entry and it being the same gesture as the
//    browser's own Back, and a real stack cannot tell you which one happened.
import { describe, expect, test, vi } from "vitest";
import { createStepHistory, stepFromState, STEP_KEY } from "./stepHistory.js";

// ---- layer 1: the real jsdom stack ----------------------------------------

// jsdom gives the whole FILE one window, so this block runs first and owns a
// pristine stack; the assertion below fails loudly rather than silently
// measuring the wrong baseline if anything is ever added above it.
describe("the trail the browser actually gets", () => {
  const settle = () => new Promise((r) => setTimeout(r, 60));
  function nextPop() {
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => {
        window.removeEventListener("popstate", on);
        reject(new Error("no popstate arrived within 500ms"));
      }, 500);
      function on() {
        clearTimeout(t);
        window.removeEventListener("popstate", on);
        resolve();
      }
      window.addEventListener("popstate", on);
    });
  }

  test("n visited steps cost n-1 entries, Back walks them, and Back from the first step leaves", async () => {
    expect(window.history.length, "this test must run first — see the block comment").toBe(1);

    const seen = [];
    const h = createStepHistory({ history: window.history, onStep: (s) => seen.push(s) });
    window.addEventListener("popstate", (e) => h.pop(e));

    h.start("garment");
    // THE anti-trap assertion. An entry here and Back from the first step
    // lands on the Studio again, which is worse than the bug being fixed.
    expect(window.history.length).toBe(1);
    expect(stepFromState(window.history.state)).toBe("garment");

    h.go("content");
    h.go("create");
    expect(seen).toEqual(["content", "create"]);
    expect(window.history.length).toBe(3); // three steps, two entries

    window.history.back();
    await nextPop();
    expect(seen.at(-1)).toBe("content");

    window.history.back();
    await nextPop();
    expect(seen.at(-1)).toBe("garment");
    expect(window.history.length).toBe(3); // going back never destroys entries

    // Back once more, from the first step. Nothing of the Studio's is behind
    // this entry, so no popstate fires at all — in a browser the entry behind
    // it belongs to wherever the customer came from, and that is where they
    // go. This is the assertion the open item named as the failure mode.
    const before = seen.length;
    window.history.back();
    await settle();
    expect(seen.length, "the first step must not own a Studio entry of its own").toBe(before);

    // Forward re-advances, one step per press.
    window.history.forward();
    await nextPop();
    expect(seen.at(-1)).toBe("content");
    window.history.forward();
    await nextPop();
    expect(seen.at(-1)).toBe("create");
  });
});

// ---- layer 2: which verb a navigation picks -------------------------------

function fakeHistory() {
  return {
    state: null,
    calls: [],
    pushState(state) {
      this.calls.push(["push", state]);
      this.state = state;
    },
    replaceState(state) {
      this.calls.push(["replace", state]);
      this.state = state;
    },
    back() {
      this.calls.push(["back"]);
    },
  };
}

const verbs = (history) => history.calls.map((c) => c[0]);

function harness() {
  const history = fakeHistory();
  const onStep = vi.fn();
  return { history, onStep, h: createStepHistory({ history, onStep }) };
}

describe("boot", () => {
  test("the first step replaces the entry the browser already has, and never pushes", () => {
    const { history, h } = harness();
    h.start("garment");
    expect(verbs(history)).toEqual(["replace"]);
    expect(history.state[STEP_KEY]).toBe("garment");
  });

  test("a replace keeps whatever else was on the entry — it is overwriting someone else's", () => {
    const { history, h } = harness();
    history.state = { somethingElse: 1 };
    h.start("garment");
    expect(history.state.somethingElse).toBe(1);
  });
});

describe("moving through the flow", () => {
  test("a step forward pushes exactly one entry and applies the step", () => {
    const { history, onStep, h } = harness();
    h.start("garment");
    h.go("content");
    expect(verbs(history)).toEqual(["replace", "push"]);
    expect(onStep.mock.calls).toEqual([["content"]]);
  });

  test("navigating to the step already on screen does nothing at all", () => {
    const { history, onStep, h } = harness();
    h.start("garment");
    h.go("garment");
    expect(verbs(history)).toEqual(["replace"]);
    expect(onStep).not.toHaveBeenCalled();
  });

  test("stepping back onto the entry we came from hands over to the browser's Back", () => {
    const { history, onStep, h } = harness();
    h.start("garment");
    h.go("content");
    onStep.mockClear();
    h.go("garment");
    // No third entry for a step already behind us, and the step change waits
    // for the popstate that Back produces rather than being applied twice.
    expect(verbs(history)).toEqual(["replace", "push", "back"]);
    expect(onStep).not.toHaveBeenCalled();
  });

  test("a jump that is NOT the previous entry pushes instead", () => {
    const { history, h } = harness();
    h.start("garment");
    h.go("content");
    h.go("create");
    h.go("garment"); // two entries back, not one — the tab row allows this
    expect(verbs(history)).toEqual(["replace", "push", "push", "push"]);
  });

  test("pushing from mid-trail drops the steps that were ahead", () => {
    const { history, onStep, h } = harness();
    h.start("garment");
    h.go("content");
    h.go("create");
    h.pop({ state: { [STEP_KEY]: "content", embStepIndex: 1 } });
    onStep.mockClear();
    h.go("download"); // "create" was ahead of us; the push drops it
    expect(verbs(history)).toEqual(["replace", "push", "push", "push"]);
    // "content", the step we pushed FROM, is the entry behind us, so Back
    // still hands over...
    h.go("content");
    expect(verbs(history).at(-1)).toBe("back");
    // ...while "create", which the push dropped, costs a fresh entry.
    h.go("create");
    expect(verbs(history).at(-1)).toBe("push");
  });
});

describe("switching projects", () => {
  test("replaces the entry rather than adding one, and still moves the step", () => {
    const { history, onStep, h } = harness();
    h.start("garment");
    h.go("content");
    h.go("create");
    onStep.mockClear();
    h.replace("content"); // opening a saved design lands on Content
    expect(verbs(history)).toEqual(["replace", "push", "push", "replace"]);
    expect(onStep.mock.calls).toEqual([["content"]]);
  });
});

describe("popstate", () => {
  test("applies the step recorded on the entry", () => {
    const { onStep, h } = harness();
    h.start("garment");
    h.go("content");
    onStep.mockClear();
    h.pop({ state: { [STEP_KEY]: "garment", embStepIndex: 0 } });
    expect(onStep.mock.calls).toEqual([["garment"]]);
  });

  test("re-syncs the trail, so the next in-app Back hands over too", () => {
    const { history, h } = harness();
    h.start("garment");
    h.go("content");
    h.go("create");
    h.pop({ state: { [STEP_KEY]: "content", embStepIndex: 1 } });
    h.go("garment");
    expect(verbs(history).at(-1)).toBe("back");
  });

  test("a state we did not write is left alone — moving the wizard on it would be a guess", () => {
    const { onStep, h } = harness();
    h.start("garment");
    onStep.mockClear();
    h.pop({ state: null });
    h.pop({ state: { someoneElse: true } });
    h.pop({});
    h.pop();
    expect(onStep).not.toHaveBeenCalled();
  });
});

describe("without a history object", () => {
  test("the step still changes — no DOM, no navigation, no crash", () => {
    const onStep = vi.fn();
    const h = createStepHistory({ history: null, onStep });
    h.start("garment");
    h.go("content");
    h.replace("create");
    expect(onStep.mock.calls).toEqual([["content"], ["create"]]);
  });
});

describe("stepFromState", () => {
  test("reads our key and nothing else", () => {
    expect(stepFromState({ [STEP_KEY]: "content" })).toBe("content");
    expect(stepFromState({ [STEP_KEY]: 3 })).toBe(null);
    expect(stepFromState({})).toBe(null);
    expect(stepFromState(null)).toBe(null);
    expect(stepFromState(undefined)).toBe(null);
  });
});
