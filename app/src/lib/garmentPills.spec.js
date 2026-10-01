import { expect, test } from "vitest";
import { PRIMARY_PILLS, pillsFor } from "./garmentPills.js";

const GARMENTS = [
  { id: "hat_front", label: "Hat Front" },
  { id: "left_chest", label: "Left Chest" },
  { id: "full_back", label: "Full Back" },
  { id: "tote", label: "Tote" },
];

test("the three primary pills are Polo, Hat, Tee in that order", () => {
  expect(PRIMARY_PILLS.map((p) => p.short)).toEqual(["Polo", "Hat", "Tee"]);
  expect(PRIMARY_PILLS.map((p) => p.id)).toEqual(["left_chest", "hat_front", "full_back"]);
});

test("a primary garment shows three pills with that one selected", () => {
  const pills = pillsFor("hat_front", GARMENTS);
  expect(pills.map((p) => p.text)).toEqual(["Polo", "Hat", "Tee"]);
  expect(pills.map((p) => p.selected)).toEqual([false, true, false]);
});

test("each primary pill's title is the engine's full label", () => {
  expect(pillsFor("left_chest", GARMENTS).map((p) => p.title)).toEqual(["Left Chest", "Hat Front", "Full Back"]);
});

test("a garment outside the three adds a fourth, selected pill with its engine label", () => {
  const pills = pillsFor("tote", GARMENTS);
  expect(pills.map((p) => p.text)).toEqual(["Polo", "Hat", "Tee", "Tote"]);
  expect(pills.map((p) => p.selected)).toEqual([false, false, false, true]);
  expect(pills[3].id).toBe("tote");
});

test("an unknown garment id selects nothing and adds nothing", () => {
  const pills = pillsFor("nope", GARMENTS);
  expect(pills.length).toBe(3);
  expect(pills.some((p) => p.selected)).toBe(false);
});
