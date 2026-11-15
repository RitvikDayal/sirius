import { test } from "node:test";
import assert from "node:assert/strict";
import { distanceWords, zoneOf, direction, phrase } from "../rules.js";
import { makeRoom, OBJECTS } from "../room.js";

// Same thresholds as src/sirius/alerts.py and src/sirius/fusion.py.
test("distance words", () => {
  assert.equal(distanceWords(0.74), "half a metre");
  assert.equal(distanceWords(0.75), "one metre");
  assert.equal(distanceWords(1.49), "one metre");
  assert.equal(distanceWords(2.49), "two metres");
  assert.equal(distanceWords(4.6), "five metres");
});

test("zones", () => {
  assert.equal(zoneOf(0.8).name, "urgent");
  assert.equal(zoneOf(1.0).name, "near");
  assert.equal(zoneOf(2.6).name, "aware");
  assert.equal(zoneOf(5.1), null);
});

test("direction uses 15 degrees either side of ahead", () => {
  assert.equal(direction(-1, -2), "left");
  assert.equal(direction(0, -2), "ahead");
  assert.equal(direction(1, -2), "right");
});

test("phrase matches what SIRIUS would say", () => {
  assert.equal(phrase("chair", [0, 1.6, 0], [-1.3, 0.5, -2.2]).text, "chair, three metres, left"); // 2.78 m away
  assert.equal(phrase("person", [0, 1.6, 0], [0.2, 0.9, -1.1]).text, "person, one metre, ahead");
});

test("room data", () => {
  const room = makeRoom(1);
  assert.equal(room.positions.length % 3, 0);
  assert.equal(room.tags.length, room.positions.length / 3);
  assert.deepEqual(OBJECTS.map(o => o.label), ["chair", "person", "table", "bottle"]);
});
