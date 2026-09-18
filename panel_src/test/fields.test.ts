// The labels the panel borrows from the guided form, and the unit it prints once.
//
// The form says "Tempo di salita (s)" because a form field has nowhere else to put the
// unit; the panel prints the number with its unit beside every one of those labels, so
// the bracket would be the unit a second time. What is checked here is that only a
// trailing bracket goes, that a label without one is untouched, and that a bare ratio -
// the roll coefficients - gets no unit at all.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { bareLabel, withUnit } from "../src/engine/fields";

describe("a label beside a number that carries its unit", () => {
  it("drops the unit the form puts in brackets at the end", () => {
    assert.equal(bareLabel("Tempo di salita (s)"), "Tempo di salita");
    assert.equal(bareLabel("Corsa del telo (cm)"), "Corsa del telo");
    assert.equal(bareLabel("Ascent time (s)"), "Ascent time");
  });

  it("leaves a label with no unit exactly as it is", () => {
    assert.equal(bareLabel("Coefficiente di rullo in apertura"), "Coefficiente di rullo in apertura");
  });

  it("drops only a bracket at the very end", () => {
    assert.equal(bareLabel("Tempo (medio) di salita"), "Tempo (medio) di salita");
    assert.equal(bareLabel("Tempo (medio) di salita (s)"), "Tempo (medio) di salita");
  });
});

describe("a number with its unit", () => {
  it("follows the number with the unit, a space between", () => {
    assert.equal(withUnit("21,8", "s"), "21,8 s");
  });

  it("adds nothing to a bare ratio", () => {
    assert.equal(withUnit("2,24", ""), "2,24");
  });
});
