// `use:tip={"fillAngle"}` — a styled help popover on hover or keyboard focus
// (2026-09-30). The copy comes from lib/settingHelp.js by key; this file only
// knows how to show it.
//
// Why not the native `title`: a browser tooltip waits about a second, cannot
// be styled, never appears for keyboard users, and does not exist on touch.
// Thirty-one of them were already in DigitizePanel and only one covered a
// setting; the customer's question ("what does Fill angle do?") had no
// answer anywhere on screen.
//
// One popover element for the whole app, made on first use and appended to
// <body>, so it can never be clipped by a scrolling panel and there is never
// more than one open. It is `role="tooltip"` and the host gets
// `aria-describedby` while it is open, so a screen reader hears the same
// three sentences a sighted user reads.
//
// Behaviour:
//   pointerenter  -> show after SHOW_DELAY_MS (a pass-over does not flash)
//   pointerleave  -> hide
//   focusin       -> show at once (keyboard users are not pointing, they are
//                    there)
//   focusout      -> hide
//   Escape        -> hide
//   touchstart    -> toggle (touch has no hover)
// Positioned under the host, flipped above when there is no room below, and
// kept inside the viewport horizontally.

import { HELP } from "./settingHelp.js";

export const SHOW_DELAY_MS = 150;
const GAP_PX = 8;
const MARGIN_PX = 8;
const TIP_ID = "tipbox";

let box = null;
let timer = null;
let openFor = null;

function ensureBox() {
  if (box) return box;
  box = document.createElement("div");
  box.id = TIP_ID;
  box.className = "tipbox";
  box.setAttribute("role", "tooltip");
  box.hidden = true;
  document.body.appendChild(box);
  return box;
}

// Built with textContent, never innerHTML: the copy is author-controlled
// today, and this keeps it that way if it ever comes from anywhere else.
function fill(el, h) {
  el.textContent = "";
  const title = document.createElement("strong");
  title.className = "tipbox-title";
  title.textContent = h.title;
  el.appendChild(title);
  for (const [label, text] of [[null, h.what], ["Changes", h.changes], ["When", h.when]]) {
    const p = document.createElement("p");
    p.className = "tipbox-line";
    if (label) {
      const b = document.createElement("b");
      b.textContent = label + ": ";
      p.appendChild(b);
    }
    p.appendChild(document.createTextNode(text));
    el.appendChild(p);
  }
}

function place(el, host) {
  const r = host.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  // Measure at the natural width first, then clamp.
  el.style.left = "0px";
  el.style.top = "0px";
  const w = el.offsetWidth;
  const h = el.offsetHeight;
  let left = r.left + r.width / 2 - w / 2;
  left = Math.max(MARGIN_PX, Math.min(left, vw - w - MARGIN_PX));
  let top = r.bottom + GAP_PX;
  let below = true;
  if (top + h > vh - MARGIN_PX && r.top - GAP_PX - h >= MARGIN_PX) {
    top = r.top - GAP_PX - h;
    below = false;
  }
  el.style.left = Math.round(left) + "px";
  el.style.top = Math.round(top) + "px";
  el.classList.toggle("tipbox-above", !below);
}

export function hideTip() {
  if (timer) { clearTimeout(timer); timer = null; }
  if (!box || box.hidden) { openFor = null; return; }
  box.hidden = true;
  if (openFor) openFor.removeAttribute("aria-describedby");
  openFor = null;
}

function showTip(host, key) {
  const h = HELP[key];
  if (!h) return;
  const el = ensureBox();
  fill(el, h);
  el.hidden = false;
  place(el, host);
  if (openFor && openFor !== host) openFor.removeAttribute("aria-describedby");
  openFor = host;
  host.setAttribute("aria-describedby", TIP_ID);
}

// Svelte action. `key` is a settingHelp key; an unknown key attaches nothing
// but does not throw, so a typo shows up as a missing tip, not a broken
// control.
export function tip(node, key) {
  let current = key;

  function onEnter() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; showTip(node, current); }, SHOW_DELAY_MS);
  }
  function onLeave() { hideTip(); }
  function onFocus() { showTip(node, current); }
  function onKey(e) { if (e.key === "Escape") hideTip(); }
  function onTouch() {
    if (openFor === node) hideTip(); else showTip(node, current);
  }

  node.addEventListener("pointerenter", onEnter);
  node.addEventListener("pointerleave", onLeave);
  node.addEventListener("focusin", onFocus);
  node.addEventListener("focusout", onLeave);
  node.addEventListener("keydown", onKey);
  node.addEventListener("touchstart", onTouch, { passive: true });

  return {
    update(next) {
      current = next;
      if (openFor === node) showTip(node, current);
    },
    destroy() {
      if (openFor === node) hideTip();
      node.removeEventListener("pointerenter", onEnter);
      node.removeEventListener("pointerleave", onLeave);
      node.removeEventListener("focusin", onFocus);
      node.removeEventListener("focusout", onLeave);
      node.removeEventListener("keydown", onKey);
      node.removeEventListener("touchstart", onTouch);
    },
  };
}

// For tests: the live popover element, or null before first use.
export function tipElement() {
  return box;
}
